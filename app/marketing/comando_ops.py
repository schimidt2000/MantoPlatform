"""Marketing integrado ao sistema (feature 345) — o núcleo do "painel de comando".

Funções puras (sem `flask.request`), fonte única para as telas (`app/api/marketing_comando_*.py`,
`marketing_read.py`) e para a rotina semanal do Claude (`app/api/marketing_agent.py`):

* **Frente** — de que frente de negócio é cada campanha (prefixo do nome, com correção manual) e
  cada venda (regra derivada do evento, Clarification 1 da spec);
* **Custo por venda** — gasto da frente ÷ vendas da frente no período (custo *misto*: ainda não
  existe atribuição venda → anúncio), contra o teto da frente;
* **Licença do tema** — origem (autoral/licenciado) e "liberado para anúncio";
* **Pedidos de criativo** — cards abertos pela rotina, vínculo card ↔ anúncio e o resultado da peça;
* **Propostas** — o que a rotina quer mudar na Meta/Google; só o Superadmin aprova;
* **Diário** — o que mudou, por quê, e se funcionou.

Quem chama decide o papel: as funções recebem `eh_superadmin`/`user_id`, nunca `current_user`.
"""

from __future__ import annotations

import math
import re
import statistics
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from sqlalchemy import and_, case, exists, func, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import aliased, lazyload

from app import db
from app.constants import (
    DIARIO_REAVALIAR_DIAS,
    DIARIO_VEREDITOS,
    DIAS_NO_MES_DO_IMPACTO,
    JANELA_TESTE_MAX,
    JANELA_TESTE_MIN,
    JANELA_TESTE_PADRAO,
    LIBERADO_NAO,
    LIBERADO_NAO_DECIDIDO,
    LIBERADO_SIM,
    LIBERADO_VALORES,
    LICENCA_AUTORAL,
    LICENCA_LICENCIADO,
    LICENCA_NAO_CLASSIFICADO,
    LICENCA_ORIGENS,
    MARKETING_AD_PLATFORMS,
    MARKETING_FORMATOS,
    MARKETING_FRENTE_PREFIXOS,
    MARKETING_FRENTES,
    MARKETING_POST_TIPOS,
    MARKETING_STATUS_FILA_ANUNCIO,
    METRICA_DA_PROPOSTA,
    METRICAS_DO_TESTE,
    PROPOSTA_ALVOS,
    PROPOSTA_APROVADA,
    PROPOSTA_EXECUTADA,
    PROPOSTA_EXPIRADA,
    PROPOSTA_FALHOU,
    PROPOSTA_PENDENTE,
    PROPOSTA_RECUSADA,
    PROPOSTA_TIPOS,
    PROPOSTA_VALIDADE_DIAS,
    TEMAS_POR_PAGINA,
    TETO_FRACAO_MARGEM,
    TETO_JANELA_DIAS,
    TZ_SP,
    now_sp,
)
from app.marketing import desempenho_ops, marketing_ops
from app.models import (
    AnuncioMeta,
    CalendarEvent,
    CatalogItem,
    EventRole,
    MarketingAdMetric,
    MarketingCalendario,
    MarketingCampaignMetric,
    MarketingCampanhaFrente,
    MarketingDiario,
    MarketingFrente,
    MarketingPost,
    MarketingPostAnuncio,
    MarketingProposta,
    SiteSetting,
    SpecialExpense,
    User,
)
from app.notificacoes import notificacoes_ops

CENTAVO = Decimal("0.01")
# O primeiro número de um texto da rotina ("R$ 1.234,56/dia", "45.5"), para o valor da proposta (351).
_NUMERO = re.compile(r"\d[\d.,]*")
# Foco do mês no calendário (351): uma ou duas frases, não um plano.
FOCO_MAX = 500
# Palavras que fazem uma venda ser da frente social (Clarification 1). Regex do Postgres (`~*`).
SOCIAL_REGEX = "(15 anos|debut|casamento|noiv|bodas)"


