"""Verificação da feature 345 — o sistema comanda o marketing.

Roda contra o `manto_345` (dump de produção de 16/11/2026 02:00 + migrations e344/f345). Escrito ANTES
do núcleo (Princípio VIII): sem as rotas, os cenários FALHAM ou ficam BLOQUEADOS.

   1  /anuncios idempotente + /run aceita conversas    10  cards prontos sem anúncio → vínculo
   2  frente pelo prefixo; "sem frente" listada         11  resultado do card soma os anúncios
   3  correção manual da frente vence o nome            12  Marketing tenta aprovar (deve falhar)
   4  custo por venda de festas (satélite/cortesia fora) 13  Superadmin aprova; 2ª decisão 409
   5  sem venda; Google "sem conexão"                   14  execução; proposta de 8 dias expira
   6  anúncio com tema não liberado (deve falhar)       15  diário: nasce da execução e reavalia
   7  post orgânico com licenciado; licenciado liberado 16  papel sem acesso (deve falhar)
   8  sugestões em lote; Marketing libera licenciado    17  limpeza; nenhuma conexão externa
   9  pedido de vídeo vai para a responsável por vídeo

Todos os dados de teste ficam em março de 2031 (gasto, vendas) e em temas/cards com o prefixo
"Verify345": nada encosta no histórico real do espelho. Token do agente gerado aqui, nunca o de produção.

Uso:
    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONPATH = (Get-Location).Path; $env:PYTHONUTF8 = '1'
    <python> specs\\345-marketing-integrado\\verify_345.py
"""

from __future__ import annotations

import os
import secrets
import socket
import sys

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
        raise OSError(f"[verify_345] conexão externa bloqueada: {host}")
    return _create_connection_original(address, *args, **kwargs)


socket.create_connection = _so_local

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.models import Role, SiteSetting, User  # noqa: E402

RUN = secrets.token_hex(3)
PASSWORD = f"verify-345-{secrets.token_hex(6)}"
TOKEN = f"tok345-{RUN}-{secrets.token_hex(8)}"
app = create_app()
app.config["MARKETING_AGENT_TOKEN"] = TOKEN
_engine = create_engine(os.environ["DATABASE_URL"].strip())

# Janela de teste: março de 2031 — nenhum dado real do espelho cai aqui.
JAN_INI, JAN_FIM = "2031-03-01", "2031-03-31"
D1, D2 = "2031-03-02", "2031-03-03"
PREFIXO = f"Verify345 {RUN}"


def _db(sql: str, **p):
    # Conexão separada: o autoflush da sessão do app esconderia um commit que não aconteceu.
    with _engine.connect() as conn:
        return conn.execute(text(sql), p).fetchall()


def _exec(sql: str, **p) -> None:
    with _engine.begin() as conn:
        conn.execute(text(sql), p)


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
USER_IDS: dict[str, int] = {}
CRIADOS_USERS: list[int] = []
TEMAS: dict[str, int] = {}
EVENTOS: list[int] = []
CLIENTES: list[int] = []
SETTINGS_ORIGINAIS: dict = {}
FRENTES_ORIGINAIS: dict[str, object] = {}

with app.app_context():
    s = SiteSetting.query.get(1)
    for campo in ("marketing_resp_foto_id", "marketing_resp_video_id"):
        SETTINGS_ORIGINAIS[campo] = getattr(s, campo, None)
    gestor = (
        User.query.filter(User.has_access.is_(True))
        .filter(User.roles.any(name=RoleName.SUPERADMIN))
        .filter(User.email.isnot(None))
        .order_by(User.id)
        .first()
    )
    gestor.set_password(PASSWORD)
    USUARIOS["gestor"], USER_IDS["gestor"] = gestor.email, gestor.id
    # Usuários descartáveis: o espelho não tem ninguém só com MARKETING, e o CASTING precisa ser
    # alguém sem nenhum papel de marketing.
    for papel, role_name in (("mkt", RoleName.MARKETING), ("cast", RoleName.CASTING)):
        u = User(
            name=f"{PREFIXO} {papel}",
            email=f"verify345-{papel}-{RUN}@example.invalid",
            has_access=True,
            is_active=True,
            receives_commission=False,
        )
        u.set_password(PASSWORD)
        u.roles.append(Role.query.filter_by(name=role_name).one())
        db.session.add(u)
        db.session.flush()
        CRIADOS_USERS.append(u.id)
        USUARIOS[papel], USER_IDS[papel] = u.email, u.id
    db.session.commit()

limiter.enabled = False


