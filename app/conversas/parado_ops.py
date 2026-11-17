"""Orçamento parado, lembrete e régua (feature 349, FR-015, FR-019 a FR-021).

**Orçamento parado** tem uma definição só, escrita aqui uma vez e usada pela lista e pela régua: o último orçamento
que a cliente recebeu (o envio pela conversa ou o orçamento ligado à ficha — sem envio, a criação, como no funil),
depois do primeiro contato, sem formulário nem evento vivo da ficha depois dele, e a conversa não perdida.

**A régua** avisa no sino quando esse orçamento completa 2, 5 e 9 dias (a janela de decisão da família é de 6 a 10
dias, pesquisa §8.4) e acaba no 10º dia. Um aviso por degrau e por orçamento (a ``dedupe_key`` leva os dois); depois
de dias sem varredura, sai só o degrau atual. **O lembrete** ("Lembrar amanhã") vence às 9h e avisa quem marcou.
Os dois só das 9h às 21h de São Paulo (o horário do alerta de espera, 328) e **nunca escrevem na conversa nem falam
com a Meta**: são avisos para a equipe.

Roda na varredura das conversas (``varredura.ciclo_de_varredura``), que só existe com o CRM ligado. Os três workers
varrem juntos sem lock: a idempotência é a ``UNIQUE(user_id, dedupe_key)`` do sino e o UPDATE condicional do
lembrete. O aviso no celular (332) sai depois do commit.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.sql.elements import TextClause

from app import db
from app.constants import TZ_SP, now_sp
from app.conversas import constantes as K
from app.conversas.acesso import e_da_equipe, responsavel_ativo
from app.conversas.leitura_ops import nome_da_conversa
from app.models import Conversa
from app.notificacoes import notificacoes_ops
from app.push import constantes as KP
from app.push import push_ops

logger = logging.getLogger(__name__)


def _ultimo_orcamento(c: str) -> str:
    """SQL do último orçamento recebido pela conversa de apelido ``c`` (``GREATEST`` ignora o nulo)."""
    return (
        "GREATEST("
        f"(SELECT MAX(oe.created_at) FROM orcamento_envios oe WHERE oe.conversa_id = {c}.id), "
        "(SELECT MAX(COALESCE(oe2.created_at, oh.created_at)) FROM orcamento_history oh "
        "LEFT JOIN orcamento_envios oe2 ON oe2.orcamento_id = oh.id "
        f"WHERE oh.client_id = {c}.client_id))"
    )


def _sem_decisao(c: str, em: str) -> str:
    """SQL: depois do primeiro contato, sem formulário nem evento vivo da ficha depois, conversa não perdida."""
    return (
        f"{em} >= LEAST({c}.primeira_recebida_em, {c}.created_at) "
        f"AND {c}.perdida_em IS NULL "
        "AND NOT EXISTS (SELECT 1 FROM form_responses fr "
        f"WHERE fr.client_id = {c}.client_id AND fr.created_at >= {em}) "
        "AND NOT EXISTS (SELECT 1 FROM event_clients ec JOIN calendar_events ce ON ce.id = ec.event_id "
        f"WHERE ec.client_id = {c}.client_id AND ce.cancelled_at IS NULL AND ce.created_at >= {em})"
    )


def filtro_da_lista(dias: int, agora: datetime) -> TextClause:
    """O recorte "Orçamento parado há ``dias`` dias ou mais" sobre ``conversas`` (a tabela da consulta da lista)."""
    return text(
        f"EXISTS (SELECT 1 FROM (SELECT {_ultimo_orcamento('conversas')} AS em) u "
        f"WHERE u.em IS NOT NULL AND u.em <= :limite_parado AND {_sem_decisao('conversas', 'u.em')})"
    ).bindparams(limite_parado=agora - timedelta(days=dias))


def parado_da_conversa(conversa_id: int, agora: datetime) -> tuple[datetime, int] | None:
    """O último orçamento sem decisão e os dias inteiros desde ele (painel da venda), ou ``None``."""
    linha = db.session.execute(
        text(
            f"SELECT u.em FROM conversas c CROSS JOIN LATERAL (SELECT {_ultimo_orcamento('c')} AS em) u "
            f"WHERE c.id = :id AND u.em IS NOT NULL AND {_sem_decisao('c', 'u.em')}"
        ),
        {"id": conversa_id},
    ).first()
    if linha is None:
        return None
    return linha[0], max(0, (agora - linha[0]).days)


# ── A régua ──────────────────────────────────────────────────────────────────────────────────────

# Os candidatos da rodada: a conversa, o orçamento e o degrau atual, só os que ainda não avisaram nesse degrau.
# O pré-filtro (orçamento recebido dentro da régua) evita calcular o último orçamento de todas as conversas.
_SQL_REGUA = f"""
SELECT c.id, u.em, d.degrau
FROM conversas c
CROSS JOIN LATERAL (SELECT {_ultimo_orcamento("c")} AS em) u
CROSS JOIN LATERAL (
    SELECT CASE WHEN u.em <= :d9 THEN 9 WHEN u.em <= :d5 THEN 5 ELSE 2 END AS degrau
) d
WHERE c.perdida_em IS NULL
  AND (c.id IN (SELECT conversa_id FROM orcamento_envios WHERE created_at > :fim)
       OR c.client_id IN (
           SELECT oh.client_id FROM orcamento_history oh
           LEFT JOIN orcamento_envios oe ON oe.orcamento_id = oh.id
           WHERE oh.client_id IS NOT NULL AND COALESCE(oe.created_at, oh.created_at) > :fim))
  AND u.em IS NOT NULL AND u.em <= :d2 AND u.em > :fim
  AND {_sem_decisao("c", "u.em")}
  AND NOT EXISTS (
      SELECT 1 FROM notifications n
      WHERE n.kind = :kind AND n.entity_type = 'conversa' AND n.entity_id = c.id
        AND n.dedupe_key = 'conversa.orcamento_parado:' || c.id || ':'
            || FLOOR(EXTRACT(EPOCH FROM u.em))::bigint || ':' || d.degrau)
