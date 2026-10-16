<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: Feature 306 — Dinheiro do cancelamento

**Branch**: `306-dinheiro-do-cancelamento` | **Data**: 2026-10-15 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/306-dinheiro-do-cancelamento/spec.md`. A spec tem as Clarifications até o clarify de 15/10, a FR-001 a FR-074, o RBAC e — com a Living Spec deste plano já aplicada (Session 2026-10-15 `/speckit-plan` nas Clarifications) — **59** cenários (entraram 37b e 38c, numerados).

**Nota**: preenchido pelo `/speckit-plan`.
- **Base**: `main` em `6356b80`, já com 303, 215b, 267c, 305 e 307 em produção (rebase de 16/10; o plan nasceu sobre `d855d1a`). A 307 mexeu em `orcamento_evento_ops.py`, `orcamento/quote_ops.py` e `calendar/routes.py` (a partir de `:2835`) só deslocando linhas: as citações foram reconferidas contra `6356b80`. Nenhuma migration nova; a cabeça segue `a7c3e91f4d28`.
- **Citações**: toda `arquivo:linha` deste plano é do HEAD, conferida com `git show HEAD:`. As do plano do backlog são de `f6ad283` e as da pesquisa da 303 são de `14cec75` (`pesquisa/LEIA-ME.md:3-5`); nenhuma delas foi usada sem reconferir.
- **Nomes**: a **tabela única de nomes** é a do [data-model.md](./data-model.md) §6 (constantes, funções e listas que a 1c, a 2a, a 2b e a 6a reusam). Este plano e a research usam os nomes dela e não definem outros.
- **Artefatos irmãos**:
  - [research.md](./research.md): as decisões (a)–(h) com as alternativas descartadas, e o mapa citação → HEAD de cada área;
  - [data-model.md](./data-model.md): as três tabelas e a tabela única de nomes (§6);
  - [contracts/api.md](./contracts/api.md);
  - [quickstart.md](./quickstart.md): a validação.

## Resumo

**O que a feature entrega.** Cancelar passa a ter **uma regra de dinheiro só**, para o avulso, o marcado pela 303, a venda inteira de vários dias e o corte de um dia.
- **O ato**:
  - o Superadmin escolhe Tudo, Parte ou Nada; nada vem escolhido;
  - a devolução nasce como Gasto Extra aprovado e travado;
  - o **retido** (pago − devolvido) move na mesma proporção a comissão (cheia × retido ÷ venda, com teto na cheia) e o BV (BV cheio × retido ÷ venda, com teto no cheio).
- **O que já foi pago**: comissão ou BV pagos (ou no banco) nunca são reescritos. A diferença nasce como linha de ajuste no **primeiro repasse aberto** de quem recebeu.
- **A DRE e o comercial**:
  - as duas DREs lançam no **mês do cancelamento** o retido, o imposto informado, o BV do retido e a comissão do retido. O exemplo-padrão dá +342, não −600;
  - o retido conta como venda do vendedor congelado.
- **Correções depois do ato**: comprovante, devolução, venda, taxa, cortesia, vendedor, acréscimos, parcelas, notas e reembolsos são só do Superadmin real. As que mexem em dinheiro recongelam na mesma transação.
- **Vários dias**: a venda cancela inteira pelo principal ou um dia só, sem desagrupar. Quando o dia cortado é o 1º, a venda passa ao dia vivo mais cedo.
- **Ensaio, avisos e elenco**:
  - o ensaio cai junto;
  - o elenco recebe e-mail; a equipe de Ensaio e o Casting recebem sino, um por ato;
  - cachê pago recusa o cancelamento;
  - a multa ao elenco vira Gasto Extra, uma por escalação.

**Abordagem.**
- **Congelamento** em três tabelas novas (`event_cancellations`, `event_cancellation_bvs`, `event_cancellation_elenco`). Pago e devolvido são lidos ao vivo, somando os ids do grupo por **consulta** (`cancel_ops.ids_do_grupo`, os mesmos de T1). Um **resumo único** (FR-005), em `Decimal` e em lote, é lido por todas as telas; nenhuma refaz a conta.
- **Núcleo puro**, com os endpoints só fazendo RBAC e serialização:
  - `cancel_ops.py`: ato, prévia por `simular=True`, resumo, alterar devolução, `reaplicar_cancelado`, multas, laço do grupo, `ao_cancelar` (ponto de extensão da 2a), Google depois do commit;
  - `comissoes_ops.py`: comissão cheia em **duas camadas** (`_base_da_comissao`, o corpo de hoje, intocado; `comissao_cheia_do_evento`, com o portão do beneficiário), reconciliação idempotente por beneficiário, `primeiro_repasse_aberto`, predicados únicos;
  - `group_ops.py`: `passar_venda`, `dias_vivos` e as listas `CAMPOS_DA_PASSAGEM`/`TABELAS_DA_PASSAGEM`;
  - `dre_ops.py`: módulo novo;
  - `gastos_ops.py`: a trava;
  - `comercial_ops.py`: acréscimos gravados no lugar, sobre a montagem da 305 extraída e fatiada.
- **Travas sempre evento → dependentes** (T1–T6, seção própria abaixo), com `populate_existing` e ordem de id. Fora da 306, os oito ajustes da seção Travas ("Fora da 306", a lista única, que a R24 repete) impedem que algum fluxo cruze essa ordem.
- **Recusas com código**: os 18 códigos 409 da 306 (com o `valor_mudou`, que o 409 do BV da 305 ganha) são constantes em `app/constants.py` e uma união em TypeScript (`CodigoRecusaCancelamento`, em `lib/eventOps.ts`).
- **Reuso das entregas anteriores**:
  - da 305: `quote_ops.bv_que_acompanha` (conta única de proporção), `estado_da_venda` + `acompanhar_bv_da_venda` (corte de dia, uma vez), `travar_evento`, a validação de `substituir_acrescimos`, `erros_do_bv`, `valor_visto`, `AcrescimosRecusados`;
  - da 303: `desmarcar`, o dublê do Google, a guarda de ambiente, `_exigir_ambiente_liberado`;
  - da 267c: o item da Planilha partido em aberto × `:pago` e o desfazer.
- **Sem env nova.** A migration é só `create_table`.

**Decisões que a spec deixou ao plan** (o detalhe, as citações e as alternativas estão em research.md):

| # | Ponto da spec | Decisão |
|---|---|---|
| (a) | Leitura 10: como fica registrado o valor pago do BV do retido | Coluna `event_cancellation_bvs.paid_amount Numeric(12,2) NULL`. No ato, recebe `amount_brl` quando o BV estava pago ou no banco. Depois do ato, uma função única `cancel_ops.marcar_status_do_bv(acrescimo_id, status, *, valor_esperado, actor_name)` serve as duas portas, a API (`financeiro_write.py:163-194`) e o Jinja (`financeiro/routes.py:1190-1197`). Ela trava o evento → o acréscimo, compara `valor_esperado` com `bv_da_planilha` e grava ou limpa `paid_amount`. `reaplicar_cancelado` nunca toca `paid_amount`. Desfazer o pago devolve o BV ao proporcional |
| (b) | Leitura 11: desfazer o "pago" de linha do cancelado (267c) | Nenhum ramo novo em `liquidar_item_de_comissao`. A guarda `if event.is_cancelled: return` em `_sync` impede o resync de zerar a linha; a Σ não muda; a próxima reconciliação absorve. O desfazer passa a travar os eventos antes das linhas. **Achado** na FR-057: no principal vivo depois do corte, desfazer a base daria desconto em dobro. Regra nova em `_sync`: com ajuste vivo e base de volta a `a_pagar`, sincroniza por `reconciliar` com alvo = cheia. Cenário novo, numerado, **38c** |
| (c) | Comprovante num dia de grupo cancelado (`satelite`/`dia`) | Nas três portas de comprovante: 404 → 403 → T1 do grupo → 409 `cancelado` a quem não é Superadmin, **antes** de `_add_payment_record`, que salva o arquivo → grava → `flush` → `reaplicar_por_dinheiro(event)`. Esta última só refaz o principal `venda` cancelado. Principal vivo (`dia`) não refaz nada; `legado` e `virtual` passam só pela guarda de pago < devolvido. **No POST**, um 409 que nasça depois de `_add_payment_record` (`tente_de_novo`, `grupo_mudou`) faz rollback e remove o arquivo novo; o PATCH não recebe arquivo (`calendar/routes.py:1159-1164`) |
| (d) | BV novo ou removido no `PUT …/acrescimos` do cancelado | `alterar_acrescimos_do_cancelado` reaproveita a montagem e a validação da 305, extraída de `comercial_ops.py:216-404` para `_montar_acrescimos` e **fatiada** em cinco passos (H4), e grava no lugar pelo id. BV novo nasce com a linha congelada. BV não pago removido apaga o acréscimo **e** a linha congelada. Depois: `expire` → `reaplicar_cancelado`, com BV = Σ `original_amount` das linhas vivas |
| (e) | "Alterar devolução" no dia cortado (clarify 15/10 = A) | Antes da trava, só 400 para `devolucao_total` ausente ou não numérico. Depois de T1 → T2 → T4 → T5 (T4 só quando reconcilia: no `venda` e no `dia` com o principal cancelado inteiro; os beneficiários se conhecem depois de T2), decide pelo regime, na ordem dos contracts §3: 409 `nao_cancelado` → 409 `regime_sem_retido` → 400 `fields` (`imposto_retido` no `dia`, no `legado` ou sem nota; acima do pago no `venda`/`legado`) → 409 `abaixo_do_piso` → 409 `acima_do_teto` (só no `dia`). Piso = devoluções do dia pagas ou no banco. Teto = pago do grupo − devoluções aprovadas dos outros dias. Mesmo `_aplicar_novo_total` do regime `venda`. Enquanto o principal vive, não reconcilia (clarify). **Exceção derivada da D28** ("Acompanham", nas Clarifications da spec, sessão de 22 a 30/09), não da resposta do clarify, que vale para o grupo vivo: com o principal já cancelado inteiro (regime `venda`), a devolução do dia é devolvido daquela venda (FR-004), e roda também `reaplicar_cancelado(principal)` (T4). É o ponto 6 da Living Spec, com variante no 39 |
| (f) | Citações que sumiram ou mudaram e mudam uma FR | Ver a tabela "Portas e pontos" em research.md. Inclui a porta não citada `PATCH /api/events/<id>` (`_gravar_venda_da_edicao`, `event_ops.py:846-879`), que recebe 409 `cancelado` quando um campo de venda chega diferente do gravado |
| (g) | Concorrência | T1–T6 e a ordem por operação (seção "Travas") |
| (h) | P-24 a P-29, FR-062 e o modelo | P-24 e P-25 confirmadas (`cancel_ops.py:65-72`). P-26: Google depois do commit, com a trava lida a cada chamada. P-27: recusa no despachante Jinja. P-28: a tela Jinja do cancelado fica com comissão 0 e vira dívida. P-29: prefixo `NOTA_COMISSAO_PROPRIA_DO_DIA`. FR-062: `cancel_ops.ao_cancelar` roda em **todo** cancelamento; avulso recebe `("todos", None)`; corte de dia que não é o principal recebe `("so_este_dia", None)`. Modelo: `commission_rate Numeric(6,3)`; `commission_cost Numeric(12,2)`, pela mesma régua de custo da comissão; `sale_handed_over`; `special_expense_id` na linha do elenco (uma multa por escalação); `day_event_id` CASCADE e NOT NULL; FKs de vendedor sem `ondelete`; `foreign_keys=` em toda relação. **Não existe `NOTA_CICLO_CANCELAMENTO`**: a nota da linha de ajuste começa pelo motivo de `MOTIVOS_AJUSTE_COMISSAO`, e o ciclo vem de `payable_from`. A marca `NOTA_CICLO_VALOR_TARDIO` (`constants.py:466`) existe porque o `_sync` regrava a linha base; o `_sync` nunca regrava ajuste (ignora `original_id` e evento cancelado), então uma segunda marca seria uma segunda fonte |

**Living Spec antes do `/speckit-tasks`** (Princípio VII). Os 19 pontos abaixo acrescentam comportamento, ou fecham o que a spec deixou ao plan, e entram **primeiro** na spec:
1. **FR-039/FR-040 e leitura 10**: `paid_amount`. BV pago, no ato ou depois, e depois desfeito volta ao proporcional. Variante 16/17-`paid_amount`.
2. **FR-057**: a regra de `_sync` com ajuste vivo e base de volta a `a_pagar` (sincroniza por `reconciliar` com alvo = cheia). Entra o cenário numerado **38c**: corte com a base paga, desfazer, sync, Σ = 75.
3. **FR-047/FR-048**: a porta `PATCH /api/events/<id>` no cancelado dá 409 `cancelado` para **todos** os papéis quando `sale_value`, `sale_value_gross`, `commission_rate`, `seller_id`, `is_cortesia_permuta` ou `with_invoice` chega diferente do gravado, com a frase "corrija pela aba Comercial". "Editar tudo" some no cancelado.
4. **FR-018/FR-049**: comprovante num dia de grupo refaz o cancelamento `venda` do principal; com o principal vivo (`dia`), nada se refaz; pago do grupo abaixo do devolvido → 409 `pago_abaixo_do_devolvido`. Entram o cenário numerado **37b** (comprovante de 200 num satélite → retido do principal refeito) e a variante 38-comprovante.
5. **FR-040 (devolução na Planilha)**: `valor_esperado` **adotado** no set-status do item `expense` quando o gasto é devolução de cancelado. O bundle (`PagamentoItemViews`) passa a mandar `valor_esperado: item.amount` para `bv` **e** `expense`; divergente → 409 `valor_mudou` "A devolução mudou para R$ X…"; sem o campo, comportamento de hoje.
6. **FR-017 + FR-004 (D28, "Acompanham", nas Clarifications da spec, sessão de 22 a 30/09)**: o "Alterar devolução" do dia cortado **depois** de o principal ter sido cancelado inteiro refaz o retido e a comissão do principal (`reaplicar_cancelado`). O "não mexe em comissão" do clarify de 15/10 vale enquanto o principal vive. Variante no 39.
7. **Entidades** (seção Entidades da spec): as colunas que a spec não lista — `commission_cost` (custo de cachês da cheia EducaManto no ato, pela régua da comissão), `sale_handed_over` (o antigo 1º dia que passou a venda; dá o `venda_passou_para`) e `special_expense_id` (a multa da linha do elenco), além do `paid_amount` do ponto 1. O dia da linha do elenco (`day_event_id`) sai em cascata com o dia, que não se exclui.
8. **RBAC** (seção RBAC da spec): entram três portas que faltam, todas com 409 novo — `PATCH /api/events/<id>` (ponto 3), `DELETE /api/events/<leader>/grupo/satelites/<sat>` (409 `cancelado`; hoje viraria 500) e `POST /api/financeiro/pagamentos/set-status` (409 `bv_nao_esta_a_pagar`, e 409 `valor_mudou` para BV ou devolução de cancelado com `valor_esperado` divergente; o 409 do BV, da 305, ganha o código e a mensagem não muda).
9. **Jinja** (FR-047, P-27): o despachante `event_detail` recusa `update_comercial`, `update_sale`, os três de comprovante e os três de reembolso **para todos os papéis, inclusive o Superadmin**, porque o Jinja não recongela (vai além da FR-047, que abre ao Superadmin pela tela nova). `set_commission_status` recusa mexer em linha de evento cancelado; `set_payment_status` trava o evento antes de mudar o status de uma devolução de cancelado.
10. **Códigos 409** (18): `cancelado`, `ja_cancelado`, `ensaio`, `grupo_mudou`, `sem_outro_dia_vivo`, `cache_pago`, `devolucao_pendente`, `max_devolucao_mudou`, `tente_de_novo`, `nao_cancelado`, `regime_sem_retido`, `abaixo_do_piso`, `acima_do_teto`, `pago_abaixo_do_devolvido`, `bv_nao_esta_a_pagar`, `valor_mudou`, `devolucao_travada` e `estado_mudou`, com a porta em que cada um nasce. O `valor_mudou` é o único que entra num 409 que já existe (o do BV da 305 no `set-status`).
11. **FR-062**: no evento avulso, o ponto de extensão recebe `("todos", None)`; no corte de um dia que não é o principal, `("so_este_dia", None)`, porque nenhum dia passou a guardar a venda.
12. **FR-070/FR-071/FR-072 — multa por escalação**: a linha do elenco é por escalação (vaga × dia). Um artista em 2 dias ou em 2 vagas tem 2 linhas, 2 campos no bloco e gera 2 gastos. "Uma linha por artista" passa a "uma linha por escalação".
13. **FR-071/FR-072 — multa vazia ou 0**: é ignorada nos dois caminhos (no ato e no `POST …/multas`); 400 para valor negativo ou inválido, ou para vaga/linha fora do ato. Só no `POST …/multas`: se, ignorados os vazios e zeros, não sobrar nenhum valor > 0, 400 `fields.multas` ("Informe a multa de ao menos um artista"), porque o endpoint existe para lançar.
14. **FR-011 — prova da prévia = execução**: variante no 2 e no 8, com `hoje` no dia 2 e no dia 10: GET `…/impacto-exclusao?devolucao=` antes e POST depois, conferindo `retido`, `comissao_retido`, `ajuste`, `ciclo`, `repasse_em` e `bv_retido` contra o gravado. A mutação "simular escreve" (o GET grava) é detectada pela conexão separada.
15. **FR-067/FR-068 — um sino por ato**: `dedupe_key` = `evento.cancelado:<id do evento da URL>` e `evento.cancelado_escala:<id do evento da URL>:<dia_id>` (o dia, porque a FR-068 pede um por dia). A equipe de Ensaio recebe um sino por ato com ensaio. Variante no 44: corte de um dia com ensaio e depois "Cancelar todos" com ensaio → 2 sinos por pessoa da equipe de Ensaio.
16. **FR-027/FR-049 — cheia 0 sem mudar o vivo**: a cheia é 0 em cortesia/permuta com valor e em evento sem vendedor, e a comissão do evento vivo (a "casca") não muda número. Variante no 16b (cheia 0 nos dois casos); o 1 confere a casca.
17. **FR-023**: o bloco opcional "o que foi pedido" é da 2a. A 306 não constrói nada dele (nem prop); o diálogo é o mesmo sem ele.
18. **FR-061 (tela)**: "Gastos extras vinculados" do principal vivo lista só dias vivos; no cancelado, lista o próprio dia e, no regime `venda`, os dias do ato.
19. **Verificação**: **59 cenários vivos** — os 57 mais 37b e 38c, numerados. "Deve falhar?": 20 "sim", 38 "não", 1 "—" (o 27). Ficam como variantes: 9/10-desfazer, 16/17-`paid_amount`, 38-comprovante, 2/8 prévia = execução, 16b cheia 0, 39 devolução do dia depois do principal cancelado, 44 dois sinos. Fechamentos: 12 e 32 fecham "sem a DRE" na História 2 e a parte da DRE na História 3; o 21 fecha na História 3 (inclusive a parte virtual e a multa, semeada por ORM), e a parte do satélite na História 5.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite) no frontend.

**Dependências principais**: Flask, SQLAlchemy, Alembic (migration à mão); React, TanStack Query, Tailwind CSS, `@manto/ui` (`Dialog`/`ConfirmDialog`), Framer Motion, `@manto/api-client`, `@manto/money` (`MoneyInput` no imposto, no novo total, na venda nova e na multa).

**Armazenamento**: PostgreSQL. As três tabelas novas e as colunas estão em data-model.md.
- **Nenhuma coluna em tabela existente.** `SpecialExpense.CATEGORY_MULTA_CANCELAMENTO = "Multa de cancelamento"` nasce no molde de `CATEGORY_DEVOLUCAO` (`models.py:1073`) e entra em `SpecialExpense.CATEGORIES` (`:1070-1072`); `category` é `String(30)` (`:1079`). Os dois kinds do sino são texto (`kind` tem 40 caracteres, `models.py:686`).
- **Espelho** (só leitura, 15/10, dump de 30/09):
  - eventos: 0 cancelados, 0 marcados, 7 grupos, 14 ensaios futuros ligados (8 a satélite), 0 cachê pago em evento futuro;
  - comissões: 0 linhas `no_banco`, 0 linhas vivas de evento cancelado, 72 linhas que o resync alcança, 142 pagas (25 de evento futuro), 2 com `original_id`;
  - gastos: 84 aprovados com evento;
  - usuários ativos: CASTING 2, ENSAIO 2, SUPERADMIN 3;
  - `alembic_version` = `a7c3e91f4d28`.

**Verificação**:
- `specs/306-dinheiro-do-cancelamento/verify_306.py` contra o `manto_local`:
  - Google dublado e e-mail travado;
  - login só pela API; escrita conferida por conexão separada;
  - harness `main` × branch por `git archive`.
- Dois scripts: `retrato_main_branch.py` (as telas dos meses sem cancelamento, `main` × branch, com relógio fixo; cenário 23) e `contagem_pre_deploy.py` (só leitura; espelho e produção).
- Portões: `npm run typecheck`, `ruff check` e `npm run build`.
- Tela aberta no Browser pane, em desktop.
- Verifies antigos de novo:
  - `verify_303` (c12 reescrito) e `verify_267` (`:278-289` reescrito);
  - `verify_267b`, `267c`, `299`, `205`, `215b`, `305` (já na História 1, porque `marcar_status_do_bv` substitui o ramo BV da 305 em `financeiro_write.py:163-194`, e de novo na História 4, pela extração de `_montar_acrescimos`), `266`, `258` e `256`;
  - e, por tocarem núcleo de outra feature (Living Spec do checklist): `273` e `301` (o 409 no orçamento), `272` (os kinds novos de sino), `238` (`assign_role`), `271` (`GET /api/dashboard`) e `307` (arquivos em comum com a 307).

**Plataforma-alvo**: web, só o app interno (desktop). Portal e público não mudam.

**Tipo de projeto**: SPA desacoplada (API JSON + React).

**Metas de desempenho**:
- **Resumo em lote, nunca por evento**: `resumos_cancelados(ids)` e `devolucoes_por_evento(ids)`. Vale para a DRE, a página de Cancelamentos e os itens de BV da Planilha (calculados a partir de `bv_rows`).
- `CommissionEntry.evento_cancelado` sai de **uma** consulta por mês.
- A prévia é um GET sem trava e sem escrita; a tela espera ≥ 400 ms de digitação.
- O resync nunca espera o ato (`SKIP LOCKED`).
- O Google de N dias e ensaios roda em série **depois** do commit. O risco é o timeout do gunicorn: o 502 vira 409 `ja_cancelado` na repetição, e a tela recarrega.

**Restrições**:
- **Dinheiro**:
  - nenhuma conta de dinheiro no navegador;
  - taxa congelada por `Decimal(str(rate))`, porque a origem é `Float` (`models.py:279`, `:865`, `:872`), e comparada por `_mesma_taxa`;
  - a condição da linha da DRE é a **quantidade** de cancelados, nunca `Decimal("0.00")`, que mudaria o expoente;
  - pago e devolvido de um ato somam os ids do grupo por consulta (`cancel_ops.ids_do_grupo`: o principal e os dias com `group_leader_id` = ele, os mesmos de T1), nunca `leader.satellites` nem `group_events`.
- **Contrato com a tela**:
  - campo novo de payload é opcional no TS;
  - gate que já existe se testa com `!== false`;
  - PUT `…/acrescimos`, PATCH `…/comercial` e os comprovantes continuam devolvendo o **detalhe**, com o resumo dentro de `event.cancelamento`. A tela grava a resposta no cache;
  - todo 409 da 306 leva `codigo` de constante (`app/constants.py`), e a tela o lê pela união `CodigoRecusaCancelamento` (`lib/eventOps.ts`).
- **Google e histórico**:
  - a remoção do Google vai depois do commit, pelo atributo do módulo (`gcal.delete_event`), com `CALENDAR_SUPPRESS_EVENT_WRITES` lido a cada chamada (chave ausente = travado);
  - `EventLog` sem `created_at`, pelo default UTC (`models.py:631`). `cancelled_at` segue na hora de São Paulo sem fuso, como hoje.
- **ORM e imports**:
  - nunca `selectinload(CalendarEvent.cancelamento)` como constante de módulo;
  - `cancel_ops` fica "folha": no topo só importa `models`, `constants` e `db`; o resto vem por import tardio;
  - os imports de `routes.py` continuam tardios.
- **Jinja**: só ganha recusas com `flash`, as duas guardas da Planilha/Comissões e a linha da DRE (`docs/PARADA_REMOCAO_JINJA.md`).

**Escala/escopo**:
- **Dados**: 3 tabelas novas, 0 colunas em tabela existente.
- **Rotas**: 2 novas (`PATCH …/devolucao`, `POST …/multas`) e cerca de 30 contratos alterados, listados no RBAC da spec (com as três portas do ponto 8 da Living Spec) e em contracts/api.md.
- **Arquivos**:
  - backend: 31, mais 1 template e 1 migration;
  - frontend: 31, dos quais 7 componentes novos;
  - scripts: 3 novos e 2 verifies reescritos.
- **Verify**: 59 cenários (57 + 37b + 38c), mais as variantes do ponto 19 da Living Spec.
- **Tarefas**: cerca de 258, pela estimativa do backlog na sexta rodada.

## Constitution Check

*GATE: aprovado antes da Phase 0 e reavaliado depois da Phase 1. Não há violação; as exceções justificadas estão em "Rastreamento de complexidade".*

| Princípio / seção | Veredito e como o plano cumpre |
|---|---|
| I. Reutilizar antes de criar | **PASSA**. Reusa:<ul><li>proporção: `bv_que_acompanha` (`orcamento/quote_ops.py:58-85`; BV e comissão do retido usam a mesma, com teto);</li><li>da 305: `estado_da_venda`/`acompanhar_bv_da_venda` (`comercial_ops.py:438`, `:492`); `travar_evento` (`orcamento_evento_ops.py:788-799`); a validação de `substituir_acrescimos`, extraída em vez de copiada; `erros_do_bv` (`:406-417`);</li><li>comparações da 215b: `_mesma_taxa`/`_mesmo_vendedor` (`event_ops.py:1105-1123`);</li><li>da 303: `desmarcar`, `_exigir_ambiente_liberado` (`sumico_ops.py:707-714`);</li><li>notificações e e-mail: `resolver_destinatarios`, `emitir`, `send_removal_email` (`email_service.py:384-413`);</li><li>comissão e cobrança: o corpo de `_event_commission` como `_base_da_comissao`, `ciclo_de_pagamento_expr` (`comissoes_ops.py:188`), `_com_marca_do_ciclo` como molde (`:842-848`), `principal_da_venda` (`cobranca_ops.py:224-228`), `e_vaga_de_presenca` (`casting_ops.py:39-58`);</li><li>tela: `MoneyInput`, `ConfirmDialog`.</li></ul>Uma régua por regra: comissão cheia, cachê pago, devolução, "linha que abre ciclo", dia do repasse, dias vivos |
| II. Padrões de código | **PASSA**. Type hints e docstrings pt-BR com o porquê. `cancelar_evento` é fatiado em passos de cerca de 30 linhas, e `_montar_acrescimos` (extraído de `comercial_ops.py:216-404`, cerca de 190 linhas) em cinco passos de cerca de 30, o limite da constituição (`.specify/memory/constitution.md:43`); a lista dos cinco está na História 4 e é a mesma da R20. Se algum passo passar disso, entra uma linha no Rastreamento de complexidade com o porquê. Constantes em `app/constants.py`: regimes, modos, alcances, os 18 códigos 409 (`CODIGO_EVENTO_CANCELADO`, `CODIGO_VALOR_MUDOU` e os demais `CODIGO_*`, espelhados na união TS `CodigoRecusaCancelamento`, em `lib/eventOps.ts`), `MOTIVOS_AJUSTE_COMISSAO` com o código da 1e, `DIA_DO_REPASSE`, `NOTA_COMISSAO_PROPRIA_DO_DIA`. No modelo, `SpecialExpense.CATEGORY_MULTA_CANCELAMENTO`; em `group_ops`, `CAMPOS_DA_PASSAGEM`/`TABELAS_DA_PASSAGEM`. Nomes: tabela única do data-model §6. `except Exception as exc:  # noqa: BLE001` com `logger.warning` na remoção do Google. TS estrito, sem `any`. `ruff check` nos tocados e `ruff format` só nos três scripts novos e em `dre_ops.py` |
| III. Camadas / API First | **PASSA**. Regras de negócio em `*_ops.py` puros, com exceções próprias (`CancelValidationError(status, field, codigo, **extras)`, `EventoCanceladoError`, `GastoLockedError`). `agenda_write`, `gastos_write`, `financeiro_*` e `admin_config_read` só validam RBAC, chamam e serializam. Nenhum módulo novo em `app/api/` (os dois endpoints moram em `agenda_write.py`), então `app/api/__init__.py` não muda. Nenhuma rota pública, então `BACKEND_PREFIXES` não muda. `dre_ops.py` importa de `financeiro/routes.py` por import tardio (ver complexidade) |
| IV. Não quebrar o que funciona | **PASSA**.<ul><li>Mudança aditiva: tabelas novas e campos opcionais.</li><li>Regressões `main` × branch exatas:<ul><li>a casca `_event_commission` em todos os eventos (1);</li><li>itens de BV (17);</li><li>DRE e Tendência de todos os meses (23);</li><li>comissões de todos os grupos (41);</li><li>cobranças da Home sem devolução.</li></ul></li><li>`_event_commission` vira casca de `_base_da_comissao` (o corpo de hoje, intocado), e as suas **8 chamadas** ficam iguais em número: `financeiro/routes.py:231`, `:434`, `:1463`; `financeiro_read.py:402`; `vendas_ops.py:290`, `:339`; `comissoes_ops.py:403` (`comissao_exibida_do_evento`) e `:937` (`_sync`). O portão do beneficiário (cortesia, sem vendedor) fica só em `comissao_cheia_do_evento`.</li><li>Verifies antigos de novo, e matriz bundle × backend (seção Fases).</li></ul> |
| V. UI/UX com feedback | **PASSA**. Todo botão com loading. Erro no campo, por `fields`: `devolucao_*`, `bv_pix_<id>`, `multa_<id>`, `venda_nova`, `alcance`. Os 409 viram frase em pt-BR, inclusive em `FinanceiroSection`, que hoje mostra texto fixo (`:379-381`) ou nada (`:158`, `:195`). Diálogo nunca limpa o que foi digitado em erro. Ações destrutivas passam por `ConfirmDialog` |
| VI. Esteira (Nível 1) | **PASSA**. Migration, 2 endpoints novos, 3 domínios. Ordem: specify → clarify (15/10) → **plan** → checklist → tasks → analyze (confere contra o **código**, não só cruza documentos) → implement → converge |
| VII. Living Spec | **PASSA, com condição**: os 19 pontos de "Living Spec antes do `/speckit-tasks`" entram na spec antes das tarefas. As leituras 1–11 e o clarify de 15/10 já estão nela |
| VIII. Verify antes do núcleo | **PASSA (portão)**. `verify_306.py`, `retrato_main_branch.py` e `contagem_pre_deploy.py` nascem na **Fundação, antes de qualquer linha de núcleo**. Rodam vermelhos, e a saída fica em `verify_306_primeira_falha.txt`. O harness `main` × branch nasce do zero. Escrita conferida por conexão separada; login por `POST /api/auth/login`; requisições fora do `app_context`; `test_client(use_cookies=False)` onde o cookie é montado; limpeza no `finally` com `roles.clear()`. São 59 cenários, 20 deles "deve falhar" (37b e 38c são "não"). Cada História fecha com os seus cenários verdes antes da seguinte |
| IX. Dinheiro BRL | **PASSA**. `Numeric(12,2)` e `Decimal`/`ROUND_HALF_UP`. `commission_rate` em `Numeric(6,3)`. `MoneyInput` e `formatBRL` de `@manto/money`. Nenhuma conta no navegador: a prévia é do servidor |
| X. Mobile-first público | **NÃO SE APLICA**: nenhuma superfície pública ou do portal muda. O banner do marcado (app interno) ganha botão de largura total no celular (FR-024), conferido a 375×812 |
| XI. Framer Motion | **PASSA**. Os diálogos novos (`AlterarDevolucaoDialog`, `LancarMultaDialog`) usam a transição dos diálogos existentes, com `useReducedMotion()` |
| XII. Combobox / Maps | **NÃO SE APLICA**. Nenhum seletor novo com mais de 10 itens: o novo principal é decidido pelo servidor, e a multa é um campo por escalação. O seletor de vendedor do `VendaForm` é o de hoje |
| XIII. RBAC declarado | **PASSA**.<ul><li>Os dois endpoints novos têm gate no início da view, comentário `RBAC:` e linha em `docs/01` §4.3.</li><li>**Cada porta alterada** (as cerca de 30 do RBAC da spec, mais as três do ponto 8 da Living Spec) ganha linha em `docs/01` §4.3 com a regra nova de papel e o 409; `docs/00` §4 ganha a regra única do cancelado e §6 a ordem de travas evento → dependentes.</li><li>**Regra única** `pode_editar_venda_do_cancelado(user)`: Superadmin pelo papel real, como `_can_delete` (`agenda_write.py:111-115`).</li><li>Helper `_recusa_do_cancelado(event)` → 409 `codigo: CODIGO_EVENTO_CANCELADO`, chamado depois de T1 em todas as portas de (a) a (h).</li><li>404 antes do 403, salvo onde o HEAD já é diferente (Gastos Extras, escrito porta a porta na História 2). Flags calculadas no servidor depois de `_role_flags` (`agenda_read.py:155-204`; não dentro dela, porque `agenda.py:150` a reusa).</li></ul> |
| XIV. Config / efeito externo | **PASSA**. Nenhuma env nova. A remoção do Google (show e ensaios) passa a respeitar `CALENDAR_SUPPRESS_EVENT_WRITES`, chave da 303 que fica travada com banco em localhost. O e-mail vai por `send_async` com `_suppress_mail`. O verify dubla `app.calendar.service.delete_event` como segunda barreira. A docstring de `config.py:145-162`, `DEVELOPMENT.md:110-115`/`:151` e `CLAUDE.md` §4 passam a dizer que a trava cobre devolução **e** cancelamento |
| Stack | **PASSA**.<ul><li>**Migration**: escrita à mão, `down_revision = "a7c3e91f4d28"` (cabeça única), só `create_table`; o `downgrade` derruba as filhas antes; nada de `flask db migrate`.</li><li>**Migração destrutiva**: o ensaio não se aplica, porque nada é alterado nem apagado. Mas como o `startCommand` roda `flask db upgrade`, **o build é reproduzido num venv Python 3.11 antes do push** (`flask db downgrade a7c3e91f4d28 && flask db upgrade && python seed.py` e o verify nesse venv). Foi o build com dependências soltas que derrubou a 303 em 01/10.</li><li>**Jinja**: nenhum template novo; só uma linha em `dashboard.html`.</li><li>**Segredos**: nenhum.</li></ul> |
| Operação e Deploy | **PASSA**. Não toca o `startCommand`, então `validar_startcommand.py` não se aplica. Sobe sozinha, à noite, backend e frontend no mesmo push. Antes: contagem do dia em produção (só leitura). Depois: evento descartável e sonda `/api/` com JSON. Rollback assimétrico: depois do primeiro cancelamento real, só se corrige para a frente (`306b`) |

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/306-dinheiro-do-cancelamento/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/api.md
├── checklists/                     # requirements.md + os do /speckit-checklist
├── tasks.md                        # /speckit-tasks
├── verify_306.py                   # Fundação, antes do núcleo (+ verify_306_primeira_falha.txt)
├── retrato_main_branch.py          # telas dos meses sem cancelamento, main × branch, relógio fixo, git archive
├── contagem_pre_deploy.py          # só leitura; espelho e produção (SSH)
└── contagem_AAAA-MM-DD.txt         # saídas das contagens (espelho e dia do deploy)
```

### Código: backend (31 arquivos, mais o template e a migration)

**Novos**

| Arquivo | O quê |
|---|---|
| `migrations/versions/<rev>_dinheiro_do_cancelamento.py` | 3 × `create_table`, `down_revision = "a7c3e91f4d28"`, `downgrade` derrubando elenco → bvs → cancelamentos |
| `app/financeiro/dre_ops.py` | `ROTULO_RETIDO`; `gastos_extras_do_periodo(start, end)`, que é o gasto aprovado menos `filtro_devolucao` ∧ evento cancelado, de qualquer regime; `tendencia_mensal(today, meses=6)`. Importa `_is_permuta`, `_month_range`, `_prev_month` e `_pct` de `financeiro/routes.py` por import tardio |

**Alterados** (âncoras no HEAD)

| Arquivo | O que muda |
|---|---|
| `app/models.py` | <ul><li>Três classes depois de `Event3DDismissal` (`:2376-2403`). A relação é declarada no filho com `foreign_keys=`: `EventCancellation.event` → backref `cancelamento` (`uselist=False`), e as filhas por backref `bvs`/`elenco` (`cascade="all, delete-orphan"`).</li><li>`SpecialExpense.CATEGORY_MULTA_CANCELAMENTO`, no molde de `CATEGORY_DEVOLUCAO` (`:1073`), entra em `CATEGORIES` (`:1070-1072`).</li><li>Docstrings e comentários reescritos: `is_cancelled` (`:399-407`), `CommissionPayment` (`:946-956`), `SpecialExpense` (`:1066-1069`, `:1091` com "cliente", `:1114-1117`).</li><li>`is_devolucao_cliente` (`:1159-1162`, código morto) ganha docstring apontando `filtro_devolucao`.</li></ul> |
| `app/constants.py` | Perto de `NOTA_CICLO_VALOR_TARDIO` (`:466`) e de `SITUACAO_*` (`:573-575`): `REGIME_*` (`venda`, `satelite`, `virtual`, `dia` e o derivado `legado`); `MODO_*`; `ALCANCE_TODOS`/`ALCANCE_SO_ESTE_DIA`; `DIA_DO_REPASSE = 5`; `MOTIVOS_AJUSTE_COMISSAO`, a tabela dos motivos de ajuste com prefixo e código da 1e (FR-033); `NOTA_COMISSAO_PROPRIA_DO_DIA`; os 18 códigos 409 (`CODIGO_EVENTO_CANCELADO` = `"cancelado"`, homônimo de `sumico_ops.CODIGO_CANCELADO` (`:641`), que é de outro fluxo, e `CODIGO_JA_CANCELADO`, `CODIGO_ENSAIO`, `CODIGO_GRUPO_MUDOU`, `CODIGO_SEM_OUTRO_DIA_VIVO`, `CODIGO_CACHE_PAGO`, `CODIGO_DEVOLUCAO_PENDENTE`, `CODIGO_MAX_DEVOLUCAO_MUDOU`, `CODIGO_TENTE_DE_NOVO`, `CODIGO_NAO_CANCELADO`, `CODIGO_REGIME_SEM_RETIDO`, `CODIGO_ABAIXO_DO_PISO`, `CODIGO_ACIMA_DO_TETO`, `CODIGO_PAGO_ABAIXO_DO_DEVOLVIDO`, `CODIGO_BV_NAO_ESTA_A_PAGAR`, `CODIGO_VALOR_MUDOU`, `CODIGO_DEVOLUCAO_TRAVADA`, `CODIGO_ESTADO_MUDOU`). Nomes e valores: data-model §6. Não entra `NOTA_CICLO_CANCELAMENTO` (decisão (h)) |
| `app/calendar/cancel_ops.py` | Reescrita (detalhe por fase). Muda:<ul><li>`CancelValidationError` (`:39-44`) e `EventoMarcadoError.MENSAGEM` (`:56-59`);</li><li>`resumo_impacto` (`:95-143`), `aplicar_estorno_comissao` (`:146-173`), `_registrar_devolucao` (`:176-209`), `cancelar_evento` (`:254-341`), `listar_cancelamentos` (`:344-405`).</li></ul>Nasce:<ul><li>exceção e regra: `EventoCanceladoError`, `pode_editar_venda_do_cancelado`;</li><li>devolução: `filtro_devolucao`, `devolucoes_por_evento`;</li><li>grupo: `ids_do_grupo(principal_ids)`, a consulta dos ids do grupo (o principal e os dias com `group_leader_id` = ele), que `travar_grupo` trava em T1 e que o resumo e o período leem sem `FOR UPDATE`;</li><li>resumo: `ResumoCancelado`, `resumo_cancelado`, `resumos_cancelados`, `serializar_resumo_cancelado`;</li><li>período: `cancelados_do_periodo`, `totais_cancelamentos`, `retido_por_vendedor`;</li><li>BV: `bv_do_retido`, `bv_da_planilha`, `marcar_status_do_bv`;</li><li>ato e correções: `previa_cancelamento`, `alterar_devolucao`, `reaplicar_cancelado`, `reaplicar_por_dinheiro`, `travar_grupo`;</li><li>elenco: `cache_pago_do_evento`, `lancar_multas_do_cancelado`;</li><li>extensão: `ao_cancelar(event, *, alcance, novo_principal)`, o ponto da 2a, chamado em **todo** cancelamento (FR-062), hoje sem efeito.</li></ul> |
| `app/financeiro/comissoes_ops.py` | Nasce:<ul><li>`_beneficiario_comissionado(event, settings) -> User \| None`: `None` para Loja Virtual, sem beneficiário, `receives_commission` falso e cortesia/permuta; extraído de `should_have` (`:926-936`) e sem olhar cancelamento;</li><li>`_base_da_comissao(event, settings, *, venda=None, taxa=None, bv_total=None, custo=None)`: o corpo de hoje de `_event_commission` (`:766-796`), **intocado**; as sobreposições, ausentes, dão o número de hoje;</li><li>`_event_commission` vira casca que só chama a base, sem argumento;</li><li>`comissao_cheia_do_evento(event, settings, *, venda=None, taxa=None, bv_total=None, custo=None) -> (cheia, beneficiario_id, taxa_usada)`: passa primeiro por `_beneficiario_comissionado` (→ 0) e então chama a base;</li><li>`comissao_do_retido`, `primeiro_repasse_aberto`, `reconciliar_comissao_do_cancelado`;</li><li>`filtro_estorno_orfao`, `linha_abre_ciclo` (Python e SQL), `tipo_da_linha`, `ciclo_de_pagamento_da_linha`.</li></ul>Toques:<ul><li>`_sync_commission_payment` (`:914-986`), `_comissao_existente` (`:886-911`), `_resync_pending_commissions` (`:989-1011`);</li><li>`liquidar_periodo` (`:249-258`), `pay_seller_month` (`:631-638`), `liquidar_item_de_comissao` (`:296-361`);</li><li>`_pending_reversals_query` (`:434-450`), `month_ids` e `reversal_ids` (`:529-553`), `month_status` e `sale_count` (`:570-573`);</li><li>`STATUS_LABELS` (`:31-35`), `CommissionEntry` e `_to_entry` (`:46-74`, `:453-465`), `CommissionKpis` e `get_month_kpis` (`:77-91`, `:581-594`);</li><li>`_group_cost` (`:725-730`), por `dias_vivos`.</li></ul> |
| `app/financeiro/routes.py` (Jinja vivo) | <ul><li>DRE: `_compute_drg` (`:205-257`, com `cancelamentos=`) e `dashboard()` (`:263-575`).</li><li>Planilha: `_build_bv_items` (`:870-901`), `_build_commission_items` (`:904-975`).</li><li>`set_payment_status`: o ramo de gasto (`:1182-1189`) trava o evento antes de mudar o status de uma devolução de cancelado; o ramo BV (`:1190-1197`) passa a `marcar_status_do_bv(valor_esperado=None)`, com `flash` em `bv_nao_esta_a_pagar`.</li><li>`set_commission_status` (`:1561-1582`): guarda de uma linha que recusa (`flash`) mexer em linha de evento cancelado, fora do caminho único (a Planilha nova).</li><li>`/vendas/`: `events_q` (`:1454`) com `cancelled_at IS NULL`.</li></ul>Nada é movido nem apagado |
| `app/templates/financeiro/dashboard.html` | Uma linha depois de `:123`, condicionada a `drg_total.n_cancelados` |
| `app/api/financeiro_read.py` | <ul><li>`api_vendas_pipeline` (`:120-175`).</li><li>`api_financeiro_dashboard` (`:185-545`): `paineis.cancelamentos` sempre; docstring `:188-189` e comentário `:231-232`.</li><li>`api_financeiro_comissoes` (`:548-595`).</li><li>`_serialize_pagamento_item` (`:598-643`): `commission_lines`.</li></ul>As consultas de BV (`:706-714`) não mudam |
| `app/api/financeiro_write.py` | O ramo BV (`:163-194`) passa a `marcar_status_do_bv`. O ramo `expense` (`:147-161`), na devolução de cancelado, trava o evento, relê o gasto com `FOR UPDATE populate_existing` e confere `valor_esperado` contra `amount` (divergente → 409 `valor_mudou` "A devolução mudou para R$ X…"); sem o campo, como hoje. O 409 de valor divergente do ramo BV, que é da 305, ganha o mesmo `codigo: CODIGO_VALOR_MUDOU`, com a mensagem de hoje |
| `app/financeiro/vendas_ops.py` | `build_kpis(…, cancelados=())` (`:249-298`); `event_payment_status(…, cancelado=False)` e o rótulo (`:32-66`); docstring `:154-157` |
| `app/financeiro/cobranca_ops.py` | As devoluções dos dias são descontadas em `recebido_da_venda` (`:217-221`), `resumir_venda` (`:301-327`), `VendaResumo` (`:98-195`) e `_primeira_parcela_descoberta` (`:265-275`). Docstrings `:3-6` e `:104-106`. `data_do_grupo` (`:236-243`) **não muda**: já pula cancelado |
| `app/api/admin_config_read.py` | `api_admin_desempenho` (`:117-178`): filtra cancelado; `retido`/`cancelados` por **nome** |
| `app/clientes/client_ops.py`, `app/api/clientes_read.py` | `list_clients` (`:111-129`), `get_client_detail` (`:132-159`), `client_metrics` (`:183-225`); `clientes_read.py:90-91` |
| `app/api/dashboard_service.py` | `compute_performance`: `perf_filter` (`:290-293`) com `cancelled_at IS NULL` |
| `app/gastos/gastos_ops.py` | Nasce: `GastoLockedError`, `devolucao_de_cancelado`, `_travar_devolucao`. Toques: `_validate_expense_data(…, tipo_atual=None)` (`:194-238`), `create_expense` (`:256-318`), `approve_expense` (`:321-330`), `reject_expense` (`:333-346`), `delete_expense` (`:356-360`), `link_expense_to_event` (`:363-378`), `edit_expense` (`:381-442`) |
| `app/api/gastos_write.py`, `app/api/gastos_read.py` | Os seis endpoints (defs em `:49`, `:82`, `:99`, `:117`, `:153`, `:172`) capturam a exceção com `json_error(…, 409, fields=…, event_id=…, codigo=CODIGO_DEVOLUCAO_TRAVADA)` e `rollback()`, na ordem de gate de cada porta como está no HEAD (História 2). `_expense_dict` (`:31-57`) ganha `locked` e `event_cancelled` |
| `app/calendar/group_ops.py` | `group_events` (`:64-75`) **não muda**. Nascem `dias_vivos(event)` (os dias do grupo sem os cancelados; régua única de custo, KPI e gastos da tela) e as listas `CAMPOS_DA_PASSAGEM`/`TABELAS_DA_PASSAGEM` (FR-059; a 2b e a 6a estendem). `validar_agrupamento` (`:116-139`) e `desagrupar` (`:204-231`) travam e recusam cancelado; `passar_venda` nova; docstring `:1-32` |
| `app/calendar/sumico_ops.py` | `MOTIVO_CANCELADO` em `_MOTIVOS_DE_DESMARCAR` (`:60-62`). `_apagar_vazio` (`:341-356`) trava, relê `cancelled_at` e recusa cancelado |
| `app/calendar/event_ops.py` | <ul><li>`delete_ensaio` (`:1791-1811`): a parte de banco vira função sem commit.</li><li>`update_event_comercial` (`:1169-1240`): relê `is_cancelled` depois de `estado_da_venda` (`:1204`); o gancho vira despachante.</li><li>`_gravar_venda_da_edicao` (`:846-879`): 409 no cancelado.</li></ul> |
| `app/calendar/comercial_ops.py` | `_montar_acrescimos`, extraído de `:216-404` e fatiado em cinco passos (História 4). `substituir_acrescimos` (`:156`) devolve `[]` no cancelado, **depois** de `travar_evento` (`:208`, `:218`). `alterar_acrescimos_do_cancelado` nova |
| `app/calendar/orcamento_evento_ops.py` | `set_event_orcamento` (`:935`): 409 no cancelado antes de aplicar a venda, cobrindo os três verbos |
| `app/calendar/casting_ops.py` | `assign_role`: o `if` do e-mail de remoção (`:153-161`) ganha `and not event.is_cancelled` |
| `app/notificacoes/notificacoes_ops.py` | `KIND_EVENTO_CANCELADO` e `KIND_EVENTO_CANCELADO_ESCALA` no catálogo e em `DESTINATARIOS_POR_KIND` (`:54-71`); dois produtores no molde de `notificar_convite_recusado` (`:252-277`), com `dedupe_key` pelo ato |
| `app/calendar/routes.py` | <ul><li>Exclusão: docstring de `_delete_event` (`:309-331`); `_delete_event_flow` (`:4348-4382`) trava e recusa cancelado **antes** da checagem do líder; `delete_calendar_event` (`:4471-4499`) mostra o `flash`.</li><li>Despachante `event_detail` (`:1657-1671`): recusa única das ações de dinheiro, para todos os papéis.</li><li>Grupo: `_handle_ungroup_event` (`:1580-1591`) e `_handle_group_events` (`:1536-1547`) traduzem a recusa.</li><li>KPI Jinja (por volta de `:1781`, `:1814-1816`): só dias vivos.</li></ul> |
| `app/api/agenda_write.py` | <ul><li>Cancelamento: `api_impacto_exclusao` (def `:514`), `api_delete_event` (`:534`), `api_cancelar_evento` (`:579`), `api_listar_cancelamentos` (`:693`).</li><li>Evento e venda: `api_update_event` (`:1067`), `api_update_event_comercial` (`:1210`), `api_set_event_orcamento` (`:1338`).</li><li>Notas: `:1489`, `:1524`, `:1562`. Acréscimos: `api_set_acrescimos` (`:1588`). Parcelas: `api_set_parcelas` (`:1644`).</li><li>Comprovantes: `:1747`, `:1778`, `:1803`. Reembolsos: `:1823`, `:1859`, `:1899`.</li><li>Grupo: `api_agrupar_eventos` (`:2365`), `api_desagrupar_evento` (`:2431`), `api_remover_satelite` (`:2455`, ausente do plano do backlog).</li><li>Novos: `PATCH …/devolucao` e `POST …/multas`. Helper `_recusa_do_cancelado`.</li></ul> |
| `app/api/agenda_read.py` | <ul><li>`serialize_event_detail` (`:711`): bloco `cancelamento`, `kpi` ausente (`:1105-1110`), flags novas.</li><li>Flags `pode_mudar_taxa`/`pode_trocar_vendedor` (`:998-999`) passam por um E com `can_edit_venda_cancelado` **só no evento cancelado**; no vivo ficam como hoje (a flag é `cancelado && is_superadmin`, e o E no vivo apagaria a 215b).</li><li>`_serialize_acrescimos` (`:544-563`): sem `bv_pix` no cancelado para quem não tem a flag.</li><li>`_compute_kpi` (`:352-421`) por `dias_vivos`.</li><li>`_serialize_gastos` (`:507`, chamado em `:1110`): no principal vivo, `dias_vivos`; no cancelado, o próprio dia e, no regime `venda`, os dias do ato (o principal e os `satelite` com `group_leader_id` = ele).</li></ul> |
| `app/admin/user_ops.py` | `delete_user` (`:417-442`): bloqueio "cancelamentos" |
| `app/config.py` | Só a docstring `:145-162` |

### Código: frontend interno (`frontend/apps/internal/src/`, 31 arquivos)

| Arquivo | O que muda |
|---|---|
| `components/EventDetail/ExcluirEventoDialog.tsx` | <ul><li>Estado e reset (`:99-118`); `ResumoImpacto` (`:30-74`).</li><li>Confirmação (`:123-152`). Textos que mentem: `:68-70`, `:218-221`.</li><li>Na H5 saem o aviso de líder (`:174-190`) e o `disabled` por `is_group_leader` (`:283`).</li><li>Trava de capacidade: `regime === undefined`.</li><li>Sem prop do bloco "o que foi pedido": é da 2a.</li></ul> |
| `CancelamentoDevolucaoBloco.tsx` *(novo)* | Tudo/Parte/Nada, nome e PIX, prévia mantida na tela, "A cliente pagou R$ X" |
| `CancelamentoBvBloco.tsx` *(novo)* | BV cheio, proporcional e "já pago"; recebedor e PIX obrigatórios quando faltam |
| `CancelamentoDiasBloco.tsx` *(novo, H5)* | Dias vivos, `alcance`, "Novo valor da venda", "a venda passa para DD/MM" |
| `MultaAoElencoBloco.tsx` *(novo, H6)* | Uma linha por escalação (artista, vaga e dia), cachê de referência, "faltavam N dias", aviso de talento sem PIX. Reusado no ato e depois |
| `ResultadoCancelamento.tsx` *(novo)* | Substitui o `KpiGrid` (`ComercialSection.tsx:81-177`) no cancelado; botões "Alterar devolução" e "Lançar multa ao elenco" |
| `AlterarDevolucaoDialog.tsx`, `LancarMultaDialog.tsx` *(novos)* | Diálogos do `PATCH …/devolucao` e do `POST …/multas` |
| `components/EventDetail/EventHeader.tsx` | `MOTIVO_SO_DEVOLVER` (`:39-41`); "Excluir ou cancelar" deixa de usar o `disabled` do marcado (`:349-357`); caixa do cancelado (`:408-420`, texto `:417`); "Analisar e decidir" (`:436-444`); "Editar tudo" (`:339-346`) escondido no cancelado |
| `components/EventDetail/SumiuDoGoogleBanner.tsx` | Prop `onCancelar`, botão `w-full sm:w-auto` no molde de `:62-66`, texto `:68-69` |
| `components/EventDetail/ComercialSection.tsx` | Link de Comissões (`:93-96`); `VendaForm` (`:186-437`) confirma a troca de vendedor; `OrcamentoPanel` (`:561-`) sem ações; `VendaPanel.canEdit` (`:919`); `GrupoPanel` (`:1050-1212`); escolha do bloco (`:1225-1236`) |
| `components/EventDetail/ColecoesComerciaisPanel.tsx` | `AcrescimosPanel.canEdit` (`:67`) pela flag no cancelado; o BV pago já é só leitura (`:191`, `:263-268`) |
| `components/EventDetail/ResumoSection.tsx` | "Recebimento — em aberto" (`:391-411`, `:399`) → devolução e retido |
| `components/EventDetail/FinanceiroSection.tsx` | `PagamentosPanel` (`:307-386`) com `can_edit_pagamentos !== false` e `add.error.message` (`:379-381`); erro em editar e excluir (`:129-207`); `NotasFiscaisPanel` (`:388-480`) e `ReembolsosPanel` (`:534-660`) pela flag no cancelado |
| `components/Pagamentos/PagamentoItemViews.tsx` | `commission_lines` no detalhe dos dois itens; valor negativo (`:245`). `valor_esperado: item.amount` (`:112-116`), hoje só no `bv`, passa a ir também no `expense` (ponto 5 da Living Spec) |
| `components/notificacoes/NotificacaoItem.tsx` | Ícones dos dois kinds (`:7-13`) |
| `pages/ComissoesPage.tsx` | `formatDate` (`:40-43`) fatia a string; filtro "No banco" (`:243-245`); quarto card (`:378-396`); colunas tipo e ciclo (`:164-170`, `:252-259`, `:435-441`) |
| `pages/GastosExtrasPage.tsx` | `GastoFormValues` (`:124-130`), `formFromExpense` (`:150-160`), `DesembolsoFields` (`:164-242`), campos (`:219-228`), `buildPayload` (`:313-316`), modal (`:369-396`), `GastoRow` (`:483-590`, rótulo `:528`, ações `:552-570`) |
| `pages/FinanceiroDashboardPage.tsx` | `DreRowKind` (`:21`), `dreRows` (`:33-58`), `Record` de status (`:60-74`), `DreTable` (`:138`), `as number` → `?? 0` (`:171`), rodapé (`:410-414`), barra (`:443-472`), selo da NF (`:583-598`), tendência (`:622-655`) |
| `pages/VendasPipelinePage.tsx` | `Record` de status (`:39-45`); `KpiGrid` (`:81-121`) por `VendasKpis`; sublinha somada à do desconto (`:96-102`) |
| `pages/AdminDesempenhoPage.tsx` | `retido`/`cancelados` (`:86-108`) |
| `pages/EventosCancelamentosPage.tsx` | `STATUS_DEVOLUCAO` + `no_banco` (`:29-32`); resumo e todas as devoluções (`:146-176`); PIX só com `show_financeiro` |
| `pages/EventDetailPage.tsx` | Sem mudança; conferir a aba Comercial com `kpi` ausente (`:127-134`) |
| `lib/agenda.ts` | `cancelamento?` (com `taxa?` e `elenco?`); flags `can_edit_pagamentos?`/`can_edit_venda_cancelado?` (`flags` é `Record<string, boolean>`, `:385`) |
| `lib/eventOps.ts` | `ImpactoElenco` (`:93-98`), `ImpactoExclusao` (`:102-115`), `CancelarEventoInput` (`:126-129`), `useCancelarEvento` (`:135-155`), `useDeleteEvent` (`:72-87`), `EventoCancelado` (`:243-257`), `invalidarComercial` (`:300-310`), `useSetAcrescimos` (`:313-337`). Nascem `usePreviaCancelamento`, `useAlterarDevolucao`, `useLancarMultas` e a união `CodigoRecusaCancelamento` (os 18 códigos, com o `valor_mudou`, ao lado de `CodigoDevolverAoGoogle`; `gastos.ts` e `financeiro.ts` a importam) |
| `lib/eventInline.ts` | `useUpdateEventComercial` (`:107-114`): invalida também `financeiro-dashboard`, `vendas-dashboard` e `cancelamentos` |
| `lib/eventAttachments.ts` | `useEventMutation` (`:46-60`): invalida `["event"]`, `financeiro-*`, `vendas-dashboard` e `cancelamentos` |
| `lib/financeiro.ts` | Tipos do DRE e do dashboard: `DreView` (`:7-25`), `TopSeller` (`:46-51`), `MonthlyTrendItem` (`:53`), `FinanceiroPaineis` (`:80`), `NotaFiscalPendente` (`:119`). Tipos de Comissões e da Planilha: `CommissionStatus` (`:194`), `CommissionEntry` (`:198`), `CommissionKpis` (`:217`), `PagamentoItem` (`:344-362`). **Exporta** `invalidarFinanceiro` (`:300`). `exportComissoesCsv` (`:309`) usa o mesmo rótulo de status |
| `lib/vendas.ts`, `lib/adminConfig.ts`, `lib/gastos.ts`, `lib/clientes.ts` | `VendasKpis` (`:43-49`); `DesempenhoItem` e `AdminDesempenho` (`:87-99`); `DisbursementType` (`:5`), `GastoExtra` (`:17-41`), `UpdateGastoInput` (`:144`); `clientes.ts:41-49` |

`lib/navigation.tsx` não muda: o gate do Financeiro e o menu são da 1c.

### Scripts e verifies

- **Novos**: `specs/306-…/verify_306.py`, `retrato_main_branch.py`, `contagem_pre_deploy.py`.
- **Reescritos**:
  - `specs/303-…/verify_303.py`: `c12_nao_cancela` (`:2339`) e `MSG_MARCADO` (`:167`);
  - `specs/267-…/verify_267.py` (`:278-289`): lê o bloco `cancelamento` de um `legado`.
- **Rodados de novo**: `verify_267b`, `267c`, `299`, `205`, `215b`, `305`, `266`, `258`, `256`.

### Docs

- `docs/00`:
  - §4 (RBAC): a regra única do cancelado (`pode_editar_venda_do_cancelado`, Superadmin pelo papel real; os demais recebem 409 `cancelado`);
  - §6 (Armadilhas transversais): a ordem de travas evento → dependentes (T1–T6) e o "relê depois de travar".
- `docs/01`:
  - §4.3: os dois endpoints novos; a linha de `_can_delete()` ganha o `PATCH …/devolucao`; **uma linha para cada porta alterada**, com o papel e o 409 (as cerca de 30 do RBAC da spec, mais `PATCH /api/events/<id>`, `DELETE …/grupo/satelites/<sat>` e `POST /api/financeiro/pagamentos/set-status`);
  - contratos, catálogo de notificações, categoria, tabela de modelos, códigos 409;
  - correção de `:770-771`.
- `docs/02`: diálogo, tela do cancelado, Gastos, Comissões, Planilha, DRE, marcado; correções de `:464-465` e `:1500-1501`.
- `docs/03`: entrada no topo e linha no índice; a 224g passa a fechada.
- `docs/04`: os invariantes da lista da spec; correções de `:314`, `:316-318`, `:320`, `:359`.
- `docs/05`: as dívidas da lista da spec, mais as deste plano (seção Polimento), riscando o que quita.
- Fora de `docs/`: `DEVELOPMENT.md:110-115` e `:151`, `CLAUDE.md` §4, `config.py:145-162` e `group_ops.py:1-32`.

**Decisão de estrutura**:
- **Onde mora cada regra**:
  - o dinheiro do cancelamento mora onde já mora o cancelamento (`cancel_ops.py`);
  - a regra da linha de comissão, onde já mora a comissão (`comissoes_ops.py`);
  - a passagem da venda, os dias vivos e as listas da passagem, onde mora o grupo (`group_ops.py`; `passar_venda` é injetada como `agrupar` injeta `sincronizar_comissao`, `group_ops.py:24-31`);
  - a DRE, num módulo novo (`dre_ops.py`), porque a conta é a mesma para a API e para o Jinja e mover `_compute_drg` está proibido.
- **`cancel_ops` é folha** no topo: `cobranca_ops`, `comissoes_ops`, `group_ops`, `comercial_ops` e `routes` só entram por import tardio. Assim `sumico_ops.py:37` e `cobranca_ops.py:31-58` não fecham ciclo.

## Modelo (resumo; colunas, índices e nulidade em data-model.md)

**`event_cancellations`** (um por evento):
- chave e vínculo: `event_id` UNIQUE, FK com CASCADE;
- tipo do ato: `regime String(12)`; `refund_mode String(8) NULL`, nulo em `satelite`/`virtual`;
- congelado do dinheiro: `sale_value`, `commission_full` e `retained_tax` (este NULL = não se aplica), em `Numeric(12,2)`; `commission_rate Numeric(6,3) NULL`; `commission_cost Numeric(12,2) NULL`, o custo de cachês da cheia EducaManto no ato, pela **mesma régua de custo da comissão** (`_group_cost` no principal, `_event_cost` no EducaManto que não é principal, `comissoes_ops.py:786`), já sem dia cancelado depois da História 5;
- quem recebe: `commission_seller_id` e `seller_id`, FKs para `users` **sem `ondelete`**, protegidas pelo bloqueio em `delete_user`; `with_invoice`;
- grupo: `group_leader_id`, FK `calendar_events` SET NULL; **`sale_handed_over Boolean NOT NULL default false`**, verdadeiro só no antigo 1º dia que passou a venda (a tela lê `venda_passou_para = group_leader_id`; o `EventLog` não se consulta, e um `dia` comum também tem `group_leader_id`);
- só no regime `dia`: `sale_value_before/after` e `sale_value_gross_before/after`;
- auditoria: `created_at`/`updated_at` (São Paulo); `updated_by_id` SET NULL.

**`event_cancellation_bvs`**:
- `cancellation_id` CASCADE, com índice;
- `acrescimo_id` SET NULL, com UNIQUE; todo leitor soma só linhas com `acrescimo_id` não nulo;
- `recipient String(200)`, `pix String(140)`;
- `original_amount`, `paid_at_cancellation`, **`paid_amount NULL`** (decisão (a)).

**`event_cancellation_elenco`** — uma linha por **escalação** (vaga × dia):
- `cancellation_id` CASCADE, com índice;
- `talent_id` NOT NULL (sem cascade), `role_id` SET NULL;
- `character_name`, cachê de referência;
- **`day_event_id` FK `calendar_events` CASCADE e NOT NULL**, com índice: o dia cancelado não se exclui (FR-021), e o CASCADE só age se essa regra for furada;
- **`special_expense_id`** SET NULL, com UNIQUE: uma multa por linha (por escalação; um artista em 2 dias ou 2 vagas tem 2 linhas), e a exclusão em Gastos Extras volta a linha a "não lançada".

Cancelado sem linha é `legado`. Criar **sempre pela relação** (`EventCancellation(event=event, …)`), nunca só pela coluna: senão `event.cancelamento` fica `None` na sessão e a resposta sai `legado`.

## Travas: sempre evento → dependentes

| Trava | O que trava | Como |
|---|---|---|
| T1 `travar_grupo(event)` | Principal e todos os dias do grupo, vivos e cancelados | Ids por **consulta** (`ids_do_grupo`: o principal e os dias com `group_leader_id` = ele; nunca por `event.satellites`); `SELECT … WHERE id IN (…) ORDER BY id FOR UPDATE` + `populate_existing()`. Relê a composição do grupo; se mudou, 409 `grupo_mudou`. Regime, vendedor, taxa e `is_cancelled` só se leem **depois** dela. `travar_evento` (que relê 4 colunas) não basta para o ato |
| T2 | `event_cancellations`, `_bvs` e `_elenco` do grupo | Leitura com `populate_existing`, sem `FOR UPDATE`: todo escritor passa por T1 |
| T3 | Acréscimos do principal | `ORDER BY id FOR UPDATE populate_existing`, como em `comercial_ops.py:211-214` |
| T4 | Linhas de comissão | **Um SELECT só**: `event_id IN (grupo) OR (seller_id IN beneficiários AND status IN ('a_pagar','no_banco'))`, com `ORDER BY id FOR UPDATE populate_existing`. Só quando `simular=False` |
| T5 | Devoluções do grupo, pendentes inclusive | `ORDER BY id FOR UPDATE populate_existing` |
| T6 | Escalações com talento dos dias alcançados | `ORDER BY id FOR UPDATE`, só no ato. Protege a régua do cachê pago contra o "pago" de cachê, que não trava o evento |

Pago e devolvido de um ato somam os ids que T1 consulta (`cancel_ops.ids_do_grupo`; na leitura do resumo, a mesma consulta sem `FOR UPDATE`).

**Ordem por operação**:

| Operação | Ordem |
|---|---|
| Cancelar (todas as variantes) | T1 → T2 → T3 → T4 → T5 → T6 → validar → `desmarcar` → `flush` → congelar → devolução → `flush` → no corte: `estado_da_venda`, venda nova e **uma** chamada a `acompanhar_bv_da_venda` → alvo → reconciliar → `cancelled_at` → `ao_cancelar` → ensaios (banco), sinos e multas → `EventLog` → commit → Google (show e ensaios) e e-mail fora da trava, com os ids guardados antes do commit. É a ordem única do ato: a H2 constrói sem ensaios, sinos e multas, e a H6 os põe neste lugar |
| Alterar devolução | 400 só se `devolucao_total` faltar ou não for número → T1 → T2 → T4 → T5 → decidir → gravar → reconciliar → commit. T4 e reconciliar só no `venda`, ou no `dia` com o principal cancelado inteiro (os beneficiários se conhecem depois de T2). A prévia não trava |
| Multas | T1 → T2 (elenco) → INSERT do gasto. Sem T3 e sem T4 (Q10 = A) |
| Acréscimos do cancelado | T1 → T2 → T3 → gravar → `flush`/`expire` → T4 → reconciliar |
| Reembolsos, parcelas e notas | `travar_evento` (o próprio evento) → relê `is_cancelled` → recusa → o de hoje. No vivo, o caminho de hoje |
| Comprovantes | T1 (também no vivo: o comprovante mexe no pago do grupo) → recusa → gravar → `flush`. Com principal `venda` cancelado: → T4 → reconciliar. No POST, 409 depois de gravar → rollback e o arquivo novo removido |
| BV na Planilha (API e Jinja) | `travar_evento(principal)` → a linha do acréscimo → T2 em leitura |
| Devolução na Planilha (API e Jinja) | `travar_evento(evento da devolução)` → o gasto `FOR UPDATE populate_existing` → `valor_esperado` (só na API) → status |

**Fora da 306, para nada cruzar essa ordem** (a lista única; a R24 a repete e o resto do plan a cita):
1. `order_by(CommissionPayment.id)` em `liquidar_periodo` (`comissoes_ops.py:249-257`) e em `pay_seller_month` (`:631-638`). É uma linha em cada, sem mudar comportamento.
2. **Desfazer da 267c**: travar os eventos das linhas (`ORDER BY id FOR UPDATE`) antes de `liquidar_periodo(…, linhas="pagas")`. Hoje ele trava as linhas e depois pede KEY SHARE no evento ao inserir o `EventLog` (`:351-359`), o que fecha ciclo com T1 → T4.
3. **Exclusão**: `_delete_event_flow` e `_apagar_vazio` travam e releem o evento antes de `_delete_event`. Fecha também a dívida 101.
4. **`_resync_pending_commissions`**: percorre os eventos por id e trava cada um com `FOR NO KEY UPDATE SKIP LOCKED`, que não segura inserção de comprovante. Relê `cancelled_at`, pula o evento travado e commita por evento.
5. **Portas vivas** (`update_event_comercial`, `_gravar_venda_da_edicao`, Jinja `:837`, `substituir_acrescimos`): reconferem `is_cancelled` logo depois do `travar_evento` delas.
6. **Gastos Extras sobre devolução**: `travar_evento` antes de decidir; no vincular, os dois eventos em ordem de id.
7. **Agrupar e desagrupar** (`group_ops.py:116-139`, `:204-231`): travam e releem em ordem de id, e decidem a recusa depois da trava.
8. **Deadlock residual** (40P01): nos endpoints da 306 vira rollback + 409 `tente_de_novo`.

**Escritores de fora que cruzam as tabelas do ato** (ficam como estão):
- `set_event_clients` (`event_ops.py:1244`) já trava o evento antes dos vínculos (305): compatível com T1.
- `delete_client` (`client_ops.py:238`) desvincula em lote (`UPDATE calendar_events … WHERE client_id`, `:249`), sem `ORDER BY id`. Pode cruzar com T1 num grupo cujos dias têm a mesma contratante e com a passagem, que move `event_clients`. **Resíduo aceito**: o Postgres desfaz um dos dois; do lado da 306 vira 409 `tente_de_novo`, do lado do `delete_client` um 500 raro com rollback inteiro, sem nada gravado pela metade. Excluir cliente é raro e só do Superadmin.
- `sync_events` grava sem ordem: é o item 8 acima.

**Resíduo aceito** (vai ao `docs/05`): um "pago" da Planilha cuja instrução começou antes da linha nova da reconciliação não a vê. Ela fica aberta naquele ciclo e aparece na Planilha; nada se perde.

## Fases de construção (para o `/speckit-tasks`)

O `tasks.md` fecha as fases **nesta ordem**, cada uma com os seus cenários verdes antes de abrir a seguinte (spec, "Cenários"). Os blocos do verify acompanham as fases: B0 Fundação, B1–B6 Histórias 1–6, B9 limpeza.

### 0. Setup

- `.specify/feature.json` → `specs/306-dinheiro-do-cancelamento`.
- `scripts\db\refresh-local-db.ps1`, a recontagem por `sql_ro.py` (números do Contexto técnico) e `contagem_2026-10-15.txt` na pasta.
- **Descartáveis do verify**:
  - usuários: SUPERADMIN, COMERCIAL, FINANCEIRO, CASTING, FIGURINO, ENSAIO, MARKETING e ARTISTA_3D;
  - um vendedor;
  - um talento com e-mail de teste, atribuído a vaga existente com `talent_id IS NULL`. Nunca `EventRole` inventada.

### 1. Fundação: verify primeiro, modelo, comissão cheia e resumo

**Constrói**
1. **Verify antes do núcleo.**
   - `verify_306.py` com os **59 cenários** (os 57 da spec mais 37b e 38c) e as variantes deste plano: 2/8 prévia = execução, 9/10-desfazer, 16/17-`paid_amount`, 16b cheia 0, 38-comprovante, 39 devolução do dia depois do principal cancelado, 44 dois sinos.
   - **Opções** (definidas no quickstart §1, Living Spec do checklist): sem argumentos, o portão (`59/59 OK`, variantes dentro do seu cenário); `--so=2,2b,8` (só os listados; a limpeza, 27, roda sempre); `--nucleo` (Fundação e História 1 antes da API); `--regressao` (os verifies antigos do quickstart §5 em subprocesso, contra a base da primeira rodada); `--semear-tela` / `--limpar-tela` (dados da conferência de tela, no molde da 303).
   - **Chão herdado do `verify_303`**: trava de e-mail; guarda `calendar_auto_sync_at`, que sai com exit 2; dublê de `app.calendar.service.delete_event` em todo cancelamento; `_esperar_threads`.
   - **Instrumentos**:
     - espião de `send_removal_email`;
     - notificações contadas por conexão separada;
     - matriz de `hoje` (dias 1–5 × depois do dia 5), trocando `now_sp` nos módulos de comissão;
     - Planilha aquecida de M−1 a M+2;
     - retrato linha a linha para a passagem;
     - retrato das tabelas tocadas antes e depois de cada GET de prévia, pela conexão separada (mutação "simular escreve").
   - **Harness `main` × branch**: `git archive` do `git merge-base`, os dois lados em subprocesso, comparação exata (quantize 0,01; percentual a 0,1).
   - Roda **vermelho**, e a saída fica em `verify_306_primeira_falha.txt`.
2. **`retrato_main_branch.py`**.
   - Só lê. Relógio fixo, trocando `datetime` em `app.financeiro.routes`, `app.api.financeiro_read` e, quando existir, `app.financeiro.dre_ops`.
   - Neutraliza `ensure_recurring_entries` (`gastos_ops.py:498-546`, chamado em `routes.py:304-305` e `financeiro_read.py:252`).
   - Lê o Jinja por `template_rendered` de `GET /financeiro/?period=custom…`.
   - Compara, nos meses sem cancelamento, o que o SC-002 lista: `GET /api/financeiro/dashboard` (DRE, Tendência e painéis) e a DRE Jinja; `GET /api/vendas/pipeline`; `GET /api/admin/desempenho`; `GET /api/clientes/<id>` de toda cliente com evento, `GET /api/clientes/` e `GET /api/clientes/metricas`; `GET /api/dashboard` (Performance e cobranças); `GET /api/financeiro/comissoes` e `GET /api/financeiro/pagamentos` (itens de comissão e de BV).
   - Comissões e Planilha gravam no GET (resync): a `main` aquece os meses antes do retrato e a rodada da branch não pode escrever linha nenhuma (o retrato de linhas do cenário 26 confere).
   - Fica fora o que muda de propósito, listado à parte na saída: o ticket médio Jinja (FR-043), o `sale_count`, o item aberto de soma zero com linha de valor (R6) e, por cancelado `legado`, o mês do `cancelled_at`, o do `expense_date` de cada devolução ligada a ele e, só na Tendência, o mês do evento (quickstart §3).
   - Mutação: somar o retido sem a condição da quantidade de cancelados acusa a diferença.
   - Não importa nada que só exista na branch.
3. **`contagem_pre_deploy.py`**.
   - Sem `create_app` e sem importar `app`. Usa `psycopg` ou `psycopg2`, porque a produção só tem o 2. Transação `default_transaction_read_only=on`.
   - Conta o que a spec lista em Premissas/Deploy, mais:
     - `a_pagar` negativas com `event_id`;
     - `no_banco` por mês;
     - ciclos abertos de soma zero com linha de valor (grupo aberto da 267c);
     - linhas vivas de evento cancelado;
     - órfãos `a_pagar`;
     - BV não pago de `legado`;
     - gasto aprovado com categoria fora de `CATEGORIES`;
     - devolução ligada a evento vivo.
4. **Migration, modelos e constantes** (seção Modelo; nomes do data-model §6): as três tabelas, `SpecialExpense.CATEGORY_MULTA_CANCELAMENTO` em `CATEGORIES`, regimes, modos, alcances, motivos, `DIA_DO_REPASSE`, `NOTA_COMISSAO_PROPRIA_DO_DIA` e os 18 `CODIGO_*` (com `CODIGO_VALOR_MUDOU`). `flask db upgrade` e `seed.py` no `manto_local`; ida e volta (`downgrade a7c3e91f4d28` → `upgrade`) conferida no espelho.
5. **Comissão cheia em duas camadas** (FR-027).
   - `_base_da_comissao(event, settings, *, venda=None, taxa=None, bv_total=None, custo=None)` é o corpo de hoje de `_event_commission` (`:766-796`), intocado; as sobreposições servem só ao recongelamento.
   - `_event_commission(event, settings)` vira casca que só chama a base. Ela continua zerando só venda nula, Loja Virtual e `receives_commission` falso, e o evento sem vendedor continua com comissão na DRE de hoje.
   - `_beneficiario_comissionado(event, settings)` sai de `should_have` (`:926-936`): `None` para Loja Virtual, sem beneficiário, `receives_commission` falso e cortesia/permuta; não olha cancelamento.
   - `comissao_cheia_do_evento(event, settings, *, venda=None, taxa=None, bv_total=None, custo=None) -> (cheia, beneficiario_id, taxa_usada)`: com `_beneficiario_comissionado` nulo, cheia 0; senão, a base.
   - Cenário 1: `main` × branch da **casca** em todos os eventos do espelho (as 8 chamadas). Variante do 16b em modo núcleo: cheia 0 em cortesia com valor e em evento sem vendedor.
6. **Funções puras**: `comissao_do_retido(cheia, retido, venda)` e `bv_do_retido(cheio, retido, venda) = min(cheio, bv_que_acompanha(cheio, retido, venda))`. Mesma tolerância de R$ 0,01 e zero quando venda ≤ 0.
7. **Resumo e período** (FR-004, FR-005, FR-044).
   - `filtro_devolucao()` = categoria + `event_id` + aprovado, nunca por `disbursement_type`. Substitui o `.first()` de `cancel_ops.py:361-372`.
   - `devolucoes_por_evento(ids)`, no molde de `cobranca_ops.comprovantes_por_evento` (`:197-214`).
   - `ids_do_grupo(principal_ids)`: a consulta dos ids do grupo (seção Travas), sem `FOR UPDATE`; T1 trava a mesma consulta na H2.
   - `ResumoCancelado` / `resumo_cancelado` / `resumos_cancelados`: `selectinload` montado **dentro** da função; pago e devolvido pelos ids do grupo por consulta (`ids_do_grupo`, seção Travas), nunca por `group_events`.
   - `cancelados_do_periodo(inicio, fim, *, seller_id=None, educamanto_only=False)`:
     - `outerjoin` com o congelado; vendedor por `coalesce(congelado, ao vivo)`;
     - filtro de tipo seguro contra nulo;
     - faixa sem fuso, como `vendas_ops.py:165-166`;
     - sem dinheiro = fora (P-24).
   - `totais_cancelamentos`, `retido_por_vendedor`.
8. **Predicados únicos**:
   - `filtro_estorno_orfao()`;
   - `linha_abre_ciclo`, em Python e em SQL;
   - `tipo_da_linha(cp)`;
   - `ciclo_de_pagamento_da_linha(cp)`, espelho de `:212-216`, com o 3º degrau em **UTC** como o `date()` do SQL. O verify compara Python e SQL em todas as linhas do espelho.
9. **Exceções e regra**:
   - `CancelValidationError(message, field=None, status=400, codigo=None, **extras)` (`:39-44`); `EventoMarcadoError` continua subclasse;
   - `EventoCanceladoError`;
   - `pode_editar_venda_do_cancelado(user)`.

**Ao fim da fase**
- **Verde**: 1, 23, 26 e 27 (limpeza); em modo núcleo, a variante "cheia 0" do 16b.
- **Vermelho esperado**: todos os outros, pelas funções e rotas que faltam.
- **Pode estar verde antes do núcleo** sem ser defeito: as partes do 6 e do 28 que já valem hoje (403 do COMERCIAL no cancelar e 401 sem sessão nas rotas que existem). O "já cancelado" do 5 **não**: no HEAD, `api_cancelar_evento` responde 400 (`agenda_write.py:609-610`), e o cenário espera 409.

  Todo outro verde é defeito do verify.

**Riscos**
- `AmbiguousForeignKeysError` sem `foreign_keys=` derruba o `create_app`, e com ele o `startCommand`.
- `selectinload` de backref como constante de módulo quebra o start (lição da 302).
- Um `Decimal("0.00")` somado sem condição quebra o 23.
- O GET da DRE comita (`ensure_recurring_entries`).
- Ciclo de import, se `cancel_ops` importar `cobranca_ops` no topo.
- `event.cancelamento` lido como `None` antes do insert.
- Pôr o portão do beneficiário na casca mudaria a DRE de hoje (evento sem vendedor); o 1 e o 23 acusam.

### 2. História 1: a comissão e o BV acompanham o retido (P1)

**Constrói (backend)**
- **Reconciliação**.
  - `primeiro_repasse_aberto(seller_id, hoje, *, excluir_event_id=None, travar=False) -> date`:
    - `hoje = now_sp().date()`;
    - nos dias 1 a `DIA_DO_REPASSE`, o mês anterior se ali houver linha que abre ciclo; senão o corrente;
    - teto de 24 ciclos;
    - `excluir_event_id` deixa a prévia igual à execução, apesar do autoflush.
  - `reconciliar_comissao_do_cancelado(event, alvos, *, motivo, hoje=None, simular=False)`:
    - invariante por beneficiário; `falta = alvo − liquidadas`;
    - a linha `a_pagar` mais antiga recebe a falta;
    - linha nova ligada à paga (`original_id`);
    - EducaManto positiva com `payable_from` = dia do evento (FR-032);
    - `audit()` por linha e motivo por prefixo de `MOTIVOS_AJUSTE_COMISSAO` (FR-033);
    - **nenhuma mutação de ORM com `simular=True`**.
- **`_sync_commission_payment`** (`:914-986`):
  - mantém o retorno antecipado da Loja Virtual (`:918-921`) e ganha `if event.is_cancelled: return` logo depois;
  - sai o `and not event.is_cancelled` (`:930-932`); `should_have` = `sale_value` ∧ `_beneficiario_comissionado(…)` não nulo (mesmo número de hoje no evento vivo);
  - **regra nova (b)**: com ajuste vivo e base de volta a `a_pagar`, reconcilia com alvo = cheia.
  - A guarda é segura antes da H2: o cancelar legado ainda desvincula as linhas (`cancel_ops.py:157-173`).
- **Consultas e itens de Comissões**:
  - `_comissao_existente` (`:886-911`): `original_id IS NULL` e sem `NOTA_COMISSAO_PROPRIA_DO_DIA`.
  - `_resync_pending_commissions` (`:989-1011`): trava 4 da seção Travas; docstring.
  - `liquidar_periodo` e `pay_seller_month` ganham `order_by(id)`; o desfazer da 267c trava os eventos antes.
  - Órfão por `filtro_estorno_orfao()` em `_pending_reversals_query` (`:434-450`) e em `reversal_ids` (`:548-553`); docstrings `:434-442` e `:468-482`.
  - `no_banco` em `STATUS_LABELS`, `_month_scoped_query` (`:410`) e `month_ids` (`:533`).
  - `CommissionEntry`/`_to_entry`: `tipo`, `original_id`, `evento_cancelado` (consulta em lote), `ciclo`, `motivo?`, todos com default.
  - `CommissionKpis`/`get_month_kpis`: `total_no_banco`; `total_month` = pago + no banco + a pagar.
  - `get_month_summary_by_seller`, **dois predicados**:
    - `month_status` = "pendente" se houver `a_pagar` com valor ≠ 0, órfão incluído, o que preserva o "Pagar Mês";
    - `abre_ciclo` só em `primeiro_repasse_aberto`;
    - `sale_count` conta só `original_id IS NULL` (`:570`), com registro no `docs/03`.
- **Planilha**:
  - `_build_commission_items` (`:904-975`): `linhas` nos dois itens. O "soma zero com linha de valor não some" vale **só no grupo aberto** (`:951-953`); o grupo pago fica como está.
  - `_build_bv_items` (`:870-901`): `amount = bv_da_planilha(a)` por import tardio; `None` pula; resumos em lote.
  - `_serialize_pagamento_item` (`:598-643`): `commission_lines`.
- **BV**: `bv_da_planilha(acr)` (tabela da decisão (a)) e `marcar_status_do_bv` nas duas portas (`financeiro_write.py:163-194`, `financeiro/routes.py:1190-1197`):
  - evento → acréscimo;
  - `atual is None` → 409 `bv_nao_esta_a_pagar` "este BV não está a pagar, recarregue";
  - valor divergente → 409 `valor_mudou`, com a frase da 305 e o valor `atual` (o código é aditivo; a mensagem não muda);
  - `audit` com o valor.
- **Exclusão** (FR-036):
  - `aplicar_estorno_comissao` (`:146-173`): `primeiro_repasse_aberto` por import tardio, ramo `no_banco`, motivo "Exclusão do evento", sem copiar as datas da venda;
  - `_delete_event_flow` (`calendar/routes.py:4348-4382`) e `_apagar_vazio` (`sumico_ops.py:341-356`) travam e releem.

**Constrói (frontend)**
- `lib/financeiro.ts`: `no_banco`, campos opcionais, `commission_lines?`, `invalidarFinanceiro` exportada.
- `ComissoesPage.tsx`: `formatDate`, filtro, 4º card, tipo e ciclo.
- `PagamentoItemViews.tsx`: as linhas.

**Ao fim da fase**
- **Verde**:
  - 13, 14, 14b;
  - **em modo núcleo**: 7–11, 12 (sem a DRE), 17 e 30, mais as variantes 9/10-desfazer e 16/17-`paid_amount`, e no 8 a comparação `reconciliar(simular=True)` × `simular=False` (o começo da variante prévia = execução). O verify semeia `event_cancellations` por ORM e chama a reconciliação e `bv_da_planilha` direto. Eles fecham pela API na H2.
- **Vermelho esperado**:
  - 2–6, 15, 16, 18, 19, 25, 28, 31, 32, 34, 36: o ato e as rotas;
  - H3–H6.
- **Verifies antigos**: `verify_305` de novo já aqui, porque `marcar_status_do_bv` substitui o ramo BV da 305 (`financeiro_write.py:163-194`); ele volta a rodar na H4, pela extração de `_montar_acrescimos` (quickstart §5).

**Riscos**
- **Ordem das travas**: deadlock 40P01 se alguma trava de várias linhas ficar sem `ORDER BY id`.
- **Autoflush**: `primeiro_repasse_aberto` dispara flush das linhas recém-mudadas; o `excluir_event_id` é o que impede a divergência.
- **Coleção velha**: `event.commission_payments` (relação em `models.py:981-986`, backref em `:984`) depois de reconciliar. Expirar antes do resumo e de `comissao_exibida_do_evento` (`:369-403`).
- **Bundle antigo**: ignora `commission_lines`. A linha `no_banco` imprime `status_label` vindo do servidor, mas o filtro não tem a opção; hoje são zero linhas. `total_month` muda: os três cards antigos deixam de fechar na janela do deploy.
- **Bundle novo com backend antigo**: `kpis.total_no_banco` ausente; o 4º card tolera `undefined`.
- **Cache**: `staleTime: 30_000` (`packages/api-client/src/queryClient.ts:39`); as mutações fora do `financeiro.ts` passam a chamar `invalidarFinanceiro`.

### 3. História 2: cancelar e devolver (P1)

**Constrói (backend)**
- **`cancelar_evento` fatiado** (`:254-341`), na ordem da FR-013 e das Travas:
  - Travar: T1–T5, com T6 vindo na H6.
  - Validar (códigos por constante):
    - FR-007, FR-009, FR-010 (`_validar_pix_do_bv`, que grava recebedor e PIX no acréscimo **depois** de T3, com `erros_do_bv`) e FR-012;
    - imposto faltando com nota, negativo, **enviado sem nota** ou no corte → 400 `fields.imposto_retido`;
    - `IntegrityError` do UNIQUE → 409 `ja_cancelado` com rollback.
  - `desmarcar(motivo=MOTIVO_CANCELADO)` **antes** de `cancelled_at`; sai a recusa do marcado (`:282-283`).
  - Congelar: `commission_rate` por `Decimal(str(…))`; `commission_cost` pela régua do custo da comissão; `paid_at_cancellation`/`paid_amount` lidos com T3.
  - Devolução: `_registrar_devolucao` (`:176-209`) com teto, nome e PIX obrigatórios, e `flush`.
  - Alvo, reconciliar, `cancelled_at`, limpeza do pedido (`:310-316`).
  - `ao_cancelar(event, alcance=ALCANCE_TODOS, novo_principal=None)` no avulso (FR-062).
  - Histórico: `EventLog` **sem** `created_at` (hoje `:321-327` grava hora de SP), e `_log_sync`.
  - Commit e Google. `gcal.delete_event` (`service.py:495-501`) pelo atributo do módulo; trava lida a cada chamada; pula marcado, `virtual-local-` e evento sem id; 404/410 = "já não estava"; `aviso` sem o texto cru do erro.
  - **A recusa do líder (`:289-292`) fica até a H5.**
- **Impacto e correções**:
  - `resumo_impacto` (`:95-143`): `acao: "cancelar"` para todo marcado (`:114`); chaves novas.
  - `previa_cancelamento`: `simular=True`, a mesma conta.
  - `alterar_devolucao`, ramo `venda`: `_aplicar_novo_total(dono, …)`. A devolução aberta absorve; zerada, é excluída com `gastos_ops._log`; sem aberta, nasce complemento; regrava `cliente` e completa nome e PIX.
  - `reaplicar_cancelado(event, *, motivo)`, ramo do dinheiro, e `reaplicar_por_dinheiro` (decisão (c)).
- **`EventoMarcadoError`**: texto e docstring "devolva ao Google ou cancele"; fica só na exclusão (`calendar/routes.py:4368-4371`, `api_delete_event`).
- **Recusa do cancelado** em `_delete_event_flow`, antes do líder; `flash` no Jinja; `api_delete_event` recusa **antes** da condição de `:555`, com `codigo`.
- **`sumico_ops`**: `MOTIVO_CANCELADO`; `_apagar_vazio` recusa cancelado.
- **Regra única em todas as portas de (a) a (h)**, sempre depois de T1. Quem passa no gate de hoje e não é Superadmin leva 409 `cancelado`; as gravações do Superadmin que recongelam abrem na H4.
  - **Comercial**: `api_update_event_comercial`, na ordem 404 → 403 → satélite (`:1224-1229`) → 409 → 215b (`:1256-1259`).
  - **Notas, parcelas e reembolsos**: as três notas, `api_set_parcelas`, lançar e marcar cobrado.
  - **Acréscimos**: `api_set_acrescimos`, e `substituir_acrescimos` no-op devolvendo `[]` depois de `:208`.
  - **Orçamento**: `set_event_orcamento` (`orcamento_evento_ops.py:935`), 409 para **todos**.
  - **Edição completa**: `api_update_event` / `_gravar_venda_da_edicao`, 409 para **todos** quando algum campo de venda chega diferente, comparado por `_mesmo_valor`, `_mesma_taxa` e `_mesmo_vendedor`.
  - **Jinja**:
    - despachante `event_detail` (`:1657-1671`), depois de `travar_evento` e de reler, para `update_comercial`, `update_sale`, os três de comprovante e os três de reembolso, **para todos os papéis**;
    - `set_commission_status` (`financeiro/routes.py:1561-1582`): guarda de uma linha que recusa com `flash` mexer em linha de evento cancelado;
    - `set_payment_status`, ramo de gasto (`:1182-1189`): trava o evento antes de mudar o status de uma devolução de cancelado.
- **Comprovantes** (`:1747`, `:1778`, `:1803`): decisão (c), ramo avulso. A recusa vem antes de `_add_payment_record` (`calendar/routes.py:1132-1155`). No **POST**, um 409 que nasça depois de `_add_payment_record` (`tente_de_novo`, `grupo_mudou`) faz rollback e remove o arquivo novo no `except`; o PATCH só troca `amount` (`calendar/routes.py:1159-1164`) e não recebe arquivo. Resposta = detalhe.
- **Endpoints**:
  - `api_cancelar_evento` (`:579`): corpo novo; `CancelValidationError` → `json_error(msg, status, fields, codigo, **extras)`; saem o `except EventoMarcadoError` (`:607-608`), o 400 fixo em `fields.motivo` (`:609-610`) e a docstring (`:580-586`).
  - `api_impacto_exclusao` (`:514`): `?devolucao=` → `{efeito}`; inválido → 400.
  - `PATCH …/devolucao` (novo), na ordem dos contracts §3: 401 → 404 → 403 → 400 só se `devolucao_total` faltar ou não for número → T1 → T2 → T4 (no `venda`; na H5, também no `dia` com o principal cancelado inteiro) → T5 → 409 `nao_cancelado` → 409 `regime_sem_retido` → 400 `fields` (`devolucao_total` negativo ou, no `venda`/`legado`, acima do pago; `devolucao_nome`/`devolucao_pix`; `imposto_retido` no `dia`, no `legado` ou sem nota) → 409 `abaixo_do_piso` → (no `dia`, H5) 409 `acima_do_teto` → núcleo → `{ok, resumo}`.
  - `api_listar_cancelamentos` (`:693`): `resumo` em lote; `devolucao` legado mantido um ciclo.
- **Detalhe** (`serialize_event_detail`, `:711`):
  - `event.cancelamento` com `show_comercial`; dinheiro, PIX e `taxa?` com `show_financeiro`;
  - `kpi` ausente (`:1105-1110`);
  - `_serialize_gastos` no cancelado: o próprio dia e, no `venda`, os dias do ato;
  - flags calculadas depois de `_role_flags`;
  - `_serialize_acrescimos` sem `bv_pix` no cancelado para quem não tem a flag;
  - `pode_mudar_taxa`/`pode_trocar_vendedor` ∧ flag, **só no cancelado**; no vivo, as da 215b sem mudança (o cenário 25 confere as duas no vivo).
- **Gastos Extras** (FR-019, FR-020): a trava roda **antes** das atribuições de `edit_expense` (`:420-428`) e de qualquer carga preguiçosa; recusa por campo **diferente** do gravado, depois de normalizar; `approved_with_edits` nunca acende na devolução; `rollback()` explícito nos seis endpoints. **Ordem porta a porta, como está no HEAD**:
  - `POST /api/gastos` (`gastos_write.py:47`): 401 → sem gate de papel (como hoje) → o recibo é salvo antes (como hoje) → 400 (validação; criar `cliente`) → trava do evento → 409 `devolucao_travada` (devolução ligada a evento cancelado);
  - `POST …/aprovar` (`:80`) e `POST …/rejeitar` (`:97`): 401 → 403 → 404 → trava → 409 `devolucao_travada` → 409 de estado de hoje;
  - `PATCH /api/gastos/<id>` (`:115`): 401 → 403 → 404 → 409 de estado de hoje (rejeitado sem `aprovar`, `gastos_ops.py:402-405`, antes da validação de `:407`) → 400 → trava → 409 `devolucao_travada`;
  - `DELETE /api/gastos/<id>` (`:151`): 401 → **404** (`:160`) → **403** (`:165`, autor do pendente ou Financeiro) → trava → 409 `devolucao_travada`;
  - `POST …/vincular-evento` (`:170`): 401 → 403 → 404 → 400 → trava dos dois eventos por id → 409 `devolucao_travada`.
- **Planilha, devolução**: o ramo `expense` da API (`financeiro_write.py:147-161`) trava o evento, relê o gasto e confere `valor_esperado` contra `amount` (ponto 5 da Living Spec).
- **`delete_user`**: bloqueio "cancelamentos" (FR-073).

**Constrói (frontend)**
- **Diálogo de cancelar**: `ExcluirEventoDialog` com `CancelamentoDevolucaoBloco` e `CancelamentoBvBloco`, mais imposto, efeito e trava de capacidade.
  - O 409 divergente refaz o impacto; o 409 `ja_cancelado` invalida e fecha.
  - Virtual: só o motivo. Marcado: aviso.
- **`lib/eventOps.ts`**:
  - tipos opcionais e a união `CodigoRecusaCancelamento`;
  - `usePreviaCancelamento`: chave `["evento-previa-cancelamento", id, valor]`, `keepPreviousData`, ≥ 400 ms, decimal com ponto;
  - `useCancelarEvento.onSuccess` invalida `invalidarSumidosGoogle`, `invalidarNotificacoes`, `financeiro-*`, `vendas-dashboard`, `gastos-extras`, `cancelamentos` e `["event"]`;
  - `useDeleteEvent` + `invalidarSumidosGoogle`;
  - `useAlterarDevolucao`.
- **Tela do cancelado**: `AlterarDevolucaoDialog`; `ResultadoCancelamento`; `ResumoSection`; `EventHeader`; `SumiuDoGoogleBanner`.
- **`FinanceiroSection`**: gates `!== false` e mensagens do servidor; `eventAttachments.useEventMutation`.
- **Planilha**: `PagamentoItemViews` manda `valor_esperado: item.amount` também no `expense`.
- **Gastos e Cancelamentos**: `GastosExtrasPage` e `lib/gastos.ts`; `EventosCancelamentosPage`; `lib/agenda.ts`.

**Ao fim da fase**
- **Verde**:
  - pela API: 2 e 8 com a variante prévia = execução (`hoje` no dia 2 e no dia 10); 2b (sem a parte do aviso), 3, 4 (sem o corte e a multa), 5, 6, 7, 9–11;
  - 12 e 32 **sem a DRE**;
  - 15, 16, 17 (sem o satélite), 18, 19, 25, 28, 30, 31, 34, 36, com as variantes 9/10-desfazer e 16/17-`paid_amount` pela API;
  - as partes "COMERCIAL/FINANCEIRO → 409" do 16b, do 16c(v) e do 16d.
- **Vermelho esperado**:
  - DRE (20–22, 24 e as partes da DRE do 12 e do 32);
  - Superadmin corrigindo dados de venda (16b–16e);
  - grupo (29, 35, 37, 37b, 38, 38c, 39–42d);
  - cachê, ensaio, aviso e multa (33, 40, 42e, 43–45c).

**Riscos**
- **Leitura do evento**: T1 sem `populate_existing` lê `is_cancelled` velho do mapa de identidade, porque o endpoint carregou o evento para o 404 e o 403. `desmarcar` depois de `cancelled_at` não faz nada, e o sino fica para sempre.
- **Prévia × execução**: qualquer mutação de ORM com `simular=True` some no rollback do GET, mas o autoflush a grava antes; a variante do 2 e do 8 e o retrato pela conexão separada acusam.
- **Depois do commit**:
  - `ObjectDeletedError` ao ler objeto expirado: guardar os ids antes;
  - N chamadas ao Google podem dar timeout; a repetição recebe 409 `ja_cancelado` e a tela recarrega.
- **Autoflush**: `total_recebido` é SQL e o autoflush o alcança. Ainda assim, `flush` explícito antes do retido e antes de `reaplicar_*`. Verify por conexão separada.
- **Gastos Extras**:
  - `date.today()` em `_validate_expense_data` (`:248`) sem data vira 409 de data falso; comparar depois de normalizar;
  - o bundle antigo manda `disbursement_type` `"cliente"`, `"fornecedor"` ou `""`, e o servidor preserva o `cliente`;
  - no `POST`, o recibo salvo antes fica órfão no 400 (como hoje) e no 409 novo (`docs/05`).
- **Bundle × backend**:
  - bundle velho com backend novo: cancelar sem modo → 400 legível (`ExcluirEventoDialog:133`); `kpi` ausente não some com a aba (`EventDetailPage:127-134`); `is_group_leader` mantido um ciclo; a Planilha velha não manda `valor_esperado` no `expense` e marca sem conferir, como hoje;
  - bundle novo com backend velho: sem `regime`, o envio fica travado.

### 4. História 3: DRE e comercial pelo que ficou (P1)

**Constrói**
- **`dre_ops.py`**:
  - `gastos_extras_do_periodo` substitui `routes.py:294-301` e `financeiro_read.py:243-250`, somando em `Decimal`;
  - `tendencia_mensal` substitui `routes.py:394-415` e `financeiro_read.py:365-385`. Tira o cancelado; o retido entra pelo mês de `cancelled_at`, só quando ≠ 0.
- **`_compute_drg(…, cancelamentos=None)`** (`:205-257`): soma sob `if cancelamentos and cancelamentos["quantidade"]` em receita (`:218`), impostos depois do quantize (`:219-222`), CPV (`:227`) e comissões (`:231`). `retido_cancelamentos` e `n_cancelados` sempre no retorno.
- **`dashboard()` Jinja**:
  - `cancelamentos=` em `:316`/`:319` (o Projetado em `:318` não muda);
  - ticket médio (`:327-330`) pela venda dos eventos com venda;
  - barra (`:375-379`), antes do `sorted`/`max`;
  - Top Vendedores (`:381-392`) com o retido antes do corte do top 5;
  - Recebimentos Previstos (`:469-473`);
  - selo da NF no título (`:496-503`);
  - comentário `:280-282`.
- **`dashboard.html`**: a linha.
- **`api_financeiro_dashboard`**:
  - os mesmos toques: `:243-250`, `:262`/`:264`, `:341-342`, `:348-363`, `:365-385`, `:428-432`;
  - NF com `cancelado?`/`retido?` (`:456-465`);
  - `paineis.cancelamentos` sempre (`:522-535`).
- **Dashboard Comercial**: `vendas_ops.build_kpis(…, cancelados=)`, onde o retido entra em `total_vendido` e em `comissao_prevista` pelo beneficiário **congelado**; `api_vendas_pipeline` com o recorte do escopo.
- **`/admin/desempenho`**: filtro na consulta (`:149-157`); `retido_por_vendedor(start.date(), (end − 1 dia).date())`, mapeado de id para **nome**.
- **Ficha da cliente**: `get_client_detail` (total = vivos + retido, resumos só se houver cancelado), `list_clients` e `client_metrics` com o filtro.
- **Performance da Home**: `compute_performance`. **Jinja `/vendas/`**: o filtro.
- **Frontend**:
  - `financeiro.ts`, mais os `Record` de status com `cancelado` nas duas páginas **no mesmo commit**;
  - `FinanceiroDashboardPage`;
  - `vendas.ts` e `VendasPipelinePage`;
  - `adminConfig.ts` e `AdminDesempenhoPage`;
  - `clientes.ts`.

**Ao fim da fase**
- **Verde**:
  - 20, 22, 24, e as partes da DRE do 12 e do 32;
  - 21 inteiro menos o satélite: a parte **virtual** fecha aqui (o regime nasce na H2 e o filtro de tipo está em `cancelados_do_periodo`), e a "multa ligada ao cancelado" é **semeada por ORM**, com a categoria `SpecialExpense.CATEGORY_MULTA_CANCELAMENTO` criada na Fundação (não depende da H6);
  - o 23 continua verde.
- **Vermelho esperado**: H4–H6.

**Riscos**
- **Comparação exata**: o expoente do `Decimal` e o retorno sem as chaves no Projetado.
- **API × Jinja**: a mesma consulta em dois lugares tem de sair de `dre_ops`.
- **Contrato e telas**:
  - `as number` com a chave ausente (`:171`);
  - contrato do Dashboard Comercial incompleto para a sublinha "de N cancelamentos": `kpis.retido_cancelamentos?` ganha `n_cancelados?` e `comissao_retido?`, registrados em contracts/api.md;
  - na janela do deploy, a Receita Bruta inclui o retido sem a linha que explica (cerca de 1 min).
- **Mudanças de comportamento intencionais** (docs/03): ticket médio Jinja; `sale_count`; ficha da cliente; o item aberto de comissão de soma zero com linha de valor, que passa a aparecer na Planilha também em mês sem cancelamento (R6); o cancelado `legado` sem dinheiro, que hoje se exclui (inclusive pelo sync) e passa a dar 409 e a ficar (R7); nos `legado`, a DRE do mês (gastos sem a devolução) e a Tendência do mês do evento (sem a venda e o cachê, FR-043); a cobrança da Home de venda viva com devolução lançada à mão, que passa a descontá-la (risco aceito 16). A contagem do quickstart §2 mede esses casos antes do push.
- **Tipo nulo** (dívida 47): o filtro seguro vale só nos cancelados.

### 5. História 4: dados de venda do cancelado, só o Superadmin (P2)

**Constrói**
- **`update_event_comercial`** (`event_ops.py:1169-1240`):
  - relê `is_cancelled` depois de `estado_da_venda` (`:1204`) e recusa com 409 `estado_mudou` se o estado mudou;
  - o gancho (`:1230-1231`, antes do commit de `:1240`) vira despachante: cancelado → `reaplicar_cancelado`, vivo → `_sync`. Isso mantém "a mesma transação".
- **`reaplicar_cancelado`**, estendido (FR-049, FR-050, FR-051):
  - venda e cortesia: `comissao_cheia_do_evento(…, taxa=congelada, bv_total=Σ original_amount das linhas vivas, custo=commission_cost)`; cortesia/permuta dá cheia 0 pelo portão do beneficiário;
  - taxa por `_mesma_taxa`; vendedor por `_mesmo_vendedor`;
  - troca de vendedor por beneficiário: o antigo com alvo 0 (devolve no primeiro repasse aberto **dele**), o novo com o alvo inteiro, e o congelado regravado;
  - motivos "taxa corrigida" e "correção da venda", para mais e para menos;
  - `updated_at`/`updated_by_id`; `EventLog` UTC.
- **Acréscimos** (decisão (d)):
  - **extração** de `_montar_acrescimos` (`comercial_ops.py:216-404`) em cinco passos de cerca de 30 linhas (o limite da constituição, `.specify/memory/constitution.md:43`), cada um com docstring do porquê. A lista é a mesma da R20: (1) ler os itens (`id` repetido, tipo, valor); (2) casar o bundle antigo sem `id`; (3) recusar BV pago removido ou trocado de tipo; (4) a régua do BV (somas em reais e em %); (5) montar o registro: BV (recebedor e PIX por `erros_do_bv`; o BV pago com valor e unidade da linha gravada; BV em % no cancelado), `valor_visto` e as `trocas` de recebedor e PIX. Se algum passo passar de ~30 linhas sem partir uma regra da 305 ao meio, entra uma linha no Rastreamento de complexidade com o porquê; o candidato é o (5), hoje o bloco maior (`:314-402`, cerca de 90 linhas). O vivo segue com o `delete`/`add` de `:407-411`; `verify_305` de novo **antes** de usar no cancelado;
  - `alterar_acrescimos_do_cancelado` reusa `_montar_acrescimos`: 400 `items` para BV pago ausente (`:283-294`), id repetido (`:254-256`), `valor_visto` contra o **cheio** (`:368-384`), `trocas` com `audit` de recebedor e PIX do BV pago (`:339-348`);
  - BV pago com valor ou unidade diferente → mantém o gravado, como no vivo (sem recusa); tipo diferente → 400; BV novo em % → 400 "lance em reais";
  - ramo do Superadmin em `api_set_acrescimos`: `expire(event, ["acrescimos"])` → `reaplicar_cancelado` → commit; a resposta é o detalhe.
- **Parcelas, notas e reembolsos**: o Superadmin grava pelas rotas de hoje, sem mexer no congelado.
- **Flags**: `can_edit_venda_cancelado` abre os campos.
- **Frontend**:
  - `VendaPanel.canEdit` pela flag; `VendaForm` confirma "o retido e a comissão do retido passam a <novo>";
  - `OrcamentoPanel` sem ações; `GrupoPanel` sem "Agrupar mais um" nem "Desfazer" no dia cancelado;
  - `AcrescimosPanel.canEdit`; `NotasFiscaisPanel`/`ReembolsosPanel` com a mensagem do servidor;
  - invalidações em `eventInline`/`eventOps`.

**Ao fim da fase**
- **Verde**: 16b (sem o satélite; com a variante "cheia 0" pela API: cortesia com valor e evento sem vendedor), 16c, 16d, 16e.
- **Vermelho esperado**: H5–H6.

**Riscos**
- **Transação**: chamar `reaplicar_cancelado` depois de `update_event_comercial` voltar já é outra transação; por isso o gancho.
- **Taxa**: `Float` × `Decimal` dá falso "a taxa mudou" (2.5 × 2.50).
- **Coleção velha**: `event.acrescimos` depois de gravar no lugar.
- **Extração da 305**: um passo fatiado que mude a ordem das recusas muda a mensagem do editor vivo; o `verify_305` acusa.
- **Linhas congeladas**: uma órfã de outro caminho só deixa de somar pelo "cinto" `acrescimo_id` não nulo.
- **16e**: a taxa padrão volta no `finally`. Até a 1e, a taxa padrão das Configurações não muda.

### 6. História 5: venda de vários dias (P2)

**Constrói**
- **`group_ops`**:
  - `dias_vivos(event)`, régua única de dias vivos para `_compute_kpi`, `_serialize_gastos` do principal vivo, KPI Jinja e `_group_cost`; `group_events` não muda;
  - `validar_agrupamento` e `desagrupar` travam e releem; recusam cancelado como principal, como satélite e como dia a soltar;
  - a recusa é traduzida nas **três** portas de desagrupar (`api_desagrupar_evento`, `api_remover_satelite`, que hoje viraria 500, e o Jinja `_handle_ungroup_event`) e no Jinja `_handle_group_events`;
  - docstring de `api_remover_satelite` (`:2456-2461`).
- **`passar_venda(antigo, novo, *, actor_name, agora)`**, sem commit, pelas listas `group_ops.CAMPOS_DA_PASSAGEM` e `group_ops.TABELAS_DA_PASSAGEM`:
  - T4 nas linhas antes do `UPDATE event_id`, que em lote travaria na ordem do scan;
  - `audit` por linha movida;
  - `orcamento_history_id` (coluna de `CAMPOS_DA_PASSAGEM`, que já vem de `SATELLITE_FIELDS_CLEARED`), clientes que faltam, `group_leader_id` dos dias;
  - `sale_handed_over = true` na linha `dia` do antigo 1º dia;
  - `EventLog` nos dois dias, com o retrato e as somas por tipo;
  - `expire` de `satellites`, `group_leader` e das coleções movidas.
- **`cancel_ops`, o laço**:
  - `alcance`, `novo_principal_id`, `grupo_mudou`, `so_este_dia` sem outro dia vivo (`sem_outro_dia_vivo`);
  - regime `satelite` em cada dia; `desmarcar` por dia;
  - `ao_cancelar` em cada dia (`("todos", None)`); no corte de dia que não é o principal, `("so_este_dia", None)`; na passagem, **depois** dela: `("so_este_dia", novo)`;
  - sai a recusa do líder; `resumo_impacto.grupo{…, proximo_principal}`.
- **Regime `dia`** (FR-056):
  - `venda_nova` e `sale_value_gross` na mesma proporção (`cheio × venda_nova ÷ venda`, ao centavo, `ROUND_HALF_UP`);
  - **piso da devolução do corte** (Living Spec do checklist): (pago do grupo − já devolvido − venda nova) − máx(0, pago do grupo − já devolvido − venda atual); abaixo, 400 `fields.devolucao_valor` (Parte) ou `fields.devolucao_modo` (Nada); a prévia devolve `devolucao_minima` (cenário 4);
  - `antes = estado_da_venda(principal)` → venda nova → **uma** chamada a `acompanhar_bv_da_venda` → `flush` → reconciliar o principal vivo ("Corte de dia: venda diminuiu");
  - congela antes/depois;
  - `NOTA_COMISSAO_PROPRIA_DO_DIA` marca a comissão própria do novo principal.
- **Correções em dia de grupo**:
  - `alterar_devolucao` no `dia` (decisão (e)): piso, teto e 409 `acima_do_teto`; com o principal já cancelado inteiro, também `reaplicar_cancelado(principal)` (ponto 6 da Living Spec, D28);
  - `alterar_devolucao` no `venda` em grupo: o piso soma as devoluções dos dias cortados (`dia`), fixas; a devolução aberta do principal absorve primeiro e, depois dela, as abertas dos dias `satelite`, em ordem de id (FR-017, Living Spec do checklist);
  - comprovante em dia de grupo (decisão (c)).
- **Custo sem o dia cancelado**: `_compute_kpi` (cachê `:371-379`, gastos `:380-389`, BV `:390-396`), `_serialize_gastos` do principal vivo, KPI Jinja e `_group_cost` (`:725-730`), todos por `dias_vivos`.
- **`cobranca_ops`**: desconta as devoluções.
- **Frontend**: `CancelamentoDiasBloco`; tipos `grupo?`; corpo com `alcance`, `novo_principal_id` e `venda_nova`; `onSuccess` invalidando `["event"]`; link "a venda passou para DD/MM".

**Ao fim da fase**
- **Verde**:
  - 29, 35, 37, **37b**, 38 (+ variante 38-comprovante), **38c**, 39 (+ variante: depois de cancelar o resto, "Alterar devolução" do dia refaz retido e comissão do principal), 41;
  - 42 (sem aviso e ensaio), 42b (sem a multa), 42c, 42d (sem o cachê pago);
  - as partes de satélite do 4, 16b, 17 e 21;
  - do 40, desagrupar e agrupar.
- **Vermelho esperado**: H6.

**Riscos**
- **Travas**: ordem cruzada se o corte travar o satélite antes do principal; `desagrupar` lido antes do commit tira o dia cancelado do grupo.
- **Grupo depois da passagem**:
  - `is_group_leader = len(satellites)` fica velho;
  - "líder" deixa de significar "tem dia vivo", então a FR-055 conta dias vivos explicitamente (`dias_vivos`);
  - `group_label` conta o dia cancelado (cosmético; 1c).
- **Efeitos fora do grupo**:
  - `_group_cost` mexe no CPV, no Top Vendedores, na tendência e na base EducaManto; o 41 compara `main` × branch em todos os grupos;
  - a cobrança da Home muda de regra (0 casos);
  - a virada do mês no 42c (Q15 = A, Q18 = A).
- **Devolução do dia × comissão**: o reaplicar do principal só pode rodar quando ele está cancelado em `venda`; com o principal vivo, a comissão não muda (clarify 15/10); o 38 e a variante do 39 provam os dois lados.
- **2a**: o ponto de extensão nunca grava nada nesta entrega.

### 7. História 6: ensaio, avisos, cachê pago e multa (P2)

**Constrói**
- **Recusas**:
  - `cache_pago_do_evento(event)`: escalação com talento em pago ou no banco, fora a vaga de presença (`e_vaga_de_presenca`);
  - T6; 409 `cache_pago` com `dias`, sem gravar nada (a 2a importa a mesma régua);
  - 409 `ensaio` (`event_type == "ENSAIO"`).
- **Ensaios**:
  - `delete_ensaio` (`:1791-1811`) separa `_apagar_ensaio_no_banco`: `_clear_event_side_tables`, `apagar_por_entidade("calendar_event", id)`, `delete`, sem commit. O botão e `_sair_de_show` (`:445-504`) continuam iguais;
  - id, `google_event_id`, data e local capturados **antes**; Google depois do commit, com a trava.
- **Sinos** (`notificacoes_ops`):
  - `evento.cancelado`: ENSAIO, um por pessoa **por ato**, só com ensaio, `dedupe_key = evento.cancelado:<id do evento da URL>`;
  - `evento.cancelado_escala`: CASTING sem SUPERADMIN, um por dia com escalados, link `?aba=producao`, `dedupe_key = evento.cancelado_escala:<id do evento da URL>:<dia_id>`;
  - `urgent` por `ANTECEDENCIA_URGENTE_DIAS` (= 7, `:85`) **só** no `evento.cancelado_escala`; o `evento.cancelado` não o tem (a FR-067 não o pede);
  - os dois por `resolver_destinatarios` (ativos com acesso; **não** a consulta de `notify_ensaio_team`) e na transação.
- **E-mail**: `send_removal_email` por `send_async`, depois do commit, uma vez por pessoa (título e data do principal e do 1º dia vivo), fora quem recusou e a vaga de presença. `assign_role` deixa de mandar no cancelado.
- **Elenco e multa**:
  - `event_cancellation_elenco` gravada no ato, **uma linha por escalação** (vaga × dia);
  - `lancar_multas_do_cancelado` grava o gasto pelo ORM, como `_registrar_devolucao` (aprovado, `fornecedor`, `SpecialExpense.CATEGORY_MULTA_CANCELAMENTO`, `Talent.pix_key` de `models.py:169`, PIX vazio permitido), **nunca** por `create_expense`, que nasce pendente e manda e-mail;
  - **valor vazio ou 0 é ignorado** nos dois caminhos (no ato, `multas[role_id]`; depois, `POST …/multas`); 400 `fields.multa_<id>` para negativo ou inválido, vaga fora dos dias alcançados, linha de outro evento ou multa já lançada;
  - `POST …/multas`; se, ignorados os vazios e zeros, não sobrar nenhum valor > 0, 400 `fields.multas` ("Informe a multa de ao menos um artista"), porque o endpoint existe para lançar;
  - `cancelamento.elenco?` só com a flag;
  - impacto: `ensaios`, `elenco[].role_id`, `talent_pix_informado`, `faltam_dias`, `cache_pago`;
  - `EventLog` com ensaios, multa e avisados.
- **Lugar no ato** (ordem única, seção Travas): `cancelled_at` → `ao_cancelar` → ensaios (banco), sinos e multas → `EventLog` → commit; Google (show e ensaios) e e-mail depois do commit.
- **Frontend**: recusa de cachê pago no diálogo (sem botão; aponta Gastos Extras); `MultaAoElencoBloco`; frases do ensaio e dos avisos; `LancarMultaDialog`; `useLancarMultas`; ícones do sino.

**Ao fim da fase**
- **Verde**:
  - 33, 40, 42e, 43, 44 (+ variante: corte de um dia com ensaio e depois "Cancelar todos" com ensaio → 2 sinos por pessoa da equipe de Ensaio), 45, 45b, 45c;
  - as partes que faltavam do 2b, 4, 42, 42b e 42d.
- **Agora**: os 59 cenários verdes, com todas as variantes.

**Riscos**
- **Ensaio no Google**: o ensaio que fica lá (falha ou trava) volta no próximo sync como ENSAIO órfão; isso vai ao `docs/05`, como hoje no `delete_ensaio`.
- **E-mail**: `send_async` reabre os objetos pela PK, então nunca mandar o ensaio apagado. `assign_role` manda o e-mail antes do commit (corrida rara).
- **Sinos**:
  - o sino usa SAVEPOINT; um 409 depois dele leva o aviso no rollback, o que é o comportamento desejado;
  - a `UNIQUE(user_id, dedupe_key)` é permanente (`models.py:674`) e `emitir` engole o duplicado no savepoint: uma chave pelo principal calaria o 2º sino do mesmo grupo; a variante do 44 acusa.
- **Multa por escalação**: um artista em 2 dias tem 2 campos e 2 gastos; o bloco mostra vaga e dia em cada linha para não parecer duplicado.
- **Trava de ambiente**: chave ausente = travado, então o "Cancelar ensaio" e a troca de tipo seguem sem trava (dívida 69).

### 8. Polimento

- **Portões**:
  - `npm run typecheck`, `ruff check` nos tocados (portão: nenhum erro novo; os arquivos de `app/` que a 306 toca já têm 14 na base, quickstart §6), `npm run build`;
  - verify 59/59 sem argumentos, com as variantes;
  - `retrato_main_branch.py` idêntico;
  - verifies antigos (quickstart §5);
  - tela aberta (quickstart §8, 21 itens);
  - `/speckit-converge` sem gaps.
- **Docs**: a lista "Docs" acima, inclusive `docs/00` §4 e §6 e uma linha em `docs/01` §4.3 por porta alterada.
  - **FR-074**: os textos que mentem:
    - diálogo `:68-70` e `:218-221`;
    - `eventOps.ts:131-134`;
    - docstrings de `cancel_ops` (`:147-156`, `:183-185`, `:264-265`) e de `api_cancelar_evento` (`agenda_write.py:580-586`);
    - `financeiro_read.py:188-189` e `:231-232`; `routes.py:280-282`;
    - `cobranca_ops.py:3-6` e `:104-106`; `vendas_ops.py:154-157`;
    - comentários de `models.py`; `group_ops.py:1-32`.
  - **`docs/05`**:
    - EventLog do desfazer da 267c 3 h antes (`comissoes_ops.py:358`);
    - `comissoes()` Jinja sem filtros e com `total_a_pagar` em dobro (`routes.py:1505-1541`);
    - comissão 0 na tela Jinja do cancelado (P-28);
    - guarda de pago abaixo do devolvido em dia **vivo** do grupo;
    - "pago" em lote sobre devolução recém-alterada, sem conferência de valor;
    - recibo órfão no 400/409 do `POST /api/gastos`;
    - resíduo da trava (seção Travas);
    - ensaio órfão no Google;
    - verifies não versionados de `scripts/db/`.
- **Contagem**: final no espelho, gravada na pasta.

### Matriz bundle × backend (janela de ~1 min, trocas separadas)

| Situação | Comportamento |
|---|---|
| Bundle novo, backend velho | Sem `regime`, o diálogo fica travado ("O sistema está atualizando — tente em um minuto"). Sem `cancelamento`, a tela cai no `KpiGrid`. As flags novas ausentes valem "fechado" só nos gates do cancelado; os gates que já existem usam `!== false`. `PATCH …/devolucao` e `POST …/multas` em 404/405 viram "atualizando". O `valor_esperado` no `expense` é ignorado pelo backend velho |
| Bundle velho, backend novo | Cancelar sem modo dá 400 legível. `kpi` ausente devolve `null` no `KpiGrid`. `devolucao` e `is_group_leader` ficam um ciclo. Comissões imprime o `status_label` do servidor. O BV com o cheio leva o 409 "O BV mudou…", que é a mensagem certa. A devolução marcada sem `valor_esperado` segue o comportamento de hoje. O `PagamentosPanel` velho mostra o texto fixo num 409 (aceito na janela) |

## Deploy (noite 2, sozinha)

1. **Antes do merge**:
   - branch rebaseada sobre a `main` (hoje `6356b80`, com 215b, 267c, 305 e 307), com as citações `arquivo:linha` reconferidas se a `main` andar de novo;
   - os 59 cenários, as variantes, as regressões, typecheck, ruff e build verdes; converge sem gaps; docs escritos;
   - `git status --short` limpo e `migrations/versions/` sem untracked.
2. **Build reproduzido num venv Python 3.11**:
   - `uv venv --python 3.11` + `requirements.txt`;
   - diff do `pip freeze` contra o da produção (SSH);
   - `flask db downgrade a7c3e91f4d28 && flask db upgrade && python seed.py` no `manto_local`, com `postgresql://`;
   - o verify nesse venv.

   É a lição do deploy da 303. O ensaio de migração destrutiva não se aplica.
