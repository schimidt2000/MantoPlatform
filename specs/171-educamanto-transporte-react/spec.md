# Feature Specification: Transporte explícito por dias no EducaManto + calculadora em React

**Feature Branch**: `171-educamanto-transporte-react`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "na página do educamanto ainda na arquitetura antiga preciso que mostre
mais explicitamente o valor de transporte quando calculado via calculadora para fora de São Paulo e
a depender da quantidade de dias, já faça essa multiplicação para o valor total. Importante que
depois também faça a versão disso para a nova arquitetura em react."

## Contexto

A calculadora do EducaManto (`/educamanto`, orçamentos por pacote musical) já calcula transporte por
endereço (feature 076): digita-se o endereço → calcula distância (Google Maps) → tarifa de van com
carretinha por km (ida e volta) + adicional por pessoa → soma ao valor final. Hoje esse valor é
calculado **uma única vez** (uma ida e volta), **independente de quantos dias** o pacote tem — mesmo
quando o pacote cobre vários dias de apresentação fora de São Paulo, o que na prática exige uma
viagem de ida e volta por dia. A linha de resultado do transporte também é discreta (uma frase única
misturando km, tipo de veículo e adicional por pessoa).

O EducaManto nunca foi migrado para a arquitetura React da migração 144 (não está entre as 6 User
Stories daquela spec) — hoje é 100% Jinja2. Esta feature corrige o cálculo/exibição na tela antiga e,
adicionalmente, cria a tela equivalente da calculadora em React (decisão confirmada com o usuário):
pacotes, dias, ensemble e transporte (já com a multiplicação por dias) com os mesmos totais sem/com
nota. Geração de PDF, histórico de orçamentos e CRUD de pacotes (criar/editar/duplicar/excluir)
permanecem exclusivamente na tela Jinja por enquanto — não fazem parte desta fatia.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Transporte multiplicado pelos dias do pacote, no Jinja (Priority: P1) 🎯 MVP

Como usuário do EducaManto (Comercial/Superadmin/Ensaio/Revendedor), ao calcular o transporte de um
pacote com mais de um dia de apresentação fora de São Paulo, quero que o valor de transporte já
reflita **uma ida e volta por dia** (não apenas uma), somado corretamente ao valor final, com uma
linha de resultado que deixa claro o valor por viagem, o número de dias e o total.

**Why this priority**: É o problema relatado — hoje o valor de transporte fica subestimado em
pacotes de múltiplos dias, o que pode gerar orçamento abaixo do custo real de logística.

**Independent Test**: No EducaManto, escolher um pacote e preencher 3 dias (ex.: 2 dias de 1 sessão
+ 1 dia de 2 sessões), calcular a distância de um endereço fora de São Paulo (transporte é sempre
van com carretinha e pessoas = catering da apresentação, comportamento já fixo desde a feature 080)
→ a linha de transporte mostra o valor de uma viagem, "× 3 dias" e o total (valor da viagem × 3);
esse total (não o valor de uma viagem só) é o que soma ao valor final sem/com nota.

**Acceptance Scenarios**:

1. **Given** um pacote com 1 dia total (d1=1 ou d2=1) e distância calculada, **When** vejo o
   resultado, **Then** o transporte é o valor de **uma** viagem (comportamento atual, sem regressão)
   e a linha de resultado mostra claramente que é 1 dia.
2. **Given** um pacote com mais de 1 dia total (ex.: d1+d2 = 3), **When** vejo o resultado, **Then**
   o transporte exibido e somado ao valor final é o valor de **uma viagem × número total de dias**.
3. **Given** o transporte já calculado com múltiplos dias, **When** altero o número de dias (d1/d2),
   **Then** o valor de transporte é recalculado automaticamente com o novo número de dias, sem
   precisar buscar a distância de novo.
4. **Given** nenhum endereço calculado (km = 0), **When** vejo o resultado, **Then** o transporte
   continua zero, independentemente do número de dias (sem regressão).
5. **Given** o transporte calculado com múltiplos dias, **When** clico em "Gerar orçamento" (PDF),
   **Then** o valor salvo/exibido no PDF é o mesmo total já multiplicado pelos dias (o PDF nunca
   mostra um valor de transporte diferente do que apareceu na tela).

---

### User Story 2 - Mesma calculadora do EducaManto em React (Priority: P2)

Como usuário do EducaManto, quero acessar uma tela em React com a mesma calculadora (seleção de
pacote, dias, ensemble, transporte já multiplicado por dias, valor final sem/com nota e detalhamento
de itens) para que o fluxo do dia a dia também funcione na nova arquitetura, consistente com o resto
do sistema já migrado.

