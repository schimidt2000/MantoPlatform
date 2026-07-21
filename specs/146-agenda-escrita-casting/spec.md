# Feature Specification: Agenda/Eventos — escrita de casting em React

**Feature Branch**: `146-agenda-escrita-casting`

**Created**: 2026-07-20

**Status**: Draft

**Input**: User description: "Migração da Agenda/Eventos para React — fatia de ESCRITA de
CASTING (US2 da spec 145, vira feature própria porque a leitura US1 já foi mergeada).
Primeira migração de escrita do módulo: estabelece o padrão de escrita da SPA (endpoints REST
por ação, feedback de clique sem envio duplicado, atualização sem reload). Migrar as ações de
casting do POST de /events/<id>: escalar talento (assign, com cachê e conflito), adicionar
cargo, remover cargo, enviar convite, dispensar/restaurar cargo, marcar figurino. Reusar o
serializer de leitura e a lógica de negócio existente (conflito, regras de sync) — não
reescrever. Respeitar RBAC, Princípio V (sem envio duplicado) e VII (cachê pt-BR). Não quebrar
o Jinja (coexistência, mesmo banco). Verificar contra manto_local que cada ação produz o mesmo
estado que o fluxo Jinja."

## Contexto (auditoria das ações de casting, 2026-07-20)

Esta é a **primeira migração de ESCRITA** do sistema — estabelece o padrão que as próximas
fatias de escrita seguirão. Ponto central da auditoria: as ações de casting **não são
gravações simples**. A principal (`_handle_assign_casting`) carrega regra de negócio densa e
**efeitos colaterais reais**:

- Teto de cachê (`cache_cap`): casting não ultrapassa o cap do orçamento; só superadmin pode,
  e fica registrado.
- Transições de `invite_status` (`None`→`pending`→`accepted`/`rejected`), reset de figurino e
  de status de pagamento ao trocar o talento.
- **E-mails**: convite ao talento escalado, aviso de remoção ao talento trocado (se não
  recusou), notificação de mudança de cachê a talento já confirmado.
- Registro em `EventLog` a cada ação.

Por isso o pedido é explícito: **reusar os handlers `_handle_*` existentes**, não reimplementar
a lógica na API (Princípio I) — o risco de divergência (ex.: esquecer de mandar o e-mail de
convite, ou de aplicar o cap) é alto e afetaria dados/comunicação reais.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Escalar/atualizar talento num cargo (Priority: P1) 🎯 MVP

Do detalhe do evento em React, o casting escala um talento a um cargo vago (ou troca/atualiza
o cachê de um já escalado). É a ação mais frequente e a mais complexa — cobre conflito de
disponibilidade, teto de cachê, convite por e-mail e atualização da tela sem reload. Migrar
ela primeiro prova o padrão de escrita inteiro.

**Why this priority**: é o coração do trabalho de casting e a ação de escrita mais rica;
provada ela, as demais (adicionar/remover cargo, convite, dispensar) são variações mais
simples do mesmo padrão.

**Independent Test**: escalar um talento a um cargo vago pela tela React e confirmar que o
estado no banco fica **idêntico** ao que o fluxo Jinja produziria — mesma linha em
`event_roles` (talent_id, cache_value respeitando o cap, assigned_at, invite_status=`pending`),
mesmo `EventLog`, mesmo disparo de convite — e que a tela reflete a mudança sem recarregar.

**Acceptance Scenarios**:

1. **Given** um cargo vago, **When** o casting escala um talento com um cachê dentro do cap,
   **Then** o registro fica igual ao do Jinja (talento, cachê, `assigned_at`,
   `invite_status=pending`), o convite é enviado uma única vez, e a tela atualiza sem reload.
2. **Given** um cachê acima do `cache_cap`, **When** quem salva NÃO é superadmin, **Then** o
   valor é limitado ao cap (mesma regra de hoje); superadmin pode ultrapassar, com registro.
3. **Given** o mesmo talento já alocado em outro cargo conflitante, **When** o casting tenta
   escalá-lo, **Then** o sistema sinaliza o conflito com a mesma regra de hoje
   (`_talent_time_conflict`) — sem gravar às escondidas.
4. **Given** o botão de salvar, **When** clicado, **Then** ele dá feedback imediato e um
   clique a mais NÃO cria convite/registro duplicado (Princípio V).
5. **Given** a ação concluída, **When** a resposta volta, **Then** ela traz o evento
   atualizado (mesmo formato de leitura da feature 145) para a tela re-renderizar.

---

### User Story 2 - Adicionar e remover cargo (Priority: P2)

Adicionar um cargo novo ao evento (com ou sem talento) e remover um cargo. Remoção respeita a
trava atual (cargo com convite `accepted` só o superadmin remove).

**Why this priority**: completa a gestão da lista de cargos; depende do padrão de escrita da
US1.

**Acceptance Scenarios**:

1. **Given** um evento, **When** o casting adiciona um cargo, **Then** a linha em
   `event_roles` fica igual à do fluxo Jinja (nome, tipo, talento/convite se informado).
2. **Given** um cargo com convite aceito, **When** um não-superadmin tenta remover, **Then** a
   remoção é bloqueada — igual a hoje.

---

### User Story 3 - Convite, dispensar/restaurar cargo, marcar figurino (Priority: P3)

As ações menores sobre um cargo: reenviar convite, dispensar um cargo obsoleto (que o sync
nunca mais recria) e restaurá-lo, e marcar o figurino como separado.

**Why this priority**: são toggles simples que fecham a paridade de casting; vêm por último
por serem os menores.

**Acceptance Scenarios**:

1. **Given** um cargo dispensado, **When** o casting o restaura, **Then** ele volta a contar
   como pendente — e o sync continua não o recriando enquanto dispensado (regra atual
   preservada).
