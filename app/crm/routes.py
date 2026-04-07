import os
import re
from datetime import datetime

_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.constants import RoleName
from app.models import (
    CRMDeal, CRMStage, CRMOrganization, CRMContact, CRMNote, CRMReminder,
    User, Role, SiteSetting, CalendarEvent,
)
from .clicksign_service import (
    detect_contract_type, get_contract_link, get_contract_label,
    parse_webhook_event, verify_webhook_hmac, CONTRACT_LINKS, CONTRACT_LABELS,
)

crm_bp = Blueprint("crm", __name__)

SOURCES = [
    ("whatsapp",  "WhatsApp"),
    ("instagram", "Instagram"),
    ("indicacao", "Indicação"),
    ("site",      "Site"),
    ("outro",     "Outro"),
]

NOTE_TYPES = [
    ("note",     "Anotação"),
    ("call",     "Ligação"),
    ("whatsapp", "WhatsApp"),
    ("email",    "E-mail"),
    ("internal", "Nota interna"),
]


def _require_crm():
    allowed = {RoleName.SUPERADMIN, RoleName.COMERCIAL, RoleName.VENDAS}
    if not any(r.name in allowed for r in current_user.roles):
        abort(403)


def _sellers():
    return (
        User.query.join(User.roles)
        .filter(Role.name.in_([RoleName.COMERCIAL, RoleName.VENDAS, RoleName.SUPERADMIN]))
        .order_by(User.name)
        .all()
    )


# ─── PIPELINE ────────────────────────────────────────────────────────────────

@crm_bp.route("/crm/")
@login_required
def pipeline():
    _require_crm()
    stages = CRMStage.query.order_by(CRMStage.position).all()
    deals_by_stage = {}
    for stage in stages:
        deals_by_stage[stage.id] = (
            CRMDeal.query.filter_by(stage_id=stage.id)
            .order_by(CRMDeal.updated_at.desc())
            .all()
        )
    return render_template(
        "crm/pipeline.html",
        stages=stages,
        deals_by_stage=deals_by_stage,
        sources=SOURCES,
        sellers=_sellers(),
    )


@crm_bp.route("/crm/deals/move", methods=["POST"])
@login_required
def move_deal():
    _require_crm()
    deal_id  = request.form.get("deal_id", type=int)
    stage_id = request.form.get("stage_id", type=int)
    deal = CRMDeal.query.get_or_404(deal_id)
    stage = CRMStage.query.get_or_404(stage_id)
    deal.stage_id = stage_id
    if stage.is_won or stage.is_lost:
        deal.closed_at = datetime.utcnow()
    db.session.commit()
    return {"ok": True}


# ─── DEAL ─────────────────────────────────────────────────────────────────────

@crm_bp.route("/crm/deals/new", methods=["GET", "POST"])
@login_required
def new_deal():
    _require_crm()
    if request.method == "POST":
        first_stage = CRMStage.query.order_by(CRMStage.position).first()
        deal = CRMDeal(
            title        = request.form.get("title", "").strip() or "Novo lead",
            stage_id     = first_stage.id if first_stage else None,
            assigned_to  = request.form.get("assigned_to", type=int) or current_user.id,
            source       = request.form.get("source") or None,
            value        = request.form.get("value", type=int) or None,
            contractor_name     = request.form.get("contractor_name", "").strip() or None,
            contractor_whatsapp = request.form.get("contractor_whatsapp", "").strip() or None,
            contractor_email    = request.form.get("contractor_email", "").strip() or None,
        )
        # vínculo com organização ou contato
        org_id  = request.form.get("organization_id", type=int)
        cont_id = request.form.get("contact_id", type=int)
        if org_id:  deal.organization_id = org_id
        if cont_id: deal.contact_id = cont_id
        db.session.add(deal)
        db.session.commit()
        flash("Lead criado.", "success")
        return redirect(url_for("crm.deal_detail", deal_id=deal.id))

    return render_template(
        "crm/deal_form.html",
        deal=None,
        stages=CRMStage.query.order_by(CRMStage.position).all(),
        organizations=CRMOrganization.query.order_by(CRMOrganization.name).all(),
        contacts=CRMContact.query.order_by(CRMContact.name).all(),
        sellers=_sellers(),
        sources=SOURCES,
    )


