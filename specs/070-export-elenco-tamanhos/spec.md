# Feature Specification: Tamanhos (Top/Bottom/Calçado/Altura) no Exportar Elenco

**Feature Branch**: `070-export-elenco-tamanhos`

**Created**: 2026-06-22

**Status**: Draft

**Input**: "No botão exportar elenco precisa ter a opção de selecionar Top, Bottom, o número do
calçado e altura."

## Contexto

O modal "Exportar elenco" (na página do evento) gera um texto copiável com campos selecionáveis por
checkbox (Personagem, Nome, Nascimento, CPF, RG, Link documento). O cliente quer **quatro novas
opções**: **Top**, **Bottom**, **número do calçado** e **altura** — dados de figurino já existentes
no cadastro do talento.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Exportar tamanhos do elenco (Priority: P1) 🎯 MVP

Como casting/comercial, quero marcar Top, Bottom, calçado e altura ao exportar o elenco para enviar
as medidas do figurino junto com o restante das informações.

**Independent Test**: Abrir "Exportar elenco" num evento com talentos escalados, marcar Top, Bottom,
Calçado e Altura, gerar o texto e ver os valores de cada pessoa no resultado.

**Acceptance Scenarios**:

1. **Given** o modal de exportar elenco, **When** marco "Top", **Then** o texto gerado inclui o
   tamanho de cima de cada talento que o possui.
2. **Given** o modal, **When** marco "Bottom", "Calçado" e "Altura", **Then** o texto inclui esses
   campos para cada talento que os possui.
3. **Given** um talento sem um desses dados preenchidos, **When** gero o texto, **Then** aquele
   campo é **omitido** apenas para essa pessoa (sem mostrar valor vazio), como já ocorre com os
   demais campos.

### Edge Cases

- Talento com todos os campos vazios: a linha mantém os campos que existirem (ex.: só personagem).
- Nenhum campo selecionado: o texto sai vazio/sem aquele dado, igual ao comportamento atual.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O modal "Exportar elenco" MUST oferecer checkboxes para **Top**, **Bottom**,
  **Calçado** e **Altura**, no mesmo padrão dos campos existentes.
- **FR-002**: Ao gerar o texto, cada campo marcado MUST aparecer para cada talento que tiver o dado
  preenchido, com rótulo claro (ex.: "Top:", "Bottom:", "Calçado:", "Altura:").
- **FR-003**: Campos sem valor para um talento MUST ser omitidos para aquele talento (sem rótulo
  órfão).
- **FR-004**: Os novos campos MUST iniciar **desmarcados** (opcionais), preservando o texto padrão
  atual quando não selecionados.
- **FR-005**: Nenhuma mudança de dados é necessária — os valores vêm do cadastro do talento já
  existente (tamanho de cima, tamanho de baixo, calçado e altura).

### Key Entities

- **Talento (existente)**: já possui tamanho de cima, tamanho de baixo, número do calçado e altura.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: As quatro novas opções aparecem no modal e, quando marcadas, refletem no texto gerado.
- **SC-002**: Talentos sem um dado têm aquele campo omitido (sem rótulo vazio).
- **SC-003**: Com nenhuma das novas opções marcada, o texto é idêntico ao comportamento atual.

## Assumptions

- "Altura" é exibida em cm (valor inteiro já cadastrado), com sufixo "cm".
- Permissões inalteradas: o modal segue visível para CASTING/COMERCIAL/SUPERADMIN, como hoje.
- Mudança puramente de interface (sem modelo, sem migration).
