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
    FIGURINO_ANEXO_FOTO,
    FIGURINO_ANEXO_KINDS,
    FIGURINO_ANEXO_ORCAMENTO,
    FIGURINO_KIND_COMPRA,
    FIGURINO_KIND_FICHA,
    FIGURINO_KIND_LABELS,
    FIGURINO_KIND_MANUTENCAO,
    FIGURINO_KIND_PRODUCAO,
    FIGURINO_KINDS,
    FIGURINO_PROD_ABERTOS,
    FIGURINO_PROD_APROVADO,
    FIGURINO_PROD_CANCELADO,
    FIGURINO_PROD_FLUXOS,
    FIGURINO_PROD_LABELS,
    FIGURINO_PROD_PRONTO,
    FIGURINO_PROD_SOLICITADO,
    FIGURINO_PROD_STATUSES,
    FIGURINO_SEV_ESPERA,
    FIGURINO_SEV_IMPEDE,
    FIGURINO_SEV_LABELS,
    FIGURINO_SEVERIDADES,
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

def _transicoes_do_fluxo(fluxo: list[str]) -> dict[str, set[str]]:
    """Monta as transições válidas a partir da ordem do fluxo daquele tipo.

    Derivar em vez de digitar duas tabelas evita o bug clássico de mudar o fluxo num lugar e
    esquecer o outro. Regras fixas em cima da ordem: dá para avançar um passo, cancelar de
    qualquer estado aberto, voltar do último passo (ficou pronto e voltou com problema) e
    reabrir um pedido cancelado.
    """
    saltos: dict[str, set[str]] = {}
    for i, estado in enumerate(fluxo):
        destinos: set[str] = set()
        if i + 1 < len(fluxo):
            destinos.add(fluxo[i + 1])
            destinos.add(FIGURINO_PROD_CANCELADO)
        saltos[estado] = destinos
    saltos[fluxo[-1]] = {fluxo[-2]} if len(fluxo) > 1 else set()
    saltos[FIGURINO_PROD_CANCELADO] = {fluxo[0]}
    return saltos


#: Transições permitidas por tipo de pedido. Produção passa por aprovação; manutenção não.
TRANSICOES_POR_TIPO: dict[str, dict[str, set[str]]] = {
    kind: _transicoes_do_fluxo(fluxo) for kind, fluxo in FIGURINO_PROD_FLUXOS.items()
}

#: Compatibilidade: o fluxo de produção continua acessível como `TRANSICOES`.
TRANSICOES = TRANSICOES_POR_TIPO[FIGURINO_KIND_PRODUCAO]


def transicoes_de(producao: FigurinoProducao) -> set[str]:
    """Para onde este pedido pode ir a partir de onde está, respeitando o tipo dele."""
    tabela = TRANSICOES_POR_TIPO.get(producao.kind, TRANSICOES)
    return tabela.get(producao.status, set())


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


def _erro_titulo(kind: str) -> str:
    """A pergunta que o campo de título faz muda com o tipo — e o erro tem que fazer a mesma."""
    return {
        FIGURINO_KIND_MANUTENCAO: "Diga o que precisa ser resolvido.",
        FIGURINO_KIND_COMPRA: "Diga o que precisa ser comprado.",
        FIGURINO_KIND_FICHA: "Diga o nome do personagem da ficha.",
    }.get(kind, "Diga o que precisa ser produzido.")


def _fluxo_de(producao: FigurinoProducao) -> list[str]:
    """Os estados que este pedido percorre, na ordem, conforme o tipo dele."""
    return FIGURINO_PROD_FLUXOS.get(producao.kind, FIGURINO_PROD_FLUXOS[FIGURINO_KIND_PRODUCAO])


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


def pode_executar_pedido(user: User | None, producao: FigurinoProducao) -> bool:
    """Quem pode mexer NESTE pedido: a oficina sempre, e o responsável pela própria compra.

    A exceção existe porque uma compra pode (e costuma) ser entregue a quem não é do figurino —
    quem pediu a tinta do cenário é do comercial. Sem isto, ninguém marcaria "comprei" e "chegou"
    fora da oficina, e o pedido de compra ficaria parado esperando um papel que não tem nada a ver
    com ele. Vale só em ``kind="compra"``: produção e manutenção continuam sendo da oficina.
    """
    if pode_executar(user):
        return True
    return bool(
        user
        and producao.kind == FIGURINO_KIND_COMPRA
        and producao.responsible_id
        and producao.responsible_id == user.id
    )


