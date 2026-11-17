"""Verificação da feature 352 — fornecedores cadastrados nos gastos extras.

Cenários (spec §Verificação):
 1. Importação: todo gasto `fornecedor` ligado, nenhum `cliente`; nome do gasto = nome do cadastro;
    `nome_normalizado` igual ao do núcleo; grupos de mesma chave PIX no mesmo fornecedor.
 2. Figurino lança gasto a um nome novo: o fornecedor nasce com nome, PIX e categoria; gasto ligado.
 3. Mesmo nome em outra grafia: liga ao existente, nenhum fornecedor a mais, gasto com o nome do cadastro.
 4. `fornecedor_id` a fornecedor sem PIX completa; a fornecedor com PIX não troca; o gasto guarda o digitado.
 5. `GET /api/gastos/fornecedores`: Figurino só ativos e sem totais; Financeiro com arquivados e totais.
 6. Financeiro renomeia e troca o PIX: gastos ligados mudam de nome; o PIX deles não muda.
 7. Financeiro junta A com B: gastos de A em B com o nome de B; A apagado; B completa o PIX.
 8. Nome repetido (cadastro e renome), categoria inválida, juntar consigo mesmo: 400 no campo.
 9. Figurino tenta cadastrar, alterar e juntar pela API: 403, nada muda.          (DEVE falhar)
10. Gasto deixa de ser "Pagamento a fornecedor": o vínculo sai.
11. Limpeza.

E-mail dublado (o alerta de gasto novo não sai). Requisições HTTP FORA do `app_context`; toda asserção
de escrita lê por conexão separada.

Rodar contra o espelho da feature (PowerShell, na raiz do repositório)::

    $env:DATABASE_URL = '<url do manto_352>'; $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
    .venv\\Scripts\\python.exe specs\\352-fornecedores-gastos-extras\\verify_352.py
"""

from __future__ import annotations

import io
import os
import re
import sys
import traceback
from collections import defaultdict
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
from app.gastos import fornecedor_ops, gastos_ops  # noqa: E402
from app.models import Fornecedor, Role, SpecialExpense, User  # noqa: E402

PREFIX = "__v352_"
NORM_PREFIX = "v352 "
SENHA = "verify-352-senha"

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_externo = create_engine(os.environ["DATABASE_URL"], future=True)

# ── dublês: o alerta por e-mail de gasto novo não sai ──────────────────────────────────────────
email_service._send = lambda *a, **k: True
email_service.send_async = lambda *a, **k: None
gastos_ops.send_async = lambda *a, **k: None


def _no_banco(sql: str, **params):
    with _externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def _um(sql: str, **params):
    linhas = _no_banco(sql, **params)
    return linhas[0] if linhas else None


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


def _usuario(sufixo: str, nome: str, papel: str) -> int:
    user = User(name=nome, email=f"{PREFIX}{sufixo}@manto.local", is_active=True, has_access=True)
    user.set_password(SENHA)
    user.roles.append(Role.query.filter_by(name=papel).one())
    db.session.add(user)
    db.session.commit()
    return user.id


def _fornecedor_direto(
    nome: str, *, pix: str | None = None, categoria: str | None = None, ativo: bool = True
) -> int:
    f = Fornecedor(
        nome=nome,
        nome_normalizado=fornecedor_ops.normalizar_nome(nome),
        pix=pix,
        categoria_padrao=categoria,
        ativo=ativo,
    )
    db.session.add(f)
    db.session.commit()
    return f.id


def preparar() -> None:
    with app.app_context():
        limpar()
        estado["fin"] = _usuario("fin", f"{PREFIX}Financeiro", "FINANCEIRO")
        estado["fig"] = _usuario("fig", f"{PREFIX}Figurino", "FIGURINO")
        estado["sem_pix"] = _fornecedor_direto(f"{PREFIX}Sem Pix")
        estado["com_pix"] = _fornecedor_direto(
            f"{PREFIX}Com Pix", pix="chave-antiga", categoria="Figurino"
        )
        estado["arquivado"] = _fornecedor_direto(f"{PREFIX}Arquivado", ativo=False)


def limpar() -> None:
    db.session.rollback()
    gastos = SpecialExpense.query.filter(SpecialExpense.description.like(f"{PREFIX}%")).all()
    pasta = Path(app.config["UPLOAD_EXPENSES"])
    for g in gastos:
        if g.receipt_path:
            (pasta / Path(g.receipt_path).name).unlink(missing_ok=True)
        db.session.delete(g)
    db.session.flush()
    Fornecedor.query.filter(Fornecedor.nome_normalizado.like(f"{NORM_PREFIX}%")).delete(
        synchronize_session=False
    )
    for user in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        user.roles.clear()
        db.session.delete(user)
    db.session.commit()


