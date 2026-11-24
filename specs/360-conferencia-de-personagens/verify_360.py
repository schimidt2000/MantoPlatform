"""Verificação da feature 360 — conferência de personagens do catálogo.

Cenários (spec §Verificação):
 1. Primeira carga da leitura real: cria conferências e personagens; resumo bate com a contagem por
    conexão separada; nenhuma tabela do catálogo muda.
 2. Segunda carga: nenhuma linha nova nem alterada.
 3. Alterar a decisão de um personagem e reler.
 4. Conferir um item; tema sem nenhum personagem "Criar" não confere.          (o segundo DEVE falhar)
 5. Item que ganha personagem no catálogo some da fila; as decisões seguem guardadas e voltam.
 6. Item que ganha ficha própria, é desativado ou vira página própria some da fila.
 7. Item pendente sem leitura aparece como "sem leitura", fora do total a conferir.
 8. Carga com item já decidido: a decisão humana fica intacta.
 9. Alterar item conferido: 409 `conferido`; reabrir preserva tudo.                    (DEVE falhar)
10. Corrigir nome, trocar e tirar ficha, "criar sem foto": o decidido muda, o proposto fica.
11. Acrescentar e excluir personagem à mão; excluir o da leitura é recusado. (o segundo DEVE falhar)
12. Mudar o tipo do item, ida e volta: elenco preservado; ficha do item só em avulso.
13. Nome vazio, tipo desconhecido, ficha inexistente e afins: 400 no campo, nada gravado.
                                                                                       (DEVE falhar)
14. Carga com referências quebradas (item, foto e ficha inexistentes): não falha.
15. Filtros, busca, ordem, contadores e "próximo item".
16. Comercial, Figurino e sem login em todos os endpoints: 403 e 401, nada gravado.   (DEVE falhar)
17. Excluir, depois da carga, foto, ficha e item que têm conferência: as exclusões seguem valendo.
18. Limpeza.

Requisições HTTP FORA do `app_context`; toda asserção de escrita lê por conexão separada.

O verify é dono das tabelas da conferência do espelho: recusa rodar se elas já tiverem linhas (use
`--recomecar` para esvaziar antes) e recusa banco que não seja local. `--manter` termina com a
leitura carregada e sem decisões, para a conferência de tela.

Rodar contra o espelho da feature (PowerShell, na raiz do repositório)::

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
    .venv\\Scripts\\python.exe specs\\360-conferencia-de-personagens\\verify_360.py
"""

from __future__ import annotations

import json
import os
import sys
import traceback
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

from app import create_app, db, limiter  # noqa: E402
from app.models import (  # noqa: E402
    CatalogCharacter,
    CatalogItem,
    CatalogItemImage,
    FigurinoSheet,
    Role,
    User,
)
from app.utils import strip_accents_lower  # noqa: E402

PREFIX = "__v360_"
SENHA = "verify-360-senha"
BASE = "/api/admin/catalogo/conferencia"
LEITURA = REPO_ROOT / "app" / "admin" / "dados" / "leitura_personagens.json"
# A regra da fila, escrita aqui à mão de propósito: o verify não pode pedir a resposta ao núcleo.
REGRA = """i.is_active AND i.figurino_sheet_id IS NULL
  AND NOT EXISTS (SELECT 1 FROM catalog_characters ch WHERE ch.catalog_item_id = i.id)
  AND NOT EXISTS (SELECT 1 FROM catalog_characters ch WHERE ch.own_item_id = i.id)"""
MANTER = "--manter" in sys.argv
RECOMECAR = "--recomecar" in sys.argv

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
_externo = create_engine(os.environ["DATABASE_URL"], future=True)


def _no_banco(sql: str, **params):
    with _externo.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def _um(sql: str, **params):
    linhas = _no_banco(sql, **params)
    return linhas[0] if linhas else None


def _executa(sql: str, **params) -> None:
    with _externo.begin() as conn:
        conn.execute(text(sql), params)


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001 — o verify relata a falha e segue para a limpeza
        with app.app_context():
            db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


# ── fotografias do banco (por conexão separada) ─────────────────────────────────────────────────


def foto_do_catalogo() -> tuple:
    """O que a conferência NÃO pode mudar (FR-014)."""
    return (
        tuple(
            _um(
                "SELECT count(*), coalesce(max(id),0), coalesce(sum(figurino_sheet_id),0), "
                "count(*) FILTER (WHERE is_active) FROM catalog_items"
            )
        ),
        tuple(
            _um(
                "SELECT count(*), coalesce(max(id),0), coalesce(sum(figurino_sheet_id),0) "
                "FROM catalog_characters"
            )
        ),
        tuple(_um("SELECT count(*), coalesce(max(id),0) FROM catalog_item_images")),
        tuple(_um("SELECT count(*), coalesce(max(id),0) FROM figurino_sheets")),
    )


def foto_da_conferencia() -> tuple:
    return (
        tuple(
            _um(
                "SELECT count(*), coalesce(max(id),0), max(updated_at), count(conferido_em) "
                "FROM catalog_conferencias"
            )
        ),
        tuple(
            _um(
                "SELECT count(*), coalesce(max(id),0), max(updated_at), "
                "count(*) FILTER (WHERE decisao = 'nao_criar') FROM catalog_conferencia_personagens"
            )
        ),
    )


