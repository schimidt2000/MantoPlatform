# Relatório de integração — feature 303 (fase de plano)

Raiz: `.`. Os caminhos abaixo são relativos a ela. Nada foi editado nem executado.

**O que decide o plano**

- **Dividir em três entregas**, na ordem sync → dinheiro → sinalizar. A ordem de construção é a mesma em qualquer corte; o que muda é quando se publica.
- **Modelo de dados**: 1 coluna e 1 índice na entrega do sync; 2 tabelas na do dinheiro; nada na de sinalizar.
- **Três decisões de frente caem**: C6 (mover o ciclo da comissão EducaManto), C12 (script em `scripts/oneoff/`) e a parte de V6 que põe lista paginada e a função do resumo como fundação de tudo.
- **Antes do `plan.md`**: a spec precisa das edições da seção 6 (Princípio VII), e a contagem pré-deploy precisa ser rodada e respondida pelo dono.

**Conferido por mim nesta passada**

- Head único `e5a1c7d93b20`: nenhum arquivo o cita como `down_revision` (`migrations/versions/e5a1c7d93b20_formulario_destino.py:21,29`). O id `a7c3e91f4d28` está livre.
- `specs/303-sync-nao-apaga-venda/plan.md` ainda é o template; não existe pasta `specs/298b*`; `.specify/feature.json` aponta para a 303.
- O `EventLog` do cancelamento sai 3 h adiantado: `app/calendar/cancel_ops.py:202-212, 272-305` grava horário de São Paulo sem fuso, e `app/api/agenda_read.py:210-214` lê sem fuso como UTC.
- `_event_commission` não olha cortesia nem beneficiário nulo (`app/financeiro/comissoes_ops.py:656-686`); quem decide é o `should_have` (`:816-826`).
- `pode_excluir` não olha grupo (`app/calendar/cancel_ops.py:57-74`) e `_delete_event_flow` só recusa o líder (`app/calendar/routes.py:4224-4234`).
- `/scripts/oneoff/` é gitignorado (`.gitignore:41`).
- O endpoint de cancelar não passa `remover_do_google` e põe todo erro em `motivo` (`app/api/agenda_write.py:558-565`).
- `fetch_single_event` engole tudo em `None` (`app/calendar/service.py:181-191`).

O restante vem das propostas e dos vereditos, sem reconferência minha.

---

## 1. Modelo de dados final

### Entrega do sync — `calendar_events`

| Coluna | Tipo | Nulo | Default | Observação |
|---|---|---|---|---|
| `google_missing_since` | `DateTime` | sim | nenhum | Horário de parede de São Paulo (`now_sp()`, `app/constants.py:291`), como `cancelled_at`. `NULL` = não marcado. |

- Índice parcial `ix_calendar_events_google_missing_since` com `WHERE google_missing_since IS NOT NULL`, declarado no modelo (`postgresql_where` + `sqlite_where`) e na migration.
- Migration: `migrations/versions/a7c3e91f4d28_evento_sumiu_do_google.py`, `down_revision = "e5a1c7d93b20"`, só `add_column` + `create_index`, sem `UPDATE`. Molde: `b8e4d27a91f5_cancelamento_de_evento.py:26-51`. Reconferir o head na hora de escrever (a 298b é da mesma onda).

Derivado, sem coluna (em `app/models.py`, junto de `:382-395`):
- `is_google_missing` = marca preenchida e `cancelled_at IS NULL`.
- `situacao` com precedência `cancelado` > `sumiu_do_google` > `exclusao_solicitada` > `None`.
- `situacao_desde`.
- Os três valores viram constantes `SITUACAO_*` em `app/constants.py` e um único `export type SituacaoEvento` em `frontend/apps/internal/src/lib/agenda.ts`.

### Entrega do dinheiro — duas tabelas

Migration encadeada: `down_revision = "a7c3e91f4d28"`, só `create_table`. Nenhuma coluna nova em `calendar_events`, `event_acrescimos` ou `commission_payments`.

**`event_cancellations`** (1:1 com o evento)

| Coluna | Tipo | Nulo | Default |
|---|---|---|---|
| `id` | Integer PK | não | |
| `event_id` | Integer, FK `calendar_events.id` ON DELETE CASCADE, UNIQUE `uq_event_cancellations_event_id` | não | |
| `regime` | String(12): `venda` \| `satelite` \| `virtual` | não | |
| `refund_mode` | String(8): `tudo` \| `parte` \| `nada` — escolha no ato, imutável | sim | |
| `sale_value` | Numeric(12,2) — venda congelada | não | `0` |
| `commission_full` | Numeric(12,2) — comissão cheia congelada | não | `0` |
| `commission_seller_id` | Integer, FK `users.id` SET NULL — beneficiário congelado | sim | |
| `seller_id` | Integer, FK `users.id` SET NULL — vendedor do evento no ato | sim | |
| `with_invoice` | Boolean | não | false |
| `retained_tax` | Numeric(12,2) — `NULL` = não se aplica | sim | |
| `created_at`, `updated_at` | DateTime, São Paulo sem fuso | não | |
| `updated_by_id` | Integer, FK `users.id` SET NULL | sim | |

**`event_cancellation_bvs`** (uma linha por acréscimo BV no ato)

