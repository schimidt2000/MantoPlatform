"""Memória persistente do auditor (SQLite local, fora do git).

Guarda o histórico de rodadas e de achados. É ela que torna a rodada idempotente
(comprovante já lido com o mesmo hash não é reprocessado) e que permite detectar
duplicata contra TODO o histórico, não só a semana corrente.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    report_sent INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS audited_files (
    entity_uid TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    run_id TEXT NOT NULL,
    extracted_json TEXT,
    audited_at TEXT NOT NULL,
    PRIMARY KEY (entity_uid, sha256)
);
CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    entity_uid TEXT,
    sha256 TEXT,
    code TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    details_json TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_findings_run ON findings (run_id);
CREATE INDEX IF NOT EXISTS ix_audited_sha ON audited_files (sha256);
"""


def _connect() -> sqlite3.Connection:
    config.ensure_dirs()
    conn = sqlite3.connect(config.STORE_PATH)
    conn.executescript(_SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def last_window_end() -> str | None:
    """Fim da última janela coletada (ISO UTC) ou None na primeira rodada."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT window_end FROM runs ORDER BY window_end DESC LIMIT 1"
        ).fetchone()
    return row[0] if row else None


def open_run(run_id: str, window_start: str, window_end: str) -> None:
    """Registra o início de uma rodada."""
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO runs (run_id, window_start, window_end, started_at)"
            " VALUES (?, ?, ?, ?)",
            (run_id, window_start, window_end, _now()),
        )


def close_run(run_id: str, report_sent: bool) -> None:
    """Registra o fim de uma rodada."""
    with _connect() as conn:
        conn.execute(
            "UPDATE runs SET finished_at = ?, report_sent = ? WHERE run_id = ?",
            (_now(), 1 if report_sent else 0, run_id),
        )


def already_audited(entity_uid: str, sha256: str) -> bool:
    """True se este comprovante (entidade + hash) já foi lido numa rodada anterior."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM audited_files WHERE entity_uid = ? AND sha256 = ?",
            (entity_uid, sha256),
        ).fetchone()
    return row is not None


def sha_seen_elsewhere(entity_uid: str, sha256: str) -> list[str]:
    """Entidades DIFERENTES que já usaram este mesmo arquivo (duplicata histórica)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT entity_uid FROM audited_files WHERE sha256 = ? AND entity_uid != ?",
            (sha256, entity_uid),
        ).fetchall()
    return [r[0] for r in rows]


def record_audited(entity_uid: str, sha256: str, run_id: str, extracted: dict) -> None:
    """Marca um comprovante como lido, com o JSON extraído."""
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO audited_files"
            " (entity_uid, sha256, run_id, extracted_json, audited_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (entity_uid, sha256, run_id, json.dumps(extracted, ensure_ascii=False), _now()),
        )


def record_findings(run_id: str, findings: list[dict]) -> None:
    """Persiste os achados de uma rodada."""
    with _connect() as conn:
        conn.executemany(
            "INSERT INTO findings"
            " (run_id, entity_uid, sha256, code, severity, title, details_json, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    run_id,
                    f.get("entity_uid"),
                    f.get("sha256"),
                    f["code"],
                    f["severity"],
                    f["title"],
                    json.dumps(f.get("details", {}), ensure_ascii=False, default=str),
                    _now(),
                )
                for f in findings
            ],
        )
