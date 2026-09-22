# Prevenção de Regressão — Checklist: Todo o comercial volta a ver e abrir o orçamento de qualquer colega

**Propósito**: testar se os requisitos da 301 dizem o bastante para que (a) a regra **não volte a
se perder** numa próxima reescrita e (b) todos os vizinhos que herdaram a trava estejam
explicitamente dentro ou fora do escopo. Esta feature existe porque esses dois buracos ficaram
abertos em julho — o checklist trata isso como risco conhecido, não hipotético.
**Created**: 2026-09-21
**Feature**: [spec.md](../spec.md)

**Nota**: gerado pelo `/speckit-checklist` a partir da spec, do plano, da pesquisa e do contrato.

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

> Compartilhados com [rbac.md](./rbac.md) — rode uma vez só.

- [X] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs) — ✅ limpo nas três SPAs
- [X] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo — ✅ limpo nos 5 arquivos Python tocados + o verify
- [X] CHK003 `verify_301.py` verde contra `manto_local`, escrita conferida por conexão separada, um cenário que falha — ✅ 13/13; escrita por conexão separada nos cenários 5/7/9/10; **cinco** cenários que devem falhar
- [X] CHK004 Tela aberta de verdade; superfície pública em viewport mobile — ✅ `/orcamento/historico`, evento 390 e `/orcamento`, logada como COMERCIAL não-superadmin; feature não toca superfície pública
- [X] CHK005 Migration manual criada e aplicada no `manto_local` se `models.py` mudou; destrutiva ensaiada — — não se aplica: `models.py` não mudou, sem migration
- [X] CHK006 `scripts/validar_startcommand.py` verde se tocou o `startCommand` do `render.yaml` — — não se aplica: não tocou o `startCommand`
- [X] CHK007 Gate de RBAC declarado em todo endpoint novo/alterado e linha em `docs/01` §4.3 — ✅ blocos `RBAC:` criados em `orcamento_read`, `orcamento_write` e `agenda_read`; linhas de `_require_vendas()` e `_can_manage_sale()` atualizadas em `docs/01` §4.3
- [X] CHK008 Docs por fonte única: `docs/01`, `docs/02`, `docs/03` sempre; `00`/`04`/`05` se aplicável — ✅ `docs/01` §3.13 e §4.3, `docs/02` (histórico, picker e aba Comercial), `docs/03` (entrada no topo + índice)
- [ ] CHK009 Nível 1: `/speckit-converge` sem gaps — ⬜ pendente — `/speckit-converge` ainda não rodou
- [ ] CHK010 Antes de "em produção": `git status` limpo, `git log -1` = cabeçalho do `docs/03`, sonda `/api/` — ⬜ pendente — só na publicação

## Durabilidade da regra (o que impede a volta)

- [x] CHK011 Os requisitos nomeiam **onde** a regra vigente passa a morar, de modo que exista fonte única para consultar numa reescrita futura? [Traceability, Spec §FR-014]
- [x] CHK012 Existe requisito exigindo **corrigir** os textos que hoje ensinam a regra errada, e não apenas escrever a regra nova em outro lugar? [Completeness, Spec §FR-014]
- [x] CHK013 A cobertura de "textos que ensinam a regra" inclui comentários e docstrings de código, ou se limita à documentação oficial? [Coverage, Gap, research.md R6]
- [x] CHK014 Os requisitos dizem o que uma reescrita futura deve fazer quando **discordar** do contrato — conferir e atualizar, ou seguir o contrato? [Gap, contracts/api-endpoints.md]
- [x] CHK015 A causa da regressão está descrita com precisão suficiente para alguém **reconhecer o mesmo padrão** em outra migração, e não só para entender este caso? [Clarity, Spec §O pedido]
- [x] CHK016 A spec registra a **extensão** do estrago (duração e quantos domínios foram alcançados) — a informação que dimensiona o risco de repetição? [Completeness, Spec §O pedido]

## Cobertura dos vizinhos que herdaram a trava

- [x] CHK017 Cada superfície que herdou a restrição aparece explicitamente **dentro** ou **fora** do escopo, sem nenhuma ficar sem menção? [Coverage, Spec §Fora de escopo]
- [x] CHK018 Os requisitos distinguem o que escapa **por decisão registrada** do que escapava **por regressão** — para que o próximo leitor não "conserte" o que é intencional? [Clarity, Spec §Fora de escopo]
- [x] CHK019 Está registrado que existem endpoints que **nunca** tiveram a trava, de forma que ninguém os altere por simetria? [Coverage, contracts/api-endpoints.md]
- [x] CHK020 A busca de orçamento usada pela aba Comercial está tratada como consumidora do mesmo requisito da lista, e não esquecida por ter tela própria? [Coverage, research.md R6]
- [x] CHK021 Os requisitos cobrem o módulo vizinho que **já** tinha o comportamento correto, dizendo explicitamente que fica como está? [Coverage, Spec §Fora de escopo]

