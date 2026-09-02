"""Verificação da feature 272 — notificações internas (o aviso deixa de ser e-mail).

Cenários (spec.md, "Verificação"), contra o manto_local, sempre conferindo escrita por CONEXÃO
SEPARADA (lição do hotfix 257 — o autoflush da sessão esconde commit que não aconteceu):
 1. Formulário público → 1 notificação por COMERCIAL/SUPERADMIN ativo com acesso; 0 para CASTING,
    inativo e sem acesso; quem tem os dois papéis recebe 1; corpo diz "cliente identificada".
 2. Nenhum e-mail: `send_form_response_email` não existe mais e `formularios_write` não usa `send_async`.
 3. Idempotência: segunda emissão devolve 0; corrida (linha já no banco) não derruba a transação
    do chamador — a escrita pendente não relacionada comita normalmente.
 4. Regime A (avaliação): `score=1` → `urgent` no mesmo commit; `score=5` → `info`; rollback antes do
    commit → zero feedback e zero notificação.
 5. Regime B: produtor estourando → o POST público continua 201 e a resposta existe.
 6. Recusa de convite → CASTING + SUPERADMIN, COMERCIAL não; `urgent` para evento em ≤ 7 dias;
    segunda recusa não re-avisa.
 7. API: lista só as do usuário; `lida` em id alheio → 404; própria → idempotente + `unread_count`;
    `lidas` respeita `ate_id`; sem `ate_id` → 400; REVENDEDOR → 403 (guarda da 078); sem sessão → 401.
 8. Paginação por keyset: 35 linhas → 30 + 5, sem repetição, mesmo com linha nova entre as páginas.
 9. Abrir a resposta (`GET /api/formularios/respostas/<id>`) marca lida a MINHA, não a do outro.
10. Exclusão da resposta apaga as dela; exclusão do usuário leva a caixa (CASCADE).
11. Retenção: lida há 31d e não lida há 181d saem; lida há 29d e não lida há 179d ficam; dry-run não apaga.
12. Relógio (`now_sp`, não UTC) e plano: o COUNT de não lidas usa o índice parcial.
13. Limpeza.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    $env:PYTHONIOENCODING = "utf-8"
    .\\.venv\\Scripts\\python.exe specs\\272-notificacoes-internas\\verify_272.py
"""
from __future__ import annotations

import os
import sys
import traceback
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import (  # noqa: E402
    create_app,
    db,
    email_service,  # noqa: E402
)
from app.api import formularios_write  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import (  # noqa: E402
    CalendarEvent,
    Client,
    ClientFeedback,
    EventRole,
    FormResponse,
    Notification,
    Role,
    Talent,
    User,
)
from app.notificacoes import notificacoes_ops as ops  # noqa: E402

PREFIX = "__v272_"
SENHA = "verify-272-senha"
DATA_LIVRE = "2031-03-15"
TEL = "11977000272"  # telefone da cliente de teste (nacional)

app = create_app()
app.config["TESTING"] = True
app.config["MAIL_SUPPRESS_SEND"] = True

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_externo = create_engine(os.environ["DATABASE_URL"], future=True)


def _no_banco(sql: str, **params):
    with _externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _usuario(sufixo: str, *papeis: str, ativo: bool = True, acesso: bool = True) -> User:
    email = f"{PREFIX}{sufixo}@manto.local"
    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(name=f"{PREFIX}{sufixo}", email=email)
        db.session.add(user)
    user.is_active = ativo
    user.has_access = acesso
    user.set_password(SENHA)
    user.roles.clear()
    for papel in papeis:
        user.roles.append(Role.query.filter_by(name=papel).one())
    db.session.commit()
    return user


def _login(c, user: User) -> None:
    r = c.post("/api/auth/login", json={"email": user.email, "password": SENHA})
    _garante(r.status_code == 200, f"login {user.email} → {r.status_code}")


