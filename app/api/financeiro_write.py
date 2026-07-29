"""Endpoints de ESCRITA da Planilha de Pagamentos (feature 160 — fecha a US4).

Reusa, sem duplicar, a mesma lógica de negócio hoje em `app/financeiro/routes.py`
(`set_payment_status`, `bulk_payment_action`, `salary_advance`, `salary_advance_delete`,
`export_pagamentos`) — os endpoints aqui só trocam a camada de entrada/saída (JSON/multipart em
vez de form+redirect). Gate: `_has_role(FINANCEIRO, SUPERADMIN)`, mesma paridade da 159
(`app/api/financeiro_read.py`).
"""

import csv
import io
import os
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from flask import current_app, jsonify, make_response, request
from flask_login import current_user
from werkzeug.utils import secure_filename

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.models import (
    CommissionPayment,
    EventAcrescimo,
    EventRole,
    RecurringExpenseEntry,
    SalaryAdvance,
    SalaryPayment,
    SpecialExpense,
    db,
)

_VALID_PAYMENT_STATUS = {"nao_pago", "pago", "no_banco"}


def _has_role(*names: str) -> bool:
    upper = [n.upper() for n in names]
    return any(r.name.upper() in upper for r in current_user.roles)


def _require_financeiro() -> Any:
    if not _has_role(RoleName.FINANCEIRO, RoleName.SUPERADMIN):
        return json_error("Sem permissão", 403)
    return None


