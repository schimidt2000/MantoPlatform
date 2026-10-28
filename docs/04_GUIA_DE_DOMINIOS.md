# 04 — Guia de Domínios

> **O que este documento é:** fluxos, invariantes e armadilhas de cada domínio — o conhecimento que
> hoje só existe espalhado em comentários e na cabeça de quem escreveu. É o que você lê **depois** do
> `docs/00_MAPA_DO_SISTEMA.md` e **antes** do código.
>
> **O que ele não é:** schema (está em `docs/01` §2), inventário de endpoints (`docs/01` §3), tabela
> de gates de RBAC (`docs/01` §4.3) nem fluxo de tela (`docs/02`). Onde o 01/02 já documenta bem,
> aqui há só a referência.
>
> Origem: auditoria de leitura de 2026-08-06 sobre ~44k linhas de Python e ~46k de TypeScript.
> Última revisão: **2026-10-23** (feature 310, lote de 23/10: o pagamento da Loja
> Virtual — a máquina de estados do pedido e do aviso, a regra única `decidir_pagamento` e as
> invariantes do §4).
> Antes: **2026-10-22** (feature 315, em branch: o pedido de cancelamento antes do ato, §1 "Antes do ato").
> Antes: **2026-10-21** (feature 313, em produção desde 22/10 ~04:58: a ordem da conta do orçamento, o desconto e o PIX na linha
> "Orçamento" de §6, e o BV do evento pelo cheio nas invariantes do BV, §1). Antes: **2026-10-20** (feature 306: o fluxo de cancelar, as invariantes 18 a 26 da Agenda e
> 6 a 10 do Financeiro, e as correções no lugar da exclusão, do grupo, da cobrança, da regra de
> comissão, do estorno, da cascata da DRE e da comissão exibida). Antes: **2026-10-20** (feature 309: produtos de tabela — preço fixo fora do markup,
> vagas congeladas e teto pela tabela — na linha Orçamento do §5). Antes: **2026-10-15** (feature 307: data especial pela data do evento na linha Orçamento
> do §5 e o teto das vagas seguindo a data do evento, §3). Antes: **2026-09-30** (feature 303: fluxos de sincronização, "Sincronizar", exclusão e
> devolução ao Google; invariantes 13-17 da Agenda; invariante 6 do frontend). Antes: **2026-08-06**.

---

## 0. Os três estágios de arquitetura

Toda estranheza deste backend se explica por uma migração Jinja → API+SPA em andamento. Cada domínio
está num destes estágios — saber qual poupa meia hora de leitura:

| Estágio | Como é | Domínios |
|---|---|---|
| **3 — nasceu desacoplado** | só `*_ops.py` puro + endpoints JSON. Sem blueprint Jinja | `impressoes3d/`, `marketing/` |
| **2 — extraiu ops, manteve Jinja** | `*_ops.py` + blueprint Jinja legado + API, os três vivos | `gastos/`, `clientes/`, `revisao/`, `orcamento/`, `educamanto/`, `formularios/`, `figurino/` |
| **1 — não extraiu** | a regra ainda mora no arquivo de rotas | `financeiro/`, `talents/`, auto-vínculo de `formularios/`, parser de Drive de `figurino/` |

**Todos os blueprints Jinja continuam registrados** (`app/__init__.py:525-542`). Onde há duplicação,
não é código morto: são **duas superfícies vivas com regras diferentes**, alcançáveis batendo direto
no host do Flask.

Convenção que se repete e vale reconhecer: docstring de módulo abrindo com *"Funções puras (sem
`request`/`render_template`/`flash`)"* — 20 arquivos declaram esse contrato e o cumprem. A única
exceção é `virtuais_ops.py:28`, que importa `current_app` para ler config (aceitável — não é
`request`).

---

## 1. Agenda e Eventos

**8.228 linhas.** O domínio mais importante e o de pior distribuição de qualidade.

### Arquivos

| Arquivo | Linhas | O que é |
|---|---|---|
| `app/calendar/routes.py` | 3.910 | ⚠️ **não é um módulo de rotas** — é a camada de ops do domínio disfarçada de Blueprint |
| `app/calendar/event_ops.py` | 1.111 | núcleo de nível-evento (34 funções) |
| `app/calendar/casting_ops.py` | 306 | **padrão-ouro do repositório** — 8 funções, 100% documentadas, zero `request` |
| `app/calendar/observation_ops.py` | 84 | o upload fica no adaptador; o núcleo recebe `file_path` pronto |
| `app/calendar/service.py` | 297 | camada fina sobre a Google Calendar API — **único arquivo que fala com o Google**, zero regra de negócio |
| `app/calendar/sync.py` | 150 | moldura do sync; excelente docstring de módulo |
| `app/calendar/sumico_ops.py` | ~900 | feature 303 — a limpeza do mês (`limpar_mes`), o retrato do que prende o evento (`preso_ao_evento`), marcar e desmarcar "Sumiu do Google Agenda", a reconferência dos marcados, a faixa e a devolução ao Google; chama o Google por atributo de `service` e os helpers de `routes.py` por import tardio |
| `app/calendar/cancel_ops.py` | ~3.330 | features 224 e 306 — o cancelamento inteiro: o ato (`cancelar_evento`, nas quatro formas de `FormaDoAto`), a prévia pela mesma conta (`previa_cancelamento`), o resumo único do cancelado em lote (`resumos_cancelados`), os cancelados do período (fonte da DRE e do Comercial), o BV da Planilha, o "Alterar devolução", as correções que recongelam, a multa ao elenco e o estorno da exclusão (`aplicar_estorno_comissao`). É "folha": no topo só importa `db` e `app.models`; o resto entra por import tardio, para `sumico_ops` e `cobranca_ops` o importarem sem ciclo |
| `app/api/agenda_read.py` | 766 | fonte única do formato JSON de leitura (sem rotas) |
| `app/api/agenda_write.py` | 1.437 | 41 rotas, 56 funções, **zero sem docstring** — melhor arquivo do domínio |
| `app/api/agenda.py` | 167 | 8 rotas de leitura |

**Mapa de `routes.py` por faixa de linha** (o arquivo não tem docstring nem índice):
`63-323` helpers de mês/sync/exclusão · `325-348` **OAuth Google (as únicas 2 rotas vivas)** ·
`349-474` views `/agenda` (mortas) · `475-1583` os 23 handlers `_handle_*` + record helpers
financeiros · `1585-1610` o dict `_EVENT_ACTIONS` · `1613-1921` `event_detail` (305 l.) ·
`1922-1953` parsers de título · `1954-2148` conflito/notificação/tipo virtual · `2149-2296`
`sync_events` · `2297-2474` talentos que trabalharam, ViaCEP, Google Maps · `2475-2680` ensaio ·
`2682-2967` precificação de orçamento e opções de formulário · `2969-3492` núcleo de criação ·
`3494-3628` wrapper Jinja de criação · `3629-3910` materiais, sync/delete flows, observações.

Constantes no topo (`:46-61`): `CALENDAR_ID`, `TZ`, os conjuntos `_CAN_ENSAIO`/`_CAN_CREATE`/
`_CAN_EDIT_EVENT`/`_CAN_DELETE`, `SOUND_TECH_TALENT_ID = 42` (técnico de som padrão de SHOW) e
`PRESENCE_CHARACTER`.

### Fluxo: sincronização Google → Manto

Entradas: thread interna a cada 600s (`app/__init__.py:215` → `_claim_auto_sync`, lock atômico em
`SiteSetting.calendar_auto_sync_at` para não rodar em todos os workers gunicorn), `sync_worker.py`,
botão do admin (`app/admin/routes.py:414`, `app/api/admin_config_write.py:77`) e sync de um evento só
(`routes.py:3723`). Todas convergem em **`sync_events(items)` (`routes.py:2149`, 146 linhas, sem
docstring)**.

Para cada item, quatro caminhos:
1. **evento virtual local** → só sinaliza divergência e pula (nunca é atualizado nem apagado);
2. **não existe** → cria + `EventLog` + coordenador padrão + técnico de som se SHOW + geocode ViaCEP
   + estimativa de rota;
3. **existe** → detecta mudança de data/hora/local, sobrescreve campos, notifica talentos
   confirmados, re-garante o técnico de som;
4. depois: `source == 'platform'` → commit e **early-return preservando o elenco**; título começando
   com `🟧 ENSAIO` → **apaga todos os roles**; senão → reconcilia os personagens do título contra os
   `EventRole` existentes, renomeando com prefixo antigo para preservar casting/figurino e disparando
   `send_removal_email` para quem sumiu do título.

Ao final, `_mark_talents_worked()`. Em seguida vem a **limpeza** (`_cleanup_stale_events`, hoje uma
delegação de uma linha para `sumico_ops.limpar_mes` — feature 303), que só roda quando a lista do
mês respondeu:
1. o evento **marcado** cujo id voltou à lista perde a marca (vale o Google; a lista já foi aplicada
   por `sync_events`);
2. cada evento do mês, com id do Google e não cancelado, que faltou na lista é **conferido no
   próprio Google** (`service.consultar_evento`, três desfechos), um por um, cada um na sua
   transação: venda virtual só gera `virtual_divergente`; o **já marcado** é pulado, sem consulta;
   **inconclusivo** (sem credencial, rede,
   5xx, 403, 429…) não apaga nem marca; **presente** → se os dados mudaram (data, quase sempre),
   `sync_events([item])` leva o evento à data nova no mesmo registro, senão nada; **ausente**
   (404, 410, `status: cancelled`) → o **vazio** é apagado (auditoria `auto_deleted` com o que o
   Google respondeu e o retrato do que estava preso) e o **com dinheiro** fica e é marcado (aviso
   no sino, histórico, auditoria `sumiu_do_google`);
3. um disjuntor por mês: a primeira consulta sem resposta por rede, 5xx ou credencial encerra as
   consultas daquele mês.

Antes do laço de meses, o ciclo automático **reconfere os marcados pelo próprio id**
(`sumico_ops.reconferir_marcados`): o que voltou perde a marca e recebe os dados do Google, mesmo
num mês que o ciclo não lista. **Só o ciclo automático reconfere**: o "Limpar eventos fantasma" não
chama a reconferência — nele o marcado só perde a marca se o id voltar à lista do mês. O resumo do ciclo (`AuditLog` `sync_ok`/`sync_erro`) traz os totais
"Sumiços: …" antes da lista de meses.

### Fluxo: "Sincronizar" de um evento

`POST /api/events/<id>/sync` (e o wrapper Jinja) → `_sync_single_event_flow` → `consultar_evento`
no próprio id **antes de mexer** (feature 303). Ausente → nada muda (nem evento, nem escala, nem
marca) e a API responde 409; inconclusivo → 502; presente → se estava marcado, a marca sai com o
histórico em nome de quem clicou, e então `sync_events([item])`. Antes da 303 o item apagado (que o
`get` do Google devolve com `status: cancelled`) ia direto para `sync_events` e virava "Sem título",
sem datas e sem escala, com e-mail de remoção.

### Fluxo: criação de evento (Manto → Google)

`POST /api/events` (`agenda_write.py:528`) → `_build_create_event_data` → `_validate_event_core`
(`routes.py:2969`) → **`insert_event` no Google** → `_create_event_core` (`routes.py:3283`) → linha do
evento, vínculos de cliente, pré-contrato, roles a partir dos personagens, cargos padrão, reembolso,
observações, `EventLog`, `AuditLog`, `_sync_commission_payment`, commit, notificação de ensaio,
checagem de conflito (avisos não bloqueantes).

⚠️ **O Google é chamado ANTES do banco e não há compensação.** Se `_create_event_core` estourar,
sobra um evento órfão no Google Calendar que o próximo sync importa como evento novo — sem venda, sem
cliente, sem elenco, indistinguível de um evento criado direto no Google.

### Fluxo: exclusão

`DELETE /api/events/<id>` (e a rota Jinja `POST /events/<id>/delete`) → `_delete_event_flow` →
**trava o evento e relê** (`refresh(…, with_for_update=True)`, feature 306: um cancelamento ou uma
marca no meio do caminho mudaria o que a decisão leu) → **recusa evento cancelado**
(`EventoCanceladoError`, feature 306 — 409 `cancelado` para todos, o Superadmin inclusive: cancelar não
tem volta, e o cancelado por engano se recria à mão; o Jinja volta ao evento com o aviso) → **recusa
evento marcado "Sumiu do Google Agenda"** (`EventoMarcadoError`, feature 303 — a API
responde 409 `sumiu_do_google`, o Jinja volta ao evento com a mensagem, que oferece as duas saídas:
devolver ao Google ou cancelar. Desde a 306 o cancelar aceita o marcado e o desmarca com o motivo
"cancelado" antes de gravar o cancelamento; antes da 306, `cancelar_evento` recusava
pela mesma regra) → recusa líder de grupo → `AuditLog 'manual_deleted'` →
`_delete_event(also_from_google=True)` → `_clear_event_side_tables` do evento **e de cada
ensaio-filho** (o histórico do ensaio estourava a exclusão do pai) + tratamento de comissão
(`cancel_ops.aplicar_estorno_comissao`: a pendente vira `cancelado`; a paga **ou no banco** gera um
estorno órfão negativo no **primeiro repasse aberto** do vendedor, com o motivo "Exclusão do evento" —
antes da 306 ele copiava a data da venda e caía num repasse já pago —, e as duas perdem o vínculo com
o evento; ver §2, Estorno) → delete no Google (falha não trava) →
apaga os avisos do sino do evento → delete local. A limpeza do sync (`sumico_ops._apagar_vazio`) trava
e relê do mesmo jeito antes de apagar, e o evento que se descobre cancelado ali fica.

