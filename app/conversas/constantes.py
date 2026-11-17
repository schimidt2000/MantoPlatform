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


# ── Equipe na caixa (feature 328) ────────────────────────────────────────────────────────────────

# A cliente que espera mais que isto, dentro do horário, vira aviso no sino (FR-007).
ESPERA_PARA_ALERTA = timedelta(minutes=15)
# Hora de São Paulo, intervalo [9, 21): fora dele o alerta não toca, e de manhã sai o que ficou.
HORARIO_DE_ALERTA = (9, 21)

FILTRO_TODAS = "todas"
FILTRO_MINHAS = "minhas"
FILTRO_SEM_RESPONSAVEL = "sem_responsavel"
FILTROS_DA_LISTA = (FILTRO_TODAS, FILTRO_MINHAS, FILTRO_SEM_RESPONSAVEL)

ACAO_ASSUMIR = "assumir"
ACAO_TRANSFERIR = "transferir"
ACAO_DEVOLVER = "devolver"
ACOES_DO_RESPONSAVEL = (ACAO_ASSUMIR, ACAO_TRANSFERIR, ACAO_DEVOLVER)

NOTA_MAXIMA = 2000
NOTAS_NO_DETALHE = 200
RESPOSTA_TITULO_MAXIMO = 80
RESPOSTA_ATALHO_MAXIMO = 30
RESPOSTA_TEXTO_MAXIMO = TEXTO_MAXIMO
# O Chrome e o Edge gravam webm, que o WhatsApp não aceita: só entra pela conversão para ogg (R7).
MIME_AUDIO_DO_NAVEGADOR = "audio/webm"
# ogg/opus é o único formato que a Meta entrega como nota de voz (`voice: true`).
MIME_NOTA_DE_VOZ = "audio/ogg"
# O cabeçalho do Opus num ogg mora na primeira página (os primeiros bytes do arquivo).
MARCA_OPUS = b"OpusHead"
INICIO_DO_OGG = 128
# Remux webm → ogg de 5 min de áudio leva milissegundos; 60 s só protege de um ffmpeg travado.
CONVERSAO_DE_AUDIO_SEGUNDOS = 60

# Textos para a equipe (Princípio XV, superfície interna).
TEXTO_CONVERSA_NAO_ENCONTRADA = "Conversa não encontrada."
TEXTO_JA_ASSUMIDA = "Esta conversa já foi assumida por {nome}."
# Quem assumiu e já não existe (usuário apagado no meio da corrida).
TEXTO_OUTRA_PESSOA = "outra pessoa"
TEXTO_ALTERADA = "Outra pessoa alterou o responsável agora. Confira e tente novamente."
TEXTO_DESTINO_INVALIDO = "Selecione uma pessoa da equipe."
TEXTO_ACAO_INVALIDA = "Ação desconhecida."
TEXTO_FILTRO_INVALIDO = "Filtro desconhecido."
TEXTO_NOTA_VAZIA = "Informe a nota."
TEXTO_NOTA_LONGA = f"A nota passa de {NOTA_MAXIMA} caracteres."
TEXTO_TITULO_VAZIO = "Informe o título."
TEXTO_TITULO_LONGO = f"O título passa de {RESPOSTA_TITULO_MAXIMO} caracteres."
TEXTO_TITULO_REPETIDO = "Já existe uma resposta com este título."
TEXTO_ATALHO_COM_ESPACO = "O atalho não pode ter espaço."
TEXTO_ATALHO_LONGO = f"O atalho passa de {RESPOSTA_ATALHO_MAXIMO} caracteres."
TEXTO_ATALHO_REPETIDO = "Já existe uma resposta com este atalho."
TEXTO_RESPOSTA_VAZIA = "Informe o texto."
TEXTO_RESPOSTA_LONGA = f"O texto passa de {RESPOSTA_TEXTO_MAXIMO} caracteres."
TEXTO_RESPOSTA_NAO_ENCONTRADA = "Resposta rápida não encontrada."
TEXTO_AUDIO_FALHOU = "Não foi possível preparar o áudio. Envie o arquivo pelo clipe."

# Avisos do sino.
TITULO_ESPERANDO = "{nome} espera resposta há {tempo}."
TITULO_TRANSFERIDA = "{quem} transferiu a conversa com {nome} para você."


