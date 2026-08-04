"""Núcleo de negócio da Gestão de Marketing e Frequência (feature 204).

Funções puras (sem `request`/`render_template`/`flash`), fonte única reusada pelos endpoints JSON
de `app/api/marketing_read.py` e `app/api/marketing_write.py`. Não há view Jinja equivalente:
o módulo nasceu depois da migração para SPA (Princípio III).

Duas responsabilidades:

1. **Planejamento** (`MarketingPost`) — o card do Kanban, com os vínculos para o Tema do catálogo,
   o responsável e o espaço de Revisão de Mídia. A ponte com a revisão reusa
   `app.revisao.review_ops.create_space` em vez de recriar um `ReviewSpace` à mão (Princípio I).
2. **Motor de metas** (`MarketingFrequencyGoal`) — "postar sobre 15 Anos a cada 15 dias". A saúde
   da meta (`last_posted_date`, `on_track`/`delayed`) é **derivada na leitura** a partir dos posts
   já publicados: nada de coluna de estado a recalcular por job, e mover um card para "publicado"
   já conserta a meta na hora.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app import db
from app.constants import (
    MARKETING_MAX_INTERVAL_DAYS,
    MARKETING_PLATFORMS,
    MARKETING_STATUS_IDEIA,
    MARKETING_STATUS_PUBLICADO,
    MARKETING_STATUSES,
)
from app.models import (
    CatalogItem,
    MarketingFrequencyGoal,
    MarketingPost,
    ReviewSpace,
    User,
)
from app.revisao import review_ops
from app.utils import audit

# Sentinela de "campo não enviado" nos PATCH: `None` é valor válido (limpa o campo), então não
# serve para distinguir "apagar" de "não mexer". Mesmo padrão de `impressoes3d_ops.update_event_gift`.
KEEP = ...

# Só link http(s) vai para um `target="_blank"` da interface — `javascript:` num href é XSS.
ALLOWED_URL_SCHEMES = ("http://", "https://")

# Status de um espaço de revisão vinculado, derivado dos materiais que ele contém.
REVIEW_STATUS_SEM_MATERIAL = "sem_material"
REVIEW_STATUS_EM_REVISAO = "em_revisao"
REVIEW_STATUS_AJUSTES = "precisa_ajustes"
REVIEW_STATUS_APROVADO = "aprovado"


class MarketingValidationError(Exception):
    """Erro de validação de negócio do módulo, com o campo culpado.

    O endpoint traduz em `json_error(msg, 400, fields={campo: msg})`, para o React destacar o
    campo exato do formulário (Princípio V — falha de validação sempre tem feedback no campo).
    """

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


# ── Validações e conversões de entrada ───────────────────────────────────────


def _clean_title(raw: Any) -> str:
    """Título obrigatório do post/meta, sem espaços nas pontas."""
    title = (raw or "").strip()
    if not title:
        raise MarketingValidationError("title", "Informe um título para a postagem.")
    return title[:200]


def _validate_status(raw: Any) -> str:
    """Garante que o status informado é um dos cinco do fluxo do Kanban."""
    status = str(raw or "").strip().lower()
    if status not in MARKETING_STATUSES:
        raise MarketingValidationError(
            "status", f"Status inválido (use: {', '.join(MARKETING_STATUSES)})."
        )
    return status


def _validate_platform(raw: Any) -> str | None:
    """Plataforma de publicação (opcional), validada contra a lista fixa."""
    if raw in (None, ""):
        return None
    platform = str(raw).strip()
    if platform not in MARKETING_PLATFORMS:
        raise MarketingValidationError(
            "platform", f"Plataforma inválida (use: {', '.join(MARKETING_PLATFORMS)})."
        )
    return platform


def _parse_date(raw: Any, field: str) -> date | None:
    """Converte `YYYY-MM-DD` (ou vazio) em `date`."""
    if raw in (None, ""):
        return None
    if isinstance(raw, date):
        return raw
    try:
        return date.fromisoformat(str(raw))
    except ValueError:
        raise MarketingValidationError(field, "Data inválida (use AAAA-MM-DD).") from None


def _validate_drive_url(raw: Any) -> str | None:
    """Link do acervo no Google Drive (opcional) — só aceita http(s)."""
    if raw in (None, ""):
        return None
    url = str(raw).strip()
    if not url.lower().startswith(ALLOWED_URL_SCHEMES):
        raise MarketingValidationError(
            "drive_folder_url", "O link do Drive precisa começar com http:// ou https://."
        )
    return url


def _validate_interval(raw: Any) -> int:
    """Intervalo alvo da meta, em dias (inteiro ≥ 1)."""
    try:
        interval = int(raw)
    except (TypeError, ValueError):
        raise MarketingValidationError(
            "target_interval_days", "Informe o intervalo em dias (número inteiro)."
        ) from None
    if interval < 1 or interval > MARKETING_MAX_INTERVAL_DAYS:
        raise MarketingValidationError(
            "target_interval_days",
            f"O intervalo deve ficar entre 1 e {MARKETING_MAX_INTERVAL_DAYS} dias.",
        )
    return interval


def _resolve_catalog_item(raw: Any) -> int | None:
    """Valida o Tema do catálogo informado e devolve o id (ou `None` para desvincular)."""
    if raw in (None, ""):
        return None
    item = CatalogItem.query.get(raw)
    if item is None:
        raise MarketingValidationError("catalog_item_id", "Tema do catálogo não encontrado.")
    return item.id


def _resolve_catalog_items(raw: Any) -> list[CatalogItem]:
    """Valida a lista de Temas do catálogo de um post e devolve os itens (sem duplicatas).

    `None`/ausente vira lista vazia (post sem Tema é válido — ver docstring de `MarketingPost`).
    """
    if raw in (None, ""):
        return []
    if not isinstance(raw, list):
        raise MarketingValidationError("catalog_item_ids", "Envie os Temas como uma lista.")
    seen: set[int] = set()
    items: list[CatalogItem] = []
    for entry in raw:
        item = CatalogItem.query.get(entry)
        if item is None:
            raise MarketingValidationError("catalog_item_ids", "Tema do catálogo não encontrado.")
        if item.id not in seen:
            seen.add(item.id)
            items.append(item)
    return items


def _resolve_assignee(raw: Any) -> int | None:
    """Valida o responsável informado e devolve o id (ou `None` para desatribuir)."""
    if raw in (None, ""):
        return None
    user = User.query.get(raw)
    if user is None:
        raise MarketingValidationError("assignee_id", "Responsável não encontrado.")
    return user.id


# ── CRUD de postagens ────────────────────────────────────────────────────────


def list_posts(*, status: str | None = None, assignee_id: int | None = None) -> list[MarketingPost]:
    """Postagens do planejamento, das mais urgentes para as mais folgadas.

    Args:
        status: Filtra por uma coluna do Kanban (validado; `None` traz todas).
        assignee_id: Filtra por responsável.

    Returns:
        Posts ordenados por prazo mais apertado primeiro; sem prazo cai para o fim (ordenado pela
        data de publicação planejada e, em último critério, pelo id).
    """
    query = MarketingPost.query
    if status:
        query = query.filter(MarketingPost.status == _validate_status(status))
    if assignee_id:
        query = query.filter(MarketingPost.assignee_id == assignee_id)

    far_future = date.max
    return sorted(
        query.all(),
        key=lambda post: (
            post.deadline_date or far_future,
            post.publish_date or far_future,
            post.id,
        ),
    )


def create_post(
    *,
    title: Any,
    status: Any = None,
    deadline_date: Any = None,
    publish_date: Any = None,
    platform: Any = None,
    drive_folder_url: Any = None,
    notes: Any = None,
    assignee_id: Any = None,
    catalog_item_ids: Any = None,
) -> MarketingPost:
    """Cria uma postagem no planejamento.

    Raises:
        MarketingValidationError: Título vazio, status/plataforma/data inválidos, link do Drive
            fora de http(s), Tema(s) ou responsável inexistentes.
    """
    post = MarketingPost(
        title=_clean_title(title),
        status=_validate_status(status) if status else MARKETING_STATUS_IDEIA,
        deadline_date=_parse_date(deadline_date, "deadline_date"),
        publish_date=_parse_date(publish_date, "publish_date"),
        platform=_validate_platform(platform),
        drive_folder_url=_validate_drive_url(drive_folder_url),
        notes=(notes or "").strip() or None,
        assignee_id=_resolve_assignee(assignee_id),
        temas=_resolve_catalog_items(catalog_item_ids),
    )
    _autofill_publish_date(post)
    db.session.add(post)
    db.session.flush()
    audit("create", "MarketingPost", post.id, post.title, "Postagem de marketing criada")
    db.session.commit()
    return post


def _autofill_publish_date(post: MarketingPost) -> None:
    """Post marcado como publicado sem data ganha a data de hoje.

    Existe porque é `publish_date` que alimenta o motor de metas: um card arrastado para
    "publicado" sem data preenchida não contaria como postagem e a meta continuaria "atrasada"
    sem motivo. Sair de "publicado" **não** apaga a data — o histórico é do usuário.
    """
    if post.status == MARKETING_STATUS_PUBLICADO and post.publish_date is None:
        post.publish_date = date.today()


def update_post(
    post: MarketingPost,
    *,
    title: Any = KEEP,
    status: Any = KEEP,
    deadline_date: Any = KEEP,
    publish_date: Any = KEEP,
    platform: Any = KEEP,
    drive_folder_url: Any = KEEP,
    notes: Any = KEEP,
    assignee_id: Any = KEEP,
    catalog_item_ids: Any = KEEP,
) -> MarketingPost:
    """Edita uma postagem. Só aplica os campos explicitamente enviados.

    Todo campo usa a sentinela `KEEP` (`...`) para "não alterar", porque `None`/lista vazia é um
    valor válido em quase todos eles (limpar prazo, desvincular todos os Temas, desatribuir
    responsável).
    """
    if title is not KEEP:
        post.title = _clean_title(title)
    if status is not KEEP:
        post.status = _validate_status(status)
    if deadline_date is not KEEP:
        post.deadline_date = _parse_date(deadline_date, "deadline_date")
    if publish_date is not KEEP:
        post.publish_date = _parse_date(publish_date, "publish_date")
    if platform is not KEEP:
        post.platform = _validate_platform(platform)
    if drive_folder_url is not KEEP:
        post.drive_folder_url = _validate_drive_url(drive_folder_url)
    if notes is not KEEP:
        post.notes = (notes or "").strip() or None
    if assignee_id is not KEEP:
        post.assignee_id = _resolve_assignee(assignee_id)
    if catalog_item_ids is not KEEP:
        post.temas = _resolve_catalog_items(catalog_item_ids)

    _autofill_publish_date(post)
    audit("edit", "MarketingPost", post.id, post.title, "Postagem de marketing editada")
    db.session.commit()
    return post


def delete_post(post: MarketingPost) -> None:
    """Exclui uma postagem do planejamento.

    O espaço de revisão vinculado **não** é excluído: os materiais e os comentários da revisão têm
    vida própria (e outras pessoas os usam). Apagar o card só desfaz o vínculo.
    """
    post_id, title = post.id, post.title
    db.session.delete(post)
    audit("delete", "MarketingPost", post_id, title, "Postagem de marketing excluída")
    db.session.commit()


def attach_review_space(post: MarketingPost, *, creator_id: int) -> ReviewSpace:
    """Cria um espaço de Revisão de Mídia com o título do post e o vincula a ele.

    Reusa `review_ops.create_space` (fonte única da criação de espaço, Princípio I) — o espaço
    nasce vazio, sem revisores: quem vai revisar é decidido dentro do próprio módulo de revisão.

    Raises:
        MarketingValidationError: O post já tem espaço vinculado (o vínculo é 1:1).
    """
    if post.review_space_id is not None:
        raise MarketingValidationError(
            "review_space_id", "Esta postagem já tem um espaço de revisão vinculado."
        )
    space, _saved, _errors = review_ops.create_space(
        title=post.title,
        description=f"Espaço criado a partir da postagem de marketing #{post.id}.",
        creator_id=creator_id,
        reviewer_ids=[],
        files=[],
    )
    post.review_space_id = space.id
    audit(
        "edit",
        "MarketingPost",
        post.id,
        post.title,
        f"Espaço de revisão #{space.id} criado e vinculado à postagem",
    )
    db.session.commit()
    return space


# ── CRUD de metas de frequência ──────────────────────────────────────────────


def list_goals() -> list[MarketingFrequencyGoal]:
    """Metas de frequência em ordem alfabética."""
    return MarketingFrequencyGoal.query.order_by(MarketingFrequencyGoal.name.asc()).all()


def create_goal(
    *, name: Any, target_interval_days: Any, catalog_item_id: Any = None
) -> MarketingFrequencyGoal:
    """Cria uma meta de frequência ("Festa de 15 Anos a cada 15 dias")."""
    goal = MarketingFrequencyGoal(
        name=_clean_goal_name(name),
        target_interval_days=_validate_interval(target_interval_days),
        catalog_item_id=_resolve_catalog_item(catalog_item_id),
    )
    db.session.add(goal)
    db.session.flush()
    audit("create", "MarketingFrequencyGoal", goal.id, goal.name, "Meta de frequência criada")
    db.session.commit()
    return goal


def _clean_goal_name(raw: Any) -> str:
    """Nome obrigatório da meta — o campo culpado é `name`, não `title`."""
    name = (raw or "").strip()
    if not name:
        raise MarketingValidationError("name", "Informe o nome do assunto da meta.")
    return name[:200]


def update_goal(
    goal: MarketingFrequencyGoal,
    *,
    name: Any = KEEP,
    target_interval_days: Any = KEEP,
    catalog_item_id: Any = KEEP,
) -> MarketingFrequencyGoal:
    """Edita uma meta de frequência. Só aplica os campos explicitamente enviados."""
    if name is not KEEP:
        goal.name = _clean_goal_name(name)
    if target_interval_days is not KEEP:
        goal.target_interval_days = _validate_interval(target_interval_days)
    if catalog_item_id is not KEEP:
        goal.catalog_item_id = _resolve_catalog_item(catalog_item_id)

    audit("edit", "MarketingFrequencyGoal", goal.id, goal.name, "Meta de frequência editada")
    db.session.commit()
    return goal


def delete_goal(goal: MarketingFrequencyGoal) -> None:
    """Exclui uma meta de frequência (as postagens seguem intactas)."""
    goal_id, name = goal.id, goal.name
    db.session.delete(goal)
    audit("delete", "MarketingFrequencyGoal", goal_id, name, "Meta de frequência excluída")
    db.session.commit()


# ── Motor de frequência (status derivado, calculado na leitura) ──────────────


def _escape_like(term: str) -> str:
    """Neutraliza os curingas do LIKE — um assunto com "%" no nome não pode casar com tudo."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def last_published_post(goal: MarketingFrequencyGoal) -> MarketingPost | None:
    """Postagem publicada mais recente que "bate" com o assunto da meta.

    O casamento tem dois modos, na ordem de confiabilidade:
    1. **Tema do catálogo vinculado** — casa se **qualquer um** dos Temas do post for o Tema da
       meta (um post pode juntar vários Temas no mesmo vídeo e ainda contar para cada meta);
    2. **Sem Tema** — casa pelo nome da meta contido no título do post (`ILIKE`), para assuntos
       que não existem como item do catálogo (ex.: "Bastidores").

    Considera apenas posts com `status = 'publicado'` **e** `publish_date` preenchida: sem data
    não há como medir frequência.
    """
    query = MarketingPost.query.filter(
        MarketingPost.status == MARKETING_STATUS_PUBLICADO,
        MarketingPost.publish_date.isnot(None),
    )
    if goal.catalog_item_id:
        query = query.filter(MarketingPost.temas.any(CatalogItem.id == goal.catalog_item_id))
    else:
        query = query.filter(MarketingPost.title.ilike(f"%{_escape_like(goal.name)}%", escape="\\"))
    return query.order_by(MarketingPost.publish_date.desc(), MarketingPost.id.desc()).first()