### Fluxo: devolver ao Google (feature 303)

`POST /api/events/<id>/devolver-ao-google` (só Superadmin) → `sumico_ops.devolver_ao_google`:
valida (marcado, não cancelado, não virtual, com datas) → **trava de ambiente**
(`CALENDAR_SUPPRESS_EVENT_WRITES`, ligada fora da produção) → consulta o id velho (sem ausência
confirmada, nada é criado) → `SELECT … FOR UPDATE` e revalida → histórico (e `source = "platform"`
quando há vaga de personagem fora do título) com `flush` → id velho **ausente**: `insert_event` com
os dados ATUAIS do sistema (dia inteiro como dia inteiro), troca o id e o link; id velho
**presente** (alguém restaurou da lixeira): nada é criado, o cabeçalho do sistema é empurrado ao id
velho se diferir → desmarca → commit. Falha do Google: rollback, auditoria `google_return_failed`
com o tipo do erro, 502 com mensagem fixa — a marca continua.

### Fluxo: cancelar (features 224 e 306)

`POST /api/events/<id>/cancelar` (só o Superadmin, `_can_delete()`) → `cancel_ops.cancelar_evento`,
numa transação e numa ordem só (as travas: `docs/00` §6, itens 25 e 26): **T1** trava o grupo inteiro
(`travar_grupo`: o principal e todos os dias, vivos e cancelados, com os ids por consulta) e relê →
recusa o já cancelado (409 `ja_cancelado`) e o Ensaio (409 `ensaio`) → decide a **forma**
(`_forma_do_ato`): `avulso` (também o principal cujos outros dias já foram todos cortados), `todos`
(pelo principal: ele no regime `venda`, cada outro dia vivo em `satelite`), `corte` (um dia que não é o
principal: `dia`, e a venda fica no principal, menor) ou `passagem` (só o 1º dia: `dia`, e a venda passa
ao dia vivo mais cedo) → T3 a T6 (acréscimos, linhas de comissão, devoluções do grupo, escalações dos
dias alcançados) → recusa cachê pago (409 `cache_pago`) e devolução pendente em qualquer dia (409
`devolucao_pendente`) → valida todos os campos de uma vez (400 com `fields`) e o "Tudo" contra o máximo
de agora (409 `max_devolucao_mudou`) → desmarca o marcado (`sumico_ops.desmarcar`, motivo "cancelado")
→ congela (`event_cancellations`, os BVs em `event_cancellation_bvs`, o elenco em
`event_cancellation_elenco`) → na passagem, marca a comissão própria do novo 1º dia e chama
`group_ops.passar_venda` → a devolução, quando há, nasce como Gasto Extra **aprovado** ligado ao evento
da URL → a comissão: no `venda`, a reconciliação pelo retido; no corte e na passagem, a venda nova do
principal que fica, com o BV a pagar acompanhando uma vez e a comissão refeita quando a cheia muda →
`cancelled_at` e `ao_cancelar` (o ponto de extensão da 2a, hoje sem efeito) de cada dia → os ensaios
saem do banco, os sinos e as multas nascem → um `EventLog` por dia → commit → **depois do commit**, fora
da trava, a remoção do Google (dias e ensaios) e o e-mail ao elenco. O marcado e o `virtual-local-…` não
chamam o Google; `CALENDAR_SUPPRESS_EVENT_WRITES` é lida a cada chamada (chave ausente = travado); falha
ou trava viram `aviso` e nunca desfazem o cancelamento. A venda da Loja Virtual (regime `virtual`) só
pede o motivo: sem retido, devolução nem multa por aqui. O clique duplo para em T1 (409
`ja_cancelado`), com o `UNIQUE(event_id)` como segunda barreira; o deadlock vira 409 `tente_de_novo`
(`cancel_ops.traduzir_erro_de_banco`).

A **prévia** (`GET /api/events/<id>/impacto-exclusao?devolucao=…`, `previa_cancelamento`) faz a mesma
conta do ato, sem trava e sem escrita: o retido, a comissão do retido, o ajuste, o ciclo, a data do
repasse e o BV do retido que ela mostra são os que o ato grava logo depois, também nos dias 1 a 5.
Depois do ato, só o Superadmin corrige, e a correção refaz o dinheiro na mesma transação: "Alterar
devolução" (`PATCH /api/events/<id>/devolucao`, `alterar_devolucao`), comprovante
(`gravar_comprovante_no_grupo` → `reaplicar_por_dinheiro`), aba Comercial e acréscimos
(`recongelar_do_comercial`). Multa (`POST /api/events/<id>/multas`), reembolsos, parcelas e notas não
mexem no congelado. **Relógio**: `cancelled_at`, `event_cancellations.created_at/updated_at` e a data
da devolução e da multa em São Paulo sem fuso (`now_sp()`); o `EventLog` da 306 (ato, passagem e
correções) sai sem `created_at`, pelo default UTC do modelo — o do cancelamento da 224 saía 3 h antes.
Modelo e transições: `specs/306-dinheiro-do-cancelamento/data-model.md` §5 a §8.

### Antes do ato: o pedido de cancelamento (feature 315)

**Fluxo.** O Comercial não cancela: pede ("Solicitar cancelamento", `POST /api/events/<id>/pedido-cancelamento`), com o
motivo, o alcance numa venda de vários dias (no 1º dia com outro dia vivo: todos ou só este) e a devolução combinada com
a cliente (tudo, parte com o valor, ou nada; quem recebe e PIX em tudo e parte; no pedido de um dia só, o novo valor da
venda). Cada Superadmin é avisado no sino na mesma transação. **Só o Superadmin fecha o pedido**, de três jeitos:
recusando (`DELETE …/pedido-cancelamento`), cancelando (o ato da 306 fecha o pedido de cada dia que encerra, em
`cancel_ops.ao_cancelar`) ou excluindo o evento vazio; cada saída responde a quem pediu, uma vez, no sino. Devolver ao
Google não mexe no pedido; editar o evento com pedido continua valendo (o pedido não tranca nada).

**Invariantes.**
1. O pedido mora no evento, nas cinco colunas (`deletion_requested_at/_by_id`, `deletion_request_reason`,
   `deletion_request_scope`, `deletion_request_refund`), e **só `app/calendar/solicitacao_ops.py` as escreve**. Pedir e
   recusar são `UPDATE` condicional (o claim): dois pedidos ao mesmo tempo dão um pedido e um 409 `pedido_pendente`;
   duas decisões dão uma decisão e um 409 `sem_pedido` — nunca duas respostas.
2. O pedido não confere dinheiro: o máximo, o mínimo e o "nada pago" são do cancelar, com o pago daquele momento. O
   que o pedido recusa é estado: cancelado (trava da 312), ensaio e cachê pago ao elenco (no próprio dia; nos outros
   dias só quando "todos" os alcança).
3. Corte por papel na leitura (Q6): todos veem que há pedido (data e alcance); motivo, autor, modo e valor da devolução
   só quem trata do cancelamento (`show_comercial`); quem recebe e PIX também exigem Financeiro ou ser o autor sem "Ver
   como". O sino, o histórico e a auditoria nunca levam nome nem PIX; a faixa e o portal não levam motivo.
4. Num pedido de "todos os dias", os outros dias da venda mostram o pedido (selo, detalhe, portal) — calculado em lote
   por quem serializa (`solicitacoes_da_venda`), nunca na propriedade do modelo.
5. Pedido de antes da 315 (alcance e devolução nulos) vale como "todos" e "sem devolução informada"; o caminho velho
   `/solicitar-exclusao` continua nas mesmas views até o bundle novo ser o único (dívida em `docs/05`).

**Armadilha.** O fecho no cancelamento roda dentro do ato, com o dia já travado: não há claim ali — a recusa que chegar
depois não acha mais o carimbo. A resposta da exclusão sai **depois** do commit (o objeto morre nele): uma recusa que
commita entre a leitura e a trava do núcleo dá ao autor "recusado" e depois "excluído" (corrida aceita, research R10).

### Depois do ato: o cancelado fora das listas (feature 312)

**Invariante.** O cancelado não aparece em lista nenhuma do sistema — agenda (Mês, Lista, Dia), busca, Home (fora a
pendência do Casting, abaixo), fichas de talento e de cliente, listas de escolha (vínculo de ensaio, tag NFC, grupo,
seletor por data de Gastos Extras, pedido de figurino e formulário, candidatos automáticos do formulário), filas do 3D,
painel "Grupo comercial" do principal vivo, lista de vendas, tabela da DRE e o aviso de conflito de agenda do talento.
Vê-se em três lugares: a página de Cancelamentos, o card "Cancelamentos do período" (DRE e Comercial) e a tela dele.
Todo filtro e toda recusa olham **só** `cancelled_at`: o pedido de exclusão e a marca "Sumiu do Google" não escondem
nem travam nada. Onde uma coisa viva já ligada a ele aparece (gasto, tag, pedido de figurino, formulário), o nome do
evento leva o selo "Cancelado"; o vínculo não se desfaz sozinho.

**Nada novo se liga a ele.** Ensaio (agendar e vincular), tag NFC nova, presente 3D novo, formulário, escala, convite,
link de avaliação e pedido de figurino são recusados no núcleo (`cancel_ops.recusar_se_cancelado_para_ligar`), antes de
e-mail ou Google, com `codigo: "cancelado"`. Ligar Gasto Extra por chamada direta continua valendo (a devolução e a
multa da 306 se ligam ali); só não é oferecido na lista.

**A tela dele só se consulta.** Toda escrita na tela do cancelado leva 409 `cancelado` para todo papel
(`cancel_ops.exigir_evento_vivo`), menos as portas com regra própria — os dados de venda (só o Superadmin, 306), o
motivo (Superadmin e Comercial, 306b) — e os desfazer: desligar o formulário, soltar tag ou presente, tirar o artista da
escala. O motivo e o autor do cancelamento só saem a Comercial, Financeiro e Superadmin (Q9).

**Fluxo: o Casting tira e avisa (Q10).** O ato da 306 manda o e-mail a cada escalado e o sino `evento.cancelado_escala`
ao Casting, um por dia. A Home do Casting mostra "Eventos cancelados — excluir e avisar", **derivada da escala de
hoje** pela régua do ato (`cancel_ops.elenco_dos_dias`: com talento, sem quem recusou, sem a vaga de presença), com o
WhatsApp pronto. No cancelado, só Casting e Superadmin tiram da escala, e só tiram (`assign` sem talento; cachê e
transporte não mudam); a vaga fica vazia como registro; nenhum e-mail de remoção sai; quando sai o último escalado de
um dia, o sino daquele dia fica lido para todos, na mesma transação. A multa tardia ao elenco sai da lista congelada do
ato (306), não da vaga de hoje.

### Invariantes

1. **O título do evento no Google é a fonte de verdade do elenco.** `parse_characters`
   (`routes.py:1935`) separa por `+` e remove o prefixo `(TIPO)`.
   Ex.: `(R&I) HOMEM ARANHA + MARIO` → `['HOMEM ARANHA', 'MARIO']`.
2. `parse_event_type` extrai o tipo do prefixo entre parênteses; título iniciado por `🟧 ENSAIO`
   força `event_type = 'ENSAIO'`.
3. `start_at`/`end_at` são **naive em horário de São Paulo** (`service.py:203-207`) — o Postgres usa
   `TIMESTAMP WITHOUT TIME ZONE` e converteria aware para UTC. **Nunca gravar aware.** Exceção
   isolada: `SiteSetting.calendar_sync_cache` usa `utcnow` (`routes.py:88`, `:101`).
4. Evento com fim < início cruza a meia-noite → fim vai para o dia seguinte (`_build_start_end`,
   `routes.py:63`).
5. `source == 'platform'` protege o elenco do sync; roles com `role_type == 'extra'` (Coordenador,
   Maquiador, Técnico) nunca são tocados; `parent_event_id` nunca é sobrescrito pelo Google.
6. Evento de venda virtual é **intocável** pelo sync — nem atualizado, nem apagado; só gera log
   `virtual_divergente`.
7. `group_leader_id` (grupo comercial) ≠ `parent_event_id` (show ↔ ensaio). Satélite tem os campos
   comerciais zerados (`_apply_satellite`, `routes.py:1424`).
8. `EventLog`, `EventContract`, `EventPayment`, `EventRating`, `ClientFeedback` e
   `EventReimbursement` **não têm cascade** — sem `_clear_event_side_tables` (`routes.py:189`) o
   delete estoura violação de FK.
9. Falha do Google **nunca** bloqueia escrita local (`event_ops.py:404`, `routes.py:238`, `:2629`) —
   vira aviso.
10. `cache_cap` em `EventRole` é **teto** vindo do orçamento: `casting_ops.py:68` trunca para
    não-superadmin e gera nota de auditoria quando ultrapassado.
11. **O que o orçamento diz sobre o evento entra por um lugar só** (feature 273):
    `app/calendar/orcamento_evento_ops.py` — fora de SP + quilometragem, equipe vendida com teto
    (coordenadores × quantidade, Técnico de Som, Maquiador, maquiagem/cantor por personagem casado
    pelo nome) e, em evento sem venda, os valores. Usado na criação, no vínculo posterior
    (`PATCH /events/<id>/orcamento`) e em `reclassificar_fora_de_sp`. **Nunca apaga nem rebaixa**
    o que o casting fez à mão; o que não casa vai ao relatório, não vira vaga nova.
