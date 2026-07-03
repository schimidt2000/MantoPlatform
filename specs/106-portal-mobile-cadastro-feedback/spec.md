# Feature Specification: Checkup Mobile do Portal + Feedback de Validação no Cadastro

**Feature Branch**: `106-portal-mobile-cadastro-feedback`

**Created**: 2026-07-02

**Status**: Draft

**Input**: User description: "Preciso que faça um checkup geral no portal para otimizar a visualização no celular, pois a maioria das pessoas acessa pelo smartphone. E também preciso que verifique se no /cadastro está funcionando aquela regra que te passei de: se tiver algo preenchido errado e a pessoa tentar enviar, a tela ir até lá ou ter algum feedback mais claro para a pessoa."

## Contexto

Duas frentes voltadas ao público externo (talentos), que acessa quase sempre pelo celular:

1. **Portal do Artista** (`/portal` — 12 telas: login, primeiro acesso, home, perfil, histórico,
   avaliação de eventos, figurino, termo, senhas): fazer um checkup sistemático de usabilidade
   mobile e corrigir os problemas encontrados (rolagem horizontal, alvos de toque pequenos,
   textos minúsculos, elementos que quebram mal em telas estreitas, inconsistências visuais).
2. **Cadastro público** (`/cadastro`): a regra de feedback de validação (constituição, Princípio
   V) foi verificada e está **incompleta** hoje — grupos de opções obrigatórios (idiomas,
   habilidades) mostram um alerta genérico do navegador (`alert`) e campos obrigatórios vazios
   dependem só do balão nativo do navegador, sem destaque visual no campo nem garantia de que a
   pessoa veja onde está o problema num formulário longo.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Portal confortável no celular (Priority: P1)

Um talento abre o portal no smartphone (tela ~360–390px). Todas as telas — login, home com
convites e eventos, perfil, histórico financeiro, avaliação de evento, figurino, termo e telas
de senha — apresentam conteúdo legível sem zoom, sem rolagem horizontal, com botões e links
confortáveis para o polegar e layout que aproveita bem a tela estreita.

