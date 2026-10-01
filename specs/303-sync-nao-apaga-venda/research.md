# Research — 303: o sync não apaga evento com venda

**Data**: 2026-09-30 · **Spec**: [spec.md](./spec.md) · **Plano**: [plan.md](./plan.md)

Cada decisão abaixo passou por uma proposta e por uma revisão adversarial contra o código
(`pesquisa/frente-*.md`); onde a revisão emendou, a decisão registrada aqui **já é a emendada**. As
citações `arquivo:linha` valem para a `main` em `14cec75`.

## Como a pesquisa foi feita

Três rodadas de agentes só de leitura, em 29–30/09: (1) 17 agentes refutaram contra o código os
fatos da spec e acharam lacunas — 8 fatos corrigidos (`pesquisa/92-…`); (2) 5 agentes mapearam como
DRE, relatórios e listas tratam o cancelado (`pesquisa/90-…`, `91-…`) — assunto da segunda entrega;
(3) 19 agentes fizeram o desenho em nove frentes, com um revisor por frente e um integrador: 97
decisões, 35 aceitas, 60 emendadas, 2 derrubadas (`pesquisa/00-integracao.md`). Depois da
integração o dono dividiu o trabalho em três entregas; este arquivo cobre a primeira.

## Decisões

### R1 — Onde mora a marca

- **Decisão**: uma coluna nova em `calendar_events`, `google_missing_since` (`DateTime`, nullable,
  horário de São Paulo por `now_sp()`), com índice parcial. Nada mais: o que estava preso, quem
  desmarcou e por quê vão para `EventLog` e `AuditLog`. "Marcado" é sempre **marca preenchida e
  `cancelled_at` nulo**, num predicado único (`sumico_ops.filtro_marcados`).
- **Porquê**: reusar `deletion_requested_*` da 224 quebra — `solicitar_exclusao` sobrescreve sem
  checar (`cancel_ops.py:203-205`), `recusar_solicitacao` zera (`:230-232`), `cancelar_evento` limpa
  (`:292-294`) e a FK aponta para `users`. Coluna nullable não muda nenhum evento existente, e não
  tocar `cancelled_at` faz a FR-005 sair de graça (todo consumidor financeiro só filtra por ele).
- **Alternativas rejeitadas**: campos da 224 (acima); tabela de sumiços (o estado é um só por evento;
  o histórico já tem casa); segunda coluna com o resumo do que estava preso (texto derivado).

### R2 — A regra de "com dinheiro" do sync

- **Decisão**: `preso_ao_evento(event) -> PresoAoEvento` (dataclass imutável com os campos do
  contrato: venda, recebido, número de comprovantes, tem contrato, número de escalados, grupo e
  técnico automático; `.vazio`, `.descricao()`). Não vazio = `sale_value > 0`, **ou** existe algum
  `EventPayment`, **ou** algum `EventContract`, **ou** alguma `EventRole` com talento — exceto, em
  evento `SHOW`, a vaga `extra` "Técnico de Som" ocupada pelo técnico padrão —, **ou**
  `group_leader_id` preenchido, **ou** ter satélites. O mesmo objeto decide, escreve o histórico e
  alimenta o sino. `pode_excluir` da 224 não muda.
- **Emenda proposta e recusada (30/09)**: a revisão dos checklists propôs que comissão já paga e
  cachê lançado na vaga automática também segurassem o evento. O dono recusou as duas: comissão paga
  de evento que sumiu deve ser estornada, como hoje (`_delete_event` chama `aplicar_estorno_comissao`,
  `routes.py:322-327`; comissão `pago` vira estorno contra o vendedor, `cancel_ops.py:139-155`); e
  "se foi pago é porque foi realizado" — evento com cachê pago não some da agenda.
- **Porquê**: a regra difere da 224 em três pontos (grupo, técnico automático, comprovante por
  existência), então `pode_excluir` não serve (`cancel_ops.py:57-74` devolveria "não vazio" para
  todo SHOW). Comprovante por existência porque a exclusão apaga a linha mesmo com valor nulo
  (`routes.py:277`). A exceção do técnico exige `SHOW` porque o orçamento cria a mesma vaga fora de
  SHOW (`orcamento_evento_ops.py:227-245`) — ali, o talento 42 é escalação de gente.
- **Alternativas rejeitadas**: lista de textos (o sino e a tela precisam de números); três números
  soltos (o histórico descreve vários fatos; divergiriam); incluir reembolso, nota e presente 3D (o
  dono manteve a spec; só se conta quantos há).

### R3 — A consulta ao Google com três desfechos

- **Decisão**: função **nova** em `app/calendar/service.py`,
  `consultar_evento(calendar_id, google_event_id) -> ConsultaEvento(desfecho, item, motivo)`, que
  nunca levanta (exceção ao carregar a credencial, e `RefreshError` em qualquer ponto — inclusive no
  `.execute()`, onde a renovação do token acontece hoje: `save_token` não grava `expiry` e o ramo de
  renovação de `load_credentials` nunca dispara — → `sem_credencial`; qualquer outra que não seja
  erro HTTP → `rede`). Cada chamada carrega a credencial e monta o cliente: o parâmetro
  `service=` de um cliente compartilhado saiu do desenho — ninguém o construía, e com ele a falha
  de credencial teria duas regras. **Ausente** = HTTP 404 ou 410, ou item com `status == "cancelled"`.
  **Presente** = item devolvido, não cancelado, com início. **Inconclusivo** = todo o resto
  (credencial ausente, falha ao renovar, 401/403/429/5xx, tempo esgotado, rede, item sem início).
  `motivo` tem classe estável e a lista é fechada — ausente: `http_404`, `http_410`, `cancelled`;
  presente: vazio ou `serie_recorrente` (item com `recurrence`, não cancelado, com início);
  inconclusivo: `sem_credencial` (credencial ausente, falha ao renovar, HTTP 401), `rede` (sem
  resposta: erro de conexão ou tempo esgotado), `http_5xx`, `http_403`, `http_429`, `http_4xx` (os
  demais) e `sem_inicio`. `fetch_single_event` fica intocada.
- **Porquê**: `fetch_single_event` devolve `None` para tudo e não olha `status` (`service.py:181-191`)
  — não distingue apagado de Google fora do ar, e devolve como evento o item cancelado que o `get`
  retorna. A sonda de 30/09 (R17) confirmou: evento apagado volta com HTTP 200, `status:
  "cancelled"` e os dados completos — por isso a checagem de `status` vem antes da de início. O outro consumidor dela é o Meet da Loja Virtual (`virtuais_ops.py:1679`), que
  depende do contrato atual.
