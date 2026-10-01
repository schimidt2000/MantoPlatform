# Integridade Checklist: o que o sync pode e não pode apagar

**Propósito**: testar se os requisitos da trava estão **escritos** de forma completa e inequívoca —
a regra de "com dinheiro", a confirmação da ausência no Google, a mudança de data, a unidade de
trabalho da limpeza, a entrada e a saída da marca e a trava de escrita fora da produção. Não testa
se o código funciona; isso é o `verify_303.py`.
**Created**: 2026-09-30
**Feature**: [spec.md](../spec.md)

**Nota**: gerado pelo `/speckit-checklist` a partir da spec, do plano, da pesquisa (`research.md`),
do modelo de dados e do contrato. Portão antes do `/speckit-tasks`. Avaliado em 30/09 por dois
agentes só de leitura e um revisor adversarial, contra os documentos e o código; cada lacuna
confirmada foi corrigida no documento indicado na própria linha.

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

- [ ] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs)
- [ ] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo
- [ ] CHK003 `verify_303.py` verde contra `manto_local`, escrita conferida por conexão separada, um cenário que falha
- [ ] CHK004 Tela aberta de verdade; superfície pública em viewport mobile
- [ ] CHK005 Migration manual `a7c3e91f4d28` criada e aplicada no `manto_local` (aditiva — sem ensaio destrutivo)
- [x] CHK006 ~~`validar_startcommand.py`~~ — **não se aplica**: não toca `render.yaml`
- [ ] CHK007 Gate de RBAC declarado em todo endpoint novo/alterado e linha em `docs/01` §4.3
- [ ] CHK008 Docs por fonte única: `docs/01`, `docs/02`, `docs/03` sempre; `00`/`04`/`05` se aplicável
- [ ] CHK009 Nível 1: `/speckit-converge` sem gaps
- [ ] CHK010 Antes de "em produção": `git status` limpo, `git log -1` = cabeçalho do `docs/03`, sonda `/api/`

## A regra de "com dinheiro"

- [x] CHK011 Cada critério que faz o evento ficar (venda, comprovante, contrato, escalado, grupo) está definido de modo conferível — venda "maior que zero", comprovante "pela existência", escalado "vaga com talento"? [Clarity, Spec §FR-001 + §Premissas, Research R2]
- [x] CHK012 A exceção do técnico de som está delimitada pelos três lados (só em SHOW, só a vaga que o sistema cria, só com o técnico padrão), com os contra-casos nomeados? [Clarity, Spec §FR-001 + §Clarifications, Research R2] — o quarto lado proposto (sem cachê nem pagamento) foi recusado pelo dono (CHK049)
- [x] CHK013 Está enumerado o que **não** segura o evento e é apagado junto com ele (reembolso, nota, presente 3D — e anexos, formulário do cliente, orçamento vinculado, figurino)? [Completeness, Spec §Fora de escopo, Gap] — **corrigido**: lista fechada em Spec §Fora de escopo (o que sai, o que só é desvinculado)
- [x] CHK014 "Evento vazio" tem a mesma definição na FR-001, na FR-007, no cenário de aceite 3 da História 1 e no cenário 7 do verify? [Consistency]
- [x] CHK015 As diferenças entre esta regra e a do botão Excluir da 224 estão declaradas, com a afirmação de que a da 224 não muda? [Consistency, Spec §Premissas, Research R2]
- [x] CHK016 Está definido o que acontece com um evento **marcado** que fica vazio depois (a equipe tira a venda e a escala enquanto ele está marcado)? [Edge Case, Gap] — **corrigido**: caso de borda novo (continua marcado; sai devolvendo e então excluindo) e Quickstart §6

## Ausência confirmada

- [x] CHK017 Toda resposta possível do Google a uma consulta individual cai em exatamente um dos três desfechos (404, 410, cancelado completo, cancelado mínimo, 401/403/429, 5xx, tempo esgotado, sem credencial, falha ao renovar, item sem início, série recorrente)? [Completeness, Spec §FR-003, Research R3] — a partição já era fechada; a lista de `motivo` passou a ser fechada em R3 e no contrato
- [x] CHK018 A ordem "olhar a situação antes de olhar o início" está escrita como requisito, com o motivo (a sonda de 30/09)? [Clarity, Research R3 + R17]
- [x] CHK019 Está declarado que "ausente" só tem efeito destrutivo depois de a **lista** do mês ter respondido, e que na reconferência e no "Sincronizar" é inofensivo? [Completeness, Research R3]
- [x] CHK020 "Rodada", na FR-040, está definida — um mês, a reconferência, ou o ciclo inteiro (reconferência + todos os meses)? [Ambiguity, Spec §FR-040, Research R4 + R12] — **corrigido**: rodada = a limpeza de um mês ou a reconferência; disjuntor local da chamada (FR-040, R4); variante "dois meses seguidos" no cenário 13
- [x] CHK021 Está dito quais classes de inconclusivo abrem o disjuntor e quais não (403 e 429 de um evento só), e por quê? [Clarity, Research R4] — **corrigido**: R4 e contrato §Google; variante no cenário 13
- [x] CHK022 Há requisito sobre o evento que fica inconclusivo **ciclo após ciclo** (nunca apagado, nunca marcado): onde isso aparece para alguém? [Coverage, Gap] — **corrigido**: totais no resumo do ciclo (FR-042, Data model §Rastro); aviso próprio fica como dívida
- [x] CHK023 A premissa sobre o que o Google responde por um evento apagado está datada, com a amostra, e os modos não observados (404, 410, resposta mínima) são tratados mesmo assim? [Assumption, Spec §Premissas, Research R17]
- [x] CHK024 Evento movido para outro calendário: o requisito diz o que o sistema **faz** (marca ou apaga, pela mesma regra), além do que a tela diz? [Clarity, Spec §Casos de borda] — frase acrescentada ao caso de borda