12. **Venda e cobrança: o grupo é uma venda só** (feature 299, `app/financeiro/cobranca_ops.py`,
    fonte única da Home e da página do evento). O valor é o do principal e o recebido é a soma dos
    comprovantes de TODOS os eventos do grupo, cancelados inclusive; nada é movido de lugar (a
    cobrança soma na leitura; só a passagem da venda da 306 move linhas, invariante 20). Desde a 306, o
    saldo, a quitação, o sinal e a parcela descoberta contam o recebido **menos as devoluções à cliente
    aprovadas** ligadas a qualquer dia do grupo (`VendaResumo.devolvido` e `recebido_liquido`; o
    recebido mostrado segue bruto): venda 2.000, pago 1.500 e devolvido 300 dão 800 a receber. A data
    do grupo é a do 1º evento não cancelado e que não é compromisso interno.
    - **"Sem valor" tem duas definições, de propósito**: na Home, vazio, zero ou abaixo de R$ 1,00
      (`event_ops.sem_valor_de_venda`); no Financeiro e na Auditoria, `<= 0`. Não unificar de
      passagem.
    - **Compromisso interno** é o título que começa com 🟧 ou 🟠: nunca é venda e não conta na data
      do grupo. O tipo vazio NÃO é ensaio — a venda 395, de R$ 35 mil, não tem tipo.
    - **Vencimento do saldo**: data combinada > 1ª parcela que o recebido não cobre > 2 dias antes;
      os dois últimos nunca antes da data da venda. Com data combinada ou cronograma, não há sinal
      pendente.
    - **Folga de centavos**: R$ 1,00 — no saldo, no sinal e no "Quitado" da página.
    - **Comissão tardia**: quando o valor chega depois (evento cadastrado e vendido num mês
      anterior), a comissão entra no ciclo do mês do valor (`payable_from = hoje`, com a marca "Ciclo: mês em que o valor foi posto" nas notas da linha, que não volta a
      `NULL`); a venda lançada agora com a data de um mês anterior segue a data da venda. A linha de
      R$ 0,00 já paga não conta como paga quando há comissão de verdade a pagar — pagar zero não
      é pagar; com a comissão calculada também em zero, ela vale —, e a comissão paga de valor
      real nunca é paga de novo. Essa regra vale só na comissão comum: a EducaManto fica como antes
      da 299, e a linha que sai da EducaManto não leva a data da realização para o ramo comum.
    - **Cortesia ou permuta nunca comissiona** (dono, 15/09): a sincronização não cria linha e
      cancela a `a_pagar`, mesmo na cortesia antiga que tem valor gravado.
12b. **PIX recebido → venda** (feature 318, `app/financeiro/pix_ops.py`). O pagamento lido do aviso do banco é
    um `event_payments` como qualquer outro (`origem='pix_email'`, sem arquivo), gravado **sempre** pelo núcleo de
    comprovante (`gravar_comprovante_no_grupo`, trava do grupo e recálculo da 306) — a soma do recebido não muda de
    fórmula. Liga sozinho só com **uma** venda aberta de valor forte (saldo, sinal, parcela descoberta, total; ao
    centavo) **e** nome do pagador batendo (≥ 2 termos ou semelhança ≥ 0,85) **ou** "já pagou antes" (PIX do mesmo
    pagador ligado à venda/cliente), **e** DKIM do Inter aprovado pelo `mx.google.com` com remetente exato.
    Conciliação com comprovante manual **nunca** é automática (sinal e saldo de 50% têm valor igual) e não cruza
    contas. "Prime Dreams" no MEI: repasse do Inter Prime (par de 1–3 PIX da Prime em 3 dias, cada par usado uma vez)
    é `conta_propria`; o resto é repasse da InfinitePay ("É esta?" só do Financeiro, pago pelo valor cobrado e com
    a conta InfinitePay). Comprovante manual igual a PIX sem arquivo → 409 `possivel_duplicata` (sob a trava);
    pagamento ligado a PIX não se exclui, se desfaz. O padrão "liga sozinho / É esta?" é o mesmo da 298 e da 317.
13. **O sync nunca apaga evento com dinheiro** (feature 303, `sumico_ops.preso_ao_evento`): segura o
    evento ter venda, qualquer comprovante (mesmo sem valor), contrato, escala com talento — menos,
    em SHOW, a vaga automática do técnico de som com o técnico padrão — ou pertencer a grupo
    comercial (principal ou satélite). Comissão já paga **não** segura (decisão do dono, 30/09): o
    evento vazio é apagado e o estorno sai contra o vendedor — desde a 306, no primeiro repasse aberto
    dele (§2, Estorno). A limpeza trava e relê o evento antes de apagar, e o cancelado nunca é apagado.
14. **Ausência só vale confirmada.** A falta na lista do mês não basta: só 404, 410 ou `status:
    cancelled` na consulta ao próprio evento contam. Inconclusivo não apaga nem marca — na dúvida,
    o evento fica. Mudança de data não é sumiço: o evento presente com outros dados recebe a data
    nova no mesmo registro.
15. **"Marcado" = `google_missing_since` preenchida E `cancelled_at` nulo** (fonte única:
    `sumico_ops.filtro_marcados()` no SQL, `CalendarEvent.is_google_missing` no objeto). A
    situação única do evento (`CalendarEvent.situacao`) resolve a precedência cancelado > sumiu do
    Google > exclusão solicitada; a tela nunca recombina as colunas. Só `marcar`/`desmarcar`
    escrevem a coluna.
16. **Marcado que reaparece sozinho: vale o Google.** A lista, a reconferência ou o "Sincronizar"
    tiram a marca e aplicam os dados do Google — o que foi editado no sistema enquanto marcado se
    perde, e a escala é reconciliada pelo título do Google (vagas fora do título saem, com e-mail
    de remoção). Só a **devolução** faz valer o sistema (e passa o elenco ao sistema quando há vaga
    fora do título). Risco aceito na 303.
17. **Relógio de cada carimbo da 303**: `google_missing_since` e `notifications.created_at` em
    horário de parede de São Paulo (`now_sp()`); o `EventLog` novo usa o default UTC do modelo (a
    tela converte); `AuditLog.created_at` é UTC.
18. **Cancelar tem uma regra de dinheiro só, e não tem volta** (feature 306). O avulso, o marcado pela
    303, a venda inteira pelo principal e o corte de um dia passam pelo mesmo `cancelar_evento`; a
    exceção é a venda da Loja Virtual (regime `virtual`), que passa pelo ato sem retido nem devolução e
    mantém o estorno próprio da loja. O regime e o modo da devolução nunca mudam depois do ato; o
    cancelado sem linha congelada (anterior à 306) é `legado`. O cancelado não se exclui (409
    `cancelado`), não se "descancela" e não volta pelo Google (o sync o pula desde a 224); aplicar
    orçamento nele também dá 409 para todos, porque recriaria venda e acréscimos de uma vez.
19. **Grupo: cancelar não desagrupa.** No principal com outro dia vivo, o alcance é obrigatório: "todos"
    cancela todos os dias vivos numa confirmação (o principal em `venda`, os outros em `satelite`, sem
    dinheiro próprio); "só este dia" no principal faz a passagem (invariante 20). Num dia que não é o
    principal, só o corte (invariante 21). O dia cancelado **fica no grupo** — é o histórico da venda —
    e não entra nem sai dele: agrupar com cancelado, desagrupar ou tirar o dia cancelado dá 409
    `cancelado` para todos, o Superadmin inclusive (`group_ops.recusar_cancelado_no_grupo`). Como
    `is_group_leader` continua verdadeiro com os outros dias cancelados, quem lê o grupo vivo usa
    `group_ops.dias_vivos`: o custo de cachês (`_group_cost`, base da EducaManto e CPV), o KPI e os
    gastos do principal vivo não contam o dia cancelado.
20. **A passagem muda o dono, não o valor nem a data** (`group_ops.passar_venda`). O novo principal é o
    dia vivo mais cedo que **não** é compromisso interno (🟧/🟠, que a cobrança da Home não lista; só
    compromisso interno vivo → 409 `sem_outro_dia_vivo`) (início, depois id; se mudou enquanto o diálogo
    estava aberto, 409
    `grupo_mudou`). Passam as mesmas linhas, só com o `event_id` trocado — nunca apagar e recriar:
    comprovantes, parcelas, notas, contratos, reembolsos, acréscimos (com o estado do BV), formulários e
    **todas** as linhas de comissão, pagas e no banco inclusive (`TABELAS_DA_PASSAGEM`), mais a devolução
    aprovada do antigo e as clientes que faltam no novo; os campos de venda e o nome do grupo passam por
    `CAMPOS_DA_PASSAGEM`. Quem acrescentar tabela ou campo de venda acrescenta nessas listas. Todo dia
    passa a apontar para o novo, e o antigo, cancelado, vira satélite dele. Ficam no antigo o elenco, os
    ensaios (que caem), a logística, o histórico, os outros Gastos Extras e a devolução do próprio ato.
    A comissão comum segue a data da venda (o mesmo repasse); a EducaManto **a pagar** vai à data do
    novo 1º dia, pela sincronização de sempre; a DRE segue o evento que guarda a venda (receita,
    imposto, BV, cachês dos dias vivos e comissão vão ao mês do novo 1º dia, e o BV à Planilha desse
    mês). A comissão própria que o novo dia já tinha de quando era venda avulsa fica marcada
    (`NOTA_COMISSAO_PROPRIA_DO_DIA`) e fora da conta da venda, da sincronização e da comissão exibida.
21. **Corte de um dia: a venda do grupo diminui e ninguém fica com retido.** O Superadmin informa a
    venda nova (maior que zero e até a atual) e devolve Parte ou Nada, com teto (pago do grupo − já
    devolvido) e **piso**: a cliente nunca fica com mais pago do que a venda nova
    (`cancel_ops._devolucao_minima`). No principal, que segue vivo e na DRE do mês do evento, o valor
    cheio cai na mesma proporção (o percentual de desconto fica), o BV a pagar acompanha uma vez só
    (`acompanhar_bv_da_venda`), o pago fica, e a comissão vai ao alvo da venda nova pela reconciliação
    ("Corte de dia: venda diminuiu") só quando a cheia muda. A devolução nasce ligada ao dia, conta no
    "já devolvido" do grupo e se corrige pelo "Alterar devolução" do dia, que só refaz o principal se
    ele já foi cancelado inteiro.
22. **Cachê pago impede o cancelamento**, por papel nenhum: 409 `cache_pago`, com os dias alcançados que
    têm cachê pago, e nada é gravado nem avisado. A régua é única (`cancel_ops.cache_pago_do_evento`,
    que a 2a importa): escalação com artista em pago ou no banco, fora a vaga de presença do técnico de
    som. Para devolver dinheiro nesse caso, a Devolução se lança em Gastos Extras.
23. **O ensaio segue o show.** Ensaio não passa pelo cancelar (409 `ensaio`). Todo ensaio dos dias
    cancelados sai do banco na transação do ato (`event_ops._apagar_ensaio_no_banco`, a mesma do
    "Cancelar ensaio" e da troca de tipo) e do Google depois do commit, com a mesma trava de ambiente; o
    histórico do show guarda data, hora e local de cada um. Na passagem, o ensaio do antigo 1º dia cai e
    não passa ao novo. Ensaio que o Google não apagou volta no próximo sync como ensaio órfão (dívida
    no `docs/05`).
24. **Multa ao elenco: um Gasto Extra por escalação** (vaga × dia). O ato congela a lista
    (`event_cancellation_elenco`: com artista, sem quem recusou o convite e sem a vaga de presença);
    tirar o artista da vaga depois não apaga a linha nem o direito à multa, e só quem está na lista
    recebe multa, no ato ou depois (`POST …/multas`, uma por linha). O gasto nasce aprovado e a pagar ao
    artista (categoria "Multa de cancelamento", PIX do cadastro), ligado ao dia, com a data do ato ou do
    lançamento — é gasto extra desse mês na DRE e na Planilha. Corrige-se em Gastos Extras, sem trava, e
    **não mexe em comissão nem em BV**. Vazio ou 0 é "sem multa".
25. **Permissão: uma regra só para os dados de venda do cancelado** —
    `cancel_ops.pode_editar_venda_do_cancelado`, o Superadmin pelo papel real (o "Ver como" não conta),
    aplicada depois da trava e da releitura (em geral por `cancel_ops.recusar_se_cancelado`). Quem passa
    no gate da porta e não é Superadmin recebe 409 `cancelado`; nas portas que não recongelam, o 409
    vale para todos. As portas e o 409 de cada uma: `docs/00` §4 e `docs/01` §4.3.
26. **Avisos do ato.** Cada artista alcançado recebe uma vez o e-mail de remoção que já existe
    (`send_removal_email`), depois do commit — só quem tem e-mail, nunca quem recusou o convite nem a
    vaga de presença; no corte, só o elenco daquele dia. Tirar da vaga um artista de evento cancelado
    **não** manda o e-mail de remoção (`casting_ops._manda_email_de_remocao`): ele já recebeu o do ato.
    Na transação, dois sinos: a equipe de Ensaio recebe `evento.cancelado` só quando caiu ensaio; o
    Casting recebe `evento.cancelado_escala` por dia cancelado com escalados (`urgent` a 7 dias ou
    menos). A `dedupe_key` é a do evento da URL do ato (`cancel_ops._chave_do_sino`): um corte de dia e
    depois o "todos" dão dois sinos a cada pessoa. Cancelamento recusado não avisa ninguém.

### Armadilhas

