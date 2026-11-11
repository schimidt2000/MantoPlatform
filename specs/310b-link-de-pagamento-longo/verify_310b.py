"""Verificação do hotfix 310b — link de pagamento com mais de 500 caracteres.

Roda contra o `manto_310b` (dump de produção de 11/11/2026 02:00; o `manto_local` está no CRM 334).
Escrito ANTES da migration (Princípio VIII): sem ela, os cenários 1, 2, 4 e 5 FALHAM — a reserva
responde 500 e o pedido fica `reservado` sem link, exatamente como em produção.

  1  link de 513 caracteres (o tamanho real de 11/11) → 201 e gravado inteiro
  2  link de 2.000 caracteres → 201 e gravado inteiro
  3  link curto continua (regressão)
  4  a página do pedido devolve o link inteiro
  5  a coluna é TEXT no banco
  6  limpeza; nenhuma conexão externa

A InfinitePay é dublê (devolve um link do tamanho pedido); nada de rede sai da máquina.

Uso:
    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONPATH = (Get-Location).Path; $env:PYTHONUTF8 = '1'
    <python> specs\\310b-link-de-pagamento-longo\\verify_310b.py
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
        raise OSError(f"[verify_310b] conexão externa bloqueada: {host}")
    return _create_connection_original(address, *args, **kwargs)


socket.create_connection = _so_local

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter  # noqa: E402
from app.integracoes import infinitepay_client as ipc  # noqa: E402
from app.marketing import virtuais_ops as ops  # noqa: E402
from app.models import CatalogCharacter, SiteSetting, VirtualCampaignSlot  # noqa: E402

RUN = secrets.token_hex(3)
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


# ── Dublê da operadora: devolve um link do tamanho que o cenário pedir ──────────────────────
TAMANHO = [100]


def _link_falso(**kw):
    base = f"https://checkout.infinitepay.io/verify-310b?lenc={kw['order_nsu']}-"
    return {"payment_url": base + "x" * (TAMANHO[0] - len(base))}


ipc.criar_link_pagamento = _link_falso

# ── Fixtures ────────────────────────────────────────────────────────────────────────────────
client = app.test_client()
CRIADAS: list[int] = []
SETTINGS_ORIGINAIS: dict = {}

with app.app_context():
    s = SiteSetting.query.get(1)
    for campo in ("infinitepay_handle", "infinitepay_webhook_token", "virtuais_pagamento_ativo"):
        SETTINGS_ORIGINAIS[campo] = getattr(s, campo, None)
    s.infinitepay_handle = "verify-310b"
    s.infinitepay_webhook_token = f"tok310b-{RUN}-{secrets.token_hex(8)}"
    s.virtuais_pagamento_ativo = True
    PERSONAGEM_ID = CatalogCharacter.query.filter_by(is_active=True).first().id
    c = ops.criar_campanha(
        catalog_character_id=PERSONAGEM_ID,
        title=f"Verify310b {RUN}",
        price_live=Decimal("120.00"),
        price_recorded=Decimal("70.00"),
        recorded_capacity=0,
        tolerance_terms="termos",
        cover_url="/catalogo/midia/campanhas/x.jpg",
    )
    c.max_reservations_per_origin = 10_000
    c.status = "publicada"
    db.session.commit()
    CAMP_ID, SLUG = c.id, c.slug
    CRIADAS.append(c.id)

limiter.enabled = False
_SEQ = [0]


def novo_horario() -> int:
    _SEQ[0] += 1
    with app.app_context():
        h = VirtualCampaignSlot(
            campaign_id=CAMP_ID,
            start_at=datetime(2031, 6, 2, 9, 0) + timedelta(minutes=10 * _SEQ[0]),
            status="livre",
        )
        db.session.add(h)
        db.session.commit()
        return h.id


def reservar(tamanho: int):
    TAMANHO[0] = tamanho
    return client.post(
        f"/api/virtuais/campanhas/{SLUG}/reservar",
        json={
            "modality": "ao_vivo",
            "slot_id": novo_horario(),
            "child_name": "Teste",
            "child_age": 30,
            "contact_phone": f"119{secrets.randbelow(10**8):08d}",
            "contact_email": f"v310b-{RUN}@example.com",
            "client_token": secrets.token_hex(8),
        },
        headers={"X-Manto-Client-Ip": "203.0.113.31", "User-Agent": "verify-310b"},
    )


def _gravado(public_token: str):
    linhas = _db(
        "select status, length(payment_url) from virtual_orders where public_token=:t",
        t=public_token,
    )
    return linhas[0] if linhas else (None, None)


def _ultimo_pedido():
    linhas = _db(
        "select status, payment_url is null from virtual_orders where campaign_id=:c "
        "order by id desc limit 1",
        c=CAMP_ID,
    )
    return linhas[0] if linhas else None


# ── Cenários ────────────────────────────────────────────────────────────────────────────────
ESTADO: dict = {}


@cenario("1 link de 513 caracteres")
def c1():
    r = reservar(513)
    check(
        "1.1 reserva responde 201",
        r.status_code == 201,
        f"HTTP {r.status_code}; último pedido no banco: {_ultimo_pedido()}",
    )
    if r.status_code != 201:
        return
    corpo = r.get_json()
    check("1.2 resposta traz o link inteiro", len(corpo.get("payment_url") or "") == 513)
    status, tamanho = _gravado(corpo["public_token"])
    check(
        "1.3 banco: pedido aguardando com o link de 513",
        (status, tamanho) == ("aguardando", 513),
        f"{status}, {tamanho}",
    )
    ESTADO["token"] = corpo["public_token"]


@cenario("2 link de 2.000 caracteres")
def c2():
    r = reservar(2000)
    check("2.1 reserva responde 201", r.status_code == 201, f"HTTP {r.status_code}")
    if r.status_code != 201:
        return
    status, tamanho = _gravado(r.get_json()["public_token"])
    check(
        "2.2 banco: link de 2.000 gravado inteiro",
        (status, tamanho) == ("aguardando", 2000),
        f"{status}, {tamanho}",
    )


@cenario("3 link curto (regressão)")
def c3():
    r = reservar(120)
    check("3.1 reserva responde 201", r.status_code == 201, f"HTTP {r.status_code}")
    if r.status_code != 201:
        return
    status, tamanho = _gravado(r.get_json()["public_token"])
    check(
        "3.2 banco: link curto gravado",
        (status, tamanho) == ("aguardando", 120),
        f"{status}, {tamanho}",
    )


@cenario("4 página do pedido")
def c4():
    token = ESTADO.get("token")
    check("4.1 há pedido do cenário 1", bool(token), "cenário 1 não gravou o pedido")
    if not token:
        return
    r = client.get(f"/api/virtuais/pedidos/{token}")
    url = (r.get_json() or {}).get("payment_url") or ""
    check(
        "4.2 a página recebe o link inteiro para o botão de pagar",
        r.status_code == 200 and len(url) == 513,
        f"HTTP {r.status_code}, {len(url)}",
    )


@cenario("5 tipo da coluna")
def c5():
    tipo = _db(
        "select data_type, character_maximum_length from information_schema.columns "
        "where table_name='virtual_orders' and column_name='payment_url'"
    )[0]
    check("5.1 payment_url é text, sem teto", tuple(tipo) == ("text", None), str(tuple(tipo)))


def limpar() -> None:
    with _engine.begin() as conn:
        for cid in CRIADAS:
            ordens = [
                r[0]
                for r in conn.execute(
                    text("select id from virtual_orders where campaign_id=:c"), {"c": cid}
                )
            ]
            conn.execute(
                text("update virtual_campaign_slots set order_id=null where campaign_id=:c"),
                {"c": cid},
            )
            if ordens:
                for tabela in (
                    "virtual_payment_notifications",
                    "virtual_refund_requests",
                    "virtual_order_notifications",
                    "virtual_media_deliveries",
                ):
                    conn.execute(
                        text(f"delete from {tabela} where order_id = any(:o)"), {"o": ordens}
                    )
                conn.execute(text("delete from virtual_orders where campaign_id=:c"), {"c": cid})
            conn.execute(
                text("delete from virtual_campaign_slots where campaign_id=:c"), {"c": cid}
            )
            conn.execute(text("delete from virtual_campaigns where id=:c"), {"c": cid})
    with app.app_context():
        s = SiteSetting.query.get(1)
        for campo, valor in SETTINGS_ORIGINAIS.items():
            setattr(s, campo, valor)
        db.session.commit()


try:
    for fn in (c1, c2, c3, c4, c5):
        fn()
finally:
    try:
        limpar()
        sobra = _db("select count(*) from virtual_campaigns where id = any(:c)", c=CRIADAS)[0][0]
        check("6.1 limpeza", sobra == 0, f"{sobra} campanha(s) sobrando")
    except Exception as exc:  # noqa: BLE001
        check("6.1 limpeza", False, f"{type(exc).__name__}: {exc}"[:200])
    check("6.2 nenhuma conexão externa escapou", not _ESCAPES, str(_ESCAPES[:5]))

ok = sum(1 for r in resultados if r[1] == "OK")
falha = sum(1 for r in resultados if r[1] == "FALHA")
print(f"\n{ok} OK · {falha} FALHA (de {len(resultados)})")
sys.exit(1 if falha else 0)