- **Invariante de segurança**: "ausente" só tem efeito destrutivo dentro de `limpar_mes`, que só roda
  depois de a **lista** do mesmo calendário ter respondido; na reconferência e no botão, é no-op.
- **Alternativas rejeitadas**: mudar o retorno de `fetch_single_event`; paginar a lista do mês para
  dispensar a consulta (a spec manda registrar como dívida).

### R4 — A limpeza: unidade de trabalho, ordem e disjuntor

- **Decisão**: `sumico_ops.limpar_mes(items, year, month) -> ResultadoLimpeza` (removidos, marcados,
  movidos, desmarcados, presentes fora da lista, inconclusivos, falhas), com `_decidir_candidato`
  por evento. `_cleanup_stale_events` em `routes.py` vira delegação de uma linha (mesmo nome, mesma
  entrada; o retorno muda de lista para `ResultadoLimpeza`, e os dois consumidores do retorno são
  ajustados). Por candidato (evento do mês, não cancelado, id fora da lista), nesta ordem: venda
  virtual → registra a divergência como hoje, sem consulta; já marcado → pula; consulta →
  inconclusivo: nada; presente: R5; ausente: vazio → apaga como hoje (com o motivo do Google na
  auditoria); com dinheiro → `marcar`. A **unidade de trabalho é o evento**: os ids são
  materializados antes, cada evento é relido com `db.session.get` (`None` = já saiu, não é falha),
  roda em `try/except` próprio e termina em commit; exceção → `rollback`, log, id em `falhas`, segue.
  **Disjuntor**: o primeiro inconclusivo de classe `rede`, `http_5xx` ou `sem_credencial` encerra
  as consultas da rodada; os restantes saem como inconclusivos. `http_403`, `http_429`, `http_4xx` e
  `sem_inicio` **não** abrem: o disjuntor existe por causa do tempo (até 60 s por tentativa) e do
  acesso perdido, e essas respostas chegam na hora — aquele evento fica inconclusivo e os outros
  seguem, para uma recusa não segurar a limpeza dos demais.
  **Rodada** = uma execução de `limpar_mes` (um mês) ou uma execução de `reconferir_marcados`. O
  disjuntor é estado local da chamada: não passa de um mês para o outro nem da reconferência para o
  laço de meses — a lista do mês seguinte é a nova sonda do Google (se ele continua fora, a lista
  falha e o mês é pulado, como hoje). Alternativa rejeitada: disjuntor da execução inteira, com um
  gerenciador de contexto compartilhado — mais maquinaria para cobrir só o caso em que a lista
  responde e a consulta não. Pior caso: uma consulta sem resposta por mês, até 60 s cada (ver
  plan.md §Metas de desempenho).
- **Porquê**: `sync_events`, `_mark_talents_worked` e `_mark_month_synced` comitam sozinhos
  (`routes.py:163, 2352, 2358, 2406, 2434`), então não há transação do mês. O laço atual percorre
  instâncias carregadas antes: com commit por evento, o ensaio-filho apagado por cascade chegaria à
  sua vez fora da sessão. O cliente do Google espera até 60 s por chamada
  (`googleapiclient/http.py:75`) e o proxy corta em 180 s (`frontend/server.js:619`).
- **Alternativas rejeitadas**: tudo ou nada por mês (um evento com consulta recusada travaria a
  limpeza para sempre); savepoint por evento com um commit no fim do mês (o `sync_events` do meio
  comitaria o pendente); manter o laço em `routes.py`.

### R5 — Mudança de data

- **Decisão**: quando a consulta devolve presente, comparar título, início, fim, local e descrição
  do item com o banco. **Mudou** → `sync_events([item])` (a mesma função, sem extrair nem copiar), e
  o id entra em `movidos`. **Não mudou** → não chama nada, soma em `presentes_fora_da_lista` e grava
  um `AuditLog` só na primeira vez (por evento e dia), com o motivo quando for série recorrente.
- **Como comparar**: pelos valores que `sync_events` gravaria, não pelo item cru — título depois de
  `_strip_reserved_title_segments` (e "Sem título" quando vazio), como em `routes.py:2229-2233`;
  início e fim por `parse_event_datetime` (horário de parede de São Paulo, sem fuso; dia inteiro =
  meia-noite, com o fim exclusivo do Google); local e descrição com nulo e vazio iguais e sem
  espaços nas pontas. É uma função só, usada aqui e no ramo "id velho presente" da R13. Invariante:
  logo depois de um `sync_events([item])`, a comparação do mesmo item dá "não mudou". Sem isso, um
  evento fora da lista com "+ Coordenador" no título do Google daria "mudou" em todo ciclo.
- **Porquê**: só "pular" não basta — o horizonte do ciclo sai da data velha do banco e começa no mês
  corrente (`sync.py:51-64`), então o mês de destino pode nunca ser listado. `sync_events` acha o
  evento pelo id (`routes.py:2247`), grava a data (`:2291-2295`) e avisa o elenco aceito
  (`:2340-2342`). Sem a comparação, um evento que nunca vem na lista (série recorrente-mãe; página
  cortada) ficaria em laço de consulta + sync + `UPDATE` global a cada 10 minutos.
- **Alternativas rejeitadas**: função própria que só troca a data (duplica a regra, não avisa o
  elenco); inverter a ordem do ciclo (não cobre mês passado).

### R6 — Marcar e avisar, juntos

