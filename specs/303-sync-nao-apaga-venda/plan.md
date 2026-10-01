<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: 303 — o sync não apaga evento com venda

**Branch**: `303-sync-nao-apaga-venda` | **Data**: 2026-09-30 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/303-sync-nao-apaga-venda/spec.md`

**Nota**: preenchido pelo `/speckit-plan`. A constituição (`.specify/memory/constitution.md`,
v3.0.0) é lida em tempo de execução — o Constitution Check abaixo é o que ela cobra.

## Resumo

Hoje a limpeza do sync apaga do banco todo evento que não aparece no Google Agenda no mês
sincronizado — com venda, comprovante, contrato e escala junto. A 303 troca isso por três regras:
(1) **ausência só vale confirmada** — antes de qualquer decisão, o sistema consulta o próprio evento
no Google, e o que mudou de data é movido, não apagado; (2) **evento com dinheiro fica** — ganha a
marca `google_missing_since`, segue valendo em tudo, e Superadmin e Comercial veem uma faixa fixa no
topo de todas as telas e um aviso no sino; (3) **o Superadmin devolve o evento ao Google** pela tela
do evento. O elenco vê "Evento em confirmação" no portal. Cancelar o evento marcado fica para a
entrega seguinte: nesta, ele não pode ser cancelado nem excluído.

Abordagem: o corpo de `_cleanup_stale_events` sai de `app/calendar/routes.py` para um núcleo novo e
puro, `app/calendar/sumico_ops.py` (a função antiga vira delegação, com o mesmo nome — há três
chamadores, dois verifies antigos que a chamam (`verify_205`, `verify_cancelamento_evento`) e um que
a substitui por dublê (`verify_168`)); uma função nova em `app/calendar/service.py`
consulta um evento com três desfechos (presente, ausente, inconclusivo) sem tocar a antiga; o sino
ganha um produtor novo, sem tabela; a faixa é um endpoint de leitura em módulo que já existe e um
componente no `AppShell`. Uma migration aditiva, de uma coluna. A pesquisa completa, com a revisão
adversarial de cada decisão, está em [research.md](./research.md) e em `pesquisa/`.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: Flask, SQLAlchemy, Alembic (migrations à mão), `google-api-python-client`
2.188 (já instalado; `HttpError.status_code`); React, TanStack Query 5, Tailwind CSS, shadcn/ui
(`@manto/ui`: `Badge`, `ConfirmDialog`, `AccordionRow`), Framer Motion, `@manto/api-client`,
`lucide-react`

**Armazenamento**: PostgreSQL — produção no Render; verificação contra `manto_local`. Uma coluna
nova e um índice parcial em `calendar_events` (ver [data-model.md](./data-model.md))

**Verificação**: `specs/303-sync-nao-apaga-venda/verify_303.py` contra `manto_local`, com o Google
substituído por um dublê que falha fechado; `cd frontend && npm run typecheck`; telas abertas no
Browser pane; portal em 375×812 e 320 px; `verify_205.py` rodado de novo depois da História 1

**Plataforma-alvo**: web — Render (Flask API JSON + 3 SPAs); staff em desktop e celular, portal em
smartphone

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: a faixa custa uma consulta de quatro colunas (três no payload) por minuto por aba de Superadmin
ou Comercial (uma única vez para os outros papéis); a limpeza faz uma consulta ao Google por evento
candidato — em regime, só adiamentos para mês posterior, sumiços novos e eventos marcados — e para
na primeira falha de rede (cada chamada ao Google pode levar até 60 s; o proxy corta em 180 s).
Pior caso do tempo a mais: uma consulta sem resposta (até 60 s) na reconferência e uma por mês — o
disjuntor é de cada rodada (research R4) — mais as consultas que respondem; isso se soma ao que o
ciclo já faz hoje (uma chamada de lista por mês, com o mesmo teto de 60 s). O claim do ciclo vale
600 s a partir do início (`sync.py:122-150`); se um ciclo passar disso, outro worker pode começar um
ciclo em paralelo, e a limpeza é segura nessa corrida (marca por `UPDATE` condicional, R6; evento
relido por id, R4). No "Limpar eventos fantasma" a requisição só responde no fim: se o proxy cortar,
a tela diz "Não foi possível concluir a ação", a limpeza termina no backend e o que ela fez se
confere em `/admin/logs` — risco que já existe hoje e que a 303 aumenta em uma consulta por candidato

**Restrições**: o `manto_local` tem o token real do Google — nenhum verify lê ou escreve na agenda
de verdade; escrita nova no Google nasce travada fora da produção (XIV); `routes.py` de calendar é
exceção histórica com imports tardios — nada é movido nem renomeado, só os toques listados abaixo;
campo novo de payload nasce opcional no TypeScript (backend e bundle sobem no mesmo push, em ordem
não garantida); o portal funciona de 320 a 430 px; a referência do app interno é 375 px

**Escala/escopo**: 1 coluna + 1 índice; 1 módulo de núcleo novo (~300 linhas, em funções de até ~30);
2 endpoints novos e 9 alterados; 3 componentes React novos (faixa, selo, banner do evento) e 1 no
portal; ~16 arquivos de backend e ~14 de frontend tocados; verify com ~35 cenários

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1 — sem violação sem justificativa.*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | Reusa `emitir`, `marcar_lidas_por_entidade` e `apagar_por_entidade` (sino); `total_recebido` (224); `sync_events` para aplicar data nova (sem copiar a regra); `_push_cabecalho_ao_google`; `_log_sync`; `_role_flags` e `_can_delete`; `insert_event`; `ConfirmDialog`, `Badge`, `AccordionRow`; o molde de polling do sino. Uma fonte para "marcado" (`filtro_marcados`), para "o que está preso" (`PresoAoEvento`) e para a situação (`CalendarEvent.situacao`). O núcleo novo **substitui** a fatia "cleanup" prevista em `docs/PLANO_EXTRACAO_CALENDAR.md` — registrado lá. |
| II. Padrões de código | Type hints e docstrings; `sumico_ops` fatiado em funções de até ~30 linhas e 3 níveis (`limpar_mes` + `_decidir_candidato`; `devolver_ao_google` + cinco helpers); situações, kind e desfechos como constantes; `ruff check` nos tocados, `ruff format` só no arquivo novo; TS sem `any`; zero CSS solto e zero `style` inline (a faixa tem altura fixa para o offset ser classe) |
| III. Camadas / API First | Núcleo em `app/calendar/sumico_ops.py`, puro (sem `flask.request`); views em `app/api/agenda.py` e `agenda_write.py` só com gate, chamada e serialização; nenhum módulo novo em `app/api/` (nada a registrar); nenhuma rota pública nova (nada em `BACKEND_PREFIXES`). `routes.py` de calendar recebe seis toques pontuais, nenhum move função |
| IV. Não quebrar o que funciona | Migration aditiva e nullable; campos de payload opcionais; `_cleanup_stale_events` mantém nome e entrada (os imports tardios e os verifies antigos continuam achando); `fetch_single_event` intocada (o Meet da Loja Virtual depende dela); `verify_205` ajustado e rodado de novo; mudanças de comportamento declaradas: depois de um erro de banco num mês, o `except` faz `rollback` e os meses seguintes passam a sincronizar (erro que não é de banco segue como hoje); e `_delete_event` passa a limpar ensaio-filho com histórico e avisos do sino em **toda** exclusão, inclusive o Excluir da 224 |
| V. UI/UX com feedback | Devolver usa `ConfirmDialog` com `pending`, erro dentro do diálogo e fechamento bloqueado durante a ação; mensagens em pt-BR sem erro técnico. **Exceção justificada** em Rastreamento de complexidade: a faixa não mostra skeleton nem erro |
| VI. Esteira (Nível 1) | Esteira completa na pasta `specs/303-sync-nao-apaga-venda/`. As entregas 2 e 3 nascem do `/speckit-specify`, cada uma com número novo (Regra Zero) — o texto delas está congelado em `entregas-2-e-3-rascunho.md` |
| VII. Living Spec | Spec reescrita em 30/09 antes deste plano: escopo da primeira entrega, regra do intervalo (FR-045), os requisitos que a pesquisa acrescentou (FR-039 a FR-044) e a tabela de cenários com os sub-cenários |
| VIII. Verify antes do núcleo | `verify_303.py` na fase Foundational, escrito sem importar nada que a 303 cria (coluna lida por SQL cru, rotas num dicionário), rodado vermelho com a saída em `verify_303_primeira_falha.txt`; lista fechada do que pode estar verde antes do núcleo: o chão (0 e 41), o 18 (a trava nasce no Setup), o 15, o sub-cenário "a lista inteira falha" do 13 e, do 7, só a afirmação de que o evento vazio é apagado. O 11 nasce vermelho inteiro: a rota de devolver ainda não existe, e o Comercial receberia 404, não 403 |
| IX. Dinheiro BRL | O corpo do aviso formata com `app.money.format_brl`; `PresoAoEvento` em `Decimal`; a faixa e o resumo da agenda não levam dinheiro |
| X. Mobile-first público | O aviso do portal é uma caixa de largura total, texto de 14 px que quebra linha, sem truncar; conferido em 320 e 375 px |
| XI. Framer Motion | Faixa e lista com `AnimatePresence`, 200–250 ms, e `useReducedMotion`; o texto "recriado à mão" usa `AccordionRow` |
| XII. Combobox / Maps | Não se aplica: nenhuma seleção nova |
| XIII. RBAC declarado | `GET /api/events/sumidos-google` — SUPERADMIN ou COMERCIAL pelo papel efetivo, vazio para os demais; `POST /api/events/<id>/devolver-ao-google` — `_can_delete()` (SUPERADMIN real); `/sync` segue sem gate e passa a poder retirar a marca — declarado; linhas em `docs/01` §4.3. O front não decide: `pode_ver` no corpo da faixa, `flags.can_delete` para o botão |
| XIV. Config / efeito externo | Trava nova `CALENDAR_SUPPRESS_EVENT_WRITES`, derivada do host do banco, com escape `CALENDAR_ALLOW_LOCAL_EVENT_WRITES`, no mesmo commit do devolver; nenhuma variável nova no painel de produção. Com a trava ligada, a devolução não faz nenhuma chamada ao Google (o sync, a limpeza e o "Sincronizar" continuam lendo). As escritas antigas sem trava viram dívida nomeada |
| Stack | Migration à mão `a7c3e91f4d28`, `down_revision = e5a1c7d93b20` (head conferido em 30/09; reconferir ao escrever — a 298b é da mesma onda); sem Jinja novo (um `elif` num wrapper Jinja vivo); sem segredo |
| Operação e Deploy | Não toca `startCommand`. Migration aditiva: ensaio `flask db upgrade && python seed.py` no espelho. Deploy à noite, num push só (o `render.yaml` redeploya os dois serviços; a ordem não é garantida). Contagem só leitura antes do `/speckit-tasks` e de novo no dia do deploy; teste do devolver em produção com evento descartável logo depois |

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/303-sync-nao-apaga-venda/
├── spec.md                          # a primeira entrega
├── plan.md                          # este arquivo
├── research.md                      # Phase 0 — decisões, com a emenda da revisão
├── data-model.md                    # Phase 1
├── quickstart.md                    # Phase 1
├── contracts/api-endpoints.md       # Phase 1
├── entregas-2-e-3-rascunho.md       # a spec de antes da divisão, congelada
├── pesquisa/                        # relatórios das nove frentes e da integração
├── checklists/                      # /speckit-checklist
├── tasks.md                         # /speckit-tasks
├── armadilhas.md                    # pegadinhas do código de hoje, por fase (lidas antes de cada fase)
├── contagem_pre_deploy.py           # só leitura: eventos passados com dinheiro fora do Google
├── verify_303.py                    # Princípio VIII — escrito antes do núcleo
└── verify_303_primeira_falha.txt    # a execução vermelha de antes do núcleo
```

