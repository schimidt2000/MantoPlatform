"""Verificação da feature 302 — o que o artista vê do evento no Portal.

Cenários (a tabela da seção "Verificação" da spec):

   1. O payload das três listas traz `start_at` **e** `end_at`.
   2. Show com um ensaio: o bloco traz data, hora e local do ensaio.
   3. Show com **dois** ensaios: a lista traz os dois, ordenados por início.
  4b. Evento que termina no dia seguinte: o payload leva as duas datas inteiras.
  4c. Show futuro cujo ensaio **já aconteceu**: o ensaio não vem no bloco.
   4. Evento sem ensaio, sem maquiagem e sem saída: `before_event` é **`None`**.
   5. `makeup_location = "manto"`: o payload devolve `Manto Produções`, nunca o código.
  5b. `makeup_location` com endereço digitado: devolve o endereço como escrito.
   6. Escalação de cargo (`role_type='extra'`): o payload diz que não é personagem.
  6b. Corpo do e-mail de convite de um cargo: diz "Função" e traduz o local da maquiagem.
  6c. Convite pendente num evento com ensaio: o item de convites traz o bloco.
   7. Show passado: o item do histórico **não** traz ensaio.
   8. `GET /api/portal/agenda` **continua** entregando `history`; o histórico segue completo.
  8b. Local de saída preenchido e horário vazio: não vira linha nenhuma.
   9. **DEVE falhar** — T não recebe nada de U.
  9b. **DEVE falhar** — sem sessão nenhuma: 401 na agenda e na ficha de figurino.
  10. **DEVE falhar** — ficha de figurino de evento em que o talento não está escalado.
  11. Evento cancelado com ensaio: continua fora da agenda.
  12. Ensaio órfão (sem `parent_event_id`): não aparece em card nenhum.
  13. Logística salva pelo endpoint real e conferida por **conexão separada**.
 13b. A contagem de consultas da agenda **não cresce** com o número de escalações.
  14. Limpeza.

TUDO O QUE ESTE ARQUIVO TOCA É DESCARTÁVEL, e isso é uma decisão de segurança, não conveniência.
O `tasks.md` original mandava **assumir uma `EventRole` existente** com `talent_id IS NULL`, por
medo da regra da casa ("nunca semeie role com `character_name` inventado — o sync do Google apaga
a role e manda e-mail de remoção a gente de verdade"). Lido de novo, assumir linha de produção é o
caminho **mais** arriscado: escreve no espelho um talento de teste e depende da limpeza rodar para
desfazer. Aqui o evento, o cargo, o ensaio e os dois talentos nascem e morrem neste arquivo, com
prefixo próprio; o que a regra proíbe — pendurar cargo inventado em evento REAL — não acontece.

SEMEAR ENSAIO É `INSERT`, NUNCA `POST /api/events/<id>/ensaios`: aquele endpoint chama
`insert_event` e cria o evento **no Google Agenda da empresa**. As travas `_suppress_mail` /
`_suppress_calendar_invites` cobrem e-mail e convite, não isso. (Os dublês abaixo também cobrem,
mas a regra vale mesmo quando alguém apagar os dublês.)

ESCRITA SE CONFERE POR CONEXÃO SEPARADA (`_no_banco`): o autoflush da sessão do app mostra o que
ainda não foi commitado, e foi assim que o hotfix 257 passou verde com os anexos sumindo.

REQUISIÇÕES HTTP FICAM FORA DE `app.app_context()`: contexto persistente vaza a sessão entre
requisições e faz cenário de permissão passar por engano — e aqui três cenários DEVEM falhar.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"; $env:MANTO_SEM_THREADS = "1"
    .venv/Scripts/python.exe specs/302-portal-detalhes-do-evento/verify_302.py
"""

from __future__ import annotations

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
os.environ.setdefault("MAIL_SUPPRESS_SEND", "true")  # cinto, além do suspensório do localhost
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, event, text  # noqa: E402

