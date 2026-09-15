# Contrato — bloco `comercial` do `GET /api/dashboard` (feature 299)

**Gate inalterado.** `show_comercial` (COMERCIAL, FINANCEIRO e SUPERADMIN), sempre pelo papel
efetivo, que respeita o "Ver como" (`dashboard_service.py:507-516`). `comercial: null` significa sem
permissão, ou que o painel inteiro falhou. CASTING recebe `null` (cenário 16).

**Compatibilidade** (R26, SC-011):
- `pending_payments` é **sempre uma lista** quando `comercial` não é `null`.
- As chaves antigas continuam com o mesmo nome e o mesmo tipo.
- Todo campo novo é **opcional no TS** e lido com fallback (`?.`, `?? 0`, `[]`).

## Formato

```json
{
  "comercial": {
    "corte": "2026-06-01",
    "pode_editar_venda": true,
    "pending_payments": [ "<LinhaCobranca>" ],
    "cobrancas_resumo": {
      "por_cor": { "vermelho": 9, "amarelo": 18, "cinza": 13 },
      "para_agir": 27,
      "total_em_aberto": 123456.78
    },
    "sem_valor": {
      "por_cor": { "vermelho": 3, "amarelo": 1, "cinza": 2 },
      "para_agir": 4,
      "a_acontecer": [ "<LinhaSemValor>" ],
      "ja_aconteceu": [ "<LinhaSemValor>" ]
    }
  },
  "formularios": { "...o bloco da 298...": "", "para_agir": 12 }
}
```

- **`corte`**: `corte_dia_sp()` (a data de início, `release_date`, ou 01/06/2026 se estiver vazia). É
  o mesmo dia de `formularios.contagens.corte`.
- **`pode_editar_venda`**: o mesmo cálculo do `pode_criar_evento` da 298 (SUPERADMIN real, ou papel
  efetivo em `_CAN_CREATE`). Com `false`, a ação da linha "sem valor" é "Abrir".
- **`cobrancas_resumo: null` / `sem_valor: null`**: aquela lista falhou (`_bloco` interno). A tela
  mostra "Não foi possível carregar …" com "Tentar de novo" (FR-032), nunca o "✓".
- **Listas**: vêm **inteiras**. O corte em 6 linhas por lista ou grupo é da tela.
- **`formularios.para_agir`**: aditivo. Conta as **linhas** vermelhas e amarelas de `a_chegar` mais
  `ja_passou`.

## `LinhaCobranca` (cada item de `pending_payments`)

Chaves antigas (compatibilidade):

| Chave | Tipo | Agora significa |
|---|---|---|
| `event_id` | int | o principal da venda |
| `event_title` | string | título do principal |
| `start_at` | string ISO \| null | início do principal |
| `sale` | number | valor de venda do principal |
| `received` | number | recebido do **grupo** |
| `saldo` | number | `sale − received` (sempre ≥ 1,00 nesta lista) |
| `severity` | `"atrasado" \| "urgent" \| "warn" \| "info"` | derivada da cor: vencido → `atrasado`; vermelho a vencer → `urgent`; amarelo → `warn`; cinza → `info` |
| `due_date` | `"AAAA-MM-DD"` \| null | = `vencimento` |

Chaves novas (opcionais no TS):

| Chave | Tipo | Regra |
|---|---|---|
| `titulo` | string | título do principal |
| `cliente` | string \| null | Contratante > 1ª cliente; `null` → a tela mostra `titulo` |
| `data_evento` | `"AAAA-MM-DD"` | data do grupo (1º evento não cancelado e que não é compromisso interno) |
| `vencimento` | `"AAAA-MM-DD"` | data combinada > 1ª parcela do principal que o recebido do grupo não cobre > data do grupo − 2. Os dois últimos nunca antes da data da venda |
| `vencimento_origem` | `"data_combinada" \| "parcela" \| "politica"` | a tela mostra "(data combinada)" no primeiro caso |
| `dias_ate_vencimento` | int | `vencimento − hoje` (SP); negativo = venceu |
| `sinal_pendente` | bool | sem data combinada, sem cronograma, e recebido < metade − R$ 1,00 |
| `severidade` | `"vermelho" \| "amarelo" \| "cinza"` | vermelho se vence em até 2 dias (inclui vencido); senão amarelo se sinal pendente ou vence em 3–30; senão cinza |
| `selo` | string | vermelho: "Atrasado" \| "Vence hoje" \| "Vence em N dias"; amarelo com sinal pendente: "Sinal pendente"; demais: "Vence em N dias" (pronto, pt-BR, "Vence em 1 dia" no singular) |
| `nota` | string \| null | "sem sinal" quando a linha é vermelha e o sinal está pendente |
| `grupo_comercial` | `{ "nome": string, "eventos": int }` \| null | só em grupo; `eventos` = não cancelados |

