# Modelo de dados — 328 Conversas em equipe

Migration à mão, **aditiva**, `down_revision = "e325a7c1d9f2"` (head da 325). Relógio: UTC naive, como as tabelas
da 325.

## `conversas` — colunas novas

| Coluna | Tipo | Regra |
|---|---|---|
| `responsavel_id` | FK `users.id` SET NULL, null, index | quem atende; nulo = fila livre |
| `assumida_em` | DateTime, null | UTC; quando o responsável atual assumiu |
| `aguardando_desde` | DateTime, null, index | UTC; primeira mensagem da cliente ainda sem resposta; nulo = ninguém esperando |

Transições do responsável: nulo → pessoa (resposta da pessoa, ou "Assumir") → outra pessoa ("Transferir") →
nulo ("Devolver à fila"). Transições da espera: nulo → momento da recebida (mensagem nova com a coluna nula) →
nulo (envio aceito pela Meta ou eco do celular).

## `conversa_notas` (`ConversaNota`)

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | Integer PK | |
| `conversa_id` | FK `conversas.id` CASCADE, index | |
| `autor_id` | FK `users.id` SET NULL, null | |
| `texto` | Text | 1–2.000 caracteres (aparado) |
| `created_at` | DateTime | UTC |

Só se acrescenta: sem edição e sem exclusão nesta fase.

## `respostas_rapidas` (`RespostaRapida`)

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | Integer PK | |
| `titulo` | String(80) | obrigatório; índice único em `lower(titulo)` (`uq_respostas_rapidas_titulo`) |
| `atalho` | String(30), null | minúsculas, sem `/` e sem espaço; índice único (`uq_respostas_rapidas_atalho`) |
| `texto` | Text | 1–4.096 caracteres; pode ter `{nome}` |
| `criado_por_id` | FK `users.id` SET NULL, null | |
| `alterado_por_id` | FK `users.id` SET NULL, null | |
| `created_at` / `updated_at` | DateTime | UTC |

## Notificação (sem tabela nova)

Kind `conversa.esperando` em `notifications`, com:
- `entity_type = "conversa"`, `entity_id = conversas.id`;
- `dedupe_key = "conversa.esperando:{id}:{epoch de aguardando_desde}"`;
- `link_path = "/conversas?c={id}"`.

Apagada por `apagar_por_entidade("conversa", id, kind="conversa.esperando")` quando a espera termina.

Kind `conversa.transferida` (FR-018), só para o destino da transferência:
- `entity_type = "conversa"`, `entity_id = conversas.id`;
- `dedupe_key = "conversa.transferida:{id}:{epoch de assumida_em}"`;
- `link_path = "/conversas?c={id}"`.

Não é apagado quando a espera termina: some pela retenção normal da 272.
