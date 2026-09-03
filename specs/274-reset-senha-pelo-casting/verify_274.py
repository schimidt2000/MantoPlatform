"""Verificação da feature 274 — o casting devolve o acesso ao portal para o artista.

O artista que não consegue entrar tinha dois caminhos e os dois podem travar: "Esqueci minha
senha" só funciona se ele digitar **exatamente** o e-mail do cadastro (e não avisa quando não
bate, de propósito), e "Primeiro Acesso" recusa quem já tem senha. Não havia ferramenta nenhuma
do lado de dentro. Caso real: duas artistas presas, uma delas com o e-mail cadastrado numa grafia
difícil de acertar.

Cenários:
 1. CASTING envia o link para talento COM senha: 200 com e-mail e validade, token gravado, e-mail
    com link do portal público, `AuditLog` registrado.
 2. Talento SEM senha: o mesmo botão serve para definir a primeira (`tinha_senha=false`).
 3. Talento sem e-mail no cadastro: 400 com mensagem e campo, e nenhum token é gravado.
 4. RBAC: FINANCEIRO → 403; talento inexistente → 404.
 5. O link entregue funciona: resolve o token e troca a senha de verdade.
 6. Enviar de novo invalida o link anterior (nunca dois links vivos).
 7. `GET /api/talents/<id>` traz o bloco `portal` para quem gere talento e esconde dos demais.
 8. Limpeza.

Nada é enviado: o SMTP é dublado. Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    $env:PYTHONIOENCODING = "utf-8"
    .\\.venv\\Scripts\\python.exe specs\\274-reset-senha-pelo-casting\\verify_274.py
"""
from __future__ import annotations

import os
import sys
import traceback
import uuid
from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()
os.environ["MAIL_SUPPRESS_SEND"] = "true"

from app import (  # noqa: E402
    create_app,
    db,
    limiter,  # noqa: E402
)
from app import email_service as es  # noqa: E402
from app.config import PORTAL_BASE_URL  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import Role, Talent, User  # noqa: E402
from app.talent_portal import portal_account_ops as ops  # noqa: E402

limiter.enabled = False  # vários logins por cliente de teste passam do limite da rota

PREFIX = "__v274_"
SENHA = "verify-274-senha"

app = create_app()
app.config["TESTING"] = True

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
enviados: list[dict] = []
es.mail.send = lambda msg: enviados.append({"to": list(msg.recipients), "html": msg.html or ""})
# O ambiente suprime e-mail (e o verify reforça isso); aqui a trava de ambiente não é o objeto de
# teste, então ela sai da frente e o SMTP dublado registra o que teria saído. O envio também vira
# síncrono: em produção ele roda em thread (send_async) e o teste não pode correr com ela.
es._emails_enabled = lambda: True
es.send_async = lambda fn, *args: fn(*args)


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001 — o verify reporta, não estoura
        db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _usuario(sufixo: str, *papeis: str) -> User:
    user = User(name=f"{PREFIX}{sufixo}", email=f"{PREFIX}{sufixo}@manto.local", is_active=True, has_access=True)
    user.set_password(SENHA)
    for p in papeis:
        user.roles.append(Role.query.filter_by(name=p).one())
    db.session.add(user)
    db.session.commit()
    return user


def _login(c, user: User) -> None:
    r = c.post("/api/auth/login", json={"email": user.email, "password": SENHA})
    _garante(r.status_code == 200, f"login {user.email} → {r.status_code}")


def _talento(sufixo: str, *, com_senha: bool, com_email: bool = True) -> Talent:
    t = Talent(
        full_name=f"{PREFIX}{sufixo}",
        email_contact=f"{PREFIX}{uuid.uuid4().hex[:8]}@exemplo.com" if com_email else None,
        cpf=str(uuid.uuid4().int)[:11],
        status="active",
    )
    if com_senha:
        t.set_password("SenhaAntiga#2026")
    db.session.add(t)
    db.session.commit()
    return t


