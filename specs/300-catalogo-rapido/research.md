# Pesquisa (Phase 0) — Feature 300, catálogo rápido

Todas as decisões abaixo foram tomadas **contra medição**, não contra intuição. Os números vêm do
espelho `manto_local` em 16/09/2026 (458 produtos, 457 ativos, 219 personagens, 2.674 fotos), com
um ouvinte de SQL contando as consultas, antes de qualquer alteração em código de produção.

## O mapa do custo, medido

| Caminho | Consultas hoje | Tempo | De onde vêm |
|---|---|---|---|
| `GET /api/admin/catalogo` | **1.846** | 1,56 s | 4 a 6 relationships por item em `_item_summary` |
| `GET /api/admin/catalogo/personagens` | **474** | 854 ms | `item.characters` no laço dos avulsos, 1 por item |
| `GET /api/catalogo` (vitrine) | **916** | 661 ms | `item.categories` + `item.images` por item |
| `GET /api/catalogo/categoria/<slug>` (maior) | **182** | 124 ms | idem, dentro de `_item_summary` público |

A aba **Personagens** do gerenciador dispara os dois primeiros: **2.320 consultas** numa abertura.

---

## R1 — `selectinload`, não `joinedload`

**Decisão**: carregamento antecipado com `selectinload` nos relationships que os serializadores
tocam. No gerenciador: `characters`, `images`, `categories`, `figurino_sheet` e `as_character`
(+ `tema` deste). Na vitrine: `categories` e `images`. Em `list_catalog_characters`: `characters` e
`images` sobre o `CatalogItem.query.all()`.

**Justificativa**: medido — **1.846 → 6** e **916 → 4** consultas, com a resposta **byte a byte
idêntica**. `selectinload` emite uma consulta extra por relationship, com `IN`, e preserva a forma
do resultado.

**Alternativas rejeitadas**:
- **`joinedload`**: em coleção produz produto cartesiano. Com média de 5,8 fotos por produto e o
  elenco junto, o JOIN devolveria milhares de linhas repetidas para montar os mesmos 458 objetos —
  troca de um problema por outro.
- **`lazy="selectin"` no próprio modelo** (`app/models.py`): resolveria em uma linha, mas mudaria o
  comportamento de **todo** o sistema — inclusive telas que só precisam de um item e todos os
  caminhos de escrita. Princípio IV: não mexer no que funciona; a otimização fica no ponto que
  precisa dela.
- **Paginação**: rejeitada por medição (o catálogo inteiro sai em menos de 0,11 s depois de R1) e
  por regra de produto — a visão Personagens precisa da lista inteira para o "usar em outro tema".

**Armadilha registrada**: `CatalogItem.cover_image` é uma *property* que devolve `images[0]`. Pedir
só a capa carrega a coleção inteira de fotos daquele produto — por isso `images` entra no
carregamento antecipado mesmo onde a tela mostra uma imagem só.

---

## R2 — A largura da miniatura

**Decisão**: **128** para as caixas de 32 a 64 px do gerenciador. A vitrine mantém as larguras que a
feature 270 já definiu para cada grade (320/480/640 com `srcset`), e as duas lacunas novas seguem o
mesmo critério: 640 + `srcset` na grade de categorias (card de ~270 px), 128 na lista de desejos
(quadrado de 64 px).

**Justificativa**: a allowlist é fechada em `(128, 320, 480, 640)` — largura fora dela é 404 e não
grava nada. 128 cobre 64 px em tela de densidade 2×, e a 270 mediu que custa menos de 10% dos bytes
do original. O `flask warm-thumbnails` já aquece exatamente essas larguras para o catálogo.

**Alternativa rejeitada**: gerar uma variante de 64 px. Mudaria a allowlist dos dois lados e
invalidaria cache existente para economizar bytes que já são poucos.

---

## R3 — Como as imagens deixam de ser pedidas todas de uma vez

**Decisão**: onde a caixa é avatar ou miniatura, trocar o `<img>` cru por `AvatarThumb`/`Foto` do
`@manto/ui`; onde o `<img>` continuar cru, acrescentar `loading="lazy"`.

**Justificativa**: Princípio I (reutilizar antes de criar) e XII.2. `<Foto>` já resolve o caso da
foto que está no banco mas sumiu do disco — que existe de verdade aqui: a recuperação pós-Railway
deixou 66 fotos ausentes, 9 delas capa de item ativo. `AvatarThumb` já traz `loading="lazy"`.

