"""Memória local do auditor de marketing (SQLite, fora do git).

Guarda só o operacional — rodadas, hashes de arquivo já lidos e achados já reportados. O
histórico analítico vive no ERP. Teste (`--local`) e produção nunca compartilham arquivo.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

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
CREATE TABLE IF NOT EXISTS files (
    sha256 TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    kind TEXT NOT NULL,
    run_id TEXT NOT NULL,
    seen_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS findings (
    code TEXT NOT NULL,
    key TEXT NOT NULL,
    first_run_id TEXT NOT NULL,
    last_run_id TEXT NOT NULL,
    PRIMARY KEY (code, key)
);
"""

_local_mode = False


def set_mode(local: bool) -> None:
    """Define qual memória usar; chame antes de qualquer outra função deste módulo."""
    global _local_mode
    _local_mode = local


def _conn() -> sqlite3.Connection:
    config.ensure_dirs()
    conn = sqlite3.connect(config.store_path(_local_mode))
    conn.executescript(_SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(UTC).isoformat()


def last_window_end() -> str | None:
    """Fim da última rodada com relatório enviado (ISO UTC), ou None na primeira vez."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT window_end FROM runs WHERE report_sent = 1 ORDER BY window_end DESC LIMIT 1"
        ).fetchone()
    return row[0] if row else None


def open_run(run_id: str, window_start: str, window_end: str) -> None:
    """Registra o início de uma rodada."""
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO runs (run_id, window_start, window_end, started_at) "
            "VALUES (?, ?, ?, ?)",
            (run_id, window_start, window_end, _now()),
        )


def close_run(run_id: str, *, report_sent: bool) -> None:
    """Fecha a rodada; só rodadas com relatório enviado avançam a janela."""
    with _conn() as conn:
        conn.execute(
            "UPDATE runs SET finished_at = ?, report_sent = ? WHERE run_id = ?",
            (_now(), 1 if report_sent else 0, run_id),
        )


def file_seen(sha256: str) -> bool:
    """True se um arquivo com este conteúdo já foi lido em alguma rodada."""
    with _conn() as conn:
        return conn.execute("SELECT 1 FROM files WHERE sha256 = ?", (sha256,)).fetchone() is not None


def remember_file(sha256: str, filename: str, kind: str, run_id: str) -> None:
    """Marca o conteúdo como lido (idempotência entre rodadas)."""
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO files (sha256, filename, kind, run_id, seen_at) VALUES (?, ?, ?, ?, ?)",
            (sha256, filename, kind, run_id, _now()),
        )


def finding_seen(code: str, key: str) -> bool:
    """True se este achado (código + chave) já saiu em relatório anterior."""
    with _conn() as conn:
        return conn.execute(
            "SELECT 1 FROM findings WHERE code = ? AND key = ?", (code, key)
        ).fetchone() is not None


def remember_finding(code: str, key: str, run_id: str) -> None:
    """Registra o achado para suprimir repetição nas próximas rodadas."""
    with _conn() as conn:
        conn.execute(
            "INSERT INTO findings (code, key, first_run_id, last_run_id) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(code, key) DO UPDATE SET last_run_id = excluded.last_run_id",
            (code, key, run_id, run_id),
        )
