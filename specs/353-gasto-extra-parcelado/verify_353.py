"""Verificação da feature 353 — gasto extra parcelado.

Cenários (spec §Verificação):
 1. Figurino lança gasto com 2 parcelas: valor = soma; 2 parcelas; 1 nota; pendente.
 2. Validações: uma parcela, sem data, valor zero, com "já pago", sem desembolso, multa, 25 parcelas → 400 no campo.
 3. Aprovado: a Planilha do mês traz um item por parcela; o gasto não parcelado segue um item.
 4. Parcela de outro mês fica na Planilha do mês dela; parcela vencida de mês anterior vem nos atrasados.
 5. Marcar parcela (set-status e lote): só ela muda; situação do gasto derivada; desmarcar destrava.
 6. Financeiro altera parcela não paga e aprova: valor e Planilha seguem.
 7. Parcela paga não muda nem sai; nova parcela entra; PATCH sem `parcelas` exige valor = soma.
 8. Desligar parcelas: com parcela paga recusa; sem paga volta a um pagamento.
 9. DRE: o gasto inteiro pela "Data do gasto".
10. Figurino tenta editar parcelas, marcar parcela e lote de parcelas → 403.          (DEVE falhar)
11. Limpeza.

E-mail dublado. Requisições HTTP FORA do `app_context`; asserções de escrita por conexão separada. Datas em 2031
para isolar a Planilha; os atrasados usam outubro/2026 (o mês corrente é o de hoje).

Rodar contra o espelho da feature (PowerShell, na raiz)::

    $env:DATABASE_URL = '<url do manto_352>'; $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
    .venv\\Scripts\\python.exe specs\\353-gasto-extra-parcelado\\verify_353.py
"""

from __future__ import annotations

import io
import json
import os
import sys
import traceback
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, email_service, limiter  # noqa: E402
from app.gastos import gastos_ops  # noqa: E402
from app.models import Fornecedor, Role, SpecialExpense, User  # noqa: E402

PREFIX = "__v353_"
SENHA = "verify-353-senha"
FORNECEDOR = f"{PREFIX}Fornecedor Parcelado"

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_externo = create_engine(os.environ["DATABASE_URL"], future=True)

email_service._send = lambda *a, **k: True
email_service.send_async = lambda *a, **k: None
gastos_ops.send_async = lambda *a, **k: None


def _no_banco(sql: str, **params):
    with _externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def _um(sql: str, **params):
    linhas = _no_banco(sql, **params)
    return linhas[0] if linhas else None


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001
        with app.app_context():
            db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


# ── preparação ──────────────────────────────────────────────────────────────────────────────────


def _usuario(sufixo: str, papel: str) -> int:
    user = User(
        name=f"{PREFIX}{sufixo}",
        email=f"{PREFIX}{sufixo}@manto.local",
        is_active=True,
        has_access=True,
    )
    user.set_password(SENHA)
    user.roles.append(Role.query.filter_by(name=papel).one())
    db.session.add(user)
    db.session.commit()
    return user.id


def preparar() -> None:
    with app.app_context():
        limpar()
        estado["fin"] = _usuario("fin", "FINANCEIRO")
        estado["fig"] = _usuario("fig", "FIGURINO")


def limpar() -> None:
    db.session.rollback()
    pasta = Path(app.config["UPLOAD_EXPENSES"])
    for g in SpecialExpense.query.filter(SpecialExpense.description.like(f"{PREFIX}%")).all():
        if g.receipt_path:
            (pasta / Path(g.receipt_path).name).unlink(missing_ok=True)
        db.session.delete(g)
    db.session.flush()
    Fornecedor.query.filter(Fornecedor.nome_normalizado.like("v353 %")).delete(
        synchronize_session=False
    )
    for user in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        user.roles.clear()
        db.session.delete(user)
    db.session.commit()


def _cliente_http(chave: str):
    c = app.test_client()
    r = c.post("/api/auth/login", json={"email": f"{PREFIX}{chave}@manto.local", "password": SENHA})
    _garante(r.status_code == 200, f"login {chave} → {r.status_code}")
    return c


