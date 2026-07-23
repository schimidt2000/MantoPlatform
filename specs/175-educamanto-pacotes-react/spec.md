# Feature Specification: EducaManto — Pacotes e Conteúdos em React

**Feature Branch**: `175-educamanto-pacotes-react`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "Migrar as telas e fluxos de pacotes/conteúdos do EducaManto (app/educamanto) do Jinja legado para o painel interno em React, usando o Design System já estabelecido nas features 173/174. Escopo: (1) listagem e CRUD de pacotes educacionais, (2) geração/download de orçamento em PDF por pacote, (3) histórico de orçamentos gerados. Fora de escopo: Portal do Artista (spec separada 176)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Montar e gerar orçamento por pacote (Priority: P1)

Um usuário com acesso ao EducaManto (Comercial, Ensaio, Revendedor ou SuperAdmin) abre a calculadora, escolhe um ou mais pacotes educacionais, ajusta parâmetros do orçamento (dias, elenco, transporte, nome do cliente) e gera um PDF do orçamento para enviar ao cliente. Essa é a tela de uso diário do módulo.

**Why this priority**: É o fluxo mais usado do EducaManto hoje (a calculadora já está em React desde a feature 171); sem os pacotes carregando e sem conseguir gerar o PDF, o resto do módulo não tem valor.

**Independent Test**: Acessar a tela do EducaManto, selecionar um pacote existente, preencher dias/elenco, clicar em "Gerar orçamento" e confirmar que o PDF é baixado e que um registro aparece no histórico.

**Acceptance Scenarios**:

1. **Given** existem pacotes cadastrados, **When** o usuário abre a tela do EducaManto, **Then** a lista de pacotes carrega com nome e valores calculados, sem exigir refresh manual.
2. **Given** o usuário selecionou pacote(s) e preencheu os campos obrigatórios (dias), **When** clica em "Gerar orçamento", **Then** o PDF é baixado automaticamente e o orçamento passa a aparecer no histórico.
3. **Given** nenhum pacote foi selecionado ou os dias estão zerados, **When** o usuário tenta gerar o orçamento, **Then** o sistema mostra uma mensagem de erro amigável e não gera o PDF.

---

### User Story 2 - Gerenciar pacotes educacionais (Priority: P2)

Um SuperAdmin cria, edita, duplica ou remove pacotes educacionais (nome, margens, dias com desconto, comissão, itens de custo/conteúdo) para manter o catálogo de ofertas atualizado.

**Why this priority**: Sem gestão de pacotes o catálogo fica estático; é usado com bem menos frequência que gerar orçamentos (só quando a oferta comercial muda), por isso vem depois da US1.

**Independent Test**: Como SuperAdmin, criar um pacote novo com itens, editá-lo, duplicá-lo e removê-lo, verificando que cada ação reflete imediatamente na lista e na calculadora (US1).

**Acceptance Scenarios**:

1. **Given** o usuário é SuperAdmin, **When** cria um pacote novo com nome, margens e ao menos um item de custo, **Then** o pacote passa a aparecer na lista de pacotes e na calculadora.
2. **Given** um pacote existente, **When** o SuperAdmin edita seus itens ou parâmetros, **Then** os valores calculados na calculadora refletem a mudança imediatamente.
3. **Given** um pacote existente, **When** o SuperAdmin clica em "Duplicar", **Then** uma cópia é criada com nome prefixado ("Cópia de ...") pronta para edição.
4. **Given** um pacote existente, **When** o SuperAdmin exclui o pacote, **Then** o sistema pede confirmação antes de remover e, após confirmar, o pacote some da lista e da calculadora.
5. **Given** um usuário sem papel SuperAdmin, **When** tenta acessar a gestão de pacotes, **Then** o sistema nega o acesso (mesma regra hoje aplicada nas rotas Jinja).

---

### User Story 3 - Consultar histórico de orçamentos gerados (Priority: P3)

Um usuário do EducaManto consulta o histórico de orçamentos já gerados, filtra por cliente/pacote e período, e reabre o PDF de um orçamento antigo (valores congelados no momento da geração). SuperAdmin também filtra por quem gerou.

**Why this priority**: É uma tela de consulta/auditoria, usada com menor frequência que gerar (US1) ou manter (US2) pacotes.

**Independent Test**: Gerar dois orçamentos diferentes, abrir o histórico, filtrar por texto e por período, e reabrir o PDF de um deles conferindo que os valores batem com os do momento da geração (não com o pacote atual, caso ele tenha sido editado depois).

**Acceptance Scenarios**:

1. **Given** existem orçamentos gerados, **When** o usuário abre o histórico, **Then** vê a lista ordenada do mais recente para o mais antigo, com cliente, pacotes e data.
2. **Given** o usuário digita um termo de busca ou define um período, **When** aplica o filtro, **Then** a lista mostra apenas os orçamentos correspondentes.
3. **Given** um orçamento do histórico, **When** o usuário reabre o PDF, **Then** os valores exibidos são os congelados na geração, mesmo que o pacote original tenha sido editado ou removido depois.
4. **Given** o usuário é SuperAdmin, **When** abre o histórico, **Then** vê e pode filtrar por "Gerado por"; usuários sem esse papel não veem essa coluna/filtro.

### Edge Cases

