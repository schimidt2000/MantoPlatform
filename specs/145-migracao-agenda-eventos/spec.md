# Feature Specification: Migração da Agenda/Eventos para React (leitura primeiro)

**Feature Branch**: `145-migracao-agenda-eventos`

**Created**: 2026-07-20

**Status**: Draft

**Input**: User description: "Migração da Agenda/Eventos (blueprint `calendar`) de Jinja/vanilla
para React consumindo endpoints JSON no Flask — User Story 2 da migração 144 (strangler-fig).
Maior e mais crítico módulo (event_detail ~900 linhas de JS, ~15 ações num único POST; ~20
rotas). Fatiar: P1 = LEITURA (agenda + detalhe do evento só exibindo); P2+ = ações de escrita
uma a uma. Reusar contratos/pacotes da Fundação. Não quebrar o Jinja atual (coexistência).
Respeitar valores pt-BR (@manto/money) e movimento (Framer Motion)."

## Contexto (auditoria do módulo, 2026-07-20)

O blueprint `calendar` (`app/calendar/routes.py`, ~3.480 linhas) é o núcleo operacional do
sistema. Superfície de leitura vs. escrita:

- **Leitura (GET):** `/agenda` (lista/calendário), `/agenda/day/<date>` (dia), a metade GET de
  `/events/<id>` (página do evento exibindo elenco, dados de venda, pagamentos, contrato,
  reembolsos, logística, agrupamento, observações), e `/agenda/log`.
- **Escrita:** ~23 ações despachadas de dentro do POST de `/events/<id>` (`_handle_*`:
  escalar casting, adicionar/remover cargo, marcar figurino, contrato, dados comerciais,
  pagamentos, reembolsos, logística, confirmação, convites, agrupamento comercial), mais
  rotas POST próprias (criar evento, gerenciar ensaio, sincronizar com Google, observações,
  excluir evento, dispensar/restaurar cargo).

Esta spec cobre a migração inteira do módulo, **fatiada por prioridade**; a fatia P1 (leitura)
é o MVP e a única detalhada para implementação imediata. As fatias de escrita (P2+) ficam
especificadas em alto nível aqui e recebem seu próprio `/speckit-plan`/`tasks` quando chegar a
vez — mesmo modelo da Fundação (feature 144).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver a agenda e o evento em React, sem risco (Priority: P1) 🎯 MVP

Migrar apenas a **leitura**: a lista/calendário da agenda e a página de detalhe do evento
exibindo todos os dados que hoje aparecem (elenco escalado, dados de venda, pagamentos,
contrato, reembolsos, logística, agrupamento, observações) — **sem nenhuma ação de escrita**.
A equipe valida em `beta` que a informação aparece igual à do sistema atual, enquanto continua
operando (criar/editar) no app Jinja em `app.` normalmente.

**Why this priority**: é a maior superfície do sistema e a mais arriscada de migrar. Começar
só pela leitura remove todo o risco de corromper dados (nenhuma escrita nova) e ainda entrega
valor de validação: prova que a serialização completa do evento — a parte mais trabalhosa —
está correta antes de qualquer ação de escrita ser construída sobre ela.

**Independent Test**: abrir `beta`, navegar pela agenda (por período/dia), abrir um evento com
dados ricos (elenco, venda, pagamentos, contrato, reembolsos) e conferir, lado a lado com a
mesma tela em `app.` (Jinja), que os dados exibidos são os mesmos — respeitando as permissões
(quem não vê dados financeiros no Jinja também não vê no React).

**Acceptance Scenarios**:

1. **Given** a agenda em React, **When** o usuário navega por um período, **Then** vê os
   mesmos eventos, com a mesma lógica de agrupamento comercial (principal + satélites) e os
   mesmos rótulos/estados que o sistema atual mostra.
2. **Given** a página de um evento em React, **When** ela carrega, **Then** exibe todas as
   seções de leitura hoje presentes (elenco, venda, pagamentos, contrato, reembolsos,
   logística, observações, agrupamento) com os mesmos valores — valores monetários no padrão
   brasileiro (`R$ 1.234,56`).
3. **Given** um usuário sem permissão para dados financeiros, **When** abre um evento, **Then**
   as seções de venda/pagamento/reembolso NÃO aparecem — exatamente como no sistema atual.
4. **Given** qualquer tela desta fatia, **When** ela carrega ou o usuário troca de evento/dia,
   **Then** há feedback de carregamento (skeleton) e a transição é suave (Framer Motion),
   respeitando `prefers-reduced-motion`.
5. **Given** o app Jinja atual, **When** esta fatia entra no ar, **Then** `/agenda` e
   `/events/<id>` em Jinja continuam funcionando sem nenhuma alteração para a equipe.

---

### User Story 2 - Escalar e gerenciar o elenco (casting) (Priority: P2)

