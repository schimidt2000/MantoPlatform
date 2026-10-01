# Frente cancelar-dados

Cancelar e devolver o dinheiro — dados e endpoints (FR-011, 013, 014, 015, 015a, 015b, 019, 021, 026)

Tamanho: G — 1 migration (2 tabelas), 2 models, cancel_ops reescrito em boa parte (~350 linhas novas: congelar, validar, resumo em lote, alterar devolução, prévia), 1 endpoint novo e 6 alterados em agenda_write, guardas em gastos_ops e gastos_write, 1 edição mínima no Jinja vivo (_build_bv_items), 2 telas alteradas e 1 diálogo novo. Depende da frente de comissão (aplicar e reaplicar a comissão do retido) e da frente da marca (predicado \"sumiu do Google\" e migration única).

## D1 — Onde ficam gravados, no ato do cancelamento, a venda e a comissão cheia congeladas, o BV negociado por acréscimo, o imposto sobre o retido e a escolha Tudo/Parte/Nada?

**Decisão.** Tabela nova `event_cancellations` (1:1 com o evento, UNIQUE em event_id) e filha `event_cancellation_bvs` (uma linha por acréscimo BV, com cópia do recebedor, PIX, valor original, valor negociado e se já estava pago no ato). Nenhuma coluna nova em `calendar_events` nem em `event_acrescimos` por esta frente. Sem backfill: cancelado sem linha é cancelado antigo (224).

**Porquê.** (a) A spec proíbe o BV negociado no próprio acréscimo (Entidades, spec.md:626-628), porque `substituir_acrescimos` apaga e recria as linhas e só resgata o status por (recebedor, PIX) (comercial_ops.py:78-85, 114-116). (b) Cada BV precisa de quatro dados: original, negociado, pago no ato e recebedor. A FR-019 manda contar o negociado, ou o original quando já estava pago, e depois que o financeiro paga o negociado o `bv_payment_status` sozinho não distingue os dois casos. (c) Ausência de linha identifica o cancelado anterior à 303 (FR-019: sem valor informado, não mostra BV) sem sentinela em sete colunas nulas. (d) Dinheiro fica em Numeric, somável em SQL. (e) `calendar_events` já tem mais de 60 colunas carregadas em toda consulta de agenda (models.py:243-326). (f) Com `relationship(..., uselist=False, cascade="all, delete-orphan")` no `CalendarEvent`, o `db.session.delete(event)` de `_delete_event` (calendar/routes.py:337) leva a linha junto, sem tocar `_clear_event_side_tables` (routes.py:259-302).

**Alternativas rejeitadas.** (1) Colunas em `calendar_events` mais `cancel_amount_brl` em `event_acrescimos`, com a aba Comercial recusando escrita. Rejeitada: contraria a spec (BV fora do acréscimo); exigiria duas colunas por acréscimo; a coluna some em silêncio se qualquer caminho regravar acréscimos (API agenda_write.py:1432 e Jinja calendar/routes.py:901); e não distingue cancelado antigo de cancelado novo. (3) Uma coluna JSON em `calendar_events`. Rejeitada: dinheiro sem tipo e invisível a consulta SQL.

**Contrato.** MIGRATION escrita à mão, só `create_table` (nenhum UPDATE), `down_revision = "e5a1c7d93b20"` — ou a revisão da marca "sumiu do Google" se ela vier em outro arquivo; o ideal é UM arquivo para a feature.

event_cancellations:
- id Integer PK
- event_id Integer NOT NULL, FK calendar_events.id ON DELETE CASCADE, UNIQUE `uq_event_cancellations_event_id`
- regime String(12) NOT NULL — 'venda' | 'satelite' | 'virtual'
- refund_mode String(8) NULL — 'tudo' | 'parte' | 'nada' (NULL fora do regime 'venda')
- sale_value Numeric(12,2) NOT NULL server_default '0' — venda congelada
- commission_full Numeric(12,2) NOT NULL server_default '0' — comissão cheia congelada
- commission_seller_id Integer NULL, FK users.id ON DELETE SET NULL — beneficiário congelado
- with_invoice Boolean NOT NULL server_default false — era "com nota" no ato
- retained_tax Numeric(12,2) NULL — imposto sobre o retido (NULL = não se aplica)
- created_at DateTime NOT NULL; updated_at DateTime NOT NULL
- updated_by_id Integer NULL, FK users.id ON DELETE SET NULL

event_cancellation_bvs:
- id Integer PK
- cancellation_id Integer NOT NULL, FK event_cancellations.id ON DELETE CASCADE, índice `ix_event_cancellation_bvs_cancellation_id`
- acrescimo_id Integer NULL, FK event_acrescimos.id ON DELETE SET NULL, índice `ix_event_cancellation_bvs_acrescimo_id`
- recipient String(200) NULL; pix String(140) NULL (cópias)
- original_amount Numeric(12,2) NOT NULL
- negotiated_amount Numeric(12,2) NOT NULL
- paid_at_cancellation Boolean NOT NULL server_default false (status 'pago' ou 'no_banco' no ato)

downgrade: drop das duas tabelas, filha primeiro.

MODELS: `EventCancellation` e `EventCancellationBv` em app/models.py. `CalendarEvent.cancelamento = db.relationship("EventCancellation", uselist=False, backref="event", cascade="all, delete-orphan")`. `EventCancellation.bvs = db.relationship("EventCancellationBv", cascade="all, delete-orphan", order_by=id)`. Property `EventCancellationBv.counted_amount` = original_amount se paid_at_cancellation, senão negotiated_amount.

**Pontos de toque.**
- app/models.py:283-295 (bloco de cancelamento do CalendarEvent — ganha só a relationship `cancelamento`)
- app/models.py:343-346 (relationship `acrescimos` — modelo do cascade a copiar)
- app/models.py:1789-1816 (EventAcrescimo — não muda)
- migrations/versions/e5a1c7d93b20_formulario_destino.py:29-30 (head atual, conferido: único revision sem filho)
- app/calendar/comercial_ops.py:78-117 (apaga e recria acréscimos)
- app/calendar/routes.py:259-302 e 305-338 (exclusão de evento — não precisa mudar com o cascade ORM)

**Riscos.**
- A frente da marca "sumiu do Google" também pede migration: dois arquivos com o mesmo down_revision criam dois heads e derrubam o `flask db upgrade` do startCommand. Juntar num arquivo ou encadear.
- `event.cancelamento` é lazy: lista que chame por evento vira N+1. Listas usam a função em lote da D5.
- Eventos já cancelados em produção ficam sem linha. A spec registra zero uso do Cancelar da 224 (spec.md:40), mas eu não consultei o banco: o plano precisa contar `cancelled_at IS NOT NULL` antes do deploy.

**Verify.** Por conexão separada: cancelar cria exatamente 1 linha em event_cancellations e N filhas (N = acréscimos BV); segunda tentativa de cancelar devolve 409 e não duplica. Cancelado semeado sem linha é lido como 'legado'. Excluir um cancelado vazio (satélite sem nada) não estoura FK. Ensaio `flask db upgrade` e downgrade em banco descartável com dump fresco, mais `python scripts/validar_startcommand.py`.

**Revisão adversarial: sim.** O desenho se sustenta: a spec proíbe o BV negociado no acréscimo e pede que o imposto more junto do que é congelado; o head é único (e5a1c7d93b20, conferido por varredura de revision/down_revision). Três ajustes pequenos. (1) Não é preciso tocar a classe CalendarEvent: o precedente 1:1 do repositório (Event3DDismissal) declara FK ON DELETE CASCADE + UNIQUE e a relação pelo lado do filho, com backref uselist=False e cascade. (2) `refund_mode` é dado derivado (pago × devolvido) que a D6 passa a regravar a cada alteração: estado duplicado que pode divergir do resumo. (3) O UNIQUE em event_id transforma clique duplo/requisição concorrente em IntegrityError (500), não no 409 prometido no verify_notes — hoje `cancelar_evento` só checa `is_cancelled` em memória. Observação: `paid_at_cancellation` inclui 'no_banco'; a FR-019 fala só em 'já pago' — é extensão do princípio da FR-017, registrar como premissa.

**Emenda.** Manter as duas tabelas e a migration única só com create_table. (a) Declarar a relação no filho, como Event3DDismissal: `event = db.relationship('CalendarEvent', backref=db.backref('cancelamento', uselist=False, cascade='all, delete-orphan'))` — zero edição no bloco do CalendarEvent. (b) `refund_mode` vira 'escolha no ato' (imutável, auditoria); o modo corrente é derivado no resumo — a D6 não o regrava. (c) `cancelar_evento` e `alterar_devolucao` começam travando a linha do evento (`with_for_update`) e o endpoint captura IntegrityError → rollback → 409. (d) Documentar no modelo que `created_at/updated_at` seguem a convenção de `cancelled_at` (São Paulo naive) e que 'no_banco' conta como pago no ato.

**Evidência da revisão.** app/models.py:2337-2350 (Event3DDismissal: unique + ondelete CASCADE + backref uselist=False cascade); app/models.py:343-346; app/calendar/cancel_ops.py:265-266 e 288 (checagem só em memória); app/calendar/comercial_ops.py:78-117; migrations/versions/e5a1c7d93b20_formulario_destino.py:29-30 (único head); app/calendar/routes.py:337 e 385 (delete pelo ORM); spec.md:626-632

## D2 — O que exatamente é congelado, e como ficam satélite de grupo, venda virtual, evento sem venda e cancelado antigo?

**Decisão.** O cancelamento grava um `regime`. Em 'venda' (caso normal), congela `sale_value`, a comissão cheia, o beneficiário, `with_invoice`, a escolha da devolução, o imposto e uma filha por BV. Em 'satelite' (`event.is_satellite`) e 'virtual' (`is_loja_virtual`), grava só a linha com o regime: sem devolução, sem mexer em comissão ou BV, e o resumo devolve retido zero. Pago e devolvido NÃO são congelados: são lidos ao vivo de `EventPayment` e `SpecialExpense`. Cancelado sem linha é 'legado': comissão 0, imposto 0, BV só o que está pago.

**Porquê.** O regime precisa ficar gravado porque `desagrupar` aceita satélite cancelado (group_ops.py:204-231 não checa cancelamento): solto do grupo, ele viraria um cancelado comum e passaria a gerar retido dos próprios comprovantes, contra a FR-029 e o cenário 32. A venda virtual não tem `EventPayment` e tem estorno próprio (FR-021); `cancelar_evento` hoje não a distingue (cancel_ops.py:262-270). A comissão cheia precisa ser congelada porque `_event_commission` recalcula da venda, da taxa, do BV e dos cachês a cada chamada (comissoes_ops.py:656-686), e a aba Comercial e a escala do cancelado continuam editáveis. O beneficiário é congelado porque `_commission_beneficiary` depende do vendedor do evento e da configuração EducaManto (comissoes_ops.py:643-653). `with_invoice` é congelado porque decide se o imposto é exigido na alteração (D6).

**Alternativas rejeitadas.** Derivar o regime ao vivo (`is_satellite`, `event_type`). Rejeitada: muda depois de desagrupar. Bloquear o cancelamento de venda virtual. Rejeitada: a FR-029 e o cenário 32 tratam "venda virtual cancelada" como caso que existe. Congelar também o pago. Rejeitada: a FR-026 define o pago como a soma dos comprovantes do evento; a D3 trava os comprovantes.

**Contrato.** cancel_ops: `_regime_do_cancelamento(event) -> str` ('satelite' se `event.is_satellite`; 'virtual' se `is_loja_virtual(event)`; senão 'venda').

`_congelar(event, regime, *, modo, imposto, bvs, settings, actor) -> EventCancellation`:
- sale_value = Decimal(event.sale_value or 0)
- commission_full = comissão cheia do evento (função da frente de comissão; hoje o cálculo é `_event_commission(event, settings)`, zero para cortesia e para beneficiário sem `receives_commission`)
- commission_seller_id = beneficiário ou None
- with_invoice = event.with_invoice

Ordem dentro de `cancelar_evento`, numa transação só: validar → congelar → gravar `cancelled_at` → criar a devolução → aplicar a comissão do retido (só regime 'venda', função da frente de comissão) → Google → logs → commit.

Venda zero com pago maior que zero: commission_full 0, sem divisão (guarda em `comissao_do_retido`, D5).

**Pontos de toque.**
- app/calendar/cancel_ops.py:236-319 (cancelar_evento)
- app/calendar/cancel_ops.py:128-155 (aplicar_estorno_comissao — deixa de ser chamada pelo cancelamento; continua no caminho de exclusão, calendar/routes.py:325-327)
- app/financeiro/comissoes_ops.py:643-686 (beneficiário e comissão cheia)
- app/financeiro/vendas_ops.py:197-205 (is_loja_virtual)
- app/calendar/group_ops.py:173-183 e 204-231 (satélite tem venda zerada; desagrupar não checa cancelado)
- app/models.py:397-405 (is_satellite / is_group_leader)

**Riscos.**
- A comissão "efetivamente paga" pode diferir da cheia congelada, porque a linha paga nunca é reescrita (comissoes_ops.py:852-865). O desconto é conta da frente de comissão; esta frente só entrega a cheia e a venda congeladas.
- Líder de grupo continua barrado enquanto tiver satélite, mesmo cancelado (`is_group_leader` = len(satellites) > 0, models.py:403-405). Mantido por decisão da spec; o diálogo já leva ao painel do grupo (ExcluirEventoDialog.tsx:174-198).
- Depois de desagrupar, o pago do líder não enxerga comprovantes anexados aos ex-satélites (`total_recebido` soma só o próprio evento, cancel_ops.py:47-54). Premissa da spec; o diálogo mostra o total pago para o Superadmin conferir.

**Verify.** Cenário 23c/32: satélite com comprovante próprio cancelado fica com regime 'satelite', nenhuma SpecialExpense, comissões do líder intactas e retido 0; desagrupar depois e reler o resumo: continua 0. Venda virtual cancelada: regime 'virtual', nenhuma devolução. Depois de cancelar, editar venda, taxa e escala do evento e reler o resumo: venda e comissão cheia não mudam (cenário 35 depende disso).

**Revisão adversarial: parcial.** Gravar o regime é certo (desagrupar não checa cancelado). Mas a definição da comissão cheia está factualmente errada: `_event_commission` NÃO zera para cortesia/permuta nem para evento sem beneficiário — quem faz isso é o `should_have` de `_sync_commission_payment`. Com `beneficiary is None` a função pula o teste de `receives_commission` e calcula taxa × base. Congelar `_event_commission` cru faria o resumo (e a DRE) mostrar comissão do retido para evento sem vendedor ou cortesia antiga com valor, enquanto Planilha e Comissões não têm linha nenhuma — quebra a FR-020. Dois buracos menores: (a) cancelado sem linha é sempre 'legado', mesmo sendo venda virtual ou satélite (FR-029 pede retido zero nos dois, independentemente de quando foi cancelado); (b) venda virtual com id `virtual-local-…` passa pelo `gcal_delete` e devolve aviso de falha do Google falso.

**Emenda.** Criar em cancel_ops (ou pedir à frente de comissão) UMA função `comissao_cheia_do_evento(event, settings) -> (Decimal, beneficiario_id | None)` que aplica o mesmo `should_have` de comissoes_ops.py:816-826 (venda, beneficiário não nulo, `receives_commission`, não cortesia, não virtual) e só então chama `_event_commission`; usar essa função no congelamento (D2) e na prévia (D9). No resumo, regime de cancelado sem linha = 'virtual' se `is_loja_virtual`, 'satelite' se `is_satellite`, senão 'legado'. Em `cancelar_evento`, não chamar o Google quando `google_event_id` começa com `GOOGLE_ID_LOCAL_PREFIX`. Regimes e modos como constantes UPPER_CASE em app/constants.py (constituição II).

**Evidência da revisão.** app/financeiro/comissoes_ops.py:656-686 (sem teste de cortesia nem de beneficiário nulo) × 816-827 (`should_have`); app/calendar/group_ops.py:204-231 (desagrupar sem checar cancelado); app/financeiro/vendas_ops.py:197-205; app/marketing/virtuais_ops.py:535 (`virtual-local-`); app/calendar/cancel_ops.py:278-286; spec.md:545-546 (FR-029); .specify/memory/constitution.md:45-46

## D3 — O que o cancelado passa a recusar para que o que foi congelado e o pago não se desfaçam?

**Decisão.** Duas travas, só em evento cancelado. (1) Acréscimos: `PUT /api/events/<id>/acrescimos` responde 409, e `substituir_acrescimos` vira no-op para cancelado (cinto para o chamador Jinja). (2) Comprovantes: adicionar, corrigir valor e excluir `EventPayment` de evento cancelado respondem 409, para qualquer papel. O resto da aba Comercial (venda, taxa, vendedor, nota, parcelas) continua editável.

**Porquê.** (1) A Planilha monta o item de BV a partir do `EventAcrescimo` e liquida pelo id dele (financeiro/routes.py:870-901; financeiro_write.py:158-172). O vínculo da D1 é `acrescimo_id`; regravar acréscimos troca os ids e o BV negociado sumiria da Planilha sem erro. (2) O pago é lido ao vivo (FR-026). Hoje CASTING e FIGURINO podem anexar comprovante (`_can_edit_event`, agenda_write.py:1549), o que mudaria retido e comissão de um cancelado sem passar pelo Superadmin e sem recalcular a linha de comissão, quebrando a FR-020.

**Alternativas rejeitadas.** Recusar toda escrita comercial no cancelado. Rejeitada: a spec conta com a aba editável e resolve pelo congelamento. Deixar comprovantes livres e recalcular a comissão a cada anexo. Rejeitada: papel sem poder de cancelar mexeria em comissão de vendedor. Resgatar o BV negociado por (recebedor, PIX) como o status. Rejeitada: chave frágil (dois BVs para o mesmo recebedor, recebedor renomeado).

**Contrato.** `api_set_acrescimos`: depois do RBAC, `if event.is_cancelled: return json_error("Evento cancelado: os acréscimos ficam como estavam no cancelamento.", 409)`.

`substituir_acrescimos`: `if itens is None or getattr(event, "is_cancelled", False): return`, com o porquê na docstring.

Payments: nos três endpoints, `if event.is_cancelled: return json_error("Evento cancelado: os comprovantes ficam congelados. O que mudou no dinheiro entra pela devolução, na tela do evento.", 409)`.

Frontend: a aba Comercial do cancelado esconde os botões de acréscimo e de comprovante por `event.cancelled_at` (é estado do evento, não RBAC).

**Pontos de toque.**
- app/api/agenda_write.py:1397-1434 (api_set_acrescimos)
- app/calendar/comercial_ops.py:66-76 (substituir_acrescimos — guarda no início)
- app/calendar/routes.py:901 (chamador Jinja, coberto pela guarda do núcleo)
- app/api/agenda_write.py:1540-1568, 1571-1593, 1596-1613 (add / edit / delete payment)
- frontend/server.js:253-264 (o POST Jinja de /events/<id> não é repassado pelo proxy)

**Riscos.**
- Cliente que paga algo depois do cancelamento (multa, por exemplo) não tem onde lançar o comprovante: ver a pergunta em aberto.
- Os helpers `_add_payment_record`, `_edit_payment_amount` e `_delete_payment_record` (calendar/routes.py:1097-1135) seguem sem guarda para o dispatcher Jinja, só alcançável falando direto com o backend.

**Verify.** Cenários que DEVEM falhar: PUT acrescimos em cancelado → 409, e por conexão separada os ids dos acréscimos não mudaram; POST, PATCH e DELETE de comprovante em cancelado → 409 e a soma de EventPayment é a mesma. Em evento vivo, os quatro endpoints seguem como antes (regressão).

**Revisão adversarial: parcial.** (1) Trava dos acréscimos: se sustenta, mas a lista de escritores está incompleta. Há um terceiro caminho: `PATCH /api/events/<id>/orcamento` → `set_event_orcamento` → `aplicar_valores_do_orcamento` → `_criar_acrescimos_do_orcamento`, que não checa cancelado e grava venda, `with_invoice` e acréscimos novos em evento cancelado sem venda (ex.: ex-satélite). Com o congelamento da D1 os números não mudam, mas a trava deixa de ser verdade. A nota sobre o Jinja também está trocada: o dispatcher usa `_handle_add_payment/_handle_edit_payment/_handle_delete_payment` (routes.py:1015-1094); os helpers 1097-1135 são só da API. (2) Trava de comprovantes para TODOS os papéis: não está na spec e cria beco sem saída — não existe 'descancelar' (o único escritor de `cancelled_at` é `cancelar_evento`), então comprovante esquecido ou com valor digitado errado no ato deixa pago, retido, teto de 'Tudo' e comissão errados para sempre. A parte que barra CASTING/FIGURINO (`_can_edit_event`) é necessária; barrar o Superadmin não é. (3) 'Esconder botões por `event.cancelled_at`' no React só vale se a regra for igual para todos; com exceção por papel, tem de vir flag do servidor (XIII).

**Emenda.** (1) Manter 409 no PUT de acréscimos e o no-op no núcleo; acrescentar em `set_event_orcamento` a recusa (409) de aplicar valores/acréscimos em evento cancelado; corrigir a nota do Jinja e registrar a falta de guarda dos `_handle_*_payment` como dívida no docs/05 (só alcançável falando direto com o backend). (2) Comprovante em cancelado: 409 para quem não é SUPERADMIN real; SUPERADMIN pode adicionar/corrigir/excluir, e o endpoint chama na MESMA transação a função de reaplicar da D6 (`reaplicar_cancelado(event)`: recalcula retido e comissão), recusando com 409 quando o novo pago ficaria abaixo do já devolvido. Se o dono preferir o congelamento total, é resposta dele — levar a pergunta antes do /speckit-tasks, não adotar por omissão. (3) Flag nova opcional no payload (`flags.can_edit_pagamentos`), calculada no servidor.

**Evidência da revisão.** app/calendar/orcamento_evento_ops.py:275-313 e 350-404 (sem checagem de cancelado); app/calendar/routes.py:3291-3323, 1015-1094 (handlers Jinja) e 1097-1135 (helpers da API); app/api/agenda_write.py:1397-1434, 1540-1613, 47-51; app/calendar/routes.py:61 (_CAN_EDIT_EVENT inclui CASTING e FIGURINO); grep `cancelled_at =` → só cancel_ops.py:288; frontend/server.js:253-264; constitution.md:223-225

## D4 — Qual é o corpo novo do POST de cancelar, quais as validações com o campo certo no envelope de erro, e como fica o Google quando o evento está marcado?

**Decisão.** `POST /api/events/<id>/cancelar` mantém caminho e RBAC (`_can_delete()`, só SUPERADMIN real). O corpo ganha `devolucao.modo` obrigatório, `bv_negociado` (lista por acréscimo) e `imposto_retido`. `CancelValidationError` passa a carregar `field` e `status`; o endpoint devolve o campo certo em `fields`. No regime 'venda', sem `modo` o cancelamento é recusado, sem ramo de compatibilidade para o bundle antigo. Evento marcado "sumiu do Google": o núcleo não chama o delete do Google e não devolve aviso.

**Porquê.** Hoje o endpoint não passa `remover_do_google` e põe todo erro no campo `motivo` (agenda_write.py:558-565); `_registrar_devolucao` não tem teto nem exige nome e PIX (cancel_ops.py:169-171). A regra do Google fica no núcleo porque vale para qualquer chamador. O valor de "Tudo" é conferido contra o servidor porque um comprovante pode entrar entre abrir o diálogo e confirmar. Recusar o corpo antigo é o comportamento seguro: nada acontece, a mensagem diz o que fazer, e aceitar seria cancelar sem a escolha que o dono exigiu.

**Alternativas rejeitadas.** O endpoint decidir `remover_do_google`. Rejeitada: a regra ficaria no adaptador. Servidor calcular "Tudo" ignorando o valor enviado. Rejeitada: devolveria um valor diferente do que a tela mostrou. Aceitar o corpo antigo como "Parte" ou "Nada". Rejeitada: contraria a Clarification.

**Contrato.** CORPO:
{
  "motivo": str,
  "devolucao": {"modo": "tudo"|"parte"|"nada", "valor": number, "nome": str, "pix": str, "observacao"?: str},
  "bv_negociado": [{"acrescimo_id": int, "valor": number}],
  "imposto_retido": number
}

ASSINATURA: `cancelar_evento(event, *, motivo, devolucao, actor, bv_negociado=None, imposto_retido=None, remover_do_google=True) -> dict`.
Devolve `{gasto_id, google_removido, aviso, resumo}`; `resumo` é o da D5 e nasce opcional no TS.

`CancelValidationError(message, field=None, status=400)`. Endpoint: `json_error(exc.message, exc.status, fields={exc.field: exc.message} if exc.field else None)`.

VALIDAÇÕES (campo):
- motivo vazio → 400 `motivo`
- já cancelado → 409, sem campo
- líder de grupo → 409, sem campo

Regime 'venda', com teto = total_recebido − devoluções aprovadas já ligadas ao evento:
- modo ausente ou inválido → 400 `devolucao_modo` ("Escolha Tudo, Parte ou Nada. Se as opções não aparecem, atualize a página.")
- 'tudo' ou 'parte' com teto 0 → 400 `devolucao_modo`
- 'parte' com valor ≤ 0 ou ≥ teto → 400 `devolucao_valor`
- 'tudo' com valor diferente do teto → 409 `devolucao_valor` mais extra `total_recebido`
- 'tudo' ou 'parte' sem nome → 400 `devolucao_nome`; sem PIX → 400 `devolucao_pix`
- `bv_negociado` tem de ter exatamente uma entrada por acréscimo BV com `amount_brl` > 0, valor entre 0 e `amount_brl`: lista ausente ou incompleta → 400 `bv_negociado`; valor fora da faixa → 400 `bv_negociado_<acrescimo_id>`
- `event.with_invoice` e `imposto_retido` ausente ou negativo → 400 `imposto_retido` (sem teto: a nota pode ter sido emitida cheia); sem nota, o campo é ignorado e grava NULL

Regimes 'satelite' e 'virtual': `devolucao.modo` diferente de ausente ou 'nada' → 400 `devolucao_modo` com o motivo; `bv_negociado` e `imposto_retido` ignorados.

Valores: `Decimal(str(x)).quantize(Decimal("0.01"), ROUND_HALF_UP)`.

GOOGLE: `if remover_do_google and not <evento marcado> and event.google_event_id` — o predicado é o da coluna que a frente da marca criar. Evento marcado devolve `google_removido=False, aviso=None`.

DEVOLUÇÃO: `_registrar_devolucao` como hoje (aprovada, categoria `CATEGORY_DEVOLUCAO`, `disbursement_type="cliente"`, `expense_date` = dia do cancelamento), só quando o valor é maior que zero.

**Pontos de toque.**
- app/api/agenda_write.py:541-566 (api_cancelar_evento)
- app/calendar/cancel_ops.py:39-44 (CancelValidationError)
- app/calendar/cancel_ops.py:158-191 (_registrar_devolucao)
- app/calendar/cancel_ops.py:236-319 (cancelar_evento; Google em 276-286)
- app/calendar/cancel_ops.py:194-213 (solicitar_exclusao segue com field='motivo')
- app/api/agenda_write.py:83-87 (_can_delete ignora o "Ver como")
- frontend/apps/internal/src/lib/eventOps.ts:120-150 (CancelarEventoInput e hook)

**Riscos.**
- Janela de deploy e cache: o bundle antigo manda `devolucao` sem `modo` (ExcluirEventoDialog.tsx:142-146) e recebe 400 com a mensagem acionável. Aceito.
- A escrita no Google de evento não marcado (`gcal_delete`) é antiga e não tem trava fora da produção (Princípio XIV). É a dívida que a FR-024 manda registrar no docs/05; o verify precisa substituir `app.calendar.service.delete_event`.
- O que acontece com a marca ao cancelar (limpar a coluna ou só perder a precedência) é da frente da marca. Esta frente só lê o predicado antes de decidir sobre o Google.
- `_can_delete` ignora o "Ver como", e o flag `can_delete` o respeita (agenda_read.py:189): o verify de recusa precisa de um COMERCIAL real.

**Verify.** Cenário 12: evento marcado cancelado com parte 600 de 1.000 → 200; SpecialExpense de 600 'nao_pago' com `disbursement_type='cliente'`, nome e PIX; stub do delete do Google NÃO chamado e `aviso` nulo. Evento não marcado: stub chamado uma vez. Cenário 16 (devem falhar, nada muda por conexão separada): sem modo; parte igual ao pago; parte acima do pago; tudo com valor divergente (409); tudo sem PIX — cada um com a chave certa em `error.fields`. BV: lista faltando um acréscimo; valor acima do original. Com nota sem imposto → `imposto_retido`. Cenário 11: COMERCIAL real → 403. Satélite com modo 'tudo' → 400. Corpo no formato antigo → 400 em `devolucao_modo`.

**Revisão adversarial: parcial.** Corpo, campos de erro e regra do Google no núcleo se sustentam (json_error aceita extras; o bundle antigo mostra `e.message`, então a recusa sem `modo` chega legível). Quatro lacunas. (1) O teto ignora gasto 'Devolução a cliente' PENDENTE já ligado ao evento: depois do cancelamento alguém aprova (`approve_expense` não tem guarda) e o devolvido sobe sem recalcular comissão — quebra a FR-020 e pode estourar o pago (o `max(…,0)` do resumo esconde). (2) Concorrência: ver D1 — hoje duas requisições passam por `is_cancelled`. (3) No 409 de 'tudo' divergente o extra devolvido é `total_recebido`, mas o valor certo de 'Tudo' é `max_devolucao` (= recebido − já devolvido); com devolução prévia a tela receberia o número errado. (4) FR-023: o contrato não diz o que vai no EventLog/auditoria — hoje só motivo e devolução; modo, BV negociado e imposto ficariam sem rastro. Além disso `cancelar_evento` com todas as validações estoura as ~30 linhas da constituição II.

**Emenda.** (1) Em `cancelar_evento`, recusar com 409 (sem campo) enquanto existir SpecialExpense de categoria devolução, ligado ao evento, com status 'pendente' ('Aprove ou rejeite a devolução pendente em Gastos Extras antes de cancelar'); e guardar aprovar/rejeitar na D8. (2) `with_for_update` na linha do evento no início + IntegrityError → 409. (3) Extra do 409 = `max_devolucao`. (4) EventLog e `_log_sync` com: modo, valor devolvido, retido, BV negociado por recebedor e imposto. Dividir em `_validar_devolucao`, `_validar_bv`, `_validar_imposto`, `_congelar`. Sem Google para id `virtual-local-`. O verify substitui `app.calendar.service.delete_event` em TODO cenário de cancelamento de evento não marcado (não há trava fora da produção).

**Evidência da revisão.** app/calendar/cancel_ops.py:39-44, 158-191, 236-319; app/api/agenda_write.py:541-566; app/gastos/gastos_ops.py:321-330 (approve sem guarda) e 430-433 (`aprovar=True` na edição); app/api_utils.py:16-42; frontend/apps/internal/src/components/EventDetail/ExcluirEventoDialog.tsx:142-150; spec.md:594-596 (FR-023); constitution.md:43

## D5 — Como é a função única de resumo do cancelado (FR-026): assinatura, o que devolve e de onde soma as devoluções?

**Decisão.** Em `app/calendar/cancel_ops.py`: `resumos_cancelados(events)` (em lote, consultas agrupadas) e `resumo_cancelado(event)` (chama o lote com um evento), devolvendo o dataclass `ResumoCancelado` em Decimal; `serializar_resumo_cancelado` faz a fronteira JSON. A devolução é toda `SpecialExpense` com `category == CATEGORY_DEVOLUCAO`, `event_id` do evento e `status == "aprovado"` — nunca por `disbursement_type`. A fórmula da comissão do retido fica numa função pura, `comissao_do_retido(cheia, retido, venda)`, usada pelo resumo e pela prévia do diálogo (D9).

**Porquê.** Hoje a devolução é lida com `.first()` filtrando `disbursement_type="cliente"` (cancel_ops.py:339-350): o complemento da FR-015a ficaria invisível, e o tipo é justamente o que o "Salvar" de Gastos Extras apaga (gastos_ops.py:237-238). A categoria é o critério da FR-028. O lote existe porque `listar_cancelamentos` percorre até 200 eventos (cancel_ops.py:332-337) e a DRE e o Dashboard precisam do período inteiro. Comissão, BV e imposto saem da linha congelada (D1), nunca de `_event_commission`.

**Alternativas rejeitadas.** Tabela própria do resumo. Rejeitada: a spec diz "derivado, sem tabela". Manter o filtro por destinatário corrigindo só o `.first()`. Rejeitada pela FR-028. Cada tela fazendo a própria conta. É o que a FR-026 proíbe.

**Contrato.** @dataclass(frozen=True) DevolucaoResumo: id, valor: Decimal, destinatario: str, pix: str, estado ('a_pagar' | 'no_banco' | 'paga', de payment_status nao_pago / no_banco / pago), data: date.

@dataclass(frozen=True) BvResumo: acrescimo_id, recebedor, original, negociado, pago_no_cancelamento: bool, conta: Decimal.

@dataclass(frozen=True) ResumoCancelado:
event_id; regime ('venda' | 'satelite' | 'virtual' | 'legado'); cancelado_em; modo; venda; pago; devolucoes: list[DevolucaoResumo]; devolvido; devolvido_pago (pagas mais no banco); a_devolver; retido; comissao_cheia; comissao_retido; comissao_beneficiario_id; bvs: list[BvResumo]; bv_que_conta; com_nota; imposto_retido; imposto_referencia; efeito_resultado.

REGRAS:
- pago = soma de EventPayment do próprio evento
- devolvido = soma de TODAS as devoluções (critério acima)
- retido = max(pago − devolvido, 0)
- regime 'venda': venda e cheia vêm da linha; comissao_retido = comissao_do_retido(cheia, retido, venda); bv_que_conta = soma de `counted_amount`; imposto_retido = retained_tax ou 0; imposto_referencia = retido × alíquota ÷ 100 quando com_nota
- 'satelite' e 'virtual': retido, comissão, BV e imposto = 0
- 'legado' (sem linha): venda = sale_value atual; comissão 0; imposto 0; bv_que_conta = soma de `amount_brl` dos BVs com status pago ou no_banco
- efeito_resultado = retido − bv_que_conta − comissao_retido − imposto_retido

`comissao_do_retido(cheia, retido, venda) -> Decimal`: 0 se venda ≤ 0 ou cheia ≤ 0; senão min(cheia, (cheia × retido ÷ venda) arredondado a 0,01 com ROUND_HALF_UP).

`resumos_cancelados(events) -> dict[int, ResumoCancelado]`: quatro consultas com IN (pagamentos agrupados, devoluções, event_cancellations, event_cancellation_bvs), mais os acréscimos pagos para o legado.

`serializar_resumo_cancelado(r, *, com_pix: bool) -> dict`: valores em float na fronteira; PIX só quando `com_pix`.

**Pontos de toque.**
- app/calendar/cancel_ops.py:47-54 (total_recebido — reusado)
- app/calendar/cancel_ops.py:322-383 (listar_cancelamentos — `_devolucao` sai e entra o resumo em lote)
- app/models.py:1018-1021 (CATEGORY_DEVOLUCAO)
- app/models.py:1107-1110 (`is_devolucao_cliente` compara o destinatário e não tem chamador em app/ — não usar)
- app/financeiro/routes.py:112, 129-132 (`_get_tax_rate`, import tardio, para a referência do imposto)
- app/financeiro/comissoes_ops.py:285-286 (comissão exibida zera para cancelado — quem consome o resumo é a frente da tela)

**Riscos.**
- Gasto "Devolução a cliente" pendente ligado ao evento não entra na soma. A D8 impede que um gasto vire devolução de cancelado fora do cancelamento.
- Desconto no repasse e comissão já paga não estão no resumo: a FR-026 não os lista e eles saem das linhas de `CommissionPayment`, que são da frente de comissão.
- Se a frente de comissão gravar na linha um valor diferente de `comissao_do_retido`, a FR-020 quebra: ela deve ler o resumo, não refazer a conta.

**Verify.** Exemplo do dono (venda 2.000, BV 200, taxa 5 gravada no evento, pago 1.000, devolvidos 600, parceiro recebe 40): resumo = pago 1.000, devolvido 600, retido 400, cheia 90, comissão do retido 18, BV 40, efeito 342; com nota e imposto 64 → 278, referência 64. Duas devoluções (600 paga mais 200 aberta) → devolvido 800, as duas listadas com o estado. Devolução com `disbursement_type` forçado a NULL continua contando (é a prova por mutação contra o critério antigo). Multa de outra categoria ligada ao evento não conta. BV pago no ato: conta 200 mesmo com negociado 50. Legado: comissão 0, BV só o pago. Retido nunca negativo.

**Revisão adversarial: sim.** Função única em lote, critério por categoria + evento + aprovado e fórmula pura batem com a FR-026/FR-028 e com o exemplo (cheia 90 → 18; efeito 342/278). Dependências que precisam ficar escritas: o resumo só é estável se (a) nada aprovar devolução de cancelado por fora (buraco apontado na D4/D8) e (b) a comissão cheia congelada seguir o `should_have` (D2). O regime de cancelado sem linha precisa da derivação virtual/satélite (D2). `imposto_referencia` usa a alíquota de hoje do SiteSetting — é só referência, dizer isso no docstring.

**Emenda.** Manter. Acrescentar: `resumo_cancelado` deriva o regime sem linha (virtual/satélite/legado); `comissao_do_retido` e a serialização em função separada (fronteira float só em `serializar_resumo_cancelado`); expor também `cancelados_do_periodo(inicio, fim)` em lote para DRE/Dashboard não reimplementarem o filtro por `cancelled_at`. Import de `_get_tax_rate` tardio, dentro da função (cancel_ops ↔ financeiro.routes).

**Evidência da revisão.** app/calendar/cancel_ops.py:47-54, 322-383 (`.first()` + filtro por `disbursement_type`); app/gastos/gastos_ops.py:237-238; app/models.py:1018-1021, 1107-1110; app/financeiro/routes.py:112, 129-132; app/financeiro/comissoes_ops.py:285-286; spec.md:526-533, 539-544

## D6 — Como é o endpoint de alterar a devolução do cancelado (FR-015a): regras para devolução aberta, paga ou no banco, e o que ele recalcula?

**Decisão.** `PATCH /api/events/<id>/devolucao`, em agenda_write.py, RBAC `_can_delete()` (SUPERADMIN real). O corpo informa o NOVO TOTAL devolvido; o servidor calcula a diferença. Piso = soma das devoluções pagas ou no banco; teto = total pago. A devolução aberta absorve a diferença (é consolidada numa só; excluída com auditoria quando o resto zera). Sem devolução aberta e com total maior que o piso, nasce um complemento (novo Gasto Extra aprovado, a pagar, com data de hoje). Na mesma transação: atualiza `refund_mode`, `retained_tax`, `updated_at` e `updated_by_id`, chama a reaplicação da comissão do retido (frente de comissão), grava EventLog e auditoria e devolve o resumo novo.

**Porquê.** O alvo como total torna a regra "só pode aumentar" uma comparação só (total ≥ piso) e garante o invariante do retido (total ≤ pago). "No banco" conta como paga (spec.md:410-411). As devoluções são lidas com `with_for_update()` porque a Planilha troca o estado delas sem guarda (financeiro_write.py:142-156, 306-318; financeiro/routes.py:1170-1177). Excluir a aberta zerada evita item de R$ 0 na Planilha.

**Alternativas rejeitadas.** Corpo com a diferença (mais 200 ou menos 100). Rejeitada: duas chamadas iguais somariam duas vezes. Editar pelo PATCH de Gastos Extras. Rejeitada: é FINANCEIRO e não recalcula comissão. Marcar a aberta zerada como "rejeitado". Rejeitada: ninguém a rejeitou, e ela seguiria na lista. Permitir alterar o BV negociado aqui. Fora: a FR-015a fala de devolução e imposto.

**Contrato.** PATCH /api/events/<int:event_id>/devolucao
Corpo: {"devolucao_total": number, "nome"?: str, "pix"?: str, "observacao"?: str, "imposto_retido"?: number}
Resposta 200: {"ok": true, "resumo": {...D5...}}

Erros:
- 404 evento não encontrado; 403 sem papel
- 409 evento não cancelado
- 409 regime 'satelite' ou 'virtual'
- 400 `devolucao_total` ausente, negativo ou maior que o pago
- 409 `devolucao_total` abaixo do já pago ou no banco ("R$ X já foram pagos — a devolução só pode aumentar")
- 400 `devolucao_nome` / `devolucao_pix` quando sobra valor a pagar e não há devolução anterior de onde copiar
- 400 `imposto_retido` negativo, ou enviado para evento que não era com nota

`alterar_devolucao(event, *, devolucao_total, nome=None, pix=None, observacao=None, imposto_retido=None, actor) -> ResumoCancelado`. Commita.

Passos:
1. resto = total − pagas
2. abertas (nao_pago) por id: a primeira recebe `amount = resto`; as demais são excluídas com AuditLog; se resto = 0, todas são excluídas
3. sem aberta e resto > 0: nova `SpecialExpense` (descrição "Devolução à cliente (complemento) — <título>", `expense_date` = hoje, nome e PIX do corpo ou copiados da devolução mais recente)
4. nome e PIX do corpo atualizam só a aberta
5. `refund_mode` = 'tudo' se total = pago, 'nada' se 0, senão 'parte'
6. regime 'venda': reaplica a comissão. 'legado': só a devolução muda

EventLog: "Alterou a devolução: R$ 600,00 → R$ 800,00 · retido R$ 200,00 · comissão do retido R$ 9,00".

Frontend invalida `["event", id]`, `["cancelamentos"]`, gastos e financeiro.

**Pontos de toque.**
- app/api/agenda_write.py:541-566 (endpoint novo logo abaixo; mesmo gate)
- app/calendar/cancel_ops.py (função nova `alterar_devolucao`; reusa `_registrar_devolucao`, 158-191)
- app/api/financeiro_write.py:142-156 e 306-318; app/financeiro/routes.py:1170-1177 e 1389 (marcar e desfazer "pago" continuam)
- app/api/agenda_read.py:714-718 (bloco do cancelado no detalhe — D11)
- frontend/apps/internal/src/lib/eventOps.ts (hook `useAlterarDevolucao`)
- frontend/apps/internal/src/components/EventDetail/ (diálogo novo `AlterarDevolucaoDialog.tsx`)
- docs/01 §4.3 (linha nova na tabela de gates)

**Riscos.**
- Depende da frente de comissão: o ajuste para mais ou para menos no primeiro repasse não liquidado é dela. Esta frente entrega o resumo novo e chama a função na mesma transação.
- A Planilha pode desfazer o "pago" de uma devolução depois de um complemento, deixando duas abertas: a consolidação do passo 2 cobre.
- BV negociado digitado errado no cancelamento não tem correção por este endpoint: ver a pergunta em aberto.
- A DRE do mês do cancelamento é reescrita a cada alteração — aceito pela spec (spec.md:754-756).

**Verify.** Cenário 23a: aberta 600 → total 800: a MESMA SpecialExpense passa a 800, sem linha nova, retido 200. Depois de marcada paga, total 500 → 409 (cenário 23b, deve falhar). Paga 600, total 800 → nova SpecialExpense de 200 a pagar; o resumo lista as duas (cenário 29). Total acima do pago → 400. Aberta 600, total 0 → gasto excluído, `refund_mode` 'nada', retido 1.000. No banco tratada como paga. COMERCIAL e FINANCEIRO reais → 403 (cenário 39). Evento não cancelado → 409. Duas chamadas iguais não duplicam. Tudo conferido por conexão separada, inclusive o EventLog.

**Revisão adversarial: parcial.** Alvo como novo total, piso = pagas + no banco, teto = pago e consolidação das abertas cumprem a FR-015a e os cenários 23a/23b/29. Problemas: (1) a trava `with_for_update` sobre as devoluções não trava nada quando não há devolução (cancelado com 'Nada' → alterar para 300): duas chamadas criam dois complementos. (2) Colisão com a D8: a D6 altera valor e exclui justamente o gasto que a D8 trava — se reusar `gastos_ops.edit_expense/delete_expense` (como manda o Princípio I) leva GastoLockedError; o contrato não diz por onde escreve. (3) `_registrar_devolucao` não aceita descrição nem data: 'reusa' exige mudar a assinatura. (4) Devolução aberta com `disbursement_type` NULL (vítima do 'Salvar' antigo) recebe valor novo e continua invisível na Planilha — nunca será paga. (5) Regravar `refund_mode` (ver D1).

**Emenda.** (1) Primeiro passo: `with_for_update` na linha do evento (ou em event_cancellations), depois ler as devoluções. (2) `alterar_devolucao` escreve direto no ORM dentro de cancel_ops e registra AuditLog pelo `_log` de gastos_ops (ações 'edit'/'delete' com detalhe 'pela alteração da devolução do evento'); deixar explícito no plano que é o único caminho que passa pela trava. (3) `_registrar_devolucao(event, devolucao, actor, *, complemento: bool = False)` muda só a descrição. (4) Ao tocar a aberta, regravar `disbursement_type='cliente'` e completar nome/PIX vazios. (5) Não regravar `refund_mode`. Linha nova no docs/01 §4.3 e comentário `RBAC:` no endpoint (SUPERADMIN real via `_can_delete`).

**Evidência da revisão.** app/calendar/cancel_ops.py:158-191; app/gastos/gastos_ops.py:85-99, 356-360, 381-442; app/api/financeiro_write.py:142-156, 306-318; app/financeiro/routes.py:1170-1177, 1388-1395; app/api/financeiro_read.py:691-702 (Planilha exige `disbursement_type` não nulo); spec.md:489-494, 410-411; constitution.md:27-35, 216-222

## D7 — Como corrigir o "Salvar" de Gastos Extras que apaga destinatário, nome e PIX da devolução (FR-015b)?

**Decisão.** Corrigir nas duas pontas, com o servidor resistindo ao bundle antigo. Backend: `_validate_expense_data` ganha o ramo "cliente"; em `edit_expense`, gasto que já é "cliente" mantém o tipo e só troca nome ou PIX quando chega valor não vazio. Devolução de evento cancelado nunca recebe `approved_with_edits`. Frontend: o formulário carrega e reenvia nome e PIX do tipo "cliente", mostra o rótulo "Devolução à cliente" e a linha da tabela deixa de chamá-la de "fornecedor".

**Porquê.** A causa está em três pontos. `_validate_expense_data` só conhece "reembolso" e "fornecedor"; o `else` zera tipo, nome e PIX (gastos_ops.py:222-238). `formFromExpense` só carrega nome e PIX de "fornecedor", e `buildPayload` só os envia para "fornecedor" (GastosExtrasPage.tsx:155-158, 313-316). `edit_expense` grava o resultado e, como o tipo mudou, liga `approved_with_edits` (gastos_ops.py:408-436). A Planilha filtra `disbursement_type IS NOT NULL` (financeiro_read.py:695; financeiro/routes.py:1034), então a devolução some. Preservar no servidor quando o corpo vem sem nome cobre o bundle em cache.

**Alternativas rejeitadas.** Corrigir só o frontend. Rejeitada: o bundle antigo continuaria destruindo a devolução. Proibir toda edição da devolução em Gastos Extras. Rejeitada: a spec mantém o Financeiro corrigindo nome e PIX.

**Contrato.** `_validate_expense_data`: ramo `elif disbursement_type == "cliente":` lê `supplier_name` e `supplier_pix` sem exigir (a preservação é de `edit_expense`).

`edit_expense`: se `expense.disbursement_type == "cliente"`, o tipo fica "cliente" e `supplier_name` / `supplier_pix` = valor do corpo quando não vazio, senão o atual. `changed` compara o resultado final: salvar sem mexer não liga a flag. Devolução de evento cancelado: `approved_with_edits` nunca é ligado; a correção de nome ou PIX fica no AuditLog.

Criação: o radio "Como será pago?" não oferece "cliente" — devolução nasce pelo cancelamento.

TS: `DisbursementType = "reembolso" | "fornecedor" | "cliente" | null`; `GastoFormValues.disbursementType` inclui "cliente"; `formFromExpense` e `buildPayload` tratam "cliente" como "fornecedor" para nome e PIX.

**Pontos de toque.**
- app/gastos/gastos_ops.py:222-238 (_validate_expense_data)
- app/gastos/gastos_ops.py:407-436 (edit_expense)
- app/api/gastos_write.py:115-148 (PATCH — sem mudança de contrato)
- app/api/gastos_read.py:31-57 (_expense_dict)
- frontend/apps/internal/src/pages/GastosExtrasPage.tsx:118-130, 148-162, 164-242, 308-318, 523-534
- frontend/apps/internal/src/lib/gastos.ts:5, 105, 144 (tipos ganham "cliente")

**Riscos.**
- `approved_with_edits` para devolução de evento vivo segue a regra atual (liga quando algo muda). A exceção é só a do cancelado, leitura literal da FR-015b.
- Devolução já destruída antes do deploy (categoria devolução com tipo NULL) não é reparada. Com zero uso do Cancelar em produção não deve existir; o plano confere por contagem.

**Verify.** Cenário 23c/30: PATCH /api/gastos/<id> de uma devolução com o corpo EXATO do bundle antigo (`disbursement_type: "cliente"`, sem `supplier_name`) → 200; por conexão separada, tipo 'cliente', nome e PIX intactos, `approved_with_edits` falso; a devolução segue em GET /api/financeiro/pagamentos do mês e no resumo do evento. Contra a main o mesmo PATCH zera os três campos (prova por mutação). PATCH trocando só o PIX → PIX novo gravado, tipo preservado.

**Revisão adversarial: parcial.** A causa e o corpo do bundle antigo conferem: `formFromExpense` carrega o tipo 'cliente' mas não nome/PIX, e `buildPayload` manda `supplier_*` como undefined (some do JSON), então chega `disbursement_type: 'cliente'` sem nome — a preservação no servidor cobre. O buraco: o ramo novo 'cliente' fica em `_validate_expense_data`, que é compartilhada com a CRIAÇÃO; `POST /api/gastos` lê `disbursement_type` do formulário sem filtro, então passa a ser possível criar gasto tipo 'cliente' (e, na edição, converter um gasto comum em 'cliente'). 'O radio não oferece' é regra só de tela.

**Emenda.** `_validate_expense_data` ganha parâmetro `tipo_atual: str | None`: 'cliente' só é aceito quando `tipo_atual == 'cliente'` (edição de gasto que já é devolução); em qualquer outro caso → GastoValidationError('disbursement_type', 'Devolução à cliente nasce pelo cancelamento do evento.'). `create_expense` passa `tipo_atual=None`. Em `edit_expense`, gasto 'cliente' mantém o tipo mesmo se o corpo vier '' ou 'fornecedor' (o radio do bundle antigo não marca nenhuma opção) e nome/PIX só trocam com valor não vazio. Verify: POST criando 'cliente' → 400; PATCH de gasto 'fornecedor' para 'cliente' → 400.

**Evidência da revisão.** frontend/apps/internal/src/pages/GastosExtrasPage.tsx:155-158, 180-185, 308-318; app/gastos/gastos_ops.py:222-238, 285-305, 407-436; app/api/gastos_write.py:59-70 (create lê `disbursement_type`), 128-137; app/api/financeiro_read.py:695; app/financeiro/routes.py:1034; constitution.md:223

## D8 — O que Gastos Extras passa a travar na devolução, e o que continua livre?

**Decisão.** A trava vale para devolução de evento CANCELADO: categoria "Devolução a cliente", com `event_id`, de evento com `cancelled_at`. Ficam travados valor, data, categoria, vínculo com o evento e exclusão, com 409 apontando para o evento; livres: nome, PIX e descrição. A trava recusa quando o campo chega DIFERENTE do gravado, não quando chega presente. O espelho também é recusado: criar, editar ou vincular um gasto de modo que ele passe a ser devolução de evento cancelado. Devolução ligada a evento vivo continua editável como hoje.

**Porquê.** Os três caminhos de escrita não têm guarda: PATCH, DELETE e vincular-evento (gastos_write.py:115-148, 151-167, 170-185; gastos_ops.py:356-378, 381-442). Comparar por diferença deixa o formulário, que reenvia todos os campos, salvar a correção de PIX. A categoria entra na trava porque a FR-028 reconhece a devolução por ela. Limitar ao cancelado é a leitura que fecha: só o cancelado tem a outra porta (D6), e o cenário 31 mantém "Devolução a cliente" de evento vivo como gasto comum. O espelho fecha o atalho de mudar o retido por "Vincular evento" sem recalcular comissão.

**Alternativas rejeitadas.** Travar toda devolução ligada a qualquer evento. Rejeitada: a de evento vivo ficaria sem lugar para corrigir. Esconder o gasto de Gastos Extras. Rejeitada: a spec mantém a devolução como saída ali e o Financeiro corrigindo nome e PIX. Travar só na tela. Rejeitada: o frontend não decide regra.

**Contrato.** gastos_ops:
- `devolucao_de_cancelado(expense) -> bool`
- `class GastoLockedError(Exception)` com `field`, `message`, `event_id`
- `edit_expense`: travado e (amount, expense_date, category ou event_id diferente do gravado) → `GastoLockedError(campo, "Devolução de evento cancelado: valor, data, categoria e vínculo se alteram na tela do evento.")`
- `delete_expense` e `link_expense_to_event`: travado → `GastoLockedError`
- espelho, em create, edit e link: resultado com categoria devolução e evento cancelado, vindo de um gasto que não era devolução de cancelado → `GastoLockedError("event_id", "Devolução de evento cancelado só nasce pelo cancelamento ou pela alteração da devolução, na tela do evento.")`

API: `except gastos_ops.GastoLockedError as exc: return json_error(exc.message, 409, fields={exc.field: exc.message}, event_id=exc.event_id)` nos quatro endpoints.

`_expense_dict`: `"locked": bool`, `"event_cancelled": bool` (opcionais no TS).

Tela: com `expense.locked`, o modal desabilita valor, data, categoria e vínculo e mostra o aviso com link para `/events/<event_id>`; a linha esconde "Vincular evento" e "Excluir" e mantém "Editar".

**Pontos de toque.**
- app/gastos/gastos_ops.py:47-57 (exceções — nova `GastoLockedError`)
- app/gastos/gastos_ops.py:256-318 (create_expense — espelho)
- app/gastos/gastos_ops.py:356-360 (delete_expense)
- app/gastos/gastos_ops.py:363-378 (link_expense_to_event)
- app/gastos/gastos_ops.py:381-442 (edit_expense)
- app/api/gastos_write.py:47-77, 115-148, 151-167, 170-185 (capturar a exceção)
- app/api/gastos_read.py:31-57 (_expense_dict ganha `locked` e `event_cancelled`)
- frontend/apps/internal/src/pages/GastosExtrasPage.tsx:88-116, 369-396, 483-590
- frontend/apps/internal/src/lib/gastos.ts:17-30 (campos opcionais)

**Riscos.**
- `api_gastos_delete` tem checagem de papel própria (gastos_write.py:161-165): a guarda fica no núcleo `delete_expense`, e o endpoint precisa capturar a exceção, senão vira 500.
- Os cards de total de Gastos Extras (gastos_ops.py:122-133) continuam somando a devolução — correto, a spec a mantém como saída ali.
- A marcação de pago na Planilha não é travada, por decisão da spec ("o desfazer pago continua").

**Verify.** Cenários 23a e 30 (devem falhar, nada muda por conexão separada): PATCH mudando o valor → 409 `amount` com `event_id` no erro; mudando a data → 409 `expense_date`; mudando a categoria → 409 `category`; DELETE → 409; vincular a outro evento ou desvincular → 409. Deve passar: PATCH com o formulário inteiro igual e só o PIX novo → 200. Espelho: vincular a um cancelado um gasto "Devolução a cliente" → 409; criar gasto dessa categoria com `event_id` de cancelado → 409. Cenário 31: devolução ligada a evento VIVO edita valor normalmente. GET /api/gastos traz `locked: true` só na devolução do cancelado. Cenário 39: FINANCEIRO recusado na alteração do valor.

**Revisão adversarial: parcial.** Trava por diferença (não por presença), limitada a devolução de evento cancelado, mais o espelho: corretos, e o formulário reenvia tudo igual (valor via Decimal, data e evento preservados no estado), então a correção de PIX passa. Não existe Jinja de gastos (app/gastos/routes.py não existe) — a guarda no núcleo cobre tudo. Faltam dois caminhos: (1) `approve_expense`, `reject_expense` e `edit_expense(aprovar=True)` não entram na trava: uma 'Devolução a cliente' pendente ligada ao evento ANTES do cancelamento pode ser aprovada depois e muda devolvido/retido sem recalcular comissão; (2) a exceção da D6 (o próprio sistema altera valor e exclui o gasto travado) não está prevista. Também: `api_gastos_aprovar/rejeitar` só capturam GastoStateError — sem capturar a exceção nova viram 500.

**Emenda.** Estender a trava: `approve_expense` e `reject_expense` (e `aprovar=True` na edição) recusam com GastoLockedError quando `devolucao_de_cancelado(expense)`; capturar a exceção nos SEIS endpoints (create, aprovar, rejeitar, PATCH, DELETE, vincular-evento). Somado à recusa do cancelamento com devolução pendente (D4), fecha o caminho. Documentar que `cancel_ops.alterar_devolucao` é o único escritor autorizado e não passa por `edit_expense/delete_expense`. `locked` e `event_cancelled` opcionais no TS; a tela decide por `expense.locked`, não por papel.

**Evidência da revisão.** app/gastos/gastos_ops.py:321-346, 356-378, 381-442; app/api/gastos_write.py:80-112 (só GastoStateError), 151-167 (DELETE sem try), 170-185; app/api/gastos_read.py:31-57; frontend/apps/internal/src/pages/GastosExtrasPage.tsx:88-116, 148-162; Glob app/gastos/routes.py → inexistente; spec.md:493-494, 640-641

## D9 — O que muda no payload de `resumo_impacto` (FR-011, FR-015), e onde é calculado o efeito na comissão mostrado antes de confirmar?

**Decisão.** `GET /api/events/<id>/impacto-exclusao` (RBAC inalterado) ganha chaves novas, todas opcionais no TS, e um parâmetro `?devolucao=<valor>`. Com ele, o servidor devolve o bloco `efeito`, calculado pela mesma `comissao_do_retido` da D5. A tela não faz conta de dinheiro. `devolucao_sugerida` continua no payload por um ciclo (o bundle antigo a lê), mas o diálogo novo não a usa. O painel "o que está em jogo" do evento marcado lê este mesmo endpoint.

**Porquê.** Hoje o payload traz `devolucao_sugerida = recebido` (cancel_ops.py:99) e o diálogo pré-preenche com ela (ExcluirEventoDialog.tsx:105-110), contra a Clarification. Faltam BV, nota, regime, o que já foi devolvido e o efeito na comissão (cancel_ops.py:95-125). Calcular a prévia no cliente duplicaria a fórmula com arredondamento de float, e a FR-026 exige que nenhuma tela refaça a conta. "Tudo" e "Nada" são duas consultas fixas; "Parte" consulta com debounce.

**Alternativas rejeitadas.** Mandar cheia, venda e comissão paga e calcular no TS. Rejeitada: segunda cópia da fórmula. Endpoint novo só para a prévia. Rejeitada: a função já existe e tem o gate certo. Remover `devolucao_sugerida` já. Rejeitada: backend e frontend sobem separados.

**Contrato.** `resumo_impacto(event, *, devolucao: Decimal | None = None) -> dict`.

Chaves novas:
- `regime`: 'venda' | 'satelite' | 'virtual'
- `sumiu_do_google`: bool (predicado da frente da marca; a tela diz que nada será removido do Google)
- `ja_devolvido`: number (devoluções aprovadas já ligadas ao evento)
- `max_devolucao`: number (= total_recebido − ja_devolvido; é o valor de "Tudo")
- `com_nota`: bool
- `imposto_aliquota`: number (% de referência)
- `bvs`: [{acrescimo_id, recebedor, valor, payment_status, ja_pago}]
- `comissao`: {beneficiario, cheia, paga, a_pagar} — `paga` soma as linhas 'pago' e 'no_banco'
- `efeito` (só com `?devolucao=` válido, entre 0 e max_devolucao): {devolucao, retido, comissao_resultante, desconto_proximo_repasse, comissao_a_pagar_depois, imposto_referencia}

Fórmulas do `efeito`:
- retido = total_recebido − ja_devolvido − devolucao
- comissao_resultante = comissao_do_retido(cheia, retido, venda)
- desconto_proximo_repasse = max(paga − resultante, 0)
- comissao_a_pagar_depois = max(resultante − paga, 0)
- imposto_referencia = retido × alíquota ÷ 100, se com_nota

Valor fora da faixa: `efeito` ausente, sem erro.

Endpoint: `request.args.get("devolucao")` convertido em Decimal; inválido vira None.

**Pontos de toque.**
- app/calendar/cancel_ops.py:77-125 (resumo_impacto)
- app/api/agenda_write.py:484-501 (api_impacto_exclusao — lê o parâmetro)
- app/financeiro/comissoes_ops.py:656-686 (comissão cheia ao vivo, antes do cancelamento)
- app/financeiro/routes.py:129-132 (_get_tax_rate)
- frontend/apps/internal/src/lib/eventOps.ts:96-118 (ImpactoExclusao e hook — a chave da consulta passa a incluir o valor)

**Riscos.**
- O `desconto_proximo_repasse` da prévia tem de bater com o que a frente de comissão grava: as duas usam `comissao_do_retido` e a mesma definição de "paga" (pago mais no banco).
- Uma requisição por valor digitado em "Parte": debounce de 350 ms e só com valor dentro da faixa.
- `acao` continua vindo de `pode_excluir`, que não olha grupo (cancel_ops.py:57-74): satélite vazio marcado cai em "excluir", e o DELETE tenta remover do Google (calendar/routes.py:4232). Pertence à frente da marca; registrado para não se perder.

**Verify.** GET sem parâmetro no exemplo: max_devolucao 1.000, comissao.cheia 90, bvs com 1 item de 200, com_nota falso, sem `efeito`. `?devolucao=600` → retido 400, comissão resultante 18; com a comissão de 90 já paga, desconto 72 (sem BV: 100 → 20 → desconto 80, cenário 20); com a comissão no banco, o mesmo desconto (cenário 21). `?devolucao=1000` → retido 0, resultante 0. `?devolucao=1500` → sem `efeito`. A prévia e o resultado gravado pelo POST batem ao centavo. COMERCIAL real → 403. Satélite → regime 'satelite'.

**Revisão adversarial: parcial.** Calcular o efeito no servidor com a mesma função é certo. O problema é o mecanismo: pôr o valor na chave da consulta do impacto faz cada valor digitado virar consulta nova sem dados; o diálogo renderiza o corpo inteiro sob `{dados && …}` e mostra Skeleton em `impacto.isLoading`, então a cada debounce o formulário desmonta (perde foco) e o efeito em `[impacto.data]` roda de novo e regrava nome (e hoje valor). Além disso cada prévia reexecuta todas as consultas do impacto (elenco, comissões, gastos, contrato) — é o padrão 'requisição por tecla' que o CLAUDE.md aponta como o primeiro a sangrar em deploy. Segundo ponto: a 'cheia' da prévia tem de sair da MESMA função do congelamento (D2), senão prévia e gravado divergem para evento sem vendedor/cortesia.

**Emenda.** Duas consultas: `useImpactoExclusao(eventId, open)` com a chave de hoje (estável, sem o valor) e `usePreviaCancelamento(eventId, devolucao)` com chave própria e `placeholderData: keepPreviousData`. No servidor, `previa_cancelamento(event, devolucao) -> dict` em cancel_ops calcula só o bloco `efeito` (pago, já devolvido, cheia, paga); o endpoint devolve só `{efeito}` quando vem `?devolucao=` — mesmo gate `_can_delete()`. 'Tudo' e 'Nada' usam a mesma prévia com valor fixo. `comissao.cheia` via `comissao_cheia_do_evento` (D2). Manter `devolucao_sugerida` um ciclo.

**Evidência da revisão.** frontend/apps/internal/src/components/EventDetail/ExcluirEventoDialog.tsx:105-110, 163-168; frontend/apps/internal/src/lib/eventOps.ts:111-118; app/calendar/cancel_ops.py:77-125; app/api/agenda_write.py:484-501; app/financeiro/comissoes_ops.py:656-686, 816-827; CLAUDE.md §2 (calculadora dispara request a cada tecla)

## D10 — O que muda na tela do diálogo `ExcluirEventoDialog.tsx`?

**Decisão.** O bloco de devolução vira três opções sem nenhuma marcada (Tudo, Parte, Nada), com "A cliente pagou R$ X" ao lado. O campo de valor só existe em "Parte"; "Tudo" mostra o valor em leitura; nome e PIX só aparecem em Tudo ou Parte. Entram três blocos: "BV — quanto o parceiro recebe" (um campo por BV, vazio), "Imposto sobre o retido" (só com nota, vazio, com a referência ao lado) e "Efeito na comissão" (lido do servidor, D9). O botão Cancelar fica desabilitado até tudo estar informado. Os erros do servidor vão para o campo certo. Satélite e venda virtual mostram só o motivo e a explicação. Os textos que mentem são reescritos (FR-025).

**Porquê.** Hoje o valor nasce preenchido (ExcluirEventoDialog.tsx:100, 105-110), "zerado" significa nada a devolver (218-221), o erro é só `e.message` (149) e o texto promete estorno "no próximo repasse" e saída "das vendas, da DRE e da planilha" (67-71) — falso depois da 303. A linha "Comissão já paga" ignora 'no_banco' (31). O `MoneyInput` só trabalha com `number` (packages/money, MoneyInputProps), então "não informado" precisa de estado próprio para não virar zero.

**Alternativas rejeitadas.** Manter um campo de valor único com "0 = nada". Rejeitada pela Clarification. Sugerir o BV inteiro. Rejeitada pela FR-019. Calcular o efeito no cliente. Rejeitada na D9.

**Contrato.** Estado: `modo: "tudo" | "parte" | "nada" | null` (começa null); `valorParte: number`; `nome` (pode sugerir `cliente_nome`, não é valor); `pix`; `bv: Record<number, number | null>` (null = não informado); `imposto: number | null`; `erros: Record<string, string>`.

Tocar no campo troca null por número. Para BV há o atalho explícito "Nada (R$ 0,00)".

Envio: `{motivo, devolucao: {modo, valor, nome, pix}, bv_negociado: [{acrescimo_id, valor}], imposto_retido}`; em 'nada', `devolucao: {modo: "nada"}`.

Consulta da prévia: `useImpactoExclusao(eventId, open, devolucao)`, em que devolucao = max_devolucao (tudo), 0 (nada) ou valorParte com debounce de 350 ms (parte).

Erros: `if (e instanceof ApiRequestError && e.fields) setErros(e.fields)`. Chaves: motivo, devolucao_modo, devolucao_valor, devolucao_nome, devolucao_pix, bv_negociado, bv_negociado_<id>, imposto_retido.

Casos:
- `max_devolucao === 0`: as três opções somem, aparece "A cliente não pagou nada neste evento — não há o que devolver" e o envio vai com modo 'nada'
- `sumiu_do_google`: "Este evento já não está no Google Agenda — nada será removido de lá."
- BV com `ja_pago`: "Já pago: a Planilha mantém o valor pago; o negociado fica registrado."

Texto novo do painel: "O registro continua existindo. O evento sai da agenda; a comissão passa a valer sobre o que ficou retido, e o que já foi pago a mais é descontado no próximo repasse em aberto."

**Pontos de toque.**
- frontend/apps/internal/src/components/EventDetail/ExcluirEventoDialog.tsx:30-74 (ResumoImpacto: texto e 'no_banco')
- ExcluirEventoDialog.tsx:99-118 (estado e pré-preenchimento)
- ExcluirEventoDialog.tsx:123-152 (confirmar e erros)
- ExcluirEventoDialog.tsx:200-264 (bloco de devolução)
- ExcluirEventoDialog.tsx:278-287 (botão)
- frontend/apps/internal/src/lib/eventOps.ts:96-150 (tipos e hooks; comentário em 125-128)
- frontend/apps/internal/src/components/EventDetail/EventHeader.tsx:304-324 (abre o diálogo — não muda)

**Riscos.**
- Browser pane e inputs React: a conferência de tela precisa do setter nativo com dispatch.
- Diálogo Radix que não desmonta: o estado precisa zerar ao fechar (hoje zera só motivo, PIX e erro, linhas 112-118); modo, BV e imposto entram no reset.
- Bundle antigo em cache: coberto pela recusa da D4.

**Verify.** Conferência de tela como Superadmin (skill manto-conferir-tela): abrir em evento com venda, BV e nota — nenhuma opção marcada, botão desabilitado; escolher Parte e digitar 600 → o bloco de efeito mostra retido 400 e o desconto; BV e imposto vazios bloqueiam o botão; erro do servidor aparece sob o campo. Evento marcado mostra a frase do Google. Satélite mostra só o motivo. Evento sem pagamento não mostra as três opções. `cd frontend && npm run typecheck` limpo.

**Revisão adversarial: parcial.** Três opções sem marcação, BV e imposto com 'não informado' separado de zero e erros por campo cumprem a Clarification. Faltam: (1) janela de deploy no sentido inverso — bundle NOVO contra backend ANTIGO (os dois serviços sobem separados): o endpoint antigo ignora `modo`, `bv_negociado` e `imposto_retido`, cancela pela regra da 224 (estorno cheio, sem congelar) e responde 200; nasce um cancelado 'legado' com devolução sem ninguém perceber. (2) O efeito que pré-preenche a partir de `impacto.data` roda a cada refetch (staleTime 0) e sobrescreve o que o Superadmin digitou; o reset ao fechar hoje não limpa valor nem nome. (3) O diálogo é único para excluir e cancelar: satélite vazio continua caindo em `acao='excluir'` e o DELETE tenta o Google — fica com a frente da marca, mas o diálogo novo não pode esconder isso.

**Emenda.** (1) Trava de capacidade: se `dados.regime === undefined` (payload antigo), o botão Cancelar fica desabilitado com 'O sistema está atualizando — tente em um minuto'; nenhum envio. (2) Sugerir o nome uma vez por abertura (efeito em `[open]` + primeira chegada dos dados), nunca a cada refetch; o reset ao fechar inclui modo, valorParte, nome, pix, bv, imposto e erros. (3) Prévia pela consulta separada da D9. (4) Em 'tudo', enviar `valor = max_devolucao` lido da última resposta; no 409 de divergência, refazer o impacto e mostrar o valor novo. Conferência de tela com setter nativo (armadilha conhecida dos inputs React).

**Evidência da revisão.** frontend/apps/internal/src/components/EventDetail/ExcluirEventoDialog.tsx:99-118, 142-152, 200-264, 278-287; frontend/apps/internal/src/lib/eventOps.ts:96-150; app/api/agenda_write.py:556-566 (endpoint atual ignora chaves desconhecidas); app/calendar/cancel_ops.py:57-74 e 96; render.yaml (backend e frontend são serviços separados — CLAUDE.md §2)

## D11 — Como o evento cancelado e a página de Cancelamentos recebem a devolução e o retido (FR-014), e como a Planilha lê o BV negociado (FR-019) a partir deste modelo?

**Decisão.** O detalhe do evento ganha o bloco opcional `event.cancelamento`, que é o resumo serializado da D5, só para quem vê dinheiro e com PIX só para quem vê financeiro; o botão "Alterar devolução" usa o flag `can_delete` que já existe. `listar_cancelamentos` troca `_devolucao` por `resumos_cancelados`, mantendo a chave `devolucao` (primeira devolução) por um ciclo e acrescentando `resumo`. Para a Planilha, `cancel_ops` expõe `bv_da_planilha(acrescimo)`, chamada dentro de `_build_bv_items`, o único ponto comum às duas telas.

**Porquê.** O detalhe hoje só traz `cancelled_at`, `cancelled_by` e `cancellation_reason` (agenda_read.py:714-718). `_build_bv_items` é compartilhado pela API e pelo Jinja (financeiro_read.py:706-715; financeiro/routes.py:1043-1052, 870-901) e usa `a.amount_brl` direto: mudar ali cobre "tela nova e antiga" com um toque mínimo no arquivo do Jinja vivo. A regra de qual valor aparece depende do modelo da D1, por isso a função mora em `cancel_ops`.

**Alternativas rejeitadas.** Endpoint separado para o resumo do evento. Rejeitada: a tela já carrega o detalhe. Filtrar o BV do cancelado nas duas consultas da Planilha. Rejeitada: esconderia BV já pago, contra a FR-019. Flag novo `can_alterar_devolucao`. Rejeitada: `can_delete` já é o mesmo gate.

**Contrato.** `serialize_event_detail`: `"cancelamento": serializar_resumo_cancelado(resumo_cancelado(event), com_pix=flags["show_financeiro"]) if event.is_cancelled and (flags["show_comercial"] or flags["show_financeiro"]) else None`.
TS: `cancelamento?: ResumoCancelado | null`.

`listar_cancelamentos`: cada cancelado ganha `"resumo": {...}`; `"devolucao"` continua com id, amount, payee_name e payment_status da primeira devolução.

`bv_da_planilha(acrescimo: EventAcrescimo) -> Decimal | None` (None = não mostra):
- evento não cancelado → `amount_brl`
- cancelado sem linha (legado) → `amount_brl` se o status é pago ou no_banco, senão None
- com linha filha de `acrescimo_id == acrescimo.id` → `amount_brl` se `paid_at_cancellation`; senão `negotiated_amount`, ou None quando zero
- cancelado com linha mas sem filha para o acréscimo → None

`_build_bv_items`: `valor = bv_da_planilha(a); if valor is None: continue; "amount": valor`.

**Pontos de toque.**
- app/api/agenda_read.py:714-718 (bloco do cancelado) e 149-198 (flags)
- app/calendar/cancel_ops.py:322-383 (listar_cancelamentos)
- app/financeiro/routes.py:870-901 (_build_bv_items — única edição no Jinja vivo desta frente)
- app/api/financeiro_read.py:706-715 e app/financeiro/routes.py:1043-1052 (consultas de BV — não mudam)
- frontend/apps/internal/src/lib/agenda.ts:300-305 (tipo do evento)
- frontend/apps/internal/src/lib/eventOps.ts:194-208 (EventoCancelado)
- frontend/apps/internal/src/pages/EventosCancelamentosPage.tsx:29-32 (rótulo de 'no_banco')

**Riscos.**
- FR-037 e FR-038 (grade "Resultado do cancelamento", filtros da página) são da frente de sinalização. Esta decisão só entrega o payload; se a 303 for dividida em 303b, o bloco `cancelamento` fica na 303.
- `bv_da_planilha` toca `a.event.cancelamento` por acréscimo: só dispara consulta para evento cancelado.
- CSV da Planilha (financeiro_write.py e o gêmeo Jinja): não conferi se reusa `_build_bv_items`; o plano confere antes de prometer o BV negociado no CSV.

**Verify.** Cenário 12/18: GET /api/events/<id> do cancelado traz `cancelamento.devolvido` 600, `a_devolver` 600, `retido` 400, devolução em 'a_pagar'; depois de marcar paga na Planilha → 'paga' e `a_devolver` 0. COMERCIAL vê o bloco sem PIX; CASTING não recebe o bloco. Cenário 23: Planilha do mês do evento, na API e na tela antiga: BV negociado 50 aparece com 50; negociado 0 não aparece; BV pago no ato aparece com 200 e status pago; cancelado legado sem linha não mostra BV não pago. GET /api/events/cancelamentos com duas devoluções traz as duas em `resumo.devolucoes`.

**Revisão adversarial: parcial.** Mudar só `_build_bv_items` cobre as duas Planilhas (API e Jinja importam a mesma função) — toque mínimo correto. O risco do CSV está resolvido: os dois exports só trazem cachês, não há BV no CSV. O defeito está na regra `bv_da_planilha`: 'cancelado com linha mas sem filha → None'. Nos regimes 'satelite' e 'virtual' a linha existe e NUNCA há filhas, e satélite pode ter acréscimo BV próprio (agrupar zera campos, não apaga `EventAcrescimo`; o KPI do grupo soma os BVs dos satélites). Resultado: cancelar um satélite esconde da Planilha o BV dele, inclusive já pago — contra a FR-019 ('nunca escondido') e contra o caso de borda 'satélite sai sem mexer em BV'. No regime 'venda', acréscimo sem filha (criado depois pelo vínculo de orçamento) também some mesmo estando pago. Falta ainda: regressão de dinheiro (PARADA exige main × branch) e quem abre o GET /events/cancelamentos ao FINANCEIRO — hoje o gate é `_can_delete()`, e o payload passa a levar PIX.

**Emenda.** `bv_da_planilha(acrescimo)`: evento vivo → `amount_brl`; cancelado de regime 'satelite' ou 'virtual' → `amount_brl` (não mexe); regime 'venda' com filha → `amount_brl` se `paid_at_cancellation`, senão o negociado (None quando zero); regime 'venda' sem filha ou 'legado' → `amount_brl` se o status é pago/no_banco, senão None. Verify: satélite cancelado com BV pago continua na Planilha; e regressão — itens de BV de todos os meses do espelho sem cancelado idênticos entre main e branch. Definir no plano: o gate de leitura de /events/cancelamentos ganha FINANCEIRO (FR-038) e `com_pix` na lista segue `show_financeiro`. Import de `bv_da_planilha` dentro de `_build_bv_items` (tardio), para não criar ciclo calendar ↔ financeiro.

**Evidência da revisão.** app/financeiro/routes.py:870-901, 1043-1052, 1408-1433 (CSV só cachês); app/api/financeiro_read.py:655-663, 706-715; app/api/financeiro_write.py:497-533 (CSV só cachês); app/calendar/group_ops.py:47-52 e 96-99 (agrupar não apaga acréscimos); app/api/agenda_read.py:384-390 (BV dos satélites no KPI), 149-198, 714-718; app/api/agenda_write.py:609-618 (gate `_can_delete`); docs/PARADA_REMOCAO_JINJA.md:89-91; spec.md:511-516, 393-395

## O que a frente deixou de decidir (revisão)

- Devolução pendente no ato: nenhuma decisão trata o gasto 'Devolução a cliente' com status 'pendente' já ligado ao evento quando ele é cancelado. `approve_expense` (app/gastos/gastos_ops.py:321-330) e `edit_expense(aprovar=True)` (430-433) aprovam depois sem recalcular retido nem comissão. Decidir: recusar o cancelamento enquanto houver pendente + trava de aprovar/rejeitar em devolução de cancelado.
- Janela de deploy no sentido bundle novo × backend antigo: o endpoint atual (app/api/agenda_write.py:556-566) ignora `modo`, `bv_negociado` e `imposto_retido` e cancela pela regra da 224 com 200. A frente só tratou bundle antigo × backend novo. Falta a trava de capacidade no diálogo (payload sem `regime` = não envia) e a ordem de subida no plano.
- Concorrência: `cancelar_evento` e `alterar_devolucao` não travam a linha do evento. Clique duplo no cancelar vira IntegrityError no UNIQUE (500) depois de duas chamadas ao Google; duas alterações simultâneas em cancelado sem devolução criam dois complementos. Falta `with_for_update` no evento e o mapeamento IntegrityError → 409.
- Definição única da comissão cheia: `_event_commission` não zera para cortesia nem para evento sem beneficiário (app/financeiro/comissoes_ops.py:656-686); o que decide se há linha é o `should_have` (816-827). A frente precisa fixar, junto com a frente de comissão, UMA função usada no congelamento, na prévia e na linha — senão resumo/DRE e Planilha divergem (FR-020).
- As duas perguntas em aberto da proposta precisam de resposta do dono ANTES do /speckit-tasks, porque o cancelamento é irreversível (não existe 'descancelar'; único escritor de `cancelled_at` é cancel_ops.py:288): (a) comprovante esquecido ou com valor errado depois do cancelamento; (b) BV negociado digitado errado. Com as travas como estão, nenhum dos dois tem conserto pelo sistema.
- Terceiro escritor em evento cancelado: `PATCH /api/events/<id>/orcamento` (app/calendar/orcamento_evento_ops.py:350-404 → 275-313) grava venda, `with_invoice` e acréscimos sem checar cancelado; e `validar_agrupamento` (app/calendar/group_ops.py:116-139) aceita cancelado como satélite ou líder — agrupar zera a venda e chama a sincronização de comissão. A FR-036 cobre só os seletores; decidir qual frente põe a recusa no núcleo.
- BV de satélite: satélite mantém linhas de `EventAcrescimo` depois de agrupar (group_ops.py:47-52) e elas aparecem na Planilha pelo mês do próprio satélite. A frente não decidiu o que a Planilha mostra para o BV de satélite cancelado (a regra proposta o esconde, até o pago).
- Conteúdo do rastro (FR-023): falta fixar o texto do EventLog/`_log_sync` do cancelamento com modo, valor devolvido, retido, BV negociado por recebedor e imposto; e o AuditLog do gasto alterado/excluído pela D6.
- Gate e PIX da página de Cancelamentos: a FR-038 abre a leitura ao FINANCEIRO, mas `api_listar_cancelamentos` é `_can_delete()` (agenda_write.py:609-618) e a lista traz também os pedidos pendentes. Falta decidir qual frente muda o gate, o que o Financeiro vê dos pendentes e o `com_pix` do `resumo` na lista.
- Contagens antes do deploy (só leitura em produção) que o plano deve listar: eventos com `cancelled_at` preenchido (legado); SpecialExpense de categoria devolução com `disbursement_type` NULL (vítimas do 'Salvar'); devoluções pendentes ligadas a evento; acréscimos BV em satélites.
- Verify: regressão de dinheiro na Planilha (itens de BV e totais de todos os meses sem cancelado, main × branch — docs/PARADA_REMOCAO_JINJA.md:89-91); stub de `app.calendar.service.delete_event` em todo cenário que cancela evento não marcado (o manto_local tem token real e não há trava — FR-024); cenários que DEVEM falhar para criar gasto tipo 'cliente' e aprovar devolução de cancelado.
- Constituição II: regimes ('venda', 'satelite', 'virtual', 'legado'), modos ('tudo', 'parte', 'nada') e estados da devolução precisam ser constantes em app/constants.py, e `cancelar_evento`/`alterar_devolucao` têm de ser fatiadas em funções de ~30 linhas — o plano descreve as duas como blocos únicos.
- Dívidas a registrar no docs/05 por esta frente: handlers Jinja de comprovante sem guarda de cancelado (app/calendar/routes.py:1015-1094, só alcançáveis direto no backend); `gcal_delete` do cancelamento sem trava fora da produção; devolução destruída antes do deploy não reparada automaticamente.

## Perguntas em aberto da frente

- Depois de cancelado, a cliente ainda pode pagar algo (multa de cancelamento, por exemplo) que precise de comprovante novo no evento? O plano adota a trava da D3: comprovantes do cancelado ficam congelados para todos os papéis. Se o caso existe na operação, a saída é liberar só ao Superadmin, recalculando retido e comissão pela mesma função da alteração de devolução.
- O BV negociado informado no cancelamento pode ser corrigido depois? A spec só prevê alterar devolução e imposto (FR-015a, FR-013). O plano adota: não é alterável na 303. Se o dono quiser, entra como campo opcional no mesmo PATCH da D6, só para BV ainda não pago.