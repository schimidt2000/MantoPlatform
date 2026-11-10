"""Verificação da feature 342 — o pedido de nota já nasce com os dados que a emissão exige.

Cenários (spec §Verificação):
 1. Schema público dos dois formulários traz as perguntas da nota, com a condição.
 2. Envio sem pedir nota, com lixo nos campos da nota: 201 e os valores são descartados.
 3. Envio pedindo nota sem documento: 400 no campo.                         (DEVE falhar)
 4. Envio pedindo nota com CNPJ de dígito errado: 400.                      (DEVE falhar)
 5. ISS só para CNPJ: com CPF passa sem responder; com CNPJ sem responder, 400. (DEVE falhar a 2ª)
 6. Ligar formulário com nota a evento vazio: documento, e-mail, referência e ISS chegam.
 7. Ligar a evento com documento digitado: o digitado fica; os vazios completam.
 8. Ligar formulário sem nota: nenhum `nota_*` muda.
 9. "Não sei": `nota_iss_retido` segue nulo; o detalhe mostra a resposta.
10. Depois de ligar: `with_invoice` igual e nenhuma nota a emitir criada.
11. Card Comercial: ligar a nota sem documento em lugar nenhum: 400; banco igual. (DEVE falhar)
12. Idem com documento no cadastro da contratante: 200.
13. Documento com dígito errado na venda: 400.                              (DEVE falhar)
14. Pedido antigo sem documento: salvar outra coisa passa; apagar documento existente não.
15. Criação e "Editar tudo" ligando a nota sem documento: 400 nas duas.     (DEVE falhar)
16. Sugestão de município: funções puras e o detalhe do evento.
17. Município gravado sem ISS retido; painel mostra município, sugestão e e-mail da nota.
18. Editor: condição válida grava; inválida 400; Comercial 403.             (DEVE falhar)
19. Limpeza.

Google DUBLADO (Agenda no-op); e-mail coletado, nada sai. Requisições HTTP FORA do `app_context`;
toda asserção de escrita lê por conexão separada.

Rodar contra o espelho da feature (PowerShell, na raiz do worktree)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
    C:\\Users\\schim\\Desktop\\Manto_Platform\\.venv\\Scripts\\python.exe specs\\342-nota-nasce-com-dados\\verify_342.py
"""
from __future__ import annotations

import json
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
from app.models import (  # noqa: E402
    CalendarEvent,
    Client,
    FormFieldDefinition,
    FormResponse,
    Role,
    User,
)

PREFIX = "__v342_"
SENHA = "verify-342-senha"
VALOR = 1800.0
CNPJ_OK = "11.222.333/0001-81"
CNPJ_OK_DIGITOS = "11222333000181"
CNPJ_RUIM = "11.222.333/0001-80"
CNPJ_DIGITADO = "61.006.839/0001-21"
CPF_OK = "529.982.247-25"
DATA_FORM = "2031-03-15"  # longe: nenhum evento real nessa data, o vínculo automático não age
NOTA_COLS = "nota_tomador_doc, nota_email, nota_iss_retido, nota_referencia, nota_municipio, with_invoice"

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_externo = create_engine(os.environ["DATABASE_URL"], future=True)

# ── dublês ──────────────────────────────────────────────────────────────────────────────────────
maps.cidade_do_endereco = lambda _e: (None, None)
cal_routes._fetch_travel_data = lambda _ev, _s: {}
cal_service.insert_event = lambda *a, **k: {"id": f"{PREFIX}g{uuid.uuid4().hex[:10]}"}
cal_service.update_event = lambda *a, **k: None
cal_service.delete_event = lambda *a, **k: None
cal_routes.insert_event = cal_service.insert_event
email_service._send = lambda *a, **k: True
email_service.send_async = lambda fn, *args: None


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
        name=f"{PREFIX}{sufixo}", company=f"{PREFIX}Empresa {sufixo}",
        phone=f"119{uuid.uuid4().int % 10**8:08d}", email=f"{PREFIX}{sufixo}@cliente.local",
        address="Av. Indianópolis, 1192 — São Paulo", cnpj=cnpj,
    )
    db.session.add(cli)
    db.session.commit()
    return cli.id


