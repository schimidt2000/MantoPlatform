"""Recuperação dos anexos órfãos deixados pelo bug do hotfix 257.

O bug salvava o arquivo no volume e perdia a linha do banco. Este script pergunta ao ERP
(`GET /api/audit-agent/<token>/orphan-attachments`, somente leitura) quais arquivos ficaram sem
dono, e monta um relatório para conferência humana: data do envio, tamanho, link para abrir o
arquivo e os eventos candidatos (mexidos naquela hora / com saldo em aberto por perto).

**Não escreve nada** — nem no banco, nem no volume. Re-vincular é decisão humana.

    python specs/257-hotfix-anexos-persistencia/recuperar_anexos_orfaos.py            # produção
    python specs/257-hotfix-anexos-persistencia/recuperar_anexos_orfaos.py --local    # Flask local
    ...--out relatorio.md      # onde gravar (padrão: ao lado deste script)

O token sai de `.audit-agent-token` (raiz do repositório, gitignored) e NUNCA é impresso.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
PROD_BASE = "https://app.mantoproducoes.com.br"
LOCAL_BASE = "http://localhost:5000"
TIMEOUT = 120
ROTULOS = {"payments": "Comprovantes de pagamento", "contracts": "Contratos", "invoices": "Notas fiscais"}

for _stream in (sys.stdout, sys.stderr):  # console do Windows em cp1252
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def token() -> str:
    caminho = REPO_ROOT / ".audit-agent-token"
    if not caminho.exists():
        raise SystemExit("Arquivo .audit-agent-token não encontrado na raiz do projeto.")
    return caminho.read_text(encoding="utf-8").strip()


def buscar(base: str) -> dict:
    """Consulta o endpoint traduzindo TODO erro à mão.

    Nada de `raise_for_status()` nem de deixar a exceção do `requests` subir: a mensagem delas
    inclui a URL, e a URL carrega o token — foi assim que ele vazou uma vez.
    """
    url = f"{base}/api/audit-agent/{token()}/orphan-attachments"
    try:
        resp = requests.get(url, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise SystemExit(f"Falha de rede falando com {base}: {type(exc).__name__}") from None
    if resp.status_code == 404:
        raise SystemExit(
            "404 do endpoint: token inválido ou env AUDIT_AGENT_TOKEN ausente no ambiente alvo.\n"
            "Confirme a variável no Railway (produção) ou no .env (local)."
        )
    if resp.status_code != 200:
        raise SystemExit(
            f"HTTP {resp.status_code} de {base} — se for 502, o deploy está reiniciando; tente de novo."
        )
    try:
        return resp.json()
    except ValueError:
        raise SystemExit(f"Resposta não-JSON de {base} (HTTP {resp.status_code}).") from None


def _data_br(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return iso


def _kb(tamanho: int) -> str:
    return f"{tamanho / 1024:.0f} KB" if tamanho < 1024 * 1024 else f"{tamanho / 1024 / 1024:.1f} MB"


def _linha_candidato(ev: dict, base: str) -> str:
    valor = f" · venda R$ {ev['sale_value']}" if ev.get("sale_value") else ""
    recebido = f" · recebido R$ {ev['received']}" if ev.get("received") is not None else ""
    return (f"    - [{ev['title']}]({base}/events/{ev['event_id']}) "
            f"({ev['start_at']}{valor}{recebido})")


def montar_relatorio(dados: dict, base: str) -> str:
    total = dados.get("orphans_total", 0)
    linhas = [
        "# Anexos órfãos — recuperação do hotfix 257",
        "",
        f"Gerado em {_data_br(dados.get('generated_at'))} · ambiente: {base}",
        "",
        f"**{total} arquivo(s) no volume sem linha no banco.** São os anexos que o bug engoliu: os",
        "bytes estão intactos, só perderam o vínculo. Abra cada link (precisa estar logado), veja o",
        "valor/cliente no próprio comprovante e re-anexe no evento certo pela tela — agora persiste.",
        "",
    ]
    for pasta, bloco in dados.get("subfolders", {}).items():
        orfaos = bloco.get("orphans", [])
        linhas.append(f"## {ROTULOS.get(pasta, pasta)} — {len(orfaos)} órfão(s) de {bloco.get('files_total', 0)} arquivo(s)")
        linhas.append("")
        if bloco.get("note"):
            linhas += [f"> {bloco['note']}", ""]
        if not orfaos:
            linhas += ["Nada órfão nesta pasta.", ""]
            continue
        for item in orfaos:
            linhas.append(f"### {_data_br(item.get('uploaded_at') or item.get('modified_at'))} — [{item['filename']}]({base}{item['file']}) ({_kb(item['size_bytes'])})")
            candidatos = item.get("candidates") or {}
            perto = candidatos.get("editados_perto") or []
            saldo = candidatos.get("com_saldo_aberto") or []
            if perto:
                linhas.append("  - **Eventos mexidos na mesma hora** (mais provável):")
                linhas += [_linha_candidato(ev, base) for ev in perto]
            if saldo:
                linhas.append("  - **Eventos com saldo em aberto por perto**:")
                linhas += [_linha_candidato(ev, base) for ev in saldo]
            if not perto and not saldo:
                linhas.append("  - Sem candidato automático — abra o arquivo para identificar.")
            linhas.append("")
    return "\n".join(linhas) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Lista os anexos órfãos do hotfix 257 (somente leitura)")
    ap.add_argument("--local", action="store_true", help="consulta o Flask local em vez da produção")
    ap.add_argument("--out", help="arquivo do relatório (padrão: ao lado deste script)")
    args = ap.parse_args()

    base = LOCAL_BASE if args.local else PROD_BASE
    dados = buscar(base)
    destino = Path(args.out) if args.out else Path(__file__).with_name(
        f"orfaos_{datetime.now().strftime('%Y%m%d_%H%M')}.md")
    destino.write_text(montar_relatorio(dados, base), encoding="utf-8")

    print(f"ambiente: {base}")
    for pasta, bloco in dados.get("subfolders", {}).items():
        print(f"  {ROTULOS.get(pasta, pasta):<28} {len(bloco.get('orphans', [])):>3} órfão(s) de {bloco.get('files_total', 0):>4} arquivo(s)")
    print(f"\ntotal de órfãos: {dados.get('orphans_total', 0)}")
    print(f"relatório: {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
