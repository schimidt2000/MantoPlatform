# Feature Specification: Sincronização automática da agenda confiável

**Feature Branch**: `029-cron-sync-confiavel`

**Created**: 2026-06-08

**Status**: Draft

**Input**: User description: "confira se o cron sync está funcionando como o botão sincronizar agora na
tela da agenda. Parece que o cron sync não funciona muito bem."

## Contexto

Há dois caminhos de sincronização da agenda com o Google Calendar:

- **Botão "Sincronizar agora"** (tela da agenda): para o **mês visualizado**, faz buscar do Google →
  atualizar o banco → remover eventos que sumiram do Google → marcar o mês como sincronizado.
- **Cron** (`sync_worker.py`): a mesma operação, mas para uma **faixa de meses** (de hoje até +6
  meses). **Precisa ser configurado à mão como um serviço Cron separado no Railway.**

A investigação confirmou que a **lógica por mês é idêntica** entre os dois — então, quando o cron
roda, ele faz exatamente o que o botão faz. O problema é **operacional**: a sincronização automática
depende de um serviço externo separado que pode não estar configurado/ativo. Quando ele não roda,
**a agenda só atualiza quando alguém clica no botão**, e eventos criados/alterados/removidos no Google
não aparecem sozinhos — exatamente o "não funciona muito bem".

Decisão (confirmada com o usuário): tornar a sincronização automática **interna ao próprio app**
(como já existe para importar talentos), reaproveitando a **mesma lógica do botão**, sem depender de
configurar um serviço separado no Railway.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Agenda se atualiza sozinha (Priority: P1)

Eventos criados, alterados ou removidos no Google Calendar aparecem na agenda da plataforma
**sozinhos**, em poucos minutos, sem ninguém precisar clicar em "Sincronizar agora".

**Why this priority**: É o objetivo central — a automação que hoje é frágil passa a ser confiável.

**Independent Test**: Criar um evento no Google Calendar para um mês futuro e confirmar que, dentro do
intervalo de sincronização, ele aparece na agenda da plataforma sem ação manual.

**Acceptance Scenarios**:

1. **Given** um evento novo no Google Calendar (mês atual ou próximos meses), **When** passa o
   intervalo de sincronização, **Then** ele aparece na agenda sem clique manual.
2. **Given** um evento removido no Google Calendar, **When** passa o intervalo, **Then** ele deixa de
   aparecer na agenda (mesma limpeza do botão).
3. **Given** um evento alterado no Google (horário/título), **When** passa o intervalo, **Then** a
   agenda reflete a alteração.

---

### User Story 2 - Mesmo resultado do botão (Priority: P1)

A sincronização automática produz **exatamente o mesmo resultado** que clicar em "Sincronizar agora"
para cada mês — nem mais, nem menos.

**Why this priority**: Garante que a automação seja confiável e previsível; o usuário já confia no
botão.

**Independent Test**: Para um mês, comparar o estado da agenda após a sincronização automática com o
estado após clicar no botão — devem ser equivalentes.

**Acceptance Scenarios**:

1. **Given** um mês qualquer dentro do horizonte, **When** a sincronização automática roda, **Then** o
   conjunto de eventos do mês fica igual ao que o botão produziria.

---

### User Story 3 - Não duplica nem se atropela (Priority: P2)

Mesmo com o app rodando em vários processos ao mesmo tempo, a sincronização automática **roda uma vez
por ciclo** — sem criar eventos duplicados nem erros por execução concorrente.

**Why this priority**: O app roda com múltiplos processos (workers); sem controle, a mesma
sincronização rodaria várias vezes em paralelo, podendo gerar erro/duplicação.

**Independent Test**: Com múltiplos processos ativos, confirmar que apenas um executa o ciclo e não há
eventos duplicados nem erros de concorrência nos logs.

**Acceptance Scenarios**:

1. **Given** múltiplos processos do app ativos, **When** chega a hora de sincronizar, **Then** apenas
   um processo executa o ciclo (os demais pulam).
