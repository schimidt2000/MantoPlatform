"""Endpoints de LEITURA de configurações/logs/desempenho/sync/migração (feature 168, US6).

Reusa, sem duplicar, os helpers já existentes em `app.calendar`, `app.drive_migration`,
`app.catalogo.importer`. Gate `require_superadmin` reimplementado como função.
"""

import json
from collections import defaultdict
from datetime import datetime
from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.models import AuditLog, CalendarEvent, EventLog, SiteSetting


def _has_role(*names: str) -> bool:
    upper = [n.upper() for n in names]
    return any(r.name.upper() in upper for r in current_user.roles)


def _require_superadmin() -> Any:
    if not _has_role(RoleName.SUPERADMIN):
        return json_error("Sem permissão", 403)
    return None


def _settings_summary(settings: SiteSetting) -> dict:
    return {
        "logo_path": settings.logo_path or "",
        "default_commission_rate": settings.default_commission_rate,
        "educamanto_seller_id": settings.educamanto_seller_id,
        "tax_rate": settings.tax_rate,
        "fator_r_threshold": settings.fator_r_threshold,
        "manto_address": settings.manto_address or "",
        "departure_margin_minutes": settings.departure_margin_minutes,
        "google_maps_api_key": settings.google_maps_api_key or "",
        "email_notifications_enabled": settings.email_notifications_enabled,
        "whatsapp_form_number": settings.whatsapp_form_number or "",
        "release_date": settings.release_date.isoformat() if settings.release_date else None,
    }


@api_bp.route("/admin/settings")
@api_login_required
def api_admin_settings_get() -> Any:
    """Configurações gerais do sistema (feature 168)."""
    denied = _require_superadmin()
    if denied:
        return denied
    settings = SiteSetting.query.get(1)
    if not settings:
        return json_error("Configurações não encontradas", 404)
    return jsonify(_settings_summary(settings))


@api_bp.route("/admin/logs")
@api_login_required
def api_admin_logs() -> Any:
    """Logs de auditoria, paginados, com filtro por tipo de entidade e ator (feature 168)."""
    denied = _require_superadmin()
    if denied:
        return denied
    entity_type = request.args.get("entity_type", "")
    actor = request.args.get("actor", "").strip()
    page = request.args.get("page", 1, type=int)

    q = AuditLog.query.order_by(AuditLog.created_at.desc())
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if actor:
        q = q.filter(AuditLog.actor_name.ilike(f"%{actor}%"))
    logs = q.paginate(page=page, per_page=50, error_out=False)

    entity_types = (
        AuditLog.query.with_entities(AuditLog.entity_type)
        .filter(AuditLog.entity_type.isnot(None))
        .distinct()
        .order_by(AuditLog.entity_type)
        .all()
    )

    return jsonify(
        {
            "items": [
                {
                    "id": log.id,
                    "actor_name": log.actor_name,
                    "actor_role": log.actor_role or "",
                    "entity_type": log.entity_type or "",
                    "entity_id": log.entity_id,
                    "entity_name": log.entity_name or "",
                    "action": log.action,
                    "detail": log.detail or "",
                    "created_at": log.created_at.isoformat(),
                }
                for log in logs.items
            ],
            "page": logs.page,
            "pages": logs.pages,
            "total": logs.total,
            "entity_types": [r[0] for r in entity_types],
        }
    )


@api_bp.route("/admin/desempenho")
@api_login_required
def api_admin_desempenho() -> Any:
    """Painel de desempenho mensal: casting/figurino/vendas (feature 168)."""
    denied = _require_superadmin()
    if denied:
        return denied
    month_str = request.args.get("month", "")
    try:
        year, month = int(month_str[:4]), int(month_str[5:7])
    except (ValueError, IndexError):
        today = datetime.utcnow().date()
        year, month = today.year, today.month

    ym = f"{year:04d}-{month:02d}"
    start = datetime(year, month, 1)
    end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)

    casting_raw: dict[str, int] = defaultdict(int)
    for log in EventLog.query.filter(
        EventLog.actor_role == "Casting", EventLog.created_at >= start, EventLog.created_at < end
    ).all():
        casting_raw[log.actor_name] += 1

    figurino_raw: dict[str, int] = defaultdict(int)
    for log in EventLog.query.filter(
        EventLog.actor_role == "Figurino",
        EventLog.created_at >= start,
        EventLog.created_at < end,
    ).all():
        figurino_raw[log.actor_name] += 1

    vendas_raw: dict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "total": 0})
    for ev in CalendarEvent.query.filter(
        CalendarEvent.seller_id.isnot(None),
        CalendarEvent.start_at >= start,
        CalendarEvent.start_at < end,
    ).all():
        nome = ev.seller.name if ev.seller else "Desconhecido"
        vendas_raw[nome]["count"] += 1
        vendas_raw[nome]["total"] += float(ev.sale_value or 0)

    casting_stats = sorted(casting_raw.items(), key=lambda x: -x[1])
    figurino_stats = sorted(figurino_raw.items(), key=lambda x: -x[1])
    vendas_stats = sorted(vendas_raw.items(), key=lambda x: -x[1]["total"])

    return jsonify(
        {
            "month": ym,
            "casting": [{"name": n, "count": c} for n, c in casting_stats],
            "figurino": [{"name": n, "count": c} for n, c in figurino_stats],
            "vendas": [
                {"name": n, "count": v["count"], "total": v["total"]} for n, v in vendas_stats
            ],
            "totals": {
                "casting": sum(casting_raw.values()),
                "figurino": sum(figurino_raw.values()),
                "vendas": sum(v["count"] for v in vendas_raw.values()),
                "valor": sum(v["total"] for v in vendas_raw.values()),
            },
        }
    )


