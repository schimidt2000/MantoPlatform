"""Verificação da feature 351 — painel atribuído.

Roda contra o `manto_351` (dump de produção de 17/11/2026 02:00 + migration a351). Escrito ANTES do núcleo
(Princípio VIII): sem as rotas e os campos novos, os cenários FALHAM ou ficam BLOQUEADOS.

   1  venda atribuída à frente da campanha            15  Marketing salva calendário/meta (DEVE FALHAR: 403)
   2  evento criado antes do contato: não atribui     16  contexto da rotina traz calendário e metas
   3  46 dias depois do contato: não atribui          17  proposta: números do texto e impacto mensal
   4  dois contatos: vale o último                    18  frente e teto da proposta
   5  origem da ficha (utm): nova atribui, antiga não 19  sino da proposta, sem duplicar
   6  período parcial; desconto de 50%               20  diário: antes, depois, controle, linha de base
   7  funil por frente e por anúncio, com custo       21  diário com janela em andamento
   8  funil do Comercial: sem dinheiro                22  proposta executada → diário herda alvo/métrica
   9  funil por peça e por conceito                   23  lista do Kanban traz frente, tipo e conceito
  10  resultado real do card                          24  Temas paginado
  11  "no ar" pelo gasto da última leitura            25  custo por cliente novo de anúncio
  12  card de anúncio em Agendado segue na fila       26  Comercial pede a atribuição (DEVE FALHAR: 403)
  13  conceito salvo no card                          27  valor da venda só para o Superadmin
  14  meta, verba e calendário salvos                 28  limpeza; nenhuma conexão externa

Todos os dados de teste ficam em 2031 (contatos, eventos, gasto) com o prefixo "V351 <run>": nada encosta no
histórico real do espelho. Usuários descartáveis (Superadmin, Marketing, Comercial); token do agente gerado aqui.

Uso (na raiz do worktree):
    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONPATH = (Get-Location).Path; $env:PYTHONUTF8 = '1'
    <python> specs\\351-painel-atribuido\\verify_351.py
"""

from __future__ import annotations

import math
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
        raise OSError(f"[verify_351] conexão externa bloqueada: {host}")
    return _create_connection_original(address, *args, **kwargs)


socket.create_connection = _so_local

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import Role, User  # noqa: E402

RUN = secrets.token_hex(3)
PASSWORD = f"verify-351-{secrets.token_hex(6)}"
TOKEN = f"tok351-{RUN}-{secrets.token_hex(8)}"
app = create_app()
app.config["MARKETING_AGENT_TOKEN"] = TOKEN
_engine = create_engine(os.environ["DATABASE_URL"].strip())

PREFIXO = f"V351 {RUN}"
INI, FIM = "2031-03-01", "2031-03-31"
CAMP_FESTA, ID_FESTA = f"FESTA · MSG · {PREFIXO}", f"c351f{RUN}"
CAMP_CORP, ID_CORP = f"CORP · MSG · {PREFIXO}", f"c351c{RUN}"
CAMP_SEM, ID_SEM = f"Sem prefixo {PREFIXO}", f"c351s{RUN}"
CAMP_GOOGLE, ID_GOOGLE = f"FESTA · Busca · {PREFIXO}", f"c351g{RUN}"
A1, A2, A3, A4, A5, A6 = (f"a351{RUN}{n}" for n in range(1, 7))
CONCEITO = f"Mãe surpresa {PREFIXO}"
MES_ATUAL = now_sp().month


def _db(sql: str, **p):
    # Conexão separada: o autoflush da sessão do app esconderia um commit que não aconteceu.
    with _engine.connect() as conn:
        return conn.execute(text(sql), p).fetchall()


def _exec(sql: str, **p):
    with _engine.begin() as conn:
        return conn.execute(text(sql), p)


def _id(sql: str, **p) -> int:
    return _db(sql, **p)[0][0]


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
            except Bloqueado as exc:
                resultados.append((nome, "BLOQUEADO", str(exc)))
                print(f"BLOQUEADO {nome}  [{exc}]", flush=True)
            except Exception as exc:  # noqa: BLE001 — o verify registra e segue para o próximo cenário
                with app.app_context():
                    db.session.rollback()
                resultados.append((nome, "FALHA", f"{type(exc).__name__}: {exc}"[:300]))
                print(f"FALHA     {nome}  [{type(exc).__name__}: {str(exc)[:240]}]", flush=True)

        run.__name__ = fn.__name__
        return run

    return deco


# ── Usuários descartáveis ───────────────────────────────────────────────────────────────────
client = app.test_client()
USUARIOS: dict[str, str] = {}
USER_IDS: dict[str, int] = {}
with app.app_context():
    for papel, role_name in (
        ("sa", RoleName.SUPERADMIN),
        ("mkt", RoleName.MARKETING),
        ("com", RoleName.COMERCIAL),
    ):
        u = User(
            name=f"{PREFIXO} {papel}",
            email=f"verify351-{papel}-{RUN}@example.invalid",
            has_access=True,
            is_active=True,
            receives_commission=False,
        )
        u.set_password(PASSWORD)
        u.roles.append(Role.query.filter_by(name=role_name).one())
        db.session.add(u)
        db.session.flush()
        USUARIOS[papel], USER_IDS[papel] = u.email, u.id
    db.session.commit()
limiter.enabled = False

# Fotografia do que os cenários 14/15 alteram (restaurada na limpeza).
FRENTES_ANTES = _db(
    "select slug, teto_custo_venda, meta_vendas_mes, verba_mes from marketing_frentes"
)
CALENDARIO_ANTES = _db("select frente, mes, meta_vendas, verba, foco from marketing_calendario")


def login(papel: str) -> None:
    client.post("/api/auth/logout")
    r = client.post("/api/auth/login", json={"email": USUARIOS[papel], "password": PASSWORD})
    if r.status_code != 200:
        raise Bloqueado(f"login {papel}: {r.status_code}")


def precisa(r, rota: str) -> None:
    if r.status_code == 404 and not (r.get_json(silent=True) or {}).get("error"):
        raise Bloqueado(f"{rota} ainda não existe")
    if r.status_code == 405:
        raise Bloqueado(f"{rota} ainda não existe (405)")


