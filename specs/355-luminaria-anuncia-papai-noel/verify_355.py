"""Verificação do ajuste 355 — a luminária anuncia o Papai Noel (origem `luminaria` na loja).

Roda contra um espelho do dump de produção de 19/11/2026 02:00. Escrito ANTES da mudança
(Princípio VIII): sem `luminaria` em `VIRTUAL_ORIGENS`, os cenários 1–3 FALHAM (a visita cai em
"outro").

  1  normalizar_origem reduz luminaria/Luminaria a `luminaria`
  2  visita com origem=luminaria conta em `luminaria`, não em `outro`
  3  funil mostra a linha "Luminária" e o link ?origem=luminaria
  4  origem desconhecida continua em `outro` (deve falhar se a lista abrir)
  5  funil sem papel de loja → 403 (deve falhar)
  6  limpeza; nenhuma conexão externa

O cartão do menu da tag é só tela (frontend): conferido no Browser pane, ver `spec.md`.

Uso:
    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONPATH = (Get-Location).Path; $env:PYTHONUTF8 = '1'
    <python> specs\\355-luminaria-anuncia-papai-noel\\verify_355.py
"""

from __future__ import annotations

import os
import secrets
import socket
import sys
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
        raise OSError(f"[verify_355] conexão externa bloqueada: {host}")
    return _create_connection_original(address, *args, **kwargs)


socket.create_connection = _so_local

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, email_service, limiter  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.marketing import virtuais_ops as ops  # noqa: E402
from app.models import CatalogCharacter, User  # noqa: E402

RUN = secrets.token_hex(3)
PASSWORD = f"verify-355-{secrets.token_hex(6)}"
app = create_app()
_engine = create_engine(os.environ["DATABASE_URL"].strip())

# Nenhum e-mail sai (nada aqui deveria mandar, mas o espelho tem credenciais reais).
EMAILS: list[dict] = []
email_service._send = lambda **kw: EMAILS.append(kw) or True


def _db(sql: str, **p):
    # Conexão separada: o autoflush da sessão do app esconderia um commit que não aconteceu.
    with _engine.connect() as conn:
        return conn.execute(text(sql), p).fetchall()


resultados: list[tuple[str, str, str]] = []


class Bloqueado(Exception):
    pass


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
SENHAS_ORIGINAIS: dict[int, str | None] = {}

with app.app_context():
    PERSONAGEM_ID = CatalogCharacter.query.filter_by(is_active=True).first().id
    camp = ops.criar_campanha(
        catalog_character_id=PERSONAGEM_ID,
        title=f"Verify355 {RUN}",
        price_live=Decimal("100.00"),
        price_recorded=Decimal("60.00"),
        recorded_capacity=5,
        tolerance_terms="termos",
        cover_url="/catalogo/midia/campanhas/x.jpg",
    )
    camp.status = "publicada"
    db.session.commit()
    CAMP_ID, SLUG = camp.id, camp.slug

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
            SENHAS_ORIGINAIS[u.id] = u.password_hash
            u.set_password(PASSWORD)
            USUARIOS[papel] = u.email
    db.session.commit()

limiter.enabled = False


def login(papel: str) -> None:
    if papel not in USUARIOS:
        raise Bloqueado(f"sem usuário {papel} no espelho")
    client.post("/api/auth/logout")
    r = client.post("/api/auth/login", json={"email": USUARIOS[papel], "password": PASSWORD})
    if r.status_code != 200:
        raise Bloqueado(f"login {papel}: {r.status_code}")


def logout() -> None:
    client.post("/api/auth/logout")


def visita(origem) -> int:
    corpo = {} if origem is None else {"origem": origem}
    return client.post(f"/api/virtuais/campanhas/{SLUG}/visita", json=corpo).status_code


def contagem() -> dict[str, int]:
    linhas = _db(
        "select origem, visits from virtual_campaign_visits where campaign_id=:c and day=:d",
        c=CAMP_ID,
        d=now_sp().date(),
    )
    return {o: n for o, n in linhas}


