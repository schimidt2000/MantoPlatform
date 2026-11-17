# Atribuição, RBAC, 390 px e texto — Checklist: Feature 351 (painel atribuído)

**Propósito**: testar a escrita dos requisitos da 351 nas quatro áreas de risco pedidas — regra da atribuição
(relógios e porta de troca da 348), RBAC e privacidade do valor da venda, UX em 390 px, texto (Princípio XV).
**Created**: 2026-11-17
**Feature**: [spec.md](../spec.md)

**Nota**: gerado pelo `/speckit-checklist` a partir da spec, do plano e da pesquisa (fluxo autônomo: profundidade
padrão, leitor = revisor do PR). Os itens CHK012+ foram avaliados contra a spec na mesma rodada; os que falhavam
viraram correção na spec (FR-003, FR-006, FR-011, FR-023, FR-032 e um caso de borda) e passaram.

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

- [ ] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs)
- [ ] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo
- [ ] CHK003 `verify_351.py` verde contra `manto_351` (exceção do plano), escrita conferida por conexão separada, um cenário que falha
- [ ] CHK004 Tela aberta de verdade (interno em 390 × 844 e tela larga)
- [ ] CHK005 Migration manual criada e aplicada no `manto_351`
- [x] CHK006 `scripts/validar_startcommand.py` — não se aplica (não toca o `startCommand`)
- [ ] CHK007 Gate de RBAC declarado em todo endpoint novo/alterado e linha em `docs/01` §4.3
- [ ] CHK008 Docs por fonte única: `docs/01`, `docs/02`, `docs/03` sempre; `04`/`05` (regra da atribuição, dívida 214)
- [ ] CHK009 Nível 1: `/speckit-converge` sem gaps
- [ ] CHK010 Texto novo ou alterado revisado pelo Princípio XV, lido na tela aberta
- [x] CHK011 Antes de "em produção" — não se aplica nesta rodada (sem merge e sem push)

## Regra da atribuição

- [x] CHK012 A regra diz qual contato vale, os limites da janela (inclusive) e o desempate? [Clarity, Spec §FR-003]
- [x] CHK013 O relógio de cada data da regra (momento do contato, criação do evento, data da venda, entrada na base) está definido? [Completeness, research R3]
- [x] CHK014 A porta única de troca da 348 é requisito, não só decisão de implementação? [Completeness, Spec §FR-001]
- [x] CHK015 A leitura da frente do evento por uma função só está escrita como requisito? [Consistency, Spec §FR-004]
- [x] CHK016 O corte de 01/06/2026 é o mesmo em FR-003, FR-009, casos de borda e História 1 (cenário 6)? [Consistency]
- [x] CHK017 As origens da ficha que contam como pagas estão delimitadas (Meta e Google; botão do site fica de fora)? [Clarity, Spec §FR-002, research R3]
- [x] CHK018 O evento com mais de uma ficha e a venda de grupo têm regra? [Edge Case, Spec §Casos de borda]
- [x] CHK019 A fórmula do desconto é a mesma na FR-006, na FR-007 e no contrato? [Consistency, Spec §FR-006]
- [x] CHK020 Está dito que o estado contra o teto usa o custo com desconto? [Clarity, Spec §FR-006]
- [x] CHK021 Está dito que a venda é do período e o contato pode ser anterior a ele? [Gap → corrigido, Spec §FR-006]
- [x] CHK022 A frente da venda atribuída (campanha × evento) foi decidida e registrada? [Ambiguity → Clarifications]

## Funil

- [x] CHK023 Cada uma das quatro divisões diz para onde vai a conversa sem anúncio, sem frente, sem peça e sem conceito? [Gap → corrigido, Spec §FR-011]
- [x] CHK024 A fonte do gasto de cada grupo está definida (Meta para frente; anúncio para anúncio, peça e conceito)? [Clarity, Spec §FR-012, research R6]
- [x] CHK025 "Sem dinheiro para o Comercial" é igual na FR-013, na seção RBAC e no cenário 8 do verify? [Consistency]

## RBAC e privacidade do valor da venda

- [x] CHK026 Todo endpoint novo ou alterado tem papel declarado, inclusive as rotas do agente que não mudam? [Coverage, Spec §RBAC]
- [x] CHK027 A regra "valor da venda só para Superadmin real" é a mesma na FR-010, no RBAC, no contrato e no cenário 27? [Consistency]
- [x] CHK028 As escritas só do Superadmin dizem que o "Ver como" não conta ("Superadmin real")? [Clarity, Spec §RBAC]
- [x] CHK029 Quem recebe o aviso da proposta e a regra de não repetir estão definidos? [Completeness, Spec §FR-024]
- [x] CHK030 Há cenário que deve falhar tanto para leitura (26) quanto para escrita (15)? [Coverage, Spec §Verificação]

## Proposta e diário

- [x] CHK031 Está delimitado quando o texto vira número e quando não vira? [Clarity, Spec §FR-022, Casos de borda]
- [x] CHK032 O impacto no mês está definido para os quatro tipos de proposta? [Gap → corrigido, Spec §FR-023]
- [x] CHK033 Janela, fim do teste e congelamento da linha de base estão definidos? [Completeness, Spec §FR-025, §FR-026]
- [x] CHK034 Falta de leitura e linha de base zero têm comportamento definido? [Edge Case, Spec §Casos de borda]

## 390 px e telas

- [x] CHK035 "Sem rolagem lateral em 390 px" é critério mensurável para cada tela tocada? [Measurability, Spec §SC-005, §FR-028]
- [x] CHK036 Tamanho da página, página no endereço e volta à página 1 estão definidos para Temas? [Completeness, Spec §FR-029, Casos de borda]
- [x] CHK037 O significado de "Minhas peças" e onde moram os filtros do Kanban estão definidos? [Clarity, Spec §FR-030, História 7]
- [x] CHK038 Os blocos novos têm estado de carregando, de erro e vazio? [Gap → corrigido, Spec §FR-032]

## Texto (Princípio XV)

- [x] CHK039 O texto da premissa e da regra está escrito na spec, sem depender de quem implementa? [Clarity, Spec §FR-007]
- [x] CHK040 Os textos de "no ar" / "sem gasto desde" e do custo por cliente novo de anúncio estão definidos? [Completeness, Spec §FR-016, História 8]
- [x] CHK041 Os estados vazios seguem "Nenhuma … ." e os erros "Não foi possível … Tente novamente."? [Consistency, Spec §FR-032]

## Dependências e premissas

- [x] CHK042 A dependência da 348 e a mesma head de migration estão documentadas, com o que muda quando ela entrar? [Dependency, Spec §Contexto, plan]
- [x] CHK043 Está registrado que o funil e o resultado real do card ficam vazios em produção até o CRM ligar? [Assumption, Spec §Premissas]
