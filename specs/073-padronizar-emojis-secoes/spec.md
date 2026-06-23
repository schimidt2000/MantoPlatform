# Feature Specification: Padronizar emojis das seções da home

**Feature Branch**: `073-padronizar-emojis-secoes`

**Created**: 2026-06-22

**Status**: Draft

**Input**: "Padronize os emojis dessas seções, pfv: casting (pessoinhas), ensaio (pode ser um show),
figurino (um vestido vermelho)." (Print da home: Casting, Ensaio e Figurino sem emoji; Nota Fiscal
🧾 e Comercial 💰 já com emoji.)

## Contexto

Na home, os cabeçalhos das seções de tarefas estão **inconsistentes**: **Nota Fiscal** (🧾) e
**Comercial** (💰) têm emoji no rótulo, mas **Casting**, **Ensaio** e **Figurino** não têm. O
cliente quer padronizar, adicionando emojis representativos às três seções que faltam.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cabeçalhos de seção com emoji padronizado (Priority: P1) 🎯 MVP

Como usuário da home, quero que todas as seções de tarefas tenham um emoji no rótulo (como Nota
Fiscal e Comercial já têm), para uma leitura visual consistente.

**Independent Test**: Abrir a home e verificar que Casting, Ensaio e Figurino exibem um emoji antes
do nome, no mesmo padrão de Nota Fiscal e Comercial.

**Acceptance Scenarios**:

1. **Given** a home, **When** vejo a seção **Casting**, **Then** o rótulo mostra **👥 Casting**
   (pessoas).
2. **Given** a home, **When** vejo a seção **Ensaio**, **Then** o rótulo mostra **🎭 Ensaio** (show).
3. **Given** a home, **When** vejo a seção **Figurino**, **Then** o rótulo mostra **👗 Figurino**
   (vestido).
4. **Given** a home, **When** vejo **Nota Fiscal** e **Comercial**, **Then** continuam com 🧾 e 💰
   (inalterados).

### Edge Cases

- Apenas os rótulos dos cabeçalhos mudam; contadores/badges de status (ex.: "205 pendentes") e o
  comportamento das seções permanecem iguais.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O cabeçalho **Casting** MUST exibir o emoji **👥** antes do nome.
- **FR-002**: O cabeçalho **Ensaio** MUST exibir o emoji **🎭** antes do nome.
- **FR-003**: O cabeçalho **Figurino** MUST exibir o emoji **👗** antes do nome.
- **FR-004**: Os cabeçalhos **Nota Fiscal** (🧾) e **Comercial** (💰) MUST permanecer inalterados.
- **FR-005**: Nenhuma outra mudança de comportamento/contadores/layout além do emoji no rótulo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: As 5 seções da home (Casting, Ensaio, Figurino, Nota Fiscal, Comercial) exibem emoji
  no rótulo.
- **SC-002**: Casting=👥, Ensaio=🎭, Figurino=👗; Nota Fiscal e Comercial inalterados.
- **SC-003**: Contadores e funcionamento das seções permanecem idênticos.

## Assumptions

- Escolha dos emojis conforme o cliente: pessoas (👥) p/ Casting, show (🎭) p/ Ensaio, vestido (👗)
  p/ Figurino.
- Mudança puramente visual no template da home (sem modelo, sem backend, sem migration).