def _personagem(pid: int):
    return _um(
        "SELECT nome, nome_lido, ficha_id, ficha_sugerida_id, decisao, sem_foto, sem_foto_lido, "
        "observacao, imagem_id, origem FROM catalog_conferencia_personagens WHERE id = :i",
        i=pid,
    )


def _conferencia(item_id: int):
    return _um(
        "SELECT id, tipo, tipo_lido, ficha_id, observacao, conferido_em, conferido_por_id "
        "FROM catalog_conferencias WHERE catalog_item_id = :i",
        i=item_id,
    )


def _personagens_de(item_id: int) -> list[int]:
    return [
        r[0]
        for r in _no_banco(
            "SELECT p.id FROM catalog_conferencia_personagens p JOIN catalog_conferencias c "
            "ON c.id = p.conferencia_id WHERE c.catalog_item_id = :i ORDER BY p.position, p.id",
            i=item_id,
        )
    ]


# ── preparação ──────────────────────────────────────────────────────────────────────────────────


def _usuario(sufixo: str, papel: str) -> int:
    user = User(
        name=f"{PREFIX}{sufixo}",
        email=f"{PREFIX}{sufixo}@manto.local",
        is_active=True,
        has_access=True,
    )
    user.set_password(SENHA)
    user.roles.append(Role.query.filter_by(name=papel).one())
    db.session.add(user)
    db.session.commit()
    return user.id


def _item_descartavel(sufixo: str, fotos: int = 0) -> int:
    item = CatalogItem(name=f"{PREFIX}{sufixo}", slug=f"v360-{sufixo.lower()}", is_active=True)
    db.session.add(item)
    db.session.flush()
    for posicao in range(fotos):
        db.session.add(
            CatalogItemImage(
                item_id=item.id,
                url=f"/catalogo/midia/{PREFIX}{sufixo.lower()}_{posicao}.jpg",
                position=posicao,
            )
        )
    db.session.commit()
    return item.id


def preparar() -> None:
    with app.app_context():
        limpar_descartaveis()
        estado["sa"] = _usuario("sa", "SUPERADMIN")
        estado["com"] = _usuario("com", "COMERCIAL")
        estado["fig"] = _usuario("fig", "FIGURINO")
        estado["item_sem_leitura"] = _item_descartavel("SemLeitura")
        estado["item_x"] = _item_descartavel("Descartavel", fotos=2)
        ficha = FigurinoSheet(character_name=f"{PREFIX}Ficha", character_name_norm="v360 ficha")
        db.session.add(ficha)
        db.session.commit()
        estado["ficha_x"] = ficha.id


def limpar_descartaveis() -> None:
    db.session.rollback()
    CatalogCharacter.query.filter(CatalogCharacter.name.like(f"{PREFIX}%")).delete(
        synchronize_session=False
    )
    for item in CatalogItem.query.filter(CatalogItem.name.like(f"{PREFIX}%")).all():
        db.session.delete(item)
    FigurinoSheet.query.filter(FigurinoSheet.character_name.like(f"{PREFIX}%")).delete(
        synchronize_session=False
    )
    for user in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        user.roles.clear()
        db.session.delete(user)
    db.session.commit()


def _cliente(chave: str | None):
    c = app.test_client()
    if chave:
        r = c.post(
            "/api/auth/login", json={"email": f"{PREFIX}{chave}@manto.local", "password": SENHA}
        )
        _garante(r.status_code == 200, f"login {chave} → {r.status_code}")
    return c


def _api(
    metodo: str,
    caminho: str,
    *,
    esperado: int = 200,
    corpo: dict | None = None,
    quem: str | None = "sa",
):
    """Uma requisição com sessão nova (login pela API). Devolve o JSON, ou `{}` sem corpo."""
    r = _cliente(quem).open(caminho, method=metodo, json=corpo)
    _garante(
        r.status_code == esperado,
        f"{metodo} {caminho} → {r.status_code} (esperado {esperado}) {r.get_data(as_text=True)[:300]}",
    )
    return r.get_json(silent=True) or {}


def _fila(**filtros) -> dict:
    consulta = "&".join(f"{k}={v}" for k, v in filtros.items())
    return _api("GET", f"{BASE}?{consulta}" if consulta else BASE)


def _escolher_itens() -> None:
    """Itens reais da fila para os cenários, escolhidos depois da carga."""
    temas = [
        r[0]
        for r in _no_banco(
            f"""SELECT c.catalog_item_id FROM catalog_conferencias c JOIN catalog_items i ON i.id = c.catalog_item_id
            WHERE {REGRA} AND c.tipo = 'tema'
              AND (SELECT count(*) FROM catalog_conferencia_personagens p
                    WHERE p.conferencia_id = c.id AND p.imagem_id IS NOT NULL) >= 3
            ORDER BY c.catalog_item_id LIMIT 5"""
        )
    ]
    avulsos = [
        r[0]
        for r in _no_banco(
            f"""SELECT c.catalog_item_id FROM catalog_conferencias c JOIN catalog_items i ON i.id = c.catalog_item_id
            WHERE {REGRA} AND c.tipo = 'avulso' ORDER BY c.catalog_item_id LIMIT 2"""
        )
    ]
    _garante(
        len(temas) == 5 and len(avulsos) == 2, f"fila sem itens para os cenários: {temas} {avulsos}"
    )
    estado.update(
        t1=temas[0],
        t2=temas[1],
        t3=temas[2],
        t4=temas[3],
        t5=temas[4],
        a1=avulsos[0],
        a2=avulsos[1],
    )


