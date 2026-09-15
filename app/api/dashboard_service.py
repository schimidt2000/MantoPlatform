"""Lógica de agregação do resumo da home/dashboard — fonte única (Princípio I).

As mesmas consultas de tarefas de casting/figurino/dispensados são usadas pela view Jinja
`home` (`app/__init__.py`) e pelo endpoint JSON `GET /api/dashboard`. Extraídas aqui para
não existirem em duas versões paralelas quando a Fundação (feature 144) migra a home.
"""

from datetime import date, datetime, timedelta
from typing import Any

from flask import current_app
from sqlalchemy import and_, func, not_

from app import db
from app.constants import EVENT_TYPE_SHOW, RoleName, now_sp
from app.models import CalendarEvent, EventRole, SiteSetting


def dashboard_cutoff() -> datetime:
    """Data de corte das tarefas: `release_date` configurada ou hoje."""
    settings = SiteSetting.query.get(1)
    release = settings.release_date if settings and settings.release_date else date.today()
    return datetime(release.year, release.month, release.day)


def _base_filters(cutoff: datetime) -> dict[str, Any]:
    """Filtros compartilhados pelas consultas de tarefas (mesmos da view `home`)."""
    from app.calendar.routes import PRESENCE_CHARACTER

    return {
        "not_presence": EventRole.character_name != PRESENCE_CHARACTER,
        "exclude_ensaios": not_(CalendarEvent.title.like("🟧 ENSAIO%")),
        "future_events": CalendarEvent.start_at >= cutoff,
        "not_dismissed": EventRole.dismissed_at.is_(None),
        # Evento cancelado (feature 224) não gera tarefa nenhuma: escalar, cobrar ou fechar
        # figurino de um evento que não vai acontecer é trabalho jogado fora.
        "not_cancelled": CalendarEvent.cancelled_at.is_(None),
    }


def compute_casting_tasks(cutoff: datetime) -> dict[str, Any]:
    """Pendências, convites recusados e contagens de casting (exclui presença/dispensados)."""
    f = _base_filters(cutoff)
    pending = (
        EventRole.query.filter(EventRole.talent_id.is_(None), f["not_presence"], f["not_dismissed"])
        .join(CalendarEvent)
        .filter(f["exclude_ensaios"], f["future_events"], f["not_cancelled"])
        .order_by(CalendarEvent.start_at.asc())
        .all()
    )
    rejected_invites = (
        EventRole.query.filter(EventRole.invite_status == "rejected")
        .join(CalendarEvent)
        .filter(f["exclude_ensaios"], f["future_events"], f["not_cancelled"])
        .order_by(CalendarEvent.start_at.asc())
        .all()
    )
    total = (
        EventRole.query.filter(f["not_presence"], f["not_dismissed"])
        .join(CalendarEvent)
        .filter(f["exclude_ensaios"], f["future_events"], f["not_cancelled"])
        .count()
    )
    done = (
        EventRole.query.filter(
            EventRole.talent_id.isnot(None),
            EventRole.invite_status != "rejected",
            f["not_presence"],
            f["not_dismissed"],
        )
        .join(CalendarEvent)
        .filter(f["exclude_ensaios"], f["future_events"], f["not_cancelled"])
        .count()
    )
    return {
        "pending": pending,
        "rejected_invites": rejected_invites,
        "unconfirmed": compute_unconfirmed_invites(),
        "total": total,
        "done": done,
    }


def compute_unconfirmed_invites() -> list[EventRole]:
    """Escalações futuras em que a pessoa ainda não confirmou (feature 231).

    Delegado a `app.calendar.invite_reminders` de propósito: a **mesma** lista alimenta este
    painel e a cobrança automática por e-mail. Se cada um tivesse a sua consulta, o painel
    mostraria alguém que o robô já cobrou — ou pior, o contrário.
    """
    from app.calendar.invite_reminders import escalacoes_sem_confirmacao

    return escalacoes_sem_confirmacao()


