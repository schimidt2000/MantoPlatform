# Tasks: Upload de Fotos e Documentos (Talento + Figurino) (155)

**Input**: Design documents from `specs/155-upload-fotos-documentos/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/upload-endpoints.md, quickstart.md

**Tests**: sem testes automatizados unitários pedidos na spec — verificação é o script de
paridade `scripts/db/verify_155_upload_fotos_documentos.py` contra `manto_local` (padrão do
projeto, ver CLAUDE.md), gerado na Phase de Polish.

**Organização**: por user story, igual à spec.md (US1 = talento, P1; US2 = figurino, P2).

## Phase 1: Setup

- [X] T001 Confirmar `manto_local` (Postgres) atualizado e nas migrations mais recentes
      (`python -m flask db heads` com `DATABASE_URL` apontando pra cópia local) — nenhuma
      migration nova é necessária nesta fatia (sem campo de banco novo).

## Phase 2: Foundational

Nenhuma tarefa bloqueante nova — `talent_ops.py`/`figurino_ops.py`, `app/storage.py`
(`save_file`/`delete_file`) e os endpoints de escrita já existem desde a 154/153.

## Phase 3: User Story 1 — Enviar/substituir/remover foto ou documento do talento (P1)

**Goal**: Casting/Superadmin envia, substitui e remove foto de rosto/corpo inteiro/documento/
CNH pela tela React do perfil do talento.

**Independent Test**: no perfil React de um talento, enviar uma foto de rosto e ver a miniatura
atualizada sem reload; repetir para corpo inteiro/documento/CNH; remover uma delas.

- [X] T002 [US1] Implementar `save_talent_photo(talent, *, photo_type, file_storage) -> str |
      None` e `remove_talent_photo(talent, *, photo_type) -> None` em
      `app/talents/talent_ops.py` (validação de extensão por `photo_type`, `delete_file` do
      arquivo antigo antes de `save_file`, mesma regra hoje em `upload_talent_photo` —
      `app/talents/routes.py:753`).
- [X] T003 [US1] Reescrever `upload_talent_photo` (`app/talents/routes.py:753`) como wrapper
      fino sobre `save_talent_photo` (parse de `request.form`/`request.files`, `flash`,
      `redirect` — comportamento Jinja idêntico ao de hoje).
- [X] T004 [US1] Adicionar rota Jinja `POST /talents/<id>/remove-photo` em
      `app/talents/routes.py` chamando `remove_talent_photo` (capacidade nova — ver spec
      Assumptions), com o mesmo gate `_can_edit_talent()`.
- [X] T005 [US1] Implementar `POST /api/talents/<id>/photo` (multipart) e
      `DELETE /api/talents/<id>/photo?photo_type=...` em `app/api/talents_write.py`, gate
      `_can_edit_talent()`, devolvendo `get_talent_profile(talent)` no sucesso (contrato em
      `contracts/upload-endpoints.md`).
- [X] T006 [P] [US1] Criar `useUploadTalentPhoto`/`useRemoveTalentPhoto` em
      `frontend/apps/internal/src/lib/talents.ts` (mutação com `FormData`, mesmo padrão de
      `eventAttachments.ts`).
- [X] T007 [US1] Adicionar na `frontend/apps/internal/src/pages/TalentDetailPage.tsx` os 4
      campos de foto/documento (input de arquivo + preview local via
      `URL.createObjectURL`/`assetUrl` + botão remover), visíveis só quando `can_edit`; erro
      400 exibido inline; `loading` no botão durante a mutação.

**Checkpoint**: US1 completa e testável isoladamente (fluxo de foto/documento de talento
funcionando ponta a ponta).

---

## Phase 4: User Story 2 — Enviar/rotacionar/remover foto da ficha de figurino (P2)

**Goal**: Figurino/Superadmin envia, gira e remove a foto de uma ficha de figurino pela tela
React.

**Independent Test**: numa ficha sem foto, enviar uma imagem, girar 90°, remover — cada ação
reflete na tela imediatamente.

- [X] T008 [US2] Implementar `save_figurino_photo(sheet, *, file_storage) -> str | None`,
      `remove_figurino_photo(sheet) -> None` e `rotate_figurino_photo(sheet, *, direction) ->
      str | None` em `app/figurino/figurino_ops.py` (paridade com o bloco de upload em
      `new_sheet`/`edit_sheet` e com `rotate_photo` — `app/figurino/routes.py:188`).
- [X] T009 [US2] Reescrever `new_sheet`/`edit_sheet` (bloco de upload) e `rotate_photo` em
      `app/figurino/routes.py` como wrappers finos sobre `figurino_ops`; adicionar rota Jinja
      `POST /figurinos/<id>/remove-photo` chamando `remove_figurino_photo` (capacidade nova).
- [X] T010 [US2] Implementar `POST /api/figurino/<id>/photo` (multipart),
      `DELETE /api/figurino/<id>/photo` e `POST /api/figurino/<id>/photo/rotate` (JSON
      `{"direction"}`) em `app/api/figurino_write.py`, gate `_can_edit_figurino()`, devolvendo
      a ficha atualizada (mesmo shape de `POST /api/figurino`).
- [X] T011 [P] [US2] Criar `useUploadFigurinoPhoto`/`useRemoveFigurinoPhoto`/
      `useRotateFigurinoPhoto` em `frontend/apps/internal/src/lib/figurino.ts`.
- [X] T012 [US2] Adicionar na `frontend/apps/internal/src/pages/FigurinoFormPage.tsx` o campo
      de foto (input + preview + botão girar + botão remover), erro 400 inline, `loading` nos
      botões durante mutação.

**Checkpoint**: US2 completa e testável isoladamente.

---

## Phase 5: Polish & Verificação

- [X] T013 Criar `scripts/db/verify_155_upload_fotos_documentos.py` (gitignored): test client
      Flask contra `manto_local`, requests fora de `app_context` — cobre upload/substituir/
      remover para os 4 campos de talento, upload/girar/remover para figurino, e os gates 403
      (usuário sem CASTING/SUPERADMIN, sem FIGURINO/SUPERADMIN).
- [X] T014 Rodar `ruff check app/` nos arquivos tocados e corrigir achados.
- [X] T015 Rodar `npx tsc --noEmit` e `npm run build` em `frontend/apps/internal`.
- [X] T016 Conferência manual mobile (320–430px) dos campos de foto/documento nas duas telas
      (Princípio VIII).
- [X] T017 Atualizar `docs/changelog.html` com entrada em linguagem simples sobre o upload de
      fotos/documentos, republicando no mesmo link existente.

## Dependencies

- Setup (Phase 1) → Foundational (Phase 2, vazia) → US1 (Phase 3) → US2 (Phase 4) → Polish
  (Phase 5).
- US1 e US2 são independentes entre si (arquivos diferentes: talents vs. figurino) — poderiam
  ser feitas em paralelo por duas pessoas, mas nesta implementação seguem em sequência (US1 é
  P1, mais usada no dia a dia).
- Dentro de cada story: núcleo (`_ops`) → wrapper Jinja → endpoint API → hook frontend →
  página frontend.

## Implementation Strategy

MVP = US1 (upload de foto/documento de talento) sozinha já entrega valor real (é a lacuna mais
citada). US2 (figurino) fecha o restante da US3. Polish roda uma vez, ao final das duas.