# ── cenários ────────────────────────────────────────────────────────────────────────────────────


def cen_01_primeira_carga() -> None:
    arquivo = json.loads(LEITURA.read_text(encoding="utf-8"))["itens"]
    ids = [i["id"] for i in arquivo]
    existentes = {
        r[0] for r in _no_banco("SELECT id FROM catalog_items WHERE id = ANY(:ids)", ids=ids)
    }
    esperados = [i for i in arquivo if i["id"] in existentes]
    antes = foto_do_catalogo()
    r = _api("POST", f"{BASE}/carregar")
    _garante(
        r["itens_novos"] == len(esperados), f"itens_novos {r['itens_novos']} ≠ {len(esperados)}"
    )
    _garante(
        r["personagens_novos"] == sum(len(i["personagens"]) for i in esperados),
        "personagens_novos não bate",
    )
    _garante(r["ja_existiam"] == 0, "ja_existiam deveria ser 0")
    _garante(len(r["ignorados"]) == len(arquivo) - len(esperados), "ignorados não bate")
    _garante(
        _um("SELECT count(*) FROM catalog_conferencias")[0] == r["itens_novos"],
        "linhas de conferência",
    )
    _garante(
        _um("SELECT count(*) FROM catalog_conferencia_personagens")[0] == r["personagens_novos"],
        "linhas de personagem",
    )
    _garante(foto_do_catalogo() == antes, "a carga alterou tabela do catálogo")
    # O decidido nasce igual ao proposto, em toda linha.
    _garante(
        _um(
            "SELECT count(*) FROM catalog_conferencias WHERE tipo <> tipo_lido "
            "OR ficha_id IS DISTINCT FROM ficha_sugerida_id OR conferido_em IS NOT NULL"
        )[0]
        == 0,
        "conferência nasceu diferente do proposto",
    )
    _garante(
        _um(
            "SELECT count(*) FROM catalog_conferencia_personagens WHERE nome <> nome_lido "
            "OR ficha_id IS DISTINCT FROM ficha_sugerida_id OR sem_foto <> sem_foto_lido "
            "OR decisao <> 'criar' OR origem <> 'leitura'"
        )[0]
        == 0,
        "personagem nasceu diferente do proposto",
    )
    yoda = _um("""SELECT p.ficha_sugerida_id, p.imagem_id, p.recorte, p.foto_largura FROM catalog_conferencia_personagens p
                  JOIN catalog_conferencias c ON c.id = p.conferencia_id
                  WHERE c.catalog_item_id = 700 AND p.nome_lido = 'Yoda'""")
    _garante(
        yoda is not None
        and yoda[1] is not None
        and json.loads(yoda[2]) == [29, 23, 33, 60]
        and yoda[3] == 905,
        f"Yoda do piloto não entrou como na leitura: {yoda}",
    )
    _garante(
        _um(
            "SELECT count(*) FROM catalog_conferencias WHERE tipo_lido = 'avulso' "
            "AND ficha_sugerida_id IS NOT NULL"
        )[0]
        > 0,
        "nenhum avulso com ficha sugerida",
    )
    _escolher_itens()


def cen_02_segunda_carga() -> None:
    antes = foto_da_conferencia()
    total = antes[0][0]
    r = _api("POST", f"{BASE}/carregar")
    _garante(
        r["itens_novos"] == 0 and r["personagens_novos"] == 0, f"segunda carga criou algo: {r}"
    )
    _garante(r["ja_existiam"] == total, f"ja_existiam {r['ja_existiam']} ≠ {total}")
    _garante(foto_da_conferencia() == antes, "segunda carga alterou a conferência")


def cen_03_decisao_do_personagem() -> None:
    pid = _personagens_de(estado["t1"])[0]
    estado["p_t1"] = pid
    r = _api("PATCH", f"{BASE}/personagens/{pid}", corpo={"decisao": "nao_criar"})
    _garante(_personagem(pid)[4] == "nao_criar", "decisão não gravada")
    devolvido = next(p for p in r["conferencia"]["personagens"] if p["id"] == pid)
    _garante(devolvido["decisao"] == "nao_criar", "resposta não traz a decisão nova")
    detalhe = _api("GET", f"{BASE}/{estado['t1']}")
    lido = next(p for p in detalhe["conferencia"]["personagens"] if p["id"] == pid)
    _garante(
        lido["decisao"] == "nao_criar" and lido["foto"] is not None, "detalhe não reflete a decisão"
    )


