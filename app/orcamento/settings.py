"""Pricing configuration for the quote calculator.

Settings are persisted in SiteSetting.pricing_config (JSON TEXT column).
Falls back to DEFAULTS when no configuration has been saved yet.
"""
import copy
import json
import logging
import math
import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

logger = logging.getLogger(__name__)

# Feature 307: limites do markup de uma faixa de data especial (um 33,4 digitado no lugar de 3,34
# multiplicaria o Natal por 10 ao vivo na calculadora).
MARKUP_FAIXA_MIN = 1.0
MARKUP_FAIXA_MAX = 6.0
# Feature 309: a 307 tinha posto "Papai Noel" em 712 e "Ajudante do Noel" em 423 para o preço da
# Visita Mágica (R$ 2.500 / R$ 3.600) sair do markup — e esse número virava o TETO da vaga. Com o
# produto de tabela o preço vem da tabela de venda e cachê volta a ser cachê (600 / 270): a troca
# INVERSA só age sobre quem ainda estiver exatamente nesses valores (padrão "Transformer → BGE").
NOEL_712 = [712, 800, 850, 900]
AJUDANTE_423 = [423, 480, 510, 540]
TIPOS_DE_VAGA = ("especial", "ator", "coordenador", "maquiador")
LABEL_FIXO_POR_TIPO = {"coordenador": "Coordenador", "maquiador": "Maquiador"}
PRODUTO_ROTULO_MAX = 60
PRODUTO_DESCRICAO_MAX = 120
PRODUTO_DETALHES_MAX = 300
PRODUTO_VAGAS_MAX = 10
NOTA_FAIXA_MAX_CHARS = 200
ROTULO_FAIXA_MAX_CHARS = 60
CHAVE_FAIXA_RE = re.compile(r"^[a-z0-9_]{1,30}$")
_DIA_MM_DD_RE = re.compile(r"^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")
_DATA_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CENTAVO = Decimal("0.01")
_DINHEIRO_MAX = 100_000.0  # teto de sanidade para um cachê/piso da faixa (o JSON aceita Infinity)


class SettingsValidationError(Exception):
    """Bloco da tabela de preços recusado; ``fields`` aponta o campo (padrão de QuoteValidationError)."""

    def __init__(self, message: str, fields: dict) -> None:
        super().__init__(message)
        self.message = message
        self.fields = fields

# Feature 307: faixa de data especial. Em 24 e 25/12 o markup e os cachês de Papai Noel, Ajudante do
# Noel e Coordenador vêm daqui (cachês reais pagos no Natal de 2025: Noel 1.000, ajudante 650,
# coordenador 500 por casa; markup 3,34 escolhido pelo dono em 15/10/2026 → para o Noel AVULSO
# sozinho ≈ R$ 5.010, Noel + ajudante ≈ R$ 7.181). `piso` eleva qualquer outro performer ao cachê do
# ajudante — sem ele Noel + boneco (200) sairia mais barato que Noel + ajudante e com teto de 200. Os
# valores de 2h–4h são lineares (cada hora = preço cheio): na véspera o tempo do Noel é o recurso
# escasso. Desde a 309 a Visita Mágica em si é vendida pelo PRODUTO (`produtos`, 5.000 / 6.500 na
# faixa); esta faixa continua valendo para os avulsos na data e é a fonte do cachê das vagas do produto.
_FAIXA_NATAL_PADRAO: dict = {
    "rotulo": "Véspera e Natal",
    "dias": ["12-24", "12-25"],
    "markup": [3.34, 3.34, 3.34, 3.34],
    "cache": {
        "Papai Noel": [1000, 2000, 3000, 4000],
        "Ajudante do Noel": [650, 1300, 1950, 2600],
    },
    "coordenador": [500, 1000, 1500, 2000],
    "piso": [650, 1300, 1950, 2600],
    "nota_mensagem": "Valores especiais de 24 e 25 de dezembro.",
}

# Feature 309: produtos de tabela. O preço ao cliente é o da tabela de venda (fixo por visita; por
# faixa de data especial quando houver) e as vagas vêm com o cachê "pela tabela vigente na data"
# (`cache: null`) — Noel 600 / Ajudante 270 / Coordenador 250 / Maquiador 250 normal, 1.000 / 650 /
# 500 / 250 na faixa natal. Markup não entra; noturno embutido. Tipo `coordenador`/`maquiador` tem o
# label fixo porque `_ensure_coordinator` e o vínculo 273 casam por esses nomes.
# 309b: descrição e "o que inclui" saem da arte da campanha (visita de até 30 minutos — a 309 nasceu
# dizendo "até 1h", e o orçamento prometia ao cliente o dobro do que se entrega).
_DESCRICAO_VISITA = "visita de até 30 minutos"
_DESCRICAO_VISITA_ANTIGA = "visita padrão, até 1h"
_DETALHES_VISITA = (
    "Chegada mágica, músicas natalinas cantadas com a família, entrega de até 10 presentes "
    "(fornecidos pela contratante) e, ao final, uma mensagem especial sobre o verdadeiro significado do Natal."
)
_PRODUTOS_PADRAO: dict = {
    "visita_magica": {
        "rotulo": "Visita Mágica — Papai Noel",
        "descricao": _DESCRICAO_VISITA,
        "detalhes": _DETALHES_VISITA,
        "ativo": True,
        "preco": 2500,
        "por_faixa": {"natal": {"preco": 5000}},
        "vagas": [
            {"label": "Papai Noel", "tipo": "especial", "cache": None, "needs_makeup": True},
            {"label": "Coordenador", "tipo": "coordenador", "cache": None, "needs_makeup": False},
            {"label": "Maquiador", "tipo": "maquiador", "cache": None, "needs_makeup": False},
        ],
        "inclui_noturno": True,
    },
    "visita_magica_ajudante": {
        "rotulo": "Visita Mágica — Papai Noel + Ajudante",
        "descricao": _DESCRICAO_VISITA,
        "detalhes": _DETALHES_VISITA,
        "ativo": True,
        "preco": 3600,
        "por_faixa": {"natal": {"preco": 6500}},
        "vagas": [
            {"label": "Papai Noel", "tipo": "especial", "cache": None, "needs_makeup": True},
            {"label": "Ajudante do Noel", "tipo": "especial", "cache": None, "needs_makeup": False},
            {"label": "Coordenador", "tipo": "coordenador", "cache": None, "needs_makeup": False},
            {"label": "Maquiador", "tipo": "maquiador", "cache": None, "needs_makeup": False},
        ],
        "inclui_noturno": True,
    },
}
# Produto sem preço para a faixa da data: "custo de cachê dobrado e markup um pouco mais alto que o
# padrão" (dono, 19/10/2026) — Σ cachês 1h das vagas pela tabela normal × fator_cache × markup.
_ESTIMATIVA_PADRAO: dict = {"fator_cache": 2.0, "markup": 3.0}

