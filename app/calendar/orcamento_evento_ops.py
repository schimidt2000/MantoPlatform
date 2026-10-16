"""Orçamento → evento: vincular e aplicar o que foi vendido (feature 273).

O orçamento já sabe tudo que o evento precisa saber sobre a venda — se é fora de SP (e quantos km),
quantos coordenadores foram vendidos, quem vai maquiado, se tem show (técnico de som), os tetos de
cachê por papel. A criação a partir do orçamento (`_create_event_core`, feature 152/239) aproveita
quase tudo isso; o que ficava de fora era o "fora de SP" (só o endereço classificava), e o evento
que nasce fora do fluxo — importado do Google Calendar, o caminho comum de quem marca a data no
celular e orça depois — não recebia **nada**: 44 dos 104 eventos futuros em 02/09/2026.

Este módulo é a fonte única de "o que o orçamento diz e como isso entra no evento", usada pela
criação, pelo vínculo posterior (`PATCH /api/events/<id>/orcamento`) e pela reclassificação
dentro/fora de SP. Puro no sentido da constituição: nada de `flask.request`; quem chama comita.

Regras que valem em todo caminho:

- **Nunca apaga nem rebaixa.** Aplicar a equipe cria o que falta (coordenadores até a quantidade
  vendida, maquiador, técnico de som) e marca maquiagem/cantor/teto em personagens que ainda não
  tinham — jamais remove uma vaga, desmarca maquiagem ou reduz um teto que alguém já subiu.
- **Personagem casa por nome normalizado** (sem acento, sem caixa, sem espaços duplicados). O que
  não casa é devolvido no relatório (`nao_casados`) para a tela dizer, em vez de inventar vaga:
  o evento do Google já tem o elenco pelo título, e um "Mickey que fala" do orçamento não pode
  virar um segundo Mickey.
- **Valores só em evento sem venda** (decisão D1 do plano das ondas): com venda digitada, o vínculo
  é rastro; os valores ficam como a comercial deixou.
"""

from __future__ import annotations

import json
import logging
import math
import unicodedata
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from app import db
from app.constants import ACRESCIMO_TIPO_BV
from app.models import CalendarEvent, EventAcrescimo, EventLog, EventRole, OrcamentoHistory

logger = logging.getLogger(__name__)

DURACOES_TABELA = (1, 2, 3, 4)

#: Feature 305 — o alerta "BV do orçamento pendente" só vale para evento criado ou ligado a orçamento
#: DEPOIS deste momento (o dono, 3a-Q4 = A: "não mexer no passado"). `datetime` NAIVE em UTC, como
#: `calendar_events.created_at` e `event_logs.created_at` em produção. Gravado no último commit antes
#: do merge como LITERAL naive, por exemplo `datetime(2026, 10, 15, 22, 0)`, com a hora tirada de
#: `datetime.now(UTC)` no Python (nunca o Git Bash). `None` = nenhum evento antigo acende (a falha
#: fecha: o alerta do passado convidaria a pagar de novo um BV pago por fora). Lido na hora da
#: chamada — o verify o troca por monkeypatch e confere o valor do commit (cenário 58).
CORTE_ALERTA_BV: datetime | None = datetime(2026, 10, 15, 5, 50)  # o deploy da 305 (02:50 em Brasília)


class OrcamentoJaVinculado(Exception):
    """O orçamento já está preso a outro evento não cancelado (1:1 entre vivos)."""

    def __init__(self, event_id: int) -> None:
        super().__init__(f"orçamento já vinculado ao evento {event_id}")
        self.event_id = event_id


# ── leitura do orçamento ───────────────────────────────────────────────────────────────────────

def snapshot_do_orcamento(entry: OrcamentoHistory) -> dict:
    """`form_snapshot` como dict; `{}` quando ausente ou corrompido (registros legados)."""
    try:
        snap = json.loads(entry.form_snapshot or "{}") or {}
    except (TypeError, ValueError):
        return {}
    # JSON válido que não é objeto (lista, texto) também é "corrompido" para quem lê `.get`.
    return snap if isinstance(snap, dict) else {}


def _km_ida(snap: dict) -> float:
    """Km de ida do orçamento; snapshots v1 só tinham `kmT` (ida e volta) — ver `casting_ops`."""
    km = float(snap.get("km_ida") or 0)
    if km <= 0 and snap.get("kmT"):
        km = float(snap.get("kmT") or 0) / 2
    return km


def _bv_do_resumo(snap: dict) -> dict | None:
    """`{"percentual": 10.0}` ou `{"valor": 10.0}` do primeiro BV do orçamento; `None` sem BV."""
    for linha in _linhas_do_snapshot(snap):
        if linha["is_bv"]:
            chave = "percentual" if linha["is_percent"] else "valor"
            return {chave: float(linha["value"])}
    return None


def resumo_do_orcamento(entry: OrcamentoHistory) -> dict:
    """O que o orçamento vendeu, na forma que a aba Comercial mostra (chips) e o vínculo aplica."""
    snap = snapshot_do_orcamento(entry)
    performers = snap.get("performers", []) or []
    return {
        "id": entry.id,
        # feature 301 — quem fez o orçamento. Chama-se `autor`, e não `vendedor`, porque o mesmo
        # bloco `venda` já traz `venda.seller`: o vendedor DO EVENTO, que pode ser outra pessoa.
        # Sem este nome a recusa de FR-011 não consegue dizer quem pode resolver (FR-010).
        "autor": (entry.user.name if entry.user else None) or "Vendedor não identificado",
        "client_name": entry.client_name or "",
        "event_date": entry.event_date or "",
        "event_location": entry.event_location or "",
        "fora_sp": bool(snap.get("fora_sp")),
        "km_ida": _km_ida(snap) if snap.get("fora_sp") else 0,
        "deslocamento_cliente": snap.get("deslocamento_responsavel") == "cliente",
        "coordenador_qty": max(int(snap.get("coordenador_qty", 1) or 1), 0),
        "maquiagens": sum(1 for p in performers if p.get("makeup")),
        "cantores": sum(
            1 for p in performers
            if p.get("type") == "cantor" or p.get("subtipo") == "cantor" or p.get("cantor")
        ),
        "personagens": [
            ((p.get("nome") or p.get("personagem") or "").strip()) for p in performers
        ],
        "has_show": bool(entry.has_show),
        # Feature 305 — o chip "BV 10%" (ou em reais) do painel Orçamento.
        "bv": _bv_do_resumo(snap),
        "total_1h": float(entry.total_1h or 0),
        "total_2h": float(entry.total_2h or 0),
        "total_3h": float(entry.total_3h or 0),
        "total_4h": float(entry.total_4h or 0),
    }


