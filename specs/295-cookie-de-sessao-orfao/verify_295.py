"""Verificação da feature 295 — o cookie de sessão órfão que trancava o usuário para fora.

O defeito, reproduzido aqui: a feature 144 gravou cookies `session` no domínio
`.mantoproducoes.com.br` para o `beta.*` compartilhar sessão com o `app.*`. O beta morreu e a
variável foi desligada, mas o cookie ficou nos navegadores. A partir daí o navegador manda DOIS
`session` na mesma requisição e o Werkzeug lê só o primeiro — com o mesmo `Path`, o mais antigo
(RFC 6265 §5.4), que é o órfão. A pessoa loga (o servidor grava o cookie host-only), a requisição
seguinte é lida pelo órfão e responde 401. Nenhum login futuro conserta, porque o servidor não
escreve mais naquele domínio: só apagar cookie pelo inspetor do navegador resolvia.

Cenários:
 1. Sessão sadia sozinha: 200, e a resposta NÃO carimba exclusão nenhuma (cliente limpo não paga
    pelo problema de quem tem o órfão).
 2. O defeito: órfão na frente do cookie bom devolve 401 — a prova de que quem é lido é o órfão.
 3. A cura: essa mesma resposta 401 carimba a exclusão do `session` no domínio órfão, com o mesmo
    nome/domínio/path do original. O navegador se cura antes de a pessoa conseguir logar.
 4. Sessão que funciona nunca é tocada: cookie bom na frente autentica (200) e NADA é recolhido.
 5. O domínio ativo jamais é recolhido — senão o recolhimento apagaria o cookie legítimo de uma
    instalação que use `SESSION_COOKIE_DOMAIN`.
 6. Lista vazia desliga o recolhimento por completo.
 7. O padrão de produção já traz `.mantoproducoes.com.br` — sem env nova no painel do Render, que
    é justamente onde variáveis `sync: false` ficam sem preencher.
 8. O caminho inteiro de quem está preso: órfão sozinho (401, sem recolher — com um cookie só não
    dá para saber que ele é órfão), login, e a cura na requisição seguinte.
 9. A resposta do PRÓPRIO login já recolhe, e sem atropelar a gravação do cookie novo: quem está
    preso loga UMA vez, não duas.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    $env:MAIL_SUPPRESS_SEND = "true"; $env:MANTO_SEM_THREADS = "1"
    .\\.venv\\Scripts\\python.exe specs\\295-cookie-de-sessao-orfao\\verify_295.py
"""
from __future__ import annotations

import os
import sys
import traceback
from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MAIL_SUPPRESS_SEND", "true")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from app import create_app, db  # noqa: E402
from app.models import User  # noqa: E402

PREFIX = "__v295_"
SENHA = "verify-295-senha"
DOMINIO_ORFAO = ".mantoproducoes.com.br"

# Um cookie de sessão do Flask que não passa na assinatura. O formato imita o real (`.eJw...`,
# zlib+base64) porque o caminho de código que interessa é o do Werkzeug decidindo QUAL dos dois
# cookies entrega — e isso acontece antes de qualquer validação.
ORFAO = ".eJwlzskNwjAQAMBe_Oaxh9dHmom8I-CbkBeid0AUMNK8.aLpQAA.orfao-do-beta-nao-valida"

app = create_app()
app.config["TESTING"] = True

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}


def cenario(nome: str, fn: Callable[[], None]) -> None:
    # Sem rollback: os cenários só fazem requisição HTTP, nenhum escreve no banco.
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _exclusoes_do_orfao(resp) -> list[str]:
    """Set-Cookie que apagam `session` no domínio órfão (Max-Age=0 / Expires no passado)."""
    achados = []
    for bruto in resp.headers.getlist("Set-Cookie"):
        if not bruto.startswith("session="):
            continue
        baixo = bruto.lower()
        if DOMINIO_ORFAO.lstrip(".") not in baixo:
            continue
        if "max-age=0" in baixo or "expires=thu, 01 jan 1970" in baixo:
            achados.append(bruto)
    return achados


def _cookie_de_sessao(resp) -> str:
    """Valor do `session` recém-gravado pelo servidor."""
    for bruto in resp.headers.getlist("Set-Cookie"):
        if bruto.startswith("session="):
            valor = bruto.split(";", 1)[0][len("session=") :]
            if valor:
                return valor
    raise AssertionError("o login não gravou cookie de sessão")


def _cliente_limpo():
    """Cliente SEM cookie jar — a única forma de mandar dois `session` na mesma requisição.

    O jar do `test_client` reescreve `HTTP_COOKIE` a partir dele mesmo: com o jar vazio ele
    APAGA o cabeçalho que a gente montou (medido: `lista: []`), e com o jar cheio ele deduplica
    por nome. Nos dois casos o cenário desta feature — dois cookies de mesmo nome chegando juntos,
    como o navegador manda — deixa de existir e o teste passa sem testar nada. Com
    `use_cookies=False` o cabeçalho chega intacto: `['ORFAO', 'BOM']`, e o Werkzeug entrega o
    primeiro.
    """
    return app.test_client(use_cookies=False)