3. **Contagem do dia em produção**, só leitura, por SSH (quickstart §2). Os números vão ao `docs/03`. Nada bloqueia o deploy, mas comunicar ao dono antes do push:
   - cancelados existentes (`legado`): a DRE do mês deles muda no deploy, porque a devolução sai dos gastos;
   - linhas `no_banco`, que passam a aparecer em Comissões;
   - marcados pela 303, que serão os primeiros cancelados;
   - BVs não pagos sem PIX, que o diálogo vai pedir;
   - grupos com o principal fora do 1º dia;
   - itens abertos de comissão de soma zero com linha de valor, que hoje somem da Planilha (`total == 0`) e passam a
     aparecer também em mês sem cancelamento (R6);
   - cancelados `legado` sem dinheiro, que hoje se excluem (inclusive pelo sync) e passam a dar 409 na exclusão (R7);
   - a Tendência do mês do evento de cada `legado`, que deixa de contar a venda e o cachê (FR-043);
   - vendas vivas com devolução lançada à mão, cuja cobrança na Home passa a descontá-la (risco aceito 16).
4. **Push** só quando o dono pedir: merge na `main` + `git push origin main`, à noite (≥ 19h BRT), em lote com nada. Backend e frontend no mesmo push. O `startCommand` não muda; nenhuma env.
5. **Depois do push**:
   - **Backend no ar**: sonda `/api/` com JSON, duas vezes (502 isolado é troca de container). Conferir o código e o `alembic_version` no container, por SSH e só leitura.
   - **Evento descartável**: título que diga que é teste, contrato anexado, **sem venda**, sem artista de verdade e sem ensaio. Cancelar com "Nada".
   - **Telas**:
     - a página de Cancelamentos mostra o evento (fica lá para sempre; risco aceito 9);
     - DRE do mês nas duas telas, **sem** a linha do retido, porque cancelado sem dinheiro fica fora (P-24);
     - Planilha do mês seguinte e Comissões sem mudança.
   - **`docs/03`**: "EM PRODUÇÃO desde …", conferido pelo endpoint.
