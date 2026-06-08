# Feature Specification: Envio de "Criar evento" robusto a falhas

**Feature Branch**: `028-criar-evento-robusto`

**Created**: 2026-06-08

**Status**: Draft

**Input**: User description: "Tornar o envio do formulário de criar evento robusto a falhas: quando
houver erro (validação ou falha ao criar no Google Agenda), a tela deve rolar automaticamente até a
mensagem de erro; falhas de conexão com o Google Agenda devem mostrar um aviso amigável em vez de
tela de erro ou 'nada'; e o botão 'Adicionar à Agenda' deve voltar ao estado normal se o envio
falhar. Contexto: uma vendedora relatou que ao clicar não acontecia nada e nenhum erro aparecia."

## Contexto

Uma vendedora tentou criar um evento a partir de um orçamento e relatou que, ao clicar em
**"Adicionar à Agenda"**, **não acontecia nada e nenhum erro aparecia**. A investigação mostrou que o
código de criação funciona; o problema é de **feedback**: quando algo falha, hoje pode acontecer:

- A mensagem de erro de validação aparece **no topo de um formulário longo** — quem está embaixo (no
  botão) não vê e acha que "não aconteceu nada".
- Uma **falha ao criar no Google Agenda** que não seja "Google desconectado" cai numa **tela de erro
  genérica** (ou nada visível, se o servidor estava reiniciando), sem explicação amigável.
- Se o envio falha por conexão (ex.: servidor reiniciando durante um deploy), o botão pode **ficar
  travado em "Adicionando…"** e a pessoa não sabe se deve tentar de novo.

Esta feature elimina o "sumiço silencioso": todo desfecho de envio dá um retorno claro e visível.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Erro sempre visível (rola até a mensagem) (Priority: P1)

Quando o envio é recusado (validação ou falha ao salvar), a pessoa **vê a mensagem imediatamente** —
a tela leva o foco/rolagem até o erro, sem precisar procurar.

**Why this priority**: É a causa direta do problema relatado ("não aparece erro"). Sem isso, a pessoa
acha que o sistema travou.

**Independent Test**: Enviar o formulário com um erro (ex.: faltando um campo) estando rolado no fim
da página e confirmar que a tela sobe até a mensagem de erro automaticamente.

**Acceptance Scenarios**:

1. **Given** o formulário com um erro de validação e a página rolada até o botão, **When** clico em
   "Adicionar à Agenda", **Then** a tela rola automaticamente até a mensagem de erro e ela fica
   claramente visível.
2. **Given** uma falha ao criar no Google Agenda, **When** o formulário recarrega com o aviso,
   **Then** a tela mostra o aviso de forma destacada (sem precisar rolar para procurar).

---

### User Story 2 - Falha do Google Agenda com aviso amigável (Priority: P1)

Se o evento não pôde ser criado no Google Agenda, a pessoa vê um **aviso claro e amigável**
(explicando o que houve e o que fazer), em vez de uma tela de erro técnica ou de "nada".

**Why this priority**: Evita o pior cenário (tela de erro/branco) e orienta a pessoa a tentar de novo
ou avisar o suporte. O Google é uma dependência externa que pode falhar.

**Independent Test**: Simular indisponibilidade do Google Agenda e confirmar que o formulário volta
com um aviso amigável (não uma página de erro do servidor), preservando o que foi preenchido.

**Acceptance Scenarios**:

1. **Given** o Google Agenda indisponível/erro, **When** envio o formulário, **Then** vejo um aviso
   amigável ("Não foi possível criar o evento na agenda agora. Tente novamente…") e **não** uma tela
   de erro técnica.
2. **Given** essa falha, **When** o formulário recarrega, **Then** os dados que preenchi continuam lá
   (coerente com a política de nunca limpar o formulário).
3. **Given** o Google não está conectado, **When** envio, **Then** vejo um aviso amigável orientando a
   reconectar (em vez de mensagem técnica crua).

---

### User Story 3 - Botão se recupera de falha (sem travar em "Adicionando…") (Priority: P2)

