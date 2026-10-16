# Pesquisa: Feature 306 (Phase 0)

**Base.** Esta pesquisa junta quatro fontes:
- a spec (`specs/306-dinheiro-do-cancelamento/spec.md`, com 74 FRs, a leitura 1–11, o clarify de 15/10 e a Living Spec do plan já aplicada: **59** cenários, com os dois novos, 37b e 38c, R28);
- o plano do backlog (`docs/backlog/1b-dinheiro-do-cancelamento.md`, citado como **Lnnn**, sem o texto riscado);
- a pesquisa da 303 (`specs/303-sync-nao-apaga-venda/pesquisa/`);
- um mapa do código **no HEAD `657adb8`**, que em `app/` e `frontend/` é igual a `d855d1a` (303, 215b, 267c e 305 em produção). Depois do rebase de 16/10 sobre `6356b80` (com a 307), as citações dos três arquivos que a 307 deslocou foram reconferidas.

O mapa foi feito em 15/10/2026 em cinco áreas: comissão e Planilha; agenda e endpoints; cancelamento, grupos, Google, casting e avisos; DRE e Gastos Extras; frontend e modelo. Depois veio uma rodada de oito decisões, (a)–(h), e uma crítica dos artefatos de plan (24 problemas, P1–P24), cujas correções estão aplicadas abaixo e valem igualmente no plan, no data-model e nos contratos.

**Nomes.** A tabela única de nomes que a 1c, a 2a, a 2b e a 6a reusam (constantes, funções de extensão, listas da passagem, códigos 409) é o **data-model §6**. Esta pesquisa usa os mesmos nomes e aponta para lá.

Toda citação `arquivo:linha` abaixo é do HEAD, conferida com `git show HEAD:`. Nada foi editado. O banco foi lido só por `docs/backlog/ferramentas/sql_ro.py`, no espelho de 30/09: 0 cancelados, 0 marcados, `site_settings.tax_rate` nulo (usa 16%) e `default_commission_rate` 2,5.

**De onde vem cada decisão:**
- **[D]**: decisão do dono, com a dúvida;
- **[P]**: premissa do plano (P-n da spec);
- **[L]**: leitura da spec (Session 2026-10-15, n);
- **[R]**: decisão técnica desta pesquisa, tirada do mapa ou da rodada (a)–(h), coerente com as decisões do dono.

---

## R0: base das citações e premissas que caíram no HEAD

**As citações vêm de três bases diferentes:**
- o plano usa `f6ad283` (01/10);
- a pesquisa da 303 usa **`14cec75`** (22/09, anterior à 303; ver `pesquisa/LEIA-ME.md:3-5`);
- a spec segue o plano (por exemplo, `routes.py:883` na FR-052).

Por isso cada citação foi reconferida contra a base certa.

**Nenhum dos três (215b, 267c, 305) tocou** `cancel_ops.py`, `group_ops.py`, `sumico_ops.py`, `service.py`, `sync.py`, `app/calendar/casting_ops.py` (`app/casting/` não existe), `notificacoes_ops.py`, `config.py`, `models.py`, `constants.py`, `cobranca_ops.py`, `financeiro_read.py` e `migrations/`. A cabeça única das migrations é `a7c3e91f4d28`, igual ao `alembic_version` do espelho.

**Deslocamentos desde `f6ad283`:**

| Arquivo | Quem mexeu | Deslocamento |
|---|---|---|
| `comissoes_ops.py` | 267c | +110 a partir de 252 |
| `financeiro/routes.py` | 267c | +14 a partir de 961; +9 em `/vendas/` |
| `financeiro_write.py` | 267c e 305 | ramos de comissão e BV reescritos |
| `agenda_write.py` | 215b e 305 | +26 até ~700; +137 no bloco de grupo |
| `calendar/routes.py` | 305 | +53 entre 834 e ~3190; +112 depois de ~4104 |
| `event_ops.py` | 215b e 305 | +93 no bloco de busca e ensaio |
| `email_service.py` | 304 | +43 |

**Premissas do plano e da pesquisa que mudaram no HEAD:**

| Premissa | No HEAD | Efeito |
|---|---|---|
| L871-873: "`liquidar_periodo` não trava" | trava, **sem `order_by`** (`comissoes_ops.py:249-258`); `pay_seller_month` também, sem ordem (`:631-638`) | R24: `order_by(id)` nas duas |
| §5: `month_status` em `routes.py` | mora em `comissoes_ops.py:573` | R6 |
| L1518: "o PIX do BV hoje não vai" | vai a todo `show_comercial` (`agenda_read.py:560`) | R19: no cancelado, a 306 **retira** o PIX |
| `cobranca_ops.py:403-410`, `:428`: a data do grupo passa a ignorar o cancelado | já ignora em `data_do_grupo` (`:236-243`, desde a 299) | R22: sobra só descontar as devoluções |
| `routes.py:3301` `_criar_acrescimos_do_orcamento` | sumiu; virou `gravar_acrescimos_do_orcamento` (`orcamento_evento_ops.py:432`), que recusa cancelado | R19: falta só o 409 no núcleo `set_event_orcamento` (`:935`) |
| `_cleanup_stale_events` (L1006) | virou `sumico_ops._apagar_vazio` (`:341-356`) | R7 |
| `comercial_ops.py:66-117` | reescrita em `:156-414`, que **continua apagando e recriando** (`:407-411`) | R20 |
| `routes.py:883` (FR-052) | a chamada está em `calendar/routes.py:905`; `estado_da_venda` em `:837` | R19 |
| `api_cancelar_evento` `:553-585` | `:579-611`, com `except EventoMarcadoError` em `:607-608` | R2 |
| `travar_evento` como trava do ato | relê **só 4 colunas** (`orcamento_evento_ops.py:799`) | R24: T1 próprio |
| 00-integracao §1 (tabela de dados) | superada em quatro pontos: `negotiated_amount` saiu (1b-Q2); `SET NULL` em vendedor; faltam colunas; `regime String(12)` | R1 |
| `down_revision = "e5a1c7d93b20"` | `a7c3e91f4d28` | R1 |
| item de comissão "só pago se todas forem" (C:163/398/640) | partido em aberto × `:pago` (`routes.py:941-959`); `continue` por grupo (`:950-952`) | R6 |
| portas não citadas | `PATCH /api/events/<id>` (`_gravar_venda_da_edicao`, `event_ops.py:846-879`) e `api_remover_satelite` (`agenda_write.py:2455`) | R19, R15 |
| `sumico_ops._bloquear_e_revalidar :716-733` | `:717-734` | molde, R24 |
| "`_event_commission` tem cinco consumidores" (rascunho do plan) | são **8 chamadas**: `financeiro/routes.py:231`, `:434`, `:1463`; `financeiro_read.py:402`; `vendas_ops.py:290`, `:339`; `comissoes_ops.py:403`, `:937` | R4 |
| `_event_commission` zera cortesia e "sem beneficiário" | não: zera só venda nula, Loja Virtual e beneficiário com `receives_commission` falso (`comissoes_ops.py:766-796`); cortesia e "sem beneficiário" estão só no `should_have` (`:926-936`) | R4: duas camadas |

---

## R1: modelo, com três tabelas novas e a relação no filho. [P-1, P-2, P-4] + [R]

**Decisão.** Uma migration escrita à mão, `<rev>_dinheiro_do_cancelamento.py`, com `down_revision = "a7c3e91f4d28"` e **só `create_table`**. O `downgrade` derruba `…_elenco`, depois `…_bvs`, depois `event_cancellations`. Dinheiro é sempre `Numeric(12,2)`. Colunas, nulidade, índices e nomes de UNIQUE estão no data-model §1–§4 e §10; aqui fica o que decide.

- **`event_cancellations`**:
  - `event_id`: FK `calendar_events`, `ondelete=CASCADE`, **UNIQUE** (`uq_event_cancellations_event_id`);
  - `regime`: `String(12)`, com os valores `venda`, `satelite`, `dia` e `virtual`; imutável;
  - `refund_mode`: `String(8)`, nulo em `satelite` e `virtual`; imutável;
  - `sale_value`, `commission_full`, `retained_tax` (nulo = não se aplica);
  - **`commission_rate Numeric(6,3)`**;
  - **`commission_cost Numeric(12,2)` nulo**: os cachês da base EducaManto no ato, pela **mesma base de custo da comissão** (R4);
  - `commission_seller_id` e `seller_id`: FK `users` **sem `ondelete`**;
  - `with_invoice`;
  - `group_leader_id`: FK `calendar_events`, `SET NULL`, com índice;
  - **`sale_handed_over Boolean NOT NULL default false`**: verdadeiro só no antigo 1º dia que passou a venda (FR-058). É dele que a tela lê `venda_passou_para` (= `group_leader_id`). O `EventLog` não se consulta, e um `dia` comum também tem `group_leader_id`, então sem a coluna não há como distinguir os dois (R16);
  - `sale_value_before`/`_after` e `sale_value_gross_before`/`_after`, só no regime `dia`;
  - `created_at`/`updated_at` em hora de São Paulo sem fuso, como `cancelled_at`;
  - `updated_by_id`: FK `users`, `SET NULL`.
- **`event_cancellation_bvs`**:
  - `cancellation_id`: `CASCADE`, com índice;
  - `acrescimo_id`: FK `event_acrescimos`, `SET NULL`, **UNIQUE** (`uq_event_cancellation_bvs_acrescimo_id`; os nulos são livres);
  - `recipient String(200)` e `pix String(140)`, os tamanhos do acréscimo (`models.py:1863-1864`);
  - `original_amount`: o BV cheio;
  - `paid_at_cancellation Boolean`;
  - **`paid_amount Numeric(12,2)` nulo** (R9).
- **`event_cancellation_elenco`**, uma linha por **escalação** (vaga × dia, R18):
  - `cancellation_id`: `CASCADE`, com índice;
  - `talent_id`: FK sem cascade, com índice;
  - `role_id`: `SET NULL`, com índice (o sync apaga vagas, e o `SET NULL` precisa do índice);
  - `character_name` e o cachê da vaga como referência (`Numeric`);
  - **`day_event_id`: FK `calendar_events`, `ondelete=CASCADE`, `NOT NULL`**, com índice. O dia cancelado não se exclui (FR-021, R7), então o CASCADE só age se essa regra for furada; com `SET NULL`, a linha perderia o dia e a multa não teria onde nascer;
  - **`special_expense_id`**: FK `special_expenses`, `SET NULL`, **UNIQUE** (`uq_event_cancellation_elenco_special_expense_id`: um gasto é de uma linha) (R18).
- **Classes.** As três ficam depois de `Event3DDismissal` (`models.py:2376-2403`), com a relação declarada **no filho**:
  - `relationship("CalendarEvent", foreign_keys=[event_id], backref=db.backref("cancelamento", uselist=False, cascade="all, delete-orphan"))`;
  - as filhas usam `backref("bvs"/"elenco", cascade="all, delete-orphan")`.

  `CalendarEvent` e `_clear_event_side_tables` não mudam. **`foreign_keys=` vai em toda relação**, porque há duas FKs para `calendar_events` e três para `users` (mais uma para `calendar_events` no elenco). Sem isso, o `AmbiguousForeignKeysError` na configuração dos mappers derruba o `create_app()`, e com ele o `startCommand`.
- **Nomes e constantes** pela tabela única do data-model §6:
  - em `app/constants.py`, perto de `NOTA_CICLO_VALOR_TARDIO` (`:466`): `REGIME_*` (com o derivado `REGIME_LEGADO`, nunca gravado), `MODO_*`, `ALCANCE_TODOS`/`ALCANCE_SO_ESTE_DIA`, `DIA_DO_REPASSE = 5`, `MOTIVOS_AJUSTE_COMISSAO` (prefixo da nota → código da 1e, FR-033), `NOTA_COMISSAO_PROPRIA_DO_DIA` (R16), `CODIGO_EVENTO_CANCELADO` e **os demais códigos 409** desta entrega, **18 ao todo** com ele (`ja_cancelado`, `ensaio`, `grupo_mudou`, `sem_outro_dia_vivo`, `cache_pago`, `devolucao_pendente`, `max_devolucao_mudou`, `tente_de_novo`, `nao_cancelado`, `regime_sem_retido`, `abaixo_do_piso`, `acima_do_teto`, `pago_abaixo_do_devolvido`, `bv_nao_esta_a_pagar`, `valor_mudou`, `devolucao_travada`, `estado_mudou`), cada um numa constante, com uma união de literais espelho em TS (`CodigoRecusaCancelamento`, em `lib/eventOps.ts`, ao lado de `CodigoDevolverAoGoogle`). `CODIGO_VALOR_MUDOU` (`"valor_mudou"`) é o único que entra num 409 que já existe: o do set-status do BV da 305, que hoje sai sem `codigo` (R9); vale também para a devolução de cancelado na Planilha (R11). Nenhum código 409 fica como string solta no núcleo ou na view (Princípio II);
  - em `models.py`: `SpecialExpense.CATEGORY_MULTA_CANCELAMENTO = "Multa de cancelamento"`, no molde de `CATEGORY_DEVOLUCAO` (`:1073`), dentro de `CATEGORIES` (`:1070-1072`) (R18);
  - em outros módulos: `sumico_ops.MOTIVO_CANCELADO`, que entra em `_MOTIVOS_DE_DESMARCAR` (`:60-62`); os dois kinds do sino em `notificacoes_ops` (R17); `group_ops.dias_vivos` (R15); `group_ops.CAMPOS_DA_PASSAGEM`/`TABELAS_DA_PASSAGEM` (R16); `cancel_ops.ao_cancelar`, o ponto de extensão da 2a (R15).

  `CODIGO_EVENTO_CANCELADO` não se confunde com `sumico_ops.CODIGO_CANCELADO` (`:641`), que é código de erro da devolução ao Google.

  **`NOTA_CICLO_CANCELAMENTO` não existe.** O rascunho do plan a listava sem uso. A linha de ajuste já leva o motivo como prefixo da nota (`MOTIVOS_AJUSTE_COMISSAO`), e a data do ciclo dispensa marca: diferente da 299, nenhuma sincronização regrava essas datas, porque o `_sync` não toca o cancelado (guarda, R6) e `_comissao_existente` ignora toda linha com `original_id` (R6).
- **Taxa.** A origem é `Float` (`CalendarEvent.commission_rate`, `models.py:279`, e o `SiteSetting`). Ela é congelada como `Decimal(str(x))` e comparada por `_mesma_taxa` (`event_ops.py:1105`). Sem isso, "2.5" e "2.50" dão falso "a taxa mudou".
- **Vendedor congelado.** `delete_user` (`app/admin/user_ops.py:417-432`) ganha o bloqueio "cancelamentos" quando o usuário é `seller_id` ou `commission_seller_id` de algum cancelamento (FR-073). Hoje isso daria 500 por violação de FK.

**Por quê.**
- A spec veta coluna em tabela existente, JSON com dinheiro e backfill (Entidades; "O que não fazer").
- Pago e devolvido são lidos ao vivo (FR-002). Cancelado sem linha é `legado`, e hoje não há nenhum.
- `commission_cost` existe porque a FR-049 pede a cheia EducaManto "com os cachês, como no ato", e `_event_cost`/`_group_cost` são lidos ao vivo (`comissoes_ops.py:709-730`). O Casting pode esvaziar a escala do cancelado (1c-Q10), e a base mudaria.
- `sale_handed_over` existe porque a resposta do cancelar e o resumo dizem "a venda passou para DD/MM" (FR-058), e nada mais distingue o antigo 1º dia de um dia cortado comum.

**Alternativas consideradas.**
- `negotiated_amount`: saiu com a 1b-Q2.
- `day_event_id` com `SET NULL`: a linha sem dia perde o vínculo da multa e do aviso; como o dia cancelado nunca se exclui, `CASCADE` + `NOT NULL` é o que descreve a regra.
- Ler "a venda passou" do `EventLog`: texto livre, não consultável.
- `SET NULL` em `seller_id`/`commission_seller_id`, como propunha a pesquisa: apagaria em silêncio o beneficiário congelado.
- Elenco em JSON (sugestão antiga da 1c): vetado, porque a multa aponta para a linha e o cachê é dinheiro.
- Tabela de ligação multa ↔ linha: mais peso que a FK, para "uma multa por linha".
- `counted_amount` como property: obrigaria `models` a consultar pago e devolvido (N+1 e ciclo `models` → `cancel_ops`).
- Derivar o custo de `commission_full/commission_rate`: falha quando a base foi presa em 0.

**Decisões do dono que amarram.**
- 1b-Q2 = A: nada negociado; proporção.
- 1c-Q10: lista do ato guardada; tirar da escala segue possível.
- 1e-Q2 = C: taxa congelada.
- 1c-Q11 = C: acréscimos editáveis, e o congelado acompanha.
- Q16 = A: o vendedor pode mudar.
- D34: uma entrega só.

---

## R2: o ato tem ordem fixa, validações antes de gravar e a prévia faz a mesma conta. [P-20, P-21, FR-007…FR-016] + [R]

**Decisão.** `cancelar_evento` (`cancel_ops.py:254-341`) é reescrita em funções de cerca de 30 linhas. A ordem é única para todas as variantes (avulso, todos, só este dia, passagem):

1. **Travas** T1 → T6 (R24). Só depois delas se leem `is_cancelled`, regime, vendedor, taxa e `google_event_id`.
2. **Validações, sem escrever nada**, na ordem e com os códigos dos contratos §1:
   - 409 `ja_cancelado`;
   - 409 `ensaio`;
   - 400 `fields.alcance` (R15);
   - 409 `sem_outro_dia_vivo` e 409 `grupo_mudou`;
   - 409 `cache_pago`, com `dias`;
   - 409 `devolucao_pendente`;
   - 400 com **todos** os `fields` de uma vez: `motivo`, `devolucao_modo`, `devolucao_valor` (teto inclusive), `devolucao_nome`, `devolucao_pix`, `imposto_retido` (R10), `venda_nova`, `bv_pix_<acrescimo_id>` e `multa_<role_id>` (só negativa ou inválida; 0 e vazio são ignorados, R18);
   - 409 `max_devolucao_mudou`, com `max_devolucao`: "Tudo" com valor diferente do máximo recalculado sob a trava.
3. Se marcado: `sumico_ops.desmarcar(event, motivo="cancelado")`, **antes** de `cancelled_at`. Depois dele, `is_google_missing` fica falso, `desmarcar` vira no-op (`sumico_ops.py:262-290`) e o aviso do sino nunca é lido.
4. `_validar_pix_do_bv` grava recebedor e PIX vindos do corpo no acréscimo, já travado (T3).
5. `flush` → congelar: cheia (R4), taxa, beneficiário, vendedor, nota, imposto, BVs e elenco.
6. `_registrar_devolucao` → `flush`.
7. Só no corte: `estado_da_venda(principal)` → venda nova → `acompanhar_bv_da_venda` **uma vez** → `flush` (R15).
8. Alvo → reconciliar (R5).
9. `cancelled_at`, `cancelled_by_id` e `cancellation_reason`, mais a limpeza do pedido de exclusão (`:310-316`).
10. `cancel_ops.ao_cancelar`, o ponto de extensão da 2a, em **cada** dia cancelado pelo ato (R15), logo depois de `cancelled_at`.
11. Ensaios (parte de banco), sinos (chave do ato, R17) e multas (R18).
12. `EventLog` **sem `created_at`** (o default é UTC, `models.py:631`) e `_log_sync`.
13. Commit. `IntegrityError` no UNIQUE vira rollback + 409 `ja_cancelado`; deadlock (40P01) vira rollback + 409 `tente_de_novo` (R24).
14. Fora da trava: Google (R23) e e-mails por `send_async`, com ids guardados antes do commit.

Do passo 9 ao 13, a ordem é **uma só** em todo artefato (plan, Travas; data-model §7.1; R24): `cancelled_at` → `ao_cancelar` → ensaios (banco), sinos e multas → `EventLog` → commit.

