# Feature Specification: Busca na Planilha de Pagamentos

**Feature Branch**: `045-busca-pagamentos`

**Created**: 2026-06-12

**Status**: Draft

**Input**: User description: "Preciso que na página de pagamentos tenha uma busca sofisticada para
achar eventos, por qualquer que seja o dado. Faça isso conversar com o restante das funções na
página."

## Contexto

A Planilha de Pagamentos lista dezenas/centenas de itens por mês (cachês, salários, gastos,
comissões). Hoje só dá para filtrar por mês e por situação (cards). Achar um item específico —
pelo nome do evento, da pessoa, função, PIX, valor ou data — exige rolar a tela inteira.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Buscar por qualquer dado (Priority: P1)

O financeiro digita qualquer termo na busca — nome do evento, nome da pessoa, personagem/função,
chave PIX, valor ou data — e a tabela mostra na hora só as linhas que batem.

**Acceptance Scenarios**:

1. **Given** a planilha do mês, **When** digita "urso da masha", **Then** só as linhas desse
   evento aparecem (busca sem diferenciar maiúsculas/acentos).
2. **When** digita o nome de uma pessoa, **Then** aparecem os pagamentos dela (cachês, salário,
   gastos, comissão).
3. **When** digita "137,50" (ou parte do valor) ou "10/06", **Then** as linhas com aquele valor ou
   data aparecem.
4. **When** limpa a busca, **Then** a tabela volta ao estado anterior.

---

### User Story 2 - Busca conversa com o resto da página (Priority: P1)

A busca combina com o filtro de situação (cards) e com a seleção em massa: tudo opera sobre o que
está visível.

**Acceptance Scenarios**:

1. **Given** filtro "No banco" ativo + busca "masha", **Then** só linhas no banco E do evento
   aparecem (os dois filtros juntos).
2. **Given** uma busca ativa, **When** clica em selecionar tudo, **Then** só as linhas visíveis da
   busca são marcadas; ações em massa atingem só elas.
3. **Given** linhas selecionadas, **When** a busca esconde algumas, **Then** as escondidas são
   desmarcadas.
4. **Given** uma busca ativa, **Then** um resumo mostra quantos itens e o valor somado do que está
   na tela.

---

### Edge Cases

- Busca sem resultados: mensagem amigável ("Nenhum item encontrado") com como limpar.
- Acentos e caixa ignorados ("FIGURINÓ" acha "figurino").
- Valor digitado com ou sem pontos de milhar ("1.950" e "1950" acham R$ 1.950,00).
- A troca de situação individual de uma linha mantém busca e filtro ativos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A planilha MUST ter campo de busca que filtra as linhas em tempo real por qualquer
  conteúdo visível da linha (data, descrição, tipo, função, nome, valor, PIX, situação).
- **FR-002**: A busca MUST ignorar maiúsculas/minúsculas e acentos; valores MUST ser encontrados
  com ou sem separador de milhar.
- **FR-003**: Busca e filtro de situação MUST combinar (E lógico); selecionar tudo e ações em
  massa MUST operar apenas sobre linhas visíveis.
- **FR-004**: Com busca ativa, a página MUST mostrar contagem e soma dos itens visíveis.
- **FR-005**: Sem resultados, MUST aparecer estado vazio claro com opção de limpar a busca.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Encontrar um pagamento específico leva segundos (digitar 1 termo), sem rolagem.
- **SC-002**: 100% das ações em massa com busca ativa atingem apenas linhas visíveis.
- **SC-003**: Busca por nome/evento/valor/data/PIX retorna as mesmas linhas que uma inspeção
  manual da tabela retornaria.

## Assumptions

- A busca opera dentro do mês selecionado (o filtro de mês continua sendo o recorte de dados).
- A busca não fica salva ao recarregar (diferente do filtro de situação, que já persiste).
- Os cards de situação continuam mostrando os totais do mês inteiro; o resumo da busca é exibido
  junto ao campo de busca.