def goal_health(goal: MarketingFrequencyGoal, *, today: date | None = None) -> dict[str, Any]:
    """Saúde da meta: quando foi o último post do assunto e se ela está em dia.

    Args:
        goal: A meta a avaliar.
        today: Data de referência (injetável para teste); default é hoje.

    Returns:
        Dicionário com `last_posted_date`, `next_due_date`, `days_since_last_post`, `days_late`,
        `never_posted` e `status` (`on_track` | `delayed`). Meta sem nenhum post publicado é
        `delayed` com `never_posted=True`: nunca ter postado é o atraso máximo, não "em dia".
    """
    reference = today or date.today()
    last_post = last_published_post(goal)
    if last_post is None or last_post.publish_date is None:
        return {
            "last_posted_date": None,
            "last_post_id": None,
            "next_due_date": None,
            "days_since_last_post": None,
            "days_late": None,
            "never_posted": True,
            "status": "delayed",
        }

    last_date = last_post.publish_date
    days_since = (reference - last_date).days
    next_due = date.fromordinal(last_date.toordinal() + goal.target_interval_days)
    days_late = max(0, days_since - goal.target_interval_days)
    return {
        "last_posted_date": last_date.isoformat(),
        "last_post_id": last_post.id,
        "next_due_date": next_due.isoformat(),
        "days_since_last_post": days_since,
        "days_late": days_late,
        "never_posted": False,
        "status": "delayed" if days_late > 0 else "on_track",
    }


