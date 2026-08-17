# Feature Specification: EducaManto por responsabilidades — fim dos pacotes por nível

**Feature Branch**: `235-educamanto-responsabilidades`

**Created**: 2026-08-13

**Status**: Draft

**Input**: User description: "Reestruturação da geração de orçamentos do EducaManto: substituir os pacotes por nível (Master/Intermediário/Econômica) por cadastro por musical + seleção de responsabilidades (iluminação, sonorização, alimentação, cenário — cada uma por conta da Manto ou da contratante), matriz de equipe técnica com 4 casos, novo PDF com mínimos exigidos/o que levamos, avisos fixos, multi-páginas por configuração, transporte SP R$800 / fora de SP 2 vans, contratação Manto embutida reusando a calculadora de orçamento, nº de ensaios por musical (mínimo 2), 5% à vista como cálculo real, breakdown restrito a superadmin, e desligamento das telas Jinja legadas do EducaManto."

## Contexto

Hoje o EducaManto vende por pacotes fechados em três níveis (Master / Intermediário / Econômica), um cadastro por espetáculo × nível (21 pacotes + 1 cópia órfã). Os níveis ficaram engessados: um cliente pode querer o espetáculo completo mas fornecer a própria iluminação, e nenhum pacote representa isso. A reestruturação troca "escolher um pacote" por "escolher um **musical** e marcar **responsabilidades**": cada bloco (sonorização, iluminação, alimentação, cenário) é marcado como *por conta da Manto* ou *por conta da contratante*, e o orçamento se forma dessa combinação. A distinção "completo vs. básico" de som/iluminação **morre**: quando é por conta da Manto, é sempre a entrega completa, com custo único por musical.

## Decisões já tomadas com o dono do produto

Registradas na conversa de 13/08/2026 (válidas como fonte para o plano):

1. Som/iluminação pela Manto = **um só nível** (o completo), custo único por musical.
2. Margens por cenário (1 sessão, 2 sessões, diárias multi-dia), desconto de 5% acima de 3 dias, arredondamento para cima na centena e o fator de nota fiscal (÷ 0,84) **continuam exatamente como hoje**.
3. Fora de SP: **2 vans, uma delas com carretinha**; o adicional de viagem é **por pessoa, uma vez só** (não por van).
4. Multi-páginas: cada página é uma configuração independente e **pode trocar de musical**.
5. Contratação Manto embutida aparece **na mesma página do PDF**, num trecho "o que está incluso", e o PDF mostra **um total combinado por duração** (EducaManto + Manto, nota aplicada sobre a soma).
6. Camarim: nº de cadeiras = **tamanho da equipe daquele musical** (personagens + produção + técnicos do caso).
7. Ensaios: campo "nº de ensaios" por musical, **padrão e mínimo 2**; os custos por pessoa por ensaio (catering R$ 28, ajuda de custo R$ 50) multiplicam pelo nº de ensaios.
8. O campo de acréscimo do vendedor (comissão dele) **continua existindo** para todos os papéis com acesso.
9. Desligamento do legado Jinja: **apenas o do EducaManto** nesta feature; o plano de desligar o restante do Jinja fica para depois.
10. O "desconto especial de 5% à vista" deixa de ser só texto: vira **cálculo real exibido no PDF** (valor final à vista).
11. Valores pendentes que o dono ainda vai enviar: **custos dos técnicos** (sonoplasta, técnico de som, técnico de iluminação) e as **áreas X/Y** do aviso de suficiência do som. Até lá, entram como constantes provisórias claramente marcadas.

## Clarifications

### Session 2026-08-17 (4ª rodada — fecha o gate de deploy)

