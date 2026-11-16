"""Verificação do hotfix 341b — um horário de chamada a cada 15 minutos.

Roda contra o `manto_341b` (dump de produção de 12/11/2026 02:00). Escrito ANTES da mudança
(Princípio VIII): com o código antigo, que gera de 10 em 10, os cenários 1, 2, 3 e 4 FALHAM.

  1  janela 14h00–18h00 → 16 horários, de 15 em 15 (14h00 … 17h45), pela rota da tela
  2  gerar a mesma janela de novo → nada criado, 16 pulados
  3  grade antiga de 10 em 10 no dia → só nasce o que fica a 15 min de todos (10h45)
  4  horário vizinho fora da janela também conta (12h10 tira o 12h15)
  5  a chamada continua durando 10 min; o passo é 15
  6  papel sem acesso → 403 (deve falhar) e nada criado
  7  limpeza; nenhuma conexão externa

Uso:
    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONPATH = (Get-Location).Path; $env:PYTHONUTF8 = '1'
    <python> specs\\341b-chamadas-a-cada-15-min\\verify_341b.py
"""

from __future__ import annotations

import os
import secrets
import socket
import sys
from datetime import datetime
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
        raise OSError(f"[verify_341b] conexão externa bloqueada: {host}")
    return _create_connection_original(address, *args, **kwargs)


socket.create_connection = _so_local

from sqlalchemy import create_engine, text  # noqa: E402

from app import constants, create_app, db, limiter  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.marketing import virtuais_ops as ops  # noqa: E402
from app.models import CatalogCharacter, User, VirtualCampaignSlot  # noqa: E402

RUN = secrets.token_hex(3)
PASSWORD = f"verify341b-{secrets.token_hex(6)}"
DIA = "2031-07-14"
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


# ── Fixtures ────────────────────────────────────────────────────────────────────────────────
client = app.test_client()
USUARIOS: dict[str, str] = {}

with app.app_context():
    PERSONAGEM_ID = CatalogCharacter.query.filter_by(is_active=True).first().id
    c = ops.criar_campanha(
        catalog_character_id=PERSONAGEM_ID,
        title=f"Verify341b {RUN}",
        price_live=Decimal("120.00"),
        price_recorded=Decimal("70.00"),
        recorded_capacity=0,
        tolerance_terms="termos",
        cover_url="/catalogo/midia/campanhas/x.jpg",
    )
    CAMP_ID = c.id
    gestor = (
        User.query.filter(User.has_access.is_(True))
        .filter(User.roles.any(name=RoleName.SUPERADMIN))
        .filter(User.email.isnot(None))
        .order_by(User.id)
        .first()
    )
    # O "outro" não pode ser Revendedor EducaManto: o guard da 078 dá 403 em toda `/api/` para
    # ele, e o 403 do cenário 6 viria pelo motivo errado (dívida 206, mesma armadilha da 310).
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


def gerar(inicio: str, fim: str):
    return client.post(
        f"/api/virtuais/campanhas/{CAMP_ID}/horarios",
        json={"date": DIA, "start": inicio, "end": fim},
    )


def horarios(de: str, ate: str) -> list[str]:
    linhas = _db(
        "SELECT start_at FROM virtual_campaign_slots WHERE campaign_id = :c "
        "AND start_at >= :de AND start_at < :ate ORDER BY start_at",
        c=CAMP_ID,
        de=f"{DIA} {de}",
        ate=f"{DIA} {ate}",
    )
    return [r[0].strftime("%H:%M") for r in linhas]


def semear(*horas: str) -> None:
    # Grade antiga gravada direto no banco: é o que existia em produção antes da 341b.
    with app.app_context():
        for h in horas:
            db.session.add(
                VirtualCampaignSlot(
                    campaign_id=CAMP_ID,
                    start_at=datetime.strptime(f"{DIA} {h}", "%Y-%m-%d %H:%M"),
                    status="livre",
                )
            )
        db.session.commit()


