"""Verificação da correção 327 — o coordenador vê o nome da cliente depois de aceitar.

Cenários:

   1. Controle: coordenador com convite aceito vê o nome da **Contratante** (e não o da assessora,
      vinculada antes dela).
   2. Só o nome: telefone e e-mail da cliente não aparecem em lugar nenhum da agenda.
   3. **DEVE falhar** — o elenco do mesmo evento (personagem aceito) não vê o nome.
   4. **DEVE falhar** — cargo de coordenador com convite pendente: nem no convite nem nos próximos.
   5. **DEVE falhar** — convite nunca enviado (`NULL`) não conta como aceite.
   6. **DEVE falhar** — outro cargo (Técnico de Som) aceito não vê o nome.
   7. Mesma pessoa coordena (aceito) e tem personagem pendente no mesmo evento: só o cartão do
      coordenador traz o nome.
   8. Evento só com o `client_id` legado: o nome vem dele.
   9. Dia de venda agrupada sem cliente próprio: vale a cliente do principal.
  10. Evento sem cliente nenhum: `cliente` nulo, sem erro.
  11. Histórico (evento passado coordenado): `cliente` nulo — fora por desenho.
  12. Aceitar pelo endpoint real faz o nome aparecer (aceite conferido por conexão separada).
  13. A agenda de quem coordena 4 eventos não custa mais consultas que a de quem coordena 1.
  14. Limpeza.

TUDO O QUE ESTE ARQUIVO TOCA É DESCARTÁVEL (eventos, cargos, clientes e talentos nascem e morrem
aqui, com prefixo próprio), pelo mesmo motivo do `verify_302.py`: nenhum cargo inventado é pendurado
em evento real. O evento é `source="platform"` para o sync do Google não o tratar como seu.

Requisições HTTP ficam FORA de `app.app_context()`, inclusive no cenário 13: contexto persistente
reaproveita a sessão entre requisições, e o many-to-one `EventClient.client` sairia do mapa de
identidade sem SQL, escondendo justamente o N+1 que o cenário mede.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"; $env:MANTO_SEM_THREADS = "1"
    .venv/Scripts/python.exe specs/327-cliente-para-coordenador/verify_327.py
"""

from __future__ import annotations

import json
import os
import sys
import traceback
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):  # console do Windows em cp1252
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
os.environ.setdefault("MAIL_SUPPRESS_SEND", "true")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, event, text  # noqa: E402

from app import create_app, db, limiter  # noqa: E402
from app.constants import now_sp  # noqa: E402
from app.models import CalendarEvent, Client, EventClient, EventRole, Talent  # noqa: E402

PREFIX = "__v327_"
SENHA = "verify-327-senha"
#: DDI "00" não existe: o telefone semeado nunca colide com uma ficha real (`phone` é UNIQUE).
FONE = "00327{:06d}"
EMAIL_CLIENTE = f"{PREFIX}ana@exemplo.com"

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False  # muitos logins no portal: o "10 per minute" estoura

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_externo = create_engine(os.environ["DATABASE_URL"], future=True)


def _no_banco(sql: str, **params):
    """Conexão separada — a única testemunha confiável de que algo foi commitado."""
    with _externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001 — harness: registra e segue
        with app.app_context():
            db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _login_talento(c, email: str) -> None:
    r = c.post("/api/portal/auth/login", json={"login": email, "password": SENHA})
    _garante(r.status_code == 200, f"login do talento {email} → {r.status_code}")


def _agenda(email: str) -> dict:
    with app.test_client() as c:
        _login_talento(c, email)
        r = c.get("/api/portal/agenda")
        _garante(r.status_code == 200, f"agenda → {r.status_code}")
        return r.get_json()


def _item(agenda: dict, lista: str, role_id: int) -> dict:
    for it in agenda[lista]:
        if it["role_id"] == role_id:
            return it
    raise AssertionError(f"escalação {role_id} não está em `{lista}`")


# ── fixtures (dentro de app_context) ─────────────────────────────────────────────────────────────


def _talento(sufixo: str) -> Talent:
    t = Talent(
        full_name=f"{PREFIX}{sufixo}",
        artistic_name=f"{PREFIX}{sufixo}",
        email_contact=f"{PREFIX}{sufixo}@manto.local",
        status="active",
        must_change_password=False,
        terms_accepted_at=datetime.utcnow(),
    )
    t.set_password(SENHA)
    db.session.add(t)
    db.session.flush()
    return t


