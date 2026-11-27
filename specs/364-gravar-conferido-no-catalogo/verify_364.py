"""Verificação da feature 364 — gravar no catálogo o que a conferência aprovou.

Cenários (spec §Verificação):
 1. Resumo do que falta gravar bate com SQL independente.
 2. Gravar um tema conferido: personagens com nome, ficha e ordem decididos; "não criar" fica de fora.
 3. Foto recortada: arquivo novo em disco, na proporção do recorte; "sem foto" nasce sem foto.
 4. Avulso com ficha liga a ficha; avulso sem ficha e genérico só ficam marcados.
 5. Item gravado sai da fila; item não conferido fica intacto.
 6. Gravar de novo: zero personagens novos.
 7. Foto que não existe no disco: personagem criado sem foto, lote segue.
 8. Ajustes das observações: foto, "sem foto", elenco novo; ajuste sem alvo é ignorado.
 9. Comercial, Figurino e sem login: 403 e 401, nada gravado.                        (DEVE falhar)
10. Limpeza: tudo o que a gravação fez é desfeito; catálogo e conferência iguais ao início.

Roda contra o espelho `manto_364` (dump de produção de 26/11, com a conferência parcial). As fotos do
tema de teste são copiadas de `C:\\tmp\\catalogo_personagens\\fotos` para a pasta de mídia da worktree.
HTTP fora do `app_context`; escrita conferida por conexão separada.

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
    .venv\\Scripts\\python.exe specs\\364-gravar-conferido-no-catalogo\\verify_364.py
"""

from __future__ import annotations

import json
import os
import shutil
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

from PIL import Image  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter  # noqa: E402
from app.admin import catalog_gravacao_ops as ops  # noqa: E402
from app.models import Role, User  # noqa: E402

PREFIX = "__v364_"
SENHA = "verify-364-senha"
BASE = "/api/admin/catalogo/conferencia"
FOTOS_LOCAIS = Path(r"C:\tmp\catalogo_personagens\fotos")
REGRA = """i.is_active AND i.figurino_sheet_id IS NULL
  AND NOT EXISTS (SELECT 1 FROM catalog_characters ch WHERE ch.catalog_item_id = i.id)
  AND NOT EXISTS (SELECT 1 FROM catalog_characters ch WHERE ch.own_item_id = i.id)"""
CONFERIDO_NA_FILA = f"""FROM catalog_conferencias c JOIN catalog_items i ON i.id = c.catalog_item_id
  WHERE {REGRA} AND c.conferido_em IS NOT NULL AND c.gravado_em IS NULL"""

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False
PASTA = Path(app.config["UPLOAD_FOLDER"]) / "catalog_photos"

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
    except Exception as exc:  # noqa: BLE001 — relata e segue para a limpeza
        with app.app_context():
            db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def foto_do_catalogo() -> tuple:
    return (
        tuple(
            _um(
                "SELECT count(*), coalesce(max(id),0), coalesce(sum(figurino_sheet_id),0) FROM catalog_items"
            )
        ),
        tuple(_um("SELECT count(*), coalesce(max(id),0) FROM catalog_characters")),
        tuple(_um("SELECT count(*), coalesce(max(id),0) FROM figurino_sheets")),
    )


def _gravar(item_id: int) -> dict:
    with app.app_context():
        return ops.gravar_lote(somente_item_id=item_id)


def _elenco(item_id: int):
    return _no_banco(
        "SELECT id, name, figurino_sheet_id, photo_url, position FROM catalog_characters "
        "WHERE catalog_item_id = :i ORDER BY position, id",
        i=item_id,
    )


def _cliente(chave: str | None):
    c = app.test_client()
    if chave:
        r = c.post(
            "/api/auth/login", json={"email": f"{PREFIX}{chave}@manto.local", "password": SENHA}
        )
        _garante(r.status_code == 200, f"login {chave} → {r.status_code}")
    return c


# ── preparação ──────────────────────────────────────────────────────────────────────────────────


def _apagar_usuarios() -> None:
    db.session.rollback()
    for user in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        user.roles.clear()
        db.session.delete(user)
    db.session.commit()


