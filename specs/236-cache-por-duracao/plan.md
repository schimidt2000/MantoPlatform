# Implementation Plan: Cachê sugerido pela duração real do evento

**Branch**: `236-cache-por-duracao` | **Date**: 2026-08-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/236-cache-por-duracao/spec.md`

## Summary

O prefill de cachês por papel já existe (`_compute_performer_caches`, feature 152/172) e já
inclui noturno (+50 ≥19h) e adicional fora-SP por pessoa — mas só produz valores para 1–4h, a
tela de criação só oferece botões de 1–4h, e a criação mapeia a duração com
`{"1"..."4"}.get(duracao, 0)`: qualquer outra coisa cai no cachê de **1 hora** (e vira teto que
`assign_casting_role` IMPÕE a não-superadmin). A feature: (1) régua de extrapolação >4h no
cálculo por papel — base de 4h SEM adicionais ÷ 4 × horas, adicionais fixos somados por fora;
(2) criação de evento recalcula os cachês NO SERVIDOR para a duração real (fonte única,
qualquer duração ≥1), eliminando o fallback; (3) tela de criação ganha "Outra duração (h)";
(4) casting ganha o aviso espelhado "abaixo do sugerido". Sem migração de banco; preço ao
cliente intocado.

## Technical Context

**Language/Version**: Python 3.12 (Flask) · TypeScript 5 (React 18 + Vite)

**Primary Dependencies**: tabelas de preço em `app/orcamento/pricing.py`/`settings.py` (fonte
única já usada pelo prefill); TanStack Query; `@manto/money`

**Storage**: PostgreSQL (`manto_local` para verificação) — **sem migração** (nenhum campo novo)

**Testing**: `verify_236.py` contra `manto_local` (casos-gabarito: orçamento 1806/evento do
Baile do Addan e orçamento 1573/mascotes) + `npx tsc --noEmit` + validação no app real

**Target Platform**: web interna (SPA `apps/internal` + API Flask)

**Project Type**: monorepo existente

**Performance Goals**: nenhum novo — cálculo é O(nº de papéis)

**Constraints**: paridade byte-a-byte com o comportamento atual para durações 1–4h (SC-005);
preço ao cliente inalterado (FR-007); teto continua imposto a não-superadmin (semântica de
`casting_ops` intocada — muda só o VALOR do teto)

**Scale/Scope**: 2 arquivos backend + 2 telas frontend; ~6 tarefas

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar antes de criar | **PASS** — a régua entra DENTRO de `_compute_performer_caches` (única fonte dos cachês por papel, já usada por prefill e criação); nenhuma tabela ou função paralela. |
| II. Padrões Python/TS | **PASS** — type hints/docstrings; TS estrito. |
| III. API-first / camadas | **PASS (melhora)** — a criação passa a recalcular os cachês no servidor a partir do `orcamento_history_id` em vez de confiar na lista `orc_caches` do cliente (mesma direção da 235). |
| IV. Não quebrar o que funciona | **PASS** — recompute do servidor usa a MESMA função do prefill (paridade 1–4h garantida por construção); `orc_caches` do cliente continua aceito como fallback quando não há orçamento vinculado. |
| V. UX com feedback | **PASS** — aviso novo "abaixo do sugerido" informativo, sem bloqueio; botão de duração extra com o mesmo padrão visual dos 1–4h. |
| VI. Full path SDD | **PASS** — esteira completa nesta pasta. |

Sem violações (Complexity Tracking vazio).

## Project Structure

### Documentation (this feature)

```text
specs/236-cache-por-duracao/
├── plan.md              # Este arquivo
├── research.md          # Decisões técnicas
├── data-model.md        # Sem schema novo — semântica dos campos existentes
├── quickstart.md        # Roteiro de validação (casos-gabarito reais)
├── contracts/
│   └── api-criacao-evento.md
├── verify_236.py        # Verificação contra manto_local
└── tasks.md             # (/speckit-tasks)
```

### Source Code (repository root)

```text
app/calendar/routes.py            # _compute_performer_caches: parâmetro de horas + régua >4h;
                                  # _create_roles_from_input/_criação: duração int ≥1, recompute
                                  # server-side via orcamento_history_id, fim do fallback→1h
app/api/agenda_write.py           # passa a duração real/ orçamento id ao núcleo (sem mudança de contrato)
frontend/apps/internal/src/
├── pages/EventCreatePage.tsx     # "Outra duração (h)" (pré-carrega duracao_custom do orçamento)
└── components/EventDetail/CastingSection.tsx   # aviso "abaixo do sugerido" (espelho do atual)
```

**Structure Decision**: nenhuma estrutura nova — a régua vive na função que já é fonte única
dos cachês por papel; a criação ganha recompute server-side; o restante é fiação de UI.
