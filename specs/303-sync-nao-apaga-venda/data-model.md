# Data model — 303: o sync não apaga evento com venda

**Spec**: [spec.md](./spec.md) · **Pesquisa**: [research.md](./research.md) R1, R2, R7, R10

Uma coluna, um índice e nenhuma tabela. O resto é derivado.

## `calendar_events` (`CalendarEvent`, `app/models.py`)

| Coluna | Tipo | Nulo | Default | Significado |
|---|---|---|---|---|
| `google_missing_since` | `DateTime` | sim | nenhum | Quando o sync percebeu que o evento não está mais no Google Agenda. **Horário de parede de São Paulo, sem fuso** (`now_sp()`), como `cancelled_at`. `NULL` = não marcado. |

Índice parcial `ix_calendar_events_google_missing_since` em `(google_missing_since)`
`WHERE google_missing_since IS NOT NULL` — declarado na migration **e** em `__table_args__` (com
`postgresql_where` e `sqlite_where`, como `Notification`), para um autogenerate futuro não propor o
drop.

**Invariantes**

- **"Marcado" = `google_missing_since IS NOT NULL AND cancelled_at IS NULL`.** A regra tem duas
  formas, e só duas: o predicado de consulta `sumico_ops.filtro_marcados()` (a faixa, a
  reconferência por id, a volta pela lista do mês) e a propriedade `CalendarEvent.is_google_missing`
  para objeto já carregado (a situação, o detalhe, o portal). A marca nunca aparece em evento
  cancelado.
- A marca **não toca** `cancelled_at`, `deletion_requested_*`, venda, comissão nem escala: enquanto
  marcado, o evento vale em tudo como antes (FR-005).
- Só `sumico_ops.marcar` grava a marca (por `UPDATE` condicional: quem não acha a coluna nula não
  marca nem avisa) e só `sumico_ops.desmarcar` a retira. Nada em `sync_events`.
- Venda virtual e evento cancelado nunca são marcados.

**Transições**

```text
           sync confirma ausência + evento com dinheiro
  não marcado ─────────────────────────────────────────▶ marcado
       ▲                                                   │
       │  reapareceu no Google (ciclo, lista do mês         │
       │  ou "Sincronizar")                                 │
       ├────────────────────────────────────────────────────┤
       │  Superadmin devolve ao Google (id novo, ou o       │
       │  id velho que já tinha voltado)                    │
       └────────────────────────────────────────────────────┘
  marcado ──✕── cancelar / excluir: recusados nesta entrega (FR-045)
```

**Leituras derivadas no modelo** (propriedades, sem consulta extra)

| Propriedade | Valor |
|---|---|
| `is_google_missing -> bool` | marca preenchida e não cancelado |
| `situacao -> str \| None` | `cancelado` > `sumiu_do_google` > `exclusao_solicitada` > `None` |
| `situacao_desde -> datetime \| None` | `cancelled_at`, `google_missing_since` ou `deletion_requested_at`, conforme a situação |

As três strings são constantes em `app/constants.py`: `SITUACAO_CANCELADO`,
`SITUACAO_SUMIU_DO_GOOGLE`, `SITUACAO_EXCLUSAO_SOLICITADA`.

**Campos existentes que a devolução ao Google altera**: `google_event_id` e `google_html_link`
(recebem os do evento recriado) e, só quando há vaga de personagem fora do título, `source`
(`"platform"`).

## Migration

`migrations/versions/a7c3e91f4d28_evento_sumiu_do_google.py` — escrita à mão.

- `revision = "a7c3e91f4d28"`, `down_revision = "e5a1c7d93b20"` (head em 30/09; **reconferir ao
  escrever** — a 298b é da mesma onda).
- `upgrade()`: `op.add_column("calendar_events", sa.Column("google_missing_since", sa.DateTime(),
  nullable=True))` e `op.create_index(..., postgresql_where=..., sqlite_where=...)`. Sem `UPDATE`.
- `downgrade()`: `drop_index` e `drop_column`.
- Aditiva e nullable: o código da `main` lê e grava no banco migrado, e um `git revert` é seguro
  para o schema; os eventos marcados têm de ser devolvidos ao Google antes (quickstart §7).
- Molde: `migrations/versions/b8e4d27a91f5_cancelamento_de_evento.py:26-51`.

## `notifications` (`Notification`, feature 272) — sem mudança de schema

Um tipo novo de linha:

