# Quickstart: Verificação Manual — Agrupamento de Eventos por Contrato

**Feature**: 053-agrupar-eventos | **Date**: 2026-06-16

Não há suite de testes automatizada no projeto — verificação manual pelo
roteiro abaixo, espelhando as Acceptance Scenarios da spec.

## Pré-requisito

- Rodar localmente: `python run.py`, logado como usuário COMERCIAL ou
  SUPERADMIN.
- Ter (ou criar) 2 eventos de teste na mesma data, com elencos diferentes.

## Roteiro

1. **Agrupar dois eventos independentes** (US1)
   - Abrir o evento A, escolher "Agrupar a outro evento", selecionar o
     evento B, escolher A como principal.
   - Confirmar: sistema pede confirmação se B tinha venda preenchida.
   - Esperado: B passa a exibir banner "faz parte do grupo de A".

2. **Bloqueios de validação** (Edge Cases)
   - Tentar agrupar A a ele mesmo → bloqueado.
   - Tentar agrupar um evento ENSAIO → bloqueado.
   - Tentar agrupar B (já satélite) a um terceiro evento C → bloqueado,
     orientado a desagrupar primeiro.

3. **Financeiro trata grupo como 1 venda** (US2)
   - Preencher venda de R$ 5.000 em A (principal), cachês de R$ 800 em B
     (satélite).
   - Abrir `/financeiro/` no período correspondente.
   - Esperado: receita bruta R$ 5.000 contada uma vez; CPV do grupo inclui os
     R$ 800 de B; contagem de "eventos vendidos" = 1, não 2.
   - Abrir o alerta de "eventos sem valor de venda" (feature 051) — B não
     deve aparecer na lista.

4. **Visualizar e desfazer** (US3)
   - Abrir A → ver B listado como satélite, com link.
   - Abrir B → ver banner com link para A, campos comerciais somente leitura.
   - Desfazer o agrupamento de B → B volta a ter campos comerciais próprios
     (zerados, editáveis); elenco/personagens/figurino de B permanecem
     intactos.

5. **Não-regressão: casting/figurino/sync** (US4)
   - Rodar a sincronização do Google Calendar com o grupo já criado →
     vínculo entre A e B permanece após o sync.
   - Abrir telas de casting e figurino → A e B continuam aparecendo
     separadamente, cada um com suas próprias tarefas.

6. **Exclusão bloqueada** (FR-009)
   - Tentar excluir A enquanto B ainda é satélite → bloqueado, com mensagem
     orientando a desagrupar antes.

## Critério de aceite

Todos os 6 passos acima devem se comportar exatamente como descrito, sem
exceções/erros 500, e sem qualquer alteração visível em eventos não
relacionados ao teste.
