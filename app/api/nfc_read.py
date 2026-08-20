"""Endpoints de LEITURA das Tags NFC (feature 255).

Dois mundos no mesmo arquivo, de propósito separados pelo gate:

- `GET /api/nfc/<code>` é **público** (sem login, padrão `catalogo_read.py`): é o que a página
  `/nfc/<code>` da vitrine consome quando a cliente encosta o celular na luminária. A resposta
  tem SEMPRE o mesmo shape — código inexistente é indistinguível de tag desativada.
- `GET /api/3d/nfc` é a lista de gestão do ERP. Gate: `ARTISTA_3D` ou `SUPERADMIN`
  (reusa `require_3d_access` da feature 200).
"""

from typing import Any

from flask import jsonify

from app.api import api_bp
from app.api.agenda_read import client_of_event
from app.api.impressoes3d_read import require_3d_access
from app.api_utils import api_login_required
from app.constants import MANTO_INSTAGRAM_URL
from app.impressoes3d import nfc_ops
from app.models import NfcTag


@api_bp.route("/nfc/<code>")
def api_nfc_resolve(code: str) -> Any:
    """Resolve o código de uma tag NFC — público, sem login, sempre 200.

    Todo o conteúdo da página pública nasce aqui (até o link do Instagram): a URL gravada na
    tag física é imutável, então o servidor é quem evolui o que ela mostra. `campaign` é o
    gancho para o sistema futuro de campanhas — hoje sempre `null`.
    """
    payload = nfc_ops.resolve_code(code)
    payload["instagram_url"] = MANTO_INSTAGRAM_URL
    return jsonify(payload)


def _serialize_admin_tag(tag: NfcTag) -> dict[str, Any]:
    """Linha da lista do ERP: payload do ops + nome da cliente do evento.

    O `client_name` entra AQUI (e não em `nfc_ops.serialize_tag`) porque `client_of_event`
    mora na camada de API — ops não importa de `app.api`.
    """
    entry = nfc_ops.serialize_tag(tag)
    client_name, _phone = client_of_event(tag.event) if tag.event else (None, None)
    entry["client_name"] = client_name
    return entry


@api_bp.route("/3d/nfc")
@api_login_required
def api_3d_nfc_list() -> Any:
    """Lista de tags NFC para a tela de gestão (`/3d/tags`), ordenada por item + nº."""
    denied = require_3d_access()
    if denied:
        return denied
    return jsonify({"tags": [_serialize_admin_tag(t) for t in nfc_ops.list_tags()]})
