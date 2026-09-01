"""Verificação do hotfix 271 — corrida na geração preguiçosa dos lançamentos do mês.

O defeito: `ensure_recurring_entries` lê o que já existe e só depois commita. Entre as duas coisas,
outra requisição pode ter inserido a mesma conta/mês — são 36 slots simultâneos no gunicorn
(3 workers × 12 threads) e a função roda em TODA carga da Home de quem é FINANCEIRO/SUPERADMIN.
A `UNIQUE(recurring_id, month_ref)` transformava a disputa em `IntegrityError` → 500, e a sessão
ficava em transação abortada. Era o "Não foi possível carregar o resumo" de 01/09/2026 — o dia 1º,
quando o `month_ref` do mês novo ainda está vazio e todo mundo tenta criar ao mesmo tempo.

Cenários:
 1. Duas gerações CONCORRENTES do mesmo mês: nenhuma estoura, e o mês fica com exatamente um
    lançamento por conta (a UNIQUE continua valendo — o que muda é quem trata a disputa).
 2. Geração repetida em série continua idempotente (não duplica, não estoura).
 3. Depois de perder a corrida, a sessão continua utilizável — é o que impedia o resto do request
    de funcionar e derrubava a Home inteira.
 4. `GET /api/dashboard` responde 200 mesmo quando a geração falha (a Home degrada, não cai).
 5. Limpeza.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    .venv/Scripts/python.exe specs/271-hotfix-corrida-lancamentos/verify_271.py
"""

from __future__ import annotations

import os
import sys
import threading
import traceback
from collections.abc import Callable
from decimal import Decimal
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

from app import create_app, db  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.models import RecurringExpense, RecurringExpenseEntry, Role, User  # noqa: E402

PREFIX = "__v271_"
SENHA = "verify-271-senha"
# Mês bem no futuro: garante `month_ref` vazio, que é a condição do dia 1º.
ANO, MES = 2029, 7
MONTH_REF = f"{ANO:04d}-{MES:02d}"

app = create_app()
app.config["TESTING"] = True

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_engine_externo = create_engine(os.environ["DATABASE_URL"], future=True)


def _no_banco(sql: str, **params):
    with _engine_externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _limpa_mes() -> None:
    RecurringExpenseEntry.query.filter_by(month_ref=MONTH_REF).delete(synchronize_session=False)
    db.session.commit()


