# Feature 310 — Pagamento da loja de conversas ligado com segurança (InfinitePay, Natal 2026)

**Branch**: `310-pagamento-loja-virtual` (da `main` em `98192e8`, worktree `C:\tmp\mp310`) ·
**Created**: 2026-10-19 · **Status**: Rascunho · **Migration**: aditiva (colunas novas; detalhe no
plano) · **Nível**: 1 (feature) — constituição, Princípio VI

**Input**: pedido do dono: "Precisamos andar com a parte do pagamento. Como devemos fazer? Um
abacatepay da vida? Ou usamos o infinitepay que já uso e tenho conta?" → decisão (19/10/2026):
**InfinitePay**, a que já existe; "pode abrir a feature com as correções e o roteiro do teste".

## O pedido, nas palavras do dono *(obrigatório)*

"Digitei alguns dados teste e publiquei. Ficou bom. Precisamos andar com a parte do pagamento."

Estado de produção em 19/10/2026 (leitura, sem escrita): a campanha "Uma chamada com o Papai
Noel" existe (id 1, `papai-noel`) e foi **pausada** pelo dono; a InfiniteTag e o token do aviso de
pagamento estão **vazios**, então toda reserva para em "O meio de pagamento ainda não está
configurado" — foi o que aconteceu com os dois pedidos de teste do dono (expirados, sem link).
**Nenhuma chamada real à InfinitePay jamais foi feita**: o `verify_205` substitui o cliente da
operadora por dublês.

## Por que a InfinitePay, e o que a pesquisa achou

Comparação com fontes oficiais, checada por um segundo agente independente
(`pesquisa/auditoria-e-operadoras-2026-10-19.txt`):

- A conta da maquininha serve para venda online: liga-se o **Checkout Integrado** no app (Vendas →
  Checkout → Configurações). Sem isso a API recusa todo link com `external_checkout_not_enabled`
  (sondado em 19/10/2026).
- **Pix grátis**, cai na hora; cartão online 4,20% (plano 1 dia útil) ou 5,49% (na hora); sem
  mensalidade. A AbacatePay cobra R$ 0,80 por Pix, paga cartão em D+30 com 10% retido por 40 dias,
  exige aprovação de conta e de cartão, e trocar custaria ~1 semana de código.
- O que a InfinitePay **não** tem: aviso de pagamento assinado, API de devolução (devolve-se pelo
  app: Pix até 90 dias, cartão até 180), ambiente de teste. A taxa do cartão é cobrada mesmo em
  venda cancelada; no Pix não pesa.
- Existe uma API nova (opcional, com chave `X-Api-Key`) que faz o link **vencer numa hora marcada**
  e **aceitar um pagamento só** — o que fecha a maior fonte de pagamento atrasado.
- Risco da conta: a InfinitePay pode desligar vendas online ou reter repasse diante de "venda
  incomum" — um pico de Natal numa conta com histórico de maquininha se encaixa. Mitigação:
  ligar e testar cedo, e o Pix como meio principal.

## Teste 0 em produção (20/10/2026, madrugada — com o dono)

- Configuração: InfiniteTag `prime-dreams` (conta logada no painel do dono; Checkout Integrado já
  ligado, "Etapa de endereço" ligada) e segredo gerado pelo servidor; campanha 2 `teste-pagamento`
  a R$ 1, publicada, 3 horários em 20/10 07:00–07:20.
- **POST /links aceitou** o pacote atual (telefone só com dígitos, `customer.name` etc.) e devolveu
  `https://checkout.infinitepay.io/prime-dreams?lenc=…`.
- **payment_check de pedido não pago, só com `handle` + `order_nsu` (ou com tx/slug vazios),
  responde `200 {"success":false}` — sem o campo `paid`.** O cliente trata como "não sei"; a
  varredura reteve 3 vezes e liberou com `expired_unverified=True`. Confirma o achado 2: sem os
  identificadores do aviso/retorno, a reconsulta não distingue "não pago" de "não achei". FR-011
  passa a tratar `success:false` sem `paid` explicitamente.
- **Teste A (Pix R$ 1, dono, 20/10 ~09:12–09:14 BRT): verde de ponta a ponta.** Pedido 4 pago em
  ~1,5 min; aviso com token certo chegou com as chaves `amount, capture_method, installments,
  invoice_slug, items, order_nsu, paid_amount, receipt_url, transaction_nsu` (sem `paid`), em
  centavos, `amount == paid_amount == 100` no Pix; reconsulta com os 4 campos devolveu `success,
  paid, amount, paid_amount, installments, capture_method` → `paid: true`; efetivado: evento 1399
  com Meet, e-mail `compra_confirmada` enviado. O contrato do `research.md` R1 (205) vale.

## Causa — o que a auditoria achou no código *(conferido contra `98192e8`)*

Cada achado foi refutado por um verificador cético contra o código
(`pesquisa/refutacao-e-lacunas-2026-10-19.json`). Os que se sustentaram:

1. **O mesmo horário pode ser vendido duas vezes.** A varredura de 60 s confirma pedidos pagos sem
   travar o horário, sem conferir se ele já é de outro pedido e sem conferir valor
   (`virtuais_ops.py` ~1110); a efetivação marca "vendido" sem gravar o dono do horário (~1295);
   a liberação de um pedido expirado devolve à vitrine um horário que outro pedido comprou (~971);
   a varredura e o aviso decidem sobre leitura velha do pedido, e um pedido **pago** pode voltar a
   "expirado". O aviso de pagamento só considera "tomado" o horário de outro pedido **travado**,
   não o **vendido**.
