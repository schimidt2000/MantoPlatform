# Feature Specification: Botões de mensagem na página do evento (confirmação + cobrança)

**Feature Branch**: `083-evento-botoes-mensagens`

**Created**: 2026-06-24

**Status**: Draft

**Input**: "Dois botões acessíveis para comercial e super admin, na página de cada evento. (1) 'Confirmar
dados do evento': copia para a área de transferência uma mensagem de confirmação (saudação conforme o
horário atual; personagens do evento; data completa do evento, como no exemplo; local do evento).
(2) 'Cobrança': só clicável quando estamos na data limite de pagamento ou já atrasado — copia uma
mensagem sobre o evento cobrando exatamente o que falta ser pago. Fora desses dois casos, o botão fica
inclicável e levemente transparente."

## Contexto

Na página de um evento, o time comercial precisa enviar duas mensagens recorrentes ao cliente: a
**confirmação dos dados do evento** (véspera/aproximação) e a **cobrança** quando o pagamento vence ou
atrasa. Hoje isso é digitado à mão. Dois botões que montam a mensagem pronta e copiam para a área de
transferência eliminam o retrabalho e padronizam o texto.

Mensagem-exemplo de confirmação fornecida pelo cliente:

```
Bom dia, Adriana! Como vai?
Passando para confirmar seu evento!

HELLO KITTY + CINNAMOROLL
Sexta-feira, 19 de junho⋅19:00 – 20:00
Spasso Dourado - Unidade Marquês de São Vicente

Tudo certinho? Estamos ansiosos por esse momento!
```

- A **saudação** ("Bom dia/Boa tarde/Boa noite") depende do **horário atual** de quem clica.
- Os **personagens** vêm do evento (título, sem o prefixo de tipo).
- A **data completa** vem do evento (dia da semana, dia, mês e faixa de horário).
- O **local** vem do evento.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Confirmar dados do evento (Priority: P1) 🎯 MVP

Como comercial (ou super admin) na página de um evento, quero clicar em **"Confirmar dados do evento"**
e ter a mensagem de confirmação pronta na área de transferência, para colar no WhatsApp do cliente.

**Acceptance Scenarios**:

1. **Given** um evento com título, data/horário e local preenchidos, **When** clico em "Confirmar dados
   do evento", **Then** a mensagem é copiada para a área de transferência e recebo um feedback visual
   ("Copiado!").
2. **Given** que clico às 9h, **When** a mensagem é montada, **Then** a saudação é "Bom dia"; às 15h é
   "Boa tarde"; às 21h é "Boa noite" (com base no horário atual de quem clica).
3. **Given** o evento "(R&I) HELLO KITTY + CINNAMOROLL", **When** a mensagem é montada, **Then** a linha
   de personagens mostra "HELLO KITTY + CINNAMOROLL" (sem o prefixo de tipo entre parênteses).
