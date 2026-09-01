# Feature 267 — integridade do vínculo e a comissão que bate

**Branch**: `267-integridade-comissao` (criar de `main`, depois do merge da 266)
**Created**: 2026-08-31 · **Status**: Draft · **Migration**: nenhuma

## Problema

A 266 costurou a navegação e fez o lead aparecer. Esta feature cuida do outro lado da mesma queixa:
**o clique que não faz nada e o número que não bate.**

São defeitos que a própria dívida técnica do repositório já prescreve — dois deles marcados **P0** e
dois **P1** (`docs/05_DIVIDA_TECNICA.md` §1, itens 1, 2, 5 e 6) — mais duas assimetrias entre o
caminho manual e o automático que corroem dado em silêncio.

### O que está quebrado, em ordem de dor

1. **Marcar comissão EducaManto como paga não faz nada** (P0). A planilha monta o item pelo ciclo
   `coalesce(payable_from, sale_date)` — comissão EducaManto entra pelo mês da **realização** — mas
   a marcação de pago filtra só por `sale_date`. O item aparece em maio, o clique procura em maio
   pela data da **venda**, acha zero linhas, e a tela mostra "pago" sobre um lote que continua
   `a_pagar` no banco. E o inverso também: o mês da venda, que não exibe a comissão, marca ela como
   paga ao ser liquidado.

2. **A tela fica com número velho depois de pagar** (P0). As mutações invalidam só
   `["financeiro-pagamentos", mês]`, mas o endpoint de status é poliforme — escreve em
   `CommissionPayment` **e** `RecurringExpenseEntry`. Comissões, Gastos Recorrentes e Dashboard
   Financeiro nunca são invalidados, e com `staleTime` de 30s e `refetchOnWindowFocus: false` o dado
   errado **fica na tela**.

3. **Venda preenchida pela tela de edição completa não gera comissão** (P1). O `PATCH` em bloco
   grava `sale_value`/`seller_id` sem sincronizar a linha — só a criação e o painel inline
   sincronizam. O paliativo de reconciliação só percorre linhas que **já existem**; ele nunca cria a
   que falta. O financeiro precisa perceber a divergência sozinho.

4. **O lucro do evento usa outra regra de comissão** (P1). O KPI recalcula com 2% sobre venda−BV,
   ignorando EducaManto (5% sobre lucro), Loja Virtual (que não comissiona) e
   `receives_commission` — enquanto o valor real vem de uma regra de 9 ramos. A tela do evento mostra
   um número que o Financeiro nunca vai pagar.

5. **Desvincular um pré-contrato pela tela do evento é desfeito sozinho.** O caminho da agenda grava
   o vínculo direto, sem marcar `event_link_source`/`event_link_locked` e sem `ensure_event_client` —
   diferente do caminho da tela de formulários. Resultado: `locked` fica falso, o reprocessamento do
   próximo ciclo de sync (a cada 10 min) religa a resposta, e **a decisão humana some em silêncio**.

6. **Excluir um evento deixa rastro mentiroso na resposta.** O SQLAlchemy anula o `event_id` sozinho
   (a relação tem backref), mas `event_link_source` continua dizendo `'auto_date'` apontando para
   nada; se o vínculo era automático, a resposta volta destravada e pode ser religada a outro evento
   do mesmo dia.

## Solução

### Frente A — a comissão que bate

- **Uma única expressão de ciclo.** Extrair para `comissoes_ops.py` a expressão
  `coalesce(payable_from, sale_date)` e a função de liquidação por período, e fazer **as quatro**
  cópias chamarem a mesma coisa. A mesma expressão que monta o item passa a liquidar o item.
- **`PATCH` em bloco sincroniza comissão**, por injeção (o domínio da agenda não importa a régua do
  financeiro), incondicionalmente — igual aos dois gêmeos que já fazem isso.
- **O KPI do evento lê a linha real** de `CommissionPayment` e, quando não existe linha, cai na regra
  **canônica** — nunca na fórmula flat. O gêmeo Jinja da mesma tela muda junto.
