# Feature 345 — O sistema comanda o marketing: painel por frente, só autoral no anúncio, pedido de criativo e aprovação do dono

**Branch**: `345-marketing-integrado` (da `main`, `68f232a7`) · **Created**: 2026-11-16 · **Status**: Rascunho ·
**Migration**: uma, aditiva (marcação de licença no catálogo; campos novos no card de marketing; tabelas novas de
desempenho por anúncio, propostas e diário de decisões; teto por frente nas configurações) ·
**Nível**: 1 (feature) — constituição, Princípio VI

**Input**: pedido do dono (chat oficial de marketing, 16/11/2026): "O meu intuito maior é ter um sistema de
marketing extremamente competente, baseado em estudos e evidências recentes [...] seria interessantíssimo ter algo
agendado para refazer a leitura, vir com sugestões de melhoria, ver o que funciona e o que não funciona. E eu queria
atrelar tudo isso ao nosso sistema, para que fique tudo registrado por lá" → "Pode começar a spec da feature. Mas
vamos acelerar".

## O pedido, nas palavras do dono *(obrigatório)*

A Manto anuncia na Meta e no Google, mas ninguém sabe o que o dinheiro traz. A leitura de 16/11 mostrou o tamanho do
problema:

- Nos 90 dias anteriores, R$ 1.465 na Meta viraram 3 conversas no WhatsApp. As campanhas otimizavam para clique e
  compravam clique acidental.
- Nenhum dos 258 clientes de 2026 tem origem registrada no sistema.
- A rotina semanal da 256 (`/marketing/desempenho`) está parada desde 08/09, porque a chave dela não foi para o Render
  na migração.

O dono quer que o sistema seja o lugar onde o marketing se decide. Em vez de "acho que funcionou", os números de cada
frente de negócio, que hoje são quatro:

- **corporativo**: público adulto e empresarial; as vendas grandes;
- **social**: 15 anos e casamento;
- **EducaManto**: escolas, teatro musical autoral;
- **festas**: precisam continuar crescendo.

O objetivo é encher janeiro a julho, que hoje são fracos, e trazer cliente novo.

Ele quer tirar da Gabi (foto e arte) a parte administrativa do Gerenciador de Anúncios e deixá-la no criativo, junto
com a Erika (vídeo). O sistema diz que peça fazer e o que ela precisa, elas produzem, e a peça vira anúncio. Ele também
quer que nada mude na Meta ou no Google sem a aprovação dele.

Duas regras de marca, ditas por ele:

- "É expressamente proibido fazermos anúncio com coisas que remetam a Disney, Hello Kitty e coisas mais licenciadas no
  geral". Só o autoral vai para anúncio.
- Nenhuma imagem gerada por IA. Um letreiro feito com IA por cima da foto real pode, "porque não distorce o
  personagem".

## Clarifications

### Session 2026-11-16

O dono pediu "vamos acelerar". As questões abaixo foram decididas sem pergunta, cada uma com o porquê:

- Q: De onde vem a frente de cada **venda**? → A: de regra derivada do evento que já existe, sem campo novo na Agenda.
  - `(EDU` no título ou tipo `EDUCAMANTO` → EducaManto.
  - Tipo `CORP` → corporativo.
  - "15 anos", "debut", "casamento", "noiv" ou "bodas" no título → social.
  - Tipo `VM` ou `VIRTUAL` → loja virtual.
  - O resto → festas.
  - Porquê: é a regra com que os números de 16/11 foram tirados. Um campo novo no evento mexeria no domínio mais
    frágil do sistema (`docs/00` §7).
- Q: De onde vem a frente de cada **campanha**? → A: do começo do nome (`CORP`, `SOCIAL`, `EDU`, `FESTA`, `LOJA`). O que
  não casa fica "sem frente", numa lista para alguém corrigir à mão, e a correção vale para as próximas leituras.
  - Porquê: a convenção de nome já era prática da V4 e funciona igual na Meta e no Google.
