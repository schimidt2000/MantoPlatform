# Feature Specification: Padronizar valores monetários no padrão brasileiro

**Feature Branch**: `027-formato-valor-brasileiro`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User description: "Padronizar todos os valores monetários do sistema para o padrão
brasileiro (milhar com ponto, decimal com vírgula, duas casas), tanto na exibição quanto na
digitação (máscara automática enquanto o usuário digita). Hoje há lugares mostrando valor cru
(ex.: 4000) e alguns no padrão americano. Deve haver uma fonte única de formatação (filtro no
backend + helper de máscara no frontend), e o valor persistido continua numérico."

## Contexto

Hoje os valores em dinheiro aparecem de formas inconsistentes pelo sistema:
- **Vários lugares já corretos** usam o padrão brasileiro (`R$ 1.500,00`) via filtro `brl`.
- **Alguns mostram valor cru** — ex.: `4000` em vez de `R$ 4.000,00`.
- **Alguns mostram no padrão americano** — ex.: `1,500.00` (vírgula no milhar, ponto no decimal),
  por usar formatação `"{:,.2f}"` direta no template.
- **Campos de digitação são inconsistentes**: uns são caixa de número "crua" (`type="number"`,
  placeholder `0`), outros pedem para digitar à mão `1.000,00`. Não existe máscara que formate
  automaticamente enquanto a pessoa digita.

Isso gera confusão (a pessoa não sabe se `4000` são quatro mil ou quarenta reais), erros de
digitação e aparência amadora. A Constituição (Princípio VII, v1.2.0) passou a exigir o padrão
brasileiro em todo valor monetário, na exibição e na digitação, com **fonte única** de formatação.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Todo valor exibido no padrão brasileiro (Priority: P1)

Em qualquer tela do sistema, todo valor em dinheiro aparece no padrão brasileiro: ponto no milhar,
vírgula no decimal, duas casas (ex.: `R$ 4.000,00`). Nunca cru (`4000`) nem americano (`1,500.00`).

**Why this priority**: É o que o usuário vê o tempo todo; valores ambíguos ou em formato errado
quebram a confiança no sistema e podem levar a decisões financeiras erradas.

**Independent Test**: Percorrer as telas que mostram dinheiro (eventos, financeiro, comissões,
pagamentos, gastos, orçamento, usuários/salários) e confirmar que todo valor está como
`R$ 0.000,00`.

**Acceptance Scenarios**:

1. **Given** um evento com venda de quatro mil reais, **When** abro a página do evento, **Then** o
   valor aparece como `R$ 4.000,00` (não `4000`, não `4,000.00`).
2. **Given** a aba de contratos/pagamentos do evento (que hoje mostra padrão americano), **When** a
   abro, **Then** os valores aparecem no padrão brasileiro.
3. **Given** qualquer valor com centavos (ex.: 1234,5), **When** é exibido, **Then** aparece com
   duas casas: `R$ 1.234,50`.

---

### User Story 2 - Digitar valor com formatação automática (Priority: P1)

Ao preencher um campo de valor (cachê, venda, salário, gasto, orçamento, etc.), o número é
formatado automaticamente no padrão brasileiro enquanto a pessoa digita — ela não precisa colocar
os pontos e a vírgula manualmente.

**Why this priority**: Evita erro de digitação (a causa de "4000" virar "40,00" ou vice-versa) e
deixa claro a grandeza do valor no momento em que se digita.

**Independent Test**: Em um campo de valor, digitar os dígitos de "quatro mil reais" e ver o campo
exibir `4.000,00`; ao salvar, o valor guardado é o número 4000.

**Acceptance Scenarios**:

1. **Given** um campo de valor vazio, **When** digito os dígitos de quatro mil, **Then** o campo
   mostra `4.000,00` já formatado.
2. **Given** um campo de valor preenchido e formatado, **When** salvo o formulário, **Then** o
   sistema guarda o valor numérico correto (4000), não o texto com pontos/vírgula.
3. **Given** um campo de valor já preenchido (edição), **When** abro o formulário, **Then** o valor
   aparece já formatado no padrão brasileiro.
4. **Given** um envio com erro de validação em outro campo, **When** a página recarrega, **Then** o
   valor digitado continua lá e continua formatado (não se perde nem "desformata").

---

### User Story 3 - Uma única fonte de formatação (Priority: P2)

A formatação para exibição e a máscara/conversão de digitação têm uma implementação única e
reutilizável, em vez de cópias espalhadas. Mudar a regra de formatação no futuro é feito em um só
lugar.

