# Feature Specification: Reestruturação do Módulo de Talentos (Listagem, Filtros e Perfil)

**Feature Branch**: `180-talentos-modulo-completo`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "Reestruturar e refinar por completo o Módulo de Talentos no app Beta (apps/internal), abrangendo a Listagem e Filtros do Banco de Talentos (/talents) e a tela de Detalhes do Talento (/talents/[id]), com fidelidade total ao comportamento do sistema Jinja legado (Live) para filtros avançados, grid do mosaico, separação rígida leitura/edição, layout em 2 colunas, histórico de eventos com KPIs, avaliações/notas e dados cadastrais completos."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Encontrar talentos rapidamente com filtros avançados (Priority: P1)

Um usuário de Casting precisa montar o elenco de um evento e busca talentos que atendam a múltiplos critérios simultâneos (ex.: personagem "Thor", idioma inglês, tamanho GG, calçado 42, com passaporte e visto americano, que já trabalhou com a Manto antes). Hoje os filtros são botões soltos sem a riqueza de opções do sistema antigo; o usuário precisa de painéis de filtro completos, com busca interna onde fizer sentido (personagem, tags), aplicados de uma vez por um botão "Filtrar".

**Why this priority**: É a ação mais frequente do dia a dia de Casting — sem filtros ricos e confiáveis, a equipe volta a usar o sistema antigo (Jinja) ou perde tempo rolando a lista inteira manualmente. É a base para qualquer outro fluxo do módulo.

**Independent Test**: Pode ser testado isoladamente acessando `/talents`, combinando múltiplos filtros no painel avançado e confirmando que o clique em "Filtrar" retorna exatamente os talentos que atendem a todos os critérios ao mesmo tempo (E lógico entre categorias de filtro, OU lógico dentro da mesma categoria).

**Acceptance Scenarios**:

1. **Given** a listagem de talentos ativos, **When** o usuário abre o painel de filtros avançados e marca duas raças e um tamanho de calçado, **Then** o sistema mantém as seleções pendentes até o clique em "Filtrar" e, ao clicar, mostra apenas talentos que combinam qualquer uma das raças marcadas E o calçado marcado.
2. **Given** o painel de filtros aberto, **When** o usuário digita no campo de busca interna de "Personagem", **Then** a lista de personagens sugeridos é restrita ao texto digitado.
3. **Given** o painel de filtros aberto, **When** o usuário marca o checkbox "Já trabalhou com a Manto" (agora dentro do painel avançado), **Then** o filtro é aplicado junto com os demais ao clicar em "Filtrar", e o checkbox não aparece mais na barra de busca principal.
4. **Given** filtros aplicados, **When** o usuário volta para a listagem depois de visitar o perfil de um talento, **Then** os filtros e a página atual continuam refletidos (não são perdidos).
5. **Given** uma tela widescreen (≥1440px), **When** a listagem é carregada, **Then** o mosaico exibe de 5 a 6 colunas de cards, cada card com foto vertical nítida e um badge de medidas (altura • tamanho • calçado) sempre visível na parte inferior.

---

### User Story 2 - Consultar o perfil completo de um talento em modo leitura limpo (Priority: P2)

Qualquer usuário autenticado (não só Casting) abre o perfil de um talento para consultar dados de contato, aparência física, documentos, veículo, histórico de participação em eventos e avaliações recebidas/dadas — sem se deparar com botões de upload, "Procurar arquivo" ou "Remover" que não pretende usar.

**Why this priority**: É a segunda ação mais comum (consulta é mais frequente que edição) e hoje mistura informação com controles de edição sempre visíveis, o que confunde e arrisca cliques acidentais. Depende dos filtros (US1) para ser alcançada, mas tem valor mesmo sem o modo de edição (US3).

**Independent Test**: Pode ser testado abrindo o perfil de qualquer talento com um usuário sem permissão de edição (ou sem clicar em "Editar") e confirmando que nenhum controle de upload/alteração aparece em nenhuma seção — apenas dados, imagens/documentos cadastrados e links "Abrir documento".