from app import create_app, db, limiter, maps  # noqa: E402
from app import email_service as es  # noqa: E402
from app.calendar import routes as cal_routes  # noqa: E402
from app.calendar import service as cal_service  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import CalendarEvent, EventRole, Role, Talent, User  # noqa: E402

PREFIX = "__v302_"
SENHA = "verify-302-senha"
#: Local exclusivo do ensaio orfao — e o que permite reconhece-lo se ele vazar para um card.
LOCAL_ORFAO = f"{PREFIX}ORFAO — nao deve aparecer"

app = create_app()
app.config["TESTING"] = True
# Muitos logins: o "10 per minute" de /api/portal/auth/login estoura. `RATELIMIT_ENABLED` depois
# do `create_app` não desliga nada — o objeto sim.
limiter.enabled = False

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_externo = create_engine(os.environ["DATABASE_URL"], future=True)

# ── dublês: nada sai para o Google nem para o SMTP ───────────────────────────────────────────────
maps.cidade_do_endereco = lambda _e: (None, None)
cal_routes._fetch_travel_data = lambda _ev, _s: {}
cal_service.insert_event = lambda *a, **k: {"id": f"{PREFIX}g{uuid.uuid4().hex[:10]}"}
cal_service.update_event = lambda *a, **k: None
cal_service.delete_event = lambda *a, **k: None
cal_routes.insert_event = cal_service.insert_event

_emails: list[dict] = []
_send_real = es._send


def _fake_send(to: str, subject: str = "", body: str = "", html: str = "") -> bool:
    """Captura o e-mail em vez de enviá-lo — o cenário 6b lê o corpo."""
    _emails.append({"to": to, "subject": subject, "html": html})
    return True


es._send = _fake_send


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


def _login_staff(c, email: str) -> None:
    r = c.post("/api/auth/login", json={"email": email, "password": SENHA})
    _garante(r.status_code == 200, f"login de staff {email} → {r.status_code}")


def _agenda(email: str) -> dict:
    with app.test_client() as c:
        _login_talento(c, email)
        r = c.get("/api/portal/agenda")
        _garante(r.status_code == 200, f"agenda → {r.status_code}")
        return r.get_json()


def _item(agenda: dict, lista: str, event_id: int) -> dict:
    for it in agenda[lista]:
        if it["event_id"] == event_id:
            return it
    raise AssertionError(f"evento {event_id} não está em `{lista}`")


def _ausente(agenda: dict, event_id: int) -> None:
    for lista in ("pending_invites", "upcoming", "history"):
        for it in agenda.get(lista, []):
            _garante(it["event_id"] != event_id, f"evento {event_id} apareceu em `{lista}`")


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
    db.session.commit()
    return t


def _staff(sufixo: str, *papeis: str) -> User:
    user = User(
        name=f"{PREFIX}{sufixo}",
        email=f"{PREFIX}{sufixo}@manto.local",
        is_active=True,
        has_access=True,
    )
    user.set_password(SENHA)
    for p in papeis:
        user.roles.append(Role.query.filter_by(name=p).one())
    db.session.add(user)
    db.session.commit()
    return user


