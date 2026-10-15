# Pesquisa — Feature 305 (Phase 0)

Base: o plano do backlog (`docs/backlog/3a-bv-do-orcamento-no-evento-099b.md`, apelido "099b") e um
mapa do código **na HEAD** (`db27518`, depois dos hotfixes 215b e 267c e do 298b), feito em 14/10/2026
por cinco leitores e cinco céticos (workflow `plan-305-code-map`, resultado em
`scratchpad/mapa_305.json` da sessão). Nada desta área andou entre `f6ad283` e a HEAD fora de
`agenda_write.py`, `agenda_read.py` e `comissoes_ops.py` (linhas deslocadas, regra igual).

Cada decisão abaixo diz de onde vem: **[D]** decisão do dono; **[P]** premissa do plano do backlog;
**[R]** decisão técnica desta pesquisa (achado do mapa ou do cético, coerente com as decisões do dono).

---

## R1 — A conta do BV do orçamento (B1) — [D: D2, Q1] + [R]

**Decisão.** `acrescimos_do_orcamento(entry, duracao)` em `app/calendar/orcamento_evento_ops.py`, pura,
devolve o valor **cheio** de cada linha que o orçamento somou. Fontes, por linha:

1. `valores_brl` da linha no `form_snapshot` (B2), se for `list` de 4 números finitos (`int`/`float`,
   não `bool`), ≥ 0 e não maiores que o total da duração;
2. senão, a conta inversa, em `Decimal`/`ROUND_HALF_UP`, **quantizando a base**:
   `L = X_d × 0,84` se tem nota, senão `X_d`; `F` = soma das linhas fixas; `P` = soma das linhas em %;
   `B = q((L − F) ÷ (1 + P/100))`; linha em % = `q(B × v/100)`; linha fixa = `q(v)`.
3. Se a conta inversa também falhar (NaN, Infinity, texto, base ≤ 0, soma dos % ≤ −100), a linha é
   pulada. **A função nunca levanta exceção** (`InvalidOperation`, `TypeError`, `ValueError`,
   `IndexError` capturadas; `is_finite()`): a B3 roda depois do `insert_event` do Google.

**Por quê.** A calculadora de hoje (`quote_ops.py:345-364`) aplica todos os % sobre o mesmo total
**antes** dos acréscimos e divide tudo por 0,84 no fim — a conta inversa com a base quantizada reproduz
a memória em 76 de 80 pares (16 orçamentos × 4 durações); os 4 restantes diferem R$ 0,01, todos em
3h, por meio centavo que o `float` arredonda para baixo. Sem quantizar a base: 73/80. A spec dizia a
fórmula sem a quantização (corrigido na FR-001).

**Duração acima de 4h.** O denominador é o **mesmo** número que o Novo evento mostra: se
`h == duracao_custom`, `result_snapshot.total_custom`; senão a conta do prefill
(`round(float(total_4h) / 4 × h, 2)`, `routes.py:3176-3181`). As linhas escalam por h/4 (régua linear da
calculadora, inclusive a fixa). As chaves da 3b (`base_4h`, `bruto_Nh`, `extra_por_horas`) **não
existem na HEAD**: a 305 só tem os dois ramos acima; a 3b acrescenta o dela.

**Alternativas rejeitadas.** Recalcular o orçamento com `calculate_quote` (vale o total congelado);
ler a memória (`result_snapshot.memoria`: só existe a partir de ~06/08, falta em 19 dos 35).

## R2 — `valores_brl` no snapshot (B2) — [P-4] + [R]

**Decisão.** No laço de `quote_ops.py:346-353`, cada acréscimo ganha `valores_brl` (4 durações),
`float(q(Decimal(str(t)) × Decimal(str(v)) / 100))` no % e `float(q(v))` no fixo, sem tocar `valores`
(a memória fica idêntica); no ramo `if personalizado:` (`:374-382`) zera `[0.0]*4` (o laço já rodou
antes). O total não muda.

**Confiança no navegador.** O `/salvar` grava o snapshot que o navegador devolveu (`orcamento_write.py:64-69`):
`valores_brl` é dado do cliente. Por isso a R1 só o aceita dentro dos limites (finito, ≥ 0, ≤ total da
duração) e cai para a conta inversa fora deles; e a diferença entre as duas fontes é no máximo R$ 0,01
nos orçamentos reais. Não vale reabrir a calculadora para recalcular no `/salvar` (fora de escopo).

