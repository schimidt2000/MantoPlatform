"""Verificação da feature 323 — a nota pedida chega ao Superadmin.

Cenários (spec §Verificação):
 1. Criar evento com nota: nasce a nota a emitir com valor, "pedida por" e data.
 2. Ligar o chip no "Editar tudo": nasce a nota a emitir.                 (DEVE falhar no código antigo)
 3. Ligar o chip no card Comercial: nasce a nota a emitir.                (DEVE falhar no código antigo)
 4. Salvar de novo com o chip ligado: nenhuma nota nova, nenhum e-mail novo.
 5. Dados da nota gravados; documento completa o cliente só se vazio; em branco vale o do cadastro.
 6. ISS retido sem município: 400 com `fields.nota_municipio` (e documento inválido também).
 7. Painel do Superadmin: nota listada, com discriminação na ordem do FR-008.
 8. Comercial, Financeiro e Superadmin com "Ver como": sem o painel.      (DEVE falhar se vazar)
 9. Inserir o PDF pela porta existente: nota emitida, fora do painel.
10. E-mail do pedido: um por Superadmin com e-mail, assunto no formato do FR-012.
11. Desligar o chip: a emitir excluída, emitida preservada.
12. Valor da venda muda: a nota única a emitir acompanha, sem e-mail; corpo sem `nota` não apaga.
13. "Editar tudo" que troca o contratante: o documento completa o NOVO cliente, não o antigo.  (converge)
14. Venda sem chip com nota lançada à mão: salvar a venda não apaga a nota.             (converge)
15. Limpeza.

Google DUBLADO (Agenda no-op). E-mail: `_send` trocado por coletor e `send_async` síncrono — nada
sai. Requisições HTTP FORA do `app_context`; toda asserção de escrita lê por conexão separada.
`VERIFY_323_HTML=<arquivo>` grava o HTML do e-mail do cenário 10.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
    C:\\Users\\schim\\Desktop\\Manto_Platform\\.venv\\Scripts\\python.exe specs\\323-nota-pedida-ao-superadmin\\verify_323.py
"""
from __future__ import annotations

import io
import os
import sys
import traceback
import uuid
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, email_service, limiter, maps  # noqa: E402
from app.calendar import routes as cal_routes  # noqa: E402
from app.calendar import service as cal_service  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import CalendarEvent, Client, Role, User  # noqa: E402

PREFIX = "__v323_"
SENHA = "verify-323-senha"
VALOR = 2127.98

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
enviados: list[dict] = []
_externo = create_engine(os.environ["DATABASE_URL"], future=True)

# ── dublês ──────────────────────────────────────────────────────────────────────────────────────
maps.cidade_do_endereco = lambda _e: (None, None)
cal_routes._fetch_travel_data = lambda _ev, _s: {}
cal_service.insert_event = lambda *a, **k: {"id": f"{PREFIX}g{uuid.uuid4().hex[:10]}"}
cal_service.update_event = lambda *a, **k: None
cal_service.delete_event = lambda *a, **k: None
cal_routes.insert_event = cal_service.insert_event


def _coletor(to: str, subject: str, body: str = "", html: str = "") -> bool:
    # Só os e-mails desta feature contam; convite e outros avisos do fluxo passam batido.
    if subject.startswith("Nota "):
        enviados.append({"to": to, "subject": subject, "html": html})
    return True


def _sincrono(fn, *args) -> None:
    fn(*args)


email_service._send = _coletor
email_service.send_async = _sincrono


def _no_banco(sql: str, **params):
    with _externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001
        with app.app_context():
            db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


# ── preparação ──────────────────────────────────────────────────────────────────────────────────

def _usuario(sufixo: str, nome: str, *papeis: str) -> int:
    user = User(name=nome, email=f"{PREFIX}{sufixo}@manto.local", is_active=True, has_access=True)
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


def _cliente_cadastro(sufixo: str, *, cnpj: str | None) -> int:
    cli = Client(
        name=f"{PREFIX}{sufixo}", company=f"{PREFIX}Esporte Clube {sufixo}",
        phone=f"119{uuid.uuid4().int % 10**8:08d}", email=f"{PREFIX}{sufixo}@cliente.local",
        address="Av. Indianópolis, 1192 — São Paulo", cnpj=cnpj,
    )
    db.session.add(cli)
    db.session.commit()
    return cli.id