def limpar() -> None:
    for t in Talent.query.filter(Talent.full_name.like(f"{PREFIX}%")).all():
        db.session.delete(t)
    for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        u.roles.clear()
        db.session.delete(u)
    db.session.execute(db.text("DELETE FROM audit_logs WHERE entity_name LIKE :p"), {"p": f"{PREFIX}%"})
    db.session.commit()


# ───────────────────────────── cenários ─────────────────────────────

def cen_01_envio_pelo_casting() -> None:
    t = _talento("com senha", com_senha=True)
    estado["t_com_senha"] = t.id
    enviados.clear()
    with app.test_client() as c:
        _login(c, estado["casting"])
        r = c.post(f"/api/talents/{t.id}/reset-senha")
        _garante(r.status_code == 200, f"POST → {r.status_code} {r.get_data(as_text=True)[:200]}")
        corpo = r.get_json()
    _garante(corpo["email"] == t.email_contact, f"e-mail devolvido: {corpo}")
    _garante(corpo["tinha_senha"] is True and corpo["expira_em"], f"resposta incompleta: {corpo}")
    # A validade é lida por uma pessoa: tem que estar no horário de parede de São Paulo (~1h), e
    # não no UTC ingênuo do banco, que mostraria 3 horas a mais.
    from datetime import datetime as _dt
    faltam = (_dt.fromisoformat(corpo["expira_em"]) - now_sp().replace(tzinfo=None)).total_seconds()
    _garante(3000 < faltam < 3900, f"validade fora do fuso de São Paulo: {corpo[chr(39)+chr(39)]}" if False else f"validade fora do fuso de SP: faltam {faltam:.0f}s")
    db.session.refresh(t)
    _garante(bool(t.password_reset_token), "token não foi gravado")
    _garante(len(enviados) == 1, f"esperava 1 e-mail, veio {len(enviados)}")
    html = enviados[0]["html"]
    _garante(PORTAL_BASE_URL in html and "localhost" not in html.lower(), "link do e-mail não é o público")
    _garante(t.password_reset_token in html, "e-mail não carrega o token deste pedido")
    logs = db.session.execute(
        db.text("SELECT action, detail FROM audit_logs WHERE entity_name = :n ORDER BY id DESC LIMIT 1"),
        {"n": t.full_name},
    ).fetchall()
    _garante(logs and "redefinição" in logs[0][0], f"sem trilha de auditoria: {logs}")


def cen_02_talento_sem_senha() -> None:
    t = _talento("sem senha", com_senha=False)
    estado["t_sem_senha"] = t.id
    enviados.clear()
    with app.test_client() as c:
        _login(c, estado["casting"])
        r = c.post(f"/api/talents/{t.id}/reset-senha")
        _garante(r.status_code == 200, f"→ {r.status_code}")
        _garante(r.get_json()["tinha_senha"] is False, "deveria dizer que não tinha senha")
    db.session.refresh(t)
    _garante(bool(t.password_reset_token), "token não gravado para quem nunca teve senha")
    _garante(len(enviados) == 1, "e-mail não saiu")


def cen_03_talento_sem_email() -> None:
    t = _talento("sem email", com_senha=True, com_email=False)
    enviados.clear()
    with app.test_client() as c:
        _login(c, estado["casting"])
        r = c.post(f"/api/talents/{t.id}/reset-senha")
        _garante(r.status_code == 400, f"→ {r.status_code}")
        erro = r.get_json()["error"]
        _garante("e-mail" in erro["message"].lower(), f"mensagem pouco clara: {erro}")
        _garante(erro.get("fields", {}).get("email_contact"), f"sem campo apontado: {erro}")
    db.session.refresh(t)
    _garante(t.password_reset_token is None, "gravou token mesmo sem e-mail")
    _garante(enviados == [], "mandou e-mail para ninguém")


