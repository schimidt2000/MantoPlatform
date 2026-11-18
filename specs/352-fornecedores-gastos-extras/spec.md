# Feature 352 — Fornecedores cadastrados nos gastos extras: digitar três letras preenche nome, PIX e categoria

**Branch**: `352-fornecedores-gastos-extras` (da `main`) · **Created**: 2026-11-17 · **Status**: Em produção (17/11 ~23h; verify 11/11) ·
**Migration**: `f352a1b2c3d4` (aditiva — tabela nova e coluna nova; reescreve o nome do fornecedor nos
gastos antigos ligados, por isso é ensaiada em banco descartável com dump fresco) · **Nível**: 1
(feature: migration, endpoint novo, tela nova) — constituição, Princípio VI

**Input**: pedido do dono: "Quando vou fazer 1 gasto extra, já tem meio que um banco de fornecedores
que sempre faço. Seria legal se tivesse um auto preenchimento com um banco de fornecedores
cadastráveis. Relacionados aos gastos extras."

## O pedido, nas palavras do dono *(obrigatório)*

> "Quando vou fazer 1 gasto extra, já tem meio que um banco de fornecedores que sempre faço. Seria
> legal se tivesse um auto preenchimento com um banco de fornecedores cadastráveis. Relacionados aos
> gastos extras."

Hoje, no gasto extra com "Pagamento a fornecedor", nome e chave PIX são digitados à mão toda vez. Em
produção (17/11) são 83 gastos a fornecedor com **65 grafias** para **41 fornecedores**: o
mesmo costureiro aparece como "ADAO", "ADÃO", "ADÃO LIMA da SILVA" e "ADÃO LIMA DA SILVA"; a gráfica
como "Thunder Print 3D", "THUNDER PRINT" e "THUNDER PRINT 3D"; o coordenador como "Will", "Will
Coordenador" e "William Castro". Somar quanto se pagou a um fornecedor exige adivinhar as grafias.

Decisões do dono (17/11, antes da spec):

1. **Quem cadastra**: qualquer pessoa que lança gasto extra cadastra fornecedor novo na hora, sem sair
   do formulário. Corrigir nome, PIX e categoria, juntar duplicados e arquivar fica com Financeiro e
   Superadmin, numa tela própria.
2. **Histórico**: o cadastro nasce com os fornecedores já digitados, juntando as grafias do mesmo
   fornecedor; "o que estiver parecido você julga e já junta e arruma". Os gastos antigos ficam
   ligados ao fornecedor.
3. **O que preenche**: escolher o fornecedor preenche nome, chave PIX e categoria (a categoria pode ser
   trocada no gasto).

## Cenários e Verificação *(obrigatório)*

### História 1 — Escolher o fornecedor preenche o gasto (Prioridade: P1)

Quem lança um gasto extra (qualquer papel que lança gasto hoje) marca "Pagamento a fornecedor" e
começa a digitar o nome. A lista mostra os fornecedores cadastrados que casam com o que foi digitado
(sem ligar para acento ou maiúscula), cada um com a chave PIX e a categoria padrão na segunda linha.
Ao tocar num fornecedor, o nome, a chave PIX e a categoria do gasto são preenchidos; a pessoa ainda
pode trocar a categoria e a chave PIX daquele gasto antes de salvar. O gasto salvo fica ligado ao
fornecedor.

**Por que esta prioridade**: é o pedido. Sozinha, já elimina a redigitação do PIX e das grafias para
os 41 fornecedores que já existem.

**Verificação**: cenários 2, 4 e 5 do `verify_352.py`.

**Cenários de aceite**:

1. **Dado** o fornecedor "Thunder Print 3D" cadastrado com PIX e categoria Marketing, **Quando** a
   pessoa digita "thun" no campo do fornecedor, **Então** a sugestão "Thunder Print 3D" aparece com o
   PIX e "Marketing" na segunda linha.
2. **Dado** a sugestão escolhida, **Quando** a pessoa salva o gasto, **Então** o gasto guarda o nome e
   o PIX do fornecedor, a categoria Marketing e o vínculo com o fornecedor.
3. **Dado** a sugestão escolhida, **Quando** a pessoa troca a categoria para "Outros" antes de salvar,
   **Então** o gasto é salvo como "Outros" e o fornecedor continua com Marketing como padrão.
4. **Dado** um fornecedor arquivado, **Quando** quem não é Financeiro digita o nome dele, **Então** ele
   não aparece nas sugestões.