# ── acréscimos do orçamento (feature 305) ─────────────────────────────────────────────────────

_CENTAVO = Decimal("0.01")

#: B8 — a recusa de BV sem quem recebe ou sem PIX (o dono, 06/10: "é de extrema importância").
MENSAGEM_PIX = "Este evento tem BV: informe quem recebe e o PIX, para o repasse ir à Planilha de Pagamentos."


def _q(valor: Decimal) -> Decimal:
    return valor.quantize(_CENTAVO, rounding=ROUND_HALF_UP)


def _dec(valor: Any) -> Decimal | None:
    """Número finito como `Decimal`, ou `None` — nunca levanta (a B3 roda depois do Google)."""
    if isinstance(valor, bool) or valor is None:
        return None
    try:
        d = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return d if d.is_finite() else None


def divisor_da_nota() -> Decimal:
    """O 0,84 da nota em `Decimal` exato, derivado da fonte única (float, por causa da calculadora).

    Nunca `Decimal(NF_DIVISOR)`: o float vira 0,8399999… e o meio centavo da conta vira para baixo.
    """
    from app.educamanto.pricing_ops import NF_DIVISOR

    return Decimal(str(NF_DIVISOR))


def _total_da_duracao(entry: OrcamentoHistory, duracao: int) -> Decimal | None:
    """O total que o Novo evento mostra para a duração: a coluna (1–4h) ou a régua linear do prefill."""
    if duracao in DURACOES_TABELA:
        total = _dec(getattr(entry, f"total_{duracao}h", None))
    else:
        quatro = _dec(entry.total_4h)
        # A MESMA conta do prefill (`routes._build_orcamento_prefill`) e da calculadora, em float:
        # recalcular em Decimal diferiria um centavo do que a tela mostrou.
        total = _dec(round(float(quatro) / 4 * duracao, 2)) if quatro is not None else None
    return total if total is not None and total > 0 else None


def _linhas_do_snapshot(snap: dict) -> list[dict]:
    """Acréscimos do snapshot, só os com tipo e valor numérico (o resto é ignorado, sem erro)."""
    linhas = []
    for a in snap.get("acrescimos") or []:
        if not isinstance(a, dict):
            continue
        tipo = a.get("tipo")
        valor = _dec(a.get("value"))
        if not isinstance(tipo, str) or not tipo.strip() or valor is None or valor == 0:
            continue
        descricao = a.get("descricao")
        linhas.append({
            "tipo": tipo.strip()[:40],
            "descricao": descricao.strip() if isinstance(descricao, str) else "",
            "is_percent": bool(a.get("is_percent")),
            "value": valor,
            "is_bv": tipo.strip().upper() == ACRESCIMO_TIPO_BV,
            "valores_brl": a.get("valores_brl"),
        })
    return linhas


def _valor_gravado(linha: dict, indice: int, teto: Decimal) -> Decimal | None:
    """`valores_brl[indice]` da calculadora, se for confiável: o navegador devolve o snapshot no
    `/salvar`, então só vale número finito, ≥ 0 e não maior que o total da duração (research R2)."""
    lista = linha.get("valores_brl")
    if not isinstance(lista, list) or len(lista) != 4:
        return None
    bruto = lista[indice]
    if isinstance(bruto, bool) or not isinstance(bruto, (int, float)):
        return None
    if isinstance(bruto, float) and not math.isfinite(bruto):
        return None
    valor = _dec(bruto)
    if valor is None or valor < 0 or valor > teto:
        return None
    return _q(valor)


def _conta_inversa(linhas: list[dict], total: Decimal, nota: bool) -> list[Decimal | None]:
    """O que cada linha somou ao preço, refeito do total (a regra da calculadora de hoje).

    A calculadora aplica todos os % sobre o MESMO total antes dos acréscimos e divide tudo por 0,84
    no fim (`quote_ops.calculate_quote`). Desfazendo: líquido = total × 0,84 (com nota); base =
    (líquido − fixos) ÷ (1 + Σ%/100), ARREDONDADA AO CENTAVO — sem isso a conta não reproduz a
    memória (76 de 80 pares iguais com a base quantizada, 73 sem; os 4 restantes diferem R$ 0,01
    por meio centavo do float). Linha em % = base × % ÷ 100; fixa = o digitado.
    """
    liquido = total * divisor_da_nota() if nota else total
    fixos = sum((linha["value"] for linha in linhas if not linha["is_percent"]), Decimal("0"))
    percentuais = sum((linha["value"] for linha in linhas if linha["is_percent"]), Decimal("0"))
    divisor = Decimal("1") + percentuais / 100
    if divisor <= 0:
        return [None] * len(linhas)
    base = _q((liquido - fixos) / divisor)
    if base <= 0:
        return [None] * len(linhas)
    return [_q(base * linha["value"] / 100) if linha["is_percent"] else _q(linha["value"]) for linha in linhas]


def acrescimos_do_orcamento(entry: OrcamentoHistory | None, duracao: int) -> dict:
    """O que o orçamento somou ao preço, linha a linha, na duração (B1 da feature 305). Pura.

    É o valor CHEIO — o que a calculadora somou; a proporção da venda é de quem grava. Fontes, por
    linha: `valores_brl` gravado pela calculadora (desde a 305), se confiável; senão a conta
    inversa (`_conta_inversa`); senão a linha é pulada. Acima de 4h, a linha de 4h × horas ÷ 4
    (a régua linear da calculadora, inclusive a fixa). Orçamento personalizado não somou nada.

    **Nunca levanta**: roda depois do `insert_event` do Google, e uma exceção ali deixaria evento
    órfão na agenda (o caso da 254).

    Returns:
        ``{"total": Decimal | None, "personalizado": bool, "linhas": [{tipo, descricao, is_bv,
        is_percent, percentual, amount_brl}]}`` — ``amount_brl`` em ``Decimal`` > 0.
    """
    vazio = {"total": None, "personalizado": False, "linhas": []}
    try:
        if entry is None or isinstance(duracao, bool) or not isinstance(duracao, int) or duracao < 1:
            return vazio
        snap = snapshot_do_orcamento(entry)
        total = _total_da_duracao(entry, duracao)
        if snap.get("personalizado_ativo"):
            return {"total": total, "personalizado": True, "linhas": []}
        linhas = _linhas_do_snapshot(snap)
        total_tabela = _total_da_duracao(entry, min(duracao, 4))
        if not linhas or total is None or total_tabela is None:
            return {"total": total, "personalizado": False, "linhas": []}
        nota = bool(snap.get("nota_fiscal"))
        indice = min(duracao, 4) - 1
        fator = Decimal("1") if duracao <= 4 else Decimal(duracao) / 4
        inversa = _conta_inversa(linhas, total_tabela, nota)
        saida = []
        for linha, alternativa in zip(linhas, inversa, strict=True):
            cheio = _valor_gravado(linha, indice, total_tabela)
            if cheio is None:
                cheio = alternativa
            if cheio is None:
                continue
            cheio = _q(cheio * fator)
            if cheio <= 0:
                continue
            saida.append({
                "tipo": linha["tipo"],
                "descricao": linha["descricao"],
                "is_bv": linha["is_bv"],
                "is_percent": linha["is_percent"],
                "percentual": linha["value"] if linha["is_percent"] else None,
                "amount_brl": cheio,
            })
        return {"total": total, "personalizado": False, "linhas": saida}
    except Exception:  # noqa: BLE001 — a regra é não levantar; o log diz o que houve
        logger.exception("acrescimos_do_orcamento: orçamento %s, duração %s", getattr(entry, "id", None), duracao)
        return vazio


