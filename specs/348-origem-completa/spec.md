# Feature 348 — Origem completa: de qual anúncio, clique ou conversa veio cada venda

**Branch**: `348-origem-completa` (da `main`, `20bf93c0`) · **Created**: 2026-11-17 · **Status**: Rascunho ·
**Migration**: uma, aditiva, revisão com prefixo `a348` sobre `d334b2c4e6f8` (colunas novas em conversa, anúncio,
orçamento, evento e ficha; uma tabela nova de códigos do site; preenchimento retroativo do `ctwa_clid`) ·
**Nível**: 1 (feature) — constituição, Princípio VI

**Input**: pesquisa "Máquina de vendas Manto" (17/11/2026), seções 6, 8.1 e 8.2; a 8.5 dividiu o trabalho em quatro
features abertas ao mesmo tempo (348 origem completa, 349 comercial mede e fecha, 350 base autorizada, 351 painel
atribuído). Esta é a 348.

## O pedido, nas palavras do dono *(obrigatório)*

A conclusão da pesquisa foi "medir primeiro, escalar depois". Hoje o caminho anúncio → conversa → orçamento → evento
→ receita **para no clique**:

- O aviso da Meta traz o `ctwa_clid` (o identificador do clique no anúncio de WhatsApp) e o sistema não o lê; sem ele,
  a venda nunca volta para a Meta.
- A consulta à Meta pede o anúncio e a campanha, não o conjunto de anúncios.
- O site não guarda nada do Google: o clique sai para o `wa.me` e o `gclid` fica para trás.
- A conversa só chega ao evento pela ficha. Cliente recorrente mistura duas vendas: a segunda festa herda o anúncio da
  primeira.
- A frente da venda é adivinhada pelo título (dívida 215 do `docs/05`): evento social sem "15 anos" ou "casamento" no
  título cai em festas.
- O Desempenho casa o lead com a campanha pelo **nome**: campanha renomeada perde os leads.

Decisões do dono que valem aqui: nada muda na Meta, no Google ou no WhatsApp de produção; o link do Google na avaliação
continua só para nota 5 (fora desta feature); o CRM segue desligado até as chaves `WHATSAPP_*` no Render.

## Clarifications

### Session 2026-11-17

Fluxo autônomo (sem pergunta ao dono); cada decisão com o porquê:

- Q: Quando o site cria o código de referência? → A: no primeiro carregamento de uma visita que chega com marcador de
  clique ou de campanha (`gclid`, `gbraid`, `wbraid`, `fbclid`, `gad_campaignid`, `utm_*`). Visita sem marcador não
  ganha código e a mensagem pronta fica como hoje.
  - Porquê: o código serve para ligar um clique pago (ou de campanha) a uma conversa. Criar código para toda visita
    encheria a tabela de linhas sem uso e não diz nada que o WhatsApp sozinho não diga.
- Q: O código vale por quanto tempo? → A: 90 dias, no navegador e no servidor. Clique novo (marcadores diferentes) troca
  o código.
  - Porquê: 90 dias é a janela máxima do Google para conversão offline; a festa fecha cedo, o corporativo demora.
- Q: Como é o código e onde aparece? → A: cinco caracteres de um alfabeto sem letras e números ambíguos (sem 0/O,
  1/I/L), com `#` na frente, numa linha própria no fim da mensagem pronta: "Código do site: #A7K2Q".
  - Porquê: curto para não assustar quem manda a mensagem, longo o bastante para não colidir nem ser casado por acaso
    com outro texto da cliente.
- Q: O código é lido só na primeira mensagem da conversa? → A: em qualquer mensagem de texto recebida da cliente; cada
  código liga uma única conversa (o primeiro uso vence).
  - Porquê: a conversa é uma por telefone. A cliente que volta meses depois por outro clique está numa conversa antiga;
    a "primeira mensagem" dela é a do novo contato, não a primeira da conversa.
