# Revisão de requisitos Checklist: Feature 298 — O formulário vira evento

**Propósito**: testar se os requisitos da 298 estão bem escritos, completos e coerentes entre si, nas
quatro áreas pedidas pelo dono: Home e visual; destino e vínculos; criar evento; permissões e dados.
Não testa código. Serve de portão antes do `/speckit-tasks`.
**Created**: 2026-09-10 · **Revisado**: 2026-09-11 (spec corrigida; 3 respostas do dono)
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md)

**Nota**: gerado pelo `/speckit-checklist` a partir da spec, do plano e dos contratos.
- **Profundidade**: normal.
- **Público**: o autor, antes das tarefas, e quem revisar o PR.
- **Referências**: `FR-`, `SC-` e `História N` apontam para a `spec.md`.
- **Portões da Manto**: ficam abertos até o fim do implement.
- **Itens de requisito**: cada item marcado aponta onde a spec passou a responder.

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

- [ ] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs)
- [ ] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo
- [ ] CHK003 `verify_298.py` verde contra `manto_local`, escrita conferida por conexão separada, um cenário que falha
- [ ] CHK004 Tela aberta de verdade; superfície pública em viewport mobile
- [ ] CHK005 Migration manual criada e aplicada no `manto_local` se `models.py` mudou; destrutiva ensaiada
- [ ] CHK006 `scripts/validar_startcommand.py` verde se tocou o `startCommand` do `render.yaml`
- [ ] CHK007 Gate de RBAC declarado em todo endpoint novo/alterado e linha em `docs/01` §4.3
- [ ] CHK008 Docs por fonte única: `docs/01`, `docs/02`, `docs/03` sempre; `00`/`04`/`05` se aplicável
- [ ] CHK009 Nível 1: `/speckit-converge` sem gaps
- [ ] CHK010 Antes de "em produção": `git status` limpo, `git log -1` = cabeçalho do `docs/03`, sonda `/api/`

## Home e visual — clareza e completude

- [x] CHK011 A posição da lista na Home está definida de forma única? A FR-005 dizia "dentro do bloco comercial" e o plano decide por um painel próprio logo depois de "Comercial". [Conflict] → FR-005: painel próprio logo depois de "Comercial".
- [x] CHK012 "Poucas linhas com 'ver todas'" está quantificado no requisito? [Clarity] → FR-005: 6 linhas por grupo e "Mostrar todas".
- [x] CHK013 A spec define qual cliente, qual data e qual cor representam uma linha que junta formulários diferentes da mesma cliente? [Gap] → FR-004 e História 3: vale o formulário que chegou por último.
- [x] CHK014 Está definido qual "há quantos dias chegou" aparece numa linha agrupada? [Gap] → FR-004: o do formulário que chegou por último.
- [x] CHK015 A prioridade visual está definida para quando várias marcas valem na mesma linha? [Gap] → FR-004: ordem fixa das marcas; sugestão numa faixa própria.
- [x] CHK016 A regra de contagem do "urgentes" no topo da Home está definida? [Ambiguity] → FR-005: conta os formulários das linhas vermelhas.
- [x] CHK017 O texto do estado vazio está especificado? [Clarity] → História 1 cenário 6 e FR-005: "Nenhum formulário esperando evento ✓".
- [x] CHK018 A ordem está definida quando dois formulários têm a mesma data informada? [Edge Case] → FR-003: o que chegou por último vem primeiro.
- [x] CHK019 Existem requisitos para a Home em tela estreita? [Gap] → FR-005: a linha quebra em duas, sem rolagem horizontal, com a ação principal visível.
- [x] CHK020 A urgência é comunicada também por texto, e não só pela cor? [Gap, Acessibilidade] → FR-004 e FR-005: distância em palavras ao lado da data.
- [x] CHK021 Está especificado o que a pessoa vê logo depois de agir numa linha e quando a Home reflete a mudança? [Clarity] → FR-018: some na hora para quem agiu; para os outros, na próxima atualização.
- [x] CHK022 "Organizada e fácil de ler de relance" tem um critério verificável? [Measurability] → SC-002 reescrito como regra objetiva: primeira linha = o formulário certo, com nome e data.

## Destino e vínculos — consistência e cobertura