**Ordem**: pela cor (vermelho, amarelo, cinza) e, dentro da cor, vencimento ascendente, depois data do
grupo, depois `event_id`.

**Entram**, sempre julgando pelo principal, as vendas (evento avulso ou principal):
- com data do grupo ≥ corte;
- sem motivo de ficar fora: cancelado, ensaio, 🟧/🟠, cortesia ou Loja Virtual;
- com valor ≥ R$ 1,00 e saldo ≥ R$ 1,00.

## `LinhaSemValor`

| Chave | Tipo | Regra |
|---|---|---|
| `event_id` | int | o principal |
| `titulo` | string | título do principal |
| `cliente` | string \| null | como na cobrança |
| `grupo_comercial` | `{ "nome", "eventos" }` \| null | como na cobrança |
| `data_evento` | `"AAAA-MM-DD"` | data do grupo |
| `dias_ate_o_evento` | int | 0 = hoje; negativo = já aconteceu |
| `valor` | number \| null | o valor gravado |
| `a_definir` | bool | valor vazio ou zero (a tela mostra "a definir") |
| `valor_simbolico` | bool | `0 < valor < 1,00` (a tela mostra o valor com "(valor simbólico)") |
| `recebido` | number | recebido do grupo (a linha mostra "já recebeu R$ X" quando for maior que 0) |
| `severidade` | `"vermelho" \| "amarelo" \| "cinza"` | vermelho se já aconteceu ou acontece em até 7 dias; amarelo 8–30; cinza > 30 |

**Partição**:
- `a_acontecer`: `dias ≥ 0`, com hoje incluído ("hoje"), o mais próximo primeiro.
- `ja_aconteceu`: `dias < 0`, o mais recente primeiro.

**Entram** as vendas com data do grupo ≥ corte, sem motivo de ficar fora e com valor vazio, zero ou
abaixo de R$ 1,00. Outro evento de grupo não entra como linha própria. Se o principal foi apagado, os
outros eventos já não são grupo e entram um a um.

## Consumo no React (`DashboardPage.tsx` + `components/home/*`)

- **Tipos** (`lib/types.ts`):
  - `PendingPayment` ganha os campos novos, todos opcionais;
  - nascem `LinhaSemValor`, `SemValorSummary` e `ComercialSummary`;
  - `LinhaFormulario.severidade` usa o tipo `Severidade` compartilhado.
- **Painéis**:
  - "Cobranças" (`SectionKey` `comercial`, uma lista só) e "Sem valor" (`SectionKey` `sem_valor`,
    dois grupos), no lugar do "💼 Comercial";
  - os dois são montados com `GrupoDeLinhas` e `LinhaDaHome`, extraídos da 298, com 6 linhas por
    lista ou grupo;
  - as ações levam a `/events/<event_id>?aba=comercial`.
- **Cards e total**:
  - o número do card comercial é o `para_agir`, e `SectionStat.noTotal` usa o mesmo número;
  - os painéis de operação continuam com `count`;
  - o contador do painel aberto mostra todas as linhas;
  - "R$ X em aberto" vem de `cobrancas_resumo.total_em_aberto`;
  - sem cobrança, o card mostra "Em dia ✓" e o painel "Nenhuma cobrança em aberto ✓".
- **Servidor antigo** (janela de deploy):
  - sem `sem_valor`, não há painel nem card, e nunca aparece o "✓";
  - sem `severidade`, a linha fica cinza e sem selo;
  - sem `para_agir`, o card e o total usam `count`;
  - sem `total_em_aberto`, a soma é a de hoje.
