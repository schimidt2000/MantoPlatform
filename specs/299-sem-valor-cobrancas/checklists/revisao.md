# Revisão de requisitos Checklist: Feature 299 — Sem valor e cobranças

**Propósito**: testar se os requisitos da 299 estão bem escritos, completos e coerentes entre si, em
quatro áreas:
- Home e visual;
- cobrança, grupo e dinheiro;
- valor a definir e comissão;
- permissões, dados e deploy.

Não testa código. Serve de portão antes do `/speckit-tasks`.

**Created**: 2026-09-14 · **Revisado**: 2026-09-14 (spec corrigida; 4 respostas do dono)
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md)

**Nota**: gerado pelo `/speckit-checklist` a partir da spec, do plano e dos contratos.
- **Como foi feito**: 4 revisores, um por área. Cada item foi conferido no texto da spec por um
  verificador independente, e os duplicados entre áreas foram unidos.
- **Profundidade**: normal.
- **Público**: o autor, antes das tarefas, e quem revisar o PR.
- **Referências**: `FR-`, `SC-` e `História N` apontam para a `spec.md`.
- **Portões da Manto**: ficam abertos até o fim do implement.
- **Itens de requisito**: cada item marcado aponta onde a spec passou a responder. "Dono" marca uma
  resposta do dono em 14/09.

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

- [ ] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs)
- [ ] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo
- [ ] CHK003 `verify_299.py` verde contra `manto_local`, escrita conferida por conexão separada, um cenário que falha
- [ ] CHK004 Tela aberta de verdade; superfície pública em viewport mobile
- [ ] CHK005 Migration manual criada e aplicada no `manto_local` se `models.py` mudou; destrutiva ensaiada
- [ ] CHK006 `scripts/validar_startcommand.py` verde se tocou o `startCommand` do `render.yaml`
- [ ] CHK007 Gate de RBAC declarado em todo endpoint novo/alterado e linha em `docs/01` §4.3
- [ ] CHK008 Docs por fonte única: `docs/01`, `docs/02`, `docs/03` sempre; `00`/`04`/`05` se aplicável
- [ ] CHK009 Nível 1: `/speckit-converge` sem gaps
- [ ] CHK010 Antes de "em produção": `git status` limpo, `git log -1` = cabeçalho do `docs/03`, sonda `/api/`

## Home e visual — clareza e completude

- [x] CHK011 A cor e o selo de uma venda com sinal pendente cujo saldo venceu ou vence em até 2 dias estão definidos sem conflito? [Conflict] → Dono; FR-026: vermelho, selo do prazo e nota "sem sinal"; História 4 cenários 14 e 15.
- [x] CHK012 Está definido onde fica na lista a venda que ainda não pagou o sinal? [Ambiguity] → Dono; FR-026: ordem por cor e, dentro da cor, pelo vencimento; História 4 cenário 6.
- [x] CHK013 A spec define o número dos cards e se a soma deles bate com o total do topo? [Gap] → Dono; FR-028 e FR-029: o card mostra só as linhas para agir; SC-009; História 5 cenário 4.
- [x] CHK014 Está definido como aparece o evento com valor R$ 0,00 sem cortesia? [Conflict] → Vocabulário "A definir"; FR-007 e FR-015; História 2 cenário 11.
- [x] CHK015 O limite de 6 linhas vale para o painel ou para cada grupo? [Ambiguity] → FR-028: 6 por lista ou grupo; Cobranças é uma lista só.
- [x] CHK016 Está definido o que a Home mostra quando uma lista não carrega? [Gap] → FR-032 e casos de borda: aviso com "Tentar de novo", nunca o "✓".
- [x] CHK017 Está claro como a linha de um grupo se identifica e se a contagem inclui cancelados? [Ambiguity] → FR-007 e FR-024: a cliente e a marca "grupo de N eventos", contando os não cancelados.
- [x] CHK018 Está definido em que parte da lista "Sem valor" entra o evento de hoje, e com que palavra? [Edge Case] → FR-008 e FR-009; História 2 cenário 10.
- [x] CHK019 A ação do FINANCEIRO ("Abrir") é coerente com ele poder aplicar orçamento? [Conflict] → FR-007 e FR-018: "Abrir" na linha, e o orçamento continua com quem aplica hoje; §RBAC.
- [x] CHK020 Existe texto de vazio para Cobranças e para o card? [Gap] → FR-032: "Nenhuma cobrança em aberto ✓" e "Em dia ✓".
- [x] CHK021 Está definido quando a linha resolvida sai e se a cobrança quitada também sai com animação? [Gap] → FR-010; História 2 cenário 7.
- [x] CHK022 "A urgência também em palavras" está definida, e a cor nunca é o único sinal? [Ambiguity, Acessibilidade] → FR-009 (distância em palavras) e FR-025 (selos com a distância).
- [x] CHK023 Há critério para o celular além de "sem rolagem horizontal"? [Measurability] → FR-030: a linha pode quebrar, nada é escondido e a ação fica visível; SC-010.
- [x] CHK024 Está claro qual texto é o selo e qual é o vencimento, sem repetir a mesma informação? [Ambiguity] → FR-024 (a data do vencimento) e FR-025 (o selo, com a distância); História 4 cenários 1–3.
- [x] CHK025 As réguas de cor das duas listas têm limites em número, sem buraco nem sobreposição? [Measurability] → FR-009 e FR-026; Clarifications; Premissas.
- [x] CHK026 O FR-029, a História 5 e o SC-009 concordam sobre o total do topo e o "R$ X em aberto"? [Consistency] → FR-029, História 5 e SC-009.

