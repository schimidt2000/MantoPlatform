# Feature 351 — Painel atribuído: quanto custa a venda que o anúncio trouxe

**Branch**: `351-painel-atribuido` (da `main`, `20bf93c0`) · **Created**: 2026-11-17 · **Status**: Implementada na branch (verify 83/83), sem merge ·
**Migration**: `a351b0c1d2e3` (aditiva, sobre `d334b2c4e6f8`) · **Nível**: 1 (feature) — constituição, Princípio VI

**Input**: pedido do dono (sessão principal, 17/11/2026): "Faça a feature 351 · painel atribuído", item 6 da
seção 8.5 da pesquisa "Máquina de vendas Manto" (Artifact privado de 17/11), com o escopo da seção 8.1.

## O pedido, nas palavras do dono *(obrigatório)*

A pesquisa de 17/11 concluiu "medir primeiro, escalar depois". O painel da 345 está no ar, mas o número que ele
mostra engana: o **custo por venda** de cada frente é o gasto em anúncio da frente dividido por **todas** as vendas
da frente (`app/marketing/comando_ops.py:353`). Uma festa que veio por indicação "barateia" o anúncio. A regra da
casa (custo de marketing por venda até 25% da margem mediana) não tem como ser aplicada com esse número.

O que o dono pediu para esta feature (seção 8.1 da pesquisa):

1. **Venda atribuída.** Venda e custo atribuídos ao lado do número misto. Só conta o fato que veio depois do contato.
   Janela de 45 dias. Mostrar também a versão com desconto de 50% de incrementalidade, com a premissa escrita na tela.
2. **Funil.** Por frente e por anúncio ou criativo, com custo por conversa, por orçamento e por evento.
3. **Card.** O resultado da peça junta as conversas reais do anúncio (CRM) com o vínculo card ↔ anúncio; o card ganha
   o campo "conceito".
4. **Metas e calendário.** Meta e verba por frente viram dado; o calendário sazonal frente × mês vira tabela, lida pela
   rotina semanal.
5. **Diário com teste estruturado.** Alvo, métrica, linha de base, controle; o antes e depois é calculado no servidor.
6. **Proposta.** O valor vira número; a tela mostra frente, teto e impacto mensal; o sino avisa quando nasce uma.
7. **Celular, em 390 px.** A tabela de campanhas não rola de lado; Temas paginado (476 linhas hoje); Kanban com filtro
   por frente e tipo e "minhas peças".
8. **Defeitos pequenos.** O "custo por cliente novo" divide todo o gasto por todos os clientes novos, de qualquer
   origem; "N anúncio(s) no ar" aparece com o anúncio pausado; o card de anúncio arrastado para Agendado ou Publicado
   some da fila da rotina.

**Contexto que limita a feature.** A feature 348 (origem completa: `ctwa_clid`, gclid, código no site, `conversa_id`
no orçamento e no evento, frente como coluna do evento) está sendo feita **ao mesmo tempo**, noutra branch. Esta
feature monta a atribuição sobre o que a `main` já tem e **não cria** as colunas da 348. O CRM (325–335) está em
produção desligado; o painel 345 está sem dados. Em produção há 618 fichas com origem gravada do Tintim (17/11), 153
delas com `utm_source = meta`.

## Clarifications

### Session 2026-11-17

- Q: A venda atribuída conta para a frente da campanha do anúncio ou para a frente do evento vendido? → A: frente da
  campanha do contato (o gasto mora lá); campanha sem frente → bloco "sem frente". A frente do evento aparece na lista
  das vendas atribuídas.
- Q: A meta de vendas por mês da frente mede todas as vendas da frente ou só as atribuídas a anúncio? → A: todas as
  vendas da frente no mês (a régua das metas da pesquisa §9.3); a régua do anúncio é o custo atribuído contra o teto.

## Cenários e Verificação *(obrigatório)*

### História 1 — Custo por venda atribuída, por frente (Prioridade: P1)

