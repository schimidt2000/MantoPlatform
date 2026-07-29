# 02 — Mapa de Páginas e UX

> **Documento vivo.** Atualizado obrigatoriamente ao fim de cada feature (ver regra em
> `CLAUDE.md` → "REGRA OBRIGATÓRIA DE DOCUMENTAÇÃO VIVA").
>
> Última atualização: **2026-07-29** · Estado do repositório: pós-feature **204**

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
     **Local/Endereço do evento** é um **`GoogleAddressInput`** (feature 195): sugestões do Google
     Places conforme se digita (debounce 350ms, a partir de 3 letras), escolher uma grava o
     endereço normalizado. Continua aceitando digitação livre para locais que o Google não conhece.
  3. **Elenco** (`ElencoBlock`) — linhas dinâmicas de personagem/equipe com
     **`CharacterAutocomplete`**: busca visual com **miniatura de foto**, restrita a
     **Personagens filhos ativos** do catálogo (Temas pai não aparecem); ao selecionar, preenche
     nome **e `figurino_sheet_id`**. Sem foto → placeholder, sem quebrar o layout. Botão
     **"Gerar título automaticamente"** monta `(TIPO) PERSONAGEM 1 + PERSONAGEM 2` e para de
     sobrescrever assim que o título é editado à mão. Flags por linha: `needs_makeup`,
     `is_singer`, cachê e talento.
     **Feature 195 — os três `<select>` do bloco viraram `Combobox` pesquisáveis com miniatura**
     (Princípio X.1/X.2): *Buscar figurino* (miniatura **quadrada** da foto da ficha, via
     `photo_url`), *Pré-escalar talento específico* e *Coordenador específico* (avatar
     **circular**, via `photo_face_path` + `assetUrl()`). Digitar filtra em tempo real ignorando
     acentos; setas/Enter/Esc navegam; sem foto salva aparece o placeholder de iniciais (talentos)
     ou 🎭 (figurinos).
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
  não são alterados pela edição. Herda automaticamente os comboboxes visuais e o
  `GoogleAddressInput` da feature 195 — os blocos são os mesmos componentes da criação. Ao abrir um
  evento já salvo, o endereço existente aparece no campo **sem** consultar o Google (só o que o
  usuário digitar dispara busca).
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

### A.4.1 Impressão 3D *(seção nova de navegação — feature 200)*

Grupo próprio na navegação lateral, visível apenas para `ARTISTA_3D` e `SUPERADMIN`.

#### `/3d/fila` — Fila de Impressão
- **Acesso**: `ARTISTA_3D`, `SUPERADMIN` (gate de servidor em `GET /api/3d/fila`).
- **Objetivo**: painel operacional com os **dois** blocos de trabalho do Artista 3D.
- **UX — bloco 1: "Shows sem presente vinculado" (feature 202)**:
  - **A pendência nasce do evento, não do presente**: todo SHOW de hoje em diante que ainda não
    tem presente vinculado aparece aqui automaticamente. Antes da 202 a fila só listava presentes
    já cadastrados e ficava vazia até alguém lembrar de vincular algo — o trabalho não aparecia.
  - Cada linha traz título do show (link para `/events/:id`), data, os **personagens contratados**
    (para reconhecer o show de relance) e o selo de urgência.
  - **"Vincular presente"** abre um `Dialog` com o mesmo formulário da tela do evento
    (`AddPresente3DForm`, fonte única), com o **prazo já pré-preenchido com a data do show** — a
    pendência é resolvida sem sair da fila.
  - **"Não leva presente"** dispensa a pendência (`Event3DDismissal`), igual ao "dispensar" do
    personagem sem ficha em `/figurinos`. O checkbox **"Mostrar dispensados"** revela os
    dispensados com botão **"Reativar"**.
