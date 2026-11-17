"""Venda atribuída (feature 351): qual contato pago trouxe cada venda — a porta única da atribuição.

A regra (spec FR-003; research R4): um contato pago vale para a venda quando o evento foi criado **depois**
dele, a data da venda cai entre o dia do contato e 45 dias depois, e a venda é de 01/06/2026 em diante. Entre
os válidos, vale o **mais recente** (no empate: conversa > ficha > origem da ficha). A venda vai para a frente
da **campanha** do contato; a frente do evento continua lida só por `comando_ops.frente_venda_sql`.

De onde vêm os contatos pagos (o que a `main` grava em 17/11/2026):

* **conversa** — `conversa_anuncios` (tipo anúncio) da conversa da ficha, com o momento real (UTC);
* **ficha** — o primeiro e o último anúncio gravados na ficha pela 334 (`anuncio_origem_*`, `anuncio_recente_*`);
* **utm** — a origem paga da ficha (`utm_source` da Meta ou do Google, como as 153 fichas do Tintim); sem data
  do contato, vale a entrada na base — conservador de propósito: só a ficha nova atribui.

Quando a 348 ligar o evento à conversa (`conversa_id`), o contato pago da conversa ligada vence a busca pela
ficha: a troca é em `atribuir_vendas`, e só nela. Todo número atribuído (frente, lista, funil com custo, card,
cliente novo) passa por aqui.

Funções puras (sem `flask.request`); quem chama decide o papel.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_

from app import db
from app.constants import (
    ATRIBUICAO_DESDE,
    ATRIBUICAO_JANELA_DIAS,
    INCREMENTALIDADE_PREMISSA,
    MARKETING_FRENTES,
    TZ_SP,
)
from app.conversas.constantes import CONTATO_ANUNCIO, PLATAFORMA_DO_ANUNCIO
from app.marketing import comando_ops, desempenho_ops
from app.models import (
    AnuncioMeta,
    CalendarEvent,
    Client,
    Conversa,
    ConversaAnuncio,
    EventClient,
    MarketingAdMetric,
    MarketingCampaignMetric,
    MarketingPost,
    MarketingPostAnuncio,
)

FONTE_CONVERSA = "conversa"
FONTE_FICHA = "ficha"
FONTE_UTM = "utm"
# Empate de momento: o dado mais direto vence (a conversa tem o momento real; a origem da ficha, não).
_PRIORIDADE = {FONTE_CONVERSA: 2, FONTE_FICHA: 1, FONTE_UTM: 0}
# A venda atribuída é pouca (dezenas por mês): a lista cobre o período inteiro na prática (SC-002).
VENDAS_NA_LISTA = 500
SEMANAS_DO_PAINEL = (4, 12, 26)
SEMANAS_PADRAO = 12


@dataclass(frozen=True)
class Toque:
    """Um contato pago de uma ficha. `momento` em UTC naive (o relógio de `created_at`)."""

    client_id: int
    momento: datetime
    fonte: str
    platform: str | None
    anuncio_id: str | None
    campaign_id: str | None
    campaign_name: str | None
    frente: str | None


@dataclass
class _Venda:
    event_id: int
    titulo: str
    sale_date: date
    sale_value: Decimal
    criado: datetime
    frente_venda: str
    clientes: set[int]


@dataclass(frozen=True)
class VendaAtribuida:
    """A venda e o contato pago que a trouxe. `frente` = a da campanha do contato (ou `None`)."""

    event_id: int
    titulo: str
    sale_date: date
    sale_value: Decimal
    frente_venda: str
    toque: Toque

    @property
    def frente(self) -> str | None:
        return self.toque.frente


# ── Relógios ──────────────────────────────────────────────────────────────────────────────────


def _dia_sp(momento_utc: datetime) -> date:
    return momento_utc.replace(tzinfo=UTC).astimezone(TZ_SP).date()


def _sp_para_utc(momento_sp: datetime) -> datetime:
    return momento_sp.replace(tzinfo=TZ_SP).astimezone(UTC).replace(tzinfo=None)


# ── Frente da campanha do contato ────────────────────────────────────────────────────────────


class _Campanhas:
    """A frente de uma campanha pela regra do painel; o `utm_campaign` casa pelo nome normalizado."""

    def __init__(self) -> None:
        self.correcoes = comando_ops.correcoes_de_frente()
        self.por_nome: dict[str, tuple[str, str]] = {}
        for platform, cid, nome in (
            db.session.query(
                MarketingCampaignMetric.platform,
                MarketingCampaignMetric.campaign_id,
                MarketingCampaignMetric.campaign_name,
            )
            .distinct()
            .all()
        ):
            self.por_nome.setdefault(desempenho_ops.normalize_campaign_name(nome), (platform, cid))

    def frente(self, platform: str | None, campaign_id: str | None, nome: str | None) -> str | None:
        return comando_ops.frente_da_campanha(
            platform or "", campaign_id or "", nome, self.correcoes
        )

    def do_utm(self, nome: str | None) -> tuple[str | None, str | None]:
        """`(campaign_id, frente)` de um `utm_campaign`."""
        casada = self.por_nome.get(desempenho_ops.normalize_campaign_name(nome))
        if casada is None:
            return None, comando_ops.frente_por_prefixo(nome)
        return casada[1], self.frente(casada[0], casada[1], nome)


# ── Contatos pagos ───────────────────────────────────────────────────────────────────────────


def _anuncios(ids: Iterable[str | None]) -> dict[str, AnuncioMeta]:
    chaves = sorted({i for i in ids if i})
    if not chaves:
        return {}
    return {
        a.anuncio_id: a for a in AnuncioMeta.query.filter(AnuncioMeta.anuncio_id.in_(chaves)).all()
    }


def _toque_meta(
    client_id: int,
    momento: datetime,
    fonte: str,
    anuncio_id: str | None,
    anuncio: AnuncioMeta | None,
    c: _Campanhas,
) -> Toque:
    cid, nome = (anuncio.campanha_id, anuncio.campanha_nome) if anuncio else (None, None)
    frente = c.frente(PLATAFORMA_DO_ANUNCIO, cid, nome) if anuncio else None
    return Toque(client_id, momento, fonte, PLATAFORMA_DO_ANUNCIO, anuncio_id, cid, nome, frente)


def _toques_da_conversa(ids: list[int], c: _Campanhas) -> list[Toque]:
    linhas = (
        db.session.query(Conversa.client_id, ConversaAnuncio.momento, ConversaAnuncio.anuncio_id)
        .join(Conversa, Conversa.id == ConversaAnuncio.conversa_id)
        .filter(ConversaAnuncio.tipo == CONTATO_ANUNCIO, Conversa.client_id.in_(ids))
        .all()
    )
    anuncios = _anuncios(ad for _, _, ad in linhas)
    return [
        _toque_meta(cl, m, FONTE_CONVERSA, ad, anuncios.get(ad or ""), c) for cl, m, ad in linhas
    ]


def _toques_da_ficha(clientes: list[Client], c: _Campanhas) -> list[Toque]:
    pares = [
        (cl.id, ad, em)
        for cl in clientes
        for ad, em in (
            (cl.anuncio_origem_id, cl.anuncio_origem_em),
            (cl.anuncio_recente_id, cl.anuncio_recente_em),
        )
        if ad and em
    ]
    anuncios = _anuncios(ad for _, ad, _ in pares)
    return [_toque_meta(cl, em, FONTE_FICHA, ad, anuncios.get(ad), c) for cl, ad, em in pares]


def _toques_da_origem(clientes: list[Client], c: _Campanhas) -> list[Toque]:
    saida = []
    for cl in clientes:
        platform = desempenho_ops.platform_from_utm_source(cl.utm_source)
        entrada = desempenho_ops._entrada(cl)
        # A ficha com anúncio de origem ganhou o utm da própria 334 (o mesmo anúncio, sem o id): contá-lo
        # de novo daria um contato "mais novo" sem anúncio, e a peça perderia a venda.
        if platform is None or entrada is None or cl.anuncio_origem_id:
            continue
        cid, frente = c.do_utm(cl.utm_campaign)
        saida.append(
            Toque(
                cl.id,
                _sp_para_utc(entrada),
                FONTE_UTM,
                platform,
                None,
                cid,
                cl.utm_campaign,
                frente,
            )
        )
    return saida


def toques_pagos(client_ids: Iterable[int]) -> dict[int, list[Toque]]:
    """Todos os contatos pagos das fichas, por ficha — três consultas, nunca uma por ficha."""
    ids = sorted({i for i in client_ids if i})
    if not ids:
        return {}
    campanhas = _Campanhas()
    clientes = Client.query.filter(Client.id.in_(ids)).all()
    toques: dict[int, list[Toque]] = defaultdict(list)
    for t in (
        _toques_da_conversa(ids, campanhas)
        + _toques_da_ficha(clientes, campanhas)
        + _toques_da_origem(clientes, campanhas)
    ):
        toques[t.client_id].append(t)
    return toques


# ── Vendas e a regra ─────────────────────────────────────────────────────────────────────────


def _vendas(inicio: date, fim: date | None, client_ids: set[int] | None = None) -> list[_Venda]:
    """Vendas (a mesma régua do custo misto) do período, com as fichas de cada uma."""
    inicio = max(inicio, ATRIBUICAO_DESDE)
    if fim is not None and inicio > fim:
        return []
    query = db.session.query(
        CalendarEvent.id,
        CalendarEvent.title,
        CalendarEvent.sale_date,
        CalendarEvent.sale_value,
        CalendarEvent.created_at,
        comando_ops.frente_venda_sql(),
        CalendarEvent.client_id,
    ).filter(CalendarEvent.sale_date >= inicio, *comando_ops.filtro_de_venda())
    if fim is not None:
        query = query.filter(CalendarEvent.sale_date <= fim)
    if client_ids is not None:
        da_ficha = db.session.query(EventClient.event_id).filter(
            EventClient.client_id.in_(client_ids)
        )
        query = query.filter(
            or_(CalendarEvent.client_id.in_(client_ids), CalendarEvent.id.in_(da_ficha))
        )
    vendas = {
        eid: _Venda(eid, titulo or "", dia, Decimal(valor), criado, frente, {cl} if cl else set())
        for eid, titulo, dia, valor, criado, frente, cl in query.all()
    }
    if vendas:
        for eid, cl in (
            db.session.query(EventClient.event_id, EventClient.client_id)
            .filter(EventClient.event_id.in_(list(vendas)))
            .all()
        ):
            vendas[eid].clientes.add(cl)
    return list(vendas.values())


def _toque_da_venda(venda: _Venda, toques: list[Toque]) -> Toque | None:
    """A regra (FR-003): fato depois do contato, venda até 45 dias depois dele; vale o último."""
    validos = [
        t
        for t in toques
        if t.momento <= venda.criado
        and 0 <= (venda.sale_date - _dia_sp(t.momento)).days <= ATRIBUICAO_JANELA_DIAS
    ]
    if not validos:
        return None
    return max(validos, key=lambda t: (t.momento, _PRIORIDADE[t.fonte]))


def atribuir_vendas(
    inicio: date, fim: date | None, *, client_ids: set[int] | None = None
) -> list[VendaAtribuida]:
    """As vendas do período (pela data da venda) que um contato pago trouxe. `fim=None` = sem limite."""
    vendas = _vendas(inicio, fim, client_ids)
    toques = toques_pagos(c for v in vendas for c in v.clientes)
    saida = []
    for v in vendas:
        toque = _toque_da_venda(v, [t for c in v.clientes for t in toques.get(c, [])])
        if toque is not None:
            saida.append(
                VendaAtribuida(
                    v.event_id, v.titulo, v.sale_date, v.sale_value, v.frente_venda, toque
                )
            )
    return saida


# ── Painel por frente ────────────────────────────────────────────────────────────────────────


def regra(inicio: date) -> dict[str, Any]:
    """A regra declarada na tela, e se o período começa antes do corte (atribuição parcial)."""
    return {
        "janela_dias": ATRIBUICAO_JANELA_DIAS,
        "incrementalidade": str(INCREMENTALIDADE_PREMISSA),
        "desde": ATRIBUICAO_DESDE.isoformat(),
        "parcial": inicio < ATRIBUICAO_DESDE,
    }


def por_frente(inicio: date, fim: date) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Vendas e faturamento atribuídos por frente da campanha; e os de campanha sem frente."""
    frentes: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"vendas": 0, "faturamento": Decimal(0)}
    )
    sem_frente = {"vendas": 0, "faturamento": Decimal(0)}
    for va in atribuir_vendas(inicio, fim):
        alvo = frentes[va.frente] if va.frente in MARKETING_FRENTES else sem_frente
        alvo["vendas"] += 1
        alvo["faturamento"] += va.sale_value
    return dict(frentes), sem_frente


