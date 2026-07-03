# Implementation Plan: Dispensar Tarefa de Casting Pendente

**Branch**: `108-dispensar-tarefa-casting` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/108-dispensar-tarefa-casting/spec.md`

## Summary

Causa raiz confirmada em `app/calendar/routes.py` (função de sync, ~linha 1893–1921): a cada
sincronização, o título do evento é reparseado (`parse_characters`); personagens ainda
listados no título e SEM cargo correspondente em `existing` são recriados via
`EventRole(event_id=..., character_name=char)`. Excluir o cargo manualmente o tira de
`existing`, então a próxima sync o recria — daí o cargo "fantasma" voltar.

Solução: em vez de excluir, o cargo ganha um estado de **dispensado** (`dismissed_at`,
`dismissed_by`). Como o cargo continua existindo (só sem talento e marcado como dispensado),
ele permanece em `existing` na sync — a sync nunca mais toca nele (nem apaga, nem recria).
A query de tarefas pendentes (`app/__init__.py`, rota `/`) passa a excluir cargos dispensados
de `pending_casting`, `total_casting` e `done_casting`.

Duas rotas novas em `calendar_bp` (fora do dispatch de `event_detail`, para poder ser
acionadas direto da home sem sair dela): `POST /roles/<int:role_id>/dismiss` e
`POST /roles/<int:role_id>/restore`, ambas restritas a SUPERADMIN, com `EventLog` de
auditoria, redirecionando de volta para `request.referrer` (ou home).

A home ganha, na seção Casting: botão "Dispensar" em cada linha pendente (com `confirm()` —
ação simples, não é caso de feedback inline da constituição V) e um bloco recolhível
"Dispensadas" (visível só a super admin) listando os cargos dispensados daquele setor com
quem/quando e botão "Restaurar".

## Technical Context

**Language/Version**: Python 3.12 + Flask + SQLAlchemy (stack existente)

**Primary Dependencies**: nenhuma nova — segue o padrão de `_handle_delete_role`/
`_handle_delete_contract` (RBAC, `EventLog`, `db.session`)

**Storage**: PostgreSQL (produção/`manto_local`); 1 migration manual (2 colunas em
`event_roles`: `dismissed_at`, `dismissed_by`)

**Testing**: test client contra `manto_local` (requests fora de app_context — regra da
constituição v1.3.0), cobrindo RBAC (403 para não-superadmin), dispensa, contagens, e o
cenário central: sync após dispensa NÃO recria/reverte o cargo

**Target Platform**: sistema interno (desktop-first), tela usada é a home

**Project Type**: web app Flask monolítico

**Performance Goals**: irrelevante — 2 colunas indexáveis, sem impacto de escala

**Constraints**: NÃO alterar a lógica de sync existente para outros casos (apagar/renomear/
criar cargos por título) — o cargo dispensado simplesmente passa a "não fazer nada" na sync
por já estar em `existing`; zero mudança de comportamento para cargos não dispensados

**Scale/Scope**: 1 migration; `app/models.py` (2 colunas + relationship); `app/calendar/
routes.py` (2 rotas novas + ajuste de RBAC); `app/__init__.py` (3 queries ajustadas + cargos
dispensados passados ao template); `app/templates/home.html` (botão Dispensar + bloco
Dispensadas na seção Casting)

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar antes de criar | ✅ Segue o padrão exato de `_handle_delete_contract`/`_handle_delete_role` (RBAC inline + EventLog); reusa `_is_superadmin()` já definido no módulo. |
| II. Padrões Python | ✅ Type hints + docstrings nas rotas novas; nomes descritivos (`dismissed_at`/`dismissed_by`, não abreviado). |
| III. Camadas | ✅ Rotas só orquestram; sem regra nova de negócio fora do padrão existente do módulo. |
| IV. Não quebrar o que funciona | ✅ Sync não muda para nenhum cargo não dispensado (cargo dispensado só passa a ficar "parado" em `existing`, mesmo comportamento de um cargo pendente comum do ponto de vista da sync); verificação cobre o cenário de regressão explícito da spec. |
| V. UI/UX + feedback | ✅ Confirmação antes de dispensar (ação não trivial mas reversível — `confirm()` é aceitável para isso, não é erro/validação); botão desabilita via proteção global de duplo envio (feature 107, `base.html`); flash de sucesso. |
| VI. Planejar antes de codar | ✅ Este plano, causa raiz já rastreada até a linha exata do sync. |
| VII. Moeda BR | N/A — feature sem valores monetários. |

**Gate: PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/108-dispensar-tarefa-casting/
├── plan.md              # Este arquivo
├── research.md          # Fase 0 — decisões técnicas
├── data-model.md        # Fase 1 — colunas novas + migration
├── quickstart.md        # Fase 1 — roteiro de verificação
├── contracts/
│   └── routes.md        # Fase 1 — contrato das rotas novas
└── tasks.md             # Fase 2
```

### Source Code (repository root)

```text
migrations/versions/
└── <novo>_event_role_dismiss.py       # manual; down_revision = a3b4c5d6e7f8

app/
├── models.py                          # EventRole += dismissed_at, dismissed_by, relationship dismisser
├── calendar/routes.py                 # POST /roles/<id>/dismiss, /roles/<id>/restore (SUPERADMIN);
│                                      #   sync inalterada (cargo dispensado já cai em `existing`)
├── __init__.py                        # rota / (home): pending_casting/total_casting/done_casting
│                                      #   excluem dismissed_at.isnot(None); + dismissed_casting p/ template
└── templates/home.html                # seção Casting: botão "Dispensar" por linha + bloco
                                       #   recolhível "Dispensadas" (superadmin) com "Restaurar"
```

**Structure Decision**: mudança inteiramente dentro do módulo de agenda/eventos existente +
home dashboard; nenhum blueprint ou arquivo novo.

## Decisões de design (detalhe em research.md)

1. **Coluna dupla vs. tabela de log separada**: 2 colunas nullable em `EventRole`
   (`dismissed_at`, `dismissed_by`) — estado simples (dispensado ou não) não justifica tabela
   própria; segue o padrão já usado no próprio modelo (`figurino_done_at`, `event_changed_at`).
2. **Rotas fora do dispatch de `event_detail`**: para permitir dispensar/restaurar direto da
   home sem navegar para a página do evento, com redirect para `request.referrer` (cai de
   volta na home) — em vez de forçar redirect para `event_detail` como o dispatch genérico faz.
3. **RBAC restrito a SUPERADMIN** (não `CASTING`): a spec é explícita (FR-006) — mais restrito
   que `_handle_delete_role` (que aceita CASTING também), porque dispensar afeta métricas e
   relatórios de forma mais duradoura que remover um cargo específico.
4. **Sync**: nenhuma linha de código do sync muda. A dispensa funciona só porque o cargo
   dispensado nunca é removido de `existing` — ele é tratado exatamente como qualquer outro
   cargo pendente do ponto de vista da sync (branch `if char in existing: pass`).
5. **Bloco "Dispensadas"**: recolhido por padrão (mesmo padrão visual dos setores da home,
   `sector-panel`/`toggleSector`), só renderizado quando `is_superadmin` — outros papéis nem
   recebem os dados no contexto do template.

## Complexity Tracking

Sem violações — tabela não aplicável.
