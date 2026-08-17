# Tasks: Solicitar ficha de figurino a partir da busca

**Tests**: `verify_237.py` contra `manto_local` + tsc + validação visual no app real.

## Phase 1: Backend (US1+US2) 🎯 MVP

- [x] T001 `app/constants.py`: `FIGURINO_KIND_FICHA = "ficha"` em KINDS/LABELS ("Ficha") + `FIGURINO_PROD_FLUXOS[ficha] = [solicitado, em_producao, pronto]` (sem aprovação, como manutenção)
- [x] T002 `app/figurino/producao_ops.py`: `criar_solicitacao_ficha(user, personagem, observacao, origem)` (título=personagem; descrição=observação+origem; kind=ficha; log de criação); `_erro_titulo` do tipo; validação em `mudar_status`: `→ pronto` de kind=ficha exige `figurino_sheet_id` (erro claro)
- [x] T003 `app/api/figurino_producao_write.py`: `POST /api/figurino/producoes/solicitar-ficha` — login required, SEM gate de papel (público do picker); 201/400 com fields
- [x] T004 `specs/237-solicitar-ficha/verify_237.py` contra `manto_local`: criar solicitação (campos certos), fluxo ficha sem etapa de aprovação, `→ pronto` bloqueado sem ficha e liberado com ficha, regressão dos fluxos producao/manutencao/compra intactos

## Phase 2: Frontend

- [x] T005 `lib/figurino.ts`: hook `useSolicitarFicha`; `FigurinoPicker.tsx`: ação "Solicitar ficha" no rodapé (sempre visível) + Dialog (nome pré-preenchido com o texto digitado, observação opcional, feedback TanStack; origem = rota atual)
- [x] T006 Telas de produção: rótulo/filtro do tipo "Ficha" onde os kinds forem hardcoded (conferir se vêm das constantes serializadas); detalhe do pedido kind=ficha sem campos de custo/fornecedor + vínculo da ficha pelo FigurinoPicker na conclusão; `npx tsc --noEmit` limpo

## Phase 3: Polish

- [x] T007 Validação visual (app real): solicitar pela busca do evento → pedido na fila → concluir vinculando ficha; conferir bloqueio sem ficha
- [x] T008 Documentação viva: docs/01 (endpoint novo + kind), docs/02 (picker + telas de produção), docs/03 (entrada no topo), tasks ticks

## Dependencies

T001 → T002 → T003 → T004; T005 após T003; T006 após T001; T007 após tudo; T008 fecha.
