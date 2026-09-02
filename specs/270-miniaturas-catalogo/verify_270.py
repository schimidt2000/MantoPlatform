"""Verificação da feature 270 — miniaturas por largura (catálogo público e Banco de Talentos).

Cenários (spec.md, "Verificação"):
 1. `/catalogo/midia/t/128/<foto>` devolve JPEG de 128px de largura com < 10% dos bytes do original,
    `Cache-Control` `immutable` de 1 ano.
 2. A segunda chamada é servida do cache: o arquivo em disco não é reescrito (mesmo `mtime`) e a
    pasta não ganha arquivo novo.
 3. Largura fora da allowlist → 404 e nenhuma pasta/arquivo de cache criado.
 4. Arquivo inexistente → 404 sem criar entrada de cache.
 5. Digest: URL nova → digest novo; receita OG e variante não colidem; o cache OG existente
    continua válido (`md5("1|url")`).
 6. Concorrência: 8 requisições simultâneas da mesma variante nova → todas 200, um único arquivo
    de cache, nenhum `.tmp` sobrando.
 7. Foto de talento: sem login → recusado; com login → 200, 320px, `Cache-Control: private … immutable`.
 8. `/uploads` fora das fotos de talento NÃO ganha cache longo; `/uploads/t/…/talent_docs/…` → 404.
 9. Variante redimensiona pela LARGURA (retrato 1200×1500 → 640×800, não 512×640).
10. Limpeza (arquivos de teste, caches gerados, usuário).

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    .\\.venv\\Scripts\\python.exe specs\\270-miniaturas-catalogo\\verify_270.py
"""
from __future__ import annotations

import glob
import hashlib
import io
import os
import sys
import threading
import time
import traceback
from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from PIL import Image  # noqa: E402

from app import create_app, db  # noqa: E402
from app.catalogo import og_ops  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.models import Role, User  # noqa: E402

PREFIX = "__v270_"
SENHA = "verify-270-senha"

app = create_app()
app.config["TESTING"] = True
UPLOADS = app.config["UPLOAD_FOLDER"]

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _jpeg(largura: int, altura: int) -> bytes:
    """JPEG sintético com textura (para o tamanho do arquivo ser realista, não 2 KB de cor lisa)."""
    img = Image.new("RGB", (largura, altura))
    px = img.load()
    for y in range(altura):
        for x in range(0, largura, 1):
            px[x, y] = ((x * 7) % 256, (y * 3) % 256, ((x ^ y) * 5) % 256)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _grava(subpasta: str, nome: str, dados: bytes) -> str:
    pasta = os.path.join(UPLOADS, subpasta)
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, nome)
    with open(caminho, "wb") as fh:
        fh.write(dados)
    estado.setdefault("arquivos", []).append(caminho)
    return caminho


def _cache_files(subpasta_cache: str, largura: int) -> list[str]:
    return sorted(glob.glob(os.path.join(UPLOADS, subpasta_cache, str(largura), "*")))


def _dimensoes(body: bytes) -> tuple[int, int]:
    img = Image.open(io.BytesIO(body))
    return img.width, img.height


def preparar() -> None:
    limpar()
    original = _jpeg(1200, 1500)
    estado["original_bytes"] = len(original)
    estado["foto"] = f"{PREFIX}teste.jpg"
    _grava(og_ops.MEDIA_SUBFOLDER, estado["foto"], original)
    estado["foto_conc"] = f"{PREFIX}conc.jpg"
    _grava(og_ops.MEDIA_SUBFOLDER, estado["foto_conc"], _jpeg(900, 900))
    estado["rosto"] = f"{PREFIX}rosto.jpg"
    _grava(og_ops.TALENT_MEDIA_SUBFOLDER, estado["rosto"], _jpeg(1000, 1333))
    estado["doc"] = f"{PREFIX}doc.jpg"
    _grava("talent_docs", estado["doc"], _jpeg(800, 600))

    email = f"{PREFIX}sa@manto.local"
    user = User(name=f"{PREFIX}sa", email=email, is_active=True, has_access=True)
    user.set_password(SENHA)
    user.roles.append(Role.query.filter_by(name=RoleName.SUPERADMIN).one())
    db.session.add(user)
    db.session.commit()
    estado["superadmin"] = user


