"""Importação e normalização de clientes a partir do CSV do Kommo CRM (feature 094).

A base de clientes é deduplicada pelo **telefone normalizado** (apenas dígitos, com DDI). Este módulo
é um serviço puro: não importa nada de HTTP/web, apenas a sessão do banco via ``app.db``.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app import db
from app.models import Client

# Cabeçalhos do CSV exportado do Kommo (kommo_export_leads_*.csv).
COL_ID = "ID"
COL_NAME = "Nome completo"
COL_PHONE = "Telefone comercial"
COL_EMAIL = "Email comercial"
COL_EMAIL_ALT = "Email pessoal"
COL_COMPANY = "Empresa lead 's"
COL_RESPONSIBLE = "Usuário responsável"
COL_TAGS = "Tags"
COL_STAGE = "Etapa do lead"
COL_FUNNEL = "Funil de vendas"
COL_VALUE = "Lead venda R$"
COL_CREATED = "Criado em"

# Um telefone discável tem entre 10 (DDD + 8) e 13 (DDI 55 + DDD + 9) dígitos. Fora disso = inválido
# (vazio, lixo ou números concatenados como nas linhas com 24/26 dígitos do export).
_PHONE_MIN = 10
_PHONE_MAX = 13


def normalize_phone(raw: str | None) -> str | None:
    """Normaliza um telefone para sua forma canônica (só dígitos, com DDI do Brasil).

    Remove tudo que não é dígito. Números com DDD mas sem código de país (10–11 dígitos) recebem o
    prefixo ``55``. Números fora da faixa discável (curtos demais ou concatenados) retornam ``None``.

    Args:
        raw: Telefone como veio do CSV (ex.: ``"'+5511942466868"``).

    Returns:
        Telefone canônico só com dígitos (ex.: ``"5511942466868"``), ou ``None`` se inválido.
    """
    digits = re.sub(r"\D", "", raw or "")
    if not digits:
        return None
    if len(digits) < _PHONE_MIN or len(digits) > _PHONE_MAX:
        return None
    if len(digits) in (10, 11):  # DDD + número, sem código de país → assume Brasil
        digits = "55" + digits
    return digits


def _parse_value(raw: str | None) -> Decimal | None:
    """Converte o valor de venda do lead ("Lead venda R$") em ``Decimal`` (ou ``None``)."""
    s = (raw or "").strip()
    if not s:
        return None
    # mantém dígitos, vírgula e ponto; trata vírgula como separador decimal pt-BR
    s = re.sub(r"[^\d,.-]", "", s).replace(".", "").replace(",", ".")
    if not s or s in {"-", "."}:
        return None
    try:
        val = Decimal(s)
    except InvalidOperation:
        return None
    return val if val > 0 else None


def _parse_created(raw: str | None) -> datetime | None:
    """Converte "Criado em" do Kommo (``DD.MM.YYYY HH:MM:SS``) em ``datetime`` (ou ``None``)."""
    s = (raw or "").strip()
    if not s:
        return None
    for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _merge_tags(existing: str | None, new: str | None) -> str | None:
    """Une tags de duas origens em uma string única, sem duplicar, preservando ordem."""
    seen: list[str] = []
    for src in (existing, new):
        for tag in (src or "").split(","):
            tag = tag.strip()
            if tag and tag not in seen:
                seen.append(tag)
    return ", ".join(seen) if seen else None


@dataclass
class ImportReport:
    """Resultado de uma importação do CSV do Kommo."""

    created: int = 0
    merged: int = 0
    skipped: int = 0
    skipped_reasons: dict[str, int] = field(default_factory=dict)

    def skip(self, reason: str) -> None:
        self.skipped += 1
        self.skipped_reasons[reason] = self.skipped_reasons.get(reason, 0) + 1

    def __str__(self) -> str:
        reasons = ", ".join(f"{k}={v}" for k, v in sorted(self.skipped_reasons.items()))
        return f"criados={self.created}, mesclados={self.merged}, ignorados={self.skipped}" + (
            f" ({reasons})" if reasons else ""
        )


def _apply_metadata(client: Client, row: dict, created_at: datetime | None) -> None:
    """Aplica/agrega metadados de marketing de uma linha do CSV ao cliente.

    Campos "mais recentes" (etapa, responsável, lead_id, valor) são sobrescritos apenas quando a linha
    é mais nova que a já registrada no cliente. Tags são sempre agregadas.
    """
    name = (row.get(COL_NAME) or "").strip()
    if name and not client.name:
        client.name = name[:200]

    client.tags = _merge_tags(client.tags, row.get(COL_TAGS))

    email = (row.get(COL_EMAIL) or row.get(COL_EMAIL_ALT) or "").strip()
    if email and not client.email:
        client.email = email[:200]
    company = (row.get(COL_COMPANY) or "").strip()
    if company and not client.company:
        client.company = company[:200]

    value = _parse_value(row.get(COL_VALUE))
    if value is not None and (client.lead_value is None or value > client.lead_value):
        client.lead_value = value

    # "mais recente" decide etapa/funil/responsável/lead_id e a data de criação registrada
    is_newer = created_at is not None and (
        client.kommo_created_at is None or created_at >= client.kommo_created_at
    )
    if is_newer or client.kommo_created_at is None:
        if created_at is not None:
            client.kommo_created_at = created_at
        stage = (row.get(COL_STAGE) or "").strip()
        if stage:
            client.lead_stage = stage[:120]
        funnel = (row.get(COL_FUNNEL) or "").strip()
        if funnel:
            client.funnel = funnel[:120]
        responsible = (row.get(COL_RESPONSIBLE) or "").strip()
        if responsible:
            client.responsible = responsible[:120]
        lead_id = (row.get(COL_ID) or "").strip()
        if lead_id:
            client.kommo_lead_id = lead_id[:40]


def import_kommo_csv(path: str) -> ImportReport:
    """Importa o CSV do Kommo, criando um cliente por telefone normalizado único (idempotente).

    Linhas sem nome ou sem telefone utilizável são ignoradas. Telefones repetidos (no arquivo ou já no
    banco) mesclam metadados num único cliente. Re-execução não duplica clientes.

    Args:
        path: Caminho para o arquivo CSV exportado do Kommo.

    Returns:
        Um :class:`ImportReport` com contagens de criados/mesclados/ignorados.
    """
    report = ImportReport()
    # cache phone -> Client desta execução (evita N queries e detecta duplicatas dentro do arquivo)
    cache: dict[str, Client] = {}

    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            name = (row.get(COL_NAME) or "").strip()
            phone = normalize_phone(row.get(COL_PHONE))
            if not phone:
                report.skip("sem_telefone")
                continue
            if not name:
                report.skip("sem_nome")
                continue

            created_at = _parse_created(row.get(COL_CREATED))

            client = cache.get(phone)
            if client is None:
                client = Client.query.filter_by(phone=phone).first()
            if client is None:
                client = Client(name=name[:200], phone=phone, source="kommo_import")
                phone_display = (row.get(COL_PHONE) or "").lstrip("'").strip()
                client.phone_display = phone_display[:30] or None
                db.session.add(client)
                cache[phone] = client
                _apply_metadata(client, row, created_at)
                report.created += 1
            else:
                cache[phone] = client
                _apply_metadata(client, row, created_at)
                report.merged += 1

    db.session.commit()
    return report
