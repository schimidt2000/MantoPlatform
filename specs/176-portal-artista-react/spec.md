# Feature Specification: Portal do Artista — App React (fatia 1)

**Feature Branch**: `176-portal-artista-react`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "Desenvolver o aplicativo isolado e mobile-first para os artistas/talentos (frontend/apps/portal). Telas: Login do talento, Minha Agenda de Ensaios/Eventos, Meus Convites de Casting (Aceitar/Recusar), Minha Ficha de Figurino e Atualização de Fotos/Documentos."

## User Scenarios & Testing *(mandatory)*

<!--
  Escopo desta fatia: as 5 telas explicitamente pedidas. O Portal do Artista hoje (Jinja/
  vanilla, `app/talent_portal`) tem mais fluxos (primeiro acesso, aceite de termos, esqueci
  minha senha, edição de perfil completo, avaliação de eventos) que NÃO fazem parte desta
  fatia — continuam servidos pela versão clássica. Um talento cujo login ainda depende de um
  desses fluxos (troca de senha obrigatória, termos não aceitos) é direcionado à versão
  clássica para completá-los, e só então usa o app novo.
-->

### User Story 1 - Login do talento (Priority: P1)

Um talento acessa o app do Portal do Artista pelo celular, entra com CPF (ou e-mail, para
estrangeiros) e senha, e chega na sua área logada.

**Why this priority**: sem login não há acesso a nenhuma outra tela — é o pré-requisito de tudo.

**Independent Test**: acessar a URL do portal, entrar com CPF/e-mail e senha de um talento já
com conta ativa, e confirmar que a sessão abre e o talento vê sua área logada.

**Acceptance Scenarios**:

1. **Given** um talento com conta ativa (senha definida, termos aceitos), **When** entra com
   CPF ou e-mail e a senha correta, **Then** a sessão abre e ele é levado à sua Agenda.
2. **Given** um talento digita CPF/e-mail ou senha incorretos, **When** tenta entrar, **Then**
   vê uma mensagem amigável de erro, sem detalhar qual dos dois campos errou (mesma regra do
   portal clássico).
3. **Given** um talento cuja conta ainda exige trocar a senha ou aceitar os termos de uso,
   **When** faz login com sucesso, **Then** é direcionado à versão clássica do portal para
   completar essa etapa antes de usar o app novo.
4. **Given** um talento logado, **When** toca em "Sair", **Then** a sessão encerra e ele volta à
   tela de login.

---

### User Story 2 - Minha Agenda de Ensaios/Eventos (Priority: P1)

Um talento logado consulta os eventos em que está escalado — os que ainda vão acontecer e o
histórico dos que já aconteceram — junto com a situação do pagamento de cada um.

**Why this priority**: é a razão principal de acesso ao portal no dia a dia — saber a agenda e
se o cachê já foi pago.

**Independent Test**: como talento com eventos futuros e passados, abrir a Agenda e conferir que
os eventos futuros aparecem em ordem cronológica e os passados no histórico, cada um com a
situação de pagamento.

**Acceptance Scenarios**:

1. **Given** o talento tem eventos futuros confirmados, **When** abre a Agenda, **Then** vê a
   lista ordenada por data (mais próximo primeiro), com nome, data/horário e local do evento.
2. **Given** o talento tem eventos passados confirmados, **When** consulta o histórico, **Then**
   vê a lista ordenada do mais recente para o mais antigo, com a situação do cachê (pago/
   pendente).
3. **Given** o talento não tem nenhum evento futuro, **When** abre a Agenda, **Then** vê uma
   mensagem amigável de lista vazia, não um erro.
4. **Given** um evento teve alguma alteração de horário/local não confirmada pelo talento (sinal
   já existente no sistema clássico), **When** ele abre a Agenda, **Then** vê um aviso destacado
   nesse evento.

---

### User Story 3 - Meus Convites de Casting (Aceitar/Recusar) (Priority: P1)

Um talento logado vê os convites de casting pendentes e decide aceitar ou recusar cada um.

**Why this priority**: ação mais sensível ao tempo do app — casting e produção dependem da
resposta do talento para fechar a escalação do evento.

**Independent Test**: como talento com um convite pendente, aceitar um e confirmar que ele sai
da lista de pendentes e aparece na Agenda como confirmado; recusar outro e confirmar que ele sai
da lista de pendentes.