2. **Pagamento pode virar dinheiro sem dono.** Sem o aviso, o pedido não tem os identificadores da
   cobrança e a reconsulta provavelmente não funciona; esgotadas 3 tentativas, o horário é liberado
   sem devolução. A página de retorno descarta os identificadores que a InfinitePay manda na URL.
   Aviso "retido" de pedido expirado nunca é retentado, e a rota responde sempre 200 (a operadora
   não reenvia). Segundo pagamento do mesmo pedido vira "duplicado" sem devolução. Nenhuma tela lê
   os avisos problemáticos.
3. **Valor só é conferido no caminho do aviso**; a varredura confirma sem olhar valor, e
   `paid_amount` zero cai no valor nominal do link.
4. **Nome da criança vai à operadora** como se fosse o comprador (`customer.name`) e na descrição
   do item — dado de menor a terceiro sem necessidade.
5. **Fora da produção nada impede cobrar de verdade**: a constituição (XIV) exige trava para a
   InfinitePay e ela não existe; a cópia local traria a tag e o token espelhados, e o webhook_url
   local aponta para a produção.
6. **Limites anti-abuso valem para a loja inteira**, não por família: o limitador lê o IP do
   balanceador do Render (o ProxyFix confia em 1 salto; o caminho tem pelo menos 2) — 20 reservas
   por minuto para todo mundo, por processo. O mesmo vale para o login da plataforma.
7. **Ligar é armadilhado**: não há interruptor (salvar a tag liga a venda de toda campanha
   publicada); publicar não confere se o pagamento está configurado; a caixa "gerar segredo novo"
   continua marcada e troca o token a cada Salvar (mata o aviso dos links abertos); a tag aceita
   qualquer texto e a troca não fica registrada; **subir o logo desliga todos os e-mails** (a
   confirmação de compra inclusive); erro da operadora vira "tente de novo" e ninguém da equipe vê.
8. **O token do aviso aparece nos logs** (gunicorn e proxy); chamada sem token grava e ocupa a
   chave de idempotência; a rota não tem limite.
9. Família: contagem regressiva errada fora do fuso de Brasília (75:00 em Manaus); clicar de novo
   devolve o link do pedido anterior mesmo com outro horário/criança; "aguardando confirmação"
   aparece para quem não pagou; horário que já começou pode ser vendido; vídeo gravado vende acima
   da capacidade; sala do Meet desiste ~2 min depois da venda.

## Cenários e Verificação *(obrigatório)*

### História 1 — Um horário, uma família (Prioridade: P1)

A família que pagou tem o horário dela, e só ela. Nenhuma combinação de aviso atrasado, varredura,
segunda família e operadora lenta põe duas crianças no mesmo horário de 10 minutos, nem devolve à
vitrine um horário já vendido, nem desfaz uma venda confirmada.

**Por que esta prioridade**: venda dupla é o pior desfecho possível no Natal — duas famílias
esperando a mesma chamada.

**Verificação**: cenários 1–7 do `verify_310.py`.

**Cenários de aceite**:

1. **Dado** o pedido A com a trava vencida e a família B tendo reservado o mesmo horário, **Quando**
   a varredura descobre que A pagou, **Então** A vai para devolução (não vira venda) e o horário
   segue com B.
2. **Dado** o pedido A pago e confirmado pela varredura, **Quando** o pedido B do mesmo horário
   expira sem pagar, **Então** o horário continua vendido para A e não volta à vitrine.
3. **Dado** um pedido em confirmação pelo aviso, **Quando** a varredura decide ao mesmo tempo que
   ele não foi pago, **Então** o pedido termina pago e o horário vendido — nunca "expirado".
4. **Dado** dois pagamentos atrasados de pedidos expirados no mesmo horário, **Quando** os avisos
   chegam, **Então** o primeiro vira venda e o segundo vira devolução.
5. **Dado** um horário que já começou (ou começa em menos de 30 minutos), **Quando** chega o
   pagamento de um pedido dele, **Então** o pedido vai para devolução e a família recebe o e-mail
   de cancelamento.
6. **Dado** vídeo gravado com 1 vaga e duas famílias pagando, **Quando** os dois pagamentos
   confirmam, **Então** uma vira venda e a outra vira devolução.
7. **Dado** um mesmo pedido processado pelo aviso e pela varredura em paralelo, **Quando** os dois
   terminam, **Então** existe uma venda, um evento na agenda e nenhum evento sobrando no Google.

---

### História 2 — Todo pagamento termina em venda ou em devolução (Prioridade: P1)

Dinheiro que entrou na conta nunca fica sem dono no sistema: ou vira venda, ou vira uma devolução
pendente que a equipe vê, ou vira um alerta "pagamento a conferir".

**Por que esta prioridade**: sem isso, uma família paga, o horário é liberado e ninguém fica sabendo
até a reclamação no WhatsApp.

**Verificação**: cenários 8–15.

**Cenários de aceite**:

1. **Dado** uma família que pagou e voltou pela página de retorno, **Quando** o aviso não chegou,
   **Então** o sistema usa os identificadores do retorno para reconsultar na hora e confirma a
   venda (quem decide continua sendo a reconsulta na operadora).
2. **Dado** um pedido sem os identificadores da cobrança, **Quando** a varredura não consegue
   provar o pagamento, **Então** o pedido não é liberado como "não pago" em silêncio: vira
   "pagamento a conferir", visível à equipe.
3. **Dado** um aviso que terminou "retido" (operadora fora do ar) para um pedido expirado,
   **Quando** a operadora volta, **Então** o aviso é reprocessado até virar venda, devolução ou
   alerta.
