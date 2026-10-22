# Feature 318 — O PIX que cai no Inter se liga sozinho à venda (e pergunta "É esta?" quando há dúvida)

**Branch**: `318-pix-recebido-por-email` (da `main` em `5781993c`) · **Created**: 2026-10-22 · **Status**: Rascunho ·
**Migration**: uma, aditiva (duas tabelas novas — contas que recebem e PIX recebidos —, três colunas no comprovante,
`file_path` do comprovante passa a aceitar vazio, seis colunas em `site_settings`), escrita à mão sobre o head da
`main` · **Nível**: 1 (feature) — migration, endpoints novos, tela nova, thread de fundo, dois domínios (financeiro e
agenda/comprovantes); constituição, Princípio VI

**Input**: pedido do dono (22/10/2026): automação que lê os e-mails de aviso de PIX recebido das contas da empresa e
liga o pagamento ao evento/cliente sozinha. Plano aprovado pelo dono em 22/10/2026
(`C:\Users\schim\.claude\plans\system-reminder-linked-sessions-now-lexical-hamster.md`).

## O pedido, nas palavras do dono *(obrigatório)*

> "Recebo um e-mail para cada PIX que entra nas contas. Quero uma automação que leia esses e-mails e ligue o pagamento
> ao evento/cliente sozinha, sem ação humana quando o vínculo é óbvio e com um 'é esse?' de um clique quando há
> dúvida." — "a ideia é que o comercial não tenha esse trabalho de fazer nada manualmente."

O sintoma, como está hoje: o "recebido" de uma venda é só a soma dos comprovantes que a comercial anexa à mão, dias
depois do PIX. O cruzamento extratos × ERP de 21/10/2026 (jun–out) achou **R$ 209 mil de dinheiro de cliente no
banco sem registro no sistema** (18,5% do recebido), cobranças em aberto que já tinham sido pagas (R$ 77 mil do
"vencido" já tinha entrado) e **nenhuma informação de qual conta recebeu** — e a conta do MEI recebeu R$ 887 mil no
período, o que importa para o contador.

## Clarifications

### Session 2026-10-22 — decisões do dono (palavras dele; não se reabrem)

- **Q: De qual caixa o sistema lê os avisos?** → **A**: "joao@manto + filtro". O sistema lê
  joao@mantoproducoes.com.br (a caixa que já lê hoje para os e-mails devolvidos, feature 219); um filtro no Gmail
  da Prime encaminha para lá só os "Pix recebido" do Inter. **Feito em 22/10/2026**: filtro
  `from:(no-reply@inter.co) subject:("Pix recebido")` → encaminhar para joao@mantoproducoes.com.br, criado e
  confirmado na conta joao@primedreams.com.br.
- **Q: Quando o sistema liga o PIX à venda sem ninguém conferir?** → **A**: "Valor + mais um sinal" — uma única venda
  aberta com aquele valor (saldo, sinal, parcela ou total) **e** (o nome de quem pagou bate com a cliente **ou** esse
  pagador já pagou essa venda antes). O resto vira "É esta?".
- **Q: Quem responde o "É esta?"** → **A**: "comercial / financeiro / superadmin".
- **Q: O que fazer com PIX que não é de venda?** → **A**: "Só ignorar" — sem fila nem aviso. (O registro fica
  guardado para deduplicar e auditar.)
- **Q: Como é o repasse da InfinitePay para o MEI?** → **A**: "Varia" (às vezes um PIX por venda, às vezes vários
  juntos), feito à mão pelo dono; chega no Inter MEI com o nome "Prime Dreams".
- **Q: A comercial anexa comprovante das vendas pagas na InfinitePay?** → **A**: "não sei se o comercial tem feito de
  forma adequada. a ideia é que o comercial não tenha esse trabalho de fazer nada manualmente".

- **Q (clarify): PIX que chega antes de a venda existir no sistema?** → **A**: "Tenta de novo por 7 dias" — a cada
  leitura, o PIX sem venda dos últimos 7 dias é comparado de novo; quando a venda aparece, liga sozinho ou vira "É
  esta?"; depois disso fica ignorado.
- **Q (clarify): "Desfazer" depois que alguém anexou arquivo ao pagamento do PIX?** → sem preferência do dono; vale o
  recomendado: o pagamento **fica como comprovante manual** (o arquivo prova o pagamento), só perde o vínculo, e o PIX
  volta a "para conferir".

