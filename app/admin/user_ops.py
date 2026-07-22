"""Núcleo de negócio da gestão de usuários (feature 167, US6 — Cauda Administrativa).

Funções puras (sem `request`/`render_template`/`flash`), reusadas tanto pelas views Jinja de
`app/admin/routes.py` quanto pelos endpoints de API (`app/api/admin_users_read.py`,
`app/api/admin_users_write.py`) — fonte única, sem duplicar regra de negócio (Princípio I).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app import db
from app.models import (
    CalendarEvent,
    CommissionPayment,
    EnsaioMaterial,
    OrcamentoHistory,
    Role,
    SalaryHistory,
    SalaryPayment,
    SiteSetting,
    SpecialExpense,
    User,
)
from app.money import parse_brl_int
from app.utils import audit


class UserValidationError(Exception):
    """Erro de validação de negócio (campo obrigatório, email duplicado, salário inválido)."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


class UserDeletionBlockedError(Exception):
    """Exclusão bloqueada por histórico financeiro vinculado ao usuário."""

    def __init__(self, blockers: list[str]) -> None:
        message = (
            f"Não é possível excluir: este usuário tem histórico de {', '.join(blockers)}. "
            "Desmarque 'Usuário ativo' na edição para desativá-lo."
        )
        super().__init__(message)
        self.blockers = blockers
        self.message = message


def list_users_with_salary() -> list[tuple[User, SalaryHistory | None]]:
    """Todos os usuários (ordenados por id) com o salário vigente de cada um, se houver."""
    users = User.query.order_by(User.id.asc()).all()
    salaries = {s.user_id: s for s in SalaryHistory.query.filter_by(end_date=None).all()}
    return [(u, salaries.get(u.id)) for u in users]


def _normalize_salary(salary_value: int | None, payment_type: str) -> tuple[int, str | None]:
    """Valida o par (valor, tipo de pagamento) de um salário (feature 084).

    Returns:
        Tupla ``(salário_normalizado, erro)`` — ``erro`` é ``None`` quando válido.
    """
    if payment_type == "comissao":
        return 0, None
    if payment_type in ("semanal", "quinzenal"):
        if salary_value is None or salary_value <= 0:
            return 0, "Salário inválido."
        return salary_value, None
    return 0, "Selecione o tipo de pagamento."


@dataclass
class SalaryInput:
    """Dados brutos de um sub-formulário de salário, antes de validados."""

    amount: str | int | float | None
    payment_type: str
    start_date: str | None = None
    notes: str | None = None


def _parse_salary_input(data: SalaryInput | None) -> dict | None:
    """Valida um `SalaryInput` opcional. Retorna dict pronto p/ `SalaryHistory` ou `None`.

    Seção de salário é opcional: sem tipo selecionado e sem valor (> 0), retorna `None` — nenhum
    registro de salário é criado. "Somente comissão" é aceito com salário-base 0.
    """
    if data is None:
        return None
    salary_value = parse_brl_int(data.amount)
    payment_type = (data.payment_type or "").strip()
    if not payment_type and (salary_value is None or salary_value <= 0):
        return None

    salary_value, type_error = _normalize_salary(salary_value, payment_type)
    if type_error:
        raise UserValidationError("salary", type_error)
    try:
        start_date = date.fromisoformat(data.start_date) if data.start_date else date.today()
    except ValueError as exc:
        raise UserValidationError("salary", "Data de início do salário inválida.") from exc
    return {
        "salary": salary_value,
        "payment_type": payment_type,
        "start_date": start_date,
        "notes": (data.notes or "").strip() or None,
    }


def create_user(
    *,
    user_type: str,
    name: str,
    email: str | None,
    temp_password: str | None,
    role_ids: list[int] | None,
    pix_key: str | None,
    pix_key_type: str | None,
    salary: SalaryInput | None,
) -> User:
    """Cria um usuário "com acesso" ou "só pagamento", com PIX/salário opcionais."""
    clean_name = (name or "").strip()
    if not clean_name:
        raise UserValidationError("name", "Informe o nome.")
    clean_email = (email or "").strip().lower()

    if user_type == "payment_only":
        if clean_email and User.query.filter_by(email=clean_email).first():
            raise UserValidationError("email", "Esse email já existe.")
        user = User(
            email=clean_email or None,
            name=clean_name,
            is_active=True,
            has_access=False,
            must_change_password=False,
        )
    else:
        if not clean_email or not temp_password:
            raise UserValidationError("email", "Para usuário com acesso, preencha email e senha.")
        if User.query.filter_by(email=clean_email).first():
            raise UserValidationError("email", "Esse email já existe.")
        user = User(email=clean_email, name=clean_name, is_active=True, must_change_password=True)
        user.set_password(temp_password)
        if role_ids:
            user.roles = Role.query.filter(Role.id.in_(role_ids)).all()

    user.pix_key = (pix_key or "").strip() or None
    user.pix_key_type = (pix_key_type or "").strip() or None

    salary_data = _parse_salary_input(salary)

    db.session.add(user)
    db.session.flush()
    if salary_data:
        db.session.add(SalaryHistory(user_id=user.id, **salary_data))

    kind = "sem acesso (só pagamento)" if user_type == "payment_only" else "com acesso"
    audit(
        "create", "user", user.id, user.name, f"Usuário criado ({kind}): {user.email or user.name}"
    )
    db.session.commit()
    return user