def _tema_com_fotos_locais(exceto: set[int]) -> int:
    """Tema conferido na fila, com 3+ personagens com foto cujos arquivos existem na pasta local."""
    candidatos = _no_banco(
        f"""SELECT c.catalog_item_id {CONFERIDO_NA_FILA} AND c.tipo = 'tema'
            AND (SELECT count(*) FROM catalog_conferencia_personagens p
                  WHERE p.conferencia_id = c.id AND p.imagem_id IS NOT NULL AND NOT p.sem_foto) >= 3
            ORDER BY c.catalog_item_id"""
    )
    for (item_id,) in candidatos:
        if item_id in exceto:
            continue
        urls = [
            r[0]
            for r in _no_banco(
                """SELECT DISTINCT g.url FROM catalog_conferencia_personagens p
               JOIN catalog_conferencias c ON c.id = p.conferencia_id
               JOIN catalog_item_images g ON g.id = p.imagem_id WHERE c.catalog_item_id = :i""",
                i=item_id,
            )
        ]
        if urls and all((FOTOS_LOCAIS / u.rsplit("/", 1)[-1]).is_file() for u in urls):
            estado.setdefault("urls", {})[item_id] = urls
            return item_id
    raise AssertionError("nenhum tema conferido com fotos locais para o teste")


def _um_item(tipo: str, extra: str = "") -> int:
    linha = _um(
        f"SELECT c.catalog_item_id {CONFERIDO_NA_FILA} AND c.tipo = :t {extra} ORDER BY 1 LIMIT 1",
        t=tipo,
    )
    _garante(linha is not None, f"nenhum item {tipo} {extra} conferido na fila")
    return linha[0]


def preparar() -> None:
    estado["catalogo"] = foto_do_catalogo()
    estado["personagens_antes"] = _no_banco(
        "SELECT id, decisao, sem_foto, imagem_id, recorte, foto_largura, foto_altura "
        "FROM catalog_conferencia_personagens"
    )
    estado["tipos_antes"] = _no_banco("SELECT id, tipo FROM catalog_conferencias")
    estado["arquivos_antes"] = {p.name for p in PASTA.glob("*")} if PASTA.is_dir() else set()
    PASTA.mkdir(parents=True, exist_ok=True)
    with app.app_context():
        _apagar_usuarios()
        for sufixo, papel in (("sa", "SUPERADMIN"), ("com", "COMERCIAL"), ("fig", "FIGURINO")):
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
    t = estado["t"] = _tema_com_fotos_locais(set())
    estado["t2"] = _tema_com_fotos_locais({t})  # as fotos deste NÃO são copiadas (cenário 7)
    estado["t3"] = _tema_com_fotos_locais({t, estado["t2"]})  # alvo dos ajustes (cenário 8)
    for url in estado["urls"][t] + estado["urls"][estado["t3"]]:
        nome = url.rsplit("/", 1)[-1]
        shutil.copyfile(FOTOS_LOCAIS / nome, PASTA / nome)
    estado["a_ficha"] = _um_item("avulso", "AND c.ficha_id IS NOT NULL")
    estado["a_sem"] = _um_item("avulso", "AND c.ficha_id IS NULL")
    estado["g"] = _um_item("generico")
    nao = _um(f"""SELECT c.catalog_item_id FROM catalog_conferencias c JOIN catalog_items i ON i.id = c.catalog_item_id
                  WHERE {REGRA} AND c.conferido_em IS NULL AND c.tipo = 'tema' ORDER BY 1 LIMIT 1""")
    _garante(nao is not None, "nenhum tema não conferido no espelho")
    estado["nao_conferido"] = nao[0]
    # No tema de teste: o 1º personagem com foto vira "não criar" e o 2º vira "criar sem foto".
    com_foto = [
        r[0]
        for r in _no_banco(
            """SELECT p.id FROM catalog_conferencia_personagens p JOIN catalog_conferencias c ON c.id = p.conferencia_id
           WHERE c.catalog_item_id = :i AND p.imagem_id IS NOT NULL AND NOT p.sem_foto ORDER BY p.position, p.id""",
            i=t,
        )
    ]
    estado["p_nao"], estado["p_sem"] = com_foto[0], com_foto[1]
    _executa(
        "UPDATE catalog_conferencia_personagens SET decisao = 'nao_criar' WHERE id = :i",
        i=com_foto[0],
    )
    _executa(
        "UPDATE catalog_conferencia_personagens SET sem_foto = true WHERE id = :i", i=com_foto[1]
    )


