"""Núcleo de negócio de Gastos Extras e Gastos Recorrentes (features 128/110/121, migração 177).

Funções puras (sem `flask.request`/`render_template`/`flash`), reusadas tanto pelas views Jinja
de `app/gastos/routes.py` quanto pelos endpoints de API (`app/api/gastos_read.py`,
`app/api/gastos_write.py`) — fonte única, sem duplicar regra de negócio (Princípio I).

`ensure_recurring_entries()`/`recurring_alerts()` são reexportadas por `app/gastos/routes.py`
(vários outros módulos — `app/__init__.py`, `app/api/dashboard_service.py`,
`app/financeiro/routes.py`, `app/api/financeiro_read.py` — importam essas duas funções de
``app.gastos.routes``; o re-export mantém esses imports funcionando sem alteração).
"""

from __future__ import annotations

import calendar as cal_mod
import os
from datetime import date, datetime, timedelta
from decimal import Decimal

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app import db
from app.constants import RoleName
from app.models import (
    AuditLog,
    CalendarEvent,
    RecurringExpense,
    RecurringExpenseEntry,
    SpecialExpense,
    User,
)


class GastoValidationError(Exception):
    """Erro de validação de negócio (campo obrigatório/inválido)."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


class GastoStateError(Exception):
    """Transição de estado não permitida (ex.: aprovar gasto que já não está pendente)."""


def is_superadmin(user: User) -> bool:
    """True se `user` tem o papel SUPERADMIN."""
    return any(r.name.upper() == RoleName.SUPERADMIN for r in user.roles)


def is_financeiro(user: User) -> bool:
    """True se `user` tem papel FINANCEIRO ou SUPERADMIN (gastos recorrentes)."""
    return any(
        r.name.upper() in (RoleName.FINANCEIRO, RoleName.SUPERADMIN) for r in user.roles
    )


def _log(
    actor: User, entity_type: str, entity_id: int, entity_name: str, action: str, detail: str = ""
) -> None:
    """Registra a ação no log de auditoria do sistema."""
    db.session.add(
        AuditLog(
            actor_name=actor.name,
            actor_role=", ".join(r.name for r in actor.roles),
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            action=action,
            detail=detail,
        )
    )


# ══════════════════════════════════════════════════════════════════
#  Gastos Extras (SpecialExpense)
# ══════════════════════════════════════════════════════════════════


def list_expenses(user: User) -> list[SpecialExpense]:
    """Lista gastos: SUPERADMIN vê todos, demais usuários só os próprios."""
    query = SpecialExpense.query
    if not is_superadmin(user):
        query = query.filter_by(created_by_id=user.id)
    return query.order_by(SpecialExpense.expense_date.desc(), SpecialExpense.id.desc()).all()


def search_events_by_date(day: date) -> list[CalendarEvent]:
    """Eventos de um dia, para o seletor de vínculo de um gasto."""
    from sqlalchemy import func

    return (
        CalendarEvent.query.filter(func.date(CalendarEvent.start_at) == day.isoformat())
        .order_by(CalendarEvent.start_at.asc())
        .all()
    )


def save_receipt(file: FileStorage, upload_dir: str) -> str | None:
    """Salva o comprovante em `upload_dir`; retorna caminho relativo 'expenses/<arquivo>'."""
    if not file or not file.filename:
        return None
    fname = secure_filename(file.filename)
    if not fname:
        return None
    unique = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{fname}"
    os.makedirs(upload_dir, exist_ok=True)
    file.save(os.path.join(upload_dir, unique))
    return f"expenses/{unique}"


def create_expense(
    creator: User, data: dict, receipt_path: str | None, event_id: int | None
) -> SpecialExpense:
    """Cria um gasto extra pendente. `data` já validado/parseado pelo chamador.

    Args:
        creator: usuário autenticado que está registrando o gasto.
        data: `description`, `category`, `amount` (Decimal), `expense_date` (date), `notes`,
            `disbursement_type`, `reimburse_user_id`, `supplier_name`, `supplier_pix`,
            `paid_at_creation` (bool).
        receipt_path: caminho já salvo do comprovante (via `save_receipt`).
        event_id: evento a vincular, se houver.

    Raises:
        GastoValidationError: descrição/valor ausente, comprovante ausente ou desembolso
            incompleto (funcionário não selecionado / fornecedor sem nome).
    """
    description = (data.get("description") or "").strip()
    amount = data.get("amount")
    if not description:
        raise GastoValidationError("description", "Informe uma descrição.")
    if amount is None or amount <= 0:
        raise GastoValidationError("amount", "Informe um valor válido (ex.: 1.000,00).")
    if not receipt_path:
        raise GastoValidationError(
            "receipt", "Anexe a Nota Fiscal (foto ou PDF que mostre o valor dos produtos)."
        )

    disbursement_type = (data.get("disbursement_type") or "").strip() or None
    reimburse_user_id = None
    supplier_name = None
    supplier_pix = None
    if disbursement_type == "reembolso":
        reimburse_user_id = data.get("reimburse_user_id")
        if not reimburse_user_id:
            raise GastoValidationError(
                "reimburse_user_id", "Selecione o funcionário a ser reembolsado."
            )
    elif disbursement_type == "fornecedor":
        supplier_name = (data.get("supplier_name") or "").strip()
        supplier_pix = (data.get("supplier_pix") or "").strip() or None
        if not supplier_name:
            raise GastoValidationError("supplier_name", "Informe o nome do fornecedor.")
    else:
        disbursement_type = None

    paid_at_creation = bool(disbursement_type) and bool(data.get("paid_at_creation"))
    category = data.get("category") or "Outros"
    if category not in SpecialExpense.CATEGORIES:
        category = "Outros"

    expense = SpecialExpense(
        description=description,
        category=category,
        amount=amount,
        expense_date=data.get("expense_date") or date.today(),
        receipt_path=receipt_path,
        notes=(data.get("notes") or "").strip() or None,
        status="pendente",
        created_by_id=creator.id,
        disbursement_type=disbursement_type,
        reimburse_user_id=reimburse_user_id,
        supplier_name=supplier_name,
        supplier_pix=supplier_pix,
        payment_status="pago" if paid_at_creation else "nao_pago",
        paid_at_creation=paid_at_creation,
        event_id=event_id,
    )
    db.session.add(expense)
    db.session.flush()
    _log(
        creator, "gasto", expense.id, expense.description, "create",
        f"Gasto registrado: R$ {amount:.2f} ({category})",
    )
    db.session.commit()
    return expense


def approve_expense(expense: SpecialExpense, approver: User) -> SpecialExpense:
    """Aprova um gasto pendente — passa a contar no balanço."""
    if expense.status != "pendente":
        raise GastoStateError("Este gasto já não está pendente.")
    expense.status = "aprovado"
    expense.approved_by_id = approver.id
    expense.approved_at = datetime.utcnow()
    _log(approver, "gasto", expense.id, expense.description, "approve", "Gasto aprovado")
    db.session.commit()
    return expense


def reject_expense(expense: SpecialExpense, approver: User, motivo: str) -> SpecialExpense:
    """Rejeita um gasto pendente, com motivo opcional."""
    if expense.status != "pendente":
        raise GastoStateError("Este gasto já não está pendente.")
    expense.status = "rejeitado"
    expense.approved_by_id = approver.id
    expense.approved_at = datetime.utcnow()
    expense.notes = motivo.strip() or expense.notes
    _log(
        approver, "gasto", expense.id, expense.description, "reject",
        f"Gasto rejeitado: {motivo.strip() or 'sem motivo'}",
    )
    db.session.commit()
    return expense


def can_delete_expense(expense: SpecialExpense, user: User) -> bool:
    """SUPERADMIN sempre; autor só enquanto o gasto está pendente."""
    return is_superadmin(user) or (
        expense.created_by_id == user.id and expense.status == "pendente"
    )


def delete_expense(expense: SpecialExpense, actor: User) -> None:
    """Exclui um gasto — chamador já deve ter checado `can_delete_expense`."""
    _log(actor, "gasto", expense.id, expense.description, "delete", "Gasto excluído")
    db.session.delete(expense)
    db.session.commit()


def link_expense_to_event(
    expense: SpecialExpense, event_id: int | None, actor: User
) -> SpecialExpense:
    """Vincula/remove o evento de um gasto existente."""
    if event_id is None:
        expense.event_id = None
        detail = "Vínculo de evento removido"
    else:
        event = CalendarEvent.query.get(event_id)
        if event is None:
            raise GastoValidationError("event_id", "Evento inválido.")
        expense.event_id = event_id
        detail = f"Gasto vinculado ao evento: {event.title}"
    _log(actor, "gasto", expense.id, expense.description, "link_event", detail)
    db.session.commit()
    return expense


# ══════════════════════════════════════════════════════════════════
#  Gastos Recorrentes (feature 110/112/113/121) — FINANCEIRO/SUPERADMIN
# ══════════════════════════════════════════════════════════════════


def _month_ref(year: int, month: int) -> str:
    """Formata a referência mensal: '2026-07'."""
    return f"{year:04d}-{month:02d}"


def _clamp_day(year: int, month: int, day: int) -> date:
    """Data no mês com o dia clampado no último dia (dia 31 num mês de 30 vira dia 30)."""
    _, last_day = cal_mod.monthrange(year, month)
    return date(year, month, min(max(day, 1), last_day))


def _weekly_first_date(conta: RecurringExpense, year: int, month: int) -> date | None:
    """Primeira ocorrência do dia da semana da conta no mês∩vigência (feature 113)."""
    _, last_day = cal_mod.monthrange(year, month)
    lo = max(date(year, month, 1), conta.start_date or date(year, month, 1))
    hi = min(date(year, month, last_day), conta.end_date or date(year, month, last_day))
    d = lo
    while d <= hi:
        if d.weekday() == conta.anchor_weekday:
            return d
        d += timedelta(days=1)
    return None


def _conta_due_date(conta: RecurringExpense, year: int, month: int) -> date:
    """Vencimento exibido no mês: 1ª ocorrência (semanal) ou o dia do mês clampado."""
    if conta.frequency == "semanal":
        first = _weekly_first_date(conta, year, month)
        if first is not None:
            return first
    return _clamp_day(year, month, conta.due_day)


def ensure_recurring_entries(year: int, month: int) -> None:
    """Cria os lançamentos 'registrado' do mês para os fixos ativos (idempotente).

    Padrão de geração preguiçosa (mesmo dos salários): chamada pelas telas que consomem os
    dados; a unique (recurring_id, month_ref) garante 1 lançamento por conta/mês. Faz commit.
    """
    ref = _month_ref(year, month)
    fixed = RecurringExpense.query.filter(
        RecurringExpense.is_active.is_(True),
        RecurringExpense.expense_type.in_(["debito_automatico", "assinatura"]),
    ).all()
    if not fixed:
        return
    existing_ids = {
        e.recurring_id for e in RecurringExpenseEntry.query.filter_by(month_ref=ref).all()
    }
    created = False
    for r in fixed:
        if r.id in existing_ids or r.amount is None:
            continue
        occurrences = r.occurrences_in_month(year, month)
        if occurrences == 0:
            continue
        db.session.add(
            RecurringExpenseEntry(
                recurring_id=r.id,
                month_ref=ref,
                amount=r.amount * occurrences,
                due_date=_conta_due_date(r, year, month),
                status="registrado",
            )
        )
        created = True
    if created:
        db.session.commit()


def recurring_alerts(today: date) -> list[dict]:
    """Alertas do mês corrente para contas variáveis ativas (home, feature 110).

    A partir do dia esperado (clampado no fim do mês): sem lançamento vira "aguardando";
    lançamento a_pagar vira "a_pagar" (com valor). pago/pulado: sem alerta.
    """
    ref = _month_ref(today.year, today.month)
    variaveis = RecurringExpense.query.filter(
        RecurringExpense.is_active.is_(True),
        RecurringExpense.expense_type == "variavel",
    ).order_by(RecurringExpense.due_day.asc(), RecurringExpense.name.asc()).all()
    if not variaveis:
        return []
    entries = {
        e.recurring_id: e
        for e in RecurringExpenseEntry.query.filter(
            RecurringExpenseEntry.month_ref == ref,
            RecurringExpenseEntry.recurring_id.in_([r.id for r in variaveis]),
        ).all()
    }
    alerts = []
    for r in variaveis:
        if r.occurrences_in_month(today.year, today.month) == 0:
            continue
        if today < _conta_due_date(r, today.year, today.month):
            continue
        entry = entries.get(r.id)
        if entry is None:
            alerts.append({"conta": r, "estado": "aguardando", "entry": None})
        elif entry.status == "a_pagar":
            alerts.append({"conta": r, "estado": "a_pagar", "entry": entry})
    return alerts


def list_recurring(month_ref: str | None = None) -> dict:
    """Contas por tipo + lançamentos do mês (`month_ref`, default mês corrente)."""
    today = date.today()
    if month_ref:
        try:
            year_i, month_i = int(month_ref[:4]), int(month_ref[5:7])
        except (ValueError, IndexError):
            year_i, month_i = today.year, today.month
    else:
        year_i, month_i = today.year, today.month
    ref = _month_ref(year_i, month_i)
    ensure_recurring_entries(year_i, month_i)

    contas = RecurringExpense.query.order_by(
        RecurringExpense.is_active.desc(),
        RecurringExpense.due_day.asc(),
        RecurringExpense.name.asc(),
    ).all()
    entries = {e.recurring_id: e for e in RecurringExpenseEntry.query.filter_by(month_ref=ref).all()}
    return {
        "contas": contas,
        "entries": entries,
        "month_ref": ref,
        "ref_year": year_i,
        "ref_month": month_i,
        "is_current_month": ref == _month_ref(today.year, today.month),
    }


def _log_recorrente(actor: User, conta: RecurringExpense, action: str, detail: str = "") -> None:
    _log(actor, "gasto_recorrente", conta.id, conta.name, action, detail)


def parse_conta_data(data: dict) -> dict:
    """Valida os dados de uma conta recorrente comum (não-programada).

    Args:
        data: `name`, `expense_type`, `frequency`, `weekday` (só semanal), `due_day` (demais),
            `amount`, `ref_mode` (só variável: `"faixa"`|`"exato"`), `amount_min`, `amount_max`,
            `start_date`, `end_date`, `default_pix`, `card_name`, `notes`.

    Raises:
        GastoValidationError: campo obrigatório ausente ou inconsistente.
    """
    name = (data.get("name") or "").strip()
    expense_type = data.get("expense_type") or ""
    if not name or expense_type not in RecurringExpense.TYPES:
        raise GastoValidationError("name", "Informe nome e tipo da conta.")

    frequency = data.get("frequency") or "mensal"
    if frequency not in RecurringExpense.FREQUENCIES:
        frequency = "mensal"

    weekday = None
    if frequency == "semanal":
        weekday = data.get("weekday")
        if weekday is None or not 0 <= int(weekday) <= 6:
            raise GastoValidationError("weekday", "Escolha o dia da semana da cobrança semanal.")
        weekday = int(weekday)
        due_day = 1
    else:
        due_day = data.get("due_day")
        if due_day is None or not 1 <= int(due_day) <= 31:
            raise GastoValidationError("due_day", "Informe o dia (1 a 31) da conta.")
        due_day = int(due_day)

    amount = data.get("amount")
    if expense_type != "variavel" and (amount is None or amount <= 0):
        raise GastoValidationError("amount", "Informe o valor fixo da conta (ex.: 1.000,00).")

    var_amount = var_min = var_max = None
    if expense_type == "variavel":
        ref_mode = data.get("ref_mode") or "faixa"
        var_amount = amount if ref_mode == "exato" else None
        var_min = data.get("amount_min") if ref_mode != "exato" else None
        var_max = data.get("amount_max") if ref_mode != "exato" else None

    start_date = data.get("start_date") or date.today()
    end_date = data.get("end_date")
    if end_date and end_date < start_date:
        raise GastoValidationError(
            "end_date", "A data de fim não pode ser anterior à data de início."
        )

    return {
        "name": name,
        "expense_type": expense_type,
        "due_day": due_day,
        "frequency": frequency,
        "weekday": weekday,
        "start_date": start_date,
        "end_date": end_date,
        "amount": amount if expense_type != "variavel" else var_amount,
        "amount_min": var_min,
        "amount_max": var_max,
        "default_pix": (data.get("default_pix") or "").strip() or None,
        "card_name": (
            (data.get("card_name") or "").strip() or None
        ) if expense_type == "assinatura" else None,
        "notes": (data.get("notes") or "").strip() or None,
    }


def create_recurring(creator: User, data: dict) -> RecurringExpense:
    """Cadastra uma conta recorrente comum (variável/débito automático/assinatura)."""
    parsed = parse_conta_data(data)
    conta = RecurringExpense(created_by_id=creator.id, **parsed)
    db.session.add(conta)
    db.session.flush()
    _log_recorrente(creator, conta, "create", f"Conta recorrente criada ({parsed['expense_type']})")
    db.session.commit()
    return conta


def update_recurring(conta: RecurringExpense, actor: User, data: dict) -> RecurringExpense:
    """Edita uma conta recorrente (lançamentos já criados não mudam)."""
    parsed = parse_conta_data(data)
    for key, value in parsed.items():
        setattr(conta, key, value)
    _log_recorrente(actor, conta, "edit", "Conta recorrente editada")
    db.session.commit()
    return conta


def toggle_recurring(conta: RecurringExpense, actor: User) -> RecurringExpense:
    """Ativa/desativa uma conta (desativada: sem alertas nem lançamentos novos)."""
    conta.is_active = not conta.is_active
    _log_recorrente(actor, conta, "toggle", "Reativada" if conta.is_active else "Desativada")
    db.session.commit()
    return conta


def delete_recurring(conta: RecurringExpense, actor: User) -> None:
    """Exclui conta SEM lançamentos; com histórico, o caminho é desativar."""
    if RecurringExpenseEntry.query.filter_by(recurring_id=conta.id).count():
        raise GastoStateError("Conta com lançamentos não pode ser excluída — desative-a.")
    _log_recorrente(actor, conta, "delete", "Conta recorrente excluída (sem lançamentos)")
    db.session.delete(conta)
    db.session.commit()


def parse_programado_data(data: dict) -> dict:
    """Valida os dados de um pagamento programado (feature 121): N parcelas próprias.

    Args:
        data: `name`, `default_pix`, `notes`, `parcelas` (lista de `{"date": date, "amount": Decimal}`).

    Raises:
        GastoValidationError: nome ausente, nenhuma parcela válida, ou valor inválido.
    """
    name = (data.get("name") or "").strip()
    if not name:
        raise GastoValidationError("name", "Informe o nome/descrição do pagamento programado.")
    parcelas_raw = data.get("parcelas") or []
    parcelas: list[tuple[date, Decimal]] = []
    for item in parcelas_raw:
        d = item.get("date")
        amount = item.get("amount")
        if not d:
            continue
        if amount is None or amount <= 0:
            raise GastoValidationError(
                "parcelas", f"Valor inválido para a data {d.strftime('%d/%m/%Y')}."
            )
        parcelas.append((d, amount))
    if not parcelas:
        raise GastoValidationError("parcelas", "Informe ao menos uma data de parcela.")
    return {
        "name": name,
        "default_pix": (data.get("default_pix") or "").strip() or None,
        "notes": (data.get("notes") or "").strip() or None,
        "parcelas": parcelas,
    }


def create_programado(creator: User, data: dict) -> RecurringExpense:
    """Cria um pagamento programado: N parcelas com data e valor próprios (feature 121)."""
    parsed = parse_programado_data(data)
    parcelas = parsed.pop("parcelas")
    conta = RecurringExpense(
        created_by_id=creator.id,
        expense_type="programado",
        due_day=1,
        frequency="mensal",
        start_date=min(d for d, _ in parcelas),
        end_date=max(d for d, _ in parcelas),
        **parsed,
    )
    db.session.add(conta)
    db.session.flush()
    for due, amount in parcelas:
        db.session.add(
            RecurringExpenseEntry(
                recurring_id=conta.id,
                month_ref=due.strftime("%Y-%m"),
                amount=amount,
                pix=conta.default_pix,
                due_date=due,
                status="a_pagar",
            )
        )
    _log_recorrente(
        creator, conta, "create", f"Pagamento programado criado: {len(parcelas)} parcela(s)"
    )
    db.session.commit()
    return conta


def _entry_do_mes(conta: RecurringExpense, ref: str) -> RecurringExpenseEntry | None:
    return RecurringExpenseEntry.query.filter_by(recurring_id=conta.id, month_ref=ref).first()


def fill_entry(
    conta: RecurringExpense, actor: User, month_ref: str, amount: Decimal, pix: str | None,
    due_date: date | None,
) -> RecurringExpenseEntry:
    """Preenche a conta variável do mês (valor + PIX + vencimento): lançamento a pagar."""
    if conta.expense_type != "variavel":
        raise GastoStateError("Só contas variáveis são preenchidas manualmente.")
    entry = _entry_do_mes(conta, month_ref)
    if entry and entry.status == "pago":
        raise GastoStateError("Lançamento já pago — não pode ser alterado.")
    if entry is None:
        entry = RecurringExpenseEntry(recurring_id=conta.id, month_ref=month_ref)
        db.session.add(entry)
    entry.amount = amount
    entry.pix = pix or conta.default_pix
    entry.due_date = due_date
    entry.status = "a_pagar"
    entry.filled_by_id = actor.id
    entry.filled_at = datetime.utcnow()
    _log_recorrente(actor, conta, "fill", f"Conta de {month_ref} preenchida: R$ {amount:.2f}")
    db.session.commit()
    return entry


def skip_entry(conta: RecurringExpense, actor: User, month_ref: str) -> RecurringExpenseEntry:
    """Pula o mês de uma conta variável (boleto não veio) — encerra o alerta sem pagamento."""
    if conta.expense_type != "variavel":
        raise GastoStateError("Só contas variáveis podem pular o mês.")
    entry = _entry_do_mes(conta, month_ref)
    if entry and entry.status == "pago":
        raise GastoStateError("Lançamento já pago — não pode ser pulado.")
    if entry is None:
        entry = RecurringExpenseEntry(recurring_id=conta.id, month_ref=month_ref)
        db.session.add(entry)
    entry.amount = None
    entry.pix = None
    entry.due_date = None
    entry.status = "pulado"
    entry.filled_by_id = actor.id
    entry.filled_at = datetime.utcnow()
    _log_recorrente(actor, conta, "skip", f"Mês {month_ref} pulado (conta não veio)")
    db.session.commit()
    return entry


def pay_entry(entry: RecurringExpenseEntry, actor: User) -> RecurringExpenseEntry:
    """Marca um lançamento a pagar como pago."""
    if entry.status != "a_pagar":
        raise GastoStateError("Só lançamentos a pagar podem ser marcados como pagos.")
    entry.status = "pago"
    entry.paid_at = date.today()
    _log_recorrente(
        actor, entry.recurring, "pay", f"Conta de {entry.month_ref} paga: R$ {entry.amount:.2f}"
    )
    db.session.commit()
    return entry


def delete_parcela(entry: RecurringExpenseEntry, actor: User) -> None:
    """Exclui uma parcela avulsa de pagamento programado ainda não paga (feature 121)."""
    conta = entry.recurring
    if not conta or conta.expense_type != "programado":
        raise GastoStateError("Esta ação só vale para parcelas de pagamento programado.")
    if entry.status == "pago":
        raise GastoStateError("Parcela já paga não pode ser excluída.")
    detail = (
        f"Parcela de {entry.due_date.strftime('%d/%m/%Y') if entry.due_date else entry.month_ref} "
        f"excluída: R$ {entry.amount:.2f}"
    )
    db.session.delete(entry)
    _log_recorrente(actor, conta, "delete_parcela", detail)
    db.session.commit()


def reopen_entry(entry: RecurringExpenseEntry, actor: User) -> RecurringExpenseEntry | None:
    """Reabre um lançamento (pago volta a 'a pagar'; pulado é removido e volta a aguardar)."""
    conta = entry.recurring
    if entry.status == "pago":
        entry.status = "a_pagar"
        entry.paid_at = None
        detail = f"Pagamento de {entry.month_ref} reaberto"
        _log_recorrente(actor, conta, "reopen", detail)
        db.session.commit()
        return entry
    if entry.status == "pulado":
        detail = f"Pulo de {entry.month_ref} desfeito (volta a aguardar valor)"
        db.session.delete(entry)
        _log_recorrente(actor, conta, "reopen", detail)
        db.session.commit()
        return None
    raise GastoStateError("Este lançamento não pode ser reaberto.")
