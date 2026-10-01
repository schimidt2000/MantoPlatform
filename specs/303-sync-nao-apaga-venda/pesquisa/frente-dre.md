# Frente dre

DRE com o retido (FR-027 a FR-031, SC-007) — app/financeiro/dre_ops.py (novo), _compute_drg, as duas views da DRE (API e Jinja), dashboard.html, payload /api/financeiro/dashboard + tipos TS, e o arnês main×branch do verify

Tamanho: M — 1 módulo novo (app/financeiro/dre_ops.py, ~150 linhas), 1 parâmetro e 2 chaves em _compute_drg, ~45 linhas trocadas nas duas views, 1 linha de DRE no template Jinja, tipos TS opcionais + linha/rodapé/barra (P1) e card/botão (P2, destacáveis para a 303b sem mexer no backend), sem migration nesta frente. O item mais caro é o arnês main×branch do verify (dre_retrato.py + worktree da main). Depende de duas entregas de outra frente: o resumo do cancelado em lote (FR-026) e a trava de categoria/vínculo da devolução em Gastos Extras (FR-015a).

## DRE-a — (a) Onde moram as funções comuns novas e quais são as assinaturas (cancelamentos do período por cancelled_at, gastos extras sem devolução de cancelado, tendência filtrada)?

**Decisão.** Módulo novo e puro `app/financeiro/dre_ops.py` (mesmo padrão de nome de comissoes_ops/vendas_ops/cobranca_ops), com 1 constante e 4 funções. As duas views passam a ler dele; `_compute_drg` NÃO se move. `dre_ops` importa `app.calendar.cancel_ops` no topo (cancel_ops só importa `app`/`models` no topo — cancel_ops.py:24-34 — e `app/calendar/` não tem `__init__.py`, então não puxa `calendar/routes`); o que ele precisa de `financeiro/routes.py` (`_is_permuta`, `_month_range`, `_prev_month`, `_pct`) entra por import tardio dentro de `tendencia_mensal`, como `vendas_ops.py:244/266/313` já faz. As views importam `dre_ops` de forma tardia dentro da própria view (é como `financeiro_read.py:191-212` e `routes.py:304` já importam tudo). Conjunto único de "cancelado que entra na DRE": `cancelled_at` dentro de [start 00:00, end 23:59:59.999999] (mesmos limites de `start_dt`/`end_dt` das views), `group_leader_id IS NULL` (satélite fora — FR-029), `event_type IS NULL OR event_type NOT IN ('ENSAIO','VIRTUAL')` (forma null-safe de propósito: o `event_type != 'ENSAIO'` de hoje, financeiro_read.py:230, descarta tipo NULL por lógica de três valores; num cancelado isso faria a devolução sair de Gastos Extras sem o retido entrar). Devolução excluída de Gastos Extras = literal da FR-028: `category == SpecialExpense.CATEGORY_DEVOLUCAO` E `event_id` de evento com `cancelled_at IS NOT NULL` — nunca por `disbursement_type`.

**Porquê.** A API copia o corpo do Jinja (financeiro_read.py:225-264 × routes.py:274-319; tendência :365-385 × :394-415): qualquer regra escrita inline nas duas diverge em silêncio — é o risco nº 2 da proposta. Um `_ops` novo cumpre o Princípio III sem tocar a exceção histórica (nada sai de routes.py). cancel_ops continua dona do resumo por evento (FR-026); dre_ops só decide PERÍODO e agregação, sem refazer conta de evento. `cancelled_at` é naive São Paulo (cancel_ops.py:272, 288), o mesmo relógio de `start_at`, então o recorte por mês não precisa de conversão. Não há índice em `cancelled_at` (models.py:238-241) e não precisa: a tabela tem ~1,3 mil linhas e zero/poucos cancelados.

**Alternativas rejeitadas.** (1) Pôr as funções em `app/calendar/cancel_ops.py`: rejeitado — gastos extras e tendência são regra da DRE, não do cancelamento, e cancel_ops passaria a importar helpers de `financeiro/routes`. (2) Escrever inline nas duas views: rejeitado — é a duplicação que já fez as telas divergirem (ticket médio, a receber). (3) Criar `financeiro_ops.py` como o docs/05 §9.2 planeja e já mover `_compute_drg`/`_resolve_period`: rejeitado — refatoração lateral em código de dinheiro, proibida pela spec (Fora de escopo) e pela PARADA_REMOCAO_JINJA. (4) Reconhecer a devolução por `disbursement_type='cliente'`: rejeitado — qualquer "Salvar" em Gastos Extras zera esse campo (gastos_ops.py:222-238, 424) e a devolução voltaria à DRE. (5) Amarrar a exclusão da devolução ao mesmo predicado do retido (não excluir devolução de satélite/virtual): rejeitado — a FR-028 e o invariante do docs/04 dizem "devolução de cancelado nunca é gasto na DRE"; a anomalia (devolução em satélite/virtual cancelado) é bloqueada na origem pela frente do cancelamento e contada antes do deploy.

**Contrato.** ```python
# app/financeiro/dre_ops.py
ROTULO_RETIDO = "Retido de cancelamentos"

def cancelamentos_do_periodo(start_date: date, end_date: date) -> list[dict[str, Any]]:
    """Um dict por cancelado com cancelled_at no período, do mais recente ao mais antigo.
    Chaves: event (CalendarEvent), event_id, title, start_at, cancelled_at,
    pago, devolvido, devolvido_a_pagar, retido, comissao_retido, bv, imposto,
    efeito_resultado (= retido - imposto - bv - comissao_retido) — todos Decimal 0.01."""

def totais_cancelamentos(resumos: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """{quantidade:int, pago, devolvido, devolvido_a_pagar, retido, comissao_retido, bv,
    imposto, efeito_resultado: Decimal}. Lista vazia -> quantidade 0 e Decimal('0')."""

def gastos_extras_do_periodo(start_date: date, end_date: date) -> Decimal:
    """A MESMA consulta de hoje (status=='aprovado', expense_date no período) + um filtro:
    ~SpecialExpense.id.in_(select id de SpecialExpense JOIN CalendarEvent onde
    category==CATEGORY_DEVOLUCAO e cancelled_at IS NOT NULL). Soma em Python, como hoje:
    sum((Decimal(g.amount) for g in rows), Decimal('0'))."""

def tendencia_mensal(today: date, meses: int = 6) -> list[dict[str, Any]]:
    """Do mês mais antigo ao corrente: {label, receita, custo, lucro, margem, n_eventos, retido}."""
```
Contrato CONSUMIDO (dono: frente do cancelamento/FR-026), em `app/calendar/cancel_ops.py`: `resumos_cancelados(events: Sequence[CalendarEvent]) -> dict[int, dict[str, Any]]`, em lote (consultas agregadas, não uma por evento), com no mínimo `pago`, `devolvido` (soma de TODAS as devoluções), `devolvido_a_pagar` (só `payment_status=='nao_pago'`; `no_banco` conta como pago), `retido` (>= 0), `comissao_retido`, `bv_conta`, `imposto_retido` — Decimal, lidos do que foi gravado no cancelamento; satélite e VIRTUAL devolvem retido/comissão/BV/imposto zero. Se a outra frente nomear diferente, só o adaptador dentro de `cancelamentos_do_periodo` muda.

**Pontos de toque.**
- app/financeiro/dre_ops.py (NOVO; ruff format só nele)
- app/calendar/cancel_ops.py:47-54 (total_recebido — base do resumo; a função em lote do resumo é da frente FR-026)
- app/calendar/cancel_ops.py:174-189 (devolução nasce aprovada, categoria CATEGORY_DEVOLUCAO, event_id preenchido — é o que a exclusão casa)
- app/models.py:1021 (SpecialExpense.CATEGORY_DEVOLUCAO)
- app/models.py:287 (cancelled_at, sem índice)
- app/financeiro/vendas_ops.py:244 (padrão de import tardio a repetir)
- app/financeiro/comissoes_ops.py:615-620 (_group_cost, importável no topo)
- app/gastos/gastos_ops.py:408-428 (categoria e vínculo hoje editáveis — a trava da FR-015a é pré-requisito da exclusão)

