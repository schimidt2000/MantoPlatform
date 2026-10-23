# Data model — Feature 317

Migration única, **aditiva**, escrita à mão: `migrations/versions/<rev>_contratos_clicksign.py`,
`down_revision = "c5d2f7a9e306"` (cabeça da `main` em 22/10). **Atenção**: a 310 (não mergeada) também parte de
`c5d2f7a9e306` (`e8b4a1c7d310`); quem mergear por último reencadeia o `down_revision`. Estilo: o de
`c5d2f7a9e306_dinheiro_do_cancelamento.py` (docstring "Aditiva / Rollback", `op.create_table` + `op.create_index`,
downgrade derruba índices e filhas primeiro). Horários em **SP sem fuso** (`now_sp()`), convertendo os `-03:00` da API.

## `clicksign_documentos` (novo) — `ClicksignDocumento`

Um envelope da conta ClickSign (cada envelope dos fluxos tem um documento e um signatário).

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | Integer PK | |
| `envelope_id` | String(36) | NOT NULL, **UNIQUE** (`uq_clicksign_documentos_envelope`) — chave da idempotência |
| `document_id` | String(36) | nulo até a 1ª consulta de documentos |
| `nome` | Text | nome do envelope como veio (para a tela) |
| `tipo` | String(12) | `cliente` · `artista` · `outro` (R-03) |
| `status` | String(12) | `draft` · `running` · `closed` · `canceled` (o da API) |
| `recusado` | Boolean | default False — evento `refusal` visto |
| `prazo` | DateTime | `deadline_at` |
| `criado_em` / `modificado_em` | DateTime | `created` / `modified` do envelope |
| `assinado_em` | DateTime | evento `sign` (o último) ou `auto_close` |
| `cancelado_em` | DateTime | `modified` quando `canceled` |
| `signatario_nome` | String(200) | |
| `signatario_telefone` | String(20) | normalizado com DDI (`normalize_phone`) |
| `signatario_email` | String(200) | |
| `canal` | String(10) | `whatsapp` · `email` · `sms` · `none` (`communicate_events.signature_request`) |
| `data_lida` | Date | do nome (R-02) |
| `telefone_lido` | String(20) | do nome, normalizado |
| `tema_lido` | String(200) | tema ou razão social |
| `event_id` | FK `calendar_events.id` **ON DELETE SET NULL** | o **principal** da venda (ou avulso) |
| `vinculo` | String(12) | `ligado` · `a_conferir` · `descartado` · `fora` (artista/outro) |
| `vinculo_origem` | String(10) | `auto` · `manual` |
| `vinculo_motivo` | String(40) | por que ficou a conferir (`sem_candidato`, `empate`, `cancelada`, `telefone_diverge`, `data_ilegivel`, `desligado`) |
| `vinculado_por_id` | FK `users.id` ON DELETE SET NULL | quem ligou/desligou à mão |
| `vinculado_em` | DateTime | |
| `contrato_anexo_id` | FK `event_contracts.id` ON DELETE SET NULL | o PDF assinado anexado |
| `anexo_pendente` | Boolean | default False — vira True quando o documento fecha ligado; o anexo bem-sucedido ou recusado (arquivo grande/ inválido → log) o zera. Excluir o anexo NÃO o religa (não reanexa sozinho) |
| `sincronizado_em` | DateTime | NOT NULL |

Índices: `ix_clicksign_documentos_event_id`, `ix_clicksign_documentos_vinculo` (parcial `vinculo = 'a_conferir'`, também
declarado no `__table_args__`), `ix_clicksign_documentos_data_lida`.

Transições do `vinculo`:

```text
(novo, tipo cliente) ──candidato único──▶ ligado(auto)
(novo, tipo cliente) ──empate/sem candidato/cancelada──▶ a_conferir
(novo, artista|outro) ──▶ fora
a_conferir ──Ligar (COMERCIAL/SA)──▶ ligado(manual)
ligado ──Desligar──▶ a_conferir (motivo desligado) + linha em clicksign_desvinculos
a_conferir ──Descartar──▶ descartado (definitivo)
ligado ──venda excluída (_clear_event_side_tables)──▶ a_conferir (event_id NULL)
ligado ──passar_venda──▶ ligado no novo principal (TABELAS_DA_PASSAGEM, com desvínculos e cobranças)
ligado ──agrupar/desagrupar──▶ não move (a busca do vigente é pelo grupo)
ligado ──evento apagado pelo sumiço do Google──▶ impossível: documento ligado prende o evento (sumico_ops.preso_ao_evento)
```

A sincronização só reavalia o vínculo de documento **novo** ou `a_conferir` com `vinculo_origem` vazio; nunca mexe em
`ligado(manual)`, `descartado` nem religa par desvinculado.

## `clicksign_desvinculos` (novo) — `ClicksignDesvinculo`

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | Integer PK | |
| `documento_id` | FK `clicksign_documentos.id` ON DELETE CASCADE | NOT NULL |
| `event_id` | FK `calendar_events.id` ON DELETE CASCADE | NOT NULL |
| `por_id` | FK `users.id` ON DELETE SET NULL | |
| `em` | DateTime | NOT NULL, `now_sp` |