def login(papel: str) -> None:
    client.post("/api/auth/logout")
    r = client.post("/api/auth/login", json={"email": USUARIOS[papel], "password": PASSWORD})
    if r.status_code != 200:
        raise Bloqueado(f"login {papel}: {r.status_code}")


def agente(metodo: str, caminho: str, **kw):
    r = getattr(client, metodo)(f"/api/marketing-agent/{TOKEN}{caminho}", **kw)
    if r.status_code == 404 and caminho.split("?")[0].strip("/") not in ("run", "context"):
        if (r.get_json(silent=True) or {}).get("error", {}).get("message") != "Não encontrado":
            raise Bloqueado(f"rota do agente {caminho} ainda não existe")
    return r


def precisa(r, rota: str) -> None:
    if r.status_code == 404 and not (r.get_json(silent=True) or {}).get("error"):
        raise Bloqueado(f"{rota} ainda não existe")
    if r.status_code == 405:
        raise Bloqueado(f"{rota} ainda não existe (405)")


def novo_tema(nome: str) -> int:
    slug = f"verify345-{RUN}-{nome}".lower()
    _exec(
        "insert into catalog_items (name, slug, is_active, imported_at) values (:n, :s, true, now())",
        n=f"{PREFIXO} {nome}",
        s=slug,
    )
    tid = _db("select id from catalog_items where slug=:s", s=slug)[0][0]
    TEMAS[nome] = tid
    return tid


def novo_cliente(nome: str) -> int:
    fone = f"5599{secrets.randbelow(10**9):09d}"
    _exec(
        "insert into clients (name, phone, source, created_at, updated_at) "
        "values (:n, :p, 'manual', now(), now())",
        n=f"{PREFIXO} {nome}",
        p=fone,
    )
    cid = _db("select id from clients where phone=:p", p=fone)[0][0]
    CLIENTES.append(cid)
    return cid


def novo_evento(
    titulo: str,
    *,
    tipo: str,
    venda: str,
    data_venda: str,
    inicio: str,
    cliente: int | None = None,
    lider: int | None = None,
    cortesia: bool = False,
) -> int:
    gid = f"v345{RUN}{len(EVENTOS)}"
    _exec(
        "insert into calendar_events (google_event_id, title, start_at, end_at, created_at, updated_at,"
        " sale_value, sale_date, event_type, client_id, group_leader_id, is_cortesia_permuta, source)"
        " values (:g, :t, :i, :i, now(), now(), :v, :d, :tp, :c, :l, :cort, 'platform')",
        g=gid,
        t=f"{PREFIXO} {titulo}",
        i=inicio,
        v=venda,
        d=data_venda,
        tp=tipo,
        c=cliente,
        l=lider,
        cort=cortesia,
    )
    eid = _db("select id from calendar_events where google_event_id=:g", g=gid)[0][0]
    EVENTOS.append(eid)
    return eid


def frente(payload: dict, slug: str) -> dict:
    for f in payload.get("frentes") or []:
        if f.get("slug") == slug:
            return f
    raise Bloqueado(f"frente {slug} ausente do desempenho")


def desempenho() -> dict:
    login("gestor")
    r = client.get(f"/api/marketing/desempenho?start={JAN_INI}&end={JAN_FIM}")
    if r.status_code != 200:
        raise AssertionError(f"desempenho {r.status_code}")
    d = r.get_json()
    if "frentes" not in d:
        raise Bloqueado("desempenho ainda sem o bloco 'frentes'")
    return d


CAMP_FESTA = f"FESTA · MSG · {RUN}"
CAMP_CORP = f"corp · busca · {RUN}"
CAMP_TESTE = f"Teste {RUN}"
ID_FESTA, ID_CORP, ID_TESTE = f"c345f{RUN}", f"c345c{RUN}", f"c345t{RUN}"


