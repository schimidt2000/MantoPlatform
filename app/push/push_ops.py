"""Os aparelhos com aviso no celular e a entrega do aviso (feature 332).

Camada de baixo: daqui só se registra o aparelho e se entrega o aviso. Quem decide O QUE avisar e
PARA QUEM são `conversas.avisos_ops` (mensagem nova) e `conversas.equipe_ops` (alerta e
transferência), e eles chamam ``despachar`` sempre depois do próprio commit (FR-006).

A entrega roda numa thread própria: é chamada externa (Google/Apple/Mozilla/Microsoft) e não pode
atrasar o webhook nem a tela. Aviso que se perde num deploy não volta — o sino e a lista continuam
valendo (spec, casos de borda). ``WEB_PUSH_SINCRONO`` entrega na hora, para o verify.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlsplit

from flask import current_app
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app import db
from app.conversas.acesso import e_da_equipe
from app.conversas.recusa import Recusa, campo
from app.conversas.relogio import agora_utc
from app.models import PushAssinatura, User
from app.push import constantes as K
from app.push import webpush

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Aviso:
    """O que o service worker mostra (contrato em ``contracts/api.md``)."""

    titulo: str
    corpo: str
    link: str
    tag: str
    urgencia: str = K.URGENCIA_AVISO

    def para_o_aparelho(self) -> dict[str, str]:
        dados = asdict(self)
        dados.pop("urgencia")
        return dados


def chaves() -> webpush.ChavesVapid | None:
    """O par VAPID da Plataforma, ou ``None`` = recurso desligado (FR-009, Princípio XIV)."""
    cfg = current_app.config
    publica = (cfg.get("WEB_PUSH_VAPID_PUBLICA") or "").strip()
    privada = (cfg.get("WEB_PUSH_VAPID_PRIVADA") or "").strip()
    if not publica or not privada:
        return None
    contato = (cfg.get("WEB_PUSH_CONTATO") or "").strip() or "mailto:contato@mantoproducoes.com.br"
    return webpush.ChavesVapid(publica=publica, privada=privada, contato=contato)


def situacao() -> dict[str, Any]:
    """O que a tela precisa para assinar: se está ligado e a chave pública."""
    par = chaves()
    return {"ligado": par is not None, "chave_publica": par.publica if par else None}


# ── Registro do aparelho (História 1) ────────────────────────────────────────────────────────────


def _servico_conhecido(endpoint: str) -> bool:
    partes = urlsplit(endpoint)
    host = (partes.hostname or "").lower()
    if partes.scheme != "https" or not host:
        return False
    return any(host == s.lstrip(".") or host.endswith(s) for s in K.SERVICOS_DE_AVISO)


def _chave_valida(texto: Any, tamanho: int, maximo: int) -> bool:
    if not isinstance(texto, str) or not texto or len(texto) > maximo:
        return False
    try:
        return len(webpush.b64_decodificar(texto)) == tamanho
    except ValueError:
        return False


def _aparelho_valido(dados: Any) -> tuple[str, str, str]:
    """O ``PushSubscription.toJSON()`` do navegador, conferido; senão a recusa 422 do campo."""
    dados = dados if isinstance(dados, dict) else {}
    endpoint = dados.get("endpoint")
    keys = dados.get("keys") if isinstance(dados.get("keys"), dict) else {}
    p256dh, auth = keys.get("p256dh"), keys.get("auth")
    ok = (
        isinstance(endpoint, str)
        and len(endpoint) <= K.ENDPOINT_MAXIMO
        and _servico_conhecido(endpoint)
        # p256dh é um ponto P-256 sem compressão (65 bytes); auth, 16 bytes (RFC 8291 §3).
        and _chave_valida(p256dh, 65, 255)
        and _chave_valida(auth, 16, 64)
    )
    if not ok:
        raise campo("aparelho", K.TEXTO_APARELHO_INVALIDO)
    return endpoint, p256dh, auth


def registrar(user_id: int, dados: Any, navegador: str | None) -> None:
    """Grava o aparelho para a pessoa logada (FR-002). Comita.

    O ``endpoint`` é UNIQUE: o mesmo navegador registrado de novo, por qualquer pessoa, continua um
    registro só e passa a ser de quem registrou por último (quem está logado é quem está com ele).
    Funciona com o envio travado, para a tela poder ser conferida no local.

    Raises:
        Recusa: 503 ``nao_configurado`` sem as chaves; 422 ``fields.aparelho`` com dado inválido.
    """
    if chaves() is None:
        raise Recusa("nao_configurado", K.TEXTO_DESLIGADO, 503)
    endpoint, p256dh, auth = _aparelho_valido(dados)
    navegador = (navegador or "")[: K.NAVEGADOR_MAXIMO] or None
    db.session.execute(
        pg_insert(PushAssinatura)
        .values(
            user_id=user_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            navegador=navegador,
            created_at=agora_utc(),
        )
        .on_conflict_do_update(
            constraint="uq_push_assinaturas_endpoint",
            set_={"user_id": user_id, "p256dh": p256dh, "auth": auth, "navegador": navegador},
        )
    )
    db.session.commit()


def remover(user_id: int, endpoint: Any) -> None:
    """Desativa o aparelho. Só o da própria pessoa: o de outra é ignorado em silêncio. Comita."""
    if not isinstance(endpoint, str) or not endpoint:
        return
    PushAssinatura.query.filter_by(user_id=user_id, endpoint=endpoint).delete()
    db.session.commit()


# ── Entrega (Histórias 2 e 3) ────────────────────────────────────────────────────────────────────


def despachar(user_ids: Iterable[int], aviso: Aviso) -> None:
    """Entrega o aviso nos aparelhos dessas pessoas, fora do caminho de quem chamou. Nunca levanta.

    Chamar DEPOIS do commit do fato (FR-006): o aviso de algo que deu rollback não pode tocar.
    """
    ids = sorted({int(uid) for uid in user_ids if uid is not None})
    if not ids:
        return
    if _parado():  # travado ou sem chaves: nada sai, nem vale abrir a thread
        logger.info("[push] travado ou desligado: %s não saiu", aviso.tag)
        return
    if current_app.config.get("WEB_PUSH_SINCRONO"):
        entregar(ids, aviso)
        return
    app = current_app._get_current_object()  # noqa: SLF001 — a thread precisa do app real
    threading.Thread(target=_entregar_em_segundo_plano, args=(app, ids, aviso), daemon=True).start()


def _parado() -> bool:
    return bool(current_app.config.get("WEB_PUSH_SUPPRESS")) or chaves() is None


def _entregar_em_segundo_plano(app: Any, ids: list[int], aviso: Aviso) -> None:
    with app.app_context():
        try:
            entregar(ids, aviso)
        finally:
            db.session.remove()


def entregar(user_ids: list[int], aviso: Aviso) -> int:
    """Entrega agora e devolve em quantos aparelhos o serviço aceitou. Nunca levanta (FR-006)."""
    try:
        return _entregar(user_ids, aviso)
    except Exception:  # noqa: BLE001 — o aviso nunca derruba quem chamou
        db.session.rollback()
        logger.exception("[push] falha ao entregar %s", aviso.tag)
        return 0


def _entregar(user_ids: list[int], aviso: Aviso) -> int:
    if current_app.config.get("WEB_PUSH_SUPPRESS"):
        logger.info("[push] travado: %s não saiu (ambiente local)", aviso.tag)
        return 0
    par = chaves()
    if par is None:
        return 0
    # Filtro no envio: quem perdeu o papel ou foi desativado não recebe, mesmo com aparelho.
    equipe = [u.id for u in User.query.filter(User.id.in_(user_ids)).all() if e_da_equipe(u)]
    if not equipe:
        return 0
    aparelhos = PushAssinatura.query.filter(PushAssinatura.user_id.in_(equipe)).all()
    corpo = aviso.para_o_aparelho()
    entregues = 0
    for aparelho in aparelhos:
        destino = {"endpoint": aparelho.endpoint, "p256dh": aparelho.p256dh, "auth": aparelho.auth}
        try:
            webpush.enviar(destino, corpo, par, ttl=K.TTL_S, urgencia=aviso.urgencia)
        except webpush.AparelhoSumiu as exc:
            logger.info(
                "[push] aparelho %s de user %s sumiu (%s): apagado",
                aparelho.id,
                aparelho.user_id,
                exc,
            )
            db.session.delete(aparelho)
            continue
        except webpush.AvisoFalhou as exc:
            logger.warning(
                "[push] aviso %s não entregue no aparelho %s: %s",
                aviso.tag,
                aparelho.id,
                str(exc)[: K.ERRO_MAXIMO],
            )
            continue
        aparelho.ultimo_aviso_em = agora_utc()
        entregues += 1
    db.session.commit()
    return entregues