**Riscos.**
- Depende de a frente do cancelamento travar categoria, vínculo e exclusão da devolução em Gastos Extras (FR-015a/FR-015b): sem a trava, trocar a categoria devolve os −600 à DRE (cenário 30).
- Cancelado anterior à 303 (sem valores gravados) entra com retido = pago − devolvido e comissão/BV/imposto zero. A spec registra zero uso em produção; o plano conta `calendar_events WHERE cancelled_at IS NOT NULL` e devolução em satélite/VIRTUAL cancelado na produção antes do deploy (esperado 0 e 0).
- Se `resumos_cancelados` fizer consulta por evento, a página de Cancelamentos (até 200) e a tendência (janela de 6 meses) viram N+1 — exigir a versão em lote.

**Verify.** Cenário 31: gasto "Outros" aprovado ligado ao cancelado (multa) e "Devolução a cliente" ligada a evento VIVO continuam em gastos_extras (dois controles positivos — sem eles a exclusão poderia estar apagando tudo). Cenário 30: depois do "Salvar" em Gastos Extras (disbursement_type mexido), a DRE continua sem a devolução. Cenário 32: satélite cancelado com comprovante e VIRTUAL cancelado não aparecem em `paineis.cancelamentos.eventos` nem mexem em receita_bruta; checar também que `n_cancelados` não conta nenhum dos dois.

**Revisão adversarial: parcial.** O módulo novo, os imports e o predicado null-safe se sustentam. Três furos:

1. `cancelamentos_do_periodo` e `totais_cancelamentos` não são só da DRE. A FR-034 pede o mesmo card no Dashboard Comercial, e a FR-038 pede filtro por mês do cancelamento e total retido na página de Cancelamentos. O Dashboard Comercial é recortado por vendedor no servidor, e a assinatura proposta `(start_date, end_date)` não tem recorte. Morando em `dre_ops`, a frente do Comercial escreve uma segunda função — a duplicação que a decisão quer evitar. A alternativa (1) foi rejeitada olhando só gastos extras e tendência.

2. O conjunto excluído de Gastos Extras e o conjunto somado em `devolvido` não estão amarrados. A exclusão é categoria + evento cancelado; o contrato consumido diz só "soma de TODAS as devoluções", sem predicado nem status. Se o resumo herdar o filtro `disbursement_type="cliente"` de hoje, uma devolução sai de Gastos Extras sem reduzir o retido e a DRE fica inflada. Caminhos que criam essa diferença e que o risco não lista:
- "Devolução a cliente" é categoria selecionável na criação manual, que nasce pendente e aceita vínculo com evento cancelado;
- `link_expense_to_event` é um segundo caminho de troca de vínculo, fora do `edit_expense`;
- rejeitar e reconsiderar mudam o status.

3. `totais_cancelamentos([])` devolve um dict com chaves, que é truthy (ver DRE-b).

**Emenda.** 1. Separar por dono. "Cancelados por mês do cancelamento + totais" vira fonte única das três telas (FR-034 nas duas, FR-038): em `cancel_ops`, ou em `dre_ops` declarado como fonte única, com assinatura `cancelamentos_do_periodo(start, end, *, beneficiario_id: int | None = None)` e `beneficiario_id` em cada resumo. `dre_ops` fica com `gastos_extras_do_periodo` e `tendencia_mensal`.

2. Um predicado único (categoria == CATEGORY_DEVOLUCAO, event_id do evento, status == 'aprovado'), exportado por `cancel_ops` e usado tanto na soma de `devolvido` quanto na exclusão de Gastos Extras. No verify, por cancelado: Σ excluído de gastos_extras == `devolvido` do resumo. Cenário extra: devolução criada à mão em Gastos Extras, ligada ao cancelado, pendente e depois aprovada.

3. Acrescentar `create_expense` e `link_expense_to_event` à lista de travas cobradas da frente do cancelamento.

**Evidência da revisão.** app/api/financeiro_read.py:82-106 e :139-144 (recorte por vendedor no pipeline); spec.md:565-567 (FR-034) e :580-583 (FR-038); app/calendar/cancel_ops.py:339-342 (`.first()` + `disbursement_type="cliente"`); app/models.py:1018-1021 (categoria em CATEGORIES); app/gastos/gastos_ops.py:289-305 (criação pendente com event_id), :363-378 (`link_expense_to_event`), :333-346 e :402-433 (rejeitar/reconsiderar); app/calendar/ sem `__init__.py` e cancel_ops.py:24-34 (import no topo é seguro — confirmado).

## DRE-b — (b) Como `_compute_drg` recebe os cancelados sem mudar o resultado para os chamadores atuais, e quais chaves novas devolve?

**Decisão.** Um parâmetro novo, opcional e por nome, no fim da assinatura: `cancelamentos: Mapping[str, Any] | None = None`, que recebe os TOTAIS já somados por `dre_ops.totais_cancelamentos` (não a lista de eventos). Dentro de um único `if cancelamentos:` a função soma: `receita_bruta += retido`; `impostos += imposto` (depois do quantize dos impostos dos eventos); `cpv += bv`; `comissoes += comissao_retido`. Tudo o mais (receita_liquida, lucro_bruto, margens, ebitda, resultado_liquido) já deriva dessas quatro linhas e não muda de código. Duas chaves novas, SEMPRE presentes: `retido_cancelamentos` (Decimal, 0 sem cancelado) e `n_cancelados` (int). `n_eventos`/`n_normais`/`n_permutas` não mudam (FR-030). As views passam `cancelamentos=` só nas chamadas de Realizado e Total; a de Projetado fica exatamente como está (retido nunca é projetado — FR-027).

**Porquê.** `_compute_drg` tem só dois chamadores em toda a árvore, incluindo scripts/db gitignorado (routes.py:316-319 e financeiro_read.py:262-264; conferido com grep sem respeitar .gitignore), todos posicionais nos 5 primeiros argumentos — um keyword novo com default None não os afeta. Receber os totais, e não os eventos, mantém a FR-026: `_compute_drg` não conhece evento cancelado, não chama `_event_commission`/`_event_bv_total` sobre ele e não importa cancel_ops para dentro de routes.py. Como o card usa o mesmo dict de totais, `efeito_resultado` do card é, por construção, a variação do resultado líquido. O `if cancelamentos:` garante que, sem cancelado, nenhuma operação aritmética nova roda sobre os acumuladores — é o que sustenta o "centavo a centavo" da SC-007.

**Alternativas rejeitadas.** (1) Passar a lista de `CalendarEvent` cancelados e calcular dentro: rejeitado — recalcularia comissão/BV da venda (a aba Comercial do cancelado segue editável) em vez de ler o gravado, e uma edição reescreveria o mês. (2) Não tocar `_compute_drg` e ajustar o dict em cada view (`drg['receita_bruta'] += ...` e refazer as linhas derivadas): rejeitado — duplica a cascata em dois lugares, exatamente o modo de falha atual. (3) Devolver também `bv_cancelamentos`/`comissao_cancelamentos`/`impostos_cancelamentos`: rejeitado — o card já traz a quebra; chave sem consumidor.

**Contrato.** ```python
def _compute_drg(events, settings, salary_cost: Decimal, gastos_extras: Decimal,
                 gastos_recorrentes: Decimal = Decimal("0"),
                 cancelamentos: Mapping[str, Any] | None = None) -> dict:
```
`cancelamentos` lê as chaves `retido`, `imposto`, `bv`, `comissao_retido`, `quantidade` do dict de `totais_cancelamentos`. Retorno: as 17 chaves de hoje, com os mesmos valores quando `cancelamentos` é None/vazio, + `retido_cancelamentos: Decimal` + `n_cancelados: int`.

**Pontos de toque.**
- app/financeiro/routes.py:205-206 (assinatura)
- app/financeiro/routes.py:218-231 (as quatro linhas que recebem soma)
- app/financeiro/routes.py:239-257 (dict de retorno: +2 chaves)
- app/financeiro/routes.py:316, 319 e app/api/financeiro_read.py:262, 264 (chamadas de Realizado e Total ganham `cancelamentos=`)
- app/financeiro/routes.py:318 e app/api/financeiro_read.py:263 (Projetado: intocadas)
- docs/04_GUIA_DE_DOMINIOS.md:237 (cita `routes.py:351`; a função está em :205 — corrigir junto com a regra nova da cascata)

