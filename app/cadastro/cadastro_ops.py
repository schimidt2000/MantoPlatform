"""Núcleo compartilhado do cadastro público de talentos (feature 162).

Extraído de ``app/cadastro/routes.py`` (feature 086) para ser reaproveitado tanto pelo handler
Jinja quanto pelo endpoint API (``app/api/cadastro_write.py``) — mesma lógica, duas superfícies
(pesquisa em `specs/162-cadastro-publico-react/research.md` §4).
"""

import os
from dataclasses import dataclass

from werkzeug.datastructures import FileStorage

from app.models import Talent
from app.storage import save_file
from app.talents.importer import (
    _parse_passport_status,
    normalize_tags,
    only_digits,
    parse_date,
)

# Limites de upload (por arquivo). O teto global da requisição é MAX_CONTENT_LENGTH.
PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
DOC_EXTS = PHOTO_EXTS | {".pdf"}
PHOTO_MAX = 8 * 1024 * 1024  # 8 MB
DOC_MAX = 10 * 1024 * 1024  # 10 MB


def _file_size(file: FileStorage) -> int:
    """Tamanho em bytes de um upload, sem consumir o stream."""
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    return size


def validate_upload(
    file: FileStorage | None,
    allowed_exts: set[str],
    max_bytes: int,
    required: bool,
    label: str,
) -> tuple[FileStorage | None, str | None]:
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


def build_phone(form) -> str:
    """Monta o telefone a partir do seletor de país (DDI) + número nacional (feature 092).

    Aceita o formato novo (``phone_ddi`` + ``phone_national``) e cai para o campo ``phone`` legado
    quando necessário. Resultado típico: ``"+55 (11) 99999-9999"``. Não duplica o ``+`` se o
    nacional já o tiver.

    Args:
        form: O ``request.form`` (MultiDict) da submissão.

    Returns:
        Telefone com código de país, ou string vazia se nada foi informado.
    """
    national = (form.get("phone_national") or "").strip()
    if not national:
        return (form.get("phone") or "").strip()
    if national.startswith("+"):
        return national
    ddi = (form.get("phone_ddi") or "+55").strip()
    if not ddi.startswith("+"):
        ddi = "+" + ddi.lstrip("+")
    return f"{ddi} {national}".strip()


def height_to_cm(raw: str) -> int | None:
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


def yes_no(raw: str | None) -> bool | None:
    """Converte "sim"/"nao" do form em bool (ou None se não respondido)."""
    if not raw:
        return None
    val = raw.strip().lower()
    if val in ("sim", "yes", "true", "1"):
        return True
    if val in ("nao", "não", "no", "false", "0"):
        return False
    return None


@dataclass
class SubmissionOutcome:
    """Resultado de processar uma submissão do formulário público de cadastro.

    Exatamente um de ``talent``/``error`` é preenchido, a menos que ``honeypot`` seja `True`
    (nesse caso os dois ficam `None` — nada é criado, mas a submissão não é um erro).
    """

    honeypot: bool
    talent: Talent | None
    error: str | None
    field: str | None


