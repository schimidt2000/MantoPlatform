# 02 — Mapa de Páginas e UX

> **Documento vivo.** Atualizado obrigatoriamente ao fim de cada feature (ver regra em
> `CLAUDE.md` → "REGRA OBRIGATÓRIA DE DOCUMENTAÇÃO VIVA").
>
> Última atualização: **2026-07-28** · Estado do repositório: pós-feature **191**

Legenda de acesso — os papéis listados são os do gate **de servidor**; a navegação lateral
(`frontend/apps/internal/src/lib/navigation.tsx`) apenas espelha isso na UI.
`REVENDEDOR_EDUCAMANTO` puro (papel único) vê **somente** Agenda e EducaManto.

---

## A. App interno — `frontend/apps/internal` (staff autenticado)

Roteador: `apps/internal/src/App.tsx`. Todas as rotas autenticadas ficam dentro de uma *layout
route* `RequireAuth` → `AppShell` (feature 173). `*` redireciona para `/`.

### A.1 Acesso

#### `/login` — Login
- **Objetivo**: autenticar staff.
- **Acesso**: anônimo.
- **UX**: `POST /api/auth/login`, cookie de sessão HttpOnly; erro amigável em pt-BR; redireciona
  para `/`.

#### `AppShell` (moldura de todas as telas)
- Navegação lateral por seções: *(sem rótulo)* Home/Agenda/Gastos Extras · **Casting** ·
  **Produção** · **Comercial** · **Financeiro** · **Ferramentas** · **Sistema**.
- Seções sem itens visíveis desaparecem inteiras.
- Menu do usuário exibe os papéis; superadmin real tem o seletor **"Ver como"** (impersonação de
  `CASTING`/`FIGURINO`/`COMERCIAL`/`FINANCEIRO`/`ENSAIO`) — com impersonação ativa, o shell passa
  a contar **apenas** o papel simulado.
- Link **"Catálogo"** é `external: true` → abre `/catalogo/` (vitrine pública) em outra aba.

---

### A.2 Home e Agenda

#### `/` — Dashboard
- **Objetivo**: visão do dia/semana com pendências por papel.
- **Acesso**: todos exceto `REVENDEDOR_EDUCAMANTO` puro.
- **API**: `GET /api/dashboard` (`dashboard_service.py`).
- **Vínculos**: cards levam a Agenda, Casting, Figurino e Financeiro.

#### `/agenda` — Agenda
- **Objetivo**: enxergar os eventos por período.
- **Acesso**: todos (inclusive `REVENDEDOR_EDUCAMANTO`).
- **UX**: 3 modos de visualização controlados por querystring (`?view=month|list|day&date=`) —
  **Mês** (`CalendarGrid`), **Lista** (`AgendaListView`) e **Dia** (`DayTimelineView`, linha do
  tempo). Clicar num dia da grade navega para `view=day`. Toolbar (`AgendaToolbar`) troca período
  e modo. Transições com Framer Motion respeitando `useReducedMotion()`.
- **API**: `GET /api/agenda`, `GET /api/agenda/day/<date_str>`.
- **Vínculos**: cada evento abre `/events/:id`.

#### `/events/new` — Novo Evento *(reconstruída na feature 184)*
- **Objetivo**: cadastrar um evento com **100 % de paridade de campos** com a tela antiga, em uma
  única página. É a tela mais crítica do comercial.
- **Acesso**: `COMERCIAL`, `SUPERADMIN` (`_can_create_event()` → `_CAN_CREATE`).
- **Estrutura — 7 blocos** (`components/EventFormBlocks/`):
  1. **Cliente e pré-contrato** (`ClienteBlock`) — busca de cliente (`ClientPicker`),
     **"+ Cadastrar novo cliente"** inline (`POST /api/clientes/quick-create`, reaproveita cliente
     existente se o telefone bater), seletor de **relação** por cliente (Contratante, Assessora,
     Mãe/Pai, Familiar, Outros) e vínculo com resposta de formulário (`FormResponsePicker`).
  2. **Dados do evento** (`DadosEventoBlock`) — tipo, data, horários, local, descrição. Tipo
     `SHOW` exibe o aviso *"Eventos SHOW sempre geram ensaio automaticamente"*.
  3. **Elenco** (`ElencoBlock`) — linhas dinâmicas de personagem/equipe com
     **`CharacterAutocomplete`**: busca visual com **miniatura de foto**, restrita a
     **Personagens filhos ativos** do catálogo (Temas pai não aparecem); ao selecionar, preenche
     nome **e `figurino_sheet_id`**. Sem foto → placeholder, sem quebrar o layout. Botão
     **"Gerar título automaticamente"** monta `(TIPO) PERSONAGEM 1 + PERSONAGEM 2` e para de
     sobrescrever assim que o título é editado à mão. Flags por linha: `needs_makeup`,
     `is_singer`, cachê e talento.
  4. **Valores e comissões** (`ValoresBlock`) — valor cheio × valor de venda com **percentual de
     desconto calculado em tempo real**, transporte, acréscimos, cortesia/permuta, vendedor.
     Máscara BRL sempre via `@manto/money`.
  5. **Forma de pagamento e comprovantes** (`PagamentoBlock`) — campos condicionais: *Faturado* →
     vencimento; *Dividido no PIX* → parcelas (2–12). Múltiplos comprovantes, cada um com valor.
  6. **Contrato** (`ContratoBlock`) — upload do arquivo + "Contrato já assinado".
  7. **Observações** (`ObservacoesBlock`) — texto, foto e link, com rótulo opcional.
  \+ Reembolso de despesas da cliente (descrição, valor, nota fiscal opcional).