def _cliente_http(chave: str):
    c = app.test_client()
    r = c.post("/api/auth/login", json={"email": f"{PREFIX}{chave}@manto.local", "password": SENHA})
    _garante(r.status_code == 200, f"login {chave} → {r.status_code}")
    return c


def _lancar(
    chave: str,
    descricao: str,
    nome: str,
    *,
    pix: str = "",
    categoria: str = "Outros",
    fornecedor_id: int | None = None,
    esperado: int = 201,
) -> dict:
    form = {
        "description": f"{PREFIX}{descricao}",
        "category": categoria,
        "amount": "123.45",
        "expense_date": "2026-11-17",
        "disbursement_type": "fornecedor",
        "supplier_name": nome,
        "supplier_pix": pix,
        "receipt": (io.BytesIO(b"%PDF-1.4\n%%EOF\n"), "nota.pdf"),
    }
    if fornecedor_id is not None:
        form["fornecedor_id"] = str(fornecedor_id)
    r = _cliente_http(chave).post("/api/gastos", data=form, content_type="multipart/form-data")
    _garante(
        r.status_code == esperado,
        f"POST /api/gastos → {r.status_code} {r.get_data(as_text=True)[:300]}",
    )
    return r.get_json()


def _gasto(gasto_id: int):
    return _um(
        "SELECT fornecedor_id, supplier_name, supplier_pix, disbursement_type FROM special_expenses WHERE id = :i",
        i=gasto_id,
    )


def _fornecedor(fid: int):
    return _um(
        "SELECT nome, nome_normalizado, pix, categoria_padrao, ativo, criado_por_id FROM fornecedores WHERE id = :i",
        i=fid,
    )


def _pix_norm(pix: str | None) -> str | None:
    bruto = (pix or "").strip().lower()
    if bruto in ("", "-"):
        return None
    return (
        re.sub(r"\s+", "", bruto)
        if re.search(r"[a-z]", bruto)
        else (re.sub(r"\D", "", bruto) or None)
    )


# ───────────────────────────── História 3 — importação ─────────────────────────────


def cen_01_importacao() -> None:
    sem_vinculo = _um(
        "SELECT count(*) FROM special_expenses WHERE disbursement_type = 'fornecedor' AND fornecedor_id IS NULL "
        "AND category <> 'Multa de cancelamento'"
    )[0]
    _garante(sem_vinculo == 0, f"{sem_vinculo} gastos a fornecedor sem vínculo")
    multa_ligada = _um(
        "SELECT count(*) FROM special_expenses WHERE category = 'Multa de cancelamento' AND fornecedor_id IS NOT NULL"
    )[0]
    _garante(multa_ligada == 0, f"{multa_ligada} multas de cancelamento ligadas a fornecedor")
    fora = _um(
        "SELECT count(*) FROM special_expenses WHERE coalesce(disbursement_type, '') <> 'fornecedor' AND fornecedor_id IS NOT NULL"
    )[0]
    _garante(fora == 0, f"{fora} gastos que não são a fornecedor com vínculo")
    divergente = _um(
        "SELECT count(*) FROM special_expenses s JOIN fornecedores f ON f.id = s.fornecedor_id WHERE s.supplier_name <> f.nome"
    )[0]
    _garante(divergente == 0, f"{divergente} gastos com nome diferente do cadastro")
    for nome, normalizado in _no_banco("SELECT nome, nome_normalizado FROM fornecedores"):
        _garante(
            fornecedor_ops.normalizar_nome(nome) == normalizado,
            f"normalização diverge: {nome!r} → {normalizado!r}",
        )
    por_pix: dict[str, set[int]] = defaultdict(set)
    for pix, fid in _no_banco(
        "SELECT supplier_pix, fornecedor_id FROM special_expenses WHERE disbursement_type = 'fornecedor'"
    ):
        if _pix_norm(pix):
            por_pix[_pix_norm(pix)].add(fid)
    espalhados = {k: v for k, v in por_pix.items() if len(v) > 1}
    _garante(
        not espalhados, f"mesma chave PIX em fornecedores diferentes: {len(espalhados)} chaves"
    )
    total = _um(
        "SELECT count(*) FROM fornecedores WHERE nome_normalizado NOT LIKE :p", p=f"{NORM_PREFIX}%"
    )[0]
    _garante(total > 0, "nenhum fornecedor importado")
    print(f"         ({total} fornecedores importados)")


