# Implementation Plan: Feedback de validação completo em "Criar evento"

**Branch**: `031-feedback-campos-evento` (sobre `030`) | **Date**: 2026-06-08 | **Spec**: [spec.md](./spec.md)

## Summary

Fechar as lacunas de validação/feedback do formulário `/events/new`: tornar **Valor de venda** e
**Vendedor responsável** obrigatórios (com aviso no campo), validar **parcelas** no "Dividido no PIX",
e garantir que todo campo com `*` seja realmente validado — no cliente (destaque imediato no campo) e
no servidor (rede de segurança). Reaproveita o destaque/rolagem (028) e o padrão de validação por
campo já usado em Data/Título. Sem migration.

## Constitution Check

- **I. Reutilizar** ✅ — estende o handler de submit e o `markError`/scroll já existentes; não cria
  fluxo novo.
- **IV. Não quebrar** ✅ — mantém clique-duplo e repopulação; adiciona validações. Verificação no app.
- **V. Feedback (NÃO-NEGOCIÁVEL)** ✅ — é o objetivo: cada campo errado avisa de forma clara e
  específica, sem mensagem enganosa.

## Estado atual (auditoria)

- **Cliente** (handler de submit em `event_create.html`): valida hoje `title`, `event_date`,
  `event_start`, `event_end` (presença) e `fim ≤ início`; destaca o campo (`field-error` + shake) e
  rola até ele. **Não** valida valor de venda, vendedor nem parcelas.
- **Servidor** (`create_event`): valida `title`, data, horário (após 030). `sale_value` é só
  `parse_brl(...)` (vira None silenciosamente); `seller_id` e `payment_installments` não são validados.
- **Template**: `Valor de venda` tem `*` (mas sem validação); `Vendedor responsável` **sem** `*`.

## Design Detalhado

### 1. Cliente — validação por campo (event_create.html, handler de submit)
Acrescentar ao bloco de validação (que já monta `invalid[]`, destaca e rola):
- **Valor de venda**: `saleEl = #sale-value`. Inválido se vazio ou `parseBRL(saleEl.value) <= 0`.
- **Vendedor**: `sellerEl = [name="seller_id"]`. Inválido se `!sellerEl.value`.
- **Parcelas**: se `#pay-method-hidden` == `pix_parcelado`, `instEl = [name="payment_installments"]`
  inválido se vazio ou fora de 2–12.
- Reusar `markError()` (já realça e limpa no `input`/`change`) e o scroll/shake do primeiro inválido.
- Mensagens não ficam "soltas": o realce é por campo; (opcional) um texto curto ao lado do primeiro.

### 2. Servidor — rede de segurança (create_event)
Acrescentar ao bloco `errors`:
- `if (parse_brl(sale_value_raw) or 0) <= 0: errors.append("Informe o valor de venda.")`
- `if not seller_id_raw.isdigit(): errors.append("Selecione o vendedor responsável.")`
- `if payment_method == "pix_parcelado":` validar `payment_inst_raw` inteiro 2–12 → senão
  `errors.append("Informe o número de parcelas (2 a 12).")`
- Erros caem no re-render já existente (preserva `old`/`old_chars`; banner + auto-scroll da 028).

### 3. Template — coerência do `*`
- Adicionar `<span style="color:var(--red)">*</span>` ao rótulo "Vendedor responsável".
- `Valor de venda` já tem `*` (agora passa a ser validado de fato).

### 4. Mensagens não enganosas
- Como valor/vendedor/horário passam a ser validados **antes** de chamar o Google, o erro genérico de
  "Google Agenda" (028) deixa de aparecer para campo vazio. Mantido só para falha real do Google.

### 5. Verificação (app real)
- Cada obrigatório vazio (um a um) → mensagem específica + campo destacado + rola até ele (cliente).
- Bypass do cliente (POST direto) → servidor recusa com a mesma mensagem (rede de segurança), 200 com
  os dados preservados, sem 500 e sem mensagem de Google.
- Valor "0,00" → inválido. Parcelas no "Dividido no PIX" vazio → aviso. 
- Preenchendo tudo certo → cria (302). Clique duplo continua bloqueado.

## Project Structure
```text
app/templates/event_create.html   # validação cliente (valor/vendedor/parcelas) + `*` no vendedor
app/calendar/routes.py            # validação servidor (sale_value, seller_id, parcelas)
```

## Fora de escopo
- Destaque por campo no re-render do servidor (cliente já faz por campo; servidor = banner + scroll).
- Refinar/segmentar a mensagem de falha do Google além do que a 030/031 já evita.
- Outros formulários do sistema. Sem migration.
