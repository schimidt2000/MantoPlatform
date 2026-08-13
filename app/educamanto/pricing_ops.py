"""Núcleo de precificação do EducaManto por responsabilidades (feature 235).

Substitui o motor por pacote/nível: o preço nasce do MUSICAL + quatro responsabilidades
(sonorização, iluminação, alimentação, cenário), cada uma "por conta da Manto" (custo entra)
ou "por conta da contratante" (custo sai). A equipe técnica segue a matriz de 4 casos
(sonoplasta fixo; técnico de som quando som=Manto; técnico de iluminação quando
iluminação=Manto).

Fechamento preservado da fórmula histórica: soma de custos × margem por cenário, desconto
acima de `discount_days`, acréscimo do vendedor capado, arredondamento para cima na centena
e nota fiscal por ÷ 0,84 — o transporte de viagem entra no líquido antes da nota.

Funções puras (sem `flask.request`), servindo API/React. A tela Jinja morreu nesta feature —
não existe mais réplica da fórmula em JavaScript.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.educamanto import pdf_textos
from app.models import EducaMantoMusical
from app.orcamento import settings as _orc_settings

# Fator de nota fiscal (com nota = líquido ÷ 0,84) — mesmo da tela histórica.
NF_DIVISOR = 0.84
# Desconto à vista (PIX) — agora calculado de fato (feature 235; antes era só texto no PDF).
AVISTA_FATOR = 0.95

# Cenários de custo/margem, na ordem canônica das colunas: 1 sessão/1 dia, 2 sessões/1 dia,
# diária de 1 sessão (multi-dia), diária de 2 sessões (multi-dia).
_CENARIOS = ("1s", "2s", "1s_days", "2s_days")

_CUSTOS_TECNICOS: dict[str, tuple[float, float, float, float]] = {
    "sonoplasta": pdf_textos.PROVISORIO_SONOPLASTA,
    "tecnico_som": pdf_textos.PROVISORIO_TECNICO_SOM,
    "tecnico_iluminacao": pdf_textos.PROVISORIO_TECNICO_ILUMINACAO,
}


@dataclass(frozen=True)
class Responsabilidades:
    """Quem assume cada bloco: True = por conta da Manto (default), False = contratante."""

    som: bool = True
    iluminacao: bool = True
    alimentacao: bool = True
    cenario: bool = True

    @classmethod
    def from_dict(cls, data: dict | None) -> "Responsabilidades":
        """Parseia o shape da API ({"som": "manto"|"contratante", ...}); ausente = Manto."""
        data = data or {}

        def _manto(key: str) -> bool:
            return str(data.get(key) or "manto").strip().lower() != "contratante"

        return cls(
            som=_manto("som"),
            iluminacao=_manto("iluminacao"),
            alimentacao=_manto("alimentacao"),
            cenario=_manto("cenario"),
        )

    def to_dict(self) -> dict:
        return {
            "som": "manto" if self.som else "contratante",
            "iluminacao": "manto" if self.iluminacao else "contratante",
            "alimentacao": "manto" if self.alimentacao else "contratante",
            "cenario": "manto" if self.cenario else "contratante",
        }


@dataclass
class TransporteInfo:
    """Transporte da configuração — caminhão dentro de SP ou 2 vans fora de SP."""

    modo: str  # "caminhao_sp" | "vans_fora_sp"
    total: float = 0.0        # somado ao líquido (só vans; o caminhão entra na base c/ margem)
    caminhao: float = 0.0     # valor do caminhão (informativo, já dentro da base)
    valor_viagem: float = 0.0
    dias: int = 0
    km_total: float = 0.0
    pessoas: int = 0

    def to_dict(self) -> dict:
        return {
            "modo": self.modo,
            "total": self.total,
            "caminhao": self.caminhao,
            "valor_viagem": self.valor_viagem,
            "dias": self.dias,
            "km_total": self.km_total,
            "pessoas": self.pessoas,
        }


@dataclass
class ConfigCalculada:
    """Resultado completo do cálculo de uma configuração (uma página do orçamento)."""

    scenario: str
    headcount_evento: int
    headcount_ensaio: int
    tecnicos: list = field(default_factory=list)
    transporte: TransporteInfo | None = None
    valor_final_sem_nota: float = 0.0
    valor_final_com_nota: float = 0.0
    a_vista_sem_nota: float = 0.0
    a_vista_com_nota: float = 0.0
    acrescimo_efetivo: float = 0.0
    acrescimo_maximo: float = 0.0
    acrescimo_capado: bool = False
    desconto_aplicado: bool = False
    combinados: dict = field(default_factory=dict)
    # Breakdown interno — REMOVIDO da resposta para papéis não-superadmin (corte na API).
    item_rows: list = field(default_factory=list)
    blocos: dict = field(default_factory=dict)
    raw_cost: float = 0.0
    valor_base: float = 0.0
    desconto: float = 0.0
    liquido: float = 0.0
    contratacao_memoria: list = field(default_factory=list)
    contratacao_totais: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Resposta completa (superadmin). O corte por papel acontece na camada de API."""
        return {
            "scenario": self.scenario,
            "headcount": self.headcount_evento,
            "headcount_ensaio": self.headcount_ensaio,
            "tecnicos": self.tecnicos,
            "transporte": self.transporte.to_dict() if self.transporte else None,
            "valor_final_sem_nota": self.valor_final_sem_nota,
            "valor_final_com_nota": self.valor_final_com_nota,
            "a_vista_sem_nota": self.a_vista_sem_nota,
            "a_vista_com_nota": self.a_vista_com_nota,
            "acrescimo_efetivo": self.acrescimo_efetivo,
            "acrescimo_maximo": self.acrescimo_maximo,
            "acrescimo_capado": self.acrescimo_capado,
            "desconto_aplicado": self.desconto_aplicado,
            "combinados": self.combinados,
            "breakdown": {
                "item_rows": self.item_rows,
                "blocos": self.blocos,
                "raw_cost": self.raw_cost,
                "valor_base": self.valor_base,
                "desconto": self.desconto,
                "liquido": self.liquido,
                "contratacao_memoria": self.contratacao_memoria,
            },
        }


