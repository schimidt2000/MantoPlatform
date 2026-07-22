# Feature Specification: Revisão de Mídia em React

**Feature Branch**: `170-revisao-midia-react`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Migrar o espaço de revisão de mídia estilo Vimeo Review
(blueprint `revisao`) para React + API JSON — fatia final da User Story 6 (Cauda
Administrativa) e última fatia da migração 144. Escopo: 14 rotas — listar espaços, criar
espaço (com upload de materiais e seleção de revisores), ver espaço, upload de materiais,
atualizar revisores, excluir espaço, visualizar material (vídeo/áudio/imagem/PDF) com
histórico de versões, excluir material, substituir material (nova versão), finalizar material
(remove arquivo do armazenamento), e os 4 comentários (listar/criar/concluir/excluir — já
JSON hoje). RBAC: Marketing/Superadmin criam espaços; criador do espaço ou Superadmin
gerenciam; criador, revisores selecionados ou Superadmin veem/comentam."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Listar e criar espaço de revisão (Priority: P1)

Como Marketing ou Superadmin, preciso ver a lista de espaços de revisão que posso acessar
(criados por mim, onde sou revisor, ou todos se sou Superadmin) e criar um espaço novo com
título, descrição, materiais e revisores selecionados.

**Why this priority**: é o ponto de entrada do módulo inteiro.

**Independent Test**: listar espaços como criador, como revisor convidado e como Superadmin;
criar um espaço novo com 2 materiais e 1 revisor, e conferir que o espaço aparece na lista de
quem tem acesso e não aparece para quem não tem.

**Acceptance Scenarios**:

1. **Given** um usuário Marketing ou Superadmin, **When** ele lista os espaços, **Then** vê os
   que criou, aqueles onde é revisor selecionado e, se Superadmin, todos os demais — ordenados
   do mais recente para o mais antigo.
2. **Given** o mesmo usuário, **When** ele cria um espaço com título, descrição, materiais
   (vídeo/áudio/imagem/PDF) e revisores, **Then** o espaço é criado com os materiais válidos
   salvos e os revisores vinculados; arquivos de tipo não suportado ou acima de 512MB são
   recusados individualmente (o espaço ainda é criado com os materiais válidos).
3. **Given** um usuário sem papel Marketing/Superadmin, **When** ele tenta criar um espaço,
   **Then** recebe 403.
4. **Given** um usuário sem nenhuma relação com um espaço (não é criador, revisor nem
   Superadmin), **When** ele tenta abri-lo, **Then** recebe 403.

---

### User Story 2 - Gerenciar o espaço: upload, revisores e exclusão (Priority: P2)

Como criador do espaço (ou Superadmin), preciso adicionar mais materiais depois da criação,
atualizar a lista de revisores e excluir o espaço inteiro quando não for mais necessário.

**Why this priority**: são as ações de manutenção do espaço — vêm logo após criar/listar por
serem parte do ciclo de vida normal de um espaço em uso.

**Independent Test**: adicionar um material a um espaço existente, trocar os revisores, e
excluir um espaço — conferindo que a exclusão remove também os arquivos do armazenamento
(material atual e versões antigas).

**Acceptance Scenarios**:

1. **Given** o criador de um espaço (ou Superadmin), **When** ele envia mais materiais,
   **Then** eles são adicionados na sequência dos já existentes (posição incremental).
2. **Given** o mesmo usuário, **When** ele atualiza a lista de revisores, **Then** a lista
   antiga é substituída pela nova (não é incremental).
3. **Given** o mesmo usuário, **When** ele exclui o espaço, **Then** todos os materiais (atual
   e versões antigas ainda disponíveis) têm seus arquivos removidos do armazenamento, e o
   espaço some da lista de todo mundo.
4. **Given** um revisor (não criador, não Superadmin), **When** ele tenta fazer upload,
   atualizar revisores ou excluir o espaço, **Then** recebe 403 — essas ações são exclusivas
   de quem gerencia o espaço.

