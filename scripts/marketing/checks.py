"""Achados da rodada do auditor de marketing (feature 256).

    python checks.py --run <run_id> [--local]

Consolida em `runs/<id>/findings.json`: arquivos rejeitados/ausentes, posts sem card, metas
atrasadas, gastos gerados sem comprovante, achados do servidor (divergência de gasto, gasto
manual, moeda, sobreposição). Achados com chave estável saem UMA vez — a memória local
(`store.findings`) suprime a repetição nas rodadas seguintes, como no auditor financeiro.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import config
import store

ORDEM_SEVERIDADE = {"critico": 0, "atencao": 1, "info": 2}
KINDS_ESPERADOS = {
    "meta_content": "Insights de conteúdo da Meta (posts)",
    "meta_account": "Insights da conta da Meta (seguidores)",
    "meta_ads": "Campanhas do Meta Ads",
    "google_ads": "Campanhas do Google Ads",
}
# Códigos cujo achado repete semana a semana enquanto a situação durar (sem supressão).
SEM_SUPRESSAO = {"sem_arquivo", "meta_atrasada", "sem_atribuicao", "nota_leitura"}


def _carrega(run_dir: Path, nome: str, padrao: dict | None = None) -> dict:
    caminho = run_dir / nome
    if not caminho.exists():
        if padrao is not None:
            return padrao
        raise FileNotFoundError(f"{nome} não existe em {run_dir} — rode a etapa anterior")
    return json.loads(caminho.read_text(encoding="utf-8"))


def achado(code: str, severity: str, title: str, key: str, **details) -> dict:
    return {"code": code, "severity": severity, "title": title, "key": key, "details": details}


def achados_de_arquivos(manifest: dict) -> list[dict]:
    saida = []
    aceitos = {f["kind"] for f in manifest["files"] if f["status"] == "accepted"}
    for f in manifest["files"]:
        if f["status"] == "rejected":
            saida.append(achado("arquivo_rejeitado", "atencao",
                                f"{f['filename']}: {f.get('reason') or 'não reconhecido'}", f["sha256"],
                                filename=f["filename"]))
    for kind, rotulo in KINDS_ESPERADOS.items():
        if kind not in aceitos:
            saida.append(achado("sem_arquivo", "info", f"Sem arquivo nesta rodada: {rotulo}",
                                f"{kind}:{manifest['run_id']}", kind=kind))
    return saida


def achados_do_contexto(contexto: dict, run_id: str) -> list[dict]:
    saida = []
    for meta in contexto.get("goals", []):
        if meta.get("status") == "delayed":
            atraso = meta.get("days_overdue") or meta.get("days_late")
            saida.append(achado("meta_atrasada", "atencao",
                                f"Meta de frequência atrasada: {meta['name']}"
                                + (f" ({atraso} dia(s))" if atraso else ""),
                                f"{meta['id']}:{run_id}", goal_id=meta["id"]))
    for gasto in contexto.get("marketing_expenses", []):
        if gasto.get("batch") and not gasto.get("has_receipt") and gasto.get("status") == "pendente":
            saida.append(achado("gasto_sem_comprovante", "info",
                                f"{gasto['description']}: aguardando fatura do cartão antes da aprovação",
                                str(gasto["id"]), expense_id=gasto["id"]))
    if not contexto.get("attributed_clients"):
        saida.append(achado("sem_atribuicao", "info",
                            "Nenhum lead da janela veio com utm_campaign — atribuição por campanha indisponível",
                            run_id))
    return saida


def achados_do_resultado(resultado: dict) -> list[dict]:
    saida = []
    for f in resultado.get("findings_server", []):
        det = f.get("details") or {}
        chave = f.get("key") or ":".join(str(det.get(k)) for k in ("platform", "month_ref") if det.get(k)) or f["title"]
        saida.append(achado(f["code"], f.get("severity", "atencao"), f["title"], chave, **det))
    for post in resultado.get("post_links", {}).get("unlinked_posts", []):
        saida.append(achado("post_nao_vinculado", "info",
                            f"Post {post['platform_post_id']} ({(post.get('published_at') or '?')[:10]}) sem card — informe o link no card",
                            post["platform_post_id"], **post))
    return saida


def suprimir_repetidos(achados: list[dict], run_id: str) -> list[dict]:
    """Achado com chave já reportada sai da lista; os novos são lembrados para a próxima rodada."""
    finais = []
    for a in achados:
        if a["code"] in SEM_SUPRESSAO:
            finais.append(a)
            continue
        if store.finding_seen(a["code"], a["key"]):
            continue
        store.remember_finding(a["code"], a["key"], run_id)
        finais.append(a)
    return finais


def main() -> int:
    ap = argparse.ArgumentParser(description="Achados da rodada do auditor de marketing")
    ap.add_argument("--run", required=True)
    ap.add_argument("--local", action="store_true")
    args = ap.parse_args()

    store.set_mode(args.local)
    run_dir = config.RUNS_DIR / args.run
    manifest = _carrega(run_dir, "manifest.json")
    contexto = _carrega(run_dir, "contexto.json", padrao={})
    resultado = _carrega(run_dir, "resultado.json", padrao={})

    todos = achados_de_arquivos(manifest) + achados_do_contexto(contexto, args.run) + achados_do_resultado(resultado)
    finais = suprimir_repetidos(todos, args.run)
    finais.sort(key=lambda a: (ORDEM_SEVERIDADE.get(a["severity"], 9), a["title"]))
    (run_dir / "findings.json").write_text(json.dumps(finais, ensure_ascii=False, indent=2), encoding="utf-8")
    por_sev = {s: sum(1 for a in finais if a["severity"] == s) for s in ORDEM_SEVERIDADE}
    print(f"[achados] {len(finais)} (suprimidos {len(todos) - len(finais)}): {por_sev}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
