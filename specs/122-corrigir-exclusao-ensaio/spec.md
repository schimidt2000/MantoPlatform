# Feature Specification: Corrigir Erro 500 ao Excluir Ensaio

**Feature Branch**: `122-corrigir-exclusao-ensaio`

**Created**: 2026-07-09

**Status**: Draft

**Input**: Relato de bug: "Havia um ensaio órfão e ao clicar em cancelar ensaio, da primeira
vez apareceu a página de erro 500 no /events/411/delete-ensaio. Após tentar duas vezes,
realmente apagou, mas sempre apareceu a tela de erro."

## Contexto

O botão "Cancelar ensaio" deveria excluir o ensaio de forma limpa, mesmo em casos
anormais (ensaio sem show vinculado — "órfão" — ou cujo evento já não existe mais no
Google Agenda). Hoje, dois pontos do processo de exclusão não estão preparados para esses
casos e derrubam a requisição com uma tela de erro técnica (500) em vez de concluir a
exclusão com um aviso amigável:

1. A tentativa de remover o evento do Google Agenda só trata a falha "Google
   desconectado" — qualquer outra falha (o evento já ter sido removido de lá, por
   exemplo) sobe sem tratamento.
2. O ensaio é apagado do banco sem antes limpar registros associados que não têm limpeza
   automática (histórico de ações, contratos, comprovantes de pagamento, avaliações) — se
   existir algum, a exclusão é rejeitada pelo banco de dados.

Qualquer um dos dois já é suficiente para transformar um clique simples em uma tela de
erro — e o segundo garante falha toda vez que o ensaio tiver histórico de ações
registrado (comum, por exemplo, quando o ensaio foi vinculado a um show manualmente).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cancelar um ensaio sem tela de erro (Priority: P1)

Um usuário com permissão de ensaio clica em "Cancelar ensaio" numa página de ensaio —
inclusive um ensaio órfão (sem show vinculado) ou cujo evento já não existe mais no Google
Agenda. A exclusão é concluída e o usuário vê a página seguinte normalmente (a do show, ou
a home), nunca uma tela de erro técnica.

**Independent Test**: criar um ensaio com histórico de ações registrado (ex.: vinculá-lo a
um show, o que gera um registro de histórico) e cujo evento no Google já não existe mais;
clicar em "Cancelar ensaio"; conferir que a exclusão é concluída sem tela de erro.

**Acceptance Scenarios**:

1. **Given** um ensaio cujo evento já foi removido do Google Agenda por fora do sistema,
   **When** o usuário clica em "Cancelar ensaio", **Then** o ensaio é excluído do sistema,
   o usuário recebe um aviso amigável (não uma tela de erro) e é levado à página seguinte
   normalmente.
2. **Given** um ensaio com histórico de ações registrado (ex.: foi vinculado a um show,
   teve dados editados), **When** o usuário clica em "Cancelar ensaio", **Then** a
   exclusão é concluída de uma vez, sem precisar de uma segunda tentativa.
3. **Given** um ensaio órfão (sem show vinculado), **When** excluído, **Then** o
   comportamento é o mesmo de um ensaio vinculado — sem erro, com o mesmo aviso de
   sucesso.
4. **Given** qualquer falha ao tentar remover o evento do Google Agenda (não só "Google
   desconectado"), **Then** a exclusão no sistema prossegue normalmente e o usuário é
   avisado que o lado do Google pode precisar de atenção manual — nunca uma tela de erro
   bloqueando a ação.

## Requirements *(mandatory)*

- **FR-001**: A exclusão de um ensaio NUNCA PODE resultar numa tela de erro técnica
  (código 500) — qualquer falha no caminho deve terminar em aviso amigável e conclusão da
  ação sempre que possível.
- **FR-002**: Se a remoção do evento no Google Agenda falhar por qualquer motivo (não só
  "Google desconectado"), o sistema DEVE registrar o erro internamente para diagnóstico e
  seguir com a exclusão no banco de dados — o Google Agenda nunca pode travar a exclusão
  local.
- **FR-003**: A exclusão de um ensaio DEVE remover também os registros associados a ele
  que hoje impedem a exclusão quando existem (histórico de ações do evento, contratos,
  comprovantes de pagamento, avaliações) — mesma limpeza que a exclusão de um evento comum
  já faz corretamente.
- **FR-004**: O comportamento deve ser o mesmo independentemente de o ensaio estar
  vinculado a um show ou ser órfão.
- **FR-005**: Uma tentativa de exclusão bem-sucedida DEVE mostrar uma única mensagem clara
  de confirmação — sem exigir uma segunda tentativa para efetivamente concluir a ação.

## Success Criteria *(mandatory)*

- **SC-001**: 100% das exclusões de ensaio (órfão ou não, com ou sem falha do Google)
  terminam sem tela de erro técnica.
- **SC-002**: Um ensaio com histórico de ações é excluído na primeira tentativa.
- **SC-003**: Erros do Google Agenda durante a exclusão ficam registrados no log interno
  para diagnóstico futuro, mesmo quando não impedem mais a ação do usuário.

## Assumptions

- O comportamento correto quando o Google Agenda falha é o mesmo já adotado em outras
  telas do sistema (ex.: criação de evento): a operação local prossegue, o usuário recebe
  um aviso amigável, e o erro técnico vai para o log — nunca para a tela do usuário.
- Esta correção cobre apenas o processo de **excluir** um ensaio (o que foi relatado). Um
  problema semelhante existe na tela de **editar** um ensaio (mesmo tipo de tratamento
  incompleto do erro do Google) — fica fora deste escopo, registrado como recomendação de
  acompanhamento.