Migrar as ações de casting: escalar talento a um cargo, adicionar/remover cargo, marcar
figurino, dispensar/restaurar cargo, enviar convite. É o conjunto de escrita mais usado no
dia a dia da operação.

**Why this priority**: é a ação mais frequente sobre um evento e a que mais se beneficia de
uma UI moderna; depende só da leitura (US1) já pronta.

**Independent Test**: em um evento, escalar um talento a um cargo vago e confirmar que o
estado no banco fica idêntico ao que o fluxo Jinja produziria (mesma linha em `event_roles`,
mesma detecção de conflito de disponibilidade).

**Acceptance Scenarios**:

1. **Given** um cargo vago, **When** o usuário escala um talento, **Then** o registro é
   criado com a mesma regra de conflito/disponibilidade de hoje, e a tela atualiza sem reload.
2. **Given** qualquer ação de casting, **When** o botão é clicado, **Then** ele mostra
   feedback imediato e nunca permite envio duplicado (Princípio V).

---

### User Story 3 - Dados de venda, pagamentos e reembolsos (Priority: P3)

Migrar as ações financeiras do evento: dados comerciais/venda, adicionar/editar/excluir
pagamento, reembolsos (adicionar/cobrar/excluir), status de pagamento. Concentra as regras
de dinheiro e usa o componente monetário único (`@manto/money`).

**Why this priority**: sensível (dinheiro real) e restrito por papel — vem depois de casting
por ser mais delicado; depende da leitura financeira (US1) e do componente monetário.

**Acceptance Scenarios**:

1. **Given** um campo de valor, **When** o usuário digita, **Then** a máscara brasileira
   formata em tempo real e o valor numérico puro é o que vai no corpo JSON (Princípio VII).
2. **Given** as ações financeiras, **When** executadas, **Then** produzem o mesmo estado que
   o fluxo Jinja (mesmas linhas em `event_payments`/`event_reimbursements`) e respeitam o RBAC.

---

### User Story 4 - Contrato, logística, confirmação, convites e agrupamento (Priority: P4)

Migrar o restante das ações sobre um evento existente: contrato (anexar/assinar/excluir),
logística, marcar confirmado, convites, e o agrupamento comercial (principal + satélites).

**Why this priority**: ações menos frequentes que casting/financeiro, mas necessárias para o
evento ser totalmente gerenciável em React sem voltar ao Jinja.

**Acceptance Scenarios**:

1. **Given** cada ação, **When** executada, **Then** produz o mesmo estado que o Jinja e a
   tela reflete a mudança sem reload.
2. **Given** o agrupamento comercial, **When** aplicado, **Then** segue as mesmas regras de
   validação de satélites de hoje (`_validate_group_satellites`).

---

### User Story 5 - Criar evento, ensaio, observações, sincronização e exclusão (Priority: P5)

Migrar o formulário de criação de evento (`event_create.html`, ~590 linhas de JS), a gestão
de ensaio (criar/editar/excluir/vincular, upload de material), observações, sincronização
manual com o Google Calendar e a exclusão de evento. Fecha o módulo — nenhuma rota da agenda
depende mais de `render_template`.

**Why this priority**: criação e ensaio são fluxos grandes e próprios; vêm por último porque
dependem de todos os padrões (upload, formulário complexo) já provados nas fatias anteriores.

**Acceptance Scenarios**:

1. **Given** o formulário de criação em React, **When** um evento é criado, **Then** produz o
   mesmo estado que o formulário Jinja (mesmo `CalendarEvent` + cargos pré-atribuídos).
2. **Given** a sincronização com o Google, **When** disparada, **Then** se comporta como hoje
   (a lógica de sync no backend é reaproveitada, não reescrita).

---

### Edge Cases

- **Serialização completa do evento (US1)**: a página do evento agrega muitas fontes
  (elenco, venda, pagamentos, contrato, reembolsos, logística, agrupamento, observações). A
  leitura precisa refletir TODAS com os mesmos valores/regras de visibilidade por papel — uma
  seção esquecida é uma regressão silenciosa.
- **Agrupamento comercial (principal + satélites)**: a agenda e o evento aplicam a mesma
  lógica de grupo (`_group_events`) para custo/venda/lucro; a leitura em React deve reproduzir
  isso, não os números do evento isolado.
- **RBAC financeiro**: dados de venda/pagamento/reembolso só aparecem para papéis autorizados
  (VENDAS/FINANCEIRO/COMERCIAL/SUPERADMIN) — a API não pode serializar esses campos para quem
  não pode vê-los (não basta esconder no front).
- **Coexistência**: enquanto as fatias de escrita não estiverem prontas, a versão React em
  `beta` é de leitura; a equipe opera no Jinja em `app.`. As duas leem o mesmo banco, então
  ficam consistentes.
