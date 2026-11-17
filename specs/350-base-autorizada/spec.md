# Feature 350 — A base autorizada: a cliente diz sim (ou para), indica e lembra do aniversário

**Branch**: `350-base-autorizada` (da `main`) · **Created**: 2026-11-17 · **Status**: Rascunho ·
**Migration**: uma, aditiva (`a350…`, encadeada em `d334b2c4e6f8`; tabelas novas de consentimento,
crianças, parceiros e pós-evento; colunas novas em `clients`) · **Nível**: 1 (feature) — constituição,
Princípio VI

**Input**: pedido da sessão principal (17/11/2026), a partir da pesquisa "Máquina de vendas Manto:
medir primeiro, escalar depois" (seções 3.6, 4.1, 5.5–5.7, 8.2, 8.4 e itens 4 e 14 do roteiro): "Faça a
feature 350 · base autorizada: dois consentimentos (LGPD) com data, texto aceito e origem; onde pedir
(orçamento e pós-evento); indicado por, parceiro e aniversário com consentimento; pós-evento único no
dia seguinte; lista de aniversários dos próximos 60 dias com aceite. O disparo automático fica fora."

## O pedido, nas palavras do dono *(obrigatório)*

A Manto quer vender mais para quem já foi cliente — a pesquisa estima R$ 0,32 por mensagem para a base,
contra R$ 7 por conversa nova — e o aniversário volta todo ano, com data. Hoje isso é impossível de
fazer direito: das 6.291 fichas, **nenhuma** tem aceite para receber novidades; o único aceite que o
sistema grava vem da loja (feature 344); retirar o aceite é manual; o erro do WhatsApp "o contato pediu
para não receber mensagens de marketing" (131050) aparece na conversa e não marca a ficha; não existe
"indicado por", nem parceiro (buffet, assessoria, agência), nem a data de aniversário da criança; e o
pedido de avaliação é um link copiado à mão, sem foto, sem indicação e sem pedir licença. Só 13% dos
eventos recebem avaliação.

A regra que vale para tudo, da pesquisa (seção 5.7): **dois consentimentos separados**, cada um com
data, texto e origem — receber novidades, e guardar o primeiro nome e o aniversário da criança.
Nenhum pré-marcado, nenhum como condição para fechar a festa. **Sem aceite, nada de prospecção.**

Decisão do dono (17/11, mantida): o botão "Avaliar no Google" continua **só para nota 5**. Esta feature
não muda esse filtro, e se o link sair pela conversa, o Google também só vai para nota 5.

## Clarifications

### Session 2026-11-17

Fluxo autônomo (a sessão principal pediu "sem parar para confirmação"); decididas sem pergunta, com o
porquê:

- Q: O pós-evento do dia seguinte sai sozinho? → A: Não. A lista "Pós-evento" põe ontem no topo e a
  vendedora copia ou envia; nada dispara sozinho (FR-020). Porquê: o CRM está desligado em produção, o
  envio automático fora da janela de 24 h exige modelo aprovado na Meta, e "nada muda no WhatsApp de
  produção" nesta rodada.
- Q: "SAIR" também apaga os aniversários? → A: Não; os dois aceites são independentes (pedido explícito).
  A lista de aniversários exige **os dois** aceites, então quem saiu some dela na hora; o nome e a data
  ficam até alguém remover. Porquê: "parar mensagens" não é "apague meus dados"; a decisão de apagar junto
  vai ao parecer jurídico.
- Q: Quem vê e mexe no dado da criança? → A: Só Comercial e Superadmin. O Financeiro vê a ficha sem as
  crianças (chave ausente). Porquê: minimização (LGPD art. 14) — o Financeiro não precisa do aniversário.
- Q: O pós-evento conta como prospecção (exige aceite)? → A: Não: é relacionamento com quem acabou de
  ser cliente, sai para todas e sempre termina com "responda SAIR". Pela conversa, só como texto livre na
  janela aberta (nunca como modelo de marketing). Porquê: é o momento de pedir o aceite; exigir aceite
  antes tornaria o pedido impossível. Vai ao parecer jurídico.
