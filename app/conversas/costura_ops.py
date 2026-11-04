"""O orçamento e o formulário pela conversa (feature 333): a costura das Conversas com a Plataforma.

``enviar_orcamento`` não fala com a Meta: manda cada parte pelo envio da conversa
(`envio_ops.enviar_texto` e `enviar_arquivo`), que já faz a chave idempotente, a trava, a janela, o
commit antes da chamada e o "não entregue" com o motivo. A ordem (research R1):

1. o pedido repetido (mesma chave) segue com o registro que já existe, e cada parte já enviada volta
   como está — só a que faltou (queda no meio) sai agora;
2. canal, trava e janela, ANTES de criar a ficha e o registro (com a janela fechada, nada nasce);
3. a ficha da conversa (`ficha_ops.ficha_para_envio`) e a do orçamento, só se ele ainda não tem;
4. o registro do envio, pela chave UNIQUE;
5. as partes do texto, na ordem, e depois o PDF; por fim, os ids no registro.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app import db
from app.config import PLATFORM_BASE_URL
from app.conversas import constantes as K
from app.conversas import envio_ops, ficha_ops
from app.conversas.configuracao import CfgWhatsapp
from app.conversas.leitura_ops import nome_da_conversa
from app.conversas.recusa import Recusa, campo
from app.conversas.relogio import agora_utc
from app.models import Conversa, ConversaMensagem, OrcamentoEnvio, OrcamentoHistory, User
from app.orcamento import quote_ops


@dataclass(frozen=True)
class EnvioDoOrcamento:
    """O registro, as mensagens que saíram (partes do texto e o PDF) e se o pedido é novo."""

    registro: OrcamentoEnvio
    mensagens: list[ConversaMensagem]
    conversa: Conversa
    novo: bool


# ── Divisão do texto ─────────────────────────────────────────────────────────────────────────────


def _por_caractere(texto: str, limite: int, medir: Callable[[str], int]) -> list[str]:
    partes, atual = [], ""
    for letra in texto:
        if atual and medir(atual + letra) > limite:
            partes.append(atual)
            atual = letra
        else:
            atual += letra
    return partes + ([atual] if atual else [])


def _dividir(
    texto: str, limite: int, medir: Callable[[str], int], separadores: tuple[str, ...]
) -> list[str]:
    if medir(texto) <= limite:
        return [texto]
    if not separadores:
        return _por_caractere(texto, limite, medir)
    separador, resto = separadores[0], separadores[1:]
    partes: list[str] = []
    atual = ""
    for pedaco in texto.split(separador):
        candidato = f"{atual}{separador}{pedaco}" if atual else pedaco
        if medir(candidato) <= limite:
            atual = candidato
            continue
        if atual:
            partes.append(atual)
        if medir(pedaco) <= limite:
            atual = pedaco
        else:
            menores = _dividir(pedaco, limite, medir, resto)
            partes.extend(menores[:-1])
            atual = menores[-1]
    if atual:
        partes.append(atual)
    return partes


def dividir_texto(texto: str, limite: int, medir: Callable[[str], int] = len) -> list[str]:
    """Divide entre parágrafos; parágrafo grande, por linha; linha grande, por palavra (R2).

    ``medir`` conta caracteres (WhatsApp) ou bytes de UTF-8 (Instagram). Nunca corta dentro de um
    caractere. Partes vazias somem.
    """
    partes = _dividir((texto or "").strip(), limite, medir, ("\n\n", "\n", " "))
    return [p.strip() for p in partes if p.strip()]


def _bytes_utf8(texto: str) -> int:
    return len(texto.encode("utf-8"))


def _partes_do_texto(conversa: Conversa, texto: str) -> list[str]:
    if conversa.canal == K.CANAL_INSTAGRAM:
        return dividir_texto(texto, K.TEXTO_MAXIMO_IG_BYTES, _bytes_utf8)
    return dividir_texto(texto, K.TEXTO_MAXIMO)


# ── Envio do orçamento ───────────────────────────────────────────────────────────────────────────


def _chave_base(chave: Any) -> str:
    chave = chave.strip() if isinstance(chave, str) else ""
    if not K.CHAVE_ENVIO_MINIMA <= len(chave) <= K.CHAVE_BASE_MAXIMA:
        raise campo("chave_envio", "Chave de envio inválida. Recarregue a tela e tente novamente.")
    return chave


def _orcamento_ou_404(orcamento_id: Any) -> OrcamentoHistory:
    valido = isinstance(orcamento_id, int) and not isinstance(orcamento_id, bool)
    entry = db.session.get(OrcamentoHistory, orcamento_id) if valido else None
    if entry is None:
        raise Recusa("nao_encontrada", K.TEXTO_ORCAMENTO_NAO_ENCONTRADO, 404)
    return entry


def _quote_com_mensagem(entry: OrcamentoHistory) -> tuple[dict, str]:
    """O orçamento congelado e a mensagem pronta. O antigo (sem snapshot) não tem a mensagem."""
    try:
        quote = json.loads(entry.result_snapshot) if entry.result_snapshot else None
    except (TypeError, ValueError):
        quote = None
    mensagem = (quote or {}).get("message") if isinstance(quote, dict) else None
    if not isinstance(mensagem, str) or not mensagem.strip():
        raise campo("orcamento", K.TEXTO_ORCAMENTO_SEM_MENSAGEM)
    return quote, mensagem


def _registro(
    chave: str, entry: OrcamentoHistory, conversa: Conversa, autor_id: int | None
) -> OrcamentoEnvio:
    db.session.execute(
        pg_insert(OrcamentoEnvio)
        .values(
            orcamento_id=entry.id,
            conversa_id=conversa.id,
            autor_id=autor_id,
            chave_envio=chave,
            created_at=agora_utc(),
        )
        .on_conflict_do_nothing(index_elements=["chave_envio"])
    )
    db.session.commit()
    return OrcamentoEnvio.query.filter_by(chave_envio=chave).one()


def _pdf(
    conversa: Conversa, quote: dict, chave: str, autor_id: int | None, cfg: CfgWhatsapp
) -> ConversaMensagem:
    """O PDF, gerado só se a parte ainda não saiu por esta chave."""
    if existente := ConversaMensagem.query.filter_by(chave_envio=chave).first():
        return existente
    from app.orcamento.pdf import gerar_orcamento_pdf

    dados = gerar_orcamento_pdf(quote)
    envio = envio_ops.enviar_arquivo(
        conversa.id, dados, quote_ops.nome_do_pdf(quote), K.MIME_PDF, None, chave, autor_id, cfg
    )
    return envio.mensagem


def enviar_orcamento(
    conversa_id: int,
    orcamento_id: Any,
    chave: Any,
    autor_id: int | None,
    cfg: CfgWhatsapp,
    cliente: Any = None,
) -> EnvioDoOrcamento:
    """A mensagem pronta (em partes, no Instagram) e o PDF, pela conversa (FR-003 a FR-008).

    Raises:
        Recusa: 404 (conversa, orçamento); 422 (chave, orçamento sem mensagem, ficha); as do envio
            comum (409 janela/trava, 503 desligado), antes de criar qualquer coisa.
    """
    chave = _chave_base(chave)
    conversa = envio_ops.conversa_ou_404(conversa_id)
    entry = _orcamento_ou_404(orcamento_id)
    quote, mensagem = _quote_com_mensagem(entry)
    registro = OrcamentoEnvio.query.filter_by(chave_envio=chave).first()
    novo = registro is None
    if registro is not None and (registro.conversa_id, registro.orcamento_id) != (
        conversa.id,
        entry.id,
    ):
        raise campo("chave_envio", "Chave de envio inválida. Recarregue a tela e tente novamente.")
    if novo:
        envio_ops.conferir_envio(cfg, conversa)
        # O nome do orçamento só batiza a ficha nova se ele ainda não é de ninguém: o orçamento da Ana
        # reenviado para a conversa da Bruna criaria a ficha "Ana" com o telefone da Bruna.
        nome = entry.client_name if entry.client_id is None else None
        ficha = ficha_ops.ficha_para_envio(conversa, cliente, nome)
        if entry.client_id is None:
            entry.client_id = ficha.id  # a ficha do primeiro envio fica (FR-006)
            db.session.commit()
        registro = _registro(chave, entry, conversa, autor_id)
    mensagens = [
        envio_ops.enviar_texto(conversa.id, parte, f"{chave}:{indice}", autor_id, cfg).mensagem
        for indice, parte in enumerate(_partes_do_texto(conversa, mensagem), start=1)
    ]
    mensagens.append(_pdf(conversa, quote, f"{chave}{K.SUFIXO_DO_PDF}", autor_id, cfg))
    registro.texto_mensagem_id = mensagens[0].id
    registro.pdf_mensagem_id = mensagens[-1].id
    db.session.commit()
    return EnvioDoOrcamento(registro, mensagens, conversa, novo)


# ── Leitura: envios do orçamento ─────────────────────────────────────────────────────────────────


def _iso(momento: datetime | None) -> str | None:
    return momento.replace(tzinfo=UTC).isoformat() if momento is not None else None


def serializar_envio(registro: OrcamentoEnvio) -> dict[str, Any]:
    conversa = registro.conversa
    autor = db.session.get(User, registro.autor_id) if registro.autor_id else None
    return {
        "id": registro.id,
        "orcamento_id": registro.orcamento_id,
        "conversa_id": registro.conversa_id,
        "conversa_nome": nome_da_conversa(conversa) if conversa is not None else None,
        "canal": conversa.canal if conversa is not None else None,
        "autor": autor.name if autor is not None else None,
        "quando": _iso(registro.created_at),
    }


def envios_do_orcamento(orcamento_id: int) -> list[dict[str, Any]]:
    """Os envios pela conversa, do mais novo ao mais antigo (FR-012)."""
    registros = (
        OrcamentoEnvio.query.filter_by(orcamento_id=orcamento_id)
        .order_by(OrcamentoEnvio.created_at.desc(), OrcamentoEnvio.id.desc())
        .all()
    )
    return [serializar_envio(r) for r in registros]


def enviados_em(orcamento_ids: list[int]) -> dict[int, str]:
    """O último envio de cada orçamento da página do histórico, num SELECT só (o selo)."""
    if not orcamento_ids:
        return {}
    linhas = (
        db.session.query(OrcamentoEnvio.orcamento_id, func.max(OrcamentoEnvio.created_at))
        .filter(OrcamentoEnvio.orcamento_id.in_(orcamento_ids))
        .group_by(OrcamentoEnvio.orcamento_id)
        .all()
    )
    return {orcamento_id: _iso(quando) for orcamento_id, quando in linhas}


# ── Formulário ───────────────────────────────────────────────────────────────────────────────────


def _primeiro_nome(conversa: Conversa) -> str | None:
    """O primeiro nome da ficha e, sem ela, o do perfil. Telefone e "Contato do Instagram" não são nome."""
    nome = (conversa.cliente.name if conversa.cliente is not None else conversa.nome_perfil) or ""
    partes = nome.strip().split()
    return partes[0] if partes else None


def formularios_da_conversa(conversa_id: int) -> list[dict[str, str]]:
    """Os formulários públicos com o link curto e o texto pronto para esta conversa (FR-010)."""
    conversa = envio_ops.conversa_ou_404(conversa_id)
    nome = _primeiro_nome(conversa)
    formularios = []
    for tipo, titulo, slug in K.FORMULARIOS_PUBLICOS:
        link = f"{PLATFORM_BASE_URL}/f/{slug}"
        texto = (
            K.TEXTO_DO_FORMULARIO.format(nome=nome, link=link)
            if nome
            else K.TEXTO_DO_FORMULARIO_SEM_NOME.format(link=link)
        )
        formularios.append({"tipo": tipo, "titulo": titulo, "link": link, "texto": texto})
    return formularios