- Q: Qual o teto de custo por venda de cada frente? → A: o padrão é 25% da margem bruta mediana da frente nos últimos
  12 meses (venda − cachês − gastos do evento). O Superadmin pode trocar o valor de cada frente.
  - Os números de 16/11 dão como ponto de partida: festas ~R$ 575, corporativo ~R$ 1.070, social ~R$ 550 e EducaManto
    ~R$ 4.500. EducaManto e social têm só 2 vendas cada, então o valor é provisório.
- Q: Quem aprova as propostas? → A: só quem estiver na lista de aprovadores de marketing, nas Configurações. O padrão é o
  dono.
  - Porquê: a Gabi e a Erika são Superadmin. Se o portão fosse "Superadmin", elas aprovariam o próprio gasto, e o dono
    pediu o contrário.
- Q: E o tema do catálogo que ainda não foi classificado? → A: conta como **não pode anunciar**.
  - Porquê: o risco é jurídico, e na dúvida a peça não sai.
  - A rotina propõe a classificação em lote dos 476 temas, e a equipe confirma.
- Q: A rotina pode criar anúncio sem aprovação? → A: pode criar **pausado**, porque anúncio pausado não gasta. Ativar,
  pausar, mudar verba e mudar público são sempre propostas com aprovação.
- Q: "Custo por venda" sem saber de onde veio cada cliente? → A: nesta feature é o custo **misto**: o gasto da frente ÷
  as vendas fechadas da frente no período. A tela diz isso com todas as letras.
  - O custo atribuído (só as vendas que vieram do anúncio) depende do CRM próprio no ar e fica para a feature seguinte.

## Cenários e Verificação *(obrigatório)*

### História 1 — O dono vê, por frente, quanto gastou e quanto vendeu (Prioridade: P1)

Na segunda de manhã, o dono abre o Desempenho de marketing e vê a semana anterior separada por frente. Cada frente
mostra:

- o gasto na Meta e no Google;
- as conversas e os cadastros que os anúncios trouxeram;
- as vendas fechadas e quantas delas foram de cliente novo;
- o custo por venda (misto) ao lado do teto.

Se uma frente estoura o teto, o painel avisa. Ninguém exportou planilha: a rotina semanal leu a Meta e o Google pelos
conectores e gravou no sistema.

**Por que esta prioridade**: sem esse número, toda outra decisão é chute. É o que faltou para julgar a V4.

**Verificação**: cenários 1 a 5 do `verify_345.py`. Eles provam três coisas: a ingestão por anúncio é idempotente, a
frente sai do nome da campanha (com a correção manual) e o custo por venda por frente bate com a conta à mão sobre
eventos semeados.

**Cenários de aceite**:

1. **Dado** uma leitura com campanhas `FESTA · MSG · ...` e `CORP · BUSCA · ...`, **Quando** a rotina grava a semana,
   **Então** o gasto de cada uma aparece na frente certa e a campanha `Teste qualquer` aparece em "sem frente".
2. **Dado** 3 vendas de festa fechadas na semana e R$ 900 de gasto em `FESTA`, **Quando** o dono abre o painel,
   **Então** a frente festas mostra custo por venda de R$ 300,00 e nenhum aviso, porque o teto é R$ 575,00.
3. **Dado** uma frente com gasto e nenhuma venda, **Quando** o dono abre o painel, **Então** o custo por venda aparece
   como "sem venda no período" com o gasto em destaque, e não como zero nem como infinito.
4. **Dado** a mesma leitura enviada duas vezes, **Quando** a rotina grava, **Então** nada duplica.
5. **Dado** o Google ainda não conectado, **Quando** a rotina roda, **Então** o painel mostra a Meta e diz que o Google
   está sem conexão, em vez de mostrar gasto zero.

---

### História 2 — Só tema autoral pode virar anúncio (Prioridade: P1)

Cada tema do catálogo tem uma marcação de licença: **autoral**, **licenciado** ou **não classificado**.

- A rotina propõe a classificação dos temas em lote, com o motivo de cada um ("personagem da Disney").
- A Gabi ou o dono confirmam numa lista, de uma vez.
- Pedido de criativo, card de anúncio e proposta de anúncio só aceitam tema autoral. O sistema recusa os outros no
  servidor, não só na tela.

