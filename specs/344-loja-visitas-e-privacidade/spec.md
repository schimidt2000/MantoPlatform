# Feature 344 — A loja conta as visitas e pede licença para mandar novidades

**Branch**: `344-loja-visitas-e-privacidade` (da `main`) · **Created**: 2026-11-16 · **Status**: pronto, aguardando deploy (`verify_344.py` 57/57) ·
**Migration**: uma, aditiva (tabela nova de visitas; colunas novas em pedido, cliente e configurações) ·
**Nível**: 1 (feature) — constituição, Princípio VI

**Input**: pedido do dono: "Consigo acompanhar quantas visitas tive? O que sugere de melhoria? Tem algum
LGPD nesse site? Pq seria interessante eu prospectar em cima desses clientes que fecharem para vender
outras coisas" → "Bora fazer os urgentes, trace o plano e execute".

## O pedido, nas palavras do dono *(obrigatório)*

Em 16/11/2026 o dono começou a divulgar a loja do Papai Noel e perguntou quantas visitas teve. A
resposta foi "não dá para saber": a loja não conta visita nenhuma, não tem o Pixel da Meta e o único
indício é o log do servidor. Na mesma conversa ele quis prospectar quem comprar para vender outros
serviços — e a loja não tem aviso de privacidade, não pergunta se a pessoa aceita receber novidades e
não leva o comprador para o cadastro de clientes. Ele escolheu os três itens urgentes: contar as
visitas por origem, pôr a loja em dia com a LGPD e deixar o Pixel da Meta pronto para ligar.

## Clarifications

### Session 2026-11-16

Fluxo autônomo (o dono pediu "trace o plano e execute"); decididas sem pergunta, com o porquê:

- Q: "Seu nome" é obrigatório? → A: na tela, sim; no servidor, não — um navegador com a página antiga em
  cache não pode ter a reserva recusada por um campo que ele nem mostra.
- Q: A ficha do cliente nasce na reserva ou na venda? → A: na venda — reserva abandonada não é cliente.
- Q: Retenção das dicas? → A: 30 dias da data de referência (chamada, prazo do vídeo ou criação).
- Q: Onde o dono informa o pixel? → A: nas Configurações, no card da loja (Superadmin), não por campanha.

## Cenários e Verificação *(obrigatório)*

### História 1 — Quantas pessoas abriram a página, e de onde vieram (Prioridade: P1)

O dono (ou o Comercial) abre a campanha no sistema e vê, por origem (Instagram, WhatsApp, Google…) e
por dia, quantas pessoas abriram a página, quantas reservaram e quantas pagaram. Na mesma tela pega o
link pronto de cada canal para colar no post, no story ou no grupo.

**Por que esta prioridade**: a divulgação começou hoje; sem o número, não dá para saber o que funciona
nem onde pôr a verba.

**Verificação**: cenários 1–6 do `verify_344.py`.

**Cenários de aceite**:

1. **Dado** a campanha publicada, **Quando** alguém abre a página pelo link `?origem=instagram`,
   **Então** a visita conta uma vez no dia, na origem Instagram — recarregar a página na mesma aba não
   conta de novo.
2. **Dado** um link sem origem vindo do Google, **Quando** a pessoa abre a página, **Então** a visita
   conta em Google; sem origem e sem procedência, conta em "Direto".
3. **Dado** que a pessoa veio do Instagram, **Quando** ela reserva e paga, **Então** a reserva e a
   venda aparecem na linha Instagram da tela da campanha.
4. **Dado** a tela da campanha, **Quando** o dono toca em "Copiar" ao lado de WhatsApp, **Então** o link
   da página com a origem WhatsApp vai para a área de transferência.

---

### História 2 — A loja explica o que faz com os dados e pede licença (Prioridade: P1)

A família lê, logo abaixo do botão, para que usamos os dados e abre o aviso de privacidade completo.
Pode marcar (ou não) "Quero receber novidades da Manto Produções por WhatsApp e e-mail". Quando a venda
se confirma, quem comprou entra no cadastro de clientes com o telefone, o e-mail, o nome, a origem e,
se marcou, o aceite com data — e a equipe sabe para quem pode mandar novidades. O que a família
escreveu sobre quem vai receber some 30 dias depois da chamada.

**Por que esta prioridade**: cada venda feita antes disso é um comprador sem aceite registrado, que
não pode ser prospectado com segurança.

