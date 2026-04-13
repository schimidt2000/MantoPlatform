import json
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def get_sheets_service(credentials_path: str):
    env_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
    if env_json:
        info = json.loads(env_json)
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        creds = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES
        )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)
