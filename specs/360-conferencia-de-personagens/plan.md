<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: Conferência de personagens do catálogo (360)

**Branch**: `360-conferencia-de-personagens` | **Data**: 2026-11-24 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/360-conferencia-de-personagens/spec.md`

**Nota**: preenchido pelo `/speckit-plan`. A constituição (`.specify/memory/constitution.md`, v3.2
na `main`; v3.3.0 na branch 359, ainda sem merge) é lida em tempo de execução.

## Resumo

A leitura das fotos (343 itens de 09/11 + 13 de 24/11) vira um arquivo versionado
(`app/admin/dados/leitura_personagens.json`) e entra em duas tabelas novas por uma carga explícita e
idempotente. A conferência é uma fila (`/admin/catalogo/conferencia`) e uma tela por item
(`/admin/catalogo/conferencia/:itemId`), só do Superadmin. Cada decisão é um `PATCH`/`POST` pequeno
que grava na hora. A fila é calculada a cada consulta contra o catálogo vivo. Nada toca
`catalog_items`, `catalog_characters` nem a vitrine: gravar o conferido é a feature seguinte.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: as da casa. Nenhuma biblioteca nova. Reuso: `FigurinoPicker`,
`useFigurinoSheets`, `Foto`, `useAbrirArquivo` (visualizador), `useRestaurarRolagem`, `PageHeader`,
`Badge`, `Skeleton`, `Button`, `Input`, `ConfirmDialog`

**Armazenamento**: PostgreSQL. Duas tabelas novas (`catalog_conferencias`,
`catalog_conferencia_personagens`). A leitura mora num JSON do repositório (~300 KB). Nenhum arquivo
novo no disco do backend: os recortes são mostrados a partir das fotos que já estão em
`/catalogo/midia/`

**Verificação**: `specs/360-conferencia-de-personagens/verify_360.py` contra o espelho `manto_360`
(dump de produção de 24/11 02h); `cd frontend && npm run typecheck`; tela aberta no Browser pane a
390×844 e em tela larga

**Plataforma-alvo**: web, app interno; a Superadmin confere no celular (modo app) e no computador

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: fila (≤ ~400 linhas leves) numa consulta só, sem N+1; detalhe do item em
uma ida ao servidor; cada decisão responde em menos de 1 s

**Restrições**: 390 px sem rolagem lateral; alvos ≥ 44 px; `useReducedMotion`; filtro e busca no
endereço (convenção da 320); arquivo abre no visualizador, nunca em outra aba; a carga não pode
derrubar o start (por isso não é migration); FK nova nunca pode travar exclusão de item, foto, ficha
ou usuário

**Escala/escopo**: 2 tabelas, 1 migration aditiva, 1 módulo de núcleo, 2 módulos de API (9 rotas),
1 arquivo de dados, 2 páginas React, 1 módulo `lib/`, ~4 componentes, 1 botão de entrada na lista do
catálogo

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1 — sem violação nova.*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | Gate `_require_superadmin` no padrão de `admin_catalogo_*`; `FigurinoPicker` é a única porta de escolha de ficha; visualizador de arquivo da 320; `unaccent_lower_sql` na busca; `iso_sp` para o carimbo; nenhum componente novo em `@manto/ui` |
| II. Padrões de código | type hints e docstrings no núcleo; funções ≤ ~30 linhas; constantes no topo de `catalog_conferencia_ops.py`; TS estrito; `ruff check` nos tocados, `ruff format` nos novos. Exceção de estilo inline na tabela de complexidade |
| III. Camadas / API First | `app/admin/catalog_conferencia_ops.py` puro; `app/api/admin_catalogo_conferencia_{read,write}.py` só RBAC + chamada + serialização; os dois importados em `app/api/__init__.py`; nenhuma rota pública nova |
| IV. Não quebrar o que funciona | Só tabelas novas. FKs com `ON DELETE CASCADE`/`SET NULL` no banco e nenhum relacionamento novo do lado de `CatalogItem`, `CatalogItemImage`, `FigurinoSheet` ou `User`: excluir item, foto, ficha ou usuário segue funcionando (cenário 17 do verify). A lista do catálogo ganha um botão |
| V. UI/UX com feedback | TanStack Query; cada controle mostra "Salvando…" e desabilita; erro no campo sem apagar o digitado (`ApiRequestError.fields`); excluir personagem acrescentado pede `ConfirmDialog` |
| VI. Esteira (Nível 1) | esteira completa; artefatos em `specs/360-conferencia-de-personagens/` |
| VII. Living Spec | regra da fila (página própria), FR-017 e FR-018 entraram na spec antes do plano |
| VIII. Verify antes do núcleo | `verify_360.py` na fase Foundational, falhando por 404 de rota inexistente; 18 cenários, 5 que devem falhar (4b, 9, 11b, 13, 16) |
| IX. Dinheiro BRL | não se aplica: nenhum valor monetário |
| X. Mobile-first público | não é superfície pública, mas nasce a 390 px por pedido do dono (celular como app) |
| XI. Framer Motion | troca de item e mudança de estado do cartão com transição curta, sob `useReducedMotion`, no padrão das telas vizinhas |
| XII. Combobox / Maps | ficha de figurino pelo `FigurinoPicker` (Combobox com miniatura quadrada); tipo do item são 4 opções: botões, não select |
| XIII. RBAC declarado | SUPERADMIN em todas as rotas, função no início da view; comentário `RBAC:` no topo dos dois módulos; linhas em `docs/01` §4.3; o frontend não decide: a página é só rota de Superadmin e o servidor recusa |
| XIV. Config / efeito externo | nenhuma env nova; nenhuma escrita em serviço de fora |
| XV. Texto por superfície | app interno: operacional. Termos: Tema, Personagem, Figurino, Situação, Excluir (apaga o acrescentado) × "Não criar" (decisão). Textos listados em `contracts/conferencia-api.md` §Textos |
| Stack | migration à mão `f360a1b2c3d4`, `down_revision = "f353a1b2c3d4"` (head da `main` e da produção); sem Jinja; sem segredo |
| Operação e Deploy | não toca `startCommand`; migration aditiva (duas tabelas vazias). Backend e frontend mudam: vai no lote da noite. Depois do deploy, um clique em "Carregar leitura" |

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/360-conferencia-de-personagens/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/conferencia-api.md
├── checklists/
├── tasks.md
├── montar_leitura.py      # junta piloto + saídas dos leitores no JSON versionado (proveniência)
└── verify_360.py
```