- Q: Qual contato de origem fica em cada venda? → A: o contato por anúncio, publicação ou site mais recente da mesma
  conversa, dentro dos 90 dias anteriores ao momento em que a venda (orçamento ou evento) é ligada à conversa. Fica
  congelado na venda.
  - Porquê: a conversa é uma por cliente; congelar o contato por venda é o que impede a segunda festa de herdar o
    anúncio da primeira. Duas vendas dentro da mesma janela, do mesmo anúncio, são as duas desse anúncio (o que é
    verdade).
- Q: Como o evento ganha a conversa nesta feature? → A: de dois jeitos: (1) pelo orçamento que foi enviado pela
  conversa (feature 333), quando o evento é criado a partir dele ou o orçamento é ligado ao evento; (2) pela criação do
  evento com a conversa informada, que é o contrato que a 349 ("Criar evento" na conversa) vai usar. Nunca pela ficha.
  - Porquê: ligar pela ficha é justamente o que mistura as vendas do cliente recorrente.
- Q: A frente vira coluna obrigatória? → A: coluna do evento, escolhida na aba Comercial. A regra atual pelo título
  vira **sugestão**:
  - sugestão **certa** (EducaManto pelo `(EDU`/tipo, corporativo pelo tipo `CORP`, social pela palavra no título, loja
    pelo tipo `VM`/`VIRTUAL`) já vem selecionada;
  - sugestão **por exclusão** (o "resto vai para festas") não vem selecionada: quem registra a venda escolhe.
  - Salvar a aba Comercial com valor de venda e sem frente escolhida é recusado (só para o bundle novo, que manda o
    campo).
  - Porquê: é o único jeito de "social sem a palavra certa não cair em festas" sem esvaziar o histórico. O evento antigo
    sem frente continua lido pela regra (marcado como "sugerida"), e os números de 16/11 da 345 não mudam.
- Q: Quem lê a frente? → A: uma função única de leitura (Python e SQL), que a 345 passa a usar e a 351 vai consumir: a
  frente gravada, e na falta dela a sugestão pela regra, com a marca "definida" ou "sugerida".
- Q: Como o lead casa com a campanha pelo id? → A: a ficha passa a guardar o id da campanha de origem (do anúncio da
  Meta, quando a consulta responde; do `gad_campaignid`/`utm_id` do clique no site). O Desempenho agrupa as campanhas
  por plataforma e id e casa a ficha pelo id; a ficha sem id (Kommo, formulário antigo) continua casando pelo nome.
  - Porquê: a campanha renomeada no meio do período deixa de partir em duas linhas e de perder os leads.
- Q: Precisa de consentimento para guardar os marcadores? → A: não nesta feature. Os marcadores são do próprio site, não
  identificam a pessoa sozinhos e servem à atribuição da venda da própria Manto; nada vai para a Meta ou o Google aqui.
  O aviso de privacidade do site ainda não fala deles: fica como pendência do dono (Premissas).
- Q: O código não usado é apagado depois de vencer? → A: não nesta feature. Depois de 90 dias ele só deixa de ligar
  conversa; a linha fica.
  - Porquê: ela não tem dado pessoal (só marcadores do clique e a página), o volume é de dezenas por dia e a limpeza
    pode entrar junto da feature de conversões para o Google, que é quem decide o que reenviar. Registrado como dívida.
- Q: Em que páginas do site o código é criado? → A: em todas as do site público, menos as da loja virtual (rota `/v` e
  o domínio `alo.`): a loja tem contagem de visita própria (344) e não vende pelo WhatsApp.

## Cenários e Verificação *(obrigatório)*

### História 1 — O clique no anúncio de WhatsApp fica guardado (Prioridade: P1)

A cliente clica num anúncio "clique para o WhatsApp" e manda a primeira mensagem. O sistema guarda, junto do contato
pelo anúncio que a 334 já registra, o identificador do clique (`ctwa_clid`). As conversas que chegaram antes desta
feature ganham o identificador a partir da mensagem crua que ficou guardada. A consulta à Meta passa a trazer também o
conjunto de anúncios.

