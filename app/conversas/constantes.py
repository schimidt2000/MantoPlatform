"""Constantes do domínio Conversas (feature 325).

Valores de enum gravados no banco e devolvidos na API: não traduzir nem renomear (Princípio XV,
"o que nenhum ajuste de texto toca"). Os textos para a equipe ficam nos dicionários ``TEXTO_*`` e
``MOTIVO_DO_ERRO``.
"""

from datetime import timedelta

# Canais. A Fase 2 acrescenta o Instagram sem migration: a coluna já existe.
CANAL_WHATSAPP = "whatsapp"
CANAL_INSTAGRAM = "instagram"

# Direção da mensagem.
RECEBIDA = "recebida"
ENVIADA = "enviada"

# Tipos de mensagem (coluna `tipo`).
TIPO_TEXTO = "texto"
TIPO_IMAGEM = "imagem"
TIPO_AUDIO = "audio"
TIPO_VIDEO = "video"
TIPO_DOCUMENTO = "documento"
TIPO_FIGURINHA = "figurinha"
TIPO_LOCALIZACAO = "localizacao"
TIPO_CONTATO = "contato"
TIPO_REACAO = "reacao"
TIPO_INTERATIVA = "interativa"
TIPO_MODELO = "modelo"
TIPO_OUTRO = "outro"

# Tipo da Meta → tipo da casa.
TIPO_DA_META = {
    "text": TIPO_TEXTO,
    "image": TIPO_IMAGEM,
    "audio": TIPO_AUDIO,
    "video": TIPO_VIDEO,
    "document": TIPO_DOCUMENTO,
    "sticker": TIPO_FIGURINHA,
    "location": TIPO_LOCALIZACAO,
    "contacts": TIPO_CONTATO,
    "reaction": TIPO_REACAO,
    "interactive": TIPO_INTERATIVA,
    "button": TIPO_INTERATIVA,
}
TIPOS_COM_MIDIA = {TIPO_IMAGEM, TIPO_AUDIO, TIPO_VIDEO, TIPO_DOCUMENTO, TIPO_FIGURINHA}

# Situação da mensagem. A recebida fica sempre `recebida`; a enviada só avança (FR-009).
SITUACAO_RECEBIDA = "recebida"
SITUACAO_PENDENTE = "pendente"
SITUACAO_ENVIADA = "enviada"
SITUACAO_ENTREGUE = "entregue"
SITUACAO_LIDA = "lida"
SITUACAO_FALHOU = "falhou"
ORDEM_DA_SITUACAO = {
    SITUACAO_PENDENTE: 0,
    SITUACAO_ENVIADA: 1,
    SITUACAO_ENTREGUE: 2,
    SITUACAO_LIDA: 3,
}
# `played` = nota de voz ouvida: para a equipe, é "lida" (research §Confirmações).
SITUACAO_DO_STATUS = {
    "sent": SITUACAO_ENVIADA,
    "delivered": SITUACAO_ENTREGUE,
    "read": SITUACAO_LIDA,
    "played": SITUACAO_LIDA,
    "failed": SITUACAO_FALHOU,
}

# Origem da mensagem.
ORIGEM_CONTATO = "contato"
ORIGEM_PLATAFORMA = "plataforma"
ORIGEM_CELULAR = "celular"
ORIGEM_OUTRO = "outro"

# Estado do aviso cru (`whatsapp_avisos.estado`).
AVISO_PENDENTE = "pendente"
AVISO_PROCESSANDO = "processando"
AVISO_PROCESSADO = "processado"
AVISO_DESCARTADO = "descartado"

# Estado da mídia (`conversa_midias.estado`).
MIDIA_PENDENTE = "pendente"
MIDIA_GUARDADA = "guardada"
MIDIA_FALHOU = "falhou"

# Tetos.
AVISO_CORPO_MAXIMO = 256 * 1024
MIDIA_TETO_BYTES = 25 * 1024 * 1024
TEXTO_MAXIMO = 4096
PREVIA_MAXIMA = 200
ERRO_MAXIMO = 500
CHAVE_ENVIO_MINIMA = 8
CHAVE_ENVIO_MAXIMA = 64