## Mudança de data

- [x] CHK025 Os campos comparados para decidir "mudou" estão listados, e está dito como se normalizam (fuso, dia inteiro, vazio × nulo) para a comparação não dar "mudou" para sempre? [Clarity, Research R5, Gap] — **corrigido**: R5 "Como comparar" (pelos valores que `sync_events` gravaria; uma função só) e variante no cenário 8
- [x] CHK026 O destino fora do alcance do ciclo (mês passado; além do horizonte) tem requisito e cenário próprios? [Coverage, Spec §FR-002, cenário 8]
- [x] CHK027 A FR-041 diz onde o "registra quantos" fica e com que frequência, para não virar uma linha de auditoria a cada 10 minutos? [Measurability, Spec §FR-041, Research R5, Data model §Rastro]
- [x] CHK028 Está definido o que acontece quando o evento está marcado **e** reaparece com outra data ou em outro mês? [Coverage, Spec §História 5, Research R12] — **corrigido**: caso de borda novo e FR-006 (vale o Google; só a devolução faz valer o sistema); variante no cenário 9

## Unidade de trabalho e concorrência

- [x] CHK029 A unidade de trabalho (um evento = uma gravação) está escrita como requisito, com o comportamento na falha — o erro de um evento não para os outros e é contado? [Completeness, Research R4, Spec §FR-042]
- [x] CHK030 "Marca e aviso nascem juntos" está definido com o que acontece na falha parcial (o aviso falha → a marca não fica)? [Clarity, Spec §FR-010, Research R6] — já estava (R6 + R4); ganhou cenário próprio, o 13b
- [x] CHK031 A corrida entre o ciclo automático e o "Limpar eventos fantasma" tem resultado exigido e conferível (uma marca, um aviso)? [Measurability, Spec §Casos de borda, Research R6] — **corrigido**: cenário 2b (o ramo perdedor da marca não era exercitado)
- [x] CHK032 A corrida entre "Devolver ao Google" e o ciclo automático está tratada — o evento recém-criado no Google ser visto pelo sync antes de o sistema gravar o id novo? [Coverage, Gap, Research R13] — **corrigido**: R13 "Corrida com o ciclo" (a guarda da 254 cobre; nada lento entre o insert e o commit); de carona, "10a a 10j" → "10a a 10i"
- [x] CHK033 O `rollback` novo no erro de um mês está declarado como mudança de comportamento, dizendo o que deixa de ser gravado? [Completeness, Plano §Rastreamento de complexidade] — **corrigido, com mudança de desenho**: o `rollback` vale só para erro de banco; em qualquer exceção ele repetiria e-mails ao elenco a cada ciclo (Plano §Rastreamento, Research §Riscos, cenário 13c)
- [x] CHK034 Está dito o que acontece com um evento que sai por outro caminho no meio da limpeza (relido e não achado não é falha)? [Edge Case, Research R4]

## A marca: entrada, saída e custo

- [x] CHK035 Os caminhos pelos quais a marca sai estão enumerados e batem entre a spec, o modelo de dados e a pesquisa? [Consistency, Spec §FR-006/FR-012/FR-039, Data model §Transições, Research R12]
- [x] CHK036 Está declarado que só um ponto grava a marca e só um a retira, e que o sync comum nunca mexe nela? [Completeness, Data model §Invariantes]
- [x] CHK037 O custo da reconferência (uma consulta ao Google por evento marcado a cada 10 minutos, enquanto o evento cancelado de verdade espera a segunda entrega) está quantificado ou aceito? [Non-Functional, Plano §Metas de desempenho, Gap] — aceito: o plano já põe os marcados entre os geradores de consulta; sem número por ciclo, e não muda o que se constrói
- [x] CHK038 O SC-001 é conferível só com a auditoria — o registro do evento apagado diz que ele estava vazio e o que o Google respondeu? [Measurability, Spec §SC-001 + §FR-023] — **corrigido**: o `auto_deleted` leva o retrato do que estava preso (Data model §Rastro, FR-023, SC-001, cenário 7)
- [x] CHK039 Todo desfecho da limpeza (marcado, removido, movido, reapareceu, presente sem mudança, inconclusivo, falha) tem rastro definido, com ator e motivo? [Completeness, Spec §FR-023, Data model §Rastro] — **corrigido**: três linhas novas no rastro, ator do "reaparecer", ramo "já tinha voltado", e o cenário 13b (a falha por evento nunca era exercitada)

