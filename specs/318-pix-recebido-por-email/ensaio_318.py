"""Ensaio da 318 antes de ligar em produção: a regra contra os PIX reais, sem gravar nada.

Lê a caixa joao@mantoproducoes de verdade (IMAP, só leitura: EXAMINE + BODY.PEEK) desde `--desde`,
e repassa os avisos em ordem cronológica pela regra (`pix_ops.vincular`) contra o banco do
worktree, **dentro de uma transação desfeita no fim** (`rollback`): nenhum pagamento, aviso ou
notificação sobra. Compara com o gabarito do cruzamento extratos × ERP de 21/10
(`receitas_entradas_classificadas.csv`, caminho por argumento — fica fora do repositório).

Para simular "o PIX chega antes do comprovante", os comprovantes registrados a partir de `--desde`
são apagados no começo da transação (voltam no rollback): o ensaio mede o cenário em que a
comercial não anexa nada. Vendas cadastradas mais de 7 dias depois do PIX não são candidatas
(não existiam quando ele chegou, nem na janela de reavaliação).

Imprime SÓ contagens — nenhum nome, valor ou número de conta.

    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
    & $py specs\\318-pix-recebido-por-email\\ensaio_318.py --desde 2026-06-01 --ate 2026-10-21 `
        --gabarito <...>\\receitas_entradas_classificadas.csv --env C:\\...\\Manto_Platform\\.env

Critério para ligar (SC-001): `auto_errado = 0`.
"""

from __future__ import annotations

import argparse
import collections
import csv
import os
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
os.environ.setdefault("MAIL_SUPPRESS_SEND", "true")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO / ".local-db-url").read_text(encoding="utf-8").strip()


def _env(caminho: Path) -> dict[str, str]:
    valores: dict[str, str] = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if "=" in linha and not linha.lstrip().startswith("#"):
            k, v = linha.split("=", 1)
            valores[k.strip()] = v.strip().strip('"').strip("'")
    return valores


