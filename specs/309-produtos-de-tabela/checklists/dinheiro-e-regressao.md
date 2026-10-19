<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Dinheiro e regressão — Checklist: Produtos de tabela (309)

**Propósito**: testar a QUALIDADE dos requisitos da spec e do plano antes do implement — os números do
produto, a posição dele na conta, o teto das vagas, a volta dos especiais, o script dos tetos antigos, a
paridade de quem não usa produto e a janela de deploy. Portão de release; público: autor + revisor.
**Created**: 2026-10-19
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [research.md](../research.md) ·
[data-model.md](../data-model.md) · [contracts/api.md](../contracts/api.md)

**Nota**: gerado pelo `/speckit-checklist` a partir da spec, do plano e das tarefas.

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

- [ ] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs)
- [ ] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo
- [ ] CHK003 `verify_309.py` verde contra `manto_local`, escrita conferida por conexão separada, um cenário que falha
- [ ] CHK004 Tela aberta de verdade; superfície pública em viewport mobile (não se aplica: telas internas)
- [ ] CHK005 Migration manual criada e aplicada no `manto_local` se `models.py` mudou (não muda); destrutiva ensaiada
- [ ] CHK006 `scripts/validar_startcommand.py` verde se tocou o `startCommand` do `render.yaml` (não toca)
- [ ] CHK007 Gate de RBAC declarado em todo endpoint novo/alterado e linha em `docs/01` §4.3
- [ ] CHK008 Docs por fonte única: `docs/01`, `docs/02`, `docs/03` sempre; `00`/`04`/`05` se aplicável
- [ ] CHK009 Nível 1: `/speckit-converge` sem gaps
- [ ] CHK010 Antes de "em produção": `git status` limpo, `git log -1` = cabeçalho do `docs/03`, sonda `/api/`

## Números do produto (completude e clareza)

- [ ] CHK011 Os quatro preços da tabela de venda (2.500 / 3.600 normal; 5.000 / 6.500 em 24 e 25/12) estão escritos como valores exatos ao cliente, e a spec diz explicitamente que NÃO são 2.501 / 3.601 / 5.010 / 7.181? [Clarity, Spec FR-002, SC-001]
- [ ] CHK012 A regra "preço fixo por visita" define o que acontece em CADA coluna de duração (iguais nas quatro) e na régua >4h (`(total_4h − produtos_total) ÷ 4 × h + produtos_total`), nos três lugares que calculam `total_custom` (venda, prefill, `_total_da_duracao`)? [Completeness, Spec FR-004; Plan Restrições; Research D3]
- [ ] CHK013 A estimativa para produto sem preço na faixa está definida como fórmula fechada (Σ cachês 1h pela tabela NORMAL × `fator_cache` × `markup`), com exemplo numérico (6.600) e com os padrões 2,0 e 3,0 declarados como editáveis? [Clarity, Spec Clarifications 19/10, FR-019; Data-model §2]
- [ ] CHK014 Está escrito que a estimativa só vale para o PREÇO e que o teto das vagas continua pela tabela vigente na data (faixa), sem usar o fator? [Consistency, Spec FR-019 × FR-011]
- [ ] CHK015 O que o cliente vê quando o preço é estimado está especificado em todas as superfícies (memória, resultado, mensagem, PDF, aviso) com o texto "(estimativa)"? [Coverage, Spec Casos de borda, FR-019]
- [ ] CHK016 A unidade de `preco` (um escalar em R$, 2 casas, > 0, ≤ limite) e de `por_faixa.<faixa>.preco` estão definidas de forma idêntica? [Consistency, Data-model §1; Contracts POST /settings]

## Posição do produto na conta (consistência com 305/307/262)

