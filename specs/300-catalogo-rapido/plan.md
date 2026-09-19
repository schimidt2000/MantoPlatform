# Plano de implementação: Catálogo rápido

**Branch**: `300-catalogo-rapido` | **Data**: 2026-09-16 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/300-catalogo-rapido/spec.md`

**Nota**: preenchido pelo `/speckit-plan`. A constituição (`.specify/memory/constitution.md`,
v3.0.0) é lida em tempo de execução — o Constitution Check abaixo é o que ela cobra.

## Resumo

A tela de gerenciamento do catálogo demora porque faz **duas coisas caras e independentes**: pede ao
banco uma consulta por produto (1.846 numa abertura; 2.320 na aba Personagens) e baixa **458 fotos
em tamanho original** para desenhá-las em quadrados de 32 a 64 px. A vitrine pública tem o mesmo
defeito (916 consultas) e o dono decidiu tratar as duas no mesmo deploy.

A abordagem, escolhida por medição e não por intuição (`research.md`): **carregamento antecipado
com `selectinload`** nos relationships que os serializadores tocam — medido 1.846→6 e 916→4, com a
resposta byte a byte idêntica — e **pedir a miniatura que já existe desde a feature 270**
(`assetUrl(url, { largura })`), com as imagens fora da tela adiadas. Nada no banco muda: sem
migration, sem coluna, sem campo novo na resposta. O único acréscimo de superfície é um `GET` no
caminho `/api/admin/catalogo/categorias`, que já existe para `POST`, para o formulário de edição
parar de baixar o catálogo inteiro só para desenhar um seletor.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: Flask, SQLAlchemy (`selectinload` de `sqlalchemy.orm`); React, TanStack
Query, Tailwind CSS, `@manto/ui` (`AvatarThumb`, `Foto`), `@manto/api-client`
(`assetUrl`/`assetSrcSet`). **Nenhuma dependência nova.**

**Armazenamento**: PostgreSQL — produção no Render (`manto-postgres`); verificação contra a cópia
`manto_local`. Fotos e miniaturas no disco persistente do `manto-backend` (`catalog_photos` e o
cache `catalog_thumbs`, `app/catalogo/og_ops.py`)

**Verificação**: `specs/300-catalogo-rapido/verify_300.py` contra `manto_local`, aferindo
**contagem de consultas** por ouvinte de SQL (R7); `cd frontend && npm run typecheck` (três SPAs);
telas abertas no Browser pane; vitrine em viewport mobile

**Plataforma-alvo**: web — Render (Flask API JSON + 3 SPAs servidas por `frontend/server.js`);
gerenciador em desktop, vitrine em smartphone

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: consultas ao banco que **não crescem com o volume** — teto de 10 por
listagem (medido: 6 no gerenciador, 4 na vitrine, contra 1.846 e 916 de hoje). Bytes de imagem na
primeira tela abaixo de 10% dos 95,4 MB atuais.

**Restrições**: contrato imutável (as respostas continuam idênticas — FR-003); allowlist de largura
fechada em `(128, 320, 480, 640)`, fora dela é 404; vitrine é superfície pública, logo 320–430 px
sem rolagem horizontal (Princípio X); `useReducedMotion` onde há animação; **nenhuma rota pública
nova**, então `BACKEND_PREFIXES` não muda.

**Escala/escopo**: 0 tabelas, 0 colunas, 0 migrations. 1 endpoint novo; 5 endpoints existentes com a
consulta alterada e a resposta preservada; 3 telas do gerenciador + 2 da vitrine.

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1 — **aprovado nas duas passagens**.*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | Nada novo é inventado: `assetUrl(url, {largura})` e a rota de variante são da 270; `AvatarThumb`/`Foto` são da 292; `flask warm-thumbnails` já existe e já cobre as larguras; a pausa de 300 ms copia o `AgruparEventosDialog`; `keepPreviousData` copia `agenda.ts`/`formulariosAdmin.ts`; o `GET` de categorias reusa caminho e gate do `POST` que já existe |
| II. Padrões de código | Type hints e docstring na view nova; TS estrito (o tipo `CatalogCategoryOption` já existe e é reusado); `ruff check` nos arquivos tocados, `ruff format` em nenhum (todos são legado) |
| III. Camadas / API First | A view nova entra em `app/api/admin_catalogo_read.py`, que **já é importado** por `app/api/__init__.py` — sem módulo novo, sem risco de registro esquecido. Ela lê `CatalogCategory` no mesmo estilo inline que a listagem vizinha já usa (linha 92), sem criar uma camada que o projeto não tem |
| IV. Não quebrar o que funciona | Mudança aditiva: nenhum contrato muda (FR-003), e o verify compara a resposta com a de referência campo a campo. O carregamento antecipado fica **no ponto que precisa dele**, não no modelo — mudar `lazy=` em `models.py` afetaria escrita e telas que não pediram nada (alternativa rejeitada em R1) |
| V. UI/UX com feedback | Os estados de carregamento das telas não mudam; `keepPreviousData` **melhora** o feedback da busca (deixa de piscar esqueleto a cada tecla). Nenhum botão é tocado |
| VI. Esteira (Nível 1) | Esteira completa; artefatos em `specs/300-catalogo-rapido/` |
| VII. Living Spec | A spec foi corrigida **antes** deste plano quando o `GET` de categorias apareceu (seção RBAC), e as respostas do clarify entraram nela na hora |
| VIII. Verify antes do núcleo | `verify_300.py` é a primeira tarefa da fase Foundational e precisa **falhar** primeiro pelo motivo certo: com o código de hoje, a contagem de consultas estoura o teto |
| IX. Dinheiro BRL | Não se aplica — a feature não toca valor monetário |
| X. Mobile-first público | A vitrine é superfície pública: grade geral, grade de categorias, página de produto e lista de desejos conferidas em 375×812 antes de "pronto" |
| XI. Framer Motion | A visão Personagens usa `AnimatePresence` + `layout`; as imagens adiadas convivem com isso, mas a conferência de tela inclui abrir essa aba e observar se o `layout` não salta quando a imagem chega |
| XII. Combobox / miniaturas | **XII.2**: as miniaturas passam a usar `AvatarThumb`/`Foto`, que já dão o espaço reservado e o fallback de 404 — resolve os 66 arquivos ausentes da migração. **XII.5**: a busca de personagem ganha a pausa que faltava |
| XIII. RBAC declarado | `GET /api/admin/catalogo/categorias` nasce com SUPERADMIN declarado (mesmo `_require_superadmin` do vizinho), linha em `docs/01` §4.3, e um cenário de verify que **deve falhar** |
| XIV. Config / efeito externo | Nenhuma variável de ambiente nova; nenhuma escrita em serviço de fora |
| Stack | Sem migration (nada em `models.py` muda), sem Jinja novo, sem segredo |
| Operação e Deploy | `startCommand` não é tocado; nenhuma migração destrutiva. **Passo operacional obrigatório**: `flask warm-thumbnails` por SSH logo após o deploy, com a fila de push vazia (R6) |

**Rastreamento de complexidade**: sem violações a justificar — a tabela fica vazia de propósito.

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/300-catalogo-rapido/
├── spec.md              # /speckit-specify + /speckit-clarify
├── plan.md              # este arquivo
├── research.md          # Phase 0 — as 7 decisões, com o que foi rejeitado e por quê
├── data-model.md        # Phase 1 — relationships e estratégia de carga (sem migration)
├── quickstart.md        # Phase 1 — como rodar a verificação e conferir as telas
├── contracts/
│   └── catalogo-listagens.md
├── checklists/
│   └── requirements.md
├── tasks.md             # /speckit-tasks
└── verify_300.py        # Princípio VIII — escrito antes do núcleo
```