### Fatos da viabilidade (22/10/2026, leitura sem escrita)

- Só o **Inter** manda e-mail por PIX recebido (remetente `no-reply@inter.co`, assunto "Pagamento Pix recebido"):
  MEI para joao@mantoproducoes (337 avisos desde 01/06/2026, ≈70/mês), Prime para joao@primedreams (≈3–9/mês).
  InfinitePay e Cora **não** mandam (a InfinitePay só avisa pedido do Checkout Integrado, que a 205/310 já recebe por
  webhook).
- O corpo do aviso traz, numa frase: valor, nome completo de quem pagou e número da conta que recebeu. **Não** traz
  CPF, id E2E nem hora (a hora é a do cabeçalho do e-mail, que chega em segundos). Outros avisos do Inter: "Pix
  devolução recebida" (devolução de PIX nosso) e "Pagamento Pix realizado" (saída) — ambos fora.
- Os avisos chegam com `dkim=pass header.i=@inter.co`, `spf=pass`, `dmarc=pass`.
- A caixa joao@mantoproducoes guarda cópia de tudo (o encaminhamento para a caixa pessoal não apaga).
- Do cruzamento de 21/10: dos 271 PIX casados com comprovante, só 137 (51%) têm o nome do pagador parecido com o da
  cliente (pagam cônjuge, empresa, escola) — o valor é a chave, o nome desempata. Há 41 transferências internas
  ("Prime Dreams" → MEI) e 18 PIX com o nome do sócio no período.

## Cenários e Verificação *(obrigatório)*

### História 1 — O PIX óbvio entra na venda sozinho (Prioridade: P1)

A cliente paga o saldo por PIX no Inter MEI. Em até ~15 minutos o sistema lê o aviso, acha a única venda aberta com
aquele saldo cuja contratante tem o mesmo nome de quem pagou, e registra o pagamento na venda, marcando que entrou no
Inter MEI. A comercial não faz nada: o saldo da venda cai, a cobrança para de aparecer como pendente, e o vendedor é
avisado no sino de que o PIX entrou.

**Por que esta prioridade**: é o caso que tira o trabalho manual da comercial e fecha o buraco de receita sem
registro.

**Verificação**: cenários 1–6 do `verify_318.py`.

**Cenários de aceite**:

1. **Dado** uma venda aberta com saldo de R$ 2.200,00 cuja contratante se chama "Maria Teste Silva", **Quando** chega
   um aviso autenticado do Inter de PIX de R$ 2.200,00 de "Maria Teste Silva", **Então** a venda ganha um pagamento
   de R$ 2.200,00 de origem "PIX · Inter MEI", o saldo vai a zero e o PIX fica "ligado automaticamente".
2. **Dado** o mesmo aviso lido duas vezes (duas rodadas, ou o mesmo e-mail encaminhado), **Quando** o sistema
   processa, **Então** existe um único PIX e um único pagamento.
3. **Dado** uma venda com sinal pendente (nada recebido, valor R$ 4.000,00), **Quando** chega PIX de R$ 2.000,00 do
   mesmo nome da contratante, **Então** liga sozinho como sinal.
