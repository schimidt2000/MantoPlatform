import os
import re
import unicodedata
from datetime import datetime, timedelta
from flask import Blueprint, redirect, url_for, render_template, request, flash, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import or_

from app.models import Talent, EventRole, CalendarEvent, ImportState, EventRating, EventSubRating
from .. import db
from app.constants import RoleName
from .importer import import_new_talents_from_sheet


def _can_edit_talent():
    return any(r.name in (RoleName.SUPERADMIN, RoleName.CASTING) for r in current_user.roles)

talents_bp = Blueprint("talents", __name__)

GOOGLE_FORM_URL = "https://forms.gle/iaZWqNpvtG5FUU3E7"
SERVICE_ACCOUNT_JSON = os.path.abspath(os.path.join("instance", "credentials", "sheets_service_account.json"))


def _get_sheet_config():
    from flask import current_app
    return (
        current_app.config.get("TALENTS_SPREADSHEET_ID", "1A_bXqUP21HR1RWS8AVBmj1oPgjhIWBaFfYxeqX17Ric"),
        current_app.config.get("TALENTS_SHEET_NAME", "Respostas"),
    )

@talents_bp.route("/talents/add")
@login_required
def add_talent():
    return redirect(GOOGLE_FORM_URL)

@talents_bp.route("/talents")
@login_required
def list_talents():
    status = request.args.get("status", "active")
    # filtrou=1 indica que o form foi submetido; sem ele é visita fresca (default ativo)
    filtrou = request.args.get("filtrou", "0") == "1"
    q = request.args.get("q", "").strip()
    ja_trabalhou = request.args.get("ja_trabalhou", "0" if filtrou else ("1" if status == "active" else "0"))
    query = Talent.query.filter_by(status=status)
    if q:
        query = query.filter(or_(
            Talent.full_name.ilike(f"%{q}%"),
            Talent.artistic_name.ilike(f"%{q}%"),
        ))
    if ja_trabalhou == "1":
        query = query.filter(Talent.worked_before.is_(True))

    def normalize_header(value: str) -> str:
        text = (value or "").strip().lower()
        text = unicodedata.normalize("NFKD", text)
        text = text.encode("ascii", "ignore").decode("ascii")
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def split_values(raw: str) -> list:
        if not raw:
            return []
        parts = re.split(r"[;,/\n]+", raw)
        return [p.strip() for p in parts if p and p.strip()]

    if status == "active":
        languages = request.args.getlist("language")
        races = request.args.getlist("race")
        tops = request.args.getlist("top")
        bottoms = request.args.getlist("bottom")
        shoes = request.args.getlist("shoe")
        passport = request.args.getlist("passport")
        character = request.args.get("character", "").strip()

        # Tag: suporta múltiplos valores OU texto único com vírgulas
        raw_tags = request.args.getlist("tag")
        tags = []
        for t in raw_tags:
            tags.extend(split_values(t))

        height_op = request.args.get("height_op", "gte")
        height_value = request.args.get("height_value")

        if languages:
            lang_filters = [Talent.languages.ilike(f"%{l}%") for l in languages]
            query = query.filter(or_(*lang_filters))

        if races:
            query = query.filter(Talent.race.in_(races))

        if tops:
            query = query.filter(Talent.clothing_size_top.in_(tops))

        if bottoms:
            query = query.filter(Talent.clothing_size_bottom.in_(bottoms))

        if shoes:
            query = query.filter(Talent.shoe_size.in_(shoes))

        if height_value:
            try:
                height_num = int(height_value)
                if height_op == "gte":
                    query = query.filter(Talent.height_cm >= height_num)
                elif height_op == "lte":
                    query = query.filter(Talent.height_cm <= height_num)
            except ValueError:
                pass

        if passport:
            passport_filters = []
            for pv in passport:
                passport_filters.append(Talent.passport_status == pv)
            if passport_filters:
                query = query.filter(or_(*passport_filters))

        if tags:
            normalized = [normalize_header(t) for t in tags]
            tag_filters = [Talent.tags.ilike(f"%{t}%") for t in normalized if t]
            if tag_filters:
                query = query.filter(or_(*tag_filters))

        # Filtro por personagem (busca no histórico de EventRole)
        character_matches: dict = {}
        if character:
            matching_roles = (
                EventRole.query
                .filter(
                    EventRole.character_name.ilike(f"%{character}%"),
                    EventRole.assigned_at.isnot(None),
                    EventRole.talent_id.isnot(None),
                )
                .all()
            )
            matching_ids = {r.talent_id for r in matching_roles}
            query = query.filter(Talent.id.in_(matching_ids)) if matching_ids else query.filter(False)
            for r in matching_roles:
                bucket = character_matches.setdefault(r.talent_id, {})
                bucket[r.character_name] = bucket.get(r.character_name, 0) + 1

        all_active = Talent.query.filter_by(status="active").all()
        language_options = sorted({p for t in all_active for p in split_values(t.languages or "")})
        race_options = sorted({t.race for t in all_active if t.race})
        tag_options = sorted({p for t in all_active for p in split_values(t.tags or "")})
        size_options = ["XGG", "GG", "G", "M", "P", "XP"]
        shoe_options = [str(n) for n in range(33, 48)]
        passport_options = [
            ("visa",     "passaporte + visto americano"),
            ("passport", "passaporte sem visto"),
            ("none",     "sem passaporte"),
        ]
    else:
        language_options = []
        race_options = []
        tag_options = []
        size_options = []
        shoe_options = []
        passport_options = []
        character = ""
        character_matches = {}

    PAGE_SIZE = 60
    page = max(1, request.args.get("page", 1, type=int))
    pagination = query.order_by(Talent.full_name.asc()).paginate(
        page=page, per_page=PAGE_SIZE, error_out=False
    )
    people = pagination.items
    from datetime import datetime as _now_dt
    import_state = ImportState.query.filter_by(key="talents_form").first()
    pending_count = Talent.query.filter_by(status="pending").count()
    return render_template(
        "talents_list.html",
        people=people,
        pagination=pagination,
        status=status,
        pending_count=pending_count,
        ja_trabalhou=ja_trabalhou,
        language_options=language_options,
        race_options=race_options,
        tag_options=tag_options,
        size_options_top=size_options,
        size_options_bottom=size_options,
        shoe_options=shoe_options,
        passport_options=passport_options,
        q=q,
        character=character,
        character_matches=character_matches,
        import_state=import_state,
        now=_now_dt.utcnow(),
    )