# ── Cenários ────────────────────────────────────────────────────────────────────────────────
@cenario("1 ingestão por anúncio idempotente; /run aceita conversas")
def c1():
    itens = []
    for n in range(3):
        for dia in (D1, D2):
            itens.append(
                {
                    "platform": "Meta Ads",
                    "ad_id": f"a345{RUN}{n}",
                    "ad_name": f"Peça {n}",
                    "adset_id": "s1",
                    "campaign_id": ID_FESTA,
                    "campaign_name": CAMP_FESTA,
                    "metric_date": dia,
                    "spend": "10.00",
                    "impressions": 100,
                    "clicks": 5,
                    "conversations": 2,
                }
            )
    r1 = agente("post", "/anuncios", json={"items": itens})
    precisa(r1, "POST /anuncios")
    itens[0]["spend"] = "12.50"
    r2 = agente("post", "/anuncios", json={"items": itens})
    linhas = _db(
        "select count(*), sum(spend) from marketing_ad_metrics where ad_id like :p", p=f"a345{RUN}%"
    )
    check(
        "1.1 primeira ingestão 200",
        r1.status_code == 200,
        f"{r1.status_code} {r1.get_data(as_text=True)[:200]}",
    )
    check("1.2 repetir não duplica (6 linhas)", linhas[0][0] == 6, str(linhas))
    check("1.3 repetir atualiza o valor (62,50)", str(linhas[0][1]) == "62.50", str(linhas))
    check("1.4 segunda ingestão 200", r2.status_code == 200, str(r2.status_code))

    login("gestor")
    run = {
        "run_id": f"v345-{RUN}",
        "mode": "local",
        "card_holder_email": USUARIOS["gestor"],
        "window": [f"{JAN_INI}T00:00:00", f"{JAN_FIM}T23:59:59"],
        "campaign_metrics": [
            {
                "platform": "Meta Ads",
                "campaign_id": ID_FESTA,
                "campaign_name": CAMP_FESTA,
                "period_start": D1,
                "period_end": D1,
                "spend": "900.00",
                "conversations": 41,
                "leads": 0,
            },
            {
                "platform": "Meta Ads",
                "campaign_id": ID_CORP,
                "campaign_name": CAMP_CORP,
                "period_start": D1,
                "period_end": D1,
                "spend": "300.00",
                "conversations": 3,
            },
            {
                "platform": "Meta Ads",
                "campaign_id": ID_TESTE,
                "campaign_name": CAMP_TESTE,
                "period_start": D1,
                "period_end": D1,
                "spend": "50.00",
                "conversations": 0,
            },
        ],
    }
    r3 = agente("post", "/run", json=run)
    conv = _db(
        "select conversations from marketing_campaign_metrics where campaign_id=:c", c=ID_FESTA
    )
    check(
        "1.5 /run 200", r3.status_code == 200, f"{r3.status_code} {r3.get_data(as_text=True)[:200]}"
    )
    check("1.6 /run grava conversas da campanha", bool(conv) and conv[0][0] == 41, str(conv))


@cenario("2 frente pelo prefixo; campanha sem prefixo vira 'sem frente'")
def c2():
    d = desempenho()
    check(
        "2.1 FESTA → festas (R$ 900)",
        frente(d, "festas").get("gasto") == "900.00",
        str(frente(d, "festas")),
    )
    check(
        "2.2 corp (minúsculo) → corporativo",
        frente(d, "corporativo").get("gasto") == "300.00",
        str(frente(d, "corporativo")),
    )
    ids = [c.get("campaign_id") for c in d.get("sem_frente") or []]
    check("2.3 'Teste' em sem frente", ID_TESTE in ids, str(d.get("sem_frente")))


@cenario("3 correção manual da frente vence o nome")
def c3():
    login("gestor")
    r = client.patch(
        "/api/marketing/campanhas/frente",
        json={"platform": "Meta Ads", "campaign_id": ID_TESTE, "frente": "educamanto"},
    )
    precisa(r, "PATCH /api/marketing/campanhas/frente")
    d = desempenho()
    ids = [c.get("campaign_id") for c in d.get("sem_frente") or []]
    check(
        "3.1 PATCH 200", r.status_code == 200, f"{r.status_code} {r.get_data(as_text=True)[:200]}"
    )
    check(
        "3.2 educamanto ganha os R$ 50",
        frente(d, "educamanto").get("gasto") == "50.00",
        str(frente(d, "educamanto")),
    )
    check("3.3 sai de sem frente", ID_TESTE not in ids, str(ids))