Se o envio não se completar (ex.: conexão caiu, servidor reiniciando), o botão **volta ao estado
normal** e a pessoa recebe um aviso para tentar de novo — em vez de ficar preso em "Adicionando…".

**Why this priority**: Cobre o caso do relato (deploy/reinício no momento do clique). Sem isso, a
pessoa fica esperando indefinidamente sem saber o que fazer.

**Independent Test**: Iniciar um envio que não recebe resposta (conexão interrompida) e confirmar
que, após um tempo, o botão é reabilitado e aparece um aviso para tentar novamente.

**Acceptance Scenarios**:

1. **Given** que cliquei e o envio não recebeu resposta dentro de um tempo razoável, **When** esse
   tempo passa, **Then** o botão volta a ficar clicável e aparece um aviso para tentar de novo.
2. **Given** o envio bem-sucedido, **When** a página navega para o evento criado, **Then** nada do
   comportamento acima atrapalha (sem aviso falso de falha).

---

### Edge Cases

- **Reinício do servidor durante o clique**: a requisição não recebe resposta → botão se recupera +
  aviso (US3); nenhum evento duplicado é criado.
- **Falha após criar no Google mas antes de salvar internamente**: o aviso é amigável; se houver risco
  de duplicidade, a mensagem orienta a verificar a agenda antes de tentar de novo.
- **Erro de validação simples** (campo faltando): rola até o erro e destaca o campo (já existe
  destaque de campo; aqui garante-se a visibilidade da mensagem).
- **Vários erros ao mesmo tempo**: a tela rola até o bloco de erros (o primeiro).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Ao recarregar o formulário com erro(s), o sistema MUST levar a visualização até a
  mensagem de erro automaticamente (rolagem/scroll), de forma que ela fique visível sem procurar.
- **FR-002**: A mensagem/bloco de erro MUST ser visualmente destacada (já é um alerta; manter e
  garantir o destaque).
- **FR-003**: Uma falha ao criar o evento no Google Agenda (qualquer causa: desconectado,
  indisponível, erro da API) MUST resultar em um **aviso amigável** no formulário, nunca em uma tela
  de erro técnica do servidor.
- **FR-004**: Em qualquer falha de envio, os dados preenchidos MUST ser preservados (coerente com o
  Princípio V — nunca limpar o formulário).
- **FR-005**: Se o envio não se completar dentro de um tempo razoável (sem resposta), o botão
  "Adicionar à Agenda" MUST voltar ao estado clicável e o sistema MUST exibir um aviso para tentar
  novamente.
- **FR-006**: O comportamento de recuperação do botão NÃO MUST disparar aviso falso quando o envio
  é bem-sucedido (a navegação para a página do evento ocorre normalmente).
- **FR-007**: A proteção contra envio duplicado (clique duplo) MUST continuar valendo (não regredir
  o comportamento já existente).

### Key Entities

- Nenhuma entidade nova. A feature afeta o **fluxo de envio** do formulário de criação de evento
  (tela e tratamento de falha no servidor). Sem mudança de banco.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em 100% dos envios recusados, a mensagem de erro fica visível sem o usuário precisar
  rolar manualmente.
- **SC-002**: 0 telas de erro técnicas/brancas em falha do Google Agenda — 100% viram aviso amigável.
- **SC-003**: Em 100% das falhas de envio sem resposta, o botão se recupera e há aviso para tentar de
  novo (nenhum estado "Adicionando…" permanente).
- **SC-004**: 0 regressões na proteção de clique duplo e 0 perda de dados preenchidos em falha.

## Assumptions

- O "tempo razoável" para considerar que o envio não respondeu é da ordem de ~15 segundos (ajustável);
  o objetivo é cobrir reinício de servidor/conexão, não envios normais (que navegam antes disso).
- O escopo é o formulário de **criar evento** (`/events/new`). Outros formulários podem reaproveitar o
  padrão depois, mas não fazem parte desta entrega.
- Reaproveitar o alerta de erro e o handler de submit já existentes (Princípio I), sem reescrever o
  fluxo.
- Sem mudança de banco e sem migration.
