"""Verificação do hotfix 356 — o cachê do elenco não some nem muda por fora do card do Casting.

Cenários (spec §Verificação). Os marcados DEVEM falhar no código de antes do 356:
 1. Comercial salva o "Editar tudo" como a tela de hoje manda (cachê `null` em toda vaga): os cachês
    ficam como estavam.                                                    (DEVE falhar antes do 356)
 2. Comercial manda um cachê digitado pela API: ignorado, sem linha no log. (DEVE falhar antes do 356)
 3. Superadmin com "Ver como Comercial" salva com cachê `null`: os cachês ficam.
 4. Superadmin sobe um cachê acima do teto pelo formulário: grava, vira teto autorizado da vaga com
    autor, e o log tem a autorização e o "Atualizou cachê … (formulário completo)".
 5. Comercial+Casting acima do teto pelo formulário: volta ao limite (nada muda, nenhuma linha);
    dentro do limite: grava com linha no log.                              (DEVE falhar antes do 356)
 6. O Casting salva pelo card DEPOIS de o formulário abrir; o formulário salvo sem a chave
    `cache_value` (campo intocado) não desfaz o valor do card.
 7. Formulário reenviando os mesmos valores: nenhuma linha nova de cachê no log.
 8. Comercial lê o evento: o elenco vem sem cachê (a premissa da tela esconder o campo).
 9. Card do Casting só com cachê novo: "Atribuído em" fica a data da escalação.
                                                                           (DEVE falhar antes do 356)
10. Card do Casting trocando a pessoa: "Atribuído em" vira hoje.
11. Card em vaga antiga com pessoa e sem data: ganha a data no primeiro salvar.
12. Limpeza.

Dublês: Google Agenda (`service.update/insert/delete_event` no-op), Maps (no-op), e-mail
(`MAIL_SUPPRESS_SEND` conferido no início; espião de `send_removal_email`). Eventos descartáveis
marcados pelo `google_event_id` com o prefixo, título com os mesmos personagens das vagas (é dele
que o sistema conta o elenco). Talentos: os ativos do espelho, só nesses eventos de 2 meses à
frente. Requisições HTTP FORA do `app_context`; toda escrita conferida por conexão separada.

Rodar (PowerShell, a partir do worktree)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
    C:\\Users\\schim\\Desktop\\Manto_Platform\\.venv\\Scripts\\python.exe specs\\356-cache-nao-se-perde\\verify_356.py
"""

from __future__ import annotations

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

from app import create_app, db, email_service, limiter, maps  # noqa: E402
from app.calendar import casting_ops  # noqa: E402
from app.calendar import routes as cal_routes  # noqa: E402
from app.calendar import service as cal_service  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import CalendarEvent, EventRole, Role, Talent, User  # noqa: E402

PREFIX = "__v356_"
SENHA = "verify-356-senha"
TITULO = "(R&I) FLORISTA + RAPOSA + CERVO"
ESCALADO_EM = datetime(2026, 11, 1, 10, 0)

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_externo = create_engine(os.environ["DATABASE_URL"], future=True)

# ── dublês ──────────────────────────────────────────────────────────────────────────────────────
maps.cidade_do_endereco = lambda _e: (None, None)
cal_routes._fetch_travel_data = lambda _ev, _s: {}
cal_routes._lookup_sp_status = lambda _loc: False
cal_routes._mark_talents_worked = lambda: None
cal_service.insert_event = lambda *a, **k: {"id": f"{PREFIX}g{uuid.uuid4().hex[:10]}"}
cal_service.update_event = lambda *a, **k: None
cal_service.delete_event = lambda *a, **k: None
cal_routes.insert_event = cal_service.insert_event

remocoes: list[str] = []


def _espiao_remocao(_talent, _event, nome, *_a, **_k):
    remocoes.append(nome)
    return True


email_service.send_removal_email = _espiao_remocao
casting_ops.send_removal_email = _espiao_remocao


# ── utilitários ─────────────────────────────────────────────────────────────────────────────────


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
    except Exception as exc:  # noqa: BLE001 — o relatório precisa de todos os cenários
        with app.app_context():
            db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _email(chave: str) -> str:
    return f"{PREFIX}{chave}@manto.local"