- **Invalidação completa** do cache financeiro num helper único chamado pelas três mutações.
- **Deep-link do evento para `/financeiro/comissoes`** (herdado da 266): as duas telas financeiras
  passam a ler filtro da URL. Entra aqui porque é a mesma história — o número do evento e o do
  financeiro viram a mesma coisa, e agora dá para ir de um ao outro.

### Frente B — o vínculo que não se desfaz sozinho

- **Um núcleo único** (`apply_event_link` / `clear_event_link`, sem commit) que grava `event_id`,
  `event_link_source`, `ambiguous`, `locked` e chama `ensure_event_client` — e os **quatro** pontos
  que hoje escrevem o vínculo à mão passam a usá-lo.
- **A exclusão de evento limpa `event_link_source`** e `ambiguous`, desvinculando sem apagar: o
  pré-contrato é o registro da festa da cliente e é a fonte do histórico anterior a 2026.

## Decisões

1. **A delegação é no núcleo, nunca no wrapper.** `link_event` **rouba** uma resposta presa a outro
   evento (sobrescreve sem checar), enquanto o caminho da agenda **recusa** e devolve 409. Delegar
   no nível do wrapper mudaria o contrato da API. Por isso o núcleo extraído é sem validação e sem
   commit, e cada chamador mantém a sua própria regra de conflito.

2. **O núcleo não commita.** `unlink_event` commita; usá-la dentro do laço de desvínculo daria um
   commit por resposta. Um `*_ops` que commita dentro de laço quebra a transação única do request —
   é justamente por isso que o núcleo sem commit precisa existir.

3. **A sincronização de comissão é incondicional.** Guardar por "campo mudou" reintroduz metade do
   bug: a venda que nunca gerou linha nenhuma precisa de sync **mesmo quando nada mudou nesta
   gravação**. É exatamente o buraco que a reconciliação não cobre.

4. **`flush` antes de sincronizar.** A reconciliação do elenco adiciona e remove `EventRole` sem
   flush; para evento EducaManto a comissão incide sobre o **lucro**, que lê os cachês. Sem o flush,
   a coleção volta do cache sem os valores novos e a comissão sai errada nessa gravação.

5. **Evento cancelado ganha guarda explícita.** O cancelamento esvazia o backref de comissão, então
   o fallback do KPI voltaria a inventar número exatamente onde o financeiro já estornou. A regra
   canônica sozinha **não** protege: quem checa cancelamento é a sincronização, não o cálculo.

6. **Comissão já paga é o que se mostra.** Ler a linha real significa exibir o valor efetivamente
   pago, que pode divergir da venda atual. É o comportamento desejado — comissão paga é histórico
   congelado — mas é visível: a tela para de "acompanhar" a venda depois do pagamento.

7. **O rótulo não pode mentir sobre a taxa.** Quando o valor vem da linha real ele não é derivável de
   um percentual único (EducaManto incide sobre lucro). O payload ganha a origem do número
   (`linha` | `estimativa`) e a tela diz "estimativa" enquanto a linha não existe, em vez de estampar
   um percentual que não corresponde à conta.

8. **O `lucro` continua sem descontar comissão.** A tela declara "venda − cachês − gastos" e é isso
   que ela mostra. Passar a descontar é mudança de definição de negócio, não correção — se for para
   fazer, é outra decisão, com rótulo e dica mudando junto.

9. **A exclusão de evento NÃO trava a resposta.** Quem estava travado por decisão humana continua
   travado; quem veio de vínculo automático volta destravado para a fila — que é o certo quando o
   evento é recriado no mesmo dia (o caso clássico do sync que apaga e o Google devolve com id novo).
   Forçar `locked` congelaria a resposta para sempre por causa de um evento que sumiu sem ninguém
   decidir nada.

