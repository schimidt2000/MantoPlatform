"""Leitura tolerante dos exports CSV da Meta e do Google Ads (feature 256).

Regras (contracts/csv-inbox.md): delimitador por sniff, BOM, preâmbulo/rodapé do Google,
números BR e US (ambíguo é rejeitado — nunca adivinhar), datas em cinco formatos, tipo de
arquivo por assinatura de colunas com aliases em `column_maps.json`. Nenhuma coluna ausente
vira zero: vira ``None``.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import config

LIMITE_LINHAS_REJEITADAS = 0.10
CAPTION_MAX = 300
_MESES = {
    "jan": 1, "fev": 2, "feb": 2, "mar": 3, "abr": 4, "apr": 4, "mai": 5, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "aug": 8, "set": 9, "sep": 9, "out": 10, "oct": 10, "nov": 11,
    "dez": 12, "dec": 12,
}
_RE_EXTENSO_PT = re.compile(r"(\d{1,2})\s+de\s+([a-zç]{3})\.?\s+de\s+(\d{4})", re.I)
_RE_EXTENSO_EN = re.compile(r"([a-z]{3})\.?\s+(\d{1,2}),\s+(\d{4})", re.I)
_RE_MOEDA_ROTULO = re.compile(r"\(([A-Z]{3})\)")
_FORMATOS_DATA = (
    "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y",
)


class AmbiguousNumber(ValueError):
    """`1.234` ou `1,234` isolados: pode ser mil e duzentos ou um vírgula dois — não adivinhamos."""


@dataclass
class FileVerdict:
    """Resultado da leitura de um arquivo da pasta de entrada."""

    filename: str
    sha256: str
    kind: str = "unknown"
    status: str = "rejected"  # accepted | rejected | skipped_duplicate
    reason: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    row_count: int = 0
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


# ── utilidades ────────────────────────────────────────────────────────────────


def slug(text: str | None) -> str:
    """Minúsculas, sem acento, sem aspas/BOM, espaços colapsados — base das comparações."""
    texto = (text or "").replace("﻿", "").replace('"', "").strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", texto)


def sha256_of(path: Path) -> str:
    """Impressão digital do conteúdo (idempotência entre rodadas)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_column_maps(path: Path = config.COLUMN_MAPS_PATH) -> dict:
    """Carrega o mapa de colunas editável."""
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    """UTF-8 (com ou sem BOM) e, se falhar, latin-1."""
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def sniff_delimiter(lines: list[str]) -> str:
    """Delimitador mais frequente entre `,` `;` e tab na linha mais 'larga' das primeiras cinco."""
    candidatos = [",", ";", "\t"]
    melhor, melhor_n = ",", -1
    for linha in lines[:5]:
        for d in candidatos:
            n = linha.count(d)
            if n > melhor_n:
                melhor, melhor_n = d, n
    return melhor


def parse_number(raw: str | None) -> Decimal | None:
    """Número nos formatos BR (`1.234,56`) e US (`1,234.56`); vazio/`--` → None.

    Raises:
        AmbiguousNumber: um único separador seguido de exatamente três dígitos.
    """
    texto = (raw or "").strip()
    if not texto or texto in {"-", "--", "—"}:
        return None
    negativo = texto.startswith("-") or texto.startswith("(")
    s = re.sub(r"[^\d,.]", "", texto)
    if not s:
        return None
    if "," in s and "." in s:
        decimal_sep = "," if s.rfind(",") > s.rfind(".") else "."
        s = s.replace("." if decimal_sep == "," else ",", "").replace(decimal_sep, ".")
    elif "," in s or "." in s:
        sep = "," if "," in s else "."
        if s.count(sep) > 1:
            s = s.replace(sep, "")
        else:
            cauda = s.split(sep)[1]
            if len(cauda) == 3:
                raise AmbiguousNumber(texto)
            s = s.replace(sep, ".")
    try:
        valor = Decimal(s)
    except InvalidOperation as exc:
        raise ValueError(f"número inválido: {texto!r}") from exc
    return -valor if negativo else valor