@crm_bp.route("/crm/deals/<int:deal_id>", methods=["GET", "POST"])
@login_required
def deal_detail(deal_id: int):
    _require_crm()
    deal = CRMDeal.query.get_or_404(deal_id)

    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_deal":
            deal.title       = request.form.get("title", deal.title).strip()
            deal.stage_id    = request.form.get("stage_id", type=int) or deal.stage_id
            deal.assigned_to = request.form.get("assigned_to", type=int) or deal.assigned_to
            deal.source      = request.form.get("source") or deal.source
            deal.value       = request.form.get("value", type=int) or deal.value
            deal.lost_reason = request.form.get("lost_reason", "").strip() or None
            org_id  = request.form.get("organization_id", type=int)
            cont_id = request.form.get("contact_id", type=int)
            deal.organization_id = org_id or None
            deal.contact_id      = cont_id or None
            stage = CRMStage.query.get(deal.stage_id)
            if stage and (stage.is_won or stage.is_lost) and not deal.closed_at:
                deal.closed_at = datetime.utcnow()
            db.session.commit()
            flash("Lead atualizado.", "success")

        elif action == "update_precontrato":
            fields = [
                "contractor_name", "contractor_cpf", "contractor_email",
                "contractor_whatsapp", "contractor_address",
                "birthday_person", "birthday_age",
                "service_type", "character_count", "characters",
                "event_theme", "service_period",
                "venue_type", "venue_cep", "venue_street", "venue_number",
                "venue_complement", "venue_neighborhood", "venue_city", "venue_state",
                "payment_method", "payment_notes", "contractual_notes",
            ]
            for f in fields:
                setattr(deal, f, request.form.get(f, "").strip() or None)
            raw_date = request.form.get("event_date", "").strip()
            if raw_date:
                try:
                    deal.event_date = datetime.fromisoformat(raw_date)
                except ValueError:
                    pass
            deal.value = request.form.get("value", type=int) or deal.value
            db.session.commit()
            flash("Dados do precontrato salvos.", "success")

        elif action == "add_note":
            content   = request.form.get("content", "").strip()
            note_type = request.form.get("note_type", "note")
            if content:
                db.session.add(CRMNote(
                    deal_id=deal.id, user_id=current_user.id,
                    content=content, note_type=note_type,
                ))
                db.session.commit()

        elif action == "add_reminder":
            msg    = request.form.get("reminder_message", "").strip()
            due_at = request.form.get("reminder_due", "").strip()
            if msg and due_at:
                try:
                    due_dt = datetime.fromisoformat(due_at)
                    db.session.add(CRMReminder(
                        deal_id=deal.id, user_id=current_user.id,
                        message=msg, due_at=due_dt,
                    ))
                    db.session.commit()
                except ValueError:
                    flash("Data do lembrete inválida.", "error")

        elif action == "done_reminder":
            rem_id = request.form.get("reminder_id", type=int)
            rem = CRMReminder.query.get(rem_id)
            if rem and rem.deal_id == deal.id:
                rem.done_at = datetime.utcnow()
                db.session.commit()

        elif action == "delete_note":
            note_id = request.form.get("note_id", type=int)
            note = CRMNote.query.get(note_id)
            if note and note.deal_id == deal.id:
                db.session.delete(note)
                db.session.commit()

        return redirect(url_for("crm.deal_detail", deal_id=deal.id))

    notes = CRMNote.query.filter_by(deal_id=deal.id).order_by(CRMNote.created_at.desc()).all()
    reminders = CRMReminder.query.filter_by(deal_id=deal.id).order_by(CRMReminder.due_at).all()
    return render_template(
        "crm/deal_detail.html",
        deal=deal,
        stages=CRMStage.query.order_by(CRMStage.position).all(),
        organizations=CRMOrganization.query.order_by(CRMOrganization.name).all(),
        contacts=CRMContact.query.order_by(CRMContact.name).all(),
        sellers=_sellers(),
        sources=SOURCES,
        note_types=NOTE_TYPES,
        notes=notes,
        reminders=reminders,
    )


@crm_bp.route("/crm/deals/<int:deal_id>/delete", methods=["POST"])
@login_required
def delete_deal(deal_id: int):
    _require_crm()
    deal = CRMDeal.query.get_or_404(deal_id)
    db.session.delete(deal)
    db.session.commit()
    flash("Lead removido.", "success")
    return redirect(url_for("crm.pipeline"))


# ─── ORGANIZAÇÕES ─────────────────────────────────────────────────────────────

@crm_bp.route("/crm/organizations")
@login_required
def organizations():
    _require_crm()
    q = request.args.get("q", "").strip()
    query = CRMOrganization.query
    if q:
        query = query.filter(CRMOrganization.name.ilike(f"%{q}%"))
    orgs = query.order_by(CRMOrganization.name).all()
    return render_template("crm/organizations.html", organizations=orgs, q=q)


@crm_bp.route("/crm/organizations/new", methods=["GET", "POST"])
@crm_bp.route("/crm/organizations/<int:org_id>/edit", methods=["GET", "POST"])
@login_required
def edit_organization(org_id: int = None):
    _require_crm()
    org = CRMOrganization.query.get_or_404(org_id) if org_id else CRMOrganization()
    if request.method == "POST":
        org.name  = request.form.get("name", "").strip()
        org.cnpj  = request.form.get("cnpj", "").strip() or None
        org.phone = request.form.get("phone", "").strip() or None
        org.email = request.form.get("email", "").strip() or None
        org.notes = request.form.get("notes", "").strip() or None
        if not org.id:
            db.session.add(org)
        db.session.commit()
        flash("Organização salva.", "success")
        return redirect(url_for("crm.organizations"))
    return render_template("crm/organization_form.html", org=org)


