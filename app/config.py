import os
import secrets

_WEAK_SECRET = "dev-secret-key"

# Endereço único da plataforma. Com o React consolidado como interface primária, `app.*` é o
# serviço Node (`frontend/server.js`) que serve os três bundles e faz proxy reverso de `/api`,
# `/uploads`, `/catalogo/midia`, `/portal/photo` e `/figurinos/<id>/print` para este Flask —
# não existe mais um segundo endereço "do backend" para o usuário final.
PLATFORM_BASE_URL = "https://app.mantoproducoes.com.br"


def _db_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///manto.db")
    # Railway fornece postgres:// mas SQLAlchemy 2.x exige postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def _suppress_mail() -> bool:
    """Decide se este processo está proibido de enviar e-mail de verdade.

    Existe porque a única trava anterior era a `SiteSetting.email_notifications_enabled` — que
    vive **no banco**. Como a cópia local (`manto_local`) é um espelho fiel da produção, essa
    flag chega ligada, e qualquer processo de desenvolvimento apontado para o espelho consegue
    disparar e-mail para o endereço real dos artistas. Não é hipotético: uma reconciliação de
    casting rodando local chegou a enviar "sua participação foi cancelada".

    Regra: ambiente local (banco em localhost) não envia, a menos que alguém peça explicitamente
    com ``MAIL_ALLOW_LOCAL_SEND=true``. ``MAIL_SUPPRESS_SEND=true`` cala o envio em qualquer
    ambiente, útil para staging e para rodar scripts de verificação com segurança.
    """
    if os.getenv("MAIL_SUPPRESS_SEND", "").lower() == "true":
        return True
    if os.getenv("MAIL_ALLOW_LOCAL_SEND", "").lower() == "true":
        return False
    db_url = _db_url()
    return "localhost" in db_url or "127.0.0.1" in db_url or db_url.startswith("sqlite")