# Janela de atendimento da Meta: só a mensagem da cliente reabre (research R9).
JANELA = timedelta(hours=24)

# Varredura (research R3/R5).
VARREDURA_INTERVALO_S = 60
VARREDURA_ESPERA = timedelta(seconds=30)
PROCESSANDO_PRESO = timedelta(minutes=10)
AVISO_IDADE_MAXIMA = timedelta(hours=48)
TENTATIVAS_MAXIMAS = 10
VARREDURA_LOTE = 50

# Cache da lista de modelos aprovados, por processo.
MODELOS_CACHE_S = 300

# Página da lista e da conversa.
PAGINA_CONVERSAS = 50
PAGINA_MENSAGENS = 50

# Envio de arquivo: MIME aceito pela Meta → tipo da casa (research §Confirmações).
MIME_DE_ENVIO = {
    "image/jpeg": TIPO_IMAGEM,
    "image/png": TIPO_IMAGEM,
    "audio/aac": TIPO_AUDIO,
    "audio/amr": TIPO_AUDIO,
    "audio/mpeg": TIPO_AUDIO,
    "audio/mp4": TIPO_AUDIO,
    "audio/ogg": TIPO_AUDIO,
    "video/mp4": TIPO_VIDEO,
    "video/3gpp": TIPO_VIDEO,
    "application/pdf": TIPO_DOCUMENTO,
    "text/plain": TIPO_DOCUMENTO,
    "application/msword": TIPO_DOCUMENTO,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": TIPO_DOCUMENTO,
    "application/vnd.ms-excel": TIPO_DOCUMENTO,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": TIPO_DOCUMENTO,
    "application/vnd.ms-powerpoint": TIPO_DOCUMENTO,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": TIPO_DOCUMENTO,
}
# O navegador manda nomes que a Meta não reconhece para o mesmo formato (o m4a do iPhone, o mp3 do
# Windows): normalizados antes de validar e de subir.
APELIDOS_DE_MIME = {
    "audio/x-m4a": "audio/mp4",
    "audio/m4a": "audio/mp4",
    "audio/mp3": "audio/mpeg",
    "audio/x-mpeg": "audio/mpeg",
    "audio/opus": "audio/ogg",
    "audio/x-aac": "audio/aac",
    "image/jpg": "image/jpeg",
    "image/pjpeg": "image/jpeg",
}
# Teto da Meta por tipo de envio (bytes).
TETO_DE_ENVIO = {
    TIPO_IMAGEM: 5 * 1024 * 1024,
    TIPO_AUDIO: 16 * 1024 * 1024,
    TIPO_VIDEO: 16 * 1024 * 1024,
    TIPO_DOCUMENTO: MIDIA_TETO_BYTES,
}
# Tipo da casa → chave do bloco no payload da Meta.
CHAVE_DA_META = {
    TIPO_IMAGEM: "image",
    TIPO_AUDIO: "audio",
    TIPO_VIDEO: "video",
    TIPO_DOCUMENTO: "document",
}

# Extensão do arquivo guardado, pelo MIME (o resto vira `.bin`).
EXTENSAO_DO_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "audio/aac": ".aac",
    "audio/amr": ".amr",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/ogg": ".ogg",
    "video/mp4": ".mp4",
    "video/3gpp": ".3gp",
    "application/pdf": ".pdf",
    "text/plain": ".txt",
}

# Texto curto do que esta fase não exibe (Princípio XV, superfície interna).
TEXTO_DO_TIPO = {
    TIPO_LOCALIZACAO: "Localização enviada. Abra no celular para ver.",
    TIPO_CONTATO: "Contato compartilhado. Abra no celular para ver.",
    TIPO_INTERATIVA: "Resposta de botão ou lista.",
    TIPO_OUTRO: "Mensagem de um tipo que a Plataforma ainda não exibe. Abra no celular para ver.",
}
TEXTO_APAGADA_NO_CELULAR = "Mensagem apagada pelo celular."
TEXTO_EDITADA_NO_CELULAR = "Mensagem editada pelo celular."
TEXTO_REACAO_REMOVIDA = "Reação removida."

