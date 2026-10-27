"""Verificação da correção 319 — o aviso de gasto extra diz o que é no assunto e na prévia.

Cenários:
 1. Reembolso com evento e comprovante: assunto "Gasto extra R$ 1.234,50 · <descrição>"; a
    prévia leva categoria, quem lançou, quem reembolsar, "com comprovante" e evento com data.
 2. Fornecedor sem evento e sem comprovante: prévia diz "pagar <fornecedor>", "sem comprovante"
    e "sem evento".
 3. Descrição longa é cortada com "…" no assunto, inteira no corpo.
 4. Texto digitado pelo usuário é escapado no corpo (nada de HTML injetado).
 5. Botão "Revisar gasto" aponta para /gastos da plataforma, sem link local.
 6. DEVE FALHAR o comportamento antigo: dois gastos do mesmo evento geravam assuntos idênticos;
    agora os assuntos diferem.

Nada sai: `_send` é trocado por um coletor, e nada é gravado (gastos transitórios + rollback).

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    $env:MAIL_SUPPRESS_SEND = "true"; $env:MANTO_SEM_THREADS = "1"; $env:PYTHONUTF8 = "1"
    .\\.venv\\Scripts\\python.exe specs\\319-aviso-gasto-extra\\verify_319.py
"""

from __future__ import annotations

import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MAIL_SUPPRESS_SEND", "true")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from app import (  # noqa: E402
    create_app,
    db,
    email_service,  # noqa: E402
)
from app.models import CalendarEvent, SpecialExpense, User  # noqa: E402

app = create_app()
resultados: list[tuple[str, bool, str]] = []
enviados: list[dict] = []


def _coletor(to, subject, html, **_kw):
    enviados.append({"to": to, "subject": subject, "html": html})
    return True


email_service._send = _coletor


def checar(nome: str, ok: bool, detalhe: str = "") -> None:
    resultados.append((nome, ok, detalhe))


def _preheader(html: str) -> str:
    inicio = html.index('<div style="display:none')
    trecho = html[inicio : html.index("</div>", inicio)]
    return trecho.split(">", 1)[1].split("&#847;", 1)[0]


def _gasto(**kw) -> SpecialExpense:
    base = dict(
        category="Transporte",
        amount=Decimal("1234.50"),
        expense_date=date(2026, 10, 22),
        status="pendente",
        payment_status="nao_pago",
        paid_at_creation=False,
    )
    base.update(kw)
    return SpecialExpense(**base)


def _enviar(expense, destinatario) -> dict:
    enviados.clear()
    n = email_service.send_new_expense_alert_email(expense, [destinatario])
    assert n == 1 and len(enviados) == 1, f"esperava 1 envio, veio {n}/{len(enviados)}"
    return enviados[0]


with app.app_context():
    try:
        usuarios = User.query.filter(User.email.isnot(None)).order_by(User.id).limit(3).all()
        autor, reembolsado, destinatario = usuarios[0], usuarios[1], usuarios[2]
        evento = (
            CalendarEvent.query.filter(CalendarEvent.start_at.isnot(None))
            .order_by(CalendarEvent.id.desc())
            .first()
        )
        data_evento = evento.start_at.strftime("%d/%m")
        primeiro = lambda u: u.name.split()[0]  # noqa: E731

        # 1
        g1 = _gasto(
            description="Uber ida e volta",
            created_by=autor,
            disbursement_type="reembolso",
            reimburse_user=reembolsado,
            receipt_path="expenses/x.pdf",
            event=evento,
        )
        m1 = _enviar(g1, destinatario)
        pre1 = _preheader(m1["html"])
        checar(
            "1a assunto com valor primeiro",
            m1["subject"] == "Gasto extra R$ 1.234,50 · Uber ida e volta",
            m1["subject"],
        )
        esperados = [
            "Transporte",
            f"lançado por {primeiro(autor)}",
            f"reembolsar {primeiro(reembolsado)}",
            "com comprovante",
            data_evento,
        ]
        faltam = [e for e in esperados if e not in pre1]
        checar("1b prévia completa", not faltam, f"faltam {faltam} em {pre1!r}")
        checar("1c prévia não repete o assunto genérico", "Novo gasto" not in pre1, pre1)

        # 2
        g2 = _gasto(
            description="Tecido do figurino",
            category="Figurino",
            created_by=autor,
            disbursement_type="fornecedor",
            supplier_name="Tecidos Ltda",
        )
        pre2 = _preheader(_enviar(g2, destinatario)["html"])
        faltam = [
            e for e in ["pagar Tecidos Ltda", "sem comprovante", "sem evento"] if e not in pre2
        ]
        checar("2 fornecedor sem evento", not faltam, f"faltam {faltam} em {pre2!r}")

        # 3
        longa = "Compra de material cenográfico para a montagem do palco principal e camarim"
        m3 = _enviar(_gasto(description=longa, created_by=autor), destinatario)
        assunto3 = m3["subject"]
        checar(
            "3 descrição longa cortada no assunto, inteira no corpo",
            assunto3.endswith("…")
            and len(assunto3) <= len("Gasto extra R$ 1.234,50 · ") + 50
            and longa in m3["html"],
            assunto3,
        )

        # 4
        m4 = _enviar(_gasto(description="<b>bold</b> & cia", created_by=autor), destinatario)
        checar(
            "4 HTML do usuário escapado",
            "<b>bold</b>" not in m4["html"] and "&lt;b&gt;bold&lt;/b&gt; &amp; cia" in m4["html"],
        )

        # 5
        html1 = m1["html"]
        checar("5a botão Revisar gasto", "Revisar gasto" in html1)
        hrefs = [h.split('"', 1)[0] for h in html1.split('href="')[1:]]
        gastos = [h for h in hrefs if h.endswith("/gastos")]
        checar("5b link para /gastos", bool(gastos), str(hrefs))
        checar(
            "5c link não é local",
            bool(gastos) and not email_service._link_local_no_corpo(html1),
            str(gastos),
        )

        # 6 — DEVE FALHAR o antigo: o assunto fixo de antes era igual para os dois gastos.
        assunto_antigo = "Novo gasto extra cadastrado — aprovação pendente"
        g6 = _gasto(
            description="Lanche da equipe", amount=Decimal("80"), created_by=autor, event=evento
        )
        m6 = _enviar(g6, destinatario)
        checar(
            "6 dois gastos do mesmo evento têm assuntos diferentes (antes: iguais)",
            m6["subject"] != m1["subject"] and assunto_antigo not in (m1["subject"], m6["subject"]),
            f"{m1['subject']!r} × {m6['subject']!r}",
        )

        print("\nPrévia do cenário 1 (como chega no celular):")
        print(f"  {m1['subject']}")
        print(f"  {pre1}")
        # Para abrir o e-mail no navegador: VERIFY_319_HTML=<arquivo>.
        if os.environ.get("VERIFY_319_HTML"):
            Path(os.environ["VERIFY_319_HTML"]).write_text(html1, encoding="utf-8")
    finally:
        db.session.rollback()

falhas = [r for r in resultados if not r[1]]
for nome, ok, det in resultados:
    print(f"{'OK  ' if ok else 'FALHA'} {nome}" + (f" — {det}" if not ok and det else ""))
print(f"\n{len(resultados) - len(falhas)}/{len(resultados)}")
sys.exit(1 if falhas else 0)
