"""Núcleo de negócio da Calculadora de Orçamento (migração 177, US2/US4).

Extraído de `_process_quote()`/`_legacy_quote()` (`app/orcamento/routes.py`) — funções puras
(sem `flask.request`/`render_template`/`flash`/`session`), reusadas tanto pela view Jinja quanto
pelos endpoints de API (`app/api/orcamento_read.py`, `app/api/orcamento_write.py`). Reusa sem
alteração `pricing.py`/`transport.py`/`settings.py`/`pdf.py`, já existentes.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app import db
from app.constants import ACRESCIMO_TIPO_BV
from app.models import OrcamentoHistory, User
from app.money import format_brl

from . import settings as _cfg
from .pricing import (
    aplicar_markup,
    calcular_maquiador,
    compute_show_pricing,
    get_ator_prices,
    get_cantor_prices,
    get_coordenador_prices,
    get_especial_prices,
    get_tecnico_prices,
)
from .transport import calcular_carro, calcular_van

_ADICIONAL_NOTURNO = 50.0  # R$ por artista/coordenador, aplicado pré-markup
_MARKUP_SERVICE = 1.5


class QuoteValidationError(Exception):
    """Erro de validação de negócio (ex.: orçamento personalizado sem valores)."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


def _fmt_brl(value: float) -> str:
    return format_brl(value, prefix=True)