- **Validação (US2 da 184)**: erro `onBlur` imediato com borda vermelha espessa e mensagem
  específica; ao submeter inválido, banner no topo **e** no rodapé e **auto-scroll suave até o
  primeiro campo com erro, com foco nele**; o destaque some assim que o campo é corrigido.
  Schema em `lib/eventFormSchema.ts`.
- **Anexos**: `PendingAttachmentsPanel` guarda os arquivos escolhidos e os envia em **fase 2**,
  depois que o evento já existe (os endpoints de arquivo precisam do `event_id`).
- **API**: `GET /api/events/new/options`, `/prefill` · `POST /api/events` (+ endpoints de
  `contracts`, `payments`, `invoices`, `observations`, `reimbursements`).
- **Vínculos entre módulos**: Catálogo → Elenco (auto-vínculo da Ficha de Figurino) ·
  Cliente ↔ Evento · Orçamento (`orcamento_history_id`) · Google Calendar (o evento é criado lá
  primeiro; falha devolve **502** com mensagem amigável).

#### `/events/:id/edit` — Editar Evento
- **Objetivo**: mesma tela unificada da criação, pré-preenchida — substitui as várias ações
  soltas da tela de detalhe.
- **Acesso**: `_can_edit_event()` (`COMERCIAL`, `SUPERADMIN`).
- **UX**: mesmos 7 blocos; o elenco é **reconciliado** por `role_id` (não substituído);
  novos anexos entram ao lado dos existentes. Agrupamento comercial e sincronização com o Google
  não são alterados pela edição.
- **API**: `PATCH /api/events/<id>`.

#### `/events/:id` — Detalhe do Evento
- **Objetivo**: painel operacional completo do evento.
- **Acesso**: todos os autenticados; **ações** gateadas por papel. **O que existe na tela é o
  que o servidor serializa** — nenhum bloco é escondido por CSS.
- **Layout (feature 190)**: duas colunas de alta densidade a partir de `xl` (empilha abaixo
  disso). **Cabeçalho**: título, badge de tipo, faixa horária, badge de confirmação e o menu
  **"⋯ Ferramentas"** (`KebabMenu` com `triggerLabel`) — Sincronizar · Exportar elenco (modal
  com seleção de campos e cópia) · Editar no Google Agenda · Confirmar dados do evento ·
  Cobrança · Cobrar reembolsos · Marcar evento como confirmado · Pedir feedback da cliente ·
  Excluir evento. Itens indisponíveis ficam desabilitados **com `title` explicando o porquê**.
  - **Coluna esquerda (operação)**: *Resumo para WhatsApp* (descrição do Google/Kommo
    convertida de HTML para texto puro, em fonte monoespaçada, com botão copiar) · *Casting* ·
    *Equipe de apoio* (mesmos cards, `role_type="extra"`) · *Figurino* · *Logística & trajeto* ·
    *Materiais de ensaio* · *Observações*.
  - **Coluna direita (comercial/financeiro)**: *Comercial — dados da venda* (clientes com
    relação, bruto/desconto/final, forma de pagamento, vendedor, acréscimos com marcação de BV) ·
    *Resultado* (grade de KPI: venda, custo de cachês, gastos extras, comissão e **lucro
    líquido** em verde/vermelho, + lista dos gastos extras aprovados) · *Contrato assinado* ·
    *Notas fiscais* · *Comprovantes de pagamento* (badge "Quitado" quando recebido ≥ venda) ·
    *Reembolsos*.
  - **Rodapé**: *Avaliações dos artistas* (média + notas individuais com tags por critério) ·
    *Feedback da cliente* · *Log de atividades* (accordion) — **este só existe no DOM para
    `SUPERADMIN`**.
- **UX/ações**: escalar talento no cargo (`/roles/<id>/assign`), enviar convite
  (`invite` → `pending`/`accepted`/`rejected`), copiar convite individual / abrir WhatsApp do
  talento, **status de pagamento do cachê** por cargo, marcar/desmarcar figurino separado,
  **vincular ficha de figurino** ao personagem, dispensar/restaurar cargo (só `SUPERADMIN`),
  confirmar evento (`COMERCIAL`/`SUPERADMIN`), editar logística (maquiagem/saída, com estimativa
  de rota do Google Maps), materiais de ensaio (arquivo e link), observações, contratos,
  comprovantes, notas fiscais, reembolsos, sincronizar com o Google, excluir. Cada mutação
  coloca **só o seu próprio controle** em estado de carregamento (Princípio V).
- **Indicador de agenda**: cada card de casting mostra "Mesmo dia"/"Conflito" quando o talento
  tem outro evento na mesma data (`talent_availability`), com o evento concorrente no `title`.
- **API**: `GET /api/events/<id>` (payload único da tela) · `POST /api/roles/<id>/payment-status`
  · `POST /api/roles/<id>/figurino-sheet` · `POST|DELETE /api/roles/<id>/figurino-done` ·
  `POST /api/events/<id>/travel-estimate` · `POST /api/events/<id>/materials` ·
  `DELETE /api/materials/<id>` · `POST /api/events/<id>/feedback-link`.