@cenario("4 custo por venda de festas; satélite e cortesia fora; cliente novo")
def c4():
    antigo = novo_cliente("antigo")
    novo1, novo2 = novo_cliente("novo1"), novo_cliente("novo2")
    novo_evento(
        "festa antiga",
        tipo="SHOW",
        venda="3000",
        data_venda="2030-05-01",
        inicio="2030-05-10 15:00",
        cliente=antigo,
    )
    lider = novo_evento(
        "festa A",
        tipo="SHOW",
        venda="3600",
        data_venda="2031-03-05",
        inicio="2031-03-20 15:00",
        cliente=antigo,
    )
    novo_evento(
        "festa B",
        tipo="R&I",
        venda="3600",
        data_venda="2031-03-06",
        inicio="2031-03-21 15:00",
        cliente=novo1,
    )
    novo_evento(
        "festa C",
        tipo="SHOW",
        venda="3600",
        data_venda="2031-03-07",
        inicio="2031-03-22 15:00",
        cliente=novo2,
    )
    novo_evento(
        "festa A dia 2",
        tipo="SHOW",
        venda="3600",
        data_venda="2031-03-05",
        inicio="2031-03-21 15:00",
        cliente=antigo,
        lider=lider,
    )
    novo_evento(
        "festa cortesia",
        tipo="SHOW",
        venda="3600",
        data_venda="2031-03-08",
        inicio="2031-03-23 15:00",
        cortesia=True,
    )
    login("gestor")
    r = client.patch("/api/marketing/frentes", json={"tetos": {"festas": "575.00"}})
    precisa(r, "PATCH /api/marketing/frentes")
    check(
        "4.1 teto de festas salvo",
        r.status_code == 200,
        f"{r.status_code} {r.get_data(as_text=True)[:200]}",
    )
    f = frente(desempenho(), "festas")
    check("4.2 3 vendas (satélite e cortesia fora)", f.get("vendas") == 3, str(f))
    check("4.3 custo por venda R$ 300,00", f.get("custo_venda") == "300.00", str(f))
    check("4.4 dentro do teto", f.get("estado") == "ok" and f.get("teto") == "575.00", str(f))
    check("4.5 2 de cliente novo", f.get("vendas_cliente_novo") == 2, str(f))
    check("4.6 41 conversas", f.get("conversas") == 41, str(f))


@cenario("5 frente com gasto e sem venda; Google sem conexão")
def c5():
    d = desempenho()
    corp = frente(d, "corporativo")
    check(
        "5.1 corporativo 'sem_venda'",
        corp.get("estado") == "sem_venda" and corp.get("custo_venda") is None,
        str(corp),
    )
    google = next(
        (p for p in d.get("plataformas") or [] if p.get("platform") == "Google Ads"), None
    )
    check(
        "5.2 Google 'sem_conexao'",
        bool(google) and google.get("situacao") == "sem_conexao",
        str(d.get("plataformas")),
    )


def _post(json: dict):
    r = client.post("/api/marketing/posts", json=json)
    precisa(r, "POST /api/marketing/posts")
    return r


@cenario("6 card de anúncio com tema não liberado é recusado (deve falhar)")
def c6():
    lic, nc = novo_tema("licenciado"), novo_tema("naoclassificado")
    _exec(
        "update catalog_items set licenca_origem='licenciado', liberado_anuncio='nao' where id=:i",
        i=lic,
    )
    login("mkt")
    r1 = _post({"title": f"{PREFIXO} anúncio lic", "tipo": "anuncio", "catalog_item_ids": [lic]})
    r2 = _post({"title": f"{PREFIXO} anúncio nc", "tipo": "anuncio", "catalog_item_ids": [nc]})
    cod1 = ((r1.get_json(silent=True) or {}).get("error") or {}).get("codigo")
    check(
        "6.1 licenciado não liberado → 422 tema_nao_liberado",
        r1.status_code == 422 and cod1 == "tema_nao_liberado",
        f"{r1.status_code} {r1.get_data(as_text=True)[:200]}",
    )
    check("6.2 não classificado → 422", r2.status_code == 422, f"{r2.status_code}")
    n = _db("select count(*) from marketing_posts where title like :p", p=f"{PREFIXO} anúncio%")
    check("6.3 nada gravado", n[0][0] == 0, str(n))


@cenario("7 post orgânico com licenciado passa; licenciado liberado pelo Superadmin passa")
def c7():
    lic = TEMAS.get("licenciado") or novo_tema("licenciado")
    login("mkt")
    r1 = _post({"title": f"{PREFIXO} post org", "tipo": "post", "catalog_item_ids": [lic]})
    check(
        "7.1 post orgânico 201",
        r1.status_code == 201,
        f"{r1.status_code} {r1.get_data(as_text=True)[:200]}",
    )
    login("gestor")
    r2 = client.patch(f"/api/marketing/temas-licenca/{lic}", json={"liberado_anuncio": "sim"})
    precisa(r2, "PATCH /api/marketing/temas-licenca/<id>")
    check(
        "7.2 Superadmin libera licenciado",
        r2.status_code == 200,
        f"{r2.status_code} {r2.get_data(as_text=True)[:200]}",
    )
    login("mkt")
    r3 = _post(
        {"title": f"{PREFIXO} anúncio liberado", "tipo": "anuncio", "catalog_item_ids": [lic]}
    )
    check("7.3 anúncio com licenciado liberado 201", r3.status_code == 201, f"{r3.status_code}")