4. **Dado** que o pagador "Empresa Teste Ltda" já pagou o sinal desta venda (ligação anterior), **Quando** chega PIX
   do saldo exato de "Empresa Teste Ltda", **Então** liga sozinho mesmo que o nome não bata com a contratante ("já
   pagou antes").
5. **Dado** um aviso **sem** autenticação do Inter (DKIM ausente ou de outro domínio), **Quando** o valor e o nome
   batem, **Então** o PIX **não** liga sozinho: vai para "É esta?" com o alerta "e-mail não autenticado".
6. **Dado** uma venda cancelada ou já quitada com o mesmo valor, **Quando** chega o PIX, **Então** ela não é candidata.

---

### História 2 — Quando há dúvida, um clique resolve: "É esta?" (Prioridade: P1)

Quando o valor bate com mais de uma venda, ou bate só o valor sem o nome, o PIX vai para a fila "PIX para conferir".
O vendedor da venda sugerida e o Financeiro são avisados no sino. Qualquer pessoa da Comercial, do Financeiro ou o
Superadmin abre a fila, vê o PIX (valor, quem pagou, conta, data e hora) e até três vendas sugeridas com o motivo de
cada uma ("valor = saldo", "valor = sinal", "nome bate", "já pagou antes"), e responde com um clique: "É esta",
"Não é esta", "Outra venda…" (busca uma venda aberta) ou "Não é de venda".

**Por que esta prioridade**: sem ela, metade dos PIX (os pagos por outra pessoa) continuaria dependendo de comprovante
manual.

**Verificação**: cenários 7–12 do `verify_318.py`.

**Cenários de aceite**:

1. **Dado** duas vendas abertas com saldo de R$ 1.000,00, **Quando** chega PIX de R$ 1.000,00, **Então** o PIX fica
   "para conferir" com as duas vendas sugeridas, e nada é registrado em venda alguma.
2. **Dado** uma única venda com saldo igual, mas pagador de outro nome e sem histórico, **Quando** chega o PIX,
   **Então** fica "para conferir" com essa venda sugerida ("valor = saldo").
3. **Dado** um PIX para conferir, **Quando** alguém da Comercial clica "É esta" numa sugestão, **Então** o pagamento
   é registrado nessa venda, o PIX fica "confirmado por <nome>", e o próximo PIX do mesmo pagador para a mesma venda
   já liga sozinho.
4. **Dado** um PIX para conferir, **Quando** alguém clica "Não é esta" na única sugestão, **Então** a venda sai das
   sugestões e o PIX sai da fila (fica ignorado).
5. **Dado** um PIX para conferir, **Quando** alguém escolhe "Outra venda…" e uma venda aberta, **Então** o pagamento
   é registrado nela.
6. **Dado** uma pessoa do Casting, **Quando** tenta ler a fila ou responder, **Então** recebe recusa (deve falhar).

---

### História 3 — Nada conta em dobro com os comprovantes manuais (Prioridade: P1)

A comercial pode continuar anexando comprovante. Se ela anexar o comprovante de um PIX que já entrou sozinho, o
sistema pergunta "Esse comprovante é do PIX de R$ X que entrou em DD/MM no Inter MEI?" — "Sim, anexar" junta o arquivo
ao pagamento que já existe; "Não, é outro pagamento" cria um novo. E se o comprovante foi anexado antes de o PIX ser
processado, o PIX se concilia com ele em vez de criar outro.

**Por que esta prioridade**: contar dobrado faria a cobrança parar de cobrar quem ainda deve — pior que hoje.

**Verificação**: cenários 13–16 do `verify_318.py`.

**Cenários de aceite**:

1. **Dado** um pagamento de R$ 1.500,00 criado por PIX (sem arquivo), **Quando** a comercial anexa um comprovante de
   R$ 1.500,00 na mesma venda, **Então** a resposta é "possível duplicata" com o PIX; ao escolher "anexar", o arquivo
   vai para o pagamento existente e o recebido continua R$ 1.500,00.
2. **Dado** o mesmo caso, **Quando** a comercial escolhe "é outro pagamento", **Então** um novo pagamento é criado
   (recebido R$ 3.000,00).
3. **Dado** um comprovante manual de R$ 800,00 já anexado (sem PIX), **Quando** chega o PIX de R$ 800,00 que liga a
   essa venda, **Então** o PIX se concilia com o comprovante existente (marca a conta) e o recebido continua R$ 800,00.
4. **Dado** um comprovante de valor diferente de qualquer PIX da venda, **Quando** é anexado, **Então** o fluxo é o de
   hoje, sem pergunta.

---

### História 4 — Saber em qual conta entrou (Prioridade: P2)

Cada pagamento que veio de PIX fica marcado com a conta que recebeu (Inter MEI, Inter Prime). O comprovante manual
ganha um campo opcional "Conta que recebeu". O Financeiro e o Superadmin veem, na tela de PIX, quanto entrou em cada
conta por mês.

**Por que esta prioridade**: responde a pergunta do contador sobre o MEI; não muda o dia a dia da comercial.

**Verificação**: cenários 17–18 do `verify_318.py`.

**Cenários de aceite**:

1. **Dado** PIX ligados no Inter MEI e no Inter Prime em outubro, **Quando** o Financeiro abre o resumo, **Então** vê
   o total de cada conta em outubro, somando também os comprovantes manuais marcados com a conta.
2. **Dado** um aviso com número de conta não cadastrado, **Quando** é lido, **Então** o PIX entra sem conta e a saúde
   da leitura mostra "conta não cadastrada".

---

### História 5 — "Prime Dreams" no MEI não conta em dobro (Prioridade: P2)

O Inter Prime e a InfinitePay repassam dinheiro ao MEI com o nome "Prime Dreams". O repasse do Inter Prime é dinheiro
de cliente que o sistema já leu na Prime: é reconhecido (mesmo valor de um PIX da Prime, ou a soma de alguns, nos
3 dias anteriores) e ignorado. O que sobra é repasse da InfinitePay: vira "É esta?" — só para o Financeiro e o
Superadmin — com as vendas no cartão/InfinitePay em aberto em que o repasse fica entre 88% e 100% do valor cobrado (a
taxa), de uma venda ou da soma de até três. Nunca liga sozinho. Ao confirmar, a venda que já tem comprovante só
concilia; a que não tem ganha o pagamento pelo valor cobrado da cliente, para a cobrança não ir atrás da taxa.

**Por que esta prioridade**: evita dobrar receita e cobre as vendas no cartão sem trabalho da comercial; o volume é
pequeno (≈3 vendas/mês).

**Verificação**: cenários 19–22 do `verify_318.py`.

**Cenários de aceite**:

1. **Dado** um PIX de R$ 2.127,98 lido na Prime ontem, **Quando** chega no MEI "Prime Dreams" R$ 2.127,98, **Então** o
   repasse é ignorado (transferência entre contas).
2. **Dado** nenhum PIX da Prime que explique o valor, e uma venda no cartão com saldo de R$ 1.000,00, **Quando** chega
   no MEI "Prime Dreams" R$ 950,00, **Então** fica "para conferir" (só Financeiro/Superadmin) com essa venda sugerida.
3. **Dado** esse PIX, **Quando** o Financeiro confirma a venda, **Então** a venda ganha pagamento de R$ 1.000,00 (o
   valor cobrado) e a taxa de R$ 50,00 fica anotada no PIX.
4. **Dado** um repasse que é a soma de duas vendas no cartão, **Quando** o Financeiro marca as duas, **Então** cada
   venda ganha o pagamento do seu saldo.

---

### História 6 — A leitura não para calada (Prioridade: P2)

O Superadmin liga e desliga a leitura, cadastra os números das contas e a lista de "pagadores próprios" (Prime Dreams,
Monta Produções, o nome do sócio). A tela mostra a última leitura, quantos avisos foram lidos, quantos não foram
entendidos e quais contas apareceram nos últimos 7 dias; leitura parada há mais de 1 hora ou erro de acesso à caixa
viram faixa de alerta na tela de PIX.

**Por que esta prioridade**: sem isso a equipe acharia que está coberta quando não está.

**Verificação**: cenários 23–25 do `verify_318.py`.

**Cenários de aceite**:

1. **Dado** a leitura desligada, **Quando** a rodada acontece, **Então** nada é lido nem gravado.
2. **Dado** um e-mail do Inter num formato desconhecido, **Quando** é lido, **Então** conta como "não entendido" na
   saúde e não some calado.
3. **Dado** duas rodadas ao mesmo tempo (três workers), **Quando** disparam, **Então** só uma lê.

### Casos de borda

- PIX de quem está na lista de pagadores próprios (exceto "Prime Dreams" no MEI, que segue a História 5) → ignorado.
- Aviso de devolução ("Pix devolução recebida") → ignorado.
- Venda cancelada depois de o PIX ser ligado → o pagamento segue as regras da 306 (vale o que o núcleo de comprovante
  já faz no cancelado).
- "Desfazer" (Financeiro/Superadmin) num PIX ligado → o pagamento criado pelo PIX é apagado se ainda não tem arquivo;
  se tem arquivo (anexado depois) ou se o PIX só conciliou um comprovante manual, o pagamento fica como comprovante
  manual sem vínculo; em todos os casos o PIX volta para "para conferir".
- PIX que chega antes de a venda ser cadastrada → é comparado de novo a cada leitura por 7 dias; depois, ignorado.
- PIX de valor quebrado que não bate com nada → ignorado (decisão do dono), mas guardado.
- O Inter mudar o texto do e-mail → todos viram "não entendidos", a faixa de alerta aparece, o fluxo manual segue
  funcionando.
- Aviso anterior à data em que a leitura foi ligada → não entra na fila (o passado é coberto pelo ensaio, não pela
  fila).
- Duas vendas do mesmo grupo comercial → a candidata é a venda (o evento líder), nunca o dia.

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: O sistema DEVE ler, a cada ~15 minutos e sem marcar nada na caixa, os e-mails do Inter de "Pix
  recebido" da caixa joao@mantoproducoes.com.br, usando a credencial que já usa para os e-mails devolvidos.
- **FR-002**: O sistema DEVE extrair de cada aviso: valor, nome de quem pagou, número da conta que recebeu, data e
  hora, identificador único do e-mail e se o e-mail é autenticado pelo Inter.
- **FR-003**: O sistema DEVE guardar cada aviso uma única vez (identificador único do e-mail), sem guardar o corpo do
  e-mail.
- **FR-004**: O sistema DEVE ligar o PIX sozinho à venda somente quando há exatamente uma venda aberta cujo valor
  pendente (saldo, sinal de 50%, parcela não recebida ou valor total sem nada recebido) é igual ao PIX ao centavo,
  **e** o nome do pagador bate com a contratante/empresa/outro cliente da venda **ou** esse pagador já teve PIX ligado
  à mesma venda ou cliente, **e** o aviso é autenticado.
- **FR-005**: O sistema DEVE pôr o PIX em "para conferir" quando há candidata(s) que não cumprem o FR-004, com até
  três vendas sugeridas e o motivo de cada uma.
- **FR-006**: O sistema DEVE ignorar (sem fila, sem aviso) o PIX sem candidata, o de pagador próprio e o de devolução;
  o PIX sem candidata DEVE ser comparado de novo a cada leitura durante 7 dias do recebimento.
- **FR-007**: Comercial, Financeiro e Superadmin DEVEM poder responder o "É esta?": confirmar uma sugestão, descartar
  uma sugestão, escolher outra venda aberta ou dizer "não é de venda".
- **FR-008**: Financeiro e Superadmin DEVEM poder desfazer uma ligação (automática ou confirmada).
- **FR-009**: Todo pagamento criado ou conciliado por PIX DEVE registrar a conta que recebeu, a origem "PIX" e quem
  (ou "o sistema") decidiu, com registro no histórico do evento.
- **FR-010**: Ao anexar comprovante manual cujo valor é igual ao de um pagamento de origem PIX sem arquivo na mesma
  venda, o sistema DEVE perguntar se é o mesmo pagamento antes de criar outro.
- **FR-011**: Quando a venda já tem comprovante manual do mesmo valor ainda sem PIX (e não marcado com outra conta),
  o PIX DEVE ir para "É esta?" com as duas saídas — "é o comprovante já anexado" (concilia, não cria outro) e "é
  outro pagamento" —, nunca ligar sozinho: sinal e saldo de 50% têm valor igual (revisão adversarial, 22/10).
- **FR-012**: O sistema DEVE tratar "Prime Dreams" no Inter MEI como descrito na História 5 (repasse da Prime ignorado;
  sobra = "É esta?" só para Financeiro/Superadmin, com vendas no cartão, nunca automático, pagamento pelo valor
  cobrado).
- **FR-013**: O comprovante manual DEVE aceitar, opcionalmente, a conta que recebeu.
- **FR-014**: Financeiro e Superadmin DEVEM ver o total recebido por conta e por mês.
- **FR-015**: O Superadmin DEVE poder ligar/desligar a leitura (nasce desligada), cadastrar o número de cada conta e a
  lista de pagadores próprios; só entram na fila avisos recebidos depois de a leitura ser ligada.
- **FR-016**: A tela DEVE mostrar a saúde da leitura (última leitura, lidos, não entendidos, contas vistas em 7 dias)
  e alertar quando a leitura parou há mais de 1 hora ou deu erro.
- **FR-017**: O sino DEVE avisar o vendedor da venda sugerida e o Financeiro quando um PIX fica para conferir, e o
  vendedor quando um PIX liga sozinho à sua venda; repasse da InfinitePay avisa só Financeiro/Superadmin.
- **FR-018**: A Home da comercial DEVE mostrar quantos PIX estão para conferir, com atalho para a fila.
- **FR-019**: O sistema NÃO DEVE escrever em serviço externo nem alterar a caixa de e-mail (só leitura); no banco
  local de desenvolvimento a leitura nasce desligada.

### Entidades

- **Conta que recebe**: conta bancária da empresa (apelido, tipo de titular MEI/PJ, banco, número da conta, ativa).
  Nasce com Inter MEI, Inter Prime, InfinitePay Prime e Cora Monta, **sem número** (o número não vai para o
  repositório; o Superadmin preenche).
- **PIX recebido**: um aviso lido (identificador do e-mail, valor, pagador, conta, data/hora, autenticado, estado —
  novo, ligado automaticamente, confirmado, para conferir, sem venda, conta própria —, sugestões e descartes, quem
  decidiu, o pagamento ligado).
- **Comprovante de pagamento** (existente): ganha conta que recebeu, origem (comprovante | PIX) e pode existir sem
  arquivo quando a origem é PIX.
- **Configuração** (existente): interruptor e data de início da leitura, marcador da rodada, última leitura, último
  erro, pagadores próprios.

### RBAC

- `GET /api/pix` (fila e ligados recentes, resumo por conta só para FINANCEIRO/SUPERADMIN) — COMERCIAL, FINANCEIRO,
  SUPERADMIN.
- `POST /api/pix/<id>/confirmar`, `/descartar`, `/nao-e-venda` — COMERCIAL, FINANCEIRO, SUPERADMIN; repasse da
  InfinitePay só FINANCEIRO, SUPERADMIN.
- `GET /api/pix/saude` — COMERCIAL, FINANCEIRO, SUPERADMIN; `GET /api/pix/resumo-por-conta` — FINANCEIRO,
  SUPERADMIN.
- `POST /api/pix/<id>/desfazer` — FINANCEIRO, SUPERADMIN.
- `GET/PATCH /api/pix/config` — SUPERADMIN.
- `POST /api/events/<id>/payments` (existente) — mesmos papéis de hoje; ganha a resposta "possível duplicata" e o
  campo opcional de conta.

## Verificação (`verify_318.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/318-pix-recebido-por-email/verify_318.py`, contra `manto_local` (`DATABASE_URL` de `.local-db-url`,
`FLASK_ENV=development`, `MANTO_SEM_THREADS=1`). Login só por `POST /api/auth/login`; escrita conferida por conexão
separada; limpeza no `finally`. Os e-mails são sintéticos (nomes fictícios), montados no verify; a leitura da caixa é
injetada (sem rede).

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | aviso autenticado, valor = saldo, nome bate, venda única | liga sozinho; saldo 0; conta marcada | não |
| 2 | mesmo e-mail duas vezes | um PIX, um pagamento | não |
| 3 | sinal pendente, PIX = metade, nome bate | liga como sinal | não |
| 4 | "já pagou antes" (pagador com PIX ligado à venda) | liga sem nome | não |
| 5 | aviso sem DKIM do Inter | não liga sozinho; "para conferir" com alerta | não |
| 6 | venda cancelada e venda quitada com o mesmo valor | não são candidatas | não |
| 7 | duas vendas com o mesmo saldo | "para conferir" com as duas; nenhum pagamento | não |
| 8 | só o valor bate | "para conferir" | não |
| 9 | Comercial confirma | pagamento criado; estado confirmado; histórico do evento | não |
| 10 | descartar a única sugestão | PIX sai da fila | não |
| 11 | "Outra venda…" | pagamento na venda escolhida | não |
| 12 | Casting lê a fila / responde | 403 | **sim** |
| 13 | comprovante manual igual a pagamento PIX sem arquivo | "possível duplicata"; "anexar" não dobra o recebido | não |
| 14 | mesmo caso, "é outro pagamento" | cria novo | não |
| 15 | PIX chega com comprovante manual igual já existente | concilia, não cria | não |
| 16 | comprovante de valor diferente | fluxo de hoje | não |
| 17 | resumo por conta × mês | soma PIX + manuais marcados | não |
| 18 | conta não cadastrada | PIX sem conta; saúde acusa | não |
| 19 | "Prime Dreams" = PIX da Prime (ou soma) | ignorado | não |
| 20 | "Prime Dreams" sem par, venda no cartão 88–100% | "para conferir" só Financeiro/Superadmin; nunca sozinho | não |
| 21 | Comercial tenta confirmar repasse da InfinitePay | 403 | **sim** |
| 22 | confirmação de duas vendas no cartão | cada uma ganha o seu saldo; taxa anotada | não |
| 23 | leitura desligada / antes da data de início | nada entra na fila | não |
| 24 | formato desconhecido | "não entendido" na saúde | não |
| 25 | duas rodadas simultâneas | só uma lê | não |
| 26 | Comercial tenta "Desfazer" | 403 | **sim** |
| 27 | "Desfazer" pelo Financeiro | sem arquivo: pagamento apagado; com arquivo: vira manual; PIX volta a "para conferir" | não |
| 27b | PIX sem venda; venda cadastrada 2 dias depois / 8 dias depois | liga na próxima leitura / continua ignorado | não |
| 28 | pagamento sem arquivo na página do evento (React e Jinja) e no agente de auditoria | não quebra | não |
| 29 | limpeza | usuários e registros descartáveis apagados (`roles.clear()` antes do usuário) | — |