def process_submission(form, files) -> SubmissionOutcome:
    """Valida e monta um ``Talent`` pendente a partir da submissão do formulário público.

    Reaproveitada por ``app/cadastro/routes.py`` (Jinja) e ``app/api/cadastro_write.py`` (API) —
    fonte única da regra de negócio do cadastro (Princípio I). Não adiciona/commita na sessão:
    o chamador decide o que fazer com o ``Talent`` retornado (e como reagir ao honeypot/erro).

    Args:
        form: ``request.form`` (MultiDict) da submissão.
        files: ``request.files`` (MultiDict) da submissão.

    Returns:
        O resultado do processamento — ver `SubmissionOutcome`.
    """
    f = form

    # Honeypot anti-bot: campo oculto que humanos não preenchem.
    if (f.get("website") or "").strip():
        return SubmissionOutcome(honeypot=True, talent=None, error=None, field=None)

    full_name = (f.get("full_name") or "").strip()
    is_foreigner = bool(f.get("is_foreigner"))
    cpf = only_digits(f.get("cpf") or "")
    phone = build_phone(f)
    email = (f.get("email") or "").strip()
    birth_date = parse_date(f.get("birth_date") or "")

    # Múltipla escolha (checkboxes) → texto separado por vírgula (fiel ao Google Form)
    languages = ", ".join(s.strip() for s in f.getlist("languages") if s.strip())
    skills = ", ".join(s.strip() for s in f.getlist("skills") if s.strip())

    # Gênero: a opção "Outro" usa o texto livre digitado
    gender = (f.get("gender") or "").strip()
    if gender == "Outro":
        gender = (f.get("gender_other") or "").strip() or "Outro"

    def _fail(field: str, msg: str) -> SubmissionOutcome:
        return SubmissionOutcome(honeypot=False, talent=None, error=msg, field=field)

    # Obrigatórios (fiel ao formulário original)
    if not full_name:
        return _fail("full_name", "Informe o nome completo.")
    if not gender:
        return _fail("gender", "Selecione o gênero.")
    if not phone:
        return _fail("phone", "Informe um telefone com DDD.")
    if not email:
        return _fail("email", "Informe um e-mail.")
    if not languages:
        return _fail("languages", "Selecione ao menos um idioma.")
    if not birth_date:
        return _fail("birth_date", "Informe a data de nascimento.")
    # CPF é obrigatório só para quem não é estrangeiro (feature 092).
    if not is_foreigner and len(cpf) < 11:
        return _fail("cpf", "CPF inválido — confira os 11 dígitos.")
    for field, value, msg in (
        ("rg", f.get("rg"), "Informe o RG/documento."),
        ("pix_key_type", f.get("pix_key_type"), "Selecione o tipo de chave PIX."),
        ("pix_key", f.get("pix_key"), "Informe a chave PIX."),
        ("race", f.get("race"), "Selecione a raça/cor."),
        ("height", f.get("height"), "Informe a altura."),
        ("clothing_top", f.get("clothing_top"), "Selecione o manequim superior."),
        ("clothing_bottom", f.get("clothing_bottom"), "Selecione o manequim inferior."),
        ("shoe_size", f.get("shoe_size"), "Informe o tamanho do sapato."),
        ("passport", f.get("passport"), "Responda sobre passaporte e visto."),
    ):
        if not (value or "").strip():
            return _fail(field, msg)
    if not skills:
        return _fail("skills", "Selecione ao menos uma habilidade.")

    # CPF duplicado (não se aplica a estrangeiro, que grava cpf = None)
    if not is_foreigner and Talent.query.filter_by(cpf=cpf).first():
        return _fail("cpf", "Este CPF já está cadastrado. Fale com a equipe da Manto.")

    # Uploads (rosto, corpo e documento são obrigatórios; CNH é opcional)
    photo_face, err = validate_upload(
        files.get("photo_face"), PHOTO_EXTS, PHOTO_MAX, True, "a foto do rosto")
    if err:
        return _fail("photo_face", err)
    photo_full, err = validate_upload(
        files.get("photo_full"), PHOTO_EXTS, PHOTO_MAX, True, "a foto de corpo inteiro")
    if err:
        return _fail("photo_full", err)
    doc_photo, err = validate_upload(
        files.get("doc_photo"), DOC_EXTS, DOC_MAX, True, "a foto do documento")
    if err:
        return _fail("doc_photo", err)
    cnh_file, err = validate_upload(
        files.get("cnh_file"), DOC_EXTS, DOC_MAX, False, "o arquivo da CNH")
    if err:
        return _fail("cnh_file", err)

    # Grava arquivos no armazenamento da Manto (local em dev, S3/R2 em produção)
    photo_face_url = save_file(photo_face, "talent_photos") if photo_face else None
    photo_full_url = save_file(photo_full, "talent_photos") if photo_full else None
    doc_photo_url = save_file(doc_photo, "talent_docs") if doc_photo else None
    cnh_file_url = save_file(cnh_file, "talent_docs") if cnh_file else None

    passport_text = (f.get("passport") or "").strip()
    passport_status = _parse_passport_status(passport_text)

    talent = Talent(
        full_name=full_name,
        cpf=(cpf or None) if not is_foreigner else None,
        is_foreigner=is_foreigner,
        artistic_name=(f.get("artistic_name") or "").strip() or None,
        phone=phone or None,
        email_contact=email or None,
        birth_date=birth_date,
        rg=(f.get("rg") or "").strip() or None,
        gender=gender or None,
        race=(f.get("race") or "").strip() or None,
        languages=languages or None,
        skills=skills or None,
        tags=normalize_tags(skills),
        height_cm=height_to_cm(f.get("height") or ""),
        clothing_size_top=(f.get("clothing_top") or "").strip() or None,
        clothing_size_bottom=(f.get("clothing_bottom") or "").strip() or None,
        shoe_size=(f.get("shoe_size") or "").strip() or None,
        passport_status=passport_status,
        passport_visa_text=passport_text or None,
        has_visa=(passport_status == "visa"),
        pix_key=(f.get("pix_key") or "").strip() or None,
        pix_key_type=(f.get("pix_key_type") or "").strip() or None,
        pix_key_secondary=(f.get("pix_key_secondary") or "").strip() or None,
        worked_before=yes_no(f.get("worked_before")),
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
    return SubmissionOutcome(honeypot=False, talent=talent, error=None, field=None)


def check_cpf_exists(raw_cpf: str) -> tuple[bool, bool]:
    """Checa se um CPF (com ou sem máscara) já está cadastrado.

    Returns:
        ``(exists, valid)`` — ``valid=False`` quando o CPF tem menos de 11 dígitos (``exists``
        sempre `False` nesse caso).
    """
    cpf = only_digits(raw_cpf)
    if len(cpf) < 11:
        return False, False
    return Talent.query.filter_by(cpf=cpf).first() is not None, True
