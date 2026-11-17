# Modelo de dados — 333

Migration `c333e1a5b7d9` (`down_revision = "b332d5f7a9c1"`), aditiva.

## `orcamento_history` (existe)

| Coluna nova | Tipo | Regra |
|---|---|---|
| `client_id` | Integer, FK `clients.id` `ON DELETE SET NULL`, índice | A ficha da cliente. Gravada no primeiro envio pela conversa e nunca trocada por envio seguinte (FR-006). |

## `conversas` (existe)

| Coluna nova | Tipo | Regra |
|---|---|---|
| `ficha_manual` | Boolean, NOT NULL, `server_default false` | A ficha (ou a falta dela, depois de "Remover vínculo") foi escolhida à mão: a ligação automática pelo telefone não age (FR-009). |

## `orcamento_envios` (nova)

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | Integer PK | |
| `orcamento_id` | Integer, FK `orcamento_history.id` `ON DELETE CASCADE`, índice | |
| `conversa_id` | Integer, FK `conversas.id` `ON DELETE CASCADE`, índice | |
| `autor_id` | Integer, FK `users.id` `ON DELETE SET NULL` | Quem enviou. |
| `chave_envio` | String(64), UNIQUE (`uq_orcamento_envios_chave`) | A chave base do pedido; as partes usam `{chave}:n` e `{chave}:pdf`. |
| `texto_mensagem_id` | Integer, FK `conversa_mensagens.id` `ON DELETE SET NULL` | A primeira parte do texto. |
| `pdf_mensagem_id` | Integer, FK `conversa_mensagens.id` `ON DELETE SET NULL` | O PDF. |
| `created_at` | DateTime, NOT NULL | UTC naive, como as Conversas. |

## `clients` (existe)

`source` ganha o valor `conversa`: a ficha criada pela conversa. `client_metrics` ganha o balde `conversa`.
