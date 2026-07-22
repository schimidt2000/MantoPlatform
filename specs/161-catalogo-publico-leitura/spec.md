# Feature Specification: Catálogo Público em React (Leitura)

**Feature Branch**: `161-catalogo-publico-leitura`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Encadear para a US5 (Superfícies Públicas — Catálogo, /cadastro, formulários, feedback) da migração React (144). Escopo real levantado no código: o Catálogo Público (`app/catalogo`, blueprint sem login, 6 templates fora de `base.html`) tem 5 telas — grade geral, grade por categoria, categorias, detalhe do produto (com galeria animada da feature 143) e lista de desejos (client-side via localStorage). Seguindo o padrão de toda a migração (agenda começou pela leitura na 145, talentos/figurino na 154, vendas na 156), a primeira fatia da US5 é a superfície mais isolada e sem dependência de autenticação: o Catálogo Público inteiro, só leitura — cadastro (`/cadastro`), formulários dinâmicos (`/f/*`) e feedback público ficam para fatias futuras da US5, cada uma com seu próprio ciclo de planejamento."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Navegar o catálogo e ver o detalhe de um produto (Priority: P1)

Como visitante anônimo (cliente em potencial, geralmente vindo de um link de WhatsApp), preciso
navegar a grade de personagens/shows do catálogo, filtrar por categoria e abrir o detalhe de um
item — com a galeria de fotos animada (cross-fade + altura suave, feature 143) — sem precisar de
login e sem nenhuma tela quebrar no celular.

**Why this priority**: é o fluxo principal do catálogo (95%+ do tráfego real) e a única parte
com valor de negócio imediato se entregue sozinha — ver a grade e abrir um produto já substitui
o uso diário da tela antiga.

**Independent Test**: um visitante anônimo abre a grade em React, filtra por uma categoria, abre
o detalhe de um produto e vê a galeria com as mesmas fotos/descrição da tela antiga, incluindo a
transição de foto (cross-fade) e os produtos relacionados — tudo em viewport 320–430px sem
quebrar.

**Acceptance Scenarios**:

1. **Given** o catálogo público em React, **When** um visitante abre a grade geral, **Then** vê
   todos os itens ativos (`is_active`), ordenados por nome, com foto de capa, nome e categorias —
   mesmos itens e ordem da tela antiga.
2. **Given** a grade geral, **When** o visitante usa a busca por texto (nome/tags/categoria) ou
   clica numa categoria no filtro lateral, **Then** a lista é filtrada no próprio navegador (sem
   nova requisição), igual ao comportamento atual.
3. **Given** a grade de categorias (`/catalogo/categorias`), **When** o visitante abre essa tela,
   **Then** vê só as categorias com pelo menos um item ativo, cada uma com contagem e foto
   representativa.
4. **Given** uma categoria específica (`/catalogo/categoria/<slug>`), **When** o visitante abre a
   URL, **Then** vê os itens ativos daquela categoria; se a categoria não existir ou não tiver
   nenhum item ativo, vê uma página de "não encontrado" amigável (paridade com o 404 atual).
5. **Given** o detalhe de um produto, **When** o visitante troca de foto na galeria, **Then** a
   transição é a mesma recriada com Framer Motion (cross-fade + altura animada, feature 143),
   respeitando `prefers-reduced-motion` (sem animação se o sistema pedir).
6. **Given** o detalhe de um produto, **When** a página carrega, **Then** mostra nome, descrição,
   categorias e até 6 produtos relacionados (mesma categoria), com link para cada um.
7. **Given** um slug de produto inexistente ou inativo, **When** o visitante acessa a URL,
   **Then** vê a página de "não encontrado" (paridade com o 404 atual).
8. **Given** um link de catálogo compartilhado (ex.: WhatsApp), **When** um serviço externo gera
   a prévia do link (Open Graph), **Then** a prévia continua funcionando — ver Assumptions sobre
   como isso é preservado durante esta fatia.

---

### User Story 2 - Favoritar itens e ver a lista de desejos (Priority: P2)

Como visitante anônimo, preciso favoritar produtos enquanto navego e depois ver minha lista de
desejos reunida, com um botão para enviar a lista por WhatsApp.

**Why this priority**: incrementa a experiência de navegação (US1), mas não é o caminho crítico
— um visitante consegue ver e escolher produtos sem nunca abrir a lista de desejos.

**Independent Test**: favoritar 2+ produtos na grade/detalhe, abrir `/catalogo/lista-desejos` e
ver os itens favoritados persistidos (mesma aba, reload da página), com o link de WhatsApp
correto.

**Acceptance Scenarios**:

1. **Given** um produto na grade ou no detalhe, **When** o visitante clica em "favoritar",
   **Then** o item é salvo no `localStorage` do navegador (sem chamada ao servidor) e o botão
   reflete o novo estado imediatamente.
2. **Given** itens já favoritados, **When** o visitante abre `/catalogo/lista-desejos`, **Then**
   vê a lista completa, montada a partir do `localStorage`, com o número de WhatsApp comercial de
   destino já configurado (mesma regra de hoje).
3. **Given** a lista de desejos vazia, **When** o visitante abre a tela, **Then** vê um estado
   vazio amigável (não uma lista/erro em branco).

---

### Edge Cases