| Coluna | Tipo | Nulo | Default |
|---|---|---|---|
| `id` | Integer PK | não | |
| `cancellation_id` | Integer, FK `event_cancellations.id` CASCADE, índice | não | |
| `acrescimo_id` | Integer, FK `event_acrescimos.id` SET NULL, índice | sim | |
| `recipient` | String(200) | sim | |
| `pix` | String(140) | sim | |
| `original_amount` | Numeric(12,2) | não | |
| `negotiated_amount` | Numeric(12,2) | não | |
| `paid_at_cancellation` | Boolean (`pago` ou `no_banco` no ato) | não | false |

- A relação é declarada no filho, como o precedente `Event3DDismissal` (`app/models.py:2340-2350`): `backref("cancelamento", uselist=False, cascade="all, delete-orphan")`. A classe `CalendarEvent` não é tocada.
- Property `EventCancellationBv.counted_amount`.
- Regimes e modos viram constantes em `app/constants.py`.

Derivado: o resumo do cancelado (FR-026). Pago e devolvido são lidos ao vivo; o modo corrente sai de pago × devolvido. Cancelado sem linha é `legado`, ou `virtual`/`satelite` quando o evento for um deles.

### Conflitos de nome resolvidos

| Conceito | Propostas | Vale |
|---|---|---|
| Coluna da marca | `google_missing_since` × `google_missing_at` | `google_missing_since` |
| Valor da situação | `sumiu_do_google` × `sumiu_google` | `sumiu_do_google` (igual ao bloco do detalhe e à ação de auditoria) |
| Bloco do detalhe | `{desde}` × `{percebido_em}` | `sumiu_do_google: {desde}` |
| Kind do sino | — | `evento.sumiu_google`, entidade `calendar_event` |
| Onde congela | tabelas (D1) × 2 colunas em `calendar_events` (C11) | tabelas |
| Resumo | `resumo_cancelado` × `resumo_do_cancelado` | `resumo_cancelado`, `resumos_cancelados` |
| Estado da devolução | `a_pagar/no_banco/paga` × códigos do modelo | códigos do modelo: `payment_status` = `nao_pago` \| `no_banco` \| `pago` |

Uma migration por entrega, encadeadas; nunca dois arquivos com o mesmo `down_revision`. Se o dono preferir o corte da Premissa (sync + dinheiro juntos), vira um arquivo só com a coluna, o índice e as duas tabelas.

---

## 2. Endpoints

### Novos

| Entrega | Método e caminho | Módulo | Gate | Corpo | Resposta | Erros |
|---|---|---|---|---|---|---|
| sync | `GET /api/events/sumidos-google` | `app/api/agenda.py` | `_ve_faixa_sumidos()`: SUPERADMIN ou COMERCIAL pelo papel efetivo | — | `{pode_ver, total, limit, items:[{id,title,start_at}]}`; teto 100; quem não vê recebe 200 vazio | 401 |
| sync | `POST /api/events/<id>/devolver-ao-google` | `app/api/agenda_write.py` | `_can_delete()` depois do 404 | vazio | detalhe (`serialize_event_detail`) + `devolucao_google: {resultado: "recriado" \| "reapareceu"}` | 404; 403; 409 `cancelado` \| `nao_marcado` \| `venda_virtual` \| `sem_data` \| `google_travado`; 502 `google_inconclusivo` \| `google_desconectado` \| `google_recusou` |
| dinheiro | `PATCH /api/events/<id>/devolucao` | `app/api/agenda_write.py` | `_can_delete()` | `{devolucao_total, nome?, pix?, observacao?, imposto_retido?}` | `{ok, resumo}` | 404; 403; 409 não cancelado, regime sem retido, total abaixo do já pago; 400 `devolucao_total`, `devolucao_nome`, `devolucao_pix`, `imposto_retido` |

- Os erros do devolver levam `codigo` no envelope de `json_error`.
- `/api/events/sumidos-google` passa pelo guard do revendedor (`app/__init__.py:55`) e vira palavra reservada sob `/events/`.
- Nenhum módulo novo em `app/api/`: `agenda` e `agenda_write` já estão registrados (`app/api/__init__.py:14-15`).

### Alterados na entrega do sync

| Endpoint | O que muda |
|---|---|
| `POST /api/events/<id>/sync` | Status novo `ausente_no_google` → 409 "Este evento não está mais no Google Agenda. Nada foi alterado." para qualquer evento. Inconclusivo segue 502. Presente + marcado: desmarca e sincroniza. |
| `PATCH /api/events/<id>` e `/basico` | Evento marcado: 200, sem push ao Google, sem aviso, sem desfazer troca de tipo. |
| `DELETE /api/events/<id>` | 409 quando o evento está marcado. |
| `POST /api/events/<id>/cancelar` | Evento marcado: não chama o Google, sem aviso, zera a marca via `desmarcar`. O dinheiro segue a regra da 224. |
| `GET /api/events/<id>/impacto-exclusao` | `acao` = `cancelar` quando marcado. |
| `POST /api/admin/sync/run` (`cleanup_past`) | Por mês: `marcados?`, `movidos?`, `desmarcados?`, `inconclusivos?`, `falhas?`; mensagem reescrita. |
| `GET /api/agenda`, `/agenda/day/<d>`, `/agenda/search` | Resumo ganha `situacao?`, `situacao_desde?`. |
| `GET /api/events/<id>` | `event.situacao?`, `event.sumiu_do_google?: {desde} \| null`; `google_html_link` sai `null` quando marcado ou cancelado. |
| `GET /api/portal/agenda`, `/portal/historico` | Cada item ganha `em_confirmacao?: boolean`. |
| `GET /api/portal/ratings/pending`; `GET\|POST /api/portal/events/<id>/rate[/detail]` | Cancelado fora das listas; 400 "Este evento foi cancelado e não recebe avaliação." |

