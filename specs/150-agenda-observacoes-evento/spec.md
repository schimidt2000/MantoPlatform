# Feature Specification: observações do evento em React (150)

**Feature Branch**: `150-agenda-observacoes-evento`

**Created**: 2026-07-21

**Status**: Draft

**Input**: Continuação da escrita da agenda (migração 144, US2). Casting e ações de nível-evento
(confirmar/logística) já migrados (146/147/148/149). Esta fatia migra as **observações do evento**
— hoje despachadas pelos POSTs Jinja `/events/<id>/observations/add` e
`/events/<id>/observations/<obs_id>/delete`. Uma observação é um bloco de informação que a equipe
anexa ao evento: **texto**, **link** ou **imagem** (`EventObservation.obs_type`). Fora de escopo:
**criar observação do tipo imagem** (depende de upload multipart, adiado junto com contrato/
pagamento/reembolso, exatamente como a 149 adiou os uploads) — imagens já existentes aparecem em
**leitura**, mas criar imagem nova segue só no Jinja por enquanto.

## Contexto

Continuação direta de 146/147/148/149, **mesmo padrão strangler-fig**: o núcleo de cada ação é
extraído para um módulo compartilhado (parâmetros explícitos, sem `request.form`/`flash`/
`current_user`), reusado por dois adaptadores finos — o handler Jinja e o endpoint JSON (Princípio
I, uma só implementação da regra). As observações operam sobre a coleção do **evento**:

- **adicionar** (`add_observation`): hoje o Jinja aceita várias observações de uma vez (arrays
  `obs_type[]`/`obs_content[]`/`obs_label[]`/`obs_image[]`), cada uma texto, link ou imagem;
  texto/link exigem conteúdo não-vazio, imagem exige arquivo. Sem gate de papel
  (`@login_required` — qualquer usuário autenticado). Esta fatia migra **texto e link** (uma
  observação por chamada da API); **imagem fica de fora** (upload adiado).
- **remover** (`delete_observation`): apaga uma observação do evento (qualquer tipo). Sem gate de
  papel além de `@login_required`, escopada ao evento.

Hoje o React (feature 145) **não mostra** a seção de Observações, embora a API já serialize
`data["observations"]` — mas **sem** o `file_path`, então imagens não teriam como ser exibidas.
Esta fatia cria a **seção de Observações** na `EventDetailPage` (leitura de todos os tipos) e os
controles de **adicionar (texto/link)** e **remover**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver e adicionar observações (texto/link) (Priority: P1)

Do detalhe do evento em React, qualquer usuário autenticado vê as observações já anexadas ao evento
(texto, link e imagem) e pode acrescentar uma observação de **texto** ou **link**, com um rótulo
opcional. A observação persiste exatamente como o form Jinja gravaria e aparece na tela sem reload.

**Independent Test**: abrir um evento que já tenha observações dos três tipos e conferir que todas
aparecem (imagem exibida a partir do arquivo já servido); adicionar uma observação de texto pela
tela React e conferir que uma `EventObservation` idêntica à que o Jinja gravaria é criada e passa a
aparecer na lista.

**Acceptance Scenarios**:

1. **Given** um evento com observações de texto, link e imagem, **When** o usuário abre o detalhe em
   React, **Then** as três aparecem — texto como texto, link como âncora clicável, imagem como
   miniatura carregada do arquivo servido — igual ao que o `event_detail.html` mostra.
2. **Given** o form de nova observação, **When** o usuário escolhe "texto", digita conteúdo e salva,
   **Then** é criada uma `EventObservation` com `obs_type="text"`, `content` igual ao digitado e
   `label` opcional — idêntica à que o Jinja gravaria — e ela aparece na lista sem reload.
3. **Given** o form de nova observação, **When** o usuário escolhe "link" e informa uma URL, **Then**
   é criada uma `EventObservation` com `obs_type="link"` e a URL em `content`.
4. **Given** conteúdo vazio para texto/link, **When** o usuário tenta salvar, **Then** nada é criado
   (paridade com o Jinja, que ignora item de texto/link sem conteúdo) e o front sinaliza sem quebrar.
5. **Given** o botão de salvar, **When** clicado, **Then** dá feedback imediato e um clique a mais
   não cria observação duplicada (Princípio V).

---

### User Story 2 - Remover observação (Priority: P2)

Do detalhe do evento em React, qualquer usuário autenticado remove uma observação do evento
(qualquer tipo). A remoção persiste e a tela atualiza sem reload.

**Independent Test**: remover uma observação pela tela React e conferir que a `EventObservation`
correspondente some do banco — mesmo efeito do POST de exclusão do Jinja — e que ela some da lista.

**Acceptance Scenarios**:

1. **Given** um evento com uma observação, **When** o usuário confirma a remoção, **Then** a
   `EventObservation` é apagada (mesmo efeito do Jinja) e some da lista sem reload.
2. **Given** uma observação inexistente ou de outro evento, **When** o usuário tenta remover, **Then**
   recebe 404 e nada muda — paridade com o `first_or_404` escopado por evento do Jinja.
3. **Given** a remoção, **When** repetida (segundo clique/segunda chamada), **Then** não quebra: a
   segunda tentativa apenas retorna 404, sem efeito colateral (Princípio V).

---

### Edge Cases

- **Imagem em leitura, não em escrita**: observações de imagem já existentes DEVEM aparecer na tela
  React (a serialização precisa expor a URL do arquivo). Mas **criar** imagem nova NÃO faz parte
  desta fatia — o form React só oferece texto e link; o botão de imagem segue só no Jinja até a
  fatia de uploads.
