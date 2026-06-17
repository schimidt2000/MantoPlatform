# Contrato: anonimato das avaliações + toggle do modo total

## A) Exibição da página `/talents/avaliacoes` (GET, existente)

Acesso: perfis atuais (`_can_edit_talent` → SUPERADMIN/CASTING). Sem mudança de acesso.

A rota calcula e passa ao template:

| Variável | Significado |
|---|---|
| `show_authors` | `is_superadmin and not settings.ratings_fully_anonymous`. |
| `fully_anonymous` | `settings.ratings_fully_anonymous` (estado do botão). |
| `is_superadmin` | Para renderizar o botão do modo total só para super admin. |

Cada item de comentário (`_comment_item`):
- Se `show_authors`: `author = talento.full_name`, `funcao = mapa[(event_id, talent_id)]`.
- Senão: `author = "Anônimo"`, `funcao = None` (e nenhum link/perfil do autor).

## B) Toggle do modo anônimo total (POST, novo)

`POST /talents/avaliacoes/modo-anonimo`

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `enabled` | "1" / "0" | sim | Novo estado do modo total. |

### Pré-condições

- Usuário autenticado **super admin**. Caso contrário: `403` (ou flash de erro + redirect),
  sem efeito.

### Efeito

- `settings.ratings_fully_anonymous = (enabled == "1")`.
- `AuditLog` registrando autor + ação (`ratings_fully_anonymous` on/off) — FR-010.
- `db.session.commit()`; flash de sucesso; redirect de volta à página de avaliações
  (preservando filtros, se simples).

### Resposta

- Sucesso: redirect para `/talents/avaliacoes`, com o novo estado refletido no botão.
- Sem permissão: 403 / flash de erro; estado inalterado.

## C) Portal — aviso de anonimato (telas existentes)

`rate.html` e `rate_detail.html` exibem um aviso textual (pt-BR), no padrão de alerta visual
existente: as avaliações enviadas são **anônimas**. Sem mudança no fluxo de envio.

## Não-regressão

- Notas, médias, distribuição, ranking e tendência: **inalterados** (a anonimização afeta só
  o rótulo do autor e a função exibida).
- Acesso à página: inalterado.
- Exibição da pessoa avaliada (subject de subcategoria): inalterada.