**Por que esta prioridade**: é risco jurídico, e é a regra que tudo o mais respeita.

**Verificação**: cenários 6 a 8 do `verify_345.py`.

**Cenários de aceite**:

1. **Dado** um tema "licenciado", **Quando** alguém tenta abrir um pedido de criativo ou um card de anúncio com ele,
   **Então** o sistema recusa com a mensagem "Este tema é licenciado e não pode ir para anúncio".
2. **Dado** um tema "não classificado", **Quando** a rotina tenta usá-lo, **Então** é recusado do mesmo jeito.
3. **Dado** 30 temas com classificação proposta, **Quando** a Gabi confirma a lista, **Então** os 30 mudam numa ação
   só, e cada mudança fica registrada com quem confirmou.
4. **Dado** um card de **post orgânico** com tema licenciado, **Quando** ele é salvo, **Então** nada é recusado. A regra
   vale só para anúncio. Post orgânico continua como hoje.

---

### História 3 — A rotina pede o criativo, a Gabi e a Erika produzem (Prioridade: P2)

Toda segunda a rotina olha o que funcionou e abre cards de **pedido de criativo** no Kanban de marketing. Cada card
traz o briefing:

- a frente e o objetivo ("conversas de festa em Alphaville");
- o formato (foto 4:5, story 9:16, vídeo de 15–30 s);
- o que mostrar, com o tema autoral do catálogo;
- o texto do letreiro;
- a data de entrega.

Foto e arte vão para a responsável por foto (Gabi); vídeo, para a responsável por vídeo (Erika). As duas são definidas
nas Configurações.

A peça segue o fluxo que já existe: produção, depois Revisão de mídia, depois pronto. Card **pronto** do tipo anúncio
vira anúncio montado **pausado** na Meta ou no Google. O card guarda o vínculo com esse anúncio e passa a mostrar o
resultado da peça: gasto, conversas e custo por conversa.

**Por que esta prioridade**: tira a Gabi do Gerenciador e fecha o ciclo entre peça e resultado. Hoje ninguém sabe qual
foto trouxe cliente.

**Verificação**: cenários 9 a 11 do `verify_345.py`.

**Cenários de aceite**:

1. **Dado** um pedido de vídeo criado pela rotina, **Quando** ele aparece no Kanban, **Então** está na coluna Ideia,
   atribuído à responsável por vídeo, com todos os campos do briefing preenchidos.
2. **Dado** um card de anúncio pronto com a peça aprovada na Revisão, **Quando** a rotina monta o anúncio pausado,
   **Então** o card mostra o vínculo com o anúncio e a situação "Montado, aguardando aprovação".
3. **Dado** um card vinculado a um anúncio que rodou na semana, **Quando** a rotina grava as métricas, **Então** o card
   mostra o gasto, as conversas e o custo por conversa da peça.

---

### História 4 — Nada muda na Meta ou no Google sem o "pode" do dono (Prioridade: P2)

A rotina não executa mudança de gasto por conta própria: ela **propõe**. Os tipos de proposta são ativar anúncio
montado, pausar, mudar verba e mudar público.

Cada proposta diz:

- o que muda;
- quanto custa por dia ou por mês;
- o motivo, com o número que o sustenta ("custo por conversa R$ 21, o dobro do teto de festas").

O dono aprova ou recusa no sistema, inclusive pelo celular. Na rodada seguinte a rotina executa só o aprovado e marca
o resultado: executada, ou falhou com o motivo. Proposta sem resposta em 7 dias expira.

**Por que esta prioridade**: é a condição do dono para tirar o Gerenciador da mão da equipe sem perder o controle do
dinheiro.

**Verificação**: cenários 12 a 14 do `verify_345.py`. Eles incluem um aprovador que não está na lista. Esse cenário
**deve falhar**.

**Cenários de aceite**:

1. **Dado** uma proposta pendente, **Quando** um Superadmin que não está na lista de aprovadores tenta aprovar, **Então**
   recebe 403 e a proposta continua pendente.
