# RBAC e Visibilidade — Checklist: Todo o comercial volta a ver e abrir o orçamento de qualquer colega

**Propósito**: testar se os **requisitos de autorização** da 301 estão completos, claros,
consistentes e mensuráveis — antes de virarem tarefas. Não testa se o código funciona: testa se o
que está escrito basta para alguém implementar sem inventar regra.
**Created**: 2026-09-21
**Feature**: [spec.md](../spec.md)

**Nota**: gerado pelo `/speckit-checklist` a partir da spec, do plano, da pesquisa e do contrato.

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

> Compartilhados com [regressao.md](./regressao.md) — rode uma vez só.

- [X] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs) — ✅ limpo nas três SPAs
- [X] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo — ✅ limpo nos 5 arquivos Python tocados + o verify
- [X] CHK003 `verify_301.py` verde contra `manto_local`, escrita conferida por conexão separada, um cenário que falha — ✅ 13/13; escrita por conexão separada nos cenários 5/7/9/10; **cinco** cenários que devem falhar
- [X] CHK004 Tela aberta de verdade; superfície pública em viewport mobile — ✅ `/orcamento/historico`, evento 390 e `/orcamento`, logada como COMERCIAL não-superadmin; feature não toca superfície pública
- [X] CHK005 Migration manual criada e aplicada no `manto_local` se `models.py` mudou; destrutiva ensaiada — — não se aplica: `models.py` não mudou, sem migration
- [X] CHK006 `scripts/validar_startcommand.py` verde se tocou o `startCommand` do `render.yaml` — — não se aplica: não tocou o `startCommand`
- [X] CHK007 Gate de RBAC declarado em todo endpoint novo/alterado e linha em `docs/01` §4.3 — ✅ blocos `RBAC:` criados em `orcamento_read`, `orcamento_write` e `agenda_read`; linhas de `_require_vendas()` e `_can_manage_sale()` atualizadas em `docs/01` §4.3
- [X] CHK008 Docs por fonte única: `docs/01`, `docs/02`, `docs/03` sempre; `00`/`04`/`05` se aplicável — ✅ `docs/01` §3.13 e §4.3, `docs/02` (histórico, picker e aba Comercial), `docs/03` (entrada no topo + índice)
- [X] CHK009 Nível 1: `/speckit-converge` sem gaps — ✅ **4 rodadas**: 8 → 2 → 2 → 1 lacuna confirmada, 5 derrubadas na refutação. As 13 foram fechadas (fases 7 a 10 do tasks.md). A 4ª só achou resíduo das próprias correções, e a classe recorrente (citação de linha deslocada) foi encerrada por medição, não por mais uma rodada
- [ ] CHK010 Antes de "em produção": `git status` limpo, `git log -1` = cabeçalho do `docs/03`, sonda `/api/` — ⬜ pendente — só na publicação

## Completude dos requisitos de autorização

- [x] CHK011 Para cada endpoint alterado, os requisitos separam **gate de módulo** de **checagem de dono**, em vez de falar em "permissão"? [Completeness, Spec §RBAC]
- [x] CHK012 Está especificado o que cada papel fora de COMERCIAL/SUPERADMIN recebe em cada endpoint tocado, e não só que "nada muda"? [Completeness, Spec §FR-008]
- [x] CHK013 Os requisitos definem quem pode excluir **e** o que a tela oferece a quem não pode — as duas metades? [Completeness, Spec §FR-006, §FR-007]
- [x] CHK014 Está especificado se a auditoria distingue o reenvio do próprio orçamento do reenvio de orçamento alheio? [Completeness, Spec §FR-013]
- [x] CHK015 Os requisitos dizem quais sinais de autorização o payload deve carregar, nomeando-os, em vez de deixar a escolha para a implementação? [Completeness, Spec §FR-007, §FR-009]

## Clareza e mensurabilidade

- [x] CHK016 "Pessoa autorizada no módulo" está definida em papéis concretos num lugar único, e não redescrita a cada requisito? [Clarity, Spec §FR-001–003]
- [x] CHK017 O requisito da mensagem de recusa especifica o **conteúdo mínimo** (motivo + quem pode agir) de forma que dê para dizer objetivamente se uma mensagem cumpre ou não? [Measurability, Spec §FR-010]
- [x] CHK018 "Setor comercial", "todo o comercial" e "pessoa autorizada no módulo" designam o mesmo conjunto, sem sobrar interpretação? [Ambiguity, Spec §Premissas]
- [x] CHK019 Os requisitos dizem **onde** cada decisão de autorização é tomada (servidor ou tela), sem deixar a escolha ao implementador? [Clarity, Spec §FR-007]
- [x] CHK020 O critério que decide quem manda no vínculo está escrito como regra única e enunciável — "o autor do orçamento já vinculado" — e não como lista de casos? [Clarity, Spec §FR-011]

## Consistência entre requisitos