def _evento(
    sufixo: str,
    *,
    dias: int = 30,
    horas: int = 4,
    talent_id: int | None = None,
    role_type: str = "character",
    invite_status: str | None = "accepted",
    makeup_time: str | None = None,
    makeup_location: str | None = None,
    departure_time: str | None = None,
    departure_location: str | None = None,
    cancelado: bool = False,
) -> CalendarEvent:
    inicio = datetime.combine(
        now_sp().date() + timedelta(days=dias), datetime.min.time()
    ).replace(hour=20)
    ev = CalendarEvent(
        title=f"{PREFIX}{sufixo}",
        event_type="SHOW",
        start_at=inicio,
        end_at=inicio + timedelta(hours=horas),
        google_event_id=f"{PREFIX}{uuid.uuid4().hex[:10]}",
        source="google_calendar",
        location=f"{PREFIX}Buffet, São Paulo",
        makeup_time=makeup_time,
        makeup_location=makeup_location,
        departure_time=departure_time,
        departure_location=departure_location,
        cancelled_at=datetime.utcnow() if cancelado else None,
    )
    db.session.add(ev)
    db.session.flush()
    if talent_id is not None:
        db.session.add(
            EventRole(
                event_id=ev.id,
                character_name=f"{PREFIX}Coordenador" if role_type == "extra" else f"{PREFIX}Bluey",
                role_type=role_type,
                talent_id=talent_id,
                invite_status=invite_status,
                cache_value=300,
            )
        )
    db.session.commit()
    return ev


def _ensaio(pai: CalendarEvent, *, dias: int, hora: int = 9, local: str | None = None) -> CalendarEvent:
    """Ensaio é evento-filho, gravado DIRETO — nunca pelo endpoint (ver docstring do módulo)."""
    inicio = datetime.combine(
        now_sp().date() + timedelta(days=dias), datetime.min.time()
    ).replace(hour=hora)
    en = CalendarEvent(
        title=f"{PREFIX}ensaio",
        event_type="ENSAIO",
        parent_event_id=pai.id if pai is not None else None,
        start_at=inicio,
        end_at=inicio + timedelta(hours=3),
        google_event_id=f"{PREFIX}{uuid.uuid4().hex[:10]}",
        source="platform",
        location=local or f"{PREFIX}R. Olga Camelini, 147",
        description="Evento em: endereço do show — NÃO deve aparecer para o artista",
    )
    db.session.add(en)
    db.session.commit()
    return en


def preparar() -> None:
    limpar()
    t = _talento("T")
    u = _talento("U")
    staff = _staff("staff", RoleName.CASTING)
    estado.update({"t": t.id, "u": u.id, "t_email": t.email_contact, "u_email": u.email_contact})
    estado["staff_email"] = staff.email

    estado["ev_base"] = _evento("base", dias=30, talent_id=t.id).id

    ev_ensaio = _evento("ensaio", dias=31, talent_id=t.id)
    estado["ev_ensaio"] = ev_ensaio.id
    estado["en_1"] = _ensaio(ev_ensaio, dias=28).id

    ev_dois = _evento("dois", dias=32, talent_id=t.id)
    estado["ev_dois"] = ev_dois.id
    # Semeados FORA DE ORDEM de propósito: a relação `ensaios` não tem `order_by`, e sem ordenar
    # na consulta o Postgres devolve em ordem arbitrária.
    estado["en_tarde"] = _ensaio(ev_dois, dias=29, hora=15).id
    estado["en_cedo"] = _ensaio(ev_dois, dias=27, hora=9).id

    # Termina 00:00 do dia seguinte (20:00 + 4h).
    estado["ev_meianoite"] = _evento("meianoite", dias=33, horas=4, talent_id=t.id).id

    ev_passado = _evento("ensaiopassado", dias=34, talent_id=t.id)
    estado["ev_ensaio_passado"] = ev_passado.id
    estado["en_passado"] = _ensaio(ev_passado, dias=-3).id

    estado["ev_maq"] = _evento(
        "maq", dias=35, talent_id=t.id, makeup_time="14:00", makeup_location="manto",
        departure_time="15:30",  # sem local: tem de cair no padrão "Manto Produções"
    ).id
    estado["ev_livre"] = _evento(
        "livre", dias=36, talent_id=t.id, makeup_time="10:00",
        makeup_location="Rua das Flores, 20 - Pinheiros",
    ).id
    # Local de saída sem horário — é o resíduo do formulário, que não pode virar linha.
    estado["ev_soloc"] = _evento(
        "soloc", dias=37, talent_id=t.id, departure_location="Manto Produções"
    ).id

    estado["ev_extra"] = _evento("extra", dias=38, talent_id=t.id, role_type="extra",
                                 makeup_time="09:00", makeup_location="manto").id

    ev_convite = _evento("convite", dias=39, talent_id=t.id, invite_status="pending")
    estado["ev_convite"] = ev_convite.id
    estado["en_convite"] = _ensaio(ev_convite, dias=36).id

    ev_hist = _evento("historico", dias=-20, talent_id=t.id)
    estado["ev_hist"] = ev_hist.id
    estado["en_hist"] = _ensaio(ev_hist, dias=-23).id

    ev_cancel = _evento("cancelado", dias=40, talent_id=t.id, cancelado=True)
    estado["ev_cancelado"] = ev_cancel.id
    _ensaio(ev_cancel, dias=37)

    # Ensaio órfão: sem pai, não pertence a evento nenhum.
    estado["en_orfao"] = _ensaio(None, dias=26, local=LOCAL_ORFAO).id

    estado["ev_u"] = _evento("doU", dias=41, talent_id=u.id).id
    estado["ev_logistica"] = _evento("logistica", dias=42, talent_id=t.id).id


