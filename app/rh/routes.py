from flask import Blueprint, render_template
from flask_login import login_required, current_user
from functools import wraps
from app.constants import RoleName

rh_bp = Blueprint("rh", __name__)

def require_permission(code: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.has_permission(code):
                return {"ok": False, "error": "Sem permissão"}, 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def require_superadmin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not any(r.name == RoleName.SUPERADMIN for r in current_user.roles):
            return {"ok": False, "error": "Acesso apenas para SuperAdmin"}, 403
        return fn(*args, **kwargs)
    return wrapper

@rh_bp.route("/dashboard", methods=["GET"])
@login_required
@require_permission("rh.view")
def dashboard():
    return render_template(
        "rh_dashboard.html",
        can_manage_users=current_user.has_permission("user.manage")
    )
