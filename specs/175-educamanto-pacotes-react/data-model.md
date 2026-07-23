# Data Model: EducaManto — Pacotes e Conteúdos em React

Nenhum modelo novo, nenhuma migration. Os 3 models já existem em `app/models.py` (linhas
1093-1187) e cobrem 100% dos requisitos do spec.

## EducaMantoPackage

Pacote educacional (ex.: "Uma Aventura Animal").

| Campo | Tipo | Regra |
|---|---|---|
| `name` | string(200) | obrigatório |
| `margin_1s` / `margin_2s` | float | multiplicador de margem por cenário (1/2 sessões) |
| `margin_1s_days` / `margin_2s_days` | float | multiplicador de margem por cenário multi-dia |
| `discount_days` | int | a partir de quantos dias totais o desconto passa a valer |
| `discount_pct` | float (0-1) | percentual de desconto aplicado acima de `discount_days` |
| `commission_rate` | float (0-1) | comissão default do pacote |
| `ensemble_1s`/`ensemble_2s`/`ensemble_1s_days`/`ensemble_2s_days` | float | cachê do figurante extra por cenário |
| `items` | relação 1:N | `EducaMantoItem`, ordenados por `sort_order`, `cascade="all, delete-orphan"` |

Formulário React envia margens/percentuais como número (ex. `5` para 5%, convertido para `0.05`
no backend — mesma regra hoje aplicada em `create_package`/`edit_package`).

## EducaMantoItem

Linha de custo/conteúdo dentro de um pacote.

| Campo | Tipo | Regra |
|---|---|---|
| `name` | string(200) | obrigatório, linhas com nome vazio são descartadas (mesma regra do `_parse_items_from_form`) |
| `qty` | int | quantidade base |
| `cost_1s`/`cost_2s`/`cost_1s_days`/`cost_2s_days` | float | custo unitário por cenário |
| `sort_order` | int | ordem de exibição — reordenação via botões (padrão feature 169), sem drag-and-drop |
| `ensemble_add` | int (0/1) | se o item cresce proporcionalmente ao ensemble |

Ao editar um pacote, a API substitui a lista de itens inteira (delete + recria), mesma regra do
`edit_package` legado — não há update parcial de item isolado.

## EducaMantoQuote

Orçamento gerado — histórico.

| Campo | Tipo | Regra |
|---|---|---|
| `user_id` | FK User | quem gerou |
| `client_name` | string(200), nullable | opcional |
| `packages_label` | string(300) | rótulo (nomes dos pacotes), gerado no momento da criação |
| `snapshot` | text (JSON) | congelado — nunca recalculado a partir do pacote atual |
| `created_at` | datetime | usado para ordenação e filtro de período |

`snapshot` já é montado por `_build_snapshot()` (a mover para `package_ops.py` ou manter em
`routes.py`/reusar via API — ver contracts). Reabrir o PDF (`orcamento_pdf`) sempre lê o
snapshot, nunca o pacote vivo — é o mecanismo que garante SC-003 do spec.

## Sem mudança de schema

Nenhum campo novo é necessário para nenhuma das 3 user stories do spec. Toda a superfície de
dados já existe; o trabalho desta feature é 100% de camada de apresentação (API + React) e
extração de núcleo de negócio (`package_ops.py`).
