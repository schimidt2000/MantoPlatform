# Modelo de dados — Feature 306

**Uma migration, aditiva.** São três `create_table`. Não entra coluna em tabela existente, nem backfill, nem script no Shell do Render.

Cabeça conferida no HEAD `657adb8`, onde `app/` e `migrations/` são iguais a `d855d1a`, e reconferida em `6356b80` (a 307 não trouxe migration):
- `a7c3e91f4d28` (`a7c3e91f4d28_evento_sumiu_do_google.py`) é a única cabeça;
- nenhum arquivo versionado de `migrations/versions/` tem `down_revision = "a7c3e91f4d28"`;
- `alembic_version` do `manto_local` = `a7c3e91f4d28`;
- `app/models.py`, `app/constants.py` e `migrations/` não mudaram desde `f6ad283`.

**Nomes.** A §6 é a **tabela única de nomes** da 306: constantes, códigos de recusa, kinds do sino, listas da passagem e as funções que a 1c, a 1e, a 2a, a 2b, a 3b, a 6a e a 6b reusam. O plan e a research apontam para ela. Nome que não está nela não existe (§6.5).

**Convenções.** Todas seguem o schema de hoje.

- **Dinheiro**: `Numeric(12, 2)`, no molde de `commission_payments.amount` (`models.py:973`). O cachê de referência é copiado de `event_roles.cache_value`, que é `Numeric(10,2)` (`:578`), e cabe.
- **Taxa**: `Numeric(6, 3)`, em % (2.500 = 2,5%). A origem é `Float`: `calendar_events.commission_rate` (`:279`), `site_settings.default_commission_rate` e `educamanto_commission_rate` (`:865`, `:872`). A conversão é `Decimal(str(x))`, e a comparação usa `_mesma_taxa` (`event_ops.py:1105-1112`).
- **Hora**:
  - `created_at`/`updated_at` usam o horário de parede de São Paulo, sem fuso (`now_sp`, `constants.py:291`), como `cancelled_at` (`models.py:297`) e `Notification.created_at` (`:694`);
  - o `EventLog` do ato usa o default UTC do modelo (`:631`).
- **Sem `CheckConstraint`**: o schema não usa nenhuma. O domínio dos textos mora em `app/constants.py` (§6.1).
- **Relação no filho**: segue o molde de `Event3DDismissal` (`models.py:2376-2403`), com FK `ondelete="CASCADE"`, unique e `backref(..., uselist=False, cascade="all, delete-orphan")`. `CalendarEvent` e `_clear_event_side_tables` não são tocados.
- **`foreign_keys=` em toda `relationship`**:
  - `event_cancellations` tem duas FKs para `calendar_events` e três para `users`;
  - `event_cancellation_elenco` tem uma terceira para `calendar_events`.

  Sem isso, `AmbiguousForeignKeysError` no `configure_mappers` derruba o `create_app()` e o `startCommand`.
- **Nomes de UNIQUE e de índice** ficam declarados no `__table_args__` do modelo **e** na migration (lição da 303, `models.py:244-250`). Assim um autogenerate futuro não propõe drop.
- **`selectinload(CalendarEvent.cancelamento)` nunca vira constante de módulo**: o backref só existe depois de `configure_mappers` (lição da 302). Monte o `selectinload` dentro da função (`resumos_cancelados`).

---

## 1. `event_cancellations` (`EventCancellation`) — nova

Uma linha por evento cancelado por esta entrega ou depois dela. Evento cancelado **sem** linha é `legado` (FR-003).

| Coluna | Tipo | Nulo | Default | Regra |
|---|---|---|---|---|
| `id` | Integer PK | — | — | |
| `event_id` | Integer FK `calendar_events.id` **ON DELETE CASCADE** | não | — | UNIQUE `uq_event_cancellations_event_id` (é o índice). Some com o evento |
| `regime` | String(12) | não | — | `REGIME_VENDA` \| `REGIME_SATELITE` \| `REGIME_DIA` \| `REGIME_VIRTUAL` (§6.1). **Imutável**. `legado` nunca é gravado |
| `refund_mode` | String(8) | sim | — | O modo escolhido no ato: `tudo`/`parte`/`nada` no `venda`, `parte`/`nada` no `dia`, `NULL` em `satelite` e `virtual`. **Imutável**. O modo corrente sai de pago × devolvido |
| `sale_value` | Numeric(12,2) | sim | — | `venda`: venda congelada (0,00 se o evento não tinha). Recongela pela correção da venda (FR-048 (c)). `NULL` nos outros regimes |
| `commission_full` | Numeric(12,2) | sim | — | `venda`: comissão cheia (FR-027) por `comissao_cheia_do_evento` (§6.4), com a taxa, o BV e o custo congelados. Vale 0,00 quando `_beneficiario_comissionado` recusa: sem beneficiário, `receives_commission` falso, cortesia/permuta. Recongela pelas correções da FR-048 (c), (f) e (g). `NULL` nos outros regimes (a Loja Virtual é `virtual`) |
| `commission_rate` | Numeric(6,3) | sim | — | `venda`: taxa usada no ato. É a do evento; senão a padrão do dia do ato; no EducaManto, a do evento ou a de Configurações (FR-029). Só a correção da taxa a troca (FR-050) |
| `commission_cost` | Numeric(12,2) | sim | — | `venda` EducaManto com responsável: a **mesma base de custo da comissão** no ato (`comissoes_ops.py:786`): `_group_cost(event)` no principal, `_event_cost(event)` no EducaManto que não é principal (`:709-730`). É lida depois de T1, com `satellites` expirado (§8.12), e antes de `cancelled_at`: entram os dias que o ato alcança e ficam fora os cortados antes (o `_group_cost` passa a somar só dias vivos na H5). `NULL` na comissão comum. **Imutável**: é o "com os cachês, como no ato" da FR-049, porque o custo é lido ao vivo e o Casting pode esvaziar a escala |
| `commission_seller_id` | Integer FK `users.id` (**sem** `ondelete`) | sim | — | Beneficiário congelado **quando comissiona** (`receives_commission`, `models.py:77`); senão `NULL`. Muda na troca de vendedor (FR-051). Bloqueia `delete_user` (FR-073) |
| `seller_id` | Integer FK `users.id` (**sem** `ondelete`) | sim | — | `venda`: vendedor do evento no ato, usado no recorte comercial (FR-044, FR-046). Muda na troca. Bloqueia `delete_user` |
| `with_invoice` | Boolean | não | `false` | `venda`: era com nota. **Imutável**: a "nota solicitada" corrigida depois (FR-048 (d)) muda o evento, não o congelado (FR-049) |
| `retained_tax` | Numeric(12,2) | sim | — | `venda` com nota: imposto informado, ≥ 0, obrigatório no ato. `NULL` = não se aplica. Só o `PATCH …/devolucao` o regrava |
| `group_leader_id` | Integer FK `calendar_events.id` **ON DELETE SET NULL** | sim | — | `satelite`/`dia`: o principal ao fim do ato. No antigo 1º dia que passou a venda, é o **novo** principal |
| `sale_handed_over` | Boolean | não | `false` | `true` só no antigo 1º dia que passou a venda (FR-058). A tela lê `venda_passou_para = group_leader_id` quando ele é `true`. É coluna nova (§11): o `EventLog` não se consulta, e um `dia` comum também tem `group_leader_id` |
| `sale_value_before` / `sale_value_after` | Numeric(12,2) | sim | — | Só no `dia`: a venda do principal antes e depois do corte |
| `sale_value_gross_before` / `sale_value_gross_after` | Numeric(12,2) | sim | — | Só no `dia`: o valor cheio do principal antes e depois, na mesma proporção (FR-056). `NULL` se o principal não tinha cheio |
| `created_at` | DateTime | não | `now_sp` | O ato |
| `updated_at` | DateTime | não | `now_sp`, onupdate `now_sp` | Último recongelamento ou alteração |
| `updated_by_id` | Integer FK `users.id` **ON DELETE SET NULL** | sim | — | Quem recongelou por último (FR-073) |