def _ceil100(valor: float) -> float:
    """Arredonda para cima até o próximo múltiplo de 100 (regra histórica do EducaManto)."""
    return math.ceil(valor / 100) * 100


def tecnicos_do_caso(resp: Responsabilidades) -> list[str]:
    """Matriz dos 4 casos — sonoplasta sempre vai; os técnicos seguem som/iluminação."""
    tecnicos = ["sonoplasta"]
    if resp.som:
        tecnicos.append("tecnico_som")
    if resp.iluminacao:
        tecnicos.append("tecnico_iluminacao")
    return tecnicos


def headcount_ensaio(musical: EducaMantoMusical, ensemble: int) -> int:
    """Quem ensaia: personagens + produção + ensemble (técnicos não ensaiam)."""
    return musical.num_personagens + musical.num_producao + ensemble


def headcount_evento(
    musical: EducaMantoMusical, resp: Responsabilidades, ensemble: int
) -> int:
    """Quem vai ao evento: equipe de ensaio + técnicos do caso — alimenta camarim,
    alimentação e o adicional por pessoa da viagem."""
    return headcount_ensaio(musical, ensemble) + len(tecnicos_do_caso(resp))


def calcular_transporte_fora_sp(
    km_ida: float, pessoas: int, dias_total: int
) -> TransporteInfo:
    """Viagem fora de SP: SEMPRE 2 vans (uma com carretinha), km de ida e volta das duas,
    adicional por pessoa uma única vez, × dias do pacote. Sem caminhão (feature 235)."""
    cfg = _orc_settings.load()["transporte"]
    dias = max(int(dias_total or 0), 1)
    km_total = float(km_ida) * 2
    vans = round(km_total * (cfg["van_com_carretinha"] + cfg["van_sem_carretinha"]), 2)
    adicional = round(pessoas * km_total / cfg["afsp_divisor"], 2)
    valor_viagem = round(vans + adicional, 2)
    return TransporteInfo(
        modo="vans_fora_sp",
        total=round(valor_viagem * dias, 2),
        valor_viagem=valor_viagem,
        dias=dias,
        km_total=km_total,
        pessoas=pessoas,
    )