def limpar() -> None:
    ids = [
        r[0]
        for r in db.session.query(CalendarEvent.id)
        .filter(CalendarEvent.title.like(f"{PREFIX}%"))
        .all()
    ]
    if ids:
        EventRole.query.filter(EventRole.event_id.in_(ids)).delete(synchronize_session=False)
        # Os filhos primeiro: `parent_event_id` é FK para a própria tabela.
        CalendarEvent.query.filter(CalendarEvent.parent_event_id.in_(ids)).delete(
            synchronize_session=False
        )
        CalendarEvent.query.filter(CalendarEvent.id.in_(ids)).delete(synchronize_session=False)
    Talent.query.filter(Talent.full_name.like(f"{PREFIX}%")).delete(synchronize_session=False)
    for user in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        user.roles.clear()  # a associação vem antes do usuário
        db.session.delete(user)
    db.session.commit()


# ── cenários ─────────────────────────────────────────────────────────────────────────────────────


def _bloco_existe(agenda: dict) -> None:
    """Controle contra passagem a vazio.

    Os cenários que afirmam "aqui NÃO tem bloco" são verdadeiros por acidente enquanto o bloco não
    existe em lugar nenhum — passariam verdes num código que não faz nada. Este controle exige que
    o evento com ensaio futuro TENHA bloco, e por isso eles só passam quando a feature existe e a
    regra de exclusão funciona.
    """
    it = _item(agenda, "upcoming", estado["ev_ensaio"])
    _garante(
        (it.get("before_event") or {}).get("rehearsals"),
        "o evento de controle (ensaio futuro) está sem bloco — os cenários de ausência abaixo "
        "estariam passando a vazio",
    )


def cen_01_faixa_horaria() -> None:
    ag = _agenda(estado["t_email"])
    it = _item(ag, "upcoming", estado["ev_base"])
    _garante(bool(it.get("start_at")) and bool(it.get("end_at")), "faltou start_at/end_at no item")
    _garante(
        it["end_at"] > it["start_at"], f"end_at {it['end_at']} não é depois de {it['start_at']}"
    )
    conv = _item(ag, "pending_invites", estado["ev_convite"])
    _garante(bool(conv.get("end_at")), "convite pendente veio sem end_at")
    hist = _item(ag, "history", estado["ev_hist"])
    _garante(bool(hist.get("end_at")), "item do histórico veio sem end_at")


