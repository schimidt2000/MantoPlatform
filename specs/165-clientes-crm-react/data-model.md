# Data Model: Clientes (CRM) em React (165)

Nenhuma tabela/campo novo — reaproveita entidades já existentes. Esta fatia extrai a lógica hoje
embutida nas views de `app/clientes/routes.py` para `app/clientes/client_ops.py` e adiciona
serialização JSON sobre ela.

## Entidades lidas/escritas (já existentes)

| Entidade         | Uso                                                                          |
|------------------|-------------------------------------------------------------------------------|
| `Client`         | busca, criação rápida, lista, ficha, edição (cpf/cnpj/address), exclusão      |
| `EventClient`    | associação cliente↔evento; contagem de eventos na lista, relação na ficha    |
| `CalendarEvent`  | eventos associados ao cliente (ficha), `sale_value` para total vendido       |
| `ClientFeedback` | avaliações das clientes (feature 130/131) — leitura, resumo e filtros        |

## Valores computados (movidos para `client_ops.py`, sem duplicar regra)

- `search_clients(query)` — mesma busca sem acentos de hoje (`strip_accents_lower`/
  `unaccent_lower_sql` sobre `Client.name`, `ilike` sobre dígitos do telefone), limite 10,
  ordenado por nome.
- `quick_create_client(name, phone_raw, ...)` — normaliza telefone (`normalize_phone`), reaproveita
  cliente existente por telefone (chave única) ou cria novo; levanta `ClientValidationError` para
  nome vazio/telefone inválido (mesmas mensagens de hoje).
- `list_clients(query)` — mesma busca sem acentos, contagem de eventos por cliente via
  `EventClient` (distinct por evento), limite 300, ordenado por (nº eventos desc, nome asc).
- `get_client_detail(client_id)` — eventos via `EventClient` (mais recente primeiro, dedup por
  evento), relação por evento, total vendido = soma de `sale_value` dos eventos com valor.
- `update_client_fields(client, cpf, cnpj, address)` — mesmas regras de truncamento/`None` em
  campo vazio de hoje.
- `delete_client(client)` — apaga `EventClient` do cliente, zera `client_id` denormalizado nos
  eventos, depois apaga o `Client` — mesma ordem de hoje (evita órfãos).
- `summarize_feedback(period, from_raw, to_raw, score, tag, client_id)` — reaproveita
  `_parse_period` (`app/talents/routes.py`); calcula total, média geral, nº de clientes avaliadas,
  distribuição por nota (1–5), lista de atenção (nota ≤2, até 10, mais recentes primeiro), lista
  de clientes com pelo menos uma avaliação — mesmos cálculos de hoje.
- `ClientValidationError(field, message)` — exceção nova, única forma de erro de validação de
  negócio nesta fatia; `routes.py` (Jinja) converte em `flash`, `app/api/clientes_write.py`
  converte em 400 `{"error": {"message", "fields": {field: message}}}`.
