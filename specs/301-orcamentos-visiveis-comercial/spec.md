# Feature 301 — Todo o comercial volta a ver e abrir o orçamento de qualquer colega

**Branch**: `301-orcamentos-visiveis-comercial` (da `main`) · **Created**: 2026-09-21 · **Status**: Rascunho ·
**Migration**: nenhuma · **Nível**: 1 (feature) — toca dois domínios (Orçamento e Agenda/evento)

**Input**: pedido do dono: "Todas as pessoas do setor comercial devem poder ver e abrir orçamentos de outras pessoas. Isso era assim até algum tempo atrás, mas alguma mudança deve ter mudado isso."

## O pedido, nas palavras do dono *(obrigatório)*

> "Todas as pessoas do setor comercial devem poder ver e abrir orçamentos de outras pessoas. Isso
> era assim até algum tempo atrás, mas alguma mudança deve ter mudado isso."

**O sintoma, como a pessoa vê**: quem tem o papel COMERCIAL abre `/orcamento/historico` e a lista
só traz os orçamentos que a própria pessoa salvou. Não há coluna "Vendedor", não há filtro por
vendedor, e um orçamento de colega não abre nem pelo link direto. Quem tem SUPERADMIN vê tudo, o
que faz o problema parecer "coisa de permissão" e não regressão.

No espelho da produção (dump de 27/08/2026) são **três pessoas com o papel COMERCIAL** — Thays,
Roberto e Fatima — além de dois SUPERADMIN. A forma mais nua do defeito é a **Fatima**: ela é do
comercial, tem **zero** orçamentos salvos, e por isso abre o Histórico de Orçamentos e encontra uma
**tela vazia**, como se o histórico da empresa não existisse.

**A mudança que mudou isso — encontrada**: a restrição foi *deliberadamente removida* em
**20/05/2026** pelo commit `6b191e4` ("fix: histórico de orçamentos visível para todos"), cuja
mensagem diz, com todas as letras: *"Histórico: remove filtro por user_id para não-SA; todos veem
todos os orçamentos"*. Em **23/07/2026**, a feature **177** (migração do módulo para React)
reescreveu a rota Jinja como endpoint de API e **reintroduziu o filtro**. A causa é documental: o
contrato `specs/177-migracao-ferramentas-react/contracts/api-endpoints.md:119` registrou a regra
como *"SUPERADMIN vê de todos os usuários, demais só o próprio (mesma regra de `is_sa` em
`routes.py:714`)"* — mas `routes.py:714`, naquele dia, **não tinha mais** esse filtro. O contrato
descreveu o código anterior a 20/05 e o React o implementou fielmente.

Depois disso a regra se espalhou para superfícies novas que a herdaram sem questionar: a aba
Comercial do evento (feature 239) e o vínculo orçamento↔evento (feature 273).

**Extensão do estrago**: a restrição viveu de **23/07/2026 a 21/09/2026 — dois meses** — e alcançou
**três superfícies em dois domínios**: o histórico de Orçamento (feature 177) e, no domínio
Agenda/evento, a aba Comercial (239) e o vínculo orçamento↔evento (273).

Sinal de que a restrição nunca foi desenhada: "Criar evento" a partir de um orçamento
(`GET /api/events/new/prefill`) **nunca** teve checagem de dono. Hoje é possível criar um evento
pré-preenchido com um orçamento que a pessoa não consegue abrir.

## Clarifications

### Session 2026-09-21

- Q: Ao abrir o Histórico de Orçamentos, a lista deve começar mostrando os orçamentos de quem? → A: Do time todo — restauração literal, sem filtro de vendedor pré-aplicado. O teto de 300 fica e os filtros resolvem quem quiser só os seus.
- Q: Quem pode re-aplicar ao evento os valores de um orçamento de outra pessoa, quando o vínculo já existe e não muda? → A: Só o autor daquele orçamento e o superadmin — a mesma trava de trocar e desvincular passa a valer para re-aplicar valores, equipe e data da venda.
- Q: Abrir, baixar PDF ou reenviar o orçamento de outra pessoa precisa ficar registrado? → A: Só o reenvio por e-mail de orçamento alheio (quem enviou, qual orçamento, para qual endereço), em `AuditLog`. Abrir e baixar PDF não geram registro.

## Cenários e Verificação *(obrigatório)*

### História 1 — O histórico volta a ser do time, não da pessoa (Prioridade: P1)

