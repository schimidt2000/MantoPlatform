"""Cliente da API v3 da ClickSign — leitura dos envelopes da conta e cadastro do aviso (feature 317).

A Manto **lê** a conta: lista envelopes, signatários, eventos e documentos, e baixa o PDF assinado.
A única escrita é o cadastro/remoção do aviso (webhook), feito pelo comando de manutenção. Nada aqui
cria contrato nem manda mensagem a cliente.

Distinção que o resto do sistema depende (molde do cliente da InfinitePay):

* ``ClicksignRecusou`` — a ClickSign respondeu e recusou (4xx compreensível): token errado,
  e-mail do usuário da API não configurado, envelope inexistente.
* ``ClicksignIndisponivel`` — **"não sei"**: timeout, 5xx, 429, resposta ilegível. Quem chama
  mantém o estado como está e tenta na próxima passada; nunca conclui "não assinado".
* ``ClicksignTravada`` — subclasse de indisponível: o processo está proibido de falar com a
  ClickSign real (``_suppress_clicksign``, Princípio XIV). Travado por padrão: quem chama passa
  ``travada=current_app.config["CLICKSIGN_SUPPRESS_CALLS"]``.

O módulo não importa Flask (Princípio III). Contrato conferido no Portão 0 (``research.md``):
``Authorization: <token>`` sem "Bearer", JSON:API, ``page[size]`` máximo 50, filtros
``filter[status|created|modified]`` com intervalo ``AAAA-MM-DD,AAAA-MM-DD``.
"""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any

import requests

logger = logging.getLogger(__name__)

# (conexão, leitura) em segundos.
TIMEOUT_SECONDS = (10, 30)
# Máximo aceito pela API (acima disso, 400 código 118 — Portão 0).
TAMANHO_DA_PAGINA = 50
# Abaixo disto de requisições restantes na janela de 10 s, espera a janela virar (50/10 s).
FOLGA_DO_LIMITE = 5
ESPERA_DO_LIMITE_SEGUNDOS = 10
TIPO_JSON_API = "application/vnd.api+json"


class ClicksignError(Exception):
    """Falha ao falar com a ClickSign. Base das exceções deste módulo."""


class ClicksignIndisponivel(ClicksignError):
    """A ClickSign não respondeu a tempo ou respondeu de forma inutilizável: "não sei"."""


class ClicksignTravada(ClicksignIndisponivel):
    """Este processo está proibido de falar com a ClickSign real (cópia local, verify)."""


