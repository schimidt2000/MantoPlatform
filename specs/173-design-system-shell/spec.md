# Feature Specification: Design System Global e Shell de Aplicação (FASE A — UI/UX Parity com Jinja)

**Feature Branch**: `173-design-system-shell`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "Design System Global e Shell de Aplicação (FASE A da iniciativa 'UI/UX Parity com Jinja'). Criar o 'molde' visual da Plataforma Manto no monorepo React: tema & tokens (Manto Dark Purple #1f1a30, fundo cinza neutro, cards brancos densos), componentes de shell reutilizáveis (AppLayout com sidebar roxa/drawer mobile, PageHeader, DenseCard, MetricBadge) e aplicação do AppLayout em TODAS as rotas existentes do app interno, sem regressão funcional. Fases B (redesenho tela a tela) e C (EducaManto/Portal do Artista) virão em specs próprias."

## Contexto

A migração React (feature 144) entregou paridade **funcional**, mas as telas do beta React perderam a identidade visual do sistema Jinja clássico: a sidebar roxa institucional (`#1f1a30`) com navegação agrupada por setor, a densidade de informação, o seletor de papel "Ver como" e o acabamento dos cards. Hoje cada página React renderiza seu próprio cabeçalho solto em fundo branco genérico — não existe nenhum componente de layout compartilhado (`Grep` por `Layout|<aside|<nav` em `frontend/apps/internal/src` retorna vazio).

Esta feature cria o "molde" visual global (design system + shell) e o propaga por **todas as 35 páginas** existentes do app interno. O redesenho interno de cada tela (dashboard com donuts, agenda em grade mensal, mosaico de talentos) fica para a FASE B; EducaManto completo e Portal do Artista para a FASE C.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Shell institucional em todas as telas do staff (Priority: P1)

Qualquer membro do staff autenticado, ao navegar por qualquer tela do beta React (dashboard, agenda, talentos, figurino, financeiro, vendas, clientes, RH, revisão, admin, EducaManto), vê a mesma moldura institucional da Manto: sidebar fixa roxa escura no desktop (logo Manto, navegação agrupada por setor — na mesma ordem e agrupamento do sistema clássico: Geral/topo, Casting, Produção, Comercial, Financeiro, Ferramentas, Sistema), conteúdo sobre fundo cinza neutro, e no mobile um menu retrátil (drawer) acionado por botão hambúrguer.

**Why this priority**: é o coração da feature — devolve a identidade visual perdida e elimina as páginas de fundo branco genérico em uma única tacada estrutural. Sem o shell, nenhum outro item da FASE A tem onde aparecer.

**Independent Test**: logar no app interno, visitar cada uma das rotas registradas e verificar que todas renderizam dentro do mesmo shell (sidebar visível no desktop, drawer no mobile), com o item de navegação da seção atual destacado, e que toda a funcionalidade pré-existente das telas continua operando.

**Acceptance Scenarios**:

1. **Given** um usuário staff autenticado em viewport desktop, **When** visita qualquer rota do app interno, **Then** vê a sidebar roxa escura fixa à esquerda com logo Manto, grupos de navegação por setor e o item correspondente à rota atual destacado.
2. **Given** o mesmo usuário em viewport mobile (<768px), **When** abre qualquer tela, **Then** a sidebar não ocupa espaço; um botão hambúrguer abre um drawer com a mesma navegação, que fecha ao navegar ou tocar fora.
3. **Given** um usuário sem determinado papel (ex.: sem FINANCEIRO), **When** olha a navegação, **Then** só vê os grupos/itens que seu papel efetivo permite acessar (mesma regra de visibilidade do menu do sistema clássico).
4. **Given** qualquer tela já migrada (ex.: criar evento, editar talento, pagamentos), **When** o usuário executa as ações principais da tela dentro do novo shell, **Then** tudo funciona como antes — sem regressão.

---

### User Story 2 - Seletor de papel "Ver como" no rodapé da sidebar (Priority: P2)

Um SUPERADMIN precisa validar o que cada setor enxerga. No rodapé da sidebar, ele vê o bloco "Ver como:" com os papéis disponíveis; ao escolher um papel, a navegação e as telas passam a refletir o que aquele papel vê, com indicação clara de que a impersonação está ativa e opção de voltar ao papel real. Usuários não-SUPERADMIN não veem o seletor. O rodapé também mostra o usuário logado (nome + papel, link para perfil) e o botão de sair.

**Why this priority**: é funcionalidade real do sistema clássico usada para auditoria de RBAC — sem ela o shell React fica atrás do Jinja em capacidade, não só em estética.