# Ordem de exibição das categorias de sub-avaliação + rótulos pt-BR.
_RATING_CATEGORIES = [
    ("artista", "Artista"),
    ("som", "Som"),
    ("figurino", "Figurino"),
    ("texto", "Texto"),
    ("coordenacao", "Coordenação"),
    ("maquiagem", "Maquiagem"),
]
_RATING_CATEGORY_LABELS = dict(_RATING_CATEGORIES)

# Atalhos de período (dias para trás) e rótulos exibidos no recorte.
_PERIOD_PRESETS = {"30d": 30, "90d": 90, "365d": 365}
_PERIOD_LABELS = {
    "30d": "últimos 30 dias",
    "90d": "últimos 3 meses",
    "365d": "últimos 12 meses",
}

_MONTHS_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]
_MONTHS_PT_ABBR = [
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
]


def _now_sp() -> datetime:
    """Agora em horário de Brasília, naïve (mesma convenção dos eventos)."""
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None)


def _avg_score(values: list) -> float:
    """Média arredondada a 1 casa; 0.0 para lista vazia."""
    return round(sum(values) / len(values), 1) if values else 0.0


def _parse_period(period: str, from_raw: str, to_raw: str) -> tuple:
    """Resolve o filtro de período em (início, fim) — fim exclusivo; None = aberto.

    Args:
        period: "30d" | "90d" | "365d" | "custom" | "all".
        from_raw: data ISO inicial (apenas period=custom).
        to_raw: data ISO final (apenas period=custom).

    Returns:
        Tupla (start, end) de datetimes naïve (horário de Brasília) ou None.
    """
    if period in _PERIOD_PRESETS:
        return _now_sp() - timedelta(days=_PERIOD_PRESETS[period]), None
    if period == "custom":
        start = end = None
        try:
            if from_raw:
                start = datetime.fromisoformat(from_raw)
        except ValueError:
            pass
        try:
            if to_raw:
                end = datetime.fromisoformat(to_raw) + timedelta(days=1)
        except ValueError:
            pass
        return start, end
    return None, None


