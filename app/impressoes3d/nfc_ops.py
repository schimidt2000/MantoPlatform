"""Núcleo de negócio das Tags NFC das peças 3D (feature 255).

Funções puras (sem `request`/`render_template`), fonte única reusada pelos endpoints JSON de
`app/api/nfc_read.py` e `app/api/nfc_write.py`, e pelo gancho de geração automática em
`app/impressoes3d/impressoes3d_ops.py` (presente 3D de item habilitado → tags por unidade).

O contrato central da feature: a URL gravada na tag física (`/nfc/<code>`) é **imutável e
eterna** — todo o conteúdo é decidido pelo servidor a cada acesso. Por isso `code` nunca muda,
tag nunca é apagada (só `is_active=False`) e a resolução pública devolve o MESMO shape para
código inexistente e tag desativada (não vazar existência é requisito — SC-006 da spec).
"""

from __future__ import annotations

import logging
import os
import secrets
import uuid
from datetime import datetime
from typing import Any

from flask import current_app
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import db
from app.constants import (
    NFC_DELIVERY_VIDEO_EXTENSIONS,
    NFC_DELIVERY_VIDEO_MAX_BYTES,
    NFC_MAX_CODE_ATTEMPTS,
    NFC_SUFFIX_ALPHABET,
    NFC_SUFFIX_LENGTH,
)
from app.models import Acervo3DItem, CalendarEvent, Client, Event3DGift, NfcTag, NfcTagDelivery
from app.storage import extension_of
from app.utils import audit

logger = logging.getLogger(__name__)

MAX_NFC_BATCH_QUANTITY = 999
NFC_PREFIX_MAX_LENGTH = 10

#: Únicas espécies de entrega aceitas hoje (feature 261). A tabela é extensível; a allowlist de
#: `kind` é intencionalmente rígida — a "extensibilidade" é o schema, não a validação.
NFC_DELIVERY_KINDS = frozenset({"video"})


class NfcValidationError(Exception):
    """Erro de validação de negócio das tags NFC, com o campo culpado.

    Mesmo padrão de `Impressao3DValidationError`: o endpoint traduz em
    `json_error(msg, 400, fields={campo: msg})` para o React destacar o campo exato.
    """

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


# ── Primitivas de criação ────────────────────────────────────────────────────


def normalize_nfc_prefix(raw: Any) -> str | None:
    """Normaliza o prefixo NFC de um item do acervo (trim, MAIÚSCULAS, sem `-`).

    Vazio vira `None` (item não habilitado). O `-` é reservado como separador do código.

    Raises:
        NfcValidationError: Prefixo com mais de 10 caracteres ou não alfanumérico.
    """
    value = (str(raw or "")).strip().upper().replace("-", "")
    if not value:
        return None
    if len(value) > NFC_PREFIX_MAX_LENGTH:
        raise NfcValidationError(
            "nfc_prefix", f"Prefixo NFC deve ter no máximo {NFC_PREFIX_MAX_LENGTH} caracteres."
        )
    if not value.isalnum():
        raise NfcValidationError("nfc_prefix", "Prefixo NFC deve conter só letras e números.")
    return value


def _new_code(prefix: str) -> str:
    """Sorteia um código inédito `<prefixo>-<sufixo>` (sufixo via `secrets`, sem ambiguidade).

    O sufixo é, na prática, um token: a página pública terá conteúdo pessoal no futuro, então
    código adivinhável está proibido pela spec (nada de sequencial na URL).
    """
    for _ in range(NFC_MAX_CODE_ATTEMPTS):
        suffix = "".join(secrets.choice(NFC_SUFFIX_ALPHABET) for _ in range(NFC_SUFFIX_LENGTH))
        code = f"{prefix}-{suffix}"
        if NfcTag.query.filter_by(code=code).first() is None:
            return code
    # 31^6 combinações por prefixo: chegar aqui indica problema real (ex.: prefixo esgotado).
    raise NfcValidationError("code", "Não foi possível gerar um código único — tente novamente.")