def custos_atribuidos(gasto: Decimal, vendas: int) -> tuple[Decimal | None, Decimal | None]:
    """`(custo por venda atribuída, o mesmo com o desconto de incrementalidade)`."""
    if not vendas or gasto <= 0:
        return None, None
    return gasto / vendas, gasto / (vendas * INCREMENTALIDADE_PREMISSA)


# ── Lista das vendas atribuídas ──────────────────────────────────────────────────────────────


def _contato(t: Toque, anuncio: AnuncioMeta | None) -> dict[str, Any]:
    return {
        "fonte": t.fonte,
        "em": t.momento.replace(tzinfo=UTC).astimezone(TZ_SP).replace(tzinfo=None).isoformat(),
        "platform": t.platform,
        "campanha": t.campaign_name,
        "anuncio_id": t.anuncio_id,
        "anuncio": anuncio.nome if anuncio else None,
    }


def lista_vendas(inicio: date, fim: date, *, com_valor: bool) -> dict[str, Any]:
    """As vendas atribuídas do período, da mais nova para a mais antiga (até 100), e o total.

    O valor de cada venda só sai para quem vê dinheiro de venda (Superadmin real) — quem chama decide.
    """
    vendas = sorted(
        atribuir_vendas(inicio, fim), key=lambda v: (v.sale_date, v.event_id), reverse=True
    )
    mostradas = vendas[:VENDAS_NA_LISTA]
    anuncios = _anuncios(v.toque.anuncio_id for v in mostradas)
    return {
        "vendas": [
            {
                "event_id": v.event_id,
                "titulo": v.titulo,
                "sale_date": v.sale_date.isoformat(),
                "valor": comando_ops.q2(v.sale_value) if com_valor else None,
                "frente_venda": v.frente_venda,
                "frente": v.frente if v.frente in MARKETING_FRENTES else None,
                "frente_nome": MARKETING_FRENTES.get(v.frente or ""),
                "contato": _contato(v.toque, anuncios.get(v.toque.anuncio_id or "")),
            }
            for v in mostradas
        ],
        "vendas_total": len(vendas),
    }


