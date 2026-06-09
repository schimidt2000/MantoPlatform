# Implementation Plan: Filtro por card + troca de situação em tempo real (Pagamentos)

**Branch**: `033-pagamentos-filtro-realtime` | **Date**: 2026-06-09 | **Spec**: [spec.md](./spec.md)

## Summary

Tornar os 5 cards de resumo clicáveis (filtro client-side por situação) e mudar a troca de situação
para **tempo real** (sem recarregar): o endpoint `set-status` passa a responder JSON quando chamado
via fetch; o JS atualiza a linha, recomputa os totais dos cards e reaplica o filtro ativo. O filtro
ativo é guardado para sobreviver a recarregamentos legítimos (mês / ações em massa). Sem migration.

## Constitution Check

- **I. Reutilizar** ✅ — reaproveita a rota `set_payment_status` (acrescenta resposta JSON), os totais
  já calculados e o template existente; sem fluxo paralelo.
- **IV. Não quebrar** ✅ — mantém o caminho de formulário como reserva; ações em massa/exportação
  intactas; verificação no app. Sem migration.
- **V. Feedback** ✅ — troca dá retorno imediato; falha reverte e avisa (sem mudança fantasma).
- **VII. Valor BR** ✅ — totais recomputados continuam no padrão brasileiro.

## Estado atual

- `pagamentos()` calcula `items` (cada um com `type`, `id`, `status`, `is_future`, `amount`, …) e os
  totais `total_val/total_pago/total_banco/total_pend/total_future`.
- Template: KPIs estáticos (linhas 28-49); cada linha tem `data-item-type`/`data-item-id`; a situação
  é um `<form>` com `<select onchange="this.form.submit()">` → POST `/set-status` → `redirect`
  (recarrega tudo).
- `set_payment_status`: trata commission/salary/expense/role e retorna `redirect(next_url)`.

## Design Detalhado

### 1. Backend — resposta JSON no `set_payment_status`
- Detectar chamada AJAX (`request.headers.get("X-Requested-With") == "XMLHttpRequest"` ou
  `request.form.get("ajax") == "1"`).
- Mesma lógica de hoje; ao final, se AJAX → `return jsonify({"ok": True, "status": <status efetivo>})`
  (para commission, o efetivo é "pago" ou "nao_pago"); senão → `redirect(next_url)` (reserva).
- Em entrada inválida AJAX → `jsonify({"ok": False}), 400`.

### 2. Template — dados nas linhas + cards clicáveis
- Em cada `<tr>`: adicionar `data-status="{{ item.status }}"`,
  `data-future="{{ '1' if item.is_future else '' }}"`,
  `data-amount="{{ (item.amount or 0) | float }}"`.
- Cards: dar a cada KPI um `data-filter` (`all`/`pago`/`no_banco`/`pendente`/`futuro`), `role="button"`,
  `tabindex`, cursor pointer e estilo de "ativo".
- Estado vazio do filtro: um `<tr id="empty-filter-row">` oculto com "nenhum item nesta situação",
  mostrado quando o filtro não casa com nenhuma linha.

### 3. JS — filtro + tempo real (no `extra_scripts`)
- **Filtro**: `applyFilter(f)` mostra/oculta linhas conforme `data-status`/`data-future`:
  - `all` → todas; `pago` → status pago; `no_banco` → status no_banco;
  - `pendente` → status nao_pago e `!future`; `futuro` → status nao_pago e `future`.
  - Marca o card ativo; clicar no card ativo de novo volta para `all`.
  - Persistir em `localStorage` (chave por página) e reaplicar no `load` (sobrevive a reload de mês /
    ações em massa).
- **Troca de situação (tempo real)**: no `change` do select, em vez de `form.submit()`:
  - `fetch('/financeiro/pagamentos/set-status', {method:'POST', headers:{X-Requested-With}, body:
    FormData})`; em sucesso: atualizar `tr.dataset.status`, classes `row-pago/row-banco`, classe do
    select (`pay-status-*`), recomputar totais e reaplicar o filtro. Em falha: reverter o select ao
    valor anterior + aviso.
- **Recompute de totais (client-side)**: somar `data-amount` por categoria (mesma regra dos totais do
  servidor) e escrever nos KPIs, formatando em pt-BR (reutiliza `window.MoneyMask.format` da 027 —
  recebe centavos; converter de reais p/ centavos ao formatar — ou um helper BR simples local).
- Manter `bulk`/`copy` como estão; o bulk continua via form (reload) e o filtro reaplica do
  localStorage.

### 4. Verificação (app real)
- Clicar cada card filtra corretamente; clicar de novo limpa; "Total" mostra tudo.
- Trocar situação não recarrega; linha + totais atualizam; filtro mantido; item que sai do filtro some.
- Falha simulada de rede → select reverte + aviso.
- Trocar mês / bulk → filtro reaplica.
- `set-status` sem AJAX (reserva) → continua redirecionando e salvando.

## Project Structure
```text
app/financeiro/routes.py                 # set_payment_status: resposta JSON p/ AJAX (reserva mantida)
app/templates/financeiro/pagamentos.html # data-* nas linhas; cards clicáveis; JS de filtro + tempo real
```

## Fora de escopo
- Nova regra de ordenação por coluna (mantém ordenação por data atual).
- Mudança de banco. Tornar bulk/exportação em AJAX (seguem como hoje).
```
