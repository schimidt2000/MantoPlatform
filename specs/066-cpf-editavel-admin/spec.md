# Feature Specification: CPF do talento editável no site (apenas admin)

**Feature Branch**: `066-cpf-editavel-admin`

**Created**: 2026-06-20

**Status**: Draft

**Input**: User description: "Preciso que o CPF dos talentos seja alterável no site apenas por admin; ficar trocando pelo banco é ruim."

## Contexto

Hoje o CPF do talento é **somente leitura** na tela de edição ("não editável") — para corrigir um
CPF errado é preciso alterar direto no banco (Railway/Postgres), o que é trabalhoso e arriscado.
O cliente quer poder **editar o CPF pela própria plataforma**, mas de forma controlada: **apenas o
admin (super admin)** pode fazer essa alteração. Os demais perfis que editam talento continuam
**sem** acesso ao CPF.

> Observação: isto **reverte** a decisão anterior de "CPF só pelo banco". A nova política é: CPF
> editável no site, restrito a super admin, com validação e registro em auditoria.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin corrige o CPF de um talento (Priority: P1) 🎯 MVP

Como super admin, quero editar o CPF de um talento na tela de edição, para corrigir um cadastro
errado sem precisar mexer no banco de dados.

**Why this priority**: É o pedido central — tirar a dependência de alterar pelo banco.

**Independent Test**: Como super admin, abrir a edição de um talento, alterar o CPF para um valor
válido e salvar; o novo CPF fica gravado.

**Acceptance Scenarios**:

1. **Given** um super admin na edição de um talento, **When** altera o CPF para um valor válido e
   salva, **Then** o CPF é atualizado e exibido no perfil.
2. **Given** um super admin, **When** informa um CPF **inválido** (não tem 11 dígitos), **Then** a
   alteração é recusada com mensagem clara e o CPF anterior é mantido.
3. **Given** um super admin, **When** informa um CPF **já usado por outro talento**, **Then** a
   alteração é recusada com mensagem clara (CPF é único) e o CPF anterior é mantido.

---

### User Story 2 - Não-admin não altera CPF (Priority: P1)

Como empresa, quero que apenas o super admin altere CPF; os demais perfis que editam talento
(ex.: casting) **não** devem ver o campo editável nem conseguir alterá-lo, para proteger um dado
sensível.

**Why this priority**: Sem isso, abrir a edição do CPF exporia o dado a mais perfis.

**Acceptance Scenarios**:

1. **Given** um usuário que edita talento mas **não** é super admin, **When** abre a edição,
   **Then** o CPF aparece **somente leitura** (como hoje).
2. **Given** esse usuário, **When** tenta enviar uma alteração de CPF (ex.: via formulário
   adulterado), **Then** o CPF **não** é alterado.

---

### Edge Cases

- **CPF com máscara** (pontos/traço) digitado pelo admin: aceito, normalizando para apenas
  dígitos antes de salvar.
- **CPF igual ao atual**: salvar não causa erro (sem mudança).
- **Campo deixado vazio pelo admin**: o CPF atual é mantido (não apaga um CPF existente).
- **CPF duplicado**: recusado (é identificador único do talento).
- A alteração de CPF é registrada em **auditoria** (quem alterou e quando), sem expor o número no
  texto do log.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O super admin MUST conseguir editar o CPF do talento pela tela de edição.
- **FR-002**: Usuários que editam talento mas **não** são super admin MUST ver o CPF apenas em
  leitura e MUST **não** conseguir alterá-lo (nem por envio adulterado).
- **FR-003**: Ao salvar, o CPF MUST ser normalizado para **apenas dígitos** e MUST ter **11
  dígitos**; caso contrário, a alteração é recusada com mensagem clara.
- **FR-004**: O CPF MUST permanecer **único** entre talentos; tentativa de usar um CPF já
  existente em outro talento é recusada com mensagem clara.
- **FR-005**: Campo de CPF vazio no envio MUST manter o CPF atual (não apaga).
- **FR-006**: A alteração de CPF MUST ser registrada em auditoria (ator + ação), sem incluir o
  número do CPF no texto do registro.

### Key Entities

- **Talento (existente)**: possui CPF (identificador único, apenas dígitos). Esta feature muda
  **quem** pode editar o CPF (super admin) e adiciona validação na edição; não muda o formato de
  armazenamento.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um super admin corrige o CPF de um talento pela plataforma, sem tocar no banco, em
  poucos cliques.
- **SC-002**: 100% das tentativas de alterar CPF por não-admin são bloqueadas (campo bloqueado e
  servidor recusa).
- **SC-003**: 100% das alterações com CPF inválido (≠ 11 dígitos) ou duplicado são recusadas, sem
  corromper o CPF atual.
- **SC-004**: Toda alteração de CPF fica registrada em auditoria.

## Assumptions

- "Admin" = perfil **SUPERADMIN**. Os demais editores de talento (ex.: CASTING) seguem sem acesso
  ao CPF.
- CPF é armazenado como **apenas dígitos** (mesmo formato já usado na importação); a validação
  exige 11 dígitos e unicidade — sem validação de dígito verificador (fora do escopo).
- A feature **reverte** a política anterior ("CPF só pelo banco"): agora é editável no site,
  restrito a super admin.
- A edição ocorre na tela de edição de talento já existente; sem nova tela.
