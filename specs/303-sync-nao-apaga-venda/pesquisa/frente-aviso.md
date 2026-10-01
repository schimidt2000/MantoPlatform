# Frente aviso

Faixa no topo e sino (FR-009, FR-010, FR-023 na parte do aviso) — feature 303

Tamanho: M — 1 produtor novo no sino, 1 endpoint GET em módulo existente, 1 função de núcleo, 1 componente + 1 arquivo de hooks no front, e 6 toques pequenos (AppShell, EventDetailPage, DashboardPage, NotificacaoItem, eventOps, _delete_event). Sem migration própria: depende da coluna da marca (frente da trava) e pede a ela 1 índice parcial, a marca por UPDATE condicional, o rollback no loop do sync e as chamadas de marcar-lidas nas saídas da marca. Nada foi executado: leitura de código apenas; a contagem de usuários COMERCIAL e de eventos passados sem Google fica para o plan, no espelho.

## A1 — Qual é o kind novo do sino: constante, destinatários, severidade, entidade, link e ícone?

**Decisão.** `KIND_EVENTO_SUMIU_GOOGLE = "evento.sumiu_google"` no catálogo de `app/notificacoes/notificacoes_ops.py`, com `DESTINATARIOS_POR_KIND[...] = (RoleName.COMERCIAL, RoleName.SUPERADMIN)`. Severidade sempre `urgent`. Entidade fraca `("calendar_event", event.id)`. `link_path = f"/events/{event.id}"` (sem `?aba=`: a marca fica no EventHeader, acima das abas). No front, uma linha no mapa de ícones: `"evento.sumiu_google": CalendarX`. Nenhuma tabela, endpoint ou tela nova para o sino.

**Porquê.** É a receita que o próprio módulo prescreve para produtor novo (notificacoes_ops.py:13-16) e `emitir` recusa kind fora do catálogo (137-138). `resolver_destinatarios` já filtra ativo + `has_access` e deduplica quem tem os dois papéis (82-98). O revendedor puro não é endereçado e nem tem sino (AppShell.tsx:156-158). `urgent` dá borda e ícone vermelhos sem mexer na UI (NotificacaoItem.tsx:29-44). Comercial e Superadmin abrem `/events/:id`, então ninguém é avisado de um link que não pode abrir (regra do comentário em notificacoes_ops.py:58-59).

**Alternativas rejeitadas.** (1) Reusar um kind existente com texto diferente: rejeitado — `marcar_lidas_por_entidade(..., kind)` e o mapa de ícones filtram por kind, e o aviso se misturaria com avaliação/recusa. (2) `severity` variável (urgent só se o evento for em ≤7 dias, como a recusa em notificacoes_ops.py:255-257): rejeitado — o dono pediu algo marcante e todo sumiço com dinheiro exige decisão. (3) Não mapear ícone (cai no Bell, como o recado NFC): aceitável, mas a linha custa nada e distingue o aviso na caixa.

**Contrato.** Constantes: `KIND_EVENTO_SUMIU_GOOGLE = "evento.sumiu_google"` (19 caracteres; coluna `kind` String(40)); `entity_type = "calendar_event"` (14; coluna String(30)); `link_path = "/events/<id>"` (coluna String(300)); `severity = "urgent"`. Front: `ICONE_POR_KIND["evento.sumiu_google"] = CalendarX` (lucide-react ^0.462).

**Pontos de toque.**
- app/notificacoes/notificacoes_ops.py:47-61 (catálogo e DESTINATARIOS_POR_KIND)
- app/notificacoes/notificacoes_ops.py:82-98 (resolver_destinatarios, sem mudança)
- app/models.py:634-641 (limites de coluna de Notification)
- frontend/apps/internal/src/components/notificacoes/NotificacaoItem.tsx:1,7-11 (ICONE_POR_KIND)

**Riscos.**
- Usuário que é COMERCIAL e REVENDEDOR ao mesmo tempo recebe o aviso (não é `isRevendedorOnly`). É o comportamento desejado, mas o plan deve contar no espelho quantos são.
- O texto do estado vazio do painel (NotificacoesPanel.tsx:117-120) lista só três tipos de aviso; fica como está (não mente, só não cita o novo).

**Verify.** Cenário 2: por conexão separada, contar linhas de `notifications` com `kind='evento.sumiu_google'` e `entity_id=<evento>`; tem de ser exatamente uma por usuário devolvido pelo mesmo filtro de `resolver_destinatarios` (contar no banco, não presumir — o manto_local tem usuários reais). Conferir `severity='urgent'`, `entity_type='calendar_event'`, `link_path='/events/<id>'`. Um usuário FIGURINO descartável NÃO pode ter linha. Limpar no `finally` com `apagar_por_entidade`.

**Revisão adversarial: sim.** Não consegui refutar. O catálogo recusa kind fora da lista, o resolvedor já filtra ativo + has_access e deduplica, e os limites de coluna fecham (kind 19/40, entity_type 14/30). Nenhum outro ponto do repo enumera os kinds além do catálogo e do mapa de ícones, então não há consumidor escondido. O link sem `?aba=` cai no Resumo. Dois detalhes menores: o docstring do módulo declara que ele importa só db/models/constants/sqlalchemy, e o texto do estado vazio do sino lista três tipos (já omite o recado NFC).

**Emenda.** Manter. Ao tocar o módulo, atualizar o docstring de imports (passa a incluir `app.money` e `CalendarEvent`) e o comentário de `NotificacaoItem` que descreve quando é `urgent`. O texto do estado vazio pode ficar como está.

**Evidência da revisão.** app/notificacoes/notificacoes_ops.py:8-11, 47-61, 82-98, 137-138; app/models.py:634-641; frontend/apps/internal/src/components/notificacoes/NotificacaoItem.tsx:7-11, 22-24, 27; NotificacoesPanel.tsx:117-120; EventDetailPage.tsx:202-205

## A2 — Qual dedupe_key garante uma notificação por sumiço, nunca repetida a cada ciclo, e um aviso novo se o evento sumir de novo depois de reaparecer?

**Decisão.** `dedupe_key = f"{KIND_EVENTO_SUMIU_GOOGLE}:{event.id}:{marcado_em:%Y%m%d%H%M%S%f}"`, em que `marcado_em` é o valor GRAVADO na coluna da marca (o carimbo daquele sumiço), nunca `now_sp()` lido na hora da emissão. O produtor só é chamado na transição sem marca → marcado.

**Porquê.** A UNIQUE é `(user_id, dedupe_key)` (models.py:622). Carimbo igual = mesmo sumiço: chamar de novo no ciclo seguinte é no-op pelo SELECT de `emitir` (notificacoes_ops.py:149-156). Reapareceu (marca zerada) e sumiu de novo = carimbo novo = chave nova = aviso novo, como pede o caso de borda da spec. A chave por dia do convite recusado (264) não serve: some-reaparece-some no mesmo dia não reavisaria. Microssegundos (`%f`) para o verify não precisar dormir 1 s entre dois sumiços e para dois sumiços no mesmo segundo não colidirem; o Postgres guarda microssegundo.

**Alternativas rejeitadas.** (1) Chave por dia `:AAAAMMDD`: rejeitada (não reavisa no mesmo dia). (2) Chave sem marcador `kind:id`: rejeitada (o segundo sumiço nunca avisaria; a linha antiga só sai pela retenção de 30/180 dias). (3) Contador de sumiços em coluna própria: rejeitada — coluna a mais para o que o carimbo já dá.

**Contrato.** Formato: `evento.sumiu_google:<event_id>:<AAAAMMDDHHMMSSffffff>` — no máximo 19+1+10+1+20 = 51 caracteres (limite 120; `emitir` corta em 120 na linha 175). Pré-requisito para a frente da trava: a marca é um DateTime naive São Paulo (`now_sp`), NULL = não marcado, zerada no reaparecimento e na decisão.

**Pontos de toque.**
- app/notificacoes/notificacoes_ops.py:101-185 (emitir; dedupe em duas camadas, sem mudança)
- app/models.py:622,641 (UNIQUE e dedupe_key String(120))
- coluna da marca em CalendarEvent (definida pela frente da trava; aqui chamada `google_missing_at`)

**Riscos.**
- Se a frente da trava gravar a marca como Date (sem hora), a chave volta a ser 'por dia' e o segundo sumiço do mesmo dia não avisa. A coluna tem de ser DateTime.
- Corrida entre o ciclo automático e o 'Limpar eventos fantasma': os dois veem o evento sem marca e gravam carimbos diferentes → duas notificações por pessoa. A marca tem de ser tomada por UPDATE condicional (`... WHERE id=:id AND <marca> IS NULL`, rowcount 1 ganha), no padrão de `_claim_auto_sync` (sync.py:122-150); só quem ganha chama o produtor.

**Verify.** Cenário 2: rodar o sync mais duas vezes e provar delta zero de linhas. Caso de borda: marcar → fazer reaparecer (marca some) → sumir de novo: tem de existir uma SEGUNDA linha por destinatário, com dedupe_key diferente. Prova por mutação: com a chave sem o carimbo, o segundo sumiço não gera linha.

**Revisão adversarial: sim.** A chave com o carimbo gravado cumpre 'cada sumiço é um aviso novo' e é no-op nos ciclos seguintes. O ponto fraco é o que a proposta já aponta: dois limpadores concorrentes gravam carimbos diferentes e a UNIQUE não pega. O ciclo automático tem claim atômico, mas o 'Limpar eventos fantasma' e a rota antiga `force_sync` não passam por ele. Falta dizer que, depois de um UPDATE por Core, o objeto ORM carregado no laço fica com a marca velha.