def cen_04_conferir() -> None:
    a1 = estado["a1"]
    r = _api("POST", f"{BASE}/{a1}/conferir")
    _garante(r["situacao"] == "conferido", "resposta não diz conferido")
    linha = _conferencia(a1)
    _garante(linha[5] is not None and linha[6] == estado["sa"], f"quem/quando não gravado: {linha}")
    fila = _fila(situacao="a_conferir")
    _garante(a1 not in [i["id"] for i in fila["itens"]], "conferido continua em 'a conferir'")
    _garante(fila["contadores"]["conferidos"] == 1, f"contador de conferidos: {fila['contadores']}")
    no_detalhe = _api("GET", f"{BASE}/{a1}")["conferencia"]
    _garante(
        no_detalhe["conferido_por"] == f"{PREFIX}sa" and no_detalhe["conferido_em"],
        "detalhe sem quem/quando",
    )
    # DEVE falhar: tema com todos os personagens em "não criar" (FR-017).
    t5 = estado["t5"]
    for pid in _personagens_de(t5):
        _api("PATCH", f"{BASE}/personagens/{pid}", corpo={"decisao": "nao_criar"})
    recusa = _api("POST", f"{BASE}/{t5}/conferir", esperado=400)
    _garante("tipo" in recusa["error"]["fields"], f"recusa sem apontar o tipo: {recusa}")
    _garante(_conferencia(t5)[5] is None, "tema sem personagem foi conferido")


def cen_05_item_ganha_personagem() -> None:
    t4 = estado["t4"]
    pid = _personagens_de(t4)[0]
    _api(
        "PATCH", f"{BASE}/personagens/{pid}", corpo={"observacao": "decisão antes de sair da fila"}
    )
    fila_antes = _fila()["contadores"]["fila"]
    with app.app_context():
        intruso = CatalogCharacter(catalog_item_id=t4, name=f"{PREFIX}Intruso", slug="v360-intruso")
        db.session.add(intruso)
        db.session.commit()
    try:
        fila = _fila()
        _garante(t4 not in [i["id"] for i in fila["itens"]], "item com elenco continua na fila")
        _garante(fila["contadores"]["fila"] == fila_antes - 1, "contador da fila não caiu")
        detalhe = _api("GET", f"{BASE}/{t4}")
        _garante(
            detalhe["na_fila"] is False and detalhe["conferencia"] is not None,
            "detalhe fora da fila",
        )
        _garante(
            _personagem(pid)[7] == "decisão antes de sair da fila", "decisão sumiu ao sair da fila"
        )
    finally:
        with app.app_context():
            CatalogCharacter.query.filter_by(slug="v360-intruso").delete()
            db.session.commit()
    fila = _fila()
    _garante(t4 in [i["id"] for i in fila["itens"]], "item não voltou para a fila")
    _garante(
        _personagem(pid)[7] == "decisão antes de sair da fila", "decisão não voltou com o item"
    )


def _fora_da_fila(item_id: int, motivo: str) -> None:
    _garante(item_id not in [i["id"] for i in _fila()["itens"]], f"item {motivo} continua na fila")


def cen_06_outras_saidas_da_fila() -> None:
    t4 = estado["t4"]
    _executa(
        "UPDATE catalog_items SET figurino_sheet_id = :f WHERE id = :i", f=estado["ficha_x"], i=t4
    )
    try:
        _fora_da_fila(t4, "com ficha própria")
    finally:
        _executa("UPDATE catalog_items SET figurino_sheet_id = NULL WHERE id = :i", i=t4)
    _executa("UPDATE catalog_items SET is_active = false WHERE id = :i", i=t4)
    try:
        _fora_da_fila(t4, "desativado")
    finally:
        _executa("UPDATE catalog_items SET is_active = true WHERE id = :i", i=t4)
    with app.app_context():
        dono = CatalogCharacter(
            catalog_item_id=estado["item_x"], name=f"{PREFIX}Dono", slug="v360-dono", own_item_id=t4
        )
        db.session.add(dono)
        db.session.commit()
    try:
        _fora_da_fila(t4, "que é página própria")
        # o item_x ganhou elenco e também saiu
        _fora_da_fila(estado["item_x"], "descartável com elenco")
    finally:
        with app.app_context():
            CatalogCharacter.query.filter_by(slug="v360-dono").delete()
            db.session.commit()
    _garante(t4 in [i["id"] for i in _fila()["itens"]], "item não voltou depois das três saídas")


def cen_07_sem_leitura() -> None:
    alvo = estado["item_sem_leitura"]
    fila = _fila()
    linha = next((i for i in fila["itens"] if i["id"] == alvo), None)
    _garante(linha is not None, "item pendente sem leitura não aparece na fila")
    _garante(linha["situacao"] == "sem_leitura" and linha["tipo"] is None, f"linha errada: {linha}")
    cont = fila["contadores"]
    _garante(cont["sem_leitura"] >= 1, "contador sem_leitura")
    _garante(
        cont["fila"] == cont["a_conferir"] + cont["conferidos"] + cont["sem_leitura"],
        f"soma: {cont}",
    )
    _garante(
        alvo not in [i["id"] for i in _fila(situacao="a_conferir")["itens"]],
        "sem leitura em 'a conferir'",
    )
    _garante(
        alvo in [i["id"] for i in _fila(situacao="sem_leitura")["itens"]], "filtro sem_leitura"
    )
    detalhe = _api("GET", f"{BASE}/{alvo}")
    _garante(
        detalhe["conferencia"] is None and detalhe["situacao"] == "sem_leitura",
        "detalhe sem leitura",
    )
    _api("POST", f"{BASE}/{alvo}/conferir", esperado=404)
    _api("PATCH", f"{BASE}/{alvo}", esperado=404, corpo={"observacao": "x"})