- [ ] CHK017 A posição do produto ("depois de '= Após markup', antes de brinde, noturno, técnico, maquiador, transporte, acréscimos e NF") está escrita UMA vez como regra e as outras menções (fora de SP, NF, BV, PIX) só a referenciam, sem contradizê-la? [Consistency, Spec FR-004, FR-020; Research D2; Contracts]
- [ ] CHK018 A spec diz explicitamente que acréscimos % (BV com `valores_brl`), NF ÷ 0,84 e PIX −5 % incidem sobre o total COM o produto — e por que (conta inversa do evento, 305)? [Completeness, Spec FR-020; Research D2]
- [ ] CHK019 O comportamento do personalizado está definido para os DOIS critérios (valor final: digitado vence e a linha do produto sai da memória; multiplicador: `cache_base × mult + produtos_total`) e diz o que a memória mostra em cada um para continuar fechando com o total? [Completeness, Spec FR-008; Research D10]
- [ ] CHK020 O split do coordenador está escrito como UMA regra (`coordenadores_da_formula = max(qty, coord_produtos) − coord_produtos`) usada pela venda e pelo teto, com o caso "dois exemplares = dois coordenadores" e o caso "qty menor que o dos produtos" explicitados? [Clarity, Spec FR-006, Casos de borda; Research D11]
- [ ] CHK021 A regra da maquiagem define os três lados: o produto inclui a vaga Maquiador pela tabela, o preço do produto NÃO cobra make à parte, e make de avulso no mesmo orçamento cobra só o incremento (venda) e entra na vaga única (teto)? [Completeness, Spec FR-007, Casos de borda; Research D12]
- [ ] CHK022 O noturno embutido está definido para venda E teto (`inclui_noturno`), com a contagem de pessoas do noturno dos avulsos (performers + coordenadores da fórmula) explícita? [Consistency, Spec FR-005; Research D7]
- [ ] CHK023 Fora de SP está definido quanto a `num_going` (conta as pessoas do produto para a van) e à parcela por pessoa no teto das vagas do produto? [Completeness, Spec FR-020; Contracts item do teto]

## Teto das vagas (dinheiro do casting)

- [ ] CHK024 Os tetos esperados estão escritos por vaga e por data (600 / 270 / 250 / 250 normal; 1.000 / 650 / 500 / 250 na faixa) e a fonte de cada um ("pela tabela vigente na data", coluna 1h) está definida por tipo de vaga? [Clarity, Spec FR-011; Data-model §1 tabela de resolução]
- [ ] CHK025 "Flat" está definido de forma verificável (as quatro colunas iguais, `cache_custom` igual, a régua não escala a vaga do produto)? [Measurability, Spec FR-011, História 2]
- [ ] CHK026 A ordem de emissão (vagas dos produtos → avulsos → extras) está escrita como obrigatória nos DOIS caminhos (prefill e criação) e a razão (pareamento posicional) está registrada? [Consistency, Spec FR-011; Research D6]
- [ ] CHK027 O caso "produto apagado depois da venda" define comportamento distinto para venda (erro de validação nomeando o produto) e teto (vaga SEM teto com nota, nunca 0), inclusive para o vínculo 273? [Edge Case, Spec FR-011, História 4; Research D14]
- [ ] CHK028 Está escrito que o cachê da vaga continua nascendo vazio e que o casting continua rebaixado ao teto (236/238 intactas), e que NÃO há piso? [Consistency, Spec FR-011, Fora de escopo; Research D13]
- [ ] CHK029 O label de vaga `especial` que não existe na tabela tem comportamento definido (sem teto com nota; não é erro de save) coerente entre data-model, contratos e spec? [Consistency, Data-model §1; Contracts POST /settings]
- [ ] CHK030 A diferença "preço congelado no snapshot × teto recalculado da tabela viva na data do evento" está explícita, com o campo que congela (`snapshot.produtos[].preco_aplicado`, `produtos_total`)? [Clarity, Data-model §5; Casos de borda]

## Especiais 600/270, migração e script dos tetos antigos

- [ ] CHK031 A volta de "Papai Noel" a [600, 650, 675, 700] e de "Ajudante do Noel" a [270, 320, 345, 370] está escrita com os quatro valores e com a decisão do dono que a autoriza? [Completeness, Spec FR-012, Clarifications]
- [ ] CHK032 A remoção da troca automática 600→712 e a troca inversa guardada estão definidas com a condição EXATA de disparo ([712, 800, 850, 900] / [423, 480, 510, 540]) e o que acontece com um valor editado (intocado)? [Clarity, Spec FR-012, História 3; Research D9]
- [ ] CHK033 A consequência para o Noel avulso (2.210 com coordenador; 1.560 na linha dele) está escrita como comportamento esperado e coberta por aviso ("use o produto") — e o aviso tem condição clara (só sem produto)? [Completeness, Spec História 3, FR-012, Casos de borda]
- [ ] CHK034 Está explícito que os especiais NÃO são excluídos e por quê (teto 0 em orçamento pré-309 que vira evento)? [Clarity, Spec FR-012; Research D9]
- [ ] CHK035 O script dos tetos define seleção (nomes, tetos exatos 712/423, data ≥ 16/10), condição de correção (`cache_value` vazio E sem artista), o que faz com as demais (só relatório), a nota gravada e o modo dry-run por padrão? [Completeness, Spec FR-018, História 6; Contracts CLI]
- [ ] CHK036 A premissa "a produção ainda guarda Noel 600 cru; 712 só existia em memória" está registrada e tem efeito definido nos dois casos (tabela salva migrada ou não)? [Assumption, Research D9]

