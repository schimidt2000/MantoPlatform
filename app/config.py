import os


def _db_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///manto.db")
    # Railway fornece postgres:// mas SQLAlchemy 2.x exige postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = _db_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

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
    TALENTS_SPREADSHEET_ID = os.getenv("TALENTS_SPREADSHEET_ID", "")
    TALENTS_SHEET_NAME     = os.getenv("TALENTS_SHEET_NAME", "Respostas")

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
