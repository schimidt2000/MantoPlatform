"""Verificação da feature 340 — caixa de avisos de pagamento fora do deploy.

Roda contra o `manto_340` (dump de produção de 10/11; o `manto_local` está na migration do CRM 334 —
exceção registrada no `plan.md`). Escrito ANTES do núcleo (Princípio VIII): contra `dc78c788` os
cenários do receptor e do dreno ficam BLOQUEADOS (arquivo/função ausente) e os de config e
`render.yaml` FALHAM.

  R  1–8, 10   Receptor `manto-avisos` (WSGI de `servicos/avisos/app.py`, sem importar `app/`)
  C  9, 11     Thread de dreno, endereço do aviso e `render.yaml`
  D  12–17     Dreno no backend: venda pela regra da 310, duplicado, concorrência, ordem, retorno
               forjado, linha parada
  L  18        Limpeza; nada de rede escapou do dublê

A INFINITEPAY E O GOOGLE SÃO DUBLÊS QUE FALHAM FECHADO (molde do `verify_310.py`). A thread de
dreno é conferida NO CÓDIGO: subir `create_app()` sem `MANTO_SEM_THREADS` ligaria a sincronização
do Google e o e-mail reais do espelho.

Uso:
    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONPATH = (Get-Location).Path; $env:PYTHONUTF8 = '1'
    <python> specs\\340-caixa-de-avisos\\verify_340.py
"""

from __future__ import annotations

import ast
import importlib.util
import io
import json
import logging
import os
import re
import secrets
import shlex
import socket
import sys
import threading
import time
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

if "sqlite" in os.environ.get("DATABASE_URL", "sqlite"):
    sys.exit("ERRO: aponte DATABASE_URL para o Postgres local, nunca SQLite.")
if os.environ.get("MANTO_SEM_THREADS") != "1":
    sys.exit("ERRO: rode com MANTO_SEM_THREADS=1 (o espelho tem credenciais reais).")
if "localhost" not in os.environ["DATABASE_URL"] and "127.0.0.1" not in os.environ["DATABASE_URL"]:
    sys.exit("ERRO: este verify só roda contra banco local.")

# ── Disjuntor de rede: nada sai da máquina ──────────────────────────────────────────────────
_ESCAPES: list[str] = []
_create_connection_original = socket.create_connection


def _so_local(address, *args, **kwargs):
    host = str(address[0])
    if host not in ("localhost", "127.0.0.1", "::1"):
        _ESCAPES.append(host)
        raise OSError(f"[verify_340] conexão externa bloqueada: {host}")
    return _create_connection_original(address, *args, **kwargs)


socket.create_connection = _so_local

from sqlalchemy import create_engine, text  # noqa: E402
from werkzeug.test import Client, EnvironBuilder, run_wsgi_app  # noqa: E402

from app import create_app, db, limiter  # noqa: E402
from app.constants import now_sp  # noqa: E402
from app.integracoes import infinitepay_client as ipc  # noqa: E402
from app.marketing import virtuais_ops as ops  # noqa: E402
from app.models import CatalogCharacter, SiteSetting, VirtualCampaignSlot  # noqa: E402

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
RECEPTOR = RAIZ / "servicos" / "avisos" / "app.py"
RUN = secrets.token_hex(3)
URL_BANCO = os.environ["DATABASE_URL"].strip()
URL_MORTA = "postgresql://ninguem:nada@127.0.0.1:1/nada"
CAMINHO = "/api/webhooks/infinitepay/"

app = create_app()
# O Google é dublê (abaixo): a trava de escrita de evento pode ser aberta neste processo.
app.config["CALENDAR_SUPPRESS_EVENT_WRITES"] = False
_engine = create_engine(URL_BANCO)


def _db(sql: str, **p):
    with _engine.connect() as conn:
        return conn.execute(text(sql), p).fetchall()


def _db_exec(sql: str, **p) -> None:
    with _engine.begin() as conn:
        conn.execute(text(sql), p)


# ── Resultado ───────────────────────────────────────────────────────────────────────────────
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


def _ops(nome: str):
    fn = getattr(ops, nome, None)
    if fn is None:
        raise Bloqueado(f"virtuais_ops.{nome} ainda não existe")
    return fn


# ── O receptor, carregado sem importar app/ ─────────────────────────────────────────────────
_MODULO: list = []


def receptor_mod():
    if not RECEPTOR.exists():
        raise Bloqueado("servicos/avisos/app.py ainda não existe")
    if not _MODULO:
        spec = importlib.util.spec_from_file_location("manto_avisos_verify", RECEPTOR)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if not hasattr(mod, "criar_aplicacao"):
            raise Bloqueado("servicos/avisos/app.py sem criar_aplicacao()")
        _MODULO.append(mod)
    return _MODULO[0]


