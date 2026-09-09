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
from datetime import datetime, timedelta
from typing import Any

from flask import current_app
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app import db
from app.constants import (
    NFC_DELIVERY_VIDEO_EXTENSIONS,
    NFC_DELIVERY_VIDEO_MAX_BYTES,
    NFC_MAX_CODE_ATTEMPTS,
    NFC_MOLDURA_EXTENSOES,
    NFC_PROCESSAMENTO_PRESO_MINUTOS,
    NFC_SUFFIX_ALPHABET,
    NFC_SUFFIX_LENGTH,
)
from app.impressoes3d import video_ops
from app.models import (
    Acervo3DItem,
    CalendarEvent,
    Client,
    Event3DGift,
    NfcTag,
    NfcTagDelivery,
    SiteSetting,
)
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
    """Entrega no payload público — só o que a página precisa para exibir, nada de caminho de disco.

    `width`/`height` entraram na feature 297 para a página reservar a altura do palco ANTES de o
    vídeo carregar. Sem eles o layout pulava quando os metadados chegavam, o que numa página que
    abre com uma animação de luz acendendo é um tranco visível.
    """
    return {
        "kind": delivery.kind,
        "title": delivery.title,
        "media_url": f"/api/nfc/{code}/entregas/{delivery.id}/media",
        "width": delivery.width,
        "height": delivery.height,
    }


def entrega_pronta(delivery: NfcTagDelivery) -> bool:
    """A entrega pode ser mostrada à cliente?

    Entrega em conversão (`pendente`/`processando`) ou que falhou não existe para o mundo lá fora:
    a página mostra o estado de sempre, como se ainda não houvesse vídeo, e a rota de mídia devolve
    o mesmo 404 genérico de sempre. Um vídeo pela metade seria pior que vídeo nenhum.
    """
    return bool(delivery.is_active) and delivery.processing_status == "pronto"


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
        (d for d in tag.deliveries if entrega_pronta(d)), key=lambda d: (d.sort_order, d.id)
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
        # Feature 297: o que o ERP precisa para mostrar o estado da conversão e o peso. Antes disto
        # a tela não tinha como saber que estava exibindo um arquivo de 147 MB.
        "processing_status": delivery.processing_status,
        "processing_error": delivery.processing_error,
        "processed_at": delivery.processed_at.isoformat() if delivery.processed_at else None,
        "file_size_bytes": delivery.file_size_bytes,
        "duration_seconds": (
            float(delivery.duration_seconds) if delivery.duration_seconds is not None else None
        ),
        "width": delivery.width,
        "height": delivery.height,
        "has_frame": bool(delivery.has_frame),
    }


# ── Entregas (US — feature 261) ───────────────────────────────────────────────


def _delivery_folder() -> str:
    return current_app.config["NFC_MEDIA_FOLDER"]


def delivery_mime_type(delivery: NfcTagDelivery) -> str:
    """MIME do arquivo da entrega.

    Desde a feature 297 o tipo é GRAVADO na conversão, e não readivinhado a cada requisição. A
    dedução por extensão fica como reserva para as entregas anteriores à migration e para o caso
    de degradação sem conversor — e ela tem defeito conhecido: `.m4v` produzia `video/m4v`, um
    MIME que não existe, e com `X-Content-Type-Options: nosniff` o navegador não tinha como se
    salvar sozinho.
    """
    if delivery.mime_type:
        return delivery.mime_type
    extensao = extension_of(delivery.file_path)
    if not extensao:
        return "video/mp4"
    sufixo = extensao.lstrip(".").lower()
    conhecidos = {"mp4": "video/mp4", "webm": "video/webm", "mov": "video/quicktime",
                  "m4v": "video/x-m4v"}
    return conhecidos.get(sufixo, "video/mp4")


def delivery_media_path(delivery: NfcTagDelivery) -> str | None:
    """Caminho absoluto do arquivo da entrega no disco, ou `None` se não há arquivo.

    Uso exclusivo do endpoint público que serve o arquivo (`GET .../entregas/<id>/media`) —
    este valor nunca sai em payload nenhum (mesmo contrato de `virtuais_ops.caminho_video`).
    """
    if not delivery.file_path:
        return None
    return os.path.join(_delivery_folder(), delivery.file_path)


