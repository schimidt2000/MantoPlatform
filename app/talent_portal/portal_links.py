"""URLs absolutas do Portal do Artista que saem por e-mail.

Fonte única para montar link de e-mail do portal. Existe por um motivo de segurança: qualquer
`url_for(..., _external=True)` deriva o host de `request.host` — e o `Host` (ou o
`X-Forwarded-Host`, já que `run.py` aplica `ProxyFix(x_host=1)`) é escolhido por quem faz a
requisição. Como o serviço Flask é alcançável direto pela internet, um atacante que conheça CPF
e e-mail do talento dispara "esqueci minha senha" com `Host: evil.example` e o talento recebe um
e-mail legítimo da Manto com o token de redefinição apontando para o servidor do atacante.

Por isso a base vem SEMPRE da config, nunca do request.
"""

from __future__ import annotations

from urllib.parse import quote

from flask import current_app

#: Caminho da tela de redefinição no portal React (`PORTAL_URL`).
RESET_PATH = "/reset-password"

#: Caminho da rota Jinja legada, servida pelo próprio Flask — usado só no fallback.
LEGACY_RESET_PATH = "/portal/reset-password"

#: Tela do portal onde o artista reenvia foto e documento. É o destino do e-mail da feature 293:
#: sem ele o link cai na agenda, e a pessoa que veio consertar a foto não acha onde fazer isso.
FOTOS_PATH = "/fotos-documentos"


def portal_base_url() -> str:
    """Base absoluta do Portal do Artista, sem barra final.

    Returns:
        `PORTAL_URL` quando configurada; senão `PUBLIC_BASE_URL`, que tem valor fixo em
        `app/config.py` e também não depende do request.
    """
    base = (current_app.config.get("PORTAL_URL") or "").strip().rstrip("/")
    if base:
        return base
    return (current_app.config.get("PUBLIC_BASE_URL") or "").strip().rstrip("/")


def portal_reset_url(token: str, destino: str | None = None) -> str:
    """URL de redefinição de senha enviada por e-mail ao talento.

    Args:
        token: Token de redefinição já persistido no `Talent`.
        destino: Caminho interno do portal para onde levar depois que a senha for criada
            (ex.: `/fotos-documentos`). Só caminho relativo — a validação final é do lado do
            React, pela mesma regra do `_safe_next` do backend: começa com `/` e não com `//`.

    Returns:
        `{PORTAL_URL}/reset-password/{token}` quando o portal React está configurado; sem
        `PORTAL_URL`, cai na rota Jinja legada sobre `PUBLIC_BASE_URL` (que continua
        funcionando em ambiente onde o front novo ainda não foi publicado).
    """
    portal_url = (current_app.config.get("PORTAL_URL") or "").strip().rstrip("/")
    if not portal_url:
        # A rota Jinja legada não conhece `?destino=`; ignorá-lo aqui é melhor que gerar um link
        # com um parâmetro que ninguém lê.
        return f"{portal_base_url()}{LEGACY_RESET_PATH}/{token}"
    url = f"{portal_url}{RESET_PATH}/{token}"
    if destino and destino.startswith("/") and not destino.startswith("//"):
        url += f"?destino={quote(destino, safe='')}"
    return url
