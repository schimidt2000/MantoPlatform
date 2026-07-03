# Feature Specification: Constituição Robusta + Auditoria Geral do Sistema

**Feature Branch**: `107-constituicao-auditoria-sistema`

**Created**: 2026-07-03

**Status**: Draft

**Input**: User description: "Primeiro preciso que revise os arquivos de constituição que são base para o spec driven development. Verifique se está tudo ok e faça as alterações necessárias para que fique mais robusto. Gostaria que você revisasse o sistema como um todo. Já que agora estamos usando o Fable, um modelo mais avançado, quero que percorra o sistema e busque por melhorias tanto front como backend. Questões de usabilidade, UX e tudo mais."

## Contexto e delimitação de escopo

Pedido em duas frentes:

1. **Constituição** (`.specify/memory/constitution.md` + documentos de governança): revisar e
   robustecer com base nas lições das features recentes (092–106) — ex.: o portão de testes
   cita uma suíte pytest que não existe no projeto (a prática real é verificação funcional
   automatizada contra a cópia local do banco), e ferramentas citadas nos portões não estão
   instaladas, tornando alguns portões letra morta.
2. **Auditoria geral com melhorias**: percorrer o sistema (front e backend) atrás de
   problemas de usabilidade, consistência e qualidade. Como "melhorar tudo" não é entregável
   nem verificável, o escopo é: **(a)** auditoria sistemática com achados priorizados e
   registrados; **(b)** implementação imediata das correções de alto impacto e baixo risco
   (violações das próprias regras da constituição: formato monetário, erros engolidos,
   feedback de UI, proteção contra duplo envio, `alert()` genérico); **(c)** o que exigir
   decisão de produto ou refatoração grande vira **backlog documentado e priorizado** para
   futuras features — não é implementado às cegas.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Constituição que reflete a prática real (Priority: P1)

O time (e o próprio agente de desenvolvimento) usa a constituição como contrato de qualidade.
Após a revisão, todos os portões são executáveis de verdade no projeto: a regra de verificação
descreve o processo que funciona (verificação automatizada contra a cópia local do banco de
produção), as ferramentas exigidas existem no ambiente, e as lições operacionais aprendidas
(migrations manuais, superfícies públicas mobile-first, validação com feedback no campo)
estão codificadas como princípios — para que as próximas features já nasçam cumprindo.

**Why this priority**: a constituição rege TODAS as features seguintes; portões inexequíveis
viram teatro de qualidade e regras não escritas se perdem entre sessões.

**Independent Test**: ler a constituição atualizada e executar cada portão listado no projeto
real — todos devem ser executáveis e verificáveis; o changelog registra o que mudou e por quê.

**Acceptance Scenarios**:

1. **Given** a constituição atualizada, **When** um desenvolvedor executa cada comando/portão
   citado, **Then** todos funcionam no ambiente do projeto (nenhum cita ferramenta ausente ou
   suíte inexistente).
2. **Given** as lições operacionais das features 088–106, **When** a constituição é lida,
   **Then** cobre: verificação funcional obrigatória por feature, migrations escritas à mão,
   mobile-first para superfícies públicas, feedback de validação no campo e formato monetário
   BR como já constava.
3. **Given** a mudança, **Then** a versão sobe com changelog datado explicando cada alteração.

---

### User Story 2 - Auditoria sistemática com achados priorizados (Priority: P1)

O dono do sistema recebe um relatório de auditoria do sistema inteiro (módulos internos:
agenda, talentos, financeiro, admin, figurino, ferramentas; e superfícies públicas já
revisadas nas features 104–106), com cada achado classificado por severidade (crítico / alto /
médio / baixo), área (UX, consistência, robustez, desempenho, segurança) e esforço, indicando
o que foi corrigido nesta feature e o que fica como backlog priorizado.

**Why this priority**: é o mapa que transforma "melhore tudo" em trabalho verificável agora e
backlog acionável depois.

**Independent Test**: o relatório existe, cobre todos os módulos, cada achado tem severidade/
área/esforço/status (corrigido nesta feature | backlog), e os achados "corrigido" apontam a
mudança correspondente.

**Acceptance Scenarios**:

1. **Given** o relatório, **When** lido, **Then** cada módulo do sistema aparece com seus
   achados (ou registro explícito de "sem achados relevantes").
2. **Given** um achado marcado como corrigido, **Then** existe mudança correspondente nesta
   feature que o resolve.
3. **Given** um achado de backlog, **Then** tem severidade, esforço estimado e recomendação
   clara — pronto para virar uma futura feature.

---

### User Story 3 - Correções de alto impacto aplicadas (Priority: P2)

Os usuários internos percebem o sistema mais consistente e confiável: valores monetários
sempre no padrão brasileiro em todas as telas, ações lentas nunca criam registros duplicados
por duplo clique, erros não são engolidos silenciosamente (ficam registrados em log), avisos
ao usuário aparecem de forma amigável (sem `alert()` genérico em fluxos principais), e ações
destrutivas sempre pedem confirmação — em TODOS os módulos, não só nos recém-reformados.

**Why this priority**: são as violações objetivas das regras já acordadas — corrigi-las tem
alto valor e risco controlado; depende do mapa da US2.

**Independent Test**: varredura automatizada + inspeção confirmam: zero formatação monetária
fora do padrão BR nas telas, zero `except` silencioso no código da aplicação, botões de ações
lentas com proteção contra duplo envio nos fluxos principais, confirmação em toda ação
destrutiva encontrada pela auditoria.

**Acceptance Scenarios**:

