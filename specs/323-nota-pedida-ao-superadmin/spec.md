# Feature 323 — A nota pedida chega ao Superadmin com tudo o que a emissão precisa

**Branch**: `323-nota-pedida-ao-superadmin` (da `main`) · **Created**: 2026-10-28 · **Status**: Pronta (verify 15/15), aguardando merge ·
**Migration**: sim, aditiva (colunas novas em `calendar_events` e `event_invoices`) · **Nível**: 1
(feature) — constituição, Princípio VI

**Input**: pedido do dono: "Feature 323 — nota pedida ao superadmin. Quando o comercial marca
'Precisa de nota fiscal' no evento (criação OU edição), nasce a tarefa urgente de emitir a nota para
o superadmin (tela inicial) e um e-mail aos superadmins no estilo da 319. O comercial informa os
dados para emitir: CNPJ do tomador (vem do cliente), ISS retido pelo tomador e município de
prestação quando fora de SP, referência do cliente (AF/pedido), observações livres. A discriminação
da nota sai montada para copiar. Anexar o PDF conclui a tarefa (já existe, 069). Corrige o furo:
ligar o chip na edição pelo React não cria nota a emitir."

## O pedido, nas palavras do dono *(obrigatório)*

> "Quando for vendido um evento e ele for marcado no sistema que precisa de nota, gerar uma task
> para o superadmin gerar essa nota. Eu faria também um disparo por e-mail para quem é superadmin,
> falando nota solicitada por Thaís […]. Eu preciso de um pouco mais de informações: o valor, o que
> precisa ter na nota. Isso é um problema, porque o cliente informa por WhatsApp se ele precisa do
> ISS retido na nota, se ele precisa de X informações na descrição. Por padrão, a gente pode pegar
> o CNPJ, o valor, e no corpo da nota normalmente eu coloco o que é o evento e quando será feito o
> pagamento e embaixo os dados de pagamento. […] Isso tem que aparecer como urgente para o
> superadmin e ser recebido por e-mail também, seguindo o formato que a gente usou para o gasto
> extra, rápido, escrito no assunto para conseguir ver o que de fato eu preciso fazer."

O dono mandou cinco notas emitidas (NFS-e 99 a 103, outubro/2026) como modelo. O que elas mostram:

