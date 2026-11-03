"""A equipe na caixa de conversas: responsável, espera, alerta e notas (feature 328).

**Fila livre** (decisão do dono, 03/11): a conversa nova chega sem responsável, quem responde primeiro
pela Plataforma vira o responsável, e dá para assumir, transferir e devolver. Toda gravação do
responsável é condicional no próprio UPDATE (research R1/R2): na corrida, a primeira fica, sem "último
ganha", e sem trava de linha longa.

**Espera**: ``conversas.aguardando_desde`` guarda a primeira mensagem da cliente ainda sem resposta
(R3). A resposta da equipe (envio aceito pela Meta ou eco do celular) a encerra e apaga os avisos de
espera; o status ``failed`` que chega depois do aceite a reabre. A rotina ``alertar_esperas`` roda na
varredura do WhatsApp e avisa quem atende depois de 15 min, só das 9h às 21h de São Paulo (R4).

Camada de baixo do domínio: importa modelos, constantes, ``acesso``, ``leitura_ops``, ``relogio``,
``recusa`` e ``notificacoes_ops`` — **nunca** ``aviso_ops`` nem ``envio_ops``, que importam este
módulo (o import de volta fecharia um ciclo). Puro: sem ``flask.request`` nem ``current_user``.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, exists, func, or_, text
from sqlalchemy.orm import joinedload

from app import db
from app.constants import TZ_SP, now_sp
from app.conversas import constantes as K
from app.conversas.acesso import PAPEIS_DE_CONVERSAS, e_da_equipe, responsavel_ativo
from app.conversas.leitura_ops import nome_da_conversa
from app.conversas.recusa import Recusa, campo
from app.conversas.relogio import agora_utc
from app.models import Conversa, ConversaMensagem, ConversaNota, Notification, User
from app.notificacoes import notificacoes_ops
from app.push import constantes as KP
from app.push import push_ops

logger = logging.getLogger(__name__)

# Gravação condicional do responsável: só vale se ninguém mudou desde a leitura (R2).
_GRAVAR_RESPONSAVEL = text(
    "UPDATE conversas SET responsavel_id = :novo, assumida_em = :quando "
    "WHERE id = :id AND responsavel_id IS NOT DISTINCT FROM :atual"
)


# ── A equipe ─────────────────────────────────────────────────────────────────────────────────────


def membros_da_equipe() -> list[User]:
    """Para quem se pode transferir: ativos, com acesso e papel de conversas, por nome."""
    pessoas = notificacoes_ops.resolver_destinatarios(PAPEIS_DE_CONVERSAS)
    return sorted(pessoas, key=lambda u: (u.name or "").casefold())


def _epoch(momento: datetime) -> int:
    """Segundos desde 1970 de um UTC naive — a identidade do aviso, igual em qualquer máquina."""
    return int(momento.replace(tzinfo=UTC).timestamp())


def _conversa_ou_404(conversa_id: int) -> Conversa:
    conversa = db.session.get(Conversa, conversa_id)
    if conversa is None:
        raise Recusa("nao_encontrada", K.TEXTO_CONVERSA_NAO_ENCONTRADA, 404)
    return conversa


# ── Responsável ──────────────────────────────────────────────────────────────────────────────────


def _gravar_responsavel(conversa: Conversa, novo_id: int | None, quando: datetime | None) -> bool:
    """O UPDATE condicional. True = gravou; False = alguém mudou o responsável no meio."""
    resultado = db.session.execute(
        _GRAVAR_RESPONSAVEL,
        {"novo": novo_id, "quando": quando, "id": conversa.id, "atual": conversa.responsavel_id},
    )
    db.session.expire(conversa, ["responsavel_id", "assumida_em", "responsavel"])
    return bool(resultado.rowcount)


def resposta_da_equipe(conversa: Conversa, autor_id: int, momento: datetime) -> None:
    """A Meta aceitou um envio da Plataforma: atribui se a conversa está na fila e encerra a espera.

    A atribuição é ``WHERE responsavel_id IS NULL`` (FR-002): a resposta de outra pessoa numa
    conversa que já tem dono não a "rouba". **Não comita**: roda dentro do ``_despachar``.
    """
    if conversa.responsavel_id is None:
        db.session.execute(
            text(
                "UPDATE conversas SET responsavel_id = :autor, assumida_em = :momento "
                "WHERE id = :id AND responsavel_id IS NULL"
            ),
            {"autor": autor_id, "momento": momento, "id": conversa.id},
        )
        db.session.expire(conversa, ["responsavel_id", "assumida_em", "responsavel"])
    encerrar_espera(conversa, momento)


def definir_responsavel(
    conversa_id: int, acao: str, quem: User, responsavel_id: Any = None
) -> Conversa:
    """Assumir, transferir ou devolver à fila (FR-003/FR-004). Comita.

    Raises:
        Recusa: 422 (ação ou destino inválidos), 404 (conversa) ou 409 (``ja_assumida``,
            ``alterada``).
    """
    if acao not in K.ACOES_DO_RESPONSAVEL:
        raise campo("acao", K.TEXTO_ACAO_INVALIDA)
    conversa = _conversa_ou_404(conversa_id)
    no_celular: tuple[int, push_ops.Aviso] | None = None
    if acao == K.ACAO_ASSUMIR:
        _assumir(conversa, quem)
    elif acao == K.ACAO_TRANSFERIR:
        no_celular = _transferir(conversa, quem, _destino(responsavel_id))
    elif conversa.responsavel_id is not None and not _gravar_responsavel(conversa, None, None):
        raise _alterada()
    db.session.commit()
    if no_celular is not None:  # feature 332: depois do commit, nunca dentro (FR-006)
        push_ops.despachar([no_celular[0]], no_celular[1])
    return conversa


def _ja_assumida(conversa: Conversa) -> Recusa:
    nome = conversa.responsavel.name if conversa.responsavel else K.TEXTO_OUTRA_PESSOA
    return Recusa("ja_assumida", K.TEXTO_JA_ASSUMIDA.format(nome=nome), 409)


def _alterada() -> Recusa:
    db.session.rollback()
    return Recusa("alterada", K.TEXTO_ALTERADA, 409)


def _assumir(conversa: Conversa, quem: User) -> None:
    """Só da fila, ou de quem não é mais da equipe. Na corrida, quem perde vê o nome de quem ganhou."""
    if conversa.responsavel_id == quem.id:
        return
    if responsavel_ativo(conversa):
        raise _ja_assumida(conversa)
    if not _gravar_responsavel(conversa, quem.id, agora_utc()):
        db.session.rollback()
        db.session.refresh(conversa)
        raise _ja_assumida(conversa) if conversa.responsavel_id else _alterada()


def _destino(responsavel_id: Any) -> User:
    """A pessoa da equipe que vai receber a conversa (FR-004), ou a recusa no campo."""
    valido = isinstance(responsavel_id, int) and not isinstance(responsavel_id, bool)
    destino = db.session.get(User, responsavel_id) if valido else None
    if destino is None or not e_da_equipe(destino):
        raise campo("responsavel_id", K.TEXTO_DESTINO_INVALIDO)
    return destino


def _transferir(
    conversa: Conversa, quem: User, destino: User
) -> tuple[int, push_ops.Aviso] | None:
    """Grava a troca e o sino do destino; devolve o aviso no celular a mandar depois do commit."""
    if conversa.responsavel_id == destino.id:
        return None
    quando = agora_utc()
    if not _gravar_responsavel(conversa, destino.id, quando):
        raise _alterada()
    if destino.id == quem.id:
        return None
    titulo = _avisar_transferencia(conversa, quem, destino, quando)
    aviso = push_ops.Aviso(
        titulo=titulo,
        corpo=conversa.ultima_previa or "",
        link=f"/conversas?c={conversa.id}",
        tag=KP.tag_da_transferencia(conversa.id),
    )
    return destino.id, aviso


def _avisar_transferencia(conversa: Conversa, quem: User, destino: User, quando: datetime) -> str:
    """FR-018: o sino de quem recebe. Na transação da troca (regime A da 272): sem troca, sem aviso.
    Devolve o título, que o aviso no celular repete (332)."""
    titulo = K.TITULO_TRANSFERIDA.format(quem=quem.name, nome=nome_da_conversa(conversa))
    notificacoes_ops.emitir(
        notificacoes_ops.KIND_CONVERSA_TRANSFERIDA,
        title=titulo,
        body=conversa.ultima_previa,
        dedupe_key=f"conversa.transferida:{conversa.id}:{_epoch(quando)}",
        link_path=f"/conversas?c={conversa.id}",
        entidade=("conversa", conversa.id),
        destinatarios=[destino],
    )
    return titulo


# ── Espera ───────────────────────────────────────────────────────────────────────────────────────


def _resposta_valida():
    """Mensagem que conta como resposta da equipe: enviada sem falha, sem reação, e eco que não é
    "apagada/editada pelo celular" (o eco sem texto — áudio, foto, figurinha — conta)."""
    falsas = (K.TEXTO_APAGADA_NO_CELULAR, K.TEXTO_EDITADA_NO_CELULAR)
    return and_(
        ConversaMensagem.direcao == K.ENVIADA,
        ConversaMensagem.situacao != K.SITUACAO_FALHOU,
        ConversaMensagem.tipo != K.TIPO_REACAO,
        or_(
            ConversaMensagem.origem != K.ORIGEM_CELULAR,
            ConversaMensagem.texto.is_(None),
            ConversaMensagem.texto.notin_(falsas),
        ),
    )


def _ultima_resposta(conversa_id: int) -> datetime | None:
    return (
        db.session.query(func.max(ConversaMensagem.momento))
        .filter(ConversaMensagem.conversa_id == conversa_id, _resposta_valida())
        .scalar()
    )


def abrir_espera(conversa: Conversa, momento: datetime) -> None:
    """Mensagem nova da cliente: a espera conta da PRIMEIRA sem resposta (não comita).

    Gravação condicional no banco (outro worker pode ter encerrado a espera agora), e uma recebida
    mais antiga que a última resposta — a que a varredura reprocessou atrasada — não abre nada.
    """
    if conversa.aguardando_desde is not None and conversa.aguardando_desde <= momento:
        return
    ultima = _ultima_resposta(conversa.id)
    # Estritamente mais antiga: no mesmo segundo da resposta, a ordem é ambígua e a cliente espera.
    if ultima is not None and momento < ultima:
        return
    db.session.execute(
        text(
            "UPDATE conversas SET aguardando_desde = :momento WHERE id = :id "
            "AND (aguardando_desde IS NULL OR aguardando_desde > :momento)"
        ),
        {"momento": momento, "id": conversa.id},
    )
    db.session.expire(conversa, ["aguardando_desde"])


def encerrar_espera(conversa: Conversa, resposta_em: datetime) -> None:
    """A equipe respondeu: some a espera e o aviso dela; o de transferência fica (FR-008).

    Só encerra a espera que começou ANTES da resposta — a cliente que escreveu depois (num aviso
    que outro worker gravou no meio) continua esperando. Condicional no banco pelo mesmo motivo.
    """
    resultado = db.session.execute(
        text(
            "UPDATE conversas SET aguardando_desde = NULL "
            "WHERE id = :id AND aguardando_desde <= :resposta"
        ),
        {"id": conversa.id, "resposta": resposta_em},
    )
    db.session.expire(conversa, ["aguardando_desde"])
    if resultado.rowcount:
        notificacoes_ops.apagar_por_entidade(
            "conversa", conversa.id, kind=notificacoes_ops.KIND_CONVERSA_ESPERANDO
        )


def recalcular_espera(conversa: Conversa) -> None:
    """A resposta que a Meta recusou depois do aceite não conta: a espera volta à primeira recebida
    (que não seja reação) depois da última resposta que valeu (não comita)."""
    ultima = _ultima_resposta(conversa.id)
    primeira = db.session.query(func.min(ConversaMensagem.momento)).filter(
        ConversaMensagem.conversa_id == conversa.id,
        ConversaMensagem.direcao == K.RECEBIDA,
        ConversaMensagem.tipo != K.TIPO_REACAO,
    )
    if ultima is not None:
        primeira = primeira.filter(ConversaMensagem.momento > ultima)
    conversa.aguardando_desde = primeira.scalar()


# ── Alerta ───────────────────────────────────────────────────────────────────────────────────────


def _utc_de_sp(momento_sp: datetime) -> datetime:
    """O horário de São Paulo (sem fuso, como ``now_sp()``) em UTC naive (armadilha 3)."""
    return momento_sp.replace(tzinfo=TZ_SP).astimezone(UTC).replace(tzinfo=None)


def _esperas_a_avisar(agora: datetime) -> list[Conversa]:
    """Esperas de mais de 15 min, com a janela de 24 h aberta e ainda sem aviso, das mais antigas.

    Sem o "ainda sem aviso", a espera que ninguém responde (o "obrigada" final da cliente) ocuparia
    o lote por 24 h e as mais novas nunca avisariam. A espera encerrada apaga o aviso dela, então o
    aviso que existe é sempre o da espera atual.
    """
    ja_avisada = exists().where(
        Notification.entity_type == "conversa",
        Notification.entity_id == Conversa.id,
        Notification.kind == notificacoes_ops.KIND_CONVERSA_ESPERANDO,
    )
    return (
        Conversa.query.options(joinedload(Conversa.responsavel), joinedload(Conversa.cliente))
        .filter(
            Conversa.aguardando_desde > agora - K.JANELA,
            Conversa.aguardando_desde <= agora - K.ESPERA_PARA_ALERTA,
            ~ja_avisada,
        )
        .order_by(Conversa.aguardando_desde)
        .limit(K.VARREDURA_LOTE)
        .all()
    )


def tempo_de_espera(desde: datetime, agora: datetime) -> str:
    """ "16 min" ou, a partir de uma hora, "12 h" (como a lista da tela)."""
    minutos = int((agora - desde).total_seconds() // 60)
    return f"{minutos} min" if minutos < 60 else f"{minutos // 60} h"


def _avisar_espera(
    conversa: Conversa, agora: datetime
) -> tuple[int, tuple[list[int], push_ops.Aviso] | None]:
    """O sino da espera (quantas linhas gravou) e, se gravou, o aviso no celular a mandar depois do
    commit (332)."""
    titulo = K.TITULO_ESPERANDO.format(
        nome=nome_da_conversa(conversa), tempo=tempo_de_espera(conversa.aguardando_desde, agora)
    )
    com_responsavel = responsavel_ativo(conversa)
    gravados = notificacoes_ops.emitir(
        notificacoes_ops.KIND_CONVERSA_ESPERANDO,
        title=titulo,
        body=conversa.ultima_previa,
        # Um aviso por espera: a identidade é a conversa + o início da espera (FR-007).
        dedupe_key=f"conversa.esperando:{conversa.id}:{_epoch(conversa.aguardando_desde)}",
        link_path=f"/conversas?c={conversa.id}",
        entidade=("conversa", conversa.id),
        severity="urgent",
        # Com responsável da equipe, só ele; senão, a equipe pelo catálogo.
        destinatarios=[conversa.responsavel] if com_responsavel else None,
    )
    if not gravados:
        return 0, None  # já avisado nesta espera (dedupe do sino): o celular também não
    destinos = [conversa.responsavel_id] if com_responsavel else [u.id for u in membros_da_equipe()]
    aviso = push_ops.Aviso(
        titulo=titulo,
        corpo=conversa.ultima_previa or "",
        link=f"/conversas?c={conversa.id}",
        tag=KP.tag_da_espera(conversa.id),
    )
    return gravados, (destinos, aviso)


def alertar_esperas(agora_sp: datetime | None = None) -> dict[str, int]:
    """Uma rodada do alerta de cliente esperando (FR-007). Comita a rodada.

    Fora de ``HORARIO_DE_ALERTA`` (São Paulo) não faz nada: a espera da noite avisa às 9h.
    ``agora_sp`` injetável é para o verify; a varredura chama sem argumento.
    """
    agora_sp = agora_sp or now_sp()
    abre, fecha = K.HORARIO_DE_ALERTA
    if not abre <= agora_sp.hour < fecha:
        return {"alertas": 0}
    agora = _utc_de_sp(agora_sp)
    gravados = 0
    no_celular: list[tuple[list[int], push_ops.Aviso]] = []
    for conversa in _esperas_a_avisar(agora):
        linhas, aviso = _avisar_espera(conversa, agora)
        gravados += linhas
        if aviso:
            no_celular.append(aviso)
    db.session.commit()
    for destinos, aviso in no_celular:  # feature 332: depois do commit da rodada
        push_ops.despachar(destinos, aviso)
    return {"alertas": gravados}


# ── Notas internas ───────────────────────────────────────────────────────────────────────────────


def gravar_nota(conversa_id: int, texto: Any, autor_id: int) -> ConversaNota:
    """Nota interna (FR-009): nunca sai para a cliente e vale com a janela fechada. Comita."""
    texto = texto.strip() if isinstance(texto, str) else ""
    if not texto:
        raise campo("texto", K.TEXTO_NOTA_VAZIA)
    if len(texto) > K.NOTA_MAXIMA:
        raise campo("texto", K.TEXTO_NOTA_LONGA)
    conversa = _conversa_ou_404(conversa_id)
    nota = ConversaNota(
        conversa_id=conversa.id, autor_id=autor_id, texto=texto, created_at=agora_utc()
    )
    db.session.add(nota)
    db.session.commit()
    return nota


def notas_da_conversa(conversa_id: int) -> list[ConversaNota]:
    """As notas mais recentes (até ``NOTAS_NO_DETALHE``), em ordem cronológica."""
    linhas = (
        ConversaNota.query.options(joinedload(ConversaNota.autor))
        .filter(ConversaNota.conversa_id == conversa_id)
        .order_by(ConversaNota.created_at.desc(), ConversaNota.id.desc())
        .limit(K.NOTAS_NO_DETALHE)
        .all()
    )
    return list(reversed(linhas))