@cenario("8 sugestões em lote; Marketing não libera licenciado (deve falhar)")
def c8():
    a1, a2, l1 = novo_tema("aut1"), novo_tema("aut2"), novo_tema("lic2")
    r = agente(
        "post",
        "/licencas/sugestoes",
        json={
            "items": [
                {"catalog_item_id": a1, "origem": "autoral", "motivo": "personagem próprio"},
                {"catalog_item_id": a2, "origem": "autoral", "motivo": "show próprio"},
                {"catalog_item_id": l1, "origem": "licenciado", "motivo": "personagem da Disney"},
            ]
        },
    )
    check(
        "8.1 sugestões gravadas",
        r.status_code == 200,
        f"{r.status_code} {r.get_data(as_text=True)[:200]}",
    )
    ainda = _db("select licenca_origem from catalog_items where id=:i", i=a1)
    check("8.2 sugestão não confirma sozinha", ainda[0][0] == "nao_classificado", str(ainda))
    login("mkt")
    r2 = client.post("/api/marketing/temas-licenca/confirmar", json={"ids": [a1, a2, l1]})
    precisa(r2, "POST /api/marketing/temas-licenca/confirmar")
    linhas = {
        row[0]: (row[1], row[2], row[3])
        for row in _db(
            "select id, licenca_origem, liberado_anuncio, licenca_por_id from catalog_items where id = any(:i)",
            i=[a1, a2, l1],
        )
    }
    check("8.3 confirmação 200", r2.status_code == 200, f"{r2.status_code}")
    check(
        "8.4 autoral sai liberado",
        linhas[a1][:2] == ("autoral", "sim") and linhas[a2][:2] == ("autoral", "sim"),
        str(linhas),
    )
    check("8.5 licenciado sai não liberado", linhas[l1][:2] == ("licenciado", "nao"), str(linhas))
    check("8.6 autor gravado", linhas[a1][2] == USER_IDS["mkt"], str(linhas))
    r3 = client.patch(f"/api/marketing/temas-licenca/{l1}", json={"liberado_anuncio": "sim"})
    check("8.7 Marketing libera licenciado → 403", r3.status_code == 403, f"{r3.status_code}")


POST_PEDIDO: list[int] = []


@cenario("9 pedido de vídeo da rotina vai para a responsável por vídeo")
def c9():
    login("gestor")
    r = client.patch(
        "/api/marketing/frentes",
        json={"resp_video_id": USER_IDS["mkt"], "resp_foto_id": USER_IDS["gestor"]},
    )
    precisa(r, "PATCH /api/marketing/frentes")
    aut = TEMAS.get("aut1")
    r2 = agente(
        "post",
        "/pedidos",
        json={
            "items": [
                {
                    "titulo": f"{PREFIXO} reels festa",
                    "tipo": "anuncio",
                    "frente": "festas",
                    "formato": "video_9x16",
                    "briefing_objetivo": "conversas de festa em Alphaville",
                    "briefing_mostrar": "chegada do personagem",
                    "briefing_letreiro": "Ele vai chamar pelo nome",
                    "catalog_item_ids": [aut],
                    "deadline_date": "2031-03-10",
                }
            ]
        },
    )
    corpo = r2.get_json(silent=True) or {}
    criados = corpo.get("criados") or []
    check(
        "9.1 pedido criado",
        r2.status_code == 200 and len(criados) == 1,
        f"{r2.status_code} {str(corpo)[:200]}",
    )
    if not criados:
        return
    POST_PEDIDO.append(criados[0])
    row = _db(
        "select status, assignee_id, origem, tipo, frente, formato, briefing_letreiro from marketing_posts"
        " where id=:i",
        i=criados[0],
    )[0]
    check("9.2 coluna Ideia", row[0] == "ideia", str(row))
    check("9.3 responsável por vídeo", row[1] == USER_IDS["mkt"], str(row))
    check(
        "9.4 origem rotina + briefing",
        row[2] == "rotina"
        and row[3] == "anuncio"
        and row[5] == "video_9x16"
        and row[6] == "Ele vai chamar pelo nome",
        str(row),
    )