| Campo | Valor |
|---|---|
| `kind` | `evento.sumiu_google` |
| `entity_type`, `entity_id` | `calendar_event`, id do evento |
| `severity` | `urgent` |
| `link_path` | `/events/<id>` |
| `dedupe_key` | `evento.sumiu_google:<id>:<AAAAMMDDHHMMSSffffff>` — o carimbo é o valor gravado em `google_missing_since` |
| destinatários | usuários ativos com papel COMERCIAL ou SUPERADMIN, resolvidos na emissão |

`created_at` das notificações é `now_sp()`; não comparar com `audit_logs.created_at` (UTC).

## Estruturas em memória (não persistem)

- **`PresoAoEvento`** (dataclass imutável, `sumico_ops`): `venda: Decimal`, `recebido: Decimal`,
  `n_comprovantes: int`, `tem_contrato: bool`, `n_escalados: int` (sem a vaga automática de técnico
  de som em SHOW), `grupo: str | None` (`"principal"` ou `"satelite"`), `tecnico_automatico: bool`
  (SHOW com a vaga automática ocupada pelo técnico padrão — é o que deixa o retrato dizer "só o
  técnico de som automático"); `.vazio` e `.descricao()`. Decide a FR-001, escreve o histórico e
  alimenta o aviso — uma fonte só. Comissão já paga não entra (decisão do dono, 30/09).
- **`ConsultaEvento`** (dataclass imutável, `service`): `desfecho` (`presente` | `ausente` |
  `inconclusivo`), `item`, `motivo`.
- **`ResultadoLimpeza`** (dataclass, `sumico_ops`): listas `removidos` (títulos), `marcados`,
  `movidos`, `desmarcados`, `presentes_fora_da_lista`, `inconclusivos`, `falhas` (ids).

## Rastro

| Fato | `EventLog` (histórico do evento) | `AuditLog` (`_log_sync`) |
|---|---|---|
| Marcar | "Sumiu do Google Agenda — mantido no sistema. Preso: …. Aviso enviado a N pessoa(s)." (ator Sistema) | `sumiu_do_google` |
| Reaparecer | "Reapareceu no Google Agenda — a marca … foi retirada." (ator Sistema no ciclo e na limpeza; a pessoa que clicou, no "Sincronizar") | `google_reapareceu` |
| Devolver | "Devolveu o evento ao Google Agenda (estava marcado … desde dd/mm/aaaa)." (ator = Superadmin); no ramo "já tinha voltado", o histórico diz que nada foi criado | `google_returned`, com o id velho e o novo (no ramo "já tinha voltado", só o id velho) |
| Devolução recusada pelo Google | — | `google_return_failed`, com o tipo do erro |
| Evento vazio apagado | — (o evento deixa de existir) | `auto_deleted`, com o que o Google respondeu e o retrato do `PresoAoEvento` na hora (`.descricao()`: "venda R$ 0,00 · 0 comprovantes · sem contrato · 0 escalados · sem grupo"; em SHOW, "só o técnico de som automático") — é o que torna o SC-001 conferível |
| Presente fora da lista, sem mudança | — | `presente_fora_da_lista`, uma vez por evento e dia (o dia é o do relógio da coluna, UTC) |
| Dados atualizados pela consulta (evento fora da lista que mudou) | — | `google_updated`, o registro que `sync_events` já faz (só quando data, horário ou local mudam, como hoje) |
| Inconclusivo | — | sem linha por evento; entra no total "sem confirmação" do resumo do ciclo (`sync_ok`/`sync_erro`, ator auto-sync) e em `inconclusivos` do "Limpar eventos fantasma" |
| Falha ao gravar um evento | — | sem linha própria (uma falha persistente geraria uma linha a cada 10 minutos, e o `rollback` a levaria junto): `logger.exception` com o id e o erro; o id entra em `falhas`, que faz o resumo do ciclo sair `sync_erro` e o `ok` do mês sair falso |

O resumo do ciclo automático (`AuditLog` `sync_ok`/`sync_erro`) traz, **antes** da lista de meses
(que é cortada nos oito primeiros), os totais do ciclo: marcados, com data atualizada, de volta ao
Google, sem confirmação e com falha (FR-042).

O `EventLog` novo não recebe `created_at`: vale o default UTC do modelo, que a tela converte.

## Configuração

| Chave (`app/config.py`) | Default | Variáveis |
|---|---|---|
| `CALENDAR_SUPPRESS_EVENT_WRITES` | `True` quando o banco é `localhost`, `127.0.0.1` ou sqlite; `False` fora | `CALENDAR_SUPPRESS_EVENT_WRITES=true` trava em qualquer ambiente; `CALENDAR_ALLOW_LOCAL_EVENT_WRITES=true` libera no local |

Nenhuma variável nova no painel de produção.
