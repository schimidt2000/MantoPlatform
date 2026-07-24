# Research: Reestruturação do Banco de Figurinos

## 1. Grade densa e enquadramento de foto

**Decision**: Grid Tailwind `grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6`,
cards com `aspect-[3/4]` para o quadro de foto, `object-cover object-top`.

**Rationale**: `aspect-[3/4]` (retrato) é a proporção que melhor acomoda fotos de corpo inteiro
tiradas em ambiente de ensaio (mais alto que largo) sem cortar a cabeça quando alinhado ao topo.
`2xl:grid-cols-6` cobre monitores ultrawide sem forçar 6 colunas em notebooks 13"-15" (onde 4-5 já
é denso o suficiente) — fidelidade ao pedido "5 a 6 colunas em telas widescreen" sem quebrar telas
menores.

**Alternatives considered**: `aspect-square` (rejeitado — corta cabeça/pés em fotos de corpo
inteiro, exatamente o problema relatado); grade fixa `grid-cols-6` sem breakpoints (rejeitado —
quebra em notebooks comuns).

## 2. Painel colapsável de faltantes

**Decision**: Reaproveitar `SectorPanel` (`frontend/apps/internal/src/components/SectorPanel.tsx`),
já usado no Dashboard para os setores Casting/Figurino/Comercial, passando `defaultOpen={false}`.

**Rationale**: Já implementa exatamente o padrão pedido (título + contagem, `aria-expanded`,
animação Framer Motion com `useReducedMotion()`, chevron rotacionado) — reaproveitar evita
duplicar um segundo componente de accordion no design system (Princípio I).

**Alternatives considered**: Novo componente `Accordion` no `@manto/ui` (rejeitado — YAGNI, um
único uso não justifica um primitivo novo de design system).

## 3. Filtro por tag

**Decision**: Reaproveitar `FilterDropdown` + `CheckboxList` (`@manto/ui`, já usados na busca de
Talentos da feature 180) para o filtro de tags de figurino.

**Rationale**: Já é o único padrão de dropdown de filtro do design system (comentário no próprio
componente confirma: "único padrão de dropdown de filtro do design system"); tags de figurino são
um conjunto pequeno e dinâmico de strings — o mesmo formato de opções `{value, label}` já cobre o
caso sem adaptação.

**Alternatives considered**: `<select multiple>` nativo (rejeitado — pior UX, sem contagem visual
de selecionados); nova lib de multi-select (rejeitado — dependência desnecessária).

## 4. Seletor de ficha para "Associar a uma ficha existente"

**Decision**: `<select>` nativo estilizado, mesmo padrão do seletor de ficha de figurino já usado em
`EventCreatePage.tsx` (`CharacterRow`), populado com `useFigurinoSheets().data.items`.

**Rationale**: Não há componente `Dialog`/`Combobox` no design system compartilhado (confirmado em
`CLAUDE.md`: "não há Dialog no design system compartilhado ainda"); o `<select>` nativo já é o
padrão estabelecido para esse exato caso de uso (escolher uma ficha entre as cadastradas).

**Alternatives considered**: Introduzir um componente `Dialog`/`Combobox` novo (rejeitado — fora do
escopo desta feature, é uma decisão de design system maior que não deve ser tomada de forma
isolada por uma feature de produto).

## 5. Fluxo de impressão

**Decision**: Botão "Imprimir" do card faz `window.open(assetUrl-style absolute path, "_blank")`
para a rota Jinja legada já existente `/figurinos/<id>/print` (sessão compartilhada via cookie
HttpOnly — mesmo domínio/proxy, sem CORS).

**Rationale**: Essa rota já renderiza a ficha de impressão completa com CSS de impressão pronto
para "Salvar como PDF" do navegador — exatamente o "fluxo de impressão/geração de PDF" pedido.
Reaproveitar evita duplicar geração de PDF/print no React e mantém FR-015 (zero alteração no
Jinja legado — é só um link para uma rota já pública ao usuário autenticado).

**Alternatives considered**: Gerar um PDF novo no backend (nova dependência, rejeitado — não
agrega valor sobre o fluxo já existente); renderizar a ficha de impressão em React
(rejeitado — duplicaria lógica de impressão já madura no Jinja, violando Princípio I).

## 6. Cobertura de "personagem sem ficha" (associar vs. apenas nome)

**Decision**: `list_sheets()` (usado só pela API) passa a considerar um cargo de evento "coberto"
quando `EventRole.figurino_sheet_id IS NOT NULL` **OU** o nome normalizado bate com alguma ficha —
não apenas por nome como hoje.

**Rationale**: É a única forma de fazer "Associar a uma ficha existente" (FR-009/010) realmente
tirar o item da lista de faltantes sem inventar um mecanismo de "resolvido" paralelo — o campo
`EventRole.figurino_sheet_id` já existe desde a feature 154/155 exatamente para esse vínculo (hoje
só é setado manualmente na criação do evento, nunca a partir da tela de figurino).

**Alternatives considered**: Renomear a ficha para bater com o nome do personagem faltante
(rejeitado — múltiplos aliases de um personagem não devem forçar renomear a ficha "canônica");
tabela paralela de "resolvidos por associação" (rejeitado — desnecessário, o FK já existe e já é
respeitado por `delete_sheet()`).

## 7. Descarte (dispensa) de alerta de faltante

**Decision**: Nova tabela `figurino_missing_dismissals` (`character_name_norm`,
`event_role_ids` JSON, `dismissed_at`, `dismissed_by`) grava os IDs de `EventRole` cobertos pelo
descarte no momento em que ele acontece. Um personagem só reaparece se surgir um `EventRole` cujo
`id` não esteja nesse conjunto (FR-011).

**Rationale**: Comparar por IDs de `EventRole` (em vez de timestamp) é exato e não depende de
`EventRole` ter uma coluna `created_at` (não existe hoje) — um cargo de evento novo sempre tem um
`id` novo, então a lógica de "reaparece se surgir ocorrência nova" cai de graça sem nenhum campo
adicional no modelo já existente.

**Alternatives considered**: Coluna `dismissed_until`/timestamp comparando com `assigned_at`
(rejeitado — `assigned_at` pode ser nulo e não representa "quando o cargo foi criado"); apagar/
suprimir permanentemente o nome (rejeitado — viola FR-011 explicitamente).

## 8. Migration de `tags`

**Decision**: Coluna `tags` (Text, JSON serializado, nullable) em `figurino_sheets`, mesmo formato
já usado por `pieces` (lista de strings, sem tabela associativa).

**Rationale**: Consistência com o padrão já estabelecido no próprio modelo (`pieces` já é uma
lista JSON em `Text`) — evita introduzir uma tabela `figurino_tags` + relação N:N para um conjunto
de tags livre, pequeno e sem necessidade de normalização/reuso entre fichas nesta fase.

**Alternatives considered**: Tabela `tags` normalizada N:N (rejeitado — YAGNI; não há requisito de
autocomplete global de tags entre fichas nesta feature, apenas filtro por tags já usadas).
