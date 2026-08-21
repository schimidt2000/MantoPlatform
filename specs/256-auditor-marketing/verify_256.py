"""Verificação da feature 256 — auditor de marketing semanal e mensuração no ERP.

Cenários (quickstart.md §2) — Test-First: cada um nasce FALHANDO e passa quando a fase
correspondente é implementada:

 1. Parsers: fixtures válidas viram normalizado; inválida rejeitada; agregado aceito; ambíguo.
 2. Token: sem env 404; errado 404; certo 200 com card_holder.
 3. Ingestão idempotente: contagens; replay; sha256 duplicado.
 4. Reembolso mensal: created → updated → frozen_divergent; manual; USD.
 5. Sobreposição diário × agregado.
 6. Vínculo de post: permalink → data → nenhum → revínculo.
 7. Importador Kommo com utms (e sem as colunas).
 8. Contexto: metas iguais ao endpoint; atribuição por utm_campaign.
 9. Tela/API de desempenho: RBAC, período inválido, vazio, tempo de resposta.
10. Permalink: PATCH inválido 400 com campo; válido normalizado.
11. Serializer do gasto expõe marketing_batch.
12. Limpeza total dos registros `__v256_`.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    $env:MARKETING_AGENT_TOKEN = (gc .marketing-agent-token -Raw).Trim()
    .venv/Scripts/python.exe specs/256-auditor-marketing/verify_256.py

Nunca chama a API de eventos (ela sincroniza com o Google de verdade); tudo que precisa de
evento é criado direto no banco e apagado no fim.
"""

from __future__ import annotations

import os
import sys
import time
import traceback
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from pathlib import Path

# Console do Windows em cp1252 não imprime setas/acentos: força UTF-8 na saída.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "marketing"))

os.environ.setdefault("FLASK_ENV", "development")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()
if not os.environ.get("MARKETING_AGENT_TOKEN"):
    token_file = REPO_ROOT / ".marketing-agent-token"
    if token_file.exists():
        os.environ["MARKETING_AGENT_TOKEN"] = token_file.read_text(encoding="utf-8").strip()

from app import create_app, db  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.models import (  # noqa: E402
    Client,
    MarketingAdSpendBatch,
    MarketingAgentRun,
    MarketingPost,
    Role,
    SpecialExpense,
    User,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PREFIX = "__v256_"
SENHA = "verify-256-senha"
TOKEN = os.environ.get("MARKETING_AGENT_TOKEN", "")

app = create_app()
app.config["TESTING"] = True
app.config["WTF_CSRF_ENABLED"] = False
app.config["MARKETING_AGENT_TOKEN"] = TOKEN

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}


# ── harness ───────────────────────────────────────────────────────────────────


def cenario(nome: str, fn: Callable[[], None]) -> None:
    """Roda um cenário isolado; qualquer exceção vira FALHA com a última linha do erro."""
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001 — harness de teste: registra e segue
        db.session.rollback()
        linha = traceback.format_exc().strip().splitlines()[-1]
        resultados.append((nome, False, linha))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _role(nome: str) -> Role:
    role = Role.query.filter_by(name=nome).first()
    _garante(role is not None, f"papel {nome} não existe no banco")
    return role


def _cria_usuario(sufixo: str, papel: str) -> User:
    email = f"{PREFIX}{sufixo}@manto.local"
    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(name=f"{PREFIX}{sufixo}", email=email, is_active=True, has_access=True)
        db.session.add(user)
    user.set_password(SENHA)
    user.roles.clear()
    user.roles.append(_role(papel))
    db.session.commit()
    return user


def _login(client, email: str):
    resp = client.post("/api/auth/login", json={"email": email, "password": SENHA})
    _garante(resp.status_code == 200, f"login {email} → {resp.status_code}")
    return client


def _apaga_usuario(email: str) -> None:
    user = User.query.filter_by(email=email).first()
    if user:
        user.roles.clear()
        db.session.delete(user)


def _agent_url(path: str, token: str | None = None) -> str:
    return f"/api/marketing-agent/{token if token is not None else TOKEN}{path}"


# ── cenários ──────────────────────────────────────────────────────────────────