def _corpo_criacao(titulo: str, *, dias: int, nota: bool, cliente_id: int | None = None, extra: dict | None = None) -> dict:
    d = (now_sp().date() + timedelta(days=dias)).isoformat()
    corpo = {
        "title": f"{PREFIX}{titulo}", "event_type": "R&I", "date": d, "start": "15:00", "end": "17:00",
        "location": f"{PREFIX}Buffet, São Paulo", "description": "", "needs_rehearsal": False,
        "sale_value": VALOR, "sale_value_gross": VALOR, "transport_value": 0, "acrescimo_value": 0,
        "with_invoice": nota, "is_cortesia_permuta": False, "seller_id": estado["com"], "sale_date": None,
        "payment_method": None, "payment_installments": None, "payment_due_date": None,
        "duracao": "2", "characters": [], "orc_caches": [], "acrescimos": [], "observations": [],
        "clients": [{"client_id": cliente_id, "relation": "Contratante"}] if cliente_id else [],
    }
    corpo.update(extra or {})
    return corpo


def _criar(chave: str, corpo: dict) -> int:
    r = _cliente_http(chave).post("/api/events", json=corpo)
    _garante(r.status_code == 201, f"POST /api/events → {r.status_code} {r.get_data(as_text=True)[:300]}")
    j = r.get_json()
    return j["event"]["id"] if "event" in j else j["id"]


def _corpo_edicao(eid: int, **troca) -> dict:
    with app.app_context():
        ev = CalendarEvent.query.get(eid)
        corpo = {
            "title": ev.title, "event_type": ev.event_type, "date": ev.start_at.date().isoformat(),
            "start": ev.start_at.strftime("%H:%M"), "end": ev.end_at.strftime("%H:%M"),
            "location": ev.location or "", "description": ev.description or "",
            "needs_rehearsal": bool(ev.needs_rehearsal),
            "sale_value": float(ev.sale_value) if ev.sale_value is not None else None,
            "sale_value_gross": float(ev.sale_value_gross) if ev.sale_value_gross is not None else None,
            "transport_value": float(ev.transport_value or 0), "acrescimo_value": float(ev.acrescimo_value or 0),
            "with_invoice": bool(ev.with_invoice), "is_cortesia_permuta": bool(ev.is_cortesia_permuta),
            "seller_id": ev.seller_id, "sale_date": ev.sale_date.isoformat() if ev.sale_date else None,
            "payment_method": ev.payment_method, "payment_installments": ev.payment_installments,
            "payment_due_date": ev.payment_due_date.isoformat() if ev.payment_due_date else None,
            "characters": [],
            "clients": [{"client_id": ec.client_id, "relation": ec.relationship_type} for ec in ev.event_clients],
        }
    corpo.update(troca)
    return corpo


def _corpo_comercial(eid: int, **troca) -> dict:
    with app.app_context():
        ev = CalendarEvent.query.get(eid)
        corpo = {
            "sale_value": float(ev.sale_value) if ev.sale_value is not None else None,
            "sale_value_gross": float(ev.sale_value_gross) if ev.sale_value_gross is not None else None,
            "transport_value": float(ev.transport_value or 0), "with_invoice": bool(ev.with_invoice),
            "is_cortesia_permuta": False, "seller_id": ev.seller_id,
            "sale_date": ev.sale_date.isoformat() if ev.sale_date else None,
            "commission_rate": None, "payment_method": ev.payment_method,
            "payment_installments": ev.payment_installments,
            "payment_due_date": ev.payment_due_date.isoformat() if ev.payment_due_date else None,
        }
    corpo.update(troca)
    return corpo


def _patch(chave: str, url: str, corpo: dict, esperado: int = 200):
    r = _cliente_http(chave).patch(url, json=corpo)
    _garante(r.status_code == esperado, f"PATCH {url} ({chave}) → {r.status_code} {r.get_data(as_text=True)[:300]}")
    return r


def _notas(eid: int) -> list:
    return _no_banco(
        "SELECT id, amount, status, file, pedida_por_id, pedida_em, aviso_enviado_em "
        "FROM event_invoices WHERE event_id = :i ORDER BY id",
        i=eid,
    )


def _painel(chave: str):
    r = _cliente_http(chave).get("/api/dashboard")
    _garante(r.status_code == 200, f"GET /api/dashboard ({chave}) → {r.status_code}")
    return r.get_json().get("notas_a_emitir")