**Erros e resposta:**
- `CancelValidationError` (`cancel_ops.py:39-44`) passa a `(message, field=None, status=400, codigo=None, **extras)`. O `codigo` sai sempre das constantes de `app/constants.py` (R1), nunca de string solta.
- A API mapeia para `json_error` com `fields`, `codigo`, `max_devolucao` e `dias`.
- Sai `except EventoMarcadoError` de `api_cancelar_evento` (`agenda_write.py:607-608`), e sai a recusa do marcado em `cancelar_evento` (`:282-283`). Ela fica só na exclusão (`calendar/routes.py:4370-4371`; `agenda_write.py:568-569`).
- A recusa do líder (`:289-292`) **fica até a História 5**. Tirada antes do laço dos dias, o principal seria cancelado com os satélites vivos.
- Resposta: `{ok, resumo, aviso?, dias_cancelados?, ensaios_cancelados?, avisados?, venda_passou_para?}`. `aviso` continua, porque o bundle antigo o mostra.

**Prévia.**
- `previa_cancelamento(event, devolucao, venda_nova=None)`, servida por `GET …/impacto-exclusao?devolucao=` (com `&venda_nova=`).
- É **a mesma conta** com `simular=True`: sem trava e **sem mutar objeto ORM**. Senão o autoflush de qualquer consulta seguinte transforma o GET em escrita.
- `primeiro_repasse_aberto(…, excluir_event_id=event.id)` faz a prévia bater com a execução (R5).
- Valor inválido dá 400 `fields.devolucao`.
- O impacto manda `acao: "cancelar"` para todo marcado (hoje `:114` decide só por `pode_excluir`).
- **Prova da FR-011 (prévia = execução).** Os cenários 4 e 6 só conferem 400 e 403; nenhum compara o `efeito` com o gravado. Entram variantes no **2** e no **8**, com `hoje` no dia 2 e no dia 10:
  - `GET …/impacto-exclusao?devolucao=` antes e `POST …/cancelar` depois, com o mesmo valor;
  - `retido`, `comissao_retido`, `ajuste`, `ciclo`, `repasse_em` e `bv_retido` da prévia iguais ao gravado, lido por conexão separada;
  - **mutação** "simular escreve": `simular=True` passa a mutar o ORM; o verify a pega por conexão separada (linha mudada ou travada depois do GET).

  É ponto da Living Spec (R30).

**Por quê.**
- Hoje `gcal_delete` roda **antes** do commit (`:300-308`). Com a trava nova, ele seguraria a linha do evento durante uma chamada de rede.
- O `EventLog` grava `agora` de São Paulo sem fuso (`:321-327`), e os leitores tratam hora sem fuso como UTC (`calendar/routes.py:1644-1647`): aparece 3 h antes (FR-016).
- O endpoint carrega o evento antes, para o 404 e o 403. Sem releitura, `event.is_cancelled` sai velho do mapa de identidade.

**Alternativas consideradas.**
- Google antes do commit: segura a trava durante a rede.
- `travar_evento` como T1: relê 4 colunas.
- Endpoint de prévia separado: a spec fixa `?devolucao=` no impacto.
- Manter a recusa do marcado: a D35 valia "até esta entrega".

**Decisões do dono que amarram.**
- D22: devolver.
- D27 ("Vem vazio"): Tudo, Parte ou Nada, obrigatório.
- D35.
- 1b-Q4 = B.
- 1c-Q3 = C.
- Q11 = B.
- FR-012: a recusa do líder sai pela Q1 = C.

---

## R3: regimes e o que cada um faz. [FR-003, P-4, P-5, P-9] + [R]

**Decisão.**

| Regime | Quando nasce | Retido, comissão e BV do retido | Devolução própria | "Alterar devolução" | BV não pago na Planilha | Entra na DRE e no comercial |
|---|---|---|---|---|---|---|
| `venda` | evento avulso ou principal no "todos" | sim (grupo inteiro) | sim | sim (R12) | proporcional (zero some) | sim, no mês do cancelamento |
| `satelite` | dia vivo no "todos" | zero (o retido é do principal) | não | 409 | some | contagem 0 |
| `dia` | "só este dia", inclusive o antigo 1º dia | zero (já está na venda nova do principal, no mês do evento) | sim, ligada ao dia | sim, regra própria (R12) | some | contagem 0; a devolução sai dos gastos |
| `virtual` | venda virtual | nenhum (o dinheiro segue o pedido `VirtualOrder`; a comissão não existe, `comissoes_ops.py:918-921`) | não | 409 | some | contagem 0 |
| `legado` (sem linha) | cancelado antes desta entrega | comissão 0, imposto 0, BV só o pago | — | aceita; imposto no corpo dá 400 | só o pago | sim |

O regime `satelite` sempre aponta o principal (`group_leader_id`). Pago e devolvido do cancelamento são **do grupo** (FR-004).

**Por quê.**
- Contar o retido do dia cortado de novo seria contar duas vezes o dinheiro que já está na venda nova do principal (L814-827).
- `n_cancelados` conta vendas, não dias.

**Alternativas consideradas.** O retido próprio por dia: o dia não tem venda (3b-Q4 = A: a proposta não tem preço por dia).

**Decisões do dono que amarram.**
- 1b-Q1 = C.
- 1b-Q5 = B.
- Q15 = A.
- D23: BV de cancelado fora da Planilha, salvo o pago.
- 3b-Q4 = A.

---

## R4: retido, comissão cheia e comissão do retido. [D14, D25, 1b-Q2 = A, FR-004, FR-027, FR-028] + [R]

**Decisão.**

- **Retido** = `max(0, pago − devolvido)`, em `Decimal`.
  - **Os dias do grupo** são os ids de T1, lidos **por consulta** por `cancel_ops.ids_do_grupo` (data-model §6.4: `group_leader_id = principal` mais o principal), vivos e cancelados; fora do ato, a mesma consulta roda sem trava. **Nunca** por `leader.satellites` nem por `group_ops.group_events` (`group_ops.py:64-75`), que passam pela coleção e saem velhos depois da passagem ou de um agrupamento no mesmo request. Vale para o pago e para o devolvido, no ato, no resumo e nas correções.
  - **Pago**: soma dos comprovantes de **todos os dias** do grupo. Comprovante sem valor conta 0; `total_recebido` já usa `coalesce` (`cancel_ops.py:65-72`). O lote sai por `cobranca_ops.comprovantes_por_evento` (`:197`). O reembolso a cobrar da cliente não entra.
  - **Devolvido**: `filtro_devolucao()`, predicado único = `category == CATEGORY_DEVOLUCAO` (`models.py:1073`) ∧ `event_id ∈ grupo` ∧ `status == "aprovado"`. **Nunca** por `disbursement_type`: o `_devolucao` de hoje usa `.first()` com `disbursement_type="cliente"` (`cancel_ops.py:361-372`), e é isso que o "Salvar" antigo de Gastos Extras estraga. `SpecialExpense.is_devolucao_cliente` (`models.py:1159-1162`) é código morto e reconhece pelo tipo: não usar.
- **Cheia** (FR-027), em **duas camadas**, porque o `_event_commission` de hoje (`comissoes_ops.py:766-796`) só zera venda nula, Loja Virtual e beneficiário com `receives_commission` falso; cortesia/permuta e "sem beneficiário" estão só no `should_have` (`:926-936`):
  - **`_base_da_comissao(event, settings, *, venda=None, taxa=None, bv_total=None, custo=None) -> Decimal`**: o corpo de hoje de `_event_commission`, **intocado**, com os insumos substituíveis (`None` = lido ao vivo, como hoje). A casca `_event_commission(event, settings)` continua existindo e a chama sem insumos: **não muda número** para nenhum dos seus consumidores;
  - **`_beneficiario_comissionado(event, settings) -> User | None`**: extraído de `should_have` (`:926-936`), sem `sale_value` e sem `is_cancelled`. Devolve `None` na Loja Virtual, sem beneficiário, com `receives_commission` falso e em cortesia/permuta;
  - **`comissao_cheia_do_evento(event, settings, *, venda=None, taxa=None, bv_total=None, custo=None) -> (cheia, beneficiario_id, taxa_usada)`**: passa **primeiro** por `_beneficiario_comissionado`; se der `None`, a cheia é 0 e o beneficiário é `None`; senão chama a base com os insumos congelados. É ela que o ato e `reaplicar_cancelado` usam. Assim, cortesia com valor e evento sem vendedor congelam cheia 0 (FR-027; linha "cortesia → cheia 0" da FR-049), sem mexer na DRE de hoje, que segue contando comissão em evento sem vendedor;
  - `_sync` passa a usar `should_have = event.sale_value and _beneficiario_comissionado(...) is not None` (R6).
  - **Os 8 consumidores da casca** (chamadas a `_event_commission` no HEAD): `_compute_drg` (`financeiro/routes.py:231`), a tabela de eventos do `dashboard()` Jinja (`:434`), `/vendas/` Jinja (`:1463`), a mesma tabela na API (`financeiro_read.py:402`), `vendas_ops.build_kpis` (`:290`), `vendas_ops.serialize_sale` (`:339`), `comissao_exibida_do_evento` (`comissoes_ops.py:403`) e `_sync_commission_payment` (`:937`). Nenhum muda.
  - **Verify**: o cenário 1 compara a **casca**, `main` × branch, em todo evento do espelho; o mesmo harness confere, de passagem, cheia == casca onde `_beneficiario_comissionado` passa (conferência auxiliar, fora da lista de variantes do R28). Variante no **16b**: cheia 0 em cortesia/permuta com valor e em evento sem vendedor, com a casca > 0 nos dois.
- **Comissão do retido** = `comissao_do_retido(cheia, retido, venda)` = `min(cheia, bv_que_acompanha(cheia, retido, venda))`. Dá 0 quando venda, retido ou cheia são ≤ 0. Exemplo: 90 × 400 ÷ 2.000 = **18**; com pago maior que a venda, dá a cheia.
  - A conta é a mesma do BV (`orcamento/quote_ops.py:58-85`, com a tolerância de R$ 0,01 e `ROUND_HALF_UP`). Assim, BV e comissão não divergem na borda.
- **No ato e depois:** a taxa usada fica congelada (R20). `commission_cost` segue **a mesma base de custo da comissão** (`comissoes_ops.py:786`): `_group_cost` quando o evento é principal de grupo, `_event_cost` no EducaManto que não é principal. É gravado só no EducaManto com responsável; `NULL` na comissão comum. Com a R15, o `_group_cost` do instante do ato soma os dias vivos, e no "todos" eles ainda estão todos vivos quando se congela (passo 5 do R2, antes de `cancelled_at`).

**Por quê.**
- FR-002: "nada é recalculado da venda viva, só do congelado".
- A extração tem de ser neutra, porque 8 chamadas leem a mesma regra.
- Pôr o portão de beneficiário dentro da base mudaria número na DRE de hoje (evento sem vendedor) e quebraria os cenários 1 e 23; deixá-lo fora da cheia congelaria comissão em cortesia com valor.

**Alternativas consideradas.**
- Uma camada só, "o núcleo de `_event_commission` sem mudar número": ou a cheia congela valor > 0 em cortesia e sem vendedor, ou a casca muda número.
- Fórmula própria de arredondamento: diverge da do BV na borda de R$ 0,01.
- Recalcular a cheia do evento vivo: proibido.
- Somar o devolvido por `disbursement_type`: frágil, pelo bug do "Salvar".

**Decisões do dono que amarram.**
- D14 ("sim, sobre o valor retido").
- D25 ("Proporcional").
- 1b-Q2 = A ("dividir de forma proporcional").
- 1e-Q2.

---

## R5: reconciliação por beneficiário e primeiro repasse aberto. [D14, D28, 1b-Q2 = A, Q16 = A, Q17 = A, P-10, P-12, FR-030…FR-033] + [R]

**Decisão.**

`reconciliar_comissao_do_cancelado(event, alvos: dict[int, Decimal], *, motivo, motivos: dict[int, str] | None = None, hoje=None, simular=False)` (`motivos` troca o motivo por beneficiário: a troca de vendedor da R20 leva dois motivos numa chamada só; motivo fora de `MOTIVOS_AJUSTE_COMISSAO` levanta `ValueError`) fica perto de `_comissao_existente` (`comissoes_ops.py:886`) e serve também ao principal **vivo** no corte.

**Beneficiários e alvo:**
- `alvos` = congelado → comissão do retido. Todo outro `seller_id` com linha viva do evento → **0**.
- Linhas marcadas com `NOTA_COMISSAO_PROPRIA_DO_DIA` ficam fora (R16).

**Conta, por beneficiário B:**
- `liquidadas_B` = Σ (`pago` + `no_banco`) das linhas do evento com `seller_id = B`.
- `falta = alvo_B − liquidadas_B`. Não é "Σ vivas": com a `a_pagar` dentro, a regra cancelaria a linha de 20 de um alvo de 20.
- `falta == 0` → toda `a_pagar` vira `cancelado`. Nunca fica `a_pagar` de R$ 0,00.
- `falta ≠ 0` → a `a_pagar` **mais antiga** (`ORDER BY id`) recebe a falta **no lugar, sem mudar data** (FR-032), e as demais são canceladas.
- Sem `a_pagar` → nasce uma linha com:
  - `event_id`, `event_title` e o valor (negativo no desconto);
  - `original_id` = a liquidada mais recente de B, se houver;
  - `sale_date = payable_from = primeiro_repasse_aberto(B, hoje)`;
  - **exceção**: a linha EducaManto **positiva** nova nasce com `payable_from` = data do evento, quando essa data ainda não passou (Q2 = A, "ficam na data original").

**Rastro:** toda linha criada ou ajustada leva o motivo como prefixo da nota (os prefixos de `MOTIVOS_AJUSTE_COMISSAO`, data-model §6; molde `_com_marca_do_ciclo`, `:842-848`) e um `audit("payment","commission",…)`. Não há marca de ciclo própria (R1: `NOTA_CICLO_CANCELAMENTO` não existe).

**Execução e prévia:** com `simular=False`, a função supõe T4 já tomada (R24). Com `simular=True`, devolve o efeito (ajuste, ciclo, `repasse_em`) sem tocar o ORM.

**`primeiro_repasse_aberto(seller_id, hoje, *, excluir_event_id=None, travar=False) -> date`:**
- `hoje = now_sp().date()`, sobre `ciclo_de_pagamento_expr()` (`:188-216`).
- Candidatos, em ordem:
  1. M−1, só se `hoje.day ≤ DIA_DO_REPASSE` **e** B tem ali uma linha que abre ciclo;
  2. senão M, se não está liquidado;
  3. senão M+1… (no máximo 24 ciclos; sem achar, o 25º, que é futuro: nunca reabre um liquidado).
- "Liquidado" = B tem linha no ciclo e nenhuma abre ciclo.
- A data devolvida é `hoje` presa ao intervalo do ciclo. Esse é o único arranjo em que a Planilha (`coalesce`) e Comissões (`sale_date`) mostram o mesmo sem tocar `_month_scoped_query`.
- `excluir_event_id` tira as linhas do próprio evento. Assim, o autoflush das linhas recém-ajustadas não muda a resposta entre prévia e execução.

**Linha nova sem liquidada** vai ao beneficiário **congelado**. O ajuste de linha liquidada vai a quem a recebeu (P-12).

**Evento com venda e sem linha de comissionado** ganha a linha no cancelamento. Vendedor sem `receives_commission` dá cheia 0, e nada nasce.

**Por quê.**
- O estorno de hoje copia `sale_date`/`payable_from` da venda (`cancel_ops.py:157-168`) e cai num repasse que já saiu (o estorno 211 nasceu em 17/09 com data de 21/08).
- O limite no dia 5 reproduz "cancelado em 02/10 sai no repasse de 05/10".

**Alternativas consideradas.**
- `payable_from = hoje` com `sale_date` herdado: certo na Planilha, errado em Comissões.
- Mudar o eixo de `_month_scoped_query`: três cópias mais o Jinja.
- Procurar o primeiro ciclo não liquidado sem limite: cairia em ciclos antigos nunca marcados.
- Sempre o mês do cancelamento: erra nos dias 1 a 5.
- Linha negativa somada a outra: proibido (FR-033).

**Decisões do dono que amarram.**
- D14: "Se os R$ 100 cheios já foram pagos, o próximo repasse desconta R$ 80".
- D28 ("Acompanham").
- 1b-Q2 = A ("ficam na data original").
- Q16 = A: "saldo negativo em uma comissão futura desse vendedor… tudo bem auditado".
- Q17 = A: correção da taxa para mais e para menos.
- 1e-Q8 = B: desconto sem repasse futuro fica a pagar.

---

## R6: sincronização automática, predicados únicos e as telas de Comissões e Planilha. [FR-031, FR-034, FR-035, FR-037, FR-038] + [R]

**Decisão.**

- **`_sync_commission_payment`** (`comissoes_ops.py:914-986`):
  - `if event.is_cancelled: return` logo depois do retorno da Loja Virtual (`:918-921`);
  - sai o `and not event.is_cancelled` de `should_have` (`:930-932`), com o comentário reescrito;
  - `should_have` passa por `_beneficiario_comissionado`;
  - **regra nova da FR-057** (R14): evento **vivo** com ajuste vivo (`original_id` → linha do próprio evento) cuja original voltou a `a_pagar` → sincroniza por `reconciliar` com alvo = cheia, em vez de regravar a base em `:963-975`.
- **`_comissao_existente`** (`:886-911`) passa a filtrar `original_id IS NULL` e a ignorar `NOTA_COMISSAO_PROPRIA_DO_DIA`. O filtro de zero pago da 299 fica. Com isso, ajuste e estorno nunca são tomados por "a comissão do evento" (FR-034, FR-057).
- **`_resync_pending_commissions`** (`:989-1011`): hoje roda em todo GET de Comissões e da Planilha (`financeiro/routes.py:1024`, `:1492`; `financeiro_read.py:566`, `:670`) e commita uma vez no fim (`:1011`). Passa a:
  - percorrer os eventos em ordem de id;
  - travar cada um com `FOR NO KEY UPDATE SKIP LOCKED` (não segura a inserção de comprovante);
  - reler `cancelled_at`;
  - pular o travado;
  - **commitar por evento**.

  Isso fecha a metade "sync com o evento lido antes" do cenário 30, sem esperar o ato (R24).
- **Predicados**, cada um numa função:
  - `filtro_estorno_orfao()`: `event_id IS NULL ∧ original_id IS NOT NULL ∧ amount < 0 ∧ a_pagar`. Usado por `_pending_reversals_query` (`:434-450`) e pela cópia `reversal_ids` (`:548-553`). Só o órfão entra pelo resgate do mês corrente; a 1e acrescenta ali a linha de saldo dela.
  - `linha_abre_ciclo` (Python e SQL): `a_pagar` ∧ `amount ≠ 0` ∧ não órfão. Só em `primeiro_repasse_aberto`.
  - `month_status` (`:573`) = "pendente" se houver `a_pagar` com valor ≠ 0, **órfão incluído**. Assim, o mês cuja única pendência é um estorno órfão não perde o "Pagar Mês" (FR-038).
  - No builder (`financeiro/routes.py:950-952`), o `continue` vale só no grupo **aberto** e só quando nenhuma linha (`a_pagar`/`no_banco`) tem valor ≠ 0. O grupo `:pago` de soma 0 continua escondido (regressão `main` × branch).
- **`no_banco`** entra em `_month_scoped_query` (`:410`), na cópia `month_ids` (`:533`) e em `STATUS_LABELS` (`:31-35`). `CommissionKpis` (`:78`) e `get_month_kpis` (`:581`) ganham `total_no_banco`, e `total_month` = pago + no banco + a pagar.
- **`CommissionEntry`** (`:47`) e `_to_entry` (`:453-465`) ganham `tipo`, `original_id`, `evento_cancelado` (uma consulta em lote por mês), `ciclo` e `motivo`, todos com valor padrão.
  - `tipo_da_linha(cp)` devolve comissão, ajuste ou estorno, mais o motivo pelo prefixo.
  - `ciclo_de_pagamento_da_linha(cp)` é espelho de `:212-216`, com `created_at.date()` **em UTC**, como o `date()` do SQL. O verify compara os dois em todo o espelho.