# ── cenários ────────────────────────────────────────────────────────────────────────────────────


def cen_01_resumo() -> None:
    r = _cliente("sa").get(f"{BASE}/gravacao")
    _garante(r.status_code == 200, f"GET gravacao → {r.status_code}")
    dados = r.get_json()
    _garante(
        dados["itens_a_gravar"] == _um(f"SELECT count(*) {CONFERIDO_NA_FILA}")[0],
        f"itens_a_gravar: {dados}",
    )
    esperado = _um(
        f"""SELECT count(*) FROM catalog_conferencia_personagens p WHERE p.decisao = 'criar'
            AND p.catalog_character_id IS NULL AND p.conferencia_id IN
            (SELECT c.id {CONFERIDO_NA_FILA} AND c.tipo IN ('tema','dupla'))"""
    )[0]
    _garante(dados["personagens_a_criar"] == esperado, f"personagens_a_criar {dados} ≠ {esperado}")
    fichas = _um(
        f"SELECT count(*) {CONFERIDO_NA_FILA} AND c.tipo = 'avulso' AND c.ficha_id IS NOT NULL"
    )[0]
    _garante(dados["fichas_a_ligar"] == fichas and dados["itens_gravados"] == 0, f"resumo: {dados}")


def cen_02_tema() -> None:
    t = estado["t"]
    propostos = _no_banco(
        """SELECT p.id, p.nome, p.ficha_id, p.decisao FROM catalog_conferencia_personagens p
           JOIN catalog_conferencias c ON c.id = p.conferencia_id WHERE c.catalog_item_id = :i
           ORDER BY p.position, p.id""",
        i=t,
    )
    r = _gravar(t)
    criar = [p for p in propostos if p[3] == "criar"]
    _garante(
        r["itens_gravados"] == 1 and r["personagens_criados"] == len(criar) and not r["falhas"],
        f"lote: {r}",
    )
    elenco = _elenco(t)
    _garante(
        [e[1] for e in elenco] == [p[1] for p in criar],
        "nomes ou ordem do elenco não batem com a conferência",
    )
    _garante([e[2] for e in elenco] == [p[2] for p in criar], "fichas do elenco não batem")
    _garante([e[4] for e in elenco] == list(range(len(criar))), "posições não são sequenciais")
    ligados = _no_banco(
        """SELECT p.id, p.catalog_character_id FROM catalog_conferencia_personagens p
           JOIN catalog_conferencias c ON c.id = p.conferencia_id WHERE c.catalog_item_id = :i""",
        i=t,
    )
    _garante(
        all((cid is not None) == (pid != estado["p_nao"]) for pid, cid in ligados),
        "vínculo com o personagem",
    )
    _garante(
        _um("SELECT gravado_em FROM catalog_conferencias WHERE catalog_item_id = :i", i=t)[0]
        is not None,
        "gravado_em não marcado",
    )
    slugs = [
        r[0]
        for r in _no_banco("SELECT slug FROM catalog_characters WHERE catalog_item_id = :i", i=t)
    ]
    _garante(len(set(slugs)) == len(slugs), "endereços repetidos")


def cen_03_foto() -> None:
    linhas = _no_banco(
        """SELECT p.id, p.recorte, ch.photo_url, g.url FROM catalog_conferencia_personagens p
           JOIN catalog_conferencias c ON c.id = p.conferencia_id
           JOIN catalog_characters ch ON ch.id = p.catalog_character_id
           LEFT JOIN catalog_item_images g ON g.id = p.imagem_id WHERE c.catalog_item_id = :i""",
        i=estado["t"],
    )
    com_foto = 0
    for pid, recorte, photo_url, origem in linhas:
        if pid == estado["p_sem"]:
            _garante(photo_url is None, "personagem 'criar sem foto' nasceu com foto")
            continue
        if not recorte:
            _garante(photo_url is None, "personagem sem recorte nasceu com foto")
            continue
        _garante(
            photo_url and photo_url.startswith("/catalogo/midia/"),
            f"foto fora da rota pública: {photo_url}",
        )
        _garante(photo_url != origem, "a foto do personagem é o arquivo da galeria, não um recorte")
        arquivo = PASTA / photo_url.rsplit("/", 1)[-1]
        _garante(arquivo.is_file(), f"recorte não está no disco: {arquivo.name}")
        _x, _y, corte_l, corte_a = json.loads(recorte)
        with (
            Image.open(PASTA / origem.rsplit("/", 1)[-1]) as original,
            Image.open(arquivo) as cortada,
        ):
            esperado = (original.width * corte_l) / (original.height * corte_a)
            obtido = cortada.width / cortada.height
        _garante(
            abs(esperado - obtido) / esperado < 0.03, f"proporção {obtido:.3f} ≠ {esperado:.3f}"
        )
        com_foto += 1
    _garante(com_foto >= 1, "nenhum recorte foi conferido")


