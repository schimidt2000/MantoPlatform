"""Núcleo puro dos contratos da ClickSign (feature 317): ler o nome, classificar, escolher a venda,
decidir o documento vigente, a situação, a cor e se dá para cobrar.

Módulo puro: não usa `flask.request`, não consulta o banco, não fala com a ClickSign e recebe `hoje`
por argumento. A sincronização (`sincronizar_ops`) junta os dados e chama estas funções; o verify as
testa sem rede.

O nome do envelope é a chave do vínculo porque os fluxos com formulário da conta montam o nome com as
respostas que a comercial transcreve: `DDMMAAAA + (DD) NNNNN-NNNN + Tema` (festa) e
`DDMMAAAA + Razão social + (DD) NNNNN-NNNN` (corporativo). A data é texto livre no fluxo — já
apareceram `DD-MM-AAAA`, `DDMMAAAA` e `DMMAAAA` — e a ClickSign devolve acento decomposto ("Ç" =
"C" + U+0327), por isso tudo passa por NFC antes (research R-02).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.constants import (
    CLICKSIGN_MARCA_ARTISTA,
    CLICKSIGN_TIPO_ARTISTA,
    CLICKSIGN_TIPO_CLIENTE,
    CLICKSIGN_TIPO_OUTRO,
    COBRAR_CONTRATO_BLOQUEIO_CANCELADA,
    COBRAR_CONTRATO_BLOQUEIO_SATELITE,
    COBRAR_CONTRATO_BLOQUEIOS,
    CONFERIR_CANCELADA,
    CONFERIR_DATA_ILEGIVEL,
    CONFERIR_EMPATE,
    CONFERIR_SEM_CANDIDATO,
    CONFERIR_SEM_TELEFONE,
    CONTRATO_AGUARDANDO,
    CONTRATO_ASSINADO,
    CONTRATO_ASSINADO_MANUAL,
    CONTRATO_PRAZO_AMARELO_ATE_DIAS,
    CONTRATO_PRAZO_VERMELHO_ATE_DIAS,
    CONTRATO_RECUSADO,
    CONTRATO_ROTULOS,
    CONTRATO_SEM_CONTRATO,
    CONTRATO_VENCIDO,
    COR_AMARELO,
    COR_CINZA,
    COR_VERMELHO,
    FORM_COR_AMARELO_ATE_DIAS,
    FORM_COR_VERMELHO_ATE_DIAS,
    MARCADORES_COMPROMISSO_INTERNO,
    VINCULO_LIGADO,
)

STATUS_EM_PROCESSO = "running"
STATUS_FECHADO = "closed"
STATUS_CANCELADO = "canceled"
STATUS_RASCUNHO = "draft"

_ORDEM_DA_COR = {COR_VERMELHO: 0, COR_AMARELO: 1, COR_CINZA: 2}
# Menor tema (sem acento e pontuação) que serve para desempatar.
TEMA_MINIMO = 3

_RE_DATA = re.compile(r"^(\d{1,2})[-./]?(\d{2})[-./]?(\d{4})$")
_RE_TELEFONE = re.compile(r"^\(?\s*(\d{2})\s*\)?\s*(\d{4,5})\s*-?\s*(\d{4})$")
_RE_EMAIL = re.compile(r"^\S+@\S+\.\S+$")
_RE_SUFIXO_COPIA = re.compile(r"\s*\(\d+\)\s*$")


# ── Nome do envelope ──────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class NomeLido:
    """O que o leitor tirou do nome do envelope.

    Attributes:
        data: Data do evento, se o primeiro pedaço formar um dia válido.
        data_escrita: O primeiro pedaço como veio (para a tela de conferência).
        telefone: Só dígitos com DDI 55 (mesmo formato de `Client.phone`), ou `None`.
        email: E-mail no lugar do telefone (um fluxo antigo), ou `None`.
        tema: Tema da festa (festa) ou razão social (corporativo), sem acento decomposto.
    """

    data: date | None
    data_escrita: str | None
    telefone: str | None
    email: str | None
    tema: str | None


def normalizar_nome(nome: str | None) -> str:
    """NFC, sem `.pdf`, sem o sufixo de cópia ` (1)` e sem espaço sobrando."""
    texto = unicodedata.normalize("NFC", nome or "").strip()
    if texto.lower().endswith(".pdf"):
        texto = texto[:-4].rstrip()
    return _RE_SUFIXO_COPIA.sub("", texto).strip()


def ler_data(texto: str) -> date | None:
    """`DD-MM-AAAA`, `DDMMAAAA` ou `DMMAAAA` → data; dia impossível → `None`."""
    achado = _RE_DATA.match(texto.strip())
    if not achado:
        return None
    dia, mes, ano = (int(parte) for parte in achado.groups())
    try:
        return date(ano, mes, dia)
    except ValueError:
        return None


def ler_telefone(texto: str) -> str | None:
    """`(11) 98492-5407` → `5511984925407` (DDI 55, como `normalize_phone` grava a ficha)."""
    achado = _RE_TELEFONE.match(texto.strip())
    if not achado:
        return None
    return "55" + "".join(achado.groups())


def ler_nome(nome: str | None) -> NomeLido:
    """Separa o nome pelos `+` e reconhece data, telefone, e-mail e o resto (tema ou razão)."""
    partes = [parte.strip() for parte in normalizar_nome(nome).split("+") if parte.strip()]
    if not partes:
        return NomeLido(None, None, None, None, None)
    data_escrita = partes[0] if re.fullmatch(r"[\d\-./]+", partes[0]) else None
    data = ler_data(partes[0]) if data_escrita else None
    telefone = email = None
    resto: list[str] = []
    for parte in partes[1:] if data_escrita else partes:
        if telefone is None and (lido := ler_telefone(parte)):
            telefone = lido
        elif email is None and _RE_EMAIL.match(parte):
            email = parte.lower()
        else:
            resto.append(parte)
    tema = " + ".join(resto) or None
    return NomeLido(data, data_escrita, telefone, email, tema[:200] if tema else None)


def classificar(nome: str | None, lido: NomeLido) -> str:
    """Cliente (data escrita + telefone ou e-mail), artista (contrato de prestação) ou outro."""
    if CLICKSIGN_MARCA_ARTISTA in normalizar_nome(nome).upper():
        return CLICKSIGN_TIPO_ARTISTA
    if lido.data_escrita and (lido.telefone or lido.email):
        return CLICKSIGN_TIPO_CLIENTE
    return CLICKSIGN_TIPO_OUTRO


def chave_telefone(digitos: str | None) -> str | None:
    """DDD + últimos 8 dígitos: casa celular antigo de 8 dígitos e número gravado sem o 55.

    `5511984925407` → `1184925407`; `11984925407` → `1184925407`; `551184925407` → `1184925407`.
    """
    so_digitos = re.sub(r"\D", "", digitos or "")
    if so_digitos.startswith("55") and len(so_digitos) in (12, 13):
        so_digitos = so_digitos[2:]
    if len(so_digitos) not in (10, 11):
        return None
    return so_digitos[:2] + so_digitos[-8:]


def canal_do_signatario(communicate_events: dict[str, Any] | None) -> str | None:
    """Por onde a ClickSign pediu a assinatura (`whatsapp`, `email`, `sms`, `none`)."""
    if not isinstance(communicate_events, dict):
        return None
    canal = communicate_events.get("signature_request")
    return str(canal) if canal else None


def texto_comparavel(texto: str | None) -> str:
    """Minúsculas, sem acento e só letras/dígitos: para comparar tema com tema."""
    decomposto = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", sem_acento.lower()).strip()


# ── Escolha da venda ──────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Candidato:
    """Uma venda viva cuja data e telefone batem com o documento.

    Attributes:
        event_id: O principal da venda (ou o avulso).
        temas: Textos para desempatar: título do evento e tema do formulário ligado.
        cancelada: A venda está cancelada (nunca liga sozinha — FR-005).
    """

    event_id: int
    temas: tuple[str, ...] = ()
    cancelada: bool = False


def _tema_bate(tema: str | None, candidato: Candidato) -> bool:
    """O tema do nome está contido num dos temas da venda (ou o contrário), sem acento."""
    alvo = texto_comparavel(tema)
    if len(alvo) < TEMA_MINIMO:
        return False
    # Tema da venda curto demais (título só com emoji, "15") bateria com qualquer coisa (C-20).
    temas = [texto_comparavel(t) for t in candidato.temas if t]
    return any(alvo in t or t in alvo for t in temas if len(t) >= TEMA_MINIMO)


def escolher_candidato(
    lido: NomeLido, candidatos: Sequence[Candidato]
) -> tuple[int | None, str | None]:
    """Decide a venda do documento: (event_id, None) para ligar, ou (None, motivo) para conferir.

    Regra (FR-004, research R-02): candidato vivo único liga; empate se resolve pelo tema; sem
    candidato, com data ilegível ou sem telefone nunca liga sozinho. Venda cancelada não liga.
    """
    if lido.data is None:
        return None, CONFERIR_DATA_ILEGIVEL
    if lido.telefone is None:
        return None, CONFERIR_SEM_TELEFONE
    vivos = [c for c in candidatos if not c.cancelada]
    if not vivos:
        return None, CONFERIR_CANCELADA if candidatos else CONFERIR_SEM_CANDIDATO
    if len(vivos) == 1:
        return vivos[0].event_id, None
    pelo_tema = [c for c in vivos if _tema_bate(lido.tema, c)]
    if len(pelo_tema) == 1:
        return pelo_tema[0].event_id, None
    return None, CONFERIR_EMPATE


# ── Documento vigente e situação da venda ─────────────────────────────────────────────────────


def _criado(documento: Any) -> datetime:
    return documento.criado_em or datetime.min


def documentos_da_venda(documentos: Iterable[Any]) -> list[Any]:
    """Documentos de cliente ligados, do mais recente para o mais antigo."""
    escolhidos = [
        d for d in documentos if d.tipo == CLICKSIGN_TIPO_CLIENTE and d.vinculo == VINCULO_LIGADO
    ]
    return sorted(escolhidos, key=lambda d: (_criado(d), d.id or 0), reverse=True)


def vigente(documentos: Iterable[Any]) -> Any | None:
    """O documento que diz a situação da venda (R-04).

    Vale o mais recente (premissa 3): o reenvio `(1)` assinado vence o original cancelado depois
    pelo prazo, porque foi criado depois dele; e o contrato novo de uma remarcação substitui o antigo
    assinado — se ele vencer ou for recusado, a venda precisa de assinatura de novo (analyze C-05).
    """
    ordenados = documentos_da_venda(documentos)
    return ordenados[0] if ordenados else None


def situacao_do_documento(documento: Any | None, assinado_manual: bool) -> str:
    """Situação da venda a partir do vigente e da marca manual do Superadmin (FR-007/FR-008)."""
    if documento is not None:
        if documento.status == STATUS_FECHADO:
            return CONTRATO_ASSINADO
        if documento.status in (STATUS_EM_PROCESSO, STATUS_RASCUNHO):
            return CONTRATO_ASSINADO_MANUAL if assinado_manual else CONTRATO_AGUARDANDO
        if assinado_manual:
            return CONTRATO_ASSINADO_MANUAL
        return CONTRATO_RECUSADO if documento.recusado else CONTRATO_VENCIDO
    return CONTRATO_ASSINADO_MANUAL if assinado_manual else CONTRATO_SEM_CONTRATO


def venda_entra(principal: Any) -> bool:
    """Venda que precisa de contrato: fora cancelada, ensaio, compromisso interno e loja virtual.

    Diferente da cobrança de valor, **cortesia entra** (clarify da 317).
    """
    from app.financeiro.vendas_ops import NON_SALE_EVENT_TYPE, is_loja_virtual

    if principal.cancelled_at:
        return False
    if principal.event_type == NON_SALE_EVENT_TYPE:
        return False
    if (principal.title or "").lstrip().startswith(MARCADORES_COMPROMISSO_INTERNO):
        return False
    return not is_loja_virtual(principal)


# ── Régua, selo e cobrança ────────────────────────────────────────────────────────────────────


def _cor_por_distancia(dias: int, vermelho_ate: int, amarelo_ate: int) -> str:
    if dias <= vermelho_ate:
        return COR_VERMELHO
    if dias <= amarelo_ate:
        return COR_AMARELO
    return COR_CINZA


def _pior(*cores: str) -> str:
    return min(cores, key=lambda cor: _ORDEM_DA_COR[cor])


def dias_ate(prazo: datetime | date | None, hoje: date) -> int | None:
    """Dias corridos até o prazo (negativo = passou)."""
    if prazo is None:
        return None
    dia = prazo.date() if isinstance(prazo, datetime) else prazo
    return (dia - hoje).days


def cor_do_contrato(
    situacao: str, prazo: datetime | None, dias_ate_o_evento: int, hoje: date
) -> str:
    """Régua da premissa 5 (confirmada no clarify) e do FR-010.

    Aguardando: a pior entre o prazo (vence hoje/amanhã = vermelho, 2–3 dias = amarelo) e a
    distância do evento (≤ 7 vermelho, 8–30 amarelo). Sem contrato: só a do evento. Vencido e
    recusado: sempre vermelho.
    """
    if situacao in (CONTRATO_VENCIDO, CONTRATO_RECUSADO):
        return COR_VERMELHO
    pelo_evento = _cor_por_distancia(
        dias_ate_o_evento, FORM_COR_VERMELHO_ATE_DIAS, FORM_COR_AMARELO_ATE_DIAS
    )
    if situacao == CONTRATO_AGUARDANDO:
        dias_prazo = dias_ate(prazo, hoje)
        if dias_prazo is None:
            return pelo_evento
        pelo_prazo = _cor_por_distancia(
            dias_prazo, CONTRATO_PRAZO_VERMELHO_ATE_DIAS, CONTRATO_PRAZO_AMARELO_ATE_DIAS
        )
        return _pior(pelo_prazo, pelo_evento)
    return pelo_evento


def selo_do_contrato(situacao: str, prazo: datetime | None, hoje: date) -> str:
    """Texto curto da linha: o prazo quando aguarda, senão o rótulo da situação."""
    if situacao == CONTRATO_AGUARDANDO:
        dias = dias_ate(prazo, hoje)
        if dias is None:
            return CONTRATO_ROTULOS[situacao]
        if dias < 0:
            return "Prazo vencido"
        if dias == 0:
            return "Vence hoje"
        if dias == 1:
            return "Vence amanhã"
        return f"Vence em {dias} dias"
    return CONTRATO_ROTULOS[situacao]


def rotulo_da_situacao(
    situacao: str, prazo: datetime | None, assinado_em: datetime | None, hoje: date
) -> str:
    """Frase da página do evento (FR-007)."""
    if situacao == CONTRATO_ASSINADO and assinado_em is not None:
        return f"Assinado em {assinado_em:%d/%m}"
    if situacao == CONTRATO_AGUARDANDO:
        return f"Aguardando assinatura — {selo_do_contrato(situacao, prazo, hoje).lower()}"
    return CONTRATO_ROTULOS[situacao]


def bloqueio_da_cobranca(situacao: str, *, eh_principal: bool, venda_viva: bool) -> str | None:
    """`None` quando dá para cobrar; senão o motivo em pt-BR (FR-012)."""
    if not venda_viva:
        return COBRAR_CONTRATO_BLOQUEIO_CANCELADA
    if not eh_principal:
        return COBRAR_CONTRATO_BLOQUEIO_SATELITE
    if situacao == CONTRATO_AGUARDANDO:
        return None
    return COBRAR_CONTRATO_BLOQUEIOS.get(situacao, CONTRATO_ROTULOS.get(situacao, situacao))


def resumo_por_cor(linhas: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Contagem por cor e o `para_agir` (vermelho + amarelo) das listas do painel."""
    por_cor = {COR_VERMELHO: 0, COR_AMARELO: 0, COR_CINZA: 0}
    for linha in linhas:
        cor = linha.get("severidade")
        if cor in por_cor:
            por_cor[cor] += 1
    return {"por_cor": por_cor, "para_agir": por_cor[COR_VERMELHO] + por_cor[COR_AMARELO]}
