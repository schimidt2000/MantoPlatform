"""Geração do PDF de orçamento do EducaManto.

Dois renderizadores convivem aqui:

- **v2 (feature 235)** — uma página A4 por CONFIGURAÇÃO (musical + responsabilidades), com
  "o que levaremos" / "mínimo exigido" por bloco, quantidades da equipe, avisos fixos,
  valor à vista (5% real) e o trecho da contratação Manto. Todo o conteúdo editorial vem de
  ``pdf_textos.py`` (fonte única; gate de revisão do dono).
- **v1 (features 077/080/082, LEGADO)** — reproduz byte-a-byte o layout antigo por pacote,
  usado SOMENTE para re-renderizar snapshots do histórico gravados antes da feature 235.
  Os textos por nível (Master/Intermediário/Econômica) vivem aqui apenas por isso.

O despacho é por ``snapshot["version"]`` (ausente = v1). Identidade visual Manto compartilhada
(mesmas cores do `orcamento/pdf.py`).
"""
from __future__ import annotations

import io
import unicodedata
from typing import Any

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as rl_canvas

from app.educamanto import pdf_textos
from app.money import format_brl

# Identidade visual Manto (mesmas cores do orcamento/pdf.py)
_PURPLE = HexColor("#2d1f6e")
_GOLD = HexColor("#b8975a")
_GRAY = HexColor("#555555")
_LIGHT = HexColor("#888888")
_BOX_BG = HexColor("#f4f2fb")

_W, _H = A4  # 595 x 842
_LEFT = 56
_RIGHT = _W - 56
_MIN_Y = 60  # abaixo disso, quebra para página de continuação


def _wrap(c: rl_canvas.Canvas, text: str, font: str, size: float, max_width: float) -> list[str]:
    """Quebra `text` em linhas que cabem em `max_width` (pt)."""
    words = (text or "").split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if c.stringWidth(trial, font, size) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ═════════════════════════════════ v2 — feature 235 ═════════════════════════════════════


def _header(c: rl_canvas.Canvas, client_name: str) -> float:
    """Faixa roxa + título; devolve o y inicial do conteúdo."""
    c.setFillColor(_PURPLE)
    c.rect(0, _H - 70, _W, 70, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(_LEFT, _H - 38, "MANTO PRODUÇÕES")
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor("#d8d2f0"))
    c.drawRightString(_RIGHT, _H - 30, pdf_textos.CONTACT_PHONE)
    c.drawRightString(_RIGHT, _H - 44, pdf_textos.CONTACT_EMAIL)

    y = _H - 104
    c.setFillColor(_GOLD)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(_LEFT, y, "ORÇAMENTO")
    if client_name:
        c.setFont("Helvetica", 10)
        c.setFillColor(_LIGHT)
        c.drawRightString(_RIGHT, y + 4, f"Cliente: {client_name}")
    y -= 12
    c.setStrokeColor(_GOLD)
    c.setLineWidth(1.5)
    c.line(_LEFT, y, _RIGHT, y)
    return y - 26


def _footer(c: rl_canvas.Canvas) -> None:
    c.setFillColor(_LIGHT)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(_W / 2, 32, "Manto Produções · EducaManto")


def _titulo_secao(c: rl_canvas.Canvas, y: float, titulo: str) -> float:
    c.setFillColor(_PURPLE)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(_LEFT, y, titulo)
    y -= 5
    c.setStrokeColor(_GOLD)
    c.setLineWidth(0.5)
    c.line(_LEFT, y, _RIGHT, y)
    return y - 12


def _paragrafo(
    c: rl_canvas.Canvas, y: float, texto: str, *,
    size: float = 8.5, indent: float = 0, color=_LIGHT, font: str = "Helvetica",
    leading: float | None = None,
) -> float:
    c.setFont(font, size)
    c.setFillColor(color)
    for ln in _wrap(c, texto, font, size, _RIGHT - _LEFT - indent):
        c.drawString(_LEFT + indent, y, ln)
        y -= leading or (size + 1.5)
    return y


