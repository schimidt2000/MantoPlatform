<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Checklist de atribuição: 334

**Propósito**: testar a qualidade dos requisitos de captura, consulta e atribuição do anúncio.
**Created**: 2026-11-04
**Feature**: [spec.md](../spec.md)

**Nota**: gerado pelo `/speckit-checklist` a partir da spec e do plano, no modo autônomo (revisor, profundidade padrão).

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

- [x] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs)
- [x] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo
- [x] CHK003 `verify_334.py` verde (e 325/328/330/332/333), com conexão separada e os cenários que falham
- [x] CHK004 Tela aberta de verdade, em desktop e em 375×812
- [x] CHK005 Migration manual criada e aplicada no `manto_local`; downgrade ensaiado
- [x] CHK006 `scripts/validar_startcommand.py` — não se aplica (sem mudança no `startCommand`)
- [x] CHK007 Gate de RBAC declarado em todo endpoint novo/alterado e linha em `docs/01` §4.3
- [x] CHK008 Docs por fonte única: `docs/01`, `docs/02`, `docs/03`; `04`, `05` e o plano
- [x] CHK009 Nível 1: `/speckit-converge` sem gaps
- [x] CHK010 Texto novo revisado pelo Princípio XV, lido na tela aberta
- [x] CHK011 Antes de "em produção": git limpo, `docs/03` batendo, sonda `/api/` — **não publicado** (o dono adiou o push; `docs/03` marca NÃO PUBLICADO)

## Captura

- [x] CHK012 Está definido o que conta como anúncio, publicação e outro, nos dois canais? [Clarity, Spec §FR-001, Cenário 10]
- [x] CHK013 A unicidade do contato (o reenvio do mesmo aviso) está definida? [Completeness, Spec §FR-001, História 1 AC1]
- [x] CHK014 O Instagram que abre a conversa sem mensagem está coberto? [Coverage, Spec §História 1 AC2]

## Consulta à Meta

- [x] CHK015 Está definido quando a consulta acontece (depois de gravar, sem atrasar) e o que fica sem ela? [Completeness, Spec §FR-002, Casos de borda]
- [x] CHK016 A repetição da consulta tem regra (diária; 404 definitivo)? [Clarity, Spec §FR-003]
- [x] CHK017 O mesmo anúncio em várias conversas consulta uma vez só? [Edge Case, Spec §Casos de borda]
- [x] CHK018 A trava local e a falta de token estão definidas? [Coverage, Spec §FR-011]

## Atribuição na ficha

- [x] CHK019 O primeiro nunca sobrescrito e o mais recente sempre atualizado estão definidos? [Clarity, Spec §FR-004]
- [x] CHK020 A ficha que já tem origem (formulário, outro anúncio) tem regra? [Edge Case, Spec §Casos de borda]
- [x] CHK021 A conversa que só ganha ficha depois está coberta, com as mesmas regras? [Coverage, Spec §FR-007]
- [x] CHK022 O orgânico está limitado à ficha nova, e a ficha antiga sem origem fica como está? [Consistency, Spec §História 3 AC4]
- [x] CHK023 A campanha que chega depois entra na ficha? [Completeness, Spec §FR-005]

## Desempenho

- [x] CHK024 "Retorno" está definido de forma mensurável (contato no período, ficha anterior ao dia do contato)? [Measurability, Spec §FR-010, Premissas]
- [x] CHK025 A data que decide se a ficha é lead do período está definida para a ficha do Kommo e para a da Plataforma? [Clarity, Spec §FR-010]
