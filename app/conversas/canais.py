"""O que o envio do Instagram Direct tem de diferente do WhatsApp (feature 330, research R7/R10).

``envio_ops`` continua o orquestrador único (chave de envio, mensagem gravada antes da chamada,
cópia local, atribuição e espera da 328, falha com motivo). Quando a conversa é do Instagram, ele
pergunta aqui: as pré-condições e a janela (24 h normal; até 7 dias com a marca HUMAN_AGENT), o limite
de texto em bytes, os tipos e tetos de arquivo, a chamada à Meta e o motivo legível da recusa.
"""

from __future__ import annotations

from typing import Any

from app.conversas import constantes as K
from app.conversas.configuracao import cfg_instagram
from app.conversas.leitura_ops import estado_da_janela
from app.conversas.recusa import Recusa, campo
from app.integracoes import instagram_client as ic
from app.integracoes import whatsapp_client as wc
from app.models import Conversa, ConversaMidia

MARCA_HUMANA = {"messaging_type": "MESSAGE_TAG", "tag": "HUMAN_AGENT"}


def e_instagram(conversa: Conversa) -> bool:
    return conversa.canal == K.CANAL_INSTAGRAM


def pre_condicoes(conversa: Conversa, *, exige_janela: bool) -> dict[str, str]:
    """Canal ligado, trava e janela. Devolve os campos extras do envio (a marca humana, se for).

    Raises:
        Recusa: 503 ``nao_configurado``, 409 ``envio_travado`` ou ``janela_fechada``.
    """
    cfg = cfg_instagram()
    if not cfg.ligado:
        raise Recusa("nao_configurado", K.TEXTO_IG_NAO_CONFIGURADO, 503)
    if cfg.travado:
        raise Recusa("envio_travado", K.TEXTO_IG_TRAVADO, 409)
    janela = estado_da_janela(conversa)
    if exige_janela and janela == K.JANELA_ESTADO_FECHADA:
        raise Recusa("janela_fechada", K.TEXTO_IG_JANELA_FECHADA, 409)
    return dict(MARCA_HUMANA) if janela == K.JANELA_ESTADO_HUMANA else {}


def validar_texto(texto: str) -> None:
    """O limite do Instagram é de 1.000 BYTES em UTF-8."""
    if len(texto.encode("utf-8")) > K.TEXTO_MAXIMO_IG_BYTES:
        raise campo("texto", K.TEXTO_IG_TEXTO_LONGO)


def tipo_do_arquivo(mime: str, tamanho: int) -> str:
    """O tipo da casa para o MIME aceito pelo Instagram, ou a recusa apontando o arquivo."""
    tipo = K.MIME_DE_ENVIO_IG.get(mime)
    if tipo is None:
        raise campo("arquivo", K.TEXTO_IG_TIPO_NAO_ACEITO)
    if tamanho > K.TETO_DE_ENVIO_IG[tipo]:
        limite = K.TETO_DE_ENVIO_IG[tipo] // (1024 * 1024)
        raise campo("arquivo", f"Arquivo acima de {limite} MB para este tipo.")
    if tamanho == 0:
        raise campo("arquivo", "O arquivo está vazio.")
    return tipo


def enviar_texto(conversa: Conversa, texto: str, extras: dict[str, str]) -> str:
    """Manda o texto e devolve o ``mid`` que a Meta deu."""
    corpo: dict[str, Any] = {
        "recipient": {"id": conversa.contato_id},
        "message": {"text": texto},
        **extras,
    }
    return ic.enviar(cfg_instagram().conexao, corpo)["id"]


def enviar_arquivo(
    conversa: Conversa, midia: ConversaMidia, dados: bytes, tipo: str, extras: dict[str, str]
) -> str:
    """Sobe e manda o arquivo numa chamada só (upload direto). Devolve o ``mid``."""
    resposta = ic.enviar_arquivo(
        cfg_instagram().conexao,
        {"id": conversa.contato_id},
        K.CHAVE_DO_ANEXO_IG[tipo],
        dados,
        midia.mime,
        midia.nome_original,
        extras,
    )
    return resposta["id"]


def motivo(exc: wc.WhatsappErro, extras: dict[str, str]) -> str:
    """O motivo legível da recusa: roteamento (outro app no controle), marca humana não liberada ou
    o motivo comum da 325 pelo código."""
    if not isinstance(exc, wc.WhatsappRecusou):
        return K.motivo_do_erro(None)
    if exc.subcode in K.SUBCODIGOS_DE_ROTEAMENTO:
        return K.MOTIVO_IG_ROTEAMENTO
    if extras.get("tag") and exc.code in K.CODIGOS_DE_PERMISSAO:
        return K.MOTIVO_IG_MARCA_HUMANA
    return K.motivo_do_erro(exc.code)