2. **Dado** uma proposta aprovada, **Quando** a rotina roda, **Então** ela a recebe na lista "a executar". Depois de
   executar, marca "executada" com a data, e a proposta não volta a aparecer.
3. **Dado** uma proposta recusada ou expirada, **Quando** a rotina roda, **Então** ela não aparece na lista "a executar".

---

### História 5 — Diário de decisões: o que mudou, por quê e se deu certo (Prioridade: P3)

Toda proposta executada vira uma entrada no diário de marketing, e pessoas também podem escrever entradas. Cada entrada
registra:

- o que mudou e por quê;
- a evidência;
- o resultado esperado;
- uma data para reavaliar (padrão: 14 dias).

Quando a data chega, a rotina escreve o resultado observado com os números e diz se funcionou ou não. O dono lê o
diário no Desempenho.

**Por que esta prioridade**: é como o sistema "aprende". Sem registro, a mesma aposta ruim se repete a cada agência.

**Verificação**: cenário 15 do `verify_345.py`.

**Cenários de aceite**:

1. **Dado** uma proposta executada, **Quando** a rotina marca a execução, **Então** nasce uma entrada no diário com o
   motivo da proposta e a data de reavaliação.
2. **Dado** uma entrada que venceu, **Quando** a rotina roda, **Então** ela aparece na lista "a reavaliar". Depois que a
   rotina grava o resultado, sai da lista.

### Casos de borda

- **Campanha renomeada no meio do período**: a frente segue o nome mais recente da campanha. A correção manual vence o
  nome.
- **Anúncio apagado na Meta**: o card mantém o vínculo e o histórico já gravado, e mostra "anúncio não existe mais".
- **Venda cancelada depois de contada**: some da conta na leitura seguinte. O custo por venda é sempre recalculado, nunca
  congelado.
- **Evento em grupo (satélites)**: conta uma venda só, a do líder. Cortesia e permuta não contam.
- **Proposta aprovada sobre um alvo que mudou** (o anúncio foi pausado à mão, por exemplo): a rotina não executa, marca
  "falhou: o anúncio já estava pausado" e registra no diário.
- **Moeda diferente de BRL na leitura**: a linha é recusada com motivo, como já faz a 256 (`skipped_currency`).
- **Dois aprovadores clicam juntos**: a primeira decisão vale. A segunda recebe 409 "já decidida".

## Requisitos *(obrigatório)*

### Requisitos funcionais

**Painel por frente (H1)**

- **FR-001**: O sistema DEVE gravar o desempenho **por anúncio e por dia**, de forma idempotente: plataforma, anúncio,
  conjunto, campanha, gasto, impressões, alcance, cliques, conversas iniciadas e cadastros/resultados. A gravação reusa
  a entrada autenticada por token da 256.
- **FR-002**: O sistema DEVE derivar a frente da campanha pelo prefixo do nome (`CORP`, `SOCIAL`, `EDU`, `FESTA`,
  `LOJA`, sem diferenciar maiúsculas) e DEVE permitir a correção manual, que vence o nome.
- **FR-003**: O sistema DEVE derivar a frente de cada venda pela regra da Clarification 1 e DEVE dizer, para cada venda
  do período, se o cliente é novo (sem evento anterior no sistema).
- **FR-004**: O sistema DEVE calcular, por frente e período:
  - o gasto;
  - as conversas;
  - as vendas fechadas (data da venda no período, sem cortesia, satélite nem cancelado);
  - as vendas de cliente novo;
  - o custo por venda misto (gasto ÷ vendas);
  - a comparação com o teto da frente.
- **FR-005**: O sistema DEVE mostrar um aviso na frente cujo custo por venda passou do teto, e um estado próprio quando
  há gasto sem venda.
- **FR-006**: O sistema DEVE mostrar, por plataforma, quando foi a última leitura e se ela está sem conexão.
- **FR-007**: O Superadmin DEVE poder editar o teto de cada frente. O valor padrão sai da regra da Clarification 3 e
  aparece com a base do cálculo ("25% da margem mediana de 294 vendas").

**Licença dos temas (H2)**