# ── Semeadura (2031) ────────────────────────────────────────────────────────────────────────
EVENTOS: dict[str, int] = {}
CLIENTES: dict[str, int] = {}
CONVERSAS: dict[str, int] = {}
POSTS: dict[str, int] = {}


def novo_cliente(nome: str, *, criado: str, source: str = "manual", **extra) -> int:
    fone = f"5598{secrets.randbelow(10**9):09d}"
    colunas = ", ".join(["name", "phone", "source", "created_at", "updated_at", *extra])
    valores = ", ".join([":n", ":p", ":s", ":c", ":c", *(f":{k}" for k in extra)])
    _exec(
        f"insert into clients ({colunas}) values ({valores})",  # noqa: S608 — colunas fixas do verify
        n=f"{PREFIXO} {nome}",
        p=fone,
        s=source,
        c=criado,
        **extra,
    )
    CLIENTES[nome] = _id("select id from clients where phone=:p", p=fone)
    return CLIENTES[nome]


def novo_evento(nome: str, *, cliente: int, criado: str, venda: str, data_venda: str) -> int:
    gid = f"v351{RUN}{nome}"
    _exec(
        "insert into calendar_events (google_event_id, title, start_at, end_at, created_at, updated_at,"
        " sale_value, sale_date, client_id, is_cortesia_permuta, source)"
        " values (:g, :t, :i, :i, :c, :c, :v, :d, :cl, false, 'platform')",
        g=gid,
        t=f"Festa {PREFIXO} {nome}",
        i="2031-04-20 15:00",
        c=criado,
        v=venda,
        d=data_venda,
        cl=cliente,
    )
    EVENTOS[nome] = _id("select id from calendar_events where google_event_id=:g", g=gid)
    _exec(
        "insert into event_clients (event_id, client_id, created_at) values (:e, :c, now())",
        e=EVENTOS[nome],
        c=cliente,
    )
    return EVENTOS[nome]


def nova_conversa(nome: str, cliente: int, contatos: list[tuple[str, str]]) -> int:
    _exec(
        "insert into conversas (canal, contato_id, client_id) values ('whatsapp', :c, :cl)",
        c=f"v351{RUN}{nome}",
        cl=cliente,
    )
    cid = _id("select id from conversas where contato_id=:c", c=f"v351{RUN}{nome}")
    CONVERSAS[nome] = cid
    for i, (anuncio, momento) in enumerate(contatos):
        _exec(
            "insert into conversa_anuncios (conversa_id, canal, chave, tipo, anuncio_id, momento, created_at)"
            " values (:cv, 'whatsapp', :k, 'anuncio', :a, :m, :m)",
            cv=cid,
            k=f"v351{RUN}{nome}{i}",
            a=anuncio,
            m=momento,
        )
    return cid