def _lancar(descricao: str, parcelas: list[dict] | None, *, esperado: int = 201, **extra) -> dict:
    form = {
        "description": f"{PREFIX}{descricao}",
        "category": extra.pop("category", "Figurino"),
        "amount": extra.pop("amount", "1.00"),
        "expense_date": extra.pop("expense_date", "2031-03-15"),
        "disbursement_type": extra.pop("disbursement_type", "fornecedor"),
        "supplier_name": FORNECEDOR,
        "supplier_pix": "pix-parcelado",
        "receipt": (io.BytesIO(b"%PDF-1.4\n%%EOF\n"), "nota.pdf"),
        **extra,
    }
    if parcelas is not None:
        form["parcelas"] = json.dumps(parcelas)
    r = _cliente_http("fig").post("/api/gastos", data=form, content_type="multipart/form-data")
    _garante(
        r.status_code == esperado,
        f"POST /api/gastos → {r.status_code} {r.get_data(as_text=True)[:300]}",
    )
    return r.get_json()


def _parcelas(gasto_id: int) -> list:
    return _no_banco(
        "SELECT id, numero, data, valor, payment_status FROM gasto_parcelas WHERE special_expense_id = :g ORDER BY numero",
        g=gasto_id,
    )


def _gasto(gasto_id: int):
    return _um(
        "SELECT amount, status, payment_status, receipt_path FROM special_expenses WHERE id = :g",
        g=gasto_id,
    )


def _planilha(mes: str | None = None) -> list[dict]:
    url = "/api/financeiro/pagamentos" + (f"?month={mes}" if mes else "")
    r = _cliente_http("fin").get(url)
    _garante(r.status_code == 200, f"planilha {mes} → {r.status_code}")
    return r.get_json()["items"]


def _do_gasto(
    itens: list[dict], parcela_ids: set[int], gasto_id: int
) -> tuple[list[dict], list[dict]]:
    das_parcelas = [
        i for i in itens if i["type"] == "expense_parcela" and int(i["id"]) in parcela_ids
    ]
    inteiro = [i for i in itens if i["type"] == "expense" and int(i["id"]) == gasto_id]
    return das_parcelas, inteiro


def _corpo_edicao(gasto_id: int, parcelas: list[dict] | None, **troca) -> dict:
    corpo = {
        "description": f"{PREFIX}{troca.pop('descricao', 'editado')}",
        "category": "Figurino",
        "amount": troca.pop("amount", 1),
        "expense_date": "2031-03-15",
        "disbursement_type": "fornecedor",
        "supplier_name": FORNECEDOR,
        "supplier_pix": "pix-parcelado",
        **troca,
    }
    if parcelas is not None:
        corpo["parcelas"] = parcelas
    return corpo


def _status(chave: str, tipo: str, item_id: int, status: str) -> int:
    corpo = {"item_type": tipo, "item_id": item_id, "status": status}
    return (
        _cliente_http(chave).post("/api/financeiro/pagamentos/set-status", json=corpo).status_code
    )


def _situacao(gasto_id: int) -> str:
    gastos = _cliente_http("fin").get("/api/gastos").get_json()["expenses"]
    return next(g for g in gastos if g["id"] == gasto_id)["situacao"]


# ───────────────────────────── História 1 ─────────────────────────────


def cen_01_lancar() -> None:
    g = _lancar(
        "adao", [{"data": "2031-03-20", "valor": 500}, {"data": "2031-03-30", "valor": 700}]
    )
    linha = _gasto(g["id"])
    _garante(Decimal(linha[0]) == Decimal("1200.00"), f"valor do gasto {linha[0]}")
    _garante(linha[1] == "pendente" and linha[3], f"status/nota: {linha}")
    parcelas = _parcelas(g["id"])
    _garante(
        [(p[1], str(p[2]), Decimal(p[3]), p[4]) for p in parcelas]
        == [
            (1, "2031-03-20", Decimal("500.00"), "nao_pago"),
            (2, "2031-03-30", Decimal("700.00"), "nao_pago"),
        ],
        f"parcelas gravadas: {parcelas}",
    )
    _garante(len(g.get("parcelas") or []) == 2, "resposta sem parcelas")
    estado["g1"], estado["p1"], estado["p2"] = g["id"], parcelas[0][0], parcelas[1][0]