- **Vínculos**: Talentos · Figurino (`EventRole.figurino_sheet_id`) · Financeiro (comissões e
  pagamentos) · Ensaios (`parent_event_id`) · Grupo comercial (`group_leader_id`) · Clientes ·
  Gastos Extras (`SpecialExpense.event_id`) · Avaliação pública da cliente (`/avaliar/<token>`).

---

### A.3 Casting

#### `/talents` — Banco de Talentos
- **Acesso**: todos exceto `REVENDEDOR_EDUCAMANTO`; **edição** só `CASTING`/`SUPERADMIN`.
- **UX**: `TalentMosaic` (grade visual com foto) + `TalentFilterPanel` (status, tags, medidas,
  passaporte/visto, idiomas). Estados `pending` × `active`.
- **API**: `GET /api/talents/directory`.

#### `/talents/:id` — Detalhe / Edição do Talento
- **UX**: modo edição unificado via `?edit=1`. A rota antiga `/talents/:id/edit` **redireciona**
  para cá (feature 180). Aprovar/rejeitar, notas internas + `warning_level` (nunca exibidos no
  Portal do Artista), foto de rosto/corpo, mídia de portfólio, histórico de avaliações.
- **API**: `GET /api/talents/<id>`, `/ratings` · `PATCH /api/talents/<id>` ·
  `POST /api/talents/<id>/{approve,reject,notes,photo}`.

#### `/casting/avaliacoes` — Avaliação de Casting
- **UX**: avaliações por evento/talento, com sub-notas e versionamento; modo **anônimo total**
  controlado por `SiteSetting.ratings_fully_anonymous` (esconde a autoria até do superadmin).
- **API**: `GET /api/ratings` · `POST /api/ratings/modo-anonimo`.

---

### A.4 Produção

#### `/revisao` — Revisão de Mídia
- **Acesso**: staff (criação de espaço também por `MARKETING`).
- **UX**: lista de espaços com status de aprovação.

#### `/revisao/novo` — Novo Espaço
- Seleção de revisores (`GET /api/revisao/reviewer-options`).

#### `/revisao/:id` — Espaço de Revisão
- **UX**: grade de assets, upload, gestão de revisores, exclusão.

#### `/revisao/:spaceId/asset/:assetId` — Asset em Revisão
- **UX**: player/imagem com **comentários em thread**, marcação de resolvido, **versionamento**
  (replace cria `ReviewAssetVersion`), status de aprovação e finalização. Suporte a Vimeo
  (feature 182).
- **API**: `revisao_read.py` / `revisao_write.py`.

#### `/figurinos` — Banco de Figurinos
- **Acesso**: staff; **edição** só `FIGURINO`/`SUPERADMIN`.
- **UX**:
  - Busca por nome + filtro por **tags** (chips).
  - Alerta **"personagem sem ficha"**: cargos de evento cujo `character_name` não casa com
    nenhuma ficha. Ações: **dispensar** (`POST /api/figurino/faltantes/dispensar`, grava os
    `event_role_ids` cobertos — um cargo novo faz o alerta voltar) ou **associar**
    (`/faltantes/associar`).
  - Indicador **"⚠ Sem personagem vinculado"** com botão **"+ Vincular"** que abre um modal de
    associação rápida a um Personagem do catálogo — **2 cliques, sem abrir a tela de edição**
    (feature 186, US2).
  - Link para a impressão legada `GET /figurinos/<id>/print` (Jinja) — em dev, proxy Vite
    **escopado por regex** para não sequestrar a rota SPA `/figurinos`.
- **API**: `GET /api/figurino`, `GET /api/catalogo/elenco-busca`,
  `PATCH /api/admin/catalogo/personagens/<id>`.

#### `/figurinos/new` e `/figurinos/:id/edit` — Ficha de Figurino
- **UX**: nome do personagem (obrigatório), foto (upload, rotação, remoção), **peças** como lista
  `{name, qty}`, **tags** via `ChipInput`, notas.
  Campo **"Vincular a um Personagem do Catálogo"** (`FigurinoCatalogLinkField`): autocomplete de
  Personagens; quando já vinculado, mostra `Personagem — Tema` e botão **Desvincular**. Escreve na
  mesma `CatalogCharacter.figurino_sheet_id` usada pelo lado do catálogo — **vínculo bidirecional
  sem coluna nova** (feature 186).
  Numa ficha nova, a foto escolhida só sobe **após** a ficha existir (o endpoint de foto exige
  `sheetId`).
- **API**: `POST /api/figurino` · `PATCH|DELETE /api/figurino/<id>` ·
  `POST|DELETE /api/figurino/<id>/photo` · `POST /api/figurino/<id>/photo/rotate`.
- **Vínculos**: Ficha ↔ Personagem do Catálogo ↔ Elenco de Evento (`EventRole`).

---

### A.5 Comercial

#### `/vendas` — Pipeline de Vendas
- **Acesso**: `COMERCIAL`, `FINANCEIRO`, `SUPERADMIN` ou responsável EducaManto.
- **UX**: eventos com venda, custo e comissão calculados; agrupamento comercial considerado.
- **API**: `GET /api/vendas/pipeline`.

#### `/clientes` · `/clientes/:id` — Clientes
- **Acesso**: `COMERCIAL`, `FINANCEIRO`, `SUPERADMIN` (`_require_vendas()`).
- **UX**: busca, criação rápida (dedupe por telefone), edição, exclusão, histórico de eventos.