**Por que esta prioridade**: sem o `ctwa_clid` a venda nunca volta para a Meta (feature "conversões para a Meta"), e
ele só existe no aviso: o que não for guardado agora se perde.

**Verificação**: cenários 1 a 3 do `verify_348.py`.

**Cenários de aceite**:

1. **Dado** um aviso com `referral` de anúncio e `ctwa_clid`, **Quando** ele é processado, **Então** o contato pelo
   anúncio guarda o `ctwa_clid`.
2. **Dado** um contato por anúncio sem `ctwa_clid` e a mensagem crua com o `referral`, **Quando** a migration roda,
   **Então** o contato ganha o `ctwa_clid`; a mensagem crua corrompida não derruba a migration.
3. **Dado** um anúncio na fila, **Quando** a consulta à Meta responde, **Então** o anúncio guarda o id e o nome do
   conjunto, além da campanha.

---

### História 2 — O clique no Google (ou em outro link de campanha) chega à conversa (Prioridade: P1)

A pessoa clica num anúncio do Google e cai no site (catálogo ou formulário). O site guarda o `gclid` (ou `gbraid`,
`wbraid`) e os marcadores de origem, e cria um código curto. Quando ela toca no botão de WhatsApp (envio da lista de
desejos ou do formulário), a mensagem pronta leva "Código do site: #A7K2Q". Quando a mensagem chega na conversa, o
sistema reconhece o código e liga o clique àquela conversa.

**Por que esta prioridade**: é o furo do Google descrito na pesquisa (6.3): sem o código, o `gclid` nunca encontra o
telefone e nenhuma venda pode voltar para o Google.

**Verificação**: cenários 4 a 7 do `verify_348.py`; tela pública em 390 px.

**Cenários de aceite**:

1. **Dado** uma visita com `gclid` na URL, **Quando** a página abre, **Então** o site guarda os marcadores e o servidor
   cria um código com eles.
2. **Dado** um código guardado, **Quando** a pessoa envia a lista de desejos ou um formulário, **Então** a mensagem
   pronta leva a linha "Código do site: #XXXXX".
3. **Dado** uma mensagem recebida com um código válido, **Quando** o aviso é processado, **Então** o código fica ligado
   à conversa e a conversa ganha um contato de origem "site" com a campanha; a ficha sem origem ganha a origem "Site".
4. **Dado** um código já ligado a outra conversa, ou criado há mais de 90 dias, ou inexistente, **Quando** ele aparece
   numa mensagem, **Então** nada é ligado.
5. **Dado** uma visita sem marcador, **Quando** a pessoa envia a lista, **Então** a mensagem é a de hoje, sem código.

---

### História 3 — Cada venda sabe de qual conversa e de qual contato veio (Prioridade: P1)

A vendedora manda o orçamento pela conversa (333). O orçamento passa a guardar a conversa e o contato de origem daquele
momento. Quando o evento nasce do orçamento (ou o orçamento é ligado a um evento), o evento herda os dois. A 349 vai
criar o evento direto da conversa: o evento aceita a conversa na criação e escolhe o contato de origem do mesmo jeito.
A aba Comercial do evento mostra de onde a venda veio.

**Por que esta prioridade**: é a ligação que a venda atribuída (351) vai somar. Ligar pela ficha atribuiria a segunda
festa de uma cliente recorrente ao anúncio da primeira.

**Verificação**: cenários 8 a 11 do `verify_348.py`.

**Cenários de aceite**:

1. **Dado** uma conversa com contato por anúncio há 5 dias, **Quando** o orçamento é enviado por ela, **Então** o
   orçamento guarda a conversa e esse contato.
2. **Dado** uma conversa com um anúncio há 120 dias e outro há 5, **Quando** a segunda venda é ligada, **Então** ela
   fica com o anúncio de 5 dias, e a primeira venda continua com o dela.