def semear() -> None:
    for anuncio, nome, camp_id, camp_nome in (
        (A1, "Peça mãe", ID_FESTA, CAMP_FESTA),
        (A2, "Peça empresa", ID_CORP, CAMP_CORP),
        (A3, "Peça bastidores", ID_FESTA, CAMP_FESTA),
        (A4, "Peça sem frente", ID_SEM, CAMP_SEM),
    ):
        _exec(
            "insert into anuncios_meta (anuncio_id, nome, campanha_id, campanha_nome, consultado_em, definitivo)"
            " values (:a, :n, :ci, :cn, now(), false)",
            a=anuncio,
            n=f"{nome} {PREFIXO}",
            ci=camp_id,
            cn=camp_nome,
        )
    _exec(
        "insert into marketing_agent_runs (run_id, mode, window_start, window_end, executed_at)"
        " values (:r, 'local', '2031-03-01', '2031-03-31', now())",
        r=f"v351-{RUN}",
    )
    run_id = _id("select id from marketing_agent_runs where run_id=:r", r=f"v351-{RUN}")
    for plat, cid, nome, gasto, conv in (
        ("Meta Ads", ID_FESTA, CAMP_FESTA, "600.00", 20),
        ("Meta Ads", ID_CORP, CAMP_CORP, "300.00", 5),
        ("Meta Ads", ID_SEM, CAMP_SEM, "100.00", 2),
        ("Google Ads", ID_GOOGLE, CAMP_GOOGLE, "400.00", 0),
    ):
        _exec(
            "insert into marketing_campaign_metrics (platform, campaign_id, campaign_name, period_start,"
            " period_end, is_daily, spend, currency, conversations, run_id)"
            " values (:pl, :ci, :cn, '2031-03-02', '2031-03-02', true, :g, 'BRL', :cv, :r)",
            pl=plat,
            ci=cid,
            cn=nome,
            g=gasto,
            cv=conv,
            r=run_id,
        )
    linhas = [
        (A1, ID_FESTA, "2031-03-02", "150.00", 6),
        (A1, ID_FESTA, "2031-03-20", "60.00", 2),
        (A3, ID_FESTA, "2031-03-02", "100.00", 3),
        (A3, ID_FESTA, "2031-03-20", "0.00", 0),
    ]
    # Teste do diário: A5 (alvo) 10 → 15 conversas; A6 (controle) 10 → 11, em torno de 15/03.
    for dia in range(8, 22):
        antes = dia < 15
        linhas.append(
            (
                A5,
                ID_FESTA,
                f"2031-03-{dia:02d}",
                "10.00",
                (10 if dia == 8 else 0) if antes else (15 if dia == 15 else 0),
            )
        )
        linhas.append(
            (
                A6,
                ID_FESTA,
                f"2031-03-{dia:02d}",
                "10.00",
                (10 if dia == 8 else 0) if antes else (11 if dia == 15 else 0),
            )
        )
    for ad, camp, dia, gasto, conv in linhas:
        _exec(
            "insert into marketing_ad_metrics (platform, ad_id, campaign_id, adset_id, metric_date, spend,"
            " currency, conversations, updated_at) values ('Meta Ads', :a, :c, 's351', :d, :g, 'BRL', :cv, now())",
            a=ad,
            c=camp,
            d=dia,
            g=gasto,
            cv=conv,
        )

    sa = USER_IDS["sa"]
    k1 = novo_cliente(
        "K1", criado="2031-03-03 13:00", anuncio_origem_id=A1, anuncio_origem_em="2031-03-03 13:00"
    )
    nova_conversa("V1", k1, [(A1, "2031-03-03 13:00")])
    _exec(
        "insert into orcamento_history (user_id, created_at, has_show, client_id, client_name)"
        " values (:u, '2031-03-04 12:00', false, :c, :n)",
        u=sa,
        c=k1,
        n=f"{PREFIXO} K1",
    )
    novo_evento(
        "E1", cliente=k1, criado="2031-03-05 12:00", venda="3000.00", data_venda="2031-03-08"
    )

    k2 = novo_cliente(
        "K2", criado="2031-03-10 13:00", anuncio_origem_id=A1, anuncio_origem_em="2031-03-10 13:00"
    )
    nova_conversa("V2", k2, [(A1, "2031-03-10 13:00")])
    novo_evento(
        "E2", cliente=k2, criado="2031-03-09 12:00", venda="2000.00", data_venda="2031-03-12"
    )

    k3 = novo_cliente(
        "K3", criado="2031-01-20 13:00", anuncio_origem_id=A1, anuncio_origem_em="2031-01-20 13:00"
    )
    nova_conversa("V3", k3, [(A1, "2031-01-20 13:00")])
    novo_evento(
        "E3", cliente=k3, criado="2031-01-25 12:00", venda="2500.00", data_venda="2031-03-07"
    )

    k4 = novo_cliente(
        "K4",
        criado="2031-03-02 13:00",
        anuncio_origem_id=A1,
        anuncio_origem_em="2031-03-02 13:00",
        anuncio_recente_id=A2,
        anuncio_recente_em="2031-03-06 13:00",
    )
    nova_conversa("V4", k4, [(A1, "2031-03-02 13:00"), (A2, "2031-03-06 13:00")])
    novo_evento(
        "E4", cliente=k4, criado="2031-03-07 12:00", venda="5000.00", data_venda="2031-03-09"
    )

    k5 = novo_cliente(
        "K5",
        criado="2031-03-01 15:00",
        utm_source="meta",
        utm_medium="ctwa",
        utm_campaign=CAMP_FESTA,
    )
    novo_evento(
        "E5", cliente=k5, criado="2031-03-04 12:00", venda="1500.00", data_venda="2031-03-06"
    )
    k6 = novo_cliente(
        "K6",
        criado="2031-03-01 15:00",
        source="kommo_import",
        utm_source="meta",
        kommo_created_at="2030-01-01 10:00",
    )
    novo_evento(
        "E6", cliente=k6, criado="2031-03-04 12:00", venda="1800.00", data_venda="2031-03-06"
    )

    k7 = novo_cliente(
        "K7", criado="2031-03-11 13:00", anuncio_origem_id=A4, anuncio_origem_em="2031-03-11 13:00"
    )
    nova_conversa("V7", k7, [(A4, "2031-03-11 13:00")])
    novo_evento(
        "E7", cliente=k7, criado="2031-03-12 12:00", venda="3500.00", data_venda="2031-03-14"
    )
    novo_cliente("K8", criado="2031-03-15 15:00")

    for nome, status, conceito, anuncios in (
        ("P1", "publicado", CONCEITO, (A1, A3)),
        ("P2", "pronto", None, (A2,)),
        ("P3", "agendado", None, ()),
    ):
        _exec(
            "insert into marketing_posts (title, status, tipo, frente, origem, conceito, assignee_id, created_at, updated_at)"
            " values (:t, :s, 'anuncio', 'festas', 'pessoa', :c, :u, now(), now())",
            t=f"{PREFIXO} {nome}",
            s=status,
            c=conceito,
            u=USER_IDS["mkt"],
        )
        POSTS[nome] = _id("select id from marketing_posts where title=:t", t=f"{PREFIXO} {nome}")
        for ad in anuncios:
            _exec(
                "insert into marketing_post_anuncios (post_id, platform, ad_id, created_at) values (:p, 'Meta Ads', :a, now())",
                p=POSTS[nome],
                a=ad,
            )


# ── Leitura ─────────────────────────────────────────────────────────────────────────────────
def desempenho(papel: str = "sa", inicio: str = INI, fim: str = FIM) -> dict:
    login(papel)
    r = client.get(f"/api/marketing/desempenho?start={inicio}&end={fim}")
    if r.status_code != 200:
        raise AssertionError(f"desempenho {r.status_code} {r.get_data(as_text=True)[:200]}")
    return r.get_json()


def frente(payload: dict, slug: str) -> dict:
    for f in payload.get("frentes") or []:
        if f.get("slug") == slug:
            return f
    raise Bloqueado(f"frente {slug} ausente do desempenho")


def atribuicao(papel: str = "sa", dividir: str = "frente"):
    login(papel)
    return client.get(f"/api/marketing/atribuicao?start={INI}&end={FIM}&dividir={dividir}")


def atribuicao_ok(papel: str = "sa", dividir: str = "frente") -> dict:
    r = atribuicao(papel, dividir)
    precisa(r, "GET /api/marketing/atribuicao")
    if r.status_code != 200:
        raise AssertionError(f"atribuicao {r.status_code} {r.get_data(as_text=True)[:200]}")
    return r.get_json()


def venda_da_lista(dados: dict, evento: str) -> dict | None:
    return next((v for v in dados.get("vendas", []) if v.get("event_id") == EVENTOS[evento]), None)


def grupo(dados: dict, chave: str) -> dict | None:
    return next(
        (g for g in (dados.get("funil") or dados).get("grupos", []) if g.get("chave") == chave),
        None,
    )


# ── Cenários ────────────────────────────────────────────────────────────────────────────────
@cenario("1 venda atribuída à frente da campanha")
def c1():
    f = frente(desempenho(), "festas")
    if "vendas_atribuidas" not in f:
        raise Bloqueado("desempenho ainda sem vendas_atribuidas")
    check(
        "1.1 festas: 2 vendas atribuídas (E1 por conversa, E5 por origem)",
        f["vendas_atribuidas"] == 2,
        str(f),
    )
    check("1.2 festas: misto conta as 7 vendas da frente", f["vendas"] == 7, str(f["vendas"]))
    check(
        "1.3 custo atribuído = 1000 ÷ 2",
        f.get("custo_venda_atribuida") == "500.00",
        str(f.get("custo_venda_atribuida")),
    )
    check(
        "1.4 faturamento atribuído = 4500",
        f.get("faturamento_atribuido") == "4500.00",
        str(f.get("faturamento_atribuido")),
    )
    dados = atribuicao_ok()
    v1 = venda_da_lista(dados, "E1")
    check(
        "1.5 E1 na lista, contato pela conversa do anúncio A1",
        bool(v1) and v1["contato"]["fonte"] == "conversa" and v1["contato"]["anuncio_id"] == A1,
        str(v1),
    )