DEFAULTS: dict = {
    # Cada tabela é uma lista de 4 valores por duração, na ordem [1h, 2h, 3h, 4h] (feature 098).
    # O valor de 3h é a média entre 2h e 4h (progressão linear), editável nas configurações.
    "markup": {
        "receptivo": [3.0, 2.7, 2.6, 2.5],
        "show":      [2.6, 2.4, 2.3, 2.2],
    },
    "ator": {
        "cara_limpa|false|false": [200, 250, 275, 300],
        "cara_limpa|false|true":  [220, 270, 295, 320],
        "cara_limpa|true|false":  [300, 350, 375, 400],
        "cara_limpa|true|true":   [320, 370, 395, 420],
        "boneco|false|false":     [200, 250, 275, 300],
        "boneco|true|false":      [300, 350, 375, 400],
    },
    "cantor": {
        "base":       [250, 300, 325, 350],
        "show_extra": [100, 100, 100, 100],
        "make_extra": [20,  20,  20,  20],
    },
    "tecnico_som": [750, 800, 825, 850],
    "coordenador": {
        "false": [250, 300, 325, 350],
        "true":  [300, 350, 375, 400],
    },
    "especiais": {
        "Homem-Aranha":           {"false": [250, 300, 325, 350], "true": [400, 450, 475, 500]},
        "Perna de Pau":           [400, 450, 475, 500],
        "Monociclo":              [400, 450, 475, 500],
        "Malabar":                [350, 400, 425, 450],
        "Pirofagista":            [450, 500, 525, 550],
        "Boneco Grande Especial": {"false": [400, 450, 475, 500], "true": [400, 450, 475, 500]},
        "Sósia":                  {"none": [350, 400, 425, 450], "show": [450, 500, 525, 550], "cantor": [500, 550, 575, 600]},
        "Bailarino":              [400, 450, 475, 500],
        "DJ":                     [200, 300, 350, 400],
        # Feature 309: cachê é cachê — o pago real de 2025 (600) e o do ajudante (270, cara limpa);
        # 2h–4h na progressão da tabela antiga do Noel e no degrau do ator. A Visita Mágica em si é
        # vendida pelo produto (`produtos`); estas linhas valem para o Noel AVULSO (festa grande) e
        # são a fonte do cachê das vagas do produto fora de 24/25.
        "Papai Noel":             [600, 650, 675, 700],
        "Ajudante do Noel":       [270, 320, 345, 370],
    },
    "especiais_regras": {
        "Boneco Grande Especial": {
            "transporte_especial": 1000,
            "min_coordenadores":   2,
        },
    },
    "brinde_show": 100,
    "maquiador": {
        "make_1":               250,
        "make_2_adicional":     50,
        "make_extra_adicional": 100,
        "make_especial":        300,
    },
    "transporte": {
        "van_com_carretinha": 5.5,
        "van_sem_carretinha": 6.3,
        "carro_por_km":       1.9,
        "afsp_divisor":       3.0,
        "ashow_divisor":      6.0,
        "ashow_min_km":       500,
        # Feature 235: caminhão de cenografia do EducaManto DENTRO de São Paulo (valor fixo,
        # entra na soma de custos do musical). Fora de SP o caminhão sai e entram 2 vans.
        "caminhao_sp":        800,
    },
    # Feature 235 (3ª rodada, valores reais do dono em EspecificacoesEducamanto.md): CUSTO de
    # som/iluminação do EducaManto POR COMBINAÇÃO de responsabilidades — os preços não são
    # aditivos (som+luz custa menos que a soma das partes) e a equipe técnica (sonoplasta/
    # técnicos) já está DENTRO do valor. Cobra-se por DIA DE EVENTO; entra na soma de custos
    # com a margem do musical, como o antigo item "Som".
    "educamanto_som_luz": {
        "som_luz": 4200,   # som e iluminação pela Manto (rider completo, 3 técnicos)
        "som":     2900,   # só som pela Manto (sonoplasta + técnico de som)
        "luz":     2900,   # só iluminação pela Manto (sonoplasta + técnico de luz)
        "nenhum":  750,    # tudo da contratante (apenas o sonoplasta)
    },
    # Feature 100: tipos de acréscimo comuns, editáveis nas Configurações de Preços. BV e Outro são
    # sempre acrescentados pelo helper acrescimo_tipos_list() (BV é protegido — regra financeira).
    "acrescimo_tipos": [
        "Taxa de urgência",
        "Deslocamento/Logística",
        "Domingo/Feriado",
        "Hora extra",
    ],
    # Feature 307: faixas de data especial, por chave; a calculadora resolve pela data do evento.
    "datas_especiais": {
        "natal": copy.deepcopy(_FAIXA_NATAL_PADRAO),
    },
    # Feature 309: produtos de tabela (preço de venda fixo + vagas com cachê pela tabela).
    "produtos": copy.deepcopy(_PRODUTOS_PADRAO),
    "produtos_estimativa": copy.deepcopy(_ESTIMATIVA_PADRAO),
}

