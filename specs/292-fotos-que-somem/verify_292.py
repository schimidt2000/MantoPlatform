"""Verificação da feature 292 — a foto que falta não pode virar quadrado quebrado.

Cenários:
 1. Variante de figurino: `/uploads/t/320/figurino_photos/<f>` → 200, JPEG de 320px de largura,
    `private … immutable`; a segunda chamada vem do cache (mesmo `mtime`, nenhum arquivo novo).
 2. `talent_docs` continua SEM variante (`/uploads/t/320/talent_docs/<f>` → 404). É documento de
    identidade: miniatura de RG espalha PII por mais um lugar no disco. Regressão da 270.
 3. Largura fora da allowlist → 404 e nada gravado em disco.
 4. `figurino_photos` passa a responder `immutable`; `contracts` continua sem cache longo.
 5. `/portal/photo/...` serve o ORIGINAL (a reescrita do portal não casa com a regex de variante)
    e agora carimba `Cache-Control` — antes revalidava toda foto a cada visita no celular.
 6. Anti-divergência TS↔PY: o `client.ts` e o `og_ops.py` concordam sobre quem tem variante e
    sobre as larguras. Sem isto o `<img>` pede uma URL que o Flask responde com 404.
 7. Rotação de figurino grava caminho NOVO, apaga o antigo e invalida as variantes dele.
 8. HEIC entra pelo portal e sai `.jpg` com no máximo 1200px.
 9. HEIC ilegível → 400 com mensagem em pt-BR e NADA gravado (não guarda arquivo invisível).
10. PDF e XML atravessam `save_file` byte a byte idênticos — PIL nunca os abre.
11. Dois `contrato.pdf` no mesmo endpoint viram dois arquivos distintos (antes se sobrescreviam).
12. Comprovante de gasto: 12 MB recusado; 1 MB grava `expenses/<x>` SEM `/uploads/`, que é a
    string exata que `_can_read_expense_receipt` compara.
13. `midia_ops` classifica cada estado pelo motivo certo — inclusive o PDF renomeado de `.jpg`,
    que existe em produção e é servido como `image/jpeg`.
14. Limpeza.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    $env:MAIL_SUPPRESS_SEND = "true"; $env:MANTO_SEM_THREADS = "1"
    .\\.venv\\Scripts\\python.exe specs\\292-fotos-que-somem\\verify_292.py
"""
from __future__ import annotations

import glob
import io
import os
import re
import sys
import time
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

from PIL import Image  # noqa: E402

from app import create_app, db, imaging  # noqa: E402
from app.catalogo import og_ops  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.models import FigurinoSheet, Role, Talent, User  # noqa: E402

PREFIX = "__v292_"
SENHA = "verify-292-senha"

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


def _imagem(largura: int, altura: int, formato: str = "JPEG") -> bytes:
    """Imagem sintética com textura — cor lisa comprime a 2 KB e falseia a comparação de bytes."""
    imaging.suporte_heif()
    img = Image.new("RGB", (largura, altura))
    px = img.load()
    for y in range(altura):
        for x in range(largura):
            px[x, y] = ((x * 7) % 256, (y * 3) % 256, ((x ^ y) * 5) % 256)
    buf = io.BytesIO()
    img.save(buf, format=formato, quality=90)
    return buf.getvalue()


def _grava(subpasta: str, nome: str, dados: bytes) -> str:
    pasta = os.path.join(UPLOADS, subpasta)
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, nome)
    with open(caminho, "wb") as fh:
        fh.write(dados)
    estado.setdefault("arquivos", []).append(caminho)
    return caminho


def _login(client) -> None:
    resp = client.post(
        "/api/auth/login",
        json={"email": estado["superadmin"].email, "password": SENHA},
    )
    _garante(resp.status_code == 200, f"login falhou: {resp.status_code} {resp.data[:200]!r}")


