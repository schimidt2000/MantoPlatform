"""Configuração do WhatsApp lida a cada chamada (feature 325; molde ``virtuais_ops._ipc_cfg``).

Relê o ``current_app.config`` toda vez, de propósito: o verify troca a configuração em tempo de
execução, e uma chave ausente cai no lado seguro (travado, desligado).
"""

from __future__ import annotations

from dataclasses import dataclass

from flask import current_app

from app.integracoes.instagram_client import ConexaoInstagram
from app.integracoes.whatsapp_client import ConexaoMeta


@dataclass(frozen=True)
class CfgWhatsapp:
    """O retrato da configuração do módulo num instante."""

    ligado: bool
    travado: bool
    app_secret: str
    verify_token: str
    pasta_midia: str
    poll_segundos: int
    conexao: ConexaoMeta


def cfg_whatsapp() -> CfgWhatsapp:
    """Monta a configuração a partir do ``current_app.config``.

    ``ligado`` exige os quatro mínimos (token, segredo do app, token de verificação e id do número);
    sem eles o webhook responde 404, o envio é recusado e o menu some (FR-015).
    """
    config = current_app.config
    token = config.get("WHATSAPP_ACCESS_TOKEN") or ""
    segredo = config.get("WHATSAPP_APP_SECRET") or ""
    verificacao = config.get("WHATSAPP_VERIFY_TOKEN") or ""
    numero = config.get("WHATSAPP_PHONE_NUMBER_ID") or ""
    travado = bool(config.get("WHATSAPP_SUPPRESS_SEND", True))
    conexao = ConexaoMeta(
        base=config.get("WHATSAPP_GRAPH_BASE") or "https://graph.facebook.com",
        versao=config.get("WHATSAPP_GRAPH_VERSION") or "v26.0",
        token=token,
        phone_number_id=numero,
        waba_id=config.get("WHATSAPP_WABA_ID") or "",
        travada=travado,
    )
    return CfgWhatsapp(
        ligado=bool(token and segredo and verificacao and numero),
        travado=travado,
        app_secret=segredo,
        verify_token=verificacao,
        pasta_midia=config.get("CONVERSAS_MEDIA_FOLDER") or "",
        poll_segundos=int(config.get("WHATSAPP_POLL_SEGUNDOS") or 5),
        conexao=conexao,
    )


@dataclass(frozen=True)
class CfgInstagram:
    """O retrato da configuração do Instagram Direct num instante (feature 330)."""

    ligado: bool
    travado: bool
    app_secret: str
    verify_token: str
    account_id: str
    pasta_midia: str
    conexao: ConexaoInstagram


def cfg_instagram() -> CfgInstagram:
    """Monta a configuração do Instagram a partir do ``current_app.config``.

    O app da Meta é o mesmo do WhatsApp: o segredo e a verificação do aviso vêm das variáveis do
    WhatsApp; a trava também (é a do "envio pela Meta"). ``ligado`` exige as cinco.
    """
    config = current_app.config
    token = config.get("INSTAGRAM_ACCESS_TOKEN") or ""
    pagina = config.get("INSTAGRAM_PAGE_ID") or ""
    conta = config.get("INSTAGRAM_ACCOUNT_ID") or ""
    segredo = config.get("WHATSAPP_APP_SECRET") or ""
    verificacao = config.get("WHATSAPP_VERIFY_TOKEN") or ""
    travado = bool(config.get("WHATSAPP_SUPPRESS_SEND", True))
    conexao = ConexaoInstagram(
        base=config.get("WHATSAPP_GRAPH_BASE") or "https://graph.facebook.com",
        versao=config.get("WHATSAPP_GRAPH_VERSION") or "v26.0",
        token=token,
        page_id=pagina,
        account_id=conta,
        travada=travado,
    )
    return CfgInstagram(
        ligado=bool(token and pagina and conta and segredo and verificacao),
        travado=travado,
        app_secret=segredo,
        verify_token=verificacao,
        account_id=conta,
        pasta_midia=config.get("CONVERSAS_MEDIA_FOLDER") or "",
        conexao=conexao,
    )


def conexao_dos_anuncios() -> ConexaoMeta | None:
    """A conexão da consulta da campanha do anúncio (feature 334), ou ``None`` quando ela está desligada.

    Desligada sem token e com a trava do "envio pela Meta" (a cópia local, o verify): o anúncio fica
    esperando e sai na primeira consulta liberada (FR-011). O token próprio vence o do WhatsApp.
    """
    config = current_app.config
    token = config.get("META_ANUNCIOS_TOKEN") or config.get("WHATSAPP_ACCESS_TOKEN") or ""
    if bool(config.get("WHATSAPP_SUPPRESS_SEND", True)) or not token:
        return None
    return ConexaoMeta(
        base=config.get("WHATSAPP_GRAPH_BASE") or "https://graph.facebook.com",
        versao=config.get("WHATSAPP_GRAPH_VERSION") or "v26.0",
        token=token,
        phone_number_id="",
        travada=False,
    )


def canais_ligados() -> list[str]:
    """Os canais configurados, na ordem da lista (feature 330): é o que liga o menu e o filtro."""
    ligados = []
    if cfg_whatsapp().ligado:
        ligados.append("whatsapp")
    if cfg_instagram().ligado:
        ligados.append("instagram")
    return ligados