**Riscos.**
- `_floatify` (financeiro_read.py:178-180) serializa as chaves novas sem mudança; um verify antigo que comparasse o conjunto exato de chaves quebraria — conferido: verify_157/189 só leem `receita_bruta`.
- Função legada com mais de 30 linhas ganha ~8: aceitável pelo Princípio II (legado segue o estilo circundante), sem extrair nada.

**Verify.** Cenário 26 (mês do cancelamento, Realizado e Total): retido_cancelamentos 400,00; variações contra o retrato tirado ANTES de criar o evento: receita_bruta +400, impostos 0, cpv +40, lucro_bruto +360, comissoes +18, ebitda +342, gastos_extras 0, resultado_liquido +342; Projetado: retido_cancelamentos 0 e todas as variações 0. Asserção extra: `paineis.cancelamentos.efeito_resultado == variação de dre.total.resultado_liquido`. Cenário 36 cobre o ramo sem cancelado.

**Revisão adversarial: parcial.** O parâmetro opcional por nome se sustenta: `_compute_drg` tem só dois chamadores, todos posicionais, conferido também em `scripts/` e `specs/`.

O que não fecha é a garantia do "centavo a centavo". As views passam `cancelamentos=tot_cancel`, e `totais_cancelamentos([])` devolve um dict cheio de zeros, que é truthy. O `if cancelamentos:` entra sempre e soma `Decimal('0')` nos quatro acumuladores. O valor não muda, mas o expoente pode (`Decimal('1000') + Decimal('0.00')` vira `Decimal('1000.00')`), e a frase "nenhuma operação aritmética nova roda" é falsa como está escrita.

O conserto óbvio, `if retido > 0`, quebra o cenário 32: retido 0 com BV de 200 já pago precisa somar +200 no CPV.

**Emenda.** Fixar a condição no contrato: `if cancelamentos and cancelamentos["quantidade"]:`. Alternativa: as views passam `None` quando a quantidade é 0. Nunca condicionar pelo retido. `n_cancelados` = quantidade. O comparador do retrato compara Decimal por valor, não por texto.

**Evidência da revisão.** app/financeiro/routes.py:205-257 (função), :316-319 e app/api/financeiro_read.py:262-264 (únicos chamadores); grep em scripts/db e specs: verify_157/189/196/214/205/173 só chamam o endpoint; scripts/db/verify_cancelamento_evento.py:248-251 lê `drg_total` de `/api/financeiro/painel`, rota que não existe, atrás de um `if`; spec.md:697 (cenário 32: retido 0, custo +200).

## DRE-c — (c) Qual é a mudança mínima em cada uma das duas views e no template Jinja?

**Decisão.** API (`api_financeiro_dashboard`): (1) :243-250 vira `gastos_extras = dre_ops.gastos_extras_do_periodo(start_date, end_date)`; (2) logo depois, `cancelados = dre_ops.cancelamentos_do_periodo(start_date, end_date)` e `tot_cancel = dre_ops.totais_cancelamentos(cancelados)`; (3) `cancelamentos=tot_cancel` em :262 e :264; (4) barra do retido em :338-345; (5) :365-385 vira `dre_ops.tendencia_mensal(today)` + conversão para float; (6) linhas de cancelado em `eventos` quando `incluir_cancelados`; (7) `CalendarEvent.cancelled_at.is_(None)` em :428-432; (8) selo nas notas a emitir em :456-465; (9) `cancelamentos`/`incluir_cancelados` em `paineis`; (10) corrigir docstring :188-189 e comentário :231-232 (FR-025). Jinja (`dashboard()`): os mesmos (1)-(3) em :294-301 e :316/:319; a barra em :375-379; a tendência em :394-415; o filtro em :469-473; o selo da nota embutido em `event_title` (:496-503), sem tocar o template; comentário :280-282; e o ticket médio (:327-330) passa a dividir a soma de `sale_value` de `eventos_com_venda` — a fórmula que a API já usa em :287-295, sem o recorte de loja. Template: UMA linha de DRE, logo abaixo de Receita Bruta (dashboard.html:123), condicional a haver retido. Nada de card, botão ou linha de cancelado na tela antiga; rodapé (:199-202) intocado; a view não é extraída nem movida.

**Porquê.** É o que a spec autoriza para a tela antiga (Fora de escopo: números das funções comuns, uma linha no template, ticket médio). Trocar o laço da tendência por uma chamada é "número vindo da função comum" — a alternativa seria repetir filtro e soma do retido dentro do laço Jinja. O ticket médio pela soma de `eventos_com_venda` cumpre a letra da FR-030 ("deixar de dividir a Receita Bruta da cascata") e é numericamente igual ao de hoje fora de cancelamento: `receita_bruta` = Σ sale_value dos não-permuta/não-satélite (routes.py:215-218) e `eventos_com_venda` é o mesmo conjunto restrito a sale_value > 0 (:323-326); a diferença só existiria com venda negativa. O selo da nota dentro de `event_title` atende o "nas duas telas" da FR-031 sem segunda mexida no template.

**Alternativas rejeitadas.** (1) Ticket médio = (receita_bruta − retido_cancelamentos) ÷ n: provadamente idêntico, mas mantém o acoplamento que criou o defeito (qualquer linha futura somada à receita infla de novo) e contraria a letra da FR-030; fica como plano B se o cenário 36 acusar diferença. (2) Linha do retido sempre visível, mesmo zerada: rejeitado — ruído em todo mês sem cancelamento. (3) Segunda alteração no template para o selo da nota: rejeitado — estoura o "uma linha" da spec. (4) Extrair Recebimentos Previstos para função comum: rejeitado — é um filtro de uma linha em cada consulta; extrair mexeria mais na view Jinja do que o mínimo.

**Contrato.** Linha Jinja (depois de Receita Bruta):
```jinja
{% if drg_total.retido_cancelamentos %}
<tr>
  <td><span class="dre-op">↳</span> Retido de cancelamentos <small>(pago − devolvido · já somado na Receita Bruta)</small></td>
  <td class="text-right num">{{ money(drg_realizado.retido_cancelamentos) }}</td>
  <td class="text-right num text-muted">{{ money(drg_projetado.retido_cancelamentos) }}</td>
  <td class="text-right num strong">{{ money(drg_total.retido_cancelamentos) }}</td>
</tr>
{% endif %}
```
Ticket médio Jinja: `receita_eventos = sum((Decimal(e.sale_value or 0) for e in eventos_com_venda), Decimal("0"))`; `ticket_medio = (receita_eventos / Decimal(len(eventos_com_venda))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)` (0 sem eventos). Selo da nota no Jinja: `event_title = f"{titulo} — evento cancelado · retido R$ {format_brl(retido)}"`. Contexto do `render_template`: mesmas variáveis; `receita_por_tipo` pode ganhar a chave `ROTULO_RETIDO`; itens de `monthly_trend` ganham `retido`.

**Pontos de toque.**
- app/api/financeiro_read.py:188-189, 231-233, 243-250, 262-264, 338-346, 365-385, 397-423, 425-435, 449-465, 522-535
- app/financeiro/routes.py:280-282, 294-301, 316-319, 323-330, 375-379, 394-415, 466-476, 489-503
- app/templates/financeiro/dashboard.html:118-123 (a linha nova entra depois de :123)
- app/templates/financeiro/dashboard.html:137 (rótulo "CPV (cachês — eventos normais)": troca de texto da FR-025, frente dos textos — mesma linha, não conta como linha nova)
- app/money.py:23 (format_brl, já importado em routes.py:33, para o selo da nota)

**Riscos.**
- Evento com `sale_value` negativo no espelho faria o ticket médio Jinja mudar fora de cancelamento — o cenário 36 compara o ticket do contexto Jinja em todos os meses; se acusar, cai para a alternativa (1).
- `.bar-label` da tela antiga tem 70px com reticências (dashboard.html:551): "Retido de cancelamentos" aparece cortado; aceito por ser tela legada fora da porta pública.
- Mexer só numa das views é silencioso: o typecheck e o ruff não pegam — só a comparação API × contexto Jinja do verify.

