"""Verificação da 304 — loja de conversas com cara de Natal + campanha do Papai Noel.

Roda contra o `manto_local` (Postgres). Requisições do test client FORA de `app.app_context()`.

  V1  Script da campanha: rodar de novo não cria outra; a campanha nasce em rascunho, com o
      personagem do catálogo, endereço curto, textos, WhatsApp e preços zerados.
  V2  A campanha em rascunho NÃO aparece para o público (deve falhar: 404 no detalhe, fora da
      vitrine); a capa dela abre sem login (rota pública).
  V3  Publicar com preço zero é RECUSADO (deve falhar) — chamada a R$ 0,00; vídeo a R$ 0,00 com
      vaga de vídeo à venda. Com a chamada cobrada e sem vaga de vídeo, publica.
  V4  E-mails da loja: tema de Natal, saudação sem o nome da criança, assunto com a campanha, a
      cartinha no e-mail da chamada ao vivo, horário de Brasília. E-mail de outro domínio sai
      IDÊNTICO ao da `main` (moldura e botão).

Uso:
    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONPATH = (Get-Location).Path
    .venv\\Scripts\\python.exe specs\\304-loja-natal-papai-noel\\verify_304.py

Pré-requisito: `criar_campanha_noel.py --execute` já rodou neste banco (o V1 confere o resultado).
"""

import importlib.util
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

if "sqlite" in os.environ.get("DATABASE_URL", "sqlite"):
    sys.exit("ERRO: aponte DATABASE_URL para manto_local (Postgres), nunca SQLite.")
if os.environ.get("MANTO_SEM_THREADS") != "1":
    sys.exit("ERRO: rode com MANTO_SEM_THREADS=1 (o manto_local tem credenciais reais).")

from sqlalchemy import create_engine, text  # noqa: E402

from app import (  # noqa: E402
    create_app,
    db,
    email_service,  # noqa: E402
)
from app.marketing import virtuais_ops as ops  # noqa: E402
from app.models import VirtualCampaign  # noqa: E402

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
SCRIPT = AQUI / "criar_campanha_noel.py"

app = create_app()
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))


def no_banco(sql: str, **params):
    """Lê por uma conexão SEPARADA — o autoflush da sessão do app esconde falta de commit."""
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.connect() as conn:
        return conn.execute(text(sql), params).fetchall()


def rodar_script(*args: str) -> str:
    saida = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONPATH": str(RAIZ)},
        cwd=str(RAIZ),
    )
    return saida.stdout + saida.stderr


# ── V1 — script idempotente e o rascunho que ele deixa ───────────────────────

antes = no_banco("select count(*) from virtual_campaigns where slug = 'papai-noel'")[0][0]
check("V1.0 pré-requisito: a campanha do script existe", antes == 1, f"achei {antes}")
saida = rodar_script("--execute")
depois = no_banco("select count(*) from virtual_campaigns where slug = 'papai-noel'")[0][0]
check(
    "V1.1 rodar de novo não cria outra",
    depois == 1 and "Já existe" in saida,
    f"{depois}; {saida[-200:]}",
)

linha = no_banco(
    """select c.status, c.title, ch.name, c.price_live, c.price_recorded, c.recorded_capacity,
              c.whatsapp_phone, c.tolerance_terms, c.intro_html, c.cover_url, c.faq_json
         from virtual_campaigns c join catalog_characters ch on ch.id = c.catalog_character_id
        where c.slug = 'papai-noel'"""
)[0]
(status, titulo, personagem, p_live, p_rec, cap, zap, termos, intro, capa, faq) = linha
check("V1.2 nasce em rascunho", status == "rascunho", status)
check(
    "V1.3 título e personagem do catálogo",
    titulo == "Uma chamada com o Papai Noel" and personagem == "Papai Noel",
    f"{titulo} / {personagem}",
)
check(
    "V1.4 preços e vagas de vídeo zerados (decisão do time)",
    p_live == 0 and p_rec == 0 and cap == 0,
    f"{p_live} {p_rec} {cap}",
)
check("V1.5 WhatsApp da empresa", zap == "5511970570577", str(zap))
check(
    "V1.6 apresentação fala da cartinha; termos escritos",
    "cartinha" in (intro or "") and bool(termos),
    "",
)
check(
    "V1.7 capa na rota pública da loja",
    (capa or "").startswith("/catalogo/midia/campanhas/"),
    str(capa),
)
check("V1.8 FAQ vazio (a página usa o da loja)", not faq, str(faq))

