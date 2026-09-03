"""Verificação do hotfix 269b — nenhum e-mail sai com link local.

O defeito: a produção no Render tinha `PORTAL_URL=http://localhost:5000` (mesmo valor do
`.env.example`), e o convite do artista, o lembrete de confirmação e o link de redefinição de
senha saíam apontando para o localhost de quem enviou.

Cenários:
 1. Config num processo que ENVIA de verdade (banco remoto, sem `MAIL_ALLOW_LOCAL_SEND`):
    `PORTAL_URL`/`PUBLIC_BASE_URL` locais são ignoradas, valem as constantes públicas, e cada
    valor recusado deixa aviso em `AVISOS_DE_URL` (o `create_app` grita no log do deploy).
 2. Config num processo LOCAL (banco em localhost ⇒ e-mail suprimido): o valor local é mantido —
    a necessidade legítima registrada pela 269 (ambiente de teste aponta para si) continua de pé.
 3. `_url_para_fora` caso a caso: vazio, sem esquema, http/https público, túnel, 127.0.0.1, ::1,
    faixas privadas (10/192.168/172.16-31), `host.docker.internal`, `.local`, barra final.
 4. Segunda camada: `_send` recusa qualquer corpo com link local e não chama o SMTP; corpo
    público passa; `MAIL_ALLOW_LOCAL_SEND=true` libera (quem testa é o próprio destinatário).
 5. Ponta a ponta com papel real do espelho: `send_invite_email` com a config saneada rende link
    público; com `PORTAL_URL` local forçada (caminho que escapasse da config), nada é enviado.
 6. Redefinição de senha (`portal_reset_url`) e cobrança da Home (`portal_url` do dashboard)
    saem com o portal público.

NADA é enviado: `mail.send` é dublado em todos os cenários e o ambiente já suprime e-mail.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    $env:PYTHONIOENCODING = "utf-8"
    .\\.venv\\Scripts\\python.exe specs\\269b-hotfix-link-do-portal\\verify_269b.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import traceback
from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()
# Cinto de segurança: este processo não envia e-mail nem que a config diga o contrário.
os.environ["MAIL_SUPPRESS_SEND"] = "true"
os.environ.pop("MAIL_ALLOW_LOCAL_SEND", None)

from app import create_app, db  # noqa: E402
from app import email_service as es  # noqa: E402
from app.config import (  # noqa: E402
    AVISOS_DE_URL,
    PLATFORM_BASE_URL,
    PORTAL_BASE_URL,
    _url_para_fora,
)
from app.models import EventRole  # noqa: E402
from app.talent_portal.portal_links import portal_reset_url  # noqa: E402

app = create_app()
app.config["TESTING"] = True

resultados: list[tuple[str, bool, str]] = []

# ── dublê do SMTP: nenhuma mensagem sai daqui ───────────────────────────────────────────────────
enviados: list[dict] = []
es.mail.send = lambda msg: enviados.append({"to": list(msg.recipients), "html": msg.html or ""})


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001 — o verify reporta, não estoura
        resultados.append((nome, False, str(exc)))
        print(f"  FALHA  {nome}: {exc}")
        if os.environ.get("VERIFY_DEBUG"):
            traceback.print_exc()


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


# ── config lida num processo separado, com o ambiente do cenário ────────────────────────────────

_FILHO = """
import importlib.util, json, pathlib, sys
alvo = pathlib.Path(sys.argv[1]) / "app" / "config.py"
spec = importlib.util.spec_from_file_location("cfg_isolada", alvo)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print(json.dumps({
    "portal": mod.Config.PORTAL_URL,
    "publica": mod.Config.PUBLIC_BASE_URL,
    "avisos": list(mod.AVISOS_DE_URL),
    "suprime": bool(mod.Config.MAIL_SUPPRESS_SEND),
}))
"""


def _config_com(**env: str) -> dict:
    """Carrega `app/config.py` num processo limpo com as variáveis do cenário."""
    ambiente = {k: v for k, v in os.environ.items() if not k.startswith(("PORTAL_URL", "PUBLIC_BASE_URL", "MAIL_"))}
    ambiente.update(env)
    saida = subprocess.run(
        [sys.executable, "-c", _FILHO, str(REPO_ROOT)],
        capture_output=True, text=True, cwd=str(REPO_ROOT), env=ambiente, timeout=120,
    )
    _garante(saida.returncode == 0, f"processo filho falhou: {saida.stderr[-400:]}")
    return json.loads(saida.stdout.strip().splitlines()[-1])


# ───────────────────────────── cenários ─────────────────────────────

def cen_01_producao_ignora_valor_local() -> None:
    cfg = _config_com(
        DATABASE_URL="postgresql://u:p@dpg-exemplo.oregon-postgres.render.com:5432/manto",
        PORTAL_URL="http://localhost:5000",
        PUBLIC_BASE_URL="http://127.0.0.1:5000",
    )
    _garante(cfg["suprime"] is False, "cenário deveria representar um processo que ENVIA e-mail")
    _garante(cfg["portal"] == PORTAL_BASE_URL, f"PORTAL_URL virou {cfg['portal']!r}")
    _garante(cfg["publica"] == PLATFORM_BASE_URL, f"PUBLIC_BASE_URL virou {cfg['publica']!r}")
    _garante(len(cfg["avisos"]) == 2, f"esperava 2 avisos, veio {cfg['avisos']}")
    _garante(
        all("IGNORADA" in a for a in cfg["avisos"]) and any("PORTAL_URL" in a for a in cfg["avisos"]),
        f"aviso pouco claro: {cfg['avisos']}",
    )


def cen_02_local_continua_apontando_para_si() -> None:
    cfg = _config_com(
        DATABASE_URL="postgresql://u:p@localhost:5432/manto_local",
        PORTAL_URL="http://localhost:5000",
    )
    _garante(cfg["suprime"] is True, "banco local deveria suprimir e-mail")
    _garante(cfg["portal"] == "http://localhost:5000", f"dev perdeu o próprio endereço: {cfg['portal']!r}")
    _garante(cfg["avisos"] == [], f"não deveria avisar em ambiente local: {cfg['avisos']}")
    # …mas quem pede para enviar de verdade daqui volta a receber link público.
    cfg = _config_com(
        DATABASE_URL="postgresql://u:p@localhost:5432/manto_local",
        PORTAL_URL="http://localhost:5000",
        MAIL_ALLOW_LOCAL_SEND="true",
    )
    _garante(cfg["suprime"] is False and cfg["portal"] == PORTAL_BASE_URL, f"envio local: {cfg}")


def cen_03_tabela_de_enderecos() -> None:
    casos_padrao = [
        None, "", "   ", "portal.mantoproducoes.com.br", "//portal.mantoproducoes.com.br",
        "http://localhost", "http://localhost:5000", "https://localhost:5173",
        "http://127.0.0.1:5000", "http://127.10.0.9", "http://0.0.0.0:8080", "http://[::1]:5000",
        "http://10.0.0.7:5000", "http://192.168.0.14:5000", "http://172.20.10.3:5000",
        "http://host.docker.internal:5000", "http://manto.local", "ftp://portal.exemplo.com",
    ]
    for valor in casos_padrao:
        obtido = _url_para_fora(valor, PORTAL_BASE_URL, "PORTAL_URL", permitir_local=False)
        _garante(obtido == PORTAL_BASE_URL, f"{valor!r} deveria cair no padrão, virou {obtido!r}")

    casos_aceitos = {
        "https://portal.mantoproducoes.com.br": "https://portal.mantoproducoes.com.br",
        "https://portal.mantoproducoes.com.br/": "https://portal.mantoproducoes.com.br",
        "https://manto-teste.onrender.com": "https://manto-teste.onrender.com",
        "https://ab12cd.ngrok-free.app/": "https://ab12cd.ngrok-free.app",
        "http://172.15.0.1:5000": "http://172.15.0.1:5000",  # fora da faixa privada 172.16–31
    }
    for valor, esperado in casos_aceitos.items():
        obtido = _url_para_fora(valor, PORTAL_BASE_URL, "PORTAL_URL", permitir_local=False)
        _garante(obtido == esperado, f"{valor!r} deveria passar como {esperado!r}, virou {obtido!r}")

    # Ambiente local: mantém o que pediram, sem aviso.
    antes = len(AVISOS_DE_URL)
    obtido = _url_para_fora("http://localhost:5000", PORTAL_BASE_URL, "PORTAL_URL", permitir_local=True)
    _garante(obtido == "http://localhost:5000", f"permitir_local não respeitado: {obtido!r}")
    _garante(len(AVISOS_DE_URL) == antes, "avisou num caso permitido")


def cen_04_send_barra_link_local() -> None:
    with app.app_context():
        es._emails_enabled = lambda: True  # a trava de ambiente é testada nos cenários 1-2
        app.config["MAIL_ALLOW_LOCAL_SEND"] = False
        enviados.clear()
        for corpo in (
            '<a href="http://localhost:5000/">portal</a>',
            '<a href="http://127.0.0.1:5000/reset-password?token=x">senha</a>',
            '<a href="HTTP://LOCALHOST:5173/">maiúsculo</a>',
        ):
            _garante(
                es._send(to="artista@exemplo.com", subject="Convite", html=corpo) is False,
                f"deixou passar: {corpo}",
            )
        _garante(enviados == [], f"chamou o SMTP mesmo assim: {enviados}")

        ok = es._send(
            to="artista@exemplo.com", subject="Convite",
            html=f'<a href="{PORTAL_BASE_URL}/">portal</a>',
        )
        _garante(ok is True and len(enviados) == 1, f"link público deveria passar: {ok} {enviados}")

        # Quem pede explicitamente para enviar do ambiente local é o próprio destinatário.
        app.config["MAIL_ALLOW_LOCAL_SEND"] = True
        enviados.clear()
        ok = es._send(to="eu@exemplo.com", subject="Teste", html='<a href="http://localhost:5000/">x</a>')
        _garante(ok is True and len(enviados) == 1, f"escape hatch quebrado: {ok} {enviados}")
        app.config["MAIL_ALLOW_LOCAL_SEND"] = False


def cen_05_convite_real_do_espelho() -> None:
    with app.app_context():
        papel = next(
            (r for r in EventRole.query.filter(EventRole.talent_id.isnot(None))
             .order_by(EventRole.id.desc()).limit(400).all()
             if r.talent and r.talent.email_contact and r.event and r.event.title),
            None,
        )
        _garante(papel is not None, "nenhum papel com talento e e-mail no espelho")

        es._emails_enabled = lambda: True
        app.config["PORTAL_URL"] = PORTAL_BASE_URL
        enviados.clear()
        _garante(es.send_invite_email(papel) is True, "convite com config saneada não saiu")
        _garante(len(enviados) == 1, f"esperava 1 envio, veio {len(enviados)}")
        html = enviados[0]["html"]
        _garante("localhost" not in html.lower() and "127.0.0.1" not in html, "convite ainda tem link local")
        _garante(PORTAL_BASE_URL in html, "convite não tem o portal público")

        # Simula um caminho que escapasse do saneamento da config: a segunda camada barra.
        app.config["PORTAL_URL"] = "http://localhost:5000"
        enviados.clear()
        _garante(es.send_invite_email(papel) is False, "convite com link local foi enviado")
        _garante(enviados == [], f"SMTP chamado com link local: {enviados}")
        app.config["PORTAL_URL"] = PORTAL_BASE_URL
        db.session.rollback()


def cen_06_reset_e_cobranca() -> None:
    with app.app_context():
        app.config["PORTAL_URL"] = PORTAL_BASE_URL
        url = portal_reset_url("tok-123")
        _garante(url.startswith(PORTAL_BASE_URL) and "tok-123" in url, f"reset: {url}")
        _garante("localhost" not in url, f"reset com localhost: {url}")
        # A cobrança da Home mostra este endereço para o staff colar no WhatsApp.
        _garante(
            (app.config.get("PORTAL_URL") or "").rstrip("/") == PORTAL_BASE_URL,
            "dashboard mostraria endereço errado",
        )


def main() -> int:
    print("Hotfix 269b — link do portal nos e-mails")
    cenario("1. processo que envia de verdade ignora PORTAL_URL/PUBLIC_BASE_URL locais", cen_01_producao_ignora_valor_local)
    cenario("2. ambiente local continua apontando para si (e envio explícito volta ao público)", cen_02_local_continua_apontando_para_si)
    cenario("3. tabela de endereços aceitos e recusados", cen_03_tabela_de_enderecos)
    cenario("4. _send barra corpo com link local e não chama o SMTP", cen_04_send_barra_link_local)
    cenario("5. convite de papel real: link público, e barrado se escapar", cen_05_convite_real_do_espelho)
    cenario("6. redefinição de senha e cobrança da Home com portal público", cen_06_reset_e_cobranca)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"{ok}/{len(resultados)} OK")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