@cenario("2 evento criado antes do contato não é atribuído")
def c2():
    dados = atribuicao_ok()
    check("2.1 E2 fora da lista", venda_da_lista(dados, "E2") is None)


@cenario("3 venda 46 dias depois do contato não é atribuída")
def c3():
    dados = atribuicao_ok()
    check("3.1 E3 fora da lista", venda_da_lista(dados, "E3") is None)


@cenario("4 dois contatos: vale o último")
def c4():
    dados = atribuicao_ok()
    v4 = venda_da_lista(dados, "E4")
    check(
        "4.1 E4 atribuída a Corporativo (A2, o último)",
        bool(v4) and v4["frente"] == "corporativo" and v4["contato"]["anuncio_id"] == A2,
        str(v4),
    )
    check(
        "4.2 a frente do evento continua Festas",
        bool(v4) and v4["frente_venda"] == "festas",
        str(v4),
    )
    f = frente(desempenho(), "corporativo")
    check(
        "4.3 corporativo: 1 atribuída, custo 300",
        f["vendas_atribuidas"] == 1 and f["custo_venda_atribuida"] == "300.00",
        str(f),
    )


@cenario("5 origem da ficha: nova atribui, antiga não")
def c5():
    dados = atribuicao_ok()
    v5 = venda_da_lista(dados, "E5")
    check(
        "5.1 E5 (ficha nova com utm meta) atribuída a Festas",
        bool(v5) and v5["frente"] == "festas" and v5["contato"]["fonte"] == "utm",
        str(v5),
    )
    check("5.2 E6 (ficha antiga do Kommo) fora da lista", venda_da_lista(dados, "E6") is None)


@cenario("6 período parcial e desconto de 50%")
def c6():
    d = desempenho(inicio="2026-05-01", fim="2026-05-31")
    at = d.get("atribuicao")
    if at is None:
        raise Bloqueado("desempenho ainda sem o bloco atribuicao")
    check("6.1 período de maio/2026 marcado como parcial", at.get("parcial") is True, str(at))
    check(
        "6.2 regra declarada: 45 dias, 0,50",
        at.get("janela_dias") == 45 and at.get("incrementalidade") == "0.50",
        str(at),
    )
    f = frente(desempenho(), "festas")
    check(
        "6.3 com desconto = 1000 ÷ (2 × 0,5)",
        f.get("custo_venda_atribuida_desconto") == "1000.00",
        str(f.get("custo_venda_atribuida_desconto")),
    )
    login("sa")
    longo = client.get("/api/marketing/atribuicao?start=2030-01-01&end=2031-03-31").get_json() or {}
    check(
        "6.5 período de mais de um ano: lista com E1 e o funil com aviso",
        venda_da_lista(longo, "E1") is not None and bool((longo.get("funil") or {}).get("aviso")),
        str(longo.get("funil"))[:200],
    )
    sem = desempenho().get("atribuicao", {}).get("sem_frente", {})
    check(
        "6.4 E7 (campanha sem frente) no bloco sem frente",
        sem.get("vendas") == 1 and sem.get("faturamento") == "3500.00",
        str(sem),
    )


@cenario("7 funil por frente e por anúncio, com custo")
def c7():
    dados = atribuicao_ok(dividir="frente")
    g = grupo(dados, "festas")
    check("7.1 festas: 3 conversas chegaram", bool(g) and g["quantidades"]["chegou"] == 3, str(g))
    check(
        "7.2 festas: 2 com orçamento, 2 com evento",
        bool(g) and g["quantidades"]["orcamento"] == 2 and g["quantidades"]["evento"] == 2,
        str(g),
    )
    check(
        "7.3 gasto só da Meta (600) e custos",
        bool(g)
        and g.get("gasto") == "600.00"
        and g.get("custo_conversa") == "200.00"
        and g.get("custo_evento") == "300.00",
        str(g),
    )
    check(
        "7.4 conversa de campanha sem frente no grupo próprio",
        grupo(dados, "__sem_frente__") is not None,
        str((dados.get("funil") or {}).get("grupos")),
    )
    por_anuncio = atribuicao_ok(dividir="anuncio")
    ga = grupo(por_anuncio, A1)
    check(
        "7.5 anúncio A1: 3 conversas, gasto 210, 70 por conversa",
        bool(ga)
        and ga["quantidades"]["chegou"] == 3
        and ga.get("gasto") == "210.00"
        and ga.get("custo_conversa") == "70.00",
        str(ga),
    )


@cenario("8 funil do Comercial dividido por frente: sem dinheiro")
def c8():
    login("com")
    r = client.get(f"/api/conversas/funil?inicio={INI}&fim={FIM}&dividir=frente")
    check(
        "8.1 Comercial divide por frente (200)",
        r.status_code == 200,
        f"{r.status_code} {r.get_data(as_text=True)[:200]}",
    )
    corpo = r.get_data(as_text=True)
    check(
        "8.2 nenhuma chave de dinheiro no payload", "gasto" not in corpo and "custo_" not in corpo
    )
    d = r.get_json() or {}
    g = next((x for x in d.get("grupos", []) if x.get("chave") == "festas"), None)
    check(
        "8.3 grupo festas com as 3 conversas",
        bool(g) and g["quantidades"]["chegou"] == 3,
        str(d.get("grupos")),
    )


@cenario("9 funil por peça e por conceito")
def c9():
    por_peca = atribuicao_ok(dividir="peca")
    g = grupo(por_peca, str(POSTS["P1"]))
    check(
        "9.1 peça P1 com as 3 conversas do A1", bool(g) and g["quantidades"]["chegou"] == 3, str(g)
    )
    check(
        "9.2 conversa de anúncio sem card em 'sem peça'",
        grupo(por_peca, "__sem_peca__") is not None,
    )
    por_conceito = atribuicao_ok(dividir="conceito")
    gc = grupo(por_conceito, CONCEITO)
    check(
        "9.3 conceito da P1 com 3 conversas e gasto dos anúncios da peça (310)",
        bool(gc) and gc["quantidades"]["chegou"] == 3 and gc.get("gasto") == "310.00",
        str(gc),
    )


