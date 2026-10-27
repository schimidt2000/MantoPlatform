# Modelo de dados — Feature 320

Nenhuma tabela, coluna ou migration. O "dado" desta feature é o estado de navegação, que mora em
três lugares do navegador:

## 1. Endereço da lista (fonte de verdade de busca e filtros)

Parâmetro ausente = valor padrão (endereço limpo na primeira visita). Escrita sempre com `replace`.

### Catálogo público — `/catalogo/` (dev: `/`)

| Parâmetro | Valor | Padrão |
|---|---|---|
| `q` | texto da busca | vazio |
| `categoria` | nome da categoria (é o que `item.categories` traz) | todas |

### Gerenciador — `/admin/catalogo`

| Parâmetro | Valor | Padrão |
|---|---|---|
| `q` | texto da busca | vazio |
| `categoria` | id da categoria | todas |
| `situacao` | `ativo` \| `inativo` | todas (`todos` interno) |
| `visao` | `cards` \| `arvore` \| `personagens` | o último escolhido (`localStorage` `manto_admin_catalogo_view`, como hoje) |

### Banco de talentos — `/talents`

| Parâmetro | Valor | Padrão |
|---|---|---|
| `status` | `pending` | ativos (já usado por `TalentDetailPage`) |
| `aba` | `emails` (fila de e-mails com problema) | diretório |
| `q` | busca | vazio |
| `pagina` | inteiro ≥ 2 | 1 |
| `ja_trabalhou` | `1` | não |
| `language`, `race`, `top`, `bottom`, `shoe`, `passport`, `tag` | repetidos (`?tag=a&tag=b`) | vazio |
| `character` | texto | vazio |
| `height_op` / `height_value` | `gte`\|`lte`\|`eq` / número | `gte` / vazio |

Nomes dos filtros avançados = nomes dos parâmetros da API (`lib/talents.ts`), para não haver
tradução.

## 2. `sessionStorage` — posição de rolagem

Chave única `manto:rolagem` → objeto `{ [location.key]: scrollY }`, no máximo 50 entradas (as
mais antigas saem). Por aba do navegador; sobrevive a recarregar; some ao fechar a aba.

## 3. `history.state` (via `state` do React Router)

| Marca | Quem põe | Quem lê |
|---|---|---|
| `daLista: true` | links da lista para o detalhe | `useVoltarParaLista` (decide `navigate(-1)` × link) |
| `arquivoAberto: <número>` | `ArquivoViewerProvider` ao abrir | o próprio provedor (fecha quando a marca sai) |

Transições do visualizador: **fechado** → (Ver) → **aberto** [PUSH com marca] → (Voltar/Esc/fora →
`navigate(-1)` | voltar do navegador) → **fechado**. Recarregar com a marca → fechado + `replace`
sem a marca.