**Verify.** Tela antiga exercitada de verdade: `GET /financeiro/?period=custom&start=&end=` com a sessão do login por API, capturando o contexto pelo sinal `flask.template_rendered` (Flask 3.1.2, requirements.txt:1) — compara `drg_realizado/projetado/total` com `dre.*` da API chave a chave (dinheiro a 0,01; margens a 0,1). A linha do template se confere no HTML com âncora: dentro do MESMO `<tr>` que contém "Retido de cancelamentos" tem de haver "R$ 400,00"; e antes do cancelamento a frase não pode existir na página (contraprova). Cenário 33: `ticket_medio` do contexto Jinja igual antes e depois do cancelamento. Mutação manual registrada nas tasks: tirar `cancelamentos=` só da view Jinja tem de derrubar a comparação API × tela antiga.

**Revisão adversarial: sim.** Nada que refute. Conferido:
- o ticket médio pela soma de `eventos_com_venda` é igual ao de hoje fora de venda negativa;
- a macro `money` existe e a linha cabe depois de Receita Bruta;
- `event_title` é usado só como texto do link da nota, então o selo embutido não exige mexer no template.

Três ressalvas pequenas:
1. A linha condicionada a `drg_total.retido_cancelamentos` some no terceiro caso do cenário 32 (retido 0, CPV +200), e a tela antiga fica com custo sem explicação.
2. O filtro de Recebimentos Previstos e o selo da nota vão além da letra do Fora de escopo ("números das funções comuns, uma linha, ticket médio"). Quem os exige é a FR-031 ("nas duas telas").
3. O rótulo "Impostos Provisionados (eventos com nota)" da tela antiga passa a omitir o imposto informado do cancelado.

**Emenda.** 1. Condicionar a linha a `drg_total.n_cancelados`, não ao retido. Ela mostra R$ 0,00 quando há cancelado sem retido.
2. Registrar no plan o desvio justificado: FR-031 acima do Fora de escopo para o filtro e o selo.
3. Na view Jinja, inserir a barra antes do `sorted` e do `max` de `receita_tipo_max`.
4. Registrar o rótulo de impostos da tela antiga no docs/05, já que o limite é uma linha no template.

**Evidência da revisão.** app/financeiro/routes.py:215-218 × :323-330 (mesmo conjunto); app/templates/financeiro/dashboard.html:9 (macro), :118-123, :213-215 (barra divide por `receita_tipo_max`), :325-328 (`n.event_title` só como texto), :125 (rótulo de impostos); spec.md:551-554 (FR-031) × :751-753 (Fora de escopo).

## DRE-d — (d) Qual é o payload novo de `GET /api/financeiro/dashboard` (retido, n_cancelados, card, tabela com incluir_cancelados, Receita por Tipo) e como ficam os tipos no TypeScript?

**Decisão.** Tudo aditivo e opcional no TS. `dre.{realizado,projetado,total}` ganham `retido_cancelamentos` e `n_cancelados`. `paineis.cancelamentos` (sempre enviado; `quantidade: 0` e `eventos: []` sem cancelado) é o card, montado de `totais_cancelamentos` + a lista do período. `paineis.receita_por_tipo` ganha a chave "Retido de cancelamentos" quando retido > 0, somada antes da ordenação (mesmo lugar e padrão da barra "Loja Virtual", :341-342), e entra no `receita_tipo_max`. Parâmetro novo `incluir_cancelados` (mesmo parser de :279: "1"/"true"/"sim"), ecoado em `paineis.incluir_cancelados`; ligado, `eventos` recebe, NO FIM da lista, uma linha por cancelado DO PERÍODO PELO `cancelled_at` (o mesmo conjunto da cascata e do card), com `status: "cancelado"`, `receita` = retido, `custo` = 0, `lucro` = retido, `comissao` = comissão do retido, `is_projetado: false`, mais `cancelado: true` e `cancelled_at`. Desligado (padrão), `eventos` é idêntico ao de hoje. A linha "↳ Retido de cancelamentos" da DreTable, o rodapé e a barra são P1 (História 7); card e botão são P2 (História 8) e podem ir para a 303b sem mudar o backend.

**Porquê.** Backend e frontend sobem separados no Render (~60 s de janela) e o bundle fica em cache: campo novo obrigatório derruba a tela (lição 16f6f1a). Opt-in no servidor garante que bundle antigo nunca recebe `status: "cancelado"`, que não existe em `STATUS_LABEL`/`STATUS_CLASS` (FinanceiroDashboardPage.tsx:60-74). A tabela segue o `cancelled_at`, não o `start_at`, porque é onde o dinheiro entrou: com o botão ligado, as linhas riscadas de setembro somam o que a linha do retido de setembro mostra; pelo `start_at`, o evento de novembro apareceria em novembro com R$ 400 que a cascata de novembro não tem. `custo` = 0 segue a régua das linhas vivas, que é só cachê (:401) — o BV aparece no card.

**Alternativas rejeitadas.** (1) Devolver sempre as linhas de cancelado e filtrar no React: rejeitado — bundle antigo renderizaria status desconhecido, e foge do padrão `incluir_loja_virtual` que a spec mandou repetir. (2) Montar as linhas no React a partir de `paineis.cancelamentos.eventos`, sem parâmetro: economiza um refetch, mas diverge da agenda e da lista de vendas, que usam `incluir_cancelados` no servidor. (3) Recorte das linhas por `start_at`: rejeitado (não fecha com a cascata). (4) Acrescentar "cancelado" a `vendas_ops.event_payment_status`: fica com a frente do Comercial; a DRE atribui o status direto na linha e só precisa do rótulo em `PAYMENT_STATUS_LABELS`.

**Contrato.** `GET /api/financeiro/dashboard?period=&start=&end=&incluir_loja_virtual=&incluir_cancelados=1` — RBAC inalterado (FINANCEIRO, SUPERADMIN; :214).
```ts
interface DreView { /* ...hoje */ retido_cancelamentos?: number; n_cancelados?: number }
interface CancelamentoDoPeriodo {
  event_id: number; title: string; start_at: string | null; cancelled_at: string;
  pago: number; devolvido: number; devolvido_a_pagar: number; retido: number;
  comissao_retido: number; bv: number; imposto: number; efeito_resultado: number;
}
interface CancelamentosResumo {
  quantidade: number; pago: number; devolvido: number; devolvido_a_pagar: number;
  retido: number; comissao_retido: number; bv: number; imposto: number;
  efeito_resultado: number; eventos: CancelamentoDoPeriodo[];
}
interface FinanceiroPaineis { /* ...hoje */ cancelamentos?: CancelamentosResumo; incluir_cancelados?: boolean }
interface MonthlyTrendItem { /* ...hoje */ retido?: number }
interface NotaFiscalPendente { /* ...hoje */ cancelado?: boolean; retido?: number | null }
type EventoStatus = "permuta" | "sem_valor" | "pago_total" | "parcial" | "pendente" | "cancelado";
interface FinanceiroEvento { /* ...hoje */ cancelado?: boolean; cancelled_at?: string | null }
interface PeriodParams { /* ...hoje */ incluirCancelados?: boolean }  // entra na queryKey
```
No endereço da tela o botão guarda `?cancelados=1` (useSearchParams); o hook traduz para `incluir_cancelados=1`.

**Pontos de toque.**
- app/api/financeiro_read.py:279 (parser a repetir), :338-346, :397-423, :500-504, :522-535
- app/financeiro/vendas_ops.py:32-38 (rótulo "cancelado")
- frontend/apps/internal/src/lib/financeiro.ts:7-25 (DreView), :53-60 (MonthlyTrendItem), :80-92 (FinanceiroPaineis), :94 (EventoStatus), :96-110 (FinanceiroEvento), :119-125 (NotaFiscalPendente), :158-171 e :174-192 (PeriodParams, hook e queryKey)
- frontend/apps/internal/src/pages/FinanceiroDashboardPage.tsx:21 e :33-58 (linha nova na cascata; kind "detalhe"), :60-74 (mapas de status), :171 (`dre[view][row.key] as number` precisa de `?? 0` para chave opcional), :410-414 (rodapé), :443-472 (barra; rótulo em `w-16 truncate` na :450 precisa de `title`), :474-514 (card da Loja Virtual como modelo), :692-778 (tabela e botão)
- docs/01_SISTEMA_E_BANCO.md:800 e docs/02_MAPA_DE_PAGINAS_E_UX.md:1572 (contrato e tela)