3. **Dado** uma conversa só com contato de mais de 90 dias, **Quando** a venda é ligada, **Então** a venda guarda a
   conversa e nenhum contato de origem (orgânica).
4. **Dado** um orçamento com conversa, **Quando** um evento é criado a partir dele ou o orçamento é ligado ao evento,
   **Então** o evento herda a conversa e o contato; trocar ou desligar o orçamento leva junto o que veio dele.
5. **Dado** a criação de um evento com `conversa_id`, **Quando** ela termina, **Então** o evento guarda a conversa e o
   contato de origem; uma conversa inexistente é recusada no campo.

---

### História 4 — A frente é escolhida na venda (Prioridade: P2)

Na aba Comercial do evento, o card da venda ganha o campo "Frente". Quando o título diz com certeza a frente, ela vem
selecionada; quando não diz, o campo vem vazio com a sugestão por escrito, e salvar a venda pede a escolha. O painel de
marketing (345) e o futuro painel atribuído (351) leem a frente por uma função só.

**Por que esta prioridade**: tira a dívida 215 sem esvaziar o histórico; o 15 anos sem "15 anos" no título deixa de
virar festa.

**Verificação**: cenários 12 a 14 do `verify_348.py`; aba Comercial aberta no Browser pane (desktop e 390 px).

**Cenários de aceite**:

1. **Dado** o evento "Festa da Sofia" (sem palavra de social) vendido como social, **Quando** a vendedora escolhe
   "Social" e salva, **Então** a frente lida é social, definida.
2. **Dado** o mesmo evento sem frente e com valor de venda, **Quando** a aba Comercial é salva sem frente, **Então** a
   gravação é recusada com o campo "Frente" apontado.
3. **Dado** um evento antigo sem frente, **Quando** o painel lê a frente, **Então** recebe a da regra, marcada como
   sugerida, igual à de 16/11.
4. **Dado** um evento satélite de grupo, **Quando** a frente é lida, **Então** é a do principal.

---

### História 5 — O lead casa com a campanha pelo id (Prioridade: P2)

No Desempenho, a campanha renomeada no meio do período aparece numa linha só, e as fichas que vieram dela contam nessa
linha mesmo com o nome antigo gravado.

**Por que esta prioridade**: correção pequena (P na pesquisa), mas sem ela o custo por lead da 345 erra.

**Verificação**: cenário 15 do `verify_348.py`.

**Cenários de aceite**:

1. **Dado** duas linhas de métrica com o mesmo id de campanha e nomes diferentes, **Quando** o Desempenho monta a
   tabela, **Então** há uma linha só, com o nome mais recente e o gasto somado.
2. **Dado** uma ficha com o id dessa campanha e o nome antigo, **Quando** a tabela é montada, **Então** o lead conta
   nessa linha; a ficha sem id continua casando pelo nome.

### Casos de borda

- A pessoa apaga o código da mensagem: a conversa fica sem o clique (limite conhecido, pesquisa 6.3); nada quebra.
- A pessoa manda o mesmo código duas vezes ou em outra conversa: só o primeiro uso liga.
- Dois cliques diferentes no mesmo aparelho: o segundo troca o código guardado; o primeiro continua válido no servidor.
- O servidor fora do ar ao criar o código: a mensagem sai sem código, e a página nunca trava por isso.
- Aviso reenviado pela Meta: o contato pelo anúncio não duplica (chave da 334) e o código não religa.
- A mensagem crua da 325 corrompida ou sem `referral`: a migration pula a linha.
- A loja virtual (Papai Noel) tem contagem de visita própria (344) e não vende pelo WhatsApp: o código não é criado
  nas páginas da loja.
- Evento cancelado: a frente e a origem são dados de venda e seguem a regra única do cancelado (306) da aba Comercial.
- Conversa apagada: orçamento e evento perdem a conversa e o contato (SET NULL), a venda fica.

