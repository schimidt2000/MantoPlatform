# Feature Specification: Tags NFC nas peças 3D com página pública por código

**Feature Branch**: `255-tags-nfc`

**Created**: 2026-08-20

**Status**: Draft

**Input**: User description: "Tags NFC nas peças 3D (luminárias) com página pública por código — todo show entrega um presente impresso em 3D com tag NFC embutida; a tag grava uma URL imutável que abre uma página pública da Manto; todo o conteúdo é decidido pelo servidor a cada acesso, permitindo campanhas futuras (descontos, fotos/vídeos do evento da cliente) sem regravar tags."

## Visão Geral

Todo show da Manto entrega um presente impresso em 3D. O produto atual é uma luminária de marca própria (versão 1) com uma tag NFC embutida. A tag grava uma URL pública da Manto que a cliente abre encostando o celular — sem login, sem digitar nada.

O princípio central da feature: **a URL gravada na tag física é imutável e eterna; todo o conteúdo é decidido pelo servidor a cada acesso**. A tag é gravada uma única vez (e travada contra regravação); o que a página mostra evolui no servidor — hoje uma página institucional simples, no futuro campanhas segmentadas, descontos e as fotos/vídeos do evento da própria cliente — sem jamais tocar nas luminárias já entregues.

### Decisões de produto já tomadas

1. **Uma tag = uma unidade física = um código.** O código identifica a luminária individual; produto e cliente são atributos no sistema, não na URL.
2. **Formato do código**: `<prefixo do produto>-<sufixo aleatório de 6 caracteres sem ambiguidade>` (ex.: `01-K7M3QF`). O prefixo `01` identifica a linha/versão do produto (luminária v1) para organização humana; o sufixo aleatório impede que uma cliente adivinhe o código de outra — requisito de privacidade, pois no futuro a página terá conteúdo pessoal.
3. **URL pública**: `app.mantoproducoes.com.br/nfc/<código>`, sem login.
4. **Geração automática**: quando um show ganha um presente 3D de um produto habilitado para NFC, o sistema gera os códigos sozinho — um por unidade. A equipe copia a URL para a tag física ao montar a peça.
5. **Associação ao evento**: a tag aponta para o evento do show; a cliente vem de carona pelo evento. A associação pode ser feita/trocada depois pela equipe.
6. **Tag nunca é apagada**: código imutável; desativação apenas lógica. Página de tag desativada ou de código inexistente mostra o conteúdo padrão genérico — nunca um erro.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cliente encosta o celular e o portal se abre (Priority: P1)

A cliente recebeu a luminária no show. Em casa, encosta o iPhone (ou Android) na peça; o celular abre a URL gravada na tag. A página carrega em identidade Manto, mobile-first, com uma animação de "portal se abrindo", um texto de boas-vindas na linha de "A magia da Manto também na sua casa — em breve, um portal se abrirá aqui" e um link para o Instagram da Manto.

**Why this priority**: é a experiência que a cliente vê — sem ela, a tag gravada não leva a lugar nenhum. É o MVP: mesmo sem admin, uma página no ar já permite gravar as primeiras tags.

**Independent Test**: abrir `/nfc/<código válido>` num celular (viewport 320–430px) sem sessão e ver a página completa com animação e link do Instagram; abrir `/nfc/inexistente` e ver a mesma página padrão genérica.

**Acceptance Scenarios**:

1. **Given** um código de tag válido e ativo, **When** a cliente abre a URL no celular sem estar logada, **Then** a página abre com a animação de portal, o texto de boas-vindas e o link do Instagram — sem pedir login.
2. **Given** um código inexistente ou uma tag desativada, **When** alguém abre a URL, **Then** a página mostra o conteúdo padrão genérico da Manto (nunca uma tela de erro técnica) e não revela se o código existe.
3. **Given** uma pessoa com preferência de movimento reduzido no celular, **When** abre a página, **Then** o conteúdo aparece sem a animação de portal (transição discreta), com o mesmo conteúdo.
4. **Given** a página aberta, **When** a resposta do servidor traz espaço de campanha vazio (comportamento de hoje), **Then** a página mostra apenas o conteúdo padrão — o espaço de campanha é o gancho para o futuro e não aparece vazio.

---

### User Story 2 - O código nasce sozinho quando o show é contratado (Priority: P2)

A equipe registra um presente 3D num evento de show (fluxo que já existe). Se o produto escolhido é habilitado para NFC (ex.: luminária v1), o sistema gera automaticamente um código por unidade, já associado ao evento. Ao montar a luminária, a equipe abre o presente no sistema, copia a URL de cada tag e grava na peça física.