---

### História 2 — Fornecedor novo se cadastra ao salvar o gasto (Prioridade: P1)

A pessoa digita um nome que não está no cadastro. O campo avisa, abaixo dele, que o fornecedor é novo
e ficará salvo para os próximos gastos. Ao salvar o gasto, o fornecedor nasce com o nome, a chave PIX
e a categoria daquele gasto, e o gasto fica ligado a ele. Se o nome digitado só difere de um
fornecedor existente por acento, maiúscula, espaço ou pontuação ("adao" × "Adão"), o gasto liga ao
fornecedor existente e nenhum fornecedor novo é criado.

**Por que esta prioridade**: sem isso o cadastro só cresce pela tela do Financeiro e volta a ter
grafias soltas. Decisão 1 do dono.

**Verificação**: cenários 2, 3 e 4 do `verify_352.py`.

**Cenários de aceite**:

1. **Dado** que "Gráfica Nova" não existe, **Quando** a pessoa salva um gasto a "Gráfica Nova" com PIX
   e categoria Marketing, **Então** o fornecedor "Gráfica Nova" passa a existir com esse PIX e categoria
   e o gasto fica ligado a ele.
2. **Dado** o fornecedor "Adão Lima da Silva", **Quando** a pessoa salva um gasto digitando "ADAO LIMA
   DA SILVA" sem escolher a sugestão, **Então** o gasto liga ao fornecedor existente e nenhum
   fornecedor novo é criado.
3. **Dado** um fornecedor cadastrado **sem** chave PIX, **Quando** um gasto ligado a ele é salvo com
   uma chave PIX, **Então** o fornecedor passa a ter essa chave (o cadastro se completa).
4. **Dado** um fornecedor cadastrado **com** chave PIX, **Quando** um gasto ligado a ele é salvo com
   outra chave, **Então** o gasto guarda a chave digitada e o cadastro **não** muda (só o Financeiro
   corrige o cadastro).

---

### História 3 — O cadastro nasce com o histórico, juntado e arrumado (Prioridade: P1)

Na publicação, o sistema lê os gastos a fornecedor já lançados, junta as grafias do mesmo fornecedor
(mesma chave PIX, ou mesmo nome sem acento, maiúscula, espaço e pontuação) e cria um fornecedor por
grupo, com o nome arrumado, a chave PIX mais recente do grupo e a categoria mais usada nele. Todos os
gastos a fornecedor antigos ficam ligados ao seu fornecedor e passam a exibir o nome arrumado. A chave
PIX gravada em cada gasto antigo **não** muda.

**Por que esta prioridade**: sem o histórico o autocompletar nasce vazio e o primeiro mês reproduz as
grafias de hoje. Decisão 2 do dono.

**Verificação**: cenário 1 do `verify_352.py` (sobre o espelho com o dump fresco).

**Cenários de aceite**:

1. **Dado** os gastos "ADAO", "ADÃO", "ADÃO LIMA da SILVA" e "ADÃO LIMA DA SILVA", **Quando** a
   importação roda, **Então** existe um único fornecedor "Adão Lima da Silva", e os cinco gastos estão
   ligados a ele e exibem esse nome.
2. **Dado** "Aluguel Sonic e knuckles" e "Real produções / Ramon Rossi" com a mesma chave PIX, **Quando**
   a importação roda, **Então** os dois viram o mesmo fornecedor.
3. **Dado** "Talita" e "Talita Stefani de castro (Will Castro)" com chaves PIX diferentes, **Quando** a
   importação roda, **Então** continuam dois fornecedores.
4. **Dado** uma devolução à cliente (desembolso "cliente"), **Quando** a importação roda, **Então** ela
   não vira fornecedor nem é ligada a um.
5. **Dado** a importação concluída, **Então** nenhum gasto a fornecedor fica sem vínculo.

---

### História 4 — Financeiro arruma o cadastro (Prioridade: P2)

Financeiro e Superadmin têm a tela "Fornecedores", que lista todos (ativos e arquivados) com busca,
chave PIX, categoria padrão, quantos gastos e quanto já foi aprovado para cada um, e a data do último
gasto. Nela é possível cadastrar um fornecedor sem lançar gasto, alterar nome, PIX e categoria padrão,
arquivar e reativar, e juntar um fornecedor duplicado com outro: os gastos do duplicado passam para o
fornecedor escolhido e o duplicado deixa de existir.