def cen_02_um_ensaio() -> None:
    it = _item(_agenda(estado["t_email"]), "upcoming", estado["ev_ensaio"])
    bloco = it.get("before_event")
    _garante(bloco is not None, "before_event veio nulo num evento COM ensaio")
    ensaios = bloco.get("rehearsals") or []
    _garante(len(ensaios) == 1, f"esperava 1 ensaio, veio {len(ensaios)}")
    en = ensaios[0]
    _garante(bool(en.get("start_at")) and bool(en.get("end_at")), "ensaio sem horário")
    _garante(PREFIX in (en.get("location") or ""), f"ensaio sem local: {en.get('location')!r}")
    _garante(
        "description" not in en,
        "o ensaio veio com `description` — o campo guarda ENDEREÇO DO SHOW, não observação (R9)",
    )


def cen_03_dois_ensaios_ordenados() -> None:
    it = _item(_agenda(estado["t_email"]), "upcoming", estado["ev_dois"])
    ensaios = (it.get("before_event") or {}).get("rehearsals") or []
    _garante(len(ensaios) == 2, f"esperava 2 ensaios, veio {len(ensaios)} — a lista foi limitada?")
    _garante(
        ensaios[0]["start_at"] < ensaios[1]["start_at"],
        "os dois ensaios vieram fora de ordem; a relação não tem `order_by` (R12)",
    )


def cen_04_sem_nada() -> None:
    ag = _agenda(estado["t_email"])
    _bloco_existe(ag)
    it = _item(ag, "upcoming", estado["ev_base"])
    _garante(
        it.get("before_event") is None,
        f"before_event devia ser None num evento sem nada, veio {it.get('before_event')!r}",
    )


def cen_04b_vira_meia_noite() -> None:
    it = _item(_agenda(estado["t_email"]), "upcoming", estado["ev_meianoite"])
    _garante(
        it["start_at"][:10] != it["end_at"][:10],
        "o evento de virada devia ter datas diferentes em start_at e end_at",
    )


def cen_04c_ensaio_ja_realizado() -> None:
    ag = _agenda(estado["t_email"])
    _bloco_existe(ag)
    it = _item(ag, "upcoming", estado["ev_ensaio_passado"])
    bloco = it.get("before_event")
    ensaios = (bloco or {}).get("rehearsals") or []
    _garante(
        not ensaios,
        "o ensaio JÁ REALIZADO continua no bloco de preparação — a janela 'ensaio passado, show "
        "futuro' existe sempre, porque o ensaio cai 2 a 4 dias antes (FR-004a)",
    )
    _garante(bloco is None, "sem ensaio e sem logística, o bloco devia ser None")


def cen_05_maquiagem_traduzida() -> None:
    it = _item(_agenda(estado["t_email"]), "upcoming", estado["ev_maq"])
    bloco = it.get("before_event") or {}
    maq = bloco.get("makeup")
    _garante(maq is not None, "faltou o bloco de maquiagem")
    _garante(maq["time"] == "14:00", f"horário de maquiagem errado: {maq}")
    _garante(
        maq["location"] == "Manto Produções",
        f"o código do banco vazou para o artista: {maq['location']!r}",
    )
    saida = bloco.get("departure")
    _garante(saida is not None, "faltou o bloco de saída")
    _garante(
        saida["location"] == "Manto Produções",
        f"saída sem local devia cair no padrão, veio {saida['location']!r}",
    )


def cen_05b_maquiagem_endereco_livre() -> None:
    it = _item(_agenda(estado["t_email"]), "upcoming", estado["ev_livre"])
    maq = (it.get("before_event") or {}).get("makeup") or {}
    _garante(
        maq.get("location") == "Rua das Flores, 20 - Pinheiros",
        f"endereço digitado à mão devia sair verbatim, veio {maq.get('location')!r}",
    )


def cen_06_role_type() -> None:
    it = _item(_agenda(estado["t_email"]), "upcoming", estado["ev_extra"])
    _garante(
        it.get("role_type") == "extra",
        f"o payload precisa dizer que a vaga é cargo, veio {it.get('role_type')!r}",
    )
    base = _item(_agenda(estado["t_email"]), "upcoming", estado["ev_base"])
    _garante(base.get("role_type") == "character", f"vaga de personagem: {base.get('role_type')!r}")