2. **Given** ciclos repetidos, **When** observo a agenda, **Then** não há eventos duplicados.

---

### User Story 4 - Visibilidade de quando sincronizou (Priority: P3)

É possível saber **quando** a sincronização automática rodou pela última vez (e se deu erro), para
diagnosticar rapidamente se está funcionando.

**Why this priority**: A causa do problema atual foi justamente a falta de visibilidade ("parece que
não funciona"). Registrar o resultado fecha o diagnóstico.

**Acceptance Scenarios**:

1. **Given** a sincronização automática rodou, **When** consulto o histórico/registro, **Then** vejo o
   horário da última execução e se houve erro.

---

### Edge Cases

- **Google desconectado/indisponível**: o ciclo falha de forma silenciosa e segura (registra o erro),
  não derruba o app, e tenta de novo no próximo ciclo.
- **Vários processos ao mesmo tempo**: apenas um roda o ciclo (controle de execução única).
- **App reiniciando/deploy**: ao subir, a sincronização recomeça sozinha após um curto aquecimento.
- **Mês sem eventos**: ciclo conclui normalmente (zero eventos é um resultado válido).
- **Compatibilidade**: o script de cron existente continua funcionando (pode ser usado como execução
  manual/backup), reaproveitando a mesma lógica.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST sincronizar a agenda com o Google Calendar **automaticamente e em
  intervalos regulares**, sem depender de ação manual nem de um serviço externo configurado à parte.
- **FR-002**: A sincronização automática MUST usar **a mesma lógica do botão "Sincronizar agora"**
  por mês (buscar → atualizar → remover ausentes → marcar sincronizado), aplicada à faixa de meses de
  hoje até +6 meses.
- **FR-003**: A lógica de sincronização MUST ter **uma fonte única** reaproveitada pelo caminho
  automático e pelo script de cron existente (sem duplicar a lógica).
- **FR-004**: Mesmo com múltiplos processos do app, a sincronização automática MUST executar **apenas
  uma vez por ciclo** (controle de execução única, à prova de concorrência).
- **FR-005**: Uma falha na sincronização NÃO MUST derrubar o app; MUST ser registrada e o ciclo MUST
  ser retomado no próximo intervalo.
- **FR-006**: O sistema MUST registrar **quando** a sincronização automática rodou pela última vez (e
  se houve erro), de forma consultável.
- **FR-007**: A sincronização automática NÃO MUST criar eventos duplicados nem alterar dados de
  eventos além do que o botão já faz.
- **FR-008**: O botão "Sincronizar agora" MUST continuar funcionando exatamente como hoje.

### Key Entities

- **Configuração do sistema (SiteSetting)** — ganha um marcador de **última sincronização automática**
  (horário), usado tanto para o controle de execução única quanto para visibilidade.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um evento criado/alterado/removido no Google Calendar reflete na agenda em até ~10
  minutos, sem ação manual, em 100% dos casos (dentro do horizonte de meses).
- **SC-002**: 0 eventos duplicados e 0 erros de concorrência após ciclos repetidos com múltiplos
  processos ativos.
- **SC-003**: O resultado da sincronização automática é equivalente ao do botão para o mesmo mês em
  100% das comparações.
- **SC-004**: É possível verificar o horário da última sincronização automática em 100% das vezes.
- **SC-005**: 0 quedas do app causadas por falha de sincronização (falhas são registradas e o ciclo
  continua).

## Assumptions

- Intervalo padrão de ~10 minutos (ajustável), cobrindo de hoje até +6 meses (mesmo horizonte do cron
  atual), com buffer para eventos mais distantes já existentes no banco.
- O token do Google fica no banco (já é o caso), então a sincronização interna autentica normalmente.
- O ambiente de produção mantém o app rodando continuamente (mesma premissa já usada pela
  sincronização de talentos existente).
- O script `sync_worker.py` é mantido como execução manual/backup, reaproveitando a mesma lógica.
- Requer um pequeno ajuste de banco (marcador de última sincronização) — migration escrita à mão.