def _corpo_criacao(titulo: str, *, dias: int, nota: bool, cliente_id: int | None = None,
                   local: str | None = None, extra: dict | None = None) -> dict:
    d = (now_sp().date() + timedelta(days=dias)).isoformat()
    corpo = {
        "title": f"{PREFIX}{titulo}", "event_type": "R&I", "date": d, "start": "15:00", "end": "17:00",
        "location": local or f"{PREFIX}Buffet, São Paulo", "description": "", "needs_rehearsal": False,
        "sale_value": VALOR, "sale_value_gross": VALOR, "transport_value": 0, "acrescimo_value": 0,
        "with_invoice": nota, "is_cortesia_permuta": False, "seller_id": estado["com"], "sale_date": None,
        "payment_method": None, "payment_installments": None, "payment_due_date": None,
        "duracao": "2", "characters": [], "orc_caches": [], "acrescimos": [], "observations": [],
        "clients": [{"client_id": cliente_id, "relation": "Contratante"}] if cliente_id else [],
    }
    corpo.update(extra or {})
    return corpo


def _criar(corpo: dict, esperado: int = 201):
    r = _cliente_http("com").post("/api/events", json=corpo)
    _garante(r.status_code == esperado, f"POST /api/events → {r.status_code} {r.get_data(as_text=True)[:300]}")
    if esperado != 201:
        return r
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


def _nota_do_evento(eid: int):
    return _no_banco(f"SELECT {NOTA_COLS} FROM calendar_events WHERE id = :i", i=eid)[0]


def _detalhe_nota(eid: int) -> dict:
    r = _cliente_http("com").get(f"/api/events/{eid}")
    _garante(r.status_code == 200, f"GET evento → {r.status_code}")
    nota = r.get_json()["venda"].get("nota")
    _garante(nota is not None, "detalhe sem venda.nota")
    return nota


# ── formulário público ──────────────────────────────────────────────────────────────────────────

_VALOR_POR_TIPO = {
    "texto_curto": "Teste", "texto_longo": "Teste", "hora": "15:00", "cpf": CPF_OK,
    "cnpj": CNPJ_OK, "cep": "01310-100", "cpf_cnpj": CNPJ_OK,
}


def _corpo_form(form_type: str, **nota) -> dict:
    """Todos os obrigatórios SEM condição preenchidos; `nota` entra por cima (chaves do formulário)."""
    with app.app_context():
        campos = (
            FormFieldDefinition.query.filter_by(form_type=form_type)
            .order_by(FormFieldDefinition.order).all()
        )
        corpo: dict[str, str] = {}
        for c in campos:
            if not c.required or c.show_if_key:
                continue
            if c.field_type == "telefone":
                corpo[f"{c.field_key}_ddi"] = "+55"
                corpo[f"{c.field_key}_national"] = f"(11) 9{uuid.uuid4().int % 10**8:08d}"
            elif c.field_type == "selecao":
                corpo[c.field_key] = c.options_list[0]
            elif c.field_type == "data":
                corpo[c.field_key] = DATA_FORM
            elif c.field_type == "email":
                corpo[c.field_key] = f"{PREFIX}contato@cliente.local"
            else:
                corpo[c.field_key] = _VALOR_POR_TIPO.get(c.field_type, "Teste")
    nome_key = "razao_social" if form_type == "corporativo" else "nome_contratante"
    corpo[nome_key] = f"{PREFIX}{uuid.uuid4().hex[:8]}"
    if form_type == "comum":
        corpo.update(cidade="Sorocaba", estado="SP")
    corpo.update(nota)
    return corpo


def _enviar(form_type: str, esperado: int = 201, **nota):
    corpo = _corpo_form(form_type, **nota)
    r = app.test_client().post(f"/api/formularios/{form_type}", data=corpo)
    _garante(r.status_code == esperado, f"POST formulário {form_type} → {r.status_code} {r.get_data(as_text=True)[:300]}")
    if esperado != 201:
        return r
    nome = corpo["razao_social" if form_type == "corporativo" else "nome_contratante"]
    return _no_banco("SELECT id FROM form_responses WHERE contact_name = :n", n=nome)[0][0]