# O ``object`` do aviso cru do Instagram (o do WhatsApp é "whatsapp_business_account").
OBJETO_INSTAGRAM = "instagram"
CANAIS = (CANAL_WHATSAPP, CANAL_INSTAGRAM)
# Assinatura dos bytes → MIME, para a mídia do Instagram (o aviso não diz o tipo exato).
ASSINATURAS_DE_ARQUIVO = (
    (b"\x89PNG", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF8", "image/gif"),
    (b"%PDF", "application/pdf"),
    (b"OggS", "audio/ogg"),
    (b"ftypM4A", "audio/mp4"),
    (b"ftyp", "video/mp4"),
)
TEXTO_CANAL_INVALIDO = "Canal desconhecido."

# ── Instagram Direct (feature 330) ───────────────────────────────────────────────────────────────

# Anexo do Instagram → tipo da casa. Os demais viram texto pronto (`TEXTO_DO_ANEXO_IG`).
TIPO_DO_ANEXO_IG = {
    "image": TIPO_IMAGEM,
    "video": TIPO_VIDEO,
    "audio": TIPO_AUDIO,
    "file": TIPO_DOCUMENTO,
}
TEXTO_DO_ANEXO_IG = {
    "share": "Compartilhou uma publicação.",
    "ig_reel": "Compartilhou um reels.",
    "reel": "Compartilhou um reels.",
    "story_mention": "Mencionou a Manto no story.",
    "ephemeral": "Mídia temporária. Abra no Instagram para ver.",
}
TEXTO_RESPOSTA_AO_STORY = "Respondeu ao seu story."
TEXTO_APAGADA_PELA_CLIENTE = "Mensagem apagada pela cliente."
TEXTO_NAO_SUPORTADA_IG = (
    "Mensagem de um tipo que a Plataforma ainda não exibe. Abra no Instagram para ver."
)
TEXTO_CONTATO_DO_INSTAGRAM = "Contato do Instagram"

# Envio (doc. da Meta, 03/11/2026): tipo da casa → chave do anexo e tetos.
MIME_DE_ENVIO_IG = {
    "image/png": TIPO_IMAGEM,
    "image/jpeg": TIPO_IMAGEM,
    "image/gif": TIPO_IMAGEM,
    "video/mp4": TIPO_VIDEO,
    "video/ogg": TIPO_VIDEO,
    "video/x-msvideo": TIPO_VIDEO,
    "video/quicktime": TIPO_VIDEO,
    "video/webm": TIPO_VIDEO,
    "audio/aac": TIPO_AUDIO,
    "audio/mp4": TIPO_AUDIO,
    "audio/wav": TIPO_AUDIO,
    "audio/x-wav": TIPO_AUDIO,
    "application/pdf": TIPO_DOCUMENTO,
}
CHAVE_DO_ANEXO_IG = {
    TIPO_IMAGEM: "image",
    TIPO_VIDEO: "video",
    TIPO_AUDIO: "audio",
    TIPO_DOCUMENTO: "file",
}
TETO_DE_ENVIO_IG = {
    TIPO_IMAGEM: 8 * 1024 * 1024,
    TIPO_VIDEO: 25 * 1024 * 1024,
    TIPO_AUDIO: 25 * 1024 * 1024,
    TIPO_DOCUMENTO: 25 * 1024 * 1024,
}
# O limite do Instagram é em BYTES de UTF-8, não em caracteres.
TEXTO_MAXIMO_IG_BYTES = 1000
# Até 7 dias depois da última mensagem da cliente, a resposta humana sai com a marca HUMAN_AGENT.
JANELA_HUMANA = timedelta(days=7)
# O perfil sem nome é buscado de novo, no máximo, uma vez por dia.
PERFIL_INTERVALO = timedelta(hours=24)
MIME_AUDIO_DO_INSTAGRAM = "audio/mp4"
# O que o navegador grava e o Instagram não aceita em áudio: vira m4a no servidor.
AUDIO_GRAVADO_PARA_O_INSTAGRAM = ("audio/webm", "audio/ogg")
TEXTO_IG_TRAVADO = "O envio pelo Instagram está travado neste ambiente."

JANELA_ESTADO_ABERTA = "aberta"
JANELA_ESTADO_HUMANA = "humana"
JANELA_ESTADO_FECHADA = "fechada"

TEXTO_IG_NAO_CONFIGURADO = "O Instagram ainda não foi configurado."
TEXTO_IG_JANELA_FECHADA = (
    "Passaram 7 dias desde a última mensagem da cliente. Só ela pode retomar a conversa pelo Instagram."
)
TEXTO_IG_SEM_MODELOS = (
    "O Instagram não tem modelos. Responda dentro de 7 dias da última mensagem da cliente."
)
TEXTO_IG_TIPO_NAO_ACEITO = "Tipo de arquivo não aceito pelo Instagram. Envie foto, vídeo, áudio ou PDF."
TEXTO_IG_TEXTO_LONGO = "A mensagem passa do limite do Instagram. Encurte o texto (acentos e emojis contam mais)."
TEXTO_POSTBACK = 'Tocou em "{titulo}".'
# Feature 350: sem aceite de novidades, modelo de marketing não sai (a categoria vem da Meta).
CATEGORIA_MARKETING = "MARKETING"
TEXTO_SEM_ACEITE = (
    "Esta cliente não autorizou receber novidades. "
    "Registre o aceite na ficha antes de enviar um modelo de marketing."
)
# Anexos que trazem um link para abrir no Instagram (o efêmero não traz).
ANEXOS_COM_LINK_IG = ("share", "ig_reel", "reel", "story_mention")
# Motivos da recusa no Instagram (feature 330): pelo subcódigo, depois pelo código da Graph API.
MOTIVO_DO_SUBCODIGO_IG = {
    2018278: "A janela do Instagram fechou. Só a cliente pode retomar a conversa.",
    2018001: "Esta pessoa não foi encontrada no Instagram.",
}
MOTIVO_DO_ERRO_IG = {
    190: "O token do Instagram venceu. Avise o Superadmin.",
    200: "O token do Instagram não tem permissão. Avise o Superadmin.",
    10: "O token do Instagram não tem permissão. Avise o Superadmin.",
    551: "Esta pessoa não pode receber mensagens agora.",
    4: "Limite de chamadas da Meta atingido. Aguarde e tente novamente.",
    613: "Limite de chamadas da Meta atingido. Aguarde e tente novamente.",
}
MOTIVO_IG_MARCA_HUMANA = "A Meta ainda não liberou a resposta depois de 24 horas no Instagram."
MOTIVO_IG_ROTEAMENTO = (
    "A conversa está com outro app no Instagram (Kommo). Responda por ele até a virada."
)
# Recusas de permissão da Graph API: com a marca HUMAN_AGENT enviada, querem dizer "marca não liberada".
CODIGOS_DE_PERMISSAO = (10, 200)
# Subcódigos de "o app não tem o controle da conversa" (roteamento). A confirmar na conta de teste
# (quickstart §3); o motivo genérico com o código cobre o que não estiver aqui.
SUBCODIGOS_DE_ROTEAMENTO = (2018300, 2534037)

# ── Orçamento e formulário pela conversa (feature 333) ──────────────────────────────────────────
# A ficha criada pela conversa (`Client.source`); `client_ops.client_metrics` tem o balde dela.
ORIGEM_DA_FICHA = "conversa"
TEXTO_ORCAMENTO_NAO_ENCONTRADO = "Orçamento não encontrado."
TEXTO_ORCAMENTO_SEM_MENSAGEM = (
    "Este orçamento não tem a mensagem pronta. Use Recalcular e envie o novo orçamento."
)
TEXTO_ESCOLHA_A_FICHA = "Selecione a ficha da cliente ou informe nome e telefone."
TEXTO_FICHA_NAO_ENCONTRADA = "Ficha não encontrada. Selecione outra ou informe nome e telefone."
TEXTO_FICHA_JA_EXISTIA = "Esta ficha já existia e foi ligada à conversa."
MIME_PDF = "application/pdf"
# As partes do envio usam a chave do pedido com um sufixo (`:1`, `:2`, …, `:pdf`), dentro do teto.
SUFIXO_DO_PDF = ":pdf"
CHAVE_BASE_MAXIMA = CHAVE_ENVIO_MAXIMA - 8
# Os formulários públicos: o link curto `/f/<slug>` é o canônico (`frontend/server.js`).
FORMULARIOS_PUBLICOS = (
    ("comum", "Pré-contrato", "pre-contrato"),
    ("corporativo", "Corporativo", "corporativo"),
)
TEXTO_DO_FORMULARIO = "Oi, {nome}! Para reservarmos a data, preencha o formulário: {link}"
TEXTO_DO_FORMULARIO_SEM_NOME = "Oi! Para reservarmos a data, preencha o formulário: {link}"

# ── De qual anúncio veio cada cliente (feature 334) ─────────────────────────────────────────────
# O tipo do contato: só `anuncio` é consultado na Meta e vira origem; `publicacao` (clique numa
# publicação do Facebook/Instagram, WhatsApp) e `outro` (demais origens do Instagram) ficam registrados.
CONTATO_ANUNCIO = "anuncio"
CONTATO_PUBLICACAO = "publicacao"
CONTATO_OUTRO = "outro"
# A origem na ficha (`Client.lead_origin`) e a atribuição que o Desempenho (feature 256) já lê:
# `utm_source=meta` vira "Meta Ads"; `utm_campaign` é o nome da campanha do primeiro anúncio.
ORIGEM_DO_ANUNCIO = {CANAL_WHATSAPP: "Anúncio do WhatsApp", CANAL_INSTAGRAM: "Anúncio do Instagram"}
ORIGEM_ORGANICA = {CANAL_WHATSAPP: "WhatsApp", CANAL_INSTAGRAM: "Instagram"}
UTM_SOURCE_DO_ANUNCIO = "meta"
UTM_MEDIUM_DO_ANUNCIO = "anuncio"
# A consulta da campanha: até 10 por vez; a falha (permissão, rede) volta depois de 24 h.
ANUNCIOS_POR_VEZ = 10
RECONSULTA_DO_ANUNCIO = timedelta(hours=24)

# ── Funil das conversas (feature 335) ───────────────────────────────────────────────────────────
# As etapas em ordem: cada conversa fica na mais avançada que alcançou, e cada etapa conta quem
# chegou nela ou além (o funil nunca cresce). As chaves vão na API; os rótulos, na tela.
ETAPAS_DO_FUNIL = ("chegou", "orcamento", "formulario", "evento", "pagou", "avaliou")
ROTULO_DA_ETAPA = {
    "chegou": "Chegou",
    "orcamento": "Orçamento enviado",
    "formulario": "Formulário",
    "evento": "Evento fechado",
    "pagou": "Pagou",
    "avaliou": "Avaliou",
}
DIVISOES_DO_FUNIL = ("vendedor", "campanha", "canal")
ROTULO_DO_CANAL = {CANAL_WHATSAPP: "WhatsApp", CANAL_INSTAGRAM: "Instagram"}
# Valores especiais do filtro e da divisão por campanha (o nome da campanha nunca começa com "__").
SEM_ANUNCIO = "__sem_anuncio__"
CAMPANHA_DESCONHECIDA = "__desconhecida__"
TEXTO_SEM_ANUNCIO = "Sem anúncio"
TEXTO_CAMPANHA_DESCONHECIDA = "Campanha desconhecida"
TEXTO_SEM_RESPONSAVEL = "Sem responsável"
PERIODO_MAXIMO_DO_FUNIL = 366  # dias
PARADOS_POR_VEZ = 200
TEXTO_PERIODO_INVALIDO = "Informe a data no formato AAAA-MM-DD."
TEXTO_PERIODO_INVERTIDO = "Escolha uma data inicial anterior à final."
TEXTO_PERIODO_LONGO = "Escolha um período de até um ano."
TEXTO_DIVISAO_INVALIDA = "Escolha dividir por vendedor, campanha ou canal."
TEXTO_ETAPA_INVALIDA = "Escolha uma das etapas do funil."

# ── Linha do tempo da ficha (feature 335) ───────────────────────────────────────────────────────
# Os títulos dos marcos (o do primeiro contato leva o canal) e a origem da ficha no marco de entrada.
MARCOS_POR_VEZ = 300
TITULO_DO_MARCO = {
    "entrada": "Entrou na base",
    "contato": "Primeiro contato pelo {canal}",
    "anuncio": "Veio do anúncio",
    "publicacao": "Veio da publicação",
    "orcamento": "Orçamento enviado",
    "formulario": "Formulário preenchido",
    "evento": "Evento fechado",
    "pagamento": "Pagamento registrado",
    "avaliacao": "Avaliação da cliente",
}
ORIGEM_DA_FICHA_LEGIVEL = {
    "kommo_import": "Veio do Kommo",
    "conversa": "Criada pela conversa",
    "manual": "Cadastrada à mão",
    "whatsform_import": "Veio do formulário",
}