O dono abre Marketing → Desempenho e, em cada frente, vê dois números lado a lado: o custo por venda **misto** (o de
hoje) e o custo por venda **atribuída** — gasto da frente dividido pelas vendas que um anúncio da frente trouxe.
Embaixo, o mesmo custo com o **desconto de 50%** ("metade dessas vendas teria acontecido sem o anúncio — premissa, até
existir teste"), e é esse que é comparado com o teto. Assim ele decide subir ou cortar verba pela regra da casa.

**Por que esta prioridade**: é o número que a regra dos 25% da margem exige. Sem ele, nenhuma decisão de verba tem base.

**Verificação**: cenários 1–6 do `verify_351.py`.

**Cenários de aceite**:

1. **Dado** uma ficha que veio de um anúncio de campanha `FESTA · …` em 01/10 e um evento dela criado em 05/10 com
   venda em 10/10, **Quando** o dono olha o período que contém 10/10, **Então** a venda conta como atribuída à frente
   Festas, e o custo atribuído é o gasto da frente ÷ vendas atribuídas.
2. **Dado** a mesma ficha com o evento criado **antes** do contato pelo anúncio, **Então** a venda não é atribuída
   (só conta o fato depois do contato).
3. **Dado** um contato pelo anúncio e a venda 46 dias depois, **Então** a venda não é atribuída (janela de 45 dias).
4. **Dado** dois contatos por anúncios de frentes diferentes antes da venda, **Então** vale o **último** contato dentro
   da janela.
5. **Dado** uma ficha marcada só pela origem (`utm_source = meta`, sem data do contato), **Então** a data do contato é
   a de entrada na base; ficha antiga (entrada fora da janela) não tem venda atribuída por essa via.
6. **Dado** um período que começa antes de 01/06/2026, **Então** as vendas anteriores a essa data ficam fora da
   atribuição e a tela diz por quê ("antes de jun/2026 o evento quase nunca tem ficha").
7. **Dado** uma venda atribuída a uma campanha sem frente, **Então** ela aparece em "vendas atribuídas a campanha sem
   frente", não em uma frente.

---

### História 2 — Funil por frente, anúncio, peça e conceito, com custo (Prioridade: P1)

No Desempenho, o dono escolhe dividir o funil das conversas por **frente**, **anúncio**, **peça** (o card do Kanban) ou
**conceito**. Cada linha mostra quantas conversas chegaram, quantas tiveram orçamento enviado e quantas viraram
evento, e o **custo** de cada etapa (gasto ÷ conversas, ÷ orçamentos, ÷ eventos). O Comercial, no Funil das conversas,
ganha as mesmas divisões, **sem dinheiro**.

**Por que esta prioridade**: o volume para decidir está na conversa, não na venda (pesquisa §6.6); o custo por conversa
por conceito é o indicador quinzenal da frente Festas (§9.3).

**Verificação**: cenários 7–9 do `verify_351.py`.

**Cenários de aceite**:

1. **Dado** conversas cujo primeiro anúncio é de campanhas de frentes diferentes, **Quando** o funil é dividido por
   frente, **Então** cada conversa cai na frente da campanha do seu primeiro anúncio; a sem anúncio cai em "Sem
   anúncio"; a de campanha sem frente, em "Sem frente".
2. **Dado** gasto do anúncio no período, **Quando** dividido por anúncio, **Então** o custo por conversa é o gasto do
   anúncio ÷ conversas que chegaram por ele.
3. **Dado** um usuário do Comercial, **Quando** pede o funil dividido por frente, **Então** recebe as contagens e
   nenhum valor em dinheiro.

---

### História 3 — O resultado real da peça e o conceito (Prioridade: P2)

A Gabi abre um card de anúncio e vê o que a peça trouxe de verdade: conversas que chegaram pelo anúncio (CRM),
orçamentos enviados, vendas atribuídas e o faturamento delas — além do gasto e das conversas que a Meta informa. O card
ganha o campo **conceito** (o ângulo da peça: "mãe que surpreende", "bastidores"…), que agrupa o funil. O texto "no ar"
só aparece para anúncio que gastou na última leitura; anúncio pausado aparece como "sem gasto desde dd/mm".

**Por que esta prioridade**: fecha o ciclo criativo → resultado que a 345 deixou no gasto e na conversa informada.

**Verificação**: cenários 10–13 do `verify_351.py`.

**Cenários de aceite**:

1. **Dado** um card ligado ao anúncio X e duas conversas que chegaram por X, uma delas com orçamento enviado, **Então**
   o resultado do card mostra 2 conversas e 1 orçamento.
2. **Dado** o anúncio X sem gasto nos últimos dias com leitura da plataforma, **Então** o card não diz "no ar".
3. **Dado** um card de anúncio pronto arrastado para Agendado ou Publicado sem anúncio montado, **Então** ele continua
   na fila da rotina ("cards prontos sem anúncio").
4. **Dado** um card salvo com conceito, **Então** o conceito volta na leitura e vira grupo no funil por conceito.

---

### História 4 — Meta, verba e calendário do ano por frente (Prioridade: P2)

O dono define, por frente, a **meta de vendas por mês** e a **verba mensal**. No calendário do ano, ajusta mês a mês
(verba maior de dez a jun para festas, por exemplo) e escreve o **foco** de cada mês. O card da frente mostra o mês
corrente: vendas da frente no mês contra a meta e gasto contra a verba. A rotina semanal lê o calendário e as metas do mês
no contexto que já recebe.

**Por que esta prioridade**: tira da prosa da skill o que a rotina precisa para propor verba.

**Verificação**: cenários 14–16 do `verify_351.py`.

**Cenários de aceite**:

1. **Dado** meta de 45 vendas/mês na frente Festas e o mês de março com meta própria de 50, **Quando** o mês corrente é
   março, **Então** a meta exibida é 50; nos outros meses, 45.
2. **Dado** o Superadmin, **Quando** salva meta, verba e o calendário, **Então** os valores voltam na leitura.
3. **Dado** um usuário de Marketing (não Superadmin), **Quando** tenta salvar, **Então** recebe 403.
4. **Dado** a rotina pedindo o contexto da semana, **Então** ele traz o calendário e as metas do mês corrente.

---

### História 5 — Proposta com número, frente, teto e impacto mensal, e aviso no sino (Prioridade: P2)

Quando a rotina propõe "subir a verba de R$ 30 para R$ 45 por dia", a tela de Decisões mostra a frente da campanha, o
teto da frente e o **impacto no mês** (+R$ 450). O topo da tela soma o impacto do que já foi aprovado no mês. Quem decide
recebe um aviso no sino assim que a proposta nasce.

**Por que esta prioridade**: hoje o valor é texto e não soma; e o dono só sabe da proposta pelo e-mail da rodada.

**Verificação**: cenários 17–19 do `verify_351.py`.

**Cenários de aceite**:

1. **Dado** a rotina criando uma proposta de verba com "R$ 30,00/dia" → "R$ 45,00/dia" em texto, **Então** os valores
   viram números e o impacto mensal é (45 − 30) × 30 = R$ 450,00.
2. **Dado** uma proposta numa campanha `CORP · …`, **Então** a frente é Corporativo e o teto exibido é o dela.
3. **Dado** a proposta criada, **Então** cada Superadmin ativo recebe uma notificação que leva a Marketing → Decisões;
   criar a mesma proposta de novo não duplica o aviso dela.

---

### História 6 — Diário com teste estruturado (Prioridade: P3)

Ao registrar uma mudança no diário, a pessoa (ou a rotina, quando executa uma proposta) informa **o que** mudou (alvo:
campanha, conjunto ou anúncio), **qual métrica** vai olhar (conversas, custo por conversa, gasto, cliques, cadastros),
o **dia da mudança**, a **janela** (padrão 7 dias) e, se houver, um **controle** (um alvo que ficou igual). O servidor
grava a **linha de base** e calcula o antes e o depois, do alvo e do controle, com a variação.

**Por que esta prioridade**: é o "teste que cabe" da pesquisa (§6.6) — sem estrutura, o veredito é opinião.

**Verificação**: cenários 20–22 do `verify_351.py`.

**Cenários de aceite**:

1. **Dado** um anúncio com 10 conversas nos 7 dias antes de 01/11 e 15 nos 7 dias a partir de 01/11, **Quando** a
   entrada tem alvo = esse anúncio, métrica = conversas, mudança em 01/11, **Então** a leitura mostra antes 10, depois
   15, +50%, e a linha de base gravada é 10.
2. **Dado** um controle que foi de 10 para 11, **Então** o efeito líquido é +40 pontos (50% − 10%).
3. **Dado** que a janela do depois ainda não terminou, **Então** a leitura diz "em andamento" e não dá variação final.

---

### História 7 — Marketing no celular (390 px) (Prioridade: P3)

A equipe usa o sistema como app no iPhone. A tabela de campanhas vira lista de cartões, sem rolagem lateral; Temas e
licença mostra 50 temas por página, com a página no endereço; o Kanban filtra por frente, por tipo (post ou anúncio) e
por "minhas peças", com os filtros no endereço.

**Por que esta prioridade**: a regra de UX da casa (tela nasce em 390 px), mas não muda número nenhum.

**Verificação**: cenários 23–24 do `verify_351.py` (payload do Kanban e página de Temas) + conferência de tela em
390 px.

**Cenários de aceite**:

1. **Dado** 476 temas, **Quando** a tela abre, **Então** mostra 50 e "página 1 de 10"; a busca volta à página 1.
2. **Dado** o filtro "Minhas peças", **Então** só os cards em que a pessoa é responsável aparecem.
3. **Dado** a tela de Desempenho em 390 px, **Então** nenhuma parte rola de lado.

---

### História 8 — Custo por cliente novo vindo de anúncio (Prioridade: P3)

O bloco do custo por cliente novo do mês divide o gasto pelos clientes novos que **vieram de anúncio**, e mostra
quantos clientes novos o mês teve no total, para comparação.

**Verificação**: cenário 25 do `verify_351.py`.

**Cenários de aceite**:

1. **Dado** 10 clientes novos no mês, 2 com origem de anúncio, e R$ 600 de gasto, **Então** o custo por cliente novo de
   anúncio é R$ 300,00 e a dica diz "2 de 10 clientes novos vieram de anúncio".

### Casos de borda

- Venda de grupo (evento com principal): só o principal conta, como no custo misto (`group_leader_id` nulo).
- Evento com mais de uma ficha (`event_clients`): vale o último contato pago de qualquer ficha do evento.
- Anúncio que a Meta ainda não respondeu (sem campanha em `anuncios_meta`): o contato vale, a frente fica "sem frente".
- Campanha corrigida à mão para uma frente (`marketing_campanha_frentes`): a correção vence o prefixo, também na
  atribuição.
- Período longo (mais de um ano): o funil recusa como hoje (422); a venda atribuída aceita.
- Frente sem gasto e com venda atribuída (anúncio fora do período): custo atribuído vazio, venda contada.
- Proposta com texto sem número ("Público: mães 25–40"): os números ficam vazios e o impacto também.
- Proposta de pausa: impacto negativo (verba que deixa de sair).
- Diário sem dado da plataforma na janela: antes/depois "sem leitura", sem variação.
- Linha de base zero: variação percentual vazia ("sem base").
- Card sem anúncio: sem bloco de resultado (como hoje).
- Temas: página além da última devolve a última; filtro novo volta à página 1.
- Calendário: mês sem meta/verba próprias usa o padrão da frente; frente sem padrão mostra "sem meta".

## Requisitos *(obrigatório)*

### Requisitos funcionais

**Atribuição (uma função só)**

- **FR-001**: O sistema DEVE ter **uma única função** que decide qual contato pago "trouxe" cada venda; toda venda
  atribuída (por frente, na lista e no card) sai dela. Quando a 348 ligar evento e orçamento à conversa, a troca é só
  nessa função. O funil (conversas) e o cliente novo de anúncio não são venda: leem a origem do contato (primeiro
  anúncio da conversa; anúncio de origem ou origem paga da ficha).
- **FR-002**: Contatos pagos de uma ficha, a partir do que a `main` já grava: (a) o contato pelo anúncio na conversa
  (`conversa_anuncios`, tipo anúncio, com o momento real); (b) o primeiro e o último anúncio gravados na ficha
  (`anuncio_origem_*`, `anuncio_recente_*`); (c) a origem paga gravada na ficha (`utm_source` da Meta ou do Google), com
  o momento = entrada na base.
- **FR-003**: Uma venda conta como atribuída a um contato quando: o evento foi criado **depois** do contato; a data da
  venda está entre o dia do contato e 45 dias depois (os dois dias inclusive); e a venda é de 01/06/2026 em diante.
  Entre vários contatos válidos, vale o **mais recente**; no empate, conversa > ficha > origem da ficha.
- **FR-004**: A frente da venda atribuída é a **frente da campanha** do contato (correção manual > prefixo do nome); o
  contato sem campanha conhecida vai para "sem frente". A frente **do evento** continua lida por uma só função
  (`frente_venda_sql`), que a 348 troca pela coluna.
- **FR-005**: A venda conta como hoje (valor > 0, não cancelada, não cortesia, não satélite de grupo).

**Painel por frente**

- **FR-006**: Cada frente DEVE mostrar, além do que mostra hoje: vendas atribuídas, faturamento atribuído, custo por
  venda atribuída (gasto da frente no período ÷ vendas atribuídas no período) e custo por venda atribuída **com
  desconto de incrementalidade** (gasto ÷ (vendas atribuídas × 50%)), e o estado contra o teto calculado com o custo
  com desconto. A venda é do período (data da venda); o contato que a trouxe pode ser anterior ao período.
- **FR-007**: A tela DEVE escrever a premissa: "Desconto de 50%: metade das vendas atribuídas teria acontecido sem o
  anúncio. É premissa até existir teste." e a regra da atribuição (último contato pago, até 45 dias, só fato depois do
  contato).