# ── Serialização (fonte única dos payloads JSON do módulo) ───────────────────


def serialize_catalog_item(item: CatalogItem | None) -> dict[str, Any] | None:
    """Tema do catálogo em JSON — nome e capa, o suficiente para a miniatura (Princípio X.2)."""
    if item is None:
        return None
    cover = item.cover_image
    return {
        "id": item.id,
        "name": item.name,
        "cover_url": cover.url if cover else None,
        "is_active": bool(item.is_active),
    }


def _serialize_assignee(user: User | None) -> dict[str, Any] | None:
    """Responsável em JSON — nome e foto de perfil para o avatar circular."""
    if user is None:
        return None
    return {"id": user.id, "name": user.name, "photo_url": user.profile_photo}


def review_space_status(space: ReviewSpace) -> str:
    """Situação do espaço de revisão, derivada do status dos materiais dentro dele.

    `aprovado` só quando **todos** os materiais estão aprovados; qualquer material pedindo ajuste
    ou rejeitado puxa o espaço para `precisa_ajustes` — é o que a equipe precisa ver no card.
    """
    assets = space.assets
    if not assets:
        return REVIEW_STATUS_SEM_MATERIAL
    statuses = [asset.status for asset in assets]
    if all(status == REVIEW_STATUS_APROVADO for status in statuses):
        return REVIEW_STATUS_APROVADO
    if any(status in (REVIEW_STATUS_AJUSTES, "rejeitado") for status in statuses):
        return REVIEW_STATUS_AJUSTES
    return REVIEW_STATUS_EM_REVISAO


