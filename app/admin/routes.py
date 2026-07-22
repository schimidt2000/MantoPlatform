from collections import defaultdict
from datetime import datetime, date, timedelta
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash, abort
from flask_login import login_required, current_user

from app import db
from app.admin import catalog_ops, config_ops, user_ops
from app.models import User, SiteSetting, Role, EventLog, CalendarEvent, AuditLog, SalaryHistory
from app.constants import RoleName

admin_bp = Blueprint("admin", __name__)


def _is_superadmin() -> bool:
    return any(r.name == RoleName.SUPERADMIN for r in current_user.roles)


def require_superadmin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _is_superadmin():
            return {"ok": False, "error": "Acesso apenas para SuperAdmin"}, 403
        return fn(*args, **kwargs)
    return wrapper


def require_users_access(fn):
    """Acesso à seção de Usuários: SUPERADMIN (tudo) ou FINANCEIRO (PIX + salário)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        roles = {r.name.upper() for r in current_user.roles}
        if not ({RoleName.SUPERADMIN, RoleName.FINANCEIRO} & roles):
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def get_settings():
    return SiteSetting.query.get(1)


@admin_bp.route("/", methods=["GET"])
@login_required
@require_superadmin
def admin_home():
    return render_template(
        "admin_dashboard.html",
        settings=get_settings(),
        active="home",
        title="Admin - Painel",
    )


@admin_bp.route("/users", methods=["GET"])
@login_required
@require_users_access
def list_users():
    users_data = [
        {"user": u, "salary": salary} for u, salary in user_ops.list_users_with_salary()
    ]
    return render_template(
        "admin_users.html",
        users_data=users_data,
        is_superadmin=_is_superadmin(),
        settings=get_settings(),
        active="users",
        title="Admin - Usuários",
    )


@admin_bp.route("/users/new", methods=["GET", "POST"])
@login_required
@require_superadmin
def create_user():
    def _render(error=None):
        return render_template(
            "admin_create_user.html",
            error=error,
            form=request.form if request.method == "POST" else {},
            settings=get_settings(),
            active="users",
            title="Admin - Criar Usuário",
            roles=Role.query.order_by(Role.name.asc()).all(),
        )

    if request.method == "GET":
        return _render()

    user_type = request.form.get("user_type", "access")
    role_ids = [int(r) for r in request.form.getlist("roles")] if user_type != "payment_only" else None
    salary = user_ops.SalaryInput(
        amount=request.form.get("salary", "").strip(),
        payment_type=request.form.get("payment_type", "").strip(),
        start_date=request.form.get("start_date", "").strip() or None,
        notes=request.form.get("notes", "").strip(),
    )

    try:
        user = user_ops.create_user(
            user_type=user_type,
            name=request.form.get("name", ""),
            email=request.form.get("email", ""),
            temp_password=request.form.get("temp_password", ""),
            role_ids=role_ids,
            pix_key=request.form.get("pix_key", ""),
            pix_key_type=request.form.get("pix_key_type", ""),
            salary=salary,
        )
    except user_ops.UserValidationError as exc:
        return _render(error=exc.message)

    if user.has_access:
        flash("Usuário criado com sucesso! A senha de primeiro uso foi copiada para a área de transferência.", "success")
    else:
        flash("Pessoa cadastrada com sucesso (sem acesso ao sistema).", "success")
    return redirect(url_for("admin.list_users"))


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@require_users_access
def edit_user(user_id: int):
    """Página unificada do usuário. Identidade/papéis = superadmin; PIX/salário = também financeiro."""
    user = User.query.get_or_404(user_id)

    def _render(error=None):
        return render_template(
            "admin_user_edit.html",
            user=user,
            error=error,
            is_superadmin=_is_superadmin(),
            history=user.salary_histories.order_by(SalaryHistory.start_date.desc()).all(),
            settings=get_settings(),
            active="users",
            title="Admin - Editar Usuário",
            roles=Role.query.order_by(Role.name.asc()).all(),
        )

    if request.method == "POST":
        # Edição de identidade/papéis é exclusiva do Superadmin (PIX e salário têm rotas próprias).
        if not _is_superadmin():
            abort(403)
        try:
            user_ops.update_user_identity(
                user,
                name=request.form.get("name", ""),
                email=request.form.get("email", ""),
                is_active=request.form.get("is_active") == "1",
                receives_commission=request.form.get("receives_commission") == "1",
                role_ids=[int(r) for r in request.form.getlist("roles")],
            )
        except user_ops.UserValidationError as exc:
            return _render(error=exc.message)
        flash("Dados do usuário atualizados.", "success")
        return redirect(url_for("admin.edit_user", user_id=user.id))

    return _render()


@admin_bp.route("/users/<int:user_id>/pix", methods=["POST"])
@login_required
@require_users_access
def update_pix(user_id: int):
    """Atualiza dados de pagamento (PIX). Superadmin ou Financeiro."""
    user = User.query.get_or_404(user_id)
    user_ops.update_pix(
        user,
        pix_key=request.form.get("pix_key", ""),
        pix_key_type=request.form.get("pix_key_type", ""),
    )
    flash("Dados de PIX atualizados.", "success")
    return redirect(url_for("admin.edit_user", user_id=user.id))


@admin_bp.route("/users/<int:user_id>/salario", methods=["POST"])
@login_required
@require_users_access
def add_salary(user_id: int):
    """Registra novo salário (encerra o vigente). Superadmin ou Financeiro."""
    user = User.query.get_or_404(user_id)
    salary = user_ops.SalaryInput(
        amount=request.form.get("salary", "").strip(),
        payment_type=request.form.get("payment_type", "").strip(),
        start_date=request.form.get("start_date", "").strip() or None,
        notes=request.form.get("notes", "").strip(),
    )
    try:
        user_ops.add_salary(user, salary)
    except user_ops.UserValidationError as exc:
        flash(exc.message, "error")
        return redirect(url_for("admin.edit_user", user_id=user.id))
    flash("Salário registrado.", "success")
    return redirect(url_for("admin.edit_user", user_id=user.id))


@admin_bp.route("/users/<int:user_id>/grant-access", methods=["POST"])
@login_required
@require_superadmin
def grant_access(user_id: int):
    """Concede acesso a uma pessoa cadastrada só para pagamento."""
    user = User.query.get_or_404(user_id)
    try:
        user_ops.grant_access(
            user,
            email=request.form.get("email", ""),
            temp_password=request.form.get("temp_password", ""),
        )
    except user_ops.UserValidationError as exc:
        flash(exc.message, "error")
        return redirect(url_for("admin.edit_user", user_id=user.id))
    flash("Acesso concedido. A pessoa deve trocar a senha no primeiro login.", "success")
    return redirect(url_for("admin.edit_user", user_id=user.id))


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@login_required
@require_superadmin
def reset_password(user_id: int):
    user = User.query.get_or_404(user_id)
    try:
        user_ops.reset_password(user, temp_password=request.form.get("temp_password", ""))
    except user_ops.UserValidationError as exc:
        flash(exc.message, "error")
        return redirect(url_for("admin.edit_user", user_id=user.id))
    flash("Senha resetada com sucesso.", "success")
    return redirect(url_for("admin.edit_user", user_id=user.id))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@require_superadmin
def delete_user(user_id: int):
    user = User.query.get_or_404(user_id)
    try:
        user_ops.delete_user(user, actor_id=current_user.id)
    except (user_ops.UserValidationError, user_ops.UserDeletionBlockedError) as exc:
        flash(exc.message, "error")
        return redirect(url_for("admin.list_users"))
    flash("Usuário excluído.", "success")
    return redirect(url_for("admin.list_users"))


@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
@require_superadmin
def admin_settings():
    settings = SiteSetting.query.get(1)
    if not settings:
        settings = SiteSetting(id=1)
        db.session.add(settings)
        db.session.commit()

    if request.method == "POST":
        config_ops.update_settings(settings, request.form, logo_file=request.files.get("logo"))
        flash("Configurações salvas.", "success")
        return redirect(url_for("admin.admin_settings"))

    users = User.query.order_by(User.name.asc()).all()
    return render_template(
        "admin_settings.html",
        settings=settings,
        users=users,
        active="settings",
        title="Admin - Configurações",
    )


# ─── LOGS DE AUDITORIA ────────────────────────────────────────────────────────

@admin_bp.route("/logs")
@login_required
@require_superadmin
def audit_logs():
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
        db.session.query(AuditLog.entity_type)
        .filter(AuditLog.entity_type.isnot(None))
        .distinct()
        .order_by(AuditLog.entity_type)
        .all()
    )

    # Seção "Eventos no banco" — estado atual da agenda
    all_events = (
        CalendarEvent.query
        .filter(CalendarEvent.event_type != "ENSAIO")
        .order_by(CalendarEvent.start_at.desc())
        .limit(200)
        .all()
    )

    return render_template(
        "admin_logs.html",
        logs=logs,
        entity_type=entity_type,
        actor=actor,
        entity_types=[r[0] for r in entity_types],
        all_events=all_events,
    )


# ─── ANÚNCIO DO PORTAL ───────────────────────────────────────────────────────

@admin_bp.route("/portal-announcement", methods=["GET", "POST"])
@login_required
@require_superadmin
def portal_announcement():
    from app.models import Talent
    from app.email_service import send_portal_announcement_email

    talents_with_email    = Talent.query.filter(Talent.email_contact.isnot(None), Talent.email_contact != "").all()
    talents_without_email = Talent.query.filter(
        (Talent.email_contact.is_(None)) | (Talent.email_contact == "")
    ).count()

    if request.method == "POST":
        sent = 0
        failed = 0
        for talent in talents_with_email:
            if send_portal_announcement_email(talent):
                sent += 1
            else:
                failed += 1
        flash(
            f"Anúncio enviado: {sent} email(s) entregue(s)"
            + (f", {failed} falha(s)." if failed else "."),
            "success" if not failed else "info",
        )
        return redirect(url_for("admin.portal_announcement"))

    return render_template(
        "admin_portal_announcement.html",
        total=len(talents_with_email),
        without_email=talents_without_email,
    )


# ─── PAINEL DE DESEMPENHO ─────────────────────────────────────────────────────

@admin_bp.route("/sync", methods=["GET", "POST"])
@login_required
@require_superadmin
def sync_status():
    """Painel de status do sync Google Calendar → banco."""
    import json as _json
    from datetime import date as _date
    from app.models import SiteSetting, CalendarEvent

    settings = SiteSetting.query.get(1)
    raw_cache = _json.loads(settings.calendar_sync_cache) if settings and settings.calendar_sync_cache else {}

    # Meses com eventos no banco (todos, inclusive passados)
    all_events = CalendarEvent.query.with_entities(CalendarEvent.start_at).all()
    months_in_db: set[str] = set()
    for ev in all_events:
        if ev.start_at:
            months_in_db.add(f"{ev.start_at.year:04d}-{ev.start_at.month:02d}")

    now = datetime.utcnow()
    months_info = []
    for ym in sorted(months_in_db, reverse=True):
        ts_str = raw_cache.get(ym)
        if ts_str:
            age_min = int((now - datetime.fromisoformat(ts_str)).total_seconds() // 60)
            fresh = age_min < 20
        else:
            age_min = None
            fresh = False
        y_int, m_int = int(ym[:4]), int(ym[5:7])
        m_start = datetime(y_int, m_int, 1)
        m_end = datetime(y_int + 1, 1, 1) if m_int == 12 else datetime(y_int, m_int + 1, 1)
        count = CalendarEvent.query.filter(
            CalendarEvent.start_at >= m_start,
            CalendarEvent.start_at < m_end,
        ).count()
        months_info.append({"ym": ym, "age_min": age_min, "fresh": fresh, "count": count})

    msg = None
    error = None
    cleanup_result = None
    sync_result = None
    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "sync_now":
            from app.calendar.routes import sync_events as _sync_events, _mark_month_synced, CALENDAR_ID as _CAL_ID
            from app.calendar.service import fetch_events_for_month as _fetch
            from datetime import date as _date_cls

            today = _date_cls.today()
            future_months = []
            for i in range(7):  # mês atual + 6 meses à frente
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
                except Exception as exc:
                    results.append({"ym": ym, "ok": False, "err": str(exc), "count": 0})

            sync_result = results
            errors_count = sum(1 for r in results if not r["ok"])
            total_events = sum(r["count"] for r in results)
            if errors_count:
                error = f"Sync concluído com {errors_count} erro(s). Verifique o resultado abaixo."
            else:
                msg = f"Sync concluído: {len(results)} meses futuros sincronizados ({total_events} eventos processados)."

        elif action == "cleanup_past":
            # Importa só quando necessário para não poluir o namespace global
            from app.calendar.routes import sync_events as _sync_events, _cleanup_stale_events, _mark_month_synced, CALENDAR_ID as _CAL_ID
            from app.calendar.service import fetch_events_for_month as _fetch

            # Limpa TODOS os meses com eventos no banco — incluindo mês atual e futuros.
            # Isso garante que eventos fantasma de qualquer mês sejam removidos.
            all_months = sorted(months_in_db)
            results = []
            for ym in all_months:
                y, m = int(ym[:4]), int(ym[5:7])
                try:
                    items = _fetch(_CAL_ID, y, m)
                    _sync_events(items)
                    removed_titles = _cleanup_stale_events(items, y, m)
                    _mark_month_synced(ym)
                    results.append({"ym": ym, "removed": len(removed_titles), "titles": removed_titles, "ok": True})
                except Exception as exc:
                    results.append({"ym": ym, "removed": 0, "titles": [], "ok": False, "err": str(exc)})
            cleanup_result = results
            total_removed = sum(r["removed"] for r in results)
            errors_count = sum(1 for r in results if not r["ok"])
            if errors_count:
                error = f"Limpeza concluída com {errors_count} erro(s). {total_removed} evento(s) fantasma(s) removido(s)."
            else:
                msg = f"Limpeza concluída: {total_removed} evento(s) fantasma(s) removido(s) em {len(all_months)} mês(es)."

    from app.models import AuditLog
    agenda_logs = (
        AuditLog.query
        .filter(AuditLog.entity_type == "agenda")
        .order_by(AuditLog.created_at.desc())
        .limit(20)
        .all()
    )

    auto_sync_at = settings.calendar_auto_sync_at if settings else None
    auto_sync_age_min = (
        int((now - auto_sync_at).total_seconds() // 60) if auto_sync_at else None
    )

    return render_template(
        "admin_sync.html",
        months_info=months_info,
        agenda_logs=agenda_logs,
        msg=msg,
        error=error,
        cleanup_result=cleanup_result,
        sync_result=sync_result,
        auto_sync_at=auto_sync_at,
        auto_sync_age_min=auto_sync_age_min,
        active="sync",
        title="Admin - Sync Agenda",
    )


@admin_bp.route("/desempenho")
@login_required
@require_superadmin
def desempenho():
    month_str = request.args.get("month", "")
    try:
        year, month = int(month_str[:4]), int(month_str[5:7])
    except (ValueError, IndexError):
        today = date.today()
        year, month = today.year, today.month

    ym = f"{year:04d}-{month:02d}"
    start = datetime(year, month, 1)
    end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)

    # ── Casting ───────────────────────────────────────────────
    casting_logs = EventLog.query.filter(
        EventLog.actor_role == "Casting",
        EventLog.created_at >= start,
        EventLog.created_at < end,
    ).all()
    casting_raw = defaultdict(int)
    for log in casting_logs:
        casting_raw[log.actor_name] += 1
    casting_stats = sorted(casting_raw.items(), key=lambda x: -x[1])

    # ── Figurino ──────────────────────────────────────────────
    figurino_logs = EventLog.query.filter(
        EventLog.actor_role == "Figurino",
        EventLog.created_at >= start,
        EventLog.created_at < end,
    ).all()
    figurino_raw = defaultdict(int)
    for log in figurino_logs:
        figurino_raw[log.actor_name] += 1
    figurino_stats = sorted(figurino_raw.items(), key=lambda x: -x[1])

    # ── Vendas ────────────────────────────────────────────────
    eventos_vendidos = (
        CalendarEvent.query
        .filter(
            CalendarEvent.seller_id.isnot(None),
            CalendarEvent.start_at >= start,
            CalendarEvent.start_at < end,
        )
        .all()
    )
    vendas_raw = defaultdict(lambda: {"count": 0, "total": 0})
    for ev in eventos_vendidos:
        nome = ev.seller.name if ev.seller else "Desconhecido"
        vendas_raw[nome]["count"] += 1
        vendas_raw[nome]["total"] += ev.sale_value or 0
    vendas_stats = sorted(vendas_raw.items(), key=lambda x: -x[1]["total"])

    return render_template(
        "desempenho.html",
        ym=ym,
        casting_stats=casting_stats,
        figurino_stats=figurino_stats,
        vendas_stats=vendas_stats,
        total_casting=sum(casting_raw.values()),
        total_figurino=sum(figurino_raw.values()),
        total_vendas=sum(v["count"] for v in vendas_raw.values()),
        total_valor=sum(v["total"] for v in vendas_raw.values()),
    )


@admin_bp.route("/migrar-arquivos", methods=["GET"])
@login_required
@require_superadmin
def migrar_arquivos():
    """Página para migrar fotos/documentos de talentos do Google Drive para o volume (feature 087)."""
    from app.drive_migration import TALENT_MEDIA_FIELDS, is_drive_url, migration_status
    from app.models import Talent

    field_labels = {
        "photo_face_path": "Foto do rosto",
        "photo_full_path": "Foto de corpo inteiro",
        "doc_photo_path": "Foto do documento",
        "cnh_file_path": "Arquivo da CNH",
    }
    pending = []
    for t in Talent.query.order_by(Talent.full_name).all():
        for field in TALENT_MEDIA_FIELDS:
            url = getattr(t, field)
            if is_drive_url(url):
                pending.append({
                    "id": t.id,
                    "name": t.full_name,
                    "field": field_labels.get(field, field),
                    "url": url,
                })
    return render_template(
        "admin_migrar_arquivos.html",
        settings=get_settings(),
        active="users",
        title="Admin - Migrar arquivos do Drive",
        remaining=len(pending),
        pending=pending,
        status=migration_status,
    )


@admin_bp.route("/migrar-arquivos", methods=["POST"])
@login_required
@require_superadmin
def migrar_arquivos_start():
    """Dispara a migração Drive -> volume em segundo plano."""
    from app.drive_migration import start_background_migration

    started = start_background_migration(current_app._get_current_object())
    if started:
        flash("Migração iniciada. Acompanhe o progresso nesta página.", "success")
    else:
        flash("A migração já está em andamento.", "warning")
    return redirect(url_for("admin.migrar_arquivos"))


@admin_bp.route("/importar-catalogo", methods=["GET"])
@login_required
@require_superadmin
def importar_catalogo():
    """Página para (re)importar o catálogo de personagens do CSV do WordPress (feature 133).

    Precisa ser disparado por aqui (botão, rodando no próprio servidor) — rodar o comando
    CLI a partir de uma máquina local, apontando só o DATABASE_URL para produção, salva as
    fotos baixadas no disco da máquina local, não no volume real do servidor.
    """
    from app.catalogo.importer import import_status
    from app.models import CatalogItem

    return render_template(
        "admin_importar_catalogo.html",
        settings=get_settings(),
        active="users",
        title="Admin - Importar catálogo",
        total_items=CatalogItem.query.count(),
        status=import_status,
    )


@admin_bp.route("/importar-catalogo", methods=["POST"])
@login_required
@require_superadmin
def importar_catalogo_start():
    """Dispara a (re)importação do catálogo em segundo plano."""
    from app.catalogo.importer import start_background_import

    csv_path = "Produtos Catalogo/wc-product-export-16-7-2026-1784216390934.csv"
    started = start_background_import(current_app._get_current_object(), csv_path)
    if started:
        flash("Importação do catálogo iniciada. Acompanhe o progresso nesta página.", "success")
    else:
        flash("A importação já está em andamento.", "warning")
    return redirect(url_for("admin.importar_catalogo"))


# ── Gestão de produtos do catálogo (criar/editar) — feature 139 ─────────────────


@admin_bp.route("/catalogo/categorias", methods=["POST"])
@login_required
@require_superadmin
def catalogo_admin_new_category():
    """Cria (ou reaproveita) uma categoria do catálogo via AJAX (feature 140)."""
    try:
        category = catalog_ops.create_or_reuse_category(request.form.get("name", ""))
    except catalog_ops.CatalogValidationError as exc:
        return {"ok": False, "error": exc.message}, 400
    return {"ok": True, "id": category.id, "name": category.name}


@admin_bp.route("/catalogo", methods=["GET"])
@login_required
@require_superadmin
def catalogo_admin_list():
    """Listagem de produtos do catálogo, com busca e filtros (feature 139)."""
    from app.models import CatalogCategory, CatalogItem

    q = request.args.get("q", "").strip()
    categoria_id = request.args.get("categoria", "").strip()
    status = request.args.get("status", "todos").strip()

    query = CatalogItem.query
    if q:
        query = query.filter(CatalogItem.name.ilike(f"%{q}%"))
    if categoria_id.isdigit():
        query = query.filter(CatalogItem.categories.any(CatalogCategory.id == int(categoria_id)))
    if status == "ativo":
        query = query.filter_by(is_active=True)
    elif status == "inativo":
        query = query.filter_by(is_active=False)

    items = query.order_by(CatalogItem.name.asc()).all()
    categories = CatalogCategory.query.order_by(CatalogCategory.name.asc()).all()

    return render_template(
        "admin_catalogo_list.html",
        settings=get_settings(),
        active="users",
        title="Admin - Gerenciar catálogo",
        items=items,
        categories=categories,
        q=q,
        categoria_id=categoria_id,
        status=status,
    )


@admin_bp.route("/catalogo/novo", methods=["GET", "POST"])
@login_required
@require_superadmin
def catalogo_admin_new():
    """Cria um novo produto do catálogo nativamente (feature 139)."""
    from app.models import CatalogCategory

    categories = CatalogCategory.query.order_by(CatalogCategory.name.asc()).all()
    all_tags = catalog_ops.all_tags()

    if request.method == "POST":
        try:
            item = catalog_ops.create_product(
                name=request.form.get("name", ""),
                description=request.form.get("description", ""),
                tags_raw=request.form.get("tags", ""),
                category_ids=[int(c) for c in request.form.getlist("category_ids[]") if c.isdigit()],
                form=request.form,
                files=request.files,
            )
        except catalog_ops.CatalogValidationError as exc:
            flash(exc.message, "error")
            return render_template(
                "admin_catalogo_form.html", settings=get_settings(), active="users",
                title="Novo produto do catálogo", item=None, categories=categories,
                all_tags=all_tags,
                selected_category_ids=set(int(c) for c in request.form.getlist("category_ids[]") if c.isdigit()),
                old=request.form,
            )
        flash(f'Produto "{item.name}" criado.', "success")
        return redirect(url_for("admin.catalogo_admin_list"))

    return render_template(
        "admin_catalogo_form.html", settings=get_settings(), active="users",
        title="Novo produto do catálogo", item=None, categories=categories,
        all_tags=all_tags, selected_category_ids=set(), old={},
    )


@admin_bp.route("/catalogo/<int:item_id>/editar", methods=["GET", "POST"])
@login_required
@require_superadmin
def catalogo_admin_edit(item_id: int):
    """Edita um produto existente do catálogo (feature 139)."""
    from app.models import CatalogCategory, CatalogItem

    item = CatalogItem.query.get_or_404(item_id)
    categories = CatalogCategory.query.order_by(CatalogCategory.name.asc()).all()
    all_tags = catalog_ops.all_tags()

    if request.method == "POST":
        try:
            catalog_ops.update_product(
                item,
                name=request.form.get("name", ""),
                description=request.form.get("description", ""),
                tags_raw=request.form.get("tags", ""),
                category_ids=[int(c) for c in request.form.getlist("category_ids[]") if c.isdigit()],
                form=request.form,
                files=request.files,
            )
        except catalog_ops.CatalogValidationError as exc:
            flash(exc.message, "error")
            return render_template(
                "admin_catalogo_form.html", settings=get_settings(), active="users",
                title=f"Editar — {item.name}", item=item, categories=categories,
                all_tags=all_tags,
                selected_category_ids=set(int(c) for c in request.form.getlist("category_ids[]") if c.isdigit()),
                old=request.form,
            )
        flash(f'Produto "{item.name}" atualizado.', "success")
        return redirect(url_for("admin.catalogo_admin_list"))

    return render_template(
        "admin_catalogo_form.html", settings=get_settings(), active="users",
        title=f"Editar — {item.name}", item=item, categories=categories,
        all_tags=all_tags, selected_category_ids={c.id for c in item.categories}, old={},
    )


@admin_bp.route("/catalogo/<int:item_id>/toggle-ativo", methods=["POST"])
@login_required
@require_superadmin
def catalogo_admin_toggle_ativo(item_id: int):
    """Ativa/inativa um produto do catálogo sem apagar os dados (feature 139)."""
    from app.models import CatalogItem

    item = CatalogItem.query.get_or_404(item_id)
    catalog_ops.toggle_active(item)
    flash(f'Produto "{item.name}" agora está {"ativo" if item.is_active else "inativo"}.', "success")
    return redirect(request.referrer or url_for("admin.catalogo_admin_list"))


@admin_bp.route("/catalogo/<int:item_id>/excluir", methods=["POST"])
@login_required
@require_superadmin
def catalogo_admin_delete(item_id: int):
    """Exclui definitivamente um produto do catálogo, com suas fotos (feature 139)."""
    from app.models import CatalogItem

    item = CatalogItem.query.get_or_404(item_id)
    name = item.name
    catalog_ops.delete_product(item)
    flash(f'Produto "{name}" excluído.', "success")
    return redirect(url_for("admin.catalogo_admin_list"))