**Riscos.**
- `Record<EventoStatus, string>` obriga a incluir "cancelado" nos dois mapas — o typecheck acusa, mas só se o tipo for ampliado junto.
- Card e linhas repetem os mesmos números em dois pontos do payload; ambos saem de `cancelamentos_do_periodo`, então não divergem.
- O selo não pode ser só cor (FR-035): a linha riscada precisa da palavra "Cancelado" — conferir na tela aberta, não no tsc.

**Verify.** Sem o parâmetro: `eventos` sem nenhuma linha `status == "cancelado"` e de mesmo tamanho de antes do cancelamento. Com `incluir_cancelados=1`: exatamente uma linha a mais, no fim, com receita 400, custo 0, lucro 400, comissao 18, `cancelado: true`. Card: quantidade 1, pago 1000, devolvido 600, devolvido_a_pagar 600 (vira 0 depois de paga na Planilha — cenário 18), retido 400, comissao_retido 18, bv 40, imposto 0, efeito_resultado 342. DRE de novembro com o botão ligado: a linha NÃO aparece (o recorte é pelo cancelamento). `receita_por_tipo["Retido de cancelamentos"] == 400` na API e no contexto Jinja.

**Revisão adversarial: parcial.** 1. Contrato da linha de cancelado incompleto. Não define `rate`, `event_type` nem `group_label`. `rate` é obrigatório no tipo e a tela renderiza `{e.rate}%`: sem ele sai "undefined%".

2. O parâmetro `incluir_cancelados` no servidor é redundante. `paineis.cancelamentos.eventos` já vai sempre, com os mesmos dados, e a proposta admite a repetição. Entrando na queryKey, o clique zera `query.data` e a página inteira volta ao esqueleto por causa de um filtro de tabela.

3. `vendas_ops.PAYMENT_STATUS_LABELS` não é lido pela DRE. Só `serialize_sale` o usa; os rótulos da DRE são os mapas do React. O touchpoint é da frente do Comercial.

4. Eixo por `cancelled_at`: na DRE do mês do evento, com o botão ligado, o cancelado não aparece, e VIRTUAL cancelado nunca aparece. O SC-008 diz que o botão "o traz". A escolha é coerente com a cascata, mas não é decisão do dono e está sem registro.

5. A linha "↳ Retido" e o hint de impostos deviam depender de `n_cancelados > 0`, não de retido > 0.

**Emenda.** Preferir montar as linhas riscadas no React a partir de `paineis.cancelamentos.eventos`, acrescentando `event_type`. O botão guarda só `?cancelados=1` no endereço: sem parâmetro no servidor, sem refetch, e bundle antigo continua sem receber status novo.

Se o parâmetro ficar, por simetria com agenda e vendas:
- fixar `rate` (taxa congelada, ou 0), `event_type` e `group_label: null` na linha;
- usar `placeholderData: keepPreviousData` no hook.

Nos dois casos:
- tirar vendas_ops.py:32-38 dos touchpoints;
- a coluna Data da linha mostra "cancelado em dd/mm · evento de dd/mm";
- registrar o eixo como premissa do plan, para o dono confirmar.

**Evidência da revisão.** frontend/apps/internal/src/lib/financeiro.ts:96-110 (`rate: number`), :188 (queryKey); FinanceiroDashboardPage.tsx:768-770 (`{e.rate}%`), :733-739, :269-286 (esqueleto quando não há data), :60-74 (mapas de status); app/financeiro/vendas_ops.py:338 (único uso dos rótulos) × app/api/financeiro_read.py:406-423; frontend/apps/internal/src/lib/agenda.ts:72-79 (padrão keepPreviousData); spec.md:736-737 (SC-008), :568-572 (FR-035 não fixa o eixo).

## DRE-e — (e) De onde vem o imposto sobre o retido na DRE?

**Decisão.** Do valor em reais gravado no cancelamento, lido pelo resumo (`imposto_retido`) e somado em `impostos` dentro do `if cancelamentos:` de `_compute_drg`, depois do quantize dos impostos dos eventos vivos. A DRE nunca multiplica `tax_rate` pelo retido e não olha `with_invoice` do cancelado: evento sem nota, ou com nota e imposto informado zero, contribui com 0. Os 16% do retido são só a referência exibida no diálogo de cancelamento (frente do cancelamento). A alteração do imposto junto com a devolução (FR-015a) reescreve o mês do cancelamento, porque a DRE é recalculada a cada abertura.

**Porquê.** Decisão do dono na Clarification de 29/09 ("depende da negociação, dos prazos e do resto — o Superadmin informa"). Aplicar `_get_tax_rate` (routes.py:129-132) ao retido seria recalcular em vez de ler o gravado, contra a FR-026, e mudaria o passado se a alíquota do SiteSetting fosse alterada.

**Alternativas rejeitadas.** 16% × retido quando `with_invoice` (era a D3-A da proposta): rejeitada pelo dono. Provisionar 16% quando o imposto não foi informado em evento com nota: rejeitado — "não informado" e "zero" são a mesma coisa para a DRE; a obrigatoriedade do campo é validação do diálogo.

**Contrato.** `totais_cancelamentos(...)["imposto"]` = Σ `imposto_retido` dos cancelados do período (Decimal 0.01). Em `_compute_drg`: `impostos = impostos + Decimal(cancelamentos["imposto"])`. Nenhuma coluna nova desta frente — onde o valor mora é decisão da frente do cancelamento.

**Pontos de toque.**
- app/financeiro/routes.py:219-223 (linha de impostos de `_compute_drg`)
- app/financeiro/routes.py:112, 129-132 (alíquota que NÃO se aplica ao retido)
- frontend/apps/internal/src/pages/FinanceiroDashboardPage.tsx:36-41 (hint "X% · eventos com nota" — acrescentar "+ imposto informado nos cancelamentos" quando n_cancelados > 0)

**Riscos.**
- O cenário 28 da spec usa 64, que é exatamente 16% de 400: passa verde mesmo se o código estivesse calculando 16% em vez de ler o informado.

**Verify.** Além do cenário 28 (imposto 64 → impostos +64, resultado +278), duas variantes que o tornam honesto: (i) evento com nota e imposto informado 50 → impostos +50 e resultado +292 (prova que é o valor informado, não a alíquota); (ii) evento com nota e imposto informado 0 → impostos +0 (prova que não há provisão automática). Depois de alterar o imposto pela FR-015a, a DRE do mesmo mês reflete o novo valor.

**Revisão adversarial: sim.** Bate com a Clarification de 29/09 e com a FR-026: lê o valor gravado e nunca multiplica a alíquota pelo retido. As duas variantes do cenário 28 (imposto 50 e imposto 0) são necessárias, porque 64 é exatamente 16% de 400. Sem furo de código.

**Emenda.** Só explicitar no contrato: cancelado anterior à 303, ou sem o campo, entra com imposto 0. O hint do React depende de `n_cancelados > 0`.

**Evidência da revisão.** spec.md:91-93 (Clarification), :479-482 (FR-013), :532-533 (FR-026); app/financeiro/routes.py:112, :129-132, :219-222; FinanceiroDashboardPage.tsx:36-41.

## DRE-f — (f) O que muda na Tendência de 6 meses, em Recebimentos Previstos e nas notas a emitir?

**Decisão.** Tendência: as duas views chamam `dre_ops.tendencia_mensal(today)`. Por mês, a consulta de hoje ganha `cancelled_at IS NULL` (cancelado deixa de contar venda, cachê e evento); o retido dos cancelados com `cancelled_at` naquele mês soma em `receita` e em `lucro`, não mexe em `custo` nem em `n_eventos`, e sai também na chave `retido`. O retido da janela inteira vem de UMA chamada a `cancelamentos_do_periodo` (primeiro dia do mês mais antigo até o último do corrente), distribuída por mês do `cancelled_at`. A soma só acontece quando o retido do mês é diferente de zero, para os tipos e valores dos meses sem cancelamento saírem iguais aos de hoje. Recebimentos Previstos: `CalendarEvent.cancelled_at.is_(None)` no filtro da junção, uma linha em cada view. Notas a emitir: a lista continua sem filtro; para nota de evento cancelado a API devolve `cancelado: true` e `retido` (resumo em lote só dos eventos cancelados presentes na lista, que não tem recorte de período), e a view Jinja embute o selo em `event_title`. Custo de notas emitidas fica como está.

