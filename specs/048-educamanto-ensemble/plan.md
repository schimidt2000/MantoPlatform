# Implementation Plan: EducaManto ensemble + catering por pessoa + dropdown + acesso ensaio

**Branch**: `048-educamanto-ensemble` | **Date**: 2026-06-15 | **Spec**: [spec.md](./spec.md)

## Summary

Com migration. Decisões: catering vira **por pessoa padronizado** (ensaio R$28; apresentação R$55/1s,
R$73/2s); ensemble entra em ensaio + apresentação + ajuda de custo; cachê do ensemble por cenário
(350/600/300/550) configurável.

## Design

### 1. Modelo (`app/models.py`)
- `EducaMantoPackage`: + `ensemble_1s=350, ensemble_2s=600, ensemble_1s_days=300, ensemble_2s_days=550`.
- `EducaMantoItem`: + `ensemble_add` (Integer, default 0) — quanto a qtd cresce por ensemble.
- `to_dict()` inclui os novos campos.

### 2. Migration `o1d2e3f4a5b6_educamanto_ensemble.py`
- add colunas (server_default p/ não quebrar).
- por pacote (loop na connection): H = qtd da "Ajuda de custo ensaio" (ou 11). Atualiza por nome:
  - "Ajuda de custo ensaio": ensemble_add=1.
  - "Catering ensaio": qty=H, custos=28 (4 cenários), ensemble_add=1.
  - "Catering apresentação": qty=H, custos=55/73/55/73, ensemble_add=1.
  - ensemble_* do pacote = 350/600/300/550.

### 3. `app/educamanto/routes.py`
- `_CAN_USE` += ENSAIO (gestão segue só superadmin).
- `_DEFAULT_ITEMS`: catering por pessoa (qty 11, 28 / 55-73) + coluna ensemble_add nas tuplas.
- `_parse_items_from_form`: lê `item_ensemble_add[]`.
- create/edit: lê `ensemble_1s/2s/1s_days/2s_days`.

### 4. `app/templates/educamanto/index.html`
- Abas → **dropdown** (`<select>` que navega por `?pkg=`).
- Bloco "Ensemble": input de quantidade (default 0).
- JS: `effQty = qty + ensemble_add*E`; linha sintética "Ensemble" (qty E, custo por cenário do
  pacote) somada ao custo/venda; recalcula ao mudar E. Sem E, idêntico ao atual.

### 5. `app/templates/educamanto/package_form.html`
- Painel "Cachê do ensemble" (4 campos).
- Coluna "Ensemble +" por item (preserva ensemble_add na edição, que recria os itens).

### 6. `app/templates/base.html`
- Links EducaManto (calculadora + pacotes) visíveis também para ENSAIO.

## Verificação
- ruff + boot + migration local.
- Test client: ENSAIO acessa /educamanto e NÃO gerencia (403 em create); to_dict traz ensemble_*;
  pacote default após migration tem catering por pessoa (qty 11) e ensemble_add=1 nos 3 itens;
  dropdown presente; JS de ensemble presente. Cálculo (unidade): com E=0 valor == base; E=3 soma
  3×cachê + 3 pessoas em cada catering + ajuda de custo 11→14.

## Project Structure
```text
migrations/versions/o1d2e3f4a5b6_educamanto_ensemble.py
app/models.py
app/educamanto/routes.py
app/templates/educamanto/index.html
app/templates/educamanto/package_form.html
app/templates/base.html
```

## Fora de escopo
- Persistir o orçamento de ensemble (cálculo é em tela, como hoje).
- Mudar margens/descontos.