- **Renomear qualquer `_helper` de `routes.py` quebra a API em silêncio.** 39 símbolos privados são
  importados por 10 módulos, e os imports são **tardios** (dentro das funções) — não aparecem em
  análise estática de topo.
- ~~Comissão diverge entre Jinja e React~~ — **desatualizado** (conferido na 299):
  `event_ops.update_event_core` e `update_event_comercial` recebem `sincronizar_comissao` e chamam
  `_sync_commission_payment` antes do commit, como o handler Jinja; os endpoints de
  `app/api/agenda_write.py` passam a função. A venda preenchida depois pelo React gera a comissão,
  no ciclo do invariante 12.
- ~~Agrupar/desagrupar só existe no Jinja morto~~ — **desatualizado** (corrigido na 299): desde a
  feature 246 a aba Comercial agrupa, desagrupa, tira satélite e nomeia o grupo
  (`group_ops`, `PATCH|DELETE /api/events/<id>/grupo`). `_delete_event_flow` continua recusando o
  líder de grupo: para **excluir**, desagrupar antes. Para **cancelar**, não (feature 306): pelo
  principal, "todos" cancela o grupo inteiro e "só este dia" passa a venda; num outro dia, o corte.
  ⚠️ Desde a 306 **o principal pode mudar**: cancelar só o 1º dia leva a venda ao dia vivo mais cedo
  (`group_ops.passar_venda`), que vira o principal, e o antigo vira satélite dele — não guarde o id do
  principal como fixo. O dia cancelado fica no grupo e não entra nem sai dele (409 `cancelado`, também
  ao Superadmin). Invariantes 19 e 20, acima.
- ~~Acréscimos, notas e parcelas só têm escrita no Jinja~~ — **desatualizado** desde a 251: a API
  grava (`PUT /api/events/<id>/acrescimos|parcelas`, notas pela aba Comercial), pelo mesmo núcleo
  `comercial_ops` que o Jinja usa.
- **BV (feature 305) — invariantes.** O acréscimo que nasce do orçamento chega em **reais**, já na
  proporção da venda (`orcamento_evento_ops.gravar_acrescimos_do_orcamento`), com a origem na
  descrição, e não é recalculado do orçamento depois. O BV em % lançado à mão é sobre o preço **com**
  os outros acréscimos e **antes** do BV e da nota (`comercial_ops.valor_do_bv_percentual`); o BV em
  reais à mão é gravado como digitado e fica fora da base do em %. Nenhum BV é gravado sem quem
  recebe e PIX (criação antes do Google, vínculo, editor). O BV **a pagar** acompanha a venda que
  muda depois (`acompanhar_bv_da_venda`: reais pelo líquido, % pela régua); `pago` e `no_banco`
  nunca mudam de valor e não saem pelo editor. O editor herda status, PIX e descrição só da linha
  de mesmo `id` (o mesmo `id` duas vezes é recusado). A lista `acrescimos` do corpo da criação é
  sempre ignorada. A proporção (criação, alerta, B10) é sempre entre valores **líquidos** (× 0,84 de
  quem tem nota): o mesmo preço com e sem nota dá o mesmo BV. Nenhum BV sem valor, zero ou negativo.
  **Desconto negociado (feature 313)**: no orçamento novo (`versao_conta: 2`) o `total_Nh` já vem com o desconto, e
  a proporção do BV passa a ser venda ÷ **cheio** da duração (`brutos` do snapshot) — com o total no denominador a
  razão daria 1 e o BV não encolheria; `deduzir_duracao` procura a duração pelo cheio primeiro e depois pelo final.
  O `sale_value_gross` do evento nasce com o cheio e o `sale_value` com o final. Orçamento sem a marca: o
  denominador e a régua acima de 4h de antes (a 305 inteira lê o salvo; nada muda no que já foi cotado).
  Quem lê a venda para gravar BV trava o evento antes (`orcamento_evento_ops.travar_evento`, chamado
  por `estado_da_venda`, `substituir_acrescimos` e `set_event_clients`; `delete_client` anula o
  evento antes de apagar os vínculos); a ordem é sempre evento → dependentes. O editor que abriu antes de uma mudança de venda não desfaz a B10 (`valor_visto`). O "Vincular
  e aplicar" que põe a venda num evento que já tinha BV roda a B10 como a aba Comercial.
- ~~`flash()` aparece dentro de `_delete_event`~~ — **desatualizado** (conferido na 303): desde a
  224 `_delete_event` devolve o aviso de falha do Google em vez de chamar `flash`, e não depende de
  request context; a limpeza do sync passou para `sumico_ops` e chama `_delete_event` sem
  `also_from_google`.
- `_compute_performer_caches` (`routes.py:2835`, ~270 l.) é **precificação de orçamento** morando no
  módulo de calendário; `app/orcamento/pricing.py:13` aponta de volta para ela. Preço de cachê não
  está onde se procura.
- Código morto puro: `travel_estimate` (`routes.py:2424`, perdeu o decorator, sem chamador — a
  estimativa que roda é `_fetch_travel_data`, `:2377`) e `_is_outside_sp` (`:2365`).
- **Docstrings mentem sobre o Jinja.** `agenda.py:3`, `agenda_write.py:4`, `casting_ops.py:3`,
  `event_ops.py:4` e `observation_ops.py:4` afirmam que existem "DOIS adaptadores finos" e que "as
  views Jinja seguem intactas". Não seguem: estão inalcançáveis. Não planeje refactor confiando nisso.

---

## 2. Financeiro

**Arquivos:** `routes.py` (1.690), `comissoes_ops.py` (405), `vendas_ops.py` (352),
`app/api/financeiro_read.py` (738), `financeiro_write.py` (532).

`routes.py` **não é um arquivo de rotas**: é o núcleo de cálculo do sistema com 3 views Jinja
penduradas, e é importado por `app/api/financeiro_read.py`, `financeiro_write.py`,
`app/calendar/routes.py` e `app/financeiro/vendas_ops.py`.

### A regra de comissão, completa (`routes.py:120-150`)

Nunca esteve escrita em lugar nenhum. São 9 ramos, em ordem:

1. Sem `sale_value` → **0**.
2. Venda da Loja Virtual (`event_type == 'VIRTUAL'`) → **0**, e a linha `CommissionPayment` **nem
   nasce** (`:155-160`). Provisionar comissão para uma venda que se fecha sozinha reservaria caixa
   para um beneficiário inexistente.
3. Beneficiário: evento EducaManto (título começa com `(EDU`) com responsável configurado em
   `SiteSetting.educamanto_seller_id` → o responsável; senão → o vendedor do evento
   (`_commission_beneficiary`, `:107`).
4. Beneficiário com `receives_commission = False` → **0**.
5. **Base EducaManto**: 5% (`EDUCAMANTO_COMMISSION_RATE`, `:30`) sobre o **LUCRO** = venda − BV −
   cachês. **Base comum**: 2,5% (`DEFAULT_COMMISSION`, `:27`) ou override do evento, sobre
   venda − BV. **BV sempre sai da base** porque é repasse a terceiro, não receita.
6. Base negativa vira 0; arredondamento `ROUND_HALF_UP` em 2 casas.
7. **Ciclo de pagamento**: comissão comum entra pelo mês da **venda** (`sale_date`); comissão
   EducaManto entra pelo mês da **realização** (`payable_from = event.start_at.date()`, `:184`).
   `coalesce(payable_from, sale_date, date(created_at))` (`comissoes_ops.ciclo_de_pagamento_expr`) é
   a expressão canônica do "mês da comissão" — o terceiro degrau entrou no hotfix 267b: comissão
   de venda gravada sem `sale_date` caía fora de TODO mês da Planilha de Pagamentos (38 linhas,
   R$ 5.162,26, em agosto/2026). A regra de negócio "venda tem data" mora em
   `event_ops.resolver_data_da_venda` (venda nova sem data → hoje em São Paulo; venda antiga sem
   data não ganha data inventada — é caso do backfill em `specs/267b-hotfix-data-da-venda/`).
8. Comissão já **paga** ou **no banco** nunca é reescrita — é histórico (`_sync_commission_payment` só
   regrava a `a_pagar`). Desde a 306, a diferença que o cancelamento, uma correção do cancelado ou o
   corte de um dia pedem nasce numa linha nova de ajuste, no primeiro repasse aberto de quem recebeu
   (invariantes 8 e 10, abaixo). Valor e datas dela nunca mudam; o vínculo (`event_id`) só muda em dois
   caminhos: a passagem da venda ao novo 1º dia (`group_ops.passar_venda`) e a exclusão do evento, que
   a desvincula e gera o estorno.
9. Se o evento é líder de grupo, o custo somado inclui os satélites **vivos**
   (`comissoes_ops._group_cost`): desde a 306 o dia cancelado sai do custo, da base da EducaManto e do
   CPV, porque o corte já tirou o dia da venda do grupo (a régua de `group_ops.dias_vivos`).

**Estorno** = o **órfão**: `CommissionPayment` `a_pagar`, negativo, sem evento e ligado à paga que
estorna (`original_id`) — o que a exclusão de um evento pago deixa (`comissoes_ops.filtro_estorno_orfao`,
predicado único desde a 306). Desde a 306 ele nasce no **primeiro repasse aberto** do vendedor, com o
motivo "Exclusão do evento" e sem copiar as datas da venda; os de antes (151, 211) herdaram o `sale_date` da
venda original, por isso `_pending_reversals_query` lista o órfão **sem filtro de
mês** e `_estornos_do_mes` o resgata no mês corrente — senão um estorno de março sumiria da tela em
abril. **Só o órfão** é resgatado: o **ajuste** do cancelado (linha ± com `original_id`, ainda ligada
ao evento) entra pelo próprio ciclo, e resgatá-lo o mostraria duas vezes. `comissoes_ops.tipo_da_linha`
diz de cada linha se é comissão, ajuste ou estorno, e o motivo sai do prefixo da nota
(`MOTIVOS_AJUSTE_COMISSAO`); Comissões e a Planilha mostram tipo e ciclo. ⚠️ Nos dias 1 a 5, o órfão
novo que caiu no repasse do mês anterior aparece duas vezes na tela de Comissões (no mês anterior, pela
data, e no corrente, pelo resgate); a Planilha o mostra uma vez (dívida no `docs/05`).

### A cascata da DRE Gerencial (`_compute_drg`, `routes.py:351`)

Nesta ordem, e **cada exclusão tem razão**:

`receita_bruta` (só eventos não-permuta e **não-satélite**, para não contar a venda do grupo duas
vezes) → `− impostos` (`DEFAULT_TAX_RATE = 16%`, só sobre eventos `with_invoice`) → `receita_liquida`
→ `− CPV` (cachês do grupo + BV) → `lucro_bruto` → `− marketing` (o cachê das permutas entra **aqui**,
fora do CPV, para não distorcer a margem) → `− comissões` → `− pessoal` → `EBITDA` → `− gastos
extras` → `− gastos recorrentes` → `resultado_liquido`.

**Com cancelado no período (feature 306)**, a cascata ganha quatro parcelas, todas pelo mês do
**cancelamento** e da mesma fonte na API e no Jinja (`cancel_ops.cancelados_do_periodo` →
`totais_cancelamentos`, passadas a `_compute_drg(…, cancelamentos=)` só no Realizado e no Total): o
**retido** soma na `receita_bruta` (linha própria "Retido de cancelamentos", logo abaixo), o **imposto
informado** no ato soma em `impostos` (nunca alíquota × retido), o **BV do retido** soma no `CPV` e a
**comissão do retido** em `comissões`. Os `gastos extras` saem de `dre_ops.gastos_extras_do_periodo`,
sem a devolução de evento cancelado, que já está descontada no retido. A condição é a **quantidade**
de cancelados, nunca o valor: somar `Decimal("0.00")` muda o expoente, e a DRE dos meses sem cancelado
deixaria de sair idêntica à de antes. `retido_cancelamentos` e `n_cancelados` saem sempre; `n_eventos`,
`n_normais` e `n_permutas` não contam o cancelado.

- **Regime: competência pela data do evento** (`start_at`), não pela venda nem pelo recebimento —
  salvo o cancelado, que sai do mês do evento e entra pelo do cancelamento (parágrafo acima).
  Recebimentos previstos (`:602-621`) são informativos de caixa e **não** alteram receita reconhecida.
- **Fator R** (`:481-484`): folha ÷ faturamento; acima de 28% a empresa fica no Anexo III (rótulo 6%),
  abaixo cai para o Anexo V (rótulo 15,5%). São **rótulos de exibição**, não entram em conta.
- **Custo de pessoal** (`_salary_cost`, `:327`): mês cheio → soma real dos `SalaryPayment` se já
  gerados; período fracionado ou mês não gerado → pro-rata do salário vigente ÷ 30. Salários com
  `payment_type == 'comissao'` são excluídos, senão a comissão contaria duas vezes.
- O dashboard calcula três visões: realizado (eventos ocorridos, com custo fixo), projetado (futuros,
  **sem** custo fixo) e total (`:459-462`).

### Planilha de Pagamentos (`pagamentos()`, `routes.py:1120`)

Une 6 fontes num único `items[]` com formato comum (`type`, `id`, `date`, `amount`, `status`,
`pix_key`, `is_future`): cachês de `EventRole`, salários, desembolsos de gastos, BV, comissões
agregadas por vendedor e contas recorrentes. Duas sutilezas: gastos com `paid_at_creation=True`
**nunca** entram (`:1139`); lançamento recorrente com status `registrado` (débito automático /
assinatura) nunca vira pendência (`:1075-1081`).

