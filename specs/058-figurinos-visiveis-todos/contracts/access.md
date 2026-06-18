# Contrato: controle de acesso de Figurinos

Sem rota nova. A feature ajusta **visibilidade** e adiciona **guarda de papel**.

## A) Visualização — liberada a todos os autenticados

| Ponto | Antes | Depois |
|---|---|---|
| Link "Figurinos" no menu (`base.html`) | só `FIGURINO`/`SUPERADMIN` | qualquer `is_authenticated` |
| `GET /figurinos` | `@login_required` | inalterado (qualquer autenticado) |
| `GET /figurinos/<id>/print` | `@login_required` | inalterado |
| `GET /figurinos/print-event/<id>` | `@login_required` | inalterado |

## B) Edição — restrita a SUPERADMIN + FIGURINO

Helper novo em `figurino/routes.py`:

```
_can_edit_figurino() -> bool
    True se current_user tem papel SUPERADMIN ou FIGURINO.
```

Guarda adicionada no topo de cada rota de mutação (antes de qualquer escrita):

```
if not _can_edit_figurino():
    abort(403)
```

Rotas guardadas: `new_sheet`, `edit_sheet`, `rotate_photo`, `delete_sheet`,
`sync_drive_page`, `sync_drive_stream`.

- Pré: usuário autenticado (já garantido por `@login_required`).
- Sem permissão → **HTTP 403** (página de acesso negado existente), nenhuma alteração.
- Com permissão (SUPERADMIN/FIGURINO) → comportamento atual, sem regressão.

## C) UI — botões de edição só para quem pode editar

Em `figurinos.html`, gate com `eff_has_role('FIGURINO','SUPERADMIN')`:
- "+ Nova Ficha", "+ Criar ficha" (x2), lápis "Editar", "Sync Drive".
- Impressão e busca permanecem para todos.

## Não-regressão

- Leitura/impressão inalteradas para os perfis que já tinham acesso.
- SUPERADMIN/FIGURINO continuam com todas as ações.
- Sem mudança em dados, sincronização de eventos ou outras telas.
