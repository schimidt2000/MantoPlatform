"""Núcleo de negócio da Produção de Figurinos (feature 225).

Funções puras (sem ``flask.request``/``render_template``/``flash``), fonte única reusada pelos
endpoints JSON de `app/api/figurino_producao_read.py` e `_write.py` e pelo resumo da home em
`app/api/dashboard_service.py`.

O módulo cobre o pedaço da operação que não existia: entre a ficha do personagem
(`FigurinoSheet`, que descreve o figurino pronto) e o gasto extra (`SpecialExpense`, que registra
o dinheiro depois que saiu), o trabalho de **produzir** não tinha registro. É por isso que os oito
lançamentos do figurino das Cartas (Alice/Cuiabá) ficam soltos: nada os junta.
"""

from __future__ import annotations

import logging
import os
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app import db
from app.constants import (
    FIGURINO_ANEXO_KINDS,
    FIGURINO_ANEXO_ORCAMENTO,
    FIGURINO_PROD_ABERTOS,
    FIGURINO_PROD_APROVADO,
    FIGURINO_PROD_CANCELADO,
    FIGURINO_PROD_EM_PRODUCAO,
    FIGURINO_PROD_LABELS,
    FIGURINO_PROD_PRONTO,
    FIGURINO_PROD_SOLICITADO,
    FIGURINO_PROD_STATUSES,
    GCAL_KIND_FIGURINO_PRODUCAO,
    GCAL_KIND_KEY,
    RoleName,
    now_sp,
)
from app.models import (
    CalendarEvent,
    FigurinoProducao,
    FigurinoProducaoAnexo,
    FigurinoProducaoLog,
    FigurinoSheet,
    SpecialExpense,
    User,
)
from app.storage import delete_file, save_file
from app.utils import audit

logger = logging.getLogger(__name__)

#: Pastas de upload. Separadas por finalidade para a foto de evolução nunca cair na mesma
#: listagem do PDF de orçamento.
SUBFOLDER_FOTOS = "figurino_producao_fotos"
SUBFOLDER_ORCAMENTOS = "figurino_producao_orcamentos"

#: Foto de evolução: só imagem (passa pela compressão de `storage.save_file`).
FOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
#: Orçamento: imagem **ou** PDF — fornecedor de aviamento manda foto do WhatsApp, ateliê manda PDF.
ORCAMENTO_EXTENSIONS = FOTO_EXTENSIONS | {".pdf"}

#: Transições permitidas. Cancelar sai de qualquer estado aberto; "pronto" é terminal.
TRANSICOES: dict[str, set[str]] = {
    FIGURINO_PROD_SOLICITADO:  {FIGURINO_PROD_APROVADO, FIGURINO_PROD_CANCELADO},
    FIGURINO_PROD_APROVADO:    {FIGURINO_PROD_EM_PRODUCAO, FIGURINO_PROD_CANCELADO},
    FIGURINO_PROD_EM_PRODUCAO: {FIGURINO_PROD_PRONTO, FIGURINO_PROD_CANCELADO},
    FIGURINO_PROD_PRONTO:      {FIGURINO_PROD_EM_PRODUCAO},  # reabrir: ficou pronto e voltou
    FIGURINO_PROD_CANCELADO:   {FIGURINO_PROD_SOLICITADO},   # reabrir um pedido desistido
}


class ProducaoValidationError(Exception):
    """Erro de validação de negócio, com o campo culpado.

    O endpoint traduz em ``json_error(msg, 400, fields={campo: msg})`` para o React destacar o
    campo exato do formulário (Princípio V).
    """

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


# ── Helpers ──────────────────────────────────────────────────────────────────


def _brl(valor: Decimal | float | None) -> str:
    """Formata em real brasileiro para o texto do histórico.

    O histórico é lido por gente, em pt-BR: `str(Decimal)` sairia "R$ 4800.00", com ponto de
    milhar no lugar errado e centavo separado por ponto.
    """
    if valor is None:
        return "—"
    return f"R$ {Decimal(valor):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _actor_role(actor: User | None) -> str:
    return ", ".join(r.name for r in actor.roles) if actor else "Sistema"