- **UX — bloco 2: presentes a imprimir**:
  - Tabela densa (`Table` do design system, com `overflow-x-auto` próprio — nada de rolagem
    horizontal na página): miniatura **quadrada** da peça + nome, evento (link para `/events/:id`)
    e local, data do evento, prazo com **selo de urgência** (`Atrasado Xd` / `Hoje` em vermelho,
    `Em ≤7d` em dourado), quantidade e status.
  - **Seletor rápido de status** por linha (`pendente` ➔ `imprimindo` ➔ `finalizado` ➔
    `entregue`) — `<select>` nativo é legítimo aqui: 4 opções, bem abaixo do limite de 10 do
    Princípio X.1. Salva na hora com feedback "Salvando…"/"Erro ao salvar"; marcar `entregue`
    tira a linha da fila.
  - Botão **"Ver Detalhes para Impressão"** abre um `Dialog` com **links de download de cada
    arquivo 3D da peça** (o Artista 3D imprime sem passar pelo Acervo) e que cruza os dados da API:
    **Personagens contratados** (com miniatura quadrada e talento escalado) e o **extrato do
    Formulário de Pré-Contrato**, mostrando só os campos que a cliente preencheu — é lá que estão
    "Nome do Aniversariante" e "Idade a Completar do Aniversariante", que definem o que imprimir.
  - Estados de carregamento (`Skeleton`), erro e vazio ("Nenhum presente 3D pendente") em pt-BR.
- **API**: `GET /api/3d/fila[?dispensados=1]` · `PATCH /api/events/<id>/3d-gifts/<gift_id>` ·
  `POST /api/events/<id>/3d-gifts` · `POST|DELETE /api/events/<id>/3d-dismissal`.
- **Vínculos**: Evento (`CalendarEvent`) → Elenco (`EventRole`) → Formulário (`FormResponse`) →
  Acervo 3D (`Acervo3DItem`).

#### `/3d/acervo` — Acervo 3D
- **Acesso**: `ARTISTA_3D`, `SUPERADMIN`.
- **Objetivo**: catálogo dos modelos base que podem virar presente de um evento.
- **UX**:
  - **Formulário no topo** — "Foto de Preview (JPG/PNG)" (via `FileUpload` do design system) e
    **"Arquivos 3D (.stl, .3mf, .zip)"**, um input `multiple`: uma mesma peça costuma vir fatiada
    em várias partes (corpo, argola, base) e todas são enviadas de uma vez (feature 201). Foto e
    **pelo menos um** arquivo são obrigatórios no cadastro; o erro é realçado no campo exato
    devolvido pela API (`fields`) e o formulário **nunca é limpo em caso de falha** (Princípio
    V) — a limpeza só acontece no sucesso, remontando o formulário por `key` (o `FileUpload`
    guarda o nome do arquivo em estado interno próprio).
  - Na **edição** os arquivos 3D são **cumulativos**: os já salvos aparecem listados com link de
    download e um ✕ que os marca para remoção (com "Desfazer"), e o input adiciona novos. O
    servidor recusa (400) qualquer combinação que deixaria a peça com zero arquivos.
  - **Grade de cards** (4 colunas no desktop, 1 no mobile) com a foto em `aspect-square`, o nome,
    badges com **a contagem de usos em eventos** e o **nº de arquivos 3D**, badge "Inativa"
    quando aplicável, a lista de arquivos para download (pelo nome original) e ações: editar
    (abre `Dialog` com o mesmo formulário), inativar/reativar e excluir.
  - **Exclusão** pede confirmação em `Dialog`; peça já vinculada a evento é bloqueada pelo
    servidor com a mensagem orientando a inativar em vez de excluir.
  - Entrada/saída de cards com Framer Motion respeitando `useReducedMotion()`.
- **API**: `GET|POST /api/3d/acervo` · `PATCH|DELETE /api/3d/acervo/<id>`.

#### `/events/:id` — bloco **"Presentes 3D"** *(injeção na tela existente)*
- **Onde**: coluna esquerda (operação/logística), logo abaixo de "Materiais de ensaio".
- **Quando**: **somente** se `event.event_type === 'SHOW'` — o servidor nem serializa a chave
  `presentes_3d` nos outros tipos.
- **Acesso**: qualquer usuário que abre o evento **lê** a lista; só `ARTISTA_3D`/`SUPERADMIN`
  (flag `can_manage_3d`) vê o formulário de adição, o seletor de status e o botão de remover.
