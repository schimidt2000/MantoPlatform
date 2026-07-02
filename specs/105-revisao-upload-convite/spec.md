# Feature Specification: Revisão — Progresso de Upload, Convite aos Revisores e Fix do Popup

**Feature Branch**: `105-revisao-upload-convite`

**Created**: 2026-07-02

**Status**: Draft

**Input**: User description: "Na tela onde crio o espaço de revisão gostaria de uma tela de carregamento que mostre de fato quanto está subindo do vídeo. Após criar, tem que ter algum botão para a editoria copiar para enviar aos revisores que terão acesso a esse vídeo. Após criar o espaço de revisão e entrar nele está bugado com o popup de histórico de versões que não fecha."

## Contexto

Feature incremental sobre o módulo de revisão (088/090/104). Três entregas na mesma área:

1. **Bug (introduzido na 104)**: na tela do material, o popup de histórico de versões aparece
   aberto ao carregar a página e não fecha — a regra visual do popup sobrepõe o estado
   "escondido", deixando a tela inutilizável até recarregar. Precisa ser corrigido.
2. **Progresso real de upload**: hoje, ao criar um espaço com vídeos grandes (até 512 MB), o
   botão vira "Enviando…" sem nenhuma indicação de progresso — a editoria não sabe se está
   subindo, travou ou quanto falta. Precisa de uma barra de progresso real (% enviado).
3. **Convite copiável**: após criar o espaço, a editoria precisa avisar os revisores
   manualmente (WhatsApp). Falta um botão que copie uma mensagem pronta com o link do espaço.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Popup de histórico não bloqueia mais a tela (Priority: P1)

Um usuário abre qualquer material de revisão. A tela carrega limpa (sem popup sobreposto). O
popup de histórico de versões só aparece quando ele toca no badge de versão, e fecha ao tocar
no ✕ ou fora do popup.

**Why this priority**: é um bug que deixa a tela do material inutilizável (o overlay cobre o
conteúdo e não fecha) — bloqueia o uso diário do módulo recém-entregue.

**Independent Test**: abrir um material qualquer → nenhum popup visível; abrir o histórico
pelo badge → popup aparece; fechar pelo ✕ e clicando fora → popup some nas duas formas.

**Acceptance Scenarios**:

1. **Given** um material de revisão, **When** a página carrega, **Then** o popup de histórico
   NÃO está visível.
2. **Given** a tela carregada, **When** o usuário toca no badge de versão, **Then** o popup
   abre; **When** toca no ✕ ou fora do cartão, **Then** o popup fecha.
3. **Given** o popup aberto e fechado repetidas vezes, **Then** o comportamento se mantém
   consistente (sem estado travado).

---

### User Story 2 - Progresso real do upload na criação do espaço (Priority: P2)