def cen_01_parsers() -> None:
    import parsers  # scripts/marketing/parsers.py

    maps = parsers.load_column_maps()
    validos = {
        "meta_conteudo.csv": "meta_content",
        "meta_conta.csv": "meta_account",
        "meta_ads_dia.csv": "meta_ads",
        "google_ads_dia.csv": "google_ads",
    }
    normalizados = {}
    for nome, kind in validos.items():
        veredito, dados = parsers.parse_file(FIXTURES / nome, maps, run_date=date(2026, 8, 18))
        _garante(veredito.status == "accepted", f"{nome}: {veredito.status} {veredito.reason}")
        _garante(veredito.kind == kind, f"{nome}: kind {veredito.kind} ≠ {kind}")
        normalizados[kind] = dados
    posts = normalizados["meta_content"]["post_metrics"]
    _garante(len(posts) == 3, f"posts: {len(posts)}")
    _garante(posts[0]["snapshot_date"] == "2026-08-17", "snapshot_date da coluna Data")
    _garante(posts[0]["permalink"].endswith("/reel/C9abcDEf1/"), f"permalink limpo: {posts[0]['permalink']}")
    _garante(posts[1]["views"] is None, "views vazio tem que virar null, não 0")
    campanhas_meta = normalizados["meta_ads"]["campaign_metrics"]
    _garante(len(campanhas_meta) == 14, f"campanhas meta: {len(campanhas_meta)}")
    grande = [c for c in campanhas_meta if c["period_start"] == "2026-08-15" and c["campaign_name"].startswith("Festa")][0]
    _garante(grande["spend"] == "1234.56", f"número BR 1.234,56 → {grande['spend']}")
    _garante(all(c["currency"] == "BRL" for c in campanhas_meta), "moeda BRL do rótulo")
    google = normalizados["google_ads"]["campaign_metrics"]
    _garante(len(google) == 14, f"google dia: {len(google)} (Total deve ser descartado)")
    _garante(google[0]["period_start"] == google[0]["period_end"] == "2026-08-11", "google diário")
    conta = normalizados["meta_account"]["account_metrics"]
    _garante(len(conta) == 7 and conta[-1]["followers"] == 12840, "conta por dia")

    veredito, dados = parsers.parse_file(FIXTURES / "google_ads_agregado.csv", maps, run_date=date(2026, 8, 18))
    _garante(veredito.status == "accepted" and veredito.kind == "google_ads", "agregado aceito")
    linhas = dados["campaign_metrics"]
    _garante(len(linhas) == 2 and linhas[0]["period_start"] == "2026-08-11" and linhas[0]["period_end"] == "2026-08-17",
             f"período do preâmbulo: {linhas[0]['period_start']}..{linhas[0]['period_end']}")

    veredito, _ = parsers.parse_file(FIXTURES / "invalido_colunas.csv", maps, run_date=date(2026, 8, 18))
    _garante(veredito.status == "rejected" and "colunas faltantes" in (veredito.reason or ""), f"inválido: {veredito.reason}")

    veredito, dados = parsers.parse_file(FIXTURES / "meta_ads_usd.csv", maps, run_date=date(2026, 8, 18))
    _garante(veredito.status == "accepted" and dados["campaign_metrics"][0]["currency"] == "USD", "moeda USD lida do rótulo")

    _garante(parsers.parse_number("1.234,56") == Decimal("1234.56"), "BR")
    _garante(parsers.parse_number("1,234.56") == Decimal("1234.56"), "US")
    _garante(parsers.parse_number("R$ 38,90") == Decimal("38.90"), "moeda no texto")
    try:
        parsers.parse_number("1.234")
        raise AssertionError("1.234 isolado deveria ser ambíguo")
    except parsers.AmbiguousNumber:
        pass
    _garante(parsers.parse_date("1 de ago. de 2026") == date(2026, 8, 1), "data por extenso pt-BR")
    estado["normalizados"] = normalizados


