<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: Feature 313 — desconto e PIX na calculadora

**Branch**: `313-desconto-e-pix-na-calculadora` | **Data**: 2026-10-21 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/313-desconto-e-pix-na-calculadora/spec.md`

**Nota**: preenchido pelo `/speckit-plan`. A constituição (`.specify/memory/constitution.md`,
v3+) é lida em tempo de execução — o Constitution Check abaixo é o que ela cobra.

## Resumo

A comercial passa a dar o desconto no orçamento — em % ou pelo valor fechado de uma duração —, a proposta diz "de/por"
e o % arredondado, o PIX de 5% vale o maior, o acréscimo em R$ entra uma vez e o BV é calculado sobre tudo (Q7/Q9), e
o evento nasce com o cheio e a venda separados, com o BV encolhendo junto. Abordagem (research R1–R3): **uma função**
para a ordem da conta do pedido (`aplicar_acrescimos` + `preco_na_duracao`, em `quote_ops`), usada pela calculadora,
pelo prefill e pelo evento; uma **marca de regra** (`versao_conta: 2`) com as bases e os cheios no `form_snapshot`, que
os leitores da 305 consultam — orçamento sem a marca segue o caminho de hoje, inalterado; no evento, o cheio vira o
denominador do BV e da dedução de duração, e o final vira a venda.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: Flask, SQLAlchemy; React, TanStack Query, Tailwind CSS, `@manto/ui`,
`@manto/api-client`, `@manto/money`; ReportLab (PDF do orçamento, `app/orcamento/pdf.py`)

**Armazenamento**: PostgreSQL — o desconto e a marca de regra moram nos JSONs `form_snapshot`/`result_snapshot` do
`OrcamentoHistory`; nenhuma coluna nova

**Verificação**: `specs/313-desconto-e-pix-na-calculadora/verify_313.py` contra `manto_local` (login só pela API;
escrita por conexão separada; Google dublado como na 305/312); gabarito de paridade antes do núcleo; regressão
305/307/309/235/190; `cd frontend && npm run typecheck`; tela aberta no Browser pane

**Plataforma-alvo**: web — staff em desktop (calculadora, Novo evento); a cliente lê a mensagem e o PDF no celular

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: o `/calcular` continua uma requisição por pausa de digitação (debounce de 400 ms da
calculadora, `OrcamentoCalculadoraPage.tsx:45`); a função da ordem da conta é aritmética pura, sem consulta nova

**Restrições**: sem desconto, preço, mensagem e PDF idênticos aos de hoje (paridade) salvo as exceções da Q7 listadas;
orçamento salvo nunca muda de preço (020); chaves novas opcionais nos dois sentidos do deploy; PDF numa página; campo
de valor pelo `MoneyInput` de `@manto/money`

**Escala/escopo**: ~6 arquivos de backend (`quote_ops.py`, `pdf.py`, `produtos.py` só na chamada, `orcamento_read.py`,
`orcamento_evento_ops.py`, `routes.py` no prefill, `app/educamanto/quote_ops.py`), ~9 de frontend (calculadora,
orçamento gerado, histórico, `AcrescimosEditor`, Novo evento, `BvDoOrcamentoBlock`, `ValoresBlock`, EducaManto,
`lib/orcamento.ts`, `lib/eventCreate.ts`, `lib/desconto.ts` novo); 0 endpoints novos; 0 tabelas

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1.*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | `bv_que_acompanha` (305) sem mudança; `AVISTA_FATOR`/`NF_DIVISOR` do EducaManto; `MemoriaDeCalculo` com os tipos de linha que existem; `sale_value_gross`/`sale_value` do evento; `MoneyInput`; o selo do `ValoresBlock`. A função nova da ordem da conta **substitui** quatro réguas para orçamento novo (R1) |
| II. Padrões de código | type hints e docstrings nas funções novas; TS estrito com as chaves novas opcionais; constantes (`PIX_PCT_PADRAO`, `VERSAO_CONTA`); `ruff check` nos tocados |
| III. Camadas / API First | a conta no `quote_ops`/`orcamento_evento_ops` (puros); `orcamento_write`/`orcamento_read` só validam e serializam; nenhum endpoint novo |
| IV. Não quebrar o que funciona | gabarito de paridade sobre os orçamentos reais antes do núcleo; marca de regra para o salvo; regressão 305/307/309/235/190; consumidores do `quote` e do snapshot conferidos (reconferência §1–§3) |
| V. UI/UX com feedback | erro no campo do desconto; resultado esmaecido "recalculando…" (R9); textos em pt-BR do dono (Q3) |
| VI. Esteira (Nível 1) | esteira completa; artefatos em `specs/313-…/` |
| VII. Living Spec | spec antes do código; Session 2026-10-21 com as leituras contestáveis |
| VIII. Verify antes do núcleo | gabarito + `verify_313.py` na Foundational, vermelho contra a `main` (primeira saída guardada) |
| IX. Dinheiro BRL | exibição por `formatBRL`; o "fechar por R$" com `MoneyInput`; no backend, o núcleo do orçamento continua em float (justificado abaixo) e o BV em Decimal HALF_UP (305) |
| X. Mobile-first público | sem tela pública; a mensagem e o PDF conferidos no celular (quickstart §3) |
| XI. Framer Motion | nada novo além do que a calculadora já tem |
| XII. Combobox / Maps | o seletor de duração tem ≤ 5 itens (select simples) |
| XIII. RBAC declarado | nenhum gate muda; cenário 15 do verify com papéis que DEVEM falhar; linha em `docs/01` §4.3 |
| XIV. Config / efeito externo | nenhuma escrita externa nova; o verify dubla o Google como a 305 |
| Stack | sem migration; sem Jinja novo (o gêmeo Jinja lê o mesmo prefill e ignora as chaves novas) |
| Operação e Deploy | não toca `startCommand`; deploy à noite (a calculadora sangra primeiro no 502) |

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/313-desconto-e-pix-na-calculadora/
├── spec.md
├── plan.md                 # este arquivo
├── research.md             # R1–R12
├── data-model.md           # as chaves novas dos snapshots
├── quickstart.md
├── contracts/api.md
├── pesquisa/reconferencia-2026-10-21.md
├── checklists/
├── tasks.md                # /speckit-tasks
├── gabarito_paridade.py    # só leitura — antes do núcleo
└── verify_313.py           # Princípio VIII — escrito antes do núcleo
```

