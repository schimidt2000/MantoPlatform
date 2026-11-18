# Feature 353 — Gasto extra parcelado: um gasto, várias datas de pagamento

**Branch**: `353-gasto-extra-parcelado` (da `352-fornecedores-gastos-extras`, que ainda não está na `main`: as
duas mexem na mesma tela e sobem juntas) · **Created**: 2026-11-17 · **Status**: Em produção (17/11 ~22h52; verify 11/11) · **Migration**:
`f353a1b2c3d4` (aditiva — tabela nova das parcelas) · **Nível**: 1 (feature: migration, tela e Planilha de
Pagamentos) — constituição, Princípio VI

**Input**: pedido do dono: "vou colocar um gasto para o Adão, só que esse gasto ele pode ser parcelado. Então, uma
parte tem que pagar no dia 20, outra parte no dia 30. Seria interessante eu já poder cadastrar num único gasto
extra."

## O pedido, nas palavras do dono *(obrigatório)*

> "Uma outra melhoria que eu gostaria de colocar aí nessa página do gasto extra é que, por exemplo, vou colocar um
> gasto para o Adão, só que esse gasto ele pode ser parcelado. Então, uma parte tem que pagar no dia 20, outra parte
> no dia 30. Seria interessante eu já poder cadastrar num único gasto extra. E aí, quando vai aprovar, eu edito, tudo
> mais, eu posso alterar essas coisas. [...] Por exemplo, o pagamento para Rosângela, já tem as datas certas, eu vou e
> coloco quais são as datas, os valores em cada data, e é isso. E o comprovante não precisa ser para cada um deles
> não, pode ser para o gasto extra como um todo."

Hoje um gasto extra tem uma data e um valor e vira **um** item na Planilha de Pagamentos, na data do gasto. Pagamento
parcelado obriga a lançar vários gastos (com a nota fiscal repetida em cada um) ou a lembrar de cabeça das datas.

Decisões do dono (17/11, antes da spec):

1. **DRE**: o gasto parcelado entra inteiro no resultado do mês da "Data do gasto" (competência), como hoje. As
   parcelas só dizem quando cada pagamento sai na Planilha de Pagamentos.
2. **Valor**: o total do gasto é a soma das parcelas, calculada sozinha.
3. **Parcela paga trava**: parcela paga (ou "no banco") não muda nem sai ao editar o gasto; as que faltam seguem
   editáveis. Para corrigir uma paga, desmarca-se na planilha primeiro.

## Cenários e Verificação *(obrigatório)*

### História 1 — Lançar o gasto em parcelas (Prioridade: P1) 🎯

Quem lança o gasto (qualquer papel que lança gasto hoje), com "Reembolso a funcionário" ou "Pagamento a fornecedor",
marca **"Pagar em parcelas"**. Aparecem duas linhas de parcela (data e valor), com "Adicionar parcela" e a opção de
remover cada uma. O campo do valor do gasto passa a mostrar o total, que é a soma das parcelas e não se digita. A nota
fiscal é uma só, a do gasto. Ao salvar, o gasto nasce pendente como hoje, com as parcelas guardadas.

**Por que esta prioridade**: é o pedido. Sem ela nada mais existe.

**Verificação**: cenários 1 e 2 do `verify_353.py`.

**Cenários de aceite**:

1. **Dado** um gasto a "Adão Lima da Silva" com "Pagar em parcelas" marcado, **Quando** a pessoa informa R$ 500,00
   em 20/11 e R$ 700,00 em 30/11 e salva, **Então** o gasto fica com valor R$ 1.200,00, duas parcelas, uma nota
   fiscal e a situação "Aguardando aprovação".
2. **Dado** "Pagar em parcelas" marcado, **Quando** a pessoa salva com uma parcela sem data ou com valor zero,
   **Então** nada é salvo e a parcela com problema é apontada.