def cen_02_token() -> None:
    with app.test_client() as c:
        guardado = app.config["MARKETING_AGENT_TOKEN"]
        app.config["MARKETING_AGENT_TOKEN"] = ""
        try:
            r = c.get(_agent_url("/context?window_start=2026-08-11T00:00:00&window_end=2026-08-18T00:00:00&card_holder_email=x"))
            _garante(r.status_code == 404, f"sem env → {r.status_code}")
        finally:
            app.config["MARKETING_AGENT_TOKEN"] = guardado
        r = c.get(_agent_url("/context?window_start=2026-08-11T00:00:00&window_end=2026-08-18T00:00:00", token="errado"))
        _garante(r.status_code == 404, f"token errado → {r.status_code}")
        r = c.get(_agent_url(f"/context?window_start=2026-08-11T00:00:00&window_end=2026-08-18T00:00:00&card_holder_email={estado['titular'].email}"))
        _garante(r.status_code == 200, f"token certo → {r.status_code} {r.get_data(as_text=True)[:200]}")
        body = r.get_json()
        _garante(body["card_holder"]["email"] == estado["titular"].email, "card_holder resolvido")
        _garante("goals" in body and "new_clients_by_month" in body, "chaves do contexto")
        r = c.get(_agent_url("/context?window_start=2026-08-11T00:00:00&window_end=2026-08-18T00:00:00&card_holder_email=ninguem@x.y"))
        _garante(r.status_code == 403, f"titular inválido → {r.status_code}")


def _payload_run(run_id: str, *, campanhas=None, posts=None, conta=None, files=None) -> dict:
    n = estado["normalizados"]
    return {
        "run_id": run_id,
        "mode": "local",
        "window": ["2026-08-11T09:00:00+00:00", "2026-08-18T09:00:00+00:00"],
        "card_holder_email": estado["titular"].email,
        "files": files if files is not None else [
            {"filename": "meta_conteudo.csv", "sha256": f"{run_id}-a".ljust(64, "0"), "kind": "meta_content",
             "period_start": "2026-08-12", "period_end": "2026-08-17", "status": "accepted", "reason": None, "row_count": 3},
        ],
        "post_metrics": posts if posts is not None else n["meta_content"]["post_metrics"],
        "campaign_metrics": campanhas if campanhas is not None else n["meta_ads"]["campaign_metrics"] + n["google_ads"]["campaign_metrics"],
        "account_metrics": conta if conta is not None else n["meta_account"]["account_metrics"],
        "findings": [],
    }


def cen_03_ingestao() -> None:
    with app.test_client() as c:
        payload = _payload_run(f"{PREFIX}run1")
        r = c.post(_agent_url("/run"), json=payload)
        _garante(r.status_code == 200, f"run → {r.status_code} {r.get_data(as_text=True)[:300]}")
        body = r.get_json()
        _garante(body["replayed"] is False, "primeira vez não é replay")
        _garante(body["upserted"]["post_metrics"] == 3, f"posts upserted {body['upserted']}")
        _garante(body["upserted"]["campaign_metrics"] == 28, f"campanhas upserted {body['upserted']}")
        _garante(body["upserted"]["account_metrics"] == 7, f"conta upserted {body['upserted']}")
        r2 = c.post(_agent_url("/run"), json=payload)
        _garante(r2.status_code == 200 and r2.get_json()["replayed"] is True, "replay do mesmo run_id")
        run = MarketingAgentRun.query.filter_by(run_id=f"{PREFIX}run1").one()
        _garante(len(run.files) == 1, "arquivo registrado uma vez")
        payload2 = _payload_run(f"{PREFIX}run1b", files=payload["files"])
        r3 = c.post(_agent_url("/run"), json=payload2)
        _garante(r3.status_code == 200 and r3.get_json()["files"]["skipped_duplicate"] == 1, f"sha duplicado: {r3.get_json()['files']}")
        estado["resultado_run1"] = body


def _acao(body: dict, plataforma: str, mes: str) -> dict:
    acoes = [a for a in body.get("ad_spend", []) if a["platform"] == plataforma and a["month_ref"] == mes]
    _garante(len(acoes) == 1, f"esperava 1 ação para {plataforma} {mes}, veio {acoes}")
    return acoes[0]


def _linha_campanha(plataforma: str, nome: str, dia: str, gasto: str, *, fim: str | None = None,
                    moeda: str = "BRL") -> dict:
    return {"platform": plataforma, "campaign_id": "h:" + nome.lower().replace(" ", "-"), "campaign_name": nome,
            "period_start": dia, "period_end": fim or dia, "spend": gasto, "currency": moeda,
            "impressions": 100, "reach": None, "clicks": 5, "results": 1, "conversions": None, "result_type": None}