def post(nome: str) -> dict:
    login("sa")
    r = client.get(f"/api/marketing/posts/{POSTS[nome]}")
    if r.status_code != 200:
        raise AssertionError(f"post {r.status_code}")
    return r.get_json()


@cenario("10 resultado real do card")
def c10():
    res = post("P1").get("resultado") or {}
    if "conversas_reais" not in res:
        raise Bloqueado("card ainda sem conversas_reais")
    check("10.1 conversas reais = 4 (V1, V2, V3, V4)", res["conversas_reais"] == 4, str(res))
    check(
        "10.2 orçamentos = 3 e eventos = 3",
        res.get("orcamentos") == 3 and res.get("eventos") == 3,
        str(res),
    )
    check(
        "10.3 vendas atribuídas = 1 (E1), faturamento 3000",
        res.get("vendas") == 1 and res.get("faturamento") == "3000.00",
        str(res),
    )


@cenario("11 'no ar' pelo gasto da última leitura")
def c11():
    p = post("P1")
    por_ad = {a["ad_id"]: a for a in p.get("anuncios", [])}
    if "no_ar" not in por_ad.get(A1, {}):
        raise Bloqueado("anúncio do card ainda sem no_ar")
    check("11.1 A1 gastou na última leitura: no ar", por_ad[A1]["no_ar"] is True, str(por_ad[A1]))
    check(
        "11.2 A3 sem gasto desde 02/03: não está no ar",
        por_ad[A3]["no_ar"] is False and por_ad[A3]["ultimo_gasto_em"] == "2031-03-02",
        str(por_ad[A3]),
    )
    check(
        "11.3 card conta 1 anúncio no ar",
        (p.get("resultado") or {}).get("anuncios_no_ar") == 1,
        str(p.get("resultado")),
    )


@cenario("12 card de anúncio em Agendado segue na fila da rotina")
def c12():
    r = client.get(f"/api/marketing-agent/{TOKEN}/comando?start={INI}&end={FIM}")
    fila = {c["id"] for c in (r.get_json() or {}).get("cards_prontos_sem_anuncio", [])}
    check("12.1 P3 (agendado, sem anúncio) na fila", POSTS["P3"] in fila, str(sorted(fila))[:200])
    check("12.2 P1 (com anúncio) fora da fila", POSTS["P1"] not in fila)


@cenario("13 conceito salvo no card")
def c13():
    login("mkt")
    r = client.patch(
        f"/api/marketing/posts/{POSTS['P3']}", json={"conceito": "  Bastidores V351  "}
    )
    check(
        "13.1 PATCH com conceito (200)",
        r.status_code == 200,
        f"{r.status_code} {r.get_data(as_text=True)[:200]}",
    )
    gravado = _db("select conceito from marketing_posts where id=:i", i=POSTS["P3"])[0][0]
    check(
        "13.2 conceito gravado e aparado (conexão separada)",
        gravado == "Bastidores V351",
        repr(gravado),
    )
    r2 = client.patch(f"/api/marketing/posts/{POSTS['P3']}", json={"conceito": "x" * 121})
    campos = ((r2.get_json(silent=True) or {}).get("error") or {}).get("fields") or {}
    check(
        "13.3 conceito longo recusado no campo (400)",
        r2.status_code == 400 and "conceito" in campos,
        f"{r2.status_code} {campos}",
    )


@cenario("14 meta, verba e calendário salvos pelo Superadmin")
def c14():
    login("sa")
    r = client.patch(
        "/api/marketing/frentes", json={"metas": {"festas": 45}, "verbas": {"festas": "2000.00"}}
    )
    check(
        "14.1 PATCH frentes com meta e verba (200)",
        r.status_code == 200,
        f"{r.status_code} {r.get_data(as_text=True)[:200]}",
    )
    linha = _db("select meta_vendas_mes, verba_mes from marketing_frentes where slug='festas'")[0]
    check(
        "14.2 meta 45 e verba 2000 gravadas",
        linha[0] == 45 and linha[1] == Decimal("2000.00"),
        str(linha),
    )
    r2 = client.patch(
        "/api/marketing/calendario",
        json={
            "frente": "festas",
            "meses": [
                {"mes": MES_ATUAL, "meta_vendas": 50, "verba": "3000.00", "foco": f"Foco {PREFIXO}"}
            ],
        },
    )
    precisa(r2, "PATCH /api/marketing/calendario")
    check(
        "14.3 PATCH calendário (200)",
        r2.status_code == 200,
        f"{r2.status_code} {r2.get_data(as_text=True)[:200]}",
    )
    cal = _db(
        "select meta_vendas, verba, foco from marketing_calendario where frente='festas' and mes=:m",
        m=MES_ATUAL,
    )[0]
    check(
        "14.4 mês corrente gravado (conexão separada)",
        cal[0] == 50 and cal[1] == Decimal("3000.00") and cal[2] == f"Foco {PREFIXO}",
        str(cal),
    )
    mc = frente(desempenho(), "festas").get("mes_corrente") or {}
    check(
        "14.5 card do mês: a meta do mês vence a padrão",
        mc.get("meta_vendas") == 50 and mc.get("verba") == "3000.00",
        str(mc),
    )
    from app.marketing import comando_ops

    with app.app_context():
        outro = comando_ops.metas_do_mes(MES_ATUAL % 12 + 1)["festas"]
    check("14.6 outro mês usa o padrão da frente (45)", outro["meta_vendas"] == 45, str(outro))


@cenario("15 Marketing tenta salvar calendário e meta (DEVE FALHAR)")
def c15():
    login("mkt")
    r = client.patch(
        "/api/marketing/calendario",
        json={"frente": "festas", "meses": [{"mes": 1, "meta_vendas": 1}]},
    )
    precisa(r, "PATCH /api/marketing/calendario")
    check("15.1 calendário recusado (403)", r.status_code == 403, str(r.status_code))
    r2 = client.patch("/api/marketing/frentes", json={"metas": {"festas": 1}})
    check("15.2 meta recusada (403)", r2.status_code == 403, str(r2.status_code))
    linha = _db("select meta_vendas from marketing_calendario where frente='festas' and mes=1")[0][
        0
    ]
    check("15.3 nada gravado", linha != 1, str(linha))


