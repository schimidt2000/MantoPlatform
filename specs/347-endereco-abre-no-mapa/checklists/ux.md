# UX mobile e acessibilidade Checklist: Tocar no endereço do evento e escolher o app de mapas

**Propósito**: testar se os requisitos de UX no celular e de acessibilidade do endereço tocável e
da escolha de app de mapas estão completos, claros e mensuráveis (app interno e portal)
**Created**: 2026-11-17
**Feature**: [spec.md](../spec.md)

**Nota**: gerado pelo `/speckit-checklist` a partir da spec e do plano. Profundidade padrão, para
revisão de PR. Itens marcados depois da revisão da spec (os que faltavam viraram FR-003, FR-011 e
um caso de borda).

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

- [x] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs)
- [x] CHK002 `ruff check` limpo nos arquivos Python tocados (só o `verify_347.py`)
- [x] CHK003 `verify_347.py` verde contra o `manto_local` (só leitura), com o cenário que deve falhar reprovado
- [x] CHK004 Tela aberta de verdade; portal em viewport mobile
- [x] CHK005 Migration: não se aplica (`models.py` intacto)
- [x] CHK006 `startCommand`: não se aplica
- [x] CHK007 RBAC: não se aplica (nenhum endpoint)
- [x] CHK008 Docs por fonte única: `docs/02` e `docs/03`; `docs/01` sem contrato novo
- [x] CHK009 Nível 1: `/speckit-converge` sem gaps
- [x] CHK010 Texto novo revisado pelo Princípio XV, lido na tela aberta
- [ ] CHK011 Antes de "em produção": `git status` limpo, `git log -1` = cabeçalho do `docs/03`, sonda `/api/`

## Completude dos requisitos

- [x] CHK012 Todas as telas em que o endereço vira tocável estão nomeadas, e as que ficam de fora também? [Completeness, Spec §FR-001, §FR-002, §Fora de escopo]
- [x] CHK013 O conteúdo da escolha (título, endereço, opções e ordem) está definido? [Completeness, Spec §FR-003]
- [x] CHK014 O tamanho mínimo de toque está definido também para as opções da escolha, não só para o endereço no portal? [Gap → Spec §FR-003]
- [x] CHK015 Está definido o que acontece depois de escolher uma opção (a escolha fecha, a tela fica como estava)? [Completeness, Spec §FR-005]
- [x] CHK016 Estão definidas todas as formas de fechar sem escolher? [Completeness, Spec §FR-006]

## Clareza

- [x] CHK017 "Parecer tocável" está traduzido em atributos verificáveis (ícone de local, cor de link)? [Clarity, Spec §FR-007]
- [x] CHK018 "Abrir o endereço" está desambiguado entre mostrar o local e iniciar a rota? [Clarity, Spec §FR-004, §Premissas]
- [x] CHK019 Está claro o que "app instalado × site" significa para quem não tem o app? [Clarity, Spec §FR-004, §Casos de borda]

## Consistência

- [x] CHK020 A escolha é a mesma (textos, ordem, comportamento) nas duas superfícies? [Consistency, Spec §FR-010]
- [x] CHK021 O alvo de 44px é coerente com os outros links do card do portal ("Ver ficha de figurino", "Falta responder este convite")? [Consistency, Spec §FR-007, §História 2]
- [x] CHK022 O cabeçalho e o "Local" de "Dados do evento" têm o mesmo comportamento? [Consistency, Spec §História 1 cenário 3]

## Acessibilidade

- [x] CHK023 Está exigido que o endereço seja alcançável e acionável por teclado no computador? [Gap → Spec §FR-011]
- [x] CHK024 Está exigido um nome acessível que diga a leitores de tela que o endereço abre um app de mapas? [Gap → Spec §FR-011]
- [x] CHK025 Está definido para onde volta o foco quando a escolha fecha? [Gap → Spec §FR-011]
- [x] CHK026 Está exigido que o movimento respeite "reduzir movimento"? [Completeness, Spec §FR-006]
- [x] CHK027 A legibilidade no tema escuro está coberta? [Gap → Spec §Casos de borda]

## Cobertura de cenários e bordas

- [x] CHK028 Evento sem endereço está coberto nas quatro telas? [Coverage, Spec §FR-008, §Casos de borda]
- [x] CHK029 Endereço longo está coberto com critério de "sem rolagem lateral" entre 320 e 430px? [Coverage, Spec §SC-002]
- [x] CHK030 Endereço que é nome de lugar e caracteres especiais estão cobertos? [Coverage, Spec §Casos de borda, §FR-009]
- [x] CHK031 O retorno ao sistema instalado na Tela de Início (sem barra de endereço) está coberto? [Coverage, Spec §Casos de borda]
- [x] CHK032 O uso no computador (tela larga) está coberto? [Coverage, Spec §Casos de borda]

## Mensurabilidade

- [x] CHK033 Os critérios de sucesso podem ser medidos sem saber a implementação (toques, larguras, endereço com acento)? [Measurability, Spec §SC-001–SC-003]

## Dependências e premissas

- [x] CHK034 A premissa de mostrar as três opções em todo aparelho está registrada e justificada? [Assumption, Spec §Premissas]
- [x] CHK035 A dependência do endereço já existir no payload, sem mudança no servidor, está registrada? [Dependency, Spec §Entidades]
