# Research: Gerenciador de Catálogo — UX e Fluxo Ficha↔Catálogo↔Venda

## 1. Deploy dos dois apps (US6) — servidor único com prefixo de rota

**Decision**: `frontend/apps/public` passa a ser construído com `base: "/catalogo/"` (Vite) e
`<BrowserRouter basename="/catalogo">` (React Router) **apenas em build de produção**
(`import.meta.env.PROD`) — em dev (`npm run dev:public`) continua em `/` como hoje, preservando o
workflow local e os testes Playwright já escritos na feature 185. Um servidor Node novo,
`frontend/server.js`, usa `serve-handler` (biblioteca por trás do pacote `serve` já usado hoje,
adicionada como dependência direta) duas vezes: requisições que começam com `/catalogo` servem de
`apps/public/dist` (prefixo removido de `req.url` antes de delegar, para bater com a raiz do
`dist`); todo o resto serve de `apps/internal/dist`. Cada branch tem seu próprio fallback de SPA
(`rewrites: [{ source: "**", destination: "/index.html" }]`), então deep-link em qualquer rota de
qualquer um dos dois apps funciona (não só `/`).

**Rationale**: Evita criar um segundo serviço Railway (o usuário optou explicitamente por servir
os dois do mesmo serviço). `serve-handler` é a peça que já roda em produção hoje (via `serve`
CLI) — trocar para uso programático é a menor mudança que permite decidir "qual dist servir" por
requisição.

**Alternatives considered**: `serve --single` apontando para um diretório único com os dois
`dist` copiados um dentro do outro — rejeitado porque o fallback do `--single` só conhece UM
`index.html` (o da raiz), quebrando deep-link/refresh dentro do app aninhado.

## 2. Link do menu lateral

