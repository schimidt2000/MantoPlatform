# Implementation Plan: Página de Clientes Organizada + Botão de Feedback Trava Após Envio (131)

**Branch**: `131-avaliacoes-clientes-pagina` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

## Summary

Duas partes independentes, ambas dentro do módulo de Clientes:

1. Nova tela `GET /clientes/avaliacoes`, irmã de `/clientes/` (mesmo padrão de
   "Banco de Talentos" + "Avaliações" como duas entradas de menu dentro de "Casting") —
   lista `ClientFeedback` com filtros por período (chips), nota (chips), card (select) e
   cliente (select), resumo (média/total), destaque de notas baixas e estado vazio.
2. Em `event_detail.html`, o botão "Pedir feedback da cliente" passa a usar a mesma
   sintaxe condicional já usada pelo botão de Cobrança (`disabled` + estilo esmaecido +
   `title` explicando) quando `client_feedbacks` (já carregado na view) não estiver vazio.

## Technical Context

**Stack**: o existente (Flask + SQLAlchemy + Jinja2 + JS vanilla). **Storage**: nenhuma
mudança de schema — só leitura de `ClientFeedback`/`CalendarEvent`/`Client` já existentes.

**Arquivos**:
- `app/clientes/routes.py` — nova rota `GET /avaliacoes` (dentro do blueprint
  `clientes_bp`, então vira `/clientes/avaliacoes`), decorada com o mesmo `@require_vendas`
  já usado no resto do blueprint (FR-010: mesma regra de permissão da área de Clientes).
  Lê `period` (`30d|90d|365d|all`, default `all`), `score` (`1..5|all`), `tag`
  (uma das 9 tags fixas de `app.feedback.routes.POSITIVE_TAGS`/`ATTENTION_TAGS`, ou
  `all`), `client_id` (`int|all`). Query: `ClientFeedback` `JOIN` `CalendarEvent` (por
  `event_id`) `LEFT JOIN` `Client` (por `CalendarEvent.client_id`, pode ser nulo — Edge
  Case do spec). Filtro de tag via `ClientFeedback.tags.ilike(f'%"{tag}"%')` (aspas
  incluídas no padrão — compara o valor exato dentro do JSON, evita que "👗 Figurino"
  capture "👗 Figurino Perfeito" por engano). Calcula em Python, sobre o resultado já
  filtrado: média, total, distribuição por nota (1–5), lista de "pontos de atenção"
  (nota ≤ 2), lista completa para exibição. Selects populados a partir de dados reais:
  clientes com pelo menos 1 feedback (ordenados por nome); tags fixas reaproveitadas de
  `app.feedback.routes` (import direto, sem duplicar a lista).
- `app/templates/clientes/avaliacoes.html` (novo) — mesma linguagem visual de
  `talents/avaliacoes.html`: chips de período/nota (`.filter-chip`/`.filter-chip.active`,
  copiados como estilo local, mesmo padrão do template de referência), selects de
  card/cliente, `.kpi-grid` (média, total, clientes avaliados) reaproveitando a classe
  global `.kpi`, distribuição por nota em barras, painel "Pontos de atenção" (nota ≤ 2,
  borda vermelha se houver algo, verde se não), lista de avaliações (nota, cards, cliente
  com link pra ficha quando existir, comentário, data), estado vazio. Macro local
  `stars(value)` equivalente à de `talents/avaliacoes.html` (mesmo padrão página-local,
  sem extrair pra arquivo compartilhado ainda — só o segundo uso, não justifica mudança de
  estrutura por ora).
- `app/templates/clientes/list.html` — pequeno link/botão no topo ("⭐ Ver avaliações")
  apontando pra nova tela, mesmo espírito de organização em duas partes pedido no spec.
- `app/templates/base.html` — novo item de sidebar "Avaliações" dentro da seção
  "Comercial", logo abaixo de "Clientes" (mesmo grupo/gating `eff_has_role('COMERCIAL',
  'FINANCEIRO', 'SUPERADMIN')` já usado pelo item "Clientes"), mesmo padrão visual do par
  "Banco de Talentos"/"Avaliações" já existente em "Casting".