Uma pessoa do comercial abre **Histórico de Orçamentos** e encontra os orçamentos de todo o time,
sabendo de quem é cada um. Ela abre o de uma colega para responder um cliente que ligou enquanto a
colega estava fora, gera o PDF, reenvia o e-mail e, se precisar, recalcula em cima dele — sem
pedir para o superadmin.

**Por que esta prioridade**: é literalmente o pedido, e é o que destrava o atendimento quando quem
vendeu não está disponível. Sozinha já resolve o dia a dia.

**Verificação**: cenários 1–5, 10 e 11 do `verify_301.py` — provam que um COMERCIAL não-superadmin
lista, abre, filtra por vendedor, baixa PDF e envia e-mail de um orçamento criado por outro
COMERCIAL, que ele não consegue excluí-lo, e que quem está fora do comercial continua barrado.

**Cenários de aceite**:

1. **Dado** que a colega A salvou um orçamento e a pessoa B (COMERCIAL, não superadmin) nunca o
   viu, **Quando** B abre o histórico, **Então** a linha do orçamento de A aparece na lista com o
   nome de A na coluna "Vendedor".
2. **Dado** o histórico aberto por B, **Quando** B usa o filtro de vendedor e escolhe A, **Então**
   a lista mostra só os orçamentos de A.
3. **Dado** o orçamento de A na lista, **Quando** B clica em "Ver", **Então** o detalhe congelado
   abre normalmente (os mesmos valores que A vê), sem erro e sem "Orçamento não encontrado".
4. **Dado** o orçamento de A aberto por B, **Quando** B clica em "Baixar PDF" e em "Enviar por
   e-mail", **Então** as duas ações concluem como se fosse um orçamento próprio — e **o reenvio
   fica registrado** (quem enviou, qual orçamento, para quem), enquanto abrir e baixar não geram
   registro nenhum.
5. **Dado** o orçamento de A na lista, **Quando** B clica em "Recalcular", **Então** a calculadora
   abre repopulada com o que A preencheu.
6. **Dado** que B é COMERCIAL e não é dono do orçamento de A, **Quando** B olha a linha de A,
   **Então** a ação "Excluir" **não é oferecida** — excluir continua sendo do dono ou do
   superadmin, e a tela não oferece um botão que o servidor vai recusar.
7. **Dado** um usuário com papel FINANCEIRO (ou qualquer papel fora de COMERCIAL/SUPERADMIN),
   **Quando** ele tenta abrir o histórico, **Então** continua recebendo 403 — esta feature não
   alarga o portão do módulo, só derruba a parede interna.

---

### História 2 — A aba Comercial do evento mostra o orçamento mesmo quando é de outro (Prioridade: P2)

Uma pessoa do comercial abre um evento vendido por uma colega. Na aba Comercial ela vê o que o
orçamento vendeu (os chips do resumo) e o link para abrir o orçamento inteiro — hoje esse bloco
some porque o orçamento é de outra pessoa.

**Por que esta prioridade**: é o mesmo bloqueio visto de outra tela. Sem isso, o histórico abre,
mas quem está atendendo pelo evento continua no escuro.

**Verificação**: cenário 6 do `verify_301.py` — evento vinculado ao orçamento de A; B abre o
detalhe e recebe `venda.orcamento` preenchido e o id do orçamento no payload.

**Cenários de aceite**:

1. **Dado** um evento vinculado ao orçamento de A, **Quando** B (COMERCIAL, não superadmin) abre o
   evento, **Então** a aba Comercial mostra o resumo do que o orçamento vendeu e o link para
   abri-lo.
2. **Dado** o mesmo evento, **Quando** um usuário FINANCEIRO o abre, **Então** o bloco do orçamento
   continua ausente do payload (o módulo de Orçamento segue fechado para ele) — comportamento
   inalterado.

---

### História 3 — Amarrar ao evento o orçamento de um colega, sem poder desfazer o dele (Prioridade: P3)

Uma pessoa do comercial cria ou edita um evento que ainda não tem orçamento e o amarra ao
orçamento que a colega fez, aplicando ao evento o que aquele orçamento vendeu. O que ela **não**
pode é mexer num evento que já está amarrado ao orçamento de outra pessoa — nem trocar, nem soltar,
nem re-aplicar valores por cima. Aí a tela diz de quem é e quem pode mexer.