def cen_08_carga_nao_sobrescreve() -> None:
    a2 = estado["a2"]
    _executa("DELETE FROM catalog_conferencias WHERE catalog_item_id = :i", i=a2)
    r = _api("POST", f"{BASE}/carregar")
    _garante(r["itens_novos"] == 1, f"a carga deveria recriar só o item apagado: {r}")
    _garante(_conferencia(a2) is not None, "item apagado não voltou")
    _garante(_personagem(estado["p_t1"])[4] == "nao_criar", "carga desfez a decisão do cenário 3")
    _garante(_conferencia(estado["a1"])[5] is not None, "carga desfez o conferido do cenário 4")


def cen_09_conferido_trava() -> None:
    t2 = estado["t2"]
    pid = _personagens_de(t2)[0]
    _api("PATCH", f"{BASE}/personagens/{pid}", corpo={"nome": "Nome decidido antes"})
    _api("POST", f"{BASE}/{t2}/conferir")
    antes = foto_da_conferencia()
    for metodo, caminho, corpo in (
        ("PATCH", f"{BASE}/personagens/{pid}", {"decisao": "nao_criar"}),
        ("PATCH", f"{BASE}/{t2}", {"observacao": "não pode"}),
        ("POST", f"{BASE}/{t2}/personagens", {"nome": f"{PREFIX}Extra"}),
        ("POST", f"{BASE}/{t2}/conferir", None),
    ):
        recusa = _api(metodo, caminho, esperado=409, corpo=corpo)
        _garante(recusa["error"].get("codigo") == "conferido", f"409 sem código: {recusa}")
    _garante(foto_da_conferencia() == antes, "item conferido foi alterado")
    r = _api("POST", f"{BASE}/{t2}/reabrir")
    _garante(r["situacao"] == "a_conferir" and _conferencia(t2)[5] is None, "reabrir não reabriu")
    _garante(_personagem(pid)[0] == "Nome decidido antes", "reabrir perdeu a decisão")
    recusa = _api("POST", f"{BASE}/{t2}/reabrir", esperado=409)
    _garante(recusa["error"].get("codigo") == "nao_conferido", f"reabrir duas vezes: {recusa}")


def cen_10_corrigir() -> None:
    pid = _personagens_de(estado["t3"])[0]
    estado["p_t3"] = pid
    original = _personagem(pid)
    _api(
        "PATCH",
        f"{BASE}/personagens/{pid}",
        corpo={"nome": "  Poe Dameron  ", "ficha_id": estado["ficha_x"]},
    )
    agora = _personagem(pid)
    _garante(agora[0] == "Poe Dameron" and agora[1] == original[1], f"nome/nome_lido: {agora}")
    _garante(
        agora[2] == estado["ficha_x"] and agora[3] == original[3], f"ficha/ficha_sugerida: {agora}"
    )
    _api("PATCH", f"{BASE}/personagens/{pid}", corpo={"ficha_id": None})
    _garante(
        _personagem(pid)[2] is None and _personagem(pid)[0] == "Poe Dameron",
        "tirar ficha mexeu no resto",
    )
    _api(
        "PATCH",
        f"{BASE}/personagens/{pid}",
        corpo={"sem_foto": True, "observacao": "criança ao lado"},
    )
    _garante(
        _personagem(pid)[5] is True and _personagem(pid)[7] == "criança ao lado", "criar sem foto"
    )
    _api("PATCH", f"{BASE}/personagens/{pid}", corpo={"sem_foto": False})
    _garante(_personagem(pid)[5] is False, "voltar a usar a foto")
    sem_foto = _um(
        "SELECT id FROM catalog_conferencia_personagens WHERE sem_foto_lido ORDER BY id LIMIT 1"
    )
    _garante(sem_foto is not None, "a leitura não tem nenhum personagem sem foto para o teste")
    recusa = _api(
        "PATCH", f"{BASE}/personagens/{sem_foto[0]}", esperado=400, corpo={"sem_foto": False}
    )
    _garante("sem_foto" in recusa["error"]["fields"], f"recusa sem campo: {recusa}")


def cen_11_acrescentar_e_excluir() -> None:
    t3 = estado["t3"]
    quantos = len(_personagens_de(t3))
    r = _api("POST", f"{BASE}/{t3}/personagens", esperado=201, corpo={"nome": f"{PREFIX}Luna"})
    novo = [p for p in r["conferencia"]["personagens"] if p["nome"] == f"{PREFIX}Luna"][0]
    linha = _personagem(novo["id"])
    _garante(
        linha[9] == "manual" and linha[5] is True and linha[8] is None,
        f"acrescentado errado: {linha}",
    )
    _garante(_personagens_de(t3)[-1] == novo["id"], "acrescentado não entrou no fim")
    _api("DELETE", f"{BASE}/personagens/{novo['id']}")
    _garante(
        _personagem(novo["id"]) is None and len(_personagens_de(t3)) == quantos,
        "excluir o acrescentado",
    )
    # DEVE falhar: o da leitura não se exclui.
    recusa = _api("DELETE", f"{BASE}/personagens/{estado['p_t3']}", esperado=409)
    _garante(recusa["error"].get("codigo") == "da_leitura", f"409 sem código: {recusa}")
    _garante(_personagem(estado["p_t3"]) is not None, "personagem da leitura foi excluído")