- **UX**: lista com miniatura quadrada, quantidade, prazo e observações; o formulário de adição
  usa obrigatoriamente o **`Combobox` de `@manto/ui`** (Princípio X.1) exibindo a **miniatura
  quadrada (`AvatarThumb`)** de cada peça do Acervo para seleção visual rápida, mais quantidade,
  prazo e observações.
- **API**: `POST|PATCH|DELETE /api/events/<id>/3d-gifts[/<gift_id>]` · `GET /api/3d/acervo?ativos=1`.

---

### A.4.2 Marketing *(seção nova de navegação — feature 204)*

Grupo próprio na navegação lateral (entre "Impressão 3D" e "Comercial"), visível apenas para
`MARKETING` e `SUPERADMIN`.

#### `/marketing/painel` — Painel de Marketing
- **Acesso**: `MARKETING`, `SUPERADMIN` (gate de servidor em `GET /api/marketing/posts`).
- **Objetivo**: conduzir a produção de conteúdo do brainstorm ao ar, no mesmo lugar onde já vivem
  o catálogo (o Tema do post) e a revisão de mídia (a aprovação do material).
- **UX — alternador de visualização (Tabela ⇄ Kanban)**:
  - Persistido em `localStorage` (`manto_marketing_painel_view`), **mesmo padrão da tela
    `/admin/catalogo`** — a visão escolhida sobrevive ao recarregar.
  - O "trilho" do item ativo é um `motion.span` com `layoutId` que **desliza** entre as duas
    opções; a troca de visão é um `AnimatePresence mode="wait"` (fade + deslocamento de 8px,
    220ms). Ambos zerados sob `useReducedMotion()`.
- **UX — Kanban (Framer Motion)**:
  - Cinco colunas na ordem do fluxo: 💡 Ideia · 🎬 Produção · 👀 Revisão · 📅 Agendado ·
    🚀 Publicado, cada uma com contador e um "+" que abre o Dialog **já com aquele status
    pré-selecionado**.
  - Cada card tem `layoutId={"marketing-post-<id>"}` dentro de um `LayoutGroup`: ao mudar de
    coluna, o card **desmonta de uma e monta na outra** e o Framer interpola a posição — o
    movimento comunica a causa (o gesto) e o efeito (a nova coluna). Entrada/saída via
    `<AnimatePresence>` (`opacity`+`scale`, 280ms).
  - **Duas formas de mover, ambas com atualização otimista** (o card sai andando no gesto, não
    quando a API responde; erro reverte o cache e mostra "Erro ao mover"):
    - **Arrastar e soltar** (mouse/toque): o card é `drag` do Framer, com `whileDrag` (escala 1.04
      + sombra), cursor `grab`/`grabbing`, alça visual (`GripVertical`) e `dragConstraints` no
      próprio quadro — sem isso o `overflow-x-auto` recortaria o card no meio do gesto. A coluna
      sob o ponteiro **se realça** (borda/anel `accent`) e uma coluna vazia mostra **"Solte aqui"**;
      a coluna de origem não pisca. Enquanto o card está no ar, o quadro deixa de rolar por toque
      (`touch-action: none`), senão a rolagem competiria com o gesto.
      O alvo é resolvido por `elementsFromPoint` em coordenadas de **viewport** (`clientX/clientY`
      do ponteiro, ou `changedTouches` no toque) — a pilha de elementos alcança a coluna mesmo com
      o card levantado por cima dela. Soltar **fora de qualquer coluna** ou na mesma coluna não
      dispara requisição: o card volta sozinho (`dragSnapToOrigin`).
      Um arraste **não** abre o Dialog: o card guarda em `ref` que houve arraste e ignora o `click`
      que vem depois do `pointerup` (o `ref` é zerado no `pointerdown` seguinte).
    - **Setas ◀ ▶** no rodapé do card, para etapa anterior/seguinte — é o caminho de **teclado**
      (arrastar não é acessível por teclado) e o confortável em tela estreita. Uma linha de ajuda
      abaixo do quadro explica as duas formas.
  - O card mostra miniatura **quadrada** do Tema, título, plataforma, selo de urgência do prazo
    (`Atrasado Xd`/`Hoje` em vermelho, `≤3d` em dourado), situação do espaço de revisão, ícone de
    pasta quando há acervo no Drive, avatar **circular** do responsável e a data de publicação.
  - Rolagem horizontal fica **dentro** do quadro (`overflow-x-auto`) — a página nunca rola na
    horizontal, nem em 375px.
