# Pesquisa (Phase 0) — Feature 315, pedido de cancelamento

Base: `pesquisa/reconferencia-2026-10-22.md` (arquivo:linha contra `7cc5e11e`) e o plano 2a (§4–§6, §8). Aqui ficam só
as decisões técnicas que o plano deixou abertas ou que a reconferência derrubou.

## R1 — Onde o pedido mora no código, e com que nome

**Decisão**: módulo novo `app/calendar/solicitacao_ops.py` ("solicitação de cancelamento"), com `solicitar`,
`recusar`, `fechar_no_cancelamento`, `responder_na_exclusao`, `faixa_das_solicitacoes`, `solicitacoes_da_venda`
(o lote do satélite, R6) e `bloqueio_do_pedido` (ensaio / cachê pago para o menu). As duas funções da 224 em
`cancel_ops.py:3502-3541` saem de lá (o módulo novo as substitui); `cancel_ops` só chama o módulo novo por import
tardio dentro de `ao_cancelar`.

**Por quê**: `PedidoDeCancelamento` (`cancel_ops.py:981-1009`) já é o **corpo** do POST de cancelar e
`_encerrar_os_dias` grava `cancellation_reason = pedido.motivo` (`:2057`): um segundo "pedido" no mesmo módulo faria
o leitor confundir os dois. `cancel_ops.py` tem ~3.650 linhas; o pedido é um fluxo à parte (pedir, avisar, decidir),
com um ponto de contato só com o cancelamento (o fecho). A UI e as rotas dizem "pedido de cancelamento"; o código
diz "solicitação".

**Alternativas**: manter no `cancel_ops` com nome novo (cresceria o arquivo que mais muda; rejeitado); entidade nova
(o plano já rejeitou — as colunas da 224 bastam).

## R2 — O fecho do pedido no cancelamento

**Decisão**: `ao_cancelar(event, *, alcance, novo_principal)` (`cancel_ops.py:1594-1602`) passa a chamar
`solicitacao_ops.fechar_no_cancelamento(event, alcance=…, novo_principal=…)`, e as três linhas que zeram o pedido em
`_encerrar_os_dias` (`:2059-2061`) **saem** de lá — a limpeza (cinco colunas) passa a ser do fecho, que lê o pedido
(autor, alcance, carimbo) **antes** de zerar. A assinatura de `ao_cancelar` não muda (o espião do `verify_306`,
`:384-412`, a fixa); quem decidiu é `event.cancelled_by_id`, gravado na linha anterior (`:2056`). O fecho: zera as
colunas, marca lidos os avisos do pedido daquele dia, e emite `evento.pedido_decidido` ao autor (salvo autor nulo,
sem acesso ou igual a quem cancelou), com o texto do alcance: "todos" = "Evento cancelado"; "só este dia" no corte =
"Dia dd/mm cancelado — a venda segue nos outros dias"; na passagem = "…: a venda passou para o dia dd/mm" (o
`novo_principal`). Roda na transação do cancelamento, sob a trava `travar_grupo` (`:846`, `FOR UPDATE` +
`populate_existing`) — não precisa de claim próprio.