**Verify.** O cenário 7 compara com tolerância de R$ 0,01 (o meio centavo do 2357 em 3h).

## R3 — A proporção (`bv_que_acompanha`) e o divisor — [D: Q1, Q8] + [R]

**Decisão.** `bv_que_acompanha(bv, venda, total)` em `app/orcamento/quote_ops.py`:
`q(bv × venda ÷ total)`, `Decimal(str(x))` nas entradas, total ≤ 0 ou nulo → `0,00`, sem exceção.
**Tolerância:** `|venda − total| ≤ R$ 0,01` conta como igual (BV cheio, sem "na proporção da
venda") — o total de duração extra é arredondado de três jeitos (float no Python, `Math.round` no JS,
Decimal) e diferia um centavo sem ter havido desconto.

**Divisor.** `NF_DIVISOR = 0.84` continua **float** em `app/educamanto/pricing_ops.py:27` (usado em float
em `:368`, `:435` e passa a ser usado em `quote_ops.py:364`, mesmo valor). Quem conta em Decimal deriva
`Decimal(str(NF_DIVISOR))` — nunca `Decimal(NF_DIVISOR)` (0,8399999…) e nunca uma segunda constante.
Importar de `pricing_ops` em `quote_ops` não cria ciclo (conferido).

**Converge (14/10): a proporção é entre LÍQUIDOS em todo lugar.** A criação e o alerta chamavam
`bv_que_acompanha(cheio, venda, total)` com a venda bruta e o total bruto — a cliente que desistia da
nota (venda 16% menor pelo mesmo preço) tinha o BV cortado em 16%, e a nota que entrava o subia 19%,
enquanto a B10 já comparava líquidos. `plano_dos_acrescimos` recebe `nota` (a do evento; `None` = a do
orçamento, no vínculo) e compara `venda × 0,84 se nota do evento` com `total × 0,84 se nota do
orçamento`; com as duas iguais, o 0,84 se cancela e nada muda.

## R4 — Onde o BV nasce, e a lista do navegador (B3, B4) — [D: Q2, PIX] + [R]

**Decisão.** `gravar_acrescimos_do_orcamento(event, entry, duracao, *, recebedor, pix, duracao_origem)`
substitui `_criar_acrescimos_do_orcamento` (`routes.py:3273-3305`, removida; `ROUND_HALF_UP` e
`EventAcrescimo` saem dos imports de `routes.py`). Chamada:

- **na criação**, dentro de `_create_event_core`, no `if entry is not None:` depois de `:3736` (onde
  `entry` e a duração já existem), antes do `EventLog` de `:3767` e do sync de `:3775`;
- **no "Vincular e aplicar"**, dentro de `aplicar_valores_do_orcamento`, no lugar de `:308-312`, que
  passa a devolver o resultado da B3 (criados, total de BV, motivo) em vez de `bool`; o sync que já
  vem depois (`api_set_event_orcamento`) passa a ver o BV.

**A lista `acrescimos` do corpo é descartada em TODA criação**, com ou sem orçamento, na API e no
Jinja (`acrescimos_json`) — senão um `POST` sem orçamento com BV na lista fura o PIX obrigatório
(SC-002). A única fonte de linha na criação é a B3.

**Guardas.** Evento cancelado ou que já tem **qualquer** linha em `event_acrescimos`: não grava (motivo).
A guarda é por **consulta** (`EXISTS` em `event_acrescimos`), nunca lendo `event.acrescimos` (carregar a
coleção vazia e depois inserir por `event_id` deixa a coleção velha — ver R7). Fora da criação, o
evento é relido com `SELECT … FOR UPDATE` **antes** da guarda "sem venda" de `aplicar_valores_do_orcamento`
(`:290`), para que duas aplicações concorrentes não misturem a venda de uma com o BV da outra; a
segunda devolve `valores_ignorados = "evento já tem venda"`.

**Duração na criação (FR-014 do plano).** O React sempre manda `duracao`; a dedução só vale para o
corpo **sem** a chave (API chamada por fora, Jinja antigo). O adaptador da API guarda
`duracao_informada = 'duracao' in body and body['duracao'] not in (None, '')` sem mexer no
`_parse_duracao`. Ordem: valor bruto igual (±R$ 0,01) a um dos 4 totais → horas da agenda de 1 a 4h, ou
iguais a `duracao_custom` → não grava ("duração não identificada"). Orçamento só com % não precisa.

