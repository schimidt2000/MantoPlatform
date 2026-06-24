# Tasks: Formulário público de cadastro (086)

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Sem testes automatizados solicitados — verificação manual contra `manto_local`.

## Phase 1: Setup

- [X] T001 Criar pacote `app/cadastro/__init__.py` e esqueleto `app/cadastro/routes.py` com
  `cadastro_bp = Blueprint("cadastro", __name__, url_prefix="/cadastro")`.
- [X] T002 Registrar `cadastro_bp` em `app/__init__.py` e adicionar `/cadastro` aos prefixos liberados
  em `portal_domain_routing`.

## Phase 2: User Story 1 — Cadastro público com upload próprio (P1) 🎯 MVP

- [X] T003 [US1] `GET /cadastro`: renderizar `app/templates/cadastro/form.html` (standalone,
  mobile-first, seções, obrigatórios, dicas de tamanho, preview, honeypot, trava de duplo envio).
- [X] T004 [US1] Helpers de upload em `app/cadastro/routes.py`: validação de ext + tamanho (fotos 8MB:
  jpg/png/webp; docs 10MB: + pdf) e gravação via `save_file`.
- [X] T005 [US1] `POST /cadastro`: validar obrigatórios, normalizar CPF/altura/passaporte (reuso do
  importer), salvar arquivos, criar `Talent(status="pending", source="public_form")`, redirecionar a
  `/cadastro/enviado`; `GET /cadastro/enviado` → `app/templates/cadastro/success.html`.

## Phase 3: User Story 2 — Vira talento pendente + anti-duplicado (P1)

- [X] T006 [US2] Bloquear **CPF duplicado** (re-render com erro, preservando textos) e garantir entrada
  no fluxo de pendentes (`status="pending"`), em `app/cadastro/routes.py`.

## Phase 4: User Story 3 — Segurança e limites (P2)

- [X] T007 [US3] `@limiter.limit` no POST + honeypot (`website`) que finge sucesso sem criar; `strip()`
  nos textos, em `app/cadastro/routes.py`.

## Phase 5: Polish & Verificação

- [X] T008 Verificar contra `manto_local`: GET 200 sem login; POST cria pendente com 3 fotos
  gravadas; CPF duplicado bloqueado; arquivo grande/ext inválida rejeitado; honeypot finge sucesso;
  `portal_domain_routing` libera `/cadastro`. Limpar talento/arquivos de teste. `ruff` sem erros novos.

## Dependencies

- T001 → T002 → (T003..T007). Tudo em `app/cadastro/` + 2 linhas em `__init__`.
- T008 por último.

## MVP

User Stories 1+2 (formulário público que cria talento pendente com upload próprio) = entrega central.