- [x] CHK021 FR-001 ("todos veem") e FR-006 ("só o dono exclui") convivem sem se contradizer, com a fronteira leitura/escrita explícita? [Consistency, Spec §FR-001, §FR-006]
- [x] CHK022 FR-009 (ver o orçamento no evento) e FR-011 (não mexer no vínculo alheio) delimitam leitura e escrita sem zona cinzenta? [Consistency, Spec §FR-009, §FR-011]
- [x] CHK023 A tabela de RBAC da spec e o contrato de endpoints descrevem a **mesma** regra para os sete endpoints, sem divergência de redação? [Consistency, Spec §RBAC, contracts/api-endpoints.md]
- [x] CHK024 FR-008 ("o portão do módulo não muda") é consistente com o `PATCH .../orcamento`, que tem gate **diferente** e aceita FINANCEIRO? [Consistency, Spec §RBAC]

## Cobertura de cenários

- [x] CHK025 Existe requisito para o fluxo alternativo "o evento está vinculado ao orçamento do próprio usuário"? [Coverage, Spec §História 3]
- [x] CHK026 Existe requisito para "trocar de um orçamento meu para o orçamento de outra pessoa" — o caso em que o autor atual sou eu e o alvo não? [Coverage, Gap]
- [x] CHK027 Está especificado o que acontece quando o orçamento alvo simplesmente **não existe**, de forma distinta de "é de outra pessoa"? [Coverage, Spec §FR-010]
- [x] CHK028 Os requisitos cobrem o papel FINANCEIRO no bloco de venda do evento, que passa por um gate diferente do módulo de Orçamento? [Coverage, Spec §FR-009]

## Casos de borda e fluxos de exceção

- [x] CHK029 Está especificado o que deve acontecer se o e-mail for enviado com sucesso mas o registro de auditoria **não persistir**? [Gap, Exception Flow, Spec §FR-013]
- [x] CHK030 O requisito de autoria cobre o orçamento cujo autor não tem nome recuperável, sem deixar a regra de "quem pode" indefinida? [Edge Case, Spec §Casos de borda]
- [x] CHK031 Está especificado quem resolve quando a pessoa que vinculou o orçamento deixa de poder mexer nele logo em seguida? [Coverage, Spec §Casos de borda]

## Dependências e premissas

- [x] CHK032 A premissa "SUPERADMIN passa em tudo" está declarada, e não apenas assumida em cada requisito? [Assumption, Constituição §XIII]
- [x] CHK033 A premissa de que a trava do `DELETE` é decisão deliberada (e não sobra da regressão) está registrada com sua origem? [Assumption, Spec §Premissas]
- [x] CHK034 A dependência da regra de autorização em relação ao campo de autoria do registro está explícita, incluindo o que muda se esse campo passar a significar outra coisa? [Dependency, data-model.md]

## Resultado da avaliacao (2026-09-21)

Os 24 itens foram avaliados contra a spec **e contra o codigo**, com uma segunda passada
adversarial que tentava derrubar cada PASS. Resultado: **10 FAIL**, todos corrigidos na spec antes
de qualquer linha de codigo (Living Spec). O que cada um pegou:

| Item | O que estava errado | Correcao |
|---|---|---|
| CHK011, CHK023, CHK024 | O preambulo do §RBAC dizia que **todos** os sete endpoints mantem `_require_vendas()` e que FINANCEIRO leva 403. Falso para os dois de evento: `GET /api/events/<id>` usa `show_comercial` e `PATCH .../orcamento` usa `_can_manage_sale()` — os dois **aceitam** FINANCEIRO, e a propria tabela logo abaixo dizia isso | Preambulo reescrito listando os tres gates reais; FR-008 escopado ao modulo de Orcamento |
| CHK012, CHK018 | Ninguem dizia o que o FINANCEIRO recebe no `PATCH .../orcamento`. Como ele passa no gate e hoje so e barrado pelo 404-por-dono que a 301 remove, a feature **daria a ele** o poder de vincular orcamento alheio — contra §Fora de escopo e SC-005 | FR-011 e a linha da tabela passam a dizer "cai para COMERCIAL e SUPERADMIN"; T013 condiciona a remocao ao papel; cenario 12 do verify prova |
| CHK016 | "Pessoa autorizada no modulo", sujeito de FR-001 a FR-005, nunca era definida | Verbete no bloco *Vocabulario* |
| CHK017 | FR-010 era universal, mas os Casos de borda mandavam manter 404 no DELETE alheio — pessoa que **tem** o modulo, orcamento que **existe**. Contradicao | FR-010 reescrito com a excecao unica e deliberada, e o conteudo minimo da mensagem fixado |
| CHK029 | Ninguem dizia o que fazer se o e-mail sair e a gravacao da auditoria falhar | FR-013 ganhou o caminho de excecao: resposta continua 200, falha vai para o log |
| CHK030 | As regras dependiam do **nome** do autor, que a propria spec admite poder faltar | Casos de borda: a trava apoia-se sempre no `user_id`; sem nome, "Vendedor nao identificado" |
| CHK034 | Faltava a metade "o que muda se o campo de autoria passar a significar outra coisa" | Paragrafo de dependencia explicita no `data-model.md` |

Os outros 14 passaram a avaliacao e sobreviveram a tentativa de refutacao.

## Notas

- Marque como concluído: `[x]`
- Anote achados na própria linha
- O bloco "Portões da Manto" (CHK001–CHK010) é de **execução** e vem da constituição; os itens
  CHK011+ são de **qualidade dos requisitos** — leem a spec, não o código.