**Verificação**: cenários 7–14 do `verify_344.py`.

**Cenários de aceite**:

1. **Dado** o formulário da loja, **Quando** a família reserva com a caixinha desmarcada, **Então** o
   pedido não registra aceite.
2. **Dado** a caixinha marcada, **Quando** a família reserva, **Então** o pedido guarda a data e a hora
   do aceite e a versão do texto que ela viu.
3. **Dado** um pedido com aceite, **Quando** a venda se confirma, **Então** existe no cadastro de
   clientes uma ficha com o telefone da família, origem "Loja", o aceite com data e a campanha, e o
   evento da chamada ligado a ela — sem o nome, a idade nem as dicas de quem vai receber.
4. **Dado** um telefone que já é cliente, **Quando** compra na loja, **Então** a ficha existente ganha o
   evento e o aceite, e o nome e o e-mail que já estavam ficam como estavam.
5. **Dado** uma chamada que aconteceu há mais de 30 dias, **Quando** a rotina periódica passa, **Então**
   as dicas sobre quem recebe somem do pedido, do evento no sistema e da descrição do evento na agenda.

---

### História 3 — Pixel da Meta pronto para ligar (Prioridade: P2)

O dono cria o Pixel no Gerenciador de Negócios e cola o número nas configurações. A partir daí, quem
abre a loja vê um aviso de cookies; se aceitar, a Meta recebe a visita, o início da compra e a compra
— é o que permite à Meta mostrar o anúncio para quem tende a comprar. Sem o número, nada muda.

**Por que esta prioridade**: só vale com anúncio pago e depende do dono criar o Pixel; a contagem
própria (História 1) já responde "quantas visitas".

**Verificação**: cenários 15–17 do `verify_344.py` + tela aberta no celular.

**Cenários de aceite**:

1. **Dado** o campo vazio, **Quando** alguém abre a loja, **Então** não aparece aviso de cookies e
   nenhum script da Meta é carregado.
2. **Dado** o campo preenchido, **Quando** alguém abre a loja e recusa os cookies, **Então** nenhum
   script da Meta é carregado e o aviso não volta na próxima visita.
3. **Dado** o aceite dos cookies, **Quando** a pessoa reserva e depois paga, **Então** a Meta recebe a
   visita, o início da compra e uma única compra com o valor — sem nome, e-mail nem telefone.

### Casos de borda

- Campanha pausada ou em rascunho: a visita não conta.
- Origem com valor desconhecido no link (`?origem=panfleto`): conta como "Outro"; nunca cria origem nova.
- Contagem fora do ar (erro na chamada): a página abre normalmente, só a visita se perde.
- Robô ou abuso enviando visitas em massa: limite por IP; o IP não é guardado.
- Pedido sem "Seu nome" (navegador com a página antiga em cache): a reserva passa; a ficha do cliente
  usa a parte do e-mail antes do `@` como nome.
- Telefone que não normaliza para o formato do cadastro: a venda segue, sem ficha de cliente (fica no
  log).
- Falha ao criar a ficha do cliente: a venda **não** é desfeita.
- Agenda fora do ar na limpeza das dicas: o pedido fica para a próxima volta; nada é apagado pela metade.
- Mesmo pedido pago mostrado duas vezes no navegador: a compra vai uma vez só para a Meta.

## Requisitos *(obrigatório)*

### Requisitos funcionais

**Contagem (História 1)**

- **FR-001**: A página pública de uma campanha publicada DEVE contar uma visita por abertura e por aba,
  por campanha, dia (São Paulo) e origem — recarregar na mesma aba não conta de novo.
- **FR-002**: A origem DEVE vir do parâmetro `origem` (ou `utm_source`) do link, reduzida a uma lista
  fechada — Instagram, Facebook, WhatsApp, Google, TikTok, E-mail, Outro; sem parâmetro, da procedência
  (Instagram, Facebook, Google, TikTok); sem nada, "Direto".
- **FR-003**: A contagem NÃO DEVE usar cookie nem guardar IP, aparelho ou qualquer dado de quem visita;
  só o total por dia e origem.
- **FR-004**: O pedido DEVE guardar a origem da visita que o gerou.
- **FR-005**: A tela da campanha no sistema DEVE mostrar, por origem e por dia (últimos 14), visitas,
  reservas, vendas e a taxa de conversão (vendas ÷ visitas), com os totais.