### Código

```text
app/models.py                                         # CatalogConferencia, CatalogConferenciaPersonagem
migrations/versions/f360a1b2c3d4_conferencia_de_personagens.py
app/admin/catalog_conferencia_ops.py                  # fila, carga, decisões (puro)
app/admin/dados/leitura_personagens.json              # a leitura (356 itens)
app/api/admin_catalogo_conferencia_read.py            # GET fila, GET item
app/api/admin_catalogo_conferencia_write.py           # carregar, PATCH item, conferir, reabrir, personagens
app/api/__init__.py                                   # importar os dois módulos
frontend/apps/internal/src/lib/catalogoConferencia.ts # tipos + hooks
frontend/apps/internal/src/pages/CatalogoConferenciaPage.tsx      # fila
frontend/apps/internal/src/pages/CatalogoConferenciaItemPage.tsx  # um item
frontend/apps/internal/src/components/conferencia/    # RecortePersonagem, PersonagemPropostoCard, ...
frontend/apps/internal/src/App.tsx                    # duas rotas
frontend/apps/internal/src/pages/AdminCatalogoListPage.tsx        # botão "Conferir personagens"
```

**Decisão de estrutura**: o núcleo fica em `app/admin/`, ao lado de `catalog_ops.py` e
`catalog_character_ops.py` (é gestão do catálogo, não a vitrine de `app/catalogo/`). Módulos de API
próprios, e não mais rotas dentro de `admin_catalogo_{read,write}.py`, porque são 9 rotas com
serializer próprio e o arquivo de escrita já tem 413 linhas. A leitura fica em `app/admin/dados/`
porque precisa estar no contêiner do backend (`app/**` está no build) e é dado do sistema, não
documentação.

## Rastreamento de complexidade

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| Princípio VIII: verify contra `manto_360`, não `manto_local` | o `manto_local` é compartilhado pelas worktrees, está num dump de 20/10 e numa revisão que a `main` não conhece; a feature precisa da produção de hoje (a fila "atual") | refazer o `manto_local` apagaria o esquema de outras sessões; o padrão da casa desde a 338 é o espelho próprio |
| Princípio II: `style={{…}}` no recorte | o recorte é geometria vinda do dado (4 percentuais e a proporção da foto); não existe classe Tailwind para valor arbitrário calculado | recortar no servidor (Pillow) gastaria CPU e disco para 700 miniaturas que mudam de uso na feature seguinte; mesmo precedente de `DayTimelineView`, `HomePerformance` e `VideoScrubber` |
| Dado no repositório (JSON de ~300 KB em `app/admin/dados/`) | a carga precisa do arquivo dentro do contêiner; o arquivo é a fonte auditável do que a leitura propôs | migration de dados: falha no start derruba a produção (serviço com disco); upload pela tela: mais uma superfície só para um arquivo que eu mesmo gero |
