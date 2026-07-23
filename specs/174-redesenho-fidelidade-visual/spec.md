# Feature Specification: Redesenho e Fidelidade Visual das Telas Principais (FASE B — UI/UX Parity com Jinja)

**Feature Branch**: `174-redesenho-fidelidade-visual`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "Spec 174 — Redesenho e Fidelidade Visual das Telas Principais (FASE B do redesign UI/UX, sequência da Spec 173 - Design System Shell). Escopo: (1) Dashboard (/): restaurar gráficos em donut (Recharts) para distribuição financeira/status, card de resumo financeiro (receita/despesa/lucro do período) e lista de tarefas pendentes agrupada por setor (casting, figurino, financeiro etc.), usando os componentes do design system (PageHeader, DenseCard, MetricBadge) já entregues na 173. (2) Agenda (/agenda): substituir a listagem simples atual por uma grade mensal de calendário completa (visão de mês, navegação entre meses, dia atual destacado), com eventos exibidos como blocos coloridos por categoria (Ensaio, Show, Corporativo, e demais categorias existentes no sistema), mantendo os endpoints e regras de RBAC/impersonação já existentes. (3) Banco de Talentos (/talents): substituir a listagem atual por um mosaico de fotos grandes (grid responsivo de 5-6 colunas em desktop, colapsando em mobile) com badges de medidas (altura, manequim etc.) visíveis diretamente nos cards. (4) Demais subpáginas internas: revisão de alinhamento e densidade visual conforme o design system da 173, sem introduzir nova arquitetura. Fora de escopo: Portal do Artista e EducaManto completo."

## Contexto

A FASE A (feature 173) entregou o shell institucional (sidebar roxa, "Ver como", tokens de tema, `PageHeader`/`DenseCard`/`MetricBadge`) em todas as rotas — mas o *conteúdo* de cada tela permaneceu no nível de fidelidade visual da migração 144 (fundação funcional, sem redesenho). Hoje:

- **Dashboard** (`DashboardPage.tsx`) mostra apenas contadores simples ("Concluídos"/"Total") em `DenseCard` — perdeu os donuts de progresso (`--p:{{pct}}deg` em CSS puro no Jinja `home.html`), o painel "Performance" (SUPERADMIN, com seletor de período 7/30/customizado e "Entrada total" em destaque) e a apresentação em painéis colapsáveis por setor com badges de urgência (`URGENTE` ≤2 dias, `Nd` ≤7 dias) que o Jinja tem.
- **Agenda** (`AgendaPage.tsx`) já busca por mês (`useAgenda(ym)`) mas renderiza uma lista agrupada por dia, não uma grade de calendário.
- **Talentos** (`TalentsListPage.tsx`) renderiza cards horizontais com avatar circular pequeno (64px) — não o mosaico de fotos grandes do catálogo visual usado para casting rápido.

Esta feature (FASE B) fecha essa lacuna de fidelidade nas 3 telas mais usadas do dia a dia, reaproveitando os endpoints JSON já existentes (`/api/dashboard`, `/api/agenda`, `/api/talents`) sempre que possível, e documenta como extensão aditiva qualquer campo novo estritamente necessário para os gráficos. As demais 30+ subpáginas recebem apenas ajuste de alinhamento/densidade ao design system da 173 (sem redesenho de conteúdo).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dashboard com indicadores visuais e tarefas por setor (Priority: P1)

Um membro do staff (casting, figurino ou financeiro) abre a Início e vê, num único olhar: os donuts de progresso do seu setor (% de cargos de casting preenchidos, % de figurinos separados), os painéis de tarefas pendentes agrupados por setor (mesma organização colapsável do sistema clássico — Casting, Figurino, Comercial, Contas recorrentes), com badge de urgência nos itens vencendo em breve, e — se SUPERADMIN — o painel de Performance com o total de entrada (cachês) no período selecionado.

**Why this priority**: é a tela mais visitada do sistema (home) e a que mais perdeu fidelidade visual — hoje um simples contador "3/10" no lugar do donut e das tarefas detalhadas por setor.

**Independent Test**: logar com cada papel (CASTING, FIGURINO, FINANCEIRO, SUPERADMIN) e verificar que os indicadores/painéis visíveis batem exatamente com o que aquele papel via no Jinja clássico (mesmos números, mesmo agrupamento, mesmas badges de urgência).

**Acceptance Scenarios**:

