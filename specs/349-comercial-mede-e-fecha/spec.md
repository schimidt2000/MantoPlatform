# Feature 349 — O comercial mede e fecha pela conversa

**Branch**: `349-comercial-mede-e-fecha` (da `main`, head `20bf93c0`) · **Created**: 2026-11-17 · **Status**: Implementada na branch (verify 18/18; sem merge) ·
**Migration**: `a349c0e1f2a3` (aditiva: colunas novas em `conversas`, com preenchimento das conversas que já existem) ·
**Nível**: 1 (feature: migration, endpoints e telas) — constituição, Princípio VI

**Input**: pedido do dono (17/11/2026, sessão principal da "máquina de vendas"): fazer a feature "comercial mede e fecha"
da pesquisa "Máquina de vendas Manto" (§8.2 e §8.4), uma das quatro abertas ao mesmo tempo (348 origem completa, 349,
350 base autorizada, 351 painel atribuído).

## O pedido, nas palavras do dono *(obrigatório)*

> Primeira resposta, perdida e motivo, qualificada, filtros, criar evento na conversa, lembrete.

A pesquisa achou que a família decide de 6 a 10 dias depois do orçamento e pede orçamento a vários fornecedores ao
mesmo tempo; que responder em minutos é barato e pesa; e que 288 das 337 vendas passaram por um vendedor só. O CRM
próprio (325–335) já guarda as conversas, o orçamento enviado e de qual anúncio a cliente veio, mas o comercial não
mede nada do próprio trabalho: o tempo da primeira resposta não fica guardado, não existe "perdida" nem motivo, não
existe "qualificada", a lista não diz de onde a cliente veio nem em que etapa está, para cotar a vendedora sai da
conversa, o evento nasce longe da conversa com o vendedor digitado à mão, e orçamento parado não lembra ninguém.

O CRM está em produção, **desligado** até as chaves `WHATSAPP_*` no Render: tudo aqui fica pronto e só ganha dado com
ele ligado.

## Clarifications

### Session 2026-11-17

Decididas no fluxo autônomo (o dono pediu para perguntar pouco), sempre com a opção recomendada:

- Q: A conversa perdida que recebe mensagem nova da cliente reabre sozinha? → A: **Não.** Ela sobe na lista com o
  selo "Perdida" e a espera da 328 corre normalmente; quem atende decide "Reabrir". Reabrir sozinho apagaria o motivo
  a cada "obrigada" da cliente.
- Q: No funil, as perdidas e as qualificadas contam pelo dia em que foram marcadas ou pela coorte do período? → A:
  **Pela coorte** (as conversas cujo primeiro contato caiu no período), como as etapas da 335: o número de perdidas
  nunca passa do de "Chegou".
- Q: Quando o orçamento e o formulário trazem datas de evento diferentes, qual vale para a pontuação? → A: **A do fato
  mais recente** (em geral o formulário, que a cliente preencheu depois do orçamento).
- Q: A lista "Pararam em" do funil mostra as conversas perdidas daquela etapa? → A: **Sim, com o selo e o motivo**:
  elas pararam ali; o cartão "Perdidas por motivo" resume o total.

## Cenários e Verificação *(obrigatório)*

### História 1 — O tempo da primeira resposta fica guardado (Prioridade: P1)

Quando a cliente escreve pela primeira vez, a conversa guarda a hora. Quando a equipe responde pela primeira vez, a
conversa guarda a hora, quem respondeu e por onde. A resposta dada pelo app do celular (coexistência) ou por outro app
do Instagram chega sem autor: ela conta como resposta, e a tela diz "pelo celular, sem autor" em vez de inventar um
nome ou esconder o caso. A conversa mostra "1ª resposta em 12 min, por Ana" (ou "Sem resposta ainda"); o funil mostra,
por vendedor, a mediana do tempo da primeira resposta e quantas saíram em até 15 minutos.

