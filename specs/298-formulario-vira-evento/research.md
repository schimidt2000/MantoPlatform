# Pesquisa — Feature 298 (Phase 0)

Feita em 10/09/2026 por cinco leituras paralelas do código, cada uma conferida por um verificador
independente, contra o HEAD `f9d4a34` da branch `298-formulario-vira-evento`. As citações
`arquivo:linha` abaixo foram conferidas no disco. Nenhuma incógnita do contexto técnico ficou aberta.

## O que o código faz hoje (fatos que o plano precisa respeitar)

- **`FormResponse`** (`app/models.py:1923-1977`).
  - `created_at` é gravado em **UTC**, sem fuso (`default=datetime.utcnow`, :1959). O resto das
    tabelas novas usa `now_sp`.
  - Não existe nada de encerramento, nem de sugestão descartada. A tabela não tem `__table_args__`.
- **Três caminhos gravam `FormResponse.event_id`**, e só um passa pelo núcleo. Os únicos pontos de
  escrita são `formularios_ops.py:279, 292, 651` e `routes.py:301, 3623`.
  - **Pelo núcleo** `apply_event_link` (`formularios_ops.py:261-283`): trava o vínculo e leva a
    cliente formulário→evento via `ensure_event_client`. Usado pela tela Formulários (`link_event`,
    que **sobrescreve** vínculo existente), pela aba Comercial (`set_event_form_response`, 409 se
    ligado a outro) e pela edição do evento (`update_event_core`, que ignora em silêncio).
  - **Criar evento**: `_link_form_response` (`app/calendar/routes.py:3611-3626`), chamado por
    `_create_event_core` (:3696). Grava à mão, sem cliente, e ignora em silêncio o formulário já
    ligado. O handler da API insere no **Google antes do banco** (`app/api/agenda_write.py:762-772`).
  - **Automático**: `_attempt_auto_link` grava direto (`formularios_ops.py:651`). É chamado no envio
    público (`app/api/formularios_write.py:117-131`) e por `retry_auto_link_pending` (:689-714),
    que roda a cada ciclo do sync (`app/calendar/sync.py:91-92`) sobre **todo** o histórico, filtrando
    só `event_id IS NULL`, `locked=False` e com data.
- **A cliente nunca vai do evento para o formulário.** Quando o evento já tem cliente,
  `ensure_event_client` acrescenta a cliente do formulário como "Outros" (`formularios_ops.py:197-209`).
- **Excluir evento** solta o formulário e preserva `locked` (`routes.py:300-302`). **Cancelar** não
  toca no formulário (`cancel_ops.py`). Os cenários 3 e 4 da História 2 já funcionam assim.
- **`_real_event_candidates`** (`formularios_ops.py:605-615`) não exclui evento cancelado.
- **Sino.**
  - Uma linha por destinatário, com `read_at` por pessoa (`models.py:603-643`) e índice
    `ix_notifications_entity(entity_type, entity_id)` (:629).
  - `marcar_lidas_por_objeto` filtra por usuário (`notificacoes_ops.py:343-355`);
    `apagar_por_entidade` apaga para todos, inclusive as lidas (:358-365).
  - O aviso de resposta sai **mesmo quando o formulário já chega ligado** (`formularios_write.py:139`,
    depois do vínculo automático em :117-131).
- **Contagem.** `count_status` (`formularios_ops.py:154-163`) alimenta a Home
  (`dashboard_service.py:578-585`) e a tela Formulários (`formularios_admin_read.py:85`). No front,
  `FormulariosSummary = StatusCounts` (`lib/types.ts:148`), e mudar um muda o outro.
- **Corte.** `dashboard_cutoff()` (`app/api/dashboard_service.py:19-23`) devolve meia-noite sem fuso
  e, sem `release_date`, cai em `date.today()`, que é UTC em produção. `formularios_ops` não tem
  corte nenhum.
- **Dados das respostas.** `FormResponse.data` é JSON `[{"secao","campos":[[chave, rótulo, valor]]}]`.
  Desde 01/06 convivem **dois vocabulários de chave**:
  - o formulário nativo (seed `a51ce3dc4f3c`);
  - a carga WhatsForm, que foi até 09/07/2026 com `created_at` histórico. Nela as chaves são *slugs*
    do rótulo, a data e a hora vêm juntas em `data_do_evento`, e não há `hora_evento`.
