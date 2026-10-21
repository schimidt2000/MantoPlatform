"""Verificação da correção 299b — a mensagem de cobrança se copia a qualquer momento.

Antes, o "💰 Cobrança" do detalhe do evento só liberava a partir do vencimento (o saldo vence 2 dias
antes do evento). Agora a data não trava mais nada; as outras travas continuam.

Cenários (objetos em memória, nada é gravado no banco):
 1. DEVE FALHAR na main antiga: venda com saldo e vencimento daqui a 10 dias → libera.
 2. DEVE FALHAR na main antiga: venda com saldo e sem vencimento (evento sem data) → libera.
 3. Venda vencida ou vencendo hoje → continua liberando.
 4. Continua travado: venda quitada (saldo abaixo da folga de R$ 1,00).
 5. Continua travado: cortesia, sem valor, valor simbólico e venda fora das listas (motivo_fora).
 6. Continua travado: o outro evento do grupo (quem cobra é o principal).
 7. `_compute_cobranca` (o JSON do detalhe) leva `enabled: true` antes do vencimento.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    $env:MANTO_SEM_THREADS = "1"; $env:PYTHONUTF8 = "1"
    .\\.venv\\Scripts\\python.exe specs\\299b-cobranca-a-qualquer-momento\\verify_299b.py
"""

from __future__ import annotations

import os
import sys
import traceback
from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MAIL_SUPPRESS_SEND", "true")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from app import create_app  # noqa: E402
from app.constants import now_sp  # noqa: E402
from app.financeiro.cobranca_ops import VendaResumo, pode_copiar_cobranca  # noqa: E402
from app.models import CalendarEvent  # noqa: E402

app = create_app()
resultados: list[tuple[str, bool, str]] = []
HOJE = date(2026, 10, 21)


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _evento(event_id: int = 1, cortesia: bool = False) -> CalendarEvent:
    return CalendarEvent(id=event_id, title="Verify 299b", is_cortesia_permuta=cortesia)


def _venda(
    principal: CalendarEvent,
    valor: str | None = "1000.00",
    recebido: str = "500.00",
    vencimento: date | None = HOJE + timedelta(days=10),
    motivo_fora: str | None = None,
) -> VendaResumo:
    return VendaResumo(
        principal=principal,
        eventos=(principal,),
        valor=Decimal(valor) if valor is not None else None,
        recebido=Decimal(recebido),
        data_do_grupo=HOJE + timedelta(days=12),
        vencimento=vencimento,
        vencimento_origem="politica",
        cliente="Cliente",
        motivo_fora=motivo_fora,
    )


def c1() -> None:
    evento = _evento()
    _garante(pode_copiar_cobranca(_venda(evento), evento, HOJE), "antes do vencimento não liberou")


def c2() -> None:
    evento = _evento()
    venda = _venda(evento, vencimento=None)
    _garante(pode_copiar_cobranca(venda, evento, HOJE), "sem vencimento não liberou")


def c3() -> None:
    evento = _evento()
    for dias in (0, -1, -30):
        venda = _venda(evento, vencimento=HOJE + timedelta(days=dias))
        _garante(pode_copiar_cobranca(venda, evento, HOJE), f"vencimento {dias:+d} dias não liberou")


def c4() -> None:
    evento = _evento()
    _garante(not pode_copiar_cobranca(_venda(evento, recebido="1000.00"), evento, HOJE), "quitada")
    _garante(not pode_copiar_cobranca(_venda(evento, recebido="999.50"), evento, HOJE), "folga")


def c5() -> None:
    cortesia = _evento(cortesia=True)
    _garante(not pode_copiar_cobranca(_venda(cortesia, recebido="0"), cortesia, HOJE), "cortesia")
    evento = _evento()
    for valor in (None, "0", "0.01"):
        venda = _venda(evento, valor=valor, recebido="0")
        _garante(not pode_copiar_cobranca(venda, evento, HOJE), f"valor {valor!r} liberou")
    fora = _venda(evento, motivo_fora="cancelado")
    _garante(not pode_copiar_cobranca(fora, evento, HOJE), "venda fora das listas liberou")


def c6() -> None:
    principal = _evento(1)
    outro = _evento(2)
    _garante(not pode_copiar_cobranca(_venda(principal), outro, HOJE), "o outro do grupo liberou")


def c7() -> None:
    from app.api.agenda_read import _compute_cobranca

    evento = _evento()
    venda = _venda(evento, vencimento=now_sp().date() + timedelta(days=10))
    with app.app_context():
        cobranca = _compute_cobranca(evento, venda)
    _garante(cobranca["enabled"] is True, f"enabled = {cobranca['enabled']!r}")
    _garante(cobranca["outstanding"] == 500.0, f"outstanding = {cobranca['outstanding']!r}")


print("verify_299b — cobrança a qualquer momento")
cenario("1. antes do vencimento libera (DEVE FALHAR na main antiga)", c1)
cenario("2. sem vencimento libera (DEVE FALHAR na main antiga)", c2)
cenario("3. vencida ou vencendo hoje continua liberando", c3)
cenario("4. quitada continua travada", c4)
cenario("5. cortesia, sem valor, simbólico e fora continuam travados", c5)
cenario("6. o outro evento do grupo continua travado", c6)
cenario("7. o JSON do detalhe leva enabled antes do vencimento", c7)

passou = sum(1 for _, ok, _ in resultados if ok)
print(f"\n{passou}/{len(resultados)} cenários OK")
for nome, ok, erro in resultados:
    if not ok:
        print(f"  - {nome}: {erro}")
sys.exit(0 if passou == len(resultados) else 1)
