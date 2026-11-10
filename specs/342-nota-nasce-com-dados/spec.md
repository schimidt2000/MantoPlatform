# Feature 342 — O pedido de nota já nasce com os dados que a emissão exige

**Branch**: `342-nota-nasce-com-dados` (da `main`) · **Created**: 2026-11-10 · **Status**: Pronta (verify 19/19), aguardando merge ·
**Migration**: `d342a7c1e9f3` (aditiva: três colunas e dez linhas de campo de formulário) ·
**Nível**: 1 (feature) — constituição, Princípio VI

**Input**: pedido do dono: "O cliente recebe e preenche um formulário; quando ele marca que precisa
de nota, o formulário deve abrir algumas perguntinhas básicas, sem tomar muito tempo dele, para
informar os dados que a gente precisa. Depois esses dados são puxados automaticamente do formulário
para o pedido de nota, ou o vendedor digita."

## O pedido, nas palavras do dono *(obrigatório)*

Desde 01/11/2026 a empresa emite NFS-e no Emissor Nacional, que exige mais dados que o sistema
antigo. Emitindo duas notas à mão no portal, o dono viu o que **só a cliente sabe**: o CNPJ ou CPF de
quem recebe a nota, se a empresa retém ISS e o texto que precisa constar na descrição (pedido, ordem
de compra). O resto o sistema ou a contadora já sabem.

O sintoma: das 16 notas do painel "Notas a emitir" (feature 323), **só 4 tinham CNPJ ou CPF**. O dono
teve de cobrar a equipe de vendas pelo WhatsApp, nota por nota.

### O que já existe e o que falta

- Os dois formulários públicos (`/f/pre-contrato`, `/f/corporativo`) já pedem o CPF (comum) ou o CNPJ
  (corporativo) e o e-mail da contratante, mas **não perguntam se a cliente precisa de nota**, quem
  recebe a nota, se há retenção de ISS nem a referência.
- O editor de formulários (123) **não tem campo condicional**: "Descreva Outros" aparece por uma
  regra fixa no código.
- Na venda (323), o bloco "Dados da nota" abre com "Precisa de nota fiscal" ligado, mas o documento
  do tomador é **opcional**; o município só existe com ISS retido; não há e-mail da nota.

## Cenários e Verificação *(obrigatório)*

### História 1 — A cliente informa os dados da nota no formulário (Prioridade: P1)

A cliente preenche o formulário de sempre. No fim há uma pergunta: "Preciso de nota fiscal". Marcando,
abrem quatro perguntas curtas, duas delas já preenchidas com o que ela digitou acima (documento e
e-mail). Sem marcar, o formulário é o de hoje.

**Por que esta prioridade**: é a única fonte dos dados que só a cliente tem; sem ela nada chega à venda.

**Verificação**: cenários 1 a 5 do `verify_342.py`.

**Cenários de aceite**:

1. **Dado** o formulário aberto, **Quando** a cliente não marca "Preciso de nota fiscal", **Então** as
   perguntas da nota não aparecem, nenhuma delas é exigida e a resposta é salva como hoje.
2. **Dado** "Preciso de nota fiscal" marcado, **Quando** ela envia sem o CNPJ ou CPF, ou com um
   número que não existe (dígito verificador errado), **Então** o envio é recusado com a mensagem no
   campo, e o que ela digitou continua na tela.
3. **Dado** "Preciso de nota fiscal" marcado e um CNPJ no documento, **Quando** ela olha o formulário,
   **Então** vê a pergunta "A empresa retém o ISS da nota?" com Sim, Não e Não sei; com um CPF, a
   pergunta não aparece e não é exigida.
4. **Dado** as perguntas da nota preenchidas, **Quando** ela desmarca "Preciso de nota fiscal" e
   envia, **Então** as respostas da nota são descartadas (a resposta salva diz só que não precisa).
5. **Dado** o formulário no celular (375 px), **Quando** o bloco da nota abre, **Então** tudo cabe
   sem rolagem lateral e os campos têm área de toque de 44 px.

---

### História 2 — As respostas chegam aos dados da nota da venda (Prioridade: P1)