**Acceptance Scenarios**:

1. **Given** o perfil de um talento em modo leitura, **When** a página carrega, **Then** nenhum campo de formulário, botão "Procurar...", "Trocar foto" ou "Remover" está visível em nenhuma seção (cabeçalho, fotos, documentos, anotações internas).
2. **Given** o perfil de um talento com histórico de eventos, **When** a página carrega, **Then** são exibidos 4 indicadores (Eventos, Personagens, Total Faturado, Último Evento) e uma tabela com Data, Evento, Personagem e Cachê de cada participação, com link para abrir o evento.
3. **Given** um talento com avaliações registradas, **When** o usuário rola até a seção "Avaliações e Notas", **Then** vê as avaliações recebidas dos colegas (com estrelas e comentário) e as avaliações gerais dadas pelo talento, sem precisar sair da página.
4. **Given** um talento sem avaliações ou sem histórico de eventos, **When** a página carrega, **Then** as respectivas seções mostram um estado vazio claro (não erro, não seção ausente).
5. **Given** um talento com cadastro pendente de aprovação, **When** um usuário com permissão de Casting abre o perfil, **Then** vê um painel de aprovação/rejeição no topo da página, sem precisar voltar à listagem.

---

### User Story 3 - Editar cadastro do talento em modo dedicado, sem risco de alteração acidental (Priority: P3)

Um usuário com permissão de Casting/Superadmin precisa corrigir ou completar dados de um talento (medidas, contato, documentos, foto). Ele clica explicitamente em "Editar" no topo do perfil, e só então os campos viram editáveis e os controles de upload aparecem; ao sair do modo edição, a tela volta a ser só leitura.

**Why this priority**: Depende do modo leitura (US2) existir primeiro como padrão seguro. É usado com menor frequência que a consulta, mas é essencial para manter o cadastro atualizado.

**Independent Test**: Pode ser testado com um usuário com permissão de edição: abrir um perfil, confirmar modo leitura por padrão, clicar em "Editar", alterar um campo de escolha fechada (ex. tamanho) e um upload de foto, salvar, e confirmar que a tela retorna ao modo leitura refletindo os novos valores.

**Acceptance Scenarios**:

1. **Given** um usuário com permissão de edição no perfil de um talento, **When** ele clica em "Editar" no topo da página, **Then** os campos de dados cadastrais viram editáveis (respeitando escolhas fechadas como tamanho/calçado/passaporte) e os controles de foto/documento aparecem.
2. **Given** o modo de edição ativo, **When** o usuário altera o tamanho superior, **Then** a opção é escolhida de uma lista fechada (XGG/GG/G/M/P/XP), não digitada livremente.
3. **Given** um usuário sem permissão de superadmin em modo de edição, **When** ele tenta alterar o CPF, **Then** o campo permanece bloqueado com indicação de que só superadmin pode alterá-lo.
4. **Given** alterações pendentes no modo edição, **When** o usuário sai da tela sem salvar (navegação ou fechamento do modo), **Then** o sistema não persiste as alterações não salvas.
5. **Given** o modo de edição ativo, **When** o usuário clica em salvar com sucesso, **Then** a tela retorna automaticamente ao modo leitura mostrando os dados atualizados.

---

### Edge Cases