## Cobrança, grupo e dinheiro — consistência e cobertura

- [x] CHK027 A premissa de que a cliente do 344 "já pagou" está sustentada, se o 344 também está entre os recebidos acima do valor? [Assumption] → Dono; §Antes da publicação: o 344 e os 5 outros casos grandes são conferidos antes do deploy; História 1.
- [x] CHK028 Está claro o que faz uma parcela contar como "não coberta" e o que vale quando todas estão cobertas? [Ambiguity] → FR-021 item 2: cobertura pelo recebido do grupo, pela ordem das datas; senão, o item 3; História 4 cenário 16.
- [x] CHK029 A spec cobre as vendas recentes com comprovante sem valor e o que a Home mostra até a limpeza? [Coverage] → Dono; casos de borda e §Antes da publicação: contam R$ 0 e são listadas e conferidas antes do deploy.
- [x] CHK030 Na venda parcelada, está claro se a cobrança pede a parcela ou o saldo, e o que vale se as parcelas não somam o valor? [Gap] → Vocabulário "Saldo" e casos de borda: pede o saldo; as parcelas só dão a data.
- [x] CHK031 A regra da metade vale para a venda parcelada com datas acertadas? [Gap] → FR-022: o cronograma substitui a regra da metade, como a data combinada; a faturada sem data combinada segue a regra.
- [x] CHK032 Está claro, num grupo, se as exclusões valem pelo principal e se o compromisso interno entra na data do grupo? [Ambiguity] → FR-002, FR-006 e FR-019 (pelo principal); casos de borda "Compromisso interno agrupado".
- [x] CHK033 A spec diz o que acontece com a venda fechada depois do prazo dos 2 dias? [Edge Case] → FR-021: o vencimento nunca fica antes da data da venda; História 4 cenário 15.
- [x] CHK034 A spec cobre o principal apagado pela sincronização do Google? [Edge Case] → casos de borda: os outros eventos aparecem, um a um, em "Sem valor".
- [x] CHK035 A spec diz quando a mensagem de cobrança é oferecida na página do evento? [Gap] → FR-003: só no principal ou avulso, a partir do vencimento, nunca em cortesia, simbólico ou sem valor; História 1 cenário 6.
- [x] CHK036 A folga de centavos vale na página do evento? [Ambiguity] → FR-003 e FR-023: aparece "Quitado"; História 1 cenário 7.
- [x] CHK037 A exclusão da Loja Virtual está justificada e o SC-005 a ressalva? [Assumption, Conflict] → Vocabulário, Premissas, FR-006, FR-019 e SC-005.
- [x] CHK038 A spec define o valor, o recebido e os cancelados do grupo, e o principal cortesia, cancelado ou simbólico? [Completeness] → FR-001, FR-004, FR-006 e casos de borda.
- [x] CHK039 Está clara a ordem do vencimento e que a data combinada substitui a regra da metade? [Clarity] → FR-021, FR-022; Clarifications do plan; História 4 cenários 12 e 13.

## Valor a definir e comissão — clareza e cobertura