#### `/clientes/avaliacoes` — Avaliações de Clientes
- **UX**: feedback recebido pelo link público `/avaliar/<token>`; o link é gerado sob demanda a
  partir do evento (token aleatório de 43 chars, nunca o id sequencial).

#### `/financeiro/comissoes` — Comissões *(reestruturada na feature 187)*
- **Acesso**: `COMERCIAL`, `FINANCEIRO`, `SUPERADMIN` ou responsável EducaManto.
- **Duas personalidades, decididas no servidor** (`can_manage`):
  - **Vendedor comum** → título **"Minhas Comissões"**, só as próprias linhas, **nenhum** controle
    de pagamento. O responsável EducaManto sem papel Financeiro cai aqui.
  - **Financeiro/Superadmin** → título **"Comissões"**, seletor de vendedor, ações de liquidação.
- **UX**:
  - Seletor de **mês** (`AAAA-MM`) com fallback tolerante para o mês corrente.
  - **3 cards de KPI**: Total do mês · Pago · A pagar (`MetricBadge`), somados da mesma fonte que
    alimenta os botões "Pagar Mês" — batem centavo a centavo.
  - **Duas abas** (`Tabs`): **Resumo por Vendedor** (linha por vendedor com contagem de vendas,
    total, pendente e status do mês; `AccordionRow` expande os eventos que compõem o total) e
    **Detalhamento de Vendas** (uma linha por comissão, com filtros por vendedor/evento/status).
  - **"Pagar Mês"** abre `Dialog` de confirmação com o valor exato **somado no servidor**; após
    confirmar, KPIs, status do vendedor e detalhamento atualizam **sem F5** (TanStack Query).
    Vendedor sem nada `a_pagar` → ação desabilitada.
  - **"Exportar Relatório (CSV)"** do resumo do mês (mês vazio → só o cabeçalho).
  - **Estornos** (valores negativos pendentes) aparecem em qualquer mês até serem resolvidos e são
    liquidados **junto** com as comissões do vendedor — nunca isoladamente.
- **API**: `GET /api/financeiro/comissoes` · `POST /api/financeiro/comissoes/pagar-mes`.

#### `/formularios` — Respostas e Editor de Formulários
- **Acesso**: `_require_vendas()` (COMERCIAL/FINANCEIRO/SUPERADMIN) para as respostas; **editor de
  campos** só `SUPERADMIN`.
- **Gerenciador de links públicos** (topo): dois cards — **Pré-Contrato (comum)** ("Festas e
  eventos de pessoa física") e **Contrato Corporativo** ("Empresas / pessoa jurídica") — cada um
  com a URL pública em campo somente-leitura (`{origin}/catalogo/f/pre-contrato` e
  `/catalogo/f/corporativo`, servidas por `apps/public` sob `/catalogo/*`), **"Copiar link"** com
  confirmação inline "✓ Copiado" (+ `aria-live`), **"Abrir"** em nova aba e, só para SUPERADMIN,
  **"✎ Editar campos deste formulário"**.
- **Tabela densa de respostas** (colunas): **Contratante** (nome + telefone), **Formulário**
  (badge), **Data do evento** (`event_date`), **Recebida em** (`created_at` com **data e hora**,
  `DD/MM/AAAA HH:mm`), **Situação** (dois badges coloridos — verde "Cliente: `<nome>`" /
  âmbar "Sem cliente"; verde "Evento vinculado" / âmbar "Sem evento") e **Ver**. Rola dentro do
  próprio contêiner no mobile.
- **Filtros**: busca persistente por nome do contratante ou telefone (usa `…/respostas/search`
  a partir de 2 caracteres) combinada com abas **Todos / Pré-contrato / Corporativo**.
- **Detalhe (`Dialog`)**: todos os campos preenchidos agrupados por seção; associar a cliente
  existente (busca), associar ao cliente sugerido por telefone, **criar cliente a partir da
  resposta** (`POST …/associar` sem `client_id` — reaproveita por telefone e ainda preenche
  CPF/CNPJ/endereço), desassociar; vincular/desvincular evento por data, **"Criar evento com os
  dados desta resposta"** (`/events/new?form_response_id=<id>`) e excluir (SUPERADMIN, com
  confirmação inline).
- **Editor de campos (`Dialog`, SUPERADMIN)**: abas comum/corporativo, campos agrupados por seção
  com marca de obrigatório e etiqueta "sistema"; criar, editar, reordenar (↑/↓) e excluir. Na
  edição, **seção e tipo ficam travados** (imutáveis no backend); `options` de campos de seleção
  aparece como textarea (uma opção por linha) e o PATCH envia o **payload completo** —
  `update_field` substitui `help_text`/`placeholder`/`required`, então omitir apagaria.
- **Vínculos**: `FormResponse` → `Client` e `CalendarEvent`; a resposta pode ser puxada no Bloco 1
  de Novo Evento (`FormResponsePicker`) ou já chegar pré-preenchida lá via
  `?form_response_id=` (pré-contrato vinculado + data do evento + cliente associado).