def _item_do_painel(eid: int) -> dict:
    bloco = _painel("sa")
    _garante(bloco is not None, "Superadmin sem o bloco notas_a_emitir")
    itens = [i for i in bloco["itens"] if i["event_id"] == eid]
    _garante(len(itens) == 1, f"evento {eid}: {len(itens)} item(ns) no painel")
    return itens[0]


def limpar() -> None:
    ids = [r[0] for r in _no_banco("SELECT id FROM calendar_events WHERE title LIKE :p OR google_event_id LIKE :p", p=f"%{PREFIX}%")]
    for eid in ids:
        for tabela in ("commission_payments", "event_logs", "event_roles", "event_clients", "event_invoices"):
            db.session.execute(text(f"DELETE FROM {tabela} WHERE event_id = :i"), {"i": eid})
    db.session.commit()
    for eid in ids:
        ev = CalendarEvent.query.get(eid)
        if ev is not None:
            db.session.delete(ev)
    db.session.commit()
    for cli in Client.query.filter(Client.name.like(f"{PREFIX}%")).all():
        db.session.delete(cli)
    db.session.commit()
    for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        u.roles.clear()
        db.session.delete(u)
    db.session.commit()


def preparar() -> None:
    with app.app_context():
        limpar()
        estado["sa"] = _usuario("sa", f"{PREFIX}Super", RoleName.SUPERADMIN)
        estado["com"] = _usuario("com", "Thaís Verify", RoleName.COMERCIAL)
        estado["fin"] = _usuario("fin", f"{PREFIX}Fin", RoleName.FINANCEIRO)
        estado["cli_sem"] = _cliente_cadastro("SemDoc", cnpj=None)
        estado["cli_com"] = _cliente_cadastro("ComDoc", cnpj="61.006.839/0001-21")
        estado["superadmins"] = User.query.join(User.roles).filter(
            Role.name == RoleName.SUPERADMIN, User.is_active.is_(True), User.email.isnot(None)
        ).distinct().count()


# ───────────────────────────── História 1 — o pedido em toda porta ─────────────────────────────

def cen_01_criacao() -> None:
    enviados.clear()
    eid = _criar("com", _corpo_criacao("criacao", dias=60, nota=True, cliente_id=estado["cli_com"]))
    estado["ev_criacao"] = eid
    notas = _notas(eid)
    _garante(len(notas) == 1 and notas[0].status == "a_emitir", f"notas: {notas}")
    _garante(float(notas[0].amount) == VALOR, f"valor {notas[0].amount}")
    _garante(notas[0].pedida_por_id == estado["com"], f"pedida_por {notas[0].pedida_por_id}")
    _garante(notas[0].pedida_em is not None, "sem pedida_em")


def cen_02_editar_tudo() -> None:
    eid = _criar("com", _corpo_criacao("editar-tudo", dias=61, nota=False, cliente_id=estado["cli_com"]))
    estado["ev_edit"] = eid
    _garante(_notas(eid) == [], "nasceu nota sem o chip")
    _patch("com", f"/api/events/{eid}", _corpo_edicao(eid, with_invoice=True))
    notas = _notas(eid)
    _garante(len(notas) == 1 and notas[0].status == "a_emitir", f"Editar tudo não pediu a nota: {notas}")
    _garante(notas[0].pedida_por_id == estado["com"], "sem pedida_por")


def cen_03_card_comercial() -> None:
    eid = _criar("com", _corpo_criacao("comercial", dias=62, nota=False, cliente_id=estado["cli_sem"]))
    estado["ev_com"] = eid
    _patch("com", f"/api/events/{eid}/comercial", _corpo_comercial(eid, with_invoice=True))
    notas = _notas(eid)
    _garante(len(notas) == 1 and notas[0].status == "a_emitir", f"card Comercial não pediu a nota: {notas}")


def cen_04_salvar_de_novo() -> None:
    eid = estado["ev_edit"]
    enviados.clear()
    _patch("com", f"/api/events/{eid}", _corpo_edicao(eid))
    _patch("com", f"/api/events/{eid}/comercial", _corpo_comercial(eid))
    _garante(len(_notas(eid)) == 1, f"nota a mais: {_notas(eid)}")
    _garante(enviados == [], f"e-mail novo ao salvar de novo: {[e['subject'] for e in enviados]}")


# ───────────────────────────── História 2 — os dados da nota ─────────────────────────────

NOTA_JUNDIAI = {
    "tomador_doc": "16.643.750/0001-11", "iss_retido": True, "municipio": "Jundiaí - SP",
    "referencia": "AF 618/2026", "observacoes": "Informar o número do pedido.",
}