@cenario("16 contexto da rotina traz calendário e metas do mês")
def c16():
    r = client.get(f"/api/marketing-agent/{TOKEN}/comando?start={INI}&end={FIM}")
    d = r.get_json() or {}
    cal = d.get("calendario")
    if cal is None:
        raise Bloqueado("contexto ainda sem calendario")
    check(
        "16.1 calendário com 5 frentes × 12 meses",
        len(cal) == 5 and all(len(f["meses"]) == 12 for f in cal),
        str(len(cal)),
    )
    metas = d.get("metas_do_mes") or {}
    check(
        "16.2 metas do mês: festas 50",
        (metas.get("festas") or {}).get("meta_vendas") == 50,
        str(metas.get("festas")),
    )


PROPOSTAS: dict[str, int] = {}


def agente_proposta(nome: str, corpo: dict) -> int:
    r = client.post(
        f"/api/marketing-agent/{TOKEN}/propostas", json={"motivo": f"{PREFIXO} {nome}", **corpo}
    )
    if r.status_code != 201:
        raise AssertionError(f"proposta {nome}: {r.status_code} {r.get_data(as_text=True)[:200]}")
    PROPOSTAS[nome] = r.get_json()["id"]
    return PROPOSTAS[nome]


def propostas() -> dict:
    login("sa")
    r = client.get("/api/marketing/propostas")
    return r.get_json() or {}


def proposta_item(dados: dict, nome: str) -> dict:
    return next(p for p in dados.get("items", []) if p["id"] == PROPOSTAS[nome])


@cenario("17 proposta: números do texto e impacto mensal")
def c17():
    antes = propostas().get("impacto_aprovado_mes")
    pid = agente_proposta(
        "verba",
        {
            "tipo": "verba",
            "platform": "Meta Ads",
            "alvo_tipo": "campanha",
            "alvo_id": ID_FESTA,
            "alvo_nome": CAMP_FESTA,
            "valor_antes": "R$ 30,00/dia",
            "valor_depois": "R$ 45,00/dia",
        },
    )
    linha = _db(
        "select valor_antes_num, valor_depois_num, frente from marketing_propostas where id=:i",
        i=pid,
    )[0]
    check(
        "17.1 números lidos do texto (30 → 45)",
        linha[0] == Decimal("30.00") and linha[1] == Decimal("45.00"),
        str(linha),
    )
    item = proposta_item(propostas(), "verba")
    if "impacto_mensal" not in item:
        raise Bloqueado("proposta ainda sem impacto_mensal")
    check(
        "17.2 impacto mensal = (45 − 30) × 30 = 450",
        item["impacto_mensal"] == "450.00",
        str(item.get("impacto_mensal")),
    )
    login("sa")
    client.post(f"/api/marketing/propostas/{pid}/decidir", json={"decisao": "aprovar"})
    depois = propostas().get("impacto_aprovado_mes")
    check(
        "17.3 aprovada entra na soma do mês (+450)",
        antes is not None
        and depois is not None
        and Decimal(depois) - Decimal(antes) == Decimal("450.00"),
        f"{antes} → {depois}",
    )


@cenario("18 frente e teto da proposta")
def c18():
    agente_proposta(
        "pausa",
        {
            "tipo": "pausar",
            "platform": "Meta Ads",
            "alvo_tipo": "campanha",
            "alvo_id": ID_CORP,
            "alvo_nome": CAMP_CORP,
            "valor_antes": "R$ 10,00/dia",
        },
    )
    agente_proposta(
        "ativar",
        {
            "tipo": "ativar",
            "platform": "Meta Ads",
            "alvo_tipo": "anuncio",
            "alvo_id": A1,
            "custo_dia_estimado": "20.00",
        },
    )
    dados = propostas()
    pausa, ativar, verba = (proposta_item(dados, n) for n in ("pausa", "ativar", "verba"))
    check(
        "18.1 campanha CORP → frente corporativo",
        pausa.get("frente") == "corporativo",
        str(pausa.get("frente")),
    )
    check(
        "18.2 pausa: impacto −300",
        pausa.get("impacto_mensal") == "-300.00",
        str(pausa.get("impacto_mensal")),
    )
    check(
        "18.3 anúncio A1 → campanha FESTA → festas; ativar 20/dia → 600",
        ativar.get("frente") == "festas" and ativar.get("impacto_mensal") == "600.00",
        str(ativar),
    )
    with app.app_context():
        from app.marketing import comando_ops

        teto = comando_ops.tetos()["festas"]["teto"]
    esperado = comando_ops.q2(teto) if teto is not None else None
    check(
        "18.4 teto da frente na proposta",
        verba.get("teto") == esperado,
        f"{verba.get('teto')} × {esperado}",
    )


@cenario("19 sino da proposta, sem duplicar")
def c19():
    pid = PROPOSTAS.get("verba")
    if pid is None:
        raise Bloqueado("sem a proposta do cenário 17")
    chave = f"marketing.proposta:{pid}"
    n = _db("select count(*) from notifications where dedupe_key=:k", k=chave)[0][0]
    superadmins = _db(
        "select count(distinct u.id) from users u join user_roles ur on ur.user_id=u.id join roles r on r.id=ur.role_id"
        " where r.name=:r and u.is_active and u.has_access",
        r=RoleName.SUPERADMIN,
    )[0][0]
    check(
        "19.1 uma notificação por Superadmin ativo",
        n == superadmins and n > 0,
        f"{n} × {superadmins}",
    )
    meu = _db(
        "select link_path from notifications where dedupe_key=:k and user_id=:u",
        k=chave,
        u=USER_IDS["sa"],
    )
    check(
        "19.2 link leva a Marketing → Decisões",
        bool(meu) and meu[0][0] == "/marketing/decisoes",
        str(meu),
    )
    from app.models import MarketingProposta
    from app.notificacoes import notificacoes_ops

    with app.app_context():
        notificacoes_ops.notificar_proposta_marketing(MarketingProposta.query.get(pid))
        db.session.commit()
    n2 = _db("select count(*) from notifications where dedupe_key=:k", k=chave)[0][0]
    check("19.3 repetir o aviso não duplica", n2 == n, f"{n} → {n2}")
    nm = _db(
        "select count(*) from notifications where dedupe_key=:k and user_id=:u",
        k=chave,
        u=USER_IDS["mkt"],
    )[0][0]
    check("19.4 Marketing (não decide) não recebe", nm == 0, str(nm))


