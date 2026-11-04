# Feature 334 — De qual anúncio veio cada cliente

**Branch**: `334-crm-origem-do-anuncio` (da `333-crm-orcamento-na-conversa`, fora da `main`: o dono adiou a publicação)
· **Created**: 2026-11-04 · **Status**: Rascunho · **Migration**: sim, aditiva (2 tabelas novas e 4 colunas) · **Nível**: 1
(feature)

**Input**: pedido do dono (04/11): "Começar a 3b". É a fatia 3b da Fase 3 do `docs/PLANO_CRM_PROPRIO.md`: o canal de
campanha pelo anúncio, que alimenta o 6b (custo por evento de cada campanha).

## O pedido, nas palavras do dono *(obrigatório)*

> "Começar a 3b" (04/11)

O plano põe o canal de campanha como o segundo ganho em dinheiro do CRM: "A primeira mensagem de quem clica num anúncio
de WhatsApp ou do Direct chega com o ID do anúncio. Isso dá o custo por evento de cada campanha." Hoje nenhuma das
6.251 fichas da base tem origem nem campanha (o export do Kommo veio sem isso), e o Desempenho mostra "nenhum lead do
período veio com utm_campaign".

## Clarifications

### Session 2026-11-04

- Q: Como a Plataforma descobre a campanha, se a Meta manda só o ID e o título do anúncio? → A: **Perguntando à Meta
  pelo ID do anúncio**, um pedido por anúncio novo, guardado. Até a permissão de leitura de anúncios existir no app da
  Meta, fica só o anúncio, e a campanha entra depois sozinha.
- Q: A ficha guarda qual origem quando a cliente veio por mais de um anúncio, ou já tinha origem? → A: **As duas: o
  anúncio mais antigo e o mais recente** — "para campanhas de repescagem, por exemplo".
- Q: E a cliente que chama sem vir de anúncio? → A: **Marcar o canal** ("WhatsApp" ou "Instagram") como origem.

## Cenários e Verificação *(obrigatório)*

### História 1 — A conversa sabe de qual anúncio a cliente veio (Prioridade: P1)

Quando a cliente clica num anúncio "enviar mensagem" (WhatsApp) ou "abrir conversa" (Instagram), a Meta manda o anúncio
junto da primeira mensagem (ou, no Instagram, ao abrir a conversa). A Plataforma registra o contato pelo anúncio na
conversa: o anúncio, o título, o link (quando houver) e quando. O cabeçalho da conversa mostra "Veio do anúncio
"{título}"" e, quando conhecida, a campanha.

**Por que esta prioridade**: sem o registro na chegada, a origem se perde (a Meta manda uma vez só).

**Verificação**: cenários 1, 2, 4 e 10 do `verify_334.py`.

**Cenários de aceite**:

1. **Dado** uma mensagem do WhatsApp com o anúncio, **Quando** ela chega, **Então** o contato pelo anúncio fica
   registrado na conversa, uma vez só (o reenvio do mesmo aviso não duplica).
2. **Dado** a cliente que abre a conversa do Instagram por um anúncio, **Quando** o aviso chega (com ou sem mensagem),
   **Então** a conversa nasce e o contato pelo anúncio fica registrado.
3. **Dado** um clique numa publicação (não anúncio), **Quando** chega, **Então** o contato fica registrado como
   publicação, sem campanha.

---

### História 2 — A campanha vem da Meta (Prioridade: P1)

Para cada anúncio novo, a Plataforma pergunta à Meta o nome do anúncio e a campanha dele, e guarda a resposta: o mesmo
anúncio não é consultado de novo. Sem a permissão de leitura de anúncios (ou com a Meta fora do ar), o anúncio fica sem
campanha, e a varredura tenta de novo no dia seguinte; quando a campanha chega, ela entra na conversa e na ficha.

**Por que esta prioridade**: é a campanha que liga a cliente ao gasto no Desempenho.

**Verificação**: cenários 1, 6 e 7 do `verify_334.py`.

---

### História 3 — A ficha guarda o primeiro e o último anúncio (Prioridade: P1)

