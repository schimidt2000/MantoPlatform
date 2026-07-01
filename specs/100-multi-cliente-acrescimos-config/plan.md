# Implementation Plan: Múltiplos clientes + tipos de acréscimo configuráveis + redesign

**Branch**: `100-multi-cliente-acrescimos-config` | **Date**: 2026-07-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/100-multi-cliente-acrescimos-config/spec.md`

## Summary

Três mudanças: (1) **múltiplos clientes por evento** com tipo de relação — nova associação
`EventClient` migrando o vínculo único atual; (2) **tipos de acréscimo configuráveis** na página de
Configurações de Preços (guardados no `pricing_config`; BV/Outro sempre presentes, BV protegido); (3)
**redesign** do editor de acréscimos (só apresentação).

## Technical Context

**Language/Version**: Python 3.x (Flask), SQLAlchemy, Jinja2, JS vanilla

**Primary Dependencies**: Flask, Flask-Migrate. Sem dependência nova.

**Storage**: PostgreSQL/SQLite. Nova tabela `event_clients` (migração manual + **data-migrate** do
`calendar_events.client_id`; down_revision `d6a7b8c9e0f1`). Tipos de acréscimo em
`SiteSetting.pricing_config`. Testar contra `manto_local`.

**Testing**: pytest/scripts contra `manto_local`. Casos: 2 clientes com relações; migração do vínculo
único; ficha do cliente via associação; regra ≥1 cliente; tipos configuráveis (BV protegido);
cálculo/salvamento de acréscimos idêntico.

**Constraints**: Não perder vínculos de cliente existentes (data-migrate). BV protegido e detectável por
`tipo == 'BV'`. Redesign sem mudar regras. Manter `client_id` denormalizado (primary = contratante) p/
compat de telas que mostram "o cliente".

**Scale/Scope**: 1 modelo novo + migração com data-migrate; edições em clientes/evento/orçamento/
configurações; CSS/HTML do editor.

## Constitution Check

- **Sem duplicação**: reusa a busca/criação rápida de clientes (feature 094) no editor multi; um único
  helper para os tipos de acréscimo (config). ✅
- **Não quebrar**: data-migrate preserva vínculos; `client_id` mantido como primary; acréscimos antigos
  intactos. ✅
- **Migração manual** + data-migrate conforme padrão; sem segredos. ✅

Resultado: PASS.

## Data Model

**`EventClient`** (tabela `event_clients`):

| Campo | Tipo | Notas |
|-------|------|-------|
| id | int PK | |
| event_id | FK(calendar_events) cascade | |
| client_id | FK(clients) | |
| relationship_type | str(30) | Contratante / Assessora / Mãe-Pai / Familiar / Outros |
| created_at | DateTime | |

`CalendarEvent.event_clients` (cascade). Mantém `client_id` (primary/contratante, sincronizado). Tipos de
relação: `CLIENT_RELATION_TIPOS` em `constants.py`.

**Config de tipos de acréscimo**: `pricing_config["acrescimo_tipos"]` (lista de tipos comuns). Helper
`acrescimo_tipos_list()` = salvos + `BV` + `Outro` (dedup; BV protegido). DEFAULTS = lista atual.

## Implementation Approach (phased)

1. **Modelo + migração (US1)**: `EventClient` + relationship; migração cria tabela e **copia**
   `client_id`→`event_clients` ('Contratante'); `CLIENT_RELATION_TIPOS`.
2. **Backend clientes multi (US1)**: `_handle_update_comercial` lê `client_id[]`/`client_relation[]`,
   recria `EventClient`, sincroniza `client_id` (contratante/primeiro), regra ≥1 cliente; `clientes`
   index/detail/delete via associação; `event_requires_client` continua, mas o handler valida associação.
3. **UI evento multi-cliente (US1 + US3)**: editor de clientes (linhas: busca/seleção + relação +
   remover) no lugar do picker único — reusando `/clientes/search` e `/clientes/quick-create`.
4. **Tipos de acréscimo configuráveis (US2)**: `pricing_config["acrescimo_tipos"]` + helper; settings.html
   com editor da lista (add/remove; BV/Outro fixos); orçamento/evento leem o helper.
5. **Redesign do editor de acréscimos (US3)**: CSS/HTML mais claro (cards, rótulos, estado vazio, R$/%
   destacado, BV em destaque) no orçamento e no evento — sem mudar cálculo/salvamento.
6. **Verificação** contra `manto_local`.

## Project Structure

```text
app/
├── models.py                    # EventClient + relationship; client_id mantido (primary)
├── constants.py                 # CLIENT_RELATION_TIPOS
├── orcamento/settings.py        # DEFAULTS.acrescimo_tipos + helper acrescimo_tipos_list; _migrate
├── orcamento/routes.py          # tipos via helper; settings POST edita a lista
├── calendar/routes.py           # _handle_update_comercial multi-cliente; render tipos via helper
├── clientes/routes.py           # index/detail/delete via EventClient
└── templates/
    ├── event_detail.html        # editor multi-cliente + editor de acréscimos redesenhado
    ├── clientes/detail.html     # eventos via associação (+ relação)
    ├── orcamento/index.html     # editor de acréscimos redesenhado
    └── orcamento/settings.html  # editor da lista de tipos de acréscimo
static/js/orcamento.js           # (ajustes visuais do editor, se necessário)

migrations/versions/
└── <hash>_event_clients.py      # tabela + data-migrate de client_id (down_revision d6a7b8c9e0f1)
```

**Structure Decision**: Associação `EventClient` como fonte de verdade, com `client_id` denormalizado
para compat. Tipos de acréscimo migram para a config (mesmo mecanismo dos demais preços). Redesign é
apresentação.

## Complexity Tracking

> Sem violações de constituição. A complexidade está na **migração de dados** (client_id → associação),
> mitigada por data-migrate idempotente e por manter `client_id` sincronizado.