## Sinais que podem reintroduzir a regra

- [x] CHK022 Existe requisito sobre o destino de sinais de autorização que deixam de ser usados — remover ou manter? [Gap, research.md R5]
- [x] CHK023 Há requisito que proíba a tela de **deduzir** permissão da ausência de dado no payload, e não só que mande a flag certa? [Completeness, Spec §FR-007, research.md R3]
- [x] CHK024 A spec registra as alternativas **recusadas** pelo dono, para o `/speckit-implement` não reintroduzi-las como "melhoria óbvia"? [Completeness, Spec §Fora de escopo]

## Qualidade da verificação como rede de segurança

- [x] CHK025 Os cenários de verificação incluem um que **falharia** se a trava de leitura voltasse? [Coverage, Spec §Verificação]
- [x] CHK026 Os cenários incluem um que **falharia** se a trava de escrita fosse removida junto com a de leitura — o erro simétrico mais provável? [Coverage, Spec §Verificação]
- [x] CHK027 Os critérios de sucesso permitem **detectar a regressão voltando** depois, ou só medem a entrega desta vez? [Measurability, Spec §Critérios de sucesso]
- [x] CHK028 Os cenários que devem falhar estão marcados como tal, distinguindo "falha esperada" de "verify quebrado"? [Clarity, Spec §Verificação]

## Premissas sobre o estado atual

- [x] CHK029 Os números do espelho usados para decidir (volume, concentração, papéis) estão **datados e com fonte**, já que envelhecem? [Assumption, Spec §Casos de borda, research.md R8]
- [x] CHK030 A premissa de que remover um sinal do payload é seguro está acompanhada de como isso foi confirmado? [Assumption, research.md R5]
- [x] CHK031 Os requisitos de documentação nomeiam **seções específicas**, em vez de dizer "atualizar os docs"? [Clarity, Spec §Docs a atualizar]
- [x] CHK032 Existe requisito para que o registro histórico da mudança guarde a relação **causa → efeito** (qual mudança anterior criou o problema), e não só o que foi feito agora? [Traceability, Spec §Docs a atualizar]

## Resultado da avaliacao (2026-09-21)

Os 22 itens foram avaliados contra a spec **e contra o codigo**, com segunda passada adversarial.
Resultado: **5 FAIL**, todos corrigidos antes do codigo:

| Item | O que estava errado | Correcao |
|---|---|---|
| CHK012 | FR-014 so mandava **escrever** a regra nova em `docs/01`. Nenhum requisito mandava **corrigir** os quatro textos que hoje ensinam a regra antiga, nem marcar o contrato da 177 — que foi quem reimportou a restricao | **FR-015** novo, nomeando os quatro textos; T025 nova para a nota no contrato da 177 |
| CHK016 | A spec nunca registrava a **duracao** da regressao, e a contagem de dominios divergia entre spec ("dois dominios") e contrato ("outros dois dominios") | §O pedido ganhou "dois meses, tres superficies em dois dominios"; contrato alinhado |
| CHK022, CHK030 | `research.md` R5 afirmava, como prova, que o endpoint tinha **dois** consumidores. Tem **tres**: faltava `OrcamentoCalculadoraPage.tsx:120`, que alimenta o selo de contagem do link do historico. Consequencia nao registrada: o selo passa a contar o time e satura em 300 | R5, contrato e plano corrigidos (leitor unico **da chave**, tres consumidores do **endpoint**); efeito registrado nos Casos de borda; T019 passa a conferir a tela da calculadora |
| CHK026 | O cenario 10 nao era discriminante: a guarda 409 de evento vivo recusaria igual, entao ele passaria verde mesmo com a trava de autoria solta — justamente o erro simetrico que ele existe para pegar | Cenario 10 ganhou arranjo obrigatorio (orcamento **sem** evento vivo), resultado fixado em **404** e contraste (A apaga o mesmo e conclui 200) |

Os outros 17 passaram e sobreviveram a refutacao.

## Notas

- Marque como concluído: `[x]`
- Anote achados na própria linha
- O bloco "Portões da Manto" (CHK001–CHK010) é de **execução** e vem da constituição; os itens
  CHK011+ são de **qualidade dos requisitos** — leem a spec, não o código.
