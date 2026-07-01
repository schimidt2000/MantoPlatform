"""Geração de PDF de orçamento sobrepondo texto ao Orcamento_blank.pdf."""
from __future__ import annotations

import io
import os
from typing import Any

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as rl_canvas

from app.money import format_brl

_BLANK_PDF_PATH = os.path.join(os.path.dirname(__file__), "Orcamento_blank.pdf")

# Cores da identidade visual Manto
_PURPLE = HexColor("#2d1f6e")
_GOLD   = HexColor("#b8975a")
_GRAY   = HexColor("#555555")
_LIGHT  = HexColor("#888888")

# A4 em pontos: 595 x 842
_W, _H = A4  # width=595, height=842

# Margens / posicionamento do conteúdo
_LEFT  = 52
_RIGHT = _W - 52
_TOP_Y = 572   # y do início do conteúdo (embaixo do logo)

# Mapeamento de fontes (reportlab embeds Helvetica por padrão)
_FONT_BOLD   = "Helvetica-Bold"
_FONT_NORMAL = "Helvetica"


def _fmt_brl(value: float) -> str:
    """Formata moeda BR com prefixo R$ (fonte única)."""
    return format_brl(value, prefix=True)


def _section_title(c: rl_canvas.Canvas, y: float, text: str) -> float:
    """Desenha um título de seção e retorna o y após a linha divisória."""
    c.setFont(_FONT_BOLD, 8)
    c.setFillColor(_PURPLE)
    c.setStrokeColor(_GOLD)
    c.drawString(_LEFT, y, text.upper())
    y -= 5
    c.setLineWidth(0.5)
    c.line(_LEFT, y, _RIGHT, y)
    return y - 10


def _field_row(c: rl_canvas.Canvas, y: float, label: str, value: str, x_split: float = 120) -> float:
    """Desenha uma linha label: valor e retorna o y seguinte."""
    c.setFont(_FONT_BOLD, 8.5)
    c.setFillColor(_LIGHT)
    c.drawString(_LEFT, y, label)
    c.setFont(_FONT_NORMAL, 8.5)
    c.setFillColor(_GRAY)
    c.drawString(_LEFT + x_split, y, value)
    return y - 13


def _price_row(c: rl_canvas.Canvas, y: float, label: str, value: str, highlight: bool = False) -> float:
    """Desenha uma linha de preço na tabela de investimento."""
    row_h = 18
    if highlight:
        c.setFillColor(HexColor("#f0eff6"))
        c.roundRect(_LEFT, y - 3, _RIGHT - _LEFT, row_h, 3, fill=1, stroke=0)
    c.setFont(_FONT_NORMAL if not highlight else _FONT_BOLD, 9)
    c.setFillColor(_PURPLE if highlight else _GRAY)
    c.drawString(_LEFT + 6, y + 4, label)
    c.setFont(_FONT_BOLD, 9)
    c.setFillColor(_GOLD)
    c.drawRightString(_RIGHT - 6, y + 4, value)
    return y - row_h