- **FR-008**: Cada tema do catálogo DEVE ter a marcação **autoral | licenciado | não classificado** (padrão: não
  classificado), com quem marcou e quando.
- **FR-009**: Marketing e Superadmin DEVEM poder confirmar várias marcações numa ação só, a partir das sugestões da
  rotina (sugestão + motivo).
- **FR-010**: O servidor DEVE recusar com 422 todo pedido de criativo, card de anúncio ou proposta de anúncio cujo tema
  não seja autoral. Post orgânico não é afetado.

**Pedido de criativo (H3)**

- **FR-011**: O card do Kanban de marketing DEVE ganhar quatro informações:
  - o **tipo**: post orgânico ou anúncio;
  - a **frente**;
  - o **formato**: foto 1:1, foto 4:5, story/reels 9:16 foto, vídeo 9:16 ou vídeo 1:1;
  - o **briefing**: objetivo, o que mostrar e texto do letreiro.

  O card também DEVE registrar a **origem** (rotina ou pessoa) e os **anúncios vinculados**.
- **FR-012**: A rotina DEVE poder abrir pedidos de criativo pelo token. Pedido de foto ou arte vai para a responsável por
  foto; pedido de vídeo, para a responsável por vídeo. As duas são definidas nas Configurações.
- **FR-013**: O card de anúncio DEVE mostrar o resultado somado dos anúncios vinculados: gasto, conversas e custo por
  conversa.
- **FR-014**: A rotina DEVE receber a lista de cards de anúncio **prontos** e ainda sem anúncio, e DEVE poder registrar o
  vínculo depois de montar o anúncio pausado.

**Propostas e aprovação (H4)**

- **FR-015**: A rotina DEVE poder registrar propostas. Cada proposta tem:
  - o tipo: ativar, pausar, verba ou público;
  - a plataforma e o alvo;
  - o valor antes e depois;
  - o custo estimado por dia;
  - o motivo e a evidência.
- **FR-016**: Só os usuários da lista de aprovadores de marketing DEVEM poder aprovar ou recusar. A decisão é única
  (409 na segunda) e registra quem decidiu e quando.
- **FR-017**: A rotina DEVE receber só as propostas aprovadas e ainda não executadas, e DEVE marcar cada uma como
  executada ou falhou (com motivo).
- **FR-018**: Proposta pendente há mais de 7 dias DEVE expirar e não pode mais ser aprovada.

**Diário (H5)**

- **FR-019**: Toda proposta executada DEVE gerar uma entrada no diário, e Marketing e Superadmin DEVEM poder escrever
  entradas à mão.
- **FR-020**: A rotina DEVE receber as entradas com reavaliação vencida e DEVE poder gravar o resultado observado
  (texto + números + funcionou: sim/não/inconclusivo).

**Texto e regras de marca**

- **FR-021**: Todo texto de tela e de briefing segue o tom interno operacional da constituição §XV.
- **FR-022**: O briefing DEVE sempre dizer "use foto do acervo da Manto; letreiro pode ser feito com IA; personagem e
  fundo nunca". A regra de imagem fica escrita no próprio pedido.

### Entidades *(se houver dados)*

- **Frente de negócio**: lista fixa (corporativo, social, educamanto, festas, loja virtual) com teto editável, em
  `SiteSetting` (singleton, `docs/00` §6 item 13). Também nas Configurações: a lista de aprovadores e as duas
  responsáveis por criativo.
- **Desempenho por anúncio** (nova): uma linha por plataforma + anúncio + dia, com métricas e ids de campanha e conjunto.
  É única por (plataforma, anúncio, dia). Convive com `marketing_campaign_metrics` da 256, que segue sendo o resumo por
  campanha.
- **Frente da campanha** (nova, pequena): correção manual por plataforma + id da campanha → frente.
- **Licença do tema**: colunas novas em `CatalogItem` (licença, quem marcou e quando, sugestão e motivo da rotina).
- **Card de marketing** (`MarketingPost`, existente): ganha tipo, frente, formato, briefing (objetivo, o que mostrar,
  letreiro) e origem. Os vínculos com anúncios vão numa tabela própria (plataforma, id do anúncio).
