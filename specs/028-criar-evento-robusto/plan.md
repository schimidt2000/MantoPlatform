# Implementation Plan: Envio de "Criar evento" robusto a falhas

**Branch**: `028-criar-evento-robusto` | **Date**: 2026-06-08 | **Spec**: [spec.md](./spec.md)

## Summary

Tornar o desfecho do envio de `/events/new` sempre visível e amigável: (1) rolar até o erro quando o
formulário recarrega com falha; (2) transformar qualquer falha do Google Agenda em aviso amigável (não
tela técnica/500); (3) recuperar o botão "Adicionar à Agenda" se o envio não responder (watchdog).
Reaproveita o alerta e o handler de submit já existentes. Sem migration.

## Constitution Check

- **I. Reutilizar** ✅ — estende o alerta de erro e o handler de submit existentes em
  `event_create.html`; não cria fluxo paralelo.
- **IV. Não quebrar** ✅ — mantém a proteção de clique duplo e a repopulação de campos; só adiciona
  visibilidade e recuperação. Verificação no app real. Sem migration.
- **V. Feedback (NÃO-NEGOCIÁVEL)** ✅ — é exatamente o objetivo: nunca deixar o usuário sem resposta.

## Estado atual (levantamento)

- `app/calendar/routes.py` `create_event` (POST):
  - Bloco de validação → re-render com `errors` (linha ~1872).
  - `insert_event(...)` dentro de `try/except RuntimeError` → re-render com `[str(exc)]` (linha ~1881).
    Qualquer exceção **não-RuntimeError** (ex.: `HttpError` da API Google) **escapa → 500**.
- `app/templates/event_create.html`:
  - Alerta de erro no topo: `{% if errors %}<div class="alert alert-error" …>` (linha ~100). Sem id,
    sem auto-scroll.
  - Handler de submit (IIFE, ~linha 813): valida, dá `scrollIntoView` no **campo** inválido, trava
    duplo envio e troca o botão para "Adicionando…". **Não** rola até o bloco de erro do servidor
    (esse é re-render) e **não** tem watchdog se a resposta não vier.

## Design Detalhado

### 1. Servidor — falha do Google vira aviso amigável (FR-003/FR-004)
- Em `create_event`, trocar `except RuntimeError` em volta de `insert_event` por um `except Exception`:
  - Logar o erro real (`current_app.logger.exception(...)`) para diagnóstico.
  - Re-render com uma mensagem **amigável** e fixa, ex.:
    "Não foi possível criar o evento na Agenda do Google agora. Verifique a conexão e tente novamente.
    Se persistir, avise o suporte." — preservando `old=request.form` e `old_chars` (já é o padrão).
  - Caso específico "Google não conectado" (RuntimeError conhecido) pode manter orientação de
    reconectar, também amigável.
- Não muda a ordem (insert_event antes de salvar no banco); só o tratamento da exceção.

### 2. Tela — rolar até o erro + destaque (FR-001/FR-002)
- Dar um `id="form-errors"` ao bloco de alerta e `tabindex="-1"`.
- Pequeno script: se o bloco existir ao carregar a página, `scrollIntoView({behavior:'smooth',
  block:'center'})` e `focus()` — assim, todo re-render com erro já abre na mensagem.
- Manter classe `alert alert-error` (destaque já existente).

### 3. Tela — watchdog do botão (FR-005/FR-006/FR-007)
- No handler de submit, quando o envio é válido e dispara (estado atual: `submitting=true`, botão
  "Adicionando…"), agendar um `setTimeout` (~15s):
  - Se a página ainda estiver aqui (não navegou), reabilitar o botão, restaurar o texto original,
    `submitting=false`, e mostrar um aviso visível ("A conexão demorou. Tente novamente.").
  - Em envio bem-sucedido a página navega antes do timeout → callback não chega a incomodar
    (FR-006). Usar `pagehide`/`beforeunload` para cancelar o timer ao navegar, evitando aviso falso.
- Mantém a proteção de clique duplo (`submitting`) intacta (FR-007).

### 4. Verificação (app real)
- Erro de validação no fim da página → rola até a mensagem.
- Google indisponível (simular exceção em `insert_event`) → aviso amigável, sem 500, campos
  preservados.
- Envio "sem resposta" (simular atraso/cancelar) → botão recupera + aviso após ~15s.
- Sucesso normal → cria e redireciona, sem aviso falso.
- Clique duplo → continua bloqueado.

## Project Structure
```text
app/calendar/routes.py        # except Exception em volta de insert_event → aviso amigável + log
app/templates/event_create.html
                              # id no bloco de erros + auto-scroll; watchdog no handler de submit
```

## Fora de escopo
- Reescrever o envio como AJAX/fetch (mantém POST tradicional).
- Aplicar o padrão a outros formulários (pode vir depois).
- Mudança de banco / migration.