## Trava de escrita fora da produção

- [x] CHK040 "Fora da produção" está definido por um critério conferível, e os ambientes estão cobertos um a um (espelho local, sqlite, banco descartável de ensaio, produção)? [Clarity, Spec §FR-024, Data model §Configuração, cenário 18]
- [x] CHK041 Está claro quais chamadas ao Google a trava cobre (a devolução inteira, inclusive a consulta e a regravação do ramo "já voltou") e quais ficam de fora (o "Sincronizar", a edição comum)? [Clarity, Spec §FR-024, Research R14] — **corrigido**: a FR-024 dizia "ambiente travado não lê nem escreve", falso ao pé da letra; reescrita, e o Plano §XIV também
- [x] CHK042 Está exigido que a produção nasça liberada sem variável nova no painel, e dito como isso se confere depois do deploy? [Completeness, Plano §Constitution Check XIV, Quickstart §6]
- [x] CHK043 O aviso sobre o escape local (cria evento de verdade na agenda da empresa) tem destino na documentação? [Traceability, Research R14, Spec §Docs] — viaja com a documentação da trava (`docs/01`, `DEVELOPMENT.md`, `CLAUDE.md` §4, skill `manto-verify`)
- [x] CHK044 Os requisitos do dublê do Google no verify (falha fechado, modos de apagado, disjuntor de rede, meses isolados) estão na spec, e "mês isolado" tem critério conferível? [Measurability, Spec §Verificação, Research R18] — **corrigido**: os cenários 1 e 7 rodam nos quatro modos de apagado (404 e 410 não passavam pela limpeza em cenário nenhum)

## Caminhos e recuperação

- [x] CHK045 Os caminhos que limpam por sumiço estão enumerados, com os meses que cada um percorre, e a regra vale em todos? [Coverage, Spec §Premissas]
- [x] CHK046 Voltar atrás tem requisito: o que fazer com os eventos marcados antes de reverter? [Recovery, Quickstart §7] — **corrigido**: "anotar a lista" não preserva nada; devolver todos antes, só reverter com a faixa vazia (Quickstart §7, Data model §Migration)
- [x] CHK047 A repetição da contagem no dia do deploy tem critério de decisão escrito (se deixar de ser zero, quem decide e com quê)? [Completeness, Spec §Casos de borda, Research R17] — **corrigido**: o deploy sobe, a limpeza não roda até o dono decidir entre (a) regra normal e (b) resolver à mão; "sem sino" viraria a 303b (Quickstart §1, Spec §Casos de borda)

## Achados além das perguntas (levantados pelos avaliadores)

- [x] CHK048 Comissão já paga ao vendedor segura o evento? Apagar o evento gera sozinho o estorno contra o vendedor. — **decidido pelo dono em 30/09: não** — o evento sem mais nada é apagado e o estorno sai, como hoje; escrito na FR-001, em §Premissas e na R2 [Gap, Spec §Clarifications 30/09]
- [x] CHK049 Cachê lançado ou pago na vaga automática do técnico de som segura o SHOW? A vaga sai por cascade com o cachê. — **decidido pelo dono em 30/09**: o caso não acontece ("se foi pago é porque foi realizado"); a vaga automática nunca conta, como na regra de 29/09 [Gap, Spec §Clarifications 30/09]
- [x] CHK050 O risco "limpeza sem teto de consultas por execução" está registrado? [Gap] — Research §Riscos e §Dívida
- [x] CHK051 A FR-045 cobre a rota antiga de exclusão (`POST /events/<id>/delete`), que não passa pela API? [Gap] — a recusa mora em `_delete_event_flow` (Research R16, Spec §RBAC, cenário 12)
- [x] CHK052 O ensaio que sai com o pai vazio, sem consulta própria, e pode voltar "solto" está declarado? [Gap] — exceção declarada à FR-002 e dívida (Spec §Casos de borda)

## Notas

- Marque como concluído: `[x]`
- Anote achados na própria linha
- Itens numerados em sequência para referência
- Placar da avaliação (37 perguntas): 14 já atendidas, 2 derrubadas pelo revisor, 5 verdadeiras mas
  dispensáveis, 16 corrigidas; mais 5 achados novos — os 2 que dependiam do dono foram respondidos
  em 30/09 (as duas regras propostas saíram).
