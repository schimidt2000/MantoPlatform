# Tasks: EducaManto vendedor + PDF (080)

**Feature**: `080-educamanto-vendedor-pdf` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Só template + pdf.py. Verificação contra **`manto_local`**.

---

## Fase 1 — PDF (US4)

- [X] T001 `app/educamanto/pdf.py`: `_tipo_for(name)` por **substring** (master/intermediário/econômica; básico→econômica); `SHORT_DESC` (curta, por tipo) e `LONG_DESC` (planos.md, por tipo).
- [X] T002 `app/educamanto/pdf.py::_draw_page`: descrição **curta** logo abaixo do título (via tipo); bloco **"O QUE ESTÁ INCLUSO"** com a descrição **longa** depois das formas de pagamento; compactar para caber em 1 página.

## Fase 2 — Calculadora vendedor (US1/US2/US3)

- [X] T003 [US1] `educamanto/index.html`: limitar acréscimo ao **valor original** (`valoresPacote(...,0).semNota`) — clamp no input + aviso de máximo em `calcular()`.
- [X] T004 [US2] `educamanto/index.html`: transporte sempre **van c/ carretinha** (`calcTransporte` fixa tarifa); ocultar seleção de tipo/carretinha/carros e o campo de pessoas; pessoas = catering da apresentação.
- [X] T005 [US2] `educamanto/index.html`: título "Transporte (opcional)" → "Transporte (APENAS SE FOR FORA DA CIDADE DE SÃO PAULO)".
- [X] T006 [US3] `educamanto/index.html`: painel "Configurações do pacote" dentro de `{% if can_manage %}` (super admin).

## Fase 3 — Verificação

- [X] T007 Contra **`manto_local`**: gerar PDF p/ pacote "… - Master/Intermediário/Econômica" → curta abaixo do título + longa após pagamento (mesma página); cap do acréscimo (clamp); transporte van c/ carretinha; config oculta p/ não-admin. `ruff` sem erros novos.

---

## Dependências

- T001 → T002. T003/T004/T005/T006 independentes no template. T007 ao final.

## MVP

T001/T002 (PDF) + T003 (cap) + T004 (transporte) são o núcleo; T005/T006 completam.
