"""Verificação da 345b — Google Ads na rotina e diário das mudanças aprovadas no chat.

Roda contra o `manto_345b` (cópia descartável do `manto_lote`, na migration `d334b2c4e6f8` da `main`).

   1  /run com `diario` cria as entradas (origem rotina, autor = titular)
   2  mesmo run_id: replayed, nada duplicado
   3  item do diário sem motivo → 400 e NADA gravado (no código antigo a rodada grava: deve falhar)
   4  token errado → 404 (deve falhar)
   5  Desempenho com o relógio de SP num domingo 22h30 (UTC já é segunda): a semana termina no domingo
      (deve falhar no código antigo, que usa o `date.today()` do servidor)
   6  conversor do Google: reais, `results` = toque no botão, nenhum `conversations`
   7  linhas do Google pelo /run e /anuncios: gravadas como Google Ads, sem conversa, com reembolso

Dados de teste em março de 2031 e com o prefixo "Verify345b": nada encosta no histórico do espelho.
Token do agente gerado aqui, nunca o de produção. Nenhuma conexão externa (socket bloqueado).

Uso (raiz da worktree):
    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONPATH = (Get-Location).Path; $env:PYTHONUTF8 = '1'
    <python> specs\\345b-google-na-rotina\\verify_345b.py
"""

from __future__ import annotations

import os
import secrets
import socket
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

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
        raise OSError(f"[verify_345b] conexão externa bloqueada: {host}")
    return _create_connection_original(address, *args, **kwargs)


socket.create_connection = _so_local

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.models import User  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "marketing"))
import google_ads  # noqa: E402

RUN = secrets.token_hex(3)
PASSWORD = f"verify-345b-{secrets.token_hex(6)}"
TOKEN = f"tok345b-{RUN}-{secrets.token_hex(8)}"
PREFIXO = f"Verify345b {RUN}"
RUN_PREFIXO = f"V345b-{RUN}"
app = create_app()
app.config["MARKETING_AGENT_TOKEN"] = TOKEN
_engine = create_engine(os.environ["DATABASE_URL"].strip())
JANELA = ["2031-03-01T00:00:00", "2031-03-31T23:59:59"]


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


def cenario(fn):
    def run():
        try:
            fn()
        except Bloqueado as exc:
            resultados.append((fn.__name__, "BLOQUEADO", str(exc)))
            print(f"BLOQUEADO {fn.__name__}  [{exc}]", flush=True)
        except Exception as exc:  # noqa: BLE001
            with app.app_context():
                db.session.rollback()
            resultados.append((fn.__name__, "FALHA", f"{type(exc).__name__}: {exc}"[:300]))
            print(f"FALHA     {fn.__name__}  [{type(exc).__name__}: {str(exc)[:240]}]", flush=True)

    run.__name__ = fn.__name__
    return run


# ── Fixtures ────────────────────────────────────────────────────────────────────────────────
client = app.test_client()
with app.app_context():
    gestor = (
        User.query.filter(User.has_access.is_(True), User.is_active.is_(True))
        .filter(User.roles.any(name=RoleName.SUPERADMIN))
        .filter(User.email.isnot(None))
        .order_by(User.id)
        .first()
    )
    gestor.set_password(PASSWORD)
    GESTOR_EMAIL, GESTOR_ID = gestor.email, gestor.id
    db.session.commit()
limiter.enabled = False


def agente(metodo: str, caminho: str, *, token: str = TOKEN, **kw):
    return getattr(client, metodo)(f"/api/marketing-agent/{token}{caminho}", **kw)


def corpo_run(run_id: str, **extra) -> dict:
    return {
        "run_id": run_id,
        "mode": "local",
        "window": JANELA,
        "card_holder_email": GESTOR_EMAIL,
        "campaign_metrics": [],
        **extra,
    }


ITENS_DIARIO = [
    {
        "titulo": f"{PREFIXO} Pausado: PMAX (Google Ads)",
        "motivo": "86% do gasto fora da Pesquisa; aprovado pelo dono no chat em 17/11.",
        "evidencia": "R$ 41 mil desde jun/25; 14% em Pesquisa.",
        "resultado_esperado": "Mesmo volume de conversas com menos gasto.",
    },
    {
        "titulo": f"{PREFIXO} Pesquisa limpa: Amplo (Google Ads)",
        "motivo": "Display e parceiros desligados; aprovado pelo dono no chat em 17/11.",
        "reavaliar_em": "2031-03-20",
    },
]


# ── Cenários ────────────────────────────────────────────────────────────────────────────────