def _usuario(chave: str, *papeis: str) -> int:
    user = User(name=f"{PREFIX}{chave}", email=_email(chave), is_active=True, has_access=True)
    user.set_password(SENHA)
    for p in papeis:
        user.roles.append(Role.query.filter_by(name=p).one())
    db.session.add(user)
    db.session.commit()
    return user.id


def _cliente(chave: str):
    """Cliente logado pela API (fora do app_context)."""
    c = app.test_client()
    r = c.post("/api/auth/login", json={"email": _email(chave), "password": SENHA})
    _garante(r.status_code == 200, f"login {chave} → {r.status_code}")
    return c


def _evento() -> int:
    """Evento da plataforma com as três vagas do título, já escaladas e com cachê (o 1516 em miniatura).

    Florista e Raposa com teto de orçamento (600 e 450); Cervo sem teto. Escalados em 01/11.
    """
    inicio = datetime.combine(now_sp().date() + timedelta(days=60), datetime.min.time()).replace(
        hour=15
    )
    ev = CalendarEvent(
        title=TITULO,
        event_type="R&I",
        start_at=inicio,
        end_at=inicio + timedelta(hours=2),
        google_event_id=f"{PREFIX}{uuid.uuid4().hex[:10]}",
        source="platform",
        location="Rua Teste 1, São Paulo",
        is_outside_sp=False,
        sale_value=Decimal("1000"),
        sale_value_gross=Decimal("1000"),
        seller_id=estado["com"],
    )
    db.session.add(ev)
    db.session.flush()
    t = estado["t"]
    for nome, tid, cache, cap in (
        ("Florista", t[0], "600", "600"),
        ("Raposa", t[1], "450", "450"),
        ("Cervo", t[2], "450", None),
    ):
        db.session.add(
            EventRole(
                event_id=ev.id,
                character_name=nome,
                role_type="character",
                talent_id=tid,
                cache_value=Decimal(cache),
                cache_cap=Decimal(cap) if cap else None,
                assigned_at=ESCALADO_EM,
                invite_status="pending",
            )
        )
    db.session.commit()
    return ev.id


def _vagas(eid: int) -> dict:
    linhas = _no_banco(
        "SELECT id, character_name, talent_id, cache_value, teto_autorizado, teto_autorizado_por, "
        "assigned_at FROM event_roles WHERE event_id = :i AND role_type = 'character' ORDER BY id",
        i=eid,
    )
    return {v.character_name: v for v in linhas}


def _caches(eid: int) -> dict[str, Decimal | None]:
    return {nome: v.cache_value for nome, v in _vagas(eid).items()}


def _logs_de_cache(eid: int) -> list[str]:
    return [
        r[0]
        for r in _no_banco(
            "SELECT message FROM event_logs WHERE event_id = :i AND "
            "(message LIKE 'Atualizou cachê%' OR message LIKE 'Limite da vaga%') ORDER BY id",
            i=eid,
        )
    ]


def _personagens(eid: int, *, com_chave: bool = True, **troca: dict) -> list[dict]:
    """O que o formulário manda por personagem. `com_chave=True` imita a tela de antes do 356 (manda
    o cachê sempre — `null` para quem não o vê); `False`, a tela nova com o campo intocado."""
    linhas = []
    for nome, v in _vagas(eid).items():
        linha = {
            "role_id": v.id,
            "name": nome,
            "figurino_sheet_id": None,
            "needs_makeup": False,
            "is_singer": False,
            "talent_id": v.talent_id,
        }
        if com_chave:
            linha["cache_value"] = None
        linha.update(troca.get(nome, {}))
        linhas.append(linha)
    return linhas


def _corpo(eid: int, characters: list[dict]) -> dict:
    with app.app_context():
        ev = CalendarEvent.query.get(eid)
        return {
            "title": ev.title,
            "event_type": ev.event_type,
            "date": ev.start_at.date().isoformat(),
            "start": ev.start_at.strftime("%H:%M"),
            "end": ev.end_at.strftime("%H:%M"),
            "location": ev.location or "",
            "description": ev.description or "",
            "needs_rehearsal": bool(ev.needs_rehearsal),
            "sale_value": float(ev.sale_value),
            "sale_value_gross": float(ev.sale_value_gross),
            "transport_value": 0,
            "acrescimo_value": 0,
            "with_invoice": False,
            "is_cortesia_permuta": False,
            "seller_id": ev.seller_id,
            "sale_date": None,
            "payment_method": None,
            "payment_installments": None,
            "payment_due_date": None,
            "characters": characters,
            "clients": [],
        }