6. **Rollback**:
   - reverter o merge, sem `downgrade`, é limpo até o primeiro cancelamento real (depois do item 5 as tabelas já não estão vazias: têm a linha do evento descartável);
   - o descartável não tem venda, comissão nem BV, então o código antigo não tem o que estragar nele;
   - depois do primeiro cancelamento real, só se corrige para a frente (`306b`): nunca `downgrade` com linha em `event_cancellations`, porque ele apaga o congelamento e nada mais se refaz. O que o código antigo faria sobre os dados novos:
     - zeraria a comissão do retido;
     - tomaria o ajuste do corte de dia (`a_pagar` com `original_id`, `event_id` no principal vivo) pela comissão do evento e o regravaria com a cheia (`_comissao_existente`, R6);
     - listaria pelo cheio o BV não pago do cancelado (`_build_bv_items`), e a Planilha da 305 deixaria marcá-lo pago por esse valor;
     - deixaria excluir o cancelado vazio, inclusive pelo sync, e o CASCADE de `event_cancellations.event_id` levaria o congelamento junto;
   - não voltam: ensaios apagados, e-mails enviados e venda passada.
7. **O dono roda**: nada.

## Ordem com os outros itens

- **Já na `main`**:
  - 303: `desmarcar`, dublê, trava;
  - 215b: a regra do cancelado vem antes;
  - 267c: item partido, desfazer, trava do lote, que ganha `order_by`;
  - 305: proporção, `travar_evento`, editor (cuja montagem esta entrega extrai e fatia).
