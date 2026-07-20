# Feature Specification: Animação suave na galeria de fotos do produto

**Feature Branch**: `143-animacao-galeria-produto`

**Created**: 2026-07-20

**Status**: Draft

**Input**: User description: "ficou podre a forma como ao fazer o swipe ou tem a troca de proporção, parece que dá um tranco na página. Eu quero que tenha uma animação suave. E pode escrever isso na constituição, para ter movimento, isso é sofisticação."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trocar de foto sem "tranco" visual (Priority: P1)

Na página do produto do catálogo (feature 142), trocar de foto — seja clicando numa
miniatura, seja arrastando (swipe) — hoje muda a foto e redimensiona a moldura
instantaneamente, sem nenhuma transição. O resultado visual é um corte seco: a pessoa vê
a foto antiga, e no instante seguinte já está tudo diferente (imagem e formato da
moldura), o que parece um problema/travamento, não uma navegação intencional.

**Why this priority**: é a reclamação direta do usuário sobre uma superfície pública —
afeta a impressão que qualquer cliente final tem do catálogo, que é a vitrine da Manto.

**Independent Test**: abrir um produto com fotos de proporções bem diferentes entre si e
trocar de foto (por miniatura e por swipe); confirmar visualmente que a transição — tanto
da imagem quanto do formato da moldura — acontece de forma suave, não instantânea.

**Acceptance Scenarios**:

1. **Given** a página de um produto com várias fotos, **When** a pessoa clica numa
   miniatura diferente da atual, **Then** a troca da foto e o ajuste do formato da moldura
   acontecem com uma transição suave e perceptível, não um corte instantâneo.
2. **Given** a mesma página, **When** a pessoa arrasta a foto principal para o lado
   (swipe), **Then** o movimento do arrasto é visível durante o gesto e a transição até a
   próxima/anterior foto continua suave — sem o "salto seco" relatado hoje.
3. **Given** a pessoa configurou o dispositivo para reduzir movimento/animações (
   preferência de acessibilidade do sistema), **When** ela troca de foto, **Then** a
   transição é reduzida/removida, respeitando essa preferência — a troca continua
   funcionando, só sem o efeito de movimento.

---

### Edge Cases

- Trocar de foto muito rápido (várias vezes seguidas antes da transição anterior
  terminar): não pode travar a página nem deixar a galeria num estado inconsistente
  (foto errada, moldura com formato errado) — a navegação mais recente sempre prevalece.
- Primeira foto carregando (antes de qualquer troca): não precisa de transição de
  entrada especial — só as trocas subsequentes precisam ser suaves.
- Produto com uma única foto: nada a animar (sem miniaturas nem swipe com efeito).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Trocar de foto (por miniatura ou por swipe) MUST acontecer com uma
  transição visual suave — nunca um corte instantâneo entre o estado antes e depois.
- **FR-002**: O ajuste do formato da moldura da foto principal (proporção mudando
  conforme a foto atual, feature 142) MUST acontecer de forma suave, sincronizada com a
  troca da imagem — não pode "pular" de um tamanho pro outro de forma abrupta.
- **FR-003**: Durante um gesto de arrastar (swipe), a pessoa MUST ver a foto reagir ao
  movimento do dedo/mouse em tempo real (não só o resultado final ao soltar).
- **FR-004**: O sistema MUST respeitar a preferência de "reduzir movimento" do sistema
  operacional da pessoa — quando ativada, a transição é removida ou bem reduzida, mas a
  navegação entre fotos continua funcionando normalmente.
- **FR-005**: Trocar de foto repetidamente e rápido MUST sempre terminar num estado
  visual consistente (a foto certa, com a moldura no formato certo) — sem travar nem
  ficar com uma transição "presa" no meio.

### Key Entities

Nenhuma entidade de dados nova — feature é inteiramente de comportamento visual
(client-side) sobre a galeria já existente (feature 142).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Ninguém que troca de foto no catálogo público tem a sensação de que a
  página "travou" ou "deu um problema" — a transição é percebida como intencional.
- **SC-002**: A troca de foto (clique ou swipe) mantém a mesma sensação de fluidez em
  qualquer combinação de proporções de foto (quadrada, retrato, paisagem).
- **SC-003**: Quem usa "reduzir movimento" no sistema não perde a capacidade de navegar
  entre fotos, só a animação.

## Assumptions

- Esta feature é puramente sobre a qualidade da transição visual — não muda nenhuma
  regra funcional já entregue na feature 142 (ordem das fotos, escolha de capa, botão de
  categoria, limiar de swipe).
- "Animação suave" é tratada como uma característica que passa a valer para toda troca de
  estado visual perceptível em superfícies públicas — por isso a atualização da
  constituição do projeto (registrada como uma decisão à parte, não uma questão desta
  spec) formaliza esse padrão para features futuras, não só para a galeria.
- Fora de escopo: qualquer efeito visual novo além de suavizar as transições já
  existentes (não é um pedido de zoom, efeito 3D, parallax etc.).