- **Cadastro de evento.**
  - O `POST /api/events` exige título, data, início, fim, vendedor e valor > 0 salvo cortesia
    (`eventFormSchema.ts:6-45`).
  - `payment_method` não tem lista branca na API. O `PagamentoBlock` oferece quatro formas (`avista`,
    `pix_parcelado`, `faturado`, `cartao`).
  - Não há colunas de tema, aniversariante, espaço, período nem CEP: isso vai para `observations`
    rotuladas.
  - `characters` vira `EventRole` real ao salvar.
- **Cache do front.** Criar evento, editar evento e ligar pela aba Comercial não invalidam
  `["dashboard"]`, `["formularios-respostas"]` nem `["notificacoes"]` (`eventCreate.ts:187-212`,
  `eventInline.ts:104-110`). As chaves do sino não são exportadas (`notificacoes.ts:45-46`).
- **Verify.** Não há listener do ORM; semear direto no banco não sincroniza nada. O `POST
  /api/events` chega ao Google de verdade (`service.py:263`) e `_suppress_calendar_invites` não o
  cobre (`config.py:133-135`).

## Decisões

### R1 — Corte pela data de chegada, com fuso e default real
- **Decisão.** Função `corte_de_chegada()` em `formularios_ops`:
  - usa `SiteSetting.release_date` ou, na falta, a constante `CORTE_FORMULARIOS_PADRAO = date(2026, 6, 1)`
    (`app/constants.py`);
  - devolve a meia-noite de São Paulo convertida para UTC (hoje, 01/06 03:00), porque `created_at`
    é UTC.
- **Por quê.**
  - A spec manda contar no fuso de São Paulo e `created_at` é UTC: sem conversão, formulário de 31/05
    depois das 21h entraria na lista.
  - O default real segue o Princípio XIV.
  - Reusar `dashboard_cutoff()` como está herdaria o `date.today()` em UTC.
- **Alternativas.**
  - Reusar `dashboard_cutoff()`: rejeitado pelo fuso e pelo fallback.
  - Coluna nova de corte: rejeitado, porque o dono quer o mesmo corte das cobranças.

### R2 — Três destinos que se excluem, e uma fonte só para as contagens
- **Decisão.** Todo formulário cai em exatamente uma das quatro partições, calculadas por
  `_status_condition` / `count_status`:
  - `historico` = chegou antes do corte;
  - desde o corte, `com_evento` = tem evento;
  - `encerrados` = encerrado e sem evento;
  - `sem_destino` = nem um nem outro.
- **Invariante.** Encerrar exige formulário sem evento; ligar a um evento limpa o encerramento.
- **Contagens.** `count_status()` passa a devolver `{total, sem_destino, com_evento, encerrados,
  historico}`, e os filtros antigos (`sem_evento`, `sem_cliente`, `ambiguos`, `futuros_sem_evento`)
  saem. A Home deixa de usar `StatusCounts` como tipo próprio (ver R8).
- **Por quê.** FR-002, FR-006 e FR-017: o cartão "Sem destino" e a lista da Home precisam do mesmo
  número, com partições que somam o total.
- **Alternativa.** Manter os filtros antigos com o corte aplicado: rejeitado no `/speckit-clarify`.

### R3 — Encerramento em colunas; sugestão descartada numa tabela
- **Decisão.**
  - `form_responses` ganha `closed_reason`, `closed_note`, `closed_by_id` (FK `users`, `SET NULL`) e
    `closed_at` (UTC, como `created_at`).
  - Tabela nova `form_response_dismissed_events`, com `UNIQUE(form_response_id, event_id)` e as duas
    FKs em `CASCADE`.
  - Índice parcial `ix_form_responses_sem_destino (created_at) WHERE event_id IS NULL AND closed_at
    IS NULL`, espelhado em `__table_args__`.
- **Por quê.**
  - O encerramento é um estado do próprio formulário, lido em toda contagem.
  - A sugestão descartada é um par que some sozinho se o formulário ou o evento for apagado.
  - Tudo é aditivo e nullable: dispensa ensaio destrutivo.
- **Alternativas.**
  - JSON de descartes no formulário: rejeitado, porque não limpa ao apagar o evento.
  - Tabela de "destinos" com histórico: é complexidade sem pedido do dono.

### R4 — Um núcleo único para "ganhar destino", por onde passam os três caminhos
- **Decisão.** `apply_event_link(response, event, *, source="manual", decisao_humana=True)` (nome fixado na R27) passa a ser a
  única porta de vínculo e faz, na mesma transação:
  - limpa o encerramento;
  - leva a cliente nos dois sentidos (R5);
  - marca como lido para todos o aviso do sino (R6);
  - devolve se houve divergência de cliente.
