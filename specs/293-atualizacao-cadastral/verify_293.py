"""Verificação da feature 293 — campanha de reenvio dos arquivos perdidos.

Cenários:
 1. Dry-run classifica nos baldes certos (recebe / bounce permanente / já recebeu / sem e-mail)
    e **não envia nada**, nem grava token.
 2. `--enviar` manda para quem deve, e uma segunda rodada manda **zero** — o dedup mora no
    `AuditLog`, que sobrevive a redeploy (o controle anterior era um `.txt` numa máquina só).
 3. O corpo carrega o link do talento certo, com `?destino=/fotos-documentos`, e o host vem da
    config — nunca `localhost`, que foi o defeito que matou os e-mails do portal até 03/09.
 4. O token da campanha vale 7 dias, e o do autoatendimento continua valendo 1 hora.
 5. Devolução permanente **resolvida** volta a receber e-mail: o critério é o bounce em aberto
    contra o `email_contact` ATUAL, não o histórico.
 6. `faltas_do_talento` devolve só o que sumiu, com o rótulo que vai no corpo do e-mail.
 7. `portal_reset_url` recusa destino externo (`//evil.example`) — o link do e-mail não pode
    virar redirecionador aberto.
 8. Limpeza.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    $env:MAIL_SUPPRESS_SEND = "true"; $env:MANTO_SEM_THREADS = "1"
    .\\.venv\\Scripts\\python.exe specs\\293-atualizacao-cadastral\\verify_293.py
"""
from __future__ import annotations

import os
import sys
import traceback
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MAIL_SUPPRESS_SEND", "true")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from app import create_app, db  # noqa: E402
from app.models import AuditLog, EmailBounce, Talent  # noqa: E402

PREFIX = "__v293_"
ACAO = "campanha_fotos_292"

app = create_app()
app.config["TESTING"] = True
UPLOADS = app.config["UPLOAD_FOLDER"]

# O `_emails_enabled()` do projeto e o supressor do Flask-Mail leem a MESMA chave, e o Flask-Mail
# a captura no `init_app`. Então: o app nasce com a supressão ligada (nada sai de verdade) e aqui
# a chave é desligada só para o gate do projeto deixar a mensagem chegar ao `mail.send`, onde o
# `record_messages` a intercepta. A asserção abaixo é o que garante que isso não vira envio real.
assert app.extensions["mail"].suppress, (
    "Flask-Mail NÃO está suprimindo o envio: rode com MAIL_SUPPRESS_SEND=true. "
    "Sem isso este verify mandaria e-mail para artista de verdade."
)
app.config["MAIL_SUPPRESS_SEND"] = False

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


def _talento(sufixo: str, **campos) -> Talent:
    """Talento de teste apontando para um arquivo que NÃO existe — o estado real dos 40."""
    padrao = {
        "full_name": f"{PREFIX}{sufixo}",
        "status": "active",
        "email_contact": f"{PREFIX}{sufixo}@manto.local",
        "phone": "+55 11 90000-0000",
        "photo_face_path": f"/uploads/talent_photos/{PREFIX}{sufixo}_sumida.jpg",
    }
    padrao.update(campos)
    talento = Talent(**padrao)
    db.session.add(talento)
    return talento