3. **Dado** "Pagar em parcelas" marcado, **Quando** a pessoa deixa uma parcela só, **Então** nada é salvo e a tela
   diz que parcelado precisa de pelo menos duas parcelas.

---

### História 2 — Cada parcela é paga na sua data, na Planilha de Pagamentos (Prioridade: P1)

Aprovado, o gasto parcelado aparece na Planilha de Pagamentos como **um item por parcela**, cada um na sua data, com o
valor da parcela, quem recebe, a chave PIX e a indicação "Parcela 1 de 2". Cada item é marcado pago (ou "no banco")
sozinho, inclusive nas ações em lote e na lista de atrasados. Em Gastos Extras, a situação do gasto acompanha as
parcelas: "A pagar" enquanto falta pagar alguma, "No banco" quando nenhuma falta e alguma está no banco, "Pago" quando
todas estão pagas.

**Por que esta prioridade**: é o motivo de parcelar: o pagamento sai na data certa e o Financeiro vê o que falta.

**Verificação**: cenários 3, 4 e 5 do `verify_353.py`.

**Cenários de aceite**:

1. **Dado** o gasto de R$ 1.200,00 aprovado, com parcelas em 20/11 e em 30/11, **Quando** o Financeiro abre a Planilha
   de novembro, **Então** vê dois itens (R$ 500,00 em 20/11 e R$ 700,00 em 30/11), e não um de R$ 1.200,00.
2. **Dado** uma parcela em 05/12, **Quando** o Financeiro abre a Planilha de novembro, **Então** ela não aparece; na de
   dezembro, aparece.
3. **Dado** os dois itens, **Quando** o Financeiro marca o de 20/11 como pago, **Então** só ele fica pago e o gasto
   segue "A pagar" em Gastos Extras; marcando o segundo, o gasto passa a "Pago".
4. **Dado** um gasto **não** parcelado, **Então** a Planilha mostra um item só, como hoje.

---

### História 3 — Alterar as parcelas ao editar e aprovar (Prioridade: P1)

Ao editar (o Financeiro, inclusive em "Salvar e aprovar"), as parcelas aparecem preenchidas. Dá para alterar data e
valor das que faltam pagar, remover parcela, adicionar parcela e desmarcar "Pagar em parcelas" (volta a ser um
pagamento só). A parcela paga ou "no banco" aparece travada, com a situação ao lado, e não pode ser alterada nem
removida. O total acompanha.

**Por que esta prioridade**: o dono disse que ajusta na hora de aprovar.

**Verificação**: cenários 6, 7 e 8 do `verify_353.py`.

**Cenários de aceite**:

1. **Dado** o gasto parcelado pendente, **Quando** o Financeiro troca a segunda parcela para R$ 800,00 em 01/12 e
   aprova, **Então** o gasto fica com R$ 1.300,00, aprovado, e a Planilha mostra a parcela nova.
2. **Dado** a primeira parcela já paga, **Quando** o Financeiro tenta alterar o valor dela ou removê-la, **Então** nada
   muda e a tela diz que a parcela paga só muda depois de desmarcada na Planilha.
3. **Dado** a primeira parcela paga, **Quando** o Financeiro adiciona uma terceira parcela, **Então** ela entra a pagar
   e o total cresce.
4. **Dado** um gasto parcelado sem parcela paga, **Quando** o Financeiro desmarca "Pagar em parcelas" e informa o
   valor, **Então** o gasto volta a ser um pagamento só, na data do gasto.

---

### História 4 — Ver as parcelas no gasto (Prioridade: P2)

