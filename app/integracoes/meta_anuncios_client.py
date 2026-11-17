"""A campanha de um anúncio da Meta (feature 334): ``GET /{ad_id}?fields=name,campaign{id,name}``.

Feature 348: a mesma chamada pede também o conjunto de anúncios (``adset{id,name}``) — sem custo de cota novo.

O aviso da mensagem que veio de um anúncio traz só o id e o título do anúncio; o nome da campanha, que o
Desempenho casa com o export de campanhas, sai desta consulta. Usa o transporte da Graph API do WhatsApp
(``whatsapp_client.requisitar``): a mesma versão, o mesmo tratamento de erro e a mesma trava do ambiente.
O token precisa de ``ads_read`` sobre a conta de anúncios da Manto.
"""

from __future__ import annotations

from typing import Any

from app.integracoes import whatsapp_client as wc


def _bloco(resposta: dict[str, Any], chave: str) -> dict[str, Any]:
    valor = resposta.get(chave)
    return valor if isinstance(valor, dict) else {}


def consultar_anuncio(conexao: wc.ConexaoMeta, anuncio_id: str) -> dict[str, Any]:
    """O nome do anúncio, a campanha e o conjunto (id e nome de cada).

    Raises:
        whatsapp_client.WhatsappRecusou: a Meta recusou (permissão, anúncio inexistente).
        whatsapp_client.WhatsappIndisponivel: rede, tempo ou trava do ambiente.
    """
    resposta = wc.requisitar(
        conexao,
        "GET",
        conexao.url(anuncio_id),
        params={"fields": "name,campaign{id,name},adset{id,name}"},
    )
    campanha, conjunto = _bloco(resposta, "campaign"), _bloco(resposta, "adset")
    return {
        "nome": (resposta.get("name") or "").strip() or None,
        "campanha_id": str(campanha.get("id") or "").strip() or None,
        "campanha_nome": (campanha.get("name") or "").strip() or None,
        "conjunto_id": str(conjunto.get("id") or "").strip() or None,
        "conjunto_nome": (conjunto.get("name") or "").strip() or None,
    }