def receptor(url: str = URL_BANCO, **kw) -> Client:
    """Um receptor novo por cenário: limites em memória zerados."""
    return Client(receptor_mod().criar_aplicacao(url, **kw))


def avisar_receptor(cli: Client, payload: dict | bytes, token: str | None = None, *,
                    ip: str = "203.0.113.40"):
    corpo = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return cli.post(CAMINHO + (token or TOKEN), data=corpo,
                    headers={"Content-Type": "application/json",
                             "X-Forwarded-For": f"10.0.0.1, {ip}"})


def caixa(marcador: str) -> list[dict]:
    linhas = _db("select id, secret_ok, length(body), drained_at, notification_id, attempts, "
                 "alerted_at, claimed_at from virtual_payment_inbox where body like :m order by id",
                 m=f"%{marcador}%")
    k = ["id", "ok", "tam", "drained", "notif", "attempts", "alerted", "claimed"]
    return [dict(zip(k, linha, strict=True)) for linha in linhas]


# ── Dublê da InfinitePay (contrato do teste 0 da 310) ───────────────────────────────────────
class Operadora:
    def __init__(self) -> None:
        self.cobrancas: dict[str, dict] = {}
        self.links: list[dict] = []

    def pagar(self, order_nsu: str, valor: Decimal) -> dict:
        c = {"tx": f"tx-{RUN}-{secrets.token_hex(4)}", "slug": f"sl-{secrets.token_hex(4)}",
             "paid": True, "amount": valor, "paid_amount": valor}
        self.cobrancas[order_nsu] = c
        return c

    def aviso(self, order_nsu: str, c: dict) -> dict:
        return {"order_nsu": order_nsu, "transaction_nsu": c["tx"], "invoice_slug": c["slug"],
                "amount": int(c["amount"] * 100), "paid_amount": int(c["paid_amount"] * 100),
                "installments": 1, "capture_method": "pix", "receipt_url": "https://recibo/x",
                "items": [], "marca": f"v340-{RUN}"}

    def criar_link_pagamento(self, **kw):
        self.links.append(kw)
        return {"payment_url": f"https://checkout.dublê/{kw['order_nsu']}"}

    def consultar_pagamento(self, *, handle, order_nsu, transaction_nsu=None, slug=None, **kw):
        base = self.cobrancas.get(order_nsu)
        if base and transaction_nsu == base["tx"] and slug == base["slug"]:
            return {"resultado": "pago", "paid": True, "amount": base["amount"],
                    "paid_amount": base["paid_amount"], "capture_method": "pix",
                    "raw": {"success": True, "paid": True}}
        return {"resultado": "nao_encontrado", "paid": False, "amount": None,
                "paid_amount": None, "capture_method": None, "raw": {"success": False}}


OP = Operadora()
ipc.criar_link_pagamento = OP.criar_link_pagamento
ipc.consultar_pagamento = OP.consultar_pagamento

# ── Dublê do Google ─────────────────────────────────────────────────────────────────────────
from app.calendar import service as gcal  # noqa: E402

GOOGLE = {"insert": 0}


def _g_insert(calendar_id, title, start_dt, end_dt, description="", location="",
              conference_request_id=None, **kw):
    GOOGLE["insert"] += 1
    gid = f"g340{RUN}{GOOGLE['insert']}"
    return {"id": gid, "htmlLink": f"https://cal/{gid}",
            "hangoutLink": f"https://meet/{gid}" if conference_request_id else None}


gcal.insert_event = _g_insert
gcal.delete_event = lambda calendar_id, google_event_id: None
gcal.fetch_single_event = lambda calendar_id, gid: {"id": gid, "hangoutLink": f"https://meet/{gid}"}

# ── Fixtures ────────────────────────────────────────────────────────────────────────────────
client = app.test_client()
CRIADAS: list[int] = []
SETTINGS_ORIGINAIS: dict = {}
NOTIF_ANTES = _db("select coalesce(max(id), 0) from notifications")[0][0]
TOKEN = f"tok340-{RUN}-{secrets.token_hex(8)}"

with app.app_context():
    s = SiteSetting.query.get(1)
    for campo in ("infinitepay_handle", "infinitepay_webhook_token", "virtuais_pagamento_ativo",
                  "infinitepay_webhook_token_anterior", "infinitepay_webhook_token_anterior_ate"):
        SETTINGS_ORIGINAIS[campo] = getattr(s, campo, None)
    s.infinitepay_handle = "verify-340"
    s.infinitepay_webhook_token = TOKEN
    s.infinitepay_webhook_token_anterior = None
    s.infinitepay_webhook_token_anterior_ate = None
    s.virtuais_pagamento_ativo = True
    PERSONAGEM_ID = CatalogCharacter.query.filter_by(is_active=True).first().id
    db.session.commit()

