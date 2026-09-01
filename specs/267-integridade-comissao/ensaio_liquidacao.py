"""Ensaio da feature 267: o que a liquidação passa a alcançar (rodar ANTES do merge).

A 267 troca o filtro das quatro liquidações de `sale_date` puro para
`coalesce(payable_from, sale_date)`. Isso MUDA quais linhas um lote liquida — e lote de comissão
é dinheiro. Este script mede a diferença contra a cópia de produção, por mês e por vendedor.

**O que tem de acontecer:** toda linha que entra ou sai de um lote tem de ter `payable_from`
preenchido (comissão EducaManto, feature 109). Qualquer linha COMUM mudando de lote é sinal de
que a expressão saiu errada — e aí o merge não vai.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    .venv/Scripts/python.exe specs/267-integridade-comissao/ensaio_liquidacao.py
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

engine = create_engine(os.environ["DATABASE_URL"], future=True)

# Mesmo conjunto de status que as quatro liquidações usam (inclui `no_banco`).
STATUS = ("a_pagar", "no_banco", "pago")

SQL = text(
    """
    SELECT
        id,
        seller_id,
        event_title,
        amount,
        status,
        sale_date,
        payable_from,
        to_char(sale_date, 'YYYY-MM')                                AS lote_antigo,
        to_char(COALESCE(payable_from, sale_date), 'YYYY-MM')        AS lote_novo
    FROM commission_payments
    WHERE status = ANY(:status)
    """
)


def main() -> int:
    with engine.connect() as conn:
        linhas = conn.execute(SQL, {"status": list(STATUS)}).fetchall()

    mudaram = [r for r in linhas if r.lote_antigo != r.lote_novo]
    com_payable = [r for r in mudaram if r.payable_from is not None]
    sem_payable = [r for r in mudaram if r.payable_from is None]

    print(f"Comissões vivas ({'/'.join(STATUS)}): {len(linhas)}")
    print(f"Mudam de lote com a feature 267: {len(mudaram)}")
    print(f"  · com payable_from (EducaManto, ESPERADO): {len(com_payable)}")
    print(f"  · SEM payable_from (comum, NÃO ESPERADO):  {len(sem_payable)}")

    if mudaram:
        print("\nDetalhe do que muda de lote:")
        for r in sorted(mudaram, key=lambda x: (x.lote_novo or "", x.seller_id)):
            marca = "ok " if r.payable_from else "!! "
            print(
                f"  {marca}#{r.id} vendedor={r.seller_id} R$ {r.amount} [{r.status}] "
                f"{r.lote_antigo} → {r.lote_novo}  ({(r.event_title or '')[:48]})"
            )

    # Impacto por lote (vendedor × mês): o que um clique em "pago" passa a pegar a mais/menos.
    antigo: dict[tuple, int] = defaultdict(int)
    novo: dict[tuple, int] = defaultdict(int)
    for r in linhas:
        if r.lote_antigo:
            antigo[(r.seller_id, r.lote_antigo)] += 1
        if r.lote_novo:
            novo[(r.seller_id, r.lote_novo)] += 1

    lotes = sorted(set(antigo) | set(novo), key=lambda k: (k[1], k[0]))
    diferentes = [k for k in lotes if antigo[k] != novo[k]]
    print(f"\nLotes (vendedor × mês) com contagem diferente: {len(diferentes)} de {len(lotes)}")
    for k in diferentes:
        print(f"  vendedor={k[0]} mês={k[1]}: {antigo[k]} → {novo[k]} linha(s)")

    # Só linhas de EducaManto podem mudar de lote. Uma comum mudando = expressão errada.
    if sem_payable:
        print("\n❌ REPROVADO: linha COMUM mudou de lote — a expressão de ciclo está errada.")
        return 1
    print("\n✅ APROVADO: só comissões com payable_from (EducaManto) mudaram de lote.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