def cen_02_validacoes() -> None:
    casos = [
        ("uma", [{"data": "2031-03-20", "valor": 500}], {}, "parcelas"),
        (
            "sem data",
            [{"data": "2031-03-20", "valor": 500}, {"data": "", "valor": 10}],
            {},
            "parcelas.1.data",
        ),
        (
            "valor zero",
            [{"data": "2031-03-20", "valor": 0}, {"data": "2031-03-21", "valor": 10}],
            {},
            "parcelas.0.valor",
        ),
        (
            "ja pago",
            [{"data": "2031-03-20", "valor": 1}, {"data": "2031-03-21", "valor": 1}],
            {"paid_at_creation": "true"},
            "parcelas",
        ),
        (
            "sem desembolso",
            [{"data": "2031-03-20", "valor": 1}, {"data": "2031-03-21", "valor": 1}],
            {"disbursement_type": ""},
            "parcelas",
        ),
        (
            "multa",
            [{"data": "2031-03-20", "valor": 1}, {"data": "2031-03-21", "valor": 1}],
            {"category": "Multa de cancelamento"},
            "parcelas",
        ),
        ("vinte e cinco", [{"data": "2031-03-20", "valor": 1}] * 25, {}, "parcelas"),
    ]
    for nome, parcelas, extra, campo in casos:
        j = _lancar(f"invalido {nome}", parcelas, esperado=400, **extra)
        _garante(campo in (j["error"].get("fields") or {}), f"{nome}: campo {campo} ausente em {j}")
    sobrou = _um(
        "SELECT count(*) FROM special_expenses WHERE description LIKE :p", p=f"{PREFIX}invalido%"
    )[0]
    _garante(sobrou == 0, f"{sobrou} gastos inválidos gravados")


# ───────────────────────────── História 2 ─────────────────────────────


def _aprovar(gasto_id: int) -> None:
    r = _cliente_http("fin").post(f"/api/gastos/{gasto_id}/aprovar")
    _garante(r.status_code == 200, f"aprovar {gasto_id} → {r.status_code}")


def cen_03_planilha() -> None:
    _aprovar(estado["g1"])
    simples = _lancar("simples", None, amount="80.00", expense_date="2031-03-10")
    _aprovar(simples["id"])
    itens = _planilha("2031-03")
    parcelas, inteiro = _do_gasto(itens, {estado["p1"], estado["p2"]}, estado["g1"])
    _garante(not inteiro, "gasto parcelado veio também inteiro")
    _garante(
        sorted((i["date"][:10], i["amount"]) for i in parcelas)
        == [("2031-03-20", 500.0), ("2031-03-30", 700.0)],
        f"itens das parcelas: {parcelas}",
    )
    _garante(
        all("Parcela" in (i.get("sublabel") or "") and "de 2" in i["sublabel"] for i in parcelas),
        "sem 'Parcela N de 2'",
    )
    so_um = [i for i in itens if i["type"] == "expense" and int(i["id"]) == simples["id"]]
    _garante(len(so_um) == 1 and so_um[0]["amount"] == 80.0, f"gasto simples: {so_um}")


def cen_04_outro_mes_e_atrasados() -> None:
    g = _lancar(
        "dois meses",
        [{"data": "2031-03-25", "valor": 100}, {"data": "2031-04-05", "valor": 200}],
        expense_date="2031-03-25",
    )
    _aprovar(g["id"])
    ids = {p[0] for p in _parcelas(g["id"])}
    marco, _ = _do_gasto(_planilha("2031-03"), ids, g["id"])
    abril, _ = _do_gasto(_planilha("2031-04"), ids, g["id"])
    _garante([i["date"][:10] for i in marco] == ["2031-03-25"], f"março: {marco}")
    _garante([i["date"][:10] for i in abril] == ["2031-04-05"], f"abril: {abril}")
    estado["g_meses"] = g["id"]
    velho = _lancar(
        "atrasado",
        [{"data": "2026-10-20", "valor": 50}, {"data": "2026-12-20", "valor": 60}],
        expense_date="2026-10-15",
    )
    _aprovar(velho["id"])
    ids = {p[0] for p in _parcelas(velho["id"])}
    atuais, _ = _do_gasto(_planilha(), ids, velho["id"])
    _garante(
        len(atuais) == 1
        and atuais[0]["date"][:10] == "2026-10-20"
        and atuais[0].get("de_mes_anterior"),
        f"atrasado no mês atual: {atuais}",
    )


