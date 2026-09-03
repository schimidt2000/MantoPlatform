"""Endpoints de ESCRITA de Talentos (feature 154).

Reusa o núcleo em `app/talents/talent_ops.py` (mesma lógica dos handlers Jinja). Gate:
CASTING/SUPERADMIN — paridade com `_can_edit_talent()`.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import RoleName
from app.models import Talent, db


def _can_edit_talent() -> bool:
    return any(r.name in (RoleName.SUPERADMIN, RoleName.CASTING) for r in current_user.roles)


def _is_superadmin() -> bool:
    return any(r.name == RoleName.SUPERADMIN for r in current_user.roles)


def _get_talent_or_404(talent_id: int) -> Talent | None:
    return Talent.query.get(talent_id)


@api_bp.route("/talents/<int:talent_id>", methods=["PATCH"])
@api_login_required
def api_update_talent(talent_id: int) -> Any:
    """Edita os dados de um talento (feature 154). CPF só é aplicado se SUPERADMIN."""
    talent = _get_talent_or_404(talent_id)
    if talent is None:
        return json_error("Talento não encontrado", 404)
    if not _can_edit_talent():
        return json_error("Sem permissão", 403)

    from app.talents.talent_ops import get_talent_profile, update_talent_fields

    body = request.get_json(silent=True) or {}
    errors = update_talent_fields(talent, body, is_superadmin=_is_superadmin())
    if errors:
        return json_error("Corrija os campos destacados", 400, fields=errors)

    from app.utils import audit

    audit("edit", "talent", talent.id, talent.full_name, "Perfil editado (API)")
    db.session.commit()
    # `include_sensitive=True`: a view já barrou quem não é CASTING/SUPERADMIN acima.
    result = get_talent_profile(talent, include_sensitive=True)
    result["can_edit"] = True
    return jsonify(result)


@api_bp.route("/talents/bounces/resolve", methods=["POST"])
@api_login_required
def api_resolve_bounce() -> Any:
    """Tira um endereço da fila de emails devolvidos (feature 219).

    Resolve por **endereço**, não por mensagem: falar uma vez com a pessoa fecha as dez tentativas
    falhas daquele email de uma vez.
    """
    if not _can_edit_talent():
        return json_error("Sem permissão", 403)

    from app.talents import bounce_ops
    from app.utils import audit

    body = request.get_json(silent=True) or {}
    address = (body.get("email") or "").strip()
    if not address:
        return json_error("Informe o email", 400, fields={"email": "Obrigatório"})

    resolved = bounce_ops.resolve_email(address, current_user.id, body.get("note"))
    if not resolved:
        return json_error("Nada pendente para esse email", 404)
    audit(
        "edit", "talent", None, address,
        f"Devolução de email resolvida ({resolved} registro(s))",
    )
    db.session.commit()
    return jsonify({"resolved": resolved, "pending_count": bounce_ops.pending_count()})


@api_bp.route("/talents/<int:talent_id>/approve", methods=["POST"])
@api_login_required
def api_approve_talent(talent_id: int) -> Any:
    """Aprova um cadastro pendente (feature 154). Idempotente — paridade com `approve_talent`."""
    talent = _get_talent_or_404(talent_id)
    if talent is None:
        return json_error("Talento não encontrado", 404)
    if not _can_edit_talent():
        return json_error("Sem permissão", 403)

    from app.talents.talent_ops import approve_talent_status

    approve_talent_status(talent)
    db.session.commit()
    return jsonify({"id": talent.id, "status": talent.status})


@api_bp.route("/talents/<int:talent_id>/reject", methods=["POST"])
@api_login_required
def api_reject_talent(talent_id: int) -> Any:
    """Rejeita/exclui um cadastro pendente (feature 154). 400 se não estiver pendente."""
    talent = _get_talent_or_404(talent_id)
    if talent is None:
        return json_error("Talento não encontrado", 404)
    if not _can_edit_talent():
        return json_error("Sem permissão", 403)

    from app.talents.talent_ops import reject_talent_record

    if not reject_talent_record(talent):
        return json_error("Só é possível rejeitar cadastros pendentes", 400)
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.route("/talents/<int:talent_id>/reset-senha", methods=["POST"])
@api_login_required
def api_enviar_reset_senha(talent_id: int) -> Any:
    """Envia ao talento o link de redefinição de senha do portal (feature 274).

    O artista que não consegue entrar tinha dois caminhos, e os dois podem travar: "Esqueci minha
    senha" só funciona se ele digitar exatamente o e-mail do cadastro (e cala quando não bate), e
    "Primeiro Acesso" recusa quem já tem senha. Este endpoint é a saída do lado de dentro, para
    quem está com a ficha aberta e falando com a pessoa.

    Gate `_can_edit_talent()` (CASTING/SUPERADMIN) — mesma régua de quem edita o cadastro. O
    envio fica no `AuditLog`: é uma ação em nome de outra pessoa.
    """
    talent = _get_talent_or_404(talent_id)
    if talent is None:
        return json_error("Talento não encontrado", 404)
    if not _can_edit_talent():
        return json_error("Sem permissão", 403)

    from app.email_service import send_async, send_password_reset_email
    from app.talent_portal.portal_account_ops import PortalAccountError, enviar_reset_pelo_staff
    from app.talent_portal.portal_links import portal_reset_url
    from app.utils import audit

    try:
        resultado = enviar_reset_pelo_staff(
            talent,
            lambda t, url: send_async(send_password_reset_email, t, url),
            portal_reset_url,
        )
    except PortalAccountError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message} if exc.field else None)

    audit(
        "enviou link de redefinição de senha do portal",
        entity_type="Talent",
        entity_id=talent.id,
        entity_name=talent.full_name,
        detail=f"para {resultado['email']}",
    )
    db.session.commit()
    return jsonify(resultado)


@api_bp.route("/talents/<int:talent_id>/notes", methods=["POST"])
@api_login_required
def api_save_talent_notes(talent_id: int) -> Any:
    """Salva anotação interna e nível de alerta (feature 154)."""
    talent = _get_talent_or_404(talent_id)
    if talent is None:
        return json_error("Talento não encontrado", 404)
    if not _can_edit_talent():
        return json_error("Sem permissão", 403)

    from app.talents.talent_ops import get_talent_profile, save_notes

    body = request.get_json(silent=True) or {}
    save_notes(talent, notes=body.get("notes"), warning_level=body.get("warning_level"))
    db.session.commit()
    # `include_sensitive=True`: a view já barrou quem não é CASTING/SUPERADMIN acima.
    result = get_talent_profile(talent, include_sensitive=True)
    result["can_edit"] = True
    return jsonify(result)


@api_bp.route("/talents/<int:talent_id>/photo", methods=["POST"])
@api_login_required
def api_upload_talent_photo(talent_id: int) -> Any:
    """Envia/substitui foto ou documento do talento (feature 155)."""
    talent = _get_talent_or_404(talent_id)
    if talent is None:
        return json_error("Talento não encontrado", 404)
    if not _can_edit_talent():
        return json_error("Sem permissão", 403)

    from app.talents.talent_ops import get_talent_profile, save_talent_photo

    photo_type = request.form.get("photo_type", "")
    error = save_talent_photo(talent, photo_type=photo_type, file_storage=request.files.get("photo"))
    if error:
        return json_error(error, 400, {"photo": error})

    from app.utils import audit

    audit("edit", "talent", talent.id, talent.full_name, f"Foto/documento enviado ({photo_type}, API)")
    db.session.commit()
    # `include_sensitive=True`: a view já barrou quem não é CASTING/SUPERADMIN acima.
    result = get_talent_profile(talent, include_sensitive=True)
    result["can_edit"] = True
    return jsonify(result)


@api_bp.route("/talents/<int:talent_id>/photo", methods=["DELETE"])
@api_login_required
def api_remove_talent_photo(talent_id: int) -> Any:
    """Remove foto ou documento do talento (feature 155). No-op seguro se já vazio."""
    talent = _get_talent_or_404(talent_id)
    if talent is None:
        return json_error("Talento não encontrado", 404)
    if not _can_edit_talent():
        return json_error("Sem permissão", 403)

    from app.talents.talent_ops import get_talent_profile, remove_talent_photo

    photo_type = request.args.get("photo_type", "")
    error = remove_talent_photo(talent, photo_type=photo_type)
    if error:
        return json_error(error, 400, {"photo": error})

    from app.utils import audit

    audit("edit", "talent", talent.id, talent.full_name, f"Foto/documento removido ({photo_type}, API)")
    db.session.commit()
    # `include_sensitive=True`: a view já barrou quem não é CASTING/SUPERADMIN acima.
    result = get_talent_profile(talent, include_sensitive=True)
    result["can_edit"] = True
    return jsonify(result)
