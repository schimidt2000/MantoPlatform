"""Relatório semanal do auditor de marketing (feature 256).

    python report.py --run <run_id> [--send | --save-only] [--local]

Monta `runs/<id>/relatorio.html` (blocos na ordem do FR-020, gráficos em HTML/CSS — Gmail
não renderiza SVG embutido) e `resumo.md`; com `--send`, envia pelo `POST /report` do ERP e
fecha a rodada na memória local. Números vêm só dos arquivos lidos e do ERP: o que não veio
aparece como "sem dado", nunca como zero.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import config
import requests
import store

TZ_SP = ZoneInfo("America/Sao_Paulo")
TOP_N = 3
COR_BARRA = {"accent": "#544596", "gold": "#b1793a", "green": "#12662f", "red": "#c0392b", "muted": "#8b7fa8"}
SEVERIDADE_ROTULO = {"critico": "Crítico", "atencao": "Atenção", "info": "Informativo"}
SEVERIDADE_COR = {"critico": "#c0392b", "atencao": "#b1793a", "info": "#57575e"}
MESES_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
            "setembro", "outubro", "novembro", "dezembro"]


# ── formatação ────────────────────────────────────────────────────────────────


def _brl(valor: Decimal | float | str | None) -> str:
    """R$ no padrão brasileiro (Princípio IX); None vira '—'."""
    if valor is None:
        return "—"
    dec = Decimal(str(valor)).quantize(Decimal("0.01"))
    inteiro, centavos = f"{dec:,.2f}".split(".")
    return f"R$ {inteiro.replace(',', '.')},{centavos}"


def _num(valor: int | float | None) -> str:
    return "—" if valor is None else f"{int(valor):,}".replace(",", ".")


def _data(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y")
    except ValueError:
        return iso


def _esc(texto: object) -> str:
    return html.escape(str(texto if texto is not None else "—"))


def _slug_campanha(nome: str | None) -> str:
    texto = unicodedata.normalize("NFKD", (nome or "").strip().lower())
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", re.sub(r"[-_/]+", " ", texto)).strip()


def _dentro(iso_dia: str, inicio: date, fim: date) -> bool:
    try:
        return inicio <= date.fromisoformat(iso_dia[:10]) <= fim
    except ValueError:
        return False


# ── blocos HTML ───────────────────────────────────────────────────────────────


def _h2(titulo: str) -> str:
    return f'<h2 style="margin:28px 0 8px;font-size:17px;color:#1a1a1a">{_esc(titulo)}</h2>'


def _p(texto: str, muted: bool = False) -> str:
    cor = "#57575e" if muted else "#1a1a1a"
    return f'<p style="margin:4px 0 8px;font-size:14px;color:{cor}">{texto}</p>'


def _tabela(cabecalhos: list[str], linhas: list[list[str]]) -> str:
    th = "".join(f'<th style="text-align:left;padding:6px 8px;border-bottom:1px solid #e5e3ef;font-size:12px;color:#57575e">{_esc(c)}</th>' for c in cabecalhos)
    tr = "".join(
        "<tr>" + "".join(f'<td style="padding:6px 8px;border-bottom:1px solid #f0eef5;font-size:13px">{c}</td>' for c in linha) + "</tr>"
        for linha in linhas
    )
    return f'<table cellpadding="0" cellspacing="0" style="border-collapse:collapse;width:100%">{th and "<tr>" + th + "</tr>"}{tr}</table>'


def _barras(itens: list[tuple[str, Decimal | int, str]], cor: str = "accent") -> str:
    """Barras horizontais em tabela (renderiza em Gmail/Outlook): (rótulo, valor, texto)."""
    if not itens:
        return _p("sem dado", muted=True)
    maximo = max((Decimal(str(v)) for _, v, _ in itens), default=Decimal(1)) or Decimal(1)
    linhas = []
    for rotulo, valor, texto in itens:
        pct = max(2, int(Decimal(str(valor)) / maximo * 100))
        linhas.append(
            f'<tr><td style="padding:3px 8px 3px 0;font-size:12px;white-space:nowrap;width:38%">{_esc(rotulo)}</td>'
            f'<td style="padding:3px 0"><table cellpadding="0" cellspacing="0" style="width:100%"><tr>'
            f'<td style="width:{pct}%;background:{COR_BARRA[cor]};height:12px;border-radius:6px"></td>'
            f'<td style="padding-left:6px;font-size:12px;white-space:nowrap">{_esc(texto)}</td></tr></table></td></tr>'
        )
    return f'<table cellpadding="0" cellspacing="0" style="width:100%">{"".join(linhas)}</table>'


# ── cálculo dos blocos ────────────────────────────────────────────────────────


def gasto_por_campanha(campanhas: list[dict], inicio: date, fim: date) -> dict[str, dict]:
    """Soma gasto/cliques por campanha na janela usando só linhas diárias (ou agregadas sem diárias)."""
    diarias = [c for c in campanhas if c["period_start"] == c["period_end"]]
    agregadas = [c for c in campanhas if c["period_start"] != c["period_end"]]
    dias_cobertos = {(c["platform"], c["campaign_id"], c["period_start"]) for c in diarias}
    saida: dict[str, dict] = {}
    for c in diarias + [a for a in agregadas if not any((a["platform"], a["campaign_id"], d) in dias_cobertos for d in (a["period_start"],))]:
        if not _dentro(c["period_start"], inicio, fim) and not _dentro(c["period_end"], inicio, fim):
            continue
        chave = f"{c['platform']}|{c['campaign_name']}"
        item = saida.setdefault(chave, {"platform": c["platform"], "name": c["campaign_name"], "spend": Decimal(0),
                                        "clicks": 0, "currency": c.get("currency", "BRL"), "leads": 0, "events": 0})
        item["spend"] += Decimal(str(c.get("spend") or 0))
        item["clicks"] += int(c.get("clicks") or 0)
    return saida


_ORIGEM_PLATAFORMA = {
    "google": "Google Ads", "adwords": "Google Ads", "googleads": "Google Ads",
    "ig": "Meta Ads", "instagram": "Meta Ads", "fb": "Meta Ads", "facebook": "Meta Ads", "meta": "Meta Ads",
}


def _plataforma_da_origem(utm_source: str | None) -> str | None:
    return _ORIGEM_PLATAFORMA.get((utm_source or "").strip().lower())


def _escolher_campanha(candidatas: list[dict], utm_source: str | None) -> dict | None:
    """Mesma campanha em duas plataformas: `utm_source` decide; sem pista, a de maior gasto."""
    if not candidatas:
        return None
    if len(candidatas) == 1:
        return candidatas[0]
    plataforma = _plataforma_da_origem(utm_source)
    da_plataforma = [c for c in candidatas if c["platform"] == plataforma]
    return da_plataforma[0] if len(da_plataforma) == 1 else max(candidatas, key=lambda c: c["spend"])


def atribuir_leads(campanhas: dict[str, dict], contexto: dict) -> int:
    """Conta leads/eventos por campanha casando `utm_campaign` normalizado com o nome; devolve total de leads."""
    por_slug: dict[str, list[dict]] = {}
    for c in campanhas.values():
        por_slug.setdefault(_slug_campanha(c["name"]), []).append(c)
    total = 0
    for cliente in contexto.get("attributed_clients", []):
        total += 1
        alvo = _escolher_campanha(por_slug.get(_slug_campanha(cliente.get("utm_campaign")), []), cliente.get("utm_source"))
        if alvo is not None:
            alvo["leads"] += 1
            alvo["events"] += len(cliente.get("events", []))
    return total


def bloco_manchete(campanhas: dict[str, dict], total_leads: int, contexto: dict, posts: list[dict]) -> tuple[str, str]:
    """Manchete = leads por campanha (decisão do dono); sem atribuição cai para alcance com o motivo."""
    if total_leads:
        gasto = sum((c["spend"] for c in campanhas.values()), Decimal(0))
        cpl = (gasto / total_leads).quantize(Decimal("0.01")) if gasto else None
        titulo = f"{total_leads} lead(s) na semana — custo por lead {_brl(cpl)}"
        return titulo, _p(f"<strong>{_esc(titulo)}</strong>") + _p(f"Gasto em anúncios na janela: {_brl(gasto)}.", muted=True)
    alcance = sum(int(p.get("reach") or 0) for p in posts)
    motivo = "nenhum lead da janela veio com utm_campaign (import do CRM ou utms das campanhas ausentes)"
    titulo = f"Alcance dos posts medidos: {_num(alcance)}"
    return titulo, _p(f"<strong>{_esc(titulo)}</strong>") + _p(f"Manchete de leads indisponível — {motivo}.", muted=True)


def bloco_atribuicao(campanhas: dict[str, dict], contexto: dict, mes: str, gasto_mes: Decimal) -> str:
    linhas = []
    for c in sorted(campanhas.values(), key=lambda x: -x["spend"]):
        cpl = _brl(c["spend"] / c["leads"]) if c["leads"] else "—"
        cpe = _brl(c["spend"] / c["events"]) if c["events"] else "—"
        linhas.append([_esc(c["platform"]), _esc(c["name"]), _brl(c["spend"]), _num(c["leads"]), cpl, _num(c["events"]), cpe])
    saida = _tabela(["Plataforma", "Campanha", "Gasto", "Leads", "Custo/lead", "Eventos", "Custo/evento"], linhas) if linhas else _p("sem campanhas na janela", muted=True)
    novos = next((m for m in contexto.get("new_clients_by_month", []) if m["month"] == mes), None)
    if novos and novos["total"]:
        cac = (gasto_mes / novos["total"]).quantize(Decimal("0.01"))
        saida += _p(f"Custo de aquisição de {MESES_PT[int(mes[5:]) - 1]}: <strong>{_brl(cac)}</strong> "
                    f"({_brl(gasto_mes)} em anúncios ÷ {novos['total']} clientes novos).")
    else:
        saida += _p(f"Custo de aquisição de {MESES_PT[int(mes[5:]) - 1]}: sem clientes novos registrados no mês.", muted=True)
    return saida


def bloco_gasto(campanhas: dict[str, dict]) -> str:
    por_plataforma: dict[str, Decimal] = defaultdict(Decimal)
    for c in campanhas.values():
        por_plataforma[c["platform"]] += c["spend"]
    saida = _barras([(p, v, _brl(v)) for p, v in sorted(por_plataforma.items())], "accent")
    itens = [(f"{c['platform']} · {c['name']}", c["spend"],
              f"{_brl(c['spend'])}" + (f" · CPC {_brl(c['spend'] / c['clicks'])}" if c["clicks"] else ""))
             for c in sorted(campanhas.values(), key=lambda x: -x["spend"])]
    return saida + "<div style='height:8px'></div>" + _barras(itens, "gold")


def bloco_posts_metas(contexto: dict, inicio: date, fim: date) -> str:
    publicados = [p for p in contexto.get("posts", []) if p.get("publish_date") and _dentro(p["publish_date"], inicio, fim)]
    saida = _p(f"{len(publicados)} post(s) do painel publicados na janela." if publicados else "Nenhum post do painel marcado como publicado na janela.", muted=not publicados)
    if publicados:
        saida += _tabela(["Data", "Título", "Plataforma", "Link"],
                         [[_data(p["publish_date"]), _esc(p["title"]), _esc(p.get("platform")),
                           (f'<a href="{_esc(p["permalink"])}">abrir</a>' if p.get("permalink") else "<em>sem link</em>")] for p in publicados])
    atrasadas = [g for g in contexto.get("goals", []) if g.get("status") == "delayed"]
    em_dia = [g for g in contexto.get("goals", []) if g.get("status") == "on_track"]
    if atrasadas:
        saida += _p("Metas atrasadas: " + ", ".join(f"<strong>{_esc(g['name'])}</strong>" for g in atrasadas) + ".")
    if em_dia:
        saida += _p("Em dia: " + ", ".join(_esc(g["name"]) for g in em_dia) + ".", muted=True)
    if not contexto.get("goals"):
        saida += _p("Nenhuma meta de frequência cadastrada.", muted=True)
    return saida


def _nome_post(post: dict, contexto: dict, linked: dict | None = None) -> str:
    """Título do card quando o servidor casou o post (por link OU por data); senão legenda."""
    casado = (linked or {}).get(post.get("platform_post_id"))
    if casado and casado.get("title"):
        return casado["title"]
    alvo = (post.get("permalink") or "").lower().split("?")[0].rstrip("/")
    for card in contexto.get("posts", []):
        if card.get("permalink") and card["permalink"].lower().split("?")[0].rstrip("/") == alvo and alvo:
            return card["title"]
    return (post.get("caption") or post.get("platform_post_id") or "?")[:60]


def bloco_ranking(posts: list[dict], contexto: dict, linked: dict | None = None) -> str:
    if not posts:
        return _p("sem export de conteúdo nesta rodada", muted=True)
    ultima = {}
    for p in posts:  # última fotografia de cada post
        if p["platform_post_id"] not in ultima or p["snapshot_date"] > ultima[p["platform_post_id"]]["snapshot_date"]:
            ultima[p["platform_post_id"]] = p
    lista = list(ultima.values())
    eng = lambda p: sum(int(p.get(k) or 0) for k in ("likes", "comments", "saves", "shares"))  # noqa: E731
    por_alcance = sorted(lista, key=lambda p: int(p.get("reach") or 0), reverse=True)
    por_eng = sorted(lista, key=eng, reverse=True)
    saida = _p("<strong>Por alcance</strong>")
    saida += _barras([(_nome_post(p, contexto, linked), int(p.get("reach") or 0), _num(p.get("reach"))) for p in por_alcance[:TOP_N]], "green")
    if len(por_alcance) > TOP_N:
        saida += _p("Menor alcance: " + ", ".join(f"{_esc(_nome_post(p, contexto, linked))} ({_num(p.get('reach'))})" for p in por_alcance[-TOP_N:]), muted=True)
    saida += _p("<strong>Por engajamento</strong> (curtidas + comentários + salvamentos + compartilhamentos)")
    saida += _barras([(_nome_post(p, contexto, linked), eng(p), _num(eng(p))) for p in por_eng[:TOP_N]], "accent")
    return saida


def bloco_seguidores(conta: list[dict]) -> str:
    com_seg = sorted([c for c in conta if c.get("followers") is not None], key=lambda c: c["metric_date"])
    if not com_seg:
        return _p("sem export da conta nesta rodada", muted=True)
    primeiro, ultimo = com_seg[0], com_seg[-1]
    delta = int(ultimo["followers"]) - int(primeiro["followers"])
    sinal = "+" if delta >= 0 else ""
    return _p(f"<strong>{_num(ultimo['followers'])}</strong> seguidores em {_data(ultimo['metric_date'])} "
              f"({sinal}{delta} desde {_data(primeiro['metric_date'])}).") + \
        _barras([(_data(c["metric_date"]), int(c.get("reach") or 0), _num(c.get("reach"))) for c in com_seg], "muted")


def bloco_financeiro(resultado: dict) -> str:
    acoes = resultado.get("ad_spend", [])
    if not acoes:
        return _p("Nenhum gasto de anúncios apurado nesta rodada.", muted=True)
    rotulo = {"created": "criado (pendente)", "updated": "atualizado (pendente)", "frozen_ok": "aprovado — confere",
              "frozen_divergent": "aprovado — DIVERGE", "skipped_manual": "já lançado à mão", "skipped_currency": "moeda ≠ BRL"}
    linhas = [[_esc(a.get("platform")), _esc(a.get("month_ref")), _esc(rotulo.get(a.get("action"), a.get("action"))),
               _brl(a.get("amount") or a.get("reported_amount")), _brl(a.get("erp_amount")) if a.get("erp_amount") else "—"] for a in acoes]
    return _tabela(["Plataforma", "Mês", "Situação", "Reportado", "No ERP"], linhas) + \
        _p(f"Reembolso ao titular do cartão previsto para o dia {config.REIMBURSEMENT_DAY}; anexar a fatura antes de aprovar.", muted=True)


def bloco_achados(findings: list[dict], codigos: set[str] | None = None, excluir: set[str] | None = None) -> str:
    itens = [f for f in findings if (codigos is None or f["code"] in codigos) and (excluir is None or f["code"] not in excluir)]
    if not itens:
        return _p("nada a apontar", muted=True)
    return "".join(
        f'<p style="margin:3px 0;font-size:13px"><span style="color:{SEVERIDADE_COR.get(f["severity"], "#57575e")};font-weight:600">'
        f'{SEVERIDADE_ROTULO.get(f["severity"], f["severity"])}</span> — {_esc(f["title"])}</p>'
        for f in itens
    )


# ── montagem ──────────────────────────────────────────────────────────────────


def build_html(manifest: dict, normalizado: dict, contexto: dict, resultado: dict, findings: list[dict]) -> tuple[str, str]:
    inicio_dt = datetime.fromisoformat(manifest["window"][0]).astimezone(TZ_SP)
    fim_dt = datetime.fromisoformat(manifest["window"][1]).astimezone(TZ_SP)
    inicio, fim = inicio_dt.date(), fim_dt.date()
    campanhas_todas = normalizado.get("campaign_metrics", [])
    campanhas = gasto_por_campanha(campanhas_todas, inicio, fim)
    total_leads = atribuir_leads(campanhas, contexto)
    mes = fim.strftime("%Y-%m")
    gasto_mes = sum((c["spend"] for c in gasto_por_campanha(campanhas_todas, fim.replace(day=1), fim).values()), Decimal(0))
    posts = normalizado.get("post_metrics", [])
    manchete, html_manchete = bloco_manchete(campanhas, total_leads, contexto, posts)
    dias = (fim - inicio).days
    aviso_janela = _p(f"Atenção: esta rodada cobre {dias} dias (mais de uma semana) — janela desde a última rodada enviada.", muted=True) if dias > config.LONG_WINDOW_DAYS else ""

    corpo = (
        f'<p style="margin:0 0 4px;font-size:12px;color:#57575e">Rodada {_esc(manifest["run_id"])} · '
        f'{inicio_dt.strftime("%d/%m/%Y")} – {fim_dt.strftime("%d/%m/%Y")}</p>'
        + aviso_janela
        + _h2("Manchete da semana") + html_manchete
        + _h2("Leads e eventos por campanha") + bloco_atribuicao(campanhas, contexto, mes, gasto_mes)
        + _h2("Gasto por plataforma e por campanha") + bloco_gasto(campanhas)
        + _h2("Posts publicados × metas de frequência") + bloco_posts_metas(contexto, inicio, fim)
        + _h2("Melhores e piores posts") + bloco_ranking(posts, contexto, resultado.get("post_links", {}).get("linked"))
        + _h2("Seguidores e alcance da conta") + bloco_seguidores(normalizado.get("account_metrics", []))
        + _h2("Conferência financeira (reembolso de anúncios)") + bloco_financeiro(resultado)
        + _h2("O que ficou sem dado") + bloco_achados(findings, codigos={"sem_arquivo", "arquivo_rejeitado", "post_nao_vinculado", "sem_atribuicao"})
        + _h2("Outros achados") + bloco_achados(findings, excluir={"sem_arquivo", "arquivo_rejeitado", "post_nao_vinculado", "sem_atribuicao", "nota_leitura"})
    )
    return manchete, corpo


def build_resumo(manifest: dict, manchete: str, resultado: dict, findings: list[dict]) -> str:
    criticos = [f for f in findings if f["severity"] == "critico"]
    linhas = [f"# Auditoria de marketing — rodada {manifest['run_id']}", "", f"**Manchete:** {manchete}", ""]
    linhas.append(f"**Críticos:** {len(criticos)}" + ("" if not criticos else " — " + "; ".join(f["title"] for f in criticos)))
    for a in resultado.get("ad_spend", []):
        linhas.append(f"- Reembolso {a.get('platform')} {a.get('month_ref')}: {a.get('action')} {_brl(a.get('amount') or a.get('reported_amount'))}")
    sem_dado = [f["title"] for f in findings if f["code"] in {"sem_arquivo", "arquivo_rejeitado"}]
    if sem_dado:
        linhas += ["", "**Sem dado:**"] + [f"- {t}" for t in sem_dado]
    return "\n".join(linhas) + "\n"


def enviar(html_corpo: str, assunto: str, run_id: str, local: bool) -> int:
    url = f"{config.base_url(local)}/api/marketing-agent/{config.agent_token()}/report"
    resp = requests.post(url, json={"subject": assunto, "html": html_corpo, "to": config.REPORT_RECIPIENTS, "run_id": run_id},
                         timeout=config.HTTP_TIMEOUT)
    resp.raise_for_status()
    body = resp.json()
    print(f"[relatorio] enviados: {body.get('sent', 0)}, recusados: {body.get('rejected', [])}")
    return int(body.get("sent", 0))


def _carrega(run_dir: Path, nome: str, padrao):
    caminho = run_dir / nome
    return json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else padrao


def _carregar_rodada(run_dir: Path) -> tuple[dict, dict, dict, dict, list[dict]]:
    manifest = _carrega(run_dir, "manifest.json", None)
    if manifest is None:
        raise FileNotFoundError("manifest.json não encontrado — rode collect.py antes")
    return (manifest, _carrega(run_dir, "normalizado.json", {}), _carrega(run_dir, "contexto.json", {}),
            _carrega(run_dir, "resultado.json", {}), _carrega(run_dir, "findings.json", []))


def _enviar_e_fechar(manifest: dict, corpo: str, manchete: str, findings: list[dict], local: bool) -> int:
    inicio = datetime.fromisoformat(manifest["window"][0]).astimezone(TZ_SP)
    criticos = sum(1 for f in findings if f["severity"] == "critico")
    assunto = f"Marketing — semana de {inicio.strftime('%d/%m')}: {manchete}" + (f" — {criticos} crítico(s)" if criticos else "")
    try:
        enviados = enviar(corpo, assunto, manifest["run_id"], local)
    except requests.RequestException as exc:
        print(f"[relatorio] envio falhou: {exc}")
        return 1
    store.close_run(manifest["run_id"], report_sent=bool(enviados))
    print(f"[relatorio] rodada fechada em {datetime.now(UTC).isoformat()}")
    return 0 if enviados else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Relatório semanal do auditor de marketing")
    ap.add_argument("--run", required=True)
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--save-only", action="store_true")
    ap.add_argument("--local", action="store_true")
    args = ap.parse_args()

    store.set_mode(args.local)
    run_dir = config.RUNS_DIR / args.run
    try:
        manifest, normalizado, contexto, resultado, findings = _carregar_rodada(run_dir)
    except FileNotFoundError as exc:
        print(f"[relatorio] {exc}")
        return 1
    manchete, corpo = build_html(manifest, normalizado, contexto, resultado, findings)
    (run_dir / "relatorio.html").write_text(corpo, encoding="utf-8")
    (run_dir / "resumo.md").write_text(build_resumo(manifest, manchete, resultado, findings), encoding="utf-8")
    print(f"[relatorio] HTML: {run_dir / 'relatorio.html'}")
    if args.save_only or not args.send:
        return 0
    return _enviar_e_fechar(manifest, corpo, manchete, findings, args.local)


if __name__ == "__main__":
    sys.exit(main())