- **UX — tabela densa**: `Table` de `@manto/ui` (Postagem · Responsável · Plataforma · Status ·
  Prazo · Publicação · Revisão · Ações), ótima para varrer datas de publicação; o badge de revisão
  é link direto para `/revisao/:id`.
- **Estados**: `Skeleton` no carregamento, alerta em pt-BR no erro e vazio explicando que o card
  nasce na primeira coluna.
- **API**: `GET /api/marketing/posts` · `POST /api/marketing/posts` ·
  `PATCH|DELETE /api/marketing/posts/<id>` · `GET /api/marketing/opcoes`.

#### `/marketing/painel` → **Card de Postagem** *(Dialog de edição)*
- **Vínculo com o catálogo**: o Tema é escolhido no **`Combobox` de `@manto/ui`** com
  `AvatarThumb` **quadrada** da capa (Princípio X.1/X.2) — seleção visual, não por nome digitado.
  O responsável usa o mesmo `Combobox`, com avatar **circular** (pessoa).
- `Status` e `Plataforma` são `<select>` nativos legítimos (5 e 7 opções — abaixo do limite de 10
  do Princípio X.1); as plataformas vêm do servidor (`MARKETING_PLATFORMS`).
- **Botão do Google Drive**: com `drive_folder_url` preenchido, aparece um botão visualmente
  distinto (contorno/fundo dourados + ícone de pasta) — **"Abrir Acervo de Mídia no Drive"** —
  com `target="_blank"` e `rel="noreferrer noopener"`. O servidor só aceita `http(s)`.
- **Ponte com a Revisão**: sem espaço vinculado, o botão **"Criar Espaço de Revisão"** cria o
  espaço com o título do post em um clique; com espaço, o bloco vira um botão grande
  **"Ir para Revisão →"** (`/revisao/:id`) mais a situação (`SEM MATERIAL`/`EM REVISÃO`/
  `PRECISA DE AJUSTES`/`APROVADO`) e a contagem de materiais aprovados.
- **Erro de validação nunca limpa o formulário** (Princípio V): o `fields` do 400 vira mensagem no
  campo exato; a limpeza só acontece no sucesso (remount por `key`).