### Armadilhas

- ✅ **Hotfix 267c — comissão paga não volta pelo lote.** `liquidar_periodo` mexe só nas linhas
  abertas (`a_pagar`, `no_banco`) e as trava (`with_for_update`); a Planilha mostra o que já foi pago
  num item à parte (`<vendedor>:<AAAA-MM>:pago`, "— pago"). As quatro portas (API e Jinja, individual
  e em massa) passam por `comissoes_ops.liquidar_item_de_comissao`: o item pago só sai de `pago` pelo
  "Não pago" do **Superadmin**, com **motivo** (vai ao histórico de cada evento); em massa e no Jinja,
  nunca. A tela antiga de Comissões (por linha) também não tira de `pago`. Antes, o "Não pago" de um
  item misto devolvia a "a pagar" o que já tinha saído, e a ressincronização o recalculava pela venda
  de hoje — o vendedor aparecia devendo o valor cheio. O valor pago gravado e o lote são da 1e.
- ✅ **Feature 267 fechou os quatro defeitos abaixo.** Hoje a comissão exibida no evento vem de
  `comissoes_ops.comissao_exibida_do_evento` (0 se cancelado → linha real → regra canônica), a
  mesma função na API e no Jinja; e a liquidação, das quatro cópias, vem de
  `comissoes_ops.liquidar_periodo`, que usa a **mesma** expressão de ciclo que monta o item. O que
  segue documentado é o estado ANTERIOR — mantido porque explica o porquê das funções existirem.
  **No cancelado (feature 306)** o número da tela não sai desta função: o detalhe da API não manda
  `kpi` (ele contaria a devolução como custo e o BV cheio) e mostra a comissão do retido, do bloco
  `cancelamento` (`cancel_ops.resumo_cancelado`). O zero continua na função, porque sem ele o fallback
  inventaria a comissão cheia de uma venda que não houve; a tela Jinja do evento cancelado mostra esse
  0 (P-28, dívida no `docs/05`). A linha real ignora a comissão própria do novo 1º dia, marcada na
  passagem (`NOTA_COMISSAO_PROPRIA_DO_DIA`).
- **A comissão tem 4 implementações divergentes.** `routes.py:120` (a completa),
  `app/api/agenda_read.py:245` (`_compute_kpi` — desconta BV mas ignora EducaManto, Loja Virtual e
  `receives_commission`, e usa **2%** de padrão), `app/calendar/routes.py:1752` (idem) e o filtro SQL
  de `comissoes_ops.py:183`. **A tela de detalhe do evento pode mostrar um número que o Financeiro
  nunca vai pagar.**
- **O "mês da comissão" muda conforme quem pergunta** — e isso é um **bug ativo**: a montagem do item
  usa `coalesce(payable_from, sale_date)` (`:1029`) mas a marcação de pago filtra só por `sale_date`
  (`:1245-1247` e `app/api/financeiro_write.py:213-215`). Comissão EducaManto vendida em janeiro com
  evento em março aparece no ciclo de março e, ao ser marcada como paga, atualiza **0 linhas**: o
  botão clica e nada acontece.
- **`set_payment_status` está duplicada linha a linha** entre `routes.py:1206` (108 l.) e
  `app/api/financeiro_write.py:52` (139 l.) — mesma árvore de 6 tipos de item, mesmos textos de
  auditoria com "(API)" no fim. E o docstring de `financeiro_write.py:3` afirma o contrário
  ("Reusa, sem duplicar…").
- **A view Jinja `comissoes()` (`:1603`) não aplica o filtro `_sem_loja_virtual`** que a API aplica
  (`comissoes_ops.py:166`): a tela Jinja lista comissões de Loja Virtual que a tela React esconde.
- **Dois relógios no mesmo módulo:** `dashboard()` usa `datetime.now(TZ_SP).date()` (`:412`) enquanto
  `set_payment_status` grava `paid_at = date.today()` (`:1251`) e `comissoes()` usa `date.today()`
  (`:1607`). Em produção (UTC), depois das 21h de Brasília a data sai um dia à frente.
- **Constantes fiscais moram no meio do arquivo de rotas** (`:258-261`: `DEFAULT_TAX_RATE`,
  `DEFAULT_FATOR_R`, `FATOR_R_RATE_LOW/HIGH`), longe de `app/constants.py`, e nada diz de onde vem o
  corte de 28% nem quando revisar.

### Invariantes que valem para todo relatório financeiro

1. **Satélites nunca são linha própria.** Venda e comissão vivem só no líder; os cachês entram via
   `_group_cost`. Esquecer o filtro `not e.is_satellite` conta a venda várias vezes.
2. **Permuta/cortesia não gera receita, mas gera custo** — o cachê sai do CPV e entra em Marketing.
3. **BV é repasse a terceiro**, nunca receita.
4. **Loja Virtual não comissiona.**
5. **Comissão paga (ou no banco) é histórico** — nunca reescrita por recálculo.
6. **O cancelado entra pelo que ficou, no mês do cancelamento** (feature 306). O **retido** (pago −
   devolvido do grupo, nunca negativo) entra na receita, o imposto informado nos impostos, o BV do
   retido no custo e a comissão do retido nas comissões — nas DREs Realizado e Total, na API e no
   Jinja, ao centavo (a cascata, acima) —, e o retido soma na Tendência do mês do cancelamento. A venda,
   os cachês e o evento do cancelado não aparecem no mês do evento, e o Projetado não muda. Fonte única
   da DRE, do Dashboard Comercial, de `/admin/desempenho` e da página de Cancelamentos:
   `cancel_ops.cancelados_do_periodo` (pela data de `cancelled_at`, fora a Loja Virtual) sobre o resumo
   em lote `resumos_cancelados`; nenhuma tela refaz a conta. Só o regime `venda` e o `legado` (cancelado
   de antes da 306: comissão 0, imposto 0, BV só o pago) trazem dinheiro; `satelite` e `dia` entram com
   zero e não contam em `n_cancelados`, que conta vendas, não dias — o que a Manto retém do dia cortado
   já está na venda nova do principal, no mês do evento. Cancelado sem venda, sem pago e sem devolvido
   fica fora; o de venda sem pagamento conta (na contagem, no painel e no BV pago do custo). O
   retido conta como venda do **vendedor congelado** (total vendido, Top Vendedores, desempenho, ficha
   da cliente) e a comissão do retido na comissão prevista do **beneficiário congelado**; ticket médio,
   eventos fechados e desconto concedido contam só venda viva.
7. **A devolução de cancelado nunca é gasto na DRE.** `dre_ops.gastos_extras_do_periodo` (a conta única
   da API e do Jinja) tira dos gastos extras toda devolução ligada a evento cancelado, de qualquer
   regime — a do dia cortado e a lançada antes do ato inclusive —, porque ela já está descontada no
   retido; a multa ao elenco e a devolução de evento vivo continuam gasto. A devolução é reconhecida por
   categoria + evento + aprovação (`cancel_ops.filtro_devolucao`), nunca pelo tipo de destinatário, que
   a tela edita. Ela nasce como Gasto Extra **aprovado** e a pagar e fica **travada** nas seis portas de
   Gastos Extras: valor, data, categoria, vínculo e exclusão só mudam pelo "Alterar devolução" (409
   `devolucao_travada`, `gastos_ops.GastoLockedError`); nome, PIX e descrição são livres, e o estado de
   pagamento é da Planilha.
8. **Comissão do cancelado = cheia × retido ÷ venda, com teto na cheia**
   (`comissoes_ops.comissao_do_retido`, pela mesma conta de proporção do BV, `quote_ops.bv_que_acompanha`:
   retido a um centavo da venda vale a cheia). A cheia tem uma definição só, `comissao_cheia_do_evento`:
   o portão do beneficiário (Loja Virtual, sem beneficiário, `receives_commission` falso ou
   cortesia/permuta → 0) sobre `_base_da_comissao`, o corpo intocado de `_event_commission` — a comissão
   do evento vivo não mudou número. A **taxa** do ato fica congelada e não acompanha a padrão das
   Configurações; só a correção da taxa do próprio cancelado a troca. A reconciliação
   (`reconciliar_comissao_do_cancelado`) mantém, por beneficiário, Σ(a pagar + no banco + pago) = alvo —
   a comissão do retido para o beneficiário congelado, 0 para todo outro com linha viva no evento: a
   `a_pagar` mais antiga recebe a falta no lugar, sem mudar de data, e as outras são canceladas; sem
   `a_pagar`, nasce uma linha de ajuste (±, `original_id` = a paga que ela acerta, o motivo de
   `MOTIVOS_AJUSTE_COMISSAO` no começo da nota) no **primeiro repasse aberto** de quem recebeu
   (`primeiro_repasse_aberto`: nos dias 1 a 5, o mês anterior, se ele ainda tem ali linha que abre
   ciclo; senão o corrente; nunca reabre ciclo liquidado). A sincronização (`_sync_commission_payment`)
   relê `cancelled_at` e não toca linha de evento cancelado, e nunca toma um ajuste (nem a comissão
   própria marcada na passagem) por "a comissão do evento".
9. **BV do retido.** O BV a pagar do cancelado vale BV cheio congelado × retido ÷ venda, com teto no
   cheio — calculado na leitura, nunca gravado; zero some da Planilha. BV pago ou no banco **nunca é
   reescrito nem escondido**, em regime nenhum: fica pelo valor pago (`event_cancellation_bvs.paid_amount`,
   gravado no ato ou quando a Planilha o marca) e, desfeito o pago, volta ao proporcional. Fonte única:
   `cancel_ops.bv_da_planilha` (Planilha nova e antiga, resumo e custo da DRE). Na **Planilha** o BV
   fica no mês do **evento**; na **DRE**, entra no mês do cancelamento. Marcar BV, nas duas Planilhas,
   passa por `cancel_ops.marcar_status_do_bv`, que trava o evento antes do acréscimo: valor esperado
   diferente → 409 `valor_mudou`; BV que não está a pagar → 409 `bv_nao_esta_a_pagar`. A multa ao elenco
   não mexe no BV, e corrigir a venda ou a taxa não muda o BV cheio congelado.
10. **Congelado: nada se recalcula da venda viva.** No ato, `event_cancellations` guarda venda, cheia,
    taxa, custo de cachês da EducaManto (`commission_cost`), beneficiário, vendedor, nota e imposto, e
    `event_cancellation_bvs`, recebedor, PIX e BV cheio de cada BV. Pago e devolvido **nunca** são
    congelados: são lidos ao vivo, somando os ids do grupo por consulta (`cancel_ops.ids_do_grupo`,
    nunca `leader.satellites`), para que corrigir comprovante ou devolução refaça as contas. Toda
    correção do Superadmin refaz retido, comissão e BV do retido na mesma transação, a partir do
    congelado (`reaplicar_cancelado`; na aba Comercial e nos acréscimos, `recongelar_do_comercial`
    recalcula a cheia pelos insumos congelados); o comprovante não recalcula a cheia, para que
    Configurações mudadas depois do ato não alcancem o cancelado. Trocar o vendedor passa o retido e a
    comissão do retido ao novo; o antigo devolve o que recebeu, no primeiro repasse aberto dele.

---

## 3. Gastos — o modelo a copiar

`gastos_ops.py` (879) + `routes.py` (507). **É a referência do padrão routes-finas + ops**: ops puro e
completo, rotas finas, API importando o mesmo ops. O docstring do módulo documenta até a dívida
pendente (o re-export de `ensure_recurring_entries`).

- **Gastos extras** (`SpecialExpense`): criar → aprovar/rejeitar (`:283`, `:295`).
  `paid_at_creation=True` marca gasto quitado no ato (PIX direto) e o exclui da planilha. Pode ser
  vinculado a evento (`link_expense_to_event`, `:325`) e então vira custo do evento.
- **Contas recorrentes** (`RecurringExpense` + `RecurringExpenseEntry`): `debito_automatico` e
  `assinatura` geram lançamento `registrado` automaticamente (`ensure_recurring_entries`, `:445` —
  geração preguiçosa idempotente, serializada por `pg_advisory_xact_lock` por mês — hotfix 271; a `UNIQUE(recurring_id, month_ref)` caiu na 121 porque o pagamento programado gera 2 lançamentos/mês); `variavel` espera
  alguém preencher o valor e vira alerta na home a partir do vencimento (`recurring_alerts`, `:482`).
- Vencimento: dia do mês **clampado no último dia** (`_clamp_day`, `:417` — dia 31 num mês de 30 vira
  30) ou, para frequência semanal, a primeira ocorrência do dia da semana dentro do mês ∩ vigência
  (`_weekly_first_date`, `:423`).

⚠️ Usa `date.today()` em ~10 pontos, não `now_sp()`.

---

## 4. Loja de Interações Virtuais (features 205 e 310)

`app/marketing/virtuais_ops.py` (2.325 linhas na auditoria; ~3.290 depois da 310). **É o melhor código documentado do
repositório** — os docstrings explicam consistentemente o *porquê*. É também um balde por camada: ~6
responsabilidades técnicas distintas num arquivo (ver `docs/05`).

### O fluxo da venda, ponta a ponta

