# Pesquisa — Feature 312

Base: `main` em `5c298ac5`. O mapa do código (o que filtra, o que recusa, o que falta, com arquivo:linha) está em
`pesquisa/reconferencia-2026-10-20.md` e não se repete aqui. O desenho de origem é o plano 1c
(`docs/backlog/1c-sinalizar-e-filtrar-cancelados.md`, §4–§6 e premissas 1–37, no checkout principal). Este
arquivo fecha só os pontos que a reconferência deixou abertos.

## R1 — O cancelado pela regra velha (o 1358) na página, no card e na tela

**Decisão**: nada a construir. A 306 já trata o cancelado sem linha de congelamento como regime `legado`
(`cancel_ops.py:437`: `regime = canc.regime if canc is not None else REGIME_LEGADO`): retido = pago − devolvido
(`:444`), vendedor de hoje, BV pago pelo `amount_brl` (`:368`), e entra em `cancelados_do_periodo` quando tem
dinheiro (`:591-623`). O "Alterar devolução" já aceita o `legado` (`:2675-2685`, `:3161-3162`).

**Razão**: o 1358 (venda R$ 7.318, cancelado em 02/10, sem devolução) aparece na página com `resumo` completo e
retido igual ao pago. O cenário 16 do verify semeia um cancelado legado (por `UPDATE` de `cancelled_at`, sem
`event_cancellations`) e confere que a página e o card não quebram.

**Alternativas**: tratar o legado na 1c (duplicaria a régua da 306) — rejeitada.

## R2 — Nome e lugar da trava geral (Q7)

**Decisão**: `cancel_ops.exigir_evento_vivo(event: CalendarEvent) -> None`, que levanta
`EventoSomenteConsultaError(CancelValidationError)` — 409, `codigo = CODIGO_EVENTO_CANCELADO` ("cancelado"),
mensagem "Este evento foi cancelado — a tela fica só para consulta.". Olha só `cancelled_at` (o pedido de
exclusão e a marca da 303 não travam). Não olha papel: vale para o Superadmin.

- Mora em `app/calendar/cancel_ops.py`, ao lado de `EventoCanceladoError` e de `recusar_se_cancelado`: é a casa
  das regras do cancelado, e as rotas já importam dali. *[analyze]* Não há ciclo de carga hoje: `cancel_ops` e
  `event_ops` só se importam dentro de função (`event_ops.py:1235/1244`, `cancel_ops.py:2222/2797`). Quem chama a
  trava (`event_ops`, `casting_ops`, `nfc_ops`, `impressoes3d_ops`, `formularios_ops`, `producao_ops`) importa
  dentro da função, no molde de `event_ops.py:1244` — no `formularios_ops` é obrigatório, para manter a invariante
  "folha" de `event_ops.py:14-18`.
- A tradução é a que já existe: `_recusa_do_cancelado(exc)` (`agenda_write.py:121-125`). Para os módulos fora de
  `agenda_write` (3D, NFC, figurino, formulários, portal, avaliação) a tradução sobe para `app/api_utils.py` como
  `json_recusa_do_cancelado(exc)`, e `_recusa_do_cancelado` passa a delegar a ela (uma fonte, Princípio I; sem
  mover mais nada).
- Na API, cada escrita da tabela "Trava" chama um ajudante `_trava_do_cancelado(event)` (irmão de
  `_recusa_se_cancelado`, `agenda_write.py:132-145`) **depois** do 404 e do 403 da rota e antes de qualquer
  escrita; `None` = segue.
- No Jinja: uma checagem no despachante `event_detail` (`routes.py:1658`, antes do `handler`, para **todas** as
  ações — a 306 já recusa as 8 de venda), `flash` com a frase e `redirect`; a mesma linha nas rotas Jinja fora do
  despachante que escrevem no evento (observações `:4504`, `:4546`; materiais `:4296-4372`; dismiss/restore de
  vaga `:4607`, `:4629`; `create-ensaio` `:2615`; `link-parent` `:2787`) e em "Imprimir fichas"
  (`figurino/routes.py:36`).

**Alternativas**: decorator por rota (o projeto proíbe gate por decorator — RBAC é função no início da view;
a trava segue o mesmo molde); lista de rotas liberadas (rejeitada no plano 1c: a exceção de venda é a regra da
306, uma função só).

## R3 — As recusas de vínculo (Q2, Q5) e os códigos HTTP

**Decisão**: uma função no núcleo, `cancel_ops.recusar_se_cancelado_para_ligar(event, *, campo: str | None = None)`,
chamada pelos núcleos de cada domínio **antes de qualquer escrita, e-mail ou Google**. Levanta
`EventoCanceladoVinculoError(CancelValidationError)` com `codigo="cancelado"` e mensagem por ação. O status segue o
vizinho de cada rota:

