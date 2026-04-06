import os
from dotenv import load_dotenv
load_dotenv()  # carrega .env se existir

# Permite OAuth sem HTTPS apenas em desenvolvimento
if os.getenv("FLASK_ENV", "development") != "production":
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

from app import create_app

app = create_app()

# Em produção atrás do Nginx, o ProxyFix garante que Flask gere
# URLs corretas com https:// e o IP real do cliente.
if os.getenv("FLASK_ENV") == "production":
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

if __name__ == "__main__":
    debug = os.getenv("FLASK_ENV", "development") != "production"
    app.run(debug=debug)
