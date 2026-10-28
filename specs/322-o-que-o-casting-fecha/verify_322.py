"""Verificação da feature 322 — o casting vê o que está fechando, e o maquiador aparece sozinho.

Cenários (spec §Verificação):
 1. Criação do orçamento (especial Boneco Grande Especial, cantor maquiado, ator): cada vaga grava o
    tipo vendido em `perfil_vendido`.
 2. Vínculo de orçamento (273) em evento sem orçamento: personagem casado ganha o tipo; o não casado
    fica vazio.
 3. Vínculo de novo e edição não trocam um tipo já gravado.
 4. Personagem à mão cantor + maquiagem: sem tipo gravado; o payload mostra as marcas.
 5. Casting lê o evento: recebe o perfil, não recebe teto nem conta do teto.
 6. Produto de tabela (Visita Mágica): Noel e ajudante com o tipo do produto.
 7. Criação manual com maquiagem: nasce 1 Maquiador sem talento nem teto, com linha no histórico.
 8. Criação do orçamento com maquiagem: 1 Maquiador só, com teto.
 9. Edição de evento com make e sem maquiador: a vaga nasce.
10. Evento que já tem "Maquiadora": nenhuma vaga nova.
11. Evento sem make / evento cancelado: nenhuma vaga.
12. Título do evento sem "Maquiador".
13. Vagas automáticas novas marcadas como do sistema.
14. Vaga adicionada por pessoa / coordenador escolhido no formulário: sem a marca do sistema.
15. Vagas anteriores ao deploy: nenhuma com a marca.
16. Superadmin muda a maquiagem na edição: vale.
17. Comercial desmarca a maquiagem pela API: a marca continua.            (DEVE falhar no código antigo)
18. Comercial marca personagem novo com maquiagem: nasce sem.             (DEVE falhar no código antigo)
19. Vínculo de orçamento feito pelo comercial marca a maquiagem do orçamento (e traz o maquiador).
20. Criação com pré-escala de personagem e de coordenador: "inserido pelo comercial" nas duas.
21. Edição que troca o talento pelo formulário liga a marca; salvar sem trocar não mexe nela.
22. Casting troca ou tira o talento pelo card: a marca sai.               (DEVE falhar no código antigo)
23. Limpeza.

Google DUBLADO (Agenda no-op; Maps não é chamado). E-mail: `MAIL_SUPPRESS_SEND` conferido no início
(a pré-escala dispara convite a talento real do espelho). Requisições HTTP FORA do `app_context`
(senão o `g` do login vaza entre clientes); toda asserção de escrita lê por conexão separada.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
    C:\\Users\\schim\\Desktop\\Manto_Platform\\.venv\\Scripts\\python.exe specs\\322-o-que-o-casting-fecha\\verify_322.py
"""
from __future__ import annotations

import json
import os
import sys
import traceback
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter, maps  # noqa: E402
from app.calendar import routes as cal_routes  # noqa: E402
from app.calendar import service as cal_service  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import CalendarEvent, EventRole, OrcamentoHistory, Role, Talent, User  # noqa: E402

PREFIX = "__v322_"
SENHA = "verify-322-senha"

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


def _no_banco(sql: str, **params):
    with _externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def _escreve(sql: str, **params) -> None:
    with _externo.begin() as conn:
        conn.execute(text(sql), params)


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

def _usuario(sufixo: str, *papeis: str) -> int:
    user = User(name=f"{PREFIX}{sufixo}", email=f"{PREFIX}{sufixo}@manto.local", is_active=True, has_access=True)
    user.set_password(SENHA)
    for p in papeis:
        user.roles.append(Role.query.filter_by(name=p).one())
    db.session.add(user)
    db.session.commit()
    return user.id


def _email(uid_chave: str) -> str:
    return f"{PREFIX}{uid_chave}@manto.local"


def _cliente(chave: str):
    """Cliente de teste logado pela API (fora do app_context)."""
    c = app.test_client()
    r = c.post("/api/auth/login", json={"email": _email(chave), "password": SENHA})
    _garante(r.status_code == 200, f"login {chave} → {r.status_code}")
    return c