### Código (caminhos reais desta feature)

```text
app/api/admin_catalogo_read.py        # _item_summary (:29) e a listagem (:81-98); view nova de categorias
app/admin/catalog_character_ops.py    # list_catalog_characters (:344) — carga antecipada na linha 363
app/api/catalogo_read.py              # vitrine: :96 (grade), :121 (categorias), :149 (categoria)
frontend/apps/internal/src/components/CatalogCardGrid.tsx        # capa 64px
frontend/apps/internal/src/components/CatalogTreeView.tsx        # capa 40px + rosto 32px
frontend/apps/internal/src/components/CatalogPersonagensView.tsx # rosto 48px + chip de tema
frontend/apps/internal/src/components/AdminCatalogCharacterPanel.tsx # 2 miniaturas + a pausa da busca
frontend/apps/internal/src/components/CatalogPhotoManager.tsx    # grade de fotos do formulário
frontend/apps/internal/src/pages/AdminCatalogoFormPage.tsx       # :41 — passa a pedir só as categorias
frontend/apps/internal/src/lib/adminCatalogo.ts                  # hook novo das categorias
frontend/apps/public/src/pages/CategoriesPage.tsx                # :51 — lacuna da 270
frontend/apps/public/src/pages/WishlistPage.tsx                  # :69 — lacuna da 270
```

**Decisão de estrutura**: a correção mora **onde o custo nasce**, não numa camada nova.

- O carregamento antecipado entra na consulta de cada listagem — três arquivos no backend —, porque
  é ali que se sabe o que a serialização vai pedir. Não sobe para `models.py` (R1) nem desce para
  uma camada de repositório, que este projeto não tem e a constituição proíbe criar.
- A escolha da largura da imagem é **do lado do cliente**, como a 270 estabeleceu: o backend
  continua devolvendo o caminho do arquivo original, e quem sabe o tamanho da caixa é o componente
  que desenha. Por isso nenhum contrato muda, e por isso as onze mudanças de frontend são todas
  locais e independentes entre si.
- A única superfície nova (`GET` de categorias) entra no arquivo de leitura que já existe e já é
  registrado, para não abrir a armadilha de "módulo novo em `app/api/` que ninguém importou".