def cen_05_marcar() -> None:
    g1, p1, p2 = estado["g1"], estado["p1"], estado["p2"]
    _garante(_status("fin", "expense_parcela", p1, "pago") == 200, "set-status p1")
    _garante([p[4] for p in _parcelas(g1)] == ["pago", "nao_pago"], "p1 pago, p2 intacta")
    _garante(_gasto(g1)[2] == "nao_pago" and _situacao(g1) == "a_pagar", "derivado com uma paga")
    r = _cliente_http("fin").post(
        "/api/financeiro/pagamentos/bulk-action",
        json={"action": "no_banco", "parcela_ids": [p2], "month": "2031-03"},
    )
    _garante(
        r.status_code == 200 and r.get_json()["changed"] == 1,
        f"lote → {r.status_code} {r.get_data(as_text=True)[:200]}",
    )
    _garante(_gasto(g1)[2] == "no_banco" and _situacao(g1) == "no_banco", "derivado no banco")
    _garante(_status("fin", "expense_parcela", p2, "pago") == 200, "set-status p2")
    _garante(_gasto(g1)[2] == "pago" and _situacao(g1) == "pago", "derivado pago")
    _garante(_status("fin", "expense_parcela", p2, "nao_pago") == 200, "desmarcar p2")
    _garante([p[4] for p in _parcelas(g1)] == ["pago", "nao_pago"], "desmarcar não voltou")


# ───────────────────────────── História 3 ─────────────────────────────


def _patch(chave: str, gasto_id: int, corpo: dict):
    return _cliente_http(chave).patch(f"/api/gastos/{gasto_id}", json=corpo)


def cen_06_alterar_e_aprovar() -> None:
    g = _lancar(
        "alterar", [{"data": "2031-03-20", "valor": 500}, {"data": "2031-03-30", "valor": 700}]
    )
    p = _parcelas(g["id"])
    parcelas = [
        {"id": p[0][0], "data": "2031-03-20", "valor": 500},
        {"id": p[1][0], "data": "2031-04-01", "valor": 800},
    ]
    r = _patch(
        "fin", g["id"], {**_corpo_edicao(g["id"], parcelas, descricao="alterar"), "aprovar": True}
    )
    _garante(r.status_code == 200, f"PATCH → {r.status_code} {r.get_data(as_text=True)[:300]}")
    linha = _gasto(g["id"])
    _garante(Decimal(linha[0]) == Decimal("1300.00") and linha[1] == "aprovado", f"gasto: {linha}")
    novas = _parcelas(g["id"])
    _garante(
        novas[1][0] == p[1][0] and str(novas[1][2]) == "2031-04-01",
        f"parcela 2 não atualizou no lugar: {novas}",
    )
    abril, _ = _do_gasto(_planilha("2031-04"), {novas[1][0]}, g["id"])
    _garante(len(abril) == 1 and abril[0]["amount"] == 800.0, f"Planilha de abril: {abril}")


def cen_07_paga_trava() -> None:
    g1, p1, p2 = estado["g1"], estado["p1"], estado["p2"]
    base = [
        {"id": p1, "data": "2031-03-20", "valor": 500},
        {"id": p2, "data": "2031-03-30", "valor": 700},
    ]
    r = _patch("fin", g1, _corpo_edicao(g1, [{**base[0], "valor": 450}, base[1]], descricao="adao"))
    _garante(
        r.status_code == 400 and "parcelas.0.valor" in r.get_json()["error"]["fields"],
        f"alterar paga: {r.status_code}",
    )
    r = _patch(
        "fin",
        g1,
        _corpo_edicao(g1, [base[1], {"data": "2031-03-31", "valor": 100}], descricao="adao"),
    )
    _garante(
        r.status_code == 400 and "parcelas" in r.get_json()["error"]["fields"],
        f"remover paga: {r.status_code}",
    )
    _garante(
        [(p[0], Decimal(p[3])) for p in _parcelas(g1)]
        == [(p1, Decimal("500.00")), (p2, Decimal("700.00"))],
        "recusa gravou",
    )
    r = _patch(
        "fin",
        g1,
        _corpo_edicao(g1, [*base, {"data": "2031-03-31", "valor": 100}], descricao="adao"),
    )
    _garante(r.status_code == 200, f"adicionar → {r.status_code} {r.get_data(as_text=True)[:300]}")
    parcelas = _parcelas(g1)
    _garante(
        len(parcelas) == 3 and parcelas[0][0] == p1 and parcelas[0][4] == "pago",
        f"após adicionar: {parcelas}",
    )
    _garante(Decimal(_gasto(g1)[0]) == Decimal("1300.00"), "total não cresceu")
    r = _patch("fin", g1, _corpo_edicao(g1, None, descricao="adao", amount=999))
    _garante(
        r.status_code == 400 and "amount" in r.get_json()["error"]["fields"],
        f"sem parcelas e valor errado: {r.status_code}",
    )
    r = _patch("fin", g1, _corpo_edicao(g1, None, descricao="adao", amount=1300))
    _garante(
        r.status_code == 200 and len(_parcelas(g1)) == 3,
        f"sem parcelas e valor certo: {r.status_code}",
    )


