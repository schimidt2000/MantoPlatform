"""Leitura do aviso de PIX recebido que o Inter manda por e-mail (feature 318).

Puro: recebe os bytes do e-mail (RFC 822) e devolve o que a regra de vínculo precisa — sem banco,
sem rede. O aviso é uma frase fixa num HTML sem parte texto:

    "Olá, JOAO Você recebeu um Pix no valor de R$ 2.200,00 de <nome>, na conta <número>."
    "Olá, JOAO Você recebeu a devolução de um Pix, no valor de R$ 1,00, na conta <número>."

O aviso não traz CPF, id E2E nem hora: a hora é a do cabeçalho `Date` (o Inter manda em segundos),
e a identidade é o `Message-ID`. A autenticidade vem do `Authentication-Results` que o Google
grava ao receber — sem `dkim=pass` do Inter, o PIX nunca liga sozinho (um e-mail forjado faria a
cobrança parar de cobrar quem ainda deve).

Conferido em 22/10/2026 contra os 338 avisos da caixa desde 01/06: 338 entendidos.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from email import message_from_bytes
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parseaddr, parsedate_to_datetime
from zoneinfo import ZoneInfo

from app.constants import PIX_TIPO_DESCONHECIDO, PIX_TIPO_DEVOLUCAO, PIX_TIPO_PIX

_SP = ZoneInfo("America/Sao_Paulo")

_RE_PIX = re.compile(
    r"Ol[aá],\s*(?P<titular>[^\s]+)?\s*Voc[eê] recebeu um Pix no valor de R\$\s*(?P<valor>[\d.]+,\d{2})"
    r" de (?P<nome>.+?), na conta (?P<conta>\d+)\.",
    re.IGNORECASE,
)
_RE_DEVOLUCAO = re.compile(
    r"Ol[aá],\s*(?P<titular>[^\s]+)?\s*Voc[eê] recebeu a devolu[cç][aã]o de um Pix, no valor de R\$\s*"
    r"(?P<valor>[\d.]+,\d{2}), na conta (?P<conta>\d+)",
    re.IGNORECASE,
)
# O Google grava `dkim=pass header.i=@inter.co` (às vezes `header.d=inter.co`). Só o do Inter vale:
# um e-mail assinado por outro domínio que diga ser do Inter não passa.
_RE_DKIM_INTER = re.compile(
    # Domínio EXATO (ou subdomínio de) `inter.co`, terminando em espaço, `;` ou fim: `inter.co.evil.com`
    # e `inter.co-evil.com` não passam (revisão adversarial da 318).
    r"dkim=pass\s+header\.[id]=@?(?:[\w-]+\.)*inter\.co(?=[\s;]|$)",
    re.IGNORECASE,
)
# Só vale o `Authentication-Results` gravado pelo Google ao receber (o primeiro, o mais recente):
# um cabeçalho com esse nome escrito por quem mandou o e-mail não prova nada.
_AUTHSERV_GOOGLE = "mx.google.com"
REMETENTE_INTER = "no-reply@inter.co"


@dataclass(frozen=True)
class AvisoPix:
    """Aviso entendido (PIX recebido ou devolução)."""

    message_id: str
    tipo: str  # PIX_TIPO_PIX | PIX_TIPO_DEVOLUCAO
    valor: Decimal
    pagador_nome: str | None  # None na devolução
    numero_conta: str
    titular: str | None  # saudação: "JOAO", "PRIME"
    recebido_em: datetime  # horário de parede de São Paulo, naive
    autenticado: bool
    remetente: str
    assunto: str


@dataclass(frozen=True)
class AvisoDesconhecido:
    """E-mail do remetente certo que o leitor não entendeu — contado na saúde, nunca some calado."""

    message_id: str
    tipo: str  # PIX_TIPO_DESCONHECIDO
    recebido_em: datetime
    autenticado: bool
    remetente: str
    assunto: str


def _cabecalho(msg: Message, nome: str) -> str:
    bruto = msg.get(nome)
    if bruto is None:
        return ""
    try:
        return str(make_header(decode_header(bruto))).strip()
    except Exception:  # cabeçalho mal codificado: o texto cru serve para diagnóstico
        return str(bruto).strip()


def _texto(msg: Message) -> str:
    """Junta as partes de texto/HTML num texto corrido (tags fora, entidades decodificadas)."""
    pedacos: list[str] = []
    for parte in msg.walk():
        if parte.get_content_type() not in ("text/plain", "text/html"):
            continue
        carga = parte.get_payload(decode=True)
        if not carga:
            continue
        texto = carga.decode(parte.get_content_charset() or "utf-8", errors="replace")
        if parte.get_content_type() == "text/html":
            texto = re.sub(r"<[^>]+>", " ", texto)
        pedacos.append(html.unescape(texto))
    return re.sub(r"\s+", " ", " ".join(pedacos)).strip()


def _valor(texto: str) -> Decimal:
    return Decimal(texto.replace(".", "").replace(",", "."))


def _recebido_em(msg: Message) -> datetime:
    """`Date` do e-mail em horário de parede de SP (naive), como `CalendarEvent.start_at`."""
    try:
        quando = parsedate_to_datetime(_cabecalho(msg, "Date"))
    except (TypeError, ValueError):
        quando = None
    if quando is None:
        return datetime.now(_SP).replace(tzinfo=None, microsecond=0)
    if quando.tzinfo is None:  # sem fuso no cabeçalho: o Inter manda em UTC
        quando = quando.replace(tzinfo=ZoneInfo("UTC"))
    return quando.astimezone(_SP).replace(tzinfo=None)


def autenticado_pelo_inter(msg: Message) -> bool:
    """`True` se o remetente é exatamente o do Inter e o Google, ao receber, aprovou o DKIM do Inter.

    Lê só o primeiro `Authentication-Results` (o mais recente, gravado pelo servidor que recebeu) e
    exige que seja do `mx.google.com`.
    """
    _, endereco = parseaddr(_cabecalho(msg, "From"))
    if endereco.strip().lower() != REMETENTE_INTER:
        return False
    resultados = msg.get_all("Authentication-Results") or []
    if not resultados:
        return False
    primeiro = str(resultados[0]).strip()
    if not primeiro.lower().startswith(_AUTHSERV_GOOGLE):
        return False
    return bool(_RE_DKIM_INTER.search(primeiro))


def ler_aviso_inter(raw: bytes) -> AvisoPix | AvisoDesconhecido | None:
    """Lê um e-mail do Inter.

    Returns:
        `AvisoPix` (PIX recebido ou devolução), `AvisoDesconhecido` (formato que o leitor não
        conhece) ou `None` quando o e-mail não tem `Message-ID` (não há como guardá-lo uma vez só).
    """
    msg = message_from_bytes(raw)
    message_id = _cabecalho(msg, "Message-ID")
    if not message_id:
        return None
    remetente = _cabecalho(msg, "From")[:200]
    assunto = _cabecalho(msg, "Subject")[:200]
    recebido_em = _recebido_em(msg)
    autenticado = autenticado_pelo_inter(msg)
    texto = _texto(msg)

    achado = _RE_PIX.search(texto)
    if achado:
        return AvisoPix(
            message_id=message_id,
            tipo=PIX_TIPO_PIX,
            valor=_valor(achado.group("valor")),
            pagador_nome=achado.group("nome").strip()[:200],
            numero_conta=achado.group("conta"),
            titular=(achado.group("titular") or "").strip(" ,").upper() or None,
            recebido_em=recebido_em,
            autenticado=autenticado,
            remetente=remetente,
            assunto=assunto,
        )
    achado = _RE_DEVOLUCAO.search(texto)
    if achado:
        return AvisoPix(
            message_id=message_id,
            tipo=PIX_TIPO_DEVOLUCAO,
            valor=_valor(achado.group("valor")),
            pagador_nome=None,
            numero_conta=achado.group("conta"),
            titular=(achado.group("titular") or "").strip(" ,").upper() or None,
            recebido_em=recebido_em,
            autenticado=autenticado,
            remetente=remetente,
            assunto=assunto,
        )
    return AvisoDesconhecido(
        message_id=message_id,
        tipo=PIX_TIPO_DESCONHECIDO,
        recebido_em=recebido_em,
        autenticado=autenticado,
        remetente=remetente,
        assunto=assunto,
    )