- **Tomador**: razão social, CNPJ, endereço e e-mail da contratante.
- **Discriminação**: uma linha do que é o evento ("Personagens para evento 17/10", "Apresentações
  Educamanto: Uma aventura Animal"); às vezes a referência do cliente na primeira linha
  ("AF 618/2026"); o bloco fixo dos dados bancários (Inter 077, Prime Dreams Eventos Ltda, CNPJ
  60.708.296/0001-21 como PIX, agência 0001, conta 44689668-3); às vezes o vencimento
  ("Vencimento: 16/10").
- **ISS**: só a nota de Jundiaí tem "ISS retido pelo tomador" e ISS devido fora de São Paulo
  (município de prestação: Jundiaí - SP). As outras não têm nada disso.

### O que já existe (feature 069) e o que falta

Hoje o chip "Precisa de nota fiscal" na **criação** do evento cria uma nota **a emitir** com o valor
da venda, e ela aparece só no card "Notas a Emitir" do painel Financeiro. Anexar o arquivo marca a
nota como **emitida**. Faltam:

1. a tarefa na tela inicial do Superadmin, em destaque de urgente;
2. o e-mail aos Superadmins;
3. os dados que a emissão precisa (tomador, ISS, município, referência, observações) e a
   discriminação montada;
4. **o furo**: ligar o chip na **edição** pelo app (formulário "Editar tudo" ou card Comercial do
   evento) não cria nota a emitir — a venda fica "com nota" e ninguém é avisado.

## Cenários e Verificação *(obrigatório)*

### História 1 — Ligar "Precisa de nota fiscal" pede a nota, em qualquer porta (Prioridade: P1) 🎯 MVP

A vendedora fecha a venda com nota, seja criando o evento, seja editando um evento que já existe
(formulário completo ou card Comercial). Em todas as portas, a venda passa a ter uma nota **a
emitir**, com o valor da venda, registrando quem pediu e quando.

**Por que esta prioridade**: sem isso a tarefa e o e-mail não têm de onde nascer, e o furo da edição
continua perdendo pedidos de nota.

**Verificação**: cenários 1–4 do `verify_323.py`.

**Cenários de aceite**:

1. **Dado** um evento novo, **Quando** a vendedora cria com "Precisa de nota fiscal" ligado,
   **Então** nasce uma nota a emitir com o valor da venda e "pedida por" = a vendedora.
2. **Dado** um evento sem nota, **Quando** a vendedora liga o chip pelo formulário "Editar tudo",
   **Então** nasce uma nota a emitir (hoje não nasce — é o cenário que deve falhar no código antigo).
3. **Dado** um evento sem nota, **Quando** a vendedora liga o chip pelo card Comercial do evento,
   **Então** nasce uma nota a emitir.
4. **Dado** um evento que já tem nota (a emitir ou emitida), **Quando** a venda é salva de novo com
   o chip ligado, **Então** nenhuma nota a mais é criada e nenhum e-mail novo sai.

---

### História 2 — A vendedora informa o que a nota precisa ter (Prioridade: P1)

Ao ligar o chip, abrem-se os dados da nota: **CNPJ ou CPF do tomador** (em branco, vale o do
cadastro do cliente contratante), **ISS retido pelo tomador** (sim/não), **município de
prestação** (só quando o ISS é retido), **referência do cliente** (AF, pedido de compra — opcional)
e **observações para a nota** (texto livre: o que o cliente pediu por WhatsApp). Os dados valem para
a venda inteira e podem ser corrigidos depois, nas mesmas portas.

**Por que esta prioridade**: é o que hoje chega por WhatsApp e se perde; sem isso o Superadmin
continua tendo de perguntar antes de emitir.

**Verificação**: cenários 5–6 do `verify_323.py`.

**Cenários de aceite**:

1. **Dado** um cliente contratante com CNPJ no cadastro, **Quando** a vendedora liga o chip e deixa
   o documento em branco, **Então** a tarefa e o e-mail usam o CNPJ do cadastro (e a tela o mostra
   como sugestão).
2. **Dado** o chip ligado, **Quando** a vendedora informa ISS retido + município + referência +
   observações e salva, **Então** os dados ficam gravados na venda e aparecem na tarefa e no e-mail.
3. **Dado** ISS retido marcado sem município, **Quando** a vendedora salva, **Então** o sistema
   recusa e aponta o campo município.

---

### História 3 — O Superadmin vê a tarefa urgente na tela inicial e emite sem perguntar nada (Prioridade: P1)

Na tela inicial, o Superadmin vê o painel **Notas a emitir**, com cada nota pedida marcada como
**urgente**: valor, tomador (razão social e CNPJ), evento e data, quem pediu e há quanto tempo, ISS
retido e município quando houver, e a **discriminação pronta** com um botão de copiar. Ele emite no
site da prefeitura, volta e **insere o PDF da nota** ali mesmo; a nota passa a emitida e sai da lista.

**Por que esta prioridade**: é a tarefa que o dono pediu; o card do Financeiro existe, mas não é a
tela que ele abre todo dia.

**Verificação**: cenários 7–9 do `verify_323.py`.

**Cenários de aceite**:

1. **Dado** uma nota a emitir, **Quando** o Superadmin abre a tela inicial, **Então** ela aparece no
   painel Notas a emitir, contada como urgente no resumo do topo.
2. **Dado** a nota na lista, **Quando** ele copia a discriminação, **Então** o texto traz: a
   referência do cliente (se houver), o que é o evento com a data, o vencimento (se houver), os dados
   bancários e as observações.
3. **Dado** a nota na lista, **Quando** ele insere o PDF, **Então** a nota fica emitida, com o
   arquivo, e sai do painel.
4. **Dado** um usuário que não é Superadmin (Comercial, Financeiro), **Quando** abre a tela inicial,
   **Então** não recebe o painel (deve falhar se o bloco vazar).

---

### História 4 — O e-mail diz no assunto o que é preciso fazer (Prioridade: P2)

Quando a nota é pedida, cada Superadmin recebe um e-mail no formato do aviso de gasto extra (319):
**assunto** `Nota R$ 2.127,98 · Esporte Clube Sírio · pedida por Thaís`; **prévia** com evento e
data, ISS retido/município quando houver e vencimento; **corpo** com os dados do tomador, valor,
ISS, referência, observações, a discriminação e o botão para a tela inicial.

**Por que esta prioridade**: o painel já resolve o fluxo; o e-mail é o alarme no celular.

**Verificação**: cenários 10–11 do `verify_323.py` (envio trocado por coletor — nada sai).

**Cenários de aceite**:

1. **Dado** uma nota pedida, **Quando** o pedido é salvo, **Então** sai um e-mail por Superadmin com
   e-mail cadastrado, com o assunto no formato acima.
2. **Dado** uma nota que já teve o aviso enviado, **Quando** a venda é salva de novo, **Então**
   nenhum e-mail novo sai.
3. **Dado** um pedido de nota, **Quando** o envio do e-mail falha, **Então** a venda e a nota ficam
   gravadas mesmo assim (o aviso é depois do fato).

---

### Casos de borda

- **Venda sem valor ("a definir")**: a nota nasce sem valor; o assunto diz `Nota (valor a definir) ·
  …`; a discriminação sai sem valor e o Superadmin vê "Valor a definir" no painel.
- **Cliente sem CNPJ no cadastro**: o campo vem vazio; salvar sem CNPJ é permitido (o cliente pode
  mandar depois), e o painel e o e-mail mostram "CNPJ não informado" em destaque.
- **CNPJ digitado pela vendedora e cliente sem CNPJ no cadastro**: o CNPJ entra também no cadastro
  do cliente (preenche só campo vazio, nunca sobrescreve — regra da base de clientes, 119).
- **Desligar o chip**: as notas **a emitir** somem (e a tarefa com elas); nota já **emitida** não é
  apagada por desligar o chip. Vale só na transição ligado → desligado: venda que nunca teve o chip
  pode ter nota lançada à mão pelo Financeiro, e salvar a venda não a apaga. *(converge, 28/10)*
- **Várias notas na mesma venda** (069): cada nota a emitir é uma tarefa com o valor dela; a
  discriminação e os dados do tomador são os da venda (o mesmo texto em todas — o Superadmin ajusta
  no site da prefeitura quando uma parcela pede outro vencimento). *(converge, 28/10)*
- **Evento cancelado**: não recebe pedido novo (a tela do cancelado só se consulta, 312); nota a
  emitir que já existia continua na lista com o selo de cancelado, como no card do Financeiro (306).
- **Evento agrupado** (satélite): a nota é da venda do principal, como hoje.
- **Nenhum Superadmin com e-mail**: o pedido grava e a tarefa aparece; nenhum e-mail sai, sem erro.
- **Clique duplo ao salvar**: no máximo uma nota a emitir nasce por ligar o chip.
- **Desligar e religar**: a nota a emitir excluída ao desligar volta como pedido novo ao religar
  (nova tarefa, novo aviso) — é um pedido novo da vendedora.
- **Valor da venda alterado depois do pedido**: enquanto a nota pedida estiver a emitir e for a
  única da venda, o valor dela acompanha a venda (sem novo aviso). Com várias notas, cada uma fica
  com o valor que tem (069).
- **Tela aberta antes do deploy**: a gravação que chega sem os dados da nota não apaga os dados já
  gravados.

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: Ligar "Precisa de nota fiscal" numa venda que ainda não tem nenhuma nota DEVE criar
  uma nota a emitir com o valor da venda, em todas as portas de escrita da venda: criação do evento,
  "Editar tudo" e card Comercial do evento.
- **FR-002**: A nota a emitir DEVE guardar quem pediu (o usuário que ligou o chip) e quando.
- **FR-003**: Venda que já tem nota (qualquer situação) NÃO DEVE ganhar nota nova ao ser salva com o
  chip ligado.
- **FR-004**: A venda com nota DEVE guardar os dados da nota: CNPJ do tomador, ISS retido pelo
  tomador (sim/não), município de prestação, referência do cliente e observações para a nota.
- **FR-005**: O campo "CNPJ ou CPF do tomador" em branco DEVE valer o documento do cadastro do
  cliente contratante (CNPJ; sem CNPJ, CPF) no painel, no e-mail e na discriminação, e a tela DEVE
  mostrar esse documento como sugestão quando o conhece; documento informado pela vendedora DEVE
  completar o cadastro do cliente só se o campo estiver vazio. Documento informado tem 14 dígitos
  (CNPJ) ou 11 (CPF).
- **FR-006**: ISS retido marcado DEVE exigir o município de prestação; a recusa aponta o campo.
- **FR-007**: A tela inicial do Superadmin DEVE ter o painel "Notas a emitir" com todas as notas a
  emitir, todas contadas como urgentes no resumo do topo, cada uma com: valor, tomador (razão social
  e CNPJ, e-mail e endereço quando houver), evento e data, quem pediu e quando, ISS retido e
  município, referência, observações e a discriminação.
- **FR-008**: O sistema DEVE montar a discriminação de cada nota, nesta ordem: referência do cliente
  (se houver); o que é o evento e a data; "Vencimento: dd/mm" (se a venda tiver data de recebimento);
  os dados bancários da empresa; as observações (se houver).
- **FR-009**: Os dados bancários da discriminação DEVEM ter default real no código (Inter 077, Prime
  Dreams Eventos Ltda, CNPJ 60.708.296/0001-21 (PIX), agência 0001, conta 44689668-3); configuração
  só sobrepõe (Princípio XIV).
- **FR-010**: O Superadmin DEVE poder copiar a discriminação e inserir o PDF da nota direto do painel;
  inserir o PDF marca a nota como emitida e a tira do painel.
- **FR-011**: Ao nascer uma nota a emitir por pedido (FR-001), cada Superadmin com e-mail DEVE
  receber um aviso, uma única vez por nota, depois de a venda estar gravada; falha no envio não
  desfaz a venda.
- **FR-012**: O assunto do aviso DEVE ser `Nota <valor> · <tomador> · pedida por <primeiro nome>`
  (tomador cortado com "…"; sem valor → "Nota (valor a definir) · …"); a prévia leva evento e data,
  ISS retido/município e vencimento; o corpo leva os dados do FR-007, a discriminação e o botão para
  a tela inicial.
- **FR-013**: Desligar o chip DEVE excluir as notas a emitir da venda e NÃO DEVE apagar nota emitida.
- **FR-014**: O painel e o aviso NÃO DEVEM chegar a quem não é Superadmin; o "Ver como" do
  Superadmin segue a regra da tela inicial (o painel some ao simular outro papel).
- **FR-015**: O envio do aviso DEVE respeitar as travas de e-mail locais (`_emails_enabled` e o
  bloqueio de link local da 269b, que é o que o `_send` aplica).
- **FR-016**: Enquanto a nota a emitir for a única da venda, o valor dela DEVE acompanhar o valor da
  venda a cada gravação, sem novo aviso.
- **FR-017**: Gravação da venda sem os dados da nota no corpo NÃO DEVE alterar os dados gravados.

### Entidades

- **Venda do evento (`CalendarEvent`)**: ganha os dados da nota — CNPJ do tomador, ISS retido (sim/
  não), município de prestação, referência do cliente, observações para a nota. São da venda, não de
  cada nota: o cliente pede uma vez.
- **Nota fiscal (`EventInvoice`, 069)**: ganha quem pediu, quando pediu e quando o aviso saiu (o que
  impede o segundo e-mail).
- **Cliente (`Client`)**: sem mudança de estrutura; o CNPJ pode ser completado (FR-005).

### RBAC

- Leitura do painel: bloco novo no `GET /api/dashboard` (ou equivalente da tela inicial) — só
  Superadmin real, sem "Ver como" (FR-014).
- Escrita dos dados da nota: entra nas portas que já gravam a venda (`POST /api/events`,
  `PATCH /api/events/<id>`, `PATCH /api/events/<id>/comercial`) com o gate de hoje de cada uma.
- Inserir o PDF: porta que já existe (`PATCH /api/events/<id>/invoices/<id>`) com o gate de hoje; a
  tela só oferece o botão ao Superadmin.
- Linha na tabela de `docs/01` §4.3 para o que mudar.

## Verificação (`verify_323.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/323-nota-pedida-ao-superadmin/verify_323.py`, contra `manto_local` (`DATABASE_URL`
de `.local-db-url`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`). Login só por
`POST /api/auth/login`; escrita conferida por conexão separada; envio de e-mail trocado por coletor;
limpeza no `finally`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | criar evento com nota | nota a emitir nasce com valor, "pedida por" e data | não |
| 2 | ligar o chip no "Editar tudo" | nota a emitir nasce (furo da edição) | **sim** no código antigo |
| 3 | ligar o chip no card Comercial | nota a emitir nasce | **sim** no código antigo |
| 4 | salvar de novo com o chip ligado | nenhuma nota nova, nenhum e-mail novo | não |
| 5 | dados da nota gravados e CNPJ do cliente completado só se vazio | FR-004/005 | não |
| 6 | ISS retido sem município | 400 com `fields.municipio` | não |
| 7 | painel do Superadmin | nota listada, urgente, com discriminação na ordem do FR-008 | não |
| 8 | Comercial e Financeiro abrem a tela inicial | sem o painel | **sim** se vazar |
| 9 | inserir PDF pela porta existente | nota emitida, fora do painel | não |
| 10 | e-mail do pedido | um por Superadmin com e-mail, assunto no formato do FR-012 | não |
| 11 | desligar o chip | a emitir excluída, emitida preservada | não |
| 12 | valor da venda muda; corpo sem `nota` | nota única a emitir acompanha o valor, sem e-mail novo; dados da nota intactos | não |
| 13 | "Editar tudo" que troca o contratante | documento completa o cliente novo, não o antigo | **sim** antes do converge |
| 14 | venda sem chip com nota lançada à mão | salvar a venda não apaga a nota | **sim** antes do converge |
| 15 | limpeza | eventos, notas e usuários descartáveis apagados (`roles.clear()` antes do usuário) | — |

Conferência de tela: formulário de criação, "Editar tudo" e card Comercial (dados da nota abrindo com
o chip), tela inicial do Superadmin (painel, copiar, inserir PDF), em desktop e em 375×812 (o dono
usa o celular).

## Critérios de sucesso *(obrigatório)*

- **SC-001**: 100% das vendas marcadas "com nota", em qualquer porta, geram uma tarefa de emissão
  (hoje a edição perde todas).
- **SC-002**: o Superadmin emite a nota sem precisar perguntar nada à vendedora quando ela preencheu
  os dados — tomador, valor, ISS e discriminação estão na tarefa.
- **SC-003**: pelo assunto do e-mail, sem abrir, o Superadmin sabe valor, cliente e quem pediu.
- **SC-004**: nenhuma venda gera dois avisos para a mesma nota.

## Fora de escopo

- Emitir a NFS-e automaticamente na prefeitura (integração com o sistema da prefeitura).
- Aviso no sininho de notificações e por WhatsApp.
- Dados de tomador diferentes por nota quando a venda tem várias notas.
- Editar os dados bancários por tela (ficam no código, com sobreposição por configuração).
- Lembrete repetido de nota parada (o painel já mostra há quanto tempo foi pedida).

## Docs a atualizar

`docs/01` (colunas novas, bloco do dashboard, campos nas portas da venda, §4.3), `docs/02` (tela
inicial — painel Notas a emitir; formulário da venda — dados da nota), `docs/03` (entrada no topo),
`docs/04` §Financeiro/Agenda (invariante: chip ligado ⇒ uma nota a emitir; desligar não apaga
emitida).

## Premissas

- "Urgente" = toda nota a emitir é urgente: o pedido existe para ser atendido logo, e a data do
  evento não diz quando a cliente precisa da nota.
- "Pedida por" é quem ligou o chip; quando a nota é do legado (sem esse registro), o painel mostra o
  vendedor da venda.
- O vencimento da discriminação vem da data de recebimento da venda (parcelas, quando houver; a
  primeira parcela a receber); sem data, a linha não entra.
- O texto "o que é o evento" segue as notas do dono, não o título do Google (que traz "(TIPO)" e os
  personagens): "Personagens para evento dd/mm"; no EducaManto, "Apresentações Educamanto — dd/mm".
  O Superadmin edita no site da prefeitura se quiser outro texto (research R6).
- O município é texto livre ("Jundiaí - SP"): o sistema não tem lista de municípios.
- Os dados do tomador além do CNPJ (razão social, endereço, e-mail) vêm do cadastro do cliente
  contratante e não são editados nesta feature.