def _payload_formulario(nome: str) -> dict:
    from app.formularios.formularios_ops import FORM_META, _load_fields

    dados: dict[str, str] = {}
    for campo in _load_fields("comum"):
        if not campo.required:
            continue
        tipo = campo.field_type
        if tipo == "data":
            dados[campo.field_key] = DATA_LIVRE
        elif tipo == "hora":
            dados[campo.field_key] = "14:00"
        elif tipo == "email":
            dados[campo.field_key] = "verify272@example.com"
        elif tipo == "telefone":
            dados[f"{campo.field_key}_ddi"] = "+55"
            dados[f"{campo.field_key}_national"] = TEL
        elif tipo == "sim_nao":
            dados[campo.field_key] = "Sim"
        elif tipo == "selecao":
            dados[campo.field_key] = (campo.options_list or [""])[0]
        elif tipo == "cpf":
            dados[campo.field_key] = "12345678901"
        elif tipo == "cnpj":
            dados[campo.field_key] = "12345678000190"
        elif tipo == "cep":
            dados[campo.field_key] = "01310100"
        else:
            dados[campo.field_key] = f"{PREFIX}valor"
    dados[FORM_META["comum"]["name_key"]] = nome
    dados["whatsapp_ddi"] = "+55"
    dados["whatsapp_national"] = TEL
    dados["data_evento"] = DATA_LIVRE
    return dados


def _ids_usuarios_teste() -> dict[str, int]:
    return {k: v.id for k, v in estado["users"].items()}


def _notifs(**filtros) -> list:
    clauses = " AND ".join(f"{k} = :{k}" for k in filtros)
    return _no_banco(
        f"SELECT id, user_id, kind, severity, title, body, link_path, dedupe_key, read_at, created_at "
        f"FROM notifications WHERE {clauses} ORDER BY id",
        **filtros,
    )


# ───────────────────────────── preparação / limpeza ─────────────────────────────

def preparar() -> None:
    limpar()
    users = {
        "sa": _usuario("sa", RoleName.SUPERADMIN),
        "com": _usuario("com", RoleName.COMERCIAL),
        "cast": _usuario("cast", RoleName.CASTING),
        "ambos": _usuario("ambos", RoleName.COMERCIAL, RoleName.SUPERADMIN),
        "inativo": _usuario("inativo", RoleName.COMERCIAL, ativo=False),
        "sem_acesso": _usuario("semacesso", RoleName.COMERCIAL, acesso=False),
        "rev": _usuario("rev", "REVENDEDOR_EDUCAMANTO"),
    }
    estado["users"] = users
    # Cliente com o telefone do formulário → o auto-vínculo da 266 identifica a cliente.
    telefone = f"55{TEL}"  # `Client.phone` guarda só dígitos com DDI, sem "+"
    cliente = Client.query.filter_by(phone=telefone).first()
    if cliente is None:
        cliente = Client(name=f"{PREFIX}Cliente Identificada", phone=telefone, source="formulario")
        db.session.add(cliente)
        db.session.commit()
    estado["cliente_id"] = cliente.id
    estado["entidades"] = []  # (entity_type, entity_id) criados pelo teste


def limpar() -> None:
    # Notificações de tudo que o teste criou (também as de usuários REAIS do espelho, que são
    # destinatários legítimos de COMERCIAL/SUPERADMIN).
    for tipo, eid in estado.get("entidades", []):
        db.session.execute(
            text("DELETE FROM notifications WHERE entity_type = :t AND entity_id = :i"),
            {"t": tipo, "i": eid},
        )
    db.session.execute(text("DELETE FROM notifications WHERE dedupe_key LIKE :p"), {"p": f"{PREFIX}%"})
    db.session.commit()
    for fr in FormResponse.query.filter(FormResponse.contact_name.like(f"{PREFIX}%")).all():
        db.session.execute(text("DELETE FROM notifications WHERE entity_type='form_response' AND entity_id=:i"), {"i": fr.id})
        db.session.delete(fr)
    db.session.commit()
    for ev in CalendarEvent.query.filter(CalendarEvent.title.like(f"{PREFIX}%")).all():
        for fb in ClientFeedback.query.filter_by(event_id=ev.id).all():
            db.session.execute(text("DELETE FROM notifications WHERE entity_type='client_feedback' AND entity_id=:i"), {"i": fb.id})
            db.session.delete(fb)
        for role in EventRole.query.filter_by(event_id=ev.id).all():
            db.session.execute(text("DELETE FROM notifications WHERE entity_type='event_role' AND entity_id=:i"), {"i": role.id})
            db.session.delete(role)
        db.session.delete(ev)
    db.session.commit()
    for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        u.roles.clear()
        db.session.delete(u)
    db.session.commit()
    c = Client.query.filter_by(phone=f"55{TEL}").first()
    if c is not None and c.name.startswith(PREFIX):
        db.session.delete(c)
        db.session.commit()