# ── Cenários ────────────────────────────────────────────────────────────────────────────────
@cenario("1  janela 14h–18h → 16 horários de 15 em 15")
def c1():
    login("gestor")
    r = gerar("14:00", "18:00")
    corpo = r.get_json() or {}
    check(
        "1.1 201 com 16 criados",
        r.status_code == 201 and corpo.get("created") == 16,
        f"{r.status_code} {corpo}",
    )
    esperado = [f"{h:02d}:{m:02d}" for h in range(14, 18) for m in (0, 15, 30, 45)]
    check(
        "1.2 14h00, 14h15 … 17h45 no banco",
        horarios("14:00", "18:00") == esperado,
        str(horarios("14:00", "18:00")),
    )


@cenario("2  mesma janela de novo → nada criado")
def c2():
    login("gestor")
    r = gerar("14:00", "18:00")
    corpo = r.get_json() or {}
    check("2.1 created 0, skipped 16", corpo == {"created": 0, "skipped": 16}, str(corpo))
    check("2.2 continuam 16", len(horarios("14:00", "18:00")) == 16)


@cenario("3  grade antiga de 10 em 10 → só nasce o que tem a pausa")
def c3():
    semear("10:00", "10:10", "10:20")
    login("gestor")
    r = gerar("10:00", "11:00")
    corpo = r.get_json() or {}
    # 10h00 já existe; 10h15 fica a 5 min de 10h10; 10h30 a 10 de 10h20; 10h45 está livre.
    check("3.1 created 1, skipped 3", corpo == {"created": 1, "skipped": 3}, str(corpo))
    check(
        "3.2 só o 10h45 nasceu",
        horarios("10:00", "11:00") == ["10:00", "10:10", "10:20", "10:45"],
        str(horarios("10:00", "11:00")),
    )


@cenario("4  horário vizinho fora da janela também conta")
def c4():
    semear("12:10")
    login("gestor")
    r = gerar("12:15", "13:00")
    corpo = r.get_json() or {}
    check("4.1 created 2, skipped 1", corpo == {"created": 2, "skipped": 1}, str(corpo))
    check(
        "4.2 12h15 não nasceu (5 min depois do 12h10)",
        horarios("12:00", "13:00") == ["12:10", "12:30", "12:45"],
        str(horarios("12:00", "13:00")),
    )


@cenario("5  a chamada dura 10 min; o passo é 15")
def c5():
    check("5.1 duração 10", constants.VIRTUAL_SLOT_MINUTES == 10)
    check("5.2 passo 15", getattr(constants, "VIRTUAL_SLOT_INTERVAL_MINUTES", None) == 15)


@cenario("6  papel sem acesso → 403 (deve falhar)")
def c6():
    if "outro" not in USUARIOS:
        check("6.0 há usuário sem acesso no espelho", False, "nenhum")
        return
    login("outro")
    antes = len(horarios("19:00", "21:00"))
    r = gerar("19:00", "21:00")
    check("6.1 403", r.status_code == 403, str(r.status_code))
    check("6.2 nada criado", len(horarios("19:00", "21:00")) == antes)
    client.post("/api/auth/logout")


@cenario("7  limpeza")
def c7():
    _ok = True
    with _engine.begin() as conn:
        conn.execute(
            text("DELETE FROM virtual_campaign_slots WHERE campaign_id = :c"), {"c": CAMP_ID}
        )
        conn.execute(text("DELETE FROM virtual_campaigns WHERE id = :c"), {"c": CAMP_ID})
    sobra = _db("SELECT count(*) FROM virtual_campaigns WHERE id = :c", c=CAMP_ID)[0][0]
    check("7.1 campanha de teste removida", sobra == 0 and _ok)
    check("7.2 nenhuma conexão externa", not _ESCAPES, str(_ESCAPES))


for fn in (c1, c2, c3, c4, c5, c6, c7):
    fn()

ok = sum(1 for _, e, _ in resultados if e == "OK")
falha = sum(1 for _, e, _ in resultados if e == "FALHA")
print(f"\n{ok} OK · {falha} FALHA (de {len(resultados)})")
sys.exit(1 if falha else 0)