## Requisitos *(obrigatório)*

### Requisitos funcionais

**Anúncio da Meta (História 1)**

- **FR-001**: O contato por anúncio do WhatsApp DEVE guardar o `ctwa_clid` do `referral` quando ele vier.
- **FR-002**: A migration DEVE preencher o `ctwa_clid` dos contatos existentes a partir da mensagem crua guardada,
  pulando a mensagem corrompida ou sem o campo.
- **FR-003**: A consulta do anúncio à Meta DEVE pedir também o conjunto (id e nome) e guardá-lo; os anúncios já
  consultados voltam para a fila uma vez, para ganhar o conjunto.

**Site e Google (História 2)**

- **FR-004**: O site público DEVE guardar no navegador, por até 90 dias, os marcadores da visita: `gclid`, `gbraid`,
  `wbraid`, `fbclid`, `gad_campaignid`, `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term`, `utm_id`,
  a página de entrada e o site de procedência. Visita nova com marcadores diferentes substitui a anterior. As páginas
  da loja virtual não guardam nem criam código.
- **FR-005**: O servidor DEVE criar o código curto (cinco caracteres, UNIQUE) a partir dos marcadores, sem login, com
  limite de chamadas por endereço; pedido sem nenhum marcador é recusado.
- **FR-006**: A mensagem pronta do envio da lista de desejos e dos formulários públicos DEVE levar a linha "Código do
  site: #XXXXX" quando houver código válido guardado; sem código, a mensagem de hoje.
- **FR-007**: A resposta de formulário enviada com código DEVE ficar ligada a ele.
- **FR-008**: Falha ao criar o código NUNCA DEVE impedir a página de abrir, o formulário de ser enviado ou o WhatsApp de
  abrir.
- **FR-009**: Toda mensagem de texto recebida no WhatsApp DEVE ser lida à procura de código; o código existente, criado
  há no máximo 90 dias e ainda sem conversa DEVE ser ligado à conversa (o primeiro uso vence) e virar um contato de
  origem "site" da conversa, com a campanha.
- **FR-010**: A ficha sem origem DEVE ganhar a origem "Site" e a campanha do primeiro contato pelo site, como a 334 faz
  com o anúncio.

**Ligação com a conversa (História 3)**

- **FR-011**: O primeiro envio de um orçamento pela conversa DEVE gravar no orçamento a conversa e o contato de origem
  daquele momento; envio seguinte não troca.
- **FR-012**: O contato de origem de uma venda DEVE ser o contato por anúncio, publicação ou site mais recente da mesma
  conversa, nos 90 dias anteriores ao momento da ligação; sem contato na janela, nenhum (venda orgânica).
- **FR-013**: O evento criado a partir de um orçamento, ou ligado a um orçamento, DEVE herdar a conversa e o contato do
  orçamento; trocar ou desligar o orçamento DEVE levar junto o que veio dele, sem apagar uma ligação feita por outro
  caminho.
- **FR-014**: A criação do evento DEVE aceitar a conversa (`conversa_id`, opcional) e gravar nela a conversa e o
  contato de origem; conversa inexistente é recusada no campo, antes do Google.
- **FR-015**: Nenhum caminho DEVE ligar uma venda a uma conversa pela ficha da cliente.
- **FR-016**: O detalhe do evento DEVE trazer, no bloco comercial, a conversa e o contato de origem (tipo, anúncio ou
  campanha, quando), e a aba Comercial DEVE mostrá-los.

**Frente (História 4)**

- **FR-017**: O evento DEVE ter a frente como campo próprio, com os valores das frentes da 345.
- **FR-018**: Uma função única DEVE dizer a frente de um evento: a gravada (definida) ou, na falta dela, a da regra
  pelo título (sugerida), em Python e em SQL com o mesmo resultado; o satélite responde com a do principal. O painel da
  345 DEVE passar a usá-la.