**Ensaio antes de ligar** (`specs/318-pix-recebido-por-email/ensaio_318.py`): lê a caixa joao@manto de verdade, só
leitura, desde 01/06/2026; roda a regra contra o `manto_local` numa transação desfeita no fim; compara com o gabarito
do cruzamento de 21/10 (`receitas_entradas_classificadas.csv`, caminho por argumento); imprime só contagens. Critério
para ligar: **zero ligação automática errada**.

Conferência de tela: página "PIX recebidos" (fila, ligados, resumo por conta, saúde), linha da Home, painel de
comprovantes do evento (pagamento de origem PIX, "possível duplicata", campo de conta), configurações "PIX por e-mail".

## Critérios de sucesso *(obrigatório)*

- **SC-001**: No ensaio sobre os PIX de 01/06 a 21/10, nenhuma ligação automática diverge do gabarito do cruzamento de
  21/10.
- **SC-002**: Pelo menos um terço dos PIX de venda do ensaio liga sozinho, e a fração cresce com as confirmações.
- **SC-003**: Um PIX de venda entra no saldo da venda em até 20 minutos depois do aviso do banco, sem ação da
  comercial (quando o vínculo é óbvio).
- **SC-004**: Responder um "É esta?" leva um clique a partir da fila.
- **SC-005**: Nenhum pagamento conta em dobro entre PIX e comprovante manual nos cenários do verify.
- **SC-006**: Financeiro vê o total recebido por conta e por mês sem planilha.

