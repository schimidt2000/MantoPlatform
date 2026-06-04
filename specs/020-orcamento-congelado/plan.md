# Implementation Plan: Orçamento congelado (registro imutável)

**Branch**: `020-orcamento-congelado` | **Date**: 2026-06-04 | **Spec**: [spec.md](./spec.md)

## Summary

Congelar o resultado de cada orçamento: nova coluna `OrcamentoHistory.result_snapshot` (JSON com o
dict de resultado já montado na geração + o multiplicador usado). "Ver" carrega o snapshot na sessão
e reusa a tela de resultado (mensagem/PDF/email do orçamento congelado). "Reabrir" vira "Recalcular
(preços atuais)". Totais salvos nunca são recalculados. Migration à mão.

## Constitution Check
- **I. Reutilizar** ✅ — "Ver" reusa `resultado.html`/PDF/email via o snapshot na sessão.
- **IV. Não quebrar** ✅ — coluna nullable; antigos sem snapshot exibem totais salvos; nada
  recalculado; verificação no app.
- **V. UI/UX** ✅ — "Ver" (congelado) + "Recalcular (preços atuais)" claros.
- **VI. Planejar antes de codar** ✅ — este plano; decisão confirmada.
- **Migration à mão** ✅ (autogenerate quebrado).

## Project Structure

```text
app/models.py                         # OrcamentoHistory.result_snapshot (Text, nullable)
migrations/versions/f2a3b4c5d6e7_*.py # add_column result_snapshot (down_revision e0f1a2b3c4d5)
app/orcamento/routes.py               # _process_quote: +markup_used no quote; grava result_snapshot
                                      #   nova rota /historico/<id>/ver (seta sessão -> resultado)
app/static/js/orcamento.js            # renderHistory: botão "Ver" + "Recalcular (preços atuais)"
app/templates/orcamento/historico.html# link "Ver" + renomear "Reabrir" -> "Recalcular (preços atuais)"
```

## Design Detalhado

### 1. Model + migration
- `OrcamentoHistory.result_snapshot = db.Column(db.Text, nullable=True)`.
- Migration `f2a3b4c5d6e7` (down_revision `e0f1a2b3c4d5`): add_column (nullable). downgrade dropa.

### 2. Congelar na geração (`_process_quote`)
- Calcular `markup_used` = markup aplicado: `cfg["markup"]["show"|"receptivo"]` (normal);
  `cust_mult` se personalizado/multiplicador; `None` se personalizado/valor_final. Incluir no dict
  `session["orcamento_quote"]` (chave `markup_used`).
- Ao criar o `OrcamentoHistory`, gravar `result_snapshot = json.dumps(session["orcamento_quote"])`.

### 3. Ver congelado (nova rota)
- `GET /orcamento/historico/<id>/ver` (mesma permissão `_require_vendas`):
  - `entry = OrcamentoHistory.query.get_or_404(id)`.
  - `quote = json.loads(entry.result_snapshot)` se houver; senão `_legacy_quote(entry)` (monta dict
    a partir dos totais salvos: total_1h/2h/4h, show flags True, client_name/local/data; mensagem
    com aviso "mensagem original não registrada").
  - `session["orcamento_quote"] = quote` e `redirect(orcamento.resultado)` — reusa tela/PDF/email.

### 4. UI do histórico
- `orcamento.js renderHistory`: trocar o botão "Reabrir" por dois: "Ver" (link
  `/orcamento/historico/<id>/ver`) e "Recalcular" (`onclick=restoreFromHistory(id)`); manter "Criar
  evento" e "✕".
- `historico.html`: adicionar link "Ver" (`/orcamento/historico/<id>/ver`) e renomear "Reabrir" para
  "Recalcular (preços atuais)".

### Verificação
- Migration up/down.
- Gerar um orçamento → `result_snapshot` gravado; "Ver" mostra a mesma mensagem/totais.
- Mudar um preço no config (em teste) → "Ver" do antigo mantém os valores; "Recalcular" mostra os
  novos. Totais salvos inalterados.
- Entry antigo (snapshot null) → "Ver" mostra totais salvos sem erro.

### Fora de escopo
- Centralizar valores fixos / unificar cálculo (REVIEW itens 1–3) — próximas features, agora seguras.
