"""CPF e CNPJ: validação pelos dígitos verificadores (feature 342).

Módulo folha, sem dependência do app: o formulário público (`app/formularios`) e a venda
(`app/calendar/pedido_de_nota_ops.py`) usam a mesma régua, e `formularios_ops` não pode importar
`calendar`.

Só o formato numérico. O CNPJ alfanumérico (IN RFB 2.229, novas inscrições a partir de julho/2026)
não cabe em `calendar_events.nota_tomador_doc`, que guarda só dígitos — dívida no `docs/05`.
"""

from __future__ import annotations

import re

CPF_DIGITOS = 11
CNPJ_DIGITOS = 14

_PESOS_CNPJ_1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_PESOS_CNPJ_2 = (6, *_PESOS_CNPJ_1)


def so_digitos(valor: str | None) -> str:
    """Tira tudo que não é dígito."""
    return re.sub(r"\D", "", valor or "")


def _repetido(digitos: str) -> bool:
    """ "000.000.000-00" e parecidos passam na conta dos verificadores, mas não existem."""
    return len(set(digitos)) == 1


def cpf_valido(valor: str | None) -> bool:
    """CPF com 11 dígitos e os dois verificadores corretos."""
    d = so_digitos(valor)
    if len(d) != CPF_DIGITOS or _repetido(d):
        return False
    for posicao in (9, 10):
        soma = sum(int(d[i]) * (posicao + 1 - i) for i in range(posicao))
        if (soma * 10) % 11 % 10 != int(d[posicao]):
            return False
    return True


def cnpj_valido(valor: str | None) -> bool:
    """CNPJ com 14 dígitos e os dois verificadores corretos."""
    d = so_digitos(valor)
    if len(d) != CNPJ_DIGITOS or _repetido(d):
        return False
    for pesos, posicao in ((_PESOS_CNPJ_1, 12), (_PESOS_CNPJ_2, 13)):
        resto = sum(int(d[i]) * peso for i, peso in enumerate(pesos)) % 11
        if (0 if resto < 2 else 11 - resto) != int(d[posicao]):
            return False
    return True


def doc_valido(valor: str | None) -> bool:
    """CPF ou CNPJ válido, pelo tamanho."""
    d = so_digitos(valor)
    if len(d) == CPF_DIGITOS:
        return cpf_valido(d)
    if len(d) == CNPJ_DIGITOS:
        return cnpj_valido(d)
    return False


def eh_cnpj(valor: str | None) -> bool:
    """O documento tem o tamanho de um CNPJ (não confere os verificadores)."""
    return len(so_digitos(valor)) == CNPJ_DIGITOS
