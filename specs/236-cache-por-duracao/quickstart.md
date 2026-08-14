# Quickstart de validação — Feature 236: Cachê sugerido pela duração real do evento

Tudo contra o espelho `manto_local` (dump fresco de 14/08 já contém os casos-gabarito).

## 1. Régua (verify_236.py, sem UI)

- `_compute_performer_caches(snap_1806, horas_extra=6)` → Green (make): **520**; Space: **500**;
  Coordenador: **575** (tabelas vigentes; noturno 22h incluso). Maquiador permanece 500.
- Paridade 1–4h: com `horas_extra=None`, saída idêntica byte-a-byte à atual para os snapshots
  1806 e 1573 (mascotes: boneco show 2h + noturno = 400 = teto real do evento 1205).
- `horas_extra=5` no orçamento 1806 ≠ valores de 1h (o antigo fallback) em 100% dos papéis.

## 2. Criação de evento (API, app real)

- Criar evento do orçamento 1806 com `duracao=6`: papéis nascem com `cache_value = cache_cap` =
  520/520/520/520/500/500 (+ coordenador 575) — nunca os valores de 1h.
- Criar com `duracao=2`: valores da tabela de 2h (paridade com hoje).
- `duracao=0` ou "abc": 400 com erro de campo, evento não criado.
- Criar evento SEM orçamento: papéis sem cap, como hoje.

## 3. Tela de criação

- Com orçamento vinculado de `duracao_custom=5`: o input "Outra (h)" já vem com 5 e mostra o
  preço de referência; escolher "2h" limpa o input; digitar 6 desmarca os botões.

## 4. Casting

- Num papel com cap 520: lançar 500 → aviso "abaixo do sugerido"; lançar 600 como não-superadmin
  → rebaixa para 520 com o aviso atual; lançar 520 → sem avisos.
- Papel adicionado à mão (sem cap): nenhum aviso novo.

## 5. Regressão

- `npx tsc --noEmit` limpo em `apps/internal`.
- Calculadora de orçamento: totais 1–4h e custom inalterados (FR-007) — conferir orçamento 1573
  recalculado idêntico.