- **Proposta** (nova): tipo, plataforma, alvo, antes/depois, custo estimado, motivo, evidência, situação (pendente →
  aprovada/recusada/expirada → executada/falhou), quem decidiu e quando, quando executou e o resultado.
- **Entrada do diário** (nova): o que mudou, motivo, evidência, resultado esperado, data de reavaliação, resultado
  observado, veredito e origem (proposta ou pessoa).

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

- `GET /api/marketing/desempenho` (alterado: ganha o bloco por frente) — MARKETING, SUPERADMIN.
- `PATCH /api/marketing/campanhas/<plataforma>/<id>/frente` — MARKETING, SUPERADMIN.
- `GET|PATCH /api/marketing/frentes` (teto) — leitura MARKETING, SUPERADMIN; escrita SUPERADMIN.
- `GET /api/marketing/temas-licenca` e `POST /api/marketing/temas-licenca/confirmar` — MARKETING, SUPERADMIN.
- `POST|PATCH /api/marketing/posts` (alterado: campos novos + recusa de tema não autoral em card de anúncio) —
  MARKETING, SUPERADMIN, como hoje.
- `GET /api/marketing/propostas` — MARKETING, SUPERADMIN. `POST /api/marketing/propostas/<id>/decidir` — **só a
  lista de aprovadores** (403 para os outros, Superadmin incluso).
- `GET|POST /api/marketing/diario` — MARKETING, SUPERADMIN.
- Agente (`/api/marketing-agent/<token>/…`, molde da 256, 404 sem token): ingestão por anúncio, sugestões de licença,
  pedidos de criativo, cards prontos sem anúncio, vínculo de anúncio, propostas (criar / a executar / marcar) e diário
  (a reavaliar / gravar resultado).
- Linhas novas na tabela de `docs/01` §4.3.

## Verificação (`verify_345.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/345-marketing-integrado/verify_345.py`, contra `manto_local` (`DATABASE_URL` de `.local-db-url`,
`FLASK_ENV=development`, `MANTO_SEM_THREADS=1`). Login só por `POST /api/auth/login`. Escrita conferida por conexão
separada. Limpeza no `finally`. O token do agente vem de variável de ambiente local do verify, não do arquivo de
produção.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | ingestão de 3 anúncios × 2 dias, enviada duas vezes | upsert idempotente por (plataforma, anúncio, dia) | não |
| 2 | campanhas `FESTA ·`, `corp ·`, `Teste` | prefixo sem diferenciar maiúsculas; "sem frente" listada | não |
| 3 | correção manual da frente de `Teste` → EDU | correção vence o nome nas leituras seguintes | não |
| 4 | 3 vendas de festa semeadas + R$ 900 em FESTA; 1 satélite e 1 cortesia no meio | custo por venda R$ 300,00; satélite e cortesia fora; cliente novo contado | não |
| 5 | frente com gasto e zero venda; plataforma Google sem leitura | estado "sem venda" e "sem conexão" no payload | não |
| 6 | card de anúncio com tema licenciado e com tema não classificado | 422 nos dois | **sim** |
| 7 | card de post orgânico com tema licenciado | 200 (regra só para anúncio) | não |
| 8 | confirmação em lote de 3 sugestões | 3 temas mudam; autor e data gravados | não |
| 9 | agente abre pedido de vídeo | card em Ideia, responsável = responsável por vídeo, briefing completo | não |
| 10 | agente lista cards prontos sem anúncio e grava vínculo | some da lista; card mostra o vínculo | não |
| 11 | métricas de anúncio vinculado | card soma gasto e conversas; custo por conversa certo | não |
| 12 | Superadmin fora da lista de aprovadores tenta aprovar | 403; proposta segue pendente | **sim** |
| 13 | aprovador aprova; segunda decisão concorrente | 200 e depois 409 "já decidida" | não / **sim** |
| 14 | agente lista "a executar", marca executada; proposta de 8 dias | executada some da lista; a de 8 dias expira e não aprova | não |
| 15 | execução gera diário; reavaliação vencida aparece e sai depois do resultado | ciclo do diário | não |
| 16 | papel sem acesso (CASTING) chama desempenho, propostas e diário | 403 | **sim** |
| 17 | limpeza | usuários, temas, cards, propostas e linhas descartáveis apagados (`roles.clear()` antes do usuário) | — |

