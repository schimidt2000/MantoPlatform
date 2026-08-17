"""Pricing configuration for the quote calculator.

Settings are persisted in SiteSetting.pricing_config (JSON TEXT column).
Falls back to DEFAULTS when no configuration has been saved yet.
"""
import copy
import json
import logging

logger = logging.getLogger(__name__)

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

    return data


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