def _remove_com_paciencia(caminho: str) -> None:
    """`os.remove` que espera um handle recém-fechado ser solto (só acontece no Windows)."""
    for tentativa in range(5):
        try:
            os.remove(caminho)
            return
        except FileNotFoundError:
            return
        except OSError:
            if tentativa == 4:
                raise
            time.sleep(0.1)


def limpar() -> None:
    for caminho in estado.get("arquivos", []):
        _remove_com_paciencia(caminho)
    # Caches gerados pelos cenários: todos os digests das URLs de teste, em todas as larguras.
    urls = [
        f"/catalogo/midia/{estado.get('foto', PREFIX + 'teste.jpg')}",
        f"/catalogo/midia/{estado.get('foto_conc', PREFIX + 'conc.jpg')}",
        f"/uploads/talent_photos/{estado.get('rosto', PREFIX + 'rosto.jpg')}",
    ]
    for url in urls:
        pastas = og_ops.pastas_da_variante(url, UPLOADS)
        if not pastas:
            continue
        for largura in og_ops.LARGURAS_PERMITIDAS:
            digest = og_ops.cache_digest(url, og_ops.receita_variante(largura))
            for f in glob.glob(os.path.join(pastas[1], str(largura), f"{digest}_*")):
                _remove_com_paciencia(f)
    for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        u.roles.clear()
        db.session.delete(u)
    db.session.commit()


# ───────────────────────────── cenários ─────────────────────────────

def cen_01_variante_128() -> None:
    with app.test_client() as c:
        r = c.get(f"/catalogo/midia/t/128/{estado['foto']}")
        _garante(r.status_code == 200, f"variante → {r.status_code}")
        _garante(r.mimetype == "image/jpeg", f"mimetype {r.mimetype}")
        w, h = _dimensoes(r.data)
        _garante(w == 128, f"largura {w}, esperava 128")
        _garante(h == 160, f"altura {h}, esperava 160 (1200×1500 → 128×160)")
        razao = len(r.data) / estado["original_bytes"]
        _garante(razao < 0.10, f"variante tem {razao:.1%} do original (limite 10%)")
        cc = r.headers.get("Cache-Control", "")
        _garante("immutable" in cc and "max-age=31536000" in cc and "public" in cc, f"Cache-Control: {cc}")
        estado["v128_bytes"] = r.data
        print(f"         (original {estado['original_bytes'] / 1024:.0f} KB → 128px {len(r.data) / 1024:.1f} KB)")


def cen_02_segunda_chamada_do_cache() -> None:
    url = f"/catalogo/midia/{estado['foto']}"
    thumb = og_ops.variante_em_cache(url, 128, UPLOADS)
    _garante(thumb is not None, "cenário 1 não deixou arquivo em cache")
    antes = os.stat(thumb.path).st_mtime_ns
    n_antes = len(_cache_files(og_ops.THUMBS_SUBFOLDER, 128))
    with app.test_client() as c:
        r = c.get(f"/catalogo/midia/t/128/{estado['foto']}")
    _garante(r.status_code == 200 and r.data == estado["v128_bytes"], "segunda resposta difere")
    _garante(os.stat(thumb.path).st_mtime_ns == antes, "o arquivo de cache foi reescrito")
    _garante(len(_cache_files(og_ops.THUMBS_SUBFOLDER, 128)) == n_antes, "a pasta ganhou arquivo novo")


def cen_03_largura_fora_da_allowlist() -> None:
    pasta_200 = os.path.join(UPLOADS, og_ops.THUMBS_SUBFOLDER, "200")
    existia = os.path.isdir(pasta_200)
    with app.test_client() as c:
        r = c.get(f"/catalogo/midia/t/200/{estado['foto']}")
    _garante(r.status_code == 404, f"largura 200 → {r.status_code}, esperava 404")
    _garante(os.path.isdir(pasta_200) == existia, "criou pasta de cache para largura proibida")


