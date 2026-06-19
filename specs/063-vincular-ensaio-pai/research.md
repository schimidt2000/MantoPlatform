# Research: Vincular um ensaio existente a um evento pai (063)

Decisões técnicas. Sem `NEEDS CLARIFICATION`.

## 1. Onde fica a ação

- **Decisão**: no bloco "Show de origem" da página do ensaio (`ensaio_detail.html`, feature 062).
  Para `show_ensaio`, mostrar um form: select **buscável** de shows + botão "Vincular"
  (rótulo "Trocar show" quando já há pai).
- **Rationale**: é onde o usuário vê o estado do vínculo (inclusive o aviso de órfão do print).

## 2. Rota para definir o pai

- **Decisão**: `POST /events/<ensaio_id>/link-parent` (`@login_required` + checagem `_CAN_ENSAIO`).
  Lê `parent_event_id`; valida e seta `ensaio.parent_event_id`; commit; `EventLog`/flash;
  redireciona para a página do ensaio.
- **Validações** (FR-006): o alvo deve ser tipo ENSAIO (senão 400); o `parent` deve existir, **não**
  ser ENSAIO e **não** ser o próprio ensaio; seleção vazia → mensagem, sem alterar.
- **Rationale**: rota dedicada e pequena, espelhando `edit_ensaio`/`delete_ensaio`. Não toca no
  Google Calendar (vínculo é interno).

## 3. Lista de shows candidatos

- **Decisão**: no branch ENSAIO de `event_detail`, passar `candidate_shows` = eventos
  **não-ENSAIO**, exceto o próprio, ordenados por `start_at` desc (mesmo padrão de
  `groupable_events`). Busca por nome no cliente (filtro JS sobre as opções do select).
- **Rationale**: reusa padrão existente; busca client-side simples (sem endpoint novo).

## 4. Efeito do vínculo

- Setar `parent_event_id` faz o ensaio aparecer em `show.ensaios` automaticamente (relação já
  existente) e a página passa a mostrar o show em "Show de origem" (feature 062). Sem mudança de
  modelo.

## 5. Permissões

- `_CAN_ENSAIO` (ENSAIO/CASTING/SUPERADMIN), como editar/cancelar ensaio.

## 6. Sem migration

- Nenhuma. Só nova rota + UI; o campo `parent_event_id` já existe.
