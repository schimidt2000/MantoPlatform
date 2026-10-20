# Checklist de requisitos: visibilidade e RBAC — Feature 312

**Purpose**: testar se a spec, o plano e os contratos dizem sem furo onde o cancelado aparece, quem vê o quê e
quem pode o quê.
**Created**: 2026-10-20 · **Audiência**: autor e revisor antes do `/speckit-tasks`
**Fontes**: [spec.md](../spec.md), [plan.md](../plan.md), [contracts/api.md](../contracts/api.md),
[research.md](../research.md)

Avaliação em 20/10: cada item foi conferido contra os documentos; os que falharam foram corrigidos nos
documentos (nota "corrigido") antes de marcar.

## Completude — onde o cancelado some

- [x] CHK001 As superfícies de lista em que o cancelado deve sumir estão enumeradas uma a uma (Dia API e Jinja,
  busca, seletores, fichas, filas 3D, conflito em três cópias, painel do grupo, ensaio legado)? [Completeness, Spec
  FR-001–FR-009]
- [x] CHK002 A spec nomeia só as visões que existem? *Corrigido: tirada a "Semana" — a agenda tem Mês, Lista e Dia
  (`AgendaPage.tsx`, `DayTimelineView.tsx`).* [Clarity, Spec História 1]
- [x] CHK003 Está dito que nenhum parâmetro traz o cancelado de volta, em toda lista? [Completeness, Spec FR-001,
  Contracts "Leitura"]
- [x] CHK004 Está dito que o filtro da busca vem antes do limite de resultados? [Clarity, Spec FR-002]
- [x] CHK005 Os seletores fora da busca (por data, candidatos automáticos do formulário, lista Jinja de shows do
  vínculo de ensaio) estão cobertos? *Corrigido: a lista Jinja entrou na FR-003.* [Coverage, Spec FR-003]
- [x] CHK006 Está definido onde o cancelado CONTINUA visível (página, card, tela dele) e por qual caminho se chega à
  tela (página, card, sino, link)? [Completeness, Spec História 2]
- [x] CHK007 Está definido que as coisas já ligadas continuam visíveis, com o selo, e onde o selo nunca aparece?
  [Consistency, Spec FR-036]

## Clareza — quem vê o motivo (Q9)

- [x] CHK008 A Q9 define o payload (campos nulos) E a tela (sem linha de motivo, "Evento cancelado em DD/MM")?
  [Clarity, Spec FR-020]
- [x] CHK009 Está dito se a Q9 segue o "Ver como"? [Clarity, Spec FR-020; verify cenário 8]
- [x] CHK010 Os outros caminhos por onde o motivo poderia vazar estão cobertos? Conferido no código: o motivo sai só
  no detalhe (`agenda_read.py:831`), na página de Cancelamentos (`cancel_ops.py:3462`, SUPERADMIN/FINANCEIRO) e no
  histórico (só Superadmin); sino e e-mail não o levam. [Coverage, Reconferência]
- [x] CHK011 O conflito Q9 × spec da 306b está resolvido por escrito, com a decisão do dono que vale? [Conflict,
  Spec Session 2026-10-20 item 2]

## RBAC — página, assign e card

- [x] CHK012 O gate da página diz papel real (não "Ver como") e inclui a fila de exclusão? [Clarity, Spec FR-027,
  Contracts]
- [x] CHK013 Está dito que abrir a leitura ao Financeiro não abre excluir, cancelar nem alterar devolução?
  [Completeness, Spec FR-027; verify cenário 17]
- [x] CHK014 O gate do `assign` no cancelado está definido por papel real, com a frase do 403 e o comportamento no
  vivo inalterado? [Clarity, Spec FR-024, Contracts "Tirar da escala"]
- [x] CHK015 A Jinja do `assign` no cancelado está coberta (o despachante recusa tudo)? [Coverage, Spec Session item
  4]
- [x] CHK016 O corte da Q1 diz se segue a flag ou o papel real? *Corrigido: pela flag, como os outros números de
  dinheiro.* [Clarity, Spec FR-032]
- [x] CHK017 O escopo do card para vendedora e revendedor EducaManto está definido (o do servidor)? [Clarity, Spec
  FR-032]
- [x] CHK018 O link "Ver na página de Cancelamentos" só para quem abre a página está definido? [Completeness, Spec
  FR-035]
- [x] CHK019 A pendência da Home tem os papéis que a veem declarados? [Completeness, Spec FR-023]

## Trava sem furo

- [x] CHK020 A regra padrão para rota de escrita que nascer depois está escrita (cai na trava; só as de regra
  própria ficam livres)? [Completeness, Spec Session item 3]
- [x] CHK021 Há um requisito verificável que impeça rota nova de escapar da trava em silêncio? *Corrigido: cenário
  9b, inventário das rotas de escrita no `url_map`.* [Measurability, Gap]
- [x] CHK022 A ordem das checagens (404 → 403 → trava) está definida? [Clarity, Contracts "Trava"]
- [x] CHK023 As escritas por id de outra entidade (vaga, presente, observação, ensaio) estão listadas? [Coverage,
  Contracts "Trava"]
- [x] CHK024 Está definido que a trava vale para o Superadmin (só a regra de venda o libera)? [Clarity, Spec FR-011]

## Superfícies fora do interno

- [x] CHK025 O portal recusa sem revelar título ou ficha, e preserva a ordem "não escalado" primeiro? [Clarity,
  Spec FR-038, História 6]
- [x] CHK026 A avaliação pública define o que a resposta 410 mostra? *Corrigido: sem título nem data.* [Clarity,
  Spec FR-016]

## Notas

- 26 itens; 5 corrigidos nos documentos em 20/10 (CHK002, CHK005, CHK016, CHK021, CHK026). Nenhuma pergunta ao dono.