def _valores_da_resposta(rid: int) -> dict[str, str]:
    bruto = _no_banco("SELECT data FROM form_responses WHERE id = :i", i=rid)[0][0]
    return {c[0]: c[2] for secao in json.loads(bruto) for c in secao["campos"] if len(c) == 3}


def _ligar(rid: int, eid: int, esperado: int = 200) -> None:
    r = _cliente_http("com").post(f"/api/formularios/respostas/{rid}/vincular-evento", json={"event_id": eid})
    _garante(r.status_code == esperado, f"vincular {rid}→{eid}: {r.status_code} {r.get_data(as_text=True)[:300]}")


NOTA_CNPJ = {
    "precisa_nota": "Sim", "nota_doc": CNPJ_OK, "nota_email": f"{PREFIX}nf@cliente.local",
    "nota_iss": "Sim", "nota_referencia": "OC 4411",
}


def limpar() -> None:
    rids = [r[0] for r in _no_banco("SELECT id FROM form_responses WHERE contact_name LIKE :p", p=f"{PREFIX}%")]
    for rid in rids:
        db.session.execute(text("DELETE FROM notifications WHERE entity_type = 'form_response' AND entity_id = :i"), {"i": rid})
        db.session.execute(text("DELETE FROM form_responses WHERE id = :i"), {"i": rid})
    db.session.execute(text("DELETE FROM form_field_definitions WHERE label LIKE :p"), {"p": f"{PREFIX}%"})
    db.session.commit()
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
        db.session.execute(text("DELETE FROM notifications WHERE user_id = :i"), {"i": u.id})
        u.roles.clear()
        db.session.delete(u)
    db.session.commit()


def preparar() -> None:
    with app.app_context():
        limpar()
        estado["sa"] = _usuario("sa", f"{PREFIX}Super", RoleName.SUPERADMIN)
        estado["com"] = _usuario("com", f"{PREFIX}Vendas", RoleName.COMERCIAL)
        estado["cli_sem"] = _cliente_cadastro("SemDoc", cnpj=None)
        estado["cli_com"] = _cliente_cadastro("ComDoc", cnpj=CNPJ_DIGITADO)
        estado["cli_outro"] = _cliente_cadastro("Outro", cnpj=None)


# ───────────────────────────── História 1 — o formulário ─────────────────────────────

def cen_01_schema() -> None:
    for form_type in ("comum", "corporativo"):
        r = app.test_client().get(f"/api/formularios/{form_type}/schema")
        _garante(r.status_code == 200, f"schema {form_type} → {r.status_code}")
        campos = {c["key"]: c for s in r.get_json()["sections"] for c in s["campos"]}
        for chave in ("precisa_nota", "nota_doc", "nota_email", "nota_iss", "nota_referencia"):
            _garante(chave in campos, f"{form_type}: falta {chave}")
        _garante(campos["precisa_nota"].get("show_if") is None, "pergunta-mãe com condição")
        _garante(campos["nota_doc"].get("show_if") == {"key": "precisa_nota", "value": "Sim"},
                 f"condição do documento: {campos['nota_doc'].get('show_if')}")
        _garante(campos["nota_doc"]["type"] == "cpf_cnpj", "tipo do documento")
        _garante(campos["nota_iss"].get("only_for_cnpj_of") == "nota_doc", "ISS sem a regra do CNPJ")
        _garante(campos["nota_iss"]["options"] == ["Não", "Sim", "Não sei"], "opções do ISS")


def cen_02_sem_nota_descarta() -> None:
    rid = _enviar("comum", nota_doc=CNPJ_RUIM, nota_email="lixo", nota_iss="Sim", nota_referencia="X")
    valores = _valores_da_resposta(rid)
    for chave in ("nota_doc", "nota_email", "nota_iss", "nota_referencia"):
        _garante(valores.get(chave) == "", f"{chave} não descartado: {valores.get(chave)!r}")
    _garante(valores.get("precisa_nota") == "", f"precisa_nota: {valores.get('precisa_nota')!r}")
    estado["resp_sem_nota"] = rid


