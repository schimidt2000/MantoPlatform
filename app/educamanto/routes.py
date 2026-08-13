"""EducaManto — redirects do legado Jinja para a plataforma React (feature 235).

As telas Jinja do EducaManto (calculadora, pacotes, histórico) foram DESLIGADAS: a interface
é o bundle `apps/internal` servido em ``PLATFORM_BASE_URL`` (mesmo padrão da raiz do Flask,
ver `app/__init__.py::home`). Estas rotas existem só para capturar acesso residual (link
antigo, favorito) e devolvê-lo à tela React equivalente, de forma permanente.

A réplica JavaScript da fórmula morreu junto com os templates — o cálculo vive apenas em
`pricing_ops.py`, servido pela API (`app/api/educamanto_read.py`/`educamanto_write.py`).
"""

from flask import Blueprint, redirect, url_for

from app.config import PLATFORM_BASE_URL

educamanto_bp = Blueprint("educamanto", __name__, url_prefix="/educamanto")


def _spa(path: str):
    return redirect(f"{PLATFORM_BASE_URL}{path}", code=301)


@educamanto_bp.route("/")
def index():
    """Calculadora Jinja aposentada → calculadora React."""
    return _spa("/educamanto")


@educamanto_bp.route("/packages")
@educamanto_bp.route("/packages/create")
@educamanto_bp.route("/packages/<int:pkg_id>/edit")
def packages_legacy(pkg_id: int | None = None):
    """Telas Jinja de pacotes aposentadas → tela React de musicais."""
    return _spa("/educamanto/musicais")


@educamanto_bp.route("/historico")
def historico():
    """Histórico Jinja aposentado → histórico React."""
    return _spa("/educamanto/historico")


@educamanto_bp.route("/orcamento/<int:quote_id>/pdf")
def orcamento_pdf(quote_id: int):
    """Link antigo de PDF do histórico → endpoint de API equivalente (mesmo Flask)."""
    return redirect(url_for("api.api_orcamento_pdf", quote_id=quote_id), code=301)
