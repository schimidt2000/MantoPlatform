"""Verificação da feature 311 — aviso do prazo de pagamento + data do aceite no termo.

Cenários:
 1. Dry-run classifica nos baldes certos (recebe / bounce permanente / já recebeu / sem e-mail),
    diz a versão de cada um e **não envia nada**, nem grava token.
 2. `--enviar` manda uma mensagem por pessoa e marca o `AuditLog`; a segunda rodada manda zero.
 3. Versão "aceitou": data do aceite em São Paulo + link `/termos`, sem link de senha.
 4. Versão "não aceitou": sem senha (ou com a temporária) leva o link de criar senha com
    `destino=%2Ftermos` e a validade de 7 dias; com senha própria leva `/termos`, sem token.
 5. DEVE FALHAR o atalho: um aceite às 01:30 UTC é do dia ANTERIOR em São Paulo — a data UTC crua
    sairia errada no e-mail e na tela.
 6. `/api/portal/auth/me` devolve `terms_accepted_at` em São Paulo para quem aceitou e `null`
    para quem não aceitou.
 7. Nenhum corpo leva `localhost`, e todo corpo diz "até 3 dias úteis".
 8. Limpeza.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    $env:MAIL_SUPPRESS_SEND = "true"; $env:MANTO_SEM_THREADS = "1"; $env:PYTHONUTF8 = "1"
    .\\.venv\\Scripts\\python.exe specs\\311-aviso-prazo-pagamento\\verify_311.py
"""

from __future__ import annotations

import os
import sys
import traceback
from collections.abc import Callable
from datetime import datetime
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

PREFIX = "__v311_"
ACAO = "campanha_prazo_pagamento_311"
SENHA = "Verify311!senha"

app = create_app()
app.config["TESTING"] = True

# Mesmo arranjo do verify_293: o Flask-Mail nasce suprimido (nada sai de verdade) e só o gate do
# projeto é liberado, para a mensagem chegar ao `mail.send`, onde `record_messages` a intercepta.
assert app.extensions["mail"].suppress, (
    "Flask-Mail NÃO está suprimindo o envio: rode com MAIL_SUPPRESS_SEND=true. "
    "Sem isso este verify mandaria e-mail para artista de verdade."
)
app.config["MAIL_SUPPRESS_SEND"] = False

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}

#: Aceite às 01:30 UTC de 13/06 = 22:30 de 12/06 em São Paulo.
ACEITE_UTC = datetime(2026, 6, 13, 1, 30)


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001
        try:
            db.session.rollback()
        except RuntimeError:  # cenário de HTTP roda fora do app_context
            pass
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _talento(sufixo: str, **campos) -> Talent:
    padrao = {
        "full_name": f"{PREFIX}{sufixo}",
        "status": "active",
        "email_contact": f"{PREFIX}{sufixo}@manto.local",
        "phone": "+55 11 90000-0000",
    }
    senha = campos.pop("senha", None)
    padrao.update(campos)
    talento = Talent(**padrao)
    if senha:
        talento.set_password(senha)
    db.session.add(talento)
    return talento


def preparar() -> None:
    limpar()
    # `must_change_password` nasce True no modelo: só quem já trocou a senha temporária tem False.
    estado["aceitou"] = _talento(
        "aceitou", terms_accepted_at=ACEITE_UTC, senha=SENHA, must_change_password=False
    )
    estado["sem_senha"] = _talento("semsenha")
    estado["temporaria"] = _talento("temporaria", senha=SENHA, must_change_password=True)
    estado["com_senha"] = _talento("comsenha", senha=SENHA, must_change_password=False)
    estado["bounce"] = _talento("bounce", terms_accepted_at=ACEITE_UTC)
    estado["ja_recebeu"] = _talento("jarecebeu")
    estado["sem_email"] = _talento("semmail", email_contact=None)
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
    estado["ids"] = {chave: t.id for chave, t in estado.items() if isinstance(t, Talent)}


