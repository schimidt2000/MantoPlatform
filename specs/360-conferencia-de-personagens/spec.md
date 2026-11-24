# Feature 360 — Conferência de personagens do catálogo: a leitura das fotos é conferida dentro do sistema, com o progresso salvo

**Branch**: `360-conferencia-de-personagens` (da `main`) · **Created**: 2026-11-24 · **Status**: Pronta na branch, sem merge (verify 18/18 no espelho `manto_360`; tela conferida a 390×844 e em tela larga) ·
**Migration**: `f360a1b2c3d4` (aditiva — duas tabelas novas, sem carga de dados e sem tocar tabela
existente) · **Nível**: 1 (feature: migration, endpoint novo, tela nova) — constituição, Princípio VI

**Input**: pedido do dono: "Lembra que estávamos fazendo uma organização do catálogo por personagens?
Quero passar para a Gabi fazer a verificação manual." e, depois de ver em que pé estava: "Sim, prepara.
Pode até ser dentro do sistema e salvando progresso. Precisa ser atual em produção."

## O pedido, nas palavras do dono *(obrigatório)*

Em 09/11/2026 uma leitura assistida das fotos passou por todos os itens do catálogo que não têm
elenco nem ficha de figurino e propôs, para cada um: o tipo do item (tema, dupla, avulso ou genérico),
os personagens individuais que aparecem (nome, a foto da galeria e o recorte de cada um, a ficha de
figurino que parece ser a dele e um aviso quando o leitor ficou em dúvida) ou, quando o item não tem
elenco, a ação proposta ("ligar o item direto à ficha X", "fica sem elenco").

O resultado, 343 itens e 703 personagens propostos, só existe numa página solta no computador do dono.
Essa página não guarda o progresso (fechou a aba, perdeu tudo), só deixa desmarcar (não há onde
escrever o nome certo nem trocar a ficha) e devolve o resultado como um texto para colar numa conversa.
Mais da metade dos nomes tem algum aviso, e vários são palpite.

O dono quer passar essa conferência para a Maria Gabriella, que é Superadmin. Para isso a conferência
precisa morar dentro do sistema, salvar cada decisão e mostrar sempre a fila verdadeira: na produção de
24/11 os 343 itens lidos seguem pendentes e há 13 itens novos, criados depois da leitura (lidos em
24/11, antes desta spec fechar). Quatro dos 343 já são a página própria de um personagem de outro tema
(Moana, Rapunzel, Soldadinhos Verde, Senhor do Tempo) e por isso não entram na fila: sobram 352.

## Clarifications

### Session 2026-11-24

Rodada em modo autônomo: o dono pediu o mínimo de confirmações, então cada pergunta foi respondida com
a opção recomendada. Todas podem ser revistas por ele antes do merge.

- Q: Marcar um item como conferido já grava os personagens no catálogo? → A: Não. A conferência só
  registra decisões; gravar no catálogo é a feature seguinte (FR-014, "Fora de escopo").
- Q: Quem pode conferir além do Superadmin? → A: Ninguém. Só o Superadmin, como na gestão do catálogo
  (FR-015).
- Q: Um item pendente que nunca foi lido pode ser conferido à mão nesta tela? → A: Não. Ele aparece
  como "Sem leitura", só informativo, com o caminho para o cadastro do catálogo (FR-003).
- Q: Um item já conferido aceita alteração direta? → A: Não. É preciso reabrir; a alteração direta é
  recusada (FR-009).
- Q: Quem confere pode escolher outra foto ou redesenhar o recorte? → A: Não. Marca "Criar sem foto" e
  a foto fica como pendência para o marketing (FR-004, "Fora de escopo").

## Cenários e Verificação *(obrigatório)*

### História 1 — Conferir um item e não perder o que foi feito (Prioridade: P1)

