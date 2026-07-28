# 03 — Histórico de Mutações

> **Documento vivo — APPEND ONLY.** Cada feature concluída adiciona uma entrada **no topo** da
> seção "Registro". Nunca reescrever entradas antigas (elas são o histórico); correções entram
> como nova entrada referenciando a anterior.
>
> Última atualização: **2026-07-27** · Estado do repositório: pós-feature **192**

Formato de cada entrada:

```
## <NNN> — <título>            (branch · data do merge · migration)
Motivação · O que mudou (Backend / Banco / Frontend) · Impacto em RBAC e regras de negócio ·
Rotas e endpoints novos/alterados · Riscos e pegadinhas
```

---

## Registro

### 192 — Detalhe do Evento: layout de duas colunas com paridade total da tela clássica
`main` (ajuste direto, sem branch de feature dedicada) · **2026-07-27** · **sem migration**

**Motivação.** A `/events/:id` em React era uma coluna única de ~1370 linhas num arquivo só,
com uma fração do que a tela clássica Jinja (`app/templates/event_detail.html`, 3.201 linhas,
ainda em produção em paralelo) entrega. Faltavam na versão React: menu "⋯ Ferramentas", bloco de
cópia rápida para WhatsApp, indicador de conflito de agenda do talento, medidas de figurino,
vínculo de ficha de figurino ao personagem, status de pagamento do cachê, equipe de apoio
separada dos personagens, materiais de ensaio, gastos extras vinculados, acréscimos/BV,
avaliações dos artistas, feedback da cliente e o log de atividades. Boa parte disso já existia
como cálculo inline na view Jinja — nunca tinha sido exposta pela API.

**Backend.** Nenhum endpoint antigo mudou de contrato; o JSON de leitura **ganhou campos**.
- `app/calendar/event_ops.py` (+~290 linhas): núcleo novo — `talent_availability` (extraído do
  loop inline de `event_detail`), `set_payment_status`, `link_figurino_sheet`,
  `clear_figurino_done`, `ensure_feedback_token`, `suggested_departure_time`,
  `add_ensaio_file`/`add_ensaio_link`/`delete_ensaio_material`.
- `app/api/agenda_read.py`: `serialize_event_detail` passou a incluir `event.description`,
  `event.google_html_link`, `event.travel` (cache do Maps + saída sugerida + `maps_url`),
  `materiais`, `ratings`, `client_feedbacks`; e, sob os gates já existentes, `acrescimos`,
  `gastos`, `mensagens`, `reembolsos_pendentes_total`, `feedback_link_pendente`. Cada cargo
  do `elenco` ganhou `talent` completo (medidas, WhatsApp com DDI, primeiro nome), `role_type`,
  `assigned_at`, `payment_status`, `availability`, `figurino_sheet_name`, `figurino_done_at`,
  `travel_cache` e `cache_cap`.
- `app/api/agenda_write.py`: 7 endpoints novos — `POST /api/roles/<id>/payment-status`,
  `POST /api/roles/<id>/figurino-sheet`, `DELETE /api/roles/<id>/figurino-done`,
  `POST /api/events/<id>/travel-estimate`, `POST /api/events/<id>/materials`,
  `DELETE /api/materials/<id>`, `POST /api/events/<id>/feedback-link`.

**Banco.** Sem migration — nenhuma coluna nova. Tudo já existia em `EventRole`
(`payment_status`, `figurino_sheet_id`, `assigned_at`), `CalendarEvent` (`description`,
`google_html_link`, `travel_*`, `feedback_token`), `EnsaioMaterial`, `EventRating`,
`ClientFeedback`, `SpecialExpense` e `EventAcrescimo`.

**Frontend.** `EventDetailPage.tsx` reescrita (1.367 → ~120 linhas) como composição de
`components/EventDetail/`: `parts.tsx` (Panel/DataRow/Stars/formatadores), `EventHeader.tsx`
(cabeçalho + menu Ferramentas + modal de exportar elenco + diálogo de exclusão),
`CastingSection.tsx`, `FigurinoSection.tsx`, `LogisticaSection.tsx`, `ComercialSection.tsx`,
`FinanceiroSection.tsx`, `FeedbackSection.tsx`, `ObservacoesSection.tsx` (+ `WhatsAppSummary` e
`LogsSection`). Hooks novos em `lib/eventDetail.ts` (todos gravam o evento devolvido no cache do
TanStack Query, como `casting.ts`) e os construtores das mensagens de WhatsApp. `KebabMenu`
ganhou `triggerLabel` e itens `disabled`/`title` em vez de um segundo componente de dropdown.
A busca de fichas de figurino reusa `useFigurinoSheets()` (`GET /api/figurino`), sem endpoint
novo.

**RBAC e regras de negócio.** Sem mudança de política — os gates novos reusam os existentes:
`_CAN_EDIT_EVENT` (status de pagamento, ficha de figurino, desmarcar figurino, estimar trajeto),
`_CAN_ENSAIO_MATERIAL` (materiais de ensaio) e Comercial/Superadmin (link de feedback, mesmo
gate de `feedback.gerar_link`). **Novo requisito de segurança**: a seção "Log de atividades" só
é renderizada para `SUPERADMIN` — para os demais papéis ela **não existe no DOM**, não é
escondida por CSS.

**Riscos e pegadinhas descobertas.**
1. `CalendarEvent.roles` **não tem `order_by`** — o Postgres devolvia os cargos em ordem
   arbitrária, e a ordem *mudava depois de um UPDATE*. Com os cards densos isso fazia a lista
   inteira pular de posição a cada mutação. `serialize_event_detail` agora ordena por `id`.
2. `api_set_payment_status` colidiu com o endpoint de mesmo nome em `financeiro_write.py`
   (Flask recusa o registro do blueprint com `AssertionError`) — renomeado para
   `api_set_role_payment_status`.
3. A descrição do evento vem do Google/Kommo **em HTML** (`<br>`, âncoras de e-mail). Colada
   crua no WhatsApp vira um paragrafão com tags à mostra; `descriptionToText()` converte para
   texto puro por regex (sem `innerHTML`/`querySelector`, proibidos pela constituição).