def cen_06b_email_de_convite() -> None:
    _emails.clear()
    with app.app_context():
        role = EventRole.query.filter_by(event_id=estado["ev_extra"]).one()
        es.send_invite_email(role)
    _garante(len(_emails) == 1, f"esperava 1 e-mail capturado, veio {len(_emails)}")
    html = _emails[0]["html"]
    _garante("Função" in html, "o e-mail de convite de um cargo não diz 'Função'")
    _garante(
        "Personagem" not in html,
        "o e-mail ainda chama um Coordenador de 'Personagem' (FR-012a)",
    )
    # A asserção tem de olhar para a LINHA da maquiagem, não para o documento. `"Manto Produções"
    # in html` é verdade sempre — está no `<title>` e no rodapé de todo e-mail (`_html_wrap`) — e
    # `">manto<"` nunca casa, porque `_info_row` renderiza `>09:00 — manto</td>`, com a hora
    # colada. As duas versões anteriores desta linha passavam verdes com a tradução removida.
    _garante(
        "— Manto Produções<" in html,
        f"o e-mail não traduziu o local da maquiagem na linha dela. HTML: {html[:400]!r}",
    )
    _garante(
        "— manto<" not in html,
        "o e-mail ainda manda o código `manto` cru como local de maquiagem",
    )


def cen_06c_convite_com_ensaio() -> None:
    it = _item(_agenda(estado["t_email"]), "pending_invites", estado["ev_convite"])
    ensaios = (it.get("before_event") or {}).get("rehearsals") or []
    _garante(
        len(ensaios) == 1,
        "o card de CONVITE não traz o ensaio — é onde a informação muda a decisão (FR-009a)",
    )


def cen_07_historico_sem_ensaio() -> None:
    ag = _agenda(estado["t_email"])
    _bloco_existe(ag)
    it = _item(ag, "history", estado["ev_hist"])
    _garante(
        it.get("before_event") is None,
        f"o item do histórico trouxe bloco de preparação: {it.get('before_event')!r}",
    )


def cen_08_history_continua_no_payload() -> None:
    ag = _agenda(estado["t_email"])
    _garante(
        "history" in ag,
        "a chave `history` sumiu do payload da agenda — o bundle velho faz `history.map(...)` e "
        "a tela do artista fica branca (FR-013a)",
    )
    _garante(any(i["event_id"] == estado["ev_hist"] for i in ag["history"]), "histórico vazio")
    with app.test_client() as c:
        _login_talento(c, estado["t_email"])
        r = c.get("/api/portal/historico")
    _garante(r.status_code == 200, f"histórico → {r.status_code}")
    corpo = r.get_json()
    _garante("items" in corpo and "totals" in corpo, "o histórico perdeu items/totals")
    _garante(
        {"paid", "pending", "overall", "count"} <= set(corpo["totals"]),
        f"totais do histórico mudaram: {corpo['totals']}",
    )


def cen_08b_local_sem_horario() -> None:
    ag = _agenda(estado["t_email"])
    _bloco_existe(ag)
    it = _item(ag, "upcoming", estado["ev_soloc"])
    bloco = it.get("before_event")
    _garante(
        bloco is None,
        "local de saída SEM horário virou bloco — é resíduo do formulário, que pré-preenche o "
        f"campo; a hora é que faz a linha existir (FR-006a). Veio {bloco!r}",
    )


def cen_09_t_nao_ve_u() -> None:
    ag = _agenda(estado["t_email"])
    _ausente(ag, estado["ev_u"])
    ag_u = _agenda(estado["u_email"])
    for eid in ("ev_base", "ev_ensaio", "ev_maq", "ev_convite", "ev_hist"):
        _ausente(ag_u, estado[eid])