- O que acontece quando nenhum talento atende à combinação de filtros aplicada? O mosaico deve mostrar um estado vazio claro, com opção de limpar filtros.
- Como o sistema trata um talento cujo campo de raça no cadastro não corresponde a nenhuma das 5 categorias fixas do filtro (dado legado em texto livre divergente)? Esse talento não deve aparecer ao filtrar por nenhuma das 5 categorias, mas deve continuar aparecendo normalmente na listagem sem filtro de raça.
- Como o histórico de eventos se comporta quando o usuário aplica um filtro de período que não contém nenhum evento? Os 4 indicadores devem refletir zero/vazio para o período, sem quebrar a página.
- O que ocorre se um talento tiver documento com foto em formato de imagem versus PDF? Ambos devem ter pré-visualização adequada (imagem inline ou visualizador de PDF), com link alternativo para abrir em nova aba.
- O que ocorre se um usuário sem permissão de edição tentar acessar a URL de edição diretamente? Deve ser redirecionado/impedido, permanecendo no modo leitura.
- Como o painel de aprovação/rejeição se comporta após a ação (aprovar/rejeitar) ser concluída? A página de detalhe deve refletir o novo status imediatamente, sem exigir recarregar manualmente.
- O que acontece com avaliações quando o modo de avaliação anônima está ativo? Autoria de quem avaliou não deve ser exibida, mantendo consistência com o restante do sistema de avaliações.

## Requirements *(mandatory)*

### Functional Requirements

**Listagem e busca**
- **FR-001**: O sistema DEVE manter as abas "Ativos" e "Pendentes" no topo da listagem de talentos.
- **FR-002**: O sistema DEVE oferecer um campo de busca principal por nome ou nome artístico, aplicado em tempo real conforme o usuário digita.
- **FR-003**: O sistema DEVE remover o checkbox "Já trabalhou com a Manto" da barra de busca principal e disponibilizá-lo dentro do painel de filtros avançados.

**Filtros avançados**
- **FR-004**: O sistema DEVE oferecer um painel de filtros avançados organizado em categorias, cada uma com sua própria área de seleção (dropdown/painel): Personagem, Idioma, Raça, Tamanho, Calçado, Altura, Passaporte, Tags, e "Já trabalhou com a Manto".
- **FR-005**: O filtro de Personagem DEVE incluir um campo de busca interna que restringe as sugestões conforme o texto digitado.
- **FR-006**: O filtro de Idioma DEVE apresentar opções em formato de múltipla escolha (checkboxes).
- **FR-007**: O filtro de Raça DEVE apresentar as opções fixas: Amarela, Branca, Indígena, Parda, Preta, em formato de múltipla escolha.
- **FR-008**: O filtro de Tamanho DEVE apresentar duas seções distintas — "Parte de cima" e "Parte de baixo" — cada uma com as opções XGG, GG, G, M, P, XP em múltipla escolha, selecionáveis de forma independente.
- **FR-009**: O filtro de Calçado DEVE apresentar as numerações de calçado disponíveis em múltipla escolha.
- **FR-010**: O filtro de Altura DEVE permitir escolher um operador de comparação (maior ou igual, menor ou igual, ou igual) combinado com um valor numérico em centímetros.
- **FR-011**: O filtro de Passaporte DEVE apresentar as opções fixas: "passaporte + visto americano", "passaporte sem visto", "sem passaporte", em múltipla escolha.
- **FR-012**: O filtro de Tags DEVE incluir um campo de busca interna ("Buscar tag...") que restringe as tags exibidas para seleção em múltipla escolha.
- **FR-013**: O filtro "Já trabalhou com a Manto" DEVE estar disponível como opção de múltipla escolha dentro do painel avançado.
- **FR-014**: O sistema DEVE aplicar todos os filtros selecionados somente quando o usuário clicar no botão "Filtrar", e não a cada seleção individual.
- **FR-015**: O sistema DEVE combinar diferentes categorias de filtro com lógica "E" (talento deve atender a todas as categorias ativas) e valores dentro da mesma categoria com lógica "OU" (talento atende se corresponder a qualquer um dos valores marcados).
- **FR-016**: O sistema DEVE indicar visualmente quantos filtros estão ativos e permitir limpar todos de uma vez.

**Grid de resultados**
- **FR-017**: O sistema DEVE exibir os resultados em um mosaico responsivo que alcança de 5 a 6 colunas em telas widescreen, mantendo fotos verticais grandes e nítidas.
- **FR-018**: Cada card do mosaico DEVE exibir, sempre visível na parte inferior, um badge com altura, tamanho e calçado do talento.