# ── V2 — rascunho não é público; a capa é ────────────────────────────────────

cliente = app.test_client()
r = cliente.get("/api/virtuais/campanhas/papai-noel")
check(
    "V2.1 rascunho: detalhe público responde 404 (deve falhar)",
    r.status_code == 404,
    str(r.status_code),
)
r = cliente.get("/api/virtuais/vitrine")
slugs = [c["slug"] for c in (r.get_json() or {}).get("campanhas", [])]
check(
    "V2.2 rascunho fora da vitrine",
    r.status_code == 200 and "papai-noel" not in slugs,
    f"{r.status_code} {slugs}",
)
r = cliente.get(capa)
check(
    "V2.3 capa abre sem login",
    r.status_code == 200 and r.mimetype.startswith("image/"),
    f"{r.status_code} {r.mimetype}",
)

# ── V3 — publicar com preço zero é recusado ──────────────────────────────────

descartavel_id = None
# Feature 310: publicar também exige o pagamento da loja ligado. Liga só para este bloco e
# devolve o estado do banco local logo depois do V3.4.
PAGAMENTO_CAMPOS = ("infinitepay_handle", "infinitepay_webhook_token", "virtuais_pagamento_ativo")
with app.app_context():
    from app.models import SiteSetting

    _cfg = db.session.get(SiteSetting, 1)
    pagamento_original = {c: getattr(_cfg, c) for c in PAGAMENTO_CAMPOS}
    _cfg.infinitepay_handle = _cfg.infinitepay_handle or "verify304"
    _cfg.infinitepay_webhook_token = _cfg.infinitepay_webhook_token or "verify304-token"
    _cfg.virtuais_pagamento_ativo = True
    db.session.commit()

with app.app_context():
    personagem_id = VirtualCampaign.query.filter_by(slug="papai-noel").first().catalog_character_id
    descartavel = ops.criar_campanha(
        catalog_character_id=personagem_id,
        title="Verify304 descartável",
        price_live=0,
        price_recorded=0,
        recorded_capacity=0,
        tolerance_terms="termos",
        cover_url=capa,
    )
    descartavel_id = descartavel.id

    def tentar_publicar() -> str | None:
        camp = db.session.get(VirtualCampaign, descartavel_id)
        try:
            ops.alterar_status(camp, "publicada")
            return None
        except ops.VirtuaisValidationError as exc:
            db.session.rollback()
            return exc.field

    campo = tentar_publicar()
    check(
        "V3.1 chamada a R$ 0,00: publicação RECUSADA (deve falhar)",
        campo == "price_live",
        str(campo),
    )

    camp = db.session.get(VirtualCampaign, descartavel_id)
    camp.price_live = Decimal("150.00")
    camp.recorded_capacity = 5
    db.session.commit()
    campo = tentar_publicar()
    check(
        "V3.2 vídeo a R$ 0,00 com vaga à venda: RECUSADA (deve falhar)",
        campo == "price_recorded",
        str(campo),
    )

    camp = db.session.get(VirtualCampaign, descartavel_id)
    camp.recorded_capacity = 0
    db.session.commit()
    campo = tentar_publicar()

estado = no_banco("select status from virtual_campaigns where id = :i", i=descartavel_id)[0][0]
check(
    "V3.3 chamada cobrada e sem vaga de vídeo: publica",
    campo is None and estado == "publicada",
    f"{campo} {estado}",
)

with app.app_context():
    db.session.delete(db.session.get(VirtualCampaign, descartavel_id))
    db.session.commit()
    _cfg = db.session.get(SiteSetting, 1)
    for _campo, _valor in pagamento_original.items():
        setattr(_cfg, _campo, _valor)
    db.session.commit()