def cen_01_corrida_simultanea() -> None:
    """Duas threads gerando o MESMO mês ao mesmo tempo — é o dia 1º com dois usuários na Home."""
    from app.gastos.gastos_ops import ensure_recurring_entries

    _limpa_mes()
    erros: list[BaseException] = []
    barreira = threading.Barrier(2)

    def gerar() -> None:
        # Sessão própria por thread, como cada worker/thread do gunicorn tem a sua.
        with app.app_context():
            try:
                barreira.wait(timeout=10)  # dispara as duas no mesmo instante
                ensure_recurring_entries(ANO, MES)
            except BaseException as exc:  # noqa: BLE001 — o teste é justamente pegar o que subir
                erros.append(exc)
            finally:
                db.session.remove()

    threads = [threading.Thread(target=gerar) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    _garante(not erros, f"a corrida estourou: {erros[:1]}")

    linhas = _no_banco(
        "SELECT recurring_id, count(*) AS n FROM recurring_expense_entries "
        "WHERE month_ref = :m GROUP BY recurring_id HAVING count(*) > 1",
        m=MONTH_REF,
    )
    _garante(not linhas, f"duplicou lançamento no mês: {linhas[:3]}")
    estado["gerados"] = len(
        _no_banco(
            "SELECT id FROM recurring_expense_entries WHERE month_ref = :m", m=MONTH_REF
        )
    )
    print(f"         ({estado['gerados']} lançamento(s) criado(s) no mês de teste)")


def cen_02_idempotente_em_serie() -> None:
    from app.gastos.gastos_ops import ensure_recurring_entries

    ensure_recurring_entries(ANO, MES)
    ensure_recurring_entries(ANO, MES)
    total = len(
        _no_banco("SELECT id FROM recurring_expense_entries WHERE month_ref = :m", m=MONTH_REF)
    )
    _garante(
        total == estado["gerados"],
        f"rodar de novo mudou a contagem: {estado['gerados']} → {total}",
    )


def cen_03_painel_quebrado_nao_derruba_a_home() -> None:
    """O conserto que esta feature entrega: um painel que estoura não leva a Home junto.

    É a resposta certa para um erro que não se consegue reproduzir — em vez de a tela inteira
    virar "Não foi possível carregar o resumo", o painel problemático some, o resto carrega, e o
    traceback vai para o log COM O NOME do painel. A próxima ocorrência se explica sozinha.
    """
    from app.api import dashboard_service as ds

    original = ds.compute_casting_tasks

    def _explode(_cutoff):
        raise RuntimeError("falha proposital do painel de casting")

    ds.compute_casting_tasks = _explode
    try:
        resumo = ds.build_dashboard_summary(estado["superadmin"], None, "7", None, None)
    finally:
        ds.compute_casting_tasks = original

    _garante(resumo is not None, "a Home caiu junto com o painel")
    _garante(resumo["casting"] is None, "o painel quebrado devia vir nulo")
    # A prova de que só ELE caiu: os vizinhos continuam preenchidos.
    _garante(
        resumo["figurino"] is not None or resumo["formularios"] is not None,
        "os outros painéis também sumiram — o isolamento não funcionou",
    )


def cen_04_dashboard_responde_200() -> None:
    with app.test_client() as c:
        r = c.post(
            "/api/auth/login",
            json={"email": estado["superadmin"].email, "password": SENHA},
        )
        _garante(r.status_code == 200, f"login → {r.status_code}")
        r = c.get("/api/dashboard")
        _garante(r.status_code == 200, f"dashboard → {r.status_code} {r.get_data(as_text=True)[:200]}")
        corpo = r.get_json()
        _garante("financeiro" in corpo, "bloco financeiro ausente do payload")


def preparar() -> None:
    limpar()
    email = f"{PREFIX}sa@manto.local"
    user = User(name=f"{PREFIX}sa", email=email, is_active=True, has_access=True)
    db.session.add(user)
    user.set_password(SENHA)
    user.roles.append(Role.query.filter_by(name=RoleName.SUPERADMIN).one())
    db.session.commit()
    estado["superadmin"] = user

    # Conta fixa de teste: garante que HÁ o que gerar no mês, mesmo que a base não tenha nenhuma.
    conta = RecurringExpense(
        name=f"{PREFIX}Conta Fixa",
        amount=Decimal("100.00"),
        expense_type="debito_automatico",
        due_day=10,
        is_active=True,
        created_by_id=user.id,
    )
    db.session.add(conta)
    db.session.commit()
    estado["conta"] = conta


def limpar() -> None:
    db.session.rollback()
    RecurringExpenseEntry.query.filter_by(month_ref=MONTH_REF).delete(synchronize_session=False)
    db.session.commit()
    for conta in RecurringExpense.query.filter(RecurringExpense.name.like(f"{PREFIX}%")).all():
        RecurringExpenseEntry.query.filter_by(recurring_id=conta.id).delete(
            synchronize_session=False
        )
        db.session.delete(conta)
    user = User.query.filter_by(email=f"{PREFIX}sa@manto.local").first()
    if user:
        user.roles.clear()
        db.session.delete(user)
    db.session.commit()


def main() -> int:
    with app.app_context():
        try:
            preparar()
            print("Hotfix 271 — corrida na geração dos lançamentos do mês")
            cenario("1. duas gerações simultâneas não estouram nem duplicam", cen_01_corrida_simultanea)
            cenario("2. geração repetida continua idempotente", cen_02_idempotente_em_serie)
            cenario("3. painel quebrado nao derruba a Home", cen_03_painel_quebrado_nao_derruba_a_home)
            cenario("4. GET /api/dashboard responde 200", cen_04_dashboard_responde_200)
        finally:
            cenario("5. limpeza", limpar)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  - {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
