# Feature 312 — O cancelado sai de toda lista e só se vê onde se trata do cancelamento

**Branch**: `312-cancelado-fora-das-listas` (da `main` em `5c298ac5`) · **Created**: 2026-10-20 · **Status**:
Rascunho · **Migration**: nenhuma · **Nível**: 1 (feature) — mais de um domínio (agenda, comercial, financeiro,
fichas, formulários, figurino, 3D, casting, portal e a página pública de avaliação), gate de papel novo na
página de Cancelamentos, campos novos em contratos de leitura — constituição, Princípio VI

**Input**: pedido do dono: "pode começar a 1c" (20/10/2026) — item **1c** do backlog de setembro, terceira
entrega da 303 (D34). Fonte completa e revisada: `docs/backlog/1c-sinalizar-e-filtrar-cancelados.md` (checkout
principal, untracked; seções 1–11, doze dúvidas respondidas pelo dono em cinco rodadas, nenhuma aberta),
reconferida contra a `main` de 20/10 em `pesquisa/reconferencia-2026-10-20.md`. Autorização do dono para esta
esteira: "das coisas já definidas por perguntas pode ir seguindo até implementação" (20/10).

## O pedido, nas palavras do dono *(obrigatório)*

29/09, depois do clarify da 303:

> "Precisamos incluir no plano essa questão do evento cancelado e com 600 devolvido aparecendo como −600, sendo
> que ele é +400. E acredito que possa ter algo especial para sinalizar e/ou filtrar eventos cancelados."

O "+400" já subiu com a 306 (o retido entra na DRE e no Total vendido do mês do cancelamento). Esta entrega é a
outra metade, que o dono reescreveu em 06/10:

> "Evento cancelado não deve ficar mostrando para o talento. Ver esses eventos cancelados deve ser uma função
> apenas de uma parte específica do sistema, para filtrar cancelados e ver o que houve. Não deve ser algo que
> fica poluindo o calendário e outras coisas."

O sintoma que a equipe vê hoje em produção (20/10):
- o "(R&I) TIMAO + PUMBA", cancelado de manhã, aparece na visão **Dia** da agenda e na **busca** como um evento
  normal;
- a tela dele mostra o **motivo** do cancelamento a todo usuário interno, inclusive Casting, Figurino e Ensaio —
  foi o que levou a Superadmin a pedir "cancelar o cancelamento — nao eram pras pessoas verem o motivo";
- a tela dele ainda deixa escalar artista (e manda convite por e-mail), agendar ensaio, ligar formulário, gerar
  link de avaliação e mexer em logística;
- o Casting não tem na Home a lista de quem precisa ser tirado da escala e avisado;
- a página de Cancelamentos é só do Superadmin e não filtra por mês;
- nenhuma tela mostra o card "Cancelamentos do período".

## Clarifications

### Decisões do dono (palavras dele; não se reabrem)

Todas registradas no plano 1c, seção 7, linha "Resposta do dono". Q = dúvida do plano 1c.

- **D31, reescrita em 06/10 e 13/10** — o cancelado deixa de aparecer, em vez de aparecer sinalizado; o card
  "Cancelamentos do período" fica; o botão "Mostrar cancelados" não existe em tela nenhuma.
- **Q1 = B** ("b", 06/10) — no card do Dashboard Comercial, a vendedora vê só os números da venda dela
  (quantidade, pago, devolvido e o que falta devolver, retido, comissão do retido e BV); **imposto e efeito no
  resultado só para Superadmin e Financeiro**.
