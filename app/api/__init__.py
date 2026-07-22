"""Camada de API JSON (`/api/*`) — Fundação da migração para SPA (feature 144).

Blueprint único com prefixo `/api`; os módulos de rotas (`auth`, `dashboard`) são
importados por efeito colateral no final para registrar suas rotas neste blueprint.
"""

from flask import Blueprint

api_bp = Blueprint("api", __name__, url_prefix="/api")

# Importa os módulos de rotas para registrá-los no blueprint (ordem após a criação do bp).
from app.api import auth as _auth  # noqa: E402,F401
from app.api import dashboard as _dashboard  # noqa: E402,F401
from app.api import agenda as _agenda  # noqa: E402,F401
from app.api import agenda_write as _agenda_write  # noqa: E402,F401
from app.api import talents_read as _talents_read  # noqa: E402,F401
from app.api import talents_write as _talents_write  # noqa: E402,F401
from app.api import figurino_read as _figurino_read  # noqa: E402,F401
from app.api import figurino_write as _figurino_write  # noqa: E402,F401
from app.api import financeiro_read as _financeiro_read  # noqa: E402,F401
from app.api import financeiro_write as _financeiro_write  # noqa: E402,F401
from app.api import catalogo_read as _catalogo_read  # noqa: E402,F401
from app.api import cadastro_write as _cadastro_write  # noqa: E402,F401
from app.api import formularios_write as _formularios_write  # noqa: E402,F401
from app.api import feedback_write as _feedback_write  # noqa: E402,F401
from app.api import clientes_read as _clientes_read  # noqa: E402,F401
from app.api import clientes_write as _clientes_write  # noqa: E402,F401
from app.api import rh_read as _rh_read  # noqa: E402,F401
from app.api import admin_users_read as _admin_users_read  # noqa: E402,F401
from app.api import admin_users_write as _admin_users_write  # noqa: E402,F401
from app.api import admin_config_read as _admin_config_read  # noqa: E402,F401
from app.api import admin_config_write as _admin_config_write  # noqa: E402,F401
from app.api import admin_catalogo_read as _admin_catalogo_read  # noqa: E402,F401
from app.api import admin_catalogo_write as _admin_catalogo_write  # noqa: E402,F401
from app.api import revisao_read as _revisao_read  # noqa: E402,F401
from app.api import revisao_write as _revisao_write  # noqa: E402,F401