4. **Dado** um pedido já pago, **Quando** chega o aviso de um **segundo** pagamento (outra
   cobrança), **Então** abre-se uma devolução do segundo pagamento e o pedido continua pago.
5. **Dado** um pagamento com valor menor que o total (ou valor pago zerado), **Quando** chega pelo
   aviso **ou** pela varredura, **Então** não vira venda e fica sinalizado à equipe.
6. **Dado** a reentrega de um aviso cujo primeiro processamento não decidiu nada, **Quando** ela
   chega, **Então** é processada (não é descartada como "duplicado").
7. **Dado** um aviso com o token certo, **Quando** ele chega, **Então** a resposta à operadora sai
   rápido e o processamento pesado (reconsulta, agenda, e-mail) acontece fora da requisição, com
   garantia de conclusão.
8. **Dado** um aviso forjado com identificadores inventados, **Quando** chega, **Então** esses
   identificadores não contaminam as reconsultas seguintes do pedido verdadeiro.

---

### História 3 — Ligar e desligar o pagamento com segurança (Prioridade: P1)

O dono configura a InfinitePay numa tela sem armadilhas, liga o pagamento quando quiser, desliga
sem perder pedidos em andamento, e fora da produção nada cobra de verdade.

**Por que esta prioridade**: hoje salvar a tag liga a venda de toda campanha publicada, e um clique
errado na tela troca o segredo e derruba os avisos.

**Verificação**: cenários 16–24.

**Cenários de aceite**:

1. **Dado** o banco local (espelho da produção, com tag e token reais), **Quando** alguém reserva,
   roda a varredura ou chama o aviso, **Então** nenhuma requisição sai para a InfinitePay nem para
   o Google, e a família vê uma mensagem clara de "pagamento travado neste ambiente".
2. **Dado** o pagamento desligado no interruptor, **Quando** uma família tenta reservar, **Então**
   não nasce link novo; avisos e reconsultas de pedidos já abertos continuam funcionando.
3. **Dado** o pagamento não configurado (tag ou segredo vazio) ou desligado, **Quando** a equipe
   tenta publicar uma campanha, **Então** a publicação é recusada com o motivo.
4. **Dado** a caixa "gerar segredo novo" marcada e salva, **Quando** a pessoa salva a tela de novo,
   **Então** o segredo **não** é trocado outra vez; trocar exige confirmação que diz quantos pedidos
   estão aguardando pagamento.
5. **Dado** uma tag com formato inválido (URL colada, espaço), **Quando** salva, **Então** é recusada;
   **Dado** uma troca de tag válida, **Então** a auditoria registra o valor antigo e o novo.
6. **Dado** o upload do logo na tela de configurações, **Quando** ele termina, **Então** os e-mails
   continuam ligados e nenhum outro campo da tela muda.
7. **Dado** a InfinitePay recusando o link (Checkout Integrado desligado, campo inválido), **Quando**
   a família tenta reservar, **Então** ela vê uma mensagem honesta, a reserva é desfeita sem contar
   no limite dela, e a equipe recebe um aviso com o motivo da operadora.

---

### História 4 — Limites por família, não pela loja inteira (Prioridade: P1)

No lançamento (story do Instagram, muita gente ao mesmo tempo), cada família tem o seu limite
anti-abuso; o limite de uma não bloqueia as outras.

**Por que esta prioridade**: hoje o limite de 20 reservas por minuto vale para a loja inteira, por
processo — um lançamento bem-sucedido daria "muitas tentativas" para famílias legítimas.

**Verificação**: cenários 25–26.

**Cenários de aceite**:

1. **Dado** duas famílias com IPs diferentes atrás do mesmo proxy, **Quando** uma estoura o seu
   limite, **Então** a outra continua reservando.
2. **Dado** um cabeçalho de origem que o cliente tenta forjar à esquerda, **Quando** a requisição
   chega, **Então** o IP considerado é o que a infraestrutura confiável registrou.

---

### História 5 — Nada da criança vai à operadora, e o segredo não vaza (Prioridade: P1)

**Verificação**: cenários 27–29.

**Cenários de aceite**:

1. **Dado** uma reserva, **Quando** o link é pedido à InfinitePay, **Então** o pacote enviado não
   contém o nome da criança (nem como comprador, nem na descrição do item); leva só o que a
   operadora precisa para o recibo (e-mail e telefone do comprador, no formato que ela aceita).
2. **Dado** um aviso de pagamento, **Quando** ele passa pelos logs do servidor e do proxy, **Então**
   o token aparece mascarado.
3. **Dado** uma chamada à rota do aviso **sem** o token certo, **Quando** ela chega, **Então** não
   ocupa a chave de idempotência de um aviso legítimo, não grava volume e respeita um limite.

---

### História 6 — A equipe vê o que precisa de ação (Prioridade: P2)

Comercial e Superadmin enxergam, num lugar só, devoluções pendentes **e** pagamentos a conferir
(retidos, divergentes, órfãos, pagos em dobro, liberados sem prova), com o que precisam para achar
a cobrança no app da InfinitePay (NSU, slug, recibo, data). O sino avisa quando nasce algo.

**Verificação**: cenários 30–32.

**Cenários de aceite**:

1. **Dado** um aviso divergente, **Quando** a equipe abre a tela, **Então** ele aparece com os
   identificadores da cobrança e um botão para marcar como resolvido.
2. **Dado** uma devolução nova, **Quando** ela nasce, **Então** Comercial e Superadmin recebem
   notificação no sino.
