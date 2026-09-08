# -*- coding: utf-8 -*-
"""Valida o `startCommand` do `manto-backend` no `render.yaml` com o parser REAL do gunicorn.

Existe por causa da queda de producao de 26/08/2026 (ainda no Railway): a flag
`--access-log-format` nao existe (o certo e `--access-logformat`), o gunicorn recusou os
argumentos, nunca subiu, e o healthcheck falhou por 4min51s — como o servico tem disco
persistente, o container antigo ja tinha sido derrubado e a producao ficou fora. No Render a
mecanica e a mesma: start que falha deixa o servico fora (docs/01 §5.3).

O gunicorn nao RODA no Windows (precisa de fcntl/grp/pwd), mas o modulo de configuracao dele so
importa esses modulos no topo — com stubs em `sys.modules` o parser funciona, e e o parser dele
que decide se um argumento existe.

E um validador MANUAL: nada no repositorio o executa. Rode ANTES de qualquer push que mexa no
`startCommand`, e faca essa mudanca em commit sozinho:

    .venv/Scripts/python.exe scripts/validar_startcommand.py

Le o `render.yaml` sem depender de PyYAML (nao esta em requirements*.txt): recorta o bloco do
servico `manto-backend` e pega a unica linha `startCommand:` dele. Mora em `scripts/`
(versionado) e NAO em `scripts/db/`, que e gitignored — sem isto no repositorio a protecao
contra repetir a queda existiria so numa maquina.
"""
import os
import pathlib
import re
import shlex
import sys
import types

REPO = pathlib.Path(__file__).resolve().parents[1]
BLUEPRINT = REPO / "render.yaml"
SERVICO = "manto-backend"
THREADS_DE_FUNDO = 6  # `_start_*` no fim de create_app, uma copia por worker

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


def bloco_do_servico(texto: str, nome: str) -> str:
    """Recorta, do YAML, o item de `services` cujo `name:` e `nome` (ate o proximo `- type:`)."""
    inicio = re.search(rf"^\s*name:\s*{re.escape(nome)}\s*$", texto, re.MULTILINE)
    if not inicio:
        raise SystemExit(f"[FALHOU] servico `{nome}` nao encontrado em {BLUEPRINT.name}")
    resto = texto[inicio.end():]
    proximo = re.search(r"^\s*-\s*type:", resto, re.MULTILINE)
    return resto if not proximo else resto[: proximo.start()]


def start_command_do_render() -> str:
    """Devolve o unico `startCommand:` do bloco do backend; zero ou mais de um e erro."""
    bloco = bloco_do_servico(BLUEPRINT.read_text(encoding="utf-8"), SERVICO)
    comandos = re.findall(r"^\s*startCommand:\s*(.+?)\s*$", bloco, re.MULTILINE)
    if len(comandos) != 1:
        raise SystemExit(
            f"[FALHOU] esperava 1 `startCommand:` no bloco `{SERVICO}` do render.yaml, "
            f"achei {len(comandos)}"
        )
    # E o healthcheck que gateia o deploy: sem ele o Render troca o container as cegas.
    if not re.search(r"^\s*healthCheckPath:\s*/health\s*$", bloco, re.MULTILINE):
        raise SystemExit(f"[FALHOU] o bloco `{SERVICO}` perdeu o `healthCheckPath: /health`")
    print(f"[OK] startCommand lido do bloco `{SERVICO}` do render.yaml (com healthCheckPath)")
    return comandos[0]


def extrair_args(start_command: str) -> list[str]:
    """Pega so a parte do gunicorn do startCommand e devolve os argumentos."""
    trecho = start_command.split("gunicorn", 1)[1]
    # shlex com posix=True respeita as aspas simples do --access-logformat, igual ao shell.
    partes = shlex.split(trecho, posix=True)
    return [p for p in partes if p != "run:app"]


def main() -> int:
    start = start_command_do_render()
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

    # Coerencia com o pool do SQLAlchemy: cada worker atende `threads` requisicoes MAIS as
    # threads de background que sobe.
    threads = int(getattr(parsed, "threads", None) or 1)
    sys.path.insert(0, str(REPO))
    from app.config import ProductionConfig

    opts = ProductionConfig.SQLALCHEMY_ENGINE_OPTIONS
    pool = int(opts.get("pool_size", 5)) + int(opts.get("max_overflow", 10))
    precisa = threads + THREADS_DE_FUNDO
    if pool < precisa:
        print(f"\n[FALHOU] pool do SQLAlchemy = {pool} conexoes por worker, mas {threads} threads "
              f"+ {THREADS_DE_FUNDO} de background precisam de {precisa}. Suba pool_size/"
              f"max_overflow em app/config.py JUNTO com as threads.")
        return 1
    print(f"[OK] pool de {pool} conexoes por worker cobre {threads} threads + "
          f"{THREADS_DE_FUNDO} de background")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