@api_bp.route("/financeiro/pagamentos/set-status", methods=["POST"])
@api_login_required
def api_set_payment_status() -> Any:
    """Marca o status de um item de pagamento (feature 160).

    Reaproveita a mesma árvore de decisão de `set_payment_status`
    (`app/financeiro/routes.py:1177`) por tipo de item.
    """
    denied = _require_financeiro()
    if denied:
        return denied

    body = request.get_json(silent=True) or {}
    item_type = body.get("item_type", "cache")
    item_id = body.get("item_id")
    status = body.get("status")

    if item_id is None or status not in _VALID_PAYMENT_STATUS:
        return json_error("Status inválido para este item", 400)

    from app.utils import audit

    if item_type == "commission":
        try:
            seller_part, period_tag = str(item_id).split(":")
            seller_id = int(seller_part)
            py, pm = int(period_tag[:4]), int(period_tag[5:7])
        except (ValueError, AttributeError):
            return json_error("Status inválido para este item", 400)
        p_start = date(py, pm, 1)
        p_end = date(py + 1, 1, 1) if pm == 12 else date(py, pm + 1, 1)
        target = status if status in ("pago", "no_banco") else "a_pagar"
        rows = CommissionPayment.query.filter(
            CommissionPayment.seller_id == seller_id,
            CommissionPayment.sale_date >= p_start,
            CommissionPayment.sale_date < p_end,
            CommissionPayment.status.in_(["a_pagar", "no_banco", "pago"]),
        ).all()
        for c in rows:
            c.status = target
            c.paid_at = date.today() if target == "pago" else None
        audit(
            "payment",
            "commission",
            seller_id,
            "",
            f"Comissões {period_tag}: → {target} ({len(rows)} itens) (API)",
        )
        db.session.commit()
        return jsonify({"status": target if target != "a_pagar" else "nao_pago"})

    if item_type == "recurring":
        entry = RecurringExpenseEntry.query.get(_to_int(item_id))
        if not entry or entry.status not in ("a_pagar", "no_banco", "pago"):
            return json_error("Status inválido para este item", 400)
        old = entry.status
        if status == "pago":
            entry.status = "pago"
            entry.paid_at = date.today()
        elif status == "no_banco":
            entry.status = "no_banco"
            entry.paid_at = None
        else:
            entry.status = "a_pagar"
            entry.paid_at = None
        conta_nome = entry.recurring.name if entry.recurring else "—"
        audit(
            "payment",
            "recurring_expense",
            entry.id,
            conta_nome,
            f"Conta recorrente: {old} → {entry.status} | {entry.month_ref} (API)",
        )
        db.session.commit()
        return jsonify({"status": status if status in ("pago", "no_banco") else "nao_pago"})

    if item_type == "salary":
        sp = SalaryPayment.query.get(_to_int(item_id))
        if not sp:
            return json_error("Item não encontrado", 400)
        old = sp.payment_status
        sp.payment_status = status
        if status == "pago":
            sp.paid_at = date.today()
        audit(
            "payment",
            "salary_payment",
            sp.id,
            sp.user.name if sp.user else "—",
            f"Salário: {old} → {status} (API)",
        )
        db.session.commit()
        return jsonify({"status": status})

    if item_type == "expense":
        exp = SpecialExpense.query.get(_to_int(item_id))
        if not exp:
            return json_error("Item não encontrado", 400)
        old = exp.payment_status
        exp.payment_status = status
        audit(
            "payment",
            "special_expense",
            exp.id,
            exp.payee_name,
            f"Desembolso gasto: {old} → {status} | {exp.description} (API)",
        )
        db.session.commit()
        return jsonify({"status": status})

    if item_type == "bv":
        acr = EventAcrescimo.query.get(_to_int(item_id))
        if not acr or not acr.is_bv:
            return json_error("Item não encontrado", 400)
        old = acr.bv_payment_status
        acr.bv_payment_status = status
        audit(
            "payment",
            "event_bv",
            acr.id,
            acr.bv_recipient or "—",
            f"BV (repasse): {old} → {status} (API)",
        )
        db.session.commit()
        return jsonify({"status": status})

    role = EventRole.query.get(_to_int(item_id))
    if not role:
        return json_error("Item não encontrado", 400)
    old = role.payment_status
    role.payment_status = status
    talent_name = role.talent.full_name if role.talent else "—"
    audit(
        "payment",
        "event_role",
        role.id,
        talent_name,
        f"Pagamento: {old} → {status} | {role.character_name} (API)",
    )
    db.session.commit()
    return jsonify({"status": status})


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bulk_set_commission_period(commission_id: str, action: str) -> bool:
    """Aplica pago/nao_pago a um item agregado de comissão ("sellerId:YYYY-MM")."""
    try:
        seller_part, period_tag = str(commission_id).split(":")
        seller_id = int(seller_part)
        py, pm = int(period_tag[:4]), int(period_tag[5:7])
    except (ValueError, AttributeError):
        return False
    p_start = date(py, pm, 1)
    p_end = date(py + 1, 1, 1) if pm == 12 else date(py, pm + 1, 1)
    target = action if action in ("pago", "no_banco") else "a_pagar"
    rows = CommissionPayment.query.filter(
        CommissionPayment.seller_id == seller_id,
        CommissionPayment.sale_date >= p_start,
        CommissionPayment.sale_date < p_end,
        CommissionPayment.status.in_(["a_pagar", "no_banco", "pago"]),
    ).all()
    for c in rows:
        c.status = target
        c.paid_at = date.today() if target == "pago" else None
    from app.utils import audit

    audit(
        "payment",
        "commission",
        seller_id,
        "",
        f"Bulk comissões {period_tag}: → {target} ({len(rows)} itens) (API)",
    )
    return True


