"""Núcleo de geração/consulta de orçamento EducaManto por responsabilidades (feature 235).

Mudança central vs. o fluxo antigo (feature 077/175): o servidor NUNCA aceita valores prontos
do cliente — `generate_quote` recebe apenas as ENTRADAS de cada configuração (página), recalcula
tudo via `pricing_ops` e congela um snapshot versionado (``{"version": 2, "configs": [...]}``).
Snapshots v1 (formato de pacotes, sem chave ``version``) continuam sendo lidos e re-renderizados
pelo caminho antigo — o histórico é imutável.

A contratação Manto embutida reusa `app.orcamento.quote_ops.calculate_quote` como fonte única
(Princípio I), sempre com ``nota_fiscal=False`` e ``fora_sp=False``: a nota incide UMA vez sobre
a soma (FR-016) e a logística é a do EducaManto.

Funções puras (sem `flask.request`), reusadas pelos endpoints de API.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy import or_

from app import db
from app.educamanto import pricing_ops
from app.educamanto.pricing_ops import ConfigCalculada, Responsabilidades
from app.models import EducaMantoMusical, EducaMantoQuote, User

_DURACOES_FIXAS = ("1h", "2h", "3h", "4h")
MAX_OBSERVACAO = 2000


class QuoteValidationError(Exception):
    """Erro de validação de negócio na geração de orçamento (nunca exceção de banco crua)."""

    def __init__(self, message: str, field: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.field = field


def _int(value, default: int = 0) -> int:
    try:
        return max(int(value if value is not None else default), 0)
    except (TypeError, ValueError):
        return default


def _float(value, default: float = 0.0) -> float:
    try:
        return max(float(value if value is not None else default), 0.0)
    except (TypeError, ValueError):
        return default


def parse_config_input(data: dict, *, prefixo_erro: str = "") -> dict:
    """Normaliza as ENTRADAS de uma configuração (uma página), sem calcular nada.

    Args:
        data: Corpo da configuração vindo do cliente.
        prefixo_erro: Prefixo do campo em erros (ex.: ``configs[1].``) para a tela apontar
            a página certa.

    Raises:
        QuoteValidationError: dias zerados, km ausente fora de SP ou contratação sem duração.
    """
    d1 = _int(data.get("d1"))
    d2 = _int(data.get("d2"))
    if d1 + d2 <= 0:
        raise QuoteValidationError(
            "Preencha os dias (1 e/ou 2 sessões).", f"{prefixo_erro}d1"
        )

    fora_sp = bool(data.get("fora_sp"))
    km_ida = _float(data.get("km_ida"))
    if fora_sp and km_ida <= 0:
        raise QuoteValidationError(
            "Informe os km de ida para evento fora de São Paulo.", f"{prefixo_erro}km_ida"
        )

    contratacao = None
    contratacao_in = data.get("contratacao_manto")
    if contratacao_in:
        duracoes = [str(d).strip() for d in (contratacao_in.get("duracoes") or []) if str(d).strip()]
        if not duracoes:
            raise QuoteValidationError(
                "Selecione ao menos uma duração da contratação Manto.",
                f"{prefixo_erro}contratacao_manto.duracoes",
            )
        contratacao = {
            "payload": dict(contratacao_in.get("payload") or {}),
            "duracoes": duracoes,
        }

    return {
        "musical_id": data.get("musical_id"),
        "d1": d1,
        "d2": d2,
        "ensemble": _int(data.get("ensemble")),
        "responsabilidades": Responsabilidades.from_dict(
            data.get("responsabilidades")
        ).to_dict(),
        "fora_sp": fora_sp,
        "km_ida": km_ida if km_ida > 0 else None,
        "acrescimo": _float(data.get("acrescimo")),
        "contratacao_manto": contratacao,
    }


def _totais_contratacao(contratacao: dict, prefixo_erro: str) -> tuple[dict, list, list]:
    """Calcula a parte Manto via `calculate_quote` (fonte única) e extrai o total por duração.

    A nota fiscal e o transporte são desligados no payload — pertencem ao fechamento do
    EducaManto (nota sobre a soma; logística própria).

    Returns:
        (totais {"1h": R$, ...}, memoria de cálculo, team_lines)
    """
    from app.orcamento.quote_ops import QuoteValidationError as OrcValidationError
    from app.orcamento.quote_ops import calculate_quote

    payload = dict(contratacao["payload"])
    payload["nota_fiscal"] = False
    payload["fora_sp"] = False

    duracoes = contratacao["duracoes"]
    custom = [d for d in duracoes if d not in _DURACOES_FIXAS]
    if custom:
        # `calculate_quote` só calcula UMA duração custom por vez (total_custom).
        if len(custom) > 1:
            raise QuoteValidationError(
                "A contratação Manto aceita só uma duração acima de 4h por orçamento.",
                f"{prefixo_erro}contratacao_manto.duracoes",
            )
        payload["duracao_custom"] = _int(custom[0].rstrip("h"))

    try:
        resultado = calculate_quote(payload)
    except OrcValidationError as exc:
        raise QuoteValidationError(
            exc.message, f"{prefixo_erro}contratacao_manto.{exc.field}"
        ) from exc

    quote = resultado["quote"]
    idx = {"1h": "total_1h", "2h": "total_2h", "3h": "total_3h", "4h": "total_4h"}
    totais: dict[str, float] = {}
    for d in duracoes:
        if d in idx:
            totais[d] = float(quote[idx[d]] or 0)
        else:
            if not quote.get("total_custom"):
                raise QuoteValidationError(
                    f"Duração {d} inválida para a contratação Manto.",
                    f"{prefixo_erro}contratacao_manto.duracoes",
                )
            totais[d] = float(quote["total_custom"])
    return totais, quote.get("memoria") or [], quote.get("team_lines") or []


def calcular_config(entrada: dict, *, prefixo_erro: str = "") -> tuple[EducaMantoMusical, ConfigCalculada, dict]:
    """Calcula uma configuração já normalizada por `parse_config_input`.

    Returns:
        (musical, resultado, contratacao_snapshot) — o último vazio quando não há contratação.

    Raises:
        QuoteValidationError: musical inexistente ou contratação inválida.
    """
    musical = EducaMantoMusical.query.get(entrada.get("musical_id"))
    if musical is None:
        raise QuoteValidationError("Musical inválido.", f"{prefixo_erro}musical_id")

    contratacao_snapshot: dict = {}
    totais: dict[str, float] = {}
    memoria: list = []
    if entrada.get("contratacao_manto"):
        totais, memoria, team_lines = _totais_contratacao(
            entrada["contratacao_manto"], prefixo_erro
        )
        contratacao_snapshot = {
            "inputs": entrada["contratacao_manto"]["payload"],
            "duracoes": entrada["contratacao_manto"]["duracoes"],
            "totais": totais,
            "team_lines": team_lines,
        }

    resultado = pricing_ops.calcular_configuracao(
        musical=musical,
        d1=entrada["d1"],
        d2=entrada["d2"],
        ensemble=entrada["ensemble"],
        resp=Responsabilidades.from_dict(entrada["responsabilidades"]),
        acrescimo=entrada["acrescimo"],
        fora_sp=entrada["fora_sp"],
        km_ida=entrada["km_ida"] or 0.0,
        contratacao_totais=totais,
        contratacao_memoria=memoria,
    )
    return musical, resultado, contratacao_snapshot


def _resultado_snapshot(resultado: ConfigCalculada) -> dict:
    """Parte CALCULADA do snapshot v2 — sempre valores do servidor (FR-026)."""
    return {
        "scenario": resultado.scenario,
        "headcount": resultado.headcount_evento,
        "headcount_ensaio": resultado.headcount_ensaio,
        "tecnicos": resultado.tecnicos,
        "transporte": resultado.transporte.to_dict() if resultado.transporte else None,
        "sem_nota": resultado.valor_final_sem_nota,
        "com_nota": resultado.valor_final_com_nota,
        "a_vista_sem_nota": resultado.a_vista_sem_nota,
        "a_vista_com_nota": resultado.a_vista_com_nota,
        "acrescimo_efetivo": resultado.acrescimo_efetivo,
        "desconto_aplicado": resultado.desconto_aplicado,
        "combinados": resultado.combinados,
    }


def generate_quote(user_id: int, data: dict) -> tuple[EducaMantoQuote, dict]:
    """Valida, RECALCULA todas as configurações no servidor e persiste o snapshot v2.

    Args:
        user_id: Quem está gerando.
        data: ``{"configs": [entradas], "client_name", "event_date", "observacao"}``.

    Returns:
        Tupla ``(quote, snapshot)`` — snapshot pronto para `pdf.gerar_orcamento_pdf`.

    Raises:
        QuoteValidationError: nenhuma configuração ou qualquer configuração inválida
            (o campo vem prefixado com ``configs[i].``).
    """
    configs_in = data.get("configs") or []
    if not configs_in:
        raise QuoteValidationError("Monte ao menos uma página antes de gerar.", "configs")

    configs_snapshot: list[dict] = []
    nomes: list[str] = []
    tem_contratacao = False
    for i, config_data in enumerate(configs_in):
        prefixo = f"configs[{i}]."
        entrada = parse_config_input(config_data, prefixo_erro=prefixo)
        musical, resultado, contratacao_snapshot = calcular_config(
            entrada, prefixo_erro=prefixo
        )
        nomes.append(musical.name)
        tem_contratacao = tem_contratacao or bool(contratacao_snapshot)
        configs_snapshot.append({
            "musical_id": musical.id,
            "musical_name": musical.name,
            "num_personagens": musical.num_personagens,
            "num_producao": musical.num_producao,
            "num_ensaios": musical.num_ensaios,
            "d1": entrada["d1"],
            "d2": entrada["d2"],
            "ensemble": entrada["ensemble"],
            "responsabilidades": entrada["responsabilidades"],
            "fora_sp": entrada["fora_sp"],
            "km_ida": entrada["km_ida"],
            "acrescimo": entrada["acrescimo"],
            "contratacao_manto": contratacao_snapshot or None,
            "resultado": _resultado_snapshot(resultado),
        })

    snapshot = {
        "version": 2,
        "client_name": (data.get("client_name") or "").strip()[:200],
        "event_date": (data.get("event_date") or "").strip()[:10] or None,
        "observacao": (data.get("observacao") or "").strip()[:MAX_OBSERVACAO],
        "configs": configs_snapshot,
    }

    label = ", ".join(dict.fromkeys(nomes))
    if tem_contratacao:
        label += " + contratação Manto"
    quote = EducaMantoQuote(
        user_id=user_id,
        client_name=snapshot["client_name"] or None,
        packages_label=label[:300],
        snapshot=json.dumps(snapshot, ensure_ascii=False),
    )
    db.session.add(quote)
    db.session.commit()
    return quote, snapshot


def load_quote_snapshot(quote: EducaMantoQuote) -> dict:
    """Carrega o snapshot congelado — v2 volta como está; v1 mantém a normalização histórica.

    v1 (sem chave ``version``): preenche `transporte.km_ida` derivando de `kmT` (ida e volta),
    como sempre — sem isso o "Recalcular" de um orçamento antigo dobrava a distância.
    """
    snapshot = json.loads(quote.snapshot or "{}")
    if snapshot.get("version"):
        return snapshot
    transporte = snapshot.get("transporte")
    if isinstance(transporte, dict) and transporte.get("km_ida") in (None, "") and transporte.get("kmT"):
        try:
            transporte["km_ida"] = float(transporte["kmT"]) / 2
        except (TypeError, ValueError):
            transporte["km_ida"] = None
    return snapshot


def search_history(
    *,
    query: str = "",
    date_from: str = "",
    date_to: str = "",
    user_id_filter: str = "",
    is_superadmin: bool = False,
) -> tuple[list[EducaMantoQuote], list[User]]:
    """Busca o histórico de orçamentos (mesmos filtros de sempre).

    Args:
        query: Busca textual em cliente/rótulo.
        date_from: Data inicial (ISO), inclusiva.
        date_to: Data final (ISO), inclusiva (até 23:59:59).
        user_id_filter: Filtra por quem gerou — só tem efeito se `is_superadmin`.
        is_superadmin: Habilita o filtro por usuário e a lista de usuários.

    Returns:
        Tupla ``(entries, users)`` — `users` só populado quando `is_superadmin`.
    """
    q = EducaMantoQuote.query
    if query:
        like = f"%{query}%"
        q = q.filter(
            or_(
                EducaMantoQuote.client_name.ilike(like),
                EducaMantoQuote.packages_label.ilike(like),
            )
        )
    if date_from:
        try:
            q = q.filter(EducaMantoQuote.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            q = q.filter(
                EducaMantoQuote.created_at < datetime.fromisoformat(date_to) + timedelta(days=1)
            )
        except ValueError:
            pass
    if is_superadmin and user_id_filter.isdigit():
        q = q.filter_by(user_id=int(user_id_filter))

    entries = q.order_by(EducaMantoQuote.created_at.desc()).limit(300).all()

    users: list[User] = []
    if is_superadmin:
        users = (
            User.query.filter(
                User.id.in_(db.session.query(EducaMantoQuote.user_id).distinct())
            )
            .order_by(User.name.asc())
            .all()
        )
    return entries, users
