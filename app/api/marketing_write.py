"""Endpoints de ESCRITA da Gestão de Marketing e Frequência (feature 204).

CRUD das postagens (`/api/marketing/posts`) e das metas (`/api/marketing/goals`), mais a ponte de
conveniência com o módulo de Revisão de Mídia (`POST /api/marketing/posts/<id>/create-review`).
Reusa, sem duplicar, `app.marketing.marketing_ops`. Gate: `MARKETING` ou `SUPERADMIN`.
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api.marketing_read import load_goal, load_post, require_marketing_access
from app.api_utils import api_login_required, json_error
from app.marketing import marketing_ops as ops

# Campos aceitos no corpo JSON de cada entidade — fonte única, para o POST e o PATCH nunca
# divergirem sobre o que existe.
POST_FIELDS = (
    "title",
    "status",
    "deadline_date",
    "publish_date",
    "platform",
    "drive_folder_url",
    "notes",
    "assignee_id",
    "catalog_item_ids",
)
GOAL_FIELDS = ("name", "target_interval_days", "catalog_item_id")


def _json_body() -> dict[str, Any]:
    """Corpo JSON da requisição (dicionário vazio quando ausente/inválido)."""
    return request.get_json(silent=True) or {}


def _create_kwargs(body: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    """Valores enviados na criação — campo ausente vira `None` (a validação decide se pode)."""
    return {field: body.get(field) for field in fields}


def _patch_kwargs(body: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    """Valores enviados na edição — campo ausente vira `KEEP` ("não alterar", ver `ops.KEEP`)."""
    return {field: body[field] if field in body else ops.KEEP for field in fields}


# ── Postagens ────────────────────────────────────────────────────────────────


@api_bp.route("/marketing/posts", methods=["POST"])
@api_login_required
def api_marketing_post_create() -> Any:
    """Cria uma postagem no planejamento (JSON)."""
    denied = require_marketing_access()
    if denied:
        return denied
    try:
        post = ops.create_post(**_create_kwargs(_json_body(), POST_FIELDS))
    except ops.MarketingValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(ops.serialize_post(post)), 201


@api_bp.route("/marketing/posts/<int:post_id>", methods=["PATCH"])
@api_login_required
def api_marketing_post_update(post_id: int) -> Any:
    """Edita uma postagem — inclui a troca de coluna do Kanban (`status`)."""
    denied = require_marketing_access()
    if denied:
        return denied
    post = load_post(post_id)
    if post is None:
        return json_error("Postagem não encontrada", 404)
    try:
        ops.update_post(post, **_patch_kwargs(_json_body(), POST_FIELDS))
    except ops.MarketingValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(ops.serialize_post(post))


@api_bp.route("/marketing/posts/<int:post_id>", methods=["DELETE"])
@api_login_required
def api_marketing_post_delete(post_id: int) -> Any:
    """Exclui uma postagem (o espaço de revisão vinculado continua existindo)."""
    denied = require_marketing_access()
    if denied:
        return denied
    post = load_post(post_id)
    if post is None:
        return json_error("Postagem não encontrada", 404)
    ops.delete_post(post)
    return "", 204


@api_bp.route("/marketing/posts/<int:post_id>/create-review", methods=["POST"])
@api_login_required
def api_marketing_post_create_review(post_id: int) -> Any:
    """Cria um espaço de Revisão de Mídia com o título do post e o vincula (1:1).

    Endpoint de conveniência: devolve `review_space_id` para o frontend redirecionar direto para
    `/revisao/<id>`, sem obrigar a equipe a criar o espaço à mão e lembrar de colar o vínculo.
    """
    denied = require_marketing_access()
    if denied:
        return denied
    post = load_post(post_id)
    if post is None:
        return json_error("Postagem não encontrada", 404)
    try:
        space = ops.attach_review_space(post, creator_id=current_user.id)
    except ops.MarketingValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify({"review_space_id": space.id, "post": ops.serialize_post(post)}), 201


# ── Metas de frequência ──────────────────────────────────────────────────────


@api_bp.route("/marketing/goals", methods=["POST"])
@api_login_required
def api_marketing_goal_create() -> Any:
    """Cria uma meta de frequência (JSON)."""
    denied = require_marketing_access()
    if denied:
        return denied
    try:
        goal = ops.create_goal(**_create_kwargs(_json_body(), GOAL_FIELDS))
    except ops.MarketingValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(ops.serialize_goal(goal)), 201


@api_bp.route("/marketing/goals/<int:goal_id>", methods=["PATCH"])
@api_login_required
def api_marketing_goal_update(goal_id: int) -> Any:
    """Edita uma meta de frequência."""
    denied = require_marketing_access()
    if denied:
        return denied
    goal = load_goal(goal_id)
    if goal is None:
        return json_error("Meta não encontrada", 404)
    try:
        ops.update_goal(goal, **_patch_kwargs(_json_body(), GOAL_FIELDS))
    except ops.MarketingValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(ops.serialize_goal(goal))


@api_bp.route("/marketing/goals/<int:goal_id>", methods=["DELETE"])
@api_login_required
def api_marketing_goal_delete(goal_id: int) -> Any:
    """Exclui uma meta de frequência (as postagens seguem intactas)."""
    denied = require_marketing_access()
    if denied:
        return denied
    goal = load_goal(goal_id)
    if goal is None:
        return json_error("Meta não encontrada", 404)
    ops.delete_goal(goal)
    return "", 204