def cen_05_dados_da_nota() -> None:
    eid = estado["ev_com"]
    _patch("com", f"/api/events/{eid}/comercial", _corpo_comercial(eid, nota=NOTA_JUNDIAI))
    linha = _no_banco(
        "SELECT nota_tomador_doc, nota_iss_retido, nota_municipio, nota_referencia, nota_observacoes "
        "FROM calendar_events WHERE id = :i", i=eid,
    )[0]
    _garante(tuple(linha) == ("16643750000111", True, "Jundiaí - SP", "AF 618/2026", "Informar o número do pedido."),
             f"dados gravados: {tuple(linha)}")
    cnpj_cli = _no_banco("SELECT cnpj FROM clients WHERE id = :i", i=estado["cli_sem"])[0][0]
    _garante(cnpj_cli == "16.643.750/0001-11", f"cliente sem CNPJ não foi completado: {cnpj_cli!r}")
    # Cliente COM CNPJ: documento diferente na venda não sobrescreve o cadastro; em branco vale o dele.
    eid2 = estado["ev_edit"]
    _patch("com", f"/api/events/{eid2}/comercial", _corpo_comercial(eid2, nota={"tomador_doc": "11.222.333/0001-81"}))
    cnpj_cli2 = _no_banco("SELECT cnpj FROM clients WHERE id = :i", i=estado["cli_com"])[0][0]
    _garante(cnpj_cli2 == "61.006.839/0001-21", f"cadastro sobrescrito: {cnpj_cli2!r}")
    _patch("com", f"/api/events/{eid2}/comercial", _corpo_comercial(eid2, nota={"tomador_doc": ""}))
    r = _cliente_http("com").get(f"/api/events/{eid2}")
    nota = r.get_json()["venda"].get("nota")
    _garante(nota is not None and nota["tomador_doc"] is None and nota["doc_do_cliente"] == "61006839000121",
             f"venda.nota: {nota}")
    _garante(_item_do_painel(eid2)["tomador"]["doc"] == "61006839000121", "painel não usou o CNPJ do cadastro")


def cen_06_validacao() -> None:
    eid = estado["ev_com"]
    r = _patch("com", f"/api/events/{eid}/comercial",
               _corpo_comercial(eid, nota={"iss_retido": True, "municipio": ""}), esperado=400)
    campos = r.get_json()["error"].get("fields") or {}
    _garante("nota_municipio" in campos, f"fields: {campos}")
    r = _patch("com", f"/api/events/{eid}", _corpo_edicao(eid, nota={"tomador_doc": "123"}), esperado=400)
    _garante("nota_tomador_doc" in (r.get_json()["error"].get("fields") or {}), "documento curto aceito")
    corpo = _corpo_criacao("invalida", dias=63, nota=True, extra={"nota": {"iss_retido": True}})
    r = _cliente_http("com").post("/api/events", json=corpo)
    _garante(r.status_code == 400, f"criação inválida → {r.status_code}")
    _garante(_no_banco("SELECT 1 FROM calendar_events WHERE title = :t", t=f"{PREFIX}invalida") == [],
             "evento criado apesar do erro")


# ───────────────────────────── História 3 — o painel ─────────────────────────────

def cen_07_painel() -> None:
    eid = estado["ev_com"]
    with app.app_context():
        ev = CalendarEvent.query.get(eid)
        ev.payment_method = "faturado"
        ev.payment_due_date = ev.start_at.date() + timedelta(days=6)
        db.session.commit()
        venc = ev.payment_due_date.strftime("%d/%m")
        dia = ev.start_at.strftime("%d/%m")
    item = _item_do_painel(eid)
    _garante(item["amount"] == VALOR, f"valor {item['amount']}")
    _garante(item["pedida_por"] == "Thaís Verify", f"pedida_por {item['pedida_por']}")
    _garante(item["iss_retido"] is True and item["municipio"] == "Jundiaí - SP", "ISS/município")
    linhas = item["discriminacao"].split("\n")
    esperado_inicio = ["AF 618/2026", f"Personagens para evento {dia}", f"Vencimento: {venc}",
                       "Esses são os dados da minha conta no Inter:", "INTER - 077"]
    _garante(linhas[:5] == esperado_inicio, f"discriminação: {linhas[:5]}")
    _garante(linhas[-1] == "Informar o número do pedido.", f"última linha: {linhas[-1]!r}")
    _garante("CNPJ: 60.708.296/0001-21 (PIX)" in linhas, "sem o CNPJ da conta")


