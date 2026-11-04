"""Envio pelas Conversas: texto, arquivo e modelo, e "marcar como lida" (feature 325, research R8).

A ordem de todo envio:
1. a mesma ``chave_envio`` já gravada devolve a mensagem existente, sem chamar a Meta (FR-018);
2. configurado? travado neste ambiente? janela aberta (texto e arquivo; modelo dispensa)?;
3. a mensagem é gravada ``pendente`` e comitada ANTES da chamada (a chave é UNIQUE);
4. a chamada à Meta sai sem trava de linha nem transação aberta;
5. a resposta grava o wamid (``enviada``) ou o motivo (``falhou``).

Falha da Meta não é erro da requisição: a mensagem fica "não entregue" com o motivo, e a tela
oferece "Tentar novamente" (nova chave). Nada é reenviado sozinho.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import IntegrityError

from app import db
from app.conversas import canais, equipe_ops, midia_ops
from app.conversas import constantes as K
from app.conversas.aviso_ops import agora_utc, atualizar_previa
from app.conversas.configuracao import CfgWhatsapp
from app.conversas.leitura_ops import janela_aberta
from app.conversas.recusa import Recusa, campo
from app.conversas.telefone import so_digitos
from app.integracoes import whatsapp_client as wc
from app.models import Conversa, ConversaMensagem, ConversaMidia

logger = logging.getLogger(__name__)

VARIAVEL = re.compile(r"\{\{\s*(\w+)\s*\}\}")
FORMATOS_DE_CABECALHO_COM_ARQUIVO = {"IMAGE", "VIDEO", "DOCUMENT", "LOCATION"}

TEXTO_NAO_CONFIGURADO = "O WhatsApp ainda não foi configurado."
TEXTO_TRAVADO = "O envio pelo WhatsApp está travado neste ambiente."
TEXTO_JANELA_FECHADA = (
    "A janela de 24 horas desta conversa fechou. Envie um modelo aprovado para retomar o contato."
)


class EnvioRecusado(Recusa):
    """Recusa do envio. Mesmo formato da `Recusa` da equipe (a tela trata as duas igual)."""


@dataclass(frozen=True)
class Envio:
    """O resultado: a mensagem e se ela nasceu agora (201) ou já existia pela chave (200)."""

    mensagem: ConversaMensagem
    nova: bool


# ── Pré-condições ────────────────────────────────────────────────────────────────────────────────


def _campo(nome: str, mensagem: str) -> EnvioRecusado:
    recusa = campo(nome, mensagem)
    return EnvioRecusado(recusa.codigo, recusa.mensagem, recusa.status, recusa.fields)


def _validar_chave(chave: str | None) -> str:
    chave = (chave or "").strip()
    if not K.CHAVE_ENVIO_MINIMA <= len(chave) <= K.CHAVE_ENVIO_MAXIMA:
        raise _campo("chave_envio", "Chave de envio inválida. Recarregue a tela e tente novamente.")
    return chave


def _ja_enviada(chave: str) -> ConversaMensagem | None:
    return ConversaMensagem.query.filter_by(chave_envio=chave).first()


def conversa_ou_404(conversa_id: int) -> Conversa:
    """A conversa, ou a recusa 404."""
    conversa = db.session.get(Conversa, conversa_id)
    if conversa is None:
        raise EnvioRecusado("nao_encontrada", K.TEXTO_CONVERSA_NAO_ENCONTRADA, 404)
    return conversa


def _pre_condicoes(
    cfg: CfgWhatsapp, conversa: Conversa, *, exige_janela: bool
) -> dict[str, str]:
    """Canal ligado, trava e janela. Devolve os campos extras do envio (Instagram: a marca humana)."""
    if canais.e_instagram(conversa):
        return canais.pre_condicoes(conversa, exige_janela=exige_janela)
    if not cfg.ligado:
        raise EnvioRecusado("nao_configurado", TEXTO_NAO_CONFIGURADO, 503)
    if cfg.travado:
        raise EnvioRecusado("envio_travado", TEXTO_TRAVADO, 409)
    if exige_janela and not janela_aberta(conversa):
        raise EnvioRecusado("janela_fechada", TEXTO_JANELA_FECHADA, 409)
    return {}


def conferir_envio(cfg: CfgWhatsapp, conversa: Conversa) -> None:
    """As pré-condições do envio comum (canal, trava e janela), sem enviar nada.

    Para o envio composto da feature 333 (orçamento: texto em partes e PDF): recusar antes de criar
    a ficha e o registro, e não no meio, com metade já enviada.

    Raises:
        EnvioRecusado: 503 ``nao_configurado``, 409 ``envio_travado`` / ``janela_fechada``.
    """
    _pre_condicoes(cfg, conversa, exige_janela=True)


# ── Reservar, despachar ──────────────────────────────────────────────────────────────────────────


def _reservar(
    conversa: Conversa,
    chave: str,
    tipo: str,
    texto: str | None,
    autor_id: int | None,
    modelo_nome: str | None = None,
) -> Envio:
    """Grava a mensagem ``pendente`` e comita. A chave repetida por corrida devolve a existente."""
    mensagem = ConversaMensagem(
        conversa_id=conversa.id,
        direcao=K.ENVIADA,
        tipo=tipo,
        texto=texto,
        chave_envio=chave,
        situacao=K.SITUACAO_PENDENTE,
        autor_id=autor_id,
        origem=K.ORIGEM_PLATAFORMA,
        modelo_nome=modelo_nome,
        momento=agora_utc(),
    )
    db.session.add(mensagem)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return Envio(_ja_enviada(chave), nova=False)
    return Envio(mensagem, nova=True)


def _destino(conversa: Conversa) -> dict[str, str]:
    """``to`` com o wa_id (como a Meta mandou); sem ele, ``recipient`` com o BSUID."""
    if so_digitos(conversa.contato_id) == conversa.contato_id:
        return {"to": conversa.contato_id}
    return {"recipient": conversa.contato_bsuid or conversa.contato_id}


def _registrar_falha(
    mensagem: ConversaMensagem,
    exc: wc.WhatsappErro,
    conversa: Conversa | None = None,
    extras: dict[str, str] | None = None,
) -> None:
    codigo = exc.code if isinstance(exc, wc.WhatsappRecusou) else None
    mensagem.situacao = K.SITUACAO_FALHOU
    mensagem.erro_codigo = codigo
    if conversa is not None and canais.e_instagram(conversa):
        mensagem.erro_motivo = canais.motivo(exc, extras or {})
    else:
        mensagem.erro_motivo = K.motivo_do_erro(codigo)
    logger.info("[whatsapp] envio %s falhou: %s", mensagem.id, exc)


def _despachar(
    mensagem: ConversaMensagem, conversa: Conversa, corpo: dict[str, Any], cfg: CfgWhatsapp
) -> None:
    """WhatsApp: manda o corpo pronto à Meta e conclui."""
    _concluir(
        mensagem, conversa, lambda: wc.enviar(cfg.conexao, {**_destino(conversa), **corpo})["id"]
    )


def _concluir(
    mensagem: ConversaMensagem,
    conversa: Conversa,
    chamar: Callable[[], str],
    extras: dict[str, str] | None = None,
) -> None:
    """Chama a Meta (sem trava de linha) e grava o id dela ou o motivo da falha.

    Só o envio ACEITO conta como resposta da equipe (feature 328): atribui a conversa da fila ao
    autor e encerra a espera. O que falhou não faz nem um nem outro. Vale para os dois canais.
    """
    try:
        externo_id = chamar()
    except wc.WhatsappErro as exc:
        _registrar_falha(mensagem, exc, conversa, extras)
    else:
        mensagem.externo_id = externo_id
        mensagem.situacao = K.SITUACAO_ENVIADA
    mensagem.momento = agora_utc()
    if mensagem.situacao == K.SITUACAO_ENVIADA and mensagem.autor_id is not None:
        equipe_ops.resposta_da_equipe(conversa, mensagem.autor_id, mensagem.momento)
    atualizar_previa(conversa, mensagem.tipo, mensagem.texto, mensagem.momento)
    db.session.commit()


# ── Texto ────────────────────────────────────────────────────────────────────────────────────────


def enviar_texto(
    conversa_id: int, texto: str | None, chave: str | None, autor_id: int | None, cfg: CfgWhatsapp
) -> Envio:
    """Texto livre, dentro da janela (FR-010; no Instagram, a janela é a da 330)."""
    chave = _validar_chave(chave)
    if existente := _ja_enviada(chave):
        return Envio(existente, nova=False)
    texto = (texto or "").strip()
    if not texto:
        raise _campo("texto", "Informe a mensagem.")
    if len(texto) > K.TEXTO_MAXIMO:
        raise _campo("texto", f"A mensagem passa de {K.TEXTO_MAXIMO} caracteres.")
    conversa = conversa_ou_404(conversa_id)
    extras = _pre_condicoes(cfg, conversa, exige_janela=True)
    if canais.e_instagram(conversa):
        canais.validar_texto(texto)
    envio = _reservar(conversa, chave, K.TIPO_TEXTO, texto, autor_id)
    if not envio.nova:
        return envio
    if canais.e_instagram(conversa):
        chamar = lambda: canais.enviar_texto(conversa, texto, extras)  # noqa: E731
        _concluir(envio.mensagem, conversa, chamar, extras)
    else:
        corpo = {"type": "text", "text": {"body": texto, "preview_url": True}}
        _despachar(envio.mensagem, conversa, corpo, cfg)
    return envio


# ── Arquivo ──────────────────────────────────────────────────────────────────────────────────────


def mime_normalizado(mime: str | None) -> str:
    """O MIME sem parâmetros, em minúsculas, com os apelidos do navegador trocados pelo da Meta."""
    limpo = (mime or "").split(";")[0].strip().lower()
    return K.APELIDOS_DE_MIME.get(limpo, limpo)


def _tipo_do_arquivo(mime: str, tamanho: int) -> str:
    tipo = K.MIME_DE_ENVIO.get(mime)
    if tipo is None:
        raise _campo(
            "arquivo",
            "Tipo de arquivo não aceito pelo WhatsApp. Envie foto, áudio, vídeo, PDF ou Office.",
        )
    if tamanho > K.TETO_DE_ENVIO[tipo]:
        limite = K.TETO_DE_ENVIO[tipo] // (1024 * 1024)
        raise _campo("arquivo", f"Arquivo acima de {limite} MB para este tipo.")
    if tamanho == 0:
        raise _campo("arquivo", "O arquivo está vazio.")
    return tipo


def enviar_arquivo(
    conversa_id: int,
    dados: bytes,
    nome: str,
    mime: str | None,
    legenda: str | None,
    chave: str | None,
    autor_id: int | None,
    cfg: CfgWhatsapp,
) -> Envio:
    """Foto, áudio, vídeo ou documento, dentro da janela (FR-011). Guarda a cópia local antes."""
    chave = _validar_chave(chave)
    if existente := _ja_enviada(chave):
        return Envio(existente, nova=False)
    mime_limpo = mime_normalizado(mime)
    conversa = conversa_ou_404(conversa_id)
    if not _e_audio_gravado(conversa, mime_limpo):
        # Recusa cedo, antes da trava e da janela. A conversa vem antes porque o tipo aceito é do
        # canal dela (330); só muda o caso da conversa inexistente (404 em vez de 422).
        _tipo_do_canal(conversa, mime_limpo, len(dados))
    extras = _pre_condicoes(cfg, conversa, exige_janela=True)
    dados, nome, mime_limpo = _audio_do_navegador(dados, nome, mime_limpo, conversa)
    tipo = _tipo_do_canal(conversa, mime_limpo, len(dados))
    # O anexo do Instagram não tem legenda: a tela manda o texto à parte (feature 330).
    sem_legenda = canais.e_instagram(conversa)
    legenda = None if sem_legenda else (legenda or "").strip()[: K.TEXTO_MAXIMO] or None
    envio = _reservar(conversa, chave, tipo, legenda, autor_id)
    if envio.nova:
        midia = _guardar_copia_local(envio.mensagem, dados, nome, mime_limpo, cfg)
        if canais.e_instagram(conversa):
            chamar = lambda: canais.enviar_arquivo(conversa, midia, dados, tipo, extras)  # noqa: E731
            _concluir(envio.mensagem, conversa, chamar, extras)
        else:
            _subir_e_despachar(envio.mensagem, midia, conversa, dados, tipo, legenda, cfg)
    return envio


def _tipo_do_canal(conversa: Conversa, mime: str, tamanho: int) -> str:
    if canais.e_instagram(conversa):
        return canais.tipo_do_arquivo(mime, tamanho)
    return _tipo_do_arquivo(mime, tamanho)


def _e_audio_gravado(conversa: Conversa, mime: str) -> bool:
    """Áudio que o navegador gravou e o servidor converte antes de conferir o tipo."""
    if canais.e_instagram(conversa):
        return mime in K.AUDIO_GRAVADO_PARA_O_INSTAGRAM
    return mime == K.MIME_AUDIO_DO_NAVEGADOR


def _audio_do_navegador(
    dados: bytes, nome: str, mime: str, conversa: Conversa
) -> tuple[bytes, str, str]:
    """O áudio gravado no formato do canal (FR-013 da 328; FR-009 da 330); o resto passa.

    WhatsApp: o webm do Chrome vira ogg (só troca o recipiente, sai como nota de voz).
    Instagram: webm e ogg viram m4a (o Instagram não aceita os dois em áudio; recodifica).
    Roda depois das pré-condições: não se gasta ffmpeg num envio que a janela ou a trava recusam.
    """
    if not _e_audio_gravado(conversa, mime):
        return dados, nome, mime
    instagram = canais.e_instagram(conversa)
    converter = midia_ops.audio_para_m4a if instagram else midia_ops.webm_para_ogg
    try:
        convertido = converter(dados)
    except midia_ops.AudioIndisponivel as exc:
        logger.warning("[conversas] áudio gravado não convertido: %s", exc)
        raise _campo("arquivo", K.TEXTO_AUDIO_FALHOU) from exc
    base = (nome.rsplit(".", 1)[0] if "." in nome else nome) or "audio"
    if instagram:
        return convertido, f"{base}.m4a", K.MIME_AUDIO_DO_INSTAGRAM
    return convertido, f"{base}.ogg", K.MIME_NOTA_DE_VOZ


def _guardar_copia_local(
    mensagem: ConversaMensagem, dados: bytes, nome: str, mime: str, cfg: CfgWhatsapp
) -> ConversaMidia:
    """A cópia que a conversa exibe, guardada ANTES do upload (a falha da Meta não a perde)."""
    midia = ConversaMidia(
        mensagem_id=mensagem.id,
        mime=mime,
        tamanho=len(dados),
        nome_original=nome[:255],
        caminho=midia_ops.guardar_bytes(dados, mime, cfg),
        estado=K.MIDIA_GUARDADA,
    )
    db.session.add(midia)
    db.session.commit()
    return midia


def _e_opus(mime: str | None, dados: bytes) -> bool:
    """ogg com Opus dentro — o único áudio que a Meta entrega como nota de voz. O ogg/vorbis do
    clipe vai como áudio comum: o cabeçalho Opus ("OpusHead") está na primeira página do ogg."""
    return mime == K.MIME_NOTA_DE_VOZ and K.MARCA_OPUS in dados[: K.INICIO_DO_OGG]


def _subir_e_despachar(
    mensagem: ConversaMensagem,
    midia: ConversaMidia,
    conversa: Conversa,
    dados: bytes,
    tipo: str,
    legenda: str | None,
    cfg: CfgWhatsapp,
) -> None:
    """Sobe o arquivo à Meta e manda a mensagem com o id dele."""
    try:
        midia.externo_id = wc.subir_midia(cfg.conexao, dados, midia.mime, midia.nome_original)
    except wc.WhatsappErro as exc:
        _registrar_falha(mensagem, exc)
        db.session.commit()
        return
    chave_meta = K.CHAVE_DA_META[tipo]
    bloco: dict[str, Any] = {"id": midia.externo_id}
    if legenda and tipo != K.TIPO_AUDIO:
        bloco["caption"] = legenda
    if tipo == K.TIPO_DOCUMENTO:
        bloco["filename"] = midia.nome_original
    if tipo == K.TIPO_AUDIO and _e_opus(midia.mime, dados):
        bloco["voice"] = True  # ogg/opus chega como nota de voz, não como arquivo (FR-014)
    _despachar(mensagem, conversa, {"type": chave_meta, chave_meta: bloco}, cfg)


# ── Modelos ──────────────────────────────────────────────────────────────────────────────────────

_CACHE_DE_MODELOS: dict[str, Any] = {"quando": 0.0, "modelos": None}


def _componente(modelo: dict[str, Any], tipo: str) -> dict[str, Any]:
    for componente in modelo.get("components") or []:
        if isinstance(componente, dict) and (componente.get("type") or "").upper() == tipo:
            return componente
    return {}


def _suportado(modelo: dict[str, Any]) -> bool:
    """Nesta fase só os modelos cujas variáveis estão todas no corpo (sem cabeçalho com arquivo)."""
    cabecalho = _componente(modelo, "HEADER")
    if (cabecalho.get("format") or "").upper() in FORMATOS_DE_CABECALHO_COM_ARQUIVO:
        return False
    if VARIAVEL.search(cabecalho.get("text") or ""):
        return False
    botoes = _componente(modelo, "BUTTONS").get("buttons") or []
    return not any(VARIAVEL.search(str(b.get("url") or "")) for b in botoes if isinstance(b, dict))


def _variaveis(texto: str) -> list[str]:
    vistas: list[str] = []
    for nome in VARIAVEL.findall(texto):
        if nome not in vistas:
            vistas.append(nome)
    return vistas


def serializar_modelo(modelo: dict[str, Any]) -> dict[str, Any]:
    """Um modelo como a tela precisa: nome, idioma, texto do corpo e as variáveis em ordem."""
    texto = _componente(modelo, "BODY").get("text") or ""
    idioma = modelo.get("language")
    return {
        "nome": modelo.get("name"),
        "idioma": idioma.get("code") if isinstance(idioma, dict) else idioma,
        "categoria": modelo.get("category"),
        "texto": texto,
        "variaveis": len(_variaveis(texto)),
        "nomes_das_variaveis": _variaveis(texto),
        "nomeadas": (modelo.get("parameter_format") or "").upper() == "NAMED",
    }


def modelos_aprovados(cfg: CfgWhatsapp, *, forcar: bool = False) -> list[dict[str, Any]]:
    """Modelos aprovados e suportados, com cache de 5 min por processo."""
    import time

    if not cfg.ligado:
        raise EnvioRecusado("nao_configurado", TEXTO_NAO_CONFIGURADO, 503)
    agora = time.monotonic()
    cache = _CACHE_DE_MODELOS
    if forcar or cache["modelos"] is None or agora - cache["quando"] > K.MODELOS_CACHE_S:
        crus = wc.listar_modelos(cfg.conexao)
        cache["modelos"] = [
            serializar_modelo(m)
            for m in crus
            if (m.get("status") or "").upper() == "APPROVED" and _suportado(m)
        ]
        cache["quando"] = agora
    return cache["modelos"]


def _texto_final(modelo: dict[str, Any], valores: list[str]) -> str:
    mapa = dict(zip(modelo["nomes_das_variaveis"], valores, strict=True))
    return VARIAVEL.sub(lambda achado: mapa.get(achado.group(1), achado.group(0)), modelo["texto"])


def _corpo_do_modelo(modelo: dict[str, Any], valores: list[str]) -> dict[str, Any]:
    parametros = []
    for nome, valor in zip(modelo["nomes_das_variaveis"], valores, strict=True):
        parametro = {"type": "text", "text": valor}
        if modelo["nomeadas"]:
            parametro["parameter_name"] = nome
        parametros.append(parametro)
    componentes = [{"type": "body", "parameters": parametros}] if parametros else []
    return {
        "type": "template",
        "template": {
            "name": modelo["nome"],
            "language": {"code": modelo["idioma"]},
            "components": componentes,
        },
    }


def _modelo_escolhido(cfg: CfgWhatsapp, nome: str | None, idioma: str | None) -> dict[str, Any]:
    for modelo in modelos_aprovados(cfg):
        if modelo["nome"] == nome and (not idioma or modelo["idioma"] == idioma):
            return modelo
    raise _campo("nome", "Selecione um modelo aprovado.")


def texto_das_variaveis(quantidade: int) -> str:
    """ "Preencha a variável do modelo." / "Preencha as 2 variáveis do modelo." (XV: contagem)."""
    if quantidade == 1:
        return "Preencha a variável do modelo."
    return f"Preencha as {quantidade} variáveis do modelo."


def _valores_do_modelo(modelo: dict[str, Any], variaveis: list[Any] | None) -> list[str]:
    valores = [str(v or "").strip() for v in (variaveis or [])]
    if len(valores) != modelo["variaveis"] or not all(valores):
        raise _campo("variaveis", texto_das_variaveis(modelo["variaveis"]))
    return valores


def enviar_modelo(
    conversa_id: int,
    nome: str | None,
    idioma: str | None,
    variaveis: list[Any] | None,
    chave: str | None,
    autor_id: int | None,
    cfg: CfgWhatsapp,
) -> Envio:
    """Modelo aprovado, com as variáveis preenchidas; vale com a janela fechada (FR-012)."""
    chave = _validar_chave(chave)
    if existente := _ja_enviada(chave):
        return Envio(existente, nova=False)
    conversa = conversa_ou_404(conversa_id)
    if canais.e_instagram(conversa):
        raise EnvioRecusado("sem_modelos", K.TEXTO_IG_SEM_MODELOS, 409)
    _pre_condicoes(cfg, conversa, exige_janela=False)
    modelo = _modelo_escolhido(cfg, nome, idioma)
    valores = _valores_do_modelo(modelo, variaveis)
    envio = _reservar(
        conversa, chave, K.TIPO_MODELO, _texto_final(modelo, valores), autor_id, modelo["nome"]
    )
    if envio.nova:
        _despachar(envio.mensagem, conversa, _corpo_do_modelo(modelo, valores), cfg)
    return envio


# ── Marcar como lida ─────────────────────────────────────────────────────────────────────────────


def marcar_lida(conversa_id: int, cfg: CfgWhatsapp) -> None:
    """Zera as não lidas da equipe e, se puder falar com a Meta, dá o tique azul na última."""
    conversa = conversa_ou_404(conversa_id)
    conversa.nao_lidas = 0
    db.session.commit()
    # Instagram (330): sem "marcar como visto" nesta fase — só a contagem da equipe.
    if canais.e_instagram(conversa) or not cfg.ligado or cfg.travado:
        return
    ultima = (
        ConversaMensagem.query.filter(
            ConversaMensagem.conversa_id == conversa.id,
            ConversaMensagem.direcao == K.RECEBIDA,
            ConversaMensagem.externo_id.isnot(None),
        )
        .order_by(ConversaMensagem.momento.desc(), ConversaMensagem.id.desc())
        .first()
    )
    if ultima is None:
        return
    try:
        wc.marcar_lida(cfg.conexao, ultima.externo_id)
    except wc.WhatsappErro as exc:
        logger.info("[whatsapp] marcar como lida falhou (melhor esforço): %s", exc)
