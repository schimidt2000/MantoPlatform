"""Normalização de chave PIX para comparação (feature 221).

As chaves no banco são texto livre (6+ colunas diferentes); a extraída do comprovante vem do
OCR. Antes de comparar, ambas passam por aqui: CPF/CNPJ viram só dígitos, telefone vira
dígitos com DDI 55, e-mail vira minúsculas, EVP (aleatória) vira minúsculas sem hífens
supérfluos. Comparar chave normalizada com chave normalizada.
"""

from __future__ import annotations

import re
import unicodedata

_UUID_RE = re.compile(r"^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$")


def normalize_pix(raw: str | None) -> tuple[str, str] | None:
    """Normaliza uma chave PIX.

    Args:
        raw: A chave como está no banco ou como saiu do OCR (pode ser None/vazia).

    Returns:
        Tupla ``(tipo, valor_normalizado)`` — tipo em {cpf, cnpj, telefone, email, evp,
        desconhecido} — ou None se a entrada é vazia.
    """
    if not raw:
        return None
    key = raw.strip()
    if not key:
        return None

    lowered = key.lower()
    if "@" in lowered and " " not in lowered:
        return ("email", lowered)

    compact = lowered.replace("-", "")
    if _UUID_RE.match(lowered) or _UUID_RE.match(compact):
        return ("evp", lowered.replace("-", ""))

    digits = re.sub(r"\D", "", key)
    if len(digits) == 11 and not key.strip().startswith("+"):
        # 11 dígitos é ambíguo (CPF ou celular sem DDI). CPF é o caso comum de cadastro.
        return ("cpf", digits)
    if len(digits) == 14:
        return ("cnpj", digits)
    if 12 <= len(digits) <= 13 and digits.startswith("55"):
        return ("telefone", digits[-11:])
    if len(digits) in (10, 11):
        return ("telefone", digits[-11:])

    return ("desconhecido", lowered)


_MASK_CHARS = ("*", "•", "●", "x", "X")


def _masked_digits_match(masked: str, full_key: str | None) -> bool | None:
    """Compara uma chave mascarada de comprovante ("***.276.510-**") com a cadastrada.

    Bancos mascaram o CPF do recebedor por LGPD; compara-se a sequência de dígitos
    VISÍVEL como substring contígua dos dígitos da chave cadastrada.

    Returns:
        True se os dígitos visíveis aparecem na chave cadastrada; False se não aparecem;
        None se não há dígitos suficientes para um veredito (menos de 4).
    """
    visible = re.sub(r"\D", "", masked)
    if len(visible) < 4:
        return None
    expected = re.sub(r"\D", "", full_key or "")
    if not expected:
        return None
    return visible in expected


def same_pix(a: str | None, b: str | None) -> bool | None:
    """Compara duas chaves PIX após normalização.

    Returns:
        True/False quando ambas existem; None quando falta uma das duas (sem veredito).
    """
    if not a or not b:
        return None
    # Chave mascarada no comprovante (padrão dos bancos): compara só os dígitos visíveis.
    a_masked = any(ch in a for ch in _MASK_CHARS)
    b_masked = any(ch in b for ch in _MASK_CHARS)
    if a_masked or b_masked:
        masked, full = (a, b) if a_masked else (b, a)
        return _masked_digits_match(masked, full)
    na, nb = normalize_pix(a), normalize_pix(b)
    if na is None or nb is None:
        return None
    # CPF e telefone de 11 dígitos se confundem; compara só o valor nesses casos.
    if {na[0], nb[0]} <= {"cpf", "telefone"}:
        return na[1][-11:] == nb[1][-11:]
    return na == nb


def normalize_name(raw: str | None) -> str:
    """Nome para comparação frouxa: maiúsculas, sem acentos, espaços colapsados."""
    if not raw:
        return ""
    text = unicodedata.normalize("NFKD", raw)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip().upper()


# Tokens sem valor identificador: sufixos societários e conectivos. "Alfa Producoes LTDA ME"
# × "Bravo Transportes LTDA ME" tem 2 tokens em comum e NÃO é a mesma empresa.
_STOP_TOKENS = frozenset(
    {"LTDA", "ME", "SA", "S.A", "S/A", "EIRELI", "EPP", "MEI", "CIA",
     "DE", "DA", "DO", "DAS", "DOS", "E"}
)


def name_matches(expected: str | None, extracted: str | None) -> bool | None:
    """Compara nomes de beneficiário de forma tolerante (subconjunto de tokens).

    O comprovante costuma trazer o nome completo ou levemente truncado; considera match
    quando os tokens SIGNIFICATIVOS (fora sufixos societários/conectivos) de um lado estão
    contidos no outro, ou há pelo menos 2 em comum.

    Returns:
        True/False quando ambos existem; None quando falta um dos dois ou não sobra token
        significativo para comparar.
    """
    ne, nx = normalize_name(expected), normalize_name(extracted)
    if not ne or not nx:
        return None
    te = set(ne.split()) - _STOP_TOKENS
    tx = set(nx.split()) - _STOP_TOKENS
    if not te or not tx:
        return None
    common = te & tx
    return te <= tx or tx <= te or len(common) >= 2