- Q: Custo do cenário/ambientação? → A: **Cenário NÃO tem custo adicional hoje e sai das
  responsabilidades por ora** ("pode inclusive tirar isso por enquanto, talvez futuramente
  a gente volte"). Não existe diferença cenário-pela-Manto × cenário-pela-contratante; o
  bloco, as colunas `custo_cenario_*` e os textos do PDF foram removidos. Nenhum valor
  muda ("não mude nada do nosso valor" — o custo era 0).
- Q: Divisão personagens×produção dos musicais? → A: **Deriva da tabela antiga de itens**:
  personagens = Cara Limpa + Bonecos (+ Papai Noel no pacote com Papai Noel); produção =
  qty do item "Produção". Cenógrafo/Maquiador ficam fora das contagens. Resultado:
  UAA 9+2 · Jardim Mágico 8+2 · Onda de Mudança 7+2 · Unicórnios 5+1 · Turma do
  Mantinho 8+2 · Natal 6+2 · Natal com Papai Noel 7+2.
- Q: Textos de alimentação (frases redigidas pelo Claude)? → A: **Aprovados como estão**;
  as frases do cenário morrem junto com o bloco.

### Session 2026-08-14 (3ª rodada — valores reais de `EspecificacoesEducamanto.md`)

- Q: Como precificar som/iluminação? → A: **Tabela ÚNICA por combinação** (vale para todos os
  musicais), com a equipe técnica JÁ DENTRO do valor: som+luz R$ 4.200 · só som R$ 2.900 · só
  luz R$ 2.900 · nada (apenas sonoplasta) R$ 750. Os preços NÃO são aditivos (o combo custa
  menos que a soma das partes) — por isso o modelo é por caso, não por bloco. Editável nas
  Configurações de Preços (`educamanto_som_luz`).
- Q: Custo ou preço? → A: **Custo da Manto, margem do musical em cima** (como o antigo item
  Som).
- Q: Escala com dias/sessões? → A: **Por dia de evento** — 1 dia (1 ou 2 sessões) = valor
  cheio; cada dia extra soma o valor de novo.
- Os **riders reais** do arquivo viram os textos do PDF: "o que levaremos" (rider Manto) e
  "mínimo exigido" (rider da contratante) para som e iluminação; a cobertura real (≈300 m²,
  até 150 pessoas) substitui o placeholder de áreas X/Y e só é impressa quando o som é da
  Manto.

### Session 2026-08-13

- Q: Quem escreve os novos textos do PDF e das dicas (mínimos exigidos da contratante, "o que levaremos" e tooltips das responsabilidades)? → A: A equipe de desenvolvimento redige a partir do material existente (PDF atual, planos.md e as descrições do dono); o dono revisa e aprova antes do deploy.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Montar orçamento por responsabilidades (Priority: P1)

O vendedor abre a calculadora, escolhe o musical (ex.: Uma Aventura Animal), e vê os quatro blocos de responsabilidade — sonorização, iluminação, alimentação e cenário — todos marcados "por conta da Manto" por padrão. Ele alterna o que a escola vai fornecer (ex.: iluminação por conta da contratante), preenche dias, ensemble, transporte e seu acréscimo, e vê o valor final se ajustar: o custo da iluminação sai, o técnico de iluminação sai da equipe, e o restante recalcula. Dicas (tooltips) ao lado de cada bloco explicam ao vendedor o que cada escolha significa.

**Why this priority**: É o coração da mudança — sem a calculadora por responsabilidades nada mais existe. Sozinha, já destrava as vendas que os pacotes engessavam.

**Independent Test**: Com um musical cadastrado, alternar cada responsabilidade e conferir que valor, equipe técnica e headcount reagem conforme a matriz; gerar o orçamento e conferir o valor congelado.

**Acceptance Scenarios**:

1. **Given** um musical selecionado com tudo "por conta da Manto", **When** o vendedor não altera nada, **Then** o valor inclui som completo, iluminação completa, alimentação, cenário e 3 técnicos (sonoplasta + téc. som + téc. iluminação).
2. **Given** som pela Manto e iluminação pela contratante, **When** o vendedor recalcula, **Then** o custo de iluminação e o técnico de iluminação saem, restando sonoplasta + técnico de som.
3. **Given** som e iluminação pela contratante, **When** o vendedor recalcula, **Then** só o sonoplasta permanece na equipe técnica.
4. **Given** qualquer configuração, **When** um usuário que não é superadmin usa a calculadora, **Then** ele vê apenas os valores finais (sem NF, com NF, à vista) e o próprio acréscimo — nunca custo base, itens, margens ou desconto interno.
5. **Given** o acréscimo digitado maior que o teto, **When** o sistema capa, **Then** o vendedor é avisado do valor efetivamente incluído (comportamento atual preservado).

---

### User Story 2 - PDF que explica responsabilidades, mínimos e quantidades (Priority: P2)

O cliente recebe um PDF que deixa claro, item a item, o que a Manto leva e o que fica por conta da escola — incluindo os mínimos exigidos quando a responsabilidade é da contratante — além das quantidades da equipe (personagens, produção, técnicos), os avisos fixos (palco mínimo, camarim, suficiência do som, visita técnica em local aberto) e o valor à vista com 5% de desconto calculado de verdade.

**Why this priority**: O PDF é o que o cliente assina; sem ele a nova lógica não chega ao mundo. Depende da US1 para existir.

**Independent Test**: Gerar PDFs nas 4 combinações de som/iluminação e conferir seções, textos, quantidades e valores.

**Acceptance Scenarios**:

1. **Given** iluminação por conta da contratante, **When** o PDF é gerado, **Then** a seção da iluminação descreve o mínimo exigido da contratante; **Given** por conta da Manto, **Then** descreve o que a Manto levará.
2. **Given** Uma Aventura Animal com som e iluminação pela Manto, **When** o PDF é gerado, **Then** aparece a equipe: 9 personagens, 2 de produção e 3 técnicos — e a linha de camarim exige cadeiras para essa equipe (14).
3. **Given** d2 = 0, **When** o PDF é gerado, **Then** a linha "dias com 2 sessões" não aparece.
4. **Given** qualquer orçamento, **When** o PDF é gerado, **Then** constam: palco mínimo de 5 m de frente × 4 m de fundo; camarim obrigatório (espaço com cadeiras para a equipe, espelho, banheiro e água); som completo suficiente para área X (fechado) / Y (aberto); aviso de visita técnica ou chamada de vídeo para local aberto; valor à vista (PIX) com 5% de desconto calculado.
5. **Given** uma observação digitada pelo vendedor, **When** o PDF é gerado, **Then** a observação aparece formatada em seção própria.

---

### User Story 3 - Várias páginas, uma comparação clara (Priority: P3)

O vendedor monta a primeira configuração, clica "gerar segunda página", monta uma variação (outro conjunto de responsabilidades ou até outro musical), e pode voltar e editar qualquer página antes de gerar. O PDF final traz uma página por configuração, e a diferença entre elas fica evidente para o cliente.

**Why this priority**: Substitui o comportamento atual de "uma página por pacote" — importante para a venda comparativa, mas o fluxo de página única já entrega valor.

**Independent Test**: Criar 2+ páginas com configurações diferentes, editar a primeira após criar a segunda, gerar e conferir o PDF.

**Acceptance Scenarios**:

1. **Given** uma página configurada, **When** o vendedor cria a segunda, **Then** a segunda nasce como cópia editável da primeira e ambas permanecem editáveis até a geração.
2. **Given** página 1 com som pela Manto e página 2 com som pela contratante, **When** o PDF é gerado, **Then** cada página mostra sua configuração e seus valores, com a diferença de responsabilidades visível.
3. **Given** páginas com musicais diferentes, **When** o PDF é gerado, **Then** cada página reflete equipe, quantidades e custos do seu musical.

---

### User Story 4 - Contratação Manto embutida (Priority: P4)

Vendendo o EducaManto para um evento que também terá uma apresentação da Manto tradicional, o vendedor clica "Adicionar contratação Manto" na própria calculadora do EducaManto. Na mesma tela abre o módulo da calculadora de orçamento de eventos — data e local herdados, coordenador, equipe, acréscimos/BV e ajustes finos — com as durações (1h, 2h, 3h, 4h ou mais). O valor se soma ao do EducaManto e a nota fiscal é aplicada sobre a soma. No PDF, a página ganha o trecho "o que está incluso" da contratação Manto e um total combinado por duração.

**Why this priority**: Cross-sell valioso, mas depende de US1/US2 prontas e de integração com outro módulo — maior risco, entregue por último.

**Independent Test**: Adicionar contratação Manto a uma configuração, conferir soma, NF sobre o total e o PDF com totais por duração.

**Acceptance Scenarios**:

1. **Given** uma configuração EducaManto com contratação Manto de 1h e 2h, **When** o PDF é gerado, **Then** a página mostra um total combinado para cada duração, com a nota aplicada sobre a soma (EducaManto + Manto).
2. **Given** a contratação Manto adicionada, **When** o vendedor monta a equipe/acréscimos, **Then** usa os mesmos módulos da calculadora de orçamento de eventos (fonte única — melhoria futura lá reflete aqui).
3. **Given** uma configuração sem contratação Manto, **When** o PDF é gerado, **Then** nada da contratação aparece.

---

### User Story 5 - Administrar musicais (Priority: P5)

O superadmin cadastra e edita musicais: nome, nº de personagens, nº de pessoas de produção, nº de ensaios (mínimo 2), itens de custo, custo do som completo, da iluminação completa, do cenário, valores de ensemble e margens. A tela substitui a atual gestão de pacotes.

**Why this priority**: A migração inicial já semeia os 7 musicais a partir dos dados atuais; a tela de administração é necessária para evolução, não para o primeiro uso.

**Independent Test**: Criar um musical novo, usá-lo na calculadora e conferir custos, equipe e PDF.

**Acceptance Scenarios**:

1. **Given** a tela de musicais, **When** o superadmin edita o nº de ensaios para 3, **Then** os custos por pessoa por ensaio multiplicam por 3 nos próximos orçamentos.
2. **Given** um musical novo criado, **When** o vendedor o usa, **Then** tudo funciona sem depender de convenção de nome (nada de detectar "master"/"econômica" por texto).
3. **Given** a tentativa de salvar nº de ensaios menor que 2, **When** o superadmin confirma, **Then** o sistema bloqueia com mensagem clara.

---

### Edge Cases

- Musical com nome livre (ex.: "Essencial"): não há mais detecção por substring — descrições vêm das responsabilidades, nunca do nome.
- Acréscimo do vendedor acima do teto: capa e avisa (comportamento atual).
- Fora de SP marcado sem km informado: transporte de vans zerado até o km existir; o caminhão de R$ 800 permanece removido.
- Dentro de SP com km digitado: km é ignorado (não há vans dentro de SP); vale só o caminhão de R$ 800.
- Ensemble 0 / responsabilidades todas da contratante: orçamento mínimo válido (elenco + produção + sonoplasta + ensaios + caminhão).
- Remover a única página: bloqueado — sempre existe ao menos uma configuração.
- Contratação Manto sem nenhuma duração selecionada: geração bloqueada com aviso.
- Orçamentos antigos no histórico (formato de pacotes): continuam abrindo e re-baixando o PDF idêntico ao congelado; o "Recalcular" de um snapshot antigo abre a calculadora nova com o que for mapeável e avisa o que não for.
- Deploy sem os valores definitivos de técnicos/áreas: valores provisórios entram destacados como pendência de negócio (gate de lançamento — ver Assumptions).

## Requirements *(mandatory)*

### Functional Requirements

**Cadastro de musicais (substitui pacotes)**

- **FR-001**: O sistema DEVE cadastrar musicais com: nome, nº de personagens, nº de pessoas de produção, nº de ensaios (inteiro, mínimo 2, padrão 2), itens de custo por cenário (1 sessão / 2 sessões / diárias multi-dia), custo único do som completo, custo único da iluminação completa, custo do cenário (ambientação de espetáculo), custos de alimentação por pessoa, cachês de ensemble por cenário e margens por cenário.
- **FR-002**: Os níveis Master/Intermediário/Econômica DEIXAM de existir como conceito: nenhuma regra pode depender do nome do musical (fim da detecção por substring).
- **FR-003**: A migração DEVE criar os 7 musicais a partir dos pacotes Master atuais (som completo = custo do Som do Master de cada espetáculo), descartar os pacotes Intermediário/Econômica e a cópia órfã, e preservar intactos todos os orçamentos já gravados no histórico.

**Calculadora por responsabilidades**

- **FR-004**: A calculadora DEVE oferecer, por configuração: musical, dias com 1 e 2 sessões, ensemble, transporte, acréscimo do vendedor, e os quatro blocos de responsabilidade — sonorização, iluminação, alimentação (dia do evento) e cenário — cada um alternável entre "por conta da Manto" (padrão) e "por conta da contratante". A data da apresentação continua existindo como campo opcional fora do preço, alimentando o alerta de personagens já escalados no dia (comportamento atual preservado).
- **FR-005**: Cada bloco de responsabilidade DEVE ter uma dica (tooltip) explicando ao vendedor o que a escolha implica para o cliente.
- **FR-006**: Blocos por conta da contratante DEVEM remover seus custos do cálculo; blocos por conta da Manto DEVEM incluí-los.
- **FR-007**: A equipe técnica DEVE seguir a matriz: som e iluminação pela Manto → sonoplasta + técnico de som + técnico de iluminação; só som → sonoplasta + técnico de som; só iluminação → sonoplasta + técnico de iluminação; nenhum → apenas o sonoplasta. O sonoplasta é fixo em todos os casos, com custo próprio por cenário (valores provisórios até o dono enviar os definitivos).
- **FR-008**: Existem dois headcounts derivados: o **do dia do evento** (personagens + produção + técnicos do caso + ensemble), que alimenta cadeiras do camarim, catering da apresentação e o adicional por pessoa da viagem; e o **de ensaio** (personagens + produção + ensemble, sem técnicos), que alimenta os custos por pessoa dos ensaios. (Confere com os dados atuais: Uma Aventura Animal tem catering de ensaio para 11 = 9 personagens + 2 produção.)
- **FR-009**: Os custos por pessoa por ensaio (catering de ensaio e ajuda de custo) DEVEM multiplicar pelo nº de ensaios do musical, aplicados sobre o headcount de ensaio.
- **FR-010**: A fórmula de fechamento DEVE permanecer a atual: margens por cenário, desconto de 5% acima de 3 dias, acréscimo capado, arredondamento para cima na centena para o valor sem NF e (líquido ÷ 0,84) arredondado para cima na centena para o valor com NF.
- **FR-011**: O valor à vista (PIX) DEVE ser calculado de fato — 5% de desconto sobre o valor final — e exibido na tela e no PDF.

**Transporte**

- **FR-012**: Dentro de São Paulo: item fixo de caminhão de R$ 800 (substitui os R$ 600 atuais); sem cálculo de vans.
- **FR-013**: Fora de São Paulo (marcado pelo vendedor): o caminhão sai do cálculo e entra o transporte de viagem com 2 vans — uma comum e uma com carretinha — cobrando o km de ida e volta das duas, multiplicado pelos dias, mais o adicional por pessoa (uma única vez, pelo headcount da configuração).

**Contratação Manto embutida**

- **FR-014**: A calculadora DEVE oferecer "Adicionar contratação Manto" por configuração, reusando os módulos da calculadora de orçamento de eventos (coordenador, equipe, acréscimos/BV, ajustes finos) como fonte única — sem duplicar regra de negócio.
- **FR-015**: Data e local DEVEM ser herdados da configuração EducaManto; as durações disponíveis (1h, 2h, 3h, 4h ou mais) geram um valor da parte Manto por duração.
- **FR-016**: O total combinado por duração DEVE ser calculado sobre a soma dos líquidos: sem NF = soma arredondada para cima na centena; com NF = (soma ÷ 0,84) arredondada para cima na centena — a nota incide uma única vez, sobre o total (nunca por parte).

**Multi-páginas**

- **FR-017**: O vendedor DEVE poder criar novas páginas (configurações independentes, inclusive de musicais diferentes), navegar entre elas, editá-las e removê-las (mínimo de 1) antes de gerar.
- **FR-018**: O PDF DEVE trazer uma página A4 por configuração, cada uma completa e autoexplicativa; o conteúdo DEVE caber na página (tipografia compacta como hoje, 8.5pt nas seções longas) e, se ainda assim estourar, a observação livre transborda para uma página de continuação — valores e avisos obrigatórios nunca saem da primeira página da configuração.

**PDF**

- **FR-019**: Para cada bloco de responsabilidade, o PDF DEVE mostrar: por conta da Manto → o que levaremos; por conta da contratante → o mínimo exigido dela.
- **FR-020**: O PDF DEVE mostrar as quantidades da equipe do musical: personagens, produção e técnicos (conforme a matriz do caso).
- **FR-021**: O PDF DEVE conter os avisos fixos: palco mínimo de 5 m de frente × 4 m de fundo; camarim obrigatório (espaço com cadeiras para a equipe, espelho, banheiro e água); "o som completo é suficiente para área X (local fechado) e área Y (local aberto)" (valores pendentes do dono); local aberto exige visita técnica ou chamada de vídeo.
- **FR-022**: Linhas de dias com valor zero NÃO aparecem no PDF.
- **FR-023**: O vendedor DEVE poder digitar uma observação livre por orçamento (texto simples, até 2.000 caracteres, com quebras de linha preservadas), exibida formatada em seção própria do PDF.
- **FR-024**: Quando houver contratação Manto, a mesma página DEVE mostrar o trecho "o que está incluso" da parte Manto e o total combinado por duração.
- **FR-025**: Os textos por nível (descrições Master/Intermediário/Econômica e "O que está incluso" por nível) DEIXAM de existir, substituídos pelos textos por responsabilidade.

**Histórico e congelamento**

- **FR-026**: A geração DEVE congelar o snapshot completo da(s) configuração(ões) — musical, responsabilidades, equipe, valores, contratação Manto e observação — e o histórico DEVE re-renderizar o PDF idêntico a partir dele; os valores congelados DEVEM ser os calculados pelo servidor.
- **FR-027**: Snapshots antigos (formato de pacotes) DEVEM continuar abrindo e re-baixando o PDF original.

**Visibilidade (RBAC)**

- **FR-028**: Apenas superadmin vê custos, breakdown de itens, margens, desconto interno e cálculos de comissão. Os demais papéis com acesso veem apenas: valores finais (sem NF, com NF, à vista), transporte total, e o próprio campo de acréscimo.

**Desligamento do legado**

- **FR-029**: As telas Jinja do EducaManto (calculadora, pacotes e histórico legados) e a réplica da fórmula em JavaScript DEVEM ser desligadas nesta feature; qualquer acesso às rotas antigas leva à tela React equivalente. O restante do legado Jinja da plataforma fica fora do escopo.

### Key Entities

- **Musical**: substitui o pacote. Nome, nº de personagens, nº de produção, nº de ensaios (≥ 2), itens de custo por cenário, custo do som completo, da iluminação completa, do cenário, alimentação por pessoa, cachês de ensemble, margens por cenário.
- **Configuração (página)**: uma combinação musical + responsabilidades + dias + ensemble + transporte + acréscimo + contratação Manto opcional + observação. Um orçamento tem 1..N configurações.
- **Responsabilidade**: um dos quatro blocos (sonorização, iluminação, alimentação, cenário) com dois estados: Manto ou contratante.
- **Equipe técnica**: derivada da matriz som × iluminação; sonoplasta fixo; custos próprios por cenário.
- **Orçamento (snapshot)**: retrato congelado de todas as configurações e valores calculados pelo servidor, base do histórico e da re-emissão do PDF.
- **Contratação Manto embutida**: subconjunto da calculadora de orçamento de eventos (equipe, coordenador, acréscimos/BV, durações), vinculado a uma configuração.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O vendedor monta um orçamento com responsabilidades personalizadas e gera o PDF em menos de 3 minutos — sem precisar escolher entre 22 pacotes.
- **SC-002**: Nas 4 combinações de som/iluminação, a equipe técnica, o headcount e os valores saem corretos em 100% dos casos de teste.
- **SC-003**: 100% dos PDFs gerados contêm os avisos obrigatórios (palco, camarim, som/área, visita técnica), nenhuma linha de dias zerada, e o valor à vista com 5% calculado.
- **SC-004**: Valor exibido na tela e valor impresso no PDF são idênticos em 100% das gerações, e o valor congelado é sempre o calculado pelo servidor.
- **SC-005**: Usuários que não são superadmin não têm acesso a nenhum custo, margem ou breakdown — em tela, em resposta de API ou em PDF.
- **SC-006**: 100% dos orçamentos antigos do histórico continuam abrindo e re-emitindo o PDF idêntico ao congelado.
- **SC-007**: Com contratação Manto de N durações, o PDF mostra N totais combinados, cada um igual à soma das partes com a nota aplicada sobre o total.
- **SC-008**: Nenhuma tela ou rota legada Jinja do EducaManto permanece acessível após o deploy.

## Assumptions

- **Valores (gate FECHADO na 4ª rodada)**: som/iluminação resolvidos na 3ª rodada (tabela
  única real); cenário saiu das responsabilidades (sem custo); personagens × produção
  derivados da tabela antiga de itens e conferidos musical a musical. Não há mais valores
  provisórios — a feature aguarda apenas o "push 235" do dono.
- **Textos das responsabilidades**: redigidos pela equipe de desenvolvimento e **aprovados
  pelo dono na 4ª rodada** (frases de alimentação como estão; as de cenário morreram com o
  bloco).
- **Catering de ensaio e ajuda de custo** não são afetados pelo bloco "alimentação": o bloco controla apenas a alimentação do dia do evento; os custos de ensaio sempre existem, multiplicados pelo nº de ensaios.
- **À vista**: o desconto de 5% é exibido como valor final à vista para os dois regimes (sem NF e com NF), calculado sobre o valor final de cada um.
- **Ensemble** continua funcionando como hoje (linha própria + crescimento dos itens por pessoa), agora também somando no headcount unificado.
- **Teto do acréscimo** continua sendo o valor da configuração sem transporte, como hoje.
- **Comissão do responsável EducaManto** (5% sobre o lucro, fora do orçamento) não muda nesta feature.
- **Gráfica e demais itens de custo** do musical permanecem itens sempre inclusos (não viram responsabilidade alternável).
- **Tela de musicais**: gerir continua só superadmin; comercial pode ver a lista de musicais **sem custos nem margens** (a visão com custos passa a ser exclusiva do superadmin, coerente com a nova regra de visibilidade).
- **Config de transporte** (tarifas por km e divisor do adicional) continua vindo das Configurações de Preços compartilhadas com a calculadora de orçamento de eventos.