def preparar() -> None:
    limpar()
    estado["recebe"] = _talento("recebe")
    estado["bounce"] = _talento("bounce")
    estado["bounce_resolvido"] = _talento("resolvido")
    estado["ja_recebeu"] = _talento("jarecebeu")
    estado["sem_email"] = _talento("semmail", email_contact=None)
    # Foto íntegra não entra na campanha: a de rosto existe de verdade e as outras estão vazias.
    pasta = os.path.join(UPLOADS, "talent_photos")
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, f"{PREFIX}ok.jpg")
    with open(caminho, "wb") as fh:
        fh.write(bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffd9"))
    estado["arquivo_ok"] = caminho
    estado["intacto"] = _talento(
        "intacto",
        photo_face_path=f"/uploads/talent_photos/{PREFIX}ok.jpg",
        photo_full_path=None,
        doc_photo_path=None,
        cnh_file_path=None,
    )
    db.session.flush()

    db.session.add(
        EmailBounce(
            email=estado["bounce"].email_contact,
            talent_id=estado["bounce"].id,
            kind="endereco_invalido",
            is_permanent=True,
            occurred_at=datetime.utcnow(),
            message_id=f"{PREFIX}bounce-1",
        )
    )
    db.session.add(
        EmailBounce(
            email=estado["bounce_resolvido"].email_contact,
            talent_id=estado["bounce_resolvido"].id,
            kind="caixa_cheia",
            is_permanent=True,
            occurred_at=datetime.utcnow(),
            resolved_at=datetime.utcnow(),
            message_id=f"{PREFIX}bounce-2",
        )
    )
    db.session.add(
        AuditLog(
            actor_name="Sistema",
            entity_type="Talent",
            entity_id=estado["ja_recebeu"].id,
            action=ACAO,
            detail="rodada anterior",
            created_at=datetime.utcnow(),
        )
    )
    db.session.commit()


def limpar() -> None:
    if estado.get("arquivo_ok") and os.path.exists(estado["arquivo_ok"]):
        os.remove(estado["arquivo_ok"])
    ids = [t.id for t in Talent.query.filter(Talent.full_name.like(f"{PREFIX}%")).all()]
    if ids:
        EmailBounce.query.filter(EmailBounce.talent_id.in_(ids)).delete(synchronize_session=False)
        AuditLog.query.filter(
            AuditLog.entity_type == "Talent", AuditLog.entity_id.in_(ids)
        ).delete(synchronize_session=False)
        Talent.query.filter(Talent.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()


def _rodar(*args: str):
    """Roda o comando restrito aos talentos deste verify.

    Sem o `--id` o comando varreria o espelho inteiro — que é uma cópia da produção, com o e-mail
    real de centenas de artistas. A supressão do Flask-Mail impede o envio, mas emitir token de
    redefinição e gravar auditoria para gente de verdade num teste é sujeira que não se justifica.
    """
    alvos = []
    for chave in ("recebe", "bounce", "bounce_resolvido", "ja_recebeu", "sem_email", "intacto"):
        if estado.get(chave) is not None:
            alvos += ["--id", str(estado[chave].id)]
    return app.test_cli_runner().invoke(args=["campanha-fotos", *alvos, *args])


def _nossos(saida: str) -> dict[str, str]:
    """Mapeia cada talento de teste para o bloco em que ele apareceu na saída do comando."""
    blocos = {}
    atual = None
    for linha in saida.splitlines():
        texto = linha.strip()
        if texto.startswith(("VÃO RECEBER", "PULADOS")):
            atual = texto.split(" (")[0]
        elif PREFIX in texto and atual:
            for chave in ("recebe", "bounce", "resolvido", "jarecebeu", "semmail", "intacto"):
                if f"{PREFIX}{chave}" in texto:
                    blocos.setdefault(chave, atual)
    return blocos


# ── Cenários ──────────────────────────────────────────────────────────────────

def c01_dry_run_classifica_e_nao_envia():
    from app.email_service import mail

    with mail.record_messages() as saiu:
        resultado = _rodar()
    _garante(resultado.exit_code == 0, f"comando falhou: {resultado.output[-400:]}")
    _garante(saiu == [], f"dry-run enviou {len(saiu)} mensagens")

    blocos = _nossos(resultado.output)
    esperado = {
        "recebe": "VÃO RECEBER",
        "resolvido": "VÃO RECEBER",
        "bounce": "PULADOS — devolução permanente, MANDAR POR WHATSAPP",
        "jarecebeu": "PULADOS — já receberam nesta campanha",
        "semmail": "PULADOS — sem e-mail no cadastro",
    }
    for chave, bloco in esperado.items():
        _garante(blocos.get(chave) == bloco, f"{chave}: caiu em {blocos.get(chave)!r}")
    _garante("intacto" not in blocos, "quem tem os arquivos entrou na campanha")

    recarregado = db.session.get(Talent, estado["recebe"].id)
    _garante(
        recarregado.password_reset_token is None,
        "o dry-run gravou token de redefinição — deveria ter feito rollback",
    )


def c02_envio_e_dedup():
    from app.email_service import mail

    alvo_id = estado["recebe"].id
    with mail.record_messages() as saiu:
        resultado = _rodar("--enviar", "--pausa", "0")
    _garante(resultado.exit_code == 0, f"comando falhou: {resultado.output[-400:]}")

    nossos = [m for m in saiu if PREFIX in (m.recipients[0] if m.recipients else "")]
    _garante(len(nossos) == 2, f"esperava 2 mensagens nossas, saíram {len(nossos)}")
    estado["mensagem"] = nossos[0]

    marcas = AuditLog.query.filter_by(
        entity_type="Talent", entity_id=alvo_id, action=ACAO
    ).count()
    _garante(marcas == 1, f"esperava 1 marca no AuditLog, achei {marcas}")

    with mail.record_messages() as denovo:
        _rodar("--enviar", "--pausa", "0")
    repetidos = [m for m in denovo if PREFIX in (m.recipients[0] if m.recipients else "")]
    _garante(repetidos == [], f"a segunda rodada reenviou para {len(repetidos)} pessoas")


def c03_corpo_do_email():
    msg = estado["mensagem"]
    corpo = msg.html or ""
    _garante("fotos-documentos" in corpo, "o link não leva à tela de fotos")
    _garante("destino=%2Ffotos-documentos" in corpo, "faltou o ?destino= no link")
    _garante("localhost" not in corpo, "o corpo carrega link local — a trava da 269b existe por isso")
    _garante("7 dias" in corpo, "o corpo não diz a validade real do link")
    _garante("foto de rosto" in corpo, "o corpo não diz o que falta daquela pessoa")
    _garante("reset-password" in corpo, "faltou o link de redefinição")


def c04_ttl_da_campanha():
    from app.talent_portal.portal_account_ops import (
        CAMPANHA_RESET_TTL,
        RESET_TOKEN_TTL,
        emitir_token_de_reset,
    )

    _garante(RESET_TOKEN_TTL == timedelta(hours=1), "o TTL do autoatendimento mudou")
    _garante(CAMPANHA_RESET_TTL == timedelta(days=7), "o TTL da campanha mudou")

    talento = db.session.get(Talent, estado["recebe"].id)
    emitir_token_de_reset(talento)
    curto = talento.password_reset_expires
    emitir_token_de_reset(talento, CAMPANHA_RESET_TTL)
    longo = talento.password_reset_expires
    db.session.rollback()
    _garante(longo - curto > timedelta(days=6), f"o TTL da campanha não valeu: {longo - curto}")


def c05_bounce_resolvido_volta_a_receber():
    """Corrigir o e-mail no cadastro tem de devolver a pessoa para a fila.

    O critério é o bounce **em aberto** contra o `email_contact` atual: quando o casting arruma o
    endereço e resolve a devolução, a pessoa volta a ser alcançável. Comparar contra o histórico
    inteiro a deixaria de fora para sempre.
    """
    blocos = _nossos(_rodar().output)
    # Já recebeu no cenário 02, então agora aparece como repetido — o que importa é que ele NÃO
    # está no balde de devolução permanente.
    caiu_em = blocos.get("resolvido")
    _garante(
        caiu_em is not None and "devolução permanente" not in caiu_em,
        f"o bounce resolvido foi tratado como e-mail morto: {caiu_em}",
    )


def c06_faltas_por_pessoa():
    from app.talents.midia_ops import faltas_do_talento

    intacto = db.session.get(Talent, estado["intacto"].id)
    _garante(faltas_do_talento(intacto) == [], f"achou falta onde não há: {faltas_do_talento(intacto)}")

    recebe = db.session.get(Talent, estado["recebe"].id)
    faltas = faltas_do_talento(recebe)
    _garante(faltas == ["foto de rosto"], f"faltas erradas: {faltas}")


def c07_destino_externo_recusado():
    from app.talent_portal.portal_links import portal_reset_url

    with app.test_request_context():
        _garante(
            "evil" not in portal_reset_url("tok", "//evil.example"),
            "o link do e-mail aceitou um destino externo",
        )
        _garante(
            "evil" not in portal_reset_url("tok", "https://evil.example"),
            "o link do e-mail aceitou uma URL absoluta como destino",
        )
        com_destino = portal_reset_url("tok", "/fotos-documentos")
        _garante("destino=%2Ffotos-documentos" in com_destino, f"destino não entrou: {com_destino}")


def main() -> int:
    print("\nVerificação da feature 293 — atualização cadastral\n")
    with app.app_context():
        try:
            preparar()
            cenario("01 dry-run classifica e não envia", c01_dry_run_classifica_e_nao_envia)
            cenario("02 envio marca no AuditLog e não repete", c02_envio_e_dedup)
            cenario("03 corpo do e-mail leva à tela de fotos", c03_corpo_do_email)
            cenario("04 link da campanha vale 7 dias", c04_ttl_da_campanha)
            cenario("05 bounce resolvido volta para a fila", c05_bounce_resolvido_volta_a_receber)
            cenario("06 faltas por pessoa, com o rótulo do e-mail", c06_faltas_por_pessoa)
            cenario("07 destino externo é recusado", c07_destino_externo_recusado)
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