**`reservar()` (`:775`) — a ordem das etapas é a regra:** duplo clique (mesmo `client_token` devolve o
pedido existente) → valida ficha → confere limites anti-abuso → **trava o slot** (`_travar_slot`,
`:747`, `SELECT … FOR UPDATE`) → grava o pedido → **commit** → **só então** fala com a InfinitePay
(`_gerar_link_pagamento`, `:898`). Falar com a operadora antes de travar deixaria a janela aberta
durante a chamada HTTP; travar durante a chamada seguraria uma linha do banco por segundos. Se a
operadora falhar, a reserva é desfeita e o horário volta (`:889-893`). Desde a 310: com o pagamento
desligado ou sem configuração, `reservar` levanta `VirtuaisPagamentoFechadoError` (503) **antes** de
qualquer trava; o `client_token` só devolve o pedido anterior se horário, formato, presente e criança
forem os mesmos (`_mesma_reserva`); o horário precisa começar a mais de 2 h; e o vídeo gravado trava
a campanha e conta as reservas ativas como vagas ocupadas.

**Anti-abuso (`_checar_limites`, `:705`):** (a) um telefone não pode ter duas reservas ativas — mas o
erro carrega `existing_order_token` para a família **retomar** o próprio pedido, não bater numa
parede; (b) teto por `origin_hash` (hash de IP+UA, nunca persistido cru, `hash_origem`, `:610`).
Desde a 310 o IP é o de `ip_do_cliente()` (o que a borda do Render viu, informado pelo Node), não o
`X-Forwarded-For` cru, e pedido que morreu por recusa da operadora (`payment_link_error`) não conta
no teto — a família não é barrada por culpa nossa.

**Soft lock de 15 min** (`VIRTUAL_SOFT_LOCK_MINUTES`), contado da criação, dentro da transação que
trava o slot.

**Aviso de pagamento — a invariante mais importante da feature: o corpo do aviso não decide nada.**
A InfinitePay **não assina webhooks**, então o payload só identifica o pedido; quem autoriza é a
reconsulta em `ipc.consultar_pagamento` **com os identificadores deste aviso**. Desde a 310 a rota
só grava e responde: `registrar_aviso` grava a linha `pendente` (a reentrega de aviso **sem**
desfecho final volta para a fila; com desfecho final é ignorada) e uma thread curta chama
`processar_aviso`, que reivindica a linha (`_reivindicar_aviso`, UPDATE condicional no molde do
`claim_sweep`), reconsulta e entrega a `decidir_pagamento`. Segredo errado responde 404 e grava o
resumo **sem** `transaction_nsu`. Todo o resto responde 200: 400 faria a operadora reenviar em loop.

**`decidir_pagamento()` — a única regra que transforma pagamento provado em venda ou devolução**
(feature 310, spec R-01). Aviso, retorno do checkout e varredura chamam a mesma função; a reconsulta
acontece antes, fora de qualquer trava (HTTP nunca segura linha do banco). Dentro dela, em ordem:
(1) trava e relê o pedido (`_travar_pedido`, `populate_existing` — sem ele a decisão saía sobre
leitura velha e um pedido pago voltava a expirado); (2) estado: pago com a mesma cobrança =
`duplicado`, pago com outra = devolução `pagamento_em_dobro`, cancelado = devolução
`pagamento_sem_pedido_ativo` (as duas sem mexer no pedido); (3) valor por `paid_amount` — ausente ou
menor que o total = `divergente`, sem venda e sem devolução automática; sobrepagamento vale; (4) só
então grava `transaction_nsu`/`invoice_slug`/`receipt_url` no pedido; (5) trava o horário: de outro
pedido, travado ou vendido = devolução de conflito; começa em menos de 30 min = `horario_passou`;
(6) vídeo: trava a campanha, `recorded_sold >= capacidade` = `sem_vaga_de_video`; (7)
`_efetivar_no_banco` e commit; (8) `_pos_venda`: Google e e-mail, fora das travas.

**Efetivação (`_efetivar_no_banco` + `_pos_venda`)** — a venda nasce inteira no banco num commit:
`CalendarEvent` com `google_event_id = 'virtual-local-<nsu>'` (`GOOGLE_ID_LOCAL_PREFIX`), pré-escala
talento+figurino (`_pre_escalar`), slot `vendido` **com `order_id` do dono**, baixa de estoque de
gravado, `VirtualMediaDelivery` com prazo, presente 3D **na mesma fila que a equipe já opera**
(`_injetar_presente_3d` → `impressoes3d_ops.add_event_gift`). Depois do commit, `regerar_sala` cria o
evento no Google (marcado com `manto_virtual_nsu`) e o e-mail sai. Falha do Google não desfaz nada:
`meet_pending` e a varredura retenta a cada 10 min até o horário (alerta com menos de 6 h).
O antigo `efetivar_pedido()` saiu na 310: a única entrada da venda é `decidir_pagamento` → `_efetivar_no_banco` + `_pos_venda`.

**`expirar_reservas()` — antes de liberar um horário vencido, reconsulta a cobrança** (desde a 310
com os identificadores do pedido ou, na falta, os do aviso mais recente com o segredo certo para o
mesmo `order_nsu`). Pedido sem link libera direto. Pago → `decidir_pagamento` (`origem=varredura`);
pago com valor errado → libera com `unverified_reason='divergente'`. "Não sei" (operadora fora,
travada) **retém o horário de fato** (`_reter_horario` estica o `locked_until` do slot) por 3
tentativas (minutos 0, 1, 2); esgotadas, libera com `expired_unverified=True` e
`unverified_reason='nao_sei'` — o pedido entra em "a conferir", e o flag muda o motivo de uma
devolução posterior (`conflito_sem_confirmacao`), porque quem liga reclamando precisa ouvir "a
operadora não confirmou a tempo". `nao_pago` ou `nao_encontrado` liberam na hora. Cada pedido é
isolado: erro num não aborta o lote.

**`claim_sweep()` (`:971`)** — UPDATE condicional atômico em `site_settings.virtual_sweep_at`: só um
worker do gunicorn ganha o ciclo. `ciclo_de_varredura()` roda as rotinas — desde a 310 quatro:
reservas, avisos (`reprocessar_avisos`), salas e prazos de vídeo — com try/except **por rotina**,
para uma caída não esconder as outras.

**Avisos à família (`_enviar_aviso`):** a trava de "no máximo um por pedido e tipo" é o **banco** —
grava `VirtualOrderNotification` antes de disparar e deixa a `UNIQUE(order_id, kind)` decidir.

### Máquina de estados do pedido (feature 310)

```text
reservado ──link ok──▶ aguardando ──decidir_pagamento: paga + confere + horário ok──▶ pago
   │                       │                  └─ horário tomado / passou / sem vaga ─▶ cancelado (+ devolução)
   │ link recusado         │ trava venceu; reconsulta nao_pago ou nao_encontrado ─▶ expirado
   ▼                       │ trava venceu; "não sei" esgotado ─▶ expirado (unverified_reason=nao_sei → a conferir)
expirado ◀─────────────────┘
expirado  ──pagamento atrasado provado──▶ decidir_pagamento (mesma regra: pago OU cancelado + devolução)
pago      ──"Cancelar e abrir devolução" (equipe)──▶ cancelado (+ devolução desistencia)
pago      ──segunda cobrança provada──▶ pago (+ devolução pagamento_em_dobro)
cancelado ──pagamento provado──▶ cancelado (+ devolução pagamento_sem_pedido_ativo)
```

Com o interruptor desligado nenhum pedido nasce (`reservar` → 503 antes de travar); os que já
existem seguem a máquina normalmente.

### Máquina de estados do aviso de pagamento (feature 310)

`state`: `pendente` → `processando` (claim de `_reivindicar_aviso`, `attempts + 1`) → `decidido`.
Desfecho final (`efetivado`, `devolucao_aberta`, `conflito`, `duplicado`, `divergente`, `orfao`,
`token_invalido`) fecha a linha; não final (`retido` = operadora fora ou erro na decisão;
`pendente_prova` = reconsulta não disse "pago", pode ser atraso de propagação) devolve a linha a
`pendente`. `reprocessar_avisos` retenta nos minutos 0/1/2 e depois a cada 10 min; com 48 h de idade
a linha vira `decidido` com o desfecho não final e aparece em "Pagamentos a conferir". `divergente`
e `orfao` também aparecem lá e tocam o sino.

### Invariantes do pagamento (feature 310 — o `verify_310` confere)

1. **Uma só função decide** se pagamento vira venda: `decidir_pagamento`. Aviso, retorno e varredura
   chamam a mesma; nenhum caminho efetiva por conta própria (era na varredura que nascia a venda
   dupla).
2. **Ordem de travas: pedido → horário → campanha**, em reserva, liberação, varredura, aviso,
   retorno e cancelamento pela equipe. Nenhuma chamada externa (InfinitePay, Google, e-mail) dentro
   de trava de linha.
3. **No máximo um pedido `pago` por horário**, e horário `vendido` aponta (`order_id`) para o pedido
   pago dele. Liberar outro pedido nunca solta horário vendido.
4. **A venda grava no banco antes do Google e do e-mail.** A disputa se decide no commit; quem perde
   não deixa evento órfão no Google, e a falha do Google não desfaz a venda.
5. **`nao_encontrado` ≠ "não pago".** É o `200 {"success": false}` da operadora (ou 404): ela não
   achou cobrança paga com aqueles dados. No aviso volta para a fila como `pendente_prova`; na
   varredura, sem identificadores, é abandono de checkout e libera. Só `paid: false` com a cobrança
   identificada é "não pago".
6. **Indisponível retém.** "Não sei" (timeout, 5xx, resposta ilegível, trava local) nunca libera nem
   cancela na hora: o horário fica travado e o aviso fica `retido`; só depois das tentativas o pedido
   sai como `nao_sei` — para "a conferir", nunca em silêncio.
7. **"A conferir" nunca é abandono de checkout.** Entram só aviso divergente, órfão ou esgotado,
   pedido liberado por operadora fora ou por valor divergente e recusa de link. Pedido que expirou
   sem aviso nem retorno expira como na 205 e não entra.
8. **Pago nunca regride.** `_liberar_reserva` relê com trava e só mexe em `reservado`/`aguardando`;
   pagamento novo de pedido pago vira devolução sem tocar no pedido; sair de `pago` só pelo
   "Cancelar e abrir devolução" da equipe.
9. **Todo pagamento provado termina em `pago` ou numa `VirtualRefundRequest`** — exceto o valor
   divergente, que fica em "a conferir" para uma pessoa decidir.
10. **Identificador só depois da prova.** `transaction_nsu`, `invoice_slug` e `receipt_url` vindos do
    aviso ou do retorno só vão para o pedido depois de a reconsulta com eles provar o pagamento: um
    aviso forjado não contamina a reconsulta do verdadeiro.
11. **`recorded_sold <= recorded_capacity`**: reserva ativa de vídeo ocupa vaga enquanto a trava vale,
    e a efetivação confere o teto com a campanha travada.

### Regras de ouro do módulo

- Tudo em `Decimal` de reais aqui dentro; **centavos só existem em
  `app/integracoes/infinitepay_client.py`**, que distingue `InfinitePayIndisponivel` ("não sei") de
  `InfinitePayError` ("falhou") — é essa distinção que permite tratar "não sei" como "segura o
  horário". Desde a 310 a reconsulta devolve `resultado` (`pago`, `nao_pago`, `nao_encontrado`), e
  `InfinitePayTravada` é subclasse de "não sei": travado, nada é efetivado nem cancelado.
- O cliente da operadora não importa Flask: a trava (`INFINITEPAY_SUPPRESS_CALLS`) e a
  `INFINITEPAY_API_KEY` são lidas em `_ipc_cfg()` a cada chamada e passadas por parâmetro; o default
  do cliente é travado.
- A feature usa **exclusivamente `now_sp()`** (importado como `agora`). Misturar com `utcnow()` faria
  sumir os horários das próximas 3h da lista.

---

## 5. Portal do Artista — o padrão a propagar

`app/talent_portal/` (2.333 linhas em 5 arquivos). **É a parte mais bem construída do repositório.**

| Arquivo | O que é |
|---|---|
| `portal_ops.py` (592) | agenda, convites, figurino, perfil, portfólio. `EDITABLE_TEXT_FIELDS`/`EDITABLE_DATE_FIELDS` (`:29`,`:53`) são a allowlist do que o talento pode editar de si mesmo |
| `portal_rating_ops.py` (453) | janelas de avaliação: `RATING_WINDOW=7d`, `RATING_EDIT_WINDOW=30d`, `COMMENT_REQUIRED_BELOW=4`, `SHOW_KEYWORDS` (decide sub-notas pelo **título** do evento) |
| `portal_account_ops.py` (266) | credenciais. `PASSWORD_RULES` (`:36`) é a fonte única de força de senha; `request_password_reset` (`:144`) é silencioso por design (anti-enumeração) |
| `portal_links.py` (51) | 40 linhas quase todas docstring de segurança |
| `routes.py` (974) | ⚠️ Jinja legado — **1 rota viva** (ver `docs/05`) |

### As 7 práticas a copiar

1. **Docstring de topo declara o modelo de RBAC em uma frase.** Ex. (`portal_agenda.py:4`): *"RBAC =
   'é o dono do recurso': toda consulta já filtra por `talent_id` da sessão (nunca aceita um id de
   talento vindo do cliente)"*. Seis linhas e o leitor sabe o modelo do arquivo inteiro.
2. **View = 5 a 10 linhas**: resolve o sujeito, chama o ops, traduz exceção, `jsonify`
   (`portal_ratings.py:59-75`).
3. **Exceção tipada com `.field`/`.status` + um tradutor de 3 linhas por módulo** (`_rating_error`,
   `portal_ratings.py:28`). Erro de validação chega no formulário React já apontado no campo certo,
   sem `if` na view.
