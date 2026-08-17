"""Núcleo de negócio de CRUD de musicais do EducaManto (feature 235).

Substitui o antigo ``package_ops.py`` (pacotes por nível). Funções puras (sem
``flask.request``), recebendo dicts já parseados pela camada de API — fonte única
(Princípio I). A validação de negócio nova: ``num_ensaios`` tem mínimo 2.
"""

from __future__ import annotations

from app import db
from app.models import EducaMantoMusical, EducaMantoMusicalItem

MIN_ENSAIOS = 2

# Campos de custo dos blocos de responsabilidade + ensaios/alimentação.
_CAMPOS_CUSTO = [
    "custo_alimentacao_1s", "custo_alimentacao_2s",
    "custo_catering_ensaio_pp", "custo_ajuda_ensaio_pp",
]
_CAMPOS_ENSEMBLE = {
    "ensemble_1s": 350, "ensemble_2s": 600,
    "ensemble_1s_days": 300, "ensemble_2s_days": 550,
}


class MusicalValidationError(Exception):
    """Erro de validação de negócio — nunca vazamento de exceção do banco."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


def parse_items(raw_items: list[dict]) -> list[dict]:
    """Normaliza a lista de itens sempre inclusos, descartando linhas sem nome."""
    items: list[dict] = []
    for i, raw in enumerate(raw_items or []):
        name = str(raw.get("name") or "").strip()
        if not name:
            continue
        items.append({
            "name": name,
            "qty": int(raw.get("qty") or 1),
            "cost_1s": float(raw.get("cost_1s") or 0),
            "cost_2s": float(raw.get("cost_2s") or 0),
            "cost_1s_days": float(raw.get("cost_1s_days") or 0),
            "cost_2s_days": float(raw.get("cost_2s_days") or 0),
            "ensemble_add": int(raw.get("ensemble_add") or 0),
            "sort_order": i,
        })
    return items


def _num(data: dict, key: str, default: float) -> float:
    """Lê um número preservando zero explícito — `value or default` trocaria 0 pelo default."""
    value = data.get(key)
    return float(value) if value is not None else float(default)


def _musical_fields(data: dict) -> dict:
    """Extrai e valida os campos escalares de um musical a partir do dict de entrada."""
    name = str(data.get("name") or "").strip()
    if not name:
        raise MusicalValidationError("name", "Informe o nome do musical.")

    num_ensaios = int(data.get("num_ensaios") or MIN_ENSAIOS)
    if num_ensaios < MIN_ENSAIOS:
        raise MusicalValidationError(
            "num_ensaios", f"O mínimo são {MIN_ENSAIOS} ensaios."
        )

    fields: dict = {
        "name": name,
        "num_personagens": max(int(data.get("num_personagens") or 0), 0),
        "num_producao": max(int(data.get("num_producao") or 0), 0),
        "num_ensaios": num_ensaios,
        "margin_1s": _num(data, "margin_1s", 0),
        "margin_2s": _num(data, "margin_2s", 0),
        "margin_1s_days": _num(data, "margin_1s_days", 0),
        "margin_2s_days": _num(data, "margin_2s_days", 0),
        "discount_days": int(data.get("discount_days") or 0),
        "discount_pct": _num(data, "discount_pct", 0),
    }
    for campo, default in _CAMPOS_ENSEMBLE.items():
        fields[campo] = _num(data, campo, default)
    for campo in _CAMPOS_CUSTO:
        valor = _num(data, campo, 0)
        if valor < 0:
            raise MusicalValidationError(campo, "Custos não podem ser negativos.")
        fields[campo] = valor
    return fields


def _nome_em_uso(name: str, ignorar_id: int | None = None) -> bool:
    q = EducaMantoMusical.query.filter(EducaMantoMusical.name == name)
    if ignorar_id is not None:
        q = q.filter(EducaMantoMusical.id != ignorar_id)
    return db.session.query(q.exists()).scalar()


def create_musical(data: dict) -> EducaMantoMusical:
    """Cria um musical com seus itens sempre inclusos.

    Raises:
        MusicalValidationError: nome ausente/duplicado, ensaios < 2 ou custo negativo.
    """
    fields = _musical_fields(data)
    if _nome_em_uso(fields["name"]):
        raise MusicalValidationError("name", "Já existe um musical com esse nome.")
    musical = EducaMantoMusical(**fields)
    db.session.add(musical)
    db.session.flush()
    for item_data in parse_items(data.get("items") or []):
        db.session.add(EducaMantoMusicalItem(musical_id=musical.id, **item_data))
    db.session.commit()
    return musical


def update_musical(musical: EducaMantoMusical, data: dict) -> EducaMantoMusical:
    """Atualiza um musical, substituindo a lista de itens inteira.

    Raises:
        MusicalValidationError: nome ausente/duplicado, ensaios < 2 ou custo negativo.
    """
    fields = _musical_fields(data)
    if _nome_em_uso(fields["name"], ignorar_id=musical.id):
        raise MusicalValidationError("name", "Já existe um musical com esse nome.")
    for field, value in fields.items():
        setattr(musical, field, value)
    for item in list(musical.items):
        db.session.delete(item)
    db.session.flush()
    for item_data in parse_items(data.get("items") or []):
        db.session.add(EducaMantoMusicalItem(musical_id=musical.id, **item_data))
    db.session.commit()
    return musical


def duplicate_musical(original: EducaMantoMusical) -> EducaMantoMusical:
    """Duplica um musical (parâmetros + itens), prefixando o nome com "Cópia de "."""
    dados = original.to_dict()
    dados.pop("id", None)
    items = dados.pop("items", [])
    dados["name"] = f"Cópia de {original.name}"
    copia = EducaMantoMusical(**dados)
    db.session.add(copia)
    db.session.flush()
    for i, item in enumerate(items):
        item.pop("id", None)
        db.session.add(EducaMantoMusicalItem(musical_id=copia.id, sort_order=i, **item))
    db.session.commit()
    return copia


def delete_musical(musical: EducaMantoMusical) -> None:
    """Exclui um musical e seus itens (cascade)."""
    db.session.delete(musical)
    db.session.commit()
