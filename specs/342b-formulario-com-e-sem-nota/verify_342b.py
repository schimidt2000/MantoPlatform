"""Verificação do hotfix 342b — cada formulário público com um link com nota e outro sem nota.

Cenários (spec §Verificação):
 1. Link com nota sem documento: 400 no documento, mesmo sem a caixa vir.   (DEVE falhar)
 2. Link com nota completo, sem mandar a caixa: 201, "Preciso de nota fiscal" = Sim e os dados ficam.
 3. Link sem nota com a caixa marcada e documento (tela adulterada): 201, resposta "Não", dados
    da nota descartados.
 4. Versão desconhecida: 404 e nada gravado.                                 (DEVE falhar)
 5. Link antigo (sem versão): a cliente ainda escolhe — com a caixa vale Sim, sem ela fica vazio.
 6. Limpeza.
A mensagem do WhatsApp dizer de qual link veio (Sim / Não) é conferida nos cenários 2 e 3.

Só o endpoint público é tocado: nenhum evento é criado nem ligado (data longe, o vínculo automático
não age). Requisições FORA do `app_context`; leitura por conexão separada.

Rodar (PowerShell, na raiz do worktree)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
    C:\\Users\\schim\\Desktop\\Manto_Platform\\.venv\\Scripts\\python.exe specs\\342b-formulario-com-e-sem-nota\\verify_342b.py
"""

from __future__ import annotations

import json
import os
import sys
import traceback
import urllib.parse
import uuid
from collections.abc import Callable
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, email_service, limiter  # noqa: E402
from app.models import FormFieldDefinition  # noqa: E402

PREFIX = "__v342b_"
CNPJ_OK = "11.222.333/0001-81"
CPF_OK = "529.982.247-25"
DATA_FORM = "2031-04-17"  # longe: nenhum evento real nessa data, o vínculo automático não age
CHAVES_DA_NOTA = ("nota_doc", "nota_email", "nota_iss", "nota_referencia")

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False
email_service._send = lambda *a, **k: True
email_service.send_async = lambda fn, *args: None

resultados: list[tuple[str, bool, str]] = []
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
        with app.app_context():
            db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


_VALOR_POR_TIPO = {
    "texto_curto": "Teste",
    "texto_longo": "Teste",
    "hora": "15:00",
    "cpf": CPF_OK,
    "cnpj": CNPJ_OK,
    "cep": "01310-100",
    "cpf_cnpj": CNPJ_OK,
}


