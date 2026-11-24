# Data model — Feature 360

Migration `f360a1b2c3d4` (`down_revision = "f353a1b2c3d4"`), aditiva: cria as duas tabelas, vazias.
`downgrade` derruba as duas (os dados da conferência se perdem; a leitura continua no arquivo).

## `catalog_conferencias` — `CatalogConferencia`

Uma linha por item do catálogo lido.

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | Integer PK | |
| `catalog_item_id` | Integer NOT NULL | FK `catalog_items.id` `ON DELETE CASCADE`; **UNIQUE** (`uq_catalog_conferencias_item`) — é a idempotência da carga |
| `tipo_lido` | String(10) NOT NULL | `tema` \| `dupla` \| `avulso` \| `generico` (CHECK) — o que a leitura propôs; nunca muda |
| `tipo` | String(10) NOT NULL | mesmo domínio (CHECK); nasce igual a `tipo_lido`; é o decidido |
| `nota` | Text NULL | nota do leitor, como veio |
| `acao` | Text NULL | ação proposta para item sem elenco, como veio |
| `grupo` | String(120) NULL | "grupo possível" (só exibição) |
| `ficha_sugerida_id` | Integer NULL | FK `figurino_sheets.id` `SET NULL` — sugerida pela leitura (avulso) |
| `ficha_id` | Integer NULL | FK `figurino_sheets.id` `SET NULL` — a decidida; nasce igual à sugerida; só vale com `tipo = avulso` |
| `observacao` | Text NULL | de quem confere; até 1000 caracteres |
| `lote` | String(10) NULL | leva da leitura: `piloto`, `01`…`27` |
| `conferido_em` | DateTime NULL | UTC; NULL = a conferir |
| `conferido_por_id` | Integer NULL | FK `users.id` `SET NULL` |
| `created_at`, `updated_at` | DateTime NOT NULL | UTC |

Relacionamentos (só deste lado, sem backref nos models existentes — research R3): `item`,
`ficha_sugerida`, `ficha`, `conferido_por`, `personagens` (`cascade="all, delete-orphan"`,
`order_by position, id`).

**Estados**: `a_conferir` (`conferido_em IS NULL`) ⇄ `conferido`. `conferir` exige, em `tema` e
`dupla`, ao menos um personagem com `decisao = criar` (FR-017). `reabrir` zera `conferido_em` e
`conferido_por_id` e preserva o resto. Conferido recusa toda escrita (409 `conferido`).

**"Sem leitura"** não é linha: é item da fila sem `catalog_conferencias`.

## `catalog_conferencia_personagens` — `CatalogConferenciaPersonagem`

Um personagem proposto (ou acrescentado) dentro da conferência de um item.

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | Integer PK | |
| `conferencia_id` | Integer NOT NULL | FK `catalog_conferencias.id` `ON DELETE CASCADE`; índice |
| `position` | Integer NOT NULL | ordem da leitura; acrescentado entra no fim |
| `origem` | String(10) NOT NULL | `leitura` \| `manual` (CHECK) |
| `nome_lido` | String(200) NULL | o que a leitura propôs; NULL em `manual` |
| `nome` | String(200) NOT NULL | o decidido; nasce igual a `nome_lido` |
| `imagem_id` | Integer NULL | FK `catalog_item_images.id` `SET NULL` — a foto da galeria escolhida pela leitura |
| `recorte` | Text NULL | JSON `[x, y, largura, altura]` em % da foto; lido pela property tolerante `recorte_list` (armadilha 11) |
| `foto_largura`, `foto_altura` | Integer NULL | pixels da foto original (proporção do recorte) |
| `ficha_sugerida_id` | Integer NULL | FK `figurino_sheets.id` `SET NULL` |
| `ficha_id` | Integer NULL | FK `figurino_sheets.id` `SET NULL`; nasce igual à sugerida |
| `aviso` | Text NULL | aviso do leitor, mais o que a carga acrescentar (foto ou ficha que sumiu) |
| `sem_foto_lido` | Boolean NOT NULL | a leitura (ou a carga) não tem foto utilizável |
| `sem_foto` | Boolean NOT NULL | decisão "criar sem foto"; nasce igual a `sem_foto_lido` |
| `decisao` | String(10) NOT NULL | `criar` \| `nao_criar` (CHECK); nasce `criar` |
| `observacao` | Text NULL | até 1000 caracteres |
| `created_at`, `updated_at` | DateTime NOT NULL | UTC |

**Tem foto** = `imagem_id` aponta para uma imagem existente **e** `recorte_list` é válido. Sem isso,
`sem_foto` não pode ser desmarcado (400). Personagem `manual` nunca tem foto.

**Excluir** só com `origem = manual`; o da leitura marca-se `nao_criar` (preserva o que a leitura viu).

## Validações (núcleo, `ConferenciaValidationError(field, message)`)

| Campo | Regra | Mensagem |
|---|---|---|
| `nome` | aparado, 1 a 200 caracteres | "Informe o nome do personagem." / "O nome pode ter até 200 caracteres." |
| `tipo` | um dos quatro | "Selecione um tipo válido." |
| `ficha_id` | nulo ou ficha existente | "Ficha de figurino não encontrada." |
| `ficha_id` do item | só com `tipo = avulso` | "Só item avulso tem ficha própria. Num tema, a ficha é de cada personagem." |
| `decisao` | `criar` \| `nao_criar` | "Selecione criar ou não criar." |
| `sem_foto = false` | exige foto utilizável | "Este personagem não tem foto na leitura." |
| `observacao` | até 1000 caracteres | "A observação pode ter até 1000 caracteres." |
| conferir tema/dupla | ≥ 1 personagem `criar` | "Um tema precisa de pelo menos um personagem. Mantenha um personagem ou altere o tipo do item." |

## Arquivo da leitura — `app/admin/dados/leitura_personagens.json`

```json
{"versao": 1, "gerado_em": "2026-11-24", "itens": [
  {"id": 700, "nome": "Star Wars", "tipo": "tema", "lote": "piloto", "nota": "…", "acao": null,
   "grupo": null, "ficha_id": null,
   "personagens": [
     {"nome": "Yoda", "foto": "8c47….jpg", "dims": [905, 1200], "recorte": [29, 23, 33, 60],
      "ficha_id": 415, "ficha_nome": "Yoda", "aviso": null, "sem_foto": false}
   ]}
]}
```

`nome` do item é só referência humana (a carga usa o `id`). `ficha_nome` serve ao aviso quando a ficha
não existe mais.

## O que NÃO muda

`catalog_items`, `catalog_characters`, `catalog_item_images`, `figurino_sheets`: nenhuma coluna nova,
nenhuma escrita desta feature (FR-014). O verify compara a contagem e o `max(id)` dessas tabelas antes
e depois.