- Q: Que origens a equipe escolhe ao registrar um aceite? → A: Lista fechada: "Conversa", "Resposta ao
  orçamento", "Telefone", "Pessoalmente". O sistema grava sozinho "Pós-evento (página de avaliação)",
  "Conversa: pediu para parar", "WhatsApp: pediu para não receber marketing" e "Loja: <campanha>" (344).
  Porquê: origem livre vira texto inútil para provar o aceite.

## Cenários e Verificação *(obrigatório)*

### História 1 — A equipe registra e retira os dois aceites, na ficha e na conversa (Prioridade: P1)

A vendedora abre a ficha da cliente e vê o cartão "Consentimentos": se ela aceita receber novidades
(desde quando, por onde e qual texto aceitou) e as crianças cujo aniversário a responsável autorizou
guardar. Quando a cliente diz que quer receber novidades (respondeu ao orçamento, pediu na conversa,
falou por telefone), a vendedora toca em "Registrar aceite", escolhe por onde veio e confirma vendo o
texto exato que está registrando. Quando a cliente pede para sair, "Retirar aceite". Para o aniversário,
"Inserir aniversário" pede o primeiro nome, a data e a confirmação de que a responsável autorizou com o
texto mostrado; "Remover" apaga o nome e a data. Na conversa ligada a uma ficha, o mesmo aceite de
novidades aparece no cabeçalho, com o mesmo botão.

**Por que esta prioridade**: sem o registro, a base inteira continua proibida de receber mensagem —
e é por ele que todas as outras histórias passam.

**Verificação**: cenários 2–6 do `verify_350.py`.

**Cenários de aceite**:

1. **Dado** uma ficha sem aceite, **Quando** a vendedora registra o aceite de novidades com a origem
   "Resposta ao orçamento", **Então** a ficha passa a "Recebe novidades desde dd/mm", o histórico ganha
   uma linha com data, texto completo, versão do texto, origem e quem registrou.
2. **Dado** uma ficha com aceite, **Quando** a vendedora retira o aceite, **Então** a ficha volta a "Sem
   aceite", e o histórico guarda a retirada com data e origem; o aceite antigo continua no histórico.
3. **Dado** uma ficha, **Quando** a vendedora insere o aniversário de "Lia" (12/03/2021) confirmando a
   autorização, **Então** Lia aparece na ficha com a data e o aceite próprio (data, versão, origem);
   **sem** a confirmação, nada é gravado e o campo é apontado.
4. **Dado** Lia na ficha, **Quando** a vendedora remove o aniversário, **Então** o nome e a data são
   apagados, e o histórico guarda só a retirada (sem o nome nem a data da criança).
5. **Dado** a conversa ligada à ficha, **Quando** a vendedora registra o aceite no cabeçalho, **Então** a
   origem gravada é "Conversa" com a referência da conversa.

---

### História 2 — Quem pede para parar sai sozinho, e modelo de marketing não sai sem aceite (Prioridade: P1)