def preparar() -> None:
    limpar()
    estado["fig_nome"] = f"{PREFIX}fig.jpg"
    estado["fig_bytes"] = _imagem(1000, 1300)
    _grava(og_ops.FIGURINO_MEDIA_SUBFOLDER, estado["fig_nome"], estado["fig_bytes"])
    estado["doc_nome"] = f"{PREFIX}doc.jpg"
    _grava("talent_docs", estado["doc_nome"], _imagem(800, 600))
    estado["contrato_nome"] = f"{PREFIX}contrato.pdf"
    _grava("contracts", estado["contrato_nome"], b"%PDF-1.5\n" + b"x" * 2000)
    estado["rosto_nome"] = f"{PREFIX}rosto.jpg"
    _grava(og_ops.TALENT_MEDIA_SUBFOLDER, estado["rosto_nome"], _imagem(900, 1200))

    email = f"{PREFIX}sa@manto.local"
    user = User(name=f"{PREFIX}sa", email=email, is_active=True, has_access=True)
    user.set_password(SENHA)
    user.roles.append(Role.query.filter_by(name=RoleName.SUPERADMIN).one())
    db.session.add(user)

    ficha = FigurinoSheet(
        character_name=f"{PREFIX}Personagem",
        photo_filename=f"/uploads/{og_ops.FIGURINO_MEDIA_SUBFOLDER}/{estado['fig_nome']}",
    )
    db.session.add(ficha)

    talento = Talent(
        full_name=f"{PREFIX}Talento",
        status="active",
        photo_face_path=f"/uploads/{og_ops.TALENT_MEDIA_SUBFOLDER}/{estado['rosto_nome']}",
    )
    db.session.add(talento)
    db.session.commit()
    estado["superadmin"] = user
    estado["ficha_id"] = ficha.id
    estado["talento_id"] = talento.id


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
                return
            time.sleep(0.1)


def limpar() -> None:
    for caminho in estado.get("arquivos", []):
        _remove_com_paciencia(caminho)
    for url in estado.get("urls_para_invalidar", []):
        og_ops.invalidar_variantes(url, UPLOADS)
    for pasta in (og_ops.FIGURINO_THUMBS_SUBFOLDER, og_ops.TALENT_THUMBS_SUBFOLDER):
        for largura in og_ops.LARGURAS_PERMITIDAS:
            for caminho in glob.glob(os.path.join(UPLOADS, pasta, str(largura), "*.tmp")):
                _remove_com_paciencia(caminho)
    estado["arquivos"] = []

    FigurinoSheet.query.filter(FigurinoSheet.character_name.like(f"{PREFIX}%")).delete(
        synchronize_session=False
    )
    Talent.query.filter(Talent.full_name.like(f"{PREFIX}%")).delete(synchronize_session=False)
    for user in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        # Papel antes do usuário: a FK de `user_roles` segura o delete (padrão dos verify_*).
        user.roles.clear()
        db.session.delete(user)
    db.session.commit()


# ── Cenários ──────────────────────────────────────────────────────────────────

def c01_variante_figurino():
    url = f"/uploads/{og_ops.FIGURINO_MEDIA_SUBFOLDER}/{estado['fig_nome']}"
    estado.setdefault("urls_para_invalidar", []).append(url)
    with app.test_client() as client:
        _login(client)
        alvo = f"/uploads/t/320/{og_ops.FIGURINO_MEDIA_SUBFOLDER}/{estado['fig_nome']}"
        resp = client.get(alvo)
        _garante(resp.status_code == 200, f"variante devolveu {resp.status_code}")
        largura, _ = Image.open(io.BytesIO(resp.data)).size
        _garante(largura == 320, f"largura {largura} != 320")
        _garante(
            len(resp.data) < len(estado["fig_bytes"]) * 0.30,
            f"variante com {len(resp.data)} bytes contra {len(estado['fig_bytes'])} do original",
        )
        _garante("immutable" in resp.headers.get("Cache-Control", ""), "sem immutable")

        cache = og_ops.variante_em_cache(url, 320, UPLOADS)
        _garante(cache is not None, "nada foi para o cache")
        mtime = os.path.getmtime(cache.path)
        arquivos_antes = sorted(
            glob.glob(os.path.join(UPLOADS, og_ops.FIGURINO_THUMBS_SUBFOLDER, "320", "*"))
        )
        time.sleep(0.05)
        resp2 = client.get(alvo)
        _garante(resp2.status_code == 200, "segunda chamada falhou")
        _garante(os.path.getmtime(cache.path) == mtime, "cache foi reescrito na segunda chamada")
        arquivos_depois = sorted(
            glob.glob(os.path.join(UPLOADS, og_ops.FIGURINO_THUMBS_SUBFOLDER, "320", "*"))
        )
        _garante(arquivos_antes == arquivos_depois, "a segunda chamada criou arquivo novo")