limiter.enabled = False
_SEQ = [0]
_BASE_DIA = datetime(2031, 4, 7, 9, 0)


def nova_campanha() -> tuple[int, str]:
    with app.app_context():
        c = ops.criar_campanha(
            catalog_character_id=PERSONAGEM_ID, title=f"Verify340 {RUN} {len(CRIADAS)}",
            price_live=Decimal("100.00"), price_recorded=Decimal("60.00"),
            recorded_capacity=0, tolerance_terms="termos",
            cover_url="/catalogo/midia/campanhas/x.jpg",
        )
        c.max_reservations_per_origin = 10_000
        c.status = "publicada"
        db.session.commit()
        CRIADAS.append(c.id)
        return c.id, c.slug


def novo_horario(camp_id: int) -> int:
    _SEQ[0] += 1
    with app.app_context():
        h = VirtualCampaignSlot(campaign_id=camp_id,
                                start_at=_BASE_DIA + timedelta(minutes=10 * _SEQ[0]),
                                status="livre")
        db.session.add(h)
        db.session.commit()
        return h.id


def reservar(slug: str, slot_id: int, *, ip: str) -> dict:
    tel = f"119{secrets.randbelow(10**8):08d}"
    r = client.post(
        f"/api/virtuais/campanhas/{slug}/reservar",
        json={"modality": "ao_vivo", "slot_id": slot_id, "child_name": "Teo", "child_age": 6,
              "contact_phone": tel, "contact_email": f"v340-{RUN}@example.com",
              "client_token": secrets.token_hex(8)},
        headers={"X-Manto-Client-Ip": ip, "X-Forwarded-For": ip, "User-Agent": "verify-340"},
    )
    corpo = r.get_json() or {}
    if r.status_code not in (200, 201) or "order_nsu" not in corpo:
        raise RuntimeError(f"reserva falhou: {r.status_code} {corpo}")
    return corpo


def pedido(nsu: str) -> dict:
    linha = _db("select id, status, slot_id, event_id, total_value from virtual_orders "
                "where order_nsu=:n", n=nsu)
    if not linha:
        return {}
    return dict(zip(["id", "status", "slot_id", "event_id", "total"], linha[0], strict=True))


def vencer(nsu: str) -> None:
    passado = now_sp() - timedelta(minutes=1)
    _db_exec("update virtual_orders set locked_until=:p where order_nsu=:n", p=passado, n=nsu)
    _db_exec("update virtual_campaign_slots set locked_until=:p where order_id="
             "(select id from virtual_orders where order_nsu=:n)", p=passado, n=nsu)


def drenar() -> dict:
    fn = _ops("drenar_caixa_de_avisos")
    with app.app_context():
        return fn()


def pedido_pago_via_caixa(ip: str) -> tuple[str, dict, dict]:
    """Reserva, paga no dublê e devolve (nsu, cobrança, aviso) — o aviso ainda não foi entregue."""
    cid, slug = nova_campanha()
    ra = reservar(slug, novo_horario(cid), ip=ip)
    nsu = ra["order_nsu"]
    c = OP.pagar(nsu, Decimal(str(pedido(nsu)["total"])))
    return nsu, c, OP.aviso(nsu, c)


# ════════════════════════════════════════════════════════════════════════════════════════════
# R — Receptor
# ════════════════════════════════════════════════════════════════════════════════════════════
@cenario("1  aviso com o segredo atual → 200 em < 1 s e linha na caixa, sem decidir nada")
def c1():
    cli = receptor()
    marca = f"c1-{RUN}"
    t0 = time.time()
    r = avisar_receptor(cli, {"order_nsu": marca, "transaction_nsu": f"tx-{marca}"})
    dt = time.time() - t0
    check("1.1 200", r.status_code == 200, str(r.status_code))
    check("1.2 corpo do contrato", r.get_json() == {"success": True, "message": None},
          str(r.get_data(as_text=True))[:120])
    check("1.3 em menos de 1 s", dt < 1.0, f"{dt:.3f}s")
    linhas = caixa(marca)
    check("1.4 uma linha na caixa, secret_ok, sem dreno",
          len(linhas) == 1 and linhas[0]["ok"] and linhas[0]["drained"] is None, str(linhas))
    corpo = _db("select body from virtual_payment_inbox where body like :m", m=f"%{marca}%")
    check("1.5 corpo guardado como veio, sem o segredo",
          bool(corpo) and json.loads(corpo[0][0]).get("order_nsu") == marca
          and TOKEN not in corpo[0][0], str(corpo)[:120])


