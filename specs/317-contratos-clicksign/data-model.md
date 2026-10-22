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
ligado ──passar_venda──▶ ligado no novo principal (TABELAS_DA_PASSAGEM)
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

As colunas antigas `clicksign_token` / `clicksign_sandbox` continuam **inertes** (nunca lidas; dívida no `docs/05`).

## Sem mudança de schema

- `EventContract`: o PDF assinado vira uma linha normal (`file_path` em `contracts/`, `is_signed=True`), criada pela
  sincronização; o `EventLog` dela leva `actor_name="ClickSign (automático)"`, `actor_role="Sistema"`.
- `CalendarEvent`, `Client`, `EventClient`, `FormResponse`: só leitura (telefones e tema).

## Regras derivadas (núcleo puro `app/contratos/contratos_ops.py`)

- **Venda que entra** (clarify): principal ou avulso, desde `corte_dia_sp()`, fora cancelado, ENSAIO, compromisso
  interno e loja virtual; **cortesia entra** (diferente de `motivo_fora_da_venda`, que a exclui).
- **Vigente** (R-04): `ClicksignDocumento` `tipo=cliente`, `vinculo=ligado`, `event_id = principal`; o de `criado_em`
  mais recente, mas um `closed` vence qualquer `canceled` criado antes dele.
- **Situação**: `assinado` · `assinado_manual` · `aguardando` · `vencido` · `recusado` · `sem_contrato`.
- **Cor** (Premissa 5): aguardando → pior entre prazo (`≤1 dia` vermelho, `2–3` amarelo) e evento (`≤7` vermelho,
  `8–30` amarelo); sem contrato → régua do evento (`FORM_COR_*`); vencido/recusado → vermelho se evento ≤ 30 dias.
- **Pode cobrar**: só principal/avulso (`escopo_do_evento`), venda viva, situação `aguardando`, papel COMERCIAL/SA.
