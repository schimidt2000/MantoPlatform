"""O funil das conversas (feature 335): até onde chegou cada conversa nova do período.

Derivado dos fatos, sem cartão para arrastar (a lição da feature 021): a coorte são as conversas cujo **primeiro
contato** (a primeira mensagem recebida da cliente ou o primeiro contato pelo anúncio, o que vier antes) caiu no
período; cada uma fica na **etapa mais avançada** que alcançou depois desse contato — Chegou, Orçamento enviado,
Formulário, Evento fechado, Pagou, Avaliou — e cada etapa conta quem chegou nela ou além. Assim o funil nunca cresce,
mesmo quando o orçamento foi pelo celular (coexistência) e só o evento aparece na Plataforma.

Só leitura. Uma consulta para a coorte e uma por tipo de fato, em lote (nunca uma por conversa).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from statistics import median
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import joinedload

from app import db
from app.constants import TZ_SP, now_sp
from app.conversas import constantes as K
from app.conversas import pontuacao_ops
from app.conversas.leitura_ops import nome_da_conversa
from app.conversas.recusa import campo
from app.models import AnuncioMeta, Conversa, MarketingPost, MarketingPostAnuncio, User

_SEM_RESPONSAVEL = "__sem_responsavel__"

# O primeiro contato de cada conversa e a campanha do primeiro anúncio dela. A agregação usa o índice
# (conversa_id, momento) das mensagens; o HAVING corta a coorte antes do JOIN.
_SQL_COORTE = """
WITH contatos AS (
    SELECT conversa_id, momento FROM conversa_mensagens WHERE direcao = :recebida
    UNION ALL
    SELECT conversa_id, momento FROM conversa_anuncios
), primeiro AS (
    SELECT conversa_id, MIN(momento) AS em FROM contatos GROUP BY conversa_id
    HAVING MIN(momento) >= :ini AND MIN(momento) < :fim
), anuncio AS (
    SELECT DISTINCT ON (ca.conversa_id) ca.conversa_id, am.campanha_nome, ca.anuncio_id, am.campanha_id
    FROM conversa_anuncios ca LEFT JOIN anuncios_meta am ON am.anuncio_id = ca.anuncio_id
    WHERE ca.tipo = :tipo_anuncio
    ORDER BY ca.conversa_id, ca.momento, ca.id
)
SELECT c.id, c.canal, c.client_id, c.responsavel_id, p.em, a.conversa_id IS NOT NULL, a.campanha_nome,
       a.anuncio_id, a.campanha_id,
       c.primeira_recebida_em, c.primeira_resposta_em, c.primeira_resposta_origem, c.perdida_motivo,
       c.qualificacao, c.lembrar_em