### Alterados na entrega do dinheiro

| Endpoint | O que muda |
|---|---|
| `POST /api/events/<id>/cancelar` | Corpo `{motivo, devolucao:{modo, valor, nome, pix, observacao?}, bv_negociado:[{acrescimo_id, valor}], imposto_retido}`. Resposta ganha `resumo?`. Campos de erro: `motivo`, `devolucao_modo`, `devolucao_valor`, `devolucao_nome`, `devolucao_pix`, `bv_negociado`, `bv_negociado_<id>`, `imposto_retido`. 409 para já cancelado, líder de grupo, devolução pendente em Gastos Extras e "Tudo" divergente (extra `max_devolucao`). |
| `GET /api/events/<id>/impacto-exclusao` | Chaves novas: `regime`, `sumiu_do_google`, `ja_devolvido`, `max_devolucao`, `com_nota`, `imposto_aliquota`, `bvs[]`, `comissao{beneficiario, cheia, paga, a_pagar}`. `devolucao_sugerida` fica um ciclo. Com `?devolucao=<decimal>` devolve só `{efeito:{devolucao, retido, comissao_cheia, comissao_retido, ja_liquidada, ajuste, ciclo, repasse_em, imposto_referencia}}`; valor inválido → 400 `fields.devolucao`. |
| `DELETE /api/events/<id>` | 409 também para cancelado. |
| `GET /api/events/<id>` | `cancelamento?` = resumo serializado (só com `show_comercial`; comissão, BV e imposto só com `show_financeiro`; PIX só com `show_financeiro`). `kpi` ausente em cancelado. |
| `GET /api/events/cancelamentos` | Cada cancelado ganha `resumo`; `devolucao` legado fica um ciclo. Gate inalterado. |
| `PUT /api/events/<id>/acrescimos`; comprovantes `POST\|PATCH\|DELETE`; `PATCH /api/events/<id>/orcamento` | 409 em cancelado. |
| Gastos: `POST`, `PATCH`, `DELETE`, aprovar, rejeitar, vincular-evento | `GastoLockedError` → 409 com `fields` e `event_id`. Tipo `cliente` preservado. `_expense_dict` ganha `locked?`, `event_cancelled?`. |
| `GET /api/financeiro/comissoes` | `status` pode ser `no_banco`; `tipo?`, `original_id?`, `evento_cancelado?`, `ciclo?`; `kpis.total_no_banco?`. |
| `GET /api/financeiro/pagamentos` | Item de comissão ganha `commission_lines?`; BV pelo valor de `bv_da_planilha`. |
| `GET /api/financeiro/dashboard` | `dre.*.retido_cancelamentos?`, `n_cancelados?`; `paineis.cancelamentos?`; barra "Retido de cancelamentos"; `monthly_trend[].retido?`; nota a emitir com `cancelado?`, `retido?`; Top Vendedores com o retido. |
| `GET /api/vendas/pipeline` | `kpis.retido_cancelamentos?`; o total inclui o retido. |
| `GET /api/admin/desempenho` | Filtra cancelado; `vendas[].retido?`, `cancelados?`; `totals.retido?`. |
| `GET /api/clientes/<id>`, `/api/clientes/`, `/metricas` | Total com o retido; contagens sem cancelado. |
| `GET /api/dashboard` | Performance ignora cancelado. |

### Entrega de sinalizar (sem migration)

- `incluir_cancelados` em `/api/agenda` e `/agenda/day`.
- `/events/cancelamentos` com gate SUPERADMIN ou FINANCEIRO e filtros `mes`, `devolucao=nao_pago|no_banco|pago|sem`.
- Recusas em vincular ensaio, tag NFC e grupo.
- `situacao` nas fichas e em Gastos Extras.
- Card e botão na DRE e no Dashboard Comercial.

Todo campo novo de payload existente nasce opcional no TypeScript.

---

## 3. Funções de núcleo e toques em `routes.py`

### Entrega do sync

**`app/calendar/service.py`**
- `consultar_evento(calendar_id, google_event_id, *, service=None) -> ConsultaEvento(desfecho, item, motivo)`. Nunca levanta. `fetch_single_event` fica intocada.
- `insert_event(..., *, all_day: bool = False)`.