4. `/api/events/<id>` não é alcançável por `REVENDEDOR_EDUCAMANTO` puro — o guard global de
   `app/__init__.py` só libera o prefixo `/events/`, não `/api/...`. Comportamento pré-existente,
   descoberto ao escolher papéis para o script de verificação.
5. Materiais de ensaio novos vão por `app.storage.save_file` (local/S3) em vez do `file.save()`
   direto do fluxo Jinja; o serializador normaliza os dois formatos de `file_path`.

**Verificação.** `scripts/db/verify_190_event_detail.py` — 53/53 contra `manto_local`
(serialização dos blocos novos, RBAC de leitura por papel, e 200/400/403/404/401 dos 7
endpoints). Frontend: `npm run build` limpo e conferência no app real (evento 286): 16 seções,
duas colunas em 1280px, sem rolagem horizontal, log ausente do DOM ao impersonar `CASTING`,
mutações de figurino/pagamento/materiais devolvendo 200 com a lista estável.

---

### 191 — Calculadora de Orçamento: paridade de layout clássico + cálculo reativo
`main` (ajuste direto, sem branch de feature dedicada) · **2026-07-27** · **sem migration**

**Motivação.** A versão React de `/orcamento` (feature 190) portou a calculadora para duas
colunas de largura igual com um botão manual "Calcular orçamento" — isso dispersou os campos em
relação à tela clássica Jinja (`app/templates/orcamento/index.html`, ainda em produção em
paralelo) e tornou o fluxo do comercial mais lento (clicar em "Calcular" a cada ajuste). Dois
recursos da tela clássica nunca foram portados: o alerta de segurança "já agendado neste dia"
(evita vender o mesmo personagem duas vezes no mesmo dia) e o painel "Personalizar valores"
(definir o total final manualmente, por valor ou por multiplicador) — a infraestrutura de API
para ambos já existia (`usePersonagensNoDia`, campos `personalizado*` em
`CalcularOrcamentoInput`), só nunca tinha sido usada na tela.

**Backend.** Nenhuma mudança — nenhum endpoint, RBAC ou model tocado. Todo o trabalho reusou
`GET /api/orcamento/personagens-no-dia`, `GET /api/orcamento/historico` e
`POST /api/orcamento/calcular`, já existentes desde a feature 177/190.

**Banco.** Sem migration.

**Frontend.** Reescrita completa de `OrcamentoCalculadoraPage.tsx` (mesmo arquivo,
`PerformerTableRow` reaproveitado sem mudanças):
- Layout `lg:grid-cols-3`: coluna esquerda (1/3) = Dados do Evento + transporte condicional
  (Fora de SP) + alerta de agenda + link "Histórico de Orçamentos" com contador dinâmico
  (`useOrcamentoHistorico({}).data.entries.length`); coluna direita (2/3) = Equipe, Acréscimos,
  card "Ajustes Finos" (Nota Fiscal, duração extra, formato do orçamento, durações incluídas,
  "Personalizar valores") e o card de Resultado.
- **Cálculo reativo**: removido o botão "Calcular orçamento"; um `useEffect` observa um
  `payload` memoizado com todo o estado do formulário e dispara `calcular.mutate` com debounce
  de ~400ms a cada alteração — sem exigir clique. Os cards de resultado ficam com opacidade
  reduzida (`opacity-50`) enquanto uma requisição está em voo, em vez de somem, preservando o
  último valor visível (Princípio V — feedback visual obrigatório).
- **Alerta "Já na agenda neste dia"**: novo componente `AgendaNoDiaAlert`, usa
  `usePersonagensNoDia(eventDate)` (existia no hook, nunca usado em nenhuma página); valida a
  data com regex antes de habilitar a query, para não disparar a API com data parcial/inválida;
  renderiza abaixo do campo Data.
- **Painel "Personalizar valores"** (novo na UI — só o tipo já existia): checkbox que abre um
  toggle "Definir valor final" / "Mudar multiplicador" e 4 campos (1h–4h), `MoneyInput` no modo
  valor final, `Input` numérico no modo multiplicador.
- Substituído o `<select>` de "Formato do orçamento" por um toggle de dois `Button`
  (`variant="default"`/`"outline"` conforme seleção), mesmo padrão visual dos botões +/- do
  Coordenador — sem componente novo no design system.

**Impacto em RBAC e regras de negócio.** Nenhum — mesma tela, mesmo RBAC (`COMERCIAL`,
`SUPERADMIN`), nenhuma regra de cálculo mudou no backend.

**Riscos e pegadinhas.**
- O alerta de agenda e o contador do histórico dependem de dados existentes em `manto_local` —
  verificado manualmente logado como SUPERADMIN contra um evento real do dia (BLUEY + BINGO,
  27/07/2026): o alerta apareceu corretamente com os dois personagens.
- O modo "Personalizar valores" retorna erro de campo do backend quando os 4 valores ficam em
  zero ("Informe valores válidos para o orçamento personalizado.") — comportamento esperado do
  endpoint, não um bug novo; confirmado que o erro aparece e some corretamente ao preencher um
  valor.
- Sem verificação funcional automatizada de backend nesta entrada (nenhum endpoint mudou) — só
  `npx tsc --noEmit` (limpo) e verificação manual na UI real via preview.

---

### 190 — Paridade e Unificação do Módulo de Orçamentos e EducaManto (React)
`190-paridade-orcamento-educamanto` · **2026-07-27** · **sem migration**

**Motivação.** As 6 telas do módulo de Ferramentas (Calculadora de Orçamento, Config. de Preços,
Histórico de Orçamentos, Calculadora EducaManto, Pacotes EducaManto, Histórico EducaManto) já
existiam e funcionavam, mas haviam perdido densidade visual e paridade de recursos frente à
extinta versão Jinja: listas de `Card` soltos em vez de tabelas gerenciais, filtros avançados já
suportados pelo backend mas nunca expostos na UI (`date_from`/`date_to`/`min_val`/`max_val`/
`user_id`/`has_show` no histórico de Orçamento), e — a lacuna mais importante — **nenhum dos dois
históricos tinha ação "Recalcular"**, apesar do backend já guardar o estado bruto necessário
(`OrcamentoHistory.form_snapshot`, `EducaMantoQuote.snapshot`) sem nunca expô-lo em JSON. A meta
de negócio é unificar a experiência do EducaManto com a Calculadora de Orçamento normal como
ferramentas irmãs do mesmo ecossistema, incluindo paridade de "reabrir, editar e recalcular".