1. **Given** um usuário com papel CASTING, **When** abre a Início, **Then** vê um donut de progresso de casting com o percentual concluído no centro, e abaixo um painel colapsável "Casting" com a lista de pendências, cada uma com badge `URGENTE` (≤2 dias) ou `Nd` (≤7 dias) quando aplicável.
2. **Given** um usuário com papel FIGURINO, **When** abre a Início, **Then** vê o donut de figurino e o painel de pendências de figurino, no mesmo padrão do casting.
3. **Given** um usuário com papel FINANCEIRO, **When** abre a Início, **Then** vê o painel de contas recorrentes pendentes do mês (nome, dia de vencimento, valor).
4. **Given** um SUPERADMIN, **When** abre a Início, **Then** vê todos os donuts/painéis acima (papel efetivo agregado) mais o painel "Performance" com seletor de período (7 dias / 30 dias / personalizado) e o valor total de entrada (soma dos cachês) do período selecionado.
5. **Given** um SUPERADMIN com "Ver como" ativo (papel simulado), **When** abre a Início, **Then** vê exatamente o que o papel simulado veria (sem o painel Performance, que é exclusivo do papel real SUPERADMIN) — mesma regra da 173.
6. **Given** qualquer painel de setor com pendências, **When** o usuário clica no cabeçalho do painel, **Then** o painel colapsa/expande, preservando o estado por sessão de navegação (não precisa persistir entre reloads).
7. **Given** um setor sem nenhuma pendência, **When** o painel é exibido, **Then** mostra um indicador "Tudo em dia ✓" no lugar da contagem de pendentes, em vez de um painel vazio.

---

### User Story 2 - Agenda em grade mensal de calendário (Priority: P1)

Um membro do staff abre a Agenda e vê uma grade de calendário do mês corrente (semanas em linhas, dias em colunas, dia atual destacado), com os eventos de cada dia exibidos como blocos coloridos por categoria (Ensaio, Show/SHOW, Corporativo/CORP, Receptivo & Interativo/R&I, Visita Mágica/VM, Social); ao navegar entre meses (‹ ›), a grade recarrega mantendo a mesma navegação já existente. Clicar num evento leva ao detalhe do evento, como hoje.

**Why this priority**: a visão de calendário é a forma como o time enxerga a operação do mês inteiro de uma vez — a lista atual (agrupada só por dia, em coluna única) obriga a rolar a página inteira para ter essa visão, perdendo a leitura rápida de "quantos eventos, de que tipo, em que semana".

**Independent Test**: navegar para um mês com eventos de tipos variados e verificar que cada dia da grade mostra os blocos corretos, com cor consistente por categoria, dia atual destacado, e que clicar num bloco abre o evento correto.

**Acceptance Scenarios**:

1. **Given** o mês corrente tem eventos, **When** a Agenda carrega, **Then** renderiza uma grade de 7 colunas (dom–sáb) com uma linha por semana cobrindo o mês inteiro (incluindo dias do mês anterior/seguinte para completar a primeira/última semana, visualmente esmaecidos), e o dia de hoje tem destaque visual próprio.
2. **Given** um dia com 1 ou mais eventos, **When** exibido na grade, **Then** cada evento aparece como um bloco compacto com cor de fundo correspondente à categoria (Ensaio, Show, Corporativo, R&I, Visita Mágica, Social — mesma paridade de cores do badge do Jinja `event_detail.html`) e o título/horário resumido.
3. **Given** um dia com mais eventos do que cabe visualmente, **When** exibido na grade, **Then** mostra um indicador "+N" que leva à visão do dia (ou expande a célula) — sem quebrar o layout da grade.
4. **Given** o usuário navega para o mês anterior/seguinte, **When** clica em ‹ ou ›, **Then** a grade recarrega para o novo mês reaproveitando a busca por `ym` já existente, preservando loading/erro por TanStack Query.
5. **Given** viewport mobile (<768px), **When** a Agenda é aberta, **Then** a grade se adapta (ex.: dias com scroll horizontal controlado, ou visão semanal/lista compacta) sem overflow horizontal da página.
6. **Given** o usuário clica num evento na grade, **When** navega, **Then** abre a página de detalhe do evento (`/events/<id>`), como no comportamento atual.
7. **Given** um usuário sem permissão para criar evento, **When** olha a Agenda, **Then** o botão "Novo evento" continua ausente (mesma regra de RBAC já existente, inalterada).

