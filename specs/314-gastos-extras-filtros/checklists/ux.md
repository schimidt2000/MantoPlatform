<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# UX, regra da situação, RBAC e texto Checklist: Feature 314 — Gastos Extras na tela inteira

**Propósito**: testar se os requisitos de layout (largura, rolagem), grupos recolhidos, filtros e URL, a regra da
situação do gasto, o RBAC do `GET /api/gastos` e o texto (Princípio XV) estão escritos completos, claros,
consistentes e mensuráveis — antes do `/speckit-tasks`.
**Created**: 2026-10-27
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md)

**Nota**: gerado pelo `/speckit-checklist` a partir da spec e do plano (sem `tasks.md` ainda). Profundidade padrão;
público: revisão do PR. Itens que falharam na primeira passada foram corrigidos na spec no mesmo ciclo — a correção
está anotada na linha.

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

- [ ] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs)
- [ ] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo
- [ ] CHK003 `verify_314.py` verde contra `manto_local`, escrita conferida por conexão separada, um cenário que falha
- [ ] CHK004 Tela aberta de verdade (1920, 1366, 1280, 375; Superadmin e Casting; Pagamentos também)
- [x] CHK005 Migration manual — não se aplica: `models.py` não muda (data-model.md)
- [x] CHK006 `scripts/validar_startcommand.py` — não se aplica: `render.yaml` não muda
- [ ] CHK007 Gate de RBAC: endpoint alterado só no payload; `docs/01` §4.3 sem linha nova, shape do `GET /api/gastos` atualizado
- [ ] CHK008 Docs por fonte única: `docs/01` (shape), `docs/02` (`/gastos` + exceção de largura no §Espaçamento), `docs/03`; `docs/05` (candidatos D3/D9)
- [ ] CHK009 Nível 1: `/speckit-converge` sem gaps
- [ ] CHK010 Texto novo ou alterado revisado pelo Princípio XV, lido na tela aberta
- [ ] CHK011 Antes de "em produção": `git status` limpo, `git log -1` = cabeçalho do `docs/03`, sonda `/api/`

## Completude dos requisitos

- [x] CHK012 As colunas da tabela e os campos do cartão do celular estão especificados um a um? [Completeness, Plan §O desenho da tela; Spec §FR-002]
- [x] CHK013 O cabeçalho do grupo recolhido tem conteúdo definido (rótulo, quantidade, total)? [Completeness, Spec §FR-005]
- [x] CHK014 Quais cartões de resumo existem e em que ordem está escrito na spec, não só no plano? [Completeness, Spec §FR-006 — corrigido: ordem acrescentada]
- [x] CHK015 Carregamento e erro da lista têm requisito (e o mesmo invólucro de largura)? [Gap → Spec §FR-017, acrescentado]
- [x] CHK016 O comportamento com valor inválido no endereço está definido? [Gap → Spec §FR-011, acrescentado]
- [x] CHK017 A pessoa sem nenhum gasto (lista vazia sem filtro) tem estado definido, separado do "filtro sem resultado"? [Coverage → Spec §Casos de borda, acrescentado; Spec §FR-012]

## Clareza dos requisitos

- [x] CHK018 "Ocupar a tela inteira" está traduzido em algo verificável (sem teto central; margens de sempre)? [Clarity, Spec §FR-001, §Premissas]
- [x] CHK019 "Sem rolagem lateral" tem um critério objetivo e as larguras em que vale? [Measurability, Spec §FR-002; Quickstart §3 (`scrollWidth <= innerWidth`)]
- [x] CHK020 A regra da situação cobre toda combinação de `status` × `payment_status` × `paid_at_creation` × desembolso, inclusive o pendente "já pago"? [Clarity, Spec §FR-003/FR-004, §Casos de borda — corrigido: pendente já pago; research D2 (ordem de decisão)]
- [x] CHK021 A composição da lista principal e do grupo "Pagos" está dita por exclusão mútua (cada caso num só lugar)? [Clarity, Spec §FR-004; data-model invariante]
- [x] CHK022 Está definido o que um filtro de situação faz com os grupos recolhidos (mostra a situação aberta, sem grupos)? [Gap → Spec §FR-006, acrescentado]
- [x] CHK023 "Os números dos cartões refletem o recorte" diz se o filtro de situação entra ou não na conta? [Ambiguity → Spec §FR-009, corrigido: não entra]