def cen_12_mudar_tipo() -> None:
    t3 = estado["t3"]
    elenco = _personagens_de(t3)
    _api("PATCH", f"{BASE}/{t3}", corpo={"tipo": "generico", "observacao": "são figurantes"})
    linha = _conferencia(t3)
    _garante(
        linha[1] == "generico" and linha[2] == "tema" and linha[4] == "são figurantes",
        f"tipo: {linha}",
    )
    _garante(_personagens_de(t3) == elenco, "mudar o tipo apagou o elenco")
    recusa = _api("PATCH", f"{BASE}/{t3}", esperado=400, corpo={"ficha_id": estado["ficha_x"]})
    _garante(
        "ficha_id" in recusa["error"]["fields"], "ficha em item não avulso deveria ser recusada"
    )
    _api("PATCH", f"{BASE}/{t3}", corpo={"tipo": "avulso", "ficha_id": estado["ficha_x"]})
    _garante(_conferencia(t3)[3] == estado["ficha_x"], "ficha do avulso não gravada")
    _api("POST", f"{BASE}/{t3}/conferir")  # avulso confere sem elenco
    _api("POST", f"{BASE}/{t3}/reabrir")
    _api("PATCH", f"{BASE}/{t3}", corpo={"tipo": "tema"})
    linha = _conferencia(t3)
    _garante(
        linha[1] == "tema" and linha[3] == estado["ficha_x"],
        "voltar a tema perdeu a ficha guardada",
    )
    _garante(_personagens_de(t3) == elenco, "elenco não voltou")


def cen_13_validacoes() -> None:
    pid, t3 = estado["p_t3"], estado["t3"]
    antes = (foto_da_conferencia(), _personagem(pid), _conferencia(t3))
    casos = (
        ("PATCH", f"{BASE}/personagens/{pid}", {"nome": "   "}, "nome"),
        ("PATCH", f"{BASE}/personagens/{pid}", {"nome": "x" * 201}, "nome"),
        ("PATCH", f"{BASE}/personagens/{pid}", {"ficha_id": 99999999}, "ficha_id"),
        ("PATCH", f"{BASE}/personagens/{pid}", {"decisao": "talvez"}, "decisao"),
        ("PATCH", f"{BASE}/personagens/{pid}", {"observacao": "x" * 1001}, "observacao"),
        ("PATCH", f"{BASE}/personagens/{pid}", {"sem_foto": "sim"}, "sem_foto"),
        ("PATCH", f"{BASE}/{t3}", {"tipo": "xpto"}, "tipo"),
        ("PATCH", f"{BASE}/{t3}", {"observacao": "x" * 1001}, "observacao"),
        ("POST", f"{BASE}/{t3}/personagens", {"nome": ""}, "nome"),
        ("POST", f"{BASE}/{t3}/personagens", {"nome": "Ok", "ficha_id": 99999999}, "ficha_id"),
    )
    for metodo, caminho, corpo, campo in casos:
        recusa = _api(metodo, caminho, esperado=400, corpo=corpo)
        _garante(campo in recusa["error"]["fields"], f"{corpo} sem apontar {campo}: {recusa}")
    _garante(
        (foto_da_conferencia(), _personagem(pid), _conferencia(t3)) == antes,
        "validação recusada gravou algo",
    )
    _api("GET", f"{BASE}/99999999", esperado=404)
    _api("PATCH", f"{BASE}/personagens/99999999", esperado=404, corpo={"nome": "x"})


def cen_14_referencias_quebradas() -> None:
    from app.admin import catalog_conferencia_ops as ops

    x = estado["item_x"]
    foto_boa = _um(
        "SELECT url FROM catalog_item_images WHERE item_id = :i ORDER BY position LIMIT 1", i=x
    )[0]
    dados = [
        {"id": 99999999, "nome": "Fantasma", "tipo": "tema", "lote": "vv", "personagens": []},
        {
            "id": x,
            "nome": "Descartável",
            "tipo": "tema",
            "lote": "vv",
            "nota": "nota do verify",
            "acao": None,
            "grupo": None,
            "ficha_id": None,
            "personagens": [
                {
                    "nome": "Foto Sumida",
                    "foto": "nao_existe.jpg",
                    "dims": [100, 100],
                    "recorte": [0, 0, 50, 50],
                    "ficha_id": None,
                    "ficha_nome": None,
                    "aviso": "aviso do leitor",
                    "sem_foto": False,
                },
                {
                    "nome": "Ficha Sumida",
                    "foto": None,
                    "dims": None,
                    "recorte": None,
                    "ficha_id": 99999999,
                    "ficha_nome": "Fantasma",
                    "aviso": None,
                    "sem_foto": True,
                },
                {
                    "nome": "Tudo Certo",
                    "foto": foto_boa.rsplit("/", 1)[-1],
                    "dims": [800, 1200],
                    "recorte": [10, 10, 40, 80],
                    "ficha_id": estado["ficha_x"],
                    "ficha_nome": "Ficha",
                    "aviso": None,
                    "sem_foto": False,
                },
            ],
        },
    ]
    with app.app_context():
        resumo = ops.carregar_leitura(dados)
    _garante(resumo["itens_novos"] == 1 and resumo["personagens_novos"] == 3, f"resumo: {resumo}")
    _garante(
        [i["id"] for i in resumo["ignorados"]] == [99999999], f"ignorados: {resumo['ignorados']}"
    )
    linhas = _no_banco(
        """SELECT p.nome, p.imagem_id, p.sem_foto_lido, p.sem_foto, p.ficha_id, p.aviso
           FROM catalog_conferencia_personagens p JOIN catalog_conferencias c ON c.id = p.conferencia_id
           WHERE c.catalog_item_id = :i ORDER BY p.position""",
        i=x,
    )
    sumida, sem_ficha, certo = linhas
    _garante(
        sumida[1] is None
        and sumida[2]
        and sumida[3]
        and "aviso do leitor" in sumida[5]
        and "galeria" in sumida[5],
        f"foto sumida: {sumida}",
    )
    _garante(
        sem_ficha[4] is None and "Fantasma" in (sem_ficha[5] or ""), f"ficha sumida: {sem_ficha}"
    )
    _garante(
        certo[1] is not None
        and not certo[2]
        and certo[4] == estado["ficha_x"]
        and certo[5] is None,
        f"personagem íntegro: {certo}",
    )


