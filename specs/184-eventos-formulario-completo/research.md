# Research: Reconstrução do Formulário de Cadastro/Edição de Eventos

Baseado em pesquisa exaustiva de `app/templates/event_create.html`, `app/templates/event_detail.html`,
`app/calendar/routes.py`, `app/api/agenda.py`/`agenda_write.py`, `app/models.py`,
`frontend/apps/internal/src/lib/eventCreate.ts`/`eventAttachments.ts`,
`frontend/packages/ui/src/components/file-upload.tsx` e os componentes `ClientPicker`/
`FormResponsePicker` — feita por dois agentes de exploração dedicados antes desta spec.

## 1. Criação de evento continua estritamente JSON — anexos em duas fases

**Decision**: `POST /api/events` permanece exatamente como está (JSON puro, sem arquivos). A
criação de um evento com anexos vira um fluxo de duas fases no frontend: (1) `POST /api/events`
com os campos centrais → recebe `event.id`; (2) uma sequência de chamadas aos endpoints de anexo
já existentes (`POST /events/<id>/payments`, `/contracts`, `/reimbursements`,
`/observations` com `obs_type=image`), um por anexo pendente.

**Rationale**: Não existe hoje nenhum precedente de upload em lote/multipart no endpoint de
criação, nem um padrão de "array local de arquivos pendentes, enviado tudo de uma vez" em nenhuma
tela do repo (confirmado por busca exaustiva) — o padrão real já usado (`EventDetailPage.tsx`,
`eventAttachments.ts`) é "adiciona um item, envia na hora, renderiza da resposta do servidor",
que só funciona porque o evento já existe. Estender `POST /api/events` para aceitar multipart
misturaria contratos (JSON vs. multipart) e duplicaria validação de arquivo que os endpoints de
anexo já fazem — mais simples e seguro reaproveitar o que já existe em uma segunda fase.

**Alternatives considered**: Multipart único cobrindo tudo (rejeitado — exigiria reescrever o
parsing de `POST /api/events` e todos os endpoints de anexo, alto risco para o endpoint mais
crítico do sistema, sem ganho real de UX perceptível pelo vendedor); persistir os arquivos como
"rascunho" antes do evento existir (rejeitado — exigiria um novo conceito de anexo órfão/rascunho
não previsto em nenhum lugar do sistema, complexidade desproporcional ao ganho).

**Reembolso também migra para a fase 2**: hoje `POST /api/events` já aceita
`has_reembolso`/`reembolso_description`/`reembolso_amount` no corpo JSON (sem arquivo). Esta
feature move essa criação inteira para a fase 2, via `POST /events/<id>/reimbursements`
(multipart, já aceita descrição+valor+arquivo opcional) — evita ter dois caminhos concorrentes de
criação de reembolso (um no corpo JSON, outro no endpoint de anexo) e ganha de graça o suporte à
nota fiscal do gasto (GAP 14 do relatório de paridade), que o corpo JSON nunca teve.

## 2. Tratamento de falha parcial na fase 2 (FR-029)

**Decision**: Depois que a fase 1 (criação do evento) tem sucesso, o formulário permanece na
mesma tela em um estado "enviando anexos", mostrando uma lista de cada anexo pendente com seu
status (enviando / enviado / falhou). Só navega para `/events/<id>` quando todos os anexos
pendentes chegaram a um estado final (enviado, ou descartado explicitamente pelo vendedor). Anexos
que falharem ficam com um botão "Tentar novamente" que reenvia só aquele item.

**Rationale**: O evento já existe em produção — voltar para "novo evento" perderia a referência a
ele; navegar direto para `/events/<id>` escondendo uma falha faria o vendedor achar que salvou tudo
quando na verdade um comprovante ficou de fora. Manter o estado visível até tudo resolver é a
única forma de cumprir FR-029 sem introduzir fila/retry assíncrono no backend.

**Alternatives considered**: Navegar direto e mostrar um toast de erro (rejeitado — toast some,
vendedor pode perder a informação de qual anexo especificamente falhou, numa tela com potencial de
vários anexos simultâneos); reverter (apagar) o evento criado se algum anexo falhar (rejeitado —
destrutivo e desnecessário; o evento em si foi criado com sucesso e é o dado mais importante).

## 3. Novo endpoint de edição em bloco — não há equivalente a reaproveitar

**Decision**: Novo endpoint `PATCH /api/events/<id>` em `app/api/agenda_write.py`, núcleo em
`app/calendar/event_ops.py::update_event_core()`. RBAC: mesmo conjunto de `_can_create_event()`
(COMERCIAL, SUPERADMIN) — não o mais permissivo `_can_edit_event()` usado pelas ações pontuais de
logística/casting, porque este endpoint também escreve campos financeiros sensíveis (valores de
venda, forma de pagamento) no mesmo payload, e criar um evento já exige esse mesmo nível de
permissão.

