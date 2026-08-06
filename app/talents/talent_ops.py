"""Núcleo de Talentos como fonte única de lógica (feature 154).

Mesmo padrão de `casting_ops.py`/`event_ops.py`/`observation_ops.py`: cada função recebe
parâmetros explícitos (sem `request.form`, `flash` ou `current_user`), para ser reusada pelos
dois adaptadores finos — o handler Jinja (`app/talents/routes.py`) e os endpoints JSON
(`app/api/talents_read.py`/`app/api/talents_write.py`). Upload/remoção de foto e documento
(feature 155) recebem o `FileStorage`/`photo_type` já extraídos pelo wrapper.
"""

import re
import unicodedata

from sqlalchemy import or_

from app.models import EventRole, Talent

PAGE_SIZE = 60

# Campos do perfil que só saem para quem tem papel de gestão de talento (CASTING/SUPERADMIN):
# dado pessoal sensível (LGPD), chave PIX, caminho do documento de identidade/CNH, placa do
# carro e anotação interna. `GET /api/talents/<id>` exigia só autenticação, então MARKETING,
# ARTISTA_3D, ENSAIO ou FIGURINO liam o CPF do elenco inteiro — e o caminho do RG junto.
#
# Os campos são zerados, não removidos: a ficha do React lê essas chaves direto (`t.cpf`,
# `t.doc_photo_path`), e sumir com elas trocaria "campo vazio" por comportamento indefinido.
TALENT_SENSITIVE_FIELDS = (
    "rg",
    "cpf",
    "pix_key",
    "pix_key_secondary",
    "pix_key_type",
    "doc_photo_path",
    "cnh_file_path",
    "cnh_expiration",
    "car_plate",
    "notes",
)
# `warning_level` NÃO entra aqui de propósito: `search_talents` já o devolve para todo o elenco a
# qualquer autenticado, e a grade de talentos desenha o alerta a partir dele. Redigir só no
# detalhe deixaria a ficha incoerente com a listagem sem esconder nada de fato. É sinalização
# operacional, não dado pessoal — diferente de `notes`, que é texto livre e continua protegido.

_SIZE_OPTIONS = ["XGG", "GG", "G", "M", "P", "XP"]
_SHOE_OPTIONS = [str(n) for n in range(33, 48)]
_PASSPORT_OPTIONS = [
    ("visa", "passaporte + visto americano"),
    ("passport", "passaporte sem visto"),
    ("none", "sem passaporte"),
]