# ─── CONTATOS ─────────────────────────────────────────────────────────────────

@crm_bp.route("/crm/contacts")
@login_required
def contacts():
    _require_crm()
    q = request.args.get("q", "").strip()
    query = CRMContact.query
    if q:
        query = query.filter(CRMContact.name.ilike(f"%{q}%"))
    all_contacts = query.order_by(CRMContact.name).all()
    return render_template("crm/contacts.html", contacts=all_contacts, q=q)


@crm_bp.route("/crm/contacts/new", methods=["GET", "POST"])
@crm_bp.route("/crm/contacts/<int:contact_id>/edit", methods=["GET", "POST"])
@login_required
def edit_contact(contact_id: int = None):
    _require_crm()
    contact = CRMContact.query.get_or_404(contact_id) if contact_id else CRMContact()
    if request.method == "POST":
        contact.name            = request.form.get("name", "").strip()
        contact.cpf             = request.form.get("cpf", "").strip() or None
        contact.phone           = request.form.get("phone", "").strip() or None
        contact.email           = request.form.get("email", "").strip() or None
        contact.organization_id = request.form.get("organization_id", type=int) or None
        contact.notes           = request.form.get("notes", "").strip() or None
        if not contact.id:
            db.session.add(contact)
        db.session.commit()
        flash("Contato salvo.", "success")
        return redirect(url_for("crm.contacts"))
    return render_template(
        "crm/contact_form.html",
        contact=contact,
        organizations=CRMOrganization.query.order_by(CRMOrganization.name).all(),
    )


# ─── MÉTRICAS ─────────────────────────────────────────────────────────────────

@crm_bp.route("/crm/metrics")
@login_required
def metrics():
    _require_crm()
    stages = CRMStage.query.order_by(CRMStage.position).all()
    all_deals = CRMDeal.query.all()

    total     = len(all_deals)
    won       = sum(1 for d in all_deals if d.stage and d.stage.is_won)
    lost      = sum(1 for d in all_deals if d.stage and d.stage.is_lost)
    conv_rate = round(won / total * 100, 1) if total else 0
    total_rev = sum(d.value or 0 for d in all_deals if d.stage and d.stage.is_won)

    # leads por origem
    source_counts = {}
    for d in all_deals:
        source_counts[d.source or "outro"] = source_counts.get(d.source or "outro", 0) + 1

    # motivos de perda
    loss_reasons = {}
    for d in all_deals:
        if d.stage and d.stage.is_lost and d.lost_reason:
            loss_reasons[d.lost_reason] = loss_reasons.get(d.lost_reason, 0) + 1

    # por etapa
    stage_counts = {s.id: len(deals_by_stage) for s in stages
                    for deals_by_stage in [CRMDeal.query.filter_by(stage_id=s.id).all()]}

    return render_template(
        "crm/metrics.html",
        total=total, won=won, lost=lost, conv_rate=conv_rate, total_rev=total_rev,
        source_counts=source_counts, loss_reasons=loss_reasons,
        stages=stages, stage_counts=stage_counts,
        sources=SOURCES,
    )


# ─── CLICKSIGN ────────────────────────────────────────────────────────────────

@crm_bp.route("/crm/deals/<int:deal_id>/contract", methods=["GET", "POST"])
@login_required
def deal_contract(deal_id: int):
    _require_crm()
    deal = CRMDeal.query.get_or_404(deal_id)

    if request.method == "POST":
        raw = request.form.get("envelope_key", "").strip()
        # aceita URL completa ou UUID direto
        match = _UUID_RE.search(raw)
        if match:
            deal.clicksign_envelope_key = match.group()
            deal.contract_sent_at = datetime.utcnow()
            db.session.commit()
            flash("Contrato registrado.", "success")
        elif raw:
            flash("Não foi possível encontrar um UUID válido no link. Cole o link completo do ClickSign.", "error")
        return redirect(url_for("crm.deal_contract", deal_id=deal.id))

    settings = SiteSetting.query.get(1)
    # vendedor pode trocar o tipo sugerido via ?type=
    type_override = request.args.get("type")
    if type_override in CONTRACT_LINKS:
        contract_type = type_override
    else:
        contract_type = detect_contract_type(deal)
    contract_link  = CONTRACT_LINKS[contract_type]
    contract_label = CONTRACT_LABELS[contract_type]
    return render_template(
        "crm/deal_contract.html",
        deal=deal,
        settings=settings,
        contract_type=contract_type,
        contract_link=contract_link,
        contract_label=contract_label,
        CONTRACT_LABELS=CONTRACT_LABELS,
    )


