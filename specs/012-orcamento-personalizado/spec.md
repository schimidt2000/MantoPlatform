# Feature Specification: Orçamento personalizado (valor final ou multiplicador)

**Feature Branch**: `012-orcamento-personalizado`

**Created**: 2026-06-01

**Status**: Draft

**Input**: User description: "Criar orçamento personalizado. Seguir os moldes dos orçamentos
atuais, mas com valores customizados. A pessoa escolhe se quer definir o valor final, ou se quer
mudar o multiplicador."

## Contexto

Hoje o orçamento é calculado automaticamente: somam-se os cachês dos artistas/coordenadores,
aplica-se um **multiplicador** (markup) por duração, e somam-se extras (brinde, noturno, técnico,
maquiador, transporte, Nota Fiscal). O vendedor não consegue ajustar o preço final — ele sai
fechado pela calculadora.

Há casos em que o vendedor precisa **fechar um valor combinado** com o cliente (negociação,
condição especial, valor cheio que ele já acordou) ou **aplicar um multiplicador diferente** do
padrão. Para isso, ele quer poder gerar um orçamento no **mesmo formato de sempre** (mesma
mensagem de WhatsApp, mesmo PDF, mesmo histórico), porém com os valores que ele definir.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Definir o valor final do orçamento (Priority: P1)

O vendedor monta a equipe normalmente, ativa o modo personalizado, escolhe "definir valor final"
e digita o valor total de cada duração (1h, 2h, 4h). O orçamento gerado usa exatamente esses
valores como VALOR TOTAL — nada é somado por cima.

**Why this priority**: É o pedido central — fechar o preço que o vendedor já combinou com o
cliente, no formato padrão da Manto.

**Independent Test**: Montar uma equipe qualquer, ativar personalizado → "valor final", digitar
R$ 2.400 para 4h e gerar. Conferir que a mensagem/PDF mostram exatamente R$ 2.400 como total de
4h (e o PIX à vista calculado em cima desse valor).

**Acceptance Scenarios**:

1. **Given** o modo personalizado ativo em "valor final", **When** o vendedor digita um valor por
   duração e gera, **Then** cada duração mostra exatamente o valor digitado como VALOR TOTAL.
2. **Given** valores digitados, **When** o orçamento é gerado, **Then** transporte, Nota Fiscal e
   demais acréscimos NÃO são somados por cima (o valor digitado é o total final).
3. **Given** uma duração deixada em branco/sem valor, **When** o vendedor gera, **Then** o sistema
   avisa que o valor é obrigatório naquele modo (não gera total R$ 0 silenciosamente).

---

### User Story 2 - Mudar o multiplicador (Priority: P1)

O vendedor monta a equipe normalmente, ativa o modo personalizado, escolhe "mudar multiplicador"
e informa um multiplicador por duração. O sistema aplica esse multiplicador sobre o cachê-base da
equipe (em vez do markup padrão) e usa o resultado como valor final.

**Why this priority**: É a segunda forma de personalização pedida; útil quando o vendedor quer
ajustar a margem sem digitar valor a valor.

**Independent Test**: Montar uma equipe, anotar o cachê-base mostrado, ativar personalizado →
"multiplicador", trocar o multiplicador de 4h e gerar. Conferir que o total de 4h = cachê-base ×
multiplicador informado.

**Acceptance Scenarios**:

1. **Given** o modo personalizado em "multiplicador", **When** o vendedor abre o painel, **Then**
   os campos vêm pré-preenchidos com o multiplicador padrão do modelo atual (show/receptivo).
2. **Given** um multiplicador alterado para uma duração, **When** o orçamento é gerado, **Then** o
   total daquela duração = cachê-base da equipe × multiplicador informado, sem extras por cima.
3. **Given** o multiplicador personalizado, **When** o orçamento é gerado, **Then** o vendedor
   consegue ver, no resultado, o cachê-base e o multiplicador aplicado (transparência).

---

### User Story 3 - Orçamento personalizado no formato de sempre (Priority: P2)

O orçamento personalizado reaproveita tudo o que já existe: seleção de quais durações entram
(feature 003), mensagem de WhatsApp, PDF, envio por email e histórico. Só os valores mudam.

**Why this priority**: Garante consistência e evita retrabalho; é a expectativa do "seguir os
moldes".

**Independent Test**: Gerar um orçamento personalizado e confirmar que copiar mensagem, baixar
PDF, enviar email e ver no histórico funcionam igual a um orçamento normal.

**Acceptance Scenarios**:

1. **Given** um orçamento personalizado gerado, **When** o vendedor copia a mensagem ou baixa o
   PDF, **Then** o formato é o mesmo de um orçamento normal, com os valores personalizados.
2. **Given** a seleção de durações (1h/2h/4h), **When** o vendedor desmarca uma duração, **Then**
   ela não aparece no orçamento personalizado, igual ao fluxo normal.