@talents_bp.route("/talents/avaliacoes")
@login_required
def avaliacoes():
    """Resumo das avaliações — filtros combináveis de período, categoria e evento.

    Visível a todos os usuários autenticados; a autoria fica anônima para todos,
    exceto super admin (salvo modo anônimo total) — ver feature 056.
    """

    event_id_raw = request.args.get("event_id", "").strip()
    event_id = int(event_id_raw) if event_id_raw.isdigit() else None

    cat = request.args.get("cat", "").strip().lower()
    if cat not in _RATING_CATEGORY_LABELS:
        cat = ""

    period = request.args.get("period", "all").strip().lower()
    if period not in ("30d", "90d", "365d", "custom", "all"):
        period = "all"
    from_raw = request.args.get("from", "").strip()
    to_raw = request.args.get("to", "").strip()

    # Critério de data do filtro de período (075): "evento" = data de realização do show
    # (CalendarEvent.start_at, padrão); "avaliacao" = data em que a nota foi enviada
    # (EventRating.submitted_at).
    date_mode = request.args.get("date_mode", "evento").strip().lower()
    if date_mode not in ("evento", "avaliacao"):
        date_mode = "evento"
    _date_col = EventRating.submitted_at if date_mode == "avaliacao" else CalendarEvent.start_at

    # Visão por evento: o evento já é o recorte — período não se aplica.
    period_start, period_end = (None, None) if event_id else _parse_period(period, from_raw, to_raw)

    selected_event = CalendarEvent.query.get(event_id) if event_id else None

    # Avaliações do recorte (join no evento para filtrar por data do evento).
    ratings_q = EventRating.query.join(CalendarEvent, EventRating.event_id == CalendarEvent.id)
    if event_id:
        ratings_q = ratings_q.filter(EventRating.event_id == event_id)
    if period_start:
        ratings_q = ratings_q.filter(_date_col >= period_start)
    if period_end:
        ratings_q = ratings_q.filter(_date_col < period_end)
    ratings = ratings_q.order_by(EventRating.submitted_at.desc()).all()

    rating_ids = [r.id for r in ratings]
    subs = (
        EventSubRating.query.filter(EventSubRating.rating_id.in_(rating_ids)).all()
        if rating_ids else []
    )
    rating_by_id = {r.id: r for r in ratings}

    # ── Anonimato da autoria (feature 056) ────────────────────────────────────
    # Por padrão a autoria é anônima para todos; só o super admin vê o nome real,
    # exceto quando o "modo anônimo total" estiver ligado (esconde até do super admin).
    from app.models import SiteSetting
    settings = SiteSetting.query.get(1)
    is_superadmin = any(r.name == RoleName.SUPERADMIN for r in current_user.roles)
    fully_anonymous = bool(settings and settings.ratings_fully_anonymous)
    show_authors = is_superadmin and not fully_anonymous

    # Função (personagem) do autor em cada evento avaliado — só quando a autoria é
    # visível, em uma única query (sem N+1). Múltiplas funções unidas por vírgula.
    event_functions: dict[tuple[int, int], str] = {}
    if show_authors and ratings:
        from app.calendar.routes import strip_role_prefix
        pairs = {(r.event_id, r.talent_id) for r in ratings}
        roles = (
            EventRole.query
            .filter(
                EventRole.event_id.in_({e for e, _ in pairs}),
                EventRole.talent_id.in_({t for _, t in pairs}),
            )
            .all()
        )
        for role in roles:
            key = (role.event_id, role.talent_id)
            if key not in pairs or not role.character_name:
                continue
            nome = strip_role_prefix(role.character_name)
            if not nome:
                continue
            atual = event_functions.get(key)
            event_functions[key] = f"{atual}, {nome}" if atual else nome

    # ── Pontuações primárias do recorte (geral ou da categoria filtrada) ──
    if cat:
        cat_subs = [s for s in subs if s.category == cat and s.score]
        primary = [
            {"score": s.score, "rating": rating_by_id.get(s.rating_id)}
            for s in cat_subs if rating_by_id.get(s.rating_id)
        ]
    else:
        primary = [{"score": r.score, "rating": r} for r in ratings if r.score]

    total = len(primary)
    avg_overall = _avg_score([p["score"] for p in primary])
    events_rated = len({p["rating"].event_id for p in primary})

    dist = {s: 0 for s in range(1, 6)}
    for p in primary:
        if 1 <= p["score"] <= 5:
            dist[p["score"]] += 1
    dist_max = max(dist.values()) if dist else 0

    # ── Médias por categoria (apenas na visão sem filtro de categoria) ──
    by_category = []
    if not cat:
        for key, label in _RATING_CATEGORIES:
            cat_scores = [s.score for s in subs if s.category == key and s.score]
            if cat_scores:
                by_category.append({
                    "key": key,
                    "label": label,
                    "avg": _avg_score(cat_scores),
                    "count": len(cat_scores),
                })

    # ── Comentários unificados: gerais ("Geral") + por categoria ──
    def _comment_item(score, text, rating, cat_key="", subject=None):
        # Anonimização no servidor (FR-006): quando a autoria não é visível, o nome e a
        # função NÃO entram no dado — vira apenas "Anônimo", sem identificador algum.
        if show_authors:
            author = rating.talent.full_name if rating.talent else "—"
            funcao = event_functions.get((rating.event_id, rating.talent_id))
        else:
            author = "Anônimo"
            funcao = None
        return {
            "score": score,
            "comment": text,
            "author": author,
            "author_funcao": funcao,
            "event_title": rating.event.title if rating.event else "—",
            "event_id": rating.event_id,
            "event_date": rating.event.start_at if rating.event else None,
            "submitted_at": rating.submitted_at,
            "cat_key": cat_key,
            "cat_label": _RATING_CATEGORY_LABELS.get(cat_key, "Geral"),
            "subject_name": subject.full_name if subject else None,
        }

    comments = []
    if not cat:
        for r in ratings:
            if r.comment and r.comment.strip():
                comments.append(_comment_item(r.score, r.comment.strip(), r))
    for s in subs:
        if cat and s.category != cat:
            continue
        r = rating_by_id.get(s.rating_id)
        if r and s.comment and s.comment.strip():
            comments.append(_comment_item(
                s.score, s.comment.strip(), r,
                cat_key=s.category, subject=s.subject_talent,
            ))
    comments.sort(key=lambda c: c["submitted_at"] or datetime.min, reverse=True)
    if not event_id:
        comments = comments[:30]   # geral: limita para não poluir

    # ── Pontos de atenção: notas 1–2 do recorte (gerais + categorias) ──
    attention = []
    if not cat:
        for r in ratings:
            if r.score and r.score <= 2:
                attention.append(_comment_item(r.score, (r.comment or "").strip(), r))
    for s in subs:
        if cat and s.category != cat:
            continue
        r = rating_by_id.get(s.rating_id)
        if r and s.score and s.score <= 2:
            attention.append(_comment_item(
                s.score, (s.comment or "").strip(), r,
                cat_key=s.category, subject=s.subject_talent,
            ))
    attention.sort(key=lambda c: c["submitted_at"] or datetime.min, reverse=True)
    attention = attention[:10]

    # ── Ranking de eventos e tendência mensal (apenas visão geral) ──
    best_events, worst_events, trend = [], [], []
    if not event_id:
        per_event: dict = {}
        per_month: dict = {}
        for p in primary:
            ev = p["rating"].event
            if not ev:
                continue
            per_event.setdefault(ev.id, {"event": ev, "scores": []})["scores"].append(p["score"])
            if ev.start_at:
                key = (ev.start_at.year, ev.start_at.month)
                per_month.setdefault(key, []).append(p["score"])

        ranked = sorted(
            (
                {
                    "id": data["event"].id,
                    "title": data["event"].title,
                    "start_at": data["event"].start_at,
                    "avg": _avg_score(data["scores"]),
                    "count": len(data["scores"]),
                }
                for data in per_event.values()
            ),
            key=lambda e: (-e["avg"], -(e["start_at"] or datetime.min).toordinal()),
        )
        best_events = ranked[:3]
        if len(ranked) >= 2:
            best_ids = {e["id"] for e in best_events}
            worst_events = [e for e in reversed(ranked) if e["id"] not in best_ids][:3]

        trend = [
            {
                "label": f"{_MONTHS_PT_ABBR[m - 1]}/{str(y)[2:]}",
                "avg": _avg_score(scores),
                "count": len(scores),
            }
            for (y, m), scores in sorted(per_month.items())
        ]

    # ── Seletor de eventos avaliados do período, agrupado por mês ──
    rated_q = (
        db.session.query(CalendarEvent.id, CalendarEvent.title, CalendarEvent.start_at)
        .join(EventRating, EventRating.event_id == CalendarEvent.id)
    )
    if period_start:
        rated_q = rated_q.filter(_date_col >= period_start)
    if period_end:
        rated_q = rated_q.filter(_date_col < period_end)
    rated_rows = (
        rated_q.group_by(CalendarEvent.id, CalendarEvent.title, CalendarEvent.start_at)
        .order_by(CalendarEvent.start_at.desc())
        .all()
    )
    if event_id and selected_event and event_id not in {r.id for r in rated_rows}:
        rated_rows = [selected_event] + list(rated_rows)

    event_groups = []
    for row in rated_rows:
        if row.start_at:
            label = f"{_MONTHS_PT[row.start_at.month - 1]} de {row.start_at.year}"
        else:
            label = "Sem data"
        if not event_groups or event_groups[-1]["label"] != label:
            event_groups.append({"label": label, "events": []})
        event_groups[-1]["events"].append(
            {"id": row.id, "title": row.title, "start_at": row.start_at}
        )

    # Rótulo do recorte exibido nos KPIs.
    recorte_parts = []
    if cat:
        recorte_parts.append(_RATING_CATEGORY_LABELS[cat])
    if not event_id:
        if period in _PERIOD_LABELS:
            recorte_parts.append(_PERIOD_LABELS[period])
        elif period == "custom" and (period_start or period_end):
            ini = period_start.strftime("%d/%m/%Y") if period_start else "…"
            fim = (period_end - timedelta(days=1)).strftime("%d/%m/%Y") if period_end else "…"
            recorte_parts.append(f"{ini} – {fim}")
        if date_mode == "avaliacao" and period != "all":
            recorte_parts.append("por data da avaliação")

    return render_template(
        "talents/avaliacoes.html",
        event_groups=event_groups,
        selected_event=selected_event,
        event_id=event_id,
        cat=cat,
        cat_label=_RATING_CATEGORY_LABELS.get(cat, ""),
        categories=_RATING_CATEGORIES,
        period=period,
        date_mode=date_mode,
        from_raw=from_raw,
        to_raw=to_raw,
        recorte_label=" · ".join(recorte_parts),
        has_filters=bool(cat or event_id or period != "all"),
        total=total,
        avg_overall=avg_overall,
        events_rated=events_rated,
        dist=dist,
        dist_max=dist_max,
        by_category=by_category,
        comments=comments,
        attention=attention,
        best_events=best_events,
        worst_events=worst_events,
        trend=trend,
        show_authors=show_authors,
        fully_anonymous=fully_anonymous,
        is_superadmin=is_superadmin,
    )