**Why this priority**: é o que elimina trabalho manual e garante que toda luminária futura já nasce com código e evento (e portanto cliente) vinculados — a base para as campanhas segmentadas.

**Independent Test**: criar um presente 3D de um item habilitado para NFC com quantidade 2 num evento e verificar que existem 2 tags novas associadas ao evento, com códigos no formato `01-XXXXXX`, e URLs copiáveis.

**Acceptance Scenarios**:

1. **Given** um item do acervo habilitado para NFC com prefixo `01`, **When** a equipe adiciona um presente 3D desse item (quantidade N) a um evento, **Then** o sistema cria N tags com códigos únicos `01-<sufixo>` associadas ao evento.
2. **Given** um item do acervo NÃO habilitado para NFC, **When** um presente 3D desse item é adicionado a um evento, **Then** nenhuma tag é criada.
3. **Given** um presente NFC já criado com quantidade 1, **When** a equipe aumenta a quantidade para 3, **Then** o sistema completa as tags que faltam (total 3); reduzir a quantidade nunca apaga tags já criadas.
4. **Given** tags geradas para um evento, **When** o presente 3D é removido do evento, **Then** as tags continuam existindo com a associação ao evento intacta (a equipe decide no admin se desativa ou reassocia).

---

### User Story 3 - Equipe gerencia as tags no ERP (Priority: P3)

Na área de Impressões 3D do ERP, a equipe abre a lista de tags NFC: código, produto, evento associado, cliente do evento, situação (ativa/inativa) e botão de copiar link. Dali ela gera lotes avulsos (escolhe produto + quantidade, para estoque), associa ou troca o evento de uma tag e ativa/desativa tags. Apagar não existe.

**Why this priority**: dá autonomia operacional (estoque de tags, correções de associação), mas o fluxo principal já funciona com US1+US2.

**Independent Test**: gerar um lote de 5 tags avulsas de um produto, associar uma delas a um evento, desativá-la e confirmar que a página pública dela passou a mostrar o conteúdo genérico.

**Acceptance Scenarios**:

1. **Given** a área de Impressões 3D, **When** a equipe abre a lista de tags, **Then** vê o número sequencial (nº 1, 2, 3… por produto), código, produto, evento, cliente (contratante do evento), situação e ação de copiar a URL completa — o número em destaque, pois é ele que a equipe anota na tag física para alocar depois.
2. **Given** a lista de tags, **When** a equipe gera um lote (produto + quantidade), **Then** as tags nascem sem evento e aparecem na lista prontas para associar depois.
3. **Given** uma tag sem evento (ou com evento errado), **When** a equipe associa/troca o evento, **Then** a mudança vale imediatamente e o cliente exibido acompanha o evento novo.
4. **Given** uma tag ativa, **When** a equipe a desativa, **Then** a página pública passa a mostrar o conteúdo padrão genérico; reativar restaura o comportamento normal. Nenhuma ação de apagar é oferecida.

---

### Edge Cases