class ComandoError(Exception):
    """Recusa de negócio com código estável — o endpoint traduz em `json_error`.

    `codigo` é o que o frontend compara (nunca o texto, Princípio XV); `field` aponta o campo do
    formulário; `status` é o HTTP (400 validação, 403 papel, 404 inexistente, 409 estado, 422 regra).
    """

    def __init__(
        self,
        message: str,
        *,
        codigo: str | None = None,
        field: str | None = None,
        status: int = 400,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.codigo = codigo
        self.field = field
        self.status = status


def q2(valor: Decimal) -> str:
    """Dinheiro em string com 2 casas, arredondamento comercial (`docs/00` §6 item 4)."""
    return str(valor.quantize(CENTAVO, rounding=ROUND_HALF_UP))


def hoje_sp() -> date:
    """A data do negócio — `date.today()` vira o dia errado depois das 21h (`docs/00` §6 item 3)."""
    return now_sp().date()


def iso_sp(carimbo: datetime | None) -> str | None:
    """Carimbo gravado em UTC naive → ISO no horário de parede de São Paulo.

    As tabelas da 345 gravam `datetime.utcnow()` (convenção do sistema), mas a tela mostra o dia: sem
    a conversão, a proposta criada às 23h de SP aparece com a data de amanhã (`docs/00` §6 item 1).
    """
    if carimbo is None:
        return None
    return carimbo.replace(tzinfo=UTC).astimezone(TZ_SP).replace(tzinfo=None).isoformat()


def _dec_opt(valor: Any, campo: str) -> Decimal | None:
    if valor in (None, ""):
        return None
    try:
        dec = Decimal(str(valor)).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        raise ComandoError("Valor inválido.", field=campo) from None
    if dec < 0:
        raise ComandoError("O valor não pode ser negativo.", field=campo)
    return dec


# ── Frente ────────────────────────────────────────────────────────────────────


def frente_por_prefixo(nome: str | None) -> str | None:
    """Frente pela primeira palavra do nome da campanha (`FESTA · MSG …` → `festas`)."""
    primeira = (nome or "").strip().split(" ", 1)[0].strip(" ·-_|").upper()
    return MARKETING_FRENTE_PREFIXOS.get(primeira)


def _correcoes() -> dict[tuple[str, str], str]:
    return {(c.platform, c.campaign_id): c.frente for c in MarketingCampanhaFrente.query.all()}


def correcoes_de_frente() -> dict[tuple[str, str], str]:
    """As correções manuais de frente, `(plataforma, campanha) → frente` — para quem calcula em lote
    (o funil e a atribuição da 351 leem a mesma regra do painel, uma consulta só)."""
    return _correcoes()


def frente_da_campanha(
    platform: str,
    campaign_id: str,
    nome: str | None,
    correcoes: dict[tuple[str, str], str] | None = None,
) -> str | None:
    """Correção manual > prefixo do nome > `None` ("sem frente")."""
    mapa = _correcoes() if correcoes is None else correcoes
    return mapa.get((platform, campaign_id)) or frente_por_prefixo(nome)


def corrigir_frente_campanha(
    platform: str, campaign_id: str, frente: str | None, user_id: int
) -> None:
    """Grava (ou desfaz, com `frente=None`) a correção manual da frente de uma campanha."""
    if not platform or not campaign_id:
        raise ComandoError("Informe a plataforma e a campanha.", field="campaign_id")
    existente = MarketingCampanhaFrente.query.filter_by(
        platform=platform, campaign_id=campaign_id
    ).first()
    if frente in (None, ""):
        if existente is not None:
            db.session.delete(existente)
        db.session.commit()
        return
    if frente not in MARKETING_FRENTES:
        raise ComandoError("Frente inválida.", field="frente")
    if existente is None:
        existente = MarketingCampanhaFrente(
            platform=platform, campaign_id=campaign_id, frente=frente
        )
        db.session.add(existente)
    existente.frente = frente
    existente.updated_by_id = user_id
    existente.updated_at = datetime.utcnow()
    db.session.commit()


def frente_venda_sql() -> Any:
    """Expressão SQL da frente de uma venda (Clarification 1) — a mesma regra dos números de 16/11."""
    titulo = func.coalesce(CalendarEvent.title, "")
    tipo = func.coalesce(CalendarEvent.event_type, "")
    return case(
        (or_(titulo.ilike("(EDU%"), tipo == "EDUCAMANTO"), "educamanto"),
        (tipo == "CORP", "corporativo"),
        (titulo.op("~*")(SOCIAL_REGEX), "social"),
        (tipo.in_(("VM", "VIRTUAL")), "loja"),
        else_="festas",
    )


def _filtro_venda() -> list[Any]:
    """A venda que conta: valor > 0, não cancelada, não cortesia, não satélite de grupo."""
    return [
        CalendarEvent.sale_value > 0,
        CalendarEvent.cancelled_at.is_(None),
        CalendarEvent.is_cortesia_permuta.is_(False),
        CalendarEvent.group_leader_id.is_(None),
    ]


def filtro_de_venda() -> list[Any]:
    """A régua da venda do custo misto, para a venda atribuída (351) contar igual."""
    return _filtro_venda()


# ── Custo por venda ───────────────────────────────────────────────────────────


def vendas_por_frente(inicio: date, fim: date) -> dict[str, dict[str, Any]]:
    """Vendas fechadas no período (pela data da venda), por frente, e quantas de cliente novo.

    Cliente novo = nenhum outro evento não cancelado do mesmo cliente antes deste.
    """
    anterior = aliased(CalendarEvent)
    tem_anterior = exists().where(
        and_(
            anterior.client_id == CalendarEvent.client_id,
            anterior.id != CalendarEvent.id,
            anterior.cancelled_at.is_(None),
            anterior.start_at < CalendarEvent.start_at,
        )
    )
    novo = case((and_(CalendarEvent.client_id.isnot(None), ~tem_anterior), 1), else_=0)
    linhas = (
        db.session.query(
            frente_venda_sql().label("frente"),
            func.count(CalendarEvent.id),
            func.sum(CalendarEvent.sale_value),
            func.sum(novo),
        )
        .filter(CalendarEvent.sale_date >= inicio, CalendarEvent.sale_date <= fim, *_filtro_venda())
        .group_by("frente")
        .all()
    )
    return {
        f: {"vendas": int(n), "faturamento": Decimal(fat or 0), "vendas_cliente_novo": int(nv or 0)}
        for f, n, fat, nv in linhas
    }


def gasto_por_frente(
    inicio: date, fim: date, *, plataforma: str | None = None
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Gasto, conversas e cadastros por frente; e as campanhas que ainda não têm frente.

    `plataforma` limita a uma só (o funil com custo da 351 usa só a Meta, de onde vêm as conversas).
    """
    correcoes = _correcoes()
    por_frente: dict[str, dict[str, Any]] = {}
    sem_frente: dict[tuple[str, str], dict[str, Any]] = {}
    for ln in desempenho_ops._effective_campaign_rows(inicio, fim):
        if ln.currency != "BRL" or (plataforma and ln.platform != plataforma):
            continue
        slug = frente_da_campanha(ln.platform, ln.campaign_id, ln.campaign_name, correcoes)
        if slug is None:
            g = sem_frente.setdefault(
                (ln.platform, ln.campaign_id),
                {
                    "platform": ln.platform,
                    "campaign_id": ln.campaign_id,
                    "campaign_name": ln.campaign_name,
                    "gasto": Decimal(0),
                },
            )
            g["gasto"] += ln.spend
            continue
        g = por_frente.setdefault(slug, {"gasto": Decimal(0), "conversas": 0, "cadastros": 0})
        g["gasto"] += ln.spend
        g["conversas"] += ln.conversations or 0
        g["cadastros"] += ln.leads or 0
    lista = sorted(sem_frente.values(), key=lambda g: -g["gasto"])
    return por_frente, [{**g, "gasto": q2(g["gasto"])} for g in lista]


def _margens_por_frente(desde: date, ate: date) -> dict[str, list[Decimal]]:
    """Margem bruta de cada venda (venda − cachês − gastos aprovados do evento), por frente."""
    caches = (
        db.session.query(
            func.coalesce(
                func.sum(
                    func.coalesce(EventRole.cache_value, 0)
                    + func.coalesce(EventRole.travel_cache, 0)
                ),
                0,
            )
        )
        .filter(EventRole.event_id == CalendarEvent.id, EventRole.dismissed_at.is_(None))
        .scalar_subquery()
    )
    gastos = (
        db.session.query(func.coalesce(func.sum(SpecialExpense.amount), 0))
        .filter(SpecialExpense.event_id == CalendarEvent.id, SpecialExpense.status == "aprovado")
        .scalar_subquery()
    )
    linhas = (
        db.session.query(frente_venda_sql(), CalendarEvent.sale_value - caches - gastos)
        .filter(CalendarEvent.sale_date >= desde, CalendarEvent.sale_date <= ate, *_filtro_venda())
        .all()
    )
    margens: dict[str, list[Decimal]] = {}
    for slug, margem in linhas:
        margens.setdefault(slug, []).append(Decimal(margem))
    return margens


def tetos(hoje: date | None = None) -> dict[str, dict[str, Any]]:
    """Teto de custo por venda de cada frente: o editado vence o padrão (25% da margem mediana)."""
    ref = hoje or hoje_sp()
    margens = _margens_por_frente(ref - timedelta(days=TETO_JANELA_DIAS), ref)
    editados = {f.slug: f for f in MarketingFrente.query.all()}
    saida: dict[str, dict[str, Any]] = {}
    for slug in MARKETING_FRENTES:
        lista = margens.get(slug) or []
        padrao = (Decimal(statistics.median(lista)) * TETO_FRACAO_MARGEM) if lista else None
        padrao = padrao if padrao is None or padrao > 0 else None
        editado = editados.get(slug)
        valor = (
            editado.teto_custo_venda if editado and editado.teto_custo_venda is not None else padrao
        )
        saida[slug] = {
            "teto": valor,
            "teto_padrao": padrao,
            "base_teto": f"25% da margem mediana de {len(lista)} venda(s) no último ano"
            if lista
            else "sem vendas no último ano",
            "teto_editado": bool(editado and editado.teto_custo_venda is not None),
        }
    return saida


def _estado(gasto: Decimal, vendas: int, custo: Decimal | None, teto: Decimal | None) -> str:
    if gasto <= 0:
        return "sem_gasto"
    if vendas == 0:
        return "sem_venda"
    if teto is not None and custo is not None and custo > teto:
        return "acima_do_teto"
    return "ok"


def _q2_opt(valor: Decimal | None) -> str | None:
    return q2(valor) if valor is not None else None


def _atribuido(gasto: Decimal, atribuida: dict[str, Any], teto: Decimal | None) -> dict[str, Any]:
    """A coluna atribuída da frente (351): o estado contra o teto usa o custo COM desconto."""
    from app.marketing import atribuicao_ops  # tardio: atribuicao_ops importa este módulo

    custo, com_desconto = atribuicao_ops.custos_atribuidos(gasto, atribuida["vendas"])
    return {
        "vendas_atribuidas": atribuida["vendas"],
        "faturamento_atribuido": q2(atribuida["faturamento"]),
        "custo_venda_atribuida": _q2_opt(custo),
        "custo_venda_atribuida_desconto": _q2_opt(com_desconto),
        "estado_atribuido": _estado(gasto, atribuida["vendas"], com_desconto, teto),
    }


def resumo_frentes(
    inicio: date, fim: date, atribuidas: dict[str, dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    """O bloco "Por frente" do Desempenho (contracts/api-345.md e api-351.md).

    O custo misto (gasto ÷ todas as vendas da frente) continua; a 351 põe ao lado o atribuído
    (`atribuidas`, de `atribuicao_ops.por_frente`) e o mês corrente contra a meta e a verba.
    """
    vendas = vendas_por_frente(inicio, fim)
    gastos, _ = gasto_por_frente(inicio, fim)
    tetos_ = tetos()
    mes = mes_corrente_por_frente()
    saida = []
    for slug, nome in MARKETING_FRENTES.items():
        v = vendas.get(slug, {"vendas": 0, "faturamento": Decimal(0), "vendas_cliente_novo": 0})
        g = gastos.get(slug, {"gasto": Decimal(0), "conversas": 0, "cadastros": 0})
        custo = (g["gasto"] / v["vendas"]) if v["vendas"] and g["gasto"] > 0 else None
        teto = tetos_[slug]["teto"]
        a = (atribuidas or {}).get(slug, {"vendas": 0, "faturamento": Decimal(0)})
        saida.append(
            {
                "slug": slug,
                "nome": nome,
                "gasto": q2(g["gasto"]),
                "conversas": g["conversas"],
                "cadastros": g["cadastros"],
                "vendas": v["vendas"],
                "vendas_cliente_novo": v["vendas_cliente_novo"],
                "faturamento": q2(v["faturamento"]),
                "custo_venda": _q2_opt(custo),
                "teto": _q2_opt(teto),
                "estado": _estado(g["gasto"], v["vendas"], custo, teto),
                **_atribuido(g["gasto"], a, teto),
                "mes_corrente": mes[slug],
            }
        )
    return saida


def situacao_plataformas(inicio: date, fim: date) -> list[dict[str, Any]]:
    """Última leitura de cada plataforma — "sem conexão" em vez de gasto zero (FR-006)."""
    ref = min(fim, hoje_sp())
    saida = []
    for platform in MARKETING_AD_PLATFORMS:
        ultima = (
            db.session.query(func.max(MarketingCampaignMetric.period_end))
            .filter(MarketingCampaignMetric.platform == platform)
            .scalar()
        )
        if ultima is None or ultima < inicio:
            situacao = "sem_conexao"
        elif ultima < ref - timedelta(days=7):
            situacao = "atrasada"
        else:
            situacao = "ok"
        saida.append(
            {
                "platform": platform,
                "ultima_data": ultima.isoformat() if ultima else None,
                "situacao": situacao,
            }
        )
    return saida


def painel_frentes(inicio: date, fim: date) -> dict[str, Any]:
    """O que o Desempenho ganha na 345 (frentes, campanhas sem frente, plataformas) e na 351 (a regra da
    atribuição, se o período é parcial e as vendas atribuídas a campanha sem frente)."""
    from app.marketing import atribuicao_ops  # tardio: atribuicao_ops importa este módulo

    _, sem_frente = gasto_por_frente(inicio, fim)
    atribuidas, sem_frente_atribuidas = atribuicao_ops.por_frente(inicio, fim)
    return {
        "frentes": resumo_frentes(inicio, fim, atribuidas),
        "sem_frente": sem_frente,
        "plataformas": situacao_plataformas(inicio, fim),
        "frente_opcoes": [{"slug": s, "nome": n} for s, n in MARKETING_FRENTES.items()],
        "atribuicao": {
            **atribuicao_ops.regra(inicio),
            "sem_frente": {
                "vendas": sem_frente_atribuidas["vendas"],
                "faturamento": q2(sem_frente_atribuidas["faturamento"]),
            },
        },
    }


# ── Metas, verba e calendário do ano (feature 351) ───────────────────────────────────────────


def _inteiro_opt(valor: Any, campo: str) -> int | None:
    if valor in (None, ""):
        return None
    try:
        numero = int(str(valor))
    except (TypeError, ValueError):
        raise ComandoError("Informe um número inteiro.", field=campo) from None
    if numero < 0:
        raise ComandoError("O valor não pode ser negativo.", field=campo)
    return numero


def metas_do_mes(mes: int) -> dict[str, dict[str, Any]]:
    """Meta, verba e foco de cada frente num mês: o calendário vence o padrão da frente."""
    frentes = {f.slug: f for f in MarketingFrente.query.all()}
    do_mes = {c.frente: c for c in MarketingCalendario.query.filter_by(mes=mes).all()}
    saida = {}
    for slug in MARKETING_FRENTES:
        f, c = frentes.get(slug), do_mes.get(slug)
        meta = c.meta_vendas if c and c.meta_vendas is not None else (f.meta_vendas_mes if f else None)
        verba = c.verba if c and c.verba is not None else (f.verba_mes if f else None)
        saida[slug] = {"meta_vendas": meta, "verba": _q2_opt(verba), "foco": c.foco if c else None}
    return saida


def mes_corrente_por_frente() -> dict[str, dict[str, Any]]:
    """O mês corrente de cada frente: vendas (todas) e gasto até hoje, contra a meta e a verba do mês."""
    hoje = hoje_sp()
    primeiro = hoje.replace(day=1)
    vendas = vendas_por_frente(primeiro, hoje)
    gastos, _ = gasto_por_frente(primeiro, hoje)
    metas = metas_do_mes(hoje.month)
    return {
        slug: {
            **metas[slug],
            "mes": hoje.month,
            "vendas": vendas.get(slug, {}).get("vendas", 0),
            "gasto": q2(gastos.get(slug, {}).get("gasto", Decimal(0))),
        }
        for slug in MARKETING_FRENTES
    }


def _linha_do_calendario(c: MarketingCalendario | None, mes: int) -> dict[str, Any]:
    return {
        "mes": mes,
        "meta_vendas": c.meta_vendas if c else None,
        "verba": _q2_opt(c.verba) if c else None,
        "foco": c.foco if c else None,
    }


def calendario(*, eh_superadmin: bool) -> dict[str, Any]:
    """O calendário do ano, frente × mês, com o padrão de cada frente ao lado."""
    frentes = {f.slug: f for f in MarketingFrente.query.all()}
    linhas: dict[str, dict[int, MarketingCalendario]] = {}
    for c in MarketingCalendario.query.all():
        linhas.setdefault(c.frente, {})[c.mes] = c
    return {
        "frentes": [
            {
                "slug": slug,
                "nome": nome,
                "meta_vendas_mes": frentes[slug].meta_vendas_mes if slug in frentes else None,
                "verba_mes": _q2_opt(frentes[slug].verba_mes) if slug in frentes else None,
                "meses": [_linha_do_calendario(linhas.get(slug, {}).get(m), m) for m in range(1, 13)],
            }
            for slug, nome in MARKETING_FRENTES.items()
        ],
        "mes_corrente": hoje_sp().month,
        "pode_editar": eh_superadmin,
    }


def _mes_valido(valor: Any, campo: str) -> int:
    try:
        mes = int(str(valor))
    except (TypeError, ValueError):
        mes = 0
    if not 1 <= mes <= 12:
        raise ComandoError("Mês inválido (1 a 12).", field=campo)
    return mes


def salvar_calendario(frente: Any, meses: Any, *, user_id: int) -> None:
    """Grava os meses enviados de uma frente; campo ausente fica como está e `null` limpa."""
    if frente not in MARKETING_FRENTES:
        raise ComandoError("Frente inválida.", field="frente")
    if not isinstance(meses, list) or not meses:
        raise ComandoError("Envie ao menos um mês.", field="meses")
    for i, item in enumerate(meses):
        if not isinstance(item, dict):
            raise ComandoError("Mês inválido.", field=f"meses.{i}")
        mes = _mes_valido(item.get("mes"), f"meses.{i}.mes")
        linha = MarketingCalendario.query.filter_by(frente=frente, mes=mes).first()
        if linha is None:
            linha = MarketingCalendario(frente=frente, mes=mes)
            db.session.add(linha)
        if "meta_vendas" in item:
            linha.meta_vendas = _inteiro_opt(item["meta_vendas"], f"meses.{i}.meta_vendas")
        if "verba" in item:
            linha.verba = _dec_opt(item["verba"], f"meses.{i}.verba")
        if "foco" in item:
            linha.foco = str(item["foco"] or "").strip()[:FOCO_MAX] or None
        linha.updated_by_id, linha.updated_at = user_id, datetime.utcnow()
    db.session.commit()


# ── Configuração das frentes ──────────────────────────────────────────────────


def _user_ref(user: User | None) -> dict[str, Any] | None:
    return (
        None
        if user is None
        else {"id": user.id, "name": user.name, "photo_url": user.profile_photo}
    )


def frentes_config(*, eh_superadmin: bool) -> dict[str, Any]:
    """Tetos, meta e verba do mês (351) e responsáveis por criativo, para o diálogo de configuração."""
    tetos_ = tetos()
    s = SiteSetting.query.get(1)
    editados = {f.slug: f for f in MarketingFrente.query.all()}
    return {
        "frentes": [
            {
                "slug": slug,
                "nome": nome,
                "meta_vendas_mes": editados[slug].meta_vendas_mes if slug in editados else None,
                "verba_mes": _q2_opt(editados[slug].verba_mes) if slug in editados else None,
                "teto": q2(t["teto"]) if t["teto"] is not None else None,
                "teto_padrao": q2(t["teto_padrao"]) if t["teto_padrao"] is not None else None,
                "base_teto": t["base_teto"],
                "teto_editado": t["teto_editado"],
            }
            for slug, nome in MARKETING_FRENTES.items()
            for t in [tetos_[slug]]
        ],
        "responsaveis": {
            "foto": _user_ref(User.query.get(s.marketing_resp_foto_id))
            if s and s.marketing_resp_foto_id
            else None,
            "video": _user_ref(User.query.get(s.marketing_resp_video_id))
            if s and s.marketing_resp_video_id
            else None,
        },
        "pode_editar": eh_superadmin,
    }


def _usuario_interno(uid: Any, campo: str) -> int | None:
    if uid in (None, ""):
        return None
    user = User.query.get(uid)
    if user is None or not user.is_active or not user.has_access:
        raise ComandoError("Escolha um usuário ativo da equipe.", field=campo)
    return user.id


# Coluna de `marketing_frentes` e conversor de cada bloco do corpo do PATCH (`tetos`, `metas`, `verbas`).
_COLUNAS_DA_FRENTE = {
    "tetos": ("teto_custo_venda", _dec_opt),
    "metas": ("meta_vendas_mes", _inteiro_opt),
    "verbas": ("verba_mes", _dec_opt),
}


def _gravar_por_frente(chave: str, valores: Any, user_id: int) -> None:
    if valores in (None, ...):
        return
    if not isinstance(valores, dict):
        raise ComandoError("Envie os valores por frente.", field=chave)
    coluna, conversor = _COLUNAS_DA_FRENTE[chave]
    for slug, valor in valores.items():
        if slug not in MARKETING_FRENTES:
            raise ComandoError("Frente inválida.", field=chave)
        linha = MarketingFrente.query.get(slug) or MarketingFrente(slug=slug)
        setattr(linha, coluna, conversor(valor, f"{chave}.{slug}"))
        linha.updated_by_id = user_id
        linha.updated_at = datetime.utcnow()
        db.session.add(linha)


def salvar_frentes(
    user_id: int,
    *,
    tetos_novos: Any = None,
    metas: Any = None,
    verbas: Any = None,
    resp_foto_id: Any = ...,
    resp_video_id: Any = ...,
) -> None:
    """Grava tetos (`None` volta ao padrão), meta e verba do mês (351) e responsáveis. `...` = não enviado."""
    _gravar_por_frente("tetos", tetos_novos, user_id)
    _gravar_por_frente("metas", metas, user_id)
    _gravar_por_frente("verbas", verbas, user_id)
    s = SiteSetting.query.get(1)
    if resp_foto_id is not ...:
        s.marketing_resp_foto_id = _usuario_interno(resp_foto_id, "resp_foto_id")
    if resp_video_id is not ...:
        s.marketing_resp_video_id = _usuario_interno(resp_video_id, "resp_video_id")
    db.session.commit()


# ── Desempenho por anúncio ────────────────────────────────────────────────────


def ingest_ad_metrics(items: Any) -> int:
    """Upsert idempotente por (plataforma, anúncio, dia) — repetir a rodada não duplica (FR-001)."""
    if not isinstance(items, list):
        raise ComandoError("items deve ser uma lista.", field="items")
    linhas = []
    agora = datetime.utcnow()
    for i, it in enumerate(items):
        if (
            not isinstance(it, dict)
            or not it.get("platform")
            or not it.get("ad_id")
            or not it.get("metric_date")
        ):
            raise ComandoError(
                "Cada item precisa de platform, ad_id e metric_date.", field=f"items[{i}]"
            )
        try:
            dia = date.fromisoformat(str(it["metric_date"]))
            gasto = Decimal(str(it.get("spend") or "0")).quantize(CENTAVO, rounding=ROUND_HALF_UP)
            inteiros = {
                c: (None if it.get(c) in (None, "") else int(it[c]))
                for c in ("impressions", "reach", "clicks", "conversations", "leads", "results")
            }
        except (ValueError, InvalidOperation, TypeError):
            raise ComandoError("Data ou número inválido.", field=f"items[{i}]") from None
        linhas.append(
            {
                "platform": str(it["platform"])[:20],
                "ad_id": str(it["ad_id"])[:80],
                "ad_name": (str(it.get("ad_name") or "")[:300] or None),
                "adset_id": (str(it.get("adset_id") or "")[:80] or None),
                "campaign_id": (str(it.get("campaign_id") or "")[:80] or None),
                "campaign_name": (str(it.get("campaign_name") or "")[:200] or None),
                "metric_date": dia,
                "spend": gasto,
                "currency": str(it.get("currency") or "BRL").upper()[:3],
                **inteiros,
                "updated_at": agora,
            }
        )
    if not linhas:
        return 0
    por_chave = {(r["platform"], r["ad_id"], r["metric_date"]): r for r in linhas}
    stmt = pg_insert(MarketingAdMetric).values(list(por_chave.values()))
    chave = ("platform", "ad_id", "metric_date")
    stmt = stmt.on_conflict_do_update(
        constraint="uq_marketing_ad_metrics_day",
        set_={c: stmt.excluded[c] for c in linhas[0] if c not in chave},
    )
    db.session.execute(stmt)
    db.session.commit()
    return len(por_chave)


# ── Licença dos temas ─────────────────────────────────────────────────────────


def serialize_tema_licenca(item: CatalogItem) -> dict[str, Any]:
    cover = item.cover_image
    return {
        "id": item.id,
        "name": item.name,
        "cover_url": cover.url if cover else None,
        "is_active": bool(item.is_active),
        "licenca_origem": item.licenca_origem,
        "liberado_anuncio": item.liberado_anuncio,
        "licenca_sugestao": item.licenca_sugestao,
        "licenca_sugestao_motivo": item.licenca_sugestao_motivo,
        "licenca_por": _user_ref(item.licenca_por),
        "licenca_em": iso_sp(item.licenca_em),
    }


def listar_temas_licenca(
    *,
    q: str | None = None,
    origem: str | None = None,
    liberado: str | None = None,
    so_sugestao: bool = False,
    pagina: int = 1,
) -> dict[str, Any]:
    """Temas ativos com a licença, filtráveis e paginados (351: 50 por página); e a contagem por origem."""
    query = CatalogItem.query.filter(CatalogItem.is_active.is_(True))
    if q:
        query = query.filter(
            CatalogItem.name.ilike(f"%{marketing_ops._escape_like(q)}%", escape="\\")
        )
    if origem in LICENCA_ORIGENS:
        query = query.filter(CatalogItem.licenca_origem == origem)
    if liberado in LIBERADO_VALORES:
        query = query.filter(CatalogItem.liberado_anuncio == liberado)
    if so_sugestao:
        query = query.filter(CatalogItem.licenca_sugestao.isnot(None))
    total = query.count()
    paginas = max(1, math.ceil(total / TEMAS_POR_PAGINA))
    pagina = min(max(1, pagina), paginas)
    itens = (
        query.order_by(CatalogItem.name.asc(), CatalogItem.id.asc())
        .offset((pagina - 1) * TEMAS_POR_PAGINA)
        .limit(TEMAS_POR_PAGINA)
        .all()
    )
    contagem = dict(
        db.session.query(CatalogItem.licenca_origem, func.count(CatalogItem.id))
        .filter(CatalogItem.is_active.is_(True))
        .group_by(CatalogItem.licenca_origem)
        .all()
    )
    sugestoes = CatalogItem.query.filter(
        CatalogItem.is_active.is_(True), CatalogItem.licenca_sugestao.isnot(None)
    ).count()
    return {
        "items": [serialize_tema_licenca(i) for i in itens],
        "contagem": {o: int(contagem.get(o, 0)) for o in LICENCA_ORIGENS},
        "com_sugestao": sugestoes,
        "total": total,
        "pagina": pagina,
        "paginas": paginas,
        "por_pagina": TEMAS_POR_PAGINA,
    }


def _liberado_padrao(origem: str) -> str:
    return {LICENCA_AUTORAL: LIBERADO_SIM, LICENCA_LICENCIADO: LIBERADO_NAO}.get(
        origem, LIBERADO_NAO_DECIDIDO
    )


def _carimbar(item: CatalogItem, user_id: int | None) -> None:
    item.licenca_por_id = user_id
    item.licenca_em = datetime.utcnow()


def marcar_licenca(
    item: CatalogItem, *, user_id: int, eh_superadmin: bool, origem: Any = ..., liberado: Any = ...
) -> CatalogItem:
    """Muda a origem e/ou o "liberado" de um tema.

    Trocar a origem sem mandar o liberado aplica o padrão (autoral → sim, licenciado → não). Liberar
    um licenciado é decisão do Superadmin (FR-009b); liberar sem classificar não é permitido.
    """
    nova_origem = item.licenca_origem if origem is ... else origem
    if nova_origem not in LICENCA_ORIGENS:
        raise ComandoError("Origem inválida.", field="licenca_origem")
    if liberado is ...:
        novo_liberado = (
            _liberado_padrao(nova_origem) if origem is not ... else item.liberado_anuncio
        )
    else:
        novo_liberado = liberado
    if novo_liberado not in LIBERADO_VALORES:
        raise ComandoError("Valor inválido para liberado.", field="liberado_anuncio")
    if novo_liberado == LIBERADO_SIM and nova_origem == LICENCA_NAO_CLASSIFICADO:
        raise ComandoError(
            "Classifique a origem do tema antes de liberar.", field="liberado_anuncio"
        )
    if (
        novo_liberado == LIBERADO_SIM
        and nova_origem == LICENCA_LICENCIADO
        and item.liberado_anuncio != LIBERADO_SIM
        and not eh_superadmin
    ):
        raise ComandoError(
            "Só o Superadmin libera um tema licenciado para anúncio.",
            codigo="so_superadmin",
            field="liberado_anuncio",
            status=403,
        )
    item.licenca_origem, item.liberado_anuncio = nova_origem, novo_liberado
    if origem is not ...:
        item.licenca_sugestao = item.licenca_sugestao_motivo = None
    _carimbar(item, user_id)
    db.session.commit()
    return item


def confirmar_sugestoes(ids: Any, *, user_id: int) -> int:
    """Aplica a sugestão da rotina em cada tema da lista (FR-009). Sem sugestão = ignorado."""
    if not isinstance(ids, list) or not ids:
        raise ComandoError("Escolha ao menos um tema.", field="ids")
    itens = CatalogItem.query.filter(
        CatalogItem.id.in_([int(i) for i in ids]), CatalogItem.licenca_sugestao.isnot(None)
    ).all()
    for item in itens:
        item.licenca_origem = item.licenca_sugestao
        item.liberado_anuncio = _liberado_padrao(item.licenca_sugestao)
        item.licenca_sugestao = item.licenca_sugestao_motivo = None
        _carimbar(item, user_id)
    db.session.commit()
    return len(itens)


def gravar_sugestoes(items: Any) -> dict[str, int]:
    """A rotina sugere a origem de temas; nunca confirma (a pessoa confirma em lote)."""
    if not isinstance(items, list):
        raise ComandoError("items deve ser uma lista.", field="items")
    gravadas = ignoradas = 0
    for it in items:
        origem = (it or {}).get("origem")
        item = CatalogItem.query.get((it or {}).get("catalog_item_id") or 0)
        if (
            item is None
            or origem not in (LICENCA_AUTORAL, LICENCA_LICENCIADO)
            or item.licenca_origem == origem
        ):
            ignoradas += 1
            continue
        item.licenca_sugestao = origem
        item.licenca_sugestao_motivo = str(it.get("motivo") or "")[:500] or None
        gravadas += 1
    db.session.commit()
    return {"gravadas": gravadas, "ignoradas": ignoradas}


# ── Pedidos de criativo e vínculo com anúncio ─────────────────────────────────


def responsavel_por_formato(formato: str | None) -> int | None:
    """Foto/arte → responsável por foto; vídeo → responsável por vídeo (Configurações)."""
    s = SiteSetting.query.get(1)
    if s is None or not formato:
        return None
    return s.marketing_resp_video_id if formato.startswith("video") else s.marketing_resp_foto_id


def criar_pedidos(items: Any) -> dict[str, Any]:
    """A rotina abre pedidos de criativo no Kanban (coluna Ideia, origem "rotina")."""
    if not isinstance(items, list):
        raise ComandoError("items deve ser uma lista.", field="items")
    criados, recusados = [], []
    for it in items:
        it = it or {}
        try:
            post = marketing_ops.create_post(
                title=it.get("titulo"),
                deadline_date=it.get("deadline_date"),
                platform=it.get("platform"),
                catalog_item_ids=it.get("catalog_item_ids") or [],
                assignee_id=responsavel_por_formato(it.get("formato")),
                tipo=it.get("tipo") or "anuncio",
                frente=it.get("frente"),
                formato=it.get("formato"),
                briefing_objetivo=it.get("briefing_objetivo"),
                briefing_mostrar=it.get("briefing_mostrar"),
                briefing_letreiro=it.get("briefing_letreiro"),
                origem="rotina",
                notes=it.get("notes"),
                conceito=it.get("conceito"),
            )
            criados.append(post.id)
        except marketing_ops.MarketingValidationError as exc:
            db.session.rollback()
            recusados.append(
                {"titulo": it.get("titulo"), "motivo": exc.message, "codigo": exc.codigo}
            )
    return {"criados": criados, "recusados": recusados}


def _serialize_card_pronto(post: MarketingPost) -> dict[str, Any]:
    return {
        "id": post.id,
        "title": post.title,
        "frente": post.frente,
        "formato": post.formato,
        "briefing_objetivo": post.briefing_objetivo,
        "briefing_mostrar": post.briefing_mostrar,
        "briefing_letreiro": post.briefing_letreiro,
        "conceito": post.conceito,
        "drive_folder_url": post.drive_folder_url,
        "temas": [{"id": t.id, "name": t.name} for t in post.temas],
        "review_space": marketing_ops.serialize_review_space(post.review_space),
    }


def cards_prontos_sem_anuncio() -> list[dict[str, Any]]:
    """Cards de anúncio prontos, ainda sem anúncio montado, com todos os temas liberados."""
    posts = (
        MarketingPost.query.filter(
            MarketingPost.tipo == "anuncio",
            # 351: arrastado para Agendado/Publicado sem anúncio montado continua na fila.
            MarketingPost.status.in_(MARKETING_STATUS_FILA_ANUNCIO),
            ~MarketingPost.anuncios.any(),
        )
        .order_by(MarketingPost.id)
        .all()
    )
    return [
        _serialize_card_pronto(p)
        for p in posts
        if all(t.liberado_anuncio == LIBERADO_SIM for t in p.temas)
    ]


def vincular_anuncio(post: MarketingPost, platform: Any, ad_id: Any) -> None:
    """Liga o anúncio montado ao card. Repetir o mesmo vínculo é inofensivo; de outro card, 409."""
    if platform not in MARKETING_AD_PLATFORMS or not ad_id:
        raise ComandoError(
            "Informe a plataforma (Meta Ads ou Google Ads) e o id do anúncio.", field="ad_id"
        )
    existente = MarketingPostAnuncio.query.filter_by(platform=platform, ad_id=str(ad_id)).first()
    if existente is not None:
        if existente.post_id != post.id:
            raise ComandoError(
                "Este anúncio já está ligado a outro card.",
                codigo="anuncio_de_outro_card",
                status=409,
            )
        return
    if post.tipo == "anuncio":
        marketing_ops.exigir_temas_liberados(post.temas)
    db.session.add(MarketingPostAnuncio(post_id=post.id, platform=platform, ad_id=str(ad_id)[:80]))
    db.session.commit()


# ── Propostas ─────────────────────────────────────────────────────────────────


def expirar_pendentes() -> None:
    """Pendente com mais de 7 dias perde a validade (FR-018) — aplicado em toda leitura/decisão."""
    limite = datetime.utcnow() - timedelta(days=PROPOSTA_VALIDADE_DIAS)
    MarketingProposta.query.filter(
        MarketingProposta.situacao == PROPOSTA_PENDENTE, MarketingProposta.criada_em < limite
    ).update({MarketingProposta.situacao: PROPOSTA_EXPIRADA}, synchronize_session=False)
    db.session.commit()


def _reais_do_texto(texto: str | None, tipo: str) -> Decimal | None:
    """O valor em reais que a rotina escreveu ("R$ 1.234,56/dia" → 1234.56), para somar o impacto.

    Só lê número em proposta de verba ou em texto com "R$": "Público: mães 25–40" não é dinheiro.
    """
    if not texto or (tipo != "verba" and "R$" not in texto):
        return None
    achado = _NUMERO.search(texto.replace("R$", " "))
    if achado is None:
        return None
    bruto = achado.group(0).rstrip(".,")
    if "," in bruto:
        bruto = bruto.replace(".", "").replace(",", ".")
    elif "." in bruto and len(bruto.rsplit(".", 1)[1]) == 3:
        bruto = bruto.replace(".", "")
    try:
        return Decimal(bruto).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None


def _nome_da_campanha(platform: str, campaign_id: str) -> str | None:
    return (
        db.session.query(MarketingCampaignMetric.campaign_name)
        .filter_by(platform=platform, campaign_id=campaign_id)
        .order_by(MarketingCampaignMetric.period_end.desc())
        .limit(1)
        .scalar()
    )


def _campanha_do_alvo(platform: str, alvo_tipo: str, alvo_id: str) -> tuple[str | None, str | None]:
    """`(id, nome)` da campanha de um conjunto ou anúncio — pela última leitura por anúncio ou pelo CRM."""
    coluna = MarketingAdMetric.adset_id if alvo_tipo == "conjunto" else MarketingAdMetric.ad_id
    linha = (
        MarketingAdMetric.query.filter(MarketingAdMetric.platform == platform, coluna == alvo_id)
        .order_by(MarketingAdMetric.metric_date.desc())
        .first()
    )
    if linha is not None and linha.campaign_id:
        return linha.campaign_id, linha.campaign_name or _nome_da_campanha(platform, linha.campaign_id)
    anuncio = AnuncioMeta.query.get(alvo_id) if alvo_tipo == "anuncio" else None
    return (anuncio.campanha_id, anuncio.campanha_nome) if anuncio else (None, None)


def _frente_da_proposta(d: dict[str, Any], post: MarketingPost | None) -> str | None:
    """A enviada > a da campanha do alvo (correção manual > prefixo) > a do card."""
    if d.get("frente") in MARKETING_FRENTES:
        return d["frente"]
    platform, alvo_id = d["platform"], str(d["alvo_id"])
    if d["alvo_tipo"] == "campanha":
        nome = d.get("alvo_nome") or _nome_da_campanha(platform, alvo_id)
        frente = frente_da_campanha(platform, alvo_id, nome)
    else:
        cid, nome = _campanha_do_alvo(platform, d["alvo_tipo"], alvo_id)
        frente = frente_da_campanha(platform, cid, nome) if cid or nome else None
    return frente or (post.frente if post else None)


def impacto_mensal(p: MarketingProposta) -> Decimal | None:
    """Quanto a proposta muda a verba do mês (30 dias). Pausa é negativa; público não tem impacto."""
    if p.tipo == "verba":
        if p.valor_antes_num is None or p.valor_depois_num is None:
            return None
        return (p.valor_depois_num - p.valor_antes_num) * DIAS_NO_MES_DO_IMPACTO
    if p.tipo == "ativar":
        base = p.valor_depois_num if p.valor_depois_num is not None else p.custo_dia_estimado
        return base * DIAS_NO_MES_DO_IMPACTO if base is not None else None
    if p.tipo == "pausar":
        base = p.valor_antes_num if p.valor_antes_num is not None else p.custo_dia_estimado
        return -base * DIAS_NO_MES_DO_IMPACTO if base is not None else None
    return None


def contexto_das_propostas() -> dict[str, dict[str, str | None]]:
    """Teto e verba do mês de cada frente, calculados uma vez para a lista inteira."""
    tetos_ = tetos()
    metas = metas_do_mes(hoje_sp().month)
    return {
        "tetos": {slug: _q2_opt(t["teto"]) for slug, t in tetos_.items()},
        "verbas": {slug: m["verba"] for slug, m in metas.items()},
    }


def impacto_aprovado_mes() -> str:
    """Soma do impacto mensal das propostas aprovadas ou executadas decididas no mês corrente (SP)."""
    agora = now_sp()
    inicio = datetime(agora.year, agora.month, 1, tzinfo=TZ_SP).astimezone(UTC).replace(tzinfo=None)
    decididas = MarketingProposta.query.filter(
        MarketingProposta.situacao.in_((PROPOSTA_APROVADA, PROPOSTA_EXECUTADA)),
        MarketingProposta.decidida_em >= inicio,
    ).all()
    return q2(sum((impacto_mensal(p) or Decimal(0) for p in decididas), Decimal(0)))


def serialize_proposta(p: MarketingProposta, contexto: dict[str, Any] | None = None) -> dict[str, Any]:
    """Proposta em JSON. `contexto` (de `contexto_das_propostas`) traz teto e verba da frente."""
    ctx = contexto or {}
    return {
        "frente": p.frente,
        "frente_nome": MARKETING_FRENTES.get(p.frente or ""),
        "valor_antes_num": _q2_opt(p.valor_antes_num),
        "valor_depois_num": _q2_opt(p.valor_depois_num),
        "impacto_mensal": _q2_opt(impacto_mensal(p)),
        "teto": ctx.get("tetos", {}).get(p.frente or ""),
        "verba_mes": ctx.get("verbas", {}).get(p.frente or ""),
        "id": p.id,
        "tipo": p.tipo,
        "platform": p.platform,
        "alvo_tipo": p.alvo_tipo,
        "alvo_id": p.alvo_id,
        "alvo_nome": p.alvo_nome,
        "valor_antes": p.valor_antes,
        "valor_depois": p.valor_depois,
        "custo_dia_estimado": q2(p.custo_dia_estimado)
        if p.custo_dia_estimado is not None
        else None,
        "motivo": p.motivo,
        "evidencia": p.evidencia,
        "post_id": p.post_id,
        "post_titulo": p.post.title if p.post else None,
        "situacao": p.situacao,
        "criada_em": iso_sp(p.criada_em),
        "decidida_por": _user_ref(p.decidida_por),
        "decidida_em": iso_sp(p.decidida_em),
        "decisao_obs": p.decisao_obs,
        "executada_em": iso_sp(p.executada_em),
        "resultado_execucao": p.resultado_execucao,
        "expira_em": iso_sp(p.criada_em + timedelta(days=PROPOSTA_VALIDADE_DIAS))
        if p.criada_em and p.situacao == PROPOSTA_PENDENTE
        else None,
    }


def criar_proposta(dados: Any) -> MarketingProposta:
    """A rotina registra uma proposta de mudança (sempre `pendente`)."""
    d = dados if isinstance(dados, dict) else {}
    if d.get("tipo") not in PROPOSTA_TIPOS:
        raise ComandoError("Tipo inválido.", field="tipo")
    if d.get("platform") not in MARKETING_AD_PLATFORMS:
        raise ComandoError("Plataforma inválida.", field="platform")
    if d.get("alvo_tipo") not in PROPOSTA_ALVOS or not d.get("alvo_id"):
        raise ComandoError(
            "Informe o alvo (campanha, conjunto ou anúncio) e o id.", field="alvo_id"
        )
    motivo = str(d.get("motivo") or "").strip()
    if not motivo:
        raise ComandoError("Toda proposta precisa de motivo.", field="motivo")
    post = None
    if d.get("post_id"):
        post = MarketingPost.query.get(d["post_id"])
        if post is None:
            raise ComandoError("Card não encontrado.", field="post_id", status=404)
        if post.tipo == "anuncio":
            try:
                marketing_ops.exigir_temas_liberados(post.temas)
            except marketing_ops.MarketingValidationError as exc:
                raise ComandoError(
                    exc.message, codigo=exc.codigo, field="post_id", status=422
                ) from None
    valor_antes = str(d.get("valor_antes") or "")[:200] or None
    valor_depois = str(d.get("valor_depois") or "")[:200] or None
    antes_num = _dec_opt(d.get("valor_antes_num"), "valor_antes_num")
    depois_num = _dec_opt(d.get("valor_depois_num"), "valor_depois_num")
    proposta = MarketingProposta(
        tipo=d["tipo"],
        platform=d["platform"],
        alvo_tipo=d["alvo_tipo"],
        alvo_id=str(d["alvo_id"])[:80],
        alvo_nome=(str(d.get("alvo_nome") or "")[:300] or None),
        valor_antes=valor_antes,
        valor_depois=valor_depois,
        # 351: o número para somar o impacto — o enviado, ou o lido do texto da rotina.
        valor_antes_num=antes_num if antes_num is not None else _reais_do_texto(valor_antes, d["tipo"]),
        valor_depois_num=depois_num if depois_num is not None else _reais_do_texto(valor_depois, d["tipo"]),
        frente=_frente_da_proposta(d, post),
        custo_dia_estimado=_dec_opt(d.get("custo_dia_estimado"), "custo_dia_estimado"),
        motivo=motivo,
        evidencia=(str(d.get("evidencia") or "").strip() or None),
        post_id=post.id if post else None,
        situacao=PROPOSTA_PENDENTE,
        criada_em=datetime.utcnow(),
    )
    db.session.add(proposta)
    db.session.flush()
    # Regime A da 272: proposta e aviso no sino na mesma transação — nunca aviso sem proposta.
    notificacoes_ops.notificar_proposta_marketing(proposta)
    db.session.commit()
    return proposta


def listar_propostas(situacao: str | None = None) -> list[MarketingProposta]:
    """Pendentes primeiro (mais novas no topo), depois o histórico — no máximo 100."""
    expirar_pendentes()
    query = MarketingProposta.query
    if situacao:
        query = query.filter(MarketingProposta.situacao == situacao)
    ordem = case((MarketingProposta.situacao == PROPOSTA_PENDENTE, 0), else_=1)
    return query.order_by(ordem, MarketingProposta.criada_em.desc()).limit(100).all()


def _travar_proposta(proposta_id: int) -> MarketingProposta:
    db.session.flush()
    # `lazyload("*")`: as relações `joined` viram LEFT JOIN, e o Postgres recusa FOR UPDATE no lado
    # anulável de uma junção externa. Trava só a linha da proposta; as relações carregam depois.
    proposta = (
        MarketingProposta.query.options(lazyload("*"))
        .filter_by(id=proposta_id)
        .with_for_update()
        .populate_existing()
        .one_or_none()
    )
    if proposta is None:
        raise ComandoError("Proposta não encontrada.", status=404)
    return proposta


def decidir(proposta_id: int, *, user_id: int, decisao: Any, obs: Any = None) -> MarketingProposta:
    """Aprova ou recusa (só Superadmin — o portão fica no endpoint). Decisão é única (409)."""
    if decisao not in ("aprovar", "recusar"):
        raise ComandoError("Escolha aprovar ou recusar.", field="decisao")
    expirar_pendentes()
    proposta = _travar_proposta(proposta_id)
    if proposta.situacao == PROPOSTA_EXPIRADA:
        db.session.rollback()
        raise ComandoError(
            "Proposta expirada: a rotina refaz a conta na próxima rodada.",
            codigo="expirada",
            status=409,
        )
    if proposta.situacao != PROPOSTA_PENDENTE:
        db.session.rollback()
        raise ComandoError("Esta proposta já foi decidida.", codigo="ja_decidida", status=409)
    proposta.situacao = PROPOSTA_APROVADA if decisao == "aprovar" else PROPOSTA_RECUSADA
    proposta.decidida_por_id = user_id
    proposta.decidida_em = datetime.utcnow()
    proposta.decisao_obs = str(obs or "").strip() or None
    db.session.commit()
    return proposta


def propostas_a_executar() -> list[dict[str, Any]]:
    expirar_pendentes()
    return [
        serialize_proposta(p)
        for p in MarketingProposta.query.filter(MarketingProposta.situacao == PROPOSTA_APROVADA)
        .order_by(MarketingProposta.id)
        .all()
    ]


def _titulo_da_proposta(p: MarketingProposta) -> str:
    verbo = {
        "ativar": "Ativado",
        "pausar": "Pausado",
        "verba": "Verba alterada",
        "publico": "Público alterado",
    }
    alvo = p.alvo_nome or p.alvo_id
    return f"{verbo.get(p.tipo, p.tipo)}: {alvo} ({p.platform})"[:200]


def marcar_execucao(proposta_id: int, *, resultado: Any, detalhe: Any) -> MarketingDiario:
    """O agente marca a proposta como executada ou falhou; nasce a entrada do diário (FR-019)."""
    if resultado not in (PROPOSTA_EXECUTADA, PROPOSTA_FALHOU):
        raise ComandoError("resultado deve ser executada ou falhou.", field="resultado")
    proposta = _travar_proposta(proposta_id)
    if proposta.situacao != PROPOSTA_APROVADA:
        db.session.rollback()
        raise ComandoError("Só proposta aprovada é executada.", codigo="nao_aprovada", status=409)
    texto = str(detalhe or "").strip() or None
    proposta.situacao = resultado
    proposta.executada_em = datetime.utcnow()
    proposta.resultado_execucao = texto
    entrada = MarketingDiario(
        titulo=_titulo_da_proposta(proposta),
        motivo=proposta.motivo,
        evidencia=proposta.evidencia,
        resultado_esperado=(
            f"{proposta.valor_antes or '—'} → {proposta.valor_depois}"
            if proposta.valor_depois
            else None
        ),
        reavaliar_em=hoje_sp() + timedelta(days=DIARIO_REAVALIAR_DIAS),
        origem="proposta",
        proposta_id=proposta.id,
        autor_id=proposta.decidida_por_id,
        criado_em=datetime.utcnow(),
        # 351: o teste nasce com o alvo da proposta e a métrica do tipo dela.
        alvo_platform=proposta.platform,
        alvo_tipo=proposta.alvo_tipo,
        alvo_id=proposta.alvo_id,
        alvo_nome=proposta.alvo_nome,
        metrica=METRICA_DA_PROPOSTA.get(proposta.tipo),
        mudou_em=hoje_sp(),
        janela_dias=JANELA_TESTE_PADRAO,
    )
    if resultado == PROPOSTA_EXECUTADA:
        entrada.linha_base = _linha_base(entrada)
    if resultado == PROPOSTA_FALHOU:
        # Não executou: não há o que reavaliar — fica registrado como inconclusivo, com o motivo.
        entrada.resultado_observado = f"Não executada: {texto or 'sem detalhe'}"
        entrada.veredito = "inconclusivo"
        entrada.avaliado_em = datetime.utcnow()
    db.session.add(entrada)
    db.session.commit()
    return entrada


# ── Diário ────────────────────────────────────────────────────────────────────

# O nome da métrica do teste → o campo somado nas duas tabelas de leitura (mesmos nomes de coluna).
_SOMAS_DO_TESTE = {"gasto": "spend", "conversas": "conversations", "cliques": "clicks", "cadastros": "leads"}
_QUATRO_CASAS = Decimal("0.0001")


def _linhas_do_alvo(platform: str, tipo: str, alvo_id: str, de: date, ate: date) -> list[Any]:
    """Leituras diárias do alvo. Campanha: o resumo por campanha (vale para o PMax, sem anúncio); conjunto
    e anúncio: a leitura por anúncio."""
    if tipo == "campanha":
        linhas = MarketingCampaignMetric.query.filter(
            MarketingCampaignMetric.platform == platform,
            MarketingCampaignMetric.campaign_id == alvo_id,
            MarketingCampaignMetric.is_daily.is_(True),
            MarketingCampaignMetric.period_start >= de,
            MarketingCampaignMetric.period_start <= ate,
        ).all()
        if linhas:
            return linhas
    coluna = {"campanha": MarketingAdMetric.campaign_id, "conjunto": MarketingAdMetric.adset_id}.get(
        tipo, MarketingAdMetric.ad_id
    )
    return MarketingAdMetric.query.filter(
        MarketingAdMetric.platform == platform,
        coluna == alvo_id,
        MarketingAdMetric.metric_date >= de,
        MarketingAdMetric.metric_date <= ate,
    ).all()


def _medir(platform: str, tipo: str, alvo_id: str, metrica: str, de: date, ate: date) -> Decimal | None:
    """O valor da métrica do alvo no intervalo; `None` = sem leitura (ou custo sem conversa)."""
    linhas = _linhas_do_alvo(platform, tipo, alvo_id, de, ate)
    if not linhas:
        return None
    soma = {nome: sum((Decimal(getattr(ln, col) or 0) for ln in linhas), Decimal(0)) for nome, col in _SOMAS_DO_TESTE.items()}
    if metrica == "custo_conversa":
        return soma["gasto"] / soma["conversas"] if soma["conversas"] else None
    return soma[metrica]


def _ultima_leitura(platform: str) -> date | None:
    por_anuncio = (
        db.session.query(func.max(MarketingAdMetric.metric_date)).filter(MarketingAdMetric.platform == platform).scalar()
    )
    por_campanha = (
        db.session.query(func.max(MarketingCampaignMetric.period_end))
        .filter(MarketingCampaignMetric.platform == platform)
        .scalar()
    )
    datas = [d for d in (por_anuncio, por_campanha) if d is not None]
    return max(datas) if datas else None


def _janelas(e: MarketingDiario) -> tuple[date, date, date, date]:
    """`(antes de, antes até, depois de, depois até)` em volta do dia da mudança."""
    dias = e.janela_dias or JANELA_TESTE_PADRAO
    return (
        e.mudou_em - timedelta(days=dias),
        e.mudou_em - timedelta(days=1),
        e.mudou_em,
        e.mudou_em + timedelta(days=dias - 1),
    )


def _variacao(antes: Decimal | None, depois: Decimal | None) -> float | None:
    if antes is None or depois is None or antes == 0:
        return None
    return round(float((depois - antes) / antes * 100), 1)


def _quatro(valor: Decimal | None) -> str | None:
    return str(valor.quantize(_QUATRO_CASAS, rounding=ROUND_HALF_UP)) if valor is not None else None


def _linha_base(e: MarketingDiario) -> Decimal | None:
    """O "antes" do alvo na hora em que a entrada nasce — congelado: a base que justificou a mudança."""
    de, ate, _, _ = _janelas(e)
    valor = _medir(e.alvo_platform or MARKETING_AD_PLATFORMS[0], e.alvo_tipo or "anuncio", e.alvo_id, e.metrica, de, ate)
    return valor.quantize(_QUATRO_CASAS, rounding=ROUND_HALF_UP) if valor is not None else None


def _controle(e: MarketingDiario, platform: str) -> dict[str, Any] | None:
    if not e.controle_id:
        return None
    a_de, a_ate, d_de, d_ate = _janelas(e)
    tipo = e.controle_tipo or e.alvo_tipo or "anuncio"
    antes = _medir(platform, tipo, e.controle_id, e.metrica, a_de, a_ate)
    depois = _medir(platform, tipo, e.controle_id, e.metrica, d_de, d_ate)
    return {
        "tipo": tipo,
        "id": e.controle_id,
        "nome": e.controle_nome,
        "antes": _quatro(antes),
        "depois": _quatro(depois),
        "variacao": _variacao(antes, depois),
    }


def teste_da_entrada(e: MarketingDiario) -> dict[str, Any] | None:
    """O antes e o depois do alvo (e do controle), calculados no servidor a cada leitura (351).

    Efeito líquido = variação do alvo − variação do controle, em pontos percentuais: a diferença em
    diferenças simples que cabe no volume da Manto (pesquisa §6.6). "Completo" quando a última leitura da
    plataforma já cobre o fim da janela do depois.
    """
    if not (e.alvo_id and e.metrica and e.mudou_em):
        return None
    platform = e.alvo_platform or MARKETING_AD_PLATFORMS[0]
    tipo = e.alvo_tipo or "anuncio"
    a_de, a_ate, d_de, d_ate = _janelas(e)
    antes = _medir(platform, tipo, e.alvo_id, e.metrica, a_de, a_ate)
    depois = _medir(platform, tipo, e.alvo_id, e.metrica, d_de, d_ate)
    variacao = _variacao(antes, depois)
    controle = _controle(e, platform)
    leitura = _ultima_leitura(platform)
    return {
        "alvo": {"platform": platform, "tipo": tipo, "id": e.alvo_id, "nome": e.alvo_nome},
        "metrica": e.metrica,
        "mudou_em": e.mudou_em.isoformat(),
        "janela_dias": e.janela_dias or JANELA_TESTE_PADRAO,
        "linha_base": _quatro(e.linha_base),
        "antes": {"de": a_de.isoformat(), "ate": a_ate.isoformat(), "valor": _quatro(antes)},
        "depois": {"de": d_de.isoformat(), "ate": d_ate.isoformat(), "valor": _quatro(depois)},
        "variacao": variacao,
        "completo": leitura is not None and leitura >= d_ate,
        "controle": controle,
        "efeito_liquido": round(variacao - controle["variacao"], 1)
        if variacao is not None and controle and controle["variacao"] is not None
        else None,
    }


def _data_opt(valor: Any, campo: str) -> date | None:
    if valor in (None, ""):
        return None
    try:
        return date.fromisoformat(str(valor))
    except ValueError:
        raise ComandoError("Data inválida (use AAAA-MM-DD).", field=campo) from None


def _campos_do_teste(d: dict[str, Any]) -> dict[str, Any]:
    """Os campos opcionais do teste estruturado (351). Sem métrica e sem alvo, a entrada é só texto."""
    metrica, alvo_id = d.get("metrica"), str(d.get("alvo_id") or "").strip()
    if not metrica and not alvo_id:
        return {}
    if metrica not in METRICAS_DO_TESTE:
        raise ComandoError("Escolha a métrica do teste.", field="metrica")
    if not alvo_id:
        raise ComandoError("Informe o id do alvo.", field="alvo_id")
    if d.get("alvo_tipo") not in PROPOSTA_ALVOS:
        raise ComandoError("Escolha campanha, conjunto ou anúncio.", field="alvo_tipo")
    platform = d.get("alvo_platform") or MARKETING_AD_PLATFORMS[0]
    if platform not in MARKETING_AD_PLATFORMS:
        raise ComandoError("Plataforma inválida.", field="alvo_platform")
    janela = _inteiro_opt(d.get("janela_dias"), "janela_dias") or JANELA_TESTE_PADRAO
    if not JANELA_TESTE_MIN <= janela <= JANELA_TESTE_MAX:
        raise ComandoError(f"Use de {JANELA_TESTE_MIN} a {JANELA_TESTE_MAX} dias.", field="janela_dias")
    controle_id = str(d.get("controle_id") or "").strip()[:80] or None
    controle_tipo = d.get("controle_tipo") or (d["alvo_tipo"] if controle_id else None)
    if controle_id and controle_tipo not in PROPOSTA_ALVOS:
        raise ComandoError("Escolha campanha, conjunto ou anúncio.", field="controle_tipo")
    return {
        "alvo_platform": platform,
        "alvo_tipo": d["alvo_tipo"],
        "alvo_id": alvo_id[:80],
        "alvo_nome": str(d.get("alvo_nome") or "").strip()[:300] or None,
        "metrica": metrica,
        "mudou_em": _data_opt(d.get("mudou_em"), "mudou_em") or hoje_sp(),
        "janela_dias": janela,
        "controle_tipo": controle_tipo if controle_id else None,
        "controle_id": controle_id,
        "controle_nome": str(d.get("controle_nome") or "").strip()[:300] or None,
    }


def serialize_diario(e: MarketingDiario) -> dict[str, Any]:
    return {
        "id": e.id,
        "titulo": e.titulo,
        "motivo": e.motivo,
        "evidencia": e.evidencia,
        "resultado_esperado": e.resultado_esperado,
        "reavaliar_em": e.reavaliar_em.isoformat(),
        "resultado_observado": e.resultado_observado,
        "veredito": e.veredito,
        "avaliado_em": iso_sp(e.avaliado_em),
        "origem": e.origem,
        "proposta_id": e.proposta_id,
        "autor": _user_ref(e.autor),
        "criado_em": iso_sp(e.criado_em),
        "a_reavaliar": e.avaliado_em is None and e.reavaliar_em <= hoje_sp(),
        "teste": teste_da_entrada(e),
    }


def listar_diario() -> list[MarketingDiario]:
    return MarketingDiario.query.order_by(MarketingDiario.criado_em.desc()).limit(200).all()


def diario_a_reavaliar() -> list[MarketingDiario]:
    return (
        MarketingDiario.query.filter(
            MarketingDiario.avaliado_em.is_(None), MarketingDiario.reavaliar_em <= hoje_sp()
        )
        .order_by(MarketingDiario.reavaliar_em)
        .all()
    )


def criar_entrada(dados: Any, *, autor_id: int | None, origem: str = "pessoa") -> MarketingDiario:
    """Entrada escrita à mão (ou pela rotina): o que mudou, por quê, e quando reavaliar."""
    d = dados if isinstance(dados, dict) else {}
    titulo = str(d.get("titulo") or "").strip()
    motivo = str(d.get("motivo") or "").strip()
    if not titulo:
        raise ComandoError("Diga o que mudou.", field="titulo")
    if not motivo:
        raise ComandoError("Diga por quê.", field="motivo")
    reavaliar = _data_opt(d.get("reavaliar_em"), "reavaliar_em") or (
        hoje_sp() + timedelta(days=DIARIO_REAVALIAR_DIAS)
    )
    teste = _campos_do_teste(d)
    entrada = MarketingDiario(
        titulo=titulo[:200],
        motivo=motivo,
        evidencia=(str(d.get("evidencia") or "").strip() or None),
        resultado_esperado=(str(d.get("resultado_esperado") or "").strip() or None),
        reavaliar_em=reavaliar,
        origem=origem,
        autor_id=autor_id,
        criado_em=datetime.utcnow(),
        **teste,
    )
    if teste:
        base = _dec_opt(d.get("linha_base"), "linha_base")
        entrada.linha_base = base if base is not None else _linha_base(entrada)
    db.session.add(entrada)
    db.session.commit()
    return entrada


def gravar_resultado(entrada_id: int, *, texto: Any, veredito: Any) -> MarketingDiario:
    """A rotina (ou uma pessoa) escreve o que aconteceu de fato e se funcionou."""
    entrada = MarketingDiario.query.get(entrada_id)
    if entrada is None:
        raise ComandoError("Entrada não encontrada.", status=404)
    if veredito not in DIARIO_VEREDITOS:
        raise ComandoError("Veredito inválido.", field="veredito")
    resultado = str(texto or "").strip()
    if not resultado:
        raise ComandoError("Escreva o resultado observado.", field="resultado_observado")
    entrada.resultado_observado, entrada.veredito = resultado, veredito
    entrada.avaliado_em = datetime.utcnow()
    db.session.commit()
    return entrada


# ── Contexto da rotina ────────────────────────────────────────────────────────


def contexto_comando(inicio: date, fim: date) -> dict[str, Any]:
    """Tudo que a rodada semanal precisa saber do ERP para decidir (agente, `GET …/comando`)."""
    liberados = (
        CatalogItem.query.filter(
            CatalogItem.is_active.is_(True), CatalogItem.liberado_anuncio == LIBERADO_SIM
        )
        .order_by(CatalogItem.name)
        .all()
    )
    sem_classificacao = (
        CatalogItem.query.filter(
            CatalogItem.is_active.is_(True), CatalogItem.licenca_origem == LICENCA_NAO_CLASSIFICADO
        )
        .order_by(CatalogItem.name)
        .all()
    )
    s = SiteSetting.query.get(1)
    contexto = contexto_das_propostas()
    return {
        **painel_frentes(inicio, fim),
        "periodo": {"start": inicio.isoformat(), "end": fim.isoformat()},
        # 351: o calendário do ano e a meta/verba/foco do mês, que antes eram prosa na skill.
        "calendario": calendario(eh_superadmin=False)["frentes"],
        "metas_do_mes": metas_do_mes(hoje_sp().month),
        "temas_liberados": [
            {"id": t.id, "name": t.name, "origem": t.licenca_origem} for t in liberados
        ],
        "temas_sem_classificacao": [
            {"id": t.id, "name": t.name, "tem_sugestao": t.licenca_sugestao is not None}
            for t in sem_classificacao
        ],
        "cards_prontos_sem_anuncio": cards_prontos_sem_anuncio(),
        "propostas_pendentes": [
            serialize_proposta(p, contexto)
            for p in MarketingProposta.query.filter(
                MarketingProposta.situacao == PROPOSTA_PENDENTE
            ).all()
        ],
        "propostas_a_executar": propostas_a_executar(),
        "diario_a_reavaliar": [serialize_diario(e) for e in diario_a_reavaliar()],
        "responsaveis": {
            "foto_id": s.marketing_resp_foto_id if s else None,
            "video_id": s.marketing_resp_video_id if s else None,
        },
        "formatos": MARKETING_FORMATOS,
        "tipos": MARKETING_POST_TIPOS,
    }