**Backend.** Dois endpoints de leitura, ambos aditivos/retrocompatíveis — nenhum endpoint
existente mudou de contrato, nenhuma lógica de negócio nova (reuso de `quote_ops` já existente).
- `app/api/orcamento_read.py`: `GET /orcamento/historico/<id>` passou a incluir também
  `form_snapshot` (estado bruto de entrada, já persistido, nunca antes exposto) ao lado do
  `quote` congelado que já existia.
- `app/api/educamanto_read.py`: **novo** `GET /educamanto/historico/<id>` — retorna
  `quote_ops.load_quote_snapshot(quote)` em JSON (mesmo dado já usado internamente para regerar o
  PDF), mesmo RBAC (`_require_use`) da listagem, sem restrição por dono (paridade com o endpoint
  de PDF por id, que também não restringe por dono).

**Banco.** Sem migration — nenhuma coluna nova, nenhum model alterado.

**Frontend.**
- Fundação em `@manto/ui`: `Table`/`TableRow`/`TableCell` (convenção densa extraída de
  `PagamentosPage`/`GastosRecorrentesPage`, feature 189), `Badge` (rótulo de tom único,
  complementar ao `MetricBadge` existente) e `CopyButton` (promovido de local em
  `PagamentosPage.tsx` para fonte única).
- `OrcamentoCalculadoraPage.tsx`: layout em duas colunas, "Limpar tudo", equipe em tabela
  (Coordenador com contador +/-, "+ Ator/Cantor"/"+ Especial"), nota informativa de BV, campo de
  duração extra (`duracao_custom`, já existia no tipo mas não estava exposto na UI), painel de
  resultados em cards 1h–4h, `Dialog` "Ver memória de cálculo"; lê `?recalcular_id=` e repopula
  todos os campos a partir de `form_snapshot` (mesmo padrão de pré-fill via query param de
  `EventCreatePage.tsx`).
- `OrcamentoConfigPrecosPage.tsx`: os 8 blocos de preço viraram tabelas (`PriceTable`) — Markup,
  Cachê Atores, Cachê Cantores, Técnico/Coordenador, Especiais (uma linha por variante); "Voltar
  à calculadora" no `PageHeader`.
- `OrcamentoHistoricoPage.tsx`: tabela gerencial com todos os filtros que o hook já suportava
  (texto, data, faixa de valor, vendedor, tipo com/sem show), badge de tipo, `Dialog` "Ver"
  (substitui a expansão inline anterior), **"Criar evento"** (`/events/new?orcamento_id=` — o
  pré-fill do lado do `EventCreatePage` já existia, só faltava o link) e **"Recalcular"**
  (`/orcamento?recalcular_id=`).
- `EducaMantoCalculadoraPage.tsx`: seletor de pacote virou dropdown (era pills), layout em duas
  colunas, cards "Sem Nota Fiscal"/"Com Nota Fiscal" recoloridos (verde/azul) com Custo Base e
  Comissão do Vendedor explícitos, detalhamento de custos dentro de um `AccordionRow`
  colapsável, atalhos no cabeçalho ("Editar pacote", "+ Novo pacote"); lê `?package_id=` (vindo
  de "Usar" na tela de Pacotes) e `?recalcular_id=` (repopula a partir do novo endpoint de
  detalhe — note que o texto do endereço não é persistido no snapshot, só o km calculado, então
  o campo de endereço fica vazio no recálculo mas o km/transporte já vêm preenchidos).
- `EducaMantoPackagesPage.tsx`: lista vertical virou grade de 2–3 colunas; cada card ganhou
  margens (1S/2S/1S-dias/2S-dias), desconto formatado ("5% após N dias") e uma mini matriz de
  custos; botão novo "Usar" (`/educamanto?package_id=`, disponível a todos que veem pacotes, não
  só a quem gerencia); "Duplicar" ganhou o rótulo "Criar cópia" pedido (mesma mutation).
- `EducaMantoHistoricoPage.tsx`: lista virou tabela; "Reabrir PDF" renomeado para "Baixar PDF";
  **"Ver"** novo (`Dialog` consumindo o endpoint de detalhe novo) e **"Recalcular"** novo
  (`/educamanto?recalcular_id=`).

**Rotas e endpoints.**
- **Novo:** `GET /api/educamanto/historico/<id>`.
- **Alterado (aditivo):** `GET /api/orcamento/historico/<id>` (campo `form_snapshot` a mais).
- Rotas de página inalteradas.

**RBAC e regras de negócio.** Sem mudança de permissões. "Recalcular" sempre roda o cálculo com
as configurações de preço **atuais** (não os valores congelados no histórico) — é a mesma
calculadora reaberta com os campos preenchidos, não uma reconstrução do valor histórico exato;
para ver o valor exatamente como foi cotado, a ação é "Ver" (mostra o snapshot congelado), não
"Recalcular".

**Riscos e pegadinhas.**
- O processo do backend local (`manto-backend-local`) não recarregou a nova rota
  `/api/educamanto/historico/<id>` automaticamente apesar do reloader do Werkzeug reportar
  "Restarting with stat" — só passou a responder (401 em vez de 404) após um restart manual do
  processo. Se uma rota nova parecer "não existir" mesmo com o código correto no disco
  (confirmado lendo `app.url_map` num processo novo), suspeite do processo de dev desatualizado
  antes de suspeitar do código.
- `EducaMantoQuote.snapshot` guarda `transporte.kmT`/`label`/`pessoas`/`total`, mas **não** o
  texto do endereço digitado — "Recalcular" no EducaManto restaura o km calculado, não o campo
  de endereço em si.