def deduzir_duracao(
    entry: OrcamentoHistory, *, bruto: Any, horas_agenda: int | None
) -> tuple[int | None, str]:
    """A duração de um evento criado sem ela no corpo (feature 305; FR-014 do plano do backlog).

    Ordem: o valor antes do desconto igual (± R$ 0,01) a um dos totais → as horas da agenda de 1 a
    4h, ou iguais à duração extra do orçamento → não identificada. Nunca o "1h calado" de antes.
    """
    valor = _dec(bruto)
    snap = snapshot_do_orcamento(entry)
    try:
        custom = int(snap.get("duracao_custom") or 0)
    except (TypeError, ValueError):
        custom = 0
    candidatas = list(DURACOES_TABELA) + ([custom] if custom > 4 else [])
    if valor is not None and valor > 0:
        for d in candidatas:
            total = _total_da_duracao(entry, d)
            if total is not None and abs(total - valor) <= _CENTAVO:
                return d, "pelo valor"
    if horas_agenda in DURACOES_TABELA or (custom > 4 and horas_agenda == custom):
        return horas_agenda, "pelo horário"
    return None, "duração não identificada"


def _so_percentuais(entry: OrcamentoHistory) -> bool:
    linhas = _linhas_do_snapshot(snapshot_do_orcamento(entry))
    return bool(linhas) and all(linha["is_percent"] for linha in linhas)


def _venda_de_verdade(venda: Any, cortesia: bool) -> bool:
    from app.calendar.event_ops import sem_valor_de_venda

    return not cortesia and not sem_valor_de_venda(venda)


def plano_dos_acrescimos(
    entry: OrcamentoHistory | None,
    *,
    venda: Any,
    cortesia: bool,
    duracao: int | None,
    duracao_origem: str = "",
    nota: bool | None = None,
) -> dict:
    """O que a B3 vai gravar — e por que não, quando não vai. Pura; a B8 pergunta a esta mesma
    função (`bv_vai_nascer`), para a recusa do PIX nunca divergir da gravação.

    A proporção é entre valores LÍQUIDOS (× 0,84 de quem tem nota), a régua da B10: a cliente que
    desiste da nota paga 16% menos pelo MESMO preço, e o BV fica. Sem isso a criação cortava o BV em
    16% (e a nota que entrava o subia 19%), e o mesmo evento dava BV diferente conforme o caminho.
    ``nota`` é a do evento; ``None`` = a do orçamento (o vínculo, que grava a nota do orçamento).

    Returns:
        ``{"linhas": [...], "total": Decimal | None, "duracao": int | None, "duracao_origem": str,
        "motivo": str | None, "tem_bv": bool}`` — cada linha com ``cheio`` (o do orçamento) e
        ``amount_brl`` (na proporção da venda).
    """
    plano = {"linhas": [], "total": None, "duracao": duracao, "duracao_origem": duracao_origem,
             "motivo": None, "tem_bv": False}
    if entry is None:
        plano["motivo"] = "sem orçamento"
        return plano
    if not _venda_de_verdade(venda, cortesia):
        plano["motivo"] = "sem valor de venda"
        return plano
    duracao_conta = duracao
    if duracao is None:
        if not _so_percentuais(entry):
            plano["motivo"] = "duração não identificada"
            return plano
        # Só %: a razão BV ÷ total é a mesma em toda duração — qualquer uma dá a proporção certa.
        duracao_conta, plano["duracao_origem"] = 1, "pela proporção"
    res = acrescimos_do_orcamento(entry, duracao_conta)
    if res["personalizado"]:
        plano["motivo"] = "orçamento personalizado"
        return plano
    if not res["linhas"] or res["total"] is None:
        plano["motivo"] = "orçamento sem acréscimos"
        return plano
    from app.orcamento.quote_ops import bv_que_acompanha

    plano["total"] = res["total"]
    nota_orcamento = bool(snapshot_do_orcamento(entry).get("nota_fiscal"))
    nota_evento = nota_orcamento if nota is None else bool(nota)
    venda_d = _dec(venda) or Decimal("0")
    venda_liquida = venda_d * divisor_da_nota() if nota_evento else venda_d
    total_liquido = res["total"] * divisor_da_nota() if nota_orcamento else res["total"]
    for linha in res["linhas"]:
        valor = bv_que_acompanha(linha["amount_brl"], venda_liquida, total_liquido)
        if valor > 0:
            plano["linhas"].append({**linha, "cheio": linha["amount_brl"], "amount_brl": valor})
    plano["tem_bv"] = any(linha["is_bv"] for linha in plano["linhas"])
    if not plano["linhas"]:
        plano["motivo"] = "orçamento sem acréscimos"
    return plano


def bv_vai_nascer(
    entry: OrcamentoHistory | None, *, venda: Any, cortesia: bool, duracao: int | None, nota: bool | None = None
) -> bool:
    """A pergunta da B8: a gravação vai criar BV? (as mesmas guardas da B3, pela mesma função)."""
    return plano_dos_acrescimos(entry, venda=venda, cortesia=cortesia, duracao=duracao, nota=nota)["tem_bv"]


