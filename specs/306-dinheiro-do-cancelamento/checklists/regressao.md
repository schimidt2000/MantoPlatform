# Checklist: o que não pode quebrar — qualidade dos requisitos

**Purpose**: portão antes do `/speckit-tasks` — a spec, o plan, a research, o data-model e os contratos nomeiam o
que a 303, a 215b, a 267c e a 305 já entregaram nos mesmos caminhos, dizem que continua igual e como isso se
prova? (testa a escrita, não o código)
**Created**: 2026-10-16
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [research.md](../research.md) ·
[data-model.md](../data-model.md) · [contracts/api.md](../contracts/api.md) · [quickstart.md](../quickstart.md)

## Completude

- [x] CHK001 A casca da comissão está declarada intocada — `_event_commission` vira casca de `_base_da_comissao`
  com o corpo de hoje, as 8 chamadas nomeadas, e o portão do beneficiário (cortesia/permuta, sem vendedor) fica
  só na camada nova `comissao_cheia_do_evento` —, de modo que nenhum consumidor do evento vivo mude número,
  inclusive o evento sem vendedor na DRE? [Spec FR-027, Clarifications (`/speckit-plan`) 5, cenário 1, SC-002;
  Plan Constitution IV, Fundação 5, Rastreamento de complexidade; Research R0, R4]
- [x] CHK002 A DRE e a Tendência dos meses sem cancelamento estão definidas como idênticas ao centavo entre `main`
  e branch, na API e no Jinja, com o que sai da comparação de propósito (ticket médio do Jinja; mês com `legado`,
  listado à parte) e a régua que evita a diferença falsa (linha pela quantidade de cancelados, nunca
  `Decimal("0.00")`; relógio fixo; `ensure_recurring_entries` neutralizado)? [Spec FR-041, FR-043, cenário 23,
  SC-002; Plan Restrições, Fundação 2, H3 riscos; Research R21, R28; quickstart §3]
- [x] CHK003 O que a 267c entregou na Planilha e em Comissões está declarado igual — item partido aberto × `:pago`
  (o `:pago` de soma 0 continua escondido), lote só nas linhas abertas, desfazer só do Superadmin e com motivo, a
  recusa de pago → x no `set_commission_status` — e o que entra por cima está listado como aditivo ou interno
  (`commission_lines?`, `order_by(id)`, eventos travados antes das linhas no desfazer, guarda de uma linha no
  cancelado)? [Spec leitura 11, RBAC `set-status` ("Comissão: contrato igual"), Dependências 267c; contracts §17,
  §21; Plan Travas ("Fora da 306" 1–2); Research R6, R14, R29]
- [x] CHK004 O que a 305 entregou no editor de acréscimos está declarado igual no evento vivo — casamento por
  `id`, `valor_visto`, BV pago intocável e 400 `items` quando ele some do corpo, `delete`/`add` do vivo,
  `travar_evento` antes dos acréscimos — e o cancelado vai por um caminho próprio, que grava no lugar? [Spec
  FR-052, leitura 6, Dependências 305; contracts §8 ("Vivo: inalterado"); data-model §9 (`event_acrescimos`);
  Research R20, R29]
- [x] CHK005 Toda mudança intencional sobre dado que já existe está listada para o `docs/03` e para o aviso ao
  dono antes do push? [Gap; Plan H3 riscos ("Mudanças de comportamento intencionais"), Deploy 3; quickstart §2,
  §9; Research R6, R7]
  → falta: a lista (ticket médio do Jinja, `sale_count`, ficha da cliente) e o aviso ao dono (`legado`,
  `no_banco`, marcados, BV sem PIX, principal fora do 1º dia) não trazem o item aberto de comissão de soma zero
  com linha de valor. Hoje ele some por `total == 0` (`financeiro/routes.py:951-952`) e passa a aparecer na
  Planilha também em mês sem cancelamento (R6), embora a contagem já o conte. Também falta o cancelado `legado`
  sem dinheiro, que hoje se exclui (R7) e passa a dar 409.
  → resolvido em 16/10: Lista única nas três partes (plan H3, plan Deploy 3, quickstart §9): + item aberto de soma zero (R6), + `legado` sem dinheiro que deixa de se excluir (R7, inclusive pelo sync), + Tendência do mês do evento de cada `legado`, + cobrança da Home de venda viva com devolução lançada à mão.