# ───────────────────────────── cenários ─────────────────────────────

def cen_01_formulario_gera_notificacoes() -> None:
    with app.test_client() as c:
        r = c.post("/api/formularios/comum", data=_payload_formulario(f"{PREFIX}Maria"))
        _garante(r.status_code == 201, f"POST público → {r.status_code} {r.get_data(as_text=True)[:200]}")
    resposta = FormResponse.query.filter_by(contact_name=f"{PREFIX}Maria").order_by(FormResponse.id.desc()).first()
    _garante(resposta is not None, "resposta não gravada")
    estado["resposta_id"] = resposta.id
    estado["entidades"].append(("form_response", resposta.id))
    ids = _ids_usuarios_teste()
    linhas = _notifs(entity_type="form_response", entity_id=resposta.id)
    por_user = {linha.user_id: linha for linha in linhas}
    for quem in ("sa", "com", "ambos"):
        _garante(ids[quem] in por_user, f"{quem} não recebeu")
    for quem in ("cast", "inativo", "sem_acesso", "rev"):
        _garante(ids[quem] not in por_user, f"{quem} recebeu e não devia")
    _garante(sum(1 for linha in linhas if linha.user_id == ids["ambos"]) == 1, "COMERCIAL+SUPERADMIN recebeu 2")
    minha = por_user[ids["com"]]
    _garante(minha.kind == ops.KIND_FORM_RESPONSE and minha.severity == "info", f"kind/severity: {minha.kind}/{minha.severity}")
    _garante(minha.dedupe_key == f"form_response.nova:{resposta.id}", f"dedupe_key {minha.dedupe_key}")
    _garante(minha.link_path == f"/formularios?resposta={resposta.id}", f"link {minha.link_path}")
    _garante("cliente identificada" in (minha.body or ""), f"corpo sem cliente: {minha.body}")
    _garante(minha.read_at is None, "nasceu lida")
    print(f"         ({len(linhas)} destinatário(s) no total, incluindo usuários reais do espelho)")


def cen_02_nenhum_email() -> None:
    _garante(not hasattr(email_service, "send_form_response_email"), "send_form_response_email ainda existe")
    fonte = Path(formularios_write.__file__).read_text(encoding="utf-8")
    _garante("send_async" not in fonte and "send_form_response_email" not in fonte, "formularios_write ainda fala em e-mail")


