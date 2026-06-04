"""Fonte única de formatação e parsing de valores monetários (padrão brasileiro).

Padrão brasileiro: ponto como separador de milhar, vírgula como separador
decimal, duas casas. Ex.: ``1500.5`` → ``"1.500,50"``.

Este módulo é puro (sem dependências de Flask/DB) para poder ser importado em
qualquer camada, inclusive no app factory, sem risco de import circular.

Use:
    - ``format_brl`` para exibir (filtro Jinja ``brl`` e templates/PDFs).
    - ``parse_brl`` / ``parse_brl_int`` para ler valores vindos de formulários,
      independentemente de virem mascarados ("1.500,50"), crus ("1500") ou no
      padrão americano ("1,500.50").
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

_CENTS = Decimal("0.01")


def format_brl(value, prefix: bool = False) -> str:
    """Formata um número no padrão brasileiro de moeda.

    Args:
        value: Número (int/float/Decimal/str numérica) ou ``None``.
        prefix: Se ``True``, prefixa com ``"R$ "``.

    Returns:
        Texto formatado (ex.: ``"1.500,50"`` ou ``"R$ 1.500,50"``). Para
        ``None`` retorna string vazia (ou ``"R$ "`` se ``prefix``).

    Examples:
        >>> format_brl(1500.5)
        '1.500,50'
        >>> format_brl(-50, prefix=True)
        'R$ -50,00'
    """
    if value is None or value == "":
        return "R$ " if prefix else ""
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return "R$ " if prefix else ""
    # f"{:,.2f}" usa vírgula no milhar e ponto no decimal (americano);
    # trocamos para o padrão brasileiro via marcador temporário.
    formatted = f"{number:,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"R$ {formatted}" if prefix else formatted


def parse_brl(text) -> Decimal | None:
    """Converte texto de valor monetário em ``Decimal`` (duas casas).

    Aceita valor mascarado em BR (``"R$ 1.500,50"``, ``"1.500,50"``), valor
    cru (``"1500"``, ``"1500.50"``) e o padrão americano (``"1,500.50"``).

    Args:
        text: Texto vindo do formulário (ou número já tipado).

    Returns:
        ``Decimal`` quantizado em duas casas, ou ``None`` se vazio/inválido.

    Examples:
        >>> parse_brl("R$ 1.500,50")
        Decimal('1500.50')
        >>> parse_brl("1,500.50")
        Decimal('1500.50')
        >>> parse_brl("")  # vazio
    """
    if text is None:
        return None
    raw = str(text).strip()
    if not raw:
        return None
    raw = raw.replace("R$", "").replace(" ", "")
    if not raw:
        return None

    has_comma = "," in raw
    has_dot = "." in raw
    if has_comma and has_dot:
        # O separador decimal é o que aparece por último.
        if raw.rfind(",") > raw.rfind("."):
            # BR: ponto = milhar, vírgula = decimal.
            cleaned = raw.replace(".", "").replace(",", ".")
        else:
            # Americano: vírgula = milhar, ponto = decimal.
            cleaned = raw.replace(",", "")
    elif has_comma:
        # Só vírgula → decimal brasileiro.
        cleaned = raw.replace(",", ".")
    else:
        # Só ponto (ou nenhum separador) → já está num formato parseável.
        cleaned = raw

    try:
        return Decimal(cleaned).quantize(_CENTS)
    except (InvalidOperation, ValueError):
        return None


def parse_brl_int(text) -> int | None:
    """Converte texto de valor monetário em ``int`` (arredondado).

    Para campos cujo valor é guardado como inteiro (ex.: contratos,
    comprovantes de pagamento). Reaproveita :func:`parse_brl`.

    Args:
        text: Texto vindo do formulário (ou número já tipado).

    Returns:
        Inteiro arredondado, ou ``None`` se vazio/inválido.
    """
    value = parse_brl(text)
    if value is None:
        return None
    return int(value.to_integral_value(rounding="ROUND_HALF_UP"))