- [x] CHK006 O rollback assimétrico diz até quando reverter o merge é limpo, por que o `downgrade` fica proibido
  depois e tudo o que o código antigo faria sobre os dados novos? [Gap; Spec cabeçalho, Riscos aceitos 8; Plan
  Deploy 6; data-model §10 (docstring); quickstart §9]
  → falta: a lista para em três pontos: a comissão do retido zerada, o congelamento apagado e o que não volta
  (ensaios, e-mails, venda passada). Não diz que o `_comissao_existente` antigo toma o ajuste do corte de dia
  (`a_pagar` com `original_id` e `event_id` no principal vivo) pela comissão do evento e o regrava com a cheia,
  o efeito que a R6 descreve. Também não diz que o `_build_bv_items` antigo volta a listar pelo cheio o BV não
  pago do cancelado, e que a 305 antiga deixa marcá-lo pago por esse valor.
  → resolvido em 16/10: Risco aceito 8 da spec, plan Deploy 6, data-model §10 e quickstart §9: até quando é limpo (o descartável não tem dinheiro), por que o `downgrade` fica proibido e o que o código antigo faria (ajuste do corte regravado com a cheia, BV pelo cheio, exclusão do cancelado vazio com CASCADE).
- [x] CHK007 A migration está escrita como só `create_table` — três tabelas, nenhuma coluna, índice ou default em
  tabela existente, `down_revision = "a7c3e91f4d28"`, `downgrade` das filhas para a mãe — e o código anterior está
  declarado capaz de ler e gravar o banco migrado na janela do deploy? [Spec cabeçalho, Entidades; Plan Stack,
  Modelo; data-model §9, §10; Research R1; quickstart §4]

## Clareza

- [x] CHK008 "Gate sem mudança" está escrito porta a porta, com o gate de hoje nomeado (`_can_delete`,
  `_can_create_event`, `_can_manage_sale`, `_can_edit_event`, `_is_superadmin`, `_can_group`,
  `_require_financeiro`) e quem passa nele, para que a regra "passa no gate e não é Superadmin → 409 `cancelado`;
  não passa → 403 como hoje" seja testável sem ler o código? [Spec FR-047, RBAC; contracts §1, §6–§17; Research
  R19]
- [x] CHK009 A soma das flags da 215b (`pode_mudar_taxa`, `pode_trocar_vendedor`) com `can_edit_venda_cancelado`
  está escrita como restrita ao evento cancelado em todos os artefatos? [Ambiguity; Plan tabela de arquivos
  (`app/api/agenda_read.py`), H2 "Detalhe"; contracts §5; Research R19; Spec Dependências 215b]
  → falta: o plan diz só "passam por um E com `can_edit_venda_cancelado`" / "∧ flag", sem "no cancelado". A flag
  é `cancelado && is_superadmin` (contracts §5), então essa leitura apagaria as duas flags em todo evento vivo e
  quebraria a 215b. Os contracts §5 e a R19 dizem "no cancelado"; o plan precisa dizer o mesmo.
  → resolvido em 16/10: Plan (tabela de arquivos e H4) e R29: o E com `can_edit_venda_cancelado` só no cancelado; no vivo, as flags da 215b; o cenário 25 confere as duas no vivo.
