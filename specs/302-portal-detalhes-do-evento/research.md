# Pesquisa — Feature 302

**Plano**: [plan.md](./plan.md) · **Spec**: [spec.md](./spec.md) · **Data**: 2026-09-22

As decisões técnicas e, principalmente, **o que foi rejeitado e por quê**. Todo número veio de
consulta ao espelho `manto_local`; toda citação de código foi conferida contra a HEAD.

---

## R1 — Um bloco `before_event`, não seis chaves soltas

**Decisão**: `_role_summary` ganha **uma** chave, `before_event`, que é `None` quando não há nada
a mostrar. Dentro dela, `makeup`, `departure` e `rehearsals`.

**Motivo**: a tela precisa responder "existe bloco?" com um teste, não com seis. Se as chaves
fossem soltas (`makeup_time`, `makeup_location`, `departure_time`, …), a decisão de renderizar a
seção migraria para o React, que teria de conhecer a regra "local sem hora não conta" (R3) — e a
mesma regra teria de ser repetida nas duas telas que mostram o bloco. Com o bloco, a regra fica
no servidor, em um lugar, e a tela faz `if (!role.before_event) return null`.

**Alternativa rejeitada**: devolver `before_event` sempre como objeto, com listas e campos vazios.
Obriga a tela a inspecionar o conteúdo para decidir se desenha — o mesmo problema, um nível
abaixo.

---

## R2 — `rehearsals` é lista, sempre

**Decisão**: lista, mesmo quando há um só ensaio; `[]` quando não há nenhum.

**Motivo**: o modelo permite N (`parent_event_id` é FK comum, com a coleção `ensaios` em
`app/models.py:352-357`), o payload interno **já é lista** (`app/api/agenda_read.py:769-778`), a
tela interna já itera — e o espelho tem um caso real: **52 pais com um ensaio, 1 com dois**. Um
objeto único esconderia o segundo em silêncio, que é exatamente a classe de defeito que esta
feature vem desfazer.

**Nota de honestidade**: a primeira redação da spec afirmava que o espelho **não** tinha nenhum
show com dois ensaios. Tinha. Eram 54 filhos para 53 pais e a aritmética não fechava; ninguém a
conferiu até uma passada adversarial. Corrigido antes de fechar a iteração 1 do checklist.

---

## R3 — O que faz a linha existir é a HORA, não o local

**Decisão**: `makeup` e `departure` só existem no bloco quando há **horário**. Sem hora, não há
linha, mesmo que o local esteja preenchido.

**Motivo, medido**: o campo "Local de saída" do formulário interno já **nasce preenchido** com
`"Manto Produções"` (`LogisticaSection.tsx`), então quem salva a seção sem mexer nos horários
grava o local sozinho. No espelho: **7 eventos** com local de saída e sem horário, e **1** com
local de maquiagem sem horário. Sem esta regra, 8 cards mostrariam `Saída: Manto Produções` sem
hora nenhuma — ruído com cara de informação, que é pior que ausência.

A hora é o dado acionável; o local é companhia dela. Bônus: a regra fica simétrica com a condição
do aviso interno (R10), que também olha para a hora.

---

## R4 — A tradução do local de maquiagem mora no servidor, e serve às três superfícies

**Decisão**: `MAKEUP_LOCATION_LABELS` + `makeup_location_label()` em `app/calendar/event_ops.py`,
**colados em `resolve_makeup_location` (`:83-91`)** — o módulo que codifica é o que decodifica.
Mapa: `"manto"` → `Manto Produções`, `"local"` → `No local do evento`, qualquer outro valor →
verbatim (é endereço livre digitado pela produção).

**Motivo**: o banco guarda código. No espelho só existem `manto` (18) e `local` (2) — **nenhum
endereço livre ainda**, mas o formulário permite um, então a função não pode ser um `dict` cego.
E o defeito não é só do portal: `app/email_service.py:231-233` concatena o valor cru, então o
artista **já recebe hoje** `Maquiagem: 14:00 — manto` por e-mail; e
`frontend/apps/internal/src/components/EventDetail/CastingSection.tsx:124` passa o mesmo valor cru
para a mensagem de WhatsApp, que escreve `📍 Local: manto`. Três superfícies, um defeito.

**Alternativa rejeitada**: traduzir no React do portal. Deixaria o e-mail errado, e poria a regra
em duas linguagens desde o nascimento.