## Paridade e regressão

- [ ] CHK037 A paridade "payload sem `produtos` = conta de hoje" está definida como comparação chave a chave do quote, com a única exceção (Noel/Ajudante avulsos a 600/270) nomeada? [Measurability, Spec SC-003, História 7; verify cenário 1]
- [ ] CHK038 A neutralidade do EducaManto está definida pelo mecanismo (`pop` de `produtos` antes de calcular) e pela prova (totais iguais com e sem a chave, com a faixa provadamente ativa na venda)? [Completeness, Spec FR-016; verify cenário 16]
- [ ] CHK039 Está escrito quais afirmações do `verify_307.py` mudam (712 → 600; 2.501 → 2.210; 3.601 → 2.912; teto 712 → 600) e que a 305 segue em regressão? [Completeness, Spec FR-021; Research D17]
- [ ] CHK040 Orçamentos salvos antes da feature têm comportamento definido nas duas superfícies (histórico congelado; teto do evento criado depois recalculado da tabela nova)? [Coverage, Spec Casos de borda, FR-010]
- [ ] CHK041 O tipo novo de linha da memória (`produto`) está declarado nos dois lugares fechados do React (união de tipos e `FUNDO`) e a soma da memória com o total (hotfix 210) está mantida como invariante? [Consistency, Research D10; Plan Restrições]

## Validação do `POST /settings` e janela de deploy

- [ ] CHK042 Cada campo do bloco `produtos` e de `produtos_estimativa` tem regra e mensagem definidas, com a chave de erro no formato `produtos.<chave>.<campo>` (inclusive `vagas.<i>.…`)? [Completeness, Spec FR-013; Contracts tabela]
- [ ] CHK043 Está definido que o bloco enviado substitui o salvo, que corpo inválido não grava nada e que a chave `produtos` AUSENTE no corpo mantém o salvo (tela aberta desde antes do deploy)? [Clarity, Spec FR-013; Contracts]
- [ ] CHK044 A normalização defensiva na carga está escrita com o que é descartado (produto/vaga malformados, faixa inexistente) e com a garantia "nunca preço 0, nunca exceção dentro do `try` de `load()`"? [Edge Case, Spec Casos de borda; Data-model §1]
- [ ] CHK045 A janela de deploy (bundle novo × backend velho) tem comportamento definido do lado do React (botão travado quando há produto e `quote.produtos` ausente) e do lado do backend velho (chave ignorada, nunca preço 0 + noturno)? [Coverage, Spec FR-017; Research D1, D15]
- [ ] CHK046 A visibilidade dos cachês do produto para todo comercial via `/opcoes` está registrada como decisão consciente (não regressão) e como dívida a anotar no `docs/05`? [Assumption, Spec FR-015; Research D19]

## Ambiguidades e conflitos a resolver antes do implement

- [ ] CHK047 "Um Maquiador por produto" (dois exemplares = dois maquiadores) e "a vaga Maquiador do produto substitui a genérica" não conflitam quando há dois produtos E um avulso maquiado? [Ambiguity, Spec Casos de borda; Contracts item do teto]
- [ ] CHK048 O texto do aviso de coordenador ("N incluído(s) no produto") e a regra de que o campo "não desce abaixo do que os produtos trazem" estão coerentes com o payload (`coordenador_qty` enviado × total calculado no servidor)? [Consistency, Spec FR-006; Contracts avisos]
- [ ] CHK049 A descrição ao cliente ("visita padrão (até 1h)") e o rótulo da vaga ("Ajudante do Noel" mesmo para duende/elfo) estão fixados como premissas, com a consequência do vínculo 273 por nome registrada em Fora de escopo (alias)? [Assumption, Spec Premissas, Fora de escopo]
- [ ] CHK050 O esforço (6–7 noites) e as fatias estão ligados a cenários do verify que fecham cada fatia, para o `tasks.md` poder ordenar verify → núcleo → teto → telas → regressão? [Traceability, Research D20; Plan Resumo]
