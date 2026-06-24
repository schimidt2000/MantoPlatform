"""Geração do PDF de orçamento do EducaManto (feature 077).

Uma página por pacote, reproduzindo a estrutura do modelo de referência
(`Orccamentos_Educamanto.pdf`): cabeçalho com contato da Manto, título "ORÇAMENTO", nome do pacote,
breve explicação, dias com 1/2 sessões, VALOR SEM NF / COM NF e formas de pagamento.

O PDF é reconstruído com reportlab (o arquivo de referência é um exemplo preenchido), mantendo a
identidade visual da Manto (mesmas cores do `orcamento/pdf.py`).
"""
from __future__ import annotations

import io
import unicodedata
from typing import Any

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as rl_canvas

from app.money import format_brl

# Identidade visual Manto (mesmas cores do orçamento)
_PURPLE = HexColor("#2d1f6e")
_GOLD = HexColor("#b8975a")
_GRAY = HexColor("#555555")
_LIGHT = HexColor("#888888")

_W, _H = A4  # 595 x 842
_LEFT = 56
_RIGHT = _W - 56

_CONTACT_PHONE = "+55 (11) 97057-0577"
_CONTACT_EMAIL = "educamanto@mantoproducoes.com.br"

# Descrição CURTA do tipo (abaixo do título). Tipo detectado por substring no nome do pacote
# (ex.: "Uma Aventura Animal - Master" -> master). Feature 077/080.
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

# Descrição LONGA do plano (após as formas de pagamento) — conteúdo de planos.md. Feature 080.
# Obs.: o resumo "Geral" NÃO entra aqui — já aparece como descrição curta abaixo do título (082).
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
    """Descrição CURTA do tipo (abaixo do título); vazio se tipo não reconhecido."""
    return SHORT_DESC.get(_tipo_for(name), "")


def detalhes_for(name: str) -> list[tuple[str, str]]:
    """Descrição LONGA do plano (após as formas de pagamento); [] se tipo não reconhecido."""
    return LONG_DESC.get(_tipo_for(name), [])


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


def _draw_page(c: rl_canvas.Canvas, pk: dict, d1: int, d2: int, transporte: dict, client_name: str) -> None:
    # ── Cabeçalho: faixa roxa com contato ──────────────────────────────────
    c.setFillColor(_PURPLE)
    c.rect(0, _H - 70, _W, 70, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(_LEFT, _H - 38, "MANTO PRODUÇÕES")
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor("#d8d2f0"))
    c.drawRightString(_RIGHT, _H - 30, _CONTACT_PHONE)
    c.drawRightString(_RIGHT, _H - 44, _CONTACT_EMAIL)

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
        c.setFillColor(HexColor("#f4f2fb"))
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

    # ── Descrição longa do plano (planos.md) — após as formas de pagamento (080) ──
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


def gerar_orcamento_pdf(snapshot: dict[str, Any]) -> bytes:
    """Gera o PDF (uma página por pacote) a partir do snapshot do orçamento.

    Args:
        snapshot: dict com ``d1``, ``d2``, ``ensemble``, ``transporte`` e ``packages``
            (lista de ``{name, sem_nota, com_nota}``), além de ``client_name`` opcional.

    Returns:
        Bytes do PDF pronto para download.
    """
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
        _draw_page(c, pk, d1, d2, transporte, client_name)
        c.showPage()
    c.save()
    return buf.getvalue()
