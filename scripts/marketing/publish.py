"""Publicação da rodada no ERP (feature 256): contexto + ingestão idempotente.

    python publish.py --run <run_id> [--local]

Lê `runs/<id>/manifest.json` e `normalizado.json`, busca o contexto (`GET /context`) e envia
o `POST /run`. Grava `contexto.json` e `resultado.json` na pasta da rodada. Sai com código ≠ 0
se o servidor recusar — e nunca inventa um resultado.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import config
import requests
import store


def _carrega(run_dir: Path, nome: str) -> dict:
    return json.loads((run_dir / nome).read_text(encoding="utf-8"))


def _grava(run_dir: Path, nome: str, dados: dict) -> None:
    (run_dir / nome).write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def buscar_contexto(base: str, token: str, janela: list[str]) -> dict:
    """`GET /context` com a janela da rodada e o titular do cartão configurado."""
    resp = requests.get(
        f"{base}/api/marketing-agent/{token}/context",
        params={"window_start": janela[0], "window_end": janela[1],
                "card_holder_email": config.CARD_HOLDER_EMAIL},
        timeout=config.HTTP_TIMEOUT,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"contexto recusado: HTTP {resp.status_code} — {resp.text[:300]}")
    return resp.json()


def montar_payload(manifest: dict, normalizado: dict) -> dict:
    """Corpo do `POST /run` (contracts/agent-endpoints.md)."""
    return {
        "run_id": manifest["run_id"],
        "mode": manifest["mode"],
        "window": manifest["window"],
        "card_holder_email": config.CARD_HOLDER_EMAIL,
        "files": [
            {k: f.get(k) for k in ("filename", "sha256", "kind", "period_start", "period_end",
                                   "status", "reason", "row_count")}
            for f in manifest["files"]
        ],
        "post_metrics": normalizado.get("post_metrics", []),
        "campaign_metrics": normalizado.get("campaign_metrics", []),
        "account_metrics": normalizado.get("account_metrics", []),
        "findings": [
            {"code": "nota_leitura", "severity": "info", "title": nota, "details": {}}
            for nota in normalizado.get("notes", [])
        ],
    }


def enviar_rodada(base: str, token: str, payload: dict) -> dict:
    """`POST /run`; o servidor é quem decide o que foi gravado, vinculado e reembolsado."""
    resp = requests.post(f"{base}/api/marketing-agent/{token}/run", json=payload, timeout=config.HTTP_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(f"ingestão recusada: HTTP {resp.status_code} — {resp.text[:500]}")
    return resp.json()


def main() -> int:
    ap = argparse.ArgumentParser(description="Publica a rodada do auditor de marketing no ERP")
    ap.add_argument("--run", required=True)
    ap.add_argument("--local", action="store_true")
    args = ap.parse_args()

    store.set_mode(args.local)
    run_dir = config.RUNS_DIR / args.run
    manifest = _carrega(run_dir, "manifest.json")
    normalizado = _carrega(run_dir, "normalizado.json")
    base, token = config.base_url(args.local), config.agent_token()

    try:
        contexto = buscar_contexto(base, token, manifest["window"])
        _grava(run_dir, "contexto.json", contexto)
        resultado = enviar_rodada(base, token, montar_payload(manifest, normalizado))
        _grava(run_dir, "resultado.json", resultado)
    except (requests.RequestException, RuntimeError) as exc:
        print(f"[publicacao] FALHA: {exc}")
        return 1

    up = resultado.get("upserted", {})
    print(f"[publicacao] replay={resultado.get('replayed')} arquivos={resultado.get('files')} "
          f"posts={up.get('post_metrics')} campanhas={up.get('campaign_metrics')} conta={up.get('account_metrics')}")
    for acao in resultado.get("ad_spend", []):
        print(f"[publicacao] reembolso {acao.get('platform')} {acao.get('month_ref')}: {acao.get('action')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
