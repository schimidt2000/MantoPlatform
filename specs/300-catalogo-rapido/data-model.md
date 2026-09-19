# Modelo de dados (Phase 1) — Feature 300

**Nenhuma mudança de schema. Sem migration, sem coluna nova, sem entidade nova.** O que esta feature
muda é *quando* os dados que já existem são buscados — não o que eles são.

Este documento existe para registrar a estratégia de carga por endpoint e a armadilha que produziu
o problema, porque é isso que precisa continuar verdadeiro depois que alguém mexer aqui de novo.

## As entidades envolvidas (todas já existentes)

| Entidade | Onde | Volume no espelho |
|---|---|---|
| `CatalogItem` | `app/models.py:2101` | 458 (457 ativos) |
| `CatalogItemImage` | `app/models.py:2161` | 2.674 |
| `CatalogCharacter` | `app/models.py:2176` | 219 |
| `CatalogCategory` | `app/models.py:2092` | 39 |
| `FigurinoSheet` | `app/models.py:363` | 619 (588 ainda fora do catálogo) |

## Os relationships, e por que todos são lentos hoje

Todos declarados `lazy=True` — carregamento preguiçoso, uma consulta por acesso, por objeto:

| Relationship | Linha | Quem toca |
|---|---|---|
| `CatalogItem.images` | `:2135` | `cover_image` em toda listagem |
| `CatalogItem.characters` | `:2142` | `_item_summary` do gerenciador; laço dos avulsos em `list_catalog_characters` |
| `CatalogItem.categories` | `:2134` | `_item_summary` dos dois lados |
| `CatalogItem.figurino_sheet` | `:2133` | `_item_summary` do gerenciador |
| `CatalogItem.as_character` (backref) | `:2214-2219` | `_item_summary` do gerenciador, + `tema` deste |
| `CatalogCharacter.own_item` | `:2214` | `_character_summary` público |

### A armadilha que precisa continuar registrada

`CatalogItem.cover_image` (`app/models.py:2156-2158`) **não é uma coluna**: é uma property que
devolve `images[0]`.

```python
@property
def cover_image(self) -> "CatalogItemImage | None":
    return self.images[0] if self.images else None
```

Quem lê "pegar a capa" imagina uma leitura barata. Na verdade, pedir a capa **carrega a coleção
inteira de fotos daquele produto** — em média 5,8 fotos, até 17. É por isso que `images` entra no
carregamento antecipado mesmo nas telas que mostram uma imagem só, e é por isso que a listagem
custava 1.846 consultas para devolver 199 KB.

## A estratégia de carga, por endpoint

O princípio: **carregar de uma vez, para todos os itens, o que a serialização vai pedir item a
item.** Nenhuma consulta pode crescer com a quantidade de produtos.

| Endpoint | Carregar antecipadamente | Consultas hoje → meta |
|---|---|---|
| `GET /api/admin/catalogo` | `images`, `characters`, `categories`, `figurino_sheet`, `as_character` (+ `tema`) | 1.846 → 6 *(medido)* |
| `GET /api/admin/catalogo/personagens` | `characters` e `images` sobre o `CatalogItem.query.all()` da linha 363 | 474 → ≤ 10 |
| `GET /api/catalogo` | `categories`, `images` | 916 → 4 *(medido)* |
| `GET /api/catalogo/categorias` | `categories`, `images` | 1+N+1+C → ≤ 10 |
| `GET /api/catalogo/categoria/<slug>` | `categories`, `images` | 182 → 4 *(medido)* |
| `GET /api/catalogo/<slug>` | fora de escopo: já é limitado a um item + 6 relacionados | — |

### O caso da visão Personagens

`list_catalog_characters` (`app/admin/catalog_character_ops.py:344`) parece cara pelos três `.all()`
sem filtro do início — mas esses são **3 consultas ao todo**. As 474 medidas vêm do laço dos avulsos
(`:405-438`), onde `item.characters` é tocado uma vez por produto (`:406`) apenas como teste de
verdade/falso, e `item.cover_image` (`:417`) nos avulsos com ficha.

A correção é a mesma das outras: carregar `characters` e `images` junto com os itens da linha 363.
Não é preciso reescrever o laço nem mudar a forma do resultado.

## Invariantes que a feature preserva

1. **A resposta não muda.** Mesmas chaves, mesmos valores, mesma ordem, mesmos nulos — em todos os
   endpoints listados. É o que o verify compara contra uma referência capturada **no código da
   `main`**. As duas ordenações que dependiam do plano de consulta (nomes de categoria, sem
   `order_by`, e personagens empatados em `position`) são **explícitas por `id`**, o que reproduz a
   produção exatamente: 0 de 458 produtos mudam. Detalhe em `contracts/catalogo-listagens.md`.
2. **O tipo de um item continua sendo a presença de elenco** (`kind` = tema/avulso), derivado em
   serialização, não em coluna.
3. **A capa continua sendo a primeira foto** (`position` 0) — a ordem de `images` é significativa e
   o carregamento antecipado a preserva (o relationship já declara `order_by`).
4. **A identidade do personagem continua sendo a ficha de figurino**, não o nome.
5. **A URL guardada no banco continua sendo a do arquivo original.** Miniatura é escolha de quem
   desenha, nunca do que está gravado — nenhuma linha de `catalog_item_images.url` ou
   `catalog_characters.photo_url` é reescrita por esta feature.
