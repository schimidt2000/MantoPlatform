<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: Feature 305 — O BV do orçamento chega ao evento

**Branch**: `305-bv-do-orcamento-no-evento` | **Data**: 2026-10-14 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/305-bv-do-orcamento-no-evento/spec.md`

**Nota**: preenchido pelo `/speckit-plan`. Pesquisa em [research.md](./research.md) (decisões R1–R11, com
o mapa do código na HEAD e as críticas que corrigiram o plano do backlog); modelo em
[data-model.md](./data-model.md); contratos em [contracts/api.md](./contracts/api.md); validação em
[quickstart.md](./quickstart.md).

## Resumo

O BV que a calculadora somou ao preço passa a chegar ao evento **em reais, na proporção da venda**, com
quem recebe e o PIX obrigatórios, pelos dois caminhos em que o evento nasce de um orçamento (criação e
"Vincular e aplicar"). O editor de Acréscimos deixa de estragar o BV (PIX apagado, "despago", % sobre a
venda cheia, vírgula que apaga a linha) e passa a aceitar o BV à mão em R$ ou %. A venda digitada à mão
não cria BV: acende um alerta. O BV a pagar acompanha a venda que muda depois; o pago não muda. O passado
fica como está (corte pelo momento do deploy).

Abordagem: tudo calculado no servidor, em `Decimal`, a partir do orçamento congelado (conta inversa da
calculadora, com a base quantizada; ou `valores_brl`, que a calculadora passa a gravar). Um núcleo puro
por regra (B1 conta, B3 grava, B6 editor, B8 PIX, B9 alerta, B10 venda) em `orcamento_evento_ops.py` e
`comercial_ops.py`; endpoints só validam RBAC e serializam. Sem migration.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: Flask, SQLAlchemy, Alembic (sem migration aqui); React, TanStack Query,
Tailwind CSS, `@manto/ui`, `@manto/api-client`, `@manto/money` (`MoneyInput` no editor)

**Armazenamento**: PostgreSQL; nenhuma coluna nova — `event_acrescimos` já tem `bv_recipient`/`bv_pix`;
chave JSON opcional `valores_brl` em `orcamento_history.form_snapshot.acrescimos[i]`

**Verificação**: `specs/305-bv-do-orcamento-no-evento/verify_305.py` contra `manto_local` (Google
dublado, login pela API, escrita por conexão separada, eventos R&I); `npm run typecheck`; `ruff`; tela
aberta em desktop (app interno); regressão de 273, 267b, 301, 215b, 267c, 267 e os locais 249/251/210

**Plataforma-alvo**: web — app interno (desktop). Portal e público não mudam

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: o alerta (B9) não pode custar uma consulta por evento na listagem — ele só
existe no detalhe, e a consulta ao `EventLog` só roda quando as outras condições já valem e o evento é
anterior ao corte

**Restrições**: nenhuma conta de dinheiro no navegador; campo novo do payload opcional no TS; a B3 roda
depois do `insert_event` do Google e **nunca** levanta exceção; o valor do repasse não se aceita do
cliente; deploy cruzado (bundle antigo recusa criar de orçamento com BV até recarregar)

**Escala/escopo**: 0 tabelas, 0 colunas, 1 chave JSON; 0 rotas novas, 6 contratos alterados; 7 arquivos
de backend, ~9 de frontend; no espelho, 35 orçamentos com BV, 3 eventos ligados (ficam como estão), 5
linhas em `event_acrescimos` (1 BV, sem PIX)

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1 — sem violação.*

| Princípio / seção | Como o plano cumpre |
|---|---|
| I. Reutilizar antes de criar | `snapshot_do_orcamento`, `DURACOES_TABELA`, `_duracao_do_evento`, `sem_valor_de_venda`, `parse_brl`, `_sync_commission_payment`, `_event_bv_total`, `_build_bv_items`, `NF_DIVISOR`; molde de trava de `sumico_ops`/`bloquear_formulario`; `MoneyInput`; `AvisosCard`. Uma conta de proporção só (`bv_que_acompanha`), reusada pela 3b e pela 2b |
| II. Padrões de código | type hints e docstrings pt-BR com o porquê; TS estrito; constantes (`CORTE_ALERTA_BV`, `NF_DIVISOR`); `ruff check` nos tocados |
| III. Camadas / API First | núcleo em `orcamento_evento_ops.py`, `comercial_ops.py`, `event_ops.py`, `quote_ops.py` (puros, sem `request`); `agenda_write`/`agenda_read` só RBAC + serialização; nenhuma rota nova |
| IV. Não quebrar o que funciona | aditivo; pontos compartilhados conferidos na HEAD (215b antes da B10; 267c intocado; 273/301 com a ordem de guardas preservada); verify de regressão no cenário 27 |
| V. UI/UX com feedback | erro no campo (400 com `fields` por linha), aviso pós-salvar (`aviso_bv`, `warnings`), loading nos botões; textos pt-BR |
| VI. Esteira (Nível 1) | specify → clarify (sem perguntas) → plan → checklist → tasks → analyze → implement → converge |
| VII. Living Spec | a spec foi corrigida pela pesquisa antes do código (FR-001 base quantizada; FR-006 lista ignorada em toda criação; FR-015 por id; FR-017 pago congelado; FR-021 gatilho venda ou nota) |
| VIII. Verify antes do núcleo | `verify_305.py` na Foundational, rodado vermelho e guardado |
| IX. Dinheiro BRL | `Decimal`/`ROUND_HALF_UP` no servidor; `@manto/money` na tela; nenhuma conta de dinheiro no navegador |
| X. Mobile-first público | não toca superfície pública |
| XI. Framer Motion | só textos e campos em painéis existentes; nenhuma animação nova |
| XII. Combobox / Maps | não se aplica (campos de texto) |
| XIII. RBAC declarado | matriz por endpoint em `contracts/api.md` e na spec; gates existentes; `docs/01` §4.3 não muda |
| XIV. Config / efeito externo | sem env nova; a B8 na criação recusa **antes** do Google; o verify dubla o Google |
| Stack | sem migration; sem Jinja novo (o gêmeo Jinja ganha só recusa e `flash`); sem segredo |
| Operação e Deploy | sem `startCommand`; deploy à noite; constante do corte gravada no último commit antes do merge; recontagem só leitura em produção antes do push |

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/305-bv-do-orcamento-no-evento/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/api.md
├── checklists/            # requirements.md + os do /speckit-checklist
├── tasks.md               # /speckit-tasks
└── verify_305.py          # escrito antes do núcleo (+ verify_305_primeira_falha.txt)
```

