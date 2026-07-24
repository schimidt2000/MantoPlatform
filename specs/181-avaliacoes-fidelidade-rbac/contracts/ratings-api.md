# Contrato: API de Avaliações (Panorama) — mudança aditiva

Endpoints existentes, sem novas rotas. Documentado aqui apenas o incremento desta feature.

## `GET /api/ratings`

Já implementado em `app/api/ratings_read.py` (RBAC: qualquer autenticado, `@api_login_required`).

**Query params** (sem mudança de nomes, só de valores aceitos):

| Param       | Valores aceitos                                              | Mudança nesta feature |
|-------------|---------------------------------------------------------------|------------------------|
| `period`    | `all \| 30d \| 90d \| 365d \| custom \| 7d`                    | **`7d` adicionado**   |
| `date_mode` | `evento \| avaliacao`                                          | sem mudança            |
| `cat`       | `"" \| artista \| som \| figurino \| texto \| coordenacao \| maquiagem` | sem mudança |
| `event_id`  | id de `CalendarEvent` ou vazio                                 | sem mudança            |
| `from`/`to` | data ISO (`period=custom`)                                     | sem mudança            |

**Resposta**: mesmo shape de `RatingsOverview` (`frontend/apps/internal/src/lib/ratings.ts`) —
nenhum campo novo. Quando `period=7d`, `recorte_label` passa a poder conter "última semana".

Comportamento não especificado anteriormente e agora explícito: `period=7d` só é reconhecido pela
nova UI React; o Jinja legado (`app/talents/routes.py::avaliacoes()`) não expõe essa opção na
interface, mas aceitaria o valor se alguém montasse a URL manualmente (mesmo comportamento
permissivo que já existe para os demais presets — não é uma regressão introduzida por esta
feature).

## `POST /api/ratings/modo-anonimo`

Já implementado em `app/api/ratings_write.py` — **sem nenhuma mudança**. RBAC já correto:
`403` se `current_user` não é SUPERADMIN (`rating_ops.is_superadmin`). Documentado aqui só para
registrar que a feature 181 depende desse contrato já existente e não deve alterá-lo.

**Body**: `{ "enabled": boolean }` → **Resposta 200**: `{ "fully_anonymous": boolean }`.
**Resposta 403** (não-SUPERADMIN): `{ "error": "Sem permissão" }` (via `json_error`).
