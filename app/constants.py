"""Application-wide constants.

Centralises role name strings so they are defined once and imported
everywhere. Using the class attributes (e.g. ``RoleName.SUPERADMIN``)
means a typo becomes an ``AttributeError`` at import time instead of a
silent authorisation bypass at runtime.
"""

from datetime import date

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


# Papéis que um SUPERADMIN pode simular no "Ver como" (feature 173 — fonte única,
# usada pelas rotas Jinja /impersonate/* e pela API /api/auth/impersonate).
IMPERSONABLE_ROLES = [
    RoleName.CASTING,
    RoleName.FIGURINO,
    RoleName.COMERCIAL,
    RoleName.FINANCEIRO,
    RoleName.ENSAIO,
]
