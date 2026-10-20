"""Endpoints de ESCRITA/AÇÃO de configurações/sync/anúncio/migração (feature 168, US6).

Reusa, sem duplicar, `app.admin.config_ops` e os helpers já existentes em `app.calendar`,
`app.drive_migration`, `app.catalogo.importer`, `app.email_service`. Gate `require_superadmin`.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from flask import current_app, jsonify, request
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.admin import config_ops
from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.models import SiteSetting

if TYPE_CHECKING:
    from app.calendar.sumico_ops import ResultadoLimpeza


def _has_role(*names: str) -> bool:
    upper = [n.upper() for n in names]
    return any(r.name.upper() in upper for r in current_user.roles)


def _require_superadmin() -> Any:
    if not _has_role(RoleName.SUPERADMIN):
        return json_error("Sem permissão", 403)
    return None


_NUMEROS_DA_LIMPEZA = ("removed", "marcados", "movidos", "desmarcados", "inconclusivos", "falhas")


def _linha_vazia(ym: str) -> dict[str, Any]:
    return {"ym": ym, **{chave: 0 for chave in _NUMEROS_DA_LIMPEZA}}


def _linha_da_limpeza(ym: str, limpeza: ResultadoLimpeza) -> dict[str, Any]:
    """Uma linha de `results[]` a partir do `ResultadoLimpeza` do mês (feature 303)."""
    return {
        "ym": ym,
        "removed": len(limpeza.removidos),
        "marcados": len(limpeza.marcados),
        "movidos": len(limpeza.movidos),
        "desmarcados": len(limpeza.desmarcados),
        "inconclusivos": len(limpeza.inconclusivos),
        "falhas": len(limpeza.falhas),
        "ok": not limpeza.falhas,
    }


def _mensagem_da_limpeza(results: list[dict[str, Any]]) -> str:
    """O texto fixo do contrato da 303, com as somas de todos os meses."""
    soma = {chave: sum(r[chave] for r in results) for chave in _NUMEROS_DA_LIMPEZA}
    mensagem = (
        f"Limpeza concluída em {len(results)} mês(es): {soma['removed']} removido(s), "
        f"{soma['marcados']} mantido(s) e marcado(s), {soma['movidos']} com data atualizada, "
        f"{soma['desmarcados']} de volta ao Google Agenda, {soma['inconclusivos']} sem "
        f"confirmação do Google, {soma['falhas']} com falha."
    )
    com_erro = sum(1 for r in results if "err" in r)
    if com_erro:
        mensagem += f" {com_erro} mês(es) com erro."
    return mensagem


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
    try:
        config_ops.update_settings(settings, fields, logo_file=logo_file)
    except config_ops.ConfigValidationError as exc:
        db.session.rollback()
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify({"ok": True})


@api_bp.route("/admin/sync/run", methods=["POST"])
@api_login_required
def api_admin_sync_run() -> Any:
    """Dispara sync manual ou a limpeza de eventos fantasma (feature 168).

    `sync_now` busca e sincroniza os próximos meses, sem limpar. `cleanup_past` passa por todo
    mês que tem evento no banco e, desde a feature 303, confere no Google cada evento que faltou
    na lista: o vazio que sumiu é removido, o que tem dinheiro fica e é marcado, o que só mudou de
    data é atualizado — a resposta traz esses números por mês.
    """
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
                limpeza = _cleanup_stale_events(items, y, m)
                _mark_month_synced(ym)
                results.append(_linha_da_limpeza(ym, limpeza))
            except Exception as exc:  # noqa: BLE001
                # Mesma regra do ciclo (`sync.py`): rollback só em erro de banco, que invalida a
                # sessão e derrubaria os meses seguintes; em outro erro o pendente de
                # `sync_events` fica, porque os e-mails ao elenco já saíram.
                if isinstance(exc, SQLAlchemyError):
                    db.session.rollback()
                results.append({**_linha_vazia(ym), "ok": False, "err": str(exc)})

        return jsonify({"results": results, "message": _mensagem_da_limpeza(results)})

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