Quando o formulário é ligado a um evento (sozinho pelo telefone e data, pela vendedora, ou na criação
do evento a partir do formulário), o documento, o e-mail, a retenção de ISS e a referência vão para
os dados da nota da venda, **só onde o campo está vazio**.

**Por que esta prioridade**: é o "puxado automaticamente" do pedido; tira a cobrança por WhatsApp.

**Verificação**: cenários 6 a 10 do `verify_342.py`.

**Cenários de aceite**:

1. **Dado** um evento sem dados da nota e um formulário em que a cliente pediu nota, **Quando** o
   formulário é ligado ao evento, **Então** documento, e-mail, referência e retenção de ISS do evento
   passam a ser os do formulário.
2. **Dado** um evento em que a vendedora já digitou outro documento, **Quando** o formulário é
   ligado, **Então** o documento digitado fica; só os campos vazios se completam.
3. **Dado** um formulário em que a cliente **não** pediu nota, **Quando** é ligado, **Então** nenhum
   dado da nota do evento muda.
4. **Dado** a resposta "Não sei" para a retenção de ISS, **Quando** o formulário é ligado, **Então** a
   venda segue "não retido" (o padrão da contadora) e a vendedora vê que a cliente não soube dizer.
5. **Dado** qualquer formulário ligado, **Quando** a cliente pediu nota, **Então** "Precisa de nota
   fiscal" da venda **não** liga sozinho: ligar muda o preço e avisa o Superadmin; é a vendedora
   quem liga. Na criação do evento a partir do formulário, o chip e os dados vêm sugeridos na tela,
   e é o Salvar da vendedora que grava.

---

### História 3 — Pedir nota exige o CNPJ ou CPF de quem recebe (Prioridade: P1)

A vendedora liga "Precisa de nota fiscal". Se a venda não tem documento (nem digitado, nem vindo do
formulário, nem no cadastro da contratante), o Salvar é recusado com a mensagem no campo.

**Por que esta prioridade**: fecha a torneira das notas sem documento; é a regra que vale mesmo
quando a cliente não preencheu o formulário.

**Verificação**: cenários 11 a 15 do `verify_342.py`.

**Cenários de aceite**:

1. **Dado** uma venda sem nota e sem documento em lugar nenhum, **Quando** a vendedora liga "Precisa
   de nota fiscal" e salva (criação, "Editar tudo" ou card Comercial), **Então** recebe "Informe o
   CNPJ ou CPF de quem recebe a nota." no campo e nada é gravado.
2. **Dado** a mesma venda com o documento no cadastro da contratante, **Quando** ela salva com o
   campo em branco, **Então** o pedido é aceito (vale o do cadastro, como hoje).
3. **Dado** um documento digitado com dígito verificador errado, **Quando** ela salva, **Então**
   recebe "CNPJ ou CPF inválido. Confira os números." no campo.
4. **Dado** um pedido de nota antigo, que já existia sem documento, **Quando** alguém salva outra
   coisa no evento (horário, elenco), **Então** a gravação passa: a regra vale para pedido novo e
   para quem tenta apagar um documento que existia, não trava o trabalho de quem não vende.
5. **Dado** a vendedora olhando os dados da nota de um evento com formulário, **Quando** o bloco
   abre, **Então** vê o que a cliente respondeu (documento, e-mail, retenção, referência) para
   conferir, com os campos já preenchidos por essas respostas.

---

### História 4 — O município do evento vem sugerido (Prioridade: P2)

Para o serviço da casa (17.10) o ISS é devido na cidade do evento. O bloco "Dados da nota" mostra
sempre o campo "Município do evento", já preenchido com a cidade tirada do endereço do formulário ou
do endereço do evento; a vendedora confere e salva. O painel do Superadmin mostra o município, e
quando ninguém confirmou ainda, mostra a sugestão marcada como tal.

**Por que esta prioridade**: evita erro de incidência, mas a nota sai sem isso (o Superadmin confere
o endereço no portal).

**Verificação**: cenários 16 e 17 do `verify_342.py`.

**Cenários de aceite**:

