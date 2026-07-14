# Implementation Plan: Reorganizar e Filtrar a Tela de Gastos Extras (125)

**Branch**: `125-reorganizar-gastos-extras` | **Date**: 2026-07-13 | **Spec**: [spec.md](./spec.md)

## Summary

Mudança 100% de apresentação em `app/templates/gastos/index.html` — sem tocar em
`app/gastos/routes.py`. Reaproveita, adaptado, o padrão já usado e testado em
`financeiro/pagamentos.html` (feature já existente): cartões de resumo clicáveis como
filtro de situação (`.kpi-filter`/`.kpi-active`, JS puro, sem reload) + busca por texto em
tempo real sobre as linhas já renderizadas. O formulário de cadastro (hoje sempre aberto,
empurrando a lista para baixo) vira um painel recolhível, aberto por um botão "+ Novo
gasto" no cabeçalho — e continua se abrindo sozinho se houver uma mensagem de erro do
próprio cadastro, para não esconder um erro que o usuário precisa ver. Badges trocam cor
solta por `.badge-green`/`.badge-amber`/`.badge-red`/`.badge-gray`/`.badge-blue` já
padronizadas no sistema. Cabeçalho ganha `page_subtitle` com a contagem, no mesmo padrão
de `clientes/list.html`.

## Technical Context

**Stack**: Jinja2 + JS vanilla (o existente). **Storage**: nenhuma mudança — mesma query
que já existe em `index()`.

**Arquivos**: só `app/templates/gastos/index.html`. Nenhuma rota, migration ou
permissão muda (Assumption da spec).

**Testing**: verificação funcional (a rota/dados não mudam, mas confere que a página
continua renderizando e que os dados client-side — `data-status`, contadores — batem com
o banco) + conferência visual/manual no app real dos filtros e da busca (comportamento é
JS de navegador, não testável pelo test client do Flask).

## Design

### Cabeçalho
```
page_title: Gastos Extras (igual)
page_subtitle: "{{ expenses|length }} gasto(s){{ ' no histórico' if is_superadmin else '' }}"
page_actions: botão "+ Novo gasto" (abre/fecha o painel de cadastro)
```

### Barra de filtro (substitui o `kpi-grid` hoje só-superadmin)
Um `kpi-grid` único, visível para **todos** os usuários autenticados (FR-001 não
restringe a superadmin) — 4 cartões clicáveis, `data-filter` = `all|pendente|aprovado|
rejeitado`, contagem sempre visível; a soma em R$ (informação sensível de balanço) só
aparece como sub-linha nos cartões "Pendentes"/"Aprovados" **quando `is_superadmin`** —
preserva FR-008 exatamente como hoje (`total_pendente`/`total_aprovado` continuam
calculados só para super admin, sem mudança no routes.py; a contagem por situação é
derivada no template via `selectattr`, não precisa de query nova).

### Busca
Campo de texto acima da tabela, mesmo padrão de `buildRowIndex`/`normTxt`/
`rowMatchesSearch` de `financeiro/pagamentos.html`, adaptado: índice de busca por linha
soma o texto de todo `<td>` **exceto** os marcados `data-noindex` (coluna "Nota Fiscal" —
só um link "Ver" — e a coluna de ações). Combina com o filtro de situação ativo (FR-003).

### Painel de cadastro recolhível
`<div id="novo-gasto-panel">` em volta do `<form>` de "Registrar novo gasto" existente
(campos/validação intocados — FR-005). Estado inicial: `display:none`, EXCETO se houver
uma mensagem `flash` de categoria `error` no momento do render (indica que o usuário acabou
de tentar cadastrar e falhou) — nesse caso nasce aberto, para o erro continuar visível
(não pode piorar o "nunca esconder um erro" já garantido hoje). Botão "+ Novo gasto" no
cabeçalho alterna `display`.

### Badges
| Hoje (inline) | Depois |
|---|---|
| `style="background:var(--success)"` (Aprovado) | `badge badge-green` |
| `style="background:var(--danger)"` (Rejeitado) | `badge badge-red` |
| `style="background:var(--muted)"` (Pendente) | `badge badge-amber` |
| Pago / No banco / A pagar (desembolso) | `badge-green` / `badge-blue` / `badge-gray` |

### Linhas da tabela
`<tr class="gasto-row" data-status="{{ e.status }}">` (igual ao `tr.pay-row` de
pagamentos.html) + `<tr id="empty-filter-row">` oculta para o caso "filtro sem resultado"
(distinto do estado vazio atual "nenhum gasto registrado ainda", que continua existindo
para quando não há NENHUM gasto).

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Todo o mecanismo de filtro/busca é adaptado do que já existe e funciona em `financeiro/pagamentos.html` — zero mecanismo novo inventado; badges passam a usar as classes já existentes em vez de duplicar cor inline. |
| II/III | N/A — sem Python/camadas tocadas nesta feature (só template). |
| IV. Não quebrar | ✅ `routes.py` intocado — mesma query, mesmos campos, mesma validação do formulário (FR-005); regras de acesso idênticas (FR-008); filtro/busca são só apresentação client-side, nunca alteram o que existe no banco. |
| V. UI/UX | ✅ Painel de cadastro some por padrão mas reabre sozinho se houver erro do próprio cadastro (não esconde erro do usuário); botão de fechar/abrir e cartões de filtro têm feedback visual de estado ativo (`kpi-active`), consistente com Princípio V/feature 124. |
| VI. Planejar | ✅ Este plano, com diagnóstico concreto feito por leitura de código (badges/CSS/estrutura) antes de qualquer alteração. |
| VII. Moeda BR | ✅ Sub-linhas de R$ continuam usando `fmt_brl` já existente — fonte única preservada. |
| VIII. Mobile-first | N/A — tela interna do painel, não superfície pública listada no Princípio VIII; mesmo assim a barra de filtro usa `flex-wrap` (como em pagamentos.html) para não quebrar em telas estreitas. |

**Gate: PASS.**

## Decisões

1. **Contadores por situação calculados no template (`selectattr`), não em nova query**:
   `expenses` já é a lista completa que a view busca — evita adicionar `GROUP BY`/query
   extra para um número que já está disponível em memória (YAGNI).
2. **Cartões de filtro visíveis para todos, R$ só para super admin**: satisfaz FR-001
   (filtro é de todo mundo) sem tocar na regra de acesso existente ao balanço financeiro
   (FR-008) — a contagem não é informação sensível (é o próprio usuário vendo os próprios
   gastos, ou o super admin vendo tudo, como já é hoje).
3. **Sem filtro dedicado de categoria**: a busca de texto já cobre por categoria (FR-002),
   mesma decisão já validada em `pagamentos.html` (que também não tem seletor dedicado por
   tipo além da busca) — evita adicionar um segundo mecanismo de filtro para o que a busca
   já resolve.
4. **Painel de cadastro reabre sozinho em caso de erro**: sem essa regra, recolher o
   formulário por padrão criaria uma regressão de UX (erro invisível) — checagem simples
   via `get_flashed_messages(with_categories=true)` no template, sem mudança de rota.
