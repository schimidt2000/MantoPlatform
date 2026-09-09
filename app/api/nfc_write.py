"""Endpoints de ESCRITA das Tags NFC (feature 255), das entregas (261) e dos recados (297).

RBAC: tudo em `/api/3d/nfc*` exige `ARTISTA_3D` ou `SUPERADMIN`, pelo gate no início de cada view.
A ÚNICA exceção é `POST /api/nfc/<code>/recados` — a rota pelo qual a cliente escreve de volta:
**pública, sem login**, com limite de taxa, como manda a natureza da página da tag.

A tag em si só tem duas escritas — gerar lote avulso e editar os campos mutáveis (evento,
situação, observações). **Não há DELETE de tag por contrato**: a tag física é eterna; a linha
idem. As entregas (vídeo, e futuramente foto/link) SÃO removíveis — são conteúdo anexado, não a
tag.
"""

from typing import Any

from flask import jsonify, request

from app import limiter
from app.api import api_bp
from app.api.impressoes3d_read import require_3d_access
from app.api.nfc_read import _serialize_admin_tag
from app.api_utils import api_login_required, json_error
from app.impressoes3d import nfc_ops, nfc_recados_ops
from app.models import NfcTag, NfcTagDelivery


def _bandeira(valor: str | None, *, padrao: bool) -> bool:
    """Lê um campo de multipart como booleano, com um padrão explícito quando ele não vem.

    O multipart não tem tipo: tudo chega string. `None` significa "o cliente não falou do assunto"
    e recebe o padrão; qualquer outra coisa é comparada contra a lista de verdades.
    """
    if valor is None:
        return padrao
    return valor.strip().lower() in ("1", "true", "sim", "on", "yes")


@api_bp.route("/3d/nfc/lote", methods=["POST"])
@api_login_required
def api_3d_nfc_batch() -> Any:
    """Gera um lote de tags avulsas (estoque, sem evento) — JSON `{item_id, quantity}`."""
    denied = require_3d_access()
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    try:
        created = nfc_ops.generate_batch(body.get("item_id"), body.get("quantity"))
    except nfc_ops.NfcValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify({"tags": [_serialize_admin_tag(t) for t in created]})


@api_bp.route("/3d/nfc/<int:tag_id>", methods=["PATCH"])
@api_login_required
def api_3d_nfc_update(tag_id: int) -> Any:
    """Edita uma tag: `event_id` (null desassocia), `is_active`, `notes` — campo ausente não altera."""
    denied = require_3d_access()
    if denied:
        return denied
    tag = NfcTag.query.get(tag_id)
    if tag is None:
        return json_error("Tag NFC não encontrada", 404)

    body = request.get_json(silent=True) or {}
    try:
        nfc_ops.update_tag(
            tag,
            # `...` = "não alterar" (None é válido: desassocia). `client_id` é a cliente
            # DIRETA — campanha/brinde sem show; independente do evento.
            event_id=body["event_id"] if "event_id" in body else ...,
            client_id=body["client_id"] if "client_id" in body else ...,
            is_active=body.get("is_active"),
            notes=body.get("notes"),
        )
    except nfc_ops.NfcValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify({"tag": _serialize_admin_tag(tag)})


@api_bp.route("/3d/nfc/<int:tag_id>/entregas", methods=["POST"])
@api_login_required
def api_3d_nfc_add_delivery(tag_id: int) -> Any:
    """Envia o vídeo da tag — multipart `file` + `kind` (só `"video"` por ora) + `title` opcional.

    Substitui a entrega de vídeo ativa da tag, se houver (1 vídeo ativo por tag por ora).
    """
    denied = require_3d_access()
    if denied:
        return denied
    tag = NfcTag.query.get(tag_id)
    if tag is None:
        return json_error("Tag NFC não encontrada", 404)

    file_obj = request.files.get("file")
    try:
        nfc_ops.add_delivery(
            tag,
            file_obj,
            kind=(request.form.get("kind") or "video").strip(),
            title=request.form.get("title"),
            # Ausente equivale a MARCADO: a caixinha do diálogo já nasce marcada, e o servidor
            # tem de concordar com ela — um cliente antigo que não mande o campo continua
            # entregando o comportamento que o dono pediu como padrão.
            com_moldura=_bandeira(request.form.get("com_moldura"), padrao=True),
        )
    except nfc_ops.NfcValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify({"tag": _serialize_admin_tag(tag)})


@api_bp.route("/3d/nfc/<int:tag_id>/entregas/<int:delivery_id>", methods=["DELETE"])
@api_login_required
def api_3d_nfc_remove_delivery(tag_id: int, delivery_id: int) -> Any:
    """Remove uma entrega (linha + arquivo do disco). Confirmação fica a cargo da UI."""
    denied = require_3d_access()
    if denied:
        return denied
    tag = NfcTag.query.get(tag_id)
    if tag is None:
        return json_error("Tag NFC não encontrada", 404)
    delivery = NfcTagDelivery.query.filter_by(id=delivery_id, tag_id=tag_id).first()
    if delivery is None:
        return json_error("Entrega não encontrada", 404)

    nfc_ops.remove_delivery(delivery)
    return jsonify({"tag": _serialize_admin_tag(tag)})