def _next_sequence(item_id: int) -> int:
    """Próximo número humano do item (nº 1, 2, 3… — o rótulo físico anotado na tagzinha)."""
    current = (
        db.session.query(func.max(NfcTag.sequence)).filter(NfcTag.item_id == item_id).scalar()
    )
    return int(current or 0) + 1


def create_tags(
    item: Acervo3DItem, quantity: int, *, event_id: int | None = None
) -> list[NfcTag]:
    """Cria `quantity` tags do item (SEM commit — o chamador fecha a transação).

    Cada tag é flushada individualmente para que código e `sequence` das seguintes enxerguem
    as anteriores dentro da mesma transação.

    Raises:
        NfcValidationError: Item sem `nfc_prefix` ou quantidade fora de 1–999.
    """
    if not item.nfc_prefix:
        raise NfcValidationError("item_id", "Esta peça do Acervo não está habilitada para NFC.")
    if quantity < 1 or quantity > MAX_NFC_BATCH_QUANTITY:
        raise NfcValidationError(
            "quantity", f"Quantidade deve ficar entre 1 e {MAX_NFC_BATCH_QUANTITY}."
        )
    tags: list[NfcTag] = []
    for _ in range(quantity):
        tag = NfcTag(
            code=_new_code(item.nfc_prefix),
            sequence=_next_sequence(item.id),
            item_id=item.id,
            event_id=event_id,
        )
        db.session.add(tag)
        db.session.flush()
        tags.append(tag)
    return tags


# ── Geração automática (gancho dos presentes 3D — US2) ───────────────────────


def sync_event_gift_tags(event: CalendarEvent, item: Acervo3DItem) -> list[NfcTag]:
    """Completa as tags de um par (evento, item) até a soma das quantidades dos presentes.

    Chamada por `add_event_gift`/`update_event_gift` ANTES do commit, na mesma transação.
    Conta por `(event_id, item_id)` — e não por linha de presente — para sobreviver a presentes
    deletados/recriados e a dois presentes do mesmo item no mesmo evento. NUNCA remove: reduzir
    quantidade ou apagar o presente não toca nas tags (a tag física já pode existir no mundo).

    Returns:
        As tags recém-criadas (vazio quando o item não é NFC ou nada falta).
    """
    if not item.nfc_prefix:
        return []
    target = (
        db.session.query(func.coalesce(func.sum(Event3DGift.quantity), 0))
        .filter(Event3DGift.event_id == event.id, Event3DGift.item_id == item.id)
        .scalar()
    )
    existing = NfcTag.query.filter_by(event_id=event.id, item_id=item.id).count()
    missing = int(target or 0) - existing
    if missing <= 0:
        return []
    created = create_tags(item, missing, event_id=event.id)
    numeros = ", ".join(f"nº {t.sequence}" for t in created)
    audit(
        "create", "NfcTag", created[0].id, item.name,
        f"{len(created)} tag(s) NFC gerada(s) automaticamente para o evento #{event.id} ({numeros})",
    )
    return created


# ── Resolução pública (US1) ──────────────────────────────────────────────────


def _serialize_public_delivery(code: str, delivery: NfcTagDelivery) -> dict[str, Any]:
    """Entrega no payload público — só o que a página precisa para exibir, nada de caminho de disco."""
    return {
        "kind": delivery.kind,
        "title": delivery.title,
        "media_url": f"/api/nfc/{code}/entregas/{delivery.id}/media",
    }


def resolve_code(raw_code: str) -> dict[str, Any]:
    """Resolve um código de tag para o payload público — SEMPRE o mesmo shape.

    Tag ativa → produto + gancho `campaign` (hoje sempre `None`; é o contrato que permitirá
    campanhas futuras sem regravar tags) + `deliveries` (feature 261: vídeo/foto/link anexados —
    hoje só vídeo). Código inexistente ou tag desativada → payload genérico idêntico, `deliveries`
    incluso e vazio, sem vazar se o código existe (SC-006).

    O contador de acesso é melhor-esforço: falha na métrica loga e NUNCA derruba a página.
    """
    code = (raw_code or "").strip().upper()
    tag = NfcTag.query.filter_by(code=code).first() if code else None
    if tag is None or not tag.is_active:
        return {"product": None, "campaign": None, "deliveries": []}

    deliveries = sorted(
        (d for d in tag.deliveries if d.is_active), key=lambda d: (d.sort_order, d.id)
    )
    payload: dict[str, Any] = {
        "product": {"name": tag.item.name, "photo_url": tag.item.photo_url},
        "campaign": None,
        "deliveries": [_serialize_public_delivery(tag.code, d) for d in deliveries],
    }
    try:
        tag.access_count = (tag.access_count or 0) + 1
        tag.last_accessed_at = datetime.utcnow()
        db.session.commit()
    except Exception:
        logger.warning("Falha ao registrar acesso da tag NFC %s", code, exc_info=True)
        db.session.rollback()
    return payload