def cen_04_reembolso() -> None:
    from app.gastos.gastos_ops import approve_expense

    n = estado["normalizados"]
    meta = n["meta_ads"]["campaign_metrics"]
    with app.test_client() as c:
        # 1ª rodada do mês: cria um gasto por plataforma (Meta Ads + Google Ads, agosto/2026)
        r = c.post(_agent_url("/run"), json=_payload_run(f"{PREFIX}reemb1", posts=[], conta=[], files=[],
                                                           campanhas=meta + n["google_ads"]["campaign_metrics"]))
        _garante(r.status_code == 200, f"run reemb1 → {r.status_code} {r.get_data(as_text=True)[:300]}")
        body = r.get_json()
        # O cenário 3 já ingeriu as campanhas de agosto (e criou os lotes); aqui o lote é atualizado.
        criado = _acao(body, "Meta Ads", "2026-08")
        _garante(criado["action"] in ("created", "updated"), f"Meta Ads agosto: {criado}")
        _garante(criado["amount"] == "1553.96", f"soma das campanhas Meta em agosto: {criado['amount']}")
        gasto = db.session.get(SpecialExpense, criado["expense_id"])
        _garante(gasto is not None and gasto.status == "pendente" and gasto.category == "Marketing", "gasto pendente de Marketing")
        # Se o lote já existia (rodada local anterior), o titular é o daquela rodada — só exigimos
        # que seja reembolso a um usuário; o caso "criado agora" é coberto pelo lote de julho abaixo.
        _garante(gasto.disbursement_type == "reembolso" and gasto.reimburse_user_id is not None, "reembolso a um titular")
        _garante(gasto.expense_date.isoformat() == "2026-08-31" and gasto.receipt_path is None, "competência último dia do mês, sem comprovante")
        lote = MarketingAdSpendBatch.query.filter_by(special_expense_id=gasto.id).one()
        _garante(len(lote.lines) == 2 and lote.frozen_at is None, f"2 linhas por campanha, lote aberto: {len(lote.lines)}")
        google = _acao(body, "Google Ads", "2026-08")
        _garante(google["action"] in ("created", "updated") and google["amount"] == "305.40", f"Google agosto: {google}")
        estado["gasto_meta_id"], estado["gasto_google_id"] = gasto.id, google["expense_id"]

        # 2ª rodada: mais um dia do mês ⇒ o MESMO gasto é atualizado (pendente)
        extra = [_linha_campanha("Meta Ads", "Festa 15 anos SP", "2026-08-18", "10.00")]
        r = c.post(_agent_url("/run"), json=_payload_run(f"{PREFIX}reemb2", posts=[], conta=[], files=[], campanhas=extra))
        atualizado = _acao(r.get_json(), "Meta Ads", "2026-08")
        _garante(atualizado["action"] == "updated" and atualizado["expense_id"] == gasto.id, f"atualização: {atualizado}")
        _garante(atualizado["amount"] == "1563.96", f"valor acumulado: {atualizado['amount']}")
        _garante(SpecialExpense.query.filter(SpecialExpense.category == "Marketing",
                                             SpecialExpense.expense_date == date(2026, 8, 31)).count() == 2,
                 "nenhum gasto duplicado")

        # aprovado ⇒ congela; diferença posterior vira achado, não alteração
        approve_expense(db.session.get(SpecialExpense, gasto.id), estado["titular"])
        db.session.commit()
        extra = [_linha_campanha("Meta Ads", "Festa 15 anos SP", "2026-08-19", "5.00")]
        r = c.post(_agent_url("/run"), json=_payload_run(f"{PREFIX}reemb3", posts=[], conta=[], files=[], campanhas=extra))
        body = r.get_json()
        congelado = _acao(body, "Meta Ads", "2026-08")
        _garante(congelado["action"] == "frozen_divergent", f"congelado divergente: {congelado}")
        _garante(congelado["erp_amount"] == "1563.96" and congelado["reported_amount"] == "1568.96", f"valores: {congelado}")
        _garante(any(f["code"] == "gasto_divergente" for f in body["findings_server"]), "achado gasto_divergente")
        db.session.expire_all()
        _garante(str(db.session.get(SpecialExpense, gasto.id).amount) == "1563.96", "gasto aprovado não muda")
        lote = MarketingAdSpendBatch.query.filter_by(special_expense_id=gasto.id).one()
        _garante(lote.frozen_at is not None, "lote congelado")

        # gasto manual de Marketing no mês/plataforma ⇒ não cria, achado se divergir
        manual = SpecialExpense(description=f"{PREFIX}Anúncios Google Ads julho", category="Marketing",
                                amount=Decimal("100.00"), expense_date=date(2026, 7, 31), status="pendente",
                                created_by_id=estado["titular"].id)
        db.session.add(manual)
        db.session.commit()
        julho = [_linha_campanha("Google Ads", "Festa 15 anos SP", "2026-07-10", "50.00")]
        r = c.post(_agent_url("/run"), json=_payload_run(f"{PREFIX}reemb4", posts=[], conta=[], files=[], campanhas=julho))
        body = r.get_json()
        pulado = _acao(body, "Google Ads", "2026-07")
        _garante(pulado["action"] == "skipped_manual" and pulado["expense_id"] == manual.id, f"manual: {pulado}")
        _garante(any(f["code"] == "gasto_manual_existente" for f in body["findings_server"]), "achado gasto_manual_existente")
        _garante(MarketingAdSpendBatch.query.filter_by(platform="Google Ads", month_ref="2026-07").count() == 0, "sem lote para julho")

        # moeda ≠ BRL ⇒ métricas gravadas, reembolso não
        usd = [_linha_campanha("Meta Ads", "Campanha teste dólar", "2026-09-01", "12.00", moeda="USD")]
        r = c.post(_agent_url("/run"), json=_payload_run(f"{PREFIX}reemb5", posts=[], conta=[], files=[], campanhas=usd))
        body = r.get_json()
        moeda = _acao(body, "Meta Ads", "2026-09")
        _garante(moeda["action"] == "skipped_currency" and moeda.get("currency") == "USD", f"USD: {moeda}")
        _garante(MarketingAdSpendBatch.query.filter_by(platform="Meta Ads", month_ref="2026-09").count() == 0, "sem lote em USD")