---

### User Story 3 - Banco de Talentos em mosaico de fotos (Priority: P2)

Um membro do casting abre o Banco de Talentos e vê um mosaico de fotos grandes (retrato) em grade de 5–6 colunas no desktop, cada card mostrando a foto em destaque, nome, e badges de medida (altura, manequim/tamanho, calçado) sobrepostos ou logo abaixo da foto — permitindo escanear visualmente muitos talentos de uma vez para decisões de casting rápidas, mantendo toda a busca/filtros/paginação/aprovação já existentes.

**Why this priority**: o casting trabalha por reconhecimento visual (silhueta, altura aparente); o card atual (avatar circular de 64px) é pequeno demais para essa tarefa e sub-aproveita as fotos de perfil já cadastradas.

**Independent Test**: abrir a lista de talentos ativos e verificar que o grid renderiza fotos grandes com badges de medida legíveis, que a busca/filtros continuam filtrando o mesmo grid, e que aprovar/rejeitar (na aba Pendentes) continua funcionando a partir do card.

**Acceptance Scenarios**:

1. **Given** a lista de talentos ativos, **When** carregada em viewport desktop largo, **Then** renderiza um grid de 5–6 colunas com foto de rosto em destaque (proporção retrato) por card.
2. **Given** um talento sem foto cadastrada, **When** exibido no mosaico, **Then** mostra um placeholder visual consistente (mesmo padrão de avatar genérico usado hoje) sem quebrar o grid.
3. **Given** um talento com altura/manequim/calçado cadastrados, **When** exibido no card, **Then** as medidas aparecem como badges compactos e legíveis sem exigir hover/clique.
4. **Given** viewport mobile (375px), **When** a lista é aberta, **Then** o grid colapsa para 2 colunas (ou 1, se necessário) sem overflow horizontal, mantendo foto e badges legíveis.
5. **Given** a aba "Pendentes", **When** exibida no mosaico, **Then** os botões "Aprovar"/"Rejeitar" continuam acessíveis por card, com os mesmos estados de loading/confirmação já existentes.
6. **Given** busca/filtros aplicados, **When** alterados, **Then** o mosaico atualiza exatamente como a lista atual atualiza hoje (mesma paginação, mesmo endpoint).
7. **Given** um talento com `warning_level` (alerta comportamental), **When** exibido no mosaico, **Then** o indicador de alerta permanece visível sobre a foto, como no card atual.

---

### User Story 4 - Alinhamento de densidade nas demais subpáginas (Priority: P3)

Um usuário navegando por qualquer subpágina interna não coberta pelas User Stories 1–3 (ex.: detalhe de evento, figurino, financeiro, clientes, RH, admin) vê consistência visual com o design system da 173: uso de `PageHeader`/`DenseCard`/`MetricBadge` onde hoje há cabeçalhos ou blocos de estatística soltos, sem mudança de fluxo ou de arquitetura.

**Why this priority**: fidelidade de "acabamento" nas telas secundárias — importante, mas sem o impacto imediato das 3 telas de uso diário acima.

**Independent Test**: amostragem de 5 subpáginas de setores diferentes (evento, figurino, financeiro, clientes, admin) e verificar que cabeçalhos/cards seguem os componentes do design system, sem CSS solto novo introduzido.

**Acceptance Scenarios**:

1. **Given** uma subpágina com cabeçalho solto (fora do padrão `PageHeader`), **When** revisada nesta feature, **Then** passa a usar `PageHeader`.
2. **Given** uma subpágina com blocos de estatística em `Card` genérico, **When** o conteúdo se encaixa no padrão de `DenseCard`, **Then** passa a usar `DenseCard`.
3. **Given** qualquer subpágina ajustada, **When** testada, **Then** nenhuma funcionalidade existente regride (mesmos fluxos, mesmos endpoints).

---

### Edge Cases

