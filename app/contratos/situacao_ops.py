"""Leitura da situação do contrato por venda: página do evento, painel da Home e `/vendas` (feature 317).

Uma fonte só (FR-019): as três telas chamam `situacao_da_venda` (uma venda) ou `situacoes_em_lote`
(muitas, com consultas fixas). A venda é o principal do grupo; os documentos e a marca manual são
procurados em TODOS os dias do grupo, porque agrupar não move linhas (analyze R1).

Sem escrita e sem chamada à ClickSign: lê só o espelho (`ClicksignDocumento`).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import date
from typing import Any

from app import db
from app.constants import (
    CLICKSIGN_TIPO_CLIENTE,
    CONFERIR_MOTIVOS,
    CONTRATO_AGUARDANDO,
    CONTRATO_ASSINADO,
    CONTRATO_ASSINADO_MANUAL,
    CONTRATO_RECUSADO,
    CONTRATO_ROTULOS,
    CONTRATO_SEM_CONTRATO,
    CONTRATO_SEM_CONTRATO_JANELA_DIAS,
    CONTRATO_VENCIDO,
    VINCULO_A_CONFERIR,
    VINCULO_LIGADO,
)
from app.contratos import contratos_ops as nucleo
from app.models import CalendarEvent, ClicksignCobranca, ClicksignDocumento, EventContract

SITUACOES_ASSINADAS = (CONTRATO_ASSINADO, CONTRATO_ASSINADO_MANUAL)


def _anexos_automaticos() -> Any:
    """Subconsulta dos `event_contracts` que a sincronização criou (não contam como marca manual)."""
    return db.session.query(ClicksignDocumento.contrato_anexo_id).filter(
        ClicksignDocumento.contrato_anexo_id.isnot(None)
    )


def _manuais_assinados(ids: list[int]) -> set[int]:
    """Eventos com anexo marcado "assinado" pelo Superadmin (fora os PDFs automáticos)."""
    if not ids:
        return set()
    return {
        event_id
        for (event_id,) in db.session.query(EventContract.event_id).filter(
            EventContract.event_id.in_(ids),
            EventContract.is_signed.is_(True),
            EventContract.id.notin_(_anexos_automaticos()),
        )
    }


def _documentos_por_evento(ids: list[int]) -> dict[int, list[ClicksignDocumento]]:
    if not ids:
        return {}
    por_evento: dict[int, list[ClicksignDocumento]] = defaultdict(list)
    for documento in ClicksignDocumento.query.filter(
        ClicksignDocumento.event_id.in_(ids),
        ClicksignDocumento.tipo == CLICKSIGN_TIPO_CLIENTE,
        ClicksignDocumento.vinculo == VINCULO_LIGADO,
    ):
        por_evento[documento.event_id].append(documento)
    return por_evento


def _ultimas_cobrancas(documento_ids: Iterable[int]) -> dict[int, ClicksignCobranca]:
    ids = [i for i in documento_ids if i]
    if not ids:
        return {}
    ultimas: dict[int, ClicksignCobranca] = {}
    for cobranca in ClicksignCobranca.query.filter(
        ClicksignCobranca.documento_id.in_(ids)
    ).order_by(ClicksignCobranca.em.desc()):
        ultimas.setdefault(cobranca.documento_id, cobranca)
    return ultimas


def situacoes_em_lote(
    grupos: dict[int, list[int]], integracao_ligada: bool = True
) -> dict[int, dict[str, Any]]:
    """Situação de muitas vendas com consultas fixas.

    Args:
        grupos: principal → ids de todos os dias do grupo (o principal incluído).
        integracao_ligada: Desligada, só a marca manual vale (e o resto é "sem contrato").

    Returns:
        principal → ``{"situacao", "documento", "outros", "assinado_manual"}``.
    """
    todos = [i for ids in grupos.values() for i in ids]
    manuais = _manuais_assinados(todos)
    por_evento = _documentos_por_evento(todos) if integracao_ligada else {}
    resultado: dict[int, dict[str, Any]] = {}
    for principal_id, ids in grupos.items():
        documentos = [d for i in ids for d in por_evento.get(i, [])]
        vigente = nucleo.vigente(documentos)
        manual = any(i in manuais for i in ids)
        resultado[principal_id] = {
            "situacao": nucleo.situacao_do_documento(vigente, manual),
            "documento": vigente,
            "outros": [d for d in nucleo.documentos_da_venda(documentos) if d is not vigente],
            "assinado_manual": manual,
        }
    return resultado


def situacao_da_venda(principal: CalendarEvent, integracao_ligada: bool = True) -> dict[str, Any]:
    """A situação de uma venda (página do evento, registro de cobrança)."""
    from app.calendar.group_ops import group_events

    ids = [e.id for e in group_events(principal)]
    return situacoes_em_lote({principal.id: ids}, integracao_ligada)[principal.id]


def _iso(valor: Any) -> str | None:
    return valor.isoformat() if valor is not None else None


def _documento_json(documento: ClicksignDocumento | None) -> dict[str, Any] | None:
    if documento is None:
        return None
    return {
        "id": documento.id,
        "nome": nucleo.normalizar_nome(documento.nome),
        "status": documento.status,
        "prazo": _iso(documento.prazo),
        "assinado_em": _iso(documento.assinado_em),
        "canal": documento.canal,
        "vinculo_origem": documento.vinculo_origem,
    }


def _cobranca_json(cobranca: ClicksignCobranca | None) -> dict[str, Any] | None:
    if cobranca is None:
        return None
    return {"por": cobranca.usuario_nome, "em": _iso(cobranca.em)}


def _data_da_venda(principal: CalendarEvent, eventos: list[CalendarEvent]) -> date | None:
    from app.financeiro.cobranca_ops import data_do_grupo

    return data_do_grupo(eventos) or (principal.start_at.date() if principal.start_at else None)


def linha_a_conferir(documento: ClicksignDocumento) -> dict[str, Any]:
    """Um documento a conferir, com o motivo em pt-BR e as vendas sugeridas."""
    from app.contratos.sincronizar_ops import sugestoes

    return {
        "documento_id": documento.id,
        "nome": nucleo.normalizar_nome(documento.nome),
        "data_lida": _iso(documento.data_lida),
        "telefone_lido": documento.telefone_lido,
        "motivo": documento.vinculo_motivo,
        "motivo_texto": CONFERIR_MOTIVOS.get(documento.vinculo_motivo or "", None),
        "status": documento.status,
        "criado_em": _iso(documento.criado_em),
        "sugestoes": sugestoes(documento),
    }


def documentos_a_conferir() -> list[ClicksignDocumento]:
    """Todos os documentos a conferir, pela data do evento lida (os sem data por último)."""
    documentos = ClicksignDocumento.query.filter(
        ClicksignDocumento.vinculo == VINCULO_A_CONFERIR
    ).all()
    return sorted(documentos, key=lambda d: (d.data_lida is None, d.data_lida or date.max, d.id))


def bloco_do_evento(
    event: CalendarEvent, *, pode_cobrar_papel: bool, pode_conferir_papel: bool, hoje: date
) -> dict[str, Any]:
    """O bloco `contrato` do detalhe do evento (contracts/api.md)."""
    from app.calendar.group_ops import group_events
    from app.contratos.sincronizar_ops import integracao_ligada
    from app.financeiro.cobranca_ops import principal_da_venda

    ligada = integracao_ligada()
    principal = principal_da_venda(event)
    eventos = group_events(principal)
    venda = situacoes_em_lote({principal.id: [e.id for e in eventos]}, ligada)[principal.id]
    documento = venda["documento"]
    situacao = venda["situacao"]
    data_evento = _data_da_venda(principal, eventos)
    dias = (data_evento - hoje).days if data_evento else 0
    eh_principal = event.id == principal.id
    venda_viva = principal.cancelled_at is None and event.cancelled_at is None
    bloqueio = nucleo.bloqueio_da_cobranca(
        situacao, eh_principal=eh_principal, venda_viva=venda_viva
    )
    ultima = _ultimas_cobrancas([documento.id]).get(documento.id) if documento else None
    a_conferir: list[dict[str, Any]] = []
    if ligada and pode_conferir_papel and venda_viva:
        for candidato in documentos_a_conferir():
            linha = linha_a_conferir(candidato)
            if any(s["event_id"] == principal.id for s in linha["sugestoes"]):
                a_conferir.append(linha)
    return {
        "integracao_ligada": ligada,
        "situacao": situacao,
        "rotulo": nucleo.rotulo_da_situacao(
            situacao,
            documento.prazo if documento else None,
            documento.assinado_em if documento else None,
            hoje,
        ),
        "cor": "verde"
        if situacao in SITUACOES_ASSINADAS
        else nucleo.cor_do_contrato(situacao, documento.prazo if documento else None, dias, hoje),
        "escopo": "evento"
        if len(eventos) < 2
        else ("grupo_principal" if eh_principal else "grupo_outro"),
        "documento": _documento_json(documento),
        "outros_documentos": [_documento_json(d) for d in venda["outros"]],
        "pode_cobrar": bool(pode_cobrar_papel and ligada and bloqueio is None),
        "motivo_bloqueio": bloqueio if pode_cobrar_papel else None,
        "ultima_cobranca": _cobranca_json(ultima),
        "pode_conferir": bool(pode_conferir_papel and ligada and venda_viva),
        "a_conferir": a_conferir,
    }


def fragmentos_da_mensagem(event: CalendarEvent) -> dict[str, str]:
    """Personagens, data e local para a mensagem do "Cobrar contrato" (molde `_serialize_mensagens`)."""
    from app.calendar.routes import _format_event_date_ptbr, parse_characters

    return {
        "characters": " + ".join(parse_characters(event.title)),
        "date_line": _format_event_date_ptbr(event.start_at, event.end_at),
        "location": event.location or "",
    }


def contratos_da_home(vendas: list[Any], hoje: date, *, pode_cobrar_papel: bool) -> dict[str, Any]:
    """O bloco `comercial.contratos` do painel (FR-010), em lote.

    Args:
        vendas: `VendaResumo` de `cobranca_ops.vendas_desde(corte)` (principais vivos desde o corte).
        hoje: Data de hoje em SP.
        pode_cobrar_papel: COMERCIAL ou Superadmin (o FINANCEIRO vê sem o botão).
    """
    from app.contratos.sincronizar_ops import integracao_ligada

    ligada = integracao_ligada()
    vivas = [v for v in vendas if nucleo.venda_entra(v.principal)]
    grupos = {v.principal.id: [e.id for e in v.eventos] for v in vivas}
    situacoes = situacoes_em_lote(grupos, ligada)
    documentos = [s["documento"] for s in situacoes.values() if s["documento"] is not None]
    cobrancas = _ultimas_cobrancas(d.id for d in documentos)

    listas: dict[str, list[dict[str, Any]]] = {
        "para_cobrar": [],
        "vencidos": [],
        "sem_contrato": [],
        "ja_aconteceu": [],
    }
    for venda in vivas:
        principal = venda.principal
        estado = situacoes[principal.id]
        situacao = estado["situacao"]
        if situacao in SITUACOES_ASSINADAS:
            continue
        data_evento = venda.data_do_grupo or (
            principal.start_at.date() if principal.start_at else None
        )
        if data_evento is None:
            continue
        dias = (data_evento - hoje).days
        documento = estado["documento"]
        if dias < 0:
            grupo = "ja_aconteceu"
        elif situacao == CONTRATO_AGUARDANDO:
            grupo = "para_cobrar"
        elif situacao in (CONTRATO_VENCIDO, CONTRATO_RECUSADO):
            grupo = "vencidos"
        elif situacao == CONTRATO_SEM_CONTRATO and dias <= CONTRATO_SEM_CONTRATO_JANELA_DIAS:
            grupo = "sem_contrato"
        else:
            continue
        prazo = documento.prazo if documento else None
        listas[grupo].append(
            {
                "event_id": principal.id,
                "titulo": principal.title,
                "cliente": venda.cliente,
                "data_evento": data_evento.isoformat(),
                "dias_ate_o_evento": dias,
                "situacao": situacao,
                "rotulo": CONTRATO_ROTULOS[situacao],
                "severidade": nucleo.cor_do_contrato(situacao, prazo, dias, hoje),
                "selo": nucleo.selo_do_contrato(situacao, prazo, hoje),
                "documento_id": documento.id if documento else None,
                "prazo": _iso(prazo),
                "canal": documento.canal if documento else None,
                "ultima_cobranca": _cobranca_json(cobrancas.get(documento.id))
                if documento
                else None,
                "mensagem": fragmentos_da_mensagem(principal) if grupo == "para_cobrar" else None,
            }
        )

    ordem = {"vermelho": 0, "amarelo": 1, "cinza": 2}
    for nome, linhas in listas.items():
        if nome == "ja_aconteceu":
            linhas.sort(key=lambda linha: (-linha["dias_ate_o_evento"], linha["event_id"]))
        else:
            linhas.sort(
                key=lambda linha: (
                    ordem[linha["severidade"]],
                    linha["dias_ate_o_evento"],
                    linha["event_id"],
                )
            )
    a_conferir = [linha_a_conferir(d) for d in documentos_a_conferir()] if ligada else []
    agir = listas["para_cobrar"] + listas["vencidos"] + listas["sem_contrato"]
    return {
        "integracao_ligada": ligada,
        **listas,
        "a_conferir": a_conferir,
        "resumo": nucleo.resumo_por_cor(agir),
        "pode_cobrar": bool(pode_cobrar_papel and ligada),
    }


def status_para_vendas(principais: list[CalendarEvent]) -> dict[int, str]:
    """Situação para a coluna Contrato de `/vendas` (FR-019), em lote."""
    from app.contratos.sincronizar_ops import integracao_ligada

    grupos = {p.id: [p.id, *[s.id for s in (p.satellites or [])]] for p in principais}
    return {pid: s["situacao"] for pid, s in situacoes_em_lote(grupos, integracao_ligada()).items()}