- **`sale_count`** (`:570`) só de `original_id IS NULL`. Isso muda os meses históricos com estorno legado, e a mudança vai ao `docs/03`.
- **`order_by(CommissionPayment.id)`** em `liquidar_periodo` (`:249-257`) e `pay_seller_month` (`:631-638`) (R24).
- **Planilha.** `_build_commission_items` (`financeiro/routes.py:904-975`) ganha a chave `linhas` (tipo, evento, valor, ciclo, status) **nos dois itens**, o aberto e o `:pago`, com `tipo_da_linha` por import tardio. `_serialize_pagamento_item` (`financeiro_read.py:598-643`) passa a mandar `commission_lines`.
- **Os dois literais 5** (`financeiro_read.py:720`; `financeiro/routes.py:1072`) ganham comentário apontando `DIA_DO_REPASSE`, sem refatorar.
- **Jinja `set_commission_status`** (`financeiro/routes.py:1561-1582`): ganha a **guarda de uma linha**. Linha cujo evento está cancelado (`cp.event is not None and cp.event.is_cancelled`) → `flash` "Comissão de evento cancelado: o valor se acerta pelo cancelamento e o pagamento pela Planilha de Pagamentos." e redirect, sem trocar status. Hoje a rota recusa só pago → x (hotfix 267c) e deixa `a_pagar` ↔ `cancelado` e `a_pagar` → `pago` em qualquer linha: no cancelado, isso quebraria a invariante Σ = alvo **fora do caminho único** (reconciliação + Planilha nova). O estorno órfão (`event_id` nulo) não é alcançado. O arquivo entra na lista do plan.

**Por quê.**
- Sem a guarda, abrir Comissões ou a Planilha rodaria `_sync` sobre a linha do retido. `should_have` falso a cancelaria (`:944-948`), e a Σ cairia.
- O ajuste do corte (`a_pagar` com `event_id`) seria tomado por `_comissao_existente` (o de id maior vence) e regravado com a cheia.
- A tela Jinja de Comissões só é alcançável pelo host do backend, mas o Financeiro a tem; a guarda custa uma linha e fecha a única porta que reescreve linha de cancelado.

**Alternativas consideradas.**
- Um predicado só para `month_status` e `abre_ciclo`: tiraria o "Pagar Mês" do mês com só órfão, mudando linha antiga.
- Travar o evento inteiro no resync com `travar_evento`: seguraria cerca de 72 eventos até o commit do GET.
- Filtros novos na tela Jinja `comissoes()` (`financeiro/routes.py:1505-1541`): fora (P-45, dívida).
- Deixar `set_commission_status` como dívida: era o rascunho; a guarda de uma linha é mais barata que a dívida.

**Decisões do dono que amarram.**
- 1b-Q3 = A e 1b-Q7: passado quieto.
- Q16 ("tudo bem auditado pela tela das comissões").
- D14.

---

## R7: exclusão recusa o cancelado e põe o estorno no ciclo certo. [D23, "Apaga como hoje" (30/09), 1b-Q3 = A, P-11, P-40, FR-021, FR-036] + [R]

**Decisão.**

- **`_delete_event_flow`** (`calendar/routes.py:4348-4382`): trava o evento (`FOR UPDATE` + `populate_existing`) e relê. Recusa o cancelado com `EventoCanceladoError`, irmã de `EventoMarcadoError`, **antes** da checagem do líder (`:4372`).
  - A rota Jinja `delete_calendar_event` (`:4474`) mostra a recusa por `flash`.
  - `api_delete_event` (`agenda_write.py:534-574`) recusa **antes** da condição `not is_google_missing and not pode_excluir` (`:555`), com 409 e `codigo: "cancelado"`. Hoje o cancelado com dinheiro leva "use o cancelamento", que é falso, e o cancelado vazio é apagado.
  - A trava fecha também a **dívida 101** (deadlock entre `_delete_event` e o PUT de acréscimos).
- **Sync de evento vazio.** `sumico_ops._apagar_vazio` (`:341-356`) trava o evento e relê `cancelled_at` antes de `_delete_event`. Se o evento foi cancelado no meio, desiste.
  - `_decidir_candidato` (`:399-431`) carrega o evento antes da consulta ao Google e não reconfere.
  - `_candidatos` filtra cancelado (`:447`), mas só no início do mês.
- **`aplicar_estorno_comissao`** (`cancel_ops.py:146-173`), caminho só da exclusão depois da H2 (`calendar/routes.py:339-341`):
  - ramo `no_banco` igual ao do `pago`;
  - `sale_date = payable_from = primeiro_repasse_aberto(...)`, por import tardio;
  - nota "Exclusão do evento";
  - docstring reescrita.

  O estorno continua órfão (`event_id` nulo). Os estornos 151 e 211 não são tocados.

**Por quê.**
- A recusa só na API não fecha a rota Jinja, que não passa por `pode_excluir`.
- O sync apagaria o cancelado "vazio" e, por cascade, o congelamento.
- Sem o ciclo certo, o estorno da exclusão "não sai de repasse nenhum" (contraria a D23).

**Alternativas consideradas.**
- Recusar só na API: a rota Jinja e o sync escapam.
- Recusar o cancelamento de evento vazio: o vazio pode ter contrato.
- Deixar o estorno da exclusão no ciclo da venda e registrar como dívida: contraria a D23 e a resposta de 30/09.

**Decisões do dono que amarram.**
- "Apaga como hoje" (30/09), com o estorno saindo.
- D23 (224g).
- 1b-Q3 = A.
- P-40: cancelar não tem volta.

---

## R8: BV do retido proporcional e o congelado na Planilha. [1b-Q2 = A, Q10 = A, P-15, P-48, FR-039, FR-040, FR-010] + [R]

**Decisão.**

- **`bv_do_retido(cheio, retido, venda)`** = `min(cheio, bv_que_acompanha(cheio, retido, venda))`, com retido ≤ 0 dando 0. Exemplo: 200 × 400 ÷ 2.000 = **40**. É calculado ao vivo e **nunca gravado**.
- **`bv_da_planilha(acrescimo)`**:

  | Situação | Valor |
  |---|---|
  | evento vivo | `amount_brl` |
  | `venda` com linha congelada, pago ou no banco | `paid_amount`; se nulo, `amount_brl` (só na janela do backend velho) |
  | `venda` com linha congelada, não pago | `bv_do_retido(original_amount, retido, venda)`; `None` se zero |
  | sem linha congelada (`legado`, `satelite`, `dia`, `virtual`) | `amount_brl` se pago ou no banco; senão `None` |

  Todo leitor (este, o resumo, a base da cheia) soma **só linhas com `acrescimo_id` não nulo**, como cinto contra órfã criada por `SET NULL`.
- **Planilha.**
  - `_build_bv_items` (`financeiro/routes.py:870-901`) passa a usar `amount = bv_da_planilha(a)`, por import tardio de `cancel_ops`. `None` pula o item.
  - Os resumos saem em lote a partir de `bv_rows`, sem N+1.
  - As duas consultas de BV (`financeiro/routes.py:1056-1066`; `financeiro_read.py:706-714`) **não mudam**: o BV fica no **mês do evento**, com recebedor e PIX do acréscimo, e o "sem PIX" de `:893-899` continua.
- **No ato** (`_validar_pix_do_bv`, regime `venda`):
  - todo BV não pago com proporção > 0 exige recebedor e PIX, do acréscimo ou de `bvs[]`;
  - a validação é `erros_do_bv` (`orcamento_evento_ops.py:406-417`, limites 200 e 140), e faltando dá 400 `bv_pix_<acrescimo_id>`;
  - o que vem no corpo é gravado no acréscimo, sob T3 e antes do congelamento, e copiado para `event_cancellation_bvs`;
  - o congelado guarda `original_amount = amount_brl` do instante do ato (no vivo ele acompanha a venda desde a 305), `paid_at_cancellation = status ∈ {pago, no_banco}` e, se verdadeiro, `paid_amount = amount_brl`.
- **Base da cheia no cancelado** = venda − Σ `original_amount` das linhas congeladas vivas. **Nunca** `_event_bv_total` ao vivo (`comissoes_ops.py:733-743`).
- **A DRE** lê "o BV do retido (ou o pago)" pela mesma função, através do resumo (R21).

**Por quê.**
- Fecha o risco aceito da 305: cancelar e recriar do mesmo orçamento listava dois BVs.
- Tira da Planilha o BV não pago de satélite, dia e virtual (D23).
- O BV pago nunca some (FR-040).

**Alternativas consideradas.**
- Gravar o proporcional no acréscimo: `value` e `amount_brl` divergem, `_event_bv_total` erra, e o editor da 305 o mostraria como cheio.
- Deixar o BV não pago de satélite e virtual pelo cheio: contraria a D23.
- Ajuste manual: saiu (1b-Q6).

**Decisões do dono que amarram.**
- 1b-Q2 = A ("o BV também é cancelado… se sobrar, dividir de forma proporcional… ficam na data original").
- 1b-Q10 = A: a multa não muda o BV.
- Regra do PIX da 3a ("extrema importância… obrigatório o PIX").
- 30/09: o pago fica.

---

## R9: BV pago depois do ato, com `paid_amount` e uma função única para marcar BV. [L10, 1e-Q5 = A] + [R], decisão (a)

**Decisão.**

`cancel_ops.marcar_status_do_bv(acrescimo_id, status, *, valor_esperado, actor_name)` é chamada pelas **duas** portas:
- a API (`financeiro_write.py:163-194`);
- o Jinja (`financeiro/routes.py:1190-1197`).

São os únicos dois escritores de `bv_payment_status` além da criação (`orcamento_evento_ops.py:496`).

**Ordem dentro da função:**
1. lê o acréscimo sem trava;
2. `travar_evento(acr.event)`, ou seja, **o evento primeiro** (docstring de `orcamento_evento_ops.py:788-793`);
3. relê o acréscimo com `FOR UPDATE` + `populate_existing`;
4. relê `EventCancellation` e `EventCancellationBv` com `populate_existing`;
5. `atual = bv_da_planilha(acr)`.

**Ao marcar pago ou no banco:**
- `atual is None` → 409 `bv_nao_esta_a_pagar`, "Este BV não está a pagar: recarregue a Planilha.";
- `valor_esperado` diferente de `atual` → 409 `valor_mudou` (`CODIGO_VALOR_MUDOU`, R1) com a frase da 305, trocando o valor por `atual`. É o 409 que a 305 já dá sem `codigo`: ganha o código, e a mensagem não muda.

**Transições:**
- `nao_pago` → pago ou no banco: `paid_amount = atual`;
- entre pago e no banco: `paid_amount` não muda;
- → `nao_pago` (desfazer): `paid_amount = None`. O BV volta ao proporcional (FR-039: "pago nunca reescrito" só vale enquanto está pago);
- toda transição grava `audit` com o valor.

`reaplicar_cancelado` **nunca** toca `paid_amount`. A correção posterior não reescreve o pago nem gera acerto ao parceiro. Resumo, custo da DRE e Planilha leem a mesma função.

**Verify**: variante **16/17-`paid_amount`** (não é cenário novo): BV pago depois do ato fica pelo pago numa correção posterior; desfeito, volta ao proporcional.

**Por quê.**
- O ramo de hoje compara `valor_esperado` com `acr.amount_brl`, que é o cheio (`financeiro_write.py:172-183`). O React manda `valor_esperado: item.amount` (`PagamentoItemViews.tsx:112-116`), que passa a ser o proporcional: **todo "pago" de BV de cancelado daria 409 para sempre**.
- O ramo Jinja não trava nem confere nada, e a FR-040 vale "nova e antiga".
- `EventAcrescimo` não tem valor pago (`models.py:1841-1868`), e a spec proíbe coluna nova ali.
- Na ordem evento → acréscimo, o "pago" concorrente se serializa com o ato, que congela `paid_at_cancellation` sob a mesma trava.

**Alternativas consideradas.**
- Regravar `amount_brl` com o proporcional: `value` e `amount_brl` divergem, `original_amount` deixa de bater, o editor da 305 congela 40 como cheio, e o desfazer não tem como voltar.
- Coluna em `event_acrescimos`: vetada.
- Ler o pago do `AuditLog`: não é consultável.
- `paid_amount` só depois do ato, com `paid_at_cancellation` lendo `amount_brl`: duas fontes para o mesmo fato.
- Travar só o acréscimo, como a 305: ordem inversa à de `substituir_acrescimos` e `acompanhar_bv_da_venda`, com risco de deadlock.

**Decisões do dono que amarram.**
- L10: "fica pelo valor pago… não gera acerto ao parceiro".
- 30/09: o pago não se mexe.
- 1e-Q5 = A: o desfazer existe para corrigir engano.

---

## R10: imposto sobre o retido. [D32, FR-009] + [R]

**Decisão.**
- **Só com nota** (`with_invoice` congelado), `imposto_retido` é obrigatório: reais ≥ 0, 400 `fields.imposto_retido` se faltar ou for inválido.
- O campo nasce vazio. A referência `imposto_aliquota` vem do servidor por `_get_tax_rate(settings)` (`financeiro/routes.py:129-132`; `DEFAULT_TAX_RATE = 16`, `:112`; `tax_rate` é nulo no espelho), que é a mesma régua da DRE do evento vivo. A referência é `imposto_aliquota` × retido ao centavo (`ROUND_HALF_UP`), e o rótulo da tela mostra a alíquota recebida, não o literal 16 (o "16% do retido" da D32 é o valor de hoje). A tela mostra "16% do retido" só como referência.
- **Sem nota**, o bloco não aparece, e `imposto_retido` **enviado** no corpo dá **400 `fields.imposto_retido`** (não é ignorado). O mesmo no corte de um dia e, no `PATCH …/devolucao`, no `dia` e no `legado`. É o que dizem o RBAC da spec e os contratos §1 e §3.
- O valor é gravado em `retained_tax`. A DRE lança o **gravado**, nunca alíquota × retido (FR-041).
- Pode ser regravado pelo "Alterar devolução" (R12), só no `venda` com nota. Lá, o 400 do imposto vem **depois** das travas, porque o regime e a nota só se leem depois de T1 (ordem dos contratos §3).

**Por quê.** D32 ("Depende da negociação"). Uma alíquota só no sistema evita uma segunda constante de 16%. Recusar o imposto sem nota, em vez de ignorá-lo, impede que um bundle errado grave imposto onde não há nota sem ninguém ver.

**Alternativas consideradas.**
- Calcular o imposto: contraria a D32.
- Constante própria de 16%: duas fontes.
- Ignorar o imposto sem nota (rascunho desta pesquisa): diverge da spec e dos contratos, e esconde o erro do cliente.

**Decisões do dono que amarram.** D32; 1b-Q2 não mexeu nisso.

---

## R11: devolução nasce no ato e fica travada em Gastos Extras. [D22, D27, P-17, P-19, FR-008, FR-019, FR-020] + [R]

**Decisão.**

- **`_registrar_devolucao(event, devolucao, actor, *, complemento=False)`** (`cancel_ops.py:176-209`):
  - continua criando o gasto **direto no ORM**, aprovado e a pagar, com categoria "Devolução a cliente", `disbursement_type="cliente"`, nome, PIX (`supplier_pix` de 120), `event_id` e `expense_date` = data de São Paulo do ato;
  - ganha o teto (≤ pago do grupo − já devolvido) e nome e PIX obrigatórios em Tudo e Parte;
  - **não** passa por `create_expense`, que nasce pendente e manda e-mail ao Financeiro (`gastos_ops.py:256-318`).
- **Gastos Extras travados** (`gastos_ops.py`):
  - **erros e predicado**: `GastoLockedError(field, message, event_id)`, ao lado de `:47-57`; `devolucao_de_cancelado(expense)` = categoria devolução ∧ `event_id` ∧ evento cancelado;
  - **trava antes de decidir**: `travar_evento` antes de decidir, e o gasto relido com `with_for_update().populate_existing()`. No vincular, os dois eventos em ordem de id;
  - **`_validate_expense_data(…, tipo_atual=None)`** (`:194-238`): o tipo `cliente` só com `tipo_atual == "cliente"`; senão 400 "Devolução à cliente nasce pelo cancelamento do evento". Hoje o `else` zera tipo, nome e PIX (`:237-238`);
  - **`create_expense`** (`:256`): categoria devolução + evento cancelado dá 409 `event_id`, comparando com a categoria **já normalizada**;
  - **`approve_expense`** (`:321`) e **`reject_expense`** (`:333`): 409 antes do teste de estado;
  - **`delete_expense`** (`:356`): 409;
  - **`link_expense_to_event`** (`:363`): 409 quando o vínculo atual é devolução de cancelado, e no caminho inverso; `event_id` normalizado para `int`;
  - **`edit_expense`** (`:381-442`):
    - a trava roda **antes** das atribuições de `:420-428`;
    - valor (quantizado), `expense_date`, categoria ou `event_id` **diferentes** do gravado dão 409;
    - **caminho inverso**: o predicado `devolucao_de_cancelado` vale para o gasto gravado **e** para o gasto como ficaria com a categoria e o `event_id` do corpo. Categoria trocada para devolução num gasto ligado a cancelado (multa inclusive) → 409 `fields.category`; devolução viva religada a cancelado → 409 `fields.event_id`. Com `event_id` trocado, os dois eventos travam em ordem de id, como no vincular;
    - o tipo `cliente` fica mesmo com corpo `""` ou `"fornecedor"`;
    - nome e PIX só trocam com valor não vazio;
    - nunca acende `approved_with_edits`;
    - `aprovar=True` é recusado.
- **`gastos_write.py`.** Os seis endpoints capturam a exceção com `json_error(msg, 409, fields={campo: msg}, event_id=…, codigo=devolucao_travada)` e `db.session.rollback()` explícito. Hoje o DELETE não tem `try`, e a exceção nova viraria 500.
- **Ordem porta a porta**, como está no HEAD (o gate de hoje não muda; a 306 só acrescenta o que vem depois dele):

  | Porta | HEAD | Depois da 306 |
  |---|---|---|
  | `POST /api/gastos` (`gastos_write.py:47`) | 401 → **sem gate de papel** → salva o comprovante (`:53-57`) → evento resolvido (`:72`) → núcleo (400) | o mesmo, e o núcleo acrescenta 400 `fields.disbursement_type` (tipo `cliente`) e, depois da trava, 409 `devolucao_travada` `fields.event_id` (devolução ligada a evento cancelado) |
  | `POST …/aprovar` (`:80`) | 401 → 403 (`_require_financeiro`, `:84-86`) → 404 (`:87-89`) → 409 de estado | 401 → 403 → 404 → trava → 409 `devolucao_travada` → 409 de estado |
  | `POST …/rejeitar` (`:97`) | 401 → 403 → 404 → 409 de estado | igual ao aprovar |
  | `PATCH /api/gastos/<id>` (`:115`) | 401 → 403 → 404 → 409 de estado (rejeitado sem `aprovar`, `gastos_ops.py:402-405`) → 400 (validação, `:407`) | 401 → 403 → 404 → 409 de estado de hoje → 400 (validação; tipo `cliente`) → trava → 409 `devolucao_travada` |
  | `DELETE /api/gastos/<id>` (`:151`) | 401 → **404 (`:158-160`) antes do 403** (`:161-165`: Financeiro, ou autor do pendente) → exclui, **sem `try`** | 401 → 404 → 403 → trava → 409 `devolucao_travada` |
  | `POST …/vincular-evento` (`:170`) | 401 → 403 → 404 → 400 | 401 → 403 → 404 → 400 → trava (os dois eventos por id) → 409 `devolucao_travada` |

  No `POST /api/gastos`, a recusa nova (e a 400 de hoje) acontece depois de o comprovante ser salvo em disco: o arquivo fica órfão, como já fica hoje na 400 (Riscos aceitos, 20).
- **`gastos_read._expense_dict`** (`:31-57`) ganha `locked` e `event_cancelled`, sem consulta nova: `e.event` já é carregado em `:52`.
- **Planilha.**
  - O estado (pago, no banco, desfazer) segue pela Planilha, fora da trava (FR-019).
  - **`valor_esperado` também no item `expense`: ADOTADO**, ponto firme da Living Spec (R30). Hoje o bundle só manda `valor_esperado: item.amount` quando `item.type === "bv"` (`PagamentoItemViews.tsx:112-116`); o `PagamentoItemViews` **muda** e passa a mandá-lo para `bv` **e** `expense`. O servidor (`financeiro_write.py:147-161`) trava o evento, relê o gasto e confere só quando o gasto é devolução de cancelado: diferente → 409 `valor_mudou` "A devolução mudou para R$ X desde que a Planilha abriu: recarregue e confira antes de marcar.". Sem o campo (bundle antigo), comportamento de hoje.
  - **Jinja `set_payment_status`**, ramo de gasto (`financeiro/routes.py:1182-1189`): passa a **travar o evento** (e reler o gasto) quando o gasto é devolução de cancelado, para serializar com o "Alterar devolução". Não confere valor, porque o Jinja não manda `valor_esperado`. O arquivo entra na lista do plan.
  - **Lote** (API `financeiro_write.py:326-338`; Jinja `financeiro/routes.py:1397-1404`): sem conferência de valor (Riscos aceitos, 8).
