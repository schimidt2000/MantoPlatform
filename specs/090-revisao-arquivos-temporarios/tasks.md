# Tasks: Arquivos temporários na Revisão (090)

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Sem testes automatizados solicitados — verificação manual contra `manto_local`.

## Phase 1: Dados

- [X] T001 `ReviewAsset`: colunas `expires_at`, `finalized_at`, `file_removed`, `version` + propriedades
  `is_available`/`days_left` em `app/models.py`.
- [X] T002 Migração manual (`down_revision='y1b2c3d4e5f6'`): adiciona colunas; existentes recebem
  `expires_at = created_at + 7 dias`, `version=1`, `file_removed=false`.

## Phase 2: US2 — Expiração automática (P1) 🎯 MVP

- [X] T003 [US2] `app/revisao/cleanup.py::cleanup_expired_review_files()` (remove arquivo de vencidos não
  finalizados, marca `file_removed`, idempotente).
- [X] T004 [US2] Thread diária `_start_review_cleanup` em `app/__init__.py` + comando
  `flask cleanup-review-files` em `app/cli.py`.

## Phase 3: US1 — Aviso + prazo no upload (P1) 🎯 MVP

- [X] T005 [US1] `_save_assets` define `expires_at = utcnow + 7d`; aviso de 7 dias em `revisao/new.html`;
  selos de prazo/estado em `revisao/space.html`.

## Phase 4: US3/US4 — Substituir e Finalizar (P2)

- [X] T006 [US3] Rota `POST /revisao/asset/<aid>/replace` (criador): mesmo tipo, remove antigo, salva
  novo, `version+1`, reinicia prazo, mantém comentários.
- [X] T007 [US4] Rota `POST /revisao/asset/<aid>/finalize` (criador): remove arquivo, marca finalizado.
- [X] T008 [US3/US4] `revisao/asset.html`: estado "arquivo removido" no lugar do player (mantendo
  comentários); controles de substituir/finalizar (com confirmação) para o criador; "expira em N dias" e
  "versão N".

## Phase 5: Verificação

- [X] T009 Verificar contra `manto_local`: migração; expires no upload; substituir (versão+prazo+remove
  antigo, comentários mantidos); finalizar (remove arquivo); cleanup remove vencido não finalizado sem
  apagar comentários; permissões. `ruff` ok. Limpar dados.

## Dependencies

- T001→T002→(resto). T003→T004. T006/T007→T008. T009 por último.

## MVP

US1 + US2 (aviso + prazo + limpeza automática). US3/US4 (substituir/finalizar) na sequência.