- Dashboard: usuário com múltiplos papéis (ex.: CASTING + FIGURINO) vê todos os donuts/painéis aos quais tem direito, na mesma ordem do Jinja (Casting → Figurino → Comercial → Recorrentes).
- Dashboard: setor com `total = 0` (sem nenhum cargo/figurino no período) — donut mostra 0% sem erro de divisão por zero (mesma regra do Jinja: `pct = 0 if total == 0`).
- Dashboard: período de Performance "personalizado" com data final anterior à inicial — tratar como erro de validação amigável, sem quebrar o painel.
- Agenda: mês sem nenhum evento — grade renderiza vazia (todas as células sem blocos), sem mensagem de erro.
- Agenda: evento sem `event_type` reconhecido — cai numa cor neutra/"outro", sem quebrar o bloco.
- Agenda: evento multi-dia (`start_at`/`end_at` em dias diferentes) — aparece pelo menos no dia de início; comportamento de estender pelos dias intermediários é desejável mas não bloqueante (documentar decisão se não implementado).
- Talentos: card no mosaico com nome muito longo — trunca com reticências, sem quebrar o grid.
- Talentos: resultado vazio (busca sem match) — mantém a mensagem "Nenhum talento encontrado." já existente, sem grid quebrado.
- Todas as telas: preferência de movimento reduzido do usuário é respeitada (sem animação de entrada de donuts/grade quando ativa) — mesma regra da 173 (Princípio IX).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O Dashboard MUST exibir donuts de progresso (percentual concluído) para Casting e Figurino quando o usuário tiver o papel/permissão correspondente, com o percentual numérico visível no centro do donut e a fração (concluídos/total) abaixo — mesma semântica de dados do endpoint `/api/dashboard` atual (`done`/`total` por setor).
- **FR-002**: O Dashboard MUST exibir as tarefas pendentes de cada setor visível (Casting, Figurino, Comercial quando aplicável, Contas recorrentes) em painéis colapsáveis agrupados por setor, cada painel com contagem de pendentes (ou indicador "Tudo em dia ✓" quando zero) e, nos itens de casting, badge de urgência (`URGENTE` para eventos em ≤2 dias, `Nd` para ≤7 dias).
- **FR-003**: O Dashboard MUST exibir, exclusivamente para o papel real SUPERADMIN (não durante impersonação), um painel de Performance com seletor de período (7 dias / 30 dias / personalizado) e o valor total de entrada (soma de cachês) do período selecionado.
- **FR-004**: Caso o painel de Performance exija dados agregados por período que o endpoint `/api/dashboard` atual não fornece, o Dashboard MUST consumir uma extensão aditiva do contrato (novo parâmetro de período e/ou novo campo na resposta) documentada em `contracts/`, sem remover ou alterar campos existentes.
- **FR-005**: A Agenda MUST renderizar uma grade mensal de calendário (7 colunas, uma linha por semana, cobrindo o mês inteiro incluindo dias adjacentes esmaecidos para completar semanas), reaproveitando a navegação de mês (`ym`) e o endpoint `/api/agenda` já existentes.
- **FR-006**: A grade da Agenda MUST destacar visualmente o dia atual e exibir os eventos de cada dia como blocos com cor de fundo distinta por categoria (`event_type`: SHOW, CORP, R&I, VM, SOCIAL, e Ensaio como categoria própria), com paridade de cor/rótulo com o mapeamento existente no Jinja (`event_detail.html`).
- **FR-007**: Quando um dia tiver mais eventos do que couber na célula da grade, o sistema MUST prover um indicador de excedente (ex.: "+N") que dá acesso aos eventos ocultos, sem quebrar o layout da grade.
- **FR-008**: A Agenda MUST manter, inalteradas, todas as regras de RBAC/impersonação e ações já existentes (ex.: botão "Novo evento" restrito a COMERCIAL/SUPERADMIN, navegação para detalhe do evento).
- **FR-009**: O Banco de Talentos MUST renderizar a lista de talentos como um mosaico de fotos grandes (grid responsivo: 5–6 colunas em desktop, colapsando progressivamente até 1–2 colunas em mobile), com cada card mostrando foto de rosto em destaque, nome, e badges de medida (altura, tamanho, calçado) diretamente visíveis (sem hover/clique adicional).
- **FR-010**: O mosaico de Talentos MUST preservar toda a funcionalidade existente da tela: busca por nome, filtros (idioma, raça, tamanhos, calçado, passaporte, tags, altura, personagem), paginação, alternância Ativos/Pendentes, aprovação/rejeição de pendentes, e indicador de `warning_level`.
- **FR-011**: Talentos sem foto cadastrada MUST exibir um placeholder visual consistente no lugar da foto, sem quebrar o grid do mosaico.
- **FR-012**: As demais subpáginas internas (fora das User Stories 1–3) MUST adotar `PageHeader`/`DenseCard`/`MetricBadge` do design system onde hoje usam cabeçalho ou blocos de estatística fora do padrão, sem alterar fluxo, contrato de API ou introduzir novos componentes de layout.
- **FR-013**: Nenhuma mudança desta feature MUST introduzir regressão funcional: todas as ações hoje disponíveis nas telas tocadas continuam funcionando (mesmos endpoints, mesmos estados de loading/erro/sucesso via TanStack Query).
- **FR-014**: Toda animação de entrada de donuts, grade de calendário e mosaico MUST respeitar `useReducedMotion()` (Princípio IX), suprimindo-se quando o usuário preferir movimento reduzido.