def compute_figurino_tasks(cutoff: datetime) -> dict[str, Any]:
    """Pendências e contagens de figurino (roles com talento, sem figurino, exceto extras)."""
    f = _base_filters(cutoff)
    pending = (
        EventRole.query.filter(
            EventRole.talent_id.isnot(None),
            EventRole.figurino_done_at.is_(None),
            EventRole.invite_status != "rejected",
            EventRole.role_type != "extra",
        )
        .join(CalendarEvent)
        .filter(f["exclude_ensaios"], f["future_events"], f["not_cancelled"])
        .order_by(CalendarEvent.start_at.asc())
        .all()
    )
    total = (
        EventRole.query.filter(
            EventRole.talent_id.isnot(None),
            EventRole.invite_status != "rejected",
            EventRole.role_type != "extra",
        )
        .join(CalendarEvent)
        .filter(f["exclude_ensaios"], f["future_events"], f["not_cancelled"])
        .count()
    )
    return {"pending": pending, "total": total, "done": total - len(pending)}


def compute_dismissed_casting_tasks(cutoff: datetime) -> list[EventRole]:
    """Cargos de casting dispensados (feature 108) — só o SUPERADMIN vê e restaura."""
    f = _base_filters(cutoff)
    return (
        EventRole.query.filter(EventRole.dismissed_at.isnot(None), f["not_presence"])
        .join(CalendarEvent)
        .filter(f["exclude_ensaios"], f["future_events"], f["not_cancelled"])
        .order_by(EventRole.dismissed_at.desc())
        .all()
    )


def compute_ensaio_tasks(cutoff: datetime) -> dict[str, Any]:
    """Pendências da equipe de ensaio — mesmas quatro listas da home Jinja aposentada (206).

    - ``pending``: shows futuros que precisam de ensaio e ainda não têm nenhum agendado;
    - ``scheduled``: shows futuros com ensaio(s) agendado(s);
    - ``orphans``: eventos ENSAIO (desde o corte) cujo show pai não existe mais (feature 057);
    - ``pending_presence``: vaga 'Técnico de Som (Presença)' sem talento em shows futuros.
    """
    from app.calendar.routes import PRESENCE_CHARACTER

    exclude_ensaios = not_(CalendarEvent.title.like("🟧 ENSAIO%"))
    now = datetime.utcnow()

    future_shows = (
        CalendarEvent.query
        .filter(
            db.or_(
                CalendarEvent.needs_rehearsal == True,  # noqa: E712 — expressão SQLAlchemy
                CalendarEvent.event_type == "SHOW",
            ),
            CalendarEvent.event_type != "ENSAIO",
            CalendarEvent.cancelled_at.is_(None),
            CalendarEvent.start_at >= now,
        )
        .order_by(CalendarEvent.start_at.asc())
        .all()
    )
    pending = [e for e in future_shows if not e.ensaios]
    scheduled = [e for e in future_shows if e.ensaios]

    # `parent is None` cobre FK nulo e FK apontando para show já removido (feature 057);
    # corte na data de início do sistema para não poluir com órfãos antigos (feature 060).
    orphans = [
        e for e in CalendarEvent.query
        .filter(
            CalendarEvent.event_type == "ENSAIO",
            CalendarEvent.cancelled_at.is_(None),
            CalendarEvent.start_at >= cutoff,
        )
        .order_by(CalendarEvent.start_at.asc())
        .all()
        if e.parent is None
    ]

    # Cinto de segurança (feature 239): a vaga de presença só é tarefa em evento SHOW e não
    # cancelado. A remoção automática na troca de tipo já limpa a vaga, mas esta consulta era a
    # única das tarefas sem `not_cancelled` — e sem filtro de tipo nenhum, então qualquer vaga
    # órfã sobrevivente seguia cobrando a equipe de ensaio para sempre.
    pending_presence = (
        EventRole.query
        .filter(EventRole.talent_id.is_(None), EventRole.character_name == PRESENCE_CHARACTER)
        .join(CalendarEvent)
        .filter(
            exclude_ensaios,
            CalendarEvent.start_at >= now,
            CalendarEvent.event_type == EVENT_TYPE_SHOW,
            CalendarEvent.cancelled_at.is_(None),
        )
        .order_by(CalendarEvent.start_at.asc())
        .all()
    )

    return {
        "pending": pending,
        "scheduled": scheduled,
        "orphans": orphans,
        "pending_presence": pending_presence,
    }


def _serialize_event_ref(event: CalendarEvent) -> dict[str, Any]:
    """Referência enxuta de um evento (sem cargo) para o painel de ensaio."""
    return {
        "event_id": event.id,
        "event_title": event.title,
        "start_at": event.start_at.isoformat() if event.start_at else None,
    }