**Duplicação aceita e registrada**: `LogisticaSection.tsx:15-20` tem um `makeupLocationLabel` em
TypeScript, e ele **continua existindo** — aquele app precisa da distinção preset x endereco livre
para montar o `<select>` do formulário e para o texto de leitura. O que muda é o **alcance**: a
mensagem de WhatsApp (`CastingSection.tsx`) passa a usar a mesma função, o que pode exigir movê-la
de dentro de `LogisticaSection.tsx` para um lugar que os dois enxerguem, **dentro do app interno**.
Não é promover para `@manto/ui` nem reescrever em outro lugar: é tirar de dentro de um componente
uma função que dois componentes usam. A duplicação Python x TypeScript **permanece** e entra em
`docs/05`.

**Divergência de texto, achada na refutação e resolvida de propósito**: o `makeupLocationLabel` do
app interno devolve `"Local do evento"`, e o contrato do portal pede `"No local do evento"`. **Não
são a mesma frase e não deveriam ser.** A do formulário é opção de `<select>` para quem preenche
("onde é a maquiagem? Manto Produções / Local do evento"); a do portal é uma linha corrida que o
artista lê no celular ("Maquiagem 14:00 — No local do evento"). O que não pode existir é uma
**terceira** redação: a spec tinha uma, no caso de borda, e foi alinhada.

---

## R5 — O portal ganha o seu próprio formatador de faixa; o do app interno **não** sobe

**Decisão**: `formatDateTimeRange(start, end)` em `frontend/apps/portal/src/lib/format.ts`. Sem
`end`, cai em `formatDateTime`.

**Motivo**: procurei antes (Princípio I é "verificar antes", não "promover sempre"). `formatRange`
existe em `frontend/apps/internal/src/components/EventDetail/parts.tsx:43-47` e produz
`05/07/2026 12:00 — 16:00`: data numérica onde o portal usa `28 de jul` (`format.ts:37-42`), e
travessão onde o pedido do dono é "20:00 **às** 23:00". Adotá-la quebraria o estilo mobile-first
do portal; promovê-la a `@manto/ui` promoveria o formato errado. `format.ts` **já é** a fonte única
declarada do app (`:1-11`) e já reexporta de `@manto/ui` o que é de fato comum (`:62`).

**Consequência registrada**: fica uma cópia conceitual entre os dois apps. Vai para `docs/05`.

---

## R6 — O payload manda `role_type`; o rótulo é escolhido na tela

**Decisão**: `"role_type": role.role_type` no payload — o código do modelo (`character` |
`extra`), não a palavra pronta.

**Motivo**: é a convenção do próprio `_role_summary`, que já manda `payment_status` e
`invite_status` como código e deixa a tela traduzir. Mandar o rótulo pronto criaria uma terceira
convenção no mesmo dicionário. E a tela **não está deduzindo RBAC nem regra de negócio** aqui — o
servidor diz qual é a natureza da vaga, a tela escolhe a palavra. É o que FR-012 pede.

**O que não fazer**: deduzir a natureza pelo `character_name` ("se começa com 'Técnico'…"). Seria
a regra espalhada em string mágica, contra o Princípio II.

---

## R7 — Uma consulta agregada para os ensaios, e o N+1 antigo morre junto

**Decisão**: `_antes_do_evento(roles) -> dict[int, dict]` monta os blocos de **todos** os eventos
da rodada em uma consulta, e `_role_summary` recebe o bloco pronto por parâmetro — exatamente como
já recebe `has_figurino`. Além disso, `.options(selectinload(EventRole.event))` nas quatro
consultas de `get_agenda` e `get_historico`.

**Motivo**: `EventRole.event` é backref `lazy=True` (`app/models.py:328`), então `_role_summary`
**já dispara hoje** um SELECT por escalação — o N+1 é anterior a esta feature. Ler
`event.ensaios` dentro do laço (também `lazy=True`) dobraria isso. O padrão a copiar está no
mesmo arquivo, em `events_with_visible_figurino` (`portal_ops.py:112-165`), cuja própria docstring
explica: *"custa duas consultas para a agenda inteira … e não uma por evento: o histórico de um
talento antigo tem centenas de linhas"*.

`selectinload` não é novidade no repositório: é o que consertou o N+1 do catálogo na feature 300
(`app/admin/catalog_character_ops.py:371`, `app/api/admin_catalogo_read.py:104`). SQLAlchemy
2.0.45 no `.venv`.

**Tarefa própria no `tasks.md`**: o `selectinload` é melhoria lateral e tem de aparecer no diff
como decisão, não como efeito colateral de outra tarefa.

**Alternativa rejeitada**: `joinedload`. Para uma coleção traria linhas duplicadas; para o
many-to-one funcionaria, mas `selectinload` é o que o repositório já usa e mantém a consulta
principal legível.

