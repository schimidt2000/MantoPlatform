"""Verificação da feature 314 — Gastos Extras na tela inteira, com filtros e as pagas recolhidas.

A tabela de cenários está na `spec.md` (seção "Verificação"). Escrito ANTES do núcleo (Princípio VIII):
a primeira rodada, sem `gastos_ops.situacao_do_gasto`, fica em `verify_314_primeira_falha.txt`.

Cenários:
 1. Financeiro pede `GET /api/gastos`: todo gasto traz `situacao` entre as cinco, e a contagem bate
    com o banco (conexão separada).
 2. Um gasto semeado por caso da regra (research.md D2) chega com a situação certa.
 3. A soma por situação dos itens do payload bate, centavo a centavo, com a MESMA regra escrita em SQL
    e rodada por conexão separada sobre `special_expenses` inteira (cada gasto num grupo só).
 4. Aprovar pela API dois "aguardando" (um com reembolso, outro sem desembolso): no GET seguinte um
    chega `a_pagar` e o outro `pago`.
 5. Usuário de Casting com 2 gastos próprios: recebe só os 2, com `situacao`, e sem `totals`.
 6. (DEVE FALHAR) o mesmo Casting não recebe os gastos do Financeiro nem o total da empresa, e
    aprovar o próprio gasto pendente é recusado (403).
 7. (DEVE FALHAR) mutação: com a regra trocada (pago no cadastro deixa de contar como pago), o
    cenário 2 cai. O oráculo é a tabela esperada daqui / o SQL do 3, nunca a função mutada.
 8. Limpeza: gastos `[verify314]`, o `AuditLog` deles e os usuários descartáveis somem
    (conferido por conexão separada). Roda sempre.

Rodar contra o manto_local (PowerShell, na raiz do worktree)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
    C:\\Users\\schim\\Desktop\\Manto_Platform\\.venv\\Scripts\\python.exe specs\\314-gastos-extras-filtros\\verify_314.py

Saída: 0 = tudo OK; 1 = algum cenário falhou; 2 = ambiente impróprio.
"""

from __future__ import annotations

import os
import sys
import traceback
from collections.abc import Callable
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):  # console do Windows em cp1252
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.gastos import gastos_ops  # noqa: E402
from app.models import AuditLog, Role, SpecialExpense, User  # noqa: E402

PREFIX = "__v314_"
MARCA = "[verify314]"
SENHA = "verify-314-senha"
CENTAVO = Decimal("0.01")

# Oráculo independente da função testada: os cinco valores e a regra D2 escritos de novo aqui.
SITUACOES = {"aguardando_aprovacao", "a_pagar", "no_banco", "pago", "rejeitado"}
SQL_SITUACAO = """
    CASE
        WHEN status = 'rejeitado' THEN 'rejeitado'
        WHEN status = 'pendente' THEN 'aguardando_aprovacao'
        WHEN paid_at_creation OR disbursement_type IS NULL OR disbursement_type = ''
             OR payment_status = 'pago' THEN 'pago'
        WHEN payment_status = 'no_banco' THEN 'no_banco'
        ELSE 'a_pagar'
    END
"""

# Um gasto por caso da regra: (apelido, status, desembolso, payment_status, paid_at_creation, esperado).
CASOS_FINANCEIRO = [
    ("aguardando", "pendente", "reembolso", "nao_pago", False, "aguardando_aprovacao"),
    ("pendente_ja_pago", "pendente", "fornecedor", "nao_pago", True, "aguardando_aprovacao"),
    ("a_pagar", "aprovado", "fornecedor", "nao_pago", False, "a_pagar"),
    ("no_banco", "aprovado", "reembolso", "no_banco", False, "no_banco"),
    ("pago_planilha", "aprovado", "fornecedor", "pago", False, "pago"),
    ("pago_cadastro", "aprovado", "fornecedor", "nao_pago", True, "pago"),
    ("sem_desembolso", "aprovado", None, "nao_pago", False, "pago"),
    ("rejeitado", "rejeitado", "reembolso", "nao_pago", False, "rejeitado"),
    ("aprovar_reembolso", "pendente", "reembolso", "nao_pago", False, "aguardando_aprovacao"),
    ("aprovar_sem", "pendente", None, "nao_pago", False, "aguardando_aprovacao"),
]
CASOS_CASTING = [
    ("casting_pendente", "pendente", "reembolso", "nao_pago", False, "aguardando_aprovacao"),
    ("casting_pago", "aprovado", "reembolso", "pago", False, "pago"),
]