**Por que esta prioridade**: é escrita, não leitura, e mexe em valor de venda e comissão (features
267/273). Entregar as histórias 1 e 2 sem esta já resolve o pedido literal; esta fecha o fluxo sem
deixar ninguém reescrever a venda alheia.

**Verificação**: cenários 7, 8 e 9 do `verify_301.py` — B vincula ao evento um orçamento de A
(passa); depois tenta trocá-lo por outro e re-aplicar os valores por cima (as duas recusam, com o
nome de A na mensagem).

**Cenários de aceite**:

1. **Dado** um evento **sem** orçamento vinculado e um orçamento de A, **Quando** B (COMERCIAL,
   não superadmin) vincula, **Então** o vínculo é criado e o evento recebe o que o orçamento
   vendeu — sem "Orçamento não encontrado" para algo que B enxerga na tela.
2. **Dado** um evento **já** vinculado ao orçamento de A, **Quando** B tenta trocar por outro
   orçamento ou desvincular, **Então** o sistema recusa dizendo que o evento está vinculado ao
   orçamento **de A** e que só A ou o superadmin podem mexer.
3. **Dado** o mesmo evento vinculado ao orçamento de A, **Quando** B tenta **re-aplicar** os
   valores, a equipe ou a data da venda a partir do mesmo orçamento de A (sem trocar o vínculo),
   **Então** o sistema recusa pela mesma regra — valor de venda e data da venda de uma venda alheia
   não são reescritos por colega.
4. **Dado** o mesmo evento vinculado ao orçamento de A, **Quando** **A** ou o superadmin troca,
   desvincula ou re-aplica, **Então** a ação conclui normalmente (comportamento inalterado).

---

### Casos de borda

- **Orçamento legado** (sem `result_snapshot` completo, anterior ao congelamento): abrir o de um
  colega passa pelo mesmo caminho de fallback do próprio — não pode estourar erro.
- **Teto de 300 linhas sobre um histórico concentrado**: a lista traz no máximo 300 registros.
  Antes eram 300 *por pessoa*; agora são 300 do time inteiro. No espelho da produção (dump de
  27/08/2026) são **1.809 orçamentos de 4 vendedores**, e **1.631 deles (90%) são de uma pessoa
  só** — 884 foram criados nos últimos três meses. Efeito prático: a primeira tela fica quase toda
  de um vendedor, e quem tem 32 ou 5 orçamentos **não encontra os próprios sem filtrar**. É o preço
  aceito da restauração literal (Clarifications, 2026-09-21); os filtros (cliente, local, período,
  faixa de valor, vendedor) passam a ser o caminho normal, não o atalho.
- **Vendedor sem nome / usuário removido**: `admin/user_ops.py` já impede apagar usuário que tenha
  orçamento, mas a coluna precisa aguentar `user_name` nulo sem quebrar a linha. A regra de quem
  exclui e de quem manda no vínculo apoia-se **sempre no `user_id`**, nunca no nome: nome ausente
  não afrouxa nem endurece a trava. Sem nome recuperável, a coluna "Vendedor" e a chave `autor`
  mostram **"Vendedor não identificado"**, e a recusa de FR-011 usa esse mesmo texto no lugar do
  nome.
- **O contador da calculadora**: `OrcamentoCalculadoraPage.tsx:120` é um **terceiro** consumidor de
  `GET /api/orcamento/historico` — chama sem filtro e usa `entries.length` como selo ao lado do
  link "Histórico de Orçamentos" (`:508-511`). Com FR-001 ele deixa de contar "os meus" e passa a
  contar o time, **saturando em 300** para todo mundo (são 1.809 no espelho). Efeito aceito, não
  defeito: o selo vira "tem histórico", não "tenho N". Fica anotado porque essa tela não aparecia
  em nenhum artefato e o `typecheck` não a acusaria — ela não lê `is_superadmin`.
- **Botão que o servidor recusa**: "Excluir" hoje é renderizado em toda linha. Com a lista
  compartilhada, ele apareceria sobre orçamentos alheios e só falharia depois do `confirm()`.
- **Exclusão com evento vivo vinculado**: a guarda 409 da feature 273 continua valendo, mas vem
  **depois** da checagem de autoria, não antes — quem não é o autor leva 404 e nunca chega no 409.
  A ordem fica como está: inverter passaria a confirmar, para quem não é autor, que o orçamento
  existe e está preso a um evento (o repositório devolve 404, não 403, justamente para não
  confirmar existência — Princípio XIII).