3. **Dado** um papel sem acesso à loja, **Quando** tenta ler a lista, **Então** recebe 403.
4. **Dado** um pedido pago que a família desistiu, **Quando** a equipe
   usa "Cancelar e abrir devolução", **Então** o horário volta à vitrine, a venda sai e a devolução
   fica pendente para execução no app da InfinitePay.

---

### História 7 — A família entende onde está (Prioridade: P2)

**Verificação**: cenários 33–36 + tela aberta em 375px.

**Cenários de aceite**:

1. **Dado** uma família em Manaus (UTC−4), **Quando** reserva, **Então** a contagem mostra os 15
   minutos reais da trava.
2. **Dado** uma família que voltou do checkout e escolheu outro horário (ou outra criança, ou
   acrescentou o presente), **Quando** clica em reservar, **Então** nasce o pedido novo — nunca o
   link do pedido anterior.
3. **Dado** um pedido com link gerado e pagamento não identificado, **Quando** a família abre a
   página, **Então** lê "ainda não identificamos o pagamento", não "aguardando confirmação".
4. **Dado** a criação do link ainda em andamento, **Quando** a família cai na página do pedido,
   **Então** vê "gerando o pagamento…" e a página se atualiza sozinha.

---

### História 8 — Sala do Meet garantida até a chamada (Prioridade: P2)

**Verificação**: cenários 37–38.

**Cenários de aceite**:

1. **Dado** o Google fora do ar no momento da venda, **Quando** ele volta horas depois, **Então** a
   sala é criada (o sistema continua tentando até o horário).
2. **Dado** uma venda sem sala a menos de X horas da chamada, **Quando** a varredura passa, **Então**
   a equipe é avisada.
3. **Dado** um evento da loja criado no Google cuja gravação local falhou, **Quando** a sincronização
   da agenda roda, **Então** ele não vira evento comum (com venda, funil e DRE).

---

### História 9 — O link de pagamento vence junto com a reserva (Prioridade: P2)

Com a API nova da InfinitePay, o link expira quando a reserva expira e aceita um pagamento só — a
família não consegue pagar um horário que já voltou para a vitrine.

**Verificação**: cenários 39–40 (contra dublê) + teste real.

**Cenários de aceite**:

1. **Dado** a chave da API configurada, **Quando** o link é criado, **Então** ele leva a validade da
   reserva e a opção de pagamento único; **Dado** a chave ausente, **Então** o fluxo atual continua.

- **FR-030**: A História 9 entra **condicional à chave**: sem a API Key o fluxo atual segue intacto;
  com ela, o link vence com a reserva. O dono está configurando o Checkout Integrado (19/10/2026) e
  cria a chave quando o código a suportar — cadastrada direto no painel do Render, nunca pelo chat.
  Não se cadastra URL de webhook no painel da InfinitePay: o endereço (com o segredo) vai dentro de
  cada link.

---

### História 10 — Teste real de baixo valor e o roteiro de ligar a loja (Prioridade: P1)

Antes de abrir para o público, um teste noturno com uma campanha só por link, a R$ 1, prova o
contrato real da InfinitePay (formato do aviso, da reconsulta, do retorno, do telefone), o caminho
sem aviso e o conflito com devolução pelo app. Há um roteiro escrito de **ligar** e **desligar** a
loja.

**Verificação**: roteiro `quickstart.md` executado com o dono (não é verify: depende da operadora
real e de um Pix de verdade); resultado registrado na spec.

**Cenários de aceite**:

1. **Dado** uma campanha publicada **fora da vitrine** (só pelo link), **Quando** a vitrine de
   `alo.*` é aberta, **Então** ela não aparece; pelo link, aceita reserva.
2. **Dado** o teste A (Pix, caminho feliz), **Quando** termina, **Então** o pedido está pago, o
   e-mail chegou, o evento com sala existe, e o formato real do aviso e da reconsulta ficou
   registrado.
3. **Dado** o teste B (aviso bloqueado de propósito), **Quando** a família volta pelo retorno,
   **Então** a venda confirma pela reconsulta.
4. **Dado** o teste C (conflito), **Quando** o segundo pagamento chega, **Então** nasce a devolução,
   ela é executada no app da InfinitePay e marcada como concluída.
5. **Dado** o fim do teste, **Quando** a limpeza roda, **Então** as vendas de teste saem dos
   relatórios (vendas, comissão, DRE) e os eventos de teste saem da agenda e do Google.

### Casos de borda

- Operadora fora do ar ao criar o link, na reconsulta e no meio do aviso — cada um termina em
  "retido e retentado", nunca em "não pago".
- Deploy no meio de um aviso (worker morto depois de gravar o registro) — a reentrega ou a varredura
  terminam o trabalho.
- QR Pix pago depois de a reserva expirar com o horário ainda livre e futuro → vira venda (como hoje).
- QR Pix pago depois de o horário passar → devolução.
- Troca do segredo com pedidos abertos → os avisos do segredo antigo continuam aceitos por um tempo
  ou caem na reconsulta pelo retorno/varredura (o plano decide); nunca dinheiro sem dono.
- Família reserva para dois irmãos na mesma aba → dois pedidos distintos.

## Requisitos *(obrigatório)*

### Requisitos funcionais

**Um horário, uma família (H1)**

- **FR-001**: Uma única regra decide se um pagamento vira venda, usada pelo aviso **e** pela
  varredura: pedido relido com trava; pago com valor conferido; horário ainda deste pedido; horário
  começando a mais de 30 minutos (folga de preparo no pagamento — a antecedência de 2 h do FR-006 vale
  para reservar; research R1.6); vaga de vídeo disponível. Falhou qualquer item →
  devolução (se houve pagamento) ou alerta (se não há prova).
