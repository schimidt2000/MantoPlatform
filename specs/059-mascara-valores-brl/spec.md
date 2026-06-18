# Feature Specification: Máscara padrão para todos os campos de valor em reais

**Feature Branch**: `059-mascara-valores-brl`

**Created**: 2026-06-18

**Status**: Draft

**Input**: User description: "Me incomoda a falta de padronização para o usuário nos campos onde colocamos valor. Queria que TODOS os campos com valores em reais do site funcionassem da mesma forma. Ao ir escrevendo, começa da direita para a esquerda e já coloca automaticamente o `.` no separador de milhar e `,` no separador de decimal."

## Contexto

Hoje **a maioria** dos campos de valor em reais (R$) já usa uma máscara "estilo
calculadora" (os dígitos preenchem da direita para a esquerda; o ponto separa o milhar e a
vírgula os centavos — ex.: digitar `4 0 0 0 0 0` resulta em `4.000,00`). Porém **alguns
campos de valor em R$ ainda não seguem esse padrão** — em telas como Orçamento e Educamanto
eles usam o campo numérico nativo do navegador, que se comporta de forma diferente (sem
separador de milhar, ponto como decimal, setinhas etc.). Essa inconsistência confunde o
usuário.

O objetivo é que **100% dos campos onde o usuário digita um valor em reais** se comportem
exatamente da mesma forma — a tal máscara calculadora.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Digitar valores em R$ sempre da mesma forma (Priority: P1) 🎯 MVP

Como usuário que preenche valores em qualquer tela do sistema, quero que **todo** campo de
valor em reais funcione igual — eu só digito os números e o sistema posiciona sozinho o
separador de milhar (`.`) e o de centavos (`,`), preenchendo da direita para a esquerda — para
não precisar pensar em formatação nem aprender comportamentos diferentes em cada tela.

**Why this priority**: É exatamente o pedido central — padronização da experiência de digitação
de dinheiro em todo o site.

**Independent Test**: Abrir qualquer formulário com valor em R$ (ex.: cadastro de evento,
pagamento, salário, gasto, orçamento, pacote educamanto), digitar uma sequência de dígitos e
confirmar que aparece formatado como `1.234,56`, preenchendo da direita para a esquerda.

**Acceptance Scenarios**:

1. **Given** um campo de valor em R$ vazio, **When** o usuário digita `150000`, **Then** o
   campo mostra `1.500,00`.
2. **Given** o mesmo campo, **When** o usuário continua digitando mais um dígito (`5`), **Then**
   o campo passa a mostrar `15.000,05` (os dígitos "empurram" da direita para a esquerda).
3. **Given** dois campos de valor em R$ em telas diferentes, **When** o usuário digita o mesmo
   número nos dois, **Then** ambos exibem exatamente o mesmo resultado.
4. **Given** um campo de valor com conteúdo, **When** o usuário apaga tudo, **Then** o campo
   fica vazio (sem `0,00` forçado) e isso significa "sem valor".

---

### User Story 2 - Campos hoje fora do padrão passam a usar a máscara (Priority: P1)

Como usuário, quero que os campos de valor em R$ que hoje têm comportamento diferente (ex.:
valores personalizados do Orçamento, custos/valores de pacotes do Educamanto, preços de
configuração de orçamento, filtros de valor) passem a usar a mesma máscara, **sem que nenhum
valor já salvo seja perdido ou alterado**.

**Why this priority**: Sem converter esses campos, a padronização fica incompleta — é parte
inseparável do pedido "TODOS os campos".

**Independent Test**: Abrir uma tela que hoje usa campo numérico nativo para R$ (ex.: edição de
pacote Educamanto ou valores personalizados do Orçamento), confirmar que agora o campo usa a
máscara padrão, salvar e reabrir, e confirmar que o valor foi gravado corretamente.

**Acceptance Scenarios**:

1. **Given** uma tela que antes usava campo numérico nativo para um valor em R$, **When** ela é
   aberta, **Then** o campo usa a máscara calculadora padrão.
2. **Given** um valor digitado com a máscara (ex.: `2.500,00`), **When** o formulário é enviado,
   **Then** o sistema grava o valor correto (R$ 2.500,00) sem erro.
3. **Given** um registro já existente com valor salvo, **When** a tela de edição é aberta,
   **Then** o valor aparece já formatado no padrão (ex.: `350,00`) e, se salvo sem alteração,
   permanece idêntico.

---

### User Story 3 - Campos numéricos que não são R$ permanecem como estão (Priority: P2)

Como usuário, quero que campos numéricos que **não** representam dinheiro — percentuais (taxa,
comissão %, desconto %), multiplicadores/markup, contagens (nº de parcelas, quantidades),
dimensões (altura em cm) e tempos (minutos) — continuem funcionando como hoje, para não serem
transformados em "reais" por engano.

**Why this priority**: Evita regressão e confusão; delimita o escopo de "valores em reais".

**Independent Test**: Conferir que campos como "comissão (%)", "nº de parcelas", "altura (cm)"
e "margem/markup" continuam aceitando o formato atual e **não** ganham máscara de R$.