- [x] CHK023 A spec diz o que acontece quando um formulário ENCERRADO é ligado a um evento? [Gap] → FR-002 e História 2 cenário 5: ligar desfaz o encerramento.
- [x] CHK024 A spec proíbe encerrar um formulário que já tem evento? [Gap] → FR-007 e História 2 cenário 6.
- [x] CHK025 "Desvincular" tem requisito próprio? [Gap] → FR-002, História 2 cenário 7 e casos de borda: volta à lista.
- [x] CHK026 Está definido se reabrir reacende o aviso do sino? [Gap] → FR-008 e FR-016: não reacende.
- [x] CHK027 A regra do plano "não emitir o aviso quando o formulário já chega ligado" está na spec? [Conflict] → FR-016 e História 6 cenário 5.
- [x] CHK028 A spec registra que ligar um formulário que já tem evento passa a ser recusado, e não trocado? [Consistency] → FR-018 e casos de borda.
- [x] CHK029 A mensagem e o comportamento de "já tem destino" estão definidos para cada ação? [Clarity] → FR-018: a mesma mensagem para todas as ações, com a lista atualizada.
- [x] CHK030 "Mostrar a divergência" de cliente tem lugar, texto e opções definidos? [Ambiguity] → decisão do dono (11/09); FR-015 e História 6 cenário 3: "usar a cliente do evento neste formulário".
- [x] CHK031 A spec define qual evento é sugerido quando há mais de um candidato? [Gap] → FR-010 e História 4 cenário 4: menor diferença; empate, o mais cedo.
- [x] CHK032 A spec exclui da sugestão os eventos cancelados, os ensaios e os agrupados? [Gap] → FR-010.
- [x] CHK033 Descartar uma sugestão pode ser desfeito? [Edge Case] → decisão do dono (11/09): definitivo; a ligação à mão continua possível (FR-010; fora de escopo).
- [x] CHK034 A spec cobre formulários repetidos de tipos diferentes? [Edge Case] → FR-009 e História 3 cenário 4.
- [x] CHK035 A spec deixa claro que o vínculo automático também leva a cliente e apaga o aviso, sem mudar a regra? [Consistency] → FR-011.
- [x] CHK036 O histórico de um encerramento desfeito é guardado? [Gap] → decisão do dono (11/09); FR-008: histórico de ações do sistema.

## Criar evento a partir do formulário — clareza e cobertura

- [x] CHK037 A spec lista o que fica de fora do evento? [Consistency] → FR-012: "Ficam só no formulário".
- [x] CHK038 A spec diz onde entram tema, espaço, aniversariante e personagens? [Gap] → FR-012: observações rotuladas; personagens também como sugestão de elenco.
- [x] CHK039 "Marcado para conferir" está definido? [Ambiguity] → FR-012: a marca é informativa; só a data suspeita exige confirmação.
- [x] CHK040 A regra do período → horário de fim está na spec? [Gap] → FR-013 e História 5 cenário 7: se não dá para ler sem ambiguidade, o fim fica em branco com o texto.
- [x] CHK041 As situações suspeitas cobrem hora ausente e período contraditório? [Coverage] → FR-013.
- [x] CHK042 A spec registra os dois formatos de formulário desde junho? [Gap, Assumption] → FR-012 e História 5.
- [x] CHK043 Está definido o que fazer quando a cliente não tem ficha? [Gap] → FR-012 e História 5 cenário 8.
- [x] CHK044 A spec diz que valor, vendedor e título não vêm do formulário? [Clarity] → FR-012 e História 5 cenário 9.
- [x] CHK045 O SC-006 tem denominador definido? [Measurability] → SC-006: os 7 campos listados.

## Permissões e dados — completude e coerência

- [x] CHK046 A ação principal de cada papel está definida na linha? [Gap] → FR-004 e História 1 cenário 7: "Criar evento" × "Abrir".
- [x] CHK047 O comportamento com a data de início vazia está definido? [Gap] → FR-001 e casos de borda: vale 01/06/2026.
- [x] CHK048 O cartão "Histórico" tem requisito para quando passa do limite de linhas? [Gap] → FR-017: aviso "mostrando os 200 mais recentes".
- [x] CHK049 A correção única dos avisos acesos hoje está na spec? [Gap] → FR-019.
- [x] CHK050 A spec trata de forma coerente o "Ver como"? [Consistency] → §RBAC: a Home respeita; a tela Formulários usa o papel real (dívida 3.5).

## Critérios de aceite e rastreabilidade

- [x] CHK051 Toda FR tem cenário no verify ou na conferência de tela? [Coverage] → cenário 13 (FR-017), cenário 14 (FR-016/018/011); estado vazio, tela estreita e FINANCEIRO na conferência de tela.
- [x] CHK052 O cabeçalho da spec reflete a tabela de sugestões descartadas? [Consistency] → cabeçalho e §Entidades.
- [x] CHK053 A numeração dos cenários do verify está coerente entre spec e plano? [Conflict] → verify renumerado para 16 cenários (o 15 deve falhar); plano e quickstart atualizados. Depois do `/speckit-analyze` (11/09), o 14 foi dividido em 14a e 14b: 17 linhas no total.

## Notas

- Marque como concluído: `[x]`
- Anote achados na própria linha
- Itens numerados em sequência para referência
- Os itens marcados `[Gap]`, `[Conflict]` e `[Ambiguity]` foram corrigidos na `spec.md` em 11/09,
  pelo Princípio VII, antes do `/speckit-tasks`. Os Portões (CHK001–CHK010) fecham no implement e no
  converge.