def cen_08_rbac() -> None:
    _garante(_painel("com") is None, "Comercial recebeu o painel")
    _garante(_painel("fin") is None, "Financeiro recebeu o painel")
    c = _cliente_http("sa")
    r = c.post("/api/auth/impersonate", json={"role": "COMERCIAL"})
    _garante(r.status_code == 200, f"impersonate → {r.status_code}")
    r = c.get("/api/dashboard")
    _garante(r.get_json().get("notas_a_emitir") is None, "Ver como Comercial recebeu o painel")


def cen_09_inserir_pdf() -> None:
    eid = estado["ev_criacao"]
    nota = _notas(eid)[0]
    hoje = now_sp().date().isoformat()
    r = _cliente_http("sa").patch(
        f"/api/events/{eid}/invoices/{nota.id}",
        data={"amount": str(VALOR), "issue_date": hoje,
              "file": (io.BytesIO(b"%PDF-1.4 verify 323"), "NFSe_verify.pdf")},
        content_type="multipart/form-data",
    )
    _garante(r.status_code == 200, f"PATCH invoice → {r.status_code} {r.get_data(as_text=True)[:200]}")
    depois = _notas(eid)[0]
    _garante(depois.status == "emitida" and depois.file, f"nota: {depois}")
    _garante(float(depois.amount) == VALOR, "valor apagado ao inserir o PDF")
    bloco = _painel("sa")
    _garante(all(i["event_id"] != eid for i in bloco["itens"]), "nota emitida continua no painel")


# ───────────────────────────── História 4 — o e-mail ─────────────────────────────

def cen_10_email() -> None:
    enviados.clear()
    eid = _criar("com", _corpo_criacao("email", dias=64, nota=True, cliente_id=estado["cli_com"],
                                       extra={"nota": {"referencia": "PO 77"}}))
    estado["ev_email"] = eid
    _garante(estado["superadmins"] >= 1, "nenhum Superadmin com e-mail no espelho")
    _garante(len(enviados) == estado["superadmins"],
             f"{len(enviados)} e-mail(s) para {estado['superadmins']} Superadmin(s)")
    assunto = enviados[0]["subject"]
    _garante(assunto.startswith("Nota R$ 2.127,98 · ") and assunto.endswith(" · pedida por Thaís"), f"assunto: {assunto!r}")
    _garante(f"{PREFIX}Esporte Clube ComDoc"[:20] in assunto, f"tomador fora do assunto: {assunto!r}")
    _garante("PO 77" in enviados[0]["html"], "discriminação fora do corpo")
    _garante(_notas(eid)[0].aviso_enviado_em is not None, "aviso_enviado_em não gravado")
    destino = os.environ.get("VERIFY_323_HTML")
    if destino:
        Path(destino).write_text(enviados[0]["html"], encoding="utf-8")


def cen_11_desligar() -> None:
    eid = estado["ev_criacao"]  # tem a nota emitida do cenário 9
    with app.app_context():
        from app.models import EventInvoice
        db.session.add(EventInvoice(event_id=eid, amount=100, status="a_emitir"))
        db.session.commit()
    _garante(len(_notas(eid)) == 2, "preparo: duas notas")
    _patch("com", f"/api/events/{eid}/comercial", _corpo_comercial(eid, with_invoice=False))
    notas = _notas(eid)
    _garante([n.status for n in notas] == ["emitida"], f"depois de desligar: {[n.status for n in notas]}")
    # Desligar e religar a venda SEM nota emitida: pedido novo, aviso novo.
    eid2 = estado["ev_email"]
    _patch("com", f"/api/events/{eid2}/comercial", _corpo_comercial(eid2, with_invoice=False))
    _garante(_notas(eid2) == [], "a emitir não foi excluída")
    enviados.clear()
    _patch("com", f"/api/events/{eid2}/comercial", _corpo_comercial(eid2, with_invoice=True))
    _garante(len(_notas(eid2)) == 1 and len(enviados) == estado["superadmins"], "religar não pediu de novo")


