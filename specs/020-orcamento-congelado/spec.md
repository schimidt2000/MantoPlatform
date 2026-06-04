# Feature Specification: Orçamento congelado (registro imutável)

**Feature Branch**: `020-orcamento-congelado`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User constraint: "Qualquer mudança que fizermos agora não deve mudar nenhum orçamento
feito até agora. Cada orçamento feito deve ter seus valores e multiplicadores mantidos."

## Contexto

Hoje cada orçamento salva os **totais** finais + os **inputs** do formulário, mas **não** salva o
multiplicador usado nem o detalhamento. "Reabrir" **recalcula** com os preços/lógica atuais — então
mudar um preço no futuro faria um orçamento antigo exibir números diferentes do que foi cotado.

Para tornar seguros os próximos ajustes (centralizar valores, unificar cálculo — ver REVIEW da 019),
o orçamento precisa virar um **registro imutável**: ao gerar, congela-se o resultado completo
(totais, multiplicadores, mensagem). Visualizar mostra exatamente o que foi cotado, para sempre.
Quem quiser um novo com preços atuais usa uma ação explícita de **recalcular**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver um orçamento exatamente como foi cotado (Priority: P1)

No histórico, "Ver" abre o orçamento **congelado**: a mesma mensagem, os mesmos totais e o mesmo
multiplicador do momento em que foi gerado — independente de mudanças de preço posteriores.

**Acceptance Scenarios**:

1. **Given** um orçamento gerado hoje, **When** o preço de um item muda nas configurações e depois
   abro "Ver" daquele orçamento, **Then** os valores exibidos são os originais (não recalculados).
2. **Given** "Ver" de um orçamento, **When** baixo o PDF ou copio a mensagem, **Then** refletem o
   conteúdo original congelado.

---

### User Story 2 - Recalcular é uma ação separada e explícita (Priority: P1)

A ação antes chamada "Reabrir" passa a se chamar "Recalcular (preços atuais)": carrega os inputs no
formulário e recalcula com os preços atuais para **gerar um novo** orçamento, **sem alterar** o
original.

**Acceptance Scenarios**:

1. **Given** um orçamento antigo, **When** clico em "Recalcular (preços atuais)", **Then** o
   formulário é preenchido e os valores são recalculados com os preços de hoje.
2. **Given** que recalculei, **When** gero, **Then** é criado um **novo** registro; o original
   permanece intacto no histórico.

---

### User Story 3 - Orçamentos antigos preservados (Priority: P1)

Orçamentos criados antes desta funcionalidade continuam mostrando seus **totais salvos**; nada é
recalculado retroativamente.

**Acceptance Scenarios**:

1. **Given** um orçamento anterior a esta entrega (sem snapshot completo), **When** abro "Ver",
   **Then** vejo os totais originais salvos (com aviso de que a mensagem original não foi
   registrada, quando for o caso).
2. **Given** qualquer orçamento do histórico, **When** a lista é exibida, **Then** os totais são os
   salvos no momento da criação (nunca recalculados).

---

### Edge Cases

- **Orçamento personalizado** (valor final / multiplicador): o critério e os valores/multiplicadores
  personalizados fazem parte do congelamento.
- **Mudança de preço futura**: não afeta nenhum orçamento já salvo.
- **Antigos sem snapshot**: exibem os totais salvos; o detalhamento/mensagem original pode não
  existir — é o único limite, e fica explícito.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Ao gerar um orçamento, o sistema MUST congelar o resultado completo (totais,
  multiplicador(es) usados e a mensagem) junto do registro.
- **FR-002**: "Ver" um orçamento MUST exibir o resultado congelado (mensagem, totais, multiplicador)
  exatamente como no momento da geração, imune a mudanças de preço posteriores.
- **FR-003**: PDF e cópia/envio a partir de "Ver" MUST refletir o conteúdo congelado.
- **FR-004**: A ação de recalcular (antiga "Reabrir") MUST ser explícita e rotulada como
  "Recalcular (preços atuais)", gerando um **novo** orçamento sem alterar o original.
- **FR-005**: Os totais salvos de qualquer orçamento NÃO MUST ser recalculados ou sobrescritos.
- **FR-006**: Orçamentos anteriores a esta funcionalidade MUST continuar exibindo seus totais
  salvos; a ausência de snapshot completo MUST ser tratada sem erro.
- **FR-007**: Nenhuma mudança de preço/configuração futura MUST alterar um orçamento já salvo.

### Key Entities *(include if feature involves data)*

- **Orçamento (histórico)**: passa a guardar, além dos totais e inputs, um **snapshot do resultado**
  (totais, multiplicadores, mensagem) que o torna imutável.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Após mudar um preço nas configurações, 100% dos orçamentos já salvos exibem em "Ver"
  os mesmos valores de antes da mudança.
- **SC-002**: Recalcular gera um novo registro em 100% dos casos, com 0 alterações no registro
  original.
- **SC-003**: 0 orçamentos têm seus totais salvos recalculados/sobrescritos.
- **SC-004**: Orçamentos antigos (sem snapshot) abrem em "Ver" sem erro, mostrando os totais
  originais.

## Assumptions

- O snapshot do resultado reaproveita o conteúdo já montado na geração (mensagem, totais, flags,
  dados de personalização) + o multiplicador aplicado.
- "Ver" reaproveita a tela de resultado existente, alimentada pelo snapshot (não recalcula).
- Para orçamentos antigos, preserva-se o que existe (totais); a mensagem original pode não estar
  disponível.
- Esta é a base (decisão do usuário) que torna seguros os ajustes seguintes do REVIEW (centralizar
  valores, unificar cálculo).