@crm_bp.route("/crm/webhooks/clicksign", methods=["POST"])
def clicksign_webhook():
    """Recebe notificações do ClickSign (assinatura concluída)."""
    settings = SiteSetting.query.get(1)
    secret = getattr(settings, "clicksign_webhook_secret", None) or ""

    raw_body   = request.get_data()
    hmac_header = request.headers.get("X-Clicksign-Hmac-Sha256", "")

    if not verify_webhook_hmac(secret, raw_body, hmac_header):
        return jsonify({"error": "invalid signature"}), 401

    try:
        payload = request.get_json(force=True) or {}
    except Exception:
        return jsonify({"error": "invalid json"}), 400

    event_data = parse_webhook_event(payload)

    if event_data["event"] != "auto_close":
        return jsonify({"ok": True, "ignored": True})

    envelope_key = event_data["envelope_key"]
    if not envelope_key:
        return jsonify({"ok": True, "ignored": True})

    deal = CRMDeal.query.filter_by(clicksign_envelope_key=envelope_key).first()
    if not deal:
        return jsonify({"ok": True, "not_found": True})

    deal.contract_signed_at = datetime.utcnow()

    # Move para stage "contrato assinado" se existir
    signed_stage = CRMStage.query.filter(
        CRMStage.name.ilike("%assinado%")
    ).first() or CRMStage.query.filter(
        CRMStage.name.ilike("%ganho%")
    ).first() or CRMStage.query.filter_by(is_won=True).first()
    if signed_stage:
        deal.stage_id = signed_stage.id

    db.session.add(CRMNote(
        deal_id=deal.id,
        user_id=None,
        content=f"Contrato assinado via ClickSign (envelope: {envelope_key}). "
                f"Signatário: {event_data['signer_email'] or event_data['signer_phone'] or '—'}",
        note_type="internal",
    ))
    db.session.commit()
    return jsonify({"ok": True})


@crm_bp.route("/crm/deals/<int:deal_id>/simulate-signed", methods=["POST"])
@login_required
def simulate_signed(deal_id: int):
    """Dev-only: simula webhook de assinatura para testar o fluxo."""
    _require_crm()
    deal = CRMDeal.query.get_or_404(deal_id)
    deal.contract_signed_at = datetime.utcnow()
    signed_stage = (
        CRMStage.query.filter(CRMStage.name.ilike("%assinado%")).first()
        or CRMStage.query.filter_by(is_won=True).first()
    )
    if signed_stage:
        deal.stage_id = signed_stage.id
    db.session.add(CRMNote(
        deal_id=deal.id,
        user_id=current_user.id,
        content="[DEV] Assinatura simulada manualmente.",
        note_type="internal",
    ))
    db.session.commit()
    flash("Assinatura simulada com sucesso.", "success")
    return redirect(url_for("crm.deal_contract", deal_id=deal.id))


@crm_bp.route("/crm/deals/<int:deal_id>/upload-proof", methods=["POST"])
@login_required
def upload_payment_proof(deal_id: int):
    _require_crm()
    deal = CRMDeal.query.get_or_404(deal_id)
    file = request.files.get("proof_file")
    if not file or not file.filename:
        flash("Nenhum arquivo selecionado.", "error")
        return redirect(url_for("crm.deal_contract", deal_id=deal.id))

    file.stream.seek(0, 2)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > 10 * 1024 * 1024:
        flash("Arquivo muito grande (máx 10 MB).", "error")
        return redirect(url_for("crm.deal_contract", deal_id=deal.id))

    ext = os.path.splitext(secure_filename(file.filename))[1].lower()
    if ext not in {".pdf", ".jpg", ".jpeg", ".png"}:
        flash("Formato inválido. Use PDF, JPG ou PNG.", "error")
        return redirect(url_for("crm.deal_contract", deal_id=deal.id))

    filename = f"proof_{deal.id}_{int(datetime.utcnow().timestamp())}{ext}"
    save_dir  = current_app.config.get("UPLOAD_PAYMENTS", current_app.config["UPLOAD_FOLDER"])
    os.makedirs(save_dir, exist_ok=True)
    file.save(os.path.join(save_dir, filename))

    deal.payment_proof_path = f"payments/{filename}"
    deal.payment_proof_at   = datetime.utcnow()
    db.session.add(CRMNote(
        deal_id=deal.id,
        user_id=current_user.id,
        content="Comprovante de pagamento enviado.",
        note_type="internal",
    ))
    db.session.commit()
    flash("Comprovante enviado.", "success")
    return redirect(url_for("crm.deal_contract", deal_id=deal.id))