def cen_12_valor_acompanha() -> None:
    eid = estado["ev_com"]
    enviados.clear()
    _patch("com", f"/api/events/{eid}/comercial", _corpo_comercial(eid, sale_value=3000, sale_value_gross=3000))
    notas = _notas(eid)
    _garante(len(notas) == 1 and float(notas[0].amount) == 3000, f"valor não acompanhou: {notas}")
    _garante(enviados == [], "e-mail ao mudar o valor")
    ref = _no_banco("SELECT nota_referencia FROM calendar_events WHERE id = :i", i=eid)[0][0]
    _garante(ref == "AF 618/2026", f"corpo sem `nota` apagou os dados: {ref!r}")


def cen_13_troca_de_contratante() -> None:
    with app.app_context():
        estado["cli_novo"] = _cliente_cadastro("Novo", cnpj=None)
    eid = _criar("com", _corpo_criacao("troca", dias=65, nota=True, cliente_id=estado["cli_sem"]))
    antes = _no_banco("SELECT cnpj FROM clients WHERE id = :i", i=estado["cli_sem"])[0][0]
    corpo = _corpo_edicao(eid, clients=[{"client_id": estado["cli_novo"], "relation": "Contratante"}],
                          nota={"tomador_doc": "44.679.207/0001-00"})
    _patch("com", f"/api/events/{eid}", corpo)
    novo = _no_banco("SELECT cnpj FROM clients WHERE id = :i", i=estado["cli_novo"])[0][0]
    depois = _no_banco("SELECT cnpj FROM clients WHERE id = :i", i=estado["cli_sem"])[0][0]
    _garante(novo == "44.679.207/0001-00", f"novo contratante não completado: {novo!r}")
    _garante(depois == antes, f"contratante antigo alterado: {antes!r} → {depois!r}")


def cen_14_nota_a_mao_sobrevive() -> None:
    eid = _criar("com", _corpo_criacao("a-mao", dias=66, nota=False, cliente_id=estado["cli_com"]))
    r = _cliente_http("fin").post(f"/api/events/{eid}/invoices", data={"amount": "500"},
                                  content_type="multipart/form-data")
    _garante(r.status_code == 201, f"POST invoices (fin) → {r.status_code}")
    _patch("com", f"/api/events/{eid}/comercial", _corpo_comercial(eid))
    _patch("com", f"/api/events/{eid}", _corpo_edicao(eid))
    notas = _notas(eid)
    _garante(len(notas) == 1 and notas[0].status == "a_emitir", f"nota lançada à mão sumiu: {notas}")


def cen_15_limpeza() -> None:
    with app.app_context():
        limpar()
        _garante(CalendarEvent.query.filter(CalendarEvent.title.like(f"{PREFIX}%")).count() == 0, "evento sobrou")
        _garante(Client.query.filter(Client.name.like(f"{PREFIX}%")).count() == 0, "cliente sobrou")
        _garante(User.query.filter(User.email.like(f"{PREFIX}%")).count() == 0, "usuário sobrou")


def main() -> int:
    print("Feature 323 — a nota pedida chega ao Superadmin")
    preparar()
    passos = [
        ("1. criação com nota: a emitir, pedida por, data", cen_01_criacao),
        ("2. Editar tudo pede a nota (DEVE falhar no antigo)", cen_02_editar_tudo),
        ("3. card Comercial pede a nota (DEVE falhar no antigo)", cen_03_card_comercial),
        ("4. salvar de novo: nenhuma nota nem e-mail novo", cen_04_salvar_de_novo),
        ("5. dados da nota gravados; cliente completado só se vazio", cen_05_dados_da_nota),
        ("6. validação: município com ISS retido, documento", cen_06_validacao),
        ("7. painel do Superadmin com discriminação na ordem", cen_07_painel),
        ("8. Comercial, Financeiro e Ver como sem o painel (DEVE falhar se vazar)", cen_08_rbac),
        ("9. inserir o PDF emite e tira do painel", cen_09_inserir_pdf),
        ("10. e-mail por Superadmin, assunto do FR-012", cen_10_email),
        ("11. desligar exclui a emitir, preserva emitida; religar pede de novo", cen_11_desligar),
        ("12. valor acompanha a nota única; corpo sem nota não apaga", cen_12_valor_acompanha),
        ("13. Editar tudo com contratante trocado completa o novo cliente", cen_13_troca_de_contratante),
        ("14. nota lançada à mão sobrevive à venda sem chip", cen_14_nota_a_mao_sobrevive),
    ]
    try:
        for nome, fn in passos:
            cenario(nome, fn)
    finally:
        cenario("15. limpeza", cen_15_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  ✗ {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