def _editar(cliente, eid: int, characters: list[dict], quem: str) -> None:
    r = cliente.patch(f"/api/events/{eid}", json=_corpo(eid, characters))
    _garante(
        r.status_code == 200,
        f"PATCH /api/events/{eid} ({quem}) → {r.status_code} {r.get_data(as_text=True)[:300]}",
    )


def _assign(chave: str, role_id: int, talent_id: int | None, cache) -> None:
    r = _cliente(chave).post(
        f"/api/roles/{role_id}/assign", json={"talent_id": talent_id, "cache_value": cache}
    )
    _garante(
        r.status_code == 200, f"assign ({chave}) → {r.status_code} {r.get_data(as_text=True)[:200]}"
    )


# ── preparação e limpeza ────────────────────────────────────────────────────────────────────────


def limpar() -> None:
    ids = [
        r[0]
        for r in _no_banco(
            "SELECT id FROM calendar_events WHERE google_event_id LIKE :p", p=f"{PREFIX}%"
        )
    ]
    for eid in ids:
        db.session.execute(
            text(
                "DELETE FROM notifications WHERE entity_type = 'calendar_event' AND entity_id = :i"
            ),
            {"i": eid},
        )
        for tabela in ("commission_payments", "event_logs", "event_roles", "event_clients"):
            db.session.execute(text(f"DELETE FROM {tabela} WHERE event_id = :i"), {"i": eid})
    db.session.commit()
    for eid in ids:
        db.session.execute(text("DELETE FROM calendar_events WHERE id = :i"), {"i": eid})
    db.session.commit()
    for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        db.session.execute(text("DELETE FROM notifications WHERE user_id = :u"), {"u": u.id})
        u.roles.clear()
        db.session.delete(u)
    db.session.commit()


def preparar() -> None:
    with app.app_context():
        _garante(
            app.config.get("MAIL_SUPPRESS_SEND") is True,
            "MAIL_SUPPRESS_SEND desligado — convite iria a talento real",
        )
        limpar()
        estado["sa"] = _usuario("sa", RoleName.SUPERADMIN)
        estado["com"] = _usuario("com", RoleName.COMERCIAL)
        estado["cast"] = _usuario("cast", RoleName.CASTING)
        estado["comcast"] = _usuario("comcast", RoleName.COMERCIAL, RoleName.CASTING)
        talentos = [
            t.id for t in Talent.query.filter_by(status="active").order_by(Talent.id).limit(4).all()
        ]
        _garante(len(talentos) == 4, "o espelho precisa de 4 talentos ativos")
        estado["t"] = talentos
        estado["ev"] = _evento()


ORIGINAL = {"Florista": Decimal("600.00"), "Raposa": Decimal("450.00"), "Cervo": Decimal("450.00")}


# ── cenários ────────────────────────────────────────────────────────────────────────────────────


def cen_01_comercial_nao_apaga() -> None:
    eid = estado["ev"]
    _editar(_cliente("com"), eid, _personagens(eid), "com")
    _garante(_caches(eid) == ORIGINAL, f"cachês depois da Comercial: {_caches(eid)}")


def cen_02_comercial_nao_grava() -> None:
    eid = estado["ev"]
    _editar(_cliente("com"), eid, _personagens(eid, Florista={"cache_value": 900}), "com")
    _garante(_caches(eid)["Florista"] == Decimal("600.00"), f"Florista {_caches(eid)['Florista']}")
    _garante(not _logs_de_cache(eid), f"log de cachê da Comercial: {_logs_de_cache(eid)}")


def cen_03_ver_como_comercial() -> None:
    eid = estado["ev"]
    c = _cliente("sa")
    r = c.post("/api/auth/impersonate", json={"role": "COMERCIAL"})
    _garante(r.status_code == 200, f"impersonate → {r.status_code}")
    _editar(c, eid, _personagens(eid), "sa como Comercial")
    _garante(_caches(eid) == ORIGINAL, f"cachês depois do Ver como: {_caches(eid)}")