- **`models.py`**, só texto: os comentários de `:1066-1069`, `:1091` (incluir "cliente") e `:1114-1117`.

**Por quê.**
- Qualquer "Salvar" de hoje apaga destinatário, nome e PIX.
- Sem a trava, editar o valor da devolução muda o retido sem `reaplicar` (a guarda do `_sync` impede o conserto depois).
- Sem `valor_esperado`, um "pago" vindo de uma Planilha aberta antes grava pago sobre o valor novo (300 → 30).

**Alternativas consideradas.**
- Entidade própria para devolução: Gasto Extra já tem aprovação, PIX e estado.
- Trava por papel: a FR-019 diz por gasto.
- Recusar a presença do campo, e não a diferença: quebraria o "Salvar sem mexer" do bundle antigo.

**Decisões do dono que amarram.**
- D22.
- D27.
- D28: a devolução que muda refaz as contas, mas só pelo caminho próprio.
- P-19: só o "Alterar devolução" escreve na devolução do cancelado.

---

## R12: "Alterar devolução" no regime `venda` e no dia cortado. [D28, D36, clarify de 15/10 = A, L9, FR-017] + [R], decisão (e)

**Decisão.** `alterar_devolucao(event, *, devolucao_total, nome, pix, observacao, imposto_retido, actor)` decide pelo regime **depois** de travar. A ordem e os códigos são os dos contratos §3; o regime só se lê depois de T1, então nada que dependa dele vem antes da trava.

1. **401 → 404 → 403** (`pode_editar_venda_do_cancelado`).
2. **Antes da trava, só**: `devolucao_total` ausente ou não numérico → 400 `fields.devolucao_total`.
3. **Travas**, na ordem numerada de R24: T1 (grupo inteiro), T2, depois T4, só no `venda` e no `dia` cujo principal já foi cancelado em `venda` (os beneficiários se conhecem depois de T2), e por fim T5 (devoluções do grupo, pendentes inclusive, `FOR UPDATE` + `populate_existing`, por id). É T4 antes de T5, como no ato.
4. **409 `nao_cancelado`**: "Este evento não está cancelado."
5. **409 `regime_sem_retido`**: `satelite` e `virtual`.
6. **400 `fields`**, todos de uma vez:
   - `devolucao_total`: negativo; no `venda`/`legado`, **acima do pago** do grupo (é 400, não 409);
   - `devolucao_nome`, `devolucao_pix`: faltando quando nasce complemento sem nome ou PIX a herdar, ou acima de 200/120 caracteres;
   - `imposto_retido`: no `dia`, no `legado` ou sem nota (R10), e quando negativo.
7. **409 `abaixo_do_piso`**, com o extra `piso`: abaixo do piso de cada regime (os limites logo abaixo; no `venda` em grupo, também as aprovadas dos dias `dia`; no `dia`, também a devolução mínima do corte, P-52).
8. **409 `acima_do_teto`**, com o extra `teto`: **só no `dia`**, acima do pago do grupo menos as devoluções aprovadas dos outros dias.
9. Grava; deadlock vira 409 `tente_de_novo`.

**Limites**:
- `venda`/`legado`: piso = devoluções pagas ou no banco de todos os dias + as aprovadas dos dias `dia`; teto = pago do grupo (acima dele, 400 do passo 6);
- `dia`: piso = o maior entre as devoluções **daquele dia** pagas ou no banco e a devolução mínima do corte, recalculada com a venda nova congelada na linha `dia` (P-52); teto = pago do grupo − devoluções aprovadas dos **outros** dias, vivos e cancelados (acima dele, 409 do passo 8).

**Como grava**:
1. **Gravação** pelo helper único `_aplicar_novo_total(dono, …)`:
   - a devolução aberta absorve a diferença e fica uma só; se zerar, é excluída com auditoria (`gastos_ops._log`, `:85`);
   - sem aberta e acima do piso, nasce o complemento ligado ao dono (data de hoje, Planilha do mês em que nasce);
   - regrava `disbursement_type="cliente"` e completa nome e PIX vazios (FR-020).

   Escreve direto no ORM, por ser o **único escritor** da devolução travada. Não regrava `refund_mode`.
2. **`venda`**: regrava o imposto se vier; `reconciliar` (retido novo, sob a T4 já tomada nas travas) → `updated_at/by` → `EventLog` (UTC).
3. **`dia` com o principal vivo** (o caso do clarify de 15/10):
   - **não** chama `reconciliar` nem `acompanhar_bv_da_venda`;
   - **não** toca o `sale_value` do principal nem `sale_value_before/after`;
   - grava só `updated_at/by` da linha `dia`, um `EventLog` no dia e `audit` por devolução;
   - o "já devolvido" e a cobrança da Home são lidos ao vivo (R22).
4. **`dia` com o principal cancelado inteiro depois** (`venda`): a devolução do dia passa a ser devolvido **daquela venda** (FR-004: o devolvido é do grupo). Faz-se a mesma conta do passo 3 e, além dela, `reaplicar_cancelado(principal)`, sob a T4 já tomada nas travas, que **refaz o retido e a comissão do principal**. A regra é "refaz-se o cancelamento que lê aquele dinheiro".
   - **De onde vem**: é **derivado da D28** do dono ("Acompanham": retido, comissão e BV acompanham a devolução), não da resposta do clarify. O clarify (A, "não mexe em comissão") foi dado sobre o grupo **vivo**, "o resto do grupo segue vivo", e só vale enquanto isso é verdade. Depois que o principal foi cancelado, não refazer deixaria o retido do principal contando uma devolução velha.
   - **Living Spec**: entra como **6º ponto** (FR-017 "no dia cortado" + FR-004), com uma **variante do cenário 39**: depois de cancelar o resto do grupo, "Alterar devolução" do dia refaz o retido e a comissão do principal (R30).
   - No `venda` em grupo, a devolução aberta do principal absorve a diferença primeiro e, depois dela, as abertas dos dias `satelite` (lançadas antes do ato), por id; as aprovadas dos dias cortados (`dia`) contam no piso como fixas, e as pagas ou no banco de todos os dias também.
5. **Resposta** `{ok, resumo}`, com piso e teto no resumo (o diálogo os mostra). A prévia não trava.

`_devolucao` (`cancel_ops.py:361-372`, `.first()` por tipo) passa a `filtro_devolucao`, com todas as devoluções na página de Cancelamentos.

**Por quê.**
- É o que pedem a FR-017, o RBAC do `PATCH …/devolucao` e o cenário 38.
- Sem isso, uma Parte digitada errada no corte ficava para sempre na Planilha e na cobrança.
- Duas chamadas simultâneas a "Nada → 300" geram um complemento só, porque T1 serializa e T5 relê.
- A ordem do rascunho ("400 do imposto antes de tudo", "fora dos limites → 409") era impossível (o regime só se lê depois de T1) e divergia dos contratos §3 e do RBAC da spec, que dão 400 `devolucao_total` acima do pago no `venda`/`legado` e 409 só abaixo do piso e, no `dia`, acima do teto.

**Alternativas consideradas.**
- Corrigir pela porta do principal: o principal vivo não tem cancelamento.
- Refazer a comissão do principal no `dia` com o principal vivo: contraria o clarify.
- Não refazer o principal cancelado depois: contraria a D28 e deixa o retido errado.
- Levar o caso ao dono como pergunta de uma linha: a D28 já responde; fica registrado na Living Spec para ele ver.
- Corrigir por Gastos Extras: travado pela FR-019.

**Decisões do dono que amarram.**
- D28 ("Acompanham"), que também decide o caso do principal cancelado depois.
- D36 ("só o Superadmin").
- Clarify de 15/10, resposta "A": "o novo total é o da devolução daquele dia… não mexe em comissão", com o grupo vivo.

---

## R13: comprovante de evento cancelado, inclusive em dia de grupo. [D36, P-18, P-27, FR-018] + [R], decisão (c)

**Decisão.** Uma sequência só nas três portas da API: `api_add_payment` (`agenda_write.py:1747`), `api_edit_payment` (`:1778`) e `api_delete_payment` (`:1803`).

1. 404, depois o gate de hoje (403): POST por `_can_edit_event` (`:1754`); PATCH e DELETE por `_is_superadmin` (`:1784`, `:1809`).
2. `travar_grupo(event)` (T1), depois relê `is_cancelled`.
3. Cancelado e não Superadmin real → 409 `cancelado`, **antes** de `_add_payment_record`, que salva o arquivo antes (`calendar/routes.py:1132-1155`, o arquivo em `:1150-1152`). Assim a recusa do papel não deixa arquivo órfão.
4. Grava, faz `flush` e chama `cancel_ops.reaplicar_por_dinheiro(event)`:
   - `principal = principal_da_venda(event)` (`cobranca_ops.py:224-228`), já travado em T1; pago e devolvido saem do **grupo inteiro**, pelos ids de T1 lidos por consulta (R4), nunca por `leader.satellites`;
   - pago do grupo menor que o devolvido → rollback + 409 `pago_abaixo_do_devolvido`, com `pago` e `devolvido` (só no editar e no excluir);
   - principal `venda` cancelado → `reaplicar_cancelado(principal, motivo="Cancelamento: comissão do retido")`: refaz o retido e reconcilia (T4); o BV proporcional é ao vivo; o pago fica (R9); grava `updated_at/by` e um `EventLog` no dia e no principal;
   - principal vivo (regime `dia`, inclusive o antigo 1º dia depois da passagem) → **nada se refaz**: o congelado do dia nunca muda por comprovante; a cobrança e o "já devolvido" são ao vivo;
   - `legado` e `virtual` → só a guarda de pago abaixo do devolvido;
   - o `satelite` sempre cai no ramo `venda`.
5. Commit. A resposta é o **detalhe** do dia, com `cancelamento` dentro.
6. **Arquivo órfão, só no POST.** Se o POST termina em 409 **depois** de `_add_payment_record` (`tente_de_novo` no deadlock, ou `grupo_mudou`), a view faz rollback e **remove o arquivo** que ele acabou de salvar. O PATCH só troca `amount` (`calendar/routes.py:1159-1164`, `_edit_payment_amount`) e não recebe arquivo; o DELETE não salva nada. O 409 `pago_abaixo_do_devolvido` só existe no editar e no excluir, então não deixa arquivo.
7. A tela invalida `["event"]` (o principal também mudou) e as chaves do financeiro. Hoje `useEventMutation` (`lib/eventAttachments.ts:46-60`) só invalida `["dashboard"]`.
8. **Jinja**: os três handlers (`calendar/routes.py:1050`, `:1085`, `:1111`) recusam o cancelado com `flash`, pela recusa única no despachante (R19). P-27 confirmada.

**Verify**: o cenário novo **37b** (comprovante de 200 num satélite → retido e comissão do principal refeitos) e a variante **38-comprovante** (comprovante no dia `dia` com o principal vivo → nada refeito; a guarda de pago abaixo do devolvido funciona).

**Por quê.**
- O pago de um cancelamento é do grupo (FR-004). Um comprovante no satélite muda o retido do principal.
- `api_add_payment` aceita satélite e não trava nada.
- UPDATE e DELETE de comprovante não pegam lock no evento: só a trava explícita do grupo os serializa.

**Alternativas consideradas.**
- Recusar comprovante em dia cancelado: contraria a FR-018 ("inclusive o da multa contratual").
- Reaplicar no próprio dia: o dia não tem venda.
- Travar só o evento do comprovante: deixa passar comprovante concorrente em outro dia.

**Decisões do dono que amarram.**
- D36 ("Sim, só o Superadmin").
- 1c-Q8 = A.
- P-37: dinheiro pago depois entra como comprovante, no mês do cancelamento.

---

## R14: desfazer "pago" (267c) numa linha do cancelado, e o desconto em dobro no principal vivo. [L11, 1e-Q5 = A, FR-057] + [R], decisão (b)

**Decisão.** `liquidar_item_de_comissao` (`comissoes_ops.py:296-361`) **não** ganha ramo novo. O desfazer fica correto por quatro peças:

1. A guarda `if event.is_cancelled: return` em `_sync` (R6). Sem ela, a linha devolvida a `a_pagar` (valor ≥ 0, com `event_id`) entra em `_resync_pending_commissions`, `should_have` falso a cancela (`:944-948`) e a Σ cai.
2. `liquidar_periodo` só troca `status` e `paid_at` (`:259-263`): **a Σ não muda**.
3. A próxima correção absorve: falta = alvo − liquidadas, e a `a_pagar` mais antiga recebe a falta.

   | Momento | Linhas | Σ |
   |---|---|---|
   | antes do desfazer | 100 pago + −80 a pagar (alvo 20) | 20 |
   | depois do desfazer | 100 a pagar + −80 a pagar | 20 |
   | próxima correção | 100 vira 20 no lugar, com a data intacta; −80 vira `cancelado` | 20 |

4. Trava: o desfazer passa a travar os **eventos** das linhas (`ORDER BY id FOR UPDATE`) antes de `liquidar_periodo(…, linhas="pagas")` (`:347`). Hoje ele trava as linhas e depois insere `EventLog` (`:351-358`), e isso pede KEY SHARE no evento: é a ordem inversa da 306 (R24).

**Achado com a mesma raiz (FR-057).** No principal **vivo** depois do corte (base 100 paga, ajuste −25 a pagar), o desfazer devolve a base a `a_pagar`, `_comissao_existente` acha a base, e `_sync` a regrava com a cheia nova, 75 (`:963-975`): Σ = 75 − 25 = **50**, um desconto em dobro.

Regra nova em `_sync`: com ajuste vivo do próprio evento cuja original voltou a `a_pagar`, sincroniza por `reconciliar` com alvo = cheia. O resultado é base 75 e ajuste cancelado. Com a base liquidada, nada muda (o "a 1e acerta" da FR-057 segue).

**Hora do histórico.** O `EventLog(created_at=now_sp())` do desfazer (`comissoes_ops.py:358`) mostra 3 h antes. Fica como está, vai ao `docs/05` e **não** serve de molde.

**Verify:**
- **variante 9/10-desfazer** (não é cenário novo): desfazer, abrir Comissões e a Planilha, corrigir um comprovante; Σ = alvo nos três momentos;
- **cenário novo, numerado, 38c**: corte com a base paga, depois desfazer, depois sync; Σ = 75. Entra na Living Spec junto da regra nova de `_sync` (R30).

**Alternativas consideradas.**
- Recusar o desfazer em cancelado: contraria a 1e-Q5 = A.
- Reconciliar dentro do desfazer: um item alcança vários eventos, e o financeiro passaria a importar o núcleo do cancelamento.
- Desfazer criando linha positiva: a 267c devolve a mesma linha.

**Decisões do dono que amarram.**
- 1e-Q5 = A ("só o Superadmin, para engano").
- L11.
- 1b-Q12 = B, que virou a 1e: depois do corte vale a regra de hoje.

---

## R15: venda de vários dias, "todos" e "só este dia". [1b-Q1 = C, 3b-Q4 = A, 3a-Q8 = A, 3a-Q1 = B, P-5, P-7, P-8, P-9, FR-054…FR-057, FR-061, FR-062] + [R]

**Decisão.**

- **`alcance`** (FR-055):
  - obrigatório no principal com outro dia **vivo**; senão 400 `fields.alcance`;
  - ausente fora do principal;
  - `"so_este_dia"` em principal sem outro dia vivo → 409 `sem_outro_dia_vivo`;
  - os valores são `ALCANCE_TODOS`/`ALCANCE_SO_ESTE_DIA` (data-model §6).

  "Tem outro dia vivo" é contado explicitamente: `is_group_leader` é `len(satellites)` (`models.py:455-457`) e continua verdadeiro com só dias cancelados.
- **"Todos"** (principal):
  - T1 sobre todos os dias, valida **todos** antes de gravar;
  - principal: regime `venda`, pago e devolvido do grupo;
  - cada dia vivo: `cancelled_at`, motivo, linha `satelite` com `group_leader_id`, `EventLog`, desmarca se marcado;
  - dia já cancelado: intocado (só entra no "já devolvido");
  - Google de cada dia e aviso por pessoa, depois do commit.
- **"Só este dia"** (dia não principal, regime `dia`):
  - pede motivo, `venda_nova` (0 < v ≤ venda atual; 400 `fields.venda_nova`) e devolução só em Parte/Nada (Tudo dá 400 `fields.devolucao_modo`), com teto = pago do grupo − já devolvido (400 `fields.devolucao_valor`) e **piso** = (pago do grupo − já devolvido − venda nova) − máx(0, pago do grupo − já devolvido − venda atual), se positivo (400 `fields.devolucao_valor` na Parte, `fields.devolucao_modo` no Nada; a prévia devolve `devolucao_minima`). O piso impede que o corte deixe a cliente com mais pago que a venda nova (Living Spec do checklist);
  - no principal: `antes = estado_da_venda(principal)` (`comercial_ops.py:438-448`) → `sale_value = venda_nova` e `sale_value_gross` na **mesma proporção**, `cheio × venda_nova ÷ venda`, ao centavo com `ROUND_HALF_UP` (o selo de % não muda; o desconto em reais cai na mesma proporção, 300 → 200 no 38) → `acompanhar_bv_da_venda(principal, antes, …)` **uma vez** (`:492`; não passa por `update_event_comercial`, que a chamaria de novo) → `flush` → `reconciliar` do principal **vivo** com alvo = cheia nova e motivo "Corte de dia: venda diminuiu";
  - linha `dia` com before/after da venda e do cheio;
  - devolução ligada ao **dia**;
  - PIX do BV não é pedido.
- **Ponto de extensão da 2a** (FR-062): **`cancel_ops.ao_cancelar(event, *, alcance=ALCANCE_TODOS, novo_principal=None)`**, o nome da tabela única (data-model §6). Hoje sem efeito; roda em **todo** cancelamento, na transação, uma vez por dia cancelado pelo ato:
  - avulso: `(ALCANCE_TODOS, None)`;
  - "todos": em **cada** dia do laço, principal e satélites, `(ALCANCE_TODOS, None)`;
  - corte de dia não principal: `(ALCANCE_SO_ESTE_DIA, None)`, porque nenhum dia passou a guardar a venda;
  - passagem: `(ALCANCE_SO_ESTE_DIA, novo_principal)` no antigo 1º dia, **depois** de `passar_venda`.

  O que ele recebe no avulso e no corte de dia não principal é a decisão que a FR-062 deixou ao plan; entra na Living Spec (R30).
- **Grupo vivo × cancelado.** **`group_ops.dias_vivos(event)`** (variante de `group_events`, `:64-75`, sem os dias cancelados) passa a ser usada por:
  - `agenda_read._compute_kpi` (`:352-421`, nas três somas de cachê, gastos e BV);
  - `_serialize_gastos` (`agenda_read.py:507`, chamado em `:1110`), **só no principal vivo** (ver abaixo);
  - o KPI Jinja de `event_detail`;
  - `comissoes_ops._group_cost` (`:725-730`), que é base do EducaManto, CPV, Top Vendedores, tendência e `/vendas/`. Isso exige `retrato_main_branch` e o cenário 41.
- **`_serialize_gastos` no cancelado.** Hoje a lista sai pelo grupo inteiro (`agenda_read.py:1110`, `_group_events`) e continua sendo servida no cancelado, que perde só o `kpi` (R19). Aplicar "só dias vivos" a todo evento esvaziaria a própria lista de gastos do cancelado (a devolução e a multa estão ligadas a ele). A regra:
  - **principal vivo**: `dias_vivos` (o dia cortado e a devolução dele saem do principal);
  - **cancelado `satelite`, `dia`, `virtual` ou `legado`**: o próprio dia;
  - **cancelado `venda`**: os dias do ato (o principal e os dias com linha `satelite` que apontam para ele).

  A cobrança soma o comprovante de todos os dias, e `data_do_grupo` já pula cancelado (`cobranca_ops.py:236-243`).
