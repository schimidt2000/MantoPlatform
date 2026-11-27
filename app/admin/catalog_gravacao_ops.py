"""Gravação do conferido no catálogo (feature 364).

A conferência de personagens (360) só registra decisões. Este módulo é o passo seguinte: pega cada
item **conferido e ainda na fila** e escreve no catálogo o que foi decidido.

* tema e dupla: um ``CatalogCharacter`` por personagem com decisão "criar" — nome e ficha decididos,
  foto recortada de verdade da galeria (ou nenhuma, quando "criar sem foto");
* avulso com ficha: a ficha passa a ser a do item;
* avulso sem ficha e genérico: nada muda no catálogo, o item só fica marcado como gravado.

Três garantias:

* **só escreve em item que ainda passa na regra da fila** (sem elenco e sem ficha): nunca acrescenta
  um segundo elenco nem troca uma ficha que alguém pôs à mão;
* **idempotente**: ``gravado_em`` no item e ``catalog_character_id`` no personagem proposto;
* **um item é uma transação**: falha no meio desfaz o item e segue para o próximo.

O recorte lê o arquivo do disco, então isto só funciona dentro do processo do backend.
"""

from __future__ import annotations

import io
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from app import db, imaging
from app.admin import catalog_conferencia_ops as conferencia_ops
from app.admin.catalog_character_ops import unique_character_slug
from app.catalogo.importer import _rewrite_public_url
from app.models import (
    CatalogCharacter,
    CatalogConferencia,
    CatalogConferenciaPersonagem,
    CatalogItem,
    CatalogItemImage,
)
from app.storage import caminho_local, save_bytes
from app.utils import audit

logger = logging.getLogger(__name__)

LOTE_PADRAO = 10
LOTE_MAXIMO = 25
QUALIDADE_JPEG = 90
PASTA_DAS_FOTOS = "catalog_photos"
AJUSTES_PATH = Path(__file__).resolve().parent / "dados" / "ajustes_conferencia.json"
# Chave do `pg_advisory_xact_lock`: dois cliques em "Gravar no catálogo" entram em fila.
TRAVA_DA_GRAVACAO = 364


# ── o que falta gravar ──────────────────────────────────────────────────────────────────────────


def _pendentes() -> Any:
    """Conferências conferidas, ainda não gravadas, cujo item continua na fila."""
    return (
        CatalogConferencia.query.join(
            CatalogItem, CatalogItem.id == CatalogConferencia.catalog_item_id
        )
        .filter(
            CatalogConferencia.conferido_em.isnot(None),
            CatalogConferencia.gravado_em.is_(None),
            *conferencia_ops.filtro_da_fila(),
        )
        .order_by(CatalogConferencia.id)
    )


def resumo_da_gravacao() -> dict:
    """Quanto falta gravar e quanto já foi, para a tela mostrar o andamento."""
    pendentes = _pendentes().all()
    com_elenco = [c for c in pendentes if c.tipo in conferencia_ops.TIPOS_COM_ELENCO]
    personagens = sum(
        1
        for c in com_elenco
        for p in c.personagens
        if p.decisao == conferencia_ops.DECISAO_CRIAR and p.catalog_character_id is None
    )
    return {
        "itens_a_gravar": len(pendentes),
        "personagens_a_criar": personagens,
        "fichas_a_ligar": sum(
            1 for c in pendentes if c.tipo == conferencia_ops.TIPO_COM_FICHA_PROPRIA and c.ficha_id
        ),
        "itens_gravados": CatalogConferencia.query.filter(
            CatalogConferencia.gravado_em.isnot(None)
        ).count(),
    }


# ── a foto ──────────────────────────────────────────────────────────────────────────────────────


def _recortar(imagem: CatalogItemImage, recorte: list[int]) -> bytes | None:
    """Recorta a foto da galeria pelos percentuais da conferência. ``None`` se não der.

    Nunca levanta: arquivo que não está no disco, imagem ilegível ou recorte degenerado viram
    personagem sem foto, não lote perdido.
    """
    caminho = caminho_local(imagem.url)
    if not caminho or not Path(caminho).is_file():
        logger.warning("Gravação 364: foto %s não está no disco (%s)", imagem.id, imagem.url)
        return None
    foto = imaging.abrir(Path(caminho).read_bytes())
    if foto is None:
        logger.warning("Gravação 364: foto %s ilegível", imagem.id)
        return None
    largura, altura = foto.size
    x, y, corte_l, corte_a = recorte
    caixa = (
        round(largura * x / 100),
        round(altura * y / 100),
        round(largura * min(100, x + corte_l) / 100),
        round(altura * min(100, y + corte_a) / 100),
    )
    if caixa[2] - caixa[0] < 2 or caixa[3] - caixa[1] < 2:
        return None
    saida = io.BytesIO()
    foto.convert("RGB").crop(caixa).save(saida, format="JPEG", quality=QUALIDADE_JPEG)
    return saida.getvalue()