Índices:
- `uq_event_cancellations_event_id`;
- `ix_event_cancellations_group_leader_id`, para ler os dias de um ato a partir do principal.

**O que não fica gravado**: pago e devolvido, que são lidos ao vivo (FR-002). O motivo, quem cancelou e quando continuam em `calendar_events.cancellation_reason`, `cancelled_by_id` e `cancelled_at`.

## 2. `event_cancellation_bvs` (`EventCancellationBv`) — nova

Uma linha por acréscimo BV do evento no ato (`venda`). Ganha linha nova também quando o Superadmin acrescenta um BV no cancelado (decisão (d) do plan).

| Coluna | Tipo | Nulo | Default | Regra |
|---|---|---|---|---|
| `id` | Integer PK | — | — | |
| `cancellation_id` | Integer FK `event_cancellations.id` **ON DELETE CASCADE** | não | — | Índice `ix_event_cancellation_bvs_cancellation_id` |
| `acrescimo_id` | Integer FK `event_acrescimos.id` **ON DELETE SET NULL** | sim | — | UNIQUE `uq_event_cancellation_bvs_acrescimo_id`: os NULL são livres, e um acréscimo tem no máximo uma linha. **Linha com `acrescimo_id` NULL é órfã, e nenhum leitor a soma** |
| `recipient` | String(200) | sim | — | Cópia de `bv_recipient` (`models.py:1863`). O diálogo completa quando falta (FR-010). Num BV não pago, regravado junto com o acréscimo (FR-049, linha (g)) |
| `pix` | String(140) | sim | — | Cópia de `bv_pix` (`:1864`), com a mesma regra |
| `original_amount` | Numeric(12,2) | não | — | O **BV cheio** = `amount_brl` no ato (> 0). Regravado só no BV **não pago** corrigido pelo Superadmin |
| `paid_at_cancellation` | Boolean | não | `false` | `bv_payment_status ∈ {pago, no_banco}` no ato, lido sob a trava do evento. **Imutável** |
| `paid_amount` | Numeric(12,2) | sim | — | Decisão (a). É o valor que conta enquanto o BV está pago ou no banco: `amount_brl` no ato, se pago; ou o `bv_da_planilha` do instante do "pago". Volta a `NULL` no desfazer. `reaplicar_cancelado` **nunca** o toca. Coluna nova (§11) |

**Sem coluna em `event_acrescimos`** (`models.py:1841-1875`). `value`, `amount_brl` e `bv_payment_status` continuam a verdade do acréscimo. O proporcional nunca é gravado (FR-039).

## 3. `event_cancellation_elenco` (`EventCancellationElenco`) — nova

Uma linha por **escalação** (vaga × dia): cada `EventRole` com talento nos dias que o ato alcança. Ficam fora a vaga com `invite_status == "rejected"` (`models.py:590`) e a vaga de presença (`casting_ops.e_vaga_de_presenca`, `casting_ops.py:39-58`) (FR-070).

**Escalação, não artista** (§11): um artista em 2 dias, ou em 2 vagas do mesmo dia, tem 2 linhas, 2 campos de multa no diálogo e, se lançadas, 2 gastos. O e-mail do ato continua um por talento (FR-066). A FR-070 e a FR-071 dizem "uma linha por artista"; a Living Spec troca por "uma linha por escalação".

**Dono da lista**:
- no `venda` é a linha do principal, com todos os dias do "todos" (`day_event_id` diz o dia);
- no `dia`, a linha daquele dia (no antigo 1º dia que passou a venda, também);
- `satelite` e `virtual` não têm elenco próprio.

| Coluna | Tipo | Nulo | Default | Regra |
|---|---|---|---|---|
| `id` | Integer PK | — | — | É o `elenco_id` do contrato |
| `cancellation_id` | Integer FK `event_cancellations.id` **ON DELETE CASCADE** | não | — | Índice `ix_event_cancellation_elenco_cancellation_id` |
| `talent_id` | Integer FK `talents.id` (**sem** `ondelete`) | não | — | Artista com multa não some. Índice `ix_event_cancellation_elenco_talent_id`. O único apagamento de talento hoje é o do pendente (`app/talents/talent_ops.py:326-338`) |
| `role_id` | Integer FK `event_roles.id` **ON DELETE SET NULL** | sim | — | A vaga do ato. Índice `ix_event_cancellation_elenco_role_id` (o sync apaga vagas, e o SET NULL precisa do índice). "Na vaga" = `role_id` não nulo **e** `event_roles.talent_id == talent_id` |
| `day_event_id` | Integer FK `calendar_events.id` **ON DELETE CASCADE** | **não** | — | O dia. Índice `ix_event_cancellation_elenco_day_event_id`. **CASCADE e NOT NULL**: dia cancelado não se exclui (FR-021; 409 em `_delete_event_flow` e `_apagar_vazio`), então o CASCADE só age se essa regra for furada, e aí a linha sai com o dia em vez de ficar sem dia |
| `character_name` | String(120) | não | — | Cópia de `event_roles.character_name` (`models.py:574`) |
| `cache_reference` | Numeric(12,2) | sim | — | Cópia de `cache_value`, **só referência**: nunca somada em custo, DRE ou multa |
| `special_expense_id` | Integer FK `special_expenses.id` **ON DELETE SET NULL** | sim | — | A multa lançada. UNIQUE `uq_event_cancellation_elenco_special_expense_id` (um gasto é de uma linha). Uma multa por linha, ou seja, por escalação. Gasto excluído em Gastos Extras faz a linha voltar a "não lançada". Coluna nova (§11) |

## 4. Declaração no ORM (`app/models.py`, depois de `Event3DDismissal`)

```python
class EventCancellation(db.Model):
    __tablename__ = "event_cancellations"
    __table_args__ = (
        db.UniqueConstraint("event_id", name="uq_event_cancellations_event_id"),
        db.Index("ix_event_cancellations_group_leader_id", "group_leader_id"),
    )
    event_id = db.Column(db.Integer, db.ForeignKey("calendar_events.id", ondelete="CASCADE"), nullable=False)
    group_leader_id = db.Column(db.Integer, db.ForeignKey("calendar_events.id", ondelete="SET NULL"))
    # … colunas da §1 …
    event = db.relationship("CalendarEvent", foreign_keys=[event_id], lazy=True,
        backref=db.backref("cancelamento", uselist=False, cascade="all, delete-orphan"))
    group_leader = db.relationship("CalendarEvent", foreign_keys=[group_leader_id], lazy=True)  # sem backref
    seller = db.relationship("User", foreign_keys=[seller_id], lazy=True)
    commission_seller = db.relationship("User", foreign_keys=[commission_seller_id], lazy=True)
    updated_by = db.relationship("User", foreign_keys=[updated_by_id], lazy=True)

class EventCancellationBv(db.Model):          # backref("bvs", cascade="all, delete-orphan", order_by id)
    acrescimo = db.relationship("EventAcrescimo", foreign_keys=[acrescimo_id], lazy=True)  # sem backref

class EventCancellationElenco(db.Model):      # backref("elenco", cascade="all, delete-orphan", order_by id)
    talent / role / day_event (foreign_keys=[day_event_id]) / special_expense — sem backref
```