@cenario("2  banco fora → 400 (a operadora reenvia), nunca 200 sem ter guardado")
def c2():
    cli = receptor(URL_MORTA)
    marca = f"c2-{RUN}"
    r = avisar_receptor(cli, {"order_nsu": marca})
    check("2.1 400", r.status_code == 400, str(r.status_code))
    check("2.2 corpo fixo, sem detalhe interno",
          r.get_json() == {"success": False, "message": "Try again"}, r.get_data(as_text=True)[:160])
    check("2.3 nada guardado", caixa(marca) == [])


@cenario("3  segredo errado → 404 e só um resumo recusado (deve falhar a autenticação)")
def c3():
    cli = receptor()
    marca = f"c3-{RUN}"
    r = avisar_receptor(cli, {"order_nsu": marca, "lixo": "x" * 5000}, token="errado")
    check("3.1 404", r.status_code == 404, str(r.status_code))
    linhas = caixa(marca)
    check("3.2 uma linha recusada de até 2 KB",
          len(linhas) == 1 and not linhas[0]["ok"] and linhas[0]["tam"] <= 2048, str(linhas))
    r2 = cli.post(CAMINHO, data=b"{}", headers={"Content-Type": "application/json"})
    check("3.3 sem segredo no caminho → 404", r2.status_code == 404, str(r2.status_code))


@cenario("4  segredo anterior: dentro da janela vale, vencido não (deve falhar)")
def c4():
    anterior = f"ant340-{RUN}-{secrets.token_hex(6)}"
    _db_exec("update site_settings set infinitepay_webhook_token_anterior=:a, "
             "infinitepay_webhook_token_anterior_ate=:t where id=1",
             a=anterior, t=now_sp() + timedelta(hours=1))
    cli = receptor()
    r = avisar_receptor(cli, {"order_nsu": f"c4a-{RUN}"}, token=anterior)
    check("4.1 anterior dentro da janela → 200", r.status_code == 200, str(r.status_code))
    _db_exec("update site_settings set infinitepay_webhook_token_anterior_ate=:t where id=1",
             t=now_sp() - timedelta(minutes=1))
    r = avisar_receptor(cli, {"order_nsu": f"c4b-{RUN}"}, token=anterior)
    check("4.2 anterior vencido → 404", r.status_code == 404, str(r.status_code))
    _db_exec("update site_settings set infinitepay_webhook_token_anterior=null, "
             "infinitepay_webhook_token_anterior_ate=null where id=1")


@cenario("5  corpo acima de 64 KB → 413, com e sem Content-Length")
def c5():
    mod = receptor_mod()
    grande = b'{"x":"' + b"a" * (mod.CORPO_MAXIMO) + b'"}'
    cli = receptor()
    r = cli.post(CAMINHO + TOKEN, data=grande, headers={"Content-Type": "application/json"})
    check("5.1 com Content-Length → 413", r.status_code == 413, str(r.status_code))
    env = EnvironBuilder(path=CAMINHO + TOKEN, method="POST",
                         input_stream=io.BytesIO(grande)).get_environ()
    env.pop("CONTENT_LENGTH", None)
    env["HTTP_TRANSFER_ENCODING"] = "chunked"
    env["wsgi.input_terminated"] = True
    _, status, _ = run_wsgi_app(mod.criar_aplicacao(URL_BANCO), env, buffered=True)
    check("5.2 sem Content-Length (chunked) → 413", status.startswith("413"), status)
    total = _db("select count(*) from virtual_payment_inbox where length(body) > :n",
                n=mod.CORPO_MAXIMO)[0][0]
    check("5.3 nada acima do teto guardado", total == 0, str(total))


@cenario("6  61ª chamada no mesmo minuto do mesmo cliente → 429; outro cliente passa")
def c6():
    cli = receptor(limite_minuto=5)
    codigos = [avisar_receptor(cli, {"marca": f"c6-{RUN}"}, ip="203.0.113.66").status_code
               for _ in range(6)]
    check("6.1 a 6ª do mesmo IP → 429", codigos[-1] == 429 and 429 not in codigos[:5], str(codigos))
    outro = avisar_receptor(cli, {"marca": f"c6-{RUN}"}, ip="203.0.113.67").status_code
    check("6.2 outro IP passa", outro == 200, str(outro))
    falso = cli.post(CAMINHO + TOKEN, data=b'{"marca":"c6"}',
                     headers={"X-Forwarded-For": "1.2.3.4, 203.0.113.66"}).status_code
    check("6.3 IP forjado à esquerda do XFF não abre balde novo", falso == 429, str(falso))
    check("6.4 limite padrão é 60/min", receptor_mod().LIMITE_POR_MINUTO == 60,
          str(receptor_mod().LIMITE_POR_MINUTO))


