# Tasks: Feedback de senha (shake) + não limpar form ao falhar criação

**Input**: `specs/018-feedback-followups/`
**Tests**: render + verificação lógica/manual.

## Phase 1: Senha (FU1)
- [ ] T001 change_password.html: remover `disabled` do botão + parar de desabilitá-lo no JS; CSS
      `.shake`; submit handler com shake nos requisitos faltantes + mismatch + loading/anti-duplo.
- [ ] T002 reset_password.html: botão com id; CSS `.shake`; submit handler espelhando o T001.

## Phase 2: Criar evento — preservar dados (FU2)
- [ ] T003 calendar/routes.py: helper `_render_create_form(...)` com `old`/`old_chars`; GET passa
      vazios; renders de erro passam `request.form` + lista de personagens enviada.
- [ ] T004 event_create.html: campos usam `old` (value/selected/checked) com fallback p/ prefill.
- [ ] T005 event_create.html: `RESUBMIT_CHARS` reconstrói as linhas de personagem (label, makeup,
      cantor, cachê, figurino) quando vier do re-render de erro.

## Phase 3: Verificação
- [ ] T006 ruff nos .py; render das 3 telas (200) com novos elementos; POST de erro reexibe
      título/data/personagens; conferência manual do shake e do anti-duplo-clique.

## Dependencies
- T001/T002 independentes. T003→T004→T005. T006 ao fim.

## Notes
- Anexos não são restauráveis (limite do navegador) — única exceção.