A cliente responde "SAIR" (ou "PARAR", "STOP", "Parar promoções"…) — a mensagem inteira é o pedido — e o
aceite de novidades da ficha é retirado na hora, com a origem "Conversa: pediu para parar". O mesmo
acontece quando o WhatsApp devolve o erro 131050 ("o contato pediu para não receber mensagens de
marketing"). E a equipe não consegue mandar um modelo de **marketing** para quem não tem aceite: o
sistema recusa e explica o que fazer. "Vou sair às 15h" não é pedido de saída.

**Por que esta prioridade**: a política do WhatsApp exige respeitar o pedido de parar; bloqueio derruba a
qualidade do número que o CRM acabou de ganhar. E a LGPD pede revogação "gratuita e facilitada".

**Verificação**: cenários 7–9 do `verify_350.py` (o 7 e o 8 são os de **saída do opt-in**).

**Cenários de aceite**:

1. **Dado** uma ficha com aceite ligada à conversa, **Quando** chega "SAIR", **Então** o aceite é
   retirado com a origem "Conversa: pediu para parar" e a referência da mensagem.
2. **Dado** a mesma ficha com aceite, **Quando** chega "vou sair às 15h", **Então** nada muda.
3. **Dado** uma mensagem de marketing enviada a uma ficha com aceite, **Quando** o WhatsApp devolve o erro
   131050, **Então** o aceite é retirado com a origem "WhatsApp: pediu para não receber marketing".
4. **Dado** uma ficha sem aceite, **Quando** a vendedora tenta enviar um modelo de categoria Marketing,
   **Então** o envio é recusado (409) com "Esta cliente não autorizou receber novidades. Registre o aceite
   na ficha antes de enviar um modelo de marketing."; modelo de Utilidade continua saindo.

---

### História 3 — Pós-evento único, no dia seguinte (Prioridade: P1)

No dia seguinte à festa, a vendedora abre a lista "Pós-evento" (eventos dos últimos 7 dias, do mais
recente) e, para cada um, prepara **uma** mensagem: agradecimento, o link das fotos (se ela colar um),
o pedido de avaliação, o pedido de indicação e o convite para receber novidades e o lembrete de
aniversário — com "responda SAIR" no fim. Com o CRM ligado e a conversa da contratante aberta, "Enviar
pela conversa"; enquanto o CRM estiver desligado (ou a janela de 24 h fechada), "Copiar mensagem". A
lista marca o que já foi enviado ou copiado, e se a avaliação já chegou.

Do lado da cliente, o link é a página de avaliação que já existe. Depois de enviar a nota, a página
mostra (além do Google, só para nota 5, como hoje) duas caixas **desmarcadas e separadas** — receber
novidades; guardar o primeiro nome e o aniversário da criança — e um botão "Indicar uma amiga" que abre o
WhatsApp com uma mensagem pronta que cita quem indicou.

**Por que esta prioridade**: é o momento em que a cliente está mais feliz; hoje sai só um link de
avaliação, e só 13% respondem. É também o ponto que mais colhe aceite.

**Verificação**: cenários 10–13 do `verify_350.py`.

**Cenários de aceite**:

1. **Dado** um evento de ontem, não cancelado, com contratante, **Quando** a vendedora abre o
   pós-evento, **Então** vê a mensagem com o nome da contratante, o link de avaliação e "SAIR"; com o
   link das fotos informado, a mensagem traz as fotos.
2. **Dado** a mensagem pronta, **Quando** ela copia, **Então** o evento fica "Copiado em dd/mm" na lista;
   copiar de novo não cria registro novo.
3. **Dado** o CRM desligado, **Quando** ela tenta enviar pela conversa, **Então** recebe a recusa com
   "copie a mensagem" e nada é gravado como enviado.
4. **Dado** a página pública de avaliação de um evento com contratante, **Quando** a cliente marca
   "receber novidades" e salva, **Então** a ficha da contratante ganha o aceite com a origem
   "Pós-evento (página de avaliação)" e o texto exibido; **Quando** ela insere o aniversário sem marcar a
   caixa da criança, **Então** nada é gravado e a caixa é apontada.
5. **Dado** a página pública de quem já recebe novidades, **Quando** ela toca "Não quero mais receber",
   **Então** o aceite é retirado com a origem "Pós-evento (página de avaliação)".
6. **Dado** evento cancelado, **Quando** se abre o pós-evento, **Então** 409 `cancelado`.

---

### História 4 — Indicado por e parceiro (Prioridade: P2)

Na ficha, a vendedora informa "Indicado por" (outra cliente, por busca) e "Veio pelo parceiro" (um
buffet, uma assessoria ou uma agência). A ficha de quem indicou mostra "Indicou" com a lista. Em
Clientes › Parceiros, a equipe cadastra o parceiro com tipo, contato e a **comissão declarada** (%), e
vê quantas clientes cada um trouxe.

**Por que esta prioridade**: indicação e parceiro são o primeiro canal da pesquisa para festas; sem o
campo, não se sabe quanto vem deles.

**Verificação**: cenários 14–15 do `verify_350.py`.

**Cenários de aceite**:

1. **Dado** duas fichas, **Quando** a vendedora informa que B foi indicada por A, **Então** B mostra
   "Indicado por A" e A mostra "Indicou: B"; indicar a própria ficha é recusado no campo.
2. **Dado** o parceiro "Buffet Alegria" (buffet, 10%), **Quando** a ficha é ligada a ele, **Então** a ficha
   mostra o parceiro e a lista de parceiros conta 1 cliente.
3. **Dado** um parceiro desativado, **Quando** se busca parceiro para uma ficha, **Então** ele não aparece;
   as fichas já ligadas continuam mostrando o nome.

---

### História 5 — Aniversários dos próximos 60 dias, com aceite (Prioridade: P2)

Em Clientes › Aniversários, a equipe vê, só para leitura, as crianças com aniversário nos próximos 60
dias cuja responsável autorizou guardar o aniversário **e** recebe novidades: data, primeiro nome, idade
que vai fazer, responsável (com link para a ficha) e em quantos dias. O envio automático do lembrete
fica fora desta feature.

**Por que esta prioridade**: é o gatilho de recompra de jan–jul (meses com mais nascimentos), mas só
rende depois que a base tiver aceites — por isso depois das histórias 1–3.

**Verificação**: cenário 16 do `verify_350.py`.

**Cenários de aceite**:

1. **Dado** Lia (aniversário em 10 dias, responsável com aceite), Theo (em 90 dias) e Bia (em 5 dias,
   responsável sem aceite de novidades), **Quando** a equipe abre a lista, **Então** só Lia aparece.
2. **Dado** uma criança nascida em 29/02, **Quando** o ano não é bissexto, **Então** o aniversário conta
   em 28/02.

---

### História 6 — O orçamento pede o aceite (Prioridade: P3)

A mensagem de WhatsApp do orçamento ganha, no fim, uma linha que convida a receber novidades ("responda
QUERO"). Quando a cliente responde, a vendedora registra o aceite com a origem "Resposta ao orçamento"
(História 1). O PDF não muda.

**Por que esta prioridade**: todo orçamento vira oportunidade de aceite, mas o registro depende da
História 1.

**Verificação**: cenário 17 do `verify_350.py`.

**Cenários de aceite**:

1. **Dado** um orçamento calculado, **Quando** a mensagem de WhatsApp é montada, **Então** ela termina com
   o convite e o "QUERO", e a frase de deslocamento continua intacta.

---

### Casos de borda

- **Conversa sem ficha** que pede "SAIR": não há aceite a retirar; nada é gravado (a mensagem continua na
  conversa). Se depois a conversa for ligada a uma ficha com aceite, a equipe vê a mensagem e retira.
- **Aceite da loja (344) depois de uma retirada**: a venda da loja só reaplica o aceite se o aceite do
  pedido for **posterior** à última retirada da ficha.
- **Registrar aceite em quem já tem**: o servidor responde 200 sem duplicar o histórico (idempotente).
- **Retirar de quem não tem**: 200, nada muda.
- **Evento sem contratante**: o pós-evento sai sem nome ("Oi! …") e a página pública não mostra as caixas
  (não há ficha onde gravar).
- **Evento agrupado (vários dias)** e **ensaio**: só o principal aparece na lista do pós-evento; o ensaio
  não aparece.
- **Data de nascimento no futuro ou criança com mais de 17 anos**: recusada no campo.
- **29/02**: em ano não bissexto, o aniversário cai em 28/02.
- **Ficha excluída**: o histórico de consentimentos e as crianças vão junto (LGPD: eliminação).
- **Parceiro com comissão fora de 0–100**: recusado no campo.

## Requisitos *(obrigatório)*

### Requisitos funcionais

**Consentimentos**

- **FR-001**: Cada ficha DEVE ter, separados, o aceite de **novidades** (WhatsApp e e-mail) e, por
  criança, o aceite de **aniversário** (primeiro nome e data). Nenhum é pré-marcado nem condição para
  fechar.
- **FR-002**: Todo aceite e toda retirada DEVEM ficar num histórico com: data, tipo, ação, **texto
  completo exibido**, versão do texto, origem, referência (conversa, mensagem, evento) e quem registrou
  (nulo quando foi a própria cliente ou o sistema). O histórico nunca é editado.
- **FR-003**: Os textos dos dois aceites DEVEM ter versão; mudar o texto exige versão nova (molde da 344).
- **FR-004**: A equipe (Comercial e Superadmin) DEVE poder registrar e retirar o aceite de novidades na
  ficha e no cabeçalho da conversa ligada, escolhendo a origem na lista fechada ("Conversa", "Resposta ao
  orçamento", "Telefone", "Pessoalmente"); e inserir e remover o aniversário de uma criança na ficha,
  confirmando a autorização com o texto exibido. O Financeiro não vê nem mexe nas crianças.
- **FR-005**: Remover o aniversário DEVE apagar o nome e a data da criança; o histórico guarda só a
  retirada.
- **FR-006**: A mensagem recebida cujo texto inteiro, normalizado (sem acento, sem pontuação nas pontas,
  sem diferença de maiúscula), for uma das palavras de saída (SAIR, PARAR, PARE, STOP, CANCELAR
  INSCRIÇÃO, DESCADASTRAR, NÃO QUERO MAIS RECEBER, PARAR PROMOÇÕES) DEVE retirar o aceite de novidades da
  ficha ligada à conversa (WhatsApp e Instagram).
- **FR-007**: O erro 131050 do WhatsApp — no aviso de status ou na recusa síncrona do envio — DEVE retirar
  o aceite de novidades da ficha ligada.
- **FR-008**: O envio de modelo de categoria **Marketing** pela conversa DEVE ser recusado (409
  `sem_aceite`) quando a ficha ligada não tem aceite de novidades ou a conversa não tem ficha.
- **FR-009**: A venda da loja (344) DEVE gravar o aceite no histórico com o texto e a versão da loja, e não
  DEVE reaplicar aceite anterior à última retirada.
- **FR-010**: O detalhe da ficha DEVE dizer se a cliente pode receber prospecção (`pode_prospectar`).

**Onde pedir**

- **FR-011**: A mensagem de WhatsApp do orçamento DEVE terminar com o convite para receber novidades
  ("responda QUERO"), sem alterar a frase de deslocamento.
- **FR-012**: A página pública de avaliação DEVE, depois do envio da nota e quando o evento tem
  contratante, oferecer as duas caixas separadas, os campos da criança e a retirada para quem já recebe;
  o botão do Google continua só para nota 5.

**Cliente, indicação e parceiro**

- **FR-013**: A ficha DEVE ter "Indicado por" (outra ficha, nunca ela mesma) e "Parceiro"; a ficha de quem
  indicou DEVE listar as indicadas.
- **FR-014**: O parceiro DEVE ser cadastrado com nome, tipo (buffet, assessoria, agência ou outro),
  contato, telefone, e-mail, comissão declarada (0–100%), observação e situação (ativo/inativo); a lista
  mostra quantas fichas cada um trouxe.

**Pós-evento**

- **FR-015**: Para cada evento já acontecido, não cancelado, a equipe DEVE poder abrir o pós-evento com a
  mensagem única (agradecimento, fotos se houver link, avaliação, indicação, convite ao aceite e "SAIR").
- **FR-016**: O pós-evento DEVE ser copiado (sempre) ou enviado pela conversa (só com o CRM ligado, a
  conversa da contratante e a janela aberta, como texto livre — nunca como modelo de marketing); o sistema
  registra canal, data e quem fez, um registro por evento. O pós-evento não exige aceite de novidades
  (relacionamento com cliente atual) e sempre termina com "responda SAIR".
- **FR-017**: A lista "Pós-evento" DEVE mostrar os eventos dos últimos 7 dias até hoje, sem ensaios e sem
  os dias satélites de um grupo, com a situação (pendente, copiado, enviado) e se a avaliação chegou.
- **FR-018**: A página pública DEVE ter "Indicar uma amiga", que abre o WhatsApp com a mensagem pronta
  citando o primeiro nome de quem indica e o WhatsApp da Manto. Nenhum dado da amiga é colhido.

**Aniversários**

- **FR-019**: A lista "Aniversários" DEVE mostrar as crianças com aniversário de hoje até 60 dias, com
  aceite de aniversário e responsável com aceite de novidades, em ordem de data, só para leitura.
- **FR-020**: Nada desta feature envia mensagem sozinho.

### Entidades

- **Consentimento (histórico)**: uma linha por aceite ou retirada — ficha, tipo (novidades | aniversario),
  ação (aceite | retirada), texto, versão, origem, referência, quem registrou, quando.
- **Criança da ficha**: primeiro nome, data de nascimento, aceite (quando, versão, origem, quem
  registrou). Existe só enquanto houver o aceite.
- **Parceiro**: nome, tipo, contato, telefone, e-mail, comissão declarada, observação, ativo.
- **Pós-evento**: um por evento — ficha, link das fotos, canal (copiado | conversa), quando, quem,
  mensagem enviada.
- **Ficha (Client)**: ganha versão do aceite, última retirada (quando e origem), indicado por, parceiro.

### RBAC

- `GET /api/clientes/<id>` (detalhe) — papéis de hoje (Comercial, Financeiro, Superadmin); crianças só
  para Comercial e Superadmin (chave ausente para o Financeiro).
- `POST|DELETE /api/clientes/<id>/consentimentos/novidades`, `POST /api/clientes/<id>/criancas`,
  `DELETE /api/clientes/<id>/criancas/<cid>`, `PATCH /api/clientes/<id>/indicacao` — Comercial e
  Superadmin.
- `GET /api/clientes/aniversarios` — Comercial e Superadmin.
- `GET /api/parceiros` — Comercial, Financeiro e Superadmin; `POST|PATCH /api/parceiros…` — Comercial e
  Superadmin.
- `GET /api/pos-evento`, `GET|POST /api/events/<id>/pos-evento` — Comercial e Superadmin (o gate de
  "Pedir feedback" de hoje).
- `GET /api/avaliar/<token>` e `POST /api/avaliar/<token>/consentimento` — públicos, pelo token do evento,
  com limite por hora.
- `POST /api/conversas/<id>/modelo` — gate de hoje + recusa `sem_aceite` para modelo de marketing.

## Verificação (`verify_350.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/350-base-autorizada/verify_350.py`, contra o espelho próprio `manto_350` (dump noturno de
17/11; `.local-db-url` da worktree), `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`. A Meta nunca é
chamada (dublê em memória + disjuntor de rede, molde do `verify_325`). Login só por `POST
/api/auth/login`; escrita conferida por conexão separada; limpeza no `finally`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | esquema | tabelas e colunas novas existem; head = `a350…` | não |
| 2 | aceite de novidades pela ficha | colunas da ficha + histórico com texto, versão, origem, autor | não |
| 3 | retirada pela ficha | aceite zerado, retirada gravada, histórico preservado; repetir é idempotente | não |
| 4 | **RBAC** | Casting registra aceite → 403; Financeiro lista aniversários → 403; detalhe do Financeiro sem `criancas` | **sim** |
| 5 | criança | sem confirmação → 400 no campo; data futura → 400; com confirmação → linha; remover apaga e loga | parcial |
| 6 | aceite pela conversa | origem "Conversa" e referência da conversa | não |
| 7 | **saída: "SAIR" recebido** | aviso do WhatsApp retira o aceite; "vou sair às 15h" não retira | não |
| 8 | **saída: erro 131050** | status com 131050 retira o aceite; recusa síncrona com 131050 também | não |
| 9 | modelo de marketing sem aceite | 409 `sem_aceite`, Meta não chamada; utilidade sai | **sim** (marketing) |
| 10 | pós-evento: mensagem | nome, link de avaliação, fotos, "SAIR"; cancelado → 409 | parcial |
| 11 | pós-evento: copiar e lista | registro único por evento; lista mostra "copiado" e avaliação | não |
| 12 | pós-evento: conversa | CRM desligado → 503; ligado e janela aberta → enviado pelo dublê, registro "conversa" | parcial |
| 13 | página pública | GET traz o bloco; POST aceita novidades e criança; sem caixa → 400; retirar | parcial |
| 14 | indicação | indicado por, lista de indicadas, auto-indicação recusada | parcial |
| 15 | parceiros | criar, editar, desativar, contagem; comissão 120 → 400; Financeiro cria → 403 | parcial |
| 16 | aniversários | janela de 60 dias, filtro de dois aceites, 29/02 | não |
| 17 | orçamento | mensagem termina com o convite; deslocamento intacto | não |
| 18 | loja (344) | aceite do pedido vai ao histórico; aceite anterior à retirada não volta | não |
| 19 | limpeza | fichas, eventos, conversas e usuários `v350-` apagados (`roles.clear()` antes) | — |

Conferência de tela: ficha do cliente (cartão Consentimentos, Indicação), cabeçalho da conversa,
Clientes › Pós-evento / Aniversários / Parceiros, diálogo do pós-evento no evento — internas em 390 px;
página pública de avaliação em viewport mobile (375×812).

## Critérios de sucesso *(obrigatório)*

- **SC-001**: A vendedora registra ou retira um aceite em até 3 toques, da ficha ou da conversa.
- **SC-002**: 100% dos pedidos de saída por palavra e dos erros 131050 retiram o aceite sem ação humana.
- **SC-003**: Nenhum modelo de marketing sai para ficha sem aceite.
- **SC-004**: O pós-evento de um evento sai (copiado ou enviado) em menos de 1 minuto, a partir da lista.
- **SC-005**: Todo aceite registrado pode ser provado: texto completo, versão, data, origem e autor.
- **SC-006**: Meta operacional (pesquisa, item 4 do roteiro, para o dono acompanhar): 40% dos eventos com
  avaliação e 50% com aceite em 30 dias de uso.

## Fora de escopo

- Disparo automático de lembrete de aniversário e de pós-evento (nenhuma mensagem sai sozinha).
- Pagamento de comissão a parceiro (a comissão é só declarada; o BV do evento segue como está).
- Benefício de indicação (personagem extra etc.): decisão do dono, não entra no texto.
- Modelos (templates) novos na Meta, ligar o CRM, mudar o filtro da nota 5.
- Código de referência e leitura automática de "indicado por" na primeira mensagem (feature 348).
- Pedir aceite na loja além do que a 344 já faz; aviso de privacidade do site.
- Pedir aceite em massa para as 6.291 fichas antigas.

## Docs a atualizar

`docs/01` §3 (endpoints) e §4.3 (gates), schema; `docs/02` (ficha, conversa, Pós-evento, Aniversários,
Parceiros, página de avaliação); `docs/03` (entrada no topo); `docs/04` §Clientes (invariantes do
consentimento) e §Conversas (saída automática); `docs/05` (risca a dívida do opt-out manual; registra
o que fica); `docs/00` §6 item 2 (o relógio das tabelas novas).

## Premissas

- Os horários do consentimento seguem o relógio de São Paulo (`now_sp()`), o mesmo do aceite da loja
  (344), para que aceite e retirada sejam comparáveis.
- "Dia seguinte" é atendido pela lista (ontem no topo); nada dispara sozinho.
- O registro do aceite pela equipe vale como prova junto da conversa/mensagem de origem (ponto para
  parecer jurídico).
- A pessoa que abre o link de avaliação é tratada como a contratante do evento (ponto para parecer).
