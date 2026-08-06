"""Configuração do agente auditor financeiro (feature 221).

Tudo que é segredo (URLs de banco, token do agente) vem de arquivos na raiz do repositório
que já estão no `.gitignore` — nada de credencial neste módulo.

Arquivos esperados na raiz do projeto:
    .railway-db-url     — URL Postgres da produção (leitura).
    .local-db-url       — URL Postgres da cópia local `manto_local`.
    .audit-agent-token  — token do agente (mesmo valor do env AUDIT_AGENT_TOKEN no Railway).
"""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDITOR_ROOT = Path(__file__).resolve().parent

# Diretórios de trabalho (fora do git — ver .gitignore)
DATA_DIR = AUDITOR_ROOT / "data"
RUNS_DIR = AUDITOR_ROOT / "runs"
STORE_PATH = DATA_DIR / "audit_store.sqlite"

# Endpoints do agente em produção
PROD_BASE_URL = "https://app.mantoproducoes.com.br"
LOCAL_BASE_URL = "http://localhost:5000"

# Destinatários do relatório semanal (precisam ser usuários internos ativos do sistema)
REPORT_RECIPIENTS = ["joao@mantoproducoes.com.br"]

# Limiar de margem apertada: custo do evento >= 85% do valor de venda vira achado
MARGEM_CUSTO_MAXIMO = Decimal("0.85")

# Tolerância (dias) entre a data extraída do comprovante e a data esperada no registro
TOLERANCIA_DIAS_DATA = 5

# Janela extra (dias) recolhida antes do fim da última rodada, para pegar uploads atrasados
MARGEM_REACOLETA_DIAS = 2


def _read_secret_file(name: str) -> str:
    """Lê um arquivo de segredo da raiz do repositório e devolve o conteúdo sem espaços."""
    path = REPO_ROOT / name
    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo {name} não encontrado na raiz do projeto ({path}). "
            "Ele é obrigatório e nunca deve ser versionado."
        )
    return path.read_text(encoding="utf-8").strip()


def db_url(local: bool) -> str:
    """URL Postgres normalizada para psycopg (v3).

    Args:
        local: True usa a cópia `manto_local`; False usa a produção (Railway, leitura).
    """
    raw = _read_secret_file(".local-db-url" if local else ".railway-db-url")
    return raw.replace("postgresql+psycopg://", "postgresql://")


def agent_token() -> str:
    """Token dos endpoints `/api/audit-agent/*` (arquivo `.audit-agent-token`)."""
    return _read_secret_file(".audit-agent-token")


def base_url(local: bool) -> str:
    """Base URL do Flask que serve os endpoints do agente."""
    return LOCAL_BASE_URL if local else os.getenv("AUDITOR_BASE_URL", PROD_BASE_URL)


def ensure_dirs() -> None:
    """Garante os diretórios de trabalho do auditor."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