def _login() -> str:
    """Loga pela API e devolve o cookie de sessão que o servidor gravou."""
    resp = _cliente_limpo().post(
        "/api/auth/login", json={"email": estado["email"], "password": SENHA}
    )
    _garante(resp.status_code == 200, f"login de apoio falhou: {resp.status_code}")
    return _cookie_de_sessao(resp)


def preparar() -> None:
    limpar()
    with app.app_context():
        usuario = User(name=f"{PREFIX}dono", email=f"{PREFIX}dono@manto.local", has_access=True)
        usuario.set_password(SENHA)
        db.session.add(usuario)
        db.session.commit()
        estado["email"] = usuario.email
    estado["cookie_bom"] = _login()


def limpar() -> None:
    with app.app_context():
        # Usuário de teste nasce sem papel nenhum, então não há vínculo de role para desfazer.
        User.query.filter(User.name.like(f"{PREFIX}%")).delete(synchronize_session=False)
        db.session.commit()


def c01_sessao_sadia_sozinha():
    resp = _cliente_limpo().get(
        "/api/auth/me", headers={"Cookie": f"session={estado['cookie_bom']}"}
    )
    _garante(resp.status_code == 200, f"a sessão boa sozinha deveria autenticar: {resp.status_code}")
    _garante(
        not _exclusoes_do_orfao(resp),
        "cliente com um cookie só recebeu carimbo de exclusão — o recolhimento está amplo demais",
    )


def c02_orfao_na_frente_derruba_a_sessao():
    resp = _cliente_limpo().get(
        "/api/auth/me",
        headers={"Cookie": f"session={ORFAO}; session={estado['cookie_bom']}"},
    )
    _garante(
        resp.status_code == 401,
        "o órfão na frente deveria vencer e derrubar a sessão — se isto passou a dar 200, o "
        f"Werkzeug mudou qual cookie entrega e a premissa da 295 mudou junto (status {resp.status_code})",
    )


def c03_a_resposta_recolhe_o_orfao():
    resp = _cliente_limpo().get(
        "/api/auth/me",
        headers={"Cookie": f"session={ORFAO}; session={estado['cookie_bom']}"},
    )
    exclusoes = _exclusoes_do_orfao(resp)
    _garante(
        len(exclusoes) == 1,
        f"a resposta 401 deveria recolher o órfão exatamente uma vez, veio {len(exclusoes)}: "
        f"{resp.headers.getlist('Set-Cookie')}",
    )
    carimbo = exclusoes[0].lower()
    _garante("path=/" in carimbo, f"exclusão sem o Path do original, não apaga nada: {carimbo}")
    _garante("httponly" in carimbo, f"exclusão sem HttpOnly não casa com o original: {carimbo}")


def c04_sessao_que_funciona_nao_e_tocada():
    """Cookie bom na frente: a pessoa está autenticada e nada pode ser mexido."""
    resp = _cliente_limpo().get(
        "/api/auth/me",
        headers={"Cookie": f"session={estado['cookie_bom']}; session={ORFAO}"},
    )
    _garante(resp.status_code == 200, f"o cookie bom na frente deveria autenticar: {resp.status_code}")
    _garante(
        not _exclusoes_do_orfao(resp),
        "uma sessão que está funcionando foi recolhida — isso deslogaria quem estava bem",
    )


def c05_dominio_ativo_nunca_e_recolhido():
    anterior = app.config.get("SESSION_COOKIE_DOMAIN")
    app.config["SESSION_COOKIE_DOMAIN"] = DOMINIO_ORFAO
    try:
        resp = _cliente_limpo().get(
            "/api/auth/me",
            headers={"Cookie": f"session={ORFAO}; session={estado['cookie_bom']}"},
        )
        _garante(
            not _exclusoes_do_orfao(resp),
            "o domínio ATIVO foi recolhido — numa instalação com SESSION_COOKIE_DOMAIN isso "
            "apagaria o cookie legítimo de todo mundo a cada requisição anônima",
        )
    finally:
        app.config["SESSION_COOKIE_DOMAIN"] = anterior


def c06_lista_vazia_desliga():
    anterior = app.config.get("SESSION_COOKIE_DOMINIOS_OBSOLETOS")
    app.config["SESSION_COOKIE_DOMINIOS_OBSOLETOS"] = []
    try:
        resp = _cliente_limpo().get(
            "/api/auth/me",
            headers={"Cookie": f"session={ORFAO}; session={estado['cookie_bom']}"},
        )
        _garante(not _exclusoes_do_orfao(resp), "lista vazia deveria desligar o recolhimento")
    finally:
        app.config["SESSION_COOKIE_DOMINIOS_OBSOLETOS"] = anterior