# Especiais que têm checkbox de show (técnico de som é adicionado se marcado)
ESPECIAIS_COM_SHOW: set = {"Homem-Aranha", "Boneco Grande Especial", "Sósia"}

# Especiais que têm checkbox de cantor (implica show)
ESPECIAIS_COM_CANTOR: set = {"Sósia"}

# Especiais que sempre ativam técnico de som (sem checkbox — comportamento fixo)
ESPECIAIS_SEMPRE_SHOW: set = {"DJ"}


def interpolar_3h(v2, v4):
    """Deriva o valor de 3h como a média entre 2h e 4h (feature 098).

    Mantém inteiro para cachês (valores em reais inteiros) e decimal para coeficientes de markup.

    Args:
        v2: Valor de 2h. v4: Valor de 4h.

    Returns:
        A média arredondada — ``int`` se ambos forem inteiros, senão ``float`` com 2 casas.
    """
    mean = (v2 + v4) / 2
    if isinstance(v2, int) and isinstance(v4, int):
        return int(round(mean))
    return round(mean, 2)


def _ensure4(lst):
    """Normaliza uma lista de preços de 3 valores [1h,2h,4h] para 4 [1h,2h,3h,4h], injetando o 3h.

    Idempotente: listas que já têm 4 valores (ou tamanho diferente de 3) são retornadas sem mudança.
    """
    if isinstance(lst, list) and len(lst) == 3:
        return [lst[0], lst[1], interpolar_3h(lst[1], lst[2]), lst[2]]
    return lst


def _inject_3h(data: dict) -> None:
    """Injeta o valor de 3h em toda tabela de preços/coeficientes salva com 3 valores (feature 098)."""
    markup = data.get("markup", {})
    for k in ("receptivo", "show"):
        if k in markup:
            markup[k] = _ensure4(markup[k])

    for key, val in list(data.get("ator", {}).items()):
        data["ator"][key] = _ensure4(val)

    cantor = data.get("cantor", {})
    for k in ("base", "show_extra", "make_extra"):
        if k in cantor:
            cantor[k] = _ensure4(cantor[k])

    if "tecnico_som" in data:
        data["tecnico_som"] = _ensure4(data["tecnico_som"])

    coord = data.get("coordenador", {})
    for k in list(coord.keys()):
        coord[k] = _ensure4(coord[k])

    for nome, val in list(data.get("especiais", {}).items()):
        if isinstance(val, dict):
            data["especiais"][nome] = {vk: _ensure4(vv) for vk, vv in val.items()}
        else:
            data["especiais"][nome] = _ensure4(val)


def _migrate(data: dict) -> dict:
    """Aplica migrações na config salva no banco sem alterar o banco."""
    especiais = data.setdefault("especiais", {})

    # Renomear Transformer → Boneco Grande Especial
    if "Transformer" in especiais and "Boneco Grande Especial" not in especiais:
        old = especiais.pop("Transformer")
        especiais["Boneco Grande Especial"] = (
            old if isinstance(old, dict) else {"false": old, "true": old}
        )

    # Remover antigas variantes de Sósia (agora unificadas em "Sósia")
    for old_key in ("Sósia com Show", "Sósia Cantor"):
        especiais.pop(old_key, None)

    # Converter Sósia de lista/dict antigo para novo formato {none/show/cantor}
    if "Sósia" in especiais:
        sosia = especiais["Sósia"]
        if isinstance(sosia, list):
            especiais["Sósia"] = {
                "none":   sosia,
                "show":   [sosia[i] + 100 for i in range(3)],
                "cantor": [sosia[i] + 150 for i in range(3)],
            }
        elif isinstance(sosia, dict) and "false" in sosia:
            base = sosia.get("false", [350, 400, 450])
            especiais["Sósia"] = {
                "none":   base,
                "show":   [base[i] + 100 for i in range(3)],
                "cantor": [base[i] + 150 for i in range(3)],
            }

    # Converter cantor de {false/true} para {base/show_extra/make_extra}
    if "cantor" in data and isinstance(data["cantor"], dict):
        c = data["cantor"]
        if "false" in c and "true" in c:
            base = c["false"]
            make_extra = [c["true"][i] - c["false"][i] for i in range(3)]
            data["cantor"] = {
                "base":       base,
                "show_extra": [100, 100, 100],
                "make_extra": make_extra,
            }

    # Adicionar especiais novos que ainda não existem — respeita exclusões explícitas pelo usuário
    excluidos = set(data.get("especiais_excluidos", []))
    for nome, val in DEFAULTS["especiais"].items():
        if nome not in especiais and nome not in excluidos:
            especiais[nome] = copy.deepcopy(val)

    # Adicionar especiais_regras se ausente
    if "especiais_regras" not in data:
        data["especiais_regras"] = copy.deepcopy(DEFAULTS["especiais_regras"])

    # Feature 098: normaliza todas as tabelas para 4 durações [1h,2h,3h,4h], injetando o 3h por média.
    _inject_3h(data)

    # Feature 100: garante a chave de tipos de acréscimo em configs salvas antes desta feature.
    if "acrescimo_tipos" not in data:
        data["acrescimo_tipos"] = copy.deepcopy(DEFAULTS["acrescimo_tipos"])

    # Feature 235: garante o caminhão de cenografia do EducaManto em configs antigas.
    data.setdefault("transporte", {}).setdefault(
        "caminhao_sp", DEFAULTS["transporte"]["caminhao_sp"]
    )
    # Feature 235 (3ª rodada): tabela de som/iluminação por combinação em configs antigas.
    data.setdefault("educamanto_som_luz", copy.deepcopy(DEFAULTS["educamanto_som_luz"]))

    _migrar_307(data)
    _migrar_309(data)

    return data


