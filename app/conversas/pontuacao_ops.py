"""A pontuação por regras de cada conversa (feature 349, FR-010 a FR-012; pesquisa §6.5).

Os sinais saem dos fatos que o funil já lê, em lote (nunca uma consulta por conversa) e só com colunas — nada de
JSON no caminho da lista: formulário preenchido, data do evento (a do fato mais recente entre orçamento e
formulário, contada de hoje em São Paulo), orçamento enviado e recompra (a ficha já tinha evento vivo antes do
primeiro contato). Os pontos e o corte moram em ``constantes.py``: hipótese inicial, revista a cada trimestre.

"Qualificada" é a decisão da vendedora quando houver; senão, pontos ≥ corte.

Folha do domínio: recebe as linhas do funil (``funil_ops.Linha``, com a etapa já calculada por ``_etapas``) sem
importar o funil — quem junta os dois é ``venda_ops`` e o próprio ``funil_ops``. Só leitura.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from sqlalchemy import text

from app import db
from app.constants import now_sp
from app.conversas import constantes as K

# Os orçamentos de cada conversa e de cada ficha: a data do evento e quando a cliente o recebeu (o envio; sem
# envio registrado, a criação — a mesma régua do funil e da linha do tempo).
_SQL_ORCAMENTOS = """
SELECT oe.conversa_id, NULL AS client_id, oh.event_date, oe.created_at
FROM orcamento_envios oe JOIN orcamento_history oh ON oh.id = oe.orcamento_id
WHERE oe.conversa_id = ANY(:conversas)
UNION ALL
SELECT NULL, oh.client_id, oh.event_date, MAX(COALESCE(oe.created_at, oh.created_at))
FROM orcamento_history oh LEFT JOIN orcamento_envios oe ON oe.orcamento_id = oh.id
WHERE oh.client_id = ANY(:fichas)
GROUP BY oh.id, oh.client_id, oh.event_date
"""
_SQL_FORMULARIOS = (
    "SELECT client_id, event_date, created_at FROM form_responses WHERE client_id = ANY(:fichas)"
)
# O evento vivo mais antigo de cada ficha: antes do primeiro contato, é recompra.
_SQL_PRIMEIRO_EVENTO = (
    "SELECT ec.client_id, MIN(ce.created_at) FROM event_clients ec "
    "JOIN calendar_events ce ON ce.id = ec.event_id "
    "WHERE ec.client_id = ANY(:fichas) AND ce.cancelled_at IS NULL GROUP BY ec.client_id"
)


@dataclass
class Pontuacao:
    """Os sinais (na ordem de ``PONTOS_DA_REGRA``) e a soma."""

    sinais: list[str] = field(default_factory=list)

    @property
    def pontos(self) -> int:
        return sum(K.PONTOS_DA_REGRA[s] for s in self.sinais)

    @property
    def pela_regra(self) -> bool:
        return self.pontos >= K.CORTE_DA_QUALIFICADA


def qualificada(decisao: str | None, pontuacao: Pontuacao) -> bool:
    """A decisão da vendedora vence; sem ela, a regra (FR-011)."""
    if decisao in K.DECISOES_DE_QUALIFICACAO:
        return decisao == K.QUALIFICACAO_QUALIFICADA
    return pontuacao.pela_regra


def _data(valor: Any) -> date | None:
    """A data do evento: ``date`` do formulário ou o texto ISO do orçamento (vazio/ilegível → ``None``)."""
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor)[:10]) if valor else None
    except ValueError:
        return None


def _fatos(linhas: list[Any]) -> tuple[dict, dict, dict, dict]:
    """Três consultas em lote: orçamentos (por conversa e por ficha), formulários e o primeiro evento da ficha."""
    conversas = [linha.id for linha in linhas]
    fichas = sorted({linha.client_id for linha in linhas if linha.client_id})
    por_conversa: dict[int, list[tuple[Any, datetime]]] = defaultdict(list)
    por_ficha: dict[int, list[tuple[Any, datetime]]] = defaultdict(list)
    formularios: dict[int, list[tuple[Any, datetime]]] = defaultdict(list)
    primeiro_evento: dict[int, datetime] = {}
    if conversas:
        for conversa_id, client_id, data, em in db.session.execute(
            # `[0]`: lista vazia em `ANY` não tem tipo para o Postgres; o id 0 não existe.
            text(_SQL_ORCAMENTOS),
            {"conversas": conversas, "fichas": fichas or [0]},
        ).fetchall():
            destino = por_conversa[conversa_id] if conversa_id else por_ficha[client_id]
            destino.append((data, em))
    if fichas:
        for client_id, data, em in db.session.execute(text(_SQL_FORMULARIOS), {"fichas": fichas}):
            formularios[client_id].append((data, em))
        primeiro_evento = dict(
            db.session.execute(text(_SQL_PRIMEIRO_EVENTO), {"fichas": fichas}).fetchall()
        )
    return por_conversa, por_ficha, formularios, primeiro_evento


def _sinal_da_data(fatos: list[tuple[Any, datetime]], hoje: date) -> str | None:
    """A data do fato mais recente: até 90 dias à frente soma mais; passada não soma."""
    if not fatos:
        return None
    data = _data(max(fatos, key=lambda f: f[1])[0])
    if data is None or data < hoje:
        return None
    return (
        K.SINAL_DATA_PROXIMA
        if (data - hoje).days <= K.DIAS_DA_DATA_PROXIMA
        else K.SINAL_DATA_DISTANTE
    )


def pontuar(linhas: list[Any]) -> dict[int, Pontuacao]:
    """``{conversa_id: Pontuacao}``. As linhas precisam de ``id``, ``client_id``, ``primeiro`` (UTC) e ``etapa``."""
    por_conversa, por_ficha, formularios, primeiro_evento = _fatos(linhas)
    hoje = now_sp().date()
    resultado: dict[int, Pontuacao] = {}
    for linha in linhas:
        depois = linha.primeiro
        ficha = linha.client_id
        forms = [f for f in formularios.get(ficha, []) if f[1] >= depois] if ficha else []
        orcs = [f for f in por_conversa.get(linha.id, []) if f[1] >= depois]
        orcs += [f for f in por_ficha.get(ficha, []) if f[1] >= depois] if ficha else []
        sinais = []
        if forms:
            sinais.append(K.SINAL_FORMULARIO)
        if sinal := _sinal_da_data(forms + orcs, hoje):
            sinais.append(sinal)
        if orcs or linha.etapa >= 1:
            sinais.append(K.SINAL_ORCAMENTO)
        if ficha and (primeiro_evento.get(ficha) or datetime.max) < depois:
            sinais.append(K.SINAL_RECOMPRA)
        resultado[linha.id] = Pontuacao(sinais)
    return resultado


def serializar(decisao: str | None, pontuacao: Pontuacao) -> dict[str, Any]:
    """A parte de pontos do bloco ``qualificacao`` do painel da venda (contrato)."""
    return {
        "qualificada": qualificada(decisao, pontuacao),
        "pela": "decisao" if decisao in K.DECISOES_DE_QUALIFICACAO else "regra",
        "decisao": decisao if decisao in K.DECISOES_DE_QUALIFICACAO else None,
        "pontos": pontuacao.pontos,
        "corte": K.CORTE_DA_QUALIFICADA,
        "sinais": [
            {"chave": s, "rotulo": K.ROTULO_DO_SINAL[s], "pontos": K.PONTOS_DA_REGRA[s]}
            for s in pontuacao.sinais
        ],
    }
