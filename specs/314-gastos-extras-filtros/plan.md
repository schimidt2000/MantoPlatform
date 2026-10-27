<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: Gastos Extras na tela inteira, com filtros e as pagas recolhidas

**Branch**: `314-gastos-extras-filtros` | **Data**: 2026-10-27 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/314-gastos-extras-filtros/spec.md`

**Nota**: preenchido pelo `/speckit-plan`. A constituição (`.specify/memory/constitution.md`,
v3.1.0) é lida em tempo de execução — o Constitution Check abaixo é o que ela cobra.

## Resumo

A `/gastos` deixa de ter teto de largura e de rolar para o lado. No computador (`xl`+) vira uma tabela de 7
colunas que cabe na tela. Abaixo disso vira cartões, o padrão de Pagamentos. Cada gasto ganha uma **situação** única,
calculada no núcleo do backend (`gastos_ops.situacao_do_gasto`) e serializada no `GET /api/gastos`:
aguardando aprovação · a pagar · no banco · pago · rejeitado. A tela agrupa por ela. À vista ficam aguardando, a
pagar e no banco. "Pagos" e "Rejeitados" ficam recolhidos em `AccordionRow` (`@manto/ui`). Os cartões de resumo
viram filtros clicáveis, como em Pagamentos (`TotalCard`, extraído para um componente compartilhado). A busca reusa
`normalizeSearch`/`searchTerms`/`matchesSearch` de `lib/pagamentos.ts`. Categoria, desembolso e mês são filtros, e
todos os filtros ficam na URL. Nenhuma migration, nenhum endpoint novo, nenhuma regra de escrita muda.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: Flask, SQLAlchemy; React, TanStack Query, React Router (`useSearchParams`), Tailwind
CSS, `@manto/ui` (`Card`, `Input`, `Button`, `AccordionRow`, `PageHeader`, `Skeleton`, `cn`), Framer Motion
(dentro do `AccordionRow`), `@manto/money`, `lucide-react`

**Armazenamento**: PostgreSQL, tabela `special_expenses`, **sem mudança de esquema**

**Verificação**: `specs/314-gastos-extras-filtros/verify_314.py` contra `manto_local` (login só pela API; leitura
de conferência por conexão separada; mutação da regra para provar que o verify morde); `cd frontend && npm run
typecheck`; tela aberta no Browser pane em 1920, 1366 e 375 px (Superadmin) e 1366 px (Casting)

**Plataforma-alvo**: app interno (`frontend/apps/internal`), staff em desktop e celular

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: o recorte roda na tela sobre a lista inteira (186 gastos em produção em 21/10), como
Pagamentos faz com o mês. Índice de busca montado uma vez por resposta (`useMemo`), não por tecla.
Nenhuma consulta nova no servidor: `situacao_do_gasto` só lê colunas já carregadas.

**Restrições**: campo novo do payload é opcional no React (armadilha 21: backend e bundle em versões diferentes
por minutos); `useReducedMotion` (já no `AccordionRow`); texto pelo Princípio XV ("Situação", "Excluir", "Nenhum
gasto encontrado."); a raiz sem `max-w` contraria o padrão do `docs/02` §Espaçamento — exceção pedida pelo dono,
registrada lá

**Escala/escopo**: 1 função nova no núcleo + 1 chave no serializer; 1 página reescrita em 3 arquivos (página, vistas
do item, modelo da situação em `lib/gastos.ts`); 1 componente extraído de `PagamentosPage` (cartão-filtro)

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1 (sem mudança).*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | `AccordionRow` (`@manto/ui`) para os grupos recolhidos; busca e mês de `lib/pagamentos.ts` (`normalizeSearch`, `searchTerms`, `matchesSearch`, `shiftMonth`, `monthLabel`, `currentMonth`); `TotalCard` de Pagamentos **extraído** para `components/CartaoFiltro.tsx` e usado pelas duas telas (não copiado); `GastoFormModal`, `EventoVincular`, `MarketingBatchDetail`, `SeloSituacao` e os hooks de `lib/gastos.ts` seguem como estão. A situação do pagamento vem do mesmo `payment_status` que a planilha escreve |
| II. Padrões de código | type hints + docstring Google em `situacao_do_gasto`; constantes `SITUACAO_*` no topo de `gastos_ops`; TS estrito (`GastoSituacao` union); `ruff check` em `gastos_ops.py`/`gastos_read.py`; `ruff format` só no `verify_314.py` |
| III. Camadas / API First | regra no `_ops` puro; `gastos_read.py` só serializa a chave; nenhum módulo novo em `app/api/` |
| IV. Não quebrar o que funciona | payload aditivo (`situacao`); `totals` continua no payload (contrato intacto); as ações e travas da 306/312 passam para as vistas novas sem mudar regra; `PagamentosPage` passa a usar o cartão extraído e é conferida na tela |
| V. UI/UX com feedback | loading/erro da query como hoje; botões com `loading`; erro da ação embaixo das ações; estado vazio com "Limpar filtros" |
| VI. Esteira (Nível 1) | specify → clarify (27/10) → plan → checklist → tasks → analyze → implement → converge |
| VII. Living Spec | a tabela do verify da spec foi ajustada neste plano (cenário 5 da busca em TS vira conferência de tela; mutação entra) — spec antes do código |
| VIII. Verify antes do núcleo | `verify_314.py` escrito antes de `situacao_do_gasto`; falha pelo motivo certo (chave `situacao` ausente) |
| IX. Dinheiro BRL | `brl()` de `lib/pagamentos.ts` (sobre `formatBRL`); somas em `number` só para exibição |
| X. Mobile-first público | não se aplica (interno); ainda assim conferido em 375 px — o pedido é sobre rolagem lateral |
| XI. Framer Motion | abrir/recolher grupo pelo `AccordionRow` (já com `useReducedMotion`) |
| XII. Combobox / Maps | categoria (7 opções + "Todas") e desembolso (4 + "Todos") ficam em `<select>` nativo: ≤ 10 itens |
| XIII. RBAC declarado | `GET /api/gastos` sem mudança de gate; a chave nova segue a regra de hoje (o não gestor recebe só os próprios gastos e nenhum `totals`); linha de `docs/01` §4.3 inalterada, shape atualizado |
| XIV. Config / efeito externo | não se aplica: nenhuma env, nenhuma escrita fora (aprovar não manda e-mail nem toca Google — `approve_expense` só grava e loga) |
| XV. Texto por superfície | app interno, tom operacional; "Situação" no cabeçalho e nos filtros; "Aguardando aprovação", "A pagar", "No banco", "Pagos", "Rejeitados"; "Excluir" (apaga de verdade); "Ver nota fiscal"; "Nenhum gasto encontrado."; contagem concorda com o número ("1 gasto", "3 gastos"); nenhum texto comparado em lógica |
| Stack | sem migration; sem Jinja; sem segredo |
| Operação e Deploy | não toca `startCommand`; deploy comum, em lote, quando o dono pedir |

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/314-gastos-extras-filtros/
├── spec.md              # /speckit-specify + Clarifications 27/10
├── plan.md              # este arquivo
├── research.md          # Phase 0 — decisões
├── data-model.md        # Phase 1 — a situação derivada
├── quickstart.md        # Phase 1 — como conferir
├── contracts/
│   └── gastos-list.md   # shape do GET /api/gastos com `situacao`
├── checklists/          # requirements.md (+ /speckit-checklist)
├── tasks.md             # /speckit-tasks
└── verify_314.py        # Princípio VIII — antes do núcleo
```

