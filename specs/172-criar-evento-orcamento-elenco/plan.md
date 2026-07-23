# Implementation Plan: Corrigir elenco incompleto ao criar evento a partir de orçamento

**Branch**: `172-criar-evento-orcamento-elenco` | **Date**: 2026-07-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/172-criar-evento-orcamento-elenco/spec.md`

## Summary

Usuário relatou que a tela de criação de evento a partir de um orçamento salvo
(`/events/new?orcamento_id=<id>`, fluxo Jinja) não traz mais o elenco (personagens + equipe)
completo como antes. A investigação (Phase 0, `research.md`) comparou o cálculo original do
orçamento (`app/orcamento/routes.py`) com o recálculo usado para pré-preencher a tela de criação
de evento (`_compute_performer_caches`, `app/calendar/routes.py`) e encontrou uma **duplicação
de regra de negócio** entre os dois pontos: o acréscimo de "Show customizado" (+R$50/artista,
opção de sósia) é aplicado no total do orçamento mas não no cachê individual de cada
personagem recalculado para a tela de criação de evento. A correção extrai essa regra
(detecção de "tem show" + acréscimo de show customizado) para uma única função em
`app/orcamento/pricing.py`, reusada pelos dois pontos — eliminando a duplicação (Princípio I da
constituição) e fazendo o elenco pré-preenchido bater com o que foi orçado, tanto no fluxo Jinja
quanto no React (mesmo núcleo `_build_orcamento_prefill`, já reusado por `GET /api/events/new/
prefill`, feature 152).

## Technical Context

**Language/Version**: Python 3.11 (Flask), mesmo runtime já usado no projeto.

**Primary Dependencies**: Flask, SQLAlchemy — nenhuma dependência nova. Reusa
`app/orcamento/pricing.py`, `app/orcamento/settings.py`, `app/calendar/routes.py`.

**Storage**: PostgreSQL (Railway prod / `manto_local` dev) — nenhuma mudança de schema.

**Testing**: script Python com Flask test client contra `manto_local`, requests fora de
`app.app_context()` (padrão do projeto — ver `CLAUDE.md`/Constituição Portão de Qualidade).

**Target Platform**: Backend Flask (Railway), consumido pelo wrapper Jinja legado
(`event_create.html`) e pela API JSON já existente (`app/api/agenda.py`,
`GET /api/events/new/prefill`).

**Project Type**: Web (backend Flask + frontend React, mas esta correção é 100% backend —
nenhum componente React é criado/alterado; o React já consome o mesmo endpoint que será
corrigido).

**Performance Goals**: N/A — cálculo em memória sobre uma lista pequena de performers (dezenas,
não milhares); sem impacto de performance mensurável.

**Constraints**: Não alterar o contrato JSON de `_build_orcamento_prefill` /
`GET /api/events/new/prefill` (mesmas chaves, feature 152) — só os valores de `caches[].
cache_1h..4h` mudam (para orçamentos com show customizado). Não é permitido criar `render_template`
novo nem lógica de negócio nova dentro de uma view (Princípio III) — a regra de negócio migra
para `app/orcamento/pricing.py`, não para dentro de `_compute_performer_caches`/`routes.py`.

**Scale/Scope**: 2 arquivos de produção tocados (`app/orcamento/routes.py`,
`app/calendar/routes.py`) + 1 função nova em `app/orcamento/pricing.py`. Sem migration, sem
tela nova.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Princípio I (Reutilizar antes de criar) — GATE CENTRAL desta correção**: o próprio bug é
  causado por violação deste princípio (lógica duplicada). A correção proposta (extrair
  `compute_show_pricing` para `app/orcamento/pricing.py`, único ponto de verdade) resolve a
  violação em vez de adicionar uma terceira cópia. ✅ PASS.
- **Princípio II (padrões Python)**: função nova com type hints + docstring Google style,
  função pequena (<30 linhas), sem aninhamento profundo. ✅ PASS (a aplicar na implementação).
- **Princípio III (Arquitetura em camadas)**: `compute_show_pricing` é lógica de negócio pura
  (sem `request`/`render_template`), chamada por `app/orcamento/routes.py` (view Jinja legada) e
  por `_compute_performer_caches` (núcleo compartilhado Jinja+API) — nenhuma lógica nova dentro
  de view. ✅ PASS.
- **Princípio IV (Não quebrar o que funciona)**: verificação funcional (quickstart.md) cobre
  explicitamente o caso comum (sem show customizado) para garantir zero regressão nos ~5
  orçamentos reais já testados, além do caso corrigido. ✅ PASS (a executar antes de "pronto").
- **Restrição de stack "Proibido Jinja2... render_template"**: esta correção **não cria** rota
  Jinja nova nem usa `render_template` em código novo — apenas corrige um cálculo dentro de um
  wrapper Jinja legado já existente (`app/calendar/routes.py::create_event`), que o próprio
  CLAUDE.md documenta como mantido em paralelo (strangler-fig) e não coberto pela proibição de
  código NOVO. Nenhuma linha de HTML/Jinja é adicionada; o `event_create.html` não muda. ✅ PASS,
  sem exceção a registrar no Complexity Tracking.
- **Portão "verificação funcional contra `manto_local`"**: aplicável, coberto pelo
  `quickstart.md`.
- **Portão "changelog do time"**: aplicável — entrada em `docs/changelog.html` ao final
  (mudança visível: elenco agora vem completo/correto ao criar evento a partir de orçamento).

Nenhuma violação — **Complexity Tracking não se aplica** a este plano.

## Project Structure

### Documentation (this feature)

```text
specs/172-criar-evento-orcamento-elenco/
├── plan.md              # This file
├── research.md          # Phase 0 — causa raiz encontrada
├── data-model.md         # Phase 1 — função compartilhada nova (sem entidades novas)
├── quickstart.md         # Phase 1 — script de verificação
└── tasks.md              # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── orcamento/
│   ├── pricing.py     # + compute_show_pricing() e SOSIA_CUSTOM_ADD_PER_ARTIST (novo)
│   └── routes.py       # passa a chamar compute_show_pricing() em vez de reimplementar
│                        # has_show e o acréscimo "+R$50/artista" inline
└── calendar/
    └── routes.py       # _compute_performer_caches() passa a chamar compute_show_pricing()
                         # e aplica custom_add_per_artist ao cachê de cada personagem
                         # (não a coordenador/técnico/maquiador)

scripts/
└── verify_172_orcamento_elenco.py   # script de verificação funcional (novo, não versionado
                                       # em produção — segue o padrão dos demais scripts de
                                       # verificação do projeto)
```

**Structure Decision**: Nenhuma estrutura nova de projeto — mudança pontual em 2 arquivos de
backend já existentes + 1 função nova no módulo de precificação já existente
(`app/orcamento/pricing.py`), que já concentra as outras funções `get_*_prices`. Não há
frontend a alterar (React consome o mesmo endpoint, que passa a devolver valores corretos sem
mudança de contrato).

## Complexity Tracking

Não se aplica — nenhuma violação de princípio identificada no Constitution Check.