def cen_04_avulso_e_generico() -> None:
    ficha = _um(
        "SELECT ficha_id FROM catalog_conferencias WHERE catalog_item_id = :i", i=estado["a_ficha"]
    )[0]
    r = _gravar(estado["a_ficha"])
    _garante(r["fichas_ligadas"] == 1, f"ficha não ligada: {r}")
    _garante(
        _um("SELECT figurino_sheet_id FROM catalog_items WHERE id = :i", i=estado["a_ficha"])[0]
        == ficha,
        "item avulso sem a ficha decidida",
    )
    for chave in ("a_sem", "g"):
        r = _gravar(estado[chave])
        _garante(
            r["itens_gravados"] == 1 and r["personagens_criados"] == 0 and r["fichas_ligadas"] == 0,
            f"{chave}: {r}",
        )
        _garante(
            _um("SELECT figurino_sheet_id FROM catalog_items WHERE id = :i", i=estado[chave])[0]
            is None,
            f"{chave} ganhou ficha",
        )
        _garante(not _elenco(estado[chave]), f"{chave} ganhou elenco")
        _garante(
            _um(
                "SELECT gravado_em FROM catalog_conferencias WHERE catalog_item_id = :i",
                i=estado[chave],
            )[0]
            is not None,
            f"{chave} não ficou marcado",
        )


def cen_05_fila_e_nao_conferido() -> None:
    fila = _cliente("sa").get(BASE).get_json()
    ids = {i["id"] for i in fila["itens"]}
    _garante(
        estado["t"] not in ids and estado["a_ficha"] not in ids, "item gravado continua na fila"
    )
    _garante(
        estado["a_sem"] in ids and estado["g"] in ids, "avulso sem ficha ou genérico saiu da fila"
    )
    n = estado["nao_conferido"]
    r = _gravar(n)
    _garante(r["itens_gravados"] == 0, f"item não conferido foi gravado: {r}")
    _garante(
        not _elenco(n)
        and _um("SELECT gravado_em FROM catalog_conferencias WHERE catalog_item_id = :i", i=n)[0]
        is None,
        "item não conferido foi tocado",
    )


def cen_06_de_novo() -> None:
    antes = len(_elenco(estado["t"]))
    r = _gravar(estado["t"])
    _garante(r["itens_gravados"] == 0 and r["personagens_criados"] == 0, f"regravou: {r}")
    _garante(len(_elenco(estado["t"])) == antes, "personagem em dobro")
    # Mesmo sem a marca do item, o vínculo do personagem impede o dobro (o item só não é refeito
    # porque já tem elenco e saiu da fila).
    _executa(
        "UPDATE catalog_conferencias SET gravado_em = NULL WHERE catalog_item_id = :i",
        i=estado["t"],
    )
    r = _gravar(estado["t"])
    _garante(
        r["personagens_criados"] == 0 and len(_elenco(estado["t"])) == antes,
        "dobro sem a marca do item",
    )


def cen_07_foto_ausente() -> None:
    t2 = estado["t2"]
    quantos = _um(
        """SELECT count(*) FROM catalog_conferencia_personagens p JOIN catalog_conferencias c ON c.id = p.conferencia_id
           WHERE c.catalog_item_id = :i AND p.decisao = 'criar'""",
        i=t2,
    )[0]
    r = _gravar(t2)
    _garante(
        r["itens_gravados"] == 1 and r["personagens_criados"] == quantos and not r["falhas"],
        f"lote: {r}",
    )
    _garante(all(e[3] is None for e in _elenco(t2)), "personagem com foto sem o arquivo existir")