- Nenhum item ativo no catálogo → grade geral mostra estado vazio amigável, não uma grade
  quebrada.
- Item sem nenhuma foto (`images` vazio) → aparece com um placeholder visual, não com erro de
  imagem quebrada — mesmo comportamento de hoje.
- Categoria com nome/slug igual a outra removida (reimportação do WordPress) → segue a mesma
  regra de dedupe por `slug` já existente no modelo, sem lógica nova nesta fatia.
- Navegação direto para uma foto específica via deep link não existe hoje (galeria é só client
  state) — fora de escopo, sem mudança.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE expor a grade geral do catálogo (itens ativos, ordenados por nome,
  com contagem de itens por categoria) como endpoint JSON, reaproveitando exatamente a mesma
  consulta e regras de hoje (`CatalogItem.filter_by(is_active=True)`), sem duplicar lógica.
- **FR-002**: O sistema DEVE expor a grade de categorias (só categorias com item ativo, com
  contagem e foto de capa) como endpoint JSON.
- **FR-003**: O sistema DEVE expor os itens ativos de uma categoria por slug como endpoint JSON,
  retornando "não encontrado" quando o slug não existir ou não tiver item ativo — paridade com o
  404 da tela antiga.
- **FR-004**: O sistema DEVE expor o detalhe de um item por slug (nome, descrição, categorias,
  todas as fotos ordenadas por posição, até 6 relacionados da mesma categoria) como endpoint
  JSON, retornando "não encontrado" para slug inexistente ou inativo.
- **FR-005**: Todos os endpoints desta fatia DEVEM permanecer acessíveis sem autenticação (mesmo
  comportamento hoje do blueprint `catalogo_bp`), e DEVEM herdar o cabeçalho
  `X-Robots-Tag: noindex` já aplicado globalmente a toda resposta do app.
- **FR-006**: A tela de detalhe do produto em React DEVE recriar a transição de galeria da
  feature 143 (cross-fade + altura animada ao trocar de foto) usando Framer Motion, respeitando
  `prefers-reduced-motion` (Princípio IX da constituição).
- **FR-007**: A lista de desejos DEVE continuar 100% client-side via `localStorage` — nenhuma
  chamada ao servidor para favoritar/desfavoritar ou montar a lista (sem mudança de arquitetura
  nesta fatia, conforme US5 na spec 144).
- **FR-008**: As 5 telas do catálogo público em React DEVEM manter identidade visual própria
  (layout fora do shell/nav do painel interno), reaproveitando o design já validado nas features
  139–143 — não herdar o shell do app interno (FR-007 da spec 144).
- **FR-009**: O comportamento das rotas antigas (Jinja, `/catalogo/*`) DEVE permanecer idêntico
  ao de antes desta fatia, incluindo as tags Open Graph (`og:title`, `og:description`,
  `og:image`) na página de detalhe — sem regressão nas prévias de link já compartilhadas.

### Key Entities

- **Item de catálogo (CatalogItem)**: já existente; esta fatia só lê campos já existentes (nome,
  slug, descrição, tags, categorias, fotos) — nenhum campo novo.
- **Categoria de catálogo (CatalogCategory)**: já existente; leitura de nome/slug.
- **Foto do item (CatalogItemImage)**: já existente; leitura de URL e posição (posição 0 = capa).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um visitante anônimo consegue navegar a grade, filtrar por categoria e ver o
  detalhe completo de um produto (com galeria animada) inteiramente pela tela React, sem abrir a
  tela antiga.
- **SC-002**: Os itens, fotos, categorias e relacionados mostrados em React são idênticos aos da
  tela antiga para os mesmos dados — verificado por paridade automatizada.
- **SC-003**: Nenhuma tela do catálogo quebra em viewport 320–430px (Princípio VIII).
- **SC-004**: Links de catálogo compartilhados externamente continuam gerando prévia (Open
  Graph) correta após esta fatia.

## Assumptions

- Esta fatia é só leitura — nenhuma ação de escrita (favoritar é client-side, não é escrita no
  servidor).
- **Open Graph / prévia de link continua servida pela rota Jinja existente**: como o React é uma
  SPA (renderização client-side), robôs de prévia de link (WhatsApp, etc.) não executam
  JavaScript e não veriam tags `og:*` dinâmicas. Nesta fatia, a rota Jinja `/catalogo/<slug>`
  **não é desligada** — continua no ar em paralelo (mesmo padrão strangler-fig de toda a
  migração) especificamente para preservar as prévias de link; a troca de qual rota fica
  publicamente linkada (Jinja com OG vs. React puro vs. uma solução de pré-renderização) é uma
  decisão explícita de fatia futura, não desta.
- Ficam explicitamente fora desta fatia (fatias futuras da US5): `/cadastro` público, formulário
  dinâmico `/f/pre-contrato` e `/f/corporativo` (componente-fábrica dirigido por
  `FormFieldDefinition`), e feedback público por token (`feedback/public.html`). Cada uma é
  isolada e independente o suficiente para merecer seu próprio ciclo `/speckit-plan`, mesmo
  padrão adotado pela Agenda (145→153), Talentos/Figurino (154→155) e Financeiro/Vendas
  (156→160).
- Fotos do catálogo continuam servidas pela rota existente `/catalogo/midia/<filename>` (fora do
  `/uploads` autenticado) — sem mudança nesta fatia.
