<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Checklist do funil e da linha do tempo: 335

**Propósito**: testar a qualidade dos requisitos da coorte, das etapas, da divisão e dos marcos.
**Created**: 2026-11-06
**Feature**: [spec.md](../spec.md)

**Nota**: gerado pelo `/speckit-checklist` a partir da spec e do plano, no modo autônomo (revisor, profundidade padrão).

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

- [x] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs)
- [x] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo
- [x] CHK003 `verify_335.py` verde (e 325/328/330/332/333/334), com conexão separada e os cenários que falham
- [x] CHK004 Tela aberta de verdade, em desktop e em 375×812
- [x] CHK005 Migration — não se aplica (nenhuma tabela ou coluna nova)
- [x] CHK006 `scripts/validar_startcommand.py` — não se aplica (sem mudança no `startCommand`)
- [x] CHK007 Gate de RBAC declarado em todo endpoint novo/alterado e linha em `docs/01` §4.3
- [x] CHK008 Docs por fonte única: `docs/01`, `docs/02`, `docs/03`; `04`, `05` e o plano
- [x] CHK009 Nível 1: `/speckit-converge` sem gaps
- [x] CHK010 Texto novo revisado pelo Princípio XV, lido na tela aberta
- [x] CHK011 Antes de "em produção": git limpo, `docs/03` batendo, sonda `/api/` — **não publicado** (o dono adiou o push; `docs/03` marca NÃO PUBLICADO)

## Coorte e etapas

- [x] CHK012 Está definido o que é o "primeiro contato" e o que acontece com a conversa sem mensagem da cliente? [Clarity, Spec §Casos de borda]
- [x] CHK013 O fato de cada etapa está definido, com a regra "depois do primeiro contato"? [Completeness, Spec §FR-004/FR-005]
- [x] CHK014 A regra da etapa mais avançada (o funil nunca cresce) e o "parou em" estão definidos? [Consistency, Spec §FR-006]
- [x] CHK015 A conversa sem ficha tem regra (até onde ela anda)? [Edge Case, Spec §Casos de borda]
- [x] CHK016 A mesma cliente em dois canais e a cliente antiga que volta estão definidas? [Coverage, Spec §Casos de borda]
- [x] CHK017 O evento cancelado e o evento de grupo têm regra no funil e na ficha? [Edge Case, Spec §FR-003, Casos de borda]
- [x] CHK018 O período (datas de São Paulo, padrão, limite) está definido de forma mensurável? [Measurability, Spec §FR-011]

## Divisão, filtros e lista

- [x] CHK019 "Vendedor" está definido (o responsável atual; a fila)? [Clarity, Spec §FR-008, Premissas]
- [x] CHK020 A soma das linhas da divisão bate com o total? [Measurability, Spec §FR-008]
- [x] CHK021 A conversa sem anúncio tem lugar no filtro e na divisão por campanha? [Coverage, Spec §FR-007]
- [x] CHK022 A lista de quem parou tem ordem e limite definidos? [Completeness, Spec §FR-009, contracts]

## Linha do tempo e acesso

- [x] CHK023 Cada tipo de marco tem a fonte, a data e o link definidos? [Completeness, research R5]
- [x] CHK024 O acesso está definido por superfície (funil só Comercial/Superadmin; ficha com o Financeiro, sem os links que ele não abre)? [Consistency, Spec §FR-010]
- [x] CHK025 Está explícito que o funil não mostra dinheiro? [Clarity, Spec §Premissas, Fora de escopo]