A Maria Gabriella abre "Conferência de personagens" no catálogo. Vê quantos itens faltam e a fila.
Em cada item ela vê as fotos da galeria, o tipo que a leitura propôs, a nota do leitor e, para cada
personagem proposto, o recorte, o nome, a ficha sugerida e o aviso. Ela decide o que vale e marca o
item como conferido. Tudo o que ela toca é salvo na hora. Ela fecha o celular no item 80, abre o
computador no dia seguinte e continua do 81.

**Por que esta prioridade**: sem progresso salvo ninguém confere 352 itens; é o motivo do pedido.

**Verificação**: cenários 3, 4 e 9 do `verify_360.py` — decisões gravadas e lidas de volta por
conexão separada; o item conferido sai de "A conferir" e o contador anda.

**Cenários de aceite**:

1. **Dado** um item do tipo tema com seis personagens propostos, **Quando** ela marca um deles como
   "Não criar" e fecha a tela, **Então** ao reabrir, em qualquer aparelho, o personagem continua
   marcado como "Não criar".
2. **Dado** um item avulso com a ação "Ligar o item direto à ficha 412 Coringa", **Quando** ela marca
   o item como conferido, **Então** o item sai de "A conferir", o contador de conferidos sobe em 1 e o
   item passa a mostrar quem conferiu e quando.
3. **Dado** um item já conferido, **Quando** alguém tenta alterar um personagem dele, **Então** a
   alteração é recusada com a instrução de reabrir o item, e nada muda.
4. **Dado** um item conferido por engano, **Quando** ela escolhe "Reabrir", **Então** o item volta para
   "A conferir" com todas as decisões que já tinha.

---

### História 2 — A fila é a verdade da produção (Prioridade: P1)

A fila mostra exatamente os itens que hoje estão pendentes no catálogo: ativos, sem ficha de figurino
própria, sem nenhum personagem cadastrado e que não são a página própria de um personagem de outro
tema (esse item já está organizado: a ficha é do personagem). Se alguém cadastrar o elenco de um item direto no catálogo,
ele some da fila e dos contadores na consulta seguinte, sem ninguém avisar. Se alguém criar um item
novo no catálogo, ele aparece na fila como "Sem leitura", contado à parte, para ninguém achar que a
conferência terminou quando ainda há item que não foi lido.

**Por que esta prioridade**: o dono pediu "precisa ser atual em produção". Conferir item que já foi
resolvido é trabalho jogado fora; esconder item novo é deixar buraco no catálogo.

**Verificação**: cenários 5, 6 e 7 do `verify_360.py` — item que ganha personagem, ficha própria ou é
desativado some da fila; item pendente sem leitura aparece como "Sem leitura"; os contadores batem com
a regra calculada por conexão separada.

**Cenários de aceite**:

1. **Dado** um item na fila, **Quando** ele ganha um personagem no catálogo (ou uma ficha própria, ou é
   desativado), **Então** ele não aparece mais na fila nem nos contadores.
2. **Dado** um item que saiu da fila e tinha decisões salvas, **Quando** ele volta a ficar pendente,
   **Então** reaparece com as decisões que tinha.
3. **Dado** um item pendente que nunca foi lido, **Quando** a fila é aberta, **Então** ele aparece como
   "Sem leitura", com o caminho para a página dele no catálogo, e não entra no total "a conferir".

---

### História 3 — Carregar a leitura sem estragar o que já foi conferido (Prioridade: P1)

A leitura entra no sistema por uma ação explícita do Superadmin, "Carregar leitura". A carga pode ser
repetida quantas vezes for preciso (por exemplo, quando chegar a leitura de itens novos): ela só
acrescenta os itens que ainda não têm leitura e nunca altera um item que já tem.

**Por que esta prioridade**: sem a carga a tela nasce vazia; e uma carga que sobrescreve apagaria dias
de conferência.

**Verificação**: cenários 1, 2 e 8 do `verify_360.py` — primeira carga cria os registros; a segunda
não muda nada (comparação por conexão separada); item com decisão humana fica intacto.