DIARIO: dict[str, int] = {}


def nova_entrada(nome: str, **extra) -> dict:
    login("mkt")
    r = client.post(
        "/api/marketing/diario", json={"titulo": f"{PREFIXO} {nome}", "motivo": "teste", **extra}
    )
    if r.status_code not in (200, 201):
        raise AssertionError(f"diário {r.status_code} {r.get_data(as_text=True)[:200]}")
    corpo = r.get_json() or {}
    DIARIO[nome] = corpo.get("id") or _id(
        "select id from marketing_diario where titulo=:t", t=f"{PREFIXO} {nome}"
    )
    login("mkt")
    lista = client.get("/api/marketing/diario").get_json() or {}
    return next(e for e in lista.get("items", []) if e["id"] == DIARIO[nome])


@cenario("20 diário: antes, depois, controle e linha de base")
def c20():
    e = nova_entrada(
        "teste",
        alvo_platform="Meta Ads",
        alvo_tipo="anuncio",
        alvo_id=A5,
        metrica="conversas",
        mudou_em="2031-03-15",
        janela_dias=7,
        controle_tipo="anuncio",
        controle_id=A6,
    )
    t = e.get("teste")
    if t is None:
        raise Bloqueado("diário ainda sem teste")
    check(
        "20.1 antes 10, depois 15",
        Decimal(t["antes"]["valor"]) == 10 and Decimal(t["depois"]["valor"]) == 15,
        str(t),
    )
    check(
        "20.2 variação +50%, controle +10%, efeito líquido +40",
        t["variacao"] == 50.0 and t["controle"]["variacao"] == 10.0 and t["efeito_liquido"] == 40.0,
        str(t),
    )
    check("20.3 janela completa (leitura até 21/03)", t["completo"] is True, str(t["completo"]))
    base = _db("select linha_base from marketing_diario where id=:i", i=DIARIO["teste"])[0][0]
    check("20.4 linha de base congelada = 10 (conexão separada)", base == Decimal("10"), str(base))


@cenario("21 diário com a janela do depois em andamento")
def c21():
    e = nova_entrada(
        "andamento",
        alvo_platform="Meta Ads",
        alvo_tipo="anuncio",
        alvo_id=A5,
        metrica="gasto",
        mudou_em="2031-03-20",
    )
    t = e.get("teste")
    if t is None:
        raise Bloqueado("diário ainda sem teste")
    check("21.1 completo = false", t["completo"] is False, str(t))
    check("21.2 janela padrão de 7 dias", t["janela_dias"] == 7, str(t["janela_dias"]))
    login("mkt")
    r = client.post(
        "/api/marketing/diario",
        json={"titulo": f"{PREFIXO} ruim", "motivo": "x", "alvo_id": A5, "metrica": "likes"},
    )
    campos = ((r.get_json(silent=True) or {}).get("error") or {}).get("fields") or {}
    check(
        "21.3 métrica inválida recusada no campo",
        r.status_code == 400 and "metrica" in campos,
        f"{r.status_code} {campos}",
    )


@cenario("22 proposta executada → diário herda alvo e métrica")
def c22():
    pid = PROPOSTAS.get("verba")
    if pid is None:
        raise Bloqueado("sem a proposta do cenário 17")
    r = client.post(
        f"/api/marketing-agent/{TOKEN}/propostas/{pid}/execucao",
        json={"resultado": "executada", "detalhe": "ok"},
    )
    check(
        "22.1 execução registrada (200)",
        r.status_code == 200,
        f"{r.status_code} {r.get_data(as_text=True)[:200]}",
    )
    linha = _db(
        "select alvo_tipo, alvo_id, metrica, alvo_platform from marketing_diario where proposta_id=:p",
        p=pid,
    )
    check(
        "22.2 entrada com alvo da proposta e custo por conversa",
        bool(linha) and tuple(linha[0]) == ("campanha", ID_FESTA, "custo_conversa", "Meta Ads"),
        str(linha),
    )


@cenario("23 lista do Kanban traz frente, tipo, responsável e conceito")
def c23():
    login("mkt")
    itens = client.get("/api/marketing/posts").get_json().get("items", [])
    p1 = next((p for p in itens if p["id"] == POSTS["P1"]), None)
    check(
        "23.1 P1 na lista com as chaves do filtro",
        bool(p1)
        and p1.get("frente") == "festas"
        and p1.get("tipo") == "anuncio"
        and p1.get("assignee_id") == USER_IDS["mkt"],
        str(p1)[:200],
    )
    check(
        "23.2 conceito no payload",
        bool(p1) and p1.get("conceito") == CONCEITO,
        str((p1 or {}).get("conceito")),
    )


@cenario("24 Temas paginado")
def c24():
    login("mkt")
    d = client.get("/api/marketing/temas-licenca?pagina=1").get_json() or {}
    if "total" not in d:
        raise Bloqueado("temas ainda sem paginação")
    ativos = _db("select count(*) from catalog_items where is_active")[0][0]
    check("24.1 total = temas ativos", d["total"] == ativos, f"{d['total']} × {ativos}")
    check("24.2 até 50 por página", len(d["items"]) == min(50, ativos), str(len(d["items"])))
    check(
        "24.3 número de páginas", d["paginas"] == max(1, math.ceil(ativos / 50)), str(d["paginas"])
    )
    ultima = client.get("/api/marketing/temas-licenca?pagina=999").get_json() or {}
    check(
        "24.4 página além da última volta a última",
        ultima.get("pagina") == d["paginas"],
        str(ultima.get("pagina")),
    )


@cenario("25 custo por cliente novo vindo de anúncio")
def c25():
    cac = desempenho().get("cac") or {}
    if "new_clients_ads" not in cac:
        raise Bloqueado("cac ainda sem new_clients_ads")
    check(
        "25.1 6 clientes novos em março/2031, 5 de anúncio",
        cac["new_clients"] == 6 and cac["new_clients_ads"] == 5,
        str(cac),
    )
    check("25.2 custo = 1400 ÷ 5", cac.get("value") == "280.00", str(cac.get("value")))