def cen_04_arquivo_inexistente() -> None:
    n_antes = len(_cache_files(og_ops.THUMBS_SUBFOLDER, 128))
    with app.test_client() as c:
        r = c.get(f"/catalogo/midia/t/128/{PREFIX}nao_existe.jpg")
        _garante(r.status_code == 404, f"inexistente → {r.status_code}")
        r2 = c.get(f"/catalogo/midia/t/128/..%2F{estado['foto']}")
        _garante(r2.status_code == 404, f"path traversal → {r2.status_code}")
    _garante(len(_cache_files(og_ops.THUMBS_SUBFOLDER, 128)) == n_antes, "404 gravou cache")


def cen_05_digest_por_url_e_receita() -> None:
    a = og_ops.cache_digest("/catalogo/midia/a.jpg", og_ops.receita_variante(128))
    b = og_ops.cache_digest("/catalogo/midia/b.jpg", og_ops.receita_variante(128))
    _garante(a != b, "foto nova com o mesmo digest")
    og = og_ops.cache_digest("/catalogo/midia/a.jpg")
    _garante(og != a, "receita OG e variante 128 colidem no digest")
    _garante(
        og == hashlib.md5(b"1|/catalogo/midia/a.jpg").hexdigest(),
        "o digest OG mudou — o cache de prévia existente em produção seria invalidado",
    )
    _garante(
        og_ops.cache_digest("/catalogo/midia/a.jpg", og_ops.receita_variante(320)) != a,
        "larguras diferentes com o mesmo digest",
    )