def cen_08_ajustes() -> None:
    t3 = estado["t3"]
    pers = _no_banco(
        """SELECT p.id, p.nome, g.url FROM catalog_conferencia_personagens p
           JOIN catalog_conferencias c ON c.id = p.conferencia_id JOIN catalog_item_images g ON g.id = p.imagem_id
           WHERE c.catalog_item_id = :i AND NOT p.sem_foto ORDER BY p.position, p.id""",
        i=t3,
    )
    alvo_foto, alvo_sem = pers[0], pers[1]
    _executa(
        "UPDATE catalog_conferencia_personagens SET sem_foto = true, imagem_id = NULL, recorte = NULL "
        "WHERE id = :i",
        i=alvo_foto[0],
    )
    ajustes = [
        {
            "item_id": t3,
            "nome": alvo_foto[1],
            "foto": alvo_foto[2].rsplit("/", 1)[-1],
            "dims": [800, 1200],
            "recorte": [10, 10, 40, 80],
        },
        {"item_id": t3, "nome": alvo_sem[1], "sem_foto": True},
        {"item_id": t3, "nome": f"{PREFIX}Novo", "criar": True},
        {"item_id": t3, "nome": "Personagem Que Não Existe", "sem_foto": True},
        {"item_id": 99999999, "nome": "Fantasma", "sem_foto": True},
        {"item_id": t3, "nome": pers[2][1], "foto": "nao_existe.jpg", "recorte": [0, 0, 10, 10]},
    ]
    with app.app_context():
        r = ops.aplicar_ajustes(ajustes)
        db.session.commit()
        de_novo = ops.aplicar_ajustes(ajustes)
        db.session.commit()
    _garante(r == {"aplicados": 3, "ignorados": 3} and de_novo == r, f"ajustes: {r} / {de_novo}")
    foto = _um(
        "SELECT imagem_id, recorte, sem_foto FROM catalog_conferencia_personagens WHERE id = :i",
        i=alvo_foto[0],
    )
    _garante(
        foto[0] is not None and json.loads(foto[1]) == [10, 10, 40, 80] and foto[2] is False,
        f"foto: {foto}",
    )
    _garante(
        _um("SELECT sem_foto FROM catalog_conferencia_personagens WHERE id = :i", i=alvo_sem[0])[0]
        is True,
        "sem_foto não aplicado",
    )
    novos = _um(
        """SELECT count(*) FROM catalog_conferencia_personagens p JOIN catalog_conferencias c ON c.id = p.conferencia_id
           WHERE c.catalog_item_id = :i AND p.nome = :n AND p.origem = 'manual'""",
        i=t3,
        n=f"{PREFIX}Novo",
    )[0]
    _garante(novos == 1, f"personagem acrescentado {novos}x")
    r = _gravar(t3)
    elenco = {e[1]: e[3] for e in _elenco(t3)}
    _garante(
        elenco.get(alvo_foto[1])
        and elenco.get(alvo_sem[1]) is None
        and elenco.get(f"{PREFIX}Novo", "x") is None,
        f"gravação depois dos ajustes: {elenco}",
    )


def cen_09_rbac() -> None:
    antes = _um(
        "SELECT count(gravado_em), (SELECT count(*) FROM catalog_characters) FROM catalog_conferencias"
    )
    for quem, esperado in (("com", 403), ("fig", 403), (None, 401)):
        c = _cliente(quem)
        _garante(c.get(f"{BASE}/gravacao").status_code == esperado, f"GET gravacao {quem}")
        _garante(c.post(f"{BASE}/gravar").status_code == esperado, f"POST gravar {quem}")
    _garante(
        _um(
            "SELECT count(gravado_em), (SELECT count(*) FROM catalog_characters) FROM catalog_conferencias"
        )
        == antes,
        "papel sem permissão gravou",
    )
    # O Superadmin grava um lote pela API e a resposta diz o que falta.
    r = _cliente("sa").post(f"{BASE}/gravar")
    dados = r.get_json()
    _garante(
        r.status_code == 200 and 1 <= dados["itens_gravados"] <= 10 and not dados["falhas"],
        f"lote: {dados}",
    )
    _garante(
        dados["restantes"] == _um(f"SELECT count(*) {CONFERIDO_NA_FILA}")[0], f"restantes: {dados}"
    )