@api_bp.route("/3d/nfc/<int:tag_id>/entregas/<int:delivery_id>/reprocessar", methods=["POST"])
@api_login_required
def api_3d_nfc_reprocess_delivery(tag_id: int, delivery_id: int) -> Any:
    """Devolve o vídeo à fila de conversão, opcionalmente trocando a moldura (feature 297).

    Parte do MESTRE sem moldura quando ele existe; nas entregas anteriores à 297, que não têm
    mestre, parte do próprio arquivo entregue — com a perda de qualidade que isso implica e que o
    dono aceitou em troca de um vídeo assistível.
    """
    denied = require_3d_access()
    if denied:
        return denied
    tag = NfcTag.query.get(tag_id)
    if tag is None:
        return json_error("Tag NFC não encontrada", 404)
    delivery = NfcTagDelivery.query.filter_by(id=delivery_id, tag_id=tag_id).first()
    if delivery is None:
        return json_error("Entrega não encontrada", 404)

    body = request.get_json(silent=True) or {}
    com_moldura = body.get("com_moldura")
    try:
        nfc_ops.reprocessar_delivery(
            delivery,
            com_moldura=None if com_moldura is None else bool(com_moldura),
        )
    except nfc_ops.NfcValidationError as exc:
        return json_error(exc.message, 409, fields={exc.field: exc.message})
    return jsonify({"tag": _serialize_admin_tag(tag)})


@api_bp.route("/3d/nfc/moldura", methods=["PUT"])
@api_login_required
def api_3d_nfc_set_moldura() -> Any:
    """Cadastra a moldura PNG do sistema — multipart `file` (feature 297).

    Um arquivo só, para toda a plataforma. Recusa PNG sem transparência real: uma moldura opaca
    cobriria o vídeo inteiro em vez de emoldurá-lo, e o erro só apareceria depois, no vídeo da
    cliente.
    """
    denied = require_3d_access()
    if denied:
        return denied
    try:
        nfc_ops.salvar_arquivo_de_sistema(request.files.get("file"), tipo="moldura")
    except nfc_ops.NfcValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(nfc_ops.estado_dos_arquivos_de_sistema())


@api_bp.route("/3d/nfc/moldura", methods=["DELETE"])
@api_login_required
def api_3d_nfc_remove_moldura() -> Any:
    """Remove a moldura do sistema. Sem ela, todo envio sai sem moldura, com aviso na tela."""
    denied = require_3d_access()
    if denied:
        return denied
    nfc_ops.remover_arquivo_de_sistema(tipo="moldura")
    return jsonify(nfc_ops.estado_dos_arquivos_de_sistema())


@api_bp.route("/3d/nfc/abertura", methods=["PUT"])
@api_login_required
def api_3d_nfc_set_abertura() -> Any:
    """Cadastra o vídeo de abertura da página da tag — multipart `file` (feature 297).

    Passa pela MESMA conversão dos vídeos de tag, sem moldura: ele é servido a todo mundo que
    encosta o celular numa luminária, então precisa ser leve pelo mesmo motivo que os outros.
    """
    denied = require_3d_access()
    if denied:
        return denied
    try:
        nfc_ops.salvar_arquivo_de_sistema(request.files.get("file"), tipo="abertura")
    except nfc_ops.NfcValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(nfc_ops.estado_dos_arquivos_de_sistema())


@api_bp.route("/3d/nfc/abertura", methods=["DELETE"])
@api_login_required
def api_3d_nfc_remove_abertura() -> Any:
    """Remove o vídeo de abertura. Sem ele, a página da tag abre direto no menu."""
    denied = require_3d_access()
    if denied:
        return denied
    nfc_ops.remover_arquivo_de_sistema(tipo="abertura")
    return jsonify(nfc_ops.estado_dos_arquivos_de_sistema())


@api_bp.route("/3d/nfc/<int:tag_id>/recados/lidos", methods=["POST"])
@api_login_required
def api_3d_nfc_recados_lidos(tag_id: int) -> Any:
    """Marca como lidos os recados de uma tag (feature 297)."""
    denied = require_3d_access()
    if denied:
        return denied
    tag = NfcTag.query.get(tag_id)
    if tag is None:
        return json_error("Tag NFC não encontrada", 404)
    return jsonify({"marcados": nfc_recados_ops.marcar_lidos(tag_id)})


@api_bp.route("/nfc/<code>/recados", methods=["POST"])
@limiter.limit("10 per hour")
def api_nfc_recado_publico(code: str) -> Any:
    """A cliente escreve de volta — PÚBLICO, sem login (feature 297).

    Responde 201 mesmo quando o código não existe ou a tag está desativada, e nesses casos **nada
    é gravado**. Não é descuido: a leitura pública já é indistinguível por contrato desde a feature
    255 (SC-006), e uma escrita que respondesse diferente viraria um oráculo de quais códigos
    existem — o sufixo de seis caracteres é, na prática, um token de acesso.

    A notificação do sino é melhor-esforço em transação própria: o recado já está comitado quando
    ela roda, e falhar o aviso não pode desfazer o que a pessoa escreveu.
    """
    body = request.get_json(silent=True) or {}
    try:
        recado = nfc_recados_ops.registrar_recado(
            code,
            message=body.get("message") or "",
            author_name=body.get("author_name"),
        )
    except nfc_ops.NfcValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})

    if recado is not None:
        _avisar_do_recado(recado)
    return jsonify({"ok": True}), 201


def _avisar_do_recado(recado) -> None:
    """Toca o sino interno sem arriscar o recado já gravado (regime B da feature 272)."""
    from flask import current_app

    from app import db
    from app.notificacoes import notificacoes_ops

    try:
        notificacoes_ops.notificar_recado_nfc(recado)
        db.session.commit()
    except Exception:  # noqa: BLE001 — aviso é acessório; o recado já está a salvo
        db.session.rollback()
        current_app.logger.exception("Falha ao notificar recado de tag NFC %s", recado.id)
