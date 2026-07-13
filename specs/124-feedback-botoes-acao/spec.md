# Feature Specification: Feedback Visual em Todo Botão de Ação

**Feature Branch**: `124-feedback-botoes-acao`

**Created**: 2026-07-13

**Status**: Draft

**Input**: "Preciso que não só nessa tela mas que isso vire regra dentro da nossa
constituição. Quero evitar ao máximo que existam telas onde vc aperta um botão e nada
acontece. Não ter nenhum feedback é muito problemático."

## Contexto

Um usuário tentou registrar um gasto extra anexando a foto da nota fiscal pelo celular, em
conexão instável. O botão "Registrar gasto" não deu nenhum sinal visível de que o envio
estava em andamento — ele pareceu travado. O usuário, achando que não tinha funcionado,
saiu da tela no meio do envio (upload de ~600KB por 14 segundos), e o pedido foi abortado
pelo próprio celular antes do servidor responder.

Investigação mostrou que o sistema já tem uma proteção global contra duplo envio (todo
`<form>` desabilita seus botões ao ser enviado), mas essa proteção só desabilita o botão —
sem nenhuma mudança visual perceptível (sem opacidade reduzida, sem texto de "enviando",
sem indicador de carregamento). Do ponto de vista de quem usa, "desabilitado sem nenhum
sinal visual" e "nada aconteceu" são indistinguíveis — por isso a cliente/usuário não
soube que o envio estava em progresso.

Esta feature: (1) reforça a constituição do projeto para que essa exigência — todo botão
de ação muda de aparência de forma visível ao ser clicado — seja regra permanente, não uma
correção pontual; e (2) corrige o mecanismo global existente para que ele realmente cumpra
essa regra em qualquer tela que use um formulário comum, sem precisar de código extra por
tela.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver que o clique foi recebido, mesmo em envio lento (Priority: P1)

Um usuário clica em qualquer botão que salva, cria, envia, aprova ou exclui algo dentro do
sistema (não só na tela de gastos). Mesmo que a ação demore (upload de arquivo grande,
conexão ruim), o botão muda de aparência imediatamente — fica visivelmente diferente do
estado normal — e continua assim até a resposta do servidor chegar. O usuário nunca fica
na dúvida se o clique "pegou" ou não.

**Why this priority**: é o problema relatado e o requisito central do pedido — sem isso,
o incidente de gastos extras (e qualquer outro parecido) se repete em qualquer tela.

**Independent Test**: em qualquer tela interna do painel com um formulário de ação (ex.:
"Registrar gasto", "Aprovar", "Salvar"), clicar no botão e observar visualmente uma
mudança perceptível (opacidade, cursor ou texto) que persiste enquanto a resposta não
chega — sem precisar de código adicionado especificamente àquela tela.

**Acceptance Scenarios**:

1. **Given** uma tela interna do painel com um formulário comum (`<form>`), **When** o
   usuário clica no botão de envio, **Then** o botão muda de aparência de forma
   perceptível (não só o atributo técnico `disabled`, sem nenhum efeito visual) até a
   página trocar ou a resposta chegar.
2. **Given** um envio que está demorando (ex.: upload de arquivo em conexão lenta),
   **When** o usuário observa o botão, **Then** ele continua visivelmente no estado de
   "processando" — nunca volta a parecer clicável nem parece "travado sem explicação".
3. **Given** um clique que a validação do próprio formulário bloqueia (ex.: um `confirm()`
   de exclusão que o usuário cancela, ou um campo obrigatório vazio), **When** o envio é
   cancelado antes de sair do navegador, **Then** o botão NÃO fica preso no estado de
   carregamento — volta ao normal e pode ser clicado de novo.
4. **Given** um usuário volta para a tela pelo botão "voltar" do navegador logo depois de
   um envio, **When** a página é restaurada do cache do navegador, **Then** o botão não
   aparece preso no estado de carregamento de uma tentativa anterior.

---

### User Story 2 - Regra permanente para telas novas (Priority: P2)

Um desenvolvedor (ou o próprio Claude Code) cria uma tela nova com um botão de ação. Sem
precisar lembrar de adicionar código específico de "loading" naquela tela, o botão já
nasce com o comportamento correto, porque a proteção é automática para qualquer
formulário comum. Se a ação for disparada de um jeito que o mecanismo automático não
cobre (JavaScript puro, fora de um `<form>`), a exigência de feedback visível continua
valendo — só que precisa ser feita à mão naquele caso específico.

**Why this priority**: garante que o problema não volte a acontecer em telas futuras, que
é o pedido explícito de virar "regra" e não só uma correção local.

