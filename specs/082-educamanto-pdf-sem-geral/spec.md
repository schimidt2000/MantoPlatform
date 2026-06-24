# Feature Specification: Remover "Geral" da seção "O que está incluso" no PDF

**Feature Branch**: `082-educamanto-pdf-sem-geral`

**Created**: 2026-06-23

**Status**: Draft

**Input**: "Na parte 'O que está incluso', retire o 'Geral:' e o texto que vem depois. Deixe apenas
Iluminação, Sonorização e Cenografia. O conteúdo do 'Geral' já é mencionado logo após o título, como
já está sendo feito."

## Contexto

No PDF do EducaManto, a descrição longa ("O QUE ESTÁ INCLUSO", após as formas de pagamento) começa
com a linha **"Geral:"** seguida de um resumo. Esse resumo geral já aparece como a **descrição curta
logo abaixo do título do pacote**, então repeti-lo em "O que está incluso" é redundante. O cliente
quer remover a linha "Geral" dessa seção, mantendo **Iluminação**, **Sonorização** e **Cenografia**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - "O que está incluso" sem a linha Geral (Priority: P1) 🎯 MVP

Como cliente que recebe o orçamento, quero que "O que está incluso" mostre apenas os detalhes de
Iluminação, Sonorização e Cenografia, sem repetir o resumo geral (que já aparece abaixo do título).

**Acceptance Scenarios**:

1. **Given** um PDF de qualquer plano, **When** vejo "O QUE ESTÁ INCLUSO", **Then** **não** aparece a
   linha "Geral:" nem o texto dela.
2. **Given** o mesmo PDF, **When** vejo "O QUE ESTÁ INCLUSO", **Then** continuam aparecendo as linhas
   de **Iluminação** (cênica completa/básica conforme o plano), **Sonorização** e **Cenografia**.
3. **Given** o resumo geral, **When** vejo a área **abaixo do título** do pacote, **Then** ele
   continua aparecendo ali (descrição curta), inalterado.

### Edge Cases

- Plano Econômica (que não tem "Iluminação") continua mostrando Sonorização e Cenografia, sem o
  "Geral".

## Requirements *(mandatory)*

- **FR-001**: A seção "O que está incluso" do PDF MUST **omitir** a linha "Geral" (rótulo + texto)
  para todos os planos.
- **FR-002**: A seção MUST manter as linhas de **Iluminação**, **Sonorização** e **Cenografia**
  conforme o plano.
- **FR-003**: A descrição curta (resumo geral) **abaixo do título** MUST permanecer inalterada.

## Success Criteria *(mandatory)*

- **SC-001**: Nenhum PDF mostra "Geral:" na seção "O que está incluso".
- **SC-002**: As linhas de Iluminação/Sonorização/Cenografia seguem presentes conforme o plano.
- **SC-003**: O resumo geral abaixo do título permanece.

## Assumptions

- Mudança apenas de conteúdo do PDF (remover um item da lista da descrição longa). Sem modelo, sem
  migration.