**Rastro.** `EventLog` "BV do orçamento #N: R$ X (10%, 2h, pelo valor; na proporção da venda de R$ Y),
para <quem recebe>" — **sem PIX** — logo depois do log de criação/vínculo e antes do sync.

## R5 — PIX obrigatório (B8) — [D: regra do PIX] + [R]

**Decisão.** Uma função de plano `bv_que_vai_nascer(entry, data_ou_evento, duracao)` responde se a B3
vai gravar BV; a B8 da criação e do vínculo pergunta a ela (a B3 usa as mesmas guardas — as duas não
podem divergir). Recusa: `400 "Corrija os campos destacados"`, `fields: {bv_recipient, bv_pix}` com a
mensagem "Este evento tem BV: informe quem recebe e o PIX, para o repasse ir à Planilha de
Pagamentos."; o texto de topo diz o mesmo, para o bundle antigo (que só mostra `error.message`).

- **Criação (API):** depois da guarda 1:1 do formulário (`agenda_write.py:892-903`) e antes do Google
  (`:905`). **Jinja:** depois de `validation_errors` e antes do Google (`routes.py:4009-4019`), por
  `_render_error` ("crie pela tela nova, que pede quem recebe e o PIX"); o template não muda.
- **Vínculo:** depois da autoria da 301 (`agenda_write.py:1345-1355`) e antes de `set_event_orcamento`
  (`:1357`), só com `entry` e `aplicar_valores_duracao`.
- **Editor (`PUT …/acrescimos` e Jinja):** dentro de `substituir_acrescimos`, **antes do delete**,
  depois da regra "PIX vazio mantém o anterior" (R7). Uma linha ruim recusa a lista inteira: a função
  passa a **levantar** `AcrescimosRecusados(erros)`; o `PUT` devolve 400 com `fields` por **índice da
  requisição** (`"items.3.bv_pix"`), o Jinja faz `rollback` + `flash`.
- Tipos: `bv_recipient`/`bv_pix` que não são `str` → 400, nunca 500 no `.strip()`. Limites 200/140.

## R6 — O tipo BV e o valor com vírgula no editor — [R] (achado do cético)

**Decisão.**
- **Vírgula.** Hoje `_to_decimal` não aceita "100,00": a linha é **descartada em silêncio** depois do
  delete — um BV digitado à brasileira some, e editar um BV pago com vírgula o apaga (e o status com
  ele). O `PUT` passa a converter com o mesmo `parse_brl` do Jinja (`routes.py:877`); e uma linha com
  tipo preenchido e valor que não é número vira 400 na linha, **nunca** "pulada". A F2 normaliza a
  vírgula antes do envio.
- **Tipo.** `is_bv` exige `"BV"` exato depois do `strip`; "bv" minúsculo escapava da Planilha, da
  comissão e da B8. O tipo é normalizado (`strip().upper() == "BV"` grava `"BV"`).
- **Converge (14/10).** O texto ambíguo é recusado na linha, nunca reinterpretado: "1.500" sem
  vírgula (o milhar que o placeholder "150,00" convida; `Decimal` lia 1,50), "1,309.52" (lia 1,31) e
  número ≥ 10¹⁰ (estourava o `Numeric(12,2)` com 500). BV sem valor, zero ou negativo também é
  recusado — apagar o valor e salvar tirava o BV da Planilha; o negativo subia a comissão. Linha que
  não é BV com valor vazio ou zero segue ignorada (a linha em branco do Jinja). E a tela manda
  número: o R$ é `MoneyInput` e o % é convertido no navegador (a F2 abaixo).

## R7 — O editor de Acréscimos (B6) — [D: Q5, Q7, 3b-Q7, P-20] + [R]

**Identidade, não heurística.** O `GET` já devolve o `id` de cada linha (`agenda_read.py:534`); a F2
passa a devolvê-lo no `PUT`. O servidor herda **só da linha antiga com aquele id**: o status de
pagamento, o PIX vazio ("mantém"), a descrição ausente e o valor congelado do pago/no banco. **Linha
sem id nasce sempre `nao_pago`.** As heurísticas do plano (chave recebedor+PIX, recebedor único,
tipo+valor) ficam **só** para o bundle antigo, que não manda id — e mesmo nele nunca promovem uma
linha nova a "pago" se houver mais de uma candidata. Motivo: pela chave, um BV novo para quem já
recebeu um BV pago no evento nasceria "pago" (a Comercial criaria dinheiro pago sem poder marcar
pago), e dois BVs da mesma pessoa se fundiam. **Converge (14/10):** o mesmo `id` duas vezes na lista
é recusado (`items.<i>.id`) — as duas linhas herdavam o "pago" da antiga, e uma requisição montada à
mão criava um segundo BV pago, para outra pessoa, sem passar pela Planilha. E a troca de quem recebe
ou do PIX num BV pago ou no banco vai ao `AuditLog` (PIX mascarado nos 4 últimos caracteres) — o
registro de quem recebeu se reescrevia sem rastro. O evento é travado antes de ler a venda
(`travar_evento`): o % não é calculado com a venda de antes de uma gravação concorrente.