**Acceptance Scenarios**:

1. **Given** um campo de percentual (ex.: comissão 2,5%), **When** a tela é aberta, **Then** ele
   **não** usa a máscara de reais.
2. **Given** um campo de contagem (ex.: nº de parcelas), **When** a tela é aberta, **Then** ele
   continua como campo numérico simples.

---

### Edge Cases

- **Valor vindo do servidor**: ao abrir uma tela de edição, o valor já gravado deve aparecer
  formatado no padrão (ex.: `1.500,00`), não como `1500.0`.
- **Campos adicionados dinamicamente** (ex.: nova linha de cachê de personagem, nova parcela,
  novo item de pacote): devem receber a máscara assim que surgem na tela.
- **Colar (paste)** um valor (ex.: `1.234,56` ou `1234.56`): o campo deve normalizar para o
  padrão.
- **Campo vazio**: continua significando "sem valor" (não forçar `0,00`).
- **Valores grandes** (ex.: centenas de milhares): separador de milhar aplicado corretamente.
- **Campos que hoje guardam reais inteiros** (sem centavos): passam a exibir centavos (`,00`)
  como todos os outros, sem alterar o valor efetivo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Todo campo em que o usuário **digita um valor em reais (R$)** MUST usar a máscara
  padrão "calculadora": preenchimento da direita para a esquerda, `.` como separador de milhar,
  `,` como separador de centavos, sempre com 2 casas decimais.
- **FR-002**: O comportamento MUST ser **idêntico** em todos os campos de R$ do site (uma única
  fonte de comportamento, sem variações por tela).
- **FR-003**: Campos de valor em R$ **inseridos dinamicamente** na página MUST receber a mesma
  máscara automaticamente.
- **FR-004**: Ao abrir uma tela com valor já existente, o campo MUST exibir esse valor já no
  formato padrão.
- **FR-005**: Ao enviar o formulário, o sistema MUST interpretar corretamente o valor mascarado
  e gravar o número correto, sem erro e sem perda de precisão.
- **FR-006**: Campos numéricos que **não** representam reais (percentuais/taxas, comissão em %,
  desconto em %, multiplicadores/markup, contagens, quantidades, dimensões, minutos) MUST
  permanecer no formato atual (não ganham a máscara de R$).
- **FR-007**: Um campo de R$ vazio MUST continuar significando "sem valor" (não deve forçar
  `0,00`).
- **FR-008**: A mudança MUST preservar todos os valores já gravados — abrir e salvar um registro
  sem alterá-lo não pode mudar seu valor.

### Áreas afetadas (campos de R$ a padronizar)

> Lista das telas/áreas onde o usuário digita valores em reais. As que já usam o padrão devem
> ser mantidas; as que ainda não usam devem ser convertidas.

- **Eventos**: cachê, adicional de viagem, valor de venda (bruto/líquido), valores de pagamento
  e parcelas (valor), comissão em R$ quando aplicável.
- **Financeiro / Pagamentos**: valores de pagamento e comissões (campos de R$).
- **Salários (Admin)**: salário do usuário.
- **Gastos**: valor do gasto.
- **Orçamento**: acréscimo em valor fixo, valores personalizados (1h/2h/4h), preços de
  configuração (ator/cantor), filtros de valor (mín./máx.) — os que representam R$.
- **Educamanto**: valores/custos de pacote e de itens em R$ (ex.: ensemble, custos por item).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos campos onde o usuário digita um valor em R$ usam a mesma máscara
  padrão.
- **SC-002**: Em qualquer campo de R$, o usuário consegue inserir o valor **sem digitar
  manualmente** o ponto de milhar ou a vírgula de centavos.
- **SC-003**: 0 regressões de gravação — os valores salvos correspondem exatamente ao que foi
  digitado/exibido, e registros existentes permanecem idênticos ao serem reabertos e salvos.
- **SC-004**: Nenhum campo **não monetário** (percentual, contagem, dimensão, markup, minutos)
  foi convertido por engano.

## Assumptions

- **Definição de "valor em reais"**: campos que representam dinheiro em R$ (cachê, venda,
  pagamentos, salário, gastos, comissão em R$, preços e custos de orçamento/educamanto).
  **Excluídos**: percentuais e taxas (inclui comissão e desconto em %), multiplicadores/markup,
  contagens (parcelas, quantidades), dimensões (altura) e tempos (minutos).
- A máscara "calculadora" **já existente no sistema** é o padrão desejado e será **reutilizada**
  (não recriada) — esta feature a aplica de forma consistente a todos os campos de R$.
- Campos de R$ que hoje aceitam apenas reais inteiros passam a aceitar centavos (2 casas), como
  os demais; isso não altera valores já gravados.
- "Todos" = todos os formulários autenticados do sistema; o portal do talento entra apenas se
  tiver campos onde o usuário digita valores em R$.
- O envio de formulário não exige "desmascarar" no cliente: o servidor interpreta a string
  formatada (padrão brasileiro) ao receber.
