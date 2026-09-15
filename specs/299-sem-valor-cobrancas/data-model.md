# Modelo de dados — Feature 299

**Nenhuma tabela, coluna nem migration nova.** Tudo o que a feature precisa já existe e aceita nulo.
O que é novo é **derivado** em memória pelo núcleo `app/financeiro/cobranca_ops.py`.

## Entidades usadas (sem mudança de schema)

| Entidade | Campos que a 299 lê ou escreve | Onde |
|---|---|---|
| `CalendarEvent` | `sale_value` (vazio = "a definir"), `sale_value_gross`, `sale_date`, `is_cortesia_permuta`, `payment_method`, `payment_due_date` (data combinada), `event_type`, `title` (marcador), `start_at` (hora de parede de SP), `cancelled_at`, `group_leader_id`, `group_name`, `client_id` | `models.py:244-330` |
| `EventPayment` (comprovante) | `event_id`, `amount` (nulo conta R$ 0) | `models.py:663-675` |
| `EventInstallment` (parcela) | `event_id`, `due_date`, `amount` (a marca `received` não é usada: a cobertura vem dos comprovantes) | `models.py:710-726` |
| `EventClient` / `Client` | contratante e cliente, pela ordem de `contratante_name` | `models.py:1841-1866`; `vendas_ops.py:81-93` |
| `CommissionPayment` | `payable_from` passa a ser usado também pela comissão comum (R22) | `models.py:914-925`; `comissoes_ops.py:689-747` |
| `SiteSetting.release_date` | a data de início (01/06/2026 em produção; reserva 01/06/2026), via `corte_dia_sp()` | `models.py:835`; `formularios_ops.py:86-91` |

## `VendaResumo` (derivado, imutável)

Uma venda é um evento avulso ou um grupo, sempre representado pelo **principal**.

| Campo | Tipo | Regra |
|---|---|---|
| `principal` | `CalendarEvent` | `group_leader` se existir; senão o próprio evento (R5). Com o principal apagado, cada outro evento é uma venda avulsa |
| `eventos` | `tuple[CalendarEvent, ...]` | principal primeiro, satélites depois, **cancelados inclusive** |
| `valor` | `Decimal \| None` | `sale_value` do principal |
| `recebido` | `Decimal` | soma de `EventPayment.amount` de **todos** os eventos do grupo, cancelados inclusive (R3) |
| `data_do_grupo` | `date \| None` | menor `start_at.date()` entre os eventos **não cancelados e que não são compromisso interno** (R5) |
| `vencimento` | `date \| None` | data combinada > 1ª parcela do principal que o recebido não cobre (parcelas somadas pela ordem das datas) > `data_do_grupo − 2`. Os dois últimos com piso na `sale_date` (R7, R33) |
| `vencimento_origem` | `"data_combinada" \| "parcela" \| "politica" \| None` | qual das três regras deu a data; `None` quando nenhuma dá (sem data combinada, sem parcela descoberta e sem data do grupo, como no avulso cancelado) |
| `cliente` | `str \| None` | `contratante_name(principal)` |
| `motivo_fora` | `str \| None` | `cancelado`, `ensaio`, `compromisso_interno`, `cortesia` ou `loja_virtual`, julgados pelo principal (R6) |

Propriedades derivadas, todas em `Decimal`:

| Propriedade | Regra |
|---|---|
| `saldo` | `valor − recebido` (`None` sem valor) |
| `sem_valor` | `valor is None or valor < 1,00` |
| `a_definir` | `valor is None or valor == 0` |
| `valor_simbolico` | `0 < valor < 1,00` |
| `sinal_pendente` | sem data combinada, sem cronograma de parcelas **e** `recebido < valor/2 − 1,00` |
| `eventos_vivos` | quantos eventos não cancelados o grupo tem |
| `situacao` | ver a tabela abaixo |

## Estados de uma venda (`situacao`)

| Estado | Condição | Onde aparece |
|---|---|---|
| `fora` | `motivo_fora` preenchido, ou `data_do_grupo` antes do corte | em nenhuma lista |
| `sem_valor` | `sem_valor` | "Evento sem valor de venda" |
| `quitada` | valor ≥ 1,00 e `saldo < 1,00` (inclui recebido acima do valor), fora cortesia | em nenhuma lista; na página, "Quitado" (a cortesia nunca: ela é `fora`, e a página diz "cortesia ou permuta") |
| `com_saldo` | valor ≥ 1,00 e `saldo ≥ 1,00` | "Cobranças" |