def _foto_do_personagem(personagem: CatalogConferenciaPersonagem) -> str | None:
    """URL pública da foto recortada, ou ``None`` para criar sem foto."""
    if personagem.sem_foto or not personagem.tem_foto or personagem.imagem is None:
        return None
    dados = _recortar(personagem.imagem, personagem.recorte_list)
    if dados is None:
        return None
    return _rewrite_public_url(save_bytes(dados, PASTA_DAS_FOTOS, ".jpg"))


# ── a gravação ──────────────────────────────────────────────────────────────────────────────────


def _criar_elenco(conferencia: CatalogConferencia, item: CatalogItem) -> int:
    """Cria os personagens "criar" ainda não gravados, na ordem da conferência."""
    criados = 0
    for personagem in conferencia.personagens:
        if personagem.decisao != conferencia_ops.DECISAO_CRIAR or personagem.catalog_character_id:
            continue
        novo = CatalogCharacter(
            catalog_item_id=item.id,
            name=personagem.nome,
            slug=unique_character_slug(item.slug, personagem.nome),
            photo_url=_foto_do_personagem(personagem),
            figurino_sheet_id=personagem.ficha_id,
            position=criados,
        )
        db.session.add(novo)
        db.session.flush()  # o próximo `unique_character_slug` precisa enxergar este endereço
        personagem.catalog_character_id = novo.id
        criados += 1
    return criados


def _gravar_item(conferencia: CatalogConferencia) -> dict:
    """Grava um item dentro de um savepoint: se falhar, o item inteiro volta atrás."""
    item = conferencia.item
    feito = {"personagens": 0, "ficha": 0}
    with db.session.begin_nested():
        if conferencia.tipo in conferencia_ops.TIPOS_COM_ELENCO:
            feito["personagens"] = _criar_elenco(conferencia, item)
        elif conferencia.tipo == conferencia_ops.TIPO_COM_FICHA_PROPRIA and conferencia.ficha_id:
            item.figurino_sheet_id = conferencia.ficha_id
            feito["ficha"] = 1
        conferencia.gravado_em = datetime.utcnow()
        audit(
            "edit",
            "CatalogItem",
            item.id,
            item.name,
            f"Conferência gravada no catálogo: {feito['personagens']} personagem(ns), "
            f"{feito['ficha']} ficha(s) ligada(s)",
        )
    return feito


def gravar_lote(limite: int = LOTE_PADRAO, somente_item_id: int | None = None) -> dict:
    """Grava no catálogo até ``limite`` itens conferidos e devolve o que fez e o que falta.

    Antes do lote aplica os ajustes das observações (idempotente). A trava consultiva enfileira
    chamadas simultâneas; cada item tem commit próprio, então um lote interrompido não perde o
    que já gravou.

    Args:
        limite: Quantos itens tentar nesta chamada (1 a ``LOTE_MAXIMO``).
        somente_item_id: Grava só este item do catálogo (uso do verify e de reprocessamento).

    Returns:
        ``{"itens_gravados", "personagens_criados", "fichas_ligadas", "falhas", "restantes"}``.
    """
    db.session.execute(
        db.text("SELECT pg_advisory_xact_lock(:chave)"), {"chave": TRAVA_DA_GRAVACAO}
    )
    aplicar_ajustes()
    consulta = _pendentes()
    if somente_item_id is not None:
        consulta = consulta.filter(CatalogConferencia.catalog_item_id == somente_item_id)
    lote = consulta.limit(max(1, min(int(limite), LOTE_MAXIMO))).all()
    resumo: dict[str, Any] = {
        "itens_gravados": 0,
        "personagens_criados": 0,
        "fichas_ligadas": 0,
        "falhas": [],
    }
    ids_falhos: list[int] = []
    for conferencia in lote:
        nome, item_id = conferencia.item.name, conferencia.catalog_item_id
        try:
            feito = _gravar_item(conferencia)
        except Exception as exc:  # noqa: BLE001 — um item ruim não pode parar a fila inteira
            logger.warning("Gravação 364: item %s falhou: %s", item_id, exc)
            resumo["falhas"].append({"id": item_id, "nome": nome, "motivo": str(exc)[:200]})
            ids_falhos.append(item_id)
            continue
        resumo["itens_gravados"] += 1
        resumo["personagens_criados"] += feito["personagens"]
        resumo["fichas_ligadas"] += feito["ficha"]
    db.session.commit()
    # O item que falhou continua pendente; tirá-lo da conta evita o laço infinito na tela.
    resumo["restantes"] = (
        max(0, _pendentes().count() - len(ids_falhos)) if somente_item_id is None else 0
    )
    return resumo


