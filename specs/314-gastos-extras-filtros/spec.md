# Feature 314 — Gastos Extras na tela inteira, com filtros e as pagas recolhidas

**Branch**: `314-gastos-extras-filtros` (da `main` `c074657b`, worktree `C:\tmp\mp314`) · **Created**: 2026-10-21 ·
**Status**: Rascunho · **Migration**: nenhuma · **Nível**: 1 (feature — o dono pediu "seguindo a esteira do
SpecKit"; tela refeita) — constituição, Princípio VI

**Input**: pedido do dono: "Feature 314 — Gastos Extras: tela inteira e filtros. Página /gastos. (1) o scroll
lateral é horrível, nem consegue rolar; a página tem de ocupar a tela inteira na largura; (2) não há filtro nenhum;
as coisas já pagas podem colapsar num card de 'pagas' e ficar só as pendentes; filtros mais ou menos como funciona
na página de pagamentos."

## O pedido, nas palavras do dono *(obrigatório)*

> "Preciso que faça umas correções nessa página. Acho que ela foi feita antes de eu fazer diversas mudanças. Como,
> por exemplo, esse scroll lateral é horrível. Eu nem consigo fazer scroll. Por que ele não ocupa a tela inteira?
> Tem que ocupar a tela inteira, lateralmente e tal. E não tem filtro nenhum. Por exemplo, as coisas que já estão
> pagas, elas podem todas colapsar para um card de pagas e ficarem só as pendentes. Enfim, seria interessante ter
> esses filtros nessa página, mais ou menos como funciona na página de pagamentos."

**O sintoma no print (21/10/2026)**: a tabela fica presa numa coluna de largura fixa no meio da tela, com um vazio
à direita. A última coluna (Ações) é cortada: os botões aparecem só como bordas roxas, e o aviso "Devolução de
cancelado: travada." aparece só como "D… ca…". Para alcançar os botões é preciso rolar a tabela para o lado, e
essa rolagem fica no rodapé de uma lista de 186 linhas. Cada linha ocupa até ~300 px de altura porque o título do
evento quebra em cinco linhas. Os cartões do topo (Todos R$ 111.068,74 · 186; Pendentes R$ 2.420,59 · 18; Aprovados
R$ 106.992,35 · 164; Rejeitados R$ 1.655,80 · 4) só informam e não filtram. Os 164 aprovados, quase todos já pagos,
ficam misturados com os 18 que pedem ação.

**A página é antiga.** A estrutura vem da migração para o React (177, julho/2026) e do RBAC (179). Depois disso só
ganhou células (256, 306, 312). Nunca recebeu o tratamento que a 218 ("as telas param de espremer") e a 194/226/267
(cartões-filtro, busca, cartões no celular, estado na URL) deram à página de Pagamentos.

## Clarifications

### Session 2026-10-27

- Q: O que recolhe no cartão "Pagos" e o que fica à vista na lista principal? → A: só os pagos de fato. Recolhem o
  pago pela planilha, o pago no cadastro e o aprovado sem ninguém a pagar. Ficam à vista os que aguardam aprovação e
  os aprovados a pagar ou no banco, e cada linha diz em que ponto do pagamento está.
- Q: E os rejeitados? → A: cartão recolhido próprio ("Rejeitados", com quantidade e total), que abre com um clique,
  igual ao de Pagos.
- Q: A página abre em qual período? → A: todos os meses. Abre sem recorte de mês, para nenhum pendente antigo sumir.
  O mês é um filtro opcional, com ‹ ›, como em Pagamentos.

## Cenários e Verificação *(obrigatório)*

### História 1 — A lista cabe na tela, sem rolagem lateral (Prioridade: P1)

Quem gerencia gastos (Financeiro, Superadmin) abre Gastos Extras num computador. A página usa toda a largura ao
lado do menu. Todas as colunas, inclusive os botões de ação, aparecem sem rolar para o lado. Numa tela estreita
(notebook pequeno, tablet, celular) cada gasto vira um cartão empilhado, como na página de Pagamentos, e nada fica
cortado.

**Por que esta prioridade**: é a queixa número um. Hoje aprovar um gasto exige rolar a tabela para o lado e caçar
o botão.

**Verificação**: conferência de tela (skill `manto-conferir-tela`) em 1920, 1366 e 375 px de largura. O
`verify_314.py` não mede layout.

**Cenários de aceite**:

1. **Dado** um Superadmin numa tela de 1920 px, **Quando** abre `/gastos`, **Então** a lista ocupa a largura útil
   inteira ao lado do menu (sem coluna central de largura fixa) e não há barra de rolagem lateral na lista.
2. **Dado** uma tela de 1366 px (notebook comum), **Quando** abre `/gastos`, **Então** os botões Aprovar, Rejeitar,
   Editar e Excluir de cada linha aparecem inteiros sem rolagem lateral, e o aviso "Devolução de cancelado:
   travada." aparece inteiro.
3. **Dado** uma tela de celular (375 px), **Quando** abre `/gastos`, **Então** cada gasto aparece como cartão, com
   valor, situação, desembolso, evento e ações visíveis, sem rolagem lateral da página.

---

### História 2 — Só o que pede ação fica à vista; o que já foi pago recolhe num cartão (Prioridade: P1)

Ao abrir a página, a pessoa vê só os gastos que ainda pedem alguma coisa: os que esperam aprovação e os aprovados
que ainda não foram pagos. Os gastos já pagos ficam recolhidos num cartão "Pagos" com quantidade e total. Um clique
abre esse cartão e mostra a lista inteira deles. Os rejeitados também ficam recolhidos, num cartão separado.

**Por que esta prioridade**: é a segunda metade do pedido. Hoje 18 gastos que pedem ação se perdem entre 164
aprovados.

**Verificação**: cenários 1–4 do `verify_314.py` (a situação de pagamento de cada gasto chega à tela e bate com o
banco) + conferência de tela.

**Cenários de aceite**:

1. **Dado** gastos em todas as situações, **Quando** a página abre, **Então** a lista principal mostra só os
   pendentes de aprovação e os aprovados ainda não pagos, e cada gasto aparece em exatamente um grupo.
2. **Dado** a lista principal, **Quando** se olha a linha de um aprovado não pago, **Então** ela diz em que ponto do
   pagamento está ("a pagar" ou "no banco"), com o mesmo vocabulário da página de Pagamentos.
3. **Dado** o cartão recolhido "Pagos" com N gastos e total R$ X, **Quando** se clica nele, **Então** os N gastos
   aparecem, com as mesmas colunas e ações da lista principal, e um novo clique recolhe de novo.
4. **Dado** que um gasto pendente é aprovado na própria página e é do tipo que não passa pela planilha de
   pagamentos, **Quando** a lista se atualiza, **Então** ele sai da lista principal e vai para o grupo certo sem
   recarregar a página.

---

### História 3 — Filtros como na página de Pagamentos (Prioridade: P2)

A pessoa filtra a lista por texto (descrição, quem recebe, evento, autor), por categoria, por tipo de desembolso e
por mês. Os cartões de resumo do topo viram filtros clicáveis, como em Pagamentos. A contagem "N de M gastos em
exibição" e o total filtrado ficam à vista. Os filtros ficam no endereço da página: recarregar ou mandar o link
para alguém mantém o mesmo recorte.

**Por que esta prioridade**: o dono pediu "esses filtros" e nomeou Pagamentos como referência. Só funciona sobre
a página da História 1.

**Verificação**: conferência de tela (busca sem acento, combinação de filtros, limpar filtros, URL); os números dos
cartões vêm da situação provada nos cenários 2 e 3 do `verify_314.py`.

**Cenários de aceite**:

1. **Dado** a lista, **Quando** se digita "lalamove", **Então** só aparecem os gastos com esse termo em algum dos
   campos da busca (FR-007: descrição, desembolso, evento, autor e os demais), sem diferença de acento ou
   maiúscula, e a contagem e o total se ajustam.
2. **Dado** o filtro "Figurino" na categoria e um mês escolhido, **Quando** se aplica, **Então** só aparecem os
   gastos daquela categoria com data naquele mês, em todos os grupos (principal, Pagos, Rejeitados).
3. **Dado** um filtro ativo, **Quando** se clica em "Limpar filtros", **Então** a página volta ao estado de abertura.
4. **Dado** um filtro aplicado, **Quando** se recarrega a página ou se abre o mesmo endereço noutra aba, **Então** o
   mesmo filtro está aplicado.
5. **Dado** um filtro que não casa com nada, **Quando** se aplica, **Então** a página diz que nada casou e oferece
   limpar o filtro, em vez de uma tabela vazia muda.

---

### História 4 — Quem só lança gastos ganha a mesma tela, só com os seus (Prioridade: P3)

Quem não gerencia (qualquer papel que lança um gasto avulso) vê só os próprios gastos. Isso já é assim e continua.
Passa a ter a mesma largura, os mesmos grupos e os mesmos filtros, e um resumo dos próprios números.

**Por que esta prioridade**: a mesma página serve as duas pessoas. Não pode ficar quebrada para quem não é
Financeiro.

**Verificação**: cenários 5 e 6 do `verify_314.py` (o 6 deve falhar) + conferência de tela com um usuário sem papel
de gestão.

**Cenários de aceite**:

1. **Dado** um usuário de Casting com 3 gastos próprios, **Quando** abre `/gastos`, **Então** vê só os 3, agrupados
   do mesmo jeito, com filtros funcionando, e não vê autor nem gastos de outra pessoa.
2. **Dado** esse mesmo usuário, **Quando** pede a lista, **Então** nenhum número de resumo da empresa (total geral,
   gastos dos outros) chega a ele.

### Casos de borda

- **Aprovado sem ninguém a pagar** (sem tipo de desembolso). Esses gastos nunca entram na planilha de Pagamentos,
  então nunca viram "pagos" lá. No espelho local há 2 assim. Sem regra própria, ficariam para sempre na lista
  principal (ver FR-004).
- **Pago no cadastro** ("já pago" ao lançar, feature 128). Também nunca passa pela planilha. Conta como pago, mas só
  depois de aprovado: o pendente marcado "já pago" ainda está aguardando aprovação.
- **Pessoa sem nenhum gasto** (o não gestor que nunca lançou): a página diz "Nenhum gasto registrado ainda." e não
  mostra filtros vazios nem grupos.
- **"No banco"**: a planilha marcou que o pagamento foi agendado no banco mas ainda não confirmou. Fica na lista
  principal e mostra "no banco".
- **Devolução à cliente de evento cancelado** (travada, 306) e **multa de cancelamento**: seguem as regras atuais de
  ação e o aviso de trava, inteiro, em qualquer grupo.
- **Data futura** (o print mostra um gasto de 30/10/2026): o filtro de mês o encontra no mês dele; sem filtro de
  mês, ele aparece normalmente.
- **Grupo recolhido vazio** (ex.: zero rejeitados): o cartão some, ou mostra "nenhum", e não abre lista vazia.
- **Filtro que esvazia a lista principal mas casa com Pagos**: a página diz "Nenhum gasto aguardando aprovação ou
  pagamento." (o mesmo nome do título da lista, no formato de estado vazio do Princípio XV) no lugar da lista
  principal, e os grupos recolhidos aparecem embaixo com quantos casaram.
- **Ação que muda o grupo** (aprovar, rejeitar, excluir, editar): o gasto muda de grupo sem a página perder os
  filtros nem o grupo aberto.
- **Bloco do auditor de marketing** (256) sob a descrição: continua visível na linha e no cartão.

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: A página DEVE ocupar a largura útil inteira ao lado do menu, sem teto central de largura.
- **FR-002**: Em tela de computador a partir de 1366 px de largura, a lista DEVE caber sem rolagem lateral, com
  todas as colunas e todas as ações visíveis. Em telas menores, cada gasto DEVE virar cartão empilhado (o padrão de
  Pagamentos), sem rolagem lateral da página.
- **FR-003**: Cada gasto DEVE ter uma situação única para esta página, derivada do que já está gravado: **aguardando
  aprovação** (pendente), **a pagar** (aprovado, não pago), **no banco** (aprovado, agendado no banco), **pago**
  (aprovado e pago pela planilha, ou pago no cadastro) e **rejeitado**.
- **FR-004**: O aprovado sem ninguém a pagar (sem tipo de desembolso) DEVE contar como resolvido: vai para o grupo
  recolhido junto com os pagos, nunca fica para sempre na lista principal. O grupo recolhido "Pagos" reúne
  exatamente: pago pela planilha, pago no cadastro e aprovado sem desembolso. A lista principal reúne exatamente:
  aguardando aprovação, a pagar e no banco (Clarifications, 2026-10-27).
- **FR-005**: Ao abrir, a lista principal DEVE mostrar só os gastos que pedem ação (FR-004 diz quais). Os pagos DEVEM
  ficar num cartão recolhido "Pagos", com quantidade e total, que abre e fecha com um clique. Os rejeitados DEVEM
  ficar num cartão recolhido próprio, "Rejeitados", com quantidade e total, que abre e fecha como o de Pagos.
- **FR-006**: Os cartões de resumo do topo DEVEM ser filtros clicáveis, como em Pagamentos: clicar num cartão
  mostra só aquela situação. Um cartão neutro ("Todos") limpa o filtro. O cartão ativo fica marcado e há um "Limpar
  filtro" visível. Os cartões são, nesta ordem: Todos, Aguardando aprovação, A pagar, No banco, Pagos, Rejeitados.
  Com uma situação escolhida, a página mostra só ela, aberta, sem grupos recolhidos. Escolher "Pagos" mostra os
  pagos direto, sem precisar abrir o grupo.
- **FR-007**: A página DEVE oferecer busca por texto sem diferença de acento ou maiúscula, com vários termos que
  precisam casar todos, sobre descrição, observação, categoria, quem recebe, PIX, evento, autor, data (dd/mm/aaaa e
  ISO), rótulo da situação e valor (formatado e cru). O comportamento é o da busca de Pagamentos (`research.md` D6).
  Buscar "pago" casa com todo gasto na situação pago, de propósito.
- **FR-008**: A página DEVE oferecer filtro por categoria, por tipo de desembolso (reembolso, fornecedor, devolução
  à cliente, sem desembolso) e por mês da data do gasto. A página abre com todos os meses. O mês é um filtro
  opcional, com ‹ › para andar entre meses e um jeito visível de voltar a "todos os meses".
- **FR-009**: Os filtros DEVEM valer para todos os grupos ao mesmo tempo (principal, Pagos, Rejeitados). Os números
  dos cartões DEVEM refletir o recorte da busca, da categoria, do desembolso e do mês, mas não o da situação:
  escolher "A pagar" não zera os outros cartões, como em Pagamentos.
- **FR-010**: A página DEVE mostrar "N de M gastos em exibição" e o total em R$ do que está em exibição, num aviso
  lido por leitor de tela, como em Pagamentos.
- **FR-011**: Os filtros (busca, categoria, desembolso, mês e situação) DEVEM ficar no endereço da página, para que
  recarregar ou compartilhar o link mantenha o recorte. Trocar filtro não empilha histórico do navegador. Valor
  desconhecido no endereço (categoria que não existe, mês malformado) é ignorado: a página abre como se aquele
  filtro não estivesse lá.
- **FR-012**: Quando nenhum gasto casa com o filtro, a página DEVE dizer isso e oferecer limpar o filtro.
- **FR-013**: Todas as ações de hoje DEVEM continuar, com as mesmas regras de quem pode e do estado travado: Aprovar,
  Rejeitar, Editar, Vincular evento, Excluir, Ver nota fiscal, o aviso de devolução travada, o selo de evento
  cancelado e o bloco do auditor de marketing. Nenhuma ação muda de regra nesta feature. A confirmação de "Excluir"
  passa a ser um diálogo da casa que mostra a descrição e o valor do gasto ("Excluir este gasto?"), no lugar do
  alerta do navegador (Princípio V). "Cancelar" no pedido do motivo da rejeição desiste da rejeição. Antes da 314, o
  gasto era rejeitado assim mesmo, e isso era defeito, não regra (achado G9 do converge).
- **FR-014**: Depois de qualquer ação, o gasto DEVE ir para o grupo da nova situação sem recarregar a página e sem
  perder filtros nem o grupo aberto.
- **FR-015**: Quem não gerencia DEVE continuar vendo só os próprios gastos, com a mesma página, os mesmos grupos e
  filtros e um resumo dos próprios números. Nenhum total da empresa chega a essa pessoa.
- **FR-016**: Os valores DEVEM aparecer no padrão brasileiro pela fonte única de formatação (Princípio IX), e
  abrir/recolher grupos DEVE ter transição suave que respeita "reduzir movimento" (Princípio XI).
- **FR-017**: Carregando, a página DEVE mostrar o esqueleto. Se a lista não carregar, DEVE mostrar "Não foi possível
  carregar os gastos.", como hoje, com o mesmo invólucro de largura da página carregada.
- **FR-018**: Cada cartão-filtro DEVE ser um botão que diz se está ligado (anunciado a leitor de tela). Cada grupo
  recolhido DEVE ser um botão que diz se está aberto. As ações em ícone DEVEM ter nome acessível e dica com o mesmo
  texto ("Ver nota fiscal", "Editar", "Vincular evento", "Excluir"). Tudo DEVE ser alcançável por teclado.

### Entidades

- **Gasto extra** (`SpecialExpense`, tabela `special_expenses`, sem mudança de esquema): `status` (pendente /
  aprovado / rejeitado), `payment_status` (não pago / no banco / pago, escrito pela planilha de Pagamentos),
  `paid_at_creation` (pago ao lançar), `disbursement_type` (reembolso / fornecedor / cliente / nenhum), `category`,
  `expense_date`, `event_id`, autor. A "situação da página" (FR-003) é derivada desses campos e nada novo se grava.

### RBAC

- `GET /api/gastos` — mesmo gate de hoje: qualquer usuário logado. Financeiro e Superadmin recebem todos os gastos e
  o resumo da empresa. Os demais recebem só os próprios gastos e nenhum resumo da empresa. Se o payload ganhar
  campos, eles seguem a mesma regra; nenhum endpoint novo é previsto. A linha em `docs/01` §4.3 só muda se o
  payload mudar.
- As escritas (`POST /api/gastos`, aprovar, rejeitar, `PATCH`, `DELETE`, vincular-evento) não mudam.

## Verificação (`verify_314.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/314-gastos-extras-filtros/verify_314.py`, contra `manto_local` (`DATABASE_URL` de `.local-db-url`,
`FLASK_ENV=development`, `MANTO_SEM_THREADS=1`). Login só por `POST /api/auth/login`. Escrita conferida por conexão
separada. Limpeza no `finally`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Financeiro descartável pede `GET /api/gastos` | todo gasto traz uma `situacao` entre as cinco, e o número de gastos bate com o banco por conexão separada | não |
| 2 | Semeia um gasto em cada caso (aguardando, a pagar, no banco, pago pela planilha, pago no cadastro, aprovado sem desembolso, rejeitado, e pendente já pago no cadastro) | cada um chega com a situação certa (FR-003/FR-004; `research.md` D2) | não |
| 3 | Soma por situação dos itens do payload | bate, centavo a centavo, com a mesma regra escrita em SQL e rodada por conexão separada sobre o banco inteiro (SC-003: cada gasto em um grupo só) | não |
| 4 | Aprovar pela API dois semeados "aguardando" (um com reembolso, um sem desembolso) | no GET seguinte um chega `a_pagar` e o outro `pago` (FR-014, lado servidor) | não |
| 5 | Usuário de Casting descartável com 2 gastos próprios pede a lista | recebe só os 2, com `situacao`, e sem `totals` | não |
| 6 | O mesmo usuário de Casting procura os gastos semeados pelo Financeiro e o total da empresa, e tenta aprovar o próprio gasto pendente | não estão no payload dele; aprovar dá 403 e o banco (conexão separada) continua "pendente" | **sim** |
| 7 | Mutação: a regra trocada (pago no cadastro deixa de contar como pago) | o cenário 2 (tabela esperada do verify) E o 3 (a regra em SQL) caem pelo motivo certo — prova que o verify morde; nenhum oráculo chama a função mutada | **sim** |
| 8 | limpeza | gastos semeados e usuários descartáveis apagados (`roles.clear()` antes do usuário), conferido por conexão separada | — |