- **FR-008**: Vendas atribuídas a campanha sem frente DEVEM aparecer à parte, com a contagem e o faturamento.
- **FR-009**: Período que começa antes de 01/06/2026 DEVE vir marcado como atribuição parcial, com o motivo na tela.
- **FR-010**: Marketing → Desempenho DEVE listar as vendas atribuídas do período (evento, data da venda, campanha,
  anúncio, de onde veio o contato); o valor de cada venda só aparece para o Superadmin.

**Funil**

- **FR-011**: O funil das conversas DEVE aceitar dividir também por **frente**, **anúncio**, **peça** e **conceito**,
  pelo primeiro anúncio da conversa. Grupos à parte, sempre por último: "Sem anúncio" (conversa sem anúncio), "Sem
  frente" (campanha sem frente ou ainda sem resposta da Meta), "Sem peça" (anúncio sem card) e "Sem conceito" (card sem
  conceito).
- **FR-012**: No Desempenho (gate de Marketing), cada grupo do funil DEVE trazer o gasto do grupo no período e o custo
  por conversa, por orçamento enviado e por evento fechado. O gasto da frente no funil é só o da plataforma de onde as
  conversas vêm com origem (Meta), para não dividir gasto do Google por conversa da Meta.
- **FR-013**: No Funil das conversas do Comercial, as novas divisões vêm sem dinheiro.