def cen_03_sem_documento() -> None:
    r = _enviar("comum", esperado=400, precisa_nota="Sim", nota_email="a@b.com")
    campos = r.get_json()["error"]["fields"]
    _garante("nota_doc" in campos, f"sem erro no documento: {campos}")
    r = _enviar("comum", esperado=400, precisa_nota="Sim", nota_doc=CPF_OK)
    _garante("nota_email" in r.get_json()["error"]["fields"], "e-mail não exigido")


def cen_04_documento_invalido() -> None:
    r = _enviar("corporativo", esperado=400, **{**NOTA_CNPJ, "nota_doc": CNPJ_RUIM})
    _garante("nota_doc" in r.get_json()["error"]["fields"], "dígito errado passou")
    r = _enviar("corporativo", esperado=400, **{**NOTA_CNPJ, "nota_doc": "123"})
    _garante("nota_doc" in r.get_json()["error"]["fields"], "tamanho errado passou")


def cen_05_iss_so_cnpj() -> None:
    rid = _enviar("comum", precisa_nota="Sim", nota_doc=CPF_OK, nota_email="a@b.com", nota_iss="Sim")
    valores = _valores_da_resposta(rid)
    _garante(valores["nota_iss"] == "", f"ISS guardado para CPF: {valores['nota_iss']!r}")
    _garante(valores["nota_doc"] == CPF_OK and valores["precisa_nota"] == "Sim", f"valores: {valores}")
    estado["resp_cpf"] = rid
    r = _enviar("comum", esperado=400, precisa_nota="Sim", nota_doc=CNPJ_OK, nota_email="a@b.com")
    _garante("nota_iss" in r.get_json()["error"]["fields"], "ISS não exigido para CNPJ")


# ───────────────────────────── História 2 — do formulário para a venda ─────────────────────────────

def cen_06_chega_ao_evento() -> None:
    rid = _enviar("corporativo", **NOTA_CNPJ)
    eid = _criar(_corpo_criacao("vazio", dias=70, nota=False, cliente_id=estado["cli_sem"]))
    estado.update(resp_cnpj=rid, ev_vazio=eid)
    _ligar(rid, eid)
    doc, email, iss, ref, _mun, _wi = _nota_do_evento(eid)
    _garante(doc == CNPJ_OK_DIGITOS, f"documento: {doc!r}")
    _garante(email == NOTA_CNPJ["nota_email"], f"e-mail: {email!r}")
    _garante(iss is True, f"ISS: {iss!r}")
    _garante(ref == "OC 4411", f"referência: {ref!r}")


def cen_07_nao_sobrescreve() -> None:
    # Cliente próprio: o documento digitado completa o cadastro do contratante (regra da 323), e o
    # `cli_sem` precisa seguir sem documento para os cenários 11 a 15.
    eid = _criar(_corpo_criacao("digitado", dias=71, nota=True, cliente_id=estado["cli_outro"], extra={
        "nota": {"tomador_doc": CNPJ_DIGITADO, "iss_retido": False, "municipio": "", "referencia": "", "observacoes": ""},
    }))
    rid = _enviar("corporativo", **NOTA_CNPJ)
    _ligar(rid, eid)
    doc, email, iss, ref, _mun, _wi = _nota_do_evento(eid)
    _garante(doc == "61006839000121", f"documento digitado trocado: {doc!r}")
    _garante(iss is False, f"ISS que a vendedora salvou foi trocado: {iss!r}")
    _garante(email == NOTA_CNPJ["nota_email"] and ref == "OC 4411", f"vazios não completaram: {email!r} {ref!r}")
    estado["ev_digitado"] = eid


def cen_08_sem_nota_nao_muda() -> None:
    eid = _criar(_corpo_criacao("intocado", dias=72, nota=False, cliente_id=estado["cli_sem"]))
    antes = _nota_do_evento(eid)
    _ligar(estado["resp_sem_nota"], eid)
    _garante(_nota_do_evento(eid) == antes, f"mudou: {antes} → {_nota_do_evento(eid)}")
    _garante(_detalhe_nota(eid).get("do_formulario") is None, "do_formulario sem pedido de nota")