# ───────────────────────────── História 2 — cadastro automático ─────────────────────────────


def cen_02_nome_novo() -> None:
    nome = f"{PREFIX}Gráfica Nova"
    gasto = _lancar("fig", "banner", nome, pix="pix-novo@teste.local", categoria="Marketing")
    linha = _gasto(gasto["id"])
    _garante(linha[0] is not None, "gasto não ficou ligado")
    f = _fornecedor(linha[0])
    _garante(
        f[0] == nome and f[2] == "pix-novo@teste.local" and f[3] == "Marketing",
        f"fornecedor nasceu errado: {f}",
    )
    _garante(f[5] == estado["fig"], "criado_por não é quem lançou")
    _garante(gasto.get("fornecedor_id") == linha[0], "resposta sem fornecedor_id")
    estado["nova"] = linha[0]
    estado["gasto_nova_1"] = gasto["id"]


def cen_03_outra_grafia() -> None:
    gasto = _lancar(
        "fig",
        "banner 2",
        "__V352_GRAFICA   NOVA",
        pix="pix-novo@teste.local",
        categoria="Marketing",
    )
    linha = _gasto(gasto["id"])
    _garante(linha[0] == estado["nova"], f"ligou a {linha[0]}, esperado {estado['nova']}")
    _garante(linha[1] == f"{PREFIX}Gráfica Nova", f"gasto ficou com o nome digitado: {linha[1]!r}")
    quantos = _um(
        "SELECT count(*) FROM fornecedores WHERE nome_normalizado = :n", n="v352 grafica nova"
    )[0]
    _garante(quantos == 1, f"{quantos} fornecedores com o mesmo nome")
    estado["gasto_nova_2"] = gasto["id"]


# ───────────────────────────── História 1 — escolher preenche ─────────────────────────────


def cen_04_completa_sem_substituir() -> None:
    g1 = _lancar(
        "fig",
        "completa",
        f"{PREFIX}Sem Pix",
        pix="chave-nova",
        categoria="Escritório",
        fornecedor_id=estado["sem_pix"],
    )
    _garante(_gasto(g1["id"])[0] == estado["sem_pix"], "não ligou pelo id")
    f = _fornecedor(estado["sem_pix"])
    _garante(f[2] == "chave-nova" and f[3] == "Escritório", f"não completou: {f}")
    g2 = _lancar(
        "fig",
        "nao troca",
        f"{PREFIX}Com Pix",
        pix="chave-outra",
        categoria="Outros",
        fornecedor_id=estado["com_pix"],
    )
    f = _fornecedor(estado["com_pix"])
    _garante(f[2] == "chave-antiga" and f[3] == "Figurino", f"cadastro trocado pelo gasto: {f}")
    _garante(_gasto(g2["id"])[2] == "chave-outra", "gasto não guardou a chave digitada")
    estado["gasto_com_pix"] = g2["id"]


def cen_05_listagem_por_papel() -> None:
    r = _cliente_http("fig").get("/api/gastos/fornecedores")
    _garante(r.status_code == 200, f"GET Figurino → {r.status_code}")
    j = r.get_json()
    ids = {f["id"] for f in j["fornecedores"]}
    _garante(
        estado["arquivado"] not in ids and estado["com_pix"] in ids,
        "Figurino vê arquivado ou não vê ativo",
    )
    _garante(not j["can_manage"], "Figurino com can_manage")
    _garante(
        all(f.get("gastos") is None and f.get("total_aprovado") is None for f in j["fornecedores"]),
        "Figurino recebeu totais",
    )
    _garante(
        "Devolução a cliente" not in j["categorias"] and "Marketing" in j["categorias"],
        f"categorias: {j['categorias']}",
    )
    j = _cliente_http("fin").get("/api/gastos/fornecedores").get_json()
    por_id = {f["id"]: f for f in j["fornecedores"]}
    _garante(estado["arquivado"] in por_id and j["can_manage"], "Financeiro não vê arquivado")
    com_pix = por_id[estado["com_pix"]]
    _garante(
        com_pix["gastos"] == 1
        and com_pix["total_aprovado"] == 0
        and com_pix["ultimo_gasto"] == "2026-11-17",
        f"totais errados: {com_pix}",
    )
    # Nome de um arquivado (que não aparece na sugestão): liga a ele, sem nascer outro, e ele segue arquivado.
    g = _lancar("fig", "arquivado", "__V352_ARQUIVADO")
    _garante(_gasto(g["id"])[0] == estado["arquivado"], "não ligou ao arquivado")
    _garante(_fornecedor(estado["arquivado"])[4] is False, "o gasto reativou o arquivado")