@talents_bp.route("/talents/avaliacoes/modo-anonimo", methods=["POST"])
@login_required
def toggle_modo_anonimo():
    """Liga/desliga o modo anônimo total das avaliações (só super admin) — feature 056."""
    if not any(r.name == RoleName.SUPERADMIN for r in current_user.roles):
        abort(403)

    from app.models import AuditLog, SiteSetting
    settings = SiteSetting.query.get(1)
    if settings is None:
        settings = SiteSetting(id=1)
        db.session.add(settings)

    enabled = request.form.get("enabled") == "1"
    settings.ratings_fully_anonymous = enabled
    db.session.add(AuditLog(
        actor_name=current_user.name,
        entity_type="settings",
        entity_id=1,
        action="ratings_fully_anonymous_on" if enabled else "ratings_fully_anonymous_off",
        detail=f"Modo anônimo total das avaliações {'ativado' if enabled else 'desativado'}.",
    ))
    db.session.commit()
    flash(
        "Modo anônimo total ativado — nem o super admin vê a autoria."
        if enabled else
        "Modo anônimo total desativado — o super admin volta a ver a autoria.",
        "success",
    )
    return redirect(url_for("talents.avaliacoes"))


@talents_bp.route("/talents/<int:talent_id>")
@login_required
def talent_detail(talent_id: int):
    talent = Talent.query.get_or_404(talent_id)

    date_from_str = request.args.get("date_from", "")
    date_to_str   = request.args.get("date_to",   "")

    date_from = None
    date_to   = None
    try:
        if date_from_str:
            date_from = datetime.fromisoformat(date_from_str)
    except ValueError:
        pass
    try:
        if date_to_str:
            date_to = datetime.fromisoformat(date_to_str) + timedelta(days=1)
    except ValueError:
        pass

    hist_q = (
        EventRole.query
        .filter(EventRole.talent_id == talent.id)
        .join(CalendarEvent)
        .filter(EventRole.assigned_at.isnot(None))
        .order_by(CalendarEvent.start_at.desc())
    )
    if date_from:
        hist_q = hist_q.filter(CalendarEvent.start_at >= date_from)
    if date_to:
        hist_q = hist_q.filter(CalendarEvent.start_at < date_to)

    history = hist_q.all()

    total_events    = len({r.event_id for r in history})
    total_earned    = sum(r.cache_value or 0 for r in history)
    characters_done = sorted({r.character_name for r in history})

    # Notas: avaliações recebidas POR este talento (como sujeito de sub-avaliação)
    received_sub_ratings = (
        EventSubRating.query
        .filter_by(subject_talent_id=talent.id)
        .join(EventRating, EventSubRating.rating_id == EventRating.id)
        .order_by(EventRating.submitted_at.desc())
        .all()
    )
    # Avaliações gerais feitas por este talento (como avaliador)
    given_ratings = (
        EventRating.query
        .filter_by(talent_id=talent.id)
        .order_by(EventRating.submitted_at.desc())
        .all()
    )

    return render_template(
        "talent_detail.html",
        talent=talent,
        history=history,
        total_events=total_events,
        total_earned=total_earned,
        characters_done=characters_done,
        date_from=date_from_str,
        date_to=date_to_str,
        can_edit=_can_edit_talent(),
        received_sub_ratings=received_sub_ratings,
        given_ratings=given_ratings,
    )


