# Implementation Plan: Clientes (CRM) em React (165)

**Branch**: `165-clientes-crm-react` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/165-clientes-crm-react/spec.md`

## Summary

Primeira fatia da User Story 6 (Cauda Administrativa) da migração 144. Migra o blueprint
`clientes` (busca, criação rápida, lista, ficha, edição de CPF/CNPJ/endereço, exclusão,
avaliações) para React + API JSON. Extrai o núcleo de negócio hoje embutido nas views de
`app/clientes/routes.py` para um módulo novo `app/clientes/client_ops.py` (mesmo padrão de
`talent_ops.py`/`figurino_ops.py`/`event_ops.py` das fatias anteriores), reusado pela view Jinja
(mantida sem regressão, FR-010) e pelos novos endpoints `/api/clientes/*`. O `ClientPicker.tsx`
(já existente desde a feature 152, hoje consumindo `/clientes/search` direto) passa a consumir o
endpoint novo — único ponto de integração entre esta fatia e a Agenda/Eventos já migrada (US2).

## Technical Context

Igual às fatias 145–164: Python/Flask + React (Vite/TS/TanStack Query). Sem dependência nova.
Verificação com test client Flask contra `manto_local`, requests fora de `app_context`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (reutilizar)**: núcleo de busca sem acentos (`strip_accents_lower`/`unaccent_lower_sql`,
  `app/utils.py`) e de período (`_parse_period`, `app/talents/routes.py`) são reaproveitados sem
  duplicação — só chamados a partir do novo `client_ops.py`. `ClientPicker.tsx` já existe (feature
  152) e é só redirecionado para o endpoint novo, não recriado.
- **II (padrões de código)**: `client_ops.py` novo com type hints/docstrings Google-style, funções
  ≤30 linhas; endpoints novos em `app/api/clientes_read.py` e `app/api/clientes_write.py`.
- **III (API first)**: endpoints novos 100% JSON; views Jinja de `app/clientes/routes.py`
  continuam existindo em paralelo (chamando os mesmos helpers de `client_ops.py`), sem mudança de
  comportamento (FR-010) até serem desativadas ao final da migração 144.
- **IV (não quebrar)**: paridade verificada contra `manto_local` — mesmos resultados de busca,
  lista, ficha e avaliações para o mesmo usuário/filtro nos dois caminhos (Jinja e React).
- **V (feedback)**: loading/erro/sucesso via TanStack Query em todas as telas novas; confirmação
  via dialog do `shadcn/ui` antes de excluir cliente (ação destrutiva); erro de validação na
  criação rápida/edição mantém os campos preenchidos e aponta o campo inválido.
- **VII (monetário)**: total vendido na ficha do cliente usa `formatBRL`/`@manto/money` no
  frontend; a API devolve número puro (float), nunca string formatada.
- **VIII (mobile-first)**: lista e ficha de clientes seguem mobile-first por princípio geral de
  UI (não é superfície pública, mas evita rolagem horizontal <768px).
- **IX (movimento)**: abertura do dialog de confirmação de exclusão e troca de filtro nas
  avaliações usam transição padrão (Framer Motion/Tailwind), sem novidade além do já estabelecido.

Sem violação nova.

## Project Structure

### Documentation (this feature)

```text
specs/165-clientes-crm-react/
├── plan.md
├── data-model.md
├── quickstart.md
├── contracts/clientes-endpoints.md
└── tasks.md
```

### Source Code (repository root)

```text
app/clientes/
├── routes.py                          # views Jinja passam a chamar client_ops.*, sem duplicar
└── client_ops.py                      # NOVO — núcleo: busca, quick-create, lista, ficha,
                                        #   update, delete, resumo de avaliações
app/api/
├── clientes_read.py                   # NOVO — GET /api/clientes/search, /, /<id>,
                                        #   /avaliacoes
└── clientes_write.py                  # NOVO — POST /api/clientes/quick-create,
                                        #   PATCH /api/clientes/<id>, DELETE /api/clientes/<id>
app/__init__.py                        # registra os 2 blueprints novos de API
frontend/apps/internal/src/
├── lib/clientes.ts                    # NOVO — hooks TanStack Query (search/list/detail/
                                        #   update/delete/avaliacoes)
├── components/ClientPicker.tsx        # ALTERADO — consome /api/clientes/search em vez de
                                        #   /clientes/search direto
├── pages/ClientsListPage.tsx          # NOVO
├── pages/ClientDetailPage.tsx         # NOVO
└── pages/ClientFeedbackPage.tsx       # NOVO — telas de avaliações
App.tsx                                # + rotas /clientes, /clientes/:id, /clientes/avaliacoes
scripts/db/verify_165_clientes_react.py  # NOVO: paridade API×Jinja + RBAC 403 (todas as rotas)
```

**Structure Decision**: núcleo extraído para `app/clientes/client_ops.py` (mesmo padrão de
extração das fatias 154 `talent_ops`/`figurino_ops` e 162 `cadastro_ops`): blueprint pequeno, sem
separação prévia — extrair vale a pena para dar aos dois consumidores (Jinja e API) uma única
fonte de verdade limpa, em vez da exceção "core-in-routes" usada quando o núcleo já era puro o
bastante (financeiro).

## Design Decisions

1. **`app/clientes/client_ops.py`** (novo): funções puras (sem `request`/`render_template`)
   chamadas por `routes.py` (Jinja) e pelos endpoints de API:
   - `search_clients(query: str) -> list[Client]`
   - `quick_create_client(name: str, phone_raw: str, *, phone_display, email, company) ->
     tuple[Client, bool]` (bool = `reused`)
   - `list_clients(query: str) -> tuple[list[Client], dict[int, int], int]` (clientes, contagem de
     eventos por cliente, total geral)
   - `get_client_detail(client_id: int) -> tuple[Client, list[CalendarEvent], dict[int, str],
     Decimal]` (cliente, eventos, relação por evento, total vendido)
   - `update_client_fields(client: Client, *, cpf, cnpj, address) -> None`
   - `delete_client(client: Client) -> None` (desvincula `EventClient` e `client_id` antes)
   - `summarize_feedback(*, period, from_raw, to_raw, score, tag, client_id) -> dict` (mesmo
     retorno hoje montado inline em `avaliacoes()`)
   Erros de validação (nome/telefone) levantam uma exceção dedicada (`ClientValidationError` com
   `field`/`message`) capturada pelos dois lados (Jinja vira `flash`, API vira 400 com `fields`).
2. **`GET /api/clientes/search?q=`**: mesmo contrato de resposta de `/clientes/search` hoje
   (`_client_to_json`, movido para `client_ops.py`), gate `require_vendas` reimplementado como
   função de API (COMERCIAL/FINANCEIRO/SUPERADMIN).
3. **`POST /api/clientes/quick-create`**: body `{"name", "phone", "phone_display"?, "email"?,
   "company"?}` → 200 `{...cliente, "reused": bool}` ou 400
   `{"error": {"message", "fields": {"name"|"phone": "..."}}}`.
4. **`GET /api/clientes/`**: querystring `q` opcional → `{"items": [...], "total_clients": N}`
   (envelope de lista, convenção geral).
5. **`GET /api/clientes/<id>`**: 200 `{cliente..., "events": [...], "total_sales": float}`; 404 se
   não existir.
6. **`PATCH /api/clientes/<id>`**: body `{"cpf"?, "cnpj"?, "address"?}` → 200 cliente atualizado.
7. **`DELETE /api/clientes/<id>`**: gate extra SUPERADMIN/FINANCEIRO (reimplementado, paridade com
   `_has_role(SUPERADMIN, FINANCEIRO)` de hoje) → 204.
8. **`GET /api/clientes/avaliacoes`**: mesma querystring de hoje (`period`, `from`, `to`, `score`,
   `tag`, `client_id`) → `summarize_feedback(...)` serializado (`{"feedbacks": [...], "total",
   "avg_overall", "clients_rated", "dist", "dist_max", "attention": [...],
   "clients_with_feedback": [...], "filters": {...}}`).
9. **`ClientPicker.tsx`**: troca a chamada direta `fetch(`${API_BASE}/clientes/search?q=...`)`
   por `fetch(`${API_BASE}/api/clientes/search?q=...`)` — único ponto de integração cruzada
   entre esta fatia e a US2 já migrada; a rota Jinja `/clientes/search` permanece intacta (FR-010)
   até desativação futura, sem outro consumidor conhecido.
10. **RBAC reimplementado, não decorator Flask**: seguindo o padrão das fatias 156–160/162–164,
    os gates de API são funções Python chamadas no início de cada view (não os decorators
    `@require_vendas`/`@login_required` do Flask-Login, que dependem de sessão de página) —
    paridade de comportamento validada pelo script de verificação, não pelo mesmo código-decorator.

## Complexity Tracking

Nenhuma violação nova.
