"""Índice do acervo de fotos e vídeos da Manto no Google Drive (feature 357).

O Drive está montado no disco pelo Google Drive para computador (`G:\\My Drive`). Este script percorre
**só as pastas de marketing** (lista fechada em `RAIZES`), grava um índice local com caminho, tema,
sessão (data da festa), tipo e tamanho, e depois responde buscas e gera prévias para olhar a peça antes
de pedi-la. O índice lê só nomes e tamanhos: nenhum arquivo é baixado ao indexar. A prévia baixa só o
arquivo pedido (o Drive para computador traz sob demanda).

Fora da lista nada é lido: Financeiro, notas de funcionários, 1on1s e o resto do Drive pessoal ficam de
fora de propósito.

Uso (a partir de `scripts/marketing/`):
    ..\\..\\.venv\\Scripts\\python.exe drive_indice.py indexar            # ~1–2 min; refaz o índice
    ..\\..\\.venv\\Scripts\\python.exe drive_indice.py temas --busca fada  # o que cada tema tem
    ..\\..\\.venv\\Scripts\\python.exe drive_indice.py buscar "fadas glow" --tipo foto_editada
    ..\\..\\.venv\\Scripts\\python.exe drive_indice.py ver "<caminho>" --saida <pasta>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

DRIVE = Path(os.getenv("MANTO_DRIVE_RAIZ", r"G:\My Drive"))
INDICE = Path(os.getenv("MANTO_DRIVE_INDICE", str(Path.home() / ".manto-drive" / "indice.sqlite")))
PREVIAS = Path(os.getenv("MANTO_DRIVE_PREVIAS", str(Path.home() / ".manto-drive" / "previas")))

# Lista fechada: só o que é material de marketing. Pasta nova entra aqui, nunca por parâmetro.
RAIZES = (
    "Temas Manto Produções",
    "Conteúdo para Vendas",
    "Publicidades",
    "Depoimentos Clientes",
    "VIDEOS GABI",
    "gabi artes",
)
# Quem aparece nestas pastas é cliente: só vai para anúncio com a autorização dela.
COM_CLIENTE = ("Depoimentos Clientes",)

FOTO = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tif", ".tiff"}
VIDEO = {".mp4", ".mov", ".m4v"}
# Pastas de projeto e cache do Premiere/After Effects: milhares de arquivos que não são peça.
IGNORAR = (
    "adobe premiere",
    "adobe after effects",
    "after effects",
    "peak files",
    "auto-save",
    "motion graphics template",
    "animation composer",
    "premiere composer",
    "aegraphics",
    "starter pack",
    "packs",
    "assets",
    "help",
    "captured and generated",
    "trilha",
    "audio",
    "audios",
)
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
MESES = {m: i for i, m in enumerate("jan fev mar abr mai jun jul ago set out nov dez".split(), 1)}


def _sa(s: str) -> str:
    """Minúsculas e sem acento, para comparar nomes."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn"
    ).lower()


def _sessao(partes: list[str]) -> str | None:
    """A data da sessão (festa ou ensaio fotográfico) pelo nome da pasta: 20250927 ou 09Abr2025."""
    for p in partes:
        m = re.search(r"(20\d{2})(\d{2})(\d{2})", p)
        if m:
            try:
                return date(int(m[1]), int(m[2]), int(m[3])).isoformat()
            except ValueError:
                pass
        m = re.search(r"(\d{1,2})\s*([a-zç]{3})[a-zç]*\s*(20\d{2})", _sa(p))
        if m and m[2] in MESES:
            try:
                return date(int(m[3]), MESES[m[2]], int(m[1])).isoformat()
            except ValueError:
                pass
    return None


def _tipo(partes_sa: list[str], ext: str) -> str:
    """Foto editada × bruta, vídeo pronto × bruto × ensaio, arte — pelo nome das pastas."""
    if ext in FOTO:
        if any(p == "arte" or p.startswith("arte ") for p in partes_sa):
            return "arte"
        if any(
            p in ("editadas", "editados", "editada", "fotos padrao") or "editad" in p
            for p in partes_sa
        ):
            return "foto_editada"
        return "foto_bruta"
    if any("ensaio" in p for p in partes_sa):
        return "video_ensaio"
    if any(
        p in ("export", "exports", "videos padrao", "finalizados") or "export" in p
        for p in partes_sa
    ):
        return "video_pronto"
    return "video_bruto"


