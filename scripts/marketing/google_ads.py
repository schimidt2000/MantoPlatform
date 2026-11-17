"""Google Ads pela API REST (feature 345b), usado pela rotina de segunda na máquina do dono.

Não há conector MCP do Google na rotina. O acesso é OAuth "App para computador" do projeto Cloud
`manto-marketing` (tela de consentimento Interna), na conta da Manto. O cliente OAuth fica em
`~/.google-ads/client_secret.json` e o token em `~/.google-ads/token.json`, os dois fora do repositório.
Este script nunca imprime token.

Uso (a partir de `scripts/marketing/`, com o `..\\..\\.venv\\Scripts\\python.exe`):
    google_ads.py login
    google_ads.py coletar --inicio 2026-11-03 --fim 2026-11-16 --saida <pasta>
    google_ads.py ler <campaign_id>
    google_ads.py pausar <campaign_id> [--aplicar]
    google_ads.py ativar <campaign_id> [--aplicar]
    google_ads.py verba <campaign_id> <reais_por_dia> [--aplicar]
    google_ads.py gaql "<consulta GAQL>"

Sem `--aplicar`, a mudança vai como ensaio (`validateOnly`): o Google confere e não altera nada.

A conversão da conta ("Contato por Whatsapp") é o TOQUE no botão, não a conversa: o `coletar` grava
como `results`, nunca como `conversations`. Conversa vinda do Google só existe com o código de
referência ou o gclid na conversa (feature 348).
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

import config
import requests

ESCOPOS = ["https://www.googleapis.com/auth/adwords"]
# A API aposenta versões a cada poucos meses: a primeira que responder fica guardada em cache.
VERSOES = ["v24", "v23", "v22", "v21", "v20"]
PORTA_LOGIN = 8765
PLATAFORMA = "Google Ads"
TIPO_RESULTADO = "conversão do Google (toque no botão, não é conversa)"
CENTAVO = Decimal("0.01")

GAQL_CAMPANHAS = (
    "SELECT campaign.id, campaign.name, segments.date, metrics.cost_micros, metrics.impressions, "
    "metrics.clicks, metrics.conversions FROM campaign "
    "WHERE segments.date BETWEEN '{inicio}' AND '{fim}' AND metrics.impressions > 0"
)
# PMax não tem `ad_group_ad`: o gasto dela aparece só por campanha.
GAQL_ANUNCIOS = (
    "SELECT campaign.id, campaign.name, ad_group.id, ad_group_ad.ad.id, ad_group_ad.ad.name, "
    "segments.date, metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions "
    "FROM ad_group_ad WHERE segments.date BETWEEN '{inicio}' AND '{fim}' AND metrics.impressions > 0"
)
GAQL_CAMPANHA = (
    "SELECT campaign.id, campaign.name, campaign.status, campaign_budget.resource_name, "
    "campaign_budget.amount_micros, campaign_budget.explicitly_shared FROM campaign "
    "WHERE campaign.id = {campaign_id}"
)


class GoogleAdsErro(RuntimeError):
    """Resposta de erro da API: o texto vai para o stderr, sem token."""


# ── conversão para o formato do ERP (pura, sem rede) ─────────────────────────


def micros_para_reais(micros: Any) -> str:
    """`cost_micros` (milionésimos da moeda) → reais com 2 casas, em string."""
    valor = Decimal(int(micros or 0)) / Decimal(1_000_000)
    return str(valor.quantize(CENTAVO, rounding=ROUND_HALF_UP))


def _metricas(linha: dict[str, Any]) -> dict[str, Any]:
    m = linha.get("metrics") or {}
    return {
        "spend": micros_para_reais(m.get("costMicros")),
        "impressions": int(m.get("impressions") or 0),
        "clicks": int(m.get("clicks") or 0),
        # Toque no botão do WhatsApp: é resultado da plataforma, NUNCA conversa.
        "results": round(float(m.get("conversions") or 0)),
    }


def _id_do_recurso(recurso: dict[str, Any]) -> str:
    return str(recurso.get("id") or str(recurso.get("resourceName") or "").split("/")[-1])


def para_campaign_metrics(linhas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Linhas de `GAQL_CAMPANHAS` → `campaign_metrics` diárias do `POST /run`."""
    saida = []
    for linha in linhas:
        dia = linha["segments"]["date"]
        saida.append(
            {
                "platform": PLATAFORMA,
                "campaign_id": _id_do_recurso(linha["campaign"]),
                "campaign_name": linha["campaign"].get("name") or "",
                "period_start": dia,
                "period_end": dia,
                "currency": "BRL",
                "result_type": TIPO_RESULTADO,
                **_metricas(linha),
            }
        )
    return saida