@cenario("10 card pronto sem anúncio → vínculo")
def c10():
    if not POST_PEDIDO:
        raise Bloqueado("sem card do cenário 9")
    pid = POST_PEDIDO[0]
    login("mkt")
    client.patch(f"/api/marketing/posts/{pid}", json={"status": "pronto"})
    r = agente("get", "/comando", query_string={"start": JAN_INI, "end": JAN_FIM})
    precisa(r, "GET /comando")
    ids = [c.get("id") for c in (r.get_json() or {}).get("cards_prontos_sem_anuncio") or []]
    check("10.1 card listado como pronto sem anúncio", pid in ids, str(ids)[:200])
    r2 = agente(
        "post", f"/posts/{pid}/anuncios", json={"platform": "Meta Ads", "ad_id": f"a345{RUN}0"}
    )
    check(
        "10.2 vínculo 200",
        r2.status_code == 200,
        f"{r2.status_code} {r2.get_data(as_text=True)[:200]}",
    )
    r3 = agente("get", "/comando", query_string={"start": JAN_INI, "end": JAN_FIM})
    ids = [c.get("id") for c in (r3.get_json() or {}).get("cards_prontos_sem_anuncio") or []]
    check("10.3 some da lista", pid not in ids, str(ids)[:200])
    r4 = agente(
        "post", f"/posts/{pid}/anuncios", json={"platform": "Meta Ads", "ad_id": f"a345{RUN}0"}
    )
    check(
        "10.4 mesmo anúncio de novo → idempotente (200)", r4.status_code == 200, str(r4.status_code)
    )


@cenario("11 resultado do card soma os anúncios vinculados")
def c11():
    if not POST_PEDIDO:
        raise Bloqueado("sem card do cenário 9")
    login("mkt")
    r = client.get(f"/api/marketing/posts/{POST_PEDIDO[0]}")
    d = r.get_json() or {}
    res = d.get("resultado") or {}
    check("11.1 anúncios no card", len(d.get("anuncios") or []) == 1, str(d.get("anuncios")))
    check(
        "11.2 gasto R$ 22,50 e 4 conversas",
        res.get("spend") == "22.50" and res.get("conversations") == 4,
        str(res),
    )
    check("11.3 custo por conversa R$ 5,63", res.get("custo_conversa") == "5.63", str(res))


PROPOSTAS: list[int] = []


@cenario("12 Marketing tenta aprovar (deve falhar)")
def c12():
    r = agente(
        "post",
        "/propostas",
        json={
            "tipo": "verba",
            "platform": "Meta Ads",
            "alvo_tipo": "campanha",
            "alvo_id": ID_FESTA,
            "alvo_nome": CAMP_FESTA,
            "valor_antes": "R$ 30/dia",
            "valor_depois": "R$ 45/dia",
            "custo_dia_estimado": "45.00",
            "motivo": f"{PREFIXO} custo por conversa R$ 7, metade do teto",
        },
    )
    check(
        "12.1 proposta criada (201)",
        r.status_code == 201,
        f"{r.status_code} {r.get_data(as_text=True)[:200]}",
    )
    pid = (r.get_json(silent=True) or {}).get("id")
    if not pid:
        return
    PROPOSTAS.append(pid)
    login("mkt")
    r2 = client.post(f"/api/marketing/propostas/{pid}/decidir", json={"decisao": "aprovar"})
    sit = _db("select situacao from marketing_propostas where id=:i", i=pid)
    check("12.2 Marketing → 403", r2.status_code == 403, str(r2.status_code))
    check("12.3 segue pendente", sit[0][0] == "pendente", str(sit))


@cenario("13 Superadmin aprova; segunda decisão 409")
def c13():
    if not PROPOSTAS:
        raise Bloqueado("sem proposta do cenário 12")
    login("gestor")
    r = client.post(
        f"/api/marketing/propostas/{PROPOSTAS[0]}/decidir",
        json={"decisao": "aprovar", "obs": "pode"},
    )
    r2 = client.post(
        f"/api/marketing/propostas/{PROPOSTAS[0]}/decidir", json={"decisao": "recusar"}
    )
    row = _db(
        "select situacao, decidida_por_id from marketing_propostas where id=:i", i=PROPOSTAS[0]
    )[0]
    cod = ((r2.get_json(silent=True) or {}).get("error") or {}).get("codigo")
    check(
        "13.1 aprovar 200",
        r.status_code == 200,
        f"{r.status_code} {r.get_data(as_text=True)[:200]}",
    )
    check(
        "13.2 aprovada por quem decidiu",
        row[0] == "aprovada" and row[1] == USER_IDS["gestor"],
        str(row),
    )
    check(
        "13.3 segunda decisão 409 ja_decidida",
        r2.status_code == 409 and cod == "ja_decidida",
        f"{r2.status_code} {cod}",
    )


