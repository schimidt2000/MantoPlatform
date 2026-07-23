# Research: Gastos Extras — RBAC, edição, "Aprovado com edições"

## 1. Como representar "Aprovado com edições" sem quebrar cálculos financeiros existentes

**Decision**: coluna booleana nova `SpecialExpense.approved_with_edits` (default `False`), em vez
de um 4º valor no campo `status`. O badge visual = `status == "aprovado" and approved_with_edits`.

**Rationale**: `SpecialExpense.status == "aprovado"` é usado como filtro literal em 7 pontos fora
de `gastos_ops.py` que movem dinheiro de verdade: DRE (`app/api/financeiro_read.py:164`,
`app/financeiro/routes.py:419`), geração da planilha de pagamentos
(`app/api/financeiro_read.py:630`, `app/financeiro/routes.py:1114`), e custo de eventos
(`app/calendar/routes.py:1734`, `app/api/agenda_read.py:178`). Um 4º valor de status faria esses
7 pontos ignorarem silenciosamente gastos aprovados-com-edição — regressão financeira real.
Com a coluna booleana, nenhum desses pontos precisa mudar.

**Alternatives considered**:
- 4º valor de `status` (`"aprovado_com_edicoes"`) — rejeitado pelo motivo acima.
- Tabela de histórico/auditoria separada para "antes/depois" — rejeitado por ser mais complexo
  do que o pedido exige; o `AuditLog` existente (via `_log()`) já registra a ação de editar,
  suficiente para rastreabilidade sem nova tabela.

## 2. Nível de acesso do papel FINANCEIRO em Gastos Extras

**Decision**: `FINANCEIRO` ganha o mesmo nível de `SUPERADMIN` (aprovar/rejeitar/editar/vincular
evento/excluir qualquer gasto) — mas **só na camada API/React**. As checagens que a Jinja legada
usa (`gastos_ops.is_superadmin`, `gastos_ops.can_delete_expense`, `gastos_ops.list_expenses`)
permanecem exatamente como estão.

**Rationale**: confirmado com o usuário. Tecnicamente seguro porque o próprio projeto já separa
RBAC de API e RBAC de Jinja como funções independentes (CLAUDE.md: "RBAC em endpoint de API é
função, não decorator... validada por paridade de comportamento, não por reusar o decorator") —
divergir aqui é o padrão esperado do repositório, não uma exceção.

**Alternatives considered**: alterar as funções compartilhadas de `gastos_ops.py` para usar
`is_financeiro` — rejeitado porque mudaria também o comportamento da tela Jinja legada
(violação direta do escopo pedido).

## 3. Componente de Modal/Dialog

**Decision**: componente `Modal` novo, local a `GastosExtrasPage.tsx` por enquanto — overlay
`fixed inset-0 bg-black/50` + painel centralizado, Framer Motion (opacity/scale, 150–350ms,
`useReducedMotion()`).

**Rationale**: grep confirmado em `frontend/packages/ui/src` — não existe `Dialog`/`Modal`/
`useDialog` no design system compartilhado (`CLAUDE.md` já documenta isso). O padrão de overlay
mais próximo no código é o drawer mobile de `frontend/packages/ui/src/components/app-layout.tsx:192-205`
(`fixed inset-0 bg-black/50` + painel animado) — mesma biblioteca, adaptado de lateral para
centralizado.

**Alternatives considered**: promover o `Modal` para `@manto/ui` já nesta feature — rejeitado
por escopo (YAGNI); fica documentado aqui como candidato natural para uma promoção futura assim
que um segundo consumidor precisar dele.

## 4. Padrão de tabela densa e KPI cards

**Decision**: `<table>` cru (sem componente `Table` — não existe um em `@manto/ui`), replicando
o padrão de `frontend/apps/internal/src/pages/PagamentosPage.tsx:383-423`
(`overflow-x-auto` + `min-w-[...]` + `thead` `text-xs uppercase text-muted` + células `px-3 py-2`,
valores `text-right tabular-nums`). KPI cards replicam o padrão local `KpiCard` de
`FinanceiroDashboardPage.tsx:109-115` sobre o `DenseCard` de `@manto/ui`.

**Rationale**: são os dois padrões de tabela densa e resumo numérico já em produção no mesmo
domínio (financeiro); manter consistência visual e não introduzir um terceiro padrão.

## 5. Fluxo "Aprovar" vs. "Editar" vs. "Salvar e Aprovar"

**Decision**: "Aprovar" continua um clique só (`POST /gastos/<id>/aprovar`, sem edição — nunca
marca `approved_with_edits`). "Editar" abre o modal preenchido; salvar sem aprovar mantém o
status atual. Quando o gasto editado está pendente, o modal expõe um botão adicional "Salvar e
Aprovar" que chama o mesmo `PATCH` com `aprovar: true`.

**Rationale**: confirmado com o usuário — preserva o fluxo rápido já em uso (a maioria das
aprovações não precisa de correção) e dá um caminho único para o caso "preciso corrigir antes de
aprovar", sem multiplicar botões.

## 6. Radio "Como será pago?"

**Decision**: mantém as 3 opções (Reembolso a funcionário / Pagamento a fornecedor / Sem
desembolso definido) como radio buttons, em vez de reduzir a 2 opções obrigatórias.

**Rationale**: confirmado com o usuário — "Sem desembolso definido" cobre um caso de uso real já
em produção (gasto pago direto do caixa da empresa, sem reembolso nem fornecedor a rastrear);
torná-lo obrigatório quebraria esse fluxo.