def _lista4(valor, padrao: list) -> list:
    """Lista de 4 preços/coeficientes da faixa; aceita 3 (injeta o 3h) e cai no padrão se inválida."""
    if isinstance(valor, list) and len(valor) in (3, 4):
        try:
            return _ensure4([float(v) for v in valor])
        except (TypeError, ValueError):
            pass
    return copy.deepcopy(padrao)


def _lista_numerica(valor) -> bool:
    """Lista de 3 ou 4 números (sem bool) — o único formato aceito numa sobrescrita de cachê."""
    return (
        isinstance(valor, list)
        and len(valor) in (3, 4)
        and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in valor)
    )


def _normalizar_faixa(chave: str, faixa) -> dict | None:
    """Devolve a faixa de data especial normalizada, ou ``None`` se não dá para aproveitar nada.

    Faixa que não é dict ou não tem ``dias`` (lista — vazia = faixa desligada) cai no padrão da
    mesma chave (``None`` se a chave não é conhecida). Cada lista passa por `_lista4`; sobrescrita
    de cachê malformada é DESCARTADA (o especial volta para tabela + piso) — virar ``[0, 0, 0, 0]``
    seria um cachê zero silencioso no Noel.
    """
    padrao = DEFAULTS["datas_especiais"].get(chave) or _FAIXA_NATAL_PADRAO
    if not isinstance(faixa, dict) or not isinstance(faixa.get("dias"), list):
        return copy.deepcopy(padrao) if chave in DEFAULTS["datas_especiais"] else None
    cache_bruto = faixa.get("cache") if isinstance(faixa.get("cache"), dict) else {}
    return {
        "rotulo": str(faixa.get("rotulo") or padrao["rotulo"]),
        "dias": [d for d in faixa["dias"] if isinstance(d, str)],
        "markup": _lista4(faixa.get("markup"), padrao["markup"]),
        "cache": {
            str(nome): _ensure4([float(v) for v in val])
            for nome, val in cache_bruto.items()
            if _lista_numerica(val)
        },
        "coordenador": _lista4(faixa.get("coordenador"), padrao["coordenador"]),
        "piso": _lista4(faixa.get("piso"), padrao["piso"]),
        "nota_mensagem": _nota_limpa(faixa.get("nota_mensagem"))[:NOTA_FAIXA_MAX_CHARS],
    }


def _nota_limpa(raw) -> str:
    """Nota numa linha só: quebra de linha quebraria o itálico do WhatsApp e o rodapé do PDF."""
    return " ".join(str(raw or "").split())


# ── validação do bloco (regra de negócio; o endpoint só traduz em 400) ─────────────────────────
def _dia_existe(mm_dd) -> bool:
    """``"MM-DD"`` que existe no calendário (2024 é bissexto: 29/02 aceito)."""
    if not isinstance(mm_dd, str) or not _DIA_MM_DD_RE.fullmatch(mm_dd):
        return False
    try:
        date.fromisoformat(f"2024-{mm_dd}")
    except ValueError:
        return False
    return True


def _dinheiro(raw) -> float | None:
    """Valor em R$ ≥ 0 (número ou string BR); ``None`` se inválido — nunca cai num default."""
    from app.money import parse_brl

    if isinstance(raw, bool) or raw is None:
        return None
    if isinstance(raw, (int, float)):
        valor = float(raw)
    else:
        parsed = parse_brl(str(raw))
        if parsed is None:
            return None
        valor = float(parsed)
    return valor if math.isfinite(valor) and 0 <= valor <= _DINHEIRO_MAX else None


def _lista_de_4(raw) -> list[float] | None:
    """Quatro valores em R$ válidos, ou ``None``."""
    if not isinstance(raw, list) or len(raw) != 4:
        return None
    valores = [_dinheiro(v) for v in raw]
    return None if any(v is None for v in valores) else valores


def _markup_de_4(raw) -> list[float] | None:
    """Quatro coeficientes com 2 casas (HALF_UP) dentro de ``[MARKUP_FAIXA_MIN, MARKUP_FAIXA_MAX]``."""
    if not isinstance(raw, list) or len(raw) != 4:
        return None
    try:
        valores = [
            float(Decimal(str(v)).quantize(_CENTAVO, rounding=ROUND_HALF_UP)) for v in raw
        ]
    except (InvalidOperation, TypeError, ValueError):
        return None
    if any(not (MARKUP_FAIXA_MIN <= v <= MARKUP_FAIXA_MAX) for v in valores):
        return None
    return valores


def _dia_para_tela(mm_dd: str) -> str:
    return f"{mm_dd[3:5]}/{mm_dd[0:2]}"


def _validar_dias(pref: str, dias, erros: dict) -> list[str] | None:
    """Dias ``MM-DD`` reais, sem repetição; lista vazia é aceita (faixa desligada)."""
    if not isinstance(dias, list):
        erros[f"{pref}.dias"] = "informe os dias (DD/MM)"
        return None
    ruins = [d for d in dias if not _dia_existe(d)]
    if ruins:
        erros[f"{pref}.dias"] = f"dia inválido: {', '.join(str(d) for d in ruins)}"
        return None
    repetidos = [d for d in dict.fromkeys(dias) if dias.count(d) > 1]
    if repetidos:
        erros[f"{pref}.dias"] = f"dia repetido: {', '.join(_dia_para_tela(d) for d in repetidos)}"
        return None
    return list(dias)


def _validar_cache(pref: str, cache, especiais: dict, erros: dict) -> dict:
    """Sobrescritas de cachê: só de especiais existentes, 4 valores em R$ maiores que zero.

    Zero é recusado de propósito: a sobrescrita passa por fora do piso, então um `[0, 0, 0, 0]`
    (o estado em que um chip novo poderia nascer) viraria cachê zero na venda E no teto da vaga.
    """
    if cache is None:
        return {}
    if not isinstance(cache, dict):
        erros[f"{pref}.cache"] = "sobrescritas inválidas"
        return {}
    limpo: dict = {}
    for nome, val in cache.items():
        if nome not in especiais:
            erros[f"{pref}.cache.{nome}"] = f"especial desconhecido: {nome}"
            continue
        lista = _lista_de_4(val)
        if lista is None or any(v <= 0 for v in lista):
            erros[f"{pref}.cache.{nome}"] = (
                "4 valores em R$ maiores que zero (remova a sobrescrita para usar o piso)"
            )
        else:
            limpo[str(nome)] = lista
    return limpo