- **FR-002**: A venda grava o dono do horário; um horário vendido nunca volta à vitrine por
  liberação de outro pedido.
- **FR-003**: Liberar, efetivar e devolver releem o pedido com trava e só seguem se o estado ainda
  for o esperado; uma venda confirmada nunca regride.
- **FR-004**: O horário de um pedido em reconsulta pendente fica de fato retido (não reaparece na
  vitrine) até a decisão.
- **FR-005**: A criação do evento/sala no Google acontece depois de a venda estar garantida no banco,
  para que nenhuma disputa deixe evento órfão; a falha do Google não desfaz a venda.
- **FR-006**: Antecedência mínima para reservar: a vitrine e a reserva só oferecem horários que
  começam **pelo menos 2 horas** depois de agora (decisão do dono, 19/10/2026 — a equipe precisa ler
  as dicas e o artista se preparar); configurável por constante.
- **FR-007**: O vídeo gravado não vende acima da capacidade: reservas ativas contam, e a efetivação
  confere o teto.
- **FR-008**: Uma disputa ou erro numa efetivação da varredura não aborta o lote nem gasta as
  reconsultas dos outros pedidos; pedido com pagamento provado nunca cai no ramo "liberar".

**Todo pagamento termina em venda ou devolução (H2)**

- **FR-010**: A página de retorno lê os identificadores que a InfinitePay manda (order_nsu, slug,
  transaction_nsu, capture_method, receipt_url) e pede ao servidor uma reconsulta imediata; o
  servidor só aceita identificadores do próprio pedido (order_nsu confere com o token) e só os grava
  depois de a reconsulta provar o pagamento.
- **FR-011**: A reconsulta distingue "pago", "não pago" e "não sei"; resposta genérica da operadora
  (404 "Not found", identificadores ausentes) é "não sei", nunca "não pago".
- **FR-012**: Pedido sem prova ao fim da tolerância vira "pagamento a conferir" (visível, H6), não
  "expirado" silencioso.
- **FR-013**: Avisos "retidos" ou sem desfecho são reprocessados (qualquer que seja o estado do
  pedido) até virarem venda, devolução ou alerta; reentrega de aviso sem desfecho final é processada.
- **FR-014**: Segundo pagamento de um pedido pago (cobrança diferente) abre devolução **dele**, sem
  cancelar o pedido.
- **FR-015**: A conferência de valor usa o valor pago informado pela operadora; ausente ou menor que
  o total → não vira venda.
- **FR-016**: A resposta ao aviso sai rápido (a InfinitePay pede < 1 s); o processamento pesado
  roda fora da requisição, com reprocessamento garantido; chamadas ao Google e ao e-mail têm prazo.
- **FR-017**: Identificadores vindos no corpo de um aviso só são gravados no pedido depois de a
  reconsulta com eles provar o pagamento.

**Ligar e desligar com segurança (H3)**

- **FR-020**: Trava da InfinitePay derivada do host do banco (localhost/sqlite = travado), com escape
  explícito para teste local, no mesmo molde das travas de e-mail e agenda (constituição XIV);
  travado, nenhuma requisição sai e o desfecho é "não sei". A criação de evento de venda virtual no
  Google respeita trava equivalente.
- **FR-021**: Interruptor "pagamento da loja ligado" no card de pagamento: desligado, não nasce link
  novo; aviso, retorno e reconsulta seguem funcionando. Nasce **desligado**.
- **FR-022**: Publicar campanha exige pagamento configurado e ligado.
- **FR-023**: Gerar segredo novo exige confirmação explícita que mostra quantos pedidos aguardam
  pagamento; a caixa volta a desmarcada depois de salvar.
- **FR-024**: A tag é validada (só letras, números, `_ . -`, sem `$` e sem URL) e a troca grava
  auditoria com o valor antigo e o novo.
- **FR-025**: Salvar qualquer parte da tela de configurações (inclusive só o logo) altera somente os
  campos enviados — e-mails, WhatsApp e data de corte não mudam de carona.
- **FR-026**: Recusa da operadora ao criar o link: a família lê mensagem honesta; o código da
  operadora fica gravado; não se repete chamada recusada; a tentativa não conta no limite por
  origem; Comercial e Superadmin recebem aviso no sino (agrupado).

**Limites por família (H4)**

- **FR-027**: Um único ponto define o IP do cliente a partir da cadeia de proxies confiáveis (número
  de saltos configurável e medido em produção); o limitador e a origem anti-abuso da loja usam esse
  ponto, nunca o cabeçalho cru. Sem IP resolvível → balde nomeado e registro em log.

**Privacidade e segredo (H5)**

- **FR-028**: O link enviado à operadora não leva o nome da criança; descrição neutra (campanha +
  formato + código do pedido); comprador com e-mail e telefone no formato aceito pela operadora.
- **FR-029**: O token do aviso aparece mascarado nos logs do servidor e do proxy; comparação em tempo
  constante; chamada sem token não ocupa a chave de idempotência, grava no máximo um resumo curto e
  respeita limite de requisições.

**Visibilidade (H6)**

- **FR-031**: Lista de pagamentos a conferir (retido, divergente, órfão, pago em dobro, liberado sem
  prova) junto das devoluções, com NSU, slug, recibo e data, e ação "marcar como resolvido" com
  auditoria; RBAC igual ao das devoluções (Comercial, Superadmin).