def _tem_papel(user: User | None, *nomes: str) -> bool:
    if not user:
        return False
    return any(r.name in nomes for r in user.roles)


def pode_executar(user: User | None) -> bool:
    """Quem move o pedido para frente, designa responsável e anexa: Figurino ou Superadmin."""
    return _tem_papel(user, RoleName.FIGURINO, RoleName.SUPERADMIN)


def pode_aprovar(user: User | None) -> bool:
    """Só Superadmin aprova (FR-011) — figurino é 70% do gasto extra da empresa."""
    return _tem_papel(user, RoleName.SUPERADMIN)


def pode_abrir(user: User | None) -> bool:
    """Qualquer papel interno abre pedido (FR-012); Revendedor EducaManto não é equipe interna."""
    if not user:
        return False
    nomes = {r.name for r in user.roles}
    return bool(nomes) and nomes != {RoleName.REVENDEDOR_EDUCAMANTO}


def _parse_decimal(raw: Any, field: str, label: str) -> Decimal | None:
    """Converte valor monetário vindo do formulário; vazio vira None."""
    if raw is None or str(raw).strip() == "":
        return None
    texto = str(raw).strip().replace("R$", "").strip()
    # Aceita "1.234,56" (pt-BR) e "1234.56" (o que o React manda) sem confundir os separadores.
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        valor = Decimal(texto)
    except (InvalidOperation, ValueError) as exc:
        raise ProducaoValidationError(field, f"{label} inválido.") from exc
    if valor < 0:
        raise ProducaoValidationError(field, f"{label} não pode ser negativo.")
    return valor


def _parse_date(raw: Any, field: str, label: str) -> date | None:
    """Lê data ISO (YYYY-MM-DD) do formulário; vazio vira None.

    Fatia a string em vez de usar `datetime.fromisoformat` em texto com fuso: um `toISOString()`
    do React chega como UTC e deslocaria o dia (a mesma armadilha que já mordeu os horários dos
    eventos).
    """
    if raw is None or str(raw).strip() == "":
        return None
    texto = str(raw).strip()[:10]
    try:
        ano, mes, dia = (int(p) for p in texto.split("-"))
        return date(ano, mes, dia)
    except (ValueError, TypeError) as exc:
        raise ProducaoValidationError(field, f"{label} inválida.") from exc


def _validar_extensao(file_obj: Any, kind: str) -> None:
    permitidas = ORCAMENTO_EXTENSIONS if kind == FIGURINO_ANEXO_ORCAMENTO else FOTO_EXTENSIONS
    nome = getattr(file_obj, "filename", "") or ""
    ext = os.path.splitext(nome)[1].lower()
    if ext not in permitidas:
        rotulo = "imagem ou PDF" if kind == FIGURINO_ANEXO_ORCAMENTO else "imagem"
        raise ProducaoValidationError("file", f"Arquivo não suportado (envie {rotulo}): {nome}")


# ── Histórico ────────────────────────────────────────────────────────────────


def registrar_log(
    producao: FigurinoProducao,
    mensagem: str,
    *,
    actor: User | None = None,
    photo_path: str | None = None,
    status_from: str | None = None,
    status_to: str | None = None,
) -> FigurinoProducaoLog:
    """Acrescenta uma linha ao histórico do pedido. Não commita (quem chama decide)."""
    log = FigurinoProducaoLog(
        producao_id=producao.id,
        actor_name=actor.name if actor else "Sistema",
        actor_role=_actor_role(actor),
        message=mensagem,
        photo_path=photo_path,
        status_from=status_from,
        status_to=status_to,
        created_at=now_sp(),
    )
    db.session.add(log)
    return log


# ── Agenda do Google ─────────────────────────────────────────────────────────


def _titulo_agenda(producao: FigurinoProducao) -> str:
    return f"🧵 Figurino: {producao.title}"


def _descricao_agenda(producao: FigurinoProducao) -> str:
    linhas = [producao.description or ""]
    if producao.event:
        linhas.append(f"Evento: {producao.event.title}")
    if producao.quantity and producao.quantity > 1:
        linhas.append(f"Quantidade: {producao.quantity}")
    linhas.append("")
    linhas.append("Pedido de produção de figurino — Plataforma Manto.")
    return "\n".join(l for l in linhas if l is not None).strip()


