# Modelo de dados — Feature 299

**Nenhuma tabela, coluna nem migration nova.** Tudo o que a feature precisa já existe e aceita nulo.
O que é novo é **derivado** em memória pelo núcleo `app/financeiro/cobranca_ops.py`.

## Entidades usadas (sem mudança de schema)

| Entidade | Campos que a 299 lê ou escreve | Onde |
|---|---|---|
| `CalendarEvent` | `sale_value` (vazio = "a definir"), `sale_value_gross`, `sale_date`, `is_cortesia_permuta`, `payment_method`, `payment_due_date` (data combinada), `event_type`, `title` (marcador), `start_at` (hora de parede de SP), `cancelled_at`, `group_leader_id`, `group_name`, `client_id` | `models.py:244-330` |
| `EventPayment` (comprovante) | `event_id`, `amount` (nulo conta R$ 0) | `models.py:663-675` |
| `EventInstallment` (parcela) | `event_id`, `due_date`, `amount`, `received` | `models.py:710-726` |
| `EventClient` / `Client` | contratante e cliente, pela ordem de `contratante_name` | `models.py:1841-1866`; `vendas_ops.py:81-93` |
| `CommissionPayment` | `payable_from` passa a ser usado também pela comissão comum (R22) | `models.py:914-925`; `comissoes_ops.py:689-747` |
| `SiteSetting.release_date` | corte (01/06/2026 em produção), via `corte_dia_sp()` | `models.py:835`; `formularios_ops.py:86-91` |

## `VendaResumo` (derivado, imutável)

Uma venda é um evento avulso ou um grupo, sempre representado pelo **principal**.

| Campo | Tipo | Regra |
|---|---|---|
| `principal` | `CalendarEvent` | `group_leader` se existir; senão o próprio evento (R5) |
| `eventos` | `tuple[CalendarEvent, ...]` | principal primeiro, satélites depois, **cancelados inclusive** |
| `valor` | `Decimal \| None` | `sale_value` do principal |
| `recebido` | `Decimal` | soma de `EventPayment.amount` de **todos** os eventos do grupo, cancelados inclusive (R3) |
| `data_do_grupo` | `date \| None` | menor `start_at.date()` entre os eventos **não cancelados** (R5) |
| `vencimento` | `date \| None` | data combinada, senão 1ª parcela não recebida do principal, senão `data_do_grupo − 2` (R7) |
| `vencimento_origem` | `"data_combinada" \| "parcela" \| "politica"` | qual das três regras deu a data |
| `cliente` | `str \| None` | `contratante_name(principal)` |
| `motivo_fora` | `str \| None` | `cancelado`, `ensaio`, `compromisso_interno`, `cortesia` ou `loja_virtual` (R6) |

Propriedades derivadas, todas em `Decimal`:

| Propriedade | Regra |
|---|---|
| `saldo` | `valor − recebido` (`None` sem valor) |
| `sem_valor` | `valor is None or valor < 1,00` |
| `valor_simbolico` | `0 < valor < 1,00` |
| `sinal_pendente` | sem data combinada **e** `recebido < valor/2 − 1,00` |
| `eventos_vivos` | quantos eventos não cancelados o grupo tem |
| `situacao` | ver a tabela abaixo |

## Estados de uma venda (`situacao`)

| Estado | Condição | Onde aparece |
|---|---|---|
| `fora` | `motivo_fora` preenchido, ou `data_do_grupo` antes do corte | em nenhuma lista |
| `sem_valor` | `sem_valor` | "Evento sem valor de venda" |
| `quitada` | valor ≥ 1,00 e `saldo < 1,00` (inclui recebido acima do valor) | em nenhuma lista |
| `com_saldo` | valor ≥ 1,00 e `saldo ≥ 1,00` | "Cobranças" |

Transições que tiram a linha da lista (FR-010), sem animação especial no servidor:
- `sem_valor` → `com_saldo` ou `quitada`: alguém põe o valor, pela aba Comercial, pelo orçamento ou
  pela edição completa.
- `com_saldo` → `quitada`: entra um comprovante em qualquer evento do grupo.
- qualquer estado → `fora`: o evento é cancelado, vira cortesia ou recebe o marcador.

## Linhas da Home (calculadas com `hoje` de São Paulo)

**Cobrança** (`situacao == com_saldo`):

| Campo | Regra |
|---|---|
| `dias_ate_vencimento` | `vencimento − hoje` (negativo = venceu) |
| `severidade` | vermelho se dias ≤ 2 (inclui vencido); amarelo de 3 a 30 dias; cinza acima de 30. O sinal pendente sobe cinza para amarelo e nunca rebaixa vermelho |
| `selo` | "Atrasado" (dias < 0) > "Vence hoje" > "Sinal pendente" > "Vence em N dias" |
| ordem | vencimento ascendente, depois `data_do_grupo`, depois `event_id` |

**Sem valor** (`situacao == sem_valor`):

| Campo | Regra |
|---|---|
| `dias_ate_o_evento` | `data_do_grupo − hoje` |
| partição | `a_acontecer` (dias ≥ 0, o mais próximo primeiro) e `ja_aconteceu` (dias < 0, o mais recente primeiro) |
| `severidade` | vermelho se dias ≤ 7 (inclui o que já aconteceu); amarelo de 8 a 30; cinza acima de 30 |

**Para o total do topo**: `para_agir` = linhas vermelhas + amarelas de cada lista comercial
(Cobranças, Sem valor e Formulários da 298).

## Regras de escrita (sem campo novo)

| Regra | Onde | Efeito |
|---|---|---|
| "Valor a definir" | `aplicar_valor_a_definir` (`event_ops`) | `sale_value` e `sale_value_gross` gravados `NULL`; a marca não é gravada |
| Data da venda | `resolver_data_da_venda(..., a_definir)` | a criação sem data vira hoje (SP); a edição sem data mantém a atual |
| Satélite na edição completa | `update_event_core` | nenhum campo comercial é gravado no satélite |
| Comissão tardia | `_sync_commission_payment` | linha nova de comissão comum com `sale_date` num mês anterior ao corrente → `payable_from = hoje`; não volta a `NULL` depois |
| Valor simbólico no orçamento | `aplicar_valores_do_orcamento` | abaixo de R$ 1,00 conta como "sem venda"; a cortesia continua recusada |

## Invariantes (vão para o `docs/04`)

1. Na cobrança, o grupo é uma venda só: o valor é o do principal e o recebido é o de todos os
   eventos, e nada é movido de lugar.
2. "Sem valor" na Home = vazio, zero ou abaixo de R$ 1,00. No Financeiro e na Auditoria continua
   `<= 0`: são duas definições de propósito.
3. Compromisso interno é o título que começa com 🟧 ou 🟠. Ele nunca é venda.
4. A folga de centavos é R$ 1,00, tanto para o saldo quanto para o sinal.
5. Com data combinada, não há sinal pendente; o vencimento é a data combinada.