def _cliente(n: int, nome: str, email: str | None = None) -> Client:
    c = Client(
        name=f"{PREFIX}{nome}",
        phone=FONE.format(n),
        phone_display=f"(00) 3270-{n:04d}",
        email=email,
        source="manual",
    )
    db.session.add(c)
    db.session.flush()
    return c


def _evento(sufixo: str, *, dias: int, client_id: int | None = None) -> CalendarEvent:
    inicio = datetime.combine(now_sp().date() + timedelta(days=dias), datetime.min.time()).replace(
        hour=15
    )
    ev = CalendarEvent(
        title=f"{PREFIX}{sufixo}",
        event_type="R&I",
        start_at=inicio,
        end_at=inicio + timedelta(hours=2),
        google_event_id=f"{PREFIX}{uuid.uuid4().hex[:10]}",
        source="platform",
        location=f"{PREFIX}Buffet, São Paulo",
        client_id=client_id,
    )
    db.session.add(ev)
    db.session.flush()
    return ev


def _vinculo(ev: CalendarEvent, cliente: Client, relacao: str) -> None:
    db.session.add(EventClient(event_id=ev.id, client_id=cliente.id, relationship_type=relacao))
    db.session.flush()


def _cargo(
    ev: CalendarEvent,
    talento: Talent,
    *,
    nome: str = "Coordenador",
    tipo: str = "extra",
    convite: str | None = "accepted",
) -> int:
    role = EventRole(
        event_id=ev.id,
        character_name=nome,
        role_type=tipo,
        talent_id=talento.id,
        invite_status=convite,
        cache_value=250,
    )
    db.session.add(role)
    db.session.flush()
    return role.id


def preparar() -> None:
    limpar()
    t = _talento("T")
    u = _talento("U")
    c1 = _talento("C1")
    c4 = _talento("C4")
    estado.update({k: v.email_contact for k, v in {"t": t, "u": u, "c1": c1, "c4": c4}.items()})

    contratante = _cliente(1, "Ana Contratante", email=EMAIL_CLIENTE)
    assessora = _cliente(2, "Bia Assessora")
    legado = _cliente(3, "Carla Legado")
    do_principal = _cliente(4, "Dora Principal")
    estado["fone_contratante"] = contratante.phone
    estado["fone_display"] = contratante.phone_display

    # Evento base: a assessora é vinculada ANTES da contratante — a preferência tem de vencer a
    # ordem de inserção. T coordena (aceito) e tem um personagem pendente; U é elenco aceito.
    ev = _evento("base", dias=20)
    _vinculo(ev, assessora, "Assessora")
    _vinculo(ev, contratante, "Contratante")
    estado["r_coord"] = _cargo(ev, t)
    estado["r_t_pers_pendente"] = _cargo(ev, t, nome="BLUEY", tipo="character", convite="pending")
    estado["r_u_elenco"] = _cargo(ev, u, nome="BINGO", tipo="character")

    ev = _evento("pendente", dias=21)
    _vinculo(ev, contratante, "Contratante")
    estado["r_pendente"] = _cargo(ev, t, convite="pending")

    ev = _evento("nunca_enviado", dias=22)
    _vinculo(ev, contratante, "Contratante")
    estado["r_nulo"] = _cargo(ev, t, convite=None)

    ev = _evento("tecnico", dias=23)
    _vinculo(ev, contratante, "Contratante")
    estado["r_tecnico"] = _cargo(ev, t, nome="Técnico de Som")

    ev = _evento("legado", dias=24, client_id=legado.id)
    estado["r_legado"] = _cargo(ev, t)

    principal = _evento("principal", dias=25)
    _vinculo(principal, do_principal, "Contratante")
    satelite = _evento("satelite", dias=26)
    satelite.group_leader_id = principal.id
    estado["r_satelite"] = _cargo(satelite, t)

    estado["r_sem_cliente"] = _cargo(_evento("sem_cliente", dias=27), t)

    ev = _evento("passado", dias=-10)
    _vinculo(ev, contratante, "Contratante")
    estado["r_passado"] = _cargo(ev, t)

    # Cenário 13: uma cliente distinta por evento, para o N+1 aparecer se existir.
    ev = _evento("um", dias=30)
    _vinculo(ev, _cliente(10, "Uma"), "Contratante")
    _cargo(ev, c1)
    for i in range(4):
        ev = _evento(f"quatro{i}", dias=31 + i)
        _vinculo(ev, _cliente(20 + i, f"Quatro {i}"), "Contratante")
        _cargo(ev, c4)
    db.session.commit()