def cen_05_sobreposicao() -> None:
    n = estado["normalizados"]
    with app.test_client() as c:
        diarias = n["google_ads"]["campaign_metrics"]
        agregadas = [
            {**diarias[0], "period_start": "2026-08-11", "period_end": "2026-08-17", "spend": "251.10"},
            {**diarias[7], "period_start": "2026-08-11", "period_end": "2026-08-17", "spend": "54.30"},
        ]
        r = c.post(_agent_url("/run"), json=_payload_run(f"{PREFIX}sobre1", posts=[], conta=[], files=[],
                                                           campanhas=diarias + agregadas))
        _garante(r.status_code == 200, f"run sobre1 → {r.status_code} {r.get_data(as_text=True)[:300]}")
        body = r.get_json()
        google = _acao(body, "Google Ads", "2026-08")
        _garante(google["amount"] == "305.40", f"só as diárias contam: {google['amount']} (agregado sobreposto ignorado)")
        _garante(any(f["code"] == "periodo_sobreposto" for f in body["findings_server"]), "achado periodo_sobreposto")


def _cria_card(c, titulo: str, publish_date: str, permalink: str | None = None) -> int:
    r = c.post("/api/marketing/posts", json={"title": f"{PREFIX}{titulo}", "status": "publicado", "platform": "Instagram",
                                             "publish_date": publish_date, "permalink": permalink})
    _garante(r.status_code in (200, 201), f"criar card → {r.status_code} {r.get_data(as_text=True)[:200]}")
    return r.get_json()["id"]


