# Modelo de dados — Feature 298 (Phase 1)

Migration à mão, **aditiva**, com `down_revision = "c9f4a2b71e60"` (head único conferido em 10/09).
Docstring no formato da `c9f4a2b71e60_nfc_moldura_e_recados.py`. Não precisa de ensaio destrutivo.
O cabeçalho do `docs/01` ainda diz que o head é `b7d2e4f1a9c3`; corrigir para o head da 298.

## 1. `form_responses` (existente) — colunas novas

| Coluna | Tipo | Nulo | Significado |
|---|---|---|---|
| `closed_reason` | String(30) | sim | código do motivo (`FORM_CLOSE_REASONS`); preenchido ⇔ encerrado |
| `closed_note` | String(300) | sim | frase livre; obrigatória quando o motivo é `outro` |
| `closed_by_id` | Integer FK `users.id` `ondelete=SET NULL` | sim | quem encerrou |
| `closed_at` | DateTime (UTC, como `created_at`) | sim | quando encerrou; **é a coluna que define "encerrado"** |

Índice parcial novo, declarado também em `__table_args__` do modelo (é o primeiro da tabela):

```text
ix_form_responses_sem_destino ON form_responses (created_at)
  WHERE event_id IS NULL AND closed_at IS NULL      -- postgresql_where e sqlite_where
```

**`client_link_source`**, valor novo: `'evento'`, quando a cliente veio do evento ligado (R5). O
comentário do modelo (`models.py:1946-1950`) passa a listar `'auto_phone' | 'manual' | 'evento' |
None`. Nenhuma migração de dados, porque é String(20) livre.

## 2. `form_response_dismissed_events` (tabela nova)

| Coluna | Tipo | Nulo | Regra |
|---|---|---|---|
| `id` | Integer PK | não | |
| `form_response_id` | FK `form_responses.id` `ondelete=CASCADE` | não | |
| `event_id` | FK `calendar_events.id` `ondelete=CASCADE` | não | |
| `dismissed_by_id` | FK `users.id` `ondelete=SET NULL` | sim | |
| `dismissed_at` | DateTime (`now_sp`) | não | |

Restrição `UNIQUE(form_response_id, event_id)` (`uq_form_response_dismissed_event`). Um par descartado
não volta como sugestão (FR-010). Descartar de novo o mesmo par é `ON CONFLICT DO NOTHING` e responde
200.

**Sem backref** em `CalendarEvent` e `FormResponse`, ou então com `passive_deletes=True`: a exclusão de
evento (`routes.py:337`) e a de formulário (`formularios_ops.py:332`) contam com o CASCADE do banco. Um
backref comum faria o ORM tentar anular FKs NOT NULL.

## 3. Constantes (`app/constants.py`)

```text
CORTE_FORMULARIOS_PADRAO = date(2026, 6, 1)   # default real quando SiteSetting.release_date é nulo
FORM_CLOSE_REASON_DESISTIU = "desistiu"
FORM_CLOSE_REASON_REPETIDO = "repetido"
FORM_CLOSE_REASON_ERRADO   = "preenchido_errado"
FORM_CLOSE_REASON_TESTE    = "teste"
FORM_CLOSE_REASON_OUTRO    = "outro"          # exige closed_note
FORM_CLOSE_REASON_LABELS   = {código: "A cliente desistiu" | "Repetido" | "Preenchido errado" | "Teste" | "Outro"}
FORM_SUGESTAO_JANELA_DIAS  = 3                # FR-010
FORM_COR_VERMELHO_ATE_DIAS = 7                # FR-005
FORM_COR_AMARELO_ATE_DIAS  = 30               # FR-005
FORM_DATA_SUSPEITA_ANOS    = 2                # FR-013
```

Os códigos seguem o molde `VIRTUAL_REFUND_REASON_*` + `_LABELS` (`constants.py:361-368`).

## 4. Estados do formulário (derivados, sem coluna de status)

`corte` = meia-noite de São Paulo de `release_date` (ou `CORTE_FORMULARIOS_PADRAO`), em UTC.

| Partição | Condição | Onde aparece |
|---|---|---|
| `historico` | `created_at < corte` | só na tela Formulários, nunca como tarefa |
| `com_evento` | `created_at >= corte` e `event_id IS NOT NULL` | tela Formulários |
| `encerrados` | `created_at >= corte`, `event_id IS NULL` e `closed_at IS NOT NULL` | tela Formulários |
| `sem_destino` | `created_at >= corte`, `event_id IS NULL` e `closed_at IS NULL` | lista da Home e tela Formulários |

As partições se excluem e somam o total. **Invariante:** `closed_at IS NOT NULL ⇒ event_id IS NULL`.
Encerrar exige formulário sem evento, e ligar a um evento limpa as quatro colunas de encerramento.

### Transições

```text
sem_destino ──ligar (tela, sugestão, criar evento, aba Comercial, automático)──▶ com_evento
sem_destino ──encerrar(motivo)──────────────────────────────────────────────────▶ encerrado
encerrado   ──reabrir───────────────────────────────────────────────────────────▶ sem_destino
encerrado   ──ligar (evento real vence o encerramento)──────────────────────────▶ com_evento
com_evento  ──evento EXCLUÍDO / desvincular──────────────────────────────────────▶ sem_destino
com_evento  ──evento CANCELADO───────────────────────────────────────────────────▶ (continua com_evento)
```