def _quebra(c: rl_canvas.Canvas, y: float, precisa: float, client_name: str) -> float:
    """Se não couber `precisa` pt até o rodapé, abre página de continuação."""
    if y - precisa < _MIN_Y:
        _footer(c)
        c.showPage()
        return _header(c, client_name)
    return y


def _fmt(v: float) -> str:
    return format_brl(v, prefix=True)


def _bloco_valores(c: rl_canvas.Canvas, y: float, resultado: dict) -> float:
    """Caixas SEM NF / COM NF lado a lado + linha do à vista (5% calculado)."""
    largura = (_RIGHT - _LEFT - 10) / 2

    def _caixa(x: float, label: str, valor: float, accent) -> None:
        c.setFillColor(_BOX_BG)
        c.roundRect(x, y - 30, largura, 38, 6, fill=1, stroke=0)
        c.setFillColor(_LIGHT)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + 12, y - 4, label)
        c.setFillColor(accent)
        c.setFont("Helvetica-Bold", 15)
        c.drawRightString(x + largura - 12, y - 22, _fmt(valor))

    _caixa(_LEFT, "VALOR SEM NF", float(resultado.get("sem_nota") or 0), _PURPLE)
    _caixa(_LEFT + largura + 10, "VALOR COM NF", float(resultado.get("com_nota") or 0), _GOLD)
    y -= 44
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(_GRAY)
    c.drawString(
        _LEFT, y,
        "À vista (PIX, 5% de desconto): "
        f"{_fmt(float(resultado.get('a_vista_sem_nota') or 0))} sem NF · "
        f"{_fmt(float(resultado.get('a_vista_com_nota') or 0))} com NF",
    )
    return y - 14


