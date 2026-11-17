"""O pós-evento único: uma mensagem no dia seguinte, copiada ou enviada pela conversa (feature 350).

A mensagem é montada **aqui** (uma fonte só para o texto copiado e o enviado): agradecimento, link
das fotos (se a equipe colar um), avaliação, indicação, convite ao aceite (pelo mesmo link) e
"responda SAIR". Não exige aceite de novidades — é relacionamento com quem acabou de ser cliente —
e pela conversa sai só como texto livre na janela aberta, nunca como modelo de marketing.

Núcleo puro, sem ``flask.request``. O registro (`PosEvento`) é um por evento. O envio pela conversa
usa `envio_ops.enviar_texto` (trava `_suppress_whatsapp`, chave idempotente); o import é tardio
porque `app.conversas` já depende de `app.clientes` (consentimento) e o ciclo quebraria o boot.

Nada aqui dispara sozinho: a equipe abre a lista e decide (spec 350, FR-020).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import exists, func, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app import db
from app.calendar.event_ops import ENSAIO_TITLE_PREFIX, ensure_feedback_token
from app.constants import (
    POS_EVENTO_CANAL_CONVERSA,
    POS_EVENTO_CANAL_COPIADO,
    POS_EVENTO_DIAS,
    now_sp,
)
from app.models import CalendarEvent, ClientFeedback, Conversa, ConversaMensagem, PosEvento

FOTOS_MAXIMO = 500
_ESQUEMAS_DE_FOTOS = ("https://", "http://")
CANAIS = (POS_EVENTO_CANAL_COPIADO, POS_EVENTO_CANAL_CONVERSA)
TIPO_ENSAIO = "ENSAIO"
_CANAL_WHATSAPP = "whatsapp"
_PREFIXO_DA_CHAVE = "pos-evento-{evento}-"

TEXTO_CANCELADO = "Este evento foi cancelado: não há pós-evento."
TEXTO_SEM_CONVERSA = "A contratante não tem conversa no CRM. Copie a mensagem."
TEXTO_JANELA_FECHADA = "A janela de 24 horas desta conversa fechou. Copie a mensagem."
TEXTO_CRM_DESLIGADO = "O CRM está desligado. Copie a mensagem."
TEXTO_ENVIO_FALHOU = "Não foi possível enviar pela conversa: {motivo} Copie a mensagem."


class PosEventoErro(Exception):
    """Recusa do pós-evento, com o campo (``fields``), o status e o código que a tela compara."""

    def __init__(
        self, campo: str | None, mensagem: str, status: int = 400, codigo: str | None = None
    ) -> None:
        super().__init__(mensagem)
        self.campo = campo
        self.mensagem = mensagem
        self.status = status
        self.codigo = codigo


# ── A mensagem ───────────────────────────────────────────────────────────────────────────────────


def exigir_vivo(event: CalendarEvent) -> None:
    """Evento cancelado não tem pós-evento (409 ``cancelado``, regra da 312)."""
    if event.is_cancelled:
        raise PosEventoErro(None, TEXTO_CANCELADO, 409, "cancelado")


def validar_fotos(valor: Any) -> str | None:
    """O link das fotos é opcional; se vier, é um endereço ``http(s)://``."""
    url = str(valor or "").strip()
    if not url:
        return None
    if not url.lower().startswith(_ESQUEMAS_DE_FOTOS) or " " in url or len(url) > FOTOS_MAXIMO:
        raise PosEventoErro("fotos_url", "Informe o link do álbum (começa com https://).")
    return url


def link_de_avaliacao(event: CalendarEvent, base_publica: str) -> str:
    """O link da página de avaliação (o token nasce na primeira vez e não expira — 130)."""
    token = ensure_feedback_token(event)
    return f"{base_publica.rstrip('/')}/catalogo/avaliar/{token}"


def _primeiro_nome(event: CalendarEvent) -> str | None:
    nome = (event.client.name if event.client else "") or ""
    partes = nome.split()
    return partes[0] if partes else None