2. **Given** cada ação, **When** executada, **Then** produz o mesmo estado/log que o Jinja e
   atualiza a tela sem reload.

---

### Edge Cases

- **Efeitos colaterais de e-mail**: escalar/trocar talento dispara e-mails reais (convite,
  remoção, mudança). A migração deve manter exatamente o mesmo comportamento de envio — nem a
  mais (duplicado) nem a menos (convite não enviado). A verificação NÃO pode disparar e-mails
  reais (o envio é isolado/mockado no teste).
- **Coexistência gravando no mesmo banco**: enquanto as duas versões (Jinja em `app.`, React
  em `beta`) coexistem, ambas gravam no mesmo `event_roles`. A migração não pode introduzir um
  segundo caminho com regra divergente — daí reusar os handlers.
- **Envio duplicado por clique/latência**: um clique a mais, ou reenvio por rede lenta, não
  pode criar cargo/convite duplicado (Princípio V) — a ação é idempotente do ponto de vista do
  usuário.
- **Cargo dispensado e o sync**: um cargo dispensado não é recriado pelo sync do Google
  (feature 108). Restaurar/dispensar pela API tem que preservar essa regra.
- **Teto de cachê por papel**: o cap só é ultrapassável por superadmin — a API tem que aplicar
  isso no servidor, não confiar no cliente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Cada ação de casting hoje despachada pelo POST de `/events/<id>` (escalar,
  adicionar cargo, remover cargo, enviar convite, dispensar, restaurar, marcar figurino) MUST
  ter um endpoint dedicado que executa a MESMA lógica de negócio já existente — reusando os
  handlers atuais, não reimplementando (Princípio I).
- **FR-002**: Cada ação MUST produzir exatamente o mesmo estado no banco que o fluxo Jinja
  equivalente (mesmas linhas/campos em `event_roles`, mesmo `EventLog`), verificado contra
  `manto_local`.
- **FR-003**: A RBAC de cada ação MUST ser idêntica à atual (ex.: remover cargo com convite
  aceito só superadmin; teto de cachê ultrapassável só por superadmin) — aplicada no servidor.
- **FR-004**: A detecção de conflito/disponibilidade de talento ao escalar MUST usar a mesma
  regra de hoje (`_talent_time_conflict`), sem reescrevê-la.
- **FR-005**: Nenhum botão de ação MUST ficar "morto" ao clique; toda ação dá feedback visual
  imediato e um clique/reenvio a mais NUNCA cria cargo, convite ou registro duplicado
  (Princípio V).
- **FR-006**: Valores de cachê MUST ser digitados/exibidos no padrão brasileiro via a fonte
  única `@manto/money` (Princípio VII); o valor persistido é numérico.
- **FR-007**: Ao concluir uma ação, a API MUST devolver o evento atualizado no mesmo formato
  de leitura da feature 145 (`serialize_event_detail`), para a tela re-renderizar sem reload,
  respeitando o RBAC de serialização.
- **FR-008**: Os e-mails disparados por escalar/trocar talento (convite, remoção, mudança)
  MUST continuar sendo enviados exatamente como hoje — sem duplicar nem omitir.
- **FR-009**: As ações de casting no `event_detail.html` Jinja MUST continuar funcionando
  inalteradas para a equipe durante toda a transição (coexistência, mesmo banco).

### Key Entities

Sem entidade nova. Escrita sobre `EventRole` (e `EventLog`) já existentes; leitura de
`Talent`. Nenhuma mudança de schema.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Para cada ação de casting migrada, o estado do banco após executá-la pela API é
  indistinguível do estado após executá-la pelo fluxo Jinja, para os mesmos dados de entrada —
  verificado campo a campo contra `manto_local`.
- **SC-002**: Zero e-mail duplicado e zero convite perdido: escalar um talento envia
  exatamente um convite, como hoje.
- **SC-003**: Nenhuma ação de casting no app Jinja regride durante a migração desta fatia.
- **SC-004**: Um clique repetido (ou reenvio por latência) numa ação de casting nunca gera um
  segundo cargo/convite/registro.

## Assumptions

- **Reuso via extração**: os handlers `_handle_*` hoje leem de `request.form`. Assume-se que a
  parte de negócio de cada um será extraída para uma função que recebe parâmetros explícitos,
  chamada tanto pelo POST Jinja (via um wrapper fino que lê o form) quanto pela API (que lê o
  JSON) — mantendo UMA implementação. O desenho exato (assinatura, onde mora) é decisão do
  `/speckit-plan`, mas a diretriz é não duplicar a lógica.
- **Endpoints REST por ação** (não um POST com campo `action`), ex.: `POST
  /api/events/<id>/roles` (adicionar), `POST /api/roles/<id>/assign` (escalar), `DELETE
  /api/roles/<id>` (remover), `POST /api/roles/<id>/invite`, `POST /api/roles/<id>/dismiss` |
  `/restore`, `POST /api/roles/<id>/figurino-done`. Nomes finais no plano.
- `figurino_done` é tecnicamente uma ação de Figurino, incluída aqui por ser um toggle simples
  sobre o cargo; sua RBAC segue a atual (Figurino/superadmin), não a de casting.
- A verificação isola/mocka o envio de e-mail (não dispara e-mail real contra `manto_local`) —
  detalhe de harness, definido no plano.
- Fora de escopo: venda/pagamentos/reembolsos, contrato, logística, confirmação, agrupamento,
  criar evento, ensaio, sync manual, excluir evento — fatias seguintes, cada uma com seu ciclo.
- Só a fatia P1 (escalar) é detalhada para implementação imediata; P2/P3 recebem plano/tarefas
  quando chegar a vez (mesmo modelo das features 144/145).