def _draw_config_page(c: rl_canvas.Canvas, snapshot: dict, config: dict) -> None:
    """Uma página A4 completa para uma configuração (v2)."""
    client_name = snapshot.get("client_name") or ""
    resultado = config.get("resultado") or {}
    resp = config.get("responsabilidades") or {}
    tecnicos = resultado.get("tecnicos") or ["sonoplasta"]
    headcount = int(resultado.get("headcount") or 0)

    y = _header(c, client_name)

    # ── Musical + equipe ──────────────────────────────────────────────────
    c.setFillColor(_PURPLE)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(_LEFT, y, config.get("musical_name", "Musical"))
    y -= 15
    equipe = pdf_textos.descricao_equipe(
        int(config.get("num_personagens") or 0),
        int(config.get("num_producao") or 0),
        tecnicos,
    )
    if int(config.get("ensemble") or 0) > 0:
        equipe += f" + {config['ensemble']} ensemble"
    y = _paragrafo(c, y, equipe, size=9.5, color=_GRAY, font="Helvetica-Oblique")
    y -= 4

    # ── Dias (linhas zeradas não aparecem — FR-022) ──────────────────────
    c.setFont("Helvetica", 10)
    c.setFillColor(_GRAY)
    for dias, rotulo in ((config.get("d1"), "1 sessão"), (config.get("d2"), "2 sessões")):
        if int(dias or 0) > 0:
            c.drawString(_LEFT, y, f"Quantidade de dias com {rotulo}: {int(dias)}")
            y -= 14
    y -= 8

    # ── Valores ───────────────────────────────────────────────────────────
    y = _bloco_valores(c, y, resultado)
    transporte = resultado.get("transporte") or {}
    if transporte.get("modo") == "vans_fora_sp" and float(transporte.get("total") or 0) > 0:
        y = _paragrafo(
            c, y,
            "(valores já incluem logística/transporte fora de SP: "
            f"{_fmt(float(transporte['total']))} — 2 vans, {transporte.get('km_total', 0):g} km "
            f"ida e volta × {int(transporte.get('dias') or 1)} dia(s))",
            size=8, font="Helvetica-Oblique",
        )
    y -= 6

    # ── Contratação Manto embutida (quando houver) ────────────────────────
    contratacao = config.get("contratacao_manto")
    combinados = resultado.get("combinados") or {}
    if contratacao and combinados:
        y = _quebra(c, y, 70, client_name)
        y = _titulo_secao(c, y, "COM CONTRATAÇÃO MANTO (apresentação tradicional)")
        team = contratacao.get("team_lines") or []
        if team:
            y = _paragrafo(c, y, "Inclui: " + ", ".join(team) + ".", size=8.5, color=_GRAY)
        for duracao in sorted(combinados, key=lambda d: (len(d), d)):
            tot = combinados[duracao]
            c.setFont("Helvetica-Bold", 8.5)
            c.setFillColor(_PURPLE)
            c.drawString(
                _LEFT + 4, y,
                f"Total com {duracao} de apresentação Manto: "
                f"{_fmt(float(tot.get('sem_nota') or 0))} sem NF · "
                f"{_fmt(float(tot.get('com_nota') or 0))} com NF",
            )
            y -= 11
        y -= 6

    # ── Responsabilidades: o que levamos / mínimo exigido (FR-019) ───────
    y = _quebra(c, y, 120, client_name)
    y = _titulo_secao(c, y, "RESPONSABILIDADES")
    for chave in pdf_textos.RESPONSABILIDADES_ORDEM:
        textos = pdf_textos.RESPONSABILIDADES[chave]
        eh_manto = str(resp.get(chave) or "manto") != "contratante"
        rotulo = "por conta da Manto" if eh_manto else "por conta da contratante"
        y = _quebra(c, y, 34, client_name)
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(_GRAY)
        c.drawString(_LEFT, y, f"{textos['label']} — {rotulo}:")
        y -= 10
        corpo = textos["manto"] if eh_manto else f"Mínimo exigido: {textos['contratante']}"
        y = _paragrafo(c, y, corpo, indent=10, size=8.5)
        y -= 3

    # ── Avisos fixos (FR-021) ─────────────────────────────────────────────
    y = _quebra(c, y, 80, client_name)
    y = _titulo_secao(c, y, "INFORMAÇÕES IMPORTANTES")
    avisos = [
        pdf_textos.AVISO_PALCO,
        pdf_textos.AVISO_CAMARIM.format(cadeiras=headcount or "—"),
    ]
    # A cobertura do rider só faz sentido quando o som é NOSSO; com som da contratante, a
    # responsabilidade pela cobertura é dela (o texto do mínimo exigido já diz isso).
    if str(resp.get("som") or "manto") != "contratante":
        avisos.append(pdf_textos.AVISO_SOM_AREA)
    avisos.append(pdf_textos.AVISO_LOCAL_ABERTO)
    for aviso in avisos:
        y = _quebra(c, y, 22, client_name)
        y = _paragrafo(c, y, f"• {aviso}", size=8.5, color=_GRAY)
        y -= 1

    # ── Formas de pagamento ───────────────────────────────────────────────
    y = _quebra(c, y, 70, client_name)
    y = _titulo_secao(c, y, "FORMAS DE PAGAMENTO")
    avista_valores = (
        f"{_fmt(float(resultado.get('a_vista_sem_nota') or 0))} sem NF / "
        f"{_fmt(float(resultado.get('a_vista_com_nota') or 0))} com NF"
    )
    linhas_pagamento = [
        (pdf_textos.PAGAMENTO_AVISTA_TITULO,
         pdf_textos.PAGAMENTO_AVISTA_DESC.format(valores=avista_valores)),
        *pdf_textos.PAGAMENTO_LINHAS_FIXAS,
    ]
    for titulo, desc in linhas_pagamento:
        y = _quebra(c, y, 24, client_name)
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(_GRAY)
        c.drawString(_LEFT, y, titulo)
        c.setFont("Helvetica", 8.5)
        c.setFillColor(_LIGHT)
        for ln in _wrap(c, desc, "Helvetica", 8.5, _RIGHT - _LEFT - 125):
            c.drawString(_LEFT + 125, y, ln)
            y -= 10
        y -= 3

    # ── Observação do vendedor (FR-023 — pode transbordar p/ continuação) ─
    observacao = (snapshot.get("observacao") or "").strip()
    if observacao:
        y = _quebra(c, y, 40, client_name)
        y = _titulo_secao(c, y, "OBSERVAÇÕES")
        for linha in observacao.splitlines():
            if not linha.strip():
                y -= 5
                continue
            y = _quebra(c, y, 14, client_name)
            y = _paragrafo(c, y, linha.strip(), size=8.5, color=_GRAY)

    _footer(c)


