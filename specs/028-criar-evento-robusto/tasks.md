# Tasks: Envio de "Criar evento" robusto a falhas

**Input**: `specs/028-criar-evento-robusto/`
**Tests**: boot + ruff + verificação no app real (reproduzir os 4 desfechos). Sem migration.

## Phase 1: Servidor — falha do Google amigável
- [x] T001 `app/calendar/routes.py` `create_event`: trocar `except RuntimeError` em volta de
      `insert_event` por `except Exception`; logar erro real (`logger.exception`); re-render com
      mensagem amigável (preservando `old`/`old_chars`). Manter caso "Google não conectado" amigável.

## Phase 2: Tela — erro sempre visível
- [x] T002 `event_create.html`: dar `id="form-errors"` + `tabindex="-1"` ao bloco de alerta de erro.
- [x] T003 `event_create.html`: script que, havendo `#form-errors` no load, rola até ele
      (`scrollIntoView`) e foca.

## Phase 3: Tela — watchdog do botão
- [x] T004 `event_create.html` (handler de submit): após disparar envio válido, agendar timeout (~15s)
      que reabilita o botão, restaura o texto, zera `submitting` e mostra aviso "A conexão demorou.
      Tente novamente."; cancelar o timer em `pagehide` (evita aviso falso no sucesso). Não regredir a
      trava de clique duplo.

## Phase 4: Verificação
- [x] T005 boot + `ruff check`/`ruff format`. Cenários no app: (a) erro de validação no fim → rola até
      a mensagem; (b) `insert_event` lançando exceção → aviso amigável (sem 500), campos preservados;
      (c) envio sem resposta → botão recupera + aviso após ~15s; (d) sucesso → cria e redireciona sem
      aviso falso; (e) clique duplo continua bloqueado.

## Dependencies
- T001 independente. T002 → T003. T004 independente. T005 por último.

## Notes
- Reaproveita alerta de erro e handler de submit existentes (Princípio I). Sem migration.
- Watchdog ~15s: cobre reinício de servidor/conexão sem atrapalhar envios normais (que navegam antes).