- **Quem passa a entrar pelo núcleo.**
  - `_link_form_response` (criar evento).
  - `_attempt_auto_link` e `retry_auto_link_pending` (automático), com `decisao_humana=False` e
    `source="auto_date"`: o vínculo automático continua destravado, e a exclusão do evento continua
    devolvendo o formulário à automação.
  - A regra de casamento automático não muda (FR-011).
- **Por quê.** Os verificadores mostraram que pôr a lógica só em `apply_event_link` não cobre a
  História 5 nem o vínculo automático. Também mostraram que forçar `locked=True` no automático
  quebraria a religação depois de excluir o evento.
- **Alternativa.** Um "helper de efeitos" chamado ao lado de cada caminho: rejeitado, porque deixa
  três lugares para esquecer.

### R5 — A cliente nos dois sentidos, sem trocar ninguém
- **Decisão.** Dentro do núcleo:
  - formulário sem cliente recebe a cliente do evento. Prefere o `EventClient` cujo telefone é o do
    formulário; na falta, `event.client_id`. Grava `client_link_source="evento"`, valor novo;
  - evento sem cliente recebe a do formulário (`ensure_event_client`, como hoje);
  - com as duas preenchidas e diferentes, **não mexe em nada**. Deixa de acrescentar como "Outros"
    e devolve `divergencia_cliente`, que a tela mostra.
- **Por quê.** FR-015 e História 6, cenário 3. Hoje 69 formulários desde junho estão ligados a
  evento com cliente e aparecem sem cliente.
- **Alternativa.** Manter o "Outros": rejeitado, porque muda o evento quando as clientes divergem.

### R6 — O sino marca como lido para todos, sem apagar
- **Decisão.**
  - Nova `notificacoes_ops.marcar_lidas_por_entidade(entity_type, entity_id, kind=None)`: UPDATE
    `read_at` com `read_at IS NULL`, sem filtro de usuário e sem commit. Usa `ix_notifications_entity`.
  - Chamada pelo núcleo (R4) e pelo encerramento.
  - O envio público deixa de emitir o aviso quando o formulário já chega com evento.
- **Por quê.**
  - Aviso lido continua lido (spec, casos de borda) e o histórico de `/notificacoes` fica; a
    retenção 30/180 dias limpa sozinha.
  - `apagar_por_entidade` levaria junto as lidas.
- **Correção de dados.** CLI `flask formularios-avisos-resolvidos` (dry-run por padrão,
  `--execute`), rodado uma vez em produção. Zera os 35 avisos acesos de hoje (SC-007).
- **Alternativa.** Fazer a correção dentro da migration: rejeitado, porque a casa corrige dados por
  CLI com dry-run (267b, 239b) e a migration fica só com esquema.

### R7 — Concorrência: trava na linha e 409 "já tem destino"
- **Decisão.**
  - Ligar, encerrar, reabrir, escolher entre repetidos e confirmar sugestão leem o formulário com
    `with_for_update()` (padrão de `virtuais_ops.py:763`), reconferem o estado e respondem **409**
    se ele mudou.
  - `link_event` deixa de sobrescrever: 409 quando o formulário já tem evento. A tela nunca oferece
    ligar formulário já ligado, então nenhum uso legítimo depende da sobrescrita.
  - `POST /api/events` com `form_response_id` de formulário já ligado responde **409 antes de
    inserir no Google**.
    - Diferente da guarda do orçamento (`agenda_write.py:746-760`), que só lê, aqui o formulário é
      **bloqueado** (`FOR UPDATE`) antes do `_insert_event`, e o bloqueio dura até o commit do
      `_create_event_core`.
    - A segunda requisição espera e recebe 409. Custo aceito: a linha fica presa durante a chamada ao
      Google.
  - `_link_form_response` levanta `FormularioJaTemDestino` em vez de pular em silêncio.
  - A edição do evento (`update_event_core`) e a aba Comercial (`set_event_form_response`) passam a
    responder o mesmo 409 com a mesma mensagem.
- **Por quê.** FR-018 e o caso de borda "duas pessoas no mesmo formulário". Sem a guarda, dois
  cliques em "Criar evento" deixam uma festa duplicada no Google.
- **Alternativa.** Checar só em Python: rejeitado, porque os verificadores mostraram a corrida.