**Card**

- **FR-014**: O resultado do card de anúncio DEVE trazer, além de gasto e conversas informadas pela plataforma: conversas
  reais (conversas cujo primeiro anúncio é um anúncio do card), orçamentos enviados e eventos fechados dessas
  conversas, vendas atribuídas aos anúncios do card e o faturamento delas.
- **FR-015**: O card DEVE ter o campo **conceito** (texto curto, opcional), editável no diálogo e aceito nos pedidos que
  a rotina abre.
- **FR-016**: Cada anúncio ligado ao card DEVE dizer se está **no ar** (gastou num dos três últimos dias com leitura da
  plataforma) ou desde quando está sem gasto; sem leitura, "sem leitura".
- **FR-017**: Card de anúncio em Pronto, Agendado ou Publicado, sem anúncio montado e com todos os temas liberados,
  DEVE continuar na fila da rotina.

**Metas, verba e calendário**

- **FR-018**: Cada frente DEVE ter meta de vendas por mês e verba mensal (opcionais), editáveis só pelo Superadmin.
- **FR-019**: O calendário frente × mês DEVE guardar, para cada frente e mês: meta de vendas e verba (opcionais, vencem
  o padrão da frente naquele mês) e o foco do mês (texto). Nasce preenchido com o foco do calendário da pesquisa de
  17/11 e sem números.