- **Colisão de sufixo aleatório**: o sistema gera outro sufixo até obter código único — nunca falha a criação do presente por causa disso.
- **Prefixo do produto alterado depois**: vale só para tags futuras; códigos já gerados são imutáveis.
- **Mesma peça em dois eventos (tag reassociada)**: a página reflete sempre a associação atual; histórico de associações fica fora do escopo v1.
- **Acesso por desktop**: a página funciona e fica apresentável, mas o layout é desenhado para celular (é assim que 99% dos acessos chegam — por NFC).
- **Evento apagado do calendário**: a tag permanece, sem evento associado (associação fica vazia, nunca quebra a página pública).
- **Produto sem foto**: não acontece — foto é obrigatória no acervo; a página pública pode contar com ela.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST manter um cadastro de tags NFC onde cada tag tem código único e imutável no formato `<prefixo>-<6 caracteres aleatórios de alfabeto sem ambiguidade>`, referência ao produto (item do acervo 3D), associação opcional a um evento e situação ativa/inativa. Tags nunca são apagadas.
- **FR-001b**: Cada tag MUST receber um número sequencial humano por linha de produto (nº 1, 2, 3…), imutável, exibido com destaque no ERP — é o rótulo físico que a equipe anota na tagzinha ao gravar em lote, para depois alocar "nº X → cliente Y" sem depender do código aleatório. O número não aparece na URL.
- **FR-002**: Um item do acervo 3D MUST poder ser habilitado para NFC com um prefixo próprio (ex.: `01` para a luminária v1); itens sem prefixo não participam do fluxo NFC.
- **FR-003**: Ao criar um presente 3D de um item habilitado para NFC num evento, o sistema MUST gerar automaticamente uma tag por unidade, associada ao evento. Ao aumentar a quantidade do presente, MUST completar as tags que faltam; ao reduzir, MUST NOT apagar nenhuma.
- **FR-004**: A equipe MUST poder gerar lotes manuais de tags (produto + quantidade) sem evento, para estoque, e associar/trocar o evento de qualquer tag depois.
- **FR-005**: A página pública `/nfc/<código>` MUST abrir sem qualquer autenticação, em qualquer celular (iPhone e Android), e MUST ser mobile-first (320–430px sem rolagem horizontal, alvos de toque ≥ 44px).
- **FR-006**: A página pública MUST apresentar identidade Manto com uma animação de "portal se abrindo" (respeitando preferência de movimento reduzido), texto de boas-vindas (copy provisória na linha de "A magia da Manto também na sua casa — em breve, um portal se abrirá aqui", lapidada na implementação) e link para o Instagram da Manto.
- **FR-007**: Código inexistente ou tag desativada MUST resultar na mesma página padrão genérica da Manto — nunca uma tela de erro técnica e nunca uma confirmação de que o código não existe.
- **FR-008**: A resposta pública de resolução do código MUST incluir um espaço reservado para conteúdo de campanha, hoje sempre vazio — o contrato que permitirá campanhas futuras (descontos, fotos/vídeos do evento) sem regravar nenhuma tag.
- **FR-009**: A página pública v1 MUST NOT exibir nenhum dado pessoal da cliente ou do evento (nome, data, fotos) — o vínculo existe só no sistema interno até que campanhas futuras definam o que expor.
- **FR-010**: No ERP, a lista de tags MUST mostrar código, produto, evento associado, cliente do evento (contratante), situação e ação de copiar a URL pública completa em um clique.
- **FR-011**: A equipe MUST poder ativar/desativar tags individualmente; nenhuma superfície oferece exclusão.
- **FR-012**: O sistema MUST registrar o último acesso e o total de acessos de cada tag (sem tela dedicada na v1 — insumo barato para o futuro).

### Key Entities

- **Tag NFC**: unidade física gravável — código único imutável, número sequencial humano por produto (rótulo de logística), produto (item do acervo 3D), evento associado (opcional, alterável), situação ativa/inativa, contadores de acesso.
- **Item do Acervo 3D** *(existente, estendido)*: ganha a habilitação NFC com prefixo de código; continua sendo o "catálogo de produtos" impressos.
- **Evento / Cliente** *(existentes)*: o evento do show é a âncora da tag; o cliente (contratante) vem do vínculo evento↔cliente que já existe.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma cliente que encosta o celular na luminária vê a página da Manto carregada em menos de 3 segundos numa conexão móvel comum, sem precisar de login ou digitação.
- **SC-002**: 100% dos presentes 3D de produtos habilitados para NFC criados a partir do lançamento nascem com seus códigos gerados automaticamente, sem nenhuma ação manual extra da equipe.
- **SC-003**: A equipe copia a URL de qualquer tag em no máximo 2 cliques a partir da lista no ERP.
- **SC-004**: Nenhuma URL já gravada em tag física precisa mudar quando o conteúdo da página mudar (campanhas futuras) — estabilidade de contrato verificável: o mesmo código continua resolvendo após qualquer evolução de conteúdo.
- **SC-005**: A página pública passa na verificação mobile: sem rolagem horizontal de 320px a 430px, alvos de toque ≥ 44px, e com preferência de movimento reduzido o conteúdo aparece sem animação.
- **SC-006**: Um código digitado "no chute" (sufixo errado) não revela nada: a resposta é indistinguível de uma tag desativada.

## Assumptions

- A luminária v1 já existe (ou será criada) como item do Acervo 3D com foto — receberá o prefixo `01` pela própria equipe no ERP.
- O handle oficial do Instagram da Manto será confirmado com o usuário durante a implementação e mantido em um único ponto de configuração.
- As tags físicas têm capacidade suficiente para a URL completa (~44 caracteres — qualquer NTAG213 comporta) e a equipe grava e trava (lock) as tags manualmente, fora do sistema.
- A gravação física e o processo de travar a tag contra regravação são procedimento operacional da equipe, não do software.
- Fora de escopo v1: sistema de campanhas/conteúdo dinâmico (fica só o gancho), exibição de fotos/vídeos do evento, saudação com nome da cliente, telas de métricas de acesso, host/domínio dedicado.