def c02_documento_sem_variante():
    with app.test_client() as client:
        _login(client)
        resp = client.get(f"/uploads/t/320/talent_docs/{estado['doc_nome']}")
        _garante(resp.status_code == 404, f"talent_docs ganhou variante: {resp.status_code}")
        _garante(
            not os.path.isdir(os.path.join(UPLOADS, "talent_docs_thumbs")),
            "criou pasta de cache para documento",
        )


def c03_largura_fora_da_allowlist():
    pasta = os.path.join(UPLOADS, og_ops.FIGURINO_THUMBS_SUBFOLDER, "999")
    with app.test_client() as client:
        _login(client)
        resp = client.get(f"/uploads/t/999/{og_ops.FIGURINO_MEDIA_SUBFOLDER}/{estado['fig_nome']}")
        _garante(resp.status_code == 404, f"largura 999 devolveu {resp.status_code}")
        _garante(not os.path.isdir(pasta), "gerou pasta de cache para largura proibida")


def c04_cache_longo_so_onde_deve():
    with app.test_client() as client:
        _login(client)
        fig = client.get(f"/uploads/{og_ops.FIGURINO_MEDIA_SUBFOLDER}/{estado['fig_nome']}")
        _garante(fig.status_code == 200, f"foto de figurino devolveu {fig.status_code}")
        _garante(
            "immutable" in fig.headers.get("Cache-Control", ""),
            "figurino_photos continua sem cache longo",
        )
        contrato = client.get(f"/uploads/contracts/{estado['contrato_nome']}")
        _garante(contrato.status_code == 200, f"contrato devolveu {contrato.status_code}")
        _garante(
            "immutable" not in contrato.headers.get("Cache-Control", ""),
            "o cache longo VAZOU para contracts (lá o arquivo pode ser regravado no mesmo caminho)",
        )


def c05_portal_serve_o_original():
    from app.talent_portal.portal_ops import portal_photo_url

    url_publica = f"/uploads/{og_ops.TALENT_MEDIA_SUBFOLDER}/{estado['rosto_nome']}"
    reescrita = portal_photo_url(url_publica)
    _garante(reescrita.startswith("/portal/photo/"), f"portal não reescreveu: {reescrita}")
    _garante(
        og_ops.pastas_da_variante(reescrita, UPLOADS) is None,
        "a URL do portal casou com a regra de variante — pediria uma URL que o Flask 404",
    )
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["talent_id"] = estado["talento_id"]
        resp = client.get(reescrita)
        _garante(resp.status_code == 200, f"portal devolveu {resp.status_code}")
        _garante(
            "immutable" in resp.headers.get("Cache-Control", ""),
            "a rota do portal continua sem cache — revalida toda foto a cada visita no celular",
        )