- **FR-032**: Notificação no sino para devolução nova, pagamento a conferir e falha de link.
- **FR-033**: O recibo da operadora (receipt_url) fica guardado no pedido quando chega.
- **FR-034**: Botão "Cancelar e abrir devolução" para pedido pago (decisão do dono, 19/10/2026 —
  família que desistiu, criança doente): Comercial e Superadmin, com confirmação; o horário volta à
  vitrine (se ainda estiver no futuro além da antecedência), a venda sai dos relatórios, o evento sai
  da agenda e do Google, e a devolução fica pendente para execução no app da InfinitePay.

**Família (H7)**

- **FR-035**: A contagem regressiva usa o tempo restante calculado no servidor (independe do fuso
  do aparelho).
- **FR-036**: Reaproveitar o pedido pelo token da aba só quando horário, formato, presente e criança
  forem os mesmos; depois de cada reserva, a aba ganha token novo.
- **FR-037**: Textos distintos para "gerando o pagamento", "link gerado, pagamento não identificado"
  e "confirmando o pagamento"; a página se atualiza sozinha nos três.

**Sala (H8)**

- **FR-038**: A sala do Meet é retentada de forma espaçada até o horário da chamada; faltando menos de
  X horas sem sala, a equipe é avisada (X definido no plano; sugestão 6 h).
- **FR-039**: Eventos da loja criados no Google levam marca própria e a sincronização da agenda não os
  importa como eventos comuns.

**Link que vence (H9)**

- **FR-040**: Com a chave da API configurada (variável de ambiente, nunca lida pela API), o link leva
  validade = fim da trava e pagamento único; sem chave, o fluxo atual. Depende do FR-030.

**Teste e operação (H10)**

- **FR-041**: Campanha pode ser publicada **fora da vitrine** (acessível só pelo link).
- **FR-042**: Pedidos/vendas de teste podem ser marcados e removidos dos relatórios de vendas,
  comissão e DRE por um procedimento documentado (script com simulação e `--execute`).
- **FR-043**: Roteiro escrito "ligar a loja / desligar a loja / teste de R$ 1" no `quickstart.md`
  e em `DEVELOPMENT.md` §Operar a produção, incluindo a regra de deploy durante a campanha.

### Entidades

- **VirtualOrder** (existente): ganha motivo de falha do link, recibo da operadora, estado "a
  conferir" e marca de teste — detalhe no plano.
- **VirtualPaymentNotification** (existente): ganha estado de processamento (pendente/decidido),
  tentativas e "resolvido por/quando"; chamada sem token deixa de ocupar `transaction_nsu`.
- **VirtualRefundRequest** (existente): novos motivos "pagamento em dobro" e "desistência" (FR-034).
- **VirtualCampaign** (existente): "listada na vitrine".
- **SiteSetting** (existente): interruptor "pagamento da loja ligado".

### RBAC

- `POST /api/virtuais/pedidos/<token>/retorno` (novo) — público, por token não adivinhável; limite
  por IP do cliente; só identificadores do próprio pedido.
- `GET /api/virtuais/pagamentos-a-conferir` + `PATCH .../<id>/resolver` (novos) — COMERCIAL,
  SUPERADMIN (mesmo gate de `/virtuais/devolucoes`).
- `PATCH /api/admin/settings` (alterado) — SUPERADMIN, como hoje.
- `POST /api/virtuais/pedidos/<id>/cancelar` (novo, FR-034) — COMERCIAL, SUPERADMIN.
- Linhas na tabela de `docs/01` §4.3.