def cen_09b_sem_sessao() -> None:
    with app.test_client() as c:
        r = c.get("/api/portal/agenda")
        _garante(r.status_code == 401, f"agenda sem sessão → {r.status_code}, esperado 401")
        r = c.get(f"/api/portal/events/{estado['ev_base']}/figurino")
        _garante(r.status_code == 401, f"figurino sem sessão → {r.status_code}, esperado 401")


def cen_10_figurino_alheio() -> None:
    with app.test_client() as c:
        _login_talento(c, estado["u_email"])
        r = c.get(f"/api/portal/events/{estado['ev_base']}/figurino")
    _garante(
        r.status_code in (403, 404),
        f"U abriu a ficha de um evento em que não está escalado → {r.status_code}",
    )


def cen_11_evento_cancelado() -> None:
    _ausente(_agenda(estado["t_email"]), estado["ev_cancelado"])


def cen_12_ensaio_orfao() -> None:
    """O ensaio sem `parent_event_id` não pertence a evento nenhum e não pode aparecer.

    A primeira versão deste cenário comparava `it["event_id"]` (o id do SHOW) com o id do ensaio
    órfão — nunca iguais, então a asserção não podia falhar. E o órfão nascia com o mesmo
    `location` de todos os outros ensaios, o que o tornava indistinguível mesmo numa comparação
    direta. Agora ele tem **local próprio**, e o que se procura é esse local em qualquer bloco.

    Honestidade sobre o alcance: com a consulta atual (`parent_event_id.in_(...)`) um órfão não
    tem como entrar, então este cenário **não falha hoje por mais errado que o resto fique**. Ele
    é uma trava para a mudança que se pode imaginar — alguém trocar o filtro por `event_type ==
    "ENSAIO"` e uma janela de datas, o que traria todo ensaio solto para o card de todo mundo.
    """
    ag = _agenda(estado["t_email"])
    _ausente(ag, estado["en_orfao"])
    _bloco_existe(ag)  # sem bloco nenhum, a varredura abaixo não prova nada
    for lista in ("pending_invites", "upcoming", "history"):
        for it in ag[lista]:
            for en in (it.get("before_event") or {}).get("rehearsals") or []:
                _garante(
                    en.get("location") != LOCAL_ORFAO,
                    f"o ensaio órfão apareceu no card do evento {it['event_id']}",
                )


def cen_13_logistica_persiste() -> None:
    eid = estado["ev_logistica"]
    with app.test_client() as c:
        _login_staff(c, estado["staff_email"])
        r = c.patch(
            f"/api/events/{eid}/logistics",
            json={
                "makeup_time": "13:00",
                "makeup_location": "local",
                "departure_time": "14:15",
                "departure_location": "",
            },
        )
    _garante(r.status_code == 200, f"salvar logística → {r.status_code}")
    # Conexão separada: o autoflush da sessão do app mostraria isto mesmo sem commit (hotfix 257).
    linha = _no_banco(
        "SELECT makeup_time, makeup_location, departure_time FROM calendar_events WHERE id = :i",
        i=eid,
    )[0]
    _garante(
        linha[0] == "13:00" and linha[1] == "local" and linha[2] == "14:15",
        f"a logística não persistiu: {linha}",
    )
    it = _item(_agenda(estado["t_email"]), "upcoming", eid)
    bloco = it.get("before_event") or {}
    _garante(
        (bloco.get("makeup") or {}).get("location") == "No local do evento",
        f"o preset `local` não foi traduzido: {bloco.get('makeup')!r}",
    )


