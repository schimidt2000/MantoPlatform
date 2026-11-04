"""Aviso do WhatsApp: gravar cru, reivindicar e processar (feature 325, FR-003 a FR-009, FR-017).

O webhook só grava o corpo e responde 200 (``gravar_aviso``). ``processar_aviso`` transforma o aviso
em conversa, mensagem, status e eco, e é **idempotente**: o reenvio da Meta e a varredura podem
refazer o mesmo aviso quantas vezes for preciso. A idempotência mora em restrições do banco
(``UNIQUE`` do wamid e de (canal, contato)), nunca na confiança do fluxo (armadilha 10 do `docs/00`).

Tudo do aviso entra numa transação só: se um pedaço falha, o aviso inteiro volta a ``pendente`` e a
varredura o refaz (research R5) — não há meio aviso gravado. A mídia é baixada DEPOIS do commit,
fora da transação (pode levar até 2 min e nunca segura linha travada).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app import db
from app.conversas import anuncio_ops, celular_ops, equipe_ops
from app.conversas import constantes as K
from app.conversas.configuracao import CfgWhatsapp
from app.conversas.ficha_ops import ficha_pelo_telefone
from app.conversas.relogio import agora_utc
from app.conversas.telefone import so_digitos, telefone_com_nono
from app.models import Conversa, ConversaMensagem, ConversaMidia, WhatsappAviso

logger = logging.getLogger(__name__)

# Um status cujo envio ainda está em voo (gravado `pendente`, sem wamid) há menos que isto espera a
# varredura; mais velho que isto, o status é de mensagem que não é nossa e é ignorado.
ENVIO_EM_VOO = 300


class MensagemAindaNaoGravada(Exception):
    """O status chegou antes de o envio gravar o wamid (corrida envio × aviso): refazer depois."""


def _momento(valor: Any) -> datetime:
    """O ``timestamp`` da Meta (epoch em segundos, string) em UTC naive; ilegível → agora."""
    try:
        return datetime.fromtimestamp(int(valor), UTC).replace(tzinfo=None)
    except (TypeError, ValueError, OverflowError, OSError):
        return agora_utc()


# ── Gravar e reivindicar ─────────────────────────────────────────────────────────────────────────


def gravar_aviso(corpo: bytes) -> int:
    """Grava o corpo cru como ``pendente`` e comita. Devolve o id do aviso."""
    aviso = WhatsappAviso(corpo=corpo.decode("utf-8", errors="replace"), estado=K.AVISO_PENDENTE)
    db.session.add(aviso)
    db.session.commit()
    return aviso.id


def reivindicar(aviso_id: int) -> bool:
    """Claim atômico (molde ``_reivindicar_aviso`` da 310): só um processo pega cada aviso."""
    agora = agora_utc()
    resultado = db.session.execute(
        text(
            "UPDATE whatsapp_avisos SET estado = :proc, tentativas = tentativas + 1, tentado_em = :agora "
            "WHERE id = :id AND (estado = :pend OR (estado = :proc AND tentado_em < :preso))"
        ),
        {
            "proc": K.AVISO_PROCESSANDO,
            "pend": K.AVISO_PENDENTE,
            "agora": agora,
            "preso": agora - K.PROCESSANDO_PRESO,
            "id": aviso_id,
        },
    )
    db.session.commit()
    return bool(resultado.rowcount)


def _fechar(aviso_id: int, estado_final: str, erro: str | None = None) -> None:
    db.session.execute(
        text(
            "UPDATE whatsapp_avisos SET estado = :e, erro = :erro, processado_em = :agora WHERE id = :id"
        ),
        {
            "e": estado_final,
            "erro": (erro or None) and erro[: K.ERRO_MAXIMO],
            "agora": agora_utc(),
            "id": aviso_id,
        },
    )
    db.session.commit()


def _devolver(aviso_id: int, erro: str) -> str:
    """Devolve o aviso a ``pendente`` — ou o descarta, se já passou da idade ou das tentativas."""
    aviso = db.session.get(WhatsappAviso, aviso_id)
    velho = aviso.recebido_em < agora_utc() - K.AVISO_IDADE_MAXIMA
    if velho or aviso.tentativas >= K.TENTATIVAS_MAXIMAS:
        _fechar(aviso_id, K.AVISO_DESCARTADO, erro)
        return K.AVISO_DESCARTADO
    db.session.execute(
        text("UPDATE whatsapp_avisos SET estado = :pend, erro = :erro WHERE id = :id"),
        {"pend": K.AVISO_PENDENTE, "erro": erro[: K.ERRO_MAXIMO], "id": aviso_id},
    )
    db.session.commit()
    return K.AVISO_PENDENTE


# ── Processar ────────────────────────────────────────────────────────────────────────────────────


def processar_aviso(aviso_id: int, cfg: CfgWhatsapp) -> str:
    """Processa um aviso reivindicado e devolve o estado em que ele ficou.

    Nunca levanta: o webhook responde 200 de qualquer jeito, e a varredura retenta o que voltou a
    ``pendente``.
    """
    if not reivindicar(aviso_id):
        return "ignorado"
    aviso = db.session.get(WhatsappAviso, aviso_id)
    try:
        corpo = json.loads(aviso.corpo)
    except ValueError:
        _fechar(aviso_id, K.AVISO_DESCARTADO, "corpo não é JSON")
        return K.AVISO_DESCARTADO
    # As conversas que ganharam mensagem da cliente neste aviso: tocam no celular depois do commit
    # (feature 332). Eco, reação e reenvio não entram.
    chegadas: set[int] = set()
    try:
        midias, perfis = _processar_corpo(corpo, cfg, chegadas)
        db.session.commit()
    except MensagemAindaNaoGravada as exc:
        db.session.rollback()
        return _devolver(aviso_id, str(exc))
    except Exception as exc:  # noqa: BLE001 — o aviso volta à fila; a varredura refaz
        db.session.rollback()
        logger.warning("[whatsapp] aviso %s falhou no processamento: %s", aviso_id, exc)
        return _devolver(aviso_id, f"{type(exc).__name__}: {exc}")
    _fechar(aviso_id, K.AVISO_PROCESSADO)
    # O perfil antes do aviso no celular (o título é o nome); a mídia, que pode levar minutos, depois
    # (SC-001 da 332: o celular toca em até 10 s); a campanha do anúncio (334), que ninguém espera
    # na tela, por último.
    if perfis:
        _atualizar_perfis(perfis)
    celular_ops.avisar_mensagens(chegadas)
    _baixar_midias(midias, cfg)
    anuncio_ops.consultar_pendentes()
    return K.AVISO_PROCESSADO


def _processar_corpo(
    corpo: Any, cfg: CfgWhatsapp, chegadas: set[int]
) -> tuple[list[int], list[int]]:
    """(mídias a baixar, conversas do Instagram cujo perfil buscar), pelo ``object`` do aviso.

    O Instagram (feature 330) entra pela mesma fila, claim e varredura; import tardio porque
    ``instagram_ops`` importa este módulo.
    """
    if isinstance(corpo, dict) and corpo.get("object") == K.OBJETO_INSTAGRAM:
        from app.conversas import instagram_ops
        from app.conversas.configuracao import cfg_instagram

        return instagram_ops.processar_entradas(corpo, cfg_instagram(), chegadas)
    midias: list[int] = []
    for change in _mudancas(corpo):
        midias.extend(_processar_change(change, cfg, chegadas))
    return midias, []


def _atualizar_perfis(conversa_ids: list[int]) -> None:
    from app.conversas import instagram_ops
    from app.conversas.configuracao import cfg_instagram

    instagram_ops.atualizar_perfis(conversa_ids, cfg_instagram())


def _baixar_midias(midias: list[int], cfg: CfgWhatsapp) -> None:
    from app.conversas import midia_ops

    for midia_id in midias:
        midia_ops.baixar_e_guardar(midia_id, cfg)


def _mudancas(corpo: Any) -> list[dict[str, Any]]:
    """As ``entry[].changes[]`` do aviso (lista vazia para formato inesperado)."""
    if not isinstance(corpo, dict):
        return []
    mudancas: list[dict[str, Any]] = []
    for entrada in corpo.get("entry") or []:
        if isinstance(entrada, dict):
            mudancas.extend(c for c in entrada.get("changes") or [] if isinstance(c, dict))
    return mudancas


def _processar_change(change: dict[str, Any], cfg: CfgWhatsapp, chegadas: set[int]) -> list[int]:
    """Uma mudança do aviso. Devolve os ids das mídias a baixar depois do commit e junta em
    ``chegadas`` as conversas com mensagem nova da cliente."""
    valor = change.get("value") or {}
    numero = (valor.get("metadata") or {}).get("phone_number_id")
    if numero and numero != cfg.conexao.phone_number_id:
        # Um app com dois números nunca mistura as caixas.
        logger.info("[whatsapp] aviso de outro número (%s) ignorado", numero)
        return []
    for erro in valor.get("errors") or []:
        logger.warning("[whatsapp] erro de conta no aviso: %s", erro)
    campo = change.get("field")
    if campo == "messages":
        return _processar_mensagens(valor, chegadas)
    if campo == "smb_message_echoes":
        return _processar_ecos(valor)
    return []


def _processar_mensagens(valor: dict[str, Any], chegadas: set[int]) -> list[int]:
    contatos = {
        c.get("wa_id"): c
        for c in valor.get("contacts") or []
        if isinstance(c, dict) and c.get("wa_id")
    }
    midias: list[int] = []
    for mensagem in valor.get("messages") or []:
        if not isinstance(mensagem, dict):
            continue
        if mensagem.get("group_id"):
            # Mensagem de grupo (Groups API) não é conversa 1:1 com a cliente: cairia na caixa do
            # participante como se ele tivesse escrito para a Manto.
            logger.info("[whatsapp] mensagem de grupo %s ignorada", mensagem.get("group_id"))
            continue
        midia_id = _gravar_recebida(mensagem, contatos.get(mensagem.get("from")) or {}, chegadas)
        if midia_id:
            midias.append(midia_id)
    for status in valor.get("statuses") or []:
        if isinstance(status, dict):
            _aplicar_status(status)
    return midias


# ── Conversa e vínculo com a ficha ───────────────────────────────────────────────────────────────


def conversa_do_contato(
    contato_id: str,
    *,
    bsuid: str | None = None,
    nome: str | None = None,
    canal: str = K.CANAL_WHATSAPP,
) -> Conversa:
    """A conversa do contato, criada se preciso — sem duplicar entre dois avisos simultâneos.

    Telefone e vínculo com a ficha só no WhatsApp: o IGSID do Instagram (feature 330) também é só
    dígitos e cairia na ficha de um telefone qualquer.
    """
    numerico = canal == K.CANAL_WHATSAPP and so_digitos(contato_id) == contato_id
    telefone = telefone_com_nono(contato_id) if numerico else None
    agora = agora_utc()
    db.session.execute(
        pg_insert(Conversa.__table__)
        .values(
            canal=canal,
            contato_id=contato_id,
            contato_bsuid=bsuid,
            telefone=telefone,
            nome_perfil=nome,
            nao_lidas=0,
            created_at=agora,
            updated_at=agora,
        )
        .on_conflict_do_nothing(constraint="uq_conversas_canal_contato")
    )
    conversa = Conversa.query.filter_by(canal=canal, contato_id=contato_id).one()
    if nome and conversa.nome_perfil != nome:
        conversa.nome_perfil = nome
    if bsuid and not conversa.contato_bsuid:
        conversa.contato_bsuid = bsuid
    _vincular_cliente(conversa)
    return conversa


def _vincular_cliente(conversa: Conversa) -> None:
    """Liga à ficha pelo telefone, com e sem o nono dígito (FR-005; regra em `ficha_ops`)."""
    if conversa.client_id is not None or conversa.ficha_manual or not conversa.telefone:
        return  # ficha escolhida (ou removida) à mão: a automática não mexe (feature 333)
    escolhida = ficha_pelo_telefone(conversa.telefone)
    if escolhida is not None:
        conversa.client_id = escolhida.id
        # A conversa que já veio de anúncio e só agora acha a ficha (feature 334, FR-007).
        anuncio_ops.aplicar_na_ficha(conversa, escolhida)


def atualizar_previa(conversa: Conversa, tipo: str, texto: str | None, momento: datetime) -> None:
    """Prévia e horário da lista: só a mensagem mais nova (recebida, enviada ou eco) muda."""
    if conversa.ultima_mensagem_em is None or momento >= conversa.ultima_mensagem_em:
        conversa.ultima_mensagem_em = momento
        previa = (texto or K.PREVIA_DO_TIPO.get(tipo) or "").strip()
        conversa.ultima_previa = previa[: K.PREVIA_MAXIMA] or None


# ── Mensagem recebida ────────────────────────────────────────────────────────────────────────────


def _texto_recebido(mensagem: dict[str, Any], tipo: str) -> str | None:
    """O texto que a conversa mostra para cada tipo (legenda, emoji, título do botão ou rótulo)."""
    bloco = mensagem.get(mensagem.get("type") or "") or {}
    if tipo == K.TIPO_TEXTO:
        return (bloco.get("body") or "").strip() or None
    if tipo in (K.TIPO_IMAGEM, K.TIPO_VIDEO, K.TIPO_DOCUMENTO):
        return (bloco.get("caption") or "").strip() or None
    if tipo in (K.TIPO_AUDIO, K.TIPO_FIGURINHA):
        return None
    if tipo == K.TIPO_REACAO:
        emoji = bloco.get("emoji")
        return f"Reagiu com {emoji}" if emoji else K.TEXTO_REACAO_REMOVIDA
    if tipo == K.TIPO_INTERATIVA:
        resposta = bloco.get("button_reply") or bloco.get("list_reply") or {}
        return resposta.get("title") or bloco.get("text") or K.TEXTO_DO_TIPO[K.TIPO_INTERATIVA]
    return K.TEXTO_DO_TIPO.get(tipo) or K.TEXTO_DO_TIPO[K.TIPO_OUTRO]


def inserir_mensagem(**valores: Any) -> int | None:
    """INSERT idempotente pelo wamid: ``None`` quando a mensagem já existia (reenvio)."""
    linha = db.session.execute(
        pg_insert(ConversaMensagem.__table__)
        .values(created_at=agora_utc(), **valores)
        .on_conflict_do_nothing(index_elements=["externo_id"])
        .returning(ConversaMensagem.__table__.c.id)
    ).first()
    return linha[0] if linha else None


def _criar_midia(mensagem_id: int, mensagem: dict[str, Any]) -> int | None:
    bloco = mensagem.get(mensagem.get("type") or "") or {}
    if not bloco.get("id"):
        return None
    midia = ConversaMidia(
        mensagem_id=mensagem_id,
        externo_id=str(bloco["id"]),
        mime=bloco.get("mime_type"),
        nome_original=(bloco.get("filename") or None),
        estado=K.MIDIA_PENDENTE,
    )
    db.session.add(midia)
    db.session.flush()
    return midia.id


def _gravar_recebida(
    mensagem: dict[str, Any], contato: dict[str, Any], chegadas: set[int]
) -> int | None:
    """Grava a mensagem da cliente (FR-006). Devolve o id da mídia a baixar, se houver."""
    wa_id = mensagem.get("from") or contato.get("wa_id")
    bsuid = mensagem.get("from_user_id") or contato.get("user_id")
    contato_id = wa_id or bsuid
    if not contato_id or not mensagem.get("id"):
        return None
    nome = ((contato.get("profile") or {}).get("name") or "").strip() or None
    conversa = conversa_do_contato(str(contato_id), bsuid=bsuid, nome=nome)
    tipo = K.TIPO_DA_META.get(mensagem.get("type") or "", K.TIPO_OUTRO)
    texto = _texto_recebido(mensagem, tipo)
    momento = _momento(mensagem.get("timestamp"))
    mensagem_id = inserir_mensagem(
        conversa_id=conversa.id,
        direcao=K.RECEBIDA,
        tipo=tipo,
        texto=texto,
        externo_id=str(mensagem["id"]),
        situacao=K.SITUACAO_RECEBIDA,
        origem=K.ORIGEM_CONTATO,
        resposta_a=(mensagem.get("context") or {}).get("id"),
        dados=json.dumps(mensagem),
        momento=momento,
    )
    if mensagem_id is None:
        return None  # reenvio: nada conta de novo
    if isinstance(mensagem.get("referral"), dict):
        # A cliente veio de um anúncio "clique para o WhatsApp" (feature 334).
        anuncio_ops.contato_do_whatsapp(conversa, str(mensagem["id"]), mensagem["referral"], momento)
    conversa.nao_lidas = (conversa.nao_lidas or 0) + 1
    if conversa.ultima_recebida_em is None or momento > conversa.ultima_recebida_em:
        conversa.ultima_recebida_em = momento
    if tipo != K.TIPO_REACAO:  # o 👍 da cliente não é pergunta esperando resposta (nem toca)
        equipe_ops.abrir_espera(conversa, momento)
        chegadas.add(conversa.id)
    atualizar_previa(conversa, tipo, texto, momento)
    return _criar_midia(mensagem_id, mensagem) if tipo in K.TIPOS_COM_MIDIA else None


# ── Status da enviada ────────────────────────────────────────────────────────────────────────────


def envio_em_voo(conversa_id: int | None = None) -> bool:
    """Há envio gravado `pendente`, sem wamid, há pouco tempo? Então o status pode ser dele."""
    return bool(
        ConversaMensagem.query.filter(
            ConversaMensagem.direcao == K.ENVIADA,
            ConversaMensagem.situacao == K.SITUACAO_PENDENTE,
            ConversaMensagem.externo_id.is_(None),
            ConversaMensagem.created_at >= agora_utc() - timedelta(seconds=ENVIO_EM_VOO),
            # O eco do Instagram (330) olha só a conversa dele; o status do WhatsApp, todas.
            *([ConversaMensagem.conversa_id == conversa_id] if conversa_id else []),
        ).first()
    )


def _aplicar_status(status: dict[str, Any]) -> None:
    """Aplica o status de uma enviada, sem nunca regredir (FR-009)."""
    situacao = K.SITUACAO_DO_STATUS.get(status.get("status") or "")
    wamid = status.get("id")
    if situacao is None or not wamid:
        return
    mensagem = ConversaMensagem.query.filter_by(externo_id=str(wamid)).with_for_update().first()
    if mensagem is None:
        if envio_em_voo():
            raise MensagemAindaNaoGravada("mensagem ainda não gravada")
        return  # status de mensagem que não saiu da Plataforma
    if mensagem.direcao != K.ENVIADA:
        return
    atual = K.ORDEM_DA_SITUACAO.get(mensagem.situacao)
    if situacao == K.SITUACAO_FALHOU:
        if atual is not None and atual <= K.ORDEM_DA_SITUACAO[K.SITUACAO_ENVIADA]:
            erro = (status.get("errors") or [{}])[0] or {}
            codigo = erro.get("code") if isinstance(erro.get("code"), int) else None
            mensagem.situacao = K.SITUACAO_FALHOU
            mensagem.erro_codigo = codigo
            mensagem.erro_motivo = K.motivo_do_erro(codigo)
            # A resposta que não chegou não conta: a espera volta (feature 328).
            db.session.flush()
            equipe_ops.recalcular_espera(mensagem.conversa)
        return
    nova = K.ORDEM_DA_SITUACAO[situacao]
    if atual is not None and nova > atual:
        mensagem.situacao = situacao


# ── Eco do app do celular (coexistência) ─────────────────────────────────────────────────────────


def _texto_do_eco(eco: dict[str, Any], tipo_meta: str) -> tuple[str, str | None]:
    if tipo_meta == "revoke":
        return K.TIPO_TEXTO, K.TEXTO_APAGADA_NO_CELULAR
    if tipo_meta == "edit":
        return K.TIPO_TEXTO, K.TEXTO_EDITADA_NO_CELULAR
    tipo = K.TIPO_DA_META.get(tipo_meta, K.TIPO_OUTRO)
    return tipo, _texto_recebido(eco, tipo)


def _processar_ecos(valor: dict[str, Any]) -> list[int]:
    """Mensagens que a equipe mandou pelo app WhatsApp Business (FR-017, research R12)."""
    midias: list[int] = []
    for eco in valor.get("message_echoes") or []:
        valido = (
            isinstance(eco, dict) and eco.get("id") and (eco.get("to") or eco.get("to_user_id"))
        )
        if valido and (midia_id := _gravar_eco(eco)):
            midias.append(midia_id)
    return midias


def _gravar_eco(eco: dict[str, Any]) -> int | None:
    """Grava um eco como enviada pelo celular. Devolve o id da mídia a baixar, se houver."""
    conversa = conversa_do_contato(
        str(eco.get("to") or eco.get("to_user_id")), bsuid=eco.get("to_user_id")
    )
    tipo, texto = _texto_do_eco(eco, eco.get("type") or "")
    momento = _momento(eco.get("timestamp"))
    mensagem_id = inserir_mensagem(
        conversa_id=conversa.id,
        direcao=K.ENVIADA,
        tipo=tipo,
        texto=texto,
        externo_id=str(eco["id"]),
        situacao=K.SITUACAO_ENVIADA,
        origem=K.ORIGEM_CELULAR,
        dados=json.dumps(eco),
        momento=momento,
    )
    if mensagem_id is None:
        return None
    # Só a cliente reabre a janela (R9): o eco atualiza a prévia, não `ultima_recebida_em`.
    atualizar_previa(conversa, tipo, texto, momento)
    # O eco é resposta da equipe pelo celular (encerra a espera), mas sem autor: não atribui
    # (feature 328). Apagar ou editar pelo celular não é resposta.
    if (eco.get("type") or "") not in ("revoke", "edit") and tipo != K.TIPO_REACAO:
        equipe_ops.encerrar_espera(conversa, momento)
    return _criar_midia(mensagem_id, eco) if tipo in K.TIPOS_COM_MIDIA else None