@api_bp.route("/financeiro/pagamentos/bulk-action", methods=["POST"])
@api_login_required
def api_bulk_payment_action() -> Any:
    """Ação em massa sobre itens selecionados (feature 160).

    Reaproveita a mesma lógica de `bulk_payment_action` (`app/financeiro/routes.py:1412`).
    """
    denied = _require_financeiro()
    if denied:
        return denied

    body = request.get_json(silent=True) or {}
    action = body.get("action")
    role_ids = body.get("role_ids") or []
    salary_ids = body.get("salary_ids") or []
    expense_ids = body.get("expense_ids") or []
    commission_ids = body.get("commission_ids") or []

    if not role_ids and not salary_ids and not expense_ids and not commission_ids:
        return jsonify({"changed": 0, "skipped": []})

    from app.utils import audit

    r_ids = [i for i in (_to_int(x) for x in role_ids) if i is not None]
    s_ids = [i for i in (_to_int(x) for x in salary_ids) if i is not None]
    g_ids = [i for i in (_to_int(x) for x in expense_ids) if i is not None]

    changed = 0
    skipped: list[str] = []

    if action == "delete":
        for rid in r_ids:
            role = EventRole.query.get(rid)
            if role:
                db.session.delete(role)
                changed += 1
        for sid in s_ids:
            sp = SalaryPayment.query.get(sid)
            if sp:
                db.session.delete(sp)
                changed += 1
        if g_ids:
            skipped.append(f"{len(g_ids)} gasto(s) — exclua pelo módulo de Gastos")
        if commission_ids:
            skipped.append(f"{len(commission_ids)} comissão(ões) — gerencie na tela de Comissões")
        audit(
            "delete",
            "payment",
            None,
            "bulk",
            f"Excluídos {len(r_ids)} cachês e {len(s_ids)} salários via pagamentos (API)",
        )
        db.session.commit()
    elif action in _VALID_PAYMENT_STATUS:
        for rid in r_ids:
            role = EventRole.query.get(rid)
            if role:
                old = role.payment_status
                role.payment_status = action
                changed += 1
                audit(
                    "payment",
                    "event_role",
                    role.id,
                    role.talent.full_name if role.talent else "—",
                    f"Bulk: {old} → {action} | {role.character_name} (API)",
                )
        for sid in s_ids:
            sp = SalaryPayment.query.get(sid)
            if sp:
                old = sp.payment_status
                sp.payment_status = action
                if action == "pago":
                    sp.paid_at = date.today()
                changed += 1
                audit(
                    "payment",
                    "salary_payment",
                    sp.id,
                    sp.user.name if sp.user else "—",
                    f"Bulk salário: {old} → {action} (API)",
                )
        for gid in g_ids:
            exp = SpecialExpense.query.get(gid)
            if exp:
                old = exp.payment_status
                exp.payment_status = action
                changed += 1
                audit(
                    "payment",
                    "special_expense",
                    exp.id,
                    exp.payee_name,
                    f"Bulk desembolso gasto: {old} → {action} | {exp.description} (API)",
                )
        for cid in commission_ids:
            if _bulk_set_commission_period(cid, action):
                changed += 1
        db.session.commit()
    else:
        return json_error("Ação inválida", 400)

    return jsonify({"changed": changed, "skipped": skipped})


@api_bp.route("/financeiro/comissoes/pagar-mes", methods=["POST"])
@api_login_required
def api_comissoes_pagar_mes() -> Any:
    """Liquidação em lote atômica de um vendedor/mês (feature 187).

    Gate de RBAC no servidor: exige Financeiro/Superadmin — um vendedor comum recebe 403 mesmo
    tentando liquidar o próprio `seller_id`, nunca só ocultado no cliente. Regra de negócio
    (transação atômica, idempotência) mora inteira em `comissoes_ops.pay_seller_month`.
    """
    denied = _require_financeiro()
    if denied:
        return denied

    from app.financeiro import comissoes_ops

    body = request.get_json(silent=True) or {}
    seller_id = body.get("seller_id")
    month = body.get("month")

    try:
        seller_id = int(seller_id)
    except (TypeError, ValueError):
        return json_error("Vendedor inválido", 400, {"seller_id": "Obrigatório"})

    try:
        result = comissoes_ops.pay_seller_month(seller_id, month, current_user)
    except comissoes_ops.InvalidMonthError:
        return json_error("Mês inválido", 400, {"month": "Use o formato AAAA-MM"})
    except comissoes_ops.SellerNotFoundError:
        return json_error("Vendedor não encontrado", 404)

    return jsonify(result.to_dict())