def mensagem(event: CalendarEvent, *, link: str, fotos_url: str | None) -> str:
    """A mensagem única, no tom da casa (constituição XV: mensagem que a equipe copia)."""
    nome = _primeiro_nome(event)
    linhas = [
        f"Oi, {nome}! " if nome else "Oi! ",
    ]
    linhas[0] += "Obrigado por celebrar com a Manto. Foi uma alegria fazer parte desse dia! 💙"
    if fotos_url:
        linhas += ["", f"📸 As fotos estão aqui: {fotos_url}"]
    linhas += [
        "",
        "⭐ Conta para a gente como foi? Sua avaliação leva um minuto:",
        f"👉 {link}",
        "",
        "💌 Conhece alguém que vai fazer festa? Indique a Manto: vamos adorar cuidar dessa festa "
        "também.",
        "",
        "🎂 No mesmo link, você pode pedir para receber nossas novidades e um lembrete antes do "
        "próximo aniversário.",
        "",
        "Se não quiser receber mensagens, é só responder SAIR.",
    ]
    return "\n".join(linhas)


# ── O estado ─────────────────────────────────────────────────────────────────────────────────────


def conversa_da_contratante(event: CalendarEvent) -> Conversa | None:
    """A conversa de WhatsApp mais recente da ficha contratante, se houver."""
    if not event.client_id:
        return None
    return (
        Conversa.query.filter_by(client_id=event.client_id, canal=_CANAL_WHATSAPP)
        .order_by(Conversa.ultima_mensagem_em.desc().nullslast(), Conversa.id.desc())
        .first()
    )


def estado_da_conversa(event: CalendarEvent, cfg: Any) -> dict[str, Any]:
    """Pode enviar pela conversa? Se não, o motivo (a tela mostra e oferece copiar)."""
    from app.conversas.leitura_ops import janela_aberta

    conversa = conversa_da_contratante(event)
    motivo = None
    if not cfg.ligado:
        motivo = TEXTO_CRM_DESLIGADO
    elif conversa is None:
        motivo = TEXTO_SEM_CONVERSA
    elif not janela_aberta(conversa):
        motivo = TEXTO_JANELA_FECHADA
    return {
        "pode_enviar": motivo is None,
        "motivo": motivo,
        "conversa_id": conversa.id if conversa else None,
    }


def _avaliacao_recebida(event_id: int) -> bool:
    return db.session.query(exists().where(ClientFeedback.event_id == event_id)).scalar()


def _iso(momento: datetime | None) -> str | None:
    return momento.isoformat() if momento else None


def detalhe(event: CalendarEvent, *, base_publica: str, fotos_url: Any, cfg: Any) -> dict[str, Any]:
    """A prévia do diálogo: mensagem, situação e se dá para enviar pela conversa."""
    exigir_vivo(event)
    registro = PosEvento.query.filter_by(event_id=event.id).first()
    fotos = validar_fotos(fotos_url) if fotos_url is not None else None
    if fotos is None and registro is not None and fotos_url is None:
        fotos = registro.fotos_url
    link = link_de_avaliacao(event, base_publica)
    return {
        "mensagem": mensagem(event, link=link, fotos_url=fotos),
        "link_avaliacao": link,
        "fotos_url": fotos,
        "situacao": registro.canal if registro else "pendente",
        "registrado_em": _iso(registro.registrado_em) if registro else None,
        "avaliacao_recebida": _avaliacao_recebida(event.id),
        "conversa": estado_da_conversa(event, cfg),
    }


# ── O registro e o envio ─────────────────────────────────────────────────────────────────────────


def registrar(
    event: CalendarEvent,
    canal: str,
    fotos_url: str | None,
    user_id: int | None,
    mensagem_id: int | None = None,
) -> PosEvento:
    """Grava (ou atualiza) o registro único do evento. Depois de "conversa", copiar não rebaixa."""
    db.session.execute(
        pg_insert(PosEvento.__table__)
        .values(
            event_id=event.id,
            client_id=event.client_id,
            canal=canal,
            fotos_url=fotos_url,
            mensagem_id=mensagem_id,
            registrado_por_id=user_id,
            registrado_em=now_sp(),
        )
        .on_conflict_do_nothing(index_elements=["event_id"])
    )
    registro = PosEvento.query.filter_by(event_id=event.id).with_for_update().one()
    if registro.canal == POS_EVENTO_CANAL_CONVERSA and canal == POS_EVENTO_CANAL_COPIADO:
        return registro
    registro.canal = canal
    registro.fotos_url = fotos_url or registro.fotos_url
    registro.mensagem_id = mensagem_id or registro.mensagem_id
    registro.client_id = event.client_id
    registro.registrado_por_id = user_id
    registro.registrado_em = now_sp()
    return registro


