# Modelo de dados — 340

## `virtual_payment_inbox` (nova) — `VirtualPaymentInbox` em `app/models.py`

O aviso de pagamento como chegou ao `manto-avisos`, antes de qualquer decisão. Quem escreve a linha
é o receptor; quem a drena é o backend. Relógio: São Paulo ingênuo (`now_sp`), como as demais
`virtual_*`.

| Coluna | Tipo | Nulo | Default | Quem grava | Para quê |
|---|---|---|---|---|---|
| `id` | Integer PK | não | serial | receptor | ordem de chegada |
| `received_at` | DateTime | não | `now_sp` | receptor | idade da linha (alerta de 1 h) |
| `body` | Text | não | — | receptor | corpo como veio (≤ 64 KB; ≤ 2 KB se `secret_ok` falso) |
| `secret_ok` | Boolean | não | `false` | receptor | resultado da conferência do segredo **na chegada** |
| `claimed_at` | DateTime | sim | — | backend | arrendamento do dreno (5 min) |
| `attempts` | Integer | não | `0` | backend | voltas que tentaram drenar |
| `error` | Text | sim | — | backend | última falha (truncada em 500) |
| `drained_at` | DateTime | sim | — | backend | registrada na fila da 310 |
| `notification_id` | Integer FK → `virtual_payment_notifications.id` `ON DELETE SET NULL` | sim | — | backend | o registro que nasceu (nulo se o aviso já estava decidido) |
| `alerted_at` | DateTime | sim | — | backend | sino de linha parada já tocado |

Índice parcial `ix_virtual_payment_inbox_pendentes` em `(id)` `WHERE drained_at IS NULL` — o dreno
roda a cada 10 s em três workers e só olha o que falta.

**Nunca guarda** o segredo do endereço nem cabeçalhos da requisição.

**Ciclo de vida**: `recebida` (`drained_at` nulo, `claimed_at` nulo) → `reivindicada`
(`claimed_at` recente) → `drenada` (`drained_at` preenchido). Reivindicada há mais de 5 min sem
dreno volta a ser elegível. Não drenada há mais de 1 h → `alerted_at` (uma vez).

**Retenção**: sem limpeza nesta feature — dezenas de linhas por dia, o mesmo volume de
`virtual_payment_notifications`, que também não é limpa.

## Migration

`migrations/versions/e340c1a2b3d4_caixa_de_avisos.py`, aditiva, `down_revision` = head da `main`
no merge (hoje `d323b5a1c0e7`; reencadear se outra feature entrar antes). `upgrade` cria a tabela,
a FK e o índice parcial; `downgrade` derruba os três. Nenhum dado existente é tocado.

## Configuração (`app/config.py`)

| Nome | Default | Para quê |
|---|---|---|
| `AVISOS_BASE_URL` (constante de módulo) | `https://manto-avisos.onrender.com` | endereço do receptor |
| `Config.INFINITEPAY_AVISO_BASE_URL` | `_url_para_fora(env, AVISOS_BASE_URL, …)` | base do `webhook_url` dos links novos |
| `Config.VIRTUAL_CAIXA_INTERVAL` | `10` | intervalo (s) da thread de dreno |

## Constantes (`app/constants.py`)

`VIRTUAL_CAIXA_ARRENDAMENTO_MIN = 5`, `VIRTUAL_CAIXA_ALERTA_HORAS = 1`, `VIRTUAL_CAIXA_LOTE = 50`.