def _orcamento(dono_id: int, *, performers: list[dict], has_show: bool, data: str, produtos: list | None = None) -> int:
    snap = {
        "performers": performers, "coordenador_qty": 1, "fora_sp": False, "km_ida": 0,
        "transporte_tipo": "carro", "num_carros": 1, "num_colaboradores": len(performers) + 1,
        "event_date": data, "event_time": "15:00", "nota_fiscal": True, "acrescimos": [],
    }
    if produtos is not None:
        snap["produtos"] = produtos
    entry = OrcamentoHistory(
        user_id=dono_id, client_name=f"{PREFIX}Cliente", event_location=f"{PREFIX}Buffet, São Paulo",
        event_date=data, total_1h=Decimal("3000"), total_2h=Decimal("4200"), total_3h=Decimal("5000"),
        total_4h=Decimal("5600"), has_show=has_show, form_snapshot=json.dumps(snap),
    )
    db.session.add(entry)
    db.session.commit()
    return entry.id


def _evento_google(sufixo: str, papeis: list[tuple[str, str, bool]], *, dias: int, tipo: str = "R&I") -> int:
    """Evento "importado do Google" (id falso, Agenda dublada) com as vagas dadas (nome, tipo, make)."""
    inicio = datetime.combine(now_sp().date() + timedelta(days=dias), datetime.min.time()).replace(hour=15)
    personagens = [n for n, t, _ in papeis if t == "character"]
    ev = CalendarEvent(
        title=f"{PREFIX}{sufixo} ({tipo}) {' + '.join(personagens)}", event_type=tipo, start_at=inicio,
        end_at=inicio + timedelta(hours=2), google_event_id=f"{PREFIX}{uuid.uuid4().hex[:8]}",
        source="google_calendar", location=f"{PREFIX}Buffet, São Paulo",
        # Venda e vendedor preenchidos: a edição pelo formulário valida os dois (feature 299/215b).
        sale_value=Decimal("1000"), sale_value_gross=Decimal("1000"), seller_id=estado["com"],
    )
    db.session.add(ev)
    db.session.flush()
    for nome, tipo_vaga, make in papeis:
        db.session.add(EventRole(event_id=ev.id, character_name=nome, role_type=tipo_vaga, needs_makeup=make or None))
    db.session.commit()
    return ev.id


def _vagas(eid: int) -> list:
    return _no_banco(
        "SELECT id, character_name, role_type, talent_id, cache_cap, needs_makeup, is_singer, perfil_vendido, "
        "criada_pelo_sistema, escalado_pelo_comercial FROM event_roles WHERE event_id = :i ORDER BY id",
        i=eid,
    )


def _vaga(eid: int, nome: str):
    achadas = [v for v in _vagas(eid) if v.character_name == nome]
    _garante(len(achadas) == 1, f"vaga {nome!r}: {len(achadas)} no evento {eid} — {[v.character_name for v in _vagas(eid)]}")
    return achadas[0]


def _maquiadores(eid: int) -> list:
    return [v for v in _vagas(eid) if "maquiad" in v.character_name.lower()]


def _corpo_criacao(titulo: str, *, dias: int, characters: list[dict], orc_id: int | None = None,
                   coordenador: int | None = None, tipo: str = "SHOW") -> dict:
    d = (now_sp().date() + timedelta(days=dias)).isoformat()
    corpo = {
        "title": f"{PREFIX}{titulo}", "event_type": tipo, "date": d, "start": "15:00", "end": "17:00",
        "location": f"{PREFIX}Buffet, São Paulo", "description": "", "needs_rehearsal": False,
        "sale_value": 4200, "sale_value_gross": 4200, "transport_value": 0, "acrescimo_value": 0,
        "with_invoice": False, "is_cortesia_permuta": False, "seller_id": estado["sa"], "sale_date": None,
        "payment_method": None, "payment_installments": None, "payment_due_date": None,
        "duracao": "2", "characters": characters, "orc_caches": [], "acrescimos": [],
        "client_pairs": [], "observations": [],
    }
    if orc_id is not None:
        corpo["orcamento_history_id"] = orc_id
    if coordenador is not None:
        corpo["coordinator_talent_id"] = coordenador
    return corpo