**Por que esta prioridade**: o cadastro aberto a todos (História 2) vai gerar duplicados que a regra de
grafia não pega ("Peterson" × "Peterson Caminhão"); sem a tela, eles só se corrigem no banco.

**Verificação**: cenários 6, 7, 8 e 9 do `verify_352.py`.

**Cenários de aceite**:

1. **Dado** o fornecedor "Marcelo" com 2 gastos, **Quando** o Financeiro o renomeia para "Marcelo
   Lima", **Então** os 2 gastos passam a exibir "Marcelo Lima".
2. **Dado** um fornecedor com gastos já pagos, **Quando** o Financeiro troca a chave PIX dele, **Então**
   os gastos já lançados mantêm a chave com que foram lançados; só os próximos usam a nova.
3. **Dado** "Peterson" (1 gasto) e "Peterson (caminhão)" (1 gasto), **Quando** o Financeiro junta
   "Peterson" com "Peterson (caminhão)", **Então** os 2 gastos ficam ligados a "Peterson (caminhão)",
   exibem esse nome, e "Peterson" deixa de existir.
4. **Dado** um nome já usado por outro fornecedor (inclusive só com acento ou maiúscula diferentes),
   **Quando** o Financeiro tenta renomear ou cadastrar com esse nome, **Então** a tela aponta no campo
   do nome que esse fornecedor já existe e nada é salvo.
5. **Dado** quem não é Financeiro nem Superadmin, **Quando** tenta alterar, juntar ou arquivar pela API,
   **Então** recebe 403 e nada muda.

### Casos de borda

- **Duas pessoas cadastram o mesmo fornecedor novo ao mesmo tempo**: o banco aceita um nome normalizado
  uma vez só; o segundo salvamento liga ao fornecedor que o primeiro criou, sem erro para quem salvou.
- **Escolher uma sugestão e depois alterar o texto do nome**: a escolha se desfaz; vale o nome digitado
  (que liga pelo nome ou cadastra um fornecedor novo). A chave PIX e a categoria já preenchidas ficam
  como estão no formulário.
- **Nome digitado igual ao de um fornecedor arquivado**: o gasto liga ao arquivado (não nasce
  duplicado) e ele continua arquivado — reativar é decisão do Financeiro.
- **Gasto passa de "fornecedor" para "reembolso" ou "sem desembolso" numa edição**: o vínculo com o
  fornecedor sai do gasto.
- **Devolução à cliente** (desembolso "cliente", feature 224/306): usa os mesmos campos de nome e PIX,
  mas nunca liga a fornecedor, nem cria um, nem aparece na importação.
- **Multa de cancelamento** (feature 306): também é desembolso "fornecedor", mas quem recebe é o
  artista da escala. Nunca liga a fornecedor, nem cadastra o artista, nem entra na importação
  (encontrado ao atualizar o `docs/01`; produção não tinha multa em 17/11).
- **Fornecedor juntado com ele mesmo**, ou com um que não existe: recusado com mensagem no campo.
- **Categoria padrão**: só as categorias que a pessoa escolhe no formulário do gasto; "Devolução a
  cliente" e "Multa de cancelamento" (que nascem só pelo cancelamento) nunca são categoria padrão.
- **Gasto lançado por automação** (o auditor de marketing lança reembolso, não fornecedor): não muda.
  Os únicos que gravam gasto são `gastos_ops` (tela e API) e `cancel_ops` (devolução e multa); a tela
  Jinja de gastos não existe mais (corrigido no `/speckit-converge`).

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: O sistema DEVE manter um cadastro de fornecedores com nome, chave PIX (opcional),
  categoria padrão (opcional), situação (ativo ou arquivado), quem cadastrou e quando.
- **FR-002**: O sistema DEVE impedir dois fornecedores cujo nome só difira por acento, maiúscula,
  espaço ou pontuação — pela própria base de dados, não só pela tela.
- **FR-003**: O campo do fornecedor no gasto extra ("Pagamento a fornecedor") DEVE sugerir os
  fornecedores ativos enquanto a pessoa digita, ignorando acento e maiúscula, e mostrar a chave PIX e
  a categoria padrão de cada sugestão.
- **FR-004**: Escolher uma sugestão DEVE preencher o nome, a chave PIX e (quando o fornecedor tem) a
  categoria do gasto; os três continuam editáveis antes de salvar.