def bv_nasce_no_vinculo(event: Any, entry: OrcamentoHistory | None, duracao: int | None) -> bool:
    """A B8 do "Vincular e aplicar": as guardas de `aplicar_valores_do_orcamento` + as da B3."""
    from app.calendar.event_ops import sem_valor_de_venda

    if entry is None or duracao not in DURACOES_TABELA:
        return False
    if getattr(event, "cancelled_at", None) is not None or getattr(event, "is_cortesia_permuta", False):
        return False
    if not sem_valor_de_venda(event.sale_value) or _tem_acrescimo(event.id):
        return False
    total = _total_da_duracao(entry, duracao)
    return total is not None and bv_vai_nascer(entry, venda=total, cortesia=False, duracao=duracao)


def erros_do_bv(recebedor: Any, pix: Any) -> dict[str, str]:
    """B8 — quem recebe e PIX: texto não vazio, até 200 e 140 caracteres. `{}` quando estão certos."""
    erros: dict[str, str] = {}
    if not isinstance(recebedor, str) or not recebedor.strip():
        erros["bv_recipient"] = "Informe quem recebe o BV."
    elif len(recebedor.strip()) > 200:
        erros["bv_recipient"] = "Quem recebe o BV: até 200 caracteres."
    if not isinstance(pix, str) or not pix.strip():
        erros["bv_pix"] = "Informe o PIX de quem recebe o BV."
    elif len(pix.strip()) > 140:
        erros["bv_pix"] = "PIX: até 140 caracteres."
    return erros


def _tem_acrescimo(event_id: int) -> bool:
    """Por CONSULTA, nunca por `event.acrescimos`: carregar a coleção vazia e inserir por `event_id`
    deixa a coleção velha na sessão, e o sync da comissão calcularia sem o BV."""
    return db.session.query(EventAcrescimo.id).filter_by(event_id=event_id).first() is not None


def _fmt_reais(valor: Any) -> str:
    from app.money import format_brl

    return format_brl(float(valor), prefix=True)


def gravar_acrescimos_do_orcamento(
    event: Any,
    entry: OrcamentoHistory | None,
    duracao: int | None,
    *,
    recebedor: str | None,
    pix: str | None,
    duracao_origem: str = "",
) -> dict:
    """Grava no evento os acréscimos que o orçamento somou ao preço (B3 da feature 305). Sem commit.

    Substitui a cópia antiga (`routes._criar_acrescimos_do_orcamento`), que calculava o % sobre a
    venda cheia — que já tem o próprio BV e a nota: R$ 130,95 onde quem indicou recebe R$ 100,00.
    Toda linha vai em REAIS (`is_percent=False`), já na proporção da venda (3a-Q1 = B), com a
    origem na descrição; o BV leva quem recebe e o PIX (a B8 garantiu os dois antes). Não toca
    evento cancelado nem evento que já tem QUALQUER acréscimo (a regra "nunca apaga nem rebaixa").

    Returns:
        ``{"criados": int, "bv_total": Decimal, "linhas": [...], "duracao": int | None,
        "duracao_origem": str, "motivo": str | None}`` — quem chama escreve o `EventLog`.
    """
    resultado = {"criados": 0, "bv_total": Decimal("0.00"), "linhas": [], "duracao": duracao,
                 "duracao_origem": duracao_origem, "motivo": None}
    if entry is None:
        resultado["motivo"] = "sem orçamento"
        return resultado
    if getattr(event, "cancelled_at", None) is not None:
        resultado["motivo"] = "evento cancelado"
        return resultado
    if _tem_acrescimo(event.id):
        resultado["motivo"] = "evento já tem acréscimos"
        return resultado
    plano = plano_dos_acrescimos(
        entry, venda=event.sale_value, cortesia=bool(getattr(event, "is_cortesia_permuta", False)),
        duracao=duracao, duracao_origem=duracao_origem, nota=bool(event.with_invoice),
    )
    resultado.update(duracao=plano["duracao"], duracao_origem=plano["duracao_origem"])
    if plano["motivo"]:
        resultado["motivo"] = plano["motivo"]
        return resultado
    if plano["tem_bv"] and erros_do_bv(recebedor, pix):
        # Defesa: a B8 já recusou antes (na criação, antes do Google; no vínculo, antes de gravar).
        # Se uma escrita concorrente mudou o evento entre a B8 e aqui, o BV não nasce sem PIX.
        resultado["motivo"] = "falta quem recebe e o PIX do BV"
        return resultado
    proporcional = any(linha["amount_brl"] != linha["cheio"] for linha in plano["linhas"])
    for linha in plano["linhas"]:
        origem = (
            f"{linha['percentual']:g}% no orçamento #{entry.id}" if linha["is_percent"]
            else f"{_fmt_reais(linha['cheio'])} no orçamento #{entry.id}"
        )
        if proporcional:
            origem += ", na proporção da venda"
        descricao = f"{linha['descricao']} — {origem}" if linha["descricao"] else origem
        db.session.add(EventAcrescimo(
            event_id=event.id,
            tipo=ACRESCIMO_TIPO_BV if linha["is_bv"] else linha["tipo"],
            descricao=descricao[:200],
            is_percent=False,
            value=linha["amount_brl"],
            amount_brl=linha["amount_brl"],
            is_bv=linha["is_bv"],
            bv_recipient=((recebedor or "").strip() or None) if linha["is_bv"] else None,
            bv_pix=((pix or "").strip() or None) if linha["is_bv"] else None,
            bv_payment_status="nao_pago",
        ))
        resultado["criados"] += 1
        if linha["is_bv"]:
            resultado["bv_total"] += linha["amount_brl"]
        resultado["linhas"].append(linha)
    db.session.flush()
    db.session.expire(event, ["acrescimos"])
    return resultado


def frase_do_bv(resultado: dict, entry: OrcamentoHistory, *, venda: Any, recebedor: str | None) -> str | None:
    """`EventLog` do BV gravado — sem o PIX: o histórico não é lugar de dado de pagamento."""
    bvs = [linha for linha in resultado.get("linhas") or [] if linha["is_bv"]]
    if not bvs:
        return None
    linha = bvs[0]
    detalhe = f"{linha['percentual']:g}%" if linha["is_percent"] else "em reais"
    if resultado.get("duracao"):
        detalhe += f", {resultado['duracao']}h"
    if resultado.get("duracao_origem"):
        detalhe += f", {resultado['duracao_origem']}"
    if linha["amount_brl"] != linha["cheio"]:
        detalhe += f"; na proporção da venda de {_fmt_reais(venda)}"
    return f"BV do orçamento #{entry.id}: {_fmt_reais(resultado['bv_total'])} ({detalhe}), para {recebedor or '—'}"