def serialize_review_space(space: ReviewSpace | None) -> dict[str, Any] | None:
    """Espaço de revisão vinculado em JSON — situação e contagem de materiais aprovados."""
    if space is None:
        return None
    assets = space.assets
    return {
        "id": space.id,
        "title": space.title,
        "asset_count": len(assets),
        "approved_count": sum(1 for asset in assets if asset.status == REVIEW_STATUS_APROVADO),
        "status": review_space_status(space),
    }


def serialize_post(post: MarketingPost) -> dict[str, Any]:
    """Postagem em JSON, com responsável, Temas do catálogo e espaço de revisão aninhados."""
    return {
        "id": post.id,
        "title": post.title,
        "status": post.status,
        "deadline_date": post.deadline_date.isoformat() if post.deadline_date else None,
        "publish_date": post.publish_date.isoformat() if post.publish_date else None,
        "platform": post.platform,
        "drive_folder_url": post.drive_folder_url,
        "notes": post.notes,
        "assignee_id": post.assignee_id,
        "assignee": _serialize_assignee(post.assignee),
        "catalog_item_ids": [item.id for item in post.temas],
        "catalog_items": [serialize_catalog_item(item) for item in post.temas],
        "review_space_id": post.review_space_id,
        "review_space": serialize_review_space(post.review_space),
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
    }


def serialize_goal(goal: MarketingFrequencyGoal, *, today: date | None = None) -> dict[str, Any]:
    """Meta em JSON, já com a saúde calculada (`goal_health`) embutida."""
    return {
        "id": goal.id,
        "name": goal.name,
        "target_interval_days": goal.target_interval_days,
        "catalog_item_id": goal.catalog_item_id,
        "catalog_item": serialize_catalog_item(goal.catalog_item),
        "created_at": goal.created_at.isoformat() if goal.created_at else None,
        **goal_health(goal, today=today),
    }