### Código

```text
app/orcamento/quote_ops.py            # B2 valores_brl; bv_que_acompanha; NF_DIVISOR em :364
app/calendar/orcamento_evento_ops.py  # B1 conta; B3 grava; B8 "vai nascer?"; B9 alerta + corte; B4 no vínculo
app/calendar/comercial_ops.py         # B6 editor (id, régua, pago congelado, vírgula, B8, FOR UPDATE, expire); B10
app/calendar/event_ops.py             # B10 em update_event_comercial e _gravar_venda_da_edicao
app/calendar/routes.py                # criação (B3 no _create_event_core, lista ignorada, B8 Jinja); prefill (B5); Jinja comercial (B6/B8/B10)
app/api/agenda_write.py               # POST /events (bv_*, B8); PATCH …/orcamento (bv_*, B8); PUT …/acrescimos (400 por linha, sync); /comercial (aviso_bv)
app/api/agenda_read.py                # _serialize_acrescimos (descricao, bv_pix); venda.orcamento.bv; venda.bv_do_orcamento_pendente
frontend/apps/internal/src/lib/{eventCreate,agenda,eventInline,eventOps,orcamento}.ts
frontend/apps/internal/src/pages/{EventCreatePage,EventEditPage}.tsx
frontend/apps/internal/src/components/EventDetail/{ColecoesComerciaisPanel,ComercialSection}.tsx
frontend/apps/internal/src/components/EventFormBlocks/ValoresBlock.tsx (só se o alerta da edição couber lá)
```