Transições que tiram a linha da lista (FR-010), com a animação na tela:
- `sem_valor` → `com_saldo` ou `quitada`: alguém põe o valor, pela aba Comercial, pelo orçamento ou
  pela edição completa.
- `com_saldo` → `quitada`: entra um comprovante em qualquer evento do grupo.
- qualquer estado → `fora`: o evento é cancelado, vira cortesia ou recebe o marcador.

## Linhas da Home (calculadas com `hoje` de São Paulo)

**Cobrança** (`situacao == com_saldo`):

| Campo | Regra |
|---|---|
| `dias_ate_vencimento` | `vencimento − hoje` (negativo = venceu) |
| `severidade` | vermelho se dias ≤ 2 (inclui vencido); senão amarelo se `sinal_pendente` ou dias de 3 a 30; senão cinza |
| `selo` | vermelho: "Atrasado" (dias < 0), "Vence hoje" (0) ou "Vence em N dias"; amarelo com sinal pendente: "Sinal pendente"; demais: "Vence em N dias" |
| `nota` | "sem sinal" quando vermelho e `sinal_pendente` |
| ordem | por cor (vermelho, amarelo, cinza) e, dentro da cor, vencimento ascendente, depois `data_do_grupo`, depois `event_id` |

**Sem valor** (`situacao == sem_valor`):

| Campo | Regra |
|---|---|
| `dias_ate_o_evento` | `data_do_grupo − hoje` |
| partição | `a_acontecer` (dias ≥ 0, hoje incluído, o mais próximo primeiro) e `ja_aconteceu` (dias < 0, o mais recente primeiro) |
| `severidade` | vermelho se dias ≤ 7 (inclui o que já aconteceu); amarelo de 8 a 30; cinza acima de 30 |

**Para o total do topo e o card**: `para_agir` = linhas vermelhas + amarelas de cada lista comercial
(Cobranças, Sem valor e Formulários da 298).

## Regras de escrita (sem campo novo)

| Regra | Onde | Efeito |
|---|---|---|
| "Valor a definir" | `aplicar_valor_a_definir` (`event_ops`) | `sale_value` e `sale_value_gross` gravados `NULL`; a marca não é gravada |
| Valor abaixo de R$ 1,00 sem a marca | `_validate_event_core` | 400, exceto na edição que mantém o mesmo valor simbólico (R$ 0,01 a R$ 0,99) que o evento já tinha, campo a campo (R32) |
| Data da venda | `resolver_data_da_venda(..., a_definir)` | a criação sem data vira hoje (SP); a edição sem data mantém a atual; o evento sem data que ganha valor recebe hoje (como hoje) |
| Satélite na edição completa | `update_event_core` | nenhum campo comercial é gravado no satélite |
| Comissão tardia | `_sync_commission_payment` | comissão comum que nasce, ou passa de simbólico para real, quando o valor chegou depois (evento cadastrado num mês anterior ao corrente e `sale_date` também num mês anterior, R45) → `payable_from = hoje`, e não volta a `NULL`; a venda lançada agora com data de um mês anterior segue a `sale_date`, como hoje; a comissão paga de valor real nunca muda nem se duplica; a linha de R$ 0,00 já paga não conta, e nasce uma `a_pagar` nova (R42), só quando a comissão calculada é maior que zero e só na comissão comum; a cortesia nunca comissiona |
| Valor simbólico na aba Comercial | `event_ops.erros_do_valor_na_aba_comercial`, chamada por `api_update_event_comercial` | valor novo entre R$ 0,01 e R$ 0,99 → 400; vazio aceito (R43) |
| Valor simbólico no orçamento | `aplicar_valores_do_orcamento` | abaixo de R$ 1,00 conta como "sem venda"; a cortesia continua recusada |

## Invariantes (vão para o `docs/04`)

1. Na cobrança, o grupo é uma venda só: o valor é o do principal, o recebido é o de todos os eventos
   e nada é movido de lugar.
2. "Sem valor" na Home = vazio, zero ou abaixo de R$ 1,00. No Financeiro e na Auditoria continua
   `<= 0`: são duas definições de propósito.
3. Compromisso interno é o título que começa com 🟧 ou 🟠. Ele nunca é venda e não conta na data do
   grupo.
4. A folga de centavos é R$ 1,00, no saldo, no sinal e no "Quitado" da página.
5. Com data combinada ou cronograma, não há sinal pendente. O vencimento nunca fica antes da data da
   venda.
6. A comissão tardia (o evento já existia num mês anterior, sem valor) entra no ciclo do mês do
   valor, e a comissão paga nunca é paga de novo.
