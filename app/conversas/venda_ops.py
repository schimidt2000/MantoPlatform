"""A venda na conversa (feature 349): perda, qualificação, lembrete, o painel e o resumo da lista.

- **Perda** (FR-007/FR-008): motivo de uma lista fechada (``MOTIVOS_DE_PERDA``, a única fonte dos rótulos) e frase
  obrigatória no "Outro", no molde do encerramento de formulário (298). Marcar perdida cancela o lembrete; reabrir
  apaga as quatro colunas. A mensagem nova da cliente NÃO reabre (clarify de 17/11).
- **Qualificação** (FR-011): a decisão da vendedora vale sobre a pontuação por regras; ``None`` volta para a regra.
- **Lembrete** (FR-019): "amanhã às 9h" de São Paulo, para quem tocou; um por conversa. Quem avisa é a varredura
  (``parado_ops``), que nunca escreve na conversa.
- **Painel** (``GET …/venda``) e **resumo da lista**: etapa, anúncio, pontuação, primeira resposta, perda, lembrete,
  o orçamento parado e o que levar ao evento — tudo em lote na lista, nunca uma consulta por conversa.

Duas pessoas decidindo juntas: vale a última gravação (as duas são decisões válidas). Puro: sem ``flask.request``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text

from app import db
from app.constants import TZ_SP, now_sp
from app.conversas import constantes as K
from app.conversas import fechamento_ops, parado_ops, pontuacao_ops, primeira_resposta_ops
from app.conversas.funil_ops import Linha, _etapas
from app.conversas.leitura_ops import _iso_utc, serializar_pessoa
from app.conversas.recusa import Recusa, campo
from app.conversas.relogio import agora_utc
from app.models import Conversa, User


def conversa_ou_404(conversa_id: int) -> Conversa:
    conversa = db.session.get(Conversa, conversa_id)
    if conversa is None:
        raise Recusa("nao_encontrada", K.TEXTO_CONVERSA_NAO_ENCONTRADA, 404)
    return conversa


def motivos_de_perda() -> list[dict[str, Any]]:
    """A lista fechada que a tela desenha (a tela não tem texto próprio de motivo)."""
    return [
        {"codigo": m, "rotulo": K.ROTULO_DO_MOTIVO[m], "pede_frase": m == K.MOTIVO_OUTRO}
        for m in K.MOTIVOS_DE_PERDA
    ]


# ── Perda ────────────────────────────────────────────────────────────────────────────────────────


def _validar_perda(motivo: Any, frase: Any) -> tuple[str, str | None]:
    motivo = motivo.strip() if isinstance(motivo, str) else ""
    frase = frase.strip() if isinstance(frase, str) else ""
    if motivo not in K.MOTIVOS_DE_PERDA:
        raise campo("motivo", K.TEXTO_MOTIVO_INVALIDO)
    if motivo == K.MOTIVO_OUTRO and not frase:
        raise campo("frase", K.TEXTO_FRASE_OBRIGATORIA)
    if len(frase) > K.PERDA_NOTA_MAXIMA:
        raise campo("frase", K.TEXTO_FRASE_LONGA)
    return motivo, frase or None


def marcar_perdida(conversa_id: int, motivo: Any, frase: Any, quem: User) -> Conversa:
    """Marca a conversa como perdida e cancela o lembrete. Comita.

    Raises:
        Recusa: 422 em ``motivo``/``frase``; 404.
    """
    motivo, frase = _validar_perda(motivo, frase)
    conversa = conversa_ou_404(conversa_id)
    conversa.perdida_em = agora_utc()
    conversa.perdida_motivo = motivo
    conversa.perdida_nota = frase
    conversa.perdida_por_id = quem.id
    conversa.lembrar_em = None
    conversa.lembrar_para_id = None
    db.session.commit()
    return conversa


def reabrir(conversa_id: int) -> Conversa:
    """Desfaz a perda (idempotente). Comita."""
    conversa = conversa_ou_404(conversa_id)
    conversa.perdida_em = None
    conversa.perdida_motivo = None
    conversa.perdida_nota = None
    conversa.perdida_por_id = None
    db.session.commit()
    return conversa


# ── Qualificação ─────────────────────────────────────────────────────────────────────────────────


def decidir_qualificacao(conversa_id: int, decisao: Any, quem: User) -> Conversa:
    """ "Qualificada", "Não qualificada" ou ``None`` (usar a regra). Comita.

    Raises:
        Recusa: 422 em ``decisao``; 404.
    """
    if decisao is not None and decisao not in K.DECISOES_DE_QUALIFICACAO:
        raise campo("decisao", K.TEXTO_DECISAO_INVALIDA)
    conversa = conversa_ou_404(conversa_id)
    conversa.qualificacao = decisao
    conversa.qualificacao_em = agora_utc() if decisao else None
    conversa.qualificacao_por_id = quem.id if decisao else None
    db.session.commit()
    return conversa


# ── Lembrete ─────────────────────────────────────────────────────────────────────────────────────


def amanha_as_9h() -> datetime:
    """O próximo dia do calendário de São Paulo, às 9h, em UTC naive (o relógio da tabela)."""
    amanha = now_sp().date() + timedelta(days=1)
    local = datetime(amanha.year, amanha.month, amanha.day, K.HORA_DO_LEMBRETE, tzinfo=TZ_SP)
    return local.astimezone(UTC).replace(tzinfo=None)


def lembrar_amanha(conversa_id: int, quem: User) -> Conversa:
    """Um lembrete por conversa: o novo substitui o anterior. Comita."""
    conversa = conversa_ou_404(conversa_id)
    conversa.lembrar_em = amanha_as_9h()
    conversa.lembrar_para_id = quem.id
    db.session.commit()
    return conversa


def cancelar_lembrete(conversa_id: int) -> Conversa:
    """Tira o lembrete (idempotente). Comita."""
    conversa = conversa_ou_404(conversa_id)
    conversa.lembrar_em = None
    conversa.lembrar_para_id = None
    db.session.commit()
    return conversa


# ── Contexto em lote (lista e painel) ────────────────────────────────────────────────────────────


def _linhas(conversas: list[Conversa]) -> list[Linha]:
    """As linhas do funil para as conversas da página: o primeiro contato é o menor entre a primeira mensagem e a
    criação da conversa (a abertura do Instagram pelo anúncio vem antes da mensagem)."""
    ids = [c.id for c in conversas]
    com_anuncio = (
        {
            linha[0]
            for linha in db.session.execute(
                text(
                    "SELECT DISTINCT conversa_id FROM conversa_anuncios "
                    "WHERE tipo = :tipo AND conversa_id = ANY(:ids)"
                ),
                {"tipo": K.CONTATO_ANUNCIO, "ids": ids},
            )
        }
        if ids
        else set()
    )
    return [
        Linha(
            id=c.id,
            canal=c.canal,
            client_id=c.client_id,
            responsavel_id=c.responsavel_id,
            primeiro=min(d for d in (c.primeira_recebida_em, c.created_at) if d is not None),
            tem_anuncio=c.id in com_anuncio,
            campanha=None,
            recebida_em=c.primeira_recebida_em,
            resposta_em=c.primeira_resposta_em,
            resposta_origem=c.primeira_resposta_origem,
            perdida_motivo=c.perdida_motivo,
            qualificacao=c.qualificacao,
            lembrar_em=c.lembrar_em,
        )
        for c in conversas
    ]


def _contexto(
    conversas: list[Conversa],
) -> tuple[dict[int, Linha], dict[int, pontuacao_ops.Pontuacao]]:
    linhas = _linhas(conversas)
    _etapas(linhas)
    pontos = pontuacao_ops.pontuar(linhas)
    for linha in linhas:
        linha.qualificada = pontuacao_ops.qualificada(linha.qualificacao, pontos[linha.id])
    return {linha.id: linha for linha in linhas}, pontos


def _perda_curta(conversa: Conversa) -> dict[str, str] | None:
    if conversa.perdida_motivo not in K.ROTULO_DO_MOTIVO:
        return None
    return {
        "motivo": conversa.perdida_motivo,
        "rotulo": K.ROTULO_DO_MOTIVO[conversa.perdida_motivo],
    }


def resumos_da_lista(conversas: list[Conversa]) -> dict[int, dict[str, Any]]:
    """O ``venda`` de cada item da lista (FR-013), em lote para a página inteira."""
    if not conversas:
        return {}
    linhas, _ = _contexto(conversas)
    return {
        c.id: {
            "anuncio": linhas[c.id].tem_anuncio,
            "etapa": K.ETAPAS_DO_FUNIL[linhas[c.id].etapa],
            # O rótulo vem daqui (fonte única com o funil): a tela não tem cópia dos nomes das etapas.
            "etapa_rotulo": K.ROTULO_DA_ETAPA[K.ETAPAS_DO_FUNIL[linhas[c.id].etapa]],
            "qualificada": linhas[c.id].qualificada,
            "perdida": _perda_curta(c),
            "lembrete_em": _iso_utc(c.lembrar_em),
        }
        for c in conversas
    }


def _primeira_resposta(conversa: Conversa) -> dict[str, Any]:
    return {
        "recebida_em": _iso_utc(conversa.primeira_recebida_em),
        "resposta_em": _iso_utc(conversa.primeira_resposta_em),
        "minutos": primeira_resposta_ops.minutos(conversa),
        "autor": serializar_pessoa(conversa.primeira_resposta_por),
        "origem": conversa.primeira_resposta_origem,
    }


def _perda(conversa: Conversa) -> dict[str, Any] | None:
    curta = _perda_curta(conversa)
    if curta is None:
        return None
    return {
        **curta,
        "frase": conversa.perdida_nota,
        "em": _iso_utc(conversa.perdida_em),
        "por": serializar_pessoa(conversa.perdida_por),
    }


def painel(conversa: Conversa) -> dict[str, Any]:
    """O painel da venda da conversa aberta (contrato ``Venda``)."""
    linhas, pontos = _contexto([conversa])
    linha = linhas[conversa.id]
    etapa = K.ETAPAS_DO_FUNIL[linha.etapa]
    parado = parado_ops.parado_da_conversa(conversa.id, agora_utc())
    return {
        "conversa_id": conversa.id,
        "etapa": {"chave": etapa, "rotulo": K.ROTULO_DA_ETAPA[etapa]},
        "anuncio": linha.tem_anuncio,
        "primeira_resposta": _primeira_resposta(conversa),
        "perda": _perda(conversa),
        "qualificacao": {
            **pontuacao_ops.serializar(conversa.qualificacao, pontos[conversa.id]),
            "decidida_por": serializar_pessoa(conversa.qualificacao_por)
            if conversa.qualificacao
            else None,
            "decidida_em": _iso_utc(conversa.qualificacao_em) if conversa.qualificacao else None,
        },
        "lembrete": {
            "em": _iso_utc(conversa.lembrar_em),
            "para": serializar_pessoa(conversa.lembrar_para),
        }
        if conversa.lembrar_em
        else None,
        "parado": {"orcamento_em": _iso_utc(parado[0]), "dias": parado[1]} if parado else None,
        "fechamento": fechamento_ops.o_que_levar(conversa),
        "motivos_de_perda": motivos_de_perda(),
    }