**`app/calendar/sumico_ops.py`** (novo)
- `PresoAoEvento` (dataclass imutável: venda, recebido, n_comprovantes, tem_contrato, n_escalados, grupo; `.vazio`, `.descricao()`).
- `preso_ao_evento(event)`.
- `filtro_marcados()` — predicado único de faixa, reconferência e situação.
- `marcar(event, preso, *, contexto) -> datetime | None` — UPDATE condicional; devolve o carimbo que gravou; `refresh` depois.
- `desmarcar(event, *, motivo, actor_name, actor_role) -> bool`.
- `limpar_mes(items, year, month, *, simular=False) -> ResultadoLimpeza` e `_decidir_candidato`.
- `reconferir_marcados()`, `listar_marcados()`, `faixa_sumidos(limite)`.
- `devolver_ao_google(event_id, *, actor)`, fatiada em `_validar`, `_exigir_ambiente_liberado`, `_bloquear_e_revalidar`, `_recriar_no_google`, `_registrar_devolucao_google`.

**`app/notificacoes/notificacoes_ops.py`**
- `KIND_EVENTO_SUMIU_GOOGLE`, entrada em `DESTINATARIOS_POR_KIND` (`:47-61`), `notificar_evento_sumiu_google(event, *, marcado_em, preso)`.

**`app/config.py`**
- `_suppress_calendar_event_writes()` e `Config.CALENDAR_SUPPRESS_EVENT_WRITES`, ao lado de `:121-142`.

**`app/talent_portal/`**
- `_role_summary` ganha `em_confirmacao`.
- `_event_ids_in_window` e `_require_open_event` recusam cancelado.

**Toques em `app/calendar/routes.py`** (nada é movido):
1. `_cleanup_stale_events` (`:341-390`): o corpo vira delegação a `sumico_ops.limpar_mes`; o retorno passa a ser `ResultadoLimpeza`.
2. `_delete_event` (`:320`): limpa as tabelas satélite de cada `event.ensaios` e chama `apagar_por_entidade("calendar_event", id)`.
3. `_sync_single_event_flow` (`:4191-4208`): usa `consultar_evento`.
4. Wrapper Jinja `sync_single_event` (`:4246`): um `elif` para o status novo.
5. Remover `fetch_single_event` do import de topo.

`force_sync` do Jinja: zero linha.

**Outros toques**
- `app/calendar/sync.py:74-85`: `reconferir_marcados` antes do laço, leitura do resultado, `rollback()` no `except`.
- `app/api/admin_config_write.py:104-108`: idem.
- `app/calendar/event_ops.py:637-643`: condição `and not event.is_google_missing`.
- `app/calendar/cancel_ops.py:278` e `:288`: duas linhas (não remove do Google; `desmarcar`).

### Entrega do dinheiro

**`app/financeiro/comissoes_ops.py`**
- `_beneficiario_comissionado(event, settings)`, extraído do `should_have`.
- `comissao_cheia_do_evento(event, settings) -> (Decimal, int | None)`.
- `comissao_do_retido(cheia, retido, venda)`.
- `reconciliar_comissao_do_cancelado(event, alvo, *, hoje=None, simular=False)`.
- `primeiro_repasse_aberto(seller_id, hoje)` e `DIA_DO_REPASSE`.
- `ciclo_de_pagamento_da_linha(cp)`, `tipo_da_linha(cp)`, e um helper único para "linha que abre ciclo".
- Guarda no topo de `_sync_commission_payment` (`:804`): `if event.is_cancelled: return`.
- `_pending_reversals_query` (`:333-336`) e a cópia inline ganham `event_id IS NULL`.
- `no_banco` entra em `_month_scoped_query` (`:300`).
- `comissao_exibida_do_evento` (`:285-286`) passa a ler o resumo.

**`app/calendar/cancel_ops.py`**
- `cancelar_evento` fatiada em `_validar_devolucao`, `_validar_bv`, `_validar_imposto`, `_congelar`.
- `CancelValidationError(message, field=None, status=400)`.
- `alterar_devolucao`, `previa_cancelamento`.
- `ResumoCancelado`, `resumo_cancelado`, `resumos_cancelados` (em lote), `serializar_resumo_cancelado`.
- `cancelados_do_periodo(inicio, fim, *, seller_id=None, educamanto_only=False)`.
- `totais_cancelamentos`, `retido_por_vendedor`.
- `filtro_devolucao` — predicado único: categoria + evento + aprovado.
- `bv_da_planilha(acrescimo)`.

**`app/financeiro/dre_ops.py`** (novo)
- `ROTULO_RETIDO`, `gastos_extras_do_periodo`, `tendencia_mensal`.

**`app/gastos/gastos_ops.py`**
- `GastoLockedError`, `devolucao_de_cancelado`, ramo `cliente` com `tipo_atual`.

**`app/financeiro/vendas_ops.py`**
- `build_kpis(..., cancelados=())`.

**Toques em `app/financeiro/routes.py`** (Jinja vivo; nada movido nem apagado):
1. `_compute_drg` (`:205-257`): parâmetro `cancelamentos=None`, quatro somas sob `if cancelamentos and cancelamentos["quantidade"]`, duas chaves novas.
2. View `dashboard()`: chamadas a `dre_ops` e `cancel_ops`, ticket médio, filtro de Recebimentos Previstos, selo da nota embutido em `event_title`, Top Vendedores.
3. `_build_bv_items` (`:870-901`): `bv_da_planilha` por import tardio.
4. `_build_commission_items` (`:904-961`): chave `linhas` e a condição do `continue`.

Em `app/templates/financeiro/dashboard.html`: uma linha, condicionada a `drg_total.n_cancelados`. Em `app/calendar/routes.py`: nada.

---

## 4. Conflitos e emendas que mudam o desenho

