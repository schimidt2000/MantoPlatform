import os
from flask import (
    Flask,
    Response,
    abort,
    render_template,
    request,
    send_from_directory,
    session,
    redirect,
)
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_login import login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime
from .config import Config, PLATFORM_BASE_URL  # se seu config.py está na raiz
from .constants import RoleName

from .email_service import mail

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = None  # suprime mensagem automática de "faça login"
limiter = Limiter(key_func=get_remote_address, default_limits=[])


def _is_revendedor_only(user) -> bool:
    """True se o usuário tem APENAS o perfil Revendedor EducaManto (feature 078).

    Multi-perfil (revendedor + outro) NÃO é restrito — preserva os acessos dos demais perfis.
    Usa os papéis reais (não a impersonação), por ser controle de acesso.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    names = {r.name.upper() for r in user.roles}
    return names == {RoleName.REVENDEDOR_EDUCAMANTO}


# Páginas que o Revendedor EducaManto pode acessar (prefixos). O resto é redirecionado à agenda.
_REVENDEDOR_ALLOWED = ("/agenda", "/events/", "/educamanto", "/auth", "/uploads", "/static", "/health")

# Mesma permissão das páginas acima, traduzida para a API que o React consome. SEM isto, todas as
# chamadas `/api/*` do revendedor caíam no `redirect("/agenda")` — inclusive `/api/auth/me` —, e
# como o front recebe o HTML da SPA com status 200 no lugar do JSON, o app inteiro morria em
# silêncio para esse perfil (a calculadora EducaManto entre outras coisas). Não amplia acesso:
# é o espelho exato do que ele já podia abrir quando as telas eram Jinja.
_REVENDEDOR_ALLOWED_API = ("/api/auth", "/api/agenda", "/api/events", "/api/educamanto")


# ── Autorização por subpasta de `/uploads` ────────────────────────────────────
# `/uploads/<path>` servia a árvore INTEIRA de uploads só com `@login_required`: contrato,
# comprovante de pagamento, nota fiscal e documento de identidade de talento ficavam ao alcance
# de QUALQUER papel — inclusive REVENDEDOR_EDUCAMANTO (que tem "/uploads" na allowlist acima) e
# MARKETING. A única barreira era o nome uuid4 do arquivo, e esse nome vem de bandeja no JSON
# das telas. Agora o PRIMEIRO SEGMENTO do caminho decide qual papel é exigido.
#
# O papel de cada subpasta é o mesmo da tela que exibe o arquivo, para não trancar nada que
# já funciona: contrato/comprovante/nota fiscal saem no bloco `show_comercial` de
# `app/api/agenda_read.py::_role_flags` (Comercial/Financeiro/Superadmin) e o documento do
# talento só aparece na ficha, sob `_can_edit_talent` (Casting/Superadmin).
UPLOADS_ROLE_BY_SUBFOLDER = {
    "contracts":   (RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN),
    "payments":    (RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN),
    "invoices":    (RoleName.COMERCIAL, RoleName.FINANCEIRO, RoleName.SUPERADMIN),
    "talent_docs": (RoleName.CASTING, RoleName.SUPERADMIN),
}

# Comprovante de gasto extra: papel NÃO basta como regra. Qualquer colaborador registra um gasto
# e o próprio `GET /api/gastos` devolve `receipt_url` do gasto dele — exigir FINANCEIRO aqui
# quebraria a tela de quem enviou. Por isso esta subpasta tem checagem de DONO no banco.
UPLOADS_OWNER_CHECKED_SUBFOLDER = "expenses"

# Demais subpastas (talent_photos, figurino_photos, figurino_thumbs, catalog_photos,
# acervo_3d_photos, acervo_3d_files, event_obs, ensaio_materials, review, logos) seguem como
# antes — mídia operacional, liberada a qualquer usuário autenticado.


def _has_any_role(user, roles: tuple[str, ...]) -> bool:
    """True se `user` tem pelo menos um dos papéis informados.

    Args:
        user: Usuário autenticado da sessão.
        roles: Nomes de papel já em MAIÚSCULAS (constantes de `RoleName`).
    """
    return any(r.name.upper() in roles for r in user.roles)


def _can_read_expense_receipt(user, relative_path: str) -> bool:
    """True se `user` pode abrir o comprovante de gasto em `relative_path`.

    Passa FINANCEIRO/SUPERADMIN (que veem todos os gastos) ou o autor do gasto. `receipt_path`
    é gravado exatamente como ``expenses/<arquivo>`` (`gastos_ops.save_receipt`), então a
    comparação é direta — sem esse casamento, nenhum arquivo é servido.
    """
    from app.gastos.gastos_ops import is_financeiro
    from app.models import SpecialExpense

    if is_financeiro(user):
        return True
    expense = SpecialExpense.query.filter_by(receipt_path=relative_path).first()
    return expense is not None and expense.created_by_id == user.id


def _can_read_upload(user, filename: str) -> bool:
    """Decide se `user` pode baixar `filename` da árvore de uploads.

    Args:
        user: Usuário autenticado da sessão.
        filename: Caminho pedido, relativo à raiz de `UPLOAD_FOLDER`.

    Returns:
        True quando a subpasta é mídia operacional (regra antiga: só login), quando o papel do
        usuário cobre a subpasta sensível, ou quando ele é o dono do comprovante de gasto.
    """
    relative_path = filename.replace("\\", "/").lstrip("/")
    subfolder = relative_path.split("/", 1)[0].lower()

    required = UPLOADS_ROLE_BY_SUBFOLDER.get(subfolder)
    if required is not None:
        return _has_any_role(user, required)
    if subfolder == UPLOADS_OWNER_CHECKED_SUBFOLDER:
        return _can_read_expense_receipt(user, relative_path)
    return True


def _safe_next(value, default="/"):
    """Retorna ``value`` apenas se for um destino interno seguro; senão, ``default`` (feature 074).

    Bloqueia open redirect: aceita caminho relativo interno (``/algo``) ou URL absoluta do **mesmo
    host**; rejeita esquemas/hosts externos (``http://evil``, ``//evil``).
    """
    from urllib.parse import urlparse
    if not value:
        return default
    parsed = urlparse(value)
    if not parsed.scheme and not parsed.netloc:
        # caminho relativo: precisa começar com '/' e não ser protocol-relative ('//')
        if value.startswith("/") and not value.startswith("//"):
            return value
        return default
    # URL absoluta: só aceita o mesmo host da requisição atual
    try:
        if parsed.netloc == request.host:
            return (parsed.path or "/") + (("?" + parsed.query) if parsed.query else "")
    except RuntimeError:
        pass  # fora de contexto de requisição
    return default

def _start_talent_sync(app):
    """Inicia thread de background que importa novos talentos da planilha periodicamente."""
    import threading
    import os as _os

    # Em modo debug o Werkzeug roda 2 processos: o reloader (pai) e o worker (filho).
    # WERKZEUG_RUN_MAIN="true" só existe no filho. Iniciamos a thread apenas lá.
    # Em produção (gunicorn) a variável nunca é definida, então passa direto.
    flask_env = _os.environ.get("FLASK_ENV", "")
    if flask_env == "development" and _os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    credentials_path = _os.path.abspath(
        _os.path.join("instance", "credentials", "sheets_service_account.json")
    )
    if not _os.path.exists(credentials_path):
        app.logger.info("[talent-sync] credenciais não encontradas — sync desativado")
        return

    SPREADSHEET_ID = app.config.get("TALENTS_SPREADSHEET_ID", "")
    SHEET_NAME     = app.config.get("TALENTS_SHEET_NAME", "Respostas")
    INTERVAL       = app.config.get("TALENTS_SYNC_INTERVAL", 900)

    if not SPREADSHEET_ID:
        app.logger.warning("[talent-sync] TALENTS_SPREADSHEET_ID não configurado — sync desativado")
        return

    def _sync_loop():
        import time
        from datetime import datetime as _dt
        time.sleep(15)  # aguarda o app estar pronto
        while True:
            try:
                from app.talents.importer import import_new_talents_from_sheet
                with app.app_context():
                    result = import_new_talents_from_sheet(
                        spreadsheet_id=SPREADSHEET_ID,
                        sheet_name=SHEET_NAME,
                        credentials_path=credentials_path,
                    )
                    imported = result.get("imported", 0)
                    # Registra o resultado no banco para exibir na UI
                    from app.models import ImportState
                    state = ImportState.query.filter_by(key="talents_form").first()
                    if state:
                        state.last_checked_at = _dt.utcnow()
                        state.last_import_count = imported
                        db.session.commit()
                    if imported > 0:
                        app.logger.info(f"[talent-sync] {imported} novo(s) talento(s) importado(s)")
                    else:
                        app.logger.debug("[talent-sync] nenhum talento novo")
            except Exception as exc:
                app.logger.warning(f"[talent-sync] erro: {exc}")
            time.sleep(INTERVAL)

    t = threading.Thread(target=_sync_loop, daemon=True, name="talent-sync")
    t.start()
    app.logger.info(f"[talent-sync] thread iniciada (intervalo: {INTERVAL}s)")


def _start_calendar_sync(app):
    """Inicia thread de background que sincroniza a agenda com o Google Calendar.

    Substitui a dependência de um serviço Cron externo: roda dentro do próprio app,
    em intervalos regulares, com a mesma lógica do botão "Sincronizar agora".
    Um claim atômico no banco garante execução única entre os workers do gunicorn.
    """
    import threading
    import os as _os

    # Mesma guarda de dev do talent-sync: em modo debug, só roda no processo filho.
    flask_env = _os.environ.get("FLASK_ENV", "")
    if flask_env == "development" and _os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    INTERVAL = app.config.get("CALENDAR_SYNC_INTERVAL", 600)

    def _sync_loop():
        import time
        time.sleep(15)  # aguarda o app estar pronto
        from app.calendar.sync import run_calendar_sync, _claim_auto_sync
        while True:
            try:
                with app.app_context():
                    if _claim_auto_sync(INTERVAL):
                        result = run_calendar_sync()
                        if result["errors"]:
                            app.logger.warning(
                                f"[calendar-sync] ciclo com {result['errors']} erro(s)"
                            )
                        else:
                            app.logger.debug(
                                f"[calendar-sync] {result['months']} mês(es) sincronizado(s)"
                            )
            except Exception as exc:  # noqa: BLE001 — nunca deixar a thread morrer
                app.logger.warning(f"[calendar-sync] erro: {exc}")
            time.sleep(INTERVAL)

    t = threading.Thread(target=_sync_loop, daemon=True, name="calendar-sync")
    t.start()
    app.logger.info(f"[calendar-sync] thread iniciada (intervalo: {INTERVAL}s)")


def _start_review_cleanup(app):
    """Thread diária que remove os arquivos de revisão vencidos (feature 090).

    Materiais de revisão expiram em 7 dias; esta rotina apaga só o arquivo do armazenamento
    (registro e comentários permanecem). Idempotente — rodar em vários workers é inofensivo.
    """
    import os as _os
    import threading

    flask_env = _os.environ.get("FLASK_ENV", "")
    if flask_env == "development" and _os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    INTERVAL = app.config.get("REVIEW_CLEANUP_INTERVAL", 24 * 3600)

    def _loop():
        import time
        time.sleep(30)  # aguarda o app estar pronto
        from app.revisao.cleanup import cleanup_expired_review_files
        while True:
            try:
                with app.app_context():
                    removed = cleanup_expired_review_files()
                    if removed:
                        app.logger.info(f"[review-cleanup] {removed} arquivo(s) de revisão removido(s)")
            except Exception as exc:  # noqa: BLE001 — nunca deixar a thread morrer
                app.logger.warning(f"[review-cleanup] erro: {exc}")
            time.sleep(INTERVAL)

    t = threading.Thread(target=_loop, daemon=True, name="review-cleanup")
    t.start()
    app.logger.info(f"[review-cleanup] thread iniciada (intervalo: {INTERVAL}s)")


def _start_virtual_sweep(app):
    """Thread das rotinas periódicas da Loja de Interações Virtuais (feature 205).

    Mesmo padrão de `_start_calendar_sync`: thread daemon, intervalo configurável, `app_context`
    dentro do laço e `except Exception` que **nunca** deixa a thread morrer (FR-057b).

    Roda as **três** rotinas que o FR-057 nomeia — expiração de reservas, retentativa de sala e
    alerta de prazo de vídeo —, todas dentro de `virtuais_ops.ciclo_de_varredura()`. Uma thread só
    porque as três compartilham o mesmo lock de execução única.

    O claim atômico (`virtuais_ops.claim_sweep`) é obrigatório aqui, não opcional: o Railway roda
    vários workers gunicorn, e dois processos expirando a mesma reserva ao mesmo tempo é a corrida
    que o soft lock existe para evitar (FR-057a).
    """
    import os as _os
    import threading

    flask_env = _os.environ.get("FLASK_ENV", "")
    if flask_env == "development" and _os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    INTERVAL = app.config.get("VIRTUAL_SWEEP_INTERVAL", 60)

    def _loop():
        import time
        time.sleep(20)  # aguarda o app estar pronto
        from app.marketing.virtuais_ops import ciclo_de_varredura, claim_sweep
        while True:
            try:
                with app.app_context():
                    if claim_sweep(INTERVAL):
                        resumo = ciclo_de_varredura()
                        reservas = resumo.get("reservas") or {}
                        salas = resumo.get("salas") or {}
                        prazos = resumo.get("prazos") or 0
                        if any(reservas.values()) or any(salas.values()) or prazos:
                            app.logger.info(
                                "[virtual-sweep] reservas=%s salas=%s prazos_alertados=%s",
                                reservas, salas, prazos,
                            )
            except Exception as exc:  # noqa: BLE001 — nunca deixar a thread morrer
                app.logger.warning(f"[virtual-sweep] erro: {exc}")
            time.sleep(INTERVAL)

    t = threading.Thread(target=_loop, daemon=True, name="virtual-sweep")
    t.start()
    app.logger.info(f"[virtual-sweep] thread iniciada (intervalo: {INTERVAL}s)")


def create_app():
    from urllib.parse import quote as _url_quote
    app = Flask(__name__)
    app.config.from_object(Config)
    app.jinja_env.filters['urlencode'] = _url_quote

    from app.money import format_brl
    app.jinja_env.filters['brl'] = format_brl

    # Absolute paths for uploads (avoids CWD resolution issues)
    _instance = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'instance'))
    app.config.setdefault("UPLOAD_FOLDER",          os.path.join(_instance, "uploads"))
    app.config.setdefault("UPLOAD_CONTRACTS",        os.path.join(_instance, "uploads", "contracts"))
    app.config.setdefault("UPLOAD_PAYMENTS",         os.path.join(_instance, "uploads", "payments"))
    app.config.setdefault("UPLOAD_INVOICES",         os.path.join(_instance, "uploads", "invoices"))
    app.config.setdefault("UPLOAD_FIGURINO_THUMBS",  os.path.join(_instance, "uploads", "figurino_thumbs"))
    app.config.setdefault("UPLOAD_FIGURINO_PHOTOS",  os.path.join(_instance, "uploads", "figurino_photos"))
    app.config.setdefault("UPLOAD_EVENT_OBS",         os.path.join(_instance, "uploads", "event_obs"))
    app.config.setdefault("UPLOAD_EXPENSES",          os.path.join(_instance, "uploads", "expenses"))
    # Vídeos da Loja de Interações Virtuais (feature 205): irmão de `uploads`, nunca dentro dele —
    # a rota `/uploads/<path>` serve qualquer coisa que caia lá, e o vídeo só pode sair pelo
    # endpoint que valida o acesso a cada requisição (FR-038e).
    if not app.config.get("VIRTUAL_VIDEO_FOLDER"):
        app.config["VIRTUAL_VIDEO_FOLDER"] = os.path.join(_instance, "virtual_videos")
    os.makedirs(app.config["VIRTUAL_VIDEO_FOLDER"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_CONTRACTS"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_PAYMENTS"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_INVOICES"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_FIGURINO_THUMBS"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_FIGURINO_PHOTOS"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_EVENT_OBS"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_EXPENSES"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)

    # ── CORS para a SPA React (feature 144) ───────────────────────────────────
    # Só habilita quando há origens configuradas (produção: domínios dos bundles React).
    # Em desenvolvimento o proxy do Vite torna as chamadas same-origin — CORS dispensável.
    # O import fica DENTRO do if e protegido de propósito: enquanto a SPA não estiver no ar,
    # esta feature é inerte, e ela nunca pode impedir o ERP inteiro de subir por causa de uma
    # dependência ausente (o start do Railway repete só 3 vezes antes de desistir).
    _cors_origins = [
        o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()
    ]
    if _cors_origins:
        try:
            from flask_cors import CORS

            CORS(app, resources={r"/api/*": {"origins": _cors_origins}}, supports_credentials=True)
        except Exception:
            app.logger.exception(
                "[cors] flask-cors indisponível — API seguirá sem CORS (SPA cross-origin falhará)"
            )

    # ── Segurança: cabeçalhos em todas as respostas (feature 074) ──────────────
    @app.after_request
    def _security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        # Sistema interno — nenhuma página deve ser indexada por buscadores (feature 127).
        resp.headers.setdefault("X-Robots-Tag", "noindex, nofollow, noarchive")
        # CSP mínima: protege clickjacking, base-tag e hijack de <form> sem restringir
        # script/style/img/font/frame-src (não quebra inline nem integrações externas).
        resp.headers.setdefault(
            "Content-Security-Policy",
            "object-src 'none'; base-uri 'self'; frame-ancestors 'self'; form-action 'self'",
        )
        # HSTS só sob HTTPS (atrás do proxy do Railway, confere X-Forwarded-Proto).
        if request.is_secure or request.headers.get("X-Forwarded-Proto") == "https":
            resp.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return resp

    # ── Acesso restrito do Revendedor EducaManto (feature 078) ────────────────
    @app.before_request
    def _revendedor_guard():
        if not _is_revendedor_only(current_user):
            return None
        path = request.path

        # A API responde JSON, nunca redirect: um 302 para uma página HTML chega no `apiFetch`
        # como 200 + HTML e explode no `JSON.parse`, virando "não funciona" sem erro nenhum na
        # tela. Fora do que o perfil pode ver, o certo é um 403 que o front sabe ler.
        if path.startswith("/api/"):
            if any(path == p or path.startswith(p + "/") for p in _REVENDEDOR_ALLOWED_API):
                return None
            from app.api_utils import json_error
            return json_error("Sem permissão", 403)

        if path == "/":
            return redirect("/agenda")
        if any(path == p or path.startswith(p) for p in _REVENDEDOR_ALLOWED):
            return None
        return redirect("/agenda")

    @app.context_processor
    def inject_revendedor_flag():
        return {"is_revendedor_only": _is_revendedor_only(current_user)}

    @app.context_processor
    def inject_settings():
        from app.models import SiteSetting
        return {"settings": SiteSetting.query.get(1)}

    @app.context_processor
    def inject_educamanto_responsavel_flag():
        # Feature 109: o responsável EducaManto vê os links de Pipeline/Comissões no menu.
        def _flag() -> bool:
            if not current_user.is_authenticated:
                return False
            from app.models import SiteSetting
            s = SiteSetting.query.get(1)
            return bool(s and s.educamanto_seller_id == current_user.id)
        return {"is_educamanto_responsavel": _flag()}

    @app.context_processor
    def inject_roles():
        def is_real_superadmin() -> bool:
            return current_user.is_authenticated and any(
                r.name == RoleName.SUPERADMIN for r in current_user.roles
            )

        def eff_has_role(*names) -> bool:
            if not current_user.is_authenticated:
                return False
            impersonate = session.get("impersonate_role")
            if impersonate and is_real_superadmin():
                return any(n.upper() == impersonate.upper() for n in names)
            return any(
                r.name.upper() in [n.upper() for n in names]
                for r in current_user.roles
            )

        view_as_role = (
            session.get("impersonate_role")
            if current_user.is_authenticated and is_real_superadmin()
            else None
        )

        return dict(
            eff_has_role=eff_has_role,
            is_real_superadmin=is_real_superadmin,
            view_as_role=view_as_role,
        )

    PORTAL_HOSTS = {"portal.mantoproducoes.com.br"}

    @app.before_request
    def portal_domain_routing():
        host = request.host.split(":")[0]
        if host in PORTAL_HOSTS:
            if not request.path.startswith(("/portal", "/cadastro", "/f/", "/static", "/uploads")):
                return redirect("/portal/")

    # ✅ Importa blueprints AQUI (depois do db existir)
    from .auth.routes import auth_bp
    from .rh.routes import rh_bp
    from .admin.routes import admin_bp
    from .calendar.routes import calendar_bp
    from .talents.routes import talents_bp
    from .financeiro.routes import financeiro_bp
    from .figurino.routes import figurino_bp
    from .talent_portal.routes import portal_bp
    from .orcamento.routes import orcamento_bp
    from .educamanto.routes import educamanto_bp
    from .gastos.routes import gastos_bp
    from .cadastro.routes import cadastro_bp
    from .revisao.routes import revisao_bp
    from .clientes.routes import clientes_bp
    from .formularios.routes import formularios_bp
    from .feedback.routes import feedback_bp
    from .catalogo.routes import catalogo_bp
    from .api import api_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(rh_bp, url_prefix="/rh")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(calendar_bp)
    app.register_blueprint(talents_bp)
    app.register_blueprint(financeiro_bp)
    app.register_blueprint(figurino_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(orcamento_bp)
    app.register_blueprint(educamanto_bp)
    app.register_blueprint(gastos_bp)
    app.register_blueprint(cadastro_bp)
    app.register_blueprint(revisao_bp)
    app.register_blueprint(clientes_bp)
    app.register_blueprint(formularios_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(catalogo_bp)
    app.register_blueprint(api_bp)

    def _wa_link(code: int) -> str:
        from zoneinfo import ZoneInfo
        import urllib.parse
        now = datetime.now(tz=ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")
        url = request.url
        msg = (
            f"🚨 *Erro na Manto Platform*\n"
            f"• Código: {code}\n"
            f"• Página: {url}\n"
            f"• Horário: {now} (SP)"
        )
        number = os.getenv("SUPPORT_WHATSAPP", "")
        return f"https://wa.me/{number}?text={urllib.parse.quote(msg)}" if number else ""

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html", wa_link=_wa_link(404)), 404

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f"500 error: {e}")
        return render_template("500.html", wa_link=_wa_link(500)), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html", wa_link=_wa_link(403)), 403

    @app.route("/robots.txt")
    def robots_txt():
        """Nega rastreamento de tudo — sistema interno, não deve ser indexado (feature 127)."""
        return Response("User-agent: *\nDisallow: /\n", mimetype="text/plain")

    @app.route("/")
    def home():
        """Raiz do Flask: 301 para a plataforma React.

        O dashboard Jinja que vivia aqui foi aposentado — a interface primária é o bundle
        `apps/internal` servido por `frontend/server.js` em ``PLATFORM_BASE_URL``, que já faz
        proxy reverso de `/api`, `/uploads`, `/catalogo/midia`, `/portal/photo` e
        `/figurinos/<id>/print` de volta para este Flask. Esta rota existe só para capturar
        acesso residual direto ao serviço do backend (link antigo, favorito, domínio anterior)
        e devolvê-lo à URL única, de forma permanente para o browser memorizar.

        Não há laço de redirecionamento: em ``PLATFORM_BASE_URL`` quem responde `/` é o serviço
        Node, que nunca repassa a raiz para cá. Em desenvolvimento este 301 também joga para
        produção — use `http://localhost:5173` (Vite) como ponto de entrada local, não `/`.
        """
        return redirect(PLATFORM_BASE_URL, code=301)

    # ── Auto-import de talentos da planilha ────────────────────────
    _start_talent_sync(app)

    # ── Sincronização automática da agenda (cron interno) ──────────
    _start_calendar_sync(app)
    _start_review_cleanup(app)

    # ── Expiração das reservas da Loja de Interações Virtuais ──────
    _start_virtual_sweep(app)

    # ── Comandos CLI de manutenção ─────────────────────────────────
    from app.cli import register_commands
    register_commands(app)

    # Import local: `app.storage` só depende do `current_app`, mas mantê-lo fora do topo do
    # pacote evita reintroduzir ciclo de import na inicialização.
    from app.storage import is_inline_safe

    @app.route("/uploads/<path:filename>")
    @login_required
    def uploaded_file(filename: str):
        """Serve um arquivo de `instance/uploads/` sem deixá-lo executar no origin da aplicação.

        `/uploads` é proxiado no MESMO domínio das SPAs (`frontend/server.js:BACKEND_PREFIXES`),
        então um arquivo de tipo perigoso (`.html`, `.svg`, `.xml`) devolvido inline rodaria
        JavaScript com a sessão de quem abre o link. Imagem, PDF, áudio e vídeo continuam inline
        (a interface os embute em `<img>`/`<video>`/visualizador de PDF); todo o resto vira
        download. O `nosniff` impede o browser de reinterpretar o tipo declarado.

        O acesso é despachado por subpasta (`_can_read_upload`): login continua sendo o piso,
        mas contrato, comprovante, nota fiscal e documento de talento exigem o papel da tela que
        os exibe. 404 em vez de 403 de propósito — não confirma a existência do arquivo a quem
        não pode vê-lo, já que o nome é o único segredo que resta.
        """
        if not _can_read_upload(current_user, filename):
            abort(404)
        inline = is_inline_safe(filename)
        resp = send_from_directory(
            app.config["UPLOAD_FOLDER"], filename, as_attachment=not inline
        )
        resp.headers["X-Content-Type-Options"] = "nosniff"
        if not inline:
            resp.headers["Content-Type"] = "application/octet-stream"
        return resp

    # ── Impersonação de role (somente SUPERADMIN) ──────────────────
    # Feature 173: lista promovida a app/constants.py (fonte única com a API).
    from app.constants import IMPERSONABLE_ROLES as _IMPERSONABLE_ROLES

    @app.route("/impersonate/<role_name>", methods=["POST"])
    @login_required
    def impersonate_role(role_name: str):
        if not any(r.name == RoleName.SUPERADMIN for r in current_user.roles):
            return "", 403
        if role_name.upper() not in _IMPERSONABLE_ROLES:
            return "", 400
        session["impersonate_role"] = role_name.upper()
        return redirect(_safe_next(request.referrer, "/"))

    @app.route("/impersonate/reset", methods=["POST"])
    @login_required
    def impersonate_reset():
        session.pop("impersonate_role", None)
        return redirect(_safe_next(request.referrer, "/"))

    @app.route("/health")
    def health():
        return "ok", 200

    return app