def cen_09_nao_sei() -> None:
    rid = _enviar("corporativo", **{**NOTA_CNPJ, "nota_iss": "Não sei"})
    eid = _criar(_corpo_criacao("naosei", dias=73, nota=False, cliente_id=estado["cli_sem"]))
    _ligar(rid, eid)
    _garante(_nota_do_evento(eid)[2] is None, f"ISS gravado com 'Não sei': {_nota_do_evento(eid)[2]!r}")
    nota = _detalhe_nota(eid)
    _garante(nota["iss_retido"] is False, "contrato: iss_retido segue booleano")
    form = nota.get("do_formulario") or {}
    _garante(form.get("iss") == "Não sei" and form.get("doc") == CNPJ_OK_DIGITOS, f"do_formulario: {form}")
    _garante(form.get("response_id") == rid, f"response_id: {form}")


def cen_10_nao_liga_o_chip() -> None:
    eid = estado["ev_vazio"]
    _garante(_nota_do_evento(eid)[5] in (False, None), "with_invoice ligou sozinho")
    notas = _no_banco("SELECT count(*) FROM event_invoices WHERE event_id = :i", i=eid)[0][0]
    _garante(notas == 0, f"{notas} nota(s) criada(s) pelo formulário")


# ───────────────────────────── História 3 — documento exigido ─────────────────────────────

NOTA_VAZIA = {"tomador_doc": "", "iss_retido": False, "municipio": "", "referencia": "", "observacoes": ""}


def cen_11_card_sem_documento() -> None:
    eid = _criar(_corpo_criacao("semdoc", dias=74, nota=False, cliente_id=estado["cli_sem"]))
    estado["ev_semdoc"] = eid
    r = _patch("com", f"/api/events/{eid}/comercial",
               _corpo_comercial(eid, with_invoice=True, nota=NOTA_VAZIA), esperado=400)
    campos = r.get_json()["error"]["fields"]
    _garante(campos.get("nota_tomador_doc") == "Informe o CNPJ ou CPF de quem recebe a nota.", f"fields: {campos}")
    _garante(_nota_do_evento(eid)[5] in (False, None), "with_invoice gravado apesar da recusa")
    _garante(_no_banco("SELECT count(*) FROM event_invoices WHERE event_id = :i", i=eid)[0][0] == 0, "nota criada")
    # Corpo sem a chave `nota` (tela antiga) também não deixa o pedido nascer sem documento.
    _patch("com", f"/api/events/{eid}/comercial", _corpo_comercial(eid, with_invoice=True), esperado=400)


def cen_12_documento_do_cadastro() -> None:
    eid = _criar(_corpo_criacao("cadastro", dias=75, nota=False, cliente_id=estado["cli_com"]))
    _patch("com", f"/api/events/{eid}/comercial", _corpo_comercial(eid, with_invoice=True, nota=NOTA_VAZIA))
    _garante(_nota_do_evento(eid)[5] is True, "pedido com documento do cadastro não gravou")
    # E o documento vindo do formulário também basta (o evento 6 recebeu o CNPJ pelo vínculo).
    eid6 = estado["ev_vazio"]
    _patch("com", f"/api/events/{eid6}/comercial", _corpo_comercial(eid6, with_invoice=True))
    _garante(_nota_do_evento(eid6)[5] is True, "documento do formulário não bastou")


def cen_13_digito_errado_na_venda() -> None:
    eid = estado["ev_semdoc"]
    r = _patch("com", f"/api/events/{eid}/comercial",
               _corpo_comercial(eid, with_invoice=True, nota={**NOTA_VAZIA, "tomador_doc": CNPJ_RUIM}), esperado=400)
    _garante(r.get_json()["error"]["fields"].get("nota_tomador_doc") == "CNPJ ou CPF inválido. Confira os números.",
             f"fields: {r.get_json()['error']['fields']}")
    r = _patch("com", f"/api/events/{eid}/comercial",
               _corpo_comercial(eid, with_invoice=True, nota={**NOTA_VAZIA, "tomador_doc": CNPJ_OK, "email": "sem-arroba"}),
               esperado=400)
    _garante("nota_email" in r.get_json()["error"]["fields"], "e-mail inválido passou")


