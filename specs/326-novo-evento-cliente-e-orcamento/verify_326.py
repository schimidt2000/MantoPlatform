"""Verificação da correção 326 — Novo evento: cliente, telefone e orçamento vinculado na tela.

A mudança é só do app interno; o que o servidor precisa garantir para ela funcionar é o que se
verifica aqui (a tela em si é conferida no Browser pane):

 1. Comercial e Superadmin leem o que o bloco Orçamento usa: histórico, pré-fill e opções.
 2. Financeiro e Casting levam 403 nos dois endpoints do bloco.          (DEVE falhar se vazar)
 3. Orçamento que já virou evento vivo: o histórico traz `event_id`, e a criação com ele é
    recusada (409 com o mesmo `event_id`) — é a regra que o bloco antecipa.
 4. Orçamento livre: o pré-fill traz o que o bloco mostra (cliente, data, local, cachês).
 5. Telefone com a máscara nova é aceito: `(11) …`, `+55 (11) …` e `+351 …` gravam os dígitos
    canônicos, e o `phone_display` guarda o mascarado.
 6. Limpeza.

Só leitura no espelho, fora os usuários e as clientes descartáveis (prefixo `__v326_`). Google
DUBLADO: a criação do cenário 3 é recusada antes dele, e o dublê garante que nada sai se a regra
quebrar. Requisições HTTP FORA do `app_context`; a escrita do cenário 5 é lida por conexão separada.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
    C:\\Users\\schim\\Desktop\\Manto_Platform\\.venv\\Scripts\\python.exe specs\\326-novo-evento-cliente-e-orcamento\\verify_326.py
"""

from __future__ import annotations

import os
import sys
import traceback
import uuid
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote

sys.stdout.reconfigure(encoding="utf-8")
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter  # noqa: E402
from app.calendar import routes as cal_routes  # noqa: E402
from app.calendar import service as cal_service  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import CalendarEvent, Client, OrcamentoHistory, Role, User  # noqa: E402

PREFIX = "__v326_"
SENHA = "verify-326-senha"

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_externo = create_engine(os.environ["DATABASE_URL"], future=True)

# ── dublês ──────────────────────────────────────────────────────────────────────────────────────
cal_service.insert_event = lambda *a, **k: {"id": f"{PREFIX}g{uuid.uuid4().hex[:10]}"}
cal_service.update_event = lambda *a, **k: None
cal_service.delete_event = lambda *a, **k: None
cal_routes.insert_event = cal_service.insert_event


def _no_banco(sql: str, **params):
    with _externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001 — o cenário falha com a mensagem, os outros seguem
        with app.app_context():
            db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


# ── preparação ──────────────────────────────────────────────────────────────────────────────────


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


def _cliente_http(chave: str):
    c = app.test_client()
    r = c.post("/api/auth/login", json={"email": f"{PREFIX}{chave}@manto.local", "password": SENHA})
    _garante(r.status_code == 200, f"login {chave} → {r.status_code}")
    return c


def preparar() -> None:
    with app.app_context():
        limpar()
        estado["com"] = _usuario("com", RoleName.COMERCIAL)
        estado["sa"] = _usuario("sa", RoleName.SUPERADMIN)
        estado["fin"] = _usuario("fin", RoleName.FINANCEIRO)
        estado["cas"] = _usuario("cas", RoleName.CASTING)
        vivos = db.session.query(CalendarEvent.orcamento_history_id).filter(
            CalendarEvent.orcamento_history_id.isnot(None), CalendarEvent.cancelled_at.is_(None)
        )
        livre = (
            OrcamentoHistory.query.filter(
                ~OrcamentoHistory.id.in_(vivos), OrcamentoHistory.client_name.isnot(None)
            )
            .order_by(OrcamentoHistory.id.desc())
            .first()
        )
        ocupado = (
            CalendarEvent.query.filter(
                CalendarEvent.orcamento_history_id.isnot(None), CalendarEvent.cancelled_at.is_(None)
            )
            .order_by(CalendarEvent.id.desc())
            .first()
        )
        _garante(livre is not None, "o espelho não tem orçamento sem evento")
        _garante(ocupado is not None, "o espelho não tem orçamento que virou evento")
        estado["livre"] = {"id": livre.id, "cliente": livre.client_name}
        estado["ocupado"] = {
            "id": ocupado.orcamento_history_id,
            "event_id": ocupado.id,
            "cliente": db.session.get(OrcamentoHistory, ocupado.orcamento_history_id).client_name
            or "",
        }


def limpar() -> None:
    for c in Client.query.filter(Client.name.like(f"{PREFIX}%")).all():
        db.session.delete(c)
    for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        u.roles.clear()
        db.session.delete(u)
    db.session.commit()


# ── cenários ────────────────────────────────────────────────────────────────────────────────────


def _rotas_do_bloco() -> list[str]:
    return [
        f"/api/orcamento/historico?q={quote(estado['livre']['cliente'][:20])}",
        f"/api/events/new/prefill?orcamento_id={estado['livre']['id']}",
    ]


def cen_01_quem_cria_le() -> None:
    for chave in ("com", "sa"):
        c = _cliente_http(chave)
        for rota in [*_rotas_do_bloco(), "/api/events/new/options"]:
            r = c.get(rota)
            _garante(r.status_code == 200, f"{chave} {rota} → {r.status_code}")


def cen_02_quem_nao_cria_nao_le() -> None:
    for chave in ("fin", "cas"):
        c = _cliente_http(chave)
        for rota in _rotas_do_bloco():
            r = c.get(rota)
            _garante(r.status_code == 403, f"{chave} {rota} → {r.status_code} (esperado 403)")


