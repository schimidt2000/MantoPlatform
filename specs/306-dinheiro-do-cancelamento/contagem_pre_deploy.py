"""Contagem do que a feature 306 encontra no banco — SÓ LEITURA, no espelho e na produção.

Roda no Setup/primeira rodada (espelho), no Polimento (espelho) e no dia do deploy (produção, por
SSH, antes do push). Não chama `create_app()` nem importa `app`: lê o `DATABASE_URL` e abre a
transação com `default_transaction_read_only=on`, então nenhuma consulta escreve. Usa `psycopg` ou
`psycopg2` (a produção só tem o 2).

A saída traz quantidades, R$ e ids — nunca nome, e-mail ou PIX —, porque vai versionada para a pasta
da feature (quickstart §2). O passado fica quieto: a contagem não lista pago a menos nem a mais.

Uso::

    python specs/306-dinheiro-do-cancelamento/contagem_pre_deploy.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

CATEGORIAS = (
    "Figurino",
    "Escritório",
    "Marketing",
    "Manutenção",
    "Devolução a cliente",
    "Outros",
    "Multa de cancelamento",
)
DEVOLUCAO = "Devolução a cliente"
PRESENCA = "Técnico de Som (Presença)"

CONSULTAS: list[tuple[str, str]] = [
    # ── eventos ──
    ("eventos cancelados", "SELECT count(*) FROM calendar_events WHERE cancelled_at IS NOT NULL"),
    (
        "cancelados sem venda nem comprovante",
        "SELECT count(*) FROM calendar_events e WHERE e.cancelled_at IS NOT NULL "
        "AND coalesce(e.sale_value, 0) = 0 AND NOT EXISTS (SELECT 1 FROM event_payments p "
        "WHERE p.event_id = e.id AND coalesce(p.amount, 0) > 0)",
    ),
    ("marcados pela 303", "SELECT count(*) FROM calendar_events WHERE google_missing_since IS NOT NULL"),
    (
        "grupos (principais)",
        "SELECT count(DISTINCT group_leader_id) FROM calendar_events WHERE group_leader_id IS NOT NULL",
    ),
    (
        "grupos com dia futuro",
        "SELECT count(DISTINCT group_leader_id) FROM calendar_events WHERE group_leader_id IS NOT NULL "
        "AND start_at >= now()",
    ),
    (
        "grupos com o principal fora do 1º dia",
        "SELECT count(*) FROM calendar_events l WHERE EXISTS (SELECT 1 FROM calendar_events s "
        "WHERE s.group_leader_id = l.id AND s.start_at < l.start_at)",
    ),
    (
        "grupos cruzando o mês",
        "SELECT count(*) FROM calendar_events l WHERE EXISTS (SELECT 1 FROM calendar_events s "
        "WHERE s.group_leader_id = l.id AND date_trunc('month', s.start_at) <> "
        "date_trunc('month', l.start_at))",
    ),
    (
        "satélites com comissão própria (ids)",
        "SELECT coalesce(string_agg(DISTINCT cp.event_id::text, ','), '-') FROM commission_payments cp "
        "JOIN calendar_events e ON e.id = cp.event_id WHERE e.group_leader_id IS NOT NULL "
        "AND cp.status <> 'cancelado'",
    ),
    (
        "ensaios futuros ligados",
        "SELECT count(*) FROM calendar_events WHERE event_type = 'ENSAIO' AND parent_event_id IS NOT NULL "
        "AND start_at >= now()",
    ),
    (
        "shows futuros com ensaio",
        "SELECT count(DISTINCT parent_event_id) FROM calendar_events WHERE event_type = 'ENSAIO' "
        "AND parent_event_id IS NOT NULL AND start_at >= now()",
    ),
    (
        "escalados de shows futuros com ensaio",
        "SELECT count(*) FROM event_roles r WHERE r.talent_id IS NOT NULL AND r.event_id IN "
        "(SELECT parent_event_id FROM calendar_events WHERE event_type = 'ENSAIO' AND start_at >= now())",
    ),
    (
        "eventos futuros com cachê pago",
        "SELECT count(DISTINCT r.event_id) FROM event_roles r JOIN calendar_events e ON e.id = r.event_id "
        "WHERE r.talent_id IS NOT NULL AND r.payment_status IN ('pago', 'no_banco') "
        f"AND r.character_name <> '{PRESENCA}' AND e.start_at >= now()",
    ),
    (
        "escalados sem e-mail (eventos futuros)",
        "SELECT count(*) FROM event_roles r JOIN calendar_events e ON e.id = r.event_id "
        "JOIN talents t ON t.id = r.talent_id WHERE e.start_at >= now() "
        "AND coalesce(t.email_contact, '') = ''",
    ),
    (
        "talentos escalados sem PIX (eventos futuros)",
        "SELECT count(DISTINCT t.id) FROM event_roles r JOIN calendar_events e ON e.id = r.event_id "
        "JOIN talents t ON t.id = r.talent_id WHERE e.start_at >= now() AND coalesce(t.pix_key, '') = ''",
    ),
    # ── dinheiro recebido ──
    ("comprovantes sem valor", "SELECT count(*) FROM event_payments WHERE amount IS NULL"),
    (
        "eventos com pago maior que a venda",
        "SELECT count(*) FROM calendar_events e WHERE coalesce(e.sale_value, 0) > 0 AND "
        "(SELECT coalesce(sum(p.amount), 0) FROM event_payments p WHERE p.event_id = e.id) > e.sale_value",
    ),
    # ── comissões ──
    ("comissões no_banco", "SELECT count(*) FROM commission_payments WHERE status = 'no_banco'"),
    (
        "comissões no_banco por mês",
        "SELECT coalesce(string_agg(m || ':' || n, ', '), '-') FROM (SELECT to_char(coalesce("
        "payable_from, sale_date), 'YYYY-MM') AS m, count(*) AS n FROM commission_payments WHERE "
        "status = 'no_banco' GROUP BY 1 ORDER BY 1) x",
    ),
    (
        "comissões a_pagar negativas com evento",
        "SELECT count(*) FROM commission_payments WHERE status = 'a_pagar' AND amount < 0 "
        "AND event_id IS NOT NULL",
    ),
    (
        "estornos órfãos a_pagar",
        "SELECT count(*) FROM commission_payments WHERE status = 'a_pagar' AND event_id IS NULL "
        "AND original_id IS NOT NULL",
    ),
    (
        "linhas vivas de evento cancelado",
        "SELECT count(*) FROM commission_payments cp JOIN calendar_events e ON e.id = cp.event_id "
        "WHERE e.cancelled_at IS NOT NULL AND cp.status <> 'cancelado'",
    ),
    (
        "linhas que o resync alcança",
        "SELECT count(*) FROM commission_payments WHERE status = 'a_pagar' AND event_id IS NOT NULL "
        "AND amount >= 0",
    ),
    ("comissões pagas", "SELECT count(*) FROM commission_payments WHERE status = 'pago'"),
    (
        "comissões pagas de evento futuro",
        "SELECT count(*) FROM commission_payments cp JOIN calendar_events e ON e.id = cp.event_id "
        "WHERE cp.status = 'pago' AND e.start_at >= now()",
    ),
    ("comissões com original_id", "SELECT count(*) FROM commission_payments WHERE original_id IS NOT NULL"),
    (
        "ciclos abertos de soma zero com linha de valor (vendedor:ciclo)",
        "SELECT coalesce(string_agg(chave, ', '), '-') FROM (SELECT seller_id::text || ':' || "
        "to_char(coalesce(payable_from, sale_date, created_at::date), 'YYYY-MM') AS chave FROM "
        "commission_payments WHERE status IN ('a_pagar', 'no_banco') GROUP BY seller_id, "
        "to_char(coalesce(payable_from, sale_date, created_at::date), 'YYYY-MM') "
        "HAVING sum(amount) = 0 AND bool_or(amount <> 0)) x",
    ),
    # ── gastos e devoluções ──
    ("gastos aprovados com evento", "SELECT count(*) FROM special_expenses WHERE status = 'aprovado' AND event_id IS NOT NULL"),
    (
        "devoluções com tipo nulo",
        f"SELECT count(*) FROM special_expenses WHERE category = '{DEVOLUCAO}' AND disbursement_type IS NULL",
    ),
    (
        "devoluções pendentes ligadas a evento",
        f"SELECT count(*) FROM special_expenses WHERE category = '{DEVOLUCAO}' AND status = 'pendente' "
        "AND event_id IS NOT NULL",
    ),
    (
        "devoluções ligadas a evento vivo (vendas vivas com devolução à mão)",
        f"SELECT count(*) FROM special_expenses s JOIN calendar_events e ON e.id = s.event_id "
        f"WHERE s.category = '{DEVOLUCAO}' AND e.cancelled_at IS NULL",
    ),
    (
        "gasto aprovado com categoria fora de CATEGORIES",
        "SELECT count(*) FROM special_expenses WHERE status = 'aprovado' AND category NOT IN ("
        + ", ".join(f"'{c}'" for c in CATEGORIAS)
        + ")",
    ),
    # ── BV ──
    (
        "BV em satélite",
        "SELECT count(*) FROM event_acrescimos a JOIN calendar_events e ON e.id = a.event_id "
        "WHERE a.is_bv AND e.group_leader_id IS NOT NULL",
    ),
    (
        "BV não pago de cancelado legado",
        "SELECT count(*) FROM event_acrescimos a JOIN calendar_events e ON e.id = a.event_id "
        "WHERE a.is_bv AND e.cancelled_at IS NOT NULL AND coalesce(a.bv_payment_status, 'nao_pago') = "
        "'nao_pago'",
    ),
    (
        "BV não pago sem recebedor ou PIX",
        "SELECT count(*) FROM event_acrescimos WHERE is_bv AND coalesce(bv_payment_status, 'nao_pago') = "
        "'nao_pago' AND (coalesce(bv_recipient, '') = '' OR coalesce(bv_pix, '') = '')",
    ),
    # ── usuários e banco ──
    (
        "usuários ativos por papel (FINANCEIRO, ENSAIO, CASTING, SUPERADMIN)",
        "SELECT coalesce(string_agg(r.name || ':' || n, ', '), '-') FROM (SELECT r.name, count(*) AS n "
        "FROM users u JOIN user_roles ur ON ur.user_id = u.id JOIN roles r ON r.id = ur.role_id "
        "WHERE u.is_active AND r.name IN ('FINANCEIRO', 'ENSAIO', 'CASTING', 'SUPERADMIN') "
        "GROUP BY r.name ORDER BY r.name) r",
    ),
    ("alembic_version", "SELECT string_agg(version_num, ',') FROM alembic_version"),
]


def _url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        arquivo = Path(__file__).resolve().parents[2] / ".local-db-url"
        url = arquivo.read_text(encoding="utf-8").strip()
    return url.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )


def _conectar(url: str):
    try:
        import psycopg

        return psycopg.connect(url, options="-c default_transaction_read_only=on")
    except ImportError:
        import psycopg2

        return psycopg2.connect(url, options="-c default_transaction_read_only=on")


def main() -> int:
    conn = _conectar(_url())
    try:
        cur = conn.cursor()
        cur.execute("SHOW default_transaction_read_only")
        if cur.fetchone()[0] != "on":
            print("A transação não abriu só leitura: abortado.")
            return 2
        for rotulo, sql in CONSULTAS:
            try:
                cur.execute(sql)
                valor = cur.fetchone()[0]
            except Exception as exc:  # noqa: BLE001 — uma tabela que ainda não existe não para a contagem
                conn.rollback()
                cur = conn.cursor()
                valor = f"(erro: {type(exc).__name__})"
            print(f"{rotulo} | {valor}")
        for tabela in ("event_cancellations", "event_cancellation_bvs", "event_cancellation_elenco"):
            try:
                cur.execute(f"SELECT count(*) FROM {tabela}")
                print(f"{tabela} | {cur.fetchone()[0]}")
            except Exception:  # noqa: BLE001 — antes da migration a tabela não existe
                conn.rollback()
                cur = conn.cursor()
                print(f"{tabela} | (não existe)")
    finally:
        conn.rollback()
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
