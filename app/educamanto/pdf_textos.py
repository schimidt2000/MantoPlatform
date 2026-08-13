"""Textos, avisos e valores provisórios do EducaManto por responsabilidades (feature 235).

Fonte ÚNICA de todo conteúdo editorial do orçamento (tooltips da calculadora, seções do PDF,
avisos fixos) e das constantes de negócio ainda PROVISÓRIAS. O gate de deploy da feature é
trocar os valores marcados ``PROVISORIO_*`` pelos definitivos do dono e ter os textos abaixo
revisados por ele — tudo concentrado neste arquivo (grep por ``PROVISORIO``).

Os rascunhos foram redigidos a partir do material existente (PDF antigo, ``planos.md`` e as
descrições do dono na conversa de 13/08/2026) — decisão registrada em
``specs/235-educamanto-responsabilidades/spec.md`` (Clarifications).
"""

from __future__ import annotations

# ── Valores PROVISÓRIOS (gate de deploy: substituir pelos definitivos do dono) ─────────────
# Custos por cenário [1 sessão, 2 sessões, diária 1s, diária 2s] — entram na soma de custos
# com margem, como o elenco.
PROVISORIO_SONOPLASTA = (450.0, 700.0, 400.0, 650.0)
PROVISORIO_TECNICO_SOM = (500.0, 750.0, 450.0, 700.0)
PROVISORIO_TECNICO_ILUMINACAO = (500.0, 750.0, 450.0, 700.0)

# Áreas de suficiência do som completo (m²) — aviso fixo do PDF.
PROVISORIO_SOM_AREA_FECHADA_M2 = 500
PROVISORIO_SOM_AREA_ABERTA_M2 = 300

# ── Contato (cabeçalho do PDF) ─────────────────────────────────────────────────────────────
CONTACT_PHONE = "+55 (11) 97057-0577"
CONTACT_EMAIL = "educamanto@mantoproducoes.com.br"

# ── Responsabilidades: rótulos, tooltips e textos do PDF ───────────────────────────────────
# Cada bloco tem: label (calculadora e PDF), tooltip (dica ao vendedor na calculadora),
# manto (PDF: "o que levaremos") e contratante (PDF: "mínimo exigido da contratante").
RESPONSABILIDADES: dict[str, dict[str, str]] = {
    "som": {
        "label": "Sonorização",
        "tooltip": (
            "Por conta da Manto: levamos o som completo do espetáculo e a equipe técnica "
            "(sonoplasta + técnico de som). Por conta da contratante: a escola fornece o "
            "sistema de som e nosso sonoplasta opera — confirme a estrutura antes de fechar."
        ),
        "manto": (
            "Sonorização teatral completa: caixas de som, microfones headset e/ou bastão e "
            "mesa digital, operada por sonoplasta e técnico de som da Manto."
        ),
        "contratante": (
            "Sistema de som em bom estado compatível com o porte do espetáculo: caixas "
            "amplificadas, mesa de som com entradas para ao menos 4 microfones e 1 linha de "
            "playback (P2/Bluetooth), montado e testado antes da primeira sessão. Nosso "
            "sonoplasta acompanha e opera o playback."
        ),
    },
    "iluminacao": {
        "label": "Iluminação",
        "tooltip": (
            "Por conta da Manto: iluminação cênica completa com técnico de iluminação. Por "
            "conta da contratante: basta o palco uniformemente iluminado — não vai técnico de "
            "iluminação da Manto."
        ),
        "manto": (
            "Iluminação cênica completa: moving heads, moving bees, parleds, ribaltas, "
            "máquinas de fumaça e de bolhas de sabão, mesa DMX e estrutura box truss, operada "
            "por técnico de iluminação da Manto."
        ),
        "contratante": (
            "Iluminação capaz de manter o palco uniformemente visível (luz frontal branca) "
            "durante toda a apresentação. Não é necessária iluminação cênica."
        ),
    },
    "alimentacao": {
        "label": "Alimentação",
        "tooltip": (
            "Alimentação da equipe no dia do evento. Por conta da contratante: o que será "
            "oferecido deve ser combinado com o vendedor antes do contrato."
        ),
        "manto": (
            "A Manto fornece a alimentação completa da equipe no dia do evento."
        ),
        "contratante": (
            "A parte contratante fornece a alimentação da equipe no dia do evento, para o "
            "número de pessoas indicado neste orçamento — o cardápio e os horários são "
            "combinados previamente com o vendedor."
        ),
    },
    "cenario": {
        "label": "Cenário",
        "tooltip": (
            "Ambientação de espetáculo (backdrops, elementos cenográficos). Por conta da "
            "contratante: levamos apenas os elementos de cena usados pelos personagens."
        ),
        "manto": (
            "Ambientação de espetáculo por conta da Manto: backdrops cenográficos, elementos "
            "cenográficos e elementos de cena do musical."
        ),
        "contratante": (
            "A ambientação do palco fica por conta da parte contratante. A Manto leva apenas "
            "os elementos de cena utilizados pelos personagens durante o espetáculo."
        ),
    },
}

# Ordem fixa de exibição das responsabilidades (calculadora e PDF).
RESPONSABILIDADES_ORDEM = ("som", "iluminacao", "alimentacao", "cenario")

# ── Avisos fixos do PDF ────────────────────────────────────────────────────────────────────
AVISO_PALCO = "Palco mínimo: 5 m de frente × 4 m de fundo."
AVISO_CAMARIM = (
    "Camarim obrigatório: espaço reservado com {cadeiras} cadeiras, espelho, banheiro e água "
    "para a equipe."
)
AVISO_SOM_AREA = (
    "O som completo é suficiente para até {fechada} m² em local fechado e {aberta} m² em "
    "local aberto."
)
AVISO_LOCAL_ABERTO = (
    "Local aberto: será necessária uma visita técnica ou chamada de vídeo antes do evento."
)

# ── Formas de pagamento (o valor à vista com 5% é calculado e impresso junto) ──────────────
PAGAMENTO_AVISTA_TITULO = "À Vista (PIX):"
PAGAMENTO_AVISTA_DESC = "desconto de 5% — {valores}."
PAGAMENTO_LINHAS_FIXAS = [
    ("Reserva Programada (PIX):", "50% no ato do contrato + 50% até 2 dias antes do espetáculo."),
    ("Cartão de Crédito:", "parcelamento disponível (taxas da operadora repassadas ao cliente)."),
]

# ── Rótulos de equipe ──────────────────────────────────────────────────────────────────────
TECNICO_LABELS = {
    "sonoplasta": "Sonoplasta",
    "tecnico_som": "Técnico de som",
    "tecnico_iluminacao": "Técnico de iluminação",
}


def descricao_equipe(num_personagens: int, num_producao: int, tecnicos: list[str]) -> str:
    """Frase das quantidades da equipe para o PDF (ex.: "9 personagens, 2 de produção e 3 técnicos")."""
    partes = [
        f"{num_personagens} personagens" if num_personagens != 1 else "1 personagem",
        f"{num_producao} de produção",
    ]
    n_tec = len(tecnicos)
    nomes = ", ".join(TECNICO_LABELS[t] for t in tecnicos)
    partes.append(f"{n_tec} técnico{'s' if n_tec != 1 else ''} ({nomes})")
    return ", ".join(partes[:-1]) + " e " + partes[-1]