- **Q2 = B** ("B, porém um evento cancelado não deve ficar aparecendo no sistema poluindo as escolhas; isso é mais
  quando já tiver coisas associadas a um evento que é cancelado.", 06/10) — o cancelado sai da Fila de Impressão
  3D e das pendências de presente; "Agendar ensaio", "Vincular presente 3D" e o formulário de pré-contrato
  recusam o cancelado; e **nenhuma lista de escolha o oferece**.
- **Q3 = C** ("O ensaio também é cancelado. E avisa não só a pessoa responsável por marcar o ensaio no sistema
  como também os artistas já escalados.", 06/10) — **já em produção pela 306**; aqui só se recusa marcar ou
  vincular ensaio a cancelado.
- **Q4 = A, e o histórico também** (a citação acima, 06/10) — a ficha do talento não conta nem lista o cancelado
  (Eventos, Personagens, Total faturado, Último evento e o histórico).
- **Q5 = B** ("b, mesmo", 06/10) — o cancelado recusa escalar ou convidar artista, gerar link de avaliação (o
  link antigo diz à cliente que o evento foi cancelado) e pedido de figurino novo, com o motivo.
- **Q6 = A** ("Não deve ser mostrado na agenda.", 13/10) — sem botão "Mostrar cancelados" em lugar nenhum.
- **Q7 = A, com os dados de venda editáveis** ("Acredito que dados de venda ainda devam poder ser editados,
  porque podemos alterar valores e inserir pagamentos de multas, mas de resto melhor não dar para mexer.", 13/10)
  — a tela do cancelado fica só para consulta, menos os dados de venda.
- **Q8 = A** ("Superadmin apenas.", 13/10) — só o Superadmin mexe nos dados de venda do cancelado (**já em
  produção pela 306**).
- **Q9 = A** ("Apenas para os comercial, financeiro e admin mesmo.", 13/10) — o motivo e o autor do cancelamento
  só para Comercial, Financeiro e Superadmin; os outros veem "Evento cancelado em DD/MM".
- **Q10, fluxo novo** ("Quando cancelado, pede para o casting excluir e avisar por WhatsApp para a pessoa que o
  evento foi cancelado.", 13/10) — o sino ao Casting já subiu com a 306; aqui entram a pendência na Home do
  Casting e a regra de que, no cancelado, quem tira da escala é o Casting (e o Superadmin).
- **Q11 = C** ("Pode mexer sim.", 13/10) — vendedor, acréscimos e reembolsos são dados de venda do cancelado
  (**já em produção pela 306**).
- **Q12 = A** ("Não. Se ele já recebeu o e-mail automático de cancelamento, não precisa do e-mail 'sua
  participação foi cancelada'.", 13/10) — **já em produção pela 306**; aqui só se confere.
- **20/10 (306b)** — "Faça com que o motivo do cancelamento seja editável por superadmin e comercial": a rota do
  motivo fica fora da trava da tela.

### Session 2026-10-20 (`/speckit-specify`) — leituras fixadas por esta spec, não palavras do dono

Cada uma vale como premissa; o dono pode contestar.

1. **Ficha da cliente** — a 306 deixou o cancelado na lista da ficha, marcado (P-43 dela). Esta spec segue o
   plano 1c: a lista não traz o cancelado, e o total, que já soma o retido, ganha a sublinha "inclui R$ X retidos
   de N cancelamento(s)". Leitura da Q4 ("não deve ser algo que fica poluindo o calendário e outras coisas").
2. **Q9 × 306b** — a spec da 306b escreveu que "Financeiro e os demais veem o motivo" e pôs o sigilo fora de
   escopo; a Q9, anterior e não revogada, manda esconder dos outros papéis. Vale a Q9. O botão "Editar motivo" da
   306b continua para Superadmin e Comercial.
3. **Trava × rotas com regra própria** — a trava não alcança as rotas que a 306 e a 306b gateiam por regra
   própria: os dados de venda (`pode_editar_venda_do_cancelado`) e o motivo (`pode_editar_motivo_do_cancelado`).
   Toda outra escrita na tela de um evento cancelado cai na trava, inclusive rota que nascer depois.
4. **Jinja** — no cancelado, a tela Jinja do evento recusa **todas** as ações, inclusive as de venda (a 306 já
   recusa essas até ao Superadmin); as correções de venda do cancelado são pela tela React.
5. **Vocabulário** — o que esta entrega cria usa `situacao`/`event_situacao`. Os booleanos que a 306 criou ficam
   onde são lista de dinheiro dela (`event_cancelled` dos gastos, `cancelado` da nota fiscal, o
   `payment_status` "cancelado" do painel). Os dois que mostram o cancelado como item de lista
   (`group.satellites[].cancelado` no principal vivo e `events[].cancelado` da ficha da cliente) saem com o item.
6. **Nomes do card** — o bloco do Dashboard Comercial usa os mesmos nomes do `paineis.cancelamentos` que a 306
   já manda na DRE (`devolucao_a_pagar`, `bv_retido`), não os do plano (`falta_devolver`, `bv`): um vocabulário
   para o mesmo número nas duas telas.
7. **`devolucao` legado da página** — o objeto único que a 306 manteve "por um ciclo" sai; o `resumo` com todas
   as devoluções fica. O bundle da 306 só o lê como reserva quando falta o `resumo`
   (`EventosCancelamentosPage.tsx:148-149`, `:229`), então tirá-lo não quebra a tela velha na janela do deploy.
8. **Cancelado pela regra velha** — o 1358 (SHOW de 17/10, cancelado em 02/10, antes da 306) existe em produção.
   A página, o card e a tela dele mostram o que houver; número que o resumo não sabe montar sai vazio, nunca
   derruba a lista.
9. **`/speckit-clarify` (20/10)** — nenhuma ambiguidade crítica: as doze dúvidas têm resposta do dono e as
   leituras acima não mudam regra de negócio. Nenhuma pergunta nova.

## Cenários e Verificação *(obrigatório)*

Semente comum: o "exemplo-padrão" do `verify_306.py` — venda R$ 2.000, pago R$ 1.000, devolução de R$ 600,
retido R$ 400, comissão do retido R$ 18, BV do retido R$ 40 —, cancelado pelo endpoint da 306, com dois talentos
descartáveis escalados (um aceito, um pendente), um terceiro que recusou e a vaga de presença; usuários
descartáveis de papel único (COMERCIAL, FINANCEIRO, CASTING, FIGURINO, ENSAIO, REVENDEDOR_EDUCAMANTO) e um
Superadmin. Todo cenário de leitura procura o cancelado pelo id e pelo título único e tem um **controle vivo** na
mesma consulta.

### História 1 — O cancelado some de toda lista (Prioridade: P1)

Quem abre a agenda (Dia, Mês, Lista — não há visão Semana), a busca, as fichas, as listas de escolha e as filas de trabalho não
vê mais o evento cancelado. A equipe deixa de ver "TIMAO + PUMBA" no Dia de 22/10 e na busca; a ficha do talento
deixa de contar o cachê de um show que não aconteceu; o seletor de evento do ensaio, da tag NFC, do grupo, do
Gasto Extra, do pedido de figurino e do formulário não oferece mais o cancelado.

**Por que esta prioridade**: é o centro do pedido ("não deve ser algo que fica poluindo o calendário e outras
coisas") e o defeito que a equipe vê hoje.

**Verificação**: cenários 1–7 do `verify_312.py`.

**Cenários de aceite**:

1. **Dado** um cancelado e um evento vivo de controle no mesmo dia, **Quando** alguém abre o Dia (React e Jinja),
   o Mês e a busca pelo título, **Então** o cancelado não vem e o vivo vem; `incluir_cancelados=1` é ignorado.
2. **Dado** um evento marcado pela 303 e um com pedido de exclusão, **Quando** a agenda abre, **Então** os dois
   continuam aparecendo com o selo deles (o filtro olha só o cancelamento).
3. **Dado** o talento escalado no cancelado, **Quando** a ficha dele abre, **Então** o cancelado não está no
   histórico e não conta em Eventos, Personagens, Total faturado nem Último evento.
4. **Dado** a cliente do cancelado, **Quando** a ficha abre, **Então** a lista e a contagem de eventos não o
   trazem, o total vendido inclui o retido (306) e a ficha diz quantos cancelamentos e quanto retido isso é.
5. **Dado** o cancelado, **Quando** se procura evento no vínculo de ensaio, na tag NFC, nos candidatos do grupo,
   no seletor por data de Gastos Extras, do pedido de figurino e da associação de formulário, e nos candidatos
   automáticos do formulário, **Então** ele não vem; o controle vivo vem.
6. **Dado** um show cancelado sem presente 3D, **Quando** a Fila de Impressão 3D e as pendências de presente
   abrem, **Então** ele não está; o presente já vinculado continua no evento.
7. **Dado** um talento escalado no cancelado, **Quando** ele é escalado noutro evento no mesmo horário (API e
   Jinja), **Então** não aparece aviso de conflito por causa do cancelado; com evento vivo o aviso vem.
8. **Dado** um principal vivo com um dia cancelado, **Quando** a aba Comercial abre, **Então** o painel "Grupo
   comercial" não lista o dia cancelado (que continua no grupo, no banco) e o rótulo "(N eventos)" da lista de
   vendas e da DRE conta só os dias vivos.
9. **Dado** um ensaio legado cancelado sozinho (estado anterior à 306), **Quando** a tela do show e a Home da
   equipe de Ensaio abrem, **Então** ele não conta como ensaio nem como "agendado".

---

### História 2 — A tela do cancelado fica só para consulta, e o motivo só para quem trata dele (Prioridade: P1)

Quem abre a tela de um evento cancelado — pela página de Cancelamentos, pelo card, pelo sino ou por link — vê o
que aconteceu e não consegue mudar nada, menos os dados de venda (pelo Superadmin, como já é desde a 306) e o
motivo (Superadmin e Comercial, desde a 306b). Casting, Figurino e Ensaio veem "Evento cancelado em DD/MM", sem o
motivo nem quem cancelou. Escalar, convidar, agendar ensaio, ligar presente 3D, tag NFC ou formulário, gerar
link de avaliação e abrir pedido de figurino são recusados no servidor com o motivo, mesmo de uma aba aberta
antes do cancelamento.

**Por que esta prioridade**: hoje a tela do cancelado ainda manda convite por e-mail a quem for escalado e mostra
o motivo a todos — é o incidente de 20/10.

**Verificação**: cenários 8–14 do `verify_312.py`.

**Cenários de aceite**:

1. **Dado** o cancelado, **Quando** Casting ou Figurino abrem a tela, **Então** recebem `cancelled_at` e não
   recebem motivo nem autor; Comercial, Financeiro e Superadmin recebem os dois; Superadmin com "Ver como"
   Casting não recebe.
2. **Dado** o cancelado, **Quando** qualquer papel (inclusive o Superadmin) tenta logística, observações, dados
   básicos, clientes, contratos, confirmar, transporte, figurino da vaga, status do cachê, remover vaga, renomear
   grupo, presença, materiais, estimativa de deslocamento ou a edição completa, **Então** recebe 409 com o código
   `cancelado` e a frase "Este evento foi cancelado — a tela fica só para consulta.", e nada é gravado.
3. **Dado** o cancelado, **Quando** o Superadmin corrige um dado de venda (venda, nota, comprovante, acréscimo,
   reembolso, devolução, multa ao elenco) ou o Comercial edita o motivo, **Então** passa como hoje — a trava não
   alcança essas portas.
4. **Dado** o cancelado, **Quando** alguém escala, adiciona vaga com talento ou convida, **Então** recebe 409
   `cancelado`, nenhum e-mail sai e a escala no banco fica igual.
5. **Dado** o cancelado, **Quando** alguém agenda ensaio (API e Jinja), vincula ensaio, vincula presente 3D novo,
   liga tag NFC nova, liga formulário (painel, `/formularios` ou edição em bloco), gera link de avaliação ou abre
   pedido de figurino com ele, **Então** é recusado com o motivo e nada é gravado (nem no Google); desligar o
   formulário, soltar a tag ou o presente e reenviar o mesmo vínculo continuam passando.
6. **Dado** o link de avaliação enviado antes do cancelamento, **Quando** a cliente o abre, **Então** a página
   diz que o evento foi cancelado e não aceita nota.
7. **Dado** o cancelado, **Quando** a tela abre, **Então** as flags dizem "somente consulta" e os botões que
   gravam não aparecem; os painéis de venda aparecem editáveis só para o Superadmin e, para os outros, com a
   frase "Evento cancelado: só o Superadmin altera os dados de venda."; a caixa vermelha diz onde o cancelado
   está agora e o que se faz ali.
8. **Dado** a tela Jinja do evento cancelado, **Quando** qualquer ação é enviada, **Então** volta com o motivo e
   nada é gravado; "Imprimir fichas" também recusa.
9. **Dado** um evento com pedido de cancelamento pendente, **Quando** as mesmas ações são feitas, **Então**
   passam como num vivo (o pedido não trava nada).

---

### História 3 — O Casting tira os escalados do cancelado e avisa cada um pelo WhatsApp (Prioridade: P2)

Cancelado o evento, o Casting recebe o sino (já em produção) e passa a ter na Home o bloco "Eventos cancelados —
excluir e avisar", artista por artista, com "Avisar no WhatsApp" (mensagem pronta) e "Tirar da escala". A linha
some quando o artista sai da escala; o bloco some com a escala vazia; o sino daquele dia fica lido. No
cancelado, só Casting e Superadmin tiram alguém da escala, e tirar não manda o segundo e-mail.

**Por que esta prioridade**: o pedido do dono ao Casting existe hoje só como um sino; sem a lista, o Casting
depende de abrir evento por evento.

**Verificação**: cenário 15 do `verify_312.py`.

**Cenários de aceite**:

1. **Dado** o cancelado com dois escalados, um que recusou e a vaga de presença, **Quando** o Casting abre a
   Home, **Então** vê os dois escalados (não quem recusou, não a presença), cada um com o WhatsApp e "Tirar da
   escala"; um escalado de evento vivo na mesma data não entra no bloco.
2. **Dado** o cancelado, **Quando** Figurino ou Comercial tentam tirar alguém da escala, **Então** recebem 403
   com "Evento cancelado: quem tira da escala é o Casting."; **Quando** o Casting tira, **Então** a vaga fica
   vazia, a linha sai da pendência e nenhum e-mail de remoção sai.
3. **Dado** o cancelado, **Quando** alguém tenta pôr talento, cachê ou transporte numa vaga dele, **Então**
   recebe 409 `cancelado`.
4. **Dado** que o último escalado a avisar saiu, **Quando** o Casting olha o sino, **Então** o aviso daquele dia
   está lido para todos.

---

### História 4 — A página de Cancelamentos para o Superadmin e o Financeiro, com filtros (Prioridade: P2)

A página de Cancelamentos vira "a parte específica" do sistema: abre para Superadmin e Financeiro (menu nas duas
seções), filtra por mês do cancelamento e pela situação da devolução (não paga, no banco, paga, sem devolução),
busca por título ou motivo, e mostra por evento a venda, o pago, cada devolução com o seu estado, o retido, a
comissão e o BV do retido e o imposto, com o total retido no cabeçalho. Mostra também o dia cortado de uma venda
de vários dias.

**Por que esta prioridade**: hoje ela é só do Superadmin, lista os 200 mais recentes sem filtro e põe pago e
retido como texto dentro da coluna Devolução.

**Verificação**: cenários 16–17 do `verify_312.py`.

**Cenários de aceite**:

1. **Dado** o cancelado do exemplo, **Quando** o Financeiro abre a página, **Então** vê a linha com pago 1.000,
   uma devolução não paga de 600, retido 400, comissão 18, BV 40, e o total retido 400; a fila "Aguardando
   exclusão" também.
2. **Dado** o filtro do mês do cancelamento, **Quando** aplicado, **Então** o cancelado vem; no mês seguinte,
   não; sem mês, vêm os 200 mais recentes e o total diz "nos N listados".
3. **Dado** um evento com uma devolução paga e outra não paga, **Quando** se filtra por "paga" e por "não paga",
   **Então** ele aparece uma vez em cada e o total não dobra; o cancelado sem devolução só aparece em "sem".
4. **Dado** `mes` ou `devolucao` inválidos, **Quando** a página é chamada, **Então** responde 400 apontando o
   campo, e a tela volta ao padrão.
5. **Dado** Comercial, Figurino, Casting ou revendedor EducaManto, **Quando** chamam a página, **Então** 403;
   anônimo, 401; o Financeiro continua sem poder alterar devolução.
6. **Dado** o 1358 (cancelado pela regra velha), **Quando** a página abre, **Então** a linha dele aparece com o
   que houver, sem derrubar a lista.

---

### História 5 — O card "Cancelamentos do período" no Dashboard Comercial e na DRE (Prioridade: P2)

Acima da lista de vendas e acima de "Eventos no período" da DRE aparece, quando houver cancelado no mês, o card
com os números do mês do cancelamento e a lista dos cancelados, cada um com o retido, o devolvido e a comissão do
retido e o link para a tela dele. A vendedora vê só os dela e seis números; Superadmin e Financeiro veem oito
(com imposto e efeito no resultado). Quem abre a página de Cancelamentos tem "Ver na página de Cancelamentos" já
filtrada no mês. O número retido do card é o mesmo da linha "Retido de cancelamentos" da DRE e do KPI do
Comercial.

**Por que esta prioridade**: é por aqui que a vendedora acha o próprio cancelado, agora que a busca não o traz; e
é o que explica a diferença entre a soma da tabela e a Receita Bruta.

**Verificação**: cenários 18–19 do `verify_312.py`.

**Cenários de aceite**:

1. **Dado** o mês do cancelamento, **Quando** a vendedora dona da venda abre o Dashboard Comercial, **Então** o
   card traz quantidade 1, retido 400, comissão do retido 18 (pela mesma regra do KPI), BV 40, pago e devolvido,
   sem imposto nem efeito no resultado, e o link do evento; o retido do card é igual ao do KPI.
2. **Dado** o mesmo mês, **Quando** Superadmin ou Financeiro abrem, **Então** veem também imposto e efeito no
   resultado; outra vendedora não vê o cancelado de quem não é dela.
3. **Dado** o mês original do evento ou um mês sem cancelado, **Quando** as telas abrem, **Então** o card não
   aparece (quantidade 0) e nada mais muda.
4. **Dado** a DRE do mês do cancelamento, **Quando** abre, **Então** o card traz os oito números, cada item com
   retido, devolvido e comissão do retido, e o retido do card é o mesmo da linha "Retido de cancelamentos".
5. **Dado** um cancelado com tudo devolvido, **Quando** o card abre, **Então** ele é item com retido R$ 0,00 e
   conta na quantidade.

---

### História 6 — O que já estava ligado ao cancelado leva o selo; portal e avaliação dizem que foi cancelado (Prioridade: P3)

A coisa viva ligada a um evento cancelado — Gasto Extra, tag NFC, pedido de figurino, formulário — continua onde
aparece, com o selo "Cancelado" ao lado do nome do evento. O select do gasto ligado ao cancelado mostra o evento
atual, não "Sem evento vinculado". O artista escalado que guardou o endereço da ficha de figurino lê "Este evento
foi cancelado." em vez da ficha.

**Por que esta prioridade**: completa a regra sem mudar dinheiro nem fluxo; os volumes hoje são pequenos.

**Verificação**: cenários 20–21 do `verify_312.py`.

**Cenários de aceite**:

1. **Dado** a devolução ligada ao cancelado, **Quando** Gastos Extras abre, **Então** ela aparece com o nome do
   evento e o selo; reenviar o mesmo evento no gasto passa; ligar um gasto novo ao cancelado por chamada direta
   passa (não é recusa, só não é oferecido).
2. **Dado** uma tag, um pedido de figurino e um formulário ligados ao evento antes do cancelamento, **Quando**
   as listas deles abrem, **Então** o evento leva a situação "cancelado".
3. **Dado** o artista escalado no cancelado, **Quando** abre a ficha de figurino pelo portal, **Então** lê "Este
   evento foi cancelado." sem ficha nem título; quem não está escalado continua recebendo a recusa de hoje.

### Casos de borda

- **Cancelado no passado**: some da agenda do dia original e entra no card e na página pelo mês do cancelamento.
- **Venda de vários dias**: o dia cancelado de um principal vivo sai do painel do grupo e entra na página como
  linha própria, com "dia cortado da venda de DD/MM" (e "a venda passou para DD/MM" quando era o 1º dia); na tela
  do principal cancelado, o painel lista os dias que caíram junto.
- **Concorrência**: a recusa lê o evento na mesma requisição que grava, sem trava de linha; o vínculo feito no
  meio do cancelamento fica como coisa já ligada (selo). Quem clica depois recebe a recusa e a tela se refaz.
- **Bundle velho durante o deploy**: todo campo novo é opcional na tela; sem ele, o card some e a pendência some,
  nunca tela branca.
- **Evento que veio do Google**: nada aqui lê ou escreve no Google.
- **Pedido de cancelamento pendente**: não é cancelamento — nada desta entrega o esconde ou trava.
- **Cancelado sem venda e sem pago**: fica fora do card e da DRE e aparece só na página (regra da 306).

## Requisitos *(obrigatório)*

### Requisitos funcionais

**Listas (História 1)**

- **FR-001**: A visão Dia da agenda (API e Jinja) e a busca da agenda DEVEM deixar de trazer o evento cancelado,
  sempre, sem parâmetro que o traga de volta.
- **FR-002**: A busca DEVE filtrar o cancelado antes do limite de resultados, para que ele não ocupe vaga; por ela
  o cancelado sai do vínculo de ensaio, da tag NFC e dos candidatos do grupo.
- **FR-003**: O seletor de evento por data (Gastos Extras, pedido de figurino, associação de formulário) e os
  candidatos automáticos do formulário DEVEM deixar de oferecer o cancelado; a lista Jinja de shows candidatos
  do vínculo de ensaio também.
- **FR-004**: A ficha do talento DEVE ignorar o cancelado no histórico e nos quatro números do cabeçalho.
- **FR-005**: A ficha da cliente DEVE deixar de listar o cancelado e de contá-lo, e DEVE informar à parte a
  quantidade de cancelamentos da cliente e o retido deles, lidos do resumo da 306.
- **FR-006**: A Fila de Impressão 3D e as pendências de presente DEVEM deixar de trazer o cancelado; o presente já
  vinculado continua no evento.
- **FR-007**: O aviso de conflito de agenda do talento (API, Jinja e a disponibilidade da tela Jinja do evento)
  DEVE ignorar o cancelado.
- **FR-008**: O painel "Grupo comercial" do principal **vivo** DEVE deixar de listar o dia cancelado; o rótulo
  "(N eventos)" da lista de vendas e da DRE DEVE contar só os dias vivos. No principal cancelado, o painel
  continua listando os dias que caíram junto.
- **FR-009**: A lista de ensaios do show e as tarefas "agendado / falta agendar" da equipe de Ensaio DEVEM
  ignorar ensaio cancelado.
- **FR-010**: Nada desta entrega DEVE esconder ou travar evento marcado pela 303 ou com pedido de exclusão: todo
  filtro e toda recusa olham só o cancelamento.

**Tela do cancelado (História 2)**

- **FR-011**: Toda escrita na tela de um evento cancelado DEVE ser recusada no servidor, para todo papel, com 409,
  o código `cancelado` e a frase "Este evento foi cancelado — a tela fica só para consulta.", sem gravar nada —
  **exceto** as portas que a 306 e a 306b gateiam por regra própria (dados de venda pelo Superadmin; motivo pelo
  Superadmin e pelo Comercial) e os desfazer (desligar formulário, soltar tag NFC ou presente 3D, tirar artista
  da escala pelo Casting — FR-024).
- **FR-012**: A regra de FR-011 DEVE morar no núcleo, numa função única, e valer também para a tela Jinja do
  evento (todas as ações, inclusive as de venda), para as rotas Jinja fora do despachante que escrevem no evento
  e para "Imprimir fichas".
- **FR-013**: Escalar, adicionar vaga com talento, convidar e reenviar convite num cancelado DEVEM ser recusados
  no núcleo, antes de qualquer e-mail.
- **FR-014**: Agendar ensaio (API e Jinja) e vincular ensaio a um cancelado DEVEM ser recusados no núcleo, antes
  de qualquer escrita no Google.
- **FR-015**: Vincular presente 3D novo, ligar tag NFC a um cancelado (vínculo novo; reenviar o mesmo passa) e
  ligar formulário a um cancelado (painel do evento, `/formularios` e edição em bloco) DEVEM ser recusados no
  núcleo; desligar continua livre.
- **FR-016**: Gerar link de avaliação de um cancelado DEVE ser recusado; a página pública do link antigo DEVE
  responder que o evento foi cancelado (sem título nem data do evento) e não aceitar nota.
- **FR-017**: Abrir pedido de figurino ou trocar o evento de um pedido para um cancelado DEVE ser recusado;
  editar um pedido já ligado sem trocar o evento continua livre.
- **FR-018**: Toda recusa desta entrega DEVE levar o código `cancelado` (a constante da 306) e uma frase que diz
  o motivo.
- **FR-019**: O detalhe do evento cancelado DEVE informar "somente consulta" e desligar as permissões de editar o
  evento, os dados principais, confirmar, agrupar, mexer no 3D e pedir exclusão, mantendo à parte o que o desfazer
  precisa (soltar presente, desligar formulário); a tela DEVE esconder o que grava e mostrar só o
  desfazer, e os painéis de venda DEVEM seguir a permissão da 306, com a frase "Evento cancelado: só o Superadmin
  altera os dados de venda." para quem não pode.
- **FR-020**: O motivo e o autor do cancelamento DEVEM sair no detalhe só para Comercial, Financeiro e Superadmin
  (seguindo o "Ver como"); os outros papéis recebem os dois vazios e a caixa diz "Evento cancelado em DD/MM",
  sem linha de motivo. A tela Jinja do evento cancelado NÃO DEVE mostrar o "Log de atividades" (que traz o motivo)
  a quem não tem a flag comercial.
- **FR-021**: A caixa do cancelado DEVE dizer onde ele está agora (página de Cancelamentos e card do período) e o
  que se faz ali (só consulta; dados de venda pelo Superadmin).
- **FR-022**: Ao receber o código `cancelado`, a tela DEVE recarregar o evento e mostrar a frase do servidor onde
  a ação foi pedida.

**Casting (História 3)**

- **FR-023**: A Home do Casting (e do Superadmin) DEVE trazer, derivada da escala, a lista dos escalados de
  eventos cancelados ainda a avisar — fora a vaga de presença e quem recusou, no mesmo corte de data das outras
  tarefas —, cada um com artista, personagem, evento, data e WhatsApp; a lista some sozinha quando a escala do
  cancelado esvazia.
- **FR-024**: Num cancelado, tirar artista da vaga DEVE ser permitido só a Casting e Superadmin (os outros recebem
  403 com "Evento cancelado: quem tira da escala é o Casting."), DEVE aceitar só a remoção (talento no pedido, ou
  cachê ou transporte diferentes dos gravados → 409 `cancelado`; o mesmo valor ou vazio não conta), DEVE manter a vaga e NÃO DEVE mandar e-mail de remoção.
- **FR-025**: Quando sai o último escalado a avisar de um dia cancelado, o sino do pedido ao Casting daquele dia
  DEVE ficar lido para todos, na mesma transação.
- **FR-026**: A Home DEVE mostrar o bloco "Eventos cancelados — excluir e avisar" com "Avisar no WhatsApp"
  (mensagem pronta: "Oi, <nome>! O evento "<título>" de DD/MM, em que você faria <personagem>, foi cancelado.
  Qualquer dúvida, fale com a gente." — sem link do portal; sem WhatsApp, "sem WhatsApp no cadastro") e "Tirar da
  escala" com confirmação; a escala na tela do cancelado DEVE mostrar o mesmo para Casting e Superadmin, com a
  frase "Evento cancelado: exclua os escalados e avise cada um pelo WhatsApp." enquanto houver alguém a avisar.

**Página de Cancelamentos (História 4)**

- **FR-027**: A página de Cancelamentos DEVE abrir para Superadmin e Financeiro pelo papel real (fila de exclusão
  inclusa); os demais recebem 403. O poder de excluir e de alterar devolução NÃO DEVE mudar.
- **FR-028**: A página DEVE aceitar filtro por mês do cancelamento (horário de São Paulo; com mês, sem limite) e
  por situação da devolução (não paga, no banco, paga, sem), com o filtro de situação aplicado antes do limite;
  valor inválido → 400 apontando o campo.
- **FR-029**: A página DEVE devolver o total retido (dos eventos, nunca por devolução) e dizer se ele é do período
  ou "dos listados"; o objeto `devolucao` legado DEVE sair.
- **FR-030**: A tela DEVE mostrar os filtros na URL, a caixa Buscar (título ou motivo, sobre a lista carregada),
  as colunas Venda, Pago, Devoluções (uma linha por devolução com o estado), Retido, Comissão, BV, Imposto, o
  total no cabeçalho, o estado vazio "Nenhum cancelamento com estes filtros" com "Limpar filtros", a mensagem de
  erro do servidor e o dia cortado de uma venda de vários dias.
- **FR-031**: O item "Exclusões e cancelamentos" do menu DEVE aparecer para Superadmin e Financeiro.

**Card (História 5)**

- **FR-032**: O Dashboard Comercial DEVE receber sempre o bloco de cancelamentos do mês do cancelamento, no
  escopo de vendedor que o servidor já decide, com os mesmos números do `paineis.cancelamentos` da DRE e a lista
  dos cancelados; imposto e efeito no resultado só para Superadmin e Financeiro, pela flag (segue o "Ver como",
  como os outros números de dinheiro da tela).
- **FR-033**: A comissão do retido no card do Comercial DEVE seguir a mesma regra de beneficiário do KPI, e o
  retido do card DEVE ser o mesmo do KPI.
- **FR-034**: Os itens do `paineis.cancelamentos` da DRE DEVEM trazer também devolvido, comissão do retido, pago,
  o que falta devolver, data do evento e vendedor; os números que o painel já manda hoje NÃO DEVEM mudar
  (trocar a fonte do painel pela função única é aditivo).
- **FR-035**: O card DEVE aparecer nas duas telas só com quantidade maior que zero, com a lista e o link de cada
  evento, e "Ver na página de Cancelamentos" filtrada no mês só para quem abre a página.

**Coisas ligadas e portal (História 6)**

- **FR-036**: As listas de Gastos Extras, tags NFC, pedidos de figurino, formulários (tela de Formulários e
  histórico da ficha da cliente) DEVEM mostrar a situação do evento ligado; o selo "Cancelado" DEVE ser desenhado
  ali e nas listas de dinheiro da 306, nunca na agenda, na busca ou no painel do grupo.
- **FR-037**: Os selects de evento de Gastos Extras DEVEM mostrar o evento atual quando ele não está na lista do
  dia (com o selo, se cancelado), em vez de "Sem evento vinculado".
- **FR-038**: A ficha de figurino do portal DEVE recusar o evento cancelado, depois da checagem de escalado, com
  "Este evento foi cancelado.", e a tela DEVE mostrar a frase do servidor. Aceitar pelo portal o convite de um
  evento cancelado DEVE ser recusado com a mesma frase.
- **FR-039**: Ligar Gasto Extra a evento cancelado por chamada direta DEVE continuar permitido (a 306 liga ali a
  devolução e a multa); só não é oferecido na lista.

### Entidades

Nenhuma entidade nova nem coluna nova. Lê `CalendarEvent.cancelled_at`, `situacao`, o resumo do cancelado da 306
(`cancel_ops`), `event_cancellation_elenco` e as notificações `evento.cancelado_escala`.

### RBAC *(obrigatório — endpoints alterados)*

- `GET /api/events/cancelamentos` — SUPERADMIN ou FINANCEIRO pelo papel real (antes: só SUPERADMIN); demais 403.
- `POST /api/roles/<id>/assign` em vaga de evento cancelado — só CASTING e SUPERADMIN, e só a remoção (no vivo,
  inalterado).
- `GET /api/events/<id>` — motivo e autor do cancelamento só com a flag comercial (COMERCIAL, FINANCEIRO,
  SUPERADMIN; segue o "Ver como").
- `GET /api/vendas/pipeline` — gate inalterado; imposto e efeito no resultado do card só para SUPERADMIN e
  FINANCEIRO.
- Todas as escritas da tela do evento — gates inalterados; a trava vem depois do 404 e do 403 de cada rota.
- Linhas na tabela de `docs/01` §4.3 e o papel FINANCEIRO no `docs/00` §4 (leitura de Cancelamentos).

## Verificação (`verify_312.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/312-cancelado-fora-das-listas/verify_312.py`, contra `manto_local` (`DATABASE_URL` de
`.local-db-url`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`), no molde do `verify_306.py` (guarda de
ambiente, disjuntor de rede, login só por `POST /api/auth/login`, escrita conferida por conexão separada,
`_send_falso` como dublê de e-mail, `GoogleFalso`, `limpar()` no `finally`, prova por mutação contra a `main`).
O cancelado nasce pelo endpoint de cancelar da 306; o "marcado e cancelado" e o ensaio legado, por `UPDATE` em
conexão separada.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Agenda Dia (API e Jinja), Mês e busca com cancelado, marcado, pedido de exclusão e vivo de controle; `incluir_cancelados=1` | o cancelado não vem; marcado e pedido vêm com a situação; parâmetro ignorado | **sim** (trazer o cancelado) |
| 2 | Ficha do talento antes e depois do cancelamento | histórico e os quatro números sem o cancelado | **sim** |
| 3 | Ficha da cliente | lista e contagem sem o cancelado; `cancelamentos {quantidade 1, retido 400}`; total com o retido | **sim** |
| 4 | Seletores: busca (ensaio, NFC, `grupo/candidatos`), `gastos/eventos?date=`, candidatos automáticos do formulário | o cancelado não é oferecido; o vivo é | **sim** |
| 5 | Fila 3D e pendências de presente | o cancelado não vem; o presente vinculado fica | **sim** |
| 6 | Conflito de agenda (API, Jinja, disponibilidade do `event_detail`) | sem aviso pelo cancelado; com vivo, o aviso vem | **sim** |
| 7 | Grupo: principal vivo + dia cancelado + dia vivo; ensaio legado | o dia cancelado fora de `satellites[]`, dentro do grupo no banco; rótulo só com vivos; ensaio legado fora de `ensaios[]` e da Home | **sim** |
| 8 | Q9: detalhe como CASTING, FIGURINO, COMERCIAL, FINANCEIRO, SUPERADMIN e SA "Ver como" Casting | motivo e autor só para os três; `cancelled_at` para todos | **sim** (ler o motivo) |
| 9 | Trava: uma rota de cada linha (logística, observações, básico, clientes, contratos, confirmar, transporte, status do cachê, remover vaga, renomear grupo, presença, materiais, estimativa, edição completa) como SUPERADMIN real; Jinja (despachante, observações, materiais, ensaio) e "Imprimir fichas" | 409 `cancelado` com a frase; nada gravado (conexão separada) | **sim** |
| 10 | Portas livres: dados de venda como SUPERADMIN (venda, nota, comprovante da multa, acréscimos, reembolso, devolução, multa ao elenco) e o motivo como COMERCIAL | passam, sem a frase da trava; como COMERCIAL, a venda dá o 409 da 306 | não |
| 11 | Q5: escalar, vaga com talento, convidar, reenviar convite; `feedback-link`; `GET/POST /api/avaliar/<token>`; pedido de figurino novo e editar sem trocar | 409/410/400 conforme o vizinho; `_send_falso` sem chamada; banco igual; editar sem trocar passa | **sim** |
| 12 | Q2: agendar ensaio (API e Jinja), vincular ensaio, presente 3D, tag NFC nova (e o mesmo id), formulário (painel, `/formularios`, bloco), desligar formulário, soltar presente | recusas sem escrita nem Google; desfazer e mesmo vínculo passam | **sim** |
| 13 | Flags do detalhe do cancelado e do vivo | `somente_consulta` e as cinco flags falsas no cancelado; vivo igual à `main` | não |
| 9b | Inventário das rotas de escrita: toda rota `POST`/`PUT`/`PATCH`/`DELETE` do `url_map` que recebe id de evento, vaga, presente, observação, ensaio ou grupo está classificada como "trava" ou "livre" (lista no verify) | rota nova sem classificação faz o cenário falhar — a trava não tem furo silencioso | **sim** (rota não classificada) |
| 14 | Controle: as escritas de 9, 11 e 12 num evento com pedido de cancelamento pendente e num evento marcado pela 303 | passam como num vivo | não |
| 15 | Q10: Home do CASTING e do FIGURINO; `assign` sem talento como FIGURINO, COMERCIAL, CASTING; com talento/cachê; sino lido; e-mail de remoção; controle vivo | pendência com os dois certos; 403 dos outros; 200 e vaga vazia pelo Casting; 409 com talento; sino lido ao esvaziar; zero e-mail no cancelado e um no vivo | **sim** (403 e 409) |
| 16 | Página como FINANCEIRO: exemplo, duas devoluções, `mes`, `devolucao`, `sem`, sem `mes` (rótulo "listados"), `mes=2026-13` e `devolucao=xyz` → 400, cancelado pela regra velha | números do resumo; filtros antes do limite; total sem dobrar; legado não derruba | não |
| 17 | RBAC da página: anônimo 401; COMERCIAL, FIGURINO, CASTING, revendedor 403; FINANCEIRO alterando devolução 403 | a leitura não abriu a escrita | **sim** |
| 18 | Card do pipeline: vendedora dona, outra vendedora, SUPERADMIN, FINANCEIRO; mês do evento; mês vazio; "Tudo" devolvido | seis × oito números; escopo; retido = KPI; quantidade 0 fora do mês; retido 0 conta | **sim** (vendedora ver imposto ou o cancelado de outra) |
| 19 | Card da DRE | itens com retido, devolvido, comissão; `paineis.cancelamentos.retido == dre.realizado.retido_cancelamentos` | não |
| 20 | Coisas ligadas: gasto (selo, reenviar o mesmo evento, gasto novo por chamada direta), tag, pedido de figurino, formulário (lista e ficha da cliente) | `event_situacao`/situação "cancelado"; vínculo direto de gasto passa | não |
| 21 | Portal: ficha de figurino do cancelado como escalado, como não escalado, e de um vivo | "Este evento foi cancelado." sem ficha; não escalado com a recusa de hoje; vivo 200 | **sim** |
| 22 | Regressão: mês, Dia e busca sem cancelado, talento e cliente sem cancelado, pipeline e DRE sem cancelado | payload igual ao da `main` (fora `cancelamentos` com quantidade 0) | não |
| 23 | Limpeza | usuários, eventos, talentos, clientes, gastos, notificações, logs e linhas da 306 do descartável apagados (`roles.clear()` antes do usuário) | — |

Regressão por fora: `verify_306.py` (base 67/69, ver `docs/03`), `verify_306b.py`, `verify_303.py`, e os antigos
de `scripts/db/` que passam pelos mesmos caminhos (`verify_cancelamento_evento.py`, `verify_145_agenda_read.py` —
o Dia, `verify_196_dashboard_comercial.py`, `verify_205.py`).

Conferência de tela (skill `manto-conferir-tela`), nos dois temas:
- agenda (Dia, Mês, Lista) e busca num mês com um cancelado e um marcado;
- Dashboard Comercial como Superadmin e como Comercial (card, lista, links);
- DRE (card e linha do retido);
- página de Cancelamentos como Financeiro (menu, filtros na URL, busca, vazio, 1024 px);
- fichas de cliente e de talento;
- Gastos Extras (selo e select);
- o painel do grupo de um principal vivo;
- a tela do cancelado como Superadmin, Comercial e Casting (só consulta, painéis de venda, caixa com e sem
  motivo, escala com "Tirar da escala");
- a Home do Casting com a pendência e o link do WhatsApp;
- a página pública de avaliação de 320 a 430 px;
- a ficha de figurino do portal no celular (375×812).

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Nenhuma visão da agenda, nenhuma busca, nenhuma ficha e nenhuma lista de escolha mostra um evento
  cancelado; os dois cancelados de produção somem do Dia e da busca no dia do deploy.
- **SC-002**: Um usuário de Casting, Figurino ou Ensaio que abre a tela do cancelado não vê o motivo nem quem
  cancelou.
- **SC-003**: Nenhuma ação na tela do cancelado, fora os dados de venda, o motivo e o desfazer, grava algo ou
  manda e-mail — de nenhum papel, nem de uma aba aberta antes do cancelamento.
- **SC-004**: O Casting acha em um clique, na Home, todo artista ainda escalado num evento cancelado, e a lista
  esvazia sozinha conforme ele tira os escalados.
- **SC-005**: O Financeiro abre a página de Cancelamentos e acha um cancelado pelo mês e pela situação da
  devolução sem pedir ao Superadmin.
- **SC-006**: O retido mostrado no card é, centavo a centavo, o mesmo da linha "Retido de cancelamentos" da DRE e
  do KPI do Comercial no mesmo mês.
- **SC-007**: Num mês sem cancelado, agenda, fichas, pipeline e DRE devolvem exatamente o mesmo de antes da
  entrega.

## Fora de escopo

- Botão ou parâmetro "Mostrar cancelados" em qualquer tela (Q6 = A).
- Card ou botão na DRE antiga (Jinja); tela nova no Jinja.
- O selo "Cancelamento pedido" e o "Evento em confirmação" do pedido (são da 2a).
- Mudar contas do cancelamento (retido, comissão, BV, imposto) — são da 306; aqui só se leem.
- Sino novo — o pedido ao Casting já sai pela 306; aqui não muda texto nem chave.
- Desfazer o cancelamento; desligar sozinho o que já estava ligado ao cancelado.
- Recusar no servidor o vínculo de Gasto Extra a cancelado.
- Trocar o 403 da ficha de figurino do portal por 404 (dívida 68 — a ordem da 302 fica).
- "Voltar para Agenda" da tela do cancelado continua apontando para `/agenda`.
- Criar usuário Financeiro em produção (é do dono).

## Docs a atualizar

`docs/00` §4 (FINANCEIRO lê Cancelamentos); `docs/01` §2.2 (`cancelled_at`), §3.3 (inventário de
`/events/cancelamentos` — quita a dívida 84), §3.4/§3.6/§3.7/§3.8/§3.13 (contratos alterados, recusas com o código
`cancelado`, 410 da avaliação, flags do detalhe, `cancelados_a_avisar`, card no pipeline), §4.3 (gates); `docs/02`
(agenda, Dashboard Comercial, DRE, página de Cancelamentos, fichas, Gastos Extras, seletores, Fila 3D, menu, tela
do evento cancelado, Home do Casting, painel do grupo, portal e avaliação); `docs/03` (entrada no topo + índice;
registrar que a frase da 306b "os demais veem o motivo" ficou superada pela Q9); `docs/04` (invariante "o
cancelado não aparece em lista nenhuma; vê-se na página, no card e na tela dele; nada novo se liga a ele; a tela
dele só se consulta, menos os dados de venda, o motivo e o desfazer"; fluxo "o Casting tira e avisa"); `docs/05`
(riscar 74 e 84; registrar o que sobrar).

## Premissas

- Ordem: sobe depois da 306/306b (já em produção). Nenhuma migration, tabela, variável de ambiente ou escrita
  externa nova.
- O cancelado entra no card e na página pelo **mês do cancelamento** (D33), no horário de São Paulo.
- O card aparece para todo papel que abre o Dashboard Comercial, no escopo dele; a página de Cancelamentos sem
  filtro de mês mostra os 200 mais recentes (sem padrão "mês corrente", que esconderia devolução antiga a pagar).
- O menu ganha o item na seção Financeiro (com chave própria) para o papel FINANCEIRO; FINANCEIRO hoje tem zero
  usuários em produção — o verify e a tela usam usuário descartável.
- O que já estava ligado ao cancelado antes do cancelamento fica como está (tag, presente, formulário, gasto,
  pedido de figurino), com o selo onde aparece.
- "Excluir" do pedido do dono ao Casting é tirar o artista da vaga; a vaga fica vazia, como registro do elenco.
- A pendência do Casting é derivada da escala, não um registro; pega também os cancelamentos feitos antes desta
  entrega (o 388 e o 1358, se ainda tiverem escalados).
- As decisões de desenho do plano 1c (§4, §8 premissas 1–37) valem onde a reconferência não as emendou.