### Código (caminhos reais)

```text
migrations/versions/a7c3e91f4d28_evento_sumiu_do_google.py   # NOVO — coluna + índice parcial
app/models.py                     # CalendarEvent: google_missing_since, índice, is_google_missing,
                                  #   situacao, situacao_desde
app/constants.py                  # SITUACAO_CANCELADO / _SUMIU_DO_GOOGLE / _EXCLUSAO_SOLICITADA
app/config.py                     # _suppress_calendar_event_writes + CALENDAR_SUPPRESS_EVENT_WRITES
app/calendar/service.py           # consultar_evento (novo, três desfechos); insert_event(all_day=)
app/calendar/sumico_ops.py        # NOVO — núcleo: PresoAoEvento, marcar, desmarcar, limpar_mes,
                                  #   reconferir_marcados, faixa_sumidos, devolver_ao_google
app/calendar/routes.py            # 6 toques: delegação de _cleanup_stale_events; _delete_event
                                  #   (ensaios-filho + aviso do sino); _delete_event_flow recusa
                                  #   evento marcado (FR-045) e o wrapper Jinja de exclusão traduz;
                                  #   _sync_single_event_flow; um elif no wrapper Jinja do
                                  #   "Sincronizar"; import sem uso
app/calendar/sync.py              # reconferir_marcados antes do laço; resumo com os totais do
                                  #   ciclo antes da lista de meses (FR-042); rollback no except
                                  #   só em erro de banco
app/calendar/event_ops.py         # 1 condição: não empurra edição ao Google se marcado
app/calendar/cancel_ops.py        # EventoMarcadoError; cancelar_evento recusa evento marcado (FR-045)
app/notificacoes/notificacoes_ops.py   # kind evento.sumiu_google + notificar_evento_sumiu_google
app/api/agenda.py                 # GET /api/events/sumidos-google
app/api/agenda_read.py            # situacao no resumo e no detalhe; sumiu_do_google; link nulo
app/api/agenda_write.py           # POST devolver-ao-google; /sync 409; cancelar e DELETE traduzem
                                  #   a recusa em 409
app/api/admin_config_write.py     # cleanup_past: números novos, mensagem, rollback só em erro de
                                  #   banco
app/talent_portal/portal_ops.py          # _role_summary: em_confirmacao
app/talent_portal/portal_rating_ops.py   # cancelado fora da avaliação

frontend/apps/internal/src/
├── lib/sumidosGoogle.ts                       # NOVO — tipos, hook com poll, hook passivo
├── lib/agenda.ts, eventOps.ts, adminConfig.ts # tipos opcionais; useDevolverAoGoogle; invalidações
├── components/FaixaSumidosGoogle.tsx          # NOVO — barra fixa + lista
├── components/SeloSituacao.tsx                # NOVO — selo único (nesta entrega: o do marcado)
├── components/EventDetail/SumiuDoGoogleBanner.tsx   # NOVO — marca, o que está em jogo, devolver
├── components/EventDetail/EventHeader.tsx     # monta o banner; menu (Sincronizar/Editar no Google)
├── components/AppShell.tsx                    # monta a faixa antes do <Outlet />
├── components/{CalendarGrid,AgendaListView,DayTimelineView}.tsx   # selo do marcado (no chip do
│                                                  #   Mês e no bloco curto do Dia, só o ícone);
│                                                  #   AgendaSearchResults.tsx herda de
│                                                  #   AgendaListItem, sem mudança de código
├── components/notificacoes/NotificacaoItem.tsx      # ícone do kind novo; título e corpo do
│                                                  #   aviso urgent em mais de uma linha
├── pages/EventDetailPage.tsx, DashboardPage.tsx     # offset de topo quando a faixa está visível
└── pages/AdminSyncPage.tsx                          # ConfirmDialog no lugar do window.confirm;
                                                   #   mensagem com os seis números; linhas por mês

frontend/apps/portal/src/
├── components/AvisoEmConfirmacao.tsx          # NOVO
├── lib/portalAgenda.ts                        # em_confirmacao?: boolean
└── pages/Portal{Agenda,Convites,Historico}Page.tsx

specs/205-loja-interacoes-virtuais/verify_205.py     # passa os outros eventos vivos + credencial nula
                                                     #   + espião da consulta
docs/01, 02, 03, 04, 05; docs/PLANO_EXTRACAO_CALENDAR.md; DEVELOPMENT.md; CLAUDE.md §4;
.claude/skills/manto-verify/SKILL.md
```

