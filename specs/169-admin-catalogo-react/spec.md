# Feature Specification: Gestão de Catálogo (CRUD de produtos) em React

**Feature Branch**: `169-admin-catalogo-react`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Migrar a gestão de produtos do catálogo (`/admin/catalogo*`) do
blueprint `admin` para React + API JSON, fatia da User Story 6 (Cauda Administrativa) da
migração 144. Escopo: listar/filtrar produtos, criar categoria, criar produto, editar produto
(nome, descrição, tags, categorias, fotos com capa e reordenação), ativar/inativar, excluir.
Todas as rotas restritas a SUPERADMIN."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Listar e filtrar produtos do catálogo (Priority: P1)

Como Superadmin, preciso ver a lista de produtos do catálogo, com busca por nome e filtro por
categoria/status (ativo/inativo/todos), pela interface React.

**Why this priority**: é a tela de entrada do módulo — base para todas as outras ações.

**Independent Test**: abrir a lista em React, buscar por nome, filtrar por categoria e por
status, e conferir paridade com a tela antiga (`/admin/catalogo`) para os mesmos filtros.

**Acceptance Scenarios**:

1. **Given** um Superadmin autenticado, **When** ele abre a lista sem filtro, **Then** vê todos
   os produtos (ativos e inativos) ordenados por nome, com as categorias disponíveis para
   filtro.
2. **Given** o mesmo Superadmin, **When** ele busca por nome e/ou filtra por categoria/status,
   **Then** a lista é restrita de acordo, mesma regra de hoje.
3. **Given** um usuário sem papel Superadmin, **When** ele tenta acessar a tela ou a API
   diretamente, **Then** recebe 403.

---

### User Story 2 - Criar categoria e criar produto (Priority: P2)

Como Superadmin, preciso criar uma categoria nova (reaproveitando se já existir pelo nome) e
criar um produto novo com nome, descrição, tags, categorias e ao menos uma foto (com a foto de
capa definida).

**Why this priority**: é o fluxo de criação completo — depende da lista (US1) para navegar até
ele e é a base para a edição (US3).

**Independent Test**: criar uma categoria nova, criar um produto usando essa categoria, com
tags e 2+ fotos, definindo uma capa diferente da primeira foto enviada, e conferir que os dados
gravados (incluindo a posição das fotos) são idênticos aos que a tela antiga gravaria.

**Acceptance Scenarios**:

1. **Given** um Superadmin autenticado, **When** ele cria uma categoria com um nome já
   existente (mesmo slug), **Then** a categoria existente é reaproveitada, não duplicada.
2. **Given** o mesmo Superadmin, **When** ele cria um produto sem nome ou sem nenhuma foto,
   **Then** a API recusa (400) com mensagem por campo, sem apagar o que já foi preenchido.
3. **Given** um arquivo de foto fora dos formatos aceitos (JPG/PNG/WebP), **When** o produto é
   enviado, **Then** a API recusa (400) apontando o(s) arquivo(s) rejeitado(s).
4. **Given** um produto criado com 3 fotos, **When** nenhuma capa é escolhida explicitamente,
   **Then** a primeira foto enviada vira a capa (posição 0) — mesma regra de hoje.
5. **Given** tags digitadas com grafia diferente de uma tag já existente (ex.: "natal" vs.
   "Natal"), **When** o produto é salvo, **Then** a grafia já existente é reaproveitada, sem
   criar uma tag duplicada — mesma regra de hoje (`_normalize_tags`).

---

### User Story 3 - Editar produto: dados, categorias, tags e fotos (Priority: P3)

Como Superadmin, preciso editar um produto existente — nome, descrição, tags, categorias,
remover fotos, adicionar fotos novas, reordenar as fotos e trocar a capa.

**Why this priority**: é a ação mais completa e mais usada no dia a dia de manutenção do
catálogo — vem depois da criação por reaproveitar toda a mesma lógica de fotos.

**Independent Test**: editar um produto existente removendo uma foto, adicionando outra,
reordenando e trocando a capa, e conferir que o resultado final (conjunto e ordem das fotos)
bate com o que a tela antiga produziria para a mesma sequência de ações.

**Acceptance Scenarios**:

1. **Given** um produto com fotos existentes, **When** o Superadmin remove uma foto e não
   adiciona nenhuma nova, e restava mais de uma foto, **Then** a foto é removida (arquivo
   apagado do armazenamento) e as demais permanecem.
2. **Given** o mesmo produto, **When** a remoção deixaria o produto sem nenhuma foto (nenhuma
   restante e nenhuma nova), **Then** a API recusa (400) — produto precisa de ao menos uma
   foto.
