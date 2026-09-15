"""Núcleo das cobranças e do "sem valor" da Home (feature 299).

Uma **venda** é um evento avulso ou um grupo, sempre representada pelo principal: o valor é o do
principal, e o recebido é a soma dos comprovantes de TODOS os eventos do grupo — cancelados
inclusive, porque o dinheiro entrou (a devolução, se houve, é gasto). Nada é movido de lugar: a soma
é feita na leitura.

Fonte única da Home (`vendas_desde`, em lote, com consultas fixas) e da página do evento
(`resumo_da_venda_do_evento`): as duas mostram o mesmo recebido, o mesmo saldo e o mesmo
vencimento (SC-003). Antes eram duas cópias da regra (`dashboard_service` e `agenda_read`), e as
duas olhavam só o próprio evento — o grupo 344 aparecia cobrando R$ 2.430 já pagos num outro evento
do grupo.

Módulo puro: não usa `flask.request`, recebe `hoje` e `corte` por argumento e não comita. Dinheiro em
`Decimal` do começo ao fim; `float` só na serialização das listas.

Duas definições de "sem valor", de propósito: aqui é vazio, zero ou abaixo de R$ 1,00
(`event_ops.sem_valor_de_venda`); no Financeiro e na Auditoria continua `<= 0` (docs/04).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload

from app import db
from app.calendar.event_ops import sem_valor_de_venda, valor_a_definir, valor_simbolico
from app.calendar.group_ops import group_events
from app.constants import (
    COBRANCA_COR_AMARELO_ATE_DIAS,
    COBRANCA_COR_VERMELHO_ATE_DIAS,
    COR_AMARELO,
    COR_CINZA,
    COR_VERMELHO,
    FOLGA_COBRANCA,
    FORM_COR_AMARELO_ATE_DIAS,
    FORM_COR_VERMELHO_ATE_DIAS,
    MARCADORES_COMPROMISSO_INTERNO,
    MOTIVO_FORA_CANCELADO,
    MOTIVO_FORA_COMPROMISSO_INTERNO,
    MOTIVO_FORA_CORTESIA,
    MOTIVO_FORA_ENSAIO,
    MOTIVO_FORA_LOJA_VIRTUAL,
    NOTA_SEM_SINAL,
    SALDO_VENCE_DIAS_ANTES,
    SELO_ATRASADO,
    SELO_SINAL_PENDENTE,
    SELO_VENCE_EM_1_DIA,
    SELO_VENCE_EM_N_DIAS,
    SELO_VENCE_HOJE,
)
from app.financeiro.vendas_ops import NON_SALE_EVENT_TYPE, contratante_name, is_loja_virtual
from app.models import CalendarEvent, EventClient, EventPayment

CENTAVO = Decimal("0.01")

SITUACAO_FORA = "fora"
SITUACAO_SEM_VALOR = "sem_valor"
SITUACAO_QUITADA = "quitada"
SITUACAO_COM_SALDO = "com_saldo"

ORIGEM_DATA_COMBINADA = "data_combinada"
ORIGEM_PARCELA = "parcela"
ORIGEM_POLITICA = "politica"

ESCOPO_EVENTO = "evento"
ESCOPO_GRUPO_PRINCIPAL = "grupo_principal"
ESCOPO_GRUPO_OUTRO = "grupo_outro"

# Ordem da lista de Cobranças: por cor e, dentro da cor, pelo vencimento. A venda sem sinal "sobe
# com as urgentes" (decisão do dono no checklist): é amarela e vem antes de toda linha cinza.
_ORDEM_DA_COR = {COR_VERMELHO: 0, COR_AMARELO: 1, COR_CINZA: 2}

# A `severity` antiga, que o bundle em cache ainda lê na janela de deploy (R26): sem ErrorBoundary,
# um valor fora da união antiga derrubaria a Home. Sai num deploy futuro (docs/05).
_SEVERITY_ANTIGA = {COR_VERMELHO: "urgent", COR_AMARELO: "warn", COR_CINZA: "info"}
_SEVERITY_ATRASADO = "atrasado"


def _dinheiro(valor: Any) -> Decimal:
    """Valor em reais como `Decimal` de 2 casas (ROUND_HALF_UP); `None` vira zero."""
    return Decimal(str(valor or 0)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _float(valor: Decimal | None) -> float | None:
    """`Decimal` → `float` só na borda (o JSON não serializa `Decimal`)."""
    return float(valor) if valor is not None else None


def _iso(valor: date | datetime | None) -> str | None:
    """Data em ISO para o JSON, ou `None`."""
    return valor.isoformat() if valor is not None else None


@dataclass(frozen=True)
class VendaResumo:
    """Uma venda resumida pelo principal: o que a Home e a página do evento mostram.

    Attributes:
        principal: O evento que guarda a venda (o próprio evento, quando avulso).
        eventos: O principal primeiro e os outros eventos do grupo depois, cancelados inclusive.
        valor: `sale_value` do principal (`None` = vazio).
        recebido: Soma dos comprovantes de todos os eventos do grupo.
        data_do_grupo: 1º evento não cancelado e que não é compromisso interno.
        vencimento: Data em que o saldo vence (ver `vencimento_do_saldo`).
        vencimento_origem: `data_combinada`, `parcela` ou `politica`.
        cliente: Contratante > 1ª cliente > `None` (a tela mostra o título).
        motivo_fora: Por que a venda não entra em nenhuma lista, julgado pelo principal.
        corte: Data de início; `None` na página do evento, que mostra qualquer venda.
        mapa: (soma, quantidade) de comprovantes por evento, para a página listar os dos outros
            eventos do grupo sem outra consulta.
    """

    principal: CalendarEvent
    eventos: tuple[CalendarEvent, ...]
    valor: Decimal | None
    recebido: Decimal
    data_do_grupo: date | None
    vencimento: date | None
    vencimento_origem: str | None
    cliente: str | None
    motivo_fora: str | None
    corte: date | None = None
    mapa: dict[int, tuple[Decimal, int]] = field(default_factory=dict, compare=False)

    @property
    def cortesia(self) -> bool:
        """Cortesia ou permuta: venda tratada como zero de propósito, nunca "sem valor"."""
        return bool(self.principal.is_cortesia_permuta)

    @property
    def saldo(self) -> Decimal | None:
        """Valor menos recebido do grupo; `None` sem valor. Negativo = recebeu acima do valor."""
        return None if self.valor is None else _dinheiro(self.valor - self.recebido)

    @property
    def sem_valor(self) -> bool:
        """Vazio, zero ou abaixo de R$ 1,00 — fora a cortesia."""
        return not self.cortesia and sem_valor_de_venda(self.valor)

    @property
    def a_definir(self) -> bool:
        """Vazio ou zero (a tela mostra "a definir") — fora a cortesia."""
        return not self.cortesia and valor_a_definir(self.valor)

    @property
    def valor_simbolico(self) -> bool:
        """Entre zero e R$ 1,00 (o R$ 0,01 de "segurar a data") — fora a cortesia."""
        return not self.cortesia and valor_simbolico(self.valor)

    @property
    def quitada(self) -> bool:
        """Venda de verdade com menos de R$ 1,00 por receber (a folga de centavos, FR-023)."""
        return not self.sem_valor and not self.cortesia and self.saldo < FOLGA_COBRANCA

    @property
    def sinal_pendente(self) -> bool:
        """Recebido abaixo da metade menos R$ 1,00 (FR-022).

        Não vale com data combinada nem com cronograma de parcelas: as datas acertadas com a
        cliente substituem a regra da metade (decisão do dono no plan).
        """
        if self.sem_valor or self.cortesia:
            return False
        if self.principal.payment_due_date or self.principal.installments:
            return False
        return self.recebido < self.valor / 2 - FOLGA_COBRANCA

    @property
    def eventos_vivos(self) -> int:
        """Quantos eventos do grupo não estão cancelados (a marca "grupo de N eventos")."""
        return sum(1 for evento in self.eventos if not evento.cancelled_at)

    @property
    def situacao(self) -> str:
        """`fora`, `sem_valor`, `quitada` ou `com_saldo` — em que lista a venda entra."""
        antes_do_corte = self.corte is not None and (
            self.data_do_grupo is None or self.data_do_grupo < self.corte
        )
        if self.motivo_fora or antes_do_corte:
            return SITUACAO_FORA
        if self.sem_valor:
            return SITUACAO_SEM_VALOR
        if self.quitada:
            return SITUACAO_QUITADA
        return SITUACAO_COM_SALDO


# ── Primitivas ────────────────────────────────────────────────────────────────────────────────


def comprovantes_por_evento(ids: list[int]) -> dict[int, tuple[Decimal, int]]:
    """Soma e quantidade de comprovantes por evento, numa consulta só.

    Comprovante sem valor conta R$ 0 na soma e 1 na quantidade (a página lista o comprovante).
    """
    if not ids:
        return {}
    linhas = (
        db.session.query(
            EventPayment.event_id,
            func.coalesce(func.sum(EventPayment.amount), 0),
            func.count(EventPayment.id),
        )
        .filter(EventPayment.event_id.in_(ids))
        .group_by(EventPayment.event_id)
        .all()
    )
    return {evento_id: (_dinheiro(total), int(quantos)) for evento_id, total, quantos in linhas}


def recebido_da_venda(
    eventos: list[CalendarEvent] | tuple[CalendarEvent, ...], mapa: dict[int, tuple[Decimal, int]]
) -> Decimal:
    """Recebido do grupo: os comprovantes de todos os eventos, cancelados inclusive (FR-001)."""
    return sum((mapa.get(evento.id, (Decimal("0"), 0))[0] for evento in eventos), Decimal("0"))


def principal_da_venda(event: CalendarEvent) -> CalendarEvent:
    """O evento que guarda a venda: o principal do grupo, ou o próprio evento."""
    if event.group_leader_id and event.group_leader is not None:
        return event.group_leader
    return event


def compromisso_interno(event: CalendarEvent) -> bool:
    """Título que começa com o laranja (🟧/🟠): ensaio, visita técnica, gravação — não é venda."""
    return (event.title or "").lstrip().startswith(MARCADORES_COMPROMISSO_INTERNO)


def data_do_grupo(eventos: list[CalendarEvent] | tuple[CalendarEvent, ...]) -> date | None:
    """Data do 1º evento do grupo que não está cancelado e não é compromisso interno (FR-002)."""
    datas = [
        evento.start_at.date()
        for evento in eventos
        if evento.start_at and not evento.cancelled_at and not compromisso_interno(evento)
    ]
    return min(datas) if datas else None


def motivo_fora_da_venda(principal: CalendarEvent) -> str | None:
    """Por que a venda fica fora das duas listas, sempre pelo principal (FR-006, FR-019).

    O tipo vazio NÃO é ensaio: a regra antiga `event_type != 'ENSAIO'` em SQL descartava o `NULL`, e
    o evento 395 (venda de R$ 35 mil sem tipo) sumiria.
    """
    if principal.cancelled_at:
        return MOTIVO_FORA_CANCELADO
    if principal.event_type == NON_SALE_EVENT_TYPE:
        return MOTIVO_FORA_ENSAIO
    if compromisso_interno(principal):
        return MOTIVO_FORA_COMPROMISSO_INTERNO
    if principal.is_cortesia_permuta:
        return MOTIVO_FORA_CORTESIA
    if is_loja_virtual(principal):
        return MOTIVO_FORA_LOJA_VIRTUAL
    return None


def _primeira_parcela_descoberta(parcelas: list[Any], recebido: Decimal) -> date | None:
    """Data da 1ª parcela que o recebido do grupo ainda não cobre, somando pela ordem das datas.

    A folga de centavos vale aqui também: o sinal pago com R$ 0,50 a menos cobre a parcela.
    """
    acumulado = Decimal("0")
    for parcela in sorted(parcelas, key=lambda p: p.due_date or date.max):
        acumulado += _dinheiro(parcela.amount)
        if parcela.due_date and acumulado - recebido >= FOLGA_COBRANCA:
            return parcela.due_date
    return None


def vencimento_do_saldo(
    principal: CalendarEvent, data_grupo: date | None, recebido: Decimal
) -> tuple[date | None, str | None]:
    """Quando o saldo vence (FR-021): data combinada > 1ª parcela descoberta > 2 dias antes.

    A data combinada vale qualquer que seja a forma de pagamento. Nos outros dois casos o
    vencimento nunca fica antes da data da venda: a venda fechada hoje para um evento amanhã vence
    hoje ("Vence hoje"), e não nasce "Atrasado".
    """
    if principal.payment_due_date:
        return principal.payment_due_date, ORIGEM_DATA_COMBINADA
    data = _primeira_parcela_descoberta(list(principal.installments or []), recebido)
    origem = ORIGEM_PARCELA
    if data is None:
        if data_grupo is None:
            return None, None
        data = data_grupo - timedelta(days=SALDO_VENCE_DIAS_ANTES)
        origem = ORIGEM_POLITICA
    if principal.sale_date and data < principal.sale_date:
        data = principal.sale_date
    return data, origem


def resumir_venda(
    principal: CalendarEvent,
    eventos: list[CalendarEvent],
    mapa: dict[int, tuple[Decimal, int]],
    *,
    corte: date | None = None,
) -> VendaResumo:
    """Monta o `VendaResumo` de uma venda, sem I/O (os comprovantes chegam no `mapa`)."""
    recebido = recebido_da_venda(eventos, mapa)
    data_grupo = data_do_grupo(eventos)
    vencimento, origem = vencimento_do_saldo(principal, data_grupo, recebido)
    return VendaResumo(
        principal=principal,
        eventos=tuple(eventos),
        valor=None if principal.sale_value is None else _dinheiro(principal.sale_value),
        recebido=recebido,
        data_do_grupo=data_grupo,
        vencimento=vencimento,
        vencimento_origem=origem,
        cliente=contratante_name(principal),
        motivo_fora=motivo_fora_da_venda(principal),
        corte=corte,
        mapa=mapa,
    )


# ── Régua, selo e ordem ───────────────────────────────────────────────────────────────────────


def cor_por_distancia(dias: int, *, vermelho_ate: int, amarelo_ate: int) -> str:
    """Cor pela distância em dias; o passado (dias negativos) é sempre vermelho."""
    if dias <= vermelho_ate:
        return COR_VERMELHO
    if dias <= amarelo_ate:
        return COR_AMARELO
    return COR_CINZA


def _dias_ate_vencimento(venda: VendaResumo, hoje: date) -> int:
    """Dias até o vencimento (negativo = venceu); sem vencimento, conta como bem distante."""
    if venda.vencimento is None:
        return COBRANCA_COR_AMARELO_ATE_DIAS + 1
    return (venda.vencimento - hoje).days


def cor_da_cobranca(venda: VendaResumo, hoje: date) -> str:
    """Cor da cobrança (FR-026): vermelho até 2 dias; amarelo com sinal pendente ou 3–30; cinza."""
    dias = _dias_ate_vencimento(venda, hoje)
    if dias <= COBRANCA_COR_VERMELHO_ATE_DIAS:
        return COR_VERMELHO
    if venda.sinal_pendente:
        return COR_AMARELO
    return cor_por_distancia(
        dias,
        vermelho_ate=COBRANCA_COR_VERMELHO_ATE_DIAS,
        amarelo_ate=COBRANCA_COR_AMARELO_ATE_DIAS,
    )


def _vence_em(dias: int) -> str:
    """ "Vence em N dias", com o singular."""
    return SELO_VENCE_EM_1_DIA if dias == 1 else SELO_VENCE_EM_N_DIAS.format(dias=dias)


def selo_da_cobranca(venda: VendaResumo, hoje: date) -> str:
    """Selo em pt-BR (FR-025): no vermelho, o do prazo; no amarelo sem sinal, "Sinal pendente"."""
    dias = _dias_ate_vencimento(venda, hoje)
    cor = cor_da_cobranca(venda, hoje)
    if cor == COR_VERMELHO and dias < 0:
        return SELO_ATRASADO
    if cor == COR_VERMELHO and dias == 0:
        return SELO_VENCE_HOJE
    if cor == COR_AMARELO and venda.sinal_pendente:
        return SELO_SINAL_PENDENTE
    return _vence_em(dias)


def nota_da_cobranca(venda: VendaResumo, hoje: date) -> str | None:
    """ "sem sinal" só na linha vermelha com sinal pendente: o selo já é o do prazo."""
    if venda.sinal_pendente and cor_da_cobranca(venda, hoje) == COR_VERMELHO:
        return NOTA_SEM_SINAL
    return None


def chave_de_ordem(venda: VendaResumo, hoje: date) -> tuple[int, date, date, int]:
    """Ordem da lista: cor, vencimento mais antigo, data do grupo e, no empate, o id."""
    return (
        _ORDEM_DA_COR[cor_da_cobranca(venda, hoje)],
        venda.vencimento or date.max,
        venda.data_do_grupo or date.max,
        venda.principal.id,
    )


# ── Lote da Home ──────────────────────────────────────────────────────────────────────────────


def _por_data(eventos: list[CalendarEvent]) -> list[CalendarEvent]:
    """Eventos do grupo pela data (os sem data por último)."""
    return sorted(eventos, key=lambda evento: evento.start_at or datetime.max)


def vendas_desde(corte: date) -> list[VendaResumo]:
    """Todas as vendas (avulsas e principais) com evento desde o corte, com consultas fixas.

    Uma consulta de principais com os satélites, as clientes e as parcelas carregados em lote, e
    uma soma de comprovantes para todos os ids: nada de `group_events` nem `is_group_leader` por
    linha (R10). A data do grupo é reconferida no Python (`situacao`): um grupo com o principal em
    02/06 e outro evento vivo em 31/05 fica fora, porque a venda é de maio.
    """
    principais = (
        CalendarEvent.query.options(
            selectinload(CalendarEvent.satellites),
            selectinload(CalendarEvent.event_clients).joinedload(EventClient.client),
            joinedload(CalendarEvent.client),
            selectinload(CalendarEvent.installments),
        )
        .filter(
            CalendarEvent.group_leader_id.is_(None),
            CalendarEvent.cancelled_at.is_(None),
            CalendarEvent.start_at >= datetime.combine(corte, time.min),
        )
        .all()
    )
    ids = [evento.id for principal in principais for evento in (principal, *principal.satellites)]
    mapa = comprovantes_por_evento(ids)
    return [
        resumir_venda(principal, [principal, *_por_data(principal.satellites)], mapa, corte=corte)
        for principal in principais
    ]


def _grupo_comercial(venda: VendaResumo) -> dict[str, Any] | None:
    """A marca "grupo de N eventos" (contando os não cancelados), ou `None` no avulso."""
    if venda.eventos_vivos < 2:
        return None
    return {"nome": venda.principal.group_display_name, "eventos": venda.eventos_vivos}


def _severity_antiga(cor: str, dias: int) -> str:
    """A `severity` da união antiga, derivada da cor (contrato `dashboard-comercial.md`)."""
    return _SEVERITY_ATRASADO if dias < 0 else _SEVERITY_ANTIGA[cor]


def linha_da_cobranca(venda: VendaResumo, hoje: date) -> dict[str, Any]:
    """Uma linha de Cobranças: as chaves antigas (bundle em cache) mais as novas do contrato."""
    principal = venda.principal
    dias = _dias_ate_vencimento(venda, hoje)
    cor = cor_da_cobranca(venda, hoje)
    return {
        "event_id": principal.id,
        "event_title": principal.title,
        "start_at": _iso(principal.start_at),
        "sale": _float(venda.valor),
        "received": _float(venda.recebido),
        "saldo": _float(venda.saldo),
        "severity": _severity_antiga(cor, dias),
        "due_date": _iso(venda.vencimento),
        "titulo": principal.title,
        "cliente": venda.cliente,
        "data_evento": _iso(venda.data_do_grupo),
        "vencimento": _iso(venda.vencimento),
        "vencimento_origem": venda.vencimento_origem,
        "dias_ate_vencimento": dias,
        "sinal_pendente": venda.sinal_pendente,
        "severidade": cor,
        "selo": selo_da_cobranca(venda, hoje),
        "nota": nota_da_cobranca(venda, hoje),
        "grupo_comercial": _grupo_comercial(venda),
    }


def listar_cobrancas(vendas: list[VendaResumo], hoje: date) -> list[dict[str, Any]]:
    """Cobranças da Home: toda venda com saldo de R$ 1,00 ou mais, na ordem do FR-026."""
    com_saldo = [venda for venda in vendas if venda.situacao == SITUACAO_COM_SALDO]
    com_saldo.sort(key=lambda venda: chave_de_ordem(venda, hoje))
    return [linha_da_cobranca(venda, hoje) for venda in com_saldo]


def linha_sem_valor(venda: VendaResumo, hoje: date) -> dict[str, Any]:
    """Uma linha de "Evento sem valor de venda", com a régua da 298 (vermelho até 7 dias)."""
    dias = (venda.data_do_grupo - hoje).days
    return {
        "event_id": venda.principal.id,
        "titulo": venda.principal.title,
        "cliente": venda.cliente,
        "grupo_comercial": _grupo_comercial(venda),
        "data_evento": _iso(venda.data_do_grupo),
        "dias_ate_o_evento": dias,
        "valor": _float(venda.valor),
        "a_definir": venda.a_definir,
        "valor_simbolico": venda.valor_simbolico,
        "recebido": _float(venda.recebido),
        "severidade": cor_por_distancia(
            dias, vermelho_ate=FORM_COR_VERMELHO_ATE_DIAS, amarelo_ate=FORM_COR_AMARELO_ATE_DIAS
        ),
    }


def resumo_por_cor(linhas: list[dict[str, Any]]) -> dict[str, Any]:
    """Contagem por cor e o `para_agir` (vermelho + amarelo), o número do card e do total."""
    por_cor = {COR_VERMELHO: 0, COR_AMARELO: 0, COR_CINZA: 0}
    for linha in linhas:
        por_cor[linha["severidade"]] += 1
    return {"por_cor": por_cor, "para_agir": por_cor[COR_VERMELHO] + por_cor[COR_AMARELO]}


def resumo_das_cobrancas(linhas: list[dict[str, Any]]) -> dict[str, Any]:
    """O `cobrancas_resumo`: contagem por cor, `para_agir` e o dinheiro em aberto de todas as linhas.

    O total soma em `Decimal` (a partir do `saldo` já arredondado) e vira `float` só no fim.
    """
    total = sum((Decimal(str(linha["saldo"])) for linha in linhas), Decimal("0"))
    return {**resumo_por_cor(linhas), "total_em_aberto": float(_dinheiro(total))}


def listar_sem_valor(vendas: list[VendaResumo], hoje: date) -> dict[str, Any]:
    """Bloco `sem_valor`: os dois grupos da 298 e a contagem por cor.

    "Ainda vai acontecer" inclui hoje e vem com o mais próximo primeiro; "já aconteceu" vem com o
    mais recente primeiro (FR-008).
    """
    linhas = [
        linha_sem_valor(venda, hoje) for venda in vendas if venda.situacao == SITUACAO_SEM_VALOR
    ]
    a_acontecer = [linha for linha in linhas if linha["dias_ate_o_evento"] >= 0]
    ja_aconteceu = [linha for linha in linhas if linha["dias_ate_o_evento"] < 0]
    a_acontecer.sort(key=lambda linha: (linha["dias_ate_o_evento"], linha["event_id"]))
    ja_aconteceu.sort(key=lambda linha: (-linha["dias_ate_o_evento"], linha["event_id"]))
    return {**resumo_por_cor(linhas), "a_acontecer": a_acontecer, "ja_aconteceu": ja_aconteceu}


# ── Página do evento ──────────────────────────────────────────────────────────────────────────


def resumo_da_venda_do_evento(event: CalendarEvent) -> VendaResumo:
    """A venda de que o evento faz parte, com a mesma conta da Home (uma consulta a mais)."""
    principal = principal_da_venda(event)
    eventos = group_events(principal)
    mapa = comprovantes_por_evento([evento.id for evento in eventos])
    return resumir_venda(principal, eventos, mapa)


def escopo_do_evento(venda: VendaResumo, event: CalendarEvent) -> str:
    """`evento` (avulso), `grupo_principal` ou `grupo_outro` — a tela escolhe o texto por ele."""
    if len(venda.eventos) < 2:
        return ESCOPO_EVENTO
    return ESCOPO_GRUPO_PRINCIPAL if event.id == venda.principal.id else ESCOPO_GRUPO_OUTRO


def pode_copiar_cobranca(venda: VendaResumo, event: CalendarEvent, hoje: date) -> bool:
    """A mensagem de cobrança só sai do principal (ou do avulso), a partir do vencimento (FR-003).

    Nunca em cortesia, valor simbólico, evento sem valor ou venda quitada. No outro evento do grupo,
    não: a mensagem sairia com os personagens e a data do evento aberto, e quem cobra é o principal.
    """
    return (
        event.id == venda.principal.id
        and venda.motivo_fora is None
        and not venda.sem_valor
        and venda.saldo >= FOLGA_COBRANCA
        and venda.vencimento is not None
        and venda.vencimento <= hoje
    )


def outros_do_grupo(venda: VendaResumo, evento_aberto_id: int) -> list[dict[str, Any]]:
    """Comprovantes dos outros eventos do grupo, um resumo por evento (no satélite, o principal).

    Só entram os eventos que têm comprovante; lista vazia no avulso.
    """
    linhas = []
    for evento in venda.eventos:
        total, quantos = venda.mapa.get(evento.id, (Decimal("0"), 0))
        if evento.id == evento_aberto_id or quantos == 0:
            continue
        linhas.append(
            {
                "event_id": evento.id,
                "event_title": evento.title,
                "start_at": _iso(evento.start_at),
                "total": float(total),
                "quantidade": quantos,
            }
        )
    return linhas