O que muda em `models.py` sem schema (FR-074 e categoria):
- `SpecialExpense.CATEGORY_MULTA_CANCELAMENTO = "Multa de cancelamento"` (§6.3), no molde de `CATEGORY_DEVOLUCAO` (`:1073`), entra em `CATEGORIES` (`:1070-1072`). São 21 caracteres e cabem em `category String(30)` (`:1079`). Sem isso, a primeira edição em Gastos Extras a remapeia para "Outros" (`gastos_ops.py:240-242`). Nasce na **Fundação**, com os modelos: o cenário 21 semeia a multa por ORM com ela antes de a H6 existir.
- Comentários e docstrings:
  - o tipo de destinatário (`:1091`) passa a incluir `"cliente"`;
  - a devolução (`:1066-1069`);
  - `approved_with_edits` (`:1114-1117`);
  - `is_cancelled` (`:399-407`);
  - `CommissionPayment` (`:946-956`), com estados, ajuste ligado à paga e motivo no prefixo da nota;
  - `is_devolucao_cliente` (`:1159-1162`), que reconhece pelo tipo e não tem uso: a docstring passa a apontar para `cancel_ops.filtro_devolucao`. Não usar.

## 5. Regimes

| Regime | Quem recebe a linha | `refund_mode` | Congelado | `bvs` | `elenco` | `group_leader_id` | Entra em DRE, Comercial e `n_cancelados` |
|---|---|---|---|---|---|---|---|
| `venda` | Evento avulso; o principal no "Cancelar todos os dias" | `tudo`/`parte`/`nada` | `sale_value`, `commission_full/_rate/(_cost)`, `commission_seller_id`, `seller_id`, `with_invoice`, `retained_tax` | Uma por BV no ato | Todas as escalações dos dias alcançados | `NULL` | Sim: retido, comissão do retido, BV que conta e imposto, no mês de `cancelled_at`. Conta 1 |
| `satelite` | Cada outro dia vivo do "todos" | `NULL` | Nada | — | Fica na linha do principal | O principal | Zero. Não conta |
| `dia` | Dia cortado sozinho; antigo 1º dia (`sale_handed_over`) | `parte`/`nada` | Venda e cheio do principal antes e depois | — | As escalações do dia | O principal (ou o novo) | Zero. Não conta. A devolução do dia sai dos gastos (FR-042) |
| `virtual` | Venda da Loja Virtual (`is_loja_virtual`) | `NULL` | Nada (estorno próprio) | — | — | `NULL` | Fora do recorte (tipo VIRTUAL) |
| `legado` (sem linha) | Cancelado antes do deploy | — | — | — | — | — | Retido = pago − devolvido, comissão 0, imposto 0, BV só o pago |

**Pago e devolvido de um ato**: somam **os ids do grupo por consulta**, os mesmos que `cancel_ops.travar_grupo` trava em T1 (`cancel_ops.ids_do_grupo`, §6.4: o principal e os dias com `group_leader_id` = principal), com os dias cancelados, porque é dinheiro (FR-004). **Nunca** pela coleção: nem `leader.satellites`, nem `group_ops.group_events` (`group_ops.py:64-75`), que a lê. Fora do ato (resumo em lote, DRE), a mesma consulta roda sem `FOR UPDATE`.
- **Pago**: Σ `coalesce(event_payments.amount, 0)`, no molde de `cancel_ops.total_recebido` (`cancel_ops.py:65-72`).
- **Devolvido**: `filtro_devolucao` = `category == CATEGORY_DEVOLUCAO` ∧ `event_id ∈ grupo` ∧ `status == "aprovado"`, **nunca** por `disbursement_type`.

**Dia cortado sem retido próprio**: o que a Manto retém do dia já está na venda nova do principal vivo. Se o principal for cancelado inteiro depois, a devolução do `dia` passa a contar no `devolvido` dessa venda pela mesma soma do grupo, e o "Alterar devolução" do dia refaz o retido e a comissão do principal (§7.2). Isso **deriva da D28** ("Acompanham"), não do clarify de 15/10, que vale para o grupo vivo; é o 6º ponto da Living Spec, com variante no cenário 39 (§11). O `dia` continua `dia`.

**Gastos do detalhe** (`_serialize_gastos`, `agenda_read.py:507`, chamado em `:1110` com os ids do grupo):
- no principal **vivo**, só os dias vivos (`group_ops.dias_vivos`): a devolução e a multa de um dia cortado não viram gasto do principal;
- no **cancelado**, a lista traz o próprio dia (`satelite`, `dia`, `legado`, `virtual`);
- no `venda`, os dias do ato: o principal e os `satelite` que apontam para ele. É onde aparecem a devolução e as multas.

## 6. Tabela única de nomes

Fonte única para o plan, a research, os contratos e os itens seguintes. Mudou aqui, muda lá.

### 6.1 Constantes em `app/constants.py`

Perto de `NOTA_CICLO_VALOR_TARDIO` (`:466`) e de `SITUACAO_*` (`:573-575`, fim do arquivo):

```python
# Regimes do cancelamento (event_cancellations.regime). `legado` é derivado (sem linha): nunca gravado.
REGIME_VENDA, REGIME_SATELITE, REGIME_DIA, REGIME_VIRTUAL = "venda", "satelite", "dia", "virtual"
REGIME_LEGADO = "legado"
# Modo da devolução escolhido no ato (refund_mode). O modo corrente sai de pago × devolvido.
MODO_TUDO, MODO_PARTE, MODO_NADA = "tudo", "parte", "nada"
# Alcance num grupo (FR-055) e o que o ponto da 2a recebe (FR-062).
ALCANCE_TODOS, ALCANCE_SO_ESTE_DIA = "todos", "so_este_dia"
# Dia do repasse. Os literais 5 de financeiro_read.py:720 e financeiro/routes.py:1072 ganham comentário.
DIA_DO_REPASSE = 5
# Prefixos da nota da linha de comissão (FR-033): uma constante por motivo, e o dict -> código da 1e.
MOTIVO_AJUSTE_RETIDO = "Cancelamento: comissão do retido"
MOTIVO_AJUSTE_TROCA_DEVOLVE = "Cancelamento: vendedor trocado — devolve o já recebido"
MOTIVO_AJUSTE_TROCA_RETIDO = "Cancelamento: vendedor trocado — comissão do retido"
MOTIVO_AJUSTE_TAXA = "Cancelamento: taxa corrigida"
MOTIVO_AJUSTE_CORRECAO_VENDA = "Cancelamento: correção da venda"
MOTIVO_AJUSTE_CORTE_DE_DIA = "Corte de dia: venda diminuiu"
MOTIVO_AJUSTE_EXCLUSAO = "Exclusão do evento"
MOTIVO_AJUSTE_TROCA_DE_TIPO = "Troca de tipo"   # só declarado; a 2b usa
MOTIVOS_AJUSTE_COMISSAO = {
    MOTIVO_AJUSTE_RETIDO: "cancelamento",
    MOTIVO_AJUSTE_TROCA_DEVOLVE: "troca_de_vendedor",
    MOTIVO_AJUSTE_TROCA_RETIDO: "troca_de_vendedor",
    MOTIVO_AJUSTE_TAXA: "correcao",
    MOTIVO_AJUSTE_CORRECAO_VENDA: "correcao",
    MOTIVO_AJUSTE_CORTE_DE_DIA: "corte_de_dia",
    MOTIVO_AJUSTE_EXCLUSAO: "exclusao",
    MOTIVO_AJUSTE_TROCA_DE_TIPO: "troca_de_tipo",
}
# P-29: marca a comissão própria do novo principal na passagem; molde de _com_marca_do_ciclo
# (comissoes_ops.py:842-848). _comissao_existente e a reconciliação ignoram a linha marcada.
NOTA_COMISSAO_PROPRIA_DO_DIA = "Comissão própria do dia"
```

### 6.2 Códigos de recusa (P18)

Toda recusa nova da 306 leva `codigo` no envelope de `json_error`. São 18 códigos 409, com o `valor_mudou`. Cada código é uma constante em `app/constants.py`, logo depois de `SITUACAO_*`, e a tela os lê por **uma** união em TypeScript.