def add_delivery(
    tag: NfcTag,
    file_obj: Any,
    *,
    kind: str = "video",
    title: str | None = None,
    com_moldura: bool = True,
) -> NfcTagDelivery:
    """Recebe o arquivo e ENFILEIRA a conversão — se já existe entrega ativa do mesmo `kind`, substitui.

    Mudou na feature 297: a requisição **não** converte. Ela grava o arquivo cru em
    `nfc_media/entrada/`, cria a linha em `pendente` e devolve. A conversão acontece depois, na
    thread de fundo, um vídeo por vez. Converter aqui prenderia quem enviou por minutos e seguraria
    uma thread do gunicorn com a única CPU do contêiner ocupada.

    `com_moldura` grava a escolha da caixinha do diálogo (marcada por padrão). Ela é decidida agora
    porque o arquivo já sobe: o processamento lê a intenção da linha, não da requisição.

    Args:
        tag: a tag que recebe a entrega.
        file_obj: o arquivo enviado (stream do multipart).
        kind: espécie de entrega; hoje só `"video"`.
        title: título exibido na página pública; vazio usa a copy padrão.
        com_moldura: gravar a moldura do sistema no vídeo entregue.

    Raises:
        NfcValidationError: `kind` não suportado, arquivo ausente, extensão fora da allowlist,
            acima do limite de tamanho, ou já existe conversão em andamento nesta tag.
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

    # CORRIDA REAL, e não hipotética: substituir apaga o arquivo e a linha da entrega anterior. Se
    # essa anterior estiver NA FILA, o worker já está com o caminho dela na mão e vai escrever num
    # arquivo que acabou de sumir, para uma linha que já não existe. Enquanto a conversão anterior
    # não terminar, o envio novo é recusado com o motivo à vista.
    anterior = next((d for d in tag.deliveries if d.kind == kind and d.is_active), None)
    if anterior is not None and anterior.processing_status in ("pendente", "processando"):
        raise NfcValidationError(
            "file",
            "Ainda estamos preparando o vídeo anterior desta tag. Aguarde ele ficar pronto para "
            "enviar outro.",
        )

    pasta = _pasta_entrada()
    os.makedirs(pasta, exist_ok=True)
    nome_bruto = f"{uuid.uuid4().hex}{extensao}"
    caminho = os.path.join(pasta, nome_bruto)

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

    if anterior is not None:
        _remover_arquivos_da_entrega(anterior)
        db.session.delete(anterior)

    delivery = NfcTagDelivery(
        tag_id=tag.id,
        kind=kind,
        title=(title or "").strip() or None,
        file_path=None,               # ainda não há o que servir: a conversão preenche
        source_file_path=nome_bruto,
        has_frame=bool(com_moldura),
        processing_status="pendente",
    )
    db.session.add(delivery)
    audit(
        "edit", "NfcTag", tag.id, tag.code,
        f"Entrega de {kind} {'substituída' if anterior else 'adicionada'} na tag NFC nº {tag.sequence}",
    )
    db.session.commit()
    return delivery


# ── Fila de conversão (feature 297) ──────────────────────────────────────────


def _pasta_entrada() -> str:
    return current_app.config["NFC_ENTRADA_FOLDER"]


def _pasta_mestres() -> str:
    return current_app.config["NFC_MESTRES_FOLDER"]


def _pasta_sistema() -> str:
    return current_app.config["NFC_SISTEMA_FOLDER"]


def _remover_arquivos_da_entrega(delivery: NfcTagDelivery) -> None:
    """Apaga do disco os três arquivos que uma entrega pode ter: entregue, mestre e cru."""
    for pasta, nome in (
        (_delivery_folder(), delivery.file_path),
        (_pasta_mestres(), delivery.master_file_path),
        (_pasta_entrada(), delivery.source_file_path),
    ):
        if not nome:
            continue
        caminho = os.path.join(pasta, nome)
        try:
            if os.path.exists(caminho):
                os.remove(caminho)
        except OSError as exc:  # noqa: BLE001 — órfão não pode travar a exclusão da linha
            logger.warning("nfc_ops: falha ao remover %s: %s", caminho, exc)


def moldura_path() -> str | None:
    """Caminho da moldura do sistema no disco, ou None se não houver uma cadastrada."""
    settings = SiteSetting.query.get(1)
    nome = settings.nfc_frame_path if settings else None
    if not nome:
        return None
    caminho = os.path.join(_pasta_sistema(), nome)
    return caminho if os.path.exists(caminho) else None


def abertura_path() -> str | None:
    """Caminho do vídeo de abertura no disco, ou None se não houver um cadastrado."""
    settings = SiteSetting.query.get(1)
    nome = settings.nfc_intro_video_path if settings else None
    if not nome:
        return None
    caminho = os.path.join(_pasta_sistema(), nome)
    return caminho if os.path.exists(caminho) else None


def _marca_de_versao(caminho: str | None) -> int | None:
    """Data de modificação do arquivo, em segundos, para furar cache do navegador.

    Moldura e abertura têm nome FIXO e são sobrescritas no lugar (molde do `logo_path`). Sem uma
    marca na URL, quem já viu a versão antiga continuaria vendo — e o dono trocaria o arquivo sem
    entender por que nada mudou.
    """
    if not caminho or not os.path.exists(caminho):
        return None
    return int(os.path.getmtime(caminho))


def estado_dos_arquivos_de_sistema() -> dict[str, Any]:
    """O que o ERP precisa saber sobre a moldura e o vídeo de abertura."""
    moldura = moldura_path()
    abertura = abertura_path()
    marca_moldura = _marca_de_versao(moldura)
    marca_abertura = _marca_de_versao(abertura)
    return {
        "moldura_url": f"/api/3d/nfc/moldura?v={marca_moldura}" if moldura else None,
        "moldura_atualizada_em": (
            datetime.utcfromtimestamp(marca_moldura).isoformat() if marca_moldura else None
        ),
        "abertura_url": f"/api/nfc/abertura/video?v={marca_abertura}" if abertura else None,
        "abertura_atualizada_em": (
            datetime.utcfromtimestamp(marca_abertura).isoformat() if marca_abertura else None
        ),
    }


def url_publica_da_abertura() -> str | None:
    """URL do vídeo de abertura para o payload público, com marca de versão, ou None."""
    marca = _marca_de_versao(abertura_path())
    return f"/api/nfc/abertura/video?v={marca}" if marca else None


def reivindicar_proxima_entrega() -> NfcTagDelivery | None:
    """Toma para si UMA entrega da fila, de forma atômica entre os três workers do gunicorn.

    O `AND processing_status = 'pendente'` depois do subselect não é redundância: sem ele, dois
    workers que escolhessem a mesma linha no subselect fariam os dois o `UPDATE`. Com ele, só um
    recebe `rowcount == 1`; o outro recebe zero e volta a dormir. Mesmo espírito do claim de
    `app/calendar/sync.py`, mas na linha do trabalho em vez de em `site_settings` — aqui a unidade
    de trabalho é o registro, não o ciclo.
    """
    linha = db.session.execute(
        db.text(
            "UPDATE nfc_tag_deliveries SET processing_status = 'processando', updated_at = :agora"
            " WHERE id = (SELECT id FROM nfc_tag_deliveries"
            "             WHERE processing_status = 'pendente' ORDER BY id LIMIT 1)"
            "   AND processing_status = 'pendente'"
            " RETURNING id"
        ),
        {"agora": datetime.utcnow()},
    ).fetchone()
    db.session.commit()
    if linha is None:
        return None
    return db.session.get(NfcTagDelivery, linha[0])


def destravar_presas() -> int:
    """Devolve à fila o que ficou preso em `processando`.

    Acontece quando um deploy troca o contêiner no meio de uma conversão: o processo morre, a linha
    fica marcada para sempre. Passado o prazo, ela volta a `pendente` e alguém pega de novo.
    """
    limite = datetime.utcnow() - timedelta(minutes=NFC_PROCESSAMENTO_PRESO_MINUTOS)
    resultado = db.session.execute(
        db.text(
            "UPDATE nfc_tag_deliveries SET processing_status = 'pendente'"
            " WHERE processing_status = 'processando' AND updated_at < :limite"
        ),
        {"limite": limite},
    )
    db.session.commit()
    return resultado.rowcount or 0


def processar_entrega(delivery: NfcTagDelivery) -> NfcTagDelivery:
    """Converte o arquivo cru de uma entrega e a deixa pronta para a cliente.

    Produz até dois arquivos: o MESTRE (1080p sem moldura, guardado para reprocessar depois) e o
    ENTREGUE (o mestre com a moldura gravada). Sem moldura, os dois são o mesmo arquivo e só um
    existe no disco.

    Nunca levanta por falta de ffmpeg ou por falha de conversão: nesses casos entrega o arquivo
    como ele veio, registra o motivo em `processing_error` e marca `pronto`. Perder o vídeo da
    cliente porque o conversor falhou seria trocar um problema por outro pior.
    """
    origem = (
        os.path.join(_pasta_entrada(), delivery.source_file_path)
        if delivery.source_file_path
        else None
    )
    if not origem or not os.path.exists(origem):
        # Reprocessamento: a origem passa a ser o mestre; e, se nem ele existe (as entregas
        # anteriores à feature 297), o próprio arquivo entregue hoje.
        origem = _origem_de_reprocessamento(delivery)
    if not origem or not os.path.exists(origem):
        delivery.processing_status = "falhou"
        delivery.processing_error = "O arquivo de origem não está mais no disco."
        db.session.commit()
        return delivery

    quer_moldura = bool(delivery.has_frame)
    moldura = moldura_path() if quer_moldura else None
    avisos: list[str] = []
    if quer_moldura and not moldura:
        avisos.append("Nenhuma moldura cadastrada — o vídeo foi entregue sem moldura.")

    if not video_ops.ffmpeg_disponivel():
        return _entregar_sem_converter(
            delivery, origem,
            "O conversor de vídeo não está disponível neste servidor — o arquivo foi entregue "
            "como veio.",
        )

    nome_base = uuid.uuid4().hex
    caminho_mestre = os.path.join(_pasta_mestres(), f"{nome_base}.mp4")
    try:
        info_mestre = video_ops.converter(origem, caminho_mestre)
    except video_ops.VideoIndisponivel as exc:
        return _entregar_sem_converter(delivery, origem, str(exc))

    if moldura:
        caminho_entregue = os.path.join(_delivery_folder(), f"{nome_base}.mp4")
        try:
            info = video_ops.converter(origem, caminho_entregue, moldura=moldura)
        except video_ops.VideoIndisponivel as exc:
            avisos.append(f"A moldura não pôde ser aplicada: {exc}")
            caminho_entregue = os.path.join(_delivery_folder(), f"{nome_base}.mp4")
            os.replace(caminho_mestre, caminho_entregue)
            info = info_mestre
            caminho_mestre = caminho_entregue
            quer_moldura = False
    else:
        # Sem moldura, mestre e entregue são o MESMO arquivo: guardar duas cópias idênticas
        # dobraria o disco sem dar nada em troca.
        caminho_entregue = os.path.join(_delivery_folder(), f"{nome_base}.mp4")
        os.replace(caminho_mestre, caminho_entregue)
        caminho_mestre = caminho_entregue
        info = info_mestre

    _apagar_arquivos_antigos(delivery)
    delivery.file_path = os.path.basename(caminho_entregue)
    delivery.master_file_path = (
        os.path.basename(caminho_mestre) if caminho_mestre != caminho_entregue else None
    )
    delivery.mime_type = "video/mp4"
    delivery.file_size_bytes = info.tamanho_bytes
    delivery.duration_seconds = round(info.duracao_segundos, 2)
    delivery.width = info.largura
    delivery.height = info.altura
    delivery.has_frame = bool(quer_moldura and moldura)
    delivery.processing_status = "pronto"
    delivery.processing_error = " ".join(avisos) or None
    delivery.processed_at = datetime.utcnow()
    _limpar_entrada(delivery)
    db.session.commit()
    return delivery


def _origem_de_reprocessamento(delivery: NfcTagDelivery) -> str | None:
    """De onde parte um reprocessamento: o mestre; na falta dele, o próprio arquivo entregue.

    As dez entregas que existiam antes da feature 297 não têm mestre — elas SÃO o arquivo cru da
    câmera. Reprocessá-las parte do que existe, com a perda de qualidade que o dono aceitou em
    troca de um vídeo que a cliente consiga assistir.
    """
    if delivery.master_file_path:
        caminho = os.path.join(_pasta_mestres(), delivery.master_file_path)
        if os.path.exists(caminho):
            return caminho
    if delivery.file_path:
        caminho = os.path.join(_delivery_folder(), delivery.file_path)
        if os.path.exists(caminho):
            return caminho
    return None


def _entregar_sem_converter(
    delivery: NfcTagDelivery, origem: str, motivo: str
) -> NfcTagDelivery:
    """Degradação segura: entrega o arquivo como veio e registra por quê.

    O vídeo da cliente nunca se perde porque o conversor faltou. A tela mostra o motivo, e o
    comando de reprocessamento resolve quando o conversor voltar.
    """
    extensao = extension_of(origem) or ".mp4"
    nome = f"{uuid.uuid4().hex}{extensao}"
    destino = os.path.join(_delivery_folder(), nome)
    try:
        os.replace(origem, destino)
    except OSError as exc:
        delivery.processing_status = "falhou"
        delivery.processing_error = f"{motivo} E o arquivo não pôde ser movido: {exc}"
        db.session.commit()
        return delivery
    _apagar_arquivos_antigos(delivery)
    delivery.file_path = nome
    delivery.master_file_path = None
    delivery.mime_type = None
    delivery.file_size_bytes = os.path.getsize(destino)
    delivery.has_frame = False
    delivery.processing_status = "pronto"
    delivery.processing_error = motivo
    delivery.processed_at = datetime.utcnow()
    delivery.source_file_path = None
    db.session.commit()
    return delivery


def _apagar_arquivos_antigos(delivery: NfcTagDelivery) -> None:
    """Remove os arquivos da versão ANTERIOR desta entrega, depois que a nova já existe no disco."""
    for pasta, nome in (
        (_delivery_folder(), delivery.file_path),
        (_pasta_mestres(), delivery.master_file_path),
    ):
        if not nome:
            continue
        caminho = os.path.join(pasta, nome)
        try:
            if os.path.exists(caminho):
                os.remove(caminho)
        except OSError as exc:  # noqa: BLE001 — órfão é aceitável; perder o vídeo novo não
            logger.warning("nfc_ops: falha ao remover versão antiga %s: %s", caminho, exc)


def _limpar_entrada(delivery: NfcTagDelivery) -> None:
    """Apaga o arquivo cru depois da conversão bem-sucedida e esquece o caminho."""
    if not delivery.source_file_path:
        return
    caminho = os.path.join(_pasta_entrada(), delivery.source_file_path)
    try:
        if os.path.exists(caminho):
            os.remove(caminho)
    except OSError as exc:  # noqa: BLE001 — o cru é descartável por definição
        logger.warning("nfc_ops: falha ao remover o arquivo cru %s: %s", caminho, exc)
    delivery.source_file_path = None


def processar_proxima() -> NfcTagDelivery | None:
    """Toma uma entrega da fila e a converte. Devolve None quando a fila está vazia.

    É o corpo de um ciclo da thread de fundo, e também o que o `verify_297.py` chama à mão — com
    `MANTO_SEM_THREADS=1` não há thread nenhuma, e a verificação precisa ser determinística.
    """
    delivery = reivindicar_proxima_entrega()
    if delivery is None:
        return None
    try:
        return processar_entrega(delivery)
    except Exception as exc:  # noqa: BLE001 — a fila nunca pode morrer por um vídeo ruim
        logger.warning("nfc_ops: falha ao processar entrega %s: %s", delivery.id, exc)
        db.session.rollback()
        delivery = db.session.get(NfcTagDelivery, delivery.id)
        if delivery is not None:
            delivery.processing_status = "falhou"
            delivery.processing_error = str(exc)[:500]
            db.session.commit()
        return delivery


def reprocessar_delivery(
    delivery: NfcTagDelivery, *, com_moldura: bool | None = None
) -> NfcTagDelivery:
    """Devolve uma entrega à fila, opcionalmente trocando a escolha da moldura.

    Raises:
        NfcValidationError: a entrega já está na fila (não faz sentido enfileirar duas vezes) ou
            não há mais de onde partir.
    """
    if delivery.processing_status in ("pendente", "processando"):
        raise NfcValidationError(
            "delivery", "Este vídeo já está na fila de preparação."
        )
    if _origem_de_reprocessamento(delivery) is None and not delivery.source_file_path:
        raise NfcValidationError(
            "delivery", "Não há arquivo de origem para refazer este vídeo."
        )
    if com_moldura is not None:
        delivery.has_frame = bool(com_moldura)
    delivery.processing_status = "pendente"
    delivery.processing_error = None
    db.session.commit()
    return delivery


def salvar_arquivo_de_sistema(file_obj: Any, *, tipo: str) -> str:
    """Guarda a moldura ou o vídeo de abertura, com nome fixo, no molde de `logo_path`.

    Nome fixo significa sobrescrever no mesmo caminho — o mesmo que o logotipo do sistema faz. Em
    troca, quem já viu o arquivo pode ficar com a versão antiga em cache; por isso as rotas que
    servem esses dois arquivos mandam prazo curto e um parâmetro de versão.

    Args:
        file_obj: o arquivo enviado.
        tipo: `"moldura"` ou `"abertura"`.

    Returns:
        O nome do arquivo gravado.

    Raises:
        NfcValidationError: extensão fora da allowlist, PNG sem transparência real, ou vídeo acima
            do limite.
    """
    nome_original = getattr(file_obj, "filename", "") or ""
    if not nome_original:
        raise NfcValidationError("file", "Escolha o arquivo.")
    extensao = extension_of(nome_original)

    if tipo == "moldura":
        if extensao not in NFC_MOLDURA_EXTENSOES:
            raise NfcValidationError("file", "A moldura precisa ser um PNG.")
        from app import imaging

        file_obj.seek(0)
        try:
            imagem = imaging.abrir(file_obj)
        except Exception as exc:  # noqa: BLE001 — arquivo corrompido ou não-imagem
            raise NfcValidationError("file", "Não foi possível ler este PNG.") from exc
        if not imaging.tem_transparencia_real(imagem.convert("RGBA")):
            raise NfcValidationError(
                "file",
                "Este PNG não tem fundo transparente — ele cobriria o vídeo inteiro em vez de "
                "emoldurá-lo.",
            )
        nome_final = "moldura.png"
    elif tipo == "abertura":
        if extensao not in NFC_DELIVERY_VIDEO_EXTENSIONS:
            raise NfcValidationError(
                "file",
                f"Formato não suportado (use {', '.join(sorted(NFC_DELIVERY_VIDEO_EXTENSIONS))}).",
            )
        nome_final = "abertura.mp4"
    else:  # pragma: no cover — chamada interna com literal
        raise NfcValidationError("file", "Tipo de arquivo de sistema desconhecido.")

    pasta = _pasta_sistema()
    os.makedirs(pasta, exist_ok=True)
    destino = os.path.join(pasta, nome_final)
    # Sufixo `.entrada`, e NÃO `.parcial`: o `video_ops.converter` usa `<destino>.parcial` como o
    # temporário DELE. Com o mesmo nome, o ffmpeg leria e escreveria no mesmo arquivo e a conversão
    # morria com FileNotFoundError. Achado abrindo a tela, não pelo verify.
    parcial = f"{destino}.entrada"

    tamanho = 0
    try:
        file_obj.seek(0)
        with open(parcial, "wb") as saida:
            while True:
                pedaco = file_obj.read(1024 * 1024)
                if not pedaco:
                    break
                tamanho += len(pedaco)
                if tamanho > NFC_DELIVERY_VIDEO_MAX_BYTES:
                    raise NfcValidationError(
                        "file",
                        f"Arquivo acima do limite de "
                        f"{NFC_DELIVERY_VIDEO_MAX_BYTES // (1024 * 1024)} MB.",
                    )
                saida.write(pedaco)
    except NfcValidationError:
        _apagar_arquivo(parcial)
        raise
    except OSError as exc:
        _apagar_arquivo(parcial)
        raise NfcValidationError("file", "Não foi possível guardar o arquivo agora.") from exc

    if tamanho == 0:
        _apagar_arquivo(parcial)
        raise NfcValidationError("file", "O arquivo chegou vazio.")

    # O vídeo de abertura passa pela MESMA conversão dos vídeos de tag, sem moldura: ele é servido
    # a todo mundo que encosta o celular numa luminária, então precisa ser leve pelo mesmo motivo.
    if tipo == "abertura" and video_ops.ffmpeg_disponivel():
        try:
            video_ops.converter(parcial, destino)
            _apagar_arquivo(parcial)
        except video_ops.VideoIndisponivel as exc:
            logger.warning("nfc_ops: abertura não convertida (%s); guardando como veio", exc)
            os.replace(parcial, destino)
    else:
        os.replace(parcial, destino)

    settings = SiteSetting.query.get(1)
    if tipo == "moldura":
        settings.nfc_frame_path = nome_final
    else:
        settings.nfc_intro_video_path = nome_final
    audit("edit", "SiteSetting", 1, tipo, f"Arquivo de sistema das tags NFC atualizado: {tipo}")
    db.session.commit()
    return nome_final


def remover_arquivo_de_sistema(*, tipo: str) -> None:
    """Apaga a moldura ou o vídeo de abertura e zera o ponteiro no banco."""
    settings = SiteSetting.query.get(1)
    nome = settings.nfc_frame_path if tipo == "moldura" else settings.nfc_intro_video_path
    if nome:
        caminho = os.path.join(_pasta_sistema(), nome)
        try:
            if os.path.exists(caminho):
                os.remove(caminho)
        except OSError as exc:  # noqa: BLE001 — o ponteiro some de qualquer forma
            logger.warning("nfc_ops: falha ao remover %s: %s", caminho, exc)
    if tipo == "moldura":
        settings.nfc_frame_path = None
    else:
        settings.nfc_intro_video_path = None
    audit("edit", "SiteSetting", 1, tipo, f"Arquivo de sistema das tags NFC removido: {tipo}")
    db.session.commit()


def _apagar_arquivo(caminho: str) -> None:
    """Remove um arquivo recém-gravado que não deve ficar no disco (upload falho/vazio)."""
    try:
        if os.path.exists(caminho):
            os.remove(caminho)
    except OSError as exc:  # noqa: BLE001 — best-effort, o erro original é o que importa
        logger.warning("nfc_ops: falha ao limpar arquivo temporário %s: %s", caminho, exc)


def remove_delivery(delivery: NfcTagDelivery) -> None:
    """Apaga a entrega — linha e arquivos do disco. Sem confirmação aqui: é o endpoint quem decide.

    São até TRÊS arquivos desde a feature 297 (entregue, mestre e cru), e não um só: apagar apenas
    o entregue deixaria o mestre ocupando disco para sempre, invisível.
    """
    tag = delivery.tag
    _remover_arquivos_da_entrega(delivery)
    db.session.delete(delivery)
    audit(
        "delete", "NfcTag", tag.id, tag.code,
        f"Entrega de {delivery.kind} removida da tag NFC nº {tag.sequence}",
    )
    db.session.commit()
