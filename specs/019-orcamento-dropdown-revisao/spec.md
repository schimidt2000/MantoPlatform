# Feature Specification: Orçamento — dropdown ao adicionar + consistência + revisão

**Feature Branch**: `019-orcamento-dropdown-revisao`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User description: "Na tela de criar orçamentos: (1) revisar o código/lógica; (2) ao clicar
em adicionar ator/cantor (e especial), descer um dropdown para escolher qual opção vai para a
lista; (3) o '+R$100 show / +R$20 maquiagem' só aparece no cantor — está fora do padrão. Sinto que
a tela está ficando complexa, inclusive a config de preços no banco."

## Contexto

A calculadora de orçamento é muito usada, mas cresceu e o usuário sente complexidade e "saída do
padrão". Esta entrega faz **mudanças concretas de baixo risco** + entrega uma **revisão escrita**
dos pontos estruturais (para decidir depois, sem mexer no cálculo de dinheiro agora):

1. **Adicionar via dropdown**: hoje "+ Ator/Cantor" e "+ Especial" já inserem uma linha com um
   padrão; o usuário quer **escolher antes**, num dropdown, qual item entra na lista.
2. **Consistência do cantor**: as dicas "(+R$100)" no Show e "(+R$20)" na Maquiagem aparecem só no
   cantor e estão **fixas no código** (podem divergir do preço configurado). Devem ser removidas
   para ficar igual aos demais tipos.
3. **Revisão**: documentar os achados estruturais (config de preços como JSON no banco; cálculo
   duplicado no navegador e no servidor; valores fixos espalhados) com recomendação — sem refatorar
   agora.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Escolher o que adicionar por um dropdown (Priority: P1)

Ao clicar em "Adicionar Ator/Cantor", desce um dropdown com as opções (Ator cara limpa, Boneco,
Cantor); ao escolher, a linha correspondente entra na lista. O mesmo para "Adicionar Especial",
listando os especiais disponíveis.

**Why this priority**: É a mudança de fluxo pedida; deixa claro o que está sendo adicionado.

**Independent Test**: Clicar no dropdown de Ator/Cantor, escolher "Cantor" e confirmar que entra uma
linha de cantor; clicar no de Especial, escolher um personagem e confirmar que ele entra.

**Acceptance Scenarios**:

1. **Given** o dropdown de Ator/Cantor, **When** o usuário escolhe uma opção, **Then** uma linha
   daquele subtipo é adicionada à lista.
2. **Given** o dropdown de Especial, **When** o usuário escolhe um personagem, **Then** uma linha
   daquele especial é adicionada.
3. **Given** uma opção escolhida, **When** a linha é adicionada, **Then** o dropdown volta ao texto
   inicial ("+ Ator / Cantor" / "+ Especial"), pronto para um novo item.

---

### User Story 2 - Show/Maquiagem consistentes em todos os tipos (Priority: P1)

As opções de Show e Maquiagem aparecem iguais em todos os tipos de artista — sem dica de valor fixa
só no cantor.

**Why this priority**: Tira a inconsistência e o valor hardcoded que pode mentir.

**Acceptance Scenarios**:

1. **Given** uma linha de cantor, **When** o usuário a vê, **Then** Show e Maquiagem aparecem sem
   "(+R$100)"/"(+R$20)" — igual aos demais tipos.
2. **Given** o cálculo do orçamento, **When** o cantor tem show/maquiagem marcados, **Then** o valor
   continua sendo calculado normalmente (a remoção é só do texto-dica, não do cálculo).

---

### User Story 3 - Revisão estrutural documentada (Priority: P2)

A equipe recebe um documento curto com os pontos de complexidade/risco do módulo de orçamento e uma
recomendação, para decidir um próximo passo sem pressa.

**Acceptance Scenarios**:

1. **Given** a revisão, **When** o usuário a lê, **Then** entende os principais riscos (config de
   preços em JSON; cálculo duplicado; valores fixos) e a recomendação de cada um.

---

### Edge Cases

- **Adicionar sem escolher**: se o dropdown voltar ao item inicial, nada é adicionado.
- **Especiais configuráveis**: a lista do dropdown de especiais reflete os especiais cadastrados
  (não uma lista fixa paralela).
- **Config de preços corrompida**: hoje o sistema cai nos preços padrão em silêncio; passa a
  registrar o erro no log (sem quebrar a tela).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: "Adicionar Ator/Cantor" MUST apresentar um dropdown com as opções de subtipo (cara
  limpa, boneco, cantor); escolher uma adiciona a linha correspondente.
- **FR-002**: "Adicionar Especial" MUST apresentar um dropdown com os especiais disponíveis;
  escolher um adiciona a linha correspondente.
- **FR-003**: Após adicionar, o dropdown MUST voltar ao rótulo inicial, pronto para novo item.
- **FR-004**: As opções Show e Maquiagem MUST aparecer iguais em todos os tipos de artista, sem dica
  de valor fixa exclusiva do cantor.
- **FR-005**: A remoção das dicas NÃO MUST alterar o cálculo do orçamento (apenas texto).
- **FR-006**: Falha ao carregar a configuração de preços NÃO MUST ser silenciosa — MUST ser
  registrada (log), mantendo o fallback para os preços padrão sem quebrar a tela.
- **FR-007**: O comportamento de cálculo, transporte, NF, durações e personalização (features
  anteriores) MUST permanecer inalterado.
- **FR-008**: A entrega MUST incluir um documento de revisão dos pontos estruturais do módulo, sem
  executá-los nesta rodada.

### Key Entities *(include if feature involves data)*

- **Configuração de preços** (já existe): sem mudança de estrutura nesta entrega; apenas o
  tratamento de erro de leitura passa a ser registrado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Adicionar um ator/cantor ou especial é feito escolhendo no dropdown em até 2 cliques,
  sem entrar uma linha "errada" por padrão.
- **SC-002**: 0 dicas de valor fixas aparecem exclusivamente no cantor; Show/Maquiagem ficam iguais
  em todos os tipos.
- **SC-003**: Os valores calculados do orçamento permanecem idênticos aos de antes para os mesmos
  inputs (nenhuma regressão de cálculo).
- **SC-004**: Falhas de leitura da config passam a aparecer no log (0 falhas silenciosas).
- **SC-005**: Existe um documento de revisão com os pontos estruturais e recomendações.

## Assumptions

- O dropdown de Ator/Cantor oferece os 3 subtipos já existentes (cara limpa, boneco, cantor); o de
  Especial reflete a lista de especiais cadastrada.
- "Remover as dicas do cantor" (decisão do usuário): Show/Maquiagem ficam sem o "(+R$ ...)".
- O refactor estrutural (normalizar a config de preços; unificar o cálculo do navegador com o do
  servidor) fica **fora desta entrega** (decisão do usuário) e vai para o documento de revisão.