| Ação | Núcleo | Status | Por quê |
|---|---|---|---|
| Vincular ensaio a show | `link_ensaio_to_show` (`event_ops.py:1871`) | **400** `fields.parent_event_id` | o vizinho traduz `EnsaioValidationError` em 400 com campo |
| Tag NFC, vínculo novo | `update_tag` (`nfc_ops.py:289`) | **400** `fields.event_id` | `nfc_write.py:48/:75` dão 400 com campo; reenviar o mesmo id passa |
| Pedido de figurino novo ou troca de evento | `_resolver_evento` (`producao_ops.py:595`) | **400** `fields.event_id` | `figurino_producao_write.py:142/:189` dão 400 com campo |
| Agendar ensaio (API e Jinja) | `create_ensaio` (`event_ops.py:1761`) | **409** | é ação sobre o evento, sem campo; antes do Google |
| Presente 3D novo | `add_event_gift` (`impressoes3d_ops.py:319`) | **409** | idem |
| Ligar formulário (painel, `/formularios`, bloco) | `apply_event_link` (`formularios_ops.py:465`) | **409** | idem; `event_id: null` (desligar) passa |
| Escalar, vaga com talento, convidar, reenviar convite | `assign_role` (com talento), `add_role` (com talento), `send_invite`, `convidar_recem_escalados` | **409** | ação sobre o evento; antes de qualquer e-mail |
| Gerar link de avaliação | `ensure_feedback_token` (`event_ops.py:1527`) | **409** | idem |
| Avaliação pública `GET`/`POST /api/avaliar/<token>` | `feedback_write.py:45, :64` | **410** "Este evento foi cancelado — não há avaliação a fazer." | o recurso existiu e deixou de valer; o 404 de hoje fica para token desconhecido |
| Ficha de figurino do portal | `portal_figurino.py:36-39` (depois do "não escalado") | **400** "Este evento foi cancelado." | molde `_require_open_event` (`portal_rating_ops.py:232-247`: 400 depois do não escalado) |

Concorrência: as recusas leem o evento na mesma requisição, sem `with_for_update` (premissa 26 do plano 1c).

**Alternativas**: 409 em tudo (os três com campo perderiam o erro no campo que a tela já desenha — Princípio V).

## R4 — Tirar da escala no cancelado (Q10)

**Decisão**: em `api_assign_role` (`agenda_write.py:206-236`), no cancelado: gate `_can_casting()` (`:59`) no
lugar de `_can_edit_event()`, com 403 "Evento cancelado: quem tira da escala é o Casting."; corpo com talento,
cachê ou transporte → 409 da trava; só `talent_id` nulo segue para `assign_role`, que já não manda o e-mail de
remoção no cancelado (`casting_ops.py:61-64`, 306). Depois da remoção, se não sobra escalado a avisar naquele
dia, `notificacoes_ops.marcar_lidas_por_entidade("calendar_event", dia.id, KIND_EVENTO_CANCELADO_ESCALA)`
(`:458`) na mesma transação. "A avisar" = a mesma régua da pendência (R5). *[analyze]* `assign_role` comita sozinho
(`casting_ops.py:161`): o "marca lido" tem de rodar **dentro** dele, antes do commit, quando `event.is_cancelled` e
o talento sai. E `assign_role` grava `role.cache_value = parse_brl(cache_value)` — a view repassa
`cache_value=role.cache_value` na remoção para não zerar o cachê (a vaga vazia guarda o valor como registro). O
"Salvar" de hoje manda sempre `cache_value` (`CastingSection.tsx:347`): a tela ganha um botão "Tirar da escala" que
manda só `{talent_id: null}`.

## R5 — A pendência do Casting na Home

**Decisão**: `dashboard_service.compute_casting_tasks` (`:53`) ganha `cancelados_a_avisar`: vagas com
`talent_id` de evento com `cancelled_at`, fora a vaga de presença e quem recusou o convite, com `start_at >=
dashboard_cutoff`, ordenadas pela data do evento; item no molde de `serialize_unconfirmed_ref` (`:277-295`). A
régua "quem está a avisar" é **a mesma** que a 306 usa para escolher quem o ato avisa: `elenco_do_ato(event,
dias=None)` (`cancel_ops.py:2109-2120`: uma consulta `event_id IN ids` e `talent_id IS NOT NULL`, depois em Python
`invite_status != "rejected"` — o `None` entra — e `not e_vaga_de_presenca(r)`, `casting_ops.py:39-57`), sobre as
vagas de **hoje** (quem o Casting já tirou sai). *[analyze]* Já aceita vários dias; armadilha: `ids = dias or
[event.id]` — lista vazia cai no próprio evento. Extrair `elenco_dos_dias(ids)` (com `ids` vazio → `[]`) e fazer
`elenco_do_ato` delegar a ela; a pendência e o "marca lido" de R4 usam `elenco_dos_dias`. Não reescrever a régua
em SQL: o `!= "rejected"` do SQL descarta o NULL e o `not_presence` do dashboard (`dashboard_service.py:31`) é outra
régua.

## R6 — Ficha da cliente e painel do grupo