def parse_int(raw: str | None) -> int | None:
    """Inteiro a partir de texto numérico (arredonda `2,00` → 2); vazio → None."""
    valor = parse_number(raw)
    return None if valor is None else int(valor.to_integral_value())


def parse_datetime(raw: str | None) -> datetime | None:
    """Data/hora nos formatos das plataformas; vazio ou irreconhecível → None."""
    texto = (raw or "").strip()
    if not texto:
        return None
    for fmt in _FORMATOS_DATA:
        try:
            return datetime.strptime(texto, fmt)
        except ValueError:
            continue
    m = _RE_EXTENSO_PT.search(texto)
    if m and slug(m.group(2))[:3] in _MESES:
        return datetime(int(m.group(3)), _MESES[slug(m.group(2))[:3]], int(m.group(1)))
    m = _RE_EXTENSO_EN.search(texto)
    if m and m.group(1).lower() in _MESES:
        return datetime(int(m.group(3)), _MESES[m.group(1).lower()], int(m.group(2)))
    return None


def parse_date(raw: str | None) -> date | None:
    """Só a data (ver `parse_datetime`)."""
    dt = parse_datetime(raw)
    return dt.date() if dt else None


def parse_period_preamble(preamble: list[str]) -> tuple[date, date] | None:
    """Período do preâmbulo do Google ("11 de ago. de 2026 - 17 de ago. de 2026")."""
    for linha in preamble:
        partes = re.split(r"\s[-–]\s", linha)
        if len(partes) == 2:
            inicio, fim = parse_date(partes[0]), parse_date(partes[1])
            if inicio and fim:
                return inicio, fim
    return None


def clean_permalink(raw: str | None) -> str | None:
    """Remove querystring/fragmento (utm e afins); mantém o resto como veio."""
    texto = (raw or "").strip()
    if not texto:
        return None
    return texto.split("#", 1)[0].split("?", 1)[0]


# ── leitura e classificação ───────────────────────────────────────────────────


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]], list[str]]:
    """Cabeçalho, linhas (dict) e preâmbulo. Rodapé `Total…` e linhas vazias são descartados."""
    linhas = [ln for ln in read_text(path).splitlines()]
    delim = sniff_delimiter([ln for ln in linhas if ln.strip()])
    registros = list(csv.reader(linhas, delimiter=delim))
    preambulo: list[str] = []
    cabecalho: list[str] = []
    dados: list[dict[str, str]] = []
    for celulas in registros:
        if not any(c.strip() for c in celulas):
            continue
        if not cabecalho:
            if len([c for c in celulas if c.strip()]) >= 3:
                cabecalho = [c.strip() for c in celulas]
            else:
                preambulo.append(delim.join(celulas).strip())
            continue
        if slug(celulas[0]).startswith("total"):
            continue
        dados.append({cabecalho[i]: (celulas[i].strip() if i < len(celulas) else "") for i in range(len(cabecalho))})
    return cabecalho, dados, preambulo


def _casa(header: str, alias: str) -> bool:
    h, a = slug(header), slug(alias)
    return h == a or h.startswith(a + " (") or h.startswith(a + "(")


def resolve_fields(headers: list[str], fields: dict[str, list[str]]) -> dict[str, str]:
    """Campo lógico → cabeçalho real encontrado (primeiro alias que casar)."""
    resolvido: dict[str, str] = {}
    for campo, aliases in fields.items():
        for alias in aliases:
            achado = next((h for h in headers if _casa(h, alias)), None)
            if achado is not None:
                resolvido[campo] = achado
                break
    return resolvido