### Código

```text
app/gastos/gastos_ops.py                                   # SITUACAO_* + situacao_do_gasto(expense)
app/api/gastos_read.py                                     # _expense_dict ganha "situacao"
frontend/apps/internal/src/lib/gastos.ts                   # GastoSituacao, rótulos, tons, ordem, grupo, índice de busca
frontend/apps/internal/src/components/CartaoFiltro.tsx     # NOVO — TotalCard extraído de PagamentosPage, tom por prop
frontend/apps/internal/src/components/Gastos/GastoItemViews.tsx  # NOVO — GastoRow (tabela) + GastoCard (celular) + ações
frontend/apps/internal/src/components/Gastos/GastosFiltros.tsx   # NOVO — busca, categoria, desembolso, mês
frontend/apps/internal/src/pages/GastosExtrasPage.tsx      # raiz sem max-w; cartões-filtro; lista principal + grupos
frontend/apps/internal/src/pages/PagamentosPage.tsx        # passa a importar o CartaoFiltro (sem mudança visual)
```

**Decisão de estrutura**: a página tem 882 linhas com tudo dentro. O formulário (`GastoFormModal` e
companhia) fica onde está, porque não muda. O que é novo, ou muda de forma, sai para arquivos próprios: as vistas do
item (linha e cartão, com as ações compartilhadas), a barra de filtros e o cartão-filtro compartilhado. É o
desenho de Pagamentos (`components/Pagamentos/PagamentoItemViews.tsx`).

### O desenho da tela

**Raiz**: `<div className="space-y-4 p-4 sm:p-6">`, sem `mx-auto max-w-*` (FR-001). Os ramos de carregamento e erro
levam o mesmo invólucro.