def _corpo(form_type: str, **extra) -> dict:
    """Todos os obrigatórios SEM condição preenchidos; `extra` entra por cima."""
    with app.app_context():
        campos = (
            FormFieldDefinition.query.filter_by(form_type=form_type)
            .order_by(FormFieldDefinition.order)
            .all()
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
    corpo.update(extra)
    return corpo


def _enviar(form_type: str, esperado: int = 201, **extra):
    corpo = _corpo(form_type, **extra)
    r = app.test_client().post(f"/api/formularios/{form_type}", data=corpo)
    _garante(
        r.status_code == esperado,
        f"POST {form_type} → {r.status_code} {r.get_data(as_text=True)[:300]}",
    )
    nome = corpo["razao_social" if form_type == "corporativo" else "nome_contratante"]
    linhas = _no_banco("SELECT id, data FROM form_responses WHERE contact_name = :n", n=nome)
    return r, linhas


def _valores(bruto: str) -> dict[str, str]:
    return {c[0]: c[2] for secao in json.loads(bruto) for c in secao["campos"] if len(c) == 3}


DADOS_CNPJ = {
    "nota_doc": CNPJ_OK,
    "nota_email": f"{PREFIX}nf@cliente.local",
    "nota_iss": "Não",
    "nota_referencia": "OC 77",
}


def cen_01_com_nota_exige_documento() -> None:
    for form_type in ("comum", "corporativo"):
        r, linhas = _enviar(form_type, esperado=400, versao_nota="com-nota")
        campos = r.get_json()["error"]["fields"]
        _garante("nota_doc" in campos and "nota_email" in campos, f"{form_type}: {campos}")
        _garante(not linhas, f"{form_type}: gravou mesmo recusando")


def cen_02_com_nota_completo() -> None:
    for form_type in ("comum", "corporativo"):
        r, linhas = _enviar(form_type, versao_nota="com-nota", **DADOS_CNPJ)
        _garante(len(linhas) == 1, f"{form_type}: {len(linhas)} respostas")
        valores = _valores(linhas[0].data)
        _garante(valores["precisa_nota"] == "Sim", f"{form_type}: {valores['precisa_nota']!r}")
        for chave, valor in DADOS_CNPJ.items():
            _garante(valores[chave] == valor, f"{form_type}: {chave} = {valores[chave]!r}")
        mensagem = urllib.parse.unquote(r.get_json()["wa_link"])
        _garante("*Preciso de nota fiscal:* Sim" in mensagem, "mensagem sem 'Sim' na nota")


def cen_03_sem_nota_descarta() -> None:
    for form_type in ("comum", "corporativo"):
        r, linhas = _enviar(form_type, versao_nota="sem-nota", precisa_nota="Sim", **DADOS_CNPJ)
        _garante(len(linhas) == 1, f"{form_type}: {len(linhas)} respostas")
        valores = _valores(linhas[0].data)
        _garante(valores["precisa_nota"] == "Não", f"{form_type}: {valores['precisa_nota']!r}")
        for chave in CHAVES_DA_NOTA:
            _garante(
                valores[chave] == "", f"{form_type}: {chave} não descartado: {valores[chave]!r}"
            )
        mensagem = urllib.parse.unquote(r.get_json()["wa_link"])
        _garante("*Preciso de nota fiscal:* Não" in mensagem, "mensagem sem 'Não' na nota")
        _garante(CNPJ_OK not in mensagem.split("Nota fiscal")[-1], "documento da nota na mensagem")


def cen_04_versao_desconhecida() -> None:
    r, linhas = _enviar("comum", esperado=404, versao_nota="talvez", **DADOS_CNPJ)
    _garante(r.get_json()["error"]["message"], "404 sem mensagem")
    _garante(not linhas, "gravou com versão desconhecida")


def cen_05_link_antigo() -> None:
    _, linhas = _enviar("comum", precisa_nota="Sim", **DADOS_CNPJ)
    valores = _valores(linhas[0].data)
    _garante(valores["precisa_nota"] == "Sim" and valores["nota_doc"] == CNPJ_OK, f"{valores}")
    _, linhas = _enviar("comum", **DADOS_CNPJ)
    valores = _valores(linhas[0].data)
    _garante(valores["precisa_nota"] == "" and valores["nota_doc"] == "", f"{valores}")


def limpar() -> None:
    with app.app_context():
        rids = [
            r[0]
            for r in _no_banco(
                "SELECT id FROM form_responses WHERE contact_name LIKE :p", p=f"{PREFIX}%"
            )
        ]
        for rid in rids:
            db.session.execute(
                text(
                    "DELETE FROM notifications WHERE entity_type = 'form_response' "
                    "AND entity_id = :i"
                ),
                {"i": rid},
            )
            db.session.execute(text("DELETE FROM form_responses WHERE id = :i"), {"i": rid})
        db.session.execute(
            text("DELETE FROM clients WHERE name LIKE :p OR company LIKE :p"), {"p": f"{PREFIX}%"}
        )
        db.session.commit()


def cen_06_limpeza() -> None:
    limpar()
    sobra = _no_banco(
        "SELECT count(*) FROM form_responses WHERE contact_name LIKE :p", p=f"{PREFIX}%"
    )[0][0]
    _garante(sobra == 0, f"{sobra} respostas sobraram")


def main() -> int:
    print("Hotfix 342b — formulário com nota e sem nota")
    limpar()
    passos = [
        ("1. link com nota sem documento (DEVE falhar)", cen_01_com_nota_exige_documento),
        ("2. link com nota completo: Sim e os dados ficam", cen_02_com_nota_completo),
        ("3. link sem nota descarta a nota mesmo marcada", cen_03_sem_nota_descarta),
        ("4. versão desconhecida (DEVE falhar)", cen_04_versao_desconhecida),
        ("5. link antigo: a cliente ainda escolhe", cen_05_link_antigo),
    ]
    try:
        for nome, fn in passos:
            cenario(nome, fn)
    finally:
        cenario("6. limpeza", cen_06_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  ✗ {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