def cen_03_orcamento_que_virou_evento() -> None:
    oc = estado["ocupado"]
    c = _cliente_http("com")
    r = c.get(f"/api/orcamento/historico?q={quote(oc['cliente'][:20])}")
    _garante(r.status_code == 200, f"histórico → {r.status_code}")
    linha = next((e for e in r.get_json()["entries"] if e["id"] == oc["id"]), None)
    _garante(linha is not None, f"orçamento #{oc['id']} fora da busca por “{oc['cliente'][:20]}”")
    _garante(
        linha["event_id"] == oc["event_id"], f"event_id {linha['event_id']} ≠ {oc['event_id']}"
    )

    antes = _no_banco("SELECT count(*) FROM calendar_events")[0][0]
    dia = (now_sp().date() + timedelta(days=400)).isoformat()
    corpo = {
        "title": f"{PREFIX}evento",
        "event_type": "R&I",
        "date": dia,
        "start": "15:00",
        "end": "17:00",
        "location": "Rua Augusta, 100, São Paulo",
        "description": "",
        "needs_rehearsal": False,
        "sale_value": 1000,
        "sale_value_gross": 1000,
        "transport_value": 0,
        "acrescimo_value": 0,
        "with_invoice": False,
        "is_cortesia_permuta": False,
        "seller_id": estado["com"],
        "sale_date": None,
        "payment_method": None,
        "payment_installments": None,
        "payment_due_date": None,
        "orcamento_history_id": oc["id"],
        "duracao": "2",
        "characters": [],
        "orc_caches": [],
        "acrescimos": [],
        "observations": [],
        "clients": [],
    }
    r = c.post("/api/events", json=corpo)
    _garante(
        r.status_code == 409,
        f"criação com orçamento ocupado → {r.status_code} {r.get_data(as_text=True)[:200]}",
    )
    # O `event_id` viaja dentro do envelope de `json_error`, ao lado da mensagem.
    _garante(
        r.get_json()["error"].get("event_id") == oc["event_id"],
        f"409 sem o event_id: {r.get_json()}",
    )
    depois = _no_banco("SELECT count(*) FROM calendar_events")[0][0]
    _garante(depois == antes, f"a recusa gravou evento ({antes} → {depois})")


def cen_04_prefill_do_livre() -> None:
    r = _cliente_http("com").get(f"/api/events/new/prefill?orcamento_id={estado['livre']['id']}")
    _garante(r.status_code == 200, f"prefill → {r.status_code}")
    p = r.get_json()
    _garante(
        p.get("orcamento_id") == estado["livre"]["id"], f"orcamento_id {p.get('orcamento_id')}"
    )
    _garante(
        p.get("client_name") == estado["livre"]["cliente"], "client_name diferente do orçamento"
    )
    for chave in ("date", "location", "total_1h", "caches"):
        _garante(chave in p, f"prefill sem `{chave}`")
    _garante(
        all("role_type" in c and "label" in c for c in p["caches"]), "cachê sem role_type/label"
    )


def cen_05_telefone_mascarado() -> None:
    meio = f"{uuid.uuid4().int % 10**8:08d}"
    casos = [
        ("nacional", f"(11) 9{meio[:4]}-{meio[4:]}", f"55119{meio}"),
        ("ddi55", f"+55 (21) 9{meio[:4]}-{meio[4:]}", f"55219{meio}"),
        ("exterior", f"+351 9{meio}", f"3519{meio}"),
    ]
    c = _cliente_http("com")
    for sufixo, digitado, canonico in casos:
        r = c.post(
            "/api/clientes/quick-create", json={"name": f"{PREFIX}{sufixo}", "phone": digitado}
        )
        _garante(
            r.status_code == 200, f"{sufixo} → {r.status_code} {r.get_data(as_text=True)[:200]}"
        )
        _garante(r.get_json().get("reused") is False, f"{sufixo}: reaproveitou ficha existente")
        linhas = _no_banco(
            "SELECT phone, phone_display FROM clients WHERE name = :n", n=f"{PREFIX}{sufixo}"
        )
        _garante(len(linhas) == 1, f"{sufixo}: {len(linhas)} fichas gravadas")
        _garante(linhas[0][0] == canonico, f"{sufixo}: phone {linhas[0][0]} ≠ {canonico}")
        _garante(linhas[0][1] == digitado, f"{sufixo}: phone_display {linhas[0][1]!r}")


def cen_06_limpeza() -> None:
    with app.app_context():
        limpar()
        _garante(Client.query.filter(Client.name.like(f"{PREFIX}%")).count() == 0, "cliente sobrou")
        _garante(User.query.filter(User.email.like(f"{PREFIX}%")).count() == 0, "usuário sobrou")
        _garante(
            CalendarEvent.query.filter(CalendarEvent.title.like(f"{PREFIX}%")).count() == 0,
            "evento sobrou",
        )


def main() -> int:
    print("Correção 326 — Novo evento: cliente, telefone e orçamento vinculado")
    preparar()
    passos = [
        ("1. Comercial e Superadmin leem histórico, pré-fill e opções", cen_01_quem_cria_le),
        (
            "2. Financeiro e Casting levam 403 no bloco (DEVE falhar se vazar)",
            cen_02_quem_nao_cria_nao_le,
        ),
        (
            "3. orçamento que virou evento: event_id no histórico e 409 na criação",
            cen_03_orcamento_que_virou_evento,
        ),
        ("4. pré-fill do orçamento livre traz o que o bloco mostra", cen_04_prefill_do_livre),
        ("5. telefone mascarado grava os dígitos canônicos", cen_05_telefone_mascarado),
    ]
    try:
        for nome, fn in passos:
            cenario(nome, fn)
    finally:
        cenario("6. limpeza", cen_06_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  ✗ {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
