"""Porta de linha de comando da rotina para os endpoints do agente (feature 345).

A rotina semanal (skill `marketing-auditor`) lê a Meta e o Google pelos conectores do Claude e fala
com o ERP só por aqui, sem nunca ver o token: ele é lido de `.marketing-agent-token` e não aparece
na saída.

Uso (a partir de `scripts/marketing/`):
    ..\\..\\.venv\\Scripts\\python.exe agente.py GET "/comando?start=2026-11-09&end=2026-11-15"
    ..\\..\\.venv\\Scripts\\python.exe agente.py POST /anuncios corpo.json
    ..\\..\\.venv\\Scripts\\python.exe agente.py POST /run corpo.json --local

O corpo é um arquivo JSON (o Claude escreve no scratchpad). A resposta sai em JSON no stdout; o
código de saída é 0 em 2xx e 1 nos demais (com o status na primeira linha do stderr).
"""

from __future__ import annotations

import argparse
import json
import sys

import config
import requests

TIMEOUT_S = 60


def main() -> int:
    """Faz uma chamada ao agente e imprime a resposta JSON."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("metodo", choices=["GET", "POST"])
    parser.add_argument(
        "caminho", help="parte depois de /api/marketing-agent/<token>, ex.: /comando?start=…"
    )
    parser.add_argument("corpo", nargs="?", help="arquivo JSON do corpo (POST)")
    parser.add_argument("--local", action="store_true", help="Flask local (http://localhost:5000)")
    args = parser.parse_args()

    url = f"{config.base_url(args.local)}/api/marketing-agent/{config.agent_token()}{args.caminho}"
    corpo = None
    if args.corpo:
        with open(args.corpo, encoding="utf-8") as f:
            corpo = json.load(f)
    resp = requests.request(args.metodo, url, json=corpo, timeout=TIMEOUT_S)
    try:
        dados = resp.json()
    except ValueError:
        dados = {"texto": resp.text[:2000]}
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(dados, ensure_ascii=False, indent=2))
    if not resp.ok:
        # Nunca imprime a URL: ela carrega o token.
        print(
            f"HTTP {resp.status_code} em {args.metodo} {args.caminho.split('?')[0]}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
