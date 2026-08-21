"""Configuração do auditor de marketing (feature 256).

Só HTTP: os scripts nunca leem URL de banco. O único segredo é o token dos endpoints do
agente, lido de `.marketing-agent-token` na raiz do repositório (gitignored).
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MARKETING_ROOT = Path(__file__).resolve().parent

# Pastas de trabalho (todas no .gitignore)
INBOX_DIR = MARKETING_ROOT / "inbox"
PROCESSED_DIR = MARKETING_ROOT / "processed"
RUNS_DIR = MARKETING_ROOT / "runs"
DATA_DIR = MARKETING_ROOT / "data"
STORE_PATH = DATA_DIR / "marketing_store.sqlite"
STORE_PATH_LOCAL = DATA_DIR / "marketing_store_local.sqlite"
COLUMN_MAPS_PATH = MARKETING_ROOT / "column_maps.json"

# Endpoints do agente
PROD_BASE_URL = "https://app.mantoproducoes.com.br"
LOCAL_BASE_URL = "http://localhost:5000"
HTTP_TIMEOUT = 90

# Destinatários do relatório semanal (usuários internos ativos; o servidor filtra)
REPORT_RECIPIENTS = ["joao@mantoproducoes.com.br"]

# Titular do cartão que paga os anúncios — recebe o reembolso (usuário interno ativo)
CARD_HOLDER_EMAIL = "joao@mantoproducoes.com.br"

# Dia do mês em que o reembolso é pago (texto do gasto/relatório)
REIMBURSEMENT_DAY = 10

# Janela padrão da primeira rodada e aviso de janela longa
DEFAULT_WINDOW_DAYS = 7
LONG_WINDOW_DAYS = 8


def _read_secret_file(name: str) -> str:
    """Lê um arquivo de segredo da raiz do repositório (sem espaços nas pontas)."""
    path = REPO_ROOT / name
    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo {name} não encontrado na raiz do projeto ({path}). "
            "Ele é obrigatório e nunca deve ser versionado."
        )
    return path.read_text(encoding="utf-8").strip()


def agent_token() -> str:
    """Token dos endpoints `/api/marketing-agent/*` (arquivo `.marketing-agent-token`)."""
    return _read_secret_file(".marketing-agent-token")


def base_url(local: bool) -> str:
    """Base URL do Flask que serve os endpoints do agente."""
    return LOCAL_BASE_URL if local else os.getenv("MARKETING_BASE_URL", PROD_BASE_URL)


def store_path(local: bool) -> Path:
    """Memória local: teste e produção nunca compartilham arquivo."""
    return STORE_PATH_LOCAL if local else STORE_PATH


def ensure_dirs() -> None:
    """Garante as pastas de trabalho do auditor."""
    for pasta in (INBOX_DIR, PROCESSED_DIR, RUNS_DIR, DATA_DIR):
        pasta.mkdir(parents=True, exist_ok=True)
