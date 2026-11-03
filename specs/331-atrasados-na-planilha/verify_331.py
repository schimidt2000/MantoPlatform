"""Verificação da correção 331 — o que ficou em aberto vem para o mês atual da Planilha de Pagamentos.

Cenários (spec §Verificação):
 1. COMERCIAL recebe 403 na planilha.                                      (DEVE falhar se vazar)
 2. O mês atual traz os itens em aberto de antes, com `de_mes_anterior`, `mes_origem` e
    `dias_em_atraso` coerentes.                                            (DEVE falhar no antigo)
 3. Cada item que vem de antes é o MESMO item da planilha do mês dele (id, data, valor, situação),
    e todo item em aberto e vencido das planilhas de maio/2026 até o mês passado aparece.
 4. Nada de antes de maio/2026 vem (salários de abril, comissões do ciclo de março).
 5. Mês passado e mês seguinte não recebem item de antes.
 6. `totals` do mês atual somam os itens que vêm de antes; `totals.anteriores` bate com eles.
 7. Abrir o mês atual não grava nada nos meses anteriores, e a DRE do mês passado sai idêntica.
 8. Marcar pago um cachê de outro mês pela tela do mês atual grava (conexão separada), tira o
    item do mês atual e o mês de origem passa a mostrá-lo pago.
 9. CSV do mês atual traz os cachês em aberto de antes; o do mês de origem só os dele.
10. Limpeza (situação do cachê restaurada, usuários descartáveis apagados).

O relógio é o de hoje em São Paulo: o "mês atual" sai de `now_sp()`, e o espelho precisa ter item
em aberto num mês anterior (em 03/11/2026: cachês e salários de outubro).

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
    C:\\Users\\schim\\Desktop\\Manto_Platform\\.venv\\Scripts\\python.exe specs\\331-atrasados-na-planilha\\verify_331.py
"""

from __future__ import annotations

import csv
import io
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

from app import create_app, db, limiter  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import Role, User  # noqa: E402

PREFIX = "__v331_"
SENHA = "verify-331-senha"
CORTE = "2026-05"
ABERTOS = ("nao_pago", "no_banco")

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_externo = create_engine(os.environ["DATABASE_URL"], future=True)


def _no_banco(sql: str, **params):
    with _externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


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


# ── apoio ───────────────────────────────────────────────────────────────────────────────────────


def _mes(base: str, delta: int) -> str:
    ano, mes = int(base[:4]), int(base[5:7]) - 1 + delta
    return f"{ano + mes // 12:04d}-{mes % 12 + 1:02d}"


def _meses_entre(inicio: str, fim_exclusivo: str) -> list[str]:
    meses, m = [], inicio
    while m < fim_exclusivo:
        meses.append(m)
        m = _mes(m, 1)
    return meses


def _chave(item: dict) -> tuple[str, str]:
    return (item["type"], str(item["id"]))


def _cents(valor: float) -> Decimal:
    return Decimal(str(valor)).quantize(Decimal("0.01"))


def _soma(itens: list[dict]) -> Decimal:
    return sum((_cents(i["amount"]) for i in itens), Decimal("0.00"))


def _usuario(sufixo: str, *papeis: str) -> int:
    user = User(
        name=f"{PREFIX}{sufixo}",
        email=f"{PREFIX}{sufixo}@manto.local",
        is_active=True,
        has_access=True,
    )
    user.set_password(SENHA)
    for p in papeis:
        user.roles.append(Role.query.filter_by(name=p).one())
    db.session.add(user)
    db.session.commit()
    return user.id


def _cliente_http(sufixo: str):
    c = app.test_client()
    r = c.post(
        "/api/auth/login", json={"email": f"{PREFIX}{sufixo}@manto.local", "password": SENHA}
    )
    _garante(r.status_code == 200, f"login {sufixo} → {r.status_code}")
    return c


def _planilha(mes: str | None = None) -> dict:
    url = "/api/financeiro/pagamentos" + (f"?month={mes}" if mes else "")
    r = estado["fin_http"].get(url)
    _garante(r.status_code == 200, f"GET {url} → {r.status_code}")
    return r.get_json()


def _anteriores(payload: dict) -> list[dict]:
    return [i for i in payload["items"] if i.get("de_mes_anterior")]


