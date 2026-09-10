"""Verificação da feature 297 — vídeo leve com moldura, menu na tag NFC e recado da cliente.

Cenários:
  1. Vídeo 4K vertical enviado → o arquivo ENTREGUE sai com 1080 de largura e pesa uma fração
     do que subiu.
  2. O arquivo entregue é vídeo válido e a rota pública o serve com `206` e `video/mp4`.
  3. Envio COM moldura → os pixels da borda mudam e o miolo do vídeo continua o mesmo.
  4. Envio SEM moldura → nasce só um arquivo, sem moldura gravada.
  5. Resolução pública traz Spotify, Instagram e vídeo de abertura, e só mostra a mensagem
     especial quando a entrega está pronta.
  6. Recado enviado pela rota pública grava tag + cliente (conferido por CONEXÃO SEPARADA) e
     dispara a notificação do sino.
  7. Recado vazio e recado acima do limite são RECUSADOS pelo servidor e nada é gravado.
  8. Ler recados sem sessão e com papel sem permissão devolve 401/403.
  9. A listagem do ERP devolve estado do processamento, peso e duração.
 10. Código inexistente, tag desativada e tag sem vídeo devolvem payloads IDÊNTICOS no que
     revela existência.
 11. Entrega em processamento não aparece para a cliente, e a mídia dela responde 404.
 12. Vídeo horizontal enviado por engano é aceito e a moldura se adapta à tela real dele.
 13. Enviar um segundo vídeo enquanto o primeiro está na fila é RECUSADO (corrida do worker).
 14. Cadastrar o vídeo de abertura converte, entra no payload público e some ao remover.
 15. O 11º recado da mesma origem é barrado com `429` **no envelope JSON** da casa.
 16. Sem moldura cadastrada, o vídeo é entregue sem moldura, com o motivo à vista.
 17. Reprocessar parte do mestre, tira a moldura, e enfileirar duas vezes é recusado com `409`.
 18. Com uma entrega em `processando`, ninguém mais reivindica — no máximo UMA conversão na
     plataforma inteira, em qualquer instante.
 19. Limpeza.

Os cenários 7, 8, 13, 15 e 17 DEVEM ser recusados pelo servidor — se passarem, o defeito é do verify.

DUAS ARMADILHAS DA CASA, respeitadas aqui de propósito:
  * Toda asserção de escrita confere por **conexão separada** (lição do hotfix 257): o autoflush
    da própria sessão esconde ausência de commit.
  * As requisições HTTP acontecem **FORA** de `app.app_context()`. Com um contexto de aplicação
    aberto por cima, o Flask reaproveita o mesmo `g` em todas as requisições, o usuário logado num
    cenário sobrevive no seguinte, e um teste de "sem sessão" responde 200 alegremente. Por isso
    cada bloco de banco abre o seu próprio contexto curto, e nada de HTTP acontece dentro dele.

A conversão roda numa thread de fundo em produção. Aqui ela é chamada à mão
(`nfc_ops.processar_proxima()`), porque `MANTO_SEM_THREADS=1` desliga as threads — é o que permite
verificar o resultado de forma determinística, sem dormir esperando.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"; $env:MANTO_SEM_THREADS = "1"
    .venv/Scripts/python.exe specs/297-nfc-moldura-e-menu/verify_297.py
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
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

from PIL import Image  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db, limiter  # noqa: E402
from app.constants import (  # noqa: E402
    MANTO_INSTAGRAM_URL,
    MANTO_SPOTIFY_URL,
    NFC_MENSAGEM_MAX_CHARS,
    RoleName,
)
from app.impressoes3d import nfc_ops, video_ops  # noqa: E402
from app.models import (  # noqa: E402
    Acervo3DItem,
    Client,
    NfcTag,
    NfcTagDelivery,
    NfcTagMessage,
    Notification,
    Role,
    SiteSetting,
    User,
)

PREFIX = "__v297_"
SENHA = "verify-297-senha"
MOLDURA_ORIGEM = Path.home() / "Desktop" / "MolduraLuminaria.png"

app = create_app()
app.config["TESTING"] = True
# O limitador se desliga pelo OBJETO, não pela config: o flask-limiter lê `RATELIMIT_ENABLED` uma
# única vez, no `init_app`, e mexer no `app.config` depois disso não tem efeito nenhum. Enquanto
# isso passou despercebido, o verify vinha passando por pouco — o login é 10/minuto e uma rodada
# mais longa estourava o limite, falhando por motivo que não tem nada a ver com a feature.
limiter.enabled = False

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}

_engine_externo = create_engine(os.environ["DATABASE_URL"], future=True)
_temporarios: list[Path] = []


def _no_banco(sql: str, **params):
    """Lê pelo banco, por fora da sessão do app (o autoflush esconde falta de commit)."""
    with _engine_externo.connect() as conn:
        return conn.execute(text(sql), params).fetchone()


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


def _usuario(sufixo: str, papel: str) -> str:
    """Cria (ou redefine) um usuário descartável e devolve o e-mail dele."""
    email = f"{PREFIX}{sufixo}@manto.local"
    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(name=f"{PREFIX}{sufixo}", email=email, is_active=True, has_access=True)
        db.session.add(user)
    user.set_password(SENHA)
    user.roles.clear()
    user.roles.append(Role.query.filter_by(name=papel).one())
    db.session.commit()
    return email


def _login(c, email: str) -> None:
    r = c.post("/api/auth/login", json={"email": email, "password": SENHA})
    _garante(r.status_code == 200, f"login {email} → {r.status_code}")


# ── Fixtures de vídeo ────────────────────────────────────────────────────────

def _gerar_video(destino: Path, largura: int, altura: int, segundos: int = 3) -> Path:
    """Gera um vídeo sintético com áudio, no encoder que ESTA máquina tem.

    O ffmpeg local é LGPL e não tem `libx264` — só `libopenh264` (pegadinha da 265). Pedir
    `libx264` aqui faria o verify falhar por motivo errado.
    """
    if destino.exists():
        return destino
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", f"testsrc2=size={largura}x{altura}:rate=24:duration={segundos}",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={segundos}",
            "-c:v", video_ops.encoder_disponivel(), "-b:v", "12M", "-pix_fmt", "yuv420p",
            "-c:a", "aac", str(destino),
        ],
        check=True, capture_output=True,
    )
    _temporarios.append(destino)
    return destino


def _pasta_temp() -> Path:
    pasta = Path(app.instance_path) / "verify_297_tmp"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _enviar(c, tag_id: int, arquivo: Path, *, com_moldura: bool, titulo: str = ""):
    """Faz o upload multipart como a tela faz. Devolve a resposta crua (o chamador decide)."""
    dados = {
        "file": (io.BytesIO(arquivo.read_bytes()), arquivo.name),
        "kind": "video",
        "com_moldura": "true" if com_moldura else "false",
    }
    if titulo:
        dados["title"] = titulo
    return c.post(
        f"/api/3d/nfc/{tag_id}/entregas", data=dados, content_type="multipart/form-data"
    )


def _enviar_ok(tag_id: int, arquivo: Path, *, com_moldura: bool, titulo: str = "") -> None:
    """Upload que DEVE dar certo, fora de qualquer contexto de aplicação."""
    with app.test_client() as c:
        _login(c, estado["artista"])
        r = _enviar(c, tag_id, arquivo, com_moldura=com_moldura, titulo=titulo)
    _garante(
        r.status_code in (200, 201),
        f"upload → {r.status_code}: {r.get_data(as_text=True)[:200]}",
    )


def _processar_um() -> int:
    """Converte a próxima entrega da fila e devolve o id dela."""
    with app.app_context():
        entregue = nfc_ops.processar_proxima()
        _garante(entregue is not None, "a fila não devolveu nenhuma entrega")
        return entregue.id


def _quadro(caminho: str, segundo: float, destino: Path) -> Image.Image:
    """Extrai um quadro do vídeo para comparar pixels."""
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", str(segundo), "-i", caminho,
         "-frames:v", "1", str(destino)],
        check=True, capture_output=True,
    )
    _temporarios.append(destino)
    return Image.open(destino).convert("RGB")


def _diferenca(a, b) -> int:
    """Distância entre dois pixels RGB, somando canal a canal."""
    return sum(abs(x - y) for x, y in zip(a, b, strict=True))


def _caminhos_da_entrega(delivery_id: int) -> tuple[str, str | None]:
    """(arquivo entregue, arquivo mestre) — caminhos absolutos."""
    with app.app_context():
        d = db.session.get(NfcTagDelivery, delivery_id)
        entregue = os.path.join(app.config["NFC_MEDIA_FOLDER"], d.file_path)
        mestre = (
            os.path.join(app.config["NFC_MESTRES_FOLDER"], d.master_file_path)
            if d.master_file_path
            else None
        )
        return entregue, mestre


# ── Preparação ───────────────────────────────────────────────────────────────

def preparar() -> None:
    estado["artista"] = _usuario("artista", RoleName.ARTISTA_3D)
    estado["casting"] = _usuario("casting", RoleName.CASTING)

    item = Acervo3DItem.query.filter_by(name=f"{PREFIX}luminaria").first()
    if item is None:
        item = Acervo3DItem(name=f"{PREFIX}luminaria", photo_url="/uploads/x.png")
        if hasattr(item, "nfc_prefix"):
            item.nfc_prefix = "V297"
        db.session.add(item)
        db.session.commit()

    cliente = Client.query.filter_by(name=f"{PREFIX}cliente").first()
    if cliente is None:
        # `phone` é NOT NULL em `clients`; um número descartável fora de qualquer faixa real.
        cliente = Client(name=f"{PREFIX}cliente", phone="+5511900000297")
        db.session.add(cliente)
        db.session.commit()
    estado["cliente_id"] = cliente.id

    tags = nfc_ops.create_tags(item, 3)
    db.session.commit()
    tags[0].client_id = cliente.id
    tags[2].is_active = False
    db.session.commit()
    estado["tag_video_id"], estado["tag_video_code"] = tags[0].id, tags[0].code
    estado["tag_sem_video_id"], estado["tag_sem_video_code"] = tags[1].id, tags[1].code
    estado["tag_inativa_code"] = tags[2].code

    # A moldura do sistema: a de verdade, se estiver no Desktop; senão uma sintética equivalente.
    settings = SiteSetting.query.get(1)
    estado["moldura_anterior"] = settings.nfc_frame_path
    estado["abertura_anterior"] = settings.nfc_intro_video_path
    destino = Path(app.config["NFC_SISTEMA_FOLDER"]) / "moldura.png"
    estado["moldura_existia"] = destino.exists()
    if MOLDURA_ORIGEM.exists():
        destino.write_bytes(MOLDURA_ORIGEM.read_bytes())
    else:
        moldura = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        px = moldura.load()
        for x in range(1080):
            for y in range(1920):
                if x < 80 or x >= 1000 or y < 80 or y >= 1840:
                    px[x, y] = (212, 175, 55, 240)
        moldura.save(destino)
    settings.nfc_frame_path = destino.name
    db.session.commit()

    pasta = _pasta_temp()
    estado["video_4k"] = _gerar_video(pasta / f"{PREFIX}4k.mp4", 2160, 3840)
    estado["video_deitado"] = _gerar_video(pasta / f"{PREFIX}deitado.mp4", 1920, 1080)


# ── Cenários ─────────────────────────────────────────────────────────────────

def cen_01_converte_e_encolhe() -> None:
    _enviar_ok(estado["tag_video_id"], estado["video_4k"], com_moldura=True, titulo=f"{PREFIX}t")
    estado["delivery_com_moldura"] = _processar_um()

    linha = _no_banco(
        "SELECT width, height, file_size_bytes, processing_status, has_frame, master_file_path"
        " FROM nfc_tag_deliveries WHERE id = :i", i=estado["delivery_com_moldura"],
    )
    _garante(linha is not None, "a entrega não foi comitada")
    largura, altura, tamanho, status, tem_moldura, mestre = linha
    _garante(largura == 1080, f"largura entregue = {largura}, esperado 1080")
    _garante(altura == 1920, f"altura entregue = {altura}, esperado 1920")
    _garante(status == "pronto", f"status = {status}")
    _garante(bool(tem_moldura) is True, "has_frame deveria ser verdadeiro")
    _garante(bool(mestre), "o mestre sem moldura não foi guardado")
    origem = estado["video_4k"].stat().st_size
    _garante(tamanho < origem / 2, f"entregue {tamanho} não é fração de {origem}")


def cen_02_serve_com_range() -> None:
    entregue, _ = _caminhos_da_entrega(estado["delivery_com_moldura"])
    info = video_ops.sondar(entregue)
    _garante(info.largura == 1080 and info.em_pe, f"o arquivo entregue não é vertical 1080: {info}")
    url = (
        f"/api/nfc/{estado['tag_video_code']}"
        f"/entregas/{estado['delivery_com_moldura']}/media"
    )
    with app.test_client() as c:
        r = c.get(url, headers={"Range": "bytes=0-63"})
    _garante(r.status_code == 206, f"Range → {r.status_code}, esperado 206")
    _garante(r.mimetype == "video/mp4", f"mimetype = {r.mimetype}")
    corpo = r.get_data()
    _garante(len(corpo) == 64, f"o Range devolveu {len(corpo)} bytes")
    _garante(corpo[4:8] == b"ftyp", "os primeiros bytes não são de um MP4")


def cen_03_moldura_muda_a_borda() -> None:
    entregue, mestre = _caminhos_da_entrega(estado["delivery_com_moldura"])
    _garante(mestre is not None, "não há mestre para comparar")
    pasta = _pasta_temp()
    q_com = _quadro(entregue, 1.5, pasta / f"{PREFIX}q_com.png")
    q_sem = _quadro(mestre, 1.5, pasta / f"{PREFIX}q_mestre.png")
    canto = _diferenca(q_com.getpixel((30, 30)), q_sem.getpixel((30, 30)))
    meio = _diferenca(q_com.getpixel((540, 960)), q_sem.getpixel((540, 960)))
    _garante(canto > 60, f"a moldura não mudou a borda (diferença {canto})")
    _garante(meio < 60, f"a moldura invadiu o miolo (diferença {meio})")


def cen_04_sem_moldura() -> None:
    _enviar_ok(estado["tag_video_id"], estado["video_4k"], com_moldura=False)
    estado["delivery_sem_moldura"] = _processar_um()
    linha = _no_banco(
        "SELECT has_frame, master_file_path, file_path FROM nfc_tag_deliveries WHERE id = :i",
        i=estado["delivery_sem_moldura"],
    )
    tem_moldura, mestre, entregue_nome = linha
    _garante(bool(tem_moldura) is False, "has_frame deveria ser falso")
    _garante(
        mestre in (None, entregue_nome),
        "sem moldura não deveria gerar um segundo arquivo no disco",
    )


def cen_05_payload_publico_do_menu() -> None:
    with app.test_client() as c:
        r = c.get(f"/api/nfc/{estado['tag_video_code']}")
    _garante(r.status_code == 200, f"resolve → {r.status_code}")
    dados = r.get_json()
    _garante(dados.get("spotify_url") == MANTO_SPOTIFY_URL, "spotify_url ausente ou errado")
    _garante(dados.get("instagram_url") == MANTO_INSTAGRAM_URL, "instagram_url ausente")
    _garante("intro_video_url" in dados, "intro_video_url ausente do payload")
    _garante(dados.get("aceita_recado") is True, "aceita_recado ausente do payload")
    _garante(len(dados.get("deliveries") or []) == 1, "a entrega pronta não apareceu")
    entrega = dados["deliveries"][0]
    _garante(entrega.get("width") == 1080, "o payload não traz a largura do vídeo")
    _garante(entrega.get("height") == 1920, "o payload não traz a altura do vídeo")


def cen_06_recado_grava_e_notifica() -> None:
    with app.app_context():
        antes = Notification.query.count()
    with app.test_client() as c:
        r = c.post(
            f"/api/nfc/{estado['tag_video_code']}/recados",
            json={"message": f"{PREFIX}que presente lindo", "author_name": f"{PREFIX}Ana"},
        )
    _garante(r.status_code in (200, 201), f"recado → {r.status_code}")
    linha = _no_banco(
        "SELECT tag_id, client_id, author_name, read_at FROM nfc_tag_messages"
        " WHERE message = :m", m=f"{PREFIX}que presente lindo",
    )
    _garante(linha is not None, "o recado não foi comitado (conexão separada não o vê)")
    tag_id, client_id, autor, lido = linha
    _garante(tag_id == estado["tag_video_id"], "o recado não ficou ligado à tag")
    _garante(client_id == estado["cliente_id"], "o recado não copiou a cliente da tag")
    _garante(autor == f"{PREFIX}Ana", "o nome de quem escreveu não foi gravado")
    _garante(lido is None, "o recado nasceu marcado como lido")
    with app.app_context():
        _garante(Notification.query.count() > antes, "o sino não recebeu notificação do recado")


def cen_07_recado_invalido_e_recusado() -> None:
    code = estado["tag_video_code"]
    with app.test_client() as c:
        vazio = c.post(f"/api/nfc/{code}/recados", json={"message": "   "})
        gigante = c.post(
            f"/api/nfc/{code}/recados",
            json={"message": "x" * (NFC_MENSAGEM_MAX_CHARS + 1)},
        )
    _garante(vazio.status_code == 400, f"recado vazio → {vazio.status_code}, esperado 400")
    _garante(gigante.status_code == 400, f"recado gigante → {gigante.status_code}, esperado 400")
    campos = (vazio.get_json() or {}).get("error", {}).get("fields") or {}
    _garante("message" in campos, "o 400 não aponta o campo `message`")
    sobrou = _no_banco("SELECT count(*) FROM nfc_tag_messages WHERE message LIKE :p", p="xxx%")
    _garante(sobrou[0] == 0, "um recado inválido foi gravado assim mesmo")


def cen_08_recados_exigem_papel() -> None:
    tag_id = estado["tag_video_id"]
    with app.test_client() as c:
        sem_sessao = c.get(f"/api/3d/nfc/{tag_id}/recados")
    _garante(sem_sessao.status_code == 401, f"sem sessão → {sem_sessao.status_code}, esperado 401")

    with app.test_client() as c:
        _login(c, estado["casting"])
        sem_papel = c.get(f"/api/3d/nfc/{tag_id}/recados")
    _garante(
        sem_papel.status_code in (403, 404),
        f"papel sem permissão → {sem_papel.status_code}, esperado 403/404",
    )

    with app.test_client() as c:
        _login(c, estado["artista"])
        ok = c.get(f"/api/3d/nfc/{tag_id}/recados")
    _garante(ok.status_code == 200, f"artista 3D → {ok.status_code}")
    _garante(len(ok.get_json().get("items") or []) >= 1, "a lista de recados veio vazia")


def cen_09_listagem_do_erp_mostra_estado() -> None:
    with app.test_client() as c:
        _login(c, estado["artista"])
        r = c.get("/api/3d/nfc")
    _garante(r.status_code == 200, f"lista → {r.status_code}")
    tags = r.get_json().get("tags")
    alvo = next((t for t in tags if t["id"] == estado["tag_video_id"]), None)
    _garante(alvo is not None, "a tag do teste sumiu da lista")
    entrega = alvo.get("video_delivery")
    _garante(entrega is not None, "a lista não traz a entrega")
    for campo in ("processing_status", "file_size_bytes", "duration_seconds", "has_frame",
                  "width", "height"):
        _garante(campo in entrega, f"a listagem não devolve `{campo}`")
    _garante(alvo.get("messages_unread") is not None, "a listagem não traz a contagem de recados")
    _garante(alvo["messages_count"] >= 1, "a contagem de recados não somou o recado do cenário 6")


def cen_10_respostas_publicas_identicas() -> None:
    with app.test_client() as c:
        inexistente = c.get("/api/nfc/01-NAOEXISTE").get_json()
        inativa = c.get(f"/api/nfc/{estado['tag_inativa_code']}").get_json()
        sem_video = c.get(f"/api/nfc/{estado['tag_sem_video_code']}").get_json()
    _garante(inexistente == inativa, "código inexistente e tag inativa devolvem coisas diferentes")
    _garante((sem_video.get("deliveries") or []) == [], "a tag sem vídeo devolveu entrega")
    # A peça pode diferir (a tag sem vídeo existe e tem produto); o que não pode diferir é o que
    # revela EXISTÊNCIA: a lista de entregas e os links do menu.
    for chave in ("deliveries", "spotify_url", "instagram_url", "intro_video_url"):
        _garante(
            inexistente.get(chave) == inativa.get(chave) == sem_video.get(chave),
            f"`{chave}` denuncia a diferença entre os três casos",
        )


def cen_11_em_processamento_nao_vaza() -> None:
    tag_id, code = estado["tag_sem_video_id"], estado["tag_sem_video_code"]
    _enviar_ok(tag_id, estado["video_4k"], com_moldura=True)
    with app.app_context():
        pendente = NfcTagDelivery.query.filter_by(tag_id=tag_id).first()
        _garante(pendente is not None, "a entrega pendente não existe")
        _garante(
            pendente.processing_status == "pendente",
            f"a entrega nasceu {pendente.processing_status}, esperado pendente",
        )
        estado["delivery_pendente"] = pendente.id

    with app.test_client() as c:
        publico = c.get(f"/api/nfc/{code}").get_json()
        midia = c.get(f"/api/nfc/{code}/entregas/{estado['delivery_pendente']}/media")
    _garante(
        (publico.get("deliveries") or []) == [],
        "a entrega em processamento apareceu para a cliente",
    )
    _garante(midia.status_code == 404, f"mídia não pronta → {midia.status_code}, esperado 404")


def cen_12_segundo_envio_na_fila_e_recusado() -> None:
    """A entrega do cenário 11 ainda está PENDENTE — enviar outra agora tem de ser recusado.

    Sem esta trava, substituir apagaria o arquivo e a linha que o worker tem na mão, e a conversão
    terminaria escrevendo para um registro que já não existe.
    """
    with app.test_client() as c:
        _login(c, estado["artista"])
        r = _enviar(c, estado["tag_sem_video_id"], estado["video_4k"], com_moldura=True)
    _garante(r.status_code == 400, f"segundo envio → {r.status_code}, esperado 400")
    campos = (r.get_json() or {}).get("error", {}).get("fields") or {}
    _garante("file" in campos, "o 400 da corrida não aponta o campo `file`")
    _processar_um()  # deixa a fila limpa para o próximo cenário


def cen_13_video_deitado_tambem_recebe_moldura() -> None:
    _enviar_ok(estado["tag_video_id"], estado["video_deitado"], com_moldura=True)
    delivery_id = _processar_um()
    estado["delivery_deitado"] = delivery_id
    entregue, _ = _caminhos_da_entrega(delivery_id)
    info = video_ops.sondar(entregue)
    _garante(info.largura == 1080, f"largura {info.largura}, esperado 1080")
    _garante(info.altura == 608, f"altura {info.altura}, esperado 608 (proporção preservada)")
    quadro = _quadro(entregue, 1.0, _pasta_temp() / f"{PREFIX}q_deitado.png")
    canto = quadro.getpixel((20, 20))
    # A moldura tem borda opaca no canto; o `testsrc2` sozinho nunca produz esse tom exato ali.
    _garante(sum(canto) > 200, f"o canto do vídeo deitado não recebeu moldura: {canto}")


def cen_14_abertura_do_sistema() -> None:
    """Cadastrar o vídeo de abertura converte, aparece no payload público e some ao remover.

    Este cenário nasceu de um defeito real: o temporário do upload e o do conversor tinham o mesmo
    nome (`<destino>.parcial`), então o ffmpeg lia e escrevia no mesmo arquivo e a rota respondia
    500. Só apareceu ao abrir a tela — o verify não tocava nesta rota.
    """
    arquivo = estado["video_deitado"]
    with app.test_client() as c:
        _login(c, estado["artista"])
        r = c.put(
            "/api/3d/nfc/abertura",
            data={"file": (io.BytesIO(arquivo.read_bytes()), "abertura.mp4")},
            content_type="multipart/form-data",
        )
    _garante(r.status_code == 200, f"PUT abertura → {r.status_code}: {r.get_data(as_text=True)[:200]}")
    _garante(r.get_json().get("abertura_url"), "a resposta não trouxe a URL da abertura")

    with app.app_context():
        caminho = nfc_ops.abertura_path()
        _garante(caminho is not None, "o arquivo da abertura não foi gravado")
        info = video_ops.sondar(caminho)
        _garante(info.largura <= 1080, f"a abertura não foi convertida: {info.largura} de largura")
        sobras = [
            n for n in os.listdir(app.config["NFC_SISTEMA_FOLDER"])
            if n.endswith((".parcial", ".entrada"))
        ]
        _garante(not sobras, f"sobraram temporários na pasta do sistema: {sobras}")

    with app.test_client() as c:
        publico = c.get(f"/api/nfc/{estado['tag_video_code']}").get_json()
        video = c.get("/api/nfc/abertura/video")
    _garante(publico.get("intro_video_url"), "intro_video_url continua nulo com abertura cadastrada")
    _garante(video.status_code == 200, f"vídeo de abertura → {video.status_code}")
    _garante(video.mimetype == "video/mp4", f"mimetype da abertura = {video.mimetype}")

    with app.test_client() as c:
        _login(c, estado["artista"])
        apagar = c.delete("/api/3d/nfc/abertura")
    _garante(apagar.status_code == 200, f"DELETE abertura → {apagar.status_code}")
    with app.test_client() as c:
        depois = c.get(f"/api/nfc/{estado['tag_video_code']}").get_json()
        sem_video = c.get("/api/nfc/abertura/video")
    _garante(depois.get("intro_video_url") is None, "intro_video_url sobreviveu à remoção")
    _garante(sem_video.status_code == 404, f"abertura removida → {sem_video.status_code}")


def cen_15_limite_de_taxa_em_json() -> None:
    """O 11º recado da mesma origem é barrado, e a recusa sai no envelope JSON da casa.

    Os outros cenários rodam com o limitador DESLIGADO (para poderem repetir envios); este liga de
    propósito. Sem o `errorhandler(429)` que a feature 297 criou, o flask-limiter responderia HTML
    cru e o `parseErrorBody` do `@manto/api-client` traduziria como "Ocorreu um erro inesperado" —
    exatamente o que acontecia nas treze rotas públicas com limite de taxa.
    """
    code = estado["tag_video_code"]
    limiter.enabled = True
    try:
        barrada = None
        with app.test_client() as c:
            for i in range(14):
                r = c.post(f"/api/nfc/{code}/recados", json={"message": f"{PREFIX}taxa {i}"})
                if r.status_code == 429:
                    barrada = r
                    break
        _garante(barrada is not None, "o limite de taxa não barrou nada em 14 envios seguidos")
        _garante(
            barrada.mimetype == "application/json",
            f"o 429 saiu como {barrada.mimetype}, não no envelope JSON",
        )
        corpo = barrada.get_json() or {}
        _garante("error" in corpo, "o 429 não veio no envelope `error` da casa")
        _garante(
            bool((corpo["error"].get("message") or "").strip()),
            "o 429 veio sem mensagem legível",
        )
    finally:
        limiter.enabled = False
        # A contagem fica na memória do processo: sem zerar, o login (10/minuto) dos cenários
        # seguintes seria barrado por causa deste teste.
        try:
            limiter.reset()
        except Exception:  # noqa: BLE001 — versões antigas não expõem reset; o desligar já basta
            pass


def cen_16_sem_moldura_cadastrada_entrega_assim_mesmo() -> None:
    """Sem moldura no sistema, o vídeo é entregue SEM moldura e o motivo fica à vista (FR-006).

    O que nunca pode acontecer é o vídeo da cliente se perder porque faltou um arquivo de
    configuração.
    """
    with app.app_context():
        settings = SiteSetting.query.get(1)
        guardado = settings.nfc_frame_path
        settings.nfc_frame_path = None
        db.session.commit()
    try:
        _enviar_ok(estado["tag_video_id"], estado["video_4k"], com_moldura=True)
        entregue_id = _processar_um()
    finally:
        with app.app_context():
            settings = SiteSetting.query.get(1)
            settings.nfc_frame_path = guardado
            db.session.commit()

    linha = _no_banco(
        "SELECT has_frame, processing_status, processing_error, file_path"
        " FROM nfc_tag_deliveries WHERE id = :i", i=entregue_id,
    )
    tem_moldura, status, erro, arquivo = linha
    _garante(bool(tem_moldura) is False, "marcou has_frame sem moldura cadastrada")
    _garante(status == "pronto", f"a entrega ficou em {status} em vez de pronto")
    _garante(bool(arquivo), "a entrega ficou sem arquivo — o vídeo da cliente se perdeu")
    _garante(erro and "moldura" in erro.lower(), f"o motivo não foi registrado: {erro!r}")


def cen_17_reprocessar_parte_do_mestre() -> None:
    """Reprocessar tira a moldura a partir do MESTRE, e enfileirar duas vezes é recusado (FR-007)."""
    tag_id = estado["tag_video_id"]
    with app.app_context():
        entrega = (
            NfcTagDelivery.query.filter_by(tag_id=tag_id)
            .order_by(NfcTagDelivery.id.desc()).first()
        )
        entrega_id = entrega.id
    # Garante uma entrega COM moldura e com mestre próprio antes de testar a volta.
    _enviar_ok(tag_id, estado["video_4k"], com_moldura=True)
    entrega_id = _processar_um()
    with app.app_context():
        antes = db.session.get(NfcTagDelivery, entrega_id)
        _garante(bool(antes.has_frame), "a entrega base deveria ter moldura")
        _garante(bool(antes.master_file_path), "a entrega base deveria ter mestre")

    with app.test_client() as c:
        _login(c, estado["artista"])
        primeira = c.post(
            f"/api/3d/nfc/{tag_id}/entregas/{entrega_id}/reprocessar",
            json={"com_moldura": False},
        )
        segunda = c.post(
            f"/api/3d/nfc/{tag_id}/entregas/{entrega_id}/reprocessar",
            json={"com_moldura": False},
        )
    _garante(primeira.status_code == 200, f"reprocessar → {primeira.status_code}")
    _garante(segunda.status_code == 409, f"segundo pedido → {segunda.status_code}, esperado 409")

    _processar_um()
    linha = _no_banco(
        "SELECT has_frame, processing_status, width FROM nfc_tag_deliveries WHERE id = :i",
        i=entrega_id,
    )
    tem_moldura, status, largura = linha
    _garante(bool(tem_moldura) is False, "o reprocessamento não tirou a moldura")
    _garante(status == "pronto", f"status após reprocessar = {status}")
    _garante(largura == 1080, f"o reprocessamento perdeu a normalização: {largura}")


def cen_18_so_uma_conversao_por_vez_na_plataforma() -> None:
    """Com uma entrega em `processando`, ninguém mais consegue reivindicar (incidente de 09/09).

    O claim garantia um dono por LINHA, mas não impedia duas conversões simultâneas em processos
    diferentes: o comando `flask nfc-reprocessar` convertia um vídeo enquanto um worker do gunicorn
    convertia outro, num contêiner de UMA CPU. O Render reiniciou o contêiner com o trabalho pela
    metade. A garantia agora é do banco, numa instrução só.
    """
    with app.app_context():
        # Duas entregas pendentes de mentira, sem arquivo: o que se testa aqui é o claim.
        a = NfcTagDelivery(tag_id=estado["tag_video_id"], kind="video",
                           processing_status="pendente", is_active=False)
        b = NfcTagDelivery(tag_id=estado["tag_video_id"], kind="video",
                           processing_status="pendente", is_active=False)
        db.session.add_all([a, b])
        db.session.commit()
        ids = [a.id, b.id]
    try:
        with app.app_context():
            primeira = nfc_ops.reivindicar_proxima_entrega()
            _garante(primeira is not None, "não conseguiu reivindicar a primeira entrega da fila")
            segunda = nfc_ops.reivindicar_proxima_entrega()
        _garante(
            segunda is None,
            "reivindicou uma SEGUNDA conversão com uma já em andamento — a trava não pegou",
        )
        com_processando = _no_banco(
            "SELECT count(*) FROM nfc_tag_deliveries WHERE processing_status = 'processando'"
        )
        _garante(
            com_processando[0] == 1,
            f"há {com_processando[0]} entregas em processando; o invariante é no máximo 1",
        )
    finally:
        with app.app_context():
            for i in ids:
                d = db.session.get(NfcTagDelivery, i)
                if d is not None:
                    db.session.delete(d)
            db.session.commit()


def limpar() -> None:
    db.session.rollback()
    settings = SiteSetting.query.get(1)
    settings.nfc_frame_path = estado.get("moldura_anterior")
    settings.nfc_intro_video_path = estado.get("abertura_anterior")
    db.session.commit()
    if not estado.get("moldura_existia", True):
        moldura = Path(app.config["NFC_SISTEMA_FOLDER"]) / "moldura.png"
        if moldura.exists():
            moldura.unlink()

    tags = (
        NfcTag.query.join(Acervo3DItem).filter(Acervo3DItem.name.like(f"{PREFIX}%")).all()
    )
    for tag in tags:
        NfcTagMessage.query.filter_by(tag_id=tag.id).delete(synchronize_session=False)
        for entrega in list(tag.deliveries):
            for pasta, nome in (
                (app.config["NFC_MEDIA_FOLDER"], entrega.file_path),
                (app.config["NFC_MESTRES_FOLDER"], entrega.master_file_path),
                (app.config["NFC_ENTRADA_FOLDER"], entrega.source_file_path),
            ):
                if nome:
                    caminho = os.path.join(pasta, nome)
                    if os.path.exists(caminho):
                        os.remove(caminho)
            db.session.delete(entrega)
        db.session.delete(tag)
    db.session.commit()

    Notification.query.filter(Notification.title.like(f"%{PREFIX}%")).delete(
        synchronize_session=False
    )
    Client.query.filter(Client.name.like(f"{PREFIX}%")).delete(synchronize_session=False)
    Acervo3DItem.query.filter(Acervo3DItem.name.like(f"{PREFIX}%")).delete(
        synchronize_session=False
    )
    for sufixo in ("artista", "casting"):
        user = User.query.filter_by(email=f"{PREFIX}{sufixo}@manto.local").first()
        if user:
            user.roles.clear()
            db.session.delete(user)
    db.session.commit()

    for caminho in _temporarios:
        try:
            if caminho.exists():
                caminho.unlink()
        except OSError:
            pass
    pasta = Path(app.instance_path) / "verify_297_tmp"
    if pasta.exists():
        for restante in pasta.iterdir():
            try:
                restante.unlink()
            except OSError:
                pass
        try:
            pasta.rmdir()
        except OSError:
            pass


def main() -> int:
    with app.app_context():
        _garante(
            app.config.get("MAIL_SUPPRESS_SEND") is True,
            "MAIL_SUPPRESS_SEND desligado — o script mandaria e-mail de verdade",
        )
        _garante(
            video_ops.ffmpeg_disponivel(),
            "sem ffmpeg nesta máquina — instale antes de rodar o verify",
        )
        preparar()

    # A partir daqui NÃO há contexto de aplicação aberto: as requisições HTTP precisam de um `g`
    # novo por requisição, ou o usuário logado num cenário sobrevive no seguinte.
    print("Feature 297 — moldura, menu e recado, contra manto_local")
    try:
        cenario("1. converte 4K e encolhe", cen_01_converte_e_encolhe)
        cenario("2. serve com Range e video/mp4", cen_02_serve_com_range)
        cenario("3. moldura muda a borda, não o miolo", cen_03_moldura_muda_a_borda)
        cenario("4. envio sem moldura", cen_04_sem_moldura)
        cenario("5. payload público do menu", cen_05_payload_publico_do_menu)
        cenario("6. recado grava e notifica", cen_06_recado_grava_e_notifica)
        cenario("7. recado inválido é RECUSADO", cen_07_recado_invalido_e_recusado)
        cenario("8. recados exigem papel", cen_08_recados_exigem_papel)
        cenario("9. listagem do ERP mostra estado", cen_09_listagem_do_erp_mostra_estado)
        cenario("10. respostas públicas idênticas", cen_10_respostas_publicas_identicas)
        cenario("11. em processamento não vaza", cen_11_em_processamento_nao_vaza)
        cenario("12. segundo envio na fila é RECUSADO", cen_12_segundo_envio_na_fila_e_recusado)
        cenario("13. vídeo deitado recebe moldura", cen_13_video_deitado_tambem_recebe_moldura)
        cenario("14. abertura do sistema converte e some ao remover", cen_14_abertura_do_sistema)
        cenario("15. limite de taxa devolve 429 em JSON", cen_15_limite_de_taxa_em_json)
        cenario("16. sem moldura cadastrada entrega assim mesmo", cen_16_sem_moldura_cadastrada_entrega_assim_mesmo)
        cenario("17. reprocessar parte do mestre", cen_17_reprocessar_parte_do_mestre)
        cenario("18. só uma conversão por vez na plataforma", cen_18_so_uma_conversao_por_vez_na_plataforma)
    finally:
        with app.app_context():
            cenario("19. limpeza", limpar)

    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"\n{ok}/{len(resultados)} OK")
    for nome, passou, erro in resultados:
        if not passou:
            print(f"  - {nome}: {erro}")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
