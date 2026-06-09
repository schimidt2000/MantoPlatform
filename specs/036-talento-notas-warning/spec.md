# Feature Specification: Anotações e warning do talento

**Feature Branch**: `036-talento-notas-warning` (sobre `035`)

**Created**: 2026-06-09

**Status**: Draft

**Input**: User description: "abrir um local na página de cada talento no banco de talentos onde podemos
fazer anotações importantes da pessoa. E também podemos colocar um warning, seja leve, moderado ou
grave. Essa classificação aparece ao lado do nome da pessoa no banco de talentos."

## Contexto

A equipe precisa registrar **observações internas** sobre cada talento (informações importantes que
ajudam na hora de escalar) e marcar um **nível de alerta (warning)**: **leve**, **moderado** ou
**grave**. Esse alerta deve aparecer **ao lado do nome** na lista do banco de talentos, para chamar
atenção rapidamente.

São informações **internas** (gestão), nunca exibidas ao próprio talento.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Anotações internas do talento (Priority: P1)

Na página do talento, a equipe autorizada registra anotações importantes sobre a pessoa e as edita
quando necessário.

**Why this priority**: É o registro de conhecimento sobre o talento — valor central da feature.

**Independent Test**: Escrever uma anotação na página do talento, salvar, recarregar e confirmar que
ela permanece.

**Acceptance Scenarios**:

1. **Given** a página de um talento, **When** escrevo uma anotação e salvo, **Then** ela fica
   registrada e visível ao reabrir.
2. **Given** uma anotação existente, **When** a edito e salvo, **Then** o novo texto substitui o
   anterior.
3. **Given** um usuário sem permissão de editar talento, **When** abre a página, **Then** não pode
   alterar a anotação (somente leitura ou oculto, conforme o acesso atual).

---

### User Story 2 - Nível de alerta (warning) (Priority: P1)

Na página do talento, a equipe define o nível de alerta: **nenhum**, **leve**, **moderado** ou
**grave**.

**Acceptance Scenarios**:

1. **Given** a página do talento, **When** escolho um nível de alerta e salvo, **Then** ele fica
   registrado.
2. **Given** um alerta definido, **When** o removo (nenhum), **Then** o talento deixa de ter alerta.

---

### User Story 3 - Alerta visível ao lado do nome no banco (Priority: P1)

Na lista do banco de talentos, talentos com alerta exibem uma **marca colorida ao lado do nome**
(leve / moderado / grave), com cores distintas, fácil de notar.

**Why this priority**: É o ponto pedido para dar visibilidade imediata do alerta.

**Acceptance Scenarios**:

1. **Given** um talento com alerta "grave", **When** vejo o banco de talentos, **Then** há uma marca
   vermelha ao lado do nome dele.
2. **Given** níveis diferentes, **When** vejo a lista, **Then** leve/moderado/grave têm cores
   distintas (ex.: amarelo / laranja / vermelho).
3. **Given** um talento sem alerta, **When** vejo a lista, **Then** não há marca nenhuma ao lado do
   nome.

---

### Edge Cases

- **Anotação vazia**: permitido (sem anotação); não quebra a página.
- **Nível inválido**: ignorado; vale apenas nenhum/leve/moderado/grave.
- **Talentos antigos**: sem anotação e sem alerta por padrão.
- **Privacidade**: anotação e alerta são internos — nunca aparecem no portal do talento.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A página do talento MUST ter um local para registrar e editar **anotações internas**.
- **FR-002**: A página do talento MUST permitir definir o **nível de alerta**: nenhum, leve, moderado
  ou grave.
- **FR-003**: Anotações e alerta MUST ser persistidos por talento.
- **FR-004**: A criação/edição de anotações e alerta MUST respeitar o controle de acesso de edição de
  talento já existente.
- **FR-005**: A lista do banco de talentos MUST exibir uma marca colorida **ao lado do nome** quando o
  talento tiver alerta, com cores distintas por nível; sem alerta, nada é exibido.
- **FR-006**: Anotações e alerta MUST ser internos — NÃO MUST aparecer no portal do talento.

### Key Entities

- **Talento (Talent)** — ganha dois atributos: **anotações internas** (texto livre) e **nível de
  alerta** (nenhum/leve/moderado/grave).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das anotações salvas permanecem após recarregar/reabrir a página.
- **SC-002**: 100% dos talentos com alerta exibem a marca correta (cor por nível) ao lado do nome no
  banco.
- **SC-003**: Talentos sem alerta não exibem marca em 100% dos casos.
- **SC-004**: Anotações/alerta nunca aparecem no portal do talento (0 vazamentos).

## Assumptions

- Níveis de alerta: **leve**, **moderado**, **grave** (+ **nenhum** = sem alerta). Cores sugeridas:
  leve = amarelo, moderado = laranja, grave = vermelho.
- Edição restrita a quem já pode editar talento (SUPERADMIN/CASTING); demais veem conforme o acesso
  atual da página.
- Requer ajuste de banco (dois campos no talento) — migration escrita à mão.
- Construído sobre a 035 (resumo de avaliações), incluída neste branch.