Na lista de Gastos Extras, o gasto parcelado mostra as parcelas: data, valor e situação de cada uma ("20/11 · R$
500,00 · Pago", "30/11 · R$ 700,00 · A pagar").

**Por que esta prioridade**: sem isso, quem lançou só vê o total e não sabe o que já saiu.

**Verificação**: tela aberta (Browser pane).

**Cenários de aceite**:

1. **Dado** o gasto com a primeira parcela paga, **Quando** a pessoa olha o gasto na lista, **Então** vê as duas
   parcelas com a situação de cada uma.

### Casos de borda

- **Gasto sem desembolso** ("Sem desembolso definido"): não há pagamento a fazer, então "Pagar em parcelas" não
  aparece.
- **Devolução à cliente** (nasce do cancelamento, feature 306) não se parcela por aqui.
- **"Já pago no cadastro"** (`paid_at_creation`, feature 128) e parcelas não combinam: recusado.
- **Gasto rejeitado ou pendente**: nenhuma parcela aparece na Planilha (como o gasto inteiro hoje).
- **Gasto excluído**: as parcelas vão junto.
- **Parcela fora do mês da "Data do gasto"**: permitido; a parcela segue a sua data na Planilha, o gasto segue a "Data
  do gasto" na DRE.
- **Datas repetidas**: permitido (dois pagamentos no mesmo dia).
- **Desmarcar "Pagar em parcelas" com parcela paga**: recusado — o pagamento já saiu como parcela.
- **Parcela paga e desmarcada na Planilha**: volta a ser editável.
- **Limite**: até 24 parcelas.
- **Gasto do auditor de marketing** (reembolso de anúncios): não parcela; nada muda.

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: Um gasto extra com desembolso (reembolso a funcionário ou pagamento a fornecedor) DEVE poder ser
  cadastrado com 2 a 24 parcelas, cada uma com data e valor maior que zero.
- **FR-002**: O valor do gasto parcelado DEVE ser a soma das parcelas, calculada pelo sistema (não digitada).
- **FR-003**: O gasto parcelado DEVE ter uma única nota fiscal, como o gasto não parcelado.
- **FR-004**: A DRE e o custo do evento DEVEM continuar contando o gasto inteiro pela "Data do gasto" — parcelar não
  muda o mês do resultado.
- **FR-005**: Aprovado, o gasto parcelado DEVE aparecer na Planilha de Pagamentos como um item por parcela, na data da
  parcela, com o valor dela, quem recebe, a chave PIX e "Parcela N de M"; o gasto não parcelado continua um item só.
- **FR-006**: Cada parcela DEVE ser marcada paga, "no banco" ou não paga sozinha, inclusive nas ações em lote e nos
  atrasados da Planilha.
- **FR-007**: A situação do gasto parcelado em Gastos Extras DEVE ser derivada das parcelas: "A pagar" se alguma não
  foi paga; "No banco" se nenhuma falta e alguma está no banco; "Pago" se todas foram pagas.
- **FR-008**: Ao editar (Financeiro e Superadmin, como hoje), as parcelas não pagas DEVEM poder ter data e valor
  alterados, ser removidas e receber novas; a parcela paga ou "no banco" NÃO pode ser alterada nem removida.
- **FR-009**: Desmarcar "Pagar em parcelas" DEVE voltar o gasto a um pagamento só, desde que nenhuma parcela tenha sido
  paga ou esteja no banco.
- **FR-010**: Na lista de Gastos Extras, o gasto parcelado DEVE mostrar cada parcela com data, valor e situação.
- **FR-011**: Erros de parcela (sem data, valor zero, menos de duas, parcela paga alterada) DEVEM ser apontados na
  parcela, sem apagar o que foi digitado.

### Entidades *(se houver dados)*

- **Parcela do gasto** (nova): o gasto a que pertence, número (1..N), data de pagamento, valor e situação de pagamento
  (não paga | no banco | paga). Some com o gasto.
- **Gasto extra** (existente): o valor passa a ser a soma das parcelas quando parcelado; a "Data do gasto" continua a
  competência; a situação de pagamento do gasto acompanha as parcelas.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

- `POST /api/gastos` — gate inalterado (qualquer usuário logado); passa a aceitar as parcelas.
- `PATCH /api/gastos/<id>` — gate inalterado (Financeiro, Superadmin); passa a aceitar as parcelas.
- Marcar a situação de pagamento na Planilha — gate inalterado (Financeiro, Superadmin); passa a aceitar o item
  parcela.

Os gates não mudam, então o `docs/01` §4.3 não ganha linha; o contrato novo fica no §3 (Planilha e §3.7).

## Verificação (`verify_353.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/353-gasto-extra-parcelado/verify_353.py`, contra o espelho próprio (exceção da 352: o `manto_local`
é compartilhado com as sessões 348–351), com `FLASK_ENV=development` e `MANTO_SEM_THREADS=1`. Login só por
`POST /api/auth/login` (um FIGURINO e um FINANCEIRO descartáveis); escrita conferida por conexão separada; limpeza no
`finally`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Figurino lança gasto com 2 parcelas | valor = soma; 2 parcelas gravadas; 1 nota | não |
| 2 | Parcela sem data, valor zero, uma parcela só, parcelado + "já pago" | 400 apontando a parcela/campo; nada gravado | não |
| 3 | Aprovado: Planilha do mês | um item por parcela, na data dela, "Parcela N de M"; gasto não parcelado segue um item | não |
| 4 | Parcela no mês seguinte | fora da Planilha do mês do gasto, dentro da do mês dela | não |
| 5 | Marcar parcela paga / no banco (e em lote) | só ela muda; situação do gasto derivada | não |
| 6 | Financeiro altera parcela não paga e aprova | valor e Planilha seguem | não |
| 7 | Alterar ou remover parcela paga | 409/400 apontando a parcela; nada muda | não |
| 8 | Desmarcar parcelas sem parcela paga / com parcela paga | volta a um pagamento / recusado | não |
| 9 | DRE do mês do gasto | soma o gasto inteiro pela "Data do gasto" | não |
| 10 | Figurino tenta editar parcelas ou marcar parcela paga | 403, nada muda | **sim** |
| 11 | limpeza | gastos, parcelas e usuários descartáveis apagados | — |