- **FR-020**: O card da frente DEVE mostrar o mês corrente: vendas da frente no mês (todas, a mesma contagem do custo
  misto) contra a meta e gasto da frente no mês contra a verba.
- **FR-021**: O contexto que a rotina semanal já recebe DEVE trazer o calendário e a meta, a verba e o foco do mês
  corrente por frente.

**Proposta**

- **FR-022**: A proposta DEVE guardar o valor antes e o valor depois como número (verba por dia), aceitos da rotina ou
  lidos do texto quando o texto traz um valor em reais; e a frente (a enviada, ou a da campanha do alvo, ou a do card).
- **FR-023**: A tela de Decisões DEVE mostrar, em cada proposta: frente, teto da frente, verba mensal da frente e o
  **impacto no mês** (verba: (depois − antes) × 30; ativar: (depois ou custo por dia) × 30; pausar: −(antes ou custo por
  dia) × 30; público: sem impacto); e no topo, o impacto somado das propostas aprovadas e executadas no mês.
- **FR-024**: Ao nascer uma proposta, cada Superadmin ativo DEVE receber uma notificação no sino, com link para
  Marketing → Decisões; a mesma proposta nunca gera dois avisos para a mesma pessoa.

**Diário**

- **FR-025**: A entrada do diário DEVE aceitar, opcionalmente: alvo (plataforma, tipo, id, nome), métrica, dia da
  mudança (padrão: hoje), janela em dias (padrão 7, de 3 a 28) e controle (tipo, id, nome).