---

### User Story 3 - Visualizar material e comentar (Priority: P3)

Como qualquer pessoa com acesso ao espaço (criador, revisor ou Superadmin), preciso visualizar
um material (vídeo, áudio, imagem ou PDF) e adicionar comentários ancorados — no tempo do
vídeo/áudio, na página do PDF, ou num ponto da imagem —, além de concluir/reabrir e excluir
comentários conforme minha permissão.

**Why this priority**: é o núcleo de valor do módulo (o "porquê" de existir) — depende do
espaço já estar criado (US1) e populado (US2).

**Independent Test**: abrir um material de cada tipo, adicionar um comentário ancorado, listar
os comentários da versão atual, concluir um comentário próprio e um alheio (conforme
permissão), e excluir um comentário — conferindo os mesmos 403 de hoje em cada ação restrita.

**Acceptance Scenarios**:

1. **Given** um material de vídeo/áudio, **When** o usuário comenta em um ponto da reprodução,
   **Then** o comentário é salvo com o `timecode` (segundos) e associado à versão atual do
   material.
2. **Given** um material de PDF, **When** o usuário comenta numa página, **Then** o comentário
   é salvo com o número da `page`.
3. **Given** um material de imagem, **When** o usuário comenta num ponto da imagem, **Then** o
   comentário é salvo com `pos_x`/`pos_y` relativos (0–1).
4. **Given** um material com versões antigas, **When** o usuário abre uma versão antiga
   (`?v=N`), **Then** vê o material daquele snapshot em modo só-leitura — sem poder comentar
   nele (comentário só na versão atual).
5. **Given** um comentário, **When** o autor, o criador do espaço ou o Superadmin o marca como
   concluído (ou reabre), **Then** o estado muda, registrando quem concluiu e quando.
6. **Given** um comentário, **When** alguém que não é o autor nem Superadmin tenta excluí-lo,
   **Then** recebe 403 — só autor ou Superadmin excluem.
7. **Given** um usuário sem acesso ao espaço, **When** ele tenta ver o material ou os
   comentários pela API diretamente, **Then** recebe 403.

---

### User Story 4 - Substituir e finalizar material (Priority: P4)

Como criador do espaço (ou Superadmin), preciso enviar uma nova versão de um material
(preservando a versão anterior no histórico) e finalizar um material aprovado, removendo seus
arquivos do armazenamento sem perder registros/comentários.

**Why this priority**: são as ações de ciclo de vida mais avançadas do material — vêm por
último por serem menos frequentes que visualizar/comentar (US3).

**Independent Test**: substituir o arquivo de um material por um novo do mesmo tipo, conferir
que a versão anterior vira um snapshot navegável no histórico com os comentários daquela
versão preservados; finalizar um material e conferir que o arquivo (atual e de versões
antigas ainda disponíveis) é removido do armazenamento, mas os registros continuam existindo.

**Acceptance Scenarios**:

1. **Given** um material existente, **When** o criador do espaço envia um arquivo do MESMO
   tipo de mídia, **Then** a versão atual vira um snapshot no histórico, a nova versão
   incrementa o número e reinicia o prazo de expiração (7 dias).
2. **Given** o mesmo material, **When** o arquivo enviado é de um tipo de mídia diferente,
   **Then** a API recusa (400) com mensagem explicando a incompatibilidade.
3. **Given** um material aprovado, **When** o criador do espaço o finaliza, **Then** o arquivo
   atual e os arquivos de versões antigas ainda disponíveis são removidos do armazenamento; o
   registro, o histórico e os comentários continuam existindo e visíveis.

---

### Edge Cases

- Upload de arquivo com extensão não reconhecida → recusado individualmente com mensagem, sem
  impedir os demais arquivos válidos do mesmo envio.
