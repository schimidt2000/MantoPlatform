# Feature 322 — O casting vê o que está fechando, e o maquiador aparece sozinho

**Branch**: `322-o-que-o-casting-fecha` (da `main` `6f706fa6`, worktree `C:\tmp\mp322`) ·
**Created**: 2026-10-28 · **Status**: Rascunho · **Migration**: uma, aditiva (três colunas novas na
vaga do evento) · **Nível**: 1 (feature) — constituição, Princípio VI

**Input**: pedido do dono (28/10/2026), resumido em "O pedido" abaixo.

## O pedido, nas palavras do dono *(obrigatório)*

"Hoje em dia, a gente coloca o valor para as pessoas como teto no cachê, mas não necessariamente ele
sabe o que exatamente foi fechado. […] A pessoa que ele tem que escalar, quando dentro da página do
evento, deve aparecer o que deve ser. Se deve ser, por exemplo, um cantor, um bailarino, um boneco
especial grande, para ela saber do que se trata aquele personagem que ela tem que fechar. Se é
cantor, se tem maquiagem."

"Eu preciso que todo evento que tenha marcado que tem maquiagem seja criada automaticamente até a
função de maquiagem. […] Que apareça adicionado pelo sistema automaticamente. Não precisa ser
parênteses, pode ser uma letra só um pouco mais clara, para que não fique tão poluído […] para que
eles entendam exatamente o que precisa ser fechado e que o maquiador apareça de fato."

"Antigamente, o maquiador às vezes aparecia no título do evento. Isso não é bom para mim. Eu não
quero que apareça no título."

Decisões do dono no mesmo dia, antes da spec:

- **O tipo vem só do orçamento.** Sem campo novo no formulário do evento: personagem que não veio
  de orçamento mostra só as marcas que já existem (maquiagem, cantor).
- **A marca de maquiagem não sai do personagem.** "Evento criado com orçamento, é sabido quais
  personagens têm make e quais não. Só deve ser alterado depois se o superadmin o fizer."
- **Sem retroativo para o maquiador.** Vale para evento criado ou editado depois do deploy.
- **"Adicionado pelo sistema" vale para toda vaga automática**: maquiador, coordenador e técnico de
  som.

### O que existe hoje (lido no código e na cópia local da produção de 20/10)