**Why this priority**: Depende da fórmula corrigida da User Story 1 (a versão React deve nascer já
com a multiplicação por dias); é a "versão nova" pedida explicitamente pelo usuário.

**Independent Test**: Acessar a tela React do EducaManto, selecionar um pacote, preencher dias e
ensemble, calcular a distância de um endereço → os valores sem/com nota e a linha de transporte
(com a multiplicação por dias) batem exatamente com os mesmos parâmetros calculados na tela Jinja.

**Acceptance Scenarios**:

1. **Given** a tela React do EducaManto carregada, **When** seleciono um pacote, **Then** vejo os
   mesmos itens/quantidades e posso preencher dias (1 e/ou 2 sessões) e ensemble.
2. **Given** dias e ensemble preenchidos, **When** informo um endereço e calculo a distância,
   **Then** o sistema mostra a distância e calcula o transporte (sempre van com carretinha, nº de
   pessoas derivado automaticamente do catering de apresentação — mesma regra fixa da tela Jinja
   desde a feature 080, sem seleção de tipo de veículo).
3. **Given** todos os parâmetros preenchidos, **When** vejo o resultado, **Then** o valor final
   sem/com nota, o desconto aplicado (se houver) e a linha de transporte (valor por viagem × dias =
   total) aparecem exatamente como calcularia a tela Jinja para os mesmos parâmetros.
4. **Given** a tela React, **When** troco de pacote sem recarregar a página, **Then** dias, ensemble
   e transporte já preenchidos são preservados e o cálculo é refeito para o novo pacote (paridade com
   o comportamento atual da tela Jinja — feature 081).
5. **Given** a tela React, **When** preciso gerar o PDF do orçamento, ver o histórico ou gerenciar
   pacotes (criar/editar/duplicar/excluir), **Then** essas ações continuam disponíveis apenas na tela
   Jinja (a tela React não as replica nesta fatia); um link visível leva à tela Jinja para essas
   ações.

### Edge Cases

- **Google Maps não configurado / endereço inválido**: mensagem amigável nas duas telas; transporte
  fica zero (sem regressão).
- **Trocar dias/ensemble** depois de calcular a distância: recalcula o transporte (incluindo a
  multiplicação por dias, e o nº de pessoas se o ensemble mudar o catering de apresentação) sem
  precisar buscar a distância de novo, nas duas telas.
- **1 dia total**: multiplicador é 1 — resultado idêntico ao comportamento anterior à feature 076/171
  (sem regressão visual ou de valor).
- **Papel ENSAIO/Revendedor** (só usam a calculadora, sem aba de pacotes): a tela React respeita a
  mesma restrição de RBAC já aplicada no Jinja.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O cálculo de transporte do EducaManto MUST multiplicar o valor de uma viagem (tarifa
  por km ida/volta + adicional por pessoa) pelo número total de dias do pacote (`d1 + d2`) antes de
  somar ao valor final — em vez do valor de uma única viagem, como hoje.
- **FR-002**: Quando o total de dias for 1, o multiplicador MUST ser 1 (comportamento atual
  preservado, sem regressão).
- **FR-003**: Quando não houver distância calculada (km = 0), o transporte MUST continuar zero,
  independentemente do número de dias.