def cen_14_legado_nao_trava() -> None:
    eid = estado["ev_semdoc"]
    # Pedido "antigo": nota ligada sem documento, gravada por fora (como as 12 pendentes de hoje).
    with _externo.begin() as conn:
        conn.execute(text("UPDATE calendar_events SET with_invoice = true WHERE id = :i"), {"i": eid})
    _patch("com", f"/api/events/{eid}", _corpo_edicao(eid, description="mudou", nota=NOTA_VAZIA))
    _patch("com", f"/api/events/{eid}/comercial", _corpo_comercial(eid, nota=NOTA_VAZIA))
    # Mas apagar um documento que existia, sem outro no cadastro, é recusado. O documento entra por
    # fora: pela API ele completaria o cadastro do cliente (323) e deixaria de faltar.
    with _externo.begin() as conn:
        conn.execute(text("UPDATE calendar_events SET nota_tomador_doc = '52998224725' WHERE id = :i"), {"i": eid})
    _patch("com", f"/api/events/{eid}/comercial", _corpo_comercial(eid, nota=NOTA_VAZIA), esperado=400)
    _garante(_nota_do_evento(eid)[0] == "52998224725", "documento apagado apesar da recusa")
    # `email` ausente no corpo não mexe; presente grava (no evento do cenário 7, que tem documento).
    eid7 = estado["ev_digitado"]
    com_doc = {**NOTA_VAZIA, "tomador_doc": CNPJ_DIGITADO}
    _patch("com", f"/api/events/{eid7}/comercial", _corpo_comercial(eid7, nota={**com_doc, "email": "nf@x.com"}))
    _patch("com", f"/api/events/{eid7}/comercial", _corpo_comercial(eid7, nota=com_doc))
    _garante(_nota_do_evento(eid7)[1] == "nf@x.com", f"e-mail apagado por corpo sem a chave: {_nota_do_evento(eid7)[1]!r}")
    _patch("com", f"/api/events/{eid7}/comercial", _corpo_comercial(eid7, nota={**com_doc, "email": ""}))
    _garante(_nota_do_evento(eid7)[1] is None, "e-mail vazio no corpo não apagou")


def cen_15_criacao_e_editar_tudo() -> None:
    _criar(_corpo_criacao("nasce-sem", dias=76, nota=True, cliente_id=estado["cli_sem"], extra={"nota": NOTA_VAZIA}),
           esperado=400)
    _garante(_no_banco("SELECT count(*) FROM calendar_events WHERE title = :t", t=f"{PREFIX}nasce-sem")[0][0] == 0,
             "evento criado apesar da recusa")
    eid = _criar(_corpo_criacao("edita-sem", dias=77, nota=False, cliente_id=estado["cli_sem"]))
    r = _patch("com", f"/api/events/{eid}", _corpo_edicao(eid, with_invoice=True, nota=NOTA_VAZIA), esperado=400)
    _garante("nota_tomador_doc" in r.get_json()["error"]["fields"], "Editar tudo sem o campo")
    # Trocando o contratante para um com documento no mesmo corpo, passa.
    _patch("com", f"/api/events/{eid}", _corpo_edicao(
        eid, with_invoice=True, nota=NOTA_VAZIA, clients=[{"client_id": estado["cli_com"], "relation": "Contratante"}]))


# ───────────────────────────── História 4 — município ─────────────────────────────

def cen_16_sugestao() -> None:
    from app.formularios.nota_do_formulario_ops import municipio_do_endereco

    casos = {
        "Rua das Flores, 120 - Centro, Sorocaba - SP, 18035-000": "Sorocaba - SP",
        "Av. Paulista, 1000 - Bela Vista, São Paulo - SP, 01310-100, Brasil": "São Paulo - SP",
        "Buffet Alegria, Praia Grande/SP": "Praia Grande - SP",
        "Rua X, 10, Jundiaí, SP": "Jundiaí - SP",
        "Buffet Bloco - AB, sem cidade": None,
        "": None,
        None: None,
    }
    for endereco, esperado in casos.items():
        _garante(municipio_do_endereco(endereco) == esperado,
                 f"{endereco!r} → {municipio_do_endereco(endereco)!r}, esperado {esperado!r}")
    eid = _criar(_corpo_criacao("soro", dias=78, nota=False, cliente_id=estado["cli_com"],
                                local="Rua das Flores, 120 - Centro, Sorocaba - SP, 18035-000"))
    estado["ev_soro"] = eid
    _garante(_detalhe_nota(eid).get("municipio_sugerido") == "Sorocaba - SP", f"detalhe: {_detalhe_nota(eid)}")
    # O formulário comum (cidade/estado) vale antes do endereço do evento.
    eid2 = _criar(_corpo_criacao("pelo-form", dias=79, nota=False, cliente_id=estado["cli_sem"], local="Buffet sem cidade"))
    _ligar(estado["resp_cpf"], eid2)
    _garante(_detalhe_nota(eid2).get("municipio_sugerido") == "Sorocaba - SP", "sugestão pelo formulário")