def _ligado_depois_do_corte(event: Any, *, novo_vinculo: bool = False) -> bool:
    """O evento foi criado, ou ligado ao orçamento ATUAL, depois do corte (3a-Q4 = A).

    Sem corte gravado, só o vínculo novo conta: o passado nunca acende por esquecimento.
    """
    if novo_vinculo:
        return True
    corte = CORTE_ALERTA_BV
    if corte is None:
        return False
    if corte.tzinfo is not None:
        # Gravado com fuso por engano: `created_at` é naive em UTC, e comparar os dois levanta.
        corte = corte.astimezone(UTC).replace(tzinfo=None)
    if event.created_at is not None and event.created_at >= corte:
        return True
    # O "(" fecha o número: sem ele, "#12" casaria "#123". "Reaplicou" não conta.
    prefixo = f"Vinculou o orçamento #{event.orcamento_history_id} (%"
    return db.session.query(EventLog.id).filter(
        EventLog.event_id == event.id, EventLog.message.like(prefixo), EventLog.created_at >= corte
    ).first() is not None


def bv_do_orcamento_pendente(event: Any, *, novo_vinculo: bool = False) -> dict | None:
    """O alerta da 3a-Q2 = A: o orçamento tem BV e a venda foi digitada à mão sem ele (B9).

    Presente quando: evento ligado a orçamento com BV (não personalizado); venda de verdade; nenhuma
    linha BV com valor no evento; não cancelado; não satélite; e criado/ligado depois do corte.
    O valor proposto é em REAIS — o que a criação gravaria (a conta do orçamento, na proporção da
    venda): a régua do % no evento (base com os outros acréscimos) não é a do orçamento salvo (base
    sem eles), e em orçamento com outro acréscimo o % daria outro BV (no 2407, R$ 2.007,73 em vez
    de R$ 435,00). Sem duração identificada, ``valor`` vem nulo e a tela pede para conferir.

    Returns:
        ``{"valor": float | None, "percentual": float | None, "duracao": int | None}`` ou ``None``.
    """
    if not event.orcamento_history_id or getattr(event, "cancelled_at", None) is not None:
        return None
    if getattr(event, "is_satellite", False):
        return None
    if not _venda_de_verdade(event.sale_value, bool(getattr(event, "is_cortesia_permuta", False))):
        return None
    if any(a.is_bv and (a.amount_brl or 0) > 0 for a in event.acrescimos):
        return None
    entry = db.session.get(OrcamentoHistory, event.orcamento_history_id)
    if entry is None:
        return None
    snap = snapshot_do_orcamento(entry)
    if snap.get("personalizado_ativo"):
        return None
    bvs = [linha for linha in _linhas_do_snapshot(snap) if linha["is_bv"]]
    if not bvs:
        return None
    if not _ligado_depois_do_corte(event, novo_vinculo=novo_vinculo):
        return None
    duracao, _origem = deduzir_duracao(
        entry, bruto=event.sale_value_gross or event.sale_value,
        horas_agenda=_duracao_do_evento(event) if event.start_at else None,
    )
    plano = plano_dos_acrescimos(
        entry, venda=event.sale_value, cortesia=False, duracao=duracao, nota=bool(event.with_invoice)
    )
    bv_plano = [linha for linha in plano["linhas"] if linha["is_bv"]]
    return {
        "valor": float(bv_plano[0]["amount_brl"]) if bv_plano else None,
        "percentual": float(bvs[0]["value"]) if bvs[0]["is_percent"] else None,
        "duracao": plano["duracao"] if bv_plano else None,
    }


# ── fora de SP ─────────────────────────────────────────────────────────────────────────────────

def aplicar_fora_sp_do_orcamento(event: Any, entry: OrcamentoHistory | None) -> bool:
    """Se o orçamento foi feito com "evento fora de São Paulo", o evento é fora de SP.

    A caixinha é a palavra da comercial na hora da venda — vale mais que o endereço (que muitas
    vezes é só "Buffet X"). A quilometragem do orçamento vira a distância do evento quando ele
    ainda não tem nenhuma: é a base da parcela do veículo no teto do carrinho (239). Um orçamento
    SEM a caixinha não diz nada (pode ter sido esquecida): não rebaixa para "dentro".

    Returns:
        ``True`` quando o orçamento manda fora de SP — e o evento ficou (ou já estava) assim. É
        "o que o orçamento diz", não "o que mudou nesta chamada": quem reclassifica pelo endereço
        usa este retorno para NÃO rebaixar um evento que a caixinha já decidiu (a primeira versão
        devolvia "mudou", e o segundo retoque de endereço derrubava o fora de SP).
    """
    if entry is None:
        return False
    snap = snapshot_do_orcamento(entry)
    if not snap.get("fora_sp"):
        return False
    event.is_outside_sp = True
    km = _km_ida(snap)
    if km > 0 and not event.travel_distance_km:
        event.travel_distance_km = km
    return True


# ── equipe ────────────────────────────────────────────────────────────────────────────────────

def _chave(nome: str | None) -> str:
    """Nome de papel comparável: sem acento, sem caixa, sem espaços repetidos."""
    texto = unicodedata.normalize("NFD", (nome or "").strip())
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return " ".join(texto.casefold().split())


def _duracao_do_evento(event: Any) -> int:
    """Horas do evento pela agenda (1..N), como a criação faz com `duracao`."""
    if not event.start_at or not event.end_at:
        return 1
    horas = (event.end_at - event.start_at).total_seconds() / 3600
    return max(1, int(round(horas)))


def _chave_cache(duracao: int) -> str:
    return "cache_custom" if duracao > 4 else f"cache_{duracao}h"


def data_do_evento(event: Any) -> str | None:
    """A data do evento como ``"AAAA-MM-DD"`` de parede, ou ``None`` sem `start_at` (feature 307).

    Fonte única para o teto das vagas: a faixa de data especial segue o dia em que o artista
    trabalha — na criação e no vínculo 273 —, que pode não ser a data do orçamento. Sem fuso: o
    `start_at` já é hora de São Paulo.
    """
    return event.start_at.date().isoformat() if getattr(event, "start_at", None) else None


def _cap_e_nota(item: dict, chave: str) -> tuple[Any, Any]:
    cap = item.get(chave)
    notas = item.get("cap_notes")
    nota = notas.get(chave) if isinstance(notas, dict) and cap is not None else None
    return cap, nota