- **Decisão**: `marcar(event, preso, *, contexto) -> datetime | None` faz `UPDATE` condicional
  (`WHERE id = :id AND google_missing_since IS NULL AND cancelled_at IS NULL`); quem não pega a linha
  devolve `None` e não registra nem avisa. Quem pega: `refresh` do objeto, `EventLog` ("Sumiu do
  Google Agenda — mantido no sistema. Preso: …. Aviso enviado a N pessoa(s)."), `_log_sync
  ("sumiu_do_google")` e o produtor do sino, com o **carimbo que o próprio `UPDATE` gravou** — tudo
  na transação do evento (regime A do módulo de notificações).
- **Porquê**: a transição sem marca → marcado não se repete; aviso perdido não teria retentativa. O
  `UPDATE` condicional resolve a corrida entre o ciclo automático e o "Limpar eventos fantasma", que
  não passam pelo mesmo claim (`sync.py:122-150`).
- **Relógio**: a coluna da marca é São Paulo sem fuso (como `cancelled_at`); o `EventLog` **não**
  recebe `created_at` — vale o default UTC, que a tela converte (`agenda_read.py:210-214`). O
  cancelamento da 224 grava São Paulo no `EventLog` e sai 3 h adiantado — dívida registrada.
- **Primeira rodada sem sino**: não é necessária — a contagem de 30/09 achou zero eventos passados
  fora do Google (R17). O parâmetro `avisar` não entra no desenho.

### R7 — O aviso do sino

- **Decisão**: `KIND_EVENTO_SUMIU_GOOGLE = "evento.sumiu_google"`, destinatários `(COMERCIAL,
  SUPERADMIN)`, severidade `urgent`, entidade `("calendar_event", id)`, link `/events/<id>`.
  `dedupe_key = "evento.sumiu_google:<id>:<AAAAMMDDHHMMSSffffff do carimbo>"`. Título "Sumiu do
  Google Agenda — <título>"; corpo "<dd/mm/aaaa> · venda R$ X · recebido R$ Y · N pessoa(s)
  escalada(s)", com "parte de grupo comercial" no lugar de "sem venda" quando for de grupo, mais
  "· contrato anexado" quando há contrato, e "recebido R$ 0,00 (N comprovante(s) sem valor)" quando
  há comprovante e a soma é zero — para o evento mantido só por contrato ou comprovante não parecer
  alarme falso. Em toda saída da marca: `marcar_lidas_por_entidade`; quando o evento é apagado:
  `apagar_por_entidade`.
- **Na tela**: a linha do sino (painel e `/notificacoes`) corta título e corpo em uma linha cada
  (`NotificacaoItem.tsx:53, 58`), e com o prefixo fixo sobrariam ~10 caracteres para o nome do
  evento. O aviso `urgent` passa a quebrar — título em até duas linhas, corpo em até três
  (`line-clamp` no lugar do `truncate`), com o texto inteiro no `title`. Os avisos `info` continuam
  como hoje.
- **Porquê**: é a receita do módulo para produtor novo, sem tabela, endpoint ou tela
  (`notificacoes_ops.py:13-16`). O carimbo na chave dá "um aviso por sumiço" e "aviso novo se sumir
  de novo". O prefixo fixo no título sobrevive ao corte de 200 caracteres.
- **Alternativas rejeitadas**: chave por dia (não reavisa no mesmo dia); chave sem carimbo (o segundo
  sumiço nunca avisaria).

### R8 — A faixa: endpoint

- **Decisão**: `GET /api/events/sumidos-google` em `app/api/agenda.py`; núcleo `faixa_sumidos(limite)`
  em `sumico_ops`. Corpo `{pode_ver, total, limit, items: [{id, title, start_at}]}`; `total` exato;
  itens ordenados por urgência (futuros por data; depois passados, do mais recente ao mais antigo;
  sem data por último), com teto de 100. Gate `_ve_faixa_sumidos()` = SUPERADMIN ou COMERCIAL **pelo
  papel efetivo**; quem não passa recebe 200 com `pode_ver: false` e lista vazia, sem tocar o banco.
- **Porquê**: o guard do revendedor devolve 403 fora de `/api/auth`, `/api/agenda`, `/api/events` e
  `/api/educamanto` (`app/__init__.py:55, 738-751`), e a spec pede vazio sem erro. `pode_ver` no
  corpo é o que deixa o front desligar o poll sem decidir RBAC. Papel efetivo porque a faixa é visão
  por papel, como a Home; o sino é da pessoa e ignora o "Ver como".
- **Alternativas rejeitadas**: pendurar em `/api/notificacoes/nao-lidas` (contrato de `COUNT` sem
  join) ou em `/api/auth/me` (sem poll); 403 para os outros papéis; teto de 20 (a FR-009 pede acesso
  a cada um).

### R9 — A faixa: componente

- **Decisão**: `FaixaSumidosGoogle` em `apps/internal/src/components/`, montado no `AppShell` antes do
  `<Outlet />`. Dois níveis: um wrapper `sticky top-14 lg:top-0 z-[25]` sem overflow, sempre
  montado; dentro, `AnimatePresence` com a barra (`overflow-hidden`, altura 0 ↔ 40 px, linha interna
  `h-10`, `bg-red text-on-color`) e, como **irmão** da barra, o painel da lista ancorado no wrapper
  (`max-h-[60vh] overflow-y-auto`). Um evento: link direto. Vários: botão que abre a lista. Sem
  dispensar. `role="alert"` só na frase de contagem. Hook `useSumidosGoogle()` (chave com o id do
  usuário; poll de 60 s enquanto `pode_ver` não for falso; nada em segundo plano) montado só no
  shell; `useFaixaSumidosVisivel()` é observer **passivo** (`enabled: false`, `select`) para a régua
  de abas do evento (`top-24 lg:top-10`) e as âncoras da Home (`scroll-mt-28 lg:scroll-mt-14`).
- **Fronteira**: "todas as telas do sistema interno" = toda rota autenticada da SPA interna, isto é,
  tudo o que o `AppShell` envolve. Ficam de fora: a tela de login (sem sessão não há papel), o
  esqueleto de carregamento do shell e as duas folhas de impressão de figurino, que são Jinja e
  abrem em aba própria (`/figurinos/<id>/print` e `/figurinos/print-event/<id>`). As SPAs pública e
  do portal não são sistema interno. Rota interna nova criada fora do shell tem de montar a faixa.
- **Conteúdo**: a frase de contagem usa sempre `total` (o `role="alert"` fica num `span` dentro do
  link ou do botão). **Um evento**: a barra é um link para `/events/<id>`; mostra a frase e, a
  partir de `sm`, ` — <título> · dd/mm/aaaa` (título numa linha, cortado com reticências; a data
  nunca é cortada; sem início: `sem data`). **Vários**: a frase é o botão que abre a lista. Cada
  linha da lista é um link para `/events/<id>` com o título (uma linha, reticências, título inteiro
  no `title`) e a data em `dd/mm/aaaa` — o formato do aviso do sino —, ou `sem data`; a ordem é a
  que o servidor mandou. Se `total` for maior que o número de itens recebidos, a lista termina com
  a linha sem link `e mais N`.
- **Tela estreita**: abaixo de `sm` a barra tem uma linha só — ícone, a frase de contagem inteira
  (`whitespace-nowrap`: não quebra nem é cortada) e, com vários eventos, o indicador de abrir;
  título de evento não vai na barra. A lista abre na largura inteira do conteúdo, sem rolagem
  horizontal. A referência do app interno é 375 px (o requisito de 320 px é só do portal).
- **Porquê**: altura fixa é o que permite compensar o offset por classe, sem `style` inline. Animar
  altura exige `overflow-hidden`, que cortaria o painel se ele ficasse dentro da barra. Cada observer
  com `refetchInterval` tem o próprio timer no TanStack 5 — dois ativos dariam dois GETs por minuto.
  `z-[25]` fica entre a régua de abas (`z-20`) e o painel do sino (`z-30`).
- **Alternativas rejeitadas**: faixa em fluxo normal (some ao rolar); slot no `AppLayout` do
  `@manto/ui` (pacote compartilhado para um consumidor); variável CSS escrita por efeito.

### R10 — Situação única e o selo

- **Decisão**: `CalendarEvent.situacao` (`cancelado` > `sumiu_do_google` > `exclusao_solicitada` >
  `None`) e `situacao_desde`, no modelo; constantes em `app/constants.py`; um
  `export type SituacaoEvento` em `lib/agenda.ts`. `serialize_event_summary` (mês, dia e busca) ganha
  `situacao` e `situacao_desde`; o detalhe ganha `situacao` e `sumiu_do_google: {desde} | null`.
  Componente `SeloSituacao.tsx` sobre o `Badge` (o nome difere do tipo `SituacaoEvento` de
  propósito; nesta entrega: selo dourado "Sumiu do Google", com o ícone `CalendarX` — o mesmo do
  aviso do sino — e texto; o do cancelado é da terceira entrega).
- **Onde o selo aparece**: **Lista e busca** (a busca reusa `AgendaListItem` —
  `AgendaSearchResults.tsx:6, 26`) — selo completo, ícone + `Sumiu do Google`, ao lado do selo de
  categoria. **Mês** — o chip mantém a cor da categoria e ganha só o ícone do selo antes do horário
  (o texto não cabe no chip de ~80 px); o `title` do chip vira `<título> — Sumiu do Google Agenda,
  percebido em dd/mm/aaaa` e o ícone leva `aria-label` "Sumiu do Google Agenda". Marcado escondido
  no `+N` só mostra o ícone ao expandir o dia — aceito, a faixa lista todos. **Dia** — selo
  completo no bloco detalhado e na lista "Sem horário"; no bloco curto, só o ícone antes do título,
  com o texto no `title` do bloco. Em toque não há tooltip: a data em que o sistema percebeu é lida
  no banner do evento, a um toque do selo (o `InfoTip` do `@manto/ui` não serve aqui — é um botão, e
  o chip e o bloco da agenda já são links).
- **Porquê**: as três leituras da agenda passam por um serializador só (`agenda_read.py:70-89`);
  precedência no servidor evita que cada tela recombine três campos. A marca nunca aparece em evento
  cancelado, inclusive na visão Dia, que hoje mostra cancelado sem sinal.

### R11 — Edição e "Sincronizar" enquanto marcado

- **Decisão**: **edição** — uma condição em `_sincronizar_e_trocar_tipo` (`event_ops.py:637-643`): o
  push ao Google só acontece se o evento não estiver marcado; salva com 200, sem aviso e sem
  desfazer troca de tipo. **Sincronizar** — `_sync_single_event_flow` passa a usar `consultar_evento`
  para qualquer evento: ausente → status novo `ausente_no_google` (409, nada muda); inconclusivo →
  502 como hoje; presente → se marcado, `desmarcar` antes, depois `sync_events([item])`. O servidor
  manda `google_html_link: null` quando o evento está marcado ou cancelado; a tela mostra
  "Sincronizar" por `google_html_link || sumiu_do_google`, e "Editar no Google Agenda" só com o link.
- **Porquê**: o único caminho que escreve o cabeçalho no Google é esse (`event_ops.py:550`); hoje, num
  evento sem par no Google, cada salvamento falharia com aviso e a troca de tipo seria desfeita com
  409. O botão hoje entrega a `sync_events` o item apagado, para **qualquer** evento apagado no
  Google ainda não percebido: com a resposta completa (o que a sonda de 30/09 viu), "sincroniza" o
  evento como se estivesse vivo, sem avisar; com a resposta mínima, o título vira "Sem título", as
  datas ficam nulas e a escala é reconciliada com e-mail de remoção (`routes.py:2229-2236,
  2361-2392`). O endpoint não tem gate de papel
  (`agenda_write.py:624`); passa a poder retirar a marca quando o evento voltou — o mesmo efeito que
  o ciclo teria em até 10 minutos.

### R12 — Reconferir os marcados

- **Decisão**: `sumico_ops.reconferir_marcados()` roda no início de `run_calendar_sync`, antes do laço
  de meses, com disjuntor próprio (o mesmo critério, estado local). Presente → `desmarcar` +
  `sync_events([item])` (um commit só);
  ausente e inconclusivo → nada. A marca sai por quatro caminhos, todos por `desmarcar`: reconferência
  por id, id de volta na lista do mês (sem faixa de mês no filtro), "Sincronizar" com presença
  confirmada e "Devolver ao Google". Nunca dentro de `sync_events`.
- **Falha na reconferência não interrompe o ciclo**: disjuntor aberto na reconferência encerra só
  as consultas dela (os marcados restantes saem como inconclusivos: nenhuma marca retirada); o laço
  de meses segue — cada mês busca a lista, roda `sync_events`, limpa (com disjuntor próprio, R4) e é
  carimbado como hoje. Exceção dentro de `reconferir_marcados` faz `rollback`, é registrada e também
  não impede o laço.
- **Quando o marcado reaparece, vale o Google**: `sync_events([item])` aplica título, data, local e
  descrição do Google por cima do que foi editado no sistema enquanto marcado (`routes.py:2291-2295`),
  avisa o elenco aceito (`:2340-2342`) e reconcilia a escala pelo título do Google, com e-mail de
  remoção (`:2361-2392`). É o padrão da verificação de 29/09 (`pesquisa/92-…`, item 12: "vale o
  Google, como hoje"); só a devolução faz valer o sistema (R13). Alternativa rejeitada: manter
  marcado para o Superadmin decidir (deixaria a faixa acesa por um evento que está no Google).
- **Porquê**: um marcado de setembro deixa de ser listado depois de 01/10 (`sync.py:52`). Dentro de
  `sync_events` a desmarcação seria disparada pelo botão com item apagado.

### R13 — Devolver ao Google

- **Decisão**: `POST /api/events/<id>/devolver-ao-google` em `agenda_write.py`, gate `_can_delete()`
  depois do 404, corpo vazio; resposta = detalhe do evento + `devolucao_google: {resultado}`. Núcleo
  `sumico_ops.devolver_ao_google(event_id, *, actor)`, fatiado em `_validar`,
  `_exigir_ambiente_liberado`, `_bloquear_e_revalidar`, `_recriar_no_google` e
  `_registrar_devolucao_google`. Ordem: valida sem bloqueio (existe, não cancelado, marcado, não
  virtual, datas válidas) → trava de ambiente → consulta o id velho → `SELECT … FOR UPDATE` com
  `populate_existing` e revalida **tudo** → monta `EventLog` e dá `flush` (`actor_role[:60]`) →
  `insert_event` → `_log_sync("google_returned")` com o id velho → troca id e link → `desmarcar` →
  commit. Erros com `codigo`: 409 `cancelado`, `nao_marcado`, `venda_virtual`, `sem_data`,
  `google_travado`; 502 `google_inconclusivo`, `google_desconectado`, `google_recusou`.
- **Id velho presente** (o evento voltou): não insere. Compara os cinco campos; iguais → só desmarca;
  diferentes → `_push_cabecalho_ao_google(event)` no id velho e só então desmarca (falha do push →
  502, marca continua). Resultado `reapareceu`.
- **Origem**: `source = "platform"` **só quando** existe vaga de personagem fora do título (calculado
  com os helpers do próprio sync); o `EventLog` diz que o elenco passa a ser mantido pelo sistema.
  Vale nos **dois ramos** (recriado e "já tinha voltado"): nos dois o Google fica com o título do
  sistema, e sem a troca o sync seguinte apagaria a vaga fora do título, com e-mail de remoção — o
  que a FR-044 proíbe.
- **Limite do ramo "já tinha voltado"**: `_push_cabecalho_ao_google` usa `update_event`, que sempre
  manda data com hora (evento de dia inteiro vira bloco com hora) e só manda o local quando não é
  vazio (`service.py:266-288`). É o comportamento de toda edição hoje — dívida no `docs/05`; o
  cenário 10c não usa dia inteiro nem local apagado.
- **Evento inexistente**: o 404 é da view, como nos vizinhos; se o evento sumir entre a view e o
  bloqueio, o núcleo levanta o código interno `inexistente`, que a view traduz no mesmo 404.
- **Dia inteiro**: `insert_event(..., *, all_day: bool = False)`; o núcleo passa `True` quando início
  e fim são meia-noite e o fim é maior que o início.
- **Falha**: exceção do insert → `rollback`, `AuditLog` `google_return_failed` com o tipo do erro,
  502 com a mensagem fixa do contrato (coluna "Mensagem" da tabela de erros: uma para a criação, que
  manda conferir na Agenda se o evento apareceu e, se apareceu, apagá-lo lá e devolver de novo;
  outra para a atualização do ramo "já tinha voltado"). Sem delete compensatório: sem cenário, seria
  código não verificado; fica o log do órfão, como na criação de evento.
- **Corrida com o ciclo**: entre o `insert_event` e o commit, o evento novo já existe no Google e
  ainda não tem linha com o id novo. Quem cobre a janela é a guarda da 254 em `sync_events`
  (`routes.py:2190-2208`: item com menos de 5 minutos e sem linha local fica para o ciclo seguinte)
  — ela não muda, e nada lento entra entre o insert e o commit (só gravações locais já preparadas).
  Se o ciclo já tinha buscado a lista do mês antes da devolução, a limpeza não acha o id novo na
  lista, consulta o evento (FR-002), encontra-o presente e sem mudança: nada é apagado nem marcado.
- **Porquê**: sem o bloqueio, dois cliques criam dois eventos no Google; sem consultar antes, um
  evento restaurado da lixeira ganharia um gêmeo. O `flush` antes do Google faz a falha previsível
  de banco acontecer antes da escrita externa. `_push_cabecalho` cumpre o "dados atuais" da FR-012
  sem disparar a reconciliação pelo título antigo.
- **Alternativas rejeitadas**: módulo novo em `app/api/` (registro a esquecer); responder `{ok}` e
  invalidar (a tela ficaria um ciclo com a marca); "desapagar" o id velho por `patch`; troca de
  origem incondicional (mudaria para sempre um evento nascido no Google).

### R14 — A trava de escrita (Princípio XIV)

- **Decisão**: trava **nova**, no molde da de convites: `_suppress_calendar_event_writes()` e
  `Config.CALENDAR_SUPPRESS_EVENT_WRITES` — travado quando o banco é local; `…=true` trava em
  qualquer ambiente; `CALENDAR_ALLOW_LOCAL_EVENT_WRITES=true` é o escape. Lida de
  `current_app.config` a cada chamada, só pelo núcleo da devolução, antes de qualquer chamada ao
  Google; ausência da chave = travado. Ambiente travado responde 409 `google_travado`.
- **Porquê**: `CALENDAR_SUPPRESS_INVITES` fala de convite a pessoa e a docstring exclui os eventos de
  show (`config.py:133-135`); o escape dela liberaria duas coisas de risco diferente. Checar dentro
  de `service.insert_event` travaria a criação local de evento — a quitação da dívida, não o mínimo.
- **Aviso na documentação**: o escape local cria evento de verdade na agenda da empresa, que a
  produção importa 5 minutos depois.

### R15 — A tela do evento marcado

- **Decisão**: `SumiuDoGoogleBanner.tsx`, renderizado quando `event.sumiu_do_google` existe. Para
  todos: a marca, "percebido em dd/mm/aaaa", que o evento segue valendo e que a edição só vai ao
  Google na devolução. Figurino, Casting, Financeiro, Ensaio e o revendedor EducaManto veem só essa
  parte comum. A frase do Comercial aparece por `flags.can_request_delete && !flags.can_delete` — o
  mesmo par de flags que o menu já usa para "Solicitar exclusão"; o front não decide por papel. Para
  quem tem `flags.can_delete`: o quadro "o que está em jogo", montado do **detalhe já carregado**; o
  botão "Devolver ao Google Agenda"; a linha "o cancelamento com devolução do dinheiro chega na
  próxima entrega"; e o `AccordionRow` "O evento já foi recriado à mão no Google?" com os três
  passos (texto fixo no contrato). O diálogo (`ConfirmDialog`) mostra "Será recriado como: <título>
  — <data e horário>" e avisa se a data já passou; em erro de estado (`nao_marcado`, `cancelado`)
  invalida o evento e a faixa e fecha.
- **Linhas do quadro**, nesta ordem: **Venda** = `kpi.sale_value`; **Pago pela cliente** =
  `pagamentos.received_total` (comprovantes deste evento — o mesmo número do aviso do sino; no
  principal de um grupo o rótulo é `Pago pela cliente (neste evento)`); **Comissão** =
  `kpi.commission`, com o rótulo `Comissão (estimativa)` quando `kpi.commission_source` é
  `estimativa` — a mesma regra do cartão da aba Comercial; **BV** = `kpi.bv_total`; **Escalados** =
  vagas de `elenco` com talento (em SHOW esse número inclui o técnico de som automático, que o aviso
  do sino não conta: a diferença de 1 entre o quadro e o sino é esperada). Só quando existem:
  **Contrato** = `anexado` (de `contratos`), **Comprovantes** = quantidade (de `pagamentos.items`)
  e, em evento de grupo, **Grupo comercial** = `principal` ou `satélite` (de `event.group.role`).
- **Satélite**: as linhas de dinheiro dão lugar a `Venda do grupo — os valores estão no evento
  principal`, com link para o principal (`event.group.leader`), e a linha de escalados é a do
  próprio satélite. O botão "Devolver ao Google Agenda" continua no satélite: a devolução é por
  evento, e o principal pode nem estar marcado.
- **Tela estreita** (375 px): o banner ocupa a largura do conteúdo, sem rolagem horizontal; o quadro
  é uma coluna de linhas rótulo → valor (o `DataRow` que a tela já usa, `EventDetail/parts.tsx`), o
  botão ocupa a largura toda, e o "recriado à mão" nasce recolhido.
- **Depois de devolver**: o diálogo fecha, o banner some e a linha de aviso do cabeçalho
  (`aria-live`, a que a tela já usa — `EventHeader.tsx:217-220`; não há toast) diz o que aconteceu,
  pelo `resultado` (textos no contrato).
- **Porquê**: `resumo_impacto.comissoes` só lista linha de comissão já criada, e no satélite diria
  "venda 0"; o detalhe já traz tudo, com a comissão estimada. Sem mostrar a data, o caso do 1244
  (19/09 no sistema, recriado à mão em 07/11) seria devolvido na data velha.

### R16 — Cancelar e excluir evento marcado (o intervalo)

- **Decisão**: nesta entrega, `cancelar_evento` e `_delete_event_flow` (`routes.py:4211-4234`)
  **recusam** evento marcado, antes de qualquer escrita, para qualquer papel. A recusa mora no
  núcleo, não na view: `_delete_event_flow` é a fonte única dos dois adaptadores — `DELETE
  /api/events/<id>` e o wrapper Jinja vivo `POST /events/<id>/delete` (`routes.py:4318-4341`), que
  não passa por `pode_excluir` e só responde chamando o backend direto. O núcleo sinaliza com
  exceção própria e cada adaptador traduz: a API em 409 `sumiu_do_google`, o Jinja em mensagem de
  erro e volta ao evento. Na tela, o item "Excluir ou cancelar" do menu fica desabilitado com o
  motivo (texto fixo do contrato, no `title` do item; em toque o `title` não abre, e a mesma
  informação já está na linha do banner do Superadmin) enquanto `event.sumiu_do_google` existir — o
  diálogo de um bundle antigo mostra a mensagem do servidor. `resumo_impacto` não muda. A segunda
  entrega troca a recusa pelo "Cancelar e devolver o dinheiro".
- **Evento marcado com exclusão solicitada** (o pedido pode ser anterior ao sumiço ou feito
  depois): os dois banners aparecem, o do sumiço primeiro. No banner "Exclusão solicitada", o botão
  "Analisar e decidir" (`EventHeader.tsx:388-392`) fica desabilitado com o mesmo motivo do item do
  menu — ele abre o mesmo diálogo da 224, que o servidor recusa (FR-045); "Recusar solicitação"
  continua. O "Solicitar exclusão" do Comercial não muda: segue disponível em evento marcado, e o
  motivo que ele escreve fica registrado para o Superadmin até a devolução ou até a segunda entrega.
- **Porquê**: decisão do dono em 30/09 (nenhum cancelamento sai com a regra velha). Além disso, o
  diálogo da 224 decide entre excluir e cancelar por `pode_excluir`, que não olha grupo — um
  satélite marcado sem mais nada receberia "será excluído de vez" e o registro que o sync acabou de
  preservar seria apagado (`routes.py:4224-4234` só recusa o líder).

### R17 — Contagem pré-deploy

- **Decisão**: `contagem_pre_deploy.py`, só leitura, contra o `manto_local` recém-restaurado do dump
  da madrugada, lendo o Google real só com `events.list` (paginado) e `events.get`. Não chama
  `create_app()`; banco com `default_transaction_read_only=on`; credencial montada do token e
  renovada só em memória. Dois passos: **sonda** (o que o Google responde de verdade para os ids
  apagados desde 01/08, tirados de `audit_logs`) e **contagem** (por mês passado: ausência
  confirmada, mudou de data, inconclusivo; os confirmados em com dinheiro ou vazios). Saída ao dono:
  eventos passados com dinheiro ausentes (quantidade, R$ e lista); eventos que mudariam de data com
  elenco de convite aceito (quantos e-mails sairiam); inconclusivos; pais vazios com ensaio-filho;
  SHOW sem venda com cachê na vaga automática; eventos que só têm reembolso, nota ou presente 3D.
- **Porquê**: a contagem decide se o primeiro "Limpar eventos fantasma" roda com a regra normal ou
  espera a decisão do dono (spec §Casos de borda, evento no passado) — não existe "primeira rodada sem
  sino". O que a contagem prevê é o
  primeiro "Limpar eventos fantasma" (o ciclo automático só limpa do mês corrente em diante). A sonda
  calibra os três modos de "apagado" do dublê. É local porque o script lê o Google, e o precedente
  (`dados_pre_deploy_299.py`) só lia o banco.
- **Resultado — rodada em 30/09/2026**, contra o `manto_local` restaurado do dump
  `manto_2026-09-30_0200.dump` (último `audit_log` às 04:50 UTC), 8 chamadas de lista e 5 de consulta
  ao Google, nenhuma escrita:
  - **Contagem**: 8 meses (2026-01 a 2026-08), 380 eventos no banco, **zero fora da lista do
    Google** — nenhum evento passado seria marcado, movido ou apagado no primeiro "Limpar eventos
    fantasma". A regra "primeira rodada sem sino" **não é necessária**; o parâmetro `avisar` não
    entra no núcleo. Repetir no dia do deploy.
  - **Sonda** dos cinco apagados por sumiço desde 01/08: quatro voltam do `events.get` com **HTTP
    200, `status: "cancelled"` e o item completo** (título, início, fim, local); nenhum 404 nem 410.
    Logo a regra "ausente" tem de olhar `status` **antes** de olhar se há início, e o dublê do
    verify precisa do modo "cancelado com dados completos", além de 404, 410 e do cancelado mínimo.
  - **O quinto não está apagado**: o evento 1275 (`(CORP) FLORES - JARDIM ENCANTADO…`) está
    **presente** no Google em 22/10. Foi movido de setembro para outubro em 10/09 às 21h28 (UTC), a
    limpeza de setembro o apagou às 21h34 e o sync de outubro o importou como o evento 1287, sem
    valor de venda, sem vendedor e sem escala. O 1275 **tinha venda**: a comissão 190 (R$ 63,45,
    venda de 04/09) foi cancelada pela exclusão. É a prova em produção do caminho de perda por
    mudança de mês (R5) — e uma venda a relançar à mão no 1287.
  - Dos outros, dois (1206 e 1265) foram apagados 8 a 10 minutos depois de criados pela plataforma.
  - Observação fora de escopo: janeiro de 2026 tem 1 evento no banco e 34 no Google — o "Limpar
    eventos fantasma", que também importa, traria os outros 33 como eventos novos (comportamento de
    hoje, não tocado).

### R18 — O verify

- **Decisão**: um `verify_303.py`, com: (a) **dublê único** `GoogleFalso` instalado em
  `service.build` e `service.load_credentials` — cobre toda função do service, inclusive a nova —,
  **fail-closed** (mês não liberado e id desconhecido respondem erro 503), com os quatro modos de
  "apagado" (cancelado com dados completos — o que o Google real devolve —, cancelado mínimo, 404 e
  410), erros dos tipos reais,
  credencial por chamada, `timeMin`/`timeMax`/`pageToken`, liberação de mês por bloco e `reset()`;
  (b) **disjuntor de rede** (`socket.connect` e `connect_ex` recusam host que não seja loopback) e
  contador de fugas, afirmados vazios no último cenário; (c) eventos de teste em **meses isolados**
  (2031 em diante e um mês passado calculado), nascidos pelo caminho real (`sync_events`), com talento
  descartável posto em vaga que o sistema criou; (d) coluna nova lida por **SQL cru**, rotas num
  dicionário — o verify não importa, no topo, nada que a 303 cria (a única exceção é o import
  tardio de `sumico_ops.faixa_sumidos` dentro do cenário 17, que vira BLOQUEADO em `ImportError`: o
  endpoint não tem parâmetro de limite); (e) três estados por cenário (OK, FALHA, BLOQUEADO) e
  controle positivo em todo "deve falhar"; (f) `_esperar_threads()` antes de afirmar sobre e-mail;
  (g) guarda de ambiente (exit 2) se `calendar_auto_sync_at` for recente (backend local ligado);
  (h) limpeza por `(entity_type, entity_id)`, nunca por id ou kind soltos; (i) dois argumentos para
  a conferência de tela: `--semear-tela` semeia em mês isolado, com o dublê, os eventos marcados e
  os descartáveis de que o quickstart §4 precisa, imprime os ids e sai **sem** limpar;
  `--limpar-tela` apaga tudo. Os eventos semeados têm id falso no Google: com o backend local ligado
  (sem a thread do sync), o "Sincronizar" responde "não está mais no Google" e a devolução responde
  a mensagem da trava.
- **Blocos e fases**: o 13d (falha na reconferência) fica no bloco B2, com a História 5; o 17
  resolve a marca por reaparecimento, não por devolução, para o bloco B3 fechar na fase 5.
- **Porquê**: `routes.py` importa cinco funções do service no topo (`:19-29`); trocar função por
  função deixa binding esquecido — foi assim que o `verify_205` chama a limpeza com lista vazia sobre
  um mês real e **apaga** os eventos daquele mês do espelho. Um dublê que devolvesse lista vazia para
  mês real faria a limpeza marcar os eventos reais do espelho.
- **`verify_205`**: em `:810`, trocar a lista vazia por todos os outros eventos vivos do mês (molde
  de `scripts/db/verify_cancelamento_evento.py:257-269`); **acrescentar** — não existe hoje, o
  verify só troca `insert_event` — `gcal_service.load_credentials = lambda: None` (cinto: nenhuma
  consulta chega ao Google real) e um espião em `gcal_service.consultar_evento` que guarda os ids
  consultados, os dois restaurados no `finally`. O V7.2 passa a exigir três coisas: os eventos
  virtuais sobrevivem; nenhum `google_event_id` virtual está entre os ids consultados (é isso que
  prova a guarda — com a credencial nula, um virtual consultado por engano também sobreviveria); e
  a contagem de eventos não virtuais do mês é igual antes e depois.
- **Falha por evento e erro de banco** (cenários 13b e 13c): o dublê do sino falha uma vez dentro
  de `marcar` (o evento entra em `falhas`, os demais seguem, a rodada seguinte marca e avisa); e um
  comando inválido injetado no meio de `sync_events` de um mês deixa a transação abortada — o
  `rollback` do `except` do mês é o que deixa o mês seguinte sincronizar.

### R19 — Portal

- **Decisão**: `_role_summary` ganha `em_confirmacao` (marcado e não cancelado) — vai o código, nunca
  o motivo; o artista não precisa saber de "Google". Componente `AvisoEmConfirmacao` (caixa
  `bg-gold-soft`, ícone, 14 px, quebra linha, sem botão, `role="note"`), no cartão da Agenda, de
  Convites e do Histórico. O "Ciente" não é reaproveitado (ele zera o aviso). Avaliação:
  `_event_ids_in_window` filtra cancelado e `_require_open_event` recusa com 400 e o motivo.
- **Posição**: primeira caixa depois do cabeçalho do cartão (título, data, local e função), acima de
  todo o resto — na Agenda, acima da caixa "Este evento teve uma alteração"; em Convites, acima do
  cachê e, portanto, antes de "Aceitar" e "Recusar"; no Histórico, abaixo da linha de título e cachê
  e acima da linha de deslocamento e de "Avaliar este evento".
- **Porquê**: `_role_summary` é a fonte única das três listas (`portal_ops.py:268-328`), sempre sobre
  consultas filtradas pelo talento da sessão. Hoje o crachá "Avaliar" acende para um evento
  cancelado que não aparece em lugar nenhum.

## O que fica registrado como dívida (`docs/05`)

Escritas antigas no Google sem trava; lista do mês sem paginação; série recorrente; id velho
restaurado da lixeira depois da devolução; `update_ensaio` e `edit_ensaio` só capturam
`RuntimeError`; agendar ensaio e presente 3D em evento cancelado; Fila de Impressão 3D sem filtro de
cancelado; lembrete diário de convite para evento marcado; `EventLog` do cancelamento 3 h adiantado;
o efeito antigo do `verify_205` no espelho; a sexta cópia do fechar-em-Esc-e-clique-fora; limpeza
sem teto de consultas por execução; evento sem confirmação do Google ciclo após ciclo sem aviso
próprio; ensaio vivo no Google reimportado solto depois de o pai vazio ser apagado; "já trabalhou
com a Manto" ligado por evento marcado que não aconteceu; a edição (e o ramo "já tinha voltado" da
devolução) transforma dia inteiro em bloco com hora e não apaga local no Google (`update_event`);
o `docs/01` não inventaria os endpoints da 224. O relógio do `EventLog` vale para os três registros
de `cancel_ops` (solicitar, recusar e cancelar). Riscar a dívida 49.

Verifies não versionados de `scripts/db/`, cada um com o seu estado depois da 303:
`verify_cancelamento_evento.py` continua válido — chama a limpeza pelo nome passando os outros
eventos vivos (`:257-269`) e passa a exercitar o núcleo novo; `verify_168_admin_config_react.py`
quebra no `cleanup_past` — o dublê devolve lista (`:92-115`) onde o endpoint passa a ler
`ResultadoLimpeza`, e precisa devolver `ResultadoLimpeza` antes de rodar de novo;
`verify_151_excluir_sync.py` **não pode ser rodado sem ajuste** — ele troca
`routes.fetch_single_event` (`:45`), que o "Sincronizar" deixa de usar: a consulta iria ao Google
real com o token do espelho, e o 200 e o 502 que ele espera (`:153-168`) viram 409.

## Riscos que o plano carrega

- O "Devolver" nunca é exercitado contra o Google real antes da produção (a trava impede) — teste
  pós-deploy com evento descartável (quickstart §6).
- Resposta perdida no insert: o Google cria e o sistema não sabe; a mensagem manda conferir antes de
  tentar de novo.
- Entre esta entrega e a seguinte, o evento cancelado de verdade fica marcado e a faixa acesa —
  decisão do dono. Ele continua valendo como qualquer evento (FR-005): a comissão segue no ciclo do
  mês, o cachê do elenco aparece na Planilha quando a data passa, a venda soma na DRE — e o
  Financeiro não vê a faixa. Quem segura é o Superadmin, à mão (spec §Premissas; a confirmar).
- Janela de deploy: bundle novo com backend antigo recebe 404 na faixa (fica oculta); backend novo
  com bundle antigo mostra o evento marcado como comum por minutos. Os dois serviços redeployam no
  mesmo push, em ordem não garantida.
- **O `rollback` do `except` do mês vale só para erro de banco.** Os e-mails de `sync_events` saem
  antes do commit (remoção de escala, `routes.py:2391`; mudança de data, `:2341`, que só não se
  repete pelo carimbo `event_changed_at` gravado na mesma transação; alerta de ensaio, `:2277`). Um
  `rollback` depois deles desfaz a exclusão da vaga, o carimbo e o evento recém-importado, e o mesmo
  e-mail sairia de novo a cada ciclo enquanto o erro persistisse. Por isso o `except` de cada mês
  (ciclo e "Limpar eventos fantasma") faz `rollback()` só em erro de banco (`SQLAlchemyError` — caso
  em que hoje o pendente já se perde e os meses seguintes falham todos); exceção que não é de banco
  mantém o comportamento de hoje: o pendente segue na sessão e entra no commit seguinte. "Marca sem
  aviso" não depende desse `rollback`: a unidade de trabalho da limpeza é o evento, com `rollback`
  próprio (R4). O mesmo risco continua, sem saída nesta entrega, nos caminhos novos que chamam
  `sync_events([item])` dentro da unidade do evento (data nova, R5; reaparecimento, R12): se
  `sync_events` falhar depois do e-mail, o `rollback` do evento repete o e-mail no ciclo seguinte —
  a falha entra em `falhas` e conta como erro do ciclo.
- Evento marcado que foi editado no sistema e depois reaparece sozinho no Google (restaurado da
  lixeira, por exemplo): vale o Google — a edição se perde, o elenco aceito é avisado da "mudança" e
  a vaga criada enquanto marcado que não está no título do Google é apagada, com e-mail de remoção
  (R12). Só a devolução faz valer os dados do sistema (FR-043, FR-044).
- Não há teto de consultas por execução: o disjuntor só abre em falha. Se a lista de um mês
  responder vazia ou cortada com o Google no ar, todo evento daquele mês vira candidato — uma
  consulta por evento, em série, e uma linha `presente_fora_da_lista` por evento e dia. Não é
  destrutivo (hoje esse caso apaga o mês inteiro), mas no "Limpar eventos fantasma" pode passar dos
  180 s do proxy: a tela diz que não concluiu e o Flask termina o trabalho. A contagem de 30/09
  (zero fora da lista) diz que não é o caso hoje.
- Sair de SHOW num evento marcado apaga os ensaios do Google para valer; a devolução recria só o pai.