**Emenda.** Manter a chave. Fixar no contrato com a frente da trava: (1) a função de marcar devolve o carimbo que ELA gravou (o `:now` do UPDATE condicional) e é esse valor que vai ao produtor, nunca uma releitura do objeto; (2) depois do UPDATE, `db.session.refresh(ev)` antes de usar o evento; (3) quem perde o UPDATE (rowcount 0) não chama produtor nem escreve histórico.

**Evidência da revisão.** app/models.py:622, 641; app/notificacoes/notificacoes_ops.py:149-156, 175; app/calendar/sync.py:122-150 (claim só do ciclo automático); app/api/admin_config_write.py:92-106 e app/calendar/routes.py:470-476 (limpam sem claim)

## A3 — Qual é o texto do aviso e quem calcula venda, recebido e escalados?

**Decisão.** Produtor novo `notificar_evento_sumiu_google(event, *, marcado_em, venda, recebido, escalados)` em notificacoes_ops. Título: `"Sumiu do Google Agenda — <título do evento>"`. Corpo: `"<dd/mm/aaaa> · venda R$ X · recebido R$ Y · N pessoa(s) escalada(s)"`, com as variantes `sem data`, `sem venda` e `ninguém escalado`. Os três números chegam por parâmetro, vindos da MESMA função da frente da trava que decide a FR-001 e escreve o histórico ("o que está preso"). Dinheiro formatado com `app.money.format_brl(valor, prefix=True)`.

**Porquê.** A FR-010 pede título, data, venda, recebido, número de escalados e link. O prefixo fixo vem primeiro porque `emitir` corta o título em 200 (notificacoes_ops.py:170) e o painel trunca em uma linha (NotificacaoItem.tsx:53,58): o fato tem de sobreviver ao corte. Receber os números por parâmetro evita duas coisas: importar `cancel_ops` num módulo que se declara puro (notificacoes_ops.py:8-11) e refazer a conta de `total_recebido` (cancel_ops.py:47-54) e a contagem de escalados — que na 303 exclui o técnico de som automático; um segundo cálculo aqui divergiria do histórico e da decisão. `app/money.py` é puro por declaração (money.py:6-7) e é a fonte única de formatação (Princípio IX).

**Alternativas rejeitadas.** (1) O produtor consulta EventPayment e EventRole sozinho: rejeitado — duplica `total_recebido` e a regra do técnico de som (Princípio I). (2) Título = só o título do evento, com o fato no corpo: rejeitado — na linha truncada do sino o aviso pareceria um evento qualquer. (3) `f"R$ {valor:,.2f}"` local, como os `_brl` de producao_ops.py:127 e desempenho_ops.py:539: rejeitado — já existe `format_brl`.

**Contrato.** ```python
def notificar_evento_sumiu_google(
    event: CalendarEvent, *, marcado_em: datetime,
    venda: Decimal | None, recebido: Decimal, escalados: int,
) -> int:
    """Evento com dinheiro sumiu do Google → COMERCIAL/SUPERADMIN. Regime A. Não comita."""
```
Título (≤200): `Sumiu do Google Agenda — {event.title}`. Corpo (≤500), exemplo: `15/11/2026 · venda R$ 2.000,00 · recebido R$ 1.000,00 · 3 pessoas escaladas`; `1 pessoa escalada`; `ninguém escalado`; `sem venda` quando `venda` é None ou 0; `sem data` quando `start_at` é None. Retorno: linhas gravadas (int).

**Pontos de toque.**
- app/notificacoes/notificacoes_ops.py:188-290 (produtores; o novo entra aqui)
- app/notificacoes/notificacoes_ops.py:39-41 (imports: acrescentar `from app.money import format_brl` e `Decimal`)
- app/money.py:23-49 (format_brl)
- app/calendar/cancel_ops.py:47-54 (total_recebido — quem chama usa, o produtor não)
- ponto da marca na frente da trava (hoje app/calendar/routes.py:371-385, dentro de _cleanup_stale_events)

**Riscos.**
- Título do evento tem até 500 caracteres (models.py:251): o corte em 200 pode partir o nome do elenco. É só apresentação; o link leva ao evento.
- Satélite de grupo marcado aparece como 'sem venda · recebido R$ 0,00': é verdade (a venda mora no líder), mas pode parecer alarme falso. A tela do evento explica; o corpo não ganha caso especial.

**Verify.** Conferir no banco (conexão separada) que `title` começa com 'Sumiu do Google Agenda — ' e que `body` contém a data em dd/mm/aaaa, 'R$ 2.000,00', 'R$ 1.000,00' e '1 pessoa escalada' no evento do cenário 1. Variante do cenário 3 (sem venda, com comprovante): corpo com 'sem venda'. Conferir que o número de escalados do corpo é o mesmo do histórico do evento.

**Revisão adversarial: parcial.** O produtor recebe três números soltos, mas o histórico da A4 descreve cinco fatos (venda, recebido, escalados, contrato, grupo). São duas listas de parâmetros para o mesmo 'o que está preso', com chance de divergir. Sem o dado de grupo, o satélite sai como 'sem venda · recebido R$ 0,00' num aviso vermelho: parece alarme falso, e a proposta aceita isso como risco quando o dado já existe em quem chama. `format_brl(valor, prefix=True)` existe e é puro.

**Emenda.** A frente da trava devolve UMA estrutura imutável (ex.: dataclass `PresoAoEvento(venda, recebido, escalados, tem_contrato, em_grupo)`) usada pela decisão da FR-001, pelo texto do histórico e pelo produtor: `notificar_evento_sumiu_google(event, *, marcado_em, preso)`. Corpo do satélite/líder: trocar 'sem venda' por 'parte de grupo comercial' quando `em_grupo`. Registrar no contrato que `escalados` é a contagem da FR-001 (sem o técnico automático), para o verify comparar com o histórico e não com a tela.

**Evidência da revisão.** app/money.py:23-49; app/notificacoes/notificacoes_ops.py:39-41, 170-171; app/calendar/cancel_ops.py:47-54, 84-88; texto do histórico na própria proposta A4 ('Preso: venda, recebido, escalados, contrato, grupo')

## A4 — Em que regime de transação o aviso nasce, e como o 'avisar' entra no histórico e na auditoria (FR-023)?

**Decisão.** Regime A, atômico com a marca: `ganhar a marca (UPDATE condicional) → flush → n = notificar_evento_sumiu_google(...) → EventLog + _log_sync com o que está preso e 'aviso enviado a n pessoa(s)' → commit`, tudo na transação de quem marca. Um único registro de histórico e um de auditoria cobrem marcar + avisar. O produtor não comita (contrato de `emitir`).

**Porquê.** É o regime que o módulo define para fato ainda não comitado (notificacoes_ops.py:20-21) e o único que sustenta o SC-003 (faixa e sino no mesmo ciclo): ou saem os dois, ou nenhum, e o ciclo seguinte tenta de novo. No regime B, uma falha na emissão deixaria o evento marcado sem aviso para sempre, porque a transição sem marca → marcado não se repete. `emitir` protege a marca da corrida de UNIQUE com savepoint por inserção (164-183). O sync roda em thread, sem `current_user`; o produtor não depende de request (prova: notificar_convite_recusado, 242-248). O retorno inteiro de `emitir` alimenta o texto do histórico sem segunda consulta.

**Alternativas rejeitadas.** (1) Regime B (marca comitada, aviso depois em transação curta com try/except): rejeitado — aviso perdido não tem retentativa. (2) Dois registros de histórico (um 'marcou', outro 'avisou'): rejeitado — duas linhas para um fato só, na mesma hora. (3) Emitir no fim do ciclo, em lote: rejeitado — `run_calendar_sync` engole o erro de cada mês (sync.py:83-85) e um lote no fim perderia o vínculo transacional com cada marca.

**Contrato.** Ordem dentro da função de marcar (frente da trava): 1) UPDATE condicional da marca; 2) se ganhou, `n = notificacoes_ops.notificar_evento_sumiu_google(ev, marcado_em=<valor gravado>, venda=..., recebido=..., escalados=...)`; 3) `EventLog(actor_name="Sistema", message="Sumiu do Google Agenda — mantido no sistema. Preso: <venda, recebido, escalados, contrato, grupo>. Aviso enviado a n pessoa(s) (Superadmin e Comercial).")` e `_log_sync("sumiu_google", ev, details=<mesmo texto>)`; 4) commit. A função de marcar aceita `avisar: bool = True`: com False, pula o passo 2 e o histórico diz 'sem aviso no sino' (é o gancho da regra 'primeira rodada sem sino' que a spec prevê).

**Pontos de toque.**
- app/calendar/routes.py:341-390 (_cleanup_stale_events: o ponto do fato; a marca e a chamada do produtor entram no lugar do _delete_event para evento com dinheiro)
- app/calendar/routes.py:393-414 (_log_sync → AuditLog, sem commit)
- app/models.py:568-581 (EventLog)
- app/calendar/sync.py:74-85 (loop por mês sem rollback)
- app/__init__.py:245-255 (ciclo de 600 s — o 'mesmo ciclo' do SC-003)