# ───────────────────────────── História 4 — Financeiro arruma ─────────────────────────────


def cen_06_renomear() -> None:
    novo = f"{PREFIX}Gráfica Renomeada"
    r = _cliente_http("fin").patch(
        f"/api/gastos/fornecedores/{estado['nova']}", json={"nome": novo, "pix": "pix-trocado"}
    )
    _garante(r.status_code == 200, f"PATCH → {r.status_code} {r.get_data(as_text=True)[:200]}")
    f = _fornecedor(estado["nova"])
    _garante(
        f[0] == novo and f[1] == "v352 grafica renomeada" and f[2] == "pix-trocado",
        f"cadastro: {f}",
    )
    for chave in ("gasto_nova_1", "gasto_nova_2"):
        linha = _gasto(estado[chave])
        _garante(linha[1] == novo, f"gasto {estado[chave]} não renomeou: {linha[1]!r}")
        _garante(linha[2] == "pix-novo@teste.local", f"PIX do gasto mudou: {linha[2]!r}")
    r = _cliente_http("fin").patch(
        f"/api/gastos/fornecedores/{estado['nova']}", json={"ativo": False}
    )
    _garante(r.status_code == 200 and _fornecedor(estado["nova"])[4] is False, "não arquivou")
    _cliente_http("fin").patch(f"/api/gastos/fornecedores/{estado['nova']}", json={"ativo": True})
    _garante(_fornecedor(estado["nova"])[4] is True, "não reativou")


def cen_07_juntar() -> None:
    g = _lancar("fig", "duplicado", f"{PREFIX}Duplicado", pix="pix-dup")
    origem = _gasto(g["id"])[0]
    r = _cliente_http("fin").post(
        "/api/gastos/fornecedores",
        json={"nome": f"{PREFIX}Destino", "categoria_padrao": "Figurino"},
    )
    _garante(
        r.status_code == 201, f"POST fornecedor → {r.status_code} {r.get_data(as_text=True)[:200]}"
    )
    destino = r.get_json()["id"]
    estado["destino"] = destino
    r = _cliente_http("fin").post(
        f"/api/gastos/fornecedores/{origem}/juntar", json={"destino_id": destino}
    )
    _garante(
        r.status_code == 200 and r.get_json()["gastos_movidos"] == 1,
        f"juntar → {r.status_code} {r.get_data(as_text=True)[:200]}",
    )
    _garante(_fornecedor(origem) is None, "origem não foi apagada")
    linha = _gasto(g["id"])
    _garante(
        linha[0] == destino and linha[1] == f"{PREFIX}Destino" and linha[2] == "pix-dup",
        f"gasto após juntar: {linha}",
    )
    f = _fornecedor(destino)
    _garante(
        f[2] == "pix-dup" and f[3] == "Figurino",
        f"destino não completou ou trocou a categoria: {f}",
    )


def cen_08_validacoes() -> None:
    fin = _cliente_http("fin")
    casos = [
        (fin.post("/api/gastos/fornecedores", json={"nome": "__V352_DESTINO"}), "nome"),
        (fin.post("/api/gastos/fornecedores", json={"nome": "  "}), "nome"),
        (
            fin.post(
                "/api/gastos/fornecedores",
                json={"nome": f"{PREFIX}X", "categoria_padrao": "Devolução a cliente"},
            ),
            "categoria_padrao",
        ),
        (
            fin.patch(
                f"/api/gastos/fornecedores/{estado['com_pix']}", json={"nome": "__v352_destino"}
            ),
            "nome",
        ),
        (
            fin.post(
                f"/api/gastos/fornecedores/{estado['destino']}/juntar",
                json={"destino_id": estado["destino"]},
            ),
            "destino_id",
        ),
        (
            fin.post(
                f"/api/gastos/fornecedores/{estado['destino']}/juntar",
                json={"destino_id": 999999999},
            ),
            "destino_id",
        ),
    ]
    for r, campo in casos:
        _garante(
            r.status_code == 400 and campo in (r.get_json()["error"].get("fields") or {}),
            f"{campo}: {r.status_code} {r.get_data(as_text=True)[:200]}",
        )
    _garante(_fornecedor(estado["com_pix"])[0] == f"{PREFIX}Com Pix", "renome recusado gravou")
    _garante(
        _um("SELECT count(*) FROM fornecedores WHERE nome_normalizado = 'v352 x'")[0] == 0,
        "cadastro recusado gravou",
    )
    _garante(
        fin.patch("/api/gastos/fornecedores/999999999", json={"nome": "y"}).status_code == 404,
        "id inexistente sem 404",
    )


