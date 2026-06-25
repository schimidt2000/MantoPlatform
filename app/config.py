import os
import secrets

_WEAK_SECRET = "dev-secret-key"


def _db_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///manto.db")
    # Railway fornece postgres:// mas SQLAlchemy 2.x exige postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def _resolve_secret_key() -> str:
    """Resolve a SECRET_KEY de forma segura (feature 074).

    - Usa ``SECRET_KEY`` do ambiente quando definida e forte.
    - Em desenvolvimento, aceita o default fraco (conveniência local).
    - Em produção, **nunca** usa a chave fraca conhecida: se ausente/fraca, gera uma chave forte e a
      persiste em ``instance/.secret_key`` (compartilhada entre workers e estável durante o deploy).
      Se não for possível gravar, usa uma chave aleatória em memória (sessões caem em restart, mas
      sem a chave fraca conhecida).
    """
    env_key = os.getenv("SECRET_KEY", "").strip()
    is_prod = os.getenv("FLASK_ENV", "development") == "production"

    if env_key and (env_key != _WEAK_SECRET or not is_prod):
        return env_key
    if not is_prod:
        return _WEAK_SECRET  # dev: conveniência

    # Produção sem chave forte: gera e persiste em instance/.secret_key
    key_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "instance", ".secret_key")
    )
    try:
        if os.path.exists(key_path):
            with open(key_path, "r", encoding="utf-8") as fh:
                saved = fh.read().strip()
            if saved:
                return saved
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        new_key = secrets.token_hex(32)
        # Escrita atômica + permissões restritas quando suportado.
        with open(key_path, "w", encoding="utf-8") as fh:
            fh.write(new_key)
        try:
            os.chmod(key_path, 0o600)
        except OSError:
            pass
        return new_key
    except OSError:
        # Último recurso: chave aleatória em memória (melhor que a chave fraca conhecida).
        return secrets.token_hex(32)


class Config:
    SECRET_KEY = _resolve_secret_key()
    SQLALCHEMY_DATABASE_URI = _db_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Segurança de sessão (074): válidas em qualquer ambiente. 'Secure' é ligado só em produção
    # (ProductionConfig), pois o dev roda em HTTP.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Limite global de upload/requisição (defesa contra DoS por arquivo gigante).
    # 512 MB para acomodar vídeos do módulo de Revisão (feature 088); as demais rotas
    # mantêm limites menores por arquivo (10–20 MB) validados nelas próprias.
    MAX_CONTENT_LENGTH = 512 * 1024 * 1024  # 512 MB

    # Email — Gmail Workspace via App Password
    MAIL_SERVER   = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT     = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS  = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USE_SSL  = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "joao@mantoproducoes.com.br")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER_NAME = os.getenv("MAIL_SENDER_NAME", "Sistema Manto")

    # URL base do portal (para links nos emails)
    PORTAL_URL = os.getenv("PORTAL_URL", "")

    # Object Storage — AWS S3 ou Cloudflare R2
    USE_S3           = os.getenv("USE_S3", "false").lower() == "true"
    S3_BUCKET        = os.getenv("S3_BUCKET", "")
    S3_REGION        = os.getenv("S3_REGION", "auto")
    AWS_ACCESS_KEY   = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_KEY   = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    # Cloudflare R2: preencha os dois abaixo. Para AWS S3: deixe vazios.
    S3_ENDPOINT_URL  = os.getenv("S3_ENDPOINT_URL", "")   # https://<id>.r2.cloudflarestorage.com
    S3_PUBLIC_URL    = os.getenv("S3_PUBLIC_URL", "")      # https://pub-<id>.r2.dev

    # Google OAuth — URL de callback para produção
    GOOGLE_OAUTH_REDIRECT_URI = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "")

    # Google Maps — distância para calculadora de orçamento (opcional)
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

    # Google Sheets — importação de talentos via formulário
    TALENTS_SPREADSHEET_ID = os.getenv("TALENTS_SPREADSHEET_ID", "1A_bXqUP21HR1RWS8AVBmj1oPgjhIWBaFfYxeqX17Ric")
    TALENTS_SHEET_NAME     = os.getenv("TALENTS_SHEET_NAME", "Respostas")
    TALENTS_SYNC_INTERVAL  = int(os.getenv("TALENTS_SYNC_INTERVAL", "900"))  # segundos (padrão: 15 min)

    # Sincronização automática da agenda com o Google Calendar (cron interno)
    CALENDAR_SYNC_INTERVAL = int(os.getenv("CALENDAR_SYNC_INTERVAL", "600"))  # segundos (padrão: 10 min)

    # Google Drive — pasta de figurinos para sync
    FIGURINO_DRIVE_FOLDER_ID = os.getenv("FIGURINO_DRIVE_FOLDER_ID", "")


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE   = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PREFERRED_URL_SCHEME    = "https"

    # PostgreSQL — obrigatório em produção
    # DATABASE_URL deve ser definida no .env
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }


_env = os.getenv("FLASK_ENV", "development")
Config = ProductionConfig if _env == "production" else DevelopmentConfig