@cenario("14 execução sai da lista; proposta de 8 dias expira")
def c14():
    if not PROPOSTAS:
        raise Bloqueado("sem proposta do cenário 12")
    pid = PROPOSTAS[0]
    r = agente("get", "/comando", query_string={"start": JAN_INI, "end": JAN_FIM})
    ids = [p.get("id") for p in (r.get_json() or {}).get("propostas_a_executar") or []]
    check("14.1 aprovada aparece 'a executar'", pid in ids, str(ids))
    r2 = agente(
        "post",
        f"/propostas/{pid}/execucao",
        json={"resultado": "executada", "detalhe": "verba 45/dia"},
    )
    check(
        "14.2 marcar execução 200",
        r2.status_code == 200,
        f"{r2.status_code} {r2.get_data(as_text=True)[:200]}",
    )
    r3 = agente("get", "/comando", query_string={"start": JAN_INI, "end": JAN_FIM})
    ids = [p.get("id") for p in (r3.get_json() or {}).get("propostas_a_executar") or []]
    check("14.3 executada some da lista", pid not in ids, str(ids))
    r4 = agente(
        "post",
        "/propostas",
        json={
            "tipo": "pausar",
            "platform": "Meta Ads",
            "alvo_tipo": "campanha",
            "alvo_id": ID_CORP,
            "alvo_nome": CAMP_CORP,
            "motivo": f"{PREFIXO} sem venda",
        },
    )
    velha = (r4.get_json(silent=True) or {}).get("id")
    if not velha:
        check("14.4 proposta velha criada", False, str(r4.status_code))
        return
    PROPOSTAS.append(velha)
    _exec(
        "update marketing_propostas set criada_em = now() - interval '8 days' where id=:i", i=velha
    )
    login("gestor")
    r5 = client.post(f"/api/marketing/propostas/{velha}/decidir", json={"decisao": "aprovar"})
    sit = _db("select situacao from marketing_propostas where id=:i", i=velha)
    cod = ((r5.get_json(silent=True) or {}).get("error") or {}).get("codigo")
    check(
        "14.4 de 8 dias não aprova (409 expirada)",
        r5.status_code == 409 and cod == "expirada",
        f"{r5.status_code} {cod}",
    )
    check("14.5 situação expirada", sit[0][0] == "expirada", str(sit))


@cenario("15 diário: nasce da execução e reavalia")
def c15():
    if not PROPOSTAS:
        raise Bloqueado("sem proposta do cenário 12")
    ent = _db(
        "select id, reavaliar_em, origem from marketing_diario where proposta_id=:p", p=PROPOSTAS[0]
    )
    check(
        "15.1 execução gerou entrada do diário", len(ent) == 1 and ent[0][2] == "proposta", str(ent)
    )
    if not ent:
        return
    did = ent[0][0]
    _exec("update marketing_diario set reavaliar_em = current_date - 1 where id=:i", i=did)
    r = agente("get", "/comando", query_string={"start": JAN_INI, "end": JAN_FIM})
    ids = [e.get("id") for e in (r.get_json() or {}).get("diario_a_reavaliar") or []]
    check("15.2 vencida aparece 'a reavaliar'", did in ids, str(ids))
    r2 = agente(
        "post",
        f"/diario/{did}/resultado",
        json={"resultado_observado": "conversas subiram 30%", "veredito": "funcionou"},
    )
    check(
        "15.3 resultado gravado 200",
        r2.status_code == 200,
        f"{r2.status_code} {r2.get_data(as_text=True)[:200]}",
    )
    r3 = agente("get", "/comando", query_string={"start": JAN_INI, "end": JAN_FIM})
    ids = [e.get("id") for e in (r3.get_json() or {}).get("diario_a_reavaliar") or []]
    row = _db("select veredito, avaliado_em is not null from marketing_diario where id=:i", i=did)[
        0
    ]
    check(
        "15.4 sai da lista e fica avaliada",
        did not in ids and row == ("funcionou", True),
        f"{ids} {row}",
    )
    login("mkt")
    r4 = client.post(
        "/api/marketing/diario",
        json={"titulo": f"{PREFIXO} trocamos o criativo", "motivo": "teste A/B"},
    )
    check("15.5 Marketing escreve entrada à mão (201)", r4.status_code == 201, f"{r4.status_code}")


@cenario("16 papel sem acesso (deve falhar)")
def c16():
    login("cast")
    codigos = {
        rota: client.get(rota).status_code
        for rota in (
            "/api/marketing/propostas",
            "/api/marketing/frentes",
            "/api/marketing/diario",
            "/api/marketing/temas-licenca",
        )
    }
    check("16.1 CASTING recebe 403 em tudo", all(c == 403 for c in codigos.values()), str(codigos))
    r = client.get(f"/api/marketing-agent/token-errado-{RUN}/comando")
    check("16.2 agente com token errado → 404", r.status_code == 404, str(r.status_code))