sobrou = no_banco("select count(*) from virtual_campaigns where id = :i", i=descartavel_id)[0][0]
check("V3.4 limpeza da campanha descartável", sobrou == 0, str(sobrou))

# ── V4 — e-mails da loja ─────────────────────────────────────────────────────

capturados: list[dict] = []
envio_original = email_service._send


def _captura(**kwargs):
    capturados.append(kwargs)
    return True


email_service._send = _captura
try:
    with app.app_context():
        campanha = SimpleNamespace(
            title="Uma chamada com o Papai Noel", recorded_delivery_days=7, slug="papai-noel"
        )
        base = dict(
            campaign=campanha,
            child_name="Maria Clara",
            contact_email="familia@example.com",
            total_value=Decimal("150.00"),
            public_token="tok304",
        )
        ao_vivo = SimpleNamespace(
            **base,
            modality="ao_vivo",
            slot=SimpleNamespace(start_at=datetime(2026, 12, 20, 14, 30)),
        )
        gravado = SimpleNamespace(**base, modality="gravado", slot=None)
        email_service.send_virtual_order_confirmed_email(ao_vivo)
        email_service.send_virtual_order_confirmed_email(gravado)
        email_service.send_virtual_video_ready_email(gravado)
        email_service.send_virtual_order_cancelled_email(ao_vivo)
finally:
    email_service._send = envio_original

confirmado_vivo, confirmado_gravado, video, cancelado = capturados
tema = email_service.TEMA_LOJA_VIRTUAL
check(
    "V4.1 assunto da confirmação com a campanha",
    confirmado_vivo["subject"] == "🎄 Reserva confirmada — Uma chamada com o Papai Noel",
    confirmado_vivo["subject"],
)
for nome, mail in [
    ("confirmação", confirmado_vivo),
    ("vídeo pronto", video),
    ("cancelamento", cancelado),
]:
    html = mail["html"]
    check(
        f"V4.2 {nome}: moldura e botão no tema",
        tema["cabecalho"] in html and tema["botao"] in html,
        "",
    )
    check(
        f"V4.3 {nome}: saúda o adulto, não a criança",
        ">Olá!<" in html and "Olá, Maria" not in html,
        "",
    )
check(
    "V4.4 chamada ao vivo: horário de Brasília e a cartinha",
    "20/12/2026 às 14:30 (horário de Brasília)" in confirmado_vivo["html"]
    and "cartinha" in confirmado_vivo["html"],
    "",
)
check(
    "V4.5 vídeo gravado: sem cartinha, com o aviso do próximo e-mail",
    "cartinha" not in confirmado_gravado["html"] and "outro e-mail" in confirmado_gravado["html"],
    "",
)
check(
    "V4.6 assunto do vídeo pronto com o primeiro nome",
    video["subject"] == "🎄 O vídeo para Maria ficou pronto!",
    video["subject"],
)

# E-mail de qualquer outro domínio: moldura e botão idênticos aos da `main`.
antigo = subprocess.run(
    ["git", "show", "main:app/email_service.py"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    cwd=str(RAIZ),
).stdout
with tempfile.TemporaryDirectory() as pasta:
    caminho = Path(pasta) / "email_service_main.py"
    caminho.write_text(antigo, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("email_service_main", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    iguais = (
        modulo._html_wrap("<p>corpo</p>", "pre") == email_service._html_wrap("<p>corpo</p>", "pre")
        and modulo._html_wrap("<p>x</p>") == email_service._html_wrap("<p>x</p>")
        and modulo._btn("Ir", "https://x") == email_service._btn("Ir", "https://x")
    )
check("V4.7 e-mail dos outros domínios idêntico ao da main", bool(antigo) and iguais, "")

# ── Resumo ───────────────────────────────────────────────────────────────────

falhas = [r for r in results if not r[1]]
print(f"\n{len(results) - len(falhas)}/{len(results)} OK")
sys.exit(1 if falhas else 0)