def _caminhao_sp() -> float:
    return float(_orc_settings.load()["transporte"].get("caminhao_sp", 800))


def _custo_alimentacao(musical: EducaMantoMusical, cenario: str) -> float:
    """Alimentação por pessoa: 1 sessão usa o valor de 1s, 2 sessões o de 2s (diárias idem)."""
    if cenario in ("2s", "2s_days"):
        return musical.custo_alimentacao_2s
    return musical.custo_alimentacao_1s


def _linhas_de_custo(
    musical: EducaMantoMusical,
    resp: Responsabilidades,
    ensemble: int,
    fora_sp: bool,
    hc_evento: int,
) -> list[dict]:
    """Linhas de custo por cenário (itens sempre inclusos + blocos condicionais + técnicos).

    Cada linha tem `name`, `qty`, `bloco` (None = item comum) e os 4 custos unitários por
    cenário. Custos de ENSAIO ficam de fora — são independentes de dias (ver docstring de
    `_valores_configuracao`).
    """
    linhas: list[dict] = []
    for item in musical.items:
        linhas.append({
            "name": item.name,
            "qty": item.qty + (item.ensemble_add or 0) * ensemble,
            "bloco": None,
            "custos": (item.cost_1s, item.cost_2s, item.cost_1s_days, item.cost_2s_days),
        })
    if ensemble > 0:
        linhas.append({
            "name": f"Ensemble ({ensemble})",
            "qty": ensemble,
            "bloco": None,
            "custos": (
                musical.ensemble_1s, musical.ensemble_2s,
                musical.ensemble_1s_days, musical.ensemble_2s_days,
            ),
        })
    if resp.som:
        linhas.append({
            "name": "Som completo", "qty": 1, "bloco": "som",
            "custos": (
                musical.custo_som_1s, musical.custo_som_2s,
                musical.custo_som_1s_days, musical.custo_som_2s_days,
            ),
        })
    if resp.iluminacao:
        linhas.append({
            "name": "Iluminação completa", "qty": 1, "bloco": "iluminacao",
            "custos": (
                musical.custo_iluminacao_1s, musical.custo_iluminacao_2s,
                musical.custo_iluminacao_1s_days, musical.custo_iluminacao_2s_days,
            ),
        })
    if resp.cenario:
        linhas.append({
            "name": "Cenário (ambientação)", "qty": 1, "bloco": "cenario",
            "custos": (
                musical.custo_cenario_1s, musical.custo_cenario_2s,
                musical.custo_cenario_1s_days, musical.custo_cenario_2s_days,
            ),
        })
    if resp.alimentacao:
        linhas.append({
            "name": "Alimentação (dia do evento)", "qty": hc_evento, "bloco": "alimentacao",
            "custos": tuple(_custo_alimentacao(musical, c) for c in _CENARIOS),
        })
    for tecnico in tecnicos_do_caso(resp):
        linhas.append({
            "name": pdf_textos.TECNICO_LABELS[tecnico], "qty": 1, "bloco": "tecnicos",
            "custos": _CUSTOS_TECNICOS[tecnico],
        })
    if not fora_sp:
        caminhao = _caminhao_sp()
        linhas.append({
            "name": "Caminhão (dentro de SP)", "qty": 1, "bloco": "caminhao",
            "custos": (caminhao, caminhao, caminhao, caminhao),
        })
    return linhas


def _custo_ensaios(musical: EducaMantoMusical, hc_ensaio: int) -> float:
    """Custo total dos ensaios: por pessoa × headcount de ensaio × nº de ensaios."""
    por_pessoa = musical.custo_catering_ensaio_pp + musical.custo_ajuda_ensaio_pp
    return por_pessoa * hc_ensaio * max(int(musical.num_ensaios or 2), 2)


