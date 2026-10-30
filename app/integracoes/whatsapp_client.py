"""Cliente da Cloud API do WhatsApp (Graph API da Meta) — feature 325, Conversas.

Envia mensagens (texto, mídia, modelo), sobe e baixa mídia, lista os modelos aprovados e marca
mensagem como lida. Contrato conferido em ``specs/325-crm-whatsapp-fundacao/research.md``
§Confirmações (versão fixa, ``Authorization: Bearer``, erro em ``{"error": {"code", ...}}``).

Distinção que o resto do sistema depende (molde da ClickSign e da InfinitePay):

* ``WhatsappRecusou`` — a Meta respondeu e recusou (4xx com ``error.code``): janela fechada, token
  vencido, modelo inexistente. O código vai para ``constantes.MOTIVO_DO_ERRO``.
* ``WhatsappIndisponivel`` — **"não sei"**: timeout, 5xx, 429, resposta ilegível.
* ``WhatsappTravado`` — subclasse de indisponível: o processo está proibido de falar com a Meta
  (``_suppress_whatsapp``, Princípio XIV). Travado por padrão: ``ConexaoMeta.travada`` nasce True.
* ``WhatsappArquivoGrande`` — a mídia passa do teto que a Plataforma guarda: falha definitiva,
  não adianta tentar de novo.

O módulo não importa Flask (Princípio III): a conexão chega pronta de ``conversas.configuracao``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)

# (conexão, leitura) em segundos; o download de mídia (até 25 MB) ganha leitura maior.
TIMEOUT_SECONDS = (5, 30)
TIMEOUT_DOWNLOAD = (5, 120)
TAMANHO_DA_PAGINA_DE_MODELOS = 100
PAGINAS_MAXIMAS_DE_MODELOS = 20


@dataclass(frozen=True)
class ConexaoMeta:
    """O que toda chamada precisa: endereço, versão, token, ids e a trava do ambiente."""

    base: str
    versao: str
    token: str
    phone_number_id: str
    waba_id: str = ""
    travada: bool = True

    def url(self, caminho: str) -> str:
        """URL completa da Graph API para ``caminho`` (sem barra inicial)."""
        return f"{self.base}/{self.versao}/{caminho}"


class WhatsappErro(Exception):
    """Falha ao falar com a Meta. Base das exceções deste módulo."""


class WhatsappIndisponivel(WhatsappErro):
    """A Meta não respondeu a tempo ou respondeu de forma inutilizável: "não sei"."""


class WhatsappTravado(WhatsappIndisponivel):
    """Este processo está proibido de falar com a Meta real (cópia local, verify)."""


class WhatsappArquivoGrande(WhatsappErro):
    """A mídia passa do teto que a Plataforma guarda (falha definitiva)."""


class WhatsappRecusou(WhatsappErro):
    """A Meta recusou a requisição (4xx com ``error.code``)."""

    def __init__(self, message: str, *, status: int | None = None, code: int | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


def _cabecalhos(token: str) -> dict[str, str]:
    """Token de System User (Bearer)."""
    return {"Authorization": f"Bearer {token}"}


def _erro_da_meta(response: requests.Response) -> WhatsappRecusou:
    """Traduz o corpo de erro da Graph API (``{"error": {"message", "code"}}``)."""
    try:
        corpo = response.json()
    except ValueError:
        corpo = {}
    erro = corpo.get("error") if isinstance(corpo, dict) else None
    erro = erro if isinstance(erro, dict) else {}
    codigo = erro.get("code")
    mensagem = erro.get("message") or f"HTTP {response.status_code}"
    return WhatsappRecusou(
        str(mensagem), status=response.status_code, code=codigo if isinstance(codigo, int) else None
    )


def _requisitar(
    conexao: ConexaoMeta,
    metodo: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    files: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Faz a requisição e devolve o JSON, traduzindo toda falha em exceção deste módulo."""
    if conexao.travada:
        raise WhatsappTravado("Chamada à Meta travada neste processo.")
    if not conexao.token:
        raise WhatsappRecusou("Token do WhatsApp não configurado.", code=200)
    try:
        response = requests.request(
            metodo,
            url,
            headers=_cabecalhos(conexao.token),
            params=params,
            json=json_body,
            files=files,
            data=data,
            timeout=TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        logger.warning("[whatsapp] timeout em %s %s", metodo, url)
        raise WhatsappIndisponivel("A Meta não respondeu a tempo.") from exc
    except requests.RequestException as exc:
        logger.warning("[whatsapp] erro de rede em %s %s: %s", metodo, url, exc)
        raise WhatsappIndisponivel("Falha de rede ao falar com a Meta.") from exc

    if response.status_code == 429 or response.status_code >= 500:
        logger.warning("[whatsapp] %s %s devolveu %s", metodo, url, response.status_code)
        raise WhatsappIndisponivel(f"Meta indisponível (HTTP {response.status_code}).")
    if response.status_code >= 400:
        raise _erro_da_meta(response)
    try:
        corpo = response.json()
    except ValueError as exc:
        raise WhatsappIndisponivel("Resposta ilegível da Meta.") from exc
    if not isinstance(corpo, dict):
        raise WhatsappIndisponivel("Formato inesperado na resposta da Meta.")
    return corpo


def enviar(conexao: ConexaoMeta, corpo: dict[str, Any]) -> dict[str, str | None]:
    """Envia uma mensagem (``POST /{phone_number_id}/messages``).

    ``corpo`` já traz ``to``/``recipient``, ``type`` e o bloco do tipo; ``messaging_product`` é
    acrescentado aqui. Devolve ``{"id": wamid, "wa_id": ...}``.

    Raises:
        WhatsappRecusou / WhatsappIndisponivel / WhatsappTravado.
    """
    payload = {"messaging_product": "whatsapp", "recipient_type": "individual", **corpo}
    resposta = _requisitar(
        conexao, "POST", conexao.url(f"{conexao.phone_number_id}/messages"), json_body=payload
    )
    mensagens = resposta.get("messages") or [{}]
    contatos = resposta.get("contacts") or [{}]
    wamid = mensagens[0].get("id") if isinstance(mensagens[0], dict) else None
    if not wamid:
        raise WhatsappIndisponivel("A Meta não devolveu o id da mensagem.")
    wa_id = contatos[0].get("wa_id") if isinstance(contatos[0], dict) else None
    return {"id": str(wamid), "wa_id": wa_id}


def marcar_lida(conexao: ConexaoMeta, wamid: str) -> None:
    """Marca a mensagem recebida como lida (tique azul para a cliente)."""
    _requisitar(
        conexao,
        "POST",
        conexao.url(f"{conexao.phone_number_id}/messages"),
        json_body={"messaging_product": "whatsapp", "status": "read", "message_id": wamid},
    )


def subir_midia(conexao: ConexaoMeta, dados: bytes, mime: str, nome: str) -> str:
    """Sobe o arquivo para a Meta (``POST /{phone_number_id}/media``) e devolve o id da mídia."""
    resposta = _requisitar(
        conexao,
        "POST",
        conexao.url(f"{conexao.phone_number_id}/media"),
        files={"file": (nome, dados, mime)},
        data={"messaging_product": "whatsapp", "type": mime},
    )
    media_id = resposta.get("id")
    if not media_id:
        raise WhatsappIndisponivel("A Meta não devolveu o id da mídia.")
    return str(media_id)


def consultar_midia(conexao: ConexaoMeta, media_id: str) -> dict[str, Any]:
    """``GET /{media_id}``: ``url`` (vale 5 min, exige o token), ``mime_type`` e ``file_size``."""
    resposta = _requisitar(
        conexao, "GET", conexao.url(media_id), params={"phone_number_id": conexao.phone_number_id}
    )
    if not resposta.get("url"):
        raise WhatsappIndisponivel("A Meta não devolveu a url da mídia.")
    return resposta


def baixar_midia(conexao: ConexaoMeta, url: str, limite_bytes: int) -> bytes:
    """Baixa o arquivo da url da Meta, com o token e um teto (molde ``clicksign_client.baixar``).

    Raises:
        WhatsappTravado: processo travado.
        WhatsappArquivoGrande: o arquivo passa de ``limite_bytes``.
        WhatsappIndisponivel: falha de rede ou status ruim (inclusive a url vencida: 404).
    """
    if conexao.travada:
        raise WhatsappTravado("Download da Meta travado neste processo.")
    try:
        response = requests.get(
            url, headers=_cabecalhos(conexao.token), timeout=TIMEOUT_DOWNLOAD, stream=True
        )
    except requests.RequestException as exc:
        raise WhatsappIndisponivel("Falha ao baixar a mídia da Meta.") from exc
    if response.status_code != 200:
        raise WhatsappIndisponivel(f"Download da mídia devolveu HTTP {response.status_code}.")
    partes: list[bytes] = []
    total = 0
    for parte in response.iter_content(chunk_size=64 * 1024):
        total += len(parte)
        if total > limite_bytes:
            raise WhatsappArquivoGrande("Mídia acima do teto da Plataforma.")
        partes.append(parte)
    return b"".join(partes)


def listar_modelos(conexao: ConexaoMeta) -> list[dict[str, Any]]:
    """Modelos APROVADOS da conta (``GET /{waba_id}/message_templates``), todas as páginas."""
    if not conexao.waba_id:
        raise WhatsappRecusou("WABA do WhatsApp não configurada.", code=100)
    params: dict[str, Any] | None = {
        "fields": "name,status,language,category,components,parameter_format",
        "status": "APPROVED",
        "limit": TAMANHO_DA_PAGINA_DE_MODELOS,
    }
    url: str | None = conexao.url(f"{conexao.waba_id}/message_templates")
    modelos: list[dict[str, Any]] = []
    for _ in range(PAGINAS_MAXIMAS_DE_MODELOS):
        if not url:
            break
        resposta = _requisitar(conexao, "GET", url, params=params)
        modelos.extend(m for m in resposta.get("data") or [] if isinstance(m, dict))
        # A página seguinte vem com a query inteira na url `next`.
        url = (resposta.get("paging") or {}).get("next")
        params = None
    return modelos