def cen_04_superadmin_acima_do_teto() -> None:
    eid = estado["ev"]
    _editar(
        _cliente("sa"), eid, _personagens(eid, com_chave=False, Florista={"cache_value": 850}), "sa"
    )
    v = _vagas(eid)["Florista"]
    _garante(v.cache_value == Decimal("850.00"), f"Florista {v.cache_value}")
    _garante(v.teto_autorizado == Decimal("850.00"), f"teto autorizado {v.teto_autorizado}")
    _garante(v.teto_autorizado_por == estado["sa"], f"autor do teto {v.teto_autorizado_por}")
    logs = _logs_de_cache(eid)
    _garante(
        any(m == "Limite da vaga Florista autorizado em R$ 850,00" for m in logs), f"logs: {logs}"
    )
    _garante(
        any(
            m.startswith("Atualizou cachê de ")
            and " como Florista para 850.00R$ (acima do cap de 600.00R$" in m
            and m.endswith("(formulário completo)")
            for m in logs
        ),
        f"logs: {logs}",
    )
    outros = {k: c for k, c in _caches(eid).items() if k != "Florista"}
    _garante(
        outros == {"Raposa": Decimal("450.00"), "Cervo": Decimal("450.00")}, f"outros: {outros}"
    )


def cen_05_casting_pelo_formulario() -> None:
    eid = estado["ev"]
    antes = len(_logs_de_cache(eid))
    c = _cliente("comcast")
    _editar(c, eid, _personagens(eid, com_chave=False, Raposa={"cache_value": 900}), "comcast")
    _garante(
        _caches(eid)["Raposa"] == Decimal("450.00"),
        f"Raposa acima do teto: {_caches(eid)['Raposa']}",
    )
    _garante(
        len(_logs_de_cache(eid)) == antes, f"linha nova sem mudança: {_logs_de_cache(eid)[antes:]}"
    )
    _editar(c, eid, _personagens(eid, com_chave=False, Raposa={"cache_value": 400}), "comcast")
    _garante(
        _caches(eid)["Raposa"] == Decimal("400.00"),
        f"Raposa dentro do teto: {_caches(eid)['Raposa']}",
    )
    novas = _logs_de_cache(eid)[antes:]
    _garante(
        len(novas) == 1 and " como Raposa para 400.00R$ (formulário completo)" in novas[0],
        f"linhas novas: {novas}",
    )
    papel = _no_banco(
        "SELECT actor_role FROM event_logs WHERE event_id = :i AND message LIKE '%como Raposa para 400.00R$%'",
        i=eid,
    )
    _garante(papel and papel[0][0] == "Casting", f"papel no log: {papel}")


def cen_06_formulario_nao_desfaz_o_card() -> None:
    eid = estado["ev"]
    # A tela do formulário "abriu" com Cervo em 450; o Casting salva 500 pelo card; o formulário
    # é salvo com o campo do Cervo intocado (a tela nova não manda a chave).
    cervo = _vagas(eid)["Cervo"]
    _assign("cast", cervo.id, cervo.talent_id, 500)
    _editar(_cliente("sa"), eid, _personagens(eid, com_chave=False), "sa")
    _garante(_caches(eid)["Cervo"] == Decimal("500.00"), f"Cervo {_caches(eid)['Cervo']}")


def cen_07_reenvio_igual_sem_log() -> None:
    eid = estado["ev"]
    antes = len(_logs_de_cache(eid))
    iguais = {nome: {"cache_value": float(c)} for nome, c in _caches(eid).items()}
    _editar(_cliente("sa"), eid, _personagens(eid, **iguais), "sa")
    _garante(
        len(_logs_de_cache(eid)) == antes, f"linha nova sem mudança: {_logs_de_cache(eid)[antes:]}"
    )


