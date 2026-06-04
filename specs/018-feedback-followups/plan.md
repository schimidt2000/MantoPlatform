# Implementation Plan: Feedback de senha (shake) + não limpar form ao falhar criação

**Branch**: `018-feedback-followups` | **Date**: 2026-06-04 | **Spec**: [spec.md](./spec.md)

## Summary

FU1: nas telas de senha (`change_password`, `reset_password`), habilitar o botão e, ao tentar
salvar com requisitos faltando, bloquear + chacoalhar os requisitos não cumpridos (+ loading /
anti-duplo-clique no envio válido). FU2: no `create_event`, repassar os valores enviados ao
template em qualquer re-render por erro, repopulando campos e linhas de personagem (anexos não são
restauráveis pelo navegador).

## Constitution Check
- **IV. Não quebrar** ✅ — servidor de senha já valida (rede de segurança); `old` é dict sempre
  presente (GET vazio) para não quebrar template; verificação no app.
- **V. UI/UX + feedback (v1.1.0)** ✅ — implementa shake no bloqueio, anti-duplicação, e "nunca
  limpar o form".

## Project Structure

```text
app/templates/portal/change_password.html   # botão sem 'disabled'; submit: shake unmet + loading
app/templates/portal/reset_password.html     # mesmo padrão (botão + submit handler + shake/loading)
app/calendar/routes.py                        # create_event: helper _render_create_form(old, old_chars)
app/templates/event_create.html               # value/selected/checked a partir de `old`; char rows de old_chars
```

## Design Detalhado

### FU1 — change_password.html
- Botão: remover atributo `disabled`; parar de alternar `submit-btn.disabled` no `checkPw`
  (mantém o cálculo de força/ícones).
- CSS: `.shake` (keyframes translateX).
- Submit handler em `#pw-form`: se houver regra não cumprida (`!re.test(pw)`) ou senhas divergentes,
  `preventDefault`, aplicar `.shake` em cada `<li>` faltante (e no `#match-hint`), focar
  `#new_password`; senão, `submitting=true`, desabilitar botão + "Salvando…".

### FU1 — reset_password.html
- Botão ganha `id`; CSS `.shake`; mesmo handler (regras do `checkStrength`), shake nos `<li>` com
  "✗", loading + anti-duplo-clique.

### FU2 — create_event (routes.py)
- Helper `_render_create_form(errors, prefill, old=None, old_chars=None)` → render com
  `old=old or {}`, `old_chars=old_chars or []`.
- GET: `old={}`, `old_chars=[]`.
- Renders de erro (validação e RuntimeError): `old=request.form`, `old_chars` montado dos arrays
  `character_names[]`/`char_needs_makeup[]`/`char_is_singer[]`/`char_cache[]`/`figurino_sheet_ids[]`.

### FU2 — event_create.html
- Campos passam a usar `old`: `event_date`, `event_start`, `event_end`, `event_type` (selected),
  `location`, `description`, `title`, `needs_rehearsal` (checked), `sale_value`, `transport_value`,
  `acrescimo_value`, `seller_id` (selected), `sale_date`, `payment_method` (hidden),
  `payment_installments`, `payment_due_date`, `with_invoice` (hidden). Fallback: `old` → `prefill`/
  vazio. Como `old` é sempre dict, `old.get(...)` é seguro.
- Char rows: `RESUBMIT_CHARS = {{ old_chars | tojson }}`; na init, se houver, construir as linhas a
  partir dele (label, makeup, singer, role 'character', sheetId) e setar o cachê de cada linha; caso
  contrário, mantém o comportamento atual (ORC_CACHES ou 1 linha vazia).

### Verificação
- Render das 3 telas (200) com os novos elementos.
- (Lógico) `create_event` POST com erro forçado → resposta reexibe título/data/personagens enviados.
- (Manual) senha incompleta → shake; duplo clique → 1 envio.

### Fora de escopo
- Restaurar anexos (impossível no navegador). Re-destacar visualmente botão de forma de
  pagamento/NF é best-effort (o valor é preservado no hidden).
