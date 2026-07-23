"""Núcleo de precificação do EducaManto (feature 171) — usado apenas pela API/React.

A tela Jinja legada (`templates/educamanto/index.html`) continua com sua própria réplica em
JavaScript (padrão já estabelecido pela feature 076/081); este módulo existe para servir a nova
tela React sem duplicar a fórmula em TypeScript (Princípio III — regra de negócio fora do
frontend). Funções puras, sem `flask.request`/`render_template`.
"""

import math
from dataclasses import dataclass, field

from app.models import EducaMantoPackage
from app.orcamento.transport import calcular_van


@dataclass
class TransporteResultado:
    """Resultado do cálculo de transporte do EducaManto, já com o multiplicador de dias."""

    vt: float
    afsp: float
    valor_viagem: float
    dias: int
    total: float
    label: str
    km_total: float
    pessoas: int

    def to_dict(self) -> dict:
        return {
            "vt": self.vt,
            "afsp": self.afsp,
            "valor_viagem": self.valor_viagem,
            "dias": self.dias,
            "total": self.total,
            "label": self.label,
            "km_total": self.km_total,
            "pessoas": self.pessoas,
        }


@dataclass
class PacoteCalculado:
    """Resultado completo do cálculo de um pacote EducaManto (itens, desconto, transporte)."""

    scenario: str
    item_rows: list = field(default_factory=list)
    raw_cost: float = 0.0
    valor_base: float = 0.0
    desconto_aplicado: bool = False
    desconto: float = 0.0
    transporte: TransporteResultado | None = None
    valor_final_sem_nota: float = 0.0
    valor_final_com_nota: float = 0.0

    def to_dict(self) -> dict:
        return {
            "scenario": self.scenario,
            "item_rows": self.item_rows,
            "raw_cost": self.raw_cost,
            "valor_base": self.valor_base,
            "desconto_aplicado": self.desconto_aplicado,
            "desconto": self.desconto,
            "transporte": self.transporte.to_dict() if self.transporte else None,
            "valor_final_sem_nota": self.valor_final_sem_nota,
            "valor_final_com_nota": self.valor_final_com_nota,
        }