- **FR-004**: A linha de resultado do transporte MUST exibir explicitamente: o valor de uma viagem, o
  número de dias usado na multiplicação e o valor total resultante (ex.: "R$ X por viagem × N dias =
  R$ Y"), além das informações já existentes (km, tipo de veículo, pessoas).
- **FR-005**: Alterar o número de dias (d1/d2) após a distância já ter sido calculada MUST recalcular
  o transporte automaticamente (com a nova multiplicação), sem exigir nova busca de distância.
- **FR-006**: O valor de transporte enviado/salvo ao gerar o PDF do orçamento MUST ser o mesmo valor
  já multiplicado pelos dias exibido na tela (paridade tela↔PDF, sem recálculo divergente).
- **FR-007**: A tela React MUST reproduzir a mesma calculadora do EducaManto (seleção de pacote,
  dias, ensemble, transporte com a multiplicação por dias, valor final sem/com nota, detalhamento de
  itens e desconto por dias) consumindo os mesmos dados/regras de negócio hoje usados pela tela
  Jinja — sem duplicar a fórmula (fonte única).
- **FR-008**: A tela React MUST respeitar o mesmo controle de acesso da tela Jinja (perfis
  Comercial/Superadmin/Ensaio/Revendedor EducaManto podem usar a calculadora; a gestão de pacotes
  continua restrita a Comercial/Superadmin, apenas na tela Jinja).
- **FR-009**: A tela React NÃO PRECISA (fora de escopo nesta fatia) replicar geração de PDF,
  histórico de orçamentos nem CRUD de pacotes (criar/editar/duplicar/excluir) — essas ações continuam
  só na tela Jinja; a tela React MUST ter um link visível para a tela Jinja onde essas ações existem.
- **FR-010**: A fórmula de transporte (tarifa por km, adicional por pessoa, e agora a multiplicação
  por dias) MUST vir de uma fonte única reutilizada por Jinja, React e geração de PDF — sem números
  mágicos duplicados entre as duas telas.

### Key Entities

- **Configuração de transporte (existente)**: tarifas van (com/sem carretinha), R$/km do carro e
  divisor do adicional por pessoa — já reutilizada do orçamento (feature 076); sem mudança de dados,
  apenas de fórmula (multiplicador de dias) e exibição.
- **Pacote EducaManto (existente)**: dias (d1/d2), ensemble, itens, margens, desconto — consumido
  tanto pela tela Jinja quanto pela nova tela React, sem duplicar o cálculo de valor final.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Para um pacote de múltiplos dias fora de São Paulo, o valor de transporte somado ao
  valor final é exatamente "valor de uma viagem × número de dias" — verificável comparando o valor
  antes e depois da mudança para os mesmos parâmetros.
- **SC-002**: Para um pacote de 1 dia, o valor final (sem/com nota) é idêntico ao calculado antes
  desta feature, para os mesmos parâmetros (sem regressão).
- **SC-003**: O valor de transporte exibido na tela e o valor que sai no PDF do orçamento gerado são
  sempre iguais, em qualquer número de dias.
- **SC-004**: Um usuário consegue reproduzir na tela React, para os mesmos pacote/dias/ensemble/
  endereço, exatamente os mesmos valores sem/com nota e de transporte que obteria na tela Jinja.
- **SC-005**: Um usuário que precisa gerar PDF, ver histórico ou gerenciar pacotes consegue chegar à
  tela Jinja a partir de um link na tela React em no máximo um clique.

## Assumptions

- "Quantidade de dias" = `d1 + d2` (dias de 1 sessão + dias de 2 sessões), o mesmo total já usado
  pelo restante do cálculo do pacote (cenário "multi-day" existente) — não é um campo novo.
- A frase "calculado via calculadora para fora de São Paulo" descreve o cenário de uso (eventos fora
  de SP, onde o custo de logística é relevante) e não uma nova condição de negócio: o cálculo de
  transporte continua baseado em km (não em uma verificação de cidade/UF) — comportamento já existente
  desde a feature 076, sem mudança de escopo geográfico.
- O "adicional de show" do orçamento continua fora do EducaManto (decisão já registrada na feature
  076) — a multiplicação por dias se aplica ao total já existente (viagem + adicional por pessoa), sem
  reintroduzir o adicional de show.
- A calculadora do orçamento (fora do EducaManto) não tem conceito de múltiplos dias e **não** é
  alterada por esta feature — a fórmula de transporte em si (tarifa por km, adicional por pessoa)
  continua a mesma fonte única de `app/orcamento/transport.py`; só o EducaManto aplica o multiplicador
  de dias.
- Escopo React confirmado com o usuário: calculadora completa (pacotes, dias, ensemble, transporte,
  totais, detalhamento), sem geração de PDF, histórico ou CRUD de pacotes — essas ações permanecem
  Jinja por ora, com link de saída a partir da tela React.
- A tela React entra em `frontend/apps/internal` (staff autenticado), seguindo o padrão de RBAC e
  chamadas de API já usado pelas demais telas migradas (`apiFetch`, `@manto/money`, `@manto/ui`).
- **Descoberto durante a implementação**: desde a feature 080, o transporte do EducaManto já não
  tem seleção de tipo de veículo/carretinha — é sempre van com carretinha, e o número de pessoas é
  derivado automaticamente do item "Catering apresentação" do pacote (campo somente leitura na tela
  Jinja). Os campos de tipo/carro ficam ocultos no HTML só para não quebrar o JS existente. Por
  isso esta feature (Jinja e React) preserva esse comportamento fixo — não reintroduz uma escolha de
  veículo que a feature 080 removeu deliberadamente.