def cen_15_filtros_e_contadores() -> None:
    fila = _fila()
    ids = [i["id"] for i in fila["itens"]]
    esperados = {r[0] for r in _no_banco(f"SELECT i.id FROM catalog_items i WHERE {REGRA}")}
    _garante(set(ids) == esperados and len(ids) == len(esperados), "a fila não é a regra")
    cont = fila["contadores"]
    _garante(cont["fila"] == len(esperados), f"contador fila {cont['fila']} ≠ {len(esperados)}")
    _garante(
        cont["fila"] == cont["a_conferir"] + cont["conferidos"] + cont["sem_leitura"],
        f"soma: {cont}",
    )
    _garante(
        sum(t["total"] for t in cont["por_tipo"].values())
        == cont["a_conferir"] + cont["conferidos"],
        "por_tipo não soma",
    )
    _garante(
        sum(t["conferidos"] for t in cont["por_tipo"].values()) == cont["conferidos"],
        "por_tipo conferidos",
    )
    nomes = [strip_accents_lower(i["nome"]) for i in fila["itens"]]
    _garante(nomes == sorted(nomes), "fila fora de ordem alfabética")
    avulsos = _fila(tipo="avulso")
    _garante(
        avulsos["itens"] and all(i["tipo"] == "avulso" for i in avulsos["itens"]), "filtro por tipo"
    )
    _garante(avulsos["contadores"] == cont, "contadores mudaram com o filtro")
    conferidos = _fila(situacao="conferido")
    _garante(
        conferidos["itens"] and all(i["situacao"] == "conferido" for i in conferidos["itens"]),
        "filtro por situação",
    )
    combinado = _fila(tipo="avulso", situacao="a_conferir")
    _garante(
        all(i["tipo"] == "avulso" and i["situacao"] == "a_conferir" for i in combinado["itens"]),
        "filtros combinados",
    )
    com_acento = next(
        i for i in fila["itens"] if strip_accents_lower(i["nome"]) != i["nome"].lower()
    )
    termo = strip_accents_lower(com_acento["nome"])[:6].upper()
    busca = _fila(q=termo)
    _garante(
        com_acento["id"] in [i["id"] for i in busca["itens"]],
        f"busca '{termo}' não achou o item acentuado",
    )
    _garante(
        all(termo.lower() in strip_accents_lower(i["nome"]) for i in busca["itens"]),
        "busca trouxe item a mais",
    )
    # "Próximo" respeita a ordem da fila e o filtro de tipo.
    a_conferir = [i["id"] for i in _fila(tipo="avulso", situacao="a_conferir")["itens"]]
    detalhe = _api("GET", f"{BASE}/{a_conferir[0]}?tipo=avulso")
    _garante(
        detalhe["proximo_id"] == a_conferir[1], f"próximo {detalhe['proximo_id']} ≠ {a_conferir[1]}"
    )
    _garante(detalhe["anterior_id"] is None, "o primeiro não tem anterior")
    segundo = _api("GET", f"{BASE}/{a_conferir[1]}?tipo=avulso")
    _garante(segundo["anterior_id"] == a_conferir[0], "anterior do segundo")
    _garante(_fila(tipo="xpto")["itens"] == fila["itens"], "tipo desconhecido deveria ser ignorado")


def cen_16_rbac() -> None:
    pid, t3 = estado["p_t3"], estado["t3"]
    rotas = (
        ("GET", BASE, None),
        ("GET", f"{BASE}/{t3}", None),
        ("POST", f"{BASE}/carregar", None),
        ("PATCH", f"{BASE}/{t3}", {"observacao": "intruso"}),
        ("POST", f"{BASE}/{t3}/conferir", None),
        ("POST", f"{BASE}/{t3}/reabrir", None),
        ("POST", f"{BASE}/{t3}/personagens", {"nome": f"{PREFIX}Intruso"}),
        ("PATCH", f"{BASE}/personagens/{pid}", {"nome": "intruso"}),
        ("DELETE", f"{BASE}/personagens/{pid}", None),
    )
    antes = foto_da_conferencia()
    for quem, esperado in (("com", 403), ("fig", 403), (None, 401)):
        for metodo, caminho, corpo in rotas:
            _api(metodo, caminho, esperado=esperado, corpo=corpo, quem=quem)
    _garante(foto_da_conferencia() == antes, "papel sem permissão gravou algo")