- **FR-005**: Ao salvar um gasto a fornecedor, o sistema DEVE ligá-lo ao fornecedor escolhido; sem
  escolha, ao fornecedor de mesmo nome normalizado; sem nenhum, DEVE cadastrar o fornecedor com o nome,
  a chave PIX e a categoria do gasto. Ligado, o gasto passa a exibir o nome como está no cadastro
  (quem digitou "ADAO LIMA DA SILVA" vê "Adão Lima da Silva").
- **FR-006**: Ao ligar um gasto a um fornecedor sem chave PIX ou sem categoria padrão, o sistema DEVE
  completar o que falta com o que veio no gasto; nunca DEVE substituir o que o cadastro já tem.
- **FR-007**: O gasto DEVE guardar o nome e a chave PIX com que foi lançado (a Planilha de Pagamentos
  paga para a chave do gasto); uma correção de chave PIX no cadastro NÃO altera gastos já lançados.
- **FR-008**: Renomear um fornecedor DEVE atualizar o nome exibido em todos os gastos ligados a ele.
- **FR-009**: Financeiro e Superadmin DEVEM ter uma tela "Fornecedores" com busca, cadastro, alteração
  de nome, PIX e categoria padrão, arquivar e reativar, e a contagem de gastos, o total aprovado e a
  data do último gasto de cada fornecedor.
- **FR-010**: Financeiro e Superadmin DEVEM poder juntar um fornecedor com outro: os gastos passam para
  o fornecedor que fica, com o nome dele; o que fica completa chave PIX e categoria que não tinha; o
  outro deixa de existir. A ação pede confirmação.
- **FR-011**: A migration DEVE importar os fornecedores dos gastos a fornecedor existentes, juntando
  por chave PIX normalizada ou nome normalizado, com o nome arrumado decidido nesta feature, a chave PIX
  mais recente do grupo e a categoria mais usada; DEVE ligar todos esses gastos e gravar neles o nome
  arrumado, sem tocar na chave PIX de nenhum gasto.
- **FR-012**: Quem não é Financeiro nem Superadmin vê só fornecedores ativos e sem os totais; alterar,
  cadastrar pela tela, juntar e arquivar respondem 403 para esses papéis.

### Entidades *(se houver dados)*

- **Fornecedor** (`fornecedores`, novo): nome (até 200), nome normalizado (único), chave PIX (até 120,
  opcional), categoria padrão (opcional), ativo, quem cadastrou, quando foi cadastrado e alterado. —
  modelo em `app/models.py`, migration à mão.
- **Gasto extra** (`special_expenses`, existente): ganha o vínculo opcional com o fornecedor (apagar o
  fornecedor nunca apaga o gasto). `supplier_name`/`supplier_pix` continuam sendo o que a Planilha de
  Pagamentos, a DRE e o auditor financeiro leem.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

- `GET /api/gastos/fornecedores` — qualquer usuário logado (é quem lança gasto); Financeiro e
  Superadmin recebem também os arquivados e os totais.
- `POST /api/gastos/fornecedores` — Financeiro, Superadmin (403 para os demais; eles cadastram pelo
  próprio gasto).
- `PATCH /api/gastos/fornecedores/<id>` — Financeiro, Superadmin (nome, PIX, categoria, arquivar e
  reativar).
- `POST /api/gastos/fornecedores/<id>/juntar` — Financeiro, Superadmin.
- `POST /api/gastos` e `PATCH /api/gastos/<id>` (existentes) — gate inalterado; passam a aceitar
  `fornecedor_id`.

Linhas na tabela de `docs/01` §4.3.