class ClicksignRecusou(ClicksignError):
    """A ClickSign recusou a requisição (4xx com corpo compreensível)."""

    def __init__(self, message: str, *, status: int | None = None, code: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


def _cabecalhos(token: str) -> dict[str, str]:
    """Cabeçalhos da API v3: token puro (sem "Bearer") e JSON:API."""
    return {"Authorization": token, "Accept": TIPO_JSON_API, "Content-Type": TIPO_JSON_API}


def _respeitar_limite(response: requests.Response) -> None:
    """Espera a janela do limite virar quando restam poucas requisições (50 a cada 10 s)."""
    restante = response.headers.get("X-Rate-Limit-Remaining")
    try:
        if restante is not None and int(restante) < FOLGA_DO_LIMITE:
            time.sleep(ESPERA_DO_LIMITE_SEGUNDOS)
    except ValueError:
        return


def _requisitar(
    metodo: str,
    url: str,
    *,
    token: str,
    travada: bool = True,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Faz a requisição e devolve o JSON, traduzindo toda falha em exceção deste módulo."""
    if travada:
        raise ClicksignTravada("Chamada à ClickSign travada neste processo.")
    if not token:
        raise ClicksignRecusou("Token da ClickSign não configurado.", status=None, code="sem_token")
    try:
        response = requests.request(
            metodo,
            url,
            headers=_cabecalhos(token),
            params=params,
            json=json_body,
            timeout=TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        logger.warning("[clicksign] timeout em %s %s", metodo, url)
        raise ClicksignIndisponivel("A ClickSign não respondeu a tempo.") from exc
    except requests.RequestException as exc:
        logger.warning("[clicksign] erro de rede em %s %s: %s", metodo, url, exc)
        raise ClicksignIndisponivel("Falha de rede ao falar com a ClickSign.") from exc

    _respeitar_limite(response)
    if response.status_code == 429 or response.status_code >= 500:
        logger.warning("[clicksign] %s %s devolveu %s", metodo, url, response.status_code)
        raise ClicksignIndisponivel(f"ClickSign indisponível (HTTP {response.status_code}).")
    if response.status_code == 204 or not response.content:
        if response.status_code >= 400:
            raise ClicksignRecusou(
                f"ClickSign recusou (HTTP {response.status_code}).", status=response.status_code
            )
        return {}
    try:
        body = response.json()
    except ValueError as exc:
        raise ClicksignIndisponivel("Resposta ilegível da ClickSign.") from exc
    if response.status_code >= 400:
        erro = (body.get("errors") or [{}])[0] if isinstance(body, dict) else {}
        detalhe = erro.get("detail") or erro.get("title") or f"HTTP {response.status_code}"
        raise ClicksignRecusou(str(detalhe), status=response.status_code, code=erro.get("code"))
    if not isinstance(body, dict):
        raise ClicksignIndisponivel("Formato inesperado na resposta da ClickSign.")
    return body


def _intervalo(inicio: date | None, fim: date | None) -> str | None:
    """Filtro de intervalo da API (``AAAA-MM-DD,AAAA-MM-DD``); sem início, sem filtro."""
    if inicio is None:
        return None
    return f"{inicio.isoformat()},{(fim or date(2999, 12, 31)).isoformat()}"


def listar_envelopes(
    *,
    base: str,
    token: str,
    travada: bool = True,
    modificado_desde: date | None = None,
    modificado_ate: date | None = None,
    criado_desde: date | None = None,
    criado_ate: date | None = None,
    status: str | None = None,
    pagina: int = 1,
) -> dict[str, Any]:
    """Uma página de envelopes (50), com ``data`` e ``meta.record_count``.

    Raises:
        ClicksignIndisponivel / ClicksignTravada / ClicksignRecusou.
    """
    params: dict[str, Any] = {"page[size]": TAMANHO_DA_PAGINA, "page[number]": pagina}
    if (modificado := _intervalo(modificado_desde, modificado_ate)) is not None:
        params["filter[modified]"] = modificado
    if (criado := _intervalo(criado_desde, criado_ate)) is not None:
        params["filter[created]"] = criado
    if status:
        params["filter[status]"] = status
    return _requisitar("GET", f"{base}/envelopes", token=token, travada=travada, params=params)


def signatarios(
    envelope_id: str, *, base: str, token: str, travada: bool = True
) -> list[dict[str, Any]]:
    """Signatários do envelope (nome, telefone, e-mail, ``communicate_events``)."""
    body = _requisitar(
        "GET", f"{base}/envelopes/{envelope_id}/signers", token=token, travada=travada
    )
    return list(body.get("data") or [])


def eventos(
    envelope_id: str, *, base: str, token: str, travada: bool = True
) -> list[dict[str, Any]]:
    """Eventos do envelope (``sign``, ``auto_close``, ``refusal``…), o mais recente primeiro."""
    body = _requisitar(
        "GET", f"{base}/envelopes/{envelope_id}/events", token=token, travada=travada
    )
    return list(body.get("data") or [])


def documentos(
    envelope_id: str, *, base: str, token: str, travada: bool = True
) -> list[dict[str, Any]]:
    """Documentos do envelope (nos fluxos da Manto, sempre um)."""
    body = _requisitar(
        "GET", f"{base}/envelopes/{envelope_id}/documents", token=token, travada=travada
    )
    return list(body.get("data") or [])


def documento(
    envelope_id: str, document_id: str, *, base: str, token: str, travada: bool = True
) -> dict[str, Any]:
    """Um documento com ``links.files`` (``original``, ``signed``, ``ziped``)."""
    body = _requisitar(
        "GET",
        f"{base}/envelopes/{envelope_id}/documents/{document_id}",
        token=token,
        travada=travada,
    )
    return dict(body.get("data") or {})


def baixar(url: str, *, travada: bool = True, limite_bytes: int = 20 * 1024 * 1024) -> bytes:
    """Baixa o arquivo de um link pré-assinado (S3, vale poucos minutos; sem token).

    Raises:
        ClicksignTravada: processo travado.
        ClicksignIndisponivel: falha de rede, status ruim ou arquivo acima do limite.
    """
    if travada:
        raise ClicksignTravada("Download da ClickSign travado neste processo.")
    try:
        response = requests.get(url, timeout=TIMEOUT_SECONDS, stream=True)
    except requests.RequestException as exc:
        raise ClicksignIndisponivel("Falha ao baixar o arquivo da ClickSign.") from exc
    if response.status_code != 200:
        raise ClicksignIndisponivel(f"Download devolveu HTTP {response.status_code}.")
    partes: list[bytes] = []
    total = 0
    for parte in response.iter_content(chunk_size=64 * 1024):
        total += len(parte)
        if total > limite_bytes:
            raise ClicksignIndisponivel("Arquivo da ClickSign acima do limite.")
        partes.append(parte)
    return b"".join(partes)


def listar_webhooks(*, base: str, token: str, travada: bool = True) -> list[dict[str, Any]]:
    """Avisos cadastrados na conta."""
    body = _requisitar("GET", f"{base}/webhooks", token=token, travada=travada)
    return list(body.get("data") or [])


def criar_webhook(
    url_destino: str,
    nomes_de_eventos: tuple[str, ...],
    *,
    base: str,
    token: str,
    travada: bool = True,
) -> dict[str, Any]:
    """Cadastra o aviso da conta; a resposta traz o ``secret`` do HMAC (só nesta hora)."""
    corpo = {
        "data": {
            "type": "webhooks",
            "attributes": {
                "endpoint": url_destino,
                "status": "active",
                "events": list(nomes_de_eventos),
            },
        }
    }
    body = _requisitar("POST", f"{base}/webhooks", token=token, travada=travada, json_body=corpo)
    return dict(body.get("data") or {})


def remover_webhook(webhook_id: str, *, base: str, token: str, travada: bool = True) -> None:
    """Remove um aviso cadastrado."""
    _requisitar("DELETE", f"{base}/webhooks/{webhook_id}", token=token, travada=travada)