def c07_padrao_ja_traz_o_dominio_do_beta():
    from app.config import Config

    _garante(
        DOMINIO_ORFAO in Config.SESSION_COOKIE_DOMINIOS_OBSOLETOS,
        "o domínio do beta precisa vir no PADRÃO: depender de env nova no painel do Render é "
        "exatamente como AUDIT_AGENT_TOKEN e MARKETING_AGENT_TOKEN ficaram sem preencher",
    )


def c08_o_navegador_preso_se_cura_sozinho():
    """O caminho real de quem está trancado: órfão sozinho, login, e a cura na requisição seguinte."""
    cli = _cliente_limpo()
    so_orfao = cli.get("/api/auth/me", headers={"Cookie": f"session={ORFAO}"})
    _garante(so_orfao.status_code == 401, "órfão sozinho deveria dar 401")
    _garante(
        not _exclusoes_do_orfao(so_orfao),
        "fora do login, com um cookie só não dá para saber que ele é órfão — recolher aqui "
        "apagaria a sessão legítima de qualquer pessoa com cookie vencido",
    )
    # A pessoa loga: agora o navegador tem o órfão E o novo. É esse par que denuncia o problema.
    novo = _login()
    curada = cli.get(
        "/api/auth/me", headers={"Cookie": f"session={ORFAO}; session={novo}"}
    )
    _garante(curada.status_code == 401, "a requisição logo após o login ainda é lida pelo órfão")
    _garante(
        len(_exclusoes_do_orfao(curada)) == 1,
        "o órfão precisa ser recolhido AQUI — é a única janela antes de a pessoa desistir",
    )
    # Recolhido o órfão, o navegador passa a mandar só o cookie bom.
    depois = cli.get("/api/auth/me", headers={"Cookie": f"session={novo}"})
    _garante(depois.status_code == 200, "depois do recolhimento a sessão tinha que valer")


def c09_o_login_ja_recolhe_sem_cobrar_login_extra():
    """A resposta do PRÓPRIO login recolhe o órfão — a pessoa presa loga uma vez, não duas.

    Sem isto o recolhimento só aconteceria na requisição seguinte, que ainda é lida pelo órfão:
    401, `aoPerderSessao` dispara e o navegador volta para a tela de login. Cura, cobrando um
    segundo login de quem já não estava entendendo nada.
    """
    resp = _cliente_limpo().post(
        "/api/auth/login",
        json={"email": estado["email"], "password": SENHA},
        headers={"Cookie": f"session={ORFAO}"},  # o pote de quem está preso: só o órfão
    )
    _garante(resp.status_code == 200, f"o login em si nunca falhou: {resp.status_code}")
    _garante(
        len(_exclusoes_do_orfao(resp)) == 1,
        "a resposta do login precisa recolher o órfão, senão a primeira consulta depois dele "
        f"ainda é lida pelo cookie velho: {resp.headers.getlist('Set-Cookie')}",
    )
    _garante(
        _cookie_de_sessao(resp),
        "recolher o órfão não pode ter atropelado a gravação do cookie novo",
    )


def main() -> int:
    print("\nVerificação da feature 295 — cookie de sessão órfão\n")
    # Nenhum `app_context` externo aqui de propósito: o Flask-Login guarda o usuário no `g`, que
    # vive no app context. Segurando um contexto por fora, o login da preparação vaza para TODAS as
    # requisições seguintes e o teste passa com qualquer cookie — foi o que aconteceu na primeira
    # versão deste arquivo, que dava 200 até para o cookie órfão sozinho.
    try:
        preparar()
        cenario("01 sessão sadia sozinha não é carimbada", c01_sessao_sadia_sozinha)
        cenario("02 órfão na frente derruba a sessão (o defeito)", c02_orfao_na_frente_derruba_a_sessao)
        cenario("03 a própria resposta 401 recolhe o órfão", c03_a_resposta_recolhe_o_orfao)
        cenario("04 sessão que funciona não é tocada", c04_sessao_que_funciona_nao_e_tocada)
        cenario("05 domínio ativo nunca é recolhido", c05_dominio_ativo_nunca_e_recolhido)
        cenario("06 lista vazia desliga o recolhimento", c06_lista_vazia_desliga)
        cenario("07 padrão já traz o domínio do beta", c07_padrao_ja_traz_o_dominio_do_beta)
        cenario("08 o navegador preso se cura sozinho", c08_o_navegador_preso_se_cura_sozinho)
        cenario("09 o login já recolhe, sem cobrar login extra", c09_o_login_ja_recolhe_sem_cobrar_login_extra)
    finally:
        try:
            limpar()
        except Exception:  # noqa: BLE001 — limpeza não pode esconder a falha real
            traceback.print_exc()

    print("")
    falhas = [n for n, ok, _ in resultados if not ok]
    for nome, ok, detalhe in resultados:
        if not ok:
            print(f"  {nome}: {detalhe}")
    print(f"\n{len(resultados) - len(falhas)}/{len(resultados)} cenários OK\n")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