def pessoas_transporte(package: EducaMantoPackage, ensemble: int) -> int:
    """Deriva o nº de pessoas que viajam a partir do item "Catering apresentação" do pacote.

    Mesma regra já usada pela tela Jinja (`cateringApresentacaoQty`/`syncPessoasTransporte`,
    feature 079): o campo de pessoas do transporte não é digitado pelo usuário, é sempre o
    headcount do catering da apresentação, crescendo com o ensemble.

    Args:
        package: Pacote EducaManto.
        ensemble: Quantidade de figurantes extras.

    Returns:
        Quantidade de pessoas, ou 0 se o pacote não tiver um item de catering de apresentação.
    """
    import unicodedata

    def _norm(value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", value or "")
        return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()

    for item in package.items:
        if "catering apresenta" in _norm(item.name):
            return item.qty + (item.ensemble_add or 0) * ensemble
    return 0


def calcular_transporte(km_ida: float, pessoas: int, dias_total: int) -> TransporteResultado:
    """Calcula o transporte de uma viagem e multiplica pelo total de dias do pacote (feature 171).

    Reusa a mesma fórmula de tarifa por km + adicional por pessoa já usada pela calculadora de
    orçamento (`app.orcamento.transport`); o multiplicador de dias é específico do EducaManto
    (pacotes de múltiplos dias fora de São Paulo exigem uma ida e volta por dia). O transporte do
    EducaManto é sempre **van com carretinha** — decisão de negócio da feature 080 (o tipo de
    veículo deixou de ser escolhível; só endereço e nº de pessoas variam).

    Args:
        km_ida: Distância de ida, em km.
        pessoas: Número de pessoas que viajam (para o adicional por pessoa).
        dias_total: Total de dias do pacote (`d1 + d2`); usa no mínimo 1.

    Returns:
        O resultado do cálculo, com o valor de uma viagem e o total já multiplicado.
    """
    dias = max(int(dias_total or 0), 1)
    if not km_ida or km_ida <= 0:
        return TransporteResultado(
            vt=0.0,
            afsp=0.0,
            valor_viagem=0.0,
            dias=dias,
            total=0.0,
            label="",
            km_total=0.0,
            pessoas=pessoas,
        )

    resultado = calcular_van(pessoas, km_ida, carretinha=True, show=False)
    valor_viagem = round(resultado["transporte"] + resultado["adicional_fora_sp"], 2)
    total = round(valor_viagem * dias, 2)
    return TransporteResultado(
        vt=resultado["transporte"],
        afsp=resultado["adicional_fora_sp"],
        valor_viagem=valor_viagem,
        dias=dias,
        total=total,
        label="Van c/ carretinha",
        km_total=km_ida * 2,
        pessoas=pessoas,
    )


def _ceil100(valor: float) -> float:
    """Arredonda para cima até o próximo múltiplo de 100 (mesma regra do template Jinja)."""
    return math.ceil(valor / 100) * 100


def _effective_items(package: EducaMantoPackage, ensemble: int) -> list[dict]:
    """Itens do pacote com a quantidade ajustada pelo ensemble, + a linha de ensemble se houver."""
    items = [
        {
            "name": item.name,
            "qty": item.qty + (item.ensemble_add or 0) * ensemble,
            "cost_1s": item.cost_1s,
            "cost_2s": item.cost_2s,
            "cost_1s_days": item.cost_1s_days,
            "cost_2s_days": item.cost_2s_days,
        }
        for item in package.items
    ]
    if ensemble > 0:
        items.append(
            {
                "name": f"Ensemble ({ensemble})",
                "qty": ensemble,
                "cost_1s": package.ensemble_1s,
                "cost_2s": package.ensemble_2s,
                "cost_1s_days": package.ensemble_1s_days,
                "cost_2s_days": package.ensemble_2s_days,
            }
        )
    return items


def _valores_pacote(
    package: EducaMantoPackage,
    d1: int,
    d2: int,
    ensemble: int,
    acrescimo: float,
) -> dict:
    """Valor final sem/com nota de um pacote — mesma regra da tela Jinja (`valoresPacote`)."""
    total_dias = d1 + d2
    if total_dias <= 0:
        return {"sem_nota": 0.0, "com_nota": 0.0, "valor_base": 0.0, "sem_exato": 0.0}

    items = _effective_items(package, ensemble)
    if total_dias == 1 and d1 == 1:
        valor_base = sum(it["qty"] * it["cost_1s"] for it in items) * package.margin_1s
    elif total_dias == 1 and d2 == 1:
        valor_base = sum(it["qty"] * it["cost_2s"] for it in items) * package.margin_2s
    else:
        part1 = sum(it["qty"] * it["cost_1s_days"] for it in items) * d1 * package.margin_1s_days
        part2 = sum(it["qty"] * it["cost_2s_days"] for it in items) * d2 * package.margin_2s_days
        valor_base = part1 + part2

    sem_exato = (
        valor_base * (1 - package.discount_pct)
        if total_dias > package.discount_days
        else valor_base
    )
    sem_com_acrescimo = sem_exato + acrescimo
    return {
        "sem_nota": _ceil100(sem_com_acrescimo),
        "com_nota": _ceil100(sem_com_acrescimo / 0.84),
        "valor_base": valor_base,
        "sem_exato": sem_exato,
    }


def calcular_pacote(
    package: EducaMantoPackage,
    d1: int,
    d2: int,
    ensemble: int,
    acrescimo: float,
    transporte: TransporteResultado | None,
) -> PacoteCalculado:
    """Calcula o pacote completo (itens, cenário, desconto, acréscimo) somando o transporte.

    Reproduz em Python a lógica hoje só em JavaScript no template Jinja (`calcular()`/
    `valoresPacote()`/`effectiveItemsFor()`), para servir a nova tela React sem duplicar a fórmula
    em TypeScript.

    Args:
        package: Pacote EducaManto (itens, margens, desconto, ensemble).
        d1: Dias de 1 sessão.
        d2: Dias de 2 sessões.
        ensemble: Quantidade de figurantes extras.
        acrescimo: Comissão do vendedor, somada só no valor "sem nota" (capada ao valor original).
        transporte: Resultado do transporte já calculado (ou `None`/zerado).

    Returns:
        O breakdown completo do pacote, incluindo os totais finais com transporte somado.
    """
    total_dias = d1 + d2
    if total_dias <= 0:
        return PacoteCalculado(scenario="")

    items = _effective_items(package, ensemble)
    original = _valores_pacote(package, d1, d2, ensemble, 0)["sem_nota"]
    acrescimo_efetivo = min(acrescimo, original) if original > 0 else acrescimo

    item_rows: list[dict] = []
    if total_dias == 1 and d1 == 1:
        scenario = "1 sessão — 1 dia"
        raw_cost = 0.0
        for it in items:
            raw = it["qty"] * it["cost_1s"]
            raw_cost += raw
            item_rows.append(
                {
                    "name": it["name"],
                    "qty": it["qty"],
                    "unit_cost": it["cost_1s"],
                    "raw": raw,
                    "sell": raw * package.margin_1s,
                }
            )
    elif total_dias == 1 and d2 == 1:
        scenario = "2 sessões — 1 dia"
        raw_cost = 0.0
        for it in items:
            raw = it["qty"] * it["cost_2s"]
            raw_cost += raw
            item_rows.append(
                {
                    "name": it["name"],
                    "qty": it["qty"],
                    "unit_cost": it["cost_2s"],
                    "raw": raw,
                    "sell": raw * package.margin_2s,
                }
            )
    else:
        scenario = (
            f"{d1}d×1 sessão + {d2}d×2 sessões"
            if (d1 > 0 and d2 > 0)
            else f"{d1} dias × 1 sessão"
            if d1 > 0
            else f"{d2} dias × 2 sessões"
        )
        raw_cost = 0.0
        for it in items:
            raw1 = it["qty"] * it["cost_1s_days"] * d1
            raw2 = it["qty"] * it["cost_2s_days"] * d2
            raw_item = raw1 + raw2
            raw_cost += raw_item
            sell_item = raw1 * package.margin_1s_days + raw2 * package.margin_2s_days
            item_rows.append(
                {
                    "name": it["name"],
                    "qty": it["qty"],
                    "raw1": raw1,
                    "raw2": raw2,
                    "raw_item": raw_item,
                    "sell_item": sell_item,
                }
            )

    vp = _valores_pacote(package, d1, d2, ensemble, acrescimo_efetivo)
    desconto_aplicado = total_dias > package.discount_days
    desconto = vp["valor_base"] - vp["sem_exato"]

    transporte_total = transporte.total if transporte else 0.0
    return PacoteCalculado(
        scenario=scenario,
        item_rows=item_rows,
        raw_cost=raw_cost,
        valor_base=vp["valor_base"],
        desconto_aplicado=desconto_aplicado,
        desconto=desconto,
        transporte=transporte,
        valor_final_sem_nota=vp["sem_nota"] + transporte_total,
        valor_final_com_nota=vp["com_nota"] + transporte_total,
    )