@cenario
def c1_diario_pelo_run():
    r = agente("post", "/run", json=corpo_run(f"{RUN_PREFIXO}-1", diario=ITENS_DIARIO))
    check(
        "1 /run com diario responde 200",
        r.status_code == 200,
        f"{r.status_code} {r.get_data(as_text=True)[:200]}",
    )
    ids = (r.get_json() or {}).get("diario") or []
    check("1 resposta traz os 2 ids do diário", len(ids) == 2, str(ids))
    linhas = _db(
        "select titulo, origem, autor_id, reavaliar_em from marketing_diario where titulo like :p order by id",
        p=f"{PREFIXO}%",
    )
    check("1 duas entradas gravadas (conexão separada)", len(linhas) == 2, str(linhas))
    check("1 origem = rotina", all(x[1] == "rotina" for x in linhas), str([x[1] for x in linhas]))
    check(
        "1 autor = titular do cartão",
        all(x[2] == GESTOR_ID for x in linhas),
        str([x[2] for x in linhas]),
    )
    if len(linhas) == 2:
        check(
            "1 reavaliar_em explícito respeitado",
            linhas[1][3] == date(2031, 3, 20),
            str(linhas[1][3]),
        )
        with app.app_context():
            from app.marketing.comando_ops import hoje_sp

            padrao = hoje_sp() + timedelta(days=14)
        check(
            "1 reavaliar_em padrão = hoje (SP) + 14",
            linhas[0][3] == padrao,
            f"{linhas[0][3]} × {padrao}",
        )


@cenario
def c2_replay_nao_duplica():
    r = agente("post", "/run", json=corpo_run(f"{RUN_PREFIXO}-1", diario=ITENS_DIARIO))
    check(
        "2 mesmo run_id → replayed",
        (r.get_json() or {}).get("replayed") is True,
        r.get_data(as_text=True)[:200],
    )
    n = _db("select count(*) from marketing_diario where titulo like :p", p=f"{PREFIXO}%")[0][0]
    check("2 continua com 2 entradas", n == 2, str(n))


@cenario
def c3_item_invalido_nada_gravado():
    run_id = f"{RUN_PREFIXO}-3"
    ruim = [{"titulo": f"{PREFIXO} válido", "motivo": "ok"}, {"titulo": f"{PREFIXO} sem motivo"}]
    r = agente("post", "/run", json=corpo_run(run_id, diario=ruim))
    corpo = r.get_json() or {}
    check("3 item sem motivo → 400", r.status_code == 400, f"{r.status_code} {str(corpo)[:200]}")
    campos = (corpo.get("error") or {}).get("fields") or {}
    check("3 o erro aponta diario[1].motivo", "diario[1].motivo" in campos, str(campos))
    rodada = _db("select count(*) from marketing_agent_runs where run_id = :r", r=run_id)[0][0]
    check("3 a rodada não foi gravada", rodada == 0, str(rodada))
    n = _db("select count(*) from marketing_diario where titulo like :p", p=f"{PREFIXO} válido%")[
        0
    ][0]
    check("3 nem o item válido foi gravado", n == 0, str(n))


@cenario
def c4_token_errado():
    r = agente(
        "post",
        "/run",
        token="token-errado",
        json=corpo_run(f"{RUN_PREFIXO}-4", diario=ITENS_DIARIO),
    )
    check("4 token errado → 404", r.status_code == 404, str(r.status_code))


@cenario
def c5_desempenho_no_relogio_de_sp():
    client.post("/api/auth/logout")
    r = client.post("/api/auth/login", json={"email": GESTOR_EMAIL, "password": PASSWORD})
    if r.status_code != 200:
        raise Bloqueado(f"login: {r.status_code}")
    # Domingo 09/03/2031 às 22h30 em São Paulo = segunda 10/03 01h30 em UTC: com o relógio do
    # servidor, a série já abriria a semana seguinte.
    assert date(2031, 3, 9).weekday() == 6
    with mock.patch("app.marketing.comando_ops.now_sp", return_value=datetime(2031, 3, 9, 22, 30)):
        r = client.get("/api/marketing/desempenho?weeks=4")
    periodo = (r.get_json() or {}).get("period") or {}
    check("5 desempenho responde 200", r.status_code == 200, str(r.status_code))
    check("5 a semana termina no domingo de SP", periodo.get("end") == "2031-03-09", str(periodo))
    check(
        "5 início = segunda de 3 semanas antes", periodo.get("start") == "2031-02-10", str(periodo)
    )


LINHA_CAMPANHA = {
    "campaign": {
        "resourceName": "customers/4115580695/campaigns/22646051445",
        "name": "FESTA · Pesquisa · Amplo (V4)",
        "id": "22646051445",
    },
    "metrics": {"clicks": "19", "conversions": 3, "costMicros": "8687898", "impressions": "460"},
    "segments": {"date": "2031-03-02"},
}
LINHA_ANUNCIO = {
    "campaign": {
        "resourceName": "customers/4115580695/campaigns/22646051445",
        "name": "FESTA · Pesquisa · Amplo (V4)",
        "id": "22646051445",
    },
    "adGroup": {"resourceName": "customers/4115580695/adGroups/177597465781", "id": "177597465781"},
    "metrics": {"clicks": "5", "conversions": 2, "costMicros": "2411240", "impressions": "173"},
    "adGroupAd": {
        "ad": {"resourceName": "customers/4115580695/ads/756948709404", "id": "756948709404"}
    },
    "segments": {"date": "2031-03-02"},
}