def cen_08_comercial_le_sem_cache() -> None:
    r = _cliente("com").get(f"/api/events/{estado['ev']}")
    _garante(r.status_code == 200, f"GET → {r.status_code}")
    flags = r.get_json()["flags"]
    elenco = [p for p in r.get_json()["elenco"] if p["role_type"] == "character"]
    _garante(flags.get("show_casting") is False, f"show_casting {flags.get('show_casting')}")
    _garante(all(p.get("cache_value") is None for p in elenco), f"cachê vazou: {elenco}")


def cen_09_atribuido_em_fica() -> None:
    eid = estado["ev"]
    raposa = _vagas(eid)["Raposa"]
    _assign("cast", raposa.id, raposa.talent_id, 420)
    v = _vagas(eid)["Raposa"]
    _garante(v.cache_value == Decimal("420.00"), f"Raposa {v.cache_value}")
    _garante(v.assigned_at == ESCALADO_EM, f"Atribuído em virou {v.assigned_at}")


def cen_10_troca_de_pessoa_data_nova() -> None:
    eid = estado["ev"]
    raposa = _vagas(eid)["Raposa"]
    _assign("cast", raposa.id, estado["t"][3], 420)
    v = _vagas(eid)["Raposa"]
    _garante(v.talent_id == estado["t"][3], f"talento {v.talent_id}")
    # A coluna guarda o instante de agora (em UTC, na prática); basta ser depois da escalação antiga.
    _garante(
        v.assigned_at is not None and v.assigned_at > ESCALADO_EM + timedelta(days=1),
        f"Atribuído em {v.assigned_at}",
    )


def cen_11_vaga_antiga_ganha_data() -> None:
    eid = estado["ev"]
    cervo = _vagas(eid)["Cervo"]
    _escreve("UPDATE event_roles SET assigned_at = NULL WHERE id = :i", i=cervo.id)
    _assign("cast", cervo.id, cervo.talent_id, 500)
    v = _vagas(eid)["Cervo"]
    _garante(v.assigned_at is not None, "vaga com pessoa ficou sem data")


def cen_12_limpeza() -> None:
    with app.app_context():
        limpar()
    _garante(
        not _no_banco(
            "SELECT 1 FROM calendar_events WHERE google_event_id LIKE :p", p=f"{PREFIX}%"
        ),
        "evento sobrou",
    )
    _garante(
        not _no_banco("SELECT 1 FROM users WHERE email LIKE :p", p=f"{PREFIX}%"), "usuário sobrou"
    )


def main() -> int:
    print("Hotfix 356 — o cachê do elenco não some nem muda por fora do card do Casting")
    preparar()
    passos = [
        (
            "1. Comercial salva o Editar tudo: cachês ficam (DEVE falhar antes do 356)",
            cen_01_comercial_nao_apaga,
        ),
        (
            "2. Comercial manda cachê pela API: ignorado (DEVE falhar antes do 356)",
            cen_02_comercial_nao_grava,
        ),
        ("3. Superadmin vendo como Comercial: cachês ficam", cen_03_ver_como_comercial),
        (
            "4. Superadmin acima do teto pelo formulário: teto autorizado e log",
            cen_04_superadmin_acima_do_teto,
        ),
        (
            "5. Casting pelo formulário: limite do card e log (DEVE falhar antes do 356)",
            cen_05_casting_pelo_formulario,
        ),
        ("6. formulário com campo intocado não desfaz o card", cen_06_formulario_nao_desfaz_o_card),
        ("7. reenvio dos mesmos valores: nenhuma linha nova", cen_07_reenvio_igual_sem_log),
        ("8. Comercial lê o elenco sem cachê", cen_08_comercial_le_sem_cache),
        (
            "9. card com cachê novo: Atribuído em fica (DEVE falhar antes do 356)",
            cen_09_atribuido_em_fica,
        ),
        ("10. card trocando a pessoa: Atribuído em vira hoje", cen_10_troca_de_pessoa_data_nova),
        ("11. vaga antiga sem data ganha a data no salvar", cen_11_vaga_antiga_ganha_data),
    ]
    try:
        for nome, fn in passos:
            cenario(nome, fn)
    finally:
        if os.environ.get("VERIFY_356_MANTER") == "1":
            print("  (VERIFY_356_MANTER=1: limpeza pulada)", estado.get("ev"))
        else:
            cenario("12. limpeza", cen_12_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  ✗ {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
