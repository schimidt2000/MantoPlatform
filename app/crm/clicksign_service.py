"""
ClickSign API v3 integration — envelope lookup and webhook processing.
"""
import re
import urllib.request
import urllib.error
import json
import hmac
import hashlib
from datetime import datetime
from typing import Optional

PRODUCTION_URL = "https://app.clicksign.com/api/v3"
SANDBOX_URL    = "https://sandbox.clicksign.com/api/v3"

# Fluxia links por tipo de contrato
CONTRACT_LINKS = {
    "corporativo":       "https://app.clicksign.com/fluxia/b19e8172-baa3-48df-a924-8c002ac0de1a",
    "infantil":          "https://app.clicksign.com/fluxia/da42ef0d-27db-4dde-a3ec-88b9fb01fedf",
    "infantil_americano":"https://app.clicksign.com/fluxia/e2a1b277-418c-4bd6-9670-4c71a06b39ad",
}

CONTRACT_LABELS = {
    "corporativo":        "Corporativo",
    "infantil":           "Infantil",
    "infantil_americano": "Infantil (número americano)",
}

_RE_DIGITS = re.compile(r"\D")


def detect_contract_type(deal) -> str:
    """Sugere o tipo de contrato com base no tipo de evento e no telefone.

    Regra: qualquer evento CORP → corporativo.
    Infantil/Social/outros → infantil (ou infantil_americano se telefone +1).
    """
    event_type = (deal.event_type or "").upper()  # vem do CalendarEvent via deal
    service    = (deal.service_type or "").upper()
    if "CORP" in event_type or "CORP" in service:
        return "corporativo"
    # número americano: começa com 1 e tem 11 dígitos (1 + 10)
    phone  = deal.contractor_whatsapp or ""
    digits = _RE_DIGITS.sub("", phone)
    if digits.startswith("1") and len(digits) == 11:
        return "infantil_americano"
    return "infantil"


def get_contract_link(deal) -> str:
    return CONTRACT_LINKS[detect_contract_type(deal)]


def get_contract_label(deal) -> str:
    return CONTRACT_LABELS[detect_contract_type(deal)]


def _base_url(sandbox: bool) -> str:
    return SANDBOX_URL if sandbox else PRODUCTION_URL


def _request(token: str, sandbox: bool, method: str, path: str, body: dict = None):
    """Faz uma requisição autenticada à API do ClickSign."""
    url = f"{_base_url(sandbox)}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": token,
            "Accept":        "application/vnd.api+json",
            "Content-Type":  "application/vnd.api+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode()}


def get_envelope(token: str, sandbox: bool, envelope_key: str) -> Optional[dict]:
    """Busca detalhes de um envelope no ClickSign."""
    result = _request(token, sandbox, "GET", f"/envelopes/{envelope_key}")
    if "error" in result:
        return None
    return result.get("data")


def verify_webhook_hmac(secret: str, raw_body: bytes, hmac_header: str) -> bool:
    """Verifica assinatura HMAC SHA256 do webhook ClickSign."""
    if not secret:
        return True  # sem secret configurado, aceita tudo (dev)
    computed = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, hmac_header or "")


def parse_webhook_event(payload: dict) -> dict:
    """
    Extrai campos relevantes do payload do webhook ClickSign.
    Retorna: { event, envelope_key, status, signer_email, signer_phone }
    """
    event_type   = payload.get("event", {}).get("name", "")
    document     = payload.get("document", {})
    envelope_key = document.get("key", "")
    status       = document.get("status", "")
    signers      = document.get("signers", [])
    signer_email = signers[0].get("email", "") if signers else ""
    signer_phone = signers[0].get("phone_number", "") if signers else ""

    return {
        "event":        event_type,
        "envelope_key": envelope_key,
        "status":       status,
        "signer_email": signer_email,
        "signer_phone": signer_phone,
    }