**Porquê.** A tendência de hoje não filtra cancelado (financeiro_read.py:369-373; routes.py:399-403): o evento do exemplo continuaria somando +2.000 e +1 evento em novembro. O lucro da tendência é "operacional puro" (receita − cachês, sem BV nem comissão — :375-381), então o retido entra cheio no lucro, na mesma régua dos eventos vivos. `EventInstallment.received` nunca é gravado (models.py:725): sem o filtro, todas as parcelas do cancelado ficam em Recebimentos Previstos para sempre. O que fazer com a nota fiscal do cancelado está fora de escopo — por isso ela fica na lista, só sinalizada.

**Alternativas rejeitadas.** (1) Descontar BV e comissão do retido no lucro da tendência: rejeitado — a tendência não desconta isso de evento vivo; misturaria duas réguas. (2) Tirar da lista a nota a emitir de cancelado: rejeitado pela FR-031. (3) Filtrar cancelado também no custo de notas emitidas: fora de escopo. (4) Filtrar e somar inline no laço de cada view: rejeitado (duplicação).

**Contrato.** `tendencia_mensal(today, meses=6)` devolve, por mês, `{label: "MM/AA", receita, custo, lucro, margem: _pct(lucro, receita), n_eventos, retido}` com os tipos crus de hoje (Decimal/int); a API converte para float; o Jinja usa direto. Nota a emitir na API: `{id, date, event_id, event_title, amount, cancelado?: bool, retido?: float}`.

**Pontos de toque.**
- app/api/financeiro_read.py:365-385 e app/financeiro/routes.py:394-415 (laços substituídos pela função)
- app/api/financeiro_read.py:428-432 e app/financeiro/routes.py:469-473 (filtro de cancelado)
- app/api/financeiro_read.py:449-465 e app/financeiro/routes.py:489-503 (notas a emitir)
- app/models.py:725 (received nunca gravado — dívida para o docs/05, não corrigir aqui)
- frontend/apps/internal/src/pages/FinanceiroDashboardPage.tsx:583-598 (selo na nota) e :622-655 (tendência)
- app/templates/financeiro/dashboard.html:263-274 e :324-336 (consomem as mesmas chaves; sem mudança)

**Riscos.**
- A tendência é ancorada em hoje (financeiro_read.py:366): o mês do evento do exemplo (futuro) não está na janela — sem relógio fixo, o verify não consegue ver a linha de novembro.
- `n_eventos` da tendência conta permuta e satélite (len de todos); continua assim, só sem os cancelados.

**Verify.** Cenário 27: com o relógio do retrato fixado num dia do mês do evento, a linha desse mês não tem os +2.000 nem o +1 evento, e a linha do mês do cancelamento tem receita +400, lucro +400, `retido` 400 e `n_eventos` inalterado. Contra a main, a mesma leitura mostra +2.000 no mês do evento (mutação da tendência). Cenário 34: parcelas do cancelado com vencimento no período ausentes de `recebimentos_previstos` e fora do total (na main, presentes); nota a emitir do cancelado presente com `cancelado: true` e `retido: 400`; no contexto Jinja, o título contém "evento cancelado · retido R$ 400,00".

**Revisão adversarial: parcial.** O filtro na tendência, o filtro nos Recebimentos Previstos e o selo da nota se sustentam; as duas consultas de tendência hoje não filtram cancelado.

O furo é a frase "cancelado deixa de contar venda, cachê e evento". Ela não vale para satélite cancelado. `_group_cost` soma `event.satellites`, e o backref não filtra cancelado. O cachê do satélite cancelado continua no custo do líder, na tendência e no CPV da cascata, enquanto a Planilha já não paga esse cachê. A FR-027 e a FR-031 dizem que cachê de cancelado fica fora.

A proposta não decide isso, e o cenário 32 não afirma nada sobre o cachê do satélite.

**Emenda.** Decidir explicitamente entre:

(a) Recomendado: não tocar `_group_cost`, porque ele também é a base da comissão EducaManto. Registrar a dívida no docs/05 e pôr no cenário 32 uma asserção que documenta o comportamento (cachê do satélite cancelado segue no custo do líder).

(b) Filtrar satélite cancelado em `_group_cost`. Muda CPV, tendência, tabela, margem do Top Vendedores e a comissão EDU. Exige o OK do dono e um cenário próprio; o cenário 36 não cobre, porque esses meses ficam fora da comparação.

Fora isso: o `cancelled_at IS NULL` entra só nas consultas, sem mexer em `n_eventos` = len(evs).

**Evidência da revisão.** app/financeiro/comissoes_ops.py:615-620 (`_group_cost` soma satélites), :676-677 (base EDU); app/models.py:365-370 (backref `satellites` sem filtro); app/financeiro/routes.py:227 (CPV), :404-406 e app/api/financeiro_read.py:374-376 (tendência), routes.py:695-704 (Planilha exclui cancelado); app/api/financeiro_read.py:369-373 e routes.py:399-403 (tendência sem filtro); app/models.py:725 e spec.md:537-538, :551-552.

## DRE-g — (g) Indicadores: o que entra e o que não entra com o retido?

**Decisão.** ENTRA, sem código novo, por derivar de `drg_total`: margem bruta e margem EBITDA; custo de talento ÷ receita (`cpv` com o BV que conta ÷ `receita_liquida` com o retido); break-even (`lucro_bruto` e `fixed_cost = pessoal + comissoes`, já com a comissão do retido); Fator R (`pessoal ÷ receita_bruta` com o retido); e a barra "Retido de cancelamentos" na Receita por Tipo, nas duas telas. NÃO ENTRA: ticket médio (API já calcula de `eventos_com_venda`; o Jinja é corrigido — DRE-c), "a receber", contagem de eventos (`n_eventos`/`n_normais`/`n_permutas` e o "N evento(s) futuro(s)" do rodapé), "a pagar/pago a talentos", auditoria de input, coluna Projetado e custo de notas emitidas. O painel Top Vendedores da DRE fica como está, nas duas telas.

**Porquê.** FR-030, com o precedente da Loja Virtual (dinheiro que entrou conta na cascata; indicadores de evento ficam limpos — financeiro_read.py:272-284). Todos os indicadores "de evento" saem de `events`/`eventos_com_venda`, que continuam filtrando `cancelled_at IS NULL` (:233), então não há o que mudar neles. Top Vendedores: a FR-032 enumera onde o retido conta como venda (Dashboard Comercial, Performance da Home, /admin/desempenho, ficha da cliente) e não cita o painel da DRE; a FR-030 final deixou de mencioná-lo; o painel usa outro eixo (`start_at`) e outra chave (`seller_id`, não o beneficiário da comissão) — incluí-lo exigiria atribuição por vendedor nas duas views, acima do mínimo autorizado para o Jinja.

**Alternativas rejeitadas.** Somar o retido ao vendedor no Top Vendedores da DRE: rejeitado nesta feature pelo motivo acima; se o dono quiser, é uma tarefa a mais (agrupar o retido por beneficiário e somar em `seller_revenue`/`seller_margin` nas duas views). Registrar no docs/05 que o ranking da DRE e o do Dashboard Comercial usam eixos diferentes.

**Contrato.** Nenhum campo novo em `kpis`. Valores esperados no exemplo (mês do cancelamento, contra o retrato anterior): `fator_r_pct = _pct(pessoal, receita_bruta_antes + 400)`; `breakeven_pct = _pct(lucro_bruto_antes + 360, fixed_cost_antes + 18)`; `fixed_cost` +18; `ticket_medio` e `a_receber_clientes` iguais.

