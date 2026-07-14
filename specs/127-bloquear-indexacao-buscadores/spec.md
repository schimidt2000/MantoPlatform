# Feature Specification: Bloquear Indexação em Buscadores

**Feature Branch**: `127-bloquear-indexacao-buscadores`

**Created**: 2026-07-14

**Status**: Draft

**Input**: "Não quero que meu site seja indexado no Google de qualquer forma. Nada desse
sistema."

## Contexto

A Plataforma Manto é um sistema interno de gestão (ERP) com dados sensíveis de clientes,
talentos e financeiro — não é um site que deveria aparecer em resultados de busca. Além
das telas internas (atrás de login), o sistema tem superfícies **públicas** sem login
(formulários de pré-contrato em `/f/pre-contrato` e `/f/corporativo`, e outras telas
públicas do portal) que um buscador consegue rastrear normalmente hoje, já que nada no
sistema hoje pede para não ser indexado.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Nenhuma página nova é indexada a partir de agora (Priority: P1)

Um buscador (Google ou qualquer outro) tenta rastrear qualquer página do sistema —
pública ou por trás de login. O sistema informa claramente, em toda resposta, que aquela
página não deve ser indexada nem seguida, e além disso pede para não ser rastreado.

**Why this priority**: é o pedido central — sem isso, qualquer página nova ou já
existente continua sendo candidata a aparecer em buscas.

**Independent Test**: acessar qualquer URL do sistema (pública ou a tela de login) e
conferir que a resposta HTTP inclui a instrução de não indexar/não seguir, e que existe
um arquivo padrão de instruções para buscadores pedindo para não rastrear nada.

**Acceptance Scenarios**:

1. **Given** qualquer página do sistema, pública ou não, **When** a resposta é
   analisada, **Then** ela informa explicitamente que não deve ser indexada nem seguida.
2. **Given** um buscador que respeita o arquivo padrão de instruções de rastreamento,
   **When** ele consulta esse arquivo, **Then** a instrução é para não rastrear nada no
   site.
3. **Given** uma página pública nova criada no futuro, **When** ela é publicada, **Then**
   ela já nasce com a mesma instrução de não indexar, sem precisar de configuração extra
   por página.

### Edge Cases

- Uma página que já foi indexada por um buscador ANTES desta mudança: a instrução de não
  indexar vale a partir de agora, mas remover algo que já está nos resultados de busca
  pode não ser instantâneo nem estar sob controle do sistema (ver Assumptions).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Toda resposta do sistema, pública ou não, DEVE informar explicitamente que
  aquela página não pode ser indexada nem ter seus links seguidos por buscadores.
- **FR-002**: O sistema DEVE disponibilizar o arquivo padrão que buscadores consultam
  antes de rastrear um site, instruindo a não rastrear nenhuma parte dele.
- **FR-003**: A instrução de não indexar DEVE valer automaticamente para qualquer página
  nova do sistema, sem exigir que cada tela nova seja configurada individualmente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das páginas do sistema (testadas por amostragem: login, home, uma
  tela interna qualquer, os dois formulários públicos) respondem com a instrução de não
  indexar.
- **SC-002**: O arquivo de instruções para buscadores existe e nega rastreamento de tudo.

## Assumptions

- Bloquear indexação FUTURA está dentro do escopo e do controle do sistema (mudança de
  código). Remover páginas que **já** estejam indexadas nos resultados de busca depende
  de ferramentas do próprio Google (Search Console) que exigem comprovar posse do
  domínio — fora do que o código do sistema consegue fazer sozinho; fica registrado como
  ação que, se necessária, o usuário precisa fazer diretamente (fora desta feature).
- A instrução vale para o site inteiro, sem exceção — nenhuma tela (pública ou interna)
  fica de fora.