**Efeitos de entrar em `com_evento`**, no núcleo `apply_event_link`, na mesma transação:
1. As colunas de encerramento são limpas.
2. A cliente é levada nos dois sentidos, sem trocar ninguém quando divergem (R5).
3. `marcar_lidas_por_entidade("form_response", id, KIND_FORM_RESPONSE)`.
4. `decisao_humana=True` grava `event_link_locked=True`; o automático não grava.

**Efeitos de entrar em `encerrado`:** grava as quatro colunas e marca os avisos como lidos (item 3).

**Reabrir:** limpa as quatro colunas. Não reemite aviso, porque o `dedupe_key` impede, e a Home é o
lembrete.

### Regras que o sync precisa respeitar
`retry_auto_link_pending` acrescenta `closed_at IS NULL` ao filtro: um formulário encerrado nunca é
religado nem marcado como ambíguo pela automação. A regra de casamento (data exata + telefone) não
muda (FR-011).

## 5. Linha da Home (derivada, não persistida)

Montada por `destino_ops.listar_sem_destino()` a partir dos formulários `sem_destino`.

| Campo | Regra |
|---|---|
| `chave` | `tel:<contact_phone>` ou `id:<id>` sem telefone |
| `formularios[]` | os `sem_destino` da mesma chave, do mais recente para o mais antigo |
| `representante` | o de `created_at` mais recente |
| `cliente` | `{id, nome}` da ficha do representante; senão `contact_name` |
| `data_informada` | `event_date` do representante |
| `dias_ate_a_data` | `event_date − hoje (SP)`, negativo se já passou |
| `dias_desde_chegada` | `hoje (SP) − data de chegada em SP` |
| `grupo` | `a_chegar` se `dias_ate_a_data ≥ 0`; senão `ja_passou` |
| `data_suspeita` | `event_date` antes do dia de chegada, ou mais de 2 anos depois dele |
| `severidade` | `cinza` se suspeita; senão `vermelho` (0–7), `amarelo` (8–30 ou já passou), `cinza` (>30) |
| `repetido` | `len(formularios) > 1` |
| `outro_com_evento` | existe formulário da mesma chave, desde o corte, com evento |
| `sugestao` | evento candidato mais próximo a até 3 dias (R10), ou nulo |

Ordem: `a_chegar` por `data_informada` crescente; `ja_passou` por `data_informada` decrescente.
Com a mesma data informada, vem primeiro o que chegou por último (`created_at` decrescente).

**Sugestão com mais de um candidato**: vale o de menor `|dias_diferenca|`; empatados, o evento mais
cedo (`start_at` crescente).

## 6. Histórico de ações (sem tabela nova)

Encerrar e reabrir gravam uma linha em `audit_logs` pelo helper existente `audit()`
(`app/utils.py:46`). Ele não comita, então a linha entra na mesma transação da ação. O ator vem de
`current_user`.

| Ação | `entity_type` | `entity_id` | `entity_name` | `action` | `detail` |
|---|---|---|---|---|---|
| Encerrar | `form_response` | id | `contact_name` | `formulario.encerrado` | `motivo=<código>; frase=<texto>` |
| Reabrir | `form_response` | id | `contact_name` | `formulario.reaberto` | `motivo_anterior=<código>; encerrado_em=<ISO>` |
| Repetidos | `form_response` | id de cada encerrado | `contact_name` | `formulario.encerrado` | `motivo=repetido; mantido=<id>` |

O formulário guarda só o estado atual. Ao reabrir, as quatro colunas voltam a nulo, e o encerramento
anterior fica só nessa linha.

## 7. Divergência de cliente

Ao ligar, se o formulário e o evento têm clientes diferentes, o núcleo não muda nada e devolve
`divergencia_cliente`. A ação "usar a cliente do evento neste formulário" grava
`client_id = <cliente do evento>` e `client_link_source = 'evento'` no formulário. O evento nunca é
alterado por essa ação.

**Divergem** = a cliente do formulário não é nenhuma das clientes do evento (`EventClient`), e o evento
tem ao menos uma cliente.

## 8. Valores derivados servidos pela API

| Campo | Onde | Regra |
|---|---|---|
| `destino` | resumo do formulário | `destino_de(response, corte)` no núcleo: `sem_destino`, `com_evento`, `encerrados` ou `historico`, as mesmas grafias das partições (§4) |
| `tipo_rotulo` | linha da Home e resumo | "Festa" (`comum`) ou "Corporativo" |
| `corte` | contagens | AAAA-MM-DD, dia em SP |
| `motivos_encerramento` | detalhe e bloco do dashboard | `[{codigo, rotulo}]` a partir de `FORM_CLOSE_REASON_LABELS`, uma fonte só |
| `pode_encerrar` | flags do detalhe | `sem_destino`: tem de ter chegado desde o corte, sem evento e sem encerramento |
| `pode_reabrir` | flags do detalhe | `encerrados` |

## 9. Correções únicas (CLI, depois do deploy)

| Comando | Seleção | Efeito |
|---|---|---|
| `formularios-avisos-resolvidos` | `Notification` com `kind=KIND_FORM_RESPONSE`, `read_at IS NULL` e formulário com evento ou encerrado | `read_at = now_sp()` num UPDATE em lote (`entity_id IN (subquery)`) |
| `formularios-cliente-do-evento` | formulário desde o corte, com evento, `client_id IS NULL`, e evento com cliente | `client_id` = escolha do núcleo (EventClient com o telefone do formulário, senão `event.client_id`), com `client_link_source='evento'` |

Os dois só contam sem `--execute`.
