"""verify_306b — o motivo do cancelamento editável por Superadmin e Comercial.

Roda contra o `manto_local` (DATABASE_URL de `.local-db-url`), com FLASK_ENV=development e
MANTO_SEM_THREADS=1. O estado cancelado nasce direto no banco (evento, motivo e as linhas de
histórico nos formatos que o cancelamento grava); só o endpoint novo é exercitado, então nada
toca o Google nem manda e-mail — e um disjuntor de rede garante isso. A conferência de escrita é
por uma conexão separada (`_externo`), não pela sessão do app.

Uso: `python specs/306b-motivo-editavel/verify_306b.py`. Saída 0 = todos os cenários OK.
"""

from __future__ import annotations

import os
import socket
import sys
import traceback
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):  # console do Windows em cp1252
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

AQUI = Path(__file__).resolve().parent
REPO_ROOT = AQUI.parents[1]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
os.environ.setdefault("MAIL_SUPPRESS_SEND", "true")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

# ── disjuntor de rede: nada sai desta máquina ──────────────────────────────────────────────────
_LOCAIS = {"127.0.0.1", "::1", "localhost"}
_connect_real = socket.socket.connect
rede_bloqueada: list[str] = []


def _connect_vigiado(self, endereco):
    host = str(endereco[0]) if isinstance(endereco, tuple) else str(endereco)
    if self.family in (socket.AF_INET, socket.AF_INET6) and host not in _LOCAIS:
        rede_bloqueada.append(host)
        raise OSError(f"verify_306b: conexão externa bloqueada ({host})")
    return _connect_real(self, endereco)


socket.socket.connect = _connect_vigiado

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.models import AuditLog, CalendarEvent, EventLog, Role, User  # noqa: E402

PREFIX = "__v306b_"
SENHA = "verify-306b-senha"
MARCADOR = "[TESTE verify 306b] pode apagar"
ROTA = "/api/events/{id}/motivo-cancelamento"
INICIO = datetime(2047, 3, 10, 15, 0)

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False

_externo = create_engine(os.environ["DATABASE_URL"], future=True)
resultados: list[tuple[str, bool, str]] = []
usuarios: dict[str, dict] = {}


# ── utilitários ────────────────────────────────────────────────────────────────────────────────
def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _no_banco(sql: str, **params) -> list:
    with _externo.connect() as conn:
        return list(conn.execute(text(sql), params))


