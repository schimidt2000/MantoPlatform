"""Os dois consentimentos da ficha: novidades e aniversário da criança (feature 350, LGPD).

Núcleo puro: sem ``flask.request`` e **sem commit** — quem chama decide a transação (o endpoint
comita; o aviso do WhatsApp comita em ``aviso_ops.processar_aviso``; a venda da loja, no fecho dela).

Regras (``specs/350-base-autorizada/data-model.md``):

- com aceite de novidades ⇔ ``Client.marketing_opt_in_at`` preenchido; a retirada zera os
  ``marketing_opt_in_*`` e grava os ``marketing_opt_out_*``;
- todo aceite e toda retirada viram uma linha em ``cliente_consentimentos`` com o texto completo,
  a versão, a origem, a referência e o autor (LGPD art. 8º §2º: o ônus da prova é de quem coleta);
- a criança só existe com o aceite; remover apaga nome e data, e o histórico não os guarda;
- carimbos em horário de São Paulo (``now_sp``), o mesmo relógio do aceite da loja (344).

Este módulo não importa ``app.conversas``: recebe a conversa pronta (a dependência vai de Conversas
para Clientes, nunca o contrário).
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from app import db
from app.constants import (
    CONSENTIMENTO_ACAO_ACEITE,
    CONSENTIMENTO_ACAO_RETIRADA,
    CONSENTIMENTO_ANIVERSARIO_TEXTO,
    CONSENTIMENTO_ANIVERSARIO_VERSAO,
    CONSENTIMENTO_NOVIDADES_TEXTO,
    CONSENTIMENTO_NOVIDADES_VERSAO,
    CONSENTIMENTO_ORIGEM_ERRO_WHATSAPP,
    CONSENTIMENTO_ORIGEM_FICHA,
    CONSENTIMENTO_ORIGEM_PEDIU_PARA_PARAR,
    CONSENTIMENTO_ORIGEM_POS_EVENTO,
    CONSENTIMENTO_ORIGENS_EQUIPE,
    CONSENTIMENTO_TIPO_ANIVERSARIO,
    CONSENTIMENTO_TIPO_NOVIDADES,
    CRIANCA_IDADE_MAXIMA,
    CRIANCA_NOME_MAXIMO,
    ERRO_WHATSAPP_PEDIU_PARA_NAO_RECEBER,
    PALAVRAS_DE_SAIDA,
    VIRTUAL_ACEITE_TEXTO,
    VIRTUAL_ACEITE_VERSAO,
    now_sp,
)
from app.models import Client, ClienteConsentimento, ClienteCrianca
from app.utils import strip_accents_lower

ORIGEM_MAXIMA = 160
REFERENCIA_MAXIMA = 80
# Quem grava sem usuário: a própria cliente (página pública, loja) ou o sistema (saída automática).
_ORIGENS_DA_CLIENTE = (CONSENTIMENTO_ORIGEM_POS_EVENTO,)
_PREFIXO_DA_LOJA = "Loja:"
_PONTAS = re.compile(r"^[^a-z0-9]+|[^a-z0-9]+$")
_ESPACOS = re.compile(r"\s+")


class ConsentimentoErro(Exception):
    """Recusa de negócio com o campo a apontar na tela (``fields``) e o status HTTP."""

    def __init__(
        self, campo: str | None, mensagem: str, status: int = 400, codigo: str | None = None
    ) -> None:
        super().__init__(mensagem)
        self.campo = campo
        self.mensagem = mensagem
        self.status = status
        self.codigo = codigo


# ── Textos ───────────────────────────────────────────────────────────────────────────────────────


def textos() -> dict[str, dict[str, str]]:
    """Os dois textos vigentes, com a versão — o que a tela mostra é o que o histórico grava."""
    return {
        CONSENTIMENTO_TIPO_NOVIDADES: {
            "texto": CONSENTIMENTO_NOVIDADES_TEXTO,
            "versao": CONSENTIMENTO_NOVIDADES_VERSAO,
        },
        CONSENTIMENTO_TIPO_ANIVERSARIO: {
            "texto": CONSENTIMENTO_ANIVERSARIO_TEXTO,
            "versao": CONSENTIMENTO_ANIVERSARIO_VERSAO,
        },
    }


def validar_origem_da_equipe(origem: Any) -> str:
    """A origem escolhida pela equipe tem de estar na lista fechada."""
    valor = str(origem or "").strip()
    if valor not in CONSENTIMENTO_ORIGENS_EQUIPE:
        raise ConsentimentoErro("origem", "Selecione por onde veio o pedido.")
    return valor


def _referencia(valor: Any) -> str | None:
    texto = str(valor or "").strip()
    return texto[:REFERENCIA_MAXIMA] or None


def _anotar(
    client: Client,
    tipo: str,
    acao: str,
    texto: str,
    versao: str,
    origem: str,
    referencia: str | None,
    user_id: int | None,
    momento: datetime,
) -> None:
    db.session.add(
        ClienteConsentimento(
            client_id=client.id,
            tipo=tipo,
            acao=acao,
            texto=texto,
            versao=versao,
            origem=origem[:ORIGEM_MAXIMA],
            referencia=_referencia(referencia),
            registrado_por_id=user_id,
            registrado_em=momento,
        )
    )


# ── Novidades ────────────────────────────────────────────────────────────────────────────────────


def pode_prospectar(client: Client | None) -> bool:
    """Sem aceite de novidades, nada de prospecção (spec 350, FR-010)."""
    return client is not None and client.marketing_opt_in_at is not None


def registrar_aceite_novidades(
    client: Client,
    *,
    origem: str,
    referencia: str | None = None,
    user_id: int | None = None,
    texto: str = CONSENTIMENTO_NOVIDADES_TEXTO,
    versao: str = CONSENTIMENTO_NOVIDADES_VERSAO,
    momento: datetime | None = None,
) -> bool:
    """Grava o aceite de novidades. Idempotente: quem já tem aceite fica como está (``False``)."""
    if pode_prospectar(client):
        return False
    momento = momento or now_sp()
    client.marketing_opt_in_at = momento
    client.marketing_opt_in_source = origem[:ORIGEM_MAXIMA]
    client.marketing_opt_in_version = versao
    _anotar(
        client,
        CONSENTIMENTO_TIPO_NOVIDADES,
        CONSENTIMENTO_ACAO_ACEITE,
        texto,
        versao,
        origem,
        referencia,
        user_id,
        momento,
    )
    return True


def _texto_do_aceite_vigente(client: Client) -> tuple[str, str]:
    """O texto e a versão que a pessoa aceitou — a retirada aponta para eles."""
    ultimo = (
        ClienteConsentimento.query.filter_by(
            client_id=client.id, tipo=CONSENTIMENTO_TIPO_NOVIDADES, acao=CONSENTIMENTO_ACAO_ACEITE
        )
        .order_by(ClienteConsentimento.registrado_em.desc(), ClienteConsentimento.id.desc())
        .first()
    )
    if ultimo is not None:
        return ultimo.texto, ultimo.versao
    # Aceite da loja anterior à 350 (sem histórico): o texto é o da caixinha da loja.
    return VIRTUAL_ACEITE_TEXTO, client.marketing_opt_in_version or VIRTUAL_ACEITE_VERSAO


def retirar_aceite_novidades(
    client: Client,
    *,
    origem: str,
    referencia: str | None = None,
    user_id: int | None = None,
    momento: datetime | None = None,
) -> bool:
    """Retira o aceite de novidades. Idempotente: quem não tem aceite fica como está (``False``)."""
    if not pode_prospectar(client):
        return False
    momento = momento or now_sp()
    texto, versao = _texto_do_aceite_vigente(client)
    client.marketing_opt_in_at = None
    client.marketing_opt_in_source = None
    client.marketing_opt_in_version = None
    client.marketing_opt_out_at = momento
    client.marketing_opt_out_source = origem[:ORIGEM_MAXIMA]
    _anotar(
        client,
        CONSENTIMENTO_TIPO_NOVIDADES,
        CONSENTIMENTO_ACAO_RETIRADA,
        texto,
        versao,
        origem,
        referencia,
        user_id,
        momento,
    )
    return True


def aceite_da_loja(
    client: Client, *, momento: datetime, versao: str | None, origem: str, pedido_id: int
) -> bool:
    """O aceite marcado na loja (344) chega à ficha — só se for posterior à última retirada.

    Sem essa regra, a venda (ou a releitura dela) reativaria o aceite de quem já pediu para sair.
    """
    if client.marketing_opt_out_at is not None and momento <= client.marketing_opt_out_at:
        return False
    if client.marketing_opt_in_at is not None and client.marketing_opt_in_at >= momento:
        return False
    if pode_prospectar(client):
        # Aceite novo e mais recente: atualiza a data e a origem, e anota (é outro "sim").
        client.marketing_opt_in_at = None
    return registrar_aceite_novidades(
        client,
        origem=origem,
        referencia=f"pedido:{pedido_id}",
        texto=VIRTUAL_ACEITE_TEXTO,
        versao=versao or VIRTUAL_ACEITE_VERSAO,
        momento=momento,
    )


# ── Saída automática (conversa) ──────────────────────────────────────────────────────────────────


def normalizar_mensagem(texto: str | None) -> str:
    """Sem acento, minúscula, espaços colapsados e sem pontuação/emoji nas pontas."""
    valor = _ESPACOS.sub(" ", strip_accents_lower(texto or "")).strip()
    return _PONTAS.sub("", valor)


def e_pedido_de_saida(texto: str | None) -> bool:
    """A mensagem INTEIRA é uma palavra de saída ("SAIR", "Parar promoções"…)? "Vou sair" não é."""
    return normalizar_mensagem(texto) in PALAVRAS_DE_SAIDA


def retirar_se_pediu_para_parar(conversa: Any, texto: str | None, referencia: str) -> bool:
    """Gancho da mensagem recebida: retira o aceite da ficha da conversa se ela pediu para parar."""
    cliente = getattr(conversa, "cliente", None)
    if cliente is None or not e_pedido_de_saida(texto):
        return False
    return retirar_aceite_novidades(
        cliente, origem=CONSENTIMENTO_ORIGEM_PEDIU_PARA_PARAR, referencia=referencia
    )


def retirar_por_erro_do_whatsapp(conversa: Any, codigo: int | None, referencia: str) -> bool:
    """Gancho do erro 131050 (o contato pediu à Meta para não receber marketing)."""
    cliente = getattr(conversa, "cliente", None)
    if cliente is None or codigo != ERRO_WHATSAPP_PEDIU_PARA_NAO_RECEBER:
        return False
    return retirar_aceite_novidades(
        cliente, origem=CONSENTIMENTO_ORIGEM_ERRO_WHATSAPP, referencia=referencia
    )


def conversa_pode_receber_marketing(conversa: Any) -> bool:
    """Modelo de marketing só sai para a conversa ligada a uma ficha com aceite (FR-008)."""
    return pode_prospectar(getattr(conversa, "cliente", None))


# ── Criança ──────────────────────────────────────────────────────────────────────────────────────


def _validar_nome(valor: Any) -> str:
    nome = _ESPACOS.sub(" ", str(valor or "")).strip()
    if not nome:
        raise ConsentimentoErro("primeiro_nome", "Informe o primeiro nome da criança.")
    if len(nome) > CRIANCA_NOME_MAXIMO:
        raise ConsentimentoErro("primeiro_nome", f"Use até {CRIANCA_NOME_MAXIMO} caracteres.")
    return nome


def _validar_nascimento(valor: Any, hoje: date) -> date:
    try:
        nascimento = date.fromisoformat(str(valor or "").strip())
    except ValueError:
        raise ConsentimentoErro("nascimento", "Informe a data de aniversário.") from None
    if nascimento > hoje:
        raise ConsentimentoErro("nascimento", "A data de aniversário não pode ser no futuro.")
    idade = (
        hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))
    )
    if idade > CRIANCA_IDADE_MAXIMA:
        raise ConsentimentoErro(
            "nascimento", f"Só guardamos aniversário até {CRIANCA_IDADE_MAXIMA} anos."
        )
    return nascimento


def inserir_crianca(
    client: Client,
    *,
    primeiro_nome: Any,
    nascimento: Any,
    aceite: Any,
    origem: str,
    user_id: int | None = None,
    referencia: str | None = None,
) -> ClienteCrianca:
    """Guarda o aniversário de uma criança, só com o aceite explícito da responsável (art. 14 §1º)."""
    momento = now_sp()
    nome = _validar_nome(primeiro_nome)
    data = _validar_nascimento(nascimento, momento.date())
    if aceite is not True:
        raise ConsentimentoErro(
            "aceite", "Confirme que a responsável autorizou guardar o aniversário."
        )
    crianca = ClienteCrianca(
        client_id=client.id,
        primeiro_nome=nome,
        nascimento=data,
        aceite_em=momento,
        aceite_versao=CONSENTIMENTO_ANIVERSARIO_VERSAO,
        aceite_origem=origem[:ORIGEM_MAXIMA],
        registrado_por_id=user_id,
    )
    db.session.add(crianca)
    _anotar(
        client,
        CONSENTIMENTO_TIPO_ANIVERSARIO,
        CONSENTIMENTO_ACAO_ACEITE,
        CONSENTIMENTO_ANIVERSARIO_TEXTO,
        CONSENTIMENTO_ANIVERSARIO_VERSAO,
        origem,
        referencia,
        user_id,
        momento,
    )
    db.session.flush()
    return crianca


def remover_crianca(client: Client, crianca_id: int, *, user_id: int | None) -> None:
    """Apaga nome e data da criança; o histórico guarda só a retirada (sem o dado dela)."""
    crianca = ClienteCrianca.query.filter_by(id=crianca_id, client_id=client.id).first()
    if crianca is None:
        raise ConsentimentoErro(None, "Aniversário não encontrado.", 404)
    texto, versao = _texto_do_aniversario(crianca)
    db.session.delete(crianca)
    _anotar(
        client,
        CONSENTIMENTO_TIPO_ANIVERSARIO,
        CONSENTIMENTO_ACAO_RETIRADA,
        texto,
        versao,
        CONSENTIMENTO_ORIGEM_FICHA,
        None,
        user_id,
        now_sp(),
    )


def _texto_do_aniversario(crianca: ClienteCrianca) -> tuple[str, str]:
    if crianca.aceite_versao == CONSENTIMENTO_ANIVERSARIO_VERSAO:
        return CONSENTIMENTO_ANIVERSARIO_TEXTO, crianca.aceite_versao
    anterior = ClienteConsentimento.query.filter_by(
        client_id=crianca.client_id,
        tipo=CONSENTIMENTO_TIPO_ANIVERSARIO,
        acao=CONSENTIMENTO_ACAO_ACEITE,
        versao=crianca.aceite_versao,
    ).first()
    return (anterior.texto if anterior else CONSENTIMENTO_ANIVERSARIO_TEXTO), crianca.aceite_versao


# ── Leitura ──────────────────────────────────────────────────────────────────────────────────────


def _iso(momento: datetime | date | None) -> str | None:
    return momento.isoformat() if momento else None


def _autor(linha: ClienteConsentimento) -> str:
    if linha.registrado_por is not None:
        return linha.registrado_por.name
    if linha.origem in _ORIGENS_DA_CLIENTE or linha.origem.startswith(_PREFIXO_DA_LOJA):
        return "A cliente"
    return "Sistema"


def _historico(client: Client) -> list[dict[str, Any]]:
    linhas = (
        ClienteConsentimento.query.filter_by(client_id=client.id)
        .order_by(ClienteConsentimento.registrado_em.desc(), ClienteConsentimento.id.desc())
        .all()
    )
    return [
        {
            "tipo": linha.tipo,
            "acao": linha.acao,
            "em": _iso(linha.registrado_em),
            "origem": linha.origem,
            "versao": linha.versao,
            "texto": linha.texto,
            "referencia": linha.referencia,
            "autor": _autor(linha),
        }
        for linha in linhas
    ]


def _criancas(client: Client) -> list[dict[str, Any]]:
    criancas = (
        ClienteCrianca.query.filter_by(client_id=client.id)
        .order_by(ClienteCrianca.nascimento, ClienteCrianca.id)
        .all()
    )
    return [
        {
            "id": c.id,
            "primeiro_nome": c.primeiro_nome,
            "nascimento": _iso(c.nascimento),
            "aceite_em": _iso(c.aceite_em),
            "origem": c.aceite_origem,
            "versao": c.aceite_versao,
        }
        for c in criancas
    ]


def serializar(client: Client, *, com_criancas: bool) -> dict[str, Any]:
    """O bloco ``consentimentos`` da ficha. Sem ``com_criancas`` a chave nem existe (RBAC)."""
    bloco: dict[str, Any] = {
        "novidades": {
            "ativo": pode_prospectar(client),
            "aceite_em": _iso(client.marketing_opt_in_at),
            "origem": client.marketing_opt_in_source,
            "versao": client.marketing_opt_in_version,
            "retirada_em": _iso(client.marketing_opt_out_at),
            "retirada_origem": client.marketing_opt_out_source,
        },
        "historico": _historico(client),
        "textos": textos(),
        "origens": list(CONSENTIMENTO_ORIGENS_EQUIPE),
    }
    if com_criancas:
        bloco["criancas"] = _criancas(client)
    return bloco


# ── Página pública de avaliação (a própria cliente) ──────────────────────────────────────────────

_ESCOLHAS_DE_NOVIDADES = (None, "aceitar", "retirar")
TEXTO_MUDOU = "O texto desta autorização mudou. Recarregue a página e confira."


def bloco_publico(client: Client) -> dict[str, Any]:
    """O que a página pública mostra: o primeiro nome, se já recebe novidades e os dois textos."""
    partes = (client.name or "").split()
    return {
        "primeiro_nome": partes[0] if partes else None,
        "recebe_novidades": pode_prospectar(client),
        "textos": textos(),
    }


def _exigir_versao(enviada: Any, vigente: str) -> None:
    """A tela manda a versão que exibiu: o histórico só grava o texto que a pessoa viu."""
    if str(enviada or "") != vigente:
        raise ConsentimentoErro(None, TEXTO_MUDOU, 409, "texto_mudou")


def _crianca_publica(client: Client, crianca: dict[str, Any], referencia: str) -> None:
    try:
        inserir_crianca(
            client,
            primeiro_nome=crianca.get("primeiro_nome"),
            nascimento=crianca.get("nascimento"),
            aceite=crianca.get("aceite"),
            origem=CONSENTIMENTO_ORIGEM_POS_EVENTO,
            referencia=referencia,
        )
    except ConsentimentoErro as exc:
        campo = f"crianca.{exc.campo}" if exc.campo else None
        raise ConsentimentoErro(campo, exc.mensagem, exc.status, exc.codigo) from None


def aplicar_escolhas_publicas(client: Client, corpo: dict[str, Any], *, referencia: str) -> None:
    """Aplica o que a cliente marcou na página de avaliação (autor nulo: foi ela)."""
    novidades = corpo.get("novidades")
    crianca = corpo.get("crianca")
    if novidades not in _ESCOLHAS_DE_NOVIDADES:
        raise ConsentimentoErro("novidades", "Escolha inválida.")
    if novidades is None and not isinstance(crianca, dict):
        raise ConsentimentoErro(None, "Marque uma das opções antes de salvar.")
    if isinstance(crianca, dict):
        _exigir_versao(corpo.get("versao_aniversario"), CONSENTIMENTO_ANIVERSARIO_VERSAO)
        _crianca_publica(client, crianca, referencia)
    if novidades == "aceitar":
        _exigir_versao(corpo.get("versao_novidades"), CONSENTIMENTO_NOVIDADES_VERSAO)
        registrar_aceite_novidades(
            client, origem=CONSENTIMENTO_ORIGEM_POS_EVENTO, referencia=referencia
        )
    elif novidades == "retirar":
        retirar_aceite_novidades(
            client, origem=CONSENTIMENTO_ORIGEM_POS_EVENTO, referencia=referencia
        )