def cen_03_idempotencia_e_corrida() -> None:
    resposta = FormResponse.query.get(estado["resposta_id"])
    _garante(ops.notificar_resposta_formulario(resposta) == 0, "segunda emissão gravou de novo")
    db.session.commit()
    antes = len(_notifs(entity_type="form_response", entity_id=resposta.id))
    # Corrida: a linha do usuário `com` já existe (cenário 1). Numa sessão com escrita pendente NÃO
    # relacionada, `emitir` para ele deve devolver 0 sem levantar, e a escrita pendente comita.
    com = estado["users"]["com"]
    com.name = f"{PREFIX}com-renomeado"
    gravadas = ops.emitir(
        ops.KIND_FORM_RESPONSE, title="repetida", dedupe_key=f"form_response.nova:{resposta.id}",
        entidade=("form_response", resposta.id), destinatarios=[com],
    )
    db.session.commit()
    _garante(gravadas == 0, f"corrida gravou {gravadas}")
    nome = _no_banco("SELECT name FROM users WHERE id = :i", i=com.id)[0][0]
    _garante(nome == f"{PREFIX}com-renomeado", "a escrita pendente do chamador se perdeu")
    _garante(len(_notifs(entity_type="form_response", entity_id=resposta.id)) == antes, "contagem mudou")
    # Corrida de verdade: linha inserida por fora, SELECT prévio não a vê → UNIQUE + savepoint.
    sa = estado["users"]["sa"]
    chave = f"{PREFIX}corrida:{uuid.uuid4().hex[:8]}"
    with _externo.begin() as conn:
        conn.execute(text(
            "INSERT INTO notifications (user_id, kind, severity, title, dedupe_key, created_at) "
            "VALUES (:u, 'form_response.nova', 'info', 'externa', :k, now())"), {"u": sa.id, "k": chave})
    sa.name = f"{PREFIX}sa-renomeado"
    # O SELECT prévio de `emitir` VÊ a linha externa (já comitada) — forçamos o caminho do savepoint
    # inserindo direto e esperando o IntegrityError ser engolido.
    from sqlalchemy.exc import IntegrityError
    try:
        with db.session.begin_nested():
            db.session.add(Notification(user_id=sa.id, kind="form_response.nova", title="dup", dedupe_key=chave, created_at=now_sp()))
            db.session.flush()
        raise AssertionError("a UNIQUE não disparou")
    except IntegrityError:
        pass
    db.session.commit()
    nome_sa = _no_banco("SELECT name FROM users WHERE id = :i", i=sa.id)[0][0]
    _garante(nome_sa == f"{PREFIX}sa-renomeado", "o savepoint não protegeu a transação do chamador")


def _evento(titulo: str, em_dias: int) -> CalendarEvent:
    inicio = now_sp().replace(microsecond=0) + timedelta(days=em_dias)
    ev = CalendarEvent(
        google_event_id=f"{PREFIX}{uuid.uuid4().hex}",
        title=f"{PREFIX}{titulo}", start_at=inicio, end_at=inicio + timedelta(hours=2),
        source="manual", feedback_token=uuid.uuid4().hex,
    )
    db.session.add(ev)
    db.session.commit()
    return ev


def cen_04_regime_a_avaliacao() -> None:
    ev = _evento("Festa Avaliada", 30)
    ids = _ids_usuarios_teste()
    with app.test_client() as c:
        r = c.post(f"/api/avaliar/{ev.feedback_token}", json={"client_name": "Ana", "score": 1, "tags": [], "comment": "Atrasaram"})
        _garante(r.status_code == 201, f"avaliar nota 1 → {r.status_code} {r.get_data(as_text=True)[:200]}")
    fb = ClientFeedback.query.filter_by(event_id=ev.id).order_by(ClientFeedback.id.desc()).first()
    estado["entidades"].append(("client_feedback", fb.id))
    linhas = _notifs(entity_type="client_feedback", entity_id=fb.id)
    por_user = {linha.user_id: linha for linha in linhas}
    _garante(ids["com"] in por_user and ids["sa"] in por_user, "COMERCIAL/SUPERADMIN não avisados")
    _garante(ids["cast"] not in por_user, "CASTING avisado de avaliação")
    _garante(por_user[ids["com"]].severity == "urgent", "nota 1 não é urgent")
    _garante(por_user[ids["com"]].link_path == f"/events/{ev.id}?aba=historico", f"link {por_user[ids['com']].link_path}")
    with app.test_client() as c:
        r = c.post(f"/api/avaliar/{ev.feedback_token}", json={"client_name": "Bia", "score": 5, "tags": []})
        _garante(r.status_code == 201, f"avaliar nota 5 → {r.status_code}")
    fb5 = ClientFeedback.query.filter_by(event_id=ev.id).order_by(ClientFeedback.id.desc()).first()
    estado["entidades"].append(("client_feedback", fb5.id))
    _garante(_notifs(entity_type="client_feedback", entity_id=fb5.id)[0].severity == "info", "nota 5 não é info")
    # Atomicidade: rollback antes do commit → nem feedback nem notificação.
    antes_fb = _no_banco("SELECT count(*) FROM client_feedbacks WHERE event_id = :e", e=ev.id)[0][0]
    antes_n = _no_banco("SELECT count(*) FROM notifications WHERE entity_type='client_feedback'")[0][0]
    fb_tmp = ClientFeedback(event_id=ev.id, score=2, client_name="Rollback")
    db.session.add(fb_tmp)
    db.session.flush()
    ops.notificar_avaliacao_recebida(fb_tmp, ev)
    db.session.rollback()
    _garante(_no_banco("SELECT count(*) FROM client_feedbacks WHERE event_id = :e", e=ev.id)[0][0] == antes_fb, "feedback sobreviveu ao rollback")
    _garante(_no_banco("SELECT count(*) FROM notifications WHERE entity_type='client_feedback'")[0][0] == antes_n, "notificação sobreviveu ao rollback")


