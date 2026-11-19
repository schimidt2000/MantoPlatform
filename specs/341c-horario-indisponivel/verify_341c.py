"""Verificação do ajuste 341c — horário indisponível à mão, que continua aparecendo na loja.

Roda contra o `manto_341c` (dump de produção de 19/11/2026 02:00). Escrito ANTES da mudança
(Princípio VIII): sem a rota de marcar e sem `indisponiveis` na API pública, os cenários 1–7 FALHAM.

  1  marcar livre como indisponível pela rota → 200 e status no banco
  2  a loja lista o indisponível em `indisponiveis` (sem id) e não em `slots`
  3  reservar o indisponível → 409 e nenhum pedido gravado
  4  liberar → volta a `livre` e à lista de escolha
  5  vendido e em pagamento não mudam por aqui → 409
  6  vendido e em pagamento também aparecem riscados na loja
  7  horário indisponível pode ser removido
  8  papel sem acesso marca → 403 (deve falhar) e nada muda
  9  limpeza; nenhuma conexão externa

Uso:
    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONPATH = (Get-Location).Path; $env:PYTHONUTF8 = '1'
    <python> specs\\341c-horario-indisponivel\\verify_341c.py
"""

from __future__ import annotations

import os
import secrets
import socket
import sys
from datetime import datetime, timedelta
from decimal import Decimal

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if "sqlite" in os.environ.get("DATABASE_URL", "sqlite"):
    sys.exit("ERRO: aponte DATABASE_URL para o Postgres local, nunca SQLite.")
if os.environ.get("MANTO_SEM_THREADS") != "1":
    sys.exit("ERRO: rode com MANTO_SEM_THREADS=1 (o espelho tem credenciais reais).")
if "localhost" not in os.environ["DATABASE_URL"] and "127.0.0.1" not in os.environ["DATABASE_URL"]:
    sys.exit("ERRO: este verify só roda contra banco local.")

_ESCAPES: list[str] = []
_create_connection_original = socket.create_connection


def _so_local(address, *args, **kwargs):
    host = str(address[0])
    if host not in ("localhost", "127.0.0.1", "::1"):
        _ESCAPES.append(host)
        raise OSError(f"[verify_341c] conexão externa bloqueada: {host}")
    return _create_connection_original(address, *args, **kwargs)


socket.create_connection = _so_local

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.integracoes import infinitepay_client as ipc  # noqa: E402
from app.marketing import virtuais_ops as ops  # noqa: E402
from app.models import CatalogCharacter, SiteSetting, User, VirtualCampaignSlot  # noqa: E402

RUN = secrets.token_hex(3)
PASSWORD = f"verify341c-{secrets.token_hex(6)}"
app = create_app()
_engine = create_engine(os.environ["DATABASE_URL"].strip())


def _db(sql: str, **p):
    # Conexão separada: o autoflush da sessão do app esconderia um commit que não aconteceu.
    with _engine.connect() as conn:
        return conn.execute(text(sql), p).fetchall()


resultados: list[tuple[str, str, str]] = []


def check(nome: str, ok: bool, detalhe: str = "") -> None:
    estado = "OK" if ok else "FALHA"
    resultados.append((nome, estado, detalhe))
    print(f"{estado:9} {nome}" + (f"  [{detalhe}]" if detalhe and not ok else ""), flush=True)


def cenario(nome: str):
    def deco(fn):
        def run():
            try:
                fn()
            except Exception as exc:  # noqa: BLE001
                with app.app_context():
                    db.session.rollback()
                resultados.append((nome, "FALHA", f"{type(exc).__name__}: {exc}"[:300]))
                print(f"FALHA     {nome}  [{type(exc).__name__}: {str(exc)[:240]}]", flush=True)

        run.__name__ = fn.__name__
        return run

    return deco


# InfinitePay por dublê: a reserva do cenário 3 não pode chegar a falar com a operadora de verdade.
ipc.criar_link_pagamento = lambda **kw: {"payment_url": f"https://checkout.dublê/{kw['order_nsu']}"}

# ── Fixtures ────────────────────────────────────────────────────────────────────────────────
client = app.test_client()
USUARIOS: dict[str, str] = {}
SETTINGS_ORIGINAIS: dict = {}
SLOTS: dict[str, int] = {}
BASE = datetime(2031, 8, 4, 14, 0)

