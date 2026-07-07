# Feature Specification: Cliente na Criação de Evento + Busca sem Acentos

**Feature Branch**: `114-cliente-criar-evento-busca-sem-acento`

**Created**: 2026-07-06

**Status**: Draft

**Input**: User description: "Preciso que na tela de criar novo evento logo no começo já tenha um campo para associar um cliente, funcionando na mesma lógica e forma que a associação na tela do evento da seção comercial. E preciso que nesses dois lugares, ao pesquisar, os acentos sejam ignorados."

## Contexto

Hoje o evento nasce sem cliente na tela "Criar evento" — a associação só existe depois, na
seção Dados da Venda da página do evento (features 094/100: múltiplos clientes com relação,
busca por nome/telefone, cadastro rápido inline). Resultado: todo evento criado vira
pendência "sem cliente" na home. Além disso, a busca de clientes é sensível a acentos:
procurar "jose" não encontra "José".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Associar cliente já na criação do evento (Priority: P1)

O comercial abre "Criar evento" e, logo no começo do formulário, encontra o mesmo bloco de
clientes da página do evento: busca por nome/telefone com sugestões, cadastro rápido de
cliente novo (nome + telefone), múltiplos clientes com tipo de relação (Contratante,
Assessora, …) e remoção. Ao criar o evento, as associações são salvas junto.

**Acceptance Scenarios**:

1. **Given** a tela de criar evento, **Then** o bloco de clientes aparece no começo do
   formulário com busca, cadastro rápido e relação — mesma forma da tela do evento.
2. **Given** um cliente selecionado com relação "Contratante", **When** o evento é criado,
   **Then** a associação aparece na página do evento (Dados da Venda) exatamente como se
   tivesse sido feita lá.
3. **Given** um erro de validação na criação (ex.: sem título), **When** o formulário
   re-renderiza, **Then** os clientes selecionados são preservados.
4. **Given** nenhum cliente selecionado, **When** o evento é criado, **Then** a criação
   segue normalmente (o campo é opcional na criação; a exigência continua valendo no save
   da venda, como hoje).

---

### User Story 2 - Busca de clientes ignora acentos (Priority: P1)

Nos dois lugares (criação de evento e página do evento — mesma busca), pesquisar "jose"
encontra "José da Conceição"; pesquisar "conceicao" também; pesquisar com acento ("josé")
encontra clientes gravados sem acento. Idem na página de lista de clientes.

**Acceptance Scenarios**:

1. **Given** cliente "José da Conceição", **When** busco "jose" ou "conceicao", **Then** ele
   aparece nas sugestões.
2. **Given** cliente "Jose Silva" (sem acento), **When** busco "josé", **Then** ele aparece.
3. **Given** busca por telefone, **Then** continua funcionando como hoje.

## Requirements *(mandatory)*

- **FR-001**: A tela de criar evento DEVE ter, no começo do formulário, o bloco de
  associação de clientes com a MESMA lógica e forma da página do evento (busca, cadastro
  rápido, múltiplos + relação, remoção) — componente compartilhado, não uma cópia.
- **FR-002**: As associações escolhidas DEVEM ser salvas na criação do evento (incluindo o
  cliente principal exibido nas telas de resumo), idênticas às feitas na página do evento.
- **FR-003**: Erro de validação na criação NÃO PODE perder os clientes já selecionados.
- **FR-004**: A busca de clientes (sugestões do evento/criação e lista de clientes) DEVE
  ignorar acentos nos dois sentidos (termo e dado com ou sem acento), sem case-sensitivity.
- **FR-005**: O campo é opcional na criação; a exigência de cliente no save da venda
  (feature 094) permanece inalterada.
- **FR-006**: A associação na página do evento NÃO PODE mudar de comportamento (mesmo
  componente, zero regressão).

## Success Criteria *(mandatory)*

- **SC-001**: Evento criado com cliente já sai da pendência "sem cliente" da home sem
  nenhum passo extra.
- **SC-002**: 100% das buscas com/sem acento retornam os mesmos resultados nos testes.
- **SC-003**: Zero regressão no editor de clientes da página do evento.

## Assumptions

- "Logo no começo" = primeiro bloco do formulário de criação, antes dos dados do evento.
- Opcional na criação (o fluxo de venda continua exigindo cliente ao salvar) — evita travar
  a criação rápida de eventos operacionais.
- "Nesses dois lugares" = as duas telas usam o mesmo serviço de busca; a correção de acentos
  vale para ele e também para a busca da lista de clientes (mesma regra, consistência).