### R8 — A Home recebe as linhas prontas, calculadas no servidor
- **Decisão.** O bloco `formularios` do `/api/dashboard` vira `{contagens, a_chegar[], ja_passou[],
  pode_criar_evento}`, e cada linha já traz severidade, marcas e sugestão (contrato em
  `contracts/dashboard-formularios.md`).
  - O cálculo mora em `app/formularios/destino_ops.py`, no molde de `compute_comercial_pending`
    (`dashboard_service.py:270-345`).
  - O front só mapeia severidade → cor.
  - A lista de urgentes do topo conta os formulários das linhas vermelhas.
- **Por quê.**
  - Severidade e datas em fuso de São Paulo são regra de negócio (Princípio III).
  - A tela Formulários já erra "hoje" no navegador (`FormulariosAdminPage.tsx:166-169`).
  - "Há N dias" calculado no navegador com `created_at` em UTC sai 3 h errado.
- **Alternativa.** Endpoint próprio para a lista: rejeitado, porque a Home já tem o bloco com gate e
  isolamento de falha (`_bloco`).

### R9 — Agrupamento pelo telefone, com a última chegada como representante
- **Decisão.**
  - Os formulários sem destino com o mesmo `contact_phone` normalizado viram **uma linha**.
  - A linha usa o formulário que chegou por último (o preenchimento mais recente é o mais
    provável de estar certo) para decidir grupo, data e cor.
  - Formulário sem telefone fica sozinho.
  - "Este é o que vale" encerra os outros como `repetido`, numa transação só.
- **Por quê.** História 3 e FR-009. O telefone já é normalizado igual nos dois lados
  (`importer.py:43-62`).
- **Limite conhecido.** Celular antigo sem o 9º dígito não agrupa. Aceito e registrado como risco.

### R10 — Sugestão em lote, sem uma consulta por linha
- **Decisão.**
  - Uma consulta de eventos candidatos para todos os telefones das linhas: não cancelados, fora de
    ensaio e satélite, sem nenhum formulário ligado, sem par descartado, e cliente (`EventClient`)
    com o telefone do formulário.
  - O casamento por diferença de datas é feito em Python: até 3 dias na lista (FR-010) e qualquer
    data desde o corte no aviso do cadastro (FR-013).
  - Confirmar a sugestão passa pelo núcleo (R4), com `source="manual"`.
- **Por quê.** A lista tem poucas dezenas de linhas, então duas consultas bastam. Também corrige para
  a sugestão a falta do filtro de cancelados de `_real_event_candidates`.

### R11 — Pré-preenchimento: um extrator puro com mapa de sinônimos
- **Decisão.**
  - `app/formularios/pre_evento_ops.py` com `extrair_para_evento(response)`, que devolve valores,
    origem de cada campo, observações rotuladas, alertas e eventos existentes da cliente.
  - Um mapa de sinônimos cobre os dois vocabulários (nativo e WhatsForm). A tabela está em
    `contracts/pre-evento.md`.
  - Endpoint `GET /api/formularios/respostas/<id>/para-evento`, só leitura, com gate
    `_can_create_event` (COMERCIAL e SUPERADMIN).
- **Regras de transformação.**
  - Hora e período são interpretados só quando o texto é inequívoco. Se não for, o campo fica vazio
    com o texto da cliente no alerta, e a comercial preenche (o fim é obrigatório).
  - Forma de pagamento por tabela constante; sem correspondente (boleto, "cartão 3x com 15%",
    "Outros") fica em branco com o texto ao lado.
  - Tema, aniversariante, espaço, briefing e observações contratuais viram `observations` de texto
    rotuladas, e não `description`, que vai para o Google.
  - Personagens entram como sugestão em `characters`, só gravados quando a comercial salva, e o texto
    original fica numa observação.
- **Por quê.**
  - Metade dos formulários desde junho vem da carga WhatsForm: um extrator só com as chaves nativas
    deixaria essas festas sem preenchimento.
  - O detalhe atual (`_require_vendas`) marca o sino como lido ao abrir, e o gate de criar evento é
    outro.
- **Alternativa.** `?resposta_id=` no `GET /api/events/new/prefill` (plano 278): rejeitado nesta
  feature. Aquele endpoint é do orçamento, e juntar as duas origens exige a regra "orçamento manda
  no preço", fora de escopo.

### R12 — Cores e grupos
- **Decisão.**
  - Grupo "a data informada ainda vai chegar", com data ≥ hoje em SP, em ordem crescente de data.
  - Grupo "a data informada já passou", em ordem decrescente de data.
  - Cor: **vermelho** se 0–7 dias; **amarelo** se 8–30 dias e em todo "já passou"; **cinza** acima de
    30 dias ou com **data suspeita** (antes do dia de chegada, ou mais de 2 anos à frente).
  - Na tela, os fundos de linha usam os tokens `bg-red-50` / `bg-gold-50`, que acompanham o tema
    escuro, e as marcas usam `MetricBadge` com os tons `red` / `gold` / `neutral`.
