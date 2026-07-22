# Implementation Plan: Upload de Fotos e Documentos (Talento + Figurino) (155)

**Branch**: `155-upload-fotos-documentos` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/155-upload-fotos-documentos/spec.md`

## Summary

Fecha a US3 (Talentos/Figurino): migra para React o upload que a fatia 154 deixou de fora —
foto de rosto/corpo inteiro/documento/CNH do talento (CASTING/SUPERADMIN) e foto/rotação da
ficha de figurino (FIGURINO/SUPERADMIN). Mesmo padrão consolidado na 153 (upload de anexos de
evento): endpoint `multipart/form-data` por ação, `FormData` no frontend, resposta JSON igual a
qualquer outro endpoint. Adiciona também "remover arquivo" como ação isolada nos dois lados —
capacidade que a tela antiga não tinha (só substituía ao reenviar).

## Technical Context

Igual à 144-154: Python/Flask + React (Vite/TS/TanStack Query). Sem dependência nova — Pillow já
é usada em `app/storage.py` (compressão) e `app/figurino/routes.py` (rotação).
Verificação com test client Flask contra `manto_local`, requests fora de `app_context`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (reutilizar)**: núcleo reaproveita `app/storage.py` (`save_file`/`delete_file`,
  compressão automática já embutida) e a lógica de validação de extensão hoje em
  `upload_talent_photo`/`new_sheet`/`edit_sheet`/`rotate_photo` — extraída para
  `talent_ops.py`/`figurino_ops.py` (já existentes desde a 154), sem duplicar.
- **II (padrões de código)**: novas funções em `talent_ops.py`/`figurino_ops.py` — puras, sem
  `request`/`flash`/`current_user`, recebem `FileStorage` já obtido pelo wrapper; type hints/
  docstrings.
- **III (API first)**: 6 endpoints novos, 100% `multipart/form-data` (upload) ou JSON puro
  (remover/rotacionar), convenção da `api-conventions.md` (feature 153); views Jinja continuam
  existindo em paralelo, sem mudança de comportamento (FR-011).
- **IV (não quebrar)**: paridade verificada contra `manto_local`; substituição de arquivo
  existente sempre chama `delete_file` no arquivo antigo antes de gravar o novo, igual ao
  comportamento Jinja atual — nenhuma rota Jinja muda de comportamento, exceto o acréscimo do
  botão "remover" (capacidade nova, ver spec Assumptions), aplicado nos dois caminhos para não
  divergir.
- **V (feedback)**: erro 400 (formato inválido) e 403 mostrados inline; `useMutation` com
  `loading` no botão de envio/remoção; preview de imagem local antes do upload confirmar
  (mesmo padrão do preview de imagem de observação, 150).
- **VII (monetário)**: N/A — sem valores monetários nesta fatia.
- **VIII (mobile-first)**: campos de foto/documento (input + preview + remover) conferidos em
  320–430px — reaproveita o padrão de anexo de evento (153) para grid de miniaturas.
- **IX (movimento)**: sem transição nova crítica; preview aparece/some com a mesma técnica já
  usada em anexos de evento (sem Framer Motion dedicado).

Sem violação nova — todo o núcleo entra nos módulos `_ops` já existentes (154), sem criar
módulo novo.

## Project Structure

### Documentation (this feature)

```text
specs/155-upload-fotos-documentos/
├── plan.md
├── data-model.md
├── quickstart.md
├── contracts/upload-endpoints.md
└── tasks.md
```

### Source Code (repository root)

```text
app/talents/talent_ops.py          # + save_talent_photo(talent, *, photo_type, file_storage)
                                    #   -> str | None (erro), remove_talent_photo(talent, *,
                                    #   photo_type) -> None — paridade com upload_talent_photo
                                    #   (validação de extensão por tipo, substituição com
                                    #   delete_file do arquivo antigo)
app/talents/routes.py              # upload_talent_photo vira wrapper fino sobre
                                    #   save_talent_photo; + rota remove_talent_photo (nova,
                                    #   Jinja) chamando remove_talent_photo
app/figurino/figurino_ops.py       # + save_figurino_photo(sheet, *, file_storage) -> str | None,
                                    #   remove_figurino_photo(sheet) -> None,
                                    #   rotate_figurino_photo(sheet, *, direction) -> str | None
                                    #   (paridade com upload/rotate/delete de photo_filename)
app/figurino/routes.py             # new_sheet/edit_sheet (upload)/rotate_photo viram wrappers
                                    #   finos sobre figurino_ops; + rota remove_photo (nova,
                                    #   Jinja)
app/api/talents_write.py           # + POST /api/talents/<id>/photo (multipart, photo_type em
                                    #   request.form), DELETE /api/talents/<id>/photo
                                    #   (?photo_type=...)
app/api/figurino_write.py          # + POST /api/figurino/<id>/photo (multipart),
                                    #   DELETE /api/figurino/<id>/photo,
                                    #   POST /api/figurino/<id>/photo/rotate (JSON {direction})
