"""Núcleo de negócio do Portal do Artista (feature 176).

Funções puras (sem `flask.request`/`render_template`/`flash`/`session`), extraídas de
`app/talent_portal/routes.py` — reusadas tanto pela view Jinja legada quanto pelos endpoints de
API (`app/api/portal_*.py`), fonte única (Princípio I). Recebem sempre um `Talent` já resolvido
pela camada que chama (Jinja lê da `session`, API lê da mesma `session` por outro caminho).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_
from werkzeug.datastructures import FileStorage

from app import db
from app.cadastro.cadastro_ops import DOC_EXTS, DOC_MAX, PHOTO_EXTS, PHOTO_MAX, validate_upload
from app.models import CalendarEvent, EventRole, FigurinoSheet, Talent, TalentMedia
from app.storage import save_file

#: Máximo de fotos de atuação que um talento pode manter no portfólio.
MAX_PORTFOLIO_PHOTOS = 3

#: Campos de texto livre do perfil que o próprio talento pode editar pelo portal.
EDITABLE_TEXT_FIELDS = (
    "full_name",
    "artistic_name",
    "phone",
    "email_contact",
    "gender",
    "race",
    "languages",
    "skills",
    "pix_key",
    "pix_key_type",
    "pix_key_secondary",
    "rg",
    "passport_visa_text",
    "car_brand",
    "car_model",
    "car_year",
    "car_plate",
    "clothing_size_top",
    "clothing_size_bottom",
    "shoe_size",
)

#: Campos de data do perfil editáveis pelo talento (ISO `YYYY-MM-DD`).
EDITABLE_DATE_FIELDS = ("birth_date", "cnh_expiration")


class PortalUploadError(Exception):
    """Erro de validação de upload (extensão/tamanho) — nunca vazamento de exceção do storage."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class PortalProfileError(Exception):
    """Erro de validação de um campo do perfil (valor fora do formato esperado)."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field = field


def now_sp() -> datetime:
    """Agora em horário de Brasília, naïve — mesma convenção dos horários de evento no banco."""
    return datetime.now(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None)


def find_talent_by_login(value: str) -> Talent | None:
    """Acha um talento por CPF (dígitos) ou e-mail (feature 092).

    Talentos estrangeiros não têm CPF e acessam o portal pelo e-mail. Se o valor tiver ``@``,
    busca por ``email_contact`` (case-insensitive); caso contrário, trata como CPF (dígitos).
    """
    value = (value or "").strip()
    if not value:
        return None
    if "@" in value:
        return Talent.query.filter(func.lower(Talent.email_contact) == value.lower()).first()
    digits = "".join(c for c in value if c.isdigit())
    if not digits:
        return None
    return Talent.query.filter_by(cpf=digits).first()


def nao_recusada():
    """Cláusula: escalação cujo convite NÃO foi recusado (aceito, pendente ou sem convite).

    É a definição de "esse trabalho é seu" que vale no sistema inteiro (feature 230): a planilha
    de pagamentos paga por **cargo atribuído** — `_pagamentos_query` não olha `invite_status` —, e
    a tela de avaliação já aceitava qualquer escalação não recusada. O portal era o único lugar
    que exigia `accepted`, e por isso escondia do artista evento que ele ia fazer (ou já tinha
    feito e recebido).

    `invite_status`: `None` = convite nunca enviado · `pending` = enviado, sem resposta ·
    `accepted` · `rejected`. Só o último tira o cargo da vida do talento — quando alguém recusa, o
    casting troca a pessoa, e é por isso que não existe cargo recusado sendo pago.
    """
    return or_(EventRole.invite_status.is_(None), EventRole.invite_status != "rejected")


def events_with_visible_figurino(talent: Talent, roles: list[EventRole]) -> set[int]:
    """Dos eventos dessas escalações, quais têm ficha de figurino **para este talento** ver.

    Existe para a agenda poder esconder o link "Ver ficha de figurino" quando não há nada do outro
    lado — mandar o artista para uma tela que diz "ainda não há ficha" é o que fazia parecer que o
    figurino não tinha subido.

    Custa **duas** consultas para a agenda inteira (uma dos cargos, uma das fichas por nome
    normalizado), e não uma por evento: o histórico de um talento antigo tem centenas de linhas.

    Args:
        talent: Talento autenticado.
        roles: Escalações já carregadas (convites, futuros e histórico).

    Returns:
        Conjunto de `event_id` com ficha visível para ele — como coordenador (elenco inteiro) ou
        como intérprete (só os personagens dele).
    """
    from app.figurino.drive_service import normalize_name

    event_ids = {r.event_id for r in roles}
    if not event_ids:
        return set()

    todos = EventRole.query.filter(EventRole.event_id.in_(event_ids)).all()
    coordena_em = {
        r.event_id
        for r in todos
        if r.talent_id == talent.id
        and r.role_type == "extra"
        and (r.character_name or "").strip().casefold() == COORDENADOR_ROLE_NAME.casefold()
    }
    relevantes = [
        r for r in todos if r.event_id in coordena_em or r.talent_id == talent.id
    ]

    com_ficha = {r.event_id for r in relevantes if r.figurino_sheet_id}

    por_nome = {
        r.event_id: normalize_name(r.character_name)
        for r in relevantes
        if not r.figurino_sheet_id and r.character_name
    }
    nomes = set(por_nome.values())
    if nomes:
        existentes = {
            n
            for (n,) in db.session.query(FigurinoSheet.character_name_norm)
            .filter(FigurinoSheet.character_name_norm.in_(nomes))
            .all()
        }
        com_ficha |= {eid for eid, norm in por_nome.items() if norm in existentes}

    return com_ficha


def _role_summary(role: EventRole, has_figurino: bool = False) -> dict:
    """Serializa uma escalação do próprio talento — inclui sempre o cachê dele.

    O cachê acompanha *todas* as listagens (convite pendente, evento futuro e histórico), não só
    o histórico: o artista precisa saber quanto vai receber **antes** de aceitar o convite, que é
    justamente a decisão que a tela de convites pede. Enquanto isso só era anexado ao histórico,
    o valor simplesmente não existia no JSON e a tela o omitia em silêncio.

    Não é vazamento: `_role_summary` só é chamado a partir de consultas já filtradas por
    `talent_id` da sessão, então é sempre o cachê do próprio dono da sessão.
    """
    event = role.event
    cache_value = float(role.cache_value or 0)
    travel_cache = float(role.travel_cache or 0)
    return {
        "role_id": role.id,
        "event_id": event.id,
        "title": event.title,
        "start_at": event.start_at.isoformat() if event.start_at else None,
        "end_at": event.end_at.isoformat() if event.end_at else None,
        "location": event.location,
        "character_name": role.character_name,
        "has_unacknowledged_change": bool(role.event_changed_at),
        "change_description": role.change_description,
        "cache_value": cache_value,
        "travel_cache": travel_cache,
        "cache_total": cache_value + travel_cache,
        # `None` quando o cachê ainda não foi definido pela produção — a tela precisa distinguir
        # "combinado R$ 0,00" de "ainda não informado" para não anunciar um valor que não existe.
        "cache_defined": role.cache_value is not None,
        "payment_status": role.payment_status,
        # A agenda só mostra o link do figurino quando há ficha para ESTA pessoa ver.
        "has_figurino": has_figurino,
        # Desde a 230 a lista inclui escalação não aceita, então a tela precisa poder dizer que
        # ainda falta responder o convite — senão o mesmo evento aparece em "Próximos" e em
        # "Convites" sem explicação. `None` = convite nunca enviado (nada a responder).
        "invite_status": role.invite_status,
    }


def get_agenda(talent: Talent) -> dict:
    """Monta a Agenda do talento: convites pendentes, eventos futuros e histórico com cachê.

    Nota: `home()`/`historico()` (Jinja legado) mantêm suas próprias consultas em vez de chamar
    esta função — elas misturam a mesma listagem com o fluxo de avaliação de eventos (fora do
    escopo desta fatia, feature 176), e essa função devolve dicts serializados (para a API), não
    os objetos ORM que o template Jinja precisa. Duplicação reconhecida e aceita deliberadamente
    aqui: refatorar `home()` tocaria a lógica de avaliação sem necessidade, mais arriscado que o
    ganho de reuso neste caso pontual.

    Args:
        talent: Talento autenticado.

    Returns:
        Dict com `pending_invites`, `upcoming` e `history` (histórico inclui `cache_total` e
        `payment_status` por item).
    """
    now = now_sp()
    # Evento cancelado (feature 224) some do portal: o talento não pode receber convite para,
    # nem se preparar para, um evento que não vai acontecer.
    nao_cancelado = CalendarEvent.cancelled_at.is_(None)

    pending_invites = (
        EventRole.query.filter_by(talent_id=talent.id, invite_status="pending")
        .join(CalendarEvent)
        .filter(nao_cancelado)
        .order_by(CalendarEvent.start_at.asc())
        .all()
    )

    # `nao_recusada()` e não `invite_status="accepted"` (feature 230): exigir aceite escondia do
    # artista o evento que ele ia fazer. Cargo com convite nunca enviado (`NULL`) não entrava nem
    # em `pending_invites` (que pede `pending`) nem aqui — ficava invisível no portal inteiro,
    # embora a planilha de pagamentos o pague. Eram 26 cargos futuros e 97 passados assim.
    upcoming = (
        EventRole.query.filter(EventRole.talent_id == talent.id, nao_recusada())
        .join(CalendarEvent)
        .filter(nao_cancelado, CalendarEvent.start_at >= now)
        .order_by(CalendarEvent.start_at.asc())
        .all()
    )

    past = (
        EventRole.query.filter(EventRole.talent_id == talent.id, nao_recusada())
        .join(CalendarEvent)
        .filter(nao_cancelado, CalendarEvent.start_at < now)
        .order_by(CalendarEvent.start_at.desc())
        .all()
    )

    # Uma varredura só para as três listas — ver `events_with_visible_figurino`.
    com_ficha = events_with_visible_figurino(talent, pending_invites + upcoming + past)

    # `cache_total`/`payment_status` já vêm de `_role_summary` — antes eram anexados só aqui, que
    # era exatamente a razão de o cachê sumir nas outras duas listas.
    def resumo(role: EventRole) -> dict:
        return _role_summary(role, has_figurino=role.event_id in com_ficha)

    return {
        "pending_invites": [resumo(r) for r in pending_invites],
        "upcoming": [resumo(r) for r in upcoming],
        "history": [resumo(r) for r in past],
    }


def _owned_role(talent: Talent, role_id: int) -> EventRole | None:
    return EventRole.query.filter_by(id=role_id, talent_id=talent.id).first()


def accept_invite(talent: Talent, role_id: int) -> EventRole | None:
    """Aceita um convite pendente — idempotente (repetir não muda nada nem gera erro)."""
    role = _owned_role(talent, role_id)
    if role is None:
        return None
    role.invite_status = "accepted"
    db.session.commit()
    return role


def reject_invite(talent: Talent, role_id: int) -> EventRole | None:
    """Recusa um convite — idempotente. Mantém `talent_id` (o casting precisa saber quem recusou)."""
    role = _owned_role(talent, role_id)
    if role is None:
        return None
    role.invite_status = "rejected"
    db.session.commit()
    return role


def ack_event_change(talent: Talent, role_id: int) -> EventRole | None:
    """Marca como reconhecida a alteração de um evento já aceito pelo talento."""
    role = _owned_role(talent, role_id)
    if role is None:
        return None
    role.event_changed_at = None
    role.change_description = None
    db.session.commit()
    return role


def portal_photo_url(path: str | None) -> str | None:
    """Converte o caminho guardado de uma imagem na URL que o PORTAL consegue abrir.

    `/uploads/<...>` é servido por uma rota `@login_required` do Flask-Login — ou seja, sessão de
    **staff**. Quem está no portal tem `session["talent_id"]` e nenhum usuário logado, então o
    navegador recebe um 302 para a tela de login do staff no lugar da imagem e o `<img>` cai no
    ícone de quebrado. `/portal/photo/<...>` é a rota equivalente que valida a sessão de talento
    (`app/talent_portal/routes.py`), restrita às subpastas de imagem por `PORTAL_PHOTO_SUBFOLDERS`.

    URL absoluta (foto herdada do Drive/Sheets) passa intacta: não é nossa para reescrever.

    Args:
        path: Valor guardado no banco (`/uploads/talent_photos/x.jpg`, `https://…` ou vazio).

    Returns:
        URL que o portal serve, ou `None` quando não há imagem.
    """
    if not path:
        return None
    prefixo = "/uploads/"
    if path.startswith(prefixo):
        return "/portal/photo/" + path[len(prefixo):]
    return path


#: Nome do cargo sentinela do coordenador — o mesmo literal que `app/calendar/event_ops.py` grava
#: ao criar o evento e que a tela de edição procura (`role_type="extra"`).
COORDENADOR_ROLE_NAME = "Coordenador"


def is_event_coordinator(talent: Talent, event: CalendarEvent) -> bool:
    """`True` se o talento está escalado como coordenador do evento (cargo, não personagem)."""
    return any(
        r.talent_id == talent.id
        and r.role_type == "extra"
        and (r.character_name or "").strip().casefold() == COORDENADOR_ROLE_NAME.casefold()
        for r in event.roles
    )


def _sheet_of_role(role: EventRole) -> FigurinoSheet | None:
    """Ficha vinculada ao cargo, ou a que casa pelo nome normalizado do personagem."""
    from app.figurino.drive_service import normalize_name

    if role.figurino_sheet:
        return role.figurino_sheet
    return FigurinoSheet.query.filter_by(
        character_name_norm=normalize_name(role.character_name)
    ).first()


def get_figurino(
    talent: Talent, event_id: int
) -> list[tuple[FigurinoSheet, str | None, str | None]] | None:
    """Fichas de figurino que o talento pode ver num evento.

    Regra: cada um vê as fichas dos **seus** personagens — exceto o **coordenador**, que vê as do
    elenco inteiro. Conferir o figurino de todo mundo em campo é o trabalho dele, e como o cargo
    de coordenador não tem personagem, a consulta por personagem próprio devolvia lista vazia:
    a tela dizia "ainda não há ficha de figurino para este evento" para um evento com todas as
    fichas prontas (relatado em 08/08/2026, evento (R&I) MOANA + MAUI).

    Args:
        talent: Talento autenticado.
        event_id: Evento consultado.

    Returns:
        Lista de `(sheet, photo_url, talent_name)` — `talent_name` é quem interpreta o personagem,
        e só interessa na visão do coordenador. Lista vazia = escalado, mas sem ficha para mostrar.
        `None` = o talento não está nesse evento (nem pendente, nem aceito).
    """
    # `nao_recusada()`, a mesma regra da agenda e do histórico (feature 230). Enquanto aqui a trava
    # era `in_(["accepted","pending"])`, o cargo com convite NUNCA ENVIADO (`NULL`) caía fora: a
    # 230 passou a mostrar o evento na agenda com o link "Ver ficha de figurino", e o link levava a
    # um 403 "você não está escalado neste evento". Foi o que a coordenadora do evento 1192
    # encontrou em 10/08/2026 — ela é a coordenadora, o evento é dela, e a tela dizia que não.
    role = EventRole.query.filter(
        EventRole.event_id == event_id,
        EventRole.talent_id == talent.id,
        nao_recusada(),
    ).first()
    if role is None:
        return None

    event = role.event
    coordena = is_event_coordinator(talent, event)
    # O coordenador varre o elenco inteiro; os demais, só os próprios cargos. Cargo `extra`
    # (transporte, maquiador, o próprio coordenador) não tem personagem e nunca traz ficha.
    cargos = [r for r in event.roles if coordena or r.talent_id == talent.id]

    seen_ids: set[int] = set()
    sheet_items: list[tuple[FigurinoSheet, str | None, str | None]] = []

    for r in cargos:
        sheet = _sheet_of_role(r)
        if not sheet or sheet.id in seen_ids:
            continue
        seen_ids.add(sheet.id)
        quem = r.talent.artistic_name or r.talent.full_name if r.talent else None
        sheet_items.append((sheet, portal_photo_url(sheet.photo_filename), quem))

    return sheet_items


def update_photo(talent: Talent, kind: str, file: FileStorage) -> Talent:
    """Substitui a foto de rosto ou corpo inteiro do talento.

    Args:
        talent: Talento autenticado.
        kind: `"face"` ou `"full"`.
        file: Arquivo enviado.

    Raises:
        PortalUploadError: Formato não aceito ou acima do limite.
    """
    validated, error = validate_upload(file, PHOTO_EXTS, PHOTO_MAX, required=True, label="Foto")
    if error:
        raise PortalUploadError(error)
    url = save_file(validated, "talent_photos")
    if kind == "full":
        talent.photo_full_path = url
    else:
        talent.photo_face_path = url
    db.session.commit()
    return talent


def update_document(talent: Talent, file: FileStorage) -> Talent:
    """Substitui o arquivo da CNH do talento.

    Raises:
        PortalUploadError: Formato não aceito ou acima do limite.
    """
    validated, error = validate_upload(file, DOC_EXTS, DOC_MAX, required=True, label="Arquivo da CNH")
    if error:
        raise PortalUploadError(error)
    talent.cnh_file_path = save_file(validated, "talent_docs")
    db.session.commit()
    return talent


# ── Perfil e portfólio (feature 191) ───────────────────────────────────────────


def _media_to_dict(item: TalentMedia) -> dict[str, Any]:
    """Serializa um item de portfólio (foto de atuação ou link)."""
    return {
        "id": item.id,
        "media_type": item.media_type,
        "label": item.label,
        "file_url": portal_photo_url(item.file_path),
        "url": item.url,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def get_profile(talent: Talent) -> dict[str, Any]:
    """Perfil completo do talento para a tela de edição do portal.

    Returns:
        Dict com dados pessoais, medidas corporais, dados de pagamento, arquivos e o portfólio
        (`media`), já serializado para JSON.
    """
    return {
        "id": talent.id,
        "cpf": talent.cpf,
        "full_name": talent.full_name,
        "artistic_name": talent.artistic_name,
        "phone": talent.phone,
        "email_contact": talent.email_contact,
        "gender": talent.gender,
        "race": talent.race,
        "languages": talent.languages,
        "skills": talent.skills,
        "birth_date": talent.birth_date.isoformat() if talent.birth_date else None,
        # Medidas corporais — o bloco mais usado do perfil (figurino depende dele).
        "height_cm": talent.height_cm,
        "clothing_size_top": talent.clothing_size_top,
        "clothing_size_bottom": talent.clothing_size_bottom,
        "shoe_size": talent.shoe_size,
        # Pagamento
        "pix_key": talent.pix_key,
        "pix_key_type": talent.pix_key_type,
        "pix_key_secondary": talent.pix_key_secondary,
        # Documentos e veículo
        "rg": talent.rg,
        "has_visa": bool(talent.has_visa),
        "passport_visa_text": talent.passport_visa_text,
        "cnh_expiration": talent.cnh_expiration.isoformat() if talent.cnh_expiration else None,
        # Sem `portal_photo_url` de propósito: `talent_docs` NÃO está em
        # `PORTAL_PHOTO_SUBFOLDERS` — documento de talento só sai por `/uploads` com papel
        # CASTING. Hoje nenhuma tela do portal renderiza este campo; se um dia render, o certo é
        # uma rota própria que confira a posse do documento, não afrouxar a lista de fotos.
        "cnh_file_url": talent.cnh_file_path,
        "car_brand": talent.car_brand,
        "car_model": talent.car_model,
        "car_year": talent.car_year,
        "car_plate": talent.car_plate,
        # Fotos oficiais
        "photo_face_url": portal_photo_url(talent.photo_face_path),
        "photo_full_url": portal_photo_url(talent.photo_full_path),
        # Portfólio
        "media": [_media_to_dict(m) for m in talent.media_items],
        "max_photos": MAX_PORTFOLIO_PHOTOS,
    }


def _parse_optional_date(raw: Any, field: str):
    """Converte uma data ISO opcional vinda do cliente, ou `None`.

    Raises:
        PortalProfileError: Valor presente mas fora do formato `YYYY-MM-DD`.
    """
    value = (raw or "").strip() if isinstance(raw, str) else raw
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError) as exc:
        raise PortalProfileError("Data inválida. Use o formato AAAA-MM-DD.", field=field) from exc


def _parse_optional_height(raw: Any):
    """Converte a altura em centímetros, ou `None`.

    Raises:
        PortalProfileError: Valor não numérico ou fora de uma faixa humana plausível.
    """
    value = (raw or "").strip() if isinstance(raw, str) else raw
    if value in (None, ""):
        return None
    try:
        height = int(value)
    except (TypeError, ValueError) as exc:
        raise PortalProfileError("Altura deve ser um número em centímetros.", field="height_cm") from exc
    if not (50 <= height <= 260):
        raise PortalProfileError("Altura deve estar entre 50 e 260 cm.", field="height_cm")
    return height


def update_profile(talent: Talent, data: dict[str, Any]) -> Talent:
    """Aplica ao talento apenas os campos de perfil que ele mesmo pode editar.

    Só as chaves presentes em `data` são tocadas (semântica de PATCH) — assim a tela pode enviar
    um bloco isolado (ex.: só as medidas) sem apagar o resto. `full_name` nunca é apagado: valor
    vazio mantém o nome atual, como já fazia a tela Jinja.

    Args:
        talent: Talento autenticado.
        data: Corpo JSON enviado pelo cliente.

    Returns:
        O talento atualizado.

    Raises:
        PortalProfileError: Altura ou data em formato inválido.
    """
    for field in EDITABLE_TEXT_FIELDS:
        if field not in data:
            continue
        value = (data.get(field) or "").strip() or None
        if field == "full_name" and not value:
            continue  # nome é obrigatório — vazio mantém o atual
        setattr(talent, field, value)

    for field in EDITABLE_DATE_FIELDS:
        if field in data:
            setattr(talent, field, _parse_optional_date(data.get(field), field))

    if "height_cm" in data:
        talent.height_cm = _parse_optional_height(data.get("height_cm"))

    if "has_visa" in data:
        talent.has_visa = bool(data.get("has_visa"))

    db.session.commit()
    return talent


def add_portfolio_photo(talent: Talent, file: FileStorage, label: str | None = None) -> TalentMedia:
    """Adiciona uma foto de atuação ao portfólio do talento.

    Args:
        talent: Talento autenticado.
        file: Imagem enviada.
        label: Legenda opcional.

    Returns:
        O item de portfólio criado.

    Raises:
        PortalUploadError: Limite de fotos atingido, formato não aceito ou acima do tamanho.
    """
    photo_count = TalentMedia.query.filter_by(talent_id=talent.id, media_type="photo").count()
    if photo_count >= MAX_PORTFOLIO_PHOTOS:
        raise PortalUploadError(f"Limite de {MAX_PORTFOLIO_PHOTOS} fotos de atuação atingido.")

    validated, error = validate_upload(file, PHOTO_EXTS, PHOTO_MAX, required=True, label="Foto")
    if error:
        raise PortalUploadError(error)

    ext = os.path.splitext(validated.filename or "")[1].lower()
    filename = f"media_{talent.id}_{uuid.uuid4().hex[:8]}{ext}"
    item = TalentMedia(
        talent_id=talent.id,
        media_type="photo",
        label=(label or "").strip() or None,
        file_path=save_file(validated, "talent_photos", filename),
    )
    db.session.add(item)
    db.session.commit()
    return item


def add_portfolio_link(talent: Talent, url: str, label: str | None = None) -> TalentMedia:
    """Adiciona um link de portfólio (Vimeo, YouTube…) ao talento.

    Args:
        talent: Talento autenticado.
        url: Endereço do vídeo/portfólio — precisa começar com `http://` ou `https://`.
        label: Rótulo opcional; sem ele, usa o começo da própria URL.

    Returns:
        O item de portfólio criado.

    Raises:
        PortalProfileError: URL vazia ou sem esquema http(s).
    """
    url_value = (url or "").strip()
    if not url_value:
        raise PortalProfileError("Informe o endereço do link.", field="url")
    if not url_value.lower().startswith(("http://", "https://")):
        raise PortalProfileError("O link deve começar com http:// ou https://", field="url")

    item = TalentMedia(
        talent_id=talent.id,
        media_type="link",
        label=(label or "").strip() or url_value[:60],
        url=url_value,
    )
    db.session.add(item)
    db.session.commit()
    return item


def delete_portfolio_item(talent: Talent, media_id: int) -> bool:
    """Remove um item do portfólio do talento (e o arquivo físico, se houver).

    Filtra por `talent_id` junto com o `id` — um talento nunca apaga a mídia de outro.

    Returns:
        True se removeu; False se o item não existe ou não é do talento.
    """
    item = TalentMedia.query.filter_by(id=media_id, talent_id=talent.id).first()
    if item is None:
        return False

    if item.file_path:
        _delete_local_upload(item.file_path)

    db.session.delete(item)
    db.session.commit()
    return True


def _delete_local_upload(file_path: str) -> None:
    """Apaga o arquivo local de um upload, ignorando silenciosamente o que não existe.

    Só age sobre caminhos locais (`/uploads/...`); em produção com S3/R2 o `file_path` é uma URL
    absoluta e nada é removido aqui — a limpeza do bucket é responsabilidade de `app.storage`.
    """
    import logging

    from flask import current_app

    if file_path.lower().startswith(("http://", "https://")):
        return

    relative = file_path.removeprefix("/uploads/").removeprefix("uploads/")
    full_path = os.path.join(current_app.config["UPLOAD_FOLDER"], relative)
    try:
        if os.path.exists(full_path):
            os.remove(full_path)
    except OSError as exc:
        logging.getLogger(__name__).warning("Falha ao remover upload %s: %s", full_path, exc)


# ── Histórico de apresentações (feature 191) ───────────────────────────────────


def get_historico(talent: Talent) -> dict[str, Any]:
    """Histórico completo de eventos passados do talento, com somatórios de cachê.

    Diferente de `get_agenda`, que devolve só os últimos eventos junto com convites e futuros,
    aqui vem a lista completa mais os totais pago/pendente que a tela exibe no topo.

    Args:
        talent: Talento autenticado.

    Returns:
        Dict com `items` (mais recente primeiro) e `totals` (`paid`, `pending`, `overall`,
        `count`). Valores monetários em `float`, formatados no cliente por `@manto/money`.
    """
    # Mesma regra da agenda (feature 230): escalação não recusada, e não só aceita — é o que a
    # planilha de pagamentos usa, então os totais daqui passam a bater com o que o financeiro paga.
    #
    # `cancelled_at` entra junto porque esta consulta não tinha o filtro que `get_agenda` já tinha
    # (feature 224): com a regra antiga o furo era pequeno (só evento cancelado com convite já
    # aceito), e ampliar para "não recusada" sem isso passaria a somar no total de cachê evento que
    # não aconteceu — e que a planilha de pagamentos também não paga.
    past = (
        EventRole.query.filter(EventRole.talent_id == talent.id, nao_recusada())
        .join(CalendarEvent)
        .filter(CalendarEvent.cancelled_at.is_(None), CalendarEvent.start_at < now_sp())
        .order_by(CalendarEvent.start_at.desc())
        .all()
    )

    com_ficha = events_with_visible_figurino(talent, past)

    items = []
    total_paid = 0.0
    total_pending = 0.0
    for role in past:
        # Campos de cachê vêm de `_role_summary` (fonte única); aqui só somamos os totais.
        item = _role_summary(role, has_figurino=role.event_id in com_ficha)
        if item["payment_status"] == "pago":
            total_paid += item["cache_total"]
        else:
            total_pending += item["cache_total"]
        items.append(item)

    return {
        "items": items,
        "totals": {
            "paid": total_paid,
            "pending": total_pending,
            "overall": total_paid + total_pending,
            "count": len(items),
        },
    }