```python
CODIGO_EVENTO_CANCELADO = "cancelado"          # a regra única (FR-047)
CODIGO_JA_CANCELADO = "ja_cancelado"
CODIGO_ENSAIO = "ensaio"
CODIGO_GRUPO_MUDOU = "grupo_mudou"
CODIGO_SEM_OUTRO_DIA_VIVO = "sem_outro_dia_vivo"
CODIGO_CACHE_PAGO = "cache_pago"
CODIGO_DEVOLUCAO_PENDENTE = "devolucao_pendente"
CODIGO_MAX_DEVOLUCAO_MUDOU = "max_devolucao_mudou"
CODIGO_TENTE_DE_NOVO = "tente_de_novo"
CODIGO_NAO_CANCELADO = "nao_cancelado"
CODIGO_REGIME_SEM_RETIDO = "regime_sem_retido"
CODIGO_ABAIXO_DO_PISO = "abaixo_do_piso"
CODIGO_ACIMA_DO_TETO = "acima_do_teto"
CODIGO_PAGO_ABAIXO_DO_DEVOLVIDO = "pago_abaixo_do_devolvido"
CODIGO_BV_NAO_ESTA_A_PAGAR = "bv_nao_esta_a_pagar"
CODIGO_VALOR_MUDOU = "valor_mudou"
CODIGO_DEVOLUCAO_TRAVADA = "devolucao_travada"
CODIGO_ESTADO_MUDOU = "estado_mudou"
CODIGOS_RECUSA_DO_CANCELAMENTO = frozenset({...})  # todos acima; o verify confere contra a união TS
```

| Código | Onde nasce (contracts/api.md) | Extras | O que a tela faz |
|---|---|---|---|
| `cancelado` | Portas da regra única (§6–§14) | — | Mostra a frase e recarrega o evento |
| `ja_cancelado` | §1 (também no UNIQUE), §2 (prévia) | — | Invalida o evento e fecha o diálogo |
| `ensaio` | §1 | — | Mostra a frase (o ENSAIO tem botão próprio) |
| `grupo_mudou` | §1; §9 (POST depois de gravar o arquivo) | — | Refaz o impacto |
| `sem_outro_dia_vivo` | §1 | — | Trata como `grupo_mudou` |
| `cache_pago` | §1 | `dias` | Explica e não oferece cancelar |
| `devolucao_pendente` | §1 | `dias` (num grupo, o dia da pendente) | Mostra a frase |
| `max_devolucao_mudou` | §1 | `max_devolucao` | Refaz o "Tudo" com o máximo novo |
| `tente_de_novo` | Todo endpoint da 306 (deadlock `40P01`) | — | Mostra a frase; quem clicou repete |
| `nao_cancelado` | §3, §4 | — | Recarrega o evento |
| `regime_sem_retido` | §3 | — | Mostra a frase |
| `abaixo_do_piso` | §3 | `piso` | Erro no campo |
| `acima_do_teto` | §3 (só `dia`) | `teto` | Erro no campo |
| `pago_abaixo_do_devolvido` | §9 | `pago`, `devolvido` | Mostra a frase |
| `bv_nao_esta_a_pagar` | §17 | — | Recarrega a Planilha |
| `valor_mudou` | §17 (BV e devolução) | — | Recarrega a Planilha |
| `devolucao_travada` | §16 | `fields`, `event_id` | Frase com o link do evento |
| `estado_mudou` | §6 | — | Recarrega o detalhe |

- **`valor_mudou`** é o único que entra num 409 que já existe: o do BV da 305 (`financeiro_write.py:170-183`), que hoje sai sem `codigo`. O extra é aditivo; a mensagem não muda.
- **Homônimos, de outros fluxos** (nunca comparar entre si): `cancelado` também é `sumico_ops.CODIGO_CANCELADO` (`:641`, devolver ao Google), `MOTIVO_FORA_CANCELADO` (`constants.py:457`) e `SITUACAO_CANCELADO` (`:573`); `ensaio` também é `MOTIVO_FORA_ENSAIO` (`:458`).
- **Fora da lista**: o `sumiu_do_google` da exclusão (`agenda_write.py:569`), que é da 303 e não muda.
- **TypeScript**: `export type CodigoRecusaCancelamento = …` em `lib/eventOps.ts`, ao lado de `CodigoDevolverAoGoogle` (`:190-199`). `lib/gastos.ts` e `lib/financeiro.ts` importam dela. O verify confere que o conjunto Python e a união TS têm os mesmos membros.

### 6.3 Constantes em modelos e em outros módulos

| Nome | Onde | Valor e regra |
|---|---|---|
| `SpecialExpense.CATEGORY_MULTA_CANCELAMENTO` | `models.py`, molde de `CATEGORY_DEVOLUCAO` (`:1073`) | `"Multa de cancelamento"`; entra em `CATEGORIES` (§4). Nasce na Fundação. A 6b a põe na lista dela |
| `sumico_ops.MOTIVO_CANCELADO` | `sumico_ops.py`, ao lado de `MOTIVO_REAPARECEU`/`MOTIVO_DEVOLVIDO` | `"cancelado"`; entra em `_MOTIVOS_DE_DESMARCAR` (`:60-62`). Hoje estoura `ValueError` (`:279-280`) |
| `notificacoes_ops.KIND_EVENTO_CANCELADO` | catálogo (`:54-71`) | `"evento.cancelado"` → `(RoleName.ENSAIO,)`. Um por pessoa **por ato**, só quando havia ensaio. `dedupe_key = evento.cancelado:<id do evento da URL>` |
| `notificacoes_ops.KIND_EVENTO_CANCELADO_ESCALA` | idem | `"evento.cancelado_escala"` → `(RoleName.CASTING,)`, sem o Superadmin (FR-068). Um por dia com escalados. `dedupe_key = evento.cancelado_escala:<id do evento da URL>:<dia_id>` |
| `group_ops.CAMPOS_DA_PASSAGEM` | `group_ops.py`, ao lado de `passar_venda` | Colunas de `calendar_events` que vão do antigo 1º dia ao novo: os 14 de `SATELLITE_FIELDS_CLEARED` (`group_ops.py:47-51`, que já incluem `orcamento_history_id`), `invoice_due_date` e `group_name`. A 2b acrescenta `educamanto_comissao_vendedor`; a 6a, as colunas de canal |
| `group_ops.TABELAS_DA_PASSAGEM` | idem | Filhas cujo `event_id` passa ao novo: comprovantes (`EventPayment`), parcelas (`EventInstallment`), notas (`EventInvoice`), contratos (`EventContract`), reembolsos (`EventReimbursement`), acréscimos (`EventAcrescimo`, com o estado do BV), **todas** as linhas de comissão (`CommissionPayment`, travadas por T4 antes do `UPDATE`), a devolução aprovada ligada ao antigo (por `filtro_devolucao`), o formulário de pré-contrato e as clientes que faltam no novo (`EventClient`) |

**Sinos, por que a chave é do ato (P2).** A `UNIQUE(user_id, dedupe_key)` é permanente (`models.py:674`), e `emitir` engole o duplicado no savepoint. Com `<principal_id>`, o 2º ato do mesmo grupo (um dia cortado com ensaio e depois "Cancelar todos" com ensaio, ou a passagem e depois o novo principal cancelado) sumiria calado. Cada evento só cancela uma vez (UNIQUE de `event_cancellations`), então o id do evento da URL identifica o ato. No `evento.cancelado_escala`, a mesma chave do ato ganha o dia, porque a FR-068 pede um sino por dia: no "todos", os dias dividem o id da URL. As duas chaves ficam abaixo dos 120 caracteres (`dedupe_key[:120]`). O verify cobre isso com uma variante do 44: corte com ensaio e depois "todos" com ensaio dão 2 sinos por pessoa da equipe de Ensaio.

### 6.4 Funções, listas e flags que outros itens reusam