FROM primeiro p
JOIN conversas c ON c.id = p.conversa_id
LEFT JOIN anuncio a ON a.conversa_id = c.id
"""


@dataclass
class Linha:
    """Uma conversa da coorte e a etapa mais avançada dela (índice em ``ETAPAS_DO_FUNIL``)."""

    id: int
    canal: str
    client_id: int | None
    responsavel_id: int | None
    primeiro: datetime  # UTC
    tem_anuncio: bool
    campanha: str | None
    # A ordem dos campos é a do SELECT (``Linha(*linha)``): os da 351 vêm antes dos da 349 porque o
    # `_SQL_POR_ANUNCIO` só traz até o `campanha_id` e o resto fica no padrão.
    anuncio_id: str | None = None  # feature 351: o primeiro anúncio e a campanha dele, por id
    campanha_id: str | None = None
    # Feature 349: o que a conversa guarda (UTC) — primeira resposta, perda, decisão de qualificação e lembrete.
    recebida_em: datetime | None = None
    resposta_em: datetime | None = None
    resposta_origem: str | None = None
    perdida_motivo: str | None = None
    qualificacao: str | None = None
    lembrar_em: datetime | None = None
    etapa: int = 0
    eventos: list[int] = field(default_factory=list)
    qualificada: bool = False

    @property
    def chave_da_campanha(self) -> str:
        if not self.tem_anuncio:
            return K.SEM_ANUNCIO
        return self.campanha or K.CAMPANHA_DESCONHECIDA

    @property
    def minutos(self) -> int | None:
        """Minutos da primeira mensagem à primeira resposta (feature 349), ou ``None``."""
        if self.recebida_em is None or self.resposta_em is None:
            return None
        return max(0, int((self.resposta_em - self.recebida_em).total_seconds() // 60))

    @property
    def sem_autor(self) -> bool:
        return self.resposta_em is not None and self.resposta_origem in (K.ORIGEM_CELULAR, K.ORIGEM_OUTRO)

    @property
    def perdida(self) -> bool:
        """Perdida conta só se não fechou: a venda que fechou depois da perda é venda (FR-009)."""
        return self.perdida_motivo is not None and self.etapa < K.ETAPAS_DO_FUNIL.index("evento")


# ── Período ──────────────────────────────────────────────────────────────────────────────────────


def _data(valor: str | None, nome: str) -> date | None:
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError as exc:
        raise campo(nome, K.TEXTO_PERIODO_INVALIDO) from exc


def periodo(inicio: str | None, fim: str | None) -> tuple[date, date]:
    """As datas de São Paulo do período (inclusivas). Padrão: do dia 1º do mês corrente até hoje.

    Raises:
        Recusa: 422 em ``inicio``/``fim``.
    """
    hoje = now_sp().date()
    de = _data(inicio, "inicio") or hoje.replace(day=1)
    ate = _data(fim, "fim") or hoje
    if de > ate:
        raise campo("inicio", K.TEXTO_PERIODO_INVERTIDO)
    if (ate - de).days >= K.PERIODO_MAXIMO_DO_FUNIL:
        raise campo("inicio", K.TEXTO_PERIODO_LONGO)
    return de, ate


def _utc(dia: date) -> datetime:
    """A meia-noite do dia em São Paulo, como UTC sem fuso (o relógio das mensagens)."""
    return datetime.combine(dia, datetime.min.time(), TZ_SP).astimezone(UTC).replace(tzinfo=None)


def conferir_filtros(canal: str | None, dividir: str | None) -> None:
    """Raises: Recusa 422 em ``canal`` ou ``dividir``."""
    if canal and canal not in K.CANAIS:
        raise campo("canal", K.TEXTO_CANAL_INVALIDO)
    if dividir and dividir not in K.DIVISOES_DO_FUNIL:
        raise campo("dividir", K.TEXTO_DIVISAO_INVALIDA)


# ── Coorte e etapas ──────────────────────────────────────────────────────────────────────────────


def _coorte(de: date, ate: date) -> list[Linha]:
    linhas = db.session.execute(
        text(_SQL_COORTE),
        {
            "recebida": K.RECEBIDA,
            "tipo_anuncio": K.CONTATO_ANUNCIO,
            "ini": _utc(de),
            "fim": _utc(ate + timedelta(days=1)),
        },
    ).fetchall()
    return [Linha(*linha) for linha in linhas]


def _maximos(sql: str, ids: list[int]) -> dict[int, datetime]:
    """``{chave: o momento mais novo do fato}`` (``sql`` devolve chave e o máximo, filtrando ``ANY(:ids)``)."""
    if not ids:
        return {}
    return dict(db.session.execute(text(sql), {"ids": ids}).fetchall())


def _com_fato(sql: str, eventos: set[int]) -> set[int]:
    if not eventos:
        return set()
    return {linha[0] for linha in db.session.execute(text(sql), {"ids": list(eventos)}).fetchall()}


def _etapas(linhas: list[Linha]) -> None:
    """Põe em cada linha a etapa mais avançada (só os fatos depois do primeiro contato contam)."""
    conversas = [linha.id for linha in linhas]
    fichas = sorted({linha.client_id for linha in linhas if linha.client_id})
    envios = _maximos(
        "SELECT conversa_id, MAX(created_at) FROM orcamento_envios WHERE conversa_id = ANY(:ids) "
        "GROUP BY conversa_id",
        conversas,
    )
    # O orçamento ligado à ficha conta pelo envio (a hora em que a cliente o recebeu), como na linha do tempo;
    # sem envio registrado, pela criação.
    orcamentos = _maximos(
        "SELECT oh.client_id, MAX(COALESCE(oe.created_at, oh.created_at)) FROM orcamento_history oh "
        "LEFT JOIN orcamento_envios oe ON oe.orcamento_id = oh.id "
        "WHERE oh.client_id = ANY(:ids) GROUP BY oh.client_id",
        fichas,
    )
    formularios = _maximos(
        "SELECT client_id, MAX(created_at) FROM form_responses WHERE client_id = ANY(:ids) GROUP BY client_id",
        fichas,
    )
    eventos_da_ficha: dict[int, list[tuple[int, datetime, int | None]]] = defaultdict(list)
    if fichas:
        for client_id, evento_id, criado, lider in db.session.execute(
            text(
                # O principal do grupo só vale vivo: o cancelado não leva pagamento nem avaliação.
                "SELECT ec.client_id, ce.id, ce.created_at, lider.id FROM event_clients ec "
                "JOIN calendar_events ce ON ce.id = ec.event_id "
                "LEFT JOIN calendar_events lider ON lider.id = ce.group_leader_id AND lider.cancelled_at IS NULL "
                "WHERE ec.client_id = ANY(:ids) AND ce.cancelled_at IS NULL"
            ),
            {"ids": fichas},
        ).fetchall():
            eventos_da_ficha[client_id].append((evento_id, criado, lider))
    for linha in linhas:
        depois = linha.primeiro
        if (envios.get(linha.id) or datetime.min) >= depois:
            linha.etapa = 1
        if linha.client_id is None:
            continue
        if (orcamentos.get(linha.client_id) or datetime.min) >= depois:
            linha.etapa = max(linha.etapa, 1)
        if (formularios.get(linha.client_id) or datetime.min) >= depois:
            linha.etapa = 2
        # O evento de grupo (feature 137): o pagamento e a avaliação podem estar no principal.
        for evento_id, criado, lider in eventos_da_ficha.get(linha.client_id, []):
            if criado >= depois:
                linha.etapa = max(linha.etapa, 3)
                linha.eventos.extend(e for e in (evento_id, lider) if e)
    todos = {e for linha in linhas for e in linha.eventos}
    pagos = _com_fato(
        "SELECT DISTINCT event_id FROM event_payments WHERE event_id = ANY(:ids)", todos
    )
    pagos |= _com_fato(
        "SELECT DISTINCT event_id FROM event_installments WHERE received AND event_id = ANY(:ids)",
        todos,
    )
    avaliados = _com_fato(
        "SELECT DISTINCT event_id FROM client_feedbacks WHERE event_id = ANY(:ids)", todos
    )
    for linha in linhas:
        if pagos & set(linha.eventos):
            linha.etapa = 4
        if avaliados & set(linha.eventos):
            linha.etapa = 5


def _filtrar(linhas: list[Linha], canal: str | None, campanha: str | None) -> list[Linha]:
    return [
        linha
        for linha in linhas
        if (not canal or linha.canal == canal)
        and (not campanha or linha.chave_da_campanha == campanha)
    ]


def _linhas(
    inicio: str | None, fim: str | None, canal: str | None
) -> tuple[date, date, list[Linha]]:
    de, ate = periodo(inicio, fim)
    conferir_filtros(canal, None)
    linhas = _filtrar(_coorte(de, ate), canal, None)
    _etapas(linhas)
    # Feature 349: a qualificação (decisão da vendedora ou pontuação por regras), em lote.
    pontos = pontuacao_ops.pontuar(linhas)
    for linha in linhas:
        linha.qualificada = pontuacao_ops.qualificada(linha.qualificacao, pontos[linha.id])
    return de, ate, linhas


# ── Saída ────────────────────────────────────────────────────────────────────────────────────────


def _porcento(parte: int, base: int) -> float | None:
    return round(100 * parte / base, 1) if base else None


def _contar(linhas: list[Linha]) -> list[int]:
    """Quantas chegaram em cada etapa ou além."""
    return [sum(1 for linha in linhas if linha.etapa >= i) for i in range(len(K.ETAPAS_DO_FUNIL))]


def _mediana(valores: list[int]) -> int | None:
    return round(median(valores)) if valores else None


def _primeira_resposta(linhas: list[Linha]) -> dict[str, Any]:
    """Feature 349 (FR-006): o tempo da primeira resposta da coorte; a sem autor (celular) contada à parte."""
    minutos = [linha.minutos for linha in linhas if linha.minutos is not None]
    rapidas = sum(1 for m in minutos if m <= K.RESPOSTA_RAPIDA_MINUTOS)
    return {
        "respondidas": len(minutos),
        "sem_resposta": sum(1 for linha in linhas if linha.recebida_em and linha.resposta_em is None),
        "sem_autor": sum(1 for linha in linhas if linha.sem_autor),
        "mediana_minutos": _mediana(minutos),
        "ate_15_min": _porcento(rapidas, len(minutos)),
    }


def _motivos_de_perda(linhas: list[Linha]) -> list[dict[str, Any]]:
    """As perdidas da coorte por motivo, na ordem da lista fechada (só os motivos que aparecem)."""
    contagem = Counter(linha.perdida_motivo for linha in linhas if linha.perdida)
    return [
        {"codigo": m, "rotulo": K.ROTULO_DO_MOTIVO[m], "quantidade": contagem[m]}
        for m in K.MOTIVOS_DE_PERDA
        if contagem.get(m)
    ]


def _medidas_da_venda(linhas: list[Linha]) -> dict[str, Any]:
    """Qualificadas, perdidas e a primeira resposta de um grupo (feature 349)."""
    resposta = _primeira_resposta(linhas)
    return {
        "qualificadas": sum(1 for linha in linhas if linha.qualificada),
        "perdidas": sum(1 for linha in linhas if linha.perdida),
        "mediana_minutos": resposta["mediana_minutos"],
        "ate_15_min": resposta["ate_15_min"],
    }


def _rotulo_da_campanha(chave: str) -> str:
    if chave == K.SEM_ANUNCIO:
        return K.TEXTO_SEM_ANUNCIO
    if chave == K.CAMPANHA_DESCONHECIDA:
        return K.TEXTO_CAMPANHA_DESCONHECIDA
    return chave


_ROTULOS_DO_SEM = {
    K.SEM_ANUNCIO: K.TEXTO_SEM_ANUNCIO,
    K.CAMPANHA_DESCONHECIDA: K.TEXTO_CAMPANHA_DESCONHECIDA,
    K.SEM_FRENTE: K.TEXTO_SEM_FRENTE,
    K.SEM_PECA: K.TEXTO_SEM_PECA,
    K.SEM_CONCEITO: K.TEXTO_SEM_CONCEITO,
    _SEM_RESPONSAVEL: K.TEXTO_SEM_RESPONSAVEL,
}


def _por_vendedor(linhas: list[Linha]) -> tuple[dict[int, str], dict[str, str]]:
    chaves = {
        linha.id: str(linha.responsavel_id) if linha.responsavel_id else _SEM_RESPONSAVEL
        for linha in linhas
    }
    ids = [int(c) for c in set(chaves.values()) if c != _SEM_RESPONSAVEL]
    nomes = {str(u.id): u.name for u in User.query.filter(User.id.in_(ids)).all()} if ids else {}
    return chaves, {c: nomes.get(c, K.TEXTO_SEM_RESPONSAVEL) for c in chaves.values()}


def _por_frente(linhas: list[Linha]) -> tuple[dict[int, str], dict[str, str]]:
    """A frente da campanha do primeiro anúncio (feature 351) — a mesma regra do painel (correção
    manual > prefixo). Import tardio: o núcleo do marketing importa o domínio das conversas."""
    from app.constants import MARKETING_FRENTES
    from app.marketing import comando_ops

    correcoes = comando_ops.correcoes_de_frente()
    chaves = {}
    for linha in linhas:
        if not linha.tem_anuncio:
            chaves[linha.id] = K.SEM_ANUNCIO
            continue
        frente = comando_ops.frente_da_campanha(
            K.PLATAFORMA_DO_ANUNCIO, linha.campanha_id or "", linha.campanha, correcoes
        )
        chaves[linha.id] = frente or K.SEM_FRENTE
    return chaves, dict(MARKETING_FRENTES)


def _por_anuncio(linhas: list[Linha]) -> tuple[dict[int, str], dict[str, str]]:
    chaves = {
        linha.id: (linha.anuncio_id or K.CAMPANHA_DESCONHECIDA) if linha.tem_anuncio else K.SEM_ANUNCIO
        for linha in linhas
    }
    ids = [c for c in set(chaves.values()) if not c.startswith("__")]
    nomes = dict(
        db.session.query(AnuncioMeta.anuncio_id, AnuncioMeta.nome)
        .filter(AnuncioMeta.anuncio_id.in_(ids), AnuncioMeta.nome.isnot(None))
        .all()
    ) if ids else {}  # fmt: skip
    return chaves, {i: nomes.get(i) or K.TEXTO_ANUNCIO_SEM_NOME.format(id=i) for i in ids}


def pecas_dos_anuncios(anuncio_ids: set[str]) -> dict[str, tuple[int, str, str | None]]:
    """``{anúncio: (card, título, conceito)}`` dos anúncios da Meta ligados a um card (feature 351)."""
    if not anuncio_ids:
        return {}
    linhas = (
        db.session.query(MarketingPostAnuncio.ad_id, MarketingPost.id, MarketingPost.title, MarketingPost.conceito)
        .join(MarketingPost, MarketingPost.id == MarketingPostAnuncio.post_id)
        .filter(MarketingPostAnuncio.platform == K.PLATAFORMA_DO_ANUNCIO, MarketingPostAnuncio.ad_id.in_(anuncio_ids))
        .all()
    )
    return {ad: (pid, titulo, conceito) for ad, pid, titulo, conceito in linhas}


def _por_peca(linhas: list[Linha], dividir: str) -> tuple[dict[int, str], dict[str, str]]:
    """Peça (card) ou conceito do card do primeiro anúncio da conversa (feature 351)."""
    pecas = pecas_dos_anuncios({linha.anuncio_id for linha in linhas if linha.anuncio_id})
    sem = K.SEM_PECA if dividir == "peca" else K.SEM_CONCEITO
    chaves, rotulos = {}, {}
    for linha in linhas:
        peca = pecas.get(linha.anuncio_id or "")
        if not linha.tem_anuncio:
            chaves[linha.id] = K.SEM_ANUNCIO
        elif peca is None:
            chaves[linha.id] = sem
        elif dividir == "peca":
            chaves[linha.id] = str(peca[0])
            rotulos[str(peca[0])] = peca[1]
        else:
            chaves[linha.id] = peca[2] or K.SEM_CONCEITO
            rotulos[chaves[linha.id]] = peca[2] or K.TEXTO_SEM_CONCEITO
    return chaves, rotulos


def _divisao(linhas: list[Linha], dividir: str) -> tuple[dict[int, str], dict[str, str]]:
    """``(chave do grupo de cada conversa, rótulo de cada chave)`` — os ``__sem…`` vêm de ``_ROTULOS_DO_SEM``."""
    if dividir == "vendedor":
        return _por_vendedor(linhas)
    if dividir == "campanha":
        chaves = {linha.id: linha.chave_da_campanha for linha in linhas}
        return chaves, {c: c for c in chaves.values()}
    if dividir == "frente":
        return _por_frente(linhas)
    if dividir == "anuncio":
        return _por_anuncio(linhas)
    if dividir in ("peca", "conceito"):
        return _por_peca(linhas, dividir)
    return {linha.id: linha.canal for linha in linhas}, dict(K.ROTULO_DO_CANAL)


def _grupos(linhas: list[Linha], dividir: str) -> list[dict[str, Any]]:
    chaves, rotulos = _divisao(linhas, dividir)
    por_chave: dict[str, list[Linha]] = defaultdict(list)
    for linha in linhas:
        por_chave[chaves[linha.id]].append(linha)
    grupos = []
    for chave, do_grupo in por_chave.items():
        contagem = _contar(do_grupo)
        rotulo = _ROTULOS_DO_SEM.get(chave) or rotulos.get(chave) or chave
        grupos.append(
            {
                "chave": chave,
                "rotulo": rotulo,
                "quantidades": dict(zip(K.ETAPAS_DO_FUNIL, contagem, strict=True)),
                "conversao": _porcento(contagem[3], contagem[0]),
                **_medidas_da_venda(do_grupo),
            }
        )
    # Do grupo com mais conversas para o com menos; o "sem" vai por último.
    return sorted(
        grupos,
        key=lambda g: (g["chave"].startswith("__"), -g["quantidades"]["chegou"], g["rotulo"]),
    )


def _campanhas(linhas: list[Linha]) -> list[dict[str, Any]]:
    contagem: dict[str, int] = defaultdict(int)
    for linha in linhas:
        contagem[linha.chave_da_campanha] += 1
    opcoes = [
        {"valor": chave, "rotulo": _rotulo_da_campanha(chave), "quantidade": n}
        for chave, n in contagem.items()
    ]
    return sorted(
        opcoes, key=lambda o: (o["valor"].startswith("__"), -o["quantidade"], o["rotulo"])
    )


def funil(
    inicio: str | None,
    fim: str | None,
    canal: str | None = None,
    campanha: str | None = None,
    dividir: str | None = None,
) -> dict[str, Any]:
    """O funil do período (contracts/api.md).

    Raises:
        Recusa: 422 em ``inicio``, ``fim``, ``canal`` ou ``dividir``.
    """
    conferir_filtros(canal, dividir)
    de, ate, linhas = _linhas(inicio, fim, canal)
    filtradas = _filtrar(linhas, None, campanha)
    contagem = _contar(filtradas)
    etapas = [
        {
            "chave": chave,
            "rotulo": K.ROTULO_DA_ETAPA[chave],
            "quantidade": contagem[i],
            "sobre_chegou": _porcento(contagem[i], contagem[0]),
            "passagem": _porcento(contagem[i], contagem[i - 1]) if i else None,
        }
        for i, chave in enumerate(K.ETAPAS_DO_FUNIL)
    ]
    dividir = dividir or K.DIVISOES_DO_FUNIL[0]
    return {
        "periodo": {"inicio": de.isoformat(), "fim": ate.isoformat()},
        "total": contagem[0],
        "etapas": etapas,
        "dividir": dividir,
        "grupos": _grupos(filtradas, dividir),
        "campanhas": _campanhas(linhas),
        # Feature 349.
        "primeira_resposta": _primeira_resposta(filtradas),
        "qualificadas": sum(1 for linha in filtradas if linha.qualificada),
        "perdidas": sum(1 for linha in filtradas if linha.perdida),
        "motivos_de_perda": _motivos_de_perda(filtradas),
    }


def parados(
    inicio: str | None,
    fim: str | None,
    etapa: str | None,
    canal: str | None = None,
    campanha: str | None = None,
) -> dict[str, Any]:
    """As conversas cuja etapa mais avançada é ``etapa``, do primeiro contato mais novo para o mais antigo.

    Raises:
        Recusa: 422 em ``etapa`` e nos do período e do canal.
    """
    if etapa not in K.ETAPAS_DO_FUNIL:
        raise campo("etapa", K.TEXTO_ETAPA_INVALIDA)
    _, _, linhas = _linhas(inicio, fim, canal)
    indice = K.ETAPAS_DO_FUNIL.index(etapa)
    escolhidas = sorted(
        (linha for linha in _filtrar(linhas, None, campanha) if linha.etapa == indice),
        key=lambda linha: linha.primeiro,
        reverse=True,
    )
    mostradas = escolhidas[: K.PARADOS_POR_VEZ]
    conversas = {
        c.id: c
        for c in Conversa.query.options(joinedload(Conversa.cliente), joinedload(Conversa.responsavel))
        .filter(Conversa.id.in_([linha.id for linha in mostradas]))
        .all()
    } if mostradas else {}  # fmt: skip
    return {
        "etapa": etapa,
        "rotulo": K.ROTULO_DA_ETAPA[etapa],
        "total": len(escolhidas),
        "conversas": [
            {
                "id": linha.id,
                "nome": nome_da_conversa(conversas[linha.id]),
                "canal": linha.canal,
                "vendedor": conversas[linha.id].responsavel.name
                if conversas[linha.id].responsavel
                else None,
                "primeiro_contato": linha.primeiro.replace(tzinfo=UTC).isoformat(),
                "campanha": _rotulo_da_campanha(linha.chave_da_campanha),
                # Feature 349: a perda aparece aqui (clarify de 17/11), com a qualificação, a 1ª resposta e o lembrete.
                "perdida": {"motivo": linha.perdida_motivo, "rotulo": K.ROTULO_DO_MOTIVO[linha.perdida_motivo]}
                if linha.perdida_motivo in K.ROTULO_DO_MOTIVO
                else None,
                "qualificada": linha.qualificada,
                "primeira_resposta_minutos": linha.minutos,
                "primeira_resposta_sem_autor": linha.sem_autor,
                # Há mensagem dela e nenhuma resposta (a conversa só com reação ou anúncio não entra).
                "primeira_resposta_pendente": bool(linha.recebida_em and linha.resposta_em is None),
                "lembrete_em": linha.lembrar_em.replace(tzinfo=UTC).isoformat() if linha.lembrar_em else None,
            }
            for linha in mostradas
            if linha.id in conversas
        ],
    }


# ── Resultado real da peça (feature 351) ───────────────────────────────────────────────────────

# As conversas cujo PRIMEIRO anúncio está no conjunto (a mesma regra da coorte), com o primeiro contato delas.
# O filtro por anúncio vem antes dos contatos: só as mensagens dessas conversas são lidas.
_SQL_POR_ANUNCIO = """
WITH anuncio AS (
    SELECT DISTINCT ON (ca.conversa_id) ca.conversa_id, am.campanha_nome, ca.anuncio_id, am.campanha_id
    FROM conversa_anuncios ca LEFT JOIN anuncios_meta am ON am.anuncio_id = ca.anuncio_id
    WHERE ca.tipo = :tipo_anuncio
    ORDER BY ca.conversa_id, ca.momento, ca.id
), escolhidas AS (
    SELECT * FROM anuncio WHERE anuncio_id = ANY(:ids)
), contatos AS (
    SELECT conversa_id, momento FROM conversa_mensagens
    WHERE direcao = :recebida AND conversa_id IN (SELECT conversa_id FROM escolhidas)
    UNION ALL
    SELECT conversa_id, momento FROM conversa_anuncios WHERE conversa_id IN (SELECT conversa_id FROM escolhidas)
), primeiro AS (
    SELECT conversa_id, MIN(momento) AS em FROM contatos GROUP BY conversa_id
)
SELECT c.id, c.canal, c.client_id, c.responsavel_id, p.em, true, e.campanha_nome, e.anuncio_id, e.campanha_id
FROM escolhidas e
JOIN conversas c ON c.id = e.conversa_id
JOIN primeiro p ON p.conversa_id = c.id
"""

_ETAPA_DO_ORCAMENTO = K.ETAPAS_DO_FUNIL.index("orcamento")
_ETAPA_DO_EVENTO = K.ETAPAS_DO_FUNIL.index("evento")


def etapas_por_anuncio(anuncio_ids: set[str]) -> dict[str, dict[str, int]]:
    """``{anúncio: {conversas_reais, orcamentos, eventos}}`` de todas as conversas que chegaram por ele.

    Sem período: é o resultado da peça desde que ela existe. Mesma regra do funil (só fato depois do primeiro
    contato), pelas mesmas consultas em lote.
    """
    if not anuncio_ids:
        return {}
    linhas = [
        Linha(*linha)
        for linha in db.session.execute(
            text(_SQL_POR_ANUNCIO),
            {"tipo_anuncio": K.CONTATO_ANUNCIO, "recebida": K.RECEBIDA, "ids": sorted(anuncio_ids)},
        ).fetchall()
    ]
    _etapas(linhas)
    saida: dict[str, dict[str, int]] = {}
    for linha in linhas:
        s = saida.setdefault(linha.anuncio_id or "", {"conversas_reais": 0, "orcamentos": 0, "eventos": 0})
        s["conversas_reais"] += 1
        s["orcamentos"] += int(linha.etapa >= _ETAPA_DO_ORCAMENTO)
        s["eventos"] += int(linha.etapa >= _ETAPA_DO_EVENTO)
    return saida