with app.app_context():
    s = SiteSetting.query.get(1)
    for campo in ("infinitepay_handle", "infinitepay_webhook_token", "virtuais_pagamento_ativo"):
        SETTINGS_ORIGINAIS[campo] = getattr(s, campo, None)
    s.infinitepay_handle = "verify-341c"
    s.infinitepay_webhook_token = f"tok341c-{RUN}-{secrets.token_hex(8)}"
    s.virtuais_pagamento_ativo = True
    c = ops.criar_campanha(
        catalog_character_id=CatalogCharacter.query.filter_by(is_active=True).first().id,
        title=f"Verify341c {RUN}",
        price_live=Decimal("120.00"),
        price_recorded=Decimal("70.00"),
        recorded_capacity=0,
        tolerance_terms="termos",
        cover_url="/catalogo/midia/campanhas/x.jpg",
    )
    c.max_reservations_per_origin = 10_000
    c.status = "publicada"
    db.session.flush()
    CAMP_ID, SLUG = c.id, c.slug
    for i, (nome, status) in enumerate(
        [
            ("livre", "livre"),
            ("outro", "livre"),
            ("vendido", "vendido"),
            ("travado", "travado"),
            ("remover", "livre"),
        ]
    ):
        h = VirtualCampaignSlot(
            campaign_id=CAMP_ID,
            start_at=BASE + timedelta(minutes=15 * i),
            status=status,
            locked_until=(datetime(2031, 8, 4, 13, 0) if status == "travado" else None),
        )
        db.session.add(h)
        db.session.flush()
        SLOTS[nome] = h.id
    gestor = (
        User.query.filter(User.has_access.is_(True))
        .filter(User.roles.any(name=RoleName.SUPERADMIN))
        .filter(User.email.isnot(None))
        .order_by(User.id)
        .first()
    )
    # Dívida 206: o "outro" não pode ser Revendedor EducaManto (o guard da 078 dá 403 em tudo).
    outro = (
        User.query.filter(User.has_access.is_(True))
        .filter(~User.roles.any(name=RoleName.SUPERADMIN))
        .filter(~User.roles.any(name=RoleName.COMERCIAL))
        .filter(~User.roles.any(name=RoleName.REVENDEDOR_EDUCAMANTO))
        .filter(User.email.isnot(None))
        .order_by(User.id)
        .first()
    )
    for papel, u in (("gestor", gestor), ("outro", outro)):
        if u is not None:
            u.set_password(PASSWORD)
            USUARIOS[papel] = u.email
    db.session.commit()

limiter.enabled = False


def login(papel: str) -> None:
    client.post("/api/auth/logout")
    r = client.post("/api/auth/login", json={"email": USUARIOS[papel], "password": PASSWORD})
    assert r.status_code == 200, f"login {papel}: {r.status_code}"


def marcar(nome: str, indisponivel: bool):
    return client.patch(
        f"/api/virtuais/horarios/{SLOTS[nome]}", json={"indisponivel": indisponivel}
    )


def status(nome: str) -> str | None:
    linha = _db("SELECT status FROM virtual_campaign_slots WHERE id=:i", i=SLOTS[nome])
    return linha[0][0] if linha else None


def publico() -> dict:
    client.post("/api/auth/logout")
    return client.get(f"/api/virtuais/campanhas/{SLUG}/horarios").get_json() or {}


def hora(nome: str) -> str:
    i = list(SLOTS).index(nome)
    return (BASE + timedelta(minutes=15 * i)).isoformat()


# ── Cenários ────────────────────────────────────────────────────────────────────────────────
@cenario("1  marcar livre como indisponível")
def c1():
    login("gestor")
    r = marcar("livre", True)
    check("1.1 200", r.status_code == 200, f"{r.status_code} {r.get_data(as_text=True)[:120]}")
    check(
        "1.2 status indisponivel no banco", status("livre") == "indisponivel", str(status("livre"))
    )


@cenario("2  a loja mostra o indisponível riscado, sem deixar escolher")
def c2():
    corpo = publico()
    livres = [s["start_at"] for s in corpo.get("slots", [])]
    riscados = corpo.get("indisponiveis")
    check("2.1 fora da lista de escolha", hora("livre") not in livres, str(livres))
    check(
        "2.2 em indisponiveis",
        isinstance(riscados, list) and hora("livre") in [x.get("start_at") for x in riscados],
        str(riscados),
    )
    check(
        "2.3 sem id nem motivo",
        isinstance(riscados, list) and all(set(x) == {"start_at"} for x in riscados),
        str(riscados),
    )
    check("2.4 o outro livre continua escolhível", hora("outro") in livres, str(livres))