### Sync, aviso e devolver

1. **Unidade de trabalho da limpeza.** A frente do aviso pede savepoint por evento com um commit no fim do mês; a do sync pede commit por evento. Vale commit por evento com `try/except` e `rollback`, porque `sync_events` e `_mark_month_synced` comitam sozinhos (`app/calendar/sync.py:78-80`). A emenda entra junto: materializar os ids e reler cada evento com `db.session.get`; `None` significa que já saiu, e não é falha.
2. **O que `marcar` recebe e devolve.** Lista de textos × três números × dataclass. Vale `PresoAoEvento`, lido pela decisão, pelo histórico e pelo sino; `marcar` devolve o carimbo que gravou. O parâmetro `avisar` sai do desenho até a contagem.
3. **Exceção do técnico de som.** Vale a versão que exige `event_type == SHOW` (FR-001 diz "em todo SHOW"). O orçamento cria a mesma vaga fora de SHOW.
4. **Evento presente que nunca vem na lista** (série recorrente-mãe). Vale comparar os cinco campos antes; se nada mudou, não chamar `sync_events`, e contar no resumo do ciclo. Sem isso fica em laço a cada 10 minutos.
5. **Disjuntor.** O primeiro inconclusivo de rede, 5xx ou credencial encerra as consultas daquela rodada: o cliente do Google espera 60 s por chamada, e o proxy corta em 180 s (`frontend/server.js:619`).
6. **Botão Sincronizar do evento marcado.** Uma frente some com ele; a spec (linhas 383-387) diz que ele existe e responde. Vale: o servidor anula `google_html_link` quando marcado ou cancelado, e a tela mostra Sincronizar por `google_html_link || sumiu_do_google`. Cancelado fica sem os dois, o que entrega a parte da FR-037 de graça.
7. **Flags novas.** `can_restore_google` e `can_edit_refund` × reusar `can_delete`. Vale reusar `flags.can_delete` combinado com o estado que o servidor manda: duas de três frentes dizem isso, e é o mesmo gate do endpoint.
8. **"Cancelar e devolver o dinheiro" pode apagar um satélite marcado.** O botão abre o diálogo que decide por `pode_excluir`, que não olha grupo. Vale: `acao = "cancelar"` para evento marcado e `DELETE` recusado com 409. Com isso saem do desenho o `also_from_google` condicional e as duas linhas de ensaio (caso que não ocorre).
9. **"O que está em jogo".** Segunda requisição ao impacto × dados do detalhe. Vale o detalhe já carregado (`kpi.bv_total` em `app/api/agenda_read.py:405`, `received_total` em `:1035`), porque `resumo_impacto.comissoes` só lista linha já criada. `bv_total` em `resumo_impacto` sai.
10. **Devolver quando o evento já voltou e foi editado enquanto marcado.** A FR-012 promete "dados atuais". Vale: comparar; se diferente, empurrar o cabeçalho para o id velho com `_push_cabecalho_ao_google` e só então desmarcar. No reaparecimento automático continua valendo o Google.
11. **`source = "platform"` na devolução.** Vale a troca condicional: só quando há vaga de personagem fora do título. Incondicional mudaria para sempre um evento nascido no Google, sem decisão do dono.
12. **Carimbo do histórico.** `EventLog` novo não recebe `created_at` (vale o default UTC). Horário de São Paulo sem fuso só nas colunas de negócio.
13. **Devolver: ordem e compensação.** Vale montar `EventLog` e dar `flush` antes do Google, com `actor_role[:60]`, e revalidar tudo depois do bloqueio. O delete compensatório sai: sem cenário ele é código não verificado. Fica o log do órfão, como na criação.
14. **Dublê do Google no verify.** Troca por função × troca de `service.build` e `service.load_credentials`. Vale a segunda, com falha fechada, disjuntor de rede, contador de fugas e credencial por chamada (senão duas variantes do cenário 13 passam a vazio).
15. **Lista paginada.** Sai da fundação: a spec manda registrar como dívida (linha 775).
16. **Ajuste do verify_205.** Vale passar `outros_vivos` em vez da lista vazia, mais o stub de credencial. Só o stub não para o estrago de hoje no espelho e esvazia o V7.2.

### Dinheiro