#### `/admin/catalogo` — Gerenciador de Catálogo *(features 185 e 186)*
- **Acesso**: **`SUPERADMIN`** (`_require_superadmin()`).
- **UX**:
  - **Alternador de visualização Cards ⇄ Árvore**, persistido em `localStorage`
    (`manto_admin_catalogo_view`); trocar o modo limpa a seleção.
  - **Cards** (`CatalogCardGrid`): grade de Temas com capa, status e **kebab menu** (`KebabMenu`)
    de ações por card.
  - **Árvore** (`CatalogTreeView`): Tema expansível com os Personagens filhos recuados e guia de
    hierarquia; por linha de Personagem — selecionar, ativar/inativar, excluir e
    **"+ Vincular Ficha"** (associação rápida).
  - **Seleção múltipla + barra flutuante de ações em massa** (`CatalogBulkActionBar`): aparece com
    1+ selecionados e some ao zerar. Ações: **Mover para…** (só para Personagens — um Tema não tem
    pai neste modelo), **Inativar**, **Excluir** (com confirmação em `Modal`).
  - Indicador **"Sem ficha vinculada"** nos Personagens pendentes.
  - Filtros: busca, categoria e status (todos/ativos/inativos).
- **API**: `GET /api/admin/catalogo` (+ `/tags`) ·
  `POST /api/admin/catalogo/personagens/mover-em-massa` ·
  `PATCH|DELETE /api/admin/catalogo/personagens/<id>` ·
  `POST /api/admin/catalogo/<id>/toggle-ativo`.

#### `/admin/catalogo/novo` e `/admin/catalogo/:id/editar` — Tema do Catálogo
- **UX**: nome, slug, descrição HTML curta, categorias, `is_active`, **URL de vídeo**
  (Drive/MP4/Vimeo — URL não reconhecida é recusada com erro **no campo**), **tags como
  `ChipInput`** (Enter ou vírgula vira chip removível, com autocomplete das tags já usadas no
  catálogo — `GET /api/admin/catalogo/tags`).
- **Galeria de fotos**: upload múltiplo, **reordenação** e **seleção de capa** (a foto em
  `position = 0` é a capa e o Open Graph do link público).
- **Painel de Personagens** (`AdminCatalogCharacterPanel`): adicionar/editar/remover Personagem
  filho com nome, foto, URL de vídeo, ordem, ativo e **dropdown de busca da Ficha de Figurino**
  (`figurino_sheet_id`).
- **Vínculos**: Tema → Personagens → Ficha de Figurino → Elenco de Evento.

---

### A.6 Financeiro

#### `/financeiro` — Painel Financeiro *(reconstruído na feature 189)*
- **Acesso**: `FINANCEIRO`, `SUPERADMIN` (403 no endpoint para os demais).
- **UX**: filtro de período em pílulas (`este_mes`, `30d`, `mes_anterior`, `custom` com intervalo
  de datas) e **layout em grid de duas colunas**:
  - **Coluna principal (2/3)** — 4 KPIs em cards (Ticket Médio, Custo Talento/Receita, Margem
    Bruta, Margem Operacional/EBITDA, com faixa de cor verde/âmbar/vermelho); **Termômetro de
    Break-even** (barra de progresso da cobertura do custo fixo `pessoal + comissões` + meta em
    BRL); **Alerta Fiscal — Fator R** (barra de progresso contra o `fator_r_threshold` + badge
    "🛡️ Protegido" / "⚠️ Em risco" e a alíquota estimada de cada faixa); **DRE Gerencial** em
    3 visões (Realizado · Projetado · Total) com **identação hierárquica** — deduções `(–)`
    recuadas, subtotais `=` em faixa destacada e margem em % ao lado de Lucro Bruto e EBITDA;
    e os cards A Receber (clientes) / A Pagar / Pago (talentos).
  - **Coluna analítica (1/3)** — Receita por Tipo de Evento (barras horizontais proporcionais),
    Top Vendedores ranqueados (receita + lucro gerado), Auditoria de Input (eventos com receita
    zerada sem marcação de permuta/cortesia, com link para o evento), Notas a Emitir,
    Tendência dos últimos 6 meses (mês · receita · custo de talento · lucro · margem · nº de
    eventos) e Recebimentos Previstos.
  - **Largura total** — tabela de Eventos no Período (data, evento, tipo, status, receita, custo,
    lucro, comissão, taxa).
- **API**: `GET /api/financeiro/dashboard`.
- **Vínculos**: cada linha de evento/auditoria/recebimento leva a `/events/<id>`; a linha de
  Gastos Recorrentes do DRE reflete os lançamentos de `/gastos/recorrentes`.

#### `/financeiro/pagamentos` — Planilha de Pagamentos *(paridade restaurada na feature 189)*
- **Acesso**: `FINANCEIRO`, `SUPERADMIN`.
- **UX**: itens de cachê, salário, gasto, BV, comissão e contas recorrentes em uma planilha
  única, na ordem de colunas clássica — **checkbox** (com "selecionar tudo") · **vencimento** ·
  **descrição detalhada** (badge do tipo + descrição do item, com botão de cópia) · **favorecido**
  em negrito · **valor** em BRL (com cópia do valor cru `1234,56`) · **chave PIX** com o tipo
  (CPF/CNPJ/E-mail/Telefone/Aleatória) e botão de cópia · **situação**. Os botões de cópia dão
  feedback "✓" temporário e anunciam por `aria-live`. Linha colorida por situação; badge
  "⏳ Futuro" em pendências com vencimento à frente; adiantamentos de salário (N por pagamento,
  com comprovante) no próprio valor; **export CSV**.
- **Situação**: seletor por linha com as opções que o backend suporta — **Não pago · No banco ·
  Pago** (comissão e conta recorrente não têm "No banco"). **Ações em lote**: marcar como pago,
  **como no banco**, como não pago, e excluir (com confirmação).