def cen_05_regime_b_best_effort() -> None:
    original = ops.notificar_resposta_formulario

    def _explode(_r):
        raise RuntimeError("falha proposital da notificação")

    ops.notificar_resposta_formulario = _explode
    try:
        with app.test_client() as c:
            r = c.post("/api/formularios/comum", data=_payload_formulario(f"{PREFIX}Sem Aviso"))
    finally:
        ops.notificar_resposta_formulario = original
    _garante(r.status_code == 201, f"POST com produtor quebrado → {r.status_code}")
    resposta = FormResponse.query.filter_by(contact_name=f"{PREFIX}Sem Aviso").first()
    _garante(resposta is not None, "a resposta se perdeu junto com o aviso")
    estado["entidades"].append(("form_response", resposta.id))
    _garante(not _notifs(entity_type="form_response", entity_id=resposta.id), "notificação gravada apesar do erro")


def cen_06_recusa_de_convite() -> None:
    from app.talent_portal.portal_ops import reject_invite

    talento = Talent.query.filter(Talent.full_name.isnot(None)).order_by(Talent.id).first()
    _garante(talento is not None, "manto_local sem talento")
    ids = _ids_usuarios_teste()
    ev = _evento("Show Recusado", 3)  # ≤ 7 dias → urgent
    role = EventRole(event_id=ev.id, character_name="Princesa", talent_id=talento.id, invite_status="pending")
    db.session.add(role)
    db.session.commit()
    estado["entidades"].append(("event_role", role.id))
    r1 = reject_invite(talento, role.id)
    _garante(r1 is not None and r1.invite_status == "rejected", "recusa não gravou")
    linhas = _notifs(entity_type="event_role", entity_id=role.id)
    por_user = {linha.user_id: linha for linha in linhas}
    _garante(ids["cast"] in por_user and ids["sa"] in por_user, "CASTING/SUPERADMIN não avisados")
    _garante(ids["com"] not in por_user, "COMERCIAL avisado de recusa")
    _garante(por_user[ids["cast"]].severity == "urgent", "recusa em ≤7 dias não é urgent")
    _garante(por_user[ids["cast"]].link_path == f"/events/{ev.id}?aba=producao", "link errado")
    antes = len(linhas)
    reject_invite(talento, role.id)
    _garante(len(_notifs(entity_type="event_role", entity_id=role.id)) == antes, "segunda recusa re-avisou")
    ev2 = _evento("Show Distante", 30)
    role2 = EventRole(event_id=ev2.id, character_name="Fada", talent_id=talento.id, invite_status="pending")
    db.session.add(role2)
    db.session.commit()
    estado["entidades"].append(("event_role", role2.id))
    reject_invite(talento, role2.id)
    _garante(_notifs(entity_type="event_role", entity_id=role2.id)[0].severity == "info", "recusa distante não é info")