**Por quê**: o gancho já é chamado em **cada** dia que o ato encerra, nas quatro formas (avulso, todos, corte,
passagem), depois de `passar_venda` — exatamente o que o plano pedia ("uma função deste item chamada pela 1b em cada
dia"). Ler antes de zerar é o único jeito de saber a quem responder; mover a limpeza para o dono do pedido deixa uma
fonte só para "o pedido fecha".

**Alternativas**: reordenar `_encerrar_os_dias` (chamar o gancho antes da limpeza) e manter a limpeza lá — duas
mãos fechando o mesmo pedido, e as duas colunas novas teriam de entrar no `cancel_ops` também; mudar a assinatura do
gancho para receber o ator — quebraria o espião do `verify_306`.

## R3 — O alcance

**Decisão**: coluna `deletion_request_scope = db.Column(db.String(16), nullable=True)` com os valores da 306,
`ALCANCE_TODOS = "todos"` e `ALCANCE_SO_ESTE_DIA = "so_este_dia"` (`constants.py:481-482`). Gravado pelo servidor:
evento sem grupo → `todos`; satélite → `so_este_dia`; principal com outro dia vivo → o que vier no corpo (obrigatório,
400 `fields.alcance`); nulo = pedido de antes do deploy ou feito pelo caminho velho sem alcance (lido como hoje: "todos" no avulso e no principal, o próprio
dia no satélite — só para mostrar).

**Por quê**: o corpo do cancelar já fala `todos | so_este_dia`; `venda | dia` colide com `REGIME_VENDA/REGIME_DIA`
(`constants.py:471-473`). "so_este_dia" tem 11 caracteres — `String(10)` do plano não cabe.

## R4 — A devolução combinada

**Decisão**: o corpo do pedido tem a forma do corpo do cancelar da 306 (`PedidoDeCancelamento.ler`,
`cancel_ops.py:1008-1082`): `{motivo, alcance?, devolucao: {modo, valor?, nome?, pix?}, venda_nova?}`. A coluna
`deletion_request_refund = db.Column(db.Text, nullable=True)` guarda o JSON `{"devolucao": {"modo", "valor", "nome",
"pix"}, "venda_nova"}` (valores em texto decimal, padrão `db.Text` da casa — `models.py` não tem `db.JSON`), lido de
forma tolerante a JSON corrompido. Validação **só de forma**, com os nomes de campo da 306: `devolucao_modo` (fora de
tudo/parte/nada; no corte, `tudo` recusado), `devolucao_valor` (Parte sem valor > 0; valor não decimal),
`devolucao_nome`/`devolucao_pix` (obrigatórios em Tudo e Parte; 200/120), `venda_nova` (obrigatória no corte, > 0).
**Venda virtual**: sem devolução — o corpo só precisa do motivo (a 306 ignora o modo, `:1653-1656`); a coluna fica
nula. O pedido **não** confere máximo a devolver, devolução mínima do corte nem "nada pago → só Nada": é dinheiro, e
quem confere é o cancelar na hora de cancelar. Em **Nada**, nome e PIX não são gravados (não há a quem devolver; o
diálogo nem os mostra) — vindos no corpo, são descartados. O pedido **não** tem `observacao`: o motivo já é o texto
livre do pedido, e a observação da devolução é do Superadmin, no cancelar.

**Por quê**: uma forma só para o mesmo dado (o Superadmin compara lado a lado); a forma do pedido não pode ser mais
rígida que a do cancelar, senão o Comercial seria barrado por uma conta que vale para o momento do cancelamento.

## R5 — Claim por `UPDATE` condicional

**Decisão**: pedir = `UPDATE calendar_events SET deletion_requested_at=:agora, …_by_id, …_reason, …_scope, …_refund
WHERE id=:id AND deletion_requested_at IS NULL AND cancelled_at IS NULL` (molde `sumico_ops.marcar`,
`sumico_ops.py:225-238`, com `synchronize_session=False`); `db.session.refresh(event)` nos **dois** ramos (a view
carregou o evento antes, `agenda_write.py:911`, e o identity map guardaria o valor velho); 0 linha → cancelado → 409
`cancelado`; senão 409 `pedido_pendente` com o nome de quem pediu. Nada no request atribui as colunas no objeto fora do
UPDATE (o autoflush gravaria por cima). A ordem das respostas segue a da 306 (`_recusas_de_estado` antes da forma):
409 ensaio → 409 cachê pago do próprio dia → 400 campos → 409 cachê pago dos outros dias que "todos" alcança → claim.
O pedir não trava o grupo: um agrupar concorrente pode gravar um alcance velho (aceito; o cancelar relê o grupo sob
trava). Recusar = `UPDATE … SET <cinco colunas> = NULL WHERE id=:id AND deletion_requested_at = :carimbo_lido`; 0 linha
→ 409 `sem_pedido` (outro Superadmin decidiu, ou o cancelamento fechou). O aviso, o histórico e a auditoria só saem
depois do claim ganho, na mesma transação. No cancelamento, o fecho (R2) roda sob `FOR UPDATE` do grupo: se uma
recusa commitou antes, o fecho lê o pedido já nulo e não responde; se o cancelamento trava primeiro, a recusa espera e
perde o claim (409).

**Por quê**: hoje `solicitar_exclusao` testa e grava em Python, sem trava — dois pedidos ao mesmo tempo passam e
sobrescrevem; duas decisões ao mesmo tempo dariam ao autor duas respostas (FR-022).

## R6 — O satélite que herda o pedido de "todos os dias" do principal

**Decisão**: `situacao` (`models.py:430-442`) continua lendo só o próprio evento. Um lote único,
`solicitacao_ops.solicitacoes_da_venda(eventos) -> dict[int, datetime]` (uma consulta pelos `group_leader_id`
distintos: `id IN (...) AND deletion_requested_at IS NOT NULL AND cancelled_at IS NULL AND (deletion_request_scope =
'todos' OR deletion_request_scope IS NULL)`), devolve, por satélite, o carimbo do pedido do principal. Quem serializa
o lote passa esse carimbo: `serialize_event_summary(event, pedido_da_venda=None)` vira `exclusao_solicitada` (se o
próprio evento não tiver situação mais forte) — o mês (`agenda_read.py:128-138`, `build_agenda_month`), o dia (`agenda.py:104`) e a busca
(`agenda.py:51-77`, a lista em `:71`) chamam o lote uma vez; `_role_summary` do portal ganha o mesmo parâmetro (o lote roda uma vez
por lista, `portal_ops.py:357-400`, `:936`); o detalhe (um evento) lê o principal direto. As outras listas que mostram
a situação (ficha da cliente, formulários, figurino, tags 3D) mostram a do próprio evento — sem lote (premissa 9 da
spec diz "onde o selo já aparece"; a herança vale onde a equipe planeja o dia: agenda, detalhe e portal).

**Por quê**: ler `event.group_leader` em cada linha é N+1 (lição da 300; o comentário de `portal_ops.py:318-320`
promete "nenhuma consulta nova"). Hoje há 0 vendas de vários dias futuras (recontagem), mas a regra vale desde já.

## R7 — A faixa vermelha com os pedidos

**Decisão**: `GET /api/events/sumidos-google` (`agenda.py:160-172`) ganha a chave **opcional**
`pedidos: {total, items[{id, title, start_at}]}` (até 100 itens; futuros por data, depois passados, sem data por
último), pelo mesmo gate `_ve_faixa_sumidos` (`agenda.py:154-157`); `total` e `items` continuam sendo **só do
sumiço** (o bundle velho escreveria "N eventos sumiram"). No componente (`FaixaSumidosGoogle.tsx`), as duas frases
dividem a linha de 40 px (`h-10`), cada uma com o seu botão, o seu `aberto`, o seu `ref` e a sua lista (o estado hoje
é um só, `:31-34`); um pedido = link direto ao evento, vários = lista com links aos eventos (nunca a
`/events/cancelamentos`, que o Comercial não abre). `useFaixaSumidosVisivel` e o `select` (`sumidosGoogle.ts:54-63`)
passam a olhar `total > 0 || (pedidos?.total ?? 0) > 0`. Cada frase é um botão com `aria-expanded`/`aria-controls`
para a sua lista, e Esc e clique fora fecham a lista aberta (o comportamento de hoje, em dobro). O evento que está
marcado **e** tem pedido (o 1350) conta nas duas frases. Em 375 px as frases encurtam ("2 sumiram do Google · 1
pedido de cancelamento"). Os hooks de pedir e recusar invalidam a faixa (`invalidarSumidosGoogle`); o cancelar e o
excluir já invalidam (`eventOps.ts:87`, `:366-368`).

## R8 — O corte da Q6 e da premissa 5

**Decisão**: no detalhe (`agenda_read.py:854-862`, dentro de `serialize_event_detail(event, user, impersonate)`,
`:814`), o bloco `deletion_request` vai a todo papel com `requested_at` e `alcance`; `requested_by`, `requested_by_id`
e `reason` só com `flags["show_comercial"]` (o molde da 312 logo acima, `:852-853`); `devolucao` (modo e valor) só com
`show_comercial`; `devolucao.nome`, `devolucao.pix` só com `show_comercial` **e** (`show_financeiro` **ou** o autor sem
"Ver como": `user.id == deletion_requested_by_id and not impersonate`) — senão o Superadmin autor em "Ver como Casting"
leria o PIX sem ler o motivo. `flags is None` (chamador interno) libera tudo, como hoje. Na fila
(`listar_cancelamentos`, `cancel_ops.py:3564`; os `pendentes[]` em `:3611-3625`), o mesmo corte por `ver_motivo`
(`:3605`) — hoje os pendentes o ignoram; a função ganha o parâmetro `usuario` (a view `agenda_write.py:985-986` passa
`current_user`). Chave opcional nova `pedido_bloqueado: {codigo, frase}` no
detalhe (ensaio; cachê pago) para o menu desabilitar o item com a frase do servidor.

## R9 — O alias `/solicitar-exclusao`

**Decisão**: as rotas novas `POST`/`DELETE /api/events/<id>/pedido-cancelamento` são **regras a mais nas mesmas
funções de view** (`api_solicitar_exclusao`, `api_recusar_solicitacao`, `agenda_write.py:908-948`; dois `route` na
mesma função registram o mesmo endpoint — conferido; sem CSRF nem limite por rota): os nomes de endpoint não mudam (a classificação do 9b do `verify_312`, `LIVRE_306`, `:706-707`, continua certa sem edição). A
view distingue o caminho pela regra (`request.url_rule.rule`): pelo caminho velho, o corpo só com `{motivo}` é aceito
e o pedido nasce "sem devolução informada" (o bundle velho e o cenário 12 do `verify_303`, `:2375-2377`, `:2583`); pelo
caminho novo, a devolução é obrigatória. Pelo caminho velho também **sem `alcance`**: o principal com outro dia vivo
grava alcance nulo (lido como "todos", R3) — o diálogo velho não tem o campo e um 400 `fields.alcance` não apareceria. Respostas: o detalhe do evento (`serialize_event_detail`, molde do
devolver-ao-google) nos dois caminhos — o bundle velho ignora o corpo e refaz o GET. A remoção do caminho velho entra
no `docs/05`.

## R10 — A resposta ao autor na exclusão

**Decisão**: no **adaptador da API** (`api_delete_event`, `agenda_write.py:669-718`): antes de `_delete_event_flow`,
guarda autor e título do pedido; depois que ele commita, emite `evento.pedido_decidido` "Evento excluído — <título>",
**sem entidade e sem link**, em transação própria (regime B: falha no aviso não desfaz a exclusão). A rota Jinja de
exclusão e o sync não respondem (P18). `apagar_por_entidade` (`routes.py:354`) já apaga os avisos do pedido no
`_delete_event`.

**Corrida aceita**: o autor é lido antes da trava do núcleo (`routes.py:~4563`, `refresh(..., with_for_update=True)`);
uma recusa que commita nesse meio dá ao autor "recusado" e depois "excluído". Janela de milissegundos entre dois
Superadmins decidindo o mesmo pedido de jeitos diferentes — fica assim, registrada.

**Por quê**: o núcleo `_delete_event_flow` (`routes.py:4540-4587`) é compartilhado com o Jinja vivo; o Jinja não é a
porta da equipe e "código velho não se limpa de passagem".

## R11 — Os avisos no sino

**Decisão**: dois kinds no catálogo (`notificacoes_ops.py:54-77`, receita `:16-18`):
`evento.pedido_cancelamento` (destinatários: SUPERADMIN ativos; `urgent` se o evento é em ≤ 7 dias — o evento que
já passou também, como nos produtores de hoje (`:272`, `:311`), `ANTECEDENCIA_URGENTE_DIAS`, `:91`; senão `info`; `dedupe_key = <kind>:<event_id>:<carimbo do pedido>`;
`entidade=("calendar_event", id)`, `link_path=/events/<id>`; corpo: data · venda · recebido · N escalados (pela régua
do **cancelamento**, `cancel_ops.elenco_dos_dias(ids)` nos dias que o pedido alcança — sem convite recusado nem a vaga de
presença —, para o número bater com quem o cancelamento avisa; o `n_escalados` de `preso_ao_evento` conta recusados) ·
alcance · pedido por <nome> · <motivo>, cortado em 500) e
`evento.pedido_decidido` (`destinatarios=[autor]`, `info`, chave `<kind>:<event_id>:<decisão>:<carimbo do pedido>`;
entidade e link menos no "excluído"). Na decisão, `marcar_lidas_por_entidade("calendar_event", id,
kind="evento.pedido_cancelamento")` (`:458-474`) — sempre com o kind, senão marca também o `pedido_decidido` da mesma
entidade. `emitir` com `destinatarios` explícitos não filtra ativo/acesso (`:153-160`): o produtor da decisão filtra
`autor.is_active and autor.has_access and autor.id != quem_decidiu`. Na tela, ícones para os dois kinds em `NotificacaoItem.tsx:7-16` (sem
entrada cai em `Bell`).

## R12 — Verify: harness e regressão

**Decisão**: `verify_315.py` importa o harness da 306 como módulo, como a 312 (`verify_312.py:7-13`, `:44-46`):
`GoogleFalso` que falha fechado, disjuntor de rede, e-mail falso, `_usuario` com prefixo, `_externo` (conexão
separada), eventos em meses isolados (2050), `_sob_mutacao` para a prova do corte; sai com código 2 se houver backend
local rodando. Primeira rodada contra a `main` em `verify_315_primeira_falha.txt`. Regressão: `verify_306` (base
conhecida 67/69), `verify_312` (27/27 — confere que a classificação do 9b segue certa), `verify_303` (o cenário 12
pelo alias), `verify_311` e `verify_302` (portal). O `scripts/db/verify_cancelamento_evento.py` envelhecido (dívidas
85 e 129) sai da regressão.
