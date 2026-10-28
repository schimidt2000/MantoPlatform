"""verify_321 — o gerador de novidades para a equipe (scripts/novidades.py).

Não usa o manto_local: só git (faixa fixa 0feb4255..6f706fa6 da main) e arquivos. Roda da raiz:

    PYTHONUTF8=1 python specs/321-novidades-para-a-equipe/verify_321.py
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "scripts" / "novidades.py"
DESDE, ATE = "0feb4255", "6f706fa6"
RESULTADOS: list[tuple[str, bool, str]] = []


def cenario(nome: str, ok: bool, detalhe: str = "") -> None:
    RESULTADOS.append((nome, ok, detalhe))
    print(f"[{'OK' if ok else 'FALHOU'}] {nome}{(' — ' + detalhe) if detalhe else ''}")


def rodar(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", env={**__import__("os").environ, "PYTHONUTF8": "1"},
    )


def main() -> int:
    saida = rodar("--desde", DESDE, "--ate", ATE, "--json")
    lista = json.loads(saida.stdout) if saida.returncode == 0 else []
    nums = [it["num"] for it in lista]

    cenario("1. a faixa 14/10..27/10 tem 21 mudanças", len(lista) == 21, f"{len(lista)}: {nums}")
    primeiro = lista[0] if lista else {}
    cenario(
        "2. a 320 vem primeiro, com spec e data de produção do docs/03",
        primeiro.get("num") == "320"
        and primeiro.get("spec") == "specs/320-voltar-sem-perder-o-lugar/spec.md"
        and (primeiro.get("producao") or "").startswith("27/10/2026"),
        f"{primeiro.get('num')} · {primeiro.get('spec')} · {primeiro.get('producao')}",
    )
    com_alerta = {it["num"] for it in lista if it.get("alerta")}
    cenario(
        "3. 310, 317 e 318 (desligadas até o dono configurar) saem com ⚠; a 320 e a 313 não",
        {"310", "317", "318"} <= com_alerta and not ({"320", "313"} & com_alerta),
        f"com alerta: {sorted(com_alerta)}",
    )
    cenario("4. docs(...) e chore(...) ficam de fora", all(it["num"] is not None for it in lista), str([it["titulo"] for it in lista if it["num"] is None]))
    cenario(
        "5. hotfix com sufixo (185b, 299b, 306b, 316b, 298b) é reconhecido pelo número",
        {"185b", "299b", "306b", "316b", "298b"} <= set(nums),
    )
    pedido_320 = primeiro.get("pedido") or []
    cenario("6. a seção 'O pedido' da spec entra no material", bool(pedido_320) and "voltar" in " ".join(pedido_320).lower())

    contar = rodar("--desde", DESDE, "--ate", ATE, "--contar")
    hook = rodar("--desde", DESDE, "--ate", ATE, "--hook")
    cenario(
        "7. --contar imprime 21; --hook sai 0 e avisa no stderr com a lista",
        contar.stdout.strip() == "21" and hook.returncode == 0 and "21 mudança" in hook.stderr and "320" in hook.stderr and hook.stdout == "",
        f"contar={contar.stdout.strip()!r} hook.rc={hook.returncode} stderr={hook.stderr.strip()[:80]!r}",
    )

    # --rascunho numa data que não existe no repositório; o arquivo é apagado no fim.
    data_teste = "1999-01-01"
    alvo = RAIZ / "docs" / "novidades" / f"{data_teste}.md"
    try:
        r = rodar("--desde", DESDE, "--ate", ATE, "--rascunho", "--hoje", data_teste)
        texto = alvo.read_text(encoding="utf-8") if alvo.exists() else ""
        secoes = ["### Comercial", "### Financeiro", "### Casting e Produção", "### Figurino", "### Marketing", "### Artistas (portal)", "### Todos"]
        cenario(
            "8. --rascunho cria o arquivo do dia com as sete seções e o material da 320",
            r.returncode == 0 and all(s in texto for s in secoes) and "### 320 — " in texto and "specs/320-voltar-sem-perder-o-lugar/spec.md" in texto,
            f"rc={r.returncode} tamanho={len(texto)}",
        )
    finally:
        if alvo.exists():
            alvo.unlink()

    # --marcar e ler_marco num arquivo temporário, importando o módulo.
    spec = importlib.util.spec_from_file_location("novidades", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with tempfile.TemporaryDirectory() as tmp:
        mod.MARCO = Path(tmp) / "ULTIMO_AVISO"
        mod.PASTA = Path(tmp)
        mod.marcar(ATE, dt.date(2026, 10, 28), "docs/novidades/2026-10-28.md")
        mod.marcar(ATE, dt.date(2026, 10, 29), None)
        marco = mod.ler_marco()
        conteudo = mod.MARCO.read_text(encoding="utf-8")
        cenario(
            "9. --marcar acrescenta uma linha por rodada e ler_marco devolve a última",
            marco is not None and marco[0] == ATE and marco[1] == "2026-10-29" and conteudo.count(ATE) == 2 and conteudo.startswith("#"),
            f"marco={marco}",
        )

    ok = sum(1 for _, r, _ in RESULTADOS if r)
    print(f"\nverify_321: {ok}/{len(RESULTADOS)}")
    return 0 if ok == len(RESULTADOS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
