# Tasks: Remover "Geral" de "O que está incluso" (082)

**Feature**: `082-educamanto-pdf-sem-geral` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Só `pdf.py`. Verificação contra **`manto_local`**.

---

## Fase 1 — Conteúdo do PDF (US1)

- [X] T001 [US1] `app/educamanto/pdf.py`: em `LONG_DESC`, remover a tupla `("Geral", …)` de **master**, **intermediario** e **economica**, mantendo Iluminação/Sonorização/Cenografia.

## Fase 2 — Verificação

- [X] T002 Contra **`manto_local`**: gerar PDF (Master/Intermediário/Econômica) → "Geral" **ausente** em "O QUE ESTÁ INCLUSO"; Iluminação/Sonorização/Cenografia **presentes**; descrição curta (abaixo do título) inalterada. `ruff` sem erros novos.

---

## Dependências

- T001 → T002.

## MVP

T001 entrega o pedido; T002 valida.