def periodo_do_painel(start: str | None, end: str | None, weeks: str | None) -> tuple[date, date]:
    """O período do Desempenho: `start&end` ou as últimas N semanas fechadas, no relógio de São Paulo.

    Raises:
        comando_ops.ComandoError: 400 em data inválida ou invertida.
    """
    if start and end:
        try:
            inicio, fim = date.fromisoformat(start), date.fromisoformat(end)
        except ValueError:
            raise comando_ops.ComandoError(
                "Datas inválidas (use AAAA-MM-DD).", field="start"
            ) from None
        if inicio > fim:
            raise comando_ops.ComandoError(
                "A data inicial precisa ser anterior à final.", field="start"
            )
        return inicio, fim
    semanas = (
        int(weeks)
        if (weeks or "").isdigit() and int(weeks) in SEMANAS_DO_PAINEL
        else SEMANAS_PADRAO
    )
    fim = comando_ops.hoje_sp()
    return fim - timedelta(days=fim.weekday()) - timedelta(days=(semanas - 1) * 7), fim


# ── Funil com custo ──────────────────────────────────────────────────────────────────────────


def _gasto_por_anuncio(inicio: date, fim: date) -> dict[str, Decimal]:
    return {
        ad: Decimal(gasto or 0)
        for ad, gasto in db.session.query(
            MarketingAdMetric.ad_id, func.sum(MarketingAdMetric.spend)
        )
        .filter(
            MarketingAdMetric.platform == PLATAFORMA_DO_ANUNCIO,
            MarketingAdMetric.currency == "BRL",
            MarketingAdMetric.metric_date >= inicio,
            MarketingAdMetric.metric_date <= fim,
        )
        .group_by(MarketingAdMetric.ad_id)
        .all()
    }