def aplicar_equipe_do_orcamento(event: Any, entry: OrcamentoHistory) -> dict:
    """Cria o que o orçamento vendeu e o evento não tem; marca o que o evento tem e não sabia.

    Personagens (por nome normalizado): `needs_makeup`/`is_singer` viram True quando o orçamento
    diz; `cache_cap`/`cache_cap_note` entram só onde não havia teto. Apoio: coordenadores até a
    quantidade vendida, "Técnico de Som" quando o orçamento tem show, "Maquiador" quando alguém
    vai maquiado — cada um com o teto da duração real do evento. Nada é removido ou rebaixado.

    Returns:
        Relatório para a tela e para o log: contagens e a lista de personagens do orçamento que
        não acharam papel no evento.
    """
    from app.calendar.routes import _compute_performer_caches

    snap = snapshot_do_orcamento(entry)
    duracao = _duracao_do_evento(event)
    chave = _chave_cache(duracao)
    itens = _compute_performer_caches(
        snap, horas_extra=duracao if duracao > 4 else None, data_evento=data_do_evento(event)
    )
    papeis = list(event.roles)
    relatorio = {
        "personagens_casados": 0, "nao_casados": [], "maquiagem_marcada": 0,
        "cantor_marcado": 0, "tetos_aplicados": 0, "coordenadores_criados": 0,
        "tecnico_criado": False, "maquiador_criado": False, "duracao": duracao,
    }

    # Personagens: cada item do orçamento casa com no máximo um papel ainda livre.
    livres = [r for r in papeis if r.role_type != "extra"]
    for item in itens:
        if (item.get("role_type") or "character") != "character":
            continue
        alvo = next((r for r in livres if _chave(r.character_name) == _chave(item.get("label"))), None)
        if alvo is None:
            relatorio["nao_casados"].append((item.get("label") or "").strip())
            continue
        livres.remove(alvo)
        relatorio["personagens_casados"] += 1
        if item.get("needs_makeup") and not alvo.needs_makeup:
            alvo.needs_makeup = True
            relatorio["maquiagem_marcada"] += 1
        if item.get("is_singer") and not alvo.is_singer:
            alvo.is_singer = True
            relatorio["cantor_marcado"] += 1
        cap, nota = _cap_e_nota(item, chave)
        if cap is not None and alvo.cache_cap is None:
            alvo.cache_cap = cap
            alvo.cache_cap_note = nota
            relatorio["tetos_aplicados"] += 1

    extras = [i for i in itens if (i.get("role_type") or "character") == "extra"]
    apoio = [r for r in papeis if r.role_type == "extra"]

    # Coordenadores: até a quantidade vendida (o `_ensure_coordinator` da criação garante 1).
    coord_itens = [i for i in extras if _chave(i.get("label")).startswith("coordenador")]
    coord_existentes = [r for r in apoio if _chave(r.character_name).startswith("coordenador")]
    faltam = len(coord_itens) - len(coord_existentes)
    for item in coord_itens[:max(faltam, 0)]:
        cap, nota = _cap_e_nota(item, chave)
        db.session.add(EventRole(
            event_id=event.id, character_name="Coordenador", role_type="extra",
            cache_cap=cap, cache_cap_note=nota,
        ))
        relatorio["coordenadores_criados"] += 1
    for item, role in zip(coord_itens, coord_existentes, strict=False):
        cap, nota = _cap_e_nota(item, chave)
        if cap is not None and role.cache_cap is None:
            role.cache_cap, role.cache_cap_note = cap, nota
            relatorio["tetos_aplicados"] += 1

    # Técnico de som e maquiador: uma vaga cada, só se o orçamento vendeu e o evento não tem.
    for rotulo, marcador, chave_relatorio in (
        ("Técnico de Som", "tecnico de som", "tecnico_criado"),
        ("Maquiador", "maquiad", "maquiador_criado"),
    ):
        item = next((i for i in extras if _chave(i.get("label")) == _chave(rotulo)), None)
        if item is None:
            continue
        existente = next(
            (r for r in apoio if marcador in _chave(r.character_name) and "presenca" not in _chave(r.character_name)),
            None,
        )
        cap, nota = _cap_e_nota(item, chave)
        if existente is None:
            db.session.add(EventRole(
                event_id=event.id, character_name=rotulo, role_type="extra",
                cache_cap=cap, cache_cap_note=nota,
            ))
            relatorio[chave_relatorio] = True
        elif cap is not None and existente.cache_cap is None:
            existente.cache_cap, existente.cache_cap_note = cap, nota
            relatorio["tetos_aplicados"] += 1
    return relatorio


def _frase_relatorio(rel: dict) -> str:
    partes = []
    if rel.get("coordenadores_criados"):
        partes.append(f"+{rel['coordenadores_criados']} coordenador(es)")
    if rel.get("maquiador_criado"):
        partes.append("maquiador criado")
    if rel.get("tecnico_criado"):
        partes.append("técnico de som criado")
    if rel.get("maquiagem_marcada"):
        partes.append(f"maquiagem em {rel['maquiagem_marcada']} personagem(ns)")
    if rel.get("cantor_marcado"):
        partes.append(f"cantor em {rel['cantor_marcado']}")
    if rel.get("tetos_aplicados"):
        partes.append(f"teto em {rel['tetos_aplicados']} papel(is)")
    if rel.get("fora_sp"):
        partes.append("fora de SP")
    if rel.get("valores"):
        partes.append(f"valores de {rel['valores']}h aplicados")
    # Feature 305 — o BV que nasceu (nunca o PIX), o mês da Planilha e o efeito na comissão.
    if rel.get("bv_total"):
        trecho = f"BV de {_fmt_reais(rel['bv_total'])} para {rel.get('bv_para') or '—'}"
        if rel.get("bv_planilha"):
            trecho += f" — entra na Planilha de {rel['bv_planilha']}"
        partes.append(trecho + "; a comissão passa a ser sobre a venda menos o BV")
    if rel.get("bv_pendente_frase"):
        partes.append(rel["bv_pendente_frase"])
    if rel.get("bv_confira"):
        partes.append(rel["bv_confira"])
    if rel.get("bv_acompanhou"):
        partes.append(rel["bv_acompanhou"])
    return ", ".join(partes) if partes else "nada a aplicar (já estava tudo lá)"


# ── valores ───────────────────────────────────────────────────────────────────────────────────