17. **Comissão cheia.** Uma função só (`comissao_cheia_do_evento`), usada no congelamento e na prévia. `_event_commission` cru daria comissão a cortesia e a evento sem vendedor.
18. **Beneficiário.** Linha nova usa `commission_seller_id` congelado; ajuste de linha liquidada usa o `seller_id` de quem recebeu. O recorte comercial (FR-032) usa `seller_id` congelado, então não é preciso travar a troca de vendedor.
19. **C6 cai.** A regra "linha a pagar com `payable_from` e sem a marca da 299" casa com toda linha criada pela própria reconciliação e separa `sale_date` de `payable_from` no recálculo. Vale uma invariante só: linha atualizada no lugar nunca muda de data. A comissão EducaManto a pagar de evento cancelado fica no ciclo em que já estava. É zero código; comunicar ao dono.
20. **C12 cai.** `scripts/oneoff/` não chega ao Render. A 303 entrega só a listagem em modo leitura, em `specs/`. Mexer em estorno legado vira correção de Nível 2 depois da resposta do dono.
21. **Regra geral da reconciliação.** `falta == 0` cancela toda linha a pagar do evento; nunca fica linha a pagar de R$ 0,00. `audit()` por linha. Nota por prefixo. `with_for_update` só fora da simulação.
22. **"Repasse aberto".** Três definições nas propostas. Vale um predicado: linha a pagar com valor diferente de zero que não seja estorno órfão. Usado em `primeiro_repasse_aberto`, `month_status` e no `continue` do builder.
23. **Devolução pendente.** Cancelar é recusado enquanto houver "Devolução a cliente" pendente ligada ao evento. Aprovar e rejeitar entram na trava. Criar gasto `cliente` é recusado no servidor.
24. **`alterar_devolucao` × trava de Gastos Extras.** Escreve direto no ORM, é o único escritor autorizado, e começa bloqueando a linha do evento. `refund_mode` não é regravado.
25. **Concorrência no cancelar.** `with_for_update` no evento; `IntegrityError` no UNIQUE vira 409.
26. **Prévia.** Consulta separada com `keepPreviousData`. Pôr o valor na chave do impacto desmonta o formulário a cada tecla.
27. **Bundle novo com backend antigo.** O diálogo não envia quando o payload vem sem `regime`.
28. **BV da Planilha.** A regra "sem filha → esconde" apagaria o BV de satélite cancelado, até o já pago. Vale a versão por regime.
29. **Quem é dono de "cancelados do período".** `dre_ops` × `vendas_ops`. Vale `cancel_ops`, com recorte por vendedor, para as duas DREs, o Dashboard Comercial, `/admin/desempenho` e a página de Cancelamentos. O filtro de tipo é seguro contra `NULL` (dívida 47, `docs/05_DIVIDA_TECNICA.md:469`). O regime vem da linha congelada, não de `group_leader_id` ao vivo.
30. **Top Vendedores da DRE.** Uma frente deixou fora; outra pôs só na API. O dono respondeu "no total vendido, no ranking e na meta" (spec, linhas 94-96), e os únicos rankings são esse e `/admin/desempenho`. Vale: entra nas duas views por `retido_por_vendedor`. É "número vindo de função comum", que o Fora de escopo admite.
31. **`no_banco` na tela de Comissões.** Necessário para o cenário 21. Muda todo mês que tenha linha no banco; ganha `total_no_banco` para os cards fecharem.
32. **Exclusão de cancelado.** `DELETE` recusa: o caminho recriaria o estorno órfão no ciclo antigo.

### Verify e processo

33. **Aquecimento da Planilha.** Abrir um mês cria salários e recorrentes, e a DRE lê os dois. Abrir M−1 a M+2 antes de qualquer retrato.
34. **Árvore da main.** `git worktree` × `git archive`. Vale `git archive` em pasta temporária, com os dois lados em subprocesso, comparação exata e linha de base em `git merge-base`.
35. **Esperar as threads de e-mail** antes de afirmar "zero e-mail" (`send_async` usa thread).
36. **Guarda contra backend local ligado**: exit 2 se `calendar_auto_sync_at` for recente.
37. **Função do resumo (FR-026)** abre a entrega do dinheiro; não bloqueia o sync.

---

## 5. Ordem de construção e divisão

### Recomendação: sim, dividir — em três entregas

Os nomes `303b` e `303c` são provisórios.

| Entrega | Conteúdo | Migration |
|---|---|---|
| **303** — sync | FR-001 a FR-012, FR-022, FR-023 (marcar, avisar, devolver, desmarcar), FR-024. Da FR-033, a propriedade `situacao`, a regra "cancelado vence a marca" e a faixa sem cancelado. Do cancelamento, só o mínimo: marcado não remove do Google e não pode ser excluído. | 1 coluna + índice |
| **303b** — dinheiro | FR-013 a FR-021, FR-025 a FR-032, FR-037, e o backend da página de Cancelamentos lendo o resumo (FR-020 e FR-026). | 2 tabelas |
| **303c** — sinalizar | FR-033 (resto), FR-034, FR-035, FR-036, FR-038. | nenhuma |

### Risco de cada opção

- **Tudo junto.** Cerca de quinze superfícies num deploy sem staging; um `git revert` por defeito em comissão desfaz a trava do sync.
- **Corte da Premissa** (sync + dinheiro; depois sinalizar). A trava espera a metade maior e mais arriscada: reconciliação de comissão, arnês main × branch da DRE, travas de Gastos Extras. Enquanto isso, 56 eventos com R$ 172 mil em comprovantes seguem expostos.
- **Três entregas.** A trava entra dias antes, com uma coluna e sem tocar dinheiro; cada deploy reverte sozinho. Custos:
  - três esteiras e três noites de deploy;
  - entre a 303 e a 303b o "Cancelar" segue na regra da 224 (estorno cheio, −600 na DRE), e um evento cancelado nesse intervalo vira `legado` (comissão 0) para sempre.
  - Mitigação: na 303 a faixa do evento marcado oferece só "Devolver ao Google Agenda" e diz que o cancelamento com devolução chega na entrega seguinte; contar `cancelled_at IS NOT NULL` antes do deploy da 303b.

### Inseparáveis