**Rationale**: Busca exaustiva (`grep` por `PATCH`/`PUT` em todo `app/api/agenda_write.py`)
confirma que não existe hoje nenhuma rota que atualize título, datas, valores, forma de pagamento,
vendedor, elenco como conjunto ou clientes como conjunto — só ações pontuais por recurso (uma
role, um comprovante, a logística). Construir a edição sobre essas ações pontuais exigiria
disparar dezenas de chamadas encadeadas por salvamento (uma por personagem alterado, uma para
clientes, etc.), com risco real de estado parcialmente salvo em caso de falha no meio — pior do
que um único endpoint transacional para os campos centrais.

**Alternatives considered**: Reaproveitar `POST /api/events` com um `event_id` opcional no corpo
para "modo edição" (rejeitado — mistura semântica de criar/atualizar no mesmo endpoint, dificulta
RBAC e auditoria, e a criação já tem lógica própria de pré-preenchimento de orçamento que não faz
sentido num fluxo de edição); expor N endpoints PATCH, um por campo (rejeitado — não é assim que o
formulário salva hoje nem como o vendedor pensa a ação "salvar o evento").

## 4. Elenco na edição: reconciliação por `role_id`, não substituição cega

**Decision**: O corpo do `PATCH` inclui `characters: {role_id: number|null, name, ...}[]`. O
núcleo (`update_event_core`) reconcilia por identidade:
- Linhas com `role_id` presente e existente → atualiza os campos daquele `EventRole`.
- Linhas sem `role_id` → cria um `EventRole` novo (mesma lógica de auto-detecção de figurino por
  nome já usada na criação).
- `EventRole`s `role_type="character"` existentes que **não** aparecem no conjunto enviado são
  candidatos a remoção — mas se algum deles tiver `invite_status == "accepted"` e quem está
  editando não for SUPERADMIN, a operação inteira é **recusada** (400/409, nada é salvo), com
  mensagem indicando qual personagem tem convite aceito. Isso replica a mesma trava que já existe
  em `DELETE /roles/<id>` hoje (feature 145/casting_ops) — só que aplicada de forma atômica ao
  conjunto inteiro, antes de qualquer escrita.

**Rationale**: Um `EventRole` carrega estado de workflow (convite aceito, figurino feito, cachê
negociado) que uma simples "apagar tudo e recriar" destruiria a cada salvamento do formulário de
edição, mesmo quando o vendedor só queria mudar o título. Reconciliar por id preserva esse estado
para quem não mudou de linha, e a trava de convite aceito evita que uma edição descuidada apague
silenciosamente o trabalho do casting.

**Alternatives considered**: Apagar todos os `EventRole` do evento e recriar do zero a cada
edição (rejeitado — destrutivo, perde `invite_status`/`figurino_done`/etc. mesmo para
personagens não alterados); não permitir editar elenco nesta tela, só na tela de detalhe
(rejeitado — contradiz a exigência explícita de paridade de campos/blocos na edição).

## 5. Clientes na edição: substituição simples (sem estado de workflow)

**Decision**: `clients: {client_id, relation}[]` no corpo do `PATCH` é tratado como substituição
completa — apaga todos os `EventClient` do evento e recria a partir da lista enviada (mesma lógica
de `_create_client_links` já usada na criação).

**Rationale**: Diferente de `EventRole`, `EventClient` não carrega nenhum estado próprio (não tem
convite, não tem histórico) — é uma tabela de associação pura. Substituição completa é simples,
correta e não tem nada a perder.

**Alternatives considered**: Reconciliar por id como o elenco (rejeitado — complexidade
desnecessária para uma entidade sem estado; nenhum ganho real).

## 6. Contrato: `is_signed` na hora do upload, sem tocar o RBAC do toggle existente

**Decision**: `POST /events/<id>/contracts` ganha um parâmetro multipart opcional `is_signed`
(`"true"`/`"false"`, default `false`), aplicado só na criação do registro. O endpoint separado
`POST /contracts/<id>/toggle-signed` (hoje restrito a SUPERADMIN) **não muda** — continua
existindo para alternar o status depois, só para SUPERADMIN.

**Rationale**: O relatório de exploração confirmou que o toggle-signed já em produção é
propositalmente restrito a SUPERADMIN (mudar o status de "assinado" depois de registrado é uma
correção sensível). Mas a legítima necessidade desta feature é permitir que o **próprio vendedor**
que está subindo o contrato já marque "já veio assinado" no momento do upload — igual ao
`contract_signed` do Jinja legado, que faz parte do mesmo formulário de criação, sem gate de
papel. Adicionar o campo só na criação do registro atende a isso sem reabrir o RBAC do toggle.