def para_itens_de_anuncio(linhas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Linhas de `GAQL_ANUNCIOS` → `items` do `POST /anuncios`."""
    saida = []
    for linha in linhas:
        anuncio = (linha.get("adGroupAd") or {}).get("ad") or {}
        saida.append(
            {
                "platform": PLATAFORMA,
                "ad_id": _id_do_recurso(anuncio),
                "ad_name": anuncio.get("name"),
                "adset_id": _id_do_recurso(linha.get("adGroup") or {}),
                "campaign_id": _id_do_recurso(linha["campaign"]),
                "campaign_name": linha["campaign"].get("name"),
                "metric_date": linha["segments"]["date"],
                "currency": "BRL",
                **_metricas(linha),
            }
        )
    return saida


# ── acesso à API ──────────────────────────────────────────────────────────────


def _credenciais() -> Any:
    # Import tardio: os conversores acima rodam (e são verificados) sem o google-auth.
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    arquivo = config.GOOGLE_ADS_DIR / "token.json"
    if not arquivo.exists():
        raise GoogleAdsErro(
            "Sem login no Google Ads: rode `google_ads.py login` (o dono autoriza no navegador)."
        )
    cred = Credentials.from_authorized_user_file(str(arquivo), ESCOPOS)
    if not cred.valid:
        cred.refresh(Request())
        arquivo.write_text(cred.to_json(), encoding="utf-8")
    return cred


def _cabecalhos() -> dict[str, str]:
    cab = {"Authorization": f"Bearer {_credenciais().token}", "Content-Type": "application/json"}
    dev = config.GOOGLE_ADS_DIR / "developer_token.txt"
    if dev.exists():
        cab["developer-token"] = dev.read_text(encoding="utf-8").strip()
    return cab


def _versao() -> str:
    cache = config.GOOGLE_ADS_DIR / "api_version.txt"
    if cache.exists():
        return cache.read_text(encoding="utf-8").strip()
    for v in VERSOES:
        r = requests.get(
            f"https://googleads.googleapis.com/{v}/customers:listAccessibleCustomers",
            headers=_cabecalhos(),
            timeout=config.HTTP_TIMEOUT,
        )
        if r.status_code != 404:
            cache.write_text(v, encoding="utf-8")
            return v
    raise GoogleAdsErro("Nenhuma versão da Google Ads API respondeu.")


def _url(caminho: str) -> str:
    return f"https://googleads.googleapis.com/{_versao()}/customers/{config.GOOGLE_ADS_CUSTOMER_ID}/{caminho}"


def gaql(consulta: str) -> list[dict[str, Any]]:
    """Roda uma consulta GAQL (`searchStream`) e devolve as linhas."""
    r = requests.post(
        _url("googleAds:searchStream"),
        headers=_cabecalhos(),
        data=json.dumps({"query": consulta}),
        timeout=config.HTTP_TIMEOUT,
    )
    if r.status_code != 200:
        raise GoogleAdsErro(f"GAQL recusada ({r.status_code}): {r.text[:1500]}")
    return [linha for bloco in r.json() for linha in bloco.get("results", [])]


def mutate(servico: str, operacoes: list[dict[str, Any]], *, aplicar: bool) -> dict[str, Any]:
    """`<servico>:mutate`. Sem `aplicar`, vai com `validateOnly` (ensaio: nada muda)."""
    corpo = {"operations": operacoes, "partialFailure": False, "validateOnly": not aplicar}
    r = requests.post(
        _url(f"{servico}:mutate"),
        headers=_cabecalhos(),
        data=json.dumps(corpo),
        timeout=config.HTTP_TIMEOUT,
    )
    if r.status_code != 200:
        raise GoogleAdsErro(f"{servico}:mutate recusado ({r.status_code}): {r.text[:1500]}")
    return r.json()


def ler_campanha(campaign_id: str) -> dict[str, Any]:
    """Estado atual de uma campanha: situação e verba diária (em reais)."""
    if not str(campaign_id).isdigit():
        raise GoogleAdsErro("O id da campanha é só número.")
    linhas = gaql(GAQL_CAMPANHA.format(campaign_id=campaign_id))
    if not linhas:
        raise GoogleAdsErro(f"Campanha {campaign_id} não encontrada na conta.")
    c, verba = linhas[0]["campaign"], linhas[0].get("campaignBudget") or {}
    return {
        "campaign_id": _id_do_recurso(c),
        "nome": c.get("name"),
        "situacao": c.get("status"),
        "verba_dia": micros_para_reais(verba.get("amountMicros")),
        "verba_compartilhada": bool(verba.get("explicitlyShared")),
        "_verba_recurso": verba.get("resourceName"),
    }


def mudar_situacao(campaign_id: str, situacao: str, *, aplicar: bool) -> dict[str, Any]:
    recurso = f"customers/{config.GOOGLE_ADS_CUSTOMER_ID}/campaigns/{campaign_id}"
    op = {"update": {"resourceName": recurso, "status": situacao}, "updateMask": "status"}
    return mutate("campaigns", [op], aplicar=aplicar)


def mudar_verba(campaign_id: str, reais_por_dia: str, *, aplicar: bool) -> dict[str, Any]:
    atual = ler_campanha(campaign_id)
    if atual["verba_compartilhada"]:
        # Verba compartilhada muda TODAS as campanhas que a usam: isso não é uma proposta de uma campanha.
        raise GoogleAdsErro(
            "A verba desta campanha é compartilhada com outras; mude pelo painel do Google."
        )
    valor = Decimal(str(reais_por_dia).replace(",", "."))
    if valor <= 0:
        raise GoogleAdsErro("A verba diária precisa ser maior que zero.")
    micros = int((valor * 1_000_000).to_integral_value())
    op = {
        "update": {"resourceName": atual["_verba_recurso"], "amountMicros": str(micros)},
        "updateMask": "amount_micros",
    }
    return mutate("campaignBudgets", [op], aplicar=aplicar)


def login() -> None:
    """OAuth no navegador do dono; o redirect volta para 127.0.0.1 e o token fica em ~/.google-ads."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    segredo = config.GOOGLE_ADS_DIR / "client_secret.json"
    if not segredo.exists():
        raise GoogleAdsErro(
            f"Falta o cliente OAuth em {segredo} (Cloud `manto-marketing`, App para computador)."
        )
    fluxo = InstalledAppFlow.from_client_secrets_file(str(segredo), ESCOPOS)
    # A URL impressa só tem o client_id (público) e o state: pode ir para o navegador do dono.
    cred = fluxo.run_local_server(
        host="127.0.0.1",
        bind_addr="127.0.0.1",
        port=PORTA_LOGIN,
        open_browser=False,
        prompt="consent",
        access_type="offline",
        authorization_prompt_message="Abra no navegador e autorize com a conta da Manto:\n{url}",
        success_message="Pronto. Pode fechar esta aba e voltar ao Claude.",
    )
    (config.GOOGLE_ADS_DIR / "token.json").write_text(cred.to_json(), encoding="utf-8")
    print(
        "Login salvo; renovação automática:",
        "sim" if cred.refresh_token else "NÃO (refaça o login)",
    )


# ── linha de comando ──────────────────────────────────────────────────────────


def _coletar(inicio: str, fim: str, saida: Path) -> dict[str, Any]:
    campanhas = para_campaign_metrics(gaql(GAQL_CAMPANHAS.format(inicio=inicio, fim=fim)))
    anuncios = para_itens_de_anuncio(gaql(GAQL_ANUNCIOS.format(inicio=inicio, fim=fim)))
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "google_campanhas.json").write_text(
        json.dumps(campanhas, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (saida / "google_anuncios.json").write_text(
        json.dumps({"items": anuncios}, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    gasto = sum(Decimal(c["spend"]) for c in campanhas)
    return {
        "janela": [inicio, fim],
        "linhas_de_campanha": len(campanhas),
        "linhas_de_anuncio": len(anuncios),
        "gasto_total": str(gasto),
        "campanhas": sorted({c["campaign_name"] for c in campanhas}),
        "arquivos": [str(saida / "google_campanhas.json"), str(saida / "google_anuncios.json")],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("login")
    p = sub.add_parser("coletar")
    p.add_argument("--inicio", required=True)
    p.add_argument("--fim", required=True)
    p.add_argument("--saida", required=True)
    sub.add_parser("ler").add_argument("campaign_id")
    for nome in ("pausar", "ativar"):
        p = sub.add_parser(nome)
        p.add_argument("campaign_id")
        p.add_argument("--aplicar", action="store_true")
    p = sub.add_parser("verba")
    p.add_argument("campaign_id")
    p.add_argument("reais_por_dia")
    p.add_argument("--aplicar", action="store_true")
    sub.add_parser("gaql").add_argument("consulta")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")
    config.GOOGLE_ADS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if args.cmd == "login":
            login()
            return 0
        if args.cmd == "coletar":
            resultado: Any = _coletar(args.inicio, args.fim, Path(args.saida))
        elif args.cmd == "ler":
            resultado = {
                k: v for k, v in ler_campanha(args.campaign_id).items() if not k.startswith("_")
            }
        elif args.cmd in ("pausar", "ativar"):
            antes = ler_campanha(args.campaign_id)["situacao"]
            mudar_situacao(
                args.campaign_id,
                "PAUSED" if args.cmd == "pausar" else "ENABLED",
                aplicar=args.aplicar,
            )
            resultado = {
                "modo": "aplicado" if args.aplicar else "ensaio (nada mudou)",
                "antes": antes,
            }
            if args.aplicar:
                resultado["depois"] = ler_campanha(args.campaign_id)["situacao"]
        elif args.cmd == "verba":
            antes = ler_campanha(args.campaign_id)["verba_dia"]
            mudar_verba(args.campaign_id, args.reais_por_dia, aplicar=args.aplicar)
            resultado = {
                "modo": "aplicado" if args.aplicar else "ensaio (nada mudou)",
                "antes": antes,
            }
            if args.aplicar:
                resultado["depois"] = ler_campanha(args.campaign_id)["verba_dia"]
        else:
            resultado = gaql(args.consulta)
    except GoogleAdsErro as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