def serialize_ensaio_summary(raw: dict[str, Any]) -> dict[str, Any]:
    """Serializa `compute_ensaio_tasks` para o JSON do dashboard."""
    return {
        "pending": [_serialize_event_ref(e) for e in raw["pending"]],
        "scheduled": [
            {
                **_serialize_event_ref(e),
                "ensaios": [
                    en.start_at.isoformat() if en.start_at else None
                    for en in sorted(e.ensaios, key=lambda x: (x.start_at is None, x.start_at))
                ],
            }
            for e in raw["scheduled"]
        ],
        "orphans": [_serialize_event_ref(e) for e in raw["orphans"]],
        "pending_presence": [serialize_task_ref(r) for r in raw["pending_presence"]],
    }


def serialize_task_ref(role: EventRole) -> dict[str, Any]:
    """Referência enxuta de um cargo/evento para o JSON do dashboard (data-model.md)."""
    event = role.event
    return {
        "role_id": role.id,
        "event_id": role.event_id,
        "event_title": event.title if event else "",
        "character_name": role.character_name,
        "start_at": event.start_at.isoformat() if event and event.start_at else None,
    }


def serialize_unconfirmed_ref(role: EventRole) -> dict[str, Any]:
    """Como `serialize_task_ref`, mais o que o casting precisa para **cobrar** (feature 231).

    Vai o nome de quem falta confirmar, a situação do convite (`pending` = enviado e sem resposta;
    `None` = nunca enviado, e aí quem tem que agir é o casting) e o WhatsApp já no formato com
    DDI. Sem o telefone o painel seria um relatório; com ele, é um toque até a cobrança — que é o
    que foi pedido. O número já é visível para casting na tela do evento, então nada de novo é
    exposto aqui.
    """
    talent = role.talent
    return {
        **serialize_task_ref(role),
        "talent_id": role.talent_id,
        "talent_name": (talent.artistic_name or talent.full_name) if talent else "—",
        "invite_status": role.invite_status,
        "whatsapp": (talent.whatsapp_number or None) if talent else None,
        "reminder_count": role.invite_reminder_count or 0,
        "reminder_at": role.invite_reminder_at.isoformat() if role.invite_reminder_at else None,
    }


def compute_performance(start_dt: datetime | None, end_dt: datetime | None) -> dict[str, Any]:
    """Agregado de Performance (SUPERADMIN): casting/figurino done/total e entrada total.

    Extraída de `app/__init__.py::home()` (linhas ~528-576) — fonte única para Jinja e API.

    Args:
        start_dt: início do período (inclusive), ou ``None`` se o período for inválido.
        end_dt: fim do período (exclusive), ou ``None`` se o período for inválido.

    Returns:
        Dicionário com `casting_total`, `casting_done`, `figurino_total`, `figurino_done` e
        `money_total` (zerados quando o período é inválido).
    """
    empty = {
        "casting_total": 0,
        "casting_done": 0,
        "figurino_total": 0,
        "figurino_done": 0,
        "money_total": 0.0,
    }
    if start_dt is None or end_dt is None:
        return empty

    exclude_ensaios = not_(CalendarEvent.title.like("🟧 ENSAIO%"))
    perf_filter = and_(
        CalendarEvent.start_at >= start_dt, CalendarEvent.start_at < end_dt, exclude_ensaios
    )
    casting_total = EventRole.query.join(CalendarEvent).filter(perf_filter).count()
    casting_done = (
        EventRole.query.filter(EventRole.assigned_at.isnot(None))
        .join(CalendarEvent)
        .filter(perf_filter)
        .count()
    )
    figurino_total = casting_total
    figurino_done = (
        EventRole.query.filter(EventRole.figurino_done_at.isnot(None))
        .join(CalendarEvent)
        .filter(perf_filter)
        .count()
    )
    # A vaga "Técnico de Som (Presença)" não entra na entrada total (feature 239, decisão 10):
    # ela nunca tem cachê, e o mesmo `not_presence` já vale para as tarefas de casting/figurino.
    from app.calendar.routes import PRESENCE_CHARACTER

    money_total = (
        db.session.query(func.coalesce(func.sum(EventRole.cache_value), 0))
        .join(CalendarEvent)
        .filter(
            perf_filter,
            EventRole.assigned_at.isnot(None),
            EventRole.character_name != PRESENCE_CHARACTER,
        )
        .scalar()
    )
    return {
        "casting_total": casting_total,
        "casting_done": casting_done,
        "figurino_total": figurino_total,
        "figurino_done": figurino_done,
        "money_total": float(money_total),
    }