- `@manto/ui` não tem um componente `Table`/`Badge` genérico antes desta feature — telas com
  tabela usavam `<table>` nativo caso a caso; os novos `Table`/`TableRow`/`TableCell`/`Badge`
  ficam disponíveis para qualquer tela futura que precise de listagem densa.
- Verificação: `npx tsc --noEmit` limpo em `frontend/apps/internal`; `ruff check` limpo nos dois
  arquivos Python tocados; fluxo completo Calculadora → Salvar → Histórico → Recalcular → Criar
  evento exercitado no navegador contra `manto_local` para os dois módulos (Orçamento e
  EducaManto), incluindo o `Dialog` "Ver" em ambos os históricos.

### 189 — Módulo Financeiro de Alta Fidelidade e Consistência (React)
`189-financeiro-alta-fidelidade` · **2026-07-27** · **sem migration**

**Motivação.** As três telas financeiras em React (`/financeiro`, `/financeiro/pagamentos`,
`/gastos/recorrentes`) haviam perdido densidade de informação e fluxos operacionais frente à
versão Jinja congelada. Especificamente: o painel financeiro virou uma pilha vertical de cards
(sem grid 2/3 + 1/3, sem termômetro de break-even, sem barra do Fator R, com a DRE achatada e
sem hierarquia); a planilha de pagamentos perdeu a **cópia rápida de PIX/valor/descrição**, a
ordem de colunas clássica e — bug operacional principal — **não tinha ação em lote para "No
banco"**, embora o backend sempre tenha suportado; e `/gastos/recorrentes` era uma lista de
cards indiferenciados, sem as três seções por tipo, sem a coluna de status do mês de referência
e sem o botão `[Preencher]` proeminente que gera o `RecurringExpenseEntry`.

**Backend.** Nenhum endpoint novo de escrita; só enriquecimento de leitura (aditivo,
retrocompatível) e uma extração para não duplicar regra de negócio.
- `app/gastos/gastos_ops.py`: **duas funções novas** — `estimate_monthly_cost(conta)` (custo
  mensal estimado, normalizando frequência: semanal ×4, quinzenal ×2, anual ÷12; variável usa o
  teto da faixa) e `recurring_summary(contas)` (`somas` por tipo + `programado_pendente_total`).
  Ambas foram **extraídas de dentro da view Jinja** `app/gastos/routes.py::recorrentes` (onde
  viviam como `_estimate`/somas inline) — a view passou a chamá-las, fonte única com a API
  (Princípio I).
- `app/api/gastos_read.py`: `_recurring_dict` ganhou parâmetros opcionais `ref_year`/`ref_month`
  e passou a serializar os rótulos derivados do model (`expected_label`, `dia_label`,
  `vigencia_label`, `parcelas_summary`), além de `estimated_monthly`, `has_entries`,
  `occurrences` (0 = "fora do ciclo") e `entries` (só para `programado`). O payload da listagem
  ganhou `ref_year`, `ref_month`, `weekday_labels`, `somas` e `programado_pendente_total`.
- `app/api/financeiro_read.py`: `kpis` ganhou `margem_bruta`, `margem_ebitda`, `tax_rate`
  (alíquota do `SiteSetting`, para o rótulo "Impostos Provisionados (16% · eventos com nota)")
  e as faixas do Fator R (`fator_r_rate_low`/`fator_r_rate_high`); cada linha de `eventos[]`
  ganhou `receita` e `event_type` (a tabela React não tinha como exibir a coluna Receita).

**Banco.** Sem migration — nenhuma coluna nova. `RecurringExpense`/`RecurringExpenseEntry` e
`SpecialExpense` seguem inalterados; toda a informação nova é derivada.

**Frontend.**
- `FinanceiroDashboardPage.tsx` **reconstruída** no layout clássico em grid: coluna principal
  (2/3) com 4 KPIs (Ticket Médio, Custo Talento/Receita, Margem Bruta, EBITDA), **termômetro de
  break-even** e **alerta fiscal do Fator R** — ambos com barra de progresso Tailwind
  (`role="progressbar"` + `aria-valuenow`) e badge de proteção tributária —, a **DRE Gerencial
  com identação hierárquica** (linhas `(–)` recuadas, subtotais `=` em faixa destacada, EBITDA e
  Resultado Líquido com régua superior) e os 3 cards de A Receber/A Pagar/Pago. Coluna analítica
  (1/3) com Receita por Tipo (barras horizontais), Top Vendedores ranqueados, Auditoria de Input,
  Notas a Emitir, Tendência de 6 meses e Recebimentos Previstos. Tabela de Eventos no Período em
  largura total, agora com Receita e Tipo.
- `PagamentosPage.tsx`: ordem de colunas do Jinja restaurada (checkbox · vencimento · descrição
  detalhada com badge de tipo · favorecido em **bold** · valor · chave PIX com tipo · situação);
  **botão compacto de cópia** ao lado da descrição, do valor (formato cru `1234,56`) e da chave
  PIX, com feedback "✓" temporário e `aria-live`; **checkbox "selecionar tudo"**; ação em lote
  **"Marcar como no banco"** (o backend já aceitava `no_banco` em `bulk-action`); seletor de
  situação colorido por estado, com as opções que cada tipo realmente suporta.
- `GastosRecorrentesPage.tsx` **refeita** em três seções tabulares (Contas Variáveis, Débito
  Automático, Assinaturas/Cartão) + Pagamentos Programados, com resumo mensal no topo, seletor
  de mês de referência e formulário de criação completo (tipo, frequência, dia/dia-da-semana,
  vigência, faixa **ou** valor exato, cartão, PIX padrão, observações). Cada linha traz
  `[Preencher]` (Dialog de `@manto/ui` com `MoneyInput`), `[Pular mês]`, `[Pagar]`/`[Reabrir]`,
  `[Histórico]` (Dialog consumindo o endpoint novo), `[Editar]` (Dialog) e
  `[Desativar]`/`[Excluir]` com confirmação em Dialog.
- `lib/financeiro.ts` e `lib/gastos.ts`: tipos estendidos (zero `any`) + hook novo
  `useRecorrenteHistorico`.

