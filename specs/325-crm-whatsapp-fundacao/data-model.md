# Modelo de dados — 325 Conversas (WhatsApp)

Migration à mão, **aditiva** (quatro tabelas novas; nenhuma coluna existente muda). `down_revision` =
head atual no momento da escrita (ver `plan.md` §Migration). Relógio: **UTC naive** em todas as
colunas de horário destas tabelas (`datetime.utcnow()`/`fromtimestamp(..., tz=utc)` sem tz), como
`created_at` do resto do sistema. A API serializa com o sufixo `+00:00` explícito
(`_iso_utc`), para o React converter para São Paulo sem o deslize de 3 h da armadilha 1 do `docs/00` §6.

## `whatsapp_avisos` — o aviso cru do webhook (`WhatsappAviso`)

Um POST da Meta = uma linha, gravada **antes** de qualquer processamento (FR-003).

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | Integer PK | |
| `corpo` | Text | JSON cru, exatamente como chegou (≤ 256 KB; acima → 413, nada gravado) |
| `estado` | String(20), index | `pendente` → `processando` → `processado` \| `descartado` (ver máquina abaixo) |
| `tentativas` | Integer, default 0 | incrementado no claim |
| `erro` | String(500), null | última falha legível (sem stack) |
| `recebido_em` | DateTime | UTC |
| `tentado_em` | DateTime, null | UTC do último claim (resgate do `processando` parado) |
| `processado_em` | DateTime, null | UTC |

Máquina de estados: `pendente` → (claim atômico `UPDATE … WHERE estado='pendente'`, `tentativas+1`)
`processando` → `processado`. Falha no processamento (exceção, mensagem do status ainda não gravada)
devolve a `pendente` com `erro`. Com **48 h** de idade ou **10 tentativas**, vira `descartado` (e o
erro fica para auditoria). A varredura também resgata `processando` parado há mais de 10 min (a
thread morreu no deploy).

## `conversas` — um contato num canal (`Conversa`)

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | Integer PK | |
| `canal` | String(20) | `whatsapp` (Fase 2: `instagram`) — constante `CANAL_*` |
| `contato_id` | String(64) | identificador do contato no canal: o `wa_id` da Meta como veio; sem `wa_id` (usuário só com nome de usuário), o BSUID |
| `contato_bsuid` | String(64), null | BSUID da Meta (`contacts[].user_id`, `"BR.…"`, desde abril de 2026); envio por `recipient` quando não há `wa_id` |
| `telefone` | String(20), null, index | dígitos com DDI, **com** nono dígito (forma de `Client.phone`) |
| `nome_perfil` | String(255), null | `contacts[].profile.name`; atualizado a cada aviso |
| `client_id` | FK `clients.id` SET NULL, null, index | ficha ligada pelo telefone (FR-005) |
| `ultima_recebida_em` | DateTime, null | UTC; **base da janela de 24 h** |
| `ultima_mensagem_em` | DateTime, null, index | UTC; ordena a lista |
| `ultima_previa` | String(200), null | trecho da última mensagem (texto ou rótulo do tipo) |
| `nao_lidas` | Integer, default 0 | contagem **compartilhada** da equipe (Clarifications) |
| `created_at` / `updated_at` | DateTime | UTC |

Restrição: **`UNIQUE(canal, contato_id)`** (`uq_conversas_canal_contato`) — a criação usa
`INSERT … ON CONFLICT DO NOTHING` e relê, para dois avisos simultâneos do mesmo contato não
duplicarem.

Janela: `janela_aberta = ultima_recebida_em is not None and agora_utc - ultima_recebida_em < 24 h`.

## `conversa_mensagens` — uma mensagem (`ConversaMensagem`)

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | Integer PK | |
| `conversa_id` | FK `conversas.id` CASCADE, index | |
| `direcao` | String(10) | `recebida` \| `enviada` |
| `tipo` | String(20) | `texto`, `imagem`, `audio`, `video`, `documento`, `figurinha`, `localizacao`, `contato`, `reacao`, `interativa`, `modelo`, `outro` |
| `texto` | Text, null | corpo, legenda ou texto curto do tipo não exibido |
| `externo_id` | String(128), null, **UNIQUE** | `wamid` da Meta — idempotência dos reenvios |
| `chave_envio` | String(64), null, **UNIQUE** | chave do navegador no envio — clique duplo (FR-018) |
| `situacao` | String(12) | recebida: `recebida`; enviada: `pendente` → `enviada` → `entregue` → `lida`, ou `falhou` |
| `erro_codigo` | Integer, null | código da Meta (`errors[0].code`) |
| `erro_motivo` | String(500), null | motivo legível em pt-BR |
| `autor_id` | FK `users.id` SET NULL, null | quem da equipe enviou pela Plataforma |
| `origem` | String(12) | `contato` (recebida), `plataforma`, `celular` (eco da coexistência), `outro` |
| `modelo_nome` | String(255), null | nome do modelo, quando `tipo = modelo` |
| `resposta_a` | String(128), null | `context.id` (a mensagem citada) |
| `dados` | Text, null | o item cru do aviso (property tolerante `dados_dict`) |
| `momento` | DateTime, index | UTC: `timestamp` da Meta (recebida/eco) ou a hora do envio |
| `created_at` | DateTime | UTC |

Ordem das situações (nunca regride — FR-009): `pendente`(0) < `enviada`(1) < `entregue`(2) <
`lida`(3). O `played` da Meta (nota de voz ouvida) vira `lida`. `falhou` só substitui
`pendente`/`enviada`; nunca sobrescreve `entregue`/`lida`.

## `conversa_midias` — o arquivo de uma mensagem (`ConversaMidia`)

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | Integer PK | |
| `mensagem_id` | FK `conversa_mensagens.id` CASCADE, **UNIQUE** | uma mídia por mensagem |
| `externo_id` | String(128), null | id da mídia na Meta (download ou o que o upload devolveu) |
| `mime` | String(120), null | |
| `tamanho` | Integer, null | bytes |
| `nome_original` | String(255), null | nome do documento / do arquivo enviado |
| `caminho` | String(500), null | caminho relativo no storage (subpasta `conversas/`) |
| `estado` | String(10) | `pendente` → `guardada` \| `falhou` (download esgotado ou acima do teto) |
| `tentativas` | Integer, default 0 | |
| `erro` | String(500), null | |
| `tentado_em` | DateTime, null | UTC do último claim de download |
| `created_at` / `updated_at` | DateTime | UTC |

## Relações e o que NÃO muda

- `Client` ganha só o backref `conversas` (sem coluna nova). `User` não muda.
- Excluir um cliente: `client_id` vira NULL (SET NULL); a conversa fica.
- Nenhuma tabela existente ganha coluna; o `seed.py` não muda (nenhum papel novo).
