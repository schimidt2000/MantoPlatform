"""O aviso do Instagram Direct vira conversa, mensagem, mídia, eco, reação e visto (feature 330).

Mesmo pipeline do WhatsApp (feature 325): o webhook grava o aviso cru, ``aviso_ops.processar_aviso``
reivindica e despacha para cá pelo ``object`` do corpo, e tudo entra numa transação só — se um pedaço
falha, o aviso volta a ``pendente`` e a varredura refaz. A idempotência é a mesma: ``UNIQUE`` do id da
Meta (o ``mid``) com ``ON CONFLICT DO NOTHING``.

Formato (research R4/R5): ``entry[].messaging[]`` — e ``entry[].standby[]`` quando outro app (o Kommo,
no piloto) tem o controle da conversa — com ``sender``, ``recipient``, ``timestamp`` (ms) e um entre
``message`` (com ``is_echo``/``is_deleted``), ``reaction`` e ``read``. O perfil (nome e @usuário) é
buscado DEPOIS do commit (``atualizar_perfis``): falha de perfil nunca devolve o aviso à fila.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_

from app import db
from app.clientes import consentimento_ops
from app.conversas import anuncio_ops, aviso_ops, equipe_ops, midia_ops, primeira_resposta_ops
from app.conversas import constantes as K
from app.conversas.relogio import agora_utc
from app.integracoes import instagram_client as ic
from app.integracoes import whatsapp_client as wc
from app.models import Conversa, ConversaMensagem, ConversaMidia

logger = logging.getLogger(__name__)

Parte = tuple[str, str, str | None, int | None]  # externo_id, tipo, texto, índice do anexo


def _momento_ms(valor: Any) -> datetime:
    """O ``timestamp`` do Instagram (epoch em MILISSEGUNDOS) em UTC naive; ilegível → agora."""
    try:
        return datetime.fromtimestamp(int(valor) / 1000, UTC).replace(tzinfo=None)
    except (TypeError, ValueError, OverflowError, OSError):
        return agora_utc()


# ── Entrada ──────────────────────────────────────────────────────────────────────────────────────


def processar_entradas(
    corpo: dict[str, Any], cfg: Any, chegadas: set[int]
) -> tuple[list[int], list[int]]:
    """Processa o aviso do Instagram. Devolve (mídias a baixar, conversas cujo perfil buscar) e junta
    em ``chegadas`` as conversas com mensagem nova da cliente (aviso no celular, feature 332).

    Não comita: ``processar_aviso`` comita o aviso inteiro. Conta diferente da Manto é ignorada.
    """
    midias: list[int] = []
    conversas: set[int] = set()
    for entrada in corpo.get("entry") or []:
        if not isinstance(entrada, dict):
            continue
        if str(entrada.get("id") or "") != cfg.account_id:
            logger.info("[instagram] aviso de outra conta (%s) ignorado", entrada.get("id"))
            continue
        for item in _itens(entrada):
            conversa_id, novas = _processar_item(item, cfg, chegadas)
            midias.extend(novas)
            if conversa_id:
                conversas.add(conversa_id)
    return midias, sorted(conversas)


def _itens(entrada: dict[str, Any]) -> list[dict[str, Any]]:
    """``messaging[]`` e ``standby[]``: a mensagem em espera é gravada igual (nunca respondida)."""
    return [
        item
        for chave in ("messaging", "standby")
        for item in entrada.get(chave) or []
        if isinstance(item, dict)
    ]


def _processar_item(
    item: dict[str, Any], cfg: Any, chegadas: set[int]
) -> tuple[int | None, list[int]]:
    mensagem = item.get("message")
    if isinstance(mensagem, dict):
        if mensagem.get("is_echo"):
            return _gravar_eco(item, mensagem)
        return _gravar_recebida(item, mensagem, cfg, chegadas)
    if isinstance(item.get("reaction"), dict):
        return _gravar_reacao(item), []
    if isinstance(item.get("read"), dict):
        _aplicar_visto(item)
    if isinstance(item.get("postback"), dict):
        return _gravar_postback(item, chegadas), []
    if isinstance(item.get("referral"), dict):
        return _gravar_abertura(item), []
    return None, []


def _gravar_abertura(item: dict[str, Any]) -> int | None:
    """A cliente abriu a conversa pelo anúncio e ainda não escreveu (``OPEN_THREAD``, feature 334):
    a conversa nasce, o contato fica registrado e o perfil vem depois do commit."""
    igsid = _contato(item, "sender")
    if not igsid:
        return None
    conversa = _conversa(igsid)
    anuncio_ops.contato_do_instagram(
        conversa,
        f"ref:{igsid}:{item.get('timestamp')}",
        item["referral"],
        _momento_ms(item.get("timestamp")),
    )
    return conversa.id


def _contato(item: dict[str, Any], chave: str) -> str:
    return str((item.get(chave) or {}).get("id") or "")


def _conversa(igsid: str) -> Conversa:
    return aviso_ops.conversa_do_contato(igsid, canal=K.CANAL_INSTAGRAM)


# ── Mensagem: as partes ──────────────────────────────────────────────────────────────────────────


def _juntar(base: str, texto: str | None) -> str:
    return f"{base} {texto}" if texto else base


def _texto_da_mensagem(mensagem: dict[str, Any]) -> str | None:
    texto = (mensagem.get("text") or "").strip() or None
    if (mensagem.get("reply_to") or {}).get("story"):
        return _juntar(K.TEXTO_RESPOSTA_AO_STORY, texto)
    return texto


def _partes(mid: str, mensagem: dict[str, Any]) -> list[Parte]:
    """Uma parte por anexo (a mídia é 1:1 com a mensagem na 325); o texto vai na primeira."""
    if mensagem.get("is_unsupported"):
        return [(mid, K.TIPO_OUTRO, K.TEXTO_NAO_SUPORTADA_IG, None)]
    texto = _texto_da_mensagem(mensagem)
    anexos = [a for a in mensagem.get("attachments") or [] if isinstance(a, dict)]
    if not anexos:
        return [(mid, K.TIPO_TEXTO, texto or K.TEXTO_NAO_SUPORTADA_IG, None)]
    partes: list[Parte] = []
    for indice, anexo in enumerate(anexos):
        externo = mid if indice == 0 else f"{mid}#{indice}"
        legenda = texto if indice == 0 else None
        tipo_meta = anexo.get("type") or ""
        if tipo_meta in K.TIPO_DO_ANEXO_IG and (anexo.get("payload") or {}).get("url"):
            partes.append((externo, K.TIPO_DO_ANEXO_IG[tipo_meta], legenda, indice))
        else:
            base = K.TEXTO_DO_ANEXO_IG.get(tipo_meta, K.TEXTO_NAO_SUPORTADA_IG)
            partes.append((externo, K.TIPO_TEXTO, _juntar(base, legenda), None))
    return partes


def _inserir_partes(
    conversa: Conversa, item: dict[str, Any], partes: list[Parte], direcao: str, origem: str
) -> tuple[list[int], list[int]]:
    """Grava as partes sem duplicar. Devolve (ids das mensagens novas, ids das mídias a baixar)."""
    mensagem = item.get("message") or {}
    momento = _momento_ms(item.get("timestamp"))
    novas: list[int] = []
    midias: list[int] = []
    for externo, tipo, texto, indice in partes:
        mensagem_id = aviso_ops.inserir_mensagem(
            conversa_id=conversa.id,
            direcao=direcao,
            tipo=tipo,
            texto=texto,
            externo_id=externo[:255],
            situacao=K.SITUACAO_RECEBIDA if direcao == K.RECEBIDA else K.SITUACAO_ENVIADA,
            origem=origem,
            resposta_a=((mensagem.get("reply_to") or {}).get("mid") or None),
            dados=json.dumps(item),
            momento=momento,
        )
        if mensagem_id is None:
            continue
        novas.append(mensagem_id)
        if indice is not None:
            midias.append(_criar_midia(mensagem_id))
    if novas:
        ultima = partes[-1]
        aviso_ops.atualizar_previa(conversa, ultima[1], partes[0][2] or ultima[2], momento)
    return novas, midias


def _criar_midia(mensagem_id: int) -> int:
    """Sem id da Meta: o link do anexo mora no ``dados`` da mensagem (research R6)."""
    midia = ConversaMidia(mensagem_id=mensagem_id, estado=K.MIDIA_PENDENTE)
    db.session.add(midia)
    db.session.flush()
    return midia.id


# ── Mensagem recebida, apagada e eco ─────────────────────────────────────────────────────────────


def _chegou_da_cliente(conversa: Conversa, item: dict[str, Any], chegadas: set[int]) -> None:
    """A cliente escreveu (ou tocou num botão): não lida, janela reaberta, espera (328) e o aviso
    no celular (332)."""
    momento = _momento_ms(item.get("timestamp"))
    conversa.nao_lidas = (conversa.nao_lidas or 0) + 1
    if conversa.ultima_recebida_em is None or momento > conversa.ultima_recebida_em:
        conversa.ultima_recebida_em = momento
    equipe_ops.abrir_espera(conversa, momento)
    primeira_resposta_ops.registrar_contato(conversa, momento)  # feature 349
    chegadas.add(conversa.id)


def _gravar_recebida(
    item: dict[str, Any], mensagem: dict[str, Any], cfg: Any, chegadas: set[int]
) -> tuple[int | None, list[int]]:
    igsid, mid = _contato(item, "sender"), mensagem.get("mid")
    if not igsid or not mid:
        return None, []
    conversa = _conversa(igsid)
    if mensagem.get("is_deleted"):
        _apagar(conversa, str(mid), item, cfg)
        return conversa.id, []
    novas, midias = _inserir_partes(
        conversa, item, _partes(str(mid), mensagem), K.RECEBIDA, K.ORIGEM_CONTATO
    )
    if novas:
        _chegou_da_cliente(conversa, item, chegadas)
        # Feature 350: "SAIR" (a mensagem inteira) também tira o aceite pelo Instagram.
        consentimento_ops.retirar_se_pediu_para_parar(
            conversa, mensagem.get("text"), f"instagram:{mid}"
        )
    if isinstance(mensagem.get("referral"), dict):
        momento = _momento_ms(item.get("timestamp"))
        anuncio_ops.contato_do_instagram(conversa, str(mid), mensagem["referral"], momento)
    return conversa.id, midias


def _gravar_postback(item: dict[str, Any], chegadas: set[int]) -> int | None:
    """Toque num botão da conversa (ice breaker): é a cliente puxando assunto (FR-004)."""
    postback = item.get("postback") or {}
    igsid = _contato(item, "sender")
    if not igsid:
        return None
    conversa = _conversa(igsid)
    titulo = (postback.get("title") or "").strip() or "botão"
    externo = str(postback.get("mid") or f"postback:{igsid}:{item.get('timestamp')}")
    parte = (externo, K.TIPO_INTERATIVA, K.TEXTO_POSTBACK.format(titulo=titulo), None)
    novas, _ = _inserir_partes(conversa, item, [parte], K.RECEBIDA, K.ORIGEM_CONTATO)
    if novas:
        _chegou_da_cliente(conversa, item, chegadas)
    if isinstance(postback.get("referral"), dict):
        momento = _momento_ms(item.get("timestamp"))
        anuncio_ops.contato_do_instagram(conversa, externo, postback["referral"], momento)
    return conversa.id


def _partes_da_mensagem(conversa: Conversa, mid: str) -> list[ConversaMensagem]:
    return ConversaMensagem.query.filter(
        ConversaMensagem.conversa_id == conversa.id,
        or_(ConversaMensagem.externo_id == mid, ConversaMensagem.externo_id.like(f"{mid}#%")),
    ).all()


def _apagar(conversa: Conversa, mid: str, item: dict[str, Any], cfg: Any) -> None:
    """A cliente apagou: some o que ela mandou (texto e mídia, inclusive o arquivo guardado) e fica o
    aviso no lugar; a prévia da lista também. Sem a mensagem gravada, ela nasce já apagada."""
    partes = _partes_da_mensagem(conversa, mid)
    if not partes:
        parte = (mid, K.TIPO_TEXTO, K.TEXTO_APAGADA_PELA_CLIENTE, None)
        _inserir_partes(conversa, item, [parte], K.RECEBIDA, K.ORIGEM_CONTATO)
        return
    for mensagem in partes:
        if mensagem.midia is not None:
            midia_ops.apagar_arquivo(mensagem.midia, cfg)
            db.session.delete(mensagem.midia)
        mensagem.tipo = K.TIPO_TEXTO
        mensagem.texto = K.TEXTO_APAGADA_PELA_CLIENTE
    if (
        conversa.ultima_mensagem_em
        and max(m.momento for m in partes) >= conversa.ultima_mensagem_em
    ):
        conversa.ultima_previa = K.TEXTO_APAGADA_PELA_CLIENTE


def _gravar_eco(item: dict[str, Any], mensagem: dict[str, Any]) -> tuple[int | None, list[int]]:
    """O que saiu da conta da Manto por outro caminho (app do Instagram ou Kommo): ENVIADA, origem
    ``outro``. O eco da própria Plataforma tem o mesmo ``mid`` e não duplica; se ele chega antes de o
    envio gravar o ``mid``, o aviso volta à fila (como o status do WhatsApp na 325)."""
    igsid, mid = _contato(item, "recipient"), mensagem.get("mid")
    if not igsid or not mid:
        return None, []
    conversa = _conversa(igsid)
    if ConversaMensagem.query.filter_by(externo_id=str(mid)[:255]).first() is not None:
        return conversa.id, []
    if aviso_ops.envio_em_voo(conversa.id):
        raise aviso_ops.MensagemAindaNaoGravada("eco antes do mid do envio")
    novas, midias = _inserir_partes(
        conversa, item, _partes(str(mid), mensagem), K.ENVIADA, K.ORIGEM_OUTRO
    )
    if novas:
        momento = _momento_ms(item.get("timestamp"))
        equipe_ops.encerrar_espera(conversa, momento)
        # Feature 349: o que saiu por outro app (Instagram, Kommo) é resposta sem autor.
        primeira_resposta_ops.registrar_resposta(conversa, momento, None, K.ORIGEM_OUTRO)
    return conversa.id, midias


# ── Reação e visto ───────────────────────────────────────────────────────────────────────────────


def _gravar_reacao(item: dict[str, Any]) -> int | None:
    """Reação da cliente: aparece na conversa, conta como não lida e não abre espera (328)."""
    reacao = item.get("reaction") or {}
    igsid, mid = _contato(item, "sender"), reacao.get("mid")
    if not igsid or not mid:
        return None
    conversa = _conversa(igsid)
    acao = reacao.get("action") or "react"
    emoji = reacao.get("emoji")
    texto = f"Reagiu com {emoji}" if acao == "react" and emoji else K.TEXTO_REACAO_REMOVIDA
    externo = f"reacao:{mid}:{item.get('timestamp')}:{acao}"
    parte = (externo, K.TIPO_REACAO, texto, None)
    novas, _ = _inserir_partes(conversa, item, [parte], K.RECEBIDA, K.ORIGEM_CONTATO)
    if novas:
        conversa.nao_lidas = (conversa.nao_lidas or 0) + 1
    return conversa.id


def _aplicar_visto(item: dict[str, Any]) -> None:
    """A cliente viu até a mensagem ``read.mid``: ela e as enviadas anteriores ficam ``lida`` (sem
    regredir). Sem a mensagem indicada (eco que não foi gravado), vale o horário do aviso."""
    igsid = _contato(item, "sender")
    conversa = Conversa.query.filter_by(canal=K.CANAL_INSTAGRAM, contato_id=igsid).first()
    if conversa is None:
        return
    mid = str((item.get("read") or {}).get("mid") or "")
    alvo = ConversaMensagem.query.filter_by(externo_id=mid[:255]).first() if mid else None
    if alvo is not None and alvo.conversa_id == conversa.id:
        ate = or_(ConversaMensagem.momento <= alvo.momento, ConversaMensagem.id == alvo.id)
    else:
        ate = ConversaMensagem.momento <= _momento_ms(item.get("timestamp"))
    ConversaMensagem.query.filter(
        ConversaMensagem.conversa_id == conversa.id,
        ConversaMensagem.direcao == K.ENVIADA,
        ConversaMensagem.situacao.in_((K.SITUACAO_ENVIADA, K.SITUACAO_ENTREGUE)),
        ate,
    ).update({"situacao": K.SITUACAO_LIDA}, synchronize_session=False)


# ── Perfil (depois do commit) ────────────────────────────────────────────────────────────────────


def _precisa_de_perfil(conversa: Conversa, agora: datetime) -> bool:
    if conversa.perfil_em is None:
        return True
    return not conversa.nome_perfil and agora - conversa.perfil_em >= K.PERFIL_INTERVALO


def atualizar_perfis(conversa_ids: list[int], cfg: Any) -> None:
    """Busca nome e @usuário de quem ainda não tem (no máximo uma vez por dia). Comita; nunca levanta."""
    agora = agora_utc()
    for conversa_id in conversa_ids:
        conversa = db.session.get(Conversa, conversa_id)
        if conversa is None or not _precisa_de_perfil(conversa, agora):
            continue
        try:
            perfil = ic.perfil(cfg.conexao, conversa.contato_id)
        except wc.WhatsappErro as exc:
            logger.info("[instagram] perfil de %s indisponível: %s", conversa_id, exc)
            perfil = {}
        conversa.nome_perfil = perfil.get("nome") or conversa.nome_perfil
        conversa.usuario = perfil.get("usuario") or conversa.usuario
        conversa.perfil_em = agora
        db.session.commit()