def _chave_de_envio(event_id: int) -> str:
    """Uma chave por tentativa: o clique duplo cai na mesma; a tentativa que falhou libera outra."""
    prefixo = _PREFIXO_DA_CHAVE.format(evento=event_id)
    falhas = ConversaMensagem.query.filter(
        ConversaMensagem.chave_envio.like(f"{prefixo}%"), ConversaMensagem.situacao == "falhou"
    ).count()
    return f"{prefixo}{falhas + 1}"


def enviar_pela_conversa(
    event: CalendarEvent, *, base_publica: str, fotos_url: str | None, user_id: int, cfg: Any
) -> PosEvento:
    """Manda a mensagem como texto livre na conversa da contratante e registra "conversa"."""
    from app.conversas import envio_ops

    registro = PosEvento.query.filter_by(event_id=event.id).first()
    if registro is not None and registro.canal == POS_EVENTO_CANAL_CONVERSA:
        return registro  # já foi: o segundo clique não manda de novo
    if not cfg.ligado:
        raise PosEventoErro(None, TEXTO_CRM_DESLIGADO, 503, "nao_configurado")
    conversa = conversa_da_contratante(event)
    if conversa is None:
        raise PosEventoErro(None, TEXTO_SEM_CONVERSA, 409, "sem_conversa")
    fotos = fotos_url or (registro.fotos_url if registro else None)
    texto = mensagem(event, link=link_de_avaliacao(event, base_publica), fotos_url=fotos)
    envio = envio_ops.enviar_texto(conversa.id, texto, _chave_de_envio(event.id), user_id, cfg)
    if envio.mensagem.situacao == "falhou":
        motivo = (envio.mensagem.erro_motivo or "a Meta recusou o envio.").rstrip(".") + "."
        raise PosEventoErro(None, TEXTO_ENVIO_FALHOU.format(motivo=motivo), 502, "envio_falhou")
    return registrar(event, POS_EVENTO_CANAL_CONVERSA, fotos, user_id, envio.mensagem.id)


# ── A lista ──────────────────────────────────────────────────────────────────────────────────────


def _eventos_recentes(agora: datetime) -> list[CalendarEvent]:
    inicio = (agora - timedelta(days=POS_EVENTO_DIAS)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return (
        CalendarEvent.query.filter(
            CalendarEvent.start_at >= inicio,
            CalendarEvent.start_at <= agora,
            CalendarEvent.cancelled_at.is_(None),
            CalendarEvent.group_leader_id.is_(None),
            CalendarEvent.parent_event_id.is_(None),
            or_(CalendarEvent.event_type.is_(None), CalendarEvent.event_type != TIPO_ENSAIO),
            ~CalendarEvent.title.startswith(ENSAIO_TITLE_PREFIX),
        )
        .order_by(CalendarEvent.start_at.desc())
        .all()
    )


def listar_recentes(agora: datetime | None = None) -> list[dict[str, Any]]:
    """Os eventos dos últimos 7 dias até agora (SP), com a situação do pós-evento."""
    eventos = _eventos_recentes(agora or now_sp())
    ids = [e.id for e in eventos]
    registros = {r.event_id: r for r in PosEvento.query.filter(PosEvento.event_id.in_(ids)).all()}
    avaliados = {
        linha[0]
        for linha in db.session.query(ClientFeedback.event_id)
        .filter(ClientFeedback.event_id.in_(ids))
        .group_by(ClientFeedback.event_id)
        .having(func.count(ClientFeedback.id) > 0)
        .all()
    }
    return [_item(e, registros.get(e.id), e.id in avaliados) for e in eventos]


def _item(event: CalendarEvent, registro: PosEvento | None, avaliado: bool) -> dict[str, Any]:
    cliente = event.client
    return {
        "event_id": event.id,
        "titulo": event.title,
        "start_at": _iso(event.start_at),
        "cliente": {"id": cliente.id, "name": cliente.name} if cliente else None,
        "situacao": registro.canal if registro else "pendente",
        "registrado_em": _iso(registro.registrado_em) if registro else None,
        "avaliacao_recebida": avaliado,
    }