def cen_06_vinculo_post() -> None:
    from app.models import MarketingPostMetric

    n = estado["normalizados"]
    posts = n["meta_content"]["post_metrics"]
    with app.test_client() as c:
        _login(c, estado["marketing"].email)
        card_a = _cria_card(c, "Reels 15 anos", "2026-08-14", "https://www.instagram.com/reel/C9abcDEf1/?utm_source=x")
        card_b = _cria_card(c, "Post do dia 12", "2026-08-12")          # dois posts no export nesse dia ⇒ ambíguo
        card_d = _cria_card(c, "Post do dia 16", "2026-08-16")          # um post só nesse dia ⇒ vínculo por data
        extra = [{**posts[2], "platform_post_id": "17890016", "permalink": None, "published_at": "2026-08-16T10:00:00"}]
    with app.test_client() as c:
        r = c.post(_agent_url("/run"), json=_payload_run(f"{PREFIX}vinc1", posts=posts + extra, campanhas=[], conta=[], files=[]))
        _garante(r.status_code == 200, f"run vinc1 → {r.status_code} {r.get_data(as_text=True)[:300]}")
        links = r.get_json()["post_links"]
        por_post = {m.platform_post_id: m for m in MarketingPostMetric.query.filter(
            MarketingPostMetric.platform_post_id.in_(["17890001", "17890002", "17890003", "17890016"])).all()}
        _garante(por_post["17890001"].marketing_post_id == card_a and por_post["17890001"].link_method == "permalink", "vínculo pelo link")
        _garante(por_post["17890016"].marketing_post_id == card_d and por_post["17890016"].link_method == "date", "vínculo por data (único candidato)")
        _garante(por_post["17890002"].marketing_post_id is None and por_post["17890003"].marketing_post_id is None, "dois posts no mesmo dia ⇒ nenhum vínculo")
        ambiguos = {u["platform_post_id"]: u for u in links["unlinked_posts"]}
        _garante("17890002" in ambiguos and ambiguos["17890002"]["candidates"] == [card_b], f"candidatos do ambíguo: {ambiguos.get('17890002')}")
    # preencher o link depois ⇒ a rodada seguinte revincula
    with app.test_client() as c:
        _login(c, estado["marketing"].email)
        r = c.patch(f"/api/marketing/posts/{card_b}", json={"permalink": "https://www.instagram.com/p/C9xyzXYZ2/"})
        _garante(r.status_code == 200, f"patch link → {r.status_code}")
    with app.test_client() as c:
        r = c.post(_agent_url("/run"), json=_payload_run(f"{PREFIX}vinc2", posts=[], campanhas=[], conta=[], files=[]))
        _garante(r.status_code == 200, "run vinc2")
        foto = MarketingPostMetric.query.filter_by(platform_post_id="17890002").first()
        db.session.refresh(foto)
        _garante(foto.marketing_post_id == card_b and foto.link_method == "permalink", "revinculado pelo link na rodada seguinte")


def cen_07_kommo() -> None:
    import csv
    import tempfile

    from app.clientes.importer import import_kommo_csv

    import_kommo_csv(str(FIXTURES / "kommo_utm.csv"))
    db.session.commit()
    helena = Client.query.filter(Client.name.like(f"{PREFIX}%Helena%")).first()
    carla = Client.query.filter(Client.name.like(f"{PREFIX}%Carla%")).first()
    _garante(helena is not None and carla is not None, "clientes importados")
    _garante(helena.lead_origin == "Google Ads" and helena.utm_source == "google" and helena.utm_medium == "cpc"
             and helena.utm_campaign == "festa-15-anos-sp", f"utms da Helena: {helena.lead_origin} {helena.utm_campaign}")
    _garante(carla.utm_campaign == "personagens_para_festa_infantil" and carla.kommo_created_at.date() == date(2026, 8, 14), "utms da Carla")

    # export antigo, sem as colunas: importa como antes e não apaga o que já havia
    with open(FIXTURES / "kommo_utm.csv", encoding="utf-8", newline="") as fh:
        linhas = list(csv.DictReader(fh))
    sem_utm = [{k: v for k, v in ln.items() if k not in ("Origem do Lead", "utm_source", "utm_medium", "utm_campaign")} for ln in linhas]
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8", newline="") as tmp:
        writer = csv.DictWriter(tmp, fieldnames=list(sem_utm[0].keys()))
        writer.writeheader()
        writer.writerows(sem_utm)
        caminho = tmp.name
    import_kommo_csv(caminho)
    db.session.commit()
    db.session.refresh(helena)
    _garante(helena.utm_campaign == "festa-15-anos-sp", "export sem colunas não apaga utms já guardadas")
    os.unlink(caminho)


