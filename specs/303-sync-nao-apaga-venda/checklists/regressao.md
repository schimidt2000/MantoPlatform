# Regressão Checklist: o que esta feature pode quebrar sem querer

**Propósito**: testar se os requisitos **dizem o que não pode mudar**. Esta feature troca o miolo de
uma limpeza que roda a cada 10 minutos, muda o retorno de uma função com cinco chamadores, mexe num
serializador do portal compartilhado por duas telas, recusa duas ações da 224 e faz a exclusão de
evento limpar mais coisas — as formas clássicas de quebrar o que funcionava.
**Created**: 2026-09-30
**Feature**: [spec.md](../spec.md)

**Nota**: gerado pelo `/speckit-checklist` a partir da spec, do plano, da pesquisa (`research.md`),
do contrato e do quickstart. Portão antes do `/speckit-tasks`. Avaliado em 30/09 por dois agentes só
de leitura e um revisor adversarial, contra os documentos e o código; cada lacuna confirmada foi
corrigida no documento indicado na própria linha.

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

## Loja Virtual

- [x] CHK011 A regra da venda virtual está declarada como inalterada, ponto a ponto (nunca apagada, divergência registrada, sem consulta individual, nunca marcada)? [Completeness, Spec §Casos de borda + §Fora de escopo, Research R4]
- [x] CHK012 Está declarado que a consulta antiga, de que o Meet da Loja Virtual depende, não muda? [Completeness, Plano §Constitution Check IV, Research R3]
- [x] CHK013 O ajuste do `verify_205` tem critério de aceite escrito (nenhum id virtual consultado; contagem do mês igual antes e depois)? [Measurability, Quickstart §3, Research R18] — **corrigido**: a "credencial nula" não existe hoje no verify (é acréscimo, não manutenção) e "nenhum id consultado" não tinha por onde ser observado — entra um espião da consulta (Research R18, Plano §Código, Quickstart §3)
- [x] CHK014 Está dito quando o `verify_205` é rodado de novo e o que o seu efeito antigo no espelho vira? [Traceability, Spec §Verificação, Research R18]

## Cancelar, excluir e solicitar exclusão (224)

- [x] CHK015 Está declarado que a regra de vazio do botão Excluir e os papéis de cancelar e excluir não mudam? [Completeness, Spec §Fora de escopo + §RBAC]
- [x] CHK016 "Solicitar exclusão", "Recusar" e "Aprovar" da 224 têm comportamento definido para evento marcado? [Coverage, Gap] — **corrigido**: caso de borda novo (solicitar e recusar seguem como hoje; "aprovar" é cancelar ou excluir, que a FR-045 recusa; "Analisar e decidir" desabilitado), linha no Contrato e no §RBAC, sub-cenário no 12
- [x] CHK017 Evento que já tinha exclusão solicitada e depois some do Google: a precedência da situação e o destino do pedido estão definidos? [Edge Case, Spec §FR-033] — precedência na FR-033; a marca não toca `deletion_requested_*` (Data model §Invariantes), então o pedido volta a aparecer quando a marca sai
- [x] CHK018 A mudança na exclusão de evento (ensaio-filho com histórico; aviso do sino) está declarada como valendo para **toda** exclusão, não só a do sync? [Completeness, Plano §Código, Spec §Casos de borda] — **corrigido**: caso de borda, Contrato (linha do `DELETE`), Plano §IV e variante no cenário 7b
- [x] CHK019 Evento cancelado continua ignorado pela limpeza, sem marca e sem consulta — com cenário? [Coverage, Spec §Casos de borda, cenário 15]
- [x] CHK020 A recusa de cancelar e excluir evento marcado tem validade escrita (a segunda entrega a substitui)? [Traceability, Spec §FR-045]

## O sync de todo dia