def limpar() -> None:
    ids = [
        r[0]
        for r in db.session.query(CalendarEvent.id)
        .filter(CalendarEvent.title.like(f"{PREFIX}%"))
        .all()
    ]
    if ids:
        EventClient.query.filter(EventClient.event_id.in_(ids)).delete(synchronize_session=False)
        EventRole.query.filter(EventRole.event_id.in_(ids)).delete(synchronize_session=False)
        # `group_leader_id` é FK para a própria tabela: solta o satélite antes de apagar.
        CalendarEvent.query.filter(CalendarEvent.id.in_(ids)).update(
            {CalendarEvent.group_leader_id: None}, synchronize_session=False
        )
        CalendarEvent.query.filter(CalendarEvent.id.in_(ids)).delete(synchronize_session=False)
    Client.query.filter(Client.name.like(f"{PREFIX}%")).delete(synchronize_session=False)
    Talent.query.filter(Talent.full_name.like(f"{PREFIX}%")).delete(synchronize_session=False)
    db.session.commit()


# ── cenários ─────────────────────────────────────────────────────────────────────────────────────


def cen_01_controle() -> None:
    it = _item(_agenda(estado["t"]), "upcoming", estado["r_coord"])
    _garante(
        it.get("cliente") == f"{PREFIX}Ana Contratante",
        f"o coordenador aceito deveria ver a contratante, veio {it.get('cliente')!r}",
    )


def cen_02_so_o_nome() -> None:
    bruto = json.dumps(_agenda(estado["t"]), ensure_ascii=False)
    for dado in (estado["fone_contratante"], estado["fone_display"], EMAIL_CLIENTE):
        _garante(dado not in bruto, f"{dado!r} da cliente vazou para a agenda do portal")


def cen_03_elenco_nao_ve() -> None:
    it = _item(_agenda(estado["u"]), "upcoming", estado["r_u_elenco"])
    _garante(it.get("cliente") is None, f"o elenco viu a cliente: {it.get('cliente')!r}")


def cen_04_pendente_nao_ve() -> None:
    ag = _agenda(estado["t"])
    for lista in ("pending_invites", "upcoming"):
        it = _item(ag, lista, estado["r_pendente"])
        _garante(it.get("cliente") is None, f"convite pendente viu a cliente em `{lista}`")


def cen_05_nunca_enviado_nao_ve() -> None:
    it = _item(_agenda(estado["t"]), "upcoming", estado["r_nulo"])
    _garante(it.get("cliente") is None, "convite nunca enviado contou como aceite")


def cen_06_outro_cargo_nao_ve() -> None:
    it = _item(_agenda(estado["t"]), "upcoming", estado["r_tecnico"])
    _garante(it.get("cliente") is None, "Técnico de Som viu a cliente")


def cen_07_mesma_pessoa_por_escalacao() -> None:
    ag = _agenda(estado["t"])
    for lista in ("pending_invites", "upcoming"):
        it = _item(ag, lista, estado["r_t_pers_pendente"])
        _garante(
            it.get("cliente") is None,
            f"o personagem pendente herdou a cliente do cargo de coordenador em `{lista}`",
        )


def cen_08_client_id_legado() -> None:
    it = _item(_agenda(estado["t"]), "upcoming", estado["r_legado"])
    _garante(it.get("cliente") == f"{PREFIX}Carla Legado", f"legado → {it.get('cliente')!r}")


def cen_09_satelite_usa_principal() -> None:
    it = _item(_agenda(estado["t"]), "upcoming", estado["r_satelite"])
    _garante(it.get("cliente") == f"{PREFIX}Dora Principal", f"satélite → {it.get('cliente')!r}")


def cen_10_sem_cliente() -> None:
    it = _item(_agenda(estado["t"]), "upcoming", estado["r_sem_cliente"])
    _garante(it.get("cliente") is None, f"sem cliente → {it.get('cliente')!r}")