Conferência de tela: formulário de gasto (criar e editar com parcela paga travada) em 390 px e desktop; a lista de
Gastos Extras com as parcelas; a Planilha de Pagamentos com os itens de parcela.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Um pagamento em N parcelas se lança uma vez, com uma nota fiscal, em vez de N gastos.
- **SC-002**: Na Planilha de Pagamentos, cada parcela aparece no dia em que tem de ser paga — nenhum pagamento
  parcelado aparece inteiro na data do gasto.
- **SC-003**: O resultado do mês (DRE) de um gasto parcelado é igual ao do mesmo gasto não parcelado.
- **SC-004**: Nenhuma parcela já paga muda de valor ou data por edição do gasto.

## Fora de escopo

- Comprovante de pagamento por parcela (o comprovante é o do gasto; o que a Planilha já guarda por item segue igual).
- Gerar parcelas iguais automaticamente ("dividir em N vezes") — as datas e valores são informados.
- Parcelar gastos recorrentes (eles já têm o "pagamento programado", feature 121).
- Parcelar a devolução à cliente e o gasto do auditor de marketing.
- Mudar a DRE para regime de caixa.

## Docs a atualizar

`docs/01` (tabela nova, contrato de `POST/PATCH /api/gastos`, itens da Planilha, §4.3), `docs/02` (formulário de
gasto, lista e Planilha de Pagamentos), `docs/03` (entrada no topo), `docs/04` §Financeiro/Gastos (parcela na Planilha,
gasto na DRE).

## Premissas

- O gasto não parcelado não muda em nada (um item na Planilha, na "Data do gasto").
- A "Data do gasto" segue obrigatória no parcelado: é a competência (DRE) e a data mostrada na lista.
- A situação de pagamento gravada no próprio gasto passa a acompanhar as parcelas, para quem já lê esse campo
  (auditor financeiro, relatórios) continuar certo.
- Quem lança gasto também lança parcelado (o gate do `POST /api/gastos` não muda); editar segue com Financeiro e
  Superadmin.