def cen_17_municipio_gravado_e_painel() -> None:
    eid = estado["ev_soro"]
    _garante(_nota_do_evento(eid)[4] is None, "sugestão gravada sem ninguém salvar")
    _patch("com", f"/api/events/{eid}/comercial", _corpo_comercial(
        eid, with_invoice=True, nota={**NOTA_VAZIA, "email": "nf@soro.com"}))
    r = _cliente_http("sa").get("/api/dashboard")
    item = next(i for i in r.get_json()["notas_a_emitir"]["itens"] if i["event_id"] == eid)
    _garante(item["municipio"] is None and item.get("municipio_sugerido") == "Sorocaba - SP", f"painel: {item}")
    _garante(item["tomador"]["email"] == "nf@soro.com", f"e-mail da nota no painel: {item['tomador']}")
    _patch("com", f"/api/events/{eid}/comercial", _corpo_comercial(
        eid, nota={**NOTA_VAZIA, "municipio": "Sorocaba - SP", "email": "nf@soro.com"}))
    _garante(_nota_do_evento(eid)[4] == "Sorocaba - SP", "município sem ISS retido não gravou")
    # A regra da 323 continua: ISS retido sem município é recusado.
    r = _patch("com", f"/api/events/{eid}/comercial", _corpo_comercial(
        eid, nota={**NOTA_VAZIA, "iss_retido": True}), esperado=400)
    _garante("nota_municipio" in r.get_json()["error"]["fields"], "ISS retido sem município passou")


# ───────────────────────────── História 5 — editor ─────────────────────────────

def cen_18_editor() -> None:
    sa, com = _cliente_http("sa"), _cliente_http("com")
    base = {"label": f"{PREFIX}Qual banco?", "section_name": "Pagamento e Observações",
            "field_type": "texto_curto", "required": True}
    r = com.post("/api/formularios/editor/comum/campo", json={**base, "show_if_key": "forma_pagamento", "show_if_value": "Outros"})
    _garante(r.status_code == 403, f"Comercial no editor → {r.status_code}")
    r = sa.post("/api/formularios/editor/comum/campo", json={**base, "show_if_key": "nao_existe", "show_if_value": "x"})
    _garante(r.status_code == 400 and "show_if_key" in r.get_json()["error"]["fields"], f"chave inexistente → {r.status_code}")
    r = sa.post("/api/formularios/editor/comum/campo", json={**base, "show_if_key": "cidade", "show_if_value": "x"})
    _garante(r.status_code == 400, "condição sobre campo de texto aceita")
    r = sa.post("/api/formularios/editor/comum/campo", json={**base, "show_if_key": "forma_pagamento", "show_if_value": ""})
    _garante(r.status_code == 400 and "show_if_value" in r.get_json()["error"]["fields"], "condição sem valor aceita")
    r = sa.post("/api/formularios/editor/comum/campo", json={**base, "show_if_key": "forma_pagamento", "show_if_value": "Outros"})
    _garante(r.status_code in (200, 201), f"criar campo condicional → {r.status_code} {r.get_data(as_text=True)[:200]}")
    linha = _no_banco("SELECT id, field_key, show_if_key, show_if_value FROM form_field_definitions WHERE label = :l", l=base["label"])[0]
    _garante((linha[2], linha[3]) == ("forma_pagamento", "Outros"), f"condição gravada: {linha}")
    # O obrigatório condicional não é exigido com outra forma de pagamento…
    _enviar("comum")
    # …e é exigido quando a condição vale.
    r = _enviar("comum", esperado=400, forma_pagamento="Outros", descreva_outros="permuta")
    _garante(linha[1] in r.get_json()["error"]["fields"], "condicional não exigido com a condição valendo")
    # Limpar a condição pelo PATCH.
    r = sa.patch(f"/api/formularios/editor/campo/{linha[0]}", json={"label": base["label"], "required": False,
                                                                    "show_if_key": "", "show_if_value": ""})
    _garante(r.status_code == 200, f"PATCH campo → {r.status_code}")
    _garante(_no_banco("SELECT show_if_key FROM form_field_definitions WHERE id = :i", i=linha[0])[0][0] is None, "condição não limpou")
    # Campo do sistema: a condição enviada é ignorada.
    id_doc = _no_banco("SELECT id FROM form_field_definitions WHERE form_type='comum' AND field_key='nota_doc'")[0][0]
    rotulo = _no_banco("SELECT label, required FROM form_field_definitions WHERE id = :i", i=id_doc)[0]
    sa.patch(f"/api/formularios/editor/campo/{id_doc}", json={"label": rotulo[0], "required": rotulo[1],
                                                              "help_text": "Com o CNPJ, a gente já encontra a razão social e o endereço.",
                                                              "show_if_key": "", "show_if_value": ""})
    _garante(_no_banco("SELECT show_if_key FROM form_field_definitions WHERE id = :i", i=id_doc)[0][0] == "precisa_nota",
             "condição de campo do sistema alterada pelo editor")


