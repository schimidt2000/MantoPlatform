# Feature Specification: Feedback Público por Token em React

**Feature Branch**: `164-feedback-publico-react`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Migrar a tela pública de feedback da cliente (/avaliar/<token>,
hoje Jinja em app/feedback/routes.py + templates feedback/public.html e invalid.html) para o app
frontend/apps/public em React, como 4ª e última fatia da US5 (Superfícies Públicas) da migração
144 — depois do catálogo (161), cadastro de talentos (162) e formulários dinâmicos (163). A
cliente de um evento recebe um link único (token aleatório associado ao evento) sem exigir
login, avalia de 1 a 5 estrelas a experiência com a equipe, opcionalmente marca etiquetas
(positivas se 5 estrelas, de atenção se menos) e deixa um comentário. Rate limiting no envio.
Token inválido/inexistente mostra uma tela de link inválido. A geração do link (ação
autenticada, comercial, na tela do evento) NÃO faz parte desta fatia — é uma ação interna, já
fora do escopo de superfícies públicas (e a tela de evento em si já migrou para React nas fatias
da US2, sem repor esse botão — fica registrado como débito a resolver fora desta fatia). Com
esta fatia, a US5 (Superfícies Públicas) fica 100% concluída."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cliente avalia a experiência através do link recebido (Priority: P1)

Uma cliente que contratou um evento recebe um link único (enviado pela equipe comercial) e, sem
precisar criar conta ou fazer login, avalia de 1 a 5 estrelas como foi a experiência com a
equipe, opcionalmente marca o que mais se destacou (ou onde pode melhorar) e deixa um comentário.

**Why this priority**: é o fluxo inteiro — sem ele a tela não tem propósito nenhum; é o único
motivo de o link existir.

**Independent Test**: abrir o link de um evento com token válido, escolher uma nota de 1 a 5
estrelas, ver as etiquetas correspondentes aparecerem, marcar algumas (opcional), escrever um
comentário (opcional) e enviar — a avaliação é salva e uma tela de agradecimento é exibida.

**Acceptance Scenarios**:

1. **Given** um link de avaliação com token válido, **When** a cliente escolhe 5 estrelas,
   **Then** aparecem etiquetas positivas (ex.: "Atuação Impecável", "Pontualidade") para marcar,
   não as de atenção.
2. **Given** o mesmo link, **When** a cliente escolhe uma nota de 1 a 4 estrelas, **Then**
   aparecem etiquetas de atenção (ex.: "Atraso", "Comunicação") para marcar, não as positivas.
3. **Given** o formulário de avaliação, **When** a cliente envia sem informar o nome ou sem
   escolher uma nota, **Then** o envio é recusado com uma mensagem clara sobre o que falta,
   mantendo o que já foi preenchido.
4. **Given** um envio válido (nome + nota, etiquetas e comentário opcionais), **When** a cliente
   confirma o envio, **Then** a avaliação é salva e uma tela de agradecimento aparece no lugar do
   formulário.

---

### Edge Cases

- O que acontece quando o token do link não existe ou está incorreto? Uma tela informa que o
  link não é válido, sem expor detalhes técnicos, sugerindo confirmar o link ou pedir um novo.
- O que acontece se a cliente enviar excesso de tentativas em pouco tempo? O envio é recusado
  temporariamente com uma mensagem amigável (mesmo limite de hoje).
- O que acontece se a cliente mudar de nota depois de já ter marcado etiquetas? As etiquetas da
  categoria anterior (positivas/atenção) são desmarcadas ao trocar de faixa de nota, evitando
  enviar uma combinação inconsistente (ex.: etiqueta de atenção junto com 5 estrelas).
- O que acontece se o evento não tiver mais dados suficientes para exibir (ex.: sem data)? A
  tela mostra o que houver disponível (nome do evento é sempre exibido; a data só aparece quando
  existir).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE exibir a tela pública de avaliação para um token válido, sem exigir
  autenticação, mostrando o nome do evento (e a data, quando disponível).
- **FR-002**: O sistema DEVE exigir nome da cliente e uma nota de 1 a 5 estrelas para aceitar o
  envio; etiquetas e comentário são sempre opcionais.
- **FR-003**: O sistema DEVE exibir etiquetas positivas quando a nota for 5, e etiquetas de
  atenção quando a nota for de 1 a 4 — nunca as duas categorias ao mesmo tempo.
- **FR-004**: O sistema DEVE recusar etiquetas que não pertençam à categoria correspondente à
  nota enviada (proteção contra manipulação do envio).
- **FR-005**: O sistema DEVE recusar o envio quando faltar nome ou nota válida, mostrando uma
  mensagem de erro clara e preservando os dados já preenchidos.
- **FR-006**: O sistema DEVE exibir uma tela de "link inválido" (sem expor detalhes técnicos)
  quando o token não corresponder a nenhum evento.
- **FR-007**: O sistema DEVE limitar a taxa de tentativas de envio por visitante numa janela de
  tempo, recusando temporariamente o excesso.
- **FR-008**: O sistema DEVE exibir uma tela de agradecimento após o envio bem-sucedido, no
  lugar do formulário.
- **FR-009**: O sistema NÃO DEVE exigir login em nenhum momento desta tela.

### Key Entities

- **ClientFeedback (Feedback da cliente)**: já existe no sistema — esta funcionalidade apenas
  cria novos registros através de uma nova superfície (React), sem alterar sua estrutura.
- **CalendarEvent.feedback_token**: já existe — usado somente para localizar o evento associado
  ao link; sua geração (ação autenticada da equipe comercial) está fora de escopo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma cliente consegue abrir o link, avaliar e enviar o feedback em menos de 1
  minuto, em qualquer tela de 320–430px de largura, sem rolagem horizontal.
- **SC-002**: 100% dos envios sem nome ou sem nota válida recebem uma mensagem de erro clara,
  sem perda do que já foi preenchido.
- **SC-003**: Zero regressão funcional em relação à versão hoje em produção: os mesmos dados de
  entrada produzem o mesmo registro de feedback salvo.
- **SC-004**: Um token inexistente sempre mostra a tela de link inválido, nunca um erro técnico
  cru.

## Assumptions

- A geração do link de avaliação (`POST /events/<id>/gerar-link-feedback`, ação autenticada da
  equipe comercial) permanece fora do escopo desta fatia — é uma ação interna, não uma
  superfície pública. Hoje esse botão só existe na tela de evento em Jinja
  (`event_detail.html`), que já foi substituída pela tela de evento em React nas fatias da US2 —
  a ausência desse botão na tela React é um débito preexistente, não introduzido nem resolvido
  por esta fatia (fica registrado para tratamento futuro, fora do escopo de Superfícies
  Públicas).
- Nenhuma regra de negócio nova é introduzida: toda validação e persistência hoje presentes na
  versão Jinja são preservadas exatamente, apenas re-expostas via API JSON.
- O design visual segue os mesmos padrões visuais já estabelecidos para o app público
  (`frontend/apps/public`, iniciado na feature 161).
- A rota Jinja `/avaliar/<token>` permanece ativa em paralelo (mesmo critério das fatias
  anteriores da US5).