# ── Gestão no ERP (US3) ──────────────────────────────────────────────────────


def list_tags() -> list[NfcTag]:
    """Todas as tags, ordenadas por item e nº sequencial (o rótulo físico da equipe).

    Carrega item e evento (com clientes) de uma vez — a lista do ERP mostra
    "nº X · código · produto · evento · cliente" sem N+1.
    """
    return (
        NfcTag.query.options(
            joinedload(NfcTag.item),
            joinedload(NfcTag.event).joinedload(CalendarEvent.event_clients),
            joinedload(NfcTag.client),
        )
        .join(Acervo3DItem, NfcTag.item_id == Acervo3DItem.id)
        .order_by(Acervo3DItem.name.asc(), NfcTag.sequence.asc())
        .all()
    )


def generate_batch(item_id: Any, quantity: Any) -> list[NfcTag]:
    """Gera um lote avulso de tags (estoque, sem evento) — commit incluso.

    Raises:
        NfcValidationError: Item inexistente/sem prefixo ou quantidade inválida.
    """
    item = Acervo3DItem.query.get(item_id) if item_id else None
    if item is None:
        raise NfcValidationError("item_id", "Selecione uma peça do Acervo 3D.")
    try:
        parsed = int(quantity)
    except (TypeError, ValueError):
        raise NfcValidationError("quantity", "Quantidade inválida.") from None
    created = create_tags(item, parsed)
    numeros = f"nº {created[0].sequence}–{created[-1].sequence}" if created else ""
    audit(
        "create", "NfcTag", created[0].id, item.name,
        f"Lote de {len(created)} tag(s) NFC gerado ({numeros})",
    )
    db.session.commit()
    return created


def update_tag(
    tag: NfcTag,
    *,
    event_id: Any = ...,
    client_id: Any = ...,
    is_active: bool | None = None,
    notes: str | None = None,
) -> NfcTag:
    """Edita os ÚNICOS campos mutáveis de uma tag: evento, cliente direta, situação e notas.

    `event_id` e `client_id` usam `...` (Ellipsis) como sentinela de "não alterar", porque
    `None` é um valor válido (desassociar). `client_id` é a cliente DIRETA — o caso da campanha
    de marketing sem show; independe do evento e ganha dele na exibição. `code` e `sequence`
    são imutáveis por contrato — não há parâmetro para eles de propósito. Apagar tag não
    existe em lugar nenhum.

    Raises:
        NfcValidationError: `event_id`/`client_id` informado não existe.
    """
    if event_id is not ...:
        if event_id is None:
            tag.event_id = None
        else:
            event = CalendarEvent.query.get(event_id)
            if event is None:
                raise NfcValidationError("event_id", "Evento não encontrado.")
            tag.event_id = event.id
    if client_id is not ...:
        if client_id is None:
            tag.client_id = None
        else:
            client = Client.query.get(client_id)
            if client is None:
                raise NfcValidationError("client_id", "Cliente não encontrada.")
            tag.client_id = client.id
    if is_active is not None:
        tag.is_active = is_active
    if notes is not None:
        tag.notes = notes.strip() or None

    audit(
        "edit", "NfcTag", tag.id, tag.code,
        f"Tag NFC nº {tag.sequence} editada"
        + (" (desativada)" if is_active is False else " (reativada)" if is_active else ""),
    )
    db.session.commit()
    return tag


# ── Serialização (fonte única dos payloads JSON do módulo) ───────────────────