**Decisão de estrutura**: a conta e a gravação do BV do orçamento moram onde já mora "o que o orçamento
diz" (`orcamento_evento_ops.py`, fonte única desde a 273); o editor e a venda que muda, onde já mora a
escrita de acréscimos (`comercial_ops.py`), chamados pelos três escritores da venda. `routes.py` perde
`_criar_acrescimos_do_orcamento`.

## Fases de construção (para o `/speckit-tasks`)

1. **Setup** — recontagem só leitura no espelho (números da pesquisa); usuários e orçamentos fictícios do
   verify; `feature.json` apontando para a pasta.
2. **Foundational (verify primeiro)** — `verify_305.py` com todos os cenários da spec, rodado **vermelho**
   e guardado em `verify_305_primeira_falha.txt`. Esperado vermelho: tudo de B1–B10 (as funções não
   existem); verdes já: RBAC "deve falhar" 19–22, regressão 23–27.
3. **História 1 (P1) — criação** — B1 (conta pura, robusta), B2 (`valores_brl`), `bv_que_acompanha`,
   `NF_DIVISOR`; B3 + B4 na criação (lista ignorada em toda criação; dedução de duração); B5 prefill;
   B8 na criação (API e Jinja). Verify: 1–8, 10–13, 31 (criação), 37, 40, 44, 46.
4. **História 2 (P2) — vínculo** — B3 dentro de `aplicar_valores_do_orcamento` com trava antes da guarda;
   relatório e frase; B8 no vínculo. Verify: 14, 31 (vínculo), 32, 34, 38, 42.
5. **História 3 (P2) — editor** — B6 (id, régua com % a 2 casas, pago congelado, venda sem valor, vírgula
   e tipo, FOR UPDATE, flush+expire), B8 no editor (400 por índice; Jinja rollback+flash), sync no PUT,
   `_serialize_acrescimos`. Verify: 9, 16, 17, 18, 21, 33, 35, 36, 43, 47, 49 (parte 1).
6. **História 4 (P2) — alerta** — B9 com corte e valor em reais; `warnings` na edição completa; frase do
   vínculo em evento com venda. Verify: 15, 45.
7. **História 5 (P3) — venda que muda** — B10 nos três escritores (gatilho venda ou nota; líquido; % pela
   régua; volta de "a definir"); `aviso_bv`; "confira o BV" no vínculo. Verify: 38, 39, 48, 49 (parte 2).
8. **História 6 (P3) — passado** — nada a construir além do corte; verify 25 e 45 (lado "antes").
9. **Frontend** — F1 (Novo evento: quadro, campos fora do RHF, 400 nos campos), F2 (editor: id, descricao
   presente/ausente, `MoneyInput`, vírgula, `maxLength`, erro na linha, "Lançar o BV" por `useEffect`,
   bloqueio se a venda mudou), F3 (painel Orçamento: chip, campos, frase), F4 (alerta nos três lugares;
   `aviso_bv` no VendaPanel); tipos opcionais; invalidações de Planilha e Comissões.
10. **Polimento** — portões (typecheck, ruff, build), tela aberta (quickstart §4), regressão (cenário 27),
    docs 01/02/03/04/05 (com as cinco dívidas e os "textos que mentem", inclusive as docstrings de
    `comercial_ops.py:17-21`, `agenda_write.py:1511-1517` e o comentário `routes.py:857-858`), constante do
    corte no último commit, recontagem em produção só leitura.

## Ordem com os outros itens

- **Na `main` já:** 215b e 267c (mesmos caminhos da venda e da comissão — a 305 os respeita: a recusa da
  215b vem antes da B10; o lote do 267c não toca linha paga).
- **3b (noites 4 e 6) depois:** herda `valores_brl` (passa a escrevê-lo com a regra nova),
  `bv_que_acompanha`, o quadro F1 e a B10 para o PIX à vista; a B1 ganha o ramo pós-3b lá.
- **1b (noite 2) depois:** edita `substituir_acrescimos` (no-op no cancelado; 409 no PUT do cancelado) e
  parte do `amount_brl` que a B3 grava; filtra cancelado na Planilha.
- **1e, 6a, 6b, 2b:** consomem; nada a construir aqui.

## Rastreamento de complexidade

Nenhuma violação a justificar.