- **1c, depois** (não pode subir antes): lê `paineis.cancelamentos`, `resumo` e `cancelados_do_periodo`, e reusa os nomes `pode_editar_venda_do_cancelado`, `can_edit_venda_cancelado`, `evento.cancelado_escala`, `group_ops.dias_vivos` e os `CODIGO_*` (tabela do data-model §6). Os arquivos em comum vão uma branch de cada vez.
- **1e**: reaproveita `primeiro_repasse_aberto`, a reconciliação, os predicados, `MOTIVOS_AJUSTE_COMISSAO` e a guarda do resync; roda de novo 9, 38 e 42b.
- **2a**: importa `cache_pago_do_evento`, a recusa `ensaio` e `cancel_ops.ao_cancelar`; o bloco "o que foi pedido" do diálogo é dela.
- **2b** (noite 7): `ensaios_so_deste`, a linha do vendedor EducaManto e `educamanto_comissao_vendedor` em `group_ops.CAMPOS_DA_PASSAGEM`/`TABELAS_DA_PASSAGEM`; roda de novo 11, 16c, 42c e 44.
- **3b**: respeita o cancelamento de vários dias.
- **6a**: as colunas de canal entram em `group_ops.CAMPOS_DA_PASSAGEM`, e a migration dela encadeia depois desta.
- **6b**: a categoria nova (`SpecialExpense.CATEGORY_MULTA_CANCELAMENTO`) entra na lista dela.

