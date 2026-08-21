"""Verificação do hotfix 257 — anexos do evento têm de sobreviver ao refresh.

Cada anexo é enviado pela API e conferido por uma **conexão psycopg independente**. Isso é o
ponto do teste: conferir pela sessão do próprio Flask passaria mesmo com o bug, porque o
autoflush do SQLAlchemy mostra o INSERT pendente antes do rollback do fim do request.

Cenários:
 1. Comprovante de pagamento persiste (`POST /events/<id>/payments`).
 2. Contrato persiste (`POST /events/<id>/contracts`).
 3. Reembolso persiste (`POST /events/<id>/reimbursements`).
 4. Nota fiscal persiste (`POST /events/<id>/invoices`).
 5. Marcar reembolso como cobrado persiste (`POST /reimbursements/<id>/collect`).
 6. Editar e excluir comprovante continuam funcionando (não-regressão).
 7. Histórico do evento registra cada anexo (paridade com o Jinja, restaurada no hotfix).
 8. Limpeza total dos registros e arquivos de teste.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    .venv/Scripts/python.exe specs/257-hotfix-anexos-persistencia/verify_257.py

O evento de teste é criado direto no banco (a API de eventos sincroniza com o Google real).
"""

from __future__ import annotations

import io
import os
import sys
import traceback
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):  # console do Windows em cp1252
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

import psycopg  # noqa: E402

from app import create_app, db  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.models import CalendarEvent, Role, User  # noqa: E402

PREFIX = "__v257_"
SENHA = "verify-257-senha"
DB_URL = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a4944415478"
    "9c6360000002000154a24f6b0000000049454e44ae426082"
)

app = create_app()
app.config["TESTING"] = True
resultados: list[tuple[str, bool, str]] = []
estado: dict = {}


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001 — harness: registra e segue
        db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def fora_da_sessao(query: str, params: tuple = ()) -> list[tuple]:
    """Consulta por conexão própria — enxerga só o que foi realmente commitado."""
    with psycopg.connect(DB_URL) as conn, conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def arquivo(nome: str) -> tuple:
    return (io.BytesIO(PNG), nome)


def _login(client) -> None:
    r = client.post("/api/auth/login", json={"email": estado["user"].email, "password": SENHA})
    _garante(r.status_code == 200, f"login → {r.status_code}")


def cen_01_comprovante() -> None:
    with app.test_client() as c:
        _login(c)
        r = c.post(f"/api/events/{estado['event_id']}/payments",
                   data={"amount": "250.00", "file": arquivo(f"{PREFIX}c.png")},
                   content_type="multipart/form-data")
        _garante(r.status_code == 201, f"POST payments → {r.status_code}")
    linhas = fora_da_sessao("SELECT id, amount, file_path FROM event_payments WHERE event_id=%s", (estado["event_id"],))
    _garante(len(linhas) == 1, f"comprovante no banco após o request: {len(linhas)} (esperado 1)")
    _garante(str(linhas[0][1]) == "250.00", f"valor gravado: {linhas[0][1]}")
    estado["payment_id"] = linhas[0][0]


def cen_02_contrato() -> None:
    with app.test_client() as c:
        _login(c)
        r = c.post(f"/api/events/{estado['event_id']}/contracts",
                   data={"file": arquivo(f"{PREFIX}k.png")}, content_type="multipart/form-data")
        _garante(r.status_code == 201, f"POST contracts → {r.status_code}")
    _garante(len(fora_da_sessao("SELECT id FROM event_contracts WHERE event_id=%s", (estado["event_id"],))) == 1,
             "contrato não persistiu")


def cen_03_reembolso() -> None:
    with app.test_client() as c:
        _login(c)
        r = c.post(f"/api/events/{estado['event_id']}/reimbursements",
                   data={"description": f"{PREFIX}taxa", "amount": "40.00", "file": arquivo(f"{PREFIX}r.png")},
                   content_type="multipart/form-data")
        _garante(r.status_code == 201, f"POST reimbursements → {r.status_code}")
    linhas = fora_da_sessao("SELECT id FROM event_reimbursements WHERE event_id=%s", (estado["event_id"],))
    _garante(len(linhas) == 1, "reembolso não persistiu")
    estado["reimbursement_id"] = linhas[0][0]


def cen_04_nota_fiscal() -> None:
    with app.test_client() as c:
        _login(c)
        r = c.post(f"/api/events/{estado['event_id']}/invoices",
                   data={"amount": "80.00", "file": arquivo(f"{PREFIX}n.png")},
                   content_type="multipart/form-data")
        _garante(r.status_code == 201, f"POST invoices → {r.status_code}")
    _garante(len(fora_da_sessao("SELECT id FROM event_invoices WHERE event_id=%s", (estado["event_id"],))) == 1,
             "nota fiscal não persistiu")


def cen_05_reembolso_cobrado() -> None:
    with app.test_client() as c:
        _login(c)
        r = c.post(f"/api/reimbursements/{estado['reimbursement_id']}/collect",
                   data={"collected_amount": "40.00", "file": arquivo(f"{PREFIX}rc.png")},
                   content_type="multipart/form-data")
        _garante(r.status_code == 200, f"POST collect → {r.status_code}")
    collected_at, receipt = fora_da_sessao(
        "SELECT collected_at, receipt_file_path FROM event_reimbursements WHERE id=%s",
        (estado["reimbursement_id"],))[0]
    _garante(collected_at is not None and receipt, f"cobrança não persistiu: {collected_at} {receipt}")


