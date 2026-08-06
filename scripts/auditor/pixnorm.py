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


def same_pix(a: str | None, b: str | None) -> bool | None:
    """Compara duas chaves PIX após normalização.

    Returns:
        True/False quando ambas existem; None quando falta uma das duas (sem veredito).
    """
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


def name_matches(expected: str | None, extracted: str | None) -> bool | None:
    """Compara nomes de beneficiário de forma tolerante (subconjunto de tokens).

    O comprovante costuma trazer o nome completo ou levemente truncado; considera match
    quando os tokens de um lado estão contidos no outro (mínimo 2 tokens em comum).

    Returns:
        True/False quando ambos existem; None quando falta um dos dois.
    """
    ne, nx = normalize_name(expected), normalize_name(extracted)
    if not ne or not nx:
        return None
    te, tx = set(ne.split()), set(nx.split())
    common = te & tx
    return te <= tx or tx <= te or len(common) >= 2
