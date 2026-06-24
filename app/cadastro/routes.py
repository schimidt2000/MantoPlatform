"""Formulário público de cadastro de talento (feature 086).

Substitui o Google Form: as fotos/documentos vão para o armazenamento da Manto (via ``save_file``),
não dependem do Drive do candidato. Cada envio válido cria um ``Talent`` pendente para revisão.
"""
import os

from flask import Blueprint, redirect, render_template, request, url_for
from werkzeug.datastructures import FileStorage

from app import db, limiter
from app.models import Talent
from app.storage import save_file
from app.talents.importer import (
    _parse_passport_status,
    normalize_tags,
    only_digits,
    parse_date,
)

cadastro_bp = Blueprint("cadastro", __name__, url_prefix="/cadastro")

# Limites de upload (por arquivo). O teto global da requisição é MAX_CONTENT_LENGTH.
_PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
_DOC_EXTS = _PHOTO_EXTS | {".pdf"}
_PHOTO_MAX = 8 * 1024 * 1024   # 8 MB
_DOC_MAX = 10 * 1024 * 1024    # 10 MB


def _file_size(file: FileStorage) -> int:
    """Tamanho em bytes de um upload, sem consumir o stream."""
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    return size


def _validate_upload(file: FileStorage | None, allowed_exts: set[str], max_bytes: int,
                     required: bool, label: str) -> tuple[FileStorage | None, str | None]:
    """Valida um upload opcional/obrigatório por extensão e tamanho.

    Returns:
        (file_ou_None, erro_ou_None). ``file`` só volta quando há conteúdo válido.
    """
    if not file or not file.filename:
        if required:
            return None, f"Anexe {label}."
        return None, None
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_exts:
        tipos = ", ".join(sorted(e.lstrip(".").upper() for e in allowed_exts))
        return None, f"{label}: tipo não permitido (use {tipos})."
    if _file_size(file) > max_bytes:
        return None, f"{label}: arquivo muito grande (máx. {max_bytes // (1024 * 1024)} MB)."
    return file, None


def _height_to_cm(raw: str) -> int | None:
    """Converte altura em metros ("1,75") para centímetros (175)."""
    if not raw:
        return None
    try:
        meters = float(raw.replace(",", ".").strip())
    except ValueError:
        return None
    if meters <= 0:
        return None
    # Aceita tanto "1,75" (metros) quanto "175" (já em cm)
    return int(round(meters * 100)) if meters < 3 else int(round(meters))


@cadastro_bp.route("/", methods=["GET"])
def form():
    """Renderiza o formulário público de cadastro."""
    return render_template("cadastro/form.html", form={}, error=None)


@cadastro_bp.route("/enviado", methods=["GET"])
def enviado():
    """Página de confirmação após envio bem-sucedido."""
    return render_template("cadastro/success.html")


