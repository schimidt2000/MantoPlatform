# Checklist de requisitos — regras, RBAC, deploy e texto (Feature 322)

**Purpose**: testar se a spec escreve com clareza e completude as regras de maior risco (trava de
maquiagem, maquiador em todos os caminhos, marcas de origem, convivência bundle × servidor, texto).
**Created**: 2026-10-28 · **Audiência**: revisão antes do `/speckit-tasks` · **Profundidade**: padrão

## RBAC da trava de maquiagem

- [x] CHK001 - A spec diz quem pode mudar a maquiagem depois que o evento existe, e por qual caminho (edição × vínculo)? [Completeness, Spec §FR-012, §FR-013]
- [x] CHK002 - Está definido o que o servidor faz com a mudança recusada (ignora em silêncio × erro)? [Clarity, Contrato §PATCH] — ignora, sem erro; a tela já trava
- [x] CHK003 - O texto da explicação da caixa travada está escrito, e não só "com a explicação"? [Clarity, Spec §FR-012] — resolvido: texto fixado na FR-012
- [x] CHK004 - A spec cobre o personagem NOVO acrescentado na edição, não só o existente? [Coverage, Clarifications]
- [x] CHK005 - Há um cenário de verify que DEVE falhar no código antigo para a trava? [Measurability, Spec §Verificação 17/18]
- [x] CHK006 - Fica claro que a marca "Cantor" não é travada? [Consistency, Spec §Fora de escopo]

## Regra do maquiador em todos os caminhos

- [x] CHK007 - Todos os caminhos que acendem a maquiagem estão listados (criação manual, criação do orçamento, edição, vínculo)? [Completeness, Spec §FR-005]
- [x] CHK008 - Está dito que o sync do Google não cria maquiador e por quê? [Coverage, Spec §Casos de borda]
- [x] CHK009 - O critério de "já tem maquiador" é definido de forma objetiva ("maquiad" no nome) e igual ao do selo existente? [Clarity, Spec §FR-005, Casos de borda]
- [x] CHK010 - Está dito que a regra não duplica a vaga do orçamento (uma só, a com teto)? [Consistency, Spec §FR-006]
- [x] CHK011 - O evento cancelado está excluído explicitamente? [Edge Case, Spec §FR-007]
- [x] CHK012 - A spec diz o que acontece com a vaga quando a maquiagem sai de todos? [Edge Case, Spec §História 4.4]
- [x] CHK013 - A criação da vaga deixa rastro no histórico do evento? [Gap] — resolvido: FR-017
- [x] CHK014 - "Sem retroativo" está escrito como requisito, não só como decisão? [Clarity, Spec §FR-007]

## Marcas de origem das vagas

- [x] CHK015 - A lista de vagas "do sistema" é fechada (maquiador, coordenador, técnico, presença)? [Completeness, Spec §FR-009]
- [x] CHK016 - Está definido que as vagas anteriores ao deploy não levam a marca? [Edge Case, Spec §História 3.4]
- [x] CHK017 - A convivência das duas marcas na mesma vaga (vaga do sistema + talento do comercial) está prevista? [Consistency, Gap] — resolvido: Casos de borda
- [x] CHK018 - Está claro quando "inserido pelo comercial" sai (troca e remoção pelo card) e quando fica (formulário salvo sem troca)? [Clarity, Spec §FR-016]
- [x] CHK019 - "Letra mais clara" tem critério verificável (tamanho e cor relativos ao nome; legível)? [Measurability, Spec §FR-010] — resolvido: FR-010 diz menor que o nome, na cor de texto secundário da página, legível
- [x] CHK020 - A marca é anunciada a quem usa leitor de tela, e não só visual? [Coverage, Gap] — resolvido: FR-010

## Compatibilidade bundle × servidor

- [x] CHK021 - A spec diz o que a tela faz quando o servidor ainda não manda os campos novos (janela do deploy)? [Gap] — resolvido: Premissas
- [x] CHK022 - A migration é descrita como aditiva, sem exigir nada do código antigo? [Completeness, Spec §cabeçalho, Plano §Restrições]

## Texto (Princípio XV)

- [x] CHK023 - Os textos novos estão escritos por extenso na spec ("adicionado pelo sistema", "inserido pelo comercial", explicação da trava)? [Completeness, Spec §FR-010, §FR-012, §FR-015]
- [x] CHK024 - O perfil usa os mesmos nomes da tabela de preços, sem inventar vocabulário? [Consistency, Spec §Premissas, Research R1]
- [x] CHK025 - A ordem e o separador das marcas do perfil estão definidos? [Clarity, Spec §Premissas]

## Notas

- Itens resolvidos nesta passada viraram texto na spec (FR-010, FR-012, FR-017, Casos de borda,
  Premissas) no mesmo commit.