def _validar_faixa(chave: str, faixa, especiais: dict, erros: dict) -> dict | None:
    """Uma faixa limpa, ou ``None`` — com os erros registrados por campo em ``erros``."""
    pref = f"datas_especiais.{chave}"
    if not CHAVE_FAIXA_RE.fullmatch(chave) or not isinstance(faixa, dict):
        erros[pref] = "faixa inválida"
        return None
    limpa: dict = {"rotulo": str(faixa.get("rotulo") or "").strip()}
    if not limpa["rotulo"]:
        erros[f"{pref}.rotulo"] = "informe o rótulo"
    elif len(limpa["rotulo"]) > ROTULO_FAIXA_MAX_CHARS:
        erros[f"{pref}.rotulo"] = f"rótulo com mais de {ROTULO_FAIXA_MAX_CHARS} caracteres"
    dias = _validar_dias(pref, faixa.get("dias"), erros)
    if dias is not None:
        limpa["dias"] = dias
    markup = _markup_de_4(faixa.get("markup"))
    if markup is None:
        erros[f"{pref}.markup"] = (
            f"4 valores entre {MARKUP_FAIXA_MIN:g} e {MARKUP_FAIXA_MAX:g} (coeficiente)"
        )
    else:
        limpa["markup"] = markup
    for campo in ("coordenador", "piso"):
        lista = _lista_de_4(faixa.get(campo))
        if lista is None:
            erros[f"{pref}.{campo}"] = "4 valores em R$"
        else:
            limpa[campo] = lista
    limpa["cache"] = _validar_cache(pref, faixa.get("cache"), especiais, erros)
    nota = _nota_limpa(faixa.get("nota_mensagem"))
    if len(nota) > NOTA_FAIXA_MAX_CHARS:
        erros[f"{pref}.nota_mensagem"] = f"nota com mais de {NOTA_FAIXA_MAX_CHARS} caracteres"
    limpa["nota_mensagem"] = nota
    return limpa


def validar_datas_especiais(bloco, especiais: dict) -> dict:
    """Valida o bloco `datas_especiais` vindo da tela e devolve a cópia limpa (feature 307).

    Um 33,4 no lugar de 3,34 multiplicaria o Natal por 10 ao vivo — por isso tudo tem faixa válida
    e o erro nomeia o campo (``datas_especiais.<faixa>.<campo>``). O bloco enviado SUBSTITUI o
    salvo; corpo inválido não grava nada.

    Raises:
        SettingsValidationError: com ``fields`` por campo.
    """
    if not isinstance(bloco, dict):
        raise SettingsValidationError("Datas especiais inválidas.", {"datas_especiais": "bloco inválido"})
    erros: dict = {}
    limpo: dict = {}
    dono_do_dia: dict[str, str] = {}
    for chave, faixa in bloco.items():
        limpa = _validar_faixa(str(chave), faixa, especiais, erros)
        if limpa is None:
            continue
        # O mesmo dia em duas faixas deixaria o preço depender da ordem das chaves.
        for dia in limpa.get("dias", []):
            if dia in dono_do_dia:
                erros[f"datas_especiais.{chave}.dias"] = (
                    f"{_dia_para_tela(dia)} já está na faixa {dono_do_dia[dia]}"
                )
            dono_do_dia.setdefault(dia, str(chave))
        limpo[str(chave)] = limpa
    if erros:
        raise SettingsValidationError("Datas especiais inválidas.", erros)
    return limpo


def remover_especial_das_faixas(data: dict, nome: str) -> None:
    """Ao excluir um especial da tabela, tira a sobrescrita dele de toda faixa (feature 307).

    Sem isso o card continuaria mandando o nome órfão e TODO "Salvar configurações" levaria 400.
    """
    for faixa in (data.get("datas_especiais") or {}).values():
        if isinstance(faixa, dict) and isinstance(faixa.get("cache"), dict):
            faixa["cache"].pop(nome, None)


def _migrar_307(data: dict) -> None:
    """Feature 307: garante `datas_especiais` em configs antigas.

    Roda DENTRO do ``try`` de `load()`: qualquer exceção aqui devolveria os DEFAULTS do código para a
    tabela inteira (markup 3,0 no lugar do 2,6 real, e sem o "Papai Noel" salvo) — por isso nada
    aqui indexa sem conferir o tipo, e bloco ou faixa malformados viram o padrão em silêncio.
    A troca automática do "Papai Noel" 600 → 712 que morava aqui saiu na 309 (cachê é cachê; a
    Visita Mágica virou produto) — `_migrar_309` faz a inversa, guardada.
    """
    bloco = data.get("datas_especiais")
    limpo: dict = {}
    if isinstance(bloco, dict):
        for chave, faixa in bloco.items():
            normalizada = _normalizar_faixa(str(chave), faixa)
            if normalizada is not None:
                limpo[str(chave)] = normalizada
    for chave, faixa in DEFAULTS["datas_especiais"].items():
        limpo.setdefault(chave, copy.deepcopy(faixa))
    # Sobrescrita de especial que não está (mais) na tabela — excluído pelo time, ou a faixa padrão
    # chegando antes dele — sai daqui: órfã, ela faria TODO "Salvar configurações" levar 400.
    especiais_vivos = data.get("especiais") if isinstance(data.get("especiais"), dict) else {}
    for faixa in limpo.values():
        faixa["cache"] = {n: v for n, v in faixa["cache"].items() if n in especiais_vivos}
    data["datas_especiais"] = limpo