**Acceptance Scenarios**:

1. **Given** o talento tem convites pendentes, **When** abre a tela de convites, **Then** vê
   cada um com nome do evento, data e local.
2. **Given** um convite pendente, **When** o talento toca em "Aceitar", **Then** o convite sai
   da lista de pendentes e o evento passa a aparecer como confirmado na Agenda.
3. **Given** um convite pendente, **When** o talento toca em "Recusar", **Then** o sistema pede
   confirmação antes de efetivar (ação difícil de desfazer) e, após confirmar, o convite sai da
   lista de pendentes.
4. **Given** o talento não tem convites pendentes, **When** abre a tela, **Then** vê uma
   mensagem amigável de lista vazia.

---

### User Story 4 - Minha Ficha de Figurino (Priority: P2)

Um talento logado, escalado em um evento, consulta a ficha de figurino do seu personagem
naquele evento (foto de referência e observações).

**Why this priority**: consulta de apoio para o dia do evento — importante, mas usada com menor
frequência que agenda/convites.

**Independent Test**: como talento escalado (convite aceito ou pendente) em um evento com ficha
de figurino cadastrada, abrir a ficha a partir do evento na Agenda e ver a foto/observações.

**Acceptance Scenarios**:

1. **Given** o talento está escalado num evento com ficha de figurino cadastrada, **When** abre
   a ficha a partir do evento, **Then** vê a foto de referência e as observações do personagem.
2. **Given** o evento tem mais de um personagem atribuído ao mesmo talento, **When** ele abre a
   ficha, **Then** vê uma ficha por personagem, sem duplicar.
3. **Given** o talento NÃO está escalado no evento, **When** tenta acessar a ficha diretamente
   pela URL, **Then** o sistema nega o acesso.
4. **Given** o evento ainda não tem ficha de figurino cadastrada, **When** o talento abre a
   tela, **Then** vê uma mensagem amigável explicando que ainda não há ficha disponível.

---

### User Story 5 - Atualização de Fotos/Documentos (Priority: P3)

Um talento logado atualiza sua foto de rosto, foto de corpo inteiro e o arquivo da CNH quando
precisa corrigir ou renovar algum desses itens.

**Why this priority**: mantém o cadastro atualizado, mas é usada esporadicamente (não no dia a
dia como agenda/convites).

**Independent Test**: como talento logado, enviar uma nova foto de rosto e confirmar que ela
substitui a anterior; enviar um novo arquivo de CNH e confirmar que ele substitui o anterior.

**Acceptance Scenarios**:

1. **Given** o talento está na tela de Fotos/Documentos, **When** envia uma nova foto de rosto
   ou de corpo inteiro (formato aceito), **Then** ela substitui a foto anterior e é exibida
   imediatamente.
2. **Given** o talento envia um arquivo de CNH (imagem ou PDF), **When** o upload conclui,
   **Then** o arquivo substitui o anterior, se houver.
3. **Given** o talento tenta enviar um arquivo em formato não aceito ou maior que o limite,
   **When** o upload é tentado, **Then** vê uma mensagem de erro amigável explicando o motivo,
   sem perder o restante da tela preenchida.

### Edge Cases

- O que acontece se a sessão do talento expirar enquanto ele usa o app (ex.: aceitar um convite
  já expirado de sessão)? A ação retorna erro de autenticação e o app leva o talento de volta ao
  login, sem perder o que ele via na tela anterior após novo login (mesma navegação).
- Como o sistema trata um talento tentando aceitar/recusar um convite que não é dele (URL
  adulterada)? Nega o acesso (mesma regra do portal clássico: a consulta já filtra pelo talento
  da sessão).
- Como o sistema trata um convite que já foi aceito/recusado antes (duplo clique, duas abas)? A
  ação é idempotente — repetir aceitar/recusar não deve gerar erro nem estado inconsistente.
- O que acontece se o talento não tiver nenhum evento, nenhum convite e nenhuma ficha? Cada tela
  mostra seu próprio estado vazio amigável, nunca um erro.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir que um talento entre no app com CPF (ou e-mail, para
  talentos estrangeiros sem CPF) e senha, reaproveitando a mesma verificação de credenciais já
  usada no portal clássico.
