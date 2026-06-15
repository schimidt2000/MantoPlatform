# Feature Specification: Cobranças comerciais incluindo o passado (data de início configurável)

**Feature Branch**: `046-cobrancas-passado`

**Created**: 2026-06-15

**Status**: Draft

**Input**: User description: "Eu comecei a marcar tudo pelo sistema a partir de maio. Preciso que
apareça não só o futuro nessa seção [cobranças do comercial na home]. Preciso também que mostre o
passado a partir de maio de 2026. Isso não deveria ser hardcoded — talvez seja legal colocar qual
deve ser a data de início na administração, nas configs."

## Contexto

O painel **💰 Comercial → cobranças pendentes** na home só mostra eventos do dia atual em diante.
Eventos **passados com saldo em aberto** (os mais importantes de cobrar!) não aparecem. O usuário
passou a registrar tudo no sistema a partir de maio/2026 e quer ver as cobranças desde então.

Já existe nas configurações de administração o campo **"Data de início do sistema"**
(`release_date`), hoje descrito como filtro das tarefas (casting, figurino, ensaio). O pedido do
usuário — "colocar a data de início nas configs" — é exatamente esse campo: ele deve passar a
governar também o painel de cobranças, sem nada hardcoded.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cobranças do passado aparecem (Priority: P1)

Com a data de início do sistema configurada (ex.: 01/05/2026), o painel de cobranças mostra
eventos com saldo em aberto a partir dessa data — incluindo os que já aconteceram.

**Acceptance Scenarios**:

1. **Given** data de início = 01/05/2026 e um show de 20/05/2026 com saldo em aberto, **When** o
   comercial abre a home, **Then** esse evento aparece nas cobranças.
2. **Given** um evento anterior à data de início, **Then** ele NÃO aparece (recorte respeitado).
3. **Given** um evento passado já quitado, **Then** não aparece.

---

### User Story 2 - Evento passado em aberto é destacado como "atrasado" (Priority: P1)

Eventos que já aconteceram e seguem com saldo em aberto recebem destaque próprio ("Atrasado") e
ficam no topo da lista — antes dos futuros.

**Acceptance Scenarios**:

1. **Given** um show de 20/05 não pago e um de 27/06 com sinal pendente, **Then** o de 20/05
   aparece como "Atrasado" e acima do de 27/06.
2. **Given** um pagamento futuro/faturado com data combinada já vencida, **Then** aparece como
   "Vencido" (destaque vermelho), junto dos atrasados.
3. **Given** vários atrasados, **Then** os mais antigos vêm primeiro.

---

### User Story 3 - Data de início configurável na administração (Priority: P1)

O super admin define a data de início do sistema nas configurações; o painel de cobranças passa a
usá-la imediatamente. Nada é hardcoded.

**Acceptance Scenarios**:

1. **Given** as configurações de administração, **Then** existe o campo "Data de início do
   sistema" com explicação de que controla também as cobranças do comercial.
2. **When** o super admin altera a data e salva, **Then** o recorte das cobranças (e das tarefas)
   muda conforme a nova data.

---

### Edge Cases

- Data de início não configurada: comportamento atual (a partir de hoje) — recomenda-se configurar.
- Evento passado sem data de término: usa a data de início do evento como referência de "passado".
- Eventos quitados nunca aparecem, independentemente da data.
- A mesma data de início continua valendo para as tarefas (casting/figurino/ensaio), coerente com
  "passei a marcar tudo no sistema a partir de maio".

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O painel de cobranças MUST listar eventos com saldo em aberto cujo início é igual ou
  posterior à **data de início do sistema** configurada — incluindo eventos já passados.
- **FR-002**: Eventos passados com saldo em aberto MUST ser destacados como "Atrasado" e ordenados
  antes dos futuros (mais antigos primeiro).
- **FR-003**: A data de início MUST vir das configurações de administração (campo já existente,
  `release_date`), sem nenhum valor fixo no código.
- **FR-004**: A explicação do campo nas configurações MUST deixar claro que ele governa também as
  cobranças do comercial.
- **FR-005**: Eventos quitados ou anteriores à data de início MUST continuar fora do painel.

### Key Entities

- **Configuração do sistema** — guarda a "data de início" usada como recorte de tarefas e cobranças.
- **Evento / Cobrança** — entra no painel quando início ≥ data de início e há saldo em aberto.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos eventos com saldo em aberto a partir da data de início aparecem (passado
  incluído).
- **SC-002**: Eventos atrasados aparecem no topo, separados visualmente dos futuros.
- **SC-003**: Alterar a data de início nas configs muda o recorte sem qualquer mudança de código.

## Assumptions

- A "data de início" é o campo existente `release_date` ("Data de início do sistema"), reaproveitado
  — não será criado um novo campo nem haverá mudança de banco.
- Como o usuário passou a usar o sistema em maio, faz sentido que a mesma data governe tarefas e
  cobranças; ele definirá 01/05/2026 nas configurações.
- "Passado" = data de início do evento já passou (horário de Brasília).