Conferência de tela no Browser pane (skill `manto-conferir-tela`):

- Desempenho, com o bloco por frente, as propostas e o diário: desktop e 390 px, porque o dono aprova pelo celular.
- Kanban, com o card de anúncio e o briefing.
- Lista de licença dos temas.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Toda segunda, até as 9h, o Desempenho mostra a semana anterior da Meta (e do Google, quando conectado) sem
  ninguém exportar planilha.
- **SC-002**: O dono responde "quanto custou cada venda de cada frente na semana?" olhando uma tela, em menos de 1
  minuto.
- **SC-003**: Zero anúncio montado ou proposto com tema licenciado ou não classificado.
- **SC-004**: 100% das mudanças de gasto feitas pela rotina na Meta ou no Google têm aprovação registrada **antes** da
  execução e entrada no diário.
- **SC-005**: Em 4 semanas de uso, a Gabi não precisa abrir o Gerenciador de Anúncios para nenhuma tarefa de rotina.
- **SC-006**: Cada pedido de criativo traz frente, formato, o que mostrar, letreiro e prazo. Quem produz não precisa
  perguntar nada para começar.
- **SC-007**: Toda decisão executada tem data de reavaliação, e 100% das que venceram têm resultado registrado na rodada
  seguinte.

## Fora de escopo

- **Atribuição Google → WhatsApp** (link com código lido pelo CRM) e **devolução da venda fechada** à Meta e ao Google
  (`ctwa_clid`, conversões offline). Dependem do CRM próprio (325–335) no ar e são a feature seguinte. Até lá o custo por
  venda é misto.
- A virada do CRM próprio (Fase 4) e o cancelamento do Tintim.
- Criar campanha ou conjunto do zero pela rotina sem proposta. Nesta feature a rotina monta só **anúncio pausado** dentro
  de campanha que já existe.
- Geração de imagem ou vídeo por IA (proibida pelo dono). Só o letreiro pode.
- LinkedIn, TikTok e outras plataformas.
- Campo "frente" no evento da Agenda (a regra derivada basta por ora).

## Docs a atualizar

- `docs/01`: §Agente de marketing, para os endpoints novos do agente e as tabelas novas; e §4.3, com as linhas de RBAC.
- `docs/02`: `/marketing/desempenho`, o Kanban e a lista de licença dos temas.
- `docs/03`: entrada no topo.
- `docs/04`: §Marketing, para a regra da frente, o custo misto, o autoral-only e o ciclo de proposta.
- `docs/05`: a dívida "custo por venda misto até a atribuição", e riscar a "rotina 256 parada" quando o token voltar ao
  Render.

## Premissas

- **Onde a rotina roda:** no PC do dono, como a 256, numa tarefa agendada do Claude com os conectores da Meta e do Google.
  Ela fala com o sistema só pela entrada autenticada por token. O sistema não chama a Meta nem o Google direto.
- **Pré-requisitos do dono:**
  - pôr `MARKETING_AGENT_TOKEN` de volta no `manto-backend` do Render;
  - ligar o Google Ads: projeto no Google Cloud com a Google Ads API no nível Explorer. Não precisa mais de developer
    token nem de conta MCC desde 09/09/2026.
  - Sem o Google, a feature funciona só com a Meta.
- **Responsáveis por criativo:** a responsável por foto é a Gabi (Gabriella) e a responsável por vídeo é a Erika. Os
  usuários já existem e são definidos nas Configurações.
- **Aprovadores:** o único aprovador padrão é o dono.
- **Classificação inicial dos temas:** a rotina sugere e uma pessoa confirma. A rotina nunca marca sozinha.
- **Moeda e janelas:** BRL. As janelas e as datas de venda seguem as convenções da `skill financeiro` (venda pela
  `sale_date`; o líder do grupo representa o grupo).