**Pontos de toque.**
- app/api/financeiro_read.py:268-295 (ticket), :296-304 (custo/receita, break-even, Fator R), :306-318 (a receber), :324-333 (talentos), :348-363 (Top Vendedores — intocado), :387-395 (auditoria)
- app/financeiro/routes.py:323-341, :344-356, :362-372, :382-392, :418-421
- frontend/apps/internal/src/pages/FinanceiroDashboardPage.tsx:410-414 (rodapé passa a dizer que o retido de cancelamentos entra no Realizado, no mês do cancelamento)

**Riscos.**
- Top Vendedores fora é leitura da spec, não frase do dono: se ele esperar ver o retido ali, é ajuste pequeno e isolado.
- Mês só com retido e sem evento vivo: margens e Fator R passam a ter denominador > 0 onde antes era 0 — é o comportamento pedido, mas muda a cor dos cartões.

**Verify.** Cenário 33, nas duas telas: `ticket_medio` e `a_receber_clientes` idênticos antes e depois; `n_eventos`, `n_normais`, `n_permutas` idênticos; Fator R e break-even iguais ao recálculo do verify a partir do retrato anterior (+400 no denominador; +360 e +18); barra do retido 400; Top Vendedores idêntico (assertiva explícita, para a decisão ficar travada).

**Revisão adversarial: parcial.** Os indicadores que entram e os que não entram estão certos e saem de graça de `drg_total` e `eventos_com_venda`.

O problema é o Top Vendedores. A proposta o deixa fora, trava isso com uma asserção e declara `open_questions: []`. O dono respondeu que o retido conta "no total vendido, no ranking e na meta". O Dashboard Comercial não tem ranking: `build_kpis` devolve cinco KPIs e a tela não lista vendedores. Os únicos rankings de vendedor do sistema são o Top Vendedores da DRE (nas duas telas) e o `/admin/desempenho`.

O rascunho da spec tinha Top Vendedores na lista "NÃO DEVE" da FR-030, e a versão final o tirou depois da resposta do dono, inclusive do cenário 33. Ler a FR-032 como "não cita o painel da DRE" reabre, pelo lado contrário, uma decisão do dono.

**Emenda.** Tirar a asserção "Top Vendedores idêntico". Levar como pergunta aberta ao dono, com padrão recomendado "entra": o retido soma em `seller_revenue` e `seller_margin` do beneficiário congelado, no mês do cancelamento.

Implementação: uma função em `dre_ops` (ex.: `retido_por_beneficiario(cancelados)`) chamada pelas duas views antes do `sorted`. Exige `beneficiario_id` no resumo (ver DRE-a). Se o dono disser "fora", registrar no docs/05 que o ranking da DRE e o do Comercial divergem.

**Evidência da revisão.** spec.md:94-96 (Clarification: "no total vendido, no ranking e na meta"), :555-558 (FR-032), :547-550 (FR-030 sem Top Vendedores), :698 (cenário 33 sem Top Vendedores); scratchpad 04-cancelado-proposta.md:165-166 (rascunho tinha Top Vendedores no "NÃO DEVE"); app/financeiro/vendas_ops.py:292-298 (KPIs sem ranking); app/api/financeiro_read.py:348-363 e app/financeiro/routes.py:381-392 (ranking da DRE); app/api/admin_config_read.py:149-170 (ranking do /admin/desempenho).

## DRE-h — (h) Como o verify compara main × branch centavo a centavo nos meses sem cancelamento (cenário 36) e prova por mutação o −600 → +342?

**Decisão.** Um arnês único, `specs/303-sync-nao-apaga-venda/dre_retrato.py`, que NÃO importa nada que só exista na branch e roda igual dos dois lados: recebe `--repo`, `--agora`, a lista de meses e `--saida`; sobe `create_app()` do repositório indicado, faz login por `POST /api/auth/login`, e para cada mês lê (1) `GET /api/financeiro/dashboard?period=custom&start=&end=` e (2) `GET /financeiro/?period=custom&...` capturando o contexto por `template_rendered`; grava tudo em JSON (Decimal como texto). Lado main = subprocesso com `cwd` num worktree da `main` (`git worktree add --detach <fora do repo> main`, caminho em `MANTO_MAIN_WORKTREE`), mesmo interpretador, `DATABASE_URL`/`FLASK_ENV=development`/`MANTO_SEM_THREADS=1` herdados; lado branch = a mesma função chamada em processo. O relógio é fixado nos dois lados (troca de `datetime` em `app.financeiro.routes`, `app.api.financeiro_read` e, se existir, `app.financeiro.dre_ops`) e `ensure_recurring_entries` é neutralizado nos dois (é escrita com commit dentro de um GET). Comparador único: toda chave presente no retrato da main tem de existir na branch com o mesmo valor (dinheiro a 0,01; percentuais a 0,1); chave nova é tolerada. Cenário 36 roda ANTES de qualquer cancelamento do verify, sobre todos os meses do espelho (do menor ao maior `start_at`), excluindo os que já tenham cancelado tocando o mês (por `cancelled_at`, `start_at`, vencimento de parcela ou data de devolução) — e a tendência é coberta em todos os meses deslocando o relógio fixo de 6 em 6 meses. Mutação: três retratos do mês do cancelamento e do mês do evento — S0 (antes de criar o evento), S1 (evento vivo, pago 1.000), S2 (cancelado com 600 devolvidos, parceiro recebe 40); variação S2−S0 do resultado líquido: branch +342,00, main −600,00, com o MESMO comparador e a MESMA base de dados.

**Porquê.** É o protocolo que a PARADA_REMOCAO_JINJA exige para código de dinheiro (:89-91) e que já foi usado na extração da régua de comissão. Rodar a main de verdade contra o mesmo banco é mais forte do que o verify reimplementar "a conta antiga": o mutante é o código anterior inteiro. A coluna nova do cancelamento é aditiva, então o código da main lê o banco migrado sem erro, e `create_app()` não cria nem altera schema. Medir por variação contra S0 isola o evento do resto do mês (salários, recorrentes, outros cenários do próprio verify). O evento é datado no dia 15 de dois meses à frente do dia da execução, para o mês do evento ser sempre diferente do mês do cancelamento. Relógio fixo resolve três fontes de falso alarme: o corte Realizado × Projetado em `now`, a janela da tendência ancorada em hoje, e a geração de recorrentes.

**Alternativas rejeitadas.** (1) Retrato da main salvo em arquivo uma vez, antes de implementar: rejeitado — o espelho muda e "agora" anda; o arquivo envelhece e o cenário falha ou passa por motivo alheio. (2) Reproduzir a fórmula antiga dentro do verify: rejeitado — a réplica pode estar errada e a prova vira circular. (3) Parsear o HTML da tela antiga: rejeitado para números (frágil); o HTML só é usado para a linha nova, com âncora. (4) `git stash`/checkout da main no mesmo diretório: rejeitado — a raiz tem untracked vivo e tokens.

**Contrato.** `python specs/303-sync-nao-apaga-venda/dre_retrato.py --repo <raiz> --agora <ISO> --meses 2025-03,2025-04,... [--tendencia] --saida <json>`; credenciais do usuário descartável por variável de ambiente, nunca em argv. Saída por mês: `{api: {dre, kpis, paineis, eventos, pendencias}, jinja: {drg_realizado, drg_projetado, drg_total, ticket_medio, ratio_custo_talento, breakeven_pct, fixed_cost, fator_r_pct, a_receber_clientes, receita_por_tipo, monthly_trend, recebimentos_previstos_total, nf_a_emitir_total}}`. O verify FALHA (não pula) se: `MANTO_MAIN_WORKTREE` não existir; `git -C <worktree> rev-parse HEAD` ≠ `git rev-parse main`; `<worktree>/app/financeiro/dre_ops.py` existir; menos de 12 meses comparados. Imprime quantos meses e quantos valores comparou e quais meses ficaram de fora por terem cancelamento.

**Pontos de toque.**
- specs/303-sync-nao-apaga-venda/dre_retrato.py (NOVO) e verify_303.py (cenários 26 a 36)
- docs/PARADA_REMOCAO_JINJA.md:89-91 (protocolo)
- app/gastos/gastos_ops.py:498-543 (ensure_recurring_entries faz commit — neutralizar no retrato)
- app/api/financeiro_read.py:218-219 e app/financeiro/routes.py:266-267 (os `datetime.now` a fixar)
- app/api/agenda_write.py:541-566 (endpoint de cancelar que semeia S2)
- specs/301-orcamentos-visiveis-comercial/verify_301.py:66-90 (esqueleto: sys.path, env, `limiter.enabled = False`)
- app/financeiro/comissoes_ops.py:576, 590-596 (taxa padrão 2,5% — o verify grava `commission_rate=5` no evento)