@cenario("7  teto de recusas guardadas por hora: acima dele, 404 sem gravar")
def c7():
    cli = receptor(teto_recusas=2)
    marca = f"c7-{RUN}"
    codigos = [avisar_receptor(cli, {"marca": marca}, token="errado", ip=f"198.51.100.{i}")
               .status_code for i in range(3)]
    check("7.1 as três → 404", codigos == [404, 404, 404], str(codigos))
    check("7.2 só duas guardadas", len(caixa(marca)) == 2, str(caixa(marca)))
    check("7.3 teto padrão é 120/h", receptor_mod().TETO_RECUSAS_HORA == 120,
          str(receptor_mod().TETO_RECUSAS_HORA))


class _Coletor(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.linhas: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.linhas.append(self.format(record))


@cenario("8  o segredo nunca aparece no log do receptor")
def c8():
    mod = receptor_mod()
    coletor = _Coletor()
    log = logging.getLogger(mod.LOGGER_NOME)
    log.addHandler(coletor)
    nivel = log.level
    log.setLevel(logging.DEBUG)
    try:
        cli = receptor()
        avisar_receptor(cli, {"marca": f"c8-{RUN}"})
        avisar_receptor(cli, {"marca": f"c8-{RUN}"}, token=TOKEN + "x")
        receptor(URL_MORTA).post(CAMINHO + TOKEN, data=b"{}")
    finally:
        log.removeHandler(coletor)
        log.setLevel(nivel)
    texto = "\n".join(coletor.linhas)
    check("8.1 houve log", bool(coletor.linhas), "nenhuma linha")
    check("8.2 linha com código e id, sem a URL",
          any(re.search(r"\[avisos\] 200 id=\d+", linha) for linha in coletor.linhas), texto[:200])
    check("8.3 nenhuma linha com o segredo nem com o caminho do aviso",
          TOKEN not in texto and CAMINHO not in texto, texto[:300])


@cenario("10 /health sem banco; /health/banco 200 com banco e 503 sem")
def c10():
    vivo, morto = receptor(), receptor(URL_MORTA)
    r = morto.get("/health")
    check("10.1 /health 200 mesmo sem banco", r.status_code == 200 and r.get_json() == {"ok": True},
          f"{r.status_code} {r.get_data(as_text=True)[:80]}")
    check("10.2 /health/banco 200 com banco", vivo.get("/health/banco").status_code == 200)
    check("10.3 /health/banco 503 sem banco", morto.get("/health/banco").status_code == 503)
    check("10.4 caminho desconhecido → 404", vivo.get("/qualquer").status_code == 404)
    check("10.5 GET no aviso → 405", vivo.get(CAMINHO + TOKEN).status_code == 405)


# ════════════════════════════════════════════════════════════════════════════════════════════
# C — Thread, endereço do aviso, render.yaml
# ════════════════════════════════════════════════════════════════════════════════════════════
def _bloco_sem_threads(arvore: ast.Module) -> ast.If | None:
    for no in ast.walk(arvore):
        if isinstance(no, ast.If) and "MANTO_SEM_THREADS" in ast.unparse(no.test):
            return no
    return None


@cenario("9  thread de dreno (no código), uma volta drena, link novo avisa o receptor")
def c9():
    fonte = (RAIZ / "app" / "__init__.py").read_text(encoding="utf-8")
    arvore = ast.parse(fonte)
    bloco = _bloco_sem_threads(arvore)
    chamadas_else = {ast.unparse(n.func) for n in ast.walk(ast.Module(body=bloco.orelse,
                     type_ignores=[])) if isinstance(n, ast.Call)} if bloco else set()
    check("9.1 _start_caixa_de_avisos chamada só no bloco que MANTO_SEM_THREADS desliga",
          "_start_caixa_de_avisos" in chamadas_else, str(sorted(chamadas_else))[:200])
    check("9.2 intervalo de 10 s", app.config.get("VIRTUAL_CAIXA_INTERVAL") == 10,
          str(app.config.get("VIRTUAL_CAIXA_INTERVAL")))
    import app as pacote_app
    volta = getattr(pacote_app, "_volta_da_caixa", None)
    if volta is None:
        raise Bloqueado("app._volta_da_caixa ainda não existe")
    marca = f"c9-{RUN}"
    avisar_receptor(receptor(), {"order_nsu": marca, "transaction_nsu": f"tx-{marca}"})
    volta(app)
    linhas = caixa(marca)
    check("9.3 uma volta da thread drena a caixa", linhas and linhas[0]["drained"] is not None,
          str(linhas))
    cid, slug = nova_campanha()
    reservar(slug, novo_horario(cid), ip="198.51.100.90")
    url = (OP.links[-1] if OP.links else {}).get("webhook_url", "")
    check("9.4 link novo avisa o manto-avisos",
          url.startswith("https://manto-avisos.onrender.com/api/webhooks/infinitepay/"), url[:60])
    regras = {r.rule for r in app.url_map.iter_rules()}
    check("9.5 rota antiga do backend continua", "/api/webhooks/infinitepay/<token>" in regras)


def _servico(texto: str, nome: str) -> str:
    inicio = re.search(rf"^\s*name:\s*{re.escape(nome)}\s*$", texto, re.MULTILINE)
    if not inicio:
        return ""
    resto = texto[inicio.end():]
    proximo = re.search(r"^\s*-\s*type:", resto, re.MULTILINE)
    return resto if not proximo else resto[: proximo.start()]


def _gunicorn_aceita(start: str, alvo: str) -> bool:
    spec = importlib.util.spec_from_file_location(
        "validar_startcommand_340", RAIZ / "scripts" / "validar_startcommand.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # traz os stubs de grp/pwd/fcntl e o Config do gunicorn
    args = [a.replace("$PORT", "8080") for a in shlex.split(start.split("gunicorn", 1)[1])
            if a != alvo]
    try:
        mod.Config().parser().parse_args(args)
    except SystemExit:
        return False
    return True


@cenario("11 render.yaml: manto-avisos, healthcheck do frontend, filtro do backend")
def c11():
    texto = (RAIZ / "render.yaml").read_text(encoding="utf-8")
    avisos = _servico(texto, "manto-avisos")
    check("11.1 serviço manto-avisos existe", bool(avisos))
    check("11.2 rootDir próprio, healthcheck e plano pago",
          "rootDir: servicos/avisos" in avisos and re.search(r"healthCheckPath:\s*/health\s", avisos)
          is not None and re.search(r"plan:\s*starter", avisos) is not None, avisos[:200])
    check("11.3 sem disco", "disk:" not in avisos)
    check("11.4 DATABASE_URL do manto-postgres",
          re.search(r"key:\s*DATABASE_URL\s+fromDatabase:\s+name:\s*manto-postgres", avisos)
          is not None)
    start = re.findall(r"^\s*startCommand:\s*(.+?)\s*$", avisos, re.MULTILINE)
    check("11.5 startCommand aceito pelo parser real do gunicorn",
          len(start) == 1 and _gunicorn_aceita(start[0], "app:aplicacao"), str(start)[:160])
    check("11.6 log de acesso sem a URL (%(U)s, %(r)s)",
          bool(start) and "%(U)s" not in start[0] and "%(r)s" not in start[0], str(start)[:160])
    frontend = _servico(texto, "manto-frontend")
    check("11.7 healthCheckPath no manto-frontend",
          re.search(r"^\s*healthCheckPath:\s*/\S*\s*$", frontend, re.MULTILINE) is not None)
    backend = _servico(texto, "manto-backend")
    ignorados = re.search(r"buildFilter:\s+ignoredPaths:\s+((?:\s*-\s*\S+\s*)+)", backend)
    lista = re.findall(r"-\s*(\S+)", ignorados.group(1)) if ignorados else []
    check("11.8 backend ignora docs, specs, frontend, servicos, .claude e .specify",
          {"docs/**", "specs/**", "frontend/**", "servicos/**", ".claude/**", ".specify/**"}
          <= set(lista), str(lista))


# ════════════════════════════════════════════════════════════════════════════════════════════
# D — Dreno no backend
# ════════════════════════════════════════════════════════════════════════════════════════════
@cenario("13 aviso pago guardado na caixa → venda pela mesma regra da 310")
def c13():
    nsu, c, aviso = pedido_pago_via_caixa("198.51.100.130")
    r = avisar_receptor(receptor(), aviso)
    check("13.1 receptor guardou", r.status_code == 200, str(r.status_code))
    check("13.2 receptor não decidiu", pedido(nsu)["status"] != "pago", str(pedido(nsu)))
    drenar()
    p = pedido(nsu)
    check("13.3 pedido pago e com evento", p["status"] == "pago" and p["event_id"] is not None, str(p))
    notif = _db("select id, outcome from virtual_payment_notifications where transaction_nsu=:t",
                t=c["tx"])
    linhas = caixa(c["tx"])
    check("13.4 aviso efetivado pela regra da 310", notif and notif[0][1] == "efetivado", str(notif))
    check("13.5 linha drenada com notification_id",
          len(linhas) == 1 and linhas[0]["drained"] is not None and notif
          and linhas[0]["notif"] == notif[0][0], str(linhas))
    email = _db("select kind from virtual_order_notifications where order_id=:o", o=p["id"])
    check("13.6 e-mail de compra confirmada registrado", ("compra_confirmada",) in email, str(email))


@cenario("14 mesmo aviso duas vezes → uma venda; o segundo cai como já decidido")
def c14():
    nsu, c, aviso = pedido_pago_via_caixa("198.51.100.140")
    cli = receptor()
    avisar_receptor(cli, aviso)
    avisar_receptor(cli, aviso)
    drenar()
    linhas = caixa(c["tx"])
    n = _db("select count(*) from virtual_payment_notifications where transaction_nsu=:t",
            t=c["tx"])[0][0]
    check("14.1 duas linhas na caixa, as duas drenadas",
          len(linhas) == 2 and all(lin["drained"] for lin in linhas), str(linhas))
    check("14.2 um registro do aviso e um pedido pago",
          n == 1 and pedido(nsu)["status"] == "pago", f"{n} {pedido(nsu)}")
    check("14.3 o segundo sem notification_id (já decidido)", linhas[-1]["notif"] is None,
          str(linhas))


@cenario("15 dois drenos ao mesmo tempo → a linha é processada uma vez")
def c15():
    _ops("drenar_caixa_de_avisos")
    marca = f"c15-{RUN}"
    avisar_receptor(receptor(), {"order_nsu": marca, "transaction_nsu": f"tx-{marca}"})
    barreira = threading.Barrier(2)
    resumos: list[dict] = []

    def um() -> None:
        barreira.wait()
        with app.app_context():
            resumos.append(ops.drenar_caixa_de_avisos())
            db.session.remove()

    tarefas = [threading.Thread(target=um) for _ in range(2)]
    for t in tarefas:
        t.start()
    for t in tarefas:
        t.join(60)
    linhas = caixa(marca)
    n = _db("select count(*) from virtual_payment_notifications where transaction_nsu=:t",
            t=f"tx-{marca}")[0][0]
    drenadas = sum(int((r or {}).get("drenadas", 0)) for r in resumos)
    check("15.1 uma tentativa, um registro", linhas and linhas[0]["attempts"] == 1 and n == 1,
          f"{linhas} n={n}")
    check("15.2 a soma dos drenos é uma linha", drenadas == 1, str(resumos))


@cenario("16 a caixa é drenada ANTES de expirar reservas — o pagamento não perde o horário")
def c16():
    nsu, c, aviso = pedido_pago_via_caixa("198.51.100.160")
    vencer(nsu)
    avisar_receptor(receptor(), aviso)
    ordem: list[str] = []
    originais = {"drenar_caixa_de_avisos": getattr(ops, "drenar_caixa_de_avisos", None),
                 "expirar_reservas": ops.expirar_reservas}
    if originais["drenar_caixa_de_avisos"] is None:
        raise Bloqueado("virtuais_ops.drenar_caixa_de_avisos ainda não existe")

    def espiao(nome):
        def fn(*a, **kw):
            ordem.append(nome)
            return originais[nome](*a, **kw)
        return fn

    for nome in originais:
        setattr(ops, nome, espiao(nome))
    try:
        with app.app_context():
            ops.ciclo_de_varredura()
    finally:
        for nome, fn in originais.items():
            setattr(ops, nome, fn)
    check("16.1 caixa antes da expiração",
          "drenar_caixa_de_avisos" in ordem and ordem.index("drenar_caixa_de_avisos")
          < ordem.index("expirar_reservas"), str(ordem))
    p = pedido(nsu)
    vendido = _db("select status, order_id from virtual_campaign_slots where id=:s", s=p["slot_id"])
    check("16.2 pedido pago e horário vendido para ele",
          p["status"] == "pago" and vendido and vendido[0] == ("vendido", p["id"]),
          f"{p} {vendido}")


@cenario("17 retorno forjado antes do aviso, pela caixa: o aviso autenticado manda (deve falhar o forjado)")
def c17():
    cid, slug = nova_campanha()
    ra = reservar(slug, novo_horario(cid), ip="198.51.100.170")
    rb = reservar(slug, novo_horario(cid), ip="198.51.100.171")
    a, b = ra["order_nsu"], rb["order_nsu"]
    cb = OP.pagar(b, Decimal(str(pedido(b)["total"])))
    client.post(f"/api/virtuais/pedidos/{ra['public_token']}/retorno",
                json={"order_nsu": a, "transaction_nsu": cb["tx"], "slug": cb["slug"]})
    avisar_receptor(receptor(), OP.aviso(b, cb))
    drenar()
    check("17.1 o aviso autenticado de B confirma B", pedido(b)["status"] == "pago", str(pedido(b)))
    check("17.2 A não ganhou nada", pedido(a)["status"] != "pago", str(pedido(a)))


@cenario("12 linha parada há mais de 1 h → sino uma vez")
def c12():
    marca = f"c12-{RUN}"
    _db_exec("insert into virtual_payment_inbox (received_at, body, secret_ok, claimed_at, attempts) "
             "values (:r, :b, true, :c, 1)",
             r=now_sp() - timedelta(hours=2), b=json.dumps({"order_nsu": marca}),
             c=now_sp())  # reivindicada agora por "outro processo": o dreno não a pega
    drenar()
    drenar()
    linha = caixa(marca)
    chave = f"virtual.caixa:{linha[0]['id']}" if linha else "?"
    sinos = _db("select count(distinct dedupe_key), count(*) from notifications "
                "where id > :n and dedupe_key like :k", n=NOTIF_ANTES, k=f"{chave}%")
    check("12.1 alerted_at gravado", bool(linha) and linha[0]["alerted"] is not None, str(linha))
    check("12.2 um sino (uma chave), sem repetir na segunda volta",
          sinos and sinos[0][0] == 1, str(sinos))


# ════════════════════════════════════════════════════════════════════════════════════════════
def limpar() -> None:
    with app.app_context():
        db.session.rollback()
    with _engine.begin() as conn:
        for cid in CRIADAS:
            ordens = [r[0] for r in conn.execute(text(
                "select id from virtual_orders where campaign_id=:c"), {"c": cid})]
            eventos = [r[0] for r in conn.execute(text(
                "select event_id from virtual_orders where campaign_id=:c and event_id is not null"),
                {"c": cid})]
            if ordens:
                conn.execute(text("update virtual_campaign_slots set order_id=null "
                                  "where campaign_id=:c"), {"c": cid})
                conn.execute(text("update virtual_payment_inbox set notification_id=null where "
                                  "notification_id in (select id from virtual_payment_notifications "
                                  "where order_id = any(:o))"), {"o": ordens})
                for tabela in ("virtual_payment_notifications", "virtual_refund_requests",
                               "virtual_order_notifications", "virtual_media_deliveries"):
                    conn.execute(text(f"delete from {tabela} where order_id = any(:o)"),
                                 {"o": ordens})
                conn.execute(text("delete from virtual_orders where campaign_id=:c"), {"c": cid})
            for ev in eventos:
                if conn.execute(text("select 1 from information_schema.tables where "
                                     "table_name='event_3d_gifts'")).first():
                    conn.execute(text("delete from event_3d_gifts where event_id=:e"), {"e": ev})
                conn.execute(text("delete from event_roles where event_id=:e"), {"e": ev})
                conn.execute(text("delete from calendar_events where id=:e"), {"e": ev})
            conn.execute(text("delete from virtual_campaign_slots where campaign_id=:c"), {"c": cid})
            if conn.execute(text("select 1 from information_schema.tables where "
                                 "table_name='virtual_campaign_acervo'")).first():
                conn.execute(text("delete from virtual_campaign_acervo where campaign_id=:c"),
                             {"c": cid})
            conn.execute(text("delete from virtual_campaigns where id=:c"), {"c": cid})
        if conn.execute(text("select 1 from information_schema.tables where "
                             "table_name='virtual_payment_inbox'")).first():
            conn.execute(text("delete from virtual_payment_inbox where body like :r"),
                         {"r": f"%{RUN}%"})
        conn.execute(text("delete from virtual_payment_notifications where order_id is null and "
                          "(transaction_nsu like :t or order_nsu like :t or raw_payload like :t)"),
                     {"t": f"%{RUN}%"})
        conn.execute(text("delete from notifications where id > :n and kind like 'virtual.%'"),
                     {"n": NOTIF_ANTES})
    with app.app_context():
        s = SiteSetting.query.get(1)
        for campo, valor in SETTINGS_ORIGINAIS.items():
            setattr(s, campo, valor)
        db.session.commit()


CENARIOS = [c1, c2, c3, c4, c5, c6, c7, c8, c10, c9, c11, c13, c14, c15, c16, c17, c12]

try:
    for fn in CENARIOS:
        fn()
finally:
    try:
        limpar()
        check("18.1 limpeza", True)
    except Exception as exc:  # noqa: BLE001
        check("18.1 limpeza", False, f"{type(exc).__name__}: {exc}"[:200])
    check("18.2 nenhuma conexão externa escapou", not _ESCAPES, str(_ESCAPES[:5]))

ok = sum(1 for r in resultados if r[1] == "OK")
falha = sum(1 for r in resultados if r[1] == "FALHA")
bloq = sum(1 for r in resultados if r[1] == "BLOQUEADO")
print(f"\n{ok} OK · {falha} FALHA · {bloq} BLOQUEADO (de {len(resultados)})")
sys.exit(1 if (falha or bloq) else 0)
