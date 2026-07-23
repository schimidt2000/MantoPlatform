# Data Model: Transporte explícito por dias no EducaManto + calculadora em React

Sem migração de banco nesta feature — todas as entidades já existem. Este documento descreve as
entidades existentes reusadas e os formatos de resposta (DTOs) novos que a API expõe para a tela
React.

## Entidades existentes (sem mudança de schema)

### EducaMantoPackage (`app/models.py:1093`)

Pacote de precificação (ex.: "Uma Aventura Animal"). Campos relevantes para o cálculo:
`margin_1s`, `margin_2s`, `margin_1s_days`, `margin_2s_days`, `discount_days`, `discount_pct`,
`ensemble_1s/_2s/_1s_days/_2s_days`. Relação `items` (`EducaMantoItem`, ordenados por
`sort_order`). Já expõe `to_dict()` — reusado como está pelo endpoint de listagem.

### EducaMantoItem (`app/models.py:1140`)

Linha de custo dentro de um pacote: `name`, `qty`, `cost_1s`, `cost_2s`, `cost_1s_days`,
`cost_2s_days`, `ensemble_add` (quanto a quantidade cresce por unidade de ensemble). Já expõe
`to_dict()` — sem mudança.

### Configuração de transporte (existente, via `app.orcamento.settings.load()["transporte"]`)

Dict com `van_com_carretinha`, `van_sem_carretinha`, `carro_por_km`, `afsp_divisor`,
`ashow_divisor`, `ashow_min_km` — mesma fonte já usada pela feature 076 e pelo orçamento. Sem
mudança nesta feature.

## Novo módulo de regra de negócio: `app/educamanto/pricing_ops.py`

Funções puras (sem `flask.request`), com type hints e docstrings, usadas apenas pelos novos
endpoints de API (o Jinja legado continua com sua réplica em JS, sem chamar este módulo):

- `calcular_transporte(tipo: Literal["van", "carro"], carretinha: bool, num_carros: int,
  km_ida: float, pessoas: int, dias_total: int) -> TransporteResultado` — reusa
  `calcular_van`/`calcular_carro` de `app.orcamento.transport` para o valor de **uma viagem**, depois
  multiplica pelo `max(dias_total, 1)`.
- `calcular_pacote(package: EducaMantoPackage, d1: int, d2: int, ensemble: int,
  acrescimo: float, transporte: TransporteResultado | None) -> PacoteCalculado` — reproduz em Python
  a mesma lógica hoje só em JS (`valoresPacote`/`effectiveItemsFor`/`calcular` do template): itens
  efetivos com ensemble, cenário (1 sessão / 2 sessões / multi-dia), custo bruto, valor base, desconto
  por dias, cap do acréscimo ao valor original, arredondamento para múltiplo de 100 (`ceil100`),
  soma do transporte (já multiplicado) ao final.

### Formato de resposta — `TransporteResultado` (DTO, não é tabela)

| Campo | Tipo | Descrição |
|---|---|---|
| `vt` | float | Valor da tarifa por km (ida e volta) de **uma** viagem |
| `afsp` | float | Adicional por pessoa (rateio) de **uma** viagem |
| `valor_viagem` | float | `vt + afsp` — total de uma única viagem |
| `dias` | int | Número de dias usado na multiplicação (`d1 + d2`, mínimo 1) |
| `total` | float | `valor_viagem * dias` — valor somado ao total do pacote |
| `label` | string | Descrição do meio de transporte (ex.: "Van c/ carretinha") |
| `km_total` | float | Km ida e volta |
| `pessoas` | int | Número de pessoas usado no adicional |

### Formato de resposta — `PacoteCalculado` (DTO, não é tabela)

| Campo | Tipo | Descrição |
|---|---|---|
| `scenario` | string | Rótulo do cenário (ex.: "2d×1 sessão + 1d×2 sessões") |
| `item_rows` | list | Detalhamento por item (nome, qtd, custo unit./total, preço de venda) |
| `raw_cost` | float | Custo bruto total (soma dos itens, sem margem) |
| `valor_base` | float | Custo × margem, antes do desconto por dias |
| `desconto_aplicado` | bool | Se o desconto por dias entrou |
| `desconto` | float | Valor do desconto aplicado (`valor_base - valor_sem_desconto_com_acrescimo`) |
| `transporte` | `TransporteResultado \| null` | Detalhamento do transporte (já com multiplicador) |
| `valor_final_sem_nota` | float | Valor final "sem nota", já somado o transporte |
| `valor_final_com_nota` | float | Valor final "com nota" (gross-up), já somado o transporte |

## Fluxo de dados (tela React)

```text
EducaMantoCalculadoraPage
  → GET /api/educamanto/packages           (lista de pacotes, 1x ao entrar na tela)
  → GET /api/educamanto/distancia?endereco= (sob demanda, botão "Calcular distância")
  → POST /api/educamanto/calcular           (debounced, a cada mudança relevante de input:
                                              pacote, dias, ensemble, acréscimo, tipo/carretinha/
                                              carros/pessoas — só se já houver km calculado)
```