**Riscos.**
- `create_app()` num worktree limpo não tem `instance/`, `credentials.json`, `token.json` nem `.local-db-url` (todos ignorados pelo git): a primeira tarefa é a fumaça do retrato no worktree, antes de qualquer código da feature.
- A tela antiga precisa responder 200 na main pelo test_client; se o template quebrar por `url_for` órfão, o lado Jinja do cenário 36 não tem linha de base — a mesma fumaça descobre.
- Custo: dois boots e ~30 meses × 2 endpoints × 2 lados; alguns minutos. Aceitável; os lados são só leitura e podem rodar em paralelo.
- Se o worktree da main ficar para trás (main andou), a comparação mente — por isso a checagem de HEAD.
- Cenários anteriores do próprio verify (12, 19-23) cancelam eventos no mês corrente: por isso o 36 roda primeiro e os cenários de DRE medem por variação entre retratos consecutivos, sem nada no meio.

**Verify.** Ordem: (36) retrato main × branch de todos os meses limpos → zero diferenças, DRE e tendência, API e contexto Jinja; (26) S0→S1→S2 com o comparador exigindo diferença no mês do cancelamento: main Δresultado −600,00 / Δgastos_extras +600,00 / Δreceita_bruta 0; branch Δresultado +342,00 / Δgastos_extras 0 / Δreceita_bruta +400,00 — o mesmo comparador que dá zero no 36 tem de acusar aqui, o que prova que ele enxerga; (27) mês do evento: S2−S0 = 0 nos dois lados para a cascata, e tendência com relógio no mês do evento; (28) imposto 64, 50 e 0; (29) devolução 600→800: retido 200, comissão 9, resultado +151, gastos_extras 0; (30)-(34) como descrito nas outras decisões; (35) depois de `GET /api/financeiro/comissoes` e `GET /api/financeiro/pagamentos` (que resincronizam comissões), a DRE continua com +18. Diagnóstico embutido: se a variação der −258, a mensagem diz "o retido entrou e a devolução continua em Gastos Extras (FR-027 sem FR-028)". Mutações manuais nas tasks: retirar o filtro de `gastos_extras_do_periodo` → 26 cai com −258; retirar `cancelled_at IS NULL` de `tendencia_mensal` → 27 cai.

**Revisão adversarial: parcial.** Worktree da main + mesmo banco é o protocolo que a PARADA pede, e rodar a main de verdade é melhor que replicar a fórmula. A `main` hoje é o mesmo commit da branch (14cec75), e `create_app()` não cria schema. Três furos:

1. Tolerância do comparador. "Dinheiro a 0,01; percentuais a 0,1" deixa passar diferença de 1 centavo (ou de 0,1 ponto). O cenário 36 e o SC-007 pedem igualdade ao centavo.

2. Relógio vazando. O lado branch roda em processo e troca `datetime` em `app.financeiro.routes` e `app.api.financeiro_read`, que também servem Planilha e Comissões. Sem restauração garantida, o cenário 35 e os seguintes rodam com relógio congelado. E "roda igual dos dois lados" deixa de ser verdade: um lado é subprocesso limpo, o outro é o processo do verify.

3. Linha de base. Exigir HEAD do worktree == `main` dá falso alarme quando a main andar com a branch sem rebase; a 298b está na mesma onda. A diferença main × branch passaria a incluir código alheio.

**Emenda.** 1. Comparação exata: Decimal por valor depois de quantize(0.01); float da API por round(x, 2) ==; percentual exato em 0,1. Sem tolerância absoluta.

2. Os dois lados como subprocesso do mesmo `dre_retrato.py`. Se o lado branch ficar em processo, a troca de `datetime` vai em context manager com restauração no `finally`, mais uma asserção de que `datetime.now` voltou.

3. Linha de base = `git merge-base main HEAD`, com a rodada final exigindo a branch rebaseada na main.

Manter a fumaça do retrato no worktree como primeira tarefa.

**Evidência da revisão.** docs/PARADA_REMOCAO_JINJA.md:89-91; spec.md:701 (cenário 36) e :732-735 (SC-007); app/financeiro/routes.py:266-267, :790, :877, :1012 e app/api/financeiro_read.py:218-219 (`datetime.now` nos mesmos módulos da Planilha e das Comissões); app/gastos/gastos_ops.py:498-546 (commit dentro do GET — neutralizar está certo); app/__init__.py:563-596 (cria instance/uploads, sem schema); `git rev-parse main` == HEAD 14cec75; memória do projeto: onda 1 = 303 + 298b.

## O que a frente deixou de decidir (revisão)

- Dono da função "cancelados por mês do cancelamento + totais": a FR-034 (card também no Dashboard Comercial, recortado por vendedor) e a FR-038 (filtro por mês e total retido na página de Cancelamentos) precisam do mesmo conjunto. A frente não disse quem é a fonte única nem previu recorte por beneficiário (app/api/financeiro_read.py:82-106; spec.md:565-567, :580-583).
- Top Vendedores da DRE × "ranking" da resposta do dono: é pergunta aberta e foi fechada como "fora", com `open_questions: []` (spec.md:94-96, :555-558).
- Cachê de satélite cancelado: continua no custo do líder via `_group_cost` (app/financeiro/comissoes_ops.py:615-620; app/models.py:365-370), na cascata e na tendência, contra a FR-027 e a FR-031. Falta decidir entre dívida registrada e filtro; o filtro mexe na base da comissão EducaManto.
- Predicado único da devolução: o que sai de Gastos Extras tem de ser exatamente o que o resumo soma em `devolvido` (categoria + evento + status). Caminhos não cobertos pela trava citada: criação manual com a categoria "Devolução a cliente" ligada a cancelado (app/gastos/gastos_ops.py:289-305; app/models.py:1018-1021), `link_expense_to_event` (gastos_ops.py:363-378) e rejeitar/reconsiderar (gastos_ops.py:333-346, :402-433).
- Devolução lançada à mão num evento vivo que depois é cancelado: passa a sair de Gastos Extras do mês da `expense_date` (reescreve aquele mês) e a reduzir o retido do mês do cancelamento. Registrar no docs/04 como consequência aceita, ou bloquear.
- Textos que passam a mentir por causa desta frente e não estão nos touchpoints (FR-025): app/calendar/cancel_ops.py:165-167 ("entra sozinho na DRE do mês") e :246 ("tira de toda métrica"); app/models.py:1014-1017 e :1062-1065 ("somado pela DRE"); app/financeiro/vendas_ops.py:154-157; o subtítulo "regime de competência (data do evento)" em FinanceiroDashboardPage.tsx:222 e dashboard.html:6, já que o retido entra pela data do cancelamento.
- Condição de exibição da linha "Retido de cancelamentos" e do hint de impostos: por `n_cancelados > 0`, não por retido > 0. No terceiro caso do cenário 32 o CPV ganha +200 sem linha que explique.
- Eixo da tabela com "Mostrar cancelados" (`cancelled_at` × `start_at`) e ausência de VIRTUAL cancelado: premissa do plan que o SC-008 não cobre no mês do evento. Registrar e confirmar com o dono (spec.md:736-737).
- Evento vivo com `event_type` NULL já fica fora da DRE hoje, pela lógica de três valores (app/api/financeiro_read.py:230; app/financeiro/routes.py:279; app/models.py:256; app/calendar/event_ops.py:924 grava None). A proposta trata o NULL só no cancelado: o mesmo evento não conta vivo e passa a contar o retido depois de cancelado. Registrar a assimetria e a dívida no docs/05; o cenário 36 não enxerga isso.
- Skill `financeiro` (.claude/skills/financeiro/SKILL.md:84-89): as receitas "Margem de um evento" e "Saídas de um mês" não conhecem cancelado nem retido e vão responder diferente da DRE nova. Atualizar a skill ou registrar no docs/05.

## Perguntas em aberto da frente