- **Por quê.** Decisões do `/speckit-clarify` de 10/09. Os fundos rgba fixos das linhas atuais da Home
  não acompanham o tema escuro.

### R13 — Invalidação do front num helper só
- **Decisão.**
  - `lib/notificacoes.ts` exporta `invalidarNotificacoes(qc)`.
  - `lib/formulariosAdmin.ts` ganha `invalidarDestinoDeFormulario(qc, id?)`, que invalida detalhe,
    lista, busca, `["dashboard"]`, `["clientes-metricas"]` e `["notificacoes"]`.
  - O helper é chamado pelas mutations novas e por `useCreateEvent`, `useUpdateEvent` e
    `useSetEventFormResponse`.
- **Por quê.** Sem isso, a linha continua na Home até 30 s depois de "Criar evento" (`staleTime` de
  `queryClient.ts:39-40`).

### R14 — Datas com fuso na API
- **Decisão.** O resumo da resposta passa a serializar `created_at` e `closed_at` com `+00:00`.
- **Por quê.** Corrige de carona o "Recebida em" que hoje sai 3 h adiantado na tabela
  (`FormulariosAdminPage.tsx:85-93`) e deixa correto o que a lista nova mostra.
- **Contrato.** É aditivo: `new Date(iso)` passa a ler certo, e `formatDate` (fatia os 10 primeiros
  caracteres) continua funcionando.

### R15 — Verify sem tocar no Google
- **Decisão.**
  - O `verify_298.py` segue o esqueleto da `verify_297.py`: `MANTO_SEM_THREADS`, `limiter.enabled =
    False`, conexão separada, requisições fora do `app_context`.
  - Formulários, clientes e eventos são semeados direto no banco, com `created_at` controlado e
    `google_event_id` com prefixo.
  - Dentro do processo do verify, `app.calendar.routes.insert_event` é trocado por uma chamada falsa
    que levanta exceção. A view importa a função na hora da requisição (`agenda_write.py:740`), então
    a troca vale.
  - O único `POST /api/events` é o do cenário 14a (guarda de 409). Mesmo antes de a guarda existir, a
    chamada falsa impede qualquer escrita no Google.
  - Todo evento de teste leva "[TESTE verify 298] pode apagar" no título (decisão do dono, 11/09).
  - Nunca `DELETE /api/events`.
  - O "evento excluído" usa `_delete_event(..., also_from_google=False)`.
  - Os avisos do sino são criados para usuários descartáveis e limpos por entidade.
- **Por quê.** O `POST /api/events` escreve no calendário real da empresa.
- **Defeitos herdados que não se copiam.** A `verify_266.py` usa `RATELIMIT_ENABLED`, que não surte
  efeito, e não define `MANTO_SEM_THREADS`.

## Decisões acrescentadas em 11/09 (respostas do dono ao checklist `revisao.md`)

### R16 — Divergência de cliente: o evento manda, a comercial decide o formulário
- **Decisão.**
  - Ao ligar, o núcleo não mexe em nada quando as duas clientes existem e diferem (R5), e devolve
    `divergencia_cliente`.
  - Endpoint `POST /api/formularios/respostas/<id>/usar-cliente-do-evento`, com `_require_vendas`,
    grava a cliente do evento no formulário, com `client_link_source='evento'`.
- **Por quê.** Quem vale para cobrança e agenda é a cliente do evento. A do formulário é registro de
  quem preencheu, e trocá-la sozinho apagaria isso.
- **Alternativas.**
  - Só avisar: deixa a divergência sem saída.
  - O evento manda sozinho: perde o registro sem perguntar.

### R17 — Descarte de sugestão definitivo
- **Decisão.** Sem rota para desfazer. O par fica em `form_response_dismissed_events` para sempre, e a
  ligação à mão pela tela Formulários continua possível.
- **Por quê.** O caso é raro e o caminho manual já existe. Uma tela de "sugestões descartadas"
  seria mais um lugar para algo que quase não acontece.

### R18 — Histórico de encerrar e reabrir no `audit_logs`, sem tabela nova
- **Decisão.** Usar o helper `audit()` (`app/utils.py:46`), que não comita e grava o ator a partir de
  `current_user`. As ações são `formulario.encerrado` e `formulario.reaberto`, com o motivo em
  `detail`. O formulário guarda só o estado atual.