@talents_bp.route("/talents/<int:talent_id>/notes", methods=["POST"])
@login_required
def save_talent_notes(talent_id: int):
    """Salva anotações internas e o nível de alerta do talento (uso interno)."""
    if not _can_edit_talent():
        abort(403)
    talent = Talent.query.get_or_404(talent_id)
    from app.talents.talent_ops import save_notes

    save_notes(
        talent, notes=request.form.get("notes", ""), warning_level=request.form.get("warning_level", "")
    )
    db.session.commit()
    flash("Anotações salvas.", "success")
    return redirect(url_for("talents.talent_detail", talent_id=talent.id))


@talents_bp.route("/talents/<int:talent_id>/edit", methods=["GET", "POST"])
@login_required
def edit_talent(talent_id: int):
    if not _can_edit_talent():
        abort(403)
    talent = Talent.query.get_or_404(talent_id)
    is_superadmin = any(r.name == RoleName.SUPERADMIN for r in current_user.roles)

    if request.method == "POST":
        f = request.form
        from app.talents.talent_ops import update_talent_fields

        data = {
            "cpf": f.get("cpf", ""),
            "full_name": f.get("full_name", ""),
            "artistic_name": f.get("artistic_name", ""),
            "phone": f.get("phone", ""),
            "email_contact": f.get("email_contact", ""),
            "gender": f.get("gender", ""),
            "race": f.get("race", ""),
            "languages": f.get("languages", ""),
            "skills": f.get("skills", ""),
            "tags": f.get("tags", ""),
            "pix_key": f.get("pix_key", ""),
            "pix_key_secondary": f.get("pix_key_secondary", ""),
            "pix_key_type": f.get("pix_key_type", ""),
            "rg": f.get("rg", ""),
            "passport_status": f.get("passport_status", ""),
            "how_found_us": f.get("how_found_us", ""),
            "worked_before": f.get("worked_before"),
            "car_brand": f.get("car_brand", ""),
            "car_model": f.get("car_model", ""),
            "car_year": f.get("car_year", ""),
            "car_plate": f.get("car_plate", ""),
            "height_cm": f.get("height_cm", ""),
            "clothing_size_top": f.get("clothing_size_top", ""),
            "clothing_size_bottom": f.get("clothing_size_bottom", ""),
            "shoe_size": f.get("shoe_size", ""),
            "birth_date": f.get("birth_date", ""),
            "cnh_expiration": f.get("cnh_expiration", ""),
        }
        cpf_before = talent.cpf
        errors = update_talent_fields(talent, data, is_superadmin=is_superadmin)
        if errors:
            flash(next(iter(errors.values())), "error")
            return render_template("talent_edit.html", talent=talent, is_superadmin=is_superadmin)

        from app.utils import audit
        audit("edit", "talent", talent.id, talent.full_name,
              "Perfil editado" + ("; CPF alterado" if talent.cpf != cpf_before else ""))
        db.session.commit()
        flash("Talento atualizado com sucesso.", "success")
        return redirect(url_for("talents.talent_detail", talent_id=talent.id))

    return render_template("talent_edit.html", talent=talent, is_superadmin=is_superadmin)


@talents_bp.route("/talents/character-suggestions")
@login_required
def character_suggestions():
    from sqlalchemy import func as sqlfunc
    q = request.args.get("q", "").strip()
    if not q or len(q) < 2:
        return jsonify([])
    rows = (
        db.session.query(EventRole.character_name, sqlfunc.count(EventRole.id).label("cnt"))
        .filter(
            EventRole.character_name.ilike(f"%{q}%"),
            EventRole.assigned_at.isnot(None),
            EventRole.talent_id.isnot(None),
        )
        .group_by(EventRole.character_name)
        .order_by(sqlfunc.count(EventRole.id).desc())
        .limit(10)
        .all()
    )
    return jsonify([{"name": r.character_name, "count": r.cnt} for r in rows])


@talents_bp.route("/talents/<int:talent_id>/upload-photo", methods=["POST"])
@login_required
def upload_talent_photo(talent_id: int):
    if not _can_edit_talent():
        abort(403)
    import uuid as _uuid
    from werkzeug.utils import secure_filename
    from app.storage import save_file
    talent = Talent.query.get_or_404(talent_id)
    photo_type = request.form.get("photo_type", "face")  # 'face' | 'full' | 'doc' | 'cnh'
    file = request.files.get("photo")
    if not file or not file.filename:
        flash("Nenhum arquivo selecionado.", "error")
        return redirect(url_for("talents.talent_detail", talent_id=talent_id))
    is_doc = photo_type in ("doc", "cnh")  # documentos aceitam PDF além de imagem
    ext = os.path.splitext(secure_filename(file.filename))[1].lower()
    allowed = (".jpg", ".jpeg", ".png", ".webp", ".pdf") if is_doc else (".jpg", ".jpeg", ".png", ".webp")
    if ext not in allowed:
        msg = "Use JPG, PNG, WEBP ou PDF." if is_doc else "Use JPG, PNG ou WEBP."
        flash(f"Formato não suportado. {msg}", "error")
        return redirect(url_for("talents.talent_detail", talent_id=talent_id))
    subfolder = "talent_docs" if is_doc else "talent_photos"
    filename = f"talent_{talent_id}_{photo_type}_{_uuid.uuid4().hex[:8]}{ext}"
    url_path = save_file(file, subfolder, filename)
    if photo_type == "full":
        talent.photo_full_path = url_path
    elif photo_type == "doc":
        talent.doc_photo_path = url_path
    elif photo_type == "cnh":
        talent.cnh_file_path = url_path
    else:
        talent.photo_face_path = url_path
    db.session.commit()
    flash("Documento atualizado." if is_doc else "Foto atualizada.", "success")
    return redirect(url_for("talents.talent_detail", talent_id=talent_id))


