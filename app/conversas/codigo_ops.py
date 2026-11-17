"""O código do site (feature 348): o clique de campanha que chega à conversa pela mensagem pronta.

O clique no Google sai do site para o ``wa.me`` e o ``gclid`` fica para trás (pesquisa "Máquina de vendas",
6.3). O padrão que funciona:

1. o site guarda os marcadores do clique e pede aqui um código curto (``criar_codigo``);
2. o botão de WhatsApp põe "Código do site: #A7K2Q" na mensagem pronta (a lista de desejos no navegador;
   o formulário público aqui, ``anexar_a_mensagem``);
3. quando a mensagem chega, o aviso lê o código (``ler_na_mensagem``) e liga o clique à conversa: o código
   vira um contato de origem ``site`` da conversa, como o anúncio da 334.

Cada código liga uma conversa só (``UPDATE … WHERE conversa_id IS NULL``: o primeiro uso vence) e vale 90 dias.
Nada aqui chama serviço de fora.
"""

from __future__ import annotations

import logging
import re
import secrets
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app import db
from app.conversas import anuncio_ops
from app.conversas import constantes as K
from app.conversas.relogio import agora_utc
from app.models import Conversa, OrigemCodigo

logger = logging.getLogger(__name__)

_REGEX = re.compile(K.REGEX_DO_CODIGO)
# Tamanho de cada coluna de marcador (o resto da URL é cortado, nunca recusado).
_TAMANHOS = {
    **dict.fromkeys(K.MARCADORES_DO_CLIQUE, 512),
    **dict.fromkeys(K.MARCADORES_UTM, 200),
}


class SemMarcador(ValueError):
    """O pedido de código não trouxe nenhum marcador de campanha."""


def _texto(valor: Any, limite: int) -> str | None:
    """Só texto entra: número, lista ou objeto vindo do navegador é ignorado."""
    if not isinstance(valor, str):
        return None
    return valor.strip()[:limite] or None


def _pagina(valor: Any) -> str | None:
    """O caminho da página de entrada, sem a query (que repete os marcadores) nem o fragmento."""
    caminho = _texto(valor, 2000)
    if not caminho:
        return None
    return caminho.split("#", 1)[0].split("?", 1)[0][:500] or None


def _novo_codigo() -> str:
    return "".join(secrets.choice(K.ALFABETO_DO_CODIGO) for _ in range(K.TAMANHO_DO_CODIGO))


def criar_codigo(marcadores: dict[str, Any]) -> OrigemCodigo:
    """Grava o clique e devolve o registro com o código novo. Comita.

    Args:
        marcadores: o que o site leu da URL (``gclid``, ``gbraid``, ``wbraid``, ``fbclid``, ``utm_*``,
            ``gad_campaignid``, ``utm_id``), mais ``pagina`` e ``procedencia``. Chave desconhecida e valor
            que não é texto são ignorados.

    Raises:
        SemMarcador: nenhum marcador de clique nem de campanha.
    """
    valores = {nome: _texto(marcadores.get(nome), limite) for nome, limite in _TAMANHOS.items()}
    campanha_id = next(
        (v for nome in K.MARCADORES_DA_CAMPANHA if (v := _texto(marcadores.get(nome), 80))), None
    )
    if not any(valores.values()) and not campanha_id:
        raise SemMarcador(K.TEXTO_SEM_MARCADOR)
    for _ in range(K.TENTATIVAS_DO_CODIGO):
        registro = OrigemCodigo(
            codigo=_novo_codigo(),
            campanha_id=campanha_id,
            pagina=_pagina(marcadores.get("pagina")),
            procedencia=_texto(marcadores.get("procedencia"), 200),
            created_at=agora_utc(),
            **valores,
        )
        db.session.add(registro)
        try:
            db.session.commit()
            return registro
        except IntegrityError:
            # Colisão do código (UNIQUE): raríssima com 31⁵ combinações; sorteia de novo.
            db.session.rollback()
    raise RuntimeError("não foi possível gerar um código livre")


def codigo_valido(texto: Any) -> OrigemCodigo | None:
    """O código existente e criado há no máximo 90 dias (esteja ligado a uma conversa ou não)."""
    codigo = _texto(texto, 16)
    if not codigo:
        return None
    registro = OrigemCodigo.query.filter_by(codigo=codigo.lstrip("#").upper()).first()
    if registro is None or registro.created_at < agora_utc() - K.VALIDADE_DO_CODIGO:
        return None
    return registro


def linha_do_codigo(codigo: str) -> str:
    """A linha que vai no fim da mensagem pronta."""
    return K.LINHA_DO_CODIGO.format(codigo=codigo)


def anexar_a_mensagem(mensagem: str, codigo: Any, form_response_id: int | None = None) -> str:
    """A mensagem pronta do formulário com a linha do código, se ele vale (FR-006, FR-007). Comita.

    Código ausente, inexistente ou vencido devolve a mensagem como veio. A resposta do formulário fica
    ligada ao código só se ele ainda não tinha uma.
    """
    registro = codigo_valido(codigo)
    if registro is None:
        return mensagem
    if form_response_id is not None:
        db.session.execute(
            text(
                "UPDATE origem_codigos SET form_response_id = :r "
                "WHERE id = :i AND form_response_id IS NULL"
            ),
            {"r": form_response_id, "i": registro.id},
        )
        db.session.commit()
    return f"{mensagem}\n\n{linha_do_codigo(registro.codigo)}"


def _ligar(codigo: str, conversa_id: int, momento: datetime) -> int | None:
    """UPDATE condicional: só o código vivo e livre liga (o primeiro uso vence). Devolve o id."""
    linha = db.session.execute(
        text(
            "UPDATE origem_codigos SET conversa_id = :c, usado_em = :m "
            "WHERE codigo = :k AND conversa_id IS NULL AND created_at >= :desde RETURNING id"
        ),
        {"c": conversa_id, "m": momento, "k": codigo, "desde": agora_utc() - K.VALIDADE_DO_CODIGO},
    ).first()
    return linha[0] if linha else None


def _titulo(registro: OrigemCodigo) -> str:
    """O que a tela mostra do contato: a campanha; sem ela, "Google" (clique com id) ou "Site"."""
    if registro.utm_campaign:
        return registro.utm_campaign
    return "Google" if registro.gclid or registro.gbraid or registro.wbraid else K.ORIGEM_DO_SITE


def ler_na_mensagem(conversa: Conversa, texto: str | None, momento: datetime) -> list[int]:
    """Os códigos da mensagem recebida que ligaram a conversa (FR-009, FR-010). Não comita.

    Cada código ligado vira um contato de origem ``site`` da conversa (chave ``site:{codigo}``) e, na
    ficha sem origem, a origem "Site" (``anuncio_ops.aplicar_na_ficha``).
    """
    ligados: list[int] = []
    for achado in dict.fromkeys(m.upper() for m in _REGEX.findall(texto or "")):
        codigo_id = _ligar(achado, conversa.id, momento)
        if codigo_id is None:
            continue
        registro = db.session.get(OrigemCodigo, codigo_id)
        anuncio_ops.registrar_contato(
            conversa,
            chave=f"site:{achado}",
            tipo=K.CONTATO_SITE,
            anuncio_id=None,
            titulo=_titulo(registro),
            link=registro.pagina,
            momento=momento,
            codigo_id=codigo_id,
        )
        logger.info("[origem] código %s ligou a conversa %s", achado, conversa.id)
        ligados.append(codigo_id)
    return ligados