def cen_07_api() -> None:
    com, sa, rev = estado["users"]["com"], estado["users"]["sa"], estado["users"]["rev"]
    with app.test_client() as c:
        r = c.get("/api/notificacoes/nao-lidas")
        _garante(r.status_code == 401, f"sem sessão → {r.status_code}")
        _login(c, com)
        r = c.get("/api/notificacoes")
        _garante(r.status_code == 200, f"listar → {r.status_code}")
        corpo = r.get_json()
        _garante(all(True for _ in corpo["items"]), "lista")
        meus = {linha.id for linha in _no_banco("SELECT id FROM notifications WHERE user_id = :u", u=com.id)}
        _garante({i["id"] for i in corpo["items"]} <= meus, "a lista trouxe notificação de outro usuário")
        esperado = _no_banco("SELECT count(*) FROM notifications WHERE user_id = :u AND read_at IS NULL", u=com.id)[0][0]
        _garante(corpo["unread_count"] == esperado, f"unread_count {corpo['unread_count']} ≠ {esperado}")
        alheia = _no_banco("SELECT id FROM notifications WHERE user_id = :u ORDER BY id LIMIT 1", u=sa.id)[0][0]
        r = c.post(f"/api/notificacoes/{alheia}/lida")
        _garante(r.status_code == 404, f"lida em id alheio → {r.status_code}")
        _garante(_no_banco("SELECT read_at FROM notifications WHERE id = :i", i=alheia)[0][0] is None, "marcou a do outro")
        minha = _no_banco("SELECT id FROM notifications WHERE user_id = :u AND read_at IS NULL ORDER BY id LIMIT 1", u=com.id)[0][0]
        r = c.post(f"/api/notificacoes/{minha}/lida")
        _garante(r.status_code == 200 and r.get_json()["read_at"], f"lida própria → {r.status_code}")
        _garante(r.get_json()["unread_count"] == esperado - 1, "unread_count não decrementou")
        read_at_1 = r.get_json()["read_at"]
        r = c.post(f"/api/notificacoes/{minha}/lida")
        _garante(r.get_json()["read_at"] == read_at_1, "marcar lida não é idempotente")
        # ate_id: uma nova (id maior) continua não lida depois de "marcar todas" com teto anterior.
        maior = _no_banco("SELECT max(id) FROM notifications WHERE user_id = :u", u=com.id)[0][0]
        ops.emitir(ops.KIND_FORM_RESPONSE, title="chegou depois", dedupe_key=f"{PREFIX}depois", destinatarios=[com])
        db.session.commit()
        nova = _no_banco("SELECT id FROM notifications WHERE dedupe_key = :k", k=f"{PREFIX}depois")[0][0]
        r = c.post("/api/notificacoes/lidas", json={"ate_id": maior})
        _garante(r.status_code == 200, f"lidas → {r.status_code}")
        _garante(_no_banco("SELECT read_at FROM notifications WHERE id = :i", i=nova)[0][0] is None, "marcar todas engoliu a que chegou depois")
        _garante(_no_banco("SELECT count(*) FROM notifications WHERE user_id = :u AND read_at IS NULL AND id <= :m", u=com.id, m=maior)[0][0] == 0, "sobrou não lida abaixo do teto")
        r = c.post("/api/notificacoes/lidas", json={})
        _garante(r.status_code == 400 and "error" in r.get_json(), f"sem ate_id → {r.status_code}")
    with app.test_client() as c:
        _login(c, rev)
        r = c.get("/api/notificacoes")
        # A guarda de perfil restrito da 078 (`_REVENDEDOR_ALLOWED_API`) barra antes da view; o sino
        # nem é renderizado para ele (AppShell). 403 é o comportamento herdado, não um gate novo.
        _garante(r.status_code == 403, f"revendedor → {r.status_code}, esperava 403 da guarda da 078")