def resolve_performance_period(
    perf_range: str, perf_start: str | None, perf_end: str | None
) -> tuple[datetime | None, datetime | None]:
    """Resolve `perf_range`/`perf_start`/`perf_end` (query params) num intervalo `[start, end)`.

    Mesma regra do Jinja: `"30"` = últimos 30 dias; `"custom"` exige `perf_start`/`perf_end`
    ISO válidos com `start <= end`; qualquer outro valor (inclusive `"7"`/ausente) = últimos 7
    dias. Datas inválidas ou fora de ordem retornam ``(None, None)`` (fallback silencioso).
    """
    if perf_range == "30":
        end_dt = datetime.utcnow()
        return end_dt - timedelta(days=30), end_dt
    if perf_range == "custom":
        if not perf_start or not perf_end:
            return None, None
        try:
            start_dt = datetime.fromisoformat(perf_start)
            end_dt = datetime.fromisoformat(perf_end) + timedelta(days=1)
        except ValueError:
            return None, None
        if start_dt > end_dt:
            return None, None
        return start_dt, end_dt
    end_dt = datetime.utcnow()
    return end_dt - timedelta(days=7), end_dt


def _is_real_superadmin(user: Any) -> bool:
    return any(r.name == RoleName.SUPERADMIN for r in user.roles)


def _effective_has_role(user: Any, impersonate: str | None, name: str) -> bool:
    """Papel efetivo, respeitando a impersonação do SUPERADMIN (mesma lógica da view home)."""
    if impersonate and _is_real_superadmin(user):
        return impersonate.upper() == name.upper()
    return any(r.name.upper() == name.upper() for r in user.roles)


def _pode_criar_evento(user: Any, impersonate: str | None, is_superadmin: bool) -> bool:
    """Se o papel EFETIVO cria evento (`_CAN_CREATE`): "Ver como FINANCEIRO" vê "Abrir".

    Decide a ação principal das linhas comerciais da Home — criar o evento a partir do formulário
    (298) e pôr o valor na aba Comercial (299): o `PATCH /comercial` tem o mesmo gate da criação.
    A lista de papéis mora na agenda, não aqui.
    """
    from app.calendar.routes import _CAN_CREATE

    return is_superadmin or any(
        _effective_has_role(user, impersonate, papel) for papel in _CAN_CREATE
    )


def _bloco(nome: str, montar: Any) -> Any:
    """Monta um painel da Home isolando a falha dele (feature 271).

    A Home é a tela de entrada do sistema: um painel que estoura não pode derrubar a página
    inteira — era o que produzia "Não foi possível carregar o resumo", uma tela vermelha que
    **não diz qual** dos oito painéis quebrou nem por quê.

    Com o isolamento, o painel problemático vem `null` (a seção simplesmente não renderiza, que
    é o mesmo contrato de "sem permissão") e o traceback vai para o log com o NOME do painel.
    Da próxima ocorrência, o log responde a pergunta que hoje não tem resposta.

    O `rollback` é obrigatório: se a falha veio de escrita, a sessão fica em transação abortada
    e os painéis seguintes falhariam em cascata por um erro que não é deles.
    """
    try:
        return montar()
    except Exception:  # noqa: BLE001 — a Home degrada, não cai
        db.session.rollback()
        current_app.logger.exception("[dashboard] painel '%s' falhou; Home segue sem ele", nome)
        return None


