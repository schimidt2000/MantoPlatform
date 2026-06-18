# Quickstart — Verificação manual da feature 059

Validar que **todos** os campos de R$ usam a máscara padrão, sem regressão de cálculo nem de
gravação. **Rodar contra a cópia local `manto_local` (Postgres)** — não SQLite vazio:

```powershell
.\scripts\db\run-local.ps1   # sobe o app com DATABASE_URL -> manto_local
```

## Passo 1 — Consistência de digitação (US1, FR-001/FR-002)

1. Abrir um campo já padronizado (ex.: cachê em um evento) e um recém-convertido (ex.: custo de
   item no pacote Educamanto). Digitar `150000` nos dois.
   - ✅ Ambos mostram `1.500,00`, preenchendo da direita para a esquerda.
2. Apagar tudo no campo.
   - ✅ Fica vazio (sem `0,00`).

## Passo 2 — Campos convertidos salvam certo (US2, FR-005/FR-008)

1. **Educamanto**: editar um pacote, ajustar `ensemble_1s` e um `item_cost_*`, salvar, reabrir.
   - ✅ Campos com máscara; valores gravados corretos; reabrir mostra `xxx,xx`.
2. **Orçamento → Configurações**: alterar um preço `ator_*`/`cantor_base_*`, salvar, reabrir.
   - ✅ Máscara aplicada; preço gravado correto.
3. **Orçamento → Histórico**: usar filtros `min_val`/`max_val` com máscara.
   - ✅ Filtro funciona com o valor mascarado.
4. **Registro existente**: abrir um pacote/preço **sem alterar** e salvar.
   - ✅ Valor permanece idêntico (FR-008).

## Passo 3 — Calculadoras ao vivo NÃO regridem (US2, Princípio IV)

1. **Orçamento (index)**: digitar `acrescimo_valor` (valor fixo) e `cust_valor_1h|2h|4h`;
   conferir os totais calculados ao vivo.
   - ✅ Os totais batem com o valor digitado (ex.: acréscimo `R$ 500,00` soma 500, não 5).
2. **Cadastro de evento**: usar o desconto em **valor** (`desc-val`).
   - ✅ O total reflete o desconto correto em R$.

## Passo 4 — Campos não-monetários inalterados (US3, FR-006)

1. Conferir comissão (%), nº de parcelas, altura (cm), markup/margens.
   - ✅ Continuam como campos numéricos comuns; **sem** máscara de R$.

## Checklist de qualidade (Portões da constituição)

- [ ] Sem migration (modelo inalterado).
- [ ] `ruff check` sem erros novos nos arquivos tocados (comparar com `git stash`).
- [ ] Verificado contra `manto_local` (Postgres), não SQLite.
- [ ] Nenhum `type="number"` remanescente para campo de R$; nenhum `float()/int()` direto em R$.
- [ ] Calculadoras do Orçamento e desconto do evento sem regressão.
