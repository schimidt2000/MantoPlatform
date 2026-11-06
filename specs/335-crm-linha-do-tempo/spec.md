# Feature 335 — Linha do tempo da ficha e funil das conversas

**Branch**: `335-crm-linha-do-tempo` (da `334-crm-origem-do-anuncio`, fora da `main`: o dono adiou a publicação)
· **Created**: 2026-11-06 · **Status**: Rascunho · **Migration**: não · **Nível**: 1 (feature: endpoints e tela novos)

**Input**: pedido do dono (04/11 e 06/11): "Começar a 3c" e "bora seguir". É a última fatia da Fase 3 do
`docs/PLANO_CRM_PROPRIO.md`: a linha do tempo na ficha e o funil derivado.

## O pedido, nas palavras do dono *(obrigatório)*

> "Começar a 3c" (04/11) · "bora seguir" (06/11)

O plano põe a **ficha única da cliente** entre os ganhos do CRM: "uma linha do tempo de conversas, orçamentos,
formulários, eventos, pagamentos e avaliações". E o funil **derivado dos fatos**, sem cartão para arrastar: "conversa
nova → orçamento enviado → formulário → evento → venda → pagamento → avaliação". A lição da feature 021 é que o funil
manual morreu porque ninguém o mantinha. Hoje a ficha mostra os eventos, os formulários e as avaliações em cartões
separados, e nada das conversas nem dos orçamentos; e não existe taxa de conversão em lugar nenhum da Plataforma.

## Clarifications

### Session 2026-11-06

- Q: Onde fica o funil? → A: **Tela nova no Comercial** ("Funil", ao lado do Pipeline de Vendas e das Conversas),
  para Comercial e Superadmin, o mesmo acesso das Conversas.
- Q: Como o funil conta? → A: **Quem chegou no período**: as conversas novas do período e até onde cada uma chegou
  ("de 100 que chegaram em outubro, 40 receberam orçamento e 9 fecharam").
- Q: O funil se divide por vendedor? → A: **Sim, e todos veem todos** (quem atende a conversa), como a caixa de
  conversas, que já é do time.
- Q: O que a linha do tempo da ficha mostra? → A: **Só os marcos** (primeiro contato, anúncio, orçamento enviado,
  formulário, evento, pagamento, avaliação), cada um com a data e o link; a conversa continua na tela de Conversas.

## Cenários e Verificação *(obrigatório)*

### História 1 — A ficha conta a história da cliente (Prioridade: P1)

Na ficha da cliente, um cartão **Linha do tempo** lista os marcos, do mais novo para o mais antigo: quando ela entrou
na base, cada primeiro contato por conversa (WhatsApp ou Instagram), os anúncios pelos quais chegou, os orçamentos
enviados, os formulários preenchidos, os eventos fechados, os pagamentos registrados e as avaliações. Cada marco tem a
data, uma linha curta e, quando a pessoa tem acesso, o link para o lugar de origem ("Abrir conversa", "Ver orçamento",
"Ver evento").

**Por que esta prioridade**: é o "ficha única" do plano; o vendedor que pega a cliente de outro entende o caso sem
abrir cinco telas.

**Verificação**: cenários 1, 2 e 3 do `verify_335.py`, e a tela.

**Cenários de aceite**:

1. **Dado** uma ficha com conversa, anúncio, orçamento enviado, formulário, evento, pagamento e avaliação, **Quando** a
   ficha abre, **Então** cada marco aparece uma vez, com a data certa, em ordem do mais novo para o mais antigo.
2. **Dado** um evento cancelado da cliente, **Quando** a ficha abre, **Então** ele não aparece (como nas listas, feature
   312), nem os pagamentos e a avaliação dele.
3. **Dado** o Financeiro abrindo a ficha, **Quando** a linha do tempo aparece, **Então** os marcos estão lá, mas sem
   "Abrir conversa" nem "Ver orçamento" (telas que ele não abre).

---

### História 2 — O funil das conversas do período (Prioridade: P1)

Na tela **Funil** (menu Comercial), o vendedor escolhe o período e vê as conversas novas que chegaram nele e até onde
cada uma foi: **Chegou → Orçamento enviado → Formulário → Evento fechado → Pagou → Avaliou**. Cada etapa mostra
quantas conversas chegaram até ela, a porcentagem sobre as que chegaram e a passagem da etapa anterior. Filtros de
canal (WhatsApp, Instagram) e de campanha (ou "Sem anúncio").

**Por que esta prioridade**: sem a taxa de conversão, o dono não sabe se o problema é responder, orçar ou fechar.

**Verificação**: cenários 4, 5, 6 e 8 do `verify_335.py`, e a tela.

