"""Núcleo de negócio da Loja de Interações Virtuais (feature 205).

Funções puras (sem ``request``/``render_template``/``flash``), fonte única reusada pelos endpoints
JSON de ``app/api/virtuais_*.py``. Toda a orquestração da feature mora aqui — as rotas só validam
RBAC, chamam estas funções e serializam (Princípio III).

**Regra monetária (Princípio IX)**: tudo aqui opera em ``Decimal`` de reais. Centavos existem
apenas dentro de ``app/integracoes/infinitepay_client.py``, na fronteira com a operadora.

Escopo já implementado: campanhas, estoque de horários e acervo liberado (US1); reserva com soft
lock, anti-abuso e link de pagamento (US2). Webhook, efetivação, fila de produção e devoluções
entram nas fases seguintes.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import secrets
import unicodedata
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from flask import current_app
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import lazyload

from app import db
from app.constants import (  # feature 310
    EVENT_TYPE_VIRTUAL,
    VIRTUAL_ANTECEDENCIA_RESERVA_HORAS,
    VIRTUAL_AVISO_CONFLITO,
    VIRTUAL_AVISO_DEVOLUCAO,
    VIRTUAL_AVISO_DIVERGENTE,
    VIRTUAL_AVISO_DUPLICADO,
    VIRTUAL_AVISO_EFETIVADO,
    VIRTUAL_AVISO_FINAIS,
    VIRTUAL_AVISO_ORFAO,
    VIRTUAL_AVISO_PENDENTE_PROVA,
    VIRTUAL_AVISO_RECUSADO_TOKEN,
    VIRTUAL_AVISO_REPROCESSA_HORAS,
    VIRTUAL_AVISO_RETIDO,
    VIRTUAL_AVISO_RETRY_LONGO_MIN,
    VIRTUAL_AVISO_STATE_DECIDIDO,
    VIRTUAL_AVISO_STATE_PENDENTE,
    VIRTUAL_AVISO_STATE_PROCESSANDO,
    VIRTUAL_CAMPAIGN_STATUS_PUBLICADA,
    VIRTUAL_CAMPAIGN_STATUS_RASCUNHO,
    VIRTUAL_CAMPAIGN_STATUSES,
    VIRTUAL_MIN_MINUTOS_NO_PAGAMENTO,
    VIRTUAL_MODALITIES,
    VIRTUAL_MODALITY_AO_VIVO,
    VIRTUAL_MODALITY_GRAVADO,
    VIRTUAL_NOTIFICATION_KIND_CANCELAMENTO,
    VIRTUAL_NOTIFICATION_KIND_COMPRA,
    VIRTUAL_NOTIFICATION_KIND_VIDEO,
    VIRTUAL_NOTIFICATION_LABELS,
    VIRTUAL_ORDER_STATUS_AGUARDANDO,
    VIRTUAL_ORDER_STATUS_CANCELADO,
    VIRTUAL_ORDER_STATUS_EXPIRADO,
    VIRTUAL_ORDER_STATUS_PAGO,
    VIRTUAL_ORDER_STATUS_RESERVADO,
    VIRTUAL_PRODUCTION_STATUS_FINALIZADO,
    VIRTUAL_PRODUCTION_STATUS_PENDENTE,
    VIRTUAL_PRODUCTION_STATUSES,
    VIRTUAL_REFUND_REASON_CONFLITO,
    VIRTUAL_REFUND_REASON_HORARIO_PASSOU,
    VIRTUAL_REFUND_REASON_LABELS,
    VIRTUAL_REFUND_REASON_PAGAMENTO_EM_DOBRO,
    VIRTUAL_REFUND_REASON_SEM_CONFIRMACAO,
    VIRTUAL_REFUND_REASON_SEM_PEDIDO_ATIVO,
    VIRTUAL_REFUND_REASON_SEM_VAGA_VIDEO,
    VIRTUAL_REFUND_STATUS_PENDENTE,
    VIRTUAL_RETRY_INTERVAL_MIN,
    VIRTUAL_RETRY_MAX_ATTEMPTS,
    VIRTUAL_SLOT_MINUTES,
    VIRTUAL_SLOT_STATUS_LIVRE,
    VIRTUAL_SLOT_STATUS_TRAVADO,
    VIRTUAL_SLOT_STATUS_VENDIDO,
    VIRTUAL_SOFT_LOCK_MINUTES,
    VIRTUAL_VIDEO_EXTENSIONS,
    VIRTUAL_VIDEO_MAX_BYTES,
)
from app.constants import (
    now_sp as agora,
)
from app.models import (
    Acervo3DItem,
    CalendarEvent,
    CatalogCharacter,
    EventRole,
    SiteSetting,
    VirtualCampaign,
    VirtualCampaignSlot,
    VirtualMediaDelivery,
    VirtualOrder,
    VirtualOrderNotification,
    VirtualPaymentNotification,
    VirtualRefundRequest,
)
from app.utils import audit

logger = logging.getLogger(__name__)

# Janela máxima que a geração de horários aceita de uma vez. Existe para um dígito errado na hora
# de fim não gerar milhares de linhas (ex.: "18:00" digitado como "1800").
MAX_SLOTS_POR_GERACAO = 500

# Estados em que uma reserva ainda segura um horário e conta para o limite por telefone.
VIRTUAL_ORDER_STATUS_ATIVOS = (VIRTUAL_ORDER_STATUS_RESERVADO, VIRTUAL_ORDER_STATUS_AGUARDANDO)


class VirtuaisConflitoError(Exception):
    """O horário (ou a última vaga de vídeo) acabou de ser tomado por outra pessoa.

    Vira **409** na API, junto da lista de horários atualizada — o segundo visitante precisa saber
    que perdeu a corrida, e não achar que o site está com defeito (US2 cenário 5).
    """


class VirtuaisLimiteError(Exception):
    """Limite anti-abuso atingido (FR-020a/FR-020b). Vira **429** na API.

    ``existing_order_token`` vem preenchido quando o motivo é "já existe reserva ativa com este
    telefone": a família precisa poder retomar o pedido que ela mesma criou, não bater numa parede.
    """

    def __init__(self, message: str, *, existing_order_token: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.existing_order_token = existing_order_token


class VirtuaisOperadoraError(Exception):
    """A operadora falhou ao gerar o link de pagamento. Vira **502** na API."""


class VirtuaisPagamentoFechadoError(Exception):
    """Pagamento desligado ou não configurado (feature 310, R-18). Vira **503** na API."""


class VirtuaisValidationError(Exception):
    """Erro de validação de negócio da feature, com o campo culpado.

    O endpoint traduz em ``json_error(msg, 400, fields={campo: msg})``, para o React destacar o
    campo exato do formulário (Princípio V — falha de validação sempre tem feedback no campo).
    """

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


# ── Conversões e validações de campo ─────────────────────────────────────────


def parse_money(raw: Any, field: str, *, label: str) -> Decimal:
    """Converte um valor monetário recebido da API em ``Decimal`` de reais.

    Aceita número ou string decimal (``"150.00"``). **Não** aceita centavos nem ``float``: o JSON
    da nossa API trafega reais (Princípio IX), e ponto flutuante é como o centavo some.

    Raises:
        VirtuaisValidationError: Valor ausente, ilegível ou negativo.
    """
    if raw is None or raw == "":
        raise VirtuaisValidationError(field, f"{label} é obrigatório.")
    try:
        value = Decimal(str(raw).strip()).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise VirtuaisValidationError(field, f"{label} inválido.") from None
    if value < 0:
        raise VirtuaisValidationError(field, f"{label} não pode ser negativo.")
    return value


def _parse_int(raw: Any, field: str, *, label: str, minimum: int = 0) -> int:
    """Converte um inteiro recebido da API, com piso."""
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise VirtuaisValidationError(field, f"{label} inválido.") from None
    if value < minimum:
        raise VirtuaisValidationError(field, f"{label} deve ser no mínimo {minimum}.")
    return value


def _parse_time(raw: Any, field: str, *, label: str) -> time:
    """Converte ``HH:MM`` em ``time``."""
    try:
        hour, minute = str(raw).strip().split(":")
        return time(int(hour), int(minute))
    except (AttributeError, TypeError, ValueError):
        raise VirtuaisValidationError(field, f"{label} inválido (use HH:MM).") from None


def _parse_date(raw: Any, field: str, *, label: str) -> date:
    """Converte ``AAAA-MM-DD`` em ``date``."""
    if isinstance(raw, date):
        return raw
    try:
        return date.fromisoformat(str(raw).strip())
    except (TypeError, ValueError):
        raise VirtuaisValidationError(field, f"{label} inválido (use AAAA-MM-DD).") from None


def slugify(value: str) -> str:
    """Converte um texto livre no slug da campanha (minúsculas, sem acento, hifens)."""
    text = unicodedata.normalize("NFKD", (value or "").strip().lower())
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-{2,}", "-", text).strip("-")


def _unique_slug(base: str, *, campaign_id: int | None = None) -> str:
    """Devolve um slug livre, acrescentando sufixo numérico se já existir."""
    root = base or "campanha"
    candidate = root
    suffix = 2
    while True:
        query = VirtualCampaign.query.filter_by(slug=candidate)
        if campaign_id is not None:
            query = query.filter(VirtualCampaign.id != campaign_id)
        if query.first() is None:
            return candidate
        candidate = f"{root}-{suffix}"
        suffix += 1


def _normalize_faq(raw: Any) -> str | None:
    """Valida e serializa o FAQ em JSON (lista de ``{pergunta, resposta}``)."""
    if raw in (None, "", []):
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            raise VirtuaisValidationError("faq", "FAQ inválido.") from None
    if not isinstance(raw, list):
        raise VirtuaisValidationError("faq", "FAQ deve ser uma lista de perguntas.")

    items = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise VirtuaisValidationError("faq", "Cada item do FAQ precisa de pergunta e resposta.")
        pergunta = (entry.get("pergunta") or "").strip()
        resposta = (entry.get("resposta") or "").strip()
        if not pergunta or not resposta:
            raise VirtuaisValidationError("faq", "Pergunta e resposta do FAQ são obrigatórias.")
        items.append({"pergunta": pergunta, "resposta": resposta})
    return json.dumps(items, ensure_ascii=False) if items else None


# ── Campanhas ────────────────────────────────────────────────────────────────


def criar_campanha(
    *,
    catalog_character_id: Any,
    title: str,
    price_live: Any,
    price_recorded: Any,
    price_gift: Any = 0,
    recorded_capacity: Any = 0,
    recorded_delivery_days: Any = 7,
    intro_html: str | None = None,
    tolerance_terms: str | None = None,
    faq: Any = None,
    cover_url: str | None = None,
    whatsapp_phone: str | None = None,
    talent_id: Any = None,
    figurino_sheet_id: Any = None,
) -> VirtualCampaign:
    """Cria uma campanha virtual vinculada a um Personagem ativo do catálogo (FR-001).

    Nasce sempre em ``rascunho``: publicar é um ato separado e explícito (FR-007), para ninguém
    expor ao público uma oferta ainda pela metade.

    O figurino, quando não informado, é herdado do vínculo que o personagem já tem no catálogo —
    é ele que a automação usa na pré-escala quando a venda se efetiva (FR-031).

    Raises:
        VirtuaisValidationError: Personagem inexistente/inativo ou campo obrigatório inválido.
    """
    character = CatalogCharacter.query.get(catalog_character_id) if catalog_character_id else None
    if character is None:
        raise VirtuaisValidationError("catalog_character_id", "Selecione um personagem do catálogo.")
    if not character.is_active:
        raise VirtuaisValidationError(
            "catalog_character_id", "Este personagem está inativo no catálogo."
        )

    clean_title = (title or "").strip()
    if not clean_title:
        raise VirtuaisValidationError("title", "Título da campanha é obrigatório.")

    campaign = VirtualCampaign(
        catalog_character_id=character.id,
        slug=_unique_slug(slugify(clean_title)),
        status=VIRTUAL_CAMPAIGN_STATUS_RASCUNHO,
        title=clean_title,
        intro_html=(intro_html or "").strip() or None,
        tolerance_terms=(tolerance_terms or "").strip() or None,
        faq_json=_normalize_faq(faq),
        cover_url=cover_url,
        whatsapp_phone=(whatsapp_phone or "").strip() or None,
        price_live=parse_money(price_live, "price_live", label="Valor da chamada ao vivo"),
        price_recorded=parse_money(
            price_recorded, "price_recorded", label="Valor do vídeo gravado"
        ),
        price_gift=parse_money(price_gift or 0, "price_gift", label="Valor do presente 3D"),
        recorded_capacity=_parse_int(
            recorded_capacity or 0, "recorded_capacity", label="Capacidade de vídeos gravados"
        ),
        recorded_delivery_days=_parse_int(
            recorded_delivery_days or 7, "recorded_delivery_days",
            label="Prazo de entrega do vídeo", minimum=1,
        ),
        talent_id=talent_id or None,
        figurino_sheet_id=figurino_sheet_id or character.figurino_sheet_id,
    )
    db.session.add(campaign)
    db.session.flush()
    audit(
        "create", "VirtualCampaign", campaign.id, clean_title,
        f"Campanha virtual criada para o personagem '{character.name}'",
    )
    db.session.commit()
    return campaign


def atualizar_campanha(campaign: VirtualCampaign, **campos: Any) -> VirtualCampaign:
    """Edita uma campanha. Só aplica os campos explicitamente informados.

    Alterar preço aqui **não** afeta pedido nenhum: os valores ficam congelados na linha do pedido
    desde a reserva (FR-022). O novo preço vale a partir da próxima reserva.
    """
    if "title" in campos:
        clean_title = (campos["title"] or "").strip()
        if not clean_title:
            raise VirtuaisValidationError("title", "Título da campanha é obrigatório.")
        campaign.title = clean_title

    money_fields = {
        "price_live": "Valor da chamada ao vivo",
        "price_recorded": "Valor do vídeo gravado",
        "price_gift": "Valor do presente 3D",
    }
    for field, label in money_fields.items():
        if field in campos:
            setattr(campaign, field, parse_money(campos[field], field, label=label))

    int_fields = {
        "recorded_capacity": ("Capacidade de vídeos gravados", 0),
        "recorded_delivery_days": ("Prazo de entrega do vídeo", 1),
        "max_reservations_per_origin": ("Limite de reservas por origem", 1),
        "reservation_window_minutes": ("Janela do limite de reservas", 1),
    }
    for field, (label, minimum) in int_fields.items():
        if field in campos:
            setattr(
                campaign, field,
                _parse_int(campos[field], field, label=label, minimum=minimum),
            )

    for field in ("intro_html", "tolerance_terms", "whatsapp_phone"):
        if field in campos:
            setattr(campaign, field, (campos[field] or "").strip() or None)

    if "cover_url" in campos and campos["cover_url"]:
        campaign.cover_url = campos["cover_url"]
    if "faq" in campos:
        campaign.faq_json = _normalize_faq(campos["faq"])
    if "talent_id" in campos:
        campaign.talent_id = campos["talent_id"] or None
    if "figurino_sheet_id" in campos:
        campaign.figurino_sheet_id = campos["figurino_sheet_id"] or None

    audit("edit", "VirtualCampaign", campaign.id, campaign.title, "Campanha virtual editada")
    db.session.commit()
    return campaign


def alterar_status(campaign: VirtualCampaign, status: str) -> VirtualCampaign:
    """Publica, pausa ou volta a campanha para rascunho (FR-007).

    Publicar exige a oferta completa: sem preços, capacidade, prazo e capa, a landing sairia
    quebrada para a família. Pausar **não** invalida reservas em curso — elas seguem até expirar
    ou serem pagas; o que para é a entrada de reservas novas.

    Raises:
        VirtuaisValidationError: Status inválido, ou publicação com campo obrigatório faltando.
    """
    clean_status = (status or "").strip().lower()
    if clean_status not in VIRTUAL_CAMPAIGN_STATUSES:
        raise VirtuaisValidationError(
            "status", f"Status inválido (use: {', '.join(VIRTUAL_CAMPAIGN_STATUSES)})."
        )

    if clean_status == VIRTUAL_CAMPAIGN_STATUS_PUBLICADA:
        faltando = _campos_faltantes_para_publicar(campaign)
        if faltando:
            campo, mensagem = faltando
            raise VirtuaisValidationError(campo, mensagem)

    campaign.status = clean_status
    audit(
        "edit", "VirtualCampaign", campaign.id, campaign.title,
        f"Campanha virtual movida para '{clean_status}'",
    )
    db.session.commit()
    return campaign


def _campos_faltantes_para_publicar(campaign: VirtualCampaign) -> tuple[str, str] | None:
    """Primeiro campo que impede a publicação, ou ``None`` se a campanha está pronta."""
    if campaign.price_live is None or campaign.price_recorded is None:
        return ("price_live", "Defina os preços antes de publicar.")
    # Zero não é preço (304): a campanha nasce em rascunho com R$ 0,00 quando o time ainda não
    # decidiu o valor (é assim que o script do Papai Noel a cria), e a trava acima só via `None` —
    # publicar esquecido iria ao ar de graça. O vídeo só cobra quando há vaga de vídeo à venda.
    if campaign.price_live <= 0:
        return ("price_live", "Defina o valor da chamada ao vivo antes de publicar.")
    if (campaign.recorded_capacity or 0) > 0 and campaign.price_recorded <= 0:
        return (
            "price_recorded",
            "Defina o valor do vídeo gravado antes de publicar (ou zere a capacidade de vídeos).",
        )
    if not campaign.cover_url:
        return ("cover_url", "A foto de capa é obrigatória para publicar.")
    if not campaign.recorded_delivery_days:
        return (
            "recorded_delivery_days",
            "Defina o prazo de entrega do vídeo gravado antes de publicar.",
        )
    if not campaign.tolerance_terms:
        return ("tolerance_terms", "Escreva os termos de tolerância antes de publicar.")
    # Feature 310 (FR-022): publicar com o pagamento desligado ou sem configuração punha no ar uma
    # campanha em que toda família preenchia a ficha para receber um erro no fim.
    if not _pagamento_ligado():
        return (
            "pagamento",
            "Ligue o pagamento da loja em Configurações (InfiniteTag, segredo e interruptor) "
            "antes de publicar.",
        )
    return None


def definir_acervo_liberado(campaign: VirtualCampaign, item_ids: list[Any]) -> VirtualCampaign:
    """Define quais peças do Acervo 3D podem ser ofertadas nesta campanha (FR-006).

    Substitui a seleção inteira — é o comportamento que a tela espera ao salvar. Peças inativas
    são recusadas: liberar o que não pode ser impresso só criaria pedido impossível de entregar.
    """
    ids = {int(i) for i in (item_ids or []) if str(i).isdigit()}
    items = Acervo3DItem.query.filter(Acervo3DItem.id.in_(ids)).all() if ids else []

    if len(items) != len(ids):
        raise VirtuaisValidationError("item_ids", "Uma das peças selecionadas não existe.")
    inativas = [i.name for i in items if not i.is_active]
    if inativas:
        raise VirtuaisValidationError(
            "item_ids", f"Peça inativa no Acervo: {', '.join(inativas)}."
        )

    campaign.acervo_items = items
    audit(
        "edit", "VirtualCampaign", campaign.id, campaign.title,
        f"Acervo 3D liberado atualizado ({len(items)} peça(s))",
    )
    db.session.commit()
    return campaign


# ── Estoque de horários ──────────────────────────────────────────────────────


def gerar_slots(campaign: VirtualCampaign, *, day: Any, start: Any, end: Any) -> dict[str, int]:
    """Gera os horários de 10 minutos de uma janela (FR-004).

    **Idempotente**: horários que já existem são contados em ``skipped`` e nada é duplicado — a
    garantia final é o ``UNIQUE(campaign_id, start_at)`` do banco, mas conferimos antes para poder
    responder quantos foram pulados.

    Args:
        campaign: A campanha que recebe os horários.
        day: Data da janela (``AAAA-MM-DD``).
        start: Hora inicial (``HH:MM``).
        end: Hora final, exclusiva (``HH:MM``).

    Returns:
        ``{"created": int, "skipped": int}``.

    Raises:
        VirtuaisValidationError: Janela inválida, invertida ou grande demais.
    """
    target_day = _parse_date(day, "date", label="Data")
    start_time = _parse_time(start, "start", label="Hora de início")
    end_time = _parse_time(end, "end", label="Hora de fim")

    inicio = datetime.combine(target_day, start_time)
    fim = datetime.combine(target_day, end_time)
    if fim <= inicio:
        raise VirtuaisValidationError("end", "A hora de fim precisa ser depois da de início.")

    total = int((fim - inicio).total_seconds() // 60 // VIRTUAL_SLOT_MINUTES)
    if total > MAX_SLOTS_POR_GERACAO:
        raise VirtuaisValidationError(
            "end", f"Janela grande demais: geraria {total} horários (máximo {MAX_SLOTS_POR_GERACAO})."
        )

    existentes = {
        slot.start_at
        for slot in VirtualCampaignSlot.query.filter(
            VirtualCampaignSlot.campaign_id == campaign.id,
            VirtualCampaignSlot.start_at >= inicio,
            VirtualCampaignSlot.start_at < fim,
        ).all()
    }

    created = 0
    skipped = 0
    momento = inicio
    while momento < fim:
        if momento in existentes:
            skipped += 1
        else:
            db.session.add(
                VirtualCampaignSlot(
                    campaign_id=campaign.id,
                    start_at=momento,
                    status=VIRTUAL_SLOT_STATUS_LIVRE,
                )
            )
            created += 1
        momento += timedelta(minutes=VIRTUAL_SLOT_MINUTES)

    if created:
        audit(
            "create", "VirtualCampaignSlot", campaign.id, campaign.title,
            f"{created} horário(s) gerado(s) em {target_day.isoformat()}",
        )
    db.session.commit()
    return {"created": created, "skipped": skipped}


def remover_slot(slot: VirtualCampaignSlot) -> None:
    """Remove um horário do estoque.

    Só horários realmente livres podem sair. Um horário reservado ou vendido tem uma família do
    outro lado — apagá-lo criaria uma venda sem hora marcada (FR-008).

    Raises:
        VirtuaisValidationError: O horário está travado ou vendido.
    """
    if slot.status != VIRTUAL_SLOT_STATUS_LIVRE or slot.order_id is not None:
        raise VirtuaisValidationError(
            "id",
            "Este horário já está reservado ou vendido e não pode ser removido. "
            "Pause a campanha se quiser parar de vender.",
        )
    slot_id, campaign_id = slot.id, slot.campaign_id
    db.session.delete(slot)
    audit(
        "delete", "VirtualCampaignSlot", slot_id, str(slot.start_at),
        f"Horário removido da campanha #{campaign_id}",
    )
    db.session.commit()


# Marca o `CalendarEvent` cujo lado Google nunca chegou a existir. A coluna `google_event_id` é
# NOT NULL e única, então a venda precisa de *algum* id para existir na Agenda com o Google fora.
# É por este prefixo que a varredura reconhece o que ainda falta criar lá (FR-057).
GOOGLE_ID_LOCAL_PREFIX = "virtual-local-"


# ── Política de retry (FR-056) ───────────────────────────────────────────────


class RetryEsgotado(Exception):
    """As 3 tentativas se esgotaram sem sucesso. A falha é definitiva (FR-056a)."""

    def __init__(self, message: str, *, ultima_falha: Exception | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.ultima_falha = ultima_falha


def deve_tentar_novamente(attempts: int, last_attempt_at: datetime | None) -> bool:
    """True se ainda cabe uma tentativa **agora**, segundo a política única da feature.

    A política é uma só para toda chamada externa que pode falhar por indisponibilidade
    (reconsulta de cobrança, e-mail, geração de sala): **3 tentativas nos minutos 0, 1 e 2**.

    Diferente de um laço com ``sleep``, esta função é consultada por quem persiste o contador —
    a varredura chama, decide e volta depois. Um laço bloqueante prenderia a thread da varredura e
    seguraria o horário de todo mundo enquanto a operadora estivesse lenta.

    Args:
        attempts: Quantas tentativas já foram feitas.
        last_attempt_at: Quando foi a última (``None`` = nunca tentou).

    Returns:
        True se cabe tentar agora; False se já bateu o teto ou o intervalo ainda não passou.
    """
    if attempts >= VIRTUAL_RETRY_MAX_ATTEMPTS:
        return False
    if last_attempt_at is None:
        return True
    proxima = last_attempt_at + timedelta(minutes=VIRTUAL_RETRY_INTERVAL_MIN)
    return agora() >= proxima


def retry_esgotou(attempts: int) -> bool:
    """True quando as tentativas acabaram e a falha virou definitiva (FR-056a)."""
    return attempts >= VIRTUAL_RETRY_MAX_ATTEMPTS


def executar_com_retry(
    operacao: Callable[[], Any], *, descricao: str, exception_types: tuple[type[Exception], ...]
) -> Any:
    """Executa ``operacao`` repetindo até 3 vezes, **sem espera entre as tentativas**.

    Usada nos caminhos síncronos (requisição do usuário), onde não dá para esperar minutos: aqui as
    3 tentativas acontecem em sequência imediata, para absorver uma falha transitória de rede sem
    segurar a página. Os caminhos assíncronos (varredura) usam ``deve_tentar_novamente``, que
    respeita o intervalo de 1 minuto.

    Raises:
        RetryEsgotado: As três tentativas falharam.
    """
    ultima: Exception | None = None
    for tentativa in range(1, VIRTUAL_RETRY_MAX_ATTEMPTS + 1):
        try:
            return operacao()
        except exception_types as exc:
            ultima = exc
            logger.warning(
                "[virtuais] %s falhou (tentativa %s/%s): %s",
                descricao, tentativa, VIRTUAL_RETRY_MAX_ATTEMPTS, exc,
            )
    raise RetryEsgotado(f"{descricao} falhou após {VIRTUAL_RETRY_MAX_ATTEMPTS} tentativas.",
                        ultima_falha=ultima)


# ── Reserva e soft lock (US2) ────────────────────────────────────────────────


def hash_origem(ip: str | None, user_agent: str | None) -> str:
    """Identidade da origem para o teto anti-abuso (FR-020b).

    Hash com sal de IP + User-Agent. **Nunca o IP cru** — guardar endereço de quem só olhou a
    landing seria coletar dado pessoal sem necessidade; para contar reservas numa janela, o hash
    basta. O User-Agent entra porque IP sozinho junde demais (uma operadora móvel inteira pode
    sair pelo mesmo NAT).

    Resistência a variação trivial: quem trocar de aba, limpar cookie ou abrir anônimo continua com
    o mesmo hash. Trocar de IP **e** de navegador ao mesmo tempo escapa — o teto é uma barreira
    contra script ingênuo, não contra adversário determinado.
    """
    sal = current_app.config.get("SECRET_KEY", "manto")
    base = f"{sal}|{(ip or '').strip()}|{(user_agent or '').strip()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _normalizar_telefone(raw: str) -> str:
    """Só os dígitos do telefone — é a chave do limite por contato (FR-020a)."""
    return re.sub(r"\D", "", raw or "")


def _gerar_order_nsu(campaign_id: int) -> str:
    """Identificador do pedido que viaja até a operadora e volta em todo aviso.

    Formato ``205-<campanha>-<aleatório>``: legível para quem for conferir no painel da InfinitePay
    e impossível de colidir. O aleatório existe porque o id sequencial ainda não existe no momento
    em que o pedido é criado — e porque um `order_nsu` adivinhável convidaria a sondagem.
    """
    return f"205-{campaign_id}-{secrets.token_hex(6)}"


def _vagas_de_video_livres(campaign: VirtualCampaign, momento: datetime | None = None) -> int:
    """Vagas de vídeo que ainda podem ser reservadas: capacidade − vendidos − reservas ativas."""
    momento = momento or agora()
    ativas = VirtualOrder.query.filter(
        VirtualOrder.campaign_id == campaign.id,
        VirtualOrder.modality == VIRTUAL_MODALITY_GRAVADO,
        VirtualOrder.status.in_(VIRTUAL_ORDER_STATUS_ATIVOS),
        VirtualOrder.locked_until > momento,
    ).count()
    return (campaign.recorded_capacity or 0) - (campaign.recorded_sold or 0) - ativas


def _limite_de_reserva(momento: datetime | None = None) -> datetime:
    """Primeiro instante em que um horário ainda pode ser reservado (feature 310, FR-006)."""
    return (momento or agora()) + timedelta(hours=VIRTUAL_ANTECEDENCIA_RESERVA_HORAS)


def listar_slots_disponiveis(campaign: VirtualCampaign, *, day: str | None = None) -> list:
    """Horários que a família pode reservar agora.

    Disponível = ``livre`` **ou** ``travado`` com ``locked_until`` vencido. A segunda condição é o
    que faz a expiração valer mesmo antes de a varredura rodar — quem abre a landing já vê o
    horário de volta.

    Horário no passado nunca entra, ainda que nunca tenha sido vendido. Desde a 310, também não
    entra o que começa em menos de ``VIRTUAL_ANTECEDENCIA_RESERVA_HORAS`` (2 h, decisão do dono):
    a equipe precisa ler as dicas e o artista se preparar.
    """
    momento = agora()
    query = VirtualCampaignSlot.query.filter(
        VirtualCampaignSlot.campaign_id == campaign.id,
        VirtualCampaignSlot.start_at > _limite_de_reserva(momento),
    ).order_by(VirtualCampaignSlot.start_at.asc())

    slots = [s for s in query.all() if s.is_available(momento)]
    if day:
        slots = [s for s in slots if s.start_at.date().isoformat() == day]
    return slots


def _validar_ficha(dados: dict[str, Any], *, exige_endereco: bool) -> dict[str, Any]:
    """Valida os campos da ficha da criança e devolve os valores limpos (FR-014).

    Cada erro aponta o campo culpado, para o React destacá-lo sem o usuário caçar o que faltou.
    """
    nome = (dados.get("child_name") or "").strip()
    if not nome:
        raise VirtuaisValidationError("child_name", "O nome da criança é obrigatório.")

    idade_raw = dados.get("child_age")
    try:
        idade = int(idade_raw)
    except (TypeError, ValueError):
        raise VirtuaisValidationError("child_age", "Informe a idade da criança.") from None
    if idade < 0 or idade > 120:
        raise VirtuaisValidationError("child_age", "Idade inválida.")

    telefone = _normalizar_telefone(dados.get("contact_phone", ""))
    if len(telefone) < 10:
        raise VirtuaisValidationError("contact_phone", "Informe um telefone com DDD.")

    email = (dados.get("contact_email") or "").strip()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise VirtuaisValidationError("contact_email", "Informe um e-mail válido.")

    endereco = (dados.get("delivery_address") or "").strip()
    if exige_endereco and not endereco:
        raise VirtuaisValidationError(
            "delivery_address", "O endereço de entrega é obrigatório quando há presente."
        )

    return {
        "child_name": nome[:120],
        "child_age": idade,
        "behavior_notes": (dados.get("behavior_notes") or "").strip() or None,
        "contact_phone": telefone[:20],
        "contact_phone_display": (dados.get("contact_phone") or "").strip()[:30] or None,
        "contact_email": email[:180],
        "delivery_address": endereco[:300] or None,
    }


def _checar_limites(campaign: VirtualCampaign, telefone: str, origem: str) -> None:
    """Aplica os dois tetos anti-abuso antes de travar qualquer horário (FR-020a–020c).

    Raises:
        VirtuaisLimiteError: Já existe reserva ativa com este telefone, ou a origem estourou o teto
            da janela configurada.
    """
    momento = agora()

    existente = (
        VirtualOrder.query.filter(
            VirtualOrder.contact_phone == telefone,
            VirtualOrder.status.in_(VIRTUAL_ORDER_STATUS_ATIVOS),
            VirtualOrder.locked_until > momento,
        )
        .order_by(VirtualOrder.created_at.desc())
        .first()
    )
    if existente is not None:
        raise VirtuaisLimiteError(
            "Você já tem uma reserva em andamento. Conclua o pagamento ou abandone-a para "
            "escolher outro horário.",
            existing_order_token=existente.public_token,
        )

    janela = momento - timedelta(minutes=campaign.reservation_window_minutes or 60)
    # Pedido que morreu porque a OPERADORA recusou o link não conta (feature 310, FR-026): a
    # família que tentou de novo não pode ser barrada por "muitas reservas" por culpa nossa.
    recentes = VirtualOrder.query.filter(
        VirtualOrder.origin_hash == origem,
        VirtualOrder.created_at >= janela,
        VirtualOrder.payment_link_error.is_(None),
    ).count()
    if recentes >= (campaign.max_reservations_per_origin or 5):
        audit(
            "edit", "VirtualCampaign", campaign.id, campaign.title,
            f"Reserva recusada por limite de origem ({recentes} na janela)",
        )
        db.session.commit()
        raise VirtuaisLimiteError(
            "Muitas reservas seguidas deste dispositivo. Aguarde alguns minutos e tente de novo, "
            "ou fale com a gente pelo WhatsApp."
        )


def _travar_slot(slot_id: int, campaign_id: int) -> VirtualCampaignSlot:
    """Trava a linha do horário no banco e confere que ele ainda está disponível.

    ``with_for_update()`` é o coração da corrida: dois visitantes que clicam no mesmo horário no
    mesmo instante entram em fila **no banco**; o segundo só continua depois que o primeiro
    comita, e aí encontra o slot ocupado. Sem isso, os dois leriam "livre" e os dois venderiam.

    Raises:
        VirtuaisConflitoError: O horário acabou de ser tomado.
    """
    slot = (
        db.session.query(VirtualCampaignSlot)
        .filter(
            VirtualCampaignSlot.id == slot_id,
            VirtualCampaignSlot.campaign_id == campaign_id,
        )
        .with_for_update()
        .first()
    )
    if slot is None:
        raise VirtuaisValidationError("slot_id", "Horário não encontrado nesta campanha.")
    if slot.start_at <= agora():
        raise VirtuaisConflitoError("Este horário já passou.")
    if slot.start_at <= _limite_de_reserva():
        raise VirtuaisConflitoError("Este horário fecha 2 horas antes. Escolha outro.")
    if not slot.is_available():
        raise VirtuaisConflitoError("Este horário acabou de ser reservado por outra pessoa.")
    return slot


def reservar(
    campaign: VirtualCampaign,
    *,
    modality: str,
    slot_id: Any = None,
    gift_item_id: Any = None,
    client_token: str | None = None,
    origin_ip: str | None = None,
    origin_user_agent: str | None = None,
    redirect_url_builder: Callable[[str], str] | None = None,
    **ficha: Any,
) -> VirtualOrder:
    """Cria o pedido, aplica o soft lock de 15 minutos e gera o link de pagamento.

    A ordem das etapas é deliberada: valida → confere limites → **trava o slot** → grava o pedido →
    só então fala com a operadora. Falar com a InfinitePay antes de travar deixaria a janela aberta
    para outro visitante levar o horário no meio da chamada HTTP.

    O soft lock conta a partir **deste instante** — o da criação da reserva, dentro da transação
    que trava o slot (FR-017).

    Args:
        campaign: A campanha publicada.
        modality: ``ao_vivo`` (consome horário) ou ``gravado`` (consome capacidade).
        slot_id: O horário escolhido; obrigatório em ``ao_vivo``.
        gift_item_id: Peça do Acervo liberada, quando houver presente.
        client_token: Token do navegador — torna o duplo clique inofensivo (FR-026).
        origin_ip / origin_user_agent: Insumos do hash de origem (nunca persistidos crus).
        redirect_url_builder: Recebe o ``public_token`` e devolve para onde a operadora manda a
            família de volta.

    Raises:
        VirtuaisValidationError: Campo inválido (400).
        VirtuaisConflitoError: Horário ou vaga tomada (409).
        VirtuaisLimiteError: Teto anti-abuso (429).
        VirtuaisOperadoraError: Falha ao gerar o link (502) — a reserva é desfeita.
    """
    if not campaign.is_public:
        raise VirtuaisConflitoError("Esta campanha não está aceitando reservas no momento.")
    # Feature 310 (R-18): com o pagamento desligado, nada é travado — a família não preenche a ficha
    # para descobrir no fim que não dá para pagar.
    if not _pagamento_ligado():
        raise VirtuaisPagamentoFechadoError("As reservas estão fechadas por enquanto.")

    modalidade = (modality or "").strip().lower()
    if modalidade not in VIRTUAL_MODALITIES:
        raise VirtuaisValidationError("modality", "Escolha entre chamada ao vivo ou vídeo gravado.")

    # Duplo clique: o mesmo token devolve o pedido que já existe em vez de travar um segundo
    # horário. É a primeira coisa checada, antes de qualquer efeito colateral (FR-026).
    if client_token:
        anterior = VirtualOrder.query.filter(
            VirtualOrder.campaign_id == campaign.id,
            VirtualOrder.client_token == client_token,
            VirtualOrder.status.in_(VIRTUAL_ORDER_STATUS_ATIVOS),
            VirtualOrder.locked_until > agora(),
        ).first()
        if anterior is not None:
            return anterior

    peca = None
    if gift_item_id:
        peca = Acervo3DItem.query.get(gift_item_id)
        liberadas = {item.id for item in campaign.acervo_items if item.is_active}
        if peca is None or peca.id not in liberadas:
            raise VirtuaisValidationError(
                "gift_item_id", "Este presente não está disponível nesta campanha."
            )

    dados = _validar_ficha(ficha, exige_endereco=peca is not None)
    origem = hash_origem(origin_ip, origin_user_agent)
    _checar_limites(campaign, dados["contact_phone"], origem)

    momento = agora()
    locked_until = momento + timedelta(minutes=VIRTUAL_SOFT_LOCK_MINUTES)

    slot = None
    if modalidade == VIRTUAL_MODALITY_AO_VIVO:
        if not slot_id:
            raise VirtuaisValidationError("slot_id", "Escolha um horário para a chamada.")
        slot = _travar_slot(int(slot_id), campaign.id)
        preco = campaign.price_live
    else:
        # Feature 310 (R-03): a reserva ativa de vídeo ocupa vaga enquanto a trava dela vale. Sem
        # isso, com 1 vaga sobrando, N famílias recebiam link ao mesmo tempo e todas que pagassem
        # viravam venda. A trava da campanha enfileira duas reservas simultâneas no banco.
        db.session.query(VirtualCampaign).filter(
            VirtualCampaign.id == campaign.id
        ).options(lazyload("*")).with_for_update().first()
        if _vagas_de_video_livres(campaign, momento) <= 0:
            raise VirtuaisConflitoError("Os vídeos gravados desta campanha esgotaram.")
        preco = campaign.price_recorded

    preco_presente = campaign.price_gift if peca is not None else Decimal("0.00")
    total = (Decimal(preco) + Decimal(preco_presente)).quantize(Decimal("0.01"))

    order = VirtualOrder(
        campaign_id=campaign.id,
        slot_id=slot.id if slot else None,
        modality=modalidade,
        status=VIRTUAL_ORDER_STATUS_RESERVADO,
        order_nsu=_gerar_order_nsu(campaign.id),
        public_token=secrets.token_urlsafe(32)[:43],
        gift_item_id=peca.id if peca else None,
        price_interaction=Decimal(preco),
        price_gift=Decimal(preco_presente),
        total_value=total,
        locked_until=locked_until,
        origin_hash=origem,
        client_token=(client_token or None),
        **dados,
    )
    db.session.add(order)
    db.session.flush()

    if slot is not None:
        slot.status = VIRTUAL_SLOT_STATUS_TRAVADO
        slot.locked_until = locked_until
        slot.order_id = order.id

    db.session.commit()

    # A operadora fica fora da transação: uma chamada HTTP lenta não pode segurar o lock do slot
    # no banco. Se ela falhar, desfazemos a reserva e devolvemos o horário ao estoque.
    try:
        _gerar_link_pagamento(order, redirect_url_builder)
    except (VirtuaisOperadoraError, VirtuaisPagamentoFechadoError):
        _liberar_reserva(order, motivo="falha ao gerar o link de pagamento")
        raise

    return order


def _pagamento_ligado() -> bool:
    """Tag, segredo e interruptor presentes (feature 310, R-18)."""
    settings = SiteSetting.query.get(1)
    return bool(
        settings
        and settings.infinitepay_handle
        and settings.infinitepay_webhook_token
        and getattr(settings, "virtuais_pagamento_ativo", False)
    )


def _ipc_cfg() -> dict[str, Any]:
    """Trava e chave da InfinitePay deste processo, lidas a cada chamada (feature 310, R5).

    Lidas aqui, na camada ``_ops``, e passadas ao cliente por parâmetro — o cliente não importa
    Flask. Chave de trava ausente = travado: quem esquecer não cobra ninguém por engano.
    """
    return {
        "travada": bool(current_app.config.get("INFINITEPAY_SUPPRESS_CALLS", True)),
        "api_key": current_app.config.get("INFINITEPAY_API_KEY") or None,
    }


def _gerar_link_pagamento(
    order: VirtualOrder, redirect_url_builder: Callable[[str], str] | None
) -> None:
    """Pede o link à InfinitePay e grava no pedido (FR-021).

    Passa o total em ``Decimal``: quem converte para centavos é o cliente da operadora, e só ele.

    Feature 310:
    - **interruptor** (R-18): desligado, não nasce link novo — avisos e reconsultas de pedidos já
      abertos seguem por outros caminhos;
    - **pacote** (R-15): nada da criança vai à operadora — descrição neutra com o código do
      pedido, comprador só com e-mail e telefone (o formato provado em produção, só dígitos);
    - **recusa** (FR-026): 4xx não é repetido (não muda na segunda vez), o código da operadora
      fica gravado no pedido e a equipe é avisada; só indisponibilidade é repetida.
    """
    from app.integracoes import infinitepay_client as ipc

    settings = SiteSetting.query.get(1)
    handle = (settings.infinitepay_handle or "") if settings else ""
    token = (settings.infinitepay_webhook_token or "") if settings else ""
    ativo = bool(getattr(settings, "virtuais_pagamento_ativo", False)) if settings else False
    if not handle or not token or not ativo:
        raise VirtuaisPagamentoFechadoError("As reservas estão fechadas por enquanto.")

    base_url = (current_app.config.get("PUBLIC_BASE_URL") or "").rstrip("/")
    redirect_url = (
        redirect_url_builder(order.public_token)
        if redirect_url_builder
        else f"{base_url}/catalogo/v/pedido/{order.public_token}"
    )
    webhook_url = f"{base_url}/api/webhooks/infinitepay/{token}"
    cfg = _ipc_cfg()
    valid_until = None
    if order.locked_until is not None:
        # Hora de parede de São Paulo → ISO com o fuso explícito, que é o que a API nova pede.
        valid_until = order.locked_until.replace(microsecond=0).isoformat() + "-03:00"

    try:
        resultado = executar_com_retry(
            lambda: ipc.criar_link_pagamento(
                handle=handle,
                order_nsu=order.order_nsu,
                total=Decimal(order.total_value),
                description=f"{order.campaign.title} — pedido {order.order_nsu}",
                redirect_url=redirect_url,
                webhook_url=webhook_url,
                customer={"email": order.contact_email, "phone_number": order.contact_phone},
                travada=cfg["travada"],
                api_key=cfg["api_key"],
                valid_until=valid_until,
            ),
            descricao="criar link de pagamento",
            exception_types=(ipc.InfinitePayIndisponivel,),
        )
    except ipc.InfinitePayRecusou as exc:
        codigo = (getattr(exc, "code", None) or str(exc) or "recusado")[:200]
        order.payment_link_error = codigo
        db.session.commit()
        _avisar_falha_de_link(order, codigo)
        raise VirtuaisOperadoraError(
            "Não conseguimos abrir o pagamento. A equipe já foi avisada; tente de novo mais tarde "
            "ou fale com a gente no WhatsApp."
        ) from exc
    except RetryEsgotado as exc:
        if isinstance(exc.ultima_falha, ipc.InfinitePayTravada):
            order.payment_link_error = "travado_neste_ambiente"
            db.session.commit()
            raise VirtuaisOperadoraError(
                "Pagamento travado neste ambiente (cópia de teste)."
            ) from exc
        raise VirtuaisOperadoraError(
            "Não conseguimos abrir o pagamento agora. Tente de novo em instantes."
        ) from exc

    order.payment_url = resultado["payment_url"]
    order.status = VIRTUAL_ORDER_STATUS_AGUARDANDO
    db.session.commit()


def _avisar_falha_de_link(order: VirtualOrder, codigo: str) -> None:
    """Sino para Comercial e Superadmin quando a operadora recusa o link (FR-026, R-19).

    Agrupa por código e hora: a mesma recusa (ex.: Checkout Integrado desligado) derruba toda
    reserva, e 50 avisos iguais ensinam a ignorar o sino.
    """
    try:
        from app.notificacoes import notificacoes_ops as nops

        emitir = getattr(nops, "notificar_virtual_atencao", None)
        if emitir is None:
            return
        emitir(
            titulo="Pagamento: a InfinitePay recusou abrir o link",
            corpo=f"Código: {codigo}. Pedido {order.order_nsu}.",
            dedupe_key=f"virtual.link:{codigo}:{agora():%Y%m%d%H}",
        )
    except Exception as exc:  # noqa: BLE001 — o aviso à equipe nunca derruba a resposta
        logger.warning("[virtuais] aviso de falha de link não saiu: %s", exc)


def _travar_pedido(order_id: int) -> VirtualOrder | None:
    """Trava a linha do pedido e devolve o estado ATUAL do banco (feature 310, R1).

    ``populate_existing`` é o ponto: sem ele, a sessão devolveria o objeto já carregado, com o
    status lido antes de outro worker mudá-lo — e a decisão sairia sobre leitura velha (foi assim
    que um pedido PAGO voltava a EXPIRADO). Ordem de travas da feature: pedido → horário → campanha.

    ``lazyload("*")``: o modelo carrega campanha e presente por JOIN externo, e o Postgres recusa
    ``FOR UPDATE`` sobre o lado opcional de um join.
    """
    return (
        db.session.query(VirtualOrder)
        .filter(VirtualOrder.id == order_id)
        .options(lazyload("*"))
        .populate_existing()
        .with_for_update()
        .first()
    )


def _travar_horario(slot_id: int) -> VirtualCampaignSlot | None:
    return (
        db.session.query(VirtualCampaignSlot)
        .filter(VirtualCampaignSlot.id == slot_id)
        .options(lazyload("*"))
        .populate_existing()
        .with_for_update()
        .first()
    )


def _liberar_reserva(
    order: VirtualOrder, *, motivo: str, unverified_reason: str | None = None
) -> bool:
    """Desfaz uma reserva ATIVA e devolve o horário ao estoque.

    Feature 310: trava o pedido antes do horário e relê o status. Só libera pedido ainda
    reservado/aguardando — um pedido que outra rotina acabou de efetivar ou cancelar fica como
    está. E nunca solta horário vendido, mesmo que o dono gravado coincida (defesa em
    profundidade contra venda de legado sem dono).

    Returns:
        True se liberou; False se o pedido já não estava ativo.
    """
    atual = _travar_pedido(order.id)
    if atual is None or atual.status not in VIRTUAL_ORDER_STATUS_ATIVOS:
        db.session.commit()
        return False
    slot = _travar_horario(atual.slot_id) if atual.slot_id else None
    if (
        slot is not None
        and slot.order_id == atual.id
        and slot.status != VIRTUAL_SLOT_STATUS_VENDIDO
    ):
        slot.status = VIRTUAL_SLOT_STATUS_LIVRE
        slot.locked_until = None
        slot.order_id = None
    atual.status = VIRTUAL_ORDER_STATUS_EXPIRADO
    atual.locked_until = None
    if unverified_reason:
        atual.expired_unverified = True
        atual.unverified_reason = unverified_reason
    logger.info("[virtuais] reserva %s liberada: %s", atual.order_nsu, motivo)
    db.session.commit()
    return True


def claim_sweep(interval_seconds: int) -> bool:
    """Reivindica o ciclo da varredura de forma atômica (FR-057a).

    ``UPDATE`` condicional em ``site_settings``: só ganha o ciclo quem encontrar
    ``virtual_sweep_at`` nulo ou mais velho que o intervalo. Como o ``UPDATE`` é atômico no banco,
    apenas um processo ganha — mesmo com vários workers do gunicorn.

    Sem isso, dois processos expirariam a mesma reserva ao mesmo tempo: os dois leriam o pedido
    vencido, os dois liberariam o slot e um poderia desfazer a decisão do outro. É a mesma corrida
    que o soft lock existe para evitar, só que do lado de dentro.

    Returns:
        True se este processo deve rodar o ciclo agora.
    """
    from sqlalchemy import text

    momento = agora()
    limite = momento - timedelta(seconds=interval_seconds)
    resultado = db.session.execute(
        text(
            "UPDATE site_settings SET virtual_sweep_at = :now "
            "WHERE id = 1 AND (virtual_sweep_at IS NULL OR virtual_sweep_at < :limite)"
        ),
        {"now": momento, "limite": limite},
    )
    db.session.commit()
    return resultado.rowcount > 0


def ciclo_de_varredura() -> dict[str, Any]:
    """Roda as três rotinas periódicas da feature num ciclo só (FR-057).

    O requisito nomeia três: expiração de reservas, retentativas pendentes e alerta de prazo de
    vídeo. Ficam juntas porque compartilham o mesmo lock de execução única (``claim_sweep``) —
    três threads separadas exigiriam três locks e triplicariam a chance de duas instâncias
    pisarem uma na outra.

    **Cada rotina é isolada da seguinte.** Uma exceção na expiração não pode impedir o alerta de
    prazo de rodar (FR-057b): são responsabilidades independentes, e acoplá-las faria uma falha
    numa esconder as outras duas.

    Returns:
        Resumo por rotina, para o log do ciclo.
    """
    resumo: dict[str, Any] = {}
    rotinas: list[tuple[str, Callable[[], Any]]] = [
        ("reservas", expirar_reservas),
        ("avisos", reprocessar_avisos),
        ("salas", retentar_salas),
        ("prazos", alertar_prazos_video),
    ]
    for nome, rotina in rotinas:
        try:
            resumo[nome] = rotina()
        except Exception as exc:  # noqa: BLE001 — uma rotina caída não derruba as outras
            db.session.rollback()
            logger.warning("[virtuais] rotina '%s' falhou no ciclo: %s", nome, exc)
            resumo[nome] = {"erro": str(exc)[:200]}
    return resumo


def _identificadores_conhecidos(order: VirtualOrder) -> dict[str, str | None]:
    """Identificadores da cobrança para reconsultar (feature 310, R-09).

    Os do pedido (gravados só depois de provados) ou, na falta, os do aviso mais recente com o
    token certo para o mesmo ``order_nsu`` — um aviso que chegou mas ainda não decidiu.
    """
    if order.transaction_nsu and order.invoice_slug:
        return {"transaction_nsu": order.transaction_nsu, "invoice_slug": order.invoice_slug}
    aviso = (
        VirtualPaymentNotification.query.filter(
            VirtualPaymentNotification.order_nsu == order.order_nsu,
            VirtualPaymentNotification.secret_ok.is_(True),
            VirtualPaymentNotification.transaction_nsu.isnot(None),
        )
        .order_by(VirtualPaymentNotification.id.desc())
        .first()
    )
    if aviso is None:
        return {"transaction_nsu": None, "invoice_slug": None}
    try:
        corpo = json.loads(aviso.raw_payload or "{}")
    except ValueError:
        corpo = {}
    return {"transaction_nsu": aviso.transaction_nsu, "invoice_slug": corpo.get("invoice_slug")}


def _reconsultar(order_nsu: str, ids: dict[str, str | None]) -> dict:
    """Reconsulta na operadora com a config do processo. "Não sei" sobe como exceção."""
    from app.integracoes import infinitepay_client as ipc

    settings = SiteSetting.query.get(1)
    handle = (settings.infinitepay_handle or "") if settings else ""
    if not handle:
        raise ipc.InfinitePayIndisponivel("Operadora não configurada.")
    cfg = _ipc_cfg()
    consulta = ipc.consultar_pagamento(
        handle=handle,
        order_nsu=order_nsu,
        transaction_nsu=ids.get("transaction_nsu"),
        slug=ids.get("invoice_slug"),
        travada=cfg["travada"],
        api_key=cfg["api_key"],
    )
    # Dublês antigos (verify_205) não trazem `resultado`; deriva do `paid`.
    consulta.setdefault("resultado", "pago" if consulta.get("paid") else "nao_pago")
    return consulta


def expirar_reservas(*, limite: int = 100) -> dict[str, int]:
    """Devolve ao estoque os horários de reservas vencidas (FR-018, FR-041a; 310 R4, R-09).

    **Antes de liberar, reconsulta a cobrança na operadora** — se a família pagou no último
    segundo, a decisão vai para ``decidir_pagamento``, a mesma regra do aviso (feature 310). A
    varredura não efetiva mais nada sozinha: era aí que nascia a venda dupla.

    Semântica da reconsulta (teste 0 em produção, 20/10/2026):
    - sem identificadores e ``nao_encontrado`` = família abandonou o checkout → libera na primeira
      consulta, sem gastar as 3 tentativas e sem ir para "a conferir";
    - ``nao_pago`` → libera;
    - "não sei" (operadora fora, travada) → retém de fato (o horário continua travado) por 3
      tentativas; esgotou → libera com ``unverified_reason='nao_sei'`` ("a conferir");
    - pago → ``decidir_pagamento``; pago com valor errado → libera com ``divergente``.

    Cada pedido é isolado: um erro num pedido não aborta o lote nem gasta a tentativa dos outros.

    Returns:
        ``{"liberadas": int, "retidas": int, "pagas": int}``.
    """
    momento = agora()
    ids_vencidas = [
        o.id
        for o in VirtualOrder.query.filter(
            VirtualOrder.status.in_(VIRTUAL_ORDER_STATUS_ATIVOS),
            VirtualOrder.locked_until.isnot(None),
            VirtualOrder.locked_until <= momento,
        )
        .order_by(VirtualOrder.locked_until.asc())
        .limit(limite)
        .all()
    ]

    resultado = {"liberadas": 0, "retidas": 0, "pagas": 0}
    for order_id in ids_vencidas:
        try:
            desfecho = _expirar_um(order_id)
        except Exception as exc:  # noqa: BLE001 — um pedido problemático não trava o lote
            db.session.rollback()
            logger.warning("[virtuais] varredura do pedido %s falhou: %s", order_id, exc)
            desfecho = "retidas"
        if desfecho:
            resultado[desfecho] += 1
    return resultado


def _expirar_um(order_id: int) -> str | None:
    from app.integracoes import infinitepay_client as ipc

    order = db.session.get(VirtualOrder, order_id)
    if order is None or order.status not in VIRTUAL_ORDER_STATUS_ATIVOS:
        return None
    if order.locked_until and order.locked_until > agora():
        return None

    if not order.payment_url:
        # Sem link não há o que reconsultar (a criação falhou ou nunca aconteceu).
        _liberar_reserva(order, motivo="lock vencido, sem cobrança para reconsultar")
        return "liberadas"

    if not deve_tentar_novamente(order.recheck_attempts, order.grace_until):
        if retry_esgotou(order.recheck_attempts):
            _liberar_reserva(
                order, motivo="tolerância esgotada sem resposta da operadora",
                unverified_reason="nao_sei",
            )
            return "liberadas"
        _reter_horario(order)
        return "retidas"

    order.recheck_attempts += 1
    order.grace_until = agora()
    db.session.commit()

    ids = _identificadores_conhecidos(order)
    try:
        consulta = _reconsultar(order.order_nsu, ids)
    except (ipc.InfinitePayIndisponivel, ipc.InfinitePayRecusou) as exc:
        logger.warning("[virtuais] reconsulta de %s sem resposta: %s", order.order_nsu, exc)
        _reter_horario(order)
        return "retidas"

    if consulta["resultado"] == "pago":
        desfecho = decidir_pagamento(
            order.id, consulta, identificadores=ids, origem="varredura"
        )
        if desfecho == VIRTUAL_AVISO_DIVERGENTE:
            _liberar_reserva(order, motivo="pago com valor divergente",
                             unverified_reason="divergente")
            return "liberadas"
        return "pagas"

    _liberar_reserva(order, motivo=f"lock vencido; reconsulta: {consulta['resultado']}")
    return "liberadas"


def _reter_horario(order: VirtualOrder) -> None:
    """Retém DE FATO o horário enquanto a reconsulta não responde (feature 310, FR-004).

    Antes, "reter" só mexia no contador do pedido: o horário com a trava vencida voltava à vitrine
    e outra família o reservava no meio das tentativas.
    """
    if not order.slot_id:
        return
    slot = _travar_horario(order.slot_id)
    if slot is not None and slot.order_id == order.id and slot.status == VIRTUAL_SLOT_STATUS_TRAVADO:
        slot.locked_until = agora() + timedelta(minutes=VIRTUAL_RETRY_INTERVAL_MIN + 1)
    db.session.commit()


# ── Efetivação: a venda vira operação (US3) ──────────────────────────────────


def extrair_meet_url(evento_google: dict) -> str | None:
    """Extrai o link da **sala** do payload do Google Calendar.

    Procura em ``hangoutLink`` e, como alternativa, no ``entryPoint`` de vídeo dentro de
    ``conferenceData`` — a API preenche um ou outro conforme o caminho de criação.

    Devolve ``None`` quando a sala ainda está sendo criada
    (``createRequest.status.statusCode == "pending"``): é assíncrono do lado do Google, e tratar
    isso como "deu certo" entregaria à família um link vazio.

    **Não confundir com ``CalendarEvent.google_html_link``**, que é o link do *evento* no Google
    Calendar e exige login no calendário — inútil para a compradora.
    """
    if not isinstance(evento_google, dict):
        return None
    direto = evento_google.get("hangoutLink")
    if direto:
        return direto
    conferencia = evento_google.get("conferenceData") or {}
    for ponto in conferencia.get("entryPoints") or []:
        if ponto.get("entryPointType") == "video" and ponto.get("uri"):
            return ponto["uri"]
    return None


def _criar_evento_google(order: VirtualOrder) -> tuple[str, str | None, str | None]:
    """Cria o evento na agenda externa com sala do Meet.

    Returns:
        ``(google_event_id, google_html_link, meet_url)``. ``meet_url`` vem ``None`` quando a sala
        ficou pendente do lado do Google — a venda segue válida e a pendência é sinalizada.

    Raises:
        RuntimeError: Google não conectado ou falha na criação (quem chama decide o que fazer).
    """
    from app.calendar.routes import CALENDAR_ID
    from app.calendar.service import insert_event

    # Feature 310 (constituição XIV): a cópia local traz o token real do Google — sem esta trava,
    # uma venda de teste criava evento e sala na agenda da empresa. Chave ausente = travado.
    if current_app.config.get("CALENDAR_SUPPRESS_EVENT_WRITES", True):
        raise RuntimeError("Escrita na agenda travada neste ambiente (cópia de teste).")

    campanha = order.campaign
    inicio = order.slot.start_at if order.slot else agora()
    fim = inicio + timedelta(minutes=VIRTUAL_SLOT_MINUTES)
    personagem = campanha.character.name if campanha.character else campanha.title

    titulo = f"🎥 VIRTUAL — {personagem} para {order.child_name}"
    descricao = (
        f"Interação virtual vendida pela loja (pedido {order.order_nsu}).\n"
        f"Criança: {order.child_name}, {order.child_age} anos.\n"
        f"Contato: {order.contact_phone_display or order.contact_phone} · {order.contact_email}\n"
    )
    if order.behavior_notes:
        descricao += f"Dicas da família: {order.behavior_notes}\n"

    # Sala só faz sentido na chamada ao vivo. Pedir uma para vídeo gravado criaria um link que
    # ninguém usa — e apareceria para a família como "entrar na chamada" num produto que não tem
    # chamada nenhuma.
    ao_vivo = order.modality == VIRTUAL_MODALITY_AO_VIVO

    # A geração da sala está nomeada na política de retry (FR-056). Aqui as 3 tentativas são
    # imediatas, não espaçadas: este é o caminho síncrono do webhook, e esperar 2 minutos seguraria
    # a resposta à operadora. O objetivo desta camada é absorver o soluço de rede — a queda longa
    # do Google é problema da varredura, que retenta com o intervalo de 1 minuto e progresso em
    # banco (`_retentar_salas`).
    resultado = executar_com_retry(
        lambda: insert_event(
            CALENDAR_ID,
            titulo,
            inicio,
            fim,
            description=descricao,
            conference_request_id=f"virtual-{order.order_nsu}" if ao_vivo else None,
        ),
        descricao=f"criar evento no Google do pedido {order.order_nsu}",
        exception_types=(Exception,),
    )
    meet = extrair_meet_url(resultado) if ao_vivo else None
    return resultado.get("id"), resultado.get("htmlLink"), meet


def _pre_escalar(event: CalendarEvent, campanha: VirtualCampaign) -> None:
    """Coloca o talento e o figurino do personagem no evento (FR-031).

    Idempotente: se o cargo já existe, não duplica — a efetivação pode ser reexecutada depois de
    uma falha parcial.
    """
    personagem = campanha.character.name if campanha.character else campanha.title
    ja_existe = EventRole.query.filter_by(
        event_id=event.id, character_name=personagem
    ).first()
    if ja_existe is not None:
        return
    db.session.add(
        EventRole(
            event_id=event.id,
            character_name=personagem,
            role_type="character",
            talent_id=campanha.talent_id,
            figurino_sheet_id=campanha.figurino_sheet_id,
            assigned_at=agora() if campanha.talent_id else None,
        )
    )


def efetivar_pedido(order: VirtualOrder, *, consulta: dict | None = None) -> VirtualOrder:
    """Converte uma reserva paga em operação (FR-029 a FR-033).

    Feature 310: só ``decidir_pagamento`` chama isto, com o pedido e o horário já travados e todas
    as condições conferidas. A venda nasce **no banco primeiro** — pedido pago, horário vendido
    com dono, evento com id local e sala pendente, entrega, presente — num commit só; o Google e o
    e-mail vêm depois, fora das travas (``_pos_venda``). Assim uma disputa é decidida no banco
    antes de qualquer chamada externa, e o perdedor não deixa evento órfão na agenda do Google.

    Idempotente: pedido já ``pago`` com evento vinculado é devolvido como está.
    """
    if order.status == VIRTUAL_ORDER_STATUS_PAGO and order.event_id:
        return order
    _efetivar_no_banco(order)
    _pos_venda(order)
    return order


def _efetivar_no_banco(order: VirtualOrder) -> None:
    campanha = order.campaign
    inicio = order.slot.start_at if order.slot else agora()
    evento = CalendarEvent(
        # Id local marcado: a linha precisa de um id único já; o verdadeiro vem do Google em
        # `_pos_venda` (mesmo caminho do `regerar_sala`). A sincronização ignora eventos virtuais.
        google_event_id=f"{GOOGLE_ID_LOCAL_PREFIX}{order.order_nsu}",
        google_html_link=None,
        title=f"🎥 VIRTUAL — {order.child_name}",
        description=(order.behavior_notes or None),
        start_at=inicio,
        end_at=inicio + timedelta(minutes=VIRTUAL_SLOT_MINUTES),
        event_type=EVENT_TYPE_VIRTUAL,
        source="platform",
        sale_value=Decimal(order.total_value),
        sale_date=inicio.date(),
    )
    db.session.add(evento)
    db.session.flush()

    _pre_escalar(evento, campanha)

    order.event_id = evento.id
    order.status = VIRTUAL_ORDER_STATUS_PAGO
    order.paid_at = agora()
    order.locked_until = None
    # Toda venda nasce com o lado Google pendente; vídeo gravado não tem sala, então a pendência
    # de SALA só existe na chamada ao vivo (o id local é reconciliado pela varredura em ambos).
    order.meet_pending = order.modality == VIRTUAL_MODALITY_AO_VIVO

    if order.slot is not None:
        order.slot.status = VIRTUAL_SLOT_STATUS_VENDIDO
        order.slot.locked_until = None
        # A 205 não gravava o dono do horário vendido: era assim que dois pagamentos atrasados
        # viravam duas vendas do mesmo horário (feature 310, invariante 2).
        order.slot.order_id = order.id

    if order.modality == VIRTUAL_MODALITY_GRAVADO:
        campanha.recorded_sold = (campanha.recorded_sold or 0) + 1

    prazo = None
    if order.modality == VIRTUAL_MODALITY_GRAVADO:
        prazo = (agora() + timedelta(days=campanha.recorded_delivery_days or 7)).date()
    db.session.add(
        VirtualMediaDelivery(
            order_id=order.id,
            status=VIRTUAL_PRODUCTION_STATUS_PENDENTE,
            due_date=prazo,
        )
    )

    if order.gift_item_id:
        _injetar_presente_3d(order, evento)

    audit(
        "create", "CalendarEvent", evento.id, evento.title,
        f"Venda virtual efetivada (pedido {order.order_nsu})",
    )
    db.session.commit()


def _pos_venda(order: VirtualOrder) -> None:
    """Lado de fora da venda: evento e sala no Google, depois o e-mail de compra.

    Falha do Google não desfaz nada: o pedido fica com ``meet_pending`` e a varredura de salas
    retenta até o horário (R11). O e-mail tem a trava de um por pedido e tipo.
    """
    try:
        regerar_sala(order)
    except Exception as exc:  # noqa: BLE001 — a venda já existe; a sala é retentada depois
        db.session.rollback()
        logger.warning("[virtuais] Google na venda %s falhou: %s", order.order_nsu, exc)
        atual = db.session.get(VirtualOrder, order.id)
        atual.meet_attempts = (atual.meet_attempts or 0) + 1
        atual.meet_last_attempt_at = agora()
        atual.meet_pending = atual.modality == VIRTUAL_MODALITY_AO_VIVO
        db.session.commit()
    _enviar_aviso(order, VIRTUAL_NOTIFICATION_KIND_COMPRA)


def _injetar_presente_3d(order: VirtualOrder, evento: CalendarEvent) -> None:
    """Cria a pendência na Fila de Impressão 3D existente (FR-032).

    Reusa `impressoes3d_ops.add_event_gift` — o presente da loja entra na **mesma** fila que a
    equipe já opera, não numa segunda paralela (Princípio I).
    """
    from app.impressoes3d import impressoes3d_ops as ops3d

    try:
        ops3d.add_event_gift(
            evento,
            item_id=order.gift_item_id,
            quantity=1,
            deadline_date=evento.start_at.date() if evento.start_at else None,
            notes=f"Presente da loja virtual · pedido {order.order_nsu} · entrega: "
                  f"{order.delivery_address or 'combinar'}",
        )
    except ops3d.Impressao3DValidationError as exc:
        # Peça inativada entre a compra e a efetivação: a venda vale, a pendência é sinalizada.
        logger.warning(
            "[virtuais] presente 3D do pedido %s não pôde entrar na fila: %s",
            order.order_nsu, exc.message,
        )


def _abrir_devolucao(
    order: VirtualOrder,
    *,
    consulta: dict | None = None,
    motivo: str | None = None,
    identificadores: dict | None = None,
) -> None:
    """Cancela o pedido e abre a devolução para a equipe executar (FR-042, FR-043).

    Nenhum evento, escala ou pendência de impressão é criado. A InfinitePay não publica API de
    estorno: o sistema garante o rastro e a cobrança; quem devolve é uma pessoa, no app.

    Feature 310: ``motivo`` explícito (horário passou, sem vaga de vídeo…); sem ele, vale a regra
    da 205 (conflito, ou conflito sem confirmação se o pedido foi liberado sem prova).
    """
    valor = Decimal(order.total_value)
    if consulta and consulta.get("paid_amount") is not None:
        valor = Decimal(consulta["paid_amount"])
    if motivo is None:
        motivo = (
            VIRTUAL_REFUND_REASON_SEM_CONFIRMACAO
            if order.expired_unverified
            else VIRTUAL_REFUND_REASON_CONFLITO
        )
    ids = identificadores or {}
    db.session.add(
        VirtualRefundRequest(
            order_id=order.id,
            amount=valor,
            reason=motivo,
            status=VIRTUAL_REFUND_STATUS_PENDENTE,
            invoice_slug=ids.get("invoice_slug") or order.invoice_slug,
            transaction_nsu=ids.get("transaction_nsu") or order.transaction_nsu,
        )
    )
    order.status = VIRTUAL_ORDER_STATUS_CANCELADO
    order.locked_until = None
    audit(
        "edit", "VirtualOrder", order.id, order.order_nsu,
        f"Pagamento não pôde virar venda ({motivo}) — devolução aberta",
    )
    db.session.commit()
    _avisar_equipe_devolucao(order, motivo)
    _enviar_aviso(order, VIRTUAL_NOTIFICATION_KIND_CANCELAMENTO)


def _abrir_devolucao_de_cobranca(
    order: VirtualOrder, *, consulta: dict, identificadores: dict, motivo: str
) -> None:
    """Devolve uma cobrança A MAIS, sem mexer no pedido (feature 310, FR-014).

    Pagamento em dobro de um pedido pago, ou pagamento de um pedido já cancelado: o pedido fica
    como está, e a cobrança nova vira devolução pendente com o valor que a operadora confirmou.
    """
    valor = Decimal(consulta.get("paid_amount") or order.total_value)
    db.session.add(
        VirtualRefundRequest(
            order_id=order.id,
            amount=valor,
            reason=motivo,
            status=VIRTUAL_REFUND_STATUS_PENDENTE,
            invoice_slug=identificadores.get("invoice_slug"),
            transaction_nsu=identificadores.get("transaction_nsu"),
        )
    )
    audit(
        "edit", "VirtualOrder", order.id, order.order_nsu,
        f"Cobrança a mais ({motivo}) — devolução aberta",
    )
    db.session.commit()
    _avisar_equipe_devolucao(order, motivo)


def _avisar_equipe_devolucao(order: VirtualOrder, motivo: str) -> None:
    """Sino para Comercial e Superadmin: devolução nova é dinheiro a devolver (FR-032)."""
    try:
        from app.notificacoes import notificacoes_ops as nops

        emitir = getattr(nops, "notificar_virtual_atencao", None)
        if emitir is None:
            return
        rotulo = VIRTUAL_REFUND_REASON_LABELS.get(motivo, motivo)
        emitir(
            titulo="Loja virtual: devolução a fazer no app da InfinitePay",
            corpo=f"{rotulo}. Pedido {order.order_nsu}.",
            dedupe_key=f"virtual.devolucao:{order.id}:{motivo}",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[virtuais] aviso de devolução não saiu: %s", exc)


def _pagamento_confere(order: VirtualOrder, consulta: dict) -> bool:
    """Pago, com valor pago informado e não menor que o total (feature 310, R-02).

    Nunca ``paid_amount or amount``: um ``paid_amount`` zero cairia no valor nominal do link e
    passaria. Sobrepagamento (cartão com juros repassados) confere.
    """
    if not consulta.get("paid"):
        return False
    pago = consulta.get("paid_amount")
    if pago is None:
        return False
    return Decimal(pago) >= Decimal(order.total_value)


def decidir_pagamento(
    order_id: int,
    consulta: dict,
    *,
    identificadores: dict | None = None,
    origem: str = "aviso",
) -> str:
    """A ÚNICA regra que transforma um pagamento provado em venda ou devolução (feature 310, R-01).

    Chamada pelo aviso, pelo retorno do checkout e pela varredura. A ``consulta`` é a reconsulta
    na operadora feita ANTES, fora de qualquer trava (HTTP nunca segura linha do banco); aqui só
    se decide, com o pedido travado e relido:

    1. estado do pedido — pago com a mesma cobrança = duplicado; pago com outra cobrança =
       devolução ``pagamento_em_dobro``; cancelado = devolução ``pagamento_sem_pedido_ativo``;
    2. valor (``_pagamento_confere``) — não confere = ``divergente`` (sem venda e sem devolução
       automática: entra em "a conferir");
    3. dono do horário — tomado por outro pedido, travado ou vendido = devolução de conflito;
    4. folga — o horário começa em menos de 30 min = devolução ``horario_passou``;
    5. vaga de vídeo — esgotada = devolução ``sem_vaga_de_video``;
    6. senão, efetiva: banco primeiro, Google e e-mail depois.

    Returns:
        O desfecho (constante ``VIRTUAL_AVISO_*``).
    """
    ids = {k: v for k, v in (identificadores or {}).items() if v}
    if not consulta.get("paid"):
        db.session.rollback()
        return VIRTUAL_AVISO_PENDENTE_PROVA

    order = _travar_pedido(order_id)
    if order is None:
        db.session.rollback()
        return VIRTUAL_AVISO_ORFAO
    tx = ids.get("transaction_nsu")

    if order.status == VIRTUAL_ORDER_STATUS_PAGO:
        if not tx or tx == order.transaction_nsu or _cobranca_ja_devolvida(order, tx):
            db.session.commit()
            return VIRTUAL_AVISO_DUPLICADO
        _abrir_devolucao_de_cobranca(
            order, consulta=consulta, identificadores=ids,
            motivo=VIRTUAL_REFUND_REASON_PAGAMENTO_EM_DOBRO,
        )
        return VIRTUAL_AVISO_DEVOLUCAO

    if order.status == VIRTUAL_ORDER_STATUS_CANCELADO:
        if not tx or tx == order.transaction_nsu or _cobranca_ja_devolvida(order, tx):
            db.session.commit()
            return VIRTUAL_AVISO_DUPLICADO
        _abrir_devolucao_de_cobranca(
            order, consulta=consulta, identificadores=ids,
            motivo=VIRTUAL_REFUND_REASON_SEM_PEDIDO_ATIVO,
        )
        return VIRTUAL_AVISO_DEVOLUCAO

    if not _pagamento_confere(order, consulta):
        db.session.commit()
        logger.warning(
            "[virtuais] pagamento divergente no pedido %s (%s): operadora %s, pedido %s",
            order.order_nsu, origem, consulta.get("paid_amount"), order.total_value,
        )
        return VIRTUAL_AVISO_DIVERGENTE

    # Provado: agora os identificadores podem ir para o pedido (FR-017).
    if tx:
        order.transaction_nsu = tx
    if ids.get("invoice_slug"):
        order.invoice_slug = ids["invoice_slug"]
    if ids.get("receipt_url"):
        order.receipt_url = ids["receipt_url"][:500]

    motivo = None
    tomado = False
    if order.slot_id is not None:
        slot = _travar_horario(order.slot_id)
        tomado = (
            slot is None
            or (slot.order_id is not None and slot.order_id != order.id)
            or (slot.status == VIRTUAL_SLOT_STATUS_VENDIDO and slot.order_id != order.id)
        )
        if not tomado and slot.start_at <= agora() + timedelta(
            minutes=VIRTUAL_MIN_MINUTOS_NO_PAGAMENTO
        ):
            motivo = VIRTUAL_REFUND_REASON_HORARIO_PASSOU
    elif order.modality == VIRTUAL_MODALITY_GRAVADO:
        campanha = (
            db.session.query(VirtualCampaign)
            .filter(VirtualCampaign.id == order.campaign_id)
            .options(lazyload("*"))
            .populate_existing()
            .with_for_update()
            .first()
        )
        if (campanha.recorded_sold or 0) >= (campanha.recorded_capacity or 0):
            motivo = VIRTUAL_REFUND_REASON_SEM_VAGA_VIDEO

    if tomado or motivo:
        _abrir_devolucao(order, consulta=consulta, motivo=motivo, identificadores=ids)
        logger.info("[virtuais] pedido %s (%s): devolução %s", order.order_nsu, origem,
                    motivo or "conflito")
        return VIRTUAL_AVISO_CONFLITO if tomado else VIRTUAL_AVISO_DEVOLUCAO

    _efetivar_no_banco(order)
    logger.info("[virtuais] pedido %s efetivado (origem=%s)", order.order_nsu, origem)
    _pos_venda(order)
    return VIRTUAL_AVISO_EFETIVADO


def _cobranca_ja_devolvida(order: VirtualOrder, tx: str) -> bool:
    return (
        VirtualRefundRequest.query.filter_by(order_id=order.id, transaction_nsu=tx).first()
        is not None
    )


def _enviar_aviso(order: VirtualOrder, kind: str) -> None:
    """Dispara um aviso à família **no máximo uma vez por pedido e tipo** (FR-028a, FR-028b).

    A trava é o banco, não a confiança no fluxo: gravamos `VirtualOrderNotification` **antes** de
    disparar e deixamos a restrição `UNIQUE(order_id, kind)` decidir. Se outra execução já gravou
    — reentrega do webhook, retentativa da varredura —, a inserção falha e nada é enviado.

    Falha de envio é registrada e sinalizada, mas nunca invalida a venda (FR-039c).
    """
    registro = VirtualOrderNotification(order_id=order.id, kind=kind)
    db.session.add(registro)
    try:
        db.session.commit()
    except IntegrityError:
        # Já avisado — a reentrega do aviso de pagamento não pode gerar um segundo e-mail.
        db.session.rollback()
        return

    enviar = _enviadores_de_aviso().get(kind)
    if enviar is None:
        return

    _entregar_aviso(registro, enviar)


def _enviadores_de_aviso() -> dict[str, Callable[[Any], bool]]:
    """Mapa `kind` → função de envio. Fonte única do disparo automático e do reenvio manual.

    **Precisa cobrir todo `VIRTUAL_NOTIFICATION_KINDS`.** Um tipo ausente aqui não estoura: o aviso
    grava a linha (a trava de idempotência), não acha o enviador e volta calado — a família nunca
    recebe e o sistema acha que avisou. Foi exatamente o que aconteceu com ``video_pronto``, e o
    teste não pegou porque contava a linha, não a entrega. V5.11b passou a travar isso.
    """
    from app.email_service import (
        send_virtual_order_cancelled_email,
        send_virtual_order_confirmed_email,
        send_virtual_video_ready_email,
    )

    return {
        VIRTUAL_NOTIFICATION_KIND_COMPRA: send_virtual_order_confirmed_email,
        VIRTUAL_NOTIFICATION_KIND_VIDEO: send_virtual_video_ready_email,
        VIRTUAL_NOTIFICATION_KIND_CANCELAMENTO: send_virtual_order_cancelled_email,
    }


def _entregar_aviso(registro: VirtualOrderNotification, enviar: Callable[[Any], bool]) -> bool:
    """Entrega um aviso já registrado, com a política de retry da feature (FR-056).

    Separado de :func:`_enviar_aviso` de propósito: a **trava** é do aviso (uma linha por pedido e
    tipo) e o **retry** é da entrega dela. Com os dois no mesmo lugar, qualquer tentativa de
    reenviar acabaria tentando gravar a linha de novo e esbarrando na própria trava.

    As 3 tentativas são imediatas — o caminho é síncrono (webhook ou varredura), e o servidor de
    e-mail que falha por soluço costuma responder na sequência. Esgotadas, a falha fica gravada em
    ``sent_ok``/``error_message`` e passa a aparecer no painel (FR-039c, FR-056a); ela **nunca**
    invalida a venda.

    Returns:
        True se o aviso saiu.
    """
    registro.attempts = (registro.attempts or 0) + 1
    registro.last_attempt_at = agora()
    order = registro.order

    def _tentar() -> bool:
        # `email_service._send` engole a exceção do SMTP e devolve `False` — é o contrato do resto
        # do sistema e não vamos mudá-lo. Mas isso significa que a falha mais comum (servidor de
        # e-mail fora) chegaria aqui como retorno falso, **sem exceção**, e o retry nunca
        # dispararia. Converter o `False` em exceção é o que faz a política valer para o caso real.
        if not enviar(order):
            raise RuntimeError("O serviço de e-mail recusou o envio.")
        return True

    try:
        registro.sent_ok = bool(
            executar_com_retry(
                _tentar,
                descricao=f"aviso {registro.kind} do pedido {order.order_nsu}",
                exception_types=(Exception,),
            )
        )
        registro.error_message = None
    except RetryEsgotado as exc:
        registro.sent_ok = False
        registro.error_message = str(exc.ultima_falha or exc)[:500]
        logger.warning(
            "[virtuais] falha ao avisar pedido %s (%s): %s",
            order.order_nsu, registro.kind, registro.error_message,
        )
    except Exception as exc:  # noqa: BLE001 — e-mail nunca derruba a venda
        registro.sent_ok = False
        registro.error_message = str(exc)[:500]
        logger.warning(
            "[virtuais] falha ao avisar pedido %s (%s): %s", order.order_nsu, registro.kind, exc
        )
    db.session.commit()
    return bool(registro.sent_ok)


def reenviar_aviso(order: VirtualOrder, kind: str) -> VirtualOrderNotification:
    """Reenvia um aviso que falhou, por ação deliberada da equipe (FR-039c).

    Só age sobre aviso **já registrado e falhado**. Reenviar um aviso que deu certo mandaria um
    segundo e-mail à família — exatamente o que a trava de unicidade existe para impedir. E criar
    a linha aqui, quando ela não existe, seria abrir um caminho paralelo ao fluxo automático.

    Raises:
        VirtuaisValidationError: Aviso inexistente ou já entregue.
    """
    registro = VirtualOrderNotification.query.filter_by(order_id=order.id, kind=kind).first()
    if registro is None:
        raise VirtuaisValidationError("kind", "Este pedido não tem aviso deste tipo registrado.")
    if registro.sent_ok:
        raise VirtuaisValidationError(
            "kind", "Este aviso já foi entregue — reenviar mandaria um segundo e-mail à família."
        )

    enviadores = _enviadores_de_aviso()
    enviar = enviadores.get(kind)
    if enviar is None:
        raise VirtuaisValidationError("kind", "Tipo de aviso desconhecido.")

    _entregar_aviso(registro, enviar)
    audit(
        "edit", "VirtualOrder", order.id, order.order_nsu,
        f"Reenvio manual do aviso '{kind}': {'entregue' if registro.sent_ok else 'falhou de novo'}",
    )
    db.session.commit()
    return registro


def token_do_aviso_valido(token: str) -> bool:
    """O segredo do endereço confere com o atual ou com o anterior ainda na janela (R-12).

    Comparação em tempo constante. Sem segredo configurado, nada é aceito.
    """
    import hmac

    settings = SiteSetting.query.get(1)
    if settings is None or not token:
        return False
    atual = settings.infinitepay_webhook_token or ""
    if atual and hmac.compare_digest(token, atual):
        return True
    anterior = getattr(settings, "infinitepay_webhook_token_anterior", None) or ""
    ate = getattr(settings, "infinitepay_webhook_token_anterior_ate", None)
    return bool(anterior and ate and ate > agora() and hmac.compare_digest(token, anterior))


def registrar_aviso_invalido(payload: dict) -> None:
    """Chamada com o segredo errado: registra um resumo curto e NÃO ocupa o ``transaction_nsu``.

    Gravar o NSU aqui deixava um aviso legítimo posterior (mesmo NSU) cair como "duplicado" — o
    atacante nem precisava do segredo (feature 310, R2).
    """
    corpo = json.dumps(payload or {}, ensure_ascii=False)[:2000]
    db.session.add(
        VirtualPaymentNotification(
            order_nsu=str((payload or {}).get("order_nsu") or "")[:64] or None,
            transaction_nsu=None,
            raw_payload=corpo,
            secret_ok=False,
            outcome=VIRTUAL_AVISO_RECUSADO_TOKEN,
            message="Segredo do endereço inválido.",
            state=VIRTUAL_AVISO_STATE_DECIDIDO,
        )
    )
    db.session.commit()


def registrar_aviso(payload: dict) -> int | None:
    """Grava o aviso (segredo certo) e devolve o id a processar, ou ``None`` se já está decidido.

    Feature 310 (R2, R-06): a rota só grava e responde; quem decide é ``processar_aviso``, fora da
    requisição. A reentrega de um aviso cujo registro NÃO tem desfecho final volta para a fila —
    antes ela caía como "duplicado" e o pagamento ficava sem dono.
    """
    tx = (payload or {}).get("transaction_nsu")
    order_nsu = (payload or {}).get("order_nsu")
    existente = (
        VirtualPaymentNotification.query.filter_by(transaction_nsu=tx).first() if tx else None
    )
    if existente is not None:
        if existente.outcome in VIRTUAL_AVISO_FINAIS:
            return None
        existente.state = VIRTUAL_AVISO_STATE_PENDENTE
        existente.last_attempt_at = None
        db.session.commit()
        return existente.id

    registro = VirtualPaymentNotification(
        order_nsu=order_nsu,
        transaction_nsu=tx,
        raw_payload=json.dumps(payload or {}, ensure_ascii=False)[:20000],
        secret_ok=True,
        state=VIRTUAL_AVISO_STATE_PENDENTE,
    )
    db.session.add(registro)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existente = VirtualPaymentNotification.query.filter_by(transaction_nsu=tx).first()
        return None if existente is None or existente.outcome in VIRTUAL_AVISO_FINAIS else existente.id
    return registro.id


def _reivindicar_aviso(registro_id: int) -> bool:
    """Claim por linha: só um processo processa cada aviso (padrão do ``claim_sweep``)."""
    from sqlalchemy import text

    momento = agora()
    preso = momento - timedelta(minutes=5)  # thread que morreu no meio (deploy) libera a linha
    resultado = db.session.execute(
        text(
            "UPDATE virtual_payment_notifications SET state = :proc, attempts = attempts + 1, "
            "last_attempt_at = :now WHERE id = :id AND (state = :pend OR "
            "(state = :proc AND last_attempt_at < :preso))"
        ),
        {"proc": VIRTUAL_AVISO_STATE_PROCESSANDO, "pend": VIRTUAL_AVISO_STATE_PENDENTE,
         "now": momento, "id": registro_id, "preso": preso},
    )
    db.session.commit()
    return resultado.rowcount > 0


def processar_aviso(registro_id: int) -> str | None:
    """Decide um aviso registrado (feature 310, R2).

    A reconsulta usa os identificadores DESTE aviso (nunca os gravados no pedido por outro aviso):
    um aviso forjado não contamina o verdadeiro. Os identificadores só vão para o pedido depois de
    provados (``decidir_pagamento``).

    Returns:
        O desfecho, ou ``None`` se outro processo já estava com o aviso.
    """
    from app.integracoes import infinitepay_client as ipc

    if not _reivindicar_aviso(registro_id):
        return None
    registro = db.session.get(VirtualPaymentNotification, registro_id)
    db.session.refresh(registro)
    try:
        payload = json.loads(registro.raw_payload or "{}")
    except ValueError:
        payload = {}

    order = (
        VirtualOrder.query.filter_by(order_nsu=registro.order_nsu).first()
        if registro.order_nsu else None
    )
    if order is None:
        return _fechar_aviso(registro, VIRTUAL_AVISO_ORFAO,
                             f"Nenhum pedido com order_nsu={registro.order_nsu!r}.")
    registro.order_id = order.id
    db.session.commit()

    ids = {
        "transaction_nsu": payload.get("transaction_nsu"),
        "invoice_slug": payload.get("invoice_slug"),
        "receipt_url": payload.get("receipt_url"),
    }
    try:
        consulta = _reconsultar(order.order_nsu, ids)
    except ipc.InfinitePayIndisponivel as exc:
        registro.recheck_result = "unavailable"
        return _fechar_aviso(registro, VIRTUAL_AVISO_RETIDO, f"Operadora indisponível: {exc}",
                             final=False)
    except ipc.InfinitePayError as exc:
        registro.recheck_result = "error"
        return _fechar_aviso(registro, VIRTUAL_AVISO_RETIDO, f"Falha na reconsulta: {exc}",
                             final=False)

    registro.recheck_payload = json.dumps(consulta.get("raw", {}), ensure_ascii=False,
                                          default=str)[:20000]
    if consulta["resultado"] != "pago":
        # Pode ser atraso de propagação na operadora: volta para a fila (R4).
        registro.recheck_result = "unpaid"
        return _fechar_aviso(registro, VIRTUAL_AVISO_PENDENTE_PROVA,
                             f"Operadora: {consulta['resultado']}.", final=False)

    registro.recheck_result = "paid"
    db.session.commit()
    try:
        desfecho = decidir_pagamento(order.id, consulta, identificadores=ids, origem="aviso")
    except Exception as exc:  # noqa: BLE001 — falha na decisão volta para a fila, nunca meia venda
        db.session.rollback()
        logger.exception("[virtuais] decisão do aviso %s falhou", registro_id)
        registro = db.session.get(VirtualPaymentNotification, registro_id)
        return _fechar_aviso(registro, VIRTUAL_AVISO_RETIDO, f"Falha ao decidir: {exc}",
                             final=False)
    if desfecho == VIRTUAL_AVISO_DIVERGENTE:
        registro.recheck_result = "divergent"
    registro = db.session.get(VirtualPaymentNotification, registro_id)
    return _fechar_aviso(registro, desfecho, _MENSAGEM_DESFECHO.get(desfecho, desfecho),
                         final=desfecho in VIRTUAL_AVISO_FINAIS)


_MENSAGEM_DESFECHO = {
    VIRTUAL_AVISO_EFETIVADO: "Venda efetivada.",
    VIRTUAL_AVISO_CONFLITO: "Horário já vendido a outra pessoa — devolução aberta.",
    VIRTUAL_AVISO_DEVOLUCAO: "Pagamento não pôde virar venda — devolução aberta.",
    VIRTUAL_AVISO_DUPLICADO: "Pagamento já decidido.",
    VIRTUAL_AVISO_DIVERGENTE: "Valor pago diferente do pedido — a conferir.",
}


def _fechar_aviso(
    registro: VirtualPaymentNotification, outcome: str, mensagem: str, *, final: bool = True
) -> str:
    """Grava o desfecho; não final volta para a fila do reprocessamento (R-06)."""
    registro.outcome = outcome
    registro.message = mensagem
    registro.state = VIRTUAL_AVISO_STATE_DECIDIDO if final else VIRTUAL_AVISO_STATE_PENDENTE
    db.session.commit()
    if outcome not in (VIRTUAL_AVISO_EFETIVADO, VIRTUAL_AVISO_DUPLICADO):
        logger.warning("[virtuais] aviso %s: %s (%s)", registro.id, outcome, mensagem)
    return outcome


def processar_notificacao_pagamento(payload: dict, *, secret_ok: bool = True) -> dict[str, Any]:
    """Compatibilidade (205): registra e processa um aviso na mesma chamada.

    A rota da 310 usa ``registrar_aviso`` + ``processar_aviso`` (resposta rápida); este atalho fica
    para scripts e verifies antigos.
    """
    if not secret_ok:
        registrar_aviso_invalido(payload)
        return {"outcome": VIRTUAL_AVISO_RECUSADO_TOKEN, "order_nsu": (payload or {}).get("order_nsu")}
    registro_id = registrar_aviso(payload)
    if registro_id is None:
        return {"outcome": VIRTUAL_AVISO_DUPLICADO, "order_nsu": (payload or {}).get("order_nsu")}
    return {"outcome": processar_aviso(registro_id), "order_nsu": (payload or {}).get("order_nsu")}


def reprocessar_avisos(*, limite: int = 50) -> dict[str, int]:
    """Rotina da varredura: avisos sem desfecho final voltam a ser processados (R-06).

    Cadência: 3 tentativas nos minutos 0/1/2 (a política da feature 205) e depois a cada 10 min,
    por até 48 h. Esgotou → fica decidido com o desfecho não final, e entra em "a conferir".
    Vale para pedido de qualquer estado — o aviso de um pagamento atrasado de pedido expirado
    também tem de terminar em venda ou devolução.
    """
    momento = agora()
    limite_idade = momento - timedelta(hours=VIRTUAL_AVISO_REPROCESSA_HORAS)
    candidatos = (
        VirtualPaymentNotification.query.filter(
            VirtualPaymentNotification.secret_ok.is_(True),
            VirtualPaymentNotification.state == VIRTUAL_AVISO_STATE_PENDENTE,
        )
        .order_by(VirtualPaymentNotification.id.asc())
        .limit(limite)
        .all()
    )
    resultado = {"processados": 0, "esperando": 0, "esgotados": 0}
    for aviso in candidatos:
        if aviso.created_at and aviso.created_at < limite_idade:
            aviso.state = VIRTUAL_AVISO_STATE_DECIDIDO
            db.session.commit()
            resultado["esgotados"] += 1
            continue
        intervalo = (
            VIRTUAL_RETRY_INTERVAL_MIN
            if (aviso.attempts or 0) < VIRTUAL_RETRY_MAX_ATTEMPTS
            else VIRTUAL_AVISO_RETRY_LONGO_MIN
        )
        if aviso.last_attempt_at and aviso.last_attempt_at > momento - timedelta(minutes=intervalo):
            resultado["esperando"] += 1
            continue
        try:
            processar_aviso(aviso.id)
            resultado["processados"] += 1
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            logger.warning("[virtuais] reprocessamento do aviso %s falhou: %s", aviso.id, exc)
    return resultado


def registrar_retorno(order: VirtualOrder, dados: dict) -> str | None:
    """Retorno do checkout como segunda prova de pagamento (feature 310, R3, R-08).

    A família toca "Continuar" e volta com ``order_nsu``, ``slug``, ``transaction_nsu`` na URL. Se
    o ``order_nsu`` não for o do pedido, nada acontece (o chamador responde 404). Sem
    identificadores, só devolve o estado. Com eles, reconsulta e decide pela mesma regra.

    Returns:
        O desfecho, ou ``None`` quando não havia o que provar.
    """
    from app.integracoes import infinitepay_client as ipc

    tx = (dados.get("transaction_nsu") or "").strip()[:120] or None
    slug = (dados.get("slug") or "").strip()[:120] or None
    if not tx or not slug or order.status == VIRTUAL_ORDER_STATUS_PAGO:
        return None
    ids = {"transaction_nsu": tx, "invoice_slug": slug,
           "receipt_url": (dados.get("receipt_url") or "")[:500] or None}
    try:
        consulta = _reconsultar(order.order_nsu, ids)
    except ipc.InfinitePayError:
        return VIRTUAL_AVISO_RETIDO
    if consulta["resultado"] != "pago":
        return VIRTUAL_AVISO_PENDENTE_PROVA
    return decidir_pagamento(order.id, consulta, identificadores=ids, origem="retorno")


def regerar_sala(order: VirtualOrder) -> VirtualOrder:
    """Tenta obter a sala de um pedido cuja criação ficou pendente (FR-037).

    Cobre as **duas** formas de ficar sem sala, que exigem tratamentos opostos:

    1. **O evento existe no Google, a sala não materializou ainda.** A criação da sala é assíncrona
       do lado deles; aqui basta reconsultar o evento e gravar o link quando aparecer.
    2. **O evento nunca chegou a existir no Google** (id local, prefixo
       ``virtual-local-``). Reconsultar não resolveria: não há o que consultar. Este caso precisa
       *criar* o evento agora e reconciliar o `CalendarEvent` local com o id verdadeiro.

    Tratar só o caso 1 — como esta função fazia — deixava o caso 2 preso para sempre: cada tentativa
    consultava um id que não existe no Google, falhava, e a família chegava no horário sem sala.

    A venda **nunca** cai por causa disso; no pior caso a pendência segue sinalizada para a equipe.
    """
    from app.calendar.routes import CALENDAR_ID
    from app.calendar.service import fetch_single_event

    if not order.event_id or not order.event:
        raise VirtuaisValidationError("id", "Este pedido ainda não tem evento na Agenda.")

    order.meet_attempts = (order.meet_attempts or 0) + 1
    order.meet_last_attempt_at = agora()

    if (order.event.google_event_id or "").startswith(GOOGLE_ID_LOCAL_PREFIX):
        google_id, html_link, url = _criar_evento_google(order)
        if google_id:
            order.event.google_event_id = google_id
            order.event.google_html_link = html_link
    else:
        evento_google = fetch_single_event(CALENDAR_ID, order.event.google_event_id)
        url = extrair_meet_url(evento_google or {})

    if url:
        order.meet_url = url
        order.meet_pending = False
    db.session.commit()
    return order


def retentar_salas(*, limite: int = 50) -> dict[str, int]:
    """Retenta, em segundo plano, as salas que ficaram pendentes (FR-056, FR-057).

    É a metade assíncrona da política de retry. A síncrona (``executar_com_retry`` dentro de
    ``_criar_evento_google``) absorve o soluço de rede em três tentativas imediatas; esta absorve a
    **queda longa** do Google, com o intervalo de 1 minuto e o progresso em banco — porque entre um
    ciclo e o seguinte o processo pode reiniciar, ou outro worker pode assumir.

    Esgotadas as 3 tentativas, o pedido para de ser retentado e passa a contar como falha
    definitiva: ``meet_pending`` continua ``True`` e o painel mostra que o sistema desistiu
    (FR-056a). Silêncio seria o único desfecho inaceitável.

    Returns:
        ``{"resolvidas": int, "retidas": int, "esgotadas": int}``.
    """
    pendentes = (
        VirtualOrder.query.filter(
            VirtualOrder.status == VIRTUAL_ORDER_STATUS_PAGO,
            VirtualOrder.meet_pending.is_(True),
            VirtualOrder.event_id.isnot(None),
        )
        .limit(limite)
        .all()
    )

    resultado = {"resolvidas": 0, "retidas": 0, "esgotadas": 0}
    for order in pendentes:
        if not deve_tentar_novamente(order.meet_attempts or 0, order.meet_last_attempt_at):
            if retry_esgotou(order.meet_attempts or 0):
                resultado["esgotadas"] += 1
            else:
                resultado["retidas"] += 1
            continue

        try:
            regerar_sala(order)
        except Exception as exc:  # noqa: BLE001 — uma sala não resolvida não derruba o ciclo
            db.session.rollback()
            logger.warning(
                "[virtuais] retentativa de sala do pedido %s falhou: %s", order.order_nsu, exc
            )
            # `regerar_sala` já incrementou o contador antes de estourar, mas o rollback desfez.
            # Sem regravar aqui, a tentativa não conta e o pedido retentaria para sempre.
            order.meet_attempts = (order.meet_attempts or 0) + 1
            order.meet_last_attempt_at = agora()
            db.session.commit()
            resultado["retidas"] += 1
            continue

        if order.meet_pending:
            resultado["retidas"] += 1
        else:
            resultado["resolvidas"] += 1
    return resultado


def alertar_prazos_video(*, dias: int = 2, limite: int = 100) -> int:
    """Alerta a equipe sobre entregas de vídeo com prazo vencendo (FR-057).

    O painel já mostra ``prazo_proximo``/``prazo_vencido`` na linha — mas isso só ajuda quem estiver
    com o painel aberto. O prazo é um compromisso com a família; quem precisa saber que ele está
    vencendo é a produção, mesmo que ninguém esteja olhando a tela.

    ``deadline_alert_at`` garante um alerta por entrega. Sem ele o alerta sairia a cada ciclo da
    varredura, e alerta de minuto em minuto vira ruído que se aprende a ignorar.

    Returns:
        Quantas entregas foram alertadas neste ciclo.
    """
    hoje = agora().date()
    limiar = hoje + timedelta(days=dias)
    vencendo = (
        VirtualMediaDelivery.query.filter(
            VirtualMediaDelivery.status != VIRTUAL_PRODUCTION_STATUS_FINALIZADO,
            VirtualMediaDelivery.due_date.isnot(None),
            VirtualMediaDelivery.due_date <= limiar,
            VirtualMediaDelivery.deadline_alert_at.is_(None),
        )
        .limit(limite)
        .all()
    )

    momento = agora()
    for entrega in vencendo:
        entrega.deadline_alert_at = momento
        pedido = entrega.order
        logger.warning(
            "[virtuais] prazo de vídeo vencendo: pedido %s, entrega até %s (status %s)",
            pedido.order_nsu if pedido else "?", entrega.due_date, entrega.status,
        )
    if vencendo:
        db.session.commit()
    return len(vencendo)


# ── Acesso da família à página do pedido (US5) ───────────────────────────────

MAX_TENTATIVAS_ACESSO = 5
BLOQUEIO_ACESSO_MINUTOS = 15


def verificar_telefone(order: VirtualOrder, telefone: str) -> bool:
    """Confere o telefone da compra para liberar os dados da criança (FR-044a–044c).

    A comparação é só por dígitos: a família digita como quiser — com DDD, com traço, com +55 —
    e o que vale é o número.

    Erros consecutivos são limitados (FR-044b). Sem isso, o telefone viraria um campo adivinhável:
    quem tivesse o endereço do pedido poderia tentar combinações até acertar e ver nome, idade,
    endereço e vídeo de uma criança.

    Raises:
        VirtuaisLimiteError: Tentativas esgotadas — bloqueado temporariamente.
    """
    momento = agora()
    if order.access_blocked_until and order.access_blocked_until > momento:
        restante = int((order.access_blocked_until - momento).total_seconds() // 60) + 1
        raise VirtuaisLimiteError(
            f"Muitas tentativas. Tente de novo em {restante} minuto(s), "
            "ou fale com a gente pelo WhatsApp."
        )

    informado = _normalizar_telefone(telefone)
    correto = _normalizar_telefone(order.contact_phone)
    # Compara pelos últimos dígitos: a compradora pode ter salvo com ou sem o DDI.
    confere = bool(informado) and (informado[-8:] == correto[-8:])

    if confere:
        order.access_attempts = 0
        order.access_blocked_until = None
        db.session.commit()
        return True

    order.access_attempts = (order.access_attempts or 0) + 1
    if order.access_attempts >= MAX_TENTATIVAS_ACESSO:
        order.access_blocked_until = momento + timedelta(minutes=BLOQUEIO_ACESSO_MINUTOS)
        order.access_attempts = 0
        logger.warning("[virtuais] pedido %s bloqueado por tentativas de acesso", order.order_nsu)
    db.session.commit()
    return False


def tentativas_restantes(order: VirtualOrder) -> int:
    """Quantas tentativas de telefone ainda cabem antes do bloqueio."""
    return max(MAX_TENTATIVAS_ACESSO - (order.access_attempts or 0), 0)


# ── Fila de Produção de Mídia (US5) ──────────────────────────────────────────


def salvar_video_entrega(delivery: VirtualMediaDelivery, file_obj: Any) -> VirtualMediaDelivery:
    """Guarda o vídeo gravado e finaliza a entrega (FR-038a a FR-038d).

    O arquivo vai para ``VIRTUAL_VIDEO_FOLDER``, que fica **fora** de ``UPLOAD_FOLDER`` de
    propósito: a rota ``/uploads/<path>`` serve qualquer coisa que caia lá, e com ``USE_S3=true``
    o ``save_file`` devolveria uma URL de bucket público. O vídeo só sai pelo endpoint que valida
    o acesso a cada requisição (FR-038e).

    A entrega só chega a ``finalizado`` depois que o arquivo está no disco e é legível — avisar a
    família de um vídeo que ela não consegue assistir é pior que demorar mais um pouco (FR-038b).

    Raises:
        VirtuaisValidationError: Arquivo ausente, formato não suportado ou acima de 250 MB.
    """
    import os
    import secrets as _secrets

    nome_original = getattr(file_obj, "filename", "") or ""
    if not nome_original:
        raise VirtuaisValidationError("video", "Escolha o arquivo de vídeo.")

    extensao = os.path.splitext(nome_original)[1].lower()
    if extensao not in VIRTUAL_VIDEO_EXTENSIONS:
        raise VirtuaisValidationError(
            "video",
            f"Formato não suportado (use {', '.join(sorted(VIRTUAL_VIDEO_EXTENSIONS))}).",
        )

    pasta = current_app.config["VIRTUAL_VIDEO_FOLDER"]
    os.makedirs(pasta, exist_ok=True)
    nome_final = f"{delivery.order.order_nsu}-{_secrets.token_hex(4)}{extensao}"
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
                if tamanho > VIRTUAL_VIDEO_MAX_BYTES:
                    raise VirtuaisValidationError(
                        "video",
                        f"Vídeo acima do limite de "
                        f"{VIRTUAL_VIDEO_MAX_BYTES // (1024 * 1024)} MB.",
                    )
                destino.write(pedaco)
    except VirtuaisValidationError:
        _remover_arquivo(caminho)
        raise
    except OSError as exc:
        _remover_arquivo(caminho)
        delivery.last_upload_error = f"Falha ao guardar o vídeo: {exc}"
        db.session.commit()
        raise VirtuaisValidationError("video", "Não foi possível guardar o vídeo agora.") from exc

    # Confere que o arquivo existe e tem conteúdo antes de dar a entrega por concluída (FR-038b).
    if not os.path.exists(caminho) or os.path.getsize(caminho) == 0:
        _remover_arquivo(caminho)
        delivery.last_upload_error = "O vídeo foi salvo vazio."
        db.session.commit()
        raise VirtuaisValidationError("video", "O vídeo chegou vazio. Tente enviar de novo.")

    # Reenvio substitui o anterior — sem deixar arquivo órfão ocupando disco.
    if delivery.video_path and delivery.video_path != nome_final:
        _remover_arquivo(os.path.join(pasta, delivery.video_path))

    delivery.video_path = nome_final
    delivery.video_mime = f"video/{extensao.lstrip('.').replace('mov', 'quicktime')}"
    delivery.video_size_bytes = tamanho
    delivery.video_published_at = agora()
    delivery.last_upload_error = None
    delivery.status = VIRTUAL_PRODUCTION_STATUS_FINALIZADO
    db.session.commit()

    _enviar_aviso(delivery.order, VIRTUAL_NOTIFICATION_KIND_VIDEO)
    return delivery


def _remover_arquivo(caminho: str) -> None:
    """Apaga um arquivo, ignorando ausência (best-effort)."""
    import os

    try:
        if os.path.exists(caminho):
            os.remove(caminho)
    except OSError as exc:  # noqa: BLE001 — arquivo órfão não pode travar o fluxo
        logger.warning("[virtuais] não foi possível remover %s: %s", caminho, exc)


def caminho_video(delivery: VirtualMediaDelivery) -> str | None:
    """Caminho absoluto do vídeo no disco, ou ``None`` se ainda não há vídeo.

    Uso exclusivo do endpoint que serve o arquivo — este valor **nunca** vai para um payload JSON.
    """
    import os

    if not delivery.video_path:
        return None
    return os.path.join(current_app.config["VIRTUAL_VIDEO_FOLDER"], delivery.video_path)


def atualizar_status_entrega(
    delivery: VirtualMediaDelivery, status: str, *, user_id: int | None = None
) -> VirtualMediaDelivery:
    """Move a entrega pelo fluxo de produção (FR-047, FR-048, FR-048a).

    Os três estados são os únicos que existem. Enviar o vídeo é a **ação** que permite chegar a
    ``finalizado`` — por isso finalizar uma entrega gravada sem vídeo é recusado: a família seria
    avisada de algo que não existe.

    Raises:
        VirtuaisValidationError: Status fora da lista, ou `finalizado` sem vídeo.
    """
    limpo = (status or "").strip().lower()
    if limpo not in VIRTUAL_PRODUCTION_STATUSES:
        raise VirtuaisValidationError(
            "status", f"Status inválido (use: {', '.join(VIRTUAL_PRODUCTION_STATUSES)})."
        )

    if (
        limpo == VIRTUAL_PRODUCTION_STATUS_FINALIZADO
        and delivery.order.modality == VIRTUAL_MODALITY_GRAVADO
        and not delivery.video_path
    ):
        raise VirtuaisValidationError("video", "Envie o vídeo antes de finalizar a entrega.")

    delivery.status = limpo
    delivery.updated_by_id = user_id
    db.session.commit()
    return delivery


def listar_fila_producao(
    *, campaign_id: Any = None, day: str | None = None, status: str | None = None
) -> list[VirtualMediaDelivery]:
    """Entregas da Fila de Produção de Mídia, mais urgente primeiro (FR-045, FR-050).

    Ordena por horário da chamada (ao vivo) ou prazo de entrega (gravado): o painel é operacional
    e existe para responder "o que fazer agora".
    """
    from sqlalchemy.orm import joinedload

    query = (
        VirtualMediaDelivery.query.join(VirtualOrder, VirtualMediaDelivery.order_id == VirtualOrder.id)
        .options(
            joinedload(VirtualMediaDelivery.order).joinedload(VirtualOrder.slot),
            joinedload(VirtualMediaDelivery.order).joinedload(VirtualOrder.campaign),
            joinedload(VirtualMediaDelivery.order).joinedload(VirtualOrder.event),
        )
        .filter(VirtualOrder.status == VIRTUAL_ORDER_STATUS_PAGO)
    )
    if campaign_id:
        query = query.filter(VirtualOrder.campaign_id == int(campaign_id))
    if status:
        query = query.filter(VirtualMediaDelivery.status == status)

    entregas = query.all()

    if day:
        alvo = _parse_date(day, "date", label="Data")
        entregas = [
            e
            for e in entregas
            if (e.order.slot and e.order.slot.start_at.date() == alvo)
            or (e.due_date == alvo)
        ]

    futuro = datetime.max
    return sorted(
        entregas,
        key=lambda e: (
            e.order.slot.start_at
            if e.order.slot
            else (datetime.combine(e.due_date, time.min) if e.due_date else futuro),
            e.id,
        ),
    )


def serialize_delivery(delivery: VirtualMediaDelivery) -> dict[str, Any]:
    """Uma linha da Fila de Produção — os quatro blocos na mesma altura (FR-046).

    Reusa `impressoes3d_ops.serialize_gift` no bloco do presente: o payload do presente 3D tem uma
    montagem só no sistema inteiro (Princípio I).

    **Nunca** devolve `video_path` — o caminho no disco não é divulgável (FR-038e).
    """
    from app.impressoes3d.impressoes3d_ops import serialize_gift

    order = delivery.order
    presente = None
    if order.event and order.event.presentes_3d:
        presente = serialize_gift(order.event.presentes_3d[0])

    hoje = agora().date()
    return {
        "id": delivery.id,
        # O id do pedido (não o da entrega) é o que as ações de reenvio de aviso e de regeração de
        # sala endereçam — elas agem sobre o pedido, não sobre a linha de produção.
        "order_id": order.id,
        "order_token": order.public_token,
        "order_nsu": order.order_nsu,
        "modality": order.modality,
        "start_at": order.slot.start_at.isoformat() if order.slot else None,
        "due_date": delivery.due_date.isoformat() if delivery.due_date else None,
        "prazo_vencido": bool(delivery.due_date and delivery.due_date < hoje),
        "prazo_proximo": bool(
            delivery.due_date and hoje <= delivery.due_date <= hoje + timedelta(days=2)
        ),
        "status": delivery.status,
        "child_name": order.child_name,
        "child_age": order.child_age,
        "behavior_notes": order.behavior_notes,
        "campaign_title": order.campaign.title if order.campaign else None,
        "meet_url": order.meet_url,
        "meet_pending": bool(order.meet_pending),
        "gift": presente,
        "has_video": bool(delivery.video_path),
        "last_upload_error": delivery.last_upload_error,
        "whatsapp_url": _whatsapp_url(order),
        # Falhas de aviso (FR-039c, FR-056a): a fila é onde a equipe já está quando decide reforçar
        # pelo WhatsApp. Sem isso a falha do e-mail existia só no banco, e o reforço manual era
        # feito no escuro — ou não era feito, porque ninguém sabia que precisava.
        "avisos_falhos": serialize_avisos_falhos(order),
        # A sala desistiu de ser gerada: `meet_pending` sozinho não distingue "ainda tentando" de
        # "parou de tentar", e essa diferença é a que decide se alguém precisa agir agora.
        "meet_retry_esgotado": bool(
            order.meet_pending and retry_esgotou(order.meet_attempts or 0)
        ),
        "meet_attempts": order.meet_attempts or 0,
    }


def serialize_avisos_falhos(order: VirtualOrder) -> list[dict[str, Any]]:
    """Avisos automáticos deste pedido que **não** foram entregues (FR-039c, FR-056a).

    Só os falhados. Listar os que deram certo encheria o painel de linhas verdes que ninguém
    precisa ver e afogaria justamente a que exige ação.
    """
    return [
        {
            "kind": aviso.kind,
            "label": VIRTUAL_NOTIFICATION_LABELS.get(aviso.kind, aviso.kind),
            "error_message": aviso.error_message,
            "attempts": aviso.attempts or 0,
            "esgotado": retry_esgotou(aviso.attempts or 0),
            "last_attempt_at": (
                aviso.last_attempt_at.isoformat() if aviso.last_attempt_at else None
            ),
        }
        for aviso in (order.sent_notifications or [])
        if not aviso.sent_ok
    ]


def _whatsapp_url(order: VirtualOrder) -> str | None:
    """Atalho de WhatsApp com a mensagem pronta (FR-039b).

    O reforço manual existe porque o aviso automático é por e-mail, e e-mail nem sempre é lido.
    A mensagem já vem escrita para a equipe não precisar redigir na pressa.
    """
    from urllib.parse import quote

    telefone = _normalizar_telefone(order.contact_phone)
    if not telefone:
        return None
    if not telefone.startswith("55"):
        telefone = f"55{telefone}"

    primeiro_nome = (order.child_name or "").split()[0] if order.child_name else ""
    if order.modality == VIRTUAL_MODALITY_GRAVADO:
        texto = f"Oi! O vídeo da {primeiro_nome} está pronto 🎬 Confira na página do seu pedido."
    else:
        texto = f"Oi! Lembrete da chamada da {primeiro_nome} 🎥 O link está na página do pedido."
    return f"https://wa.me/{telefone}?text={quote(texto)}"


# ── Serialização (fonte única dos payloads JSON da feature) ──────────────────


def _money(value: Any) -> str | None:
    """Formata dinheiro para o JSON: string decimal em reais, nunca centavos (Princípio IX)."""
    if value is None:
        return None
    return str(Decimal(value).quantize(Decimal("0.01")))


def serialize_campaign(campaign: VirtualCampaign) -> dict[str, Any]:
    """Payload público da campanha — o que a landing precisa, e nada além disso."""
    character = campaign.character
    return {
        "slug": campaign.slug,
        "title": campaign.title,
        "character": (
            {"name": character.name, "photo_url": character.photo_url} if character else None
        ),
        "cover_url": campaign.cover_url,
        "intro_html": campaign.intro_html,
        "tolerance_terms": campaign.tolerance_terms,
        "faq": campaign.faq_items,
        "whatsapp_phone": campaign.whatsapp_phone,
        "price_live": _money(campaign.price_live),
        "price_recorded": _money(campaign.price_recorded),
        "price_gift": _money(campaign.price_gift),
        "recorded_available": campaign.recorded_available,
        "recorded_delivery_days": campaign.recorded_delivery_days,
        "gift_items": [
            {"id": item.id, "name": item.name, "photo_url": item.photo_url}
            for item in campaign.acervo_items
            if item.is_active
        ],
    }


def listar_vitrine() -> list[dict[str, Any]]:
    """Campanhas publicadas, para a vitrine da loja (feature 224e).

    É o que a raiz de `alo.mantoproducoes.com.br` mostra: antes ela caía no catálogo de eventos,
    que é outro produto. Payload enxuto de card — o resto a landing de cada campanha carrega.

    `tem_horario` diz se ainda há chamada ao vivo para vender, e `tem_gravado` se ainda há vídeo
    no estoque. Uma campanha sem nenhum dos dois continua listada, mas o card avisa: sumir dela
    de repente confundiria quem recebeu o link e voltaria depois.
    """
    campanhas = (
        VirtualCampaign.query.filter_by(status=VIRTUAL_CAMPAIGN_STATUS_PUBLICADA)
        .order_by(VirtualCampaign.created_at.desc())
        .all()
    )
    vitrine = []
    for campanha in campanhas:
        character = campanha.character
        vitrine.append({
            "slug": campanha.slug,
            "title": campanha.title,
            "character_name": character.name if character else None,
            "cover_url": campanha.cover_url,
            "price_live": _money(campanha.price_live),
            "price_recorded": _money(campanha.price_recorded),
            "tem_horario": len(listar_slots_disponiveis(campanha)) > 0,
            "tem_gravado": campanha.recorded_available > 0,
        })
    return vitrine


def serialize_campaign_admin(campaign: VirtualCampaign) -> dict[str, Any]:
    """Payload administrativo — acrescenta configuração, números de venda e as opções de acervo.

    ``available_gift_items`` traz o Acervo 3D ativo inteiro, não só o liberado: é o que a tela usa
    para montar o seletor de peças. Vem por aqui, e não pelo endpoint do módulo 3D, porque aquele é
    restrito ao Artista 3D — quem monta a campanha é o Comercial (FR-005, FR-009).
    """
    metrics = campaign_metrics(campaign)
    disponiveis = (
        Acervo3DItem.query.filter(Acervo3DItem.is_active.is_(True))
        .order_by(Acervo3DItem.name.asc())
        .all()
    )
    return {
        "available_gift_items": [
            {"id": item.id, "name": item.name, "photo_url": item.photo_url}
            for item in disponiveis
        ],
        **serialize_campaign(campaign),
        "id": campaign.id,
        "status": campaign.status,
        "catalog_character_id": campaign.catalog_character_id,
        "talent_id": campaign.talent_id,
        "figurino_sheet_id": campaign.figurino_sheet_id,
        "recorded_capacity": campaign.recorded_capacity,
        "recorded_sold": campaign.recorded_sold,
        "max_reservations_per_origin": campaign.max_reservations_per_origin,
        "reservation_window_minutes": campaign.reservation_window_minutes,
        "acervo_item_ids": [item.id for item in campaign.acervo_items],
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
        **metrics,
    }


def campaign_metrics(campaign: VirtualCampaign) -> dict[str, Any]:
    """Números de acompanhamento da campanha (FR-005, FR-009).

    ``revenue`` soma só pedidos pagos — reserva não paga não é receita.
    """
    from app.constants import VIRTUAL_ORDER_STATUS_PAGO

    pagos = VirtualOrder.query.filter_by(
        campaign_id=campaign.id, status=VIRTUAL_ORDER_STATUS_PAGO
    ).all()
    revenue = sum((order.total_value or Decimal("0") for order in pagos), Decimal("0"))

    slots = VirtualCampaignSlot.query.filter_by(campaign_id=campaign.id).all()
    momento = agora()
    return {
        "sold_count": len(pagos),
        "revenue": _money(revenue),
        "slots_total": len(slots),
        "slots_available": sum(
            1 for s in slots if s.is_available(momento) and s.start_at > momento
        ),
        "recorded_used": campaign.recorded_sold,
        "recorded_capacity_total": campaign.recorded_capacity,
    }


def serialize_slot(slot: VirtualCampaignSlot) -> dict[str, Any]:
    """Horário em JSON. O payload público nunca revela quem reservou."""
    return {
        "id": slot.id,
        "start_at": slot.start_at.isoformat() if slot.start_at else None,
        "status": slot.status,
        "locked_until": slot.locked_until.isoformat() if slot.locked_until else None,
    }


def serialize_order_full(order: VirtualOrder) -> dict[str, Any]:
    """Pedido completo — **só depois da validação dupla** (FR-044a).

    É o payload que revela o que o resumo esconde: nome e idade da criança, dicas, endereço e o
    acesso ao vídeo. Mesmo aqui, o vídeo vai como **endereço do endpoint**, nunca como caminho de
    arquivo: o caminho no disco não é divulgável (FR-038e).
    """
    entrega = order.media_delivery
    return {
        **serialize_order_summary(order),
        "verified": True,
        "child_name": order.child_name,
        "child_age": order.child_age,
        "behavior_notes": order.behavior_notes,
        "delivery_address": order.delivery_address,
        "gift": (
            {"name": order.gift_item.name, "photo_url": order.gift_item.photo_url}
            if order.gift_item
            else None
        ),
        "video_url": (
            f"/api/virtuais/pedidos/{order.public_token}/video"
            if entrega and entrega.video_path
            else None
        ),
        "recorded_due_date": (
            entrega.due_date.isoformat() if entrega and entrega.due_date else None
        ),
    }


def serialize_refund(refund: VirtualRefundRequest) -> dict[str, Any]:
    """Devolução em JSON — traz o que a equipe precisa para achar a cobrança na operadora."""
    order = refund.order
    return {
        "id": refund.id,
        "status": refund.status,
        "amount": _money(refund.amount),
        "reason": refund.reason,
        # O `reason` cru é chave de sistema; quem atende o telefone precisa da frase (FR-018b).
        "reason_label": VIRTUAL_REFUND_REASON_LABELS.get(refund.reason, refund.reason),
        "sem_confirmacao": refund.reason == VIRTUAL_REFUND_REASON_SEM_CONFIRMACAO,
        "invoice_slug": refund.invoice_slug,
        "transaction_nsu": refund.transaction_nsu,
        "created_at": refund.created_at.isoformat() if refund.created_at else None,
        "resolved_at": refund.resolved_at.isoformat() if refund.resolved_at else None,
        "order": (
            {
                "order_nsu": order.order_nsu,
                "child_name": order.child_name,
                "contact_phone_display": order.contact_phone_display or order.contact_phone,
                "contact_email": order.contact_email,
                "campaign_title": order.campaign.title if order.campaign else None,
            }
            if order
            else None
        ),
    }


def serialize_order_summary(order: VirtualOrder) -> dict[str, Any]:
    """Resumo do pedido para a página pública **antes** da validação dupla (FR-044a).

    Devolve só o suficiente para a família reconhecer que chegou ao pedido certo: situação,
    horário, valor e uma dica do telefone. **Nenhum dado de criança sai aqui** — nome, idade,
    dicas, endereço, sala e vídeo só depois que o telefone for conferido (US5).

    ``phone_hint`` mostra os quatro últimos dígitos: ajuda quem tem o pedido a saber qual telefone
    digitar, e não entrega o número a quem só descobriu o endereço.
    """
    telefone = order.contact_phone or ""
    campaign = order.campaign
    return {
        "status": order.status,
        "modality": order.modality,
        "start_at": order.slot.start_at.isoformat() if order.slot else None,
        "total_value": _money(order.total_value),
        "locked_until": order.locked_until.isoformat() if order.locked_until else None,
        "payment_url": (
            order.payment_url if order.status in VIRTUAL_ORDER_STATUS_ATIVOS else None
        ),
        "requires_verification": True,
        "phone_hint": f"•••• {telefone[-4:]}" if len(telefone) >= 4 else None,
        # A sala é o único item "sensível" liberado antes da validação dupla, e por um motivo
        # prático: quem tem o link do pedido é quem comprou, e chegar atrasado na chamada de 10
        # minutos por causa de uma etapa a mais custa a experiência inteira. Nome, idade, dicas,
        # endereço e vídeo continuam atrás da validação (FR-044a).
        "meet_url": order.meet_url if order.status == VIRTUAL_ORDER_STATUS_PAGO else None,
        "meet_pending": bool(order.meet_pending) if order.status == VIRTUAL_ORDER_STATUS_PAGO else False,
        "campaign": (
            {
                "slug": campaign.slug,
                "title": campaign.title,
                "whatsapp_phone": campaign.whatsapp_phone,
                "recorded_delivery_days": campaign.recorded_delivery_days,
            }
            if campaign
            else None
        ),
    }
