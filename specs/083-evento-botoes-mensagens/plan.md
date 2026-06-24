# Implementation Plan: Botões de mensagem no evento (083)

**Branch**: `083-evento-botoes-mensagens` | **Date**: 2026-06-24 | **Spec**: [spec.md](spec.md)

## Summary

Dois botões no `page_actions` da página do evento (`event_detail.html`), visíveis só para COMERCIAL/
SUPERADMIN:

1. **Confirmar dados do evento** — monta e copia a mensagem de confirmação (saudação por horário +
   personagens + data pt-BR + local).
2. **Cobrança** — habilitado só na data limite/atraso com saldo em aberto; copia mensagem de cobrança
   com o valor exato em aberto. Caso contrário fica desabilitado e translúcido.

A montagem dos textos é feita no cliente (JS) para a saudação refletir o horário do clique; os dados
fixos (personagens, data formatada, local, valor, vencimento, flag de habilitação) são calculados no
servidor e embutidos via um bloco JSON no template. **Sem model novo, sem migration.**

## Technical Context

**Language/Version**: Python 3 / Flask / Jinja2 + JS vanilla.

**Arquivos**:
- `app/calendar/routes.py` — em `event_detail()`: helper `_format_event_date_ptbr()` (dia da semana e
  mês por extenso pt-BR) e cálculo de `cobranca` (valor em aberto + data limite + flag). Passa novas
  variáveis ao `render_template`.
- `app/templates/event_detail.html` — dois botões no bloco `page_actions` + script de montagem/cópia.

**Cálculo do valor em aberto / vencimento** (helper no route):
- Se o evento tem parcelas (`event.installments`): `outstanding = Σ amount das não recebidas`;
  `due = menor due_date entre as não recebidas`.
- Senão: `outstanding = (sale_value or 0) − received_total` (recebimentos `EventPayment`);
  `due = event.payment_due_date`.
- `cobranca_enabled = due is not None and due <= hoje and outstanding > 0`.
- Valor formatado server-side em pt-BR ("R$ 1.234,56") para evitar problemas de locale no cliente.

**Saudação (JS, no clique)**: hora 05–11 → "Bom dia"; 12–17 → "Boa tarde"; 18–04 → "Boa noite".

**Cópia**: `navigator.clipboard.writeText` com fallback `document.execCommand('copy')`; feedback visual
trocando o rótulo do botão para "✅ Copiado!" por ~1,5s.

**Testing**: contra **`manto_local`** — para um evento real, conferir a string de confirmação (saudação
nos 3 períodos, personagens sem prefixo, data pt-BR, local) e a lógica de cobrança (habilitado só com
vencimento/atraso e saldo; valor em aberto correto). `ruff` sem erros novos.

**Scale/Scope**: 1 rota (contexto) + 1 template (UI/JS). Nenhuma mudança de schema.

## Constitution Check

- **I. Qualidade**: helper com type hints + docstring; sem lógica de negócio no template (só montagem
  de texto).
- **IV. Não quebrar**: adiciona variáveis novas ao contexto e botões novos; nada existente é alterado.

**Resultado**: PASS — sem migration.

## Project Structure

```text
app/calendar/routes.py        — _format_event_date_ptbr(); cálculo cobrança; novas vars no render
app/templates/event_detail.html — 2 botões em page_actions + <script> de montagem/cópia
```

## Complexity Tracking

> Sem violações.
