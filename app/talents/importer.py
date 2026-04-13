import re
import unicodedata
from datetime import datetime, date, timedelta
from typing import Dict, Any, Iterable, Optional

from app.models import Talent, ImportState
from .. import db
from .sheets_client import get_sheets_service


def only_digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def normalize_header(value: str) -> str:
    text = (value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_date(value: Any) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, (int, float)):
        # Google Sheets date serial (days since 1899-12-30)
        try:
            return date(1899, 12, 30) + timedelta(days=int(value))
        except Exception:
            return None
    if isinstance(value, str):
        raw = value.strip()
        # Serial numérico que chegou como string (ex: "36531")
        if raw.lstrip("-").isdigit():
            try:
                return date(1899, 12, 30) + timedelta(days=int(raw))
            except Exception:
                pass
        for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
    return None


def normalize_tags(raw: str) -> str:
    if not raw:
        return ""
    parts = re.split(r"[;,/\n]+", raw)
    cleaned = []
    for p in parts:
        tag = normalize_header(p)
        if tag:
            cleaned.append(tag)
    return ",".join(dict.fromkeys(cleaned))


def drive_direct_url(raw_url: str) -> str:
    if not raw_url:
        return ""
    url = raw_url.strip()
    match = re.search(r"/d/([A-Za-z0-9_-]+)", url)
    if not match:
        match = re.search(r"[?&]id=([A-Za-z0-9_-]+)", url)
    if not match:
        return url
    file_id = match.group(1)
    return f"https://lh3.googleusercontent.com/d/{file_id}"


def first_present(row: list, header_map: Dict[str, int], candidates: Iterable[str]) -> str:
    for name in candidates:
        key = normalize_header(name)
        idx = header_map.get(key)
        if idx is not None and idx < len(row):
            val = row[idx]
            return "" if val is None else str(val).strip()
    # fallback: substring match
    for name in candidates:
        key = normalize_header(name)
        if not key:
            continue
        for header_key, idx in header_map.items():
            if key in header_key and idx < len(row):
                val = row[idx]
                return "" if val is None else str(val).strip()
    return ""