**Cenários de aceite**:

1. **Dado** conversas que chegaram no período em pontos diferentes do caminho, **Quando** o funil abre, **Então** cada
   etapa conta as conversas que chegaram até ela ou além (a que fechou evento conta em "Orçamento enviado" e em
   "Formulário" mesmo sem esses fatos registrados: o orçamento pode ter ido pelo celular) e as porcentagens batem.
2. **Dado** uma conversa que chegou fora do período, **Quando** o funil abre, **Então** ela não conta, mesmo que o
   evento dela tenha fechado dentro do período.
3. **Dado** o fato que aconteceu antes do primeiro contato da conversa (um evento antigo da mesma ficha), **Quando** o
   funil conta, **Então** esse fato não faz a conversa avançar.
4. **Dado** o filtro de canal ou de campanha, **Quando** aplicado, **Então** só as conversas daquele canal ou daquela
   campanha contam.

---

### História 3 — Por vendedor, por campanha e por canal (Prioridade: P2)

Abaixo do funil, uma tabela divide as mesmas etapas por **vendedor** (o responsável pela conversa; "Sem responsável"
para a fila), por **campanha** ou por **canal**, à escolha, com a conversão de "Chegou" até "Evento fechado". Todo o
Comercial vê a tabela inteira.

**Por que esta prioridade**: o plano põe a conversão por vendedor como o terceiro ganho do CRM.

**Verificação**: cenário 6 do `verify_335.py`, e a tela.

**Cenários de aceite**:

1. **Dado** conversas de dois vendedores e da fila, **Quando** a tabela é por vendedor, **Então** cada um tem a sua
   linha e a soma das linhas é o total do funil.
2. **Dado** a tabela por campanha, **Quando** há conversa sem anúncio, **Então** ela entra em "Sem anúncio".

---

### História 4 — Quem parou em cada etapa (Prioridade: P2)

Ao tocar numa etapa do funil, abre a lista das conversas que **pararam ali** (chegaram nela e não na seguinte): nome,
canal, vendedor, quando chegou e "Abrir conversa". É a lista de quem recebeu orçamento e não fechou, para o
vendedor retomar.

**Por que esta prioridade**: o follow-up de orçamento é o primeiro ganho em dinheiro do plano; a automação é da Fase
6, mas a lista já ajuda à mão.

**Verificação**: cenário 7 do `verify_335.py`, e a tela.

**Cenários de aceite**:

1. **Dado** a etapa "Orçamento enviado", **Quando** tocada, **Então** a lista traz só as conversas com orçamento e sem
   formulário nem evento, da mais nova para a mais antiga.
2. **Dado** a última etapa ("Avaliou"), **Quando** tocada, **Então** a lista traz as que chegaram até o fim.

### Casos de borda

- **Conversa sem ficha**: conta em "Chegou" e, se teve orçamento pela conversa, em "Orçamento enviado"; as etapas que
  dependem da ficha (formulário, evento, pagamento, avaliação) só andam quando a conversa tem ficha.
- **A mesma cliente em duas conversas** (WhatsApp e Instagram) que chegaram no período: duas conversas no funil; o
  evento da ficha conta nas duas. O funil é de conversas, não de pessoas.
- **Cliente antiga que volta por uma conversa nova**: é conversa nova (conta). A que volta na mesma conversa antiga
  não é (a repescagem está nos Retornos do Desempenho, feature 334).
- **Primeiro contato**: a primeira mensagem recebida da cliente ou o primeiro contato pelo anúncio (a abertura do
  Instagram sem mensagem), o que vier antes. A conversa só com mensagens da Manto (a equipe escreveu primeiro, com
  modelo) chega pela primeira mensagem dela, quando houver; sem nenhuma, não entra no funil.
- **Evento cancelado** não conta como fechado, nem o pagamento e a avaliação dele.
- **Evento de grupo** (feature 137): o pagamento pode estar no principal; conta para o grupo inteiro.
- **Orçamento mandado pelo celular** (coexistência, fora da Plataforma): não aparece na linha do tempo; no funil, a
  conversa que formulou ou fechou conta em "Orçamento enviado" mesmo assim (a etapa mais avançada puxa as anteriores).
- **Período e fuso**: o período é de datas de São Paulo; o primeiro contato (gravado em UTC) é convertido.
- **Funil vazio**: sem conversa no período, a tela diz isso e sugere outro período.

## Requisitos *(obrigatório)*

### Funcionais

- **FR-001**: A ficha DEVE mostrar a linha do tempo com os marcos: entrada na base, primeiro contato de cada conversa,
  contatos por anúncio ou publicação, orçamentos enviados, formulários, eventos fechados, pagamentos registrados e
  avaliações — do mais novo para o mais antigo, sem duplicar.