- **FR-026**: Com alvo e métrica, o servidor DEVE gravar a linha de base (o valor da janela anterior à mudança, quando
  não informada) e devolver, a cada leitura, o antes, o depois, a variação do alvo e do controle e o efeito líquido, e
  se a janela do depois já terminou.
- **FR-027**: A entrada que nasce de proposta executada DEVE herdar o alvo da proposta e a métrica padrão do tipo
  (verba e público → custo por conversa; ativar e pausar → conversas).

**Telas e defeitos**

- **FR-028**: A tabela de campanhas do Desempenho DEVE virar lista de cartões abaixo de 768 px, sem rolagem lateral.
- **FR-029**: Temas e licença DEVE paginar no servidor (50 por página), com página, busca e filtros no endereço.
- **FR-030**: O Kanban DEVE filtrar por frente, tipo e "minhas peças", com os filtros no endereço, e mostrar a frente no
  card.
- **FR-031**: O custo por cliente novo do mês DEVE dividir o gasto pelos clientes novos do mês **vindos de anúncio**
  (ficha com anúncio de origem ou origem paga) e mostrar o total de clientes novos ao lado.
- **FR-032**: Todo bloco novo (vendas atribuídas, funil com custo, calendário, teste do diário) DEVE ter estado de
  carregando, de erro ("Não foi possível carregar … Tente novamente.") e vazio no padrão da casa ("Nenhuma venda
  atribuída no período.", "Nenhuma conversa com anúncio no período.").

### Entidades *(se houver dados)*

- **Frente de marketing** (`marketing_frentes`, existe): ganha `meta_vendas_mes` e `verba_mes`.
- **Calendário da frente** (`marketing_calendario`, nova): frente × mês (1–12), meta de vendas, verba, foco; UNIQUE
  (frente, mês). As 60 linhas nascem na migration.
- **Card de marketing** (`marketing_posts`, existe): ganha `conceito`.
- **Proposta** (`marketing_propostas`, existe): ganha `frente`, `valor_antes_num`, `valor_depois_num`.
- **Entrada do diário** (`marketing_diario`, existe): ganha alvo (`alvo_platform`, `alvo_tipo`, `alvo_id`,
  `alvo_nome`), `metrica`, `mudou_em`, `janela_dias`, `linha_base` e controle (`controle_tipo`, `controle_id`,
  `controle_nome`).
- **Venda atribuída** (derivada, não gravada): venda + contato pago que a trouxe + frente da campanha do contato.
- **Notificação** (existe): novo tipo `marketing.proposta`.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

- `GET /api/marketing/desempenho` (existe; o bloco por frente ganha os números atribuídos) — MARKETING, SUPERADMIN.
- `GET /api/marketing/atribuicao` (novo: vendas atribuídas e funil com custo) — MARKETING, SUPERADMIN; o valor de cada
  venda só para SUPERADMIN real.
- `GET /api/marketing/calendario` (novo) — MARKETING, SUPERADMIN; `PATCH /api/marketing/calendario` (novo) — só
  SUPERADMIN real.
- `GET|PATCH /api/marketing/frentes` (existe; ganha meta e verba) — leitura MARKETING, SUPERADMIN; escrita só
  SUPERADMIN real.
- `GET /api/marketing/propostas` (existe; ganha frente, teto, impacto) — MARKETING, SUPERADMIN.
- `GET|POST /api/marketing/diario` (existe; ganha o teste) — MARKETING, SUPERADMIN.
- `GET /api/marketing/posts` (existe; o card ganha `conceito` e a situação de cada anúncio — o filtro do Kanban roda na
  tela) e `POST|PATCH /api/marketing/posts` (ganha `conceito`) — MARKETING, SUPERADMIN.
- `GET /api/marketing/temas-licenca` (existe; ganha `pagina`) — MARKETING, SUPERADMIN.
- `GET /api/conversas/funil` (existe; ganha as divisões, sem dinheiro) — COMERCIAL, SUPERADMIN.
- Agente (`/api/marketing-agent/<token>/…`): **sem mudança de rota**; o contexto e os pedidos ganham campos pelo núcleo.

## Verificação (`verify_351.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/351-painel-atribuido/verify_351.py`, contra o espelho **`manto_351`** (dump noturno de produção, banco
próprio desta feature — o `manto_local` é compartilhado com as sessões 348–350; exceção registrada no `plan.md`),
`FLASK_ENV=development`, `MANTO_SEM_THREADS=1`. Login só por `POST /api/auth/login`; escrita conferida por conexão
separada; dados semeados com prefixo próprio e limpos no `finally`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | contato pelo anúncio FESTA, evento criado depois, venda em 5 dias | venda atribuída a Festas; custo atribuído = gasto ÷ atribuídas | não |
| 2 | evento criado antes do contato | não atribuída | não |
| 3 | venda 46 dias depois do contato | não atribuída | não |
| 4 | dois contatos (CORP depois de FESTA) | vale o último (Corporativo) | não |
| 5 | ficha só com `utm_source=meta` (entrada recente × antiga) | recente atribui; antiga não | não |
| 6 | período antes de 01/06/2026; desconto de 50% | `parcial = true`; custo com desconto = 2 × atribuído | não |
| 7 | funil por frente e por anúncio com gasto | grupos certos e custo por conversa/orçamento/evento | não |
| 8 | funil do Comercial dividido por frente | sem chave de dinheiro | não |
| 9 | funil por peça e por conceito | conversa do anúncio do card cai no card e no conceito | não |
| 10 | resultado do card | conversas reais, orçamentos, vendas atribuídas | não |
| 11 | anúncio sem gasto nos últimos dias com leitura | `no_ar = false` | não |
| 12 | card de anúncio em Agendado sem anúncio | continua em `cards_prontos_sem_anuncio` | não |
| 13 | conceito salvo pelo PATCH do card | lido por conexão separada | não |
| 14 | meta, verba e calendário salvos pelo Superadmin | lidos por conexão separada; mês com meta própria vence | não |
| 15 | **Marketing (não Superadmin) salva calendário/meta** | **403** | **sim** |
| 16 | contexto da rotina | traz calendário e metas do mês | não |
| 17 | proposta de verba em texto | números lidos, impacto = (45 − 30) × 30 | não |
| 18 | frente e teto da proposta | frente da campanha `CORP · …` | não |
| 19 | sino da proposta | uma notificação por Superadmin; sem duplicar | não |
| 20 | diário com alvo/métrica/controle | antes, depois, variação, efeito líquido; linha de base gravada | não |
| 21 | diário com janela em andamento | `completo = false` | não |
| 22 | proposta executada → diário | herda alvo e métrica | não |
| 23 | lista do Kanban | cada card traz frente, tipo, responsável e conceito (base do filtro, que roda na tela) | não |
| 24 | Temas paginado | 50 por página; página além da última | não |
| 25 | custo por cliente novo de anúncio | gasto ÷ novos de anúncio; total ao lado | não |
| 26 | **Comercial pede `/api/marketing/atribuicao`** | **403** | **sim** |
| 27 | **Marketing pede valor da venda** | `valor` vazio na lista (só Superadmin) | não |
| 28 | limpeza | registros e usuários descartáveis apagados | — |