# Rótulo da prévia na lista, por tipo.
PREVIA_DO_TIPO = {
    TIPO_IMAGEM: "Foto",
    TIPO_AUDIO: "Áudio",
    TIPO_VIDEO: "Vídeo",
    TIPO_DOCUMENTO: "Documento",
    TIPO_FIGURINHA: "Figurinha",
    TIPO_LOCALIZACAO: "Localização",
    TIPO_CONTATO: "Contato",
    TIPO_REACAO: "Reação",
    TIPO_INTERATIVA: "Resposta",
    TIPO_MODELO: "Modelo",
    TIPO_OUTRO: "Mensagem",
}

# Código de erro da Meta → motivo para a equipe (research R10 + §Confirmações).
MOTIVO_DO_ERRO = {
    131047: "A janela de 24 horas fechou. Envie um modelo aprovado.",
    131026: "O número não tem WhatsApp ou não pode receber mensagens agora.",
    131051: "Este tipo de mensagem não é aceito pelo WhatsApp.",
    130429: "Limite de envio da Meta atingido. Aguarde alguns minutos e tente novamente.",
    131056: "Mensagens demais para este contato em pouco tempo. Aguarde e tente novamente.",
    131049: "A Meta segurou a mensagem para proteger a qualidade do número.",
    131050: "O contato pediu para não receber mensagens de marketing.",
    131048: "A Meta restringiu envios por suspeita de spam.",
    131052: "Não foi possível baixar a mídia do contato.",
    131053: "Não foi possível enviar o arquivo à Meta.",
    131000: "Erro desconhecido na Meta. Tente novamente.",
    131008: "Falta um dado obrigatório na mensagem.",
    131009: "Um dado da mensagem é inválido.",
    131005: "O token do WhatsApp não tem permissão. Avise o Superadmin.",
    10: "O token do WhatsApp não tem permissão. Avise o Superadmin.",
    190: "O token do WhatsApp venceu. Avise o Superadmin.",
    200: "O token do WhatsApp não foi informado. Avise o Superadmin.",
    100: "A Meta recusou um dado da mensagem.",
    4: "Limite de chamadas da Meta atingido. Aguarde e tente novamente.",
    80007: "Limite de chamadas da conta atingido. Aguarde e tente novamente.",
    368: "A conta do WhatsApp está restrita. Avise o Superadmin.",
    131031: "A conta do WhatsApp está bloqueada. Avise o Superadmin.",
    131042: "Há um problema de pagamento na conta da Meta. Avise o Superadmin.",
    133010: "O número da Manto não está registrado na Meta. Avise o Superadmin.",
    132000: "O número de variáveis não confere com o modelo.",
    132001: "Este modelo não existe nesse idioma ou não foi aprovado.",
    132012: "Uma variável do modelo está em formato inválido.",
    132015: "Este modelo está pausado pela Meta.",
    132016: "Este modelo foi desativado pela Meta.",
    132018: "Uma variável do modelo foi recusada pela Meta.",
}
MOTIVO_GENERICO = "A Meta recusou a mensagem (código {codigo})."
MOTIVO_INDISPONIVEL = "Não foi possível enviar. Tente novamente."
MOTIVO_ARQUIVO_GRANDE = "Arquivo acima de 25 MB. Abra no celular."
MOTIVO_MIDIA_INDISPONIVEL = "Arquivo indisponível. Abra no celular."


def motivo_do_erro(codigo: int | None) -> str:
    """O motivo em pt-BR de um código de erro da Meta (os não mapeados citam o código)."""
    if codigo is None:
        return MOTIVO_INDISPONIVEL
    return MOTIVO_DO_ERRO.get(codigo) or MOTIVO_GENERICO.format(codigo=codigo)