**Decision**: Nenhuma mudança de código em `navigation.tsx` — o `href="/catalogo/"` já está
correto uma vez que o deploy (decisão #1) serve o app público sob esse mesmo prefixo, na mesma
origem. O bug relatado desaparece só com a mudança de infraestrutura.

## 3. Busca visual de Personagem (US1) e RBAC (US2)

**Decision**: Estender `GET /api/catalogo/elenco-busca` (`app/api/catalogo_read.py`, feature 185)
para incluir `photo_url` em cada Personagem, e ampliar o gate de `COMERCIAL`/`SUPERADMIN` para
também aceitar `FIGURINO`. Novo componente `CharacterAutocomplete.tsx` em
`frontend/apps/internal/src/components/` — type-ahead com `<img>` de miniatura por sugestão
(placeholder de emoji quando não há foto), reaproveitado tanto em `ElencoBlock.tsx` (US1) quanto
em `FigurinoFormPage.tsx` (US2, vincular a partir da ficha).

**Rationale**: Reaproveita o endpoint e o formato de dado já validado pela feature 185 (Princípio
I) em vez de criar um endpoint paralelo. Achatar Temas/Personagens já é feito nesse endpoint — só
falta a foto.

## 4. Vínculo a partir da Ficha de Figurino

**Decision**: Sem coluna nova. "Vincular a um Personagem" na tela da Ficha, ao selecionar,
dispara `PATCH /api/admin/catalogo/personagens/<id>` com `figurino_sheet_id = <id da ficha atual>`
— a mesma escrita que já acontece do lado do catálogo (feature 185). Ao carregar a tela da Ficha,
uma leitura busca (via `elenco-busca`, filtrando client-side por `figurino_sheet_id === sheet.id`)
se já existe um Personagem vinculado a ela, para mostrar o estado atual e permitir desvincular.

**Rationale**: `CatalogCharacter.figurino_sheet_id` já é a fonte única do vínculo (unidirecional
no schema, bidirecional na UI) — dois formulários escrevendo na mesma coluna, sem duplicar
lógica de negócio (reaproveita `catalog_character_ops.update_character`).

## 5. Árvore hierárquica (US3) — dado necessário na listagem

**Decision**: Estender `GET /api/admin/catalogo` (`app/api/admin_catalogo_read.py`) para incluir,
por item, um resumo de `characters: [{id, name, photo_url, figurino_sheet_id, is_active}]` —
suficiente para renderizar a árvore sem N+1 requisições ao expandir cada Tema.

**Rationale**: Evita buscar o detalhe completo (`GET /api/admin/catalogo/<id>`) de cada Tema só
para saber quantos/quais filhos ele tem.

## 6. Alternador Cards/Árvore e persistência de preferência

**Decision**: Estado local (`useState` inicializado de `localStorage`, chave
`manto_admin_catalogo_view`) — client-side, sem endpoint novo. `AdminCatalogoListPage.tsx` passa
a orquestrar dois componentes de apresentação: `CatalogCardGrid.tsx` (existente, refatorado com
kebab menu) e `CatalogTreeView.tsx` (novo).

## 7. Kebab menu

**Decision**: Não existe `DropdownMenu` no design system (`@manto/ui`) — construído um componente
local `KebabMenu.tsx` em `frontend/apps/internal/src/components/` (botão `⋮` + painel ancorado que
fecha ao clicar fora/Esc), no mesmo espírito enxuto de `FilterDropdown` já existente em
`@manto/ui` (sem overlay de terceiros). Fica local ao app por ora — promover para `@manto/ui` é
decisão futura se aparecer um segundo consumidor fora do catálogo (YAGNI, Governança da
constituição).

## 8. Seleção múltipla e ações em massa

**Decision**: Checkbox nativo (`<input type="checkbox">`, mesmo padrão já usado em
`AdminCatalogoFormPage.tsx` para capa/rádio) por item; barra flutuante fixa
(`position: fixed; bottom`) quando `selecionados.length > 0`. "Mover para…" é um painel inline
DENTRO da própria barra (um `<select>` de Temas + botão "Confirmar"), não um modal — não existe
`Dialog` no design system e a constituição não exige um para esta ação (Princípio V exige
confirmação para ações destrutivas via `window.confirm()`, que continua valendo para
inativar/excluir em massa).

**Alternatives considered**: Modal dedicado — rejeitado por exigir criar o primeiro `Dialog` do
design system só para este fluxo (complexidade não justificada, YAGNI).

## 9. Endpoint de mover em massa

**Decision**: Novo endpoint `POST /api/admin/catalogo/personagens/mover-em-massa` — body
`{character_ids: number[], target_item_id: number}`, delegando a uma função nova e pequena em
`catalog_character_ops.py` (`move_characters(character_ids, target_item)`) que reatribui
`catalog_item_id` em lote dentro de uma única transação, recusando (`CatalogValidationError`) se
`target_item_id` estiver entre os próprios `character_ids` teria sentido só se Temas também
pudessem ser movidos — como só Personagens têm pai, a validação real é: `target_item_id` deve
existir e estar ativo.

**Rationale**: Um único endpoint transacional evita N chamadas PATCH sequenciais do frontend (mais
rápido, e ou tudo aplica ou nada aplica).

## 10. Inativar/excluir em massa

**Decision**: Reaproveita os endpoints já existentes (`POST .../toggle-ativo`,
`DELETE /api/admin/catalogo/<id>`, `DELETE /api/admin/catalogo/personagens/<id>`) chamados em
sequência pelo frontend (Promise.all) — sem endpoint novo, já que cada chamada individual já é
idempotente e rápida (Princípio I, não duplicar o que já existe em lote no backend sem necessidade
real de transação atômica entre itens diferentes).

## 11. Capa e reordenação (US5)

**Decision**: Badge "⭐ Capa" via CSS absoluto sobre a foto cuja `id === coverPhotoId` (ou a
primeira nova, mesma lógica de `newPhotoCoverIndex` já existente); "Definir como capa" some o
rádio escondido por um botão explícito que chama a mesma função já existente
(`setCoverPhotoId`/`setNewPhotoCoverIndex`). Reordenação por arrastar: atributos HTML5 nativos
(`draggable`, `onDragStart`/`onDragOver`/`onDrop`) sobre a grade já existente — zero dependência
nova — computando a nova ordem e chamando a mesma função `moveExistingPhoto`-like já usada pelas
setas (unifica os dois caminhos de reordenação no mesmo estado).