1. **Dado** um evento com endereço "…, Sorocaba - SP, 18000-000", **Quando** o bloco abre, **Então**
   o município vem "Sorocaba - SP" e é gravado quando a vendedora salva.
2. **Dado** um município já gravado, **Quando** o endereço do evento muda, **Então** o gravado fica.
3. **Dado** um endereço de onde não se tira cidade, **Quando** o bloco abre, **Então** o campo vem
   vazio e continua obrigatório só com ISS retido (regra da 323).

---

### História 5 — O Superadmin configura campo condicional no editor (Prioridade: P3)

No editor de formulários, um campo personalizado pode ser marcado "Aparece só quando [campo] for
[valor]". Os campos da nota já nascem assim e não podem ser excluídos.

**Verificação**: cenário 18 do `verify_342.py`.

**Cenários de aceite**:

1. **Dado** um campo personalizado, **Quando** o Superadmin escolhe "Aparece só quando Forma de
   pagamento for Outros" e salva, **Então** o formulário público só mostra e só exige o campo nessa
   condição.
2. **Dado** uma condição que aponta para um campo inexistente ou para o próprio campo, **Quando**
   ele salva, **Então** recebe o erro no campo.

### Casos de borda

- **Cliente pede nota e a venda foi fechada sem nota**: nada liga sozinho; o bloco da venda mostra
  "A cliente pediu nota fiscal no formulário." para a vendedora decidir.
- **Dois formulários no mesmo evento**: vale o primeiro que preencher cada campo vazio; a tela mostra
  as respostas do mais recente que pediu nota.
- **Formulário desligado do evento**: os dados já levados ficam (podem ter sido conferidos); a
  vendedora apaga se quiser.
- **Evento cancelado**: o vínculo já é recusado (312); nada chega.
- **Evento de vários dias (satélite)**: os dados da nota são da venda, que mora no principal; ligado
  a um dia satélite, o formulário não escreve dados de nota.
- **Resposta antiga** (anterior a esta feature): não tem as perguntas; nada muda.
- **Bundle antigo com servidor novo** (minutos do deploy): o formulário antigo não manda as perguntas
  da nota; como a pergunta-mãe é opcional, o envio passa como "não precisa".
- **Documento do formulário diferente do cadastro**: a nota pode ir para um terceiro; o cadastro da
  cliente não é alterado por este caminho (ele já se completa pelo CPF/CNPJ do formulário, 119).

## Requisitos *(obrigatório)*

### Requisitos funcionais

**Formulário público**

- **FR-001**: Os dois formulários DEVEM ter, numa seção "Nota fiscal" no fim, a pergunta opcional
  "Preciso de nota fiscal" (marcar = sim).
- **FR-002**: Com a pergunta marcada, o formulário DEVE mostrar: (a) CNPJ ou CPF de quem recebe a
  nota, obrigatório; (b) e-mail para receber a nota, obrigatório; (c) "A empresa retém o ISS da
  nota?" com Sim, Não e Não sei, obrigatória e exibida só quando (a) é um CNPJ; (d) o que precisa
  constar na nota (pedido, ordem de compra), opcional, até 120 caracteres.
- **FR-003**: O documento DEVE ser validado pelo tamanho (11 ou 14 dígitos) e pelos dígitos
  verificadores, na tela e no servidor.
- **FR-004**: Ao abrir o bloco, documento e e-mail DEVEM vir preenchidos com o CPF/CNPJ e o e-mail já
  digitados acima, editáveis; nunca sobrescrevem o que a cliente já digitou no bloco.
- **FR-005**: Campo condicional escondido NÃO DEVE ser exigido, e o valor que tenha ficado nele DEVE
  ser descartado no servidor.
- **FR-006**: O formulário NÃO DEVE perguntar código de serviço, alíquota nem endereço do tomador.

**Campo condicional (editor)**

- **FR-007**: Um campo DEVE poder declarar "aparece só quando o campo X tem o valor V"; X é um campo
  de seleção ou de sim/não do mesmo formulário, diferente dele mesmo.
- **FR-008**: O editor DEVE permitir definir e limpar a condição em campo personalizado e mostrá-la
  na lista; em campo do sistema a condição é só leitura.