3. **Given** um orçamento personalizado, **When** ele é salvo no histórico, **Then** pode ser
   reaberto mostrando que era personalizado e com quais valores/multiplicadores.

---

### Edge Cases

- **Modo personalizado desligado**: o orçamento se comporta exatamente como hoje (cálculo
  automático com markup + extras). O modo é opt-in.
- **Valor/multiplicador inválido** (texto, negativo, vazio): o sistema avisa e não gera um
  orçamento com valor zerado ou absurdo.
- **PIX à vista**: o desconto de 5% incide sobre o valor personalizado de cada duração.
- **Equipe vazia no modo "valor final"**: ainda é possível gerar (o vendedor define os valores na
  mão); no modo "multiplicador" sem cachê-base, o total seria 0 — avisar.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O vendedor MUST poder ativar um modo "orçamento personalizado" a partir do mesmo
  formulário de orçamento, sem precisar de uma página separada.
- **FR-002**: No modo personalizado, o vendedor MUST escolher entre dois critérios:
  (a) **definir o valor final** por duração, ou (b) **mudar o multiplicador** por duração.
- **FR-003**: O ajuste (valor ou multiplicador) MUST ser por duração — 1h, 2h e 4h independentes.
- **FR-004**: No critério "valor final", o valor digitado por duração MUST ser usado como VALOR
  TOTAL final, sem somar transporte, Nota Fiscal ou outros acréscimos por cima.
- **FR-005**: No critério "multiplicador", o total de cada duração MUST ser o cachê-base da equipe
  multiplicado pelo multiplicador informado, sem extras por cima.
- **FR-006**: No critério "multiplicador", os campos MUST vir pré-preenchidos com o multiplicador
  padrão do modelo vigente (show ou receptivo), servindo de ponto de partida.
- **FR-007**: O orçamento personalizado MUST reaproveitar o formato existente: mensagem de
  WhatsApp, PDF, envio por email, seleção de durações (feature 003) e histórico.
- **FR-008**: O desconto PIX à vista (5%) MUST incidir sobre os valores personalizados.
- **FR-009**: O sistema MUST validar as entradas: valores/multiplicadores ausentes, não numéricos
  ou ≤ 0 não geram orçamento — o vendedor recebe um aviso claro.
- **FR-010**: Com o modo personalizado desligado, o orçamento MUST funcionar exatamente como hoje.
- **FR-011**: O histórico MUST registrar que o orçamento foi personalizado e guardar o critério e
  os valores/multiplicadores usados, permitindo reabrir.
- **FR-012**: No critério "multiplicador", o resultado MUST mostrar o cachê-base e o multiplicador
  aplicado, para o vendedor conferir o cálculo.
- **FR-013**: O acesso ao orçamento personalizado MUST seguir a mesma permissão do orçamento atual
  (COMERCIAL e SUPERADMIN).

### Key Entities *(include if feature involves data)*

- **Orçamento (cálculo)** — já existe: ganha a noção opcional de "personalizado", com critério
  (valor final | multiplicador) e os valores/multiplicadores por duração.
- **Histórico de orçamento** — já existe: passa a registrar também os dados de personalização no
  snapshot que já guarda.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O vendedor consegue gerar um orçamento com valor final definido por ele em até 3
  cliques a partir do formulário (ativar → escolher critério → digitar → gerar).
- **SC-002**: 100% dos orçamentos no critério "valor final" mostram exatamente o valor digitado
  como total (diferença de R$ 0,00 em relação ao informado).
- **SC-003**: No critério "multiplicador", o total exibido corresponde a cachê-base ×
  multiplicador para cada duração (verificável na própria tela de resultado).
- **SC-004**: Com o modo desligado, 100% dos orçamentos produzem o mesmo resultado de antes
  (nenhuma regressão no cálculo automático).
- **SC-005**: Mensagem, PDF, email e histórico funcionam para o orçamento personalizado sem
  passos extras em relação ao normal.

## Assumptions

- "Seguir os moldes" = reaproveitar o formulário e o formato de saída atuais; a personalização é
  um painel opt-in dentro do fluxo existente, não uma tela nova.
- "Definir o valor final" significa o **total ponta a ponta** por duração: o que o vendedor digita
  é o que o cliente paga; o sistema não soma transporte/NF/extras depois (decisão do usuário).
- "Mudar o multiplicador" age sobre o **cachê-base** (soma dos cachês de artistas e coordenadores,
  como hoje antes do markup), produzindo diretamente o total — sem extras posteriores.
- O ajuste é **por duração**; um multiplicador/valor por 1h, 2h e 4h.
- A "duração personalizada" (horas fora de 1/2/4) fica **fora de escopo** no modo personalizado
  nesta entrega — o vendedor define os totais das durações padrão.
- A permissão é a mesma do orçamento atual (COMERCIAL, SUPERADMIN).
