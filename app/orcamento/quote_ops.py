"""Núcleo de negócio da Calculadora de Orçamento (migração 177, US2/US4).

Extraído de `_process_quote()`/`_legacy_quote()` (`app/orcamento/routes.py`) — funções puras
(sem `flask.request`/`render_template`/`flash`/`session`), reusadas tanto pela view Jinja quanto
pelos endpoints de API (`app/api/orcamento_read.py`, `app/api/orcamento_write.py`). Reusa sem
alteração `pricing.py`/`transport.py`/`settings.py`/`pdf.py`, já existentes.
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from app import db
from app.constants import ACRESCIMO_TIPO_BV
from app.educamanto.pricing_ops import AVISTA_FATOR, NF_DIVISOR
from app.models import OrcamentoHistory, User
from app.money import format_brl

from . import produtos as _produtos
from . import settings as _cfg
from .pricing import (
    MARCA_CACHE_FAIXA,
    aplicar_markup,
    cache_na_faixa,
    calcular_maquiador,
    compute_show_pricing,
    get_ator_prices,
    get_cantor_prices,
    get_coordenador_prices,
    get_especial_prices,
    get_tecnico_prices,
    markup_vigente,
)
from .transport import aplicar_deslocamento_cliente, calcular_carro, calcular_van

_ADICIONAL_NOTURNO = 50.0  # R$ por artista/coordenador, somado DEPOIS do markup (linha "pos")
_MARKUP_SERVICE = 1.5


class QuoteValidationError(Exception):
    """Erro de validação de negócio (ex.: orçamento personalizado sem valores).

    ``extra`` vai dentro do objeto de erro da API (``json_error(**extra)``) para a tela agir, não só mostrar — a
    feature 313 manda nele as durações que o orçamento mostra quando o "fechar por R$" aponta para outra.
    """

    def __init__(self, field: str, message: str, extra: dict | None = None) -> None:
        super().__init__(message)
        self.field = field
        self.message = message
        self.extra = extra or {}


def _fmt_brl(value: float) -> str:
    return format_brl(value, prefix=True)


_CENTAVO = Decimal("0.01")


def bv_que_acompanha(bv: Any, venda: Any, total: Any) -> Decimal:
    """O BV na proporção da venda: ``bv × venda ÷ total``, ao centavo (feature 305, 3a-Q1 = B).

    Fonte única da regra "o BV acompanha o valor total na mesma proporção" — o dono: "se o valor
    total do orçamento mudar, o BV deve acompanhar proporcionalmente". Usada pela gravação do BV do
    orçamento no evento, pelo alerta e pela venda que muda depois; a 3b e a 2b reusam.

    Venda que difere do total em até R$ 0,01 conta como igual (devolve o BV cheio): o total de duração
    extra é arredondado de três jeitos (float aqui, ``Math.round`` no navegador, ``Decimal``) e um
    centavo de diferença não é desconto. Nunca levanta: entrada ruim ou total ≤ 0 devolve 0,00.

    Args:
        bv: o BV cheio (o que o orçamento somou ao preço, ou o BV que já estava no evento).
        venda: o valor de venda (ou o líquido novo, na venda que muda depois).
        total: o total do orçamento na duração (ou o líquido anterior).

    Returns:
        O BV em ``Decimal`` com duas casas, ``ROUND_HALF_UP``.
    """
    try:
        bv_d, venda_d, total_d = (Decimal(str(x)) for x in (bv, venda, total))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")
    if not (bv_d.is_finite() and venda_d.is_finite() and total_d.is_finite()) or total_d <= 0:
        return Decimal("0.00")
    if abs(venda_d - total_d) <= _CENTAVO:
        return bv_d.quantize(_CENTAVO, rounding=ROUND_HALF_UP)
    return (bv_d * venda_d / total_d).quantize(_CENTAVO, rounding=ROUND_HALF_UP)


#: Feature 313 — a marca de regra gravada no snapshot: orçamento com ela foi cotado pela ordem da conta da Q7 (o
#: acréscimo em R$ uma vez; o BV sobre a base com os outros acréscimos) e tem `bases`/`brutos`. Sem ela, todo leitor
#: (prefill, evento) segue o caminho de antes — o que foi cotado não muda (020). A noite dos dias será a versão 3.
VERSAO_CONTA = 2

#: O PIX à vista padrão, em %: o mesmo fator do EducaManto. Arredondado porque `(1 − 0,95) × 100` em float dá
#: 5,000000000000004 — e o negociado de exatamente 5% (o caso mais comum) perderia o "já está aplicado".
PIX_PCT_PADRAO = round((1 - AVISTA_FATOR) * 100, 6)


def aplicar_acrescimos(base: float, acrescimos: list[dict], nota: bool) -> dict[str, Any]:
    """O que é do pedido, por cima da base de uma duração, na ordem que o dono deu (feature 313, Q7/Q9).

    "O acréscimo adicionado manualmente é colocado por cima de tudo no valor. E o BV é calculado em cima de tudo
    isso" (Q7). Em ordem: (a) os acréscimos que não são BV — em R$ entram inteiros, uma vez; em % incidem sobre a
    ``base``; (b) o BV em % incide sobre ``base + (a)``, cada linha de BV sobre o mesmo número (os BVs não se veem);
    o BV em reais entra inteiro, uma vez (Q9 = B); (c) a nota fiscal sobre a soma (``÷ NF_DIVISOR``).

    A soma é feita na ordem do snapshot e com os mesmos ``round`` da conta de antes: onde a regra do dono não muda
    o número (BV sozinho, só acréscimos sem BV em %), o centavo é o de sempre — a paridade com os orçamentos salvos.

    Returns:
        ``{"valores": [float por linha], "base_bv": float, "antes_nf": float, "preco": float}`` — ``valores`` sem
        arredondar (a memória arredonda); ``antes_nf`` e ``preco`` ao centavo.
    """
    valores = [0.0] * len(acrescimos)
    add_nao_bv = 0.0
    for k, a in enumerate(acrescimos):
        if a.get("is_bv"):
            continue
        valores[k] = (base * a["value"] / 100.0) if a["is_percent"] else a["value"]
        add_nao_bv += valores[k]
    base_bv = base + add_nao_bv
    for k, a in enumerate(acrescimos):
        if a.get("is_bv"):
            valores[k] = (base_bv * a["value"] / 100.0) if a["is_percent"] else a["value"]
    add = 0.0
    for v in valores:
        add += v
    antes_nf = round(base + add, 2)
    preco = round(antes_nf / NF_DIVISOR, 2) if nota else antes_nf
    return {"valores": valores, "base_bv": base_bv, "antes_nf": antes_nf, "preco": preco}


def _tem_parte_fixa(acrescimos: list[dict], produtos_total: float) -> bool:
    """Acréscimo em R$ (BV em reais inclusive) ou produto de tabela: a duração extra deixa de ser linear."""
    return bool(produtos_total) or any(not a["is_percent"] for a in acrescimos)


def _preco_extra(
    base_4h: float, total_4h: float, produtos_total: float, horas: int, acrescimos: list[dict], nota: bool
) -> dict[str, Any]:
    """O preço de uma duração acima de 4h pela régua da Q7 (feature 313, research R1).

    A régua de horas vale só para a base (o produto de tabela fica fixo, 309); os acréscimos, o BV e a nota vêm por
    cima, uma vez. Sem parte fixa a conta é linear e dá o mesmo número que escalar o preço de 4h — e aí ela escala o
    preço de 4h, com o arredondamento de sempre (refazer pela base mudaria o centavo de metade dos orçamentos com
    nota ou %).

    Returns:
        ``{"preco": float, "valores": [float por linha]}``.
    """
    if not _tem_parte_fixa(acrescimos, produtos_total):
        preco = round(total_4h / 4 * horas, 2)
        quatro = aplicar_acrescimos(base_4h, acrescimos, nota)["valores"]
        return {"preco": preco, "valores": [v / 4 * horas for v in quatro]}
    base_h = (base_4h - produtos_total) / 4 * horas + produtos_total
    conta = aplicar_acrescimos(base_h, acrescimos, nota)
    return {"preco": conta["preco"], "valores": conta["valores"]}


def _linhas_do_snapshot_313(snap: dict) -> list[dict]:
    """Os acréscimos do snapshot na forma que `aplicar_acrescimos` lê (`value` numérico, sem linha vazia)."""
    linhas = []
    for a in snap.get("acrescimos") or []:
        if not isinstance(a, dict) or not a.get("tipo"):
            continue
        try:
            valor = float(a.get("value"))
        except (TypeError, ValueError):
            continue
        if not valor:
            continue
        linhas.append({
            "tipo": a["tipo"],
            "is_percent": bool(a.get("is_percent")),
            "value": valor,
            "is_bv": a["tipo"] == ACRESCIMO_TIPO_BV,
        })
    return linhas


def preco_na_duracao(snap: dict, horas: int) -> dict[str, Any] | None:
    """O preço de um orçamento da versão 2 numa duração qualquer, a partir do snapshot salvo (research R1).

    Fonte única do que a calculadora mostrou, para o prefill do Novo evento ("Outra (h)") e o evento (o BV e a
    dedução de duração). 1–4h: o cheio gravado (`brutos`) e as linhas do `valores_brl`; acima de 4h: `_preco_extra`
    sobre as bases. No personalizado o cheio acima de 4h é a régua sobre `brutos["4h"]` (o produto fixo, sem
    acréscimos nem nota). O total aplica o desconto do snapshot.

    Returns:
        ``{"bruto": float, "linhas": [float por acréscimo], "total": float}``, ou ``None`` quando o snapshot não é
        da versão 2 ou não se sustenta (o chamador segue o caminho de antes).
    """
    if not isinstance(snap, dict) or snap.get("versao_conta") != VERSAO_CONTA:
        return None
    try:
        brutos = snap.get("brutos") or {}
        d = float(snap.get("desconto_aplicado") or 0)
        horas = int(horas)
        produtos_total = float(snap.get("produtos_total") or 0)
        personalizado = bool(snap.get("personalizado_ativo"))
        linhas_acr = _linhas_do_snapshot_313(snap)
        if horas in (1, 2, 3, 4):
            bruto = float(brutos[f"{horas}h"])
            linhas = []
            for a in snap.get("acrescimos") or []:
                if isinstance(a, dict) and a.get("tipo") and a.get("value"):
                    lista = a.get("valores_brl") or [0, 0, 0, 0]
                    linhas.append(float(lista[horas - 1]))
        elif personalizado:
            quatro = float(brutos["4h"])
            bruto = round((quatro - produtos_total) / 4 * horas + produtos_total, 2)
            linhas = [0.0] * len(linhas_acr)
        else:
            bases = snap.get("bases") or []
            extra = _preco_extra(
                float(bases[3]), float(brutos["4h"]), produtos_total, horas, linhas_acr, bool(snap.get("nota_fiscal"))
            )
            bruto, linhas = extra["preco"], extra["valores"]
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    total = round(bruto * (1 - d / 100), 2) if d else bruto
    # A duração em que a comercial digitou o valor final sai com o valor exato (Q8 = B); a extra só é "a digitada"
    # se for a mesma duração extra do orçamento.
    alvo = f"{horas}h" if horas <= 4 else ("extra" if int(float(snap.get("duracao_custom") or 0)) == horas else None)
    if d and alvo and snap.get("desconto_duracao") == alvo and snap.get("desconto_valor") is not None:
        total = round(float(snap["desconto_valor"]), 2)
    return {"bruto": bruto, "linhas": linhas, "total": total}


def _vazio(valor: Any) -> bool:
    return valor is None or (isinstance(valor, str) and not valor.strip())


def _ler_desconto(
    payload: dict, brutos: list[float], bruto_custom: float | None, mostradas: list[str]
) -> tuple[float, str | None, float | None, float | None, str | None]:
    """O desconto negociado da entrada (feature 313, Q8 = B: "ou digita o valor e mostra a porcentagem, ou digita a
    porcentagem e calcula o valor").

    Com ``desconto_valor`` + ``desconto_duracao``, o % é achado sem arredondar sobre o cheio daquela duração (e
    ``desconto_pct`` é ignorado); sem eles, vale ``desconto_pct``. Vazio, 0 ou o valor igual ao cheio = sem desconto.

    Returns:
        ``(d, modo, pct digitado, valor digitado, duração)`` — ``d`` é o % exato (0 sem desconto).

    Raises:
        QuoteValidationError: o campo que está errado (`desconto_pct` ou `desconto_valor`).
    """
    raw_valor, raw_dur, raw_pct = (payload.get(k) for k in ("desconto_valor", "desconto_duracao", "desconto_pct"))
    sem = (0.0, None, None, None, None)
    if not _vazio(raw_valor) or not _vazio(raw_dur):
        if _vazio(raw_valor) or _vazio(raw_dur):
            raise QuoteValidationError("desconto_valor", "Informe o valor final e a duração a que ele se refere.")
        try:
            valor = float(raw_valor)
        except (TypeError, ValueError):
            raise QuoteValidationError("desconto_valor", "O valor final precisa ser um número.") from None
        if isinstance(raw_valor, bool) or raw_dur not in mostradas:
            # As mostradas vão junto: a tela troca o seletor por elas (sem isso, ele ficava preso nas durações do
            # resultado anterior — ex.: "fechar 2h por" e a comercial deixa só um produto, que mostra um valor).
            raise QuoteValidationError(
                "desconto_valor",
                "Escolha uma das durações que o orçamento mostra.",
                {"duracoes_do_desconto": list(mostradas)},
            )
        cheio = bruto_custom if raw_dur == "extra" else brutos[int(raw_dur[0]) - 1]
        if not cheio or valor != valor or valor <= 0 or valor > cheio + 0.005:
            raise QuoteValidationError(
                "desconto_valor",
                f"O valor final precisa ser maior que zero e até o valor cheio ({_fmt_brl(cheio or 0)}).",
            )
        if abs(valor - cheio) <= 0.005:
            return sem
        return (1 - valor / cheio) * 100, "valor", None, round(valor, 2), raw_dur
    if _vazio(raw_pct):
        return sem
    try:
        pct = float(raw_pct)
    except (TypeError, ValueError):
        raise QuoteValidationError("desconto_pct", "O desconto precisa ser um número.") from None
    if isinstance(raw_pct, bool) or pct != pct or pct < 0 or pct >= 100:
        raise QuoteValidationError("desconto_pct", "O desconto precisa ser de 0 a menos de 100%.")
    if pct == 0:
        return sem
    return pct, "pct", pct, None, None


def texto_do_percentual(d: float) -> str:
    """O % como a proposta mostra (feature 313, Q3 = A): uma casa, para baixo, com vírgula e sem ",0".

    A proposta nunca promete mais desconto do que dá (4,96% → "4,9"). O ``round(d, 6)`` antes do piso evita que 10%
    achado pelo valor digitado (9,9999999…) vire "9,9".
    """
    piso = Decimal(str(round(d, 6))).quantize(Decimal("0.1"), rounding="ROUND_FLOOR")
    texto = f"{piso:.1f}".replace(".", ",")
    return texto[:-2] if texto.endswith(",0") else texto


def _is_noturno(raw_time: str) -> bool:
    """Retorna True se o horário do evento for a partir das 19h."""
    try:
        return datetime.strptime(raw_time, "%H:%M").hour >= 19
    except ValueError:
        return False


def _rotulo_da_faixa(faixa: dict, raw_date: str) -> str:
    """Ex.: ``"Véspera e Natal · 24/12"`` — o detalhe da linha de markup na memória de cálculo.

    Sem parênteses de propósito: a tela já envolve o detalhe em parênteses.
    """
    dia_mes = f"{raw_date[8:10]}/{raw_date[5:7]}" if len(raw_date) == 10 else raw_date
    return f"{faixa['rotulo']} · {dia_mes}"


def calculate_quote(payload: dict[str, Any]) -> dict[str, Any]:
    """Calcula um orçamento a partir do payload do formulário (elenco/horas/transporte/show).

    Args:
        payload: dict com as mesmas chaves do formulário legado — ver
            `specs/177-migracao-ferramentas-react/contracts/api-endpoints.md`
            (`POST /api/orcamento/calcular`) para o shape completo.

    Returns:
        `{"quote": {...}, "snapshot": {...}}` — `quote` é o resultado pronto para exibição/PDF/
        e-mail; `snapshot` é o estado de entrada, usado para reabrir o formulário no histórico.

    Raises:
        QuoteValidationError: orçamento personalizado sem nenhum valor válido informado.
    """
    performers: list[dict] = payload.get("performers") or []

    coordenador_qty_raw = int(payload.get("coordenador_qty") or 1)
    dj_only = len(performers) > 0 and all(
        p.get("type") == "especial" and p.get("personagem") == "DJ" for p in performers
    )
    coordenador_qty = max(0 if dj_only else 1, coordenador_qty_raw)

    # A tabela de preços é carregada UMA vez aqui e repassada onde a feature 307 precisa dela.
    cfg_precos = _cfg.load()
    regras = cfg_precos.get("especiais_regras", {})
    for p in performers:
        if p.get("type") == "especial":
            minimo = regras.get(p.get("personagem", ""), {}).get("min_coordenadores", 1)
            coordenador_qty = max(coordenador_qty, minimo)

    fora_sp = bool(payload.get("fora_sp"))
    # Chave ausente (snapshots antigos, EducaManto) = "manto" — comportamento pré-feature.
    deslocamento_responsavel = payload.get("deslocamento_responsavel") or "manto"
    if deslocamento_responsavel != "cliente":
        deslocamento_responsavel = "manto"
    event_time = payload.get("event_time") or ""
    noturno = _is_noturno(event_time)
    # Feature 307: a faixa de data especial (24 e 25/12 na tabela de preços) é resolvida UMA vez
    # pela data do evento e passada aos getters. Sem faixa (data vazia, chave ausente em snapshot
    # antigo, EducaManto) a conta é a de sempre, byte a byte.
    raw_date = payload.get("event_date") or ""
    faixa = _cfg.faixa_especial(raw_date, cfg_precos)

    # Feature 309: produtos de tabela (a Visita Mágica) — preço fixo por visita, fora do markup; as
    # vagas deles contam para coordenador, maquiagem e van. Chave ausente = conta de hoje. Produto que
    # sumiu da tabela recusa a venda (molde do personagem removido, feature 254).
    try:
        produtos = _produtos.aplicar(payload.get("produtos"), cfg_precos, faixa)
    except _produtos.ProdutoDesconhecido as exc:
        raise QuoteValidationError(
            "produtos",
            f'O produto "{exc.chave}" não está mais na tabela de preços — remova-o do orçamento ou '
            "peça ao superadmin para recriá-lo.",
        ) from exc
    # O coordenador do produto não é cobrado em dobro: `coordenador_qty` passa a ser o total vendido
    # (vai ao snapshot e ao teto) e só `coord_formula` entra na fórmula.
    coordenador_qty, coord_formula, coord_inclusos = _produtos.split_coordenadores(coordenador_qty, produtos)
    makes_produtos = _produtos.makes_dos_produtos(produtos)
    produtos_total = _produtos.somar_produtos(produtos)

    acrescimos: list[dict] = []
    for a in payload.get("acrescimos") or []:
        tipo = (a.get("tipo") or "").strip()
        value = a.get("value")
        if not tipo or not value:
            continue
        acrescimos.append({
            "tipo": tipo,
            "descricao": (a.get("descricao") or "").strip(),
            "is_percent": bool(a.get("is_percent")),
            "value": float(value),
            "is_bv": tipo == ACRESCIMO_TIPO_BV,
        })

    show_sosia_tipo = payload.get("show_sosia_tipo") or "predefinido"
    nota_fiscal = bool(payload.get("nota_fiscal"))
    modo_duracao = payload.get("modo_duracao") or "horas"
    duracao_custom = int(payload.get("duracao_custom") or 0)

    event_has_show, sosia_custom_add_per_artist = compute_show_pricing(performers, show_sosia_tipo)
    event_has_makeup = False
    num_makes_regular = 0
    num_makes_especial = 0

    for p in performers:
        ptype = p.get("type", "")
        makeup = bool(p.get("makeup", False))
        makeup_tipo = p.get("makeup_tipo", "comum")
        if makeup and ptype in ("ator", "cantor", "especial"):
            event_has_makeup = True
            if makeup_tipo == "especial":
                num_makes_especial += 1
            else:
                num_makes_regular += 1

    cache_totals = [0.0, 0.0, 0.0, 0.0]
    # Personagens do produto antes dos avulsos — a mesma ordem que o teto das vagas emite.
    team_lines: list[str] = _produtos.labels_de_personagem(produtos)
    num_going = coordenador_qty + len(team_lines)

    # Memória de cálculo: uma linha por parcela que entra na conta, na ordem em que entra.
    # Existe só para exibição — nenhum valor daqui volta para o cálculo. O `tipo` diz ao React
    # como pintar a linha: cache (pré-markup), info (não soma no cachê), subtotal, markup,
    # pos (somado depois do markup) e total.
    memoria: list[dict[str, Any]] = []

    def _linha(label: str, valores, tipo: str, detalhe: str = "") -> None:
        memoria.append({
            "label": label,
            "detalhe": detalhe,
            "valores": [round(float(v), 2) for v in valores],
            "tipo": tipo,
        })

    def _linha_fixa(label: str, valor: float, tipo: str, detalhe: str = "") -> None:
        _linha(label, [valor] * 4, tipo, detalhe)

    for p in performers:
        ptype = p.get("type", "")
        show = bool(p.get("show", False))
        makeup = bool(p.get("makeup", False))
        nome = (p.get("nome") or "").strip()

        partes: list[str] = []
        if ptype == "ator":
            subtipo = p.get("subtipo", "cara_limpa")
            if subtipo == "cantor":
                prices = get_cantor_prices(show, makeup)
                label = nome or "Cantor"
                partes.append("cantor")
            else:
                prices = get_ator_prices(subtipo, show, makeup)
                label = nome or ("Boneco" if subtipo == "boneco" else "Ator")
                partes.append("boneco" if subtipo == "boneco" else "cara limpa")
            if show:
                partes.append("show")
            if makeup:
                partes.append(f"make {p.get('makeup_tipo', 'comum')}")
        elif ptype == "cantor":
            prices = get_cantor_prices(show=True, makeup=makeup)
            label = nome or "Cantor"
            partes.append("cantor")
            if makeup:
                partes.append("make")
        elif ptype == "especial":
            personagem = p.get("personagem", "")
            cantor_flag = bool(p.get("cantor", False))
            # Recalcular um orçamento antigo cujo personagem foi REMOVIDO da tabela de preços
            # (feature 254): sem esta checagem o preço saía silenciosamente zerado — e antes
            # dela, com o default de 3 itens, o cálculo inteiro caía com IndexError.
            if personagem and personagem not in _cfg.load()["especiais"]:
                raise QuoteValidationError(
                    "performers",
                    f'O personagem "{personagem}" não está mais na tabela de preços. '
                    "Remova-o do orçamento ou recadastre-o nas Configurações de Preços.",
                )
            prices = get_especial_prices(personagem, show, cantor_flag, faixa=faixa)
            if personagem == "Boneco Grande Especial":
                bge_sub = p.get("bge_subtipo", "")
                bge_nome = (p.get("bge_outro_nome") or "").strip()
                if bge_sub == "dinossauro":
                    label = "BGE Dinossauro"
                elif bge_sub == "transformers":
                    label = "BGE Transformers"
                elif bge_sub == "outro" and bge_nome:
                    label = f"BGE {bge_nome}"
                else:
                    label = nome or personagem
            else:
                label = nome or personagem
            if cantor_flag:
                partes.append("cantor")
            elif show:
                partes.append("show")
        else:
            prices = (0, 0, 0, 0)
            label = nome or "Profissional"

        prices, marca = cache_na_faixa(p, prices, faixa)
        if marca:
            partes.append(marca)

        team_lines.append(label)
        num_going += 1
        for i in range(4):
            cache_totals[i] += prices[i]
        _linha(label, prices, "cache", ", ".join(partes))

    if sosia_custom_add_per_artist:
        custom_add = len(performers) * sosia_custom_add_per_artist
        for i in range(4):
            cache_totals[i] += custom_add
        _linha_fixa(
            "Show customizado", custom_add, "cache",
            f"{len(performers)} artista(s) × {_fmt_brl(sosia_custom_add_per_artist)}",
        )

    coord_prices = get_coordenador_prices(event_has_show, coord_formula, faixa=faixa)
    for i in range(4):
        cache_totals[i] += coord_prices[i]
    _linha(
        f"Coordenador(es) ({coordenador_qty})", coord_prices, "cache",
        ("com show" if event_has_show else "sem show")
        + (f", {MARCA_CACHE_FAIXA}" if faixa is not None else "")
        + (f", {coord_inclusos} no produto" if coord_inclusos else ""),
    )

    cache_base = [round(v, 2) for v in cache_totals]
    personalizado = bool(payload.get("personalizado"))
    criterio_pers = payload.get("personalizado_criterio") or "valor_final"
    cust_mult = [0.0, 0.0, 0.0, 0.0]

    brinde = 0.0
    if event_has_show:
        num_going += 1
        brinde = float(_cfg.load().get("brinde_show", 100))

    _linha("Subtotal cachê", cache_base, "subtotal")

    markup_aplicado = markup_vigente(event_has_show, faixa, cfg_precos)
    totals = aplicar_markup(cache_totals, event_has_show, faixa=faixa, settings=cfg_precos)
    _linha(
        "× Markup", markup_aplicado, "markup",
        _rotulo_da_faixa(faixa, raw_date) if faixa is not None
        else ("Show" if event_has_show else "Receptivo / Interativo"),
    )
    _linha("= Após markup", totals, "subtotal")

    # Feature 309: o produto entra DEPOIS do markup e ANTES de brinde/noturno/técnico/maquiador/
    # transporte/acréscimos/NF — assim o BV % e a NF incidem sobre ele (conta inversa da 305 intacta)
    # e o markup nunca o multiplica. Igual nas quatro durações.
    if produtos:
        for i in range(4):
            totals[i] = round(totals[i] + produtos_total, 2)
        memoria.extend(_produtos.linhas_da_memoria(produtos, faixa))
        _linha("= Após produtos", totals, "subtotal")

    if brinde:
        for i in range(4):
            totals[i] = round(totals[i] + brinde, 2)
        _linha_fixa("Brinde do show", brinde, "pos")

    if noturno:
        # O produto embute o noturno (`inclui_noturno`); só avulsos e coordenadores da fórmula somam.
        pessoas_noturno = len(performers) + coord_formula + _produtos.noturno_do_produto(produtos)
        adicional_noturno = pessoas_noturno * _ADICIONAL_NOTURNO
        if adicional_noturno:
            for i in range(4):
                totals[i] = round(totals[i] + adicional_noturno, 2)
            _linha_fixa(
                "Adicional noturno", adicional_noturno, "pos",
                f"{pessoas_noturno} pessoa(s) × {_fmt_brl(_ADICIONAL_NOTURNO)}",
            )

    if event_has_show:
        tecnico = get_tecnico_prices()
        tecnico_com_markup = [round(v * _MARKUP_SERVICE, 2) for v in tecnico]
        for i in range(4):
            totals[i] = round(totals[i] + tecnico_com_markup[i], 2)
        _linha("Técnico de som", tecnico_com_markup, "pos", f"markup de serviço {_MARKUP_SERVICE}×")

    if event_has_makeup:
        # Feature 309: a make do Noel do produto já está no preço do produto — o avulso maquiado paga só
        # o degrau seguinte da tabela (incremento), não o make_1 de novo.
        if produtos:
            maquiador_cost = _produtos.incremento_make(makes_produtos, num_makes_regular, num_makes_especial)
        else:
            maquiador_cost = calcular_maquiador(num_makes_regular, num_makes_especial)
        maq_with_markup = round(maquiador_cost * _MARKUP_SERVICE, 2)
        for i in range(4):
            totals[i] = round(totals[i] + maq_with_markup, 2)
        _linha_fixa(
            "Maquiador", maq_with_markup, "pos",
            f"{num_makes_regular + num_makes_especial} make(s), markup de serviço {_MARKUP_SERVICE}×"
            + (f" (incremento sobre {makes_produtos} make(s) do produto)" if produtos else ""),
        )

    transport_total = 0.0
    seen_transport: set = set()
    for p in performers:
        if p.get("type") == "especial":
            personagem = p.get("personagem", "")
            if personagem not in seen_transport:
                transport_esp = regras.get(personagem, {}).get("transporte_especial", 0)
                if transport_esp:
                    for i in range(4):
                        totals[i] = round(totals[i] + transport_esp, 2)
                    transport_total += transport_esp
                    seen_transport.add(personagem)
                    _linha_fixa(
                        "Transporte especial", transport_esp, "pos", personagem,
                    )

    for p in performers:
        if p.get("type") == "especial" and p.get("personagem") == "Boneco Grande Especial":
            bge_sub = p.get("bge_subtipo", "")
            bge_extra = 130 if bge_sub == "dinossauro" else 70 if bge_sub == "transformers" else 0
            if bge_extra:
                for i in range(4):
                    totals[i] = round(totals[i] + bge_extra, 2)
                _linha_fixa("Adicional BGE", bge_extra, "pos", bge_sub)

    transport_breakdown = None
    if fora_sp:
        km_ida = float(payload.get("km_ida") or 0)
        transporte_tipo = payload.get("transporte_tipo") or "van"
        num_colaboradores = int(payload.get("num_colaboradores") or num_going)

        if transporte_tipo == "van":
            carretinha = bool(payload.get("carretinha"))
            tb = calcular_van(num_colaboradores, km_ida, carretinha, event_has_show)
        else:
            num_carros = int(payload.get("num_carros") or 1)
            tb = calcular_carro(num_carros, num_colaboradores, km_ida, event_has_show)

        if deslocamento_responsavel == "cliente":
            tb = aplicar_deslocamento_cliente(tb)

        transport_breakdown = tb
        for i in range(4):
            totals[i] = round(totals[i] + tb["total"], 2)
        if deslocamento_responsavel == "cliente":
            # Fora do `transport_total` de propósito: sem linha "Logística e Transporte" na
            # mensagem — os adicionais ficam embutidos no valor da apresentação.
            _linha_fixa(
                "Adicionais fora de SP", tb["total"], "pos",
                f"deslocamento por conta da contratante — {transporte_tipo} não incluído · "
                f"{num_colaboradores} pessoa(s) · {km_ida:g} km (ida)",
            )
        else:
            transport_total += tb["total"]
            _linha_fixa(
                "Transporte fora de SP", tb["total"], "pos",
                f"{transporte_tipo} · {num_colaboradores} pessoa(s) · {km_ida:g} km (ida)",
            )

    # Feature 313: a base de cada duração antes do que é do pedido (acréscimos, BV, nota) — gravada no snapshot
    # para o prefill e o evento refazerem qualquer duração pela mesma conta (`preco_na_duracao`).
    bases = list(totals)
    if acrescimos:
        # Feature 313 (Q7/Q9): a ordem do dono — acréscimo manual uma vez, BV sobre tudo isso, nota no fim.
        contas = [aplicar_acrescimos(t, acrescimos, False) for t in totals]
        for k, a in enumerate(acrescimos):
            valores = [round(c["valores"][k], 2) for c in contas]
            rotulo = a["tipo"] + (f" — {a['descricao']}" if a["descricao"] else "")
            sufixo = f"{a['value']:g}%" if a["is_percent"] else _fmt_brl(a["value"])
            _linha(f"Acréscimo: {rotulo}", valores, "pos", sufixo)
            # Feature 305: o que este acréscimo somou ao preço em cada duração, em reais, gravado no
            # snapshot — é daqui que o evento tira o BV do orçamento (a memória acima é só exibição,
            # em float). A conta é a mesma, em Decimal HALF_UP; no meio centavo pode diferir da
            # memória em R$ 0,01, e quem lê aceita essa tolerância. O BV em % incide sobre a base COM os
            # outros acréscimos (313, Q7) — `base_bv` da conta.
            a["valores_brl"] = [
                float(
                    (
                        Decimal(str(c["base_bv"] if a["is_bv"] else t)) * Decimal(str(a["value"])) / 100
                    ).quantize(_CENTAVO, rounding=ROUND_HALF_UP)
                )
                if a["is_percent"]
                else float(Decimal(str(a["value"])).quantize(_CENTAVO, rounding=ROUND_HALF_UP))
                for t, c in zip(totals, contas, strict=True)
            ]
        totals = [c["antes_nf"] for c in contas]

    if nota_fiscal:
        antes_nf = list(totals)
        totals = [round(t / NF_DIVISOR, 2) for t in totals]
        _linha(
            "Nota fiscal", [round(totals[i] - antes_nf[i], 2) for i in range(4)], "pos",
            "valor bruto = líquido ÷ 0,84",
        )

    total_custom = None
    conta_extra: dict[str, Any] | None = None
    if duracao_custom > 0 and duracao_custom not in (1, 2, 3, 4):
        # Feature 313 (Q7): a régua de horas só na base; o acréscimo em R$ uma vez; o produto fixo (309). Sem parte
        # fixa, o mesmo número de sempre (o preço de 4h escalado). A mesma conta do prefill e do evento.
        conta_extra = _preco_extra(bases[3], totals[3], produtos_total, duracao_custom, acrescimos, nota_fiscal)
        total_custom = conta_extra["preco"]

    # No personalizado "multiplicador" o produto NÃO é multiplicado: soma por fora. A validação de
    # "valores válidos" olha a base × multiplicador, como hoje — senão um multiplicador zerado passaria.
    base_validacao = None
    if personalizado:
        if criterio_pers == "multiplicador":
            cust_mult = [float(payload.get(f"cust_mult_{d}") or 0) for d in ("1h", "2h", "3h", "4h")]
            base_validacao = [round(cache_base[i] * cust_mult[i], 2) for i in range(4)]
            totals = [round(base_validacao[i] + produtos_total, 2) for i in range(4)]
        else:
            totals = [float(payload.get(f"cust_valor_{d}") or 0) for d in ("1h", "2h", "3h", "4h")]
        transport_breakdown = None
        transport_total = 0.0
        total_custom = None
        # Feature 305: no personalizado nenhum acréscimo é somado ao preço — o que vai ao evento é zero.
        for a in acrescimos:
            a["valores_brl"] = [0.0, 0.0, 0.0, 0.0]

        # No personalizado o valor final é digitado (ou vem de um multiplicador sobre o cachê-base):
        # transporte, NF e acréscimos NÃO são somados. A memória acompanha — mostrar as parcelas
        # automáticas aqui daria a entender que elas entraram na conta.
        memoria = [linha for linha in memoria if linha["tipo"] == "cache"]
        _linha("Subtotal cachê (base)", cache_base, "subtotal")
        if criterio_pers == "multiplicador":
            _linha("× Multiplicador personalizado", cust_mult, "markup")
            # Feature 309: o produto volta à memória depois do multiplicador (Σcache × mult + Σproduto).
            memoria.extend(_produtos.linhas_da_memoria(produtos, faixa))
        else:
            _linha("Valor final digitado", totals, "markup")

        incluir_chk = payload.get("incluir_duracao") or ["1h", "2h", "3h", "4h"]
        idx = {"1h": 0, "2h": 1, "3h": 2, "4h": 3}
        conferidos = base_validacao if base_validacao is not None else totals
        # Converge 309: só produto + multiplicador tem base zero (o coordenador está no produto) —
        # o produto é um valor válido por si. Com base (avulsos), multiplicador zerado continua erro.
        tem_produto_no_total = (
            criterio_pers == "multiplicador" and produtos_total > 0 and all(b <= 0 for b in cache_base)
        )
        if not tem_produto_no_total and all(conferidos[idx[d]] <= 0 for d in incluir_chk if d in idx):
            raise QuoteValidationError(
                "personalizado", "Informe valores válidos para o orçamento personalizado."
            )
        if criterio_pers != "multiplicador":
            # Converge 309: no valor final o produto NÃO está dentro do total digitado — `produtos_total`
            # zero no quote/snapshot para a régua do evento (prefill, `_total_da_duracao`) ser a linear.
            produtos_total = 0.0

    # Feature 313: o preço cheio de cada duração — o "valor antes do desconto" que vai ao evento.
    brutos = list(totals)
    bruto_custom = total_custom

    # Feature 313 (D3, Q1 = A, Q8 = B): o desconto negociado é o ÚLTIMO passo, sobre o total (apresentação,
    # transporte, acréscimos e nota). As durações que a proposta mostra são as que aceitam "fechar por R$".
    so_produto_d = bool(produtos) and not performers and coord_formula == 0
    incluir_d = payload.get("incluir_duracao") or ["1h", "2h", "3h", "4h"]
    mostradas = ["1h"] if so_produto_d else [d for d in ("1h", "2h", "3h", "4h") if d in incluir_d]
    if total_custom and not so_produto_d:
        mostradas.append("extra")
    desconto, desconto_modo, desconto_digitado, desconto_valor, desconto_duracao = _ler_desconto(
        payload, brutos, bruto_custom, mostradas
    )
    if desconto:
        totals = [round(b * (1 - desconto / 100), 2) for b in brutos]
        if total_custom:
            total_custom = round(bruto_custom * (1 - desconto / 100), 2)
        if desconto_modo == "valor":
            # A duração digitada sai com o valor exato (R$ 2.200,00, não R$ 2.199,99).
            if desconto_duracao == "extra":
                total_custom = desconto_valor
            else:
                totals[int(desconto_duracao[0]) - 1] = desconto_valor
        _linha(
            f"Desconto ({texto_do_percentual(desconto)}%)",
            [totals[i] - brutos[i] for i in range(4)],
            "pos",
            "sobre o total — apresentação, transporte, acréscimos e nota",
        )

    _linha("TOTAL FINAL AO CLIENTE", totals, "total")

    # Feature 313 (3a-Q1 = B): o BV de quem indicou acompanha o valor final, na mesma proporção — pela função
    # única da 305. O BV cheio é o que as linhas de BV somaram ao preço (no personalizado, nada).
    linhas_bv = [a for a in acrescimos if a["is_bv"]] if not personalizado else []
    bv_cheio = [sum(a["valores_brl"][i] for a in linhas_bv) for i in range(4)] if linhas_bv else None
    bv_cheio_custom = None
    if linhas_bv and conta_extra is not None:
        bv_cheio_custom = float(
            sum(
                (Decimal(str(conta_extra["valores"][k])) for k, a in enumerate(acrescimos) if a["is_bv"]),
                Decimal("0"),
            ).quantize(_CENTAVO, rounding=ROUND_HALF_UP)
        )

    def _bv_acompanha(cheio: float | None, venda: float | None, bruto: float | None) -> float | None:
        if cheio is None or not venda or not bruto:
            return None
        return float(bv_que_acompanha(cheio, venda, bruto))

    # Feature 313 (D4): o PIX à vista vale o maior entre o padrão (5%) e o negociado — nunca soma. Com o negociado de
    # 5% ou mais, o PIX é o próprio valor final (e o BV, o mesmo), sem refazer a conta.
    pix_maior = bool(desconto) and round(desconto, 6) >= PIX_PCT_PADRAO
    pix_pct = desconto if pix_maior else PIX_PCT_PADRAO
    pix = [totals[i] if pix_maior else round(brutos[i] * AVISTA_FATOR, 2) for i in range(4)]
    pix_custom = None
    if total_custom:
        pix_custom = total_custom if pix_maior else round(bruto_custom * AVISTA_FATOR, 2)
    bv_final = [_bv_acompanha(bv_cheio[i], totals[i], brutos[i]) for i in range(4)] if bv_cheio else [None] * 4
    bv_pix = (
        [bv_final[i] if pix_maior else _bv_acompanha(bv_cheio[i], pix[i], brutos[i]) for i in range(4)]
        if bv_cheio
        else [None] * 4
    )
    bv_final_custom = _bv_acompanha(bv_cheio_custom, total_custom, bruto_custom)
    bv_pix_custom = bv_final_custom if pix_maior else _bv_acompanha(bv_cheio_custom, pix_custom, bruto_custom)
    if desconto and bv_cheio:
        _linha("BV a repassar a quem indicou (acompanha o desconto)", bv_final, "subtotal")

    raw_time = event_time
    try:
        fmt_date = datetime.strptime(raw_date, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        fmt_date = raw_date
    try:
        fmt_time = datetime.strptime(raw_time, "%H:%M").strftime("%Hh%M")
    except ValueError:
        fmt_time = raw_time

    client_name = (payload.get("client_name") or "").strip()
    event_location = (payload.get("event_location") or "").strip()

    tipo_evento = "Show com Som" if event_has_show else "Interação / Receptivo"
    saudacao = f"Olá, *{client_name}*!" if client_name else "Olá!"
    team_text = "\n".join(f"• {line}" for line in team_lines)

    def _dur_block(label: str, total: float, bruto: float | None = None) -> str:
        # Feature 313 (Q3 = A): com desconto, "de R$ X por R$ Y" e o % arredondado; a quebra apresentação/transporte
        # sai do CHEIO — as duas linhas somam o "de" (o desconto é do total, Q1 = A, nunca só da apresentação).
        bruto = total if bruto is None else bruto
        lines = [label]
        if transport_total > 0:
            apres = round(bruto - transport_total, 2)
            lines.append(f"  • Valor da Apresentação: {_fmt_brl(apres)}")
            lines.append(f"  • Logística e Transporte: {_fmt_brl(transport_total)}")
        if desconto and abs(bruto - total) >= 0.005:
            lines.append(f"  • *VALOR TOTAL: de {_fmt_brl(bruto)} por {_fmt_brl(total)}*")
            lines.append(f"  _(desconto de {texto_do_percentual(desconto)}% aplicado)_")
        else:
            lines.append(f"  • *VALOR TOTAL: {_fmt_brl(total)}*")
        return "\n".join(lines)

    if modo_duracao == "entradas":
        dur_labels = [
            "🎭 *1 entrada de 30 minutos*",
            "🎭 *2 entradas de 30 minutos (2h)*",
            "🎭 *3 entradas de 30 minutos (3h)*",
            "🎭 *4 entradas de 30 minutos (4h)*",
        ]
    else:
        dur_labels = ["🕐 *1 hora*", "🕑 *2 horas*", "🕒 *3 horas*", "🕓 *4 horas*"]

    incluir = payload.get("incluir_duracao") or ["1h", "2h", "3h", "4h"]
    show = [("1h" in incluir), ("2h" in incluir), ("3h" in incluir), ("4h" in incluir)]

    # Feature 309: só produto no orçamento (sem avulso e sem coordenador da fórmula) = UM valor — a
    # Visita é "visita padrão (até 1h)"; listar 2h–4h diria ao cliente que 4 horas de Noel custam o
    # mesmo que 1. Com avulsos, o bloco do produto vem antes das durações.
    so_produto = bool(produtos) and not performers and coord_formula == 0
    if so_produto:
        show = [True, False, False, False]
        total_custom = None
        bruto_custom = pix_custom = bv_final_custom = bv_pix_custom = None
    bloco_produto = _produtos.bloco_da_mensagem(produtos)

    if so_produto:
        investimento = bloco_produto
        # Converge 309: com NF, transporte, BV, noturno por fora ou dois exemplares o total NÃO é o
        # preço do produto — o cliente precisa ver o VALOR TOTAL (e a logística), como nas durações.
        if len(produtos) > 1 or abs(totals[0] - produtos_total) >= 0.005:
            investimento += f"\n\n{_dur_block('🎅 *Total da visita*', totals[0], brutos[0])}"
    else:
        investimento = "\n\n".join(_dur_block(dur_labels[i], totals[i], brutos[i]) for i in range(4) if show[i])
        if bloco_produto:
            investimento = f"{bloco_produto}\n\n{investimento}"

    if total_custom:
        if modo_duracao == "entradas":
            entradas_custom = duracao_custom * 2
            custom_label = f"🎭 *{entradas_custom} entradas de 30 min ({duracao_custom}h)*"
        else:
            custom_label = f"🕐 *{duracao_custom} horas*"
        investimento += f"\n\n{_dur_block(custom_label, total_custom, bruto_custom)}"

    pix_durs = [("1h", totals[0]), ("2h", totals[1]), ("3h", totals[2]), ("4h", totals[3])]
    if so_produto:
        pix_vista = f"  • *{_fmt_brl(pix[0])}*"
    else:
        pix_vista = "\n".join(
            f"  • {lbl}: *{_fmt_brl(pix[i])}*" for i, (lbl, _tot) in enumerate(pix_durs) if show[i]
        )
    if total_custom:
        pix_vista += f"\n  • {duracao_custom}h: *{_fmt_brl(pix_custom)}*"

    # Feature 313 (D4, Q3 = A): o PIX vale o maior. Com o negociado de 5% ou mais não há o que baixar — a proposta
    # diz que o desconto já está aplicado, sem repetir os valores; abaixo disso, o 5% de sempre, pelo cheio.
    if pix_maior:
        pix_bloco = f" o mesmo valor — o desconto de {texto_do_percentual(desconto)}% já está aplicado.\n\n"
    else:
        pix_bloco = f"\n{pix_vista}\n_(desconto especial de 5% aplicado)_\n\n"

    nf_header = "\n🧾 _Valores com Nota Fiscal inclusa_" if nota_fiscal else ""

    # Evento em SP não tem deslocamento — nenhuma frase. Fora de SP, a mensagem sempre diz de
    # quem é a responsabilidade (frases exatas definidas pelo dono, 26/08/2026).
    if fora_sp and deslocamento_responsavel == "cliente":
        deslocamento_nota = "\n\n_O deslocamento é por conta da contratante._"
    elif fora_sp:
        deslocamento_nota = (
            "\n\n_Esse orçamento inclui deslocamento por responsabilidade da Manto Produções._"
        )
    else:
        deslocamento_nota = ""

    # Feature 307: a nota da faixa de data especial (texto da tabela de preços) sai em itálico
    # junto da frase de deslocamento — e também no PDF, que a lê de `quote.data_especial` (o
    # orçamento congelado não relê a tabela).
    nota_faixa = (faixa or {}).get("nota_mensagem") or ""
    nota_especial = f"\n\n_{nota_faixa}_" if nota_faixa else ""

    message = (
        f"{saudacao} ✨ É um prazer preparar a proposta para o seu evento.\n\n"
        f"Estamos prontos para levar toda a magia da Manto Produções para o seu dia especial! "
        f"Confira os detalhes abaixo:\n\n"
        f"📍 *DETALHES DO EVENTO*\n"
        f"• Data: {fmt_date}\n"
        f"• Local: {event_location}\n"
        f"• Horário: {fmt_time}\n"
        f"• Modalidade: {tipo_evento}\n\n"
        f"🎭 *PERSONAGENS E EXPERIÊNCIA*\n"
        f"{team_text}\n\n"
        f"💰 *INVESTIMENTO*{nf_header}\n\n"
        f"{investimento}{deslocamento_nota}{nota_especial}\n\n"
        f"💳 *FORMAS DE PAGAMENTO*\n\n"
        f"1️⃣ *À Vista (PIX):*{pix_bloco}"
        f"2️⃣ *Reserva Programada (PIX):* 50% no ato do contrato + 50% até 2 dias antes do evento.\n\n"
        f"3️⃣ *Cartão de Crédito:* Parcelamento disponível (taxas da operadora repassadas ao cliente).\n\n"
        f"✨ Podemos seguir com a reserva da sua data? "
        f"Aguardamos sua confirmação para enviarmos o link do contrato digital."
    )

    if personalizado:
        markup_used = cust_mult if criterio_pers == "multiplicador" else None
    else:
        markup_used = markup_aplicado

    quote = {
        "message": message,
        "transport_breakdown": transport_breakdown,
        "fora_sp": fora_sp,
        "deslocamento_responsavel": deslocamento_responsavel if fora_sp else None,
        "markup_used": markup_used,
        # Feature 307: a faixa de data especial aplicada (None fora dela; ausente em orçamentos
        # antigos). Leva a nota porque o PDF e o orçamento congelado não releem a tabela.
        "data_especial": (
            {
                "chave": faixa["chave"],
                "rotulo": faixa["rotulo"],
                "markup": list(faixa["markup"]),
                "nota_mensagem": nota_faixa,
            }
            if faixa is not None
            else None
        ),
        # Feature 309: produtos de tabela aplicados — SEMPRE presentes (vazios sem produto): é a
        # presença da chave que diz ao React que o backend conhece produtos (janela de deploy).
        "produtos": _produtos.para_quote(produtos),
        "produtos_total": produtos_total,
        "coordenadores_inclusos": coord_inclusos,
        "avisos": _produtos.avisos_para(performers, produtos),
        # Converge 309: "um valor só" é decisão do servidor — a tela rotula "Preço de tabela" por ela,
        # não pelos `show_*` (produto + avulso com 2h–4h desmarcadas também mostra só 1h).
        "valor_unico": so_produto,
        "total_1h": totals[0],
        "total_2h": totals[1],
        "total_3h": totals[2],
        "total_4h": totals[3],
        "total_custom": total_custom,
        "duracao_custom": duracao_custom,
        "show_1h": show[0],
        "show_2h": show[1],
        "show_3h": show[2],
        "show_4h": show[3],
        "client_name": client_name,
        "fmt_date": fmt_date,
        "fmt_time": fmt_time,
        "event_location": event_location,
        "team_lines": team_lines,
        "nota_fiscal": nota_fiscal,
        "modo_duracao": modo_duracao,
        "personalizado": personalizado,
        "personalizado_criterio": criterio_pers if personalizado else None,
        "cache_base": cache_base if personalizado else None,
        "custom_mult": cust_mult if personalizado else None,
        # Detalhamento linha a linha da conta (só exibição). Vai junto no `form_snapshot` do
        # histórico, então um orçamento salvo reabre com a mesma memória que foi apresentada.
        "memoria": memoria,
        # Feature 313: a base de 4h (antes dos acréscimos) — o ponto de partida de qualquer duração extra.
        "base_4h": None if personalizado else bases[3],
        # Feature 313: o cheio (antes do desconto), o desconto, o PIX que vale o maior e o BV que acompanha.
        **{f"bruto_{i + 1}h": brutos[i] for i in range(4)},
        "bruto_custom": bruto_custom,
        "desconto_pct": desconto or None,
        "desconto_pct_texto": texto_do_percentual(desconto) if desconto else None,
        "desconto_modo": desconto_modo,
        "pix_pct": pix_pct,
        **{f"pix_{i + 1}h": pix[i] for i in range(4)},
        "pix_custom": pix_custom,
        **{f"bv_{i + 1}h": bv_final[i] for i in range(4)},
        "bv_custom": bv_final_custom,
        **{f"bv_pix_{i + 1}h": bv_pix[i] for i in range(4)},
        "bv_pix_custom": bv_pix_custom,
    }

    snapshot = {
        "performers": performers,
        "coordenador_qty": coordenador_qty,
        "fora_sp": fora_sp,
        "deslocamento_responsavel": deslocamento_responsavel,
        "km_ida": str(payload.get("km_ida") or "0"),
        "transporte_tipo": payload.get("transporte_tipo") or "van",
        "carretinha": bool(payload.get("carretinha")),
        "num_carros": str(payload.get("num_carros") or "1"),
        "num_colaboradores": str(payload.get("num_colaboradores") or ""),
        "event_date": raw_date,
        "event_time": raw_time,
        "client_name": client_name,
        "event_location": event_location,
        "acrescimos": acrescimos,
        "show_sosia_tipo": show_sosia_tipo,
        "nota_fiscal": nota_fiscal,
        "modo_duracao": modo_duracao,
        "duracao_custom": str(duracao_custom),
        "personalizado_ativo": personalizado,
        "personalizado_criterio": criterio_pers,
        "cust_mult_1h": str(payload.get("cust_mult_1h") or ""),
        "cust_mult_2h": str(payload.get("cust_mult_2h") or ""),
        "cust_mult_3h": str(payload.get("cust_mult_3h") or ""),
        "cust_mult_4h": str(payload.get("cust_mult_4h") or ""),
        "cust_valor_1h": str(payload.get("cust_valor_1h") or ""),
        "cust_valor_2h": str(payload.get("cust_valor_2h") or ""),
        "cust_valor_3h": str(payload.get("cust_valor_3h") or ""),
        "cust_valor_4h": str(payload.get("cust_valor_4h") or ""),
        "event_has_show": event_has_show,
        # Feature 309: preço E composição congelados — o teto das vagas emite a partir daqui (só o
        # valor do cachê vem da tabela viva na data do evento); a régua do prefill lê `produtos_total`.
        "produtos": _produtos.para_snapshot(produtos),
        "produtos_total": produtos_total,
        # Feature 313 (research R2): a marca de regra e o que o prefill e o evento precisam para refazer qualquer
        # duração pela mesma conta (`preco_na_duracao`), sem a conta inversa da regra antiga.
        "versao_conta": VERSAO_CONTA,
        "desconto_pct_digitado": desconto_digitado,
        "desconto_valor": desconto_valor,
        "desconto_duracao": desconto_duracao,
        "desconto_aplicado": desconto,
        "bases": None if personalizado else [float(b) for b in bases],
        "brutos": {
            **{f"{i + 1}h": brutos[i] for i in range(4)},
            **({"custom": bruto_custom} if bruto_custom else {}),
        },
    }

    return {"quote": quote, "snapshot": snapshot}


def save_quote_history(user: User, quote: dict, snapshot: dict) -> OrcamentoHistory:
    """Persiste o orçamento calculado no histórico (`OrcamentoHistory`)."""
    entry = OrcamentoHistory(
        user_id=user.id,
        client_name=quote.get("client_name") or None,
        event_location=quote.get("event_location") or None,
        event_date=snapshot.get("event_date") or None,
        total_1h=quote["total_1h"],
        total_2h=quote["total_2h"],
        total_3h=quote["total_3h"],
        total_4h=quote["total_4h"],
        has_show=bool(snapshot.get("event_has_show")),
        result_snapshot=json.dumps(quote, ensure_ascii=False),
        form_snapshot=json.dumps(snapshot, ensure_ascii=False),
    )
    db.session.add(entry)
    db.session.commit()
    return entry


def legacy_quote(entry: OrcamentoHistory) -> dict:
    """Monta um quote mínimo a partir dos totais salvos (orçamentos sem snapshot completo)."""
    try:
        fmt_date = (
            datetime.strptime(entry.event_date, "%Y-%m-%d").strftime("%d/%m/%Y")
            if entry.event_date
            else ""
        )
    except ValueError:
        fmt_date = entry.event_date or ""
    return {
        "message": (
            "_(Mensagem original não registrada — orçamento anterior ao registro completo. "
            "Os valores abaixo são os que foram cotados.)_"
        ),
        "transport_breakdown": None,
        "fora_sp": False,
        "deslocamento_responsavel": None,
        "markup_used": None,
        "total_1h": float(entry.total_1h or 0),
        "total_2h": float(entry.total_2h or 0),
        "total_3h": float(entry.total_3h or 0),
        "total_4h": float(entry.total_4h or 0),
        "total_custom": None,
        "duracao_custom": 0,
        "show_1h": True,
        "show_2h": True,
        "show_3h": entry.total_3h is not None,
        "show_4h": True,
        "client_name": entry.client_name or "",
        "fmt_date": fmt_date,
        "fmt_time": "",
        "event_location": entry.event_location or "",
        "team_lines": [],
        "nota_fiscal": False,
        "modo_duracao": "horas",
        "personalizado": False,
        "personalizado_criterio": None,
        "cache_base": None,
        "custom_mult": None,
        # Orçamentos antigos não guardaram a memória — lista vazia é o sinal de "não registrada".
        "memoria": [],
    }


def quote_for_entry(entry: OrcamentoHistory) -> dict:
    """Devolve o quote (congelado) de um registro do histórico, com fallback legado."""
    if entry.result_snapshot:
        try:
            return json.loads(entry.result_snapshot)
        except (json.JSONDecodeError, TypeError):
            return legacy_quote(entry)
    return legacy_quote(entry)


def personagens_no_dia(day) -> list[dict]:
    """Personagens já escalados em eventos na data informada (evita venda duplicada)."""
    from sqlalchemy import func, not_

    from app.models import CalendarEvent, EventRole

    rows = (
        EventRole.query.join(CalendarEvent, EventRole.event_id == CalendarEvent.id)
        .filter(
            EventRole.role_type == "character",
            not_(CalendarEvent.title.like("🟧 ENSAIO%")),
            # Evento cancelado (feature 224) libera o personagem: alertar sobre ele faria o
            # comercial recusar uma venda que está de pé.
            CalendarEvent.cancelled_at.is_(None),
            func.date(CalendarEvent.start_at) == day,
        )
        .with_entities(EventRole.character_name, CalendarEvent.title)
        .all()
    )
    agrupado: dict[str, list[str]] = {}
    for nome, titulo in rows:
        if not nome or not nome.strip():
            continue
        eventos = agrupado.setdefault(nome.strip(), [])
        if titulo and titulo not in eventos:
            eventos.append(titulo)
    return [
        {"nome": nome, "eventos": eventos}
        for nome, eventos in sorted(agrupado.items(), key=lambda kv: kv[0].lower())
    ]
