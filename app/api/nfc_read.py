"""Endpoints de LEITURA das Tags NFC (feature 255) e das entregas anexadas a elas (feature 261).

Dois mundos no mesmo arquivo, de propósito separados pelo gate:

- `GET /api/nfc/<code>` e `GET /api/nfc/<code>/entregas/<id>/media` são **públicos** (sem login,
  padrão `catalogo_read.py`): é o que a página `/nfc/<code>` da vitrine consome quando a cliente
  encosta o celular na luminária. A resolução tem SEMPRE o mesmo shape — código inexistente é
  indistinguível de tag desativada; a mídia responde 404 idêntico para código errado, tag
  desativada e entrega inexistente/inativa — nada aqui pode confirmar existência.
- `GET /api/3d/nfc` é a lista de gestão do ERP. Gate: `ARTISTA_3D` ou `SUPERADMIN`
  (reusa `require_3d_access` da feature 200).
- `GET /api/3d/nfc/<tag_id>/entregas/<id>/media` (feature 265) é o espelho ADMIN da mídia:
  mesmo gate da lista, serve inclusive tag desativada e NUNCA toca `access_count` — é como a
  equipe revisa um vídeo sem inflar a métrica de acessos das clientes.
"""

import os
from typing import Any

from flask import jsonify, send_file

from app import limiter
from app.api import api_bp
from app.api.agenda_read import client_of_event
from app.api.impressoes3d_read import require_3d_access
from app.api_utils import api_login_required, json_error
from app.constants import MANTO_INSTAGRAM_URL
from app.impressoes3d import nfc_ops
from app.models import NfcTag, NfcTagDelivery


@api_bp.route("/nfc/<code>")
def api_nfc_resolve(code: str) -> Any:
    """Resolve o código de uma tag NFC — público, sem login, sempre 200.

    Todo o conteúdo da página pública nasce aqui (até o link do Instagram): a URL gravada na
    tag física é imutável, então o servidor é quem evolui o que ela mostra. `campaign` é o
    gancho para o sistema futuro de campanhas — hoje sempre `null`. `deliveries` (feature 261)
    é a lista de vídeo/foto/link anexados — hoje só vídeo, no máximo um.
    """
    payload = nfc_ops.resolve_code(code)
    payload["instagram_url"] = MANTO_INSTAGRAM_URL
    return jsonify(payload)


@api_bp.route("/nfc/<code>/entregas/<int:delivery_id>/media")
@limiter.limit("120 per minute")
def api_nfc_delivery_media(code: str, delivery_id: int) -> Any:
    """Serve o arquivo de uma entrega — público, revalidado a cada requisição (feature 261).

    Espelha `GET /api/virtuais/pedidos/<token>/video` (feature 205): o arquivo mora fora de
    `UPLOAD_FOLDER`, então este endpoint é o ÚNICO caminho até ele. Código errado, tag inativa,
    entrega de outra tag e entrega inativa devolvem o MESMO 404 genérico — nenhum deles pode
    revelar mais que o outro (mesmo espírito do SC-006 de `resolve_code`). `conditional=True` dá
    suporte a `Range`, essencial para o vídeo tocar no celular sem baixar tudo de uma vez.
    """
    clean_code = (code or "").strip().upper()
    tag = NfcTag.query.filter_by(code=clean_code).first() if clean_code else None
    if tag is None or not tag.is_active:
        return json_error("Arquivo não encontrado", 404)

    delivery = next(
        (d for d in tag.deliveries if d.id == delivery_id and d.is_active), None
    )
    if delivery is None:
        return json_error("Arquivo não encontrado", 404)

    caminho = nfc_ops.delivery_media_path(delivery)
    if not caminho or not os.path.exists(caminho):
        return json_error("Arquivo não encontrado", 404)

    # `max_age`: sem ele o Flask manda `no-cache` e cada revisita rebaixa o vídeo inteiro pelo
    # Python, segurando uma thread do gunicorn a cada vez. Trocar o vídeo cria uma entrega nova
    # (id novo na URL), então cache velho não existe. O limite de taxa acima é folgado de
    # propósito: um player pede muitos `Range` ao arrastar a barra — 120/min nunca alcança gente
    # de verdade, só script martelando.
    return send_file(
        caminho,
        mimetype=nfc_ops.delivery_mime_type(delivery),
        conditional=True,
        max_age=86400,
    )


@api_bp.route("/3d/nfc/<int:tag_id>/entregas/<int:delivery_id>/media")
@api_login_required
def api_3d_nfc_delivery_media(tag_id: int, delivery_id: int) -> Any:
    """Serve o arquivo de uma entrega para REVISÃO no ERP — nunca toca `access_count` (265).

    Existe porque revisar pelo link público (`/nfc/<code>`) incrementava a métrica de acesso
    das clientes (o contador mora em `resolve_code`, que a página pública sempre chama).
    Diferenças do endpoint público: gate ARTISTA_3D/SUPERADMIN, busca por `tag_id` (não por
    código) e serve MESMO com a tag desativada — tag inativa com vídeo continua auditável por
    dentro. `max_age`/`conditional` pelo mesmo motivo do público: substituir o vídeo cria uma
    entrega nova (URL nova), então cache velho não existe, e `Range` deixa arrastar a barra.
    """
    denied = require_3d_access()
    if denied:
        return denied

    delivery = NfcTagDelivery.query.filter_by(id=delivery_id, tag_id=tag_id).first()
    if delivery is None:
        return json_error("Entrega não encontrada", 404)

    caminho = nfc_ops.delivery_media_path(delivery)
    if not caminho or not os.path.exists(caminho):
        return json_error("Arquivo não encontrado", 404)

    return send_file(
        caminho,
        mimetype=nfc_ops.delivery_mime_type(delivery),
        conditional=True,
        max_age=86400,
    )


def _serialize_admin_tag(tag: NfcTag) -> dict[str, Any]:
    """Linha da lista do ERP: payload do ops + nome da cliente resolvido.

    Precedência: cliente DIRETA da tag (campanha/brinde sem show) → contratante do evento.
    O `client_name` entra AQUI (e não em `nfc_ops.serialize_tag`) porque `client_of_event`
    mora na camada de API — ops não importa de `app.api`. `client_direct` diz à UI se o nome
    veio do vínculo direto (editável na tag) ou de carona do evento.
    """
    entry = nfc_ops.serialize_tag(tag)
    if tag.client is not None:
        entry["client_name"] = tag.client.name
        entry["client_direct"] = True
    else:
        client_name, _phone = client_of_event(tag.event) if tag.event else (None, None)
        entry["client_name"] = client_name
        entry["client_direct"] = False
    return entry


@api_bp.route("/3d/nfc")
@api_login_required
def api_3d_nfc_list() -> Any:
    """Lista de tags NFC para a tela de gestão (`/3d/tags`), ordenada por item + nº."""
    denied = require_3d_access()
    if denied:
        return denied
    return jsonify({"tags": [_serialize_admin_tag(t) for t in nfc_ops.list_tags()]})
