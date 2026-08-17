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

# Custos de som/iluminação: NÃO ficam aqui — são a tabela única por combinação em
# `pricing_config['educamanto_som_luz']` (3ª rodada, valores reais de
# EspecificacoesEducamanto.md: 4.200 / 2.900 / 2.900 / 750, equipe técnica inclusa,
# por dia de evento, com margem em cima).

# ── Contato (cabeçalho do PDF) ─────────────────────────────────────────────────────────────
CONTACT_PHONE = "+55 (11) 97057-0577"
CONTACT_EMAIL = "educamanto@mantoproducoes.com.br"

# ── Responsabilidades: rótulos, tooltips e textos do PDF ───────────────────────────────────
# Cada bloco tem: label (calculadora e PDF), tooltip (dica ao vendedor na calculadora),
# manto (PDF: "o que levaremos") e contratante (PDF: "mínimo exigido da contratante").
RESPONSABILIDADES: dict[str, dict[str, str]] = {
    # Som e iluminação: riders REAIS de EspecificacoesEducamanto.md (14/08/2026) — "manto" é o
    # rider do que levamos; "contratante" é o rider MÍNIMO que ela precisa fornecer.
    "som": {
        "label": "Sonorização",
        "tooltip": (
            "Por conta da Manto: rider completo de som com sonoplasta e técnico de som "
            "(operação considera 1 dia de ensaio, 1 de montagem e 1 de evento). Por conta da "
            "contratante: ela fornece PA, microfones, mesa e técnico — nosso sonoplasta opera "
            "o espetáculo."
        ),
        "manto": (
            "Sonorização completa: 04 caixas de som 1.000 W com pedestais de 1,75 m, "
            "03 microfones headset (Armer), 03 microfones bastão de stand by (Arcano/Armer), "
            "mesa digital UI16 ou Duonn Atrium 12, tablet e notebook — operada por sonoplasta "
            "e técnico de som da Manto."
        ),
        "contratante": (
            "PA compatível com o espaço da apresentação, retorno de palco, 03 microfones "
            "headset (Armer/Shure/Sennheiser), 03 microfones bastão de stand by "
            "(Arcano/Armer/Shure/Sennheiser), mesa de som que comporte os microfones e um "
            "notebook, e técnico de som. A cobertura sonora do ambiente deve ser garantida "
            "pela empresa responsável pela montagem do som; nosso sonoplasta opera o "
            "espetáculo."
        ),
    },
    "iluminacao": {
        "label": "Iluminação",
        "tooltip": (
            "Por conta da Manto: rider completo de iluminação cênica com técnico de luz. Por "
            "conta da contratante: ela fornece o rider mínimo de iluminação com técnico "
            "próprio."
        ),
        "manto": (
            "Iluminação cênica completa: 02 moving heads, 02 moving bees, 10 par LEDs, "
            "08 ribaltas, 01 máquina de fumaça, mesa de iluminação (Operator/Pilot) e "
            "estrutura em box de 10 metros — operada por técnico de iluminação da Manto."
        ),
        "contratante": (
            "02 moving heads, 02 moving bees, 10 par LEDs, 08 ribaltas, 01 máquina de "
            "fumaça, mesa de iluminação e técnico de iluminação próprios."
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
# Cobertura real do rider (EspecificacoesEducamanto.md) — impressa quando o som é da Manto.
AVISO_SOM_AREA = (
    "Nosso som atende um espaço de aproximadamente 300 m² (ex.: 25 m × 12 m) e até 150 "
    "pessoas — a capacidade pode variar conforme a eficiência acústica do local."
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