@cadastro_bp.route("/", methods=["POST"])
@limiter.limit("10 per hour")
def submit():
    """Recebe o cadastro: valida, salva arquivos e cria um talento pendente."""
    f = request.form

    def _render_error(msg: str):
        return render_template("cadastro/form.html", form=f, error=msg), 400

    # Honeypot anti-bot: campo oculto que humanos não preenchem.
    if (f.get("website") or "").strip():
        return redirect(url_for("cadastro.enviado"))

    full_name = (f.get("full_name") or "").strip()
    cpf = only_digits(f.get("cpf") or "")
    phone = (f.get("phone") or "").strip()
    email = (f.get("email") or "").strip()
    birth_date = parse_date(f.get("birth_date") or "")

    # Obrigatórios mínimos
    if not full_name:
        return _render_error("Informe o nome completo.")
    if len(cpf) < 11:
        return _render_error("CPF inválido — confira os 11 dígitos.")
    if not phone:
        return _render_error("Informe um telefone com DDD.")
    if not email:
        return _render_error("Informe um e-mail.")

    # CPF duplicado
    if Talent.query.filter_by(cpf=cpf).first():
        return _render_error("Este CPF já está cadastrado. Fale com a equipe da Manto.")

    # Uploads (rosto, corpo e documento são obrigatórios; CNH é opcional)
    photo_face, err = _validate_upload(
        request.files.get("photo_face"), _PHOTO_EXTS, _PHOTO_MAX, True, "a foto do rosto")
    if err:
        return _render_error(err)
    photo_full, err = _validate_upload(
        request.files.get("photo_full"), _PHOTO_EXTS, _PHOTO_MAX, True, "a foto de corpo inteiro")
    if err:
        return _render_error(err)
    doc_photo, err = _validate_upload(
        request.files.get("doc_photo"), _DOC_EXTS, _DOC_MAX, True, "a foto do documento")
    if err:
        return _render_error(err)
    cnh_file, err = _validate_upload(
        request.files.get("cnh_file"), _DOC_EXTS, _DOC_MAX, False, "o arquivo da CNH")
    if err:
        return _render_error(err)

    # Grava arquivos no armazenamento da Manto (local em dev, S3/R2 em produção)
    photo_face_url = save_file(photo_face, "talent_photos") if photo_face else None
    photo_full_url = save_file(photo_full, "talent_photos") if photo_full else None
    doc_photo_url = save_file(doc_photo, "talent_docs") if doc_photo else None
    cnh_file_url = save_file(cnh_file, "talent_docs") if cnh_file else None

    skills = (f.get("skills") or "").strip()
    passport_text = (f.get("passport") or "").strip()
    passport_status = _parse_passport_status(passport_text)

    talent = Talent(
        full_name=full_name,
        cpf=cpf,
        artistic_name=(f.get("artistic_name") or "").strip() or None,
        phone=phone or None,
        email_contact=email or None,
        birth_date=birth_date,
        rg=(f.get("rg") or "").strip() or None,
        gender=(f.get("gender") or "").strip() or None,
        race=(f.get("race") or "").strip() or None,
        languages=(f.get("languages") or "").strip() or None,
        skills=skills or None,
        tags=normalize_tags(skills),
        height_cm=_height_to_cm(f.get("height") or ""),
        clothing_size_top=(f.get("clothing_top") or "").strip() or None,
        clothing_size_bottom=(f.get("clothing_bottom") or "").strip() or None,
        shoe_size=(f.get("shoe_size") or "").strip() or None,
        passport_status=passport_status,
        passport_visa_text=passport_text or None,
        has_visa=(passport_status == "visa"),
        pix_key=(f.get("pix_key") or "").strip() or None,
        pix_key_type=(f.get("pix_key_type") or "").strip() or None,
        pix_key_secondary=(f.get("pix_key_secondary") or "").strip() or None,
        worked_before=_yes_no(f.get("worked_before")),
        how_found_us=(f.get("how_found_us") or "").strip() or None,
        car_model=(f.get("car_model") or "").strip() or None,
        car_brand=(f.get("car_brand") or "").strip() or None,
        car_year=(f.get("car_year") or "").strip() or None,
        car_plate=(f.get("car_plate") or "").strip() or None,
        cnh_expiration=parse_date(f.get("cnh_expiration") or ""),
        cnh_file_path=cnh_file_url,
        photo_face_path=photo_face_url,
        photo_full_path=photo_full_url,
        doc_photo_path=doc_photo_url,
        status="pending",
        source="public_form",
    )
    db.session.add(talent)
    db.session.commit()
    return redirect(url_for("cadastro.enviado"))


def _yes_no(raw: str | None) -> bool | None:
    """Converte "sim"/"nao" do form em bool (ou None se não respondido)."""
    if not raw:
        return None
    val = raw.strip().lower()
    if val in ("sim", "yes", "true", "1"):
        return True
    if val in ("nao", "não", "no", "false", "0"):
        return False
    return None
