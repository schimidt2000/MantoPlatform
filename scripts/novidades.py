"""Novidades para a equipe (feature 321).

Lista o que entrou na `main` desde o último aviso à equipe e monta o rascunho do
comunicado por grupo de WhatsApp. Quem escreve o texto final é a skill
`manto-novidades`; este script só junta o material, de forma determinística.

Uso (na raiz do repositório):

    python scripts/novidades.py                 # lista as mudanças sem aviso
    python scripts/novidades.py --rascunho      # grava docs/novidades/<hoje>.md
    python scripts/novidades.py --contar        # só o número (o hook pre-push usa)
    python scripts/novidades.py --marcar        # grava a main atual como "avisada"
    python scripts/novidades.py --desde <ref> --ate <ref> [--json]

O marco "até onde a equipe já foi avisada" fica em `docs/novidades/ULTIMO_AVISO`
(última linha não comentada: `<hash> <data> <arquivo do comunicado>`). O script
anda pela primeira linha de pais da `main` (`--first-parent`): cada merge
`merge: NNN — título` é uma mudança; commit solto que não seja `docs…` também
conta. Para cada mudança ele acha `specs/NNN-*/spec.md`, lê o cabeçalho de
situação e a seção "O pedido", e dá pistas de grupo pelos arquivos tocados.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "docs" / "novidades"
MARCO = PASTA / "ULTIMO_AVISO"
SPECS = RAIZ / "specs"

RE_MERGE = re.compile(r"^merge:\s*(?P<num>\d+[a-z]?)\s*[—–-]\s*(?P<titulo>.+)$")
RE_NUM_NO_ASSUNTO = re.compile(r"^(?:\w+)\((?P<num>\d+[a-z]?)\)")

# Pistas de grupo pelos caminhos tocados. Não decidem nada: a skill lê a spec.
PISTAS = [
    (r"frontend/apps/portal|app/api/portal|portal_", "casting (portal do elenco)"),
    (r"frontend/apps/public|lojaTema|virtuais|loja", "redes sociais"),
    (r"orcamento|quote|calculadora|catalogo|catalog|clientes|formulario|cobranca|vendas", "vendas"),
    (r"gastos|expense|financeiro|comiss|pagamento|dre_|/pix|contas_rec|devolu", "financeiro (sem grupo: só o dono)"),
    (r"casting|talent|escala|cache_|elenco", "casting"),
    (r"ensaio|educamanto", "ensaios"),
    (r"figurino", "figurinos"),
    (r"cancel", "vendas · casting"),
    (r"email_service|notific", "(aviso por e-mail ou sino)"),
]

# Nomes reais dos grupos no WhatsApp (dono, 28/10). Financeiro não tem grupo nem há grupo geral:
# a tabela grupo × papel está na skill manto-novidades.
GRUPOS_PADRAO = [
    "vendas",
    "casting",
    "ensaios",
    "figurinos",
    "redes sociais",
]


def git(*args: str) -> str:
    saida = subprocess.run(
        ["git", *args], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if saida.returncode != 0:
        raise SystemExit(f"git {' '.join(args)}: {saida.stderr.strip()}")
    return saida.stdout


def ler_marco() -> tuple[str, str] | None:
    """Devolve (hash, resto da linha) da última linha não comentada do ULTIMO_AVISO."""
    if not MARCO.exists():
        return None
    linhas = [linha.strip() for linha in MARCO.read_text(encoding="utf-8").splitlines()]
    uteis = [linha for linha in linhas if linha and not linha.startswith("#")]
    if not uteis:
        return None
    partes = uteis[-1].split(maxsplit=1)
    return partes[0], (partes[1] if len(partes) > 1 else "")


def pasta_da_spec(num: str) -> Path | None:
    candidatas = sorted(SPECS.glob(f"{num}-*"))
    candidatas = [c for c in candidatas if c.is_dir() and re.match(rf"^{re.escape(num)}-", c.name)]
    return candidatas[0] if candidatas else None


def ler_spec(pasta: Path | None) -> dict:
    info = {"spec": None, "titulo_spec": None, "status": None, "pedido": [], "alerta": None}
    if pasta is None:
        return info
    arquivo = pasta / "spec.md"
    if not arquivo.exists():
        return info
    info["spec"] = arquivo.relative_to(RAIZ).as_posix()
    texto = arquivo.read_text(encoding="utf-8", errors="replace")
    linhas = texto.splitlines()
    for linha in linhas:
        if linha.startswith("# "):
            info["titulo_spec"] = linha[2:].strip()
            break
    m = re.search(r"\*\*Status\*\*:\s*(.+?)(?:\s*·\s*\*\*|\n|$)", texto)
    if m:
        info["status"] = m.group(1).strip()
    # Seção "O pedido" (qualquer título que comece por "## O pedido").
    dentro = False
    for linha in linhas:
        if linha.startswith("## "):
            if dentro:
                break
            dentro = linha.lower().startswith("## o pedido")
            continue
        if dentro and linha.strip():
            info["pedido"].append(linha.rstrip())
            if len(info["pedido"]) >= 14:
                break
    return info


RE_ENTRADA_03 = re.compile(r"^### (?P<num>\d+[a-z]?)(?: e \d+[a-z]?)? — ", re.MULTILINE)
RE_PRODUCAO = re.compile(r"EM PRODUÇÃO desde\s*\*{0,2}\s*([0-9/]+(?:\s*~?\s*[0-9h:]+)?)", re.IGNORECASE)
RE_DESLIGADA = re.compile(r"desligad|interruptor|até o dono ligar|só liga quando|antes de ligar", re.IGNORECASE)
_DOCS03: dict[str, str] | None = None


def entradas_do_docs03() -> dict[str, str]:
    """Texto de cada entrada do Registro do docs/03, pelo número da feature."""
    global _DOCS03
    if _DOCS03 is None:
        _DOCS03 = {}
        arquivo = RAIZ / "docs" / "03_HISTORICO_MUTACOES.md"
        texto = arquivo.read_text(encoding="utf-8", errors="replace") if arquivo.exists() else ""
        inicio = texto.find("\n## Registro")
        texto = texto[inicio:] if inicio >= 0 else texto
        cabecalhos = list(RE_ENTRADA_03.finditer(texto))
        for i, m in enumerate(cabecalhos):
            fim = cabecalhos[i + 1].start() if i + 1 < len(cabecalhos) else len(texto)
            _DOCS03.setdefault(m.group("num"), texto[m.start():fim])
    return _DOCS03


def ler_docs03(num: str | None) -> dict:
    """Quando entrou em produção e se há sinal de "nasce desligada", pela entrada do docs/03."""
    info = {"producao": None, "alerta": None, "docs03": False}
    if not num:
        return info
    entrada = entradas_do_docs03().get(num)
    if not entrada:
        return info
    info["docs03"] = True
    m = RE_PRODUCAO.search(entrada)
    if m:
        info["producao"] = m.group(1).strip()
    if RE_DESLIGADA.search(entrada):
        info["alerta"] = "a entrada do docs/03 fala em interruptor/desligada: confira se já está ligada antes de anunciar"
    return info


def arquivos_do_commit(sha: str, merge: bool) -> list[str]:
    if merge:
        saida = git("diff", "--name-only", f"{sha}^1", sha)
    else:
        saida = git("show", "--name-only", "--format=", sha)
    return [linha.strip() for linha in saida.splitlines() if linha.strip()]


def pistas(arquivos: list[str]) -> list[str]:
    achadas: list[str] = []
    for padrao, grupo in PISTAS:
        if any(re.search(padrao, a, re.IGNORECASE) for a in arquivos) and grupo not in achadas:
            achadas.append(grupo)
    return achadas


def mudancas(desde: str, ate: str) -> list[dict]:
    """Mudanças na primeira linha de pais entre `desde` (exclusivo) e `ate` (inclusivo)."""
    formato = "%H%x1f%h%x1f%ad%x1f%P%x1f%s"
    saida = git("log", "--first-parent", "--date=short", f"--format={formato}", f"{desde}..{ate}")
    lista: list[dict] = []
    for linha in saida.splitlines():
        sha, curto, data, pais, assunto = linha.split("\x1f")
        merge = len(pais.split()) > 1
        if assunto.startswith(("docs", "chore")):
            continue
        m = RE_MERGE.match(assunto)
        if m:
            num, titulo = m.group("num"), m.group("titulo").strip()
        else:
            m2 = RE_NUM_NO_ASSUNTO.match(assunto)
            num = m2.group("num") if m2 else None
            titulo = assunto
        arquivos = arquivos_do_commit(sha, merge)
        item = {
            "num": num,
            "titulo": titulo,
            "sha": curto,
            "data": data,
            "merge": merge,
            "arquivos": len(arquivos),
            "pistas": pistas(arquivos),
        }
        item.update(ler_spec(pasta_da_spec(num) if num else None))
        item.update(ler_docs03(num))
        lista.append(item)
    return lista


def imprimir(lista: list[dict], desde: str, ate: str) -> None:
    print(f"{len(lista)} mudança(s) na main sem aviso à equipe ({desde}..{ate}):")
    for it in lista:
        num = it["num"] or "—"
        producao = f"  (em produção desde {it['producao']})" if it["producao"] else "  (sem data de produção no docs/03)"
        print(f"- {num:>5}  {it['data']}  {it['sha']}  {it['titulo']}{producao}")
        if it["alerta"]:
            print(f"         ⚠ {it['alerta']}")
        if it["pistas"]:
            print(f"         grupos prováveis: {', '.join(it['pistas'])}")


def rascunho(lista: list[dict], desde: str, ate: str, hoje: dt.date) -> Path:
    PASTA.mkdir(parents=True, exist_ok=True)
    destino = PASTA / f"{hoje.isoformat()}.md"
    if destino.exists():
        raise SystemExit(f"{destino.relative_to(RAIZ)} já existe; apague ou use outra data.")
    linhas = [
        f"# Novidades para a equipe — {hoje.strftime('%d/%m/%Y')}",
        "",
        f"> Rascunho gerado por `scripts/novidades.py` ({desde}..{ate}). A skill `manto-novidades`",
        "> escreve o texto de cada grupo a partir do material abaixo (constituição, Princípio XV,",
        '> "mensagem de WhatsApp que a equipe copia"). Depois de enviar: `python scripts/novidades.py --marcar`.',
        "",
        "## Situação",
        "",
        "- [ ] textos escritos  · [ ] dono aprovou  · [ ] enviados  · [ ] `--marcar` rodado",
        "",
        "## Mensagens por grupo",
        "",
    ]
    for g in GRUPOS_PADRAO:
        linhas += [f"### {g}", "", "_(escrever)_", ""]
    linhas += ["## Material (uma mudança por bloco)", ""]
    for it in lista:
        num = it["num"] or "sem número"
        linhas.append(f"### {num} — {it['titulo']}")
        linhas.append("")
        linhas.append(f"- merge `{it['sha']}` em {it['data']}; spec: `{it['spec'] or 'não encontrada'}`")
        if it["producao"]:
            linhas.append(f"- em produção desde {it['producao']} (docs/03)")
        elif not it["docs03"]:
            linhas.append("- sem entrada no docs/03 (conferir se está em produção)")
        if it["alerta"]:
            linhas.append(f"- ⚠ {it['alerta']}")
        if it["pistas"]:
            linhas.append(f"- grupos prováveis (pelos arquivos): {', '.join(it['pistas'])}")
        if it["pedido"]:
            linhas.append("- O pedido, na spec:")
            linhas += [f"  > {linha}" for linha in it["pedido"]]
        linhas.append("")
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8", newline="\n")
    return destino


def marcar(ate: str, hoje: dt.date, arquivo: str | None) -> None:
    PASTA.mkdir(parents=True, exist_ok=True)
    sha = git("rev-parse", "--short", ate).strip()
    cabecalho = (
        "# Até onde a equipe já foi avisada (feature 321). Uma linha por rodada: <hash da main> <data> <comunicado>.\n"
        "# Só a última linha vale. Gravado por `python scripts/novidades.py --marcar`; não edite à mão.\n"
    )
    atual = MARCO.read_text(encoding="utf-8") if MARCO.exists() else cabecalho
    if not atual.endswith("\n"):
        atual += "\n"
    atual += f"{sha} {hoje.isoformat()} {arquivo or ''}".rstrip() + "\n"
    MARCO.write_text(atual, encoding="utf-8", newline="\n")
    print(f"Marco gravado: {sha} ({hoje.isoformat()}). Faça o commit de docs/novidades/.")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Novidades para a equipe: o que entrou na main desde o último aviso.")
    p.add_argument("--desde", help="commit exclusivo (padrão: docs/novidades/ULTIMO_AVISO)")
    p.add_argument("--ate", default="main", help="commit inclusivo (padrão: main)")
    p.add_argument("--rascunho", action="store_true", help="grava docs/novidades/<hoje>.md")
    p.add_argument("--contar", action="store_true", help="imprime só o número de mudanças")
    p.add_argument("--hook", action="store_true", help="mensagem curta para o pre-push (nunca falha)")
    p.add_argument("--marcar", action="store_true", help="grava --ate como avisado no ULTIMO_AVISO")
    p.add_argument("--arquivo", help="com --marcar: o comunicado enviado (docs/novidades/AAAA-MM-DD.md)")
    p.add_argument("--json", action="store_true", help="saída em JSON")
    p.add_argument("--hoje", help="AAAA-MM-DD (testes)")
    a = p.parse_args(argv)

    hoje = dt.date.fromisoformat(a.hoje) if a.hoje else dt.date.today()

    if a.marcar:
        marcar(a.ate, hoje, a.arquivo)
        return 0

    marco = ler_marco()
    desde = a.desde or (marco[0] if marco else None)
    if not desde:
        print("Sem marco: informe --desde <commit> ou rode --marcar uma vez.", file=sys.stderr)
        return 2

    try:
        lista = mudancas(desde, a.ate)
    except SystemExit as e:
        if a.hook:
            print(f"novidades: não consegui contar ({e}).", file=sys.stderr)
            return 0
        raise

    if a.hook:
        if lista:
            nums = ", ".join(it["num"] or it["sha"] for it in lista)
            print(
                f"novidades: {len(lista)} mudança(s) na main ainda sem aviso à equipe ({nums}). "
                "Depois do deploy, rode /manto-novidades.",
                file=sys.stderr,
            )
        return 0
    if a.contar:
        print(len(lista))
        return 0
    if a.json:
        print(json.dumps(lista, ensure_ascii=False, indent=1))
        return 0
    imprimir(lista, desde, a.ate)
    if a.rascunho:
        destino = rascunho(lista, desde, a.ate, hoje)
        print(f"\nRascunho: {destino.relative_to(RAIZ).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