def _gastos_do_funil(dividir: str, inicio: date, fim: date) -> dict[str, Decimal]:
    """Gasto de cada grupo do funil. Frente: só a Meta (as conversas com origem vêm de anúncio da Meta)."""
    if dividir == "frente":
        gastos, _ = comando_ops.gasto_por_frente(inicio, fim, plataforma=PLATAFORMA_DO_ANUNCIO)
        return {slug: g["gasto"] for slug, g in gastos.items()}
    por_anuncio = _gasto_por_anuncio(inicio, fim)
    if dividir == "anuncio":
        return por_anuncio
    saida: dict[str, Decimal] = defaultdict(Decimal)
    for ad, post_id, conceito in (
        db.session.query(MarketingPostAnuncio.ad_id, MarketingPost.id, MarketingPost.conceito)
        .join(MarketingPost, MarketingPost.id == MarketingPostAnuncio.post_id)
        .filter(MarketingPostAnuncio.platform == PLATAFORMA_DO_ANUNCIO)
        .all()
    ):
        chave = str(post_id) if dividir == "peca" else conceito
        if chave:
            saida[chave] += por_anuncio.get(ad, Decimal(0))
    return saida


def _com_custo(grupo: dict[str, Any], gasto: Decimal | None) -> dict[str, Any]:
    q = grupo["quantidades"]

    def custo(n: int) -> str | None:
        return comando_ops.q2(gasto / n) if gasto and gasto > 0 and n else None

    return {
        **grupo,
        "gasto": comando_ops.q2(gasto) if gasto is not None else None,
        "custo_conversa": custo(q["chegou"]),
        "custo_orcamento": custo(q["orcamento"]),
        "custo_evento": custo(q["evento"]),
    }