def travar_evento(event: Any) -> None:
    """Relê a linha do evento com `SELECT … FOR UPDATE` (feature 305). Quem lê a venda para gravar o
    BV trava antes: duas aplicações no mesmo evento não passam juntas pela guarda "sem venda" (a
    venda seria de uma e o BV da outra); duas mudanças de venda não proporcionam o BV duas vezes a
    partir do mesmo "antes"; o editor não calcula o % com a venda de antes de outra gravação. A
    ordem é sempre evento → acréscimos (sem ciclo). O molde de `sumico_ops._bloquear_e_revalidar`."""
    if getattr(event, "id", None) is None:
        return
    # O que já foi escrito no evento vai ao banco antes; o refresh abaixo só relê a venda.
    db.session.flush()
    db.session.query(CalendarEvent.id).filter(CalendarEvent.id == event.id).with_for_update().one_or_none()
    db.session.refresh(event, ["sale_value", "with_invoice", "is_cortesia_permuta", "cancelled_at"])


def aplicar_valores_do_orcamento(
    event: Any,
    entry: OrcamentoHistory,
    *,
    duracao: int,
    sale_date=None,
    bv_recipient: str | None = None,
    bv_pix: str | None = None,
) -> dict | None:
    """Venda, transporte e nota fiscal do orçamento para a duração escolhida — só em evento SEM venda.

    Os totais vêm de `_build_orcamento_prefill` (a mesma conta da tela de criação: transporte
    fora-SP, deslocamento por conta da cliente, acréscimo legado). Com venda já digitada não
    mexe (D1 do plano das ondas): quem chama decide se avisa. Os acréscimos do orçamento nascem
    junto pela B3 da feature 305 (em reais, com quem recebe e o PIX), como na criação.

    Returns:
        O resultado da B3 (``criados``, ``bv_total``, ``motivo``…, mais ``venda_antes``) quando
        aplicou; ``None`` quando não.
    """
    from app.calendar.comercial_ops import estado_da_venda
    from app.calendar.event_ops import resolver_data_da_venda, sem_valor_de_venda
    from app.calendar.routes import _build_orcamento_prefill

    # Trava e relê; o "antes" vai para a B10, que o chamador roda quando a B3 não grava.
    antes = estado_da_venda(event)
    # Feature 299: o valor simbólico (o R$ 0,01 de "segurar a data") conta como "sem venda" — é
    # pelo orçamento que a comercial põe o valor de verdade.
    if not sem_valor_de_venda(event.sale_value) or getattr(event, "is_cortesia_permuta", False):
        # Cortesia/permuta grava venda 0 de propósito — não é "sem venda".
        return None
    if duracao not in DURACOES_TABELA:
        # A régua acima de 4h só existe na criação (que recalcula os cachês para a duração real);
        # o `total_custom` do prefill usa o `duracao_custom` gravado no orçamento, não a pedida.
        return None
    pre = _build_orcamento_prefill(entry.id)
    total = pre.get(f"total_{duracao}h") or 0
    if not total:
        return None
    valor = Decimal(str(total)).quantize(Decimal("0.01"))
    event.sale_value = valor
    event.sale_value_gross = valor
    event.transport_value = Decimal(str(pre.get("transport_value") or 0))
    event.acrescimo_value = Decimal(str(pre.get("acrescimo_value") or 0))
    event.with_invoice = bool(pre.get("with_invoice"))
    event.sale_date = resolver_data_da_venda(sale_date, valor, None, event.sale_date)
    # Acréscimos tipados (BV etc.) nascem junto, pela MESMA B3 da criação — senão dois eventos
    # vendidos pelo mesmo orçamento teriam BV diferente conforme o caminho. Antes do sync da
    # comissão, que o chamador faz em seguida: a base já sai sem o BV.
    resultado = gravar_acrescimos_do_orcamento(event, entry, duracao, recebedor=bv_recipient, pix=bv_pix)
    resultado["venda_antes"] = antes
    return resultado


def _relatar_bv(
    relatorio: dict,
    event: Any,
    entry: OrcamentoHistory,
    resultado: dict | None,
    *,
    novo_vinculo: bool,
    recebedor: str | None,
) -> None:
    """O BV no relatório do vínculo (feature 305): o que nasceu, ou por que não, e o que fazer."""
    from app.calendar.event_ops import sem_valor_de_venda
    from app.constants import now_sp

    orcamento_tem_bv = any(linha["is_bv"] for linha in _linhas_do_snapshot(snapshot_do_orcamento(entry)))
    ja_tem_bv = db.session.query(EventAcrescimo.id).filter_by(event_id=event.id, is_bv=True).first() is not None
    aviso_acrescimos = (
        f"BV do orçamento #{entry.id} não aplicado: o evento já tem acréscimos — confira em Acréscimos"
    )
    if resultado is not None:
        relatorio["acrescimos_criados"] = resultado["criados"]
        relatorio["bv_total"] = float(resultado["bv_total"])
        if resultado["motivo"]:
            relatorio["acrescimos_ignorados"] = resultado["motivo"]
            if resultado["motivo"] == "evento já tem acréscimos" and orcamento_tem_bv:
                relatorio["bv_confira"] = aviso_acrescimos
        if resultado["bv_total"] > 0:
            relatorio["bv_para"] = (recebedor or "").strip() or None
            inicio = getattr(event, "start_at", None)
            hoje = now_sp().date()
            if inicio is not None and (inicio.year, inicio.month) < (hoje.year, hoje.month):
                relatorio["bv_planilha"] = f"{inicio.month:02d}/{inicio.year}"
        return
    if not orcamento_tem_bv:
        return
    if not sem_valor_de_venda(event.sale_value) and not getattr(event, "is_cortesia_permuta", False):
        relatorio.setdefault("acrescimos_ignorados", "evento já tem venda")
        if ja_tem_bv:
            relatorio["bv_confira"] = aviso_acrescimos
        elif bv_do_orcamento_pendente(event, novo_vinculo=novo_vinculo):
            relatorio["bv_pendente_frase"] = (
                "o BV do orçamento não entra sozinho: lance-o em Acréscimos, com quem recebe e o PIX, "
                "e confira se o valor de venda é o total com o BV"
            )


# ── o vínculo ─────────────────────────────────────────────────────────────────────────────────

def outro_evento_vivo_do_orcamento(entry_id: int, *, exceto_event_id: int | None) -> CalendarEvent | None:
    """Evento não cancelado que já aponta para este orçamento (1:1 entre vivos)."""
    q = CalendarEvent.query.filter(
        CalendarEvent.orcamento_history_id == entry_id, CalendarEvent.cancelled_at.is_(None)
    )
    if exceto_event_id is not None:
        q = q.filter(CalendarEvent.id != exceto_event_id)
    return q.first()