# ── feature 309: produtos de tabela ────────────────────────────────────────────────────────────
def _normalizar_vaga(vaga) -> dict | None:
    """Vaga do produto normalizada, ou ``None`` se não dá para aproveitar (tipo ou nome inválidos).

    Cachê fixo malformado vira ``None`` = "pela tabela" (descartar a vaga por isso tiraria o Noel do
    produto); maquiagem só existe em especial/ator; coordenador e maquiador têm o label fixo.
    """
    if not isinstance(vaga, dict):
        return None
    tipo = vaga.get("tipo")
    if tipo not in TIPOS_DE_VAGA:
        return None
    label = LABEL_FIXO_POR_TIPO.get(tipo) or str(vaga.get("label") or "").strip()[:120]
    if not label:
        return None
    cache = _dinheiro(vaga.get("cache")) if vaga.get("cache") is not None else None
    if cache is not None and cache <= 0:
        cache = None
    return {
        "label": label,
        "tipo": tipo,
        "cache": cache,
        "needs_makeup": bool(vaga.get("needs_makeup")) if tipo in ("especial", "ator") else False,
    }


def _descricao_limpa(raw) -> str:
    """Descrição ao cliente numa linha, SEM parênteses externos: mensagem, PDF e tela já a põem entre
    parênteses — "(visita padrão (até 1h))" era o resultado de digitar com eles."""
    texto = _nota_limpa(raw)
    if len(texto) >= 2 and texto.startswith("(") and texto.endswith(")"):
        texto = texto[1:-1].strip()
    return texto


def _normalizar_produto(produto, faixas: set[str]) -> dict | None:
    """Produto normalizado na defensiva, ou ``None`` (descartado: sem rótulo, sem preço > 0 ou sem vaga).

    Nunca produz preço 0; `por_faixa` só com faixas que existem (as outras são descartadas).
    """
    if not isinstance(produto, dict):
        return None
    rotulo = str(produto.get("rotulo") or "").strip()[:PRODUTO_ROTULO_MAX]
    preco = _dinheiro(produto.get("preco"))
    if not rotulo or preco is None or preco <= 0:
        return None
    # Converge 309: conferir o tipo ANTES de iterar — `"vagas": 5` levantava dentro de `load()`.
    vagas_brutas = produto.get("vagas") if isinstance(produto.get("vagas"), list) else []
    vagas = [v for v in (_normalizar_vaga(x) for x in vagas_brutas) if v is not None][:PRODUTO_VAGAS_MAX]
    if not vagas:
        return None
    por_faixa: dict = {}
    bruto = produto.get("por_faixa") if isinstance(produto.get("por_faixa"), dict) else {}
    for chave, val in bruto.items():
        if str(chave) not in faixas or not isinstance(val, dict):
            continue
        preco_faixa = _dinheiro(val.get("preco"))
        if preco_faixa is not None and preco_faixa > 0:
            por_faixa[str(chave)] = {"preco": preco_faixa}
    return {
        "rotulo": rotulo,
        "descricao": _descricao_limpa(produto.get("descricao"))[:PRODUTO_DESCRICAO_MAX],
        "detalhes": _nota_limpa(produto.get("detalhes"))[:PRODUTO_DETALHES_MAX],
        "ativo": bool(produto.get("ativo", True)),
        "preco": preco,
        "por_faixa": por_faixa,
        "vagas": vagas,
        "inclui_noturno": bool(produto.get("inclui_noturno", True)),
    }


def _normalizar_estimativa(raw) -> dict:
    """Fatores da estimativa com defaults por campo (fator > 0 finito; markup dentro dos limites)."""
    limpo = copy.deepcopy(_ESTIMATIVA_PADRAO)
    if not isinstance(raw, dict):
        return limpo
    fator = raw.get("fator_cache")
    if isinstance(fator, (int, float)) and not isinstance(fator, bool) and math.isfinite(fator) and fator > 0:
        limpo["fator_cache"] = float(fator)
    markup = raw.get("markup")
    if (
        isinstance(markup, (int, float))
        and not isinstance(markup, bool)
        and math.isfinite(markup)
        and MARKUP_FAIXA_MIN <= markup <= MARKUP_FAIXA_MAX
    ):
        limpo["markup"] = float(markup)
    return limpo


def _migrar_309b(chave: str, bruto: dict, produto: dict) -> None:
    """309b: a Visita Mágica salva antes da correção dizia "até 1h" e não tinha "o que inclui".

    Só os dois produtos padrão, e só o que o time não mexeu: descrição EXATAMENTE a antiga vira a nova;
    `detalhes` AUSENTE (config salva antes da 309b) ganha o texto da arte — vazio salvo pela tela é
    escolha do time e fica vazio.
    """
    padrao = _PRODUTOS_PADRAO.get(chave)
    if padrao is None:
        return
    if produto["descricao"] == _DESCRICAO_VISITA_ANTIGA:
        produto["descricao"] = padrao["descricao"]
    if "detalhes" not in bruto:
        produto["detalhes"] = padrao["detalhes"]


def _migrar_309(data: dict) -> None:
    """Feature 309: garante `produtos` e `produtos_estimativa` e desfaz a troca 600 → 712 da 307.

    Roda DENTRO do ``try`` de `load()` (ver `_migrar_307`): nada indexa sem conferir o tipo. Os
    padrões só entram quando o bloco está ausente ou não é um dicionário; produto ou vaga malformados
    são descartados em silêncio — nunca viram preço 0. A inversa do Noel/Ajudante age só sobre quem
    ainda está EXATAMENTE em 712/423: valor editado pelo time não é tocado.
    """
    faixas = set((data.get("datas_especiais") or {}).keys())
    bloco = data.get("produtos")
    if not isinstance(bloco, dict):
        data["produtos"] = copy.deepcopy(DEFAULTS["produtos"])
    else:
        limpo: dict = {}
        for chave, produto in bloco.items():
            normalizado = _normalizar_produto(produto, faixas)
            if normalizado is not None and CHAVE_FAIXA_RE.fullmatch(str(chave)):
                limpo[str(chave)] = normalizado
                _migrar_309b(str(chave), produto, normalizado)
        data["produtos"] = limpo
    data["produtos_estimativa"] = _normalizar_estimativa(data.get("produtos_estimativa"))

    especiais = data.get("especiais")
    if isinstance(especiais, dict):
        if especiais.get("Papai Noel") == NOEL_712:
            especiais["Papai Noel"] = copy.deepcopy(DEFAULTS["especiais"]["Papai Noel"])
        if especiais.get("Ajudante do Noel") == AJUDANTE_423:
            especiais["Ajudante do Noel"] = copy.deepcopy(DEFAULTS["especiais"]["Ajudante do Noel"])