### Código (caminhos reais)

```text
app/orcamento/quote_ops.py          # aplicar_acrescimos, preco_na_duracao, desconto, PIX, BV, mensagem, quote/snapshot
app/orcamento/pdf.py                # "R$ Y (de R$ X)", PIX de pix_*, linha do desconto
app/orcamento/produtos.py           # sem mudança de regra (legado segue usando total_na_duracao)
app/api/orcamento_read.py           # desconto_pct na linha do histórico
app/api/orcamento_write.py          # (validação vem do quote_ops — nada a mudar além do que o 400 já faz)
app/calendar/orcamento_evento_ops.py  # _bruto_da_duracao / _total_da_duracao; v2 pela R1; 273 com bruto ≠ venda
app/calendar/routes.py              # _build_orcamento_prefill: bruto_*, desconto_pct, extra_por_horas
app/educamanto/quote_ops.py         # pop das chaves de desconto
frontend/apps/internal/src/lib/{orcamento.ts,eventCreate.ts,desconto.ts}
frontend/apps/internal/src/pages/{OrcamentoCalculadoraPage,OrcamentoResultadoPage,OrcamentoHistoricoPage,EventCreatePage,EducaMantoCalculadoraPage}.tsx
frontend/apps/internal/src/components/orcamento/AcrescimosEditor.tsx
frontend/apps/internal/src/components/EventFormBlocks/{BvDoOrcamentoBlock,ValoresBlock}.tsx
```

**Decisão de estrutura**: a ordem da conta mora no `quote_ops` (o dono da conta), e o evento a chama em vez de
desfazer o total; nenhuma camada nova.

## Fases de construção

1. **Setup** — ponteiro, ambiente do verify (`env313.ps1` no scratchpad), conferir que o `manto_local` tem os
   orçamentos (contagem).
2. **Foundational** — `gabarito_paridade.py` rodado na `c074657b` (gravado); `verify_313.py` inteiro (cenários 1–16)
   rodado **vermelho** contra a `main`, primeira saída guardada (`verify_313_primeira_falha.txt`).
3. **H3 — a ordem da conta (Q7/Q9)** — `aplicar_acrescimos`, `preco_na_duracao`, a extra pela R1, `versao_conta`,
   `bases`, `brutos` no snapshot; a memória; a linha do BV nascendo em % (editor). Verdes: 1, 8, 9, 10.
4. **H1 — desconto** — entrada %/valor, validação, `bruto_*`/`total_*`, `desconto_*`, `bv_*`, memória, snapshot.
   Verdes: + 2, 3, 4.
5. **H2 — PIX e proposta** — `pix_*` pela constante, mensagem (três formatos) e PDF. Verdes: + 5, 6, 7.
6. **H4 — evento** — prefill, `orcamento_evento_ops` (cheio × final), 273. Verdes: + 11, 12, 13, 14, 15.
7. **Telas** — calculadora (bloco Desconto, card Resultado, ajuda), orçamento gerado, histórico, Novo evento,
   `BvDoOrcamentoBlock`, `ValoresBlock`, EducaManto. Typecheck.
8. **Polimento** — regressão (16), rodada inteira duas vezes, tela aberta, docs 01–05.

## Deploy e rollback

Um push só, à noite (a calculadora sangra primeiro no 502), sem migration e sem script no Shell do Render. Sonda: um
endpoint `/api/` com JSON e um orçamento calculado em produção logo depois. **Rollback** = `git revert` do merge +
push: o código antigo ignora as chaves novas; os orçamentos salvos nesse meio-tempo (`versao_conta: 2`) seguem com
as colunas no valor final e, se virarem evento depois do revert, o BV sai pela conta inversa antiga (pode diferir
nos orçamentos com BV e outro acréscimo — os mesmos da exceção da Q7) e o cheio do evento igual à venda. Nenhum dado
se perde; o revert não precisa de script.

## Rastreamento de complexidade

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| Núcleo do orçamento em float (IX pede Decimal no backend) | a paridade byte a byte com os 2.710 orçamentos salvos e com a mensagem de hoje exige a mesma aritmética (`round(x, 2)` de float); o BV, que vai a dinheiro gravado, já é Decimal (305) | converter o núcleo para Decimal mudaria centavos de orçamentos sem desconto — exatamente o que a SC-002 proíbe; a conversão é dívida própria (`docs/05`) |
| Duas leituras do orçamento no evento (`versao_conta` ausente × 2) | o salvo tem de sair como foi cotado (020) e o novo pela regra do dono | uma régua só mudaria o BV e a venda de orçamentos antigos que viram evento depois (o `verify_305` cen_04 quebraria) |