- **FR-006**: A mesma tela DEVE listar o link da página para cada origem, com um botão de copiar.
- **FR-007**: Falha na contagem NUNCA DEVE impedir a página de abrir nem a reserva.

**LGPD (História 2)**

- **FR-010**: A loja DEVE ter um aviso de privacidade público: quem é o controlador, o que coletamos, para
  quê, com quem compartilhamos (InfinitePay para o pagamento; Google para a agenda e a sala), por quanto
  tempo, os direitos da pessoa, e o canal para exercê-los (o WhatsApp da campanha).
- **FR-011**: O formulário DEVE ter, abaixo do botão de reservar, uma linha que diz para que usamos os
  dados, com link para o aviso.
- **FR-012**: O formulário DEVE ter a caixinha opcional e desmarcada "Quero receber novidades da Manto
  Produções por WhatsApp e e-mail". Marcada, o pedido guarda data/hora e a versão do texto; desmarcada,
  nada.
- **FR-013**: O formulário DEVE pedir "Seu nome" (de quem compra). O servidor aceita pedido sem ele.
- **FR-014**: Quando a venda se efetiva, o comprador DEVE entrar no cadastro de clientes pelo telefone:
  ficha nova com origem "Loja", nome, telefone, e-mail, origem do acesso e campanha; ficha existente só
  preenche o que está vazio. O evento da venda fica ligado à ficha.