## Rastreamento FR → fase

| FR | Fase | Onde | Cenários |
|---|---|---|---|
| 001 regra única | Fund. + H2 (+H5) | `cancel_ops` resumo/ato/laço | 2, 2b, 37, 38 |
| 002 congelar | Fund. (modelo) + H2 (+H5 `dia`, H6 elenco) | `_congelar` | 2, 16b, 38, 45c |
| 003 regimes | Fund. (`legado`) + H2 (`venda`, `virtual`) + H5 (`satelite`, `dia`) | constantes, resumo | 2, 17, 21, 37, 38 |
| 004 retido | Fund. | `filtro_devolucao`, resumo, ids do grupo por consulta | 2, 16, 32, 39 |
| 005 resumo único | Fund. (+consumidores H1–H3) | `resumo(s)_cancelado(s)` | 12, 25 |
| 006 só Superadmin cancela | H2 | `api_cancelar_evento` | 6, 28 |
| 007 Tudo/Parte/Nada | H2 | validação | 3, 4 |
| 008 devolução aprovada | H2 | `_registrar_devolucao` | 2, 36 |
| 009 imposto | H2 | validação (sem nota → 400), congelado | 4, 21 |
| 010 PIX do BV | H2 | `_validar_pix_do_bv` | 4 |
| 011 prévia | H1 (`simular`) + H2 | `previa_cancelamento` | 2 e 8 (variante prévia = execução), 4, 6 |
| 012 recusas 409 | H2 | validação, UNIQUE, `CODIGO_*` | 3, 5 |
| 013 ordem atômica | H2 (+T6 na H6) | Travas | 5, 30 |
| 014 marcado | H2 | `desmarcar` antes | 2b, 35 |
| 015 Google depois do commit | H2 (+ensaios na H6) | remoção com trava | 31, 37, 43 |
| 016 histórico UTC | H2 (+H5, H6) | `EventLog` sem `created_at` | 2 |
| 017 alterar devolução | H2 (`venda`) + H5 (`dia`) | `alterar_devolucao` | 15, 38, 39 (variante do principal cancelado depois) |
| 018 comprovante no cancelado | H2 (+grupo na H5) | `reaplicar_por_dinheiro` | 16, 37b, 38 (variante 38-comprovante) |
| 019 trava de Gastos | H2 | `gastos_ops` + `_write`, porta a porta | 18, 36 |
| 020 tipo cliente | H2 | `_validate_expense_data` | 18 |
| 021 exclusão e orçamento | H1 (trava) + H2 (recusa) | `_delete_event_flow`, `_apagar_vazio`, `set_event_orcamento` | 19 |
| 022 tela do cancelado | H2 (+link na H5) | `ResultadoCancelamento` etc. | 25; telas 7–13 |
| 023 diálogo | H2 (+H5 dias, H6 multa) | `ExcluirEventoDialog` + blocos; o bloco "o que foi pedido" é da 2a (nada aqui, nem prop) | 3, 4; telas 1–6 |
| 024 marcado com 2 saídas | H2 | `EventHeader`, banner | tela 14 |
| 025 página de Cancelamentos | H2 | `listar_cancelamentos`, página | tela 21 |
| 026 princípios de tela | H2–H6 | todas | telas |
| 027 comissão cheia | Fund. | `_base_da_comissao` (casca intocada) + `comissao_cheia_do_evento` (portão) | 1 (casca), 10, 16b (variante cheia 0) |
| 028 comissão do retido | Fund. (pura) + H1 | `comissao_do_retido` | 7, 32 |
| 029 taxa congelada | Fund. (coluna) + H2 + H4 | congelado, `reaplicar` | 16e |
| 030 invariante por beneficiário | H1 | `reconciliar_…` | 7–12 (+ variante 9/10-desfazer) |
| 031 primeiro repasse aberto | H1 | `primeiro_repasse_aberto`, predicados | 8, 13, 14 |
| 032 data intocada | H1 | reconciliação | 7, 11 |
| 033 motivo e vínculo | Fund. (`MOTIVOS_AJUSTE_COMISSAO`) + H1 | nota por prefixo | 16c |
| 034 resync não toca | H1 | guarda + `SKIP LOCKED` | 12, 30 |
| 035 órfão por predicado | H1 | `filtro_estorno_orfao` | 14 |
| 036 estorno da exclusão | H1 | `aplicar_estorno_comissao` | 14b |
| 037 "No banco" em Comissões | H1 | `comissoes_ops`, página | 13; tela 16 |
| 038 passado quieto | Fund. (todas) | retrato | 26 |
| 039 BV do retido | Fund. (pura) + H1 | `bv_do_retido`, `paid_amount` | 16, 17 (+ variante 16/17-`paid_amount`) |
| 040 BV na Planilha | H1 (+devolução na H2) | `bv_da_planilha`, `marcar_status_do_bv`, `paid_amount`; `valor_esperado` no `bv` e no `expense` (409 `valor_mudou`) | 17, 36 |
| 041 DRE no mês do cancelamento | H3 | `_compute_drg`, API | 12 e 32 (parte da DRE), 20, 21 |
| 042 gastos sem a devolução | H3 | `dre_ops.gastos_extras_do_periodo` | 20, 21, 38 |
| 043 painéis | H3 | `dashboard()`, API | 21, 22 |
| 044 fonte única do período | Fund. + H3 | `cancelados_do_periodo` | 21, 24 |
| 045 `paineis.cancelamentos` | H3 | API | 20 |
| 046 retido como venda | H3 | `build_kpis`, desempenho, clientes | 22, 24, 16c |
| 047 regra única de edição | H2 (recusas) + H4 (Superadmin) | `pode_editar_…`, `_recusa_do_cancelado`; Jinja para todos | 16, 16b, 16c, 16d, 19, 28 |
| 048 dados abertos | H2 (orçamento travado) + H4 | portas (a)–(h) | 16b, 16d, 19 |
| 049 recongelar | H4 (+comprovante e devolução na H2) | `reaplicar_cancelado` | 16b, 16d |
| 050 taxa corrigida | H4 | idem | 16b, 16e |
| 051 troca de vendedor | H4 | reconciliação por beneficiário | 16c |
| 052 acréscimos no lugar | H2 (no-op/409) + H4 | `alterar_acrescimos_do_cancelado` sobre `_montar_acrescimos` fatiado | 16d, 19 |
| 053 reembolsos, parcelas e notas | H2 (409) + H4 | regra única | 16b, 16d |
| 054 cancelar todos | H5 | laço, T1 | 35, 37 |
| 055 alcance | H5 | validação, `dias_vivos` | 42d |
| 056 só este dia | H5 | regime `dia` | 38, 39 |
| 057 corte × comissão viva | H5 (+regra (b) na H1) | reconciliação no principal vivo | 38, 38c, 39 |
| 058 passagem no 1º dia | H5 | `passar_venda`, `sale_handed_over` | 42, 42b, 42d |
| 059 mesma linha | H5 | `group_ops.CAMPOS_DA_PASSAGEM`/`TABELAS_DA_PASSAGEM` | 42 |
| 060 datas na passagem | H5 | idem; `_sync` de hoje | 42c |
| 061 grupo | H5 (+tela do cancelado na H2) | `group_ops.dias_vivos`, KPI, `_serialize_gastos`, `_group_cost`, cobrança | 29, 40, 41 |
| 062 ponto da 2a | H2 (avulso) + H5 | `cancel_ops.ao_cancelar` | 2, 38, 42 (chamada registrada) |
| 063 cachê pago | H6 | `cache_pago_do_evento`, T6 | 33, 40 |
| 064 ENSAIO 409 | H6 | validação | 40 |
| 065 ensaio cai | H6 | `_apagar_ensaio_no_banco` | 42e, 43 |
| 066 e-mail ao elenco | H6 | `send_async` depois do commit | 44 |
| 067 sino à equipe de Ensaio | H6 | `notificacoes_ops`, `dedupe_key` pelo ato | 44 (+ variante dois sinos) |
| 068 sino ao Casting | H6 | idem, um por dia | 44 |
| 069 sem e-mail de remoção | H6 | `assign_role` | 45c |
| 070 elenco do ato | H6 | `event_cancellation_elenco`, uma linha por escalação | 44, 45c |
| 071 multa no ato | H6 | `lancar_multas_do_cancelado` (vazio/0 ignorado) | 4, 45 |
| 072 multa depois | H6 | `POST …/multas` (vazio/0 ignorado; nenhum valor > 0 → 400 `fields.multas`) | 45b, 45c |
| 073 excluir usuário | H2 | `delete_user` | 34 |
| 074 textos que mentem | Polimento (+cada fase) | docstrings e telas | `verify_303` c12 |