- **FR-009**: Os campos da nota DEVEM ser do sistema (não se excluem); texto, ajuda e ordem seguem
  editáveis como nos demais.

**Do formulário para a venda**

- **FR-010**: Ao ligar um formulário a um evento principal vivo, por qualquer caminho, o sistema DEVE
  copiar para os dados da nota da venda, **só nos campos vazios**: documento, e-mail, referência e
  retenção de ISS (Sim/Não; "Não sei" não grava). Formulário sem pedido de nota não copia nada.
- **FR-011**: O sistema NÃO DEVE ligar "Precisa de nota fiscal" por causa do formulário, nem criar
  pedido de nota, nem avisar o Superadmin.
- **FR-012**: Na criação de evento a partir do formulário, a tela DEVE vir com "Precisa de nota
  fiscal" e os dados da nota sugeridos quando a cliente pediu nota.
- **FR-013**: O detalhe do evento DEVE trazer o que a cliente respondeu sobre a nota (do formulário
  ligado mais recente que pediu nota) para a tela mostrar ao lado dos campos.

**Venda**

- **FR-014**: Salvar com "Precisa de nota fiscal" ligado DEVE ser recusado, com a mensagem no campo do
  documento, quando não houver documento na venda nem no cadastro da contratante **e** (a) o pedido
  está nascendo nesta gravação, ou (b) a gravação apagaria o documento que a venda tinha. Vale nas
  três portas: criação, "Editar tudo" e card Comercial.
- **FR-015**: Documento digitado na venda DEVE passar pela validação de dígitos verificadores.
- **FR-016**: A venda DEVE guardar o e-mail para envio da nota; o painel "Notas a emitir" mostra esse
  e-mail e, sem ele, o do cadastro (como hoje).
- **FR-017**: O município do evento DEVE poder ser gravado com ou sem ISS retido; continua
  obrigatório só com ISS retido.
- **FR-018**: O sistema DEVE sugerir o município a partir (1) da cidade e do estado do formulário
  ligado, (2) do endereço do evento; a sugestão só vira dado gravado quando alguém salva o bloco.
- **FR-019**: O painel "Notas a emitir" DEVE mostrar o município gravado ou, sem ele, a sugestão
  identificada como "a confirmar".
- **FR-020**: Nada desta feature DEVE alterar a emissão direta (329) nem os campos que ela lê
  (`is_outside_sp`, ISS retido, documento): os dados continuam nos mesmos lugares, só chegam mais
  preenchidos.

### Entidades *(se houver dados)*

- **Evento (venda)**: ganha o e-mail da nota; o município deixa de depender do ISS retido; a
  retenção passa a distinguir "não informado" de "não".
- **Definição de campo de formulário**: ganha a condição de exibição (campo e valor).
- **Resposta de formulário**: sem mudança de estrutura; as perguntas novas entram no JSON de seções
  com chave estável.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

Nenhum endpoint novo. Alterados, com os gates de hoje:

- `GET /api/formularios/<tipo>/schema`, `POST /api/formularios/<tipo>` — públicos.
- `POST/PATCH /api/formularios/campos…` (editor) — Superadmin.
- `POST /api/events`, `PATCH /api/events/<id>`, `PATCH /api/events/<id>/comercial` — os gates da
  venda (Comercial, Financeiro, Superadmin onde já valem).
- `GET /api/events/<id>` — `venda.nota` segue dentro do bloco que só o papel de venda recebe.
- `GET /api/dashboard` (painel Notas a emitir) — Superadmin.

