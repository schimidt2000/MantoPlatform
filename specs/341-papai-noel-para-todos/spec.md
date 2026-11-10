<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Feature 341 — O Papai Noel liga para qualquer idade, e o vídeo tem data de entrega

**Branch**: `341-papai-noel-para-todos` (da `340-caixa-de-avisos` em `d01ce070`, worktree
`C:\tmp\mp341`) · **Created**: 2026-11-10 · **Status**: Rascunho · **Migration**: aditiva
(`virtual_campaigns.recorded_delivery_until`) · **Nível**: 1 (feature) — migration; constituição,
Princípio VI

**Input**: pedido do dono (10/11/2026), com a loja já no ar:

## O pedido, nas palavras do dono *(obrigatório)*

> "Preciso de um ajuste apenas na comunicação ali, porque beleza, a maioria das pessoas vai contratar
> para criança, só que ela pode contratar, por exemplo, para uma avó, um adulto, então acho que a gente
> precisa alterar esse texto aí, porque não deixar tão focado em criança. Mas também que serve para
> criança, entende?"

> "E uma outra coisa é que os vídeos serão entregues até o dia 13 do 12. Ou seja, são 7 dias após o
> dia 6, entendeu? Então acho que pode colocar direto, que é até dia 13 do 12."

**Como está hoje.** A loja fala só de criança: "Nome da criança", "o Papai Noel liga para a sua
criança", "E se a criança ficar com vergonha?", "Criança" na página do pedido, "os dados da criança"
no e-mail. Quem compra para a avó preenche "Nome da criança" com o nome dela. A idade já aceita
adulto (0 a 120). O vídeo diz "entregue em até 7 dias", e o prazo interno de cada vídeo é
"pagamento + 7 dias": um vídeo comprado em 15/11 vence em 22/11 na Fila de Produção, embora a equipe
grave depois de 06/12.

**Já feito, sem código (10/11, pela tela da campanha, no ar):** a apresentação e os termos da
campanha do Papai Noel falam de "quem você quer surpreender: a criança da casa, a vovó, o padrinho…"
e de entrega do vídeo "até 13 de dezembro". O que sobra é o texto fixo do código e a data.

## Cenários e Verificação *(obrigatório)*

### História 1 — A loja convida para qualquer idade, com a criança ainda no centro (Prioridade: P1)

Quem chega à loja entende que pode reservar para a criança da casa e também para a avó, o padrinho
ou um adulto. A cartinha continua lá, como o momento da criança. Nenhum rótulo obriga a escrever o
nome da avó em "Nome da criança".

**Por que esta prioridade**: é o pedido principal, e a loja já está vendendo.

**Verificação**: cenários 1–3 do `verify_341.py` (textos que o servidor envia: e-mails, mensagens de
erro, descrição do evento) e tela aberta da campanha e do pedido em 375×812 (textos do site).

**Cenários de aceite**:

1. **Dado** a página da campanha, **Quando** a família lê o topo, os formatos, a ficha e as perguntas
   frequentes, **Então** o texto fala de "quem vai receber" e cita criança e adulto, e há uma pergunta
   "É só para criança?" respondida.
2. **Dado** a ficha, **Quando** a família vai preencher o nome, **Então** o rótulo é "Nome de quem
   vai receber"; a idade continua aceitando adulto.
3. **Dado** o e-mail de compra da chamada ao vivo, **Quando** chega, **Então** ele lembra da
   cartinha "se for uma criança" e não diz "dados da criança".
4. **Dado** a página do pedido e o e-mail do vídeo pronto, **Quando** abertos, **Então** não
   dizem "Criança" nem "sua criança".

---

### História 2 — O vídeo tem data de entrega, e a equipe vê o prazo certo (Prioridade: P1)

A campanha ganha "Entrega dos vídeos até" na tela de gestão. Com a data preenchida (13/12/2026), a
página diz "entregue até 13 de dezembro", o e-mail de compra diz "até 13/12/2026", e o prazo do vídeo
na Fila de Produção e na página do pedido é 13/12 — não "pagamento + 7 dias". Sem a data, tudo segue
como hoje.

**Por que esta prioridade**: sem isso, a Fila de Produção alarmaria prazo vencendo em novembro para
vídeos que só serão gravados depois de 06/12.

**Verificação**: cenários 4–8 do `verify_341.py`.

**Cenários de aceite**:

1. **Dado** a campanha com entrega até 13/12/2026, **Quando** um vídeo é pago em 15/11, **Então** o
   prazo da entrega é 13/12/2026.
2. **Dado** a mesma campanha, **Quando** um vídeo é pago depois de 13/12, **Então** vale "pagamento +
   dias" (a data não pode virar prazo no passado).
3. **Dado** a campanha sem data, **Quando** um vídeo é pago, **Então** o prazo é "pagamento + dias",
   como hoje.
4. **Dado** a gestão da campanha, **Quando** o Superadmin preenche ou apaga a data e salva, **Então**
   ela grava e volta na tela; data inválida → erro no campo.
5. **Dado** a API pública da campanha, **Quando** lida, **Então** traz `recorded_delivery_until`
   (data ou nulo).

### Casos de borda

- Campanha com vídeo esgotado (capacidade 0, o caso de hoje): o texto do cartão "esgotado" também
  mostra a data; nada quebra.
- Data de entrega já passada na hora do pagamento: prazo "pagamento + dias" (história 2.2).
- Bundle velho com backend novo (deploy): o campo novo da API é opcional no React (armadilha 21 do
  `docs/00`).