**Rotas e endpoints.**
- **Novo:** `GET /api/gastos/recorrentes/<conta_id>/historico` — todos os lançamentos da conta,
  do mais recente para o mais antigo (equivale ao painel `?conta=<id>` da tela Jinja).
- **Alterados (aditivos):** `GET /api/financeiro/dashboard` e `GET /api/gastos/recorrentes`.
- Rotas de página inalteradas.

**RBAC e regras de negócio.** Sem mudança. O endpoint novo usa o mesmo gate
`gastos_ops.is_financeiro` (FINANCEIRO/SUPERADMIN) dos demais de recorrentes; a página Jinja
legada segue funcionando (`/gastos/recorrentes` e `/financeiro/` verificados em 200 após a
extração para `gastos_ops`).

**Riscos e pegadinhas.**
- **Os status de pagamento do backend são exatamente três**: `nao_pago` ("Não pago"), `pago` e
  `no_banco` (`_VALID_PAYMENT_STATUS` em `app/api/financeiro_write.py` e `_STATUS_LABELS` em
  `app/financeiro/routes.py`). Não existem `pendente` nem `agendado` — "pendente" é o rótulo de
  UI de `nao_pago`. `commission` e `recurring` **não têm** `no_banco`: em lote o backend
  devolve o item em `skipped`, e a UI já nem oferece a opção.
- **`text-amber`/`bg-amber-soft` não existem** no preset do design system
  (`@manto/ui/tailwind-preset` tem `green`, `red`, `blue`, `gold`, `accent` — não `amber`). A
  versão anterior de `GastosRecorrentesPage` usava essas classes no alerta do topo e elas nunca
  renderizaram cor nenhuma. Estados de atenção agora usam `gold`.
- `occurrences === 0` significa **"fora do ciclo"** (fora da vigência ou da frequência no mês),
  não "sem lançamento" — sem esse campo no payload a UI teria que reimplementar
  `RecurringExpense.occurrences_in_month`, que é regra de negócio real.
- O botão `[Excluir]` da conta só aparece com `has_entries === false`; com histórico o caminho é
  desativar (`delete_recurring` levanta `GastoStateError` → 409).
- Verificação funcional: `scripts/db/verify_189_financeiro_alta_fidelidade.py` (**51/51** contra
  `manto_local`) — novos campos do dashboard, `no_banco` individual **e** em lote com persistência
  conferida no banco, resumo/rótulos/`occurrences` das recorrentes, `preencher` gerando o
  `RecurringExpenseEntry` que aparece na planilha de pagamentos, e o histórico (200/404/403).
  Fluxo completo também exercitado no navegador contra `manto_local` (criar conta → `[Preencher]`
  com máscara BRL → linha vira "a pagar R$ 512,30" → item aparece na planilha de pagamentos).

### 188 — Refatoração e Paridade do Módulo de Formulários
`188-formularios-paridade-listagem` · **2026-07-27** · **sem migration**

**Motivação.** A migração para React deixou `/formularios` com menos informação que a tela Jinja
antiga: o painel superior com os **links públicos copiáveis** havia sumido, a listagem virou uma
pilha de cards sem **Data do evento**, o "Recebida em" perdeu a **hora**, e a "Situação" caiu para
texto cinza ("Sem cliente • Sem evento") em vez dos **badges coloridos**. Esta entrada restaura a
paridade e moderniza o editor de campos.

**Backend.**
- `app/api/formularios_admin_read.py`: **`client_name` promovido do detalhe para o
  `_response_summary`** — a coluna "Situação" da listagem precisa do nome para o badge
  "Cliente: `<nome>`". `_response_detail` deixa de duplicá-lo (herda do summary).
- `app/formularios/formularios_ops.py`: `list_responses` e `search_responses` passam a fazer
  `joinedload(FormResponse.client)`. Sem isso, ler `r.client.name` em até 200 linhas geraria
  N+1 queries.
- **Correção de bug Postgres-only** em `app/gastos/gastos_ops.py::search_events_by_date`:
  `func.date(CalendarEvent.start_at) == day.isoformat()` comparava um `date` com **string** e
  estourava `psycopg.errors.UndefinedFunction: operador não existe: date = character varying`
  → `GET /api/gastos/eventos?date=...` respondia **500 em produção**. Agora compara com o próprio
  `date`. O SQLite de dev aceitava a comparação (tipagem dinâmica), então o bug nunca aparecia
  localmente. Afetava o seletor "vincular evento" **desta** tela e o da tela de Gastos Extras
  (mesmo hook `useGastosEventos`).
- Nenhum endpoint novo, nenhuma mudança de RBAC.

**Banco.** Nenhuma alteração de schema.

**Frontend.**
- `FormulariosAdminPage.tsx` reescrita: **gerenciador de links públicos** (dois cards com URL
  somente-leitura, "Copiar link" com confirmação "✓ Copiado" + `aria-live`, "Abrir" em nova aba e
  atalho SUPERADMIN para o editor); **tabela densa** com as 6 colunas da tela antiga (Contratante,
  Formulário, Data do evento, Recebida em com `DD/MM/AAAA HH:mm`, Situação, Ver); badges de
  situação via `MetricBadge` (verde resolvido / âmbar pendente); busca + abas de tipo de
  formulário; detalhe e editor em `Dialog` de `@manto/ui` (antes eram painéis inline).
- **Novo** `components/FormFieldEditor.tsx`: editor de `FormFieldDefinition` com formulário real
  (rótulo, seção com `datalist`, tipo, opções, ajuda, placeholder, obrigatório) no lugar dos
  `window.prompt()`/`window.confirm()` anteriores.
- `lib/formulariosAdmin.ts`: `client_name` no `FormResponseSummary`; `FIELD_TYPES` e
  `optionsToText()` (converte o `options` JSON do backend em texto "uma opção por linha");
  `UpdateFieldInput` explícito.
- `EventCreatePage.tsx`: aceita **`?form_response_id=<id>`** e pré-preenche pré-contrato vinculado,
  data do evento e cliente associado — reusando `GET /api/formularios/respostas/<id>` (mesmo RBAC),
  sem endpoint novo.