UNIQUE (`documento_id`, `event_id`) — molde `FormResponseDismissedEvent` (298), sem backref.

## `clicksign_cobrancas` (novo) — `ClicksignCobranca`

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | Integer PK | |
| `documento_id` | FK `clicksign_documentos.id` ON DELETE CASCADE | NOT NULL |
| `event_id` | FK `calendar_events.id` ON DELETE CASCADE | NOT NULL (principal na hora da cobrança) |
| `usuario_id` | FK `users.id` ON DELETE SET NULL | |
| `usuario_nome` | String(120) | NOT NULL (o nome sobrevive à exclusão do usuário) |
| `em` | DateTime | NOT NULL, `now_sp` |

Índice `ix_clicksign_cobrancas_documento_em` (`documento_id`, `em`).

## `site_settings` (colunas novas)

| Coluna | Tipo | Para quê |
|---|---|---|
| `clicksign_webhook_id` | String(36) | id do aviso cadastrado na ClickSign |
| `clicksign_webhook_secret` | String(64) | segredo HMAC atual (R-05) |
| `clicksign_webhook_secret_anterior` | String(64) | vale 24 h depois de recadastrar |
| `clicksign_webhook_secret_anterior_ate` | DateTime | |
| `clicksign_sync_at` | DateTime | claim atômico da sincronização (3 workers gunicorn) |
| `clicksign_sync_cursor` | DateTime | `modified` máximo já processado (início da próxima busca, com folga de 10 min) |
| `clicksign_sync_pendente` | Boolean (NOT NULL, default false) | o aviso que chega com uma passada em curso marca; a passada repete antes de soltar o claim |
| `clicksign_sync_fim` | DateTime | fim da última passada aplicada: a periódica dos outros workers pula (converge C-15) |

Lock, marco, pendente e fim são escritos numa **conexão própria** (fora da sessão da passada): a simulação nunca
comita nada, e o lock é renovado a cada página (converge C-09/C-10).

As colunas antigas `clicksign_token` / `clicksign_sandbox` continuam **inertes** (nunca lidas; dívida no `docs/05`).

## Sem mudança de schema

- `EventContract`: o PDF assinado vira uma linha normal (`file_path` em `contracts/`, `is_signed=True`), criada pela
  sincronização; o `EventLog` dela leva `actor_name="ClickSign (automático)"`, `actor_role="Sistema"`.
- `CalendarEvent`, `Client`, `EventClient`, `FormResponse`: só leitura (telefones e tema).

## Regras derivadas (núcleo puro `app/contratos/contratos_ops.py`)

- **Venda que entra** (clarify): principal ou avulso, desde `corte_dia_sp()`, fora cancelado, ENSAIO, compromisso
  interno e loja virtual; **cortesia entra** (diferente de `motivo_fora_da_venda`, que a exclui).
- **Vigente** (R-04): `ClicksignDocumento` `tipo=cliente`, `vinculo=ligado`, `event_id IN group_events(principal)` (o
  documento ligado a um dia que depois virou satélite continua valendo para a venda — achado R1 do analyze); o de
  `criado_em` **mais recente**, sempre (converge C-05: a remarcação vencida não volta a "Assinado" pelo contrato
  antigo; o reenvio `(1)` assinado já é o mais recente). Na Home, em lote por todos os ids dos grupos.
- **Assinado à mão**: algum `EventContract.is_signed` em qualquer dia do grupo cujo id **não** é `contrato_anexo_id` de
  nenhum documento (o PDF automático não conta como marca manual).
- **Situação**: `assinado` · `assinado_manual` · `aguardando` · `vencido` · `recusado` · `sem_contrato`.
- **Cor** (Premissa 5): aguardando → pior entre prazo (`≤1 dia` vermelho, `2–3` amarelo) e evento (`≤7` vermelho,
  `8–30` amarelo); sem contrato → régua do evento (`FORM_COR_*`); vencido/recusado → sempre vermelho (FR-010). Contagem
  por cor própria do domínio (sem "verde"; não reusar `resumo_por_cor`).
- **Chave de telefone**: DDD + últimos 8 dígitos (casa celular antigo de 8 dígitos e número sem 55); fontes: `Client.phone`
  do `CalendarEvent.client`, dos `EventClient` e `FormResponse.contact_phone` ligado — em lote, não por evento.
- **Coluna de `/vendas`** (FR-019): `contract_status_map` devolve as seis situações quando a integração está ligada; a
  venda sem documento cai na regra antiga do `EventContract` (`pendente` → "Anexo sem assinatura"). Labels e
  `ContractStatus` do frontend ampliados (`VendasPipelinePage.tsx:34`, `vendas.ts:6`).
- **Pode cobrar**: só principal/avulso (`escopo_do_evento`), venda viva, situação `aguardando`, papel COMERCIAL/SA.