**Alternativa rejeitada**: `IntersectionObserver` próprio. O atributo nativo resolve, não custa
nada e não adiciona código para manter.

---

## R4 — As categorias do formulário de edição

**Decisão**: acrescentar `GET /api/admin/catalogo/categorias`, no caminho que **já existe** para
`POST` (criar categoria), com o mesmo gate SUPERADMIN.

**Justificativa**: hoje abrir a edição de um produto baixa a listagem inteira — 458 produtos com
todos os personagens, 199 KB — para desenhar 39 opções de um seletor. Depois de R1 isso deixa de
ser *lento* (6 consultas), mas continua sendo 199 KB por abertura, o que pesa em 4G. São ~10 linhas
reusando caminho e gate existentes.

**Alternativas rejeitadas**:
- **Aproveitar o cache do TanStack Query**: funciona só quando a pessoa chegou pela lista; link
  direto ou recarregar a página refaz a busca inteira.
- **`?only=categories` na listagem**: um parâmetro que muda a *forma* da resposta é pior de manter
  que um caminho próprio, e contraria o contrato de que a listagem devolve sempre a mesma coisa.
- **Reusar o endpoint público `/api/catalogo/categorias`**: forma diferente e devolve só categorias
  **com item ativo** — o formulário precisa de todas.

**Consequência assumida**: é endpoint novo, então entra na tabela de `docs/01` §4.3 e na seção RBAC
da spec (já ajustada — Princípio VII, a spec muda antes do código).

---

## R5 — A pausa da busca de personagem

**Decisão**: 300 ms de pausa, mantendo o mínimo de **2 caracteres** de hoje, com
`placeholderData: keepPreviousData`.

**Justificativa**: Princípio XII.5 exige busca preditiva com pausa. 300 ms é o que o
`AgruparEventosDialog` já usa neste repositório (Princípio I). Manter 2 caracteres é deliberado: a
tela não passa a exigir mais do que exigia. `keepPreviousData` é o padrão que `agenda.ts`,
`formulariosAdmin.ts` e a Home já seguem, e evita o piscar de esqueleto a cada refinamento.

---

## R6 — O aquecimento das miniaturas

**Decisão**: `flask warm-thumbnails` rodado por SSH no `manto-backend` logo após o deploy, com
`MANTO_SEM_THREADS=1` e **sem push na fila**.

**Justificativa**: o cache está frio (9 arquivos gerados em 128 px). A geração é sob demanda e
auto-curável, mas sem aquecimento a primeira pessoa a abrir a tela paga a geração de centenas de
miniaturas **dentro de uma thread do gunicorn** — a assinatura exata do incidente da feature 263,
em que requisição presa segurando thread derrubou a produção. Um deploy troca o contêiner e mataria
a rodada, por isso a exigência de fila vazia. O comando só grava arquivo de imagem em disco; não
escreve no banco.

**Correção (18/09/2026, revisão pré-deploy):** a premissa desta decisão estava errada. Os "9
arquivos" foram medidos no **espelho local** e generalizados para a produção sem medir. Conferido
por SSH, somente leitura: a produção tinha **2.628 variantes de 128 px para 2.715 originais (97%)**
e ~460 em cada largura de capa — o `warm-thumbnails` da 270 já tinha aquecido. O risco do incidente
da 263 não existe lá, e o aquecimento vira higiene opcional. A lição fica: número de cache do
espelho não diz nada sobre o disco da produção, que tem vida própria.

**Segunda correção (18/09/2026, segunda revisão):** a primeira correção também errou, por outro
caminho. Os 2.628 eram contagem agregada da **galeria**; as **fotos de personagem** nunca tinham
sido aquecidas a 128. Das 243 da produção, só 44 existem no disco (199 perdidas na migração do
Railway, 404 sem gerar nada); as 44 foram aquecidas antes do deploy, uma por vez, pela rota
pública. Contagem agregada não diz QUAIS arquivos estão lá.

---

## R7 — O critério do `verify_300.py`

**Decisão**: o verify afere **contagem de consultas ao banco** com ouvinte de SQL, com teto um pouco
acima do medido — nunca tempo de relógio.

**Justificativa**: o relógio varia com a máquina e com a carga, e transformaria o verify numa fonte
de falso alarme que a equipe aprenderia a ignorar. A contagem é determinística e é exatamente a
regressão que se quer impedir: se alguém remover o carregamento antecipado, ela dispara. Um teto
colado no número exato de hoje quebraria a cada acréscimo legítimo de campo.