# ── os ajustes das observações ──────────────────────────────────────────────────────────────────


def ler_ajustes() -> list[dict]:
    """Os ajustes versionados que saíram da leitura das observações de quem conferiu."""
    if not AJUSTES_PATH.is_file():
        return []
    conteudo = json.loads(AJUSTES_PATH.read_text(encoding="utf-8"))
    return list(conteudo.get("ajustes") or [])


def _imagem_do_item(item_id: int, arquivo: str | None) -> CatalogItemImage | None:
    if not arquivo:
        return None
    return CatalogItemImage.query.filter(
        CatalogItemImage.item_id == item_id, CatalogItemImage.url.like(f"%/{arquivo}")
    ).first()


def _aplicar_um(conferencia: CatalogConferencia, ajuste: dict) -> bool:
    """Aplica um ajuste a um personagem (ou o acrescenta). ``False`` = sem alvo, ignorado."""
    nome = str(ajuste.get("nome") or "").strip()
    personagem = next((p for p in conferencia.personagens if p.nome == nome), None)
    if personagem is None and ajuste.get("criar"):
        ultima = max((p.position for p in conferencia.personagens), default=-1)
        personagem = CatalogConferenciaPersonagem(
            position=ultima + 1,
            origem=conferencia_ops.ORIGEM_MANUAL,
            nome=nome[:200],
            sem_foto_lido=True,
            sem_foto=True,
            decisao=conferencia_ops.DECISAO_CRIAR,
        )
        conferencia.personagens.append(personagem)
        if conferencia.tipo not in conferencia_ops.TIPOS_COM_ELENCO:
            conferencia.tipo = "tema"
    if personagem is None or personagem.catalog_character_id:
        return False
    if ajuste.get("sem_foto"):
        personagem.sem_foto = True
        return True
    if ajuste.get("criar") and not ajuste.get("foto"):
        return True  # acrescentado só com o nome: já está (ou acabou de entrar) no elenco proposto
    imagem, recorte, dims = (
        _imagem_do_item(conferencia.catalog_item_id, ajuste.get("foto")),
        ajuste.get("recorte"),
        ajuste.get("dims"),
    )
    if imagem is None or not (isinstance(recorte, list) and len(recorte) == 4):
        return False
    personagem.imagem_id = imagem.id
    personagem.recorte = json.dumps([int(v) for v in recorte])
    personagem.foto_largura, personagem.foto_altura = (dims or [None, None])[:2]
    personagem.sem_foto = False
    return True


def aplicar_ajustes(ajustes: list[dict] | None = None) -> dict:
    """Leva para a conferência o que as observações pediram: foto, "sem foto" e elenco novo.

    Só mexe em item **ainda não gravado**. Idempotente: reaplicar regrava os mesmos valores, e o
    personagem com ``criar`` não é acrescentado duas vezes (casa pelo nome). Ajuste cujo item,
    personagem ou foto não existe mais é ignorado e contado.

    Returns:
        ``{"aplicados", "ignorados"}``.
    """
    aplicados = ignorados = 0
    for ajuste in ler_ajustes() if ajustes is None else ajustes:
        conferencia = CatalogConferencia.query.filter_by(
            catalog_item_id=ajuste.get("item_id")
        ).first()
        if conferencia is None or conferencia.gravado_em is not None:
            ignorados += 1
        elif _aplicar_um(conferencia, ajuste):
            aplicados += 1
        else:
            ignorados += 1
    db.session.flush()
    return {"aplicados": aplicados, "ignorados": ignorados}