def cen_17_exclusoes_seguem_valendo() -> None:
    x = estado["item_x"]
    linhas = _no_banco(
        """SELECT p.id, p.imagem_id, p.ficha_id FROM catalog_conferencia_personagens p
           JOIN catalog_conferencias c ON c.id = p.conferencia_id WHERE c.catalog_item_id = :i
           ORDER BY p.position""",
        i=x,
    )
    certo = linhas[2]
    with app.app_context():
        db.session.delete(db.session.get(CatalogItemImage, certo[1]))
        db.session.commit()
    _garante(_personagem(certo[0])[8] is None, "excluir a foto não anulou a referência")
    detalhe = _api("GET", f"{BASE}/{x}")
    sem_foto = next(p for p in detalhe["conferencia"]["personagens"] if p["id"] == certo[0])
    _garante(sem_foto["foto"] is None, "personagem ainda mostra foto excluída")
    with app.app_context():
        db.session.delete(db.session.get(FigurinoSheet, estado["ficha_x"]))
        db.session.commit()
    _garante(_personagem(certo[0])[2] is None, "excluir a ficha não anulou a referência")
    _garante(_conferencia(estado["t3"])[3] is None, "ficha excluída ficou na conferência do item")
    _cliente("sa").delete(f"/api/admin/catalogo/{x}")
    _garante(
        _um("SELECT 1 FROM catalog_items WHERE id = :i", i=x) is None,
        "o item não foi excluído pela API",
    )
    _garante(_conferencia(x) is None, "a conferência não foi junto com o item")
    _garante(not _personagens_de(x), "personagens órfãos depois de excluir o item")


def cen_18_limpeza() -> None:
    with app.app_context():
        limpar_descartaveis()
    _executa("DELETE FROM catalog_conferencias")
    _garante(
        _um("SELECT count(*) FROM catalog_conferencia_personagens")[0] == 0, "personagem sobrou"
    )
    _garante(
        _um("SELECT count(*) FROM users WHERE email LIKE :p", p=f"{PREFIX}%")[0] == 0,
        "usuário sobrou",
    )
    _garante(
        _um("SELECT count(*) FROM catalog_items WHERE name LIKE :p", p=f"{PREFIX}%")[0] == 0,
        "item sobrou",
    )
    _garante(
        _um("SELECT count(*) FROM figurino_sheets WHERE character_name LIKE :p", p=f"{PREFIX}%")[0]
        == 0,
        "ficha sobrou",
    )
    _garante(
        _um("SELECT count(*) FROM catalog_characters WHERE name LIKE :p", p=f"{PREFIX}%")[0] == 0,
        "personagem do catálogo sobrou",
    )
    _garante(
        foto_do_catalogo() == estado["catalogo_no_inicio"],
        "o catálogo terminou diferente do que começou",
    )
    if MANTER:
        from app.admin import catalog_conferencia_ops as ops

        with app.app_context():
            resumo = ops.carregar_leitura(ops.ler_arquivo_da_leitura())
        print(f"         --manter: leitura carregada ({resumo['itens_novos']} itens)")


def main() -> int:
    print("Feature 360 — conferência de personagens do catálogo")
    url = os.environ["DATABASE_URL"]
    if "@localhost" not in url and "@127.0.0.1" not in url:
        print("RECUSADO: este verify só roda contra banco local.")
        return 2
    if RECOMECAR:
        _executa("DELETE FROM catalog_conferencias")
    if _um("SELECT count(*) FROM catalog_conferencias")[0]:
        print("RECUSADO: o espelho já tem conferência. Use --recomecar para esvaziar antes.")
        return 2
    estado["catalogo_no_inicio"] = foto_do_catalogo()
    passos = [
        ("1. primeira carga da leitura real", cen_01_primeira_carga),
        ("2. segunda carga não muda nada", cen_02_segunda_carga),
        ("3. decisão do personagem gravada e relida", cen_03_decisao_do_personagem),
        ("4. conferir; tema sem personagem não confere (DEVE falhar)", cen_04_conferir),
        (
            "5. item que ganha personagem sai da fila e volta com as decisões",
            cen_05_item_ganha_personagem,
        ),
        (
            "6. ficha própria, desativado e página própria saem da fila",
            cen_06_outras_saidas_da_fila,
        ),
        ("7. item pendente sem leitura", cen_07_sem_leitura),
        ("8. carga não sobrescreve decisão humana", cen_08_carga_nao_sobrescreve),
        ("9. conferido trava; reabrir preserva (DEVE falhar)", cen_09_conferido_trava),
        ("10. corrigir nome, ficha e foto", cen_10_corrigir),
        (
            "11. acrescentar e excluir; o da leitura não se exclui (DEVE falhar)",
            cen_11_acrescentar_e_excluir,
        ),
        ("12. mudar o tipo, ida e volta", cen_12_mudar_tipo),
        ("13. validações no campo (DEVE falhar)", cen_13_validacoes),
        ("14. carga com referências quebradas", cen_14_referencias_quebradas),
        ("15. filtros, busca, ordem, contadores e próximo", cen_15_filtros_e_contadores),
        ("16. Comercial, Figurino e sem login (DEVE falhar)", cen_16_rbac),
        ("17. excluir foto, ficha e item segue valendo", cen_17_exclusoes_seguem_valendo),
    ]
    try:
        preparar()
        for nome, fn in passos:
            cenario(nome, fn)
    finally:
        cenario("18. limpeza", cen_18_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  ✗ {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
