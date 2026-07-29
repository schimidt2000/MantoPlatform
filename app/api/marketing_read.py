"""Endpoints de LEITURA da Gestão de Marketing e Frequência (feature 204).

`/api/marketing/posts` (planejamento — Kanban e tabela), `/api/marketing/goals` (metas de
frequência com a saúde já calculada) e `/api/marketing/opcoes` (Temas do catálogo e usuários para
os `Combobox` da tela). Reusa, sem duplicar, `app.marketing.marketing_ops`.

Gate: `MARKETING` ou `SUPERADMIN` — reimplementado como função, não decorator (padrão da camada
de API do projeto).
"""

from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app.api import api_bp
from app.api_utils import api_login_required, json_error
from app.constants import MARKETING_PLATFORMS, MARKETING_STATUSES, RoleName
from app.marketing import marketing_ops as ops
from app.models import CatalogItem, MarketingFrequencyGoal, MarketingPost, User


def has_marketing_access(user: Any) -> bool:
    """True se o usuário pode ver/gerir o módulo de marketing (Marketing ou Superadmin)."""
    allowed = {RoleName.MARKETING, RoleName.SUPERADMIN}
    return any(role.name.upper() in allowed for role in user.roles)


def require_marketing_access() -> Any:
    """Devolve a resposta 403 quando o usuário não tem acesso ao módulo, ou `None`."""
    if not has_marketing_access(current_user):
        return json_error("Sem permissão", 403)
    return None


def load_post(post_id: int) -> MarketingPost | None:
    """Carrega uma postagem por id (fonte única usada também pelos endpoints de escrita)."""
    return MarketingPost.query.get(post_id)


def load_goal(goal_id: int) -> MarketingFrequencyGoal | None:
    """Carrega uma meta de frequência por id."""
    return MarketingFrequencyGoal.query.get(goal_id)


@api_bp.route("/marketing/posts")
@api_login_required
def api_marketing_posts_list() -> Any:
    """Postagens do planejamento (`?status=` e `?responsavel=` filtram).

    Devolve também `statuses` e `plataformas` para a interface montar as colunas do Kanban e o
    seletor de plataforma a partir do servidor, sem repetir a lista em dois lugares.
    """
    denied = require_marketing_access()
    if denied:
        return denied
    status = request.args.get("status", "").strip() or None
    assignee_id = request.args.get("responsavel", type=int)
    try:
        posts = ops.list_posts(status=status, assignee_id=assignee_id)
    except ops.MarketingValidationError as exc:
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(
        {
            "items": [ops.serialize_post(post) for post in posts],
            "statuses": MARKETING_STATUSES,
            "plataformas": MARKETING_PLATFORMS,
        }
    )


@api_bp.route("/marketing/posts/<int:post_id>")
@api_login_required
def api_marketing_post_detail(post_id: int) -> Any:
    """Detalhe de uma postagem do planejamento."""
    denied = require_marketing_access()
    if denied:
        return denied
    post = load_post(post_id)
    if post is None:
        return json_error("Postagem não encontrada", 404)
    return jsonify(ops.serialize_post(post))


@api_bp.route("/marketing/goals")
@api_login_required
def api_marketing_goals_list() -> Any:
    """Metas de frequência com `last_posted_date` e status derivado (`on_track`/`delayed`)."""
    denied = require_marketing_access()
    if denied:
        return denied
    goals = ops.list_goals()
    payload = [ops.serialize_goal(goal) for goal in goals]
    return jsonify(
        {
            "items": payload,
            "delayed_count": sum(1 for goal in payload if goal["status"] == "delayed"),
        }
    )


@api_bp.route("/marketing/opcoes")
@api_login_required
def api_marketing_options() -> Any:
    """Opções dos `Combobox` da tela: Temas ativos do catálogo e usuários com acesso.

    Existe porque `/api/admin/catalogo` é exclusivo de `SUPERADMIN` (feature 169) — o papel
    `MARKETING` precisa dos Temas para o vínculo visual sem ganhar acesso à gestão do catálogo.
    """
    denied = require_marketing_access()
    if denied:
        return denied
    temas = (
        CatalogItem.query.filter(CatalogItem.is_active.is_(True))
        .order_by(CatalogItem.name.asc())
        .all()
    )
    usuarios = User.query.filter_by(is_active=True, has_access=True).order_by(User.name.asc()).all()
    return jsonify(
        {
            "temas": [ops.serialize_catalog_item(item) for item in temas],
            "usuarios": [
                {"id": user.id, "name": user.name, "photo_url": user.profile_photo}
                for user in usuarios
            ],
            "plataformas": MARKETING_PLATFORMS,
        }
    )