- FR-027 com FR-028.
- FR-001/004 com FR-002/003 e FR-008.
- A marca com faixa, sino e desmarcar.
- FR-016/017/018 com a guarda em `_sync_commission_payment`.
- FR-013 com FR-015a e FR-015b.
- FR-014 com FR-037.

### Fases da 303 (sync)

0. **Pré-requisitos**: edições da spec (seção 6) e contagem pré-deploy com sonda.
1. **Setup**: constantes `SITUACAO_*` e kind; trava em `app/config.py`.
2. **Foundational**:
   - migration e modelo;
   - `consultar_evento`;
   - `verify_303.py` com `GoogleFalso`, rodado vermelho, saída em `verify_303_primeira_falha.txt`;
   - ajuste do verify_205.
3. **H1**: `sumico_ops` (marcar, limpar), delegação, FR-008, sino na transação da marca, `situacao` no resumo e no detalhe, selo.
4. **H5**: aplicar data nova, `reconferir_marcados`, desmarcar.
5. **H2**: endpoint da faixa, componente e hooks, offsets.
6. **H3a**: devolver ao Google, banner com o que está em jogo, os dois toques no cancelar e no `DELETE`.
7. **H6**: portal (`em_confirmacao`) e avaliação.
8. **Polimento**: docs, typecheck, ruff, telas, contagem do dia do deploy, e teste pós-deploy do devolver com evento descartável.

Os blocos do verify seguem essa ordem, com o cenário 2 no bloco de H1, para `--ate` ser linear.

### Fases da 303b (dinheiro)

1. **Foundational**:
   - migration e modelos;
   - constantes;
   - `verify_303b.py` e `dre_dump.py`, vermelhos;
   - extração de `_beneficiario_comissionado`, com regressão main × branch das comissões;
   - resumo do cancelado (leitura).
2. **H4**: reconciliação, repasse aberto, guarda do resync, payloads de Comissões e Planilha.
3. **H3b**: cancelar novo, alterar devolução, prévia, Gastos Extras, diálogo, bloco `cancelamento`, FR-037.
4. **H7**: DRE nas duas telas e FR-032.
5. **Polimento**.

---

## 6. Constitution Check

| Princípio | Como o desenho cumpre, ou o que justificar |
|---|---|
| **I** Reutilizar | Reusa `emitir`, `marcar_lidas_por_entidade`, `total_recebido`, `sync_events`, `_push_cabecalho_ao_google`, `ConfirmDialog`, `Badge`, `format_brl`, `_role_flags`. Uma fonte para comissão cheia, resumo, cancelados do período, predicado da devolução e predicado de marcados. **Registrar**: `sumico_ops` substitui a fatia "cleanup" de `docs/PLANO_EXTRACAO_CALENDAR.md:27,57`. |
| **II** Código | **Atenção**: as propostas descrevem blocos de 120+ linhas. O plano fixa a fatiagem da seção 3 e as constantes. `_compute_drg` cresce ~8 linhas em legado, o que é aceito. |
| **III** Camadas | Núcleo novo em `*_ops`; views só com gate e serialização. `routes.py` de calendar e financeiro recebem os toques listados na seção 3. Nenhum módulo novo em `app/api/`. |
| **IV** Não quebrar | Campos opcionais; backend sobe antes; trava de capacidade no diálogo. Regressão main × branch para DRE e comissões. Verifies de outras features a rodar de novo: 205 (pipeline e cleanup). |
| **V** UI | **Exceção a justificar**: a faixa não mostra skeleton nem erro no primeiro GET, porque o front ainda não sabe se o papel vê a faixa. O devolver usa `ConfirmDialog` com `pending` e erro dentro do diálogo. |
| **VI** Dois níveis | **Decidir**: a 303b e a 303c são Nível 1. A Regra Zero reserva sufixo para hotfix; ou nascem do `/speckit-specify` com número novo, ou a pasta com sufixo entra como exceção registrada. |
| **VII** Living Spec | **Editar a spec antes do `plan.md`**: (1) Premissa "Tamanho" e o que sai para 303b e 303c; (2) FR-032 sem "Performance da Home" e sem "meta do Dashboard Comercial"; (3) cenário 40 e sub-cenários novos (1b, 7b, 10b, 13 em variantes, 24b, 27b); (4) evento marcado não se exclui; (5) devolver com evento editado enquanto marcado; (6) o que é o "verify cruzado" (cenários 23 e 35). |
| **VIII** Verify | Escrito antes do núcleo, por SQL cru nas colunas novas, três estados, controle positivo em todo "deve falhar". Lista fechada do que pode estar verde antes: 7, 15, a metade "Comercial não cancela" do 11, e o sub-cenário "lista inteira falha" do 13. |
| **IX** Dinheiro | Decimal com `ROUND_HALF_UP`; float só na fronteira do JSON; texto do sino por `format_brl`. |
| **X** Mobile | Aviso do portal sem truncar, conferido em 320 e 375 px. |
| **XI** Movimento | Faixa e painel com Framer Motion e `useReducedMotion`. O texto "recriado à mão" usa `AccordionRow`. |
| **XII** Combobox | Sem seleção nova acima de 10 itens na 303. |
| **XIII** RBAC | Três endpoints novos com gate no início da view e linha em `docs/01` §4.3. `/sync` segue sem gate de papel e passa a poder retirar a marca quando o Google confirma presença; declarar. |
| **XIV** Efeito externo | Trava nova derivada do host, com escape `CALENDAR_ALLOW_LOCAL_EVENT_WRITES`, no mesmo commit. Nenhuma variável nova na produção. As escritas antigas sem trava viram dívida. |
| **Stack** | Migration à mão, aditiva, encadeada. Jinja: só os toques da seção 3 e uma linha de template. |
| **Operação** | Deploy à noite, backend primeiro. `startCommand` intocado. Ensaio `flask db upgrade && python seed.py` no espelho. |

