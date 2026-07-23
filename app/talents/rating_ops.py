"""Núcleo de negócio de Avaliação de Casting (migração 177, US6).

Extraído de `avaliacoes()`/`toggle_modo_anonimo()` (`app/talents/routes.py`) — funções puras
(sem `flask.request`/`render_template`/`flash`), reusadas tanto pela view Jinja quanto pelo
endpoint de API (`app/api/ratings_read.py`, `app/api/ratings_write.py`). Não confundir com
`app/talents/talent_ops.py`, que cobre outro domínio (perfil/aprovação de talento).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app import db
from app.constants import RoleName
from app.models import CalendarEvent, EventRating, EventRole, EventSubRating, SiteSetting, User

RATING_CATEGORIES = [
    ("artista", "Artista"),
    ("som", "Som"),
    ("figurino", "Figurino"),
    ("texto", "Texto"),
    ("coordenacao", "Coordenação"),
    ("maquiagem", "Maquiagem"),
]
RATING_CATEGORY_LABELS = dict(RATING_CATEGORIES)

_PERIOD_PRESETS = {"30d": 30, "90d": 90, "365d": 365}
PERIOD_LABELS = {
    "30d": "últimos 30 dias",
    "90d": "últimos 3 meses",
    "365d": "últimos 12 meses",
}

MONTHS_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]
MONTHS_PT_ABBR = [
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
]


def _now_sp() -> datetime:
    """Agora em horário de Brasília, naïve (mesma convenção dos eventos)."""
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None)


def avg_score(values: list) -> float:
    """Média arredondada a 1 casa; 0.0 para lista vazia."""
    return round(sum(values) / len(values), 1) if values else 0.0


def parse_period(period: str, from_raw: str, to_raw: str) -> tuple:
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


def is_superadmin(user: User) -> bool:
    """True se `user` tem o papel SUPERADMIN."""
    return any(r.name == RoleName.SUPERADMIN for r in user.roles)


def build_overview(args: dict, viewer_is_superadmin: bool) -> dict[str, Any]:
    """Monta o panorama de avaliações (filtros + KPIs + comentários) — mesmo shape usado pela
    view Jinja `avaliacoes()` e pelo endpoint `GET /api/ratings`.

    Args:
        args: mesmas chaves de `request.args` — `event_id`, `cat`, `period`, `from`, `to`,
            `date_mode`.
        viewer_is_superadmin: se o requisitante é SUPERADMIN (controla visibilidade de autoria).

    Returns:
        Dict com `event_groups`, `selected_event` (instância `CalendarEvent` ou `None`), `cat`,
        `period`, `date_mode`, `from_raw`, `to_raw`, `recorte_label`, `has_filters`, `total`,
        `avg_overall`, `events_rated`, `dist`, `dist_max`, `by_category`, `comments`,
        `attention`, `best_events`, `worst_events`, `trend`, `show_authors`, `fully_anonymous`.
    """
    event_id_raw = str(args.get("event_id", "")).strip()
    event_id = int(event_id_raw) if event_id_raw.isdigit() else None

    cat = str(args.get("cat", "")).strip().lower()
    if cat not in RATING_CATEGORY_LABELS:
        cat = ""

    period = str(args.get("period", "all")).strip().lower()
    if period not in ("30d", "90d", "365d", "custom", "all"):
        period = "all"
    from_raw = str(args.get("from", "")).strip()
    to_raw = str(args.get("to", "")).strip()

    date_mode = str(args.get("date_mode", "evento")).strip().lower()
    if date_mode not in ("evento", "avaliacao"):
        date_mode = "evento"
    date_col = EventRating.submitted_at if date_mode == "avaliacao" else CalendarEvent.start_at

    period_start, period_end = (None, None) if event_id else parse_period(period, from_raw, to_raw)

    selected_event = CalendarEvent.query.get(event_id) if event_id else None

    ratings_q = EventRating.query.join(CalendarEvent, EventRating.event_id == CalendarEvent.id)
    if event_id:
        ratings_q = ratings_q.filter(EventRating.event_id == event_id)
    if period_start:
        ratings_q = ratings_q.filter(date_col >= period_start)
    if period_end:
        ratings_q = ratings_q.filter(date_col < period_end)
    ratings = ratings_q.order_by(EventRating.submitted_at.desc()).all()

    rating_ids = [r.id for r in ratings]
    subs = (
        EventSubRating.query.filter(EventSubRating.rating_id.in_(rating_ids)).all()
        if rating_ids
        else []
    )
    rating_by_id = {r.id: r for r in ratings}

    settings = SiteSetting.query.get(1)
    fully_anonymous = bool(settings and settings.ratings_fully_anonymous)
    show_authors = viewer_is_superadmin and not fully_anonymous

    event_functions: dict[tuple[int, int], str] = {}
    if show_authors and ratings:
        from app.calendar.routes import strip_role_prefix

        pairs = {(r.event_id, r.talent_id) for r in ratings}
        roles = EventRole.query.filter(
            EventRole.event_id.in_({e for e, _ in pairs}),
            EventRole.talent_id.in_({t for _, t in pairs}),
        ).all()
        for role in roles:
            key = (role.event_id, role.talent_id)
            if key not in pairs or not role.character_name:
                continue
            nome = strip_role_prefix(role.character_name)
            if not nome:
                continue
            atual = event_functions.get(key)
            event_functions[key] = f"{atual}, {nome}" if atual else nome

    if cat:
        cat_subs = [s for s in subs if s.category == cat and s.score]
        primary = [
            {"score": s.score, "rating": rating_by_id.get(s.rating_id)}
            for s in cat_subs
            if rating_by_id.get(s.rating_id)
        ]
    else:
        primary = [{"score": r.score, "rating": r} for r in ratings if r.score]

    total = len(primary)
    avg_overall = avg_score([p["score"] for p in primary])
    events_rated = len({p["rating"].event_id for p in primary})

    dist = {s: 0 for s in range(1, 6)}
    for p in primary:
        if 1 <= p["score"] <= 5:
            dist[p["score"]] += 1
    dist_max = max(dist.values()) if dist else 0

    by_category = []
    if not cat:
        for key, label in RATING_CATEGORIES:
            cat_scores = [s.score for s in subs if s.category == key and s.score]
            if cat_scores:
                by_category.append({
                    "key": key,
                    "label": label,
                    "avg": avg_score(cat_scores),
                    "count": len(cat_scores),
                })

    def _comment_item(score, text, rating, cat_key="", subject=None):
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
            "cat_label": RATING_CATEGORY_LABELS.get(cat_key, "Geral"),
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
            comments.append(
                _comment_item(s.score, s.comment.strip(), r, cat_key=s.category, subject=s.subject_talent)
            )
    comments.sort(key=lambda c: c["submitted_at"] or datetime.min, reverse=True)
    if not event_id:
        comments = comments[:30]

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
            attention.append(
                _comment_item(s.score, (s.comment or "").strip(), r, cat_key=s.category, subject=s.subject_talent)
            )
    attention.sort(key=lambda c: c["submitted_at"] or datetime.min, reverse=True)
    attention = attention[:10]

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
                    "avg": avg_score(data["scores"]),
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
                "label": f"{MONTHS_PT_ABBR[m - 1]}/{str(y)[2:]}",
                "avg": avg_score(scores),
                "count": len(scores),
            }
            for (y, m), scores in sorted(per_month.items())
        ]

    rated_q = db.session.query(CalendarEvent.id, CalendarEvent.title, CalendarEvent.start_at).join(
        EventRating, EventRating.event_id == CalendarEvent.id
    )
    if period_start:
        rated_q = rated_q.filter(date_col >= period_start)
    if period_end:
        rated_q = rated_q.filter(date_col < period_end)
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
            label = f"{MONTHS_PT[row.start_at.month - 1]} de {row.start_at.year}"
        else:
            label = "Sem data"
        if not event_groups or event_groups[-1]["label"] != label:
            event_groups.append({"label": label, "events": []})
        event_groups[-1]["events"].append({"id": row.id, "title": row.title, "start_at": row.start_at})

    recorte_parts = []
    if cat:
        recorte_parts.append(RATING_CATEGORY_LABELS[cat])
    if not event_id:
        if period in PERIOD_LABELS:
            recorte_parts.append(PERIOD_LABELS[period])
        elif period == "custom" and (period_start or period_end):
            ini = period_start.strftime("%d/%m/%Y") if period_start else "…"
            fim = (period_end - timedelta(days=1)).strftime("%d/%m/%Y") if period_end else "…"
            recorte_parts.append(f"{ini} – {fim}")
        if date_mode == "avaliacao" and period != "all":
            recorte_parts.append("por data da avaliação")

    return {
        "event_groups": event_groups,
        "selected_event": selected_event,
        "event_id": event_id,
        "cat": cat,
        "cat_label": RATING_CATEGORY_LABELS.get(cat, ""),
        "categories": RATING_CATEGORIES,
        "period": period,
        "date_mode": date_mode,
        "from_raw": from_raw,
        "to_raw": to_raw,
        "recorte_label": " · ".join(recorte_parts),
        "has_filters": bool(cat or event_id or period != "all"),
        "total": total,
        "avg_overall": avg_overall,
        "events_rated": events_rated,
        "dist": dist,
        "dist_max": dist_max,
        "by_category": by_category,
        "comments": comments,
        "attention": attention,
        "best_events": best_events,
        "worst_events": worst_events,
        "trend": trend,
        "show_authors": show_authors,
        "fully_anonymous": fully_anonymous,
    }


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def serialize_overview(overview: dict[str, Any]) -> dict[str, Any]:
    """Converte o dict de `build_overview()` (com objetos `CalendarEvent`/`datetime`) em JSON puro."""
    selected_event = overview["selected_event"]

    def _comment(c: dict) -> dict:
        return {**c, "event_date": _iso(c["event_date"]), "submitted_at": _iso(c["submitted_at"])}

    def _ranked_event(e: dict) -> dict:
        return {**e, "start_at": _iso(e["start_at"])}

    return {
        "event_groups": [
            {
                "label": g["label"],
                "events": [
                    {"id": ev["id"], "title": ev["title"], "start_at": _iso(ev["start_at"])}
                    for ev in g["events"]
                ],
            }
            for g in overview["event_groups"]
        ],
        "selected_event": (
            {"id": selected_event.id, "title": selected_event.title, "start_at": _iso(selected_event.start_at)}
            if selected_event
            else None
        ),
        "event_id": overview["event_id"],
        "cat": overview["cat"],
        "cat_label": overview["cat_label"],
        "categories": [{"key": k, "label": lbl} for k, lbl in overview["categories"]],
        "period": overview["period"],
        "date_mode": overview["date_mode"],
        "from_raw": overview["from_raw"],
        "to_raw": overview["to_raw"],
        "recorte_label": overview["recorte_label"],
        "has_filters": overview["has_filters"],
        "total": overview["total"],
        "avg_overall": overview["avg_overall"],
        "events_rated": overview["events_rated"],
        "dist": overview["dist"],
        "dist_max": overview["dist_max"],
        "by_category": overview["by_category"],
        "comments": [_comment(c) for c in overview["comments"]],
        "attention": [_comment(c) for c in overview["attention"]],
        "best_events": [_ranked_event(e) for e in overview["best_events"]],
        "worst_events": [_ranked_event(e) for e in overview["worst_events"]],
        "trend": overview["trend"],
        "show_authors": overview["show_authors"],
        "fully_anonymous": overview["fully_anonymous"],
    }


def set_anonymous_mode(enabled: bool, actor: User) -> None:
    """Liga/desliga o modo anônimo total das avaliações (feature 056)."""
    from app.models import AuditLog

    settings = SiteSetting.query.get(1)
    if not settings:
        settings = SiteSetting(id=1)
        db.session.add(settings)
    settings.ratings_fully_anonymous = enabled
    db.session.add(
        AuditLog(
            actor_name=actor.name,
            entity_type="settings",
            entity_id=1,
            action="ratings_fully_anonymous_on" if enabled else "ratings_fully_anonymous_off",
            detail=f"Modo anônimo total das avaliações {'ativado' if enabled else 'desativado'}.",
        )
    )
    db.session.commit()
