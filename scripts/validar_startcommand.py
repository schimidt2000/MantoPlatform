# -*- coding: utf-8 -*-
"""Valida os argumentos do gunicorn do `railway.json` usando o parser REAL do gunicorn.

Existe por causa da queda de producao de 26/08/2026: a flag `--access-log-format` nao existe
(o nome correto e `--access-logformat`), o gunicorn recusou os argumentos, nunca subiu, e o
healthcheck do Railway falhou por 4min51s — com o container antigo ja derrubado por causa do
volume, o servico ficou fora.

O gunicorn nao RODA no Windows (precisa de fcntl/grp/pwd), mas o modulo de configuracao dele so
importa esses modulos no topo — com stubs em `sys.modules` o parser funciona, e e o parser dele
que decide se um argumento existe. Rode ANTES de qualquer push que mexa no comando de start:

    .venv\\Scripts\\python.exe scripts\\validar_startcommand.py

Mora em `scripts/` (versionado) e NAO em `scripts/db/`, que e gitignored: sem isto no repositorio
a protecao contra repetir a queda existiria so numa maquina.
"""
import json
import os
import pathlib
import shlex
import sys
import types

REPO = pathlib.Path(__file__).resolve().parents[1]

# Stubs dos modulos Unix que o gunicorn.config importa no topo. So precisam existir para o
# import passar; o parser de argumentos nao chama nada deles.
for nome in ("grp", "pwd", "fcntl"):
    if nome not in sys.modules:
        sys.modules[nome] = types.ModuleType(nome)

# O gunicorn.config chama os.geteuid()/os.getegid() ao DEFINIR as classes User/Group — nao
# existem no Windows. Valores fajutos: o parser nunca os usa para decidir se um argumento existe.
if not hasattr(os, "geteuid"):
    os.geteuid = lambda: 0  # type: ignore[attr-defined]
if not hasattr(os, "getegid"):
    os.getegid = lambda: 0  # type: ignore[attr-defined]

from gunicorn.config import Config  # noqa: E402 — depende dos stubs acima


def extrair_args(start_command: str) -> list[str]:
    """Pega só a parte do gunicorn do startCommand e devolve os argumentos."""
    trecho = start_command.split("gunicorn", 1)[1]
    # shlex com posix=True respeita as aspas simples do --access-logformat, igual ao shell.
    partes = shlex.split(trecho, posix=True)
    return [p for p in partes if p != "run:app"]


def main() -> int:
    railway = json.loads((REPO / "railway.json").read_text(encoding="utf-8"))
    start = railway["deploy"]["startCommand"]

    # nixpacks.toml precisa ser identico — divergencia ja causou confusao antes.
    nixpacks = (REPO / "nixpacks.toml").read_text(encoding="utf-8")
    if start not in nixpacks:
        print("[FALHOU] o startCommand do railway.json NAO aparece igual no nixpacks.toml")
        return 1
    print("[OK] railway.json e nixpacks.toml tem o mesmo comando")

    args = extrair_args(start)
    # $PORT nao existe aqui; troca por um valor valido so para o parser aceitar o --bind.
    args = [a.replace("$PORT", "8080") for a in args]

    try:
        parsed = Config().parser().parse_args(args)
    except SystemExit:
        # argparse chama sys.exit e ja imprimiu o erro (foi exatamente isto que derrubou a prod).
        print("\n[FALHOU] o gunicorn RECUSA estes argumentos — NAO faca push.")
        return 1

    print("[OK] o gunicorn aceita todos os argumentos")
    for campo in ("workers", "threads", "worker_class", "timeout", "graceful_timeout",
                  "max_requests", "max_requests_jitter", "accesslog", "access_log_format"):
        valor = getattr(parsed, campo, None)
        if valor is not None:
            print(f"     {campo} = {valor!r}")

    # Coerencia com o pool do SQLAlchemy: cada worker atende `threads` requisicoes MAIS as 6
    # threads de background que sobe (`_start_*` no fim de create_app).
    threads = int(getattr(parsed, "threads", None) or 1)
    sys.path.insert(0, str(REPO))
    from app.config import ProductionConfig

    opts = ProductionConfig.SQLALCHEMY_ENGINE_OPTIONS
    pool = int(opts.get("pool_size", 5)) + int(opts.get("max_overflow", 10))
    precisa = threads + 6
    if pool < precisa:
        print(f"\n[FALHOU] pool do SQLAlchemy = {pool} conexoes por worker, mas {threads} threads "
              f"+ 6 de background precisam de {precisa}. Suba pool_size/max_overflow em "
              f"app/config.py JUNTO com as threads.")
        return 1
    print(f"[OK] pool de {pool} conexoes por worker cobre {threads} threads + 6 de background")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