**Riscos.**
- `run_calendar_sync` captura a exceção do mês sem `rollback()` (sync.py:83-85): um erro na marca ou na emissão deixa a sessão inválida e derruba os meses seguintes do ciclo. A frente da trava precisa do rollback no except; este desenho depende disso.
- Se a exceção da emissão escapar num caminho em que o evento seria apagado depois, o evento não pode cair no `_delete_event`: a ordem é decidir 'tem dinheiro' antes e nunca apagar no except.
- Primeiro 'Limpar eventos fantasma' depois do deploy pode marcar dezenas de uma vez (admin_config_write.py:92-106): dezenas de avisos urgentes por pessoa. O plan conta antes (só leitura) e, se forem muitos, essa rodada roda com `avisar=False`.

**Verify.** Cenário 1: depois do sync, por conexão separada, a marca, a linha de `event_logs` e a de `audit_logs` (action `sumiu_google`) existem junto das notificações — tudo ou nada. Cenário 13 (consulta ao Google falha): zero notificações novas. Prova por mutação: forçar o produtor a levantar exceção (stub) e conferir que a marca NÃO ficou gravada e o evento NÃO foi apagado.

**Revisão adversarial: parcial.** 1) 'Tudo ou nada' não se sustenta só por estar na mesma transação. Se o produtor levantar exceção que não é de banco depois do UPDATE da marca, ela sobe até `run_calendar_sync`, que captura sem rollback; o `sync_events` do mês seguinte comita a sessão e persiste a marca SEM aviso e SEM histórico, junto com exclusões pendentes do mês que falhou. O mesmo vale para os outros dois chamadores. A prova por mutação proposta passaria verde chamando só `_cleanup_stale_events` e erraria em produção. 2) 'commit' dentro da função de marcar contradiz o regime do próprio módulo para rotina de fundo (quem comita é a rodada) e expira todos os objetos do laço. 3) O histórico converte `EventLog.created_at` naive de UTC para São Paulo; se o EventLog receber o carimbo `now_sp` da marca (como o cancel_ops faz), aparece 3 h antes. 4) `avisar: bool` não tem caminho: os três chamadores chamam `_cleanup_stale_events(items, y, m)` sem esse argumento. E a 'primeira rodada sem sino' é regra que a spec condiciona a uma contagem e a uma decisão do dono ainda não tomada.

**Emenda.** 1) Envolver cada evento em `with db.session.begin_nested():` (UPDATE condicional → produtor → EventLog → _log_sync); no except, logar e seguir para o próximo evento. Cobre os três chamadores sem tocar cada except; o rollback em sync.py:83-85 fica como higiene, não como pré-requisito. 2) Commit uma vez no fim do mês, como hoje, trocando `if removed_titles` por 'houve exclusão ou marca'. 3) EventLog sem `created_at` explícito (default utcnow); o carimbo SP fica só na coluna da marca e na dedupe_key. 4) Tirar `avisar` do desenho até o plan contar no espelho; se a contagem pedir, levar a pergunta ao dono e só então definir quem passa o parâmetro. 5) Verify: a mutação roda via `run_calendar_sync` com dois meses ou mais (Google substituído), conferindo por conexão separada depois do ciclo inteiro.

**Evidência da revisão.** app/calendar/sync.py:74-85; app/calendar/routes.py:163, 2352, 2358, 2406 (commits no meio do ciclo), 385-388, 470-476; app/api/admin_config_write.py:101-108; app/notificacoes/notificacoes_ops.py:26; app/api/agenda_read.py:210-214; app/calendar/cancel_ops.py:202-212; spec.md:388-392

## A5 — O que acontece com o aviso do sino quando o evento é resolvido (reaparece, é devolvido ao Google, é cancelado) ou apagado?

**Decisão.** O aviso some sozinho: em toda saída da marca, a mesma transação chama `marcar_lidas_por_entidade("calendar_event", event.id, KIND_EVENTO_SUMIU_GOOGLE)`. Se o evento for apagado de verdade, `_delete_event` chama `apagar_por_entidade("calendar_event", event.id)`. Abrir a tela do evento NÃO marca como lida (o GET do detalhe continua sem escrita).

**Porquê.** As duas funções já existem e são usadas exatamente assim pelos formulários (notificacoes_ops.py:362-378 e 400-407; destino_ops.py:176-177; formularios_ops.py:500-501, 575). Um aviso urgente não lido sobre evento já resolvido é ruído, e a faixa some sozinha — o sino tem de acompanhar. Marcar como lida (e não apagar) preserva o histórico em `/notificacoes`. Um satélite marcado sem nada próprio ainda cai em 'excluir' pela regra da 224 (cancel_ops.py:57-74), então existe caminho em que o evento marcado é apagado e o link ficaria morto.

**Alternativas rejeitadas.** (1) Deixar o aviso não lido até a pessoa clicar: rejeitado — o badge ficaria aceso por um problema que não existe mais. (2) Marcar como lida para o usuário ao abrir o evento por qualquer caminho (`marcar_lidas_por_objeto`, como formularios_admin_read.py:140): rejeitado — põe um UPDATE no GET mais usado do sistema (agenda.py:131-139); a resolução já limpa para todos. (3) Apagar a notificação na resolução: rejeitado — perde o rastro da caixa.

**Contrato.** Chamadas, sempre sem commit próprio: `notificacoes_ops.marcar_lidas_por_entidade("calendar_event", event.id, notificacoes_ops.KIND_EVENTO_SUMIU_GOOGLE)` em desmarcar (reapareceu), devolver ao Google e cancelar; `notificacoes_ops.apagar_por_entidade("calendar_event", event.id)` em `_delete_event`.

**Pontos de toque.**
- app/notificacoes/notificacoes_ops.py:362-378 (marcar_lidas_por_entidade) e 400-407 (apagar_por_entidade), sem mudança
- app/calendar/routes.py:305-338 (_delete_event: +1 chamada a apagar_por_entidade)
- função de desmarcar da frente da trava (reaparecimento e devolver ao Google)
- app/calendar/cancel_ops.py (cancelar_evento: +1 chamada na mesma transação)
- frontend/apps/internal/src/lib/eventOps.ts:73-78 e 141-148 (onSuccess de excluir e cancelar: invalidar `["notificacoes"]` via invalidarNotificacoes, notificacoes.ts:54-56)

**Riscos.**
- `apagar_por_entidade` filtra só por entidade (sem kind): hoje nenhum outro kind usa `calendar_event`, então só apaga o que é da 303. Kind futuro com a mesma entidade passa a ser apagado junto — o que é o certo quando o evento deixa de existir.
- `_delete_event` mora em routes.py (exceção histórica): a mudança é uma linha com import tardio; nada é movido.

**Verify.** Cenário 9 (reapareceu), 10 (devolvido) e 12 (cancelado): por conexão separada, todas as linhas do kind para aquele evento ficam com `read_at` preenchido e `GET /api/notificacoes/nao-lidas` do Superadmin cai. Evento marcado e depois excluído (satélite sem nada próprio): zero linhas do kind para o id.

**Revisão adversarial: sim.** As duas funções existem e são usadas exatamente assim; não há outro kind com entidade `calendar_event`. `_delete_event` tem só dois chamadores (limpeza do sync e exclusão manual), então uma linha cobre os dois. Falta uma invalidação: o 'Limpar eventos fantasma' marca eventos e hoje só invalida `admin-sync-status`, então o Superadmin que acabou de clicar fica até 60 s sem faixa nem badge.

**Emenda.** Manter. Acrescentar `invalidarSumidosGoogle` + `invalidarNotificacoes` no `onSuccess` de `useRunSync`. Em `cancelar_evento`, a chamada de marcar-lidas é incondicional (UPDATE filtrado por kind é no-op quando não há aviso) e fica antes do commit que já existe. No 'devolver ao Google', só depois de o Google aceitar.

**Evidência da revisão.** app/notificacoes/notificacoes_ops.py:362-378, 400-407; app/formularios/destino_ops.py:176; formularios_ops.py:500, 575; app/calendar/routes.py:305-338, 385, 4232; app/calendar/cancel_ops.py:288-313; frontend/apps/internal/src/lib/eventOps.ts:73-78, 141-148; lib/adminConfig.ts:131-142

## B1 — Qual é o caminho do endpoint da faixa e em que módulo de app/api ele entra?

**Decisão.** `GET /api/events/sumidos-google`, em `app/api/agenda.py` (módulo de leitura da Agenda/Eventos, já importado em `app/api/__init__.py:14`). O núcleo é uma função pura `faixa_sumidos()` no módulo de ops da marca em `app/calendar/` (o mesmo arquivo onde a frente da trava puser marcar/desmarcar; se ela não criar um, `app/calendar/sumico_ops.py`).

**Porquê.** O guard do revendedor EducaManto devolve 403 para todo `/api/*` fora de `/api/auth`, `/api/agenda`, `/api/events` e `/api/educamanto` (app/__init__.py:55, 738-751), e a spec pede faixa vazia sem erro para os outros papéis — o caminho tem de morar num desses prefixos. Palavra fixa depois de `/events/` não colide com `<int:event_id>`; há precedentes (`/events/cancelamentos` em agenda_write.py:609, `/events/new/options` em agenda.py:142). Entrar em módulo existente dispensa o registro em `__init__.py`, que é o esquecimento que não acusa erro. A view só faz RBAC e serializa (Princípio III); `calendar` já tem núcleos puros fora de routes.py (cancel_ops, event_ops, casting_ops).

