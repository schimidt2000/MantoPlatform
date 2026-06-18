# Research: Figurinos visíveis a todos (edição restrita)

Decisões técnicas da feature 058. Sem `NEEDS CLARIFICATION`.

---

## 1. Estado atual (diagnóstico)

- **Menu** (`base.html`): o link "Figurinos" está dentro de
  `eff_has_role('FIGURINO','SUPERADMIN')` → só esses perfis veem.
- **Rotas** (`figurino/routes.py`): TODAS têm apenas `@login_required`, **sem guarda de
  papel**. Ou seja, qualquer usuário logado que conheça a URL já pode criar/editar/excluir.
- **Template** (`figurinos.html`): botão "Sync Drive" é gated por `is_real_superadmin()`;
  "Nova Ficha", "Criar ficha" e o lápis de editar **não** são gated.

## 2. Abrir visualização: liberar o link do menu

- **Decisão**: trocar o gate do link no `base.html` de
  `eff_has_role('FIGURINO','SUPERADMIN')` para `current_user.is_authenticated` (todos veem).
- **Rationale**: FR-001. A seção "Produção" passa a aparecer para todos (só contém Figurinos).
- **Alternativas**: criar nova seção de menu (desnecessário).

## 3. Restringir edição: guarda no servidor

- **Decisão**: criar `_can_edit_figurino()` (SUPERADMIN ou FIGURINO via `current_user.roles`,
  no mesmo padrão do `_is_superadmin()` já existente) e adicionar `if not
  _can_edit_figurino(): abort(403)` no topo das rotas de mutação: `new_sheet`, `edit_sheet`,
  `rotate_photo`, `delete_sheet`, `sync_drive_page`, `sync_drive_stream`.
- **Rationale**: FR-003/FR-006 — recusa antes de qualquer escrita; reusa o padrão local
  (Princípio I). As rotas de leitura (`figurinos`, `print_sheet`, `print_event_figurinos`)
  permanecem só com `@login_required`.
- **Alternativas**: decorator novo de role (poderia, mas o projeto usa checagem inline por
  blueprint; manter o padrão local é mais consistente aqui).

## 4. Esconder botões de edição na UI

- **Decisão**: gate dos botões de criar/editar/excluir/sync em `figurinos.html` com
  `eff_has_role('FIGURINO','SUPERADMIN')` (mesmo helper do menu/base). Leitura e impressão
  seguem visíveis a todos.
- **Rationale**: FR-004/FR-005. Consistência com o gate do menu.
- **Alternativas**: passar um flag `can_edit` da rota — usar `eff_has_role` no template evita
  alterar a assinatura da rota e é o padrão já usado em `base.html`.

## 5. Acesso negado

- **Decisão**: `abort(403)` reusa a página 403 amigável já existente (feature 050).
- **Rationale**: Princípio V; sem stack trace ao usuário.

## 6. Sem mudança de modelo / migration

- **Decisão**: nenhuma. Só controle de acesso e visibilidade.