**Independent Test**: como SUPERADMIN, escolher "Ver como: CASTING" e verificar que a navegação encolhe para o que CASTING vê e que as telas respeitam o papel simulado; limpar e verificar retorno ao estado real.

**Acceptance Scenarios**:

1. **Given** um SUPERADMIN real, **When** seleciona um papel no "Ver como", **Then** a navegação e o conteúdo passam a refletir o papel simulado, o rodapé indica o papel ativo e aparece a opção de limpar a simulação.
2. **Given** uma impersonação ativa, **When** o SUPERADMIN limpa a simulação, **Then** tudo volta ao papel real imediatamente.
3. **Given** um usuário não-SUPERADMIN, **When** olha o rodapé da sidebar, **Then** o seletor "Ver como" não existe; vê apenas seu usuário e o sair.

---

### User Story 3 - Tema global e vocabulário visual denso (Priority: P2)

O time enxerga o beta com a mesma "cara" do sistema clássico: tokens de tema centralizados (roxo institucional `#1f1a30` em sidebar/elementos primários, fundo global cinza neutro, cards brancos com borda sutil e sombra leve, tipografia compacta para tabelas e badges) disponíveis para todas as telas, mais os blocos de construção reutilizáveis: cabeçalho de página padronizado (título, trilha de navegação, ações à direita), card denso com cabeçalho compacto e estatísticas, e badge métrico colorido compacto (medidas de talento, status de evento).

**Why this priority**: os tokens e componentes são o "molde" que a FASE B vai consumir tela a tela; entram já aplicados no shell e disponíveis no design system compartilhado.

**Independent Test**: inspecionar que os tokens existem no tema compartilhado (não hardcoded por tela), que `PageHeader`, `DenseCard` e `MetricBadge` estão exportados pelo design system com exemplos reais de uso em pelo menos uma tela cada, e que o fundo global das páginas deixou de ser branco puro.

**Acceptance Scenarios**:

1. **Given** o design system, **When** um desenvolvedor cria uma tela nova, **Then** consegue montar cabeçalho, cards densos e badges usando apenas componentes exportados e tokens do tema, sem CSS solto.
2. **Given** qualquer página dentro do shell, **When** renderizada, **Then** o fundo do conteúdo é cinza neutro e os cards são brancos com borda sutil e sombra leve — sem tela de fundo branco genérico.
3. **Given** um usuário com preferência de movimento reduzido, **When** navega (abrir drawer, trocar rota), **Then** as transições animadas são suprimidas.

---

### Edge Cases

- Rotas de tela cheia que não devem ganhar sidebar: `/login` permanece fora do shell.
- Rota desconhecida (fallback `*` → redirect `/`) continua funcionando dentro do shell.
- Impersonação ativa + navegação para tela que o papel simulado não pode ver: a tela responde como responderia ao papel real simulado (ex.: 403 amigável), sem quebrar o shell.
- Drawer aberto no mobile + rotação/resize para desktop: o layout se recompõe sem estado travado (sem overlay órfão).
- Sidebar com muitos grupos em telas baixas: navegação rola internamente; rodapé (Ver como/usuário/sair) permanece acessível.
- Usuário com sessão expirada: o comportamento atual do `RequireAuth` (redirect a `/login`) é preservado.
- Itens do menu clássico cujas telas ainda são Jinja (ex.: Gastos, Orçamento, Formulários admin, Avaliações de talento, EducaManto pacotes): a navegação do shell só lista rotas que existem na SPA — itens Jinja-only ficam de fora nesta fase (entram nas FASES B/C quando migrarem).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O design system compartilhado MUST expor tokens de tema centralizados: cor institucional Manto Dark Purple `#1f1a30` (sidebar/primários), fundo global cinza neutro claro, superfície de card branca com borda sutil e sombra leve, e escala tipográfica de alta densidade (tamanhos compactos para tabelas, badges e metadados).
- **FR-002**: O design system MUST exportar um componente de layout de aplicação (shell) com: sidebar fixa em desktop e drawer retrátil em mobile, logo/marca Manto, navegação agrupada por setor na mesma ordem do sistema clássico (Geral, Casting, Produção, Comercial, Financeiro, Ferramentas, Sistema), destaque do item ativo e rodapé com "Ver como", usuário logado e sair.
- **FR-003**: A navegação do shell MUST respeitar o papel efetivo do usuário (incluindo impersonação): grupos e itens só aparecem para quem pode acessá-los, com a mesma semântica de visibilidade do menu Jinja clássico.
- **FR-004**: A navegação do shell MUST listar apenas rotas existentes na SPA interna; itens do menu clássico ainda Jinja-only não aparecem nesta fase.
- **FR-005**: O seletor "Ver como" MUST permitir a um SUPERADMIN real ativar/limpar a simulação de papel, refletindo imediatamente na navegação e nas telas, com indicação visível do papel simulado; MUST ser invisível para não-SUPERADMIN. A simulação MUST ter o mesmo efeito da funcionalidade equivalente do sistema clássico (mesmo estado de sessão no servidor).
- **FR-006**: O design system MUST exportar um cabeçalho de página padronizado (título, trilha de navegação opcional, ações primárias à direita, área de filtros rápidos opcional) e ele MUST ser adotado por todas as páginas do app interno.
- **FR-007**: O design system MUST exportar um card denso (cabeçalho compacto, divisões limpas, suporte a estatísticas rápidas) e um badge métrico compacto colorido (ex.: medidas de talento "180cm • M • 40", status de evento), prontos para consumo pela FASE B; cada um MUST ter pelo menos um uso real em tela nesta fase.
- **FR-008**: TODAS as rotas autenticadas do app interno MUST renderizar dentro do shell; `/login` MUST permanecer fora. Nenhuma página pode manter cabeçalho/navegação próprios divergentes do padrão.
- **FR-009**: A adoção do shell MUST acontecer sem regressão funcional: toda ação hoje disponível em cada tela continua funcionando (mesmos fluxos, mesmos estados de loading/erro/sucesso).
- **FR-010**: O shell MUST ser mobile-first: drawer com overlay, fechamento ao navegar/tocar fora, conteúdo utilizável em viewport de celular; transições (drawer, hover, troca de item ativo) MUST usar movimento sutil e respeitar preferência de movimento reduzido do usuário.
- **FR-011**: Botões só-ícone do shell (hambúrguer, sair, fechar drawer) MUST ter rótulo acessível e dica visual (tooltip ou equivalente).
- **FR-012**: Estados de carregamento do shell (ex.: usuário/papéis ainda carregando) MUST usar skeleton/placeholder — nunca tela em branco.