## Verificação (`verify_310.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/310-pagamento-loja-virtual/verify_310.py`, contra `manto_local`. A InfinitePay e o
Google são **dublês que falham fechado** (nenhuma rede); prova por mutação roda a sonda limpa antes
da mutada.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | trava vencida, B reserva, varredura acha A pago | A vira devolução; horário segue com B | **sim** no HEAD |
| 2 | A confirmado pela varredura, B expira | horário segue vendido para A | **sim** no HEAD |
| 3 | aviso confirma A enquanto a varredura decide "não pago" (barreira entre threads) | A termina pago | **sim** no HEAD |
| 4 | dois pagamentos atrasados de expirados, mesmo horário | 1 venda + 1 devolução | **sim** no HEAD |
| 5 | pagamento de horário que já começou / dentro da antecedência | devolução + e-mail | **sim** no HEAD |
| 6 | vídeo com 1 vaga, dois pagamentos | 1 venda + 1 devolução | **sim** no HEAD |
| 7 | aviso e varredura no mesmo pedido em paralelo | 1 venda, 1 evento, 0 chamada extra ao Google | não |
| 8 | retorno com identificadores, sem aviso | reconsulta imediata confirma | — |
| 9 | retorno com order_nsu de outro pedido | recusado, nada gravado | **sim** |
| 10 | reconsulta "Not found"/sem identificadores | "não sei" → "a conferir", nunca "não pago" | — |
| 11 | aviso retido de pedido expirado, operadora volta | reprocessado até decisão | — |
| 12 | segundo pagamento de pedido pago | devolução do segundo; pedido segue pago | — |
| 13 | valor menor / zerado, pelo aviso e pela varredura | não vira venda; sinalizado | **sim** |
| 14 | reentrega de aviso sem desfecho | processada | — |
| 15 | aviso forjado com identificadores inventados | não contamina a reconsulta | **sim** |
| 16 | banco local: reservar, varredura, aviso | 0 requisição à InfinitePay e ao Google | — |
| 17 | interruptor desligado | sem link novo; aviso de pedido aberto segue | — |
| 18 | publicar sem pagamento configurado/ligado | recusado | **sim** |
| 19 | salvar a tela duas vezes com a caixa marcada uma vez | segredo trocado uma vez só | — |
| 20 | tag inválida / troca de tag | recusada / auditoria antigo→novo | **sim** / — |
| 21 | upload só do logo | e-mails, WhatsApp e data de corte intactos | — |
| 22 | operadora recusa o link (`external_checkout_not_enabled`) | mensagem honesta, motivo gravado, sem retry, fora do limite, sino | — |
| 23 | aviso lento (dublê de Google/e-mail parados) | resposta rápida; processamento conclui depois | — |
| 24 | SUPERADMIN-only no PATCH de configurações | COMERCIAL recebe 403 | **sim** |
| 25 | duas famílias, IPs distintos, uma estoura o limite | a outra segue | — |
| 26 | cabeçalho de origem forjado à esquerda | IP confiável é o considerado | **sim** |
| 27 | pacote enviado à operadora | sem nome da criança; telefone no formato aceito | — |
| 28 | log do servidor/proxy com o aviso | token mascarado | — |
| 29 | aviso sem token com NSU de um aviso real | não ocupa o NSU; limite aplicado | **sim** |
| 30 | lista de pagamentos a conferir | itens com NSU/slug/recibo; resolver audita | — |
| 31 | papel sem acesso lê a lista | 403 | **sim** |
| 32 | devolução nova / a conferir / falha de link | notificação no sino | — |
| 33 | contagem com fuso do aparelho diferente | tempo restante do servidor | — |
| 34 | segunda reserva com outro horário/criança na mesma aba | pedido novo | — |
| 35 | textos dos três estados de espera | distintos; atualização automática | — |
| 36 | cancelar pedido pago (FR-034) | horário volta, venda sai, devolução pendente | — |
| 37 | Google volta horas depois | sala criada antes do horário | — |
| 38 | evento da loja órfão no Google + sincronização | não importado como evento comum | — |
| 39 | (se FR-030) chave presente | link com validade e pagamento único | — |
| 40 | (se FR-030) chave ausente | fluxo atual intacto | — |
| 41 | campanha fora da vitrine | some da vitrine; abre pelo link | — |
| 42 | limpeza de venda de teste | sai de vendas, comissão e DRE | — |
| 43 | regressão | `verify_205.py` e `verify_304.py` verdes | — |
| 44 | limpeza | registros descartáveis apagados; nada de rede escapou do dublê | — |

Conferência de tela: vitrine, campanha, pedido (estados de espera, retorno) em 375×812; card de
pagamento em Configurações; lista de pagamentos a conferir.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Em nenhum cenário de concorrência, atraso ou falha da operadora duas famílias ficam com
  o mesmo horário (0 em 44 cenários e na rodada repetida 20×).
- **SC-002**: 100% dos pagamentos provados terminam em venda ou devolução pendente; 100% dos casos
  de R-07 (divergente, órfão, esgotado, operadora fora, falha de link) aparecem em "a conferir" em até
  20 minutos.
- **SC-003**: A família que pagou vê "pago" em até 1 minuto depois de voltar do checkout, mesmo sem
  aviso da operadora.
- **SC-004**: O teste real de R$ 1 (A, B e C) passa com custo ≤ R$ 5, todos devolvidos, e deixa o
  formato real do aviso e da reconsulta registrado.
- **SC-005**: Com o banco local, 0 requisição sai para a InfinitePay ou o Google.
- **SC-006**: No lançamento, uma família só é limitada pelo que ela própria faz.

## Regras complementares (fechadas pela checklist de 20/10/2026)

**Dinheiro**
- **R-01 Ordem da regra única** (FR-001): (1) relê o pedido com trava; (2) estado — `pago` com a
  mesma cobrança = duplicado; `pago` com outra = devolução `pagamento_em_dobro`; `cancelado` =
  devolução `pagamento_sem_pedido_ativo`; (3) valor; (4) dono do horário; (5) folga de 30 min;
  (6) vaga do vídeo; (7) grava a venda; (8) Google e e-mail fora das travas.
- **R-02 Valor**: `paid_amount >= total` vira venda; **sobrepagamento** (cartão com juros repassados)
  também vira venda, sem devolução de diferença. `paid_amount` ausente ou menor = **divergente**:
  sem venda e **sem devolução automática** — entra em "a conferir" (a equipe olha o app e decide).
- **R-03 Vídeo**: reserva ativa de vídeo ocupa vaga enquanto a trava dela vale (15 min); a efetivação
  confere `vendidos < capacidade`.
- **R-04 Presente 3D**: devolução e cancelamento pela equipe tiram o presente da fila de impressão se
  ainda não começou; se já começou, fica e entra em "a conferir".
- **R-05 Ordem de travas** pedido → horário → campanha vale para reserva, liberação, varredura,
  aviso, retorno e cancelamento pela equipe.
- **R-06 Reprocessamento de aviso**: 3 tentativas nos minutos 0/1/2, depois a cada 10 min, por até
  48 h; esgotou = "a conferir". Desfechos finais: `efetivado`, `devolucao_aberta`, `conflito`,
  `duplicado`, `divergente`, `orfao`; não finais: `pendente`, `retido`, `pendente_prova`.
- **R-07 "A conferir"** reúne só: aviso divergente, órfão ou esgotado; pedido liberado **por operadora
  fora** (não por abandono); falha de link (agrupada por código e hora). Pedido abandonado sem aviso
  nem retorno expira como hoje e **não** entra. Quem resolve: COMERCIAL e SUPERADMIN; resolver é
  irreversível e auditado.