def _valores_configuracao(
    linhas: list[dict],
    musical: EducaMantoMusical,
    d1: int,
    d2: int,
    custo_ensaios: float,
) -> tuple[float, float, str, list[dict], dict]:
    """Valor base (custo × margem) + memória de linhas para o cenário efetivo.

    Os ENSAIOS entram uma única vez (não escalam com os dias do evento — regra nova da
    feature 235: o nº de ensaios é do musical), usando a margem de diária aplicável no
    multi-dia e a margem do cenário nos casos de 1 dia.

    Returns:
        (valor_base, raw_cost, rótulo do cenário, item_rows, blocos_venda)
    """
    item_rows: list[dict] = []
    blocos: dict[str, float] = {}
    raw_cost = 0.0
    valor_base = 0.0

    def _acumula(nome: str, qty: float, raw: float, sell: float, bloco: str | None) -> None:
        nonlocal raw_cost, valor_base
        raw_cost += raw
        valor_base += sell
        item_rows.append({
            "name": nome, "qty": qty, "raw": round(raw, 2), "sell": round(sell, 2),
        })
        if bloco:
            blocos[bloco] = round(blocos.get(bloco, 0.0) + sell, 2)

    total_dias = d1 + d2
    if total_dias == 1 and d1 == 1:
        scenario = "1 sessão — 1 dia"
        for ln in linhas:
            raw = ln["qty"] * ln["custos"][0]
            _acumula(ln["name"], ln["qty"], raw, raw * musical.margin_1s, ln["bloco"])
        _acumula("Ensaios", 1, custo_ensaios, custo_ensaios * musical.margin_1s, "ensaios")
    elif total_dias == 1 and d2 == 1:
        scenario = "2 sessões — 1 dia"
        for ln in linhas:
            raw = ln["qty"] * ln["custos"][1]
            _acumula(ln["name"], ln["qty"], raw, raw * musical.margin_2s, ln["bloco"])
        _acumula("Ensaios", 1, custo_ensaios, custo_ensaios * musical.margin_2s, "ensaios")
    else:
        scenario = (
            f"{d1}d×1 sessão + {d2}d×2 sessões" if (d1 > 0 and d2 > 0)
            else f"{d1} dias × 1 sessão" if d1 > 0
            else f"{d2} dias × 2 sessões"
        )
        for ln in linhas:
            raw1 = ln["qty"] * ln["custos"][2] * d1
            raw2 = ln["qty"] * ln["custos"][3] * d2
            sell = raw1 * musical.margin_1s_days + raw2 * musical.margin_2s_days
            _acumula(ln["name"], ln["qty"], raw1 + raw2, sell, ln["bloco"])
        margem_ensaio = musical.margin_1s_days if d1 > 0 else musical.margin_2s_days
        _acumula("Ensaios", 1, custo_ensaios, custo_ensaios * margem_ensaio, "ensaios")

    return valor_base, raw_cost, scenario, item_rows, blocos


def _fechar(valor_base: float, musical: EducaMantoMusical, total_dias: int) -> float:
    """Aplica o desconto por duração — devolve o valor exato pré-acréscimo/transporte."""
    if total_dias > musical.discount_days:
        return valor_base * (1 - musical.discount_pct)
    return valor_base


def _combinado(liquido: float, extra: float) -> dict:
    """Total combinado (EducaManto + parte Manto): nota UMA vez, sobre a soma (FR-016)."""
    soma = liquido + extra
    sem = _ceil100(soma)
    com = _ceil100(soma / NF_DIVISOR)
    return {
        "sem_nota": sem,
        "com_nota": com,
        "a_vista_sem": round(sem * AVISTA_FATOR, 2),
        "a_vista_com": round(com * AVISTA_FATOR, 2),
    }