def _criar(chave: str, corpo: dict) -> int:
    c = _cliente(chave)
    r = c.post("/api/events", json=corpo)
    _garante(r.status_code == 201, f"POST /api/events → {r.status_code} {r.get_data(as_text=True)[:300]}")
    j = r.get_json()
    return j["event"]["id"] if "event" in j else j["id"]


def _corpo_edicao(eid: int, characters: list[dict], *, coordenador: int | None = None) -> dict:
    """Corpo do formulário de edição a partir do que está gravado (o React manda o evento inteiro)."""
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
            "characters": characters, "clients": [],
        }
    if coordenador is not None:
        corpo["coordinator_talent_id"] = coordenador
    return corpo


def _personagens_do_form(eid: int, **troca) -> list[dict]:
    """O que o formulário de edição manda hoje para cada personagem gravado (role_id, flags, talento)."""
    linhas = []
    for v in _vagas(eid):
        if v.role_type != "character":
            continue
        linha = {
            "role_id": v.id, "name": v.character_name, "figurino_sheet_id": None, "cache_value": None,
            "needs_makeup": bool(v.needs_makeup), "is_singer": bool(v.is_singer), "talent_id": v.talent_id,
        }
        linha.update(troca.get(v.character_name, {}))
        linhas.append(linha)
    return linhas


def _editar(chave: str, eid: int, corpo: dict) -> None:
    c = _cliente(chave)
    r = c.patch(f"/api/events/{eid}", json=corpo)
    _garante(r.status_code == 200, f"PATCH /api/events/{eid} ({chave}) → {r.status_code} {r.get_data(as_text=True)[:300]}")


def _vincular(chave: str, eid: int, orc_id: int) -> dict:
    c = _cliente(chave)
    r = c.patch(f"/api/events/{eid}/orcamento", json={"orcamento_history_id": orc_id})
    _garante(r.status_code == 200, f"vínculo ({chave}) → {r.status_code} {r.get_data(as_text=True)[:300]}")
    return r.get_json()


def _elenco(chave: str, eid: int) -> list[dict]:
    c = _cliente(chave)
    r = c.get(f"/api/events/{eid}")
    _garante(r.status_code == 200, f"GET evento ({chave}) → {r.status_code}")
    return r.get_json()["elenco"]


def preparar() -> None:
    with app.app_context():
        _garante(app.config.get("MAIL_SUPPRESS_SEND") is True, "MAIL_SUPPRESS_SEND desligado — convite iria a talento real")
        limpar()
        estado["sa"] = _usuario("sa", RoleName.SUPERADMIN)
        estado["com"] = _usuario("com", RoleName.COMERCIAL)
        estado["cast"] = _usuario("cast", RoleName.CASTING)
        talentos = [t.id for t in Talent.query.filter_by(status="active").order_by(Talent.id).limit(4).all()]
        _garante(len(talentos) == 4, "o espelho precisa de 4 talentos ativos")
        estado["talentos"] = talentos
        data = (now_sp().date() + timedelta(days=50)).isoformat()
        estado["orc_a"] = _orcamento(estado["sa"], has_show=True, data=data, performers=[
            {"type": "especial", "personagem": "Boneco Grande Especial", "nome": "Bumblebee"},
            {"type": "cantor", "nome": "Moana", "makeup": True},
            {"type": "ator", "subtipo": "cara_limpa", "nome": "Fada"},
        ])
        # O vínculo é 1:1 entre eventos vivos (273): o evento do vínculo precisa do seu orçamento.
        estado["orc_vinc"] = _orcamento(estado["sa"], has_show=True, data=data, performers=[
            {"type": "especial", "personagem": "Boneco Grande Especial", "nome": "Bumblebee"},
            {"type": "cantor", "nome": "Moana", "makeup": True},
        ])
        estado["orc_produto"] = _orcamento(estado["sa"], has_show=False, data=data, performers=[],
                                           produtos=[{"chave": "visita_magica_ajudante"}])
        estado["orc_da_com"] = _orcamento(estado["com"], has_show=False, data=data, performers=[
            {"type": "ator", "subtipo": "cara_limpa", "nome": "Bluey", "makeup": True},
        ])
        estado["corte"] = _no_banco("SELECT coalesce(max(id), 0) FROM event_roles")[0][0]