def cen_10_limpeza() -> None:
    criados = [
        r[0]
        for r in _no_banco(
            "SELECT catalog_character_id FROM catalog_conferencia_personagens WHERE catalog_character_id IS NOT NULL"
        )
    ]
    if criados:
        _executa("DELETE FROM catalog_characters WHERE id = ANY(:ids)", ids=criados)
    _executa(
        "UPDATE catalog_items i SET figurino_sheet_id = NULL FROM catalog_conferencias c "
        "WHERE c.catalog_item_id = i.id AND c.gravado_em IS NOT NULL AND c.tipo = 'avulso'"
    )
    _executa("UPDATE catalog_conferencias SET gravado_em = NULL")
    ids_antes = [r[0] for r in estado["personagens_antes"]]
    _executa(
        "DELETE FROM catalog_conferencia_personagens WHERE NOT (id = ANY(:ids))", ids=ids_antes
    )
    with _externo.begin() as conn:
        for pid, decisao, sem_foto, imagem_id, recorte, largura, altura in estado[
            "personagens_antes"
        ]:
            conn.execute(
                text(
                    "UPDATE catalog_conferencia_personagens SET decisao=:d, sem_foto=:s, imagem_id=:g, recorte=:r, "
                    "foto_largura=:l, foto_altura=:a WHERE id=:i AND (decisao, sem_foto, imagem_id, recorte) "
                    "IS DISTINCT FROM (:d, :s, :g, :r)"
                ),
                {
                    "d": decisao,
                    "s": sem_foto,
                    "g": imagem_id,
                    "r": recorte,
                    "l": largura,
                    "a": altura,
                    "i": pid,
                },
            )
        for cid, tipo in estado["tipos_antes"]:
            conn.execute(
                text("UPDATE catalog_conferencias SET tipo=:t WHERE id=:i AND tipo <> :t"),
                {"t": tipo, "i": cid},
            )
    for arquivo in PASTA.glob("*"):
        if arquivo.name not in estado["arquivos_antes"]:
            arquivo.unlink()
    with app.app_context():
        _apagar_usuarios()
    _garante(
        foto_do_catalogo() == estado["catalogo"], "o catálogo terminou diferente do que começou"
    )
    _garante(
        _um(
            "SELECT count(*) FROM catalog_conferencia_personagens WHERE catalog_character_id IS NOT NULL"
        )[0]
        == 0,
        "vínculo sobrou",
    )
    _garante(
        _um("SELECT count(*) FROM users WHERE email LIKE :p", p=f"{PREFIX}%")[0] == 0,
        "usuário sobrou",
    )


def main() -> int:
    print("Feature 364 — gravar no catálogo o conferido")
    url = os.environ["DATABASE_URL"]
    if "@localhost" not in url and "@127.0.0.1" not in url:
        print("RECUSADO: este verify só roda contra banco local.")
        return 2
    if _um("SELECT count(gravado_em) FROM catalog_conferencias")[0]:
        print("RECUSADO: o espelho já tem gravação. Restaure o dump antes.")
        return 2
    passos = [
        ("1. resumo do que falta gravar", cen_01_resumo),
        ("2. tema conferido vira elenco", cen_02_tema),
        ("3. foto recortada de verdade; sem foto nasce sem foto", cen_03_foto),
        ("4. avulso com ficha, avulso sem ficha e genérico", cen_04_avulso_e_generico),
        ("5. gravado sai da fila; não conferido fica intacto", cen_05_fila_e_nao_conferido),
        ("6. gravar de novo não duplica", cen_06_de_novo),
        ("7. foto ausente no disco não derruba o lote", cen_07_foto_ausente),
        ("8. ajustes das observações", cen_08_ajustes),
        ("9. Comercial, Figurino e sem login (DEVE falhar)", cen_09_rbac),
    ]
    try:
        preparar()
        for nome, fn in passos:
            cenario(nome, fn)
    finally:
        cenario("10. limpeza", cen_10_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  ✗ {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
