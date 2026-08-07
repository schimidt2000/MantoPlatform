"""Coleta semanal do agente auditor financeiro (feature 221).

Lê o Postgres (produção ou `manto_local`) em MODO SOMENTE LEITURA, monta o manifesto da
rodada com tudo que precisa de auditoria e baixa os comprovantes da janela:

    python collect.py --local            # contra manto_local + arquivos de instance/uploads
    python collect.py                    # contra produção + download via /api/audit-agent

Saída: `runs/<carimbo>/manifest.json` + `runs/<carimbo>/files/…`. Itens com comprovante e
hash inédito ficam com status `needs_extraction` — a leitura (OCR/visão) é feita pelo Claude
na rodada, fora deste script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
import psycopg.rows
import requests

import config
import store
from pixnorm import normalize_pix

TZ_SP = ZoneInfo("America/Sao_Paulo")


# ── Janela ────────────────────────────────────────────────────────────────────


def compute_window(args: argparse.Namespace) -> tuple[datetime, datetime]:
    """Janela CONTÁBIL da rodada em UTC aware: do fim da última rodada enviada até agora.

    Esta é a janela dos números da semana (sem sobreposição entre relatórios). A coleta de
    itens usa uma janela estendida (margem de recoleta) derivada dela no `main`.
    """
    now = datetime.now(timezone.utc)
    if args.desde:
        start_sp = datetime.strptime(args.desde, "%Y-%m-%d").replace(tzinfo=TZ_SP)
        return start_sp.astimezone(timezone.utc), now
    last_end = store.last_window_end()
    if last_end:
        start = datetime.fromisoformat(last_end)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
    else:
        start = now - timedelta(days=7)
    return start, now


def _naive_utc(dt: datetime) -> datetime:
    """Colunas gravadas com `datetime.utcnow` são naive UTC — parâmetro precisa casar."""
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _naive_sp(dt: datetime) -> datetime:
    """O módulo virtual grava horário de parede de São Paulo (naive)."""
    return dt.astimezone(TZ_SP).replace(tzinfo=None)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _rel_path(raw: str | None) -> str | None:
    """Normaliza o caminho do arquivo para relativo à raiz de uploads."""
    if not raw:
        return None
    rel = raw.replace("\\", "/")
    if rel.startswith("/uploads/"):
        rel = rel[len("/uploads/"):]
    return rel.lstrip("/")


def _dec(value) -> str | None:
    """Decimal → str (JSON não tem Decimal; string preserva os centavos)."""
    if value is None:
        return None
    return str(Decimal(value))


class FileFetcher:
    """Obtém os bytes de um comprovante — produção (HTTP) ou cópia local (disco)."""

    def __init__(self, local: bool, files_dir: Path):
        self.local = local
        self.files_dir = files_dir
        files_dir.mkdir(parents=True, exist_ok=True)
        if not local:
            self.base = config.base_url(local=False)
            self.token = config.agent_token()
        self.local_uploads = config.REPO_ROOT / "instance" / "uploads"

    def fetch(self, rel: str) -> tuple[Path | None, str | None]:
        """Baixa/copia `rel`; devolve (caminho_local, 'arquivo_ausente'|None)."""
        dest = self.files_dir / rel.replace("/", "__")
        if dest.exists():
            return dest, None
        if self.local:
            src = self.local_uploads / Path(rel)
            if not src.is_file():
                return None, "arquivo_ausente"
            shutil.copyfile(src, dest)
            return dest, None
        url = f"{self.base}/api/audit-agent/{self.token}/file/{rel}"
        resp = requests.get(url, timeout=60)
        if resp.status_code == 404:
            # 404 tem dois significados: arquivo sumido (achado) ou token inválido/env
            # ausente no Railway (erro de configuração — abortar, nunca reportar como
            # se todos os comprovantes tivessem sumido).
            try:
                msg = resp.json().get("error", {}).get("message")
            except ValueError:
                msg = None
            if msg == "arquivo_ausente":
                return None, "arquivo_ausente"
            raise RuntimeError(
                "Endpoint do auditor respondeu 404 genérico — AUDIT_AGENT_TOKEN não "
                "configurado no Railway ou token local divergente."
            )
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        return dest, None


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ── Coleta de itens auditáveis (com comprovante) ─────────────────────────────


def collect_items(cur, win: tuple[datetime, datetime]) -> list[dict]:
    """Itens com comprovante esperado, um dict por arquivo a auditar."""
    a, b = _naive_utc(win[0]), _naive_utc(win[1])
    items: list[dict] = []

    cur.execute(
        """
        SELECT p.id, p.event_id, p.file_path, p.amount, p.created_at,
               e.title, e.sale_value, e.sale_date, e.is_cortesia_permuta, e.event_type,
               c.name AS client_name, c.cpf AS client_cpf, c.cnpj AS client_cnpj
          FROM event_payments p
          JOIN calendar_events e ON e.id = p.event_id
          LEFT JOIN clients c ON c.id = e.client_id
         WHERE p.created_at >= %s AND p.created_at < %s
         ORDER BY p.id
        """,
        (a, b),
    )
    for r in cur.fetchall():
        items.append({
            "entity_uid": f"event_payment:{r['id']}",
            "kind": "entrada",
            "descricao": f"Recebimento do evento “{r['title']}”",
            "amount": _dec(r["amount"]),
            "expected_date": str(r["created_at"].date()),
            "expected_payer": r["client_name"],
            "expected_pix": None,
            "file_rel": _rel_path(r["file_path"]),
            "event_id": r["event_id"],
            "flags": {"amount_null": r["amount"] is None,
                      "cortesia": bool(r["is_cortesia_permuta"])},
        })

    cur.execute(
        """
        SELECT g.id, g.description, g.category, g.amount, g.expense_date, g.receipt_path,
               g.status, g.disbursement_type, g.supplier_name, g.supplier_pix,
               g.approved_with_edits, g.event_id, g.payment_status, g.paid_at_creation,
               u.name AS reimburse_name, u.pix_key AS reimburse_pix
          FROM special_expenses g
          LEFT JOIN users u ON u.id = g.reimburse_user_id
         WHERE (g.created_at >= %s AND g.created_at < %s)
            OR (g.approved_at >= %s AND g.approved_at < %s)
         ORDER BY g.id
        """,
        (a, b, a, b),
    )
    for r in cur.fetchall():
        fornecedor = r["disbursement_type"] == "fornecedor"
        items.append({
            "entity_uid": f"special_expense:{r['id']}",
            "kind": "gasto",
            "descricao": f"Gasto extra “{r['description']}” ({r['category']})",
            "amount": _dec(r["amount"]),
            "expected_date": str(r["expense_date"]) if r["expense_date"] else None,
            "expected_payee": r["supplier_name"] if fornecedor else r["reimburse_name"],
            "expected_pix": r["supplier_pix"] if fornecedor else r["reimburse_pix"],
            "file_rel": _rel_path(r["receipt_path"]),
            "event_id": r["event_id"],
            "flags": {"status": r["status"],
                      "approved_with_edits": bool(r["approved_with_edits"]),
                      "receipt_null": r["receipt_path"] is None,
                      "payment_status": r["payment_status"],
                      "paid_at_creation": bool(r["paid_at_creation"])},
        })

    cur.execute(
        """
        SELECT sa.id, sa.amount, sa.proof, sa.advance_date,
               u.name AS user_name, u.pix_key AS user_pix
          FROM salary_advances sa
          JOIN salary_payments sp ON sp.id = sa.salary_payment_id
          JOIN users u ON u.id = sp.user_id
         WHERE sa.created_at >= %s AND sa.created_at < %s
         ORDER BY sa.id
        """,
        (a, b),
    )
    for r in cur.fetchall():
        items.append({
            "entity_uid": f"salary_advance:{r['id']}",
            "kind": "adiantamento",
            "descricao": f"Adiantamento de salário — {r['user_name']}",
            "amount": _dec(r["amount"]),
            "expected_date": str(r["advance_date"]) if r["advance_date"] else None,
            "expected_payee": r["user_name"],
            "expected_pix": r["user_pix"],
            "file_rel": _rel_path(r["proof"]),
            "event_id": None,
            "flags": {},
        })

    cur.execute(
        """
        SELECT er.id, er.event_id, er.description, er.amount, er.collected_at,
               er.collected_amount, er.invoice_file_path, er.receipt_file_path,
               e.title
          FROM event_reimbursements er
          JOIN calendar_events e ON e.id = er.event_id
         WHERE (er.created_at >= %s AND er.created_at < %s)
            OR (er.collected_at >= %s AND er.collected_at < %s)
         ORDER BY er.id
        """,
        (a, b, a, b),
    )
    for r in cur.fetchall():
        base = {
            "event_id": r["event_id"],
            "expected_payee": None,
            "expected_pix": None,
        }
        if r["invoice_file_path"]:
            items.append({
                **base,
                "entity_uid": f"event_reimbursement:{r['id']}:nf",
                "kind": "reembolso_nf",
                "descricao": f"Nota do reembolso “{r['description']}” — {r['title']}",
                "amount": _dec(r["amount"]),
                "expected_date": None,
                "file_rel": _rel_path(r["invoice_file_path"]),
                "flags": {},
            })
        if r["receipt_file_path"]:
            items.append({
                **base,
                "entity_uid": f"event_reimbursement:{r['id']}:recibo",
                "kind": "reembolso_recibo",
                "descricao": f"Recebimento do reembolso “{r['description']}” — {r['title']}",
                "amount": _dec(r["collected_amount"] or r["amount"]),
                "expected_date": str(r["collected_at"].date()) if r["collected_at"] else None,
                "file_rel": _rel_path(r["receipt_file_path"]),
                "flags": {},
            })
    return items


# ── Anomalias detectáveis direto no SQL ──────────────────────────────────────


def collect_sql_anomalies(cur, win: tuple[datetime, datetime]) -> list[dict]:
    """Achados que não dependem de ler comprovante."""
    a, b = _naive_utc(win[0]), _naive_utc(win[1])
    asp, bsp = _naive_sp(win[0]), _naive_sp(win[1])
    out: list[dict] = []

    cur.execute(
        """
        SELECT file_path, COUNT(*) AS n, ARRAY_AGG(id ORDER BY id) AS ids
          FROM event_payments
         WHERE file_path IS NOT NULL
         GROUP BY file_path HAVING COUNT(*) > 1
        """
    )
    for r in cur.fetchall():
        out.append({
            "entity_uid": f"file:{r['file_path']}",
            "code": "mesmo_arquivo_dois_pagamentos", "severity": "critico",
            "title": f"Mesmo arquivo usado em {r['n']} recebimentos (ids {r['ids']})",
            "details": {"file_path": r["file_path"], "ids": r["ids"]},
        })

    # Recebido acima do esperado. Esperado = venda + transporte + acréscimos, porque
    # transporte/acréscimo são cobrados nos mesmos comprovantes mas ficam fora de
    # `sale_value`. Diferença de até 1% vira "atenção" (juros de parcelamento,
    # arredondamento); acima disso é crítico (centavos sem vírgula, pagamento duplicado).
    cur.execute(
        """
        SELECT e.id, e.title, e.sale_value,
               COALESCE(e.sale_value, 0) + COALESCE(e.transport_value, 0)
                 + COALESCE(e.acrescimo_value, 0) AS esperado,
               SUM(p.amount) AS recebido
          FROM calendar_events e
          JOIN event_payments p ON p.event_id = e.id
         WHERE e.sale_value IS NOT NULL AND e.is_cortesia_permuta IS NOT TRUE
         GROUP BY e.id, e.title, e.sale_value, esperado
        HAVING SUM(p.amount) > COALESCE(e.sale_value, 0) + COALESCE(e.transport_value, 0)
                 + COALESCE(e.acrescimo_value, 0)
        """
    )
    for r in cur.fetchall():
        esperado, recebido = Decimal(r["esperado"]), Decimal(r["recebido"])
        excesso = recebido - esperado
        grave = esperado > 0 and (excesso / esperado) > Decimal("0.01")
        out.append({
            "entity_uid": f"calendar_event:{r['id']}",
            "code": "recebido_maior_que_venda",
            "severity": "critico" if grave else "atencao",
            "title": (f"“{r['title']}”: recebido R$ {recebido} excede em R$ {excesso} o "
                      f"esperado R$ {esperado} (venda + transporte + acréscimos)"),
            "details": {"event_id": r["id"], "recebido": str(recebido),
                        "esperado": str(esperado), "excesso": str(excesso)},
        })

    # `start_at` é horário de parede de São Paulo (naive) — comparar com janela SP.
    cur.execute(
        """
        SELECT e.id, e.title,
               SUM(CASE WHEN i.received THEN i.amount ELSE 0 END) AS recebido_parcelas
          FROM calendar_events e
          JOIN event_installments i ON i.event_id = e.id
         WHERE NOT EXISTS (SELECT 1 FROM event_payments p WHERE p.event_id = e.id)
           AND e.start_at >= %s
         GROUP BY e.id, e.title
        HAVING BOOL_OR(i.received)
        """,
        (asp - timedelta(days=90),),
    )
    for r in cur.fetchall():
        out.append({
            "entity_uid": f"calendar_event:{r['id']}",
            "code": "parcela_recebida_sem_comprovante", "severity": "atencao",
            "title": f"“{r['title']}”: parcela marcada como recebida sem nenhum comprovante anexado",
            "details": {"event_id": r["id"], "recebido_parcelas": _dec(r["recebido_parcelas"])},
        })

    # Espelha RecurringExpenseEntry.out_of_range (app/models.py): conta variável com valor
    # exato esperado, ou faixa de um lado só — cada referência vale sozinha.
    cur.execute(
        """
        SELECT ree.id, re.name, ree.amount, re.amount AS ref_exato,
               re.amount_min, re.amount_max, re.expense_type, ree.month_ref
          FROM recurring_expense_entries ree
          JOIN recurring_expenses re ON re.id = ree.recurring_id
         WHERE ree.paid_at >= %s AND ree.paid_at < %s
           AND ree.amount IS NOT NULL
           AND (
                (re.expense_type = 'variavel' AND re.amount IS NOT NULL
                 AND ree.amount <> re.amount)
             OR (re.amount_min IS NOT NULL AND ree.amount < re.amount_min)
             OR (re.amount_max IS NOT NULL AND ree.amount > re.amount_max)
           )
        """,
        (a, b),
    )
    for r in cur.fetchall():
        if r["amount_min"] is not None or r["amount_max"] is not None:
            faixa = f"faixa R$ {r['amount_min'] or '—'}–{r['amount_max'] or '—'}"
        else:
            faixa = f"esperado R$ {r['ref_exato']}"
        out.append({
            "entity_uid": f"recurring_expense_entry:{r['id']}",
            "code": "recorrente_fora_da_faixa", "severity": "atencao",
            "title": f"“{r['name']}” ({r['month_ref']}): R$ {r['amount']} fora do previsto ({faixa})",
            "details": {"entry_id": r["id"], "amount": _dec(r["amount"])},
        })

    cur.execute(
        """
        SELECT n.id, n.transaction_nsu, n.recheck_result, n.outcome, n.created_at
          FROM virtual_payment_notifications n
         WHERE n.created_at >= %s AND n.created_at < %s
           AND (n.recheck_result = 'divergent' OR n.outcome IN ('duplicado', 'orfao'))
        """,
        (asp, bsp),
    )
    for r in cur.fetchall():
        out.append({
            "code": "loja_virtual_divergente", "severity": "atencao",
            "title": (f"Loja virtual: notificação {r['transaction_nsu']} com "
                      f"recheck={r['recheck_result']} / outcome={r['outcome']}"),
            "details": {"notification_id": r["id"]},
        })
    return out


# ── Saídas sem comprovante possível (listadas, não auditáveis) ───────────────


def collect_nao_auditaveis(cur, win: tuple[datetime, datetime]) -> list[dict]:
    """Pagamentos marcados como pagos que não têm campo de anexo no sistema."""
    a, b = _naive_utc(win[0]), _naive_utc(win[1])
    # `start_at` (cachês/BV) é horário de parede SP — janela própria.
    asp, bsp = _naive_sp(win[0]), _naive_sp(win[1])
    out: list[dict] = []

    cur.execute(
        """
        SELECT cp.id, cp.event_title, cp.amount, cp.paid_at, u.name AS seller
          FROM commission_payments cp
          JOIN users u ON u.id = cp.seller_id
         WHERE cp.paid_at >= %s AND cp.paid_at < %s AND cp.status = 'pago'
        """,
        (a, b),
    )
    out += [{"tipo": "comissao", "quem": r["seller"], "referencia": r["event_title"],
             "amount": _dec(r["amount"])} for r in cur.fetchall()]

    cur.execute(
        """
        SELECT ree.id, re.name, ree.amount, ree.paid_at
          FROM recurring_expense_entries ree
          JOIN recurring_expenses re ON re.id = ree.recurring_id
         WHERE ree.paid_at >= %s AND ree.paid_at < %s
        """,
        (a, b),
    )
    out += [{"tipo": "recorrente", "quem": r["name"], "referencia": str(r["paid_at"])[:10],
             "amount": _dec(r["amount"])} for r in cur.fetchall()]

    cur.execute(
        """
        SELECT sp.id, sp.amount, sp.paid_at, sp.month_ref, u.name AS user_name
          FROM salary_payments sp
          JOIN users u ON u.id = sp.user_id
         WHERE sp.paid_at >= %s AND sp.paid_at < %s AND sp.payment_status = 'pago'
        """,
        (a, b),
    )
    out += [{"tipo": "salario", "quem": r["user_name"], "referencia": r["month_ref"],
             "amount": _dec(r["amount"])} for r in cur.fetchall()]

    cur.execute(
        """
        SELECT r.id, r.cache_value, r.travel_cache, t.full_name, e.title, e.start_at
          FROM event_roles r
          JOIN talents t ON t.id = r.talent_id
          JOIN calendar_events e ON e.id = r.event_id
         WHERE e.start_at >= %s AND e.start_at < %s
           AND r.payment_status NOT IN ('nao_pago')
           AND r.cache_value IS NOT NULL
        """,
        (asp, bsp),
    )
    out += [{"tipo": "cache", "quem": r["full_name"], "referencia": r["title"],
             "amount": _dec(r["cache_value"])} for r in cur.fetchall()]

    cur.execute(
        """
        SELECT ac.id, ac.bv_recipient, ac.amount_brl, e.title
          FROM event_acrescimos ac
          JOIN calendar_events e ON e.id = ac.event_id
         WHERE ac.is_bv IS TRUE AND ac.bv_payment_status = 'pago'
           AND e.start_at >= %s AND e.start_at < %s
        """,
        (asp, bsp),
    )
    out += [{"tipo": "bv", "quem": r["bv_recipient"], "referencia": r["title"],
             "amount": _dec(r["amount_brl"])} for r in cur.fetchall()]
    return out


# ── Números da semana e margens ──────────────────────────────────────────────


def collect_aggregates(cur, win: tuple[datetime, datetime]) -> dict:
    """Entradas × saídas da janela e margem por evento realizado na janela."""
    a, b = _naive_utc(win[0]), _naive_utc(win[1])
    asp, bsp = _naive_sp(win[0]), _naive_sp(win[1])
    agg: dict = {}

    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) AS s FROM event_payments"
        " WHERE created_at >= %s AND created_at < %s", (a, b))
    entradas_eventos = cur.fetchone()["s"]
    cur.execute(
        "SELECT COALESCE(SUM(total_value), 0) AS s FROM virtual_orders"
        " WHERE paid_at >= %s AND paid_at < %s", (asp, bsp))
    entradas_virtual = cur.fetchone()["s"]

    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) AS s FROM special_expenses"
        " WHERE approved_at >= %s AND approved_at < %s AND status = 'aprovado'", (a, b))
    saidas_gastos = cur.fetchone()["s"]
    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) AS s FROM commission_payments"
        " WHERE paid_at >= %s AND paid_at < %s AND status = 'pago'", (a, b))
    saidas_comissoes = cur.fetchone()["s"]
    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) AS s FROM recurring_expense_entries"
        " WHERE paid_at >= %s AND paid_at < %s", (a, b))
    saidas_recorrentes = cur.fetchone()["s"]
    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) AS s FROM salary_payments"
        " WHERE paid_at >= %s AND paid_at < %s AND payment_status = 'pago'", (a, b))
    saidas_salarios = cur.fetchone()["s"]
    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) AS s FROM salary_advances"
        " WHERE created_at >= %s AND created_at < %s", (a, b))
    saidas_adiantamentos = cur.fetchone()["s"]

    agg["entradas"] = {
        "eventos": _dec(entradas_eventos),
        "loja_virtual": _dec(entradas_virtual),
        "total": _dec(Decimal(entradas_eventos) + Decimal(entradas_virtual)),
    }
    agg["saidas"] = {
        "gastos_extras": _dec(saidas_gastos),
        "comissoes": _dec(saidas_comissoes),
        "recorrentes": _dec(saidas_recorrentes),
        "salarios": _dec(saidas_salarios),
        "adiantamentos": _dec(saidas_adiantamentos),
        "total": _dec(
            Decimal(saidas_gastos) + Decimal(saidas_comissoes)
            + Decimal(saidas_recorrentes) + Decimal(saidas_salarios)
            + Decimal(saidas_adiantamentos)
        ),
    }

    # Margem por evento: `start_at` é SP-naive; em grupos a venda fica no líder e os cachês
    # se espalham nos satélites (regra do próprio app, `_group_cost`) — o custo soma o grupo
    # inteiro e satélites (sale_value zerado) não entram na lista.
    cur.execute(
        """
        SELECT e.id, e.title, e.start_at, e.sale_value,
               COALESCE((SELECT SUM(COALESCE(r.cache_value, 0) + COALESCE(r.travel_cache, 0))
                           FROM event_roles r
                          WHERE r.event_id IN (SELECT s.id FROM calendar_events s
                                                WHERE s.id = e.id OR s.group_leader_id = e.id)
                            AND r.dismissed_at IS NULL), 0) AS custo_caches,
               COALESCE((SELECT SUM(g.amount) FROM special_expenses g
                          WHERE g.event_id IN (SELECT s.id FROM calendar_events s
                                                WHERE s.id = e.id OR s.group_leader_id = e.id)
                            AND g.status = 'aprovado'), 0) AS custo_gastos
          FROM calendar_events e
         WHERE e.start_at >= %s AND e.start_at < %s
           AND e.sale_value IS NOT NULL AND e.sale_value > 0
           AND e.is_cortesia_permuta IS NOT TRUE
           AND e.event_type != 'VIRTUAL'
           AND e.group_leader_id IS NULL
         ORDER BY e.start_at
        """,
        (asp, bsp),
    )
    margens = []
    for r in cur.fetchall():
        venda = Decimal(r["sale_value"])
        custo = Decimal(r["custo_caches"]) + Decimal(r["custo_gastos"])
        razao = (custo / venda) if venda else None
        margens.append({
            "event_id": r["id"], "title": r["title"],
            "data": str(r["start_at"].date()),
            "venda": _dec(venda), "custo": _dec(custo),
            "custo_sobre_venda": str(razao.quantize(Decimal("0.001"))) if razao is not None else None,
            "apertada": bool(razao is not None and razao >= config.MARGEM_CUSTO_MAXIMO),
        })
    agg["margens_eventos"] = margens
    return agg


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> int:
    """Roda a coleta e grava o manifesto da rodada."""
    ap = argparse.ArgumentParser(description="Coleta semanal do auditor financeiro")
    ap.add_argument("--local", action="store_true",
                    help="usa manto_local + arquivos de instance/uploads")
    ap.add_argument("--desde", help="início da janela (YYYY-MM-DD, horário SP)")
    args = ap.parse_args()

    config.ensure_dirs()
    store.set_mode(local=args.local)
    win = compute_window(args)
    # Itens/anomalias usam janela estendida (uploads atrasados são recolhidos; a memória por
    # hash evita retrabalho). Números da semana usam a janela contábil, sem sobreposição —
    # senão os 2 dias de margem contariam em dois relatórios seguidos.
    win_itens = (win[0] - timedelta(days=config.MARGEM_REACOLETA_DIAS), win[1])
    run_id = datetime.now(TZ_SP).strftime("%Y%m%d_%H%M%S")
    run_dir = config.RUNS_DIR / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "extracted").mkdir()

    print(f"[coleta] rodada {run_id} — janela {win[0].isoformat()} → {win[1].isoformat()}"
          f" ({'manto_local' if args.local else 'PRODUÇÃO (leitura)'})")

    conn = psycopg.connect(config.db_url(local=args.local), autocommit=True)
    try:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SET default_transaction_read_only = on")
            items = collect_items(cur, win_itens)
            anomalias_sql = collect_sql_anomalies(cur, win_itens)
            nao_auditaveis = collect_nao_auditaveis(cur, win)
            aggregates = collect_aggregates(cur, win)
    finally:
        conn.close()

    fetcher = FileFetcher(local=args.local, files_dir=run_dir / "files")
    needs = 0
    for item in items:
        rel = item["file_rel"]
        if not rel:
            item["status"] = "sem_anexo"
            continue
        path, err = fetcher.fetch(rel)
        if err:
            item["status"] = "arquivo_ausente"
            continue
        sha = _sha256(path)
        item["sha256"] = sha
        item["file_local"] = str(path)
        duplicado_de = store.sha_seen_elsewhere(item["entity_uid"], sha)
        if duplicado_de:
            item["duplicata_de"] = duplicado_de
        if store.already_audited(item["entity_uid"], sha):
            item["status"] = "ja_auditado"
        else:
            item["status"] = "needs_extraction"
            needs += 1

    manifest = {
        "run_id": run_id,
        "modo": "local" if args.local else "producao",
        "window": [win[0].isoformat(), win[1].isoformat()],
        "window_coleta": [win_itens[0].isoformat(), win_itens[1].isoformat()],
        "items": items,
        "anomalias_sql": anomalias_sql,
        "nao_auditaveis": nao_auditaveis,
        "aggregates": aggregates,
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    store.open_run(run_id, win[0].isoformat(), win[1].isoformat())

    print(f"[coleta] {len(items)} itens ({needs} precisam de leitura de comprovante), "
          f"{len(anomalias_sql)} anomalias SQL, {len(nao_auditaveis)} pagamentos sem anexo possível")
    print(f"[coleta] manifesto: {run_dir / 'manifest.json'}")
    for item in items:
        if item.get("status") == "needs_extraction":
            print(f"  LER: {item['entity_uid']} -> {item['file_local']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
