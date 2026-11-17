"""De qual anúncio veio cada cliente (feature 334): o contato pelo anúncio, a campanha e a ficha.

- **Captura**, dentro da transação do aviso e sem chamada externa: o ``referral`` da Meta vira um
  ``ConversaAnuncio`` — no WhatsApp junto da mensagem; no Instagram também na abertura da conversa,
  antes de a cliente escrever. A chave UNIQUE (wamid/mid ou ``ref:{igsid}:{timestamp}``) segura o
  reenvio do aviso.
- **Campanha**, depois do commit: o aviso traz só o id e o título do anúncio; o nome da campanha, que
  o Desempenho casa com o export de campanhas, vem da Graph API (``meta_anuncios_client``). Cada
  anúncio é consultado uma vez, não importa em quantas conversas apareça; a falha volta pela
  varredura depois de 24 h.
- **Ficha**: o primeiro anúncio nunca é sobrescrito e dá a origem à ficha que ainda não tem; o mais
  recente acompanha a repescagem. A ficha nascida pela conversa sem anúncio ganha o canal.

Feature 348: o contato guarda o ``ctwa_clid`` (o clique, que a Conversions API pede para devolver a venda);
a consulta traz também o conjunto; a ficha guarda o id da campanha (o Desempenho casa por ele). E o contato
pelo **site** (o código da mensagem pronta, `codigo_ops`) também dá origem à ficha: vale o primeiro contato,
anúncio ou site.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app import db
from app.conversas import constantes as K
from app.conversas.configuracao import conexao_dos_anuncios
from app.conversas.relogio import agora_utc
from app.integracoes import meta_anuncios_client as mac
from app.integracoes import whatsapp_client as wc
from app.models import AnuncioMeta, Client, Conversa, ConversaAnuncio, OrigemCodigo

logger = logging.getLogger(__name__)

# "Não existe" na Graph: HTTP 404 ou o código 803. O código 100 (subcódigo 33) junta "não existe" com
# "sem acesso à conta de anúncios" e volta como falha comum: tratado como definitivo, o anúncio
# capturado antes de a permissão chegar nunca ganharia a campanha.
_NAO_EXISTE = 803
# Marca da consulta em andamento: o processo que morre no meio deixa a linha para a varredura.
_CONSULTANDO = "consultando"


def _texto(valor: Any, limite: int) -> str | None:
    return str(valor or "").strip()[:limite] or None


# ── Captura ──────────────────────────────────────────────────────────────────────────────────────


def contato_do_whatsapp(
    conversa: Conversa, chave: str, referral: dict[str, Any], momento: datetime
) -> None:
    """O ``messages[].referral`` do WhatsApp: ``source_type`` ``ad`` é anúncio, ``post`` é publicação."""
    tipo = {"ad": K.CONTATO_ANUNCIO, "post": K.CONTATO_PUBLICACAO}.get(
        str(referral.get("source_type") or "").lower(), K.CONTATO_OUTRO
    )
    registrar_contato(
        conversa,
        chave=chave,
        tipo=tipo,
        anuncio_id=referral.get("source_id"),
        titulo=referral.get("headline") or referral.get("body"),
        link=referral.get("source_url"),
        momento=momento,
        ctwa_clid=referral.get("ctwa_clid"),
    )


def contato_do_instagram(
    conversa: Conversa, chave: str, referral: dict[str, Any], momento: datetime
) -> None:
    """O ``referral`` do Instagram: ``source`` ``ADS`` é anúncio (``ad_id``); o resto, outro."""
    anuncio = str(referral.get("source") or "").upper() == "ADS"
    contexto = referral.get("ads_context_data")
    contexto = contexto if isinstance(contexto, dict) else {}
    registrar_contato(
        conversa,
        chave=chave,
        tipo=K.CONTATO_ANUNCIO if anuncio else K.CONTATO_OUTRO,
        anuncio_id=referral.get("ad_id") if anuncio else None,
        titulo=contexto.get("ad_title"),
        link=None,
        momento=momento,
    )


def registrar_contato(
    conversa: Conversa,
    *,
    chave: str,
    tipo: str,
    anuncio_id: Any,
    titulo: Any,
    link: Any,
    momento: datetime,
    ctwa_clid: Any = None,
    codigo_id: int | None = None,
) -> bool:
    """Grava o contato sem duplicar (FR-001) e, no anúncio, deixa-o na fila da consulta e na ficha.

    O contato pelo site (feature 348) vai à ficha também. Devolve se o contato é novo. Não comita: é a
    transação do aviso.
    """
    anuncio_id = _texto(anuncio_id, 64)
    if tipo == K.CONTATO_ANUNCIO and not anuncio_id:
        tipo = K.CONTATO_OUTRO  # anúncio sem id não tem campanha a perguntar
    tabela = ConversaAnuncio.__table__
    linha = db.session.execute(
        pg_insert(tabela)
        .values(
            conversa_id=conversa.id,
            canal=conversa.canal,
            chave=chave[:255],
            tipo=tipo,
            anuncio_id=anuncio_id,
            titulo=_texto(titulo, 255),
            link=_texto(link, 2000),
            momento=momento,
            created_at=agora_utc(),
            ctwa_clid=_texto(ctwa_clid, 512),
            codigo_id=codigo_id,
        )
        .on_conflict_do_nothing(index_elements=["chave"])
        .returning(tabela.c.id)
    ).first()
    if linha is None:
        return False
    if tipo == K.CONTATO_ANUNCIO:
        # `consultado_em` vazio é a fila: o mesmo anúncio em outra conversa não pergunta de novo.
        db.session.execute(
            pg_insert(AnuncioMeta.__table__)
            .values(anuncio_id=anuncio_id, definitivo=False)
            .on_conflict_do_nothing(index_elements=["anuncio_id"])
        )
    if tipo in (K.CONTATO_ANUNCIO, K.CONTATO_SITE):
        ficha = db.session.get(Client, conversa.client_id) if conversa.client_id else None
        if ficha is not None:
            aplicar_na_ficha(conversa, ficha)
    return True


# ── Ficha ────────────────────────────────────────────────────────────────────────────────────────


def _campanha(anuncio_id: str | None) -> str | None:
    anuncio = db.session.get(AnuncioMeta, anuncio_id) if anuncio_id else None
    return anuncio.campanha_nome if anuncio is not None else None


def _sem_origem(ficha: Client) -> bool:
    """Nada diz de onde a ficha veio: nem a origem nem a atribuição (formulário, Kommo, outro anúncio)."""
    return not any(
        (valor or "").strip() for valor in (ficha.lead_origin, ficha.utm_source, ficha.utm_campaign)
    )


def _origem_do_anuncio(ficha: Client, contato: ConversaAnuncio) -> None:
    anuncio = db.session.get(AnuncioMeta, contato.anuncio_id) if contato.anuncio_id else None
    ficha.lead_origin = K.ORIGEM_DO_ANUNCIO.get(contato.canal)
    ficha.utm_source = K.UTM_SOURCE_DO_ANUNCIO
    ficha.utm_medium = K.UTM_MEDIUM_DO_ANUNCIO
    # Desconhecidas ainda: a consulta, quando responder, preenche (`_propagar`).
    ficha.utm_campaign = ((anuncio.campanha_nome if anuncio else None) or "")[:200] or None
    ficha.utm_campaign_id = anuncio.campanha_id if anuncio else None


def _origem_do_site(ficha: Client, contato: ConversaAnuncio) -> None:
    """A origem do clique no site (feature 348). Sem ``utm_source``, o clique com id do Google é
    "google"/"cpc" — é o que o Desempenho reconhece como Google Ads."""
    codigo = db.session.get(OrigemCodigo, contato.codigo_id) if contato.codigo_id else None
    if codigo is None:
        return
    do_google = any((codigo.gclid, codigo.gbraid, codigo.wbraid))
    ficha.lead_origin = K.ORIGEM_DO_SITE
    ficha.utm_source = codigo.utm_source or (K.UTM_SOURCE_DO_GOOGLE if do_google else None)
    ficha.utm_medium = codigo.utm_medium or (K.UTM_MEDIUM_DO_CLIQUE if do_google else None)
    ficha.utm_campaign = codigo.utm_campaign
    ficha.utm_campaign_id = codigo.campanha_id


def aplicar_na_ficha(conversa: Conversa, ficha: Client) -> bool:
    """O primeiro e o mais recente anúncio da conversa na ficha (FR-004, FR-005, FR-007).

    A origem (``lead_origin``/``utm_*``) da ficha que ainda não tem vem do PRIMEIRO contato, anúncio ou
    site (feature 348); o primeiro anúncio nunca é sobrescrito. Devolve se a conversa tem contato por
    anúncio ou pelo site. Não comita.
    """
    contatos = (
        ConversaAnuncio.query.filter(
            ConversaAnuncio.conversa_id == conversa.id,
            ConversaAnuncio.tipo.in_((K.CONTATO_ANUNCIO, K.CONTATO_SITE)),
        )
        .order_by(ConversaAnuncio.momento, ConversaAnuncio.id)
        .all()
    )
    if not contatos:
        return False
    anuncios = [c for c in contatos if c.tipo == K.CONTATO_ANUNCIO]
    if anuncios and ficha.anuncio_origem_id is None:
        ficha.anuncio_origem_id = anuncios[0].anuncio_id
        ficha.anuncio_origem_em = anuncios[0].momento
    if _sem_origem(ficha):
        primeiro = contatos[0]
        if primeiro.tipo == K.CONTATO_ANUNCIO:
            _origem_do_anuncio(ficha, primeiro)
        else:
            _origem_do_site(ficha, primeiro)
    if anuncios:
        recente = anuncios[-1]
        if ficha.anuncio_recente_em is None or recente.momento > ficha.anuncio_recente_em:
            ficha.anuncio_recente_id = recente.anuncio_id
            ficha.anuncio_recente_em = recente.momento
    return True


def ao_ganhar_ficha(conversa: Conversa, ficha: Client, *, nova: bool) -> None:
    """A conversa acabou de ganhar a ficha: os anúncios dela entram; sem anúncio, a ficha que nasceu
    agora pela conversa ganha o canal como origem (FR-006). A ficha antiga sem origem fica como está:
    a conversa de hoje não diz como ela chegou. Não comita."""
    if not aplicar_na_ficha(conversa, ficha) and nova and not (ficha.lead_origin or "").strip():
        ficha.lead_origin = K.ORIGEM_ORGANICA.get(conversa.canal)


# ── Campanha ─────────────────────────────────────────────────────────────────────────────────────


def _reivindicar(condicao: str, params: dict[str, Any]) -> list[str]:
    """Claim por linha (``SKIP LOCKED``): dois workers nunca perguntam o mesmo anúncio."""
    linhas = db.session.execute(
        text(
            "UPDATE anuncios_meta SET consultado_em = :agora, erro = :consultando "
            "WHERE anuncio_id IN (SELECT anuncio_id FROM anuncios_meta "
            f"WHERE {condicao} ORDER BY anuncio_id LIMIT :limite FOR UPDATE SKIP LOCKED) "
            "RETURNING anuncio_id"
        ),
        {"agora": agora_utc(), "consultando": _CONSULTANDO, "limite": K.ANUNCIOS_POR_VEZ, **params},
    ).fetchall()
    db.session.commit()
    return [linha[0] for linha in linhas]


def _propagar(anuncio_id: str, campanha: str, campanha_id: str | None = None) -> None:
    """A campanha que chegou depois vai às fichas que este anúncio trouxe e ainda estão sem ela
    (FR-005). Só as que a 334 atribuiu: a origem que veio de outro lugar não muda. Feature 348: o id
    da campanha vai junto, também para a ficha que já tinha o nome e ainda não o id."""
    db.session.execute(
        text(
            "UPDATE clients SET "
            "utm_campaign = CASE WHEN utm_campaign IS NULL OR utm_campaign = '' THEN :campanha "
            "ELSE utm_campaign END, "
            "utm_campaign_id = COALESCE(utm_campaign_id, :campanha_id) "
            "WHERE anuncio_origem_id = :anuncio AND utm_source = :fonte AND utm_medium = :meio "
            "AND (utm_campaign IS NULL OR utm_campaign = '' OR utm_campaign_id IS NULL)"
        ),
        {
            "campanha": campanha[:200],
            "campanha_id": campanha_id,
            "anuncio": anuncio_id,
            "fonte": K.UTM_SOURCE_DO_ANUNCIO,
            "meio": K.UTM_MEDIUM_DO_ANUNCIO,
        },
    )


def _gravar(anuncio_id: str, **valores: Any) -> None:
    anuncio = db.session.get(AnuncioMeta, anuncio_id)
    for nome, valor in valores.items():
        setattr(anuncio, nome, valor)
    anuncio.consultado_em = agora_utc()
    db.session.commit()


def _consultar_um(conexao: wc.ConexaoMeta, anuncio_id: str) -> None:
    try:
        dados = mac.consultar_anuncio(conexao, anuncio_id)
    except wc.WhatsappRecusou as exc:
        definitivo = exc.status == 404 or exc.code == _NAO_EXISTE
        codigo = f"[{exc.code}] " if exc.code is not None else ""
        _gravar(anuncio_id, erro=f"{codigo}{exc}"[:255], definitivo=definitivo)
        logger.info("[anuncios] a Meta recusou a consulta do anúncio %s: %s", anuncio_id, exc)
        return
    except Exception as exc:  # noqa: BLE001 — rede, tempo ou resposta estranha: a varredura refaz
        _gravar(anuncio_id, erro=f"{type(exc).__name__}: {exc}"[:255])
        logger.warning("[anuncios] consulta do anúncio %s falhou: %s", anuncio_id, exc)
        return
    campanha = _texto(dados.get("campanha_nome"), 255)
    campanha_id = _texto(dados.get("campanha_id"), 64)
    if campanha:
        _propagar(anuncio_id, campanha, campanha_id)
    _gravar(
        anuncio_id,
        nome=_texto(dados.get("nome"), 255),
        campanha_id=campanha_id,
        campanha_nome=campanha,
        conjunto_id=_texto(dados.get("conjunto_id"), 64),
        conjunto_nome=_texto(dados.get("conjunto_nome"), 255),
        erro=None,
        definitivo=False,
    )


def _consultar(condicao: str, params: dict[str, Any]) -> int:
    """Consulta o lote que cumpre ``condicao``. Nunca levanta: o aviso já foi gravado e fechado."""
    conexao = conexao_dos_anuncios()
    if conexao is None:
        return 0  # travado ou sem token: o anúncio espera na fila (FR-011)
    consultados = 0
    try:
        for anuncio_id in _reivindicar(condicao, params):
            _consultar_um(conexao, anuncio_id)
            consultados += 1
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        logger.warning("[anuncios] consulta interrompida: %s", exc)
    return consultados


def consultar_pendentes() -> int:
    """Os anúncios nunca consultados (FR-002). Chamado depois do commit de cada aviso."""
    return _consultar("consultado_em IS NULL", {})


def _propagar_pendentes() -> int:
    """A campanha já conhecida que não chegou à ficha: a ficha atribuída (ainda sem a campanha) enquanto
    outro worker consultava o mesmo anúncio não é vista pelo ``_propagar`` dele. Idempotente."""
    resultado = db.session.execute(
        text(
            "UPDATE clients SET "
            "utm_campaign = CASE WHEN clients.utm_campaign IS NULL OR clients.utm_campaign = '' "
            "THEN LEFT(anuncios_meta.campanha_nome, 200) ELSE clients.utm_campaign END, "
            "utm_campaign_id = COALESCE(clients.utm_campaign_id, anuncios_meta.campanha_id) "
            "FROM anuncios_meta "
            "WHERE clients.anuncio_origem_id = anuncios_meta.anuncio_id "
            "AND anuncios_meta.campanha_nome IS NOT NULL "
            "AND clients.utm_source = :fonte AND clients.utm_medium = :meio "
            "AND (clients.utm_campaign IS NULL OR clients.utm_campaign = '' "
            "OR (clients.utm_campaign_id IS NULL AND anuncios_meta.campanha_id IS NOT NULL))"
        ),
        {"fonte": K.UTM_SOURCE_DO_ANUNCIO, "meio": K.UTM_MEDIUM_DO_ANUNCIO},
    )
    db.session.commit()
    return resultado.rowcount or 0


def reconsultar() -> dict[str, int]:
    """Os que falharam há mais de 24 h, menos os que a Meta disse que não existem (FR-003), e a campanha
    que ficou para trás em alguma ficha. Varredura."""
    prazo = agora_utc() - K.RECONSULTA_DO_ANUNCIO
    feitos = _consultar(
        "erro IS NOT NULL AND NOT definitivo AND consultado_em < :prazo", {"prazo": prazo}
    )
    return {"anuncios_consultados": feitos, "campanhas_propagadas": _propagar_pendentes()}


# ── Leitura ──────────────────────────────────────────────────────────────────────────────────────


def _iso(momento: datetime | None) -> str | None:
    return momento.replace(tzinfo=UTC).isoformat() if momento is not None else None


def anuncio_da_conversa(conversa_id: int) -> dict[str, Any] | None:
    """O contato mais recente por anúncio ou publicação, para o cabeçalho da conversa (FR-008)."""
    contato = (
        ConversaAnuncio.query.filter(
            ConversaAnuncio.conversa_id == conversa_id,
            ConversaAnuncio.tipo.in_((K.CONTATO_ANUNCIO, K.CONTATO_PUBLICACAO)),
        )
        .order_by(ConversaAnuncio.momento.desc(), ConversaAnuncio.id.desc())
        .first()
    )
    if contato is None:
        return None
    campanha = _campanha(contato.anuncio_id) if contato.tipo == K.CONTATO_ANUNCIO else None
    return {
        "tipo": contato.tipo,
        "titulo": contato.titulo,
        "campanha": campanha,
        "link": contato.link,
        "quando": _iso(contato.momento),
    }


def _anuncio_da_ficha(anuncio_id: str | None, momento: datetime | None) -> dict[str, Any] | None:
    if not anuncio_id:
        return None
    contato = (
        ConversaAnuncio.query.filter(
            ConversaAnuncio.anuncio_id == anuncio_id,
            or_(ConversaAnuncio.titulo.isnot(None), ConversaAnuncio.link.isnot(None)),
        )
        .order_by(ConversaAnuncio.momento.desc())
        .first()
    )
    anuncio = db.session.get(AnuncioMeta, anuncio_id)
    return {
        "anuncio_id": anuncio_id,
        # O título é o que a cliente viu; sem ele, o nome interno do anúncio na Meta.
        "titulo": (contato.titulo if contato else None) or (anuncio.nome if anuncio else None),
        "campanha": anuncio.campanha_nome if anuncio else None,
        "quando": _iso(momento),
    }


def origem_da_ficha(ficha: Client) -> dict[str, Any]:
    """A origem, a campanha e o primeiro e o mais recente anúncio, para a ficha (FR-009)."""
    return {
        "lead_origin": ficha.lead_origin,
        "campanha": ficha.utm_campaign,
        "primeiro": _anuncio_da_ficha(ficha.anuncio_origem_id, ficha.anuncio_origem_em),
        "recente": _anuncio_da_ficha(ficha.anuncio_recente_id, ficha.anuncio_recente_em),
    }