- **Agrupar e desagrupar.**
  - `validar_agrupamento` (`group_ops.py:116-139`) recusa cancelado como principal ou satélite. Chamadores: `api_agrupar_eventos` (`agenda_write.py:2365`) e o Jinja `_handle_group_events` (`calendar/routes.py:1536`).
  - `desagrupar` (`:204-231`) recusa dia cancelado com exceção, que precisa ser traduzida nos **três** chamadores: `api_desagrupar_evento` (`:2431`), **`api_remover_satelite`** (`:2455`, ausente do plano; sem a tradução vira 500) e o Jinja `_handle_ungroup_event` (`:1580`).
  - Os dois travam com releitura em ordem de id e decidem a recusa depois da trava (R24).
  - A docstring de `api_remover_satelite` ("é ela que destrava o cancelamento") é reescrita.

**Por quê.**
- A proporção pelo líquido é a da 305 (uma conta de proporção só, L3271). Reimplementá-la e deixar o Comercial salvar depois escalaria duas vezes.
- A base da comissão é venda − BV, então o alvo só se calcula depois do BV acompanhar.

**Alternativas consideradas.**
- Desagrupar para cancelar: contraria a Q1 = C.
- Retido próprio do dia: a proposta não tem preço por dia.
- Somar o dia cancelado no custo do grupo: a devolução do dia voltaria como gasto do principal.

**Decisões do dono que amarram.**
- 1b-Q1 = C ("não necessariamente deve-se ter que desagrupar").
- 3b-Q4 = A.
- 3a-Q1 = B: o BV acompanha a venda.
- P-9: o retido do dia cai no mês do evento.

---

## R16: passagem da venda do 1º dia. [1b-Q5 = B, Q13, Q15 = A, Q18 = A, P-6, P-29, FR-058…FR-060] + [R]

**Decisão.** `group_ops.passar_venda(antigo, novo, *, actor_name, agora)` roda **sem commit**, dentro do ato, sob T1, depois de congelar a linha `dia` do antigo e **antes da devolução** e de `cancelled_at` (ordem única do plan §Travas): assim a `TABELAS_DA_PASSAGEM` não leva ao novo principal a devolução que o próprio ato cria, e a linha `dia` já existe para receber `sale_handed_over`.

- **Quem recebe**: o dia vivo mais cedo, sem o antigo (por `start_at`, e no empate por id). `novo_principal_id` diferente dele → 409 `grupo_mudou`.
- **Validação antes de mover**: cachê pago e devolução pendente no antigo, venda nova, Parte/Nada, multas. Recusa não move nada; erro no meio desfaz tudo.
- **Duas listas únicas em constante, em `group_ops`** (nomes da tabela única, data-model §6), que a 2b e a 6a estendem:
  - **`group_ops.CAMPOS_DA_PASSAGEM`**: os 14 campos comerciais (`SATELLITE_FIELDS_CLEARED`, `group_ops.py:47-51`, mais `snapshot_comercial`/`apply_satellite`, `:87-99`), entre eles o vínculo do orçamento (`orcamento_history_id`, coluna de `calendar_events`; 1:1 entre vivos, `orcamento_evento_ops.py:903-932`), a previsão da nota e o nome do grupo, com retrato dos dois dias no histórico;
  - **`group_ops.TABELAS_DA_PASSAGEM`**: comprovantes, parcelas, notas, contratos, reembolsos, acréscimos (com o estado do BV), a devolução aprovada ligada ao antigo, o formulário de pré-contrato, as clientes que faltam e **todas** as linhas de comissão.
- **Comissão**: `SELECT … WHERE event_id = antigo ORDER BY id FOR UPDATE populate_existing` **antes** do `UPDATE event_id` (um UPDATE em lote trava na ordem do scan), com `audit` por linha. Só o vínculo muda; valor, datas, estado, beneficiário, `paid_at` e nota ficam.
- **Comissão própria do novo principal** (de quando era venda avulsa; agrupar só cancela a que estava a pagar, `group_ops.py:24-27`): ganha o prefixo `NOTA_COMISSAO_PROPRIA_DO_DIA`, no molde de `_com_marca_do_ciclo`. `_comissao_existente` e a reconciliação a ignoram (P-29).
- **Grupo**: todo dia passa a `group_leader_id = novo`. Depois, `expire` de `satellites` e `group_leader` dos dois eventos.
- **Marca da passagem**: a linha `dia` do antigo 1º dia nasce com `sale_handed_over = true` e `group_leader_id = novo` (R1). É dela que saem o `venda_passou_para` da resposta e do resumo e o link "a venda passou para DD/MM".
- **Ponto da 2a**: `cancel_ops.ao_cancelar(antigo, alcance=ALCANCE_SO_ESTE_DIA, novo_principal=novo)`, **depois** da passagem e na mesma transação (R15).
- **Fica com o antigo 1º dia**: elenco, ensaios (que caem), "precisa ensaio", histórico, observações, logística, confirmação, avaliação, 3D/NFC, figurino, Gastos Extras que não são devolução, dia do orçamento (3b), orçamento e página EducaManto (2b).
- **Datas**: nenhuma muda.
  - A comissão comum segue a data de venda (Q13).
  - A EducaManto a pagar vai à data do novo 1º dia pelo `_sync` seguinte (`comissoes_ops.py:955-956`; Q18 = A, sem marca).
  - A DRE e a Planilha seguem o evento que guarda a venda (Q15 = A), sem data nova guardada.
- **Google**: só a remoção do antigo e dos ensaios dele, depois do commit.
- **`EventLog`** sem `created_at`. `agrupar` e `desagrupar` gravam hora de São Paulo sem fuso (`group_ops.py:204-231`): não copiar esse molde.
- **Prova**: "soma antes = soma depois", linha a linha (cenário 42).

**Por quê.** A passagem é um dos dois únicos toques em linha paga ou no banco (o outro é a exclusão), e só no vínculo (SC-004). Apagar e recriar perderia ids e o estado do BV pago.

**Alternativas consideradas.**
- Apagar e recriar: proibido.
- Mover só a venda e deixar os filhos: quebra a soma.
- Nova data de competência: a Q15 = A pede a competência de hoje.
- As listas em `app/constants.py` (rascunho do plan) com o nome `…_DA_VENDA` (rascunho desta pesquisa): ficam em `group_ops`, ao lado de `SATELLITE_FIELDS_CLEARED`, que é a origem delas, com o nome da tabela única.

**Decisões do dono que amarram.**
- 1b-Q5 = B ("valor, vendedor, comprovantes, comissão, BV, parcelas, nota e contrato vão junto, com os mesmos valores e datas").
- Q13 ("a data importante para a comissão segue sendo a data de venda").
- Q15 = A ("DRE do mês novo").
- Q18 = A ("passa para o próximo mês mesmo").
- 1b-Q3 = A: a comissão própria não vira desconto.

---

## R17: ensaio, avisos e cachê pago. [1b-Q4 = B, 1c-Q3 = C, 1b-Q11 = B, 1c-Q10, 1c-Q12 = A, P-30…P-35, FR-063…FR-069] + [R]

**Decisão.**

- **Cachê pago.** `cancel_ops.cache_pago_do_evento(event)`: escalação com talento e `payment_status ∈ {pago, no_banco}`, fora a vaga de presença (`casting_ops.e_vaga_de_presenca`, a fonte única desse teste).
  - É exportada à 2a.
  - Recusa 409 `codigo: "cache_pago"` com a frase da FR-063 e `dias`, para qualquer dia alcançado, sem gravar nada.
  - T6 trava as escalações dos dias (`ORDER BY id FOR UPDATE`), porque o "pago" de cachê na Planilha não trava o evento.
- **Ensaio.**
  - `event_type == "ENSAIO"` → 409 `ensaio`.
  - `event_ops.delete_ensaio` (`:1791-1811`) separa a parte de banco numa função sem commit: `_clear_event_side_tables` + `notificacoes_ops.apagar_por_entidade("calendar_event", id)` + `delete`. `delete_ensaio` e `_sair_de_show` (`:445-504`; `aplicar_troca_de_tipo` começa em `:505`) seguem iguais.
  - Id, `google_event_id`, data e local de cada ensaio são capturados **antes** do delete. O histórico do show os registra. O Google vai depois do commit, com a trava (R23).
  - Depois, `expire` de `show.ensaios`.
- **E-mail.**
  - `send_removal_email` (`email_service.py:384`) por `send_async` (`:25`), **depois do commit**, **uma vez por `talent_id`**, sem quem recusou o convite (`invite_status == "rejected"`) e sem a vaga de presença.
  - Leva o dia mais cedo em que o artista estava escalado e o personagem dessa vaga.
  - `send_async` reabre por chave primária numa thread: passa só talento e evento, que persistem.
  - No corte, vai só ao elenco do dia.
  - A trava de e-mail fora da produção continua.
- **Sino**, regime A, na transação, por `emitir` (`notificacoes_ops.py:111`, com SAVEPOINT):
  - `evento.cancelado`: catálogo só `(ENSAIO,)`; uma notificação por pessoa **por ato** e só quando havia ensaio; **`dedupe_key = evento.cancelado:<id do evento da URL>`**, a chave do **ato**;
  - `evento.cancelado_escala`: catálogo só `(CASTING,)`, sem o SUPERADMIN; uma por dia com escalados; `urgent` a ≤ `ANTECEDENCIA_URGENTE_DIAS` (`:85`, 7 dias); link `?aba=producao`; texto "Evento cancelado: tire os N artistas da escala e avise cada um pelo WhatsApp"; pela mesma regra do ato, **`dedupe_key = evento.cancelado_escala:<id do evento da URL>:<dia_id>`** (o ato e o dia: a chave só do ato engoliria o 2º dia do "todos"); cabe nos 120 caracteres;
  - **por que a chave do ato**: a `UNIQUE(user_id, dedupe_key)` é permanente (`models.py:674`), e `emitir` engole o duplicado no SAVEPOINT. Com `<principal_id>`, um dia com ensaio cortado e depois "Cancelar todos", ou uma passagem seguida do cancelamento do novo principal, perderiam calados o 2º sino da equipe de Ensaio. Cada evento só cancela uma vez (UNIQUE de `event_cancellations`), então a chave do ato nunca repete;
  - **verify**: variante no **44**: corte de um dia com ensaio, depois "Cancelar todos" com ensaio → **2 sinos** por pessoa da equipe de Ensaio;
  - destinatários por `resolver_destinatarios` (`:92`, ativos e com acesso), **não** pela consulta de `notify_ensaio_team` (`event_ops.py:78-81`, que não filtra ativos);
  - catálogo em `DESTINATARIOS_POR_KIND` (`:62`); o `kind` cabe em 40 caracteres;
  - na tela, só o ícone em `NotificacaoItem.tsx:7-13`.
- **Tirar da escala no cancelado.** `casting_ops.assign_role`: o `if` do e-mail de remoção (`:153-161`) ganha `and not event.is_cancelled`, no núcleo, valendo para a API (`agenda_write.py:161`) e para o Jinja.

**Por quê.**
- Recusa antes do commit não avisa ninguém, porque o rollback leva os sinos.
- E-mail antes do commit avisaria de um cancelamento desfeito.
- O e-mail de hoje em `assign_role` vai antes do commit (`:161` antes de `:162`); a corrida com o ato é rara.

**Alternativas consideradas.**
- Gravar quem marcou o ensaio: o dono não pediu (Q11).
- WhatsApp pelo sistema: manual, pelo Casting.
- E-mail novo: o modelo não muda.
- Sino fora da transação: avisaria de recusa.
- `dedupe_key` pelo principal (rascunho): o 2º aviso some calado (acima).

**Decisões do dono que amarram.**
- 1b-Q4 = B ("Não. Mas… multa").
- 1c-Q3 = C ("O ensaio também é cancelado. E avisa…").
- 1b-Q11 = B.
- 1c-Q10 ("pede para o casting excluir e avisar por WhatsApp").
- 1c-Q12 = A.
- 30/09 ("se foi pago é porque foi realizado").

---

## R18: multa ao elenco e a lista do ato. [1b-Q8 = A, 1b-Q9 = A, 1b-Q10 = A, 1c-Q7, 1c-Q10, P-34, FR-070…FR-072] + [R]

**Decisão.**

- **Lista do ato** (`event_cancellation_elenco`): uma linha por **escalação** (vaga × dia) com artista nos dias alcançados, sem quem recusou e sem a vaga de presença. Guarda talento, vaga, personagem, cachê de referência e dia.
  - **A multa é por escalação.** Um artista em dois dias, ou em duas vagas, tem **duas linhas**, dois campos de multa no diálogo e, se as duas forem preenchidas, **dois gastos**. Recebe um e-mail só (R17).
  - A FR-070 e a FR-071 dizem "uma linha por artista" (1b-Q8 = A, "artista por artista"), mas o corpo da spec já usa `role_id`. A leitura "artista por artista = escalação por escalação" fica **explícita na Living Spec** (R30), em vez de agregar por talento: agregar perderia o dia (a multa nasce ligada ao dia do artista) e a vaga ("saiu da escala" é por vaga).
  - É a lista do aviso, do sino e da multa. Nunca é lida da escala de hoje.
- **No ato.** `multas: [{role_id, valor}]`.
  - **0 e vazio são ignorados** (sem multa). Só valor **negativo ou inválido**, ou `role_id` fora da lista, dá 400 `fields.multa_<role_id>`.
  - Depois do `flush` das linhas do elenco, cada valor > 0 vira um `SpecialExpense` **direto no ORM**, no molde de `_registrar_devolucao` (nunca `create_expense`, que nasce pendente e manda e-mail): aprovado, `nao_pago`, categoria `SpecialExpense.CATEGORY_MULTA_CANCELAMENTO`, `disbursement_type="fornecedor"` (a Planilha exige tipo não nulo, `financeiro/routes.py:1048`; `financeiro_read.py:695`), nome e PIX de `Talent.pix_key` (`models.py:169`, 120 caracteres; vazio é permitido e a Planilha mostra "sem PIX"), `event_id` = o dia do artista e `expense_date` = data do cancelamento.
  - `special_expense_id` na linha do elenco: **uma multa por linha**.
  - A multa **não** é travada: corrige-se em Gastos Extras.
  - Excluída lá, o `SET NULL` volta a linha a "não lançada".
- **Depois do ato**: `POST /api/events/<id>/multas {multas: [{elenco_id, valor}]}`, pela mesma função das `multas` do cancelar (`lancar_multas_do_cancelado`) e com **a mesma regra de valor** (FR-072).
  - Superadmin pela regra única; evento vivo dá 409 `nao_cancelado`.
  - **0 e vazio são ignorados**, como no ato; se, depois de ignorá-los, não sobrar nenhum valor > 0 (lista ausente, vazia ou só com vazios e zeros), 400 `fields.multas` "Informe a multa de ao menos um artista", como a spec já diz. É o pedido inteiro que não lança nada, não um valor recusado: a regra de valor do ato continua a mesma.
  - Valor negativo ou inválido, `elenco_id` de outro evento, fora da lista ou com multa já lançada → 400 `fields.multa_<elenco_id>`, sem gravar nada.
  - Data do lançamento (P-34). Travas: T1 → T2 (elenco) → INSERT, sem T3 nem T4.
  - `cancelamento.elenco[]` mostra "saiu da escala" quando `role.talent_id` difere do talento da linha.
- **`faltam_dias`**: contado pelo servidor no fuso de São Paulo, por dia no grupo, sem prazo.
- **Categoria.** `SpecialExpense.CATEGORY_MULTA_CANCELAMENTO = "Multa de cancelamento"` (21 caracteres), no molde de `CATEGORY_DEVOLUCAO` (`models.py:1073`), entra em `SpecialExpense.CATEGORIES` (`models.py:1070-1072`, `String(30)`). Nasce na Fundação, porque o cenário 21 semeia uma multa por ORM antes da História 6. Sem isso, a primeira edição em Gastos Extras a remapeia para "Outros" (`gastos_ops.py:240-242`). Ela aparece também na criação manual: é só categoria de custo.
- **DRE e comissão.** A multa entra nos gastos extras do mês em que nasce, sem código novo, e **não** mexe em comissão nem em BV.

**Por quê.**
- "A multa aponta para a linha" (spec, Entidades): a FK é a forma mais simples de saber "multa lançada".
- A lista é do ato porque o Casting tira o artista da vaga depois (1c-Q10).

**Alternativas consideradas.**
- Multa como cachê da vaga: proibido.
- Casar multa e artista por nome e PIX: frágil.
- Várias multas por linha: sem pedido do dono; a correção é em Gastos Extras.
- Uma linha por talento (agregada): perde o dia e a vaga.
- 0 dá 400 no `POST …/multas` (rascunho dos contratos §4): a FR-072 pede a mesma regra do ato, onde 0 é "sem multa".

**Decisões do dono que amarram.**
- 1b-Q8 = A: artista por artista (lido como escalação por escalação), cachê ao lado só como referência, vazio = sem multa.
- 1b-Q9 = A: sem prazo.
- 1b-Q10 = A: só custo.
- 1c-Q7 = A: "inserir pagamentos de multas".

---

## R19: dados de venda do cancelado com uma regra única e todas as portas. [1c-Q7 = A, 1c-Q8 = A, 1c-Q11 = C, P-44, FR-047, FR-048, FR-053] + [R], decisão (f)

**Decisão.**

- **Regra.**
  - `cancel_ops.pode_editar_venda_do_cancelado(user)` = SUPERADMIN pelo papel **real**, a mesma régua de `_is_superadmin`/`_can_delete` (`agenda_write.py:63`, `:111-115`).
  - Ajudante `_recusa_do_cancelado(event)` em `agenda_write`: 409 `codigo: CODIGO_EVENTO_CANCELADO` (`"cancelado"`), com "No evento cancelado, só o Superadmin corrige os dados de venda", ou `None`.
  - Ordem em toda porta: 404 → gate de hoje (403) → satélite (409, se houver) → **409 `cancelado`** → checagens da 215b e de campo.
  - **Exceção, uma só**: no `PATCH /api/events/<id>` (edição completa), o 400 de `_validate_event_core` vem **antes** do 409 `cancelado`, como hoje (contracts §7). Ali o 409 depende de comparar o corpo com o gravado, e o corpo só se compara depois de validado.
- **Portas:**

  | Dado | Portas (HEAD) | No cancelado |
  |---|---|---|
  | (a) comprovantes | `agenda_write.py:1747`, `:1778`, `:1803`; Jinja `calendar/routes.py:1050`, `:1085`, `:1111` | R13 |
  | (b) devolução e imposto | `PATCH …/devolucao` (novo) | R12 |
  | (c)(d)(f) venda, taxa, cortesia, vendedor, data, forma de pagamento | `PATCH …/comercial` (`:1210`; a 215b em `:1256-1258`); **`PATCH /api/events/<id>`** (`api_update_event` `:1067` → `_gravar_venda_da_edicao`, `event_ops.py:846-879`); Jinja `_handle_update_comercial` (`:811`) | R20 |
  | (d) parcelas e notas | `:1644`; `:1489`, `:1524`, `:1562` | regra única, sem mexer no congelado |
  | (e) multa | `POST …/multas` (novo) | R18 |
  | (g) acréscimos | `PUT …/acrescimos` (`:1588`); Jinja pelo mesmo `_handle_update_comercial` | R20 |
  | (h) reembolsos | `:1823`, `:1859` (`_can_edit_event`); `:1899` (Superadmin) | regra única |
  | orçamento | `api_set_event_orcamento` (`:1338`), três verbos | 409 **para todos** os que passam em `_can_manage_sale`, na view, logo depois do 409 satélite (`:1365-1370`) e antes do 404 do alvo, da autoria da 301 e da B8; `set_event_orcamento` (`orcamento_evento_ops.py:935`) recusa de novo depois de `travar_evento`, como cinto, antes de aplicar a venda |
  | grupo | `api_agrupar_eventos` (`:2365`), `api_desagrupar_evento` (`:2431`), **`api_remover_satelite`** (`DELETE …/grupo/satelites/<sat>`, `:2455`) | 409 `cancelado` vindo do núcleo (R15) |
  | Planilha | `POST /api/financeiro/pagamentos/set-status` (`financeiro_write.py`) | 409 `bv_nao_esta_a_pagar` e 409 `valor_mudou` ("o BV/a devolução mudou") (R9, R11) |

  Três dessas portas não estão no RBAC da spec: `PATCH /api/events/<id>`, `DELETE …/grupo/satelites/<sat>` e `POST /api/financeiro/pagamentos/set-status`. Os 409 novos delas entram pela Living Spec (R30).