4. **Ops puro recebe o sujeito já resolvido.** Quando precisa de algo do request (URL de reset, envio
   de e-mail), recebe **callback** — é assim que o módulo fica puro sem perder o envio.
5. **Constantes documentadas com `#:` no topo** (`portal_rating_ops.py:36-55`) viram a documentação
   das regras de negócio sem custar arquivo extra.
6. **Docstring de topo registra a divergência deliberada** (`portal_ops.py:138-142` explica por que
   `get_agenda` não é reusado pelo Jinja). Poupa o próximo agente de "consertar" o intencional.
7. **Contrato de endpoint no formato de `app/api/maps_read.py:21-34`** — linha `RBAC:` +
   `Query params:` + `Returns:` com o shape literal. É a **única** docstring de contrato completa do
   repositório e o molde que os outros 287 endpoints deveriam copiar.

### Segurança registrada em `portal_links.py:4-8`

**Nunca** `url_for(_external=True)` para link de reset de senha: `ProxyFix(x_host=1)` deixa o
atacante escolher o `Host` e receber um e-mail legítimo da Manto apontando para o servidor dele. A
base sai sempre da config.

---

## 6. Demais domínios

| Domínio | O que saber |
|---|---|
| **Talentos** | `talent_ops.py` (525) e `rating_ops.py` (496) existem e são bons, mas a view Jinja os ignora e faz query direta (`list_talents`, 153 l.). Pior cobertura de docstring dos domínios auditados (26/52). `get_talent_profile` (`talent_ops.py:202`) existe e **não é usada** pela view. Importação vem de Google Sheets (`importer.py`), dedupe pelo UNIQUE de `Talent.cpf` |
| **Figurino** | Fichas com peças, foto e impressão por evento. O sync com o Drive (`sync_drive_stream`, `routes.py:400`) é um endpoint **SSE** que emite progresso item a item; o parser do Google Doc mora em routes (`_sync_extract_name`:280, `_sync_extract_pieces`:312, `_sync_save_photo`:351) |
| **Clientes** | `client_ops.py` (310) — padrão ops+routes respeitado |
| **Revisão de mídia** | Material expira em **7 dias** (`EXPIRY_DAYS`, `review_ops.py:27`); `cleanup_expired_review_files()` remove o **arquivo** mas preserva registro e comentários (`file_removed=True`) — o histórico nunca se perde. Ao substituir material, a versão anterior vira snapshot (`snapshot_current_version`, `:203`) e os comentários ficam presos à versão em que foram feitos |
| **Formulários** | **Destino (feature 298)**: todo formulário que chega desde o corte (meia-noite de SP da `release_date`, ou 01/06/2026, comparada com `created_at` — que é **UTC ingênuo**, ao contrário do resto do sistema) tem destino: ligado a evento, encerrado com motivo, ou na lista da Home. As partições `sem_destino`/`com_evento`/`encerrados`/`historico` somam o total e servem Home e `/formularios` pela mesma regra (`formularios_ops.condicao_particao`/`destino_de`). Invariante: `closed_at IS NOT NULL ⇒ event_id IS NULL`; ligar desfaz o encerramento; evento **cancelado** mantém o vínculo, evento **excluído** (ou desvincular) devolve à lista. **Núcleo único de vínculo**: todo caminho passa por `apply_event_link` (cliente nos dois sentidos sem trocar ninguém quando divergem; `event_link_locked` só em decisão humana; aviso do sino lido para todos) — até a 298 três caminhos gravavam `event_id` à mão, e o segundo vínculo é 409 em todos (no `POST /api/events`, antes do Google, com o formulário bloqueado). Auto-vínculo resposta → evento (`formularios_ops._attempt_auto_link`, desde a 298 pelo núcleo com `decisao_humana=False`; ignora formulário encerrado) é a regra mais sutil do domínio: (1) exatamente um evento real na data, sem contradição de telefone; (2) telefone que resolve empate, ou aponta para um único evento futuro. **Nunca força vínculo ambíguo** — marca para revisão manual. Roda também no ciclo de sync da agenda (`calendar/sync.py:91`), para cobrir o caso do evento só existir depois da resposta. Desde a **266** há um irmão para cliente (`attempt_auto_link_client`): telefone que bate com exatamente uma ficha (`Client.phone` é UNIQUE) grava `client_id` + `client_link_source='auto_phone'`; desde a 298 roda **antes** do vínculo de evento (senão o núcleo levaria a cliente do evento e o preenchimento da ficha nunca rodaria). ⚠️ Ele roda **só no envio**, nunca no `retry_auto_link_pending` — o filtro de lá é `event_link_locked`, que não sabe nada sobre cliente, e religaria a cada ciclo o vínculo que a comercial desfez |
| **Impressões 3D** | `impressoes3d_ops.py` (573) — estágio 3, 100% de type hints, 1 função sem docstring em 24. Consumido por outros domínios (a loja virtual injeta presentes aqui). O pacote não se chama `3d_impressions` porque identificador Python não começa com dígito (documentado no `__init__.py`) |
| **Marketing** | `marketing_ops.py` (566): calendário editorial, metas de frequência (`goal_health`, `:440`, compara o intervalo alvo com o último post publicado) e ponte para o módulo de Revisão (`attach_review_space`, `:317`). Desde a 204b a relação post↔tema é **N:N** via `marketing_post_temas` |
| **Orçamento** | `calculate_quote` (`quote_ops.py:105`) tem **~540 linhas** — a maior função do repositório. Produz as 4 faixas de duração. Regras não óbvias: adicional noturno de R$50 por artista/coordenador a partir das 19h somado **DEPOIS do markup** (linha `pos` da memória — o comentário antigo dizia "pré" e estava errado); markup diferente para show e receptivo; maquiador com tabela progressiva; transporte com adicional fora de SP proporcional a colaboradores × km. **Data especial (feature 307)**: a tabela de preços tem faixas por data (`datas_especiais`, padrão `natal` = 24 e 25/12); `settings.faixa_especial(event_date)` decide pelo recorte `MM-DD` da data do evento (nunca por `datetime` com fuso), e com faixa o markup é o dela para qualquer produto, Noel/Ajudante/Coordenador levam o cachê da faixa e os demais sobem ao `piso` — regra numa fonte só — `pricing.cache_na_faixa` e os getters com `faixa=`, usados pela venda e pelo **teto das vagas** (`_compute_performer_caches`; `markup_vigente` só na venda) —, teto que segue a data do **evento** na criação e no vínculo 273 (`orcamento_evento_ops.data_do_evento`). Invariantes: sem faixa a conta é byte a byte a de antes; a faixa age antes de acréscimos/NF (a conta inversa da 305 continua válida); o EducaManto remove `event_date` antes de chamar `calculate_quote`; `_migrate` roda dentro do `try` de `load()` — exceção ali devolve os DEFAULTS do código para a tabela inteira, por isso o bloco é lido na defensiva. **Produtos de tabela (feature 309)**: a Visita Mágica é vendida pelo preço da tabela de venda (`pricing_config.produtos`, preço FIXO por visita, `por_faixa` nas datas especiais), não derivada dos cachês — a 307 tinha posto "Papai Noel" em 712 para `(712 + 250) × 2,6` dar 2.500 e esse número virava o TETO da vaga; a 309 devolve 600/270 à tabela ("cachê é cachê") e põe o preço no produto. Fonte única `app/orcamento/produtos.py` para a venda e para o teto: `aplicar`/`preco_do_produto` (preço da faixa; sem preço na faixa → estimativa `Σ cachês × fator × markup`, marcada em `quote.avisos`), `split_coordenadores(coordenador_qty, produtos) → (total, da_formula, inclusos)` (o coordenador do produto não é cobrado em dobro — `total = max(qty, inclusos)`), `incremento_make` (a make do Noel já está no preço; o avulso maquiado paga só o degrau seguinte da tabela; UM Maquiador por orçamento), `labels_de_personagem` (team_lines/personagens), `noturno_do_produto` (só com `inclui_noturno: false`). Na conta: o produto entra DEPOIS de "= Após markup" e ANTES de brinde/noturno/técnico/maquiador/transporte/acréscimos/NF — assim BV % e NF incidem sobre ele, o markup nunca o multiplica, e a conta inversa da 305 continua válida; é igual nas 4 colunas (não escala com a duração) e na régua >4h fica fixo (`total_na_duracao(total_4h, produtos_total, h, acrescimos, nf)`: a parte do produto, inclusive o seu % e a sua NF, é subtraída, o resto é regrado por hora e ela volta — usada pela venda, pelo prefill e por `_total_da_duracao`/`fator_regua` no evento); personalizado "valor final" vence tudo e "multiplicador" não multiplica o produto (`cache_base × mult + produtos_total`, validação olha a base). **A ordem da conta e o desconto (feature 313)**: uma função só, `quote_ops.aplicar_acrescimos(base, acrescimos, nota)`, para 1–4 h e a extra (`_preco_extra`) — base (apresentação + transporte + produto) → acréscimos em R$ **uma vez** (não escalam com as horas) → % que não são BV sobre a base → BV em % sobre o valor com os acréscimos (o BV em R$ entra uma vez, nesse passo) → nota → **desconto**, o último passo, sobre o total (`desconto_pct`, ou o % exato achado pelo `desconto_valor` de uma duração, igual nas outras). O PIX à vista vale o maior entre 5% (`PIX_PCT_PADRAO`, de `AVISTA_FATOR`) e o desconto, sempre sobre o cheio; o BV a repassar acompanha o desconto e o PIX por `bv_que_acompanha`. A regra vale só para orçamento com `versao_conta: 2` no snapshot — **todo leitor do salvo pergunta pela marca** (`orcamento_evento_ops.snapshot_v2`, que também cruza `bases` × `brutos`), e sem ela segue a conta de antes: 17 dos 2.484 orçamentos do espelho mudariam pela regra nova (9 BV + "Outro", 8 duração extra + R$ — as exceções da Q7, `gabarito_paridade.py`), os outros saem byte a byte. O texto do % é `texto_do_percentual` (uma casa, **para baixo**) no servidor e `textoDoPercentual` no navegador, a mesma regra no selo do valor de venda. O núcleo continua em float (`round(x, 2)`): a paridade com os orçamentos salvos exige a mesma aritmética — dívida própria no `docs/05`. Só produto no orçamento (sem avulso e sem coordenador da fórmula) = UM valor (`show_1h` só, `total_custom` None, bloco único na mensagem e PIX único). **Teto das vagas**: `_compute_performer_caches` emite primeiro as vagas `character` dos produtos a partir das vagas **congeladas no snapshot** (`snapshot.produtos[].vagas` — editar o produto depois da venda não muda a composição; produto apagado = `cache_Nh = None` com nota, nunca 0), flat nas 4 colunas, cachê pela tabela vigente na data do EVENTO (600/270/250/250; 1.000/650/500/250 na faixa da 307), nota com `MARCA_PRODUTO`; depois os avulsos e os extras (coordenadores do produto → da fórmula → técnico → UM maquiador com `calcular_maquiador(Σ makes dos produtos + comuns avulsos, especiais avulsos)`); prefill = criação (pareamento posicional) e o vínculo 273 casa por nome. EducaManto faz `payload.pop("produtos")`. Invariantes: sem produto a conta é byte a byte a de antes (gabarito `verify_309_golden.json` no HEAD `6356b80`); `quote` sempre traz `produtos`, `produtos_total`, `coordenadores_inclusos`, `avisos` (é a presença da chave que diz ao React que o backend conhece produtos). **Ponto positivo:** `compute_show_pricing` (`pricing.py:9`) é explicitamente uma fonte única extraída de duplicação anterior — o padrão certo |
| **EducaManto** | Calculadora de pacotes educacionais: pessoas no transporte derivadas do pacote+elenco (`pricing_ops.py:70`), transporte por km/pessoas/dias (`:96`), arredondamento para cima na centena (`_ceil100`, `:141`). Conecta-se ao Financeiro pela regra de comissão EducaManto (§2, ramo 5) |
| **Contratos da ClickSign** (feature 317) | `app/contratos/` (`contratos_ops` puro, `sincronizar_ops`, `situacao_ops`) + cliente `app/integracoes/clicksign_client.py`. **Invariantes:** (1) **o contrato é da venda** — o principal do grupo ou o avulso; o documento e a marca manual são procurados em **todos os dias do grupo** (agrupar não move linhas) e a cobrança só sai do principal; (2) **a ClickSign é a fonte e o aviso não decide** — o webhook só dispara uma passada incremental (`filter[modified]` desde o marco) que reconsulta a API; segredo vazado não marca contrato como assinado; (3) **vínculo automático só com candidato único** (data do nome + telefone, chave DDD + 8 últimos, na ficha, nas contratantes ou no formulário ligado; tema desempata). Sem candidato, os sinais da **317b**, nesta ordem e só com venda viva única: mesmo telefone com a data a um dia; formulário do mesmo telefone e da mesma data já ligado a um evento (festa remarcada); e-mail no lugar do telefone; **tema por palavra** no dia (`contratos_ops.tema_por_palavra`, sem as palavras que não dizem a festa — cor, figurino, "festa", razão social; dia sem venda olha o anterior e o seguinte). A **venda cancelada certa liga sozinha** (317b, decisão do dono em 28/10 — o PDF não entra no evento cancelado); ligar à mão a cancelada continua recusado (312). Envelope **cancelado na ClickSign sem venda vai para `fora`**. O resto vai para "A conferir", e nunca se religa sozinho o par que a comercial desligou (`clicksign_desvinculos`); (4) **vigente** = o em processo mais recente; senão, um assinado vence qualquer cancelado (o reenvio duplicado que venceu não faz cobrar quem já assinou); (5) o PDF assinado entra uma vez (`anexo_pendente`) e o PDF automático não conta como "assinado à mão". **Dependência externa frágil**: o vínculo lê o **nome** que os fluxos com formulário da conta montam (`DDMMAAAA + (DD) NNNNN-NNNN + Tema`); se alguém mudar a personalização do nome no painel da ClickSign, tudo passa a cair em "A conferir" — visível, nunca em vínculo errado. A data no fluxo é texto livre (`DD-MM-AAAA`, `DDMMAAAA`, `DMMAAAA`) e a ClickSign devolve acento decomposto (normalizar NFC antes de ler) |
| **Feedback** | Avaliação da **cliente** sobre a equipe, via link público com `CalendarEvent.feedback_token`. **Não confundir** com `EventRating`, que é a avaliação do **artista** sobre o evento, feita com login pelo portal |
| **RH** | `app/rh/routes.py` são 33 linhas de casca Jinja; a lógica está em `app/api/rh_read.py`. É o único consumidor do RBAC por `has_permission` — e `rh.view` nunca é semeado (ver `docs/00` §4) |
| **Catálogo** | **INVARIANTE (feature 300): toda listagem carrega o acompanhamento de uma vez, nunca item a item.** As serializadoras (`_item_summary` do gerenciador e da vitrine, `_category_summary`, o laço dos avulsos em `list_catalog_characters`) tocam `images`, `categories`, `characters`, `figurino_sheet` e `as_character` por item, e **todos os relationships do catálogo são `lazy=True`** — sem `.options(selectinload(...))` na consulta, cada produto vira 4 a 6 idas ao banco (eram 1.846 no gerenciador e 917 na vitrine, com 458 produtos). ⚠️ A armadilha é `CatalogItem.cover_image` (`models.py:2156`): **não é coluna, é property sobre `images[0]`** — pedir "só a capa" carrega a coleção inteira de fotos daquele produto. Duas ordenações são explícitas de propósito, porque dependiam do plano de consulta e mudariam com o carregamento antecipado: nomes de categoria e personagens empatados em `position` ordenam por **`id`** — o que reproduz exatamente a ordem que a produção sempre serviu (0 de 458 mudam). ⚠️ **Não ordenar alfabeticamente**: o card da vitrine mostra só as 3 primeiras etiquetas, e a ordem alfabética trocaria as etiquetas visíveis em 123 produtos (pego na revisão pré-deploy da 300). A escolha da miniatura é do **cliente** (`assetUrl(url, { largura })`), nunca do banco: a resposta sempre devolve o caminho do arquivo original |