**Alternativas rejeitadas.** (1) `/api/faixa` ou `/api/notificacoes/faixa`: rejeitado — o revendedor puro levaria 403 do guard. (2) Pendurar em `/api/notificacoes/nao-lidas`: rejeitado — o contrato do endpoint é 'COUNT sem join, a consulta mais barata do sistema' (notificacoes_read.py:20-28; notificacoes_ops.py:295-297) e a caixa é da pessoa, não do papel. (3) Campo em `/api/auth/me`: rejeitado — `useCurrentUser` não faz polling (useAuth.ts:28-40; staleTime 30 s e foco desligado em queryClient.ts:39-40), a faixa não apareceria no ciclo nem sumiria sozinha. (4) Módulo novo `app/api/sumico_read.py`: rejeitado — uma rota só, e exige registro.

**Contrato.** `GET /api/events/sumidos-google` — `@api_login_required`; 401 sem sessão (envelope de `json_error`); 200 sempre para quem tem sessão. Corpo em B2. Sem parâmetros de query.

**Pontos de toque.**
- app/api/agenda.py:1-22 (docstring ganha a linha `RBAC:`; imports) e rota nova depois de 140
- app/__init__.py:55 e 738-751 (guard do revendedor — sem mudança, é a restrição)
- app/api/__init__.py:14 (agenda já registrado — sem mudança)
- app/calendar/<ops da marca>.py (função faixa_sumidos)
- docs/01_SISTEMA_E_BANCO.md §4.3 (linha nova na tabela de gates) e bloco de contratos perto da linha 1233

**Riscos.**
- Na janela de deploy (backend e frontend sobem separados), o bundle novo contra o backend antigo recebe 404 nessa rota: a faixa fica oculta e o poll segue a cada 60 s até o backend subir. Não quebra nada, mas a ordem ideal é backend primeiro.
- `/api/events/sumidos-google` passa a ser mais uma palavra reservada sob `/events/` — registrar em docs/01.

**Verify.** Sem sessão → 401 JSON. Usuário só REVENDEDOR_EDUCAMANTO → 200 com faixa vazia (não 403): prova que o caminho atravessa o guard. `GET /api/events/123` continua respondendo o detalhe (a rota nova não engole a dinâmica).

**Revisão adversarial: sim.** Não consegui refutar. O guard do revendedor libera `/api/events/...`; as únicas rotas com segmento fixo sob `/events/` são `new/options`, `new/prefill` e `cancelamentos`, e todas as dinâmicas usam `<int:...>`, então não há colisão. `agenda.py` já está registrado e já importa `session`. Só o docstring do módulo diz `/api/agenda*` e não tem linha `RBAC:`.

**Emenda.** Manter. Atualizar o docstring de `agenda.py` (escopo + linha `RBAC:`) e registrar em docs/01 §4.3 que `sumidos-google` é palavra reservada sob `/events/`.

**Evidência da revisão.** app/__init__.py:55, 747-751; app/api/agenda.py:1-5, 10, 142, 155; app/api/agenda_write.py:609; constituição XIII (linhas 216-222)

## B2 — Qual é o payload do endpoint e como a consulta fica barata com poll de 60 s?

**Decisão.** Corpo: `{pode_ver, total, limit, items: [{id, title, start_at}]}`. `total` é a contagem exata de eventos marcados e NÃO cancelados; `items` traz no máximo `FAIXA_LIMITE = 20`, ordenados por urgência (futuros por data crescente; depois os passados, do mais recente ao mais antigo; sem data por último). Uma única consulta de três colunas, sem join, sem ORM de objeto: busca todos os marcados, ordena em Python e corta. Índice parcial na coluna da marca, declarado no modelo E na migration da 303.

**Porquê.** A faixa precisa de quantidade + id, título e data (FR-009) — nada de dinheiro, então o mesmo corpo serve a Superadmin e Comercial. A FR-033 manda não contar cancelado: o filtro `cancelled_at IS NULL` fica na consulta mesmo que o cancelamento zere a marca. Marcados são poucos por natureza (5 sumiços em dois meses, cada um resolvido em dias), então trazer todos e ordenar em Python dispensa COUNT separado e expressão `CASE` no ORDER BY; o limite protege o payload e o DOM no cenário de enxurrada. Urgência primeiro porque o elenco do evento de sábado está esperando; evento passado é o menos urgente. `start_at` em ISO naive São Paulo, como `serialize_event_summary` (agenda_read.py:82).

**Alternativas rejeitadas.** (1) Reusar `serialize_event_summary` nos itens: rejeitado — arrasta characters, location, grupo e a futura 'situação' sem uso e acopla a faixa ao contrato da agenda. (2) COUNT + SELECT com LIMIT e ORDER BY em SQL: rejeitado — duas consultas e um CASE para um conjunto de um dígito. (3) Sem índice (seq scan em ~1,3 mil linhas): funcionaria hoje, mas a consulta roda por aba por minuto e a tabela só cresce; o índice parcial custa uma linha. (4) Incluir venda/recebido nos itens: rejeitado — transforma a consulta em join e põe dinheiro num endpoint de shell.

**Contrato.** ```python
FAIXA_LIMITE = 20

def faixa_sumidos(limite: int = FAIXA_LIMITE) -> dict[str, Any]:
    """{"total": int, "limit": int, "items": [{"id", "title", "start_at"}]} — marcados e não cancelados."""
```
Filtro: `<marca> IS NOT NULL AND cancelled_at IS NULL`. Resposta 200 de quem vê: `{"pode_ver": true, "total": 2, "limit": 20, "items": [{"id": 1244, "title": "(R&I) GABBY + PANDY + GATUNO", "start_at": "2026-09-19T15:00:00"}, ...]}`. Resposta 200 de quem não vê: `{"pode_ver": false, "total": 0, "limit": 20, "items": []}`. Índice: `ix_calendar_events_google_missing ON calendar_events (id) WHERE <marca> IS NOT NULL`. TypeScript (arquivo novo `lib/sumidosGoogle.ts`): `interface SumidoGoogle { id: number; title: string; start_at: string | null }` e `interface FaixaSumidos { pode_ver: boolean; total: number; limit: number; items: SumidoGoogle[] }`; o componente lê com `data?.total ?? 0` e `data?.items ?? []`.

**Pontos de toque.**
- app/calendar/<ops da marca>.py (faixa_sumidos, FAIXA_LIMITE)
- app/models.py:238-241 (__table_args__ de CalendarEvent: índice parcial com postgresql_where e sqlite_where, como models.py:624-628)
- migration da 303 (escrita à mão, aditiva): coluna da marca + `op.create_index(..., postgresql_where=...)`
- app/api/agenda.py (serialização na view)

**Riscos.**
- Índice parcial declarado só na migration vira drift: um autogenerate futuro proporia drop (aviso em models.py:616-617). Declarar nos dois lugares.
- Se a frente da trava decidir que a marca NÃO é zerada no cancelamento (para guardar rastro), o filtro `cancelled_at IS NULL` é o que sustenta a FR-033; não remover.
- Enxurrada (primeiro 'Limpar eventos fantasma'): com mais de 20 marcados, os passados mais antigos ficam fora da lista até os primeiros serem resolvidos; o `total` continua exato.

**Verify.** Cenário 17: Superadmin e Comercial com 1 marcado → `total == 1` e o item com id, título e `start_at` iguais aos do banco; depois de resolvido → `total == 0`, `items == []`. Cenário 37: evento marcado e depois cancelado não conta. Chamar `faixa_sumidos(limite=1)` com dois marcados → `total == 2`, `len(items) == 1`, e o item é o de data futura mais próxima. Conferir que a resposta não tem nenhuma chave de dinheiro.

**Revisão adversarial: parcial.** 1) O teto de 20 contradiz a FR-009, que pede 'o acesso a cada um'. Na enxurrada, os passados mais antigos ficam fora da lista e, como evento passado pode não ter saída boa (lacuna 5), 'aparecem conforme estes forem resolvidos' pode significar nunca. O painel da decisão D já rola (`max-h-[60vh]`), então o teto não protege o DOM. 2) 'Marcado e não cancelado' fica definido aqui e de novo na situação única da FR-033 (outra frente): duas cópias do mesmo predicado. 3) 'Futuro' não diz contra qual relógio nem se o evento de hoje mais cedo conta. 4) O índice parcial é inofensivo, mas não é necessário para ~1,3 mil linhas.

**Emenda.** 1) Subir o teto para um valor que só corta em caso patológico (ex.: 100), mantendo `total` exato e o rodapé; ou sem teto, já que são três colunas. 2) O predicado vira uma expressão única no módulo de ops da marca, usada por `faixa_sumidos`, pela situação da FR-033 e pela conferência por id da FR-006. 3) Ordenar por dia: `start_at.date() >= now_sp().date()` é futuro. 4) Se o índice ficar, declarar no modelo e na migration, como proposto.

**Evidência da revisão.** spec.md:460-463 (FR-009), 562-564 (FR-033); scratchpad 02-lacunas.json:23-26; app/models.py:238-241, 616-628; app/api/agenda_read.py:82

## B3 — Qual é o RBAC do endpoint e o que os outros papéis recebem?

**Decisão.** Gate por função no início da view: `_ve_faixa_sumidos()` = SUPERADMIN ou COMERCIAL pelo papel EFETIVO, lido de `_role_flags(current_user, session.get("impersonate_role"))` (`is_superadmin` ou `is_comercial`). Quem não passa recebe 200 com a faixa vazia e `pode_ver: false` — nunca 403. O campo `pode_ver` é a única fonte de RBAC para o front: ele decide se a aba continua consultando.

