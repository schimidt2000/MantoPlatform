"""Serviço do auditor de marketing (feature 256) — fonte única das regras de negócio.

Quatro responsabilidades, todas puras (sem `flask.request`):

* ``agent_context`` — o que a rodada precisa saber do ERP (posts publicados, metas, clientes
  novos, gastos de marketing, clientes com utm) para montar o relatório;
* ``ingest_run`` — ingestão idempotente do histórico (arquivos, fotografias de post, campanhas,
  conta) numa transação só; repetir o mesmo ``run_id`` devolve o resultado guardado;
* ``link_post_metrics`` — casa fotografias com o card do painel (permalink > data > nenhum);
* ``sync_ad_spend`` — mantém o Gasto Extra de reembolso por plataforma e mês civil.

O agente só escreve aqui; nenhuma outra tabela é tocada (FR-019).
"""

from __future__ import annotations

import json
import re
import unicodedata
from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app import db
from app.constants import MARKETING_AD_PLATFORMS, MARKETING_IMPORT_KINDS
from app.models import (
    CalendarEvent,
    Client,
    EventClient,
    MarketingAccountMetric,
    MarketingAdSpendBatch,
    MarketingAgentRun,
    MarketingCampaignMetric,
    MarketingImportFile,
    MarketingPost,
    MarketingPostMetric,
    SpecialExpense,
    User,
)

TOLERANCIA_DIVERGENCIA = Decimal("0.01")
LINK_PERMALINK = "permalink"
LINK_DATE = "date"
LINK_NONE = "none"
STATUS_PUBLICADO = "publicado"
CATEGORIA_MARKETING = "Marketing"
# O export de conteúdo da Meta cobre até 90 dias: cards mais antigos que isso não precisam
# entrar no contexto para o vínculo.
JANELA_POSTS_DIAS = 90
_POST_METRIC_COLS = ("reach", "impressions", "likes", "comments", "saves", "shares", "views")
_CAMPAIGN_INT_COLS = ("impressions", "reach", "clicks", "results", "conversions")