- [x] CHK010 Está claro se as portas de dinheiro (a)–(h) passam a tomar a T1 (`travar_grupo`, o grupo inteiro em
  `FOR UPDATE`) também no evento **vivo**, para decidir a recusa, e o que isso muda no caminho de hoje?
  [Ambiguity; contracts preâmbulo "Trava", §9, §10, §11; Plan H2 ("sempre depois de T1"); Research R13]
  → falta: o preâmbulo dos contracts fala de "toda porta de dinheiro do cancelado". A §9 e a R13 travam o grupo
  antes de saber se o evento está cancelado, ou seja, também no vivo, com `grupo_mudou` e `tente_de_novo`
  possíveis num comprovante de evento vivo. A §10, a §11 e o RBAC da spec não dizem se reembolsos, parcelas e
  notas travam. Falta dizer, porta a porta, se o vivo trava, que a resposta e a ordem das recusas do vivo seguem
  as de hoje e qual cenário confere a porta viva depois disso.
  → resolvido em 16/10: FR-053 "Travas no evento vivo", preâmbulo dos contratos, §10, §11 e a tabela de ordem do plan: comprovante trava o grupo também no vivo; reembolsos, parcelas e notas travam só o evento; no vivo, respostas e ordem de hoje; variante 16-vivo.
- [x] CHK011 "A extração de `_montar_acrescimos` é neutra no vivo" está definida de forma verificável: as cinco
  fatias com a lista fixa, o vivo seguindo com o `delete`/`add`, a ordem das recusas e as mensagens do editor
  iguais, e o `verify_305` como prova antes de a montagem servir ao cancelado? [Plan Constitution II, H4
  (Acréscimos, riscos); Research R20; contracts §8; quickstart §5]
- [x] CHK012 O 409 de valor divergente da 305 no `set-status` do BV está escrito com o que muda —
  `codigo: "valor_mudou"`, comparação com `bv_da_planilha` em vez de `amount_brl`, evento travado antes do
  acréscimo — e com o que fica: a frase, a resposta `{status}` e o mesmo resultado no evento vivo, onde
  `bv_da_planilha` = `amount_brl`? [Spec FR-040, RBAC `set-status`; contracts §17, §22; Research R8 (tabela), R9]
- [x] CHK013 O que a 303 entregou está separado do que muda? Ficam a marca pelo sync, o `devolver-ao-google` (com
  o `codigo: "cancelado"` dele, que não se confunde com o `CODIGO_EVENTO_CANCELADO`), o `_apagar_vazio`, que só
  apaga evento vazio, o dublê e a `CALENDAR_SUPPRESS_EVENT_WRITES` lida a cada chamada (chave ausente = travado).
  Mudam a recusa do marcado, que sai do cancelar e fica na exclusão, o motivo `cancelado` no `desmarcar` e a
  trava, que passa a cobrir o cancelamento, mas não o "Cancelar ensaio". [Spec FR-014, FR-015, Dependências 303;
  Research R1, R7, R23; contracts §13, §20; quickstart §5 (`verify_303`)]

## Consistência

- [x] CHK014 As regressões `main` × branch são as mesmas na spec, no plan e no quickstart, e cada uma tem cenário
  e fase em que fecha? [Gap; Spec SC-002, §Harness; Plan Constitution IV, H5; Research R22, R28; quickstart §1
  (tabela B0–B6)]
  → falta: das cinco do SC-002, as cobranças da Home sem devolução não têm número na tabela dos 59, nem variante,
  nem bloco B0–B6. A mudança de `cobranca_ops` é da H5, e o 41 só confere a data do grupo e as comissões dos
  grupos.
  → resolvido em 16/10: SC-002 reescrito com seis regressões e o cenário de cada uma; o 41 ganhou a regressão das cobranças da Home sem devolução; quickstart B0 a roda desde a Fundação.
- [x] CHK015 A lista das mudanças fora da 306 por concorrência é uma só nos artefatos? [Conflict; Plan Resumo
  ("quatro ajustes pequenos"), Travas ("Fora da 306", oito itens), Rastreamento de complexidade (cinco); Research
  R24 (oito itens)]
  → falta: o Resumo do plan fala em quatro ajustes, a seção Travas e a R24 listam oito, e o Rastreamento de
  complexidade, cinco. Falta uma lista só, que os outros citem.
  → resolvido em 16/10: Lista única = seção Travas do plan (oito itens), que a R24 repete; o Resumo e o Rastreamento de complexidade passam a citá-la.