@talents_bp.route("/talents/<int:talent_id>/approve", methods=["POST"])
@login_required
def approve_talent(talent_id: int):
    """Aprova um cadastro pendente (do formulário público), tornando-o ativo no banco."""
    if not _can_edit_talent():
        abort(403)
    talent = Talent.query.get_or_404(talent_id)
    from app.talents.talent_ops import approve_talent_status

    approve_talent_status(talent)
    db.session.commit()
    flash(f"{talent.full_name} aprovado(a) e adicionado(a) ao banco.", "success")
    return redirect(request.referrer or url_for("talents.list_talents", status="pending"))


@talents_bp.route("/talents/<int:talent_id>/reject", methods=["POST"])
@login_required
def reject_talent(talent_id: int):
    """Rejeita/exclui um cadastro pendente."""
    if not _can_edit_talent():
        abort(403)
    talent = Talent.query.get_or_404(talent_id)
    name = talent.full_name
    from app.talents.talent_ops import reject_talent_record

    if not reject_talent_record(talent):
        flash("Só é possível rejeitar cadastros pendentes.", "error")
        return redirect(url_for("talents.talent_detail", talent_id=talent_id))
    db.session.commit()
    flash(f"Cadastro de {name} rejeitado e removido.", "success")
    return redirect(url_for("talents.list_talents", status="pending"))