def build_dashboard_summary(
    user: Any,
    impersonate: str | None,
    perf_range: str = "7",
    perf_start: str | None = None,
    perf_end: str | None = None,
) -> dict[str, Any]:
    """Monta o resumo do dashboard para o endpoint JSON, filtrado por papel.

    Args:
        user: Usuário autenticado (``current_user``).
        impersonate: Papel impersonado na sessão, ou ``None``.
        perf_range: período do painel Performance (``"7"``, ``"30"`` ou ``"custom"``).
        perf_start: início do período customizado (ISO date), quando ``perf_range="custom"``.
        perf_end: fim do período customizado (ISO date), quando ``perf_range="custom"``.

    Returns:
        Dicionário no formato de `data-model.md` (seções ``None`` = sem permissão). O bloco
        ``comercial`` (feature 299) segue `specs/299-sem-valor-cobrancas/contracts/
        dashboard-comercial.md`: para quem tem o papel ele nunca vem ``None`` por falha interna —
        a lista que falhou vem ``None`` e a tela mostra o aviso, em vez de sumir com o painel.
    """
    cutoff = dashboard_cutoff()
    is_superadmin = _is_real_superadmin(user) and not impersonate
    show_casting = _effective_has_role(user, impersonate, RoleName.CASTING) or is_superadmin
    show_figurino = _effective_has_role(user, impersonate, RoleName.FIGURINO) or is_superadmin
    show_financeiro = _effective_has_role(user, impersonate, RoleName.FINANCEIRO) or is_superadmin
    show_comercial = (
        _effective_has_role(user, impersonate, RoleName.COMERCIAL)
        or show_financeiro
        or is_superadmin
    )

    def _painel_casting() -> dict[str, Any]:
        raw = compute_casting_tasks(cutoff)
        return {
            "pending": [serialize_task_ref(r) for r in raw["pending"]],
            "rejected_invites": [serialize_task_ref(r) for r in raw["rejected_invites"]],
            "unconfirmed": [serialize_unconfirmed_ref(r) for r in raw["unconfirmed"]],
            "total": raw["total"],
            "done": raw["done"],
        }

    casting = _bloco("casting", _painel_casting) if show_casting else None

    def _painel_figurino() -> dict[str, Any]:
        raw_fig = compute_figurino_tasks(cutoff)
        return {
            "pending": [serialize_task_ref(r) for r in raw_fig["pending"]],
            "total": raw_fig["total"],
            "done": raw_fig["done"],
        }

    figurino = _bloco("figurino", _painel_figurino) if show_figurino else None

    # Ensaio (restaurado na 206 — as quatro listas viviam só na home Jinja aposentada).
    # Mesmo gate da home: ENSAIO ou superadmin (CASTING vê materiais no evento, não o painel).
    show_ensaio = _effective_has_role(user, impersonate, RoleName.ENSAIO) or is_superadmin
    ensaio = (
        _bloco("ensaio", lambda: serialize_ensaio_summary(compute_ensaio_tasks(cutoff)))
        if show_ensaio
        else None
    )

    def _painel_recorrentes() -> dict[str, Any]:
        from app.gastos.gastos_ops import ensure_recurring_entries, recurring_alerts

        today = date.today()
        # Único bloco do dashboard que ESCREVE no banco (geração preguiçosa dos lançamentos do
        # mês) — e, portanto, o único que pode falhar por disputa entre requisições simultâneas.
        ensure_recurring_entries(today.year, today.month)
        return {
            "recurring_expense_alerts": [_serialize_alert(a) for a in recurring_alerts(today)]
        }

    financeiro = _bloco("recorrentes", _painel_recorrentes) if show_financeiro else None

    def _painel_comercial() -> dict[str, Any]:
        # Feature 299: Cobranças e "Sem valor" saem do mesmo núcleo da página do evento — o grupo
        # é uma venda só. O corte é a data de início (`corte_dia_sp`), o mesmo dos formulários,
        # e não o `cutoff` dos painéis de operação (que vira hoje quando a configuração está vazia).
        from app.financeiro import cobranca_ops
        from app.formularios.formularios_ops import corte_dia_sp

        hoje = now_sp().date()
        bloco: dict[str, Any] = {
            "corte": None,
            "pode_editar_venda": _pode_criar_evento(user, impersonate, is_superadmin),
            "pending_payments": [],
            "cobrancas_resumo": None,
            "sem_valor": None,
        }
        try:
            corte = corte_dia_sp()
            bloco["corte"] = corte.isoformat()
            vendas = cobranca_ops.vendas_desde(corte)
            linhas = cobranca_ops.listar_cobrancas(vendas, hoje)
        except Exception:  # noqa: BLE001 — as duas listas viram aviso; o painel não some (R47)
            db.session.rollback()
            current_app.logger.exception("[dashboard] vendas da Home falharam; listas em aviso")
            return bloco
        bloco["pending_payments"] = linhas
        bloco["cobrancas_resumo"] = _bloco(
            "cobrancas_resumo", lambda: cobranca_ops.resumo_das_cobrancas(linhas)
        )
        bloco["sem_valor"] = _bloco("sem_valor", lambda: cobranca_ops.listar_sem_valor(vendas, hoje))
        return bloco

    # O `_bloco` de fora fica só como rede para defeito no próprio envelope: falha das vendas e
    # das listas já vira `None` NA LISTA, e `comercial: null` continua significando "sem permissão".
    comercial = _bloco("comercial", _painel_comercial) if show_comercial else None

    # Mesmo conjunto de `_require_vendas` (COMERCIAL ∪ FINANCEIRO ∪ SUPERADMIN), em variável
    # própria para os dois gates poderem divergir depois sem ninguém se perder.
    show_formularios = show_comercial

    def _painel_formularios() -> dict[str, Any]:
        from app.formularios import destino_ops

        # Feature 298: a lista dos formulários que chegaram desde o corte e ainda não têm destino,
        # no lugar dos quatro números (que contavam o histórico importado e diziam 1.347).
        # As contagens vêm do MESMO núcleo dos cartões de /formularios — não podem divergir.
        bloco = destino_ops.listar_sem_destino()
        bloco["pode_criar_evento"] = _pode_criar_evento(user, impersonate, is_superadmin)
        return bloco

    formularios = _bloco("formularios", _painel_formularios) if show_formularios else None

    performance: dict[str, Any] | None = None
    if is_superadmin:
        start_dt, end_dt = resolve_performance_period(perf_range, perf_start, perf_end)
        if start_dt is not None and end_dt is not None:
            perf = compute_performance(start_dt, end_dt)
            # `end_dt` é exclusive (para a query); `perf_range="custom"` já entra com +1 dia
            # para cobrir o dia inteiro (ver `resolve_performance_period`) — subtrai de volta
            # só para exibição, sem afetar a contagem.
            display_end = end_dt - timedelta(days=1) if perf_range == "custom" else end_dt
            performance = {
                "range": perf_range,
                "start": start_dt.date().isoformat(),
                "end": display_end.date().isoformat(),
                **perf,
            }

    dismissed = (
        [serialize_task_ref(r) for r in compute_dismissed_casting_tasks(cutoff)]
        if is_superadmin
        else []
    )

    # Painel PESSOAL (feature 225) — o único da home cujo gate é a identidade, não o papel:
    # quem tem peça de figurino sob sua responsabilidade precisa ver isso, seja qual for o papel,
    # e o "Ver como" de um super admin não muda de quem são os pedidos. Devolve None quando a
    # pessoa não é responsável por nada, e aí o React simplesmente não desenha o painel — mesmo
    # contrato das outras seções.
    from app.figurino.producao_ops import resumo_home as _producao_resumo_home
    from app.figurino.producao_ops import resumo_setor as _producao_resumo_setor

    minhas_pecas = _producao_resumo_home(user)
    # Caixa de entrada do setor (225b): pedidos abertos que ninguém assumiu. Este é por PAPEL —
    # manutenção quase sempre nasce órfã, porque quem relata o defeito recebeu o feedback do
    # evento e não é quem vai consertar.
    fila_oficina = _producao_resumo_setor(user) if show_figurino else None

    # URL raiz do portal (mesma fonte de `_portal_url()` em `app/email_service.py`), para a
    # mensagem de cobrança via WhatsApp linkar direto para o portal (feature 239).
    portal_url = current_app.config.get("PORTAL_URL", "").rstrip("/") or None

    return {
        "casting": casting,
        "figurino": figurino,
        "figurino_producao": minhas_pecas,
        "figurino_oficina": fila_oficina,
        "ensaio": ensaio,
        "comercial": comercial,
        "formularios": formularios,
        "financeiro": financeiro,
        "performance": performance,
        "dismissed_casting": dismissed,
        "portal_url": portal_url,
    }


def _serialize_alert(alert: dict[str, Any]) -> dict[str, Any]:
    """Serializa um alerta de conta recorrente (shape de `recurring_alerts`).

    O alerta é ``{"conta": RecurringExpense, "estado": str, "entry": RecurringExpenseEntry|None}``.
    O valor vem do lançamento do mês quando já existe (``a_pagar``); senão, do valor
    esperado da conta (``aguardando``).
    """
    conta = alert["conta"]
    entry = alert.get("entry")
    amount = entry.amount if entry is not None else conta.amount
    return {
        "name": conta.name,
        "due_day": conta.due_day,
        "amount": float(amount) if amount is not None else None,
    }