def cen_06_concorrencia() -> None:
    caminho = f"/catalogo/midia/t/320/{estado['foto_conc']}"
    codigos: list[int] = []
    erros: list[BaseException] = []
    barreira = threading.Barrier(8)

    def pedir() -> None:
        try:
            with app.test_client() as c:
                barreira.wait(timeout=10)
                # No Windows a troca atômica (`os.replace`) e uma LEITURA concorrente do mesmo
                # arquivo podem colidir com ACCESS_DENIED — artefato do sistema de arquivos daqui,
                # não do motor: no Linux (produção) o rename é atômico para quem lê. Só no Windows,
                # e só para PermissionError, a requisição é repetida; o que se prova continua
                # sendo: todas 200 ao final, um arquivo de cache, nenhum `.tmp`.
                for tentativa in range(3):
                    try:
                        r = c.get(caminho)
                        break
                    except PermissionError:
                        if os.name != "nt" or tentativa == 2:
                            raise
                        time.sleep(0.05)
                codigos.append(r.status_code)
                _dimensoes(r.data)  # JPEG íntegro
                r.close()  # solta o handle do arquivo (no Windows ele bloqueia a limpeza)
        except BaseException as exc:  # noqa: BLE001
            erros.append(exc)

    threads = [threading.Thread(target=pedir) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    _garante(not erros, f"uma requisição concorrente estourou: {erros[:1]}")
    _garante(codigos == [200] * 8, f"códigos: {codigos}")
    digest = og_ops.cache_digest(f"/catalogo/midia/{estado['foto_conc']}", og_ops.receita_variante(320))
    pasta = os.path.join(UPLOADS, og_ops.THUMBS_SUBFOLDER, "320")
    finais = glob.glob(os.path.join(pasta, f"{digest}_*.jpg"))
    sobras = glob.glob(os.path.join(pasta, f"{digest}_*.tmp"))
    _garante(len(finais) == 1, f"{len(finais)} arquivos de cache para o mesmo digest")
    _garante(not sobras, f"ficaram temporários: {sobras}")


def cen_07_talento_exige_login() -> None:
    caminho = f"/uploads/t/320/talent_photos/{estado['rosto']}"
    with app.test_client() as c:
        r = c.get(caminho)
        _garante(r.status_code in (302, 401), f"sem login → {r.status_code}")
    with app.test_client() as c:
        r = c.post("/api/auth/login", json={"email": estado["superadmin"].email, "password": SENHA})
        _garante(r.status_code == 200, f"login → {r.status_code}")
        r = c.get(caminho)
        _garante(r.status_code == 200, f"variante de talento → {r.status_code}")
        w, _h = _dimensoes(r.data)
        _garante(w == 320, f"largura {w}, esperava 320")
        cc = r.headers.get("Cache-Control", "")
        _garante("private" in cc and "immutable" in cc and "public" not in cc, f"Cache-Control: {cc}")
        # O original da foto de talento também ganhou o cache longo privado.
        r = c.get(f"/uploads/talent_photos/{estado['rosto']}")
        _garante(r.status_code == 200, f"original de talento → {r.status_code}")
        cc = r.headers.get("Cache-Control", "")
        _garante("private" in cc and "immutable" in cc, f"Cache-Control do original: {cc}")


def cen_08_resto_de_uploads_sem_cache_longo() -> None:
    with app.test_client() as c:
        r = c.post("/api/auth/login", json={"email": estado["superadmin"].email, "password": SENHA})
        _garante(r.status_code == 200, f"login → {r.status_code}")
        r = c.get(f"/uploads/talent_docs/{estado['doc']}")
        _garante(r.status_code == 200, f"documento → {r.status_code}")
        cc = r.headers.get("Cache-Control", "")
        _garante("immutable" not in cc and "max-age=31536000" not in cc, f"documento com cache longo: {cc}")
        r = c.get(f"/uploads/t/320/talent_docs/{estado['doc']}")
        _garante(r.status_code == 404, f"variante de documento → {r.status_code}, esperava 404")
        r = c.get(f"/uploads/t/200/talent_photos/{estado['rosto']}")
        _garante(r.status_code == 404, f"largura proibida em talento → {r.status_code}")
    pasta_docs = os.path.join(UPLOADS, "talent_docs_thumbs")
    _garante(not os.path.isdir(pasta_docs), "criou cache de miniatura para documentos")


def cen_09_redimensiona_pela_largura() -> None:
    with app.test_client() as c:
        r = c.get(f"/catalogo/midia/t/640/{estado['foto']}")
    _garante(r.status_code == 200, f"640 → {r.status_code}")
    w, h = _dimensoes(r.data)
    _garante((w, h) == (640, 800), f"{w}×{h}: a variante deve ter LARGURA 640 (retrato), não lado maior 640")


def cen_10_limpeza() -> None:
    limpar()
    for url, largura in (
        (f"/catalogo/midia/{estado['foto']}", 128),
        (f"/catalogo/midia/{estado['foto_conc']}", 320),
        (f"/uploads/talent_photos/{estado['rosto']}", 320),
    ):
        _garante(og_ops.variante_em_cache(url, largura, UPLOADS) is None, f"cache de {url} sobrou")
    _garante(User.query.filter(User.email.like(f"{PREFIX}%")).count() == 0, "usuário de teste sobrou")


def main() -> int:
    print("Feature 270 — miniaturas por largura")
    with app.app_context():
        preparar()
        try:
            cenario("1. /t/128 devolve 128px com <10% dos bytes e immutable", cen_01_variante_128)
            cenario("2. segunda chamada vem do cache (mtime igual)", cen_02_segunda_chamada_do_cache)
            cenario("3. largura fora da allowlist → 404 sem gravar", cen_03_largura_fora_da_allowlist)
            cenario("4. arquivo inexistente / traversal → 404 sem cache", cen_04_arquivo_inexistente)
            cenario("5. digest por URL e por receita; OG preservado", cen_05_digest_por_url_e_receita)
            cenario("6. 8 requisições simultâneas → 1 arquivo, sem .tmp", cen_06_concorrencia)
            cenario("7. talento: login obrigatório, 320px, cache private", cen_07_talento_exige_login)
            cenario("8. resto de /uploads sem cache longo; docs sem variante", cen_08_resto_de_uploads_sem_cache_longo)
            cenario("9. retrato 1200×1500 → 640×800 (pela largura)", cen_09_redimensiona_pela_largura)
        finally:
            cenario("10. limpeza", cen_10_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"{ok}/{len(resultados)} OK")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