**Régua do BV em % (FR-016).** `L` = venda × 0,84 com nota, senão a venda; `B = q((L − Σ BV em R$) ÷
(1 + Σ % de BV/100))`; BV = `q(B × %/100)`. O % é arredondado a 2 casas **antes** da conta (o banco
guarda `Numeric(12,2)`; sem isso o próximo "salvar sem mexer" deriva centavos). Recalcula só
`nao_pago`. Base ≤ 0, % negativo ou soma ≤ −100: 400 na linha.

**Pago e no banco não mudam de valor (P-20).** BV `pago` ou `no_banco` mantém `amount_brl` **e** `value`,
em % **ou em reais**, mesmo que o corpo traga outro número — "BV pago ou no banco não muda (dinheiro
que já saiu)". Quem recebe e PIX continuam editáveis. (O plano deixava o BV pago em reais editável
pela Comercial; baixar um BV pago tiraria dinheiro do CPV e subiria a comissão da vendedora.)

**Venda sem valor.** Com a venda em "Valor a definir", R$ 0,01 ou cortesia, o BV em % já existente
mantém o `amount_brl` (pelo id), e um BV em % **novo** é recusado ("lance o BV em % depois do valor de
venda, ou em reais") — senão nasce R$ 0,00 a pagar, apaga o alerta e a comissão sai sobre a venda
cheia.

**BV em reais (Q7 = B).** Gravado como digitado (`is_percent=false`, `value = amount_brl`), sem
recálculo ao salvar.

**Coleção velha (o defeito mais sério, também no Jinja de hoje).** `substituir_acrescimos` carrega
`event.acrescimos`, apaga por `Query.delete()` e recria por `add(event_id=…)`: a coleção em memória
continua com as linhas apagadas, e `_sync_commission_payment` (via `_event_bv_total`) calcula com o BV
velho; o `_resync` da Planilha esconde o erro. Decisão: a função lê as linhas antigas com
`SELECT … FOR UPDATE` (um "marcar pago" concorrente falha alto em vez de sumir), e termina com
`db.session.flush()` + `db.session.expire(event, ["acrescimos"])`. Assim o `PUT`, o Jinja, a B3 e a B10
leem a coleção certa sem precisar lembrar. Reproduzido em sqlite pelo cético: 130,95 continua depois do
delete+add+flush; vira 100,00 só com o `expire`.

**Sync.** O `PUT` passa a chamar `_sync_commission_payment(event)` antes do commit (como o Jinja).

**Cancelado.** A régua da B6 e a B10 não rodam em evento cancelado (os valores ficam); a B8 continua
valendo. O 409 do `PUT` em cancelado e a edição do BV do cancelado são da 1b.

## R8 — O alerta (B9) — [D: Q2, Q4] + [R]

**Decisão.** `bv_do_orcamento_pendente(event)` em `orcamento_evento_ops.py`, chamada no bloco `venda`
de `agenda_read.py` (depois de `:961`, chave no dicionário de `:962-1006`, sem tocar `pode_mudar_taxa`
do 215b). Presente quando: ligado a orçamento com BV não personalizado; venda de verdade
(`not sem_valor_de_venda` e não cortesia); **nenhuma linha BV com `amount_brl` > 0**; não cancelado;
não satélite; e passou o corte.

**O valor, não o %.** O alerta devolve `{"valor": X, "percentual": p | None, "duracao": h | None}`:
`X` é o BV cheio da R1 × venda ÷ total (R3) na duração deduzida (R4). O "Lançar o BV" preenche a linha
**em reais**, como a B3 grava. Motivo: a régua do % no evento (base com os outros acréscimos, 3b-Q7)
não é a do orçamento salvo (base sem eles); em 9 dos 35 orçamentos com BV daria outro valor (no 2407,
R$ 2.007,73 em vez de R$ 435,00). Sem duração identificada: `valor = None` com o `percentual` e o texto
"confira a duração" — o alerta não some.

**Corte.** Constante `CORTE_ALERTA_BV` (datetime **naive em UTC**) no mesmo módulo, lida na hora da
chamada (o verify a troca por monkeypatch). Presente se `event.created_at ≥ corte` **ou** existe
`EventLog` "Vinculou o orçamento #<id atual> (" com `created_at ≥ corte` (o `(` evita `#12` casar
`#123`); "Reaplicou" não conta. Na frase do vínculo, que é montada antes do próprio log
(`set_event_orcamento:423-424`), passa-se `novo_vinculo`. A consulta ao log só roda quando as outras
condições já valem e o evento é anterior ao corte. O valor da constante é o momento do deploy, gravado
no último commit antes do merge como literal naive (hora tirada de `datetime.now(UTC)` no Python,
nunca o Git Bash). **Converge (14/10):** com a constante vazia, só o vínculo novo acende — a falha
fecha (antes, `None` acendia todo o passado); um valor com fuso é normalizado para UTC naive.

**TZ do manto_local.** O servidor está em America/Sao_Paulo e o app não fixa o TZ da sessão: o
`EventLog` do verify sai em hora de parede de SP, 3h antes do relógio UTC do `created_at`. O cenário
45 usa folga maior que 3h nas datas (ou `PGTZ=UTC` no processo do verify).

**Também acende por warnings.** A edição completa que deixa o alerta aceso põe uma linha em
`warnings` (a tela segura a navegação no `AvisosCard`), e o vínculo em evento com venda diz na frase.

## R9 — A venda que muda depois (B10) — [D: Q1, Q8, P-30] + [R]

**Decisão.** Núcleo puro `acompanhar_bv_da_venda(event, antes, *, actor_name, tz) -> str | None` em
`comercial_ops.py`, onde `antes = (venda, nota, cortesia)` capturados **antes** de qualquer escrita:

- **Gatilho:** a venda **ou a nota** mudou, de um valor de verdade a outro; evento não cancelado.
- **BV em reais `nao_pago`:** `bv_que_acompanha(valor, líquido_novo, líquido_antigo)`, com
  `líquido = venda × 0,84 se nota, senão venda` — trocar só a nota não muda o preço, então não muda o
  BV em reais. Grava `amount_brl` **e** `value` (o editor reenvia `value`).
- **BV em % `nao_pago`:** a régua da R7 sobre a venda e a nota novas (depois dos em reais).
- **Volta de "a definir"/cortesia a um valor:** o BV em % a pagar é recalculado pela régua (ele é
  % do preço); o em reais fica, com o aviso "confira o BV".
- **Pago ou no banco:** intactos.
- `EventLog` "BV acompanhou a venda: de R$ Z para R$ W — venda de R$ X para R$ Y, para <quem recebe>"
  (sem PIX); comissão a pagar sincronizada pelo sync que já vem depois.

**Lugares.** `update_event_comercial` (capturar a cortesia antes de `:1186`; chamar depois de `:1203`,
antes do sync de `:1205-1207`; passa a devolver o aviso), `_gravar_venda_da_edicao` (capturar antes de
`:857`; o aviso vai a `warnings` em `update_event_core`), e o gêmeo Jinja `_handle_update_comercial`
(capturar **antes** de `:841`; rodar **depois** de `substituir_acrescimos` (`:883`), que reposta as
linhas a cada envio; `flash` com o aviso). O "Vincular e aplicar" sobre evento que já tinha linha BV
acrescenta "confira o BV" à frase. A 215b (`_erro_de_taxa_ou_vendedor`) continua antes.

**Converge (14/10).** (1) O "Vincular e aplicar" que põe a venda num evento que já tinha acréscimos
(a B3 não grava) roda a B10 — o BV em % ficava sobre a venda velha, contra a FR-022; o aviso vai a
`relatorio.bv_acompanhou`. (2) O "antes" é lido com o evento travado (`estado_da_venda` →
`travar_evento`): duas mudanças de venda partiam do mesmo "antes" e o BV era proporcionado duas vezes.
(3) No Jinja, o BV a pagar que o envio MEXEU (comparado com o gravado antes de `substituir_acrescimos`)
fica como digitado, com o aviso "confira o BV" — reproporcioná-lo dobrava o combinado novo.
(4) Marcar pago na Planilha trava a linha e confere `valor_esperado` (409 se a B10 mudou o valor).

**Segundo converge (15/10).** (1) O "redigitado" do Jinja é decidido BV a BV, pelo número que a tela
mostra (`bvs_a_pagar_por_valor`, um multiconjunto de (unidade, valor)): o reenviado sem mexer acompanha
a venda, o mexido fica — tudo-ou-nada impedia o BV intocado de acompanhar. A leitura é por colunas
(nenhuma entidade carregada sem trava) e os `FOR UPDATE` usam `populate_existing`. (2) O Jinja manda o
texto cru ao núcleo (o `parse_brl` lia "1.500" de linha nova, sem máscara, como R$ 1,50). (3) O editor
manda `valor_visto` (o R$ que abriu); se a venda mudou o BV a pagar desde então, 400 na linha em vez de
desfazer a proporção. (4) `_valor_digitado` arredonda ao centavo antes das guardas (R$ 0,004 virava BV
de R$ 0,00). (5) `set_event_clients` e o Jinja travam o evento antes dos dependentes (a ordem inversa
dava deadlock com a edição completa). (6) O cenário 58 exige o literal da T041 — esquecê-lo, depois que
a falha passou a fechar, deixaria o alerta desligado em silêncio.

**Terceiro converge (15/10, 5 de 5 confirmados, todos de gravidade baixa).** (1) A chave do "BV a BV"
do Jinja inclui quem recebe e o PIX (`_bv_na_tela`): só pelo valor, um 120 redigitado casava com o
120 reenviado de outro BV e a proporção trocava de dono. (2) `valor_visto` inválido (inf, NaN, 1e30) é
ignorado — dava 500 no `_q`. (3) `delete_client` anula o `client_id` do evento ANTES de apagar os
vínculos: com o evento travado primeiro em `set_event_clients`, a ordem inversa da exclusão fechava
deadlock. (4) O `MoneyInput` conta o −0 como negativo (apagar e redigitar um desconto virava
cobrança) e não carrega o sinal para a linha BV. (5) O aviso do editor diz "os BVs mudaram (a venda
mudou ou houve outra gravação)" — depois de uma resposta perdida, "a venda mudou" era falso.