def indexar(_args) -> int:
    INDICE.parent.mkdir(parents=True, exist_ok=True)
    temporario = INDICE.with_suffix(".tmp")
    temporario.unlink(missing_ok=True)
    db = sqlite3.connect(temporario)
    db.execute(
        "CREATE TABLE arquivos (caminho TEXT PRIMARY KEY, raiz TEXT, tema TEXT, sessao TEXT, tipo TEXT,"
        " ext TEXT, bytes INTEGER, modificado TEXT, busca TEXT)"
    )
    total, inicio = 0, datetime.now()
    for raiz in RAIZES:
        base = DRIVE / raiz
        if not base.exists():
            print(f"[aviso] pasta não encontrada no Drive: {raiz}", file=sys.stderr)
            continue
        linhas = []
        for pasta, subpastas, arquivos in os.walk(base):
            rel = Path(pasta).relative_to(base)
            partes = list(rel.parts)
            partes_sa = [_sa(p) for p in partes]
            # Poda a descida nas pastas de projeto/cache (o grosso dos 147 mil arquivos).
            subpastas[:] = [
                s
                for s in subpastas
                if not UUID.match(s.lower()) and not any(k in _sa(s) for k in IGNORAR)
            ]
            for nome in arquivos:
                ext = Path(nome).suffix.lower()
                if ext not in FOTO and ext not in VIDEO:
                    continue
                caminho = Path(pasta) / nome
                try:
                    st = caminho.stat()
                except OSError:
                    continue
                tema = partes[0] if raiz == "Temas Manto Produções" and partes else None
                linhas.append(
                    (
                        str(caminho),
                        raiz,
                        tema,
                        _sessao(partes),
                        _tipo(partes_sa, ext),
                        ext,
                        st.st_size,
                        datetime.fromtimestamp(st.st_mtime).date().isoformat(),
                        _sa(f"{raiz} {' '.join(partes)} {nome}"),
                    )
                )
        db.executemany("INSERT OR REPLACE INTO arquivos VALUES (?,?,?,?,?,?,?,?,?)", linhas)
        db.commit()
        total += len(linhas)
        print(f"{raiz}: {len(linhas)} fotos e vídeos", file=sys.stderr)
    db.execute("CREATE INDEX ix_tema ON arquivos (tema, tipo)")
    db.execute("CREATE TABLE sobre (chave TEXT PRIMARY KEY, valor TEXT)")
    db.execute(
        "INSERT INTO sobre VALUES ('gerado_em', ?)", (datetime.now().isoformat(timespec="seconds"),)
    )
    db.commit()
    db.close()
    os.replace(temporario, INDICE)  # troca atômica: quem lê no meio nunca vê índice pela metade
    segundos = int((datetime.now() - inicio).total_seconds())
    print(
        json.dumps(
            {"indice": str(INDICE), "arquivos": total, "segundos": segundos}, ensure_ascii=False
        )
    )
    return 0


def _abrir() -> sqlite3.Connection:
    if not INDICE.exists():
        sys.exit("Sem índice. Rode primeiro: drive_indice.py indexar")
    return sqlite3.connect(INDICE)


def _filtro(termo: str | None) -> tuple[str, list[str]]:
    palavras = _sa(termo or "").split()
    return " AND ".join(["busca LIKE ?"] * len(palavras)) or "1=1", [f"%{p}%" for p in palavras]


def temas(args) -> int:
    """Por tema: quantas fotos editadas, vídeos prontos e brutos, e a sessão mais recente."""
    db = _abrir()
    where, params = _filtro(args.busca)
    linhas = db.execute(
        f"""SELECT tema, sum(tipo='foto_editada'), sum(tipo='foto_bruta'), sum(tipo='video_pronto'),
                   sum(tipo='video_bruto'), sum(tipo='arte'), max(sessao)
            FROM arquivos WHERE tema IS NOT NULL AND {where} GROUP BY tema ORDER BY tema""",
        params,
    ).fetchall()
    chaves = (
        "tema",
        "fotos_editadas",
        "fotos_brutas",
        "videos_prontos",
        "videos_brutos",
        "artes",
        "ultima_sessao",
    )
    print(
        json.dumps(
            [dict(zip(chaves, linha, strict=True)) for linha in linhas],
            ensure_ascii=False,
            indent=1,
        )
    )
    return 0


def buscar(args) -> int:
    db = _abrir()
    where, params = _filtro(args.termo)
    if args.tipo:
        where += " AND tipo = ?"
        params.append(args.tipo)
    linhas = db.execute(
        f"""SELECT caminho, raiz, tema, sessao, tipo, round(bytes / 1048576.0, 1) FROM arquivos WHERE {where}
            ORDER BY coalesce(sessao, modificado) DESC, caminho LIMIT ?""",
        [*params, args.limite],
    ).fetchall()
    saida = []
    for caminho, raiz, tema, sessao, tipo, mb in linhas:
        item = {"caminho": caminho, "tema": tema, "sessao": sessao, "tipo": tipo, "mb": mb}
        if raiz in COM_CLIENTE:
            item["aviso"] = "cliente na imagem: só com autorização dela"
        saida.append(item)
    print(json.dumps(saida, ensure_ascii=False, indent=1))
    return 0