def classify(headers: list[str], maps: dict) -> tuple[dict | None, dict[str, str], list[str]]:
    """Primeiro tipo cujo conjunto obrigatório é satisfeito; senão (None, {}, faltantes do melhor)."""
    melhor: tuple[int, dict, list[str]] | None = None
    for spec in maps["kinds"]:
        resolvido = resolve_fields(headers, spec["fields"])
        faltantes = [grupo for grupo in spec["required"] if not any(c in resolvido for c in grupo)]
        if not faltantes:
            return spec, resolvido, []
        satisfeitos = len(spec["required"]) - len(faltantes)
        if melhor is None or satisfeitos > melhor[0]:
            melhor = (satisfeitos, spec, [spec["fields"][g[0]][0] for g in faltantes])
    return None, {}, melhor[2] if melhor else []


# ── normalização por tipo ─────────────────────────────────────────────────────


def _val(row: dict[str, str], res: dict[str, str], campo: str) -> str | None:
    header = res.get(campo)
    if header is None:
        return None
    valor = row.get(header, "")
    return valor if valor != "" else None


def _currency_from_header(res: dict[str, str], campo: str, default: str = "BRL") -> str:
    m = _RE_MOEDA_ROTULO.search(res.get(campo, ""))
    return m.group(1) if m else default


def normalize_meta_content(rows, res, platform, run_date, notes):
    itens, rejeitadas = [], 0
    for row in rows:
        post_id = _val(row, res, "post_id")
        if not post_id:
            rejeitadas += 1
            continue
        data_foto = parse_date(_val(row, res, "date"))
        if data_foto is None:
            data_foto = run_date
            if "data da fotografia assumida = data da rodada" not in notes:
                notes.append("data da fotografia assumida = data da rodada")
        publicado = parse_datetime(_val(row, res, "published_at"))
        try:
            itens.append({
                "platform": platform,
                "platform_post_id": post_id,
                "permalink": clean_permalink(_val(row, res, "permalink")),
                "post_type": (_val(row, res, "post_type") or None),
                "caption": (_val(row, res, "caption") or "")[:CAPTION_MAX] or None,
                "published_at": publicado.isoformat() if publicado else None,
                "snapshot_date": data_foto.isoformat(),
                **{k: parse_int(_val(row, res, k)) for k in ("reach", "impressions", "likes", "comments", "saves", "shares", "views")},
            })
        except (AmbiguousNumber, ValueError):
            rejeitadas += 1
    return {"post_metrics": itens}, rejeitadas


def normalize_meta_account(rows, res, platform, run_date, notes):
    itens, rejeitadas = [], 0
    for row in rows:
        dia = parse_date(_val(row, res, "date"))
        if dia is None:
            rejeitadas += 1
            continue
        try:
            itens.append({
                "platform": platform,
                "metric_date": dia.isoformat(),
                "followers": parse_int(_val(row, res, "followers")),
                "reach": parse_int(_val(row, res, "reach")),
                "profile_views": parse_int(_val(row, res, "profile_views")),
            })
        except (AmbiguousNumber, ValueError):
            rejeitadas += 1
    return {"account_metrics": itens}, rejeitadas


def _campaign_id(row, res, nome: str) -> str:
    explicito = _val(row, res, "campaign_id")
    return explicito if explicito else "h:" + re.sub(r"[^a-z0-9]+", "-", slug(nome)).strip("-")


def normalize_meta_ads(rows, res, platform, run_date, notes):
    itens, rejeitadas = [], 0
    moeda = _currency_from_header(res, "spend")
    for row in rows:
        nome = _val(row, res, "campaign_name")
        dia = parse_date(_val(row, res, "day"))
        inicio = dia or parse_date(_val(row, res, "period_start"))
        fim = dia or parse_date(_val(row, res, "period_end"))
        if not nome or inicio is None or fim is None:
            rejeitadas += 1
            continue
        try:
            gasto = parse_number(_val(row, res, "spend"))
            itens.append({
                "platform": platform,
                "campaign_id": _campaign_id(row, res, nome),
                "campaign_name": nome,
                "period_start": inicio.isoformat(),
                "period_end": fim.isoformat(),
                "spend": str(gasto if gasto is not None else Decimal("0")),
                "currency": moeda,
                "impressions": parse_int(_val(row, res, "impressions")),
                "reach": parse_int(_val(row, res, "reach")),
                "clicks": parse_int(_val(row, res, "clicks")),
                "results": parse_int(_val(row, res, "results")),
                "conversions": None,
                "result_type": _val(row, res, "result_type"),
            })
        except (AmbiguousNumber, ValueError):
            rejeitadas += 1
    return {"campaign_metrics": itens}, rejeitadas