def _validar_vaga(pref: str, vaga, especiais: dict, erros: dict, avisos: list[str], rotulo_produto: str) -> dict | None:
    """Uma vaga limpa, ou ``None`` com os erros registrados (``<pref>.<campo>``)."""
    if not isinstance(vaga, dict):
        erros[pref] = "vaga inválida"
        return None
    tipo = vaga.get("tipo")
    if tipo not in TIPOS_DE_VAGA:
        erros[f"{pref}.tipo"] = f"tipo de vaga desconhecido: {tipo}"
        return None
    if tipo in LABEL_FIXO_POR_TIPO:
        label = LABEL_FIXO_POR_TIPO[tipo]
    else:
        label = str(vaga.get("label") or "").strip()
        if not label:
            erros[f"{pref}.label"] = "informe o nome da vaga"
        elif len(label) > 120:
            erros[f"{pref}.label"] = "nome com mais de 120 caracteres"
    cache = None
    if vaga.get("cache") is not None:
        cache = _dinheiro(vaga.get("cache"))
        if cache is None or cache <= 0:
            erros[f"{pref}.cache"] = f"cachê em R$ maior que zero e até {_DINHEIRO_MAX:,.0f}, ou vazio para usar a tabela".replace(",", ".")
    # `needs_makeup` só existe para especial/ator; nos demais o valor é ignorado (contrato).
    make = vaga.get("needs_makeup", False) if tipo in ("especial", "ator") else False
    if not isinstance(make, bool):
        erros[f"{pref}.needs_makeup"] = "verdadeiro ou falso"
        make = False
    if tipo == "especial" and label and label not in especiais:
        avisos.append(f'"{rotulo_produto}": a vaga "{label}" não está na tabela de preços e nasce sem teto.')
    return {
        "label": label,
        "tipo": tipo,
        "cache": cache,
        "needs_makeup": make if tipo in ("especial", "ator") else False,
    }


def _validar_produto(chave: str, produto, especiais: dict, faixas: set[str], erros: dict, avisos: list[str]) -> dict | None:
    pref = f"produtos.{chave}"
    if not CHAVE_FAIXA_RE.fullmatch(chave) or not isinstance(produto, dict):
        erros[pref] = "produto inválido"
        return None
    rotulo = str(produto.get("rotulo") or "").strip()
    if not rotulo:
        erros[f"{pref}.rotulo"] = "informe o rótulo"
    elif len(rotulo) > PRODUTO_ROTULO_MAX:
        erros[f"{pref}.rotulo"] = f"rótulo com mais de {PRODUTO_ROTULO_MAX} caracteres"
    descricao = _descricao_limpa(produto.get("descricao"))
    if len(descricao) > PRODUTO_DESCRICAO_MAX:
        erros[f"{pref}.descricao"] = f"descrição com mais de {PRODUTO_DESCRICAO_MAX} caracteres"
    detalhes = _nota_limpa(produto.get("detalhes"))
    if len(detalhes) > PRODUTO_DETALHES_MAX:
        erros[f"{pref}.detalhes"] = f"texto com mais de {PRODUTO_DETALHES_MAX} caracteres"
    for campo in ("ativo", "inclui_noturno"):
        if not isinstance(produto.get(campo, True), bool):
            erros[f"{pref}.{campo}"] = "verdadeiro ou falso"
    msg_preco = f"preço em R$ maior que zero e até {_DINHEIRO_MAX:,.0f}".replace(",", ".")
    preco = _dinheiro(produto.get("preco"))
    if preco is None or preco <= 0:
        erros[f"{pref}.preco"] = msg_preco
    por_faixa: dict = {}
    bruto = produto.get("por_faixa")
    if bruto is not None and not isinstance(bruto, dict):
        erros[f"{pref}.por_faixa"] = "faixas inválidas"
    for faixa_chave, val in (bruto or {}).items() if isinstance(bruto, dict) else []:
        if str(faixa_chave) not in faixas:
            avisos.append(f'"{rotulo or chave}": a faixa "{faixa_chave}" não existe mais — o preço dela foi descartado.')
            continue
        preco_faixa = _dinheiro(val.get("preco")) if isinstance(val, dict) else None
        if preco_faixa is None or preco_faixa <= 0:
            erros[f"{pref}.por_faixa.{faixa_chave}.preco"] = msg_preco
        else:
            por_faixa[str(faixa_chave)] = {"preco": preco_faixa}
    vagas_brutas = produto.get("vagas")
    vagas: list[dict] = []
    if not isinstance(vagas_brutas, list) or not 1 <= len(vagas_brutas) <= PRODUTO_VAGAS_MAX:
        erros[f"{pref}.vagas"] = f"de 1 a {PRODUTO_VAGAS_MAX} vagas"
    else:
        for i, vaga in enumerate(vagas_brutas):
            limpa = _validar_vaga(f"{pref}.vagas.{i}", vaga, especiais, erros, avisos, rotulo or chave)
            if limpa is not None:
                vagas.append(limpa)
    return {
        "rotulo": rotulo,
        "descricao": descricao,
        "detalhes": detalhes,
        "ativo": bool(produto.get("ativo", True)),
        "preco": preco,
        "por_faixa": por_faixa,
        "vagas": vagas,
        "inclui_noturno": bool(produto.get("inclui_noturno", True)),
    }