- O que acontece se o pacote usado em um orçamento antigo for editado ou excluído depois? O histórico deve continuar mostrando o snapshot congelado, sem quebrar (comportamento já existente no Jinja legado, deve ser preservado).
- Como o sistema trata a tentativa de excluir um pacote que está selecionado no momento na calculadora de outro usuário? A exclusão prossegue (sem lock), a tela da calculadora deve tratar o pacote ausente sem quebrar.
- O que acontece se o usuário tentar gerar orçamento sem nenhum pacote com valor de dias preenchido? Mensagem de erro amigável, sem chamar a API.
- Como o sistema se comporta se não houver nenhum pacote cadastrado ainda (primeiro acesso)? Mesma regra do legado: cria automaticamente o pacote padrão "Uma Aventura Animal" na primeira listagem.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE listar todos os pacotes educacionais cadastrados, com nome e valores calculados, para os papéis Comercial, Ensaio, Revendedor EducaManto e SuperAdmin.
- **FR-002**: O sistema DEVE permitir que SuperAdmin e Comercial acessem a gestão (criar/editar/duplicar/excluir) de pacotes; Ensaio e Revendedor EducaManto só usam a calculadora, sem acesso à gestão.
- **FR-003**: O sistema DEVE restringir criação, edição e exclusão de pacotes apenas ao papel SuperAdmin, mantendo a regra já existente no Jinja legado.
- **FR-004**: O sistema DEVE gerar um PDF de orçamento a partir dos pacotes selecionados e parâmetros informados (dias, elenco, transporte, nome do cliente), reaproveitando a lógica de geração de PDF já existente (`app/educamanto/pdf.py`).
- **FR-005**: O sistema DEVE salvar cada orçamento gerado em um histórico, com um snapshot congelado dos valores no momento da geração (independente de mudanças futuras no pacote original).
- **FR-006**: O sistema DEVE permitir consultar o histórico de orçamentos com busca textual (cliente/pacotes) e filtro por período de geração.
- **FR-007**: O sistema DEVE exibir e permitir filtrar por "Gerado por" no histórico apenas para o papel SuperAdmin.
- **FR-008**: O sistema DEVE permitir reabrir o PDF de qualquer orçamento do histórico, mostrando os valores congelados na geração original.
- **FR-009**: O sistema DEVE exibir mensagem de erro amigável (sem quebrar a tela) quando a geração de orçamento for tentada sem pacote selecionado ou sem dias preenchidos.
- **FR-010**: O sistema DEVE pedir confirmação do usuário antes de excluir um pacote (ação destrutiva).
- **FR-011**: O sistema DEVE criar automaticamente o pacote padrão "Uma Aventura Animal" caso nenhum pacote exista ainda, preservando o comportamento atual.
- **FR-012**: O sistema DEVE manter as rotas Jinja legadas de `app/educamanto` funcionando sem regressão durante e após esta migração (padrão strangler-fig do projeto).

### Key Entities *(include if feature involves data)*

- **Pacote educacional (EducaMantoPackage)**: nome, margens por cenário (1/2 sessões, com/sem desconto por dias), percentual de comissão, valores de elenco (ensemble) por cenário; contém uma lista ordenada de itens de custo.
- **Item de pacote (EducaMantoItem)**: nome, quantidade, custos por cenário (1/2 sessões × normal/dias), indicador se cresce com o elenco.
- **Orçamento gerado (EducaMantoQuote)**: quem gerou, nome do cliente, rótulo dos pacotes incluídos, snapshot congelado (JSON) dos valores usados na geração, data de criação.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário consegue gerar e baixar um orçamento em PDF a partir da tela React em menos de 1 minuto, sem precisar recarregar a página manualmente.
- **SC-002**: 100% dos fluxos de gestão de pacotes (criar, editar, duplicar, excluir) funcionam na tela React com o mesmo resultado que a versão Jinja legada, validado pela verificação funcional contra `manto_local`.
- **SC-003**: Reabrir qualquer orçamento do histórico sempre reproduz os valores exatamente como gerados originalmente, mesmo após o pacote correspondente ter sido alterado ou excluído.
- **SC-004**: Nenhuma rota Jinja legada de `app/educamanto` quebra após a migração (paridade comportamental).

## Assumptions

- O núcleo de geração de PDF (`app/educamanto/pdf.py`) e a lógica de cálculo (`app/educamanto/pricing_ops.py`) são reaproveitados como estão, sem duplicar regra de negócio — apenas expostos via novos endpoints de API.
- O RBAC replicado na API segue exatamente os conjuntos de papéis hoje usados em `app/educamanto/routes.py` (`_CAN_USE`, `_CAN_PACKAGES`, `_CAN_MANAGE`).
- "Conteúdos" citados no pedido do usuário correspondem aos itens de custo/conteúdo do pacote (`EducaMantoItem`) já existentes no modelo — não há um conceito de "conteúdo pedagógico" separado nos models atuais; se esse for outro conceito, precisa de esclarecimento antes da implementação.
- Reordenação de itens dentro de um pacote (se necessária) segue o mesmo padrão adotado na feature 169 (botões, não drag-and-drop).
- Fora de escopo: qualquer tela ou fluxo do Portal do Artista (spec 176, dedicada).
