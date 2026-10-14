"""Verificação do 298b — a idade do aniversariante e a assessoria do WhatsForm chegam ao cadastro.

Cenários (spec.md):
 1. Resposta com as chaves que a carga do WhatsForm gravou (`idade_a_completar_do_aniversariante` e
    `gostaria_que_a_confirmacao_do_evento_seja_com_assessoria_se_sim_digite_o_telefone`) →
    observações "Aniversariante" com a idade e "Assessoria" com o telefone.
 2. Resposta nativa continua igual, e a chave nativa vence a do WhatsForm quando há as duas.
 3. Pergunta criada no editor (chave fora do mapa) fica só nas respostas do formulário: não vira
    observação e não dá erro (1d-Q1 e Q2 = A, 06/10).
 4. DEVE FALHAR: Financeiro abre o cadastro a partir do formulário → 403.
 5. Limpeza.

Só leitura no endpoint; semeia respostas com o prefixo `__v298b_`, apaga no fim. Requisições FORA
do `app.app_context()`.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    $env:MANTO_SEM_THREADS = "1"; $env:PYTHONIOENCODING = "utf-8"
    .\\.venv\\Scripts\\python.exe specs\\298b-sinonimos-do-formulario\\verify_298b.py
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402
from app.constants import RoleName, now_sp  # noqa: E402
from app.models import FormResponse, Role, User  # noqa: E402

PREFIX = "__v298b_"
SENHA = "verify-298b-senha"
CHAVE_IDADE_WF = "idade_a_completar_do_aniversariante"
CHAVE_ASSESSORIA_WF = (
    "gostaria_que_a_confirmacao_do_evento_seja_com_assessoria_se_sim_digite_o_telefone"
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
    except Exception as exc:  # noqa: BLE001
        with app.app_context():
            db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _para_evento(papel: str, form_id: int):
    c = app.test_client()
    r = c.post("/api/auth/login", json={"email": estado[papel], "password": SENHA})
    _garante(r.status_code == 200, f"login {papel} → {r.status_code}")
    return c.get(f"/api/formularios/respostas/{form_id}/para-evento")


def _observacoes(resp) -> dict[str, str]:
    _garante(
        resp.status_code == 200,
        f"para-evento → {resp.status_code} {resp.get_data(as_text=True)[:200]}",
    )
    return {o["label"]: o["text"] for o in resp.get_json().get("observacoes") or []}


# ── preparo e limpeza ───────────────────────────────────────────────────────────────────────────
def _usuario(apelido: str, papel: str) -> str:
    email = f"{PREFIX}{apelido}@manto.local"
    user = User(name=f"{PREFIX}{apelido}", email=email, is_active=True, has_access=True)
    user.set_password(SENHA)
    user.roles.append(Role.query.filter_by(name=papel).one())
    db.session.add(user)
    return email


def _form(nome: str, campos: list[tuple[str, str]]) -> int:
    fr = FormResponse(
        form_type="comum",
        data=json.dumps(
            [{"secao": "Dados", "campos": [[k, k, v] for k, v in campos]}], ensure_ascii=False
        ),
        contact_name=f"{PREFIX}{nome}",
        event_date=(now_sp() + timedelta(days=40)).date(),
        created_at=datetime.utcnow() - timedelta(days=1),
    )
    db.session.add(fr)
    db.session.flush()
    return fr.id


def preparar() -> None:
    with app.app_context():
        limpar()
        estado["comercial"] = _usuario("comercial", RoleName.COMERCIAL)
        estado["financeiro"] = _usuario("financeiro", RoleName.FINANCEIRO)
        estado["wf"] = _form(
            "whatsform",
            [
                ("nome_do_aniversariante", "Criança Teste"),
                (CHAVE_IDADE_WF, "5"),
                (CHAVE_ASSESSORIA_WF, "(11) 90000-0000"),
            ],
        )
        estado["nativo"] = _form(
            "nativo",
            [
                ("nome_aniversariante", "Criança Nativa"),
                ("idade_aniversariante", "7"),
                (CHAVE_IDADE_WF, "9"),
                ("assessoria", "(11) 91111-1111"),
            ],
        )
        estado["editor"] = _form(
            "editor",
            [
                ("nome_aniversariante", "Criança Editor"),
                ("como_conheceu_a_manto_teste", "Instagram"),
            ],
        )
        db.session.commit()


def limpar() -> None:
    db.session.rollback()
    ids = [
        r.id for r in FormResponse.query.filter(FormResponse.contact_name.like(f"{PREFIX}%")).all()
    ]
    if ids:
        for sql in (
            "DELETE FROM notifications WHERE entity_type='form_response' AND entity_id = ANY(:ids)",
            "DELETE FROM audit_logs WHERE entity_type='form_response' AND entity_id = ANY(:ids)",
            "DELETE FROM form_response_dismissed_events WHERE form_response_id = ANY(:ids)",
            "DELETE FROM form_responses WHERE id = ANY(:ids)",
        ):
            db.session.execute(text(sql), {"ids": ids})
    for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        u.roles.clear()
        db.session.delete(u)
    db.session.commit()


# ── cenários ────────────────────────────────────────────────────────────────────────────────────
def cen_01_whatsform_chega() -> None:
    obs = _observacoes(_para_evento("comercial", estado["wf"]))
    _garante(obs.get("Aniversariante") == "Criança Teste, 5 anos", f"aniversariante: {obs}")
    _garante(obs.get("Assessoria") == "(11) 90000-0000", f"assessoria: {obs}")


def cen_02_nativo_vence() -> None:
    obs = _observacoes(_para_evento("comercial", estado["nativo"]))
    _garante(obs.get("Aniversariante") == "Criança Nativa, 7 anos", f"a nativa não venceu: {obs}")
    _garante(obs.get("Assessoria") == "(11) 91111-1111", f"assessoria nativa: {obs}")


def cen_03_pergunta_do_editor_fica_no_formulario() -> None:
    obs = _observacoes(_para_evento("comercial", estado["editor"]))
    _garante(
        not any("Instagram" in t for t in obs.values()),
        f"a pergunta do editor virou observação: {obs}",
    )
    _garante(obs.get("Aniversariante") == "Criança Editor", f"{obs}")


def cen_04_financeiro_nao_abre() -> None:
    r = _para_evento("financeiro", estado["wf"])
    _garante(r.status_code == 403, f"Financeiro abriu o cadastro: {r.status_code}")


def cen_05_limpeza() -> None:
    with app.app_context():
        limpar()
        _garante(
            FormResponse.query.filter(FormResponse.contact_name.like(f"{PREFIX}%")).count() == 0,
            "sobrou",
        )


def main() -> int:
    print("298b — sinônimos do WhatsForm no cadastro do evento")
    preparar()
    try:
        cenario("1. WhatsForm: idade e assessoria chegam como observação", cen_01_whatsform_chega)
        cenario("2. nativo igual; a chave nativa vence a do WhatsForm", cen_02_nativo_vence)
        cenario(
            "3. pergunta do editor fica só no formulário",
            cen_03_pergunta_do_editor_fica_no_formulario,
        )
        cenario("4. DEVE FALHAR: Financeiro abre o cadastro → 403", cen_04_financeiro_nao_abre)
    finally:
        cenario("5. limpeza", cen_05_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"{ok}/{len(resultados)} OK")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