@cenario("3  reservar o indisponível → 409 e nada gravado")
def c3():
    antes = _db("SELECT count(*) FROM virtual_orders WHERE campaign_id=:c", c=CAMP_ID)[0][0]
    r = client.post(
        f"/api/virtuais/campanhas/{SLUG}/reservar",
        json={
            "modality": "ao_vivo",
            "slot_id": SLOTS["livre"],
            "child_name": "Teo",
            "child_age": 6,
            "contact_phone": f"119{secrets.randbelow(10**8):08d}",
            "contact_email": f"v341c-{RUN}@example.com",
            "client_token": secrets.token_hex(8),
        },
        headers={"X-Manto-Client-Ip": "203.0.113.71", "User-Agent": "verify-341c"},
    )
    depois = _db("SELECT count(*) FROM virtual_orders WHERE campaign_id=:c", c=CAMP_ID)[0][0]
    check("3.1 409", r.status_code == 409, str(r.status_code))
    check("3.2 nenhum pedido", antes == depois, f"{antes} -> {depois}")
    check("3.3 continua indisponível", status("livre") == "indisponivel", str(status("livre")))


@cenario("4  liberar volta para a escolha")
def c4():
    login("gestor")
    r = marcar("livre", False)
    check("4.1 200", r.status_code == 200, str(r.status_code))
    check("4.2 status livre", status("livre") == "livre", str(status("livre")))
    check(
        "4.3 escolhível de novo",
        hora("livre") in [s["start_at"] for s in publico().get("slots", [])],
    )


@cenario("5  vendido e em pagamento não mudam por aqui")
def c5():
    login("gestor")
    for nome in ("vendido", "travado"):
        r = marcar(nome, True)
        check(
            f"5.{nome} 409",
            r.status_code == 409,
            f"{r.status_code} {r.get_data(as_text=True)[:100]}",
        )
        check(f"5.{nome} status intacto", status(nome) == nome, str(status(nome)))


@cenario("6  vendido e em pagamento também aparecem riscados")
def c6():
    riscados = [x.get("start_at") for x in (publico().get("indisponiveis") or [])]
    check("6.1 vendido riscado", hora("vendido") in riscados, str(riscados))
    check("6.2 em pagamento riscado", hora("travado") in riscados, str(riscados))


@cenario("7  horário indisponível pode ser removido")
def c7():
    login("gestor")
    marcar("remover", True)
    r = client.delete(f"/api/virtuais/horarios/{SLOTS['remover']}")
    check("7.1 200", r.status_code == 200, f"{r.status_code} {r.get_data(as_text=True)[:100]}")
    check("7.2 saiu do banco", status("remover") is None, str(status("remover")))


@cenario("8  papel sem acesso → 403 (deve falhar)")
def c8():
    if "outro" not in USUARIOS:
        check("8.0 há usuário sem acesso no espelho", False, "nenhum")
        return
    login("outro")
    r = marcar("outro", True)
    check("8.1 403", r.status_code == 403, str(r.status_code))
    check("8.2 nada mudou", status("outro") == "livre", str(status("outro")))
    client.post("/api/auth/logout")


@cenario("9  limpeza")
def c9():
    with _engine.begin() as conn:
        conn.execute(
            text("UPDATE virtual_campaign_slots SET order_id=NULL WHERE campaign_id=:c"),
            {"c": CAMP_ID},
        )
        conn.execute(text("DELETE FROM virtual_orders WHERE campaign_id=:c"), {"c": CAMP_ID})
        conn.execute(
            text("DELETE FROM virtual_campaign_slots WHERE campaign_id=:c"), {"c": CAMP_ID}
        )
        conn.execute(text("DELETE FROM virtual_campaigns WHERE id=:c"), {"c": CAMP_ID})
    with app.app_context():
        s = SiteSetting.query.get(1)
        for campo, valor in SETTINGS_ORIGINAIS.items():
            setattr(s, campo, valor)
        db.session.commit()
    sobra = _db("SELECT count(*) FROM virtual_campaigns WHERE id=:c", c=CAMP_ID)[0][0]
    check("9.1 campanha de teste removida", sobra == 0)
    check("9.2 nenhuma conexão externa", not _ESCAPES, str(_ESCAPES))


for fn in (c1, c2, c3, c4, c5, c6, c7, c8, c9):
    fn()

ok = sum(1 for _, e, _ in resultados if e == "OK")
falha = sum(1 for _, e, _ in resultados if e == "FALHA")
print(f"\n{ok} OK · {falha} FALHA (de {len(resultados)})")
sys.exit(1 if falha else 0)