**Princípio V (nenhum botão morto).** Todo disparador de mutation desta tela dá retorno visual:
`Button loading` em associar/desassociar/vincular/desvincular/salvar/excluir; nas linhas de
resultado da busca de cliente e nas setas ↑/↓ do editor, o estado usa `mutation.variables` para
que **só o item clicado** fique em spinner (e não a lista inteira); o `<select>` de evento — que é
o próprio gatilho da ação — trava e troca o rótulo para "Vinculando…" enquanto o vínculo está em
voo. "Copiar link" não é assíncrono: confirma inline com "✓ Copiado" + `aria-live`.

**RBAC e regras de negócio.** Inalterados. Respostas seguem em `_require_vendas()`
(COMERCIAL/FINANCEIRO/SUPERADMIN) e o editor em `_require_superadmin()`; a UI só espelha o
`can_edit_structure`/`is_superadmin` que o servidor já devolve.

**Rotas e endpoints.** Nenhum novo. `/formularios` mantém a rota; `/events/new` ganha o parâmetro
opcional `form_response_id` (o `orcamento_id` continua funcionando igual).

**Riscos e pegadinhas.**
- **`update_field` substitui, não faz merge**: omitir `help_text`/`placeholder`/`required` no PATCH
  **apaga** esses atributos. A versão anterior da tela mandava só `label` + `required` num
  `window.prompt()` e silenciosamente limpava ajuda/placeholder do campo. O editor novo sempre
  envia o payload completo.
- `field_type` e `section_name` são **imutáveis** após a criação (o backend nunca os altera) — o
  formulário de edição os desabilita e explica o porquê.
- Os links dos cards usam `window.location.origin` + `/catalogo/f/<slug>`, que só resolve no build
  de produção (onde `frontend/server.js` serve `apps/public` sob `/catalogo/*`). No dev server do
  `apps/internal` (:5173) o link abre um 404 da SPA — esperado, não é regressão.
- **`func.date(coluna) == <str>` é bomba-relógio neste repo**: passa no SQLite e explode no
  Postgres. Ao escrever qualquer filtro por dia, compare com o objeto `date` — e verifique contra
  `manto_local`, nunca contra o SQLite de `instance/` (regra do `CLAUDE.md`). Foi assim que o 500
  do `/api/gastos/eventos` apareceu: só ao exercitar o seletor de evento contra o Postgres local.
- Verificação funcional: `scripts/db/verify_formularios_listagem_paridade.py` (20/20 contra
  `manto_local`) — cobre `client_name` em listagem/busca/detalhe, `event_date`/`created_at`
  serializados e o RBAC dos três endpoints. O 500 do `/api/gastos/eventos` foi confirmado
  (e a correção validada) direto contra `manto_local`: 2026-08-22 → 3 eventos, 2026-08-15 → 1.

### 187 — Reestruturação do Módulo de Comissões
`187-comissoes-modulo-completo` · merge **2026-07-24** (`4c20e47`) · **sem migration**

**Motivação.** A tela `/financeiro/comissoes` misturava a visão do vendedor com a do financeiro,
dependia do cliente para restringir escopo e sofria de dessincronização ao marcar comissões como
pagas uma a uma.

**Backend.**
- Novo módulo de núcleo de negócio **`app/financeiro/comissoes_ops.py`** (385 linhas): dataclasses
  `CommissionEntry`, `CommissionKpis`, `CommissionMonthSummaryRow`, `PayoutResult`; funções
  `parse_month_strict`, `resolve_month`, `get_month_entries`, `get_month_summary_by_seller`,
  `get_month_kpis`, `pay_seller_month`. Exceções próprias `InvalidMonthError` e
  `SellerNotFoundError`.
- `GET /api/financeiro/comissoes` reescrito: devolve `month`, `can_manage`, `title`, `kpis`,
  `by_seller`, `entries` e (só para gestor) `sellers`. Continua chamando
  `_resync_pending_commissions()` de `app/financeiro/routes.py` para não duplicar a reconciliação.
- **Novo** `POST /api/financeiro/comissoes/pagar-mes` — liquidação em lote atômica por
  vendedor/mês, com `SELECT ... FOR UPDATE` (`with_for_update()`) sobre os registros elegíveis.
  Duas chamadas concorrentes (duplo clique / duas abas): a segunda espera a primeira commitar,
  relê o estado, encontra 0 elegíveis e reporta `changed_count = 0` — **idempotente, nunca paga
  duas vezes**. Registra `audit("payment", "commission_month", ...)`.
- Decisão explícita: `app/financeiro/routes.py` (Jinja legado) **não** foi tocado e **não**
  importa `comissoes_ops` — mantém sua própria cópia de `_bulk_set_commission_period`.

**Banco.** Nenhuma alteração de schema. `CommissionPayment` já tinha tudo que era necessário
(`status`, `paid_at`, `payable_from`, `original_id`, `amount` assinado).

**Frontend.**
- `ComissoesPage.tsx` reconstruída (~464 linhas alteradas): 3 cards de KPI, seletor de mês,
  **duas abas** (Resumo por Vendedor / Detalhamento de Vendas), accordion por vendedor, modal de
  confirmação com o valor somado no servidor, e **export CSV** do resumo.
- Três componentes novos em `@manto/ui`: **`AccordionRow`**, **`Dialog`** e **`Tabs`**.

**RBAC e regras de negócio.**
- **O servidor decide o escopo**: `seller_filter = requested_seller_id if can_manage else
  current_user.id`. Vendedor comum nunca recebe dados de outro, mesmo forçando `seller_id` na
  querystring.
- `can_manage` = `FINANCEIRO` ou `SUPERADMIN`. Título muda para **"Minhas Comissões"** quando
  falso, e nenhuma ação de pagamento é renderizada.
- O **responsável EducaManto** sem papel Financeiro continua sendo vendedor comum nesta tela.
- `pagar-mes` responde **403** para não-gestor, inclusive para o próprio `seller_id`.
- **Estornos** (`amount < 0`, `status='a_pagar'`) aparecem em **qualquer mês** até serem resolvidos
  (`_pending_reversals_query`, sem filtro de mês, deduplicado por `id`) e só são liquidados junto
  com as demais comissões do vendedor — nunca isoladamente.