10. **O módulo de Comissões fica fora.** Ele recorta o mês por `sale_date` (com fallback em
    `created_at`) enquanto a Planilha usa `coalesce(payable_from, sale_date)`. Alinhar os dois
    **move** linhas de EducaManto entre meses já fechados e conferidos pela equipe: é mudança de
    leitura financeira histórica, não correção de escrita, e merece feature própria com ensaio no
    dump. As duas telas respondem a perguntas diferentes ("quanto foi vendido neste mês" × "o que sai
    no repasse deste mês") — a divergência é defensável **enquanto estiver escrita**.

11. **A escrita nova em `event_clients` é assumida.** Com o núcleo unificado, vincular um
    pré-contrato pela tela do evento passa a inserir a cliente em `event_clients` — e, se o evento
    não tinha cliente nenhum, ela entra como **Contratante**. Hoje nada é criado. É o objetivo do
    item, mas é escrita a partir de uma tela que não pediu isso.

## Correções de premissa (verificadas em 31/08)

Três coisas que a dívida técnica e a análise afirmam e que **não** se confirmaram no código:

1. **Não são 4 fórmulas de comissão divergentes, são 3.** `comissoes_ops.py:183` é um recorte de
   **mês**, não um cálculo — problema irmão, tela diferente, outra convenção. E
   `financeiro/routes.py:120` é `_is_permuta()`, sem relação com comissão; o DRE já consome a regra
   canônica. Tratar os dois como "cópias da regra" faria a feature crescer para dentro do módulo de
   Comissões sem necessidade.

2. **Não são 2 cópias do filtro por `sale_date`, são 4.** Além das duas de liquidação em lote,
   existem os dois controles **individuais** da mesma planilha com o filtro idêntico. Corrigir só o
   lote deixa o bug vivo no clique unitário do mesmo item da tela.

3. **Excluir evento com pré-contrato NÃO estoura violação de chave.** A relação evento↔resposta tem
   backref, então o SQLAlchemy anula o `event_id` sozinho. O defeito real é o `event_link_source`
   obsoleto e a possibilidade de religação — sério, mas não é a falha de produção que a análise
   sugeriu. *(O caso que **realmente** estoura é o de cliente, e por isso foi para a 266: aquela
   relação não tem backref.)*

## Verificação

`verify_267.py` contra o `manto_local`, escrito antes do código. Os quatro casos que definem a
feature, todos conferidos **por conexão separada** (o autoflush esconde ausência de commit — lição
do hotfix 257):

- comissão EducaManto com venda e realização em meses diferentes: liquidar pelo mês da realização
  **persiste** (hoje o item volta para "não pago" ao recarregar), e o mês da venda **não** a liquida;
- evento sem linha de comissão + venda preenchida pelo formulário grande → a linha nasce com o valor
  certo; trocar a vendedora migra a linha sem duplicar;
- quatro eventos lado a lado com o número idêntico ao da tela de Comissões: comum, EducaManto (sobre
  lucro, não 2% da venda), Loja Virtual (R$ 0,00) e cancelado (R$ 0,00, não o valor estornado);
- vincular pré-contrato pela aba Comercial → resposta fica `manual` + travada, a cliente aparece em
  `event_clients`, e o ciclo de sync seguinte **não** religa o que foi desvinculado.

Ensaio obrigatório no dump antes do merge: contar, por mês, quantas linhas o filtro velho pega e
quantas o novo pega. A diferença tem de ser **exatamente** as linhas com `payable_from` preenchido.
Qualquer linha comum mudando de lote é sinal de que a expressão saiu errada.

Portões: `npm run typecheck` limpo nos três apps, `ruff check` limpo, `docs/01`/`docs/02`/`docs/03`
atualizados — e reescrever a docstring de `comissoes_ops.py`, que hoje declara explicitamente que
`financeiro/routes.py` **não** importa dele (a extração inverte isso; deixar o texto velho é pior
que a duplicação).

## Fora de escopo

Alinhamento do recorte de mês do módulo de Comissões (decisão 10) · o `lucro` passar a descontar
comissão (decisão 8) · deduplicação de `set_payment_status` entre Jinja e API (`docs/05` §5) · e
tudo o que a análise mapeou para as ondas 2 a 4.
