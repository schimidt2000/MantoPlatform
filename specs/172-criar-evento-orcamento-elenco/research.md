# Research — Corrigir elenco incompleto ao criar evento a partir de orçamento

## Contexto da investigação

O spec (Assumptions) deixou em aberto onde exatamente a informação de elenco se perde entre o
orçamento salvo e a tela de criação de evento. Esta fase investigou tecnicamente o caminho
completo: `app/orcamento/routes.py` (calcula e salva o snapshot do orçamento) →
`OrcamentoHistory.form_snapshot` → `_build_orcamento_prefill`/`_compute_performer_caches`
(`app/calendar/routes.py`, núcleo compartilhado feature 152, reusado pelo wrapper Jinja
`event_create.html` E pelo endpoint `GET /api/events/new/prefill`) → tela de criação de evento.

## Verificação empírica (dados reais, `manto_local`)

Rodando `_build_orcamento_prefill` diretamente contra os 5 orçamentos mais recentes salvos em
produção (`manto_local`), o elenco (personagens + coordenador + técnico de som) voltou completo
e correto em todos os casos testados — nomes, cachês por duração e `role_type` batendo com o
que a calculadora tinha originalmente computado. Ou seja, para o caso comum, a função já
funciona.

Isso descartou a hipótese inicial mais óbvia (um campo renomeado/removido na extração da
feature 152) e levou a uma comparação linha a linha entre o cálculo ORIGINAL do orçamento
(`app/orcamento/routes.py`, função que gera `session["orcamento_quote"]` e o `form_snapshot`) e
o cálculo que `_compute_performer_caches` refaz para a tela de criação de evento — já que os
dois precisam produzir o MESMO resultado (mesmo motor de preço, chamado duas vezes de forma
independente) e são dois pontos de código que **duplicam a mesma regra de negócio** (a
Constituição do projeto, Princípio I, cita justamente isso como "a principal causa de bugs e
saída do padrão" no sistema).

## Causa raiz encontrada

Comparando `app/orcamento/routes.py` (cálculo original, ~linha 201-298) com
`_compute_performer_caches` em `app/calendar/routes.py` (~linha 2591), duas divergências reais:

### 1. Acréscimo "Show customizado" (+R$50/artista) não é aplicado no cachê por personagem

`app/orcamento/routes.py`, ao calcular os totais do orçamento:

```python
# Show customizado: +R$50 por artista (não conta coord, técnico nem maquiador)
if show_sosia_tipo == "customizado" and performers:
    custom_add = len(performers) * 50
    for i in range(4):
        cache_totals[i] += custom_add
```

Esse acréscimo entra em `entry.total_1h..4h` (persistido no `OrcamentoHistory`), então o valor
de venda pré-preenchido na tela de criação de evento já vem correto. **Mas
`_compute_performer_caches` nunca aplica esse mesmo acréscimo aos cachês individuais** — cada
personagem sai da tela de criação de evento com o cachê R$50 abaixo do que deveria (quando o
orçamento usou "Show customizado" — opção de sósia, painel `#sosia-show-panel` em
`orcamento/index.html`). Resultado: a soma dos cachês do elenco não bate com o valor de venda do
evento, e o elenco chega "incompleto" (cachê per personagem menor do que o orçado) sempre que
esse tipo de show foi usado.

### 2. Detecção de "tem show" (`has_show`) duplicada com fórmulas diferentes

`app/orcamento/routes.py` (linhas ~218-223):

```python
if ptype == "cantor" or (ptype == "ator" and show) or \
   (ptype == "especial" and (show or cantor_flag or personagem_esp in _cfg.ESPECIAIS_SEMPRE_SHOW)):
    event_has_show = True
```

`_compute_performer_caches` (linhas ~2602-2606):

```python
has_show = any(
    p.get("show") or p.get("cantor") or p.get("type") == "cantor" or
    (p.get("type") == "especial" and p.get("personagem", "") in _orc_cfg.ESPECIAIS_SEMPRE_SHOW)
    for p in performers
)
```

São reimplementações independentes da mesma regra. Na prática, o frontend da calculadora
(`app/static/js/orcamento.js`, linhas ~733/774-776) garante que o campo `cantor` só é gravado
como `true` quando `type === 'especial'` (é zerado ao trocar de tipo), então hoje as duas
fórmulas produzem o mesmo resultado para qualquer snapshot real — **não é a causa do bug
relatado**. Mesmo assim, é duplicação de uma regra de negócio (viola o Princípio I da
constituição: "UMA fonte de verdade") e fica frágil a qualquer mudança futura no frontend que
volte a divergir as duas cópias sem que ninguém perceba — por isso entra no escopo desta
correção como cleanup de baixo risco, não como o bug principal.

## Decisão

**Decision**: Extrair a detecção de "tem show" e o acréscimo de "show customizado" para uma
única função compartilhada em `app/orcamento/pricing.py` (já é o módulo de onde
`_compute_performer_caches` importa os preços-base), e fazer tanto o cálculo original
(`app/orcamento/routes.py`) quanto `_compute_performer_caches` chamarem essa única função — em
vez de reimplementar a regra duas vezes.

**Rationale**: Elimina a duplicação apontada acima na raiz (Princípio I da constituição:
"[um] mesmo comportamento... deve ter UMA fonte de verdade no código"), sem exigir refatoração
maior do fluxo (nenhuma mudança de schema/endpoint; a assinatura pública de
`_build_orcamento_prefill`/`_compute_performer_caches`, já reusada pela API `/api/events/new/
prefill`, não muda). Isso corrige os dois pontos encontrados de uma vez — tanto o cachê que
falta o "+R$50/artista" quanto a possível divergência de `has_show` — e serve tanto o fluxo
Jinja quanto o React (mesma função compartilhada).

**Alternatives considered**:
- Corrigir só `_compute_performer_caches` isoladamente (duplicar a correção nos dois lugares em
  vez de unificar): rejeitado — perpetua exatamente o padrão de duplicação que causou o bug;
  a próxima mudança de regra de preço divergiria de novo.
- Reescrever esse trecho como parte de uma extração maior para um `orcamento_ops.py` completo:
  fora de escopo — o próprio CLAUDE.md recomenda extrair `*_ops.py` só quando há núcleo de
  negócio real a duplicar, e essa extração maior tocaria ~15 pontos de chamada fora do escopo
  deste bugfix (mesmo motivo já registrado no Complexity Tracking da feature 152). A extração
  pontual da função de show/acréscimo resolve o bug real sem essa reestruturação.

## NEEDS CLARIFICATION resolvidos

Nenhum. O Technical Context desta feature não depende de stack nova — reusa 100% o
backend Flask/SQLAlchemy e os módulos `app/orcamento/pricing.py` e `app/calendar/routes.py` já
existentes.