frontend/apps/internal/src/
├── lib/talents.ts                 # + useUploadTalentPhoto, useRemoveTalentPhoto
├── lib/figurino.ts                # + useUploadFigurinoPhoto, useRemoveFigurinoPhoto,
│                                   #   useRotateFigurinoPhoto
├── pages/TalentDetailPage.tsx     # + 4 campos de foto/documento (input + preview + remover),
│                                   #   visíveis só quando can_edit
├── pages/FigurinoFormPage.tsx     # + campo de foto (input + preview + girar + remover)
App.tsx                            # sem rota nova (upload é ação dentro de página existente)
scripts/db/verify_155_upload_fotos_documentos.py  # NOVO: paridade API×Jinja + RBAC 403
```

**Structure Decision**: núcleo entra nos mesmos `talent_ops.py`/`figurino_ops.py` da 154 (sem
módulo novo) — mesma decisão estrutural, agora estendida para cobrir arquivo. Endpoints entram
nos módulos de escrita já existentes (`talents_write.py`/`figurino_write.py`), sem arquivo novo.

## Design Decisions

1. **`save_talent_photo`/`remove_talent_photo`** (`app/talents/talent_ops.py`):
   - `save_talent_photo(talent, *, photo_type: str, file_storage) -> str | None`: paridade
     exata com `upload_talent_photo` — valida extensão por `photo_type` (`face`/`full`: JPG/
     PNG/WEBP; `doc`/`cnh`: + PDF), gera nome `talent_{id}_{photo_type}_{uuid}{ext}`, chama
     `delete_file` no path antigo do campo (se houver) antes de `save_file`, grava no campo
     correspondente. Retorna mensagem de erro (string) se `photo_type`/extensão inválidos,
     `None` em sucesso.
   - `remove_talent_photo(talent, *, photo_type: str) -> None`: chama `delete_file` no path
     atual do campo (no-op seguro se já vazio) e limpa o campo. Ação nova (spec Assumptions).
2. **`save_figurino_photo`/`remove_figurino_photo`/`rotate_figurino_photo`**
   (`app/figurino/figurino_ops.py`):
   - `save_figurino_photo(sheet, *, file_storage) -> str | None`: paridade com o bloco de
     upload já em `new_sheet`/`edit_sheet` — `delete_file` no `photo_filename` antigo antes de
     `save_file`. Retorna erro de extensão ou `None`.
   - `remove_figurino_photo(sheet) -> None`: `delete_file` + limpa `photo_filename` (no-op
     seguro se vazio).
   - `rotate_figurino_photo(sheet, *, direction: str) -> str | None`: paridade exata com
     `rotate_photo` (só funciona para `photo_filename` local, `/uploads/...` — mesma limitação
     de hoje, não migrada para S3 nesta fatia); retorna mensagem de erro amigável se sem foto,
     path não-local, ou falha ao abrir/girar a imagem (nunca propaga exceção).
3. **Endpoints REST** (multipart onde há arquivo, JSON puro para remover/rotacionar):
   - `POST /api/talents/<id>/photo` (CASTING/SUPERADMIN, multipart: `photo_type` em
     `request.form`, arquivo em `request.files["photo"]`): 400 se `photo_type` inválido ou
     extensão não aceita; devolve o talento atualizado (mesmo shape de `GET /api/talents/<id>`
     minus `history`, reaproveitando `get_talent_profile`).
   - `DELETE /api/talents/<id>/photo?photo_type=...` (CASTING/SUPERADMIN): mesmo formato de
     resposta; no-op seguro se campo já vazio.
   - `POST /api/figurino/<id>/photo` (FIGURINO/SUPERADMIN, multipart: arquivo em
     `request.files["photo"]`): devolve a ficha atualizada (mesmo shape do `POST /api/figurino`).
   - `DELETE /api/figurino/<id>/photo` (FIGURINO/SUPERADMIN): idem.
   - `POST /api/figurino/<id>/photo/rotate` (FIGURINO/SUPERADMIN, JSON `{"direction": "cw"|
     "ccw"}`, default `"cw"`): devolve a ficha atualizada; 400 se sem foto ou falha ao girar.
4. **Frontend — `FormData` + `apiFetch`, mesmo padrão de `eventAttachments.ts` (153)**: cada
   hook de upload monta `FormData` e chama `apiFetch<T>(path, {method, body: form})` — o
   cliente já detecta `FormData` e não força `Content-Type` (`packages/api-client/src/client.ts`,
   inalterado). Preview local usa `URL.createObjectURL(file)` até a mutação confirmar, depois
   troca para `assetUrl(resultado.photo_url)` — evita esperar round-trip pra mostrar algo na
   tela (Princípio V).
5. **Remover como no-op seguro nos dois lados**: tanto o núcleo quanto os endpoints tratam
   "remover campo já vazio" como sucesso (200), nunca 404/500 — simplifica o frontend (não
   precisa checar se há foto antes de habilitar o botão) e é consistente com o resto da API
   (idempotência já usada em `approve_talent`, 154).

## Complexity Tracking

Nenhuma violação nova.