| Nome | O que é | Quem reusa |
|---|---|---|
| `cancel_ops.ao_cancelar(event, *, alcance, novo_principal)` | Ponto de extensão da 2a, sem efeito nesta entrega. Roda **em todo cancelamento**, na transação: avulso e cada dia do "todos" → `(ALCANCE_TODOS, None)`; corte de um dia que não é o principal → `(ALCANCE_SO_ESTE_DIA, None)`; antigo 1º dia, **depois** de `passar_venda` → `(ALCANCE_SO_ESTE_DIA, novo_principal)`. Os dois primeiros casos são decisão do plan (FR-062, §11) | 2a |
| `cancel_ops.pode_editar_venda_do_cancelado(user)` | A regra única: papel **real** SUPERADMIN, a régua de `_can_delete()` (`agenda_write.py:111-115`) | 1c |
| `cancel_ops.EventoCanceladoError` | Irmã de `EventoMarcadoError`; a exclusão a levanta | — |
| `cancel_ops.CancelValidationError(message, *, fields=None, field=None, status=400, codigo=None, **extras)` | Recusa do núcleo. `fields` leva todos os campos recusados de uma vez; `field=` é atalho para `{field: message}`; `extras` nunca leva `fields`. A view a traduz numa linha só: `json_error(exc.message, exc.status, fields=exc.fields, codigo=exc.codigo, **exc.extras)` | — |
| `cancel_ops.recusar_se_cancelado(event, user)` | A regra única das portas (a)–(h): `travar_evento`, relê `cancelled_at` e levanta `CancelValidationError(status=409, codigo=CODIGO_EVENTO_CANCELADO)` para quem não é Superadmin real | 1c |
| `cancel_ops.gravar_comprovante_no_grupo(event, acao, …)` | O núcleo das três portas de comprovante: T1, releitura, recusa, gravação, `reaplicar_por_dinheiro`; a view só traduz e remove o arquivo novo | — |
| `cancel_ops.marcar_status_da_devolucao(exp_id, status, *, valor_esperado, actor_name)` | A função única da devolução nas duas Planilhas, no molde de `marcar_status_do_bv` (o Jinja passa `valor_esperado=None`) | — |
| `cancel_ops.limites_da_devolucao(event)` | Piso e teto do "Alterar devolução" por regime (§7.2), expostos em `ResumoCancelado.limites_devolucao` só com `can_edit_venda_cancelado` | — |
| `cancel_ops.travar_grupo(event)` / `cancel_ops.ids_do_grupo(principal_ids)` | T1, e a consulta de ids que ela trava (fora do ato, a mesma consulta sem trava) | — |
| `cancel_ops.cache_pago_do_evento(event)` | A régua do cachê pago (FR-063), com T6 no ato | 2a |
| `cancel_ops.filtro_devolucao()`, `devolucoes_por_evento(ids)` | A devolução por categoria, evento e aprovação; o lote | — |
| `cancel_ops.ResumoCancelado`, `resumo_cancelado`, `resumos_cancelados(ids)`, `serializar_resumo_cancelado` | O resumo único (FR-005), em lote | 1c |
| `cancel_ops.cancelados_do_periodo`, `totais_cancelamentos`, `retido_por_vendedor` | A fonte única do período (FR-044) | 1c |
| `cancel_ops.bv_do_retido`, `bv_da_planilha`, `marcar_status_do_bv` | O BV do retido e a função única das duas Planilhas | — |
| `cancel_ops.previa_cancelamento`, `alterar_devolucao`, `reaplicar_cancelado`, `reaplicar_por_dinheiro`, `lancar_multas_do_cancelado` | O ato e as correções | 1e (`reaplicar_cancelado` na data de venda) |
| `comissoes_ops._base_da_comissao(event, settings, *, venda=None, taxa=None, bv_total=None, custo=None)` | **Camada 1 (P1)**: o corpo de hoje de `_event_commission` (`comissoes_ops.py:766-796`), intocado, com sobreposições opcionais; sem elas, o número é o de hoje. A casca `_event_commission(event, settings)` só a chama, e os **8** consumidores não mudam número (`financeiro/routes.py:231`, `:434`, `:1463`; `financeiro_read.py:402`; `vendas_ops.py:290`, `:339`; `comissoes_ops.py:403`, `:937`), conferido pelo cenário 1 | — |
| `comissoes_ops._beneficiario_comissionado(event, settings)` | Extraído de `should_have` (`:926-936`), sem olhar cancelamento: Loja Virtual, beneficiário `None`, `receives_commission` falso e cortesia/permuta recusam | — |
| `comissoes_ops.comissao_cheia_do_evento(event, settings, *, venda, taxa, bv_total, custo) -> (cheia, beneficiario_id, taxa_usada)` | **Camada 2 (P1)**: passa por `_beneficiario_comissionado` e, se passar, chama a base. Variante do 16b: cheia 0 em cortesia com valor e em evento sem vendedor | — |
| `comissoes_ops.comissao_do_retido`, `primeiro_repasse_aberto`, `reconciliar_comissao_do_cancelado` | A proporção, o ciclo e a invariante por beneficiário | 1e |
| `comissoes_ops.filtro_estorno_orfao`, `linha_abre_ciclo`, `tipo_da_linha`, `ciclo_de_pagamento_da_linha` | Os predicados únicos | 1e |
| `group_ops.dias_vivos(event)` | `group_events` sem os dias cancelados, o principal primeiro. Só para leitura: KPI (`_compute_kpi`), `_serialize_gastos` no principal vivo, KPI Jinja e `_group_cost` | 3b |
| `group_ops.passar_venda(antigo, novo, *, actor_name, agora)` | A passagem, sem commit, pelas duas listas da §6.3 | 2b, 6a |
| `gastos_ops.GastoLockedError(field, message, event_id)`, `gastos_ops.devolucao_de_cancelado(expense)` | A trava de Gastos Extras | — |
| `comercial_ops._montar_acrescimos` (em cinco fatias de ~30 linhas, a mesma lista do plan e da R20) e `alterar_acrescimos_do_cancelado` | A montagem da 305 extraída de `:216-404` e a gravação no lugar | — |
| `event_ops._apagar_ensaio_no_banco(ensaio)` | A parte de banco de `delete_ensaio` (`:1791-1811`), sem commit | — |
| `dre_ops.ROTULO_RETIDO = "Retido de cancelamentos"`, `gastos_extras_do_periodo`, `tendencia_mensal` | A DRE única da API e do Jinja | 1c (pelo `paineis.cancelamentos`) |
| Flags `can_edit_venda_cancelado`, `can_edit_pagamentos` | Calculadas depois de `_role_flags` (`agenda_read.py:155-204`) | 1c |

### 6.5 Nomes que não existem

| Não use | Use | Por quê |
|---|---|---|
| `ao_cancelar_dia` (rascunho da R15) | `cancel_ops.ao_cancelar` | O ponto roda em todo cancelamento, não só no corte |
| `CAMPOS_DA_VENDA` / `TABELAS_DA_VENDA` (rascunho da R16) | `group_ops.CAMPOS_DA_PASSAGEM` / `TABELAS_DA_PASSAGEM` | Ficam ao lado de `passar_venda`, que as percorre; a lista de tabelas nomeia classes de `models` |
| `CATEGORY_MULTA_CANCELAMENTO` em `app/constants.py` (rascunho do plan) | `SpecialExpense.CATEGORY_MULTA_CANCELAMENTO` | `CATEGORIES` e `CATEGORY_DEVOLUCAO` moram no modelo |
| `NOTA_CICLO_CANCELAMENTO` (rascunho do plan) | Nada: **removida** | Não tem uso. O ciclo da linha do cancelado vem de `sale_date`/`payable_from` gravados na criação (o primeiro repasse aberto), e `_sync` não toca evento cancelado (guarda). O motivo vai pelo prefixo de `MOTIVOS_AJUSTE_COMISSAO`. No principal vivo depois do corte vale a regra de hoje (1b-Q12 = B), sem marca. Diferente da `NOTA_CICLO_VALOR_TARDIO` (`constants.py:466`), que existe porque `_sync` regrava a data da linha viva |
| "variante só dias vivos de `group_events`" | `group_ops.dias_vivos` | Nome próprio, para não confundir com a coleção inteira |
| `_event_commission` como "núcleo" da cheia | `_base_da_comissao` + `comissao_cheia_do_evento` | A cheia precisa do gate do beneficiário; a casca não pode mudar número (P1) |
| `evento.cancelado:<principal_id>` / `evento.cancelado_escala:<dia_id>` | As chaves da §6.3 | Com `<principal_id>`, o 2º ato do grupo é engolido (P2); a chave do Casting segue o mesmo esquema do ato, com o dia |

