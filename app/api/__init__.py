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