def import_new_talents_from_sheet(
    spreadsheet_id: str,
    sheet_name: str,
    credentials_path: str,
    import_key: str = "talents_form",
    header_row: int = 1,
    max_cols: str = "AZ",  # header pode passar de Z
) -> Dict[str, Any]:
    """
    Le so linhas novas a partir de ImportState.last_row + 1.
    Cria Talent se CPF novo. Marca como 'pending'.
    Atualiza ImportState.last_row ao final.
    """

    service = get_sheets_service(credentials_path)

    # 0) Garantir ImportState
    state = ImportState.query.filter_by(key=import_key).first()
    if not state:
        state = ImportState(key=import_key, last_row=header_row)
        db.session.add(state)
        db.session.commit()

    # 1) Ler header para mapear colunas por nome
    header_range = f"{sheet_name}!A{header_row}:{max_cols}{header_row}"
    header_resp = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=header_range,
            valueRenderOption="UNFORMATTED_VALUE",
        )
        .execute()
    )

    header = (header_resp.get("values") or [[]])[0]
    header_map = {
        normalize_header(str(name)): idx
        for idx, name in enumerate(header)
        if name is not None and str(name).strip() != ""
    }

    # 2) Ler so novas linhas
    start_row = state.last_row + 1
    data_range = f"{sheet_name}!A{start_row}:{max_cols}"

    data_resp = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=data_range,
            valueRenderOption="UNFORMATTED_VALUE",
        )
        .execute()
    )

    rows = data_resp.get("values") or []
    if not rows:
        return {"imported": 0, "skipped": 0, "skipped_details": [], "new_last_row": state.last_row}

    imported = 0
    skipped = 0
    skipped_details: list = []

    # 3) Importar
    for offset, row in enumerate(rows):
        current_sheet_row = start_row + offset

        full_name = first_present(row, header_map, ["Nome Completo", "Nome"])
        artistic_name = first_present(row, header_map, ["Nome Artistico"])
        phone = first_present(row, header_map, ["Telefone com DDD", "Telefone"])
        email = first_present(row, header_map, ["E-mail", "Email"])
        birth_date_raw = first_present(row, header_map, [
            "Data de Nascimento",
            "Data de nascimento",
            "Nascimento",
            "Data Nascimento",
            "date of birth",
        ])

        cpf = only_digits(first_present(row, header_map, ["CPF", "CPF (Cadastro de Pessoas Fisicas)"]))
        rg = first_present(row, header_map, ["RG", "RG (Registro Geral)"])

        pix_primary = first_present(row, header_map, ["Chave PIX"])
        pix_secondary = first_present(row, header_map, ["Chave PIX (secundaria)", "Chave PIX Secundaria"])

        height_raw = first_present(row, header_map, ["Altura (em metros, ex: 1,75)", "Altura"])
        clothing_top = first_present(row, header_map, ["Tamanho de Manequim/Roupa Superior"])
        clothing_bottom = first_present(
            row,
            header_map,
            ["Tamanho de Manequim/Roupa Inferior (Calcas, Saias, Shorts)"],
        )
        shoe_size = first_present(row, header_map, ["Tamanho do Sapato (Numeracao Brasileira)", "Tamanho do Sapato"])

        languages = first_present(row, header_map, ["Idiomas"])
        skills = first_present(row, header_map, ["Habilidades", "Habilidades (Marque todas as opcoes que te definem)"])
        race = first_present(row, header_map, ["Raca"])

        passport_visa_text = first_present(row, header_map, ["Possui Passaporte e visto americano?"])
        passport_visa_norm = normalize_header(passport_visa_text)
        has_visa = passport_visa_norm in ("sim", "yes", "true", "1", "x")

        photo_face = drive_direct_url(
            first_present(row, header_map, ["Foto do Rosto (Close-up)", "Foto do Rosto"])
        )
        photo_body = drive_direct_url(first_present(row, header_map, ["Foto de Corpo Inteiro"]))

        # Carro (opcional)
        car_model = first_present(row, header_map, ["Modelo do Carro"])
        car_brand = first_present(row, header_map, ["Marca do Carro"])
        car_year = first_present(row, header_map, ["Ano do Carro"])
        car_plate = first_present(row, header_map, ["Placa do Carro"])

        # CNH (opcional)
        cnh_exp_raw = first_present(row, header_map, ["Data de vencimento da CNH"])
        cnh_file = first_present(row, header_map, ["Foto ou arquivo da CNH aberta"])

        # campos extras
        gender = first_present(row, header_map, ["Genero", "Gênero"])
        doc_photo = drive_direct_url(
            first_present(row, header_map, ["Foto do seu documento (CPF, RG ou CNH)", "Foto do seu documento"])
        )
        pix_key_type = first_present(row, header_map, ["Tipo de chave pix", "Tipo de chave PIX"])
        worked_before_raw = first_present(row, header_map, ["Ja trabalhou com a Manto?", "Já trabalhou com a Manto?"])
        worked_before = normalize_header(worked_before_raw) in ("sim", "yes", "true", "1", "x") if worked_before_raw else None
        how_found_us = first_present(row, header_map, ["Onde conheceu a Manto?", "Onde conheceu a manto"])

        # Regras minimas
        if not full_name or len(cpf) < 11:
            motivo = "nome ausente" if not full_name else f"CPF inválido ({cpf or 'vazio'})"
            skipped_details.append({"linha": current_sheet_row, "nome": full_name or "(sem nome)", "motivo": motivo})
            skipped += 1
            continue

        # CPF unico — atualiza campos vazios se já existe
        exists = Talent.query.filter_by(cpf=cpf).first()
        if exists:
            changed = False
            if not exists.birth_date and parse_date(birth_date_raw):
                exists.birth_date = parse_date(birth_date_raw)
                changed = True
            if not exists.rg and rg:
                exists.rg = rg
                changed = True
            if exists.worked_before is None and worked_before is not None:
                exists.worked_before = worked_before
                changed = True
            if changed:
                db.session.commit()
            skipped_details.append({"linha": current_sheet_row, "nome": full_name, "motivo": f"CPF já cadastrado ({cpf})"})
            skipped += 1
            continue

        # Altura em metros -> cm (ex: "1,75" => 175)
        height_cm = None
        if height_raw:
            try:
                meters = float(height_raw.replace(",", "."))
                height_cm = int(round(meters * 100))
            except ValueError:
                height_cm = None

        t = Talent(
            full_name=full_name,
            cpf=cpf,
            rg=rg or None,
            artistic_name=artistic_name or None,
            phone=phone or None,
            email_contact=email or None,
            birth_date=parse_date(birth_date_raw),
            race=race or None,
            pix_key=pix_primary or None,
            pix_key_secondary=pix_secondary or None,
            height_cm=height_cm,
            clothing_size_top=clothing_top or None,
            clothing_size_bottom=clothing_bottom or None,
            shoe_size=shoe_size or None,
            languages=languages or None,
            skills=skills or None,
            tags=normalize_tags(skills),
            passport_visa_text=passport_visa_text or None,
            photo_face_path=photo_face or None,
            photo_full_path=photo_body or None,
            car_model=car_model or None,
            car_brand=car_brand or None,
            car_year=car_year or None,
            car_plate=car_plate or None,
            cnh_expiration=parse_date(cnh_exp_raw),
            cnh_file_path=cnh_file or None,
            has_visa=has_visa,
            gender=gender or None,
            doc_photo_path=doc_photo or None,
            pix_key_type=pix_key_type or None,
            worked_before=worked_before,
            how_found_us=how_found_us or None,
            status="active",
            source="google_form",
            source_row=current_sheet_row,
        )

        db.session.add(t)
        imported += 1

    # 4) Atualiza last_row para "ultima linha lida"
    state.last_row = start_row + len(rows) - 1
    db.session.commit()

    return {"imported": imported, "skipped": skipped, "skipped_details": skipped_details, "new_last_row": state.last_row}