A busca (acento, vários termos) é TypeScript reaproveitado de Pagamentos e se confere na tela.

Conferência de tela (UI interna, skill `manto-conferir-tela`): `/gastos` como Superadmin em 1920, 1366 e 375 px.
Conferir sem rolagem lateral, grupos recolhidos, filtros na URL, aprovar e ver o gasto mudar de grupo, e devolução
travada inteira. Repetir em 1366 px com um usuário sem papel de gestão.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Em telas de 1366 px ou mais, aprovar um gasto pendente leva 1 clique a partir da abertura da página,
  sem rolagem lateral (hoje: rolar a tabela inteira até o rodapé, depois para o lado).
- **SC-002**: Ao abrir a página, a lista principal mostra exatamente os gastos aguardando aprovação, a pagar e no
  banco (no print de 21/10: os 18 pendentes mais os aprovados ainda não pagos), e não os 186.
- **SC-003**: 100% dos gastos aparecem em exatamente um grupo. A soma dos grupos é igual ao total da página.
- **SC-004**: Achar um gasto conhecido pelo nome do fornecedor ou do evento leva menos de 10 segundos (digitar na
  busca), sem rolar a lista.
- **SC-005**: Um link copiado com filtros, aberto noutra aba, mostra o mesmo recorte.
- **SC-006**: Nenhum gasto de outra pessoa e nenhum total da empresa chega a quem não gerencia (cenário 6 do verify).