def cen_08_contexto() -> None:
    with app.test_client() as c:
        r = c.get(_agent_url(f"/context?window_start=2026-08-11T00:00:00&window_end=2026-08-18T00:00:00&card_holder_email={estado['titular'].email}"))
        _garante(r.status_code == 200, f"contexto → {r.status_code}")
        ctx = r.get_json()
        atribuidos = {a["utm_campaign"]: a for a in ctx["attributed_clients"]}
        _garante("festa-15-anos-sp" in atribuidos and "personagens_para_festa_infantil" in atribuidos, f"atribuídos: {list(atribuidos)}")
        _garante(atribuidos["festa-15-anos-sp"]["lead_origin"] == "Google Ads", "origem no contexto")
        _login(c, estado["marketing"].email)
        metas_api = {g["id"]: g["status"] for g in c.get("/api/marketing/goals").get_json()["items"]} if c.get("/api/marketing/goals").status_code == 200 else None
        if metas_api is not None:
            metas_ctx = {g["id"]: g["status"] for g in ctx["goals"]}
            _garante(metas_ctx == metas_api, f"metas do contexto ≠ endpoint: {metas_ctx} vs {metas_api}")
        # atribuição chega à tela: campanha Festa ganha 1 lead e a manchete vira leads
        r = c.get("/api/marketing/desempenho?start=2026-08-01&end=2026-08-31")
        body = r.get_json()
        festas = {cp["platform"]: cp for cp in body["campaigns"] if cp["campaign_name"] == "Festa 15 anos SP"}
        _garante("Google Ads" in festas and "Meta Ads" in festas, f"campanha nas duas plataformas: {list(festas)}")
        _garante(festas["Google Ads"]["leads"] >= 1 and festas["Google Ads"]["cost_per_lead"] is not None,
                 f"utm_source=google ⇒ lead vai para o Google Ads: {festas['Google Ads']}")
        _garante(festas["Meta Ads"]["leads"] == 0, f"Meta Ads não herda o lead do Google: {festas['Meta Ads']}")
        _garante(body["headline"]["kind"] == "leads" and body["headline"]["value"] >= 2, f"manchete de leads: {body['headline']}")


def cen_09_desempenho() -> None:
    with app.test_client() as c:
        _login(c, estado["marketing"].email)
        t0 = time.time()
        r = c.get("/api/marketing/desempenho?weeks=12")
        dt = time.time() - t0
        _garante(r.status_code == 200, f"desempenho → {r.status_code} {r.get_data(as_text=True)[:300]}")
        body = r.get_json()
        for chave in ("period", "headline", "weekly", "campaigns", "posts", "goals", "cac", "runs", "empty"):
            _garante(chave in body, f"chave {chave} ausente")
        _garante(body["period"]["weeks"] == 12 and len(body["weekly"]) == 12, f"12 semanas: {len(body['weekly'])}")
        _garante(body["headline"]["kind"] in ("leads", "alcance"), f"manchete: {body['headline']}")
        _garante(body["empty"] is False, "há rodadas (cenário 3) ⇒ empty false")
        _garante(any(run["run_id"].startswith(PREFIX) for run in body["runs"]), "rodadas de teste listadas")
        _garante(dt < 1.0, f"resposta em {dt:.2f}s (SC-006 exige < 1 s no servidor)")
        r = c.get("/api/marketing/desempenho?start=2026-08-01&end=2026-08-21")
        _garante(r.status_code == 200 and r.get_json()["period"]["start"] == "2026-08-01", "intervalo livre")
        campanhas = {cp["campaign_name"]: cp for cp in r.get_json()["campaigns"]}
        _garante("Festa 15 anos SP" in campanhas, f"campanhas do período: {list(campanhas)[:5]}")
        r = c.get("/api/marketing/desempenho?start=2026-08-21&end=2026-08-01")
        _garante(r.status_code == 400, f"start > end → {r.status_code}")
    with app.test_client() as c:
        _login(c, estado["casting"].email)
        r = c.get("/api/marketing/desempenho?weeks=4")
        _garante(r.status_code == 403, f"CASTING → {r.status_code}")


def cen_10_permalink() -> None:
    with app.test_client() as c:
        _login(c, estado["marketing"].email)
        card = _cria_card(c, "Card do permalink", "2026-08-01")
        r = c.patch(f"/api/marketing/posts/{card}", json={"permalink": "ftp://x"})
        _garante(r.status_code == 400, f"permalink inválido → {r.status_code}")
        _garante("permalink" in (r.get_json().get("error", {}).get("fields") or {}), f"erro no campo: {r.get_json()}")
        r = c.patch(f"/api/marketing/posts/{card}", json={"permalink": "https://www.instagram.com/p/ABCdef123/?utm_source=ig_web&igsh=zzz"})
        _garante(r.status_code == 200, f"permalink válido → {r.status_code}")
        _garante(r.get_json()["permalink"] == "https://www.instagram.com/p/ABCdef123/", f"normalizado: {r.get_json()['permalink']}")
        r = c.get(f"/api/marketing/posts/{card}")
        _garante(r.status_code == 200 and r.get_json()["permalink"] == "https://www.instagram.com/p/ABCdef123/", "GET devolve o link")
        r = c.patch(f"/api/marketing/posts/{card}", json={"permalink": None})
        _garante(r.status_code == 200 and r.get_json()["permalink"] is None, "limpar o link")