**Perfil do talento — modo leitura**
- **FR-019**: O sistema DEVE exibir o perfil do talento por padrão em modo leitura, sem nenhum controle de upload, remoção ou edição de campo visível.
- **FR-020**: O sistema DEVE exibir, em modo leitura, apenas informações consolidadas, imagens de documentos já cadastrados, ou links de abertura (ex.: "Abrir documento") quando aplicável.
- **FR-021**: O sistema DEVE exibir um botão "Editar" destacado no cabeçalho do perfil, visível apenas para usuários com permissão de edição.
- **FR-022**: O sistema DEVE exibir, no cabeçalho, um link de retorno para a listagem, nome completo, nome artístico e um resumo de medidas do talento.
- **FR-023**: O sistema DEVE exibir, quando o talento estiver com cadastro pendente, um painel de aprovação/rejeição diretamente na tela de perfil.

**Perfil do talento — layout e conteúdo**
- **FR-024**: O sistema DEVE organizar o perfil em duas colunas em telas widescreen: uma coluna de destaque visual e histórico (foto principal, documento com foto, histórico de eventos, avaliações) e uma coluna de dados cadastrais (anotações internas, contato, documentos/PIX, aparência, veículo).
- **FR-025**: O sistema DEVE exibir a foto principal do talento em destaque, em formato vertical.
- **FR-026**: O sistema DEVE exibir uma pré-visualização do documento com foto (CNH/RG) cadastrado.
- **FR-027**: O sistema DEVE exibir 4 indicadores de histórico: total de eventos, total de personagens distintos, total faturado e data do último evento.
- **FR-028**: O sistema DEVE permitir filtrar o histórico de eventos por período de datas.
- **FR-029**: O sistema DEVE exibir uma tabela de histórico com data, evento, personagem, cachê e uma ação para abrir o evento.
- **FR-030**: O sistema DEVE exibir uma seção de avaliações contendo as avaliações recebidas de colegas (com nota em estrelas e comentário) e as avaliações gerais dadas pelo próprio talento (com nota em estrelas e comentário).
- **FR-031**: O sistema DEVE exibir anotações internas com um seletor de nível de alerta (Sem alerta, Atenção, Bloqueado); em modo leitura, exibe apenas o texto e o nível atual; em modo edição, permite editar e salvar.
- **FR-032**: O sistema DEVE exibir dados de contato: telefone, e-mail, data de nascimento, gênero, "como conheceu a Manto" e indicador "já trabalhou com a Manto".
- **FR-033**: O sistema DEVE exibir dados de documentos e PIX: CPF, RG, chave PIX, tipo de chave, e link para abrir o documento.
- **FR-034**: O sistema DEVE exibir dados de aparência: altura, raça/etnia, tamanho superior, tamanho inferior, calçado, idiomas, status de passaporte/visto (em texto legível, não código interno), e badges de habilidades e tags.
- **FR-035**: O sistema DEVE exibir a seção de veículo (marca, modelo, ano, placa, validade da CNH) sempre que qualquer um desses dados estiver preenchido, incluindo quando somente a validade da CNH existir.

**Perfil do talento — modo edição**
- **FR-036**: O sistema DEVE revelar os controles de edição de dados, troca de fotos e upload de arquivos somente após o usuário clicar em "Editar".
- **FR-037**: O sistema DEVE apresentar campos de escolha fechada (tamanho superior, tamanho inferior, calçado, passaporte) como seleção entre opções pré-definidas, não como texto livre.
- **FR-038**: O sistema DEVE restringir a edição do CPF a usuários com permissão de superadmin, mantendo o campo bloqueado para os demais.
- **FR-039**: O sistema DEVE retornar ao modo leitura automaticamente após salvar as alterações com sucesso, refletindo os novos dados.
- **FR-040**: O sistema NÃO DEVE persistir alterações feitas em modo edição caso o usuário saia sem salvar.