def sincronizar_agenda(producao: FigurinoProducao) -> str | None:
    """Põe (ou tira) o prazo do pedido na agenda, com a pessoa responsável convidada.

    Cria quando há responsável e prazo; move quando um dos dois muda; remove quando o pedido é
    concluído, cancelado, fica sem responsável ou sem prazo.

    Returns:
        Aviso em pt-BR quando o Google não colaborou, ou ``None`` em caso de sucesso.
        **Nunca levanta**: falha de integração externa não pode derrubar a operação de negócio
        (mesma política de `event_ops.update_event_core`, que devolve `warnings` ao front).
    """
    from flask import current_app

    from app.calendar.routes import CALENDAR_ID
    from app.calendar.service import delete_event as gcal_delete
    from app.calendar.service import upsert_task_event

    # Trava de ambiente (ver `config._suppress_calendar_invites`): a cópia local do banco traz o
    # token do Google da produção, e o calendário de destino é fixo. Sem isto, qualquer teste
    # local cria compromisso de verdade na agenda da empresa e convida a pessoa real.
    if current_app.config.get("CALENDAR_SUPPRESS_INVITES"):
        logger.info(
            "[figurino-prod] compromisso do pedido %s não sincronizado: convites desligados "
            "neste ambiente", producao.id,
        )
        return None

    prazo = producao.prazo_efetivo
    quer_compromisso = bool(producao.responsible_id and prazo and producao.is_open)

    if not quer_compromisso:
        if not producao.google_event_id:
            return None
        try:
            gcal_delete(CALENDAR_ID, producao.google_event_id)
        except Exception as exc:  # noqa: BLE001 — o pedido já mudou; o Google é consequência
            logger.warning("[figurino-prod] falha ao remover compromisso: %s", exc)
            return f"O pedido foi salvo, mas não foi possível remover o prazo da agenda: {exc}"
        finally:
            producao.google_event_id = None
        return None

    email = (producao.responsible.email or "").strip() if producao.responsible else ""
    convidados = [email] if email else []
    try:
        criado = upsert_task_event(
            CALENDAR_ID,
            _titulo_agenda(producao),
            prazo,
            google_event_id=producao.google_event_id,
            description=_descricao_agenda(producao),
            attendee_emails=convidados,
            extended_private={
                GCAL_KIND_KEY: GCAL_KIND_FIGURINO_PRODUCAO,
                "manto_producao_id": str(producao.id),
            },
        )
    except Exception as exc:  # noqa: BLE001 — ver docstring
        logger.warning("[figurino-prod] falha ao sincronizar compromisso: %s", exc)
        return f"O pedido foi salvo, mas não foi possível marcar o prazo na agenda: {exc}"

    producao.google_event_id = criado.get("id") or producao.google_event_id
    if not email:
        return (
            f"O prazo entrou na agenda, mas {producao.responsible.name} não tem e-mail "
            "cadastrado — o convite não foi enviado."
        )
    return None


# ── Leitura ──────────────────────────────────────────────────────────────────


def _base_query():
    return FigurinoProducao.query.options(
        joinedload(FigurinoProducao.event),
        joinedload(FigurinoProducao.figurino_sheet),
        joinedload(FigurinoProducao.responsible),
        joinedload(FigurinoProducao.requested_by),
    )


def list_producoes(
    *,
    status: str | None = None,
    somente_abertos: bool = False,
    responsible_id: int | None = None,
    event_id: int | None = None,
    busca: str | None = None,
) -> list[FigurinoProducao]:
    """Lista pedidos com os filtros da tela da oficina.

    Ordem: prazo mais próximo primeiro, e quem não tem prazo vai para o fim — quem abre a fila
    quer ver o que aperta, não o que foi cadastrado primeiro.
    """
    q = _base_query()
    if status:
        q = q.filter(FigurinoProducao.status == status)
    if somente_abertos:
        q = q.filter(FigurinoProducao.status.in_(FIGURINO_PROD_ABERTOS))
    if responsible_id:
        q = q.filter(FigurinoProducao.responsible_id == responsible_id)
    if event_id:
        q = q.filter(FigurinoProducao.event_id == event_id)
    if busca:
        termo = f"%{busca.strip()}%"
        q = q.filter(
            or_(
                FigurinoProducao.title.ilike(termo),
                FigurinoProducao.description.ilike(termo),
            )
        )
    itens = q.all()
    sem_prazo = date.max
    return sorted(
        itens,
        key=lambda p: (p.prazo_efetivo or sem_prazo, -p.id),
    )