**Porquê.** A spec fixa: leitura para SUPERADMIN e COMERCIAL; outros papéis recebem vazio, sem erro. `_role_flags` já é a fonte das flags por papel do domínio da agenda e já tem as duas chaves (agenda_read.py:149-177), então não nasce predicado novo. `pode_ver` no corpo cumpre o Princípio XIII (o frontend não decide RBAC): sem ele, ou o React repetiria a regra de papéis para desligar o poll, ou toda aba de todo papel consultaria a cada minuto para sempre.

**Alternativas rejeitadas.** (1) 403 para os outros papéis: rejeitado pela spec (e viraria erro no console a cada poll). (2) O front decide `enabled` pelos papéis de `/api/auth/me`, como a navegação faz (navigation.tsx:68-76): rejeitado — duplica a regra em dois lugares e diverge no dia em que o servidor mudar. (3) Poll para todo mundo sem `pode_ver`: rejeitado — requisição por minuto por aba para Figurino, Casting, Ensaio e revendedor, sem nunca haver o que mostrar. (4) Gate pelos papéis reais (`current_user.roles`), como `_can_delete` (agenda_write.py:83-87): rejeitado — ver a decisão E.

**Contrato.** ```python
def _ve_faixa_sumidos() -> bool:
    """RBAC da faixa (303): SUPERADMIN ou COMERCIAL pelo papel efetivo (respeita o "Ver como")."""
    flags = _role_flags(current_user, session.get("impersonate_role"))
    return flags["is_superadmin"] or flags["is_comercial"]
```
View: se não passa, `jsonify({"pode_ver": False, "total": 0, "limit": FAIXA_LIMITE, "items": []})` sem tocar no banco; se passa, `jsonify({"pode_ver": True, **faixa_sumidos()})`. Docstring do módulo ganha a linha `RBAC:` com essa regra.

**Pontos de toque.**
- app/api/agenda.py:14-19 (importar `_role_flags` de agenda_read) e a função `_ve_faixa_sumidos` + a view
- app/api/agenda_read.py:149-177 (_role_flags — sem mudança)
- docs/01_SISTEMA_E_BANCO.md §4.3

**Riscos.**
- `_role_flags` é nome privado importado de outro módulo; renomear quebra a rota em silêncio. Os dois módulos são do mesmo domínio e já se importam (agenda.py:14-19).
- FINANCEIRO não vê a faixa (decisão da spec), embora passe a ler a página de Cancelamentos.

**Verify.** Cenário 17 com usuários descartáveis REAIS (login por POST /api/auth/login): SUPERADMIN → `pode_ver true, total 1`; COMERCIAL → idem; FIGURINO → 200, `pode_ver false, total 0, items []` (é o cenário que deve 'falhar': com evento marcado no banco, a resposta não pode trazê-lo); FINANCEIRO → vazio; só-REVENDEDOR → 200 vazio. Prova por mutação: trocar o gate por `True` faz o cenário do Figurino acusar.

**Revisão adversarial: sim.** Não consegui refutar. `_role_flags` tem as duas chaves e ignora `impersonate_role` de quem não é Superadmin real. Responder 200 vazio cumpre a spec, e `pode_ver` no corpo cumpre 'o frontend nunca decide RBAC'. Existe um predicado mais direto no mesmo pacote (`_effective_has_role`), que evita montar um dicionário de 14 chaves a cada poll; é preferência, não defeito.

**Emenda.** Manter. Opcional: `_effective_has_role(current_user, impersonate, RoleName.SUPERADMIN/COMERCIAL)` no lugar de `_role_flags`. Como o endpoint é novo, os tipos TS podem ser obrigatórios desde que o componente leia com `data?.` (já previsto).

**Evidência da revisão.** app/api/agenda_read.py:149-177; app/api/dashboard_service.py:358-366; spec.md:642-643; constituição XIII (linhas 223-225)

## C1 — Onde a faixa monta no frontend interno e como ela é 'fixa' sem brigar com o cabeçalho do mobile e com as camadas do app?

**Decisão.** Componente novo `FaixaSumidosGoogle` (em `apps/internal/src/components/`), montado em `AppShell.tsx` como irmão ANTES do `<Outlet />`, dentro do `AppLayout` — sem tocar no `@manto/ui`. É `sticky`, de altura fixa `h-10` (40 px), uma linha só: `top-14` abaixo de `lg` (logo sob a barra do app, que tem `h-14`) e `lg:top-0` no desktop. Camada `z-[25]`. Cores de alerta sólido: `bg-red text-on-color`, com ícone `AlertTriangle`.

**Porquê.** O dono decidiu 'faixa fixa no topo de todas as telas' (D21, docs/PLANO_BACKLOG_SETEMBRO.md:98) e a História 2 é 'a equipe não tem como não ver'. O app não tem ScrollRestoration nem `scrollTo` na troca de rota, então uma faixa em fluxo normal ficaria fora da tela ao navegar a partir de uma página rolada. Todas as rotas autenticadas passam por um layout só (App.tsx:88-168; AppShell.tsx:151-166) e os filhos do `AppLayout` caem num `<main>` sem overflow (app-layout.tsx:245), então o sticky vale pela página inteira e a faixa não remonta na navegação. Altura fixa é o que permite compensar o offset por classe, sem `style` inline (Princípio II). `z-[25]` fica estritamente entre a régua de abas do evento (`z-20`, EventDetailPage.tsx:242) e a camada de popover/barra do app (`z-30`: app-layout.tsx:194, NotificacoesPanel.tsx:68, KebabMenu.tsx:26-37): em `z-20` a régua venceria o empate por vir depois no DOM (a armadilha descrita em KebabMenu.tsx:26-30); em `z-30` a faixa cobriria o painel do sino no mobile. Vermelho sólido distingue o alerta global dos avisos suaves de página (`bg-red-soft` do cancelado, `bg-gold-soft` da exclusão solicitada, EventHeader.tsx:365, 379); o par `bg-red` + tinta `on-color` já é o do botão destrutivo (confirm-dialog.tsx:64; theme.css:56, 67, 161, 169).

**Alternativas rejeitadas.** (1) Faixa em fluxo normal (não sticky): rejeitada — some ao rolar e ao navegar; contraria 'fixa'. (2) Slot novo de banner no `AppLayout` do `@manto/ui`: rejeitado — muda pacote compartilhado para um único consumidor; o filho antes do Outlet resolve. (3) Altura livre com variável CSS `--faixa-h` escrita por `style`: rejeitado — estilo inline é proibido e a altura variável obrigaria a medir o DOM. (4) `bg-red-soft`/`bg-gold-soft`: rejeitado — igual aos avisos de página e, no dourado, translúcido (não serve para sticky com conteúdo passando por baixo). (5) Pôr a faixa também no Jinja legado: rejeitado — as telas antigas não são alcançáveis pelo endereço público (frontend/server.js:253-264 não as lista) e código velho não se mexe de passagem.

**Contrato.** Raiz: `sticky top-14 z-[25] h-10 lg:top-0 bg-red text-on-color` + `relative` implícito do sticky para ancorar a lista. Texto: `1 evento sumiu do Google Agenda` / `N eventos sumiram do Google Agenda` (neutro, sem 'com venda'). Com 1 evento: link direto para `/events/<id>`, com título e data visíveis a partir de `sm` e no `aria-label` sempre. Com mais de 1: botão 'Ver eventos' que abre a lista (decisão D). Sem botão de dispensar. Não renderiza nada quando `pode_ver` é falso ou `total` é 0.

**Pontos de toque.**
- frontend/apps/internal/src/components/AppShell.tsx:164-166 (montagem: `<FaixaSumidosGoogle />` antes de `<Outlet />`)
- frontend/apps/internal/src/components/FaixaSumidosGoogle.tsx (novo)
- frontend/packages/ui/src/components/app-layout.tsx:194 e 245 (barra do mobile `sticky top-0 z-30 h-14`; `<main>` — sem mudança)
- frontend/apps/internal/src/components/KebabMenu.tsx:26-37 (regra das camadas — sem mudança)
- docs/02_MAPA_DE_PAGINAS_E_UX.md (faixa global) e docs/04 (regra: sticky de página soma a altura da faixa)

**Riscos.**
- No mobile a faixa soma 40 px aos 56 px da barra: 96 px de cromo fixo (12% de 812 px). É o preço do 'não tem como não ver' e só existe enquanto houver evento marcado.
- `z-[25]` é valor arbitrário entre dois degraus do app; precisa de comentário apontando para a regra do KebabMenu, senão alguém 'arruma' para z-20 ou z-30.
- Em 375 px o título do evento não cabe na linha com 1 evento; ele fica no `aria-label` e o toque leva direto ao evento. Conferir na tela.

**Verify.** Conferência de tela (skill manto-conferir-tela), não verify: como Superadmin e como Comercial, a faixa em duas telas quaisquer, no topo, continuando visível ao rolar e depois de navegar a partir de uma página rolada; como Figurino, ausente. Em 375×812: faixa logo abaixo da barra do app, sem rolagem horizontal; abrir o sino — o painel cobre a faixa, não o contrário. Abrir um diálogo: a faixa fica por baixo. Tema escuro: contraste do texto sobre o vermelho.