def _gabarito(caminho: Path, desde: date, ate: date) -> list[dict]:
    linhas = []
    with caminho.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["conta"] != "inter_mei" or r["tipo"] != "Pix recebido":
                continue
            d = date.fromisoformat(r["data"])
            if desde <= d <= ate:
                r["_data"] = d
                r["_valor"] = Decimal(r["valor"])
                linhas.append(r)
    return linhas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", default="2026-06-01")
    ap.add_argument("--ate", default="2026-10-21")
    ap.add_argument("--gabarito", required=True)
    ap.add_argument("--env", default=str(Path(r"C:\Users\schim\Desktop\Manto_Platform\.env")))
    # Simula o clique certo no "É esta?" quando a venda certa está entre as sugestões: mede o regime
    # em que cada confirmação ensina o "já pagou antes" (o replay puro só tem as automáticas).
    ap.add_argument("--simular-confirmacao", action="store_true")
    args = ap.parse_args()
    desde, ate = date.fromisoformat(args.desde), date.fromisoformat(args.ate)

    url = os.environ["DATABASE_URL"]
    if "localhost" not in url and "127.0.0.1" not in url:
        print("AMBIENTE IMPRÓPRIO — DATABASE_URL não é local.")
        return 2

    from app import create_app, db
    from app.constants import (
        PIX_ESTADO_CONTA_PROPRIA,
        PIX_ESTADO_LIGADO_AUTO,
        PIX_ESTADO_NOVO,
        PIX_ESTADO_PARA_CONFERIR,
        PIX_TIPO_PIX,
    )
    from app.financeiro import pix_email_ops, pix_ops
    from app.financeiro.cobranca_ops import principal_da_venda
    from app.financeiro.pix_aviso import AvisoPix, ler_aviso_inter
    from app.integracoes.imap_client import fetch_messages
    from app.models import CalendarEvent, ContaRecebimento, EventPayment, PixRecebido

    cred = _env(Path(args.env))
    dias = (date.today() - desde).days + 2
    print(f"lendo a caixa (só leitura), {dias} dias…", flush=True)
    brutos = fetch_messages(
        cred["MAIL_USERNAME"], cred["MAIL_PASSWORD"], sender="no-reply@inter.co",
        subject="Pix recebido", since_days=dias, limit=5000,
    )
    avisos = [a for a in (ler_aviso_inter(b) for b in brutos) if isinstance(a, AvisoPix)]
    avisos = [a for a in avisos if a.tipo == PIX_TIPO_PIX and desde <= a.recebido_em.date() <= ate]
    avisos.sort(key=lambda a: a.recebido_em)
    print(f"avisos de PIX no período: {len(avisos)}", flush=True)

    gabarito = _gabarito(Path(args.gabarito), desde, ate)
    usados: set[str] = set()

    def verdade(aviso: AvisoPix) -> dict | None:
        nome = pix_ops.normalizar_nome(aviso.pagador_nome)
        melhores = [
            g for g in gabarito
            if g["entrada_id"] not in usados and abs(g["_valor"] - aviso.valor) <= Decimal("0.01")
            and abs((g["_data"] - aviso.recebido_em.date()).days) <= 1
        ]
        melhores.sort(key=lambda g: (
            not pix_ops.nome_bate(nome, [g["contraparte"]]), abs((g["_data"] - aviso.recebido_em.date()).days)
        ))
        if melhores:
            usados.add(melhores[0]["entrada_id"])
            return melhores[0]
        return None

    app = create_app()
    contagem: collections.Counter = collections.Counter()
    with app.app_context():
        conn = db.session.connection()
        try:
            # A conta MEI ganha número só dentro da transação (o ensaio não toca a configuração).
            numero_mei = avisos[0].numero_conta if avisos else None
            mei = ContaRecebimento.query.filter_by(apelido="Inter MEI").first()
            if mei is not None and numero_mei and not mei.numero_conta:
                mei.numero_conta = numero_mei
            EventPayment.query.filter(
                EventPayment.created_at >= datetime.combine(desde, datetime.min.time())
            ).delete(synchronize_session=False)
            db.session.flush()

            original = pix_ops.vendas_abertas
            from app.constants import RoleName
            from app.models import Role, User

            quem_confirma = User.query.join(User.roles).filter(Role.name == RoleName.SUPERADMIN).first()

            def vendas_na_epoca(limite: datetime):
                return [
                    v for v in original()
                    if v.principal.created_at is None or v.principal.created_at <= limite + timedelta(days=7)
                ]

            for i, aviso in enumerate(avisos, 1):
                pix = pix_email_ops._ingerir(aviso, None)
                pix.message_id = f"<ensaio-{i}-{pix.message_id}"[:300]
                db.session.add(pix)
                db.session.flush()
                if pix.estado == PIX_ESTADO_NOVO:
                    pix_ops.vincular(pix, vendas=vendas_na_epoca(aviso.recebido_em + timedelta(hours=3)))
                    db.session.flush()

                g = verdade(aviso)
                classe = g["classificacao"] if g else "sem_gabarito"
                certo_evento = None
                if g and classe.startswith("casada") and g["event_id"]:
                    ev = db.session.get(CalendarEvent, int(g["event_id"]))
                    certo_evento = principal_da_venda(ev).id if ev else None

                if pix.estado == PIX_ESTADO_LIGADO_AUTO:
                    pagamento = db.session.get(EventPayment, pix.event_payment_id)
                    ev = db.session.get(CalendarEvent, pagamento.event_id) if pagamento else None
                    ligado = principal_da_venda(ev).id if ev else None
                    if certo_evento is not None and ligado == certo_evento:
                        contagem["auto_certo"] += 1
                    elif certo_evento is None and classe in ("sem_gabarito", "sem_registro_no_erp"):
                        contagem["auto_sem_gabarito"] += 1  # conferir à mão: venda que o ERP não tinha
                    else:
                        contagem["auto_errado"] += 1
                elif pix.estado == PIX_ESTADO_PARA_CONFERIR:
                    sugeridos = {e for c in pix.candidatos or [] for e in c.get("event_ids") or []}
                    if certo_evento is not None and certo_evento in sugeridos:
                        contagem["conferir_com_a_certa"] += 1
                        if args.simular_confirmacao and quem_confirma is not None:
                            pix_ops.confirmar(pix.id, [certo_evento], quem_confirma)
                            db.session.flush()
                    elif certo_evento is not None:
                        contagem["conferir_sem_a_certa"] += 1
                    else:
                        contagem["conferir_nao_venda"] += 1
                elif pix.estado == PIX_ESTADO_CONTA_PROPRIA:
                    contagem["conta_propria"] += 1
                else:
                    contagem["ignorado_venda" if certo_evento else "ignorado_nao_venda"] += 1
                contagem[f"gabarito:{classe}"] += 1
                if i % 50 == 0:
                    print(f"  … {i}/{len(avisos)}", flush=True)
        finally:
            db.session.rollback()
            conn.close()
        sobras = PixRecebido.query.filter(PixRecebido.message_id.like("<ensaio-%")).count()

    vendas_total = sum(v for k, v in contagem.items() if k.startswith("gabarito:casada"))
    print("\n── ensaio 318 (só contagens) ──")
    for chave in sorted(contagem):
        print(f"  {chave:28s} {contagem[chave]}")
    if vendas_total:
        print(f"\n  ligaria sozinho certo: {contagem['auto_certo']}/{vendas_total} PIX de venda "
              f"({100 * contagem['auto_certo'] / vendas_total:.0f}%)")
    print(f"  ligação automática ERRADA: {contagem['auto_errado']}")
    print(f"  sobras no banco: {sobras}")
    return 0 if contagem["auto_errado"] == 0 and sobras == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