- **Ações ainda não migradas na página do evento (US1)**: na fatia de leitura, a página não
  oferece botões de ação (eles chegam em US2–US5); exibir dados não implica poder alterá-los.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A agenda (lista/calendário e visão de dia) MUST ser exibível em React
  consumindo endpoints JSON, com os mesmos eventos, agrupamento comercial e estados que o
  sistema atual mostra.
- **FR-002**: A página de detalhe do evento MUST exibir em React, apenas para leitura na fatia
  P1, todas as seções hoje presentes (elenco, venda, pagamentos, contrato, reembolsos,
  logística, agrupamento, observações), com valores idênticos aos do sistema atual.
- **FR-003**: A serialização de dados financeiros (venda, pagamentos, reembolsos) MUST
  respeitar o mesmo RBAC das views atuais — a API não retorna esses campos para papéis sem
  permissão.
- **FR-004**: Todos os valores monetários exibidos MUST seguir o padrão brasileiro via a fonte
  única `@manto/money` (Princípio VII).
- **FR-005**: Toda mudança de estado visual perceptível (carregar, trocar de dia/evento) MUST
  ter transição suave via Framer Motion, respeitando `prefers-reduced-motion` (Princípio IX);
  todo carregamento assíncrono MUST ter feedback (skeleton/loading, erro, sucesso).
- **FR-006**: Cada rota da agenda hoje em `render_template` MUST ser mapeada a um endpoint JSON
  equivalente (documentado rota-Jinja → endpoint-JSON) antes de o código daquela fatia ser
  escrito; as rotas Jinja permanecem funcionando durante toda a transição (coexistência).
- **FR-007**: As fatias de escrita (P2–P5) MUST, quando implementadas, produzir exatamente o
  mesmo estado no banco que os fluxos Jinja equivalentes produzem hoje (mesmas tabelas/linhas:
  `CalendarEvent`, `EventRole`, `EventPayment`, `EventContract`, `EventReimbursement`), e
  respeitar o RBAC por papel.
- **FR-008**: Nenhum botão de ação (fatias P2+) MUST ficar "morto" ao clique; toda ação dá
  feedback visual imediato e nunca gera registro duplicado por clique repetido (Princípio V).
- **FR-009**: O app Jinja atual (`/agenda`, `/events/<id>` e ações) MUST continuar íntegro e
  inalterado para a equipe durante toda a migração deste módulo.

### Key Entities

Nenhuma entidade nova. A feature é de apresentação/contrato sobre os modelos existentes
(`CalendarEvent`, `EventRole`, `EventPayment`, `EventContract`, `EventReimbursement`,
`EventObservation`, `EnsaioMaterial` e relacionados em `app/models.py`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em qualquer evento aberto na fatia de leitura (US1), 100% das seções e valores
  exibidos batem com os do sistema Jinja atual para o mesmo usuário/papel — verificado
  comparando a resposta da API com o que a view Jinja produz, contra `manto_local`.
- **SC-002**: Zero regressão no app Jinja durante a migração: `/agenda` e `/events/<id>` em
  Jinja seguem respondendo e exibindo os mesmos dados após cada fatia entrar.
- **SC-003**: Nenhum dado financeiro é exposto pela API a um papel que não o veria no sistema
  atual (verificado por papel).
- **SC-004**: Ao final de todas as fatias, nenhuma rota da agenda depende de `render_template`
  e a equipe consegue operar um evento de ponta a ponta (criar, escalar, cobrar, contratar,
  agrupar) em React, com paridade funcional ao Jinja.

## Assumptions

- A fatia P1 é de **leitura pura**; a versão React da agenda fica em `beta` para validação
  enquanto a equipe continua operando no Jinja em `app.` — não há necessidade de "deep-link"
  de volta ao Jinja para ações nesta fatia (as ações chegam nas fatias seguintes).
- A visão de agenda em React reproduz as visões que já existem (lista/período + dia); não é
  escopo desta migração redesenhar a experiência de calendário nem adicionar visualizações
  novas (ex.: visão mensal em grade) além do que o sistema já oferece.
- A sincronização com o Google Calendar (OAuth, sync automático/manual) permanece no backend
  como está; a fatia P5 apenas expõe o disparo manual — a lógica de sync não é reescrita.
- A lógica de negócio já existente (agrupamento comercial, detecção de conflito de talento,
  cálculo de cachê/lucro, cascata de exclusão via `_clear_event_side_tables`) é reaproveitada
  no backend, servindo tanto o Jinja quanto a API (fonte única, Princípio I) — sem duplicar.
- `event_detail.html` (monólito com ~15 ações num POST) vira, nas fatias de escrita, endpoints
  REST dedicados por ação, não um único endpoint com campo `action` — decisão a confirmar no
  `/speckit-plan` de cada fatia, alinhada ao Princípio III (API First) da constituição v2.0.0.
- Fora de escopo desta spec: detalhar plano/tarefas das fatias P2–P5 (cada uma tem seu ciclo
  quando chegar a vez); e qualquer módulo fora do blueprint `calendar`.