### Key Entities

- **Progresso de setor (donut)**: percentual derivado de `done`/`total` já retornado por `/api/dashboard` para Casting e Figurino — sem nova entidade de dados, apenas nova representação visual.
- **Painel de setor**: agrupamento visual (Casting, Figurino, Comercial, Recorrentes) de itens de pendência já existentes na resposta do dashboard, com estado de colapsado/expandido local à sessão de navegação (não persistido).
- **Performance (SUPERADMIN)**: agregado de período (período selecionado, casting done/total, figurino done/total, entrada total em cachês) — pode exigir extensão aditiva do contrato do dashboard (ver FR-004).
- **Célula de calendário**: dia do mês exibido na grade da Agenda, contendo 0..N eventos resumidos (`EventoResumo` já existente), cor por `event_type`.
- **Card de talento (mosaico)**: mesma entidade `TalentSummary` já existente, com nova apresentação visual (foto grande + badges de medida sempre visíveis) — sem novo campo de dado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário de cada papel (CASTING, FIGURINO, FINANCEIRO, SUPERADMIN) vê no Dashboard React exatamente os mesmos números (percentuais, contagens, entrada total) que via na home Jinja clássica para o mesmo estado de dados.
- **SC-002**: A Agenda em grade mensal permite identificar visualmente, sem rolar a página, todos os eventos de um mês típico (até ~40 eventos) distribuídos pelas semanas, com categoria reconhecível pela cor em menos de 1 segundo de leitura.
- **SC-003**: O mosaico de Talentos permite ao casting escanear visualmente pelo menos 15 talentos "acima da dobra" em viewport desktop padrão (1440px), com medidas legíveis sem interação adicional.
- **SC-004**: Em viewport mobile (375px), as 3 telas principais (Dashboard, Agenda, Talentos) permanecem utilizáveis sem overflow horizontal e sem perda de funcionalidade.
- **SC-005**: Nenhuma regressão funcional: as verificações funcionais já existentes de agenda/dashboard/talentos (features 145, 154, 173) continuam passando após o redesenho.
- **SC-006**: Ao menos 5 subpáginas amostradas fora do escopo principal usam `PageHeader`/`DenseCard`/`MetricBadge` em vez de cabeçalho/estatística solta, após a revisão de alinhamento.

## Assumptions

- Os donuts serão implementados com a técnica mais simples que atinja a paridade visual exigida (CSS puro via `conic-gradient`, como no Jinja, ou uma lib de gráficos leve como Recharts) — a escolha técnica fica para o `/speckit-plan`; o requisito funcional é o resultado visual (percentual em donut), não a tecnologia específica.
- O painel de Performance (FASE B) reproduz o que existe hoje no Jinja (casting done/total, figurino done/total, entrada total) — não introduz novas métricas financeiras (DRE completo já existe em tela própria, `/financeiro`, fora do escopo desta feature).
- A grade de calendário cobre a visão mensal; visões de semana/dia não fazem parte do escopo desta feature (podem ser iniciativa futura).
- O comportamento de eventos multi-dia na grade (aparecer em todos os dias do intervalo vs. só no dia de início) fica a critério da implementação, desde que documentado — não é um critério de bloqueio de entrega.
- O mosaico de Talentos reaproveita as fotos já cadastradas (`photo_face_path`); não introduz upload de novas fotos ou novo campo de mídia.
- "Demais subpáginas" (User Story 4) recebe uma passada de alinhamento, não um redesenho completo linha a linha — o critério de conclusão é a adoção dos componentes do design system onde já fazem sentido, não a reescrita de cada tela.
- EducaManto e Portal do Artista permanecem fora do escopo (conforme CLAUDE.md e specs 173/171).
