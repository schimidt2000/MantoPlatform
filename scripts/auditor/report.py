"""Relatório semanal do auditor financeiro (feature 221).

Monta o HTML do relatório a partir do manifesto + achados e (opcionalmente) envia por
e-mail via o endpoint do agente:

    python report.py --run 20260810_060012 --save-only      # só gera o HTML
    python report.py --run 20260810_060012 --send           # gera e envia (produção)
    python report.py --run 20260810_060012 --send --local   # envia via Flask local
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import requests

import config
import store

TZ_SP = ZoneInfo("America/Sao_Paulo")

_SEV_LABEL = {
    "critico": ("🔴 Precisa da sua atenção", "#b42318"),
    "atencao": ("🟡 Vale conferir", "#7a5800"),
    "info": ("ℹ️ Informativo", "#175cd3"),
    "ok": ("✅ Conferidos e OK", "#067647"),
}


def _brl(raw) -> str:
    """Formata '1234.56' como 'R$ 1.234,56' (mesma convenção da plataforma)."""
    if raw is None:
        return "—"
    value = Decimal(str(raw))
    inteiro, _, centavos = f"{value:,.2f}".partition(".")
    return "R$ " + inteiro.replace(",", ".") + "," + centavos


def _tabela_resumo(agg: dict) -> str:
    entradas, saidas = agg["entradas"], agg["saidas"]
    saldo = Decimal(entradas["total"]) - Decimal(saidas["total"])
    cor_saldo = "#067647" if saldo >= 0 else "#b42318"
    linhas = [
        ("Entradas de eventos", entradas["eventos"]),
        ("Entradas da loja virtual", entradas["loja_virtual"]),
        ("<b>Total de entradas</b>", entradas["total"]),
        ("Gastos extras aprovados", saidas["gastos_extras"]),
        ("Comissões pagas", saidas["comissoes"]),
        ("Despesas recorrentes", saidas["recorrentes"]),
        ("Salários", saidas["salarios"]),
        ("Adiantamentos", saidas["adiantamentos"]),
        ("<b>Total de saídas</b>", saidas["total"]),
    ]
    linhas_html = "".join(
        f"<tr><td style='padding:6px 12px;border-bottom:1px solid #eee'>{nome}</td>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #eee;text-align:right'>"
        f"{_brl(valor)}</td></tr>"
        for nome, valor in linhas
    )
    return (
        "<table style='border-collapse:collapse;width:100%;max-width:520px'>"
        f"{linhas_html}"
        f"<tr><td style='padding:8px 12px'><b>Saldo da semana</b></td>"
        f"<td style='padding:8px 12px;text-align:right;color:{cor_saldo}'>"
        f"<b>{_brl(saldo)}</b></td></tr></table>"
    )


def _bloco_achados(findings: list[dict]) -> str:
    html = ""
    for sev in ("critico", "atencao", "info", "ok"):
        grupo = [f for f in findings if f["severity"] == sev]
        if not grupo:
            continue
        label, cor = _SEV_LABEL[sev]
        if sev == "ok":
            html += (f"<h3 style='color:{cor};margin:24px 0 8px'>{label}: "
                     f"{len(grupo)} comprovantes</h3>")
            continue
        itens = "".join(
            f"<li style='margin:6px 0'>{f['title']}</li>" for f in grupo)
        html += (f"<h3 style='color:{cor};margin:24px 0 8px'>{label} ({len(grupo)})</h3>"
                 f"<ul style='padding-left:20px;margin:0'>{itens}</ul>")
    return html


def _bloco_nao_auditaveis(nao_auditaveis: list[dict]) -> str:
    if not nao_auditaveis:
        return ""
    total = sum(Decimal(x["amount"]) for x in nao_auditaveis if x["amount"])
    rotulos = {"comissao": "Comissão", "recorrente": "Despesa recorrente",
               "salario": "Salário", "cache": "Cachê", "bv": "BV"}
    linhas = "".join(
        f"<tr><td style='padding:4px 10px;border-bottom:1px solid #eee'>"
        f"{rotulos.get(x['tipo'], x['tipo'])}</td>"
        f"<td style='padding:4px 10px;border-bottom:1px solid #eee'>{x['quem'] or '—'}</td>"
        f"<td style='padding:4px 10px;border-bottom:1px solid #eee'>{x['referencia'] or ''}</td>"
        f"<td style='padding:4px 10px;border-bottom:1px solid #eee;text-align:right'>"
        f"{_brl(x['amount'])}</td></tr>"
        for x in nao_auditaveis
    )
    return (
        f"<h3 style='color:#475467;margin:24px 0 8px'>⚪ Pagos sem campo de comprovante "
        f"no sistema ({_brl(total)})</h3>"
        "<p style='margin:0 0 8px;color:#475467;font-size:13px'>Cachês, comissões, "
        "recorrentes e BV não têm anexo no sistema hoje — conferência manual.</p>"
        f"<table style='border-collapse:collapse;width:100%'>{linhas}</table>"
    )


def build_html(manifest: dict, findings: list[dict]) -> str:
    """HTML interno do relatório (a moldura padrão vem do `_html_wrap` do servidor)."""
    inicio = datetime.fromisoformat(manifest["window"][0]).astimezone(TZ_SP)
    fim = datetime.fromisoformat(manifest["window"][1]).astimezone(TZ_SP)
    criticos = sum(1 for f in findings if f["severity"] == "critico")
    manchete = ("Nenhum problema crítico encontrado. 🎉" if criticos == 0 else
                f"<b style='color:#b42318'>{criticos} ponto(s) crítico(s)</b> precisam da sua atenção.")
    return (
        f"<h2 style='margin:0 0 4px'>Auditoria financeira semanal</h2>"
        f"<p style='margin:0 0 16px;color:#475467'>Período: "
        f"{inicio.strftime('%d/%m %H:%M')} → {fim.strftime('%d/%m/%Y %H:%M')} "
        f"(horário de São Paulo)</p>"
        f"<p style='margin:0 0 16px'>{manchete}</p>"
        f"<h3 style='margin:0 0 8px'>📊 Números da semana</h3>"
        + _tabela_resumo(manifest["aggregates"])
        + _bloco_achados(findings)
        + _bloco_nao_auditaveis(manifest["nao_auditaveis"])
        + "<p style='margin:24px 0 0;color:#98a2b3;font-size:12px'>Gerado automaticamente "
          "pelo agente auditor (Claude Code) — verificação de consistência, não prova de "
          "autenticidade bancária.</p>"
    )


def main() -> int:
    """Gera (e opcionalmente envia) o relatório de uma rodada."""
    ap = argparse.ArgumentParser(description="Relatório semanal do auditor")
    ap.add_argument("--run", required=True)
    ap.add_argument("--send", action="store_true", help="envia por e-mail via endpoint")
    ap.add_argument("--save-only", action="store_true", help="só gera o HTML")
    ap.add_argument("--local", action="store_true", help="usa o Flask local no envio")
    args = ap.parse_args()

    run_dir = config.RUNS_DIR / args.run
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    findings = json.loads((run_dir / "findings.json").read_text(encoding="utf-8"))
    store.set_mode(local=manifest.get("modo") == "local")

    html = build_html(manifest, findings)
    out = run_dir / "relatorio.html"
    out.write_text(html, encoding="utf-8")
    print(f"[relatorio] HTML: {out}")

    if args.save_only or not args.send:
        return 0

    inicio = datetime.fromisoformat(manifest["window"][0]).astimezone(TZ_SP)
    criticos = sum(1 for f in findings if f["severity"] == "critico")
    alerta = f" — {criticos} crítico(s)" if criticos else " — tudo OK"
    subject = f"Auditoria financeira — semana de {inicio.strftime('%d/%m')}{alerta}"

    url = f"{config.base_url(args.local)}/api/audit-agent/{config.agent_token()}/report"
    resp = requests.post(url, json={"subject": subject, "html": html,
                                    "to": config.REPORT_RECIPIENTS}, timeout=60)
    resp.raise_for_status()
    body = resp.json()
    enviados = body.get("sent", 0)
    print(f"[relatorio] enviados: {enviados}, recusados: {body.get('rejected', [])}")
    store.close_run(manifest["run_id"], report_sent=bool(enviados))
    return 0 if enviados else 1


if __name__ == "__main__":
    sys.exit(main())
