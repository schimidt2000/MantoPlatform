"""Núcleo de negócio de geração/consulta de orçamento EducaManto (feature 175).

Funções puras (sem `flask.request`/`render_template`) extraídas de
`app/educamanto/routes.py` — reusadas pela view Jinja legada e pelos endpoints de API
(`app/api/educamanto_write.py`, `app/api/educamanto_read.py`), fonte única (Princípio I).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy import or_

from app import db
from app.models import EducaMantoQuote, User


class QuoteValidationError(Exception):
    """Erro de validação de negócio na geração de orçamento (nunca vazamento de exceção de banco)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def build_snapshot(data: dict) -> tuple[dict, str]:
    """Monta o snapshot congelado do orçamento a partir do JSON do cliente.

    Args:
        data: Corpo já parseado (pacotes selecionados, dias, ensemble, transporte, cliente).

    Returns:
        Tupla `(snapshot, label)` — `label` é a lista de nomes de pacotes, usada no histórico.
    """
    clean_pkgs = []
    for p in data.get("packages") or []:
        clean_pkgs.append(
            {
                "id": p.get("id"),
                "name": str(p.get("name") or "Pacote")[:200],
                "sem_nota": float(p.get("sem_nota") or 0),
                "com_nota": float(p.get("com_nota") or 0),
            }
        )
    try:
        d1 = int(data.get("d1") or 0)
        d2 = int(data.get("d2") or 0)
    except (TypeError, ValueError):
        d1 = d2 = 0
    transporte = data.get("transporte") or {}
    client_name = (data.get("client_name") or "").strip()[:200]
    snapshot = {
        "d1": d1,
        "d2": d2,
        "ensemble": int(data.get("ensemble") or 0),
        "acrescimo": float(data.get("acrescimo") or 0),
        "transporte": {
            "total": float(transporte.get("total") or 0),
            "label": str(transporte.get("label") or ""),
            "kmT": transporte.get("kmT"),
            "pessoas": transporte.get("pessoas"),
        },
        "client_name": client_name,
        "packages": clean_pkgs,
    }
    label = ", ".join(p["name"] for p in clean_pkgs)[:300]
    return snapshot, label


def generate_quote(user_id: int, data: dict) -> tuple[EducaMantoQuote, dict]:
    """Valida, monta o snapshot e persiste um orçamento gerado.

    Args:
        user_id: Quem está gerando o orçamento.
        data: Corpo já parseado (pacotes selecionados, dias, ensemble, transporte, cliente).

    Returns:
        Tupla `(quote, snapshot)` — `snapshot` é o dict pronto para `pdf.gerar_orcamento_pdf`.

    Raises:
        QuoteValidationError: Nenhum pacote selecionado, ou dias zerados.
    """
    if not (data.get("packages") or []):
        raise QuoteValidationError("Selecione ao menos um pacote.")

    snapshot, label = build_snapshot(data)
    if snapshot["d1"] + snapshot["d2"] <= 0:
        raise QuoteValidationError("Preencha os dias (1 e/ou 2 sessões) antes de gerar.")

    quote = EducaMantoQuote(
        user_id=user_id,
        client_name=snapshot["client_name"] or None,
        packages_label=label,
        snapshot=json.dumps(snapshot, ensure_ascii=False),
    )
    db.session.add(quote)
    db.session.commit()
    return quote, snapshot


def load_quote_snapshot(quote: EducaMantoQuote) -> dict:
    """Carrega o snapshot congelado de um orçamento do histórico (nunca recalcula do pacote atual)."""
    return json.loads(quote.snapshot or "{}")


def search_history(
    *,
    query: str = "",
    date_from: str = "",
    date_to: str = "",
    user_id_filter: str = "",
    is_superadmin: bool = False,
) -> tuple[list[EducaMantoQuote], list[User]]:
    """Busca o histórico de orçamentos com os mesmos filtros da tela Jinja legada.

    Args:
        query: Busca textual em cliente/rótulo de pacotes.
        date_from: Data inicial (ISO), inclusiva.
        date_to: Data final (ISO), inclusiva (até 23:59:59).
        user_id_filter: Filtra por quem gerou — só tem efeito se `is_superadmin`.
        is_superadmin: Se `True`, habilita o filtro por usuário e a lista de usuários.

    Returns:
        Tupla `(entries, users)` — `users` só populado quando `is_superadmin`.
    """
    q = EducaMantoQuote.query
    if query:
        like = f"%{query}%"
        q = q.filter(
            or_(
                EducaMantoQuote.client_name.ilike(like),
                EducaMantoQuote.packages_label.ilike(like),
            )
        )
    if date_from:
        try:
            q = q.filter(EducaMantoQuote.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            q = q.filter(
                EducaMantoQuote.created_at < datetime.fromisoformat(date_to) + timedelta(days=1)
            )
        except ValueError:
            pass
    if is_superadmin and user_id_filter.isdigit():
        q = q.filter_by(user_id=int(user_id_filter))

    entries = q.order_by(EducaMantoQuote.created_at.desc()).limit(300).all()

    users: list[User] = []
    if is_superadmin:
        users = (
            User.query.filter(
                User.id.in_(db.session.query(EducaMantoQuote.user_id).distinct())
            )
            .order_by(User.name.asc())
            .all()
        )
    return entries, users