- **API**: `GET /api/financeiro/pagamentos` · `POST .../set-status`, `.../bulk-action`,
  `.../salary/<id>/advance` · `GET .../export`.

#### `/gastos` — Gastos Extras
- **Acesso**: staff para lançar; aprovar/rejeitar em `_require_financeiro()`.
- **UX**: fluxo criar → aprovar/rejeitar → reembolsar, com vínculo opcional a evento (feature 179
  trouxe RBAC e edição).

#### `/gastos/recorrentes` — Gastos Recorrentes *(refeita na feature 189)*
- **Acesso**: `FINANCEIRO`, `SUPERADMIN`.
- **UX**: seletor de **mês de referência** no topo, cards de resumo (estimativa mensal por tipo +
  total a pagar dos programados), alerta das contas que precisam de atenção no mês, formulário de
  criação e **três seções tabulares por tipo**:
  1. **Contas Variáveis** — colunas Conta · Vencimento · Frequência (com a vigência) · **Faixa de
     valor esperado** · **Mês MM/AAAA** · Ações. O status do mês mostra "aguardando valor",
     "a pagar"/"pago"/"pulado" com o valor lançado, "⚠" quando fora da faixa, "vence dd/mm" e
     "fora do ciclo" quando a conta não é cobrada naquele mês. Enquanto não há valor lançado, o
     botão **`[Preencher]`** aparece em destaque e abre um **Dialog** (`@manto/ui`) com
     `MoneyInput` (máscara BRL), PIX e vencimento — ao salvar, chama
     `POST /api/gastos/recorrentes/<id>/preencher`, gera o `RecurringExpenseEntry` e o item passa
     a aparecer na Planilha de Pagamentos e na linha "Gastos Recorrentes" do DRE.
     Demais ações por linha: `[Pular mês]`, `[Pagar]`/`[Reabrir]`, `[Histórico]`, `[Editar]`,
     `[Desativar]`/`[Reativar]` e `[Excluir]` (só sem lançamentos).
  2. **Débito Automático** — despesas fixas debitadas em conta, com o lançamento do mês já
     "registrado" automaticamente.
  3. **Assinaturas (Cartão)** — inclui a coluna **Cartão** (ex.: "Inter Prime"), valor e status
     do mês corrente.
  Abaixo delas, **Pagamentos Programados** lista cada parcela (data, valor, situação) com pagar,
  reabrir e excluir parcela.
- **Formulário de criação**: nome, **tipo** (variável / débito automático / assinatura),
  frequência (mensal/semanal/quinzenal/anual), dia do vencimento **ou** dia da semana, vigência
  (início/fim, vazio = eterna), **faixa esperada ou valor exato** (variável) / valor fixo,
  cartão (assinatura), PIX padrão e observações.
- **Ações destrutivas ou irreversíveis** (pular mês, reabrir, desativar, excluir conta, excluir
  parcela) passam por Dialog de confirmação — Princípio V.
- **API**: `GET /api/gastos/recorrentes` · `GET /api/gastos/recorrentes/<id>/historico` ·
  `POST /api/gastos/recorrentes` (+ `/<id>/preencher`, `/pular`, `/toggle`) ·
  `PATCH|DELETE /api/gastos/recorrentes/<id>` ·
  `POST /api/gastos/recorrentes/entry/<id>/{pagar,reabrir}` · `DELETE .../entry/<id>`.
- **Vínculos**: cada lançamento preenchido/registrado entra em `/financeiro/pagamentos` (tipo
  "Recorrente") e no DRE de `/financeiro` pelo mês de referência.

---

### A.7 Ferramentas

| Rota | Tela | Acesso | Destaques |
|---|---|---|---|
| `/orcamento` | Calculadora de Orçamento | `COMERCIAL`, `SUPERADMIN` | layout clássico de duas colunas assimétrico (1/3 dados do evento + segurança de agenda, 2/3 equipe/ajustes/resultado); **cálculo 100% reativo** — sem botão "Calcular", qualquer alteração recalcula (debounce ~400ms); alerta "Já na agenda neste dia" abaixo da Data (evita venda em dobro de personagem); painel "Personalizar valores" (valor final ou multiplicador, por duração); contador de itens no link "Histórico de Orçamentos"; distância (Google Maps), salvar no histórico, "Ver memória de cálculo"; lê `?recalcular_id=` para reabrir um orçamento salvo com os campos preenchidos (feature 191, sobre a base da feature 190) |
| `/orcamento/historico` | Orçamentos | `COMERCIAL`, `SUPERADMIN` | tabela densa com filtros avançados (data, valor, vendedor, tipo), PDF, envio por e-mail, exclusão; **Criar evento** (`/events/new?orcamento_id=`) e **Recalcular** (`/orcamento?recalcular_id=`), feature 190 |
| `/orcamento/configuracoes` | Config. Preços | `SUPERADMIN` | `SiteSetting.pricing_config` + personagens especiais, em tabelas densas (feature 190) |
| `/educamanto` | Calculadora EducaManto | `COMERCIAL`, `SUPERADMIN`, `ENSAIO`, `REVENDEDOR_EDUCAMANTO` | seletor de pacote em dropdown, duas colunas, cards Sem/Com Nota Fiscal, transporte, cálculo; lê `?package_id=` (vindo de "Usar" na tela de Pacotes) e `?recalcular_id=` (feature 190) |
| `/educamanto/pacotes` · `/novo` · `/:id/editar` | Pacotes EducaManto | `COMERCIAL`, `SUPERADMIN` | grade de cards com margens/desconto/matriz de custos; Usar, CRUD + duplicar (feature 190) |
| `/educamanto/historico` | Histórico EducaManto | mesmos da calculadora | tabela densa; Ver (Dialog com o snapshot), Baixar PDF e **Recalcular** (`/educamanto?recalcular_id=`), feature 190 |