## 7. Transições de estado

### 7.1 Cancelamento do evento

```text
vivo ─────────────────────────────── POST …/cancelar (Superadmin) ──────────────────────────▶ cancelado
  │  T1..T6 → valida → alvos do Google (antes do desmarcar) → (marcado: desmarcar(motivo=MOTIVO_CANCELADO)
  │  ANTES de cancelled_at) → flush → congela (linha + bvs + elenco) → (passagem: marca a comissão própria
  │  do novo → passar_venda → expire) → devolução → flush → (corte e passagem: venda nova + acompanhar_bv
  │  uma vez no principal que fica)
  │  → alvo → reconciliar → cancelled_at/by/reason, limpa pedido de exclusão → ao_cancelar
  │  → ensaios (banco), sinos e multas → EventLog (UTC) → commit
  │  → depois do commit: Google (show e ensaios), e-mail ao elenco
vivo marcado (303) ── mesmo ato, sem chamar o Google ───────────────────────────────────────▶ cancelado
cancelado ── excluir ─▶ 409 (sem volta; recria-se à mão)          cancelado ── "descancelar": não existe
cancelado `venda` ── correções FR-048 pelo Superadmin ─▶ cancelado `venda` (recongela; regime e refund_mode intactos)
`dia` (principal vivo) ── principal cancelado inteiro depois ─▶ continua `dia`; a devolução dele entra no devolvido da venda (§5)
`satelite`/`dia` ── desagrupar ─▶ 409          cancelado ── agrupar (principal ou satélite) ─▶ 409
```

### 7.2 Devolução à cliente

É um `SpecialExpense` da categoria devolução, aprovado e ligado ao evento ou a um dia do grupo.

```text
(ato, Tudo/Parte) nasce: aprovado · nao_pago · disbursement_type="cliente" · nome/PIX · expense_date = hoje (SP)
nao_pago ⇄ no_banco ⇄ pago            Planilha (Financeiro/Superadmin). O estado não é travado em Gastos Extras
                                       (FR-019), mas a porta trava o evento e confere valor_esperado (contrato §17):
                                       a tela manda valor_esperado em `bv` e em `expense`; a Planilha Jinja só trava
valor/data/categoria/vínculo/exclusão  só `cancel_ops.alterar_devolucao` (travado nas seis portas de Gastos Extras)
alterar_devolucao(devolucao_total):
   venda:  devolucao_total = o novo total devolvido do GRUPO
           piso = Σ devoluções pagas ou no banco de todos os dias + Σ devoluções aprovadas dos dias `dia`
                  (fixas: só o "Alterar devolução" do dia as muda)
           absorve: a aberta do principal; depois, as abertas dos dias `satelite`, por id
           teto = pago do grupo  (acima → 400, não 409)
   dia:    devolucao_total = o total daquele dia
           piso = máx(Σ devoluções do dia pagas ou no banco, devolução mínima do corte com a venda nova
                  congelada na linha `dia`)  (P-52)
           teto = pago do grupo − Σ devoluções aprovadas dos outros dias, vivos e cancelados  (acima → 409)
   aberta (nao_pago) do dono existe → absorve a diferença e fica uma só; se zerar, é excluída (audit via gastos_ops._log)
   sem aberta e total > piso        → nasce complemento (nao_pago, data de hoje, Planilha do mês dele)
   tocar uma devolução aberta       → regrava disbursement_type="cliente" e completa nome/PIX vazios (FR-020)
   depois de gravar: venda → reaplicar_cancelado(evento); dia com principal vivo → nada se refaz (clarify 15/10);
                     dia com principal cancelado inteiro → reaplicar_cancelado(principal) (D28; §5, §11)
pendente ligada a qualquer dia do grupo → recusa o ato (409, extra `dias`); depois do ato, aprovar/rejeitar → 409 (travada)
modo corrente (derivado): devolvido == 0 → nada · devolvido >= pago → tudo · entre → parte
```

### 7.3 Comissão do retido (`commission_payments`)

A regra vale por beneficiário: **Σ(a_pagar + no_banco + pago) = alvo**. O alvo é a comissão do retido para o beneficiário congelado e 0 para os outros que têm linha no evento.

```text
falta = alvo − liquidadas (pago + no_banco)
 falta == 0  → toda a_pagar do beneficiário no evento → cancelado (nunca fica a_pagar de 0,00)
 falta != 0  → a a_pagar mais antiga (ORDER BY id) recebe a falta NO LUGAR (data intacta, FR-032); as outras → cancelado
 sem a_pagar → nasce linha a_pagar (±): event_id = evento, original_id = a liquidada mais recente que ela acerta
               (NULL quando o beneficiário não tem liquidada), sale_date = payable_from = primeiro repasse aberto
               (EducaManto positiva: payable_from = dia do evento, se ainda não passou), notes = "<motivo>: …"
               (prefixo de MOTIVOS_AJUSTE_COMISSAO; sem marca de ciclo, §6.5)
a_pagar → no_banco → pago                         Planilha (liquidar_item_de_comissao / pagar-mes), sem mudar valor
pago → a_pagar                                     desfazer 267c (Superadmin + motivo): Σ igual; a próxima reconciliação absorve
pago | no_banco                                    nunca reescrito; só a passagem (event_id → novo principal) e a exclusão
                                                   (event_id → NULL + estorno órfão −, "Exclusão do evento") tocam o vínculo
qualquer status, linha de evento cancelado         set_commission_status Jinja recusa (contrato §21): o caminho é a Planilha
```

- **Tipo da linha**:
  - `estorno`: `event_id IS NULL ∧ original_id IS NOT NULL`, o órfão, que entra pelo resgate do mês;
  - `ajuste`: `event_id IS NOT NULL ∧ original_id IS NOT NULL`;
  - `comissao`: o resto.
- **Ciclo** = `ciclo_de_pagamento_expr`, que é `coalesce(payable_from, sale_date, date(created_at))` (`comissoes_ops.py:188-216`). O espelho em Python usa `created_at.date()` em UTC.
- `_sync_commission_payment` não toca linha de evento cancelado (guarda `if event.is_cancelled: return`, depois da Loja Virtual, `:914-921`).
- `_comissao_existente` ignora `original_id IS NOT NULL` e a nota `NOTA_COMISSAO_PROPRIA_DO_DIA`.

### 7.4 BV do retido

São dois registros: `event_acrescimos.bv_payment_status` e a linha congelada.

```text
no ato:   paid_at_cancellation = status ∈ {pago, no_banco};  paid_amount = amount_brl se sim, senão NULL
nao_pago ── marcar pago/no_banco (marcar_status_do_bv: evento → acréscimo; valor_esperado == atual) ─▶ pago|no_banco; paid_amount = atual
pago ⇄ no_banco                                   paid_amount não muda
pago|no_banco ── desfazer ─▶ nao_pago; paid_amount = NULL → volta ao proporcional (FR-039)
BV não pago ausente do PUT/deixou de ser BV (Superadmin) → sai a linha congelada junto com o acréscimo (decisão (d) do plan)
BV novo no PUT do cancelado → nasce acréscimo nao_pago + linha congelada (original_amount = amount_brl)
```