- **Exclusão** com confirmação em duas etapas **dentro do próprio Dialog** ("Excluir
  definitivamente"), sem `window.confirm` e sem Dialog aninhado.
- O Dialog lê o post **do cache do TanStack Query** (não de uma cópia em estado): criar o espaço
  de revisão altera o post pela API, e uma cópia congelada seguiria oferecendo "Criar Espaço de
  Revisão" depois de o espaço já existir.
- **API**: `POST /api/marketing/posts/<id>/create-review` · `PATCH|DELETE /api/marketing/posts/<id>`.

#### `/marketing/metas` — Metas de Frequência (*Health Dashboard*)
- **Acesso**: `MARKETING`, `SUPERADMIN` (gate de servidor em `GET /api/marketing/goals`).
- **Objetivo**: responder de relance **qual assunto está pedindo post agora**, a partir das regras
  combinadas em reunião (ex.: "Festa de 15 Anos a cada 15 dias").
- **UX**:
  - Faixa de resumo no topo: 🚨 "N assunto(s) precisando de post" (vermelho) ou ✅ "Todos os
    assuntos em dia" (verde), com "X em dia · Y meta(s) acompanhada(s)".
  - Um card por meta, **ordenados por urgência** (sem posts → mais atrasados → em dia): miniatura
    quadrada do Tema (ou ícone de alvo quando a meta não tem Tema), intervalo alvo, selo
    `SEM POSTS`/`ATRASADO Xd`/`EM DIA` **com ícone** (nada depende só da cor), frase de urgência,
    barra de consumo do intervalo, "Último post" e "Próximo previsto".
  - CRUD da meta em `Dialog`: nome, intervalo em dias (com atalhos 7/15/30) e `Combobox` de Tema —
    com Tema o casamento com os posts é exato, sem Tema cai no casamento pelo nome no título.
  - Exclusão com confirmação em duas etapas dentro do card.
  - Entrada dos cards e reordenação com Framer Motion (`layout` + `AnimatePresence`), respeitando
    `useReducedMotion()`.
- **Regra de negócio visível na tela**: o status é derivado no servidor a partir dos posts
  publicados — mover um card do Kanban para "Publicado" conserta a saúde da meta na hora (e um post
  publicado sem data ganha a data de hoje automaticamente).
- **API**: `GET|POST /api/marketing/goals` · `PATCH|DELETE /api/marketing/goals/<id>` ·
  `GET /api/marketing/opcoes`.
- **Vínculos**: Meta → Tema do catálogo (`CatalogItem`) → postagens publicadas (`MarketingPost`).

---

### A.5 Comercial

#### `/vendas` — Dashboard Comercial *(pivot na feature 196; era "Pipeline de Vendas")*
- **Acesso**: `COMERCIAL`, `FINANCEIRO`, `SUPERADMIN` ou responsável EducaManto
  (`_can_view_vendas()`).
- **Objetivo**: é a tela de metas e performance de quem vende. O papel `COMERCIAL` **não** acessa
  o Painel Financeiro, então esta é a única superfície onde ele acompanha o próprio resultado.
  Até a 195 era uma cópia empobrecida da tabela do Painel Financeiro (venda/custo/lucro/comissão,
  sem período e sem KPI) — redundante para o gestor e pouco útil para o vendedor.
- **Duas personalidades, decididas no servidor** (`can_filter_seller` / `scope_label`):
  - **Vendedor comum** → "Minhas vendas": KPIs e tabela só com as vendas dele, **sem** filtro de
    vendedor. Passar `seller_id` na URL não muda nada (o servidor ignora). O responsável
    EducaManto sem papel comercial cai aqui, restrito aos eventos `(EDU…`.
  - **Financeiro/Superadmin** → "Empresa toda": KPIs consolidados, coluna **Vendedor** na tabela e
    `<select>` "Todos os vendedores".
- **Filtros de período** (topo, botões): **Mês atual** · **Mês anterior** · **Últimos 30 dias** —
  resolvidos por `_resolve_period()`, o mesmo helper do Painel Financeiro. A faixa de datas
  resolvida aparece ao lado ("01/06/2026 a 30/06/2026").
- **4 cards de KPI** (grid 1/2/4 colunas), na estética do Painel Financeiro:
  1. **Total vendido** (R$) — subtítulo mostra o desconto concedido no período, quando houver.
  2. **Ticket médio** (R$) — total ÷ eventos fechados.
  3. **Eventos fechados** (quantidade).
  4. **Comissão prevista** (R$) — **destacado em verde sutil** (borda + fundo `green-soft`) para
     incentivar o comercial. Para gestor é a comissão projetada da equipe; para o vendedor, a
     projeção sobre as vendas dele.
- **Tabela de acompanhamento (funil fechado)**, componentes `Table`/`TableRow`/`TableCell` de
  `@manto/ui`. Colunas: **Data do evento** · **Cliente** (contratante do `EventClient`, com
  fallback para o cliente denormalizado) · **Evento** (título ou rótulo do grupo, com badge
  `GRUPO`/`PERMUTA` e a data em que a venda foi fechada) · **Valor da venda** (com o preço de
  tabela riscado quando houve desconto) · **Vendedor** (só gestor) · **Contrato**
  (`Badge` — Assinado/Pendente/Sem contrato) · **Cobrança** (`Badge` — Pago total/Parcial/
  Pendente/Permuta) · **Ações** ("Ver evento" → `/events/:id`).
  Rola dentro do próprio contêiner no mobile — o corpo da página nunca rola na horizontal.
- **Nota de negócio**: as colunas de **Custo** e **Lucro líquido** saíram desta tela e **não
  existem no payload** — são informação do setor financeiro. O foco aqui é a relação comercial.
- **O que conta como venda fechada** (`vendas_ops.list_closed_sales`): evento com `sale_value > 0`
  ou marcado como cortesia/permuta; recortado pela **data de fechamento** (`sale_date`, ou a data
  do evento quando ninguém preencheu `sale_date` — sem esse resgate some receita real do
  relatório); satélites de grupo comercial ficam de fora (o principal carrega o valor do grupo).
  Evento de agenda ainda sem valor **não** aparece — quem cobra esse preenchimento é a auditoria
  do Painel Financeiro. Permutas entram na lista com badge, mas **não** somam nos KPIs (mesma
  régua de `eventos_com_venda` do Painel Financeiro).
- **Estados**: `Skeleton` de 4 cards + tabela no carregamento; alerta em pt-BR no erro; vazio com
  "Nenhuma venda fechada neste período. Troque o filtro acima para ver outro mês.". Troca de
  período/vendedor faz o bloco reanimar com Framer Motion (220ms, respeitando
  `useReducedMotion()`).
- **API**: `GET /api/vendas/pipeline?period=&seller_id=`.
- **Vínculos**: `/events/:id` (ação de linha), `/financeiro/comissoes` (a comissão prevista aqui é
  a mesma base que vira `CommissionPayment` lá) e `/financeiro` (Painel Financeiro — custo, lucro
  e auditoria de eventos sem valor).

#### `/clientes` · `/clientes/:id` — Clientes
- **Acesso**: `COMERCIAL`, `FINANCEIRO`, `SUPERADMIN` (`_require_vendas()`).
- **UX**: busca, criação rápida (dedupe por telefone), edição, exclusão, histórico de eventos.

#### `/clientes/avaliacoes` — Satisfação das Clientes *(refeita na feature 197)*
- **Acesso**: `COMERCIAL`, `FINANCEIRO`, `SUPERADMIN` (`_require_vendas()`).
- **Objetivo**: painel de satisfação — onde se mede a qualidade percebida do serviço. A origem do
  dado é o link público `/avaliar/<token>`, gerado sob demanda a partir do evento (token aleatório
  de 43 chars, nunca o id sequencial).
- **UX**:
  - **3 cards de KPI** (calculados no servidor, sempre sobre o recorte filtrado): **Nota Média
    Geral** (`4.1 / 5.0` + estrelas), **Total de Avaliações** (com "N clientes avaliadas") e
    **Índice de Excelência** (% de notas 5).
  - **Distribuição por nota** — barras de 5 a 1 estrela com a contagem.
  - **Filtros**: busca textual (nome da cliente **ou** título do evento, sem acento), faixa de
    nota (Todas · 5 · 4 · **3 ou menos (atenção)**), ordenação (Mais recentes · Maior nota · Menor
    nota), período e tag. Busca, faixa de nota e ordenação rodam **no cliente** (a faixa "3 ou
    menos" não cabe no parâmetro `score` do servidor, que só aceita nota exata); **período e tag
    vão ao servidor**. Contador "X de Y avaliação(ões)" e "Limpar filtros".
  - **Grade de cards** (1 coluna no mobile → 2 → 3): estrelas somente-leitura (`StarRating` de
    `@manto/ui`) + badge da nota, **nome da cliente em destaque**, título do evento com **link para
    `/events/:id`** e a data do evento, **comentário** em `blockquote` e as tags marcadas.
  - **Empty state** com ícone, distinguindo "nenhuma avaliação ainda" de "os filtros não acharam
    nada".
- **Vínculos**: cada card leva ao evento (`/events/:id`); a tela é acessada por `/clientes`.
- **API**: `GET /api/clientes/avaliacoes?period=&from=&to=&score=&tag=&client_id=`.

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

#### `/financeiro/pagamentos` — Planilha de Pagamentos *(paridade restaurada na feature 189; visualização e filtro por faixa na feature 194)*
- **Acesso**: `FINANCEIRO`, `SUPERADMIN`.
- **UX**: itens de cachê, salário, gasto, BV, comissão e contas recorrentes em uma planilha
  única, na ordem de colunas clássica — **checkbox** (com "selecionar tudo") · **vencimento** ·
  **descrição detalhada** (badge do tipo + descrição do item, com botão de cópia) · **favorecido**
  em negrito · **valor** em BRL (com cópia do valor cru `1234,56`) · **chave PIX** com o tipo
  (CPF/CNPJ/E-mail/Telefone/Aleatória) e botão de cópia · **situação**. Os botões de cópia dão
  feedback "✓" temporário e anunciam por `aria-live`; adiantamentos de salário (N por pagamento,
  com comprovante) no próprio valor; **export CSV**. Trocar o mês limpa filtro e seleção.
- **As 4 faixas (fonte única de cor e de filtro)**: **Pago** · **No banco** · **Pendente**
  (`nao_pago` já vencido) · **Futuro** (`nao_pago` a vencer). A tela deriva "pendente"/"futuro"
  do campo `is_future` que a API já manda — a mesma regra com que o backend soma os totais —, e
  não de uma comparação de datas própria, então filtro e KPI nunca divergem.
- **Cards de KPI = filtro rápido da tabela** *(feature 194)*: os 5 cards do topo (Total no
  período · Pagos · No banco · Pendentes · Futuro) são botões (`aria-pressed`) que filtram as
  linhas no cliente. Clicar em "Total no período" — ou reclicar o card já ativo — limpa o filtro.
  Cada card mostra o valor em BRL, a **contagem de itens** da faixa e "· filtro ativo" quando
  ligado. O card ativo recebe borda de 2px na cor do status + `ring` + fundo colorido e sombra;
  os inativos ficam esmaecidos (`opacity-60` + dessaturação, restaurados no hover). O estado do
  filtro é anunciado por `aria-live` ("Filtro X ativo: N de M itens"), aparece no título da
  tabela ("Itens do mês (N de M)") e tem um botão "Limpar filtro"; faixa vazia mostra estado
  vazio com atalho "Ver todos os N itens".
- **Colorização da tabela** *(feature 194)*: cada linha tem uma nuance de fundo pela sua faixa —
  verde (pago), azul (no banco), rosa/vermelho (pendente), dourado (futuro, cor `gold` do
  `@manto/ui`; **`amber` não é usado no sistema**). Descrição, favorecido e valor ficam em
  `font-bold text-ink` para manter o contraste sobre os quatro fundos. O seletor de situação e o
  badge "⏳ Futuro" usam a mesma paleta, então a cor do card clicado é a cor das linhas reveladas.
- **Situação**: seletor por linha com as opções que o backend suporta — **Não pago · No banco ·
  Pago** — as 3 valem para todos os tipos, inclusive comissão e conta recorrente (feature 199).
- **Ações em lote** *(barra no topo da tabela, feature 194)*: aparece com 1+ itens marcados
  (animação `AnimatePresence`, respeitando `useReducedMotion`) e some ao voltar a 0. Mostra
  **`"X selecionados • R$ Y.YYY,YY"`** — a soma dos itens marcados, calculada no estado do React
  e formatada por `formatBRL` de `@manto/money`. Ações: **Marcar pago · No banco · Não pago ·
  Excluir** (com confirmação) · **Limpar seleção**. Cada botão tem **spinner individual** — só a
  ação em voo gira (lida de `mutation.variables`), as outras ficam desabilitadas até a resposta,
  impedindo dois lotes concorrentes (Princípio V). "Selecionar tudo" opera sobre as linhas
  **visíveis**: com filtro ligado, marca só aquela faixa sem mexer no resto da seleção; a linha
  marcada ganha barra lateral roxa.
- **API**: `GET /api/financeiro/pagamentos` · `POST .../set-status`, `.../bulk-action`,
  `.../salary/<id>/advance` · `GET .../export`. A feature 194 não criou nem alterou endpoint —
  é toda de apresentação sobre o payload existente.

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
| `/orcamento` | Calculadora de Orçamento | `COMERCIAL`, `SUPERADMIN` | layout clássico de duas colunas assimétrico (1/3 dados do evento + segurança de agenda, 2/3 equipe/ajustes/resultado); **cálculo 100% reativo** — sem botão "Calcular", qualquer alteração recalcula (debounce ~400ms); alerta "Já na agenda neste dia" abaixo da Data (evita venda em dobro de personagem); painel "Personalizar valores" (valor final ou multiplicador, por duração); contador de itens no link "Histórico de Orçamentos"; campo **Local/Endereço do evento** com **`GoogleAddressInput`** e botão **"Calcular km (Maps)"** ao lado de *Km (ida)*, que preenche a distância pela Distance Matrix (feature 195 — antes o KM aqui era 100% manual); escolher uma sugestão do Google com "Fora de SP" ligado já dispara o cálculo. Salvar no histórico, "Ver memória de cálculo"; lê `?recalcular_id=` para reabrir um orçamento salvo com os campos preenchidos (feature 191, sobre a base da feature 190) |
| `/orcamento/historico` | Orçamentos | `COMERCIAL`, `SUPERADMIN` | tabela densa com filtros avançados (data, valor, vendedor, tipo), PDF, envio por e-mail, exclusão; **Criar evento** (`/events/new?orcamento_id=`) e **Recalcular** (`/orcamento?recalcular_id=`), feature 190 |
| `/orcamento/configuracoes` | Config. Preços | `SUPERADMIN` | `SiteSetting.pricing_config` + personagens especiais, em tabelas densas (feature 190) |
| `/educamanto` | Calculadora EducaManto | `COMERCIAL`, `SUPERADMIN`, `ENSAIO`, `REVENDEDOR_EDUCAMANTO` | seletor de pacote em dropdown, duas colunas, cards Sem/Com Nota Fiscal, transporte com **`GoogleAddressInput`** no endereço (feature 195 — escolher a sugestão já recalcula o KM), cálculo; lê `?package_id=` (vindo de "Usar" na tela de Pacotes) e `?recalcular_id=` (feature 190) |
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
             ├──► Presente 3D (Event3DGift.item_id → Acervo3DItem)  [só event_type='SHOW']
             └──► Feedback da cliente (feedback_token → ClientFeedback)

   Formulário de pré-contrato (FormResponse.event_id)
             └──► Fila de Impressão 3D: idade e nº de aniversariantes lidos direto das
                  respostas da cliente, cruzados com os Personagens contratados

   Catálogo (Tema) ──── MarketingPost.catalog_item_id ────► Postagem de Marketing
             │                                                    │ 1:1
             │                                                    ├──► Espaço de Revisão
             │                                                    │    (review_space_id)
             │                                                    └──► Responsável (users)
             └──── MarketingFrequencyGoal.catalog_item_id ────► Meta de Frequência
                       (saúde derivada dos posts publicados do mesmo Tema)
```

Pontos de atenção recorrentes:
1. **Ficha ↔ Personagem é 1:1 por vez** — vincular a partir da Ficha substitui o vínculo antigo.
2. **A busca de elenco só oferece Personagens filhos**, nunca Temas pai (um Tema não é atração
   vendável isoladamente).
3. **`EventRole.character_name` é texto livre** — daí existir o alerta de "personagem sem ficha"
   em `/figurinos` e o fluxo de associação/dispensa.
4. **Presente 3D é exclusivo de evento `SHOW`** — a API recusa o vínculo em qualquer outro tipo,
   e a seção nem aparece na tela do evento (feature 200).
5. **Postagem ↔ Espaço de Revisão é 1:1** (`marketing_posts.review_space_id` é UNIQUE) — a segunda
   tentativa de criar o espaço devolve 400. Excluir a postagem **não** apaga o espaço: materiais e
   comentários da revisão têm vida própria (feature 204).
6. **A meta de frequência não tem estado próprio** — `on_track`/`delayed` é calculado na leitura a
   partir dos posts publicados. Sem `publish_date` o post não conta, daí a data automática ao mover
   o card para "Publicado" (feature 204).