def _orientacao(largura: int, altura: int) -> str:
    if abs(largura - altura) <= 0.05 * max(largura, altura):
        return "quadrada"
    return "vertical" if altura > largura else "horizontal"


def ver(args) -> int:
    """Prévia de uma foto (JPEG de 1024 px) ou três quadros de um vídeo, para olhar antes de pedir."""
    caminho = Path(args.caminho)
    if not any(caminho.is_relative_to(DRIVE / r) for r in RAIZES):
        sys.exit("Só abro arquivos das pastas de marketing (RAIZES).")
    saida = Path(args.saida) if args.saida else PREVIAS
    saida.mkdir(parents=True, exist_ok=True)
    base = re.sub(r"[^\w.-]+", "_", caminho.stem)[:60]
    ext = caminho.suffix.lower()
    if ext in FOTO:
        from PIL import Image, ImageOps

        if ext in (".heic", ".heif"):
            import pillow_heif

            pillow_heif.register_heif_opener()
        with Image.open(caminho) as im:
            im = ImageOps.exif_transpose(im)
            largura, altura = im.size
            im.thumbnail((1024, 1024))
            previa = saida / f"{base}.jpg"
            im.convert("RGB").save(previa, "JPEG", quality=85)
        info = {
            "previa": str(previa),
            "largura": largura,
            "altura": altura,
            "orientacao": _orientacao(largura, altura),
        }
        # Sem esticar: o maior recorte na proporção do anúncio tem de ter pelo menos a altura dele
        # (4:5 = 1080×1350; 9:16 = 1080×1920).
        info["aguenta_4x5"] = min(altura, largura / 0.8) >= 1350
        info["aguenta_9x16"] = min(altura, largura / 0.5625) >= 1920
    elif ext in VIDEO:
        sonda = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(caminho),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        dados = json.loads(sonda.stdout)
        video = next(s for s in dados["streams"] if s.get("codec_type") == "video")
        largura, altura = int(video["width"]), int(video["height"])
        rotacao = abs(int((video.get("side_data_list") or [{}])[0].get("rotation", 0) or 0))
        if rotacao in (90, 270):
            largura, altura = altura, largura
        duracao = float(dados["format"].get("duration") or 0)
        # Quadros espaçados por igual, com o segundo de cada um: para escolher o trecho a recortar.
        n = max(1, min(args.quadros, 24))
        quadros = []
        for i in range(n):
            segundo = duracao * (i + 0.5) / n
            quadro = saida / f"{base}_q{i + 1:02d}_{segundo:05.1f}s.jpg"
            subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-ss", f"{segundo:.2f}", "-i", str(caminho), "-frames:v", "1",
                 "-vf", "scale=540:-2", str(quadro)],
                check=True,
            )  # fmt: skip
            quadros.append({"segundo": round(segundo, 1), "arquivo": str(quadro)})
        info = {
            "quadros": quadros,
            "largura": largura,
            "altura": altura,
            "orientacao": _orientacao(largura, altura),
            "segundos": round(duracao, 1),
            "aguenta_9x16": altura > largura and altura >= 1920,
        }
    else:
        sys.exit(f"Tipo não suportado: {ext}")
    info["caminho"] = str(caminho)
    if any(caminho.is_relative_to(DRIVE / r) for r in COM_CLIENTE):
        info["aviso"] = "cliente na imagem: só com autorização dela"
    print(json.dumps(info, ensure_ascii=False, indent=1))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("indexar", help="refaz o índice (só nomes e tamanhos)").set_defaults(fn=indexar)
    p = sub.add_parser("temas", help="o que cada tema tem")
    p.add_argument("--busca")
    p.set_defaults(fn=temas)
    p = sub.add_parser("buscar", help="arquivos por palavra (tema, pasta, nome)")
    p.add_argument("termo")
    p.add_argument(
        "--tipo",
        choices=[
            "foto_editada",
            "foto_bruta",
            "arte",
            "video_pronto",
            "video_bruto",
            "video_ensaio",
        ],
    )
    p.add_argument("--limite", type=int, default=30)
    p.set_defaults(fn=buscar)
    p = sub.add_parser("ver", help="prévia de uma foto ou três quadros de um vídeo")
    p.add_argument("caminho")
    p.add_argument("--saida")
    p.add_argument("--quadros", type=int, default=3, help="vídeo: quantos quadros (até 24)")
    p.set_defaults(fn=ver)
    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