**Cenários de aceite**:

1. **Dado** o sistema sem nenhuma leitura carregada, **Quando** o Superadmin aciona "Carregar leitura",
   **Então** os itens lidos que existem no catálogo passam a ter proposta e a tela informa quantos
   itens e quantos personagens entraram.
2. **Dado** a leitura já carregada e itens já conferidos, **Quando** a carga é acionada de novo,
   **Então** nenhum item existente muda e a tela informa que não havia nada novo.
3. **Dado** uma leitura que cita um item que não existe mais, uma foto que saiu da galeria ou uma ficha
   que foi excluída, **Quando** a carga roda, **Então** ela não falha: o item inexistente é ignorado e
   contado, o personagem com foto ausente entra como "sem foto" e a ficha ausente entra como "sem
   ficha", os dois com aviso.

---

### História 4 — Corrigir o que a leitura errou (Prioridade: P2)

A leitura erra nomes, troca fichas e às vezes escolhe um recorte ruim. Quem confere corrige no próprio
cartão: escreve o nome certo, troca a ficha por outra (ou tira), decide "Criar" ou "Não criar", marca
"Criar sem foto" quando o recorte não presta (fica a pendência de foto para o marketing), acrescenta um
personagem que a leitura não viu, corrige o tipo do item quando a leitura classificou errado (um tema
que na verdade é genérico) e deixa uma observação no personagem ou no item.

**Por que esta prioridade**: 534 dos 612 personagens da leitura grande têm aviso. Sem como corrigir, a
conferência vira uma lista de "está errado" que alguém teria de reinterpretar depois.

**Verificação**: cenários 10 a 14 do `verify_360.py` — cada correção gravada e conferida por conexão
separada; validações recusam nome vazio, tipo desconhecido e ficha inexistente.

**Cenários de aceite**:

1. **Dado** um personagem proposto como "Piloto Rebelde" com o aviso "Nome a confirmar", **Quando** ela
   troca o nome para "Poe Dameron", **Então** o nome novo fica salvo e o nome que a leitura propôs
   continua visível como referência.
2. **Dado** um personagem com a ficha sugerida "417 Luke Skywalker", **Quando** ela troca para a ficha
   "565 Anakin", **Então** a ficha escolhida fica salva e a sugerida continua visível.
3. **Dado** um personagem com recorte em que aparece uma criança, **Quando** ela marca "Criar sem
   foto", **Então** o personagem fica marcado para ser criado sem foto.
4. **Dado** um tema em que a leitura não viu a Luna, **Quando** ela acrescenta "Luna Lovegood",
   **Então** o personagem entra no elenco proposto, sem foto, identificado como acrescentado à mão, e
   pode ser excluído depois (os propostos pela leitura não se excluem: marcam-se "Não criar").
5. **Dado** um item que a leitura classificou como tema, **Quando** ela muda o tipo para genérico,
   **Então** o elenco proposto deixa de valer para aquele item, fica guardado e volta se o tipo voltar
   a ser tema ou dupla.
6. **Dado** um nome em branco, um tipo que não existe ou uma ficha inexistente, **Quando** a alteração
   é enviada, **Então** ela é recusada com a mensagem no campo, e o que estava digitado não se perde.

---

### História 5 — Encontrar um item e saber quanto falta (Prioridade: P2)

A fila tem filtro por tipo (tema, dupla, avulso, genérico) e por situação (a conferir, conferido, sem
leitura), busca pelo nome do item e um contador de progresso ("120 de 352 conferidos"). O filtro e a
busca ficam no endereço da página: recarregar ou voltar do catálogo traz a mesma fila, no mesmo ponto.

**Por que esta prioridade**: dá para começar pelos 170 itens de um toque só (avulsos e genéricos) e
deixar os temas para depois; e dá para o dono acompanhar o andamento sem perguntar.