def cen_08_desligar() -> None:
    r = _patch("fin", estado["g1"], _corpo_edicao(estado["g1"], [], descricao="adao", amount=1300))
    _garante(
        r.status_code == 400 and "parcelas" in r.get_json()["error"]["fields"],
        f"desligar com paga: {r.status_code}",
    )
    g = _lancar(
        "desligar", [{"data": "2031-03-20", "valor": 10}, {"data": "2031-03-21", "valor": 20}]
    )
    r = _patch("fin", g["id"], _corpo_edicao(g["id"], [], descricao="desligar", amount=999))
    _garante(r.status_code == 200, f"desligar → {r.status_code} {r.get_data(as_text=True)[:300]}")
    _garante(
        not _parcelas(g["id"]) and Decimal(_gasto(g["id"])[0]) == Decimal("999.00"),
        "não voltou a um pagamento",
    )


def cen_09_dre() -> None:
    from app.financeiro.dre_ops import gastos_extras_do_periodo

    with app.app_context():
        marco = gastos_extras_do_periodo(date(2031, 3, 1), date(2031, 3, 31))
        abril = gastos_extras_do_periodo(date(2031, 4, 1), date(2031, 4, 30))
    # Março: g1 (1300) + simples (80) + "dois meses" (300, data 25/03) + "alterar" (1300). Abril: nada dos gastos.
    _garante(marco == Decimal("2980.00"), f"DRE março {marco}")
    _garante(abril == Decimal("0"), f"DRE abril {abril}")


def cen_10_figurino_nao_mexe() -> None:
    g1 = estado["g1"]
    antes = _parcelas(g1)
    r = _patch(
        "fig",
        g1,
        _corpo_edicao(g1, [{"data": "2031-03-20", "valor": 1}, {"data": "2031-03-21", "valor": 1}]),
    )
    codigos = [
        r.status_code,
        _status("fig", "expense_parcela", estado["p2"], "pago"),
        _cliente_http("fig")
        .post(
            "/api/financeiro/pagamentos/bulk-action",
            json={"action": "pago", "parcela_ids": [estado["p2"]]},
        )
        .status_code,
    ]
    _garante(codigos == [403, 403, 403], f"esperado 403: {codigos}")
    _garante(_parcelas(g1) == antes, "Figurino mexeu nas parcelas")


def cen_11_limpeza() -> None:
    with app.app_context():
        limpar()
    _garante(
        _um("SELECT count(*) FROM special_expenses WHERE description LIKE :p", p=f"{PREFIX}%")[0]
        == 0,
        "gasto sobrou",
    )
    _garante(
        _um(
            "SELECT count(*) FROM gasto_parcelas p LEFT JOIN special_expenses s ON s.id = p.special_expense_id WHERE s.id IS NULL"
        )[0]
        == 0,
        "parcela órfã",
    )
    _garante(
        _um("SELECT count(*) FROM users WHERE email LIKE :p", p=f"{PREFIX}%")[0] == 0,
        "usuário sobrou",
    )


def main() -> int:
    print("Feature 353 — gasto extra parcelado")
    passos = [
        ("1. lançar com 2 parcelas", cen_01_lancar),
        ("2. validações no campo", cen_02_validacoes),
        ("3. um item por parcela na Planilha", cen_03_planilha),
        ("4. outro mês e atrasados", cen_04_outro_mes_e_atrasados),
        ("5. marcar parcela e situação derivada", cen_05_marcar),
        ("6. alterar parcela e aprovar", cen_06_alterar_e_aprovar),
        ("7. parcela paga trava", cen_07_paga_trava),
        ("8. desligar parcelas", cen_08_desligar),
        ("9. DRE pela data do gasto", cen_09_dre),
        ("10. Figurino não mexe (DEVE falhar)", cen_10_figurino_nao_mexe),
    ]
    try:
        preparar()
        for nome, fn in passos:
            cenario(nome, fn)
    finally:
        cenario("11. limpeza", cen_11_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  ✗ {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
