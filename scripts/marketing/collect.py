"""Coleta da rodada do auditor de marketing (feature 256).

Lê os CSVs de `inbox/`, reconhece e normaliza cada um, grava `runs/<id>/manifest.json` e
`runs/<id>/normalizado.json` e move os arquivos para `processed/<id>/`:

    python collect.py            # produção (janela desde a última rodada enviada)
    python collect.py --local    # memória local separada; nada vai para produção
    python collect.py --desde 2026-08-01

Nada aqui toca rede nem banco — a ingestão é o `publish.py`.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import config
import parsers
import store


def compute_window(desde: str | None) -> tuple[datetime, datetime]:
    """Janela UTC: do fim da última rodada enviada (ou `--desde`, ou 7 dias) até agora."""
    agora = datetime.now(UTC)
    if desde:
        inicio = datetime.strptime(desde, "%Y-%m-%d").replace(tzinfo=UTC)
        return inicio, agora
    ultimo = store.last_window_end()
    if ultimo:
        inicio = datetime.fromisoformat(ultimo)
        if inicio.tzinfo is None:
            inicio = inicio.replace(tzinfo=UTC)
        return inicio, agora
    return agora - timedelta(days=config.DEFAULT_WINDOW_DAYS), agora


def _destino(processed_dir: Path, path: Path, veredito: parsers.FileVerdict) -> Path:
    sufixo = {"rejected": "_REJEITADO", "skipped_duplicate": "_DUPLICADO"}.get(veredito.status, "")
    return processed_dir / f"{path.stem}{sufixo}{path.suffix}"


def processar_arquivo(path: Path, maps: dict, run_id: str, run_date) -> tuple[parsers.FileVerdict, dict]:
    """Veredito + dados de um arquivo; conteúdo já visto é pulado sem reler."""
    sha = parsers.sha256_of(path)
    if store.file_seen(sha):
        return parsers.FileVerdict(filename=path.name, sha256=sha, status="skipped_duplicate",
                                   reason="conteúdo idêntico a um arquivo já lido"), {}
    veredito, dados = parsers.parse_file(path, maps, run_date=run_date)
    store.remember_file(sha, path.name, veredito.kind, run_id)
    return veredito, dados


def _processar_inbox(maps: dict, run_id: str, run_date, processed_dir: Path) -> tuple[list[dict], dict]:
    """Lê e move cada CSV da inbox; devolve os vereditos e o normalizado consolidado."""
    vereditos: list[dict] = []
    normalizado: dict = {"post_metrics": [], "campaign_metrics": [], "account_metrics": [], "notes": []}
    for path in sorted(config.INBOX_DIR.glob("*.csv")):
        veredito, dados = processar_arquivo(path, maps, run_id, run_date)
        vereditos.append(veredito.as_dict())
        for chave in ("post_metrics", "campaign_metrics", "account_metrics"):
            normalizado[chave].extend(dados.get(chave, []))
        normalizado["notes"].extend(f"{path.name}: {n}" for n in veredito.notes)
        shutil.move(str(path), str(_destino(processed_dir, path, veredito)))
        print(f"[coleta] {path.name}: {veredito.kind} / {veredito.status}"
              + (f" — {veredito.reason}" if veredito.reason else ""))
    return vereditos, normalizado


def _gravar_saidas(run_dir: Path, manifest: dict, normalizado: dict) -> None:
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "normalizado.json").write_text(json.dumps(normalizado, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Coleta do auditor de marketing")
    ap.add_argument("--local", action="store_true")
    ap.add_argument("--desde", help="início da janela (YYYY-MM-DD)")
    args = ap.parse_args()

    store.set_mode(args.local)
    config.ensure_dirs()
    inicio, fim = compute_window(args.desde)
    run_id = fim.strftime("%Y%m%d-%H%M%S")
    run_dir, processed_dir = config.RUNS_DIR / run_id, config.PROCESSED_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    store.open_run(run_id, inicio.isoformat(), fim.isoformat())

    vereditos, normalizado = _processar_inbox(parsers.load_column_maps(), run_id, fim.date(), processed_dir)
    manifest = {"run_id": run_id, "mode": "local" if args.local else "prod",
                "window": [inicio.isoformat(), fim.isoformat()],
                "generated_at": datetime.now(UTC).isoformat(), "files": vereditos}
    _gravar_saidas(run_dir, manifest, normalizado)
    aceitos = sum(1 for v in vereditos if v["status"] == "accepted")
    print(f"[coleta] run_id={run_id} arquivos={len(vereditos)} aceitos={aceitos} "
          f"posts={len(normalizado['post_metrics'])} campanhas={len(normalizado['campaign_metrics'])} "
          f"conta={len(normalizado['account_metrics'])}")
    print(run_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