**Alternatives considered**: Estender o RBAC do toggle-signed para incluir COMERCIAL (rejeitado —
mudaria o comportamento de um endpoint existente usado hoje por outras telas, fora do escopo desta
feature, e reduziria uma trava de integridade posta lá deliberadamente); não suportar
`is_signed` na criação, deixando sempre `false` e exigindo um SUPERADMIN alternar depois
(rejeitado — quebra paridade explícita com o checkbox "Contrato já assinado" do Bloco 6, pedido
pelo usuário).

## 7. Cadastro rápido de cliente: zero backend novo

**Decision**: Bloco 1 usa o hook já existente `useQuickCreateClient()`
(`frontend/apps/internal/src/lib/clientes.ts`), que chama `POST /api/clientes/quick-create`
(já existe, RBAC `COMERCIAL/FINANCEIRO/SUPERADMIN`, já trata nome/telefone obrigatórios com
`ApiRequestError.fields`, e já reaproveita um cliente existente pelo telefone em vez de duplicar).

**Rationale**: Esse endpoint já faz exatamente o que o Bloco 1 pede (nome, telefone, empresa
opcional, "salvar e adicionar") — não há necessidade de tocar no backend.

**Alternatives considered**: Nenhuma — o endpoint já resolve o requisito por completo.

## 8. Auto-geração de título e calculadora de desconto: 100% client-side

**Decision**: Ambas são funções puras no frontend, sem chamada de rede. Título: concatena os
nomes de personagem (linhas `characters`) em maiúsculas com `" + "`, prefixado por `(TIPO) ` se
`event_type` estiver selecionado; só continua atualizando automaticamente enquanto o vendedor não
tiver editado manualmente o campo Título (flag local `titleEdited`, replicando `autoTitle()`/
`titleEdited` do Jinja legado). Desconto: `(gross - final) / gross * 100`, recalculado a cada
tecla nos dois campos de valor, sem persistir separadamente (mesmo comportamento do legado — é só
um indicador, o valor final que importa é `sale_value`).

**Rationale**: Paridade exata de comportamento com o legado (`autoTitle()`, painel de "% Desconto"
em `event_create.html`), sem necessidade de nenhum campo novo no modelo.

**Alternatives considered**: Persistir o percentual de desconto como campo do evento (rejeitado —
o legado nunca fez isso; é derivado de `sale_value_gross`/`sale_value`, recalculável a qualquer
momento).

## 9. Validação em tempo real + auto-scroll: `react-hook-form` (mode `onBlur`) + `setFocus`

**Decision**: `useForm` passa a rodar com `mode: "onBlur"` (valida ao perder o foco, além de já
validar no submit) para os campos escalares controlados por `zod`. Ao falhar o `handleSubmit`,
uma ordem fixa de campos (`FIELD_ORDER`, seguindo a ordem visual dos 7 blocos) é varrida contra
`formState.errors`; o primeiro nome de campo presente em `errors` recebe `setFocus(nome)` (API
nativa do `react-hook-form`, já move o foco) e o container do campo recebe
`scrollIntoView({behavior: "smooth", block: "center"})` explicitamente, para garantir a rolagem
suave pedida mesmo em campos que o navegador já traria para a viewport de forma abrupta. Campos
fora do `react-hook-form` (blocos de lista — elenco, clientes, comprovantes, observações) entram
na mesma varredura via um estado de erro próprio (`blockErrors: Record&lt;string, string&gt;`),
populado por uma função de validação client-side chamada junto do `handleSubmit`.

**Rationale**: `react-hook-form` já é a base do formulário atual — `setFocus` é a forma
suportada de focar um campo por nome sem manipular refs manualmente, e complementa (não substitui)
o `scrollIntoView` pedido explicitamente no requisito.

**Alternatives considered**: Biblioteca de scroll-to-error de terceiros (rejeitado — desnecessário,
`react-hook-form` já tem `setFocus` e `scrollIntoView` nativo do browser resolve o resto sem nova
dependência).

## 10. Ponto de entrada para editar

**Decision**: `EventDetailPage.tsx` ganha um botão "Editar" no `actions` do `PageHeader`, visível
quando `data.flags.can_edit_event` for verdadeiro, linkando para `/events/${id}/edit`.

**Rationale**: `flags.can_edit_event` já existe e já é a trava usada por toda ação de edição da
tela de detalhe — reaproveitá-la para a nova tela de edição é a única forma de manter paridade de
permissão sem inventar uma regra nova.
