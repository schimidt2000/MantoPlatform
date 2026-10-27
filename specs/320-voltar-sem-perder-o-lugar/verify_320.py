"""Verificação da feature 320 — voltar sem perder o lugar.

A tabela de cenários está na `spec.md` (seção "Verificação", 1–12). O comportamento é só de
navegador (histórico, rolagem, sobreposição), então este arquivo faz o que o Princípio VIII pede
do lado do banco e entrega a navegação ao `verify_320_navegador.mjs` (Playwright/Chromium):

  - cria um usuário SUPERADMIN descartável no `manto_local` (login dele só por
    `POST /api/auth/login`, feito pelo navegador);
  - cria dois gastos extras descartáveis com comprovante em foto (PNG) e em PDF de 2 páginas,
    gravados na pasta de uploads do Flask local (os do banco só existem na produção);
  - roda o cenário 9 aqui mesmo (varredura do código: nenhum link de arquivo do sistema abre em
    outra aba);
  - roda o navegador contra o Vite do worktree (cenários 1–8, 10, 11) e, se houver Vite da `main`,
    a contraprova (cenário 12: 1, 5 e 7 TÊM de falhar lá);
  - apaga os gastos e o usuário no `finally`.

Pré-requisitos (quickstart.md): Flask local na 5000 sobre o `manto_local`, Vite do worktree
(`VERIFY_320_INTERNO`, `VERIFY_320_PUBLICO`) e, para a contraprova, Vite da `main`
(`VERIFY_320_MAIN_INTERNO`, `VERIFY_320_MAIN_PUBLICO`).

Rodar (PowerShell, raiz do worktree)::

    $env:DATABASE_URL = (Get-Content C:\\Users\\schim\\Desktop\\Manto_Platform\\.local-db-url -Raw).Trim()
    $env:VERIFY_320_INTERNO = 'http://localhost:5320'; $env:VERIFY_320_PUBLICO = 'http://localhost:5321'
    & $py specs\\320-voltar-sem-perder-o-lugar\\verify_320.py              # todos
    & $py specs\\320-voltar-sem-perder-o-lugar\\verify_320.py '--so=7,8'   # iteração

Saída: 0 = tudo OK; 1 = algum cenário falhou; 2 = ambiente impróprio.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import struct
import subprocess
import sys
import zlib
from datetime import date
from decimal import Decimal
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO_ROOT = AQUI.parents[1]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MAIL_SUPPRESS_SEND", "true")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from app import create_app, db  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.models import Role, SpecialExpense, User  # noqa: E402

PREFIX = "__v320_"
EMAIL = f"{PREFIX}super@manto.local"
SENHA = secrets.token_urlsafe(18)
NAVEGADOR = AQUI / "verify_320_navegador.mjs"
FRONTEND_INTERNO = REPO_ROOT / "frontend" / "apps" / "internal" / "src"
# Pasta de uploads do Flask LOCAL que serve o navegador (a do checkout principal, não a do worktree).
UPLOADS = Path(
    os.environ.get("VERIFY_320_UPLOADS", r"C:\Users\schim\Desktop\Manto_Platform\instance\uploads")
)

app = create_app()
resultados: dict[str, tuple[bool, str]] = {}


def checar(n: str, nome: str, ok: bool, detalhe: str = "") -> None:
    resultados[n] = (ok, f"{nome}: {detalhe}" if detalhe else nome)


# ── banco ─────────────────────────────────────────────────────────────────────────────────────
def limpar() -> None:
    with app.app_context():
        db.session.rollback()
        SpecialExpense.query.filter(SpecialExpense.description.like(f"{PREFIX}%")).delete(
            synchronize_session=False
        )
        for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
            u.roles.clear()
            db.session.delete(u)
        db.session.commit()
    for nome in ARQUIVOS.values():
        (UPLOADS / "expenses" / nome).unlink(missing_ok=True)


def criar_usuario() -> int:
    with app.app_context():
        user = User(name=f"{PREFIX}super", email=EMAIL, is_active=True, has_access=True)
        user.set_password(SENHA)
        user.roles.append(Role.query.filter_by(name=RoleName.SUPERADMIN).one())
        db.session.add(user)
        db.session.commit()
        return user.id


def _png(largura: int = 240, altura: int = 160) -> bytes:
    """PNG de verdade (faixas coloridas), sem depender do Pillow."""
    linhas = b"".join(
        b"\x00" + bytes((40 + (y * 3) % 200, 90, 160 - (y % 100)) * largura) for y in range(altura)
    )

    def bloco(tipo: bytes, dados: bytes) -> bytes:
        return struct.pack(">I", len(dados)) + tipo + dados + struct.pack(">I", zlib.crc32(tipo + dados))

    cabecalho = struct.pack(">IIBBBBB", largura, altura, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", cabecalho) + bloco(b"IDAT", zlib.compress(linhas)) + bloco(b"IEND", b"")


def _pdf(paginas: int = 2) -> bytes:
    """PDF de verdade com texto em cada página (offsets do xref calculados)."""
    objetos: list[bytes] = [b"<< /Type /Catalog /Pages 2 0 R >>"]
    filhos = " ".join(f"{3 + 2 * i} 0 R" for i in range(paginas))
    objetos.append(f"<< /Type /Pages /Kids [{filhos}] /Count {paginas} >>".encode())
    fonte = 3 + 2 * paginas
    for i in range(paginas):
        conteudo = f"BT /F1 28 Tf 72 700 Td (Comprovante 320 - pagina {i + 1}) Tj ET".encode()
        objetos.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {4 + 2 * i} 0 R "
            f"/Resources << /Font << /F1 {fonte} 0 R >> >> >>".encode()
        )
        objetos.append(b"<< /Length %d >>\nstream\n" % len(conteudo) + conteudo + b"\nendstream")
    objetos.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    saida = bytearray(b"%PDF-1.4\n")
    offsets = []
    for n, corpo in enumerate(objetos, start=1):
        offsets.append(len(saida))
        saida += f"{n} 0 obj\n".encode() + corpo + b"\nendobj\n"
    inicio_xref = len(saida)
    saida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
    saida += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    saida += f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{inicio_xref}\n%%EOF\n".encode()
    return bytes(saida)


ARQUIVOS = {"fotos": f"{PREFIX}foto.png", "pdfs": f"{PREFIX}comprovante.pdf"}


def criar_gastos(user_id: int) -> dict[str, list[str]]:
    """Dois gastos descartáveis com comprovante (foto e PDF) gravado no disco do Flask local.

    Os comprovantes do `manto_local` apontam para arquivos que só existem na produção (0 de 135 no
    disco em 27/10/2026), e os soltos na pasta local são de mentira (texto com extensão .jpg/.pdf).
    O verify grava os dele e apaga no `finally`. Data antiga de propósito: o gasto cai no fim da
    lista e a tela precisa estar rolada para vê-lo.
    """
    pasta = UPLOADS / "expenses"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / ARQUIVOS["fotos"]).write_bytes(_png())
    (pasta / ARQUIVOS["pdfs"]).write_bytes(_pdf())
    caminhos: dict[str, list[str]] = {"fotos": [], "pdfs": []}
    with app.app_context():
        for chave, nome in ARQUIVOS.items():
            caminho = f"expenses/{nome}"
            db.session.add(
                SpecialExpense(
                    description=f"{PREFIX}{chave}",
                    category="Outros",
                    amount=Decimal("1.00"),
                    expense_date=date(2001, 1, 1),
                    receipt_path=caminho,
                    created_by_id=user_id,
                )
            )
            caminhos[chave].append(caminho)
        db.session.commit()
    return caminhos


# ── cenário 9: varredura do código ────────────────────────────────────────────────────────────
# Um `<a … target="_blank">` cujo href é arquivo do sistema (assetUrl, comprovante, `/uploads`) é
# exatamente a armadilha do iPhone. Links para outros sites (WhatsApp, Drive, Maps) não entram.
ANCORA = re.compile(r"<a\b[^>]*?>", re.S)
ARQUIVO_NO_HREF = re.compile(r"href=\{[^}]*(assetUrl\(|receipt_url|receipt_path|proofUrl|/uploads)", re.S)


def cenario_9() -> None:
    achados = []
    for arquivo in FRONTEND_INTERNO.rglob("*.tsx"):
        texto = arquivo.read_text(encoding="utf-8")
        for m in ANCORA.finditer(texto):
            tag = m.group(0)
            if 'target="_blank"' in tag and ARQUIVO_NO_HREF.search(tag):
                linha = texto.count("\n", 0, m.start()) + 1
                achados.append(f"{arquivo.relative_to(REPO_ROOT).as_posix()}:{linha}")
    checar(
        "9",
        "nenhum link de arquivo do sistema abre em outra aba",
        not achados,
        "; ".join(achados[:20]) if achados else "",
    )


# ── navegador ─────────────────────────────────────────────────────────────────────────────────
def rodar_navegador(
    interno: str, publico: str, so: list[str], contraprova: bool, gastos: dict
) -> dict:
    env = dict(os.environ)
    env.update(
        {
            "V320_INTERNO": interno,
            "V320_PUBLICO": publico,
            "V320_EMAIL": EMAIL,
            "V320_SENHA": SENHA,
            "V320_DADOS": json.dumps({"comprovantes": gastos}),
            "V320_SO": ",".join(so),
            "V320_CONTRAPROVA": "1" if contraprova else "",
        }
    )
    proc = subprocess.run(
        ["node", str(NAVEGADOR)],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=900,
    )
    sys.stdout.write(proc.stderr)
    ultima = (proc.stdout.strip().splitlines() or ["{}"])[-1]
    try:
        return json.loads(ultima)
    except json.JSONDecodeError:
        print(proc.stdout)
        raise SystemExit(2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--so", default="", help="cenários separados por vírgula (ex.: 7,8)")
    args = parser.parse_args()
    so = [s.strip() for s in args.so.split(",") if s.strip()]

    interno = os.environ.get("VERIFY_320_INTERNO", "http://localhost:5320")
    publico = os.environ.get("VERIFY_320_PUBLICO", "http://localhost:5321")
    main_interno = os.environ.get("VERIFY_320_MAIN_INTERNO")
    main_publico = os.environ.get("VERIFY_320_MAIN_PUBLICO")

    limpar()
    try:
        gastos = criar_gastos(criar_usuario())
        if not so or "9" in so:
            cenario_9()
        nav = [s for s in so if s not in ("9", "12")] if so else []
        if not so or nav:
            for n, (ok, texto) in rodar_navegador(interno, publico, nav, False, gastos).items():
                resultados[n] = (ok, texto)
        if not so or "12" in so:
            if main_interno and main_publico:
                contra = rodar_navegador(main_interno, main_publico, ["1", "5", "7"], True, gastos)
                passaram = [n for n, (ok, _t) in contra.items() if ok]
                checar(
                    "12",
                    "contraprova: 1, 5 e 7 falham na main",
                    len(contra) == 3 and not passaram,
                    "; ".join(f"{n}: {t}" for n, (_ok, t) in contra.items()),
                )
            else:
                print("cenário 12 pulado: sem VERIFY_320_MAIN_INTERNO/VERIFY_320_MAIN_PUBLICO")
    finally:
        limpar()
        with app.app_context():
            sobrou = (
                User.query.filter(User.email.like(f"{PREFIX}%")).count()
                + SpecialExpense.query.filter(SpecialExpense.description.like(f"{PREFIX}%")).count()
                + sum((UPLOADS / "expenses" / n).exists() for n in ARQUIVOS.values())
            )
        if sobrou:
            print(f"LIMPEZA FALHOU: {sobrou} usuário(s) {PREFIX} no banco")

    def chave(n: str) -> int:
        return int(re.sub(r"\D", "", n) or 0)

    for n in sorted(resultados, key=chave):
        ok, texto = resultados[n]
        print(f"{'PASS' if ok else 'FAIL'} {n:>2} — {texto}")
    total = len(resultados)
    bons = sum(1 for ok, _t in resultados.values() if ok)
    print(f"\n{bons}/{total}")
    return 0 if bons == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
