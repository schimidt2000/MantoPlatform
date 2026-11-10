# Pesquisa (Phase 0) — Feature 339

Decisões técnicas que a spec deixou para o plano. Cada uma: **Decisão · Por quê · Alternativas**.
Citações `arquivo:linha` conferidas na `main` em `96837811`.

## R1 — Teto autorizado mora na vaga, em colunas próprias

**Decisão**: três colunas novas em `event_roles`: `teto_autorizado Numeric(10,2)`,
`teto_autorizado_por Integer FK users.id`, `teto_autorizado_em DateTime` (hora de SP). O teto efetivo
passa a ser `max(cache_cap + parcela_do_carrinho, teto_autorizado or 0, cache_value_atual or 0)` —
o último termo é a regra da 238 mantida como piso (o cachê **atual** da pessoa nunca é rebaixado por
quem só reabre o card), mas o que sobrevive à troca de pessoa é o `teto_autorizado`.

Regras de escrita, todas em `casting_ops.assign_role` (`app/calendar/casting_ops.py:118`, núcleo dos
dois adaptadores):
- Só grava quando `is_superadmin`, `role.cache_cap is not None`, a vaga fica **com talento** e o cachê
  salvo é > 0. Tirar a pessoa (talento vazio) nunca mexe no teto autorizado — é exatamente o caminho
  que perdeu os R$ 400 no evento 1423.