def _csv(mes: str | None = None) -> list[list[str]]:
    url = "/api/financeiro/pagamentos/export" + (f"?month={mes}" if mes else "")
    r = estado["fin_http"].get(url)
    _garante(r.status_code == 200, f"GET {url} → {r.status_code}")
    linhas = list(csv.reader(io.StringIO(r.get_data(as_text=True))))
    return linhas[1:]


def _foto_dos_meses_anteriores(inicio_do_mes: date) -> list[tuple]:
    """Tudo que a planilha lê nos meses anteriores, pela conexão separada."""
    mes = inicio_do_mes.strftime("%Y-%m")
    return _no_banco(
        """
        SELECT 'sal', id::text, payment_status, amount::text, month_ref FROM salary_payments WHERE month_ref < :mes
        UNION ALL
        SELECT 'role', r.id::text, r.payment_status, coalesce(r.cache_value, 0)::text, to_char(e.start_at, 'YYYY-MM')
          FROM event_roles r JOIN calendar_events e ON e.id = r.event_id WHERE e.start_at < :inicio
        UNION ALL
        SELECT 'gasto', id::text, payment_status, amount::text, expense_date::text FROM special_expenses
         WHERE expense_date < :inicio
        UNION ALL
        SELECT 'rec', id::text, status, coalesce(amount, 0)::text, month_ref FROM recurring_expense_entries
         WHERE month_ref < :mes
        UNION ALL
        SELECT 'bv', a.id::text, a.bv_payment_status, coalesce(a.amount_brl, 0)::text, '' FROM event_acrescimos a
         WHERE a.is_bv
        ORDER BY 1, 2
        """,
        mes=mes,
        inicio=inicio_do_mes,
    )


# ── preparação e limpeza ────────────────────────────────────────────────────────────────────────


def limpar() -> None:
    db.session.rollback()
    for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        u.roles.clear()
        db.session.delete(u)
    db.session.commit()


def preparar() -> None:
    hoje = now_sp().date()
    estado["hoje"] = hoje
    estado["mes_atual"] = hoje.strftime("%Y-%m")
    estado["inicio_do_mes"] = hoje.replace(day=1)
    with app.app_context():
        limpar()
        _usuario("fin", RoleName.FINANCEIRO)
        _usuario("com", RoleName.COMERCIAL)
    estado["fin_http"] = _cliente_http("fin")
    estado["com_http"] = _cliente_http("com")


# ── cenários ────────────────────────────────────────────────────────────────────────────────────


def cen_01_rbac() -> None:
    r = estado["com_http"].get("/api/financeiro/pagamentos")
    _garante(r.status_code == 403, f"COMERCIAL deveria levar 403, levou {r.status_code}")


def cen_02_mes_atual() -> None:
    p = _planilha()
    _garante(p.get("mes_atual") == estado["mes_atual"], f"mes_atual {p.get('mes_atual')!r}")
    _garante(p.get("atrasados_desde") == CORTE, f"atrasados_desde {p.get('atrasados_desde')!r}")
    _garante(p["month"] == estado["mes_atual"], f"month {p['month']}")
    anteriores = _anteriores(p)
    _garante(
        anteriores,
        "nenhum item de mês anterior no mês atual (o espelho tem cachês de outubro em aberto)",
    )
    for i in anteriores:
        _garante(i["status"] in ABERTOS, f"{_chave(i)} veio com situação {i['status']}")
        _garante(not i["is_future"], f"{_chave(i)} veio como futuro")
        origem = i.get("mes_origem") or ""
        _garante(CORTE <= origem < estado["mes_atual"], f"{_chave(i)} com mes_origem {origem!r}")
        esperado = max(0, (estado["hoje"] - date.fromisoformat(i["date"])).days)
        _garante(
            i.get("dias_em_atraso") == esperado,
            f"{_chave(i)} dias {i.get('dias_em_atraso')} ≠ {esperado}",
        )
    for i in p["items"]:
        if not i.get("de_mes_anterior"):
            _garante(i.get("de_mes_anterior") is False, f"{_chave(i)} sem o campo de_mes_anterior")
    tipos = sorted({i["type"] for i in anteriores})
    print(f"         {len(anteriores)} itens de antes ({', '.join(tipos)}), {_soma(anteriores)}")


