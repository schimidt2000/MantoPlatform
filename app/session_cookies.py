"""Higiene do cookie de sessão (feature 295).

Módulo folha de propósito: não importa nada de `app`, para poder ser usado tanto pelo
`after_request` em `app/__init__.py` quanto pelas rotas de login sem criar ciclo.
"""

from __future__ import annotations

from flask import g

#: Marca, no `g` da requisição, que a resposta deve recolher cookies de sessão de domínios
#: obsoletos mesmo sem os sinais que o `after_request` usa por conta própria.
FLAG_RECOLHER = "_recolher_cookie_orfao"


def marca_para_recolher_cookie_orfao() -> None:
    """Pede o recolhimento do cookie de sessão órfão na resposta desta requisição.

    Chamada por TODA rota que abre sessão. No login o servidor está reescrevendo a sessão, então
    qualquer cookie de mesmo nome em outro domínio é obsoleto por definição — e é o único momento
    em que dá para afirmar isso com um cookie só no pote. Sem esta marca o recolhimento ainda
    acontece, mas só na requisição seguinte: a pessoa loga, a primeira consulta é lida pelo órfão,
    toma 401 e volta para a tela de login. Cura, cobrando um login extra de quem já estava perdido.

    Ver `_recolhe_cookie_de_sessao_orfao` em `app/__init__.py` para o porquê do órfão existir.
    """
    setattr(g, FLAG_RECOLHER, True)