**Why this priority**: Hoje há várias cópias da mesma lógica (`_fmt_brl`, `br_money`, filtro `brl`,
formatação inline no template). Cópias divergem e recriam o problema. Consolidar previne regressão.

**Independent Test**: Procurar no código pela formatação de dinheiro e confirmar que exibição usa um
único filtro e que os campos de digitação usam um único helper de máscara (uma classe/attr comum).

**Acceptance Scenarios**:

1. **Given** o código de exibição, **When** procuro como um valor vira texto `R$`, **Then** há um
   único filtro/local responsável.
2. **Given** os campos de digitação de valor, **When** os inspeciono, **Then** todos usam o mesmo
   mecanismo de máscara (mesma marcação), sem máscaras ad-hoc por tela.

---

### Edge Cases

- **Valor zero / vazio**: campo vazio continua vazio (placeholder), não vira `0,00` forçado; exibição
  de zero é `R$ 0,00`.
- **Valor nulo (sem valor cadastrado)**: exibição mostra `R$ 0,00` ou traço, conforme já feito hoje;
  não quebra.
- **Colar um valor** já formatado (`R$ 1.234,56`) ou no formato americano num campo: o sistema
  normaliza para o padrão brasileiro / número correto ao salvar.
- **Estorno / valor negativo** (comissões): preserva o sinal e formata o módulo (ex.: `- R$ 50,00`).
- **Valores grandes** (milhões): milhar agrupado corretamente (`R$ 1.000.000,00`).
- **Backend recebe o texto mascarado**: precisa converter de volta para número antes de salvar; nunca
  persistir a string com pontos/vírgula.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Todo valor monetário **exibido** em qualquer tela MUST estar no padrão brasileiro:
  ponto no milhar, vírgula no decimal, duas casas. Valor cru (`4000`) e padrão americano
  (`4,000.00`) são proibidos.
- **FR-002**: A exibição de dinheiro MUST usar uma **única** fonte de formatação reutilizável (um
  filtro no backend), eliminando as cópias/divergências atuais e a formatação americana inline.
- **FR-003**: Todo campo de **entrada** de valor monetário MUST formatar automaticamente enquanto o
  usuário digita, para o padrão brasileiro (milhar com ponto, decimal com vírgula).
- **FR-004**: A máscara de digitação MUST usar um **único** helper reutilizável no frontend
  (marcação/classe comum), sem máscaras ad-hoc por tela.
- **FR-005**: Ao enviar o formulário, o valor MUST ser convertido de volta para número antes de
  salvar; o sistema NÃO MUST persistir a string formatada.
- **FR-006**: Em erro de validação, o valor digitado MUST ser preservado e continuar formatado
  (coerente com o Princípio V — nunca limpar o que o usuário preencheu).
- **FR-007**: Campos de valor em **edição** MUST exibir o valor já formatado ao abrir.
- **FR-008**: Campo vazio MUST permanecer vazio (não forçar `0,00`); zero exibido é `R$ 0,00`.
- **FR-009**: Valores negativos (estornos) MUST manter o sinal e formatar o módulo.
- **FR-010**: A mudança NÃO MUST alterar nenhum valor já gravado no banco (é formatação de
  apresentação/entrada, não de dado).

### Key Entities

- Nenhuma entidade nova. A feature afeta **apresentação** (templates) e **entrada** (formulários) de
  valores monetários já existentes (venda, cachê, adicional de viagem, salário, gasto, contrato,
  pagamento, comissão, orçamento, transporte, etc.). Sem mudança de banco.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos valores monetários exibidos nas telas estão no padrão brasileiro (0
  ocorrências de valor cru ou americano).
- **SC-002**: 100% dos campos de entrada de valor formatam automaticamente para o padrão brasileiro
  ao digitar.
- **SC-003**: 0 valores gravados no banco são alterados pela mudança (comparação antes/depois).
- **SC-004**: A formatação de exibição tem 1 fonte única e a máscara de entrada tem 1 helper único
  (0 cópias divergentes remanescentes para os fluxos cobertos).
- **SC-005**: Em 100% dos formulários de valor, um erro de validação preserva o valor digitado e
  formatado.

## Assumptions

- O símbolo `R$` continua como hoje (rótulo/adorno ao lado do campo ou prefixo no texto exibido); a
  máscara cuida do **número** (separadores e casas decimais).
- A feature cobre os fluxos de valor monetário já existentes no sistema; PDFs/integrações que já usam
  formatação brasileira são reaproveitados/consolidados na fonte única quando viável.
- Sem mudança de banco e sem migration — é apresentação e entrada.
- Reaproveitar o filtro `brl` e os parsers `_parse_brl` já existentes como base da fonte única, em
  vez de criar algo paralelo (Princípio I).
