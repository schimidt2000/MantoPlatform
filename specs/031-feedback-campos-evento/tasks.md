# Tasks: Feedback de validação completo em "Criar evento"

**Input**: `specs/031-feedback-campos-evento/`
**Tests**: boot + ruff + verificação no app real (cada campo). Sem migration. Inclui o fix 030.

## Phase 1: Servidor (rede de segurança)
- [x] T001 `app/calendar/routes.py` `create_event`: validar
      - `sale_value` obrigatório e > 0 → "Informe o valor de venda.";
      - `seller_id` obrigatório (dígito) → "Selecione o vendedor responsável.";
      - se `payment_method == "pix_parcelado"`, `payment_installments` inteiro 2–12 → "Informe o
        número de parcelas (2 a 12)."
      Erros caem no re-render existente (preserva `old`/`old_chars`).

## Phase 2: Cliente (feedback por campo)
- [x] T002 `event_create.html` (handler de submit): adicionar ao `invalid[]`
      valor de venda (vazio/≤0 via `parseBRL`), vendedor (`[name=seller_id]` vazio) e parcelas (se
      método `pix_parcelado`, vazio/ fora de 2–12). Reusar `markError` + scroll/shake do 1º inválido.
- [x] T003 `event_create.html`: adicionar `*` ao rótulo "Vendedor responsável".

## Phase 3: Verificação
- [x] T004 boot + `ruff check`. Cenários no app:
      (a) valor de venda vazio → bloqueia + destaca + rola; (b) vendedor não selecionado → idem;
      (c) "Dividido no PIX" sem parcelas → aviso; (d) bypass do cliente (POST direto) → servidor
      recusa com a mesma mensagem, 200, dados preservados, sem 500/sem "Google"; (e) tudo certo →
      cria (302); (f) clique duplo continua bloqueado.

## Dependencies
- T001 e T002/T003 independentes; T004 por último.

## Notes
- Reusa `markError`/scroll (028) e `parseBRL` da página. Campos `*` agora todos validados
  (Data, Início, Fim, Título, Valor de venda, Vendedor). Sem migration.