# ── Cenários ────────────────────────────────────────────────────────────────────────────────
@cenario("1  normalizar_origem reconhece a luminária")
def c1():
    check(
        "1.1 luminaria",
        ops.normalizar_origem("luminaria") == "luminaria",
        ops.normalizar_origem("luminaria"),
    )
    check(
        "1.2 Luminaria com maiúscula",
        ops.normalizar_origem(" Luminaria ") == "luminaria",
        ops.normalizar_origem(" Luminaria "),
    )


@cenario("2  visita com origem=luminaria conta na luminária")
def c2():
    logout()
    st = visita("luminaria")
    check("2.1 204", st == 204, str(st))
    cont = contagem()
    check("2.2 1 visita em luminaria", cont.get("luminaria") == 1, str(cont))
    check("2.3 nada em outro", "outro" not in cont, str(cont))


@cenario("3  funil mostra a linha Luminária e o link do canal")
def c3():
    login("gestor")
    r = client.get(f"/api/virtuais/campanhas/{CAMP_ID}/funil")
    corpo = r.get_json() or {}
    check("3.1 200", r.status_code == 200, f"{r.status_code} {str(corpo)[:160]}")
    linha = next((x for x in corpo.get("por_origem", []) if x.get("origem") == "luminaria"), {})
    check(
        "3.2 linha luminaria com 1 visita", linha.get("visitas") == 1, str(corpo.get("por_origem"))
    )
    check("3.3 rótulo Luminária", linha.get("rotulo") == "Luminária", str(linha.get("rotulo")))
    links = {x.get("origem"): x.get("url") for x in corpo.get("links", [])}
    check(
        "3.4 link da luminária no domínio da loja",
        links.get("luminaria") == f"https://alo.mantoproducoes.com.br/{SLUG}?origem=luminaria",
        str(links.get("luminaria")),
    )
    logout()


@cenario("4  origem desconhecida segue em outro (deve falhar se a lista abrir)")
def c4():
    visita("lumi-panfleto")
    cont = contagem()
    check("4.1 desconhecida vira outro", cont.get("outro") == 1, str(cont))
    check("4.2 nenhuma origem nova inventada", "lumi-panfleto" not in cont, str(cont))


@cenario("5  funil sem papel de loja → 403 (deve falhar)")
def c5():
    login("outro")
    r = client.get(f"/api/virtuais/campanhas/{CAMP_ID}/funil")
    check("5.1 403", r.status_code == 403, str(r.status_code))
    logout()


def limpar() -> None:
    with app.app_context():
        db.session.rollback()
    with _engine.begin() as conn:
        conn.execute(
            text("delete from virtual_campaign_visits where campaign_id=:c"), {"c": CAMP_ID}
        )
        conn.execute(
            text("delete from virtual_campaign_slots where campaign_id=:c"), {"c": CAMP_ID}
        )
        tem_acervo = conn.execute(
            text(
                "select 1 from information_schema.tables where table_name='virtual_campaign_acervo'"
            )
        ).first()
        if tem_acervo:
            conn.execute(
                text("delete from virtual_campaign_acervo where campaign_id=:c"), {"c": CAMP_ID}
            )
        conn.execute(text("delete from virtual_campaigns where id=:c"), {"c": CAMP_ID})
        for uid, h in SENHAS_ORIGINAIS.items():
            conn.execute(text("update users set password_hash=:h where id=:u"), {"h": h, "u": uid})


@cenario("6  limpeza; nenhuma conexão externa")
def c6():
    limpar()
    check(
        "6.1 campanha removida", not _db("select 1 from virtual_campaigns where id=:c", c=CAMP_ID)
    )
    check("6.2 nenhuma conexão externa", not _ESCAPES, str(_ESCAPES))
    check("6.3 nenhum e-mail", not EMAILS, str(len(EMAILS)))


if __name__ == "__main__":
    try:
        for fn in (c1, c2, c3, c4, c5):
            fn()
    finally:
        c6()
    falhas = [r for r in resultados if r[1] != "OK"]
    print(f"\n{len(resultados) - len(falhas)}/{len(resultados)} OK")
    sys.exit(1 if falhas else 0)