## Verificação (`verify_352.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/352-fornecedores-gastos-extras/verify_352.py`, contra o espelho próprio `manto_352`
(dump de produção de 17/11; exceção registrada no `plan.md` — o `manto_local` é compartilhado com
as sessões 348–351), com `FLASK_ENV=development` e `MANTO_SEM_THREADS=1`. Login só por `POST /api/auth/login`
com usuários descartáveis (um FINANCEIRO, um FIGURINO); escrita conferida por conexão separada;
limpeza no `finally`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Importação | todo gasto `fornecedor` ligado; nenhum `cliente` ligado; grupos de mesma chave PIX normalizada no mesmo fornecedor; nomes normalizados únicos | não |
| 2 | Figurino cria gasto a nome novo | fornecedor nasce com nome, PIX e categoria; gasto ligado | não |
| 3 | Figurino cria gasto com o mesmo nome em outra grafia | liga ao existente, nenhum fornecedor a mais | não |
| 4 | Gasto com `fornecedor_id` a fornecedor sem PIX / com PIX | completa o vazio; não troca o existente; gasto guarda o PIX digitado | não |
| 5 | `GET` como Figurino × Financeiro | Figurino: só ativos, sem totais; Financeiro: arquivados e totais | não |
| 6 | Financeiro renomeia e troca PIX | gastos ligados mudam de nome; PIX dos gastos não muda | não |
| 7 | Financeiro junta A com B | gastos de A em B com o nome de B; A apagado; B completa o PIX | não |
| 8 | Nome duplicado (cadastro e renome) e juntar consigo mesmo | 400 com `fields.nome` / `fields.destino_id`; nada gravado | não |
| 9 | Figurino tenta `PATCH`, `POST` e `juntar` | 403, nada muda | **sim** |
| 10 | Gasto passa de fornecedor para reembolso | vínculo sai | não |
| 11 | limpeza | gastos, fornecedores e usuários descartáveis apagados (`roles.clear()` antes do usuário) | — |

Conferência de tela: formulário de gasto extra (criar e editar) e a tela "Fornecedores", no Browser
pane, em 390px (o app interno é usado como app instalado no celular) e em desktop.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Lançar um gasto a um fornecedor já usado exige digitar no máximo 3 letras e um toque para
  ter nome, chave PIX e categoria preenchidos — zero redigitação de PIX.
- **SC-002**: Depois da publicação, os 83 gastos a fornecedor (65 grafias, produção em 17/11) aparecem
  sob 41 fornecedores (ensaio no dump de 17/11), e nenhum gasto a fornecedor fica sem fornecedor.
- **SC-003**: Nenhum fornecedor novo nasce duplicado por diferença de acento, maiúscula, espaço ou
  pontuação.
- **SC-004**: O Financeiro responde "quanto já aprovamos para o fornecedor X e quando foi o último
  gasto" numa única tela, sem somar grafias.

## Fora de escopo

- Ligar o "Orçamento de fornecedor" do pedido de figurino (feature 225) ao cadastro — o campo segue
  texto livre.
- Dados fiscais do fornecedor (CNPJ/CPF como campo próprio, endereço, telefone) e nota fiscal por
  fornecedor.
- Excluir fornecedor: duplicado se junta, fornecedor fora de uso se arquiva.
- Alterar a chave PIX dos gastos já lançados ao corrigir o cadastro (inclusive dos não pagos).
- Gastos recorrentes (`RecurringExpense`) e reembolsos a funcionário.
- Separar um fornecedor que a importação juntou (os grupos foram conferidos um a um nesta feature).

## Docs a atualizar

`docs/01` (schema `fornecedores` + coluna `special_expenses.fornecedor_id`, endpoints, §4.3 RBAC),
`docs/02` (tela "Fornecedores" e o campo do fornecedor em Gastos Extras), `docs/03` (entrada no topo),
`docs/04` §Financeiro/Gastos (o gasto guarda nome e PIX do lançamento; o cadastro completa, não
substitui).

## Premissas

- Os gates novos seguem o resto de Gastos: decidem pelo papel real, e o "Ver como" não muda o que a
  tela de Fornecedores mostra nem o que a API aceita (`docs/00` §4).
- A importação inclui gastos rejeitados: o fornecedor existiu ("Eduardo" só tem um gasto, rejeitado);
  o Financeiro arquiva se não quiser vê-lo nas sugestões.
- O PIX do fornecedor aparece para quem lança gasto (qualquer papel com Gastos Extras): é o que permite
  o preenchimento automático que o dono escolheu (decisão 3).
- A busca das sugestões é local: a lista de fornecedores ativos (dezenas) vem uma vez e o filtro roda
  no navegador, sem requisição por tecla.
- Chave PIX normalizada para juntar grafias: com "@", em minúsculas; sem "@", só os dígitos (CPF,
  CNPJ e telefone digitados com ou sem pontuação viram a mesma chave).
- O nome arrumado de cada grupo da importação foi decidido nesta feature a partir das grafias de
  produção em 17/11 (tabela no `plan.md`, só nomes — chave PIX e documento não vão para o repositório).
  Grafia que surgir em produção até a publicação cai na regra geral: a grafia mais usada do grupo, e no
  empate a mais recente.
- A categoria padrão importada é a mais usada nos gastos do grupo (empate: a do gasto mais recente).