def gerar_orcamento_pdf(quote: dict[str, Any]) -> bytes:
    """
    Gera bytes de um PDF de orçamento sobrepondo conteúdo ao Orcamento_blank.pdf.

    Args:
        quote: dicionário com os dados do orçamento (vindos da session).

    Returns:
        Bytes do PDF final pronto para download.
    """
    # ── 1. Gera a camada de texto com reportlab ────────────────────────────
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    c.setAuthor("Manto Produções")
    c.setTitle("Orçamento Manto Produções")

    y = _TOP_Y

    # ── Dados do evento ────────────────────────────────────────────────────
    y = _section_title(c, y, "Dados do Evento")

    client_name    = quote.get("client_name", "")
    event_date     = quote.get("fmt_date", "")
    event_time     = quote.get("fmt_time", "")
    event_location = quote.get("event_location", "")

    if client_name:
        y = _field_row(c, y, "Cliente:", client_name)
    if event_date:
        y = _field_row(c, y, "Data:", event_date)
    if event_time:
        y = _field_row(c, y, "Horário:", event_time)
    if event_location:
        y = _field_row(c, y, "Local:", event_location)

    y -= 6

    # ── Equipe ─────────────────────────────────────────────────────────────
    team_lines: list[str] = quote.get("team_lines", [])
    if team_lines:
        y = _section_title(c, y, "Equipe")
        c.setFont(_FONT_NORMAL, 8.5)
        c.setFillColor(_GRAY)
        for member in team_lines:
            c.drawString(_LEFT + 8, y, f"• {member}")
            y -= 13
        y -= 4

    # ── Investimento ───────────────────────────────────────────────────────
    y = _section_title(c, y, "Investimento")

    nota_fiscal   = quote.get("nota_fiscal", False)
    modo_duracao  = quote.get("modo_duracao", "horas")
    total_custom  = quote.get("total_custom")
    duracao_custom = quote.get("duracao_custom", 0)

    def _dur_label(idx: int) -> str:
        if modo_duracao == "entradas":
            labels = ["1 entrada de 30 min", "2 entradas de 30 min (2h)",
                      "3 entradas de 30 min (3h)", "4 entradas de 30 min (4h)"]
        else:
            labels = ["1 hora", "2 horas", "3 horas", "4 horas"]
        return labels[idx]

    totals = [
        float(quote.get("total_1h", 0) or 0),
        float(quote.get("total_2h", 0) or 0),
        float(quote.get("total_3h", 0) or 0),
        float(quote.get("total_4h", 0) or 0),
    ]
    # Durações que o vendedor escolheu incluir. 1h/2h/4h default True p/ orçamentos antigos;
    # 3h default False (orçamentos antigos não têm 3h e não devem exibir uma linha zerada).
    show = [
        quote.get("show_1h", True),
        quote.get("show_2h", True),
        quote.get("show_3h", False),
        quote.get("show_4h", True),
    ]

    for i, total in enumerate(totals):
        if not show[i]:
            continue
        y = _price_row(c, y, _dur_label(i), _fmt_brl(total), highlight=(i == 3))
        y -= 2

    if total_custom:
        if modo_duracao == "entradas":
            custom_label = f"{duracao_custom * 2} entradas de 30 min ({duracao_custom}h)"
        else:
            custom_label = f"{duracao_custom} horas"
        y -= 2
        y = _price_row(c, y, custom_label, _fmt_brl(float(total_custom)), highlight=True)

    if nota_fiscal:
        c.setFont(_FONT_NORMAL, 7.5)
        c.setFillColor(_LIGHT)
        c.drawString(_LEFT, y, "* Valores com Nota Fiscal inclusa")
        y -= 12

    y -= 8

    # ── Formas de pagamento ────────────────────────────────────────────────
    y = _section_title(c, y, "Formas de Pagamento")

    _pix_vista = [
        f"1h {_fmt_brl(round(totals[0]*0.95,2))}" if show[0] else None,
        f"2h {_fmt_brl(round(totals[1]*0.95,2))}" if show[1] else None,
        f"3h {_fmt_brl(round(totals[2]*0.95,2))}" if show[2] else None,
        f"4h {_fmt_brl(round(totals[3]*0.95,2))}" if show[3] else None,
    ]
    pix_lines = [
        ("PIX à vista (5% desc.):", " | ".join(p for p in _pix_vista if p)),
        ("Reserva programada:", "50% no ato + 50% até 2 dias antes"),
        ("Cartão de crédito:", "Parcelamento disponível (taxas repassadas)"),
    ]

    for label, value in pix_lines:
        c.setFont(_FONT_BOLD, 8)
        c.setFillColor(_LIGHT)
        c.drawString(_LEFT, y, label)
        c.setFont(_FONT_NORMAL, 8)
        c.setFillColor(_GRAY)
        # value pode ser longo — quebra se necessário
        c.drawString(_LEFT + 130, y, value)
        y -= 13

    y -= 8

    # ── Rodapé de validade ────────────────────────────────────────────────
    c.setFont(_FONT_NORMAL, 7.5)
    c.setFillColor(_LIGHT)
    c.drawString(_LEFT, y, "Esta proposta tem validade de 7 dias a contar da data de envio.")

    c.save()

    # ── 2. Faz o merge: texto sobre o background ───────────────────────────
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        from PyPDF2 import PdfReader, PdfWriter  # fallback

    blank_path = os.path.abspath(_BLANK_PDF_PATH)
    background = PdfReader(blank_path)
    text_layer = PdfReader(io.BytesIO(buf.getvalue()))

    writer = PdfWriter()
    bg_page = background.pages[0]
    bg_page.merge_page(text_layer.pages[0])
    writer.add_page(bg_page)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
