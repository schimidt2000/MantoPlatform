<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Checklist de envio e ficha: 333

**Propósito**: testar a qualidade dos requisitos do envio do orçamento pela conversa e da ligação à ficha:
idempotência, ordem das partes, ficha criada ou reaproveitada, escolha manual, Instagram em partes e pré-condições antes
de criar qualquer coisa.
**Created**: 2026-11-03
**Feature**: [spec.md](../spec.md)

**Nota**: gerado pelo `/speckit-checklist` a partir da spec e do plano. Modo autônomo: revisor, profundidade padrão,
foco dado pelo pedido. As lacunas marcadas `[Gap]` foram fechadas na spec na mesma rodada.

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

- [x] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs)
- [x] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo (os I001/E402 de `app/models.py` são anteriores)
- [x] CHK003 `verify_333.py` verde (e 325/328/330/332), com conexão separada e os cenários que falham, 15/15 (e 332 17/17, 330 29/29, 328 24/24, 325 22/22)
- [x] CHK004 Tela aberta de verdade, em desktop e em 375×812
- [x] CHK005 Migration manual criada e aplicada no `manto_local`; downgrade ensaiado
- [x] CHK006 `scripts/validar_startcommand.py` — não se aplica (sem mudança no `startCommand`)
- [x] CHK007 Gate de RBAC declarado em todo endpoint novo/alterado e linha em `docs/01` §4.3
- [x] CHK008 Docs por fonte única: `docs/01`, `docs/02`, `docs/03`; `04` e o plano (`docs/01`, `02`, `03`, `04`, `05`, plano)
- [x] CHK009 Nível 1: `/speckit-converge` sem gaps (18 achados de um revisor independente, fechados em T020–T036)
- [x] CHK010 Texto novo revisado pelo Princípio XV, lido na tela aberta
- [x] CHK011 Antes de "em produção": git limpo, `docs/03` batendo, sonda `/api/` — **não publicado** (o dono adiou o push; `docs/03` marca NÃO PUBLICADO)

## Idempotência

- [x] CHK012 O efeito de repetir o mesmo pedido está definido, inclusive quando o primeiro parou no meio? [Completeness, Spec §FR-004, Casos de borda — fechado: "repetir manda só as partes que faltaram"]
- [x] CHK013 Está claro que o registro do envio é um por pedido, e não um por parte? [Clarity, Spec §FR-005]

## Ordem das partes e falha

- [x] CHK014 A ordem (texto em partes, depois o PDF) está definida nos dois canais? [Clarity, Spec §FR-003]
- [x] CHK015 Está definido o que acontece com as outras partes quando a Meta recusa uma? [Exception Flow, Spec §Casos de borda]
- [x] CHK016 Está definido o que acontece se a janela fecha no meio do envio? [Gap → fechado, Spec §Casos de borda]

## Instagram em partes

- [x] CHK017 A regra de divisão (onde quebra, teto em bytes) é específica e mensurável? [Clarity, Spec §FR-003, Casos de borda]
- [x] CHK018 O PDF no Instagram está coberto (aceito e enviado por último)? [Coverage, Spec §Casos de borda]

## Pré-condições antes de criar qualquer coisa

- [x] CHK019 Está explícito que, com a janela fechada, a trava ou o canal desligado, nem a ficha nem o registro nascem? [Gap → fechado, Spec §História 1 AC3]
- [x] CHK020 Os textos de recusa das pré-condições são os mesmos do envio comum? [Consistency, Spec §História 1]

## Ficha criada ou reaproveitada

- [x] CHK021 A ordem do nome da ficha nova está completa (orçamento, perfil, telefone)? [Gap → fechado, Spec §FR-007]
- [x] CHK022 A regra do telefone com e sem o nono dígito, inclusive com duas fichas, está definida? [Edge Case → fechado, Spec §FR-007]
- [x] CHK023 Está definido o que a pessoa vê quando a ficha "nova" já existia pelo telefone? [Gap → fechado, Spec §História 4]
- [x] CHK024 A origem da ficha nova e onde ela aparece estão definidas? [Clarity, Spec §FR-013]
- [x] CHK025 O caso do Instagram sem ficha (recusa no campo e as duas saídas) está definido? [Coverage, Spec §FR-008]

## Escolha manual

- [x] CHK026 Está definido que remover o vínculo também é escolha manual, que a ligação automática respeita? [Gap → fechado, Spec §FR-009]
- [x] CHK027 O efeito de trocar a ficha sobre orçamentos já ligados está definido? [Consistency, Spec §FR-009]
- [x] CHK028 Está claro que, com ficha na conversa, o envio usa essa ficha (sem perguntar)? [Clarity, Spec §FR-006, História 3]

## Orçamento, histórico e evento

- [x] CHK029 O reenvio do orçamento para outra ficha tem regra (fica a primeira)? [Edge Case, Spec §FR-006]
- [x] CHK030 Os "recentes" estão definidos (período, ordem, limite, campos da busca)? [Clarity, Spec §FR-001, Premissas]
- [x] CHK031 O envio de orçamento de outra pessoa do time está coberto (permitido e registrado)? [Gap → fechado, Spec §RBAC]
- [x] CHK032 A relação da cliente no evento e a lista que já tem clientes estão definidas? [Gap → fechado, Spec §FR-011]

## Formulário

- [x] CHK033 O texto do formulário está definido, inclusive sem nome conhecido? [Completeness, Spec §Premissas]
- [x] CHK034 O endereço do link (o público da Plataforma, mesmo no ambiente local) está claro? [Clarity, Spec §FR-010]
