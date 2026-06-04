# Implementation Plan: Orçamento — dropdown ao adicionar + consistência + revisão

**Branch**: `019-orcamento-dropdown-revisao` | **Date**: 2026-06-04 | **Spec**: [spec.md](./spec.md)

## Summary

Três entregas de baixo risco no módulo de orçamento: (1) trocar os botões "+ Ator/Cantor" e
"+ Especial" por dropdowns que escolhem o item antes de adicioná-lo; (2) remover as dicas fixas
"(+R$100)/(+R$20)" exclusivas do cantor (e código morto), padronizando Show/Maquiagem; (3) trocar o
`except Exception: pass` da leitura de config por log. Sem mudança de cálculo. Mais um documento de
revisão ([REVIEW.md](./REVIEW.md)) com os pontos estruturais, sem executá-los.

## Constitution Check
- **I. Reutilizar** ✅ — reaproveita `addPerformer`/`update`; só estende com `choice`.
- **II. Padrões** ✅ — remove `except` silencioso (passa a logar) e código morto.
- **IV. Não quebrar** ✅ — cálculo intacto; mudanças são de UI/texto/log; verificação no app.
- **V. UI/UX** ✅ — dropdown claro; Show/Maquiagem consistentes.
- **VI. Planejar antes de codar** ✅ — este plano; escopo confirmado (sem refactor estrutural agora).

## Project Structure

```text
app/templates/orcamento/index.html   # botões "Adicionar" → dois <select> (subtipos / especiais)
app/static/js/orcamento.js            # addPerformer(type, choice) + addFromDropdown(); remover
                                      #   dicas (+R$100/+R$20) do cantor e a var morta `fantasia`
app/orcamento/settings.py             # load(): except → logging.exception (mantém fallback)
specs/019-orcamento-dropdown-revisao/REVIEW.md   # revisão estrutural (entregável)
```

## Design Detalhado

### 1. Dropdown ao adicionar (index.html + JS)
- `index.html`: o bloco `.add-performer-btns` troca os 2 botões por 2 `<select>`:
  - Ator/Cantor: opção placeholder "+ Ator / Cantor" + `cara_limpa`/`boneco`/`cantor`.
  - Especial: placeholder "+ Especial" + uma opção por especial (`especiais_list` do template).
  - `onchange="addFromDropdown('ator'|'especial', this)"`.
- `orcamento.js`:
  - `addPerformer(type, choice)`: `choice` opcional define `subtipo` (ator) ou `personagem`
    (especial); mantém defaults se ausente (compatível).
  - `addFromDropdown(type, sel)`: se `sel.value`, chama `addPerformer` e reseta `sel.value=''`.

### 2. Consistência do cantor (JS buildCard)
- Trocar `showLbl`/`makeLbl` por `'Show'`/`'Maquiagem'` fixos (sem o "(+R$ ...)").
- Remover a variável morta `fantasia`.
- Não toca em `calcTotals`/`pricing` — cálculo idêntico.

### 3. Falha silenciosa (settings.py)
- `load()`: `except Exception:` passa a `logging.getLogger(__name__).exception(...)` antes do
  fallback para `DEFAULTS` (cumpre o Princípio II; sem quebrar a tela).

### 4. REVIEW.md (entregável, sem executar)
- Documenta: config de preços como JSON em `SiteSetting.pricing_config`; cálculo duplicado
  JS×servidor; valores fixos (BGE +130/+70 em 3 lugares; brinde; adicional noturno); recomendação
  e ordem sugerida para um refactor futuro.

### Verificação
- Render do index (200) com os 2 `<select>` e as opções.
- (Lógico) `addPerformer('ator','cantor')` cria linha cantor; `addFromDropdown` reseta o select.
- buildCard de cantor sem "(+R$"; cálculo de um cenário conhecido permanece igual (sanidade).
- `settings.load()` continua retornando DEFAULTS quando não há config (sem exceção propagada).

### Fora de escopo (vai para REVIEW.md)
- Normalizar a config de preços em tabelas; unificar o cálculo do navegador com o do servidor;
  centralizar os valores fixos.