---

## 7. Perguntas que só o dono responde

1. **Publicar a metade do sync sozinha, antes do dinheiro?** Recomendo sim. Para de perder evento dias antes e não toca dinheiro. O custo é o "Cancelar" seguir na regra da 224 até a entrega seguinte. Se o dono preferir esperar, sobe sync e dinheiro juntos; a construção não muda.
2. **Depois de cancelado, dá para corrigir comprovante esquecido ou BV negociado digitado errado?** Cancelar não tem volta. Recomendo não: os dois ficam travados, porque o diálogo mostra o total pago e pede o BV antes de confirmar. Se o dono quiser a correção, ela é só do Superadmin e recalcula retido e comissão pelo mesmo caminho da alteração de devolução.
3. **Primeira rodada do "Limpar eventos fantasma"**, depois da contagem. Com a lista na mão, o dono decide se a primeira rodada marca sem sino e sem e-mail de mudança de data a artista. Recomendo decidir pelo número, sem corte fixo. A contagem é pré-requisito do `/speckit-tasks`.

Comunicar, sem reabrir:
- A comissão EducaManto a pagar de evento cancelado fica no ciclo em que estava.
- A tela de Comissões passa a mostrar "No banco".
- Os estornos órfãos já pendentes (o do 1244) não são tocados pela 303.

---

## 8. Riscos do plano e o que vai para `docs/05`

### Riscos a carregar

- **Devolver em produção nunca foi exercitado contra o Google real**; a trava impede localmente. O quickstart prevê o teste pós-deploy com evento descartável.
- **Timeout ambíguo no insert.** O Google pode criar e a resposta se perder. A mensagem manda conferir a Agenda antes de tentar de novo.
- **Evento movido de calendário** responde como ausente. A tela diz "não está mais na agenda", não "foi apagado".
- **Eventos cancelados entre a 303 e a 303b** viram `legado`.
- **Janela de deploy**: bundle velho com backend novo e o inverso.
- **Dias 1 a 5 do mês**: o desconto pode abater de repasse já pago e não marcado. Só tem prova na matriz com `hoje` injetado.
- **Mudança de comportamento em dia de erro**: o `rollback` no `except` do mês descarta trabalho parcial que hoje é comitado de carona.
- **`formatDate` em `ComissoesPage.tsx:40-43`** lê data sem hora como UTC e mostra um dia antes. Aparece nas datas de borda do ciclo. Corrigir na 303b (uma função) ou registrar.
- **O verify escreve no espelho** salários e recorrentes de M−1 a M+2. O cenário de limpeza declara a exceção.

### Para `docs/05`

- Riscar a dívida 49 (`docs/05_DIVIDA_TECNICA.md:471`).
- Registrar, do sync e do Google:
  - escritas antigas no Google sem trava (criar, editar, excluir, cancelar, ensaio, venda virtual);
  - lista do mês sem paginação;
  - série recorrente;
  - id velho restaurado da lixeira depois da devolução;
  - `update_ensaio` e `edit_ensaio` só capturam `RuntimeError`;
  - agendar ensaio e presente 3D em evento cancelado;
  - Fila de Impressão 3D sem filtro de cancelado;
  - lembrete diário de convite para evento marcado;
  - `EventLog` de solicitar e recusar exclusão 3 h adiantado.
- Registrar, do dinheiro:
  - D20 (gasto "Pago" sem prova);
  - painel Jinja de estornos e `set_commission_status`;
  - estorno de exclusão no ciclo da venda e sem ramo `no_banco`;
  - handlers Jinja de comprovante sem guarda de cancelado;
  - cachê de satélite cancelado em `_group_cost`;
  - `event_type` nulo fora da DRE (dívida 47);
  - parcelas nunca marcadas como recebidas;
  - réguas de `/admin/desempenho`;
  - rótulo de impostos da DRE antiga;
  - desconto sem repasse futuro.
- Registrar, de ferramental:
  - verifies não versionados que envelhecem (`verify_cancelamento_evento.py`, `verify_151_excluir_sync.py`, `verify_168_admin_config_react.py`);
  - o efeito antigo do verify_205 no espelho;
  - a skill `financeiro` sem a regra do retido;
  - a sexta cópia do fechar-em-Esc-e-clique-fora.

### Contagens antes de cada deploy (só leitura)

- **303**: eventos passados com dinheiro ausentes do Google; "mudou de data" com convite aceito; pais vazios com ensaio-filho; SHOW sem venda com cachê na vaga automática.
- **303b**: `cancelled_at IS NOT NULL`; linhas a pagar negativas com `event_id`; linhas `no_banco` por mês; devolução com `disbursement_type` nulo; devolução pendente ligada a evento; ciclos de soma zero com linha de valor.