**Verificação**: cenário 15 do `verify_360.py` (filtros e busca devolvem só o que pedem; os totais por
tipo e por situação somam o total da fila) e conferência de tela.

**Cenários de aceite**:

1. **Dado** a fila com os quatro tipos, **Quando** ela filtra por "Avulso" e "A conferir", **Então** só
   aparecem itens avulsos ainda não conferidos, e o total mostrado é o desse recorte.
2. **Dado** a busca por "frozen", **Quando** ela digita, **Então** aparecem os itens cujo nome contém o
   termo, sem diferenciar acento nem maiúscula.

### Casos de borda

- **Duas pessoas no mesmo item**: cada alteração vale por campo; a última gravada fica. Se uma marca
  o item como conferido enquanto a outra edita, a edição seguinte é recusada com a instrução de
  reabrir, e a tela mostra o estado atual.
- **Item excluído do catálogo durante a conferência**: some da fila; a alteração em curso recebe "item
  não encontrado" e a tela atualiza a fila.
- **Ficha sugerida excluída depois da carga**: o personagem passa a aparecer sem ficha.
- **Foto do recorte removida da galeria depois da carga**: o personagem passa a aparecer sem foto.
- **Leitura que não conseguiu recortar** (a própria leitura marcou "sem foto"): o personagem já nasce
  como "Criar sem foto", com o motivo no aviso; não há recorte para voltar atrás.
- **Item sem nenhuma foto na galeria**: aparece com o estado vazio de fotos; a conferência segue pelos
  nomes.
- **Carga acionada duas vezes ao mesmo tempo**: nenhum item fica duplicado.
- **Falha de rede ao salvar**: o que foi digitado continua no campo, o cartão mostra que não foi
  possível salvar e oferece tentar novamente; nada é dado como salvo sem a resposta do servidor.
- **Usuário que conferiu foi excluído**: o item continua conferido, sem o nome de quem conferiu.
- **Tema com todos os personagens em "Não criar"**: não pode ser conferido; a tela orienta a corrigir o
  tipo do item (FR-017).
- **Item aberto pelo endereço depois de sair da fila**: a tela diz que o item já tem elenco ou ficha no
  catálogo e oferece o próximo.
- **Fila zerada**: quando não resta item a conferir, a tela diz que a conferência terminou e quantos
  itens ficaram sem leitura, se houver.

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: O sistema DEVE guardar, para cada item do catálogo lido, a proposta da leitura: tipo
  proposto, nota do leitor, ação proposta (quando não há elenco), grupo possível e, por personagem, nome
  proposto, foto da galeria e recorte, ficha de figurino sugerida, aviso e a marca "sem foto".
- **FR-002**: A fila da conferência DEVE ser calculada a cada consulta como: itens ativos, sem ficha de
  figurino própria, sem nenhum personagem cadastrado no catálogo e que não são a página própria de um
  personagem de outro tema. Item fora dessa regra não aparece na
  fila nem nos contadores; as decisões dele continuam guardadas.
- **FR-003**: Item que está na fila e não tem leitura DEVE aparecer como "Sem leitura", contado à
  parte, sem ação de conferência e com o caminho para a página dele no catálogo.
- **FR-004**: Quem confere DEVE poder, por personagem: alterar o nome, trocar ou tirar a ficha de
  figurino, escolher "Criar" ou "Não criar", marcar "Criar sem foto" e escrever uma observação. O nome
  e a ficha propostos pela leitura DEVEM continuar visíveis depois da correção.
- **FR-005**: Quem confere DEVE poder acrescentar um personagem a um item (nome obrigatório, ficha
  opcional). O personagem acrescentado entra sem foto, fica identificado como acrescentado à mão e pode
  ser excluído; personagem proposto pela leitura não pode ser excluído.
- **FR-006**: Quem confere DEVE poder, por item: corrigir o tipo, escolher ou tirar a ficha do item
  quando o tipo é avulso, escrever uma observação, marcar como conferido e reabrir.
