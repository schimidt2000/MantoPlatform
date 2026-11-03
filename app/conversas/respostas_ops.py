"""Respostas rápidas da equipe de Conversas (feature 328, FR-010).

Uma lista só, de todo o Comercial (decisão do dono, 03/11): qualquer pessoa com acesso às Conversas
cria, edita e exclui. Escolher uma na tela **insere** o texto no campo, sem enviar; o ``{nome}`` é
trocado lá, pelo primeiro nome do contato — aqui fica o texto cru.

A unicidade (título sem distinguir caixa e atalho) é conferida antes de gravar, para a recusa sair no
campo certo; o índice do banco segura a corrida entre duas gravações (``IntegrityError`` vira a mesma
recusa). Puro: sem ``flask.request`` nem ``current_user``.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app import db
from app.conversas import constantes as K
from app.conversas.recusa import Recusa
from app.conversas.relogio import agora_utc
from app.models import RespostaRapida

_CAMPOS = ("titulo", "atalho", "texto")


def listar() -> list[RespostaRapida]:
    """A lista da equipe, em ordem alfabética do título."""
    return RespostaRapida.query.order_by(func.lower(RespostaRapida.titulo)).all()


def serializar(resposta: RespostaRapida) -> dict[str, Any]:
    return {
        "id": resposta.id,
        "titulo": resposta.titulo,
        "atalho": resposta.atalho,
        "texto": resposta.texto,
    }


def _texto_de(valor: Any) -> str:
    return valor.strip() if isinstance(valor, str) else ""


def _repetido(coluna: Any, valor: str, ignorar_id: int | None) -> bool:
    consulta = RespostaRapida.query.filter(coluna == valor)
    if ignorar_id is not None:
        consulta = consulta.filter(RespostaRapida.id != ignorar_id)
    return db.session.query(consulta.exists()).scalar()


def _titulo(valor: Any, ignorar_id: int | None) -> tuple[str, str | None]:
    titulo = _texto_de(valor)
    if not titulo:
        return titulo, K.TEXTO_TITULO_VAZIO
    if len(titulo) > K.RESPOSTA_TITULO_MAXIMO:
        return titulo, K.TEXTO_TITULO_LONGO
    if _repetido(func.lower(RespostaRapida.titulo), titulo.lower(), ignorar_id):
        return titulo, K.TEXTO_TITULO_REPETIDO
    return titulo, None


def _atalho(valor: Any, ignorar_id: int | None) -> tuple[str | None, str | None]:
    """Opcional; o "/" do começo sai (é como se digita na caixa) e fica em minúsculas."""
    atalho = _texto_de(valor).lstrip("/").lower() or None
    if atalho is None:
        return None, None
    if any(c.isspace() for c in atalho):
        return atalho, K.TEXTO_ATALHO_COM_ESPACO
    if len(atalho) > K.RESPOSTA_ATALHO_MAXIMO:
        return atalho, K.TEXTO_ATALHO_LONGO
    if _repetido(RespostaRapida.atalho, atalho, ignorar_id):
        return atalho, K.TEXTO_ATALHO_REPETIDO
    return atalho, None


def _texto(valor: Any, _ignorar_id: int | None) -> tuple[str, str | None]:
    texto = _texto_de(valor)
    if not texto:
        return texto, K.TEXTO_RESPOSTA_VAZIA
    if len(texto) > K.RESPOSTA_TEXTO_MAXIMO:
        return texto, K.TEXTO_RESPOSTA_LONGA
    return texto, None


_VALIDADORES = {"titulo": _titulo, "atalho": _atalho, "texto": _texto}


def _validar(dados: dict[str, Any], campos: tuple[str, ...], ignorar_id: int | None) -> dict:
    """Os valores limpos dos ``campos``, ou a recusa 422 com todos os campos errados de uma vez."""
    limpos: dict[str, Any] = {}
    erros: dict[str, str] = {}
    for nome in campos:
        limpos[nome], erro = _VALIDADORES[nome](dados.get(nome), ignorar_id)
        if erro:
            erros[nome] = erro
    if erros:
        raise Recusa("invalido", next(iter(erros.values())), 422, erros)
    return limpos


def _gravar(resposta: RespostaRapida) -> RespostaRapida:
    """Comita; a corrida contra o índice único vira a recusa no campo, como a conferência prévia."""
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        nome = "atalho" if "atalho" in str(exc.orig) else "titulo"
        texto = K.TEXTO_ATALHO_REPETIDO if nome == "atalho" else K.TEXTO_TITULO_REPETIDO
        raise Recusa("invalido", texto, 422, {nome: texto}) from exc
    return resposta


def criar(dados: dict[str, Any], autor_id: int) -> RespostaRapida:
    """Nova resposta rápida da equipe. Comita."""
    limpos = _validar(dados, _CAMPOS, None)
    agora = agora_utc()
    resposta = RespostaRapida(
        **limpos,
        criado_por_id=autor_id,
        alterado_por_id=autor_id,
        created_at=agora,
        updated_at=agora,
    )
    db.session.add(resposta)
    return _gravar(resposta)


def _ou_404(resposta_id: int) -> RespostaRapida:
    resposta = db.session.get(RespostaRapida, resposta_id)
    if resposta is None:
        raise Recusa("nao_encontrada", K.TEXTO_RESPOSTA_NAO_ENCONTRADA, 404)
    return resposta


def alterar(resposta_id: int, dados: dict[str, Any], autor_id: int) -> RespostaRapida:
    """Altera só os campos enviados (PATCH). Comita."""
    resposta = _ou_404(resposta_id)
    campos = tuple(nome for nome in _CAMPOS if nome in dados)
    for nome, valor in _validar(dados, campos, resposta.id).items():
        setattr(resposta, nome, valor)
    resposta.alterado_por_id = autor_id
    resposta.updated_at = agora_utc()
    return _gravar(resposta)


def excluir(resposta_id: int) -> None:
    """Apaga de verdade: é configuração, não histórico (a tela pede confirmação). Comita."""
    db.session.delete(_ou_404(resposta_id))
    db.session.commit()
