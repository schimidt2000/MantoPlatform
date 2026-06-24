# Feature Specification: EducaManto — cap do acréscimo, transporte fixo, ocultar config, descrições no PDF

**Feature Branch**: `080-educamanto-vendedor-pdf`

**Created**: 2026-06-23

**Status**: Draft

**Input**: "O acréscimo do vendedor não pode ser maior que o valor original (ex.: sem nota 12.000 →
acréscimo máx. 12.000, total 24k). A única opção de transporte deve ser van com carretinha (pode
esconder); o nº de pessoas também pode esconder; e no lugar de 'opcional' escrever '(APENAS SE FOR
FORA DA CIDADE DE SÃO PAULO)'. As configurações do pacote devem ficar escondidas para o vendedor,
aparecendo só para super admin. No PDF, encaixar mais duas informações (ver `planos.md`): a descrição
curta do tipo logo abaixo do título; a descrição longa depois das formas de pagamento."

## Contexto

Refinamentos finais da calculadora EducaManto e do PDF, separando o que o vendedor vê do que o super
admin vê e enriquecendo o PDF com as descrições dos planos (`planos.md`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cap do acréscimo do vendedor (Priority: P1) 🎯 MVP

Como gestor, quero impedir que o acréscimo do vendedor ultrapasse o valor original (sem nota), para
não dobrar o preço além do permitido.

**Acceptance Scenarios**:

1. **Given** o sem nota = R$ 12.000, **When** o vendedor tenta um acréscimo > 12.000, **Then** o
   acréscimo é **limitado a 12.000** (total máximo 24.000) e há um aviso do máximo.
2. **Given** um acréscimo ≤ original, **When** calculo, **Then** é aceito normalmente.

### User Story 2 - Transporte fixo (van c/ carretinha) e campos ocultos (Priority: P1)

Como vendedor, quero o transporte simplificado: sempre **van com carretinha**, sem escolher tipo nem
informar pessoas (ocultos), e o título indicando que é **apenas fora da cidade de SP**.

**Acceptance Scenarios**:

1. **Given** a seção de transporte, **When** abro, **Then** **não** vejo seleção de van/carro,
   carretinha ou nº de pessoas; o cálculo usa **van com carretinha** e o nº de pessoas do catering.
2. **Given** o título da seção, **When** vejo, **Then** está escrito "Transporte (APENAS SE FOR FORA
   DA CIDADE DE SÃO PAULO)".

### User Story 3 - Configurações do pacote só para super admin (Priority: P1)

Como gestor, quero que as "Configurações do pacote" (margens, desconto, taxa interna) **não apareçam
para o vendedor**, só para o super admin.

**Acceptance Scenarios**:

1. **Given** um vendedor (não super admin), **When** abre a calculadora, **Then** **não** vê o painel
   "Configurações do pacote".
2. **Given** um super admin, **When** abre, **Then** vê o painel normalmente.

### User Story 4 - Duas descrições do tipo no PDF (Priority: P1)

Como cliente, quero ver no PDF uma descrição curta do tipo logo abaixo do título e uma descrição
detalhada do plano após as formas de pagamento.

**Acceptance Scenarios**:

1. **Given** um pacote "… - Master/Intermediário/Econômica", **When** gero o PDF, **Then** logo
   abaixo do título aparece a **descrição curta** do tipo.
2. **Given** o mesmo PDF, **When** olho **depois das formas de pagamento**, **Then** aparece a
   **descrição longa** do plano (itens de cenografia/iluminação/sonorização do `planos.md`).
3. **Given** um pacote cujo nome contém o tipo (ex.: "Uma Aventura Animal - Master"), **When** gero,
   **Then** o tipo é detectado pelo nome (substring) e as descrições corretas aparecem.

### Edge Cases

- Pacote sem tipo reconhecível no nome: PDF sai sem as descrições (sem erro).
- Acréscimo aplicado a vários pacotes: o limite considera o valor original do pacote em tela.
- A descrição longa deve caber na mesma página do pacote (uma página por pacote).

## Requirements *(mandatory)*

- **FR-001**: O acréscimo do vendedor MUST ser **limitado ao valor original** (sem nota, sem o
  acréscimo) do pacote em tela; tentativas acima são limitadas a esse máximo, com aviso.
- **FR-002**: O transporte MUST usar sempre **van com carretinha**; a seleção de tipo/carretinha/
  carros e o **nº de pessoas** MUST ficar **ocultos** (pessoas = catering da apresentação).
- **FR-003**: O título da seção de transporte MUST ser "Transporte (APENAS SE FOR FORA DA CIDADE DE
  SÃO PAULO)".
- **FR-004**: O painel "Configurações do pacote" MUST aparecer **apenas para super admin**.
- **FR-005**: No PDF, a **descrição curta** do tipo MUST aparecer **logo abaixo do título** do pacote.
- **FR-006**: No PDF, a **descrição longa** do plano (conteúdo de `planos.md`) MUST aparecer **depois
  das formas de pagamento**.
- **FR-007**: O tipo MUST ser detectado pelo **nome do pacote** (substring: Master / Intermediário /
  Econômica — aceitando "Básico" como Econômica).
- **FR-008**: Tudo cabe em **uma página por pacote**.

### Key Entities

- **Pacote (existente)**: o nome contém o tipo; o tipo define as descrições curta e longa.
- **Planos (`planos.md`)**: fonte do conteúdo das descrições longas por tipo.

## Success Criteria *(mandatory)*

- **SC-001**: Acréscimo nunca excede o valor original (limitado + aviso).
- **SC-002**: Vendedor não vê tipo/carretinha/pessoas nem "Configurações do pacote"; transporte usa
  van c/ carretinha; título com "(APENAS SE FOR FORA DA CIDADE DE SÃO PAULO)".
- **SC-003**: PDF mostra descrição curta abaixo do título e descrição longa após as formas de
  pagamento, na mesma página.

## Assumptions

- "Valor original" do cap = valor sem nota do pacote **sem** o acréscimo (após desconto), na tela.
- Terceiro tipo é "Econômica" (`planos.md`); "Básico" é tratado como Econômica.
- Descrição curta = textos já existentes (077) por tipo; descrição longa = `planos.md`.
- Apenas calculadora + PDF do EducaManto; sem modelo, sem migration.
