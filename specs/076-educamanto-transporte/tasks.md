# Tasks: Transporte no EducaManto (076)

**Feature**: `076-educamanto-transporte` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Sem modelo/migration. Verificação contra **`manto_local`**.

---

## Fase 1 — Helper compartilhado de distância

- [X] T001 `app/maps.py` (novo): `distance_km_ida(endereco)` retorna `(km_ida|None, error|None, http_status)` — move a lógica de Google Maps de `orcamento.api_distancia` (origem = endereço da Manto; km arredondado p/ cima).
- [X] T002 `app/orcamento/routes.py::api_distancia`: passa a chamar `app.maps.distance_km_ida` (mesmo comportamento/JSON). Verificar que o orçamento segue funcionando.

## Fase 2 — Backend EducaManto

- [X] T003 [US1] `app/educamanto/routes.py`: `GET /educamanto/api/distancia` (`_require_use`) usando o helper; retorna `{km_ida}` ou `{error}`.
- [X] T004 [US1] `app/educamanto/routes.py::index`: passar `transporte_json = json_for_script(settings.transporte)` (config de transporte do orçamento) ao template.

## Fase 3 — Frontend EducaManto (US1)

- [X] T005 [US1] `app/templates/educamanto/index.html`: bloco "Transporte" — endereço + botão "Calcular distância", rádio van/carro, checkbox carretinha (van), nº de carros (carro), nº de pessoas. `window.TRANSPORTE_CFG` via `transporte_json`.
- [X] T006 [US1] JS: `fetchDistancia()` (chama `/educamanto/api/distancia`) e `calcTransporte()` reproduzindo `calcular_van`/`calcular_carro` (tarifa/km ida+volta + adicional por pessoa; sem adicional show). Recalcula ao mudar tipo/carretinha/pessoas.
- [X] T007 [US1] Integrar ao `calcular()`: somar o transporte ao valor final (sem nota e com nota) e exibir linha "Transporte" no resumo/detalhe. Sem endereço (km=0) → transporte 0.

## Fase 4 — Verificação

- [X] T008 Contra **`manto_local`**: `/educamanto/api/distancia` responde como o do orçamento; conferir que a fórmula JS bate com `calcular_van`/`calcular_carro` para os mesmos parâmetros; página renderiza; sem endereço o valor final não muda; orçamento ainda funciona. `ruff check` sem erros novos.

---

## Dependências

- T001 → T002, T003. T004 → T005. T005 → T006 → T007. T008 ao final.

## MVP

T001–T003 + T005–T007 entregam o transporte somado ao valor final; T008 valida sem regressão.