def cen_11_serializer_gasto() -> None:
    with app.test_client() as c:
        _login(c, estado["titular"].email)
        r = c.get("/api/gastos")
        _garante(r.status_code == 200, f"GET /api/gastos → {r.status_code}")
        gastos = {g["id"]: g for g in r.get_json()["expenses"]}
        gerado = gastos.get(estado["gasto_meta_id"])
        _garante(gerado is not None, "gasto gerado aparece na lista")
        lote = gerado.get("marketing_batch")
        _garante(lote is not None and lote["platform"] == "Meta Ads" and lote["month_ref"] == "2026-08", f"marketing_batch: {lote}")
        _garante(len(lote["lines"]) == 2 and lote["frozen"] is True, f"linhas e congelamento: {lote}")
        comum = next((g for g in gastos.values() if g["id"] != estado["gasto_meta_id"] and g["id"] != estado["gasto_google_id"]), None)
        _garante(comum is None or comum.get("marketing_batch") is None, "gasto comum tem marketing_batch null")


# ── preparação e limpeza ──────────────────────────────────────────────────────


def preparar() -> None:
    estado["titular"] = _cria_usuario("titular", RoleName.SUPERADMIN)
    estado["marketing"] = _cria_usuario("marketing", RoleName.MARKETING)
    estado["casting"] = _cria_usuario("casting", RoleName.CASTING)


def limpar() -> None:
    db.session.rollback()
    runs = MarketingAgentRun.query.filter(MarketingAgentRun.run_id.like(f"{PREFIX}%")).all()
    run_ids = [r.id for r in runs]
    if run_ids:
        from app.models import (
            MarketingAccountMetric,
            MarketingCampaignMetric,
            MarketingPostMetric,
        )
        for modelo in (MarketingPostMetric, MarketingCampaignMetric, MarketingAccountMetric):
            modelo.query.filter(modelo.run_id.in_(run_ids)).delete(synchronize_session=False)
        lotes = MarketingAdSpendBatch.query.filter(MarketingAdSpendBatch.last_run_id.in_(run_ids)).all()
        for lote in lotes:
            gasto = lote.expense
            db.session.delete(lote)
            if gasto is not None:
                db.session.delete(gasto)
        for r in runs:
            db.session.delete(r)
    SpecialExpense.query.filter(SpecialExpense.description.like(f"{PREFIX}%")).delete(synchronize_session=False)
    MarketingPost.query.filter(MarketingPost.title.like(f"{PREFIX}%")).delete(synchronize_session=False)
    Client.query.filter(Client.name.like(f"{PREFIX}%")).delete(synchronize_session=False)
    for sufixo in ("titular", "marketing", "casting"):
        _apaga_usuario(f"{PREFIX}{sufixo}@manto.local")
    db.session.commit()


def main() -> int:
    inicio = time.time()
    with app.app_context():
        try:
            limpar()
            preparar()
            print("Feature 256 — verificação contra manto_local")
            cenario("1. parsers das fixtures", cen_01_parsers)
            cenario("2. token do agente", cen_02_token)
            cenario("3. ingestão idempotente", cen_03_ingestao)
            cenario("4. reembolso mensal", cen_04_reembolso)
            cenario("5. sobreposição diário × agregado", cen_05_sobreposicao)
            cenario("6. vínculo post ↔ card", cen_06_vinculo_post)
            cenario("7. importador Kommo com utms", cen_07_kommo)
            cenario("8. contexto e atribuição", cen_08_contexto)
            cenario("9. API de desempenho (RBAC, período, vazio)", cen_09_desempenho)
            cenario("10. permalink no card", cen_10_permalink)
            cenario("11. serializer do gasto", cen_11_serializer_gasto)
        finally:
            cenario("12. limpeza", limpar)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK em {time.time() - inicio:.1f}s")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  - {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