## Consistência

- [x] CHK024 Os rótulos das situações são os mesmos na spec, no plano, no data-model e no vocabulário de Pagamentos ("No banco", "Pagos")? [Consistency, Spec §FR-003; data-model; lib/pagamentos `BUCKET_LABELS`]
- [x] CHK025 A numeração dos cenários do verify bate entre as histórias, os critérios e a tabela? [Consistency, Spec §Verificação, §História 2/3/4, §SC-006]
- [x] CHK026 FR-002 (≥ 1366 px sem rolagem) e o plano (tabela a partir de `xl` = 1280) não se contradizem? [Consistency — o plano é mais estrito; a conta de larguras está no plano]
- [x] CHK027 "Nenhum total da empresa ao não gestor" (FR-015) é compatível com manter `totals` só para gestão? [Consistency, Spec §RBAC; contracts/gastos-list.md]

## Critérios de aceite

- [x] CHK028 SC-002 diz exatamente quem aparece na abertura, sem "da ordem de"? [Measurability → Spec §SC-002, corrigido]
- [x] CHK029 SC-003 (um grupo por gasto; soma dos grupos = total) é verificável por dado, não por olho? [Measurability, Spec §SC-003; verify cenário 3]
- [x] CHK030 A prova de que o verify "morde" está prevista (mutação com oráculo independente)? [Acceptance Criteria, Spec §Verificação cenário 7]

## Cobertura de cenários e bordas

- [x] CHK031 A ação que muda o gasto de grupo (aprovar, rejeitar, editar, excluir) tem requisito de manter filtros e grupo aberto? [Coverage, Spec §FR-014, §Casos de borda]
- [x] CHK032 Data futura, devolução travada, multa, bloco do auditor e grupo vazio estão cobertos? [Edge Case, Spec §Casos de borda]
- [x] CHK033 Texto longo (título de evento de cinco linhas do print) tem requisito de quebra/recorte? [Edge Case, Plan §O desenho da tela (`line-clamp-2` + `title`; `overflow-wrap`)]
- [x] CHK034 A janela de deploy (bundle novo com backend velho, sem `situacao`) tem comportamento definido? [Edge Case, research D1; contracts/gastos-list.md]

## Requisitos não funcionais (acessibilidade, RBAC)

- [x] CHK035 Acessibilidade dos cartões-filtro (ligado/desligado), dos grupos (aberto/fechado) e das ações em ícone (nome + dica) está especificada? [Gap → Spec §FR-018, acrescentado]
- [x] CHK036 O RBAC da chave nova está dito para as duas classes de usuário (gestão × não gestão)? [Completeness, Spec §RBAC; contracts/gastos-list.md]
- [x] CHK037 O efeito do "Ver como" nesta tela está declarado? [Assumption → Spec §Premissas, acrescentado: segue o papel real, como hoje]

## Texto (Princípio XV)

- [x] CHK038 Todo texto novo está listado com o termo do glossário ("Situação", "Excluir", "Ver nota fiscal", "Nenhum gasto encontrado.", "Limpar filtros")? [Completeness, Plan §Constitution Check XV]
- [x] CHK039 A concordância da contagem ("1 gasto", "3 gastos") está pedida para cartões e grupos? [Clarity, Plan §Constitution Check XV]
- [x] CHK040 Fica claro que nenhuma chave, enum ou código muda junto com o texto (o `"situacao"` da API é chave, não texto)? [Consistency, contracts/gastos-list.md; Plan XV]

## Notas

- 29 itens de requisito (CHK012–CHK040): 19 passaram de primeira, 10 foram corrigidos na spec (CHK014, 015, 016, 017, 020, 022, 023, 028, 035, 037 — marcados "corrigido/acrescentado").
- Portões CHK001–CHK004 e CHK007–CHK011 ficam para o implement/converge.