- **FR-007**: O elenco proposto só vale para item do tipo tema ou dupla. Ao mudar o tipo para avulso ou
  genérico o elenco é preservado e deixa de valer; ao voltar, volta a valer. A ficha do item segue a
  mesma regra com o tipo avulso: só pode ser escolhida em item avulso, fica guardada se o tipo mudar e
  volta a valer se o tipo voltar.
- **FR-008**: Cada alteração DEVE ser salva no momento em que é feita, sem botão geral de salvar, com
  resposta visível (salvando, salvo, erro) no próprio cartão.
- **FR-009**: Item conferido DEVE registrar quem conferiu e quando, e DEVE recusar alteração até ser
  reaberto. Reabrir preserva todas as decisões.
- **FR-010**: A carga da leitura DEVE ser uma ação explícita do Superadmin, idempotente: acrescenta só
  os itens que ainda não têm leitura, nunca altera item que já tem, não duplica sob clique duplo e
  devolve o resumo do que entrou, do que já existia e do que foi ignorado, com o motivo.
- **FR-011**: A carga DEVE tolerar referência que deixou de existir: item inexistente é ignorado; foto
  que saiu da galeria vira personagem "sem foto"; ficha inexistente vira "sem ficha". Nos dois últimos
  casos o aviso do personagem diz o que aconteceu.
- **FR-012**: A fila DEVE ter filtro por tipo e por situação (a conferir, conferido, sem leitura),
  busca pelo nome do item sem diferenciar acento nem maiúscula, e contadores: total da fila, conferidos,
  a conferir, sem leitura e o total por tipo. A fila vem em ordem alfabética do nome do item. O
  progresso é "conferidos de (conferidos + a conferir)"; os itens sem leitura aparecem à parte e não
  entram nessa conta. Os contadores são sempre os da fila inteira, não os do filtro. Filtro e busca
  ficam no endereço.
- **FR-013**: A tela DEVE mostrar, em cada item, as fotos da galeria do item para comparação com os
  recortes, abrindo no visualizador do sistema (nunca em outra aba).
- **FR-014**: Nenhuma ação da conferência DEVE alterar o catálogo: nenhum personagem é criado, nenhuma
  ficha é ligada, nenhuma foto é gravada e nada muda na vitrine pública.
- **FR-015**: Só o Superadmin acessa a conferência e a carga; os demais papéis recebem recusa em todos
  os endpoints e não veem a entrada da tela.
- **FR-016**: A tela DEVE ser utilizável a 390 px de largura sem rolagem lateral, com as ações de cada
  cartão ao alcance do polegar e alvos de toque de pelo menos 44 px. Cada controle de um personagem
  tem rótulo acessível que diz de qual personagem é ("Nome de Yoda", "Não criar Yoda").
- **FR-017**: Um item do tipo tema ou dupla só pode ser marcado como conferido se tiver pelo menos um
  personagem com a decisão "Criar". Sem nenhum, a tela recusa e orienta a corrigir o tipo do item.
- **FR-018**: Cada item é conferido numa tela própria, com a ação de conferir fixa no rodapé. Depois de
  conferir, a tela oferece o próximo item a conferir, respeitando o filtro e a busca em uso na fila. A
  fila tem "Continuar conferência", que abre o primeiro item a conferir.

### Entidades *(se houver dados)*

- **Conferência do item**: a leitura de um item do catálogo e o que foi decidido sobre ele. Uma por
  item. Guarda o tipo proposto e o tipo decidido, a nota e a ação da leitura, o grupo possível, a ficha
  sugerida e a ficha decidida do item (para avulso), a observação, de qual leva de leitura veio e, se
  conferido, quem e quando. Some junto com o item se ele for excluído do catálogo. Modelo em
  `app/models.py`, migration à mão.
