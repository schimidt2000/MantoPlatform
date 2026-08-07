"""Application-wide constants.

Centralises role name strings so they are defined once and imported
everywhere. Using the class attributes (e.g. ``RoleName.SUPERADMIN``)
means a typo becomes an ``AttributeError`` at import time instead of a
silent authorisation bypass at runtime.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

# Feature 094: a partir desta data, salvar os dados de venda de um evento exige um cliente associado.
# Eventos com início ANTERIOR a esta data são grandfathered (podem ficar sem cliente).
CLIENT_REQUIRED_FROM = date(2026, 6, 29)


def event_requires_client(event) -> bool:
    """True se o evento exige cliente para salvar a venda (feature 094).

    Baseia-se na data de início do evento: eventos a partir de ``CLIENT_REQUIRED_FROM`` exigem cliente;
    passados/antigos (ou sem data) são isentos (grandfathering).
    """
    start = getattr(event, "start_at", None)
    if start is None:
        return False
    return start.date() >= CLIENT_REQUIRED_FROM


# Feature 109: eventos cujo título começa com este prefixo (case-insensitive) são EducaManto —
# cobre "(EDU)" e "(EDUCAMANTO)". A comissão da venda vai ao responsável EducaManto configurado.
EDUCAMANTO_TITLE_PREFIX = "(EDU"


# Feature 099: tipos de acréscimo do orçamento/evento. "BV" é um repasse (não é lucro nem comissão);
# "Outro" permite descrição livre. A lista é um ponto de partida ajustável.
ACRESCIMO_TIPO_BV = "BV"
ACRESCIMO_TIPO_OUTRO = "Outro"
ACRESCIMO_TIPOS = [
    "Taxa de urgência",
    "Deslocamento/Logística",
    "Domingo/Feriado",
    "Hora extra",
    ACRESCIMO_TIPO_BV,
    ACRESCIMO_TIPO_OUTRO,
]

# Feature 100: tipos de relação de um cliente com o evento (lista fixa). Usada na associação
# múltipla evento↔cliente. "Contratante" é o padrão da migração do vínculo único anterior.
CLIENT_RELATION_TIPOS = [
    "Contratante",
    "Assessora",
    "Mãe/Pai",
    "Familiar",
    "Outros",
]


# Feature 200: tipo de evento que recebe Presente 3D. Só eventos SHOW entram na Fila de Impressão.
EVENT_TYPE_SHOW = "SHOW"

# Feature 200: ciclo de vida de um `Event3DGift`, na ordem em que o Artista 3D o percorre.
# 'entregue' é o estado final — some da Fila de Impressão.
GIFT_3D_STATUS_PENDENTE   = "pendente"
GIFT_3D_STATUS_IMPRIMINDO = "imprimindo"
GIFT_3D_STATUS_FINALIZADO = "finalizado"
GIFT_3D_STATUS_ENTREGUE   = "entregue"
GIFT_3D_STATUSES = [
    GIFT_3D_STATUS_PENDENTE,
    GIFT_3D_STATUS_IMPRIMINDO,
    GIFT_3D_STATUS_FINALIZADO,
    GIFT_3D_STATUS_ENTREGUE,
]


# Feature 225: ciclo de vida de um `FigurinoProducao`, na ordem em que a oficina o percorre.
# 'pronto' é o estado final feliz; 'cancelado' é a saída (pedido recusado na aprovação ou
# abandonado depois) — aprovação sem recusa possível não seria aprovação.
FIGURINO_PROD_SOLICITADO  = "solicitado"
FIGURINO_PROD_APROVADO    = "aprovado"
FIGURINO_PROD_EM_PRODUCAO = "em_producao"
FIGURINO_PROD_PRONTO      = "pronto"
FIGURINO_PROD_CANCELADO   = "cancelado"
FIGURINO_PROD_STATUSES = [
    FIGURINO_PROD_SOLICITADO,
    FIGURINO_PROD_APROVADO,
    FIGURINO_PROD_EM_PRODUCAO,
    FIGURINO_PROD_PRONTO,
    FIGURINO_PROD_CANCELADO,
]
#: Estados em que o pedido ainda dá trabalho a alguém — os que aparecem na fila e na home.
FIGURINO_PROD_ABERTOS = [
    FIGURINO_PROD_SOLICITADO,
    FIGURINO_PROD_APROVADO,
    FIGURINO_PROD_EM_PRODUCAO,
]
#: Rótulos em pt-BR. Fonte única: o React lê daqui via serialização, não redigita.
FIGURINO_PROD_LABELS = {
    FIGURINO_PROD_SOLICITADO:  "Solicitado",
    FIGURINO_PROD_APROVADO:    "Aprovado",
    FIGURINO_PROD_EM_PRODUCAO: "Em produção",
    FIGURINO_PROD_PRONTO:      "Pronto",
    FIGURINO_PROD_CANCELADO:   "Cancelado",
}
#: Tipos de anexo de um pedido de produção (feature 225).
FIGURINO_ANEXO_FOTO      = "foto"
FIGURINO_ANEXO_ORCAMENTO = "orcamento"
FIGURINO_ANEXO_KINDS = [FIGURINO_ANEXO_FOTO, FIGURINO_ANEXO_ORCAMENTO]

#: Chave que marca, no Google Agenda, um compromisso criado pela oficina de figurino
#: (`extendedProperties.private.manto_kind`). `sync_events` pula tudo que a carrega — sem isso
#: o prazo do figurino viraria um evento fantasma na plataforma.
GCAL_KIND_KEY = "manto_kind"
GCAL_KIND_FIGURINO_PRODUCAO = "figurino_producao"


# Feature 204: ciclo de vida de um `MarketingPost`, na ordem em que a equipe de marketing o
# percorre — é também a ordem das colunas do Kanban de `/marketing/painel`.
MARKETING_STATUS_IDEIA     = "ideia"
MARKETING_STATUS_PRODUCAO  = "producao"
MARKETING_STATUS_REVISAO   = "revisao"
MARKETING_STATUS_AGENDADO  = "agendado"
MARKETING_STATUS_PUBLICADO = "publicado"
MARKETING_STATUSES = [
    MARKETING_STATUS_IDEIA,
    MARKETING_STATUS_PRODUCAO,
    MARKETING_STATUS_REVISAO,
    MARKETING_STATUS_AGENDADO,
    MARKETING_STATUS_PUBLICADO,
]

# Feature 204: plataformas de publicação aceitas em `MarketingPost.platform`. Lista fixa e curta
# (7 itens, abaixo do limite de 10 do Princípio X.1 — `<select>` nativo é legítimo na tela).
MARKETING_PLATFORMS = [
    "Instagram",
    "TikTok",
    "YouTube",
    "Facebook",
    "Kwai",
    "LinkedIn",
    "Outro",
]

# Feature 204: intervalo máximo aceito numa meta de frequência (5 anos em dias) — evita meta
# absurda por dígito digitado errado.
MARKETING_MAX_INTERVAL_DAYS = 1825


# ── Loja de Interações Virtuais (feature 205) ───────────────────────────────

# Fuso do negócio. A Plataforma grava datas de agenda como **naive São Paulo** — convenção que
# `app/calendar/service.py:parse_event_datetime` estabelece ao converter tudo que vem do Google.
TZ_SP = ZoneInfo("America/Sao_Paulo")


def now_sp() -> datetime:
    """O "agora" do negócio: horário de São Paulo, sem fuso anexado.

    Toda a feature 205 usa **só** este relógio — horários de slot, soft lock, janela do anti-abuso
    e carimbos de criação. Misturar com ``datetime.utcnow()`` custaria 3 horas de erro: horários
    das próximas 3h sumiriam da lista, o contador do soft lock mostraria minutos a mais, e a janela
    do teto por origem contaria pedidos do intervalo errado.

    Por isso as tabelas ``virtual_*`` usam esta função também em ``created_at``/``updated_at``, e
    não o ``datetime.utcnow`` do resto do sistema: dentro da feature, um relógio só.
    """
    return datetime.now(TZ_SP).replace(tzinfo=None)

# Tipo de evento das vendas do canal virtual. Existe para segregar essas vendas dos KPIs de
# eventos e do cálculo de comissão (FR-052/054) e para excluí-las da sincronização com o Google
# Calendar (FR-029a) — a venda é a fonte de verdade desses eventos, não a agenda externa.
EVENT_TYPE_VIRTUAL = "VIRTUAL"

VIRTUAL_MODALITY_AO_VIVO = "ao_vivo"
VIRTUAL_MODALITY_GRAVADO = "gravado"
VIRTUAL_MODALITIES = [VIRTUAL_MODALITY_AO_VIVO, VIRTUAL_MODALITY_GRAVADO]

VIRTUAL_CAMPAIGN_STATUS_RASCUNHO = "rascunho"
VIRTUAL_CAMPAIGN_STATUS_PUBLICADA = "publicada"
VIRTUAL_CAMPAIGN_STATUS_PAUSADA = "pausada"
VIRTUAL_CAMPAIGN_STATUSES = [
    VIRTUAL_CAMPAIGN_STATUS_RASCUNHO,
    VIRTUAL_CAMPAIGN_STATUS_PUBLICADA,
    VIRTUAL_CAMPAIGN_STATUS_PAUSADA,
]

VIRTUAL_SLOT_STATUS_LIVRE = "livre"
VIRTUAL_SLOT_STATUS_TRAVADO = "travado"
VIRTUAL_SLOT_STATUS_VENDIDO = "vendido"
VIRTUAL_SLOT_STATUSES = [
    VIRTUAL_SLOT_STATUS_LIVRE,
    VIRTUAL_SLOT_STATUS_TRAVADO,
    VIRTUAL_SLOT_STATUS_VENDIDO,
]

VIRTUAL_ORDER_STATUS_RESERVADO = "reservado"
VIRTUAL_ORDER_STATUS_AGUARDANDO = "aguardando"
VIRTUAL_ORDER_STATUS_PAGO = "pago"
VIRTUAL_ORDER_STATUS_EXPIRADO = "expirado"
VIRTUAL_ORDER_STATUS_CANCELADO = "cancelado"
VIRTUAL_ORDER_STATUSES = [
    VIRTUAL_ORDER_STATUS_RESERVADO,
    VIRTUAL_ORDER_STATUS_AGUARDANDO,
    VIRTUAL_ORDER_STATUS_PAGO,
    VIRTUAL_ORDER_STATUS_EXPIRADO,
    VIRTUAL_ORDER_STATUS_CANCELADO,
]

# Ciclo de vida de uma entrega na Fila de Produção de Mídia. São os três únicos estados
# (FR-048a): enviar o vídeo é a AÇÃO que permite chegar a 'finalizado', nunca um estado próprio.
VIRTUAL_PRODUCTION_STATUS_PENDENTE = "pendente"
VIRTUAL_PRODUCTION_STATUS_GRAVANDO = "gravando"
VIRTUAL_PRODUCTION_STATUS_FINALIZADO = "finalizado"
VIRTUAL_PRODUCTION_STATUSES = [
    VIRTUAL_PRODUCTION_STATUS_PENDENTE,
    VIRTUAL_PRODUCTION_STATUS_GRAVANDO,
    VIRTUAL_PRODUCTION_STATUS_FINALIZADO,
]

VIRTUAL_REFUND_STATUS_PENDENTE = "pendente"
VIRTUAL_REFUND_STATUS_CONCLUIDA = "concluida"

# Origem do conflito que gerou a devolução (FR-018b). São dois casos com culpas opostas, e a
# equipe precisa saber qual é ao falar com a família: no primeiro a reserva simplesmente venceu; no
# segundo o sistema liberou o horário **sem conseguir confirmar** se havia pagamento, porque a
# operadora não respondeu — a família pode ter pago em dia e perdido o horário mesmo assim.
VIRTUAL_REFUND_REASON_CONFLITO = "conflito_horario"
VIRTUAL_REFUND_REASON_SEM_CONFIRMACAO = "conflito_sem_confirmacao"
VIRTUAL_REFUND_REASON_LABELS = {
    VIRTUAL_REFUND_REASON_CONFLITO: "Horário já vendido a outra família",
    VIRTUAL_REFUND_REASON_SEM_CONFIRMACAO: (
        "Horário liberado sem confirmação da operadora — a família pode ter pago no prazo"
    ),
}

VIRTUAL_NOTIFICATION_KIND_COMPRA = "compra_confirmada"
VIRTUAL_NOTIFICATION_KIND_VIDEO = "video_pronto"
VIRTUAL_NOTIFICATION_KIND_CANCELAMENTO = "cancelamento"
VIRTUAL_NOTIFICATION_KINDS = [
    VIRTUAL_NOTIFICATION_KIND_COMPRA,
    VIRTUAL_NOTIFICATION_KIND_VIDEO,
    VIRTUAL_NOTIFICATION_KIND_CANCELAMENTO,
]
# Rótulos em pt-BR dos avisos, para o painel dizer qual e-mail falhou sem expor o `kind` cru.
VIRTUAL_NOTIFICATION_LABELS = {
    VIRTUAL_NOTIFICATION_KIND_COMPRA: "Confirmação de compra",
    VIRTUAL_NOTIFICATION_KIND_VIDEO: "Vídeo pronto",
    VIRTUAL_NOTIFICATION_KIND_CANCELAMENTO: "Cancelamento e devolução",
}

# Duração fixa de uma chamada ao vivo e janela do "soft lock" do horário (FR-017).
VIRTUAL_SLOT_MINUTES = 10
VIRTUAL_SOFT_LOCK_MINUTES = 15

# Política única de retry para chamadas externas (FR-056): 3 tentativas nos minutos 0, 1 e 2.
# O intervalo curto é deliberado — protege contra vender horário já pago sem prender estoque no
# pico da campanha (pior caso de devolução de um slot: 17 minutos, SC-005).
VIRTUAL_RETRY_MAX_ATTEMPTS = 3
VIRTUAL_RETRY_INTERVAL_MIN = 1

# Teto de upload do vídeo gravado (FR-038d).
VIRTUAL_VIDEO_MAX_BYTES = 250 * 1024 * 1024
VIRTUAL_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}

# Sessão de acesso da página do pedido, aberta após a validação dupla (FR-044c).
VIRTUAL_ACCESS_SESSION_MINUTES = 30

# Limites anti-abuso padrão de uma campanha nova (FR-020b/020d) — ajustáveis por campanha.
VIRTUAL_DEFAULT_MAX_RESERVATIONS_PER_ORIGIN = 5
VIRTUAL_DEFAULT_RESERVATION_WINDOW_MINUTES = 60


class RoleName:
    SUPERADMIN = "SUPERADMIN"
    CASTING    = "CASTING"
    FIGURINO   = "FIGURINO"
    COMERCIAL  = "COMERCIAL"
    FINANCEIRO = "FINANCEIRO"
    ENSAIO     = "ENSAIO"
    # Perfil restrito (feature 078): só agenda (visualização) + EducaManto.
    REVENDEDOR_EDUCAMANTO = "REVENDEDOR_EDUCAMANTO"
    # Equipe de marketing (feature 088): cria espaços de revisão de mídia.
    MARKETING  = "MARKETING"
    # Artista 3D (feature 200): gestão total do Acervo/Fila 3D + leitura dos eventos
    # (precisa do elenco e do formulário de pré-contrato para saber o que imprimir).
    ARTISTA_3D = "ARTISTA_3D"


# Papéis que executam a produção de figurino (feature 225): assumem o pedido, movem o status,
# anexam foto e orçamento. Abrir pedido é de qualquer papel interno — quem sabe que falta uma
# bermuda é quem vendeu o evento, não a oficina.
FIGURINO_PROD_EXEC_ROLES = [RoleName.FIGURINO, RoleName.SUPERADMIN]


# Papéis que podem gerir campanhas da Loja de Interações Virtuais (feature 205, FR-010).
# COMERCIAL monta e publica a oferta; SUPERADMIN tem acesso total, como em todo o sistema.
VIRTUAIS_ADMIN_ROLES = [RoleName.SUPERADMIN, RoleName.COMERCIAL]


# Papéis que um SUPERADMIN pode simular no "Ver como" (feature 173 — fonte única,
# usada pelas rotas Jinja /impersonate/* e pela API /api/auth/impersonate).
IMPERSONABLE_ROLES = [
    RoleName.CASTING,
    RoleName.FIGURINO,
    RoleName.COMERCIAL,
    RoleName.FINANCEIRO,
    RoleName.ENSAIO,
]