Conferência de tela (Browser pane, backend próprio na porta 5351 e Vite na 6351, `manto_351`): Desempenho, Decisões,
Temas e licença, Painel (Kanban) e o diálogo do card, o diálogo de frentes e o calendário, e o Funil das conversas —
em 390 × 844 e em tela larga.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Em cada frente, o dono lê o custo por venda misto, o atribuído e o atribuído com desconto lado a lado, sem
  abrir outra tela, e sabe se a frente está abaixo do teto pela regra da casa.
- **SC-002**: Toda venda atribuída do período pode ser conferida uma a uma (qual contato, de qual campanha e anúncio).
- **SC-003**: Com o funil por conceito, o dono compara o custo por conversa de dois conceitos do mesmo período em menos
  de um minuto.
- **SC-004**: A soma do impacto mensal das propostas aprovadas no mês aparece na tela de Decisões, sem conta à mão.
- **SC-005**: Nenhuma tela de marketing rola de lado em 390 px.
- **SC-006**: Quem decide fica sabendo de uma proposta nova no mesmo minuto em que ela nasce (sino), sem esperar o
  e-mail da rodada.

## Fora de escopo

- Tudo da 348: `ctwa_clid`, gclid/gbraid/wbraid, código no site, `conversa_id` no orçamento e no evento, frente como
  coluna do evento.