class IngestValidationError(ValueError):
    """Corpo do ``POST /run`` inválido — vira 400 com ``fields`` na rota."""

    def __init__(self, message: str, fields: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.fields = fields or {}


# ── helpers puros ─────────────────────────────────────────────────────────────


def normalize_permalink(url: str | None) -> str:
    """Forma canônica para comparar links: sem esquema, `www.`, querystring, fragmento e barra final."""
    texto = (url or "").strip().lower()
    texto = re.sub(r"^https?://", "", texto)
    texto = texto[4:] if texto.startswith("www.") else texto
    texto = texto.split("#", 1)[0].split("?", 1)[0]
    return texto.rstrip("/")


def normalize_campaign_name(name: str | None) -> str:
    """Minúsculas, sem acento, `-`/`_`/`/` viram espaço — casa `festa-15-anos-sp` com `Festa 15 anos SP`."""
    texto = unicodedata.normalize("NFKD", (name or "").strip().lower())
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"[-_/]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


_SOURCE_PLATFORM = {
    "google": "Google Ads", "adwords": "Google Ads", "googleads": "Google Ads",
    "ig": "Meta Ads", "instagram": "Meta Ads", "fb": "Meta Ads", "facebook": "Meta Ads", "meta": "Meta Ads",
}


def platform_from_utm_source(source: str | None) -> str | None:
    """`utm_source` → plataforma de anúncios, quando o valor for reconhecível; senão None."""
    return _SOURCE_PLATFORM.get((source or "").strip().lower())


def pick_campaign_group(candidatos: list[dict[str, Any]], utm_source: str | None) -> dict[str, Any] | None:
    """Mesma campanha em duas plataformas: decide pelo `utm_source`; sem pista, a de maior gasto."""
    if not candidatos:
        return None
    if len(candidatos) == 1:
        return candidatos[0]
    plataforma = platform_from_utm_source(utm_source)
    por_plataforma = [c for c in candidatos if c["platform"] == plataforma]
    if len(por_plataforma) == 1:
        return por_plataforma[0]
    return max(candidatos, key=lambda c: Decimal(str(c["spend"])))


def month_ref(dia: date) -> str:
    """`YYYY-MM` do dia."""
    return dia.strftime("%Y-%m")


def last_day_of_month(dia: date) -> date:
    """Último dia do mês civil do dia."""
    return dia.replace(day=monthrange(dia.year, dia.month)[1])


def _parse_date(value: Any, campo: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise IngestValidationError(f"Data inválida em {campo}", {campo: "YYYY-MM-DD"}) from exc


def _parse_datetime_opt(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    dt = datetime.fromisoformat(str(value))
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def _parse_window(window: Any) -> tuple[datetime, datetime]:
    if not isinstance(window, list) or len(window) != 2:
        raise IngestValidationError("window deve ser [início, fim] em ISO", {"window": "lista de 2 datas"})
    try:
        inicio, fim = _parse_datetime_opt(window[0]), _parse_datetime_opt(window[1])
    except ValueError as exc:
        raise IngestValidationError("window inválida", {"window": str(exc)}) from exc
    if inicio is None or fim is None or inicio >= fim:
        raise IngestValidationError("window inválida", {"window": "início deve ser anterior ao fim"})
    return inicio, fim


def _dec(value: Any, campo: str) -> Decimal:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise IngestValidationError(f"Valor inválido em {campo}", {campo: "decimal"}) from exc


def _int_opt(value: Any) -> int | None:
    return None if value in (None, "") else int(value)


def resolve_card_holder(email: str | None) -> User:
    """Titular do cartão (recebe o reembolso): precisa ser usuário interno ativo."""
    user = (
        User.query.filter(func.lower(User.email) == (email or "").strip().lower(),
                          User.is_active.is_(True), User.has_access.is_(True)).first()
        if email else None
    )
    if user is None:
        raise PermissionError("Titular do cartão não é usuário interno ativo")
    return user


def _user_ref(user: User) -> dict[str, Any]:
    return {"user_id": user.id, "name": user.name, "email": user.email}


# ── contexto da rodada ────────────────────────────────────────────────────────


def _serialize_post_ref(post: MarketingPost) -> dict[str, Any]:
    return {
        "id": post.id,
        "title": post.title,
        "platform": post.platform,
        "publish_date": post.publish_date.isoformat() if post.publish_date else None,
        "permalink": post.permalink,
        "status": post.status,
    }


def serialize_batch(batch: MarketingAdSpendBatch | None) -> dict[str, Any] | None:
    """Lote de reembolso como a tela de Gastos Extras e o contexto do agente enxergam."""
    if batch is None:
        return None
    return {
        "platform": batch.platform,
        "month_ref": batch.month_ref,
        "reported_total": str(batch.reported_total),
        "frozen": batch.frozen_at is not None,
        "run_id": batch.last_run.run_id if batch.last_run else None,
        "lines": [
            {"campaign_name": ln.campaign_name, "amount": str(ln.amount),
             "clicks": ln.clicks, "results": ln.results}
            for ln in batch.lines
        ],
    }


def batch_for_expense(expense_id: int) -> MarketingAdSpendBatch | None:
    """Lote ligado a um Gasto Extra (ou None — gasto comum)."""
    return MarketingAdSpendBatch.query.filter_by(special_expense_id=expense_id).first()


def batches_for_expenses(expense_ids: list[int]) -> dict[int, MarketingAdSpendBatch]:
    """Lotes de vários gastos numa consulta só (lista de Gastos Extras)."""
    if not expense_ids:
        return {}
    lotes = MarketingAdSpendBatch.query.filter(MarketingAdSpendBatch.special_expense_id.in_(expense_ids)).all()
    return {b.special_expense_id: b for b in lotes}


def _serialize_expense(expense: SpecialExpense) -> dict[str, Any]:
    return {
        "id": expense.id,
        "description": expense.description,
        "amount": str(expense.amount),
        "expense_date": expense.expense_date.isoformat(),
        "status": expense.status,
        "has_receipt": bool(expense.receipt_path),
        "batch": serialize_batch(batch_for_expense(expense.id)),
    }


def _goals_context() -> list[dict[str, Any]]:
    from app.marketing import marketing_ops

    return [
        {"id": g.id, "name": g.name, "target_interval_days": g.target_interval_days,
         **marketing_ops.goal_health(g)}
        for g in marketing_ops.list_goals()
    ]


def attributed_clients(window_start: datetime, window_end: datetime) -> list[dict[str, Any]]:
    """Clientes que entraram na janela com `utm_campaign` e os eventos que fecharam depois."""
    clientes = (
        Client.query.filter(Client.utm_campaign.isnot(None), Client.utm_campaign != "",
                            Client.kommo_created_at >= window_start,
                            Client.kommo_created_at < window_end)
        .order_by(Client.kommo_created_at.asc()).all()
    )
    saida = []
    for cliente in clientes:
        eventos = (
            db.session.query(CalendarEvent)
            .join(EventClient, EventClient.event_id == CalendarEvent.id)
            .filter(EventClient.client_id == cliente.id,
                    CalendarEvent.cancelled_at.is_(None),
                    CalendarEvent.start_at >= cliente.kommo_created_at)
            .all()
        )
        saida.append({
            "client_id": cliente.id,
            "created_at": cliente.kommo_created_at.date().isoformat(),
            "lead_origin": cliente.lead_origin,
            "utm_source": cliente.utm_source,
            "utm_medium": cliente.utm_medium,
            "utm_campaign": cliente.utm_campaign,
            "events": [
                {"event_id": ev.id, "start_at": ev.start_at.isoformat() if ev.start_at else None,
                 "sale_value": str(ev.sale_value) if ev.sale_value is not None else None}
                for ev in eventos
            ],
        })
    return saida


def agent_context(window_start: datetime, window_end: datetime, card_holder_email: str | None) -> dict[str, Any]:
    """Tudo que a rodada precisa do ERP, somente leitura (ver contracts/agent-endpoints.md)."""
    from app.clientes.client_ops import client_metrics

    titular = resolve_card_holder(card_holder_email)
    desde = (window_end - timedelta(days=JANELA_POSTS_DIAS)).date()
    posts = (
        MarketingPost.query.filter(MarketingPost.status == STATUS_PUBLICADO,
                                   MarketingPost.publish_date.isnot(None),
                                   MarketingPost.publish_date >= desde)
        .order_by(MarketingPost.publish_date.desc()).all()
    )
    mes_anterior = (window_end.date().replace(day=1) - timedelta(days=1)).replace(day=1)
    gastos = (
        SpecialExpense.query.filter(SpecialExpense.category == CATEGORIA_MARKETING,
                                    SpecialExpense.expense_date >= mes_anterior)
        .order_by(SpecialExpense.expense_date.desc()).all()
    )
    return {
        "window": [window_start.isoformat(), window_end.isoformat()],
        "card_holder": _user_ref(titular),
        "posts": [_serialize_post_ref(p) for p in posts],
        "goals": _goals_context(),
        "new_clients_by_month": client_metrics()["new_by_month"],
        "marketing_expenses": [_serialize_expense(g) for g in gastos],
        "attributed_clients": attributed_clients(window_start, window_end),
    }


# ── ingestão ──────────────────────────────────────────────────────────────────


def _validate_payload(payload: dict[str, Any]) -> tuple[datetime, datetime]:
    if not isinstance(payload, dict):
        raise IngestValidationError("Corpo deve ser um objeto JSON")
    faltando = {k: "obrigatório" for k in ("run_id", "mode", "window", "card_holder_email") if not payload.get(k)}
    if faltando:
        raise IngestValidationError("Campos obrigatórios ausentes", faltando)
    if payload["mode"] not in ("prod", "local"):
        raise IngestValidationError("mode inválido", {"mode": "prod | local"})
    for lista in ("files", "post_metrics", "campaign_metrics", "account_metrics", "findings"):
        if not isinstance(payload.get(lista, []), list):
            raise IngestValidationError(f"{lista} deve ser lista", {lista: "lista"})
    return _parse_window(payload["window"])


def _register_files(run: MarketingAgentRun, files: list[dict[str, Any]]) -> dict[str, int]:
    contagem = {"accepted": 0, "rejected": 0, "skipped_duplicate": 0}
    for f in files:
        sha = str(f.get("sha256") or "")
        if len(sha) != 64:
            raise IngestValidationError("sha256 inválido", {"files.sha256": f.get("filename", "?")})
        if f.get("status") == "skipped_duplicate" or MarketingImportFile.query.filter_by(sha256=sha).first():
            contagem["skipped_duplicate"] += 1
            continue
        status = "accepted" if f.get("status") == "accepted" else "rejected"
        kind = f.get("kind") if f.get("kind") in MARKETING_IMPORT_KINDS else "unknown"
        db.session.add(MarketingImportFile(
            run_id=run.id, filename=str(f.get("filename") or "?")[:300], sha256=sha, kind=kind,
            period_start=date.fromisoformat(f["period_start"]) if f.get("period_start") else None,
            period_end=date.fromisoformat(f["period_end"]) if f.get("period_end") else None,
            status=status, reason=f.get("reason"), row_count=int(f.get("row_count") or 0),
        ))
        contagem[status] += 1
    return contagem


def _dedupe(rows: list[dict[str, Any]], chave: tuple[str, ...]) -> list[dict[str, Any]]:
    """Última ocorrência vence — `ON CONFLICT` não aceita a mesma chave duas vezes no mesmo INSERT."""
    por_chave = {tuple(r[c] for c in chave): r for r in rows}
    return list(por_chave.values())


def _upsert(model: Any, rows: list[dict[str, Any]], constraint: str, chave: tuple[str, ...]) -> int:
    if not rows:
        return 0
    rows = _dedupe(rows, chave)
    stmt = pg_insert(model).values(rows)
    atualizaveis = {c: stmt.excluded[c] for c in rows[0] if c not in chave}
    db.session.execute(stmt.on_conflict_do_update(constraint=constraint, set_=atualizaveis))
    return len(rows)


def _post_rows(run: MarketingAgentRun, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for i, it in enumerate(items):
        if not it.get("platform") or not it.get("platform_post_id"):
            raise IngestValidationError("post_metrics sem platform/platform_post_id", {f"post_metrics[{i}]": "platform, platform_post_id"})
        rows.append({
            "platform": str(it["platform"])[:20], "platform_post_id": str(it["platform_post_id"])[:80],
            "permalink": (it.get("permalink") or None), "post_type": (it.get("post_type") or None),
            "caption": (it.get("caption") or None),
            "published_at": _parse_datetime_opt(it.get("published_at")),
            "snapshot_date": _parse_date(it.get("snapshot_date"), f"post_metrics[{i}].snapshot_date"),
            **{c: _int_opt(it.get(c)) for c in _POST_METRIC_COLS},
            "extra_json": json.dumps(it["extra"]) if it.get("extra") else None,
            "run_id": run.id,
        })
    return rows


def _campaign_rows(run: MarketingAgentRun, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for i, it in enumerate(items):
        if not it.get("platform") or not it.get("campaign_id") or not it.get("campaign_name"):
            raise IngestValidationError("campaign_metrics incompleto", {f"campaign_metrics[{i}]": "platform, campaign_id, campaign_name"})
        inicio = _parse_date(it.get("period_start"), f"campaign_metrics[{i}].period_start")
        fim = _parse_date(it.get("period_end"), f"campaign_metrics[{i}].period_end")
        rows.append({
            "platform": str(it["platform"])[:20], "campaign_id": str(it["campaign_id"])[:80],
            "campaign_name": str(it["campaign_name"])[:200],
            "period_start": inicio, "period_end": fim, "is_daily": inicio == fim,
            "spend": _dec(it.get("spend", "0"), f"campaign_metrics[{i}].spend"),
            "currency": str(it.get("currency") or "BRL").upper()[:3],
            **{c: _int_opt(it.get(c)) for c in _CAMPAIGN_INT_COLS},
            "result_type": (it.get("result_type") or None),
            "run_id": run.id,
        })
    return rows


def _account_rows(run: MarketingAgentRun, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for i, it in enumerate(items):
        if not it.get("platform"):
            raise IngestValidationError("account_metrics sem platform", {f"account_metrics[{i}]": "platform"})
        rows.append({
            "platform": str(it["platform"])[:20],
            "metric_date": _parse_date(it.get("metric_date"), f"account_metrics[{i}].metric_date"),
            "followers": _int_opt(it.get("followers")), "reach": _int_opt(it.get("reach")),
            "profile_views": _int_opt(it.get("profile_views")),
            "extra_json": json.dumps(it["extra"]) if it.get("extra") else None,
            "run_id": run.id,
        })
    return rows



def _upsert_all(run: MarketingAgentRun, payload: dict[str, Any]) -> dict[str, int]:
    return {
        "post_metrics": _upsert(MarketingPostMetric, _post_rows(run, payload.get("post_metrics", [])),
                                "uq_marketing_post_metrics_snapshot", ("platform", "platform_post_id", "snapshot_date")),
        "campaign_metrics": _upsert(MarketingCampaignMetric, _campaign_rows(run, payload.get("campaign_metrics", [])),
                                    "uq_marketing_campaign_metrics_period", ("platform", "campaign_id", "period_start", "period_end")),
        "account_metrics": _upsert(MarketingAccountMetric, _account_rows(run, payload.get("account_metrics", [])),
                                   "uq_marketing_account_metrics_day", ("platform", "metric_date")),
    }


def _apply_run_totals(run: MarketingAgentRun, arquivos: dict[str, int], upserted: dict[str, int], payload: dict[str, Any]) -> None:
    run.files_accepted, run.files_rejected = arquivos["accepted"], arquivos["rejected"]
    run.posts_upserted = upserted["post_metrics"]
    run.campaigns_upserted = upserted["campaign_metrics"]
    run.account_upserted = upserted["account_metrics"]
    run.findings_json = json.dumps(payload.get("findings", []), ensure_ascii=False)


def ingest_run(payload: dict[str, Any], *, development: bool) -> dict[str, Any]:
    """Ingestão idempotente de uma rodada (ver contracts/agent-endpoints.md, `POST /run`).

    Raises:
        IngestValidationError: corpo inválido ou ``mode=local`` fora de desenvolvimento (400).
        PermissionError: titular do cartão inválido (403) — antes de qualquer escrita.
    """
    inicio, fim = _validate_payload(payload)
    if payload["mode"] == "local" and not development:
        raise IngestValidationError("mode=local só é aceito em ambiente de desenvolvimento", {"mode": "local"})
    titular = resolve_card_holder(payload["card_holder_email"])

    existente = MarketingAgentRun.query.filter_by(run_id=str(payload["run_id"])[:40]).first()
    if existente is not None and existente.result_json:
        return {**json.loads(existente.result_json), "replayed": True}

    run = MarketingAgentRun(run_id=str(payload["run_id"])[:40], mode=payload["mode"],
                            window_start=inicio, window_end=fim, executed_at=datetime.utcnow())
    db.session.add(run)
    db.session.flush()
    arquivos = _register_files(run, payload.get("files", []))
    upserted = _upsert_all(run, payload)
    post_links = link_post_metrics()
    ad_spend, findings_server = sync_ad_spend(run, card_holder=titular)
    _apply_run_totals(run, arquivos, upserted, payload)
    resultado = {
        "run_id": run.run_id, "replayed": False, "files": arquivos, "upserted": upserted,
        "post_links": post_links, "ad_spend": ad_spend, "findings_server": findings_server,
    }
    run.result_json = json.dumps(resultado, ensure_ascii=False)
    db.session.commit()
    return resultado


# ── vínculo post ↔ card ───────────────────────────────────────────────────────



def _card_indexes() -> tuple[dict[str, MarketingPost], dict[tuple[str | None, date | None], list[MarketingPost]]]:
    cards = MarketingPost.query.filter(MarketingPost.status == STATUS_PUBLICADO).all()
    por_link = {normalize_permalink(c.permalink): c for c in cards if c.permalink}
    por_data: dict[tuple[str | None, date | None], list[MarketingPost]] = {}
    for c in cards:
        por_data.setdefault((c.platform, c.publish_date), []).append(c)
    return por_link, por_data


def _resolve_card(foto: MarketingPostMetric, por_link, por_data, posts_por_data) -> tuple[MarketingPost | None, str, list[MarketingPost]]:
    """permalink > data+plataforma (um card E um post naquele dia) > nenhum (com candidatos)."""
    card = por_link.get(normalize_permalink(foto.permalink)) if foto.permalink else None
    if card is not None:
        return card, LINK_PERMALINK, []
    if foto.published_at is None:
        return None, LINK_NONE, []
    chave = (foto.platform, foto.published_at.date())
    candidatos = por_data.get(chave, [])
    if len(candidatos) == 1 and len(posts_por_data.get(chave, set())) == 1:
        return candidatos[0], LINK_DATE, candidatos
    return None, LINK_NONE, candidatos


def _linked_map() -> dict[str, dict[str, Any]]:
    """Todos os posts já casados com card (para o relatório nomear pelo título do card)."""
    fotos = MarketingPostMetric.query.filter(MarketingPostMetric.marketing_post_id.isnot(None)).all()
    return {
        f.platform_post_id: {"card_id": f.marketing_post_id, "title": f.marketing_post.title if f.marketing_post else None,
                             "method": f.link_method}
        for f in fotos
    }


def link_post_metrics() -> dict[str, Any]:
    """Casa fotografias com cards publicados; roda sobre tudo que ainda não está casado por link.

    Preencher o link no card depois melhora o vínculo na rodada seguinte; um vínculo nunca piora.
    """
    por_link, por_data = _card_indexes()
    fotos = MarketingPostMetric.query.filter(MarketingPostMetric.link_method != LINK_PERMALINK).all()
    posts_por_data: dict[tuple[str, date], set[str]] = {}
    for foto in fotos:
        if foto.published_at is not None:
            posts_por_data.setdefault((foto.platform, foto.published_at.date()), set()).add(foto.platform_post_id)
    contagem = {LINK_PERMALINK: 0, LINK_DATE: 0, LINK_NONE: 0}
    sem_vinculo: dict[str, dict[str, Any]] = {}
    for foto in fotos:
        card, metodo, candidatos = _resolve_card(foto, por_link, por_data, posts_por_data)
        foto.marketing_post_id, foto.link_method = (card.id if card else None), metodo
        contagem[metodo] += 1
        if card is None:
            sem_vinculo.setdefault(foto.platform_post_id, {
                "platform_post_id": foto.platform_post_id,
                "published_at": foto.published_at.isoformat() if foto.published_at else None,
                "permalink": foto.permalink, "candidates": [c.id for c in candidatos],
            })
    db.session.flush()
    return {**contagem, "linked": _linked_map(), "unlinked_posts": list(sem_vinculo.values())}


# ── reembolso mensal (US2 — preenchido na fase seguinte) ──────────────────────


def _finding(code: str, severity: str, title: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": severity, "title": title, "details": details}


def _brl(valor: Decimal) -> str:
    inteiro, centavos = f"{valor.quantize(Decimal('0.01')):,.2f}".split(".")
    return f"R$ {inteiro.replace(',', '.')},{centavos}"


def _months_touched(run: MarketingAgentRun) -> set[str]:
    linhas = MarketingCampaignMetric.query.filter_by(run_id=run.id).all()
    return {month_ref(ln.period_end) for ln in linhas} | {month_ref(ln.period_start) for ln in linhas}



def _campaign_rows_for_months(meses: set[str]) -> list[MarketingCampaignMetric]:
    primeiro = min(date.fromisoformat(m + "-01") for m in meses)
    ultimo = last_day_of_month(max(date.fromisoformat(m + "-01") for m in meses))
    return MarketingCampaignMetric.query.filter(
        MarketingCampaignMetric.platform.in_(MARKETING_AD_PLATFORMS),
        MarketingCampaignMetric.period_end >= primeiro, MarketingCampaignMetric.period_start <= ultimo,
    ).all()


def _daily_dates(linhas: list[MarketingCampaignMetric]) -> dict[tuple[str, str], set[date]]:
    dias: dict[tuple[str, str], set[date]] = {}
    for ln in linhas:
        if ln.is_daily:
            dias.setdefault((ln.platform, ln.campaign_id), set()).add(ln.period_start)
    return dias


def _accumulate(grupos: dict, ln: MarketingCampaignMetric, mes: str) -> None:
    grupo = grupos.setdefault((ln.platform, mes, ln.currency), {"total": Decimal(0), "lines": {}})
    grupo["total"] += ln.spend
    linha = grupo["lines"].setdefault(ln.campaign_name, {"amount": Decimal(0), "clicks": 0, "results": 0})
    linha["amount"] += ln.spend
    linha["clicks"] += ln.clicks or 0
    linha["results"] += ln.results or ln.conversions or 0


def _spend_by_month(meses: set[str]) -> tuple[dict[tuple[str, str, str], dict[str, Any]], list[dict[str, Any]]]:
    """(plataforma, mês, moeda) → total e linhas por campanha, com TODO o histórico desses meses.

    Linha agregada que cruza um dia já coberto por linha diária da mesma campanha é ignorada
    (FR-007) e vira achado `periodo_sobreposto` — nunca soma em dobro.
    """
    if not meses:
        return {}, []
    linhas = _campaign_rows_for_months(meses)
    dias = _daily_dates(linhas)
    grupos: dict[tuple[str, str, str], dict[str, Any]] = {}
    sobrepostos: set[tuple[str, str]] = set()
    for ln in linhas:
        cobertos = dias.get((ln.platform, ln.campaign_id), set())
        if not ln.is_daily and any(ln.period_start <= d <= ln.period_end for d in cobertos):
            sobrepostos.add((ln.platform, month_ref(ln.period_end)))
            continue
        mes = month_ref(ln.period_end)
        if mes in meses:
            _accumulate(grupos, ln, mes)
    achados = [
        _finding("periodo_sobreposto", "atencao",
                 f"{p} {m}: export agregado cruza dias já cobertos por linhas diárias — só as diárias contaram",
                 platform=p, month_ref=m)
        for p, m in sorted(sobrepostos)
    ]
    return grupos, achados


def _mes_extenso(mes: str) -> str:
    nomes = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
             "setembro", "outubro", "novembro", "dezembro"]
    ano, num = mes.split("-")
    return f"{nomes[int(num) - 1]}/{ano}"


def _manual_expense(platform: str, mes: str) -> SpecialExpense | None:
    """Gasto de Marketing lançado à mão no mês com a plataforma no nome (e sem lote do agente)."""
    inicio = date.fromisoformat(mes + "-01")
    candidatos = SpecialExpense.query.filter(
        SpecialExpense.category == CATEGORIA_MARKETING,
        SpecialExpense.expense_date >= inicio, SpecialExpense.expense_date <= last_day_of_month(inicio),
        func.lower(SpecialExpense.description).contains(platform.lower()),
    ).all()
    com_lote = {b.special_expense_id for b in MarketingAdSpendBatch.query.filter(
        MarketingAdSpendBatch.special_expense_id.in_([c.id for c in candidatos] or [0])).all()}
    return next((c for c in candidatos if c.id not in com_lote), None)


def _replace_lines(batch: MarketingAdSpendBatch, lines: dict[str, dict[str, Any]]) -> None:
    from app.models import MarketingAdSpendLine

    for antiga in list(batch.lines):
        db.session.delete(antiga)
    for nome, dados in sorted(lines.items(), key=lambda kv: -kv[1]["amount"]):
        db.session.add(MarketingAdSpendLine(batch=batch, campaign_name=nome[:200], amount=dados["amount"],
                                            clicks=dados["clicks"], results=dados["results"]))


def _create_batch(run: MarketingAgentRun, card_holder: User, platform: str, mes: str,
                  grupo: dict[str, Any]) -> dict[str, Any]:
    from app.gastos.gastos_ops import create_expense

    competencia = last_day_of_month(date.fromisoformat(mes + "-01"))
    proximo = (competencia + timedelta(days=1))
    expense = create_expense(
        card_holder,
        {
            "description": f"Anúncios {platform} — {_mes_extenso(mes)} (auditor de marketing)",
            "category": CATEGORIA_MARKETING,
            "amount": grupo["total"],
            "expense_date": competencia,
            "notes": (f"Gerado pela rodada {run.run_id} do auditor de marketing a partir dos relatórios da "
                      f"plataforma. Reembolso previsto para 10/{proximo.strftime('%m/%Y')}. "
                      "Anexar a fatura do cartão antes de aprovar."),
            "disbursement_type": "reembolso",
            "reimburse_user_id": card_holder.id,
            "supplier_name": None,
            "supplier_pix": None,
            "paid_at_creation": False,
        },
        receipt_path=None,
        event_id=None,
        require_receipt=False,
    )
    batch = MarketingAdSpendBatch(platform=platform, month_ref=mes, special_expense_id=expense.id,
                                  reported_total=grupo["total"], last_run_id=run.id)
    db.session.add(batch)
    db.session.flush()
    _replace_lines(batch, grupo["lines"])
    return {"platform": platform, "month_ref": mes, "action": "created", "expense_id": expense.id,
            "amount": str(grupo["total"]), "lines": len(grupo["lines"])}


def _update_or_freeze(run: MarketingAgentRun, batch: MarketingAdSpendBatch, grupo: dict[str, Any],
                      achados: list[dict[str, Any]]) -> dict[str, Any]:
    expense = batch.expense
    batch.reported_total, batch.last_run_id = grupo["total"], run.id
    base = {"platform": batch.platform, "month_ref": batch.month_ref, "expense_id": expense.id}
    if expense.status == "pendente":
        expense.amount = grupo["total"]
        _replace_lines(batch, grupo["lines"])
        return {**base, "action": "updated", "amount": str(grupo["total"]), "lines": len(grupo["lines"])}
    if batch.frozen_at is None:
        batch.frozen_at = datetime.utcnow()
    diverge = abs(Decimal(expense.amount) - grupo["total"]) > TOLERANCIA_DIVERGENCIA
    if diverge:
        achados.append(_finding(
            "gasto_divergente", "critico",
            f"{batch.platform} {_mes_extenso(batch.month_ref)}: lançado {_brl(Decimal(expense.amount))} × "
            f"reportado pela plataforma {_brl(grupo['total'])} (gasto já {expense.status})",
            platform=batch.platform, month_ref=batch.month_ref, expense_id=expense.id))
    return {**base, "action": "frozen_divergent" if diverge else "frozen_ok",
            "erp_amount": str(Decimal(expense.amount).quantize(Decimal("0.01"))), "reported_amount": str(grupo["total"])}



def _skip_currency(platform: str, mes: str, moeda: str, total: Decimal, achados: list[dict[str, Any]]) -> dict[str, Any]:
    achados.append(_finding("moeda_nao_brl", "atencao",
                            f"{platform} {_mes_extenso(mes)}: gasto reportado em {moeda} ({total}) — reembolso não gerado",
                            platform=platform, month_ref=mes, currency=moeda))
    return {"platform": platform, "month_ref": mes, "action": "skipped_currency", "currency": moeda, "reported_amount": str(total)}


def _skip_manual(platform: str, mes: str, manual: SpecialExpense, total: Decimal, achados: list[dict[str, Any]]) -> dict[str, Any]:
    if abs(Decimal(manual.amount) - total) > TOLERANCIA_DIVERGENCIA:
        achados.append(_finding(
            "gasto_manual_existente", "atencao",
            f"{platform} {_mes_extenso(mes)}: já existe gasto lançado à mão ({_brl(Decimal(manual.amount))}) "
            f"diferente do reportado ({_brl(total)}) — nenhum gasto novo foi criado",
            platform=platform, month_ref=mes, expense_id=manual.id))
    return {"platform": platform, "month_ref": mes, "action": "skipped_manual", "expense_id": manual.id,
            "erp_amount": str(Decimal(manual.amount).quantize(Decimal("0.01"))), "reported_amount": str(total)}


def sync_ad_spend(run: MarketingAgentRun, *, card_holder: User) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Mantém um Gasto Extra de Marketing por plataforma × mês civil (FR-014…018).

    Sem lote e sem gasto manual ⇒ cria (pendente, reembolso ao titular, sem comprovante); lote
    com gasto pendente ⇒ atualiza; gasto aprovado/rejeitado ⇒ congela e compara; gasto manual no
    mês ⇒ não cria e aponta divergência; moeda ≠ BRL ⇒ só achado.
    """
    grupos, achados = _spend_by_month(_months_touched(run))
    acoes: list[dict[str, Any]] = []
    for (platform, mes, moeda), grupo in sorted(grupos.items()):
        total = grupo["total"].quantize(Decimal("0.01"))
        grupo["total"] = total
        if moeda != "BRL":
            acoes.append(_skip_currency(platform, mes, moeda, total, achados))
            continue
        batch = MarketingAdSpendBatch.query.filter_by(platform=platform, month_ref=mes).first()
        if batch is not None:
            acoes.append(_update_or_freeze(run, batch, grupo, achados))
            continue
        manual = _manual_expense(platform, mes)
        if manual is not None:
            acoes.append(_skip_manual(platform, mes, manual, total, achados))
            continue
        acoes.append(_create_batch(run, card_holder, platform, mes, grupo))
    db.session.flush()
    return acoes, achados


# ── agregações da tela "Marketing → Desempenho" (US3) ─────────────────────────


def _week_start(dia: date) -> date:
    return dia - timedelta(days=dia.weekday())


def _effective_campaign_rows(inicio: date, fim: date) -> list[MarketingCampaignMetric]:
    """Linhas de campanha no período com a regra de sobreposição (diárias vencem agregadas)."""
    linhas = MarketingCampaignMetric.query.filter(
        MarketingCampaignMetric.platform.in_(MARKETING_AD_PLATFORMS),
        MarketingCampaignMetric.period_end >= inicio, MarketingCampaignMetric.period_start <= fim,
    ).all()
    dias: dict[tuple[str, str], set[date]] = {}
    for ln in linhas:
        if ln.is_daily:
            dias.setdefault((ln.platform, ln.campaign_id), set()).add(ln.period_start)
    efetivas = []
    for ln in linhas:
        cobertos = dias.get((ln.platform, ln.campaign_id), set())
        if not ln.is_daily and any(ln.period_start <= d <= ln.period_end for d in cobertos):
            continue
        efetivas.append(ln)
    return efetivas


def _latest_snapshots(inicio: date, fim: date) -> list[MarketingPostMetric]:
    """Última fotografia de cada post publicado (ou medido) no período."""
    fotos = MarketingPostMetric.query.filter(
        db.or_(
            db.and_(MarketingPostMetric.published_at >= datetime.combine(inicio, datetime.min.time()),
                    MarketingPostMetric.published_at <= datetime.combine(fim, datetime.max.time())),
            db.and_(MarketingPostMetric.published_at.is_(None),
                    MarketingPostMetric.snapshot_date >= inicio, MarketingPostMetric.snapshot_date <= fim),
        )
    ).order_by(MarketingPostMetric.snapshot_date.asc()).all()
    ultima: dict[tuple[str, str], MarketingPostMetric] = {}
    for f in fotos:
        ultima[(f.platform, f.platform_post_id)] = f
    return list(ultima.values())


def _q2(valor: Decimal) -> str:
    return str(valor.quantize(Decimal("0.01")))


def _serialize_snapshot(f: MarketingPostMetric) -> dict[str, Any]:
    return {
        "platform": f.platform, "platform_post_id": f.platform_post_id, "permalink": f.permalink,
        "published_at": f.published_at.isoformat() if f.published_at else None,
        "post_type": f.post_type, "caption": f.caption, "snapshot_date": f.snapshot_date.isoformat(),
        **{c: getattr(f, c) for c in _POST_METRIC_COLS},
        "marketing_post": {"id": f.marketing_post.id, "title": f.marketing_post.title} if f.marketing_post else None,
        "link_method": f.link_method,
    }


def _weekly_series(inicio: date, fim: date, fotos, campanhas, conta, clientes) -> list[dict[str, Any]]:
    semanas: dict[date, dict[str, Any]] = {}
    cursor = _week_start(inicio)
    while cursor <= fim:
        semanas[cursor] = {"week_start": cursor.isoformat(), "reach": 0, "followers": None, "spend": Decimal(0),
                           "clicks": 0, "leads": 0, "events": 0, "posts_published": 0}
        cursor += timedelta(days=7)
    for f in fotos:
        if f.published_at is not None:
            s = semanas.get(_week_start(f.published_at.date()))
            if s is not None:
                s["posts_published"] += 1
                s["reach"] += f.reach or 0
    for ln in campanhas:
        s = semanas.get(_week_start(ln.period_end))
        if s is not None:
            s["spend"] += ln.spend
            s["clicks"] += ln.clicks or 0
    for m in sorted(conta, key=lambda x: x.metric_date):
        s = semanas.get(_week_start(m.metric_date))
        if s is not None and m.followers is not None:
            s["followers"] = m.followers
    for cl in clientes:
        s = semanas.get(_week_start(date.fromisoformat(cl["created_at"])))
        if s is not None:
            s["leads"] += 1
            s["events"] += len(cl["events"])
    return [{**s, "spend": _q2(s["spend"])} for s in semanas.values()]


def _campaign_table(campanhas, clientes) -> list[dict[str, Any]]:
    grupos: dict[tuple[str, str], dict[str, Any]] = {}
    for ln in campanhas:
        g = grupos.setdefault((ln.platform, ln.campaign_name), {
            "platform": ln.platform, "campaign_name": ln.campaign_name, "spend": Decimal(0),
            "impressions": 0, "clicks": 0, "leads": 0, "events": 0, "currency": ln.currency})
        g["spend"] += ln.spend
        g["impressions"] += ln.impressions or 0
        g["clicks"] += ln.clicks or 0
    por_slug: dict[str, list[dict[str, Any]]] = {}
    for g in grupos.values():
        por_slug.setdefault(normalize_campaign_name(g["campaign_name"]), []).append(g)
    for cl in clientes:
        g = pick_campaign_group(por_slug.get(normalize_campaign_name(cl["utm_campaign"]), []), cl.get("utm_source"))
        if g is not None:
            g["leads"] += 1
            g["events"] += len(cl["events"])
    saida = []
    for g in sorted(grupos.values(), key=lambda x: -x["spend"]):
        saida.append({
            **g, "spend": _q2(g["spend"]),
            "cpc": _q2(g["spend"] / g["clicks"]) if g["clicks"] else None,
            "cost_per_lead": _q2(g["spend"] / g["leads"]) if g["leads"] else None,
            "cost_per_event": _q2(g["spend"] / g["events"]) if g["events"] else None,
        })
    return saida


def _cac(fim: date) -> dict[str, Any]:
    from app.clientes.client_ops import client_metrics

    mes = month_ref(fim)
    primeiro = fim.replace(day=1)
    gasto = sum((ln.spend for ln in _effective_campaign_rows(primeiro, last_day_of_month(fim)) if ln.currency == "BRL"), Decimal(0))
    novos = next((m for m in client_metrics()["new_by_month"] if m["month"] == mes), None)
    total = novos["total"] if novos else 0
    return {"month": mes, "spend": _q2(gasto), "new_clients": total,
            "value": _q2(gasto / total) if total else None}


def _runs_table(limite: int = 20) -> list[dict[str, Any]]:
    runs = MarketingAgentRun.query.order_by(MarketingAgentRun.executed_at.desc()).limit(limite).all()
    return [{
        "run_id": r.run_id, "mode": r.mode, "executed_at": r.executed_at.isoformat(),
        "window": [r.window_start.isoformat(), r.window_end.isoformat()],
        "files_accepted": r.files_accepted, "files_rejected": r.files_rejected, "report_sent": r.report_sent,
        "rejected_files": [{"filename": f.filename, "reason": f.reason} for f in r.files if f.status == "rejected"],
    } for r in runs]


def desempenho_summary(inicio: date, fim: date, *, weeks: int | None = None) -> dict[str, Any]:
    """Tudo que a tela "Marketing → Desempenho" mostra (contracts/desempenho-api.md)."""
    clientes = attributed_clients(datetime.combine(inicio, datetime.min.time()),
                                  datetime.combine(fim + timedelta(days=1), datetime.min.time()))
    campanhas = _effective_campaign_rows(inicio, fim)
    fotos = _latest_snapshots(inicio, fim)
    conta = MarketingAccountMetric.query.filter(MarketingAccountMetric.metric_date >= inicio,
                                                MarketingAccountMetric.metric_date <= fim).all()
    tabela = _campaign_table(campanhas, clientes)
    gasto = sum((Decimal(c["spend"]) for c in tabela), Decimal(0))
    if clientes:
        headline = {"kind": "leads", "value": len(clientes),
                    "cost_per_lead": _q2(gasto / len(clientes)) if gasto else None, "fallback_reason": None}
    else:
        headline = {"kind": "alcance", "value": sum(f.reach or 0 for f in fotos), "cost_per_lead": None,
                    "fallback_reason": "nenhum lead do período veio com utm_campaign"}
    return {
        "period": {"start": inicio.isoformat(), "end": fim.isoformat(), "weeks": weeks},
        "headline": headline,
        "weekly": _weekly_series(inicio, fim, fotos, campanhas, conta, clientes),
        "campaigns": tabela,
        "posts": [_serialize_snapshot(f) for f in sorted(fotos, key=lambda x: x.published_at or datetime.min, reverse=True)],
        "goals": _goals_context(),
        "cac": _cac(fim),
        "runs": _runs_table(),
        "empty": MarketingAgentRun.query.count() == 0,
    }