`bv_da_planilha(acr)` é a fonte única da Planilha, do resumo e do custo da DRE (decisão (a)):

| Situação | Valor que conta |
|---|---|
| Evento vivo | `amount_brl` |
| `venda`, linha congelada, pago ou no banco | `paid_amount`; se nulo, `amount_brl` (só na janela do deploy) |
| `venda`, linha congelada, não pago | `bv_do_retido(original_amount, retido, venda)` = `min(cheio, bv_que_acompanha(cheio, retido, venda))` (`orcamento/quote_ops.py:58`). Dá `None` quando o resultado é 0: some da Planilha |
| Sem linha congelada (`legado`, `satelite`, `dia`, `virtual`) | `amount_brl` se pago ou no banco; senão `None` |

### 7.5 Multa ao elenco

Uma multa por **escalação** (vaga × dia), nunca por artista agregado (§3).

```text
linha do elenco (ato) ── multa no ato (multas[role_id]) ou POST …/multas (elenco_id) ─▶ special_expense_id = gasto
   valor vazio ou 0 → ignorado nos dois caminhos (sem multa); negativo ou inválido → 400
   POST …/multas sem nenhum valor > 0 depois de ignorar vazios e zeros → 400 fields.multas
          "Informe a multa de ao menos um artista"
   gasto: category CATEGORY_MULTA_CANCELAMENTO · aprovado · disbursement_type="fornecedor" · nao_pago ·
          supplier_name/pix do Talent (pix_key, models.py:169) · event_id = day_event_id ·
          expense_date = data do ato / do lançamento (P-34)
gasto ── Gastos Extras (livre, sem trava) ─▶ continua lançada;  Planilha: nao_pago ⇄ no_banco ⇄ pago
gasto excluído ── SET NULL ─▶ "não lançada" (pode lançar de novo)
artista tirado da vaga pelo Casting (talent_id → NULL na vaga) ─▶ linha fica ("saiu da escala"); sem e-mail de remoção
multa já lançada na linha ─▶ 400 no POST …/multas (corrige-se em Gastos Extras)
```

O gasto da multa nasce direto no ORM, no molde de `_registrar_devolucao`. Não passa por `create_expense`, que nasce pendente e manda e-mail ao Financeiro (`gastos_ops.py:296`, `:314-316`).

## 8. Invariantes

1. **Um cancelamento por evento** (UNIQUE). Toda linha nasce na mesma transação que grava `cancelled_at`. Cancelado sem linha é `legado`. `regime` e `refund_mode` nunca mudam.
2. **Pago e devolvido nunca são gravados**, e são sempre do grupo por consulta (§5).
   - retido = max(0, pago − devolvido);
   - comissão do retido = mín(cheia, arredonda(cheia × retido ÷ venda)), e vale 0 se venda, retido ou cheia ≤ 0;
   - as duas contas de proporção (comissão e BV) passam por `bv_que_acompanha`, para não divergirem na tolerância de R$ 0,01.
3. **Nada se recalcula da venda viva.** O recongelamento usa a taxa congelada e o BV = Σ `original_amount` das linhas **com `acrescimo_id` não nulo**, nunca `_event_bv_total` (`comissoes_ops.py:733-743`). No EducaManto, usa o `commission_cost` do ato.
4. **A taxa congelada** só muda pela correção da taxa (ou da data de venda, depois da 1e). Mudar a taxa padrão não alcança cancelado.
5. **A invariante da 7.3 vale depois de todo ato e de toda correção**, inclusive depois do desfazer da 267c, porque o Σ não muda. Linha paga ou no banco nunca é reescrita.
6. **BV pago nunca é reescrito nem escondido.** `paid_amount` não nulo ⇔ `bv_payment_status ∈ {pago, no_banco}`, salvo a janela do deploy. Só `marcar_status_do_bv` o escreve.
7. **Linha congelada órfã não conta.** Uma `event_cancellation_bvs` com `acrescimo_id` NULL não entra no resumo, nem em `bv_da_planilha`, nem na cheia. O próprio fluxo nunca cria órfã: ele apaga a linha junto com o acréscimo.
8. **Devolução de cancelado**:
   - só `cancel_ops` escreve valor, data, categoria e vínculo;
   - `disbursement_type` fica `"cliente"`;
   - `approved_with_edits` nunca acende;
   - o status de pagamento é só da Planilha.
9. **Elenco.** A linha nunca é apagada por mudança na escala. Toda linha (escalação) tem no máximo uma multa, e todo gasto de multa ligado a uma linha é da categoria multa.
10. **Ordem de travas, sempre evento → dependentes** (decisão (g)):
    - T1 grupo: ids por consulta (`ids_do_grupo`), `SELECT … WHERE id IN (…) ORDER BY id FOR UPDATE` + `populate_existing`; a composição é relida, e se mudou, 409 `grupo_mudou`;
    - T2 cancelamentos, leitura com `populate_existing`;
    - T3 acréscimos `ORDER BY id FOR UPDATE`;
    - T4 linhas de comissão, num SELECT só `ORDER BY id FOR UPDATE`;
    - T5 devoluções do grupo `ORDER BY id FOR UPDATE`;
    - T6 escalações com talento, só no ato.

    O "Alterar devolução" segue a mesma ordem: T1 → T2 → T4 → T5. A correção comercial do cancelado pelo
    Superadmin (aba Comercial) também: T1 → T2 → T4 (linhas do evento e dos beneficiários antigo e novo)
    antes de gravar e reconciliar.

    `liquidar_periodo` e `pay_seller_month` ganham `order_by(CommissionPayment.id)` (`comissoes_ops.py:249-258`, `:631-638`). O desfazer da 267c trava os eventos das linhas antes delas.
11. **Hora.** `created_at`/`updated_at` usam o horário de São Paulo sem fuso. `EventLog` do ato e da passagem sai sem `created_at` (default UTC).
12. **Coleções.** Crie pela relação: `EventCancellation(event=event, …)`, `cancelamento.bvs.append(...)`, `cancelamento.elenco.append(...)`. Depois de T1 e antes de ler `_group_cost`, expire `satellites`. Depois de reconciliar e passar a venda, faça `db.session.expire(event, ["commission_payments"])` (a relação de `models.py:981-986`, backref em `:984`) e expire `acrescimos`, `satellites`, `group_leader` e `ensaios` dos eventos tocados.

## 9. O que NÃO muda em tabelas existentes

Nenhuma coluna, índice, tipo ou default muda. O que passa a ser **escrito** (ou lido de outro jeito):

| Tabela | O que a 306 escreve | Observação |
|---|---|---|
| `calendar_events` | `cancelled_at/_by_id/cancellation_reason` em cada dia; limpa o pedido de exclusão; `google_missing_since` = NULL (`desmarcar`). No corte: `sale_value` e `sale_value_gross` do principal. Na passagem: `group_leader_id` dos dias e `CAMPOS_DA_PASSAGEM` (FR-059) | `commission_rate`, `seller_id`, `sale_value` e `is_cortesia_permuta` do cancelado mudam pelas correções da FR-048 (c) e (f) e recongelam |
| `commission_payments` | Linhas novas (`original_id` = a paga; `event_id` do evento); `amount` da `a_pagar` no lugar; `status` → `cancelado`; `event_id` na passagem e na exclusão | `status no_banco` já existe (docstring `:946-956`). Nota com prefixo de motivo |
| `special_expenses` | Devolução (`cliente`, aprovada); complemento; multa (`fornecedor`, aprovada, uma por escalação) | `DISBURSEMENT_TYPES` já tem `cliente` (`:1075`); `amount Numeric(10,2)` (`:1080`) |
| `event_acrescimos` | `bv_recipient`/`bv_pix` completados no ato (FR-010); regravação no lugar pelo Superadmin; `bv_payment_status` pela Planilha | Continuam apagar e recriar no vivo (`comercial_ops.py:407-413`) |
| `event_payments`, `event_reimbursements`, `event_installments`, `event_invoices`, `event_contracts`, `event_clients` | `event_id` → novo principal na passagem (`TABELAS_DA_PASSAGEM`); comprovantes do Superadmin no cancelado | — |
| `event_roles` | Nada no ato (a escala fica). `assign_role` do cancelado não manda e-mail de remoção (`casting_ops.py:153-161`) | Ensaios do dia são apagados: as linhas deles saem com o ensaio |
| `event_logs`, `audit_logs`, `notifications`, `sync_logs` | Linhas novas | Kinds novos são texto (`kind String(40)`, `models.py:686`) |

