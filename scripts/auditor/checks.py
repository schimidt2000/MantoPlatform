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
import re
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
    """Aceita '6612.00', '6.612,00', 'R$ 6.612,00' e '6.612' (ponto de milhar pt-BR)."""
    if raw is None:
        return None
    text = str(raw).replace("R$", "").replace(" ", "").strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", text):
        # Só pontos, em grupos de milhar ('6.612'): é milhar pt-BR, não decimal.
        text = text.replace(".", "")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _parse_date(raw) -> date | None:
    """Aceita ISO ('2026-08-05') e pt-BR ('05/08/2026')."""
    if not raw:
        return None
    text = str(raw).strip()
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})", text)
    if m:
        text = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    try:
        return date.fromisoformat(text[:10])
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

    flags = item.get("flags", {})
    if flags.get("payment_status") == "pago" and flags.get("status") == "rejeitado":
        findings.append({**base, "code": "gasto_pago_porem_rejeitado", "severity": "critico",
                         "title": f"{item['descricao']}: o dinheiro JÁ SAIU (pago no ato) "
                                  "mas o gasto foi rejeitado na aprovação"})

    esperado = _parse_dec(item.get("amount"))
    lido = _parse_dec(extracted.get("valor"))
    # Fail-closed: extração existe mas não parseia → achado, nunca silêncio (um comprovante
    # com valor ilegível não pode sair como "confere").
    if extracted.get("valor") is not None and lido is None:
        findings.append({**base, "code": "extracao_ilegivel", "severity": "atencao",
                         "title": f"{item['descricao']}: valor extraído do comprovante "
                                  f"(“{extracted.get('valor')}”) não pôde ser interpretado"})
    if extracted.get("data") is not None and _parse_date(extracted.get("data")) is None:
        findings.append({**base, "code": "extracao_ilegivel", "severity": "atencao",
                         "title": f"{item['descricao']}: data extraída do comprovante "
                                  f"(“{extracted.get('data')}”) não pôde ser interpretada"})
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
    store.set_mode(local=manifest.get("modo") == "local")

    # Achados de estado persistente re-coletados pela margem de 2 dias repetiriam no
    # relatório seguinte — mesma supressão das anomalias históricas.
    codigos_persistentes = {"sem_anexo", "gasto_aprovado_sem_comprovante",
                            "arquivo_ausente", "comprovante_duplicado",
                            "valor_nao_registrado", "gasto_pago_porem_rejeitado"}

    findings: list[dict] = []
    suprimidos_itens = 0
    for item in manifest["items"]:
        extracted = _load_extraction(run_dir, item["entity_uid"])
        for f in check_item(item, extracted):
            if (f["code"] in codigos_persistentes
                    and store.finding_seen_before(f["code"], item["entity_uid"],
                                                  manifest["run_id"])):
                suprimidos_itens += 1
                continue
            findings.append(f)
        if extracted is not None and item.get("sha256"):
            store.record_audited(item["entity_uid"], item["sha256"],
                                 manifest["run_id"], extracted)
    if suprimidos_itens:
        print(f"[batimento] {suprimidos_itens} achados de itens já reportados antes — suprimidos")

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
