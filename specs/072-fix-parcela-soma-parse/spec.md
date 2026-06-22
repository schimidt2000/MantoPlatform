# Feature Specification: Corrigir soma das parcelas (Parcelado por datas)

**Feature Branch**: `072-fix-parcela-soma-parse`

**Created**: 2026-06-22

**Status**: Draft

**Input**: "Não é a primeira vez que aparece esse erro no parcelado (datas); imagino que seja algo
relacionado a formatação." (Print: duas parcelas de R$ 9.400,00 mostram "Soma das parcelas: R$
18.80 ⚠️ difere do valor de venda".)

## Contexto

No bloco **Parcelado (datas)** da seção comercial do evento, a soma das parcelas é calculada
errado quando os valores estão no formato brasileiro com milhar. Duas parcelas de **R$ 9.400,00**
(total **R$ 18.800,00**) são somadas como **R$ 18,80** — o valor "9.400,00" é lido como "9,40".

**Causa raiz**: a soma é calculada ao **carregar a página** por um script que roda **antes** de a
biblioteca de máscara monetária terminar de carregar. Sem a máscara disponível, o cálculo cai num
leitor genérico (`parseFloat`) que não entende o padrão brasileiro (ponto de milhar), lendo
"9.400,00" como 9,40. Quando o usuário digita depois, a máscara já carregou e a soma fica certa —
mas a exibição inicial está errada (e gera o alerta falso de divergência).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Soma correta ao abrir a tela (Priority: P1) 🎯 MVP

Como comercial, quero que a soma das parcelas apareça **correta já ao abrir** a tela, mesmo com
valores na casa dos milhares, sem alerta falso de divergência.

**Independent Test**: Abrir um evento com duas parcelas de R$ 9.400,00 → a soma mostra
**R$ 18.800,00** e **não** acusa divergência (pois bate com o valor de venda).

**Acceptance Scenarios**:

1. **Given** duas parcelas de R$ 9.400,00 já salvas, **When** abro a tela do evento, **Then** vejo
   "Soma das parcelas: R$ 18.800,00" (sem alerta de divergência se igual à venda).
2. **Given** parcelas com valores na casa dos milhares, **When** edito/adiciono/removo parcelas,
   **Then** a soma permanece correta a cada alteração.
3. **Given** a soma igual ao valor de venda, **When** a tela carrega, **Then** **não** aparece o
   aviso "difere do valor de venda".
4. **Given** a soma diferente do valor de venda, **When** a tela carrega, **Then** aparece o aviso
   corretamente (ex.: parcelas somando R$ 18.000 num evento de R$ 18.800).

### Edge Cases

- **Sem máscara carregada ainda**: a soma deve estar correta mesmo assim (não depende da ordem de
  carregamento).
- **Campo vazio**: conta como zero.
- **Valores com centavos** (ex.: 9.400,50): somados corretamente.
- O mesmo cálculo aparece nas **notas fiscais** (feature 069) — deve seguir a mesma regra correta.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A soma das parcelas MUST interpretar corretamente valores no padrão brasileiro com
  milhar (ex.: "9.400,00" = 9.400), inclusive **na carga inicial** da página.
- **FR-002**: O resultado da soma MUST ser exibido no padrão brasileiro (ex.: "R$ 18.800,00").
- **FR-003**: O aviso "difere do valor de venda" MUST aparecer **apenas** quando a soma realmente
  diferir do valor de venda.
- **FR-004**: O cálculo MUST ser correto independentemente da **ordem de carregamento** da máscara
  monetária (não pode depender de a biblioteca já estar pronta).
- **FR-005**: A mesma correção MUST valer para a soma das **notas fiscais** (mesmo componente de
  cálculo), evitando o mesmo erro.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Duas parcelas de R$ 9.400,00 somam **R$ 18.800,00** na carga e após edição (100% dos
  casos), sem alerta falso.
- **SC-002**: O aviso de divergência só aparece quando há divergência real.
- **SC-003**: Valores com centavos e campos vazios são somados corretamente.

## Assumptions

- Os campos de valor são sempre do tipo "máscara calculadora" (todos os dígitos = centavos), então
  ler os dígitos e dividir por 100 é a interpretação correta e consistente com o backend.
- Correção puramente de interface (sem modelo, sem migration, sem mudança de backend).