3. **Given** um produto com 3 fotos, **When** o Superadmin reordena manualmente (move uma foto
   para outra posição), **Then** a nova ordem é persistida, com a foto de capa sempre na
   posição 0.
4. **Given** uma foto existente marcada como capa e removida na mesma edição, **When** o
   produto é salvo sem nova capa escolhida, **Then** a capa passa a ser a primeira foto
   restante — mesma regra de fallback de hoje.

---

### User Story 4 - Ativar/inativar e excluir produto (Priority: P4)

Como Superadmin, preciso ativar/inativar um produto sem apagar seus dados, e excluir
definitivamente um produto (com suas fotos) quando necessário.

**Why this priority**: são as ações mais pontuais e de menor uso — inativar é reversível e mais
comum; excluir é definitivo e mais raro.

**Independent Test**: inativar um produto ativo e reativá-lo; excluir um produto e confirmar
que os arquivos de foto são removidos do armazenamento junto com o registro.

**Acceptance Scenarios**:

1. **Given** um produto ativo, **When** o Superadmin o inativa, **Then** ele deixa de aparecer
   no catálogo público (fora do escopo desta fatia verificar o público, só o flag), mas
   continua existindo e editável no admin.
2. **Given** um produto (ativo ou inativo), **When** o Superadmin o exclui, **Then** o registro
   e todas as suas fotos (arquivos no armazenamento) são removidos definitivamente.

---

### Edge Cases

- Nome de categoria vazio → 400, mensagem de campo.
- Busca/filtro sem nenhum resultado → lista vazia, sem erro.
- Reimportação do catálogo (fatia 168, `/api/admin/importar-catalogo/start`) não interfere
  nesta fatia — dedupe por `wp_product_id`, produtos criados nativamente (sem esse id) nunca são
  tocados pela reimportação.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE expor a listagem/filtro de produtos (busca por nome, categoria,
  status) como endpoint JSON, restrito a SUPERADMIN.
- **FR-002**: O sistema DEVE expor a criação de categoria (reaproveitando por slug) como
  endpoint JSON.
- **FR-003**: O sistema DEVE expor a criação e a edição de produto (multipart, pois envolve
  arquivo) como endpoints JSON, reaproveitando exatamente as regras hoje existentes: validação
  de nome/foto obrigatórios, validação de extensão de foto, normalização de tags por slug,
  regra de capa (explícita → primeira nova → primeira restante), reordenação manual de fotos.
- **FR-004**: O sistema DEVE expor ativar/inativar e excluir produto como endpoints JSON,
  reaproveitando a remoção de arquivos de foto no armazenamento ao excluir.
- **FR-005**: Toda validação de erro DEVE retornar mensagem amigável em pt-BR, com campo
  específico quando aplicável, sem apagar os dados já preenchidos no formulário React.
- **FR-006**: O comportamento das rotas Jinja antigas (`/admin/catalogo*`) DEVE permanecer
  idêntico ao de antes desta fatia até serem desativadas.

### Key Entities

- **Produto do catálogo (CatalogItem)**: nome, slug, descrição, tags (JSON), categorias,
  status ativo; já existente.
- **Foto do produto (CatalogItemImage)**: url, posição (0 = capa); já existente.
- **Categoria (CatalogCategory)**: nome, slug; já existente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um Superadmin consegue listar, criar categoria, criar produto (com fotos/capa/
  tags/categorias), editar, ativar/inativar e excluir produtos inteiramente pela interface
  React, sem abrir a tela antiga.
- **SC-002**: O conjunto e a ordem final das fotos de um produto, após qualquer sequência de
  remoção/adição/reordenação/escolha de capa, é idêntico ao que a tela antiga produziria para a
  mesma sequência — verificado por paridade automatizada.
- **SC-003**: Nenhum endpoint desta fatia é acessível por um usuário sem papel Superadmin.

## Assumptions

- **Reordenação de fotos no React usa botões "mover para a esquerda/direita"**, não
  arrastar-e-soltar por ponteiro (como a feature 142 fez no catálogo público) — o contrato de
  backend (`photo_order`, lista de ids na ordem final) é o mesmo; a fatia usa uma interação mais
  simples no admin (uso interno, não é a vitrine pública) para reduzir escopo, sem perder a
  capacidade de reordenar.
- Valores e uploads seguem os mesmos limites/formatos de hoje (JPG/PNG/WebP); compressão de
  imagem (se houver) continua no `app.storage`/`app.catalogo.importer`, sem mudança.