def update_user_identity(
    user: User,
    *,
    name: str,
    email: str | None,
    is_active: bool,
    receives_commission: bool,
    role_ids: list[int] | None,
) -> User:
    """Atualiza nome/email/status/comissão/papéis (exclusivo Superadmin)."""
    clean_name = (name or "").strip()
    clean_email = (email or "").strip().lower()
    if not clean_name:
        raise UserValidationError("name", "Informe o nome.")
    if user.has_access and not clean_email:
        raise UserValidationError("email", "Email é obrigatório para usuário com acesso.")
    if clean_email:
        existing = User.query.filter(User.email == clean_email, User.id != user.id).first()
        if existing:
            raise UserValidationError("email", "Esse email já existe.")

    user.name = clean_name
    user.email = clean_email or None
    user.is_active = is_active
    user.receives_commission = receives_commission
    if user.has_access:
        user.roles = Role.query.filter(Role.id.in_(role_ids)).all() if role_ids else []

    audit("edit", "user", user.id, user.name, f"Usuário editado: {user.email}")
    db.session.commit()
    return user


def update_pix(user: User, *, pix_key: str | None, pix_key_type: str | None) -> User:
    """Atualiza dados de pagamento (PIX). Superadmin ou Financeiro."""
    user.pix_key = (pix_key or "").strip() or None
    user.pix_key_type = (pix_key_type or "").strip() or None
    audit("edit", "user", user.id, user.name, "PIX atualizado")
    db.session.commit()
    return user


def add_salary(user: User, salary: SalaryInput) -> SalaryHistory:
    """Registra novo salário (encerra o vigente). Superadmin ou Financeiro."""
    salary_value = parse_brl_int(salary.amount)
    payment_type = (salary.payment_type or "").strip()
    salary_value, type_error = _normalize_salary(salary_value, payment_type)
    if type_error:
        raise UserValidationError("salary", type_error)
    try:
        start_date = date.fromisoformat(salary.start_date) if salary.start_date else date.today()
    except ValueError as exc:
        raise UserValidationError("salary", "Data de início inválida.") from exc

    current = user.salary_histories.filter_by(end_date=None).first()
    if current:
        current.end_date = start_date
    entry = SalaryHistory(
        user_id=user.id,
        salary=salary_value,
        payment_type=payment_type,
        start_date=start_date,
        notes=(salary.notes or "").strip() or None,
    )
    db.session.add(entry)
    audit(
        "create",
        "salary",
        user.id,
        user.name,
        f"Salário registrado: R${salary_value} ({payment_type}) a partir de {start_date}",
    )
    db.session.commit()
    return entry


def grant_access(user: User, *, email: str, temp_password: str) -> User:
    """Concede acesso a uma pessoa cadastrada só para pagamento."""
    if user.has_access:
        raise UserValidationError("email", "Esse usuário já tem acesso ao sistema.")
    clean_email = (email or "").strip().lower()
    if not clean_email or not temp_password:
        raise UserValidationError(
            "email", "Para conceder acesso, informe email e senha temporária."
        )
    existing = User.query.filter(User.email == clean_email, User.id != user.id).first()
    if existing:
        raise UserValidationError("email", "Esse email já existe.")

    user.email = clean_email
    user.set_password(temp_password)
    user.has_access = True
    user.must_change_password = True
    audit("edit", "user", user.id, user.name, f"Acesso concedido: {user.email}")
    db.session.commit()
    return user


def reset_password(user: User, *, temp_password: str) -> User:
    """Reseta a senha de um usuário (exclusivo Superadmin)."""
    if not temp_password:
        raise UserValidationError("temp_password", "Senha temporária obrigatória.")
    user.set_password(temp_password)
    user.must_change_password = True
    audit("reset_password", "user", user.id, user.name, "Senha resetada pelo admin")
    db.session.commit()
    return user


def delete_user(user: User, *, actor_id: int) -> None:
    """Exclui um usuário sem histórico financeiro vinculado (exclusivo Superadmin)."""
    if user.id == actor_id:
        raise UserValidationError("id", "Você não pode excluir seu próprio usuário.")

    blockers = []
    if CommissionPayment.query.filter_by(seller_id=user.id).count():
        blockers.append("comissões")
    if OrcamentoHistory.query.filter_by(user_id=user.id).count():
        blockers.append("orçamentos")
    if SpecialExpense.query.filter_by(created_by_id=user.id).count():
        blockers.append("gastos extras")
    if CalendarEvent.query.filter_by(seller_id=user.id).count():
        blockers.append("vendas de eventos")
    if blockers:
        raise UserDeletionBlockedError(blockers)

    SiteSetting.query.filter_by(educamanto_seller_id=user.id).update({"educamanto_seller_id": None})
    SalaryPayment.query.filter_by(user_id=user.id).delete()
    SalaryHistory.query.filter_by(user_id=user.id).delete()
    EnsaioMaterial.query.filter_by(user_id=user.id).update({"user_id": None})
    SpecialExpense.query.filter_by(approved_by_id=user.id).update({"approved_by_id": None})
    SpecialExpense.query.filter_by(reimburse_user_id=user.id).update({"reimburse_user_id": None})

    audit("delete", "user", user.id, user.name, f"Usuário excluído: {user.email or user.name}")
    db.session.delete(user)
    db.session.commit()