@talents_bp.route("/talents/<int:talent_id>/reset-password", methods=["POST"])
@login_required
def reset_talent_password(talent_id: int):
    if not _can_edit_talent():
        abort(403)
    import secrets, string
    from app.email_service import send_welcome_email
    talent = Talent.query.get_or_404(talent_id)
    alphabet = string.ascii_letters + string.digits
    new_pw = "".join(secrets.choice(alphabet) for _ in range(8))
    talent.set_password(new_pw)
    talent.must_change_password = True
    db.session.commit()
    email_sent = send_welcome_email(talent, new_pw)
    msg = f"Senha resetada. Nova senha temporária: {new_pw}"
    if email_sent:
        msg += f" — Email enviado para {talent.email_contact}."
    elif talent.email_contact:
        msg += " (falha no envio do email — anote a senha acima)"
    else:
        msg += " (sem email cadastrado — anote a senha acima)"
    flash(msg, "success")
    return redirect(url_for("talents.talent_detail", talent_id=talent_id))


@talents_bp.route("/talents/import", methods=["POST"])
@login_required
def import_talents():
    from datetime import datetime as _dt
    spreadsheet_id, sheet_name = _get_sheet_config()
    try:
        result = import_new_talents_from_sheet(
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name,
            credentials_path=SERVICE_ACCOUNT_JSON,
        )
        imported = result.get("imported", 0)
        # Atualiza registro de sync manual
        state = ImportState.query.filter_by(key="talents_form").first()
        if state:
            state.last_checked_at = _dt.utcnow()
            state.last_import_count = imported
            db.session.commit()
        flash(f"Import finalizado: {imported} novo(s), {result.get('skipped', 0)} ignorado(s).")
        for item in result.get("skipped_details", []):
            flash(f"Ignorado (linha {item['linha']}): {item['nome']} — {item['motivo']}", "warning")
    except FileNotFoundError:
        flash("Credenciais do Google Sheets não encontradas.", "error")
    except Exception as e:
        flash(f"Erro ao importar: {e}", "error")
    return redirect(url_for("talents.list_talents", status="active"))