- **`PATCH /api/events/<id>`.** No cancelado, se algum campo de venda chegar **diferente** do gravado (`_mesmo_valor` `:740`, `_mesma_taxa` `:1105`, `_mesmo_vendedor` `:1115`), dá 409 `cancelado` **para todos**, com "corrija pela aba Comercial". A tela esconde "Editar tudo" no cancelado.
- **Jinja.** Uma recusa só, no despachante `event_detail` (`calendar/routes.py:1657-1671`), para o conjunto de ações de dinheiro: `update_comercial`, **`update_sale`**, `add_payment`, `edit_payment`, `delete_payment`, **`add_reembolso`, `collect_reembolso` e `delete_reembolso`**.
  - Roda depois de `travar_evento` e de reler o evento, antes de qualquer handler (antes de `estado_da_venda`, `:837`).
  - Recusa **para todos**, inclusive o Superadmin: o recálculo só existe na API, e o Jinja da venda só é alcançável pelo host do backend. Isso vai **além da FR-047** (que fala só de quem não é Superadmin) e entra na Living Spec (R30).
  - As outras recusas Jinja ficam no núcleo: agrupar e desagrupar (R15), excluir (R7), `set_payment_status` (R9, R11) e a guarda de `set_commission_status` (R6).
- **`update_event_comercial`** (`event_ops.py:1169`):
  - relê `is_cancelled` depois de `estado_da_venda` (`:1204`) e recusa com 409 `estado_mudou` se o estado mudou (corrida entre a checagem da porta e a trava);
  - o gancho `sincronizar_comissao` (`:1231`, antes do commit de `:1240`) vira despachante: cancelado → `reaplicar_cancelado`, vivo → `_sync`. É "a mesma transação" sem núcleo novo.
  - Nas outras portas vivas entra só a releitura de `is_cancelled` depois do `travar_evento` de cada uma, como cinto, e nenhuma recongela: a edição completa (`_gravar_venda_da_edicao`, `:859`) dá 409 `cancelado` (contracts §7); o Jinja (`:837`) dá `flash`, pelo despachante (contracts §21); e o `PUT …/acrescimos` dá 409 `estado_mudou` quando `substituir_acrescimos` (`comercial_ops.py:208`) relê o evento já cancelado e devolve `[]` (contracts §8). O acompanhamento do BV da 305 (B10: a venda que muda leva o BV junto, uma vez) segue igual no vivo, uma vez por gravação.
- **Payload** (`serialize_event_detail`, `agenda_read.py:711`):
  - `flags.can_edit_venda_cancelado` e `flags.can_edit_pagamentos` são calculadas **depois** de `_role_flags` (`:155-204`), que `agenda.py:150` reusa na agenda; não entram dentro dela;
  - no cancelado, `venda.pode_mudar_taxa` e `pode_trocar_vendedor` (`:998-999`) passam por um E com `can_edit_venda_cancelado`;
  - `bv_pix` (`:560`) só vai com `can_edit_venda_cancelado`. Não apaga nada, porque o editor trata PIX vazio como "mantém" (`comercial_ops.py:332-333`);
  - `event.cancelamento` só com `show_comercial`; comissão, BV, imposto, PIX e taxa só com `show_financeiro`; `cancelamento.elenco` só com `can_edit_venda_cancelado`;
  - **`kpi` ausente** no cancelado (`:1105-1110`); `gastos` continua, com a regra de dias do R15.
- **O resumo vai DENTRO de `event.cancelamento`.** O PUT de acréscimos, o PATCH comercial e os comprovantes devolvem o **detalhe**, e a tela o grava no cache (`useSetAcrescimos`, `useEventMutation`). `{ok, resumo}` gravaria lixo em `["event", id]`.
- **Códigos.** Todo 409 desta entrega (18, com `valor_mudou`) sai de uma constante de `app/constants.py` (R1), e a tela os lê pela união de literais `CodigoRecusaCancelamento` (`lib/eventOps.ts`); nenhuma porta compara string solta.
- **Documentação (Princípio XIII).**
  - `docs/01` §4.3 ganha uma linha para **cada porta alterada** (as cerca de 30 da tabela acima, de R11, R13, R15 e R7), não só para os dois endpoints novos e a linha de `_can_delete()`; cada view alterada leva o comentário `RBAC:`.
  - `docs/00` §4 ganha a **regra única do cancelado** (Superadmin real; 409 `cancelado`; o Jinja recusa para todos); o §6, a ordem de travas evento → dependentes (R24).

**Por quê.**
- A 1c-Q8 = A pede uma regra só, sem parâmetro de "qual dado".
- A edição em bloco virou porta de venda com a 215b e a 305, e no cancelado gravaria a venda sem recongelar.

**Alternativas consideradas.**
- Espalhar a regra por endpoint: proibido.
- `_gravar_venda_da_edicao` ignorar em silêncio a venda do cancelado: 200 sem gravar.
- Travar o Jinja só para quem não é Superadmin: exigiria recálculo no Jinja (Princípio IV, PARADA).

**Decisões do dono que amarram.**
- 1c-Q7 = A ("dados de venda ainda devam poder ser editados… de resto melhor não dar para mexer").
- 1c-Q8 = A ("Superadmin apenas").
- 1c-Q11 = C ("Pode mexer sim").

---

## R20: recongelamento, com taxa congelada, troca de vendedor e acréscimos no lugar. [1e-Q2 = C, Q16 = A, Q17 = A, 1c-Q11 = C, L6, P-50, FR-049…FR-052] + [R], decisão (d)

**Decisão.**

- **`reaplicar_cancelado(event, *, motivo, mudou)`**, só no regime `venda`, na mesma transação, seguindo a tabela da FR-049:
  - **venda** → cheia = (venda − Σ BV congelado) × taxa congelada (EducaManto com `commission_cost`), e "Cancelamento: correção da venda";
  - **taxa** → `commission_rate` nova, com "Cancelamento: taxa corrigida", para mais e para menos, inclusive a paga;
  - **cortesia** → cheia 0, ou restaurada com os insumos congelados;
  - **data de venda** → nada até a 1e;
  - **comprovante e devolução** → nada no congelado.

  Em seguida reconcilia por beneficiário (R5) e grava `updated_at/by`, `EventLog` e o resumo na resposta. Venda nova abaixo do retido **não** é recusada, porque há teto no cheio.
- **Taxa.** Todo recongelamento reusa `event_cancellations.commission_rate`. Só a correção da taxa troca a taxa congelada (a da data de venda, só depois da 1e). Mudar a padrão nas Configurações não alcança cancelado. A comparação é por `_mesma_taxa`.
- **Vendedor.**
  - `seller_id` novo; `commission_seller_id` = `_beneficiario_comissionado` com a regra do novo.
  - `alvos = {novo: comissão do retido, antigo: 0}`: a `a_pagar` do antigo é cancelada, o que ele já recebeu ganha linha negativa no primeiro repasse aberto **dele** ("vendedor trocado — devolve o já recebido"), e o novo recebe a linha inteira ("vendedor trocado — comissão do retido").
  - Novo sem comissão → ninguém recebe.
  - No EducaManto, o beneficiário é o responsável: muda só o recorte comercial (P-50).
  - A tela confirma: "o retido e a comissão do retido passam a <novo>".
- **Acréscimos.** `alterar_acrescimos_do_cancelado` reaproveita a montagem e a validação da 305: `comercial_ops.py:216-404` (cerca de 190 linhas) é extraído para `_montar_acrescimos(…)`, e o vivo continua com o `delete`/`add` de `:407-411`.
  - **Fatiado** (Princípio II): `_montar_acrescimos` vira um orquestrador curto sobre **cinco fatias**, uma por bloco da montagem de hoje, **a mesma lista do plan** (História 4):
    1. ler os itens (`id` repetido, tipo, valor);
    2. casar o bundle antigo sem `id`;
    3. recusar BV pago removido ou trocado de tipo;
    4. a régua do BV (somas em reais e em %);
    5. montar o registro: BV (recebedor e PIX por `erros_do_bv`; o BV pago com valor e unidade da linha gravada; BV em % no cancelado), `valor_visto` e as `trocas` de recebedor e PIX.

    Cada uma com cerca de 30 linhas (o limite da constituição) e docstring do porquê;
  - a extração é **neutra** no vivo: o `verify_305` roda de novo sem mudança de resultado (R28);
  - se alguma fatia passar de ~30 linhas sem partir uma regra da 305 ao meio, entra **uma linha** no **Rastreamento de complexidade** do plan, com o porquê.

  | Caso | No cancelado |
  |---|---|
  | BV novo (sem id), não pago | nasce o acréscimo, faz `flush`, e nasce **também** a linha congelada (`original_amount = amount_brl`, `paid_at_cancellation=False`); recebedor e PIX obrigatórios; BV novo em % → 400 `items.<i>.value` com "lance em reais" (ramo `cancelado` de `:351-358`) |
  | BV não pago ausente, ou que deixou de ser BV | apaga o acréscimo **e** a linha congelada na mesma transação, sem órfã por `SET NULL`; `EventLog` e `audit` com o cheio |
  | BV não pago editado | regrava cheio, recebedor e PIX no acréscimo **e** no congelado |
  | Acréscimo que não é BV | ausente do corpo é apagado; editado é regravado no lugar; novo sem id nasce. Nenhum mexe no congelado nem na cheia (FR-049 (g)); `audit` em cada um |
  | BV pago ou no banco | valor ou unidade diferente → **mantém o gravado**, como no vivo (`comercial_ops.py:337-338`), sem recusa; tipo diferente → 400 (`:288-289`); ausente → 400 `items` (`:290-294`, leitura 6); recebedor e PIX trocam com rastro (`trocas`, `:339-348`), só no acréscimo |
  | bundle antigo sem nenhum `id` e com acréscimos gravados | 400 "recarregue a página" (não há como casar) |

  Herdados da 305: `id` repetido (`items.<i>.id`) e `valor_visto` (`:368-384`). Depois de gravar: `flush` → `expire(event, ["acrescimos"])` → `reaplicar_cancelado(…, "Cancelamento: correção da venda")`, com BV = Σ `original_amount` das linhas vivas.
- **`substituir_acrescimos` no cancelado** devolve `[]` **depois** de `travar_evento` (`:208`) e da leitura de `cancelado` (`:218`), servindo de cinto para todo chamador. A API (`:1588`) decide entre vivo e cancelado lendo o evento **sem** trava: o vivo segue como hoje, sem T1 (a 305 já trava o evento dentro de `substituir_acrescimos`), e só o ramo do cancelado (Superadmin) toma T1 → T2 → T3 e relê. Se `substituir_acrescimos` reler o evento já cancelado e devolver `[]`, a view faz rollback e responde 409 `estado_mudou`, nunca 200 sem gravar. O `_sync` de `:1637` vira no-op no cancelado, e o ramo do Superadmin chama `reaplicar_cancelado` explicitamente.

**Por quê.**
- Apagar e recriar troca a identidade que `event_cancellation_bvs.acrescimo_id` guarda.
- BV novo sem linha congelada nunca iria à Planilha nem à base da cheia (FR-040: "`venda` sem congelado → só se pago").
- `acompanhar_bv_da_venda` já pula cancelado (`:531-532`), então o PATCH comercial não move o BV cheio congelado.

**Alternativas consideradas.**
- BV novo sem congelado: some da Planilha.
- Linha órfã com flag "removido": coluna a mais, e todo leitor filtra.
- Recusar BV novo ou removido: contraria a FR-052.
- No-op calado antes da trava: corrida com o ato.
- Ler a taxa padrão de hoje: proibido.

**Decisões do dono que amarram.**
- 1e-Q2 = C (a taxa da data de venda; mudar a padrão só vale dali em diante).
- Q16 = A.
- Q17 = A ("Sim").
- 1c-Q11 = C.
- L6.

---

## R21: DRE com o retido no mês do cancelamento. [D30, D32, D33, Q15 = A, P-16, P-41, P-42, FR-041…FR-045] + [R]

**Decisão.**

- **`app/financeiro/dre_ops.py`** (novo), com imports tardios de `routes`:
  - `ROTULO_RETIDO`;
  - `gastos_extras_do_periodo(start, end)`: a consulta de `financeiro/routes.py:294-301` e `financeiro_read.py:243-250`, somada em `Decimal`, **menos** `filtro_devolucao ∧ evento cancelado` de qualquer regime, `dia` inclusive. A multa e a devolução de evento vivo ficam;
  - `tendencia_mensal(today, meses=6)`: substitui `routes.py:394-415` e `financeiro_read.py:365-385`, com `cancelled_at IS NULL` e o retido somado no mês do cancelamento **só quando ≠ 0**.
- **`cancel_ops.cancelados_do_periodo(inicio, fim, *, seller_id=None, educamanto_only=False)`**, mais `totais_cancelamentos` e `retido_por_vendedor`: a **fonte única**.
  - Faixa `[inicio 00:00, fim 23:59:59.999999]` sem fuso, como `vendas_ops.py:165-166`.
  - `outerjoin event_cancellations`: o regime vem da linha (sem linha é `legado`), e o vendedor é `coalesce(congelado, ao vivo)`.
  - Filtro de tipo seguro contra nulo: `or_(event_type.is_(None), event_type.notin_(["ENSAIO","VIRTUAL"]))`.
  - Só `venda` e `legado` trazem dinheiro e contam em `quantidade`. Cancelado sem venda e sem pago fica fora (P-24).
  - Usa `resumos_cancelados` em lote, e o `selectinload(CalendarEvent.cancelamento)` é montado **dentro** da função (lição da 302).
- **`_compute_drg(..., cancelamentos=None)`** (`routes.py:205-257`) soma sob `if cancelamentos and cancelamentos["quantidade"]:` em quatro lugares:
  - receita (`:218`);
  - impostos, depois do quantize (`:219-222`);
  - CPV, com o BV do retido ou o pago (`:227`);
  - comissões (`:231`).

  `retido_cancelamentos` e `n_cancelados` aparecem sempre no retorno, no Projetado também, que não muda. A condição é a **quantidade**, não o valor: somar `Decimal("0.00")` muda o expoente e quebra a comparação exata do cenário 23.
- **Jinja `dashboard()`** (`routes.py:263-575`), sem mover nada (PARADA):
  - `:294-301` passa a `dre_ops`;
  - `cancelamentos=` em `:316` e `:319`;
  - ticket médio (`:327-330`) passa a dividir por Σ venda dos eventos com venda;
  - barra do retido antes do `sorted`/`max` (`:375-379`);
  - Top Vendedores (`:381-392`) com `retido_por_vendedor` **antes** do corte do top 5;
  - tendência por `dre_ops`;
  - Recebimentos Previstos (`:469-473`) com `cancelled_at IS NULL`;
  - NF a emitir (`:496-503`) com o selo no título.

  `dashboard.html` ganha uma linha depois de `:123`, condicionada a `n_cancelados`.
- **API `api_financeiro_dashboard`** (`financeiro_read.py:185-545`): os mesmos toques, mais:
  - `paineis.cancelamentos` **sempre**, com quantidade 0 quando não há cancelado;
  - NF com `cancelado?`/`retido?`;
  - `monthly_trend[].retido?`;
  - docstring `:188-189` (cita `routes.py:387`, quando `dashboard()` está em `:263`) e comentário `:231-232`, como pede a FR-074.
- **`comissao_exibida_do_evento`** (`comissoes_ops.py:369-403`): fica em 0 na tela Jinja do evento cancelado, com dívida no `docs/05` (P-28). A API não a chama, porque o `kpi` vem ausente.

**Por quê.**
- O exemplo-padrão dá +400 − 40 − 18 = **+342** (+278 com imposto de 64), contra −600 na `main`.
- Sem tirar a devolução dos gastos, daria 400 − 40 − 18 − 600 = −258.
- A competência de hoje já põe o retido do dia cortado no mês do evento.

**Alternativas consideradas.**
- Retido no mês do evento: contraria a D30.
- Imposto = alíquota × retido: contraria a D32.
- Mover `_compute_drg` ou extrair as views: proibido (PARADA).
- A condição pelo valor do retido: quebra a regressão exata.

**Decisões do dono que amarram.**
- D30 ("No mês do cancelamento").
- D32.
- D33 ("O retido conta como venda").
- 1c-Q6 = A: sem "Mostrar cancelados"; o dinheiro fecha pela linha do retido.
- Q15 = A.

---

## R22: relatórios comerciais, ficha da cliente e cobrança da Home. [D33, P-43, FR-046, FR-061] + [R]

**Decisão.**

- **Dashboard Comercial.**
  - `vendas_ops.build_kpis(..., *, cancelados=())` (`:249-298`): `total_vendido` (`:269`) += Σ retido; `comissao_prevista` (`:284-290`) += comissão do retido quando `commission_target_id is None` ou o beneficiário **congelado** é o alvo. Ticket, eventos fechados e desconto não mudam.
  - `api_vendas_pipeline` (`financeiro_read.py:120-175`) passa `cancelados_do_periodo(start, end, seller_id=scope.seller_id, educamanto_only=scope.educamanto_only)`.
  - Contrato `kpis.retido_cancelamentos?` **e** a quantidade e a comissão do retido, que a sublinha pede: `kpis.n_cancelados?` (o nome da DRE) e `kpis.comissao_retido?`.
- **`/admin/desempenho`** (`admin_config_read.py:117-178`): `cancelled_at IS NULL` na consulta (`:149-157`); `retido_por_vendedor` mapeado de id para **nome**, porque a agregação é por nome; `vendas[].retido?`, `cancelados?`, `totals.retido?`.
- **Ficha da cliente.**
  - `client_ops.get_client_detail` (`:132-159`): total = Σ vivos + Σ retido, com resumos **só se** houver cancelado (o PATCH e o DELETE também a chamam, `clientes_write.py:75`, `:101`).
  - `list_clients` (`:111-129`) e `client_metrics` (`:183-225`) filtram o cancelado.
- **Performance da Home**: `compute_performance` (`dashboard_service.py:290-293`) com `cancelled_at IS NULL`. **`/vendas/` Jinja** (`routes.py:1454`): o mesmo filtro.
- **Status de pagamento do evento** ganha "cancelado" (`vendas_ops.py:32-38`, `:44-66`), mostrado em `paineis.cancelamentos.itens[].status` da DRE; as uniões TS `SalePaymentStatus` (`lib/vendas.ts:9`) e `EventoStatus` (`lib/financeiro.ts:94`) ganham o membro. As chaves TS entram **no mesmo commit** nas duas páginas que usam `Record<…>` (`FinanceiroDashboardPage.tsx:60-74`; `VendasPipelinePage.tsx:39-45`).
- **Cobrança da Home** (FR-061).
  - `VendaResumo` (`cobranca_ops.py:98-195`) ganha **`devolvido` à parte**, e `recebido` continua **bruto**.
  - `saldo`, `quitada`, `sinal_pendente` e `_primeira_parcela_descoberta` (`:265-275`) passam a usar recebido − devolvido.
  - Chamadores: `resumir_venda` (`:301`), `vendas_desde` (`:403`), `resumo_da_venda_do_evento` (`:545`, usado por `agenda_read.py:1054`).
  - `data_do_grupo` não muda. Docstrings `:3-6` e `:104-106` (FR-074).
  - Exemplo: venda 2.000, pago 1.500, devolvido 300 → 800 a receber.

**Por quê.**
- Mantendo `recebido` bruto, `outros_do_grupo` (`:576-600`) e a regressão das cobranças sem devolução ficam idênticos.
- O líquido entra só nas contas de saldo.

**Alternativas consideradas.**
- `recebido` líquido: muda a exibição por evento do grupo.
- `event_payment_status(cancelado=)` sem chamador: a FR-046 pede o status.

**Decisões do dono que amarram.**
- D33.
- P-43.
- 1b-Q1 = C: o dinheiro do grupo mora no principal.

---

## R23: Google depois do commit, com a trava de ambiente. [FR-014, FR-015, P-26, Princípio XIV, dívida 69] + [R]

**Decisão.**

