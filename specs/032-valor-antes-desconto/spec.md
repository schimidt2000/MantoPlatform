# Feature Specification: "Valor antes do desconto" no evento

**Feature Branch**: `032-valor-antes-desconto` (sobre `031`)

**Created**: 2026-06-09

**Status**: Draft

**Input**: User description: "retire o valor no contrato. Coloque ao lado do valor de venda, valor
antes do desconto. Obrigatório ser digitado também. Esse valor vai servir para painéis financeiros
depois onde podemos ver quanto demos de desconto para gerarmos relatórios."

## Contexto

No formulário de criação de evento, o campo **"Valor no contrato (R$)"** (na seção Contrato) não tem
uso claro e será **removido**. No lugar, ao lado do **"Valor de venda"**, entra um novo campo
**"Valor antes do desconto (R$)"**, **obrigatório**.

A ideia: hoje o sistema guarda só o **valor final** da venda (após desconto). Guardando também o
**valor antes do desconto**, é possível calcular **quanto de desconto foi concedido** em cada evento —
base para painéis e relatórios financeiros futuros (desconto = valor antes do desconto − valor de
venda).

Quando o evento vem de um orçamento, o "valor antes do desconto" já nasce preenchido com o total do
orçamento (o preço cheio), e o "valor de venda" é o que efetivamente será cobrado (podendo ser menor,
se houver desconto).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar o valor antes do desconto (Priority: P1)

Ao criar um evento, a pessoa informa o **valor antes do desconto** (preço cheio) e o **valor de
venda** (preço final). Ambos são obrigatórios.

**Why this priority**: É o dado que falta para medir desconto; sem ele, não há relatório de desconto.

**Independent Test**: Criar um evento informando os dois valores e confirmar que ambos ficam
registrados no evento.

**Acceptance Scenarios**:

1. **Given** o formulário de criar evento, **When** olho a seção de valores, **Then** vejo "Valor
   antes do desconto" ao lado de "Valor de venda", ambos com indicação de obrigatório.
2. **Given** o "valor antes do desconto" vazio/zero, **When** envio, **Then** sou avisado de forma
   clara (campo destacado) e o envio é bloqueado.
3. **Given** os dois valores preenchidos, **When** crio o evento, **Then** ambos ficam salvos no
   evento (o valor antes do desconto fica disponível para uso financeiro futuro).

---

### User Story 2 - Preenchimento automático a partir do orçamento (Priority: P2)

Quando o evento é criado a partir de um orçamento, o "valor antes do desconto" já vem preenchido com o
total do orçamento (preço cheio), e acompanha a duração selecionada.

**Why this priority**: Evita redigitar e garante que o "preço cheio" seja o do orçamento.

**Acceptance Scenarios**:

1. **Given** criação a partir de um orçamento, **When** a tela abre, **Then** "valor antes do
   desconto" e "valor de venda" vêm com o total do orçamento.
2. **Given** que eu troco a duração (1h/2h/4h), **When** seleciono outra, **Then** ambos os valores
   acompanham o total daquela duração.
3. **Given** que aplico um desconto, **When** confirmo, **Then** o "valor de venda" diminui e o "valor
   antes do desconto" permanece o preço cheio (a diferença é o desconto).

---

### User Story 3 - Remover "Valor no contrato" (Priority: P2)

O campo "Valor no contrato (R$)" sai do formulário de criação de evento (o anexo do contrato e o
"contrato já assinado" permanecem).

**Acceptance Scenarios**:

1. **Given** a seção Contrato no formulário de criar evento, **When** a vejo, **Then** não há mais o
   campo "Valor no contrato"; o arquivo do contrato e o "já assinado" continuam.

---

### Edge Cases

- **Valor antes do desconto = 0 ou vazio**: inválido (precisa ser maior que zero), com aviso no campo.
- **Sem desconto**: "valor antes do desconto" == "valor de venda" (desconto = 0). Válido.
- **Erro de envio**: os dois valores preenchidos são preservados (Princípio V).
- **Eventos antigos** (criados antes desta mudança): não têm "valor antes do desconto" — relatórios
  futuros tratam ausência como "sem dado", sem quebrar.
- **Bypass do cliente**: o servidor também exige o valor antes do desconto.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O formulário de criar evento MUST exibir "Valor antes do desconto (R$)" ao lado de
  "Valor de venda", marcado como obrigatório.
- **FR-002**: "Valor antes do desconto" MUST ser obrigatório e maior que zero (validado no cliente,
  com destaque no campo, e no servidor como rede de segurança).
- **FR-003**: O valor antes do desconto MUST ser persistido no evento, separado do valor de venda,
  para uso em relatórios financeiros futuros.
- **FR-004**: O campo "Valor no contrato (R$)" MUST ser removido do formulário de criar evento; o
  anexo do contrato e o "contrato já assinado" permanecem.
- **FR-005**: Quando criado a partir de um orçamento, "valor antes do desconto" MUST vir preenchido
  com o total do orçamento e acompanhar a duração selecionada.
- **FR-006**: Aplicar um desconto MUST reduzir o "valor de venda" e MUST NÃO alterar o "valor antes do
  desconto" (para que a diferença represente o desconto).
- **FR-007**: Em erro de validação, os valores preenchidos MUST ser preservados.

### Key Entities

- **Evento (CalendarEvent)** — ganha o atributo **valor antes do desconto** (preço cheio), ao lado do
  já existente valor de venda (preço final). A diferença entre os dois é o desconto concedido.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos eventos criados pelo formulário passam a registrar o valor antes do desconto.
- **SC-002**: O desconto de qualquer evento é calculável como (valor antes do desconto − valor de
  venda) em 100% dos eventos novos.
- **SC-003**: 0 eventos criados sem "valor antes do desconto" (campo obrigatório, cliente + servidor).
- **SC-004**: O campo "Valor no contrato" não aparece mais no formulário de criar evento.

## Assumptions

- O relatório/painel de desconto em si é **fora de escopo** desta entrega; aqui apenas **capturamos e
  guardamos** o valor antes do desconto. A leitura/relatório vem depois.
- "Valor antes do desconto" é o preço cheio (do orçamento, quando houver); "valor de venda" é o final.
- Eventos anteriores ficam sem o dado (campo opcional no banco para não quebrar registros existentes);
  só o formulário passa a exigir no preenchimento novo.
- Requer um ajuste de banco (nova coluna no evento) — migration escrita à mão.
- Construído sobre 030 (horário obrigatório) e 031 (feedback dos campos), incluídos neste branch.