**Decisão de estrutura**: o núcleo novo mora em `app/calendar/sumico_ops.py` porque marcar,
desmarcar, limpar e devolver compartilham o mesmo estado (a marca) e nenhum deles é "cancelamento"
(`cancel_ops`) nem "edição" (`event_ops`); o domínio já aceita `*_ops` fora de `routes.py`.
`_cleanup_stale_events` continua em `routes.py` como delegação de uma linha, porque é por esse nome
que `sync.py`, `admin_config_write.py`, a rota Jinja e os verifies antigos chegam à limpeza. A
consulta de três desfechos mora em `service.py`, junto das outras chamadas ao Google, para o dublê do
verify trocar só `build` e `load_credentials`. No frontend, faixa e selo ficam no app interno, não no
`@manto/ui`: o vocabulário "Sumiu do Google" é de domínio, e todos os consumidores estão ali.

## Fases de construção

0. **Pré-requisito cumprido em 30/09**: `contagem_pre_deploy.py` rodada (research R17) — zero
   eventos passados fora do Google, então a primeira rodada do "Limpar eventos fantasma" não precisa
   de regra especial. A sonda mostrou que o Google devolve o apagado como "cancelado" com dados
   completos. A contagem se repete no dia do deploy (fase 8).
1. **Setup**: constantes `SITUACAO_*`; trava em `app/config.py`.
2. **Foundational**: migration e modelo; `consultar_evento` e `insert_event(all_day=)`;
   `verify_303.py` com o dublê, rodado vermelho; ajuste do `verify_205.py`.