def cenario(num: str, nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((f"{num}. {nome}", True, ""))
        print(f"  OK     {num}. {nome}", flush=True)
    except Exception as exc:  # noqa: BLE001 — o placar registra qualquer falha
        detalhe = f"{type(exc).__name__}: {exc}"
        resultados.append((f"{num}. {nome}", False, detalhe))
        print(f"  FALHA  {num}. {nome}: {detalhe}", flush=True)
        if not isinstance(exc, AssertionError):
            traceback.print_exc()


def _usuario(apelido: str, *papeis: str) -> None:
    email = f"{PREFIX}{apelido}@manto.local"
    with app.app_context():
        user = User(name=f"{PREFIX}{apelido}", email=email, is_active=True, has_access=True)
        user.set_password(SENHA)
        for p in papeis:
            user.roles.append(Role.query.filter_by(name=p).one())
        db.session.add(user)
        db.session.commit()
        usuarios[apelido] = {"id": user.id, "email": email}


def _cliente(apelido: str):
    c = app.test_client()
    r = c.post("/api/auth/login", json={"email": usuarios[apelido]["email"], "password": SENHA})
    _garante(r.status_code == 200, f"login de {apelido} → {r.status_code}")
    return c


def _erro(r) -> dict:
    return (r.get_json(silent=True) or {}).get("error") or {}


def _evento(rotulo: str, *, motivo: str | None, lider: int | None = None, dias: int = 0) -> int:
    """Evento de teste; com `motivo`, já cancelado (sem `event_cancellations`: o motivo é do evento)."""
    with app.app_context():
        ev = CalendarEvent(
            title=f"(CORP) V306B {rotulo}",
            google_event_id=f"v306b-{uuid.uuid4().hex[:12]}",
            event_type="CORP",
            start_at=INICIO + timedelta(days=dias),
            end_at=INICIO + timedelta(days=dias, hours=3),
            location="Rua V306B, 1",
            description=MARCADOR,
            group_leader_id=lider,
        )
        if motivo is not None:
            ev.cancelled_at = datetime(2047, 3, 1, 10, 0)
            ev.cancelled_by_id = usuarios["sa"]["id"]
            ev.cancellation_reason = motivo
        db.session.add(ev)
        db.session.commit()
        return ev.id


def _historico(event_id: int, *mensagens: str) -> None:
    """Linhas do `EventLog` e, para as que o ato também manda ao `AuditLog`, a linha de lá."""
    with app.app_context():
        ev = db.session.get(CalendarEvent, event_id)
        for m in mensagens:
            db.session.add(EventLog(event_id=event_id, actor_name=f"{PREFIX}sa", actor_role="SUPERADMIN", message=m))
            db.session.add(
                AuditLog(
                    actor_name=f"{PREFIX}sa",
                    actor_role="SUPERADMIN",
                    entity_type="agenda",
                    entity_id=event_id,
                    entity_name=ev.title,
                    action="event_cancelled",
                    detail=f"gcal:v306b-{event_id} | {m}",
                )
            )
        db.session.commit()


def _motivo(event_id: int) -> str | None:
    return _no_banco("SELECT cancellation_reason FROM calendar_events WHERE id = :i", i=event_id)[0][0]


def _linhas(event_id: int) -> list[str]:
    return [r[0] for r in _no_banco("SELECT message FROM event_logs WHERE event_id = :i ORDER BY id", i=event_id)]


def _auditoria(event_id: int) -> list[str]:
    return [
        r[0]
        for r in _no_banco(
            "SELECT detail FROM audit_logs WHERE entity_type = 'agenda' AND entity_id = :i "
            "AND action = 'event_cancelled' ORDER BY id",
            i=event_id,
        )
    ]


def _retrato(event_id: int) -> tuple:
    return (_motivo(event_id), _linhas(event_id), _auditoria(event_id))


def _editar(apelido: str, event_id: int, motivo, cliente=None):
    c = cliente or _cliente(apelido)
    return c.patch(ROTA.format(id=event_id), json={"motivo": motivo})


# ── cenários ───────────────────────────────────────────────────────────────────────────────────
ANTIGO = "cliente desistiu do evento dia 07/09/2026"
NOVO = "Cliente desistiu"


def c1_comercial_edita() -> None:
    eid = _evento("C1", motivo=ANTIGO)
    _historico(
        eid,
        f"Evento cancelado: {ANTIGO} | devolve tudo: devolução de R$ 1.140,00 a Fulana | retido R$ 0,00",
        "Adicionou função: Coordenador",
    )
    r = _editar("com", eid, f"  {NOVO}  ")
    _garante(r.status_code == 200, f"PATCH → {r.status_code} {r.get_json(silent=True)}")
    corpo = r.get_json()
    _garante(corpo.get("motivo") == NOVO and corpo.get("eventos") == [eid], f"resposta {corpo}")
    _garante(_motivo(eid) == NOVO, f"motivo no banco: {_motivo(eid)!r}")
    linhas = _linhas(eid)
    _garante(
        linhas[0] == f"Evento cancelado: {NOVO} | devolve tudo: devolução de R$ 1.140,00 a Fulana | retido R$ 0,00",
        f"linha do ato: {linhas[0]!r}",
    )
    _garante(linhas[1] == "Adicionou função: Coordenador", f"linha alheia mudou: {linhas[1]!r}")
    _garante(len(linhas) == 3 and linhas[2] == "Editou o motivo do cancelamento", f"linha nova: {linhas[2:]!r}")
    _garante(all(ANTIGO not in m for m in linhas), "o texto antigo ficou no histórico")
    auditoria = _auditoria(eid)
    _garante(all(ANTIGO not in m for m in auditoria), f"o texto antigo ficou na auditoria: {auditoria}")
    _garante(f"Evento cancelado: {NOVO} |" in auditoria[0], f"auditoria: {auditoria[0]!r}")
    detalhe = _cliente("com").get(f"/api/events/{eid}").get_json()
    _garante(detalhe["event"]["cancellation_reason"] == NOVO, "o detalhe não mostra o motivo novo")


def c2_superadmin_e_ver_como() -> None:
    eid = _evento("C2", motivo=ANTIGO)
    _historico(eid, f"Evento cancelado: {ANTIGO}")
    c = _cliente("sa")
    r = c.post("/api/auth/impersonate", json={"role": RoleName.FINANCEIRO})
    _garante(r.status_code == 200, f"impersonate → {r.status_code}")
    r = _editar("sa", eid, NOVO, cliente=c)
    _garante(r.status_code == 200, f"Superadmin vendo como Financeiro → {r.status_code} (o papel real manda)")
    _garante(_linhas(eid)[0] == f"Evento cancelado: {NOVO}", f"linha: {_linhas(eid)[0]!r}")


def c3_deve_falhar_sem_papel() -> None:
    eid = _evento("C3", motivo=ANTIGO)
    _historico(eid, f"Evento cancelado: {ANTIGO}")
    antes = _retrato(eid)
    for apelido in ("fin", "cast"):
        r = _editar(apelido, eid, NOVO)
        _garante(r.status_code == 403, f"{apelido} → {r.status_code}, esperado 403")
    _garante(_retrato(eid) == antes, "o banco mudou depois do 403")


def c4_deve_falhar_vivo() -> None:
    eid = _evento("C4", motivo=None)
    r = _editar("sa", eid, NOVO)
    _garante(r.status_code == 409 and _erro(r).get("codigo") == "nao_cancelado", f"→ {r.status_code} {_erro(r)}")
    _garante(_motivo(eid) is None and _linhas(eid) == [], "o vivo ganhou motivo ou histórico")
    r = _cliente("sa").patch(ROTA.format(id=999_999_999), json={"motivo": NOVO})
    _garante(r.status_code == 404, f"evento inexistente → {r.status_code}")


def c5_deve_falhar_vazio() -> None:
    eid = _evento("C5", motivo=ANTIGO)
    antes = _retrato(eid)
    for vazio in ("", "   ", None, 12):
        r = _editar("com", eid, vazio)
        _garante(
            r.status_code == 400 and "motivo" in (_erro(r).get("fields") or {}),
            f"motivo {vazio!r} → {r.status_code} {_erro(r)}",
        )
    _garante(_retrato(eid) == antes, "o banco mudou depois do 400")


def c6_grupo() -> None:
    principal = _evento("C6 PRINCIPAL", motivo=ANTIGO)
    dia2 = _evento("C6 DIA 2", motivo=ANTIGO, lider=principal, dias=1)
    cortado = _evento("C6 DIA 3", motivo="festa remarcada", lider=principal, dias=2)
    _historico(principal, f"Evento cancelado: {ANTIGO} | devolve parte: devolução de R$ 500,00 a Fulana")
    _historico(dia2, f'Evento cancelado com todos os dias do grupo de "(CORP) V306B C6 PRINCIPAL": {ANTIGO}')
    _historico(cortado, "Dia cancelado: festa remarcada | venda do grupo R$ 3.000,00 → R$ 2.000,00")
    antes_cortado = _retrato(cortado)
    r = _editar("com", principal, NOVO)
    _garante(r.status_code == 200, f"PATCH → {r.status_code} {r.get_json(silent=True)}")
    _garante(sorted(r.get_json()["eventos"]) == sorted([principal, dia2]), f"eventos: {r.get_json()['eventos']}")
    _garante(_motivo(principal) == NOVO and _motivo(dia2) == NOVO, "o motivo não chegou aos dois dias")
    _garante(
        _linhas(dia2)[0] == f'Evento cancelado com todos os dias do grupo de "(CORP) V306B C6 PRINCIPAL": {NOVO}',
        f"linha do dia 2: {_linhas(dia2)[0]!r}",
    )
    _garante(_linhas(dia2)[-1] == "Editou o motivo do cancelamento", "o dia 2 não ganhou a linha nova")
    _garante(_retrato(cortado) == antes_cortado, "o dia cortado com outro motivo mudou")
    # pelo dia (não pelo principal) também alcança o ato inteiro
    r = _editar("sa", dia2, "Outro texto")
    _garante(r.status_code == 200 and _motivo(principal) == "Outro texto", "editar pelo dia não alcançou o principal")


def c7_troca_exata() -> None:
    curto = "cliente desistiu"
    eid = _evento("C7", motivo=curto)
    _historico(
        eid,
        f"Evento cancelado: {curto} | retido R$ 0,00",
        f"Evento cancelado: {curto} do evento | nota antiga",
        f"Ligou e disse que {curto} | sem prefixo",
        f"Evento cancelado: {curto}",
    )
    r = _editar("com", eid, NOVO)
    _garante(r.status_code == 200, f"PATCH → {r.status_code}")
    linhas = _linhas(eid)
    esperado = [
        f"Evento cancelado: {NOVO} | retido R$ 0,00",
        f"Evento cancelado: {curto} do evento | nota antiga",
        f"Ligou e disse que {curto} | sem prefixo",
        f"Evento cancelado: {NOVO}",
        "Editou o motivo do cancelamento",
    ]
    _garante(linhas == esperado, f"linhas: {linhas}")


def c8_flag() -> None:
    cancelado = _evento("C8 CANCELADO", motivo=ANTIGO)
    vivo = _evento("C8 VIVO", motivo=None)
    esperado = {"sa": True, "com": True, "fin": False, "cast": False}
    for apelido, pode in esperado.items():
        c = _cliente(apelido)
        flags = c.get(f"/api/events/{cancelado}").get_json()["flags"]
        _garante(flags.get("can_edit_motivo_cancelado") is pode, f"{apelido} no cancelado: {flags.get('can_edit_motivo_cancelado')}")
        flags = c.get(f"/api/events/{vivo}").get_json()["flags"]
        _garante(flags.get("can_edit_motivo_cancelado") is False, f"{apelido} no vivo: {flags.get('can_edit_motivo_cancelado')}")
    # o "Ver como" muda a flag (a tela), não o papel real (o servidor)
    c = _cliente("sa")
    c.post("/api/auth/impersonate", json={"role": RoleName.CASTING})
    flags = c.get(f"/api/events/{cancelado}").get_json()["flags"]
    _garante(flags.get("can_edit_motivo_cancelado") is False, "Superadmin vendo como Casting enxerga o botão")


# ── limpeza ────────────────────────────────────────────────────────────────────────────────────
def limpar() -> None:
    with app.app_context():
        ids = [
            r[0]
            for r in db.session.execute(
                text("SELECT id FROM calendar_events WHERE description = :m"), {"m": MARCADOR}
            )
        ]
        if ids:
            db.session.execute(text("DELETE FROM event_logs WHERE event_id = ANY(:i)"), {"i": ids})
            db.session.execute(
                text("DELETE FROM audit_logs WHERE entity_type = 'agenda' AND entity_id = ANY(:i)"), {"i": ids}
            )
            db.session.execute(text("UPDATE calendar_events SET group_leader_id = NULL WHERE id = ANY(:i)"), {"i": ids})
            db.session.execute(text("DELETE FROM calendar_events WHERE id = ANY(:i)"), {"i": ids})
        for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
            u.roles.clear()
            db.session.delete(u)
        db.session.commit()
    usuarios.clear()


def main() -> int:
    print("Feature 306b — motivo do cancelamento editável", flush=True)
    limpar()
    _usuario("sa", RoleName.SUPERADMIN)
    _usuario("com", RoleName.COMERCIAL)
    _usuario("fin", RoleName.FINANCEIRO)
    _usuario("cast", RoleName.CASTING)
    try:
        cenario("1", "Comercial edita: banner, histórico, auditoria e linha nova sem o texto antigo", c1_comercial_edita)
        cenario("2", "Superadmin edita mesmo vendo como Financeiro (papel real)", c2_superadmin_e_ver_como)
        cenario("3", "DEVE FALHAR: Financeiro e Casting → 403, banco intacto", c3_deve_falhar_sem_papel)
        cenario("4", "DEVE FALHAR: evento vivo → 409 nao_cancelado; inexistente → 404", c4_deve_falhar_vivo)
        cenario("5", "DEVE FALHAR: motivo vazio → 400 fields.motivo, banco intacto", c5_deve_falhar_vazio)
        cenario("6", "grupo: o ato inteiro muda, o dia cortado com outro motivo não", c6_grupo)
        cenario("7", "a troca é exata: prefixo + motivo + (' | ' ou fim)", c7_troca_exata)
        cenario("8", "flag can_edit_motivo_cancelado por papel, no vivo e no 'Ver como'", c8_flag)
    finally:
        limpar()
        sobras = _no_banco("SELECT count(*) FROM calendar_events WHERE description = :m", m=MARCADOR)[0][0]
        sobras += _no_banco("SELECT count(*) FROM users WHERE email LIKE :p", p=f"{PREFIX}%")[0][0]
        print(f"  limpeza: {sobras} sobra(s)", flush=True)
    if rede_bloqueada:
        print(f"  rede bloqueada: {sorted(set(rede_bloqueada))}", flush=True)
    ok = sum(1 for _n, passou, _d in resultados if passou)
    print(f"{ok}/{len(resultados)} OK", flush=True)
    return 0 if ok == len(resultados) and not rede_bloqueada else 1


if __name__ == "__main__":
    sys.exit(main())
