# Tasks: Gerar orçamento PDF no EducaManto + histórico (077)

**Feature**: `077-educamanto-orcamento-pdf` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Migration **manual**. Verificação contra **`manto_local`**.

---

## Fase 1 — Modelo + migration

- [X] T001 `app/models.py`: `class EducaMantoQuote` (`educamanto_quotes`: user_id, created_at, client_name, packages_label, snapshot Text) + relationship User.
- [X] T002 `migrations/versions/w9f0a1b2c3d4_educamanto_quotes.py` (down_revision = head `v8e9f0a1b2c3`): `op.create_table` + índice em `user_id`.

## Fase 2 — Explicações + PDF

- [X] T003 `app/educamanto/routes.py` (ou módulo): constante `PACKAGE_EXPLANATIONS` (mapa por nome normalizado: master/intermediário/básico → textos fixos) + helper `explanation_for(name)`.
- [X] T004 `app/educamanto/pdf.py` (novo): `gerar_orcamento_pdf(snapshot)` — uma página por pacote (nome, explicação, dias 1/2 sessões, VALOR SEM NF, VALOR COM NF, formas de pagamento), identidade Manto; tenta embutir logo extraído de `Orccamentos_Educamanto.pdf`.

## Fase 3 — Rotas (US1/US2)

- [X] T005 [US1] `POST /educamanto/orcamento/gerar` (`_require_use`): recebe JSON (client_name, d1, d2, ensemble, transporte, packages[{id,name,sem_nota,com_nota}]); valida ≥1 pacote e dias; cria `EducaMantoQuote` (snapshot) e retorna o PDF p/ download.
- [X] T006 [US2] `GET /educamanto/orcamento/<int:id>/pdf` (`_require_use`): re-renderiza o PDF a partir do snapshot salvo.
- [X] T007 [US2] `GET /educamanto/historico` (`_require_use`): lista os orçamentos (data, cliente, pacotes) com busca por cliente/data + link p/ baixar; template `templates/educamanto/historico.html`.

## Fase 4 — Frontend (US1)

- [X] T008 [US1] `app/templates/educamanto/index.html`: botão "Gerar orçamento" + link "Histórico"; modal com checkboxes dos pacotes (ativo pré-marcado) + campo cliente opcional.
- [X] T009 [US1] JS: fatorar `valoresPacote(p, d1, d2, E)` (usado pela tela e pela geração, garantindo paridade); ao gerar, validar dias, calcular por pacote (+ transporte), `fetch` POST JSON, baixar o PDF (blob). Aviso se nenhum pacote/dias.

## Fase 5 — Verificação

- [X] T010 Contra **`manto_local`**: gerar PDF com 2 pacotes (2 páginas) via test client; conferir que `sem_nota/com_nota` do snapshot batem com `valoresPacote`+transporte; histórico lista e re-baixa idêntico; sem pacote/dias bloqueia; `ruff check` sem erros novos.

---

## Dependências

- T001 → T002 → (T005). T003 → T004 → T005 → T006/T007. T008 → T009. T010 ao final.

## MVP

T001–T005 + T008/T009 entregam gerar+baixar; T006/T007 completam o histórico; T010 valida.
