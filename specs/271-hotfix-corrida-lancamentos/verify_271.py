"""Verificação do hotfix 271 — a Home degrada por painel, e a geração preguiçosa não corre.

Sintoma de 01/09/2026: "Não foi possível carregar o resumo" logo após o login. `GET /api/dashboard`
montava seis painéis sem barreira nenhuma — uma exceção em qualquer um virava 500 e a Home inteira
sumia. Agora cada painel passa por `_bloco()`: exceção → rollback + log com o nome → painel `None`.

Corrida: `ensure_recurring_entries` lê o que já existe e só depois commita. Entre as duas coisas,
outra requisição pode ter inserido a mesma conta/mês — são 36 slots simultâneos no gunicorn e a
função roda em TODA carga da Home de quem é FINANCEIRO/SUPERADMIN; no dia 1º o mês está vazio e
todo mundo tenta criar ao mesmo tempo. **Não há `UNIQUE(recurring_id, month_ref)` desde a 121**
(pagamento programado gera 2 lançamentos/mês), então a corrida não estourava: duplicava em
silêncio. A correção serializa a geração do mês com `pg_advisory_xact_lock(271, AAAAMM)`.

Cenários:
 1. Corrida forçada: uma transação segura o lock e insere um lançamento SEM commitar; a geração
    concorrente tem de esperar (tempo medido) e, depois, não duplicar aquela conta. Sem o lock ela
    não enxerga a linha não commitada e duplica.
 2. Geração repetida em série continua idempotente (não duplica, não estoura).
 3. Painel quebrado (monkeypatch em `compute_casting_tasks`) não derruba a Home: 200, `casting`
    vem `None`, os demais painéis vêm. Falhava antes da correção.
 4. `GET /api/dashboard` responde 200 no caminho normal.
 5. Limpeza.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    .venv/Scripts/python.exe specs/271-hotfix-corrida-lancamentos/verify_271.py
"""

from __future__ import annotations

import os
import sys
import threading
import time
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


def _conta_alvo() -> RecurringExpense:
    """Primeira conta fixa ativa que a geração criaria no mês de teste."""
    fixas = RecurringExpense.query.filter(
        RecurringExpense.is_active.is_(True),
        RecurringExpense.expense_type.in_(["debito_automatico", "assinatura"]),
        RecurringExpense.amount.isnot(None),
    ).order_by(RecurringExpense.id).all()
    for conta in fixas:
        if conta.occurrences_in_month(ANO, MES) > 0:
            return conta
    raise AssertionError("manto_local sem conta fixa ativa para o cenário")


def cen_01_corrida_simultanea() -> None:
    """Uma transação segura o lock com um lançamento não commitado; a geração tem de esperar."""
    from app.gastos.gastos_ops import ensure_recurring_entries

    _limpa_mes()
    with app.app_context():
        conta = _conta_alvo()
        alvo_id, alvo_valor = conta.id, conta.amount
        db.session.remove()

    lock_tomado = threading.Event()
    erros: list[BaseException] = []
    SEGURA_POR = 1.5

    def primeira_requisicao() -> None:
        # Simula quem chegou antes: já passou pela leitura, já inseriu, ainda não commitou.
        try:
            with _engine_externo.connect() as conn, conn.begin():
                conn.execute(text("SELECT pg_advisory_xact_lock(271, :m)"), {"m": ANO * 100 + MES})
                conn.execute(
                    text(
                        "INSERT INTO recurring_expense_entries "
                        "(recurring_id, month_ref, amount, due_date, status, created_at) "
                        "VALUES (:r, :m, :a, :d, 'registrado', now())"
                    ),
                    {"r": alvo_id, "m": MONTH_REF, "a": alvo_valor, "d": f"{MONTH_REF}-05"},
                )
                lock_tomado.set()
                time.sleep(SEGURA_POR)
        except BaseException as exc:  # noqa: BLE001
            erros.append(exc)
            lock_tomado.set()

    esperou: dict[str, float] = {}

    def segunda_requisicao() -> None:
        with app.app_context():
            try:
                lock_tomado.wait(timeout=10)
                t0 = time.perf_counter()
                ensure_recurring_entries(ANO, MES)
                esperou["s"] = time.perf_counter() - t0
            except BaseException as exc:  # noqa: BLE001 — o teste é justamente pegar o que subir
                erros.append(exc)
            finally:
                db.session.remove()

    threads = [threading.Thread(target=primeira_requisicao), threading.Thread(target=segunda_requisicao)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    _garante(not erros, f"a corrida estourou: {erros[:1]}")
    _garante(
        esperou.get("s", 0) >= SEGURA_POR * 0.6,
        f"a geração não esperou o lock (levou {esperou.get('s', 0):.2f}s; sem lock = duplicata)",
    )
    linhas = _no_banco(
        "SELECT count(*) AS n FROM recurring_expense_entries WHERE month_ref = :m AND recurring_id = :r",
        m=MONTH_REF, r=alvo_id,
    )
    _garante(linhas[0][0] == 1, f"conta {alvo_id} ficou com {linhas[0][0]} lançamento(s) no mês")
    duplicadas = _no_banco(
        "SELECT recurring_id, count(*) AS n FROM recurring_expense_entries "
        "WHERE month_ref = :m GROUP BY recurring_id HAVING count(*) > 1",
        m=MONTH_REF,
    )
    _garante(not duplicadas, f"duplicou lançamento no mês: {duplicadas[:3]}")
    estado["gerados"] = len(
        _no_banco("SELECT id FROM recurring_expense_entries WHERE month_ref = :m", m=MONTH_REF)
    )
    print(
        f"         (esperou {esperou['s']:.2f}s pelo lock; {estado['gerados']} lançamento(s) no mês)"
    )


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
            cenario("1. geração concorrente espera o lock e não duplica", cen_01_corrida_simultanea)
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
