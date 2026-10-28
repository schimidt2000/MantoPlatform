"""A nota pedida chega ao Superadmin (feature 323).

Quando a vendedora liga "Precisa de nota fiscal", a venda passa a ter uma nota **a emitir** com quem
pediu e quando — em qualquer porta (criação, "Editar tudo", card Comercial). Até a 323 só a criação
fazia isso: ligar o chip na edição deixava a venda "com nota" e ninguém era avisado.

A venda guarda os dados que a emissão precisa (documento do tomador, ISS retido, município,
referência, observações), o Superadmin vê a tarefa na tela inicial com a discriminação pronta e
recebe um e-mail por nota.

Regras de concorrência: `acompanhar_pedido` roda com a linha do evento travada pelos núcleos
(`comercial_ops.estado_da_venda` → `travar_evento`), então o clique duplo espera e encontra a nota do
primeiro. O aviso é reivindicado por UPDATE condicional e sai depois do commit da venda — nunca com a
trava na mão, e falha de envio não desfaz a venda.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from flask import current_app
from sqlalchemy import and_, update
from sqlalchemy.orm import selectinload

from app import db
from app.constants import EDUCAMANTO_TITLE_PREFIX, RoleName, now_sp
from app.models import CalendarEvent, Client, EventClient, EventInvoice, Role, User

logger = logging.getLogger(__name__)

STATUS_A_EMITIR = "a_emitir"
RELACAO_CONTRATANTE = "Contratante"

DOC_CNPJ_DIGITOS = 14
DOC_CPF_DIGITOS = 11
MUNICIPIO_MAX = 120
REFERENCIA_MAX = 120
OBSERVACOES_MAX = 1000

MSG_DOC_INVALIDO = "Informe o CNPJ com 14 dígitos ou o CPF com 11."
MSG_MUNICIPIO_FALTANDO = "Informe o município onde o serviço é prestado."
MSG_OBSERVACOES_LONGAS = f"Use no máximo {OBSERVACOES_MAX} caracteres."

CAMPO_DOC = "nota_tomador_doc"
CAMPO_MUNICIPIO = "nota_municipio"
CAMPO_OBSERVACOES = "nota_observacoes"


class NotaInvalida(Exception):
    """Dados da nota recusados; `fields` vai direto ao envelope `json_error`."""

    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__("Corrija os campos destacados")
        self.fields = fields


@dataclass(frozen=True)
class DadosDaNota:
    """Os cinco dados da nota, já normalizados (vazio = `None`)."""

    tomador_doc: str | None
    iss_retido: bool
    municipio: str | None
    referencia: str | None
    observacoes: str | None


# ── Entrada ─────────────────────────────────────────────────────────────────────────────────


def _texto(valor: Any, limite: int) -> str | None:
    texto = str(valor or "").strip()
    return texto[:limite] or None


def ler_dados_da_nota(raw: Any) -> DadosDaNota | None:
    """Converte a chave `nota` do corpo. `None` (chave ausente) = não mexer no que está gravado.

    Raises:
        NotaInvalida: documento sem 11/14 dígitos, ISS retido sem município ou observações longas.
    """
    if raw is None or not isinstance(raw, dict):
        return None
    doc = re.sub(r"\D", "", str(raw.get("tomador_doc") or "")) or None
    iss = bool(raw.get("iss_retido"))
    municipio = _texto(raw.get("municipio"), MUNICIPIO_MAX) if iss else None
    observacoes_brutas = str(raw.get("observacoes") or "").strip()

    erros: dict[str, str] = {}
    if doc and len(doc) not in (DOC_CNPJ_DIGITOS, DOC_CPF_DIGITOS):
        erros[CAMPO_DOC] = MSG_DOC_INVALIDO
    if iss and not municipio:
        erros[CAMPO_MUNICIPIO] = MSG_MUNICIPIO_FALTANDO
    if len(observacoes_brutas) > OBSERVACOES_MAX:
        erros[CAMPO_OBSERVACOES] = MSG_OBSERVACOES_LONGAS
    if erros:
        raise NotaInvalida(erros)

    return DadosDaNota(
        tomador_doc=doc,
        iss_retido=iss,
        municipio=municipio,
        referencia=_texto(raw.get("referencia"), REFERENCIA_MAX),
        observacoes=observacoes_brutas or None,
    )


def _dados_gravados(event: Any) -> DadosDaNota:
    return DadosDaNota(
        tomador_doc=event.nota_tomador_doc or None,
        iss_retido=bool(event.nota_iss_retido),
        municipio=event.nota_municipio or None,
        referencia=event.nota_referencia or None,
        observacoes=event.nota_observacoes or None,
    )


def dados_mudariam(event: Any, dados: DadosDaNota | None) -> bool:
    """O corpo alteraria os dados gravados? Entra no "venda mudaria" do cancelado (306)."""
    return dados is not None and dados != _dados_gravados(event)


def contratante(event: Any) -> Client | None:
    """O cliente contratante: o vínculo marcado "Contratante"; sem ele, o `client_id` legado."""
    for vinculo in getattr(event, "event_clients", None) or []:
        if vinculo.relationship_type == RELACAO_CONTRATANTE and vinculo.client is not None:
            return vinculo.client
    return event.client


def gravar_dados_da_nota(event: Any, dados: DadosDaNota | None) -> None:
    """Grava os dados da nota na venda. Sem commit; `None` não mexe em nada (FR-017).

    O cliente se completa à parte (`completar_documento_do_cliente`), depois que os vínculos de
    cliente da gravação estiverem refeitos.
    """
    if dados is None:
        return
    event.nota_tomador_doc = dados.tomador_doc
    event.nota_iss_retido = dados.iss_retido
    event.nota_municipio = dados.municipio
    event.nota_referencia = dados.referencia
    event.nota_observacoes = dados.observacoes


def completar_documento_do_cliente(event: Any, dados: DadosDaNota | None) -> None:
    """O documento informado completa o cadastro do contratante só se o campo estiver vazio — a
    base de clientes nunca é sobrescrita por uma venda (regra da 119). Sem commit.

    Chamar DEPOIS de refazer os vínculos de cliente: o "Editar tudo" apaga e recria os vínculos
    na mesma gravação, e antes disso o contratante lido seria o antigo.
    """
    if dados is None or not dados.tomador_doc:
        return
    # O DELETE em massa dos vínculos não passa pela coleção já carregada: relê do banco.
    db.session.flush()
    db.session.expire(event, ["event_clients", "client"])
    cliente = contratante(event)
    doc = dados.tomador_doc
    if cliente is None:
        return
    if len(doc) == DOC_CNPJ_DIGITOS and not (cliente.cnpj or "").strip():
        cliente.cnpj = formatar_doc(doc)
    elif len(doc) == DOC_CPF_DIGITOS and not (cliente.cpf or "").strip():
        cliente.cpf = formatar_doc(doc)


# ── O pedido ────────────────────────────────────────────────────────────────────────────────


def acompanhar_pedido(event: Any, *, pedida_por_id: int | None, nota_antes: bool = False) -> None:
    """Acompanha o chip "Precisa de nota fiscal" depois de gravado. Sem commit.

    Chamar com o evento travado (`estado_da_venda`). Ligado e sem nenhuma nota → nasce a nota a
    emitir com o valor da venda (FR-001). Ligado com a nota pedida única ainda a emitir → o valor
    acompanha a venda (FR-016). Desligado AGORA (`nota_antes` e chip apagado) → exclui as notas a
    emitir; a emitida é documento contábil e fica (FR-013). Só na transição: a venda que nunca teve
    o chip pode ter nota lançada à mão pelo Financeiro (`POST …/invoices`), e salvar a venda não
    pode apagá-la. Cancelado e satélite não mudam: o cancelado tem a regra da 306 e o satélite não
    tem venda.
    """
    if event.is_cancelled or event.is_satellite:
        return
    notas = EventInvoice.query.filter_by(event_id=event.id).all()
    if not event.with_invoice:
        if not nota_antes:
            return
        for nota in notas:
            if nota.status == STATUS_A_EMITIR:
                db.session.delete(nota)
    elif not notas:
        db.session.add(EventInvoice(
            event_id=event.id,
            amount=event.sale_value,
            status=STATUS_A_EMITIR,
            pedida_por_id=pedida_por_id,
            pedida_em=now_sp(),
        ))
    elif len(notas) == 1 and notas[0].status == STATUS_A_EMITIR and notas[0].file is None:
        notas[0].amount = event.sale_value
    db.session.flush()
    # A coleção `event.invoices` já pode estar carregada; o detalhe devolvido lê dela.
    db.session.expire(event, ["invoices"])


def carimbar_pedido_da_criacao(event: Any, *, pedida_por_id: int | None) -> None:
    """Na criação, `_create_event_row` já criou a nota a emitir: carimba quem pediu. Sem commit."""
    agora = now_sp()
    for nota in EventInvoice.query.filter_by(event_id=event.id, status=STATUS_A_EMITIR).all():
        if nota.pedida_por_id is None and nota.file is None:
            nota.pedida_por_id = pedida_por_id
            nota.pedida_em = agora


# ── O aviso ─────────────────────────────────────────────────────────────────────────────────


def superadmins_com_email() -> list[User]:
    """Superadmins ativos com e-mail — os destinatários do aviso."""
    return (
        User.query.join(User.roles)
        .filter(Role.name == RoleName.SUPERADMIN, User.is_active.is_(True), User.email.isnot(None))
        .distinct()
        .all()
    )


def reivindicar_avisos(event_id: int) -> list[int]:
    """Marca `aviso_enviado_em` das notas pedidas sem aviso e devolve os ids. Commita.

    O UPDATE condicional é a barreira contra o segundo e-mail: duas gravações seguidas (ou duas
    abas) disputam a mesma linha e só uma a leva.
    """
    resultado = db.session.execute(
        update(EventInvoice)
        .where(and_(
            EventInvoice.event_id == event_id,
            EventInvoice.status == STATUS_A_EMITIR,
            EventInvoice.pedida_por_id.isnot(None),
            EventInvoice.aviso_enviado_em.is_(None),
        ))
        .values(aviso_enviado_em=now_sp())
        .returning(EventInvoice.id)
    )
    ids = [linha[0] for linha in resultado]
    db.session.commit()
    return ids


def avisar_notas_pedidas(event_id: int) -> int:
    """Depois do commit da venda: um e-mail por nota pedida, uma vez. Nunca levanta.

    Returns:
        Quantas notas tiveram o aviso disparado (0 também quando não há Superadmin com e-mail).
    """
    from app.email_service import send_async, send_nota_pedida_email

    try:
        ids = reivindicar_avisos(event_id)
        destinatarios = superadmins_com_email() if ids else []
        for nota_id in ids:
            if destinatarios:
                send_async(send_nota_pedida_email, EventInvoice.query.get(nota_id), destinatarios)
        return len(ids) if destinatarios else 0
    except Exception as exc:  # noqa: BLE001 — o aviso é depois do fato; a venda já está gravada
        db.session.rollback()
        logger.warning("[nota-pedida] aviso do evento %s falhou: %s", event_id, exc)
        return 0


# ── Leitura: tomador, vencimento, discriminação, painel ─────────────────────────────────────


def formatar_doc(doc: str | None) -> str | None:
    """Máscara de CNPJ (00.000.000/0000-00) ou CPF (000.000.000-00); outro tamanho volta cru."""
    digitos = re.sub(r"\D", "", doc or "")
    if len(digitos) == DOC_CNPJ_DIGITOS:
        return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"
    if len(digitos) == DOC_CPF_DIGITOS:
        return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"
    return (doc or "").strip() or None


def doc_do_cliente(cliente: Client | None) -> str | None:
    """CNPJ do cadastro; sem CNPJ, CPF — só dígitos."""
    if cliente is None:
        return None
    for doc in (cliente.cnpj, cliente.cpf):
        digitos = re.sub(r"\D", "", doc or "")
        if digitos:
            return digitos
    return None


def tomador(event: Any) -> dict[str, str | None]:
    """Quem recebe a nota: nome, documento (o da venda ou o do cadastro), e-mail e endereço."""
    cliente = contratante(event)
    return {
        "nome": (cliente.company or cliente.name) if cliente else None,
        "doc": event.nota_tomador_doc or doc_do_cliente(cliente),
        "email": cliente.email if cliente else None,
        "endereco": cliente.address if cliente else None,
    }


def vencimento(event: Any, hoje: date | None = None) -> date | None:
    """Faturado: a data de vencimento; senão a primeira parcela a receber a partir de hoje."""
    if event.payment_due_date:
        return event.payment_due_date
    hoje = hoje or now_sp().date()
    datas = [
        p.due_date for p in (event.installments or [])
        if p.due_date and not p.received and p.due_date >= hoje
    ]
    return min(datas) if datas else None


def _o_que_e(event: Any) -> str:
    """A linha do serviço, como o dono escreve nas notas — o título do Google traz "(TIPO)" e os
    personagens, que não vão para a nota."""
    dia = event.start_at.strftime("%d/%m") if event.start_at else ""
    if (event.title or "").startswith(EDUCAMANTO_TITLE_PREFIX):
        return f"Apresentações Educamanto — {dia}".rstrip(" —")
    return f"Personagens para evento {dia}".rstrip()


def discriminacao(event: Any, hoje: date | None = None) -> str:
    """O corpo da nota, pronto para copiar (research R6)."""
    linhas = []
    if event.nota_referencia:
        linhas.append(event.nota_referencia)
    linhas.append(_o_que_e(event))
    venc = vencimento(event, hoje)
    if venc:
        linhas.append(f"Vencimento: {venc.strftime('%d/%m')}")
    linhas.append(current_app.config.get("NOTA_DADOS_BANCARIOS") or "")
    if event.nota_observacoes:
        linhas.append(event.nota_observacoes)
    return "\n".join(linha for linha in linhas if linha)


def nome_de_quem_pediu(nota: EventInvoice) -> str | None:
    """Quem ligou o chip; nota do legado (sem o carimbo) mostra o vendedor da venda."""
    pessoa = nota.pedida_por or (nota.event.seller if nota.event else None)
    return pessoa.name if pessoa else None


def _iso(valor: Any) -> str | None:
    return valor.isoformat() if valor else None


def _valor(valor: Decimal | None) -> float | None:
    return float(valor) if valor is not None else None


def serializar_item(nota: EventInvoice, hoje: date) -> dict[str, Any]:
    """Uma linha do painel Notas a emitir (contracts §3)."""
    event = nota.event
    return {
        "id": nota.id,
        "event_id": event.id,
        "event_title": event.title,
        "event_start_at": _iso(event.start_at),
        "amount": _valor(nota.amount),
        "issue_date": _iso(nota.issue_date),
        "tomador": tomador(event),
        "iss_retido": bool(event.nota_iss_retido),
        "municipio": event.nota_municipio,
        "referencia": event.nota_referencia,
        "observacoes": event.nota_observacoes,
        "pedida_por": nome_de_quem_pediu(nota),
        "pedida_em": _iso(nota.pedida_em),
        "vencimento": _iso(vencimento(event, hoje)),
        "discriminacao": discriminacao(event, hoje),
        "cancelado": bool(event.is_cancelled),
    }


def painel() -> dict[str, Any]:
    """Todas as notas a emitir, a pedida há mais tempo primeiro; legado no fim, pela data do evento."""
    notas = (
        EventInvoice.query.filter(EventInvoice.status == STATUS_A_EMITIR)
        .join(CalendarEvent, EventInvoice.event_id == CalendarEvent.id)
        # Evento, clientes, parcelas e quem pediu num punhado de consultas, não um por linha.
        .options(
            selectinload(EventInvoice.event).selectinload(CalendarEvent.event_clients)
            .selectinload(EventClient.client),
            selectinload(EventInvoice.event).selectinload(CalendarEvent.installments),
            selectinload(EventInvoice.event).selectinload(CalendarEvent.client),
            selectinload(EventInvoice.event).selectinload(CalendarEvent.seller),
            selectinload(EventInvoice.pedida_por),
        )
        .order_by(
            EventInvoice.pedida_em.is_(None),
            EventInvoice.pedida_em.asc(),
            CalendarEvent.start_at.asc(),
        )
        .all()
    )
    hoje = now_sp().date()
    return {"itens": [serializar_item(nota, hoje) for nota in notas]}


def serializar_dados(event: Any) -> dict[str, Any]:
    """`venda.nota` do detalhe do evento (contracts §2)."""
    return {
        "tomador_doc": event.nota_tomador_doc,
        "doc_do_cliente": doc_do_cliente(contratante(event)),
        "iss_retido": bool(event.nota_iss_retido),
        "municipio": event.nota_municipio,
        "referencia": event.nota_referencia,
        "observacoes": event.nota_observacoes,
    }