- **FR-019**: A aba Comercial DEVE mostrar o campo "Frente": a sugestão certa vem selecionada; a sugestão por exclusão
  vem como texto, com o campo vazio.
- **FR-020**: Salvar a aba Comercial com o campo "frente" no corpo, valor de venda maior que zero e nenhuma frente (nem
  no corpo nem gravada) DEVE ser recusado com o campo apontado; corpo sem o campo (bundle antigo) não mexe na frente.
- **FR-021**: A criação do evento DEVE aceitar a frente (opcional) e, sem ela, gravar só a sugestão certa.
- **FR-022**: Frente fora da lista DEVE ser recusada no campo.

**Lead e campanha (História 5)**

- **FR-023**: A ficha DEVE guardar o id da campanha de origem quando ele for conhecido (anúncio da Meta consultado,
  clique no site com `gad_campaignid` ou `utm_id`).
- **FR-024**: O Desempenho DEVE agrupar as campanhas por plataforma e id (nome mais recente) e casar o lead e o retorno
  pelo id; sem id, pelo nome, como hoje.

### Entidades *(se houver dados)*

- **Contato de origem da conversa** (`conversa_anuncios`, da 334): ganha o `ctwa_clid` e a referência ao código do
  site; ganha o tipo "site".
- **Anúncio da Meta** (`anuncios_meta`): ganha o id e o nome do conjunto.
- **Código do site** (tabela nova): código, marcadores do clique, página de entrada, procedência, criação, conversa e
  momento em que foi usado, resposta de formulário que o levou.
- **Orçamento** (`orcamento_history`): ganha a conversa e o contato de origem.
- **Evento** (`calendar_events`): ganha a conversa, o contato de origem e a frente.
- **Ficha** (`clients`): ganha o id da campanha de origem.

Modelos em `app/models.py`; migration à mão.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

- `POST /api/origem/codigo` (novo) — público, sem login, com limite por endereço (como os formulários públicos).
- `POST /api/formularios/<tipo>` — público, como hoje; campo novo opcional `origem_codigo`.
- `POST /api/events` — `_can_create_event` (Comercial, Superadmin), como hoje; campos novos opcionais `conversa_id` e
  `frente`.
- `PATCH /api/events/<id>/comercial` — `_can_create_event`, como hoje, com a regra do cancelado; campo novo opcional
  `frente`.
- `GET /api/events/<id>` — a origem e a frente saem dentro do bloco comercial, que já é só de quem vê o comercial.

## Verificação (`verify_348.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/348-origem-completa/verify_348.py`, contra o espelho `manto_348` (dump noturno de 17/11; exceção ao
`manto_local` compartilhado registrada no `plan.md`), com `FLASK_ENV=development` e `MANTO_SEM_THREADS=1`. Login só por
`POST /api/auth/login`; escrita conferida por conexão separada; Meta e Google simulados; limpeza no `finally`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | aviso com `referral` e `ctwa_clid` | FR-001 | não |
| 2 | preenchimento retroativo da migration (com uma mensagem corrompida) | FR-002 | não |
| 3 | consulta à Meta com conjunto (Graph simulada) | FR-003 | não |
| 4 | `POST /api/origem/codigo` com `gclid` e utm; sem marcador → 400 | FR-005 | o sem marcador, **sim** |
| 5 | formulário público com `origem_codigo` → mensagem com a linha e resposta ligada | FR-006, FR-007 | não |
| 6 | mensagem recebida com o código → ligado, contato "site", ficha com origem "Site" | FR-009, FR-010 | não |
| 7 | código usado, vencido ou inexistente → nada ligado | FR-009 | **sim** (recusa) |
| 8 | envio de orçamento pela conversa → orçamento com conversa e contato | FR-011, FR-012 | não |
| 9 | cliente recorrente: dois anúncios (120 e 5 dias), duas vendas, contatos distintos; só contato velho → nenhum | FR-012, FR-015 | não |
| 10 | evento criado do orçamento e orçamento ligado/trocado/desligado → herança e retirada | FR-013 | não |
| 11 | `POST /api/events` com `conversa_id` (Google simulado); conversa inexistente → 400 | FR-014 | o inexistente, **sim** |
| 12 | frente: social escolhida, sem frente com venda → 400, frente inválida → 400, bundle antigo intacto | FR-019 a FR-022 | os 400, **sim** |
| 13 | função da frente: Python = SQL em eventos reais; satélite lê o principal | FR-018 | não |
| 14 | RBAC: Figurino no `PATCH …/comercial` → 403; detalhe sem bloco comercial não traz origem | RBAC | **sim** |
| 15 | Desempenho: campanha renomeada numa linha; lead casado pelo id | FR-023, FR-024 | não |
| 16 | limpeza | registros descartáveis apagados | — |