def pedidos_do_responsavel(user: User) -> list[FigurinoProducao]:
    """Pedidos abertos sob responsabilidade da pessoa — o painel pessoal da home (FR-050)."""
    return list_producoes(responsible_id=user.id, somente_abertos=True)


def serialize_anexo(anexo: FigurinoProducaoAnexo) -> dict[str, Any]:
    return {
        "id": anexo.id,
        "kind": anexo.kind,
        "url": anexo.file_path,
        "original_name": anexo.original_name,
        "caption": anexo.caption,
        "supplier_name": anexo.supplier_name,
        "amount": float(anexo.amount) if anexo.amount is not None else None,
        "uploaded_by": anexo.uploaded_by.name if anexo.uploaded_by else None,
        "created_at": anexo.created_at.isoformat() if anexo.created_at else None,
    }


def serialize_log(log: FigurinoProducaoLog) -> dict[str, Any]:
    return {
        "id": log.id,
        "actor_name": log.actor_name,
        "actor_role": log.actor_role,
        "message": log.message,
        "photo_url": log.photo_path,
        "status_from": log.status_from,
        "status_to": log.status_to,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def _serialize_gasto(gasto: SpecialExpense) -> dict[str, Any]:
    return {
        "id": gasto.id,
        "description": gasto.description,
        "amount": float(gasto.amount or 0),
        "status": gasto.status,
        "expense_date": gasto.expense_date.isoformat() if gasto.expense_date else None,
        "receipt_url": gasto.receipt_url,
    }


def serialize_producao(
    producao: FigurinoProducao, *, detalhado: bool = False
) -> dict[str, Any]:
    """Serializa o pedido. ``detalhado`` acrescenta anexos, histórico e gastos."""
    prazo = producao.prazo_efetivo
    previsto = producao.estimated_cost
    gasto = producao.total_gasto
    payload: dict[str, Any] = {
        "id": producao.id,
        "title": producao.title,
        "description": producao.description,
        "status": producao.status,
        "status_label": FIGURINO_PROD_LABELS.get(producao.status, producao.status),
        "quantity": producao.quantity,
        "event_id": producao.event_id,
        "event_title": producao.event.title if producao.event else None,
        "event_start_at": (
            producao.event.start_at.isoformat()
            if producao.event and producao.event.start_at
            else None
        ),
        "figurino_sheet_id": producao.figurino_sheet_id,
        "figurino_sheet_name": (
            producao.figurino_sheet.character_name if producao.figurino_sheet else None
        ),
        "figurino_sheet_photo": (
            producao.figurino_sheet.photo_url if producao.figurino_sheet else None
        ),
        "requested_by": producao.requested_by.name if producao.requested_by else None,
        "responsible_id": producao.responsible_id,
        "responsible_name": producao.responsible.name if producao.responsible else None,
        "approved_by": producao.approved_by.name if producao.approved_by else None,
        "approved_at": producao.approved_at.isoformat() if producao.approved_at else None,
        "due_date": producao.due_date.isoformat() if producao.due_date else None,
        # O prazo que vale: o informado, ou a data do evento quando ninguém informou (FR-004).
        "prazo_efetivo": prazo.isoformat() if prazo else None,
        "dias_para_prazo": producao.dias_para_prazo,
        "is_late": producao.is_late,
        "is_open": producao.is_open,
        "estimated_cost": float(previsto) if previsto is not None else None,
        "total_gasto": float(gasto),
        "gastos_count": sum(1 for g in producao.gastos if g.status == "aprovado"),
        "cancellation_reason": producao.cancellation_reason,
        "done_at": producao.done_at.isoformat() if producao.done_at else None,
        "google_event_id": producao.google_event_id,
        "created_at": producao.created_at.isoformat() if producao.created_at else None,
    }
    if detalhado:
        payload["anexos"] = [serialize_anexo(a) for a in producao.anexos]
        payload["logs"] = [serialize_log(l) for l in producao.logs]
        payload["gastos"] = [_serialize_gasto(g) for g in producao.gastos]
    return payload


# ── Escrita ──────────────────────────────────────────────────────────────────


def _resolver_evento(event_id: Any) -> CalendarEvent | None:
    if event_id in (None, "", "0"):
        return None
    ev = CalendarEvent.query.get(int(event_id))
    if not ev:
        raise ProducaoValidationError("event_id", "Evento não encontrado.")
    return ev


def _resolver_ficha(sheet_id: Any) -> FigurinoSheet | None:
    if sheet_id in (None, "", "0"):
        return None
    ficha = FigurinoSheet.query.get(int(sheet_id))
    if not ficha:
        raise ProducaoValidationError("figurino_sheet_id", "Ficha de figurino não encontrada.")
    return ficha


def _resolver_responsavel(user_id: Any) -> User | None:
    if user_id in (None, "", "0"):
        return None
    user = User.query.get(int(user_id))
    if not user:
        raise ProducaoValidationError("responsible_id", "Usuário não encontrado.")
    return user


def create_producao(
    *,
    title: str,
    actor: User,
    description: str | None = None,
    event_id: Any = None,
    figurino_sheet_id: Any = None,
    responsible_id: Any = None,
    due_date: Any = None,
    estimated_cost: Any = None,
    quantity: Any = 1,
) -> tuple[FigurinoProducao, str | None]:
    """Abre um pedido de produção. Retorna ``(pedido, aviso_da_agenda)``.

    Commita: `sincronizar_agenda` precisa do id do pedido para carimbar o compromisso do Google,
    e o e-mail ao responsável (disparado pelo endpoint) precisa da PK — `send_async` empacota
    objetos ORM por chave primária e recarrega numa sessão nova.
    """
    titulo = (title or "").strip()
    if not titulo:
        raise ProducaoValidationError("title", "Diga o que precisa ser produzido.")

    try:
        qtd = max(1, int(quantity or 1))
    except (TypeError, ValueError) as exc:
        raise ProducaoValidationError("quantity", "Quantidade inválida.") from exc

    evento = _resolver_evento(event_id)
    ficha = _resolver_ficha(figurino_sheet_id)
    producao = FigurinoProducao(
        title=titulo,
        description=(description or "").strip() or None,
        status=FIGURINO_PROD_SOLICITADO,
        quantity=qtd,
        event_id=evento.id if evento else None,
        figurino_sheet_id=ficha.id if ficha else None,
        requested_by_id=actor.id,
        due_date=_parse_date(due_date, "due_date", "Data do prazo"),
        estimated_cost=_parse_decimal(estimated_cost, "estimated_cost", "Custo previsto"),
    )
    responsavel = _resolver_responsavel(responsible_id)
    if responsavel:
        producao.responsible_id = responsavel.id

    db.session.add(producao)
    db.session.flush()

    registrar_log(
        producao,
        f"Pedido aberto por {actor.name}.",
        actor=actor,
        status_to=FIGURINO_PROD_SOLICITADO,
    )
    audit(
        "criou", entity_type="FigurinoProducao", entity_id=producao.id,
        entity_name=producao.title, detail=f"Pedido de produção de figurino: {producao.title}",
    )
    db.session.commit()

    aviso = sincronizar_agenda(producao)
    db.session.commit()
    return producao, aviso


def update_producao(
    producao: FigurinoProducao, *, actor: User, **campos: Any
) -> tuple[FigurinoProducao, str | None]:
    """Edita os dados do pedido. Só os campos enviados mudam. Retorna ``(pedido, aviso)``."""
    mudancas: list[str] = []

    if "title" in campos:
        titulo = (campos["title"] or "").strip()
        if not titulo:
            raise ProducaoValidationError("title", "Diga o que precisa ser produzido.")
        if titulo != producao.title:
            mudancas.append(f"título → {titulo}")
            producao.title = titulo

    if "description" in campos:
        producao.description = (campos["description"] or "").strip() or None

    if "quantity" in campos:
        try:
            producao.quantity = max(1, int(campos["quantity"] or 1))
        except (TypeError, ValueError) as exc:
            raise ProducaoValidationError("quantity", "Quantidade inválida.") from exc

    if "event_id" in campos:
        ev = _resolver_evento(campos["event_id"])
        novo = ev.id if ev else None
        if novo != producao.event_id:
            mudancas.append(f"evento → {ev.title if ev else 'nenhum'}")
            producao.event_id = novo

    if "figurino_sheet_id" in campos:
        ficha = _resolver_ficha(campos["figurino_sheet_id"])
        producao.figurino_sheet_id = ficha.id if ficha else None

    if "due_date" in campos:
        novo_prazo = _parse_date(campos["due_date"], "due_date", "Data do prazo")
        if novo_prazo != producao.due_date:
            mudancas.append(
                f"prazo → {novo_prazo.strftime('%d/%m/%Y') if novo_prazo else 'sem prazo'}"
            )
            producao.due_date = novo_prazo

    if "estimated_cost" in campos:
        producao.estimated_cost = _parse_decimal(
            campos["estimated_cost"], "estimated_cost", "Custo previsto"
        )

    if "responsible_id" in campos:
        responsavel = _resolver_responsavel(campos["responsible_id"])
        novo = responsavel.id if responsavel else None
        if novo != producao.responsible_id:
            mudancas.append(
                f"responsável → {responsavel.name if responsavel else 'ninguém'}"
            )
            producao.responsible_id = novo

    if mudancas:
        registrar_log(producao, "Pedido atualizado: " + "; ".join(mudancas), actor=actor)
        audit(
            "editou", entity_type="FigurinoProducao", entity_id=producao.id,
            entity_name=producao.title, detail="; ".join(mudancas),
        )
    db.session.commit()

    aviso = sincronizar_agenda(producao)
    db.session.commit()
    return producao, aviso


def mudar_status(
    producao: FigurinoProducao,
    novo_status: str,
    *,
    actor: User,
    motivo: str | None = None,
    observacao: str | None = None,
) -> tuple[FigurinoProducao, str | None]:
    """Move o pedido de estado, validando a transição. Retorna ``(pedido, aviso_da_agenda)``."""
    if novo_status not in FIGURINO_PROD_STATUSES:
        raise ProducaoValidationError("status", "Situação desconhecida.")

    anterior = producao.status
    if novo_status == anterior:
        raise ProducaoValidationError("status", "O pedido já está nessa situação.")
    if novo_status not in TRANSICOES.get(anterior, set()):
        de = FIGURINO_PROD_LABELS.get(anterior, anterior)
        para = FIGURINO_PROD_LABELS.get(novo_status, novo_status)
        raise ProducaoValidationError("status", f"Não dá para ir de “{de}” para “{para}”.")

    if novo_status == FIGURINO_PROD_APROVADO and not pode_aprovar(actor):
        raise ProducaoValidationError("status", "Só um super admin aprova um pedido de figurino.")
    if novo_status != FIGURINO_PROD_APROVADO and not pode_executar(actor):
        raise ProducaoValidationError("status", "Sem permissão para mover este pedido.")

    if novo_status == FIGURINO_PROD_CANCELADO and not (motivo or "").strip():
        raise ProducaoValidationError("motivo", "Diga por que o pedido está sendo cancelado.")

    agora = now_sp()
    producao.status = novo_status

    if novo_status == FIGURINO_PROD_APROVADO:
        producao.approved_by_id = actor.id
        producao.approved_at = agora
        producao.cancelled_at = None
        producao.cancellation_reason = None
    elif novo_status == FIGURINO_PROD_PRONTO:
        producao.done_at = agora
    elif novo_status == FIGURINO_PROD_CANCELADO:
        producao.cancelled_at = agora
        producao.cancellation_reason = (motivo or "").strip()
    elif novo_status in (FIGURINO_PROD_EM_PRODUCAO, FIGURINO_PROD_SOLICITADO):
        # Reabertura: o pedido volta a dar trabalho, então os carimbos de fim saem de cena.
        producao.done_at = None
        producao.cancelled_at = None
        producao.cancellation_reason = None

    rotulo = FIGURINO_PROD_LABELS.get(novo_status, novo_status)
    mensagem = f"Situação alterada para “{rotulo}”."
    if motivo:
        mensagem += f" Motivo: {motivo.strip()}"
    if observacao:
        mensagem += f" {observacao.strip()}"
    registrar_log(
        producao, mensagem, actor=actor, status_from=anterior, status_to=novo_status
    )
    audit(
        "editou", entity_type="FigurinoProducao", entity_id=producao.id,
        entity_name=producao.title, detail=f"{anterior} → {novo_status}",
    )
    db.session.commit()

    aviso = sincronizar_agenda(producao)
    db.session.commit()
    return producao, aviso


def delete_producao(producao: FigurinoProducao, *, actor: User) -> None:
    """Apaga o pedido. Anexos e histórico vão junto (CASCADE); gastos **não** (SET NULL)."""
    if producao.google_event_id:
        from app.calendar.routes import CALENDAR_ID
        from app.calendar.service import delete_event as gcal_delete

        try:
            gcal_delete(CALENDAR_ID, producao.google_event_id)
        except Exception as exc:  # noqa: BLE001 — o compromisso órfão é menos grave que travar
            logger.warning("[figurino-prod] compromisso não removido na exclusão: %s", exc)

    for anexo in list(producao.anexos):
        delete_file(anexo.file_path)

    audit(
        "deletou", entity_type="FigurinoProducao", entity_id=producao.id,
        entity_name=producao.title, detail=f"Pedido de figurino removido por {actor.name}",
    )
    db.session.delete(producao)
    db.session.commit()


# ── Anexos ───────────────────────────────────────────────────────────────────


def add_anexo(
    producao: FigurinoProducao,
    file_obj: Any,
    *,
    kind: str,
    actor: User,
    caption: str | None = None,
    supplier_name: str | None = None,
    amount: Any = None,
) -> FigurinoProducaoAnexo:
    """Anexa uma foto de evolução ou um orçamento de fornecedor ao pedido."""
    if kind not in FIGURINO_ANEXO_KINDS:
        raise ProducaoValidationError("kind", "Tipo de anexo desconhecido.")
    if not file_obj or not getattr(file_obj, "filename", ""):
        raise ProducaoValidationError("file", "Escolha um arquivo.")
    _validar_extensao(file_obj, kind)

    subfolder = (
        SUBFOLDER_ORCAMENTOS if kind == FIGURINO_ANEXO_ORCAMENTO else SUBFOLDER_FOTOS
    )
    url = save_file(file_obj, subfolder)

    anexo = FigurinoProducaoAnexo(
        producao_id=producao.id,
        kind=kind,
        file_path=url,
        original_name=(getattr(file_obj, "filename", "") or "")[:255] or None,
        caption=(caption or "").strip()[:300] or None,
        supplier_name=(supplier_name or "").strip()[:200] or None
        if kind == FIGURINO_ANEXO_ORCAMENTO
        else None,
        amount=_parse_decimal(amount, "amount", "Valor do orçamento")
        if kind == FIGURINO_ANEXO_ORCAMENTO
        else None,
        uploaded_by_id=actor.id,
    )
    db.session.add(anexo)

    if kind == FIGURINO_ANEXO_ORCAMENTO:
        detalhe = f"Orçamento anexado{f' — {anexo.supplier_name}' if anexo.supplier_name else ''}"
        if anexo.amount is not None:
            detalhe += f", {_brl(anexo.amount)}"
        registrar_log(producao, detalhe + ".", actor=actor)
    else:
        # A foto entra no próprio relato: é isso que faz o histórico virar "evolução" e não lista.
        registrar_log(
            producao,
            (caption or "").strip() or "Foto do andamento.",
            actor=actor,
            photo_path=url,
        )

    db.session.commit()
    return anexo


def remove_anexo(anexo: FigurinoProducaoAnexo, *, actor: User) -> None:
    """Remove um anexo e o arquivo correspondente."""
    producao = anexo.producao
    rotulo = "Orçamento" if anexo.kind == FIGURINO_ANEXO_ORCAMENTO else "Foto"
    delete_file(anexo.file_path)
    db.session.delete(anexo)
    registrar_log(producao, f"{rotulo} removido(a).", actor=actor)
    db.session.commit()


# ── Gastos ───────────────────────────────────────────────────────────────────


def vincular_gasto(
    producao: FigurinoProducao, gasto: SpecialExpense, *, actor: User
) -> SpecialExpense:
    """Aponta um gasto extra **existente** para o pedido (FR-032).

    Existir esta operação é o que permite organizar os 40 lançamentos de figurino que já estão no
    banco sem recriar nenhum — recriar perderia data de competência, comprovante e aprovação.
    """
    if gasto.figurino_producao_id == producao.id:
        return gasto
    gasto.figurino_producao_id = producao.id
    registrar_log(
        producao,
        f"Gasto vinculado: {gasto.description} ({_brl(gasto.amount)}).",
        actor=actor,
    )
    audit(
        "editou", entity_type="SpecialExpense", entity_id=gasto.id,
        entity_name=gasto.description,
        detail=f"Vinculado ao pedido de figurino #{producao.id} ({producao.title})",
    )
    db.session.commit()
    return gasto


def desvincular_gasto(gasto: SpecialExpense, *, actor: User) -> SpecialExpense:
    """Desfaz o vínculo entre gasto e pedido."""
    producao = gasto.figurino_producao
    gasto.figurino_producao_id = None
    if producao:
        registrar_log(producao, f"Gasto desvinculado: {gasto.description}.", actor=actor)
    audit(
        "editou", entity_type="SpecialExpense", entity_id=gasto.id,
        entity_name=gasto.description, detail="Desvinculado do pedido de figurino",
    )
    db.session.commit()
    return gasto


def gastos_vinculaveis(producao: FigurinoProducao, *, limite: int = 60) -> list[SpecialExpense]:
    """Gastos que fazem sentido oferecer para vincular a este pedido.

    Prioriza o que é do mesmo evento e o que é da categoria Figurino — é onde estão os
    lançamentos que hoje ficam órfãos.
    """
    q = SpecialExpense.query.filter(
        or_(
            SpecialExpense.figurino_producao_id.is_(None),
            SpecialExpense.figurino_producao_id == producao.id,
        )
    )
    if producao.event_id:
        q = q.filter(
            or_(
                SpecialExpense.event_id == producao.event_id,
                SpecialExpense.category == "Figurino",
            )
        )
    else:
        q = q.filter(SpecialExpense.category == "Figurino")
    return q.order_by(SpecialExpense.expense_date.desc()).limit(limite).all()


# ── Resumo da home ───────────────────────────────────────────────────────────


def resumo_home(user: User) -> dict[str, Any] | None:
    """Painel pessoal "Minhas peças" da tela inicial (FR-050/052).

    Diferente de todos os outros painéis da home, o gate aqui é a **identidade**, não o papel:
    quem tem pedido sob sua responsabilidade vê o painel, seja qual for o papel. Por isso não
    passa por `_effective_has_role` — e por isso o "Ver como" de um super admin não muda o que
    aparece: os pedidos continuam sendo os dele.

    Returns:
        ``None`` quando a pessoa não é responsável por nada — a home simplesmente não desenha o
        painel, que é o contrato das outras seções.
    """
    pedidos = pedidos_do_responsavel(user)
    if not pedidos:
        return None
    return {
        "pending": len(pedidos),
        "atrasados": sum(1 for p in pedidos if p.is_late),
        "items": [
            {
                "id": p.id,
                "title": p.title,
                "status": p.status,
                "status_label": FIGURINO_PROD_LABELS.get(p.status, p.status),
                "event_title": p.event.title if p.event else None,
                "prazo": p.prazo_efetivo.isoformat() if p.prazo_efetivo else None,
                "dias_para_prazo": p.dias_para_prazo,
                "is_late": p.is_late,
            }
            for p in pedidos
        ],
    }
