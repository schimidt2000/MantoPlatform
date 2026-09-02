# 02 — Mapa de Páginas e UX

> **Documento vivo.** Atualizado obrigatoriamente ao fim de cada feature (ver regra em
> `CLAUDE.md` → "REGRA OBRIGATÓRIA DE DOCUMENTAÇÃO VIVA").
>
> **Não comece por aqui.** O documento de entrada é `docs/00_MAPA_DO_SISTEMA.md`. Este 02 é a
> referência **por tela** — consulte a entrada da tela que você vai mexer, não o documento inteiro.
>
> Última atualização: **2026-09-02** · Em branch: **272-notificacoes-internas** (sino de notificações
> no shell + `/notificacoes`). Antes: **270-miniaturas-catalogo** (variantes de miniatura na vitrine e no
> Banco de Talentos). Antes: **239-backlog-agosto** (rodada de 11 itens do
> backlog — ver `specs/239-backlog-agosto/`)
>
> UX nova da 239: **Catálogo** subiu para a **1ª seção do menu** (logo após Agenda), visível a
> **todos os papéis** (inclusive `REVENDEDOR_EDUCAMANTO` — o catálogo já é público, sem login); o
> item de gestão "Gerenciar catálogo" não mudou de lugar. `CastingSection` do detalhe do evento
> ganhou o **carrinho de transporte** (botão "🚗 Marcar transporte"/"🚗 Leva o carro" por papel,
> só em evento fora de SP; badge dourada "🚗 Transporte"; linha de teto + explicação da conta,
> **visível só a superadmin**, com a parcela do veículo somada quando marcado) e os **badges de
> maquiador** ("Falta maquiador" dourado/"Maquiador fechado" verde no cabeçalho da seção, 💄 ao
> lado de cada personagem com `needs_makeup`); a vaga "Técnico de Som (Presença)" virou um card
> **somente leitura** (sem cachê, sem convite, sem botão de pagamento — designação continua no
> painel de Ensaio). A aba **Comercial** ganhou o link **"Orçamento de origem"** (só quando o
> usuário consegue de fato abrir aquele orçamento). `EnsaioSection` esconde o botão **"+ Agendar
> ensaio"** quando o evento não pede ensaio e não tem nenhum já agendado (evita contradizer o
> aviso "Este evento não pede ensaio."). O diálogo de **novo pedido de produção/compra** ganhou
> `max-h-[85vh] overflow-y-auto` — parava de caber na tela em formulário longo. A **calculadora do
> EducaManto** reposicionou o card "Contratação Manto" para logo após "Dias e ensemble" (ninguém
> achava no fim da coluna), a aba marca **"· + Manto"** quando a contratação está ativa, ganhou um
> **banner** sob os cards "Sem Nota Fiscal"/"Com Nota Fiscal" avisando que esses dois valores não
> incluem a contratação Manto, **`InfoTip`** real nos ⓘ (componente novo em `@manto/ui` — hover,
> clique, toque e teclado; o `title` nativo antigo não respondia a toque nem teclado), e passou a
> desabilitar "Gerar orçamento" com aviso inline quando a contratação está ativa e nenhuma duração
> foi marcada. O **Dashboard** incluiu o link do portal na mensagem de cobrança pronta do WhatsApp,
> e a edição de evento (aba Resumo e formulário completo) ganhou um card de **avisos não-bloqueantes**
> quando a troca de tipo do evento remove ensaio/vagas automaticamente (decisão 7 da rodada).
>
> Última atualização: **2026-08-11** · Estado do repositório: pós-feature **235 (aba Personagens no
> gerenciador de catálogo)**
>
> UX nova da 235: `/admin/catalogo` ganhou uma **terceira visão, 🎭 Personagens** — uma linha por
> personagem (não por tema), com a ficha vinculada, em quantos temas ele aparece e quantos
> figurinos iguais existem. É por ali, ou pelo bloco "Reaproveitar personagem que já existe" dentro
> do tema, que o **mesmo** personagem entra em outro tema sem ser recadastrado. A ficha de figurino
> ganhou o campo **"Figurinos iguais que temos"**.
>
> UX da 234: a galeria de `/admin/catalogo/:id/editar` virou **uma grade só** (fotos salvas e
> novas juntas), **a primeira foto é a capa** (o campo de capa separado deixou de existir), o
> arraste passou a ser por ponteiro — funciona no toque e reorganiza as vizinhas ao vivo — e a
> remoção fica pendente com desfazer. E, o principal: **reordenar e salvar agora muda de verdade**
> (a ordem era aceita pela API e descartada no banco).
>
> UX da 233: quem é **pré-escalado na criação ou edição do evento** passa a receber o convite
> na hora — antes o cargo nascia com pessoa e sem convite, e nenhuma tela pedia o clique em
> "Convidar". E a ficha de figurino do portal deixou de recusar quem está escalado sem convite
> enviado: desde a 230 o evento aparecia na agenda com o link, e o link caía em 403.
>
> UX nova da 232: na avaliação do portal, **detalhar voltou a ser o caminho padrão**. O botão
> principal virou "Enviar e avaliar em detalhes →" e **rola até o bloco das partes**; "Só enviar a
> nota geral" é o desvio. Voltaram os rótulos com emoji, o cabeçalho "Avaliação detalhada", o
> "Enviar avaliação completa ✓" e o "Pular — já enviei o suficiente" — e a categoria `texto`
> recuperou o nome e a explicação que tinha no Jinja ("🎭 Show no geral — coreografia,
> posicionamento, texto e interações"), em vez de "Texto / roteiro".
>
> UX nova da 231: a **home ganhou o painel "🙋 Confirmações pendentes"** (Casting/Superadmin), com
> quem ainda não confirmou presença nos eventos de hoje em diante. Cada linha traz a ação certa:
> **"Cobrar no WhatsApp"** com a mensagem pronta para quem recebeu o convite e não respondeu, e
> **"Enviar convite"** para quem nunca recebeu. Em paralelo, um lembrete automático por e-mail
> cobra só quem já foi convidado, só na semana do evento, no máximo 2 vezes por convite e **1
> e-mail por pessoa por dia** (todos os eventos dela na mesma mensagem).
>
> UX nova da 230: **"Próximos eventos" e "Histórico" do portal passaram a listar toda escalação não
> recusada** — aceita, pendente ou **sem convite enviado**. Antes exigiam aceite, e por isso
> escondiam do artista evento que ele ia fazer (26 cargos futuros invisíveis) ou que já tinha feito e
> recebido (97 passados, R$ 36.910). Agora os totais de cachê do portal batem com a Planilha de
> Pagamentos, que sempre pagou por cargo atribuído. Convites continua listando só o que precisa de
> resposta, e o card futuro com convite pendente ganhou a linha "Falta responder este convite ›".
>
> UX nova da 229: o link **"Avaliar este evento"** passou a aparecer também nos itens do histórico
> **dentro da Agenda** — antes só existia na aba Histórico, e como as duas listas se chamam
> "Histórico", quem estava na Agenda concluía que não havia como avaliar (relato de artista em
> 10/08). O componente virou `components/RatingLink.tsx`, que lê a mesma query do crachá da aba,
> então botão e contador nunca discordam.
>
> UX nova da 228: `ConfirmDialog` saiu de dentro de `GastosRecorrentesPage` e virou componente do
> `@manto/ui`. A **exclusão em lote de pagamentos** deixou de usar o alerta nativo do navegador e
> passa pelo diálogo, mostrando quantos itens, **quanto em reais** e quantos estão fora da tela por
> causa do filtro/busca. Sobram 37 `window.confirm` no repositório — inventariados em
> `05_DIVIDA_TECNICA.md` §7.4, para trocar por tela.
>
> UX nova da 227: **a foto de perfil voltou a aparecer no Portal do Artista** — ela era pedida em
> `/uploads/…`, rota de staff, e 255 dos 259 talentos viam o ícone de imagem quebrada. E o
> **coordenador** do evento passou a ver as fichas de figurino do elenco inteiro (antes via a
> mensagem "ainda não há ficha", porque o cargo dele não tem personagem); o link na agenda agora
> só aparece quando existe ficha do outro lado.
>
> UX nova da 226: **`/financeiro/pagamentos` deixou de ser tabela-única.** Abaixo de `xl` os itens
> viram cartões empilhados (a tabela de 1040px só cabe a partir de 1280px, porque a sidebar come
> 256px), a **caixa de busca** que existia na planilha Jinja voltou — agora varrendo o dado, não o
> DOM —, os adiantamentos de salário saíram do `<details>` da célula para uma **janela sobreposta**,
> e a barra de ações em lote virou rodapé fixo no celular. Nenhum endpoint mudou.
>
> UX nova da 219: **`/talents` ganhou uma terceira aba — "Emails com problema"**, com contador, ao
> lado de Ativos e Pendentes (só `CASTING`/`SUPERADMIN`). Lista quem não está recebendo nossos
> emails, separando "caixa cheia" (avisar no WhatsApp, com mensagem já pronta no link) de "endereço
> errado" (pegar o email certo). "Resolver" fecha o endereço inteiro; corrigir o email na ficha
> também tira da fila. No cadastro público, a tela de sucesso passou a mostrar o email enviado e
> permite **corrigir só ele e reenviar** — o cadastro já está gravado nesse ponto, nada se perde —,
> e `/cadastro/confirmar/:token` é o destino do link de confirmação.
>
> UX nova da 218: onze telas de administração saíram de coluna única estreita
> (`max-w-lg`…`max-w-3xl`) para largura de desktop com blocos lado a lado — ficha e criação de
> usuário, configurações, logs (viraram tabela), desempenho, clientes e ficha do cliente, revisão e
> espaço de revisão, catálogo admin e seu formulário, ficha de figurino, configuração de preços.
> Todo grid novo leva **`[&>*]:min-w-0`**: item de grid nasce com `min-width:auto` e sem isso o
> `overflow-x-auto` das tabelas para de agir e a página estoura no celular.
>

> UX nova da 215: **`/events/:id` foi reformulada** — quatro abas (Resumo · Produção · Comercial ·
> Histórico) com a aba na URL (`?aba=`), faixa de pendências clicável no Resumo, e **edição inline
> por bloco** (o formulário `/events/:id/edit` virou item do menu Ferramentas, não mais o caminho
> obrigatório). As buscas de **talento** e **ficha de figurino** da tela ganharam foto/miniatura e
> filtro em tempo real, e a de talento mostra **quem está ocupado antes de escalar**.
>
> UX do hotfix 210: `/events/:id/edit` voltou a abrir com o horário e a descrição reais do evento
> (abria +3h e com a descrição em branco, e salvava assim); a fase de anexos de `/events/new` passa
> o id do evento recém-criado (todo comprovante falhava); "Ver memória de cálculo" mostra o
> detalhamento linha a linha em vez da mensagem de WhatsApp; **`/orcamento/:id` é nova** — é para
> onde "Gerar Orçamento" leva agora.
>
> UX novas da 207: `/agenda` ganhou campo único de busca (evento/cliente/telefone, param `q`,
> resultados Próximos/Anteriores no lugar das visões enquanto há termo); detalhe do evento
> ganhou botão "Imprimir fichas" (1 folha por ESCALAÇÃO — personagem × quem veste, pois a folha
> imprime nome e medidas do talento; hotfix fichas-por-escalacao) e exclusão de feedback p/ SUPERADMIN;
> `/admin/catalogo/:id` ganhou editor rich-text na descrição e drag de foto da galeria →
> personagem; `/avaliar/<token>` mostra CTA do Google Review após nota 5; a seção "Log de
> atividades" do evento agora só existe para SUPERADMIN (o servidor omite a chave).

Legenda de acesso — os papéis listados são os do gate **de servidor**; a navegação lateral
(`frontend/apps/internal/src/lib/navigation.tsx`) apenas espelha isso na UI.
`REVENDEDOR_EDUCAMANTO` puro (papel único) vê **somente** Agenda e EducaManto — e **entra direto
na Agenda** (feature 214): a Home não é do perfil dele, então `/` redireciona, tanto no login
quanto ao chegar por favorito. No servidor, o guard do perfil devolve **403 JSON** para a API fora
do perfil, nunca redirect (ver `docs/01`).

---

**`Dialog` do design system (`@manto/ui`, corrigido na 212).** O painel é centralizado por **flex**
num container `fixed inset-0 overflow-y-auto`, nunca por `translate` de utilitário: o painel é um
`motion.div` e o Framer Motion escreve `transform` inline, que vencia as classes de centralização —
o diálogo abria com o canto superior esquerdo no meio da tela e metade dele para fora, em 11 telas.
Diálogo mais alto que a janela faz o **container rolar**. Regra geral: não centralize com
`translate` um elemento cujo `transform` é animado.

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
- Navegação lateral por seções: *(sem rótulo)* Home/Agenda/**Catálogo**/Gastos Extras ·
  **Casting** · **Produção** · **Comercial** · **Financeiro** · **Ferramentas** · **Sistema**.
- Seções sem itens visíveis desaparecem inteiras.
- Menu do usuário exibe os papéis; superadmin real tem o seletor **"Ver como"** (impersonação de
  `CASTING`/`FIGURINO`/`COMERCIAL`/`FINANCEIRO`/`ENSAIO`) — com impersonação ativa, o shell passa
  a contar **apenas** o papel simulado.
- Link **"Catálogo"** é `external: true` → abre `/catalogo/` (vitrine pública) em outra aba.
  **Feature 239**: saiu da seção Comercial (onde vivia ao lado de "Gerenciar catálogo") e subiu
  para a 1ª seção do menu, logo após Agenda, com `isVisible: everyone` — visível a **todos os
  papéis internos, inclusive `REVENDEDOR_EDUCAMANTO`** (o catálogo já é público, sem exigir
  login; não fazia sentido escondê-lo de quem só vê Agenda e EducaManto). "Gerenciar catálogo"
  não mudou de lugar (`admin-catalogo`, continua restrito a Comercial/Financeiro/Superadmin).
- **Sino de notificações (feature 272)** — slot `headerActions` do `AppLayout`, renderizado na
  **linha da marca da sidebar** (desktop) e à direita da **barra superior do mobile, fora do
  drawer**. Badge com a contagem de não lidas (`9+` acima de 9; polling de 60 s só da contagem,
  pausado em aba oculta, refeito ao voltar o foco). Clique abre um popover (para a direita da
  sidebar no desktop; sob a barra no mobile): últimas 20 agrupadas por dia, ícone por `kind`
  (formulário, estrela, recusa), vermelho quando `urgent`, "Marcar todas como lidas" (com teto
  `ate_id`) e "Ver todas". Clicar num item marca lida (otimista) e navega para `link_path`.
  Fecha em Esc e clique fora; foco volta ao sino; `aria-live` só quando a contagem sobe. O
  revendedor EducaManto não vê o sino. Sem toast, sem som.

#### `/notificacoes` — Notificações *(feature 272)*
- **Acesso**: qualquer usuário interno (a caixa é do próprio usuário); **sem item de menu** — a
  entrada é o "Ver todas" do sino (exceção registrada em `docs/04` §8).
- **UX**: `PageHeader` com "Marcar todas como lidas"; abas **Não lidas (n)** / **Todas**; mesma
  `NotificacaoItem` do popover, agrupada por dia; "Carregar mais" por cursor (`next_before`); na
  aba "Não lidas" a linha sai da lista ao ser lida (200 ms, respeita `prefers-reduced-motion`).
- **API**: `GET /api/notificacoes` · `POST /api/notificacoes/<id>/lida` · `POST /api/notificacoes/lidas`.

---

### A.2 Home e Agenda

#### `/` — Dashboard
- **Objetivo**: visão do dia/semana com pendências por papel.
- **Acesso**: todos exceto `REVENDEDOR_EDUCAMANTO` puro.
- **API**: `GET /api/dashboard` (`dashboard_service.py`).
- **Vínculos**: cards levam a Agenda, Casting, Figurino e Financeiro.
- **Feature 266 — painel "📝 Respostas de formulário"**: quatro linhas rótulo→número (festa futura
  sem evento *em vermelho quando > 0*, sem evento, sem cliente, ambíguo) + botão "Abrir formulários".
  Mesmo gate do painel Comercial, e **respeita "Ver como"** (o bloco vem `null` do servidor e a
  seção some). Os números são os mesmos cartões de `/formularios` — vêm do mesmo `count_status()`.
  ⚠️ Contam o que **não foi tratado**, não o que é "novo": não existe noção de lido no modelo.
  As mutações de `/formularios` invalidam `["dashboard"]`, senão o número ficaria velho na tela
  (`staleTime` de 30s + `refetchOnWindowFocus: false`).
- **Desde a 206 é a única `/` da plataforma.** O dashboard Jinja foi aposentado: a raiz do Flask
  responde 301 para `https://app.mantoproducoes.com.br`. Painéis atuais: Casting, Figurino,
  Comercial (cobranças), Contas recorrentes, Performance e Cargos dispensados — **menos** blocos
  do que a home Jinja tinha (ver o aviso em `01_SISTEMA_E_BANCO.md` §3.16). Lista incompleta desde
  a feature 231 (o painel "🙋 Confirmações pendentes" não está listada acima — ver nota da 231 no
  cabeçalho deste documento).
- **Feature 239**: a mensagem pronta de **"Cobrar no WhatsApp"** (painel "Confirmações
  pendentes", feature 231) passou a incluir a URL raiz do Portal do Artista no texto —
  `GET /api/dashboard` manda `portal_url` (mesma fonte usada nos e-mails automáticos); com a env
  `PORTAL_URL` ausente, `portal_url` vem `null` e o link é omitido em vez de sair quebrado.
- **Redesign 2026-08-20 (triagem por cards)**: a home deixou de ser uma pilha de listas abertas.
  UX atual: (1) **visão geral no topo** (`HomeOverview.tsx`) — um card compacto por setor com
  contagem de pendências, selo vermelho de urgentes e contexto extra (R$ em aberto no Comercial,
  "N sem convite enviado" nas Confirmações); tocar no card abre e rola até o painel
  (`scroll-mt` compensa o topbar sticky do mobile); (2) linha-resumo "N pendências no total ·
  N urgentes"; (3) **painel nasce aberto só se tem item urgente** (escolha manual da pessoa
  prevalece depois); (4) **listas truncadas em 6 linhas** (`ListaTruncada`) com "Mostrar todas as
  N" — as consultas já vêm ordenadas por data, então o topo é o mais próximo de acontecer;
  (5) desktop = grade de 2 colunas de painéis (mobile continua 1 coluna); (6) o painel Casting
  ganhou o subgrupo **"Convites recusados"** — `rejected_invites` já vinha da API (231) e era
  descartado pela tela; recusa cujo cargo já voltou para `pending` não conta duas vezes.
  `SectorPanel` agora aceita modo controlado (`open`/`onOpenChange`) e `urgentCount`.
  Sem mudança de backend: tudo deriva do `GET /api/dashboard` existente.
- **Painel "📈 Performance" (2026-08-20, `HomePerformance.tsx`)**: voltou à Home depois da
  migração (a API já calculava; a tela não desenhava). **Somente leitura e só para o superadmin
  real** — o gate é do servidor: `GET /api/dashboard` devolve `performance: null` para quem não
  é SA e durante o "Ver como", e aí o card some. Seletor segmentado 7 dias / 30 dias /
  Personalizado (datas + Aplicar; período inválido mantém o card com instrução em vez de sumir).
  Três métricas: **Casting escalado** (cargos com talento ÷ total, barra verde ≥ 90 %, dourada
  ≥ 70 %, vermelha abaixo), **Figurino pronto** (mesma régua) e **Cachês escalados** (soma de
  `cache_value` dos cargos escalados no período — a vaga de Presença fica de fora, decisão 10 da
  239). O período entra na chave da query (`["dashboard", periodo]`) com `keepPreviousData`, para
  a troca não piscar a visão geral. Rótulo "Cachês escalados" é deliberado: o campo `money_total`
  é custo de cachê comprometido, não receita.

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
     Máscara BRL sempre via `@manto/money`. **"Data da venda" nasce preenchida com hoje**
     (hotfix 267b): o formulário clássico prefilhava e o React não — 44 vendas entraram sem data
     entre 05/08 e 02/09/2026 e sumiram da Planilha de Pagamentos. O servidor também assume hoje
     quando uma venda nova chega sem data (`event_ops.resolver_data_da_venda`); o prefill é para
     a pessoa ver a data que vai valer.
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
- **Layout (feature 215 — substitui o mural de duas colunas da 190)**: **quatro abas**
  (`Tabs` do design system) com a aba ativa na URL (`?aba=resumo|producao|comercial|historico`),
  para deep-link e F5 caírem no mesmo lugar. A régua de abas é **sticky no topo** e rola na
  horizontal no mobile. Uma aba só existe se o payload trouxe algum bloco dela — Comercial e
  Histórico somem para quem o RBAC não serializou. Dentro de cada aba, duas colunas a partir de
  `xl`; abaixo disso, coluna única. **Motivação**: para o `SUPERADMIN`, que recebe todos os
  blocos, a tela da 190 empilhava 16 painéis sem hierarquia (~4000px no desktop, o dobro no
  mobile), e o mesmo personagem aparecia duas vezes (em *Casting* e em *Figurino*).
  - **Cabeçalho** (fora das abas): título, badge de tipo, faixa horária, badge de confirmação e
    o menu **"⋯ Ferramentas"** (`KebabMenu` com `triggerLabel`) — Sincronizar · Exportar elenco
    (modal com seleção de campos e cópia: Personagem, Nome completo, Data de nascimento, CPF, RG,
    Link documento, Top, Bottom, Calçado e Altura — os quatro campos de documento/nascimento só
    chegam no JSON para Casting/Comercial/Superadmin, feature 222) · Editar no Google Agenda ·
    Confirmar dados do evento ·
    Cobrança · Cobrar reembolsos · Marcar evento como confirmado · Pedir feedback da cliente ·
    **Editar tudo (formulário completo)** · **Excluir ou cancelar** (só `SUPERADMIN`) ou
    **Solicitar exclusão** (`COMERCIAL`, com motivo obrigatório) — feature 224. Itens
    indisponíveis ficam desabilitados **com `title` explicando o porquê**.
  - **Banners** acima das abas (feature 224): evento **cancelado** (motivo, autor, data, e o
    aviso de que não conta em métrica nenhuma) e **exclusão solicitada** aguardando decisão,
    esta com os botões "Analisar e decidir" e "Recusar solicitação" para o Superadmin. O
    diálogo de exclusão abre com o resumo de impacto — venda, quanto a cliente já pagou, elenco
    escalado e comissão em jogo — e diz qual das duas ações vai acontecer **antes** de
    confirmar; quando é cancelamento, pede o valor a devolver (pré-preenchido com o recebido),
    nome e PIX de quem recebe.
  - **Aba Resumo**: **faixa de pendências** (chips *Elenco 2/2 escalados*, *Presença*,
    *Figurino n/m com ficha*, *Agenda n com conflito*, *Contrato*, *Recebimento*, *Evento
    confirmado* — verde quando resolvido, dourado quando não; **clicar leva para a aba que
    resolve**) · *Dados do evento* (**editável inline**) · *Resumo para WhatsApp* (descrição do
    Google/Kommo convertida de HTML para texto puro, monoespaçada, com botão copiar) ·
    *Observações*.
  - **Aba Produção**: *Casting* · *Equipe de apoio* (mesmos cards, `role_type="extra"`, inclusive
    o card somente-leitura da vaga de Presença — feature 239) · *Figurino* · *Ensaios* (o botão
    "+ Agendar ensaio" some quando o evento não pede ensaio **e** não tem nenhum já agendado —
    feature 239, evita contradizer o aviso "Este evento não pede ensaio." logo abaixo) ·
    *Logística & trajeto* · *Materiais de ensaio* · *Presente 3D* · *Pedido virtual*.
  - **Navegação para fora (feature 266)**: o nome de cada cliente vira link para `/clientes/:id`
    (texto puro quando não há nome — um link chamado "—" não diz para onde vai); o talento
    escalado leva a `/talents/:id` **pelo avatar e pelo nome, nos dois cards** (o do personagem e
    o de Presença — linkar só um deixaria a mesma pessoa clicável numa lista e morta na de baixo;
    o avatar leva `aria-label` porque o `AvatarThumb` é decorativo); e o pré-contrato ganha link
    para `/formularios?resposta=<id>` **nos dois ramos** — o `DataRow` só aparece sem permissão de
    edição, então quem tem `can_edit_core` (o caso normal do comercial) vê a linha "Ver resposta
    completa" abaixo do `FormResponsePicker`.
  - **Aba Comercial**: *Clientes* (**editável inline**) · *Pré-contrato* (**editável inline**) ·
    *Comercial — dados da venda* (**editável inline**: bruto/desconto/final, transporte, comissão,
    forma de pagamento, parcelas, datas, vendedor, nota fiscal, cortesia/permuta; acréscimos com
    marcação de BV seguem em leitura) · **"Orçamento de origem"** (feature 239, decisão 16 — link
    "Abrir orçamento" para `/orcamento/:id` quando o evento nasceu de um orçamento **e** quem lê
    consegue de fato abri-lo: superadmin, ou o comercial dono daquele orçamento; para os demais
    — ex. FINANCEIRO — o servidor manda `null` e a linha some) · *Resultado* (grade de KPI: venda,
    custo de cachês, gastos extras, comissão e **lucro líquido** em verde/vermelho, + lista dos
    gastos extras aprovados) ·
    *Contrato assinado* · *Notas fiscais* · *Comprovantes de pagamento* (badge "Quitado" quando
    recebido ≥ venda) · *Reembolsos*.
  - **Aba Histórico**: *Avaliações dos artistas* (média + notas individuais com tags por
    critério) · *Feedback da cliente* · *Log de atividades* (accordion) — **este só existe no DOM
    para `SUPERADMIN`**.
  - **Evento de ENSAIO** não usa abas: o servidor não serializa os blocos de show, então a tela
    segue com os poucos painéis que existem, empilhados.
- **Edição inline (feature 215)**: o princípio é **"o que a aba mostra, a aba edita"** — a tela
  `/events/:id/edit` deixou de ser o caminho obrigatório e virou item de menu, para quem quiser
  mexer em elenco, clientes e valores de uma vez. Cada bloco tem seu botão *Editar*, troca a
  leitura por um formulário no lugar e grava por um **endpoint estreito** (ver API abaixo):
  salvar o cabeçalho não toca no elenco, salvar valores não toca nos clientes. Gate: `can_edit_core`
  (`COMERCIAL`/`SUPERADMIN`) — para os demais, o painel fica só em leitura, sem botão.
  **Pegadinha da descrição**: o textarea mostra a versão em texto puro, mas o HTML original só é
  substituído se o usuário realmente digitar no campo — sem isso, o `<br>`/âncoras do Google
  Agenda seriam achatados a cada salvamento.
  **Avisos não-bloqueantes (feature 239, decisão 7)**: quando o cabeçalho salvo troca o tipo do
  evento e a troca envolve sair de SHOW, o servidor devolve `warnings[]` com o que foi removido
  automaticamente (ensaios cancelados, vagas de som removidas). O bloco "Dados do evento" (aba
  Resumo) mostra um `AvisosCard` dourado com esses avisos e um "Fechar"; o formulário completo
  (`/events/:id/edit`) mostra o mesmo card e **segura a navegação automática** pós-salvamento até
  o usuário clicar "Ver evento" — sem isso a troca de tipo apagava ensaio/vaga em silêncio e a
  tela já tinha saído do ar antes de alguém notar.
- **Buscas visuais na tela (feature 215)**: *Casting* e *Figurino* passaram a usar o `Combobox`
  do design system, alinhando-se ao padrão da 195/209.
  - **Talento**: era um `<select>` nativo com ~260 nomes, sem foto e sem indicar quem já estava
    comprometido. Agora é busca em tempo real com **avatar circular** e **selo de agenda na
    própria opção** — `● Ocupado` (vermelho, horários se sobrepõem) ou `● Mesmo dia` (dourado),
    com o evento concorrente na linha de apoio. O aviso passou a existir **antes** de escalar,
    não só depois.
  - **Figurino**: era um `<datalist>`, que no Chrome não renderiza imagem e só vinculava a ficha
    no `blur` — digitar errado não vinculava nada, sem aviso. Agora é busca com **miniatura
    quadrada** da ficha, vínculo no clique e as fichas homônimas do personagem no topo da lista.
- **UX/ações**: escalar talento no cargo (`/roles/<id>/assign`), enviar convite
  (`invite` → `pending`/`accepted`/`rejected`), copiar convite individual / abrir WhatsApp do
  talento, **status de pagamento do cachê** por cargo, marcar/desmarcar figurino separado,
  **vincular ficha de figurino** ao personagem, dispensar/restaurar cargo (só `SUPERADMIN`),
  confirmar evento (`COMERCIAL`/`SUPERADMIN`), editar logística (maquiagem/saída, com estimativa
  de rota do Google Maps), materiais de ensaio (arquivo e link), observações, contratos,
  comprovantes, notas fiscais, reembolsos, sincronizar com o Google, excluir. Cada mutação
  coloca **só o seu próprio controle** em estado de carregamento (Princípio V).
- **Visibilidade financeira (210c)**: "Comprovantes de pagamento" (com *Recebido X de Y* e o selo
  *Quitado ✓*) e "Reembolsos" aparecem para **`COMERCIAL`** também, não só Financeiro — paridade
  com o Jinja. Só os KPIs de lucro/cachês/gastos ficam restritos a `FINANCEIRO`/`SUPERADMIN`.
  Editar valor e excluir comprovante/reembolso continuam só `SUPERADMIN`.
- **Indicador de agenda**: cada card de casting mostra "Mesmo dia"/"Conflito" quando o talento
  tem outro evento na mesma data (`talent_availability`), com o evento concorrente no `title` —
  e desde a 215 o mesmo indicador aparece na busca, antes de escalar.
- **Teto de cachê (feature 215)**: quando o evento nasce da calculadora de orçamento, cada cargo
  guarda um `cache_cap` (= o cachê calculado). **O valor do teto continua invisível para quem
  escala** — decisão de produto: o casting não negocia contra um número na tela. O que aparece é
  só o aviso, em três estados no card: *valor digitado acima do teto e ainda não salvo* → aviso
  vermelho + borda vermelha no campo ("Acima do limite deste evento. Ao salvar, o valor volta
  para o limite.", ou a variante de superadmin, que pode salvar assim mesmo e fica no log);
  *valor acima do teto já gravado* → nota discreta "Cachê autorizado acima do limite deste
  evento.", sem borda vermelha (é estado legítimo, não erro); *sem teto* (evento criado à mão) →
  nada. Ao salvar, o campo **reespelha o `cache_value` devolvido pelo servidor**: como
  `assign_casting_role` rebaixa o valor ao teto para não-superadmin, sem isso a tela exibiria o
  número recusado. A tela Jinja antiga mostrava o valor do cap (`event_detail.html`); a migração
  React o havia perdido por completo — o servidor rebaixava em silêncio.
  **Feature 239, decisão 18 — exceção para superadmin**: só ele vê uma linha discreta com o
  **número do teto** (`cache_cap_efetivo`) e a **conta que o produziu** (`cache_cap_note` —
  ex. "Ator cara-limpa: base 2h R$ 300 + noturno R$ 50 = R$ 350", ou "definido manualmente, sem
  orçamento vinculado" quando o papel não veio de orçamento); quem autoriza acima do teto precisa
  saber de onde ele saiu. O servidor faz o mesmo corte de RBAC — `cache_cap`/`cache_cap_note` nem
  chegam no payload de quem não é superadmin.
- **Carrinho de transporte fora de SP (feature 239)**: em evento com `is_outside_sp`, cada card
  de casting ganha o botão **"🚗 Marcar transporte"**/**"🚗 Leva o carro"** (gate `_can_edit_event`,
  mesmo de quem escala) para marcar quem leva o veículo. Marcado, o card mostra a badge dourada
  **"🚗 Transporte"** (com o valor da parcela no `title`) e, só para superadmin, a linha do teto
  passa a somar essa parcela ("... + transporte R$ 100,00 (carrinho)"). O valor pago continua sendo
  um número só em `cache_value` — não existe campo de dinheiro separado para o transporte na tela.
- **Vaga "Técnico de Som (Presença)" somente leitura (feature 239, decisões 9/11)**: dentro de
  "Equipe de apoio" ela vira um card sem nenhuma ação — sem campo de cachê, sem botão de convite,
  sem status de pagamento, só o nome de quem foi designado (ou "— ninguém designado —") e a nota
  "Vaga sem cachê — designação no painel de Ensaio." A vaga do PIX ("Técnico de Som", Nivaldo)
  continua um card comum.
- **Badge de maquiador (feature 239, decisão 17)**: no cabeçalho da seção Casting, badge
  **"Falta maquiador"** (dourado) quando algum personagem tem `needs_makeup` e não existe vaga
  extra de maquiador com talento atribuído, ou **"Maquiador fechado"** (verde) quando existe.
  Cada personagem com `needs_makeup` ganha 💄 ao lado do nome. O card da vaga de Maquiador sem
  talento herda o destaque visual (borda dourada) já usado para conflito de agenda.
- **API**: `GET /api/events/<id>` (payload único da tela) · `POST /api/roles/<id>/payment-status`
  · `POST /api/roles/<id>/figurino-sheet` · `POST|DELETE /api/roles/<id>/figurino-done` ·
  `POST /api/events/<id>/travel-estimate` · `POST /api/events/<id>/materials` ·
  `DELETE /api/materials/<id>` · `POST /api/events/<id>/feedback-link`.
  **Feature 215**: `GET /api/events/<id>/casting-options` (talentos com `photo_url` +
  `availability` desta janela) · `PATCH /api/events/<id>/basico` ·
  `PATCH /api/events/<id>/comercial` · `PUT /api/events/<id>/clients` ·
  `PATCH /api/events/<id>/form-response`.
- **Vínculos**: Talentos · Figurino (`EventRole.figurino_sheet_id`) · Financeiro (comissões e
  pagamentos) · Ensaios (`parent_event_id`) · Grupo comercial (`group_leader_id`) · Clientes ·
  Gastos Extras (`SpecialExpense.event_id`) · Avaliação pública da cliente (`/avaliar/<token>`).
- **Hotfix 257 (2026-08-21)**: anexar comprovante, contrato, reembolso ou nota fiscal **não**
  gravava (2xx e nada no banco; a tela desenhava o anexo por causa do autoflush e o refresh
  perdia). Faltava `db.session.commit()` nos cinco POSTs. Os arquivos enviados no período
  ficaram órfãos no volume — ver `specs/257-hotfix-anexos-persistencia/`.

---

### A.3 Casting

#### `/talents` — Banco de Talentos
- **Acesso**: todos exceto `REVENDEDOR_EDUCAMANTO`; **edição** só `CASTING`/`SUPERADMIN`.
- **UX**: `TalentMosaic` (grade visual com foto) + `TalentFilterPanel` (status, tags, medidas,
  passaporte/visto, idiomas). Estados `pending` × `active`. Desde a feature 270 o card baixa a
  **variante** da foto de rosto (`srcset` 320/480/640 + `sizes` da grade de 2–6 colunas, `loading="lazy"`)
  por `/uploads/t/<largura>/talent_photos/<arquivo>`, e tanto a variante quanto o original têm
  `Cache-Control: private, immutable` — a segunda abertura da grade não refaz requisição de foto
  (antes, `/uploads` respondia `no-cache` e revalidava todas). A foto de documento continua
  inteira e sem cache longo.
- **Aba "Emails com problema"** (feature 219, só `CASTING`/`SUPERADMIN`): fila de quem não está
  recebendo nossos emails, agrupada por endereço, com o motivo traduzido, o que fazer, contador de
  falhas e link de WhatsApp com a mensagem já escrita. `Resolver` fecha o endereço inteiro.
  O `view` da aba é **estado separado** do `status` do diretório de propósito: alternar para a fila
  e voltar não pode perder página, busca nem filtros aplicados.
- **API**: `GET /api/talents/directory` · `GET /api/talents/bounces` ·
  `POST /api/talents/bounces/resolve`.

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
- **No menu, mora em MARKETING** (mudou em 2026-08-11): revisar mídia é etapa do marketing, ao
  lado do painel que planeja a postagem que essa mídia vai virar — não da produção de figurino.
  O item continua **aberto a toda a equipe interna** (`notRevendedor`), porque
  `revisao/review_ops.can_view` libera qualquer pessoa que esteja em `space.reviewer_ids` e
  `GET /api/revisao/reviewer-options` oferece qualquer usuário ativo como revisor: gatear o item
  por papel deixaria um convidado do financeiro sem porta de entrada. **Consequência aceita**: a
  seção "Marketing" do menu, que antes só existia para `MARKETING`/`COMERCIAL`/`CASTING`/`SA`,
  agora aparece para todo papel interno — com "Revisão" dentro.

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

> **Item avulso × tema (fase 1).** O painel de Personagens do gerenciador
> (`/admin/catalogo/:id/editar`) agora abre com o tipo do item: quando NÃO tem elenco, mostra o
> campo **"Item avulso · ficha de figurino"** (a ficha é do próprio item); quando tem elenco de
> UM personagem só, oferece **"Transformar em item avulso"**. A grade do catálogo carimba
> **Tema · N personagens** ou **Avulso** + a ficha. Regra para quem organiza: *elenco individual
> é só para tema de verdade; avulso recebe ficha direto.* Na tela da Ficha, um figurino que
> pertence a um item avulso aparece como "Vinculado a um item do Catálogo", não como sem vínculo.

#### `/figurinos/new` e `/figurinos/:id/edit` — Ficha de Figurino
- **UX**: nome do personagem (obrigatório), foto (upload, rotação, remoção), **peças** como lista
  `{name, qty}`, **tags** via `ChipInput`, notas.
  Campo **"Figurinos iguais que temos"** (feature 235): quantos figurinos daquela ficha existem no
  acervo. **Não é o `qty` da peça** — aquele é "2 luvas" dentro de UM figurino; este é "temos 3
  Gatunos", e é o que decide se dá para escalar o mesmo personagem em dois eventos ao mesmo tempo.
  Zero é válido (ficha de figurino ainda não produzido) e aparece como selo vermelho no Banco de
  Figurinos; acima de 1, o card mostra `N×`.
  Campo **"Vincular a um Personagem do Catálogo"** (`FigurinoCatalogLinkField`): autocomplete de
  Personagens; quando já vinculado, mostra `Personagem — Tema` e botão **Desvincular**. Escreve na
  mesma `CatalogCharacter.figurino_sheet_id` usada pelo lado do catálogo — **vínculo bidirecional
  sem coluna nova** (feature 186).
  Numa ficha nova, a foto escolhida só sobe **após** a ficha existir (o endpoint de foto exige
  `sheetId`). O vínculo de Personagem também existe na CRIAÇÃO (`NewFigurinoCharacterField`,
  hotfix vincular-na-criacao): escolhe-se o personagem antes do "Criar ficha" e o PATCH roda logo
  depois da criação, mesmo padrão deferido da foto; lista só personagens **sem** ficha (trocar a
  ficha de quem já tem é fluxo da edição) e, com o nome da ficha vazio, escolher o personagem
  preenche o nome de brinde. Com foto e/ou vínculo pendentes a navegação pós-criação vai para a
  **edição** (confirmação visual), senão para a lista.
- **API**: `POST /api/figurino` · `PATCH|DELETE /api/figurino/<id>` ·
  `POST|DELETE /api/figurino/<id>/photo` · `POST /api/figurino/<id>/photo/rotate`.
- **Vínculos**: Ficha ↔ Personagem do Catálogo ↔ Elenco de Evento (`EventRole`).

#### `/figurinos/producao` — Produção e Compras *(feature 225; menu unificado na 225f)*
- **É a única porta para os três tipos de pedido.** Abas **Tudo / Produção / Manutenção /
  Compras**, e a aba mora na URL (`?tipo=`) — por isso ela é linkável e serve de destino do
  redirect de `/compras`. Trocar de aba usa `replace`, então quatro cliques não deixam quatro
  paradas para o botão Voltar desfazer. Sem `?tipo=`, abre em "Tudo"; com `?ficha=`, abre em
  Manutenção (é o destino dos avisos "não pode ir").
- O título da página é fixo e igual ao rótulo do menu — um título que mudasse junto com a aba
  faria a tela parecer três telas diferentes.
- **Fotos já na abertura** *(225g)*, nos três tipos: opcionais, quantas quiser, logo abaixo dos
  detalhes (a foto é continuação do enunciado, não anexo administrativo). Antes só dava para
  anexar **depois** de criar, na tela de detalhe — e lá o anexo exige permissão de execução, então
  quem abria o pedido frequentemente não conseguia anexar nada ao próprio pedido.
  - A criação virou **`multipart/form-data`** (o formulário carrega arquivo). Todo campo chega
    como string; campo vazio é **omitido** pelo front, porque os resolvedores tratam ausente e
    `""` como "sem valor" mas engasgariam com a string `"null"`.
  - A lista de fotos é validada **antes** de o pedido ser criado: um arquivo que não serve recusa
    o pedido inteiro, em vez de deixar um pedido salvo pela metade.
  - O histórico ganha **uma** linha ("3 fotos anexada(s) na abertura."), não uma por foto.
  - Compressão é a de `storage.save_file` (1200px, JPEG 85) — a mesma de todo upload do app.
    **Furo conhecido: `.heic` passa sem compressão** (ver 225g em `docs/03`).
- **Acesso**: qualquer papel interno lê e abre pedido; **Figurino/Superadmin** executam;
  **só Superadmin aprova**. As flags vêm do servidor em `flags` (`can_create`, `can_execute`,
  `can_approve`) — a tela não recalcula RBAC.
- **UX**: quatro números no topo (em aberto, atrasados, previsto, gasto lançado), filtros por
  situação, **"Só os meus"** e busca. A tabela é ordenada por **prazo**, não por criação: é o
  prazo que organiza o trabalho do dia. Quem não tem prazo vai para o fim.
  Badge de prazo em vermelho quando venceu ou vence em ≤2 dias; dourado até 7 dias.
  Sem prazo próprio, vale a data do evento.
- **Novo pedido**: título, detalhes, evento (opcional — via data + seletor, mesmo padrão de
  Gastos Extras), prazo, quantidade, custo previsto. O campo **Responsável** só aparece para
  quem executa: quem pede não escolhe quem faz — **exceto em compra** (ver `/compras`).
  **Feature 239**: o `DialogContent` ganhou `max-h-[85vh] overflow-y-auto` (mesmo padrão de
  `Fila3DPage`/`FormulariosAdminPage`) — o diálogo estourava a altura da tela em formulário longo
  (com fotos anexadas na abertura, feature 225g) e a parte de baixo ficava inalcançável.
- **Rotas declaradas ANTES das dinâmicas** em `App.tsx` — `/figurinos/producao/12` não pode cair
  em `/figurinos/:id/edit` (mesmo cuidado de `/events/cancelamentos` na 224).
- **API**: `GET /api/figurino/producoes` · `POST /api/figurino/producoes` ·
  `GET /api/figurino/producoes/responsaveis`.

#### Pedidos de Compra — aba `?tipo=compra` *(feature 225c; menu unificado na 225f)*
- **Não tem tela nem item de menu próprios.** Nasceu com os dois na 225c e perdeu ambos na 225f:
  produção, manutenção e compra são o **mesmo objeto** (`figurino_producoes`, discriminado por
  `kind`), e dois itens de menu para uma tabela só eram porta duplicada. A compra é a aba
  **Compras** de `/figurinos/producao`, endereçável por `?tipo=compra`.
- **`/compras` continua respondendo**, como `<Navigate replace>` para
  `/figurinos/producao?tipo=compra` — a rota circulou em links e favoritos, e é ela que mantém
  "abrir direto nas compras" possível de qualquer lugar.
- **Acesso**: qualquer papel interno vê e abre (menos Revendedor EducaManto). **Só Superadmin
  aprova.** Depois de aprovada, quem move é o **responsável pela própria compra** (ou a oficina)
  — é o que faz o pedido entregue ao Comercial não travar em "aprovado".
- **Fluxo**: `Solicitado → Aprovado → Comprado → Recebido`, com `Cancelado` como saída (exige
  motivo). **`Comprado` ainda conta como em aberto** — o dinheiro saiu, a coisa não chegou. Dá
  para voltar de `Recebido` para `Comprado` (chegou errado); voltar limpa o `done_at`.
- **Escolher ficha é sempre pelo `FigurinoPicker`** (`components/FigurinoPicker.tsx`) — ver
  "Padrões transversais" no fim deste documento.
- **Novo pedido de compra**: o que comprar, detalhes, **para qual figurino (opcional)**, evento
  (opcional), prazo, quantidade, quanto deve custar e **quem é o responsável** — este último
  aparece para qualquer pessoa aqui, e a lista traz a **equipe interna inteira**
  (`?tipo=compra`), não só o figurino.
- **Os chips de situação mudam com o tipo** (`filtrosDe`): "Comprados/Recebidos" só na compra,
  "Em produção/Prontos" só na oficina. Trocar de aba com um filtro órfão volta para "Em aberto".
- **Onde a compra aparece**: aba **Compras** (e também na aba **Tudo**, junto com os outros dois);
  painel pessoal da home (**"🧵 Minhas peças e compras"**); e, quando nasce sem dono, na caixa de
  entrada do setor — mas **só para quem aprova**, não para a oficina.
- **A aba ativa pré-seleciona o tipo** no diálogo de "Novo pedido": quem está em Compras e clica
  já encontra "Comprar" marcado. O seletor dos três tipos continua à vista — é sugestão, não
  trava, e com um menu só é ali que a pessoa descobre que dá para pedir compra.
- O detalhe é `/figurinos/producao/:id` para os três tipos; o breadcrumb volta para a aba de
  origem (`?tipo=compra` quando é compra).

#### `/figurinos/producao/:id` — Detalhe do pedido
- **UX**: coluna esquerda tem o que precisa ser feito, as fotos, os **gastos** e o **histórico**;
  a direita tem as ações de situação, os dados, o responsável e os anexos.
  - **Gastos**: soma só o aprovado, compara com o previsto e avisa em vermelho quando estourou.
    "Vincular" oferece os gastos do mesmo evento e os de categoria Figurino — **vincular não
    recria nada**, o lançamento continua com data, comprovante e aprovação.
  - **Orçamentos**: o menor valor vem destacado em verde — a tela existe para comparar propostas.
  - **Histórico**: mudanças de situação, vínculos e notas livres, do mais novo para o mais antigo.
    Uma foto do andamento entra **como linha do histórico**, com legenda — é o que faz dele uma
    evolução e não uma lista.
  - Trocar o responsável dispara e-mail **e** o convite do Google. Se o Google falhar, aparece
    uma faixa dourada de aviso: o pedido foi salvo, o que falhou foi a integração.
- **Os botões de situação vêm do servidor** (`transicoes`) — a tela não decide para onde o pedido
  pode ir. Cancelar exige motivo.
- **API**: `GET|PATCH|DELETE /api/figurino/producoes/<id>` ·
  `POST /api/figurino/producoes/<id>/status` · `.../comentarios` · `.../anexos` ·
  `.../gastos` · `.../gastos-vinculaveis`.

#### Onde a manutenção aparece *(feature 225b)*

O valor da manutenção não está na tarefa, está no **aviso chegar onde a decisão é tomada**:

| Superfície | O que mostra |
|---|---|
| `/figurinos` (lista de fichas) | Selo sobre a foto: `⚠ Não pode ir` (vermelho) ou `🪡 N consertos` (dourado). Leva para a oficina já filtrada por aquele figurino (`?ficha=`). |
| Detalhe do evento → Produção → Figurino | O card do personagem fica com **borda vermelha** e traz o texto do problema + link "ver na oficina". O bloqueio **vence o "Separado"** — marcar como separada uma peça que não pode ir é o erro que o aviso existe para impedir. |
| Home → "🪡 Oficina — sem responsável" | Pedidos abertos que ninguém assumiu. Gate por **papel** (FIGURINO/SA), ao contrário de "Minhas peças". |
| `/figurinos/producao` | Abas **Tudo / Produção / Manutenção / Compras**; a linha mostra a ficha em vez do evento quando há ficha. |

No formulário, escolher "Consertar / ajustar" troca o resto: exige **qual figurino** e
**se dá para usar assim**, muda os rótulos, e some com quantidade. O painel de gastos só aparece
se houver custo previsto ou gasto lançado — a maior parte da manutenção é trabalho manual, e um
"R$ 0,00" grande sugeriria que falta lançar alguma coisa.

#### Home — painel "🧵 Minhas peças de figurino" *(feature 225)*
Primeiro painel **pessoal** da home: todos os outros são por papel, este é por identidade
(`responsible_id == user.id`). Aparece no topo, só para quem tem peça sob sua responsabilidade, e
some sozinho quando não há nenhuma. Vermelho para atrasado ou ≤2 dias — mesma linguagem de
urgência das tarefas de casting, mas medida pelo **prazo do pedido**, que costuma ser bem antes do
show. Chave `figurino_producao` em `GET /api/dashboard`.

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
  - **Exclusão forçada (feature 213, só `SUPERADMIN`)**: quando a peça está em uso, o diálogo
    oferece uma caixa de seleção "Excluir mesmo assim, removendo o presente de todos os N
    evento(s) e da Fila de Impressão. Não dá para desfazer" — o botão fica **desabilitado** até
    ela ser marcada e vira "Excluir e desvincular" (`DELETE .../<id>?force=true`). Quem não é
    superadmin continua vendo só a orientação de inativar. A auditoria grava de quantos eventos a
    peça foi desvinculada.
  - Entrada/saída de cards com Framer Motion respeitando `useReducedMotion()`.
- **API**: `GET|POST /api/3d/acervo` · `PATCH|DELETE /api/3d/acervo/<id>` (`?force=true` no DELETE
  = desvincular de todos os eventos, `SUPERADMIN`).

#### `/events/:id` — bloco **"Presentes 3D"** *(injeção na tela existente)*
- **Onde**: **Aba Produção** — ver §A.2. *(Corrigido em 2026-08-06: este bloco ainda descrevia o
  layout pré-215, "coluna esquerda, abaixo de Materiais de ensaio". A feature 215 substituiu o mural
  de duas colunas por quatro abas.)*
- **Quando**: **somente** se `event.event_type === 'SHOW'` — o servidor nem serializa a chave
  `presentes_3d` nos outros tipos.
- **Acesso**: qualquer usuário que abre o evento **lê** a lista; só `ARTISTA_3D`/`SUPERADMIN`
  (flag `can_manage_3d`) vê o formulário de adição, o seletor de status e o botão de remover.
- **UX**: lista com miniatura quadrada, quantidade, prazo e observações; o formulário de adição
  usa obrigatoriamente o **`Combobox` de `@manto/ui`** (Princípio X.1) exibindo a **miniatura
  quadrada (`AvatarThumb`)** de cada peça do Acervo para seleção visual rápida, mais quantidade,
  prazo e observações.
- **API**: `POST|PATCH|DELETE /api/events/<id>/3d-gifts[/<gift_id>]` · `GET /api/3d/acervo?ativos=1`.

#### `/3d/tags` — Tags NFC *(feature 255; vídeo na 261; revisão de vídeos na 265)*
- **Acesso**: `ARTISTA_3D`, `SUPERADMIN` (mesmo gate da seção 3D).
- **Objetivo**: a ponte entre a tag NFC física (embutida na luminária entregue) e o sistema.
  Fluxo real da equipe: gerar lote → gravar as tagzinhas → **anotar o Nº em cada uma** → na
  alocação, "nº X → evento/cliente Y" pelo vínculo de evento. Desde a 265, também o posto de
  **revisão dos vídeos**: o Artista 3D acompanha o que tem vídeo ou não e assiste por dentro,
  **sem contar acesso** (revisar pelo link público inflava a métrica das clientes).
- **UX**:
  - **Duas abas** *(feature 265)*: **"Tags"** (gestão — tudo abaixo) e **"Vídeos"** (revisão).
    A aba mora na URL (`?aba=videos`, padrão de `/figurinos/producao?tipo=`): link
    compartilhável, F5 mantém, troca com `replace` (Voltar não acumula paradas). Título do
    `PageHeader` fixo — a página é uma só, as abas é que recortam.
  - **Formulário de lote no topo** (aba Tags): `Combobox` das peças habilitadas (só `nfc_prefix`
    não-nulo e ativas) + quantidade → "Gerar tags" com loading e confirmação textual ("N tags
    geradas — anote o Nº em cada tagzinha ao gravar").
  - **Tabela** (uma linha por tag física): **Nº em destaque** (`font-display`, é o rótulo que
    grita mais que o código, de propósito), código + **copiar link** (`CopyButton`, copia
    `<origin>/nfc/<code>` — é o que se grava na tag), produto com miniatura quadrada, evento
    (título+data, ou "— estoque"), **cliente** (contratante do evento), **coluna "Vídeo"**
    *(265)* — badge azul "com vídeo" **clicável** (abre o diálogo de vídeo, com player) ou
    badge neutra "sem vídeo" —, acessos (tooltip com o último), badge Ativa/Inativa e ações.
  - **Vincular (evento OU cliente direta)**: `Dialog` com dois `Combobox` **assíncronos** —
    evento pela busca da agenda (`useAgendaSearch`) e **cliente direta** pela busca de clientes
    (`useClientSearch`), para o caso de campanha/brinde **sem show** (a pessoa é cadastrada no
    módulo Clientes e vinculada aqui). Escolher **já salva** (PATCH e fecha); "Desvincular
    evento"/"Desvincular cliente" no rodapé. Na tabela, cliente direta aparece com badge
    "direta" e tem precedência sobre a contratante do evento.
  - **Desativar/Reativar** com loading por linha. **Não existe ação de excluir a TAG em lugar
    nenhum** — nota fixa no rodapé explica: código gravado numa peça entregue é eterno;
    desativar faz a página pública mostrar o conteúdo padrão.
  - **Vídeo** *(feature 261; player e ConfirmDialog na 265)* — ação por linha (ou badge da
    coluna Vídeo), abre `Dialog` dedicado ("Um vídeo especial para você"): **sem vídeo** →
    input de arquivo oculto (`accept=".mp4,.mov,.webm,.m4v"`, disparado por um botão "Enviar
    vídeo" que abre o seletor nativo — mesmo padrão de `FilaProducaoMidiaPage`, feature 205) +
    campo "Título" opcional; escolher o arquivo já dispara o envio, com `loading` no botão.
    **Com vídeo** → **player embutido** (`<video controls playsInline preload="metadata">`,
    `key={delivery.id}` para remontar no Substituir; `src` pelo **espelho admin**, nunca a URL
    pública), nome do arquivo + data do envio, e os botões **Substituir** (reabre o seletor; o
    novo upload apaga arquivo e linha do vídeo anterior — 1 vídeo ativo por tag) e **Remover**
    (**`ConfirmDialog`** irmão do diálogo, com pending e erro dentro dele — o `window.confirm`
    da 261 violava o Princípio V e foi trocado na 265; some da página pública imediatamente).
    O diálogo lê a tag da **lista viva** (`tags.find`, não uma cópia local) — assim que o
    upload/remoção invalida a query, ele mostra o novo estado sem fechar e reabrir (depois de
    Remover, o mesmo diálogo já oferece "Enviar vídeo"). Erro de upload (formato fora da
    allowlist, acima de 250 MB) aparece inline no diálogo.
  - **Aba "Vídeos"** *(feature 265)* — o painel de revisão, componentes em
    `apps/internal/src/components/nfc/` (`NfcVideosPanel` + `NfcVideoCard`):
    - **KPIs** (`DenseCard`): Tags ativas · Com vídeo · Sem vídeo · Nunca acessadas — calculados
      no cliente sobre a lista já carregada (com/sem vídeo contam só tags ativas); a busca não
      mexe nos KPIs.
    - **Busca** por código, nº, produto, evento ou cliente (filtra cards e lista sem vídeo).
    - **Cards com player**, agrupados por **evento (data desc) → "Clientes diretas (sem show)"
      → "Estoque"** (espelha a precedência da tabela). Cada card: vídeo
      (`preload="metadata"` — obrigatório num grid com N players), título (fallback "Sem
      título — a página usa a copy padrão"), nº + código + `CopyButton` da URL pública,
      produto, cliente, data do envio, badge "Inativa" quando for o caso (tag desativada com
      vídeo continua auditável por dentro — lá fora ela dá 404), e ações "Gerenciar vídeo"
      (abre o diálogo) e **"Ver na tabela"** (troca para a aba Tags, `scrollIntoView` +
      highlight `bg-gold-soft` de ~2s na linha — efêmero, não vai para a URL).
    - **Seção "Sem vídeo"**: tabela compacta das tags **ativas** ainda sem vídeo (a fila de
      trabalho do revisor), cada linha com "Enviar vídeo" (abre o diálogo direto no estado de
      upload) e "Ver na tabela". Vazio: "Todas as tags ativas têm vídeo."
    - Mobile: KPIs em faixa, grid de cards em 1 coluna, sem rolagem horizontal.
- **API**: `GET /api/3d/nfc` · `POST /api/3d/nfc/lote` · `PATCH /api/3d/nfc/<id>` ·
  `POST /api/3d/nfc/<id>/entregas` (multipart) · `DELETE /api/3d/nfc/<id>/entregas/<delivery_id>` ·
  `GET /api/3d/nfc/<id>/entregas/<delivery_id>/media` *(265 — espelho admin da mídia: mesmo
  gate, serve inclusive tag desativada e **nunca incrementa `access_count`**; é o `src` de todos
  os players do ERP)*.
- **Acervo (`/3d/acervo`)**: o formulário da peça ganhou o campo opcional **"Prefixo NFC"** com
  hint do formato do código — preenchido, presentes da peça geram tags automaticamente.

#### `/nfc/<code>` — página pública da tag NFC *(feature 255, SEM login; vídeo na 261)*
- **Endereço**: raiz do domínio (`app.mantoproducoes.com.br/nfc/<code>`) — **URL gravada na tag
  física, imutável e eterna**. Servida pelo bundle da vitrine via `NFC_PREFIX` no
  `frontend/server.js` (mesmo mecanismo do `/cadastro`; `isRootSurface` no `App.tsx` roda o
  Router sem basename e sem o `WishlistFloat`).
- **Objetivo**: a cliente encosta o celular na luminária e cai aqui. V1 é o "portal fechado":
  identidade Manto + Instagram; com a feature 261, uma tag pode ganhar um **vídeo pessoal** entre
  a arte e o CTA. Todo o conteúdo vem de `GET /api/nfc/<code>` — a página evolui (campanhas,
  fotos do evento) sem regravar tag nenhuma (`campaign: null` é o gancho; `deliveries` é o
  gancho da 261).
- **UX** (mobile-first de verdade — o acesso nasce de um toque NFC, geralmente à noite ao lado
  da luminária acesa; 2ª rodada, redesenhada com a foto da peça física em mãos):
  - **Retrato da luminária**: céu noturno (gradiente roxo da paleta) com 12 estrelinhas
    piscando, nuvens difusas na base, e a **estrela "Magia de Sonhar" que ACENDE** como a
    lâmpada real — contorno apagado chega primeiro, o brilho quente sobe revelando o escrito
    (Fraunces itálico, SVG inline; cores da peça registradas como tokens `lamp.*` no
    `tailwind.config.ts` do app público — zero cor hardcoded). Halo `drop-shadow-lamp`
    "respirando". Com `useReducedMotion`: estrela já acesa, nada pisca.
  - A arte substitui a foto do produto do acervo (a luminária É a estrela); modo genérico usa o
    mesmo palco.
  - Copy provisória: eyebrow "Manto Produções" + "A magia da Manto também na sua casa" + **sem
    vídeo**: "Este é o portal da sua luminária. Em breve, ele se abrirá bem aqui…" (placeholder
    inalterado). **Com vídeo** *(feature 261)*: o parágrafo dá lugar a um card arredondado
    (paleta `lamp`/`gold` do `tailwind.config.ts`, zero cor hardcoded) com o título da entrega
    (fallback "Um vídeo especial para você") e um `<video controls playsInline
    preload="metadata">` (`src` via `assetUrl(media_url)`, largura do `max-w-md`) — entra na
    MESMA coreografia de fases (`enter()`) das linhas ao redor, respeitando
    `useReducedMotion`. O CTA do Instagram continua abaixo, intacto.
  - CTA "Seguir @mantoproducoes" (URL vem do servidor; botão só renderiza com o dado na mão —
    nunca botão morto), toque ≥ 44px, sem rolagem horizontal de 320 a 430px.
  - **Código inexistente ou tag desativada = mesma página em modo genérico** — nunca uma tela
    de erro, nunca a confirmação de que um código existe (SC-006).

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
  - Seis colunas na ordem do fluxo: 💡 Ideia · 🎬 Produção · 👀 Revisão · ✅ Pronto · 📅 Agendado ·
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
- **Feature 256**: campo **"Link do post publicado"** (`permalink`, http(s), querystring removida) —
  é por ele que o auditor casa o card com as métricas reais do export da Meta. Mudar o status para
  "Publicado" sem link destaca o campo (borda dourada + orientação), sem bloquear.
- **Vínculo com o catálogo (múltiplos Temas, feature 204b)**: um post pode falar de vários Temas
  ao mesmo tempo (ex.: Reels que junta "15 Anos" e "Debutante"). A UI compõe o **`Combobox` de
  `@manto/ui`** (que continua single-select — nenhum componente novo entrou no design system)
  como "adicionar": cada seleção vira um chip removível abaixo, com `AvatarThumb` **quadrada** da
  capa (Princípio X.1/X.2); o Tema já escolhido some das opções do `Combobox`. O responsável usa o
  mesmo `Combobox` (single, como antes), com avatar **circular** (pessoa).
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

#### `/marketing/desempenho` — Desempenho de marketing *(feature 256)*
- **Acesso**: `MARKETING`, `SUPERADMIN` (gate de servidor em `GET /api/marketing/desempenho`).
- **Objetivo**: o histórico que o auditor de marketing semanal grava a partir dos exports da
  Meta/Google — a memória que o e-mail não tem.
- **UX**: seletor segmentado 4/12/26 semanas + intervalo livre (`keepPreviousData`, sem piscar);
  4 KPIs (manchete = **leads no período e custo por lead**, ou alcance com o motivo quando não há
  atribuição; CAC do mês; gasto no período; posts publicados + metas atrasadas); gráficos SVG
  próprios (`components/charts/`): **um eixo por gráfico** (alcance por semana e seguidores são
  dois gráficos), barras de gasto por campanha (uma matiz = magnitude), **funil de unidades
  mistas como tiles** (gasto → cliques → leads → eventos com CPC/taxa/custo na seta); tabela
  semanal escondida em `<details>`; tabelas de campanhas e de posts (vínculo "pelo link" / "pela
  data" / "sem card"); metas atrasadas com atalho; lista de rodadas com arquivos rejeitados e
  motivo. Estado vazio explica onde salvar os exports e quando a rotina roda. Mobile: tabelas
  rolam dentro do bloco, página sem rolagem horizontal (375 px conferido).
- **API**: `GET /api/marketing/desempenho`.
- **Rotina que alimenta**: `scripts/marketing/` (collect → publish → checks → report), scheduled
  task `auditoria-marketing-semanal` (segunda 06:30, catch-up), skill local `marketing-auditor`.
  Relatório por e-mail com barras em HTML/CSS (Gmail não renderiza SVG).

#### `/virtuais/campanhas` — Interações Virtuais (feature 205, US1)
- **Acesso**: `COMERCIAL`, `SUPERADMIN` (gate de servidor `require_virtuais_access()`).
- **Objetivo**: montar e acompanhar as campanhas do canal de venda self-service — chamadas de vídeo
  de 10 min e vídeos gravados com Personagens do catálogo.
- **UX**: tabela densa com uma linha por campanha — miniatura **quadrada** do personagem
  (`AvatarThumb`), situação em `Badge` (`Rascunho`/`Publicada`/`Pausada`), os dois preços, vendidos,
  faturado, horários disponíveis/total e vídeos consumidos/capacidade. Estado vazio convida a criar
  a primeira. Entrada da tabela com Framer Motion respeitando `useReducedMotion()`.
- **Valores**: sempre `R$ {formatBRL(...)}` do `@manto/money` — nenhuma máscara própria
  (Princípio IX).
- **API**: `GET /api/virtuais/campanhas`.

#### `/virtuais/campanhas/:id` — Edição da campanha
- **Acesso**: idem.
- **UX**: quatro cards.
  - **Conteúdo público** — título, **foto de capa** (upload com prévia), texto de apresentação,
    termos de tolerância, WhatsApp de atendimento e **editor de perguntas frequentes** (feature
    224b). Capa e FAQ faltavam: a tela só mandava JSON, então a capa nunca chegava — e como ela
    é pré-requisito de publicação, **nenhuma campanha conseguia sair do rascunho**; o FAQ era
    carregado e reenviado sem ter editor, então saía sempre vazio na landing. Enviar capa faz a
    requisição virar `multipart` (`campaignBody` em `lib/virtuais.ts`).
  - **Preços e estoque** — os três preços em `MoneyInput` (digitação mascarada, valor cru no JSON),
    capacidade de vídeos com "N de M já vendidos" e prazo de entrega em dias.
  - **Estoque de horários** — data + janela início/fim geram os slots de 10 min; o retorno diz
    quantos foram criados e quantos já existiam. Lista os horários com selo de situação; só os
    livres têm botão de remover.
  - **Presentes 3D liberados** — `Combobox` pesquisável do Acervo 3D com miniatura **quadrada**
    (Princípio XII.2); as peças já liberadas viram chips removíveis.
  - Publicar/Pausar no cabeçalho, ao lado de Salvar. Todo botão mostra estado de carregamento
    (Princípio V).
- **Regra de negócio visível na tela**: publicar exige preços, capa, prazo e termos — faltando
  qualquer um, o erro aparece **no campo culpado** e nada do que foi digitado se perde. Alterar
  preço **não** afeta pedidos já criados (os valores ficam congelados na reserva).
- **API**: `GET /api/virtuais/campanhas/<id>/admin` · `PATCH /api/virtuais/campanhas/<id>` ·
  `POST .../publicar` · `PUT .../acervo` · `POST .../horarios` · `DELETE /api/virtuais/horarios/<id>`.
- **Vínculos**: Campanha → `CatalogCharacter` → `FigurinoSheet`; Campanha ↔ `Acervo3DItem` (N:N).

#### `/v/:slug` — Landing e checkout da campanha *(app público, feature 205 US2)*

> ⚠️ **Rota de produção: `/catalogo/v/:slug`.** Estas telas moram em `frontend/apps/public`
> (`App.tsx:37-38`), que roda sob o basename `/catalogo` em produção — é assim que o backend gera os
> links (`app/email_service.py:594` e `:672`, `app/marketing/virtuais_ops.py:919`). Diferente de
> `/f/*`, **não há redirect curto** para `/v` em `frontend/server.js`. Em dev
> (`npm run dev:public`) elas ficam na raiz. O mesmo vale para `/v/pedido/:token` abaixo.
> *(Os blocos `/v/*` estão fisicamente nesta seção A por herança da feature 205, mas pertencem à
> seção B — app público.)*

- **Acesso**: público, sem login. Rascunho → 404; pausada → 410 (a família precisa saber se errou
  o link ou se a campanha saiu do ar).
- **Objetivo**: vender a interação sem atendimento — do link do Instagram ao pagamento.
- **UX (mobile-first, Princípio X)**: coluna única, capa, textos, escolha de modalidade com os dois
  preços, prazo do vídeo gravado visível **antes** da compra, grade de horários, upsell de presente
  3D com miniatura, ficha da criança, total e botão de reservar. **FAQ somente no fim da página**
  (FR-013), seguido do atalho de WhatsApp.
- **Regras visíveis na tela**: erro de validação destaca o campo, leva o foco e **não apaga nada**
  do que foi digitado; `409` mostra aviso e recarrega os horários; `429` explica o limite; `502`
  avisa que o pagamento não abriu — e o horário já voltou ao estoque. O botão nunca fica "morto".
- **Conferido** em 375px e 320px: sem rolagem horizontal, alvos ≥ 44px, nada abaixo de 12px.
- **API**: `GET /api/virtuais/campanhas/<slug>` · `GET .../horarios` · `POST .../reservar` ·
  `GET /api/virtuais/enderecos/autocomplete`.

#### `/v/pedido/:token` — Acompanhamento do pedido *(app público, feature 205 US2)*
- **Acesso**: público, por endereço não adivinhável. **Nenhum dado de criança aparece aqui** —
  nome, endereço, sala e vídeo exigem a validação dupla que entra na US5 (FR-044a).
- **Objetivo**: ser o destino do retorno do checkout. Como a confirmação do pagamento é
  assíncrona, mostra "aguardando" e **vira "confirmado" sozinha** (FR-035a).
- **Detalhe que importa**: a consulta continua rodando com a aba em segundo plano e revalida ao
  voltar o foco — a família vai pagar em outra aba, e sem isso voltaria a uma tela congelada.
- **API**: `GET /api/virtuais/pedidos/<public_token>`.

#### `/virtuais/devolucoes` — Devoluções pendentes *(feature 205 US3)*
- **Acesso**: `COMERCIAL`, `SUPERADMIN`.
- **Objetivo**: garantir que nenhuma devolução se perca. A InfinitePay **não publica API de
  estorno**, então quando um pagamento cai em horário já vendido o sistema cancela o pedido, abre
  a devolução aqui e cobra até alguém marcar como concluída.
- **UX**: tabela com família, valor em BRL, `invoice_slug` e `transaction_nsu` (o que a equipe usa
  para achar a cobrança no painel da operadora), contato e o botão "Já devolvi" com confirmação em
  duas etapas.

#### Detalhe do evento — seção **Interação virtual** *(feature 205 US3)*
- Aparece só em evento `event_type='VIRTUAL'` (mesmo padrão de `Presente3DSection`).
- Traz o que o talento precisa para executar: nome e idade da criança, **dicas da família em
  destaque**, contato, endereço do presente (quando houver) e o botão "Entrar na sala".
- Sala pendente → aviso de que a venda está válida e a sala pode ser gerada de novo.

#### `/virtuais/producao` — Fila de Produção de Mídia *(feature 205 US5)*
- **Acesso**: `COMERCIAL`, `CASTING`, `SUPERADMIN`.
- **Objetivo**: responder "o que eu gravo agora". Espelha a arquitetura da Fila 3D (feature 200).
- **UX**: tabela densa, **uma linha por entrega**, com os quatro blocos na mesma altura —
  horário/modalidade, criança, **dicas da família** e presente 3D. Prazo vencido tinge a linha;
  prazo próximo é sinalizado. Filtros de situação e data não recarregam a página (a lista anterior
  fica visível enquanto a nova chega).
- **Ações na própria linha**: entrar na sala (ao vivo), enviar/substituir o vídeo (gravado) e o
  atalho de WhatsApp com a mensagem pronta.
- **Regra visível**: só existem `pendente`, `gravando` e `finalizado`. Finalizar uma entrega
  gravada sem vídeo é recusado, com o motivo no campo.

#### `/v/pedido/:token` — incremento de validação dupla e vídeo *(US5)*
- Antes de validar: só situação, horário, valor e a dica dos 4 últimos dígitos do telefone.
- Depois de confirmar o telefone: nome e idade da criança, as dicas que a família escreveu, o
  presente, o endereço e o **player do vídeo** — servido por endpoint validado, nunca por link de
  arquivo.
- Cinco erros de telefone bloqueiam por 15 minutos; a sessão expira por 30 min de inatividade.
- **Vídeo gravado não mostra "entrar na chamada"** — não existe chamada nesse produto.

#### `/v/:slug` — etapa de presente 3D *(US4)*
- Acima de 10 peças, `Combobox` pesquisável com miniatura quadrada (Princípio XII.1); abaixo,
  grade visual de `AvatarThumb` — no celular, ver o presente vale mais que ler uma lista.
- O endereço só é exigido quando há presente selecionado, via `GoogleAddressInput`.
- Campanha sem acervo liberado não mostra a etapa, e o servidor recusa `gift_item_id`.

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
- **Banner de falha de entrega** (feature 205f, `components/AvisosFalhosBanner.tsx`): aparece na
  Fila de Produção de Mídia e no painel do evento virtual quando um aviso automático não chegou à
  família ou quando a sala do Meet parou de ser retentada. Distingue "ainda tentando" (a varredura
  insiste sozinha) de "esgotado" (o sistema desistiu; alguém precisa agir), e traz os botões
  **Reenviar manualmente** e **Tentar criar a sala de novo**. Falha silenciosa era o pior desfecho:
  a equipe jurava ter enviado e a família não tinha recebido nada.
- **Loja de Interações Virtuais fora do funil** (feature 205): venda virtual não tem vendedor —
  ela se fecha sozinha na loja pública. Deixá-la aqui inflaria metas que ninguém bateu e afundaria
  a taxa de conversão de quem vende de verdade. Some da tela do vendedor comum e, para gestor,
  aparece num **card próprio acima do funil** (vendas · receita · ticket do canal) com o botão
  "Incluir no funil" — opt-in explícito, `?incluir_loja_virtual=1`. O vendedor comum não recebe o
  bloco nem com o parâmetro: escopo é decisão do servidor.
- **API**: `GET /api/vendas/pipeline?period=&seller_id=&incluir_loja_virtual=`.
- **Vínculos**: `/events/:id` (ação de linha), `/financeiro/comissoes` (a comissão prevista aqui é
  a mesma base que vira `CommissionPayment` lá) e `/financeiro` (Painel Financeiro — custo, lucro
  e auditoria de eventos sem valor).

#### `/clientes` · `/clientes/:id` — Clientes
- **Acesso**: `COMERCIAL`, `FINANCEIRO`, `SUPERADMIN` (`_require_vendas()`).
- **UX**: busca, criação rápida (dedupe por telefone), edição, exclusão, histórico de eventos.
- **Métricas no topo da lista (feature 220)**: KPIs **Novos este mês**, **Com evento** e
  **Recorrentes (2+ eventos)** + barras de **novos clientes por mês** (12 meses; tooltip com a
  quebra formulário/Kommo/manual). `GET /api/clientes/metricas`.
- **Ficha (`/clientes/:id`, feature 220)**: além do card **Eventos** (agenda 2026+), o card
  **"Festas anteriores (formulários)"** lista os formulários preenchidos pela cliente — data da
  festa, link para o evento quando existe ("na agenda") ou marcação "só formulário" (histórico
  pré-2026, que não é materializado no calendário). É a base do marketing de recompra.
  **Feature 266**: as linhas "só formulário" passaram a ser clicáveis (`/formularios?resposta=<id>`),
  e a ficha ganhou o card **"Avaliações"** — nota média em estrelas + notas/comentários dela,
  consumindo `GET /api/clientes/avaliacoes?client_id=` (o filtro já existia no servidor e nenhuma
  tela usava). ⚠️ O recorte do servidor é por `CalendarEvent.client_id` — o FK do **contratante** —
  enquanto o card "Eventos" logo acima lista pela associação múltipla `EventClient`: quem entra num
  evento só como assessora aparece lá e não aqui, e por isso o estado vazio diz *"nenhuma avaliação
  nos eventos em que ela é a contratante"*. Unificar os dois recortes mudaria a semântica de
  `/clientes/avaliacoes` inteira — fica para uma feature própria.
- **Cadastro manual (feature 258)**: botão **"Nova cliente"** no cabeçalho (e no estado vazio da
  busca) abre diálogo com nome*, telefone*, e-mail, empresa, CPF, CNPJ e endereço. Reusa
  `POST /api/clientes/quick-create` (feature 165) e a regra de telefone único: número já
  cadastrado devolve a ficha existente com aviso "nada foi duplicado" + atalho para abri-la, e
  **não sobrescreve** nada dela. Cadastro real invalida lista, busca e métricas (aparece sem F5)
  e nasce com `source="manual"`, separado no gráfico por origem.

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
- **Deep-link (feature 266)**: aceita `?resposta=<id>` e abre o diálogo de detalhe daquela resposta
  direto — é o destino dos links do detalhe do evento (aba Comercial) e da ficha da cliente.
  A URL é a fonte de verdade de qual resposta está aberta: abrir empilha no histórico (o **voltar
  fecha o diálogo**) e fechar limpa o parâmetro, inclusive depois de excluir — senão um F5
  reabriria o diálogo num id morto. Id não-inteiro é ignorado sem disparar requisição
  (`/respostas/NaN` devolveria 404 HTML e estouraria o `JSON.parse` do `apiFetch`).
- **Gerenciador de links públicos** (topo): dois cards — **Pré-Contrato (comum)** ("Festas e
  eventos de pessoa física") e **Contrato Corporativo** ("Empresas / pessoa jurídica") — cada um
  com a URL pública em campo somente-leitura (`{origin}/catalogo/f/pre-contrato` e
  `/catalogo/f/corporativo`, servidas por `apps/public` sob `/catalogo/*`), **"Copiar link"** com
  confirmação inline "✓ Copiado" (+ `aria-live`), **"Abrir"** em nova aba e, só para SUPERADMIN,
  **"✎ Editar campos deste formulário"**.
- **Cartões de situação (feature 220)**: cinco cartões-filtro clicáveis entre os links e a
  tabela — **Todas · Festa futura sem evento (vermelho quando > 0) · Sem evento · Sem cliente ·
  Vínculo ambíguo** — com contagem grande (`counts` do próprio `GET /api/formularios/respostas`).
  Clicar filtra a tabela no servidor (`?filtro=`) e limpa a busca; "Festa futura sem evento"
  ordena pela data da festa (mais urgente primeiro) — é o caso "a cliente acha que está fechado
  e o evento não existe".
- **Tabela densa de respostas** (colunas): **Contratante** (nome + telefone), **Formulário**
  (badge), **Data do evento** (`event_date`), **Recebida em** (`created_at` com **data e hora**,
  `DD/MM/AAAA HH:mm`), **Situação** (badges — verde "Cliente: `<nome>`" / âmbar "Sem cliente";
  verde "Evento vinculado · auto|manual" / âmbar "Sem evento" / **vermelho "⚠ Sem evento — festa
  dd/mm/aaaa"** quando a festa é futura, com a linha inteira em `bg-red-50`; âmbar "Revisar
  vínculo" quando a automação marcou ambíguo) e **Ver**. Rola dentro do próprio contêiner no
  mobile.
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
  - **Alternador de visualização Cards ⇄ Árvore ⇄ Personagens**, persistido em `localStorage`
    (`manto_admin_catalogo_view`); trocar o modo limpa a seleção.
  - **Cards** (`CatalogCardGrid`): grade de Temas com capa, status e **kebab menu** (`KebabMenu`)
    de ações por card.
  - **Árvore** (`CatalogTreeView`): Tema expansível com os Personagens filhos recuados e guia de
    hierarquia; por linha de Personagem — selecionar, ativar/inativar, excluir e
    **"+ Vincular Ficha"** (associação rápida).
  - **Seleção múltipla + barra flutuante de ações em massa** (`CatalogBulkActionBar`): aparece com
    1+ selecionados e some ao zerar. Ações: **Mover para…** (só para Personagens — um Tema não tem
    pai neste modelo), **Inativar**, **Excluir** (com confirmação em `Modal`).
  - **Personagens** (`CatalogPersonagensView`, feature 235): as outras duas visões olham pelo
    produto e pela hierarquia e repetem o mesmo personagem uma vez por tema; esta olha **pelo
    personagem** — uma linha por identidade. Por linha: foto, nome, ficha vinculada (ou o selo
    vermelho de pendência), chips dos temas em que aparece (`×N` quando o tema tem mais de uma
    aparição), quantidade de figurinos iguais, manutenção aberta e **"Usar em outro tema"**.
    - **A identidade é a ficha de figurino**, não o nome — é ela que diz que o Gatuno da Gabby e o
      da Gabby Humanizada são o mesmo. **Personagem sem ficha não pode ser reaproveitado** (não há
      o que afirme a igualdade), e é isso que o selo vermelho comunica.
    - **Termômetro clicável** no topo: personagens · aparições · com ficha · sem ficha · em mais de
      um tema · **fichas do acervo ainda fora do catálogo** (588 de 616 hoje). Os contadores de
      "sem ficha" e "em mais de um tema" filtram a lista.
    - Alerta de logística quando um tema pede mais aparições simultâneas do que existem figurinos
      (ex.: "Astronauta ×2" com 1 figurino).
    - Neste modo a busca é **client-side** e os filtros de categoria/status somem: a lista de temas
      precisa vir inteira, porque é dela que sai o destino do "usar em outro tema".
  - Indicador **"Sem ficha vinculada"** nos Personagens pendentes.
  - Filtros: busca, categoria e status (todos/ativos/inativos).
- **API**: `GET /api/admin/catalogo` (+ `/tags`, `/personagens`) ·
  `POST /api/admin/catalogo/<id>/personagens/reaproveitar` ·
  `POST /api/admin/catalogo/personagens/mover-em-massa` ·
  `PATCH|DELETE /api/admin/catalogo/personagens/<id>` ·
  `POST /api/admin/catalogo/<id>/toggle-ativo`.

#### `/admin/catalogo/novo` e `/admin/catalogo/:id/editar` — Tema do Catálogo
- **UX**: nome, slug, descrição HTML curta, categorias, `is_active`, **URL de vídeo**
  (Drive/MP4/Vimeo — URL não reconhecida é recusada com erro **no campo**), **tags como
  `ChipInput`** (Enter ou vírgula vira chip removível, com autocomplete das tags já usadas no
  catálogo — `GET /api/admin/catalogo/tags`).
- **Galeria de fotos** (`CatalogPhotoManager`, refeita na 234): **uma grade só** para fotos
  salvas e recém-escolhidas (estas com selo "nova"). **A primeira foto é a capa** — não existe
  mais campo de capa separado; "★" é atalho de "mover para a 1ª posição". Reordena **arrastando
  por ponteiro** (mouse e toque, as vizinhas se reorganizam ao vivo) ou pelos botões ‹ › de cada
  foto; remoção fica pendente até salvar, com desfazer. Arrastar arquivos do desktop para a grade
  adiciona fotos. Selo "alterações não salvas" enquanto houver ordem/remoção pendente.
- **Arrastar uma foto já salva até um Personagem** faz ele adotá-la como foto — o hit-test é por
  atributo (`data-catalog-character-drop`), e a mutação mora na página, não no painel.
- **Painel de Personagens** (`AdminCatalogCharacterPanel`): adicionar/editar/remover Personagem
  filho com nome, foto, URL de vídeo, ordem, ativo e **dropdown de busca da Ficha de Figurino**
  (`figurino_sheet_id`).
  - **"Reaproveitar personagem que já existe"** vem ANTES de "Novo personagem" (feature 235): busca
    nas 616 fichas do acervo (`FigurinoSheetPicker`) e traz o personagem com o nome e a foto que ele
    já tem em outro tema. É o caminho certo para "Gatuno também está na Gabby Humanizada" —
    recadastrar quebraria a conta de em quantos temas ele é usado.
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
- **Loja de Interações Virtuais** (feature 205): a receita da loja **continua na cascata da DRE** —
  Fator R, break-even e resultado líquido seguem exatos, porque é dinheiro que entrou. O que sai
  são os indicadores **de evento** (ticket médio e "A Receber de clientes"): dezenas de microvendas
  de 10 minutos ao lado de shows completos não distorcem só a média, mudam a leitura que a equipe
  faz do próprio desempenho. Na coluna analítica a loja aparece como **barra própria** em Receita
  por Tipo (identificada, nunca diluída dentro de SHOW) e num **card consolidado** com vendas,
  receita e ticket do canal, mais o botão "Incluir a loja nos indicadores de evento" — opt-in
  explícito, `?incluir_loja_virtual=1`. Venda virtual **nunca** gera comissão.
- **API**: `GET /api/financeiro/dashboard?incluir_loja_virtual=`.
- **Vínculos**: cada linha de evento/auditoria/recebimento leva a `/events/<id>`; a linha de
  Gastos Recorrentes do DRE reflete os lançamentos de `/gastos/recorrentes`.

#### `/financeiro/pagamentos` — Planilha de Pagamentos *(paridade restaurada na feature 189; visualização e filtro por faixa na feature 194; celular, busca e janela de adiantamentos na 226)*
- **Acesso**: `FINANCEIRO`, `SUPERADMIN`.
- **UX**: itens de cachê, salário, gasto, BV, comissão e contas recorrentes em uma planilha
  única, na ordem de colunas clássica — **checkbox** (com "selecionar tudo") · **vencimento** ·
  **descrição detalhada** (badge do tipo + descrição do item, com botão de cópia) · **favorecido**
  em negrito · **valor** em BRL (com cópia do valor cru `1234,56`) · **chave PIX** com o tipo
  (CPF/CNPJ/E-mail/Telefone/Aleatória) e botão de cópia · **situação**. Os botões de cópia dão
  feedback "✓" temporário e anunciam por `aria-live`; **export CSV**. Trocar o mês limpa filtro,
  busca e seleção.
- **Duas apresentações do mesmo item** *(feature 226)*: a **tabela** só existe de `xl` (≥1280px)
  para cima — abaixo disso os itens viram **cartões** (1 coluna no telefone, 2 de `md` para cima),
  com o mesmo dado empilhado: tipo + vencimento + faixa · descrição (link do evento) · favorecido ·
  valor grande com cópia · chave PIX em linha própria (`break-all`) · seletor de situação de 44px ·
  botão de adiantamentos. O corte é em `xl` e não em `lg` porque a partir de `lg` a sidebar de
  256px deixa só 768px de conteúdo, e a tabela pede 1040px — era exatamente aí que a rolagem
  lateral escondia favorecido, PIX e situação. `PagamentoRow`/`PagamentoCard` leem faixa, cor e
  rótulo de `lib/pagamentos.ts` (fonte única), então nunca contam histórias diferentes.
- **Navegação de mês** *(feature 226)*: setas ‹ › ao lado do seletor de mês (o controle nativo de
  `input[type=month]` é o alvo mais difícil de acertar com o dedo). O título da lista mostra o mês
  por extenso — "Itens de agosto de 2026 (N)".
- **Busca** *(restaurada na feature 226; existia na planilha Jinja e não veio na migração para
  React)*: campo com lupa, botão de limpar e resumo vivo **"N itens · R$ X"** da seleção
  visível. Casa sem acento e sem caixa contra evento, favorecido, tipo, função/sublabel, data
  (`dd/mm/aaaa` e ISO), PIX, situação e valor — este **duas vezes**: formatado (`1.234,56`) e cru
  (`1234,56`, como se digita conferindo o extrato). Cada palavra é uma restrição que **se soma**
  (E), então "joao 1500" funciona; a versão Jinja casava a frase inteira e não achava nada. O
  índice é montado a partir do **dado** (uma vez por resposta da API), não do `textContent` das
  células como na versão Jinja — por isso a mesma busca vale para a tabela e para os cartões.
  Combina com o filtro de faixa (E).
- **Adiantamentos de salário em janela sobreposta** *(feature 226)*: o botão "✎ Adiantamentos" da
  linha/cartão abre um `Dialog` do `@manto/ui` com bruto · total adiantado · líquido a pagar, a
  lista do que já foi lançado (data, valor, link do comprovante, remover com confirmação em dois
  toques — sem `window.confirm`) e o formulário de novo adiantamento (`MoneyInput`, data de hoje,
  `FileUpload` de comprovante obrigatório). Antes era um `<details>` dentro da célula "Valor":
  no desktop obrigava a rolar a planilha de lado para achar o formulário e no celular ele nascia
  com 28px de largura. A janela recebe o item **da query** (não uma cópia em `useState`), então o
  total se atualiza sozinho depois de gravar; salário 100% adiantado troca o formulário por
  explicação + o caminho para liberar espaço. Teto de valor validado no cliente com a mesma regra
  do backend (soma dos adiantamentos ≤ salário bruto).
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
  marcada ganha barra lateral roxa. Abaixo de `xl` a barra vira **rodapé fixo** com rótulo curto
  (Pago · Banco · Não pago) e ícone para excluir/limpar — ancorada no topo da lista ela saía da
  tela no primeiro rolar, e com os rótulos longos comia 146px de um telefone de 812px (feature
  226). A seleção sobrevive ao filtro/busca **de propósito**, então a barra avisa quando parte
  dela está escondida: "(N fora do filtro/busca)".
- **Excluir pede confirmação em diálogo** *(feature 228)*: `ConfirmDialog` do `@manto/ui` com a
  contagem, **a soma em BRL** e o aviso de que não dá para desfazer — e, quando a seleção tem item
  escondido pelo filtro ou pela busca, uma linha em vermelho dizendo que ele vai junto. Era
  `window.confirm`, que não mostrava valor nem o que estava fora da tela; virou risco de verdade
  na 226, quando o botão passou a ser um ícone de lixeira de 44px encostado no "limpar seleção",
  num rodapé fixo de celular. O erro da API aparece dentro do diálogo, que fica aberto para nova
  tentativa.
- **API**: `GET /api/financeiro/pagamentos` · `POST .../set-status`, `.../bulk-action`,
  `.../salary/<id>/advance`, `.../salary/advance/<id>/delete` · `GET .../export`. Nem a 194 nem a
  226 criaram ou alteraram endpoint — as duas são de apresentação sobre o payload existente.

#### `/gastos` — Gastos Extras
- **Acesso**: staff para lançar; aprovar/rejeitar em `_require_financeiro()`.
- **UX**: fluxo criar → aprovar/rejeitar → reembolsar, com vínculo opcional a evento (feature 179
  trouxe RBAC e edição).

- **Feature 256**: gasto gerado pelo auditor de marketing mostra, abaixo da descrição, o bloco
  "Gerado pelo auditor de marketing — <plataforma> <mês>" com as linhas por campanha, o total
  reportado pelas plataformas, a rodada de origem e o selo "atualiza até aprovar" / "congelado".
  Nasce pendente e sem comprovante — anexar a fatura do cartão antes de aprovar.

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
| `/orcamento` | Calculadora de Orçamento | `COMERCIAL`, `SUPERADMIN` | layout clássico de duas colunas assimétrico (1/3 dados do evento + segurança de agenda, 2/3 equipe/ajustes/resultado); **cálculo 100% reativo** — sem botão "Calcular", qualquer alteração recalcula (debounce ~400ms); alerta "Já na agenda neste dia" abaixo da Data (evita venda em dobro de personagem); painel "Personalizar valores" (valor final ou multiplicador, por duração); contador de itens no link "Histórico de Orçamentos"; campo **Local/Endereço do evento** com **`GoogleAddressInput`** e botão **"Calcular km (Maps)"** ao lado de *Km (ida)*, que preenche a distância pela Distance Matrix (feature 195 — antes o KM aqui era 100% manual); escolher uma sugestão do Google com um modo fora de SP ativo já dispara o cálculo. **Deslocamento em duas etapas** (feature 262, no lugar da checkbox "Evento Fora de São Paulo"): "Evento em São Paulo" (padrão) × "Evento fora de São Paulo"; marcando fora, o painel dourado abre com a escolha "Por nossa conta" (padrão) × "Por conta da cliente" — no modo cliente o painel vira "Adicionais — Fora de SP", esconde tipo de transporte/carretinha/nº de carros (km e colaboradores ficam) e o veículo sai da conta. Salvar no histórico, "Ver memória de cálculo"; lê `?recalcular_id=` para reabrir um orçamento salvo com os campos preenchidos (feature 191, sobre a base da feature 190; snapshot antigo fora de SP reabre como "por nossa conta") |
| `/events/cancelamentos` | Exclusões e cancelamentos | `SUPERADMIN` | fila com os pedidos de exclusão do Comercial aguardando decisão e o histórico de eventos cancelados, com o valor e a situação da devolução de cada um. É a **única porta de entrada** para um evento cancelado — ele sai da agenda de propósito (feature 224). Declarada **antes** de `/events/:id` no `App.tsx`, senão `:id` casaria com "cancelamentos" |
| `/orcamento/:id` | Orçamento gerado | `COMERCIAL`, `SUPERADMIN` | destino de "Gerar Orçamento" e de "Abrir orçamento" no histórico (hotfix 210, sucessora de `orcamento/resultado.html`): mensagem de WhatsApp copiável, resumo por duração, detalhamento do transporte quando fora de SP (no modo "deslocamento por conta da cliente" o tile "Veículo" some e aparece a nota "van/carro não incluído" — feature 262), memória de cálculo e envio do PDF por e-mail. **Feature 266**: ganhou **Criar evento** (`/events/new?orcamento_id=`) como única ação sólida da barra — esta é a tela onde o "sim" da cliente chega, e converter exigia voltar ao histórico e reencontrar a linha. Rota declarada **depois** de `/orcamento/historico` e `/orcamento/configuracoes` — `:id` casaria com elas |
| `/orcamento/historico` | Orçamentos | `COMERCIAL`, `SUPERADMIN` | tabela densa com filtros avançados (data, valor, vendedor, tipo), PDF, envio por e-mail, exclusão; **Abrir orçamento** (`/orcamento/:id`), **Criar evento** (`/events/new?orcamento_id=`) e **Recalcular** (`/orcamento?recalcular_id=`), feature 190 |
| `/orcamento/configuracoes` | Config. Preços | `SUPERADMIN` | `SiteSetting.pricing_config` + personagens especiais, em tabelas densas (feature 190) |
| `/educamanto` | Calculadora EducaManto | `COMERCIAL`, `SUPERADMIN`, `ENSAIO`, `REVENDEDOR_EDUCAMANTO` | feature 235 — por responsabilidades: seletor de **musical**, 4 blocos Manto×Contratante com tooltip (textos de `pdf_textos.py` via `/api/educamanto/textos`), **multi-páginas** (abas; nova página = cópia da atual; musicais podem diferir), equipe técnica da matriz visível, cards Sem/Com NF + **à vista (−5%)**, observação (2.000 chars), transporte novo (checkbox fora de SP → 2 vans; dentro de SP caminhão incluso), **contratação Manto embutida** (Comercial/Superadmin; `PerformersEditor`/`AcrescimosEditor` compartilhados + durações 1h–4h/extra; totais combinados com NF única sobre a soma), breakdown de custos **só para superadmin** (corte na API); mantém `?musical_id=`/`?package_id=`, `?recalcular_id=` (v2 restaura tudo; v1 mapeia pacote→musical com aviso), Data da apresentação + alerta de agenda. **Feature 239**: card "Contratação Manto" reposicionado para logo após "Dias e ensemble" (descoberta — no fim da coluna ninguém achava); a aba da página marca **"+ Manto"** quando a contratação está ativa (`Página N · Nome + Manto`); tooltips dos 4 blocos viraram **`InfoTip`** (hover/clique/toque/teclado, com fallback pt-BR e estado de erro/carregamento em vez de sumir enquanto os textos não chegam); `contratacao_manto` é enviada ao servidor sempre que ativa, mesmo sem duração marcada (antes o payload virava `null` em silêncio e o orçamento saía sem a parte Manto) — "Gerar orçamento" fica desabilitado com aviso inline nesse caso; campo "Extra (h)" de 1 a 4 marca o checkbox de duração correspondente em vez de descartar o valor; "Nova Página" faz cópia profunda da contratação (performers/acréscimos não ficam mais compartilhados entre páginas); `event_location` entra no payload da contratação; banner dourado sob os cards "Sem Nota Fiscal"/"Com Nota Fiscal" avisando que esses dois valores não incluem a contratação Manto quando ela está ativa (usar os totais combinados) |
| `/educamanto/musicais` · `/novo` · `/:id/editar` | Musicais EducaManto | ver: `COMERCIAL`, `SUPERADMIN` (comercial **sem custos/margens**); gerir: `SUPERADMIN` | feature 235 — substitui `/educamanto/pacotes`: cards com equipe/ensaios (custos só p/ superadmin), Usar, CRUD + duplicar com `ConfirmDialog`; form com personagens/produção/ensaios (mín. 2), custos por cenário de som/iluminação/cenário, alimentação e ensaios por pessoa, itens sempre inclusos |
| `/educamanto/historico` | Histórico EducaManto | mesmos da calculadora | tabela densa; Ver (Dialog com o snapshot), Baixar PDF e **Recalcular** (`/educamanto?recalcular_id=`), feature 190 |

---

### A.8 Sistema

| Rota | Tela | Acesso | Destaques |
|---|---|---|---|
| `/admin/usuarios` · `/novo` · `/:id` | Usuários | `SUPERADMIN`, `FINANCEIRO` | papéis, PIX, salário (`SalaryHistory`), conceder acesso, reset de senha, exclusão; usuários "apenas pagamento" (`has_access=False`). **Feature 218**: a lista virou tabela com busca, filtros combináveis (papel · situação · frequência), ordenação e resumo de folha do mês; a ficha virou duas colunas e cada faixa do histórico salarial tem **corrigir/excluir inline (só SUPERADMIN)**, que realinha a planilha de pagamentos |
| `/admin/configuracoes` | Administração | `SUPERADMIN` | `SiteSetting`: cores/logo, comissão padrão, responsável EducaManto, imposto, Fator R, endereço base, ClickSign, e-mail, anonimato de avaliações, WhatsApp dos formulários |
| `/admin/logs` | Logs | `SUPERADMIN` | `AuditLog` |
| `/rh` | Painel de RH (`RhDashboardPage`, `App.tsx:130`) | **`SUPERADMIN` na prática** | ⚠️ Única tela do sistema cujo endpoint usa o **segundo mecanismo de RBAC** — `current_user.has_permission('rh.view')` (`app/api/rh_read.py:20`), código de permissão, não `RoleName`. E `rh.view` **nunca é semeado** (`seed.py` só cria `user.manage`), então todo mundo que não é SUPERADMIN recebe 403. Ver `docs/01` §4.3 e `docs/05` §7.1 |
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
  (`WishlistFloat`) sempre visível. A capa do card vem em **variante** (feature 270): `src` 640 +
  `srcset` 320/480/640 + `sizes` da grade real (`grid-cols-2 sm:3 lg:4`; no celular a coluna real,
  `calc(50vw - 32px)`) — o navegador pede 320/480 no celular e 640 no desktop em vez do original. Na grade de categoria (`large`) o `sizes`
  é o da grade de 2/3 colunas.
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
  - **Quadro da mídia com teto e piso (feature 211)**: o palco vive entre **380px** e
    **`min(62vh, 620px)`**, garantido em CSS (`min-height`/`max-height`), com a foto inteira por
    `object-contain`. Antes só havia teto: retrato alto tomava a tela e paisagem larga virava uma
    tira, cada produto abrindo de um jeito. As duas colunas do grid usam **`min-w-0`** — sem
    isso, `min-width: auto` do item de grid deixava uma foto de arquivo grande espremer a coluna
    do texto (título quebrado, tags empilhadas, botões virando bolinhas).
  - Seção **"Elenco Individual"** (`CharacterGrid` + `CharacterCard`): um card por Personagem
    filho ativo, com foto/preview, nome e **"+ Adicionar à lista"** próprio. Tema sem Personagens
    → a seção **não é renderizada** (sem espaço vazio).
  - **"Adicionar à lista"** no cabeçalho adiciona o **pacote completo** como item único.
  - Botão de **copiar link do Personagem** (alvo de toque corrigido para mobile).
  - Open Graph usa a foto de `position = 0` do Tema.
  - **Miniaturas por largura (feature 270)**: a tira de miniaturas da `ProductGallery` (64px)
    pede `assetUrl(url, { largura: 128 })` em vez do original (antes, abrir um produto com 8
    fotos baixava 8 originais para desenhar 8 quadradinhos); o palco continua no original.
    `CharacterCard` usa `srcset` 320/480/640 como o `ProductCard`. Servidas por
    `/catalogo/midia/t/<largura>/<arquivo>` (ver `docs/01` §3).
- **API**: `GET /api/catalogo/<slug>`.

#### `/catalogo/lista-desejos` — Lista de Interesse
- **UX**: lista persistida em **`localStorage`** (degrada sem quebrar em modo privado/cota);
  revisar itens e **enviar por WhatsApp** (`api.whatsapp.com/send?phone=...&text=...`), com o
  número vindo de `SiteSetting` no payload do catálogo.

#### `/cadastro` e `/cadastro/enviado` — Cadastro de Talento
> **Endereço canônico na RAIZ do domínio** (hotfix cadastro-raiz), nos hosts `app.` e `portal.` —
> é o link divulgado às artistas, herdado do formulário Jinja aposentado. O mesmo bundle da
> vitrine atende `/catalogo/cadastro/*` (e-mails de confirmação antigos); o roteador escolhe o
> `basename` pela URL (`apps/public/src/App.tsx`). O upload copia cada arquivo para a memória na
> escolha — imune ao `ERR_UPLOAD_FILE_CHANGED` do Chrome que custou um formulário inteiro.
- **UX**: formulário público de candidatura; `GET /api/cadastro/check-cpf` valida duplicidade em
  tempo real (estrangeiro grava `cpf = NULL`). Cria `Talent` com `status = "pending"`.
- **Confirmação de email (feature 219)**: o campo de e-mail avisa "você quis dizer gmail.com?"
  quando o domínio é um engano conhecido (`hotmail.con` é caso real) — **avisa, não bloqueia**.
  Depois do envio, a tela de sucesso mostra o endereço para releitura e permite **corrigir só ele
  e reenviar**, autenticada pelo par `id` + `verify_token` que veio na resposta. A ordem é
  deliberada: o `Talent` já está gravado quando a confirmação entra em cena, então errar o email
  nunca custa as fotos, o documento e o formulário inteiro.

#### `/cadastro/confirmar/:token` — Confirmação do e-mail (também em `/catalogo/cadastro/confirmar/:token`)
- **UX**: destino do link do email. Confirma ao carregar e carimba `email_verified_at`; o token é
  de uso único, então o segundo clique cai em "Link já utilizado" — tratado como sucesso tardio,
  não como erro. A ficha do talento passa a mostrar "✓ confirmado" ao lado do e-mail.
- **API**: `POST /api/cadastro/confirmar`.

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
| `/portal/agenda` | Próximos eventos + histórico recente | Dia da semana + "amanhã"/"em 5 dias"; alerta de alteração com botão **Ciente**; link para a ficha de figurino **só quando há ficha para aquela pessoa ver** (`has_figurino`, feature 227); nos itens do **histórico**, o mesmo link de avaliar da aba Histórico (`RatingLink`, feature 229); lista escalação **não recusada** (aceita, pendente ou sem convite — feature 230) |
| `/portal/convites` | Convites de casting pendentes | Botões **Aceitar** / **Recusar** (recusa pede confirmação); alimenta o contador da aba |
| `/portal/historico` | Histórico completo de apresentações | Somatórios recebido / a receber / total; cachê + deslocamento por evento; link para avaliar via `RatingLink` (o mesmo da Agenda desde a 229) |
| `/portal/perfil` | Dados pessoais, **medidas corporais**, PIX e portfólio | Medidas alimentam o módulo de Figurino; até 3 fotos de atuação + links (Vimeo/YouTube) |
| `/portal/fotos-documentos` | Foto de rosto, corpo inteiro, foto do documento (RG/CPF/CNH — card novo da feature 264) e CNH | Preview do arquivo atual antes de substituir (fotos); documento e CNH mostram sucesso apos envio |
| `/portal/eventos/:id/figurino` | Ficha de figurino do papel no evento | Peças, orientações e fotos; foto vem de `/portal/photo/<file>` (rota Jinja, mesma sessão). **Coordenador vê o elenco inteiro** com o nome de quem interpreta cada personagem (feature 227) |
| `/portal/eventos/:id/avaliar` | Avaliar o evento | Etapa 1 nota geral (abaixo de 4 exige comentário); etapa 2 opcional por categoria e por pessoa; janela de 7 dias para avaliar, 30 para editar. Etapa 2 é o **destino padrão** da etapa 1 desde a 232 (rolagem até o bloco), com desvio explícito para quem só quer a nota geral |
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
> sessão de talento, e o app React depende dela. Por isso ela é um dos filtros do proxy reverso
> de `frontend/server.js` (feature 206) — casada **antes** do mount `/portal`, senão o fallback
> do bundle do portal devolveria `index.html` no lugar da imagem.
>
> **Toda** imagem que o portal exibe tem de sair por aqui, não por `/uploads/<file>`: aquela rota
> é `@login_required` do Flask-Login (sessão de **staff**), e quem está no portal só tem
> `session["talent_id"]` — o `<img>` recebe um 302 para a tela de login do staff e vira ícone
> quebrado. Até a feature 227 as fotos **do próprio talento** (avatar, perfil, fotos &
> documentos, portfólio, tela de avaliação) devolviam o caminho cru e quebravam para 255 dos 259
> talentos; a ficha de figurino já fazia certo desde a 176. A conversão agora é uma função só —
> `portal_ops.portal_photo_url()` — usada por todos os serializadores do portal. Documento de
> talento (`talent_docs`) fica **de fora** de propósito: não está em `PORTAL_PHOTO_SUBFOLDERS`.

O login do portal não tem mais como cair no Jinja: `must_redirect_to_classic` saiu do payload de
`POST /api/portal/auth/login` na 206. Quem tem senha temporária ou termo pendente é guiado pelos
`pending_steps` dentro do próprio React.

**Como o talento chega.** `portal.mantoproducoes.com.br` continua sendo o endereço divulgado, mas
agora aponta para o serviço do frontend: qualquer caminho fora de `/portal` recebe 302 para
`/portal` + o caminho original (ver `01_SISTEMA_E_BANCO.md` §5.2.2). Ou seja,
`portal.mantoproducoes.com.br/` abre a agenda do portal React, e o link de redefinição de senha do
e-mail (`/reset-password/<token>`) chega inteiro em `/portal/reset-password/<token>`.
`app.mantoproducoes.com.br/portal/*` também funciona — é a mesma origem.

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

   Catálogo (Tema) ──── marketing_post_temas (N:N) ────► Postagem de Marketing
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

---

## Padrões transversais do app interno

### Espaçamento da página *(auditado em 2026-08-11)*

`AppLayout` renderiza `<main className="min-h-screen">` **sem padding nenhum** — o espaçamento é
responsabilidade de cada página. Quem esquece nasce colado na barra lateral de 256px, e foi o que
aconteceu com seis telas (as duas de Produção de Figurinos e as quatro de Interações Virtuais).

A raiz de toda página é:

```tsx
<div className="mx-auto max-w-<X> space-y-4 p-4 sm:p-6">
```

`p-4 sm:p-6` é o padrão em **57/57** páginas. O `max-w` varia com o conteúdo: `max-w-[1400px]` e
`max-w-6xl` para listas e tabelas, `max-w-5xl` para formulários, `max-w-lg` para telas de um
campo só. **Os ramos de carregamento e de erro levam o mesmo invólucro** — senão o esqueleto
aparece deslocado e a tela "pula" quando os dados chegam.

### Escolher uma ficha de figurino

Existe **um** componente: `components/FigurinoPicker.tsx`, sobre o `Combobox` do `@manto/ui`.
São 616 fichas (612 com foto): uma lista alfabética é inviável e a escolha é visual por natureza,
então cada resultado traz a miniatura quadrada (Princípio X.2). O `Combobox` já dá filtro
sem acento, teto de 30 resultados, limpar e navegação por teclado — nada disso se reimplementa.

| Onde | Contexto |
|---|---|
| Elenco do evento (`EventDetail/FigurinoSection`) | Vincular a ficha ao cargo |
| `/admin/catalogo` → vincular figurino | Ligar personagem do catálogo à ficha |
| Painel de personagens do tema (3 pontos) | Vincular, reaproveitar em outro tema, criar |
| `/figurinos/producao` → novo pedido | Qual figurino é o conserto (manutenção) |
| `/compras` → novo pedido | Para qual figurino é a compra (opcional) |

Histórico: a 209 criou o `FigurinoSheetPicker` (lista própria), a 215 criou o `FigurinoPicker`
(design system) e a **225d unificou nos dois últimos pontos da tabela, que ainda eram `<select>`
cego**, apagando o `FigurinoSheetPicker`. Duas buscas da mesma coisa com aparências diferentes é
exatamente o que o princípio de consistência proíbe.

**Pegadinha ao testar por script**: no `Combobox` o `role="option"` fica no `<li>`, mas o
`onClick` mora no `<button>` de dentro. `document.querySelector('[role=option]').click()` não
seleciona nada e o campo volta nulo sem erro — use `[role=option] button`.


### Feature 236 (branch `236-cache-por-duracao`, 2026-08-14)

- **`/events/new`**: card do orçamento vinculado ganhou **"Outra (h)"** (≥5) ao lado dos botões
  1–4h — pré-carrega a duração extra do orçamento e mostra o preço de referência; a duração
  escolhida vai para a criação e define os cachês/tetos dos papéis (recalculados no servidor).
- **Detalhe do evento → Elenco (`CastingSection`)**: sem mudança visível (2ª rodada do dono):
  o cachê NASCE VAZIO e nenhuma sugestão é exibida — o valor da régua age só como TETO
  invisível (`cache_cap`), imposto como sempre. Expor a sugestão ancoraria o casting no máximo
  (quem escala pode se escalar).


### Feature 237 (branch `237-solicitar-ficha`, 2026-08-14)

- **`FigurinoPicker` (porta única da busca de ficha)**: rodapé ganhou "Não achou? Solicitar
  ficha" → dialog com o nome pré-preenchido com o texto digitado (novo `onInputValueChange` do
  `Combobox`, que observa sem assumir a busca) + observação; cria pedido tipo "Ficha" e confirma
  na própria tela. O `ElencoBlock` (criação E edição de evento) trocou seu Combobox cru pelo
  picker — o resquício que tinha escapado da unificação da 225d.
- **Produção e Compras**: fila/badge mostram o tipo "Ficha" (rótulo do servidor); filtros do
  tipo = os da manutenção; detalhe de pedido ficha esconde o painel de dinheiro e traz "Ficha
  criada (obrigatória para concluir)" com o próprio picker — concluir sem vínculo é barrado
  pelo servidor.