**A volta não é exata.** `200 → 180 → 200` volta ao ponto só com números redondos; a cadeia de
proporções acumula centavos. O cenário 49 usa os números redondos do plano e um caso não redondo com
tolerância declarada.

## R10 — Frontend — [R]

- Todo campo novo do payload é **opcional** no tipo (bundle novo × backend velho).
- F2: `MoneyInput` (`@manto/money`) para o valor em R$ e parse pt-BR para o %, enviando número; `id`
  e `descricao` (só quando presente — com o backend velho a chave fica fora) e `bv_pix ?? ""`;
  `maxLength` 200/140; erro do 400 na linha pelo índice. Editor aberto quando a venda muda: compara os
  BVs do cache com o snapshot do abrir() e bloqueia o Salvar com "a venda mudou e o BV foi
  recalculado — reabra".
- "Lançar o BV": `?lancar=bv` lido por `useEffect` no `AcrescimosPanel` (o painel já está montado),
  idempotente, e o parâmetro apagado com `replace` ao abrir.
- F1: os campos de PIX ficam **fora** do react-hook-form (estado próprio) ou com default — campo
  `disabled` chega vazio e o `eventSchema` é compartilhado com a edição.
- Nenhuma conta de dinheiro no navegador: o quadro mostra `valores_brl` do servidor; proporção é
  "calculado ao salvar". Hooks novos antes dos `return` antecipados (ValoresBlock `:76`, VendaPanel
  `:835`, OrcamentoPanel `:600`, AcrescimosPanel `:65`).
- Invalidar `["financeiro-pagamentos"]` e `["financeiro-comissoes"]` nas mutações que passam a mexer no
  BV e na comissão.

## R11 — Riscos aceitos (dívida, não código desta entrega)

- Cancelar e recriar do mesmo orçamento lista dois BVs na Planilha até a 1b filtrar o cancelado.
- A guarda 1:1 orçamento↔evento continua sem trava (dívida da 273).
- O gêmeo Jinja da venda aceita Financeiro e não recusa satélite/cancelado — só é alcançável pelo host
  do backend (o domínio público não serve a página; os logs "Atualizou dados comerciais" pararam em
  30/07). A B10 ali pula cancelado e satélite.
- Orçamento inexistente na criação (apagado com a tela aberta) estoura a FK depois do Google: defeito
  anterior; a B8 carrega o `entry` antes e passa a responder 404 nesse caso.