- Envio de conversões à Meta (Conversions API) e ao Google (Data Manager API).
- Casar lead e campanha pelo id no Desempenho (`desempenho_ops.py:909-916`) — fica para a 348/seguinte.
- Pontuação de lead, conversa qualificada, perda e motivo (349).
- Opt-in, aniversário, indicação (350).
- Mudanças da 345b: Google Ads na rotina, `/run` aceitando entradas do diário, `date.today()` em
  `app/api/marketing_read.py:176`, estado vazio de `MarketingDesempenhoPage.tsx:65-83`; e `scripts/marketing/*`,
  a skill `marketing-auditor` e `app/api/marketing_agent.py`.
- Teste de incrementalidade de verdade (liga e desliga em blocos): o diário só ganha a estrutura para registrá-lo.
- Reembolso mensal mudando com leitura parcial (`desempenho_ops.py:530`, `:784`).
- Aprovar proposta em lote; filtros novos na lista de propostas e do diário além do que esta spec diz.

## Docs a atualizar

`docs/01` §3 (endpoints novos e campos), §4.3 (gates), schema das tabelas; `docs/02` (Desempenho, Decisões, Temas,
Painel, diálogo do card, diálogo de frentes e calendário, Funil); `docs/03` (entrada no topo); `docs/04` §Marketing
(regra da atribuição, desconto, calendário) e §CRM (funil por frente); `docs/05` (dívida 214 paga em parte; dívidas
novas: atribuição sem `conversa_id` até a 348, desconto de 50% como premissa).

## Premissas

- **Janela de 45 dias e último contato pago** (pesquisa §9.3): o último contato antes da venda leva a venda inteira.
  Primeiro contato e divisão entre contatos ficam de fora até haver volume.
- **Desconto de incrementalidade de 50%** (pesquisa §3.8): constante declarada na tela; não é configurável nesta
  feature.
- **"Fato depois do contato"** usa a criação do evento (como o funil da 335, `funil_ops.py:190-193`) e a data da venda
  dentro da janela.
- **Corte em 01/06/2026**: antes disso o evento quase nunca tem ficha (cruzamento Tintim × produção, 17/11).
- **Contato pela origem da ficha** (Tintim/Kommo): sem data do contato gravada, usa a entrada na base. Na prática só
  atribui a ficha nova; a antiga fica de fora. É conservador de propósito.
- **"No ar"** é derivado da leitura (gasto nos três últimos dias com leitura da plataforma): o sistema não guarda a
  situação do anúncio na Meta, e a rota do agente não muda nesta feature.
- **Mês = 30 dias** no impacto mensal da proposta.
- **Quem recebe o aviso da proposta**: todos os Superadmins ativos (quem decide, `eh_superadmin`).
- **Metas de vendas** são de todas as vendas da frente no mês (a régua da pesquisa §9.3); a verba é o gasto da frente no
  mês.
- O CRM está desligado em produção: o funil e o resultado real do card ficam vazios até o número principal entrar no
  CRM; a venda atribuída já usa as 153 fichas com `utm_source = meta`.