- **Sem gate de papel**: adicionar e remover exigem apenas usuário autenticado (como o Jinja). Não
  há RBAC de papel a preservar aqui — mas o servidor DEVE continuar exigindo sessão válida (401 sem
  login), nunca confiar só no front.
- **Escopo por evento na remoção**: o Jinja remove com `first_or_404(id=obs_id, event_id=event_id)`
  — remover uma observação que não pertence ao evento dá 404. A API preserva esse escopo.
- **Conteúdo vazio**: texto/link sem conteúdo são ignorados (não viram registro), igual ao loop do
  Jinja. A API rejeita com 400 (uma observação por chamada, então "ignorar em silêncio" vira erro
  explícito) — o front impede o envio antes disso.
- **Coexistência**: Jinja (`app.`) e React (`beta`) gravam no mesmo banco; um só caminho de lógica
  (núcleo compartilhado) evita divergência. O POST/DELETE Jinja continua 200/302 inalterado.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Adicionar (texto/link) e remover observação MUST ter endpoints JSON dedicados que
  executam a MESMA lógica já existente, reusando um núcleo compartilhado — não reimplementando
  (Princípio I).
- **FR-002**: Cada ação MUST produzir exatamente o mesmo estado no banco que o fluxo Jinja
  equivalente (mesma linha em `event_observations`: `obs_type`, `content`, `label`; mesma remoção),
  verificado campo a campo contra `manto_local`.
- **FR-003**: A autorização MUST ser idêntica à atual: apenas sessão autenticada (sem gate de
  papel), aplicada no servidor — requisição sem login recebe 401/redirect, nunca cria/remove.
- **FR-004**: A serialização de leitura MUST passar a expor, por observação de tipo imagem, a **URL
  servível do arquivo** (derivada de `file_path`), para o React exibir a imagem — mantendo os
  campos já existentes (`id`, `obs_type`, `content`, `label`, `created_at`) para texto e link.
- **FR-005**: Ao concluir, cada endpoint MUST devolver o evento atualizado no formato de leitura da
  145 (`serialize_event_detail`), respeitando o RBAC de serialização, para a tela re-renderizar sem
  reload.
- **FR-006**: O endpoint de adicionar MUST aceitar apenas `obs_type` "text" ou "link" com `content`
  não-vazio (rejeitando vazio e rejeitando "image" com 400); o de remover MUST escopar a observação
  ao evento (404 se não pertencer).
- **FR-007**: Nenhum botão MUST ficar "morto" ao clique; toda ação dá feedback imediato e um clique
  a mais NUNCA cria/remove registro duplicado (Princípio V).
- **FR-008**: As ações de observação no `event_detail.html` Jinja (incluindo criar imagem e criar
  várias de uma vez) MUST continuar funcionando inalteradas durante toda a transição (coexistência,
  mesmo banco).
- **FR-009**: A seção de Observações em React MUST cumprir o Princípio VIII (mobile-first) — sem
  rolagem horizontal em 320–430px, alvos de toque ≥44px, imagens sem estourar a largura.

### Key Entities

Sem entidade nova. Escrita sobre `EventObservation` (`event_id`, `obs_type`, `content`, `label`,
`file_path`, `created_at`) já existente. Nenhuma mudança de schema.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Para adicionar (texto/link) e remover, o estado do banco após executar pela API é
  indistinguível do estado após executar pelo fluxo Jinja, para os mesmos dados — verificado campo a
  campo contra `manto_local`.
- **SC-002**: Observações dos três tipos (texto, link, imagem) já existentes aparecem corretamente
  na tela React, com a imagem carregada do arquivo servido.
- **SC-003**: Nenhuma ação de observação no app Jinja regride durante a migração (incluindo criar
  imagem e criar várias de uma vez, que seguem só no Jinja).
- **SC-004**: Um clique repetido em salvar/remover nunca gera um segundo registro nem um segundo
  efeito relevante.

## Assumptions

- **Reuso via extração**: o núcleo de cada ação é extraído para um módulo compartilhado (ex.:
  `observation_ops`) recebendo parâmetros explícitos; o handler Jinja e o endpoint JSON viram
  adaptadores finos. O Jinja continua fazendo o loop de múltiplas observações e o tratamento de
  upload de imagem; a API chama o núcleo para uma observação de texto/link. UMA implementação da
  regra de criar/remover (nome do módulo é decisão do plano).
- **Endpoints REST por ação**: `POST /api/events/<id>/observations` (adiciona uma; body `obs_type`
  ∈ {text,link}, `content`, `label?`) e `DELETE /api/observations/<obs_id>`. Nomes finais no plano.
- **URL da imagem**: derivada de `file_path` (relativo a `UPLOAD_FOLDER`) pela rota estática de
  uploads já existente; a serialização passa a incluir esse campo (só relevante para `obs_type`
  "image"). Decisão de forma (campo `url`/`image_url`) fica no plano.
- A verificação usa test client contra `manto_local`, requests fora de `app_context`; sem e-mail
  (observações não disparam notificação).
- Fora de escopo: **criar observação de imagem** (upload multipart, adiado com os demais uploads);
  e o restante do evento ainda em Jinja (criar/excluir evento, venda/comercial, sincronização) —
  fatias seguintes.
- Continuação natural do bloco de detalhe do evento em React: depois desta fatia, as observações
  deixam de estar ausentes na tela React (leitura completa + escrita de texto/link).