- [x] CHK021 Está declarado o que **não** muda no sync: importar evento novo, atualizar o existente, reconciliar a escala pelo título, marcar trabalhado? [Completeness, Plano §Constitution Check IV, Gap] — declarado por lista fechada: o plano nomeia os toques de `routes.py` e nenhum é `sync_events`
- [x] CHK022 Todos os chamadores da limpeza e todos os consumidores do retorno (que muda de tipo) estão listados? [Completeness, Research R4, Plano §Decisão de estrutura] — três chamadores conferidos no código; o plano agora nomeia os três verifies antigos
- [x] CHK023 O tempo a mais do ciclo (consultas individuais, até 60 s cada) está confrontado com os limites que já existem — a reserva do ciclo e o corte do proxy? [Non-Functional, Plano §Metas de desempenho, Research R4, Gap] — **corrigido**: Plano §Metas (pior caso, o claim de 600 s, a corrida segura entre dois ciclos, o que fazer se o proxy cortar) e Quickstart §4.8
- [x] CHK024 Está dito que "Sincronizar agora" e o "Sincronizar" do evento continuam sem limpar? [Consistency, Spec §Premissas]
- [x] CHK025 O evento criado pela plataforma minutos antes (ainda fora da lista do Google) está coberto? Os casos 1206 e 1265 têm explicação? [Coverage, Research R17, Gap] — coberto pela regra geral (FR-002: todo candidato é consultado; presente não é apagado); os dois casos seguem sem explicação, e isso não bloqueia
- [x] CHK026 Está declarado o que o ciclo faz quando a reconferência dos marcados abre o disjuntor — os meses ainda sincronizam? [Clarity, Research R12, Gap] — **corrigido**: Research R12 (a falha na reconferência não interrompe o ciclo; cada mês tem o seu disjuntor) e cenário 13d. O revisor propôs um disjuntor da execução inteira; ficou o local, mais simples (R4, alternativa rejeitada)
- [x] CHK027 O trabalho que o `rollback` novo descarta está nomeado e tem conferência prevista? [Measurability, Plano §Rastreamento de complexidade] — **corrigido**: nomeado no Plano §Rastreamento; "conferido no ensaio" não apontava para nada — virou o cenário 13c

## E-mails ao elenco

- [x] CHK028 Nenhum caminho novo manda e-mail de remoção: está exigido para o "Sincronizar" de evento ausente, para a devolução e para o sync seguinte a ela? [Coverage, Spec §FR-039 + §FR-044, cenários 10g e 14] — **corrigido**: faltava o quarto caminho — o marcado que reaparece sozinho: vale o Google, com e-mail de remoção possível; declarado como risco aceito (Spec §Casos de borda, FR-006, Research R12 e §Riscos)
- [x] CHK029 A mudança de data aplicada pelo sync passa a avisar o elenco aceito em casos que antes apagavam e reimportavam — a mudança está declarada? [Completeness, Research R5 + R17, Gap] — declarada como decisão em R5 (reusar `sync_events` justamente porque avisa o elenco) e medida na contagem (R17)
- [x] CHK030 Editar um evento marcado avisa o elenco como uma edição comum? Está dito? [Clarity, Spec §FR-008, Gap] — determinado pelo plano: uma condição só (o push ao Google); o resto da edição é a de hoje
- [x] CHK031 O lembrete diário de convite de evento marcado está nomeado como coisa que continua, com destino? [Traceability, Spec §Fora de escopo]
- [x] CHK032 A devolução não reenvia convite — está declarado na spec e dito na tela? [Consistency, Spec §Premissas, Contrato §Textos fixos]

## Portal

- [x] CHK033 O serializador do portal é compartilhado por agenda e histórico: a chave nova nasce opcional e nenhuma sai? [Completeness, Contrato §Endpoints alterados, Research R19]
- [x] CHK034 As listas citadas no contrato do portal existem hoje (a 302 tirou o histórico da tela Agenda)? [Consistency, Contrato §Endpoints alterados]
- [x] CHK035 Avaliação de evento cancelado: está dito o que acontece com a nota já dada antes do cancelamento? [Edge Case, Spec §FR-022, Gap] — nenhum documento manda mexer em nota existente: ela fica gravada, como hoje
- [x] CHK036 O portão "só o escalado vê" tem cenário que deve falhar? [Coverage, Spec §Verificação cenário 24]

## Dinheiro (o que esta entrega não toca)