def serialize_tag(tag: NfcTag) -> dict[str, Any]:
    """Tag em JSON para o ERP — item aninhado (miniatura) e evento resumido.

    O nome da cliente NÃO sai daqui: `client_of_event` mora na camada de API
    (`app/api/agenda_read.py`) e é o endpoint quem o acrescenta — ops não importa de `app.api`
    (a dependência só aponta para baixo).
    """
    item = tag.item
    event = tag.event
    return {
        "id": tag.id,
        "code": tag.code,
        "sequence": tag.sequence,
        "item": {
            "id": item.id,
            "name": item.name,
            "photo_url": item.photo_url,
            "nfc_prefix": item.nfc_prefix,
        },
        "event": (
            {
                "id": event.id,
                "title": event.title,
                "start_at": event.start_at.isoformat() if event.start_at else None,
            }
            if event
            else None
        ),
        # Cliente DIRETA (campanha/brinde sem show). A contratante do evento não sai daqui —
        # é o endpoint quem resolve a precedência (ops não importa de `app.api`).
        "client": (
            {"id": tag.client.id, "name": tag.client.name} if tag.client else None
        ),
        "is_active": bool(tag.is_active),
        "notes": tag.notes,
        "access_count": int(tag.access_count or 0),
        "last_accessed_at": tag.last_accessed_at.isoformat() if tag.last_accessed_at else None,
        "created_at": tag.created_at.isoformat() if tag.created_at else None,
        # Entrega de vídeo ativa (feature 261) para a tela `/3d/tags` mostrar "tem vídeo" e
        # oferecer Substituir/Remover. `None` quando não há entrega — a tela mostra "Enviar".
        "video_delivery": _serialize_admin_video_delivery(tag),
    }


def _active_video_delivery(tag: NfcTag) -> NfcTagDelivery | None:
    """A entrega de vídeo ativa da tag, se houver (por ora, no máximo uma)."""
    return next(
        (d for d in tag.deliveries if d.kind == "video" and d.is_active), None
    )


def _serialize_admin_video_delivery(tag: NfcTag) -> dict[str, Any] | None:
    """Entrega de vídeo para o ERP: id, título, nome do arquivo e data — nunca o caminho no disco."""
    delivery = _active_video_delivery(tag)
    if delivery is None:
        return None
    return {
        "id": delivery.id,
        "kind": delivery.kind,
        "title": delivery.title,
        "file_name": delivery.file_path,
        "created_at": delivery.created_at.isoformat() if delivery.created_at else None,
    }


# ── Entregas (US — feature 261) ───────────────────────────────────────────────


def _delivery_folder() -> str:
    return current_app.config["NFC_MEDIA_FOLDER"]


def delivery_mime_type(delivery: NfcTagDelivery) -> str:
    """MIME do arquivo da entrega, deduzido da extensão (mesma fórmula de `virtuais_ops`)."""
    extensao = extension_of(delivery.file_path)
    return f"video/{extensao.lstrip('.').replace('mov', 'quicktime')}" if extensao else "video/mp4"


def delivery_media_path(delivery: NfcTagDelivery) -> str | None:
    """Caminho absoluto do arquivo da entrega no disco, ou `None` se não há arquivo.

    Uso exclusivo do endpoint público que serve o arquivo (`GET .../entregas/<id>/media`) —
    este valor nunca sai em payload nenhum (mesmo contrato de `virtuais_ops.caminho_video`).
    """
    if not delivery.file_path:
        return None
    return os.path.join(_delivery_folder(), delivery.file_path)


def _remove_delivery_file(delivery: NfcTagDelivery) -> None:
    """Apaga o arquivo da entrega do disco, sem derrubar o fluxo se ele já não existir."""
    caminho = delivery_media_path(delivery)
    if not caminho:
        return
    try:
        if os.path.exists(caminho):
            os.remove(caminho)
    except OSError as exc:  # noqa: BLE001 — arquivo órfão não pode travar a exclusão da linha
        logger.warning("nfc_ops: falha ao remover arquivo de entrega %s: %s", caminho, exc)


