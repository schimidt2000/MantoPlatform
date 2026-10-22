"""Gabarito de paridade da feature 313 — só leitura.

Recalcula todos os orçamentos salvos do `manto_local` (o `form_snapshot` de cada um, montado em payload como o
"Recalcular" da calculadora faz) com o `calculate_quote` do código que estiver no disco, e grava `{id: {quote,
snapshot} | {erro}}` num JSON. Rodado UMA vez na `c074657b`, antes de mexer no núcleo, ele é a única prova honesta de
"sem as chaves novas, o resultado é o de hoje": comparar com o `result_snapshot` salvo não serve, porque a tabela de
preços mudou desde que cada orçamento foi cotado (research R11).

Uso (ambiente do verify: DATABASE_URL de .local-db-url, FLASK_ENV=development, MANTO_SEM_THREADS=1)::

    python gabarito_paridade.py --gravar <arquivo.json>
    python gabarito_paridade.py --comparar <arquivo.json>     # resumo das diferenças contra o código atual

O `verify_313.py` importa `recalcular_todos` e `diferencas` para o cenário 1.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

#: Chaves que a 313 acrescenta ao `quote` e ao `snapshot` (data-model.md): a paridade as ignora — o que se exige é
#: que todo o resto seja idêntico. `memoria` não está aqui: as linhas novas (desconto, BV a repassar) só existem
#: com desconto ou BV, e sem eles a memória tem de ser a de hoje.
CHAVES_NOVAS_QUOTE = {
    "bruto_1h",
    "bruto_2h",
    "bruto_3h",
    "bruto_4h",
    "bruto_custom",
    "base_4h",
    "desconto_pct",
    "desconto_pct_texto",
    "desconto_modo",
    "pix_pct",
    "pix_1h",
    "pix_2h",
    "pix_3h",
    "pix_4h",
    "pix_custom",
    "bv_1h",
    "bv_2h",
    "bv_3h",
    "bv_4h",
    "bv_custom",
    "bv_pix_1h",
    "bv_pix_2h",
    "bv_pix_3h",
    "bv_pix_4h",
    "bv_pix_custom",
}
CHAVES_NOVAS_SNAPSHOT = {
    "versao_conta",
    "bases",
    "brutos",
    "desconto_pct_digitado",
    "desconto_valor",
    "desconto_duracao",
    "desconto_aplicado",
}


def payload_do_snapshot(snap: dict) -> dict:
    """O payload que o "Recalcular" monta a partir do snapshot salvo (`OrcamentoCalculadoraPage.tsx:249-278`)."""
    payload = dict(snap)
    payload["personalizado"] = bool(snap.get("personalizado_ativo"))
    payload["personalizado_criterio"] = snap.get("personalizado_criterio") or None
    # Feature 309: só a chave do produto volta; o preço é resolvido pela tabela vigente.
    payload["produtos"] = [
        {"chave": p.get("chave")} for p in snap.get("produtos") or [] if isinstance(p, dict)
    ]
    return payload


def recalcular_todos() -> dict[str, Any]:
    """`{id: {"quote", "snapshot"} | {"erro"}}` para todo orçamento com `form_snapshot` JSON. Dentro do app."""
    from app.models import OrcamentoHistory
    from app.orcamento import quote_ops

    saida: dict[str, Any] = {}
    for entry in OrcamentoHistory.query.order_by(OrcamentoHistory.id).all():
        try:
            snap = json.loads(entry.form_snapshot or "")
        except (TypeError, ValueError):
            continue
        if not isinstance(snap, dict):
            continue
        try:
            res = quote_ops.calculate_quote(payload_do_snapshot(snap))
        except quote_ops.QuoteValidationError as exc:
            saida[str(entry.id)] = {"erro": f"{exc.field}: {exc.message}"}
            continue
        except (
            TypeError,
            ValueError,
        ) as exc:  # snapshot antigo com texto onde hoje vai número ("0,01")
            saida[str(entry.id)] = {"erro": f"{type(exc).__name__}: {exc}"}
            continue
        saida[str(entry.id)] = {"quote": res["quote"], "snapshot": res["snapshot"]}
    return saida


def _sem_novas(d: dict, novas: set[str]) -> dict:
    return {k: v for k, v in d.items() if k not in novas}


def _caminhos(a: Any, b: Any, prefixo: str = "") -> list[str]:
    """Os caminhos em que `a` e `b` diferem (dicts e listas descendo; o resto por igualdade)."""
    if isinstance(a, dict) and isinstance(b, dict):
        out: list[str] = []
        for k in sorted(set(a) | set(b)):
            out += _caminhos(a.get(k), b.get(k), f"{prefixo}.{k}" if prefixo else str(k))
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            out += _caminhos(x, y, f"{prefixo}[{i}]")
        return out
    return [] if a == b else [prefixo]


def diferencas(gabarito: dict[str, Any], atual: dict[str, Any]) -> dict[str, list[str]]:
    """`{id: [caminhos que mudaram]}` — só os ids com diferença, ignorando as chaves novas da 313."""
    out: dict[str, list[str]] = {}
    for oid, g in gabarito.items():
        a = atual.get(oid)
        if a is None:
            out[oid] = ["(sumiu)"]
            continue
        if "erro" in g or "erro" in a:
            if g.get("erro") != a.get("erro"):
                out[oid] = [f"erro: {g.get('erro')!r} → {a.get('erro')!r}"]
            continue
        caminhos = _caminhos(
            {
                "quote": _sem_novas(g["quote"], CHAVES_NOVAS_QUOTE),
                "snapshot": _sem_novas(g["snapshot"], CHAVES_NOVAS_SNAPSHOT),
            },
            {
                "quote": _sem_novas(a["quote"], CHAVES_NOVAS_QUOTE),
                "snapshot": _sem_novas(a["snapshot"], CHAVES_NOVAS_SNAPSHOT),
            },
        )
        # `valores_brl` dentro de `snapshot.acrescimos` é do BV cheio: quando a regra da Q7 muda o preço, muda junto,
        # e isso é avaliado com o preço (cenário 1); aqui só se registra.
        if caminhos:
            out[oid] = caminhos
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--gravar")
    grupo.add_argument("--comparar")
    args = parser.parse_args()
    if not os.environ.get("DATABASE_URL") or os.environ.get("MANTO_SEM_THREADS") != "1":
        print("ambiente impróprio: DATABASE_URL e MANTO_SEM_THREADS=1", file=sys.stderr)
        return 2
    from app import create_app

    app = create_app()
    with app.app_context():
        atual = recalcular_todos()
    if args.gravar:
        texto = json.dumps(atual, ensure_ascii=False, sort_keys=True, default=str)
        Path(args.gravar).write_text(texto, encoding="utf-8")
        erros = sum(1 for v in atual.values() if "erro" in v)
        print(
            f"gravados {len(atual)} orçamentos ({erros} com erro de validação); sha256 "
            f"{hashlib.sha256(texto.encode('utf-8')).hexdigest()[:16]}"
        )
        return 0
    gabarito = json.loads(Path(args.comparar).read_text(encoding="utf-8"))
    # Comparação pelo mesmo caminho de serialização da gravação (floats e strings iguais aos do JSON).
    atual = json.loads(json.dumps(atual, ensure_ascii=False, sort_keys=True, default=str))
    difs = diferencas(gabarito, atual)
    print(f"{len(gabarito)} no gabarito; {len(difs)} com diferença")
    contagem = Counter(c.split("[")[0] for cs in difs.values() for c in cs)
    for caminho, n in contagem.most_common(20):
        print(f"  {n:5d}  {caminho}")
    return 0 if not difs else 1


if __name__ == "__main__":
    sys.exit(main())