def calcular_configuracao(
    musical: EducaMantoMusical,
    d1: int,
    d2: int,
    ensemble: int,
    resp: Responsabilidades,
    acrescimo: float,
    fora_sp: bool,
    km_ida: float,
    contratacao_totais: dict[str, float] | None = None,
    contratacao_memoria: list | None = None,
) -> ConfigCalculada:
    """Calcula uma configuração completa (uma página do orçamento).

    Args:
        musical: Musical escolhido.
        d1: Dias com 1 sessão. d2: Dias com 2 sessões (d1 + d2 > 0).
        ensemble: Figurantes extras (≥ 0).
        resp: Responsabilidades Manto × contratante.
        acrescimo: Comissão do vendedor em R$ (capada no valor da configuração sem transporte).
        fora_sp: Evento fora de São Paulo (2 vans; sem caminhão).
        km_ida: Distância de ida em km (obrigatória > 0 quando `fora_sp`).
        contratacao_totais: Totais da contratação Manto por duração (ex.: {"1h": 3200.0}),
            já calculados por `app.orcamento.quote_ops.calculate_quote` SEM nota fiscal.
        contratacao_memoria: Memória de cálculo da parte Manto (breakdown, só superadmin).

    Returns:
        O resultado completo — a camada de API corta o breakdown por papel.
    """
    total_dias = d1 + d2
    if total_dias <= 0:
        return ConfigCalculada(scenario="", headcount_evento=0, headcount_ensaio=0)

    hc_ensaio = headcount_ensaio(musical, ensemble)
    hc_evento = headcount_evento(musical, resp, ensemble)
    linhas = _linhas_de_custo(musical, resp, ensemble, fora_sp, hc_evento)
    custo_ensaios = _custo_ensaios(musical, hc_ensaio)
    valor_base, raw_cost, scenario, item_rows, blocos = _valores_configuracao(
        linhas, musical, d1, d2, custo_ensaios
    )
    sem_exato = _fechar(valor_base, musical, total_dias)

    if fora_sp and km_ida > 0:
        transporte = calcular_transporte_fora_sp(km_ida, hc_evento, total_dias)
    elif fora_sp:
        transporte = TransporteInfo(modo="vans_fora_sp", pessoas=hc_evento)
    else:
        transporte = TransporteInfo(
            modo="caminhao_sp", caminhao=_caminhao_sp(), pessoas=hc_evento
        )

    # Teto do acréscimo: o valor da configuração SEM transporte de viagem e SEM acréscimo
    # (regra histórica — transporte é repasse de custo, não amplia a comissão).
    teto = _ceil100(sem_exato)
    acrescimo_efetivo = min(acrescimo, teto) if teto > 0 else acrescimo

    liquido = sem_exato + acrescimo_efetivo + transporte.total
    sem_nota = _ceil100(liquido)
    com_nota = _ceil100(liquido / NF_DIVISOR)

    combinados = {
        duracao: _combinado(liquido, extra)
        for duracao, extra in (contratacao_totais or {}).items()
    }

    return ConfigCalculada(
        scenario=scenario,
        headcount_evento=hc_evento,
        headcount_ensaio=hc_ensaio,
        tecnicos=tecnicos_do_caso(resp),
        transporte=transporte,
        valor_final_sem_nota=sem_nota,
        valor_final_com_nota=com_nota,
        a_vista_sem_nota=round(sem_nota * AVISTA_FATOR, 2),
        a_vista_com_nota=round(com_nota * AVISTA_FATOR, 2),
        acrescimo_efetivo=acrescimo_efetivo,
        acrescimo_maximo=teto,
        acrescimo_capado=acrescimo > acrescimo_efetivo,
        desconto_aplicado=total_dias > musical.discount_days,
        combinados=combinados,
        item_rows=item_rows,
        blocos=blocos,
        raw_cost=round(raw_cost, 2),
        valor_base=round(valor_base, 2),
        desconto=round(valor_base - sem_exato, 2),
        liquido=round(liquido, 2),
        contratacao_memoria=contratacao_memoria or [],
        contratacao_totais=contratacao_totais or {},
    )
