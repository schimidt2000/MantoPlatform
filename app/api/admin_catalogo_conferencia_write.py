"""Endpoints de ESCRITA da conferência de personagens do catálogo (feature 360).

RBAC: SUPERADMIN em todas as rotas — o mesmo gate da gestão do catálogo, chamado no início de cada
view.

As rotas de decisão não alteram o catálogo; só `…/gravar` (feature 364) escreve nele. A conferência registra decisões
(`app.admin.catalog_conferencia_ops`). Toda rota de decisão devolve `{"conferencia", "situacao"}`
para a tela atualizar o item sem nova consulta.
"""

from collections.abc import Callable
from typing import Any

from flask import jsonify, request
from flask_login import current_user

from app import db
from app.admin import catalog_conferencia_ops as ops
from app.admin import catalog_gravacao_ops
from app.api import api_bp
from app.api.admin_catalogo_read import _require_superadmin
from app.api_utils import api_login_required, json_error
from app.models import CatalogConferencia

CAMPOS_DO_ITEM = ("tipo", "ficha_id", "observacao")
CAMPOS_DO_PERSONAGEM = ("nome", "ficha_id", "decisao", "sem_foto", "observacao")


def _corpo(permitidos: tuple[str, ...]) -> dict:
    """Só os campos previstos, e só os que vieram: campo ausente não muda nada."""
    bruto = request.get_json(silent=True) or {}
    return {campo: bruto[campo] for campo in permitidos if campo in bruto}


def _decidir(acao: Callable[[], CatalogConferencia], status: int = 200) -> Any:
    """Roda uma decisão do núcleo e traduz as três recusas dele em `json_error`."""
    denied = _require_superadmin()
    if denied:
        return denied
    try:
        conferencia = acao()
    except ops.ConferenciaNaoEncontrada as exc:
        db.session.rollback()
        return json_error(exc.message, 404)
    except ops.ConferenciaConflito as exc:
        db.session.rollback()
        return json_error(exc.message, 409, codigo=exc.codigo)
    except ops.ConferenciaValidationError as exc:
        db.session.rollback()
        return json_error(exc.message, 400, fields={exc.field: exc.message})
    return jsonify(ops.resposta_da_conferencia(conferencia)), status


@api_bp.route("/admin/catalogo/conferencia/carregar", methods=["POST"])
@api_login_required
def api_catalogo_conferencia_carregar() -> Any:
    """Carrega a leitura versionada. Idempotente: só acrescenta item que ainda não tem leitura."""
    denied = _require_superadmin()
    if denied:
        return denied
    return jsonify(ops.carregar_leitura(ops.ler_arquivo_da_leitura()))


@api_bp.route("/admin/catalogo/conferencia/<int:item_id>", methods=["PATCH"])
@api_login_required
def api_catalogo_conferencia_alterar_item(item_id: int) -> Any:
    """Corrige o tipo, a ficha (só em avulso) e a observação do item."""
    return _decidir(lambda: ops.alterar_item(item_id, _corpo(CAMPOS_DO_ITEM)))


@api_bp.route("/admin/catalogo/conferencia/<int:item_id>/conferir", methods=["POST"])
@api_login_required
def api_catalogo_conferencia_conferir(item_id: int) -> Any:
    """Marca o item como conferido por quem está logado."""
    return _decidir(lambda: ops.conferir(item_id, current_user.id))


@api_bp.route("/admin/catalogo/conferencia/<int:item_id>/reabrir", methods=["POST"])
@api_login_required
def api_catalogo_conferencia_reabrir(item_id: int) -> Any:
    """Devolve o item para "a conferir", preservando as decisões."""
    return _decidir(lambda: ops.reabrir(item_id))


@api_bp.route("/admin/catalogo/conferencia/<int:item_id>/personagens", methods=["POST"])
@api_login_required
def api_catalogo_conferencia_acrescentar(item_id: int) -> Any:
    """Acrescenta um personagem que a leitura não viu (`nome`, `ficha_id` opcional)."""
    corpo = request.get_json(silent=True) or {}
    return _decidir(
        lambda: ops.acrescentar_personagem(item_id, corpo.get("nome"), corpo.get("ficha_id")),
        status=201,
    )


@api_bp.route("/admin/catalogo/conferencia/personagens/<int:personagem_id>", methods=["PATCH"])
@api_login_required
def api_catalogo_conferencia_alterar_personagem(personagem_id: int) -> Any:
    """Corrige nome, ficha, decisão, "criar sem foto" e observação de um personagem."""
    return _decidir(lambda: ops.alterar_personagem(personagem_id, _corpo(CAMPOS_DO_PERSONAGEM)))


@api_bp.route("/admin/catalogo/conferencia/personagens/<int:personagem_id>", methods=["DELETE"])
@api_login_required
def api_catalogo_conferencia_excluir_personagem(personagem_id: int) -> Any:
    """Exclui um personagem acrescentado à mão; o da leitura devolve 409 `da_leitura`."""
    return _decidir(lambda: ops.excluir_personagem(personagem_id))


@api_bp.route("/admin/catalogo/conferencia/gravar", methods=["POST"])
@api_login_required
def api_catalogo_conferencia_gravar() -> Any:
    """Grava no catálogo um lote do que foi conferido (feature 364). A tela chama em laço.

    É a única rota da conferência que escreve no catálogo: cria os personagens dos temas e duplas
    conferidos e liga a ficha dos avulsos. Idempotente; `restantes` diz se ainda há o que gravar.
    """
    denied = _require_superadmin()
    if denied:
        return denied
    return jsonify(catalog_gravacao_ops.gravar_lote())