- **FR-015**: Com aceite no pedido, a ficha DEVE registrar a data do aceite e de onde veio ("Loja: <título
  da campanha>").
- **FR-016**: Nome, idade e dicas de quem vai receber NUNCA DEVEM ir para o cadastro de clientes.
- **FR-017**: Falha ao criar ou atualizar a ficha NUNCA DEVE desfazer nem atrasar a venda.
- **FR-018**: As dicas sobre quem vai receber DEVEM ser apagadas 30 dias depois da data de referência —
  a chamada (ao vivo), o prazo do vídeo (gravado), ou a criação do pedido que não virou venda — no
  pedido, no evento do sistema e na descrição do evento na agenda do Google.
- **FR-019**: O cadastro de clientes DEVE contar a origem "Loja" à parte no gráfico de clientes novos e
  mostrar, na ficha, se a pessoa aceitou novidades, quando e por onde.

**Pixel (História 3)**

- **FR-020**: O Superadmin DEVE poder informar o ID do Pixel da Meta nas configurações (só dígitos;
  vazio desliga).
- **FR-021**: Com o ID vazio, nenhuma página da loja muda.
- **FR-022**: Com o ID preenchido, as páginas da loja (vitrine, campanha, pedido, aviso de privacidade)
  DEVEM mostrar um aviso de cookies com "Aceitar" e "Recusar"; a escolha fica no navegador e o aviso não
  volta.
- **FR-023**: Só com o aceite o pixel é carregado: visita a cada página da loja, início da compra quando a
  reserva é criada e compra (valor e moeda) uma única vez por pedido, quando a página do pedido o mostra
  pago.
- **FR-024**: Nenhum dado pessoal (nome, e-mail, telefone) vai para a Meta.
- **FR-025**: O aviso de privacidade DEVE explicar os cookies da Meta quando o pixel estiver ligado.

### Entidades *(se houver dados)*

- **Visita da campanha** (nova): campanha, dia, origem, quantidade. Única por campanha + dia + origem.
- **Pedido da loja** (`VirtualOrder`): + origem da visita, nome de quem compra, data/hora do aceite de
  novidades, versão do texto do aceite.
- **Cliente** (`Client`): + data do aceite de novidades, de onde veio o aceite; origem nova "loja_virtual".
- **Configurações** (`SiteSetting`): + ID do Pixel da Meta.

Modelos em `app/models.py`, migration escrita à mão sobre o head `f310b2a4c6e8`.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

- `POST /api/virtuais/campanhas/<slug>/visita` — público, com limite por IP; só campanha publicada.
- `GET /api/virtuais/campanhas/<id>/funil` — Comercial e Superadmin (`require_virtuais_access`).
- `GET /api/virtuais/rastreamento` — público (devolve só o ID do pixel, que já é público no HTML de quem usa).
- `POST /api/virtuais/campanhas/<slug>/reservar` — inalterado no acesso; aceita `buyer_name`,
  `marketing_opt_in`, `origem`.
- `PATCH /api/admin/config` (existente) — Superadmin; campo novo `meta_pixel_id`.
- `GET /api/clientes/<id>` (existente) — inalterado no acesso; serializa o aceite.

## Verificação (`verify_344.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/344-loja-visitas-e-privacidade/verify_344.py`, contra um espelho próprio `manto_344`
(dump de produção de 16/11/2026; o `manto_local` está no CRM). Login só por `POST /api/auth/login`;
escrita conferida por conexão separada; InfinitePay e Google por dublê; limpeza no fim.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | visita com `origem=instagram` | conta 1 em Instagram no dia | não |
| 2 | `utm_source=WhatsApp` e `origem=panfleto` | WhatsApp e Outro; nenhuma origem nova | não |
| 3 | sem origem, procedência do Google; sem nada | Google e Direto | não |
| 4 | campanha pausada | não conta (404) | não |
| 5 | reserva com origem + venda | funil: visita, reserva e venda na mesma origem | não |
| 6 | funil sem papel de loja | 403 | **sim** |
| 7 | reserva sem aceite | pedido sem data de aceite | não |
| 8 | reserva com aceite e nome | pedido com data, versão e nome | não |
| 9 | venda com aceite, telefone novo | ficha nova: origem Loja, aceite, evento ligado, nada de quem recebe | não |
| 10 | venda de telefone já cliente | ficha existente mantém nome/e-mail, ganha evento e aceite | não |
| 11 | falha forçada na ficha | a venda continua efetivada | não |
| 12 | dicas com chamada há 31 dias | apagadas no pedido, no evento e na agenda (dublê chamado sem as dicas) | não |
| 13 | dicas com chamada há 29 dias / Google fora | ficam | não |
| 14 | gráfico de clientes | origem Loja conta à parte | não |
| 15 | rastreamento com ID vazio | devolve vazio | não |
| 16 | Superadmin grava ID; não-dígito | grava; 400 | não |
| 17 | papel sem acesso grava ID | 403 | **sim** |
| 18 | limpeza | registros do verify apagados; nenhuma conexão externa | — |

Conferência de tela: campanha (contagem + links) e configurações no sistema interno; loja (campanha,
pedido, aviso de privacidade, aviso de cookies com e sem ID) em 375×812.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: No dia seguinte à publicação, o dono responde "quantas visitas e de onde" abrindo uma tela,
  sem pedir a ninguém.
- **SC-002**: 100% das vendas a partir da publicação viram ficha no cadastro de clientes, e a equipe sabe
  quais aceitaram novidades.
- **SC-003**: Nenhuma dica sobre quem recebe sobrevive mais de 31 dias depois da data de referência.
- **SC-004**: Com o ID do pixel informado, o Gerenciador de Eventos da Meta mostra visitas e compras da
  loja em até 1 dia; sem ID, nada da Meta é carregado.
- **SC-005**: A página continua abrindo no mesmo tempo de hoje (a contagem não atrasa a primeira tela).

## Fora de escopo

- Trocar horário de pedido pago, combo, link curto.
- Descadastro automático por mensagem (opt-out pelo WhatsApp) — vai para o CRM próprio; aqui o direito é
  exercido pelo WhatsApp da campanha.
- API de Conversões da Meta (servidor → Meta), tag do Google Ads/Analytics.
- Aceite retroativo de quem comprou antes da 344.

## Docs a atualizar

`docs/01` (tabelas/colunas novas, endpoints, RBAC §4.3), `docs/02` (loja: formulário, aviso de
privacidade, aviso de cookies; campanha: card de visitas; configurações; ficha do cliente), `docs/03`
(entrada no topo), `docs/04` (invariantes: contagem anônima, cliente nasce da venda, retenção das
dicas), `docs/05` (dívidas criadas).

## Premissas

- 30 dias de retenção das dicas, contados da data de referência — tempo para remarcar ou reclamar.
- "Visita" = abertura da página numa aba (não pessoa única): sem cookie, não dá para saber se é a mesma
  pessoa em dois aparelhos.
- O canal para exercer direitos é o WhatsApp da campanha; CNPJ e e-mail do encarregado entram quando o
  dono informar (o texto deve passar por um advogado).
- Base legal: execução do contrato para a venda; consentimento para novidades.