def validar_produtos(bloco, estimativa, especiais: dict, datas_especiais: dict) -> tuple[dict, dict | None, list[str]]:
    """Valida `produtos` (e `produtos_estimativa`, se vier) da tela; devolve as cópias limpas e avisos.

    Preço fixo errado é dinheiro ao vivo na calculadora — por isso cada campo tem regra e o erro nomeia
    o campo (``produtos.<chave>.<campo>`` / ``produtos.<chave>.vagas.<i>.<campo>`` /
    ``produtos_estimativa.<campo>``). Faixa que não existe mais em `por_faixa` NÃO é erro: é descartada
    com aviso (senão remover uma faixa travaria o Salvar). Label de especial fora da tabela também só
    avisa (a vaga nasce sem teto). ``estimativa`` ``None`` = não veio no corpo = manter a salva.

    Raises:
        SettingsValidationError: com ``fields`` por campo.
    """
    if not isinstance(bloco, dict):
        raise SettingsValidationError("Produtos de tabela inválidos.", {"produtos": "bloco inválido"})
    erros: dict = {}
    avisos: list[str] = []
    faixas = set((datas_especiais or {}).keys())
    limpo: dict = {}
    for chave, produto in bloco.items():
        limpa = _validar_produto(str(chave), produto, especiais, faixas, erros, avisos)
        if limpa is not None:
            limpo[str(chave)] = limpa
    estimativa_limpa = None
    if estimativa is not None:
        if not isinstance(estimativa, dict):
            erros["produtos_estimativa"] = "bloco inválido"
        else:
            fator = _dinheiro(estimativa.get("fator_cache"))
            if fator is None or fator <= 0:
                erros["produtos_estimativa.fator_cache"] = "fator maior que zero"
            markup = _markup_de_4([estimativa.get("markup")] * 4)
            if markup is None:
                erros["produtos_estimativa.markup"] = (
                    f"markup entre {MARKUP_FAIXA_MIN:g} e {MARKUP_FAIXA_MAX:g} (coeficiente)"
                )
            if not erros:
                estimativa_limpa = {"fator_cache": fator, "markup": markup[0]}
    if erros:
        raise SettingsValidationError("Produtos de tabela inválidos.", erros)
    return limpo, estimativa_limpa, avisos


def faixa_especial(event_date: str | None, settings: dict | None = None) -> dict | None:
    """Faixa de data especial em que a data do evento cai, ou ``None`` (feature 307).

    A comparação é por recorte de texto (``"AAAA-MM-DD"`` → ``"MM-DD"``), nunca por ``datetime``:
    a data é de parede, e fuso já virou o dia errado nesta casa. Data vazia, malformada ou fora de
    todas as faixas = ``None`` = conta de hoje. A primeira faixa que casar vence.

    Args:
        event_date: a data do payload/snapshot, ``"AAAA-MM-DD"`` ou vazia.
        settings: a configuração já carregada, para não reler o banco dentro de um cálculo.

    Returns:
        Cópia da faixa com a chave em ``"chave"`` (``rotulo``, ``dias``, ``markup``, ``cache``,
        ``coordenador``, ``piso``, ``nota_mensagem``), ou ``None``.
    """
    raw = (event_date or "").strip()
    if not _DATA_ISO_RE.fullmatch(raw):
        return None
    mes_dia = raw[5:]
    bloco = (settings if settings is not None else load()).get("datas_especiais") or {}
    for chave, faixa in bloco.items():
        if isinstance(faixa, dict) and mes_dia in (faixa.get("dias") or []):
            encontrada = copy.deepcopy(faixa)
            encontrada["chave"] = chave
            return encontrada
    return None


def load() -> dict:
    """Return current pricing config, falling back to DEFAULTS."""
    try:
        from app.models import SiteSetting
        setting = SiteSetting.query.get(1)
        if setting and setting.pricing_config:
            return _migrate(json.loads(setting.pricing_config))
    except Exception:
        logger.exception("Falha ao carregar pricing_config; usando preços DEFAULTS")
    return copy.deepcopy(DEFAULTS)


def save(data: dict) -> None:
    """Persist pricing config to the database."""
    from app import db
    from app.models import SiteSetting
    setting = SiteSetting.query.get(1)
    if not setting:
        setting = SiteSetting(id=1)
        db.session.add(setting)
    setting.pricing_config = json.dumps(data, ensure_ascii=False)
    db.session.commit()


def acrescimo_tipos_list() -> list:
    """Lista de tipos de acréscimo p/ os seletores (feature 100).

    Junta os tipos comuns configurados + ``BV`` + ``Outro`` (dedup, preservando ordem). BV e Outro estão
    sempre presentes; BV é protegido (regra financeira de repasse).
    """
    from app.constants import ACRESCIMO_TIPO_BV, ACRESCIMO_TIPO_OUTRO
    salvos = load().get("acrescimo_tipos") or []
    out: list[str] = []
    for t in [*salvos, ACRESCIMO_TIPO_BV, ACRESCIMO_TIPO_OUTRO]:
        t = (t or "").strip()
        if t and t not in out:
            out.append(t)
    return out


def especiais_list() -> list:
    """Return list of special character names."""
    return list(load()["especiais"].keys())


def especiais_com_show() -> set:
    """Return set of especial names that have show variants (derived from config)."""
    especiais = load()["especiais"]
    return {
        nome for nome, val in especiais.items()
        if isinstance(val, dict) and any(k in val for k in ("true", "false", "show", "none"))
    }


def especiais_com_cantor() -> set:
    """Return set of especial names that have cantor variants (derived from config)."""
    especiais = load()["especiais"]
    return {nome for nome, val in especiais.items() if isinstance(val, dict) and "cantor" in val}
