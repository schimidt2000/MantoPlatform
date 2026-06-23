# Implementation Plan: Transporte no EducaManto (076)

**Branch**: `076-educamanto-transporte` | **Date**: 2026-06-23 | **Spec**: [spec.md](spec.md)

## Summary

Adicionar ao EducaManto um bloco de transporte idêntico ao do orçamento: endereço → distância
(Google Maps) → van/carro (+ carretinha) + nº de pessoas → transporte (tarifa/km + adicional por
pessoa), somado ao valor final. Reutiliza a configuração de transporte e o cálculo de distância do
orçamento (extraídos para um helper compartilhado). **Sem modelo, sem migration.**

## Technical Context

**Language/Version**: Python 3.11, Flask; Jinja2 + JS vanilla (cálculo client-side, como o EducaManto
já faz).

**Primary Dependencies**: `googlemaps` (já usado), config `settings.transporte` (já existe).

**Storage**: sem migration.

**Testing**: contra **`manto_local`** — endpoint de distância do EducaManto responde igual ao do
orçamento; a fórmula JS reproduz `calcular_van`/`calcular_carro`; página renderiza; sem endereço o
valor final não muda. `ruff` sem erros novos.

**Constraints**: reutilizar (fonte única de cálculo/config); não regredir o valor final atual;
permissões do EducaManto (inclui ENSAIO, que não tem acesso ao endpoint do orçamento → daí o
endpoint próprio); pt-BR; injeção de JSON segura (`json_for_script`, feature 074).

**Scale/Scope**: novo `app/maps.py` (helper de distância); `app/orcamento/routes.py` (usa o helper);
`app/educamanto/routes.py` (endpoint `/api/distancia` + `transporte_json` no index);
`app/templates/educamanto/index.html` (bloco de transporte + JS).

## Constitution Check

- **I. Reutilizar (NÃO-NEGOCIÁVEL)**: ✅ Helper de distância compartilhado; mesma config de
  transporte; mesma fórmula.
- **IV. Não quebrar (NÃO-NEGOCIÁVEL)**: ✅ Sem endereço → valor final inalterado; orçamento
  verificado após o refactor do helper.
- **VII. Valores BR (NÃO-NEGOCIÁVEL)**: ✅ Exibição em pt-BR.

**Resultado**: PASS — sem migration.

## Project Structure

```text
app/maps.py                         # distance_km_ida(endereco) -> (km|None, error|None, status)
app/orcamento/routes.py             # api_distancia passa a usar app.maps (mesmo comportamento)
app/educamanto/routes.py            # GET /educamanto/api/distancia (_require_use) + transporte_json
app/templates/educamanto/index.html # bloco "Transporte" (endereço+calcular, van/carro, carretinha,
                                     #   pessoas) + JS calcTransporte; soma ao valor final + linha
```

**Structure Decision**: Helper compartilhado + bloco client-side no EducaManto. Sem migration.

## Complexity Tracking

> Sem violações. Adicional de show do orçamento omitido (não se aplica ao EducaManto).