def desvincular_eventos_cancelados(entry_id: int, *, actor_name: str, tz: Any) -> list[int]:
    """Solta o FK dos eventos CANCELADOS que ainda apontam para o orçamento (antes de apagá-lo).

    "Cancelar libera o orçamento" (decisão 5) — mas a 224 mantém a linha cancelada, e a FK sem
    `ondelete` estourava `IntegrityError` no DELETE mesmo sem evento vivo. Cada evento solto
    ganha uma linha no histórico; sem commit.
    """
    soltos: list[int] = []
    cancelados = CalendarEvent.query.filter(
        CalendarEvent.orcamento_history_id == entry_id, CalendarEvent.cancelled_at.isnot(None)
    ).all()
    for ev in cancelados:
        ev.orcamento_history_id = None
        db.session.add(EventLog(
            event_id=ev.id, actor_name=actor_name, actor_role="Comercial",
            message=f"Orçamento #{entry_id} excluído do histórico; vínculo desfeito (evento cancelado)",
            created_at=datetime.now(tz=tz),
        ))
        soltos.append(ev.id)
    return soltos


def set_event_orcamento(
    event: Any,
    entry: OrcamentoHistory | None,
    *,
    actor_name: str,
    tz: Any,
    aplicar_equipe: bool = True,
    aplicar_valores_duracao: int | None = None,
    sale_date=None,
    sincronizar_comissao: Any = None,
    bv_recipient: str | None = None,
    bv_pix: str | None = None,
) -> dict:
    """Vincula (ou desvincula, com ``entry=None``) o orçamento e aplica o que foi vendido. Não comita.

    Args:
        event: O `CalendarEvent` alvo (já sem satélite — a view recusa antes).
        entry: O orçamento, ou ``None`` para desvincular (só solta o FK; nada mais muda).
        actor_name: Quem executa, para o `EventLog`.
        tz: Fuso do carimbo do log.
        aplicar_equipe: Aplica fora de SP + equipe (padrão). Pode ser chamado de novo no mesmo
            orçamento: é idempotente, só cria/marca o que falta.
        aplicar_valores_duracao: 1..4 (tabela) para aplicar venda/transporte/nota/acréscimos em
            evento **sem venda** (cortesia/permuta conta como venda); ``None`` não mexe em valores.
        sale_date: Data da venda a gravar quando os valores forem aplicados (``None`` = hoje SP).
        sincronizar_comissao: Injetado pela view (mesmo arranjo da 267) — chamado quando os
            valores mudaram, para a linha de comissão nascer junto.

    Returns:
        Relatório (contagens, `nao_casados`, `fora_sp`, `valores`) — vai para a resposta da API.

    Raises:
        OrcamentoJaVinculado: outro evento não cancelado já aponta para o orçamento.
    """
    if entry is None:
        anterior = event.orcamento_history_id
        event.orcamento_history_id = None
        if anterior:
            db.session.add(EventLog(
                event_id=event.id, actor_name=actor_name, actor_role="Comercial",
                message=f"Desvinculou o orçamento #{anterior}", created_at=datetime.now(tz=tz),
            ))
        frase = "orçamento desvinculado"
        # Feature 305: desvincular não mexe no BV — o relatório diz que ele continua.
        bv = sum(
            (Decimal(str(a.amount_brl or 0)) for a in EventAcrescimo.query.filter_by(event_id=event.id, is_bv=True)),
            Decimal("0"),
        )
        if bv > 0:
            frase += f"; o BV de {_fmt_reais(bv)} continua no evento — confira em Acréscimos"
        return {"desvinculado": anterior, "frase": frase}

    outro = outro_evento_vivo_do_orcamento(entry.id, exceto_event_id=event.id)
    if outro is not None:
        raise OrcamentoJaVinculado(outro.id)

    novo_vinculo = event.orcamento_history_id != entry.id
    event.orcamento_history_id = entry.id
    relatorio: dict = {"vinculado": entry.id, "novo_vinculo": novo_vinculo}

    if aplicar_equipe:
        relatorio["fora_sp"] = aplicar_fora_sp_do_orcamento(event, entry)
        relatorio.update(aplicar_equipe_do_orcamento(event, entry))
    resultado_bv = None
    if aplicar_valores_duracao:
        resultado_bv = aplicar_valores_do_orcamento(
            event, entry, duracao=aplicar_valores_duracao, sale_date=sale_date,
            bv_recipient=bv_recipient, bv_pix=bv_pix,
        )
        if resultado_bv is not None:
            relatorio["valores"] = aplicar_valores_duracao
            if resultado_bv["criados"] == 0:
                # A venda voltou de "a definir" e o evento já tinha BV: a B10 recalcula o % e avisa do
                # em reais, como na aba Comercial (FR-022) — antes do sync, que já vê o BV certo.
                from app.calendar.comercial_ops import acompanhar_bv_da_venda

                aviso = acompanhar_bv_da_venda(event, resultado_bv["venda_antes"], actor_name=actor_name, tz=tz)
                if aviso:
                    relatorio["bv_acompanhou"] = aviso
            if sincronizar_comissao is not None:
                db.session.flush()
                sincronizar_comissao(event)
        else:
            from app.calendar.event_ops import sem_valor_de_venda

            if not sem_valor_de_venda(event.sale_value):
                relatorio["valores_ignorados"] = "evento já tem venda"
            elif getattr(event, "is_cortesia_permuta", False):
                relatorio["valores_ignorados"] = "evento é cortesia/permuta"
            elif aplicar_valores_duracao not in DURACOES_TABELA:
                relatorio["valores_ignorados"] = "duração fora da tabela (1h a 4h)"
            else:
                relatorio["valores_ignorados"] = "orçamento sem total"

    _relatar_bv(relatorio, event, entry, resultado_bv, novo_vinculo=novo_vinculo, recebedor=bv_recipient)
    frase_bv = frase_do_bv(resultado_bv, entry, venda=event.sale_value, recebedor=bv_recipient) if resultado_bv else None

    quem = entry.client_name or "sem cliente"
    prefixo = "Vinculou o orçamento" if novo_vinculo else "Reaplicou o orçamento"
    relatorio["frase"] = _frase_relatorio(relatorio)
    if frase_bv:
        db.session.add(EventLog(
            event_id=event.id, actor_name=actor_name, actor_role="Comercial",
            message=frase_bv, created_at=datetime.now(tz=tz),
        ))
    db.session.add(EventLog(
        event_id=event.id, actor_name=actor_name, actor_role="Comercial",
        message=f"{prefixo} #{entry.id} ({quem}, {entry.event_date or 'sem data'}): {relatorio['frase']}",
        created_at=datetime.now(tz=tz),
    ))
    return relatorio