def normalize_google_ads(rows, res, platform, run_date, notes, preamble_period=None):
    itens, rejeitadas = [], 0
    for row in rows:
        nome = _val(row, res, "campaign_name")
        dia = parse_date(_val(row, res, "day"))
        if dia:
            inicio = fim = dia
        elif preamble_period:
            inicio, fim = preamble_period
        else:
            inicio = fim = None
        if not nome or inicio is None:
            rejeitadas += 1
            continue
        try:
            gasto = parse_number(_val(row, res, "spend"))
            itens.append({
                "platform": platform,
                "campaign_id": _campaign_id(row, res, nome),
                "campaign_name": nome,
                "period_start": inicio.isoformat(),
                "period_end": fim.isoformat(),
                "spend": str(gasto if gasto is not None else Decimal("0")),
                "currency": (_val(row, res, "currency") or "BRL").upper(),
                "impressions": parse_int(_val(row, res, "impressions")),
                "reach": None,
                "clicks": parse_int(_val(row, res, "clicks")),
                "results": None,
                "conversions": parse_int(_val(row, res, "conversions")),
                "result_type": None,
            })
        except (AmbiguousNumber, ValueError):
            rejeitadas += 1
    return {"campaign_metrics": itens}, rejeitadas


_NORMALIZERS = {
    "meta_content": normalize_meta_content,
    "meta_account": normalize_meta_account,
    "meta_ads": normalize_meta_ads,
    "google_ads": normalize_google_ads,
}


def _periodo(dados: dict) -> tuple[str | None, str | None]:
    datas: list[str] = []
    for item in dados.get("post_metrics", []):
        datas.append(item["snapshot_date"])
    for item in dados.get("campaign_metrics", []):
        datas.extend([item["period_start"], item["period_end"]])
    for item in dados.get("account_metrics", []):
        datas.append(item["metric_date"])
    return (min(datas), max(datas)) if datas else (None, None)


def parse_file(path: Path, maps: dict, *, run_date: date) -> tuple[FileVerdict, dict]:
    """Lê, classifica e normaliza um arquivo; devolve o veredito e os dados no shape do `POST /run`."""
    veredito = FileVerdict(filename=path.name, sha256=sha256_of(path))
    headers, rows, preambulo = read_rows(path)
    if not headers or not rows:
        veredito.reason = "sem linhas"
        return veredito, {}
    spec, res, faltantes = classify(headers, maps)
    if spec is None:
        veredito.reason = "colunas faltantes: " + ", ".join(faltantes)
        return veredito, {}
    veredito.kind = spec["kind"]
    extra = {}
    if spec["kind"] == "google_ads" and "day" not in res:
        extra["preamble_period"] = parse_period_preamble(preambulo)
        if extra["preamble_period"] is None:
            veredito.reason = "período não identificado (sem coluna Dia nem preâmbulo com datas)"
            return veredito, {}
        veredito.notes.append("agregado por período (sem detalhamento por dia)")
    dados, rejeitadas = _NORMALIZERS[spec["kind"]](rows, res, spec["platform"], run_date, veredito.notes, **extra)
    if rejeitadas / len(rows) > LIMITE_LINHAS_REJEITADAS:
        veredito.reason = f"{rejeitadas} de {len(rows)} linhas ilegíveis (números ambíguos ou datas inválidas)"
        return veredito, {}
    if rejeitadas:
        veredito.notes.append(f"{rejeitadas} linha(s) ilegível(is) ignorada(s)")
    veredito.status = "accepted"
    veredito.row_count = len(rows) - rejeitadas
    veredito.period_start, veredito.period_end = _periodo(dados)
    return veredito, dados