- [x] CHK016 A ida e volta da migration tem um lugar e um comando só? [Conflict; data-model §10 ("Antes do
  push"); Plan Fundação 4, Deploy 2; quickstart §4, §7]
  → falta: o data-model manda `upgrade` + `downgrade -1` + `upgrade` "num banco descartável restaurado do dump";
  o plan e o quickstart mandam `downgrade a7c3e91f4d28` → `upgrade` no `manto_local`, com as três tabelas vazias
  depois da limpeza do verify. Falta escolher um.
  → resolvido em 16/10: Lugar único = quickstart §4, no `manto_local` depois da limpeza do verify; data-model §10 aponta para lá; o §7 o repete no venv 3.11.
- [x] CHK017 A ordem "gate → satélite → 409 `cancelado` → 215b e checagens de campo" é a mesma em toda porta onde
  a 306 encontra a 215b? [Conflict; Research R19 ("Ordem em toda porta"); contracts §6, §7; Spec RBAC
  (`PATCH /api/events/<id>`)]
  → falta: a R19 dá a regra para toda porta, com o 409 antes das checagens de campo. Já os contracts §7 e o
  RBAC da spec põem o 400 de `_validate_event_core` antes do 409 no `PATCH /api/events/<id>`, que é o
  comportamento de hoje. Falta a R19 registrar essa exceção.
  → resolvido em 16/10: R19 registra a exceção única: no `PATCH /api/events/<id>`, o 400 de `_validate_event_core` vem antes do 409 (contracts §7).
- [x] CHK018 A B10 da 305 (a venda que muda leva o BV junto, uma vez) está declarada igual nos três escritores
  vivos (`update_event_comercial`, `_gravar_venda_da_edicao`, Jinja comercial)? Só muda a releitura de
  `is_cancelled` depois do `travar_evento` de cada um, e o corte de dia chama `acompanhar_bv_da_venda` uma vez,
  sem passar por `update_event_comercial`. [Spec FR-056, Dependências 305; Plan Travas ("Fora da 306" 5), H5;
  Research R15, R19, R29; contracts §6]
- [x] CHK019 Os verifies antigos a rodar de novo são os mesmos na spec, no plan, na research e no quickstart, com
  a fase em que cada um pode quebrar primeiro? A lista: `verify_303` (c12 e `MSG_MARCADO`) e `verify_267`
  (`:278-289`) reescritos; `267b`, `267c`, `299`, `205`, `215b`, `305`, `266`, `258` e `256` de novo, com o
  `verify_305` duas vezes (H1 e H4). [Spec §Verifies antigos; Plan Contexto técnico, Scripts e verifies, H1;
  Research R28; quickstart §5]

## Cobertura

- [x] CHK020 A regressão `main` × branch alcança o que a H3 reescreve fora da DRE e da Tendência nos meses sem
  cancelamento: Top Vendedores, Receita por Tipo, Recebimentos Previstos, NF a emitir, indicadores, Dashboard
  Comercial, `/admin/desempenho`, ficha da cliente e Performance da Home? [Gap; Spec SC-002, cenários 22, 24;
  Plan H3; quickstart §3]
  → falta: o `dre_retrato.py` compara só DRE e Tendência, e o 22 e o 24 conferem só o mês do cancelamento. O
  `dashboard()` muda em `:375-392` e `:469-503`, a API em `:341-363` e `:428-465`, e mudam também `build_kpis`,
  `api_admin_desempenho`, `client_ops` e `compute_performance`. Falta a comparação dos meses sem cancelado, ou a
  regra escrita de que cada bloco só muda com cancelado no período, com a mutação que acusa.
  → resolvido em 16/10: O retrato vira `retrato_main_branch.py` e o cenário 23 cobre DRE (API e Jinja), Tendência, painéis, Dashboard Comercial, desempenho, ficha, lista e métricas de clientes, Performance da Home, Comissões e Planilha; mutação da condição da quantidade.
- [x] CHK021 Há regressão `main` × branch de Comissões (KPIs, `by_seller`, `month_status`) e dos itens de comissão
  da Planilha (`S:C`, `S:C:pago`) nos meses sem cancelamento, como há para os itens de BV, com as mudanças de
  propósito (`sale_count`, soma zero no aberto) à parte? [Gap; Spec SC-002, SC-005, cenários 13, 26; Research
  R6; quickstart §1]
  → falta: o SC-002 e o harness (1, 14b, 17, 20, 23, 41) não incluem Comissões nem esses itens. O 13 compara
  Planilha × Comissões só num vendedor descartável, e o 26 retrata linhas, não telas. Mesmo assim, `total_month`,
  `_month_scoped_query` com `no_banco`, o predicado novo de `month_status` e o `continue` do builder mudam código
  que lê os meses de hoje.
  → resolvido em 16/10: Comissões (KPIs, `by_seller`, `month_status`) e os itens de comissão e BV da Planilha entram no cenário 23 e no SC-002, com `sale_count` e o item de soma zero listados à parte.
- [x] CHK022 O passado quieto está definido de forma testável: o retrato de todas as linhas de comissão do espelho
  antes e depois do verify e de abrir Comissões e Planilha (com o resync novo), os eventos e estornos nomeados
  (270, 294, 311, 405, 62, 69, 203; 151 e 211) e a contagem que só lê? [Spec FR-038, SC-011, cenário 26; Plan
  Fundação 3; quickstart §2]
- [x] CHK023 O gêmeo Jinja tem definido que, no evento vivo, nada muda além da trava? O despachante só recusa o
  cancelado, marcar BV passa pela função única com o mesmo resultado e `_build_bv_items` usa `bv_da_planilha`,
  que no vivo é o valor de hoje. A regressão dos itens de BV passa pelas duas Planilhas. [Spec FR-040, FR-047,
  cenário 17 ("API e Jinja"); contracts §21; Research R8, R9; Plan Rastreamento de complexidade]

## Não funcionais (concorrência e deploy)

- [x] CHK024 A ordem evento → dependentes está escrita para todo escritor que cruza as tabelas do ato, inclusive
  os de fora da 306 (`set_event_clients`, `delete_client`, `sync_events`), com o que o deadlock residual vira em
  cada um? [Gap; Plan Travas; data-model §8.10, §9; Research R24, Riscos aceitos 2; contracts §20]
  → falta: o plan e a R24 tratam o 40P01 como 409 `tente_de_novo` só nos endpoints da 306 e nomeiam o
  `sync_events`. Não nomeiam o `set_event_clients` (`event_ops.py:1244`), que já trava o evento antes dos
  vínculos e é compatível, nem o `delete_client` (`client_ops.py:238`). O `UPDATE calendar_events … WHERE
  client_id` dele é em lote e sem `ORDER BY id`, então pode cruzar com a T1 num grupo cujos dias têm a mesma
  contratante, e com a passagem, que move `event_clients` (data-model §9). Falta dizer se ele fica como resíduo
  aceito (500 raro) ou ganha a ordem.
  → resolvido em 16/10: Plan Travas e R24: `set_event_clients` compatível; `delete_client` como resíduo aceito (409 `tente_de_novo` do lado da 306, 500 raro do lado dele, rollback inteiro), nomeado no risco aceito 2 da research.
- [x] CHK025 O resync com `SKIP LOCKED` está definido por completo? Eventos em ordem de id,
  `FOR NO KEY UPDATE SKIP LOCKED` (que não segura o INSERT de comprovante), releitura de `cancelled_at`, evento
  travado pulado, commit por evento e a guarda do cancelado logo depois do retorno da Loja Virtual, sem esperar o
  ato e sem regravar a linha do retido. [Spec FR-034, cenários 12, 30; Plan Travas ("Fora da 306" 4), H1,
  Rastreamento de complexidade; Research R6, R24]
- [x] CHK026 A matriz bundle × backend cobre os dois sentidos para cada contrato que muda? Isso inclui os campos
  novos opcionais no TS, o `!== false` só nos gates que já existem, as flags só do cancelado por valor
  verdadeiro, os 404/405 dos endpoints novos como "atualizando", o `kpi` ausente, o `valor_esperado` no
  `expense` (ignorado pelo backend velho, ausente no bundle velho), o `codigo` desconhecido caindo em
  `e.message`, os campos que ficam por um ciclo e os efeitos de número na janela (cards de Comissões, Receita
  Bruta sem a linha do retido). [Plan Matriz bundle × backend, H1 e H3 riscos; Research R26; contracts
  preâmbulo, §22; Spec casos de borda, P-21, Riscos aceitos 6–7]
- [x] CHK027 O deploy está escrito com os passos que protegem a produção de hoje? Build num venv 3.11 (o
  `startCommand` roda `flask db upgrade`), `create_app()` com os mappers configurados (`foreign_keys=` em toda
  relação), contagem só leitura antes, push sozinho à noite com backend e frontend juntos, sonda que separa
  backend novo de antigo (401 × 404 no `PATCH …/devolucao`), evento descartável sem venda e o que dizer ao dono.
  [Plan Stack, Deploy, Fundação riscos; data-model §10; quickstart §7, §9; Spec Premissas "Deploy", SC-014]

## Dependências

- [x] CHK028 A base (`d855d1a`, "já com 303, 215b, 267c e 305") e as citações `arquivo:linha` do HEAD estão
  conferidas contra a `main` de hoje? [Gap; Spec cabeçalho, Dependências; Plan nota "Base", Deploy 1;
  quickstart §9]
  → falta: a `main` já recebeu a 307 (merge `6356b80`, em produção desde 16/10 ~01:25). Ela mexe em
  `app/calendar/orcamento_evento_ops.py` (`travar_evento` de `:776` para `:788`, `set_event_orcamento` de `:923`
  para `:935`), em `app/orcamento/quote_ops.py` (`bv_que_acompanha` de `:55` para `:58`) e em
  `app/calendar/routes.py`, com deslocamento a partir de `:2832` que chega a +22 em `_delete_event_flow`
  (`:4326` → `:4348`) e em `delete_calendar_event` (`:4452` → `:4474`). O plan e o quickstart pedem rebase
  "sobre a main, que já tem 303, 215b, 267c e 305". Falta nomear a 307, reconferir as citações depois do rebase
  e pôr o `verify_307` na lista do quickstart §5.
  → resolvido em 16/10: Rebase sobre `6356b80` (307) em 16/10; base nomeada na spec, no plan, na research e no quickstart; 19 citações remapeadas por script contra o diff da 307 e conferidas por amostra; `verify_307` no quickstart §5.
- [x] CHK029 A lista de verifies antigos cobre todo núcleo de outra feature que a 306 altera, e não só os "arquivos
  em comum"? [Gap; Spec §Verifies antigos; quickstart §5; contracts §12, §20]
  → falta: não entram o `verify_273` e o `verify_301`, embora o 409 novo em `set_event_orcamento` venha antes
  da autoria da 301 (contracts §12). O 273 aparece só dentro do `--regressao` do `verify_305`, que o quickstart
  §5 manda rodar sem ele. Faltam também o `verify_272` (o catálogo `DESTINATARIOS_POR_KIND` ganha dois kinds), o
  `verify_238` (`assign_role` ganha a condição do e-mail) e o `verify_271` (a `GET /api/dashboard`, onde mudam a
  Performance e a cobrança da Home).
  → resolvido em 16/10: `verify_273` (base 8/15), `verify_301`, `verify_272`, `verify_238`, `verify_271` e `verify_307` entram na spec, no plan, na R28 e no quickstart §5, com a fase de cada um.
- [x] CHK030 As dependências para a frente estão fixadas? A 1c não sobe antes e reusa os nomes da tabela única do
  data-model §6; a 1e, a 2a, a 2b, a 3b, a 6a e a 6b sabem o que herdam e quais cenários daqui rodam de novo; e
  os arquivos em comum vão uma branch de cada vez. [Spec Dependências, §"Cenários daqui que outras entregas
  rodam de novo"; Plan "Ordem com os outros itens"; data-model §6]

## Rodada do cético (16/10): o que estava marcado e não estava escrito

- [x] CHK031 O caminho vivo do `PUT …/acrescimos` está igual nos contratos e na research? [contracts §8; Research R20]
  → resolvido: no vivo, sem T1 (a 305 já trava dentro de `substituir_acrescimos`); a corrida que relê cancelado vira 409 `estado_mudou`, nunca 200 sem gravar; a tabela de códigos da spec cita a porta.
- [x] CHK032 A R19 contradizia os contratos sobre as outras portas vivas e não nomeava a B10 da 305? [Research R19; Spec Dependências 305]
  → resolvido: a R19 diz o que cada porta viva faz ao reler cancelado (409 `cancelado`, `flash`, 409 `estado_mudou`), e a B10 está nas Dependências 305 da spec.
- [x] CHK033 O que fica igual da 267c (lote só nas abertas, desfazer do Superadmin com motivo, item de soma zero no lote) está escrito? [Spec Dependências 267c]
  → resolvido.
- [x] CHK034 Os meses que saem do retrato por causa de um `legado` estão nomeados? [quickstart §3; plan Fundação 2]
  → resolvido: o do `cancelled_at`, o do `expense_date` de cada devolução e, só na Tendência, o do evento.
- [x] CHK035 O gate do orçamento está nomeado, e o FINANCEIRO no cancelado leva 409? [contracts §12; Spec RBAC; verify 19]
  → resolvido: `_can_manage_sale()`; o 19 testa o FINANCEIRO.
- [x] CHK036 O 400 "Valor esperado inválido." de hoje continua, e antes da trava? [contracts §17]
  → resolvido: passo 0.
- [x] CHK037 A tabela de verifies antigos da spec diz quando o `verify_305` roda? [Spec §Verifies antigos]
  → resolvido: História 1 e História 4; as outras fases estão no quickstart §5.

**Itens que testavam implementação**, com a pergunta sobre o texto:
- CHK001: a comissão do vivo não muda número em nenhum consumidor, inclusive o evento sem vendedor na DRE?
- CHK011: a extração do editor da 305 está definida como neutra no vivo, com as mesmas recusas, ordem e mensagens, e o `verify_305` verde antes do uso no cancelado?
- CHK025: o resync não regrava a linha do retido, não espera o ato, e o cenário 30 prova a corrida?

## Notas

- Depois das correções de 16/10: 37 de 37 (os 13 abertos escritos; o cético acrescentou CHK031–CHK037, resolvidos).
- Primeira rodada: 17 de 30 passam. Os 13 abertos são de escrita e entram na spec (Living Spec) ou no plan antes do
  `/speckit-tasks`. Nenhum leva pergunta ao dono: todos são técnicos.
- Para avaliar, foram conferidos no código, só leitura, em `d855d1a` e na `main` (`6356b80`):
  - as 8 chamadas de `_event_commission`;
  - o `set_event_clients` e o `delete_client`;
  - o `continue` de soma zero em `_build_commission_items`;
  - a `CALENDAR_SUPPRESS_EVENT_WRITES`, sempre presente no `Config` (`config.py:266`);
  - o deslocamento que a 307 trouxe.
- O bloco fixo "Portões da Manto" do molde fica fora, como nos checklists da 305. Ele confere o código no fecho
  (plan §8 Polimento, quickstart §6), não a escrita.