- **Concorrência**: duas pessoas abrindo o mesmo orçamento é leitura pura; nenhuma escreve no
  registro. "Recalcular" cria um orçamento novo, do próprio usuário — nunca sobrescreve o do colega.
- **Quem vinculou não consegue reajustar depois**: consequência aceita de FR-011. B amarra o
  orçamento de A a um evento (permitido); a partir daí o evento está vinculado ao orçamento **de
  A**, então se B quiser re-aplicar com outra duração, trocar ou soltar, a recusa cai em cima
  dele. Quem resolve é A ou o superadmin. É coerente com a regra ("a venda é de quem fez o
  orçamento"), mas a mensagem precisa deixar isso óbvio para B não achar que é defeito.

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: O histórico de orçamentos DEVE mostrar os orçamentos de **todas** as pessoas do
  comercial a qualquer pessoa autorizada no módulo, sem esconder os de outro autor.
- **FR-002**: Qualquer pessoa autorizada no módulo DEVE conseguir abrir o orçamento congelado de
  outra pessoa e recalcular em cima dele (a calculadora reabre com tudo o que o autor preencheu).
- **FR-003**: Gerar o PDF e reenviar o e-mail de um orçamento DEVEM funcionar para qualquer pessoa
  autorizada no módulo, independentemente de quem o criou.
- **FR-004**: A lista DEVE identificar o autor de cada orçamento (coluna "Vendedor") para todas as
  pessoas autorizadas, não só para o superadmin — lista compartilhada sem autoria é indistinguível
  de dado errado.
- **FR-005**: O filtro por vendedor (e a lista de vendedores que o alimenta) DEVE estar disponível
  para todas as pessoas autorizadas no módulo, não só para o superadmin.
- **FR-006**: **Excluir** um orçamento DEVE continuar restrito ao autor e ao superadmin — é a única
  trava de dono que esta feature preserva de propósito, e é a mesma decisão registrada em `6b191e4`.
- **FR-007**: A tela NÃO DEVE oferecer "Excluir" em orçamento que a pessoa não pode excluir; o
  servidor continua sendo a autoridade e recusa mesmo assim (o frontend nunca decide RBAC —
  Princípio XIII).
- **FR-008**: O portão do **módulo de Orçamento** (as rotas `/api/orcamento/*`) NÃO DEVE mudar:
  quem não é COMERCIAL nem SUPERADMIN continua recebendo 403, inclusive FINANCEIRO. Os dois
  endpoints de **evento** tocados por esta feature têm gate próprio, mais largo, que já aceita
  FINANCEIRO — e também não muda. Para eles valem as regras nominais de FR-009 e FR-011.
- **FR-009**: Ao abrir um evento, uma pessoa do comercial DEVE ver o que o orçamento vinculado
  vendeu e conseguir abri-lo, mesmo quando o orçamento é de outra pessoa; para quem não tem acesso
  ao módulo de Orçamento, esse bloco continua não existindo na tela.
- **FR-010**: Toda recusa de **escrita** sobre orçamento de outra pessoa (o 409 do vínculo) DEVE
  trazer (a) o motivo — o evento está vinculado ao orçamento de outra pessoa — e (b) o nome do
  autor com a saída: só ele ou o superadmin podem **trocar, desvincular ou re-aplicar**.
  **Exceção única e deliberada**: o `DELETE` de orçamento alheio responde **404 "Orçamento não
  encontrado"**, sem motivo nem nome, porque ali a autoria *é* a trava — um 403 explicativo
  confirmaria a existência do registro (Princípio XIII: recurso de outro dono devolve 404).
  Fora dessas duas situações, "não encontrado" só vale para orçamento que de fato não existe.
- **FR-011**: Qualquer pessoa do comercial DEVE poder **vincular** a um evento **ainda sem
  orçamento** o orçamento de outra pessoa, aplicando na mesma ação o que aquele orçamento vendeu.
  Toda escrita posterior sobre um evento já vinculado ao orçamento de outra pessoa — **trocar**,
  **desvincular** ou **re-aplicar** valores, equipe ou data da venda — DEVE continuar restrita ao
  autor do orçamento vinculado e ao superadmin. A recusa DEVE nomear **o autor** e dizer que só ele
  ou o superadmin podem mexer (decisões do dono, 2026-09-21).

  **Quem pode vincular**: COMERCIAL e SUPERADMIN. O FINANCEIRO passa no gate `_can_manage_sale()`
  deste endpoint, mas **continua levando 404** ao apontar um orçamento que não é dele — ele não tem
  o módulo de Orçamento e esta feature não o alarga (§Fora de escopo, SC-005). Hoje quem o barra é
  o 404-por-dono sobre o alvo, que cai; então a queda **tem de ser condicionada ao papel**, senão a
  feature dá ao FINANCEIRO um poder que ninguém pediu.

  *Vocabulário*: nesta spec, **autor** é sempre quem fez o orçamento — é o sujeito das regras de
  FR-006 e FR-011. "Vendedor" fica reservado ao rótulo da coluna na tela, e "dono" ao mecanismo
  ("checagem de dono", como em `docs/01` §3.13) ou ao dono do produto. A distinção importa porque o
  evento tem o **seu** vendedor, que pode ser outra pessoa. E **pessoa autorizada no módulo** —
  sujeito de FR-001 a FR-005 — é quem passa em `_require_vendas()` de `orcamento_read.py:30`:
  papel COMERCIAL ou SUPERADMIN, nunca FINANCEIRO. Onde esta spec disser só "módulo", leia "módulo
  de Orçamento"; os endpoints de evento têm gate próprio, na tabela de RBAC.
- **FR-012**: A tela DEVE abrir com os orçamentos de **todo o time**, sem nenhum filtro de vendedor
  pré-aplicado — nem "meus orçamentos" por padrão. Quem quiser só os próprios usa o seletor de
  vendedor de FR-005.
- **FR-013**: Reenviar por e-mail o orçamento **de outra pessoa** DEVE deixar registro de auditoria
  com quem enviou, qual orçamento e para qual endereço. Abrir e baixar PDF **não** geram registro,
  e reenviar o próprio orçamento também não — só o que sai da empresa por cima da venda de outra
  pessoa. O registro usa a trilha de auditoria que já existe, sem migration.
  **Se o envio der certo e a gravação do registro falhar**, a resposta continua **200**: o e-mail
  já saiu e não se desfaz. A falha vai para o log do servidor (com id do orçamento, ator e
  destinatário) e a gravação roda em `try/except` próprio, sem derrubar a resposta — falha de
  auditoria nunca é mostrada ao usuário como falha de envio.
- **FR-014**: O comportamento restaurado DEVE ser registrado como regra explícita na tabela de RBAC
  (`docs/01` §4.3) e em `docs/01` §3.13, para que a próxima reescrita do módulo não reimporte a
  restrição a partir de um contrato desatualizado — foi exatamente assim que ela voltou.
- **FR-015**: Todo texto que hoje **ensina a regra antiga** DEVE ser corrigido na mesma entrega em
  que o código muda — não basta escrever a regra nova em outro lugar. São quatro, todos já com
  tarefa dona: os dois comentários de `app/api/agenda_read.py` (`:157-159` e `:901-904`), o
  docstring de `api_set_event_orcamento` (`agenda_write.py`) e o docstring de
  `OrcamentoPicker.tsx` (`:12-15`). Além deles, o contrato da feature 177
  (`specs/177-migracao-ferramentas-react/contracts/api-endpoints.md:118-119`) DEVE receber uma nota
  inline de **regra superada**, apontando para `docs/01` §4.3 — ele continua vivo como registro
  histórico, e foi ele que reimportou a restrição.

### Entidades *(se houver dados)*

Nenhuma entidade nova e nenhuma migration. A feature só muda o **escopo de leitura** sobre
`OrcamentoHistory` (`app/models.py`), cujo `user_id` continua sendo a autoria do registro — ele
deixa de ser filtro de visibilidade e passa a ser apenas informação exibida e critério de filtro
opcional.

- **`AuditLog`** (`app/models.py`, já existente): FR-013 grava uma linha por reenvio de e-mail de
  orçamento alheio. Os campos que a tabela já tem bastam — ator, tipo e id do objeto, ação e um
  detalhe livre para o destinatário. Nenhuma coluna nova, nenhuma migration.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

Nenhum endpoint novo. **Nenhum gate muda** — o que muda é a **checagem de dono interna**. Mas os
sete endpoints **não** compartilham o mesmo gate, e confundi-los é como se derruba o acesso do
FINANCEIRO ao evento sem querer:

- os **cinco** de `/api/orcamento/historico*` passam por `_require_vendas()` de
  `orcamento_read.py:30` — **COMERCIAL** ou **SUPERADMIN**; FINANCEIRO leva **403** (é o homônimo
  de regra diferente, já marcado em `docs/01` §4.3);
- `GET /api/events/<id>` passa pela flag `show_comercial` (`agenda_read.py:152`, aplicada em
  `:899`) — COMERCIAL, **FINANCEIRO** ou SUPERADMIN;
- `PATCH /api/events/<id>/orcamento` passa por `_can_manage_sale()` (`agenda_write.py:53`,
  chamado em `:1164`) — COMERCIAL, **FINANCEIRO**, SUPERADMIN.

Nos dois de evento o FINANCEIRO **não** leva 403, e não é esta feature que vai mudar isso.

| Endpoint | Gate de módulo | Checagem de dono hoje | Depois |
|---|---|---|---|
| `GET /api/orcamento/historico` | COMERCIAL, SUPERADMIN | não-SA só vê os próprios | **nenhuma** — todos veem todos |
| `GET /api/orcamento/historico/<id>` | COMERCIAL, SUPERADMIN | não-SA só o próprio | **nenhuma** |
| `GET /api/orcamento/historico/<id>/pdf` | COMERCIAL, SUPERADMIN | não-SA só o próprio | **nenhuma** |
| `POST /api/orcamento/historico/<id>/enviar-email` | COMERCIAL, SUPERADMIN | não-SA só o próprio | **nenhuma** |
| `DELETE /api/orcamento/historico/<id>` | COMERCIAL, SUPERADMIN | não-SA só o próprio | **mantida** (FR-006) |
| `GET /api/events/<id>` (bloco `venda`) | COMERCIAL, FINANCEIRO, SUPERADMIN | comercial não-SA só vê o orçamento que criou | **nenhuma** para o comercial; FINANCEIRO segue sem o bloco |
| `PATCH /api/events/<id>/orcamento` | `_can_manage_sale()` — COMERCIAL, FINANCEIRO, SUPERADMIN | não-SA só o próprio (404 ao vincular; 409 ao trocar/soltar; **re-aplicar no vínculo alheio passa batido** — só não passa hoje porque o 404 vem antes) | **vincular em evento sem orçamento: cai para COMERCIAL e SUPERADMIN** — FINANCEIRO continua no 404, por não ter o módulo; **trocar, soltar ou re-aplicar sobre vínculo alheio: mantida e ampliada**, com o 409 nomeando o autor (FR-011) |

## Verificação (`verify_301.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/301-orcamentos-visiveis-comercial/verify_301.py`, contra `manto_local`
(`DATABASE_URL` de `.local-db-url`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`). Login só por
`POST /api/auth/login`; escrita conferida por conexão separada; limpeza no `finally`.

Usuários descartáveis: **A** (COMERCIAL, autor dos orçamentos), **B** (COMERCIAL, não superadmin —
é quem prova a feature), **F** (FINANCEIRO, prova que o portão do módulo não mudou).

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | A salva um orçamento; B lista o histórico | a linha de A aparece para B, com `user_name` = nome de A | não |
| 2 | B abre `GET /historico/<id>` do orçamento de A | 200 com `quote` **e** `form_snapshot` (Recalcular funciona) | não |
| 3 | B lista com `user_id=<A>` e com `user_id=<B>` | o filtro por vendedor vale para não-superadmin e separa certo | não |
| 4 | B baixa o PDF do orçamento de A | 200 `application/pdf` | não |
| 5 | B envia o e-mail do orçamento de A | 200 `{"sent": true}` (destino descartável) **e** o registro de auditoria gravado com B, o orçamento e o destinatário — conferido por conexão separada (FR-013) | não |
| 6 | evento vinculado ao orçamento de A; B abre `GET /api/events/<id>` | `venda.orcamento` preenchido e id do orçamento presentes | não |
| 7 | B vincula o orçamento de A a um evento **sem** orçamento (`PATCH .../orcamento`) | 200 e o vínculo gravado, conferido por conexão separada (FR-011, 1ª metade) | não |
| 8 | **B tenta trocar/soltar o vínculo do orçamento de A** | 409 com `orcamento_de_outro`, **com o nome de A** na mensagem, e o vínculo intacto | **sim** |
| 9 | **B tenta re-aplicar do orçamento de A no evento já vinculado a A** — nas duas formas: com `aplicar_valores_duracao`+`sale_date`, e **só com `aplicar_equipe`** | recusa pela mesma regra, e `sale_value`, `sale_date`, `is_outside_sp` e a contagem de `EventRole` do evento **inalterados**, conferidos por conexão separada (FR-011, 2ª metade) | **sim** |
| 10 | **B tenta `DELETE` um orçamento de A que não tem evento vivo vinculado**; em seguida **A** apaga o mesmo | B leva **404** e o registro continua no banco (conexão separada); A conclui **200**. O par prova que o 404 veio da **autoria**, não do estado | **sim** (o de B) |
| 11 | **F (FINANCEIRO) tenta listar o histórico** | 403 — o portão do módulo não foi alargado | **sim** |
| 12 | **F (FINANCEIRO) tenta vincular o orçamento de A a um evento sem orçamento** | **404** — passar em `_can_manage_sale()` não dá acesso a orçamento alheio (FR-011, SC-005) | **sim** |
| 13 | limpeza | evento, orçamentos e usuários descartáveis apagados (`roles.clear()` antes do usuário) | — |

**Arranjo obrigatório do cenário 9** — sem ele a asserção **passa verde com a guarda quebrada**, e
vira o "verify que passa sem exercitar nada" do Princípio VIII. Aplicar é **idempotente**: só
acrescenta o que falta. Se o evento do cenário nascer vinculado pelo caminho normal, a equipe e o
fora de SP já estarão lá, e uma re-aplicação **aceita** não mudaria nada — a asserção "inalterado"
seria verdadeira dos dois jeitos. Então o evento precisa nascer com o vínculo **gravado direto no
banco, sem aplicar nada**, e:

- o orçamento de A tem de vender **fora de SP e equipe de apoio** (senão não há o que acrescentar);
- o evento tem de estar **sem valor de venda** e não ser cortesia/permuta (senão
  `aplicar_valores_do_orcamento` devolve `False` sozinho e a metade dos valores também nasce vazia);
- o orçamento tem de ter **total na duração pedida**.

**Arranjo obrigatório do cenário 10** — pelo mesmo motivo. O `DELETE` tem **duas** recusas: a
autoria (404) e o evento vivo vinculado (409). Se o orçamento de A usado aqui for um dos que os
cenários 6–9 amarram a eventos, o 409 recusaria sozinho, e o cenário passaria verde mesmo se a
trava de autoria tivesse sido solta junto com a de leitura — que é justamente o erro simétrico que
ele existe para pegar. Então este cenário usa um orçamento de A **criado só para ele, sem evento
vivo vinculado**, espera **404** (não "recusa") e fecha com o contraste: o mesmo `DELETE` feito
por A conclui 200.

**Conferência de tela** (Browser pane, Princípio "tela aberta"): `/orcamento/historico` logado como
B — coluna "Vendedor" preenchida, filtro de vendedor presente, "Ver"/"Recalcular"/"Baixar
PDF"/"Enviar e-mail" funcionando sobre a linha de A, e **sem** botão "Excluir" na linha de A; e um
evento vendido por A aberto como B, com a aba Comercial mostrando o resumo do orçamento. Tela
interna — não é superfície pública, então sem exigência de viewport mobile.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Uma pessoa do comercial encontra o orçamento de qualquer colega pelo histórico sem
  precisar de ajuda do superadmin, em uma tela só.
- **SC-002**: A contagem de orçamentos que uma pessoa comum do comercial enxerga no histórico é
  **igual** à que o superadmin enxerga com os mesmos filtros.
- **SC-003**: 100% das ações de leitura da tela (ver, recalcular, PDF, e-mail) concluem sobre o
  orçamento de um colega, sem mensagem de "não encontrado".
- **SC-004**: Em um evento vendido por outra pessoa, quem é do comercial vê o que o orçamento
  vendeu — hoje esse bloco aparece em 0% desses casos.
- **SC-005**: Nenhuma pessoa fora do comercial passa a enxergar orçamento algum: quem recebia
  recusa antes continua recebendo depois.
- **SC-006**: Nenhum orçamento é excluído por quem não é o autor nem superadmin, e a tela não
  oferece essa ação a quem não pode executá-la.
- **SC-007**: Nenhum evento vinculado ao orçamento de outra pessoa tem o vínculo trocado ou solto,
  nem o valor de venda ou a data da venda reescritos, por quem não é o autor daquele orçamento nem
  superadmin; a recusa nomeia quem pode resolver, então ninguém precisa perguntar "por que não
  deixou?".
- **SC-008**: Todo reenvio de orçamento de outra pessoa é reconstituível depois do fato — quem
  enviou, qual orçamento e para qual endereço — sem depender da memória de ninguém.
- **SC-009**: Uma pessoa do comercial sem nenhum orçamento próprio (hoje, a Fatima) deixa de abrir
  o histórico numa tela vazia e passa a encontrar o histórico da empresa no primeiro acesso.

## Fora de escopo

- **EducaManto**: `GET /api/educamanto/historico` **já** mostra o histórico de todos (a regressão
  nunca chegou lá). Continua como está, inclusive o corte do custo interno do caminhão para
  não-superadmin.
- **Alargar o módulo para FINANCEIRO ou outros papéis**: o pedido diz "setor comercial". O gate
  `_require_vendas()` de `orcamento_read.py` fica como está.
- **Gastos Extras, Comissões e Dashboard Comercial**: também escopam por pessoa, mas por decisão
  registrada (features 013, 179, 187, 196), não por regressão. Não se tocam aqui.
- **Paginação do histórico**: decidido nas Clarifications (2026-09-21) — o teto de 300 linhas fica
  e a tela abre com o time inteiro, mesmo sabendo que 90% das linhas são de um vendedor só. Se
  virar dor, entra como dívida em `docs/05`, não nesta feature.
- **Filtro "meus orçamentos" por padrão**: descartado na mesma decisão. A lista não nasce filtrada;
  quem quiser só os seus escolhe o próprio nome no seletor de vendedor.
- **Configuração de Preços** (`/api/orcamento/settings`): continua exclusiva do SUPERADMIN.
- **Reescrever a spec da feature 177**: o contrato dela descreve o que foi feito em julho e fica
  como registro histórico; a regra corrigida passa a morar em `docs/01`.

## Docs a atualizar

`docs/01` §3.13 (a regra de escopo do histórico, explícita, mais a linha de auditoria do reenvio de
orçamento alheio) e §4.3 (linha do `_require_vendas()` homônimo de `orcamento_read.py` — anotar que
o gate é de módulo e que **não há** checagem de dono, exceto no `DELETE`; e a regra de
`PATCH /api/events/<id>/orcamento`: vincular é livre, trocar/soltar/re-aplicar é do autor) ·
`docs/02` (tela Histórico de Orçamentos: coluna Vendedor e filtro de vendedor para todo o
comercial) · `docs/03` (entrada no topo, registrando que a 301 desfaz a regressão introduzida pela
177 em 23/07/2026).

## Premissas

- **"Setor comercial" = papel `COMERCIAL`** (mais SUPERADMIN, que já passa em tudo). Não inclui
  FINANCEIRO, que hoje leva 403 no módulo de Orçamento e continua levando.
- **"Ver e abrir" inclui as ações de leitura que saem do registro**: detalhe, Recalcular, PDF e
  reenvio de e-mail. Era exatamente o que a tela Jinja permitia antes de 23/07/2026 — o
  `ver_historico` carregava qualquer orçamento na sessão e PDF/e-mail saíam de lá, sem checagem de
  dono.
- **Excluir fica com o dono** porque foi decisão explícita e separada em `6b191e4`, tomada no mesmo
  commit que liberou a visualização. Restaurar a visibilidade não é motivo para reabrir essa.
- **Mostrar o autor de cada orçamento é parte de "ver"**: uma lista com orçamentos de terceiros sem
  dizer de quem são não é utilizável. (O EducaManto esconde o autor de não-superadmin; aqui a
  escolha é oposta e consciente — lá o histórico nunca teve coluna de vendedor.)
- **Reenviar o orçamento de um colega não falsifica remetente**: o e-mail de orçamento é
  institucional — assina "Manto Produções" com o telefone da empresa e pede resposta no próprio
  e-mail, sem nome nem contato do vendedor. Por isso FR-003 libera o reenvio sem risco de o cliente
  achar que falou com a pessoa errada; o que FR-013 registra é o fato, não uma correção de autoria.
- **Sem migration**: nada muda no banco; `user_id` já existe e continua guardando a autoria, e
  `AuditLog` já tem as colunas de que FR-013 precisa.
- O e-mail de teste do cenário 5 vai para endereço descartável — `manto_local` escreve em serviços
  reais (memória do projeto), então o cenário usa destinatário controlado.