3. **História 1**: `sumico_ops` (preso, marcar, limpar), delegação, rollback de erro de banco nos
   dois laços,
   `_delete_event`, FR-008 e FR-039 (edição e Sincronizar), sino na transação da marca, `situacao`
   no resumo e no detalhe, selo na agenda, e a **parte comum do banner** do evento (marca, "percebido
   em", frase da edição — o aceite 4 da História 1) → verify bloco B1. Nesta fase o desfecho
   "presente" da consulta só não apaga nem marca, e o "Sincronizar" de um marcado que voltou
   sincroniza sem tirar a marca: aplicar a data nova e desmarcar são da fase seguinte.
4. **História 5**: aplicar data nova (`mesmos_dados`), `reconferir_marcados`, `desmarcar` (inclusive
   no "Sincronizar", com o ator que clicou — `_sync_single_event_flow` ganha `actor_name` e
   `actor_role`), FR-041 → bloco B2 (8, 9 e 13d).
5. **História 2**: endpoint da faixa, componente, hooks, offsets → bloco B3.
6. **História 3**: devolver ao Google (núcleo, endpoint, o resto do banner — quadro, botão, passos —
   e o diálogo), FR-045 (cancelar e excluir recusam) → bloco B4.
7. **História 6**: portal (`em_confirmacao`) e avaliação → bloco B5.
8. **Polimento**: docs, typecheck, ruff, telas, `verify_205`, contagem do dia do deploy, teste do
   devolver em produção.

Os blocos do verify seguem essa ordem, para `--ate Bn` ser linear; o tasks.md traz, por fase, a lista
esperada de verdes, vermelhos e bloqueados.

## Rastreamento de complexidade

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| V — a faixa não mostra skeleton nem erro no primeiro carregamento | Antes da primeira resposta o front não sabe se o papel vê a faixa (o servidor decide, `pode_ver`); o estado normal é a ausência | Skeleton em toda tela para todo papel seria um tranco permanente para avisar de algo que quase nunca existe; em erro o poll de 60 s tenta de novo e, com dado em cache, a faixa se mantém |
| III — imports tardios de `app/calendar/routes.py` dentro de `sumico_ops` (`sync_events`, `_delete_event`, `_log_sync`, `_is_virtual_event`, constantes do técnico de som) | O núcleo histórico do calendar mora em `routes.py` e a constituição manda não refatorar (`docs/00` §7) | Extrair essas funções para um `_ops` é a fatia 3 do plano de extração, pausada; copiar a regra violaria o Princípio I |
| II — um degrau de camada arbitrário (`z-[25]`) na faixa | Tem de ficar acima da régua de abas do evento (`z-20`) e abaixo do painel do sino e dos menus (`z-30`) | `z-20` perde o empate para a régua (vem depois no DOM); `z-30` cobre o painel do sino no celular |
| I — sexta cópia do fechar-em-Esc-e-clique-fora, na lista da faixa (molde `NotificacoesBell.tsx:38-58`) | A lista precisa fechar em Esc e em clique fora, devolvendo o foco | O `@manto/ui` não tem popover nem hook de fechar-fora; as cinco cópias vivas diferem em detalhe, e extrair um hook migrando as cinco é refatoração lateral fora do escopo — dívida registrada no `docs/05` |
| IV — `rollback()` novo no `except` de cada mês (sync e admin), **só em erro de banco** | Depois de um erro de banco a sessão fica inválida e todos os meses seguintes falham (defeito de hoje, que a limpeza nova, com mais comandos por ciclo, tornaria mais provável). "Marca sem aviso" não depende dele: a unidade de trabalho da limpeza é o evento, com `rollback` próprio (R4) | `rollback` em qualquer exceção desfaria o que `sync_events` deixou pendente (evento recém-importado; título, data e local; vagas da reconciliação; o carimbo `event_changed_at`) depois de os e-mails já terem saído — e o mesmo e-mail sairia a cada ciclo enquanto o erro persistisse (research §Riscos). Conferido no cenário 13c do verify |
