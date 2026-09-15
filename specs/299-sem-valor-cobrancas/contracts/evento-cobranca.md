# Contrato — cobrança na página do evento (feature 299)

Vale para `GET /api/events/<id>` e para toda escrita que devolve o detalhe
(`serialize_event_detail` / `_event_detail_json`): comprovante, orçamento, grupo, comercial etc.

**Gate inalterado.** Os blocos `cobranca`, `venda`, `pagamentos` e `mensagens` só saem com
`show_comercial` (COMERCIAL, FINANCEIRO e SUPERADMIN; `agenda_read.py:149, 889`). CASTING não os
recebe (cenário 16).

**Compatibilidade.** Todas as chaves de hoje continuam com nome e tipo. As novas são opcionais no TS
(`lib/agenda.ts:414-439, 450, 469-472`).

## `cobranca`

Calculada por `cobranca_ops.resumo_da_venda_do_evento(event)` a partir do **principal**: é a mesma
conta da Home (SC-003).

| Chave | Tipo | Regra |
|---|---|---|
| `outstanding` | number | `max(saldo do grupo, 0)`; nunca negativo (antes: soma das parcelas, ou saldo só do evento) |
| `due` | `"AAAA-MM-DD"` \| null | vencimento da venda (R7) |
| `enabled` | bool | `pode_copiar_cobranca`: vencimento ≤ hoje (SP), saldo ≥ R$ 1,00 (folga do FR-023), valor ≥ R$ 1,00, sem motivo de ficar fora e o evento aberto **não** é outro evento do grupo (FR-003) |
| `valor`* | number \| null | valor de venda do principal |
| `recebido`* | number | recebido do grupo |
| `quitado`* | bool | valor ≥ R$ 1,00 e saldo < R$ 1,00 |
| `sem_valor`* | bool | valor vazio, zero ou abaixo de R$ 1,00 (fora cortesia) |
| `valor_simbolico`* | bool | `0 < valor < 1,00` |
| `sinal_pendente`* | bool | como na Home |
| `vencimento_origem`* | `"data_combinada" \| "parcela" \| "politica"` | |
| `escopo`* | `"evento" \| "grupo_principal" \| "grupo_outro"` | a tela escolhe o texto |
| `grupo_tamanho`* | int | eventos não cancelados do grupo (1 no avulso) |

\* nova e opcional.

**Outro evento do grupo** (`escopo = "grupo_outro"`):
- os números são os do grupo;
- o ponteiro é o `event.group.leader {id, title}`, que já existe (`agenda_read.py:572-580`), então
  não há campo novo de principal;
- `enabled` é `false`, porque a mensagem sai com os personagens e a data do evento aberto
  (`agenda_read.py:647-648`), e quem cobra é o principal.

## `venda` (aba Comercial)

| Chave | Tipo | Regra |
|---|---|---|
| `sale_value` | number \| null | sem mudança |
| `sem_valor`* | bool | `sem_valor_de_venda(sale_value)`, fora cortesia |
| `a_definir`* | bool | `sale_value` vazio ou zero, fora cortesia |
| `valor_simbolico`* | bool | `0 < sale_value < 1,00` |

**Tela**:
- `VendaPanel`: com `a_definir`, "A definir"; valor simbólico mostra o valor com a marca "valor
  simbólico"; no satélite, "Valor de venda: no evento principal", com link. O quadrinho "Venda" do
  resultado continua com o número (FR-015).
- `OrcamentoPanel`: `semVenda = venda.sem_valor ?? (!venda.sale_value && !venda.is_cortesia_permuta)`.

## `pagamentos`

| Chave | Tipo | Regra |
|---|---|---|
| `items` | lista | sem mudança: os comprovantes do **próprio** evento |
| `received_total` | number | sem mudança: soma dos `items` |
| `outros_do_grupo`* | `[{ "event_id", "event_title", "start_at", "total", "quantidade" }]` | um resumo por evento dos comprovantes dos **outros** eventos do grupo, sem arquivo; lista vazia no avulso |

**Tela** (`FinanceiroSection.tsx:207-285`):
- **Principal ou avulso**: "Recebido {recebido} de {valor} — falta {outstanding}". "Quitado" vem de
  `cobranca.quitado`. Com `outros_do_grupo`, aparece "Inclui R$ X em comprovantes de outros eventos
  do grupo", com os links.
- **Outro evento do grupo**: "Este evento é parte do grupo {nome}. A venda está no {principal}.",
  seguido de "Recebido no grupo R$ X de R$ Y — falta Z" e "neste evento: R$ W".
- **Sem valor**: "Recebido R$ X · valor de venda a definir", nunca "de R$ 0,00".
- **Sem os campos novos** (servidor antigo): o texto de hoje.

## `mensagens`

Sem mudança de chave. `cobranca_amount` e `cobranca_due` passam a sair do saldo e do vencimento do
grupo, porque `_serialize_mensagens` continua lendo `outstanding` e `due`.

## Outros consumidores (sem mudança de contrato)

- **`ResumoSection.tsx:368-376`, chip "Recebimento"**:
  - sem valor → "valor a definir";
  - outro evento do grupo → "no principal";
  - senão, `cobranca.quitado`, com fallback para `outstanding <= 0`.
- **`EventHeader.tsx:225-259`, menu "Cobrança"**: `enabled` vem do servidor. No outro evento do
  grupo, o título explica "A cobrança deste grupo está no evento principal".

## `PATCH /api/events/<id>/orcamento` (FR-018)

- **Gate inalterado**: `_can_manage_sale`, e satélite continua 409.
- **Regra nova**: `aplicar_valores_do_orcamento` (`orcamento_evento_ops.py:284`) e a mensagem
  `valores_ignorados` (`:404`) passam a tratar valor abaixo de R$ 1,00 como "sem venda". O orçamento
  é aplicado sobre o R$ 0,01.
- **Cortesia**: continua recusada ("evento é cortesia/permuta"), com a trava antes da checagem de
  valor, porque o `verify_273` a exige.
- **Data da venda**: não muda (`resolver_data_da_venda` mantém a data que existia).