## 10. Migration

**Arquivo provisório**: `migrations/versions/c5d2f7a9e306_dinheiro_do_cancelamento.py`. Ela tem `revision = "c5d2f7a9e306"`, um id provisório que não colide com nada no HEAD (gere outro se preferir), e `down_revision = "a7c3e91f4d28"`. É escrita à mão, porque `flask db migrate` é proibido.

```python
def upgrade() -> None:
    op.create_table(
        "event_cancellations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("calendar_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("regime", sa.String(12), nullable=False),
        sa.Column("refund_mode", sa.String(8)),
        sa.Column("sale_value", sa.Numeric(12, 2)),
        sa.Column("commission_full", sa.Numeric(12, 2)),
        sa.Column("commission_rate", sa.Numeric(6, 3)),
        sa.Column("commission_cost", sa.Numeric(12, 2)),
        sa.Column("commission_seller_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("seller_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("with_invoice", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("retained_tax", sa.Numeric(12, 2)),
        sa.Column("group_leader_id", sa.Integer(), sa.ForeignKey("calendar_events.id", ondelete="SET NULL")),
        sa.Column("sale_handed_over", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sale_value_before", sa.Numeric(12, 2)), sa.Column("sale_value_after", sa.Numeric(12, 2)),
        sa.Column("sale_value_gross_before", sa.Numeric(12, 2)), sa.Column("sale_value_gross_after", sa.Numeric(12, 2)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.UniqueConstraint("event_id", name="uq_event_cancellations_event_id"),
    )
    op.create_index("ix_event_cancellations_group_leader_id", "event_cancellations", ["group_leader_id"])
    op.create_table(
        "event_cancellation_bvs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cancellation_id", sa.Integer(), sa.ForeignKey("event_cancellations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("acrescimo_id", sa.Integer(), sa.ForeignKey("event_acrescimos.id", ondelete="SET NULL")),
        sa.Column("recipient", sa.String(200)), sa.Column("pix", sa.String(140)),
        sa.Column("original_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_at_cancellation", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("paid_amount", sa.Numeric(12, 2)),
        sa.UniqueConstraint("acrescimo_id", name="uq_event_cancellation_bvs_acrescimo_id"),
    )
    op.create_index("ix_event_cancellation_bvs_cancellation_id", "event_cancellation_bvs", ["cancellation_id"])
    op.create_table(
        "event_cancellation_elenco",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cancellation_id", sa.Integer(), sa.ForeignKey("event_cancellations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("talent_id", sa.Integer(), sa.ForeignKey("talents.id"), nullable=False),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("event_roles.id", ondelete="SET NULL")),
        sa.Column("day_event_id", sa.Integer(), sa.ForeignKey("calendar_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("character_name", sa.String(120), nullable=False),
        sa.Column("cache_reference", sa.Numeric(12, 2)),
        sa.Column("special_expense_id", sa.Integer(), sa.ForeignKey("special_expenses.id", ondelete="SET NULL")),
        sa.UniqueConstraint("special_expense_id", name="uq_event_cancellation_elenco_special_expense_id"),
    )
    for col in ("cancellation_id", "talent_id", "role_id", "day_event_id"):
        op.create_index(f"ix_event_cancellation_elenco_{col}", "event_cancellation_elenco", [col])


def downgrade() -> None:
    # Filhas primeiro.
    for col in ("day_event_id", "role_id", "talent_id", "cancellation_id"):
        op.drop_index(f"ix_event_cancellation_elenco_{col}", table_name="event_cancellation_elenco")
    op.drop_table("event_cancellation_elenco")
    op.drop_index("ix_event_cancellation_bvs_cancellation_id", table_name="event_cancellation_bvs")
    op.drop_table("event_cancellation_bvs")
    op.drop_index("ix_event_cancellations_group_leader_id", table_name="event_cancellations")
    op.drop_table("event_cancellations")
```

**A docstring da migration diz:**
- **Aditiva**: o código anterior lê e grava no banco migrado.
- **Rollback: reverter o merge, sem `downgrade`, é limpo até o primeiro cancelamento real.** Depois dele:
  - o código antigo zera a comissão do retido na primeira abertura de Comissões ou da Planilha (`should_have`, `comissoes_ops.py:930-932`, `:945-948`);
  - o código antigo toma o ajuste do corte de dia (`a_pagar` com `original_id`, ligado ao principal vivo) pela comissão do evento e o regrava com a cheia (`_comissao_existente`, R6);
  - o código antigo lista pelo cheio o BV não pago do cancelado (`_build_bv_items`), e a Planilha da 305 deixa marcá-lo pago por esse valor;
  - o código antigo deixa excluir o cancelado vazio, inclusive pelo sync, e o CASCADE leva o congelamento junto;
  - o `downgrade` apaga o congelamento sem volta;
  - ensaios apagados, e-mails enviados e a venda passada de dia não voltam.

  A partir daí, defeito se corrige para a frente (`306b`).

**Antes do push:**
- reproduzir o build num venv 3.11 (`manto_deploy_dependencias_soltas`);
- a ida e volta da migration (`upgrade`, `downgrade a7c3e91f4d28`, `upgrade`) no `manto_local`, com as três tabelas vazias depois da limpeza do verify. O lugar único do roteiro é o quickstart §4; o §7 o repete no venv 3.11. Banco descartável do dump não é preciso: a migration só cria tabelas;
- conferir `create_app()` com os mappers configurados.

O ensaio de migração destrutiva não se aplica.

## 11. O que este modelo leva à spec (Living Spec, antes do `/speckit-tasks`)

A seção Entidades da spec (em Requisitos) e algumas FRs não dizem o que este modelo fixa. Entram na spec antes das tarefas:

1. **`paid_amount`** em `event_cancellation_bvs` (FR-039/FR-040, leitura 10): o valor que conta enquanto o BV está pago ou no banco; desfazer o pago volta ao proporcional.
2. **Colunas que as Entidades não listam**: `commission_cost` (o custo de cachês da cheia EducaManto no ato, com a base da §1), `sale_handed_over` (o antigo 1º dia que passou a venda) e `special_expense_id` (a multa da linha do elenco).
3. **Multa por escalação** (vaga × dia), no lugar de "uma linha por artista" da FR-070 e da FR-071. A 1b-Q8 = A continua valendo: cada campo é de um artista, numa vaga e num dia. Vazio e 0 são "sem multa" no ato e no lançamento depois (FR-072).
4. **FR-062**: no evento avulso, o ponto recebe `("todos", None)`; no corte de um dia que não é o principal, `("so_este_dia", None)`, porque nenhum dia passou a guardar a venda.
5. **O dia cortado com o principal cancelado depois** (6º ponto da lista do plan): a devolução do `dia` conta no devolvido da venda do principal, e o "Alterar devolução" do dia refaz o retido e a comissão do principal. Deriva da D28 ("Acompanham"); o "não mexe em comissão" do clarify de 15/10 vale enquanto o principal está vivo. Variante no cenário 39.
