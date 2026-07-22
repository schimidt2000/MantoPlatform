"""Endpoints de ESCRITA/AÇÃO de configurações/sync/anúncio/migração (feature 168, US6).

Reusa, sem duplicar, `app.admin.config_ops` e os helpers já existentes em `app.calendar`,
`app.drive_migration`, `app.catalogo.importer`, `app.email_service`. Gate `require_superadmin`.
"""

from datetime import date
from typing import Any

from flask import current_app, jsonify, request
from flask_login import current_user

from app.admin import config_ops
from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.models import SiteSetting


def _has_role(*names: str) -> bool:
    upper = [n.upper() for n in names]
    return any(r.name.upper() in upper for r in current_user.roles)


def _require_superadmin() -> Any:
    if not _has_role(RoleName.SUPERADMIN):
        return json_error("Sem permissão", 403)
    return None


@api_bp.route("/admin/settings", methods=["PATCH"])
@api_login_required
def api_admin_settings_update() -> Any:
    """Atualiza as configurações gerais do sistema (feature 168)."""
    denied = _require_superadmin()
    if denied:
        return denied
    settings = SiteSetting.query.get(1)
    if not settings:
        return json_error("Configurações não encontradas", 404)
    is_multipart = request.content_type and "multipart/form-data" in request.content_type
    fields = request.form if is_multipart else (request.get_json(silent=True) or {})
    logo_file = request.files.get("logo") if is_multipart else None
    config_ops.update_settings(settings, fields, logo_file=logo_file)
    return jsonify({"ok": True})


@api_bp.route("/admin/sync/run", methods=["POST"])
@api_login_required
def api_admin_sync_run() -> Any:
    """Dispara sync manual ou limpeza de eventos fantasma (feature 168)."""
    denied = _require_superadmin()
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    action = body.get("action", "")

    from app.calendar.routes import CALENDAR_ID as _CAL_ID
    from app.calendar.routes import _cleanup_stale_events, _mark_month_synced
    from app.calendar.routes import sync_events as _sync_events
    from app.calendar.service import fetch_events_for_month as _fetch
    from app.models import CalendarEvent

    if action == "sync_now":
        today = date.today()
        future_months = []
        for i in range(7):
            total_m = today.month - 1 + i
            y = today.year + total_m // 12
            m = total_m % 12 + 1
            future_months.append((y, m, f"{y:04d}-{m:02d}"))

        results = []
        for y, m, ym in future_months:
            try:
                items = _fetch(_CAL_ID, y, m)
                _sync_events(items)
                _mark_month_synced(ym)
                results.append({"ym": ym, "ok": True, "count": len(items)})
            except Exception as exc:  # noqa: BLE001 - erro de integração externa, reportado ao usuário
                results.append({"ym": ym, "ok": False, "err": str(exc), "count": 0})

        errors_count = sum(1 for r in results if not r["ok"])
        total_events = sum(r["count"] for r in results)
        message = (
            f"Sync concluído com {errors_count} erro(s). Verifique o resultado abaixo."
            if errors_count
            else f"Sync concluído: {len(results)} meses futuros sincronizados ({total_events} eventos processados)."
        )
        return jsonify({"results": results, "message": message})

    if action == "cleanup_past":
        months_in_db: set[str] = set()
        for ev in CalendarEvent.query.with_entities(CalendarEvent.start_at).all():
            if ev.start_at:
                months_in_db.add(f"{ev.start_at.year:04d}-{ev.start_at.month:02d}")

        results = []
        for ym in sorted(months_in_db):
            y, m = int(ym[:4]), int(ym[5:7])
            try:
                items = _fetch(_CAL_ID, y, m)
                _sync_events(items)
                removed_titles = _cleanup_stale_events(items, y, m)
                _mark_month_synced(ym)
                results.append({"ym": ym, "removed": len(removed_titles), "ok": True})
            except Exception as exc:  # noqa: BLE001
                results.append({"ym": ym, "removed": 0, "ok": False, "err": str(exc)})

        total_removed = sum(r["removed"] for r in results)
        errors_count = sum(1 for r in results if not r["ok"])
        message = (
            f"Limpeza concluída com {errors_count} erro(s). {total_removed} evento(s) fantasma(s) removido(s)."
            if errors_count
            else f"Limpeza concluída: {total_removed} evento(s) fantasma(s) removido(s) em {len(results)} mês(es)."
        )
        return jsonify({"results": results, "message": message})

    return json_error("Ação inválida", 400)


@api_bp.route("/admin/portal-announcement", methods=["POST"])
@api_login_required
def api_admin_portal_announcement() -> Any:
    """Envia o anúncio do portal por email às talentos com email cadastrado (feature 168)."""
    denied = _require_superadmin()
    if denied:
        return denied
    from app.email_service import send_portal_announcement_email
    from app.models import Talent

    talents_with_email = Talent.query.filter(
        Talent.email_contact.isnot(None), Talent.email_contact != ""
    ).all()
    sent = 0
    failed = 0
    for talent in talents_with_email:
        if send_portal_announcement_email(talent):
            sent += 1
        else:
            failed += 1
    return jsonify({"sent": sent, "failed": failed})


@api_bp.route("/admin/migrar-arquivos/start", methods=["POST"])
@api_login_required
def api_admin_migrar_arquivos_start() -> Any:
    """Dispara a migração de arquivos do Drive para o volume em segundo plano (feature 168)."""
    denied = _require_superadmin()
    if denied:
        return denied
    from app.drive_migration import start_background_migration

    started = start_background_migration(current_app._get_current_object())
    return jsonify({"started": started})


@api_bp.route("/admin/importar-catalogo/start", methods=["POST"])
@api_login_required
def api_admin_importar_catalogo_start() -> Any:
    """Dispara a (re)importação do catálogo em segundo plano (feature 168)."""
    denied = _require_superadmin()
    if denied:
        return denied
    from app.catalogo.importer import start_background_import

    csv_path = "Produtos Catalogo/wc-product-export-16-7-2026-1784216390934.csv"
    started = start_background_import(current_app._get_current_object(), csv_path)
    return jsonify({"started": started})