def cen_06_editar_e_excluir() -> None:
    """Não-regressão: PATCH e DELETE do comprovante já commitavam e devem continuar iguais."""
    with app.test_client() as c:
        _login(c)
        r = c.patch(f"/api/payments/{estado['payment_id']}", json={"amount": 300})
        _garante(r.status_code == 200, f"PATCH payment → {r.status_code}")
        valor = fora_da_sessao("SELECT amount FROM event_payments WHERE id=%s", (estado["payment_id"],))[0][0]
        _garante(str(valor) == "300.00", f"valor editado não persistiu: {valor}")
        r = c.delete(f"/api/payments/{estado['payment_id']}")
        _garante(r.status_code == 200, f"DELETE payment → {r.status_code}")
    _garante(not fora_da_sessao("SELECT id FROM event_payments WHERE id=%s", (estado["payment_id"],)),
             "exclusão do comprovante não persistiu")


def cen_07_historico() -> None:
    """O histórico do evento tem de registrar cada anexo — era o rastro que a API perdia."""
    mensagens = [
        m for (m,) in fora_da_sessao(
            "SELECT message FROM event_logs WHERE event_id=%s ORDER BY id", (estado["event_id"],))
    ]
    esperado = [
        ("Adicionou pagamento recebido de R$ 250.00", "comprovante"),
        ("Adicionou contrato assinado", "contrato"),
        ("Registrou reembolso a cobrar", "reembolso"),
        ("Adicionou nota fiscal", "nota fiscal"),
        ("Marcou reembolso como cobrado", "reembolso cobrado"),
        ("Corrigiu valor de comprovante: R$ 250.00 → R$ 300", "correção de valor"),
        ("Excluiu comprovante de R$ 300.00", "exclusão"),
    ]
    for trecho, rotulo in esperado:
        _garante(any(trecho in m for m in mensagens),
                 f"histórico sem o registro de {rotulo}: {mensagens}")
    autores = {a for (a,) in fora_da_sessao(
        "SELECT DISTINCT actor_name FROM event_logs WHERE event_id=%s", (estado["event_id"],))}
    _garante(autores == {estado["user"].name}, f"autor do log errado: {autores}")


def preparar() -> None:
    limpar()
    user = User(name=f"{PREFIX}sa", email=f"{PREFIX}sa@manto.local", is_active=True, has_access=True)
    user.set_password(SENHA)
    user.roles.append(Role.query.filter_by(name=RoleName.SUPERADMIN).one())
    db.session.add(user)
    inicio = datetime.utcnow() + timedelta(days=30)
    evento = CalendarEvent(
        google_event_id=f"{PREFIX}google", title=f"{PREFIX}evento", start_at=inicio,
        end_at=inicio + timedelta(hours=2), event_type="SHOW", sale_value=1000, source="platform",
    )
    db.session.add(evento)
    db.session.commit()
    estado["user"], estado["event_id"] = user, evento.id


def limpar() -> None:
    db.session.rollback()
    for evento in CalendarEvent.query.filter(CalendarEvent.title.like(f"{PREFIX}%")).all():
        for tabela in ("event_payments", "event_contracts", "event_reimbursements",
                       "event_invoices", "event_roles", "event_logs"):
            db.session.execute(db.text(f"DELETE FROM {tabela} WHERE event_id = :eid"), {"eid": evento.id})
        db.session.delete(evento)
    usuario = User.query.filter_by(email=f"{PREFIX}sa@manto.local").first()
    if usuario:
        usuario.roles.clear()
        db.session.delete(usuario)
    db.session.commit()
    for pasta in ("payments", "contracts", "invoices", "reimbursements"):
        destino = Path(app.config.get(f"UPLOAD_{pasta.upper()}", REPO_ROOT / "instance" / "uploads" / pasta))
        if destino.exists():
            # `secure_filename` come os "__" do prefixo ao salvar (`__v257_c.png` → `v257_c.png`),
            # então a limpeza procura pelo miolo, senão sobra arquivo de teste no volume.
            for f in destino.glob(f"*{PREFIX.strip('_')}_*"):
                f.unlink(missing_ok=True)


def main() -> int:
    with app.app_context():
        try:
            preparar()
            print("Hotfix 257 — anexos do evento contra manto_local")
            cenario("1. comprovante de pagamento persiste", cen_01_comprovante)
            cenario("2. contrato persiste", cen_02_contrato)
            cenario("3. reembolso persiste", cen_03_reembolso)
            cenario("4. nota fiscal persiste", cen_04_nota_fiscal)
            cenario("5. reembolso marcado como cobrado persiste", cen_05_reembolso_cobrado)
            cenario("6. editar e excluir comprovante (não-regressão)", cen_06_editar_e_excluir)
            cenario("7. histórico do evento registra os anexos", cen_07_historico)
        finally:
            cenario("8. limpeza", limpar)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  - {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