@api_bp.route("/admin/sync-status")
@api_login_required
def api_admin_sync_status() -> Any:
    """Status de sincronização da agenda por mês (feature 168)."""
    denied = _require_superadmin()
    if denied:
        return denied
    settings = SiteSetting.query.get(1)
    raw_cache = (
        json.loads(settings.calendar_sync_cache)
        if settings and settings.calendar_sync_cache
        else {}
    )

    months_in_db: set[str] = set()
    for ev in CalendarEvent.query.with_entities(CalendarEvent.start_at).all():
        if ev.start_at:
            months_in_db.add(f"{ev.start_at.year:04d}-{ev.start_at.month:02d}")

    now = datetime.utcnow()
    months_info = []
    for ym in sorted(months_in_db, reverse=True):
        ts_str = raw_cache.get(ym)
        age_min = (
            int((now - datetime.fromisoformat(ts_str)).total_seconds() // 60) if ts_str else None
        )
        fresh = age_min is not None and age_min < 20
        y_int, m_int = int(ym[:4]), int(ym[5:7])
        m_start = datetime(y_int, m_int, 1)
        m_end = datetime(y_int + 1, 1, 1) if m_int == 12 else datetime(y_int, m_int + 1, 1)
        count = CalendarEvent.query.filter(
            CalendarEvent.start_at >= m_start, CalendarEvent.start_at < m_end
        ).count()
        months_info.append({"ym": ym, "age_min": age_min, "fresh": fresh, "count": count})

    auto_sync_at = settings.calendar_auto_sync_at if settings else None
    auto_sync_age_min = int((now - auto_sync_at).total_seconds() // 60) if auto_sync_at else None

    recent_logs = (
        AuditLog.query.filter(AuditLog.entity_type == "agenda")
        .order_by(AuditLog.created_at.desc())
        .limit(20)
        .all()
    )

    return jsonify(
        {
            "months": months_info,
            "auto_sync_age_min": auto_sync_age_min,
            "recent_logs": [
                {
                    "id": log.id,
                    "actor_name": log.actor_name,
                    "detail": log.detail or "",
                    "created_at": log.created_at.isoformat(),
                }
                for log in recent_logs
            ],
        }
    )


@api_bp.route("/admin/migrar-arquivos/status")
@api_login_required
def api_admin_migrar_arquivos_status() -> Any:
    """Status da migração de arquivos do Drive para o volume (feature 168)."""
    denied = _require_superadmin()
    if denied:
        return denied
    from app.drive_migration import TALENT_MEDIA_FIELDS, is_drive_url, migration_status
    from app.models import Talent

    pending = []
    for t in Talent.query.order_by(Talent.full_name).all():
        for field in TALENT_MEDIA_FIELDS:
            url = getattr(t, field)
            if is_drive_url(url):
                pending.append({"talent_id": t.id, "name": t.full_name, "field": field})

    status = dict(migration_status)
    status["started_at"] = status["started_at"].isoformat() if status["started_at"] else None
    status["finished_at"] = status["finished_at"].isoformat() if status["finished_at"] else None
    return jsonify({"pending_count": len(pending), "pending": pending, "status": status})


@api_bp.route("/admin/importar-catalogo/status")
@api_login_required
def api_admin_importar_catalogo_status() -> Any:
    """Status da importação do catálogo (feature 168)."""
    denied = _require_superadmin()
    if denied:
        return denied
    from app.catalogo.importer import import_status
    from app.models import CatalogItem

    status = dict(import_status)
    status["started_at"] = status["started_at"].isoformat() if status["started_at"] else None
    status["finished_at"] = status["finished_at"].isoformat() if status["finished_at"] else None
    return jsonify({"total_items": CatalogItem.query.count(), "status": status})