- KPIs derivam do **mesmo** resumo que alimenta o botão "Pagar Mês", garantindo que batem centavo
  a centavo com o que pode ser efetivamente liquidado.

**Pegadinhas.** Mês inválido cai silenciosamente no mês corrente em `resolve_month` (leitura), mas
`pay_seller_month` usa `parse_month_strict` e **falha** — a escrita nunca adivinha o mês.

---

### 186 — Gerenciador de Catálogo: UX e fluxo Ficha ↔ Catálogo ↔ Venda
`186-gerenciador-catalogo-ux` · merge **2026-07-24** (`31310d3`) · **sem migration**

**Motivação.** A 185 entregou a estrutura Tema/Personagem funcional, mas "cega": a busca de elenco
mostrava só nome, o vínculo com a Ficha de Figurino só existia por um lado, e não havia forma de
tratar em lote o acervo antigo sem vínculo.

**Backend.**
- `GET /api/catalogo/elenco-busca` passou a servir também o lado da Ficha: gate ampliado para
  `COMERCIAL`, `FIGURINO` e `SUPERADMIN` (antes era só o fluxo comercial), incluindo `photo_url` e
  `figurino_sheet_id` de cada Personagem — dado interno, por isso fora da grade pública.
- **Novo** `POST /api/admin/catalogo/personagens/mover-em-massa` +
  `catalog_character_ops.move_characters(character_ids, target_item)`.
- `admin_catalogo_read` passou a expor o indicador de vínculo pendente por Personagem.

**Banco.** Nenhuma alteração. **Decisão de projeto**: o vínculo bidirecional reusa a coluna
existente **`catalog_characters.figurino_sheet_id`** — não há coluna espelho em `figurino_sheets`;
o "personagem vinculado" de uma ficha é derivado por busca inversa.

**Frontend.**
- **`CharacterAutocomplete`** — busca visual com miniatura, filtrada para **Personagens filhos
  ativos** (Temas pai nunca aparecem); placeholder quando não há foto; ao selecionar preenche nome
  e `figurino_sheet_id` na linha do elenco.
- **`CatalogTreeView`** (árvore hierárquica Tema → Personagens, com guia de recuo),
  **`CatalogCardGrid`**, **`KebabMenu`** e **`CatalogBulkActionBar`** (barra flutuante de ações em
  massa: Mover para… / Inativar / Excluir; "Mover" só existe para Personagens).
- `/admin/catalogo`: alternador **Cards ⇄ Árvore** persistido em `localStorage`
  (`manto_admin_catalogo_view`), seleção múltipla, e associação rápida "+ Vincular Ficha".
- `FigurinoFormPage`: campo **"Vincular a um Personagem do Catálogo"** com Desvincular.
- `FigurinoListPage`: indicador **"⚠ Sem personagem vinculado"** + modal de vínculo em 2 cliques.
- **US6 — deploy**: `frontend/server.js` novo (serve `apps/internal/dist` na raiz e
  `apps/public/dist` sob `/catalogo/*`, cada um com seu fallback de SPA), `base` condicional em
  `apps/public/vite.config.ts`, `basename` condicional em `apps/public/src/App.tsx`,
  `frontend/nixpacks.toml` passando a compilar os **dois** apps, e correção do link "/catalogo" no
  menu lateral.

**RBAC.** Gerenciador continua exclusivo de `SUPERADMIN`. A exceção é `elenco-busca`, aberta
também a `COMERCIAL` e `FIGURINO` — comercial escala evento e figurino vincula ficha sem ser
superadmin.

**Regras de negócio.** Um Personagem aponta para **no máximo uma** Ficha por vez: vincular pelo
lado da Ficha **substitui** o vínculo anterior, nunca duplica.

**Pegadinhas.** Um *Build/Start Command* customizado no painel do Railway tem precedência sobre o
`nixpacks.toml` — foi exatamente um build command com sintaxe de Turborepo/pnpm que causou o erro
"Missing script: build". Os dois campos precisam ficar vazios.

---

### 185 — Catálogo Vitrine Completo: Temas, Personagens e Vídeo
`185-catalogo-vitrine-completo` · merge **2026-07-24** (`17e6e11`, + fix `528e561`) ·
migration **`9f1c3a7b5e2d`**

**Motivação.** O catálogo só suportava fotos e tratava cada produto como uma unidade indivisível —
invisível para o cliente que um Tema é composto por atrações individuais também contratáveis.

**Banco (migration `9f1c3a7b5e2d` — head atual).**
- **Nova tabela `catalog_characters`**: `catalog_item_id` (FK → `catalog_items`, **ON DELETE
  CASCADE**), `name`, `slug` (unique, prefixado pelo slug do Tema), `photo_url`, `video_url`,
  **`figurino_sheet_id`** (FK → `figurino_sheets`, **ON DELETE SET NULL**), `position`,
  `is_active`, `created_at`; índice `ix_catalog_characters_catalog_item_id`.
- **Nova coluna `catalog_items.video_url`** (Drive/MP4/Vimeo).

**Backend.**
- Novo `app/admin/catalog_character_ops.py`: `unique_character_slug`, `create_character`,
  `update_character`, `delete_character`, `_validate_video_url`, `_validate_photo_extension`.
- Novo `app/catalogo/media.py` (normalização/detecção do tipo de vídeo).
- Endpoints novos: `POST /api/admin/catalogo/<item_id>/personagens`,
  `PATCH|DELETE /api/admin/catalogo/personagens/<character_id>`,
  `GET /api/admin/catalogo/tags`, `GET /api/catalogo/elenco-busca`.
  `GET /api/catalogo/<slug>` passou a devolver `video_url`, `video_kind` e o elenco de Personagens.

**Frontend.**
- **Público**: `VideoPlayer` (autoplay mudo em loop, botões próprios de som e tela cheia),
  `ProductGallery` com **transição animada de altura** entre foto horizontal e vídeo 9:16,
  `CharacterCard`/`CharacterGrid` para a seção **"Elenco Individual"**, `WishlistButton` por
  Personagem. Vídeo inválido é ignorado silenciosamente na vitrine.