- O e-mail de vídeo pronto usa o primeiro nome no assunto; nada muda nele além do preheader.

## Requisitos *(obrigatório)*

### Requisitos funcionais

**Texto (Princípio XV, site público: caloroso e claro)**

- **FR-001**: O texto fixo da loja (`lojaTema.ts`, página da campanha, página do pedido) DEVE falar
  de "quem vai receber"/"quem você escolher", citar criança e adulto onde apresenta a loja, e manter a
  cartinha como o momento da criança ("se for uma criança…").
- **FR-002**: As perguntas frequentes da loja DEVEM ganhar "É só para criança?" com resposta que diz
  que a maioria é para criança e que adulto também pode receber.
- **FR-003**: O rótulo do nome na ficha DEVE ser "Nome de quem vai receber"; a página do pedido
  mostra "Para" no lugar de "Criança".
- **FR-004**: Os e-mails da loja DEVEM trocar "dados da criança" e "vídeo da sua criança" por texto
  sem idade; o da chamada ao vivo mantém a cartinha condicionada ("se for uma criança").
- **FR-005**: As mensagens de erro da ficha (`child_name`, `child_age`) DEVEM dizer "Informe o nome de
  quem vai receber." e "Informe a idade."; a descrição do evento da venda no Google diz "Para:".
- **FR-006**: As telas internas que mostram o pedido (Fila de Produção, seção do pedido no evento)
  DEVEM dizer "Para" no lugar de "Criança".
- **FR-007**: Chaves de API e de banco (`child_name`, `child_age`) NÃO mudam (Princípio XV).

**Data de entrega do vídeo**

- **FR-008**: `virtual_campaigns` DEVE ganhar `recorded_delivery_until` (data, opcional), editável na
  gestão da campanha ("Entrega dos vídeos até"), aceita no `POST`/`PATCH` da campanha (data
  `AAAA-MM-DD` ou vazio) com erro no campo quando inválida.
- **FR-009**: O prazo do vídeo pago DEVE ser `recorded_delivery_until` quando preenchida e a data do
  pagamento não passou dela; senão, pagamento + `recorded_delivery_days`. Uma função só decide.
- **FR-010**: A API pública e a da gestão DEVEM trazer `recorded_delivery_until` (ISO ou nulo).
- **FR-011**: A página da campanha DEVE mostrar "entregue até 13 de dezembro" com a data, senão
  "entregue em até N dias"; o e-mail de compra do vídeo mostra a data do prazo da entrega
  (`dd/mm/aaaa`).

### Entidades

- **VirtualCampaign** ganha `recorded_delivery_until` (Date, nulo). Migration à mão, aditiva, sobre
  `e340c1a2b3d4`.

### RBAC

- Nenhum endpoint novo. `POST`/`PATCH /api/virtuais/campanhas*` seguem em `require_virtuais_access`
  (Comercial e Superadmin); o campo novo segue o mesmo gate.

## Verificação (`verify_341.py`) *(obrigatório — Princípio VIII)*

Contra o `manto_340` (já na migration da 340; exceção registrada no `plan.md` da 340), com
`DATABASE_URL` de `.local-db-url`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`; e-mails capturados
(nada sai); limpeza no `finally`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Erro da ficha sem nome / sem idade | "Informe o nome de quem vai receber." / "Informe a idade." | não |
| 2 | E-mail de compra ao vivo e de vídeo | sem "criança" fora da cartinha condicionada; ao vivo com "cartinha"; vídeo sem | não |
| 3 | Descrição do evento da venda | "Para: <nome>, N anos", sem "Criança:" | não |
| 4 | Prazo com data, pago antes | `due_date` = data da campanha | não |
| 5 | Prazo com data, pago depois | `due_date` = pagamento + dias | não |
| 6 | Prazo sem data | `due_date` = pagamento + dias | não |
| 7 | Gestão grava, limpa e recusa data inválida | 200 / 200 / 400 com `fields.recorded_delivery_until` | inválida **sim** |
| 8 | API pública e e-mail de compra do vídeo | `recorded_delivery_until` no JSON; e-mail com `dd/mm/aaaa` | não |
| 9 | limpeza | campanha e pedidos descartáveis apagados | — |

Regressão: `verify_304.py` (cartinha na apresentação e no e-mail ao vivo), `verify_205.py`.
Tela: campanha e pedido em 375×812; gestão da campanha (campo novo).

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Nenhum texto que a família lê na loja obriga a escrever o nome de um adulto num campo
  "da criança".
- **SC-002**: Com a data preenchida, todo vídeo vendido até ela aparece na Fila de Produção com
  prazo 13/12, e a página e o e-mail dizem a mesma data.

## Fora de escopo

- Renomear `child_name`/`child_age` (chave de API e coluna).
- Abrir vagas de vídeo (capacidade continua decisão da equipe na tela).
- Texto de outras estações (princesas): a regra nova vale para elas pela mesma redação.

## Docs a atualizar

`docs/01` §2 (coluna nova) e §3.13.4 (campo nas rotas da campanha); `docs/02` (página da campanha,
pedido e gestão); `docs/03` (entrada); `docs/04` §Loja Virtual (prazo do vídeo).

## Premissas

- O tom é o do site público (constituição §XV): pode "a gente", uma exclamação, nada de gíria.
- O prazo interno vale só para vídeos pagos depois do deploy; vídeo já pago mantém o prazo gravado
  (hoje não há nenhum: capacidade 0).