## Fora de escopo

- Lista e classificação de "PIX sem venda" (decisão do dono: ignorar; os dados ficam guardados).
- Alerta do teto do MEI (a base — recebido por conta — fica pronta).
- Link de pagamento InfinitePay gerado pelo ERP para cada venda (follow-up recomendado depois da 310).
- Cora e outras contas sem aviso por e-mail; contas pessoais.
- Importação de extrato (CSV/OFX) e id E2E.
- Componente de sugestão compartilhado com a 317 (quem fizer merge por último reaproveita).

## Docs a atualizar

`docs/01` (tabelas novas, colunas, endpoints e linha na tabela de RBAC §4.3, thread nova e config), `docs/02` (tela
"PIX recebidos", painel de comprovantes, configurações, linha da Home), `docs/03` (entrada no topo), `docs/04`
(invariante: recebido = soma dos comprovantes, agora também os de origem PIX; padrão "liga sozinho / É esta?"),
`docs/05` (dívida criada, se houver).

## Premissas

- Venda = evento líder do grupo comercial; universo de candidatas = o mesmo da cobrança (não cancelada, não cortesia,
  fora do ENSAIO e da loja virtual, saldo acima da folga de R$ 1,00).
- "Nome bate" = dois ou mais termos normalizados em comum (sem acento, sem "ltda", "me", "de/da/do"), ou semelhança
  alta, contra contratante, empresa e outros clientes do evento.
- Tolerância de valor ao centavo para ligação; repasse da InfinitePay com o repasse entre ~88% e 100% do valor cobrado.
- A hora do PIX é a do cabeçalho do e-mail, em horário de parede de São Paulo.
- A leitura usa a credencial de e-mail que o sistema já tem; nenhuma variável de ambiente obrigatória nova.
