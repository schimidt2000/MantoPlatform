# Checklist: quem lê o quê, e o deploy — Feature 315

**Purpose**: testar a qualidade dos requisitos de leitura (o corte da Q6 e da premissa 5 em cada superfície), da faixa,
do selo e da herança do satélite, do portal, do deploy cruzado, da migration e do rollback, e do pedido real do 1350.
**Created**: 2026-10-22 · **Público**: autor e revisor, antes do `/speckit-tasks`
**Fontes**: `spec.md`, `research.md`, `data-model.md`, `contracts/api.md`, `plan.md`

## O corte por papel

- [x] CHK001 A matriz "quem lê o quê" cobre todas as superfícies — detalhe, fila, faixa, sino, resumo da agenda, portal e
  histórico do evento? [Gap → corrigido (histórico do evento), data-model "Leitura da devolução"]
- [x] CHK002 Está consistente que a leitura segue o papel **em uso** ("Ver como") e a escrita o papel **real**? [Consistency,
  Spec §FR-010/FR-017, data-model]
- [x] CHK003 A regra do autor para nome e PIX é inequívoca (pelo id do usuário)? [Clarity, data-model]
- [x] CHK004 Está escrito que o corte é no servidor e que a tela só reage à ausência dos campos? [Clarity, Spec §FR-010,
  research R8]
- [x] CHK005 A fila "Cancelamentos" tem o mesmo corte do detalhe, inclusive no "Ver como"? [Consistency, Spec §FR-010,
  contracts]
- [x] CHK006 O texto do sino e da faixa estão definidos sem nome e PIX (e a faixa sem motivo nem autor)? [Completeness,
  Spec §FR-008/FR-012]

## Faixa, selo e herança

- [x] CHK007 As frases da faixa para 1 e N pedidos, o link (evento × lista) e a forma curta no celular estão definidos?
  [Clarity, Spec §FR-012, research R7]
- [x] CHK008 Está escrito que `total` da faixa continua só do sumiço e que a altura não muda? [Consistency, research R7,
  contracts]
- [x] CHK009 A acessibilidade das duas frases (cada uma com o seu botão e a sua lista; teclado) está especificada?
  [Gap → corrigido, research R7]
- [x] CHK010 O evento marcado **e** com pedido (o 1350) tem comportamento definido na faixa, na tela, no selo e no
  portal? [Gap → corrigido, Spec "Casos de borda"]
- [x] CHK011 As superfícies onde o satélite herda o pedido de "todos os dias" estão definidas, e consistentes entre a spec
  e a pesquisa? [Conflict → corrigido, Spec premissa 9, research R6]
- [x] CHK012 A restrição de não haver uma consulta por linha a mais é mensurável? [Measurability, plan "Metas de
  desempenho", research R6]

## Portal

- [x] CHK013 As três telas do portal, o evento passado e o satélite estão cobertos pelo "Evento em confirmação"? [Coverage,
  Spec §FR-014/FR-015, contracts]
- [x] CHK014 Está escrito que o portal nunca recebe motivo nem autor? [Completeness, Spec §FR-014]

## Deploy cruzado, migration e rollback

- [x] CHK015 Os dois sentidos do deploy cruzado (tela velha × servidor novo; tela nova × servidor velho) estão
  especificados? [Coverage, Spec "Casos de borda", research R9]
- [x] CHK016 O alias aceita o corpo velho só pelo caminho velho, e a remoção fica registrada? [Clarity, Spec §FR-025,
  research R9]
- [x] CHK017 As chaves novas das respostas são opcionais para a tela, com o comportamento de ausência definido?
  [Completeness, contracts, plan "Restrições"]
- [x] CHK018 A migration é aditiva, com `down_revision` certo, e o que o `downgrade` perde está escrito? [Completeness,
  data-model, plan "Deploy e rollback"]
- [x] CHK019 O rollback descreve o que acontece com os pedidos feitos no meio-tempo? [Coverage, plan "Deploy e rollback"]
- [x] CHK020 A sonda do deploy prova o backend novo (não só um 200)? [Measurability, plan "Deploy e rollback"]

## O pedido real

- [x] CHK021 O comportamento do pedido do 1350 depois do deploy (faixa, fila, selo, sem aviso retroativo) está definido e
  é verificável? [Completeness, Spec §FR-026, SC-006, cenário 25]
- [x] CHK022 A conferência de tela inclui o diálogo de pedir no celular (o Comercial pede pelo telefone)? [Gap →
  corrigido, quickstart §3]

## Notes

- 22 itens; 5 lacunas achadas e corrigidas nos documentos (CHK001, CHK009, CHK010, CHK011, CHK022). Nenhuma decisão de
  negócio nova.