def funil_com_custo(inicio: date, fim: date, dividir: str) -> dict[str, Any]:
    """O funil das conversas (335) dividido por frente/anúncio/peça/conceito, com o gasto de cada grupo.

    O funil continua sem dinheiro no domínio das conversas (invariante 39 do `docs/04`): o custo é somado aqui,
    pela chave do grupo, e só sai pelo gate de Marketing.

    Raises:
        app.conversas.recusa.Recusa: 422 do funil (divisão inválida, período maior que um ano).
    """
    from app.conversas import funil_ops

    dados = funil_ops.funil(inicio.isoformat(), fim.isoformat(), dividir=dividir)
    gastos = _gastos_do_funil(dados["dividir"], inicio, fim)
    grupos = [
        _com_custo(g, None if g["chave"].startswith("__") else gastos.get(g["chave"], Decimal(0)))
        for g in dados["grupos"]
    ]
    return {**dados, "grupos": grupos}


# ── Card e cliente novo ──────────────────────────────────────────────────────────────────────


def clientes_dos_anuncios(anuncio_ids: set[str]) -> set[int]:
    """Fichas que chegaram (pela conversa ou pela ficha) por algum dos anúncios."""
    if not anuncio_ids:
        return set()
    pela_conversa = (
        db.session.query(Conversa.client_id)
        .join(ConversaAnuncio, ConversaAnuncio.conversa_id == Conversa.id)
        .filter(ConversaAnuncio.anuncio_id.in_(anuncio_ids), Conversa.client_id.isnot(None))
    )
    pela_ficha = db.session.query(Client.id).filter(
        or_(Client.anuncio_origem_id.in_(anuncio_ids), Client.anuncio_recente_id.in_(anuncio_ids))
    )
    return {cid for (cid,) in pela_conversa.all()} | {cid for (cid,) in pela_ficha.all()}


def vendas_por_anuncio(anuncio_ids: set[str]) -> dict[str, dict[str, Any]]:
    """`{anúncio: {vendas, faturamento}}` — vendas cujo contato atribuído é do anúncio, desde jun/2026."""
    clientes = clientes_dos_anuncios(anuncio_ids)
    if not clientes:
        return {}
    saida: dict[str, dict[str, Any]] = {}
    for va in atribuir_vendas(ATRIBUICAO_DESDE, None, client_ids=clientes):
        ad = va.toque.anuncio_id
        if ad in anuncio_ids:
            s = saida.setdefault(ad, {"vendas": 0, "faturamento": Decimal(0)})
            s["vendas"] += 1
            s["faturamento"] += va.sale_value
    return saida


def clientes_novos(inicio: date, fim: date) -> tuple[int, int]:
    """`(clientes novos no período, os que vieram de anúncio)` — a régua de entrada na base do Desempenho.

    "De anúncio" = ficha com anúncio de origem gravado (334) ou origem paga (`utm_source` de plataforma de
    anúncio). É o divisor honesto do custo por cliente novo: o gasto em anúncio não trouxe a indicação.
    """
    entrada = desempenho_ops._entrada_na_base()
    pagas = list(desempenho_ops._SOURCE_PLATFORM)
    de_anuncio = or_(
        Client.anuncio_origem_id.isnot(None), func.lower(func.trim(Client.utm_source)).in_(pagas)
    )
    total, anuncio = (
        db.session.query(func.count(Client.id), func.count(Client.id).filter(de_anuncio))
        .filter(
            entrada >= datetime.combine(inicio, datetime.min.time()),
            entrada < datetime.combine(fim + timedelta(days=1), datetime.min.time()),
        )
        .one()
    )
    return int(total or 0), int(anuncio or 0)