@cenario
def c6_conversor_do_google():
    cm = google_ads.para_campaign_metrics([LINHA_CAMPANHA])[0]
    check("6 plataforma Google Ads", cm["platform"] == "Google Ads", cm["platform"])
    check("6 gasto em reais com 2 casas", cm["spend"] == "8.69", cm["spend"])
    check("6 conversão do Google vai para results", cm["results"] == 3, str(cm["results"]))
    check("6 nunca vira conversations", "conversations" not in cm, str(cm))
    check(
        "6 diário (period_start == period_end)",
        cm["period_start"] == cm["period_end"] == "2031-03-02",
        str(cm),
    )
    item = google_ads.para_itens_de_anuncio([LINHA_ANUNCIO])[0]
    check(
        "6 anúncio: ad_id e adset_id do Google",
        (item["ad_id"], item["adset_id"]) == ("756948709404", "177597465781"),
        str(item),
    )
    check(
        "6 anúncio: sem conversations",
        "conversations" not in item and item["results"] == 2,
        str(item),
    )


@cenario
def c7_google_ponta_a_ponta():
    corpo = corpo_run(
        f"{RUN_PREFIXO}-7", campaign_metrics=google_ads.para_campaign_metrics([LINHA_CAMPANHA])
    )
    r = agente("post", "/run", json=corpo)
    check("7 /run com o Google → 200", r.status_code == 200, r.get_data(as_text=True)[:300])
    linha = _db(
        "select spend, results, conversations from marketing_campaign_metrics "
        "where platform = 'Google Ads' and campaign_id = '22646051445' and period_start = '2031-03-02'"
    )
    check("7 campanha gravada como Google Ads", len(linha) == 1, str(linha))
    if linha:
        check(
            "7 gasto 8,69, results 3, conversations vazio",
            (str(linha[0][0]), linha[0][1], linha[0][2]) == ("8.69", 3, None),
            str(linha),
        )
    lote = _db(
        "select reported_total from marketing_ad_spend_batches where platform = 'Google Ads' and month_ref = '2031-03'"
    )
    check(
        "7 reembolso do Google em 2031-03", len(lote) == 1 and str(lote[0][0]) == "8.69", str(lote)
    )
    r = agente(
        "post", "/anuncios", json={"items": google_ads.para_itens_de_anuncio([LINHA_ANUNCIO])}
    )
    check("7 /anuncios com o Google → 200", r.status_code == 200, r.get_data(as_text=True)[:200])
    ad = _db(
        "select spend, results, conversations from marketing_ad_metrics "
        "where platform = 'Google Ads' and ad_id = '756948709404' and metric_date = '2031-03-02'"
    )
    check(
        "7 anúncio gravado sem conversa",
        len(ad) == 1 and ad[0][2] is None and ad[0][1] == 2,
        str(ad),
    )


def limpeza() -> None:
    lotes = _db(
        "select id, special_expense_id from marketing_ad_spend_batches where month_ref = '2031-03' and platform = 'Google Ads'"
    )
    for lote_id, gasto_id in lotes:
        _exec("delete from marketing_ad_spend_lines where batch_id = :i", i=lote_id)
        _exec("delete from marketing_ad_spend_batches where id = :i", i=lote_id)
        if gasto_id:
            _exec("delete from special_expenses where id = :i", i=gasto_id)
    _exec(
        "delete from marketing_ad_metrics where platform = 'Google Ads' and metric_date = '2031-03-02'"
    )
    _exec(
        "delete from marketing_campaign_metrics where run_id in "
        "(select id from marketing_agent_runs where run_id like :p)",
        p=f"{RUN_PREFIXO}%",
    )
    _exec("delete from marketing_agent_runs where run_id like :p", p=f"{RUN_PREFIXO}%")
    _exec("delete from marketing_diario where titulo like :p", p=f"{PREFIXO}%")


try:
    for c in (
        c1_diario_pelo_run,
        c2_replay_nao_duplica,
        c3_item_invalido_nada_gravado,
        c4_token_errado,
        c5_desempenho_no_relogio_de_sp,
        c6_conversor_do_google,
        c7_google_ponta_a_ponta,
    ):
        c()
finally:
    try:
        limpeza()
        resto = _db("select count(*) from marketing_diario where titulo like :p", p=f"{PREFIXO}%")[
            0
        ][0]
        check("limpeza: nada do verify ficou no espelho", resto == 0, str(resto))
    except Exception as exc:  # noqa: BLE001
        check("limpeza", False, f"{type(exc).__name__}: {exc}"[:200])
    check("nenhuma conexão externa", not _ESCAPES, str(_ESCAPES))

falhas = [r for r in resultados if r[1] != "OK"]
print(f"\n{len(resultados) - len(falhas)}/{len(resultados)} OK")
sys.exit(1 if falhas else 0)