- `app/templates/event_detail.html` — botão `#btn-feedback-cliente`: `{% if
  client_feedbacks %}disabled style="opacity:.45; cursor:not-allowed;" title="A cliente já
  enviou feedback para este evento" {% else %}title="Copiar link da página de avaliação
  deste evento"{% endif %}` (cópia literal da estrutura condicional já usada em
  `#btn-cobranca`); no JS de wiring, `if (bf && !bf.disabled) bf.addEventListener(...)`
  (mesmo guard já usado para `bp`/Cobrança). `client_feedbacks` já é passado à view hoje
  (feature 130) — nenhuma mudança de rota necessária para isso.

**Testing**: verificação funcional vs `manto_local` — criar feedbacks de teste com notas/
cards/datas variadas para 2+ clientes, conferir cada filtro isoladamente e combinado,
conferir resumo/distribuição/pontos de atenção batem com o filtro aplicado, conferir
estado vazio (filtro sem resultado E sem nenhum dado), conferir permissão (mesma de
`/clientes/`), conferir botão de pedir feedback desabilitado só após existir feedback e
segue clicável antes disso.

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Tela nova segue o precedente já existente ("Banco de Talentos" + "Avaliações" como duas entradas de menu) em vez de inventar uma estrutura nova. Filtros em chips (`.filter-chip`) e KPIs (`.kpi-grid`) copiam o padrão visual/interativo já usado em `talents/avaliacoes.html` e `style.css`. Botão de feedback reaproveita literalmente a mesma estrutura condicional do botão de Cobrança, já testada e em produção. Tags reaproveitadas de `app.feedback.routes` (constantes existentes), sem duplicar a lista. |
| III. Permissões | ✅ FR-010: a nova tela usa o mesmo `@require_vendas` do resto do blueprint `clientes_bp` — nenhuma regra de acesso nova inventada. |
| IV. Não quebrar | ✅ Botão de Cobrança não muda; botão de feedback só ganha um novo ramo condicional (feedback já existe) sem alterar o comportamento quando não existe (FR-013). Tela nova é aditiva — `/clientes/` continua igual, só ganha um link a mais. |
| V. UI/UX | ✅ Estado vazio explícito (FR-009); notas baixas destacadas visualmente (FR-008), mesmo padrão "borda vermelha se houver, verde se não" já usado em `talents/avaliacoes.html` pro painel de pontos de atenção. Botão desabilitado explica o motivo via `title` (FR-012), consistente com o guard de feedback visível da constituição (Princípio V/feature 124) — aqui a ausência de ação é intencional e comunicada, não um botão "morto" sem explicação. |
| VI. Planejar | ✅ Este plano, escrito depois de uma exploração dedicada de `clientes/routes.py`, `clientes/list.html`, `talents/routes.py::avaliacoes` e `talents/avaliacoes.html` para confirmar o padrão a espelhar antes de decidir a estrutura. |
| VIII. Mobile-first | N/A — tela interna do painel administrativo (mesmo critério já usado para as demais telas internas: `talents/avaliacoes.html` e `clientes/list.html` também não são superfícies públicas). |

**Gate: PASS.**

## Decisões

1. **Duas telas (`/clientes/` e `/clientes/avaliacoes`), não uma só**: o par "Banco de
   Talentos"/"Avaliações" já é o precedente direto no mesmo código — replicar a mesma
   forma evita inventar uma estrutura de abas nova e mantém a navegação do sistema
   consistente (Princípio I).
2. **Filtro de card via `LIKE` no JSON, sem normalizar a coluna `tags`**: criar uma tabela
   de junção só para filtrar por tag seria complexidade desproporcional ao pedido — o
   `LIKE` com aspas inclusas no padrão já resolve o caso real (tags são um conjunto fixo e
   pequeno, sem risco de colisão parcial verificado nas Decisões técnicas acima).
   Reavaliar se o conjunto de tags deixar de ser fixo no futuro.
3. **Sem gráfico de tendência mensal nem alternância de "data do evento vs. avaliação"**:
   não foram pedidos (spec, Assumptions) e adicionam complexidade sem necessidade
   confirmada — every widget copiado de `talents/avaliacoes.html` precisa responder a um
   FR concreto do spec, não "porque a referência tem".
4. **Botão de feedback não tem caminho de reabilitação manual nesta fase** (spec,
   Assumptions): não foi pedido; se a necessidade de pedir de novo aparecer na prática,
   vira uma feature própria (ex.: um botão "pedir de novo mesmo assim").