---

## R8 — A lista de passados **fica** no payload, mesmo saindo da tela

**Decisão**: `get_agenda` continua devolvendo `history`. Só o `PortalAgendaPage` para de usá-la.
Remover do payload é tarefa do ciclo seguinte, registrada em `docs/05`.

**Motivo**: `manto-backend` e `manto-frontend` são **dois serviços** no `render.yaml`, com
`autoDeploy` cada um. Eles não trocam de contêiner no mesmo instante. Existe, portanto, uma janela
de **servidor novo com bundle velho**, e o bundle velho executa `agenda.history.map(...)`
(`PortalAgendaPage.tsx:153`): `undefined.map` é exceção, e o artista vê tela branca no celular.
O custo de manter é uma lista que ninguém lê por um ciclo; o custo de remover é o portal fora do ar
para quem não recarregou.

**O simétrico, e é por isso que ele também é regra**: na janela oposta — bundle novo com servidor
velho — os campos novos não existem. Por isso `before_event` e `role_type` nascem **opcionais** no
TypeScript, e a tela se comporta como hoje quando eles faltam (FR-013b).

---

## R9 — A observação do ensaio não vai para o portal

**Decisão**: o item de ensaio leva `start_at`, `end_at` e `location`. **Sem `description`.**

**Motivo, medido**: das 40 descrições de ensaio preenchidas, **23 começam com `"Evento em:"`**
seguido do endereço **do show**, e as outras 17 também são endereços (`"Manto Produções R. Olga
Camelini, 147…"`, `"Ensaio no Espaço de Artes Manto Produções…"`). **Nenhuma** é orientação de
preparo — o `"Ex.: levar figurino completo"` é só o placeholder do formulário
(`EnsaioSection.tsx`). Expor o campo poria, sob o rótulo "Ensaio", o endereço do **show** em mais
da metade dos casos: o artista leria "Ensaio · Belém - PA" e iria para o lugar errado. O
`location` do ensaio está preenchido em 100% dos 54 e é o dado certo.

**Efeito colateral bom**: evita a armadilha do HTML. `CalendarEvent.description` vem do Google e
pode conter marcação; hoje nenhuma descrição de ensaio tem tag, mas o portal não precisa aprender a
limpar HTML para esta feature.

**Registrar em `docs/05`**: reabrir quando o campo Observações do ensaio for usado como
observação.

---

## R10 — O aviso interno é um chip na faixa de pendências, não uma notificação

**Decisão**: entra em `calcularPendencias` (`ResumoSection.tsx:307`), a faixa de chips da aba
Resumo onde já vivem Elenco, Presença, Figurino, Agenda, Contrato, Recebimento e Evento
confirmado. Cada chip tem `ok` e leva à aba que o resolve — o chip novo leva a Produção. Um
alerta em linha dentro de `LogisticaSection` completa: o chip descobre, o alerta explica.

**Motivo**: é o mecanismo que já existe para exatamente esta pergunta — *"falta o quê aqui?"*. Não
há estado a manter, nem emissão, nem deduplicação: a condição é calculada do payload que a página
já recebe. **Zero mudança de backend** — `makeup_time`, `departure_time`, `start_at` e o elenco já
saem em `agenda_read.py`.

**Alternativa rejeitada: a notificação interna da feature 272.** Existe e funciona, mas a razão de
não servir está na docstring do próprio módulo: uma notificação ali é *"um registro derivado de um
fato que o banco já gravou"*, emitida *"no mesmo ponto do código que grava o fato"*. Logística em
branco é **ausência de fato** — não existe instante de emissão. Emitir exigiria uma rotina de
fundo com claim atômico, e o aviso nasceria em 11 eventos de uma vez, virando o ruído que o
desenho de destinatários da 272 foi feito para evitar.

**Alternativa registrada, fora de escopo**: uma lista "logística pendente" no Dashboard, no molde
de `compute_ensaio_tasks` (`app/api/dashboard_service.py`). O dono pediu a tela do evento.

**Condição, item a item**:

| Parte da condição | Por quê |
|---|---|
| quem abre pode editar o evento | é o mesmo portão do formulário e do `PATCH /api/events/<id>/logistics`. Cobrar de quem não pode resolver é ruído — e a tela nunca adivinha permissão |
| evento **futuro** | sem isso, os ~700 eventos passados acendem para sempre. Comparar por `start_at`, nunca por `toISOString()` |
| ao menos uma pessoa escalada e não dispensada | sem elenco não há quem informar. É a mesma regra do chip "Elenco" |
| falta **horário** de maquiagem **ou** de saída | a hora é o critério (R3): o local sozinho é resíduo do formulário em 7 eventos |