def cen_04_rbac() -> None:
    with app.test_client() as c:
        _login(c, estado["financeiro"])
        r = c.post(f"/api/talents/{estado['t_com_senha']}/reset-senha")
        _garante(r.status_code == 403, f"FINANCEIRO → {r.status_code}, esperava 403")
    with app.test_client() as c:
        _login(c, estado["casting"])
        r = c.post("/api/talents/99999999/reset-senha")
        _garante(r.status_code == 404, f"inexistente → {r.status_code}")


def cen_05_o_link_funciona() -> None:
    t = db.session.get(Talent, estado["t_com_senha"])
    token = t.password_reset_token
    _garante(ops.find_talent_by_reset_token(token) is not None, "token entregue não resolve")
    ops.reset_password_with_token(token, "SenhaNova#2026", "SenhaNova#2026")
    db.session.commit()
    db.session.refresh(t)
    _garante(t.check_password("SenhaNova#2026"), "senha nova não entrou")
    _garante(t.password_reset_token is None, "token não foi consumido")


def cen_06_segundo_envio_invalida_o_primeiro() -> None:
    t = db.session.get(Talent, estado["t_sem_senha"])
    primeiro = t.password_reset_token
    with app.test_client() as c:
        _login(c, estado["casting"])
        _garante(c.post(f"/api/talents/{t.id}/reset-senha").status_code == 200, "2º envio falhou")
    db.session.refresh(t)
    _garante(t.password_reset_token != primeiro, "token não mudou")
    _garante(ops.find_talent_by_reset_token(primeiro) is None, "link antigo continua valendo")
    _garante(ops.find_talent_by_reset_token(t.password_reset_token) is not None, "link novo não vale")


def cen_07_bloco_portal_na_ficha() -> None:
    tid = estado["t_sem_senha"]
    with app.test_client() as c:
        _login(c, estado["casting"])
        r = c.get(f"/api/talents/{tid}")
        _garante(r.status_code == 200, f"GET → {r.status_code}")
        portal = r.get_json().get("portal")
        _garante(portal is not None, "bloco portal não veio para quem gere talento")
        _garante(portal["tem_senha"] is False, f"tem_senha errado: {portal}")
        _garante(portal["reset_pendente"] is True and portal["reset_expira_em"], f"pendência: {portal}")
    with app.test_client() as c:
        _login(c, estado["financeiro"])
        r = c.get(f"/api/talents/{tid}")
        _garante(r.status_code == 200, f"GET financeiro → {r.status_code}")
        _garante(r.get_json().get("portal") is None, "bloco portal vazou para quem não gere talento")


def cen_08_limpeza() -> None:
    limpar()
    _garante(Talent.query.filter(Talent.full_name.like(f"{PREFIX}%")).count() == 0, "talento sobrou")
    _garante(User.query.filter(User.email.like(f"{PREFIX}%")).count() == 0, "usuário sobrou")


def main() -> int:
    print("Feature 274 — reset de senha do portal pelo casting")
    with app.app_context():
        limpar()
        estado["casting"] = _usuario("casting", RoleName.CASTING)
        estado["financeiro"] = _usuario("financeiro", RoleName.FINANCEIRO)
        try:
            cenario("1. casting envia o link: e-mail público, token gravado, auditoria", cen_01_envio_pelo_casting)
            cenario("2. talento sem senha recebe o mesmo link (primeira senha)", cen_02_talento_sem_senha)
            cenario("3. talento sem e-mail: 400 explicando, sem token e sem envio", cen_03_talento_sem_email)
            cenario("4. FINANCEIRO 403; talento inexistente 404", cen_04_rbac)
            cenario("5. o link entregue redefine a senha de verdade", cen_05_o_link_funciona)
            cenario("6. segundo envio invalida o link anterior", cen_06_segundo_envio_invalida_o_primeiro)
            cenario("7. bloco `portal` na ficha só para quem gere talento", cen_07_bloco_portal_na_ficha)
        finally:
            cenario("8. limpeza", cen_08_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"{ok}/{len(resultados)} OK")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
