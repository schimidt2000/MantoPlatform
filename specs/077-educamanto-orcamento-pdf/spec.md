# Feature Specification: Gerar orçamento PDF no EducaManto + histórico

**Feature Branch**: `077-educamanto-orcamento-pdf`

**Created**: 2026-06-23

**Status**: Draft

**Input**: "Botão de gerar orçamento no EducaManto: usa as informações já preenchidas, escolhe quais
pacotes mostrar; cada página do PDF é um pacote, com uma breve explicação no subtítulo (Master /
Intermediário / Básico). Usar o PDF de referência (`Orccamentos_Educamanto.pdf`). Precisa também de
histórico de orçamentos gerados, como na calculadora de orçamentos."

## Contexto

O EducaManto calcula o valor de um pacote (sem nota / com nota) a partir dos dias preenchidos
(1 sessão / 2 sessões), ensemble e transporte. O cliente quer um **botão "Gerar orçamento"** que,
usando o que já está preenchido, permita **escolher quais pacotes** entrar no orçamento e produza um
**PDF com uma página por pacote** — cada página com o nome do pacote, a explicação do pacote, os dias
e os valores (sem/com NF) e as formas de pagamento, seguindo o layout do PDF de referência. Além
disso, manter um **histórico** dos orçamentos gerados (como na calculadora de orçamentos).

### Decisão do cliente

- Os **pacotes já são** Master / Intermediário / Básico (são os próprios pacotes). A explicação de
  cada um é **fixa pelo nome**:
  - **Master**: "A Manto Produções se responsabiliza pela sonorização, iluminação completa e
    alimentação no dia do evento."
  - **Intermediário**: "A Manto Produções se responsabiliza pela sonorização, iluminação básica e
    alimentação no dia do evento."
  - **Básico**: "A Manto Produções se responsabiliza apenas pela sonorização básica. Iluminação e
    Alimentação no dia do evento por conta da parte contratante."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gerar PDF com os pacotes escolhidos (Priority: P1) 🎯 MVP

Como vendedor, quero clicar em "Gerar orçamento", escolher quais pacotes mostrar e baixar um PDF com
uma página por pacote, já com os valores do que preenchi.

**Independent Test**: Com dias preenchidos, clicar em "Gerar orçamento", marcar 2 pacotes, gerar →
sai um PDF de 2 páginas, cada uma com o pacote (nome, explicação, dias, VALOR SEM NF, VALOR COM NF,
formas de pagamento).

**Acceptance Scenarios**:

1. **Given** dias preenchidos, **When** clico em "Gerar orçamento", **Then** vejo a lista de pacotes
   com caixas de seleção (e um campo opcional de cliente).
2. **Given** pacotes marcados, **When** gero, **Then** o PDF tem **uma página por pacote escolhido**,
   na ordem dos pacotes.
3. **Given** cada página, **When** abro o PDF, **Then** vejo: nome do pacote, **breve explicação**,
   dias com 1 e 2 sessões, **VALOR SEM NF** e **VALOR COM NF** (os mesmos que a tela mostra para
   aquele pacote, incluindo o transporte preenchido) e as **formas de pagamento**.
4. **Given** nenhum pacote marcado, **When** tento gerar, **Then** recebo um aviso para escolher ao
   menos um.

### User Story 2 - Histórico de orçamentos gerados (Priority: P1)

Como vendedor, quero ver o histórico dos orçamentos gerados e poder baixar o PDF de novo, como na
calculadora de orçamentos.

**Independent Test**: Após gerar um orçamento, ele aparece no histórico (data, cliente, pacotes);
clicar em "Baixar PDF" reproduz o mesmo PDF.

**Acceptance Scenarios**:

1. **Given** um orçamento gerado, **When** abro o histórico, **Then** vejo a entrada com data,
   cliente (se informado) e os pacotes incluídos.
2. **Given** uma entrada do histórico, **When** clico em baixar, **Then** o PDF é reproduzido
   **igual** ao gerado (valores congelados no momento da geração).
3. **Given** muitas entradas, **When** abro o histórico, **Then** consigo buscar/filtrar (por
   cliente/data), como na calculadora.

### Edge Cases

- **Dias não preenchidos** (valor vazio): o botão avisa que é preciso preencher os dias antes.
- **Pacote sem explicação mapeada** (nome diferente de Master/Intermediário/Básico): a página sai
  sem o subtítulo de explicação (sem erro).
- **Transporte preenchido**: o valor por pacote no PDF inclui o transporte (igual à tela).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O EducaManto MUST ter um botão **"Gerar orçamento"** que abre a escolha de **quais
  pacotes** incluir (seleção múltipla) e um campo **opcional de cliente**.
- **FR-002**: O PDF gerado MUST conter **uma página por pacote** escolhido, na ordem dos pacotes.
- **FR-003**: Cada página MUST exibir: **nome do pacote**, **breve explicação** (fixa pelo nome),
  **dias com 1 sessão** e **dias com 2 sessões**, **VALOR SEM NF**, **VALOR COM NF** e as **formas de
  pagamento** padrão.
- **FR-004**: Os valores no PDF MUST ser os mesmos que a tela calcula para aquele pacote, com a
  configuração preenchida (dias/ensemble/transporte) — sem recalcular diferente.
- **FR-005**: O layout MUST seguir a **estrutura do PDF de referência** (cabeçalho com contato da
  Manto, título "ORÇAMENTO", nome do pacote, explicação, dias, valores, formas de pagamento).
- **FR-006**: O sistema MUST registrar cada orçamento gerado em um **histórico** (data, cliente,
  pacotes incluídos) e permitir **baixar de novo** o PDF a partir do histórico, reproduzindo o
  mesmo resultado (valores congelados).
- **FR-007**: O histórico MUST oferecer busca/filtro básico (por cliente/data), no estilo da
  calculadora de orçamentos.
- **FR-008**: A geração MUST exigir ao menos **um pacote** selecionado e os **dias preenchidos**.
- **FR-009**: O acesso MUST seguir os perfis que já usam o EducaManto.

### Key Entities

- **Orçamento gerado (novo)**: pertence a um usuário; guarda data, cliente (opcional) e um
  **instantâneo** do orçamento (configuração de dias/ensemble/transporte + lista de pacotes com seus
  valores sem/com NF), para reproduzir o PDF idêntico depois.
- **Pacote (existente)**: nome (Master/Intermediário/Básico) determina a explicação fixa.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: É possível gerar um PDF com N páginas = N pacotes escolhidos, cada página com nome,
  explicação, dias, valores sem/com NF e formas de pagamento.
- **SC-002**: Os valores no PDF batem com os exibidos na tela para os mesmos parâmetros.
- **SC-003**: O orçamento gerado aparece no histórico e pode ser baixado de novo, idêntico.
- **SC-004**: A geração é bloqueada sem pacote selecionado ou sem dias preenchidos.

## Assumptions

- O PDF de referência (`Orccamentos_Educamanto.pdf`) é um **modelo preenchido de exemplo**; o layout
  é **reproduzido** (mesma estrutura/textos e identidade visual da Manto), não sobreposto ao arquivo
  de exemplo.
- Os valores por pacote são **calculados na tela** (motor existente) e **congelados** no histórico
  no momento da geração (não recalculam com preços futuros) — coerente com "congelar o orçamento".
- Formas de pagamento são as do modelo: À Vista (PIX, 5% desconto), Reserva Programada (PIX, 50%+
  50%), Cartão de Crédito (parcelamento com taxas repassadas).
- Histórico é um módulo próprio do EducaManto (separado do histórico da calculadora), com o mesmo
  estilo de uso.