def _suppress_calendar_invites() -> bool:
    """Decide se este processo está proibido de escrever compromissos no Google Agenda real.

    Mesma armadilha do e-mail (`_suppress_mail`), por um caminho diferente: o token do Google
    também vive **no banco** (``SiteSetting.google_token``) e o calendário de destino é fixo
    (``eventos@mantoproducoes.com.br``). Um processo de desenvolvimento apontado para a cópia
    local herda as duas coisas e cria compromisso de verdade na agenda da empresa — com convite
    de verdade para o e-mail pessoal de quem for designado.

    Não é hipotético: aconteceu ao verificar a feature 225 na tela, e um convite chegou à
    responsável real antes de ser cancelado.

    Vale só para os compromissos internos criados pela plataforma (prazo de figurino). A
    sincronização dos eventos de show não passa por aqui — ela precisa continuar funcionando
    localmente, e não convida ninguém.
    """
    if os.getenv("CALENDAR_SUPPRESS_INVITES", "").lower() == "true":
        return True
    if os.getenv("CALENDAR_ALLOW_LOCAL_INVITES", "").lower() == "true":
        return False
    db_url = _db_url()
    return "localhost" in db_url or "127.0.0.1" in db_url or db_url.startswith("sqlite")


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
            with open(key_path, encoding="utf-8") as fh:
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

    # Trava de ambiente: impede que um processo local/de teste apontado para o espelho da
    # produção envie e-mail real para artista e cliente. Ver `_suppress_mail`.
    MAIL_SUPPRESS_SEND = _suppress_mail()

    # A mesma trava, para o Google Agenda: o token também vem do banco espelhado e o calendário
    # é fixo, então um processo local cria compromisso — e convite — de verdade. Ver
    # `_suppress_calendar_invites` (feature 225).
    CALENDAR_SUPPRESS_INVITES = _suppress_calendar_invites()

    # Varredura das devoluções de email (feature 219). Lê a MESMA conta que envia, por IMAP e em
    # modo somente leitura, com a App Password já configurada acima — sem credencial nova. Só
    # roda em produção por padrão: um processo local apontado para o espelho leria a caixa real.
    EMAIL_BOUNCE_SWEEP_ENABLED = os.getenv(
        "EMAIL_BOUNCE_SWEEP_ENABLED",
        "false" if _suppress_mail() else "true",
    ).lower() == "true"
    EMAIL_BOUNCE_SWEEP_INTERVAL = int(os.getenv("EMAIL_BOUNCE_SWEEP_INTERVAL", "1800"))
    # Janela de busca. Reprocessar é inofensivo (`message_id` é único), então a janela pode ser
    # larga o bastante para o passivo entrar na primeira execução.
    EMAIL_BOUNCE_LOOKBACK_DAYS = int(os.getenv("EMAIL_BOUNCE_LOOKBACK_DAYS", "90"))

    # Cobrança automática de confirmação de convite (feature 231). Mesma guarda do bounce: fica
    # DESLIGADA quando o ambiente já suprime e-mail (banco local), senão um processo apontado para
    # o espelho cobraria artista de verdade por evento que já aconteceu. A regra de quem recebe e
    # quando está em `app/calendar/invite_reminders.py`.
    INVITE_REMINDERS_ENABLED = os.getenv(
        "INVITE_REMINDERS_ENABLED",
        "false" if _suppress_mail() else "true",
    ).lower() == "true"
    INVITE_REMINDERS_INTERVAL = int(os.getenv("INVITE_REMINDERS_INTERVAL", "3600"))

    # URL base do portal (para links nos emails)
    PORTAL_URL = os.getenv("PORTAL_URL", "")

    # URL base pública (feature 205) — usada para montar o `redirect_url` do checkout, o endereço
    # do webhook que a InfinitePay chama e o destino do 301 da raiz do Flask. Precisa ser
    # alcançável pela internet: sem ela, a operadora não tem para onde devolver a família nem
    # para onde avisar o pagamento. Passou a apontar fixo para `PLATFORM_BASE_URL` (antes o
    # default era vazio, o que gerava URL quebrada em qualquer ambiente sem o env definido);
    # continua sobrescritível por `PUBLIC_BASE_URL` para dev/staging (ex.: túnel ngrok).
    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL") or PLATFORM_BASE_URL

    # Intervalo (segundos) da varredura que expira as reservas virtuais (feature 205, FR-057).
    VIRTUAL_SWEEP_INTERVAL = int(os.getenv("VIRTUAL_SWEEP_INTERVAL", "60"))

    # Token do agente auditor financeiro (feature 221). Sem valor configurado, os endpoints
    # `/api/audit-agent/*` respondem 404 para tudo — mesmo racional do webhook da InfinitePay.
    AUDIT_AGENT_TOKEN = os.getenv("AUDIT_AGENT_TOKEN", "")
    # Agente de marketing (feature 256): mesmo molde — sem o env, os endpoints
    # `/api/marketing-agent/*` respondem 404 (interruptor geral).
    MARKETING_AGENT_TOKEN = os.getenv("MARKETING_AGENT_TOKEN", "")

    # Pasta dos vídeos gravados (feature 205, FR-038e). **Fora** de `UPLOAD_FOLDER` de propósito:
    # `/uploads/<path>` é uma rota servida (ainda que com login de staff) e, com `USE_S3=true`,
    # `save_file` devolveria uma URL de bucket público. Um vídeo em que o nome da criança é dito em
    # voz alta não pode depender de o endereço não vazar — ele só sai pelo endpoint que valida.
    VIRTUAL_VIDEO_FOLDER = os.getenv("VIRTUAL_VIDEO_FOLDER", "")

    # Pasta das entregas de mídia das tags NFC (feature 261) — mesmo motivo do
    # `VIRTUAL_VIDEO_FOLDER` da 205: **fora** de `UPLOAD_FOLDER` de propósito. `/uploads/<path>`
    # exige login (`@login_required`) e a página `/nfc/<code>` é pública, sem sessão — o arquivo só
    # pode sair pelo endpoint que revalida tag e entrega ativas a cada requisição.
    NFC_MEDIA_FOLDER = os.getenv("NFC_MEDIA_FOLDER", "")

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

    # Domínio do cookie de sessão (feature 144). Para a SPA React em outro subdomínio
    # (ex.: beta.mantoproducoes.com.br) autenticar contra a API (app.mantoproducoes.com.br),
    # o cookie precisa valer para todo o domínio registrável — defina o env
    # SESSION_COOKIE_DOMAIN=".mantoproducoes.com.br". Como app.* e beta.* são o MESMO site
    # (mesmo eTLD+1), SameSite="Lax" já deixa o cookie ser enviado no fetch entre eles — NÃO
    # é preciso SameSite="None". Ausente (ex.: dev/localhost) = cookie host-only, como hoje.
    # ATENÇÃO: definir isto amplia o alcance do cookie de sessão do ERP atual para todos os
    # subdomínios — só use subdomínios confiáveis sob este domínio.
    SESSION_COOKIE_DOMAIN = os.getenv("SESSION_COOKIE_DOMAIN") or None

    # PostgreSQL — obrigatório em produção
    # DATABASE_URL deve ser definida no .env
    # pool_size/max_overflow explícitos: sem eles valem os defaults do SQLAlchemy (5 + 10), que
    # ficam APERTADOS depois que o gunicorn passou a 12 threads por worker (railway.json). Cada
    # worker consome conexões por 12 threads de requisição MAIS as 6 threads de background
    # (`_start_*` no fim de create_app), ou seja até 18 usuários simultâneos do pool. 10 + 10 = 20
    # cobre isso com folga; × 3 workers = 60 conexões no pior caso. Um download de mídia segura a
    # conexão durante TODA a transferência (a sessão só é devolvida no teardown, que roda depois
    # do último byte) — por isso o pool tem que acompanhar as threads.
    # `scripts/db/validar_startcommand.py` confere esta coerência automaticamente.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 10,
        "max_overflow": 10,
    }


_env = os.getenv("FLASK_ENV", "development")
Config = ProductionConfig if _env == "production" else DevelopmentConfig