Medido: a condição acende hoje em **11 eventos** — os mesmos 11 eventos futuros com elenco, todos
sem logística. Pouco o bastante para ser lido, longe de virar bandeira permanente.

---

## R11 — O bloco vai também para Convites, e não vai para o Histórico

**Decisão**: `before_event` é anexado às listas de **convites pendentes** e **eventos futuros**.
No histórico vai `None`.

**Motivo (Convites)**: decisão do dono, e a medição a sustenta — há **4 convites pendentes** em
eventos futuros e **2 são de eventos que já têm ensaio marcado**. O card de convite é o único
lugar da plataforma onde a informação muda uma decisão que ainda não foi tomada; é o mesmo
argumento que desceu o cachê para lá (a docstring de `_role_summary` registra: *"o artista precisa
saber quanto vai receber **antes** de aceitar o convite"*).

**Motivo (Histórico)**: preparação para um evento que já aconteceu é ruído — e anexar o bloco
custaria a consulta agregada sobre as centenas de linhas do histórico de um talento antigo, por
nada.

---

## R12 — Ordenação e filtro dos ensaios

**Decisão**: a consulta filtra `event_type == "ENSAIO"` e `cancelled_at IS NULL`, e ordena por
`start_at` crescente.

**Motivo da ordenação**: a relação `ensaios` **não tem `order_by`** (`app/models.py:352-357`), e o
Postgres devolve em ordem arbitrária — que muda depois de um UPDATE. O artista com dois ensaios
os veria trocando de lugar entre visitas. O payload interno já resolve assim
(`agenda_read.py:777`); copiamos.

**Motivo do filtro de cancelado**: hoje há zero ensaios cancelados, então é cinto de segurança. O
cancelamento genérico da feature 224 não é impedido de alcançar um evento-filho, e um ensaio
cancelado aparecendo no card do artista seria pior que não aparecer.

---

## R13 — Ensaio no verify: escrita direta no banco, nunca pelo endpoint

**Decisão**: o `verify_302.py` insere o evento-filho com `INSERT`, com `google_event_id`
descartável, e apaga no `finally`.

**Motivo**: `POST /api/events/<id>/ensaios` chama `insert_event` e **cria o evento no Google
Agenda da empresa**. As travas de ambiente (`_suppress_mail`, `_suppress_calendar_invites`) cobrem
e-mail e convite — **não** a criação do evento. O espelho `manto_local` carrega token real do
Google; um verify descuidado sujaria a agenda de produção.

Pela mesma razão, o verify **nunca** cria `EventRole` com `character_name` inventado (o sync do
Google apaga a role e dispara e-mail de remoção a gente de verdade): assume uma role existente com
`talent_id IS NULL` e a devolve ao estado original na limpeza.

---

## R14 — O "Jinja legado do portal" que todo mundo cita **não existe mais**

**Achado**, e ele muda uma linha de regressão de cada artefato: `app/talent_portal/routes.py` tem
**82 linhas** e define exatamente duas coisas — `_is_portal_photo_path` e a rota
`/portal/photo/<caminho>`. As 20 rotas Jinja do portal (login, primeiro acesso, senha, termos,
home, histórico, perfil, mídia, convites, figurino e avaliação) foram removidas na fase 2 da
remoção do Jinja, e `app/templates/portal/` está **vazio**.

**Por que isso quase virou um erro nosso**: a conclusão que os artefatos tiravam — "só `get_agenda`
e `get_historico` chamam `_role_summary`" — está **certa**, e foi confirmada por varredura. Mas a
**razão** escrita era falsa: "porque o Jinja legado tem consultas próprias". Essa frase veio da
docstring de `get_agenda` (`portal_ops.py:211-216`), que ainda descreve um `home()`/`historico()`
que não existe. Conclusão certa, motivo errado — o tipo de coisa que sobrevive a uma revisão
porque o resultado confere.

**O que fica registrado como dívida** (não é escopo desta feature consertar):

- `docs/02` §C.1 lista as rotas Jinja do portal como "ainda registradas";
- as docstrings de `portal_ops.get_agenda`, `app/api/portal_agenda.py`, `portal_ratings.py`,
  `portal_profile.py` e `portal_auth.py` citam a "view Jinja legada" ou a sessão compartilhada com
  ela;
- `docs/04` §5 dá `routes.py` como tendo 974 linhas.

A única coisa que esta feature precisa garantir é o que a constituição já manda: **não criar Jinja
novo**. E não cria.