def c06_ts_e_py_concordam():
    """O comentário do `client.ts` promete que os dois lados concordam; aqui a promessa é medida."""
    fonte = (REPO_ROOT / "frontend/packages/api-client/src/client.ts").read_text(encoding="utf-8")

    m = re.search(r"const VARIANTE_UPLOADS = /\^\\/uploads\\/\(([^)]+)\)", fonte)
    _garante(m is not None, "não achei VARIANTE_UPLOADS no client.ts")
    subpastas_ts = set(m.group(1).split("|"))
    _garante(
        subpastas_ts == set(og_ops.SUBPASTAS_COM_VARIANTE),
        f"TS tem {sorted(subpastas_ts)} e Python tem {sorted(og_ops.SUBPASTAS_COM_VARIANTE)}",
    )

    m = re.search(r"export type LarguraMiniatura = ([^;]+);", fonte)
    _garante(m is not None, "não achei LarguraMiniatura no client.ts")
    larguras_ts = {int(x.strip()) for x in m.group(1).split("|")}
    _garante(
        larguras_ts == set(og_ops.LARGURAS_PERMITIDAS),
        f"TS tem {sorted(larguras_ts)} e Python tem {sorted(og_ops.LARGURAS_PERMITIDAS)}",
    )

    _garante(
        "/catalogo/midia/" in fonte and og_ops.PREFIXOS_COM_VARIANTE[0] == "/catalogo/midia/",
        "prefixo do catálogo divergiu",
    )


def c07_rotacao_grava_caminho_novo():
    from app.figurino.figurino_ops import rotate_figurino_photo

    ficha = FigurinoSheet.query.get(estado["ficha_id"])
    antiga = ficha.photo_filename
    caminho_antigo = os.path.join(UPLOADS, antiga[len("/uploads/"):])

    # Gera a variante ANTES de girar: é ela que precisa sumir.
    with app.test_client() as client:
        _login(client)
        client.get(f"/uploads/t/320/{og_ops.FIGURINO_MEDIA_SUBFOLDER}/{estado['fig_nome']}")
    _garante(og_ops.variante_em_cache(antiga, 320, UPLOADS) is not None, "variante não foi gerada")

    erro = rotate_figurino_photo(ficha, direction="cw")
    db.session.commit()
    _garante(erro is None, f"rotação falhou: {erro}")
    _garante(ficha.photo_filename != antiga, "a rotação regravou no MESMO caminho")
    novo = os.path.join(UPLOADS, ficha.photo_filename[len("/uploads/"):])
    estado.setdefault("arquivos", []).append(novo)
    estado.setdefault("urls_para_invalidar", []).append(ficha.photo_filename)
    _garante(os.path.exists(novo), "arquivo novo não foi gravado")
    _garante(not os.path.exists(caminho_antigo), "arquivo antigo continua no disco")
    _garante(
        og_ops.variante_em_cache(antiga, 320, UPLOADS) is None,
        "a variante antiga sobreviveu — seria servida na orientação errada por um ano",
    )
    # 1000x1300 (retrato) girado vira 1300x1000 (paisagem) e cai para 1200x923 no teto de
    # `MAX_PX` — a rotação agora respeita o mesmo 1200px/q85 do resto do sistema, em vez do
    # `quality=92, subsampling=0` que fazia o arquivo CRESCER a cada giro.
    girada = Image.open(novo)
    _garante(girada.width > girada.height, f"não girou: {girada.size}")
    _garante(max(girada.size) <= 1200, f"rotação ignorou o teto de 1200px: {girada.size}")
    _garante(
        os.path.getsize(novo) < len(estado["fig_bytes"]),
        "a foto girada ficou MAIOR que a original",
    )


def c08_heic_vira_jpg():
    from app.talent_portal.portal_ops import update_photo
    from werkzeug.datastructures import FileStorage

    talento = Talent.query.get(estado["talento_id"])
    heic = _imagem(2400, 1800, formato="HEIF")
    with app.test_request_context():
        update_photo(
            talento,
            "full",
            FileStorage(stream=io.BytesIO(heic), filename="IMG_0042.HEIC"),
        )
    db.session.commit()
    caminho = os.path.join(UPLOADS, talento.photo_full_path[len("/uploads/"):])
    estado.setdefault("arquivos", []).append(caminho)
    _garante(
        talento.photo_full_path.endswith(".jpg"),
        f"HEIC ficou como {talento.photo_full_path} — o navegador não abre isso",
    )
    img = Image.open(caminho)
    _garante(img.format == "JPEG", f"formato gravado: {img.format}")
    _garante(max(img.size) <= 1200, f"não reduziu: {img.size}")