Conferência de tela: lista de desejos e formulário público em 390×844 (mensagem com o código); aba Comercial do evento
com o campo "Frente" e a origem, em desktop e 390 px.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: 100% das conversas que chegarem de anúncio de WhatsApp, depois de ligado o CRM, guardam o identificador
  do clique.
- **SC-002**: Toda visita com marcador de campanha que tocar no botão de WhatsApp leva o código na mensagem; toda
  mensagem recebida com código válido liga o clique à conversa.
- **SC-003**: Uma cliente que comprou duas vezes, por dois anúncios diferentes, aparece com cada venda no seu anúncio.
- **SC-004**: Nenhuma venda nova registrada pela aba Comercial fica com frente adivinhada pela regra por exclusão.
- **SC-005**: A campanha renomeada no meio do período aparece numa linha só, com os leads dela.
- **SC-006**: Os números por frente do painel da 345 continuam os mesmos para os eventos antigos.

## Fora de escopo

- Enviar conversões para a Meta (Conversions API) ou para o Google (Data Manager API): features 7 e 8 da pesquisa.
- Botão "Criar evento" na conversa, qualificada, perdida, primeira resposta: 349.
- Venda atribuída, funil por frente e por criativo, metas e verba: 351.
- Ligar uma venda já existente a uma conversa à mão (seletor de conversa no evento).
- Campo "Frente" no diálogo de criação do evento (a criação aceita o campo pela API; a tela escolhe na aba Comercial).
- Código no botão de WhatsApp da loja virtual e dos e-mails.
- Ligação de clique pelo Instagram Direct (o `wa.me` só abre o WhatsApp).
- Mudar o aviso de privacidade do site.

## Docs a atualizar

`docs/01` (schema das tabelas tocadas, endpoint novo, campos novos de `POST /api/events` e `PATCH …/comercial`, e o
**contrato para a 349 e a 351**: `conversa_id`, contato de origem, função da frente); `docs/02` (aba Comercial, lista de
desejos e formulários públicos); `docs/03` (entrada no topo); `docs/04` (invariante: a venda liga à conversa, nunca à
ficha; a frente é da venda); `docs/05` (quitar a dívida 215; registrar o que nascer).

## Premissas

- O CRM segue desligado em produção: nenhuma conversa nova chega até as chaves `WHATSAPP_*`; o código do site já é
  criado e guardado desde o deploy, e passa a ligar conversas quando o CRM ligar.
- Em produção, `conversas`, `conversa_anuncios` e `orcamento_envios` estão vazias (pesquisa, 17/11): o preenchimento
  retroativo é uma garantia, não uma carga.
- O id da campanha do Google chega pelo `gad_campaignid`, que o Google Ads acrescenta à URL final; links da Meta para o
  site podem usar `utm_id={{campaign.id}}` (convenção a combinar com quem cria os anúncios).
- O aviso de privacidade do site não cita os marcadores de campanha; a revisão do texto é do dono.
- A janela de 90 dias é a mesma para o código, para o contato de origem e para o Google.