**Revisão adversarial: sim.** A montagem e as camadas conferem. `<main>` não tem overflow; a barra do mobile é `sticky top-0 z-30 h-14`; o painel do sino mora dentro do header (z-30) no mobile e dentro da sidebar (z-40) no desktop, então cobre a faixa; diálogos são z-50. Não há ScrollRestoration nem `scrollTo` no app. Contraste do par `bg-red` + `on-color`, calculado dos tokens: cerca de 5,4:1 no claro e 6,7:1 no escuro. Dois reparos: não existe nenhum `z-[N]` arbitrário no app hoje (a faixa inaugura um degrau), e em 375 px a frase de dois dígitos + ícone + 'Ver eventos' fica no limite da largura com altura fixa de uma linha.

**Emenda.** Manter. Frase com `truncate min-w-0` e rótulo curto do botão abaixo de `sm` ('Ver'), para a linha única nunca quebrar. Atualizar os comentários que descrevem a régua de camadas (KebabMenu.tsx:26-35 e NotificacoesPanel.tsx:25-26) com o degrau novo, além do comentário no componente.

**Evidência da revisão.** frontend/packages/ui/src/components/app-layout.tsx:189, 194, 245; AppShell.tsx:151-166; App.tsx:88-168; NotificacoesPanel.tsx:68; Modal.tsx:34; packages/ui/src/theme.css:56, 67, 161, 169; busca por `z-\[\d+\]` em apps/internal e packages/ui sem resultado

## C2 — Como o hook TanStack busca a faixa sem pesar em toda tela e sem o front decidir RBAC?

**Decisão.** Hook `useSumidosGoogle()` em `lib/sumidosGoogle.ts`: chave `["sumidos-google", <id do usuário>]`, `refetchInterval` em função do dado — 60 s (o `POLL_MS` de `lib/notificacoes.ts`) enquanto o servidor não disser `pode_ver: false`, e desligado quando disser. `refetchIntervalInBackground: false`, `refetchOnWindowFocus` ligado só para quem vê, `retry: false`. Helper `invalidarSumidosGoogle(queryClient)` chamado no sucesso de cancelar, excluir e devolver ao Google.

**Porquê.** Cada usuário faz UMA requisição ao montar o shell; só Superadmin e Comercial seguem consultando. Aba esquecida não consulta. É o mesmo desenho do sino, que é o único polling do app e justifica as exceções ao QueryClient padrão (notificacoes.ts:58-80; queryClient.ts:31-42). 60 s contra um ciclo de sync de 600 s (app/__init__.py:245) é folga de sobra. O id do usuário na chave impede que a faixa de quem saiu apareça para quem entrou no mesmo navegador (o logout só zera `ME_KEY`, useAuth.ts:58-66). O 'Ver como' já invalida todas as queries (useAuth.ts:73-97), então `pode_ver` é reavaliado na hora. Em erro transitório o TanStack mantém o último dado: a faixa não pisca. A invalidação explícita faz a faixa sumir no clique de quem resolveu, sem esperar o poll.

**Alternativas rejeitadas.** (1) Pendurar em `useNaoLidas`: rejeitado (contrato do endpoint, ver B1). (2) `enabled` calculado pelos papéis no front: rejeitado (ver B3). (3) Poll fixo para todos: rejeitado (peso sem retorno). (4) Intervalo de 10 min igual ao sync: rejeitado — a faixa demoraria a sumir em outras abas depois da decisão. (5) Chave sem o usuário, como `NAO_LIDAS_KEY`: rejeitada — vaza o estado entre logins no mesmo navegador por até um ciclo.

**Contrato.** ```ts
export function useSumidosGoogle(): UseQueryResult<FaixaSumidos>
// queryKey: ["sumidos-google", user.id]; queryFn: apiFetch("/api/events/sumidos-google")
// enabled: Boolean(user)
// refetchInterval: (q) => (q.state.data?.pode_ver === false ? false : POLL_MS)
// refetchIntervalInBackground: false
// refetchOnWindowFocus: (q) => q.state.data?.pode_ver !== false
// retry: false
export function useFaixaSumidosVisivel(): boolean   // select: pode_ver && total > 0
export function invalidarSumidosGoogle(queryClient: QueryClient): void  // prefixo ["sumidos-google"]
```

**Pontos de toque.**
- frontend/apps/internal/src/lib/sumidosGoogle.ts (novo: tipos, hooks, invalidarSumidosGoogle)
- frontend/apps/internal/src/lib/notificacoes.ts:54-59 (reusar POLL_MS e invalidarNotificacoes)
- frontend/apps/internal/src/lib/useAuth.ts:28-40, 73-97 (useCurrentUser para o id; invalidação do 'Ver como' — sem mudança)
- frontend/apps/internal/src/lib/eventOps.ts:73-78 (useDeleteEvent) e 141-148 (useCancelarEvento): acrescentar as duas invalidações
- mutation nova de 'Devolver ao Google' (outra frente): mesma dupla de invalidações
- frontend/packages/api-client/src/queryClient.ts:31-42 (padrões que o hook sobrepõe — sem mudança)

**Riscos.**
- `refetchInterval` e `refetchOnWindowFocus` como função dependem do TanStack v5 (o app está em ^5.62 — package.json do internal); conferir os tipos no typecheck.
- Depois do sync marcar, a faixa leva até 60 s para aparecer numa aba aberta. É o mesmo atraso do sino.
- Se o primeiro GET falhar (rede), o hook segue tentando a cada 60 s porque só desliga com `pode_ver === false` explícito — proposital.

**Verify.** Conferência de tela com a aba de rede aberta: como Figurino, um único GET `/api/events/sumidos-google` ao entrar e nenhum depois; como Superadmin, um GET por minuto com a aba em foco e nenhum com a aba escondida. Cancelar o evento marcado: a faixa some sem recarregar a página. `npm run typecheck` limpo.

**Revisão adversarial: parcial.** 1) `useFaixaSumidosVisivel()` é descrito como o mesmo query com `select`. No TanStack v5 cada observer com `refetchInterval` tem o próprio `setInterval` e busca sem checar frescor; observers montados em momentos diferentes (faixa no shell, hook na página do evento ou na Home) disparam GETs defasados. Resultado: 2 GETs por minuto nessas telas, e a própria conferência proposta ('um GET por minuto') falharia na tela do evento. 2) Falta a invalidação no 'Limpar eventos fantasma' (ver A5). O resto confere: o logout só zera `ME_KEY`, o 'Ver como' invalida tudo, e função em `refetchInterval`/`refetchOnWindowFocus` é válida na v5.

**Emenda.** `useFaixaSumidosVisivel` vira observer passivo: mesma chave, `enabled: false`, `select`. Assim não busca ao montar nem cria timer, e continua recebendo as atualizações do cache. Só o `useSumidosGoogle()` montado no shell faz poll. Conferência de tela: contar os GETs na página do evento, não só na agenda.

**Evidência da revisão.** frontend/node_modules/@tanstack/query-core/build/modern/queryObserver.js:177-187, 208-219; frontend/apps/internal/src/lib/notificacoes.ts:58-80; lib/useAuth.ts:58-66, 73-97; packages/api-client/src/queryClient.ts:31-42; lib/adminConfig.ts:131-142

## C3 — Como a faixa sticky convive com a régua de abas do evento e com os outros pontos que dependem do topo da página?

**Decisão.** Compensação explícita por classe, lida do mesmo cache: `useFaixaSumidosVisivel()` nos dois únicos consumidores de offset do app interno. Régua de abas do evento: `top-14 lg:top-0` vira `top-24 lg:top-10` quando a faixa está visível. Âncoras da Home: `scroll-mt-16 lg:scroll-mt-4` vira `scroll-mt-28 lg:scroll-mt-14`.

**Porquê.** Varredura do app interno: só existem dois usos de offset de topo — a régua `sticky top-14 z-20 ... lg:top-0` (EventDetailPage.tsx:242) e o `scroll-mt` das seções da Home (DashboardPage.tsx:1002); o sticky de Modal.tsx:56 vive dentro do próprio contêiner com rolagem e não é afetado, e nenhuma tela usa altura de viewport. Sem a compensação, a faixa (40 px no topo) cobriria a régua de abas ao rolar — as abas ficariam inacessíveis justamente na tela em que o Superadmin decide. Com altura fixa, a soma é constante e cabe em classes que o Tailwind 3.4 já tem (3,5 rem + 2,5 rem = `top-24`; 2,5 rem = `top-10`). O hook com `select` só re-renderiza a página quando o booleano muda, não a cada poll.

**Alternativas rejeitadas.** (1) Variável CSS no `documentElement` escrita por efeito: rejeitada — estilo imperativo, contra o Princípio II. (2) `group-data-[faixa=on]` num wrapper do shell: rejeitada — funciona, mas esconde a dependência numa classe longa que ninguém acha por busca; o hook é tipado e explícito. (3) Tirar o sticky da régua quando há faixa: rejeitado — regressão da 215 (trocar de aba sem voltar ao topo). (4) Deixar a Home como está: rejeitado — 'ir para a seção' pararia com o título escondido sob a faixa.

**Contrato.** EventDetailPage: `cn("sticky z-20 -mx-4 mb-4 overflow-x-auto bg-surface/95 px-4 py-2 backdrop-blur sm:mx-0 sm:px-0", faixaVisivel ? "top-24 lg:top-10" : "top-14 lg:top-0")`. DashboardPage: `className: faixaVisivel ? "scroll-mt-28 lg:scroll-mt-14" : "scroll-mt-16 lg:scroll-mt-4"`. Regra para o futuro (docs/04): todo sticky de topo em página interna soma a faixa por `useFaixaSumidosVisivel()`.