ORDER BY u.em
LIMIT :lote
"""


def _epoch(momento: datetime) -> int:
    """Segundos desde 1970 de um UTC naive (o mesmo ``EXTRACT(EPOCH)`` do SQL acima)."""
    return int(momento.replace(tzinfo=UTC).timestamp())


def _utc_de_sp(momento_sp: datetime) -> datetime:
    return momento_sp.replace(tzinfo=TZ_SP).astimezone(UTC).replace(tzinfo=None)


def _destinos(conversa: Conversa, preferido: Any = None) -> list[Any]:
    """Quem recebe: a pessoa preferida (quem marcou o lembrete) se ainda é da equipe; senão quem atende; senão a
    equipe toda."""
    if preferido is not None and e_da_equipe(preferido):
        return [preferido]
    if responsavel_ativo(conversa):
        return [conversa.responsavel]
    return notificacoes_ops.resolver_destinatarios(
        notificacoes_ops.DESTINATARIOS_POR_KIND[notificacoes_ops.KIND_CONVERSA_ORCAMENTO_PARADO]
    )


def _aviso(conversa: Conversa, titulo: str) -> push_ops.Aviso:
    return push_ops.Aviso(
        titulo=titulo,
        corpo=conversa.ultima_previa or "",
        link=f"/conversas?c={conversa.id}",
        tag=KP.tag_do_lembrete(conversa.id),
    )


def _avisar_regua(agora: datetime) -> tuple[int, list[push_ops.Lote]]:
    linhas = db.session.execute(
        text(_SQL_REGUA),
        {
            "d2": agora - timedelta(days=K.DEGRAUS_DA_REGUA[0]),
            "d5": agora - timedelta(days=K.DEGRAUS_DA_REGUA[1]),
            "d9": agora - timedelta(days=K.DEGRAUS_DA_REGUA[2]),
            "fim": agora - timedelta(days=K.FIM_DA_REGUA_DIAS),
            "kind": notificacoes_ops.KIND_CONVERSA_ORCAMENTO_PARADO,
            "lote": K.VARREDURA_LOTE,
        },
    ).fetchall()
    gravados, lotes = 0, []
    for conversa_id, orcamento_em, degrau in linhas:
        conversa = db.session.get(Conversa, conversa_id)
        destinos = _destinos(conversa)
        titulo = K.TITULO_ORCAMENTO_PARADO.format(nome=nome_da_conversa(conversa), dias=degrau)
        n = notificacoes_ops.emitir(
            notificacoes_ops.KIND_CONVERSA_ORCAMENTO_PARADO,
            title=titulo,
            body=K.CORPO_ORCAMENTO_PARADO,
            dedupe_key=f"conversa.orcamento_parado:{conversa_id}:{_epoch(orcamento_em)}:{degrau}",
            link_path=f"/conversas?c={conversa_id}",
            entidade=("conversa", conversa_id),
            destinatarios=destinos,
        )
        if n:
            gravados += n
            lotes.append(([u.id for u in destinos], _aviso(conversa, titulo)))
    return gravados, lotes


def _avisar_vencidos(agora: datetime) -> tuple[int, list[push_ops.Lote]]:
    vencidas = (
        Conversa.query.filter(Conversa.lembrar_em.isnot(None), Conversa.lembrar_em <= agora)
        .order_by(Conversa.lembrar_em)
        .limit(K.VARREDURA_LOTE)
        .all()
    )
    gravados, lotes = 0, []
    for conversa in vencidas:
        lido = conversa.lembrar_em
        destinos = _destinos(conversa, conversa.lembrar_para)
        titulo = K.TITULO_LEMBRETE.format(nome=nome_da_conversa(conversa))
        n = notificacoes_ops.emitir(
            notificacoes_ops.KIND_CONVERSA_LEMBRETE,
            title=titulo,
            body=conversa.ultima_previa,
            dedupe_key=f"conversa.lembrete:{conversa.id}:{_epoch(lido)}",
            link_path=f"/conversas?c={conversa.id}",
            entidade=("conversa", conversa.id),
            destinatarios=destinos,
        )
        # Condicional: quem marcou outro lembrete no meio da rodada não o perde.
        db.session.execute(
            text(
                "UPDATE conversas SET lembrar_em = NULL, lembrar_para_id = NULL "
                "WHERE id = :id AND lembrar_em = :lido"
            ),
            {"id": conversa.id, "lido": lido},
        )
        if n:
            gravados += n
            lotes.append(([u.id for u in destinos], _aviso(conversa, titulo)))
    return gravados, lotes


def avisar_lembretes(agora_sp: datetime | None = None) -> dict[str, int]:
    """Uma rodada do lembrete vencido e da régua (FR-020). Comita a rodada.

    Fora de ``HORARIO_DE_ALERTA`` (São Paulo) não faz nada: o que vencer à noite avisa às 9h. ``agora_sp``
    injetável é para o verify; a varredura chama sem argumento.
    """
    agora_sp = agora_sp or now_sp()
    abre, fecha = K.HORARIO_DE_ALERTA
    if not abre <= agora_sp.hour < fecha:
        return {"lembretes": 0, "regua": 0}
    agora = _utc_de_sp(agora_sp)
    lembretes, lotes = _avisar_vencidos(agora)
    regua, lotes_regua = _avisar_regua(agora)
    db.session.commit()
    push_ops.despachar_varios(lotes + lotes_regua)  # depois do commit, nunca dentro (332)
    return {"lembretes": lembretes, "regua": regua}