## Fora de escopo

- Paginação no servidor ou filtro no servidor: a lista inteira (186 hoje) chega numa requisição, e o recorte é na
  tela, como em Pagamentos.
- Mudar regras de quem aprova, rejeita, edita ou exclui, ou a trava da devolução de cancelado (306/312).
- Trocar o `window.prompt` do motivo de rejeição por um diálogo do `@manto/ui`. Rejeitar não apaga, então não cai no
  Princípio V; é dívida da tela e vira candidata no `docs/05`. (A exclusão, que apaga, passa ao `ConfirmDialog`
  nesta feature: a ação é reescrita aqui e o Princípio V exige o diálogo — achado C1 do `/speckit-analyze`.)
- Seleção em massa (aprovar vários de uma vez) e exportar CSV.
- A página de Gastos Recorrentes (`/gastos/recorrentes`) e a página de Pagamentos.
- Marcar como pago a partir desta página: o pagamento continua sendo feito na planilha de Pagamentos.

## Docs a atualizar

`docs/02` (`/gastos` — layout, grupos, filtros, URL), `docs/03` (entrada no topo + linha no índice), `docs/01` §4.3 e
o shape do `GET /api/gastos` só se o payload mudar, `docs/05` (risca/registra dívida da tela, se houver).

## Premissas

- "Ocupar a tela inteira" = sem teto de largura central. A página fica com as margens internas de sempre e usa todo o
  espaço ao lado do menu lateral.
- "Pagas" usa o mesmo vocabulário de Pagamentos ("no banco", "pago"). A fonte da situação de pagamento é o que a
  planilha de Pagamentos grava. Esta página só lê.
- O filtro e a busca rodam na tela sobre a lista que já chega inteira, como em Pagamentos (feature 226). Com ~200
  gastos isso é instantâneo.
- A ordem dentro de cada grupo continua a de hoje: data do gasto, mais recente primeiro.
- O "Ver como" segue como hoje nesta tela: quem decide gestor × não gestor é o servidor, pelo papel real
  (`gastos_ops.is_financeiro`). Nada muda aqui.
- Os números do print (186 · 18 pendentes · 164 aprovados · 4 rejeitados) são de produção em 21/10. O espelho local
  está mais antigo (135 gastos, de 27/05 a 30/09/2026) e serve ao verify, não à contagem.