def limpar() -> None:
    ids = [r[0] for r in _no_banco("SELECT id FROM calendar_events WHERE title LIKE :p OR google_event_id LIKE :p", p=f"%{PREFIX}%")]
    for eid in ids:
        for tabela in ("commission_payments", "event_logs", "event_roles", "event_clients"):
            db.session.execute(text(f"DELETE FROM {tabela} WHERE event_id = :i"), {"i": eid})
    db.session.commit()
    for eid in ids:
        ev = CalendarEvent.query.get(eid)
        if ev is not None:
            db.session.delete(ev)
    db.session.commit()
    for o in OrcamentoHistory.query.filter(OrcamentoHistory.client_name.like(f"{PREFIX}%")).all():
        db.session.delete(o)
    db.session.commit()
    for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        u.roles.clear()
        db.session.delete(u)
    db.session.commit()


# ───────────────────────────── História 1 — o tipo do personagem ─────────────────────────────

def cen_01_criacao_grava_o_tipo() -> None:
    corpo = _corpo_criacao("orcamento", dias=50, orc_id=estado["orc_a"], characters=[
        {"name": "Bumblebee"}, {"name": "Moana", "needs_makeup": True, "is_singer": True}, {"name": "Fada"},
    ])
    eid = _criar("sa", corpo)
    estado["ev_orc"] = eid
    perfis = {v.character_name: v.perfil_vendido for v in _vagas(eid) if v.role_type == "character"}
    _garante(perfis == {
        "Bumblebee": "Boneco Grande Especial",
        "Moana": "Cantor · show · com maquiagem",
        "Fada": "Ator cara-limpa",
    }, f"perfis: {perfis}")


def cen_02_vinculo_grava_o_tipo() -> None:
    with app.app_context():
        eid = _evento_google("vinculo", [("BUMBLEBEE", "character", False), ("Outro", "character", False),
                                         ("Coordenador", "extra", False)], dias=51)
    estado["ev_vinc"] = eid
    _vincular("sa", eid, estado["orc_vinc"])
    _garante(_vaga(eid, "BUMBLEBEE").perfil_vendido == "Boneco Grande Especial", f"casado: {_vaga(eid, 'BUMBLEBEE')}")
    _garante(_vaga(eid, "Outro").perfil_vendido is None, f"não casado ganhou tipo: {_vaga(eid, 'Outro')}")


def cen_03_tipo_nao_muda() -> None:
    eid = estado["ev_vinc"]
    _escreve("UPDATE event_roles SET perfil_vendido = 'Tipo escrito antes' WHERE event_id = :i AND character_name = 'BUMBLEBEE'", i=eid)
    _vincular("sa", eid, estado["orc_vinc"])
    _garante(_vaga(eid, "BUMBLEBEE").perfil_vendido == "Tipo escrito antes", "o vínculo trocou o tipo")
    _editar("sa", eid, _corpo_edicao(eid, _personagens_do_form(eid)))
    _garante(_vaga(eid, "BUMBLEBEE").perfil_vendido == "Tipo escrito antes", "a edição trocou o tipo")


def cen_04_personagem_a_mao() -> None:
    t1, _t2, t3, _t4 = estado["talentos"]
    corpo = _corpo_criacao("manual", dias=52, tipo="R&I", coordenador=t3, characters=[
        {"name": "Cantora", "needs_makeup": True, "is_singer": True, "talent_id": t1},
        {"name": "Simples"},
    ])
    eid = _criar("sa", corpo)
    estado["ev_manual"] = eid
    _garante(_vaga(eid, "Cantora").perfil_vendido is None, "personagem à mão ganhou tipo gravado")
    elenco = {r["character_name"]: r for r in _elenco("sa", eid)}
    _garante(elenco["Cantora"].get("perfil") == "Cantor · com maquiagem", f"payload Cantora: {elenco['Cantora'].get('perfil')!r}")
    _garante(elenco["Simples"].get("perfil") is None, f"payload Simples: {elenco['Simples'].get('perfil')!r}")