def cen_19_limpeza() -> None:
    with app.app_context():
        limpar()
        _garante(CalendarEvent.query.filter(CalendarEvent.title.like(f"{PREFIX}%")).count() == 0, "evento sobrou")
        _garante(Client.query.filter(Client.name.like(f"{PREFIX}%")).count() == 0, "cliente sobrou")
        _garante(User.query.filter(User.email.like(f"{PREFIX}%")).count() == 0, "usuário sobrou")
        _garante(FormResponse.query.filter(FormResponse.contact_name.like(f"{PREFIX}%")).count() == 0, "resposta sobrou")
        _garante(FormFieldDefinition.query.filter(FormFieldDefinition.label.like(f"{PREFIX}%")).count() == 0, "campo sobrou")


def main() -> int:
    print("Feature 342 — o pedido de nota já nasce com os dados")
    preparar()
    passos = [
        ("1. schema público com as perguntas da nota e a condição", cen_01_schema),
        ("2. sem pedir nota: valores da nota descartados", cen_02_sem_nota_descarta),
        ("3. pedindo nota sem documento ou e-mail (DEVE falhar)", cen_03_sem_documento),
        ("4. documento com dígito ou tamanho errado (DEVE falhar)", cen_04_documento_invalido),
        ("5. ISS só para CNPJ (DEVE falhar sem resposta)", cen_05_iss_so_cnpj),
        ("6. formulário com nota chega ao evento vazio", cen_06_chega_ao_evento),
        ("7. não sobrescreve o que a vendedora digitou", cen_07_nao_sobrescreve),
        ("8. formulário sem nota não muda nada", cen_08_sem_nota_nao_muda),
        ("9. 'Não sei' não grava; o detalhe mostra a resposta", cen_09_nao_sei),
        ("10. o formulário não liga o chip nem cria nota", cen_10_nao_liga_o_chip),
        ("11. card Comercial sem documento (DEVE falhar)", cen_11_card_sem_documento),
        ("12. documento do cadastro ou do formulário basta", cen_12_documento_do_cadastro),
        ("13. dígito errado e e-mail inválido na venda (DEVE falhar)", cen_13_digito_errado_na_venda),
        ("14. pedido antigo não trava; apagar documento sim", cen_14_legado_nao_trava),
        ("15. criação e Editar tudo sem documento (DEVE falhar)", cen_15_criacao_e_editar_tudo),
        ("16. sugestão de município", cen_16_sugestao),
        ("17. município sem ISS retido; painel com sugestão e e-mail", cen_17_municipio_gravado_e_painel),
        ("18. editor: condição válida, inválida e 403 (DEVE falhar)", cen_18_editor),
    ]
    try:
        for nome, fn in passos:
            cenario(nome, fn)
    finally:
        cenario("19. limpeza", cen_19_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  ✗ {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
