# Cobertura de Requisitos Checklist: EducaManto por responsabilidades

**Purpose**: Testar a qualidade dos requisitos (completude, clareza, consistência, mensurabilidade) nas cinco frentes pedidas — cálculo, PDF, RBAC, migração e retrocompatibilidade — antes de gerar tarefas.
**Created**: 2026-08-13
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [data-model.md](../data-model.md) · [contracts](../contracts/educamanto-endpoints.md)

## Cálculo — Completude e Clareza

- [x] CHK001 Todos os inputs do cálculo estão enumerados com tipo e obrigatoriedade? [Completeness, Spec §FR-004]
- [x] CHK002 A matriz dos 4 casos de equipe técnica está definida sem caso ausente ou sobreposto? [Completeness, Spec §FR-007]
- [x] CHK003 O efeito de cada responsabilidade sobre a soma de custos está especificado (entra/sai antes da margem)? [Clarity, Spec §FR-006, research §D2]
- [x] CHK004 A fórmula de fechamento (margens, desconto, teto do acréscimo, ceil100, ÷0,84) referencia valores exatos e a ordem das operações? [Clarity, Spec §FR-010]
- [x] CHK005 O headcount usado nos ensaios está distinguido do headcount do dia do evento (técnicos ensaiam?)? [Ambiguity → resolvido: ensaios = personagens + produção + ensemble; evento inclui técnicos — Spec §FR-008/§FR-009]
- [x] CHK006 O cálculo do "à vista 5%" define base, arredondamento e os dois regimes (sem/com NF)? [Clarity, Spec §FR-011, research §D9]
- [x] CHK007 A composição do total combinado com contratação Manto define explicitamente onde entram ceil100 e ÷0,84? [Clarity → explicitado na Spec §FR-016]
- [x] CHK008 As regras de transporte definem os dois modos com valores, fórmula e o que acontece com o caminhão em cada um? [Completeness, Spec §FR-012/§FR-013]
- [x] CHK009 O comportamento com km ausente/zero em cada modo de transporte está definido? [Edge Case, Spec §Edge Cases]
- [x] CHK010 Está especificado que técnicos passam pela margem como os demais custos (não são somados flat)? [Clarity, research §D3]

## PDF — Completude e Mensurabilidade

- [x] CHK011 Cada responsabilidade tem os dois textos exigidos (Manto/contratante) com autoria e gate de revisão definidos? [Completeness, Spec §FR-019, Clarifications 13/08]
- [x] CHK012 Os avisos fixos estão todos enumerados com seus valores (palco 5×4, camarim, som X/Y, visita técnica)? [Completeness, Spec §FR-021]
- [x] CHK013 A regra de ocultar linhas zeradas está definida e testável? [Measurability, Spec §FR-022]
- [x] CHK014 O limite de uma página A4 por configuração (e o que fazer se o conteúdo não couber) está especificado? [Gap → resolvido na Spec §FR-018]
- [x] CHK015 O conteúdo do trecho da contratação Manto no PDF (o que está incluso + totais por duração) está definido? [Completeness, Spec §FR-024]
- [x] CHK016 A remoção dos textos por nível está declarada explicitamente (sem sobra de SHORT_DESC/LONG_DESC)? [Completeness, Spec §FR-025]
- [x] CHK017 O formato/limite da observação livre do vendedor está definido? [Gap → resolvido: texto livre até 2.000 caracteres, Spec §FR-023]

## RBAC — Consistência

- [x] CHK018 A lista do que papéis não-superadmin PODEM ver está fechada (allowlist) e não apenas a do que não podem? [Clarity, Spec §FR-028]
- [x] CHK019 O corte de visibilidade está exigido também na resposta da API e no histórico, não só na tela? [Coverage, Spec §SC-005, contracts]
- [x] CHK020 O contrato da tela de musicais está consistente com FR-028 (comercial não vê custos/margens)? [Conflict → resolvido: listagem de gestão com custos passa a ser só superadmin; contrato corrigido]
- [x] CHK021 A permanência do campo de acréscimo para o revendedor está conciliada com a ocultação do breakdown (aviso de teto sem expor cálculo)? [Consistency, Spec §FR-028, contracts]
- [x] CHK022 Os papéis com acesso a cada endpoint novo estão enumerados? [Completeness, contracts]

## Migração — Completude e Riscos

- [x] CHK023 O destino de cada dado atual está mapeado (Master→musical, Som→coluna, catering→coluna, caminhão→regra, níveis→poda)? [Completeness, data-model §Migração]
- [x] CHK024 A preservação de ids dos Master está declarada como requisito (base do Recalcular)? [Completeness, research §D1]
- [ ] CHK025 A divisão personagens × produção de CADA musical tem fonte definida (só a Uma Aventura Animal está confirmada: 9+2; os totais 10/9/7/9/10 dos demais precisam da divisão do dono)? [Gap — pendência de negócio adicionada à spec; gate de deploy]
- [x] CHK026 Requisitos de rollback/backup da migração estão definidos (downgrade não restaura níveis podados; dump antes do deploy)? [Recovery, data-model §Migração]
- [x] CHK027 A verificação de paridade numérica pós-migração tem critério objetivo? [Measurability, quickstart §1]
- [x] CHK028 O default `discount_days` do model foi alinhado ao banco real (3) para pacote novo não nascer divergente? [Consistency, data-model]

## Retrocompatibilidade — Cobertura

- [x] CHK029 O comportamento de snapshots v1 está definido para as três ações (Ver, Baixar PDF, Recalcular)? [Coverage, Spec §FR-027, data-model §Snapshot]
- [x] CHK030 O mapeamento de Recalcular v1 para pacotes apagados (Intermediário/Econômica) está especificado com aviso ao vendedor? [Edge Case, research §D1]
- [x] CHK031 O destino das rotas Jinja desligadas está definido rota a rota (redirect, não 404)? [Completeness, contracts §Rotas Jinja]
- [x] CHK032 A garantia de que `app/orcamento` permanece intocado (calculadora de eventos sem regressão) está declarada e verificável? [Consistency, plan §Structure, quickstart §10]

## Dependências, Assunções e Pendências

- [x] CHK033 Todas as pendências de negócio (técnicos, áreas X/Y, iluminação/cenário por musical, textos) estão listadas com dono e marcadas como gate de deploy — não de plano? [Assumption, Spec §Assumptions, research §Pendências]
- [x] CHK034 A dependência da config de transporte compartilhada (tarifas + nova chave caminhao_sp) está documentada? [Dependency, research §D5]
- [x] CHK035 A não-mudança da comissão do responsável EducaManto (5% sobre lucro) está declarada como fora de escopo? [Completeness, Spec §Assumptions]

## Notas da rodada de 13/08/2026

- **CHK005, CHK007, CHK014, CHK017, CHK020**: falhas reais encontradas nesta rodada e corrigidas na mesma data — spec (FR-008/009/016/018/023, Assumptions) e contrato (RBAC da tela de musicais) atualizados; ver commit desta rodada.
- **CHK025**: única pendência aberta — depende do dono enviar a divisão personagens × produção dos 6 musicais restantes (junto com os valores dos técnicos). Registrada na spec como gate de deploy; não bloqueia `/speckit-tasks`.