# ── Limpeza ─────────────────────────────────────────────────────────────────────────────────
def limpar() -> None:
    with _engine.begin() as conn:

        def tem(tabela: str) -> bool:
            return bool(conn.execute(text("select to_regclass(:t)"), {"t": tabela}).scalar())

        if tem("marketing_diario"):
            conn.execute(
                text(
                    "delete from marketing_diario where titulo like :p or proposta_id = any(:ids)"
                ),
                {"p": f"{PREFIXO}%", "ids": PROPOSTAS or [0]},
            )
        if tem("marketing_propostas"):
            conn.execute(
                text("delete from marketing_propostas where motivo like :p"), {"p": f"{PREFIXO}%"}
            )
        posts = [
            r[0]
            for r in conn.execute(
                text("select id from marketing_posts where title like :p"), {"p": f"{PREFIXO}%"}
            )
        ]
        if posts:
            if tem("marketing_post_anuncios"):
                conn.execute(
                    text("delete from marketing_post_anuncios where post_id = any(:i)"),
                    {"i": posts},
                )
            conn.execute(
                text("delete from marketing_post_temas where post_id = any(:i)"), {"i": posts}
            )
            conn.execute(text("delete from marketing_posts where id = any(:i)"), {"i": posts})
        if tem("marketing_ad_metrics"):
            conn.execute(
                text("delete from marketing_ad_metrics where ad_id like :p"), {"p": f"a345{RUN}%"}
            )
        if tem("marketing_campanha_frentes"):
            conn.execute(
                text("delete from marketing_campanha_frentes where campaign_id like :p"),
                {"p": f"c345%{RUN}"},
            )
        # /run (mode local) criou o lote de reembolso de março/2031 e o Gasto Extra dele.
        lotes = conn.execute(
            text(
                "select id, special_expense_id from marketing_ad_spend_batches"
                " where month_ref = '2031-03'"
            )
        ).fetchall()
        for lote_id, gasto_id in lotes:
            conn.execute(
                text("delete from marketing_ad_spend_lines where batch_id=:b"), {"b": lote_id}
            )
            conn.execute(text("delete from marketing_ad_spend_batches where id=:b"), {"b": lote_id})
            conn.execute(text("delete from special_expenses where id=:g"), {"g": gasto_id})
        conn.execute(
            text("delete from marketing_campaign_metrics where campaign_id like :p"),
            {"p": f"c345%{RUN}"},
        )
        conn.execute(
            text(
                "delete from marketing_import_files where run_id in "
                "(select id from marketing_agent_runs where run_id=:r)"
            ),
            {"r": f"v345-{RUN}"},
        )
        conn.execute(text("delete from marketing_agent_runs where run_id=:r"), {"r": f"v345-{RUN}"})
        for ev in sorted(EVENTOS, reverse=True):
            conn.execute(
                text("update calendar_events set group_leader_id = null where group_leader_id=:e"),
                {"e": ev},
            )
        for ev in EVENTOS:
            conn.execute(text("delete from event_clients where event_id=:e"), {"e": ev})
            conn.execute(text("delete from calendar_events where id=:e"), {"e": ev})
        if CLIENTES:
            conn.execute(text("delete from clients where id = any(:i)"), {"i": CLIENTES})
        if TEMAS:
            conn.execute(
                text("delete from catalog_items where id = any(:i)"), {"i": list(TEMAS.values())}
            )
        if tem("marketing_frentes"):
            conn.execute(
                text(
                    "update marketing_frentes set teto_custo_venda = null, updated_by_id = null,"
                    " updated_at = null where updated_by_id = any(:u)"
                ),
                {"u": [USER_IDS["gestor"], *CRIADOS_USERS]},
            )
    with app.app_context():
        s = SiteSetting.query.get(1)
        for campo, valor in SETTINGS_ORIGINAIS.items():
            if hasattr(s, campo):
                setattr(s, campo, valor)
        for uid in CRIADOS_USERS:
            u = User.query.get(uid)
            if u is not None:
                u.roles.clear()
                db.session.flush()
                db.session.delete(u)
        db.session.commit()


try:
    for fn in (c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12, c13, c14, c15, c16):
        fn()
finally:
    try:
        limpar()
        check("17.1 limpeza", True)
    except Exception as exc:  # noqa: BLE001
        check("17.1 limpeza", False, f"{type(exc).__name__}: {exc}"[:200])
    check("17.2 nenhuma conexão externa escapou", not _ESCAPES, str(_ESCAPES[:5]))

ok = sum(1 for r in resultados if r[1] == "OK")
falha = sum(1 for r in resultados if r[1] == "FALHA")
bloq = sum(1 for r in resultados if r[1] == "BLOQUEADO")
print(f"\n{ok} OK · {falha} FALHA · {bloq} BLOQUEADO (de {len(resultados)})")
sys.exit(1 if falha or bloq else 0)