def cen_03_mesmo_item() -> None:
    # Os meses passados vêm PRIMEIRO: abrir um mês regera os salários não pagos dele com id novo
    # (`_ensure_salary_payments`), então o mês atual é lido depois, já com os ids de agora.
    esperados: dict[tuple[str, str], tuple[dict, str]] = {}
    for mes in _meses_entre(CORTE, estado["mes_atual"]):
        for i in _planilha(mes)["items"]:
            if i["status"] in ABERTOS and not i["is_future"]:
                esperados[_chave(i)] = (i, mes)
    atual = {_chave(i): i for i in _anteriores(_planilha())}
    faltam = sorted(set(esperados) - set(atual))
    sobram = sorted(set(atual) - set(esperados))
    _garante(not faltam, f"{len(faltam)} itens em aberto ficaram para trás: {faltam[:5]}")
    _garante(not sobram, f"{len(sobram)} itens que o mês de origem não tem em aberto: {sobram[:5]}")
    for chave, (origem, mes) in esperados.items():
        veio = atual[chave]
        for campo in ("date", "amount", "status", "person_name", "event_id", "event_title"):
            _garante(
                veio[campo] == origem[campo],
                f"{chave}.{campo}: {veio[campo]!r} ≠ {origem[campo]!r}",
            )
        _garante(veio["mes_origem"] == mes, f"{chave} mes_origem {veio['mes_origem']} ≠ {mes}")
        _garante(not origem.get("de_mes_anterior"), f"{chave} marcado como anterior no próprio mês")
    print(
        f"         {len(esperados)} itens conferidos contra {len(_meses_entre(CORTE, estado['mes_atual']))} meses"
    )


def cen_04_corte() -> None:
    atual = _anteriores(_planilha())
    _garante(
        all(i["mes_origem"] >= CORTE for i in atual), "item de antes de maio/2026 no mês atual"
    )
    salarios_de_abril = {
        str(r[0])
        for r in _no_banco(
            "SELECT id FROM salary_payments WHERE month_ref = '2026-04' AND payment_status IN ('nao_pago', 'no_banco')"
        )
    }
    _garante(
        salarios_de_abril,
        "o espelho deixou de ter salário de abril em aberto: o cenário não prova nada",
    )
    vieram = {str(i["id"]) for i in atual if i["type"] == "salary"}
    _garante(
        not (salarios_de_abril & vieram),
        f"salário de abril no mês atual: {salarios_de_abril & vieram}",
    )
    _garante(
        not any(i["type"] == "commission" and str(i["id"]).endswith(":2026-03") for i in atual),
        "comissão do ciclo de março (repasse de abril) no mês atual",
    )


def cen_05_outros_meses() -> None:
    for mes in (_mes(estado["mes_atual"], -1), _mes(estado["mes_atual"], 1)):
        p = _planilha(mes)
        _garante(not _anteriores(p), f"{mes} recebeu item de mês anterior")
        _garante(
            p["totals"].get("anteriores") == 0,
            f"{mes} totals.anteriores = {p['totals'].get('anteriores')}",
        )
        _garante(p.get("mes_atual") == estado["mes_atual"], f"{mes} mes_atual {p.get('mes_atual')}")


def cen_06_totais() -> None:
    p = _planilha()
    itens, t = p["items"], p["totals"]
    conta = {
        "total": _soma(itens),
        "pago": _soma([i for i in itens if i["status"] == "pago"]),
        "no_banco": _soma([i for i in itens if i["status"] == "no_banco"]),
        "pendente": _soma([i for i in itens if i["status"] == "nao_pago" and not i["is_future"]]),
        "futuro": _soma([i for i in itens if i["status"] == "nao_pago" and i["is_future"]]),
        "anteriores": _soma(_anteriores(p)),
    }
    for campo, valor in conta.items():
        _garante(_cents(t[campo]) == valor, f"totals.{campo} = {t[campo]} ≠ {valor}")
    _garante(conta["anteriores"] > 0, "totals.anteriores zerado")


def cen_07_nada_muda() -> None:
    dre = "/api/financeiro/dashboard?period=mes_anterior"
    antes_dre = estado["fin_http"].get(dre).get_json()["dre"]
    antes = _foto_dos_meses_anteriores(estado["inicio_do_mes"])
    _planilha()
    _csv()
    depois = _foto_dos_meses_anteriores(estado["inicio_do_mes"])
    _garante(
        antes == depois,
        f"abrir o mês atual mudou {len(set(antes) ^ set(depois))} linhas de meses anteriores",
    )
    _garante(
        estado["fin_http"].get(dre).get_json()["dre"] == antes_dre, "a DRE do mês passado mudou"
    )


