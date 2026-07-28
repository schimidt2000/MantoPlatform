"""Endpoints de LEITURA do Google Maps (feature 195).

Proxy do Places Autocomplete: a `SiteSetting.google_maps_api_key` fica exclusivamente no servidor
e o frontend consome esta rota, nunca a API do Google diretamente. A regra de negócio mora em
`app/maps.py` (fonte única, reusada pela Distance Matrix desde a feature 076) — aqui só validamos
RBAC e serializamos.
"""

from typing import Any

from flask import jsonify, request

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.maps import address_autocomplete


@api_bp.route("/maps/address-autocomplete")
@api_login_required
def api_maps_address_autocomplete() -> Any:
    """Sugestões de endereço para um termo digitado (`?q=`), restritas ao Brasil.

    RBAC: qualquer usuário autenticado do staff — a rota é usada pelo formulário de eventos e
    pelas duas calculadoras, que já têm RBAC próprio nas suas telas/endpoints de escrita. Não
    expõe nenhum dado do sistema, apenas o retorno público do Google.

    Query params:
        q: Texto digitado. Menos de `AUTOCOMPLETE_MIN_CHARS` caracteres devolve lista vazia.
        session_token: Token opcional de sessão do Places (agrupa a busca no billing do Google).

    Returns:
        `{"items": [{"description": str, "place_id": str}]}` em sucesso; envelope `json_error`
        com 502/503 se o Google falhar ou a chave não estiver configurada.
    """
    sugestoes, error, status = address_autocomplete(
        request.args.get("q", ""),
        session_token=(request.args.get("session_token") or None),
    )
    if error:
        return json_error(error, status)
    return jsonify({"items": sugestoes})