- Cachê salvo > `cache_cap + parcela` → `teto_autorizado = cachê`, com autor e data.
- Cachê salvo ≤ `cache_cap + parcela` → `teto_autorizado = NULL` ("o último valor do Superadmin
  manda", premissa da spec).
- Vaga sem `cache_cap` não tem teto nenhum, logo não há o que autorizar.

A nota do log "acima do cap — autorizado pelo admin" (`casting_ops.py:276,295`) passa a comparar
contra o teto efetivo **sem** o cachê atual: o Casting salvando os R$ 400 já autorizados não é
"autorizado pelo admin" de novo.

`agenda_read._serialize_role` espelha a fórmula em `cache_cap_efetivo` (fonte do aviso da tela, que
o Casting vê sem o número) e manda, só para Superadmin, `teto_autorizado`, `teto_autorizado_por_nome`
e `teto_autorizado_em`.

**Por quê**: o teto da 238 vivia no `cache_value`, que é da pessoa; qualquer "tirar e pôr" o zerava.
Coluna própria também sobrevive ao recálculo de teto da troca de tipo e do vínculo de orçamento (R3,
R4), que reescrevem `cache_cap`.

**Alternativas**: (a) sobrescrever `cache_cap` com o valor autorizado — rejeitada: o recálculo da troca
de tipo apagaria a autorização, e a conta do teto (`cache_cap_note`) perderia o sentido; (b) manter o
cachê na vaga ao tirar a pessoa — rejeitada: muda o fluxo do card e põe dinheiro em vaga sem ninguém.

**Preenchimento (FR-005)**: na própria migration, `UPDATE event_roles SET teto_autorizado =
cache_value WHERE cache_cap IS NOT NULL AND cache_value > cache_cap AND does_transport IS NOT TRUE`
(autor e data ficam `NULL`; a tela do Superadmin diz "autorizado antes da 339"). Vagas com carrinho
ficam de fora: a parcela é calculada em tempo de execução (`valor_transporte_papel`) e o cachê delas
pode estar acima do cap só pela parcela — o piso do cachê atual (acima) as protege até a próxima
troca.

## R2 — Normalização de nome e contagem no título

**Decisão**: uma função pura nova `contar_personagens(titulo) -> Counter[str]` em
`app/calendar/titulo_ops.py` (módulo novo, sem `flask.request`), que aplica `parse_characters`
(`app/calendar/routes.py:2087`, import tardio, como os outros `_ops`) e conta por
`orcamento_evento_ops._chave` (`app/calendar/orcamento_evento_ops.py:807`: sem acento, sem caixa,
espaços colapsados). A mesma `_chave` compara o nome da vaga. Funções irmãs:
`tirar_ultima_ocorrencia(titulo, nome)` e `acrescentar_personagem(titulo, nome)` — preservam o prefixo
`(TIPO)` e a grafia do resto do título; o nome acrescentado vai em maiúsculas.

**Por quê**: `parse_characters` já é a régua do sync (prefixo de tipo, nomes reservados); `_chave` já
casa vaga × orçamento no vínculo 273 e na 322. Reusar os dois evita uma terceira normalização.

**Alternativas**: comparação exata por `character_name` como o sync faz hoje (`routes.py:2546`) —
rejeitada: é ela que deixa "STORMTROOPERS" × "Stormtroopers " divergirem.

## R3 — Recálculo de teto na troca de tipo (FR-007/008)

**Decisão**: função nova `recalcular_tetos_pelo_tipo(event, *, show: bool) -> list[MudancaDeTeto]` em
`app/calendar/teto_ops.py` (módulo novo). Passos:
1. Sem `event.orcamento_history_id` → devolve lista vazia (nada a recalcular; o aviso sai igual).
2. `snapshot_do_orcamento(entry)` (`orcamento_evento_ops.py:65`), **cópia profunda**, e liga/desliga
   `show` em cada performer `ator` e `especial`; `cantor` é sempre show na tabela (`routes.py:3160`).
3. `_compute_performer_caches(snap, horas_extra=…, data_evento=data_do_evento(event))`
   (`routes.py:3047`) com a duração real (`_duracao_do_evento`, `_chave_cache`) — a mesma chamada do
   vínculo (`orcamento_evento_ops.py:860`). `has_show` sai dos performers, então o coordenador vai
   sozinho para a coluna de show.
4. Casa itens × vagas pelo `_chave(label)`, cada item servindo uma vaga (mesmo laço de
   `aplicar_equipe_do_orcamento`, `orcamento_evento_ops.py:871-894`); coordenadores em sequência
   (`:905`). Para cada vaga casada: `cache_cap` e `cache_cap_note` novos. Vaga com teto que não casou
   entra na lista "teto não recalculado" do aviso.
5. Devolve `(vaga, teto_antigo, teto_novo)` para o `EventLog` (FR-011) e para o texto do aviso.

Chamada em `event_ops._entrar_em_show` e `_sair_de_show` (`app/calendar/event_ops.py:433,455`), que
já rodam **depois** do push do prefixo ao Google (`_sincronizar_e_trocar_tipo`, `:609`) — troca
desfeita (409 `EventTypeChangeBlocked`) não recalcula nem avisa (caso de borda da spec).

**Por quê**: é a conta da criação, com a única diferença do "show"; nenhuma tabela nova de preço.

**Alternativas**: (a) somar uma diferença fixa (show − receptivo) ao teto — rejeitada: cantor,
especial e coordenador têm tabelas próprias; (b) usar `perfil_vendido` (322) — rejeitada: é texto para
humano e está vazio nas vagas anteriores à 322 (caso do 1423).

`_entrar_em_show` passa também a chamar `notify_ensaio_team(event)` (`event_ops.py:79`), o e-mail que
o sync já manda quando vê um SHOW novo (`routes.py:2460,2497`) — a troca pela plataforma era a única
porta de "virar SHOW" que não avisava o Ensaio por e-mail.

## R4 — Vínculo de orçamento reescreve o teto (FR-025)

**Decisão**: `aplicar_equipe_do_orcamento` (`orcamento_evento_ops.py:843`) ganha o parâmetro
`reescrever_tetos: bool`. `set_event_orcamento` (`:1126`) passa `True` quando `novo_vinculo` (troca
ou primeiro vínculo); reaplicar o mesmo orçamento continua idempotente ("só onde não havia"). As
mudanças entram no relatório e no `EventLog`.

**Por quê**: a regra de hoje ("nada é removido ou rebaixado") protege contra reaplicar o mesmo
orçamento; um orçamento **novo** é justamente a nova verdade do que foi vendido.

**Alternativas**: endpoint separado "aplicar tetos do orçamento" — rejeitada: mais um botão para a
Comercial lembrar.

## R5 — Vaga a mais: comparação título antigo × novo (FR-018..024)

**Decisão**: função `reconciliar_vagas_pelo_titulo(event, titulo_antigo, titulo_novo, *, autor) ->
Resultado` em `titulo_ops.py`:
1. `perdidos = {nome: antigo[nome] - novo[nome]}` só para nomes cuja contagem caiu.
2. Para cada nome perdido, `vagas = [r for r in event.roles if r.role_type == "character" and
   _chave(r.character_name) == nome]` e `excedente = len(vagas) - novo[nome]`; se ≤ 0, nada.
3. Remove até `excedente` vagas **sem talento** (dispensadas primeiro, depois maior `id`), com
   `EventLog` "STORMTROOPERS: o título pede 1, havia 2 — vaga vazia removida".
4. Sobrou excedente → marca as vagas **ocupadas** daquele nome com `sobrando_desde` (coluna nova em
   `event_roles`, hora de SP) e emite o aviso `evento.vaga_sobrando` (R7).

Marca persistida (e não calculada a cada leitura) porque a régua é "o que saiu do título", e isso só
se vê no momento da troca. Resolução (`resolver_sobra(event, nome)`): `len(vagas) ≤
contar_personagens(event.title)[nome]` → limpa `sobrando_desde` das vagas daquele nome e encerra os
avisos (FR-017). Roda em `assign_role` quando a vaga marcada perde o talento (e aí remove a vaga vazia
se ainda sobrar — FR-021) e em `delete_role`.

Pontos de chamada:
- `sync_events` (`routes.py:2474`, onde `old_title` e `title` coexistem), **antes** do `continue` dos
  eventos da plataforma (`:2533`) — é o que estende a regra a eles.
- No bloco de reconciliação dos eventos vindos do Google (`:2544-2590`), o ramo que apaga vaga de nome
  ausente e chama `send_removal_email` passa a apagar só vaga **sem talento**; vaga ocupada segue a
  regra acima (FR-023, confirmado no clarify). A criação de vaga nova e a migração de nome reservado
  para `extra` ficam como estão; ENSAIO segue limpando o elenco (`:2538`).
- `update_event_core` e `update_event_basics` (`event_ops.py`), depois de gravar o título do
  formulário e reconciliar o elenco.

**Alternativas**: comparação absoluta título × vagas — rejeitada (vaga com grafia diferente do título
viraria "a mais" na primeira troca de título).

## R6 — Título acompanha as vagas, ensaio acompanha o título (FR-027..032)

**Decisão**: em `titulo_ops.py`:
- `ajustar_titulo_apos_remocao(event, nome)` e `ajustar_titulo_apos_inclusao(event, nome)`: aplicam a
  regra de contagem do FR-027/028 (só mexe se título e vagas ficaram desiguais na direção certa) e
  devolvem o título novo ou `None`.
- `propagar_titulo_aos_ensaios(event)`: para cada ensaio com `parent_event_id == event.id`, não
  cancelado e com `start_at >= now_sp()` (naive, hora de parede — `docs/00` §6 item 1), grava
  `ENSAIO_TITLE_PREFIX + event.title` (`event_ops.py:1813`).
- Push ao Google **depois do commit** (regra do §6 item 25: Google e e-mail nunca com a trava na mão),
  por `service.update_event` com os campos atuais do evento; falha vira aviso (FR-031), nunca desfaz.

Chamadas: `delete_role`/`add_role` (via os endpoints de `agenda_write.py`) e as reescritas acima; a
propagação aos ensaios roda também quando o título muda por `update_event_core/basics` e pelo sync
(`titulo_mudou`, `routes.py:2484`). Na edição completa ("Editar") o título do formulário vence e não há
ajuste automático (FR-028).

**Por quê**: o sync copia o título do Google em toda rodada (`routes.py:2474`); se o sistema não
empurrar o título novo, a rodada seguinte desfaz a correção. Vale também para o ensaio: ele nasce
com `source` padrão (`google_calendar`), então o sync sobrescreve o título dele a cada rodada. Por isso
o push do ensaio passa a própria descrição e local (`update_ensaio`, `event_ops.py:1915-1946`, é o
molde; `update_event` com `description=""` apagaria a descrição). Na rodada em que o sync propaga o
título ao ensaio, o item do ensaio já buscado no mesmo lote ainda traz o título velho e pode
regravá-lo por uma rodada — transitório, a rodada seguinte lê o novo do Google.

**Alternativas**: remontar o título inteiro a partir das vagas — rejeitada na spec (perde a ordem e a
grafia da Comercial).

## R7 — Avisos e "Ciente" por pessoa

**Fatos** (mapeamento de 09/11): `Notification` (`app/models.py:685-725`) é uma linha **por pessoa**
(`user_id`), com `UNIQUE(user_id, dedupe_key)` e um único estado, `read_at` — que o sino grava ao
clicar no item (`NotificacoesPanel.tsx:51-55`, `NotificacoesPage.tsx:37-38`). Eventos usam
`entidade=("calendar_event", id)` e `link_path=f"/events/{id}"`. `emitir(...)`
(`notificacoes_ops.py:142`) não comita, aceita `destinatarios` explícito e engole duplicata pelo
`UNIQUE`. A retenção (`limpar_antigas`, `:616`) apaga lida há 30 dias e não lida há 180.

**Decisão**:
- Coluna nova `notifications.ciente_em DateTime NULL` (hora de SP, como `created_at`). É o estado da
  faixa; `read_at` continua sendo só o do sino (FR-015). "Ciente" grava `ciente_em` e, se vazio,
  `read_at`.
- Dois `kind` novos no catálogo: `evento.tipo_show` → `(CASTING, ENSAIO, SUPERADMIN)` e
  `evento.vaga_sobrando` → `(CASTING, SUPERADMIN)`, numa constante `KINDS_COM_CIENTE`.
- Produtores `notificar_troca_de_tipo_show(event, *, entrou, autor_id, autor_nome)` e
  `notificar_vaga_sobrando(event, nome, *, pedido, vagas, autor_id)`: destinatários =
  `resolver_destinatarios(papéis)` **menos o autor** (FR-033), passados como lista explícita.
  Chaves: `evento.tipo_show:{id}:{entrou|saiu}:{carimbo}` (cada troca é um fato) e
  `evento.vaga_sobrando:{id}:{nome}:{pedido}:{vagas}` (a mesma situação nunca duplica — FR-022).
  `severity="urgent"` quando o evento é em até 7 dias (mesma régua de
  `notificar_cancelamento_na_escala`, `:328`).
- Resolução da sobra (FR-017): `ciente_em = now_sp()` em todas as linhas `evento.vaga_sobrando` daquele
  evento e nome (prefixo da chave), de todo mundo.
- Endpoint novo `POST /api/notificacoes/<id>/ciente` em `app/api/notificacoes_write.py`, no molde do
  `/lida` (`:20`): só `@api_login_required`, escopo por `current_user.id`, 404 para id alheio ou de
  `kind` sem "Ciente".
- Faixa: `serialize_event_detail` (`app/api/agenda_read.py:909`) ganha a chave `avisos` — as linhas do
  **usuário que pediu** com `kind in KINDS_COM_CIENTE`, entidade = o evento, `ciente_em IS NULL` —
  antes do `return` antecipado do evento de ENSAIO (`:1015`). Como as escritas do detalhe devolvem o
  mesmo serializer (`setQueryData`), a faixa se atualiza sozinha depois de qualquer ação.
- Retenção: linha de `KINDS_COM_CIENTE` com `ciente_em IS NULL` conta como "não lida" (180 dias), para
  a faixa não sumir 30 dias depois de alguém abrir o sino.
- A lista de escalados da faixa (FR-012) é lida do `elenco` que o payload já traz, com o corte de cachê
  que ele já faz (`_serialize_role`, `:418`): o Ensaio vê nomes, quem tem `show_casting` vê o cachê. O
  texto do sino diz o fato; a lista viva fica na faixa, sem congelar valores no `body` (500 chars).

**Alternativas**: (a) "Ciente" = `read_at` — rejeitada: o sino apagaria a faixa (FR-015); (b) tabela
própria `event_avisos` + `event_aviso_cientes` — rejeitada: duplicaria endereçamento, deduplicação e
retenção que a 272 já resolve, e a caixa já é por pessoa.

## R7b — Tela

- Faixa nova `AvisosDoEvento.tsx` em `components/EventDetail/`, renderizada em `EventHeader.tsx` junto
  das outras (`SumiuDoGoogleBanner` `:493`, `QuadroDoPedido` `:499`), no molde do `QuadroDoPedido`
  (`mt-3 rounded-md border border-gold/40 bg-gold-soft p-3 text-sm`, `role="status"`). A mutação do
  "Ciente" fica em `EventHeader` (o comentário de `:219-221` avisa que o `onSuccess` não roda depois que
  a faixa desmonta) e invalida `["event", id]` e o prefixo `["notificacoes"]`.
- Card de casting (`CastingSection.tsx`): vaga com `sobrando` mostra a marca "O título pede N — tire
  alguém da escala."; Superadmin vê "autorizado por <nome> em dd/mm" na linha do teto (`:230-247`).
- `NotificacaoItem.tsx:7`: ícone por `kind` novo.
- Tipos em `lib/agenda.ts` (`RoleItem` `:143`, `EventoDetalhe` `:433`): campos novos **opcionais**
  (`docs/00` §6 item 21).
- `lib/casting.ts` (`useAddRole`, `useDeleteRole`, `:79,94`): a resposta passa a trazer `warnings`;
  mostrar em toast como o PATCH do evento já faz.

## R9 — Google na verificação

`service.update_event` não respeita nenhuma trava de `app/config.py` (dívida registrada em
`config.py:167-169`). O verify troca `app.calendar.service.build` e `load_credentials` por um
`GoogleFalso` que grava os `patch` (molde de `verify_303.py:449-450` e `verify_306.py:324-325`),
desliga e-mail (`MAIL_SUPPRESS_SEND`, `es._send`) e espiona `send_removal_email` religando o nome em
todos os módulos `app.*` carregados (`verify_306.py:359-381`). O sync é exercitado chamando
`sync_events([item])` com itens montados à mão, sem `created` (a guarda dos 5 minutos ignoraria).

## R8 — Migration

**Decisão**: uma migration à mão, aditiva, `down_revision = "d323b5a1c0e7"` (head da `main` em
09/11). Colunas: `event_roles.teto_autorizado`, `teto_autorizado_por` (FK `users.id`, `ON DELETE SET
NULL`), `teto_autorizado_em`, `sobrando_desde`; a coluna do "Ciente" (R7); e o `UPDATE` do R1.

**Atenção no merge**: 328, 329, 330, 332–335 e 338 também partem de `d323b5a1c0e7`. Quem entrar na
`main` depois troca o `down_revision` para o head do momento (é a colisão já registrada na memória da
329).