**Cartões-filtro** (`grid grid-cols-2 gap-2 sm:grid-cols-3 sm:gap-3 xl:grid-cols-6`): Todos · Aguardando aprovação ·
A pagar · No banco · Pagos · Rejeitados. Valor e contagem vêm do **recorte dos outros filtros** (busca, categoria,
desembolso, mês), para que o número que se clica seja o número que aparece (FR-009). Clicar filtra a situação, e
reclicar ou clicar em "Todos" limpa. Tons: aguardando = `gold`, a pagar = `red`, no banco = `blue`, pago = `green`,
rejeitado = neutro (`text-muted`). São as cores de Pagamentos para pendente, no banco e pago.

**Sem filtro de situação** (abertura): a lista principal mostra aguardando + a pagar + no banco, na ordem de hoje
(data desc). Embaixo vêm dois `AccordionRow` fechados, "Pagos — N gastos · R$ X" e "Rejeitados — N gastos · R$ X",
cada um com a mesma lista (tabela/cartões) dentro. O grupo vazio não aparece. Os grupos são componentes com chave
estável, então o aberto/fechado sobrevive à revalidação depois de uma ação (FR-014).

**Com filtro de situação**: só aquela situação, aberta, sem grupos recolhidos. Se a situação for pago ou rejeitado,
a lista aparece direto, sem precisar abrir o grupo.

**Tabela (`xl`+, `w-full table-fixed`, sem `min-w`, sem `overflow-x-auto`)**, 7 colunas com `colgroup`:

| Coluna | Largura | Conteúdo |
|---|---|---|
| Data | `w-24` (96 px) | dd/mm/aaaa |
| Gasto | flexível | descrição; categoria · observação (muted); "por <autor>" (só gestão); bloco do auditor (256) |
| Valor | `w-28` (112 px) | `brl`, à direita |
| Situação | `w-28` (112 px) | selo da situação; "com edições" (muted) quando `approved_with_edits` |
| Desembolso | `w-36` (144 px) | quem recebe + (reembolso / fornecedor / devolução à cliente) |
| Evento | `w-40` (160 px) | título com `line-clamp-2` + `title` com o nome inteiro; selo Cancelado |
| Ações | `w-44` (176 px) | `flex flex-wrap gap-1`: Aprovar, Rejeitar (pendente, gestão) numa linha; ícones de 32 px com `aria-label`/`title` para Ver nota fiscal, Editar, Vincular evento, Excluir na outra; aviso "Devolução de cancelado: travada." e erro da ação embaixo, com quebra de linha |

As colunas fixas somam 800 px. A janela útil é a largura menos o menu (256 px) e o padding da página (48 px):
976 px em 1280, e a coluna Gasto fica com ≈ 176 px (quebra em mais linhas); 1062 px em 1366, Gasto ≈ 262 px; 1616 px
em 1920, Gasto ≈ 816 px. Sem rolagem lateral em `xl` (1280) e acima (FR-002 pede 1366). Células com `px-2`, e texto
longo quebra (`[overflow-wrap:anywhere]` em Gasto, Desembolso e Evento). A tela aberta em 1280/1366 é o portão
desta conta.

**Cartões (`< xl`)**: `grid gap-2 md:grid-cols-2 [&>*]:min-w-0`, o mesmo de Pagamentos. Cada cartão traz descrição +
valor no topo, selo da situação, data · categoria, desembolso, evento, autor (gestão) e as ações com texto (no
celular há espaço vertical, então os ícones voltam a ser botões com rótulo).

**Barra de filtros** (`GastosFiltros`), acima da lista: busca (ícone + limpar, igual a Pagamentos), categoria
(`<select>`: "Todas as categorias" + `categories` do payload), desembolso (`<select>`: "Todos os desembolsos",
Reembolso, Fornecedor, Devolução à cliente, Sem desembolso) e mês (‹ › + `Input type="month"` + "Todos os meses"
quando há mês). Ao lado: "N de M gastos · R$ X" quando algum filtro está ativo, e "Limpar filtros" (FR-003 da
História 3). Linha `sr-only` com `aria-live` (FR-010).

**URL** (`useSearchParams`, `replace: true`): `busca`, `categoria`, `desembolso` (`reembolso` | `fornecedor` |
`cliente` | `nenhum`), `mes` (`AAAA-MM`), `situacao` (`aguardando_aprovacao` | `a_pagar` | `no_banco` | `pago` |
`rejeitado`). Valor inválido na URL = filtro ignorado, nunca tela vazia muda.

**Não gestor**: mesma tela. Os cartões-filtro são calculados da própria lista (só os seus gastos). Sem coluna/linha
de autor e sem ações de gestão, como hoje.

## Rastreamento de complexidade

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| Raiz da página sem `max-w` (padrão do `docs/02` §Espaçamento é `mx-auto max-w-<X>`) | pedido explícito do dono ("tem que ocupar a tela inteira, lateralmente") | `max-w-[1600px]`/`110rem` (o teto mais largo hoje) ainda deixaria o vazio do print num monitor de 1920+; registrado como exceção no `docs/02` |