**Pontos de toque.**
- frontend/apps/internal/src/pages/EventDetailPage.tsx:237-242 (classe da régua + comentário)
- frontend/apps/internal/src/pages/DashboardPage.tsx:995-1003 (propsSecao)
- frontend/apps/internal/src/lib/sumidosGoogle.ts (useFaixaSumidosVisivel)
- frontend/apps/internal/src/components/Modal.tsx:56 (sticky interno — sem mudança)

**Riscos.**
- Sticky novo em outra tela que esqueça a regra fica coberto pela faixa — só aparece quando há evento marcado, ou seja, raramente e na pior hora. Por isso a regra vai para docs/04 e para um comentário no componente.
- Durante os ~200 ms de entrada/saída da faixa o offset da régua muda de uma vez; só é visível se a página estiver rolada naquele instante.

**Verify.** Conferência de tela com um evento marcado: abrir `/events/<id>`, rolar até o fim — a régua de abas fica inteira e clicável logo abaixo da faixa, em desktop e em 375 px; resolver o evento e conferir que a régua volta a colar em `top-0`/`top-14`. Na Home, clicar num atalho de seção: o título da seção aparece abaixo da faixa, não sob ela.

**Revisão adversarial: sim.** A varredura confirma: os únicos consumidores de offset de topo são a régua de abas do evento e o `scroll-mt` da Home. Os demais `scrollIntoView` usam `block: "center"`, o sticky do Modal é interno e não há sticky no `@manto/ui` além da barra do app. As somas fecham (56+40 = `top-24`; `lg:top-10`; `scroll-mt-28`/`lg:scroll-mt-14`). Depende da emenda da C2 para não duplicar o poll.

**Emenda.** Manter, com o hook passivo da C2.

**Evidência da revisão.** frontend/apps/internal/src/pages/EventDetailPage.tsx:237-242; DashboardPage.tsx:983-1003; Tags3DPage.tsx:159; EventCreatePage.tsx:381, 501; Modal.tsx:56; packages/ui/src/components/table.tsx:11

## C4 — Como a faixa atende acessibilidade, movimento reduzido e mobile?

**Decisão.** `role="alert"` só no parágrafo da frase de contagem (não no contêiner nem na lista). Ícone `AlertTriangle` com `aria-hidden`, texto sempre presente (cor não é o único sinal). Entrada e saída com `AnimatePresence` + `motion.div` animando altura 0 ↔ 40 px e opacidade em 200 ms; com `useReducedMotion()`, sem transição (`initial={false}`, sem `exit`). Lista com 250 ms no máximo, mesma regra. Sem skeleton: enquanto carrega, nada aparece.

**Porquê.** `role="alert"` anuncia quando o texto entra ou muda — é o que se quer quando um evento some ou a contagem sobe; como o shell é rota de layout, a faixa não remonta na navegação e não reanuncia a cada tela, e o poll com dado igual não mexe no DOM. Deixar a lista fora do nó de alerta evita que abrir 'Ver eventos' leia a lista inteira em voz alta. O padrão de movimento é o mesmo das faixas que já existem (AvisosFalhosBanner.tsx:46-50; SugestaoDeEventoFaixa.tsx:40-45) e do AppLayout (app-layout.tsx:148, 212-228) — Princípio XI. A faixa é um alerta: o estado normal é a ausência, então skeleton seria um tranco em toda tela para todo mundo.

**Alternativas rejeitadas.** (1) `role="alert"` no contêiner inteiro: rejeitado — reanuncia tudo a cada abertura da lista. (2) `aria-live="polite"` como o sino (NotificacoesBell.tsx:90-92): rejeitado — o sino é passivo por desenho; aqui o dono pediu o oposto. (3) Sem animação: rejeitado — 40 px entrando de uma vez empurram a página num tranco (Princípio XI). (4) Toast ou som: rejeitado — fora do pedido e o toast some.

**Contrato.** Estrutura: `<AnimatePresence>{visivel && <motion.div className="sticky ..."><AlertTriangle aria-hidden /><p role="alert">…contagem…</p>{link direto | botão 'Ver eventos' com aria-expanded e aria-controls}{lista}</motion.div>}</AnimatePresence>`. Animação: `initial={reduce ? false : {height: 0, opacity: 0}}`, `animate={{height: 40, opacity: 1}}`, `exit={reduce ? undefined : {height: 0, opacity: 0}}`, `transition={{duration: 0.2, ease: "easeOut"}}`. Data do evento por `formatShortDate(start_at)` (nunca `toISOString`). Alvos de toque do botão e dos itens da lista com pelo menos 40 px de altura.

**Pontos de toque.**
- frontend/apps/internal/src/components/FaixaSumidosGoogle.tsx (novo)
- frontend/apps/internal/src/components/AvisosFalhosBanner.tsx:46-56 e formularios/SugestaoDeEventoFaixa.tsx:40-45 (vocabulário e padrão de movimento a copiar)
- frontend/packages/ui/src/lib/date.ts:46-50 (formatShortDate para a data do evento)

**Riscos.**
- Leitores de tela anunciam a faixa de novo a cada recarga completa da página — aceitável para um alerta que exige decisão.
- Animar `height` num elemento sticky pode causar um reflow perceptível em páginas pesadas (Home); 200 ms e só na entrada/saída.

**Verify.** Conferência de tela: com `prefers-reduced-motion` emulado, a faixa aparece e some sem transição; inspecionar a árvore de acessibilidade (read_page): um nó `alert` com a frase de contagem e a lista fora dele; navegar por teclado até o botão, abrir com Enter, fechar com Esc com o foco voltando ao botão.

**Revisão adversarial: parcial.** 1) A raiz é ao mesmo tempo sticky, `h-10` e animada em altura 0↔40. Animar altura exige `overflow-hidden` (é o que a faixa existente usa), e isso recorta o painel `absolute top-full` da decisão D, que mora dentro da mesma raiz. Sem o overflow, o texto vaza durante a animação. E `h-10` por classe briga com a altura que o Framer escreve. 2) 'Enquanto carrega, nada aparece' e, em erro, também nada: a constituição V pede feedback de erro em estado assíncrono. O sino tem a mesma exceção, mas aqui o alerta é o que 'não tem como não ver'; a exceção precisa estar escrita no plano.

**Emenda.** Estrutura em dois níveis: wrapper `sticky top-14 lg:top-0 z-[25]` sem overflow (sempre montado, altura 0 quando vazio) contendo `<AnimatePresence>` com a barra `motion.div` (`overflow-hidden`, altura 0↔40, sem `h-10` na raiz animada; a linha interna tem `h-10`) e, como IRMÃO da barra, o painel da lista ancorado no wrapper. Registrar no plan a exceção ao Princípio V: primeiro GET com erro não mostra nada porque o front ainda não sabe se o papel vê a faixa; o poll de 60 s tenta de novo e, com dado em cache, o TanStack mantém a faixa.

**Evidência da revisão.** frontend/apps/internal/src/components/formularios/SugestaoDeEventoFaixa.tsx:40-45; AvisosFalhosBanner.tsx:9-11, 46-50; constituição V (linhas 95-96) e XI (linhas 192-198)

## D — Como a faixa lista vários eventos sem crescer sem limite?

**Decisão.** A barra tem sempre uma linha e 40 px. Com mais de um evento, a lista abre num painel flutuante ancorado sob a barra (`absolute top-full`, largura da área de conteúdo, `max-h-[60vh] overflow-y-auto`, `bg-panel text-ink border border-line shadow-lg`), que não empurra a página. Cada item é um link com título (truncado) e data; clicar fecha o painel. O servidor entrega no máximo 20 itens e o `total` exato; quando `total > items.length`, o rodapé do painel diz 'Mostrando 20 de N — os demais aparecem conforme estes forem resolvidos'. Fecha com Esc e clique fora.

**Porquê.** A lista em fluxo faria a altura da faixa variar e quebraria a compensação de offset da decisão C3 (e, no cenário de enxurrada, tomaria a tela). O painel flutuante mantém a barra constante e dá 'o acesso a cada um (título e data)' da FR-009 a um clique. O limite de 20 com `total` exato é honesto: nada some da contagem, e a ordem por urgência garante que os mais próximos aparecem primeiro. Volume real esperado é 0 a 2 (5 sumiços em dois meses), então o painel quase sempre terá duas linhas. O contrato de fechar em Esc e clique fora é o mesmo do sino e do KebabMenu (NotificacoesBell.tsx:43-58); não existe hook compartilhado para isso no repo, e criar um agora seria refatoração lateral.

**Alternativas rejeitadas.** (1) Listar os eventos em linha dentro da barra, quebrando em várias linhas: rejeitado — altura variável, e no mobile dois eventos já ocupariam a tela. (2) Chips com rolagem horizontal na barra: rejeitado — títulos de evento são longos (até 500 caracteres) e rolagem horizontal escondida não é 'acesso'. (3) Link 'ver todos' para a página de Cancelamentos: rejeitado — o Comercial não tem acesso a ela (agenda_write.py:609-618) e ela lista cancelados, não marcados. (4) Página nova só para os marcados: rejeitada — tela nova para um conjunto que normalmente tem um item. (5) Sem limite no servidor: rejeitado — a primeira rodada do 'Limpar eventos fantasma' pode marcar dezenas.