### Key Entities

- **Papel efetivo**: papel real do usuário ou, para SUPERADMIN com "Ver como" ativo, o papel simulado guardado na sessão do servidor — determina navegação visível e comportamento das telas.
- **Grupo de navegação**: agrupamento setorial de itens de menu (Geral, Casting, Produção, Comercial, Financeiro, Ferramentas, Sistema), cada item com rota, ícone e regra de visibilidade por papel.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das rotas autenticadas do app interno (35 páginas hoje) renderizam dentro do shell institucional; zero páginas restantes com fundo branco genérico sem moldura.
- **SC-002**: Um usuário de cada papel (SUPERADMIN, CASTING, FIGURINO, COMERCIAL, FINANCEIRO, ENSAIO, RH) vê na navegação exatamente os itens que seu papel permite — paridade de visibilidade com o menu do sistema clássico, verificada item a item.
- **SC-003**: SUPERADMIN consegue ativar e limpar "Ver como" em menos de 3 cliques, com efeito imediato e indicação visível do papel simulado.
- **SC-004**: Em viewport mobile (375px), todas as telas permanecem utilizáveis: navegação acessível via drawer, sem overflow horizontal no shell.
- **SC-005**: Nenhuma regressão funcional nas telas existentes: as verificações funcionais das features anteriores (fluxos de criação/edição/ação) continuam passando após a adoção do shell.
- **SC-006**: Desenvolvedor monta uma tela nova padrão (cabeçalho + cards + badges) usando somente exports do design system, sem escrever CSS solto.

## Assumptions

- A ordem/agrupamento da navegação segue o `base.html` Jinja atual (fonte da verdade da identidade clássica); itens Jinja-only (Gastos, Orçamento, Formulários, Avaliações, EducaManto pacotes, Catálogo público) ficam fora do menu React nesta fase — serão adicionados quando suas telas migrarem (FASES B/C).
- "Ver como" reutiliza o mecanismo de sessão existente no servidor (`impersonate_role`), expondo-o à SPA; o comportamento efetivo de RBAC nas telas já respeita esse estado hoje (padrão das features 145+), então o shell só precisa acionar/refletir o estado.
- O endpoint de identidade atual (`/api/auth/me`) já fornece papéis e estado de impersonação suficientes para montar a navegação; qualquer complemento (ex.: ação de impersonar via API) faz parte desta feature.
- A logo Manto usada no Jinja está disponível como asset estático reaproveitável pelo frontend.
- Tema escuro global do app não faz parte do escopo (o Jinja clássico é tema claro com sidebar escura); a paridade visual é com o Jinja.
- O app público (`frontend/apps/public`) não recebe o shell de staff — mantém sua identidade própria; os tokens/moldes compartilhados ficam disponíveis para uso futuro.