def responsaveis_elegiveis(kind: str | None = None) -> list[User]:
    """Quem pode ser designado responsável, conforme o tipo do pedido.

    Produção e manutenção são trabalho de oficina — a lista é a equipe de figurino. Compra não:
    qualquer pessoa da equipe interna pode ficar encarregada de comprar alguma coisa, e limitar a
    lista ao figurino tornaria o campo "responsável" inútil justamente onde ele foi pedido.
    """
    usuarios = User.query.filter(User.is_active.is_(True)).order_by(User.name.asc()).all()
    if kind == FIGURINO_KIND_COMPRA:
        return [u for u in usuarios if pode_abrir(u)]
    return [
        u for u in usuarios
        if any(r.name in (RoleName.FIGURINO, RoleName.SUPERADMIN) for r in u.roles)
    ]


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
    if producao.kind == FIGURINO_KIND_COMPRA:
        return f"🛒 Comprar: {producao.title}"
    return f"🧵 Figurino: {producao.title}"


def _descricao_agenda(producao: FigurinoProducao) -> str:
    linhas = [producao.description or ""]
    if producao.event:
        linhas.append(f"Evento: {producao.event.title}")
    if producao.figurino_sheet:
        linhas.append(f"Figurino: {producao.figurino_sheet.character_name}")
    if producao.quantity and producao.quantity > 1:
        linhas.append(f"Quantidade: {producao.quantity}")
    linhas.append("")
    linhas.append(
        "Pedido de compra — Plataforma Manto."
        if producao.kind == FIGURINO_KIND_COMPRA
        else "Pedido de produção de figurino — Plataforma Manto."
    )
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
    kind: str | None = None,
    somente_abertos: bool = False,
    responsible_id: int | None = None,
    event_id: int | None = None,
    figurino_sheet_id: int | None = None,
    busca: str | None = None,
) -> list[FigurinoProducao]:
    """Lista pedidos com os filtros da tela da oficina.

    Ordem: prazo mais próximo primeiro, e quem não tem prazo vai para o fim — quem abre a fila
    quer ver o que aperta, não o que foi cadastrado primeiro.
    """
    q = _base_query()
    if status:
        q = q.filter(FigurinoProducao.status == status)
    if kind:
        q = q.filter(FigurinoProducao.kind == kind)
    if somente_abertos:
        q = q.filter(FigurinoProducao.status.in_(FIGURINO_PROD_ABERTOS))
    if responsible_id:
        q = q.filter(FigurinoProducao.responsible_id == responsible_id)
    if event_id:
        q = q.filter(FigurinoProducao.event_id == event_id)
    if figurino_sheet_id:
        q = q.filter(FigurinoProducao.figurino_sheet_id == figurino_sheet_id)
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


def pedidos_sem_dono(kinds: list[str] | None = None) -> list[FigurinoProducao]:
    """Pedidos abertos que ninguém assumiu — a caixa de entrada do setor de figurino.

    Manutenção nasce sem responsável quase sempre: quem relata o defeito é quem recebeu o
    feedback do evento, não quem vai consertar. Sem esta lista, o pedido ficaria esperando alguém
    lembrar de abrir a fila.

    Args:
        kinds: Limita aos tipos informados; ``None`` traz todos.
    """
    itens = [p for p in list_producoes(somente_abertos=True) if p.responsible_id is None]
    if kinds is None:
        return itens
    return [p for p in itens if p.kind in kinds]


# ── Alerta por ficha ─────────────────────────────────────────────────────────