def _gerar_v2(snapshot: dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.setAuthor("Manto Produções")
    c.setTitle("Orçamento EducaManto")
    configs = snapshot.get("configs") or [{}]
    for config in configs:
        _draw_config_page(c, snapshot, config)
        c.showPage()
    c.save()
    return buf.getvalue()


# ═══════════════════════ v1 — LEGADO (snapshots pré-feature 235) ════════════════════════
# Reproduz o PDF antigo por pacote/nível para o histórico congelado. NÃO usar em orçamentos
# novos — os textos por nível abaixo existem só para manter o re-download idêntico (FR-027).

_V1_CONTACT_PHONE = pdf_textos.CONTACT_PHONE
_V1_CONTACT_EMAIL = pdf_textos.CONTACT_EMAIL

SHORT_DESC = {
    "master": (
        "A Manto Produções se responsabiliza pela sonorização, iluminação completa e "
        "alimentação no dia do evento."
    ),
    "intermediario": (
        "A Manto Produções se responsabiliza pela sonorização, iluminação básica e "
        "alimentação no dia do evento."
    ),
    "economica": (
        "A Manto Produções se responsabiliza apenas pela sonorização básica. Iluminação e "
        "Alimentação no dia do evento por conta da parte contratante."
    ),
}

LONG_DESC = {
    "master": [
        ("Iluminação Cênica Completa", "Moving Head, Moving Bee, Parleds, Ribaltas, Máquinas de Fumaça, Máquinas de Bolha de Sabão, Mesa DMX, Estrutura Box Truss"),
        ("Sonorização Teatral", "Caixas de Som, Microfones Headset, Microfones Headset e/ou Bastão e Mesa Digital"),
        ("Cenografia", "3 Backdrops cenográficos, 2 Árvores Cenográficas, 1 Bateria Cenográfica e Elementos de Selva"),
    ],
    "intermediario": [
        ("Iluminação Cênica Básica", "Moving Bee, Parleds, Máquinas de Bolha de Sabão, Mesa DMX, Estrutura Box Truss"),
        ("Sonorização Simplificada", "Caixas de Som, Microfones Headset e/ou Bastão e Mesa Digital"),
        ("Cenografia", "3 Backdrops cenográficos, 2 Árvores Cenográficas, 1 Bateria Cenográfica e Elementos de Selva"),
    ],
    "economica": [
        ("Sonorização Simplificada", "Caixas de Som, Microfones Headset e/ou Bastão e Mesa Digital"),
        ("Cenografia", "1 Backdrop cenográfico, Bateria Cenográfica e Elementos de Selva"),
    ],
}

_PAYMENT_LINES = [
    ("À Vista (PIX):", "desconto especial de 5% aplicado."),
    ("Reserva Programada (PIX):", "50% no ato do contrato + 50% até 2 dias antes do espetáculo."),
    ("Cartão de Crédito:", "parcelamento disponível (taxas da operadora repassadas ao cliente)."),
]


def _norm(name: str) -> str:
    """Normaliza o nome do pacote p/ casar no mapa (sem acentos, minúsculo)."""
    n = unicodedata.normalize("NFKD", (name or "").strip().lower())
    return "".join(ch for ch in n if not unicodedata.combining(ch))


def _tipo_for(name: str) -> str:
    """Detecta o tipo do plano pelo nome do pacote (substring). '' se não reconhecido."""
    n = _norm(name)
    if "master" in n:
        return "master"
    if "intermedi" in n:
        return "intermediario"
    if "economic" in n or "basic" in n:
        return "economica"
    return ""


def explanation_for(name: str) -> str:
    """(v1) Descrição CURTA do tipo; vazio se tipo não reconhecido."""
    return SHORT_DESC.get(_tipo_for(name), "")


def detalhes_for(name: str) -> list[tuple[str, str]]:
    """(v1) Descrição LONGA do plano; [] se tipo não reconhecido."""
    return LONG_DESC.get(_tipo_for(name), [])


def _draw_page_v1(c: rl_canvas.Canvas, pk: dict, d1: int, d2: int, transporte: dict, client_name: str) -> None:
    # ── Cabeçalho: faixa roxa com contato ──────────────────────────────────
    c.setFillColor(_PURPLE)
    c.rect(0, _H - 70, _W, 70, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(_LEFT, _H - 38, "MANTO PRODUÇÕES")
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor("#d8d2f0"))
    c.drawRightString(_RIGHT, _H - 30, _V1_CONTACT_PHONE)
    c.drawRightString(_RIGHT, _H - 44, _V1_CONTACT_EMAIL)

    y = _H - 110

    # ── Título ──────────────────────────────────────────────────────────────
    c.setFillColor(_GOLD)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(_LEFT, y, "ORÇAMENTO")
    if client_name:
        c.setFont("Helvetica", 10)
        c.setFillColor(_LIGHT)
        c.drawRightString(_RIGHT, y + 4, f"Cliente: {client_name}")
    y -= 14
    c.setStrokeColor(_GOLD)
    c.setLineWidth(1.5)
    c.line(_LEFT, y, _RIGHT, y)
    y -= 34

    # ── Nome do pacote ────────────────────────────────────────────────────
    c.setFillColor(_PURPLE)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(_LEFT, y, pk.get("name", "Pacote"))
    y -= 22

    # ── Breve explicação (subtítulo) ──────────────────────────────────────
    explic = explanation_for(pk.get("name", ""))
    if explic:
        c.setFont("Helvetica-Oblique", 10.5)
        c.setFillColor(_GRAY)
        for ln in _wrap(c, explic, "Helvetica-Oblique", 10.5, _RIGHT - _LEFT):
            c.drawString(_LEFT, y, ln)
            y -= 15
    y -= 12

    # ── Dias ──────────────────────────────────────────────────────────────
    c.setFont("Helvetica", 11)
    c.setFillColor(_GRAY)
    c.drawString(_LEFT, y, f"Quantidade de dias com 1 sessão: {int(d1)}")
    y -= 18
    c.drawString(_LEFT, y, f"Quantidade de dias com 2 sessões: {int(d2)}")
    y -= 34

    # ── Valores ───────────────────────────────────────────────────────────
    sem = float(pk.get("sem_nota") or 0)
    com = float(pk.get("com_nota") or 0)

    def _value_box(yb: float, label: str, value: float, accent) -> None:
        c.setFillColor(_BOX_BG)
        c.roundRect(_LEFT, yb - 30, _RIGHT - _LEFT, 40, 6, fill=1, stroke=0)
        c.setFillColor(_LIGHT)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(_LEFT + 14, yb - 4, label)
        c.setFillColor(accent)
        c.setFont("Helvetica-Bold", 18)
        c.drawRightString(_RIGHT - 14, yb - 8, format_brl(value, prefix=True))

    _value_box(y, "VALOR SEM NF", sem, _PURPLE)
    y -= 50
    _value_box(y, "VALOR COM NF", com, _GOLD)
    y -= 56

    _t_total = float((transporte or {}).get("total") or 0)
    if _t_total > 0:
        c.setFont("Helvetica-Oblique", 8.5)
        c.setFillColor(_LIGHT)
        c.drawString(_LEFT, y, f"(valores já incluem logística/transporte: {format_brl(_t_total, prefix=True)})")
        y -= 22

    # ── Formas de pagamento ───────────────────────────────────────────────
    c.setFillColor(_PURPLE)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(_LEFT, y, "FORMAS DE PAGAMENTO")
    y -= 6
    c.setStrokeColor(_GOLD)
    c.setLineWidth(0.5)
    c.line(_LEFT, y, _RIGHT, y)
    y -= 18
    for titulo, desc in _PAYMENT_LINES:
        c.setFont("Helvetica-Bold", 9.5)
        c.setFillColor(_GRAY)
        c.drawString(_LEFT, y, titulo)
        c.setFont("Helvetica", 9.5)
        c.setFillColor(_LIGHT)
        for ln in _wrap(c, desc, "Helvetica", 9.5, _RIGHT - _LEFT - 130):
            c.drawString(_LEFT + 130, y, ln)
            y -= 13
        y -= 5

    # ── Descrição longa do plano — após as formas de pagamento (080) ──────
    detalhes = detalhes_for(pk.get("name", ""))
    if detalhes:
        y -= 8
        c.setFillColor(_PURPLE)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(_LEFT, y, "O QUE ESTÁ INCLUSO")
        y -= 6
        c.setStrokeColor(_GOLD)
        c.setLineWidth(0.5)
        c.line(_LEFT, y, _RIGHT, y)
        y -= 14
        for label, txt in detalhes:
            c.setFont("Helvetica-Bold", 8.5)
            c.setFillColor(_GRAY)
            c.drawString(_LEFT, y, f"{label}:")
            y -= 11
            c.setFont("Helvetica", 8.5)
            c.setFillColor(_LIGHT)
            for ln in _wrap(c, txt, "Helvetica", 8.5, _RIGHT - _LEFT - 12):
                c.drawString(_LEFT + 12, y, ln)
                y -= 10
            y -= 4

    # ── Rodapé ────────────────────────────────────────────────────────────
    c.setFillColor(_LIGHT)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(_W / 2, 32, "Manto Produções · EducaManto")


def _gerar_v1(snapshot: dict[str, Any]) -> bytes:
    packages = snapshot.get("packages") or []
    d1 = snapshot.get("d1", 0) or 0
    d2 = snapshot.get("d2", 0) or 0
    transporte = snapshot.get("transporte") or {}
    client_name = snapshot.get("client_name") or ""

    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.setAuthor("Manto Produções")
    c.setTitle("Orçamento EducaManto")

    if not packages:  # segurança: nunca gerar PDF vazio sem páginas
        packages = [{"name": "—", "sem_nota": 0, "com_nota": 0}]

    for pk in packages:
        _draw_page_v1(c, pk, d1, d2, transporte, client_name)
        c.showPage()
    c.save()
    return buf.getvalue()


# ═══════════════════════════════════ Despacho ═══════════════════════════════════════════


def gerar_orcamento_pdf(snapshot: dict[str, Any]) -> bytes:
    """Gera o PDF a partir do snapshot congelado — v2 (configs) ou v1 (pacotes, legado).

    Args:
        snapshot: Snapshot do orçamento. ``{"version": 2, "configs": [...]}`` usa o layout
            por responsabilidades; sem ``version``, reproduz o PDF antigo por pacote.

    Returns:
        Bytes do PDF pronto para download.
    """
    if snapshot.get("version") == 2:
        return _gerar_v2(snapshot)
    return _gerar_v1(snapshot)
