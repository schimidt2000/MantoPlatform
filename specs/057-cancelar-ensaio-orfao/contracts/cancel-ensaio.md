# Contrato: expor cancelamento de ensaio (reusa `delete_ensaio`)

Esta feature **não cria rota nova**. Reusa a rota existente e adiciona pontos de UI + uma
lista de descoberta de órfãos na home.

## A) Rota reutilizada (sem alteração)

`POST /events/<int:ensaio_id>/delete-ensaio` → `calendar.delete_ensaio`

- Pré: `event_type == "ENSAIO"` (senão 400); RBAC `_CAN_ENSAIO` (senão 403).
- Efeito: remove do Google Calendar (aviso se falhar), apaga o ensaio, redireciona ao show
  pai se existir, senão à home; flash de sucesso.

## B) Home — dados passados ao template (novo)

A rota `home` (`/`) passa, quando `show_ensaio`:

| Variável | Significado |
|---|---|
| `orphan_ensaios` | Lista de `CalendarEvent` com `event_type == "ENSAIO"` e `parent is None`, ordenada por `start_at` (inclui passados). |

(As já existentes `pending_ensaio`, `scheduled_ensaio`, `pending_presence` permanecem.)

## C) Pontos de UI (novos) — todos reusando a rota A

| Local | Conteúdo |
|---|---|
| Home — setor Ensaios, seção "Ensaios sem show (órfãos)" | Para cada `orphan_ensaios`: título/data + botão "Cancelar ensaio" (form POST para a rota A, com `confirm`). Aparece só para `show_ensaio`. |
| Home — lista "Ensaios agendados" | Botão "Cancelar ensaio" ao lado do "Editar" existente (form POST para a rota A, `redirect_to`/confirm). |
| `event_detail.html` quando `event_type == "ENSAIO"` | Banner com botão "Cancelar ensaio" (form POST para a rota A, com `confirm`), visível para `show_ensaio`. |

## D) Confirmação (Princípio V)

Todos os botões pedem confirmação antes de enviar (ex.: "Cancelar este ensaio? Esta ação
remove o ensaio do sistema e da agenda."). O show pai nunca é afetado.

## Não-regressão

- A rota `delete_ensaio` e o botão já existente na página do show pai permanecem iguais.
- Cancelar um ensaio não altera nenhum show.
- Sem mudança em sincronização, criação ou edição de ensaios.