def cen_11_historico() -> None:
    it = _item(_agenda(estado["t"]), "history", estado["r_passado"])
    _garante(it.get("cliente") is None, "o histórico trouxe a cliente")


def cen_12_aceite_pelo_endpoint() -> None:
    with app.test_client() as c:
        _login_talento(c, estado["t"])
        r = c.post(f"/api/portal/invites/{estado['r_pendente']}/accept")
        _garante(r.status_code == 200, f"aceitar → {r.status_code}")
    linha = _no_banco("SELECT invite_status FROM event_roles WHERE id = :i", i=estado["r_pendente"])
    _garante(linha and linha[0][0] == "accepted", f"aceite não foi gravado: {linha}")
    it = _item(_agenda(estado["t"]), "upcoming", estado["r_pendente"])
    _garante(
        it.get("cliente") == f"{PREFIX}Ana Contratante",
        f"depois do aceite o nome deveria aparecer, veio {it.get('cliente')!r}",
    )


def cen_13_consulta_nao_cresce() -> None:
    with app.app_context():
        motor = db.engine  # o Engine sobrevive ao contexto; a requisição roda fora dele
    contagem = {"n": 0}

    def _conta(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        contagem["n"] += 1

    def _medir(email: str) -> int:
        with app.test_client() as c:
            _login_talento(c, email)
            contagem["n"] = 0
            event.listen(motor, "before_cursor_execute", _conta)
            try:
                r = c.get("/api/portal/agenda")
            finally:
                event.remove(motor, "before_cursor_execute", _conta)
        _garante(r.status_code == 200, f"agenda → {r.status_code}")
        nomes = [i.get("cliente") for i in r.get_json()["upcoming"]]
        _garante(all(nomes), f"cenário sem passar a vazio: alguma cliente veio nula {nomes}")
        return contagem["n"]

    um, quatro = _medir(estado["c1"]), _medir(estado["c4"])
    _garante(
        quatro <= um + 1,
        f"a agenda custa {quatro} consultas para 4 eventos coordenados e {um} para 1 (N+1)",
    )


def cen_14_limpeza() -> None:
    with app.app_context():
        limpar()
    sobra = _no_banco(
        "SELECT (SELECT count(*) FROM calendar_events WHERE title LIKE :p),"
        " (SELECT count(*) FROM clients WHERE name LIKE :p),"
        " (SELECT count(*) FROM talents WHERE full_name LIKE :p)",
        p=f"{PREFIX}%",
    )[0]
    _garante(tuple(sobra) == (0, 0, 0), f"sobrou semeadura: {sobra}")


def main() -> int:
    print("Correção 327 — o coordenador vê o nome da cliente depois de aceitar")
    with app.app_context():
        _garante(app.config.get("MAIL_SUPPRESS_SEND") is True, "MAIL_SUPPRESS_SEND desligado")
        preparar()
    try:
        cenario("1. controle: coordenador aceito vê a contratante", cen_01_controle)
        cenario("2. só o nome: telefone e e-mail não saem", cen_02_so_o_nome)
        cenario("3. **deve falhar** elenco do mesmo evento não vê", cen_03_elenco_nao_ve)
        cenario("4. **deve falhar** convite pendente não vê", cen_04_pendente_nao_ve)
        cenario("5. **deve falhar** convite nunca enviado não vê", cen_05_nunca_enviado_nao_ve)
        cenario("6. **deve falhar** outro cargo não vê", cen_06_outro_cargo_nao_ve)
        cenario("7. a regra é por escalação, não por evento", cen_07_mesma_pessoa_por_escalacao)
        cenario("8. client_id legado", cen_08_client_id_legado)
        cenario("9. dia agrupado usa a cliente do principal", cen_09_satelite_usa_principal)
        cenario("10. evento sem cliente", cen_10_sem_cliente)
        cenario("11. histórico fica sem a cliente", cen_11_historico)
        cenario("12. aceitar pelo endpoint faz o nome aparecer", cen_12_aceite_pelo_endpoint)
        cenario("13. a consulta não cresce com os eventos coordenados", cen_13_consulta_nao_cresce)
    finally:
        cenario("14. limpeza", cen_14_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"{ok}/{len(resultados)} OK")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  - {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