A ficha da cliente guarda o anúncio que a trouxe (o mais antigo) e o mais recente. O primeiro nunca é sobrescrito; o
mais recente muda a cada anúncio novo, para a repescagem. A origem da ficha ("Anúncio do WhatsApp", "Anúncio do
Instagram") e a campanha do primeiro anúncio entram nos campos de atribuição que o Desempenho já usa. A ficha nova da
cliente que chegou sem anúncio ganha o canal como origem ("WhatsApp", "Instagram").

A ficha mostra a origem, o primeiro anúncio e o mais recente (campanha, título e data).

**Por que esta prioridade**: é na ficha que o Desempenho conta lead e evento.

**Verificação**: cenários 1, 3, 4, 5 e 9 do `verify_334.py`.

**Cenários de aceite**:

1. **Dado** uma ficha sem origem, **Quando** a cliente chega pelo anúncio A, **Então** a ficha fica com origem "Anúncio
   do WhatsApp", campanha de A, e A como primeiro e mais recente.
2. **Dado** a mesma cliente, **Quando** ela volta pelo anúncio B, **Então** o mais recente vira B e o primeiro continua A.
3. **Dado** uma conversa que só ganha ficha depois (Instagram, ou ficha criada no envio do orçamento), **Quando** a
   ficha é ligada, **Então** ela recebe o primeiro e o último anúncio da conversa.
4. **Dado** uma conversa sem anúncio, **Quando** a ficha nasce por ela, **Então** a origem é "WhatsApp" ou "Instagram".
   Uma ficha antiga sem origem (do Kommo) ligada à conversa não ganha o canal: a conversa de hoje não diz como ela
   chegou.

---

### História 4 — O Desempenho conta os leads e as repescagens (Prioridade: P2)

O Desempenho passa a contar como lead do período também a ficha que entrou pela conversa (hoje só conta a importada do
Kommo). A tabela de campanhas ganha a coluna "Retornos": fichas que já existiam e voltaram por um anúncio da campanha
no período (a repescagem), com os eventos fechados depois.

**Por que esta prioridade**: fecha o ciclo campanha → lead → evento, que é o 6b.

**Verificação**: cenário 8 do `verify_334.py`, e a tela.

### Casos de borda

- **Sem token ou sem permissão**: o contato e o anúncio ficam registrados; só a campanha espera. Nenhum erro chega à
  cliente nem ao processamento da mensagem.
- **Ambiente local**: a consulta à Meta fica travada como o envio (a mesma trava); o resto funciona.
- **Mesmo anúncio em várias conversas**: uma consulta só à Meta.
- **Anúncio apagado na Meta** (404): fica registrado como "sem campanha", sem nova tentativa.
- **A campanha muda de nome na Meta**: vale o nome da consulta; não há reconsulta automática.
- **Ficha já com origem** (de um formulário com UTM, ou de outro anúncio): o primeiro anúncio e a origem não mudam; o
  mais recente, sim.
- **Ficha trocada na conversa** (333): a ficha nova recebe os anúncios da conversa; a antiga fica como estava.

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: A Plataforma DEVE registrar cada contato por anúncio ou publicação que chega no aviso da Meta (WhatsApp:
  o `referral` da mensagem; Instagram: o `referral` da mensagem ou o aviso de abertura da conversa), uma vez só por
  contato.
- **FR-002**: Para cada anúncio novo, a Plataforma DEVE consultar a Meta (nome do anúncio, campanha) depois de gravar o
  aviso, sem atrasar nem derrubar o processamento, e guardar a resposta para não consultar de novo.
- **FR-003**: Sem permissão ou com falha da Meta, a consulta DEVE ser tentada de novo pela varredura, no máximo uma vez
  por dia; anúncio inexistente (404) não é tentado de novo.
- **FR-004**: A ficha DEVE guardar o primeiro anúncio (nunca sobrescrito) e o mais recente (atualizado a cada contato
  novo), com as datas.
- **FR-005**: No primeiro anúncio, a ficha sem origem DEVE receber a origem ("Anúncio do WhatsApp" / "Anúncio do
  Instagram"), a fonte e o meio de atribuição e, quando conhecida, a campanha. A campanha que chega depois DEVE ser
  gravada também.
- **FR-006**: A ficha nascida pela conversa sem anúncio DEVE receber o canal como origem ("WhatsApp" / "Instagram").
- **FR-007**: Quando a conversa ganha ficha depois dos contatos (ligação manual, automática ou no envio do orçamento),
  a ficha DEVE receber o primeiro e o último anúncio da conversa, pelas mesmas regras.
- **FR-008**: O cabeçalho da conversa DEVE mostrar o anúncio mais recente da conversa (título e, quando conhecida, a
  campanha).
- **FR-009**: A ficha da cliente DEVE mostrar a origem, o primeiro e o mais recente anúncio (campanha ou título, data).
- **FR-010**: O Desempenho DEVE contar como lead do período a ficha pela data em que entrou na base (do Kommo ou criada
  na Plataforma) e mostrar, por campanha, os retornos (fichas anteriores ao contato que voltaram por anúncio da campanha
  no período) e os eventos fechados depois.
- **FR-011**: A consulta à Meta DEVE respeitar a trava do ambiente local e nascer desligada sem token.
- **FR-012**: Os textos novos seguem o Princípio XV.

### Entidades

- **Contato por anúncio** (tabela nova): conversa, canal, a chave do contato (única), o anúncio (ou a publicação), o
  tipo, o título, o link e quando.
- **Anúncio da Meta** (tabela nova, um por anúncio): o nome, a campanha (id e nome), quando foi consultado e o motivo da
  falha.
- **Ficha** (`clients`): o primeiro anúncio e quando; o mais recente e quando. A origem e a atribuição usam os campos de
  hoje (`lead_origin`, `utm_source`, `utm_medium`, `utm_campaign`).

### RBAC

- Nenhum endpoint novo. A conversa e a ficha ganham campos nos endpoints de hoje, com os gates de hoje
  (`pode_conversas`; `_require_vendas` da base de clientes). O Desempenho mantém o gate de hoje.

## Verificação (`verify_334.py`) *(obrigatório — Princípio VIII)*

Contra o `manto_local`, com disjuntor de rede e dublê da Meta (o aviso assinado e a consulta do anúncio). Login pela API,
conferência por conexão separada e limpeza no `finally`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Mensagem do WhatsApp com anúncio, ficha sem origem | contato registrado; consulta feita uma vez; ficha com origem, campanha, primeiro e mais recente | não |
| 2 | O mesmo aviso de novo; o mesmo anúncio em outra conversa | nada duplica; nenhuma consulta nova | não |
| 3 | A cliente volta por outro anúncio | o mais recente muda; o primeiro e a origem não | não |
| 4 | Instagram: abertura pelo anúncio sem mensagem, depois a ficha ligada à mão | conversa nasce; a ficha recebe o primeiro e o último | não |
| 5 | Ficha nascida sem anúncio (envio do orçamento, WhatsApp e Instagram); ficha antiga ligada | "WhatsApp" / "Instagram"; a antiga continua sem origem | não |
| 6 | A Meta recusa a consulta (sem permissão); a varredura no dia seguinte | sem campanha e com o motivo; depois a campanha entra no anúncio e na ficha | **sim** |
| 7 | Ambiente travado; sem token | nenhuma consulta sai; o contato fica registrado | **sim** |
| 8 | Desempenho | o lead da conversa conta na campanha; o retorno da ficha antiga conta em "Retornos" | não |
| 9 | Conversa e ficha na API | o anúncio no cabeçalho; a origem, o primeiro e o mais recente na ficha | não |
| 10 | Clique em publicação | registrado como publicação, sem consulta e sem origem de anúncio | não |
| 11 | Limpeza | registros e usuários de teste apagados | — |

Conferência de tela: o cabeçalho da conversa com o anúncio; a ficha da cliente com a origem; a tabela de campanhas do
Desempenho com "Retornos". Em desktop e 375×812.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Toda cliente que chega por anúncio da Meta fica com o anúncio registrado na conversa e na ficha.
- **SC-002**: Com a permissão de leitura de anúncios, a campanha aparece na ficha sem ação de ninguém.
- **SC-003**: O Desempenho mostra leads e eventos por campanha para as clientes que entram pelas Conversas.
- **SC-004**: Nenhuma mensagem deixa de ser processada por causa da consulta do anúncio.

## Fora de escopo

- O Google Ads e o UTM dos formulários (o 6a já cobre o formulário).
- A linha do tempo da ficha e o funil derivado (3c).
- Reconsulta de campanha renomeada; edição manual da origem.
- Atribuição multi-toque com pesos (só primeiro e último).

## Docs a atualizar

- `docs/01`: as tabelas, as colunas, a consulta à Meta e a variável.
- `docs/02`: Conversas (cabeçalho), Clientes (ficha) e Marketing → Desempenho (Retornos).
- `docs/03`: entrada no topo.
- `docs/04`: invariantes da atribuição.
- `docs/05`: a permissão de leitura de anúncios.
- `docs/PLANO_CRM_PROPRIO.md`: Fase 3b.

## Premissas

- **Token**: a consulta usa o token do WhatsApp (usuário do sistema do portfólio), que precisa da permissão de leitura de
  anúncios e da conta de anúncios atribuída. Uma variável própria (`META_ANUNCIOS_TOKEN`) sobrepõe, se o dono preferir
  outro usuário.
- **Atribuição**: origem "Anúncio do WhatsApp"/"Anúncio do Instagram", fonte `meta` (o Desempenho já a lê como "Meta
  Ads") e meio `anuncio`. A orgânica fica só com a origem.
- **Repescagem**: um retorno é o contato por anúncio, no período, de uma ficha que entrou na base antes do dia do
  contato.
