"""Verificação da feature 300 — catálogo rápido: a tela abre sem ficar esperando.

Cenários (a tabela da seção "Verificação" da spec):
  1. Listagem do gerenciador (com e sem filtros) e a visão Personagens: consultas ≤ teto e
     resposta idêntica à referência.
  2. Miniatura de uma capa real: responde e pesa menos de 10% do original.
  3. Vitrine: grade geral, grade de categorias e a maior categoria.
  4. Categorias do formulário de edição, sem carregar a lista de produtos.
  5. Papel sem permissão recusado no gerenciador e no endpoint novo — **DEVE falhar**.
  6. Arquivo ausente e largura fora da allowlist: 404 sem gravar lixo no disco.
  7. Limpeza.

O CRITÉRIO É A CONTAGEM DE CONSULTAS, NUNCA O RELÓGIO (research.md R7): tempo varia com a máquina
e transformaria este arquivo numa fonte de falso alarme que a equipe aprende a ignorar.

A referência do "antes" está em `referencia_300.json`, capturada pela T001 ANTES de qualquer
alteração de código. Sem ela, "a resposta não muda" seria promessa sem verificador.

NADA AQUI ESCREVE NO BANCO além do usuário descartável dos cenários de permissão.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"; $env:MANTO_SEM_THREADS = "1"
    .venv/Scripts/python.exe specs/300-catalogo-rapido/verify_300.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
import traceback
from collections.abc import Callable
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):  # console do Windows em cp1252
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import event  # noqa: E402

from app import create_app, db, limiter  # noqa: E402
from app.catalogo.og_ops import (  # noqa: E402
    LARGURAS_PERMITIDAS,
    MEDIA_SUBFOLDER,
    THUMBS_SUBFOLDER,
)
from app.constants import RoleName  # noqa: E402
from app.models import CatalogItemImage, Role, User  # noqa: E402

PREFIX = "v300-"
SENHA = "verify-300-senha"
REFERENCIA = Path(__file__).with_name("referencia_300.json")

#: Teto de consultas por listagem. Um pouco acima do medido (6 no gerenciador, 4 na vitrine) de
#: propósito: teto colado no número de hoje quebraria a cada acréscimo legítimo de campo, e um
#: verify que quebra à toa é um verify que a equipe aprende a ignorar (spec §Premissas).
TETO = 10

app = create_app()
app.config["TESTING"] = True
limiter.enabled = False  # pelo OBJETO: `RATELIMIT_ENABLED` só é lido no `init_app`

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}
contador = {"n": 0}

#: O engine, pego UMA vez dentro de um contexto. `db.engine` exige contexto de aplicação, e os
#: endpoints públicos não fazem login — sem requisição anterior, não há contexto e ele estoura.
#: (Nos autenticados isso passava por acidente: o `test_client` usado como gerenciador de contexto
#: deixa pendurado o contexto da requisição de login. Medição que depende disso é medição por
#: sorte.)
with app.app_context():
    _ENGINE = db.engine


def _contar(conn, cursor, statement, parameters, context, executemany):
    contador["n"] += 1


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


def _impressao(payload) -> str:
    """Mesma receita da T001: JSON canônico (chaves ordenadas) → sha256.

    Ordenar as CHAVES normaliza o que não importa; a ordem das LISTAS é preservada e comparada,
    porque a ordem dos produtos na tela é justamente parte do contrato.
    """
    canonico = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def _usuario(sufixo: str, papel: str) -> str:
    email = f"{PREFIX}{sufixo}@manto.local"
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(name=f"{PREFIX}{sufixo}", email=email, is_active=True, has_access=True)
            db.session.add(user)
        user.set_password(SENHA)
        user.roles.clear()
        user.roles.append(Role.query.filter_by(name=papel).one())
        db.session.commit()
    return email


def _medir(url: str, email: str | None = None):
    """Uma requisição HTTP, contando as consultas SÓ dela.

    O ouvinte entra DEPOIS do login: autenticar custa consultas próprias (procurar o usuário,
    gravar a sessão) que não são da listagem e poluiriam a medida. Sobra o custo do
    `user_loader` da própria requisição, que é constante e cabe folgado no teto.

    As requisições ficam FORA de `app.app_context()` — contexto persistente vaza o usuário entre
    requisições e faz o cenário de permissão passar por engano.
    """
    with app.test_client() as c:
        if email is not None:
            r = c.post("/api/auth/login", json={"email": email, "password": SENHA})
            _garante(r.status_code == 200, f"login {email} → {r.status_code}")
        contador["n"] = 0
        event.listen(_ENGINE, "before_cursor_execute", _contar)
        try:
            resposta = c.get(url)
        finally:
            event.remove(_ENGINE, "before_cursor_execute", _contar)
        return resposta, contador["n"]


def _confere(url: str, chave_ref: str, email: str | None = None) -> None:
    """Consultas dentro do teto E resposta idêntica à capturada antes da mudança."""
    referencia = estado["ref"]["endpoints"][chave_ref]
    resposta, queries = _medir(url, email)
    _garante(resposta.status_code == 200, f"{url} → {resposta.status_code}")
    _garante(
        queries <= TETO,
        f"{url}: {queries} consultas (teto {TETO}; antes eram {referencia['queries']})",
    )
    atual = _impressao(json.loads(resposta.get_data(as_text=True)))
    _garante(
        atual == referencia["sha256"],
        f"{url}: a resposta MUDOU — {atual[:12]}… ≠ {referencia['sha256'][:12]}…",
    )


# ── Cenários ─────────────────────────────────────────────────────────────────────────────────────


def cen_01() -> None:
    """Os três modos do gerenciador: listagem, filtros e a visão Personagens."""
    admin = estado["admin"]
    _confere("/api/admin/catalogo", "GET /api/admin/catalogo", admin)
    _confere("/api/admin/catalogo/personagens", "GET /api/admin/catalogo/personagens", admin)

    # Com filtro não há referência (o recorte é outro), mas o teto vale igual: é a propriedade
    # que importa — o custo não pode crescer com a quantidade de produtos.
    for filtro in ("?q=a", "?status=ativo", "?status=inativo"):
        resposta, queries = _medir(f"/api/admin/catalogo{filtro}", admin)
        _garante(resposta.status_code == 200, f"{filtro} → {resposta.status_code}")
        _garante(queries <= TETO, f"filtro {filtro}: {queries} consultas (teto {TETO})")


def cen_02() -> None:
    """A miniatura que a tela passa a pedir existe, responde e é muito mais leve."""
    caminho, arquivo = estado["capa"]
    with app.test_client() as c:
        original = c.get(caminho)
        variante = c.get(f"/catalogo/midia/t/128/{arquivo}")
    _garante(original.status_code == 200, f"original {caminho} → {original.status_code}")
    _garante(variante.status_code == 200, f"miniatura de {arquivo} → {variante.status_code}")
    bytes_original = len(original.get_data())
    bytes_variante = len(variante.get_data())
    _garante(
        bytes_variante < bytes_original * 0.10,
        f"miniatura com {bytes_variante} B contra {bytes_original} B do original (esperado <10%)",
    )


def cen_03() -> None:
    """A vitrine pública, nos três caminhos de listagem."""
    slug = estado["ref"]["maior_categoria_slug"]
    _confere("/api/catalogo", "GET /api/catalogo")
    _confere("/api/catalogo/categorias", "GET /api/catalogo/categorias")
    _confere(f"/api/catalogo/categoria/{slug}", f"GET /api/catalogo/categoria/{slug}")


def cen_04() -> None:
    """As categorias do formulário chegam sozinhas, sem a lista de produtos junto."""
    resposta, queries = _medir("/api/admin/catalogo/categorias", estado["admin"])
    _garante(resposta.status_code == 200, f"categorias do admin → {resposta.status_code}")
    corpo = json.loads(resposta.get_data(as_text=True))
    _garante("categories" in corpo, "a resposta não traz a chave `categories`")
    _garante("items" not in corpo, "a resposta traz `items` — o catálogo veio junto de novo")
    _garante(
        len(corpo["categories"]) == estado["ref"]["volume"]["catalog_categories"],
        f"{len(corpo['categories'])} categorias; esperadas "
        f"{estado['ref']['volume']['catalog_categories']} (TODAS, inclusive sem produto ativo)",
    )
    _garante(
        {"id", "name"} == set(corpo["categories"][0]),
        f"forma inesperada: {sorted(corpo['categories'][0])}",
    )
    _garante(queries <= TETO, f"categorias do admin: {queries} consultas (teto {TETO})")


def cen_05() -> None:
    """DEVE FALHAR: quem não é SUPERADMIN não entra no gerenciador nem no endpoint novo."""
    intruso = estado["intruso"]
    for url in ("/api/admin/catalogo", "/api/admin/catalogo/personagens",
                "/api/admin/catalogo/categorias"):
        resposta, _ = _medir(url, intruso)
        # 405 não é gate frouxo: o roteamento recusa o método ANTES de a view (e o gate) rodar.
        # Distinguir importa — senão esta linha manda investigar RBAC quando o que falta é a rota.
        _garante(
            resposta.status_code != 405,
            f"{url} ainda não aceita GET (405) — T017 pendente; o gate nem chegou a ser exercitado",
        )
        _garante(
            resposta.status_code in (403, 404),
            f"COMERCIAL recebeu {resposta.status_code} em {url} — o gate afrouxou",
        )


def cen_06() -> None:
    """Ausente, CORROMPIDO e largura fora da allowlist: sem 200, e nada é gravado no cache.

    O corrompido é um caso distinto do ausente: ali o arquivo existe e o decodificador é que
    recusa. Sem este cenário, "a geração que falha cai no espaço reservado" seria só uma frase
    na spec.
    """
    with app.app_context():
        cache = Path(app.config["UPLOAD_FOLDER"]) / THUMBS_SUBFOLDER
        origem = Path(app.config["UPLOAD_FOLDER"]) / MEDIA_SUBFOLDER
    antes = sum(1 for _ in cache.rglob("*")) if cache.exists() else 0

    # Um arquivo que EXISTE e não é imagem — apagado no `finally`, aconteça o que acontecer.
    corrompido = origem / f"{PREFIX}corrompido.jpg"
    corrompido.write_bytes(b"isto nao e uma imagem, e o decodificador precisa recusar")
    try:
        with app.test_client() as c:
            ausente = c.get("/catalogo/midia/t/128/v300-nao-existe-de-verdade.jpg")
            _, arquivo = estado["capa"]
            fora = c.get(f"/catalogo/midia/t/999/{arquivo}")
            quebrado = c.get(f"/catalogo/midia/t/128/{corrompido.name}")
    finally:
        corrompido.unlink(missing_ok=True)

    _garante(ausente.status_code == 404, f"arquivo ausente → {ausente.status_code} (esperado 404)")
    _garante(
        fora.status_code == 404,
        f"largura 999 → {fora.status_code}; a allowlist {LARGURAS_PERMITIDAS} é fechada",
    )
    _garante(
        quebrado.status_code != 200,
        f"arquivo corrompido devolveu {quebrado.status_code} — a tela desenharia lixo",
    )

    depois = sum(1 for _ in cache.rglob("*")) if cache.exists() else 0
    _garante(depois == antes, f"o cache cresceu de {antes} para {depois} arquivos com pedido inválido")


def cen_07() -> None:
    """Dois pedidos simultâneos da mesma miniatura: os dois recebem a imagem, e ela é a mesma.

    A feature 270 corrigiu aqui uma corrida real: o temporário da escrita atômica era único por
    PID, e as threads de um worker escreviam por cima umas das outras — uma resposta saiu com
    bytes pela metade. Esta feature não pode reintroduzir isso, e promessa sem verificador não
    vale nada.

    **A variante é aquecida antes**, de propósito: a geração simultânea A FRIO é coberta pelo
    cenário 6 do `verify_270`, e no Windows ela esbarra num limite da plataforma — `os.replace`
    sobre um arquivo que outra thread está abrindo levanta `PermissionError`, o que faria este
    verify falhar por causa do sistema de arquivos do desenvolvedor, não do produto (dívida 59).
    O que se guarda aqui é o que importa para a 300: servir a MESMA miniatura a vários pedidos
    ao mesmo tempo, sem bytes pela metade.
    """
    _, arquivo = estado["capa"]
    url = f"/catalogo/midia/t/480/{arquivo}"
    with app.test_client() as c:
        aquecer = c.get(url)
    _garante(aquecer.status_code == 200, f"aquecimento de {url} → {aquecer.status_code}")

    respostas: list[tuple[int, int, str]] = []
    trava = threading.Lock()

    def pedir() -> None:
        # Um cliente POR THREAD: o `test_client` não é seguro para uso simultâneo.
        with app.test_client() as c:
            r = c.get(url)
            corpo = r.get_data()
        with trava:
            respostas.append((r.status_code, len(corpo), hashlib.sha256(corpo).hexdigest()))

    threads = [threading.Thread(target=pedir) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    _garante(len(respostas) == 6, f"{len(respostas)} de 6 pedidos responderam")
    _garante(
        all(status == 200 for status, _, _ in respostas),
        f"status diferentes de 200: {[s for s, _, _ in respostas]}",
    )
    tamanhos = {tamanho for _, tamanho, _ in respostas}
    digests = {digest for _, _, digest in respostas}
    _garante(len(digests) == 1, f"os pedidos simultâneos devolveram bytes DIFERENTES: {tamanhos}")
    _garante(tamanhos.pop() > 500, "miniatura suspeita de vir pela metade (menos de 500 bytes)")


def limpar() -> None:
    """Apaga os usuários descartáveis (`roles.clear()` antes, senão a FK segura)."""
    apagados = 0
    for user in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        user.roles.clear()
        db.session.delete(user)
        apagados += 1
    db.session.commit()
    sobraram = User.query.filter(User.email.like(f"{PREFIX}%")).count()
    _garante(sobraram == 0, f"{sobraram} usuários de teste sobraram")
    print(f"         {apagados} usuário(s) descartável(is) apagado(s)")


# ── Execução ─────────────────────────────────────────────────────────────────────────────────────


def main() -> int:
    _garante(
        REFERENCIA.exists(),
        f"{REFERENCIA.name} não existe — rode a T001 ANTES de qualquer alteração de código",
    )
    estado["ref"] = json.loads(REFERENCIA.read_text(encoding="utf-8"))

    with app.app_context():
        # Uma capa de verdade, cujo arquivo exista em disco: sem isso o cenário 2 mediria o 404.
        raiz = Path(app.config["UPLOAD_FOLDER"]) / MEDIA_SUBFOLDER
        estado["capa"] = None
        for imagem in CatalogItemImage.query.filter(
            CatalogItemImage.url.like("/catalogo/midia/%")
        ).limit(200):
            nome = imagem.url.rsplit("/", 1)[-1]
            if (raiz / nome).is_file():
                estado["capa"] = (imagem.url, nome)
                break
        _garante(
            estado["capa"] is not None,
            f"nenhuma foto do catálogo encontrada em {raiz} — o espelho está sem as mídias",
        )

    estado["admin"] = _usuario("admin", RoleName.SUPERADMIN)
    estado["intruso"] = _usuario("intruso", RoleName.COMERCIAL)

    print(f"Referência de {estado['ref']['capturado_em']} · {estado['ref']['volume']} · teto {TETO}\n")
    try:
        cenario("1. gerenciador: listagem, filtros e Personagens", cen_01)
        cenario("2. miniatura de uma capa real", cen_02)
        cenario("3. vitrine: grade, categorias e a maior categoria", cen_03)
        cenario("4. categorias do formulário, sem o catálogo junto", cen_04)
        cenario("5. papel sem permissão recusado (DEVE falhar)", cen_05)
        cenario("6. ausente, corrompido e largura inválida sem sujar o cache", cen_06)
        cenario("7. dois pedidos simultâneos da mesma miniatura", cen_07)
    finally:
        with app.app_context():
            cenario("8. limpeza", limpar)

    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  - {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