def _is_noturno(raw_time: str) -> bool:
    """Retorna True se o horário do evento for a partir das 19h."""
    try:
        return datetime.strptime(raw_time, "%H:%M").hour >= 19
    except ValueError:
        return False


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

    regras = _cfg.load().get("especiais_regras", {})
    for p in performers:
        if p.get("type") == "especial":
            minimo = regras.get(p.get("personagem", ""), {}).get("min_coordenadores", 1)
            coordenador_qty = max(coordenador_qty, minimo)

    fora_sp = bool(payload.get("fora_sp"))
    event_time = payload.get("event_time") or ""
    noturno = _is_noturno(event_time)

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
    team_lines: list[str] = []
    num_going = coordenador_qty

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
            prices = get_especial_prices(personagem, show, cantor_flag)
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

    coord_prices = get_coordenador_prices(event_has_show, coordenador_qty)
    for i in range(4):
        cache_totals[i] += coord_prices[i]
    _linha(
        f"Coordenador(es) ({coordenador_qty})", coord_prices, "cache",
        "com show" if event_has_show else "sem show",
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

    markup_aplicado = _cfg.load()["markup"]["show" if event_has_show else "receptivo"]
    totals = aplicar_markup(cache_totals, event_has_show)
    _linha(
        "× Markup", markup_aplicado, "markup",
        "Show" if event_has_show else "Receptivo / Interativo",
    )
    _linha("= Após markup", totals, "subtotal")

    if brinde:
        for i in range(4):
            totals[i] = round(totals[i] + brinde, 2)
        _linha_fixa("Brinde do show", brinde, "pos")

    if noturno:
        adicional_noturno = (len(performers) + coordenador_qty) * _ADICIONAL_NOTURNO
        for i in range(4):
            totals[i] = round(totals[i] + adicional_noturno, 2)
        _linha_fixa(
            "Adicional noturno", adicional_noturno, "pos",
            f"{len(performers) + coordenador_qty} pessoa(s) × {_fmt_brl(_ADICIONAL_NOTURNO)}",
        )

    if event_has_show:
        tecnico = get_tecnico_prices()
        tecnico_com_markup = [round(v * _MARKUP_SERVICE, 2) for v in tecnico]
        for i in range(4):
            totals[i] = round(totals[i] + tecnico_com_markup[i], 2)
        _linha("Técnico de som", tecnico_com_markup, "pos", f"markup de serviço {_MARKUP_SERVICE}×")

    if event_has_makeup:
        maquiador_cost = calcular_maquiador(num_makes_regular, num_makes_especial)
        maq_with_markup = round(maquiador_cost * _MARKUP_SERVICE, 2)
        for i in range(4):
            totals[i] = round(totals[i] + maq_with_markup, 2)
        _linha_fixa(
            "Maquiador", maq_with_markup, "pos",
            f"{num_makes_regular + num_makes_especial} make(s), markup de serviço {_MARKUP_SERVICE}×",
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

        transport_breakdown = tb
        for i in range(4):
            totals[i] = round(totals[i] + tb["total"], 2)
        transport_total += tb["total"]
        _linha_fixa(
            "Transporte fora de SP", tb["total"], "pos",
            f"{transporte_tipo} · {num_colaboradores} pessoa(s) · {km_ida:g} km (ida)",
        )

    if acrescimos:
        for a in acrescimos:
            valores = [
                round(t * a["value"] / 100.0, 2) if a["is_percent"] else a["value"]
                for t in totals
            ]
            rotulo = a["tipo"] + (f" — {a['descricao']}" if a["descricao"] else "")
            sufixo = f"{a['value']:g}%" if a["is_percent"] else _fmt_brl(a["value"])
            _linha(f"Acréscimo: {rotulo}", valores, "pos", sufixo)
        new_totals = []
        for t in totals:
            add = 0.0
            for a in acrescimos:
                add += (t * a["value"] / 100.0) if a["is_percent"] else a["value"]
            new_totals.append(round(t + add, 2))
        totals = new_totals

    if nota_fiscal:
        antes_nf = list(totals)
        totals = [round(t / 0.84, 2) for t in totals]
        _linha(
            "Nota fiscal", [round(totals[i] - antes_nf[i], 2) for i in range(4)], "pos",
            "valor bruto = líquido ÷ 0,84",
        )

    total_custom = None
    if duracao_custom > 0 and duracao_custom not in (1, 2, 3, 4):
        total_custom = round(totals[3] / 4 * duracao_custom, 2)

    if personalizado:
        if criterio_pers == "multiplicador":
            cust_mult = [float(payload.get(f"cust_mult_{d}") or 0) for d in ("1h", "2h", "3h", "4h")]
            totals = [round(cache_base[i] * cust_mult[i], 2) for i in range(4)]
        else:
            totals = [float(payload.get(f"cust_valor_{d}") or 0) for d in ("1h", "2h", "3h", "4h")]
        transport_breakdown = None
        transport_total = 0.0
        total_custom = None

        # No personalizado o valor final é digitado (ou vem de um multiplicador sobre o cachê-base):
        # transporte, NF e acréscimos NÃO são somados. A memória acompanha — mostrar as parcelas
        # automáticas aqui daria a entender que elas entraram na conta.
        memoria = [linha for linha in memoria if linha["tipo"] == "cache"]
        _linha("Subtotal cachê (base)", cache_base, "subtotal")
        if criterio_pers == "multiplicador":
            _linha("× Multiplicador personalizado", cust_mult, "markup")
        else:
            _linha("Valor final digitado", totals, "markup")

        incluir_chk = payload.get("incluir_duracao") or ["1h", "2h", "3h", "4h"]
        idx = {"1h": 0, "2h": 1, "3h": 2, "4h": 3}
        if all(totals[idx[d]] <= 0 for d in incluir_chk if d in idx):
            raise QuoteValidationError(
                "personalizado", "Informe valores válidos para o orçamento personalizado."
            )

    _linha("TOTAL FINAL AO CLIENTE", totals, "total")

    raw_date = payload.get("event_date") or ""
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

    def _dur_block(label: str, total: float) -> str:
        lines = [label]
        if transport_total > 0:
            apres = round(total - transport_total, 2)
            lines.append(f"  • Valor da Apresentação: {_fmt_brl(apres)}")
            lines.append(f"  • Logística e Transporte: {_fmt_brl(transport_total)}")
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

    investimento = "\n\n".join(_dur_block(dur_labels[i], totals[i]) for i in range(4) if show[i])

    if total_custom:
        if modo_duracao == "entradas":
            entradas_custom = duracao_custom * 2
            custom_label = f"🎭 *{entradas_custom} entradas de 30 min ({duracao_custom}h)*"
        else:
            custom_label = f"🕐 *{duracao_custom} horas*"
        investimento += f"\n\n{_dur_block(custom_label, total_custom)}"

    pix_durs = [("1h", totals[0]), ("2h", totals[1]), ("3h", totals[2]), ("4h", totals[3])]
    pix_vista = "\n".join(
        f"  • {lbl}: *{_fmt_brl(round(tot * 0.95, 2))}*" for i, (lbl, tot) in enumerate(pix_durs) if show[i]
    )
    if total_custom:
        pix_vista += f"\n  • {duracao_custom}h: *{_fmt_brl(round(total_custom * 0.95, 2))}*"

    nf_header = "\n🧾 _Valores com Nota Fiscal inclusa_" if nota_fiscal else ""

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
        f"{investimento}\n\n"
        f"💳 *FORMAS DE PAGAMENTO*\n\n"
        f"1️⃣ *À Vista (PIX):*\n"
        f"{pix_vista}\n"
        f"_(desconto especial de 5% aplicado)_\n\n"
        f"2️⃣ *Reserva Programada (PIX):* 50% no ato do contrato + 50% até 2 dias antes do evento.\n\n"
        f"3️⃣ *Cartão de Crédito:* Parcelamento disponível (taxas da operadora repassadas ao cliente).\n\n"
        f"✨ Podemos seguir com a reserva da sua data? "
        f"Aguardamos sua confirmação para enviarmos o link do contrato digital."
    )

    if personalizado:
        markup_used = cust_mult if criterio_pers == "multiplicador" else None
    else:
        markup_used = _cfg.load()["markup"]["show" if event_has_show else "receptivo"]

    quote = {
        "message": message,
        "transport_breakdown": transport_breakdown,
        "fora_sp": fora_sp,
        "markup_used": markup_used,
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
    }

    snapshot = {
        "performers": performers,
        "coordenador_qty": coordenador_qty,
        "fora_sp": fora_sp,
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