**Contrato.** Painel: `id` estável para `aria-controls`; `<ul>` de `<li><Link to={"/events/" + id}>{title} · {formatShortDate(start_at)}</Link></li>`; evento sem data mostra 'sem data'. Rodapé condicional: `total > items.length`. Estado aberto/fechado é `useState` local do componente (não vai para URL nem para storage: a faixa não se dispensa, e a lista fechada é o estado padrão a cada tela).

**Pontos de toque.**
- frontend/apps/internal/src/components/FaixaSumidosGoogle.tsx (novo: barra + painel)
- frontend/apps/internal/src/components/notificacoes/NotificacoesBell.tsx:43-58 e NotificacoesPanel.tsx:60-68 (contrato de fechar e classes do painel a espelhar)
- app/calendar/<ops da marca>.py (FAIXA_LIMITE = 20 e a ordenação)

**Riscos.**
- Terceira cópia do fechar-em-Esc-e-clique-fora no app (sino, kebab, faixa): dívida pequena a registrar em docs/05, não a resolver aqui.
- O painel vive na camada `z-[25]` da faixa: um menu de página (`z-30`) aberto ao mesmo tempo pintaria por cima dele — não acontece na prática porque o clique fora fecha um antes de abrir o outro.

**Verify.** Conferência de tela com dois eventos marcados: a barra diz '2 eventos sumiram do Google Agenda', continua com 40 px, o painel abre sobre o conteúdo sem empurrá-lo (inclusive sobre a régua de abas do evento), cada linha tem título e data e leva ao evento certo. No verify, a parte de limite e ordem está em B2 (`faixa_sumidos(limite=1)`).

**Revisão adversarial: sim.** O painel flutuante preserva a altura constante de que a C3 depende e dá título e data a um clique. Três reparos: o teto de 20 e o rodapé herdam o problema da B2; o painel não pode ficar dentro do elemento com `overflow-hidden` (C4); e não é a 'terceira cópia' do fechar-em-Esc-e-clique-fora — o padrão já existe em cinco arquivos. O `FilterDropdown` do `@manto/ui` não serve pronto (gatilho e painel com estilo de filtro, largura fixa e z-20), então a cópia enxuta segue o precedente do sino.

**Emenda.** Manter, com o teto e o rodapé da B2 e a estrutura da C4. Corrigir a contagem na dívida do docs/05 (sexta ocorrência do padrão, candidata a hook único em outra feature).

**Evidência da revisão.** frontend/apps/internal/src/components/notificacoes/NotificacoesBell.tsx:43-58; KebabMenu.tsx:36-37; frontend/packages/ui/src/components/filter-dropdown.tsx:29-43, 78-81; combobox.tsx e info-tip.tsx (mesmo listener de `mousedown`)

## E — O que a faixa faz quando o Superadmin está no 'Ver como' (impersonação de papel)?

**Decisão.** A faixa segue o papel EFETIVO: 'Ver como COMERCIAL' mostra a faixa; 'Ver como FIGURINO, CASTING, FINANCEIRO ou ENSAIO' recebe `pode_ver: false` e não mostra. O sino continua sendo a caixa da pessoa real e ignora o 'Ver como'. Os gates de escrita (devolver ao Google, cancelar) continuam nos papéis reais, como hoje.

**Porquê.** A faixa é uma visão por papel, como a Home e as flags do evento, que respeitam a impersonação (`_effective_has_role`, dashboard_service.py:362-366; `_role_flags`, agenda_read.py:149-160); não é uma caixa pessoal, como o sino, que a ignora de propósito (notificacoes_read.py:3-7). 'Ver como' existe para o dono conferir o que cada papel enxerga — inclusive a conferência de tela desta feature ('ausente como Figurino'). O Superadmin em 'Ver como Figurino' não fica cego: o aviso urgente segue no sino dele, e o chip do papel simulado fica visível no rodapé (AppShell.tsx:100-104). Trocar o papel já invalida todas as queries (useAuth.ts:73-97), então a faixa aparece ou some na hora, sem código extra.

**Alternativas rejeitadas.** (1) Faixa pelo papel real (Superadmin sempre vê, qualquer que seja o 'Ver como'): rejeitada — quebra o propósito do 'Ver como' e deixa a tela inconsistente (faixa mandando decidir, botões de decisão escondidos pelas flags). (2) Esconder a faixa sempre que houver impersonação: rejeitada — 'Ver como COMERCIAL' tem de mostrar o que o Comercial vê. (3) Fazer os gates de escrita também respeitarem o 'Ver como': fora do escopo — mudaria `_can_delete` (agenda_write.py:83-87) para todas as ações da 224.

**Contrato.** Sem contrato novo além de B3: `pode_ver` = papel efetivo é SUPERADMIN ou COMERCIAL. Tabela: real SUPERADMIN sem 'Ver como' → vê; 'Ver como COMERCIAL' → vê; 'Ver como' qualquer outro papel → não vê; `impersonate_role` na sessão de quem não é Superadmin real é ignorado (agenda_read.py:154-155).

**Pontos de toque.**
- app/api/agenda.py (gate `_ve_faixa_sumidos` lendo `session["impersonate_role"]`)
- app/api/agenda_read.py:149-160 (semântica da impersonação em _role_flags — sem mudança)
- app/api/auth.py:96-122 e app/constants.py:534-540 (IMPERSONABLE_ROLES: CASTING, FIGURINO, COMERCIAL, FINANCEIRO, ENSAIO — sem mudança)
- frontend/apps/internal/src/lib/useAuth.ts:73-97 (invalida tudo ao trocar de papel — sem mudança)
- app/api/notificacoes_read.py:3-7 (sino ignora o 'Ver como' — sem mudança)

**Riscos.**
- Superadmin que esquece o 'Ver como Figurino' ligado deixa de ver a faixa até voltar ao papel real; o sino (urgente, não lido) é a rede.
- Em 'Ver como COMERCIAL' a API ainda aceita devolver e cancelar (gates reais) embora a tela não mostre os botões — comportamento que já existe desde a 224; os cenários 11 e 23b do verify precisam de um COMERCIAL real, não do 'Ver como'.

**Verify.** Com o Superadmin descartável e um evento marcado: `POST /api/auth/impersonate {role: "FIGURINO"}` → GET da faixa com `pode_ver false, total 0`; `{role: "COMERCIAL"}` → `pode_ver true, total 1`; `DELETE /api/auth/impersonate` → `pode_ver true`. Na mesma sessão, `GET /api/notificacoes/nao-lidas` não muda com o 'Ver como'. Usar a mesma sessão de cookies nas três chamadas (o estado mora na sessão).

**Revisão adversarial: sim.** Não consegui refutar. Leitura por papel respeita o 'Ver como' em todo o app (Home, flags do evento, `/api/auth/me`), e a caixa do sino o ignora de propósito; a proposta segue as duas regras. Os gates de escrita continuam nos papéis reais. A spec deixou essa escolha para o plan (lacuna registrada).

**Emenda.** Manter. No verify, as chamadas de impersonação usam a mesma sessão de cookies, e os cenários 11 e 23b usam um COMERCIAL real.

**Evidência da revisão.** app/api/agenda_read.py:154-160; app/api/dashboard_service.py:362-366; app/api/auth.py:38-47, 96-122; app/api/notificacoes_read.py:3-7; app/api/agenda_write.py:83-87; scratchpad 02-lacunas.json:243-246

## O que a frente deixou de decidir (revisão)

- Atomicidade por evento nos três chamadores de `_cleanup_stale_events` (sync.py:79, admin_config_write.py:104, routes.py:475): nenhum faz rollback no except, e `sync_events`/`_mark_month_synced` comitam no meio do ciclo (routes.py:163, 2352). A frente precisa decidir o savepoint por evento; sem isso, 'marca sem aviso' acontece e o verify não vê.
- Invalidação da faixa e do sino no `useRunSync` (adminConfig.ts:131-142): o 'Limpar eventos fantasma' é justamente o caminho que marca em lote.
- Fonte única do predicado 'marcado e não cancelado', compartilhada entre a faixa, a situação da FR-033 e a conferência por id da FR-006. Hoje cada frente escreveria a sua.
- Nomes do contrato entre as frentes: a coluna da marca ('aqui chamada google_missing_at'), a função que devolve 'o que está preso' e o módulo de ops aparecem como placeholders. O plan precisa fixá-los num lugar só antes das tasks.
- Primeira rodada depois do deploy: quem conta os eventos passados com dinheiro fora do Google (só leitura, no espelho), qual é o limiar de 'muitos' e que pergunta vai ao dono (a lacuna já traz as opções A/B/C). A faixa acende com todos mesmo sem sino, e isso interage com o teto da lista.
- Convenção de relógio do rastro: `EventLog.created_at` e `AuditLog.created_at` são UTC naive e a tela converte (agenda_read.py:210-214); a marca e a notificação são `now_sp`. O contrato deve dizer qual relógio vai em cada campo, para o histórico não sair 3 h antes (o cancel_ops já grava SP no EventLog).
- Exceção ao Princípio V para o estado de erro e de carregamento da faixa: precisa estar justificada no plano, não só implícita.
- Cenário de verify para o 'Ver como' na faixa e para o ciclo de vários meses com falha no produtor. A tabela da spec (cenário 17) cobre só papéis reais.
- Docs que a faixa obriga a tocar além de docs/01 §4.3 e docs/02: a régua de camadas descrita em KebabMenu.tsx:26-35 e NotificacoesPanel.tsx:25-26, a regra de sticky em docs/04, e a contagem real de cópias do fechar-em-clique-fora no docs/05.

## Perguntas em aberto da frente