def limpar() -> None:
    ids = [t.id for t in Talent.query.filter(Talent.full_name.like(f"{PREFIX}%")).all()]
    if ids:
        EmailBounce.query.filter(EmailBounce.talent_id.in_(ids)).delete(synchronize_session=False)
        AuditLog.query.filter(AuditLog.entity_type == "Talent", AuditLog.entity_id.in_(ids)).delete(
            synchronize_session=False
        )
        Talent.query.filter(Talent.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()


def _rodar(*args: str):
    """Roda o comando restrito aos talentos deste verify.

    Sem o `--id` o comando varreria o espelho inteiro — cópia da produção, com o e-mail real de
    centenas de artistas. A supressão impede o envio, mas emitir token e gravar auditoria para
    gente de verdade num teste é sujeira que não se justifica.
    """
    alvos = []
    for talento_id in estado["ids"].values():
        alvos += ["--id", str(talento_id)]
    return app.test_cli_runner().invoke(args=["campanha-prazo-pagamento", *alvos, *args])


def _nossos(saida: str) -> dict[str, tuple[str, str]]:
    """Mapeia cada talento de teste para (bloco, versão) em que ele apareceu na saída."""
    blocos: dict[str, tuple[str, str]] = {}
    atual = None
    for linha in saida.splitlines():
        texto = linha.strip()
        if texto.startswith(("VÃO RECEBER", "PULADOS")):
            atual = texto.split(" (")[0]
        elif texto.startswith("#") and PREFIX in texto and atual:
            nome = texto.split()[1].removeprefix(PREFIX)
            versao = texto.split(None, 2)[2].strip()
            blocos.setdefault(nome, (atual, versao))
    return blocos


def _msg_de(chave: str):
    endereco = f"{PREFIX}{chave}@manto.local"
    for msg in estado["mensagens"]:
        if msg.recipients and msg.recipients[0] == endereco:
            return msg
    raise AssertionError(f"nenhuma mensagem para {endereco}")


# ── Cenários ──────────────────────────────────────────────────────────────────


def c01_dry_run_classifica_e_nao_envia():
    from app.email_service import mail

    with mail.record_messages() as saiu:
        resultado = _rodar()
    _garante(resultado.exit_code == 0, f"comando falhou: {resultado.output[-600:]}")
    _garante(saiu == [], f"dry-run enviou {len(saiu)} mensagens")

    blocos = _nossos(resultado.output)
    esperado = {
        "aceitou": ("VÃO RECEBER", "aceitou"),
        "semsenha": ("VÃO RECEBER", "nao aceitou, criar senha"),
        "temporaria": ("VÃO RECEBER", "nao aceitou, criar senha"),
        "comsenha": ("VÃO RECEBER", "nao aceitou, tem senha"),
        "bounce": ("PULADOS — devolução permanente, MANDAR POR WHATSAPP", "aceitou"),
        "jarecebeu": ("PULADOS — já receberam nesta campanha", "nao aceitou, criar senha"),
        "semmail": ("PULADOS — sem e-mail no cadastro", "nao aceitou, criar senha"),
    }
    for chave, par in esperado.items():
        _garante(
            blocos.get(chave) == par, f"{chave}: caiu em {blocos.get(chave)!r}, esperava {par!r}"
        )
    _garante(
        "EXEMPLO (aceitou)" in resultado.output, "o dry-run não mostrou o exemplo de quem aceitou"
    )
    _garante("DRY-RUN" in resultado.output, "o dry-run não se anunciou")

    db.session.expire_all()
    for chave in ("sem_senha", "temporaria"):
        recarregado = db.session.get(Talent, estado["ids"][chave])
        _garante(
            recarregado.password_reset_token is None,
            f"o dry-run gravou token para {chave} — deveria ter feito rollback",
        )


def c02_envio_e_dedup():
    from app.email_service import mail

    with mail.record_messages() as saiu:
        resultado = _rodar("--enviar", "--pausa", "0")
    _garante(resultado.exit_code == 0, f"comando falhou: {resultado.output[-600:]}")

    nossos = [m for m in saiu if m.recipients and PREFIX in m.recipients[0]]
    destinos = sorted(m.recipients[0].removeprefix(PREFIX).split("@")[0] for m in nossos)
    _garante(
        destinos == ["aceitou", "comsenha", "semsenha", "temporaria"],
        f"destinatários errados: {destinos}",
    )
    estado["mensagens"] = nossos

    for chave in ("aceitou", "sem_senha", "temporaria", "com_senha"):
        marcas = AuditLog.query.filter_by(
            entity_type="Talent", entity_id=estado["ids"][chave], action=ACAO
        ).count()
        _garante(marcas == 1, f"{chave}: esperava 1 marca no AuditLog, achei {marcas}")

    with mail.record_messages() as denovo:
        _rodar("--enviar", "--pausa", "0")
    repetidos = [m for m in denovo if m.recipients and PREFIX in m.recipients[0]]
    _garante(repetidos == [], f"a segunda rodada reenviou para {len(repetidos)} pessoas")


def c03_versao_aceitou():
    corpo = _msg_de("aceitou").html or ""
    _garante("12 de junho de 2026" in corpo, "a data do aceite não saiu em São Paulo (12/06)")
    _garante("13 de junho" not in corpo, "a data saiu em UTC (13/06)")
    _garante("/termos" in corpo, "faltou o link do termo")
    _garante("reset-password" not in corpo, "quem aceitou recebeu link de criar senha")
    _garante("Ver o termo que aceitei" in corpo, "faltou o botão da versão 'aceitou'")


def c04_versao_nao_aceitou():
    for chave in ("semsenha", "temporaria"):
        corpo = _msg_de(chave).html or ""
        _garante("reset-password" in corpo, f"{chave}: faltou o link de criar senha")
        _garante("destino=%2Ftermos" in corpo, f"{chave}: o link não leva ao termo")
        _garante("7 dias" in corpo, f"{chave}: o corpo não diz a validade real do link")
        _garante("você ainda não aceitou" in corpo, f"{chave}: o corpo não diz que falta o aceite")
        _garante("Você aceitou em" not in corpo, f"{chave}: o corpo diz que aceitou")

    corpo = _msg_de("comsenha").html or ""
    _garante("/termos" in corpo, "comsenha: faltou o link do termo")
    _garante("reset-password" not in corpo, "comsenha: quem tem senha recebeu link de criar senha")
    _garante("Esqueci minha senha" in corpo, "comsenha: faltou lembrar do 'Esqueci minha senha'")
    db.session.expire_all()
    com_senha = db.session.get(Talent, estado["ids"]["com_senha"])
    _garante(com_senha.password_reset_token is None, "comsenha: o comando gravou token à toa")


def c05_aceite_tarde_da_noite_e_do_dia_anterior():
    from app.talent_portal.portal_account_ops import aceite_do_termo_para_exibir

    talento = db.session.get(Talent, estado["ids"]["aceitou"])
    exibido = aceite_do_termo_para_exibir(talento)
    # O atalho (mostrar a coluna crua) daria 13/06 01:30 — é o que este cenário existe para pegar.
    _garante(talento.terms_accepted_at.day == 13, "o preparo do cenário mudou")
    _garante(exibido == datetime(2026, 6, 12, 22, 30), f"conversão errada: {exibido}")
    _garante(
        aceite_do_termo_para_exibir(db.session.get(Talent, estado["ids"]["sem_senha"])) is None,
        "quem não aceitou ganhou data de aceite",
    )


def _me(email: str) -> dict:
    cliente = app.test_client()
    login = cliente.post("/api/portal/auth/login", json={"login": email, "password": SENHA})
    _garante(
        login.status_code == 200,
        f"login de {email} deu {login.status_code}: {login.get_data(as_text=True)[:200]}",
    )
    _garante(
        "terms_accepted_at" in (login.get_json() or {}), "o login não devolve terms_accepted_at"
    )
    resposta = cliente.get("/api/portal/auth/me")
    _garante(resposta.status_code == 200, f"/me deu {resposta.status_code}")
    return resposta.get_json()


def c06_api_me():
    # Requisições FORA do app_context (o `g` do flask-login vazaria entre elas).
    estado["me_aceitou"] = _me(f"{PREFIX}aceitou@manto.local")
    estado["me_comsenha"] = _me(f"{PREFIX}comsenha@manto.local")


def c06b_api_me_confere():
    aceitou = estado["me_aceitou"]
    _garante(aceitou["terms_accepted"] is True, "terms_accepted mudou de significado")
    _garante(
        aceitou["terms_accepted_at"] == "2026-06-12T22:30:00",
        f"terms_accepted_at errado: {aceitou['terms_accepted_at']!r}",
    )
    comsenha = estado["me_comsenha"]
    _garante(comsenha["terms_accepted_at"] is None, "quem não aceitou ganhou terms_accepted_at")
    _garante("accept_terms" in comsenha["pending_steps"], "o portal deixou de pedir o aceite")


def c07_todo_corpo():
    for msg in estado["mensagens"]:
        corpo = msg.html or ""
        _garante("localhost" not in corpo, f"{msg.recipients[0]}: link local no corpo")
        _garante("até 3 dias úteis" in corpo, f"{msg.recipients[0]}: o corpo não diz o prazo")
        _garante(
            msg.subject == "Prazo de pagamento: até 3 dias úteis", f"assunto errado: {msg.subject}"
        )


def main() -> int:
    print("\nVerificação da feature 311 — aviso do prazo de pagamento\n")
    try:
        with app.app_context():
            preparar()
            cenario("01 dry-run classifica e não envia", c01_dry_run_classifica_e_nao_envia)
            cenario("02 envio marca no AuditLog e não repete", c02_envio_e_dedup)
            cenario("03 versão 'aceitou': data em SP e /termos", c03_versao_aceitou)
            cenario("04 versão 'não aceitou': link certo por caso", c04_versao_nao_aceitou)
            cenario(
                "05 aceite às 22h30 é do mesmo dia em SP",
                c05_aceite_tarde_da_noite_e_do_dia_anterior,
            )
        cenario("06 /me e login devolvem terms_accepted_at", c06_api_me)
        with app.app_context():
            cenario("06b /me: SP para quem aceitou, null para quem não", c06b_api_me_confere)
            cenario("07 todo corpo: prazo, assunto, sem localhost", c07_todo_corpo)
    finally:
        with app.app_context():
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
