# Modelo de dados — 350 base autorizada

Migration à mão `migrations/versions/a350b1c2d3e4_base_autorizada.py`, `down_revision = "d334b2c4e6f8"`,
aditiva. Ordem do upgrade: `parceiros` → colunas de `clients` → `cliente_consentimentos` →
`cliente_criancas` → `pos_eventos`. O downgrade desfaz na ordem inversa.

Relógio: todo carimbo novo é `now_sp()` (horário de parede de São Paulo, naive) — o mesmo do aceite da
loja (344). Ver `plan.md` §Rastreamento de complexidade.

## `parceiros` — `Parceiro`

| Coluna | Tipo | Regra |
|---|---|---|
| id | Integer PK | |
| nome | String(160) NOT NULL | 2–160 caracteres |
| tipo | String(20) NOT NULL | `buffet` \| `assessoria` \| `agencia` \| `outro` (`PARCEIRO_TIPOS`) |
| contato | String(120) NULL | pessoa de contato |
| telefone | String(30) NULL | como digitado |
| email | String(200) NULL | |
| comissao_percentual | Numeric(5,2) NOT NULL default 0 | 0 ≤ x ≤ 100, declarada (não paga nada) |
| observacao | Text NULL | |
| ativo | Boolean NOT NULL default true | inativo não aparece na escolha; fichas ligadas mantêm |
| criado_em / atualizado_em | DateTime NOT NULL | `now_sp()` |

Índice: `ix_parceiros_nome`. Sem exclusão (só desativar).

## `clients` — colunas novas em `Client`

| Coluna | Tipo | Regra |
|---|---|---|
| marketing_opt_in_version | String(20) NULL | versão do texto aceito; nulo no legado da 344 até a próxima venda |
| marketing_opt_out_at | DateTime NULL | última retirada (`now_sp()`) |
| marketing_opt_out_source | String(160) NULL | origem da última retirada |
| indicado_por_id | Integer NULL FK `clients.id` ON DELETE SET NULL | nunca o próprio id; índice |
| parceiro_id | Integer NULL FK `parceiros.id` ON DELETE SET NULL | índice |

Estado: **com aceite** ⇔ `marketing_opt_in_at IS NOT NULL`. Retirar zera `marketing_opt_in_at`,
`marketing_opt_in_source`, `marketing_opt_in_version` e grava `marketing_opt_out_*`. Registrar aceite
grava `marketing_opt_in_*` e mantém `marketing_opt_out_*` (história).

Sem `relationship` com backref nas tabelas filhas: o ORM não tenta anular FK `NOT NULL` ao excluir a
ficha; quem apaga é o `ON DELETE CASCADE` do banco.

## `cliente_consentimentos` — `ClienteConsentimento` (histórico, append-only)

| Coluna | Tipo | Regra |
|---|---|---|
| id | Integer PK | |
| client_id | Integer NOT NULL FK `clients.id` ON DELETE CASCADE | |
| tipo | String(20) NOT NULL | `novidades` \| `aniversario` |
| acao | String(10) NOT NULL | `aceite` \| `retirada` |
| texto | Text NOT NULL | texto completo exibido (na retirada: o texto do aceite retirado) |
| versao | String(20) NOT NULL | |
| origem | String(160) NOT NULL | lista de `CONSENTIMENTO_ORIGENS_*` ou "Loja: <campanha>" |
| referencia | String(80) NULL | `conversa:<id>`, `mensagem:<id>`, `evento:<id>`, `pedido:<id>` |
| registrado_por_id | Integer NULL FK `users.id` ON DELETE SET NULL | nulo = a cliente ou o sistema |
| registrado_em | DateTime NOT NULL | `now_sp()` |

Índice `ix_cliente_consentimentos_client` (client_id, registrado_em). Nunca recebe UPDATE nem DELETE
(fora a cascata da ficha). A retirada de aniversário **não** leva nome nem data da criança.

## `cliente_criancas` — `ClienteCrianca`

| Coluna | Tipo | Regra |
|---|---|---|
| id | Integer PK | |
| client_id | Integer NOT NULL FK `clients.id` ON DELETE CASCADE | índice |
| primeiro_nome | String(60) NOT NULL | 1–60, sem espaços nas pontas |
| nascimento | Date NOT NULL | não futuro; idade ≤ 17 |
| aceite_em | DateTime NOT NULL | `now_sp()` |
| aceite_versao | String(20) NOT NULL | |
| aceite_origem | String(160) NOT NULL | |
| registrado_por_id | Integer NULL FK `users.id` ON DELETE SET NULL | |

Existe só com o aceite. Remover = DELETE da linha + linha `retirada` no histórico.

Próximo aniversário: `date(ano, mes, dia)` no ano corrente; já passou → ano seguinte; 29/02 em ano não
bissexto → 28/02. Idade que vai fazer = ano do próximo − ano de nascimento.

## `pos_eventos` — `PosEvento`

| Coluna | Tipo | Regra |
|---|---|---|
| id | Integer PK | |
| event_id | Integer NOT NULL UNIQUE FK `calendar_events.id` ON DELETE CASCADE | um por evento |
| client_id | Integer NULL FK `clients.id` ON DELETE SET NULL | a contratante no momento |
| fotos_url | String(500) NULL | `http(s)://` |
| canal | String(12) NOT NULL | `copiado` \| `conversa` |
| mensagem_id | Integer NULL FK `conversa_mensagens.id` ON DELETE SET NULL | quando enviado pela conversa |
| registrado_por_id | Integer NULL FK `users.id` ON DELETE SET NULL | |
| registrado_em | DateTime NOT NULL | `now_sp()`; atualizado a cada cópia |

Transição: (sem linha) → `copiado` ⇄ `copiado` (atualiza data) → `conversa` (definitivo; uma cópia
depois não rebaixa o canal).

## Lista do pós-evento (consulta, sem tabela)

`calendar_events` com `start_at` entre 00:00 de (hoje − 7) e agora (SP), `cancelled_at IS NULL`,
`group_leader_id IS NULL`, `parent_event_id IS NULL`, `event_type` ≠ `ENSAIO` e título sem
`ENSAIO_TITLE_PREFIX`; LEFT JOIN `pos_eventos`; avaliação recebida = existe `client_feedbacks` do evento.