**Independent Test**: revisar o checklist de qualidade do projeto e confirmar que existe
um item explícito cobrando essa checagem antes de qualquer tela ser declarada pronta.

**Acceptance Scenarios**:

1. **Given** uma tela nova criada com um `<form>` comum e um botão de ação, **When** a
   tela é testada, **Then** o feedback visual já funciona sem nenhum código adicional
   específico daquela tela.
2. **Given** uma ação disparada por JavaScript puro (não um envio de formulário comum),
   **When** o checklist de qualidade é conferido antes de declarar a tela pronta, **Then**
   existe um item explícito lembrando que o feedback visual, nesse caso, precisa ser
   implementado manualmente.

### Edge Cases

- Botão com ícone (sem texto, ou texto + ícone): a mudança visual não pode depender de
  substituir o conteúdo do botão de um jeito que apague o ícone.
- Formulário com mais de um botão de ação (ex.: "Aprovar" e "Rejeitar" como formulários
  separados na mesma linha de uma tabela): só o botão realmente clicado deve mostrar o
  estado de carregamento de forma consistente — os demais continuam normais até a página
  recarregar.
- Envio cancelado antes de sair do navegador (validação nativa do campo, `confirm()`
  negado, JavaScript que impede o envio): o botão nunca deve ficar preso no estado de
  carregamento.
- Navegação "para trás" do navegador restaurando uma versão antiga da página (comum no
  Safari/iOS, o navegador do incidente relatado): o botão não pode aparecer travado.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A constituição do projeto DEVE declarar como regra permanente e
  não-negociável que todo botão de ação muda de aparência de forma visivelmente
  perceptível ao ser clicado — desabilitar o botão sem nenhuma mudança visual não conta
  como cumprir a regra.
- **FR-002**: Qualquer formulário comum (`<form>`) de qualquer tela do painel interno DEVE
  ganhar esse feedback visual automaticamente, sem exigir código específico daquela tela.
- **FR-003**: O feedback visual DEVE incluir, no mínimo, uma mudança perceptível de
  aparência (ex.: opacidade reduzida e cursor de carregamento) que dure enquanto a
  resposta não chega.
- **FR-004**: Se o próprio envio for cancelado antes de sair do navegador (validação,
  confirmação negada, JavaScript que impede o envio), o botão NÃO PODE ficar preso no
  estado de carregamento.
- **FR-005**: Ao restaurar uma página pelo cache do navegador (navegação "para trás"), o
  sistema DEVE garantir que nenhum botão apareça preso num estado de carregamento de uma
  tentativa anterior.
- **FR-006**: O checklist de qualidade do projeto (usado antes de declarar qualquer tarefa
  "pronta") DEVE incluir um item explícito cobrando essa checagem — cobertura automática
  para formulários comuns, implementação manual para ações disparadas por JavaScript puro.
- **FR-007**: A correção NÃO PODE alterar o comportamento hoje correto dos formulários
  públicos de pré-contrato (feature 118/123), que já mostram "Enviando…" corretamente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em qualquer tela interna testada com um formulário comum, o botão de ação
  mostra uma mudança visual perceptível dentro de instantes do clique, sem exigir nenhum
  código adicionado especificamente àquela tela.
- **SC-002**: 100% dos formulários internos testados (incluindo o de gastos extras que
  originou o pedido) mostram esse comportamento após a correção.
- **SC-003**: Um envio cancelado pela própria validação do formulário nunca deixa o botão
  preso — pode ser clicado novamente de imediato.
- **SC-004**: A constituição do projeto passa a exigir essa checagem de forma explícita e
  verificável para qualquer tela nova ou tocada.

## Assumptions

- O mecanismo automático cobre apenas envios de `<form>` HTML comuns (a grande maioria das
  telas internas do painel). Ações disparadas por JavaScript puro (`fetch` fora de um
  formulário, botões `onclick` sem `<form>`) não são cobertas automaticamente — continuam
  exigindo feedback visual implementado à mão naquela tela específica; isso fica
  registrado como responsabilidade do checklist de qualidade (FR-006), não resolvido
  automaticamente nesta feature.
- Os formulários públicos de pré-contrato (feature 118/123) já implementam esse
  comportamento corretamente de forma independente e não são alterados por esta feature
  (FR-007) — o problema identificado é específico do painel interno.
- Uma auditoria exaustiva de todo botão `onclick`/JavaScript puro do sistema fica fora do
  escopo desta feature — o foco é corrigir o mecanismo automático (que cobre a maioria dos
  casos, incluindo o incidente relatado) e deixar a regra registrada para o restante.