def c09_heic_ilegivel_recusa_e_nao_grava():
    from app.talent_portal.portal_ops import PortalUploadError, update_photo
    from werkzeug.datastructures import FileStorage

    talento = Talent.query.get(estado["talento_id"])
    antes = talento.photo_face_path
    quantos = len(os.listdir(os.path.join(UPLOADS, og_ops.TALENT_MEDIA_SUBFOLDER)))
    with app.test_request_context():
        try:
            update_photo(
                talento,
                "face",
                FileStorage(stream=io.BytesIO(b"isto nao e uma imagem"), filename="foto.heic"),
            )
            raise AssertionError("aceitou um HEIC ilegível — gravaria um arquivo invisível")
        except PortalUploadError as exc:
            _garante("Não conseguimos ler" in str(exc), f"mensagem pouco clara: {exc}")
    _garante(talento.photo_face_path == antes, "trocou o caminho mesmo recusando")
    depois = len(os.listdir(os.path.join(UPLOADS, og_ops.TALENT_MEDIA_SUBFOLDER)))
    _garante(depois == quantos, "gravou arquivo mesmo recusando")


def c10_pdf_e_xml_intactos():
    from app.storage import save_file
    from werkzeug.datastructures import FileStorage

    for nome, dados in (
        ("nota.pdf", b"%PDF-1.7\n" + bytes(range(256)) * 8),
        ("nfe.xml", b"<?xml version='1.0'?><nfeProc>" + b"a" * 500 + b"</nfeProc>"),
    ):
        with app.test_request_context():
            url = save_file(FileStorage(stream=io.BytesIO(dados), filename=nome), "invoices")
        caminho = os.path.join(UPLOADS, url[len("/uploads/"):])
        estado.setdefault("arquivos", []).append(caminho)
        with open(caminho, "rb") as fh:
            gravado = fh.read()
        _garante(gravado == dados, f"{nome} foi alterado ao atravessar save_file")


def c11_homonimos_nao_se_sobrescrevem():
    from app.calendar.routes import _save_file_upload
    from werkzeug.datastructures import FileStorage

    caminhos = []
    for conteudo in (b"%PDF-1.5 primeiro", b"%PDF-1.5 segundo"):
        with app.test_request_context():
            url = _save_file_upload(
                FileStorage(stream=io.BytesIO(conteudo), filename="contrato.pdf"),
                os.path.join(UPLOADS, "contracts"),
                "contracts",
            )
        _garante(url is not None, "upload recusado")
        caminho = os.path.join(UPLOADS, url[len("/uploads/"):])
        estado.setdefault("arquivos", []).append(caminho)
        caminhos.append(caminho)
    _garante(caminhos[0] != caminhos[1], "dois 'contrato.pdf' foram para o MESMO arquivo")
    with open(caminhos[0], "rb") as fh:
        _garante(fh.read() == b"%PDF-1.5 primeiro", "o primeiro contrato foi sobrescrito")


def c12_comprovante_de_gasto():
    from app.gastos.gastos_ops import RECEIPT_MAX_BYTES, save_receipt
    from werkzeug.datastructures import FileStorage

    with app.test_request_context():
        grande = save_receipt(
            FileStorage(
                stream=io.BytesIO(b"%PDF-1.5" + b"x" * (RECEIPT_MAX_BYTES + 1)),
                filename="grande.pdf",
            ),
            os.path.join(UPLOADS, "expenses"),
        )
    _garante(grande is None, "aceitou comprovante acima do teto")

    with app.test_request_context():
        ok = save_receipt(
            FileStorage(stream=io.BytesIO(_imagem(2000, 1500)), filename="comprovante.jpg"),
            os.path.join(UPLOADS, "expenses"),
        )
    _garante(ok is not None, "recusou um comprovante válido")
    _garante(
        ok.startswith("expenses/") and not ok.startswith("/uploads/"),
        f"formato do caminho mudou ({ok}) — `_can_read_expense_receipt` compara string exata",
    )
    caminho = os.path.join(UPLOADS, ok)
    estado.setdefault("arquivos", []).append(caminho)
    _garante(max(Image.open(caminho).size) <= 1200, "o comprovante não foi comprimido")