def cen_05_casting_le_o_tipo_sem_dinheiro() -> None:
    elenco = {r["character_name"]: r for r in _elenco("cast", estado["ev_orc"])}
    moana = elenco["Moana"]
    _garante(moana.get("perfil") == "Cantor · show · com maquiagem", f"casting não recebeu o perfil: {moana.get('perfil')!r}")
    _garante(moana.get("cache_cap") is None and moana.get("cache_cap_note") is None, "casting recebeu teto/conta")


def cen_06_produto_de_tabela() -> None:
    corpo = _corpo_criacao("produto", dias=53, tipo="R&I", orc_id=estado["orc_produto"], characters=[
        {"name": "Papai Noel", "needs_makeup": True}, {"name": "Ajudante do Noel"},
    ])
    eid = _criar("sa", corpo)
    estado["ev_produto"] = eid
    noel, aj = _vaga(eid, "Papai Noel").perfil_vendido, _vaga(eid, "Ajudante do Noel").perfil_vendido
    _garante(noel == "Visita Mágica — Papai Noel + Ajudante · com maquiagem", f"Noel: {noel!r}")
    _garante(aj == "Visita Mágica — Papai Noel + Ajudante", f"Ajudante: {aj!r}")
    _garante(len(_maquiadores(eid)) == 1, f"produto: {len(_maquiadores(eid))} maquiadores")


# ───────────────────────────── História 2 — o maquiador aparece ─────────────────────────────

def cen_07_criacao_manual_cria_maquiador() -> None:
    eid = estado["ev_manual"]
    mq = _maquiadores(eid)
    _garante(len(mq) == 1, f"maquiadores: {[m.character_name for m in mq]}")
    _garante(mq[0].character_name == "Maquiador" and mq[0].role_type == "extra", f"vaga: {tuple(mq[0])}")
    _garante(mq[0].talent_id is None and mq[0].cache_cap is None, f"nasceu com talento/teto: {tuple(mq[0])}")
    logs = [r[0] for r in _no_banco("SELECT message FROM event_logs WHERE event_id = :i", i=eid)]
    _garante(any("Vaga de Maquiador criada" in m for m in logs), f"sem linha no histórico: {logs}")


def cen_08_orcamento_um_maquiador_com_teto() -> None:
    mq = _maquiadores(estado["ev_orc"])
    _garante(len(mq) == 1 and mq[0].cache_cap is not None, f"maquiadores do orçamento: {[tuple(m) for m in mq]}")


def cen_09_edicao_cria_maquiador() -> None:
    with app.app_context():
        eid = _evento_google("edicao", [("Elsa", "character", True), ("Coordenador", "extra", False)], dias=54)
    estado["ev_edicao"] = eid
    _garante(not _maquiadores(eid), "o evento de teste já nasceu com maquiador")
    _editar("sa", eid, _corpo_edicao(eid, _personagens_do_form(eid)))
    _garante(len(_maquiadores(eid)) == 1, f"edição: {len(_maquiadores(eid))} maquiadores")


def cen_10_maquiadora_existente() -> None:
    with app.app_context():
        eid = _evento_google("maquiadora", [("Elsa", "character", True), ("Maquiadora", "extra", False)], dias=55)
    _editar("sa", eid, _corpo_edicao(eid, _personagens_do_form(eid)))
    _garante([m.character_name for m in _maquiadores(eid)] == ["Maquiadora"], f"duplicou: {[m.character_name for m in _maquiadores(eid)]}")


