# Checklist: o pedido e a decisão — Feature 315

**Purpose**: testar a qualidade dos requisitos do ciclo do pedido (pedir, recusar, cancelar, excluir, devolver ao
Google), de quem fecha, da resposta ao autor, da venda de vários dias, das recusas, da devolução combinada e da
concorrência.
**Created**: 2026-10-22 · **Público**: autor e revisor, antes do `/speckit-tasks`
**Fontes**: `spec.md`, `research.md` (R1–R12), `data-model.md`, `contracts/api.md`

## Ciclo e saídas

- [x] CHK001 Todas as saídas de um pedido pendente (recusar, cancelar, excluir) estão especificadas, com o que acontece
  ao pedido, ao aviso dos Superadmins e à resposta ao autor? [Completeness, Spec §FR-017–FR-021, data-model "Ciclo"]
- [x] CHK002 Está escrito que "Devolver ao Google" não decide o pedido, e o que o Superadmin faz depois? [Coverage,
  Spec §FR-006, premissa 1]
- [x] CHK003 Está claro que só o Superadmin fecha, pelo papel **real** (inclusive em "Ver como Comercial"), e que o
  autor e os outros Comerciais recebem recusa? [Clarity, Spec §FR-017, RBAC, cenário 19]
- [x] CHK004 A ausência de desistência (Q5 = D) é um requisito verificável, e não só a falta de um botão? [Measurability,
  cenário 26]
- [x] CHK005 O texto de cada resposta (recusado com motivo, cancelado, um dia, passagem do 1º dia, excluído) está
  definido? [Clarity, Spec História 3 AC1/AC4/AC6, research R2]
- [x] CHK006 A resposta ao autor é "uma por pedido", e não uma por dia cancelado, nas vendas de vários dias? [Consistency,
  Spec §FR-019, História 3 AC5]
- [x] CHK007 O que acontece com um pedido quando o cancelamento chega por outro caminho que não o "Analisar e decidir"?
  [Edge Case, Spec "Casos de borda", research R2]
- [x] CHK008 A exclusão de evento vazio com pedido está especificada (resposta sem link; falha no aviso não desfaz a
  exclusão; Jinja e sync sem resposta)? [Completeness, Spec §FR-020, research R10]

## Venda de vários dias

- [x] CHK009 O vocabulário do alcance é o mesmo na spec, na pesquisa, no modelo e no contrato (todos / só este dia)?
  [Consistency, research R3, data-model, contracts]
- [x] CHK010 Está escrito que o alcance é gravado e não muda quando o 1º dia muda? [Clarity, Spec §FR-004]
- [x] CHK011 O fecho por dia (corte, passagem, todos) e o que fica pendente nos outros dias estão definidos? [Coverage,
  Spec §FR-019, "Casos de borda", research R2]
- [x] CHK012 O pedido de antes do deploy (alcance nulo) tem leitura definida para mostrar e para fechar? [Edge Case,
  research R3, R6, Spec §FR-026]

## Recusas na porta

- [x] CHK013 As quatro recusas (cancelado, ensaio, cachê pago, pedido pendente) têm código, frase e ordem consistentes
  entre a spec, o RBAC e o contrato? [Consistency, Spec §FR-005, RBAC, contracts]
- [x] CHK014 O alcance da régua do cachê pago (todos os dias que o pedido alcança × só o próprio dia) está definido?
  [Clarity, Spec §FR-005]
- [x] CHK015 Está definido como a tela antecipa as recusas de ensaio e cachê pago (item desabilitado com a frase do
  servidor) sem decidir sozinha? [Completeness, Spec §FR-005, contracts `pedido_bloqueado`]

## Devolução combinada

- [x] CHK016 A forma da devolução está definida para cada caso — evento simples, um dia só, passagem, venda virtual — e
  igual à do cancelar da 306? [Completeness, Spec §FR-003, research R4]
- [x] CHK017 Está escrito o que "Nada" grava (sem nome nem PIX) e que o pedido não tem observação própria? [Gap →
  corrigido, research R4, data-model]
- [x] CHK018 Está explícito que o pedido confere a forma e não o dinheiro (máximo, mínimo, "nada pago"), e quem confere o
  dinheiro? [Clarity, premissa 4, research R4]

## Concorrência e casos de pessoa

- [x] CHK019 Os pares concorrentes (pedir × pedir, recusar × recusar, recusar × cancelar, pedir × cancelar) têm um
  vencedor definido e nenhum aviso ou resposta em dobro? [Coverage, Spec §FR-022, research R5]
- [x] CHK020 Autor sem acesso, autor apagado e "quem decide é o autor" estão especificados? [Edge Case, Spec §FR-023,
  "Casos de borda"]
- [x] CHK021 O Superadmin que pede recebe o aviso do próprio pedido, e isso está escrito? [Clarity, premissa 8]
- [x] CHK022 A urgência do aviso está definida também para evento que já passou? [Gap → corrigido, Spec §FR-008,
  data-model, research R11]

## Notes

- 22 itens; 2 lacunas achadas e corrigidas nos documentos (CHK017, CHK022). Nenhuma decisão de negócio nova.