def cen_09_figurino_nao_gerencia() -> None:
    fig = _cliente_http("fig")
    antes = _fornecedor(estado["com_pix"])
    respostas = [
        fig.post("/api/gastos/fornecedores", json={"nome": f"{PREFIX}Intruso"}),
        fig.patch(
            f"/api/gastos/fornecedores/{estado['com_pix']}",
            json={"nome": f"{PREFIX}Invadido", "ativo": False},
        ),
        fig.post(
            f"/api/gastos/fornecedores/{estado['com_pix']}/juntar",
            json={"destino_id": estado["destino"]},
        ),
    ]
    _garante(
        [r.status_code for r in respostas] == [403, 403, 403],
        f"esperado 403: {[r.status_code for r in respostas]}",
    )
    _garante(_fornecedor(estado["com_pix"]) == antes, "Figurino alterou o cadastro")
    _garante(
        _um("SELECT count(*) FROM fornecedores WHERE nome_normalizado = 'v352 intruso'")[0] == 0,
        "Figurino cadastrou",
    )


def cen_10_deixa_de_ser_fornecedor() -> None:
    gid = estado["gasto_com_pix"]
    corpo = {
        "description": f"{PREFIX}nao troca",
        "category": "Outros",
        "amount": 123.45,
        "expense_date": "2026-11-17",
        "disbursement_type": "fornecedor",
        "supplier_name": f"{PREFIX}Com Pix",
        "supplier_pix": "chave-outra",
        "fornecedor_id": estado["com_pix"],
    }
    r = _cliente_http("fin").patch(f"/api/gastos/{gid}", json=corpo)
    _garante(
        r.status_code == 200 and _gasto(gid)[0] == estado["com_pix"],
        f"edição mantendo fornecedor: {r.status_code}",
    )
    corpo.update({"disbursement_type": "reembolso", "reimburse_user_id": estado["fin"]})
    r = _cliente_http("fin").patch(f"/api/gastos/{gid}", json=corpo)
    _garante(
        r.status_code == 200, f"PATCH reembolso → {r.status_code} {r.get_data(as_text=True)[:200]}"
    )
    _garante(_gasto(gid)[0] is None, "vínculo ficou no reembolso")
    # A multa de cancelamento paga o artista da escala: nunca cadastra nem liga fornecedor.
    multa = _lancar("fig", "multa", f"{PREFIX}Artista Multado", pix="pix-artista", categoria="Multa de cancelamento")
    _garante(_gasto(multa["id"])[0] is None, "multa ligada a fornecedor")
    _garante(
        _um("SELECT count(*) FROM fornecedores WHERE nome_normalizado = 'v352 artista multado'")[0] == 0,
        "multa cadastrou o artista como fornecedor",
    )


def cen_11_limpeza() -> None:
    with app.app_context():
        limpar()
    _garante(
        _um("SELECT count(*) FROM special_expenses WHERE description LIKE :p", p=f"{PREFIX}%")[0]
        == 0,
        "gasto sobrou",
    )
    _garante(
        _um(
            "SELECT count(*) FROM fornecedores WHERE nome_normalizado LIKE :p", p=f"{NORM_PREFIX}%"
        )[0]
        == 0,
        "fornecedor sobrou",
    )
    _garante(
        _um("SELECT count(*) FROM users WHERE email LIKE :p", p=f"{PREFIX}%")[0] == 0,
        "usuário sobrou",
    )


def main() -> int:
    print("Feature 352 — fornecedores cadastrados nos gastos extras")
    passos = [
        ("1. importação: vínculos, nomes e grupos por PIX", cen_01_importacao),
        ("2. nome novo cadastra o fornecedor", cen_02_nome_novo),
        ("3. outra grafia liga ao existente", cen_03_outra_grafia),
        ("4. completa o que falta, não substitui", cen_04_completa_sem_substituir),
        ("5. listagem por papel", cen_05_listagem_por_papel),
        ("6. renomear reescreve o nome, não o PIX", cen_06_renomear),
        ("7. juntar", cen_07_juntar),
        ("8. validações no campo", cen_08_validacoes),
        ("9. Figurino não gerencia (DEVE falhar)", cen_09_figurino_nao_gerencia),
        ("10. deixa de ser fornecedor e multa: sem vínculo", cen_10_deixa_de_ser_fornecedor),
    ]
    try:
        preparar()
        for nome, fn in passos:
            cenario(nome, fn)
    finally:
        cenario("11. limpeza", cen_11_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  ✗ {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
