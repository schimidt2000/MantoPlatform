"""Núcleo de negócio de CRUD de pacote EducaManto (feature 175).

Funções puras (sem `flask.request`/`render_template`/`flash`), extraídas de
`app/educamanto/routes.py` — reusadas tanto pela view Jinja legada quanto pelos endpoints de API
(`app/api/educamanto_write.py`), fonte única (Princípio I). Recebem `dict` já parseado
(a view Jinja parseia `request.form`; a API parseia o JSON do corpo).
"""

from __future__ import annotations

from app import db
from app.models import EducaMantoItem, EducaMantoPackage


class PackageValidationError(Exception):
    """Erro de validação de negócio (nome do pacote/item) — nunca vazamento de exceção do banco."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


def parse_items(raw_items: list[dict]) -> list[dict]:
    """Normaliza a lista de itens de um pacote, descartando linhas sem nome.

    Args:
        raw_items: Lista de dicts com as chaves de `EducaMantoItem` (nome, quantidade, custos).

    Returns:
        Lista limpa, pronta para virar `EducaMantoItem`, com `sort_order` sequencial.
    """
    items: list[dict] = []
    for i, raw in enumerate(raw_items or []):
        name = str(raw.get("name") or "").strip()
        if not name:
            continue
        items.append(
            {
                "name": name,
                "qty": int(raw.get("qty") or 1),
                "cost_1s": float(raw.get("cost_1s") or 0),
                "cost_2s": float(raw.get("cost_2s") or 0),
                "cost_1s_days": float(raw.get("cost_1s_days") or 0),
                "cost_2s_days": float(raw.get("cost_2s_days") or 0),
                "ensemble_add": int(raw.get("ensemble_add") or 0),
                "sort_order": i,
            }
        )
    return items


def _num(data: dict, key: str, default: float) -> float:
    """Lê um número do dict preservando zero explícito — `value or default` trocaria 0 pelo default."""
    value = data.get(key)
    return float(value) if value is not None else float(default)


def _package_fields(data: dict) -> dict:
    """Extrai e valida os campos escalares de um pacote a partir do dict de entrada."""
    name = str(data.get("name") or "").strip()
    if not name:
        raise PackageValidationError("name", "Informe o nome do pacote.")
    return {
        "name": name,
        "margin_1s": _num(data, "margin_1s", 0),
        "margin_2s": _num(data, "margin_2s", 0),
        "margin_1s_days": _num(data, "margin_1s_days", 0),
        "margin_2s_days": _num(data, "margin_2s_days", 0),
        "discount_days": int(data.get("discount_days") or 0),
        "discount_pct": _num(data, "discount_pct", 0),
        "commission_rate": _num(data, "commission_rate", 0),
        "ensemble_1s": _num(data, "ensemble_1s", 350),
        "ensemble_2s": _num(data, "ensemble_2s", 600),
        "ensemble_1s_days": _num(data, "ensemble_1s_days", 300),
        "ensemble_2s_days": _num(data, "ensemble_2s_days", 550),
    }


def create_package(data: dict) -> EducaMantoPackage:
    """Cria um pacote educacional com seus itens.

    Args:
        data: Campos do pacote + `items` (lista de dicts), já parseados.

    Returns:
        O pacote criado, persistido.

    Raises:
        PackageValidationError: Nome do pacote ausente.
    """
    pkg = EducaMantoPackage(**_package_fields(data))
    db.session.add(pkg)
    db.session.flush()
    for item_data in parse_items(data.get("items") or []):
        db.session.add(EducaMantoItem(package_id=pkg.id, **item_data))
    db.session.commit()
    return pkg


def update_package(pkg: EducaMantoPackage, data: dict) -> EducaMantoPackage:
    """Atualiza um pacote existente, substituindo a lista de itens inteira.

    Args:
        pkg: Pacote já carregado do banco.
        data: Campos do pacote + `items` (lista de dicts), já parseados.

    Returns:
        O mesmo pacote, atualizado.

    Raises:
        PackageValidationError: Nome do pacote ausente.
    """
    for field, value in _package_fields(data).items():
        setattr(pkg, field, value)
    for item in list(pkg.items):
        db.session.delete(item)
    db.session.flush()
    for item_data in parse_items(data.get("items") or []):
        db.session.add(EducaMantoItem(package_id=pkg.id, **item_data))
    db.session.commit()
    return pkg


def duplicate_package(original: EducaMantoPackage) -> EducaMantoPackage:
    """Duplica um pacote (parâmetros + itens), prefixando o nome com "Cópia de "."""
    copy = EducaMantoPackage(
        name=f"Cópia de {original.name}",
        margin_1s=original.margin_1s,
        margin_2s=original.margin_2s,
        margin_1s_days=original.margin_1s_days,
        margin_2s_days=original.margin_2s_days,
        discount_days=original.discount_days,
        discount_pct=original.discount_pct,
        commission_rate=original.commission_rate,
        ensemble_1s=original.ensemble_1s,
        ensemble_2s=original.ensemble_2s,
        ensemble_1s_days=original.ensemble_1s_days,
        ensemble_2s_days=original.ensemble_2s_days,
    )
    db.session.add(copy)
    db.session.flush()
    for item in original.items:
        db.session.add(
            EducaMantoItem(
                package_id=copy.id,
                name=item.name,
                qty=item.qty,
                cost_1s=item.cost_1s,
                cost_2s=item.cost_2s,
                cost_1s_days=item.cost_1s_days,
                cost_2s_days=item.cost_2s_days,
                ensemble_add=item.ensemble_add,
                sort_order=item.sort_order,
            )
        )
    db.session.commit()
    return copy


def delete_package(pkg: EducaMantoPackage) -> None:
    """Exclui um pacote e seus itens (cascade)."""
    db.session.delete(pkg)
    db.session.commit()