@cenario("26 Comercial pede a atribuição (DEVE FALHAR)")
def c26():
    r = atribuicao("com")
    precisa(r, "GET /api/marketing/atribuicao")
    check("26.1 Comercial recebe 403", r.status_code == 403, str(r.status_code))


@cenario("27 valor da venda só para o Superadmin")
def c27():
    sa = venda_da_lista(atribuicao_ok("sa"), "E1")
    mkt_dados = atribuicao_ok("mkt")
    mkt = venda_da_lista(mkt_dados, "E1")
    check("27.1 Superadmin vê o valor", bool(sa) and sa.get("valor") == "3000.00", str(sa))
    check(
        "27.2 Marketing vê a venda sem o valor",
        bool(mkt) and mkt.get("valor") is None and mkt_dados.get("pode_ver_valor") is False,
        str(mkt),
    )


def limpar() -> None:
    with _engine.begin() as conn:
        ids_prop = list(PROPOSTAS.values())
        if ids_prop:
            conn.execute(
                text("delete from marketing_diario where proposta_id = any(:i)"), {"i": ids_prop}
            )
            conn.execute(
                text("delete from notifications where dedupe_key = any(:k)"),
                {"k": [f"marketing.proposta:{i}" for i in ids_prop]},
            )
        conn.execute(
            text("delete from marketing_diario where titulo like :p"), {"p": f"{PREFIXO}%"}
        )
        conn.execute(
            text("delete from marketing_propostas where motivo like :p"), {"p": f"{PREFIXO}%"}
        )
        if POSTS:
            conn.execute(
                text("delete from marketing_post_anuncios where post_id = any(:i)"),
                {"i": list(POSTS.values())},
            )
            conn.execute(
                text("delete from marketing_posts where id = any(:i)"), {"i": list(POSTS.values())}
            )
        conn.execute(
            text("delete from marketing_ad_metrics where ad_id like :p"), {"p": f"a351{RUN}%"}
        )
        conn.execute(
            text("delete from marketing_campaign_metrics where campaign_id like :p"),
            {"p": f"c351%{RUN}"},
        )
        conn.execute(text("delete from marketing_agent_runs where run_id=:r"), {"r": f"v351-{RUN}"})
        conn.execute(
            text("delete from anuncios_meta where anuncio_id like :p"), {"p": f"a351{RUN}%"}
        )
        if CONVERSAS:
            conn.execute(
                text("delete from conversa_anuncios where conversa_id = any(:i)"),
                {"i": list(CONVERSAS.values())},
            )
            conn.execute(
                text("delete from conversas where id = any(:i)"), {"i": list(CONVERSAS.values())}
            )
        if EVENTOS:
            conn.execute(
                text("delete from event_clients where event_id = any(:i)"),
                {"i": list(EVENTOS.values())},
            )
            conn.execute(
                text("delete from calendar_events where id = any(:i)"),
                {"i": list(EVENTOS.values())},
            )
        if CLIENTES:
            conn.execute(
                text("delete from orcamento_history where client_id = any(:i)"),
                {"i": list(CLIENTES.values())},
            )
            conn.execute(
                text("delete from clients where id = any(:i)"), {"i": list(CLIENTES.values())}
            )
        for slug, teto, meta, verba in FRENTES_ANTES:
            conn.execute(
                text(
                    "update marketing_frentes set teto_custo_venda=:t, meta_vendas_mes=:m, verba_mes=:v,"
                    " updated_by_id = case when updated_by_id = any(:u) then null else updated_by_id end where slug=:s"
                ),
                {"t": teto, "m": meta, "v": verba, "s": slug, "u": list(USER_IDS.values())},
            )
        for fr, mes, meta, verba, foco in CALENDARIO_ANTES:
            conn.execute(
                text(
                    "update marketing_calendario set meta_vendas=:m, verba=:v, foco=:f,"
                    " updated_by_id = case when updated_by_id = any(:u) then null else updated_by_id end"
                    " where frente=:fr and mes=:mes"
                ),
                {
                    "m": meta,
                    "v": verba,
                    "f": foco,
                    "fr": fr,
                    "mes": mes,
                    "u": list(USER_IDS.values()),
                },
            )
        conn.execute(
            text("delete from notifications where user_id = any(:u)"),
            {"u": list(USER_IDS.values())},
        )
    with app.app_context():
        db.session.rollback()
        for uid in USER_IDS.values():
            u = User.query.get(uid)
            if u is not None:
                u.roles.clear()
                db.session.flush()
                db.session.delete(u)
        db.session.commit()


try:
    semear()
    for fn in (
        c1,
        c2,
        c3,
        c4,
        c5,
        c6,
        c7,
        c8,
        c9,
        c10,
        c11,
        c12,
        c13,
        c14,
        c15,
        c16,
        c17,
        c18,
        c19,
        c20,
        c21,
        c22,
        c23,
        c24,
        c25,
        c26,
        c27,
    ):
        fn()
finally:
    try:
        limpar()
        sobra = _db("select count(*) from clients where name like :p", p=f"{PREFIXO}%")[0][0]
        sobra += _db("select count(*) from users where email like :p", p=f"verify351-%-{RUN}@%")[0][
            0
        ]
        sobra += _db("select count(*) from marketing_posts where title like :p", p=f"{PREFIXO}%")[
            0
        ][0]
        check("28.1 limpeza sem resto", sobra == 0, str(sobra))
    except Exception as exc:  # noqa: BLE001 — a falha da limpeza é resultado do verify
        check("28.1 limpeza sem resto", False, f"{type(exc).__name__}: {exc}"[:200])
    check("28.2 nenhuma conexão externa escapou", not _ESCAPES, str(_ESCAPES[:5]))

ok = sum(1 for r in resultados if r[1] == "OK")
falha = sum(1 for r in resultados if r[1] == "FALHA")
bloq = sum(1 for r in resultados if r[1] == "BLOQUEADO")
print(f"\n{ok} OK · {falha} FALHA · {bloq} BLOQUEADO (de {len(resultados)})")
sys.exit(1 if falha or bloq else 0)