A editoria cria um espaço com um vídeo de 300 MB. Ao clicar em "Criar espaço", aparece uma
barra de progresso mostrando a porcentagem real já enviada (e o total, ex.: "45% — 135 MB de
300 MB"). O formulário fica bloqueado durante o envio. Se a conexão falhar, uma mensagem
amigável aparece e o formulário volta a ficar editável (sem perder o que foi preenchido). Ao
concluir, segue para a tela do espaço criado.

**Why this priority**: uploads grandes sem feedback geram dúvida ("travou?"), abas fechadas no
meio do envio e envios duplicados. É o cenário mais frequente da editoria (vídeos pesados).

**Independent Test**: criar um espaço com arquivo grande e observar a barra progredir de 0 a
100% com números reais; simular falha de rede e ver a mensagem de erro com formulário
preservado.

**Acceptance Scenarios**:

1. **Given** o formulário de novo espaço com arquivos selecionados, **When** a editoria clica
   em "Criar espaço", **Then** uma barra de progresso exibe a porcentagem real enviada e a
   quantidade (MB enviados / total), atualizando conforme o upload avança.
2. **Given** um envio em andamento, **When** o upload está acontecendo, **Then** o botão de
   criar está desabilitado (sem duplo envio) e os campos não são editáveis.
3. **Given** uma falha de conexão no meio do envio, **When** o upload aborta, **Then** aparece
   mensagem de erro amigável e o formulário volta a ficar editável com todos os dados
   preenchidos preservados.
4. **Given** o envio concluído com sucesso, **Then** a editoria é levada para a tela do espaço
   criado (comportamento atual preservado, incluindo avisos de arquivos rejeitados).
5. **Given** o envio de nova versão de um material (tela do material), **When** o arquivo é
   grande, **Then** o mesmo indicador de progresso é exibido.

---

### User Story 3 - Copiar convite para os revisores (Priority: P3)

Logo após criar o espaço (e também depois, na tela do espaço), a editoria vê um botão
"Copiar convite". Ao tocar, uma mensagem pronta é copiada para a área de transferência — com o
título do espaço e o link direto — pronta para colar no WhatsApp dos revisores selecionados. Um
feedback visual confirma que foi copiado.

**Why this priority**: elimina a etapa manual de montar a mensagem/link, mas o fluxo funciona
sem ele (dá para copiar a URL do navegador).

**Independent Test**: criar um espaço, tocar em "Copiar convite" e colar em qualquer campo —
conferir mensagem com título e link corretos; testar também pela tela do espaço.

**Acceptance Scenarios**:

1. **Given** um espaço recém-criado, **When** a editoria entra na tela do espaço, **Then** há
   um botão "Copiar convite" visível e um destaque pós-criação convidando a compartilhar.
2. **Given** o botão tocado, **Then** a área de transferência recebe uma mensagem em pt-BR com
   o título do espaço e o link direto para ele, e o botão exibe confirmação visual
   ("Copiado ✓") por alguns segundos.
3. **Given** um navegador que bloqueie a cópia automática, **Then** a mensagem é exibida em um
   campo selecionável para cópia manual.
4. **Given** um revisor que recebeu o link, **When** ele acessa logado, **Then** cai
   diretamente no espaço (acesso segue as permissões existentes — revisor selecionado, criador
   ou super admin).

---

### Edge Cases

- Criação de espaço **sem arquivos** (só título): não mostra barra de progresso — envio segue
  direto (rápido) sem regressão.
- Arquivo rejeitado no servidor (tipo não suportado/tamanho): avisos atuais continuam
  aparecendo após o redirect.
- Upload lento com progresso parado: a barra mostra o último valor real (sem simular avanço);
  o usuário pode cancelar recarregando a página — nada é criado até o envio completar.
- Espaço sem revisores selecionados: o convite copia mesmo assim (a editoria pode adicionar
  revisores depois).
- Título com caracteres especiais/emoji: a mensagem copiada preserva o texto fielmente.
- Popup de histórico em material com 1 versão só: continua abrindo normalmente (lista com a
  versão atual e aviso de que não há anteriores).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O popup de histórico de versões DEVE iniciar fechado ao carregar a tela do
  material e DEVE fechar pelo botão ✕ e pelo clique fora do cartão, de forma consistente.
- **FR-002**: Na criação do espaço com arquivos, o envio DEVE exibir progresso real: barra
  visual + porcentagem + volume enviado/total (em MB), atualizados durante todo o upload.
- **FR-003**: Durante o envio, o formulário DEVE ficar bloqueado (botão desabilitado com
  estado de carregamento; campos não editáveis) — nenhum clique extra pode duplicar o espaço.
- **FR-004**: Em falha de envio (rede/servidor), o usuário DEVE ver mensagem de erro amigável
  e o formulário DEVE voltar editável com todos os valores preservados.
- **FR-005**: Ao concluir o envio, o fluxo atual DEVE ser preservado: redirecionamento para o
  espaço criado, mensagens de sucesso e avisos de arquivos rejeitados.
- **FR-006**: O envio de nova versão de um material DEVE exibir o mesmo indicador de progresso
  quando houver arquivo em envio.
- **FR-007**: A tela do espaço DEVE ter um botão "Copiar convite" que copia para a área de
  transferência uma mensagem em pt-BR contendo o título do espaço e o link direto.
- **FR-008**: Após copiar, o botão DEVE exibir confirmação visual temporária; se a cópia
  automática for bloqueada pelo navegador, a mensagem DEVE ser exibida para cópia manual.
- **FR-009**: Imediatamente após a criação, a tela do espaço DEVE destacar a ação de convite
  (a editoria acabou de criar e vai compartilhar — o botão precisa estar evidente).
- **FR-010**: O link do convite DEVE levar ao espaço respeitando as permissões existentes
  (login + revisor selecionado/criador/super admin) — nenhum acesso novo é criado.

### Key Entities

Sem entidades novas — a feature usa o `ReviewSpace` existente (título, link e revisores) e não
altera dados persistidos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em um upload de vídeo grande, o usuário vê o progresso real (％ e MB) do início
  ao fim — zero janelas de "tela parada sem feedback" maiores que 2 segundos.
- **SC-002**: Zero espaços duplicados por duplo clique/reenvio durante o upload.
- **SC-003**: Após uma falha de rede, 100% dos dados preenchidos permanecem no formulário.
- **SC-004**: A editoria copia o convite pronto em 1 toque e o cola com título e link corretos.
- **SC-005**: A tela do material carrega sem nenhum popup sobreposto em 100% dos acessos, e o
  histórico abre/fecha corretamente em todas as tentativas.

## Assumptions

- O convite é texto para colar no WhatsApp (fora do sistema) — não há envio automático de
  mensagem/e-mail nem notificação interna nesta feature.
- Revisores já são usuários do sistema com login; o link não cria acesso público (segue a
  regra de permissão existente do espaço).
- O progresso de upload cobre a tela de criação do espaço e o envio de nova versão do
  material; o formulário "Adicionar materiais" dentro do espaço também ganha o indicador por
  usar o mesmo padrão de envio.
- Não há retomada de upload interrompido (resume) nem cancelamento parcial — em falha, o
  usuário reenvia.
- Mensagem do convite (padrão): saudação curta + título do espaço + link + observação de que é
  preciso entrar com o login do sistema. Texto final pode ser ajustado depois sem nova spec.
