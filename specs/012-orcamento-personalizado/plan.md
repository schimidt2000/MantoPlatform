# Implementation Plan: Orçamento personalizado (valor final ou multiplicador)

**Branch**: `012-orcamento-personalizado` | **Date**: 2026-06-01 | **Spec**: [spec.md](./spec.md)

## Summary

Adicionar um painel opt-in "Personalizar valores" no mesmo formulário de orçamento. Quando ativo,
o vendedor escolhe um critério — **valor final** (digita o total por duração) ou **multiplicador**
(aplica um multiplicador por duração sobre o cachê-base). O resultado é usado como VALOR TOTAL,
**sem somar nenhum extra depois** (transporte, NF, brinde, noturno, técnico, maquiador, acréscimo).
Todo o resto (mensagem WhatsApp, PDF, email, seleção de durações da feature 003, histórico) é
reaproveitado. Sem mudança de banco.

## Technical Context

**Language/Version**: Python 3.11+ (Flask, SQLAlchemy, Jinja2), JS vanilla.
**Storage**: nenhuma migration. O histórico já guarda um `form_snapshot` JSON livre — só
adicionamos chaves de personalização nesse snapshot.
**Constraints**: modo desligado = comportamento idêntico ao atual (zero regressão); personalizado
não soma extras; ajuste por duração; mesma permissão (COMERCIAL/SUPERADMIN).
**Scale/Scope**: 1 painel no template + estado/lógica no JS + um fork em `_process_quote` + exibição
no resultado. Sem novas rotas, sem novos modelos.

## Constitution Check

- **I. Reutilizar antes de criar** ✅ — reaproveita formulário, motor de mensagem/PDF/histórico e a
  seleção de durações (feature 003). O fork acontece num único ponto do cálculo.
- **II. Padrões Python** ✅ — helper pequeno de parsing; fork legível com early-return.
- **III. Camadas** ✅ — cálculo no fluxo de `_process_quote`; exibição no template; sem lógica nova
  espalhada.
- **IV. Não quebrar** ✅ — caminho automático intacto sob `if not personalizado`; sem migration;
  branch isolado; verificação no app real.
- **V. UI/UX (pt-BR)** ✅ — painel discreto, opt-in, com leitura do cachê-base para transparência.
- **VI. Planejar antes de codar** ✅ — este plano; 3 decisões delicadas confirmadas com o usuário.

## Decisões confirmadas (AskUserQuestion)

1. **Mesmo formulário + painel opt-in** (não tela nova).
2. **Valor/multiplicador = TOTAL final**; nada é somado depois (transporte/NF/extras off no modo).
3. **Por duração** (1h/2h/4h independentes).

## Project Structure

```text
app/
├── orcamento/routes.py             # _process_quote: fork personalizado (sem extras);
│                                   #   captura cache_base; salva personalização no snapshot/quote
├── static/js/orcamento.js          # estado + painel; calcTotals com fork; submit hidden fields;
│                                   #   _applySnapshot restaura personalização
├── templates/orcamento/index.html  # painel "Personalizar valores" (toggle + critério + 3 campos)
└── templates/orcamento/resultado.html  # nota "Orçamento personalizado" (critério, base, mult)
```

## Design Detalhado

### 1. Cachê-base (ponto do fork)
O cachê-base = soma dos cachês de artistas + coordenadores + show customizado, **antes** do markup.
- **JS**: hoje `calcTotals()` monta `cache[]` e depois aplica markup/extras. Extrair `cache[]` como
  base; expor também numa função `cacheBase()` reutilizável (ou capturar dentro de `calcTotals`).
- **Server**: em `_process_quote`, `cache_totals` já é esse valor logo após somar coordenador e show
  customizado (antes de `aplicar_markup`). Capturar `cache_base = list(cache_totals)` nesse ponto.

### 2. Estado e UI (JS + index.html)
Novo painel (colapsável, off por padrão), abaixo de "Incluir no orçamento":
- checkbox `personalizado_ativo` → liga/desliga.
- radios `personalizado_criterio`: `valor_final` | `multiplicador`.
- 3 campos por duração:
  - **multiplicador**: `number` `×`, pré-preenchidos com o markup vigente (`show`/`receptivo`) ao
    ativar; mostra leitura "Base (cachê): 1h X · 2h Y · 4h Z".
  - **valor_final**: `number` com prefixo `R$`, vazios.
- Estado JS: `personalizadoAtivo`, `personalizadoCriterio`, `custMult=[…]`, `custValor=[…]`.
- `calcTotals()`: se `personalizadoAtivo`, calcula `base=cacheBase()`; então
  `multiplicador → base[i]*custMult[i]`; `valor_final → custValor[i]`; **retorna sem extras**.
- `updateDebugPanel()`: no modo personalizado, renderiza até "Subtotal Cachê" e então uma linha
  "Personalizado (critério)" com o total — early-return (não mostra markup/extras).
- Hidden fields no submit: `personalizado_ativo`, `personalizado_criterio`,
  `cust_mult_1h/2h/4h`, `cust_valor_1h/2h/4h`.
- Validação no submit: se ativo, cada duração **incluída** (feature 003) deve ter total > 0; senão
  bloqueia com mensagem (`.orc-field-error`), igual ao padrão atual.

### 3. Fork no servidor (`_process_quote`)
```text
cache_base = list(cache_totals)              # após coord + show custom
personalizado = "personalizado_ativo" in form
if personalizado:
    if criterio == "multiplicador":
        totals = [round(cache_base[i] * mult[i], 2) for i in range(3)]
    else:  # valor_final
        totals = [valor[i] for i in range(3)]
    transport_breakdown = None; transport_total = 0; total_custom = None
else:
    totals = aplicar_markup(...); <todos os extras como hoje>
```
- Parsing tolerante (`_parse_num`): vírgula→ponto, vazio/≤0 inválido. Se personalizado e algum valor
  exigido for inválido → `flash(...)` + redirect para o form (fallback; o cliente já bloqueia).
- A montagem da mensagem não muda: com `transport_total = 0`, `_dur_block` mostra só "VALOR TOTAL".
- PIX à vista (5%) já deriva de `totals` → ok.

### 4. Resultado (transparência — FR-012)
`session["orcamento_quote"]` ganha: `personalizado` (bool), `personalizado_criterio`,
`cache_base` (lista), `custom_mult` (lista). Em `resultado.html`, se `personalizado`, um painel
discreto: critério; para `multiplicador`, "base × mult = total" por duração.

### 5. Histórico (reabrir)
`snapshot` ganha: `personalizado_ativo`, `personalizado_criterio`, `cust_mult_*`, `cust_valor_*`.
`_applySnapshot` (JS) restaura o painel e os campos. PDF/email usam o `quote` da sessão → sem mudança.

### Verificação (app real)
- Valor final: 4h = 2400 digitado → mensagem/PDF/PIX batem (2400 e 2280 no PIX).
- Multiplicador: trocar mult de 4h → total = cache_base[4h] × mult; resultado mostra a conta.
- Transporte/NF/acréscimo ligados + personalizado → **não** somam.
- Modo desligado → resultado idêntico ao atual (sanidade de não-regressão).
- Reabrir do histórico restaura o painel.

### Fora de escopo
- Duração personalizada (horas fora de 1/2/4) no modo personalizado.
- Máscara BRL com pontos/milhar nos inputs (usar `number` com prefixo); pode evoluir depois.
- Personalizar por item/artista (é por duração no total).
