"""Batimento comprovante × registro do auditor financeiro (feature 221).

Cruza o que o Claude extraiu de cada comprovante (`runs/<id>/extracted/<uid>.json`) com o
que o sistema registrou (manifesto da coleta), aplica as regras determinísticas e grava os
achados na memória do auditor:

    python checks.py --run 20260810_060012

Formato esperado de cada extração (JSON escrito pelo Claude ao ler o comprovante):
    {
      "valor": "1234.56",           # string decimal, ponto como separador
      "data": "2026-08-05",          # data da transação no comprovante
      "pagador": "Fulano de Tal",
      "recebedor": "Ciclano LTDA",
      "chave_pix": "...",            # se visível
      "banco": "Nubank",
      "id_transacao": "E1234...",
      "parece_comprovante": 0.95,    # 0-1: aparência de comprovante bancário genuíno
      "observacoes": "..."
    }
Campos ilegíveis/ausentes: null.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

import config
import store
from pixnorm import name_matches, same_pix

SEVERIDADE_ORDEM = {"critico": 0, "atencao": 1, "info": 2, "ok": 3}


def _load_extraction(run_dir: Path, uid: str) -> dict | None:
    path = run_dir / "extracted" / (uid.replace(":", "_") + ".json")
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_dec(raw) -> Decimal | None:
    if raw is None:
        return None
    try:
        return Decimal(str(raw).replace("R$", "").replace(" ", "").replace(",", "."))
    except InvalidOperation:
        return None


def _parse_date(raw) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


def check_item(item: dict, extracted: dict | None) -> list[dict]:
    """Aplica as verificações de um item auditável; devolve os achados."""
    uid = item["entity_uid"]
    base = {"entity_uid": uid, "sha256": item.get("sha256"),
            "details": {"descricao": item["descricao"], "kind": item["kind"]}}
    findings: list[dict] = []

    status = item.get("status")
    if status == "sem_anexo":
        if item["kind"] == "gasto" and item.get("flags", {}).get("status") == "aprovado":
            findings.append({**base, "code": "gasto_aprovado_sem_comprovante",
                             "severity": "critico",
                             "title": f"{item['descricao']}: aprovado SEM comprovante anexado"})
        else:
            findings.append({**base, "code": "sem_anexo", "severity": "atencao",
                             "title": f"{item['descricao']}: sem comprovante anexado"})
        return findings
    if status == "arquivo_ausente":
        findings.append({**base, "code": "arquivo_ausente", "severity": "critico",
                         "title": f"{item['descricao']}: registro aponta para arquivo que "
                                  "não existe mais no servidor"})
        return findings
    if item.get("duplicata_de"):
        findings.append({**base, "code": "comprovante_duplicado", "severity": "critico",
                         "title": f"{item['descricao']}: mesmo arquivo já usado em "
                                  f"{', '.join(item['duplicata_de'])}",
                         "details": {**base["details"], "tambem_em": item["duplicata_de"]}})
    if status == "ja_auditado":
        return findings
    if extracted is None:
        findings.append({**base, "code": "sem_extracao", "severity": "atencao",
                         "title": f"{item['descricao']}: comprovante não foi lido nesta rodada"})
        return findings

    if item.get("flags", {}).get("amount_null"):
        findings.append({**base, "code": "valor_nao_registrado", "severity": "atencao",
                         "title": f"{item['descricao']}: comprovante anexado sem valor "
                                  "digitado no sistema"})

    esperado = _parse_dec(item.get("amount"))
    lido = _parse_dec(extracted.get("valor"))
    if esperado is not None and lido is not None and esperado != lido:
        findings.append({**base, "code": "divergencia_valor", "severity": "critico",
                         "title": f"{item['descricao']}: sistema R$ {esperado} × "
                                  f"comprovante R$ {lido}",
                         "details": {**base["details"], "sistema": str(esperado),
                                     "comprovante": str(lido)}})

    data_esperada = _parse_date(item.get("expected_date"))
    data_lida = _parse_date(extracted.get("data"))
    if data_esperada and data_lida:
        delta = abs((data_lida - data_esperada).days)
        if delta > config.TOLERANCIA_DIAS_DATA:
            findings.append({**base, "code": "divergencia_data", "severity": "atencao",
                             "title": f"{item['descricao']}: data do comprovante "
                                      f"({data_lida}) difere {delta} dias do registro "
                                      f"({data_esperada})"})

    pix_ok = same_pix(item.get("expected_pix"), extracted.get("chave_pix"))
    if pix_ok is False:
        findings.append({**base, "code": "divergencia_pix", "severity": "critico",
                         "title": f"{item['descricao']}: chave PIX do comprovante NÃO é a "
                                  "cadastrada para o beneficiário",
                         "details": {**base["details"],
                                     "cadastrada": item.get("expected_pix"),
                                     "no_comprovante": extracted.get("chave_pix")}})

    campo_nome = "expected_payer" if item["kind"] == "entrada" else "expected_payee"
    lado_extraido = "pagador" if item["kind"] == "entrada" else "recebedor"
    nome_ok = name_matches(item.get(campo_nome), extracted.get(lado_extraido))
    if nome_ok is False and pix_ok is not True:
        findings.append({**base, "code": "divergencia_beneficiario", "severity": "atencao",
                         "title": f"{item['descricao']}: {lado_extraido} do comprovante "
                                  f"(“{extracted.get(lado_extraido)}”) não bate com o "
                                  f"registro (“{item.get(campo_nome)}”)"})

    aparencia = extracted.get("parece_comprovante")
    if aparencia is not None and float(aparencia) < 0.5:
        findings.append({**base, "code": "aparencia_suspeita", "severity": "critico",
                         "title": f"{item['descricao']}: arquivo não parece um comprovante "
                                  "bancário genuíno",
                         "details": {**base["details"], "score": aparencia,
                                     "observacoes": extracted.get("observacoes")}})

    if not findings:
        findings.append({**base, "code": "ok", "severity": "ok",
                         "title": f"{item['descricao']}: confere"})
    return findings


def main() -> int:
    """Roda o batimento de uma rodada coletada."""
    ap = argparse.ArgumentParser(description="Batimento comprovante × registro")
    ap.add_argument("--run", required=True, help="id da rodada (pasta em runs/)")
    args = ap.parse_args()

    run_dir = config.RUNS_DIR / args.run
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))

    findings: list[dict] = []
    for item in manifest["items"]:
        extracted = _load_extraction(run_dir, item["entity_uid"])
        findings += check_item(item, extracted)
        if extracted is not None and item.get("sha256"):
            store.record_audited(item["entity_uid"], item["sha256"],
                                 manifest["run_id"], extracted)

    suprimidas = 0
    for anomalia in manifest["anomalias_sql"]:
        uid = anomalia.get("entity_uid")
        if uid and store.finding_seen_before(anomalia["code"], uid, manifest["run_id"]):
            suprimidas += 1
            continue
        findings.append({"entity_uid": None, "sha256": None, **anomalia})
    if suprimidas:
        print(f"[batimento] {suprimidas} anomalias históricas já reportadas antes — suprimidas")

    for margem in manifest["aggregates"].get("margens_eventos", []):
        if margem["apertada"]:
            findings.append({
                "entity_uid": f"calendar_event:{margem['event_id']}", "sha256": None,
                "code": "margem_apertada", "severity": "atencao",
                "title": f"“{margem['title']}” ({margem['data']}): custo R$ {margem['custo']} "
                         f"é {Decimal(margem['custo_sobre_venda']) * 100:.0f}% da venda "
                         f"R$ {margem['venda']}",
                "details": margem,
            })

    findings.sort(key=lambda f: SEVERIDADE_ORDEM.get(f["severity"], 9))
    store.record_findings(manifest["run_id"], findings)
    (run_dir / "findings.json").write_text(
        json.dumps(findings, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    n = {sev: sum(1 for f in findings if f["severity"] == sev) for sev in SEVERIDADE_ORDEM}
    print(f"[batimento] {len(findings)} achados — críticos: {n['critico']}, "
          f"atenção: {n['atencao']}, info: {n['info']}, ok: {n['ok']}")
    print(f"[batimento] gravado em {run_dir / 'findings.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
