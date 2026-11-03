# Feature 328 — Conversas em equipe: responsável, alerta de cliente esperando, notas, respostas rápidas e áudio

**Branch**: `328-crm-equipe-na-caixa` (da `325-crm-whatsapp-fundacao`, que ainda não está na `main`, por decisão
do dono: "continuar a implementação sem fazer o push") · **Created**: 2026-11-03 · **Status**: Implementado, não publicado ·
**Migration**: sim, aditiva (3 colunas em `conversas`, 2 tabelas novas) · **Nível**: 1 (feature)

**Input**: pedido do dono (03/11): "Dá para continuar a implementação sem fazer o push?? Vou deixar mais pra
frente". As quatro decisões de equipe foram respondidas no mesmo dia (Clarifications).

## O pedido, nas palavras do dono *(obrigatório)*

> "Se tornarmos a nossa usabilidade boa o suficiente, a ideia é que 3 pessoas usem sempre pelo mesmo número."
> (30/10)

> "Dá para continuar a implementação sem fazer o push?? Vou deixar mais pra frente" (03/11)

É a Fase 2 do `docs/PLANO_CRM_PROPRIO.md`, primeira parte: a **equipe** na caixa de conversas. O plano
chamava de "Caixa de conversas" e dividia em três pedaços; o dono escolheu este primeiro.
- **Esta feature:** responsável e transferência, alerta de cliente esperando, notas internas, respostas
  rápidas e áudio gravado no navegador.
- **Depois:** Instagram Direct na mesma caixa e notificação no celular (push).

## Clarifications

### Session 2026-11-03

Perguntas feitas ao dono antes da spec, respondidas todas com a opção recomendada:

- Q: Quando chega uma conversa nova, como ela vai para uma das 3 pessoas? → A: **Fila livre**. Todos veem a
  conversa nova; quem responder primeiro vira o responsável, com o nome à vista. Dá para transferir.
- Q: Depois de quanto tempo sem resposta a cliente vira alerta no sino? → A: **15 minutos, das 9h às 21h**
  (São Paulo). O alerta vai para o responsável ou, se ninguém assumiu, para todos. Fora do horário não toca;
  de manhã aparece o que ficou.
- Q: Quem cria e edita as respostas rápidas? → A: **Qualquer Comercial**. É uma lista só, da equipe.
- Q: O que vem primeiro depois da fundação? → A: **A equipe na caixa** (esta feature). Depois, o Instagram
  Direct e o push no celular.

## Cenários e Verificação *(obrigatório)*

### História 1 — Fila livre e responsável (Prioridade: P1)

A conversa nova chega "Sem responsável" e aparece para as três pessoas. Quem responde primeiro pela Plataforma
vira a responsável, e o nome dela aparece na lista e na conversa. Dá para **Assumir** uma conversa sem dono,
**Transferir** para outra pessoa da equipe e **Devolver à fila**. A lista filtra entre "Todas", "Minhas" e
"Sem responsável".

**Por que esta prioridade**: com três pessoas no mesmo número, sem dono a cliente é respondida duas vezes ou
fica sem resposta.

**Verificação**: cenários 1 a 6 do `verify_328.py`.

**Cenários de aceite**:

1. **Dado** uma conversa sem responsável, **Quando** a Ana responde pela Plataforma, **Então** a Ana vira a
   responsável.
2. **Dado** uma conversa com a Ana responsável, **Quando** a Bia responde, **Então** a Ana continua
   responsável: responder não "rouba" a conversa.
3. **Dado** uma conversa sem responsável, **Quando** a Bia clica "Assumir" ao mesmo tempo que a Ana, **Então**
   só uma assume e a outra recebe "Esta conversa já foi assumida por …".
4. **Dado** uma conversa da Ana, **Quando** ela transfere para a Bia ou devolve à fila, **Então** o
   responsável muda e todos veem a mudança.
5. **Dado** uma mensagem que a equipe mandou pelo app do celular (eco), **Quando** ela chega, **Então** a
   conversa **não** ganha responsável, porque o app não diz quem enviou.

### História 2 — Alerta de cliente esperando (Prioridade: P1)

Se a cliente escreveu e ninguém respondeu em 15 minutos, entre 9h e 21h, o sino avisa: "Ana Souza espera
resposta há 15 min." O aviso vai para a responsável ou, se ninguém assumiu, para toda a equipe. É um aviso por
espera; quando alguém responde (pela Plataforma ou pelo celular), o aviso some. Na lista, a conversa esperando
mostra há quanto tempo.

**Por que esta prioridade**: a cliente que espera esfria, e o tempo da primeira resposta é o que mais pesa na
venda de festa.

**Verificação**: cenários 7 a 11.

**Cenários de aceite**:

1. **Dado** uma mensagem da cliente sem resposta há 16 min, às 14h, **Quando** a varredura roda, **Então** a
   responsável recebe um aviso no sino com o link da conversa.
2. **Dado** o mesmo caso sem responsável, **Quando** a varredura roda, **Então** todos do Comercial e o
   Superadmin recebem o aviso.
3. **Dado** que a varredura roda de novo, **Quando** a espera ainda é a mesma, **Então** ninguém recebe aviso
   repetido.
4. **Dado** a espera às 22h30, **Quando** a varredura roda, **Então** não sai aviso; às 9h do dia seguinte,
   ele sai.
5. **Dado** um aviso enviado, **Quando** alguém responde, **Então** o aviso some do sino de todos e a lista
   deixa de mostrar a espera.

### História 3 — Notas internas (Prioridade: P2)

Na conversa, a pessoa escreve uma **nota interna** ("cliente quer saber do Papai Noel em dezembro, ligar
amanhã"). A nota nunca sai para a cliente: aparece na linha do tempo, com outro visual e o autor. Vale com a
janela de 24 h fechada.

**Verificação**: cenários 12 e 13.

**Cenários de aceite**:

1. **Dado** uma conversa, **Quando** a Ana grava uma nota, **Então** ela aparece na conversa como nota da Ana,
   e a Meta não é chamada.
2. **Dado** uma nota vazia, **Quando** a Ana tenta gravar, **Então** o sistema recusa e aponta o campo.

### História 4 — Respostas rápidas (Prioridade: P2)

A equipe mantém uma lista de textos prontos ("Formas de pagamento", "Endereço do escritório"). Na caixa de
envio, o botão de respostas rápidas (ou digitar "/" no começo do campo) abre a lista, que filtra pelo título ou
pelo atalho. Escolher uma **insere o texto no campo**, sem enviar. `{nome}` vira o primeiro nome do contato.
Qualquer pessoa do Comercial cria, edita e exclui; excluir pede confirmação.

**Verificação**: cenários 14 a 16.

**Cenários de aceite**:

1. **Dado** uma resposta "Olá, {nome}! Segue o catálogo.", **Quando** a Ana a escolhe na conversa da Ana Souza,
   **Então** o campo recebe "Olá, Ana! Segue o catálogo." e nada é enviado ainda.
2. **Dado** um título repetido ou um atalho repetido, **Quando** alguém grava, **Então** o sistema recusa e
   aponta o campo.
3. **Dado** alguém do Casting, **Quando** tenta listar ou criar, **Então** recebe 403.

### História 5 — Gravar áudio no navegador (Prioridade: P2)

Na caixa de envio, o microfone grava um áudio. O tempo aparece correndo, e dá para cancelar ou enviar. Ele
chega à cliente como **nota de voz** do WhatsApp. O Chrome grava num formato que o WhatsApp não aceita (webm), e
a Plataforma converte para ogg antes de enviar, sem recodificar. Sem permissão de microfone, a tela diz como
liberar.

**Verificação**: cenários 17 e 18.

**Cenários de aceite**:

1. **Dado** um áudio webm (Chrome), **Quando** é enviado, **Então** ele sai para a Meta como `audio/ogg`, com a
   marca de nota de voz, e a cópia guardada é o ogg.
2. **Dado** que o ffmpeg não está disponível, **Quando** chega um webm, **Então** o envio é recusado com "Não
   foi possível preparar o áudio. Envie o arquivo pelo clipe." e nada sai.

### Casos de borda

- **Responsável sem papel.** A pessoa perdeu o papel ou foi desativada. A conversa continua com o nome dela,
  qualquer um pode assumir de novo ("Assumir" vale também quando o responsável não tem mais acesso), e o alerta
  dessa conversa vai para a equipe toda.
- **Resposta que falhou.** Mensagem "não entregue" não conta como resposta: a espera continua.
- **Modelo aprovado conta como resposta.** Encerra a espera e atribui como o texto.
- **Várias mensagens seguidas da cliente.** A espera conta da **primeira** sem resposta.
- **Fronteira das 21h.** A espera que completa 15 min às 20h58 avisa. A que completa às 21h05 avisa às 9h.
- **Resposta rápida com `{nome}` sem nome de contato.** O marcador vira vazio e a vírgula que sobra não quebra
  o texto ("Olá! Segue o catálogo.").

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: A conversa DEVE ter um responsável opcional (pessoa da equipe). Conversa nova nasce sem
  responsável.
- **FR-002**: O primeiro envio bem-sucedido pela Plataforma (texto, arquivo, áudio ou modelo) numa conversa sem
  responsável DEVE torná-la do autor. Envio em conversa com responsável não muda o responsável. O eco do celular
  não atribui.
- **FR-003**: "Assumir" DEVE ser atômico: só tem efeito se a conversa está sem responsável (ou com responsável
  sem papel de conversas). Na corrida, o segundo recebe 409 com o nome de quem assumiu.
- **FR-004**: "Transferir" DEVE aceitar só pessoas ativas com papel de conversas (422 nos demais). "Devolver à
  fila" tira o responsável. Os dois valem para qualquer pessoa da equipe.
- **FR-005**: A lista DEVE filtrar entre "Todas", "Minhas" e "Sem responsável", e mostrar o responsável e o
  tempo de espera de cada conversa.
- **FR-006**: A conversa DEVE guardar o início da espera: o momento da primeira mensagem da cliente ainda sem
  resposta. Fica vazio quando a equipe responde pela Plataforma (envio aceito pela Meta) ou pelo celular (eco).
- **FR-007**: Uma rotina periódica DEVE emitir o aviso "esperando" quando a espera passa de **15 minutos**,
  **só entre 9h e 21h de São Paulo**. Destinatário: o responsável com papel de conversas; senão, toda a equipe.
  No máximo **um aviso por espera** (identidade = conversa + início da espera).
- **FR-008**: Quando a espera termina, os avisos "esperando" daquela conversa DEVEM ser apagados.
- **FR-009**: A equipe DEVE poder gravar notas internas numa conversa (texto de 1 a 2.000 caracteres). Elas
  nunca são enviadas, valem com a janela fechada e aparecem na conversa com autor e horário.
- **FR-010**: A equipe DEVE poder criar, editar e excluir respostas rápidas: título de até 80 caracteres e
  único; atalho opcional de até 30, sem espaço e único; texto de até 4.096.
- **FR-011**: Escolher uma resposta rápida DEVE inserir o texto no campo, trocando `{nome}` pelo primeiro nome
  do contato, **sem enviar**.
- **FR-012**: A caixa de envio DEVE gravar áudio pelo microfone (MediaRecorder). A gravação tem tempo
  correndo, "Cancelar" e "Enviar", e para sozinha em **5 minutos**. O áudio vai como nota de voz. Com a
  permissão negada ou sem microfone, a tela diz "Não foi possível usar o microfone. Libere o acesso nas
  configurações do navegador." e nada é gravado.
- **FR-013**: O servidor DEVE aceitar áudio `audio/webm` (Chrome) e convertê-lo para `audio/ogg` (Opus) com o
  ffmpeg da casa antes de guardar e enviar, sem recodificar. Sem ffmpeg ou se a conversão falhar → 422 com
  mensagem clara, e nada é enviado.
- **FR-014**: Áudio ogg/opus enviado pela Plataforma DEVE ir com a marca de nota de voz (`voice: true`).
- **FR-015**: Todos os endpoints novos: COMERCIAL e SUPERADMIN (papel real), 403 nos demais.
- **FR-016**: Os textos novos seguem o Princípio XV ("Assumir", "Transferir", "Devolver à fila", "Nota
  interna", "Respostas rápidas", "Gravar áudio").
- **FR-017**: No celular (até 767 px), o menu do responsável, a alternância Mensagem/Nota, o botão de
  respostas rápidas e o microfone DEVEM ter alvo de toque de 44 px ou mais. A lista de respostas rápidas abre
  na largura da tela. Nada pode exigir rolagem lateral de 320 a 430 px.
- **FR-018**: Transferir uma conversa para outra pessoa DEVE avisá-la no sino: "{Quem} transferiu a conversa
  com {Nome} para você.", com o link. Quem transfere para si mesmo ("Assumir") não gera aviso.

### Entidades

Modelo em `app/models.py`, migration à mão.

- **Conversa** (colunas novas): `responsavel_id` (pessoa da equipe, SET NULL), `assumida_em` (UTC) e
  `aguardando_desde` (UTC, início da espera).
- **Nota da conversa**: conversa (CASCADE), autor (SET NULL), texto e horário.
- **Resposta rápida**: título (único), atalho (único, opcional), texto, quem criou, quem alterou e horários.

### RBAC

- `POST /api/conversas/<id>/responsavel` (assumir, transferir, devolver), `GET /api/conversas/equipe`,
  `POST /api/conversas/<id>/notas` e `GET|POST|PATCH|DELETE /api/conversas/respostas-rapidas…`: COMERCIAL e
  SUPERADMIN (`pode_conversas`), papel real.
- `GET /api/conversas` e `GET /api/conversas/<id>` mudam só no payload (responsável, espera, notas).

## Verificação (`verify_328.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/328-crm-equipe-na-caixa/verify_328.py`, contra `manto_local`, no molde do `verify_325`: disjuntor
de rede, dublê da Meta, conferência por conexão separada, login só por `POST /api/auth/login` e limpeza no
`finally`. Usuários descartáveis: Ana (Comercial), Bia (Comercial) e Casting.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Conversa nova | sem responsável | não |
| 2 | Ana envia texto | Ana vira responsável | não |
| 3 | Bia envia na conversa da Ana | Ana continua | não |
| 4 | Assumir conversa já assumida | 409 com o nome | **sim** |
| 5 | Transferir para a Bia; transferir para o Casting; devolver à fila | Bia (com aviso no sino dela); 422; sem responsável | 422 **sim** |
| 6 | Eco do celular em conversa sem responsável | continua sem responsável e a espera termina | não |
| 7 | Espera de 16 min às 14h, com responsável | 1 aviso para a responsável | não |
| 8 | Espera sem responsável | aviso para toda a equipe | não |
| 9 | Varredura de novo | nenhum aviso repetido | não |
| 10 | Espera às 22h30 | nenhum aviso; às 9h sim | não |
| 11 | Resposta encerra a espera (texto; e, noutra conversa, modelo aprovado) | `aguardando_desde` vazio, os avisos de espera apagados e o de transferência mantido; o modelo também atribui | não |
| 12 | Nota interna | gravada com autor; a Meta não é chamada | não |
| 13 | Nota vazia | 422 com `fields.texto` | **sim** |
| 14 | CRUD de resposta rápida (Bia cria, Ana edita, Ana exclui) | lista da equipe | não |
| 15 | Título ou atalho repetido | 422 com o campo | **sim** |
| 16 | Casting lista, cria ou assume | 403 | **sim** |
| 17 | Áudio webm convertido | a Meta recebe `audio/ogg` com `voice: true`; a cópia guardada é ogg | não |
| 18 | Sem ffmpeg | 422, nada sai | **sim** |
| 19 | Envio que falhou na hora; e status `failed` que chega depois do aceite | não atribui e não encerra a espera; a falha tardia reabre a espera na primeira recebida sem resposta | não |
| 20 | Limpeza | conversas, notas, respostas, avisos e usuários de teste apagados | — |

Conferência de tela: lista (filtros, responsável, espera), conversa (assumir, transferir, nota, respostas
rápidas, gravar áudio), em desktop e em 375×812.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Nenhuma conversa fica "de ninguém" depois da primeira resposta: 100% das conversas respondidas
  pela Plataforma têm responsável.
- **SC-002**: A cliente que espera 15 min entre 9h e 21h gera aviso em até 1 minuto, uma vez só.
- **SC-003**: Responder com uma resposta rápida leva no máximo 3 toques (abrir a lista, escolher, enviar).
- **SC-004**: Um áudio gravado no Chrome ou no Firefox chega à cliente como nota de voz; gravado no Safari,
  chega como áudio comum, que toca do mesmo jeito (Premissas).

## Fora de escopo

- Instagram Direct (próxima feature da Fase 2) e push no celular (a seguinte).
- Rodízio automático e distribuição por uma pessoa (o dono escolheu a fila livre).
- Respostas rápidas por pessoa, com variáveis além de `{nome}` ou com anexo.
- Horário de atendimento configurável na tela (9h–21h fica fixo em constante; ver Premissas).
- Métricas de tempo de resposta por vendedor (Fase 3).

## Docs a atualizar

- `docs/01`: colunas e tabelas, endpoints, RBAC §4.3.
- `docs/02`: a tela Conversas ganha filtros, responsável, nota, respostas rápidas e áudio.
- `docs/03`: entrada no topo.
- `docs/04`: invariantes de responsável e de espera, na linha "Conversas".
- `docs/05`: o que ficar de dívida.
- `docs/PLANO_CRM_PROPRIO.md`: a Fase 2a marcada.

## Premissas

- **Horário de atendimento**: 9h–21h de São Paulo, de domingo a domingo. É constante no código
  (`HORARIO_DE_ALERTA`); uma tela para configurar fica para quando o dono pedir.
- **Quem é "a equipe"**: usuários ativos com acesso e papel COMERCIAL ou SUPERADMIN, os mesmos do gate
  `pode_conversas`.
- **Nota interna é registro**: nesta fase não se edita nem se exclui (como a observação do evento). Corrigir é
  escrever outra nota.
- **Respostas rápidas** aparecem em ordem alfabética do título.
- **Prazo da varredura**: a rotina de alerta roda na thread `whatsapp-sweep` (a cada 60 s), então o aviso
  sai entre 15 e 16 minutos.
- **Áudio no Safari** sai em `audio/mp4` (AAC), que a Meta aceita como áudio comum, sem a marca de nota de voz
  (ela exige ogg/opus). Firefox grava ogg direto.