4. **Given** o evento em 19/06 das 19:00 às 20:00, **When** a mensagem é montada, **Then** a linha de
   data mostra o dia da semana, o dia/mês e a faixa de horário em português (ex.: "Sexta-feira, 19 de
   junho · 19:00 – 20:00").
5. **Given** o evento com local preenchido, **When** a mensagem é montada, **Then** a linha de local
   aparece; **When** o local está vazio, **Then** a linha de local é omitida (sem linha em branco
   sobrando).

### User Story 2 - Cobrança no vencimento/atraso (Priority: P2)

Como comercial (ou super admin), quero um botão de **"Cobrança"** que só fique ativo quando o
pagamento do evento está vencendo (data limite = hoje) ou já atrasado, e que copie uma mensagem
cobrando exatamente o valor que falta ser pago.

**Acceptance Scenarios**:

1. **Given** um evento cuja data limite de pagamento ainda está no futuro (nada vencido), **When** vejo
   a página, **Then** o botão "Cobrança" aparece **desabilitado** e levemente **transparente**, e não
   responde ao clique.
2. **Given** um evento cuja data limite de pagamento é **hoje** ou já **passou** e ainda há valor em
   aberto, **When** clico em "Cobrança", **Then** a mensagem de cobrança é copiada com o valor exato em
   aberto e recebo feedback visual.
3. **Given** um evento totalmente pago, **When** vejo a página, **Then** o botão "Cobrança" fica
   desabilitado (não há o que cobrar).
4. **Given** o botão está habilitado, **When** passo o mouse, **Then** há indicação clara de que está
   clicável; **When** está desabilitado, **Then** um tooltip explica por que (ex.: "Disponível apenas
   na data limite ou em atraso").

### Edge Cases

- Evento sem valor de venda / sem data limite de pagamento e sem parcelas: botão "Cobrança"
  desabilitado (não há vencimento a cobrar).
- Evento com parcelas: o valor em aberto é a soma das parcelas ainda não recebidas; a "data limite" é a
  data de vencimento da parcela em aberto mais antiga.
- Evento sem horário de término: a linha de data mostra só o horário de início.
- Usuário sem papel comercial nem super admin: nenhum dos dois botões aparece.

## Requirements *(mandatory)*

### Botão "Confirmar dados do evento"

- **FR-001**: O botão MUST aparecer na página do evento apenas para usuários com papel **COMERCIAL** ou
  **SUPERADMIN**.
- **FR-002**: Ao clicar, o sistema MUST copiar para a área de transferência uma mensagem de confirmação
  e exibir feedback visual de sucesso.
- **FR-003**: A **saudação** MUST ser escolhida pelo **horário atual** de quem clica: "Bom dia" (05:00–
  11:59), "Boa tarde" (12:00–17:59), "Boa noite" (18:00–04:59).
- **FR-004**: A mensagem MUST conter os **personagens do evento** (título sem o prefixo de tipo entre
  parênteses).
- **FR-005**: A mensagem MUST conter a **data completa do evento** em português (dia da semana, dia de
  mês, e faixa de horário início–fim), seguindo o exemplo.
- **FR-006**: A mensagem MUST conter o **local do evento** quando preenchido, e MUST omitir a linha
  quando vazio.
- **FR-007**: A estrutura da mensagem (abertura "Passando para confirmar seu evento!" e fechamento
  "Tudo certinho? Estamos ansiosos por esse momento!") MUST seguir o exemplo fornecido.

### Botão "Cobrança"

- **FR-008**: O botão MUST aparecer na página do evento apenas para usuários com papel **COMERCIAL** ou
  **SUPERADMIN**.
- **FR-009**: O botão MUST estar **clicável apenas** quando a data limite de pagamento for **hoje** ou
  já tiver **passado** e ainda houver **valor em aberto**.
- **FR-010**: Fora dessa condição, o botão MUST aparecer **desabilitado** e **levemente transparente**,
  e MUST ignorar cliques.
- **FR-011**: Quando habilitado e clicado, o sistema MUST copiar uma mensagem de cobrança que
  identifica o evento e cobra **exatamente o valor em aberto** (o que falta ser pago).
- **FR-012**: O **valor em aberto** MUST ser calculado como a soma das parcelas ainda não recebidas
  quando houver parcelas; caso não haja parcelas, o valor de venda em aberto considerando a data limite
  de pagamento do evento.

## Success Criteria *(mandatory)*

- **SC-001**: A partir da página do evento, o comercial copia a mensagem de confirmação em **um clique**
  (sem digitar nada).
- **SC-002**: A saudação corresponde corretamente ao horário em 100% dos três períodos (manhã/tarde/
  noite).
- **SC-003**: Personagens, data e local na mensagem batem com os dados exibidos no evento.
- **SC-004**: O botão "Cobrança" só é clicável quando há vencimento (hoje) ou atraso com saldo em
  aberto; nos demais casos aparece transparente e não copia nada.
- **SC-005**: A mensagem de cobrança traz exatamente o valor em aberto do evento.

## Assumptions

- **Saudação personalizada com nome**: o evento não possui um campo de "nome do contato/cliente"
  (`CalendarEvent` não tem esse dado). Portanto a saudação será **sem nome** ("Bom dia! Como vai?") em
  vez de "Bom dia, Adriana!". O comercial pode ajustar o nome após colar, se quiser.
- **Personagens**: derivados do título via a mesma regra já usada no sistema (`parse_characters`,
  remove o prefixo `(TIPO)` e mantém a junção por " + ").
- **Data em português**: dia da semana e mês por extenso em pt-BR, faixa de horário início–fim; usa o
  separador do exemplo entre data e horário.
- **Valor em aberto / data limite**: usa as parcelas (`EventInstallment`: `due_date`, `amount`,
  `received`) quando existirem; senão, `payment_due_date` + `sale_value` do evento (descontando
  recebimentos já registrados). Para eventos satélite de um grupo, usa os dados financeiros do próprio
  evento (sem herdar do principal nesta feature).
- **Cópia**: feita no cliente (área de transferência do navegador); a saudação é calculada no momento do
  clique para refletir o horário atual.