**Why this priority**: é o principal canal de acesso dos talentos ("a maioria acessa pelo
smartphone") — qualquer atrito aqui atinge todos os usuários externos do portal.

**Independent Test**: percorrer as 12 telas do portal num viewport de 360×740 e 390×844:
zero scroll horizontal, alvos de toque adequados, textos legíveis, fluxos completáveis
(aceitar convite, editar perfil, avaliar evento, ver figurino, trocar senha).

**Acceptance Scenarios**:

1. **Given** qualquer tela do portal aberta em viewport ≤ 390px, **When** a página carrega,
   **Then** não há rolagem horizontal nem conteúdo cortado.
2. **Given** a home do portal em tela estreita, **When** exibida com convites, eventos e
   resumo financeiro, **Then** cabeçalho, cards e badges se reorganizam sem sobreposição e as
   ações (aceitar/recusar convite, abrir avaliação) têm alvo de toque confortável (≥ 44px).
3. **Given** o perfil do portal no celular, **When** o talento edita campos e medidas,
   **Then** os campos ocupam a largura disponível, sem pares espremidos lado a lado.
4. **Given** o histórico financeiro no celular, **Then** valores e badges são legíveis e o
   resumo se adapta à largura sem quebrar o padrão monetário brasileiro.
5. **Given** as telas do portal comparadas entre si, **Then** mantêm a mesma identidade visual
   do sistema (cores via paleta, espaçamentos consistentes).

---

### User Story 2 - Feedback claro de validação no cadastro público (Priority: P2)

Uma pessoa preenche o formulário público de cadastro no celular. Ao tocar em "Enviar cadastro"
com campos obrigatórios vazios ou grupos sem seleção (idiomas/habilidades), a tela **rola até o
primeiro problema**, o campo é **destacado visualmente** (borda de erro + leve tremida) com uma
**mensagem clara junto dele**, e o foco vai para o campo. Nada do que já foi preenchido se
perde. O envio nunca é bloqueado em silêncio.

**Why this priority**: o cadastro é a porta de entrada de novos talentos; a regra exigida
(feedback visível no campo) está incompleta hoje e formulários longos no celular tornam o balão
nativo fácil de passar despercebido.

**Independent Test**: no celular, enviar o formulário com (a) campo texto obrigatório vazio no
meio da página, (b) nenhum idioma marcado, (c) nenhuma habilidade marcada — em todos os casos a
tela rola até o item, destaca-o com mensagem visível e mantém os dados preenchidos.

**Acceptance Scenarios**:

1. **Given** o formulário com um campo obrigatório vazio fora da área visível, **When** a
   pessoa tenta enviar, **Then** a página rola até o campo, ele ganha destaque de erro (borda +
   tremida), recebe foco e exibe mensagem clara ao lado — sem `alert` do navegador.
2. **Given** nenhum idioma (ou habilidade) selecionado, **When** tenta enviar, **Then** o grupo
   inteiro é destacado com a mensagem correspondente visível junto ao grupo e a tela rola até ele.
3. **Given** múltiplos campos com problema, **When** tenta enviar, **Then** todos os campos
   inválidos ficam destacados e a rolagem vai para o PRIMEIRO deles.
4. **Given** um campo destacado com erro, **When** a pessoa o corrige, **Then** o destaque do
   campo some (não fica erro "fantasma").
5. **Given** qualquer tentativa de envio bloqueada, **Then** os valores preenchidos permanecem
   intactos e o botão de enviar volta ao estado normal.

---

### Edge Cases

- Campo obrigatório escondido/desabilitado por regra condicional (ex.: CPF desabilitado para
  estrangeiro, "Outro" gênero sem texto): a validação respeita o estado atual — nunca rola até
  um campo invisível/desabilitado.
- Campos de arquivo obrigatórios (fotos/documento): recebem o mesmo destaque e mensagem; após
  erro de servidor, o aviso existente de "anexe novamente os arquivos" permanece.
- Erro retornado pelo servidor (ex.: CPF duplicado): a caixa de erro no topo continua, e a
  página abre já posicionada nela.
- Teclado virtual aberto na hora do scroll: o campo destacado fica visível (scroll centraliza).
- Telas do portal com dados longos (nome de evento comprido, muitos convites): quebram linha
  sem estourar a largura.
- Telefone/DDI no cadastro em telas muito estreitas (~320px): continua utilizável (já há
  regra de empilhamento; não regredir).

## Requirements *(mandatory)*

### Functional Requirements

**Portal (US1)**

- **FR-001**: Nenhuma tela do portal PODE apresentar rolagem horizontal ou conteúdo cortado em
  viewports de 320–430px.
- **FR-002**: Ações principais do portal (botões, links de navegação, aceitar/recusar convite)
  DEVEM ter alvo de toque ≥ 44px de altura em telas de toque.
- **FR-003**: Nenhum texto informativo do portal PODE ficar abaixo de 12px; conteúdo essencial
  deve ser legível sem zoom.
- **FR-004**: Elementos lado a lado (cabeçalho, pares de campos, grids de resumo) DEVEM
  reorganizar-se (empilhar/quebrar) em telas estreitas sem sobreposição ou espremido.
- **FR-005**: Correções visuais DEVEM usar a paleta/variáveis existentes — cores hardcoded
  encontradas no caminho devem ser trocadas por variáveis quando tocadas.
- **FR-006**: Fluxos do portal (login, primeiro acesso, aceitar/recusar convite, editar perfil,
  avaliar evento, ver figurino, trocar/recuperar senha) DEVEM permanecer funcionais após o
  checkup — sem regressão de comportamento.

**Cadastro (US2)**

- **FR-007**: Ao tentar enviar com campos inválidos, o sistema DEVE rolar até o primeiro campo
  com problema, destacá-lo (borda de erro + animação breve), focá-lo e exibir mensagem clara
  junto ao campo — substituindo o `alert` e não dependendo apenas do balão nativo do navegador.
- **FR-008**: Grupos de seleção obrigatórios (idiomas, habilidades) DEVEM receber o mesmo
  tratamento: destaque visual do grupo + mensagem visível junto dele + rolagem até ele.
- **FR-009**: TODOS os campos inválidos DEVEM ficar destacados simultaneamente (não só o
  primeiro); a rolagem/foco vai para o primeiro.
- **FR-010**: O destaque de erro de um campo DEVE desaparecer quando o campo é corrigido.
- **FR-011**: Nenhuma tentativa de envio bloqueada PODE limpar dados preenchidos, e o botão de
  envio DEVE voltar ao estado normal (não ficar travado em "Enviando…").
- **FR-012**: Campos desabilitados/ocultos por regras condicionais NÃO PODEM ser alvo de
  validação nem de rolagem.

### Key Entities

Sem entidades novas — mudanças de apresentação e validação de formulário; nenhum dado
persistido muda.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 12/12 telas do portal sem rolagem horizontal e sem conteúdo cortado em 360px e
  390px de largura.
- **SC-002**: 100% das ações principais do portal com alvo de toque ≥ 44px.
- **SC-003**: No cadastro, em 100% das tentativas de envio inválidas a pessoa vê o campo
  problemático destacado com mensagem e a tela posicionada nele — zero bloqueios silenciosos e
  zero `alert` genérico.
- **SC-004**: Zero perda de dados preenchidos em qualquer tentativa de envio bloqueada.
- **SC-005**: Zero regressões nos fluxos existentes do portal e do cadastro (roteiros completos
  executáveis do início ao fim).

## Assumptions

- "Portal" = Portal do Artista (`/portal/*`, 12 telas) — não inclui o sistema interno (que é
  usado em desktop pela equipe); o `/cadastro` entra pela segunda frente.
- O checkup corrige problemas de apresentação/usabilidade sem redesenhar telas nem mudar
  fluxos/negócio.
- A validação aprimorada do cadastro é no navegador (antes do envio), mantendo as validações
  de servidor existentes como estão (CPF duplicado, arquivos etc.).
- Padrão de referência para o feedback de campo: o mesmo da constituição do projeto (borda
  vermelha + "shake" + foco + mensagem junto ao campo), aplicado de forma consistente.
- Telas de referência: 320px (mínimo suportado), 360/390px (alvo principal), 430px (maior
  smartphone comum).