### Key Entities *(include if feature involves data)*

- **Talento (Talent)**: pessoa cadastrada no banco de talentos — dados pessoais, de contato, aparência física, documentos, veículo, status (ativo/pendente) e anotações internas de risco.
- **Participação em Evento**: registro histórico de um talento em um evento — personagem interpretado, cachê recebido, data do evento.
- **Avaliação Recebida**: nota e comentário dado por um colega de produção sobre o desempenho do talento em uma categoria (ex.: atuação), vinculada a um evento.
- **Avaliação Dada**: nota geral e comentário que o próprio talento deu sobre um evento em que participou.
- **Filtro Ativo**: critério de busca aplicado (categoria + um ou mais valores) que compõe a consulta de listagem.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário de Casting consegue combinar 3 ou mais critérios de filtro (ex.: personagem, tamanho e passaporte) e obter a lista filtrada em uma única ação de "Filtrar".
- **SC-002**: 100% dos cards de talento no mosaico exibem altura, tamanho e calçado sem exigir clique ou navegação adicional.
- **SC-003**: 0% dos acessos ao perfil de um talento em modo leitura exibem qualquer controle de upload, remoção ou campo editável.
- **SC-004**: Um usuário com permissão de edição consegue alterar dados cadastrais e trocar uma foto do talento sem sair da página de perfil, entrando e saindo do modo de edição em uma única sessão.
- **SC-005**: 100% dos perfis de talento com histórico de eventos exibem corretamente os 4 indicadores (Eventos, Personagens, Total Faturado, Último Evento) refletindo o período selecionado.
- **SC-006**: Um usuário consegue visualizar as avaliações recebidas e dadas por um talento sem sair da tela de perfil, quando existentes.
- **SC-007**: Usuários que não possuem permissão de edição nunca veem o botão "Editar" nem conseguem acionar controles de alteração de dados.

## Assumptions

- O botão "Editar" e os controles de edição/upload são visíveis apenas para papéis com permissão de escrita em Talentos (Casting e Superadmin), consistente com o controle de acesso já existente para as ações de aprovar/rejeitar/editar/anotar/enviar arquivo.
- A rota atual de edição dedicada (`/talents/:id/edit`) deixa de ser a forma principal de edição; ela é substituída pelo alternador de modo na própria tela de perfil (`/talents/:id`), preservando o mesmo conjunto de permissões e validações já existentes.
- O filtro de Raça usa as 5 categorias fixas solicitadas como opções de seleção; talentos cujo dado de raça (texto livre historicamente coletado) não corresponda a nenhuma das 5 categorias continuam visíveis na listagem sem filtro de raça aplicado, mas não aparecem quando qualquer uma das 5 categorias é marcada.
- O filtro de Altura com operador "igual" é uma capacidade nova (hoje o sistema só compara "maior/igual" ou "menor/igual"); segue a mesma lógica de comparação numérica em centímetros.
- As avaliações recebidas/dadas seguem as mesmas regras de exibição de autoria (modo anônimo) já aplicadas às avaliações em outras telas do sistema — não é criado um comportamento de anonimato diferente para o perfil do talento.
- O painel de aprovação/rejeição no perfil do talento usa as mesmas ações e permissões já existentes na listagem (aba Pendentes), apenas disponibilizadas também na tela de perfil.
- A verificação funcional automatizada da entrega roda contra a cópia local do banco de produção (`manto_local`, PostgreSQL), conforme padrão já estabelecido no projeto para toda validação de feature.
- Esta reestruturação não altera nenhuma tela ou rota do sistema Jinja legado (`/talents`, `/talents/<id>`, `/talents/<id>/edit` no Flask/Jinja) — a mudança é inteiramente na aplicação React (`frontend/apps/internal`), com o Jinja permanecendo como referência de comportamento, não como código compartilhado.
