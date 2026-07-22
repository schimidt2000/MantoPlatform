# Implementation Plan: Feedback Público por Token em React

**Branch**: `164-feedback-publico-react` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/164-feedback-publico-react/spec.md`

## Summary

Quarta e última fatia da US5 (Superfícies Públicas) — migra a tela pública de feedback da
cliente (`/avaliar/<token>`, hoje Jinja em `app/feedback/routes.py`) para o app `frontend/apps/
public`, consumindo 2 endpoints JSON novos em `app/api/feedback_write.py` (dados do evento pelo
token + submissão). Toda a lógica de negócio (filtro de etiquetas por nota, validação de nome/
nota, persistência) é reaproveitada por import direto das funções/constantes já existentes em
`app/feedback/routes.py`. A rota Jinja `/avaliar/<token>` continua no ar em paralelo; a geração
do link (ação autenticada) não é tocada. Com esta fatia, a US5 fica 100% concluída.

## Technical Context

**Language/Version**: Python 3.11 (backend) + TypeScript 5.7 (frontend)

**Primary Dependencies**: Flask + SQLAlchemy + Flask-Limiter (reaproveitados, zero dependência
nova no backend). Frontend: React 18 + Vite + react-router-dom + TanStack Query + Tailwind CSS +
`@manto/ui` + `@manto/api-client` — todas já instaladas em `apps/public` desde a 161. Nenhuma
dependência nova.

**Storage**: PostgreSQL (`manto_local` para verificação) — mesmas tabelas `ClientFeedback`/
`CalendarEvent.feedback_token` já existentes, nenhum campo/migration novo.

**Testing**: script com `Flask test client` contra `manto_local` (paridade Jinja×API, requests
fora de `app.app_context()`); `tsc --noEmit` + `vite build` no frontend.

**Target Platform**: navegador (mobile-first, 320–430px), sem autenticação.

**Project Type**: web (Flask API + SPA React, monorepo `frontend/`).

**Performance Goals**: sem meta numérica nova — mesma carga que a tela Jinja atual atende hoje.

**Constraints**: nenhuma nova além das já em vigor nas fatias anteriores da US5.

**Scale/Scope**: 1 tela pública (avaliação, com estado de "link inválido" embutido — não é uma
rota separada, é o mesmo componente reagindo a um 404 do endpoint de leitura) + 1 tela de
agradecimento embutida no mesmo componente (troca de estado local, sem navegação — paridade com
`submitted` do Jinja), 2 endpoints JSON.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (reutilizar)**: zero regra de negócio nova — os 2 endpoints reaproveitam literalmente
  `POSITIVE_TAGS`, `ATTENTION_TAGS`, `_tags_for_score` de `app/feedback/routes.py` por import
  direto (mesmo padrão já usado na 163 com `app/formularios/routes.py`). Componentes `@manto/ui`
  (`Button`, `Card`, `Input`) reaproveitados.
- **II (padrões de código)**: endpoint novo em `app/api/feedback_write.py`, type hints/
  docstring; frontend com TypeScript estrito (sem `any`), componentes React pequenos (grupo de
  estrelas, grupo de etiquetas).
- **III (API first)**: 2 endpoints novos, 100% JSON — a rota Jinja `/avaliar/<token>` segue
  existindo em paralelo só pelo motivo documentado no Summary, não por regra de negócio nova.
- **IV (não quebrar)**: paridade verificada contra `manto_local` — mesmo `ClientFeedback` salvo
  (mesma nota, etiquetas filtradas, comentário) entre o caminho Jinja e o caminho API, para os
  mesmos dados de entrada. Rota Jinja segue funcionando sem alteração; `gerar_link` (autenticada)
  inteiramente intocada.
- **V (feedback)**: formulário nunca perde o nome já digitado num erro de validação; botão de
  envio com estado "Enviando..." (disabled); troca de nota anima a revelação do bloco de
  etiquetas (paridade com a transição CSS `max-height`/`opacity` já existente no Jinja, portada
  para Framer Motion); mensagens de erro amigáveis em pt-BR.
- **VIII (mobile-first)**: superfície pública de alto tráfego externo (link enviado por
  WhatsApp) — tela conferida em 320–430px antes de "pronto"; alvo de toque das estrelas ≥44px.
- **IX (movimento)**: revelação do bloco de etiquetas ao escolher a nota usa transição suave
  (Framer Motion `AnimatePresence`/altura animada), respeitando `prefers-reduced-motion` — mesma
  ideia da transição CSS que já existe no Jinja hoje, só portada para o padrão do projeto.

Sem violação nova.

## Project Structure

### Documentation (this feature)

```text
specs/164-feedback-publico-react/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/feedback-endpoints.md
└── tasks.md
```

### Source Code (repository root)

```text
app/api/feedback_write.py                  # NOVO — GET .../avaliar/<token> + POST submissão
app/api/__init__.py                        # + import de feedback_write

frontend/apps/public/
├── src/
│   ├── App.tsx                            # + rota /avaliar/:token
│   ├── lib/
│   │   └── feedback.ts                    # NOVO — tipos + hooks (useFeedbackEvent, useSubmitFeedback)
│   ├── components/feedback/
│   │   ├── StarRating.tsx                 # NOVO — grupo de 5 estrelas
│   │   └── TagChips.tsx                   # NOVO — chips de etiqueta (positiva/atenção)
│   └── pages/
│       └── AvaliarPage.tsx                # NOVO — tela única: formulário, agradecimento,
│                                           #   e link inválido (todos os 3 estados)

scripts/db/verify_164_feedback_publico_react.py  # NOVO: paridade Jinja×API (submissão válida,
                                                   # token inválido, etiqueta fora de categoria,
                                                   # nome/nota faltando)
```

**Structure Decision**: núcleo do backend fica só em `app/api/feedback_write.py`, que **importa**
(não copia) `POSITIVE_TAGS`/`ATTENTION_TAGS`/`_tags_for_score` de `app/feedback/routes.py` —
mesmo padrão da 163 (`app/formularios/routes.py` já separa a lógica em construções puras,
reaproveitáveis sem extração). A validação de nome/nota e a persistência do `ClientFeedback` são
simples o bastante (menos de 15 linhas) para ficarem só no endpoint novo, sem precisar de uma
função extraída à parte — diferente da 162 (onde ~100 linhas de validação justificavam extração).
`AvaliarPage.tsx` é um único componente com 3 estados (formulário / agradecimento / link
inválido) — paridade exata com o Jinja de hoje, que já resolve os 3 estados num único template
(`public.html` com `submitted`/`error`, `invalid.html` para 404).

## Complexity Tracking

Nenhuma violação nova.