@api_bp.route("/financeiro/pagamentos/salary/<int:sp_id>/advance", methods=["POST"])
@api_login_required
def api_salary_advance(sp_id: int) -> Any:
    """Registra um adiantamento de salário (feature 160).

    Reaproveita a mesma validação de `salary_advance` (`app/financeiro/routes.py:1288`).
    """
    denied = _require_financeiro()
    if denied:
        return denied

    from app.money import parse_brl
    from app.utils import audit

    sp = SalaryPayment.query.get(sp_id)
    if not sp:
        return json_error("Lançamento de salário não encontrado", 404)

    adv = parse_brl(request.form.get("amount", ""))
    adv = adv if adv is not None else Decimal("0")
    if adv <= 0:
        return json_error(
            "Informe um valor de adiantamento maior que zero.", 400, {"amount": "Obrigatório"}
        )
    if (sp.advance_total + adv) > (sp.amount or Decimal("0")):
        return json_error(
            "A soma dos adiantamentos não pode ser maior que o salário.",
            400,
            {"amount": "Excede o salário"},
        )

    try:
        adv_date = date.fromisoformat(request.form.get("advance_date", "").strip())
    except ValueError:
        from zoneinfo import ZoneInfo

        adv_date = datetime.now(ZoneInfo("America/Sao_Paulo")).date()

    proof = request.files.get("advance_proof")
    if not (proof and proof.filename):
        return json_error(
            "Anexe o comprovante do adiantamento.", 400, {"advance_proof": "Obrigatório"}
        )

    proof.stream.seek(0, 2)
    size = proof.stream.tell()
    proof.stream.seek(0)
    if size > 10 * 1024 * 1024:
        return json_error(
            "Comprovante acima de 10 MB.", 400, {"advance_proof": "Arquivo grande demais"}
        )

    advance = SalaryAdvance(salary_payment_id=sp.id, amount=adv, advance_date=adv_date)
    db.session.add(advance)
    db.session.flush()
    fname = f"adv_{sp.id}_{advance.id}_{secure_filename(proof.filename)}"
    proof.save(os.path.join(current_app.config["UPLOAD_PAYMENTS"], fname))
    advance.proof = f"/uploads/payments/{fname}"

    audit(
        "payment",
        "salary_payment",
        sp.id,
        sp.user.name if sp.user else "—",
        f"Adiantamento de salário adicionado: R$ {adv} (API)",
    )
    db.session.commit()
    return jsonify(
        {
            "id": advance.id,
            "amount": float(advance.amount or 0),
            "date": advance.advance_date.isoformat() if advance.advance_date else None,
            "proof": advance.proof or "",
        }
    )


@api_bp.route("/financeiro/pagamentos/salary/advance/<int:adv_id>/delete", methods=["POST"])
@api_login_required
def api_salary_advance_delete(adv_id: int) -> Any:
    """Remove um adiantamento de salário (feature 160).

    Reaproveita a mesma lógica de `salary_advance_delete` (`app/financeiro/routes.py:1351`).
    """
    denied = _require_financeiro()
    if denied:
        return denied

    advance = SalaryAdvance.query.get(adv_id)
    if not advance:
        return json_error("Adiantamento não encontrado", 404)

    from app.utils import audit

    sp = advance.payment
    if advance.proof and advance.proof.startswith("/uploads/payments/"):
        try:
            os.remove(
                os.path.join(current_app.config["UPLOAD_PAYMENTS"], os.path.basename(advance.proof))
            )
        except OSError:
            pass

    valor = advance.amount
    db.session.delete(advance)
    audit(
        "payment",
        "salary_payment",
        sp.id if sp else 0,
        sp.user.name if sp and sp.user else "—",
        f"Adiantamento removido: R$ {valor} (API)",
    )
    db.session.commit()
    return "", 204


@api_bp.route("/financeiro/pagamentos/export")
@api_login_required
def api_export_pagamentos() -> Any:
    """Exporta CSV dos cachês do mês (feature 160).

    Reaproveita a mesma consulta/colunas de `export_pagamentos`
    (`app/financeiro/routes.py:1501`). Única rota desta fatia fora do envelope JSON padrão.
    """
    denied = _require_financeiro()
    if denied:
        return denied

    from app.financeiro.routes import _STATUS_LABELS, _pagamentos_query

    today = date.today()
    month = request.args.get("month", today.strftime("%Y-%m"))
    roles = _pagamentos_query(month)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Data", "Evento", "Função", "Nome", "Valor", "Pix", "Situação"])
    for r in roles:
        writer.writerow(
            [
                r.event.start_at.strftime("%d/%m/%Y") if r.event.start_at else "",
                r.event.title,
                r.character_name,
                r.talent.full_name if r.talent else "",
                r.cache_value or "",
                r.talent.pix_key if r.talent else "",
                _STATUS_LABELS.get(r.payment_status, r.payment_status),
            ]
        )

    resp = make_response(output.getvalue())
    resp.headers["Content-Type"] = "text/csv; charset=utf-8"
    resp.headers["Content-Disposition"] = f"attachment; filename=pagamentos_{month}.csv"
    return resp