## Rastreamento de complexidade

| Violação ou desvio | Por que é necessário | Alternativa mais simples rejeitada porque |
|---|---|---|
| Ramos novos em handlers Jinja vivos: despachante `event_detail`, `delete_calendar_event`, grupo, `_compute_drg`/`dashboard()`, `_build_*_items`, `set_payment_status` (BV e gasto), `set_commission_status` (guarda de uma linha), `/vendas/`; e uma linha em `dashboard.html` | A FR-040/041 exige Planilha e DRE "nova e antiga" iguais ao centavo, e a P-27/FR-047 exige que o Jinja não fure a regra única nem a invariante por beneficiário | Desligar ou limpar o Jinja é a remoção pausada pelo dono (`docs/PARADA_REMOCAO_JINJA.md`); deixar o ramo velho faria a DRE antiga mostrar −600 e deixaria o Jinja cancelar a linha do retido |
| `dre_ops.py` importa helpers de `financeiro/routes.py` por import tardio (núcleo → routes) | Uma conta só para a API e o Jinja | Mover `_compute_drg`/helpers está proibido pela PARADA |
| Comissão cheia em duas camadas (`_base_da_comissao` + `comissao_cheia_do_evento`) ao lado da casca `_event_commission` | A FR-027 zera cortesia e evento sem vendedor, mas a casca não pode mudar número (cenários 1 e 23): hoje o evento sem vendedor tem comissão na DRE | Pôr o portão na casca mudaria a DRE de hoje; deixar a cheia sem portão congelaria comissão em cortesia com valor (FR-049) |
| Mudanças fora da 306 por concorrência: os oito ajustes da seção Travas ("Fora da 306", a lista única) | Sem elas, a ordem evento → linhas da 306 fecha deadlock (40P01 = 500) ou deixa o resync regravar a linha do retido (cenário 30) | Travar só o evento no resync seguraria até 72 eventos no GET; tratar só o 40P01 como 409 não evita a perda de dado |
| `_sync_commission_payment` ganha a regra do ajuste vivo (FR-057) | O desfazer da 267c no principal vivo depois do corte daria desconto em dobro (Σ 50 ≠ 75) | Recusar o desfazer contraria a 1e-Q5 = A; reconciliar dentro do desfazer faria o financeiro importar o núcleo do cancelamento |
| Coluna `paid_amount` em tabela nova (além do "BV cheio" da spec) | Sem ela o pago depois do ato seria reescrito por correção, e o `valor_esperado` da 305 daria 409 eterno | Regravar `amount_brl` quebra `_event_bv_total`, `original_amount`, o editor da 305 e o desfazer; coluna em `event_acrescimos` é vetada pela spec |