- **`cancel_ops._remover_do_google(alvos)`** roda **depois** do commit, sobre `(event_id, google_event_id)` guardados em variáveis simples **antes** do commit. Depois do commit, os objetos expiram, e os ensaios apagados disparariam `ObjectDeletedError`.
  - **Trava** lida a cada chamada: `current_app.config.get("CALENDAR_SUPPRESS_EVENT_WRITES", True)`, no molde de `sumico_ops._exigir_ambiente_liberado` (`:707-714`). Chave ausente = travado.
  - **Travada**: zero chamadas e `aviso`.
  - **Pula** o marcado (já não está no Google), lido **antes** do `desmarcar` do ato: a lista de alvos se monta logo depois de T1, porque o `desmarcar` zera `google_missing_since` e deixa o `google_event_id`; no "todos", vale para cada dia marcado. Pula também o id `virtual-local-…` (`virtuais_ops.GOOGLE_ID_LOCAL_PREFIX`, `:545`) e o evento sem id.
  - **404/410** contam como "já não estava" (`service._status_http`, `:243`).
  - **Falha** vira `aviso` sem o texto cru do erro, no padrão de `_MENSAGENS_DEVOLVER` (`sumico_ops.py:652`), e nunca desfaz o cancelamento.
  - Chama `service.delete_event` (`:495-501`) **pelo atributo do módulo**, para o dublê do verify interceptar.
- **Cobertura**: show, cada dia do "todos", o antigo 1º dia e todos os ensaios.
- **O cancelado que sobra no Google não volta**: o sync o pula (`calendar/routes.py:2261`), `_candidatos` o filtra (`sumico_ops.py:447`) e o "Sincronizar" não o toca.
- **Escopo da trava**: só o cancelamento. O botão "Cancelar ensaio" (`delete_ensaio`) e a troca de tipo continuam escrevendo sem trava (a dívida 69 encolhe; risca-se "cancelar").
- **Textos**: docstring de `config.py:145-162`, `DEVELOPMENT.md:110-115` e `:151`, `CLAUDE.md` §4 ("`_suppress_calendar_event_writes` só a devolução").

**Por quê.**
- Hoje a chamada roda dentro do núcleo, antes do commit (`cancel_ops.py:300-308`), e seguraria a trava durante a rede.
- O espelho traz o token real.

**Alternativas consideradas.**
- Antes do commit: trava longa.
- Fila ou thread: um mecanismo a mais, sem pedido.
- Trava geral do calendário: escopo da dívida 69.

**Decisões do dono que amarram.**
- D35 (o marcado não chama o Google).
- P-26.
- Princípio XIV.

---

## R24: concorrência, com seis travas e a ordem evento → dependentes. [P-20, FR-013, FR-054] + [R], decisão (g)

**Decisão.**

| Trava | O que trava | Como |
|---|---|---|
| **T1** `travar_grupo(event)` | principal e todos os dias, vivos e cancelados | ids **por consulta** (`cancel_ops.ids_do_grupo`, R4), nunca por `event.satellites`; `SELECT … WHERE id IN (…) ORDER BY id FOR UPDATE` + `populate_existing()`; relê a composição e, se mudou, rollback + 409 `grupo_mudou`; avulso = uma linha. Relê **todas** as colunas, ao contrário de `travar_evento`, que relê só 4 (`orcamento_evento_ops.py:799`) |
| **T2** | `event_cancellations`, `_bvs` e `_elenco` do grupo | leitura com `populate_existing`, sem `FOR UPDATE` (todo escritor passa por T1) |
| **T3** | acréscimos do principal | `ORDER BY id FOR UPDATE populate_existing` (molde `comercial_ops.py:211-214`) |
| **T4** | linhas de comissão | **um SELECT só**: `event_id IN (grupo) OR (seller_id IN beneficiários AND status IN ('a_pagar','no_banco'))`, `ORDER BY id FOR UPDATE populate_existing`; só com `simular=False` |
| **T5** | devoluções do grupo, pendentes inclusive | `ORDER BY id FOR UPDATE populate_existing`; disjuntas entre grupos |
| **T6** | escalações com talento dos dias alcançados | `ORDER BY id FOR UPDATE`, só no ato (régua do cachê pago contra o "pago" de cachê na Planilha) |

| Operação | Ordem |
|---|---|
| Cancelar (todas as variantes) | T1 → T2 → T3 → T4 → T5 → T6 → validar → `desmarcar` → `flush` → congelar → devolução → `flush` → (corte: `estado_da_venda`, venda nova, `acompanhar_bv_da_venda` uma vez) → alvo → reconciliar → `cancelled_at` → `ao_cancelar` → ensaios (banco), sinos e multas → `EventLog` → commit → Google e e-mail |
| Alterar devolução | T1 → T2 → (`venda`, ou `dia` com o principal cancelado: T4) → T5 → gravar → (nos mesmos casos: reconciliar) → commit |
| Multas | T1 → T2 → INSERT |
| Acréscimos do cancelado | T1 → T2 → T3 → gravar → `flush`/`expire` → T4 → reconciliar |
| Comprovantes | T1 → recusa → gravar → `flush` → (`venda` cancelado: T4 → reconciliar) |
| BV na Planilha | `travar_evento(principal)` → acréscimo → T2 em leitura |
| Devolução na Planilha (API e ramo de gasto do Jinja) | `travar_evento(evento da devolução)` → gasto relido → (API) conferência de `valor_esperado` |
| Gastos Extras sobre devolução | `travar_evento` (no vincular, os dois eventos por id) → gasto `with_for_update().populate_existing()` → decide |

**Mudanças fora da 306, para não cruzar a ordem:**
1. `order_by(CommissionPayment.id)` em `liquidar_periodo` (`comissoes_ops.py:249-257`) e `pay_seller_month` (`:631-638`): uma linha cada, sem mudar comportamento.
2. O desfazer da 267c trava os eventos das linhas antes (R14).
3. `_delete_event_flow` e `_apagar_vazio` travam e releem (R7).
4. `_resync_pending_commissions` usa `FOR NO KEY UPDATE SKIP LOCKED` por evento e commita por evento (R6).
5. As portas vivas (`update_event_comercial`, `_gravar_venda_da_edicao`, Jinja `:837`, `substituir_acrescimos`) reconferem `is_cancelled` logo depois do `travar_evento` delas.
6. Gastos Extras sobre devolução: `travar_evento` antes de decidir; no vincular, os dois eventos em ordem de id (R11).
7. Agrupar e desagrupar (`group_ops.py:116-139`, `:204-231`) travam com releitura em ordem de id e decidem depois.
8. Deadlock residual (40P01; o `sync_events` grava sem ordem): nos endpoints da 306, rollback + 409 `tente_de_novo` ("Outra gravação estava em curso neste evento: tente de novo."). No POST de comprovante, o arquivo salvo é removido (R13).

Esta é a lista única; o plan (seção Travas) a repete com as mesmas oito, e o Resumo e o Rastreamento de complexidade a citam.

**Escritores de fora** que cruzam as tabelas do ato: `set_event_clients` (`event_ops.py:1244`) já trava o evento antes dos vínculos, e é compatível; `delete_client` (`client_ops.py:238`, `UPDATE` em lote em `:249`, sem `ORDER BY id`) pode cruzar com T1 e com a passagem, e fica como resíduo aceito (do lado da 306, 409 `tente_de_novo`; do lado dele, 500 raro com rollback inteiro); `sync_events` é o item 8.

**Documentação.** A ordem evento → dependentes entra no `docs/00` §6 (Armadilhas transversais), ao lado da regra única do cancelado no §4 (R19); o `docs/04` já a tem desde a 305.

**Por quê.**
- A regra da casa, desde a 305, é "evento → dependentes" (docstring de `travar_evento`; `docs/04:261-263`).
- O INSERT de um comprovante pega FOR KEY SHARE no evento e espera o FOR UPDATE do ato. Depois do commit, entraria num cancelado sem `reaplicar`, e por isso a releitura depois da trava.
- Duas travas de várias linhas sem ordem (Planilha × reconciliação) fecham ciclo. Por isso um SELECT ordenado.
- O clique duplo é serializado por T1; o UNIQUE é a segunda barreira.

**Alternativas consideradas.**
- `travar_evento` como T1: relê pouco.
- Travar as linhas do evento e as do beneficiário em dois comandos: deadlock com `liquidar_periodo`.
- `travar_evento` no resync: seguraria cerca de 72 eventos até o commit do GET.
- `pg_advisory_xact_lock` por beneficiário: fica como saída do resíduo aceito.

**Decisões do dono que amarram.** FR-013 ("nunca 'paga de 20'"), D34.

---

## R25: sessão do ORM, com autoflush, releitura e coleções velhas. [R]

**Decisão.**
- **`simular=True` nunca muta objeto ORM.** A prévia num GET passaria a escrever e a travar até o rollback do teardown. A mutação "simular escreve" do verify (R2, prova da FR-011) é o que pega a regressão.
- **`flush` explícito:**
  - antes de toda releitura com `populate_existing`, que relê o banco **por cima** de mudanças não enviadas;
  - depois de `_registrar_devolucao` e antes de `reaplicar_cancelado` (o retido é SQL e depende do autoflush);
  - antes de congelar (armadilha do cache da base EducaManto, `event_ops.py:966-969`).
- **Criar pela relação**, nunca só pela coluna: `EventCancellation(event=event, …)`, e o mesmo em `bvs` e `elenco`. Senão `event.cancelamento`, já lido como `None` pelo serializador ou pelo resumo, continua `None`, e o regime sai `legado` na própria resposta.
- **`expire` depois de cada escrita:**
  - `event.acrescimos`, depois dos acréscimos do cancelado (molde 305, `comercial_ops.py:413`);
  - `event.commission_payments` (relação em `models.py:981-986`, backref `lazy=True` em `:984`), depois de reconciliar e antes do resumo;
  - `satellites` e `group_leader` dos dois eventos, depois de `passar_venda`;
  - `show.ensaios`, depois de apagar os ensaios;
  - `event.roles`, depois de `assign_role`.
- **`selectinload(CalendarEvent.cancelamento)`** nunca como constante de módulo: o backref só existe depois de `configure_mappers` (lição da 302).
- **`EventLog` sem `created_at`** em todo código novo, com o default UTC (`models.py:631`). `group_ops` e o desfazer da 267c gravam hora de São Paulo e não servem de molde.
- **O verify confere por conexão separada**: o serializador mostra escrita sem commit (`agenda_write.py:1769-1771`).

**Por quê.** Cada item é um defeito já visto na casa: a coleção velha da 305 (R7 dela), o backref da 302 e o "3 h antes".

**Alternativas consideradas.** `no_autoflush` em blocos: esconde a ordem real e conflita com `populate_existing`.

**Decisões do dono que amarram.** Nenhuma; é técnica (P-20, P-22).

---

## R26: deploy cruzado, bundle × backend, e cache da tela. [P-21, P-23] + [R]

**Decisão.**

- **Bundle novo com backend antigo:**
  - `regime` ausente no impacto desliga o envio, com "O sistema está atualizando — tente em um minuto";
  - `cancelamento` ausente faz a tela cair no `KpiGrid` antigo;
  - `PATCH …/devolucao` e `POST …/multas` com 404/405 viram "atualizando";
  - **gate que existe hoje** ("Adicionar pagamento") é testado por `flags.can_edit_pagamentos !== false`, nunca por valor verdadeiro, porque `flags` é `Record<string, boolean>` (`lib/agenda.ts:385`) e o `tsc` não acusa;
  - gate **só do cancelado** (`can_edit_venda_cancelado`) pode ser por valor verdadeiro;
  - campos novos de Comissões, Planilha e DRE são **opcionais** no TS.
- **Bundle antigo com backend novo:**
  - cancelar sem modo dá 400 `devolucao_modo`, com `e.message` legível;
  - `kpi` ausente: `KpiGrid` devolve `null`, e a aba abre por `data.venda` (`EventDetailPage.tsx:127-134`);
  - ficam **por um ciclo**: `devolucao` (página de Cancelamentos), `devolucao_sugerida` (impacto) e `is_group_leader` (o diálogo antigo manda desagrupar);
  - Comissões imprime `status_label` do servidor, então "no banco" aparece;
  - o BV da Planilha aberta antes do deploy recebe 409 `valor_mudou` "O BV mudou para R$ X", que é a mensagem certa;
  - a Planilha antiga não manda `valor_esperado` no `expense`: a devolução é marcada sem conferência, como hoje;
  - um `codigo` 409 novo que o bundle antigo não conhece cai no `e.message`, que é frase legível;
  - PUT de acréscimos sem nenhum `id` no cancelado dá "recarregue".
- **Repetição depois do 502**: 409 "já cancelado", e a tela recarrega o evento (`invalidateQueries(["event"])`) em vez de mostrar erro.
- **Cache** (`staleTime: 30_000`, `packages/api-client/src/queryClient.ts:39`):
  - `invalidarFinanceiro` (`lib/financeiro.ts:300`, hoje privada) passa a ser exportada;
  - cancelar, alterar devolução, multas, comprovante e PATCH/PUT do cancelado invalidam `["event"]` (cada dia e o novo principal), `financeiro-*`, `vendas-dashboard`, `gastos-extras`, `cancelamentos`, `["dashboard"]`, `invalidarSumidosGoogle` e `invalidarNotificacoes`;
  - `useEventMutation` (`lib/eventAttachments.ts:46-60`) e `useDeleteEvent` (`lib/eventOps.ts:72-87`, que hoje não invalida a faixa de sumidos) também.
- **Deploy**:
  - noite 2, sozinha, depois de 215b e 267c, com backend e frontend no mesmo push;
  - build reproduzido num venv 3.11 antes, porque o `startCommand` roda `flask db upgrade`;
  - `contagem_pre_deploy.py` por SSH, só leitura;
  - nenhum script nem variável para o dono;
  - teste com um evento descartável sem venda, sem artista real e sem ensaio;
  - **rollback**: reverter o merge, sem `downgrade`, é limpo até o primeiro cancelamento real (a migration é aditiva; as tabelas ficam e o código antigo as ignora). Depois dele, **rollback assimétrico**: o defeito se corrige para a frente (`306b`).

**Por quê.** Os dois serviços trocam separados, com cerca de 1 min de 502 (CLAUDE.md §2).

**Alternativas consideradas.**
- Ramo de compatibilidade "cancelar sem modo = Nada": contraria a D27.
- Gate por valor verdadeiro: some para todos na janela.

**Decisões do dono que amarram.** D27 e D34.

---

## R27: telas. [FR-022…FR-026; Princípios V, IX, XI, XIII] + [R]

**Decisão.** Nenhuma conta de dinheiro no navegador. Dinheiro sempre por `@manto/money` (`MoneyInput` e formatação). Diálogos com a transição padrão e `useReducedMotion`. Toda recusa vira frase em português. Toda trava decidida pelas flags e por `expense.locked`, nunca pelo papel.

- **`ExcluirEventoDialog.tsx`**:
  - começa sem modo marcado;
  - valor só em Parte; nome e PIX só em Tudo e Parte;
  - blocos BV do parceiro (cheio, proporcional, já pago, recebedor e PIX quando faltam), Imposto (só com nota), Efeito na comissão (do servidor) e Multa ao elenco;
  - frases do que mais acontece;
  - cachê pago sem botão, apontando Gastos Extras;
  - venda virtual só com o motivo; marcado com aviso;
  - na H5, lista de dias, alcance, "Novo valor da venda" e a frase do `proximo_principal`; saem `:174-190` e o `disabled` por `is_group_leader` (`:283`);
  - erro no campo certo por `fields`, e o `codigo` do 409 lido pela união de literais em TS (R1), nunca por comparação de texto da mensagem;
  - Multa ao elenco com **um campo por escalação** (artista × dia × vaga), 0 ou vazio = sem multa (R18);
  - o bloco opcional **"o que foi pedido" da FR-023 é da 2a**: nada é construído aqui, nem prop.

  Divisão sugerida em `BlocoDevolucao`, `BlocoBv` e `MultaAoElencoBloco`.
- **Prévia**: `usePreviaCancelamento` com chave própria `["evento-previa-cancelamento", id, valor, venda_nova]`, `placeholderData: keepPreviousData` (molde `lib/agenda.ts:84-91`), debounce ≥ 400 ms e decimal com ponto.
- **Tela do cancelado**:
  - `ResultadoCancelamento` (em `ComercialSection`, no lugar do `KpiGrid`, `:82-177`) com "Alterar devolução" num lugar só, pela flag;
  - `AlterarDevolucaoDialog` (novo total, nome, PIX, observação, imposto; piso e teto do servidor);
  - `LancarMultaDialog` com "saiu da escala";
  - link "a venda passou para DD/MM";
  - `ResumoSection.tsx:391-411` troca "em aberto" por devolução e retido;
  - texto da caixa do cancelado (`EventHeader.tsx:408-420`);
  - "Editar tudo" escondido no cancelado.
- **Portas de venda na tela**:
  - `VendaPanel` e `AcrescimosPanel.canEdit` (`ColecoesComerciaisPanel.tsx:67`), `NotasFiscaisPanel`, `ReembolsosPanel` e `PagamentosPanel` usam `can_edit_venda_cancelado` / `can_edit_pagamentos` no cancelado;
  - o erro de `FinanceiroSection.tsx:379-381` passa a mostrar `error.message`;
  - editar e excluir comprovante passam a mostrar o erro (hoje nenhum);
  - `OrcamentoPanel` sem ações no cancelado;
  - `GrupoPanel` sem "Desfazer agrupamento" do dia cancelado.
- **Marcado**:
  - "Excluir ou cancelar" e "Analisar e decidir" deixam de ficar desabilitados;
  - `SumiuDoGoogleBanner` ganha `onCancelar` (`w-full sm:w-auto`);
  - os textos "chega na próxima entrega" (`SumiuDoGoogleBanner.tsx:68-69`, `EventHeader.tsx:39-41`, `EventoMarcadoError.MENSAGEM`) são reescritos.
- **Financeiro**:
  - `ComissoesPage`: `formatDate` (`:40-43`) fatia a string, sem `new Date("AAAA-MM-DD")`, que mostra um dia antes justamente no dia 1º das linhas que a reconciliação cria; filtro e 4º card "No banco"; colunas tipo e ciclo;
  - `PagamentoItemViews` **muda**: mostra as `commission_lines` e passa a mandar `valor_esperado: item.amount` para `bv` **e** `expense` (hoje só `bv`, `:112-116`; adotado, R11);
  - `GastosExtrasPage` e `lib/gastos.ts` com o tipo `cliente` (rótulo, carga e reenvio de nome e PIX) e campos travados por `expense.locked`;
  - DRE nova com a linha "↳ Retido de cancelamentos" por `n_cancelados` e `?? 0` em `:171`;
  - sublinha no Dashboard Comercial (somada à do desconto) e em `/admin/desempenho`;
  - `EventosCancelamentosPage` com o resumo, todas as devoluções e `no_banco` (`:29-32`), e o PIX só com `show_financeiro`.
- **Sino**: ícones dos dois kinds em `NotificacaoItem.tsx:7-13`.

**Por quê.** A FR-026 e os Princípios V, IX, XI e XIII. Arquivos que o plano não citava: `FinanceiroSection.tsx`, `lib/eventAttachments.ts`, `ColecoesComerciaisPanel.tsx`, `PagamentoItemViews.tsx`, `lib/eventInline.ts` e `EventEditPage`.

**Alternativas consideradas.**
- A prévia na chave do impacto: proibido.
- Travas por papel: proibido.
- Uma prop opcional "o que foi pedido" no `ExcluirEventoDialog`, sem uso: código morto até a 2a, que vai desenhar o bloco com o dado dela.

**Decisões do dono que amarram.**
- D27.
- 1c-Q6 = A.
- 1c-Q9 = A: motivo só para Comercial, Financeiro e Superadmin (já é `show_comercial`).

---

## R28: verificação, com harness `main` × branch, scripts e verifies antigos. [Princípio VIII] + [R]

**Decisão.**

- **`verify_306.py`** herda o chão do `verify_303.py`:
  - dublê `GoogleFalso` (`:274`);
  - guarda de ambiente (`:927`);
  - trava de e-mail (`:1013`);
  - `_esperar_threads` (`:519`).

  O dublê substitui `service.delete_event` em **todo** cancelamento.
