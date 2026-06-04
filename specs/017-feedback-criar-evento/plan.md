# Implementation Plan: Feedback ao criar evento

**Branch**: `017-feedback-criar-evento` | **Date**: 2026-06-04 | **Spec**: [spec.md](./spec.md)

## Summary

Adicionar, na tela de criar evento, feedback de carregamento + prevenção de duplo envio e validação
no cliente (título, data, fim>início) com realce/"shake" no campo. Tudo no template
`event_create.html` (HTML/CSS/JS). Sem mudança de rota, regra ou dados. A validação do servidor
permanece como rede de segurança.

## Technical Context

**Language/Version**: Jinja2 + CSS + JS vanilla.
**Storage**: nenhum.
**Constraints**: não alterar regras/campos do create_event; validação cliente espelha a do servidor;
servidor segue validando.
**Scale/Scope**: 1 template (`event_create.html`): id no botão, estilos `field-error`/`shake`, e um
handler de submit.

## Constitution Check

- **I. Reutilizar** ✅ — mesmo padrão do `orcamento.js` (`.orc-input-error` + shake); replico enxuto.
- **IV. Não quebrar** ✅ — só adiciona camada de UX; servidor inalterado; verificação no app.
- **V. UI/UX + feedback (v1.1.0)** ✅ — implementa exatamente os novos requisitos: loading,
  anti-duplicação, sem limpar form (validação no cliente evita o round-trip que zerava), feedback
  no campo.
- **VI. Planejar antes de codar** ✅ — este plano. Sem clarificações (pedido concreto).

## Project Structure

```text
app/templates/event_create.html
  - botão "Adicionar à Agenda": +id="btn-submit-event"
  - <style>: .field-error (borda vermelha) + .shake (animação)
  - <script> (extra_scripts): handler de submit em #event-form
```

## Design Detalhado

### 1. Botão + estilos
- Botão (linha ~433): adicionar `id="btn-submit-event"`.
- `<style>` no template: `.field-error { borda vermelha + leve sombra }` e
  `.shake { animation }` (keyframes translateX), espelhando o padrão do orçamento.

### 2. Handler de submit (#event-form)
```text
flag submitting=false
on submit:
  if submitting → preventDefault (ignora clique extra)
  limpar .field-error anteriores
  validar:
    - título (#event-title) não vazio
    - data ([name=event_date]) não vazia
    - se event-start e event_end preenchidos → fim > início
  se inválido:
    preventDefault; marcar campos com .field-error; aplicar .shake no 1º;
    scrollIntoView + focus no 1º; (re-disparo do shake via reflow)
    listeners 'input'/'change' removem o realce ao corrigir
    return
  válido:
    submitting=true; botão.disabled=true; botão.textContent='⏳ Adicionando…'
    (deixa o submit prosseguir)
```
- Campos: `#event-title` (name=title), `[name=event_date]`, `#event-start` (name=event_start),
  `[name=event_end]`. Comparação de horário com strings "HH:MM" (mesmo dia) — coerente com o
  servidor (`et <= st`).

### Verificação
- Render da página (200) com `id="btn-submit-event"`, `.shake` e `.field-error` no HTML.
- (Manual) título vazio → shake+foco, sem enviar; duplo clique em form válido → 1 submit; corrigir
  campo remove realce.

### Fora de escopo
- Repor todos os campos no erro raro da API do Google (re-render servidor) — follow-up.
- Aplicar o mesmo padrão às demais telas (será feito conforme cada uma for tocada).