def cen_11_sem_make_e_cancelado() -> None:
    with app.app_context():
        eid = _evento_google("semmake", [("Anna", "character", False), ("Coordenador", "extra", False)], dias=56)
    _editar("sa", eid, _corpo_edicao(eid, _personagens_do_form(eid)))
    _garante(not _maquiadores(eid), "evento sem maquiagem ganhou maquiador")
    from app.calendar.casting_ops import garantir_vaga_de_maquiador
    from app.constants import TZ_SP  # noqa: F401 — o núcleo recebe o fuso de quem chama

    with app.app_context():
        cid = _evento_google("cancelado", [("Elsa", "character", True)], dias=57)
        ev = CalendarEvent.query.get(cid)
        ev.cancelled_at = datetime.utcnow()
        db.session.commit()
        criada = garantir_vaga_de_maquiador(ev, tz=TZ_SP)
        db.session.commit()
    _garante(criada is None and not _maquiadores(cid), "cancelado ganhou maquiador")


def cen_12_titulo_sem_maquiador() -> None:
    for chave in ("ev_orc", "ev_manual", "ev_produto"):
        titulo = _no_banco("SELECT title FROM calendar_events WHERE id = :i", i=estado[chave])[0][0]
        _garante("maquiad" not in titulo.lower(), f"título com maquiador: {titulo}")


# ───────────────────────────── História 3 — vagas do sistema ─────────────────────────────

def cen_13_vagas_do_sistema_marcadas() -> None:
    ev_orc = {v.character_name: v for v in _vagas(estado["ev_orc"])}
    for nome in ("Coordenador", "Técnico de Som", "Técnico de Som (Presença)", "Maquiador"):
        _garante(ev_orc[nome].criada_pelo_sistema is True, f"orçamento: {nome} sem a marca")
    _garante(_vaga(estado["ev_manual"], "Maquiador").criada_pelo_sistema is True, "maquiador automático sem a marca")
    _garante(_vaga(estado["ev_vinc"], "Maquiador").criada_pelo_sistema is True, "maquiador do vínculo sem a marca")
    personagens = [v for v in _vagas(estado["ev_orc"]) if v.role_type == "character"]
    _garante(all(v.criada_pelo_sistema is None for v in personagens), "personagem marcado como do sistema")
    elenco = {r["character_name"]: r for r in _elenco("cast", estado["ev_orc"])}
    _garante(elenco["Maquiador"].get("criada_pelo_sistema") is True, "payload sem criada_pelo_sistema")