---

### A.8 Sistema

| Rota | Tela | Acesso | Destaques |
|---|---|---|---|
| `/admin/usuarios` · `/novo` · `/:id` | Usuários | `SUPERADMIN`, `FINANCEIRO` | papéis, PIX, salário (`SalaryHistory`), conceder acesso, reset de senha, exclusão; usuários "apenas pagamento" (`has_access=False`) |
| `/admin/configuracoes` | Administração | `SUPERADMIN` | `SiteSetting`: cores/logo, comissão padrão, responsável EducaManto, imposto, Fator R, endereço base, ClickSign, e-mail, anonimato de avaliações, WhatsApp dos formulários |
| `/admin/logs` | Logs | `SUPERADMIN` | `AuditLog` |
| `/admin/desempenho` | Desempenho | `SUPERADMIN` | métricas por vendedor/período |
| `/admin/sync` | Sincronização Agenda | `SUPERADMIN` | status e execução manual do sync com o Google Calendar |
| `/admin/anuncio-portal` | Anúncio do Portal | `SUPERADMIN` | mensagem exibida no Portal do Artista |
| `/admin/migrar-arquivos` | Migrar Arquivos | `SUPERADMIN` | job de migração de storage com status |
| `/admin/importar-catalogo` | Importar Catálogo | `SUPERADMIN` | importação do export WordPress (dedupe por `wp_product_id`) |

---

## B. App público — `frontend/apps/public` (visitante anônimo)

Roteador: `apps/public/src/App.tsx`. Em **produção** roda sob o prefixo **`/catalogo`**
(`basename` + `base` do Vite + `frontend/server.js`); em dev roda na raiz.
Todas as telas são **mobile-first** (Princípio VIII).

#### `/catalogo/` — Vitrine (grade do catálogo)
- **Objetivo**: descoberta dos Temas ativos.
- **UX**: `ProductCard` com capa, busca e filtros; **lista de interesse** flutuante
  (`WishlistFloat`) sempre visível.
- **API**: `GET /api/catalogo`.

#### `/catalogo/categorias` e `/catalogo/categoria/:slug`
- Navegação por categoria com contagem de itens.

#### `/catalogo/:slug` — Página do Tema *(feature 185)*
- **UX**:
  - **`ProductGallery`** alternando fotos e vídeos. Vídeo (`VideoPlayer`) toca **automático, mudo
    e em loop**, sem controles nativos por cima do layout; botões próprios de **som** (não
    reinicia o vídeo) e **tela cheia**. A troca entre foto horizontal e vídeo vertical (9:16)
    **anima a altura do container**, sem salto. Vídeo inválido é **ignorado silenciosamente** na
    vitrine (e sinalizado no gerenciador interno).
  - Seção **"Elenco Individual"** (`CharacterGrid` + `CharacterCard`): um card por Personagem
    filho ativo, com foto/preview, nome e **"+ Adicionar à lista"** próprio. Tema sem Personagens
    → a seção **não é renderizada** (sem espaço vazio).
  - **"Adicionar à lista"** no cabeçalho adiciona o **pacote completo** como item único.
  - Botão de **copiar link do Personagem** (alvo de toque corrigido para mobile).
  - Open Graph usa a foto de `position = 0` do Tema.
- **API**: `GET /api/catalogo/<slug>`.

#### `/catalogo/lista-desejos` — Lista de Interesse
- **UX**: lista persistida em **`localStorage`** (degrada sem quebrar em modo privado/cota);
  revisar itens e **enviar por WhatsApp** (`api.whatsapp.com/send?phone=...&text=...`), com o
  número vindo de `SiteSetting` no payload do catálogo.

#### `/catalogo/cadastro` e `/catalogo/cadastro/enviado` — Cadastro de Talento
- **UX**: formulário público de candidatura; `GET /api/cadastro/check-cpf` valida duplicidade em
  tempo real (estrangeiro grava `cpf = NULL`). Cria `Talent` com `status = "pending"`.

#### `/catalogo/f/pre-contrato` · `/catalogo/f/corporativo` · `/catalogo/f/:formType/enviado`
- **UX**: formulários de pré-contrato com **schema dinâmico** vindo do servidor
  (`FormFieldDefinition`, editável em `/formularios`). Resposta vira `FormResponse` e dispara
  mensagem para o WhatsApp configurado.

#### `/catalogo/avaliar/:token` — Avaliação da Cliente
- **UX**: link público por token do evento; grava `ClientFeedback`, exibido em
  `/clientes/avaliacoes`.

---

## C. Portal do Artista — React (`frontend/apps/portal`)

SPA mobile-first própria, servida sob `/portal/*`. **Quem acessa:** talento autenticado por
sessão própria (`Talent.password_hash` → `session["talent_id"]`), separada da sessão de staff —
não há papéis dentro do portal. **RBAC:** "é o dono do recurso" — toda tela consome apenas dados
do talento da sessão.