def cen_13b_consulta_nao_cresce() -> None:
    """A agenda de quem tem 13 escalações não pode custar mais consultas que a de quem tem 1.

    **Exceção declarada à regra do módulo**: este é o único cenário que roda as requisições
    DENTRO de `app.app_context()`, porque precisa de `db.engine` para escutar as consultas. A
    regra existe para cenários de **permissão** (contexto persistente vaza a sessão entre
    requisições e faz o cenário passar por engano); aqui não se testa permissão nenhuma, e cada
    `_medir` abre o seu próprio `test_client` com login próprio.
    """
    contagem = {"n": 0}

    def _conta(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        contagem["n"] += 1

    def _medir(email: str) -> int:
        with app.test_client() as c:
            _login_talento(c, email)
            contagem["n"] = 0
            event.listen(db.engine, "before_cursor_execute", _conta)
            try:
                r = c.get("/api/portal/agenda")
            finally:
                event.remove(db.engine, "before_cursor_execute", _conta)
        _garante(r.status_code == 200, f"agenda → {r.status_code}")
        return contagem["n"]

    with app.app_context():
        muitos = _medir(estado["t_email"])
        poucos = _medir(estado["u_email"])
    _garante(
        muitos <= poucos + 2,
        f"a agenda custa {muitos} consultas para 13 escalações e {poucos} para 1 — está crescendo "
        "por item (N+1). O bloco tem de vir de UMA consulta agregada (R7)",
    )


def cen_14_limpeza() -> None:
    limpar()
    _garante(
        CalendarEvent.query.filter(CalendarEvent.title.like(f"{PREFIX}%")).count() == 0,
        "evento descartável sobrou",
    )
    _garante(
        Talent.query.filter(Talent.full_name.like(f"{PREFIX}%")).count() == 0,
        "talento descartável sobrou",
    )
    _garante(
        User.query.filter(User.email.like(f"{PREFIX}%")).count() == 0, "usuário descartável sobrou"
    )


def main() -> int:
    print("Feature 302 — o que o artista vê do evento no Portal")
    with app.app_context():
        preparar()
    try:
        cenario("1. faixa horária: start_at e end_at nas três listas", cen_01_faixa_horaria)
        cenario("2. show com um ensaio: data, hora e local no bloco", cen_02_um_ensaio)
        cenario("3. show com DOIS ensaios: os dois, em ordem", cen_03_dois_ensaios_ordenados)
        cenario("4. evento sem nada: before_event é None", cen_04_sem_nada)
        cenario("4b. evento que termina no dia seguinte", cen_04b_vira_meia_noite)
        cenario("4c. ensaio já realizado sai do bloco", cen_04c_ensaio_ja_realizado)
        cenario("5. maquiagem 'manto' vira 'Manto Produções'; saída cai no padrão", cen_05_maquiagem_traduzida)
        cenario("5b. endereço de maquiagem digitado sai verbatim", cen_05b_maquiagem_endereco_livre)
        cenario("6. role_type no payload distingue cargo de personagem", cen_06_role_type)
        cenario("6b. e-mail de convite diz 'Função' e traduz o local", cen_06b_email_de_convite)
        cenario("6c. convite pendente traz o bloco com o ensaio", cen_06c_convite_com_ensaio)
        cenario("7. item do histórico não traz ensaio", cen_07_historico_sem_ensaio)
        cenario("8. `history` continua no payload; histórico completo", cen_08_history_continua_no_payload)
        cenario("8b. local de saída sem horário não vira linha", cen_08b_local_sem_horario)
        cenario("9. **deve falhar** T não vê nada de U, nem U de T", cen_09_t_nao_ve_u)
        cenario("9b. **deve falhar** sem sessão: 401 na agenda e no figurino", cen_09b_sem_sessao)
        cenario("10. **deve falhar** ficha de figurino de evento alheio", cen_10_figurino_alheio)
        cenario("11. evento cancelado continua fora da agenda", cen_11_evento_cancelado)
        cenario("12. ensaio órfão não aparece em card nenhum", cen_12_ensaio_orfao)
        cenario("13. logística salva pelo endpoint persiste (conexão separada)", cen_13_logistica_persiste)
        cenario("13b. a consulta da agenda não cresce com o número de escalações", cen_13b_consulta_nao_cresce)
    finally:
        with app.app_context():
            cenario("14. limpeza", cen_14_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"{ok}/{len(resultados)} OK")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