def cen_14_vaga_de_pessoa_sem_marca() -> None:
    eid = estado["ev_manual"]
    coord = _vaga(eid, "Coordenador")
    _garante(coord.criada_pelo_sistema is None, "coordenador escolhido no formulário levou a marca do sistema")
    c = _cliente("cast")
    r = c.post(f"/api/events/{eid}/roles", json={"character_name": "Fotógrafo", "role_type": "extra"})
    _garante(r.status_code in (200, 201), f"Adicionar pessoa → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(_vaga(eid, "Fotógrafo").criada_pelo_sistema is None, "vaga adicionada pelo casting levou a marca")


def cen_15_vagas_antigas_sem_marca() -> None:
    n = _no_banco(
        "SELECT count(*) FROM event_roles r JOIN calendar_events e ON e.id = r.event_id "
        "WHERE r.id <= :corte AND (r.criada_pelo_sistema OR r.escalado_pelo_comercial OR r.perfil_vendido IS NOT NULL)",
        corte=estado["corte"],
    )[0][0]
    _garante(n == 0, f"{n} vagas anteriores ao deploy com marca")


# ───────────────────────────── História 4 — a trava da maquiagem ─────────────────────────────

def cen_16_superadmin_muda_a_maquiagem() -> None:
    eid = estado["ev_edicao"]
    _editar("sa", eid, _corpo_edicao(eid, _personagens_do_form(eid, Elsa={"needs_makeup": False})))
    _garante(not _vaga(eid, "Elsa").needs_makeup, "superadmin não conseguiu desmarcar")
    _editar("sa", eid, _corpo_edicao(eid, _personagens_do_form(eid, Elsa={"needs_makeup": True})))
    _garante(_vaga(eid, "Elsa").needs_makeup is True, "superadmin não conseguiu marcar")
    _garante(len(_maquiadores(eid)) == 1, "desmarcar/marcar duplicou ou apagou o maquiador")


def cen_17_comercial_nao_desmarca() -> None:
    eid = estado["ev_edicao"]
    _editar("com", eid, _corpo_edicao(eid, _personagens_do_form(eid, Elsa={"needs_makeup": False})))
    _garante(_vaga(eid, "Elsa").needs_makeup is True, "o comercial desmarcou a maquiagem")


def cen_18_comercial_nao_marca_novo() -> None:
    eid = estado["ev_edicao"]
    linhas = _personagens_do_form(eid) + [{"name": "Novo", "needs_makeup": True, "is_singer": False}]
    _editar("com", eid, _corpo_edicao(eid, linhas))
    _garante(not _vaga(eid, "Novo").needs_makeup, "o comercial marcou maquiagem num personagem novo")


def cen_19_vinculo_do_comercial_marca() -> None:
    with app.app_context():
        eid = _evento_google("vinculocom", [("Bluey", "character", False), ("Coordenador", "extra", False)], dias=58)
    _vincular("com", eid, estado["orc_da_com"])
    _garante(_vaga(eid, "Bluey").needs_makeup is True, "o vínculo do comercial não marcou a maquiagem do orçamento")
    _garante(len(_maquiadores(eid)) == 1, f"vínculo: {len(_maquiadores(eid))} maquiadores")


# ───────────────────────────── História 5 — inserido pelo comercial ─────────────────────────────

def cen_20_pre_escala_marcada() -> None:
    eid = estado["ev_manual"]
    _garante(_vaga(eid, "Cantora").escalado_pelo_comercial is True, "pré-escala do personagem sem a marca")
    _garante(_vaga(eid, "Coordenador").escalado_pelo_comercial is True, "coordenador escolhido sem a marca")
    _garante(_vaga(eid, "Simples").escalado_pelo_comercial is None, "vaga sem talento com a marca")
    elenco = {r["character_name"]: r for r in _elenco("cast", eid)}
    _garante(elenco["Cantora"].get("escalado_pelo_comercial") is True, "payload sem escalado_pelo_comercial")


def cen_21_edicao_liga_e_preserva() -> None:
    eid = estado["ev_manual"]
    t1, t2, _t3, _t4 = estado["talentos"]
    _escreve("UPDATE event_roles SET escalado_pelo_comercial = NULL WHERE event_id = :i AND character_name = 'Cantora'", i=eid)
    _editar("com", eid, _corpo_edicao(eid, _personagens_do_form(eid, Simples={"talent_id": t2})))
    _garante(_vaga(eid, "Simples").escalado_pelo_comercial is True, "a troca pelo formulário não ligou a marca")
    _garante(_vaga(eid, "Cantora").escalado_pelo_comercial is None, "salvar sem trocar mexeu na marca")
    _garante(_vaga(eid, "Cantora").talent_id == t1, "o talento da Cantora mudou")


def cen_22_casting_troca_ou_tira() -> None:
    eid = estado["ev_manual"]
    _t1, _t2, _t3, t4 = estado["talentos"]
    simples, coord = _vaga(eid, "Simples"), _vaga(eid, "Coordenador")
    # Controle: sem a marca ligada antes, "a marca sai" passaria a vazio no código antigo.
    _garante(simples.escalado_pelo_comercial is True and coord.escalado_pelo_comercial is True,
             f"pré-condição: Simples={simples.escalado_pelo_comercial} Coordenador={coord.escalado_pelo_comercial}")
    c = _cliente("cast")
    r = c.post(f"/api/roles/{simples.id}/assign", json={"talent_id": t4, "cache_value": None})
    _garante(r.status_code == 200, f"assign → {r.status_code} {r.get_data(as_text=True)[:200]}")
    r = c.post(f"/api/roles/{coord.id}/assign", json={"talent_id": None, "cache_value": None})
    _garante(r.status_code == 200, f"tirar → {r.status_code} {r.get_data(as_text=True)[:200]}")
    _garante(_vaga(eid, "Simples").escalado_pelo_comercial is None, "a troca pelo casting manteve a marca")
    _garante(_vaga(eid, "Coordenador").escalado_pelo_comercial is None, "tirar o talento manteve a marca")


def cen_23_limpeza() -> None:
    with app.app_context():
        limpar()
        _garante(CalendarEvent.query.filter(CalendarEvent.title.like(f"{PREFIX}%")).count() == 0, "evento sobrou")
        _garante(OrcamentoHistory.query.filter(OrcamentoHistory.client_name.like(f"{PREFIX}%")).count() == 0, "orçamento sobrou")
        _garante(User.query.filter(User.email.like(f"{PREFIX}%")).count() == 0, "usuário sobrou")


def main() -> int:
    print("Feature 322 — o casting vê o que está fechando")
    preparar()
    passos = [
        ("1. criação do orçamento grava o tipo de cada personagem", cen_01_criacao_grava_o_tipo),
        ("2. vínculo grava o tipo do casado; o não casado fica vazio", cen_02_vinculo_grava_o_tipo),
        ("3. vínculo de novo e edição não trocam o tipo", cen_03_tipo_nao_muda),
        ("4. personagem à mão: sem tipo gravado, marcas no payload", cen_04_personagem_a_mao),
        ("5. casting recebe o perfil e não recebe teto nem conta", cen_05_casting_le_o_tipo_sem_dinheiro),
        ("6. produto de tabela: tipo do produto no Noel e no ajudante", cen_06_produto_de_tabela),
        ("7. criação manual com maquiagem cria 1 Maquiador vazio, com histórico", cen_07_criacao_manual_cria_maquiador),
        ("8. criação do orçamento: 1 Maquiador só, com teto", cen_08_orcamento_um_maquiador_com_teto),
        ("9. edição de evento com make e sem maquiador cria a vaga", cen_09_edicao_cria_maquiador),
        ("10. evento com Maquiadora não ganha outra vaga", cen_10_maquiadora_existente),
        ("11. sem make e cancelado: nenhuma vaga", cen_11_sem_make_e_cancelado),
        ("12. título sem Maquiador", cen_12_titulo_sem_maquiador),
        ("13. vagas automáticas marcadas como do sistema", cen_13_vagas_do_sistema_marcadas),
        ("14. vaga de pessoa e coordenador escolhido sem a marca do sistema", cen_14_vaga_de_pessoa_sem_marca),
        ("15. vagas anteriores ao deploy sem marca", cen_15_vagas_antigas_sem_marca),
        ("16. superadmin muda a maquiagem na edição", cen_16_superadmin_muda_a_maquiagem),
        ("17. comercial não desmarca a maquiagem (DEVE falhar no antigo)", cen_17_comercial_nao_desmarca),
        ("18. comercial não marca maquiagem em personagem novo (DEVE falhar no antigo)", cen_18_comercial_nao_marca_novo),
        ("19. vínculo do comercial marca a maquiagem do orçamento e traz o maquiador", cen_19_vinculo_do_comercial_marca),
        ("20. pré-escala de personagem e coordenador: inserido pelo comercial", cen_20_pre_escala_marcada),
        ("21. edição que troca o talento liga a marca; sem troca não mexe", cen_21_edicao_liga_e_preserva),
        ("22. casting troca ou tira o talento: a marca sai (DEVE falhar no antigo)", cen_22_casting_troca_ou_tira),
    ]
    manter = os.environ.get("VERIFY_322_MANTER") == "1"
    try:
        for nome, fn in passos:
            cenario(nome, fn)
    finally:
        if manter:
            # Para a conferência de tela (quickstart): os eventos e os usuários __v322_ ficam; a
            # próxima rodada sem a variável limpa tudo.
            print("  (VERIFY_322_MANTER=1: limpeza pulada) eventos:",
                  {k: v for k, v in estado.items() if k.startswith("ev_")})
        else:
            cenario("23. limpeza", cen_23_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  ✗ {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