**Onboarding.** Enquanto houver etapa de conta pendente (`pending_steps` de
`GET /api/portal/auth/me`), o `OnboardingGate` serve a etapa **no lugar** do app, em qualquer
rota — não existe URL de onboarding para pular, e um deep link para `/portal/agenda` com senha
pendente cai na mesma trava.

**Shell.** Header com foto/nome (atalho para o perfil) + botão Sair; navegação inferior fixa de
4 abas com contador de pendências em Convites (convites a responder) e Histórico (eventos a
avaliar). Alvos de toque ≥44px, nada abaixo de 12px, sem rolagem horizontal de 320px a 430px
(Princípio VIII).

| Rota (React) | Objetivo | UX e vínculos |
|---|---|---|
| `/portal/login` | Entrar com CPF ou e-mail | Links para primeiro acesso e recuperação; erro genérico, sem dizer qual campo errou |
| `/portal/first-access` | Receber senha temporária por e-mail | Confirma com o e-mail mascarado (`jo***@dominio.com`) |
| `/portal/forgot-password` | Pedir link de redefinição | Confirmação neutra — nunca revela se a conta existe |
| `/portal/reset-password/:token` | Definir nova senha pelo link do e-mail | Valida o token antes de mostrar o formulário; checklist de força ao vivo |
| *(gate)* Criar senha | Troca obrigatória no primeiro acesso | Servida pelo `OnboardingGate`, não é rota navegável |
| *(gate)* Termos | Aceite do Termo de Consentimento | Checkbox só libera após rolar o texto até o fim |
| `/portal/agenda` | Próximos eventos + histórico recente | Dia da semana + "amanhã"/"em 5 dias"; alerta de alteração com botão **Ciente**; link para a ficha de figurino |
| `/portal/convites` | Convites de casting pendentes | Botões **Aceitar** / **Recusar** (recusa pede confirmação); alimenta o contador da aba |
| `/portal/historico` | Histórico completo de apresentações | Somatórios recebido / a receber / total; cachê + deslocamento por evento; link para avaliar |
| `/portal/perfil` | Dados pessoais, **medidas corporais**, PIX e portfólio | Medidas alimentam o módulo de Figurino; até 3 fotos de atuação + links (Vimeo/YouTube) |
| `/portal/fotos-documentos` | Foto de rosto, corpo inteiro e CNH | Preview do arquivo atual antes de substituir |
| `/portal/eventos/:id/figurino` | Ficha de figurino do papel no evento | Peças, orientações e fotos; foto vem de `/portal/photo/<file>` (rota Jinja, mesma sessão) |
| `/portal/eventos/:id/avaliar` | Avaliar o evento | Etapa 1 nota geral (abaixo de 4 exige comentário); etapa 2 opcional por categoria e por pessoa; janela de 7 dias para avaliar, 30 para editar |
| `/portal/termos` | Reler o termo já aceito | Modo leitura, sem trava nem botão |

### C.1 Rotas Jinja legadas do portal (ainda registradas)

As rotas de `app/talent_portal` continuam de pé em paralelo (strangler-fig), servidas pelo Flask
em **outro domínio** — sem colisão com o `/portal/*` do serviço estático. Paridade verificada na
feature 191; decomissioná-las é limpeza futura.

`/portal/login`, `/first-access`, `/change-password`, `/forgot-password`,
`/reset-password/<token>`, `/terms`, `/logout`, `/portal/`, `/portal/historico`,
`/portal/profile`, `/portal/media/*`, `/portal/invites/<id>/{accept,reject}`,
`/portal/roles/<id>/ack-change`, `/portal/events/<id>/figurino`,
`/portal/events/<id>/rate[/detail]`.

> `/portal/photo/<file>` **não** é legado a decomissionar: serve as fotos de figurino checando a
> sessão de talento, e o app React depende dela.

---

## D. Vínculos entre módulos (mapa de relações)

```
        Catálogo (Tema)
             │ 1:N
             ▼
    Catálogo (Personagem) ──── figurino_sheet_id ────► Ficha de Figurino
             │                                              │
             │ busca visual (elenco-busca)                  │ vínculo bidirecional
             ▼                                              ▼
   Novo Evento / Elenco  ──── EventRole.figurino_sheet_id ──┘
             │
             ├──► Talento (EventRole.talent_id) ──► Convite ──► Portal do Artista
             ├──► Cliente (EventClient, tipo de relação)
             ├──► Orçamento (orcamento_history_id)
             ├──► Google Calendar (google_event_id / google_html_link)
             ├──► Financeiro: CommissionPayment (venda → comissão do vendedor)
             │                EventPayment / EventInvoice / EventInstallment
             ├──► Gastos (SpecialExpense.event_id)
             ├──► Ensaio (parent_event_id)  ·  Grupo comercial (group_leader_id)
             └──► Feedback da cliente (feedback_token → ClientFeedback)
```

Pontos de atenção recorrentes:
1. **Ficha ↔ Personagem é 1:1 por vez** — vincular a partir da Ficha substitui o vínculo antigo.
2. **A busca de elenco só oferece Personagens filhos**, nunca Temas pai (um Tema não é atração
   vendável isoladamente).
3. **`EventRole.character_name` é texto livre** — daí existir o alerta de "personagem sem ficha"
   em `/figurinos` e o fluxo de associação/dispensa.