- **FR-002**: O sistema DEVE encerrar a sessão do talento ao acionar "Sair".
- **FR-003**: O sistema DEVE direcionar à versão clássica do portal (fora do app novo) o login de
  um talento cuja conta ainda exija trocar a senha ou aceitar os termos de uso — essas duas
  etapas não são reproduzidas nesta fatia do app novo.
- **FR-004**: O sistema DEVE listar, na Agenda, os eventos futuros em que o talento está
  escalado com convite aceito, ordenados por data.
- **FR-005**: O sistema DEVE listar, no histórico da Agenda, os eventos passados em que o
  talento esteve escalado com convite aceito, com a situação de pagamento do cachê de cada um.
- **FR-006**: O sistema DEVE sinalizar, na Agenda, um evento que teve alteração ainda não
  reconhecida pelo talento.
- **FR-007**: O sistema DEVE listar os convites de casting pendentes do talento, com nome,
  data e local do evento.
- **FR-008**: O sistema DEVE permitir que o talento aceite um convite pendente, passando o
  evento a contar como confirmado na Agenda.
- **FR-009**: O sistema DEVE permitir que o talento recuse um convite pendente, com confirmação
  antes de efetivar a ação (irreversível pelo próprio talento).
- **FR-010**: O sistema DEVE exibir a ficha de figurino (foto de referência + observações) de
  cada personagem do talento em um evento em que ele esteja escalado (convite aceito ou
  pendente), negando acesso a quem não estiver escalado nesse evento.
- **FR-011**: O sistema DEVE permitir que o talento envie uma nova foto de rosto e uma nova foto
  de corpo inteiro, substituindo a anterior.
- **FR-012**: O sistema DEVE permitir que o talento envie um novo arquivo de CNH, substituindo o
  anterior, se houver.
- **FR-013**: O sistema DEVE rejeitar arquivos em formato não aceito ou acima do limite de
  tamanho, com mensagem amigável, preservando o restante da tela preenchida.
- **FR-014**: O sistema DEVE manter as rotas Jinja legadas de `app/talent_portal` funcionando
  sem regressão (padrão strangler-fig do projeto) — nenhuma das telas fora do escopo desta
  fatia (primeiro acesso, esqueci a senha, termos, avaliação de eventos, edição de perfil
  completo) é reproduzida no app novo agora.

### Key Entities *(include if feature involves data)*

- **Talento (Talent)**: identidade que faz login no app (CPF ou e-mail + senha); dono das
  fotos/documentos e do histórico de eventos.
- **Escalação (EventRole)**: vínculo entre talento e evento — status do convite (pendente/
  aceito/recusado), cachê e situação de pagamento, personagem interpretado.
- **Evento (CalendarEvent)**: data, horário, local; contém as escalações.
- **Ficha de Figurino (FigurinoSheet)**: foto de referência + observações de um personagem.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um talento consegue entrar no app e ver sua Agenda em menos de 30 segundos numa
  conexão de celular comum.
- **SC-002**: Um talento consegue aceitar ou recusar um convite de casting em no máximo 2 toques
  a partir da tela de convites.
- **SC-003**: 100% das telas do app novo funcionam sem rolagem horizontal entre 320px e 430px de
  largura (Princípio VIII).
- **SC-004**: Nenhuma rota Jinja legada de `app/talent_portal` quebra após esta fatia (paridade
  comportamental).

## Assumptions

- A sessão do app novo reaproveita o mesmo mecanismo de sessão já usado pelo portal clássico
  (cookie de sessão Flask, chave `talent_id`) — um talento autenticado num continua autenticado
  no outro, sem exigir dois logins.
- Talentos cuja conta ainda depende de primeiro acesso, troca de senha obrigatória, aceite de
  termos, recuperação de senha, avaliação de eventos ou edição de dados de perfil (além de
  fotos/CNH) usam a versão clássica do portal para essas etapas — fora do escopo desta fatia.
- "Documentos", no pedido do usuário, corresponde ao único arquivo de documento self-service já
  existente no modelo de dados do talento (arquivo da CNH); não há outro tipo de documento
  digitalizável hoje.
- Limite/formatos de arquivo para fotos e CNH seguem os mesmos já usados no portal clássico e no
  cadastro público (`app/cadastro`), sem novas restrições.