- Arquivo acima de 512MB → recusado individualmente, mesma regra acima.
- Comentário em uma versão diferente da atual → recusado (409) — comentário só na versão
  vigente.
- Resolver/reabrir um comentário → alterna o estado (não é uma ação unidirecional).
- Espaço sem nenhum material → tela de detalhe mostra estado vazio amigável.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE expor listar espaços (filtrado por acesso), criar espaço (com
  upload multipart de materiais e seleção de revisores), ver detalhe do espaço, upload de
  materiais adicionais, atualizar revisores e excluir espaço como endpoints JSON, reaproveitando
  exatamente as regras de RBAC e validação de arquivo já existentes.
- **FR-002**: O sistema DEVE expor a visualização de um material (com suporte a `?v=` para
  versões antigas, somente leitura) como endpoint JSON.
- **FR-003**: O sistema DEVE expor excluir, substituir (nova versão, mesmo tipo de mídia) e
  finalizar (remove arquivos) material como endpoints JSON, reaproveitando o snapshot de
  versão e a limpeza de arquivos já existentes.
- **FR-004**: O sistema DEVE expor listar (por versão), criar, concluir/reabrir e excluir
  comentário como endpoints JSON — já são JSON hoje; esta fatia só os move para o padrão
  `/api/*` e os liga ao frontend React.
- **FR-005**: Toda validação de erro (arquivo inválido, tipo incompatível na substituição,
  comentário fora da versão atual) DEVE retornar mensagem amigável em pt-BR.
- **FR-006**: O comportamento das rotas Jinja antigas (`/revisao/*`) DEVE permanecer idêntico
  ao de antes desta fatia até serem desativadas.

### Key Entities

- **Espaço de Revisão (ReviewSpace)**: título, descrição, criador; já existente.
- **Material (ReviewAsset)**: arquivo, tipo de mídia, posição, versão, prazo de expiração,
  estado finalizado; já existente.
- **Versão anterior (ReviewAssetVersion)**: snapshot de uma versão substituída; já existente.
- **Revisor (ReviewReviewer)**: vínculo usuário↔espaço; já existente.
- **Comentário (ReviewComment)**: corpo, âncora (timecode/página/posição), versão, estado
  resolvido; já existente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário com acesso consegue criar espaço, gerenciar materiais/revisores,
  visualizar qualquer tipo de material, comentar, resolver/excluir comentários, substituir e
  finalizar materiais inteiramente pela interface React, sem abrir a tela antiga.
- **SC-002**: Os dados/resultados em React são idênticos aos da tela antiga para o mesmo
  usuário e mesma ação — verificado por paridade automatizada.
- **SC-003**: Nenhuma ação restrita (criar espaço, gerenciar espaço, excluir comentário alheio)
  é executável por quem não tem a permissão correspondente — 403 em todos os casos.
- **SC-004**: Ao final desta fatia, **100% das rotas do sistema têm endpoint JSON
  equivalente** (SC-002 da spec 144) — a migração 144 fica completa.

## Assumptions

- O visualizador de material em React usa players HTML5 nativos (`<video>`/`<audio>`) para
  vídeo/áudio, `<img>` para imagem e um link/`<iframe>` para PDF — sem replicar a UI completa
  de anotação em timeline (marcadores visuais sobre a barra de progresso) do template Jinja
  atual nesta fatia; a lista de comentários com timecode/página exibido em texto e um botão
  "ir para este ponto" cobre o mesmo valor funcional (ver, criar, ancorar, resolver, excluir
  comentário) com uma interação mais simples. Ajustar a fidelidade visual da timeline fica para
  uma iteração futura, se necessário.
- Upload de múltiplos arquivos grandes (até 512MB) usa o mesmo padrão multipart já estabelecido
  (`contracts/upload-endpoints.md`, feature 153) — sem barra de progresso dedicada nesta fatia
  (o padrão de loading do botão, Princípio V, já indica que o envio está em andamento).