1. **Given** qualquer tela com valores monetários, **Then** exibe padrão brasileiro
   (milhar com ponto, decimal com vírgula) — confirmado por varredura nas telas e templates.
2. **Given** um erro interno em fluxo auditado, **When** ocorre, **Then** é registrado em log
   (nenhum `except` que engole erro sem registrar no código da aplicação).
3. **Given** os formulários de ação lenta identificados pela auditoria, **When** o usuário
   clica duas vezes, **Then** apenas um registro/ação é criado (botão desabilita).
4. **Given** ações destrutivas encontradas na auditoria, **Then** todas pedem confirmação.
5. **Given** as correções aplicadas, **Then** os fluxos existentes continuam funcionando
   (verificação de regressão nas telas tocadas).

---

### Edge Cases

- Achado crítico que exige decisão de produto (ex.: mudança de fluxo de negócio): NÃO é
  corrigido nesta feature — entra no backlog com destaque, para decisão do dono.
- Correção mecânica que tocaria código compartilhado sensível (ex.: sync de eventos): só é
  aplicada com verificação de regressão específica; na dúvida, vira backlog.
- Telas legadas com muitos problemas acumulados: a auditoria registra tudo, mas a correção
  se limita às classes de problema da US3 (sem redesenho).
- Constituição: regras novas NÃO invalidam código existente retroativamente — valem para
  código novo/tocado (dívida pré-existente vai para o backlog).

## Requirements *(mandatory)*

### Functional Requirements

**Constituição (US1)**

- **FR-001**: A constituição DEVE ter todos os portões de qualidade executáveis no ambiente
  real do projeto (nenhuma referência a ferramenta/suíte inexistente).
- **FR-002**: A constituição DEVE incorporar as práticas operacionais consolidadas:
  verificação funcional automatizada por feature contra a cópia local do banco de produção,
  migrations escritas manualmente, mobile-first para superfícies públicas, validação de
  formulário com feedback visível no campo.
- **FR-003**: A revisão DEVE preservar os princípios existentes que funcionam (reutilização,
  camadas, feedback de UI, moeda BR, segredos) — mudanças são aditivas/corretivas, com
  changelog e versão incrementada.
- **FR-004**: Os documentos de apoio (CLAUDE.md) DEVEM ficar coerentes com a constituição
  revisada (sem instruções contraditórias).

**Auditoria (US2)**

- **FR-005**: A auditoria DEVE cobrir todos os módulos do sistema (agenda/eventos, talentos,
  financeiro, vendas, admin, figurino, ferramentas, clientes, revisão, portal, cadastro,
  autenticação) nas dimensões: UX/usabilidade, consistência visual, robustez de erros,
  proteção de formulários, formato monetário, e riscos evidentes de segurança/desempenho.
- **FR-006**: Cada achado DEVE ser registrado com: módulo, descrição, severidade
  (crítico/alto/médio/baixo), esforço (baixo/médio/alto) e status (corrigido | backlog).
- **FR-007**: O relatório DEVE viver no repositório, em local reencontrável
  (documentação da feature), com resumo executivo dos números.

**Correções (US3)**

- **FR-008**: Toda formatação monetária fora do padrão BR encontrada em telas DEVE ser
  corrigida usando a fonte única de formatação existente.
- **FR-009**: Todo `except` que engole erro sem registro no código da aplicação DEVE passar a
  registrar em log (sem mudar o comportamento de recuperação).
- **FR-010**: Formulários de ações lentas dos fluxos principais identificados sem proteção
  contra duplo envio DEVEM ganhar a proteção padrão (botão desabilita + estado de envio).
- **FR-011**: Ações destrutivas sem confirmação encontradas DEVEM ganhar confirmação.
- **FR-012**: Usos de `alert()`/`confirm()` genéricos em fluxos principais internos podem
  permanecer para confirmação simples, mas avisos de erro/validação em fluxos principais
  DEVEM usar feedback visível na página (padrão da constituição).
- **FR-013**: Nenhuma correção PODE alterar regra de negócio, fluxo ou dados — apenas
  apresentação, robustez e proteção; comportamento verificado após cada classe de correção.

### Key Entities

Sem entidades novas — mudanças em documentos de governança, templates e tratamento de erros;
nenhum dado persistido muda.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos portões da constituição revisada são executáveis no projeto real.
- **SC-002**: Relatório de auditoria cobre 12/12 módulos com achados classificados; resumo
  executivo com contagem por severidade e status.
- **SC-003**: Zero ocorrências de formatação monetária fora do padrão BR em templates após a
  feature (varredura automatizada).
- **SC-004**: Zero `except` silencioso (sem log) no código da aplicação após a feature
  (varredura automatizada).
- **SC-005**: 100% dos formulários de ação lenta dos fluxos principais auditados com proteção
  contra duplo envio.
- **SC-006**: Zero regressões nos fluxos tocados (verificação automatizada de renderização +
  fluxos principais contra a cópia local do banco).

## Assumptions

- "Sistema como um todo" = auditoria de TODOS os módulos, mas implementação restrita a
  correções objetivas de baixo risco (classes listadas na US3); melhorias que mudam fluxo,
  visual ou arquitetura viram backlog priorizado para decisão do dono.
- A revisão da constituição é técnica/operacional — não muda decisões de produto nem
  princípios de negócio já ratificados.
- O relatório de auditoria vive em `specs/107-.../` (documentação da feature) e o backlog
  em arquivo próprio referenciado pela memória do projeto.
- Melhorias de desempenho profundas (queries, índices) e redesigns são explicitamente fora
  do escopo de implementação desta feature (entram no backlog se encontrados).