def _normalize_header(value: str) -> str:
    text = (value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _split_values(raw: str) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[;,/\n]+", raw)
    return [p.strip() for p in parts if p and p.strip()]


def search_talents(
    *,
    status: str = "active",
    q: str = "",
    ja_trabalhou: bool = False,
    language: list[str] | None = None,
    race: list[str] | None = None,
    top: list[str] | None = None,
    bottom: list[str] | None = None,
    shoe: list[str] | None = None,
    height_op: str = "gte",
    height_value: str | None = None,
    passport: list[str] | None = None,
    tags: list[str] | None = None,
    character: str = "",
    page: int = 1,
    page_size: int = PAGE_SIZE,
) -> dict:
    """Busca/filtra talentos paginados — mesma lógica de `list_talents` (Jinja).

    Args:
        status: `"active"` ou `"pending"`.
        q: texto buscado em nome/nome artístico.
        ja_trabalhou: filtra só quem já trabalhou com a Manto (aplicável a qualquer status).
        language, race, top, bottom, shoe, passport, tags: filtros de múltipla escolha
            (só considerados quando `status == "active"`, mesma regra de hoje).
        height_op: `"gte"`, `"lte"` ou `"eq"` (feature 180).
        height_value: valor de altura em cm (string, convertido internamente).
        character: nome de personagem já interpretado (busca no histórico de `EventRole`).
        page: página (1-based).
        page_size: itens por página.

    Returns:
        Dict com `items` (talentos + `character_matches` por item), `total`, `page`, `pages`,
        `pending_count`, e `filter_options` (presente só quando `status == "active"`).
    """
    query = Talent.query.filter_by(status=status)
    if q:
        query = query.filter(
            or_(Talent.full_name.ilike(f"%{q}%"), Talent.artistic_name.ilike(f"%{q}%"))
        )
    if ja_trabalhou:
        query = query.filter(Talent.worked_before.is_(True))

    character_matches: dict[int, dict[str, int]] = {}
    filter_options: dict | None = None

    if status == "active":
        if language:
            query = query.filter(or_(*[Talent.languages.ilike(f"%{v}%") for v in language]))
        if race:
            query = query.filter(Talent.race.in_(race))
        if top:
            query = query.filter(Talent.clothing_size_top.in_(top))
        if bottom:
            query = query.filter(Talent.clothing_size_bottom.in_(bottom))
        if shoe:
            query = query.filter(Talent.shoe_size.in_(shoe))
        if height_value:
            try:
                height_num = int(height_value)
                if height_op == "lte":
                    query = query.filter(Talent.height_cm <= height_num)
                elif height_op == "eq":
                    query = query.filter(Talent.height_cm == height_num)
                else:
                    query = query.filter(Talent.height_cm >= height_num)
            except ValueError:
                pass
        if passport:
            query = query.filter(or_(*[Talent.passport_status == v for v in passport]))
        if tags:
            normalized = [_normalize_header(t) for t in tags]
            tag_filters = [Talent.tags.ilike(f"%{t}%") for t in normalized if t]
            if tag_filters:
                query = query.filter(or_(*tag_filters))
        if character:
            matching_roles = EventRole.query.filter(
                EventRole.character_name.ilike(f"%{character}%"),
                EventRole.assigned_at.isnot(None),
                EventRole.talent_id.isnot(None),
            ).all()
            matching_ids = {r.talent_id for r in matching_roles}
            query = (
                query.filter(Talent.id.in_(matching_ids)) if matching_ids else query.filter(False)
            )
            for r in matching_roles:
                bucket = character_matches.setdefault(r.talent_id, {})
                bucket[r.character_name] = bucket.get(r.character_name, 0) + 1

        all_active = Talent.query.filter_by(status="active").all()
        filter_options = {
            "languages": sorted({p for t in all_active for p in _split_values(t.languages or "")}),
            "races": sorted({t.race for t in all_active if t.race}),
            "tags": sorted({p for t in all_active for p in _split_values(t.tags or "")}),
            "sizes": _SIZE_OPTIONS,
            "shoes": _SHOE_OPTIONS,
            "passport": _PASSPORT_OPTIONS,
        }

    page = max(1, page)
    pagination = query.order_by(Talent.full_name.asc()).paginate(
        page=page, per_page=page_size, error_out=False
    )
    pending_count = Talent.query.filter_by(status="pending").count()

    items = [
        {
            "id": t.id,
            "full_name": t.full_name,
            "artistic_name": t.artistic_name,
            "status": t.status,
            "warning_level": t.warning_level,
            "photo_face_path": t.photo_face_path,
            "height_cm": t.height_cm,
            "clothing_size_top": t.clothing_size_top,
            "clothing_size_bottom": t.clothing_size_bottom,
            "shoe_size": t.shoe_size,
            "character_matches": character_matches.get(t.id, {}),
        }
        for t in pagination.items
    ]

    result = {
        "items": items,
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
        "pending_count": pending_count,
    }
    if filter_options is not None:
        result["filter_options"] = filter_options
    return result


def get_talent_profile(
    talent: Talent, *, date_from=None, date_to=None, include_sensitive: bool = False
) -> dict:
    """Monta o perfil completo de um talento — mesma lógica de `talent_detail` (Jinja).

    Não inclui avaliações recebidas/dadas (`EventRating`/`EventSubRating`) — ficam fora desta
    fatia (ver spec.md Assumptions); o wrapper Jinja calcula esses dois blocos separadamente.

    Args:
        talent: o talento.
        date_from: início do recorte do histórico (inclusive), ou None.
        date_to: fim do recorte do histórico (exclusive — já deve vir com +1 dia aplicado pelo
            chamador, mesma convenção de hoje), ou None.
        include_sensitive: quando False (padrão **seguro**), zera `TALENT_SENSITIVE_FIELDS`.
            O chamador só passa True depois de checar o papel de gestão de talento — o padrão
            é fechado para que um endpoint novo que esqueça o gate vaze nada.

    Returns:
        Dict com `talent` (campos completos) e `history` (itens + totais).
    """
    from app.models import CalendarEvent

    hist_q = (
        EventRole.query.filter(EventRole.talent_id == talent.id)
        .join(CalendarEvent)
        .filter(EventRole.assigned_at.isnot(None))
        .order_by(CalendarEvent.start_at.desc())
    )
    if date_from:
        hist_q = hist_q.filter(CalendarEvent.start_at >= date_from)
    if date_to:
        hist_q = hist_q.filter(CalendarEvent.start_at < date_to)
    history = hist_q.all()

    talent_data = {
        "id": talent.id,
        "full_name": talent.full_name,
        "artistic_name": talent.artistic_name,
        "status": talent.status,
        "gender": talent.gender,
        "birth_date": talent.birth_date.isoformat() if talent.birth_date else None,
        "race": talent.race,
        "languages": talent.languages,
        "is_foreigner": talent.is_foreigner,
        "phone": talent.phone,
        "email_contact": talent.email_contact,
        # Feature 219: `null` = o talento nunca clicou no link de confirmação. Não é erro por si
        # só (cadastro antigo nunca recebeu o email), mas junto com uma devolução na fila é o
        # sinal de que o endereço não presta.
        "email_verified_at": (
            talent.email_verified_at.isoformat() if talent.email_verified_at else None
        ),
        "tags": talent.tags,
        "skills": talent.skills,
        "height_cm": talent.height_cm,
        "clothing_size_top": talent.clothing_size_top,
        "clothing_size_bottom": talent.clothing_size_bottom,
        "shoe_size": talent.shoe_size,
        "passport_status": talent.passport_status,
        "rg": talent.rg,
        "cpf": talent.cpf,
        "pix_key": talent.pix_key,
        "pix_key_secondary": talent.pix_key_secondary,
        "pix_key_type": talent.pix_key_type,
        "photo_face_path": talent.photo_face_path,
        "photo_full_path": talent.photo_full_path,
        "doc_photo_path": talent.doc_photo_path,
        "cnh_file_path": talent.cnh_file_path,
        "cnh_expiration": talent.cnh_expiration.isoformat() if talent.cnh_expiration else None,
        "car_brand": talent.car_brand,
        "car_model": talent.car_model,
        "car_year": talent.car_year,
        "car_plate": talent.car_plate,
        "worked_before": talent.worked_before,
        "how_found_us": talent.how_found_us,
        "notes": talent.notes,
        "warning_level": talent.warning_level,
    }

    if not include_sensitive:
        for field in TALENT_SENSITIVE_FIELDS:
            talent_data[field] = None

    last = history[0] if history else None
    return {
        "talent": talent_data,
        "history": {
            "items": [
                {
                    "event_id": r.event_id,
                    "event_title": r.event.title if r.event else None,
                    "character_name": r.character_name,
                    "cache_value": float(r.cache_value) if r.cache_value is not None else None,
                    "start_at": r.event.start_at.isoformat()
                    if r.event and r.event.start_at
                    else None,
                }
                for r in history
            ],
            "total_events": len({r.event_id for r in history}),
            "total_earned": float(sum(r.cache_value or 0 for r in history)),
            "characters_done": sorted({r.character_name for r in history}),
            "last_event": (
                {
                    "event_id": last.event_id,
                    "event_title": last.event.title if last.event else None,
                    "character_name": last.character_name,
                    "start_at": last.event.start_at.isoformat()
                    if last.event and last.event.start_at
                    else None,
                }
                if last is not None
                else None
            ),
        },
    }


def approve_talent_status(talent: Talent) -> None:
    """Aprova um cadastro, tornando-o ativo. Paridade com `approve_talent` — idempotente, não
    valida o status atual (mesmo comportamento de hoje)."""
    talent.status = "active"


def reject_talent_record(talent: Talent) -> bool:
    """Rejeita/exclui um cadastro pendente. Paridade com `reject_talent`.

    Returns:
        True se o talento estava pendente (e foi removido da sessão); False se não estava
        (nada é alterado).
    """
    if talent.status != "pending":
        return False
    from app import db

    db.session.delete(talent)
    return True


_WARNING_LEVELS = {"", "leve", "moderado", "grave"}
_PASSPORT_STATUSES = {"visa", "passport", "none"}


def update_talent_fields(talent: Talent, data: dict, *, is_superadmin: bool) -> dict[str, str]:
    """Atualiza os dados editáveis de um talento. Paridade com `edit_talent`.

    Args:
        talent: o talento a atualizar.
        data: campos vindos do form/JSON (mesmos nomes de `edit_talent`).
        is_superadmin: se True, permite alterar `cpf` (validado); se False, `cpf` em `data` é
            ignorado silenciosamente (paridade: o campo nem aparece no form para quem não é
            superadmin).

    Returns:
        Mapa de erros campo→mensagem (vazio = sucesso e talento já atualizado).
    """
    if is_superadmin and data.get("cpf") is not None:
        from app.talents.importer import only_digits

        cpf_raw = only_digits(data.get("cpf") or "")
        if cpf_raw and cpf_raw != talent.cpf:
            if len(cpf_raw) != 11:
                return {"cpf": "CPF inválido: informe 11 dígitos."}
            if Talent.query.filter(Talent.cpf == cpf_raw, Talent.id != talent.id).first():
                return {"cpf": "CPF já cadastrado para outro talento."}
            talent.cpf = cpf_raw

    def _str_or_none(key: str) -> str | None:
        return (data.get(key) or "").strip() or None if key in data else getattr(talent, key)

    talent.full_name = (data.get("full_name") or "").strip() or talent.full_name
    talent.artistic_name = _str_or_none("artistic_name")
    talent.phone = _str_or_none("phone")

    # Trocar o email é justamente o desfecho de uma pendência da fila de devoluções (feature 219):
    # as falhas do endereço antigo deixam de ser pendência de alguém e saem da fila sozinhas.
    email_antigo = talent.email_contact
    talent.email_contact = _str_or_none("email_contact")
    if email_antigo and email_antigo != talent.email_contact:
        from app.talents import bounce_ops

        bounce_ops.clear_for_email(email_antigo)
    talent.gender = _str_or_none("gender")
    talent.race = _str_or_none("race")
    talent.languages = _str_or_none("languages")
    talent.skills = _str_or_none("skills")
    talent.tags = _str_or_none("tags")
    talent.pix_key = _str_or_none("pix_key")
    talent.pix_key_secondary = _str_or_none("pix_key_secondary")
    talent.pix_key_type = _str_or_none("pix_key_type")
    talent.rg = _str_or_none("rg")

    if "passport_status" in data:
        ps = (data.get("passport_status") or "").strip()
        talent.passport_status = ps if ps in _PASSPORT_STATUSES else None
        talent.has_visa = talent.passport_status == "visa"

    talent.how_found_us = _str_or_none("how_found_us")
    if "worked_before" in data:
        wb = data.get("worked_before")
        if wb is None or wb == "":
            talent.worked_before = None
        elif isinstance(wb, bool):
            talent.worked_before = wb
        else:
            # Paridade com o form Jinja: campo cru "1"/"0" (select), não um booleano.
            talent.worked_before = str(wb) == "1"
    talent.car_brand = _str_or_none("car_brand")
    talent.car_model = _str_or_none("car_model")
    talent.car_year = _str_or_none("car_year")
    talent.car_plate = _str_or_none("car_plate")

    if "height_cm" in data:
        try:
            talent.height_cm = int(data["height_cm"]) if data["height_cm"] else None
        except (ValueError, TypeError):
            pass

    talent.clothing_size_top = _str_or_none("clothing_size_top")
    talent.clothing_size_bottom = _str_or_none("clothing_size_bottom")
    talent.shoe_size = _str_or_none("shoe_size")

    if "birth_date" in data or "cnh_expiration" in data:
        from app.talents.importer import parse_date

        if "birth_date" in data:
            talent.birth_date = parse_date(data.get("birth_date") or "")
        if "cnh_expiration" in data:
            talent.cnh_expiration = parse_date(data.get("cnh_expiration") or "")

    return {}


def save_notes(talent: Talent, *, notes: str | None, warning_level: str | None) -> None:
    """Salva anotação interna e nível de alerta. Paridade com `save_talent_notes`."""
    talent.notes = (notes or "").strip() or None
    level = (warning_level or "").strip()
    talent.warning_level = level if level in _WARNING_LEVELS and level else None


_PHOTO_FIELDS = {
    "face": "photo_face_path",
    "full": "photo_full_path",
    "doc": "doc_photo_path",
    "cnh": "cnh_file_path",
}
_DOC_PHOTO_TYPES = {"doc", "cnh"}
_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")
_DOC_EXTS = _IMAGE_EXTS + (".pdf",)


def save_talent_photo(talent: Talent, *, photo_type: str, file_storage) -> str | None:
    """Salva/substitui a foto ou documento de um talento (feature 155).

    Paridade com `upload_talent_photo`: valida extensão por `photo_type`, apaga o arquivo
    anterior do mesmo campo antes de salvar o novo (nunca acumula arquivo órfão).

    Returns:
        Mensagem de erro amigável, ou `None` em caso de sucesso.
    """
    import os
    import uuid as _uuid

    from werkzeug.utils import secure_filename

    from app.storage import delete_file, save_file

    field_name = _PHOTO_FIELDS.get(photo_type)
    if field_name is None:
        return "Tipo de foto/documento inválido."
    if file_storage is None or not file_storage.filename:
        return "Nenhum arquivo selecionado."

    is_doc = photo_type in _DOC_PHOTO_TYPES
    ext = os.path.splitext(secure_filename(file_storage.filename))[1].lower()
    allowed = _DOC_EXTS if is_doc else _IMAGE_EXTS
    if ext not in allowed:
        return "Use JPG, PNG, WEBP ou PDF." if is_doc else "Use JPG, PNG ou WEBP."

    subfolder = "talent_docs" if is_doc else "talent_photos"
    filename = f"talent_{talent.id}_{photo_type}_{_uuid.uuid4().hex[:8]}{ext}"
    old_path = getattr(talent, field_name)
    url_path = save_file(file_storage, subfolder, filename)
    if old_path:
        delete_file(old_path)
    setattr(talent, field_name, url_path)
    return None


def suggest_characters(q: str) -> list[dict]:
    """Sugere personagens já interpretados que combinam com `q` (feature 180, extraído de
    `character_suggestions` do Jinja — mesma query, mesmo formato de resposta, reusada pelos
    dois adaptadores).

    Args:
        q: texto buscado no nome do personagem; menos de 2 caracteres retorna lista vazia.

    Returns:
        Até 10 personagens `{"name": str, "count": int}`, ordenados por frequência decrescente.
    """
    from sqlalchemy import func as sqlfunc

    from app import db

    q = (q or "").strip()
    if not q or len(q) < 2:
        return []
    rows = (
        db.session.query(EventRole.character_name, sqlfunc.count(EventRole.id).label("cnt"))
        .filter(
            EventRole.character_name.ilike(f"%{q}%"),
            EventRole.assigned_at.isnot(None),
            EventRole.talent_id.isnot(None),
        )
        .group_by(EventRole.character_name)
        .order_by(sqlfunc.count(EventRole.id).desc())
        .limit(10)
        .all()
    )
    return [{"name": r.character_name, "count": r.cnt} for r in rows]


def remove_talent_photo(talent: Talent, *, photo_type: str) -> str | None:
    """Remove a foto/documento de um talento (ação nova, feature 155). No-op seguro se vazio.

    Returns:
        Mensagem de erro se `photo_type` for inválido, senão `None`.
    """
    from app.storage import delete_file

    field_name = _PHOTO_FIELDS.get(photo_type)
    if field_name is None:
        return "Tipo de foto/documento inválido."
    old_path = getattr(talent, field_name)
    if old_path:
        delete_file(old_path)
        setattr(talent, field_name, None)
    return None