- **FR-002**: Cada marco DEVE ter a data e, quando a pessoa tem acesso à tela de origem, o link para ela.
- **FR-003**: Evento cancelado (e os pagamentos e a avaliação dele) NÃO DEVE aparecer na linha do tempo.
- **FR-004**: A tela Funil DEVE contar, para as conversas cujo primeiro contato caiu no período, quantas chegaram a
  cada etapa: Chegou, Orçamento enviado, Formulário, Evento fechado, Pagou, Avaliou.
- **FR-005**: Uma etapa só conta pelo fato que aconteceu **depois** do primeiro contato da conversa.
- **FR-006**: Cada conversa tem a etapa **mais avançada** que alcançou; cada etapa conta as conversas que chegaram
  nela ou além (o funil nunca cresce de uma etapa para a seguinte) e mostra a porcentagem sobre "Chegou" e a passagem
  da etapa anterior. "Parou em" uma etapa é ter nela a etapa mais avançada.
- **FR-007**: O funil DEVE ter filtros de canal e de campanha (incluindo "Sem anúncio").
- **FR-008**: A tabela DEVE dividir as etapas por vendedor (o responsável; "Sem responsável"), por campanha ou por
  canal; a soma das linhas é o total.
- **FR-009**: Tocar numa etapa DEVE listar as conversas que pararam nela, com "Abrir conversa".
- **FR-010**: O funil e a lista DEVEM ser só de Comercial e Superadmin (papel real), como as Conversas; a linha do
  tempo segue o acesso da ficha (Comercial, Financeiro e Superadmin).
- **FR-011**: O período é de datas de São Paulo; o padrão é o mês corrente.
- **FR-012**: Os textos novos seguem o Princípio XV.

### Entidades

Nenhuma tabela nova: tudo é derivado do que existe — `Conversa` e `ConversaMensagem` (325), `ConversaAnuncio` e
`AnuncioMeta` (334), `OrcamentoEnvio` e `OrcamentoHistory.client_id` (333), `FormResponse.client_id`, `EventClient` e
`CalendarEvent`, `EventPayment`/`EventInstallment` e `ClientFeedback`.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: O vendedor entende a história de uma cliente pela ficha, sem abrir outra tela, em menos de 1 minuto.
- **SC-002**: O dono lê a conversão do mês (chegou → evento fechado) numa tela só, por vendedor e por campanha.
- **SC-003**: A lista de quem parou em "Orçamento enviado" sai com um toque.
- **SC-004**: A tela do funil responde em até 2 s para um trimestre (cerca de 2.000 conversas).

## Premissas

- O funil é de **conversas** (o CRM nasce na conversa); antes da virada (Fase 4) ele mostra pouco, e o histórico de
  antes da Plataforma não entra.
- "Pagou" é ter ao menos um pagamento registrado (comprovante, PIX ou parcela recebida), não o total quitado.
- "Vendedor" é o responsável atual pela conversa (feature 328).
- Sem valores em dinheiro no funil (o Pipeline de Vendas já mostra a venda, com o acesso dele).

## Fora de escopo

- Automações (lembrete de orçamento parado, pós-evento): Fase 6.
- Tempo de primeira resposta.
- Funil de pessoas (deduplicar a mesma cliente em dois canais).
- Valores em dinheiro e comissão no funil.
- Marcos editáveis à mão.

## Verificação (`verify_335.py`, contra o `manto_local`)

Molde do `verify_334`: conexão separada, Meta dublê e disjuntor de rede; tudo leva `v335-`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Ficha com conversa, anúncio, orçamento enviado, formulário, evento, pagamento e avaliação | cada marco uma vez, data certa, do mais novo para o mais antigo | não |
| 2 | Evento cancelado da mesma ficha | some da linha do tempo, com o pagamento e a avaliação dele | não |
| 3 | Financeiro e Casting na ficha | Financeiro vê os marcos sem os links de conversa e orçamento; Casting recebe 403 | **sim** |
| 4 | Funil com conversas em etapas diferentes | as contagens e as porcentagens de cada etapa | não |
| 5 | Conversa de fora do período; evento antigo da mesma ficha | não contam; o fato anterior ao primeiro contato não faz andar | não |
| 6 | Filtros de canal e campanha; tabela por vendedor, campanha e canal | só o filtrado conta; a soma das linhas é o total | não |
| 7 | Quem parou em cada etapa | a lista de "Orçamento enviado" sem quem formulou ou fechou | não |
| 8 | Financeiro e Casting no funil; período inválido | 403 para os dois; 422 com o campo | **sim** |
| 9 | Limpeza | registros e usuários de teste apagados | — |