- **Por quê.** O `audit_logs` já é o histórico de ações do sistema (`app/models.py:584-600`), com
  índice por entidade, e já tem precedentes em gastos, sync e avaliações. Não precisa de coluna nem
  de tabela de histórico.
- **Alternativa.** Tabela `form_response_closures`: rejeitada por ser estrutura nova sem leitura
  prevista na tela.

## Decisões acrescentadas pelo `/speckit-analyze` (11/09)

### R19 — Motivos de encerramento servidos pelo servidor
A lista `[{codigo, rotulo}]` sai de `FORM_CLOSE_REASON_LABELS` no detalhe do formulário e no bloco
`formularios` do dashboard. O diálogo desenha o `<select>` a partir dela, sem mapa em TS (Princípio
I; molde `figurino_producao_read.py:80`).

### R20 — Data suspeita sem botão desabilitado
O Salvar fica sempre ativo. No envio, se a data suspeita não foi confirmada nem trocada, `setError`
no campo `date` com a explicação, e o efeito de foco que já existe leva até ela
(`EventCreatePage.tsx:265-275`). A explicação aparece ao lado da data desde que o cadastro abre
(Princípio V; decisão do dono).

### R21 — Campos novos opcionais no React
Portão da constituição (`constitution.md:297-298`): `contagens`, `a_chegar`, `ja_passou`,
`pode_criar_evento`, `motivos_encerramento`, `corte`, `destino`, `closed_*`, `truncado`,
`divergencia_cliente` e `sugestao` entram opcionais nos tipos e são lidos com fallback.

### R22 — Envio público: a cliente pelo telefone antes do vínculo automático
Em `formularios_write.py`, `attempt_auto_link_client` passa a rodar antes de `_attempt_auto_link`.
Assim a origem `auto_phone` e o `fill_client_from_response`, que completa CPF/CNPJ e endereço na
ficha, continuam valendo. As regravações duplicadas (`:119-120`, `:128-129`) saem, porque o núcleo
já faz isso.

### R23 — Correção única dos formulários já ligados sem cliente
Comando `flask formularios-cliente-do-evento [--execute]` (FR-020), irmão do
`formularios-avisos-resolvidos`. Aplica a mesma escolha do núcleo (EventClient pelo telefone, senão
`event.client_id`, com `client_link_source='evento'`) nos formulários desde o corte com evento com
cliente e `client_id` nulo. Por padrão só conta.

### R24 — Linha resolvida sai com transição
`AnimatePresence` na lista do painel, com `exit` de 150–350 ms e `useReducedMotion`. Onde a transição
não for possível, fica sem animação (aceito pelo dono).

### R25 — "Não é este" com confirmação
`ConfirmDialog` do `@manto/ui`: "A sugestão não voltará para este formulário; ainda dá para ligar à
mão pela tela Formulários". O descarte usa `INSERT … ON CONFLICT DO NOTHING`, ou captura o
`IntegrityError`, e devolve 200 também na segunda vez.

### R26 — "Divergem" e onde a divergência aparece
**Divergem** = a cliente do formulário não é nenhuma das clientes do evento (`EventClient`). O
resultado do vínculo volta nos endpoints da tela Formulários, da sugestão e do `vincular-evento`
usado pelo cadastro. O detalhe do formulário recalcula e mostra a divergência enquanto ela existir.

### R27 — Nomes sem ambiguidade
- O parâmetro do núcleo que grava `event_link_locked` chama-se `decisao_humana`.
- "Bloquear" (`bloquear_formulario`, `SELECT … FOR UPDATE`) é só o bloqueio de linha.
- O valor de `destino` usa as mesmas grafias das partições: `sem_destino`, `com_evento`,
  `encerrados` e `historico`.
- O tipo exibido é `tipo_rotulo` = "Festa" / "Corporativo".

### R28 — Distância em palavras a partir do servidor, e o corte entregue ao front
- A linha usa `dias_ate_a_data` e `dias_desde_chegada` do servidor, com um formatador local ("hoje",
  "amanhã", "em N dias", "passou há N dias"). `formatRelativeDay` não serve: diz "ontem" e "há N
  dias" e usa o relógio do navegador. `formatShortDate` fica só para a data.
- As contagens trazem `corte` (AAAA-MM-DD, dia em SP), para os rótulos "desde DD/MM" e "antes de
  DD/MM".
