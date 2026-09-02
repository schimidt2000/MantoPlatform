"""Leitura da caixa de notificações do usuário (feature 272).

RBAC: só `@api_login_required`. **Nenhum gate por papel** — o RBAC aconteceu na emissão (quem foi
endereçado, `notificacoes_ops.DESTINATARIOS_POR_KIND`); na leitura o escopo é sempre
`Notification.user_id == current_user.id`, no servidor. REVENDEDOR_EDUCAMANTO recebe 200 com lista
vazia, não 403. Impersonação ("Ver como") **não** se aplica: a caixa é do usuário real — não existe
caixa do papel, existe caixa da pessoa.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required
from app.notificacoes import notificacoes_ops


@api_bp.route("/notificacoes/nao-lidas")
@api_login_required
def api_notificacoes_nao_lidas() -> Any:
    """`{"unread_count": n}` — o endpoint do polling (60 s por aba aberta).

    Um COUNT no índice parcial, zero join, zero objeto ORM. Existe separado da lista porque tem de
    ser a consulta mais barata do sistema.
    """
    return jsonify({"unread_count": notificacoes_ops.contar_nao_lidas(current_user.id)})


@api_bp.route("/notificacoes")
@api_login_required
def api_notificacoes_listar() -> Any:
    """Página da caixa por keyset.

    Query: `antes_de=<id>` (cursor), `limite` (1..100, padrão 30), `somente_nao_lidas=1`.
    Resposta: `items`, `next_before` (id do último item quando a página veio cheia; `null` quando
    acabou) e `unread_count`.
    """
    antes_de = request.args.get("antes_de", type=int)
    limite = request.args.get("limite", default=notificacoes_ops.LIMITE_PADRAO, type=int)
    somente = request.args.get("somente_nao_lidas", "") in ("1", "true")
    limite_efetivo = max(1, min(limite or notificacoes_ops.LIMITE_PADRAO, notificacoes_ops.LIMITE_MAXIMO))
    itens = notificacoes_ops.listar(
        current_user.id, antes_de=antes_de, limite=limite_efetivo, somente_nao_lidas=somente
    )
    return jsonify({
        "items": [notificacoes_ops.serializar(n) for n in itens],
        "next_before": itens[-1].id if len(itens) == limite_efetivo else None,
        "unread_count": notificacoes_ops.contar_nao_lidas(current_user.id),
    })
