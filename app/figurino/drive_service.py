import io
import os
import re
import unicodedata

from flask import current_app
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Google Docs mimetypes that can be exported as PDF
_EXPORTABLE_TYPES = {
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.spreadsheet",
    "application/vnd.google-apps.presentation",
}


def normalize_name(value: str) -> str:
    text = (value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def get_drive_service(credentials_path: str):
    creds = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def list_figurino_files(credentials_path: str) -> list:
    folder_id = current_app.config.get("FIGURINO_DRIVE_FOLDER_ID", "")
    if not folder_id:
        return []
    service = get_drive_service(credentials_path)
    results = (
        service.files()
        .list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name, webViewLink, mimeType)",
            pageSize=200,
        )
        .execute()
    )
    return results.get("files", [])


def generate_thumbnail(service, file_id: str, mime_type: str, output_path: str) -> bool:
    """Export the file as PDF and convert its first page to PNG.

    Returns True on success, False on any error.
    """
    try:
        import fitz  # PyMuPDF

        buf = io.BytesIO()

        if mime_type in _EXPORTABLE_TYPES:
            # Google Docs/Sheets/Slides → export as PDF
            request = service.files().export_media(
                fileId=file_id, mimeType="application/pdf"
            )
        elif mime_type == "application/pdf":
            # Already a PDF → download directly
            request = service.files().get_media(fileId=file_id)
        else:
            return False  # unsupported type

        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        buf.seek(0)
        doc = fitz.open(stream=buf.read(), filetype="pdf")
        page = doc[0]
        # Render at 2× zoom — enough for a card thumbnail
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        pix.save(output_path)
        doc.close()
        return True

    except Exception as e:
        print(f"[figurino] thumbnail error for {file_id}: {e}")
        return False