**Por que esta prioridade**: é o número que a pesquisa diz faltar ("tempo até a primeira resposta contra taxa de
fechamento") e o mais barato de melhorar.

**Verificação**: cenários 1, 2 e 3 do `verify_349.py`.

**Cenários de aceite**:

1. **Dado** uma conversa nova, **Quando** a cliente escreve às 10h00 e a Ana responde pela Plataforma às 10h12,
   **Então** a conversa guarda 10h00, 10h12, a Ana e a origem "plataforma", e mostra "1ª resposta em 12 min, por Ana".
2. **Dado** uma conversa nova, **Quando** a equipe responde primeiro pelo celular (eco), **Então** a primeira resposta é
   o eco, sem autor, origem "celular", e a tela diz "pelo celular, sem autor".
3. **Dado** uma primeira resposta que a Meta aceitou e depois recusou (status `failed`), **Quando** o status chega,
   **Então** ela deixa de ser a primeira resposta, e a próxima resposta que valeu (ou nenhuma) toma o lugar.
4. **Dado** uma conversa aberta pela equipe com um modelo antes de a cliente escrever, **Quando** a cliente responde
   depois, **Então** o envio anterior não conta: a primeira resposta é a primeira da equipe depois da mensagem dela.
5. **Dado** conversas que já existiam antes desta feature, **Quando** a migration roda, **Então** as três informações
   são preenchidas a partir das mensagens guardadas.

---

### História 2 — Conversa perdida, com motivo (Prioridade: P1)

Na conversa, a vendedora marca "Perdida" e escolhe o motivo numa lista fechada (Achou caro, Fechou com outra empresa,
Sem data ou elenco na data, Desistiu ou adiou a festa, Parou de responder, Fora da área atendida, Outro — este pede
uma frase), no molde do encerramento de formulário (298). A conversa ganha o selo "Perdida" e sai da régua de
lembretes e do filtro de orçamento parado. "Reabrir" desfaz. A cliente que volta a escrever aparece no topo da lista
com o selo, e quem atende decide reabrir; criar o evento pela conversa reabre sozinho. O funil conta as perdidas do
período e o motivo de cada uma.

**Por que esta prioridade**: sem perda registrada, o funil só sabe que a conversa "parou"; com o motivo, o dono sabe
se perde por preço, por data ou por demora.

**Verificação**: cenários 4, 5 e 6 do `verify_349.py`.

**Cenários de aceite**:

1. **Dado** uma conversa aberta, **Quando** a vendedora marca "Perdida" com "Achou caro", **Então** a conversa guarda o
   motivo, quem marcou e quando, e a lista mostra o selo.
2. **Dado** "Outro" sem frase (ou um motivo fora da lista), **Quando** salva, **Então** o servidor recusa com 422 no
   campo, e nada é gravado.
3. **Dado** uma conversa perdida, **Quando** alguém clica "Reabrir", **Então** as quatro informações da perda somem.
4. **Dado** uma conversa perdida, **Quando** o evento é criado pela conversa, **Então** a perda some.

---

### História 3 — Conversa qualificada, por regra e por decisão (Prioridade: P2)

Cada conversa tem uma pontuação calculada por regras com o que o orçamento e o formulário já dizem: formulário
preenchido (+3), data do evento definida até 90 dias à frente (+2) ou mais longe (+1), orçamento enviado (+1), cliente
que já fechou evento antes (+2). Com 3 pontos ou mais, a conversa é "Qualificada (pela regra)". A vendedora pode
decidir à mão — "Qualificada" ou "Não qualificada" —, e a decisão dela vale sobre a regra até ser desfeita. A conversa
mostra a pontuação e de onde veio cada ponto. As regras são hipótese inicial, revista a cada trimestre com a taxa de
fechamento por sinal.

**Por que esta prioridade**: a 351 (painel atribuído) e o auditor precisam de "conversa qualificada" para medir
anúncio por conceito em vez de custo por conversa; a marca manual corrige o que a regra não vê.

**Verificação**: cenários 7 e 8 do `verify_349.py`.

**Cenários de aceite**:

1. **Dado** uma conversa com orçamento enviado e data do evento em 30 dias, **Quando** a conversa abre, **Então** a
   pontuação é 3, com os dois sinais listados, e o selo é "Qualificada".
2. **Dado** essa conversa, **Quando** a vendedora marca "Não qualificada", **Então** o selo some, a pontuação continua
   visível, e a tela diz que a decisão foi dela.
3. **Dado** a decisão manual, **Quando** ela escolhe "Usar a regra", **Então** a qualificação volta a seguir a pontuação.

---

### História 4 — A lista diz de onde veio, em que etapa está e quem espera (Prioridade: P1)

Cada item da lista de conversas mostra, além do que já mostra, selos curtos: "Anúncio" quando a cliente veio de
anúncio, a etapa mais avançada da conversa (Orçamento enviado, Formulário, Evento fechado, Pagou, Avaliou — a mesma
régua do funil), "Qualificada" e "Perdida". Um segundo grupo de filtros, combinável com Todas/Minhas/Sem responsável e
com o canal: "Esperando resposta", "Orçamento parado" (2, 5 ou 9 dias) e "Veio de anúncio". O filtro mora no endereço.

**Por que esta prioridade**: é o que a vendedora usa o dia todo; hoje ela abre conversa por conversa para saber quem
precisa de follow-up.

**Verificação**: cenários 9, 10 e 11 do `verify_349.py`, e a tela em 390 px.

**Cenários de aceite**:

1. **Dado** conversas com e sem anúncio, com e sem orçamento, **Quando** a lista abre, **Então** cada item mostra os
   selos certos, e a conversa sem nada a mostrar não ganha selo.
2. **Dado** o filtro "Esperando resposta", **Quando** aplicado, **Então** só vêm as conversas com a cliente esperando.
3. **Dado** o filtro "Orçamento parado — 5 dias", **Quando** aplicado, **Então** vêm as conversas cujo último orçamento
   foi enviado há 5 dias ou mais, sem formulário nem evento depois, e não perdidas; a de 3 dias não vem.
4. **Dado** o filtro "Veio de anúncio", **Quando** aplicado, **Então** só vêm as conversas com contato por anúncio.

---

### História 5 — Cotar sem sair da conversa (Prioridade: P2)

No diálogo de envio de orçamento, "Fazer orçamento" abre a calculadora já com o nome da cliente e a marca da conversa
("Orçamento para a conversa com Ana · Voltar para a conversa"). "Gerar orçamento" salva e volta para a conversa com o
diálogo de envio aberto e o orçamento novo escolhido: falta só tocar em "Enviar".

**Por que esta prioridade**: tira a ida e volta entre telas no celular, mas a vendedora já consegue cotar hoje.

**Verificação**: tela (fluxo completo no Browser pane, em 390 px); sem cenário de banco além do envio, que é o da 333.

**Cenários de aceite**:

1. **Dado** uma conversa com a Ana, **Quando** a vendedora toca "Fazer orçamento", **Então** a calculadora abre com
   "Ana" no nome e a faixa de volta para a conversa.
2. **Dado** a calculadora aberta pela conversa, **Quando** a vendedora toca "Gerar orçamento", **Então** volta à
   conversa com o diálogo de envio aberto e o orçamento recém-salvo escolhido.
3. **Dado** a calculadora aberta pela conversa, **Quando** a página carrega, **Então** ela faz o mesmo número de
   cálculos que faria com o nome digitado à mão (nenhuma requisição a mais por tecla).

---

### História 6 — Criar o evento a partir da conversa (Prioridade: P2)

Na conversa, "Criar evento" abre a criação de evento já com o último orçamento enviado nessa conversa, a ficha da
cliente como Contratante e o vendedor igual a quem atende a conversa. Sem ficha ligada, o botão abre "Ligar à ficha"
primeiro. O evento criado assim fica ligado à conversa num ponto único do servidor: hoje o vínculo passa pela ficha
(a ficha da conversa entra entre as clientes do evento); a coluna `conversa_id` do evento, que é da 348, se pluga
nesse mesmo ponto.

**Por que esta prioridade**: fecha o caminho conversa → evento e acaba com o vendedor digitado à mão, que hoje
distorce a comissão e o funil por vendedor.

**Verificação**: cenários 12 e 13 do `verify_349.py`, e a tela.

**Cenários de aceite**:

1. **Dado** uma conversa com ficha, orçamento enviado e responsável Ana, **Quando** a vendedora toca "Criar evento",
   **Então** a criação abre com o orçamento, a ficha como Contratante e a Ana como vendedora.
2. **Dado** o evento criado com a conversa, **Quando** ele é salvo, **Então** a ficha da conversa está entre as
   clientes do evento e a perda da conversa (se havia) some.
3. **Dado** um `conversa_id` que não existe, **Quando** o evento é criado, **Então** o servidor recusa com 422 no
   campo, sem criar o evento.

---

### História 7 — Orçamento parado vira lembrete para a equipe (Prioridade: P2)

"Lembrar amanhã" na conversa (e na lista "Pararam em" do funil) marca um aviso no sino de quem tocou, amanhã às 9h.
Além disso, a régua automática avisa no sino quando o último orçamento da conversa completa 2, 5 e 9 dias sem
formulário, sem evento e sem perda — cobrindo a janela de decisão de 6 a 10 dias. O aviso vai para quem atende a
conversa (ou para a equipe, se ninguém atende), só das 9h às 21h. **Nada sai para a cliente**: lembrete é aviso para a
equipe.

**Por que esta prioridade**: a venda decidida no 6º ao 10º dia é a que se perde por esquecimento.

**Verificação**: cenários 14, 15 e 16 do `verify_349.py`.

**Cenários de aceite**:

1. **Dado** uma conversa, **Quando** a vendedora toca "Lembrar amanhã", **Então** o lembrete fica marcado para amanhã
   às 9h, e a conversa mostra "Lembrete amanhã às 9h" com "Cancelar lembrete".
2. **Dado** o lembrete vencido, **Quando** a varredura roda, **Então** sai um aviso no sino de quem marcou, uma vez só,
   e o lembrete some da conversa.
3. **Dado** um orçamento enviado há 5 dias sem decisão, **Quando** a varredura roda às 10h, **Então** sai um aviso
   "Orçamento para Ana sem retorno há 5 dias" para quem atende, uma vez só; às 22h nada sai; com a conversa perdida
   nada sai.
4. **Dado** o lembrete e a régua, **Quando** rodam, **Então** nenhuma mensagem é gravada nem enviada na conversa.

---

### Casos de borda

- Duas mensagens da cliente processadas fora de ordem: a primeira mensagem é sempre a mais antiga (gravação
  condicional), e a primeira resposta é recalculada se a primeira mensagem andar para trás.
- Resposta pela Plataforma e eco do celular quase juntos: vale a de horário mais antigo; a gravação é condicional
  (`primeira_resposta_em IS NULL`).
- Instagram aberto pelo anúncio sem mensagem: não há primeira mensagem ainda; a primeira resposta só conta depois da
  primeira mensagem dela.
- Conversa perdida que recebe mensagem nova: continua perdida (com o selo), sem régua; quem atende reabre.
- Régua com a Plataforma parada por dias: no retorno, sai só o degrau atual (o maior já alcançado), nunca três avisos
  de uma vez; depois do 10º dia sem decisão, a régua acabou.
- "Lembrar amanhã" tocado duas vezes: o segundo substitui o primeiro (um lembrete por conversa).
- Quem marcou o lembrete perdeu o acesso: o aviso vai para quem atende ou para a equipe.
- Responsável da conversa que não está entre os vendedores do evento: a criação abre com o vendedor padrão da tela
  (o usuário logado), e a vendedora escolhe.
- Ficha da conversa removida depois do orçamento: "Criar evento" pede a ficha de novo.
- Duas pessoas marcam perda (ou decidem a qualificação) quase juntas: vale a última gravação, com o nome dela; as duas
  são decisões válidas, não há conflito a recusar.
- "Lembrar amanhã" tocado depois da meia-noite: "amanhã" é o próximo dia do calendário de São Paulo, às 9h.
- O painel da venda falha ao carregar: a conversa continua lendo e respondendo; a faixa mostra "Não foi possível
  carregar a venda. Tente novamente." com o botão.
- Recorte sem resultado: estado vazio no padrão da casa ("Nenhuma conversa esperando resposta.", "Nenhum orçamento
  parado há 5 dias ou mais.", "Nenhuma conversa de anúncio encontrada.").

## Requisitos *(obrigatório)*

### Requisitos funcionais

**Primeira resposta**

- **FR-001**: A conversa DEVE guardar a hora da primeira mensagem da cliente (sem contar reação) e mantê-la sempre a
  mais antiga.
- **FR-002**: A conversa DEVE guardar a hora, o autor e a origem (`plataforma`, `celular`, `outro`) da primeira
  resposta válida da equipe depois da primeira mensagem — a mesma régua de "resposta válida" da espera (328): enviada
  e aceita, sem reação, sem "apagada/editada pelo celular".
- **FR-003**: A resposta que a Meta recusar depois do aceite DEVE deixar de ser a primeira resposta, e a seguinte que
  valeu toma o lugar.
- **FR-004**: A resposta sem autor (celular, outro app) DEVE aparecer como tal na conversa e no funil, contada à parte.
- **FR-005**: A migration DEVE preencher as três informações das conversas já existentes a partir das mensagens.
- **FR-006**: O funil DEVE mostrar, no total e por grupo, a mediana do tempo da primeira resposta, quantas saíram em
  até 15 minutos, quantas foram sem autor e quantas ainda não têm resposta.

**Perdida**

- **FR-007**: Comercial e Superadmin DEVEM poder marcar a conversa como perdida com um motivo da lista fechada; "Outro"
  exige frase de até 300 caracteres. A lista de motivos vem do servidor (fonte única), como no formulário (298).
- **FR-008**: "Reabrir" DEVE apagar a perda; marcar perdida DEVE cancelar o lembrete da conversa.
- **FR-009**: O funil DEVE contar as perdidas da coorte (as que não chegaram a Evento fechado) e dividi-las por motivo;
  a lista "Pararam em" DEVE mostrar a perdida com o selo e o motivo.
- **FR-009a**: Mensagem nova da cliente NÃO DEVE reabrir a conversa perdida.

**Qualificada**

- **FR-010**: O servidor DEVE calcular a pontuação da conversa pelas regras (FR na História 3), só com fatos depois do
  primeiro contato (a recompra olha para antes), e devolver os sinais que somaram. Com datas diferentes no orçamento e
  no formulário, vale a do fato mais recente.
- **FR-011**: Comercial e Superadmin DEVEM poder decidir "Qualificada", "Não qualificada" ou "Usar a regra"; a decisão
  manual vale sobre a regra e guarda quem e quando.
- **FR-012**: O funil DEVE contar as qualificadas (pela decisão ou pela regra) no total e por grupo.

**Lista**

- **FR-013**: Cada item da lista DEVE trazer: veio de anúncio (sim/não), a etapa mais avançada (régua do funil),
  qualificada, perdida (com o motivo) e se há lembrete — tudo calculado em lote para a página, nunca uma consulta por
  conversa.
- **FR-014**: A lista DEVE aceitar o recorte `esperando`, `orcamento_parado` (com `dias` em 2, 5 ou 9; padrão 2) e
  `anuncio`, combinável com o filtro de responsável, o canal e a busca; recorte desconhecido → 422 no campo.
- **FR-015**: "Orçamento parado há N dias" DEVE ser: último orçamento enviado (pela conversa ou ligado à ficha) depois
  do primeiro contato, há N dias ou mais, sem formulário nem evento vivo da ficha depois dele, e conversa não perdida.

**Cotar sem sair**

- **FR-016**: A calculadora DEVE aceitar o nome da cliente e a conversa pelo endereço, preencher o nome uma vez ao
  abrir e, ao gerar o orçamento, voltar para a conversa com o envio pronto. Nenhuma requisição a mais por tecla.

**Criar evento**

- **FR-017**: O servidor DEVE dizer, por conversa, o que levar para o evento: o último orçamento enviado nela, a ficha
  e o vendedor (quem atende; senão quem mandou o último orçamento).
- **FR-018**: A criação de evento DEVE aceitar a conversa de origem (opcional) e chamar um ponto único que liga o
  evento à conversa — hoje: a ficha da conversa entre as clientes do evento e a perda apagada; com a 348, a coluna
  `conversa_id`. Conversa inexistente → 422 no campo, nada criado.

**Lembrete**

- **FR-019**: Comercial e Superadmin DEVEM poder marcar "Lembrar amanhã" (amanhã às 9h de São Paulo, para quem tocou)
  e cancelar; um lembrete por conversa.
- **FR-020**: A varredura das conversas DEVE emitir o aviso do lembrete vencido (uma vez, e apagar o lembrete) e o
  aviso da régua de 2, 5 e 9 dias (um por degrau por orçamento, só o degrau atual, só das 9h às 21h).
- **FR-021**: Lembrete e régua NUNCA DEVEM gravar nem enviar mensagem na conversa.

### Entidades

- **Conversa** (`conversas`, `app/models.py`): ganha a primeira mensagem (`primeira_recebida_em`), a primeira resposta
  (`primeira_resposta_em`, `primeira_resposta_por_id`, `primeira_resposta_origem`), a perda (`perdida_em`,
  `perdida_motivo`, `perdida_nota`, `perdida_por_id`), a decisão de qualificação (`qualificacao`, `qualificacao_em`,
  `qualificacao_por_id`) e o lembrete (`lembrar_em`, `lembrar_para_id`). Migration à mão `a349c0e1f2a3` sobre
  `d334b2c4e6f8`, aditiva, com o preenchimento da FR-005.
- **Aviso do sino** (`notifications`, feature 272): dois `kind` novos no catálogo — `conversa.lembrete` e
  `conversa.orcamento_parado`. Sem tabela nova.

### RBAC

Todos pelo papel real de Conversas (`pode_conversas`: COMERCIAL e SUPERADMIN), função no início da view; linha na
tabela de `docs/01` §4.3.

- `GET /api/conversas` — parâmetros novos `recorte` e `dias`; campo novo `venda` em cada item.
- `GET /api/conversas/<id>/venda` — painel da venda (etapa, pontuação, primeira resposta, perda, lembrete, o que levar
  ao evento, motivos de perda).
- `POST /api/conversas/<id>/perdida` e `DELETE /api/conversas/<id>/perdida`.
- `POST /api/conversas/<id>/qualificacao`.
- `POST /api/conversas/<id>/lembrete` e `DELETE /api/conversas/<id>/lembrete`.
- `GET /api/conversas/funil` e `/funil/parados` — campos novos.
- `POST /api/events` — campo opcional `conversa_id`; gate de sempre (`_can_create_event`, COMERCIAL e SUPERADMIN).

## Verificação (`verify_349.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/349-comercial-mede-e-fecha/verify_349.py`, contra o espelho próprio **`manto_349`** (restaurado do dump
noturno de 17/11; o `manto_local` é compartilhado e não recebe escrita desta feature), com `DATABASE_URL` de
`.local-db-url`, `FLASK_ENV=development` e `MANTO_SEM_THREADS=1`. Login só por `POST /api/auth/login`; escrita
conferida por conexão separada; Meta e push nunca chamados (`WHATSAPP_SUPPRESS_SEND` e dublês); limpeza no `finally`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | recebida 10h00 + envio aceito 10h12 pela Plataforma | primeira mensagem, resposta, autor e origem gravados | não |
| 2 | eco do celular antes da Plataforma | primeira resposta sem autor, origem `celular` | não |
| 3 | `failed` na primeira resposta; modelo antes da cliente | recálculo; envio anterior à cliente não conta | não |
| 4 | marcar perdida "Achou caro" e reabrir | colunas gravadas/apagadas, lembrete cancelado | não |
| 5 | "Outro" sem frase; motivo inventado | 422 no campo, nada gravado | **sim** (recusa) |
| 6 | funil com perdida, resposta e qualificada | contagens, mediana e motivos no total e por grupo | não |
| 7 | pontuação: orçamento + data em 30 dias; recompra | 3 pontos e sinais; recompra soma | não |
| 8 | decisão manual "Não qualificada" e "Usar a regra" | a decisão vence e volta | não |
| 9 | lista com selos | anúncio, etapa, qualificada, perdida e lembrete por item | não |
| 10 | recortes `esperando` e `anuncio` | só as conversas certas | não |
| 11 | recorte `orcamento_parado` 2/5/9 | janela, decisão e perda excluem; `recorte` inválido → 422 | não |
| 12 | `GET …/venda` e `POST /api/events` com `conversa_id` | o que levar; ficha entre as clientes; perda apagada | não |
| 13 | `POST /api/events` com conversa inexistente | 422 `conversa_id`, nenhum evento criado | **sim** (recusa) |
| 14 | "Lembrar amanhã" e o vencido na varredura | 9h de SP; um aviso só; lembrete apagado | não |
| 15 | régua 2/5/9 às 10h e às 22h; perdida | o degrau atual uma vez; nada à noite; nada na perdida | não |
| 16 | lembrete e régua | nenhuma linha nova em `conversa_mensagens` | não |
| 17 | Casting tenta marcar perdida, decidir, lembrar e ler `…/venda` | 403 em todos | **sim** |
| 18 | limpeza | usuários, conversas, eventos e avisos descartáveis apagados (`roles.clear()` antes do usuário) | — |

Conferência de tela (internal, 390 px e computador): `/conversas` (selos, filtros, faixa da venda, perda, qualificação,
lembrete, "Criar evento"), `/orcamento?conversa=…` (faixa e volta), `/events/new?conversa=…`, `/funil` (colunas novas,
perdidas, "Lembrar amanhã").

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Com o CRM ligado, 100% das conversas com mensagem da cliente e resposta da equipe têm o tempo da primeira
  resposta guardado, inclusive as respondidas pelo celular (marcadas como sem autor).
- **SC-002**: O dono responde "quanto tempo cada vendedor leva para responder" e "por que perdemos" olhando só o funil,
  sem planilha.
- **SC-003**: A vendedora encontra, em um toque, quem espera resposta e quem recebeu orçamento há 2, 5 ou 9 dias sem
  decidir.
- **SC-004**: Do orçamento ao envio, a vendedora não precisa achar a conversa de novo: cotar e enviar leva no máximo três
  toques depois de "Gerar orçamento" (nenhum, além de "Enviar").
- **SC-005**: Todo evento criado pela conversa sai com o vendedor certo sem digitação.
- **SC-006**: Nenhum orçamento enviado passa da janela de 10 dias sem ao menos três avisos à equipe, salvo se perdido ou
  decidido antes; e nenhuma mensagem sai para a cliente por conta de lembrete.
- **SC-007**: A lista de conversas continua tão rápida quanto hoje no celular (sem consulta por item).

## Fora de escopo

- Coluna `conversa_id` no evento e no orçamento, `ctwa_clid`, gclid e frente como coluna (348).
- Opt-in, aniversário, indicação, pós-evento pela conversa (350); painel atribuído, metas e verba (351).
- Mandar conversões para a Meta ou o Google (features 7 e 8 da pesquisa).
- Lembrete com data escolhida, lembrete para outra pessoa, ação em lote no funil.
- Mensagem automática para a cliente (follow-up por modelo): continua manual pela caixa de envio.
- Tempo de resposta descontando a noite e o fim de semana (a mediana suaviza; fica como dívida se o dono quiser).
- Extração por IA de campos da conversa para a pontuação (Fase 5 do plano do CRM).

## Docs a atualizar

`docs/01` (§3 inventário de endpoints, §4.3 RBAC, schema de `conversas`), `docs/02` (Conversas, Funil, Calculadora de
orçamento, Criar evento), `docs/03` (entrada no topo), `docs/04` §Conversas (primeira resposta, perda, qualificação,
régua), `docs/05` (dívidas criadas/quitadas).

## Premissas

- Decisões tomadas no fluxo autônomo (a pesquisa e o pedido não fixaram); o dono pode trocá-las sem mudar o desenho:
  - motivos de perda: os sete da História 2;
  - pontos e corte da qualificação: os da História 3 (hipótese, revista por trimestre);
  - régua: 2, 5 e 9 dias após o último orçamento; "amanhã" = 9h de São Paulo; horário dos avisos = o do alerta de
    espera (9h às 21h);
  - tempo de primeira resposta em tempo corrido; o funil usa mediana e "até 15 min" (o mesmo limite do alerta).
- O vendedor do evento segue as regras de hoje (lista de vendedores da criação de evento); a feature só pré-preenche.
- A perda não esconde a conversa da lista: a caixa continua sendo de todas as mensagens.
- Lembrete e régua rodam na varredura das conversas, que só existe com o CRM ligado; com ele desligado não há conversa
  nem orçamento enviado pela conversa para lembrar.