def cen_08_pagar_pelo_mes_atual() -> None:
    cache = next(
        (i for i in _anteriores(_planilha()) if i["type"] == "cache" and i["status"] == "nao_pago"),
        None,
    )
    _garante(cache is not None, "nenhum cachê de mês anterior em aberto para pagar")
    role_id, origem = int(cache["id"]), cache["mes_origem"]
    estado["role_restaurar"] = (role_id, cache["status"])
    r = estado["fin_http"].post(
        "/api/financeiro/pagamentos/set-status",
        json={"item_type": "cache", "item_id": role_id, "status": "pago"},
    )
    _garante(r.status_code == 200, f"set-status → {r.status_code} {r.get_data(as_text=True)[:200]}")
    gravado = _no_banco("SELECT payment_status FROM event_roles WHERE id = :i", i=role_id)[0][0]
    _garante(gravado == "pago", f"no banco ficou {gravado!r}")
    _garante(
        ("cache", str(role_id)) not in {_chave(i) for i in _anteriores(_planilha())},
        "o cachê pago continua no mês atual",
    )
    no_mes = {_chave(i): i for i in _planilha(origem)["items"]}
    _garante(
        no_mes.get(("cache", str(role_id)), {}).get("status") == "pago",
        f"{origem} não mostra o cachê pago",
    )


def cen_09_csv() -> None:
    p = _planilha()
    caches = [i for i in p["items"] if i["type"] == "cache"]
    de_antes = [i for i in caches if i.get("de_mes_anterior")]
    _garante(de_antes, "nenhum cachê de antes para conferir no CSV")
    linhas = _csv()
    _garante(
        len(linhas) == len(caches),
        f"CSV do mês atual com {len(linhas)} linhas, planilha com {len(caches)} cachês",
    )
    alvo = de_antes[0]
    data_br = date.fromisoformat(alvo["date"]).strftime("%d/%m/%Y")
    _garante(
        any(
            li[0] == data_br and li[1] == alvo["event_title"] and li[3] == alvo["person_name"]
            for li in linhas
        ),
        f"CSV sem o cachê de antes {data_br} {alvo['event_title']}",
    )
    origem = alvo["mes_origem"]
    caches_origem = [i for i in _planilha(origem)["items"] if i["type"] == "cache"]
    _garante(
        len(_csv(origem)) == len(caches_origem), f"CSV de {origem} não bate com os cachês do mês"
    )


def cen_10_limpeza() -> None:
    restaurar = estado.get("role_restaurar")
    if restaurar:
        role_id, situacao = restaurar
        with _externo.begin() as conn:
            conn.execute(
                text("UPDATE event_roles SET payment_status = :s WHERE id = :i"),
                {"s": situacao, "i": role_id},
            )
        ficou = _no_banco("SELECT payment_status FROM event_roles WHERE id = :i", i=role_id)[0][0]
        _garante(ficou == situacao, f"cachê {role_id} ficou {ficou!r}")
    with app.app_context():
        limpar()
    _garante(
        not _no_banco("SELECT id FROM users WHERE email LIKE :p", p=f"{PREFIX}%"),
        "usuário descartável sobrou",
    )


def main() -> int:
    print("Correção 331 — o que ficou em aberto vem para o mês atual da Planilha de Pagamentos")
    preparar()
    passos = [
        ("1. COMERCIAL leva 403 (DEVE falhar se vazar)", cen_01_rbac),
        ("2. mês atual traz os itens de antes (DEVE falhar no antigo)", cen_02_mes_atual),
        ("3. mesmo item do mês de origem, nenhum esquecido", cen_03_mesmo_item),
        ("4. nada de antes de maio/2026", cen_04_corte),
        ("5. mês passado e mês seguinte sem itens de antes", cen_05_outros_meses),
        ("6. totais somam os itens de antes", cen_06_totais),
        ("7. nada grava nos meses anteriores; DRE do mês passado igual", cen_07_nada_muda),
        ("8. pagar pelo mês atual grava e tira o item", cen_08_pagar_pelo_mes_atual),
        ("9. CSV com os cachês de antes", cen_09_csv),
    ]
    try:
        for nome, fn in passos:
            cenario(nome, fn)
    finally:
        cenario("10. limpeza", cen_10_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  ✗ {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