**Decisão**: `get_client_detail` (`client_ops.py:135-172`) já soma o retido ao `total_sales` com
`resumos_cancelados(cancelados)` (`:164-171`) e precisa do cancelado em `events` para isso. Ele passa a devolver
também `cancelamentos: {quantidade, retido}` saído da **mesma** chamada (sem rodar o lote duas vezes); o
serializador (`clientes_read.py:80-93`) tira o cancelado da lista e o `"cancelado": e.is_cancelled` (`:87`). O retido
fora de `venda`/`legado` já é zero (`cancel_ops.py:444`); `quantidade` conta todos os cancelados da cliente. `ClientDetailPage.tsx:183-208`
perde o ramo do cancelado e ganha a sublinha. `_group_block` (`agenda_read.py:715-724`): no principal vivo, a
lista usa `group_ops.dias_vivos`; no principal cancelado, fica como está. O `cancelado` de `satellites[]` continua
no contrato (a tela do principal cancelado o usa) e só deixa de aparecer no vivo; o badge em
`ComercialSection.tsx:1233-1234` fica (só aparece no principal cancelado).

## R7 — O bloco do card no Dashboard Comercial

**Decisão**: `financeiro_read` (pipeline, `:122-183`) ganha `cancelamentos`, montado por uma função nova em
`cancel_ops` — `painel_de_cancelamentos(inicio, fim, *, seller_id=None, educamanto_only=False,
commission_target_id=None, com_imposto: bool)` —
que a DRE também passa a usar no `paineis.cancelamentos` (`financeiro_read.py:538-563`), para a mesma forma e os
mesmos nomes nas duas telas (`quantidade, pago, devolvido, devolucao_a_pagar, retido, comissao_retido, bv_retido,
imposto?, efeito_resultado?, itens[]`). A comissão do retido segue a regra de beneficiário do KPI
(`vendas_ops.py:311-327`): com `commission_target_id`, só os resumos com `beneficiario.id == commission_target_id`;
sem ele (a DRE), a soma de `totais_cancelamentos`. *[analyze]* O alvo vem de `_resolve_vendas_scope`
(`financeiro_read.py:82-106`), não do `seller_id`: no EducaManto vendido pelo Comercial X com responsável Y, e no
usuário só de EducaManto (sem `seller_id`, com alvo), inferir do vendedor divergiria do KPI. Os totais continuam
saindo de `totais_cancelamentos` chamada pelo nome do módulo (a cascata da DRE e a mutação do verify dependem dele,
`financeiro_read.py:255`). Cada item: `event_id, titulo, event_date, cancelado_em, seller_name` (busca em lote: o
resumo só tem `seller_id`, `:494`), `pago, devolvido, devolucao_a_pagar, retido, comissao_retido, status`.

**Alternativas**: montar o bloco do pipeline à parte (dois somadores para o mesmo número — rejeitada, divergência
3 do plano 1c).

## R8 — Filtros da página de Cancelamentos

**Decisão**: `listar_cancelamentos(*, flags, mes: date | None = None, devolucao: str | None = None)`: com `mes`,
`cancelled_at` no mês em São Paulo (a coluna é naive SP), sem limite; sem `mes`, os 200 mais recentes. `devolucao`
∈ {`nao_pago`, `no_banco`, `pago`, `sem`}. *[analyze]* O `resumo` do regime `venda` soma as devoluções do **grupo**
(`do_grupo`, `cancel_ops.py:440`), e a passagem da venda move a devolução de evento (`group_ops.py:446-451`): um
`EXISTS` por `event_id` divergiria da coluna "Devoluções". O filtro olha as **devoluções do resumo** de cada
cancelado (o que a tela mostra): com `devolucao`, a consulta traz os cancelados (do mês, se houver), o lote de
resumos roda e o filtro se aplica sobre `resumo.devolucoes[].estado` antes do corte de 200 — volume de dezenas
(2 em produção em 20/10); a régua do `filtro_devolucao` (`:233-243`) já está dentro do resumo. Resposta ganha `total_retido`,
`total_retido_escopo` (`periodo` | `listados`) e `filtros`; sai `devolucao` (objeto legado). Validação na view:
`mes` fora de `AAAA-MM` ou `devolucao` fora do vocabulário → 400 com `fields`.

## R9 — Selo nas coisas ligadas

**Decisão**: `serialize_tag` (`nfc_ops.py:341-368`), `formularios_admin_read.py:89`, `clientes_read.py:96-104`
(form_history) e o pedido de figurino (`producao_ops.py:553`) ganham `event_situacao` (a `situacao` do evento,
`models.py:427-449`). Gastos Extras lê o `event_cancelled` que a 306 já manda (`gastos_read.py:53-54`).
`SeloSituacao.tsx` ganha o ramo `cancelado` (Badge vermelho "Cancelado", ícone `Ban`), usado só nessas listas.

## R10 — Recarregar a tela ao receber "cancelado"

**Decisão**: o tratamento que `EventHeader.tsx` já faz para `codigo` de recusa vira um utilitário em
`lib/eventOps.ts` (invalidar `["event", id]` quando `error.codigo === "cancelado"`), aplicado no `onError` das
mutações da tela do evento. A mensagem do servidor aparece onde a ação foi pedida.