- **Harness `main` × branch**, que nasce do zero:
  - `git archive` do `git merge-base` numa pasta temporária, com os dois lados em subprocesso;
  - comparação exata (Decimal a 0,01, percentual a 0,1);
  - relógio fixo trocando `datetime` em `app.financeiro.routes`, `app.api.financeiro_read` e `app.financeiro.dre_ops`;
  - `ensure_recurring_entries` neutralizado (ele commita no GET);
  - Jinja lido por `template_rendered`.

  É exigido nos cenários 1, 14b, 17, 20, 23 e 41 e na regressão das cobranças sem devolução.
- **`contagem_pre_deploy.py`**: só leitura, por SSH, com a lista da spec (Premissas, "Deploy") mais:
  - `a_pagar` < 0 com evento;
  - `no_banco` por mês;
  - ciclos abertos de soma zero com linha de valor (grupo aberto da 267c);
  - órfãos `a_pagar`;
  - BV não pago de cancelado `legado`;
  - devoluções com tipo nulo e pendentes ligadas;
  - devolução ligada a evento vivo;
  - gasto aprovado fora de `CATEGORIES`.
- **Contagem: 59 cenários vivos.** A spec tem 57 (45 números mais 12 sufixos). O plan **numera dois novos**, que entram na spec pela Living Spec (R30) e contam:
  - **37b**: comprovante de 200 num satélite → retido e comissão do principal refeitos (R13);
  - **38c**: corte com a base paga, depois desfazer, depois sync → Σ 75 (R14).

  Ficam como **variantes** (não mudam a contagem):
  - **38-comprovante**: comprovante no dia `dia` com o principal vivo → nada refeito; guarda de pago abaixo do devolvido (R13);
  - **9/10-desfazer**: desfazer, abrir Comissões e a Planilha, corrigir um comprovante → Σ = alvo nos três momentos (R14);
  - **16/17-`paid_amount`**: BV pago depois do ato fica pelo pago; desfeito, volta ao proporcional (R9);
  - **16b**: cheia 0 em cortesia/permuta com valor e em evento sem vendedor (R4);
  - **2 e 8**, com `hoje` no dia 2 e no dia 10: prévia = execução (FR-011) e a mutação "simular escreve" (R2);
  - **39**: depois de cancelar o resto do grupo, "Alterar devolução" do dia refaz o retido e a comissão do principal (R12);
  - **44**: corte com ensaio e depois "Cancelar todos" com ensaio → 2 sinos por pessoa da equipe de Ensaio (R17).

  A contagem "58" do rascunho do plan e o "57 → 59" do rascunho desta pesquisa ficam corrigidos assim em todo artefato (Contexto, Fundação, linha VIII, pontos da Living Spec).
- **Portões por fase** (onde um cenário depende de algo que nasce numa fase posterior):
  - **12** e **32**: fecham **sem a DRE** na História 2 (12 com a 1, verde junto da 2); a parte da DRE ("18 nas quatro", "DRE com o retido inteiro") fecha na **História 3**, quando a DRE nasce;
  - **21**: a parte **virtual** fecha na **História 3** (o regime `virtual` nasce na 2, e o filtro de tipo está em `cancelados_do_periodo`); a parte de satélite reabre na 5; a **multa ligada ao cancelado** é **semeada por ORM** com a categoria `SpecialExpense.CATEGORY_MULTA_CANCELAMENTO`, criada na **Fundação**, e não depende da História 6;
  - o **5** ("já cancelado" e clique duplo) **não** está verde antes do núcleo: no HEAD, `api_cancelar_evento` responde 400 (`agenda_write.py:609-610`), e o cenário espera 409 `ja_cancelado`.
- **Verifies antigos a rodar de novo**:

  | Verify | O que muda |
  |---|---|
  | `verify_303` | c12 em `:2339`; `MSG_MARCADO` em `:167` |
  | `verify_267` | `:278-289`; lê o bloco `cancelamento` de um `legado` |
  | `verify_267b` | `:200` |
  | **`verify_267c`** | `S:C` e `S:C:pago` |
  | **`verify_305`** | `valor_esperado` (agora também no `expense`); o 15c põe `cancelled_at` à mão em `:810-820`; prova que `_montar_acrescimos` fatiado não muda o vivo (R20). Pode quebrar já na **História 1**, porque `marcar_status_do_bv` substitui o ramo BV da 305 (`financeiro_write.py:163-194`), e de novo na **História 4**, pela extração |
  | **`verify_215b`** | — |
  | `verify_299`, `verify_205` (`:1181`, `:1298`), `verify_266`, `verify_258`, `verify_256` | rodar de novo |
  | `verify_273` (base 8/15), `verify_301` | o 409 novo em `set_event_orcamento`, antes da venda e da autoria da 301 |
  | `verify_272` | `DESTINATARIOS_POR_KIND` com dois kinds novos |
  | `verify_238` | `assign_role` com a condição do e-mail |
  | `verify_271` | `GET /api/dashboard` (Performance e cobrança da Home) |
  | `verify_307` | arquivos em comum com a 307 |

**Por quê.** Princípio VIII: o verify nasce vermelho, antes do núcleo. Nada versionado serve para a comparação `main` × branch.

**Alternativas consideradas.**
- `git worktree`: suja o repositório.
- Comparar contra números gravados: não pega regressão nova.

**Decisões do dono que amarram.** D34 (uma entrega; as Histórias fecham em ordem) e a leitura 5.

---

## R29: o que a 305, a 267c e a 215b mudaram no desenho (síntese)

| Feature | O que mudou (HEAD) | Consequência na 306 | R |
|---|---|---|---|
| 305 | `travar_evento` (`orcamento_evento_ops.py:788-799`): ordem evento → dependentes, mas relê 4 colunas | é a regra; o ato tem T1 próprio | R24 |
| 305 | `substituir_acrescimos` por `id`, BV pago intocável, `valor_visto`, 400 `items`, mas ainda apaga e recria (`comercial_ops.py:156-414`, `:407-411`) | montagem extraída e fatiada; o cancelado grava no lugar; no-op depois da trava | R20 |
| 305 | `acompanhar_bv_da_venda` (`:492`) e `estado_da_venda` (`:438`), proporção pelo líquido; pula cancelado e satélite (`:531-532`) | o corte reusa, **uma vez**; o PATCH no cancelado não move o BV | R15, R20 |
| 305 | `bv_que_acompanha` (`orcamento/quote_ops.py:58-85`), conta única | `bv_do_retido` e `comissao_do_retido` sobre ela | R4, R8 |
| 305 | `set-status` do BV com `valor_esperado` contra o cheio (`financeiro_write.py:163-194`) | 409 eterno sem mudança; `paid_amount` + função única nas duas portas; o 409 ganha o código `valor_mudou` | R9 |
| 305 | `_serialize_acrescimos` já manda `bv_pix` (`agenda_read.py:560`) | no cancelado, só com a flag | R19 |
| 305 | `api_set_acrescimos` sincroniza a comissão (`agenda_write.py:1637`) | no-op no cancelado; o Superadmin chama `reaplicar` | R20 |
| 305 | Jinja da aba Comercial com `estado_da_venda` (`calendar/routes.py:837`) e ids (`:905`) | recusa no despachante, antes do handler | R19 |
| 305 | `gravar_acrescimos_do_orcamento`/`bv_nasce_no_vinculo` recusam cancelado | falta só o 409 em `set_event_orcamento` | R19 |
| 267c | `liquidar_periodo` trava sem ordem (`comissoes_ops.py:249-258`) | `order_by(id)`; a corrida "paga de 20" se serializa na linha | R24 |
| 267c | item partido aberto × `:pago` (`financeiro/routes.py:941-959`) | `commission_lines` nos dois; o `continue` pelo predicado só no aberto | R6 |
| 267c | desfazer (`:296-361`) com `EventLog` depois de travar as linhas, em hora de São Paulo | trava dos eventos antes; não é molde; resolve a leitura 11 e o achado da FR-057 | R14 |
| 267c | `set_commission_status` Jinja (`financeiro/routes.py:1561-1582`) recusa só pago → x | guarda de uma linha: linha de evento cancelado não muda por ali | R6 |
| 305 | `PagamentoItemViews` manda `valor_esperado` só no `bv` (`:112-116`) | passa a mandar também no `expense`; o servidor confere a devolução de cancelado | R11 |
| 215b | `taxa_e_vendedor_negados` (`event_ops.py:1125`), via `_erro_de_taxa_ou_vendedor` (`agenda_write.py:89-101`) | a regra do cancelado roda **antes** | R19 |
| 215b | `_mesma_taxa` e `_mesmo_vendedor` (`event_ops.py:1105-1123`) | reusados para "mudou?" no recongelamento e no PATCH em bloco | R1, R19, R20 |
| 215b | flags `pode_mudar_taxa`/`pode_trocar_vendedor` (`agenda_read.py:998-999`) | **no cancelado**, E com `can_edit_venda_cancelado`; no vivo, como a 215b as calcula | R19 |
| 215b/305 | `PATCH /api/events/<id>` grava a venda (`_gravar_venda_da_edicao`) | 409 `cancelado` quando a venda chega diferente | R19 |

---

## R30: NEEDS CLARIFICATION, nenhuma. As leituras deixadas ao plan estão confirmadas.

**Nenhuma pergunta ao dono.** O único caso que não foi perguntado, o "Alterar devolução" do dia cortado depois de o principal ter sido cancelado inteiro, é **derivado da D28** ("Acompanham") e fica explícito na Living Spec (ponto 6), onde o dono o vê (R12).

**Fica fora da spec**, sem mudar texto: a guarda de pago abaixo do devolvido em dia **vivo** do grupo (FR-038, Princípio IV); vai ao `docs/05`.

**Living Spec antes do `/speckit-tasks`** (Princípio VII). Cada ponto tem **um status só**: entra na spec como alteração, com o mesmo texto no plan. Os pontos 1 e 6 podiam ser lidos da spec (FR-039; FR-049 com a FR-004), mas entram como texto explícito para a spec dizer o que o código faz.

1. **FR-039/FR-040 e leitura 10**: `paid_amount`; o BV pago (no ato ou depois) e depois desfeito volta ao proporcional (R9). Variante 16/17.
2. **FR-057**: a regra nova de `_sync` com ajuste vivo e base de volta a `a_pagar` (R14); entra o cenário **38c**.
3. **FR-047/FR-048**: `PATCH /api/events/<id>` no cancelado dá 409 `cancelado` **para todos** quando um campo de venda chega diferente do gravado, com a frase "corrija pela aba Comercial"; "Editar tudo" some no cancelado (R19).
4. **FR-018/FR-049**: comprovante num dia de grupo refaz o cancelamento `venda` do principal; entra o cenário **37b** e a variante 38-comprovante (R13).
5. **`valor_esperado` no `expense`** (firme, adotado): o `PagamentoItemViews` manda `valor_esperado` para `bv` e `expense`, e o set-status da devolução de cancelado dá 409 "A devolução mudou para R$ X" (R11).
6. **P-5, FR-017 "no dia cortado" e FR-004**: com o principal cancelado inteiro depois, o "Alterar devolução" do dia (e o comprovante do dia) refaz o retido e a comissão do principal. Derivado da D28; o clarify de 15/10 vale para o grupo vivo. Variante do **39** (R12).
7. **Entidades** (seção "Entidades" da spec): as colunas que a spec não lista, `commission_cost`, `sale_handed_over` e `special_expense_id`, além de `paid_amount` (ponto 1) (R1).
8. **RBAC da spec**: entram as três portas que faltam, com os 409 novos: `PATCH /api/events/<id>` (`cancelado`), `DELETE /api/events/<leader>/grupo/satelites/<sat>` (`cancelado`) e `POST /api/financeiro/pagamentos/set-status` (`bv_nao_esta_a_pagar` e `valor_mudou`, este com "o BV mudou" ou "a devolução mudou"; o 409 da 305 ganha o código) (R19).
9. **Jinja, além da FR-047**: o despachante `event_detail` recusa `update_comercial`, `update_sale`, os três de comprovante e os três de reembolso **para todos**, inclusive o Superadmin; `set_commission_status` recusa linha de evento cancelado (R6, R19).
10. **Os 18 códigos 409** desta entrega, como contrato: `cancelado`, `ja_cancelado`, `ensaio`, `grupo_mudou`, `sem_outro_dia_vivo`, `cache_pago`, `devolucao_pendente`, `max_devolucao_mudou`, `tente_de_novo`, `nao_cancelado`, `regime_sem_retido`, `abaixo_do_piso`, `acima_do_teto`, `pago_abaixo_do_devolvido`, `bv_nao_esta_a_pagar`, `valor_mudou`, `devolucao_travada`, `estado_mudou` (R1).
11. **A decisão da FR-062**: `cancel_ops.ao_cancelar` recebe `(ALCANCE_TODOS, None)` no avulso e em cada dia do "todos", `(ALCANCE_SO_ESTE_DIA, None)` no corte de dia não principal e `(ALCANCE_SO_ESTE_DIA, novo)` depois da passagem (R15).
12. **FR-070/FR-071/FR-072**: a multa é **por escalação** (vaga × dia): um artista em 2 dias ou 2 vagas tem 2 linhas e pode ter 2 multas; 0 e vazio são ignorados no ato e no `POST …/multas`, e só negativo ou inválido dá 400 no campo; no `POST …/multas`, o pedido sem nenhum valor > 0 depois disso dá 400 `fields.multas` "Informe a multa de ao menos um artista" (R18).
13. **Cenários**: **59 vivos**, com 37b e 38c numerados, e as variantes do R28 (entre elas a prova da FR-011 no 2 e no 8).

**Leituras confirmadas contra o HEAD:**
- **P-24 e P-25**: `total_recebido` usa `coalesce` (`cancel_ops.py:65-72`); `comprovantes_sem_valor` conta `amount IS NULL`; o cancelado sem venda e sem pago fica fora de `quantidade`.
- **P-26**: Google depois do commit, com a trava lida a cada chamada (R23).
- **P-27**: recusa no despachante Jinja (R19).
- **P-28**: 0 na tela Jinja do cancelado, com dívida (R21).
- **P-29**: prefixo `NOTA_COMISSAO_PROPRIA_DO_DIA` (R16).
- **FR-062**: ponto 11 acima (R15).
- **Leitura 10**: `paid_amount` (R9).
- **Leitura 11**: desfazer sem ramo novo (R14).

**Decisões de modelo fechadas antes da migration** (R1; colunas no data-model §1–§3):
- `paid_amount`; `commission_rate Numeric(6,3)`; `commission_cost` pela mesma base de custo da comissão;
- **`sale_handed_over Boolean NOT NULL default false`** no antigo 1º dia;
- `special_expense_id` com `SET NULL` e UNIQUE; `acrescimo_id` com `SET NULL` e UNIQUE;
- **`day_event_id` com `CASCADE` e `NOT NULL`**;
- FKs de vendedor sem `ondelete`, com o bloqueio em `delete_user`;
- `foreign_keys=` em toda relação;
- before/after da venda e do cheio no `dia`.

**Nomes** pela tabela única do data-model §6: `cancel_ops.ao_cancelar`, `group_ops.CAMPOS_DA_PASSAGEM`/`TABELAS_DA_PASSAGEM`, `group_ops.dias_vivos`, `SpecialExpense.CATEGORY_MULTA_CANCELAMENTO`, `ALCANCE_TODOS`/`ALCANCE_SO_ESTE_DIA`, `CODIGO_EVENTO_CANCELADO`, `CODIGO_VALOR_MUDOU` e os demais códigos 409 (18 ao todo), com a união TS `CodigoRecusaCancelamento` em `lib/eventOps.ts`. `NOTA_CICLO_CANCELAMENTO` **não existe** (R1).

---

## Riscos aceitos

**Herdados da spec** (Premissas, "Riscos aceitos", 1–19), sem repetir o texto:
- PIX de repasse sem marcar a Planilha nos dias 1 a 5;
- desconto de vendedor sem repasse futuro;
- DRE sem fechamento de mês;
- tipo nulo no evento vivo;
- tela Jinja de Comissões;
- "no banco" no bundle antigo;
- 409 "já cancelado" na janela do deploy;
- rollback assimétrico;
- descartável do teste na página;
- taxa padrão congelada até a 1e;
- comissão paga de venda viva até a 1e;
- mês do cancelamento = mês do registro;
- retido do dia cortado no mês do evento;
- tela do cancelado editável até a 1c;
- 3D e NFC ficam com o antigo 1º dia;
- cobrança da Home muda de regra;
- todo ensaio cai até a noite 7;
- BV pago cheio antes do cancelamento;
- página de Cancelamentos sem leitor Financeiro até a 1c.

**Novos desta pesquisa** (vão ao `docs/05` quando forem dívida):

1. **"Pago" da Planilha contra a linha nova da reconciliação.** Uma instrução de liquidação que começou antes da linha nova não a vê, e ela fica aberta naquele ciclo. Não se perde: aparece na Planilha. Saída futura: `pg_advisory_xact_lock` por beneficiário em `liquidar_periodo`, `pay_seller_month` e T4.
2. **Deadlock residual (40P01)** com escritores sem ordem, o `sync_events` e o `delete_client` (o `UPDATE` em lote de `client_ops.py:249`): vira 409 `tente_de_novo` nos endpoints da 306 (no POST de comprovante, com o arquivo salvo removido, R13); fora deles, 500 raro.
3. **`EventLog` do desfazer da 267c** com `created_at=now_sp()` (`comissoes_ops.py:358`): aparece 3 h antes.
4. **Guarda de pago abaixo do devolvido em dia vivo do grupo**: excluir um comprovante do principal vivo pode deixar o grupo abaixo da devolução do dia cortado.
5. **`comissao_exibida_do_evento`** mostra 0 na tela Jinja do evento cancelado (P-28).
6. **`comissoes()` Jinja** (`financeiro/routes.py:1505-1541`) sem os filtros e com `total_a_pagar` em dobro. A troca de status de linha de cancelado pelo `set_commission_status` Jinja **não** é mais risco: a guarda de uma linha a fecha (R6).
7. **Estorno órfão de exclusão nos dias 1 a 5** aparece em dois meses na tela de Comissões (pelo resgate do mês corrente).
8. **Set-status de gasto sem conferência de valor**: o lote (API `financeiro_write.py:326-338`; Jinja `financeiro/routes.py:1397-1404`) e o individual do Jinja (`:1182-1189`), que passa a travar o evento mas não manda `valor_esperado`. Um "pago" com tela velha pode cair sobre a devolução recém-alterada. A API individual confere (R11).
9. **Ensaio que fica no Google** (falha, ou trava ligada) volta no sync como ENSAIO órfão, o mesmo buraco de `delete_ensaio` hoje. O show não volta.
10. **Timeout depois do commit.** Com muitos dias e ensaios, as remoções em série podem estourar o gunicorn depois do commit. A tela vê 502, e a repetição recebe 409 `ja_cancelado`.
11. **`sale_count`** passa a contar só `original_id IS NULL` e muda meses históricos com estorno legado (registrar no `docs/03`).
12. **`group_label`** conta o dia cancelado (`financeiro_read.py:410-412`, `vendas_ops.py:322-326`): cosmético, da 1c.
13. **E-mail de remoção em `assign_role`** sai antes do commit e lê `is_cancelled` sem trava: corrida rara com o ato.
14. **Escalar alguém novo num cancelado** ainda manda convite (`casting_ops.py:216`): trava geral da 1c.
15. **`/admin/desempenho`** agrupa por nome e usa mês padrão em UTC (`admin_config_read.py:128`): o retido é mapeado de id para nome.
16. **Cobrança da Home** também desconta devolução lançada à mão em venda viva (0 no espelho).
17. **`is_devolucao_cliente`** (`models.py:1159-1162`) fica como código morto, com a docstring apontando `filtro_devolucao`.
18. **`delete_ensaio`** (botão) e a troca de tipo seguem escrevendo no Google sem trava (dívida 69, sem o "cancelar").
19. **Datas de borda no dia 1º** em Comissões só se corrigem com o bundle novo (`formatDate`).
20. **Comprovante órfão no `POST /api/gastos`.** A recusa nova (409 `devolucao_travada`, devolução ligada a evento cancelado), como a 400 de validação de hoje, acontece depois de o comprovante ser salvo (`gastos_write.py:53-57`): o arquivo fica no disco sem gasto. Raro (criar devolução à mão ligada a cancelado) e já existe hoje na 400.
