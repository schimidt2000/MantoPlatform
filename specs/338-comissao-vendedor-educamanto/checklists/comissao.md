<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Comissão e dinheiro Checklist: Comissão do vendedor e lucro real no EducaManto

**Propósito**: testar a escrita dos requisitos de dinheiro (base do responsável, linha do vendedor,
cancelado, DRE) e do RBAC do card Comercial antes das tarefas.
**Created**: 2026-11-06
**Feature**: [spec.md](../spec.md)

**Nota**: gerado pelo `/speckit-checklist` a partir da spec, do plano e das tarefas. Profundidade padrão,
para quem revisa o PR. Os itens marcados foram conferidos contra a spec depois dos ajustes desta rodada.

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

- [x] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs)
- [x] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo
- [x] CHK003 `verify_338.py` verde contra o espelho (`manto_338`), escrita conferida por conexão separada, um cenário que falha
- [x] CHK004 Tela aberta de verdade (card Comercial e Comissões)
- [x] CHK005 Migration manual criada e aplicada no espelho
- [x] CHK006 `scripts/validar_startcommand.py` — não se aplica (o `startCommand` não muda)
- [x] CHK007 Gate de RBAC declarado no `/comercial` e linha em `docs/01` §4.3
- [x] CHK008 Docs por fonte única: `docs/01`, `docs/02`, `docs/03`; `docs/04` §2
- [x] CHK009 Nível 1: `/speckit-converge` sem gaps
- [x] CHK010 Texto novo (rótulo, ajuda, erros da API) revisado pelo Princípio XV, lido na tela aberta
- [ ] CHK011 Antes de "em produção": `git status` limpo, `git log -1` = cabeçalho do `docs/03`, sonda `/api/`

## Completude dos requisitos

- [x] CHK012 Todos os termos da base do responsável estão enumerados (venda, BV, cachês, gastos, imposto, comissão do vendedor)? [Completeness, Spec §FR-001]
- [x] CHK013 Está dito quais gastos extras contam (aprovados, ligados aos dias vivos, fora a devolução, de qualquer data)? [Completeness, Spec §FR-001]
- [x] CHK014 A alíquota do imposto e a base sobre a qual incide (a venda) estão definidas? [Completeness, Spec §FR-001, Premissas]
- [x] CHK015 Estão listadas todas as condições para a linha do vendedor existir (valor, venda, cortesia, EducaManto com responsável, vendedor com comissão, evento vivo)? [Completeness, Spec §FR-003]
- [x] CHK016 O ciclo da linha do vendedor (mês do evento) e a data da venda dela estão definidos? [Completeness, Spec §FR-003, Clarifications]
- [x] CHK017 Os relatórios que somam a comissão do vendedor (DRE, comissão prevista) estão nomeados? [Completeness, Spec §FR-004]
- [x] CHK018 Está definido o que o cancelamento congela e qual o alvo do vendedor? [Completeness, Spec §FR-005, data-model]

## Clareza

- [x] CHK019 O arredondamento é único e no fim, sem arredondar o imposto à parte? [Clarity, Spec §FR-001]
- [x] CHK020 "Quem recebe" a comissão do vendedor está definido (o vendedor do evento)? [Clarity, Premissas]
- [x] CHK021 As mensagens de erro do campo têm texto fechado, no padrão da constituição XV? [Clarity, contracts/api.md]
- [x] CHK022 "Chave ausente não mexe no valor" está escrito para o PATCH (bundle antigo)? [Clarity, contracts/api.md]

## Consistência

- [x] CHK023 A regra do cancelado do vendedor é a mesma proporção do responsável e do BV (teto no valor)? [Consistency, Spec §FR-005]
- [x] CHK024 O valor de teste do Jundiaí (R$ 771,82) e do Santo Américo (R$ 61,01) fecham com FR-001? [Consistency, Spec §História 1, research R3]
- [x] CHK025 O 409 do cancelado no campo novo segue a regra única da 306 ("a porta não recongela → 409 para todos")? [Consistency, Spec §FR-006]
- [x] CHK026 A validação "até a venda" é coerente com a venda "a definir"? [Consistency, contracts/api.md, Casos de borda]

## Cobertura de cenários e bordas

- [x] CHK027 O caso vendedor = responsável está coberto? [Coverage, Casos de borda]
- [x] CHK028 Comissão do vendedor maior que o lucro está coberta? [Edge Case, Casos de borda]
- [x] CHK029 Grupo de dias: onde mora o valor, agrupar, passagem e corte de um dia? [Coverage, Casos de borda]
- [x] CHK030 Linha já paga: no vivo (intacta) e no cancelado (ajuste negativo pela 306)? [Coverage, Spec §FR-003, §FR-005]
- [x] CHK031 Evento que deixa de ser EducaManto ou responsável retirado? [Edge Case, Casos de borda]
- [x] CHK032 Gasto aprovado depois do pagamento? [Edge Case, Spec §História 1 cenário 3]
- [ ] CHK033 A exclusão do evento com linha do vendedor paga (estorno) está descrita? [Gap] — coberta só no plano (research R8: o estorno copia o `source`); aceitável, é o caminho de sempre da exclusão.

## RBAC

- [x] CHK034 O gate do campo novo está declarado e é o do card (Comercial e Superadmin)? [Spec §RBAC, contracts/api.md]
- [x] CHK035 Há um cenário de autorização que deve falhar no verify? [Spec §Verificação, cenário 7]

## Dependências e premissas

- [x] CHK036 A colisão de migration com as branches do CRM está registrada? [Dependency, plan §Operação e Deploy]
- [x] CHK037 O banco de verificação diferente do `manto_local` está justificado? [Assumption, research R9]