def c13_classificacao_dos_motivos():
    from app.talents import midia_ops

    with app.test_request_context():
        pdf_disfarcado = f"{PREFIX}disfarce.jpg"
        # HEIC de iPhone gravado com nome `.jpg`: o Pillow abre, o navegador NÃO. Conferir só
        # "o Pillow consegue abrir?" deixaria este caso passar como íntegro — e ele some da tela
        # do mesmo jeito. Cinco deles estavam em produção, invisíveis ao classificador antigo.
        heic_disfarcado = f"{PREFIX}heic_disfarce.jpg"
        _grava(og_ops.TALENT_MEDIA_SUBFOLDER, pdf_disfarcado, b"%PDF-1.5\n" + b"z" * 500)
        _grava(og_ops.TALENT_MEDIA_SUBFOLDER, heic_disfarcado, _imagem(300, 300, formato="HEIF"))
        casos = {
            None: midia_ops.MOTIVO_VAZIO,
            "": midia_ops.MOTIVO_VAZIO,
            "https://lh3.googleusercontent.com/d/abc": midia_ops.MOTIVO_EXTERNO,
            f"/uploads/{og_ops.TALENT_MEDIA_SUBFOLDER}/{PREFIX}nao_existe.jpg": (
                midia_ops.MOTIVO_SUMIU
            ),
            f"/uploads/{og_ops.TALENT_MEDIA_SUBFOLDER}/{pdf_disfarcado}": (
                midia_ops.MOTIVO_NAO_E_IMAGEM
            ),
            f"/uploads/{og_ops.TALENT_MEDIA_SUBFOLDER}/{heic_disfarcado}": (
                midia_ops.MOTIVO_FORMATO_OCULTO
            ),
            f"/uploads/{og_ops.TALENT_MEDIA_SUBFOLDER}/{estado['rosto_nome']}": (
                midia_ops.MOTIVO_OK
            ),
        }
        for url, esperado in casos.items():
            obtido = midia_ops.classificar(url)
            _garante(obtido == esperado, f"{url!r}: esperava {esperado!r}, veio {obtido!r}")

        talento = Talent.query.get(estado["talento_id"])
        talento.photo_face_path = f"/uploads/{og_ops.TALENT_MEDIA_SUBFOLDER}/{PREFIX}sumida.jpg"
        faltas = midia_ops.faltas_do_talento(talento)
        _garante(faltas == ["foto de rosto"], f"faltas erradas: {faltas}")


def main() -> int:
    print("\nVerificação da feature 292 — fotos que somem\n")
    with app.app_context():
        try:
            preparar()
            cenario("01 variante de figurino (320px, immutable, cache)", c01_variante_figurino)
            cenario("02 talent_docs continua sem variante (PII)", c02_documento_sem_variante)
            cenario("03 largura fora da allowlist não gera nada", c03_largura_fora_da_allowlist)
            cenario("04 cache longo só nas fotos operacionais", c04_cache_longo_so_onde_deve)
            cenario("05 portal serve o original, agora com cache", c05_portal_serve_o_original)
            cenario("06 client.ts e og_ops.py concordam", c06_ts_e_py_concordam)
            cenario("07 rotação grava caminho novo e invalida cache", c07_rotacao_grava_caminho_novo)
            cenario("08 HEIC do iPhone vira .jpg de 1200px", c08_heic_vira_jpg)
            cenario("09 HEIC ilegível recusa e não grava", c09_heic_ilegivel_recusa_e_nao_grava)
            cenario("10 PDF e XML atravessam intactos", c10_pdf_e_xml_intactos)
            cenario("11 homônimos não se sobrescrevem", c11_homonimos_nao_se_sobrescrevem)
            cenario("12 comprovante de gasto: teto e formato do caminho", c12_comprovante_de_gasto)
            cenario("13 classificação dos motivos", c13_classificacao_dos_motivos)
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
