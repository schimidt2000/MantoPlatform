from app.talents.sheets_client import get_sheets_service

SPREADSHEET_ID = "1A_bXqUP21HR1RWS8AVBmj1oPgjhIWBaFfYxeqX17Ric"
SHEET_NAME = "Respostas"
CREDENTIALS_PATH = r".\instance\credentials\sheets_service_account.json"

service = get_sheets_service(CREDENTIALS_PATH)
res = service.spreadsheets().values().get(
    spreadsheetId=SPREADSHEET_ID,
    range=f"{SHEET_NAME}!A1:Z1000"
).execute()

values = res.get("values", [])
print("Linhas recebidas:", len(values))
print("Primeira linha (header):", values[0] if values else None)
print("Segunda linha (primeira resposta):", values[1] if len(values) > 1 else None)