- [x] CHK037 A FR-005 é conferível — há cenário ou argumento escrito de por que venda, comissão, Planilha e DRE não mudam? [Measurability, Spec §FR-005, Research R1]
- [x] CHK038 A consequência do intervalo está declarada: o evento cancelado de verdade segue contando (comissão, cachê na Planilha) até a segunda entrega, e quem cuida disso? [Coverage, Spec §Clarifications 30/09, Research §Riscos, Gap] — consequência **escrita** (Spec §Premissas, Research §Riscos): o Financeiro não vê a faixa, então quem segura é o Superadmin, conferindo a faixa antes de fechar a Planilha — **confirmado pelo dono em 30/09**

## Payloads e a janela de deploy

- [x] CHK039 Todo campo novo em payload existente nasce opcional, e está dito o que cada combinação mostra (site novo + servidor velho; servidor novo + site velho)? [Completeness, Contrato, Research §Riscos]
- [x] CHK040 O link do Google passar a vir nulo para evento marcado **e cancelado** está declarado como mudança, com os consumidores do campo listados? [Completeness, Contrato §Endpoints alterados, Research R11]
- [x] CHK041 O aviso de tipo novo no sino tem comportamento definido no site antigo (ícone padrão)? [Edge Case, Gap] — o código de hoje já cai no ícone padrão; registrado no Contrato §Sino
- [x] CHK042 As ações novas de auditoria têm rótulo onde a auditoria do sync é exibida? [Completeness, Contrato §Nomes fixados, Gap] — `/admin/logs` mostra o código cru para toda ação; nada a regredir
- [x] CHK043 O revendedor EducaManto: está dito o que ele recebe na faixa e no evento marcado, sem erro e sem dinheiro? [Coverage, Spec §RBAC, Research R8]
- [x] CHK044 A ordem do deploy (servidor antes do site) e a migration aditiva estão declaradas, com o que se confere depois? [Completeness, Plano §Constitution Check Operação, Quickstart §6] — **corrigido**: "backend primeiro" não é executável (um push redeploya os dois, sem ordem garantida); virou "num push só", com a sonda que distingue backend novo de antigo (Quickstart §6, Plano)

## Verifies e documentos que envelhecem

- [x] CHK045 Os verifies antigos que tocam a limpeza estão listados, com o que acontece a cada um (ajustado, rodado de novo, ou dívida)? [Traceability, Research R18 + §Dívida] — **corrigido**: o estado de cada um depois da 303; o `verify_151` não pode ser rodado sem ajuste (consultaria o Google real) — Research §Dívida, Quickstart §3
- [x] CHK046 A lista de documentos a atualizar cobre cada fato que muda (contrato, telas, invariantes, dívidas, plano de extração, trava)? [Completeness, Spec §Docs] — **corrigido**: faltavam o schema e o head no `docs/01`, a frase das escritas no Google do `docs/00` §1, os fluxos de exclusão e do "Sincronizar" no `docs/04` e a fatia A do `docs/05` §9.1

## Achados além das perguntas (levantados pelos avaliadores)

- [x] CHK047 Quando o evento marcado reaparece sozinho, qual lado vence — o Google ou a edição feita no sistema? [Gap] — **corrigido**: vale o Google (FR-006, caso de borda, invariante no `docs/04`); só a devolução faz valer o sistema
- [x] CHK048 Se a devolução falhar no teste pós-deploy, o evento de teste tem saída? [Gap] — **corrigido**: restaurar na lixeira do Google e então excluir (Quickstart §6)
- [x] CHK049 Os e-mails de `sync_events` saem antes do commit: um `rollback` incondicional no erro do mês repetiria o mesmo e-mail a cada ciclo? [Gap] — **corrigido, com mudança de desenho**: `rollback` só em erro de banco (Plano, Research §Riscos, cenário 13c)

## Notas

- Marque como concluído: `[x]`
- Anote achados na própria linha
- Itens numerados em sequência para referência
- Placar da avaliação (36 perguntas): 14 já atendidas, 3 derrubadas pelo revisor, 8 verdadeiras mas
  dispensáveis, 11 corrigidas (a que dependia do dono foi confirmada em 30/09); mais 3 achados
  novos, todos corrigidos.