**Prova de pagamento**
- **R-08 Retorno**: antes do aviso → decide pela reconsulta com os identificadores do retorno; depois
  do aviso → devolve o estado já decidido; sem identificadores → só devolve o estado.
- **R-09 Varredura** usa, na falta de identificadores no pedido, os de avisos já registrados com o
  token certo para o mesmo `order_nsu`.
- **R-10 Risco aceito**: pagou + aviso perdido (ex.: 502 no deploy) + família não tocou "Continuar" =
  pedido expira e o dinheiro só aparece no app da InfinitePay. Mitigação: regra de deploy (R-17) e
  conferência no painel "Seus Checkouts" depois de cada deploy durante a campanha.

**Segurança**
- **R-11 Ameaça do aviso**: qualquer um que saiba o endereço pode chamar; o corpo nunca decide; só
  a reconsulta na operadora com os identificadores do próprio aviso prova; identificadores só são
  gravados depois da prova.
- **R-12 Segredo anterior** vale 24 h depois de regerar (cobre links abertos; a trava de 15 min
  torna mais que isso desnecessário). Regerar mostra a contagem de pedidos aguardando.
- **R-13 Logs**: o segredo aparece mascarado no log de acesso do servidor, no log do proxy e em
  qualquer mensagem de aplicação.
- **R-14 Limites**: aviso 60/min por IP e corpo até 64 KB; retorno 20/min por IP do cliente.
- **R-15 Pacote à operadora**: `handle`, `order_nsu`, `redirect_url`, `webhook_url`, item com
  descrição "<título> — pedido <order_nsu>", valor em centavos, `customer` só com `email` e
  `phone_number` (dígitos). Nada de nome, idade, dicas ou endereço.
- **R-16 IP do cliente** vale enquanto o Node for o único caminho público de `/api`; quem chama o
  backend direto só escolhe o próprio balde. Se o `BACKEND_URL` mudar para rede privada, revisar.

**Trava e operação**
- **R-17 Trava local**: InfinitePay (link e reconsulta) pela trava nova; criar e apagar evento no
  Google pela `CALENDAR_SUPPRESS_EVENT_WRITES`; e-mail pela `_suppress_mail` existente. Travado, a
  família lê "Pagamento travado neste ambiente (cópia de teste)". O `webhook_url` local apontaria
  para a produção — por isso o link nem é criado.
- **R-18 Interruptor**: nasce desligado; depois do deploy o dono liga no card. Desligado com campanha
  publicada: a campanha continua visível e a reserva responde "As reservas estão fechadas por
  enquanto" (nenhum horário é travado).
- **R-19 Cancelar pago**: horário volta à vitrine só se faltar mais de 2 h; senão fica vendido sem
  dono. A família recebe o e-mail de cancelamento com devolução em andamento. Sino deduplica por
  item (devolução, aviso, pedido) e falha de link por código por hora.
- **R-20 Deploy na campanha**: de 1º/11 a 25/12, nenhum deploy entre 9h e 23h (BRT); depois de cada
  deploy, conferir "Pagamentos a conferir" e o painel da InfinitePay. Vai para `DEVELOPMENT.md` e a
  skill `manto-deploy`.
- **R-21 Limpeza de teste**: o pedido fica `cancelado` (histórico), avisos ficam, auditoria registra;
  saem evento, escala, entrega, presente e o evento do Google; horário volta a livre.
- **R-22 SC-001**: uma rodada = os 7 cenários de concorrência da H1 com duas conexões reais e barreira
  entre threads; 20 rodadas seguidas sem dois pedidos pagos no mesmo horário.

## Fora de escopo

- Trocar de operadora (AbacatePay etc.) e devolução automática por API (a InfinitePay não tem).
- Assinatura recorrente, cupom, parcelamento com juros repassados, boleto.
- Nome do responsável na ficha (`buyer_name`): exigiria campo novo no checkout; o comprador vai à
  operadora só com e-mail e telefone.
- Levar o retorno e os e-mails para `alo.*` em vez de `app.*` (funciona; é cosmético).
- O botão "Nova campanha" quebrado (`docs/05` 88) — feature própria.
- O limitador em memória por processo (o limite efetivo fica ~3× o nominal); documentado, não
  corrigido.

## Docs a atualizar

`docs/01` (§4.3 RBAC, contratos novos, §5 variáveis novas), `docs/02` (card de pagamento, lista a
conferir, estados da página do pedido), `docs/03` (entrada no topo), `docs/04` (máquina de estados do
pedido virtual e a regra única de efetivação), `docs/05` (risca o que quitar; registra o limitador
em memória), `DEVELOPMENT.md` §Operar a produção (ligar/desligar a loja, teste de R$ 1, trava local),
skill `manto-deploy` (deploy durante a campanha).

## Premissas

- Pix é o meio principal; cartão fica sempre ligado no checkout (a operadora não permite desligar).
- A antecedência mínima e o X horas do alerta de sala são configuráveis; os valores do Natal saem
  da resposta do dono.
- O número de saltos de proxy em produção é medido por leitura (SSH, só log), antes do código final.
- O teste real é feito pelo dono (o Pix sai da conta dele) com a campanha fora da vitrine, à noite.
- Nenhum deploy desta feature no horário de pico de vendas; ela sobe antes de a campanha reabrir.
- A migration pendura em `a7c3e91f4d28`; 306 e 309 também — quem mergear por último reencadeia.
- Só a operadora real responde: segundo pagamento no mesmo link legado e a reconsulta de um Pix pago
  e devolvido — testados no teste C com o dono depois do deploy.