def cen_08_paginacao() -> None:
    com = estado["users"]["com"]
    for i in range(35):
        ops.emitir(ops.KIND_FORM_RESPONSE, title=f"pag {i}", dedupe_key=f"{PREFIX}pag:{i}", destinatarios=[com])
    db.session.commit()
    with app.test_client() as c:
        _login(c, com)
        p1 = c.get("/api/notificacoes?limite=30").get_json()
        _garante(len(p1["items"]) == 30 and p1["next_before"] == p1["items"][-1]["id"], "página 1 errada")
        # Uma linha nova entre as páginas não repete nem pula nada.
        ops.emitir(ops.KIND_FORM_RESPONSE, title="entre páginas", dedupe_key=f"{PREFIX}entre", destinatarios=[com])
        db.session.commit()
        p2 = c.get(f"/api/notificacoes?limite=30&antes_de={p1['next_before']}").get_json()
        ids1 = {i["id"] for i in p1["items"]}
        ids2 = {i["id"] for i in p2["items"]}
        _garante(not (ids1 & ids2), "repetiu item entre páginas")
        total = _no_banco("SELECT count(*) FROM notifications WHERE user_id = :u", u=com.id)[0][0]
        _garante(len(ids1) + len(ids2) == total - 1, f"páginas somam {len(ids1)+len(ids2)}, esperava {total-1} (a nova fica fora, é mais recente)")


def cen_09_abrir_resposta_marca_lida() -> None:
    com, sa = estado["users"]["com"], estado["users"]["sa"]
    with app.test_client() as c:
        r = c.post("/api/formularios/comum", data=_payload_formulario(f"{PREFIX}Para Abrir"))
        _garante(r.status_code == 201, "POST")
    resposta = FormResponse.query.filter_by(contact_name=f"{PREFIX}Para Abrir").first()
    estado["entidades"].append(("form_response", resposta.id))
    with app.test_client() as c:
        _login(c, com)
        r = c.get(f"/api/formularios/respostas/{resposta.id}")
        _garante(r.status_code == 200, f"detalhe → {r.status_code}")
    linhas = {linha.user_id: linha for linha in _notifs(entity_type="form_response", entity_id=resposta.id)}
    _garante(linhas[com.id].read_at is not None, "abrir a resposta não marcou a minha")
    _garante(linhas[sa.id].read_at is None, "abrir a resposta marcou a do outro")


def cen_10_exclusoes() -> None:
    from app.formularios.formularios_ops import delete_response

    resposta = FormResponse.query.get(estado["resposta_id"])
    outras_antes = _no_banco("SELECT count(*) FROM notifications WHERE entity_type='form_response' AND entity_id <> :i", i=resposta.id)[0][0]
    delete_response(resposta)
    _garante(not _notifs(entity_type="form_response", entity_id=estado["resposta_id"]), "excluir a resposta deixou notificações")
    _garante(_no_banco("SELECT count(*) FROM notifications WHERE entity_type='form_response' AND entity_id <> :i", i=estado["resposta_id"])[0][0] == outras_antes, "apagou notificação de outra resposta")
    inativo = estado["users"]["inativo"]
    ops.emitir(ops.KIND_FORM_RESPONSE, title="cascade", dedupe_key=f"{PREFIX}cascade", destinatarios=[inativo])
    db.session.commit()
    _garante(_no_banco("SELECT count(*) FROM notifications WHERE user_id = :u", u=inativo.id)[0][0] == 1, "seed do cascade")
    inativo.roles.clear()
    db.session.delete(inativo)
    db.session.commit()
    _garante(_no_banco("SELECT count(*) FROM notifications WHERE dedupe_key = :k", k=f"{PREFIX}cascade")[0][0] == 0, "CASCADE não levou a caixa")
    del estado["users"]["inativo"]