- [x] CHK040 A spec define se o cadastro aceita valor abaixo de R$ 1,00 sem a marca, e o SC-008 tem requisito que o sustente? [Conflict] → Dono; FR-012, FR-013 e FR-014: recusa, salvo o evento que já tem esse valor e não o muda; SC-008 com conferência 30 dias depois.
- [x] CHK041 Está definido o ciclo da comissão da venda de R$ 0,01 que ganha valor depois? [Gap] → FR-031: inclui a venda que passa de sem valor para valor real num mês posterior.
- [x] CHK042 Está definido o que acontece com a comissão já paga quando o valor é apagado e reposto? [Gap] → FR-031 e casos de borda: nunca é paga de novo nem alterada.
- [x] CHK043 Está definida a data da venda do evento importado do Google quando ele ganha valor? [Gap] → FR-017: o dia em que o valor é posto, como hoje.
- [x] CHK044 O FR-013 e o caso de borda do R$ 0,01 concordam sobre como esse evento abre na edição? [Conflict] → FR-013 (vazio ou zero abre marcado; simbólico abre desmarcado) e casos de borda; História 3 cenário 8.
- [x] CHK045 O vendedor obrigatório vale também na edição completa e no importado do Google? [Ambiguity] → FR-016: sim, exceto no outro evento de um grupo; História 3 cenário 3.
- [x] CHK046 O "A definir" vale também para o quadrinho "Venda" do lucro? [Ambiguity] → FR-015: não; ele continua mostrando o número, porque é indicador financeiro.
- [x] CHK047 Está claro em que ciclo entra a comissão quando o valor é posto num mês posterior? [Clarity] → FR-031; Clarifications do plan; História 3 cenário 7.
- [x] CHK048 A marca "Valor a definir" é só o valor vazio, e a relação dela com a cortesia está clara? [Completeness] → FR-012 (a cortesia vence a marca) e Premissas.
- [x] CHK049 A data da venda fica a do cadastro quando o valor chega depois ou a edição deixa o campo vazio? [Coverage] → FR-017; História 3 cenário 7.
- [x] CHK050 O orçamento pode ser aplicado sobre o R$ 0,01, inclusive no aviso do Google? [Coverage] → FR-018; História 3 cenário 6.
- [x] CHK051 A spec define o retorno ao salvar sem valor e sem a marca, com o foco e o Salvar sempre ativo? [Non-functional] → FR-014 (os campos de valor e o texto da explicação); História 3 cenário 2.

## Permissões, dados e deploy — completude e mensurabilidade

- [x] CHK052 O corte é a data fixa 01/06/2026 ou a data de início das configurações? [Ambiguity] → Vocabulário "Data de início", FR-005, FR-019 e Premissas: segue a configuração, com 01/06/2026 de reserva.
- [x] CHK053 O FR-031 vale para as comissões que nasceram atrasadas antes da publicação? [Gap] → FR-031 e Fora de escopo: só para as que nascerem ou mudarem depois.
- [x] CHK054 A convivência das duas versões no deploy está definida nos dois sentidos, com critério conferível? [Gap] → casos de borda "Deploy", SC-011 e verify cenário 13 (chaves antigas presentes).
- [x] CHK055 O cenário de autorização cobre as regras de acesso que a spec declara? [Coverage] → verify cenário 16 (Home, detalhe, criar, editar, com o controle do FINANCEIRO) e a conferência de tela ("Abrir").
- [x] CHK056 Todo requisito que não é só de tela tem cenário no verify? [Coverage] → tabela ampliada: FR-002 (1, 8), FR-004 (8), FR-008 (2), FR-016 e FR-017 (5), FR-018 (6), FR-019 (12) e os casos de borda do grupo (3, 6).
- [x] CHK057 A seção RBAC nomeia os papéis e lista todas as rotas que mudam, e os docs acompanham? [Completeness] → §RBAC (as quatro rotas, com os papéis) e §Docs a atualizar (o `docs/01` com o orçamento e o §4.3).
- [x] CHK058 O Fora de escopo e o FR-031 concordam sobre o que muda na comissão, e os docs registram? [Consistency] → Fora de escopo ("a única mudança é o ciclo do FR-031") e o `docs/04` (ciclo da comissão tardia).
- [x] CHK059 O SC-001 e o SC-004 têm linha de base conferível? [Measurability] → SC-001 (a mesma consulta de 14/09) e SC-004 (as 2 + 3 linhas explicadas).
- [x] CHK060 A spec registra a mudança que a equipe verá no dia e quem avisa? [Dependency] → §Antes da publicação: texto do aviso no `quickstart.md`, e o dono decide quem envia.
- [x] CHK061 Está claro que o Financeiro e os relatórios mostram outra conta nos grupos, e que isso é aceito? [Clarity] → Clarifications (specify), FR-003, Fora de escopo e §Docs (`docs/05`).

## Notas

- Marque como concluído: `[x]`
- Anote achados na própria linha
- Itens numerados em sequência para referência
- Os itens `[Gap]`, `[Conflict]` e `[Ambiguity]` foram corrigidos na `spec.md` em 14/09, pelo
  Princípio VII, antes do `/speckit-tasks`. Quatro deles vieram de respostas do dono: CHK011/012,
  CHK013, CHK040 e CHK027/029. Os outros seguem o plano, a 298 ou a constituição.
- Os Portões (CHK001–CHK010) fecham no implement e no converge.
