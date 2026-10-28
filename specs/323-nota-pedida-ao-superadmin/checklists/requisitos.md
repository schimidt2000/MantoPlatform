# Requisitos Checklist: 323 — nota pedida ao Superadmin

**Propósito**: testar a escrita dos requisitos nos pontos de risco pedidos — RBAC do bloco da Home,
idempotência do pedido e do e-mail, texto (XV), compatibilidade de payload, desligar o chip,
cancelado/satélite. Revisor de PR; profundidade padrão.
**Created**: 2026-10-28
**Feature**: [spec.md](../spec.md)

**Nota**: gerado pelo `/speckit-checklist` a partir da spec, do plano e dos contratos. Os itens
CHK012+ foram avaliados contra a spec nesta rodada; os achados viraram FR-016/FR-017 e três casos
de borda.

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

- [x] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs)
- [x] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo
- [x] CHK003 `verify_323.py` verde contra `manto_local`, escrita conferida por conexão separada, um cenário que falha
- [x] CHK004 Tela aberta de verdade; superfície pública em viewport mobile
- [x] CHK005 Migration manual criada e aplicada no `manto_local` se `models.py` mudou; destrutiva ensaiada
- [x] CHK006 `scripts/validar_startcommand.py` verde se tocou o `startCommand` do `render.yaml` — não se aplica (não toca)
- [x] CHK007 Gate de RBAC declarado em todo endpoint novo/alterado e linha em `docs/01` §4.3
- [x] CHK008 Docs por fonte única: `docs/01`, `docs/02`, `docs/03` sempre; `00`/`04`/`05` se aplicável
- [x] CHK009 Nível 1: `/speckit-converge` sem gaps
- [x] CHK010 Texto novo ou alterado (tela, e-mail, PDF, erro da API) revisado pelo Princípio XV: tom da superfície e glossário, lido na tela aberta
- [ ] CHK011 Antes de "em produção": `git status` limpo, `git log -1` = cabeçalho do `docs/03`, sonda `/api/`

## RBAC do bloco da Home

- [x] CHK012 Está definido quem recebe o painel e quem não recebe, inclusive Financeiro, que já vê o card do Financeiro? [Completeness, Spec §FR-014, História 3 cenário 4]
- [x] CHK013 O efeito do "Ver como" sobre o painel está especificado, e de forma consistente com a regra da tela inicial (`docs/00` §4)? [Consistency, Spec §FR-014]
- [x] CHK014 O gate da ação "Inserir nota" a partir do painel está declarado, reusando a porta existente sem ampliar papéis? [Clarity, Spec §RBAC, contracts §4]
- [x] CHK015 Há um cenário de verificação de autorização que DEVE falhar se o bloco vazar? [Measurability, Spec §Verificação #8]

## Idempotência do pedido e do e-mail

- [x] CHK016 A condição que cria a nota pedida ("venda sem nenhuma nota") está escrita sem ambiguidade para venda com nota emitida ou a emitir? [Clarity, Spec §FR-001, §FR-003]
- [x] CHK017 O clique duplo (duas gravações simultâneas) tem requisito explícito de no máximo uma nota? [Coverage, Spec §Casos de borda]
- [x] CHK018 "Um aviso por nota" está quantificado e cobre o salvar de novo, o religar e a nota do legado? [Completeness, Spec §FR-011, Casos de borda, data-model]
- [x] CHK019 O momento do aviso em relação à gravação (depois do fato; falha não desfaz) está especificado? [Clarity, Spec §FR-011, História 4 cenário 3]
- [x] CHK020 O que acontece com o valor da nota pedida quando a venda muda depois do pedido está definido? [Gap → resolvido em FR-016]

## Texto (Princípio XV)

- [x] CHK021 O assunto do e-mail tem formato exato, incluindo as variações sem valor e sem cliente? [Clarity, Spec §FR-012, contracts §5]
- [x] CHK022 As mensagens de erro de validação estão redigidas no padrão do interno ("Informe…") e amarradas a um campo? [Completeness, contracts §1]
- [x] CHK023 Rótulos, botões e estado vazio do painel e do formulário estão listados com os verbos do glossário (Inserir, Ver, Informar)? [Consistency, plan §Constitution Check XV]
- [x] CHK024 O tom do e-mail (interno operacional, modelo 319) está declarado? [Clarity, Spec §História 4]

## Compatibilidade de payload

- [x] CHK025 A spec diz o que acontece quando a gravação chega sem os dados da nota (bundle antigo)? [Gap → resolvido em FR-017]
- [x] CHK026 Os campos novos de resposta (painel, `venda.nota`, `pedida_por`) estão marcados como opcionais para o cliente? [Completeness, contracts cabeçalho]
- [x] CHK027 A distinção `null` × ausente do bloco da Home está definida? [Clarity, contracts §3]

## Desligar o chip

- [x] CHK028 O destino das notas a emitir e das emitidas ao desligar está especificado separadamente? [Completeness, Spec §FR-013]
- [x] CHK029 O destino dos dados da nota ao desligar está definido? [Clarity, data-model "Desligar o chip não apaga os dados"]
- [x] CHK030 A divergência com o comportamento do Jinja legado (que apaga tudo) está registrada como decisão? [Consistency, research R2]

## Cancelado e satélite

- [x] CHK031 O evento cancelado tem regra para pedido novo e para nota a emitir que já existia? [Coverage, Spec §Casos de borda]
- [x] CHK032 Alterar os dados da nota no cancelado pelo "Editar tudo" está coberto pela regra do 409 da 306? [Consistency, contracts §1]
- [x] CHK033 O satélite de grupo tem regra (a nota é da venda do principal)? [Coverage, Spec §Casos de borda]

## Notas

- Marque como concluído: `[x]`
- Anote achados na própria linha
- Itens numerados em sequência para referência
