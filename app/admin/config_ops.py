"""Núcleo de negócio das configurações do sistema (feature 168, US6 — Cauda Administrativa).

Funções puras (sem `request`/`render_template`), reusadas tanto pela view Jinja de
`app/admin/routes.py` quanto pelos endpoints de API (`app/api/admin_config_write.py`).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app import db
from app.models import SiteSetting
from app.utils import audit

#: `.svg` saiu de propósito: SVG é XML executável, então `/uploads` passou a servi-lo como anexo
#: com `X-Content-Type-Options: nosniff` — o navegador se recusa a desenhá-lo num `<img>`. Aceitar
#: aqui só produziria um logo que não aparece. Servi-lo inline traria de volta o XSS armazenado.
_ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def update_settings(settings: SiteSetting, fields: dict[str, Any], logo_file=None) -> SiteSetting:
    """Atualiza as configurações gerais do sistema.

    Campos numéricos/data inválidos são ignorados silenciosamente (mesma tolerância de hoje) —
    nunca bloqueiam o restante do formulário.

    Args:
        settings: Registro único de `SiteSetting` (id=1).
        fields: Campos brutos vindos do form/JSON (strings ou já tipados).
        logo_file: Arquivo de upload do logo (Werkzeug `FileStorage`), opcional.
    """
    commission_raw = str(fields.get("default_commission_rate") or "").strip()
    try:
        if commission_raw:
            settings.default_commission_rate = float(commission_raw)
    except ValueError:
        pass

    edu_raw = str(fields.get("educamanto_seller_id") or "").strip()
    settings.educamanto_seller_id = int(edu_raw) if edu_raw.isdigit() else None

    edu_rate_raw = str(fields.get("educamanto_commission_rate") or "").strip()
    try:
        if edu_rate_raw:
            settings.educamanto_commission_rate = float(edu_rate_raw)
    except ValueError:
        pass

    tax_raw = str(fields.get("tax_rate") or "").strip()
    try:
        if tax_raw:
            settings.tax_rate = float(tax_raw)
    except ValueError:
        pass

    fator_r_raw = str(fields.get("fator_r_threshold") or "").strip()
    try:
        if fator_r_raw:
            settings.fator_r_threshold = float(fator_r_raw)
    except ValueError:
        pass

    if logo_file is not None and logo_file.filename:
        import os

        from werkzeug.utils import secure_filename

        filename = secure_filename(logo_file.filename)
        ext = os.path.splitext(filename)[1].lower()
        if ext in _ALLOWED_LOGO_EXTENSIONS:
            from app.storage import save_file as _save_file

            settings.logo_path = _save_file(logo_file, "logos", f"logo{ext}")

    manto_addr = (fields.get("manto_address") or "").strip()
    if manto_addr:
        settings.manto_address = manto_addr

    margin_raw = str(fields.get("departure_margin_minutes") or "").strip()
    try:
        if margin_raw:
            settings.departure_margin_minutes = int(margin_raw)
    except ValueError:
        pass

    maps_key = (fields.get("google_maps_api_key") or "").strip()
    if maps_key:
        settings.google_maps_api_key = maps_key

    settings.email_notifications_enabled = bool(fields.get("email_notifications_enabled"))

    wa_form_raw = (fields.get("whatsapp_form_number") or "").strip()
    wa_form_digits = "".join(c for c in wa_form_raw if c.isdigit())
    settings.whatsapp_form_number = wa_form_digits or None

    # Semântica do whatsapp_form_number (vazio limpa e volta ao default), NÃO a do
    # manto_address (que ignora vazio) — senão o superadmin nunca conseguiria restaurar o
    # link padrão do Google Review. Dois cuidados extras:
    # - só aplica quando a CHAVE veio no payload: o form Jinja legado de /admin/settings não
    #   tem este campo e, sem o guard, qualquer salvamento por lá zeraria o link;
    # - só aceita http(s): o valor vira href em página pública (CTA pós-feedback) — uma
    #   `javascript:` URL colada aqui seria XSS entregue à cliente.
    if "google_review_url" in fields:
        review_url_raw = (fields.get("google_review_url") or "").strip()
        if review_url_raw and not review_url_raw.lower().startswith(("http://", "https://")):
            review_url_raw = ""
        settings.google_review_url = review_url_raw or None

    release_raw = (fields.get("release_date") or "").strip()
    if release_raw:
        try:
            settings.release_date = date.fromisoformat(release_raw)
        except ValueError:
            pass
    else:
        settings.release_date = None

    settings.updated_at = datetime.utcnow()
    audit("edit", "settings", 1, "Configurações", "Configurações do sistema atualizadas")
    db.session.commit()
    return settings