- O orçamento sabe o tipo de cada personagem (ator cara-limpa, boneco, cantor, especial: Bailarino,
  Boneco Grande Especial, Perna de Pau, Sósia…; com show, com maquiagem, cantor). Quando o evento
  nasce do orçamento, esse texto vai só para a **conta do teto**, que só o superadmin lê ("Especial
  Boneco Grande Especial: base 2h R$ 450"). O card do casting mostra o nome e um 💄 — nem a marca
  "cantor", que o formulário já grava, aparece.
- Dos 147 personagens de eventos futuros, 60 têm a conta do orçamento; 87 não vieram de orçamento.
- A vaga "Maquiador" só nasce pelo orçamento (na criação ou no vínculo da feature 273). Marcar
  maquiagem à mão, ou o evento vir do Google, não cria a vaga: 3 eventos futuros têm personagem
  maquiado e nenhum maquiador (1319, 403, 382 — os dois últimos têm orçamento ligado).
- O título já não aceita "Maquiador", "Coordenador" nem "Técnico de Som" (feature 239, decisão 6);
  nenhum título atual tem "maquia".

## Clarifications

### Session 2026-10-28

- Q: Na edição de um evento que já existe, quem não é superadmin pode marcar maquiagem num
  personagem NOVO? → A: Não, só o superadmin; a caixa aparece travada para os outros (FR-012).
- Q: O coordenador escolhido no campo "Coordenador" do formulário de criação mostra "adicionado
  pelo sistema"? → A: Não; só a vaga que o sistema cria quando o campo fica vazio (FR-011).
- Pedido novo do dono no meio da sessão: "os pré-escalados pelo comercial devem aparecer esse aviso
  de que foi inserido pelo comercial" → História 5, FR-014 a FR-016.

## Cenários e Verificação *(obrigatório)*

### História 1 — O casting vê o que é cada personagem (Prioridade: P1)

Quem escala abre o evento e, em cada personagem, lê logo abaixo do nome o que foi vendido: "Boneco
Grande Especial", "Cantor · show · com maquiagem", "Ator cara-limpa · com maquiagem", "Bailarino".
Sabe, antes de procurar alguém, se precisa de quem canta, de quem dança, de quem aguenta um boneco
grande e se vai ter maquiagem. Personagem sem orçamento mostra só as marcas que existem ("Cantor",
"Com maquiagem").

**Por que esta prioridade**: é o pedido central — sem isso o casting escala só pelo nome e pelo
teto, e erra o perfil.

**Verificação**: cenários 1 a 6 do `verify_322.py`.

**Cenários de aceite**:

1. **Dado** um orçamento com um especial "Boneco Grande Especial" chamado "Bumblebee", um cantor com
   maquiagem chamado "Moana" e um ator cara-limpa, **Quando** o evento é criado a partir dele,
   **Então** cada vaga guarda o seu tipo e o casting lê "Boneco Grande Especial", "Cantor · show ·
   com maquiagem" e "Ator cara-limpa".
2. **Dado** um evento do Google sem orçamento, **Quando** a comercial liga um orçamento a ele (o
   vínculo da feature 273), **Então** cada personagem que casa pelo nome ganha o tipo do orçamento;
   o que não casa continua sem tipo.
3. **Dado** um personagem criado à mão, marcado como cantor e com maquiagem, **Quando** o casting
   abre o evento, **Então** lê "Cantor · com maquiagem", sem tipo inventado.
4. **Dado** um usuário do casting (não superadmin), **Quando** lê o evento, **Então** recebe o tipo
   de cada personagem e continua **sem** receber o valor do teto nem a conta dele.
5. **Dado** um personagem que já tem tipo, **Quando** um orçamento é ligado de novo ou o evento é
   editado, **Então** o tipo não é apagado.

---

### História 2 — Personagem com maquiagem traz o maquiador junto (Prioridade: P1)

Basta um personagem com maquiagem para o evento ter a vaga "Maquiador" na equipe de apoio — criada
pelo formulário, pelo orçamento, pela edição ou pelo vínculo de orçamento. O casting vê a vaga, e o
selo "Falta maquiador" passa a apontar para uma vaga que existe.

**Por que esta prioridade**: hoje a maquiagem marcada à mão fica sem maquiador e ninguém percebe até
o dia do evento.

**Verificação**: cenários 7 a 12 do `verify_322.py`.

**Cenários de aceite**:

1. **Dado** o formulário de criação com um personagem marcado com maquiagem e sem orçamento,
   **Quando** o evento é salvo, **Então** nasce uma vaga "Maquiador" na equipe de apoio, sem
   talento e sem teto.
2. **Dado** um evento criado do orçamento com maquiagem, **Quando** é salvo, **Então** existe uma
   única vaga "Maquiador" (a do orçamento, com teto), nunca duas.
3. **Dado** um evento antigo sem maquiador e com personagem maquiado, **Quando** alguém o edita e
   salva, **Então** a vaga nasce nessa edição.
4. **Dado** um evento que já tem um maquiador (com ou sem talento, criado por qualquer caminho),
   **Quando** qualquer caminho roda de novo, **Então** nenhuma vaga nova nasce.
5. **Dado** um evento sem nenhum personagem maquiado, **Quando** é criado ou editado, **Então**
   nenhuma vaga de maquiador nasce.
6. **Dado** qualquer evento com a vaga de maquiador, **Quando** o título é montado e enviado ao
   Google, **Então** "Maquiador" não aparece no título.

---

### História 3 — "Adicionado pelo sistema" nas vagas automáticas (Prioridade: P2)

Ao lado do nome de cada vaga que o sistema criou sozinho (maquiador, coordenador, técnico de som e a
presença do técnico), aparece "adicionado pelo sistema" em letra menor e mais clara, sem parênteses
e sem selo colorido. O casting entende por que a vaga está lá sem ninguém tê-la pedido.

**Por que esta prioridade**: é o que dá sentido à vaga automática; sem a marca, parece erro.

**Verificação**: cenários 13 a 15 do `verify_322.py`.

**Cenários de aceite**:

1. **Dado** um evento criado depois do deploy, **Quando** o casting o abre, **Então** o maquiador,
   o coordenador e o técnico de som que o sistema criou mostram "adicionado pelo sistema".
2. **Dado** uma vaga que uma pessoa adicionou pelo "Adicionar pessoa" ou pelo formulário,
   **Quando** o casting abre o evento, **Então** a vaga não tem a marca.
3. **Dado** uma vaga automática em que alguém já foi escalado, **Quando** o casting abre o evento,
   **Então** a marca continua (ela diz quem criou a vaga, não quem a preencheu).
4. **Dado** um evento criado antes do deploy, **Quando** o casting o abre, **Então** nenhuma vaga
   antiga mostra a marca (não há como saber quem a criou).

---

### História 4 — Depois que o evento existe, só o superadmin mexe na maquiagem (Prioridade: P2)

A maquiagem é definida quando o evento nasce (pelo orçamento ou por quem cria o evento). Depois,
na edição, a caixa "Maquiagem" de cada personagem aparece travada para quem não é superadmin, com a
explicação. O servidor recusa a mudança mesmo que alguém a envie por fora da tela. O vínculo de
orçamento continua marcando a maquiagem que o orçamento diz — é o orçamento falando, não uma pessoa.

**Por que esta prioridade**: protege a regra da História 2 (a marca é o que cria o maquiador) e é a
decisão explícita do dono.

**Verificação**: cenários 16 a 19 do `verify_322.py` (o 17 DEVE falhar no comportamento antigo).

**Cenários de aceite**:

1. **Dado** um usuário comercial editando um evento, **Quando** tenta desmarcar a maquiagem de um
   personagem, **Então** a marca continua como estava.
2. **Dado** um usuário comercial editando um evento, **Quando** acrescenta um personagem novo e
   tenta marcá-lo com maquiagem, **Então** o personagem nasce sem a marca.
3. **Dado** o superadmin editando, **Quando** marca ou desmarca a maquiagem, **Então** a mudança
   vale; ao marcar, o maquiador nasce se faltar.
4. **Dado** o superadmin desmarcando a maquiagem de todos, **Quando** salva, **Então** a vaga de
   maquiador fica como está (o sistema não apaga vaga; o casting dispensa se quiser).

---

### História 5 — O pré-escalado pelo comercial aparece como tal (Prioridade: P2)

Quando o comercial já escolhe a pessoa no formulário do evento ("Pré-escalar talento específico" de
um personagem, ou o campo "Coordenador"), o card do casting mostra, junto ao nome do talento,
"inserido pelo comercial" no mesmo estilo discreto da marca do sistema. O casting sabe que aquela
escala não foi dele e confere antes de seguir.

**Por que esta prioridade**: pedido do dono no meio da spec (28/10): "os pré-escalados pelo
comercial devem aparecer esse aviso de que foi inserido pelo comercial".

**Verificação**: cenários 20 a 22 do `verify_322.py`.

**Cenários de aceite**:

1. **Dado** o formulário de criação com um talento pré-escalado num personagem e outro no campo
   "Coordenador", **Quando** o evento é salvo, **Então** as duas vagas mostram "inserido pelo
   comercial".
2. **Dado** o formulário de edição em que o comercial troca ou põe um talento num personagem,
   **Quando** salva, **Então** a vaga passa a mostrar a marca.
3. **Dado** uma vaga com a marca, **Quando** o casting troca o talento pelo card da página do
   evento, **Então** a marca sai (quem escalou agora foi o casting); **e quando** o casting tira o
   talento, a marca sai também.
4. **Dado** um evento salvo de novo pelo formulário sem mexer no talento, **Quando** salva,
   **Então** a marca de cada vaga fica como estava.

---

### Casos de borda

- Personagem do orçamento que não casa pelo nome no vínculo: fica sem tipo (como hoje fica sem
  teto); o relatório do vínculo já lista os não casados.
- Vaga de maquiador com nome diferente ("Maquiadora", "Maquiador 2"): conta como maquiador — o
  critério é o mesmo do selo de hoje (nome contendo "maquiad").
- Evento cancelado: nenhuma vaga nova nasce (a regra da feature 312 continua valendo).
- Produto de tabela (feature 309, Visita Mágica): o Papai Noel e o ajudante mostram o tipo do
  produto; a maquiagem do produto também traz o maquiador.
- Evento do Google cujo título traz personagem novo: o personagem nasce sem maquiagem (como hoje),
  então não cria maquiador.
- Personagem acrescentado na edição por quem não é superadmin com o tipo vazio: continua sem tipo
  (o tipo só vem do orçamento).
- Vaga do sistema em que o comercial pôs o talento (o coordenador garantido e preenchido depois
  pela edição): mostra as duas marcas — "adicionado pelo sistema" no nome da vaga e "inserido pelo
  comercial" no talento.

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: A vaga de personagem DEVE guardar o tipo vendido no orçamento, em texto que uma
  pessoa lê (tipo + marcas: "Cantor · show · com maquiagem"), gravado quando o evento nasce do
  orçamento e quando um orçamento é ligado a um evento existente.
- **FR-002**: O tipo DEVE chegar a todo usuário que vê o card do personagem na página do evento,
  inclusive quem não vê o teto; nenhum valor em dinheiro vai junto.
- **FR-003**: Personagem sem tipo DEVE mostrar as marcas que já tem ("Cantor", "Com maquiagem");
  sem marca nenhuma, não mostra linha de tipo.
- **FR-004**: Ligar um orçamento ou editar o evento NÃO DEVE apagar nem trocar um tipo já gravado
  (mesma regra "nunca apaga nem rebaixa" do vínculo da feature 273).
- **FR-005**: Todo evento com ao menos um personagem com maquiagem DEVE ter uma vaga de maquiador na
  equipe de apoio depois de criado, editado ou ligado a um orçamento; se já houver uma (qualquer
  nome contendo "maquiad"), nenhuma nova nasce.
- **FR-006**: A vaga criada pela regra da FR-005 DEVE nascer sem talento e sem teto; quando o
  orçamento traz o maquiador com teto, vale a vaga do orçamento (uma só).
- **FR-007**: Nenhuma vaga de maquiador DEVE nascer em evento cancelado, nem em evento sem
  personagem maquiado, nem retroativamente por script.
- **FR-008**: O título do evento NÃO DEVE conter "Maquiador" em nenhum caminho (já garantido pela
  feature 239; o verify prova que continua).
- **FR-009**: Toda vaga criada pelo sistema sem ninguém pedir — maquiador (FR-005 e orçamento),
  coordenador, técnico de som e presença do técnico — DEVE ficar marcada como criada pelo sistema,
  a partir do deploy.
- **FR-010**: A página do evento DEVE mostrar "adicionado pelo sistema" ao lado do nome das vagas
  marcadas, em letra menor que o nome e na cor de texto secundário da página (legível, não apagada),
  sem parênteses nem selo; o leitor de tela lê a marca junto com o nome.
- **FR-011**: Vaga adicionada por uma pessoa (formulário, "Adicionar pessoa", coordenador escolhido
  no formulário de criação) NÃO DEVE ter a marca.
- **FR-012**: Na edição do evento, só o superadmin DEVE poder mudar a marca de maquiagem de um
  personagem existente ou marcar um personagem novo; para os demais, o servidor mantém o valor
  anterior (ou "sem maquiagem" no personagem novo), sem erro, e a tela mostra a caixa travada com o
  texto "Só o superadmin muda a maquiagem depois que o evento existe."
- **FR-013**: Na criação do evento, quem cria DEVE continuar podendo marcar a maquiagem (como hoje);
  o vínculo de orçamento DEVE continuar marcando a maquiagem que o orçamento diz.
- **FR-014**: O talento posto numa vaga pelo formulário do evento (criação ou edição: pré-escala de
  personagem e campo "Coordenador") DEVE ficar marcado como inserido pelo comercial.
- **FR-015**: A página do evento DEVE mostrar "inserido pelo comercial" junto ao talento da vaga
  marcada, no mesmo estilo discreto da FR-010.
- **FR-016**: A marca da FR-014 DEVE sair quando o talento da vaga muda por outro caminho
  (escalação ou remoção pelo card do casting) e NÃO DEVE mudar quando o formulário é salvo sem
  trocar o talento.
- **FR-017**: A vaga de maquiador criada pela regra da FR-005 DEVE deixar uma linha no histórico do
  evento, em nome do Sistema ("Vaga de Maquiador criada: há personagem com maquiagem").

### Entidades *(se houver dados)*

- **Vaga do evento** (`EventRole`): ganha o **tipo vendido** (texto curto, vazio quando não veio de
  orçamento), a marca **criada pelo sistema** (sim/não; vazio nas vagas anteriores ao deploy) e a
  marca **talento inserido pelo comercial** (sim/não; acompanha o talento atual, não a vaga).
  Modelo em `app/models.py`, migration à mão, aditiva.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

- `GET /api/events/<id>` — papéis inalterados; o payload de cada vaga ganha o tipo e a marca do
  sistema para todo papel que já recebe o elenco.
- `PATCH /api/events/<id>` — papéis inalterados (`_can_edit_event`); a marca de maquiagem passa a
  ser ignorada para quem não é superadmin (Princípio XIII). Linha em `docs/01` §4.3.
- `POST /api/events` e `PATCH /api/events/<id>/orcamento` — papéis inalterados; passam a gravar o
  tipo e a garantir o maquiador.

## Verificação (`verify_322.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/322-o-que-o-casting-fecha/verify_322.py`, contra `manto_local` (`DATABASE_URL` de
`.local-db-url`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`). Login só por
`POST /api/auth/login`; escrita conferida por conexão separada; limpeza no `finally`; eventos de
teste criados pela API e apagados no fim (nunca vaga com nome inventado em evento real).

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | criação do orçamento com especial, cantor maquiado e ator | cada vaga grava o tipo certo | não |
| 2 | vínculo de orçamento em evento sem orçamento | personagem casado ganha o tipo; o não casado fica vazio | não |
| 3 | vínculo de novo / edição | o tipo gravado não muda | não |
| 4 | personagem à mão cantor + maquiagem | sem tipo; flags no payload | não |
| 5 | casting lê o evento | recebe o tipo, não recebe teto nem conta | não |
| 6 | produto de tabela (Visita Mágica) | Noel e ajudante com tipo do produto | não |
| 7 | criação manual com maquiagem | nasce 1 maquiador sem talento nem teto, com linha no histórico | não |
| 8 | criação do orçamento com maquiagem | 1 maquiador só, com teto | não |
| 9 | edição de evento com make e sem maquiador | a vaga nasce | não |
| 10 | evento que já tem "Maquiadora" | nenhuma vaga nova | não |
| 11 | evento sem make / evento cancelado | nenhuma vaga | não |
| 12 | título do evento com maquiador | sem "Maquiador" | não |
| 13 | vagas automáticas novas | marcadas como do sistema | não |
| 14 | vaga adicionada por pessoa / coordenador escolhido | sem marca | não |
| 15 | vaga anterior ao deploy | sem marca | não |
| 16 | superadmin muda a maquiagem | vale | não |
| 17 | comercial desmarca a maquiagem pela API | a marca continua | **sim** (no código antigo desmarca) |
| 18 | comercial marca personagem novo | nasce sem maquiagem | **sim** (no código antigo marca) |
| 19 | vínculo de orçamento por comercial | a maquiagem do orçamento é marcada | não |
| 20 | criação com pré-escala de personagem e coordenador | as duas vagas marcadas "inserido pelo comercial" | não |
| 21 | edição troca o talento pelo formulário / salva sem trocar | marca nasce / fica como estava | não |
| 22 | casting troca ou tira o talento pelo card | a marca sai | **sim** (sem a regra da FR-016 ficaria) |
| 23 | limpeza | eventos, vagas e usuários descartáveis apagados | — |

Conferência de tela: página do evento (card de personagem com tipo, equipe de apoio com "adicionado
pelo sistema") em desktop e 375×812; formulário de edição com a caixa de maquiagem travada para
comercial e livre para superadmin.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Em todo evento criado do orçamento depois do deploy, 100% dos personagens mostram ao
  casting o tipo vendido, sem abrir o orçamento.
- **SC-002**: Nenhum evento criado ou editado depois do deploy fica com personagem maquiado e sem
  vaga de maquiador.
- **SC-003**: O casting distingue, só olhando a página, a vaga que o sistema criou da que alguém
  adicionou.
- **SC-004**: Nenhum título de evento contém "Maquiador".
- **SC-005**: O casting distingue, só olhando a página, a escala que o comercial fez da que ele
  mesmo fez.

## Fora de escopo

- Campo de tipo no formulário do evento (decisão do dono: o tipo vem só do orçamento).
- Preencher o tipo ou criar maquiador em eventos já existentes por script (sem retroativo).
- Mostrar o tipo no Portal do Artista, no e-mail de convite ou na tela de figurino.
- Remover sozinho a vaga de maquiador quando a maquiagem sai de todos.
- Travar a marca "cantor" (o pedido fala só da maquiagem).

## Docs a atualizar

`docs/01` (schema de `event_roles`, payload de `GET /api/events/<id>`, regra do `PATCH`, §4.3),
`docs/02` (página do evento — Casting e Equipe de apoio; formulário de edição), `docs/03` (entrada
no topo), `docs/04` (invariante: personagem maquiado ⇒ vaga de maquiador), `docs/05` (dívidas que
nascerem).

## Premissas

- O texto do tipo segue o que a calculadora já chama de cada coisa, com a grafia da tabela de
  preços ("Boneco Grande Especial", "Ator cara-limpa" — nomes próprios como "Homem-Aranha" não
  perdem a maiúscula), e as marcas na ordem show · cantor · com maquiagem (research R1).
- Na janela do deploy (servidor e tela publicados separadamente), a tela sem os campos novos no
  servidor simplesmente não mostra perfil nem marcas; o servidor novo com a tela antiga só manda
  chaves a mais. A migration é aditiva.
- "Inserido pelo comercial" vale para todo talento que entra pelo formulário do evento, que é a
  ferramenta da comercial — mesmo quando quem salva é o superadmin. A marca acompanha o talento:
  quem escala pelo card do casting é o casting.
- Escalas feitas pelo formulário antes do deploy não levam a marca (não há registro de por onde
  entraram).
- A vaga de maquiador da FR-005 não tem teto: o orçamento é que define quanto se paga de make; sem
  orçamento o casting combina o valor, como faz hoje com toda vaga sem teto.
