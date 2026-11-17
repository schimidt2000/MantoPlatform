"""Cliente HTTP do Instagram Direct pela Página do Facebook (feature 330) — sem Flask.

A mensageria do Instagram mora na mesma Graph API do WhatsApp (``graph.facebook.com``, versão fixa),
então este cliente usa o MESMO transporte (``whatsapp_client.requisitar``): timeouts, a tradução do
erro da Meta (``WhatsappRecusou`` com ``code``/``subcode``) e a trava do ambiente são uma fonte só.

Envio: ``POST /{page_id}/messages`` com o IGSID da cliente; arquivo vai no mesmo endpoint, com upload
direto (``filedata``). Perfil: ``GET /{igsid}?fields=name,username``. A codificação exata do upload e
os campos do perfil ficam a confirmar na conta de teste (quickstart §3); a montagem mora só aqui.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.integracoes import whatsapp_client as wc


@dataclass(frozen=True)
class ConexaoInstagram:
    """Endereço, versão, token da Página, ids da Página e da conta, e a trava do ambiente."""

    base: str
    versao: str
    token: str
    page_id: str
    account_id: str
    travada: bool = True

    def url(self, caminho: str) -> str:
        """URL completa da Graph API para ``caminho`` (sem barra inicial)."""
        return f"{self.base}/{self.versao}/{caminho}"

    def transporte(self) -> wc.ConexaoMeta:
        """A conexão no formato do transporte comum (token e trava são o que ele usa)."""
        return wc.ConexaoMeta(
            base=self.base,
            versao=self.versao,
            token=self.token,
            phone_number_id="",
            travada=self.travada,
        )


def _id_da_resposta(resposta: dict[str, Any]) -> str:
    mid = resposta.get("message_id")
    if not mid:
        raise wc.WhatsappIndisponivel("A Meta não devolveu o id da mensagem do Instagram.")
    return str(mid)


def enviar(conexao: ConexaoInstagram, corpo: dict[str, Any]) -> dict[str, str]:
    """Envia texto (``POST /{page_id}/messages``). ``corpo`` traz ``recipient`` e ``message``.

    Raises:
        WhatsappRecusou / WhatsappIndisponivel / WhatsappTravado (o transporte é o comum).
    """
    resposta = wc.requisitar(
        conexao.transporte(), "POST", conexao.url(f"{conexao.page_id}/messages"), json_body=corpo
    )
    return {"id": _id_da_resposta(resposta)}


def enviar_arquivo(
    conexao: ConexaoInstagram,
    destino: dict[str, str],
    tipo: str,
    dados: bytes,
    mime: str,
    nome: str,
    extras: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Sobe e envia o arquivo numa chamada só (upload direto no ``/messages``).

    ``tipo`` é a chave do anexo da Meta (``image``, ``video``, ``audio``, ``file``); ``extras`` leva a
    marca de resposta humana quando a janela é a de 7 dias.
    """
    mensagem = {"attachment": {"type": tipo, "payload": {"is_reusable": False}}}
    campos = {"recipient": json.dumps(destino), "message": json.dumps(mensagem)}
    for chave, valor in (extras or {}).items():
        campos[chave] = valor
    resposta = wc.requisitar(
        conexao.transporte(),
        "POST",
        conexao.url(f"{conexao.page_id}/messages"),
        data=campos,
        files={"filedata": (nome, dados, mime)},
    )
    return {"id": _id_da_resposta(resposta)}


def perfil(conexao: ConexaoInstagram, igsid: str) -> dict[str, str | None]:
    """Nome e @usuário de quem escreveu (``GET /{igsid}?fields=name,username``)."""
    resposta = wc.requisitar(
        conexao.transporte(), "GET", conexao.url(igsid), params={"fields": "name,username"}
    )
    nome = (resposta.get("name") or "").strip() or None
    usuario = (resposta.get("username") or "").strip().lstrip("@") or None
    return {"nome": nome, "usuario": usuario}