- **Personagem proposto**: um personagem dentro da conferência de um item. Guarda o nome proposto e o
  nome decidido, a foto da galeria e o recorte, a ficha sugerida e a ficha decidida, o aviso, se a
  leitura não achou foto, a decisão ("criar" ou "não criar"), a marca "criar sem foto", a observação, a
  ordem e a origem (leitura ou acrescentado à mão). Modelo em `app/models.py`, migration à mão.
- **Leitura**: o arquivo com as propostas (343 itens de 09/11 e os 13 de 24/11), versionado junto com
  o sistema. É a fonte da carga; não é alterado pela conferência.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

Todos os endpoints novos são só do Superadmin (Princípio XIII), mesmo gate da gestão do catálogo; cada
um ganha linha na tabela de `docs/01` §4.3.

- `GET /api/admin/catalogo/conferencia` — papéis: SUPERADMIN (fila, contadores, filtros)
- `GET /api/admin/catalogo/conferencia/<item_id>` — papéis: SUPERADMIN (detalhe do item)
- `POST /api/admin/catalogo/conferencia/carregar` — papéis: SUPERADMIN (carga da leitura)
- `PATCH /api/admin/catalogo/conferencia/<item_id>` — papéis: SUPERADMIN (tipo, ficha do item,
  observação)
- `POST /api/admin/catalogo/conferencia/<item_id>/conferir` e `…/reabrir` — papéis: SUPERADMIN
- `POST /api/admin/catalogo/conferencia/<item_id>/personagens` — papéis: SUPERADMIN (acrescentar)
- `PATCH` e `DELETE /api/admin/catalogo/conferencia/personagens/<id>` — papéis: SUPERADMIN

