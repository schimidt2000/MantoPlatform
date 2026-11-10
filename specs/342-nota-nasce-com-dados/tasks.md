# Tasks: 342 — O pedido de nota já nasce com os dados que a emissão exige

**Input**: artefatos em `/specs/342-nota-nasce-com-dados/`

**Verificação**: `specs/342-nota-nasce-com-dados/verify_342.py` contra o espelho `manto_342`.

## Formato: `[ID] [P?] [Story] Descrição`

## Phase 1: Setup

- [x] T001 Criar o espelho `manto_342` do dump noturno e gravar a URL em `.local-db-url` do worktree
  (ignorado pelo git)

## Phase 2: Foundational (bloqueia as histórias)

- [x] T002 Migration `migrations/versions/d342a7c1e9f3_nota_nasce_com_dados.py`: `nota_email`,
  `show_if_key`, `show_if_value` e os dez campos da seção "Nota fiscal" (idempotente)
- [x] T003 `app/models.py`: `CalendarEvent.nota_email`, `FormFieldDefinition.show_if_key/value`,
  tipo `cpf_cnpj` em `FIELD_TYPES`
- [x] T004 [P] `app/documentos.py`: `cpf_valido`, `cnpj_valido`, `doc_valido`
- [x] T005 `specs/342-nota-nasce-com-dados/verify_342.py` com os 19 cenários da spec, falhando pelos
  motivos certos antes do núcleo

## Phase 3: História 1 — A cliente informa os dados da nota no formulário (P1) 🎯 MVP

- [x] T006 [US1] `app/formularios/formularios_ops.py`: `campo_visivel`; `_validate_dynamic` e
  `_build_sections_dynamic` respeitam a condição e a regra do CNPJ; validação do tipo `cpf_cnpj`;
  rótulo do tipo em `FIELD_TYPE_LABELS`
- [x] T007 [US1] `app/api/formularios_write.py`: `show_if` e `only_for_cnpj_of` no schema
- [x] T008 [P] [US1] `frontend/apps/public/src/lib/documento.ts` (dígitos verificadores, máscara) e
  tipos novos em `lib/formularios.ts`
- [x] T009 [US1] `DynamicForm.tsx`/`DynamicField.tsx`: esconder por condição, pré-preencher documento
  e e-mail ao abrir o bloco, campo `cpf_cnpj`, não enviar campo escondido
- [x] T010 [US1] Verify 1–5 verdes

## Phase 4: História 2 — As respostas chegam aos dados da nota da venda (P1)

- [x] T011 [US2] `app/formularios/nota_do_formulario_ops.py`: `respostas_da_nota`,
  `levar_para_o_evento`, `do_formulario_do_evento`
- [x] T012 [US2] `apply_event_link` chama a ponte (import tardio)
- [x] T013 [US2] `pre_evento_ops.extrair_para_evento`: `with_invoice` e `nota` sugeridos;
  `EventCreatePage.tsx` aplica
- [x] T014 [US2] Verify 6–10 verdes

## Phase 5: História 3 — Pedir nota exige o CNPJ ou CPF (P1)

- [x] T015 [US3] `pedido_de_nota_ops.py`: `email` em `DadosDaNota`/`ler`/`gravar`; dígitos
  verificadores; `erro_de_documento`; `serializar_dados` com `email` e `do_formulario`;
  `tomador()["email"]`
- [x] T016 [US3] `app/api/agenda_write.py`: as três portas chamam `erro_de_documento` antes de gravar
- [x] T017 [US3] Interno: `lib/notaFiscal.ts`, `lib/eventFormSchema.ts`, `DadosDaNotaCampos.tsx`,
  `ValoresBlock.tsx`, `ComercialSection.tsx` — e-mail, respostas do formulário, erro no campo, aviso
  "A cliente pediu nota fiscal no formulário."
- [x] T018 [US3] Verify 11–15 verdes

## Phase 6: História 4 — O município do evento vem sugerido (P2)

- [x] T019 [US4] `nota_do_formulario_ops.municipio_sugerido` (formulário, depois endereço);
  `ler_dados_da_nota` grava município sem ISS; `serializar_dados` e `serializar_item` com
  `municipio_sugerido`
- [x] T020 [US4] Interno: campo "Município do evento" sempre visível com a sugestão;
  `PainelNotasAEmitir.tsx` mostra município ou sugestão "a confirmar"
- [x] T021 [US4] Verify 16–17 verdes

## Phase 7: História 5 — Campo condicional no editor (P3)

- [x] T022 [US5] `create_field`/`update_field` validam e gravam `show_if_*`;
  `formularios_admin_{read,write}.py` serializam
- [x] T023 [US5] `FormFieldEditor.tsx` e `lib/formulariosAdmin.ts`: "Aparece só quando…"
- [x] T024 [US5] Verify 18 verde

## Phase 8: Polimento e portões

- [x] T025 `ruff check` nos tocados; `ruff format` só nos novos; `cd frontend && npm run typecheck`
- [x] T026 Conferir telas: `/f/pre-contrato` e `/f/corporativo` em 375×812; card Comercial; "Editar
  tudo"; painel; editor
- [x] T027 Docs: `docs/01`, `02`, `03` (entrada no topo + índice), `04`, `05`
- [x] T028 `/speckit-converge`; commits por caminho (`feat(342):`, `docs(342):`); sem merge nem push

## Como foi executado (2026-11-10)

- T001–T028 concluídas. `verify_342.py` 19/19 e `verify_323.py` 15/15 no espelho `manto_342`; `ruff check`
  limpo nos tocados; `npm run typecheck` limpo.
- T026: abertos no Browser pane `/f/corporativo` e `/f/pre-contrato` em 375×812, o card Comercial do evento com
  formulário ligado (bloco, erro no campo, salvar), o painel "Notas a emitir" e o editor de campos. **Não
  abertos**: "Editar tudo" e a criação a partir do formulário (mesmo componente `DadosDaNotaCampos`; cobertos
  pelo typecheck e pelos cenários 6, 15 e 16).
- Checklist, analyze e converge foram feitos em linha, relendo spec × plano × código, sem rodar as skills
  `/speckit-checklist`, `/speckit-analyze` e `/speckit-converge` como passos separados.
- Ajuste fora do previsto: `specs/323-nota-pedida-ao-superadmin/verify_323.py`, cenário 3, passou a mandar o
  documento no pedido (a regra nova recusa o pedido sem documento).

## Dependências e ordem

Foundational bloqueia tudo. US1 → US2 (a ponte lê as chaves que a US1 cria). US3 e US4 tocam
`pedido_de_nota_ops.py` e as mesmas telas: em sequência. US5 é independente depois da US1.

## Estratégia

MVP = US1 + US2 + US3 (o pedido do dono). US4 e US5 completam.
