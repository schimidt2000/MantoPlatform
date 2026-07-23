# Data Model — Corrigir elenco incompleto ao criar evento a partir de orçamento

Nenhuma entidade nova e nenhuma migration. Esta correção é um bugfix de cálculo em cima de
entidades já existentes:

- **`OrcamentoHistory`** (`app/models.py`) — inalterada. `form_snapshot` continua sendo a fonte
  do pré-preenchimento; nenhum campo novo é gravado a partir de agora (a correção é só na
  releitura/recálculo do snapshot já existente).
- **`EventRole`** (`app/models.py`) — inalterada. Continua recebendo `cache_value`/`cache_cap`
  no momento da criação do evento, só que agora com o valor correto (incluindo o acréscimo de
  "show customizado" quando aplicável).

## Função compartilhada nova (não é entidade de dado, é lógica de negócio)

- **`compute_show_pricing(performers: list[dict], show_sosia_tipo: str) -> tuple[bool, float]`**
  (novo, em `app/orcamento/pricing.py`): dado a lista de performers do snapshot e o tipo de show
  selecionado, devolve `(has_show, custom_add_per_artist)` — `custom_add_per_artist` é `0.0` se
  `show_sosia_tipo != "customizado"`, senão `SOSIA_CUSTOM_ADD_PER_ARTIST` (constante nova no
  mesmo módulo, valor `50`, mesmo número hoje hardcoded em `app/orcamento/routes.py`). Substitui
  as duas reimplementações hoje existentes em `app/orcamento/routes.py` e em
  `_compute_performer_caches` (`app/calendar/routes.py`).
