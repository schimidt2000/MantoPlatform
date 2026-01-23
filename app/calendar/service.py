import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

TZ = ZoneInfo("America/Sao_Paulo")

def _instance_path(filename: str) -> str:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base_dir, "instance", filename)

def get_client_secrets_path() -> str:
    return _instance_path("google_oauth_client.json")

def get_token_path() -> str:
    return _instance_path("google_token.json")

def build_flow(redirect_uri: str) -> Flow:
    return Flow.from_client_secrets_file(
        get_client_secrets_path(),
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )

def get_authorization_url(redirect_uri: str) -> tuple[str, str]:
    flow = build_flow(redirect_uri)
    auth_url, state = flow.authorization_url(
        access_type="offline",              # necessário para refresh_token :contentReference[oaicite:6]{index=6}
        include_granted_scopes="true",
        prompt="consent"                    # garante refresh_token na 1ª autorização em muitos casos :contentReference[oaicite:7]{index=7}
    )
    return auth_url, state

def save_token(creds: Credentials) -> None:
    data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }
    with open(get_token_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_credentials() -> Credentials | None:
    token_path = get_token_path()
    if not os.path.exists(token_path):
        return None

    with open(token_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    creds = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes"),
    )

    # refresh automático se expirado
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        save_token(creds)

    return creds

def fetch_events_for_month(calendar_id: str, year: int, month: int) -> list[dict]:
    creds = load_credentials()
    if not creds:
        raise RuntimeError("Google não conectado. Acesse /google/connect primeiro.")

    service = build("calendar", "v3", credentials=creds)

    start = datetime(year, month, 1, 0, 0, 0, tzinfo=TZ)
    # primeiro dia do mês seguinte
    if month == 12:
        end = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=TZ)
    else:
        end = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=TZ)

    resp = service.events().list(
        calendarId=calendar_id,
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
        showDeleted=False,
        maxResults=2500,
    ).execute()  # parâmetros são os oficiais para listar ordenado por início :contentReference[oaicite:8]{index=8}

    return resp.get("items", [])