## Verificação (`verify_360.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/360-conferencia-de-personagens/verify_360.py`, contra o espelho `manto_360` (dump de
produção de 24/11 02h; exceção ao `manto_local` registrada no plano), com `DATABASE_URL` de
`.local-db-url`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`. Login só por `POST /api/auth/login`;
escrita conferida por conexão separada; limpeza no `finally`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Primeira carga da leitura real | cria conferências e personagens; resumo bate com a contagem por conexão separada; nenhuma tabela do catálogo muda | não |
| 2 | Segunda carga | zero linhas novas ou alteradas | não |
| 3 | Alterar a decisão de um personagem e reler | gravado e lido de volta por conexão separada | não |
| 4 | Conferir item; tema sem nenhum personagem "Criar" | o primeiro sai de "a conferir" e registra quem e quando; o segundo é recusado (FR-017) | **sim** (o segundo) |
| 5 | Item ganha personagem no catálogo | some da fila e dos contadores; decisões seguem guardadas | não |
| 6 | Item ganha ficha própria / é desativado / vira página própria de um personagem | some da fila | não |
| 7 | Item pendente sem leitura | aparece como "sem leitura", fora do total a conferir | não |
| 8 | Carga com item já decidido | decisão humana intacta depois da carga | não |
| 9 | Alterar personagem de item conferido | 409 com a instrução de reabrir; nada muda | **sim** |
| 10 | Corrigir nome e trocar ficha | decidido muda, proposto preservado | não |
| 11 | Acrescentar e excluir personagem à mão; excluir personagem da leitura | o primeiro passa; excluir o da leitura é recusado | **sim** (o segundo) |
| 12 | Mudar o tipo do item ida e volta | elenco preservado; ficha do item só vale em avulso | não |
| 13 | Nome vazio, tipo desconhecido, ficha inexistente | 400 com o campo apontado; nada gravado | **sim** |
| 14 | Carga com referências quebradas (item, foto e ficha inexistentes) | não falha; ignora, marca sem foto e sem ficha, com aviso | não |
| 15 | Filtros, busca e contadores | cada filtro devolve só o que pede; totais somam | não |
| 16 | Papel sem permissão (Comercial, Figurino) em todos os endpoints; sem login | 403 e 401; nada gravado | **sim** |
| 17 | Excluir, depois da carga, uma foto da galeria, uma ficha e um item que têm conferência (descartáveis) | as exclusões que já existem seguem funcionando: a foto e a ficha viram "sem foto" e "sem ficha" no personagem, e o item leva a conferência junto | não |
| 18 | Limpeza | usuários e registros descartáveis apagados (`roles.clear()` antes do usuário); tabelas da conferência vazias de novo | — |

Conferência de tela: `/admin/catalogo/conferencia` aberta no Browser pane a 390×844 e em tela larga:
fila, um tema com recortes, um avulso, um genérico, correção de nome, troca de ficha, conferir e
reabrir, estado "Sem leitura", fila filtrada e busca.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Um item avulso ou genérico é conferido com um toque; um tema de seis personagens em que
  a leitura acertou é conferido em menos de 30 segundos.
- **SC-002**: 100% das decisões tomadas num aparelho estão presentes ao abrir a tela em outro.
- **SC-003**: A fila mostra exatamente os itens pendentes da produção (352 no espelho de 24/11):
  nenhum item resolvido aparece e nenhum pendente fica de fora.
- **SC-004**: Repetir a carga não muda nenhum registro existente.
- **SC-005**: A tela inteira funciona a 390 px de largura sem rolagem lateral.
- **SC-006**: Depois de conferir todos os itens, o catálogo e a vitrine pública estão idênticos ao que
  eram antes.
- **SC-007**: O dono vê o andamento ("N de 352 conferidos") sem perguntar a ninguém.

## Fora de escopo

- **Gravar o resultado no catálogo**: criar os personagens com o recorte de verdade, ligar as fichas,
  transformar item em tema, fazer a busca achar personagem e criar o filtro "Sem foto" para o
  marketing. É a feature seguinte, e ela lê o que esta guardou.
- Trocar a foto do personagem ou redesenhar o recorte na tela. Quem confere marca "Criar sem foto".
- Fazer uma leitura nova de dentro do sistema. A leitura continua sendo feita fora e entra pela carga.
- Aviso automático ao marketing. A marca "sem foto" fica guardada para a feature seguinte.
- Criar tema de grupo a partir do "grupo possível" (Turma do Mickey, Vingadores). A tela só mostra a
  sugestão.
- Acesso de outros papéis (Figurino, Marketing).

## Docs a atualizar

`docs/01` §3 (endpoints), §4.3 (gates) e o schema das duas tabelas; `docs/02` (tela nova e a entrada a
partir do catálogo); `docs/03` (entrada no topo); `docs/04` (catálogo: o fluxo leitura → conferência →
gravação e a regra da fila; vai para `docs/regras-de-negocio/` se a 359 já estiver na `main` no merge);
`docs/05` (dívida: gravar o conferido no catálogo; leitura versionada no repositório). Decisão de
arquitetura (a leitura entra por carga explícita, não por migration; a conferência não toca o
catálogo): nota em `docs/decisoes/` se a 359 já estiver na `main` no merge, senão na entrada do
`docs/03`.

## Premissas

- A conferência só registra decisões. A regra do dono de 09/11 ("nada se grava em produção sem a
  conferência do dono por lote") continua valendo para a gravação no catálogo, que fica para a feature
  seguinte; o que o dono delegou à Maria Gabriella é a conferência.
- Só o Superadmin confere, como na gestão do catálogo.
- Item sem leitura é só informativo. Item novo normalmente ganha elenco direto no cadastro do catálogo;
  se o dono quiser leitura para ele, a leitura é feita fora e entra por nova carga.
- A leitura de um item entra uma vez. Não há recarga de item já lido nesta feature.
- Os avisos e as notas da leitura são mostrados como vieram, sem reescrita.
- As regras de foto do dono (olhar todas as fotos; preferir o personagem sozinho; recorte com vizinho
  só se não houver outro; qualidade ruim vira "criar sem foto e avisar o marketing") já foram aplicadas
  pela leitura e são as mesmas que orientam quem confere.