def add_delivery(
    tag: NfcTag, file_obj: Any, *, kind: str = "video", title: str | None = None
) -> NfcTagDelivery:
    """Salva o arquivo e cria a entrega — se já existe entrega ativa do mesmo `kind`, substitui.

    "Substitui" = apaga arquivo e linha antigos antes de criar a nova: por ora é 1 vídeo ativo
    por tag (a TABELA é extensível; este comportamento é o de hoje, não uma limitação do schema).
    O arquivo só é considerado salvo depois de escrito por inteiro e não-vazio no disco — criar a
    linha antes disso deixaria a página pública apontar para um vídeo que não existe.

    Raises:
        NfcValidationError: `kind` não suportado, arquivo ausente, extensão fora da allowlist ou
            acima do limite de tamanho.
    """
    if kind not in NFC_DELIVERY_KINDS:
        raise NfcValidationError("kind", "Tipo de entrega não suportado.")

    nome_original = getattr(file_obj, "filename", "") or ""
    if not nome_original:
        raise NfcValidationError("file", "Escolha o arquivo do vídeo.")

    extensao = extension_of(nome_original)
    if extensao not in NFC_DELIVERY_VIDEO_EXTENSIONS:
        raise NfcValidationError(
            "file",
            f"Formato não suportado (use {', '.join(sorted(NFC_DELIVERY_VIDEO_EXTENSIONS))}).",
        )

    pasta = _delivery_folder()
    os.makedirs(pasta, exist_ok=True)
    nome_final = f"{uuid.uuid4().hex}{extensao}"
    caminho = os.path.join(pasta, nome_final)

    tamanho = 0
    try:
        file_obj.seek(0)
        with open(caminho, "wb") as destino:
            while True:
                pedaco = file_obj.read(1024 * 1024)
                if not pedaco:
                    break
                tamanho += len(pedaco)
                if tamanho > NFC_DELIVERY_VIDEO_MAX_BYTES:
                    raise NfcValidationError(
                        "file",
                        f"Vídeo acima do limite de "
                        f"{NFC_DELIVERY_VIDEO_MAX_BYTES // (1024 * 1024)} MB.",
                    )
                destino.write(pedaco)
    except NfcValidationError:
        _apagar_arquivo(caminho)
        raise
    except OSError as exc:
        _apagar_arquivo(caminho)
        raise NfcValidationError("file", "Não foi possível guardar o vídeo agora.") from exc

    if not os.path.exists(caminho) or os.path.getsize(caminho) == 0:
        _apagar_arquivo(caminho)
        raise NfcValidationError("file", "O vídeo chegou vazio. Tente enviar de novo.")

    anterior = next((d for d in tag.deliveries if d.kind == kind and d.is_active), None)
    if anterior is not None:
        _remove_delivery_file(anterior)
        db.session.delete(anterior)

    delivery = NfcTagDelivery(
        tag_id=tag.id, kind=kind, title=(title or "").strip() or None, file_path=nome_final,
    )
    db.session.add(delivery)
    audit(
        "edit", "NfcTag", tag.id, tag.code,
        f"Entrega de {kind} {'substituída' if anterior else 'adicionada'} na tag NFC nº {tag.sequence}",
    )
    db.session.commit()
    return delivery


def _apagar_arquivo(caminho: str) -> None:
    """Remove um arquivo recém-gravado que não deve ficar no disco (upload falho/vazio)."""
    try:
        if os.path.exists(caminho):
            os.remove(caminho)
    except OSError as exc:  # noqa: BLE001 — best-effort, o erro original é o que importa
        logger.warning("nfc_ops: falha ao limpar arquivo temporário %s: %s", caminho, exc)


def remove_delivery(delivery: NfcTagDelivery) -> None:
    """Apaga a entrega — linha e arquivo do disco. Sem confirmação aqui: é o endpoint quem decide."""
    tag = delivery.tag
    _remove_delivery_file(delivery)
    db.session.delete(delivery)
    audit(
        "delete", "NfcTag", tag.id, tag.code,
        f"Entrega de {delivery.kind} removida da tag NFC nº {tag.sequence}",
    )
    db.session.commit()