## Verificação (`verify_342.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/342-nota-nasce-com-dados/verify_342.py`, contra o espelho local (`DATABASE_URL` de
`.local-db-url` ou do espelho próprio da feature, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`).
Login só por `POST /api/auth/login`; escrita conferida por conexão separada; limpeza no `finally`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Schema público dos dois formulários | perguntas da nota presentes, com a condição | não |
| 2 | Envio sem pedir nota, com lixo nos campos da nota | 201; valores da nota descartados | não |
| 3 | Envio pedindo nota sem documento | 400 com `fields` no documento | **sim** |
| 4 | Envio pedindo nota com CNPJ de dígito errado | 400 | **sim** |
| 5 | Envio com CPF sem responder ISS (201) e com CNPJ sem responder ISS (400) | ISS só para CNPJ | **sim** (2ª metade) |
| 6 | Ligar formulário com nota a evento vazio | documento, e-mail, referência e ISS no evento | não |
| 7 | Ligar a evento com documento digitado | o digitado fica; vazios completam | não |
| 8 | Ligar formulário sem nota | nenhum `nota_*` muda | não |
| 9 | Resposta "Não sei" | `nota_iss_retido` segue nulo; detalhe mostra "Não sei" | não |
| 10 | Depois de ligar | `with_invoice` igual, nenhuma nota a emitir criada | não |
| 11 | Card Comercial: ligar nota sem documento em lugar nenhum | 400 `nota_tomador_doc`; banco igual | **sim** |
| 12 | Idem com documento no cadastro da contratante | 200 | não |
| 13 | Documento com dígito errado na venda | 400 | **sim** |
| 14 | Pedido antigo sem documento, salvar outra coisa | 200 | não |
| 15 | Criação e "Editar tudo" sem documento | 400 nas duas | **sim** |
| 16 | Sugestão de município pelo endereço e pelo formulário | "Sorocaba - SP"; funções puras com casos-limite | não |
| 17 | Gravar município sem ISS retido | fica gravado; painel mostra | não |
| 18 | Editor: condição válida grava; inválida 400; papel sem permissão 403 | campo condicional | **sim** |
| 19 | Limpeza | registros descartáveis apagados | — |

Conferência de tela: `/f/pre-contrato` e `/f/corporativo` em 375×812 (bloco fechado, aberto com CPF,
aberto com CNPJ, erro); card Comercial e "Editar tudo" do evento (bloco com as respostas do
formulário, erro de documento, município sugerido); painel "Notas a emitir"; editor de formulários.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Toda nota pedida a partir da entrega chega ao painel com CNPJ ou CPF (hoje: 4 de 16).
- **SC-002**: A cliente que precisa de nota responde o bloco em menos de um minuto: no caso comum,
  confere dois campos já preenchidos e responde no máximo duas perguntas.
- **SC-003**: A cliente que não precisa de nota não vê nenhuma pergunta a mais além da primeira.
- **SC-004**: Nenhum dado de nota digitado pela equipe é trocado por resposta de formulário.
- **SC-005**: Nenhuma gravação que hoje passa em evento com pedido de nota antigo deixa de passar.

## Fora de escopo

- Emissão direta (329) e qualquer mudança no que ela lê ou grava.
- Enviar a nota por e-mail à cliente (o e-mail fica guardado para quem emite).
- Código de serviço, alíquota, competência e endereço do tomador (o portal completa pelo CNPJ).
- Alíquota de retenção por cidade.
- Consultar a Receita para validar se o CNPJ existe.
- Preencher em lote as 12 notas pendentes sem documento (a vendedora digita; o formulário novo só
  vale para respostas novas).
- Trocar a regra fixa de "Descreva Outros" pela condição nova.

## Docs a atualizar

`docs/01` (colunas novas, contrato do schema público, `venda.nota`, tabela de gates sem mudança),
`docs/02` (formulário público, bloco Dados da nota, editor), `docs/03` (entrada no topo), `docs/04`
(§Formulários: campo condicional e o caminho formulário → dados da nota; §Agenda: regra do
documento), `docs/05` (dívida: `descreva_outros` segue fixo; cadeia de migrations com 329/CRM).

## Premissas

- Vale para os dois formulários (comum e corporativo).
- A pergunta-mãe é uma caixa de marcar opcional: um toque para quem precisa, nenhum para quem não.
- Padrão da contadora: "não retido". "Não sei" não muda a venda, só aparece para a vendedora.
- Formato do município: "Cidade - UF", o mesmo do campo atual.
- A regra do documento não é retroativa: os pedidos antigos sem documento continuam editáveis.
- O formulário nunca liga "Precisa de nota fiscal" na venda existente, porque isso muda o preço.