def alertas_por_ficha(sheet_ids: list[int] | None = None) -> dict[int, dict[str, Any]]:
    """Manutenções abertas por ficha de figurino (feature 225b).

    É o que faz o defeito relatado numa festa chegar em quem vai separar o figurino da próxima:
    a ficha carrega o aviso, e o elenco do evento também. Sem isto, "tem uma peça solta dentro do
    boneco" continua sendo uma conversa que ninguém lembra na hora certa.

    Args:
        sheet_ids: Limita a consulta a estas fichas. ``None`` traz todas — a lista de figurinos
            precisa de todas de uma vez, e são poucas linhas (só manutenção aberta).

    Returns:
        ``{sheet_id: {"abertas": int, "impede_uso": bool, "titulos": [str, ...]}}``. Ficha sem
        manutenção aberta simplesmente não aparece no dicionário.
    """
    q = FigurinoProducao.query.filter(
        FigurinoProducao.kind == FIGURINO_KIND_MANUTENCAO,
        FigurinoProducao.status.in_(FIGURINO_PROD_ABERTOS),
        FigurinoProducao.figurino_sheet_id.isnot(None),
    )
    if sheet_ids:
        q = q.filter(FigurinoProducao.figurino_sheet_id.in_(sheet_ids))

    saida: dict[int, dict[str, Any]] = {}
    for p in q.all():
        entry = saida.setdefault(
            p.figurino_sheet_id, {"abertas": 0, "impede_uso": False, "titulos": []}
        )
        entry["abertas"] += 1
        entry["titulos"].append(p.title)
        if p.severity == FIGURINO_SEV_IMPEDE:
            entry["impede_uso"] = True
    return saida


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
        "kind": producao.kind,
        "kind_label": FIGURINO_KIND_LABELS.get(producao.kind, producao.kind),
        "severity": producao.severity,
        "severity_label": FIGURINO_SEV_LABELS.get(producao.severity or ""),
        "impede_uso": producao.impede_uso,
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
    kind: str = FIGURINO_KIND_PRODUCAO,
    severity: str | None = None,
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
    # A ordem das validações segue a ordem dos campos NA TELA, não a ordem em que dá jeito de
    # escrever: quem esquece dois campos recebe primeiro o erro do de cima e conserta de cima
    # para baixo. Em manutenção a tela pede ficha e gravidade antes do título.
    tipo = (kind or FIGURINO_KIND_PRODUCAO).strip()
    if tipo not in FIGURINO_KINDS:
        raise ProducaoValidationError("kind", "Tipo de pedido desconhecido.")
    e_manutencao = tipo == FIGURINO_KIND_MANUTENCAO

    evento = _resolver_evento(event_id)
    ficha = _resolver_ficha(figurino_sheet_id)
    gravidade = (severity or "").strip() or None

    if e_manutencao:
        if ficha is None:
            raise ProducaoValidationError(
                "figurino_sheet_id", "Escolha de qual figurino é o conserto."
            )
        # A gravidade é obrigatória na manutenção porque é ela que decide se a peça pode ir para
        # o próximo evento — a informação que faz o registro valer alguma coisa.
        if gravidade not in FIGURINO_SEVERIDADES:
            raise ProducaoValidationError(
                "severity", "Diga se a peça ainda pode ser usada assim como está."
            )
    else:
        gravidade = None

    titulo = (title or "").strip()
    if not titulo:
        raise ProducaoValidationError("title", _erro_titulo(tipo))

    try:
        qtd = max(1, int(quantity or 1))
    except (TypeError, ValueError) as exc:
        raise ProducaoValidationError("quantity", "Quantidade inválida.") from exc

    producao = FigurinoProducao(
        title=titulo,
        description=(description or "").strip() or None,
        status=FIGURINO_PROD_SOLICITADO,
        kind=tipo,
        severity=gravidade,
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

    rotulo_tipo = FIGURINO_KIND_LABELS[tipo].lower()
    abertura = f"Pedido de {rotulo_tipo} aberto por {actor.name}."
    if gravidade:
        abertura += f" Gravidade: {FIGURINO_SEV_LABELS[gravidade].lower()}."
    registrar_log(
        producao, abertura, actor=actor, status_to=FIGURINO_PROD_SOLICITADO
    )
    audit(
        "criou", entity_type="FigurinoProducao", entity_id=producao.id,
        entity_name=producao.title,
        detail=f"Pedido de {rotulo_tipo} de figurino: {producao.title}",
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
            raise ProducaoValidationError("title", _erro_titulo(producao.kind))
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
        if producao.is_manutencao and ficha is None:
            raise ProducaoValidationError(
                "figurino_sheet_id", "Um conserto precisa dizer de qual figurino é."
            )
        producao.figurino_sheet_id = ficha.id if ficha else None

    if "severity" in campos and producao.is_manutencao:
        nova = (campos["severity"] or "").strip() or None
        if nova not in FIGURINO_SEVERIDADES:
            raise ProducaoValidationError(
                "severity", "Diga se a peça ainda pode ser usada assim como está."
            )
        if nova != producao.severity:
            mudancas.append(f"gravidade → {FIGURINO_SEV_LABELS[nova].lower()}")
            producao.severity = nova

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


def criar_solicitacao_ficha(
    actor: User,
    personagem: str,
    observacao: str | None = None,
    origem: str | None = None,
) -> tuple[FigurinoProducao, str | None]:
    """Abre um pedido do tipo FICHA a partir da busca (feature 237).

    É o caminho do botão "Solicitar ficha" do FigurinoPicker: sem valores, sem compra, sem
    responsável — só o nome do personagem, a observação de quem pediu e a tela de origem
    (registrada na descrição, para a oficina saber o contexto). Reusa `create_producao`
    inteiro (validações, log, e-mail ao setor quando nasce sem dono).

    Args:
        actor: Quem está solicitando (vira ``requested_by``).
        personagem: Nome do personagem da ficha (vira o título do pedido).
        observacao: Texto livre opcional de quem pediu.
        origem: Rota/tela de onde a busca foi aberta (opcional).

    Returns:
        Tupla ``(pedido, aviso_da_agenda)`` — mesmo contrato de `create_producao`.

    Raises:
        ProducaoValidationError: personagem vazio.
    """
    partes = []
    if (observacao or "").strip():
        partes.append(observacao.strip())
    if (origem or "").strip():
        partes.append(f"Solicitada pela busca em: {origem.strip()}")
    return create_producao(
        title=(personagem or "").strip(),
        actor=actor,
        description="\n\n".join(partes) or None,
        kind=FIGURINO_KIND_FICHA,
    )


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
    if novo_status not in transicoes_de(producao):
        de = FIGURINO_PROD_LABELS.get(anterior, anterior)
        para = FIGURINO_PROD_LABELS.get(novo_status, novo_status)
        extra = (
            " Manutenção não passa por aprovação."
            if producao.is_manutencao and novo_status == FIGURINO_PROD_APROVADO
            else ""
        )
        raise ProducaoValidationError(
            "status", f"Não dá para ir de “{de}” para “{para}”.{extra}"
        )

    if novo_status == FIGURINO_PROD_APROVADO and not pode_aprovar(actor):
        rotulo = "de compra" if producao.is_compra else "de figurino"
        raise ProducaoValidationError("status", f"Só um super admin aprova um pedido {rotulo}.")
    if novo_status != FIGURINO_PROD_APROVADO and not pode_executar_pedido(actor, producao):
        raise ProducaoValidationError("status", "Sem permissão para mover este pedido.")

    if novo_status == FIGURINO_PROD_CANCELADO and not (motivo or "").strip():
        raise ProducaoValidationError("motivo", "Diga por que o pedido está sendo cancelado.")

    # Feature 237: o pedido de ficha só conclui apontando para a ficha criada — é o elo que
    # faz o solicitante encontrá-la; concluir sem vínculo deixaria o loop aberto de novo.
    if (
        novo_status == FIGURINO_PROD_PRONTO
        and producao.kind == FIGURINO_KIND_FICHA
        and not producao.figurino_sheet_id
    ):
        raise ProducaoValidationError(
            "figurino_sheet_id",
            "Vincule a ficha criada antes de concluir o pedido de ficha.",
        )

    agora = now_sp()
    producao.status = novo_status

    # O estado final feliz é o ÚLTIMO do fluxo do tipo — "pronto" na produção e na manutenção,
    # "recebido" na compra. Derivar em vez de listar evita o bug de acrescentar um fluxo novo e
    # esquecer de carimbar `done_at` nele.
    estado_final = _fluxo_de(producao)[-1]

    if novo_status == FIGURINO_PROD_APROVADO:
        producao.approved_by_id = actor.id
        producao.approved_at = agora
        producao.cancelled_at = None
        producao.cancellation_reason = None
    elif novo_status == estado_final:
        producao.done_at = agora
    elif novo_status == FIGURINO_PROD_CANCELADO:
        producao.cancelled_at = agora
        producao.cancellation_reason = (motivo or "").strip()
    else:
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


def validar_fotos(files: list[Any]) -> list[Any]:
    """Filtra e valida as fotos que vieram no formulário de abertura (feature 225g).

    Roda **antes** de o pedido existir, e valida a lista INTEIRA: se a terceira foto for um
    arquivo que não serve, quem pediu recebe o erro com o pedido ainda em mãos, em vez de um
    pedido salvo pela metade com duas fotos e uma mensagem de erro.

    Returns:
        Só os arquivos realmente preenchidos — campo de upload vazio manda ``FileStorage`` sem
        nome, e tratá-lo como foto criaria anexo fantasma.
    """
    validos = [f for f in files if f and (getattr(f, "filename", "") or "").strip()]
    for file_obj in validos:
        _validar_extensao(file_obj, FIGURINO_ANEXO_FOTO)
    return validos


def add_fotos_iniciais(
    producao: FigurinoProducao, files: list[Any], *, actor: User
) -> int:
    """Anexa as fotos que chegaram junto com a abertura do pedido. Retorna quantas entraram.

    Diferente de `add_anexo`, **não escreve uma linha de histórico por foto**: num pedido que
    acabou de nascer isso empilharia N linhas "Foto do andamento." embaixo da linha de abertura,
    dizendo a mesma coisa N vezes. As fotos aparecem na grade de Fotos do detalhe, e o histórico
    ganha uma linha só, com a contagem.

    A compressão é a de `storage.save_file` — a mesma de todo upload do app (lado máximo de
    1200px, JPEG qualidade 85). Aqui não se inventa outro padrão.
    """
    if not files:
        return 0

    for file_obj in files:
        url = save_file(file_obj, SUBFOLDER_FOTOS)
        db.session.add(
            FigurinoProducaoAnexo(
                producao_id=producao.id,
                kind=FIGURINO_ANEXO_FOTO,
                file_path=url,
                original_name=(getattr(file_obj, "filename", "") or "")[:255] or None,
                uploaded_by_id=actor.id,
            )
        )

    plural = "fotos" if len(files) > 1 else "foto"
    registrar_log(producao, f"{len(files)} {plural} anexada(s) na abertura.", actor=actor)
    db.session.commit()
    return len(files)


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


def _serialize_para_home(p: FigurinoProducao) -> dict[str, Any]:
    return {
        "id": p.id,
        "title": p.title,
        "status": p.status,
        "status_label": FIGURINO_PROD_LABELS.get(p.status, p.status),
        "kind": p.kind,
        "kind_label": FIGURINO_KIND_LABELS.get(p.kind, p.kind),
        "impede_uso": p.impede_uso,
        "figurino_sheet_name": (
            p.figurino_sheet.character_name if p.figurino_sheet else None
        ),
        "event_title": p.event.title if p.event else None,
        "prazo": p.prazo_efetivo.isoformat() if p.prazo_efetivo else None,
        "dias_para_prazo": p.dias_para_prazo,
        "is_late": p.is_late,
    }


def resumo_setor(user: User) -> dict[str, Any] | None:
    """Caixa de entrada do setor de figurino: pedidos abertos que ninguém assumiu (225b).

    Diferente do painel pessoal, este é por **papel** — é o setor que precisa ver o que chegou.
    Existe porque manutenção quase sempre nasce órfã: quem relata o defeito é quem recebeu o
    feedback do evento, não quem vai consertar.
    """
    if not pode_executar(user):
        return None
    # Compra sem dono é assunto de quem aprova, não da oficina: a compra pode não ter nada a ver
    # com figurino, e enfiar tinta de cenário na caixa de entrada da costureira transformaria o
    # painel em ruído. Mesmo recorte do e-mail de setor (`equipe_figurino`).
    kinds = (
        FIGURINO_KINDS if pode_aprovar(user)
        else [FIGURINO_KIND_PRODUCAO, FIGURINO_KIND_MANUTENCAO]
    )
    pedidos = pedidos_sem_dono(kinds)
    if not pedidos:
        return None
    return {
        "pending": len(pedidos),
        "impedem_uso": sum(1 for p in pedidos if p.impede_uso),
        "items": [_serialize_para_home(p) for p in pedidos],
    }


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
        "items": [_serialize_para_home(p) for p in pedidos],
    }


def equipe_figurino(kind: str | None = None) -> list[User]:
    """Quem recebe o aviso de pedido novo sem dono: o setor que precisa agir, com e-mail.

    Mesmo desenho de `gastos_ops._financeiro_and_superadmin_users`: avisa o **setor**, não uma
    pessoa. O aviso individual só existe quando alguém é designado responsável.

    Em ``kind="compra"`` o setor é só o Superadmin — é ele quem aprova, e a compra pode não ter
    nada a ver com a oficina (tinta de cenário, material de escritório). Mandar para a equipe de
    figurino um pedido que não é dela transformaria o aviso em ruído, e aviso ignorado não avisa.
    """
    from app.models import Role

    papeis = (
        [RoleName.SUPERADMIN]
        if kind == FIGURINO_KIND_COMPRA
        else [RoleName.FIGURINO, RoleName.SUPERADMIN]
    )
    return (
        User.query.join(User.roles)
        .filter(
            Role.name.in_(papeis),
            User.is_active.is_(True),
            User.email.isnot(None),
        )
        .distinct()
        .all()
    )
