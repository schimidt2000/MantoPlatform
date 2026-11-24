"""Monta o arquivo versionado da leitura das fotos (feature 360).

Junta as duas fontes da leitura assistida num JSON só, no formato do ``data-model.md``:

* o piloto de 09/11 (19 itens): bloco ``const TEMAS = [...]`` da página
  ``scripts/oneoff/piloto_personagens/conferencia.html`` (literal JavaScript, lido pelo ``node``);
* as saídas dos leitores ``saida_NN.json`` (01–26 de 09/11 e 27 de 24/11).

Não toca em banco nem em produção. As fontes ficam fora do repositório (``C:\\tmp`` e pasta
gitignored); este script é a proveniência do arquivo que a carga lê.

Uso:
    python -I montar_leitura.py <conferencia.html> <pasta propostas> <saida.json>
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path

TIPOS = {"tema", "dupla", "avulso", "generico"}
RE_FICHA = re.compile(r"^(\d+)\s+(.+)$")
RE_FICHA_NA_ACAO = re.compile(r"[Ll]igar o item direto à ficha (\d+)\s+(.+)")
EXTRAIR_PILOTO_JS = (
    "const fs=require('fs');const h=fs.readFileSync(process.argv[1],'utf8');"
    "const m=h.match(/const TEMAS = \\[([\\s\\S]*?)\\n\\];/);"
    "process.stdout.write(JSON.stringify(eval('['+m[1]+']')));"
)

problemas: list[str] = []


def sem_acento(texto: str) -> str:
    """Minúsculas sem acento: "Genérico" → "generico"."""
    decomposto = unicodedata.normalize("NFD", texto.strip().lower())
    return "".join(c for c in decomposto if unicodedata.category(c) != "Mn")


def ficha(valor: str | None, onde: str) -> tuple[int | None, str | None]:
    """ "416 Stormtrooper" → (416, "Stormtrooper"). Formato estranho vira problema, não ficha."""
    if not valor:
        return None, None
    achado = RE_FICHA.match(str(valor).strip())
    if not achado:
        problemas.append(f"{onde}: ficha em formato inesperado ({valor!r})")
        return None, None
    return int(achado.group(1)), achado.group(2).strip()


def recorte_valido(recorte: object, dims: object) -> list[int] | None:
    """Devolve o recorte ajustado a 0–100 ou ``None`` se a geometria não serve."""
    if not (
        isinstance(recorte, list)
        and len(recorte) == 4
        and isinstance(dims, list)
        and len(dims) == 2
    ):
        return None
    try:
        x, y, largura, altura = (int(round(float(v))) for v in recorte)
    except (TypeError, ValueError):
        return None
    largura, altura = min(largura, 100 - x), min(altura, 100 - y)
    if x < 0 or y < 0 or largura <= 0 or altura <= 0:
        return None
    return [x, y, largura, altura]


def personagem(bruto: dict, onde: str) -> dict:
    """Normaliza um personagem da leitura (chaves curtas ``n/f/d/c``) para o formato do arquivo."""
    nome = str(bruto.get("n") or "").strip()
    ficha_id, ficha_nome = ficha(bruto.get("ficha"), f"{onde} / {nome}")
    saida = {
        "nome": nome,
        "foto": None,
        "dims": None,
        "recorte": None,
        "ficha_id": ficha_id,
        "ficha_nome": ficha_nome,
        "aviso": (bruto.get("aviso") or None),
        "sem_foto": True,
    }
    foto = bruto.get("f")
    recorte = recorte_valido(bruto.get("c"), bruto.get("d"))
    if not bruto.get("semFoto") and foto and recorte:
        nome_arquivo = foto if "." in foto else f"{foto}.jpg"
        saida.update(
            foto=nome_arquivo, dims=[int(v) for v in bruto["d"]], recorte=recorte, sem_foto=False
        )
    elif not bruto.get("semFoto"):
        problemas.append(f"{onde} / {nome}: recorte inválido, entrou sem foto")
    if not nome:
        problemas.append(f"{onde}: personagem sem nome")
    return saida


def item(bruto: dict, lote: str) -> dict | None:
    """Normaliza um item da leitura. ``None`` (com problema registrado) se o tipo não existe."""
    onde = f"lote {lote} item {bruto.get('id')} {bruto.get('nome')}"
    tipo = sem_acento(str(bruto.get("tipo") or ""))
    if tipo not in TIPOS or not isinstance(bruto.get("id"), int):
        problemas.append(f"{onde}: tipo ou id inválido ({bruto.get('tipo')!r})")
        return None
    acao = bruto.get("acao") or None
    ficha_id = ficha_nome = None
    if tipo == "avulso" and acao:
        achado = RE_FICHA_NA_ACAO.search(acao)
        if achado:
            ficha_id, ficha_nome = int(achado.group(1)), achado.group(2).strip().rstrip(".")
    return {
        "id": bruto["id"],
        "nome": bruto.get("nome"),
        "tipo": tipo,
        "lote": lote,
        "nota": bruto.get("nota") or None,
        "acao": acao,
        "grupo": bruto.get("grupo") or None,
        "ficha_id": ficha_id,
        "ficha_nome": ficha_nome,
        "personagens": [personagem(p, onde) for p in bruto.get("ps") or []],
    }


def ler_piloto(html: Path) -> list[dict]:
    """O bloco TEMAS é JavaScript (chaves sem aspas): só o ``node`` lê sem reescrever um parser."""
    saida = subprocess.run(
        ["node", "-e", EXTRAIR_PILOTO_JS, str(html)],
        capture_output=True,
        check=True,
        encoding="utf-8",
    )
    return json.loads(saida.stdout)


def main() -> None:
    html, pasta, destino = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    itens: list[dict] = []
    for bruto in ler_piloto(html):
        itens.append(item(bruto, "piloto"))
    for arquivo in sorted(pasta.glob("saida_*.json")):
        for bruto in json.loads(arquivo.read_text(encoding="utf-8")):
            itens.append(item(bruto, arquivo.stem[-2:]))
    itens = [i for i in itens if i]

    repetidos = [i for i, n in Counter(i["id"] for i in itens).items() if n > 1]
    if repetidos:
        problemas.append(f"itens repetidos entre lotes: {repetidos}")

    destino.parent.mkdir(parents=True, exist_ok=True)
    conteudo = {"versao": 1, "gerado_em": date.today().isoformat(), "itens": itens}
    destino.write_text(
        json.dumps(conteudo, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
    )

    pers = [p for i in itens for p in i["personagens"]]
    print("itens:", len(itens), dict(Counter(i["tipo"] for i in itens)))
    print(
        "personagens:",
        len(pers),
        "| com ficha:",
        sum(1 for p in pers if p["ficha_id"]),
        "| sem foto:",
        sum(1 for p in pers if p["sem_foto"]),
        "| com aviso:",
        sum(1 for p in pers if p["aviso"]),
    )
    print("avulsos com ficha do item:", sum(1 for i in itens if i["ficha_id"]))
    print("problemas:", len(problemas))
    for problema in problemas:
        print("  ", problema)


if __name__ == "__main__":
    main()