---

## 7. Núcleo transversal do backend

| Arquivo | Papel | Nota |
|---|---|---|
| `app/__init__.py` (662) | factory + infra de request | `create_app()` ocupa 341-662 e acumula 13 responsabilidades |
| `app/models.py` (2.577) | fonte única de schema, 68 tabelas | sem docstring de módulo nem índice; banners de seção só a partir da linha 1162 |
| `app/constants.py` (260) | apesar do nome, 88% constantes de features; RBAC na linha 231 | contém 2 funções de negócio: `event_requires_client` (`:17`) e `now_sp` (`:114`) |
| `app/config.py` (192) | `Config` → `Development`/`Production` por `FLASK_ENV` | `_db_url()` converte `postgres://` → `postgresql://`; `_suppress_mail()` (`:21-39`) impede e-mail real quando o banco é local; `_resolve_secret_key()` (`:42-82`) nunca usa chave fraca em produção |
| `app/storage.py` (376) | abstração de arquivo (local ou S3/R2 por `USE_S3`) | **exemplar em documentação.** `save_file` (`:160`) comprime imagem (máx 1200px, JPEG q85) e grava com nome UUID |
| `app/api_utils.py` (50) | envelope de erro + `api_login_required` | curto e perfeito |
| `app/money.py` (118) | `format_brl`/`parse_brl` | puro de propósito (sem Flask/DB), para poder ser importado no factory |
| `app/utils.py` (84) | `unaccent_lower_sql` (busca sem acento sem extensão), `json_for_script` (anti-XSS), `audit()` | ⚠️ `audit()` **não comita** — quem chama comita |
| `app/maps.py` (124) | Distance Matrix + Places | a chave nunca sai do servidor |
| `app/email_service.py` (707) | Flask-Mail + HTML por helpers | `send_async` (`:21-58`) empacota objetos ORM como `(classe, pk)` e recarrega dentro da thread — sem isso a sessão estoura |

**As 7 threads de background** repetem o mesmo esqueleto: talent-sync, calendar-sync,
review-cleanup, virtual-sweep, **email-bounce** (feature 219), **invite-reminders** (231) e
**backup-drive** (264) — as três últimas não constavam nesta contagem até a feature 266.
A diferença que importa: **calendar-sync, virtual-sweep, email-bounce e invite-reminders fazem
claim atômico** entre workers gunicorn; **talent-sync e review-cleanup não**. Review-cleanup
justifica (é idempotente — e desde a 272 o mesmo laço roda também a retenção das notificações,
`notificacoes_ops.limpar_antigas`, idempotente pelo mesmo motivo); talent-sync não justifica nada, e `app/talents/importer.py` lê
`ImportState.last_row` no início (`:179`) e grava no fim (`:343`) sem lock — dois workers
processam as mesmas linhas da planilha.

`invite_reminders.py` é o **molde para qualquer aviso por data** (janela de horário, máximo de
lembretes, claim atômico); nenhuma das 7 toca cobrança de cliente — ver a spec da feature 267.

**Link que sai por e-mail nunca vem do request nem de env não conferida** (hotfix 269b).
`PORTAL_URL` e `PUBLIC_BASE_URL` passam por `config._url_para_fora`: endereço local só é aceito em
processo que não envia e-mail de verdade, senão vale a constante pública (`PORTAL_BASE_URL` /
`PLATFORM_BASE_URL`) e o boot grita no log. Segunda camada em `email_service._send`: corpo com link
local não é enviado. Motivo: a env da produção estava com `http://localhost:5000` e o convite do
artista — e o link de redefinição de senha — apontava para lá.

**E-mail local é bloqueado por config, não por banco.** `SiteSetting.email_notifications_enabled` vem
ligado na cópia local do banco de produção; a trava real é `MAIL_SUPPRESS_SEND`
(`config.py:21-39`), checada antes (`email_service.py:538`).

---

## 8. Frontend

### Pacotes compartilhados

- **`@manto/api-client`** — `apiFetch<T>` é a **única porta** para `/api/*`: manda
  `credentials: "include"`, **omite `Content-Type` de propósito quando o body é FormData** (senão o
  boundary do multipart quebra) e traduz o envelope de erro em `ApiRequestError` com `.status` e
  `.fields`. `assetUrl(path)` detecta `http(s)://` e **não** prefixa, porque fotos legadas importadas
  do Drive já guardam URL absoluta (`client.ts:44-51`).
  **`createQueryClient()` define `staleTime: 30_000` e `refetchOnWindowFocus: false`** — é por isso
  que invalidação faltante **não se conserta sozinha**: o dado errado fica na tela.
- **`@manto/money`** — `formatBRL` devolve `"1.234,56"` **sem prefixo R$**. `MoneyInput` guarda valor
  numérico cru no state e string mascarada na tela; ⚠️ renderiza `<input>` **sem classe nenhuma** (o
  pacote não depende de `@manto/ui`), então o call site precisa vestir o campo.
- **`@manto/ui`** — 21 arquivos. Componentes e helpers com docstrings boas, **mas sem README/catálogo**
  (não existe nenhum `.md` em `frontend/`). Duas regras de acessibilidade que só existem em comentário
  e valem como regra do projeto: **`text-gold` reprova AA (3.25:1) — use `text-gold-ink` para texto**
  (`badge.tsx:19-21`); **`text-line` é token de borda de 1px, invisível como ícone (1.2:1) — use
  `text-muted`** (`portal/StarRating.tsx:46-49`).

### Invariantes do frontend

1. **Horário de parede.** Para preencher `<input type=date/time>` ou comparar datas, **recorte a
   string** (`lib/horaLocal.ts`: `dataDeIsoLocal`, `horaDeIsoLocal`, `hojeYmd`).
2. **RBAC é do servidor.** Ou o payload traz a chave (bloco ausente = seção não renderiza), ou traz
   `flags.<nome>`. Filtro de UI é conveniência, nunca fonte de verdade.
3. **Papel efetivo.** Com "Ver como" ativo, o SUPERADMIN conta **só** com o papel simulado
   (`agenda_read.py:127-133`; `navigation.tsx:66`). `useImpersonate` chama `invalidateQueries()` sem
   argumento — invalida tudo, de propósito.
4. **Escrita de evento devolve o `EventoDetalhe` inteiro.** `useEventMutation`
   (`lib/eventDetail.ts:14-23`) grava a resposta com `setQueryData(["event", eventId])` — a tela
   re-renderiza sem refetch e sem merge no cliente. **Todo hook novo de escrita de evento deve seguir
   isso.**
5. Arquivo do Flask sempre via `assetUrl()`; dinheiro sempre via `formatBRL`.
6. **Todo elemento fixo no topo soma a altura da faixa** "eventos sumiram do Google Agenda"
   (feature 303): 40 px, `sticky top-14 lg:top-0 z-[25]`, só quando ela está na tela. Quem gruda
   no topo ou rola até uma âncora lê `useFaixaSumidosVisivel()` (observer passivo — nunca um
   segundo hook com poll) e escolhe entre duas classes literais inteiras (a régua de abas do evento
   vai de `top-14 lg:top-0` para `top-24 lg:top-10`; as âncoras da Home, de `scroll-mt-16
   lg:scroll-mt-4` para `scroll-mt-28 lg:scroll-mt-14`). O `z-[25]` fica acima da régua (`z-20`)
   e abaixo da barra do mobile e do sino (`z-30`).

### Armadilhas já pagas (registradas no código)

- Modal centralizado: **flex, nunca `translate`** (`dialog.tsx:45-58`) — o Framer escreve `transform`
  inline e vence a classe; o bug atingiu 11 telas.
- O grid de duas colunas do detalhe do evento precisa de `[&>*]:min-w-0`, senão o card de casting
  estoura a viewport do celular (`EventDetailPage.tsx:24-31`).
- `AccordionRow.summary` **não pode conter elemento interativo** — ele é renderizado dentro do
  `<button>` de expandir; use `actions` (`accordion-row.tsx:7-14`).
- **Invalidação por prefixo do TanStack Query só alcança chaves FILHAS**: `["gastos-recorrentes"]`
  não invalida `["gastos-recorrentes-historico", id]`.
- **`/api/financeiro/pagamentos/set-status` é poliforme**: escreve em `CommissionPayment`,
  `RecurringExpenseEntry`, `SalaryPayment` ou `Role` conforme `item_type`. Qualquer mutação sobre ele
  precisa invalidar os **quatro** domínios de cache.
- `VideoPlayer` existe duas vezes com propósitos distintos (`apps/public` = catálogo MP4/Drive/Vimeo;
  `internal/components/revisao` = player com scrubber e marcadores de comentário). **Não é
  duplicação.**

### Onde mexer para X

| Quero | Faço |
|---|---|
| Tela nova no ERP | rota em `internal/src/App.tsx` + item em `lib/navigation.tsx` (com `isVisible`) + módulo em `lib/` + página em `pages/` — exceção: `/notificacoes` (272) não tem item de menu, a entrada é o sino |
| Avisar alguém de um fato (em vez de e-mail) | constante `KIND_*` + entrada em `DESTINATARIOS_POR_KIND` + `notificar_x()` em `app/notificacoes/notificacoes_ops.py` + uma chamada no ponto do fato (mesma transação quando o fato ainda não comitou; em rotina de fundo, quem comita é a rodada) |
| Algo sempre visível no shell (sino, atalho) | slot `headerActions` do `AppLayout` (`packages/ui`) — renderizado na linha da marca (desktop) e na barra superior do mobile |
| Campo novo no evento | tipo em `lib/agenda.ts` (`EventoDetalhe`) + seção em `components/EventDetail/` + mutação via `useEventMutation` |
| Componente compartilhado | `packages/ui/src/components/` + **export nomeado em `packages/ui/src/index.ts`** |

---

## 9. O que esta auditoria NÃO cobriu

Declarado explicitamente para você não confundir ausência com inexistência:

- **`app/admin/`, `app/auth/`, `app/cadastro/`, `app/catalogo/`, `app/cli.py`, `app/drive_migration.py`**
  não foram auditados em profundidade. Aparecem aqui só onde outro domínio os cita.
- **`migrations/`** (115 arquivos): só se verificou a cadeia de revisões e o head. O conteúdo das
  migrations não foi lido.
- **`seed.py`, `sync_worker.py`, `run.py`, `reset_beta.py`** e os scripts na raiz do repositório: não
  auditados.
- **`specs/`**: não auditado.
- **Testes e2e Playwright** de `apps/internal` e `apps/public`: existência registrada, conteúdo não
  auditado. `apps/portal` **não tem nenhum teste**.
- **Templates Jinja** (`app/templates/`): contabilizados por tamanho e alcançabilidade, não lidos.
- **Cobertura de segurança**: não houve revisão de segurança dedicada. Os pontos de segurança citados
  (allowlist de `/uploads`, `portal_links.py`, webhook não assinado, `origin_hash`) apareceram como
  subproduto da leitura, não de uma varredura sistemática.
