# Feature Specification: Talento adicionado não consegue avaliar o evento

**Feature Branch**: `085-fix-avaliacao-nao-aparece`

**Created**: 2026-06-24

**Status**: Draft

**Input**: "A Erika Lopes Soares foi adicionada ao evento 'maple zayu clutch + mulher casal amarelo…',
porém no portal não aparece para ela avaliar o evento. Analise o que está incorreto e conserte."

## Contexto / Diagnóstico

O evento em questão é **#198 — "(R&I) MAPLE + ZAYU + CLUTCH + MULHER CASAL AMARELO JUNINO + …"**, que
**terminou em 14/06/2026**. A Erika foi adicionada ao elenco **depois**. No portal do talento, o evento
**não aparece para avaliar**. Investigando a regra que decide quais eventos um talento pode avaliar,
encontramos **dois bloqueios**:

1. **Exige convite "aceito"**: a elegibilidade para avaliar só considera funções com
   `convite = aceito`. Quem é **adicionado ao elenco mas não passou pelo fluxo de aceitar o convite**
   (caso típico de quem é incluído depois do evento, para corrigir/registrar o elenco real) fica de
   fora — mesmo tendo participado.
2. **Janela de 7 dias contada só pelo fim do evento**: a avaliação fica disponível por 7 dias após o
   **término do evento**. Quem é **adicionado tardiamente** (depois desses 7 dias) **nunca** ganha
   janela — como o evento da Erika terminou há mais de 7 dias, a avaliação já estava fechada quando ela
   foi incluída.

Ou seja: um talento legitimamente escalado, mas incluído tarde e/ou sem ter clicado em "aceitar", não
consegue avaliar. Esta correção remove esses dois bloqueios sem abrir a avaliação para quem **recusou**
o convite.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Talento incluído no elenco consegue avaliar (Priority: P1) 🎯 MVP

Como talento que foi escalado para um evento (inclusive se fui adicionado depois do evento ou ainda não
"aceitei" formalmente), quero ver o evento no portal para **avaliá-lo**.

**Acceptance Scenarios**:

1. **Given** que fui **adicionada ao elenco** de um evento já terminado e **ainda não avaliei**, **When**
   abro o portal, **Then** o evento aparece na seção "para avaliar" e consigo abrir a avaliação.
2. **Given** que fui adicionada **dias depois** do término do evento, **When** abro o portal nos 7 dias
   seguintes à minha inclusão, **Then** o evento aparece para avaliar (a janela conta a partir da minha
   inclusão, não só do fim do evento).
3. **Given** que tenho um convite **pendente** (não recusado) para um evento que já terminou, **When**
   abro a avaliação, **Then** consigo avaliar normalmente.
4. **Given** que **recusei** o convite, **When** abro o portal, **Then** o evento **não** aparece para
   avaliar.

### Edge Cases

- Evento ainda **não terminado**: continua **não** disponível para avaliação (a avaliação só abre após o
  término).
- Talento que **já avaliou**: continua fora da lista "para avaliar" (sem duplicar), mas mantém a janela
  de **edição** existente.
- Inclusão muito antiga (fora da janela) sem avaliação: permanece indisponível, como hoje, evitando
  reabrir avaliações de eventos muito antigos.

## Requirements *(mandatory)*

- **FR-001**: A elegibilidade para avaliar um evento MUST considerar qualquer talento **escalado** para
  o evento cujo convite **não tenha sido recusado** (aceito, pendente ou sem status), e **não apenas**
  os com convite "aceito".
- **FR-002**: A elegibilidade MUST **excluir** funções com convite **recusado**.
- **FR-003**: A janela de disponibilidade da avaliação (7 dias) MUST ser contada a partir do **mais
  recente** entre o **término do evento** e o **momento em que o talento foi adicionado/escalado**.
- **FR-004**: A avaliação MUST continuar disponível **somente após o término** do evento.
- **FR-005**: As mesmas regras de elegibilidade MUST valer na **listagem do portal** e nas **telas de
  avaliar/enviar avaliação** (acesso direto à página), para não haver botão que leva a erro.
- **FR-006**: A janela de **edição** de uma avaliação já enviada MUST seguir a mesma flexibilização de
  status de convite (não exigir "aceito").

## Success Criteria *(mandatory)*

- **SC-001**: Um talento adicionado ao elenco de um evento terminado, sem avaliação e dentro da janela,
  vê e consegue concluir a avaliação em 100% dos casos.
- **SC-002**: Um talento adicionado **após** a janela de 7 dias do fim do evento ganha 7 dias a partir
  da sua inclusão para avaliar.
- **SC-003**: Quem **recusou** o convite nunca vê o evento para avaliar.
- **SC-004**: Eventos ainda não terminados nunca aparecem para avaliação.

## Assumptions

- "Escalado e não recusado" é o sinal de participação suficiente para avaliar — cobre quem foi
  adicionado diretamente/tardiamente e ainda não clicou em "aceitar". Convite **recusado** continua
  bloqueando.
- A inclusão/escalação do talento é registrada com um carimbo de data (momento da atribuição); quando
  esse carimbo não existir, a janela usa apenas o término do evento (comportamento atual).
- Janela mantida em 7 dias (avaliar) e 30 dias (editar), agora contadas pelo evento **ou** pela
  inclusão, o que for mais recente.
- Correção de regra de visibilidade/elegibilidade; sem alteração de modelo de dados nem migration.
