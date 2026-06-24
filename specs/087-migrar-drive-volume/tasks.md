# Tasks: Migrar Drive → volume (087)

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Sem testes automatizados solicitados — verificação manual contra `manto_local`.

## Phase 1: User Story 1 — Uploads no volume organizados (P1)

- [X] T001 [US1] Confirmar que os uploads usam subpastas por tipo dentro de `UPLOAD_FOLDER`
  (`/app/instance/uploads`) e que `USE_S3` desligado grava no volume (sem mudança de código; documentar
  no plano/relatório). Sem alteração de caminho (mount path == pasta de uploads).

## Phase 2: User Story 2 — Migração Drive → volume (P1) 🎯 MVP

- [X] T002 [US2] Helpers em `app/cli.py`: `_drive_file_id(url)` (lh3 `/d/<id>`, drive `open?id=`/`?id=`/
  `/file/d/<id>`), `_download_drive(url)` (lh3 direto com `=s0`; doc via `uc?export=download&id=`;
  extensão pelo Content-Type) e `_save_bytes_to_volume(data, ext, subfolder)` via `save_file`.
- [X] T003 [US2] Comando `migrate-drive-to-volume` (registrado em `register_commands`) com `--dry-run` e
  `--limit`: percorre Talent, migra `photo_face_path`/`photo_full_path`→`talent_photos` e
  `doc_photo_path`/`cnh_file_path`→`talent_docs`, atualiza o campo e dá commit por talento.
- [X] T004 [US2] Idempotência + resiliência: só processa links de Drive (pula `/uploads/` e vazios);
  try/except por arquivo mantendo o link original em falha; contadores OK/ERRO/SKIP e resumo final.

## Phase 3: Polish & Verificação

- [X] T005 Verificar contra `manto_local`: dry-run conta ~649 arquivos; parser de URL correto; migração
  real com `--limit` baixa+salva no volume e atualiza link; reexecução pula migrados; falha simulada não
  derruba. Rodar `ruff` (sem erros novos).

## Dependencies

- T002 → T003 → T004 (helpers antes do comando). Tudo em `app/cli.py`.
- T005 por último.

## MVP

User Story 2 (comando de migração) é o MVP — destrava a saída do Drive.