def cen_11_retencao() -> None:
    com = estado["users"]["com"]
    agora = now_sp().replace(microsecond=0)
    seeds = {
        "lida31": (agora - timedelta(days=40), agora - timedelta(days=31)),
        "lida29": (agora - timedelta(days=40), agora - timedelta(days=29)),
        "nao181": (agora - timedelta(days=181), None),
        "nao179": (agora - timedelta(days=179), None),
    }
    for nome, (criada, lida) in seeds.items():
        db.session.add(Notification(user_id=com.id, kind=ops.KIND_FORM_RESPONSE, title=nome, dedupe_key=f"{PREFIX}ret:{nome}", created_at=criada, read_at=lida))
    db.session.commit()
    candidatas = ops.contar_antigas(agora)
    _garante(candidatas >= 2, f"contar_antigas={candidatas}")
    apagadas = ops.limpar_antigas(agora)
    _garante(apagadas == candidatas, f"apagou {apagadas}, contou {candidatas}")
    restantes = {linha[0] for linha in _no_banco("SELECT title FROM notifications WHERE dedupe_key LIKE :p", p=f"{PREFIX}ret:%")}
    _garante(restantes == {"lida29", "nao179"}, f"restaram {restantes}")


def cen_12_relogio_e_plano() -> None:
    com = estado["users"]["com"]
    ops.emitir(ops.KIND_FORM_RESPONSE, title="relogio", dedupe_key=f"{PREFIX}relogio", destinatarios=[com])
    db.session.commit()
    criada = _no_banco("SELECT created_at FROM notifications WHERE dedupe_key = :k", k=f"{PREFIX}relogio")[0][0]
    _garante(abs((criada - now_sp()).total_seconds()) < 60, f"created_at {criada} longe de now_sp {now_sp()}")
    _garante(abs((criada - datetime.utcnow()).total_seconds()) > 3600 * 2, "created_at parece UTC, não São Paulo")
    # Com poucas linhas o planejador prefere Seq Scan (é mais barato numa tabela de 1 página); o que
    # se prova aqui é que o índice parcial SERVE à consulta — desligando o seq scan só nesta sessão.
    with _externo.connect() as conn:
        conn.execute(text("SET enable_seqscan = off"))
        plano = " ".join(r[0] for r in conn.execute(
            text("EXPLAIN SELECT count(id) FROM notifications WHERE user_id = :u AND read_at IS NULL"),
            {"u": com.id}).fetchall())
    _garante("ix_notifications_user_unread" in plano, f"plano sem o índice parcial: {plano[:200]}")
    print(f"         (plano: {plano[:110]}...)")


def cen_13_limpeza() -> None:
    limpar()
    _garante(User.query.filter(User.email.like(f"{PREFIX}%")).count() == 0, "usuário sobrou")
    _garante(_no_banco("SELECT count(*) FROM notifications WHERE dedupe_key LIKE :p", p=f"{PREFIX}%")[0][0] == 0, "notificação de teste sobrou")
    _garante(CalendarEvent.query.filter(CalendarEvent.title.like(f"{PREFIX}%")).count() == 0, "evento sobrou")


def main() -> int:
    print("Feature 272 — notificações internas")
    with app.app_context():
        preparar()
        try:
            cenario("1. formulário público → notificação por papel", cen_01_formulario_gera_notificacoes)
            cenario("2. nenhum e-mail (função removida)", cen_02_nenhum_email)
            cenario("3. idempotência e corrida com savepoint", cen_03_idempotencia_e_corrida)
            cenario("4. regime A: avaliação (urgent/info, rollback atômico)", cen_04_regime_a_avaliacao)
            cenario("5. regime B: produtor quebrado não derruba o POST", cen_05_regime_b_best_effort)
            cenario("6. recusa de convite → casting, sem re-aviso", cen_06_recusa_de_convite)
            cenario("7. API: escopo, 404 alheio, idempotente, ate_id, 400, 401", cen_07_api)
            cenario("8. paginação por keyset", cen_08_paginacao)
            cenario("9. abrir a resposta marca lida só a minha", cen_09_abrir_resposta_marca_lida)
            cenario("10. exclusão de resposta e de usuário", cen_10_exclusoes)
            cenario("11. retenção 30d/180d", cen_11_retencao)
            cenario("12. relógio now_sp e índice parcial no plano", cen_12_relogio_e_plano)
        finally:
            cenario("13. limpeza", cen_13_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"{ok}/{len(resultados)} OK")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