- **Interno**: `ChipInput` (tags com Enter/vírgula, autocomplete das tags existentes),
  `AdminCatalogCharacterPanel` (CRUD de Personagens com foto, vídeo e dropdown de Ficha de
  Figurino), `ElencoBlock` do Novo Evento passando a auto-vincular a ficha do Personagem
  selecionado.
- Suíte E2E nova para catálogo público e admin; `verify_185.py` de verificação funcional.

**Regras de negócio.**
- URL de vídeo não reconhecida (não é Drive/MP4/Vimeo) é **recusada com erro no campo** no
  gerenciador.
- Excluir um Tema **apaga em cascata** seus Personagens; excluir uma Ficha **apenas desvincula**
  (`SET NULL`), sem apagar o Personagem.
- A lista de interesse do cliente aceita Tema completo **e** Personagem individual como itens
  distintos.

**Fix pós-merge (`528e561`).** Alvo de toque do botão "copiar link do Personagem" no mobile.

---

### 184 — Reconstrução do Formulário de Cadastro/Edição de Eventos
`184-eventos-formulario-completo` · merge **2026-07-24** (`1da7be6`) · **sem migration**

**Motivação.** `/events/new` no app React não tinha paridade de campos com a tela Jinja em
produção, forçando o vendedor a voltar para a tela antiga — risco real de dado divergente na tela
mais crítica do comercial. E a edição estava espalhada em várias ações soltas na tela de detalhe.

**Backend.**
- `app/calendar/event_ops.py` ampliado (+255 linhas): `update_event_core` e a reconciliação de
  elenco por `role_id`.
- `POST /api/events` e **`PATCH /api/events/<id>`** cobrindo os 7 blocos; `_build_create_event_data`
  / `_build_update_event_data` normalizam o corpo JSON. Validação central via `_validate_event_core`,
  devolvendo **`fields`** no envelope de erro para o formulário apontar o campo exato.
- `agenda_read.py` passou a serializar os campos que faltavam para pré-preencher a edição.
- Falha ao criar o evento no Google Calendar devolve **502** com mensagem amigável.

**Banco.** Nenhuma alteração — a feature foi de paridade e UX sobre o schema existente.

**Frontend.**
- `EventCreatePage.tsx` reescrita (982 linhas alteradas) e **`EventEditPage.tsx` nova** (489
  linhas), ambas montadas sobre **7 blocos** compartilhados em
  `src/components/EventFormBlocks/`: Cliente · Dados do Evento · Elenco · Valores · Pagamento ·
  Contrato · Observações.
- `eventFormSchema.ts` novo: validação `onBlur` imediata, banner de erro no topo **e** no rodapé,
  **auto-scroll suave até o primeiro campo inválido com foco**, e limpeza do destaque assim que o
  campo é corrigido.
- `ClientPicker` ganhou **cadastro rápido inline** (reaproveita cliente existente por telefone) e
  seletor de relação (Contratante/Assessora/Mãe-Pai/Familiar/Outros).
- `PendingAttachmentsPanel` novo: anexos escolhidos antes do evento existir sobem em **fase 2**,
  após a criação.
- Rota `/events/:id/edit` registrada no `App.tsx`; suíte E2E `event-form.spec.ts`.

**RBAC.** `_can_create_event()` / `_can_edit_event()` = `COMERCIAL` + `SUPERADMIN`, com paridade
verificada contra `_CAN_CREATE` / `_CAN_EDIT_EVENT` do Jinja. Acesso direto à URL de edição por
papel sem permissão (ex.: `ENSAIO`) é bloqueado no servidor.

**Regras de negócio confirmadas na tela.**
- Evento tipo **SHOW sempre gera ensaio**, independentemente do checkbox (o aviso é explícito).
- Percentual de desconto = `sale_value_gross − sale_value`, calculado em tempo real.
- *Faturado* exige vencimento; *Dividido no PIX* exige parcelas entre **2 e 12**.
- Fora de cortesia/permuta, os dois valores de venda são obrigatórios.
- Horário de fim não pode ser igual ao de início.
- Na edição, o elenco é **reconciliado** por `role_id` (não substituído), e agrupamento comercial
  / sincronização com o Google não são alterados pela feature.

---

### Contexto imediatamente anterior (para leitura do histórico)

| Feature | Entrega | Migration |
|---|---|---|
| **183** | Reestruturação do Banco de Figurinos — tags JSON na ficha, alerta "personagem sem ficha" com dispensa rastreável (`figurino_missing_dismissals`), impressão legada linkada da SPA | `7c2d9e4f1a3b`, `4e6f8a1c2d5b` |
| **182** | Revisão de mídia com Vimeo; correção do proxy Vite de `/uploads` | `aa1bb2cc3dd4` |
| **181** | Avaliações — fidelidade visual e RBAC | — |
| **180** | Módulo de Talentos completo (modo edição unificado em `/talents/:id?edit=1`) | — |
| **144** | Migração React SPA concluída (constituição v2.0.0) — fatias 145–177 | — |

**Correção pontual pós-187** — `6d6e234` (2026-07-25, branch `fix-figurino-nova-ficha-foto`):
completa o formulário de **Nova Ficha** de figurino (foto, textos de apoio, obrigatoriedade do
nome do personagem). Só frontend, sem impacto de schema, API ou RBAC.

---

## Convenções para as próximas entradas

1. **Append no topo** da seção "Registro", nunca no fim.
2. Sempre declarar **se houve migration** (e qual `revision`) — ou "sem migration", explicitamente.
3. Sempre declarar **impacto em RBAC**, mesmo quando for "nenhum".
4. Rotas novas ou alteradas precisam também ser refletidas em
   [`01_SISTEMA_E_BANCO.md`](01_SISTEMA_E_BANCO.md) §3 e, se tiverem tela,
   em [`02_MAPA_DE_PAGINAS_E_UX.md`](02_MAPA_DE_PAGINAS_E_UX.md).
5. Registrar **pegadinhas** descobertas na implementação — é a parte do documento que mais evita
   retrabalho.