app = create_app()
app.config["TESTING"] = True
app.config["RATELIMIT_ENABLED"] = False

resultados: list[tuple[str, bool, str]] = []
estado: dict = {"gastos": {}, "usuarios": {}, "cenario2_ok": False}

# Conexão separada: confirma o que foi COMITADO, não o que a sessão do teste tem em memória.
_engine_externo = create_engine(os.environ["DATABASE_URL"], future=True)


def _no_banco(sql: str, **params) -> list:
    """Lê pelo banco, por fora da sessão do app (o autoflush esconde falta de commit)."""
    with _engine_externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001 — harness: registra e segue
        with app.app_context():
            db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _centavos(valor) -> Decimal:
    return Decimal(str(valor)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


# ── semente ───────────────────────────────────────────────────────────────────────────────────
def _usuario(sufixo: str, papel: str) -> int:
    email = f"{PREFIX}{sufixo}@manto.local"
    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(name=f"{PREFIX}{sufixo}", email=email, is_active=True, has_access=True)
        db.session.add(user)
    user.set_password(SENHA)
    user.roles.clear()
    user.roles.append(Role.query.filter_by(name=papel).one())
    db.session.commit()
    return user.id


def _gasto(autor_id: int, caso: tuple) -> int:
    apelido, status, desembolso, pagamento, ja_pago, _esperado = caso
    gasto = SpecialExpense(
        description=f"{MARCA} {apelido}",
        category="Outros",
        amount=Decimal("123.45") + len(apelido),
        expense_date=date(2026, 10, 1),
        status=status,
        created_by_id=autor_id,
        payment_status=pagamento,
        paid_at_creation=ja_pago,
        disbursement_type=desembolso,
    )
    if desembolso == "reembolso":
        gasto.reimburse_user_id = autor_id
    elif desembolso == "fornecedor":
        gasto.supplier_name = f"{PREFIX}fornecedor"
    db.session.add(gasto)
    db.session.commit()
    return gasto.id


def semear() -> None:
    with app.app_context():
        _garante(
            app.config.get("MAIL_SUPPRESS_SEND") is True,
            "e-mail não está suprimido — ambiente impróprio",
        )
        fin = _usuario("financeiro", RoleName.FINANCEIRO)
        cas = _usuario("casting", RoleName.CASTING)
        estado["usuarios"] = {"financeiro": fin, "casting": cas}
        for caso in CASOS_FINANCEIRO:
            estado["gastos"][caso[0]] = _gasto(fin, caso)
        for caso in CASOS_CASTING:
            estado["gastos"][caso[0]] = _gasto(cas, caso)


# ── cliente HTTP (fora do app_context) ────────────────────────────────────────────────────────
def _cliente(apelido: str):
    c = app.test_client()
    r = c.post(
        "/api/auth/login", json={"email": f"{PREFIX}{apelido}@manto.local", "password": SENHA}
    )
    _garante(r.status_code == 200, f"login {apelido} → {r.status_code}")
    return c


def _lista(apelido: str) -> dict:
    r = _cliente(apelido).get("/api/gastos")
    _garante(r.status_code == 200, f"GET /api/gastos como {apelido} → {r.status_code}")
    return r.get_json()


def _por_id(payload: dict) -> dict[int, dict]:
    return {e["id"]: e for e in payload["expenses"]}


# ── cenários ──────────────────────────────────────────────────────────────────────────────────
def c1_todo_gasto_tem_situacao() -> None:
    payload = _lista("financeiro")
    sem = [e["id"] for e in payload["expenses"] if e.get("situacao") not in SITUACOES]
    _garante(not sem, f"gasto sem `situacao` válida: {sem[:5]} (de {len(payload['expenses'])})")
    total = _no_banco("SELECT count(*) FROM special_expenses")[0][0]
    _garante(
        len(payload["expenses"]) == total, f"payload {len(payload['expenses'])} × banco {total}"
    )


def _confere_casos() -> None:
    itens = _por_id(_lista("financeiro"))
    erros = []
    for apelido, *_resto, esperado in CASOS_FINANCEIRO:
        if apelido.startswith("aprovar_"):
            continue  # o cenário 4 muda estes dois
        recebido = itens.get(estado["gastos"][apelido], {}).get("situacao")
        if recebido != esperado:
            erros.append(f"{apelido}: {recebido} (esperado {esperado})")
    _garante(not erros, "; ".join(erros))


def c2_cada_caso_na_situacao_certa() -> None:
    _confere_casos()
    estado["cenario2_ok"] = True


def c3_soma_por_situacao_bate_com_o_sql() -> None:
    payload = _lista("financeiro")
    da_api: dict[str, list[Decimal]] = {}
    for e in payload["expenses"]:
        da_api.setdefault(e.get("situacao"), []).append(_centavos(e["amount"]))
    linhas = _no_banco(
        f"SELECT {SQL_SITUACAO} AS s, count(*), coalesce(sum(amount), 0) FROM special_expenses GROUP BY s"
    )
    do_banco = {s: (n, _centavos(t)) for s, n, t in linhas}
    api_resumo = {s: (len(v), sum(v, Decimal("0"))) for s, v in da_api.items()}
    _garante(api_resumo == do_banco, f"API {api_resumo} × SQL {do_banco}")
    _garante(
        sum(n for n, _ in do_banco.values()) == len(payload["expenses"]), "um gasto fora de grupo"
    )


def c4_aprovar_muda_a_situacao() -> None:
    fin = _cliente("financeiro")
    for apelido in ("aprovar_reembolso", "aprovar_sem"):
        r = fin.post(f"/api/gastos/{estado['gastos'][apelido]}/aprovar")
        _garante(
            r.status_code == 200,
            f"aprovar {apelido} → {r.status_code} {r.get_data(as_text=True)[:200]}",
        )
    status = dict(
        _no_banco(
            "SELECT id, status FROM special_expenses WHERE id IN (:a, :b)",
            a=estado["gastos"]["aprovar_reembolso"],
            b=estado["gastos"]["aprovar_sem"],
        )
    )
    _garante(set(status.values()) == {"aprovado"}, f"aprovação não gravou: {status}")
    itens = _por_id(_lista("financeiro"))
    reembolso = itens[estado["gastos"]["aprovar_reembolso"]].get("situacao")
    sem = itens[estado["gastos"]["aprovar_sem"]].get("situacao")
    _garante(reembolso == "a_pagar", f"aprovado com reembolso chegou {reembolso}")
    _garante(sem == "pago", f"aprovado sem desembolso chegou {sem}")


def c5_casting_ve_so_os_seus() -> None:
    payload = _lista("casting")
    meus = {estado["gastos"]["casting_pendente"], estado["gastos"]["casting_pago"]}
    ids = {e["id"] for e in payload["expenses"]}
    no_banco = {
        r[0]
        for r in _no_banco(
            "SELECT id FROM special_expenses WHERE created_by_id = :u",
            u=estado["usuarios"]["casting"],
        )
    }
    _garante(
        ids == meus == no_banco, f"Casting recebeu {sorted(ids)}; dele no banco {sorted(no_banco)}"
    )
    _garante("totals" not in payload, "Casting recebeu `totals`")
    situacoes = {e["id"]: e.get("situacao") for e in payload["expenses"]}
    esperado = {
        estado["gastos"]["casting_pendente"]: "aguardando_aprovacao",
        estado["gastos"]["casting_pago"]: "pago",
    }
    _garante(situacoes == esperado, f"situações do Casting {situacoes}")


def c6_casting_nao_alcanca_o_alheio() -> None:
    cas = _cliente("casting")
    payload = cas.get("/api/gastos").get_json()
    alheios = {estado["gastos"][caso[0]] for caso in CASOS_FINANCEIRO}
    vazou = alheios & {e["id"] for e in payload["expenses"]}
    _garante(not vazou, f"gasto do Financeiro vazou para o Casting: {sorted(vazou)}")
    _garante("totals" not in payload, "total da empresa vazou para o Casting")
    r = cas.post(f"/api/gastos/{estado['gastos']['casting_pendente']}/aprovar")
    _garante(r.status_code == 403, f"Casting aprovou o próprio gasto → {r.status_code}")
    status = _no_banco(
        "SELECT status FROM special_expenses WHERE id = :i", i=estado["gastos"]["casting_pendente"]
    )[0][0]
    _garante(status == "pendente", f"a recusa gravou mesmo assim: {status}")


def _situacao_quebrada(expense: SpecialExpense) -> str:
    """A regra com um defeito plantado: o pago no cadastro deixa de contar como pago."""
    if expense.status == "rejeitado":
        return "rejeitado"
    if expense.status == "pendente":
        return "aguardando_aprovacao"
    if not expense.disbursement_type or expense.payment_status == "pago":
        return "pago"
    if expense.payment_status == "no_banco":
        return "no_banco"
    return "a_pagar"


def c7_mutacao_derruba_o_cenario_2() -> None:
    _garante(estado["cenario2_ok"], "o cenário 2 não passou sem mutação — a mutação não prova nada")
    original = getattr(gastos_ops, "situacao_do_gasto", None)
    _garante(original is not None, "gastos_ops.situacao_do_gasto não existe")
    gastos_ops.situacao_do_gasto = _situacao_quebrada
    try:
        _deve_cair(_confere_casos, "cenário 2", "pago_cadastro")
        # O oráculo independente (a regra em SQL) também tem de acusar: o pago no cadastro semeado
        # sai de "pago" e entra em "a_pagar" na soma da API, e o SQL não muda.
        _deve_cair(c3_soma_por_situacao_bate_com_o_sql, "cenário 3", "SQL")
    finally:
        gastos_ops.situacao_do_gasto = original


def _deve_cair(cenario_fn: Callable[[], None], nome: str, motivo: str) -> None:
    """Roda um cenário que TEM de falhar sob a mutação, e pelo motivo esperado."""
    try:
        cenario_fn()
    except AssertionError as exc:
        _garante(motivo in str(exc), f"{nome} caiu, mas pelo motivo errado: {exc}")
        return
    raise AssertionError(f"com a regra quebrada o {nome} continuou verde — o verify não morde")


def limpar() -> None:
    with app.app_context():
        db.session.rollback()
        ids = [
            g.id
            for g in SpecialExpense.query.filter(SpecialExpense.description.like(f"{MARCA}%")).all()
        ]
        if ids:
            AuditLog.query.filter(
                AuditLog.entity_type == "gasto", AuditLog.entity_id.in_(ids)
            ).delete(synchronize_session=False)
            SpecialExpense.query.filter(SpecialExpense.id.in_(ids)).delete(
                synchronize_session=False
            )
        for user in User.query.filter(User.email.like(f"{PREFIX}%")).all():
            user.roles.clear()
            db.session.delete(user)
        db.session.commit()


def c8_limpeza() -> None:
    limpar()
    restam_gastos = _no_banco(
        "SELECT count(*) FROM special_expenses WHERE description LIKE :m", m=f"{MARCA}%"
    )[0][0]
    restam_users = _no_banco("SELECT count(*) FROM users WHERE email LIKE :p", p=f"{PREFIX}%")[0][0]
    ids = list(estado["gastos"].values()) or [0]
    restam_logs = _no_banco(
        "SELECT count(*) FROM audit_logs WHERE entity_type = 'gasto' AND entity_id = ANY(:ids)",
        ids=ids,
    )[0][0]
    _garante(
        restam_gastos == restam_users == restam_logs == 0,
        f"sobrou: {restam_gastos} gastos, {restam_users} usuários, {restam_logs} logs",
    )


def main() -> int:
    print("verify_314 — Gastos Extras: situação do gasto e RBAC da lista")
    try:
        limpar()  # resto de uma rodada interrompida
        semear()
    except Exception as exc:  # noqa: BLE001 — sem semente não há o que verificar
        print(f"  AMBIENTE  {exc}")
        limpar()
        return 2
    try:
        cenario("1 todo gasto tem situação e a contagem bate", c1_todo_gasto_tem_situacao)
        cenario("2 cada caso da regra na situação certa", c2_cada_caso_na_situacao_certa)
        cenario("3 soma por situação = regra em SQL", c3_soma_por_situacao_bate_com_o_sql)
        cenario("4 aprovar muda a situação", c4_aprovar_muda_a_situacao)
        cenario("5 Casting vê só os seus, sem totals", c5_casting_ve_so_os_seus)
        cenario("6 (deve falhar) Casting não alcança o alheio", c6_casting_nao_alcanca_o_alheio)
        cenario("7 (deve falhar) mutação derruba o cenário 2", c7_mutacao_derruba_o_cenario_2)
    finally:
        cenario("8 limpeza", c8_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
