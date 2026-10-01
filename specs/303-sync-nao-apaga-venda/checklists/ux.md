# UX Checklist: a faixa, o sino, a tela do evento marcado e o portal

**Propósito**: testar a **qualidade dos requisitos de tela** desta feature — se o que está escrito é
completo, inequívoco e conferível por outra pessoa: a faixa fixa, o aviso no sino, a tela do evento
marcado, o diálogo de devolver ao Google, o `/admin/sync` e o aviso no portal do artista em celular.
Não testa se o código funciona; isso é o `verify_303.py` e a conferência de tela.
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

## A faixa

- [x] CHK011 "Destaque de alerta" está quantificado (cor, altura, posição em desktop e em celular)? [Clarity, Spec §FR-009, Research R9]
- [x] CHK012 "Todas as telas do sistema interno" tem fronteira definida — o que fica de fora (login, telas sem o shell, impressão)? [Clarity, Spec §FR-009, Gap] — **corrigido**: Research R9 "Fronteira" e FR-009 (ficam de fora o login e as duas folhas de impressão de figurino, que são Jinja)
- [x] CHK013 Os dois textos (singular e plural) estão fixados e iguais na spec, no contrato e no quickstart? [Consistency, Contrato §Textos fixos]
- [x] CHK014 O conteúdo de cada linha da lista está definido, inclusive para evento sem data e para título longo? [Completeness, Spec §FR-009, Gap] — **corrigido**: Research R9 "Conteúdo" e Contrato §Textos fixos (formato da data, `sem data`, corte do título, um evento × vários)
- [x] CHK015 Está definido o que a faixa mostra quando há mais eventos marcados do que o teto da lista? [Edge Case, Research R8, Gap] — a frase usa sempre o total e a lista termina em `e mais N` (dobrado no CHK014)
- [x] CHK016 O inventário de elementos fixos no topo que precisam compensar a altura da faixa está completo (hoje: a régua de abas do evento e as âncoras da Home)? [Completeness, Plano §Código, Research R9]
- [x] CHK017 A ordem de sobreposição está definida contra cada vizinho (régua de abas, painel do sino, menus, diálogos)? [Clarity, Research R9, Plano §Rastreamento de complexidade] — sai dos números já escritos (`z-[25]` contra `z-40`/`z-50` de diálogo e drawer)
- [x] CHK018 A ausência de skeleton e de mensagem de erro está registrada como exceção justificada, com o que o usuário vê se a consulta falha? [Consistency, Plano §Constitution Check V]
- [x] CHK019 Os requisitos de teclado e leitor de tela da faixa e da lista estão definidos (foco, Esc, o que é anunciado e o que não é)? [Coverage, Research R9, Quickstart §4] — nota para o tasks: `aria-expanded`/`aria-controls` como nas outras cópias do padrão (`KebabMenu`, `NotificacoesBell`)
- [x] CHK020 Está definido em quanto tempo a faixa reflete uma mudança — para quem resolveu (na hora) e para os outros (até um minuto)? [Measurability, Contrato §Frontend, Spec §SC-003]
- [x] CHK021 O comportamento sob "Ver como" está definido para a faixa e para o sino, e os dois são coerentes? [Consistency, Spec §Casos de borda, Research R8]
- [x] CHK022 Em 320–430 px a faixa tem requisito (uma linha, quebra, o que é cortado)? [Coverage, Quickstart §4, Gap] — **corrigido**: Research R9 "Tela estreita" e Quickstart §4.2 (a referência do app interno é 375 px; 320 px é só do portal)
- [x] CHK023 Movimento reduzido tem requisito para a faixa e para a lista? [Coverage, Research R9, Quickstart §4]

## O sino

- [x] CHK024 O título e o corpo do aviso estão definidos com todas as variantes (sem data, sem venda, grupo, uma pessoa, ninguém)? [Completeness, Contrato §Sino]
- [x] CHK025 Está dito o que acontece com o aviso em cada saída da marca (lido) e quando o evento é apagado (removido)? [Completeness, Spec §FR-010, Research R7]
- [x] CHK026 Está declarado que quem vira Superadmin ou Comercial depois da marca não recebe o aviso (mas vê a faixa)? [Edge Case, Data model §notifications, Gap] — já estava: destinatários "resolvidos na emissão"; a faixa é por papel efetivo na hora
- [x] CHK027 A severidade do aviso está definida e é coerente com os outros avisos urgentes do sino? [Consistency, Research R7]

## A tela do evento marcado

- [x] CHK028 O que cada papel vê no banner está definido — Superadmin, Comercial **e os demais** (Figurino, Financeiro, Casting, revendedor)? [Completeness, Research R15, Contrato §Textos fixos, Gap] — **corrigido**: texto comum fixado; a frase do Comercial sai por `can_request_delete && !can_delete` (o front não decide por papel)
- [x] CHK029 Os campos do quadro "o que está em jogo" estão listados com a origem, e a comissão aparece como estimativa quando é estimativa? [Clarity, Spec §FR-011, Research R15] — **corrigido**: Research R15 "Linhas do quadro" (mapa campo a campo; rótulo de estimativa; a diferença de 1 no SHOW entre o quadro e o sino é declarada)
- [x] CHK030 A variante do satélite (venda do grupo, link para o principal) está definida? [Coverage, Spec §FR-011, Research R15] — **corrigido**: "decide-se no evento principal" era herança de antes da divisão; o botão de devolver continua no satélite (FR-011, R15, Contrato)
- [x] CHK031 A tela diz a quem edita um evento marcado que a edição **não** vai ao Google até a devolução? [Completeness, Spec §FR-008, Gap] — **corrigido**: segunda frase do banner comum (Contrato §Textos fixos)
- [x] CHK032 O texto do motivo no item "Excluir ou cancelar" desabilitado está fixado? [Completeness, Research R16, Contrato §Textos fixos, Gap] — **corrigido**: Contrato §Textos fixos
- [x] CHK033 Está definido como o Comercial "conta ao Superadmin" — e a tela não promete um canal que o sistema não tem? [Ambiguity, Spec §História 2, Contrato §Textos fixos] — por fora, ou pelo "Solicitar exclusão" da 224, que continua valendo em evento marcado (Spec §Casos de borda)
- [x] CHK034 O banner tem requisito para tela estreita (a equipe usa celular)? [Coverage, Plano §Plataforma-alvo, Gap] — **corrigido**: Research R15 "Tela estreita" e Quickstart §4.3/§4.5
- [x] CHK035 O selo da agenda está definido nas três visões (Mês, Lista, Dia) e na busca, com cor, texto e o que acontece no chip pequeno do Mês? [Completeness, Spec §FR-004 + §FR-033, Research R10] — **corrigido**: Research R10 "Onde o selo aparece" (no chip do Mês e no bloco curto do Dia, só o ícone; a busca herda da Lista)
- [x] CHK036 O tooltip do selo tem equivalente para toque? [Coverage, Contrato §Textos fixos, Gap] — **corrigido**: em toque, a data é lida no banner do evento (Contrato, R10)
- [x] CHK037 Os passos do "recriado à mão no Google" estão na mesma ordem e com o mesmo conteúdo na spec e no desenho da tela? [Consistency, Spec §Casos de borda, Research R15] — só havia uma listagem; o texto de tela agora está fixado no Contrato (ver CHK056)

## O diálogo de devolver

- [x] CHK038 Cada código de erro da devolução tem mensagem em pt-BR fixada? [Completeness, Contrato §devolver-ao-google, Gap] — **corrigido**: coluna "Mensagem" na tabela de erros (duas para `google_recusou`: criação e atualização)
- [x] CHK039 O que o usuário vê no sucesso está definido, para "recriado" e para "já tinha voltado"? [Completeness, Contrato §devolver-ao-google, Gap] — **corrigido**: linha `aria-live` do cabeçalho, um texto por `resultado` (o campo era devolvido sem consumidor)
- [x] CHK040 O formato de "data e horário" no "Será recriado como" está definido para dia inteiro e para evento de vários dias? [Clarity, Contrato §Textos fixos] — **corrigido**: formato próprio (o `formatRange` do cabeçalho mostraria "00:00 — 00:00" e perderia o dia do fim)
- [x] CHK041 O estado durante a espera está definido (a chamada ao Google pode levar até 60 s), com o fechamento bloqueado? [Completeness, Plano §Metas de desempenho, Quickstart §4] — "fechamento bloqueado durante a ação" já cobre Esc, clique fora e o X (mesmo `onOpenChange`)
- [x] CHK042 O erro de estado (já devolvido em outra aba) tem comportamento definido e diferente do erro do Google? [Coverage, Contrato §Frontend, Spec §Casos de borda]
- [x] CHK043 O aviso de data passada está definido com o critério (passada em relação a quê — início ou fim)? [Clarity, Spec §FR-012, Contrato §Textos fixos] — **corrigido**: pelo fim (ou início, sem fim); evento de hoje não terminado não recebe o aviso; o mesmo corte ordena a faixa

## `/admin/sync`

- [x] CHK044 O texto da confirmação e o da mensagem de resultado do "Limpar eventos fantasma" estão fixados, com todos os números da FR-042? [Completeness, Spec §FR-042 + §FR-025, Contrato §Endpoints alterados] — **corrigido**: textos fixados; seis números (o contrato dizia quatro); `ConfirmDialog` no lugar do `window.confirm`; linhas por mês e tom de alerta quando há falha

## Portal do artista (celular)

- [x] CHK045 O texto do aviso está fixado e é o que o dono ditou? [Consistency, Spec §O pedido, Contrato §Textos fixos]
- [x] CHK046 A posição do aviso dentro do cartão está definida nas três telas? [Clarity, Research R19, Gap] — **corrigido**: Research R19 "Posição" (primeira caixa depois do cabeçalho; em Convites, antes do cachê e dos botões)
- [x] CHK047 Os requisitos visuais do aviso são conferíveis (largura, tamanho do texto, quebra de linha, sem truncar, 320 a 430 px)? [Measurability, Plano §Constitution Check X, Quickstart §4]
- [x] CHK048 O aviso faz sentido no **Histórico** — evento que já passou "em confirmação"? [Ambiguity, Spec §FR-022] — respondido pelo CHK049
- [x] CHK049 Há requisito para o evento marcado cuja data **passa** enquanto ele espera (o "Avaliar" acende? conta como trabalhado?) [Coverage, Gap] — **corrigido**: caso de borda novo (continua valendo em tudo, FR-005; o "já trabalhou" que não se desliga é dívida)
- [x] CHK050 Está declarado que marcar e desmarcar não mandam e-mail nem mensagem ao elenco? [Clarity, Spec §História 6, Gap] — **corrigido**: História 6 (e o que o sync já manda quando o evento volta com outra data continua); afirmação nos cenários 1 e 9
- [x] CHK051 O convite pendente de evento marcado tem requisito (aviso, e aceitar e recusar continuam)? [Coverage, Spec §Casos de borda]
- [x] CHK052 Está exigido que o motivo nunca chegue ao artista (a palavra "Google" não aparece no portal)? [Clarity, Research R19, Contrato §Endpoints alterados]

## Achados além das perguntas (levantados pelos avaliadores)

- [x] CHK053 O aviso do sino é legível sem abrir? A linha do sino corta título e corpo em uma linha, e com o prefixo fixo sobrariam ~10 caracteres para o nome do evento. [Gap] — **corrigido**: o aviso `urgent` quebra em até 2 + 3 linhas (Research R7, Contrato §Sino, FR-010, Quickstart §4.7)
- [x] CHK054 Evento marcado **com** exclusão solicitada: os dois banners e o botão "Analisar e decidir" têm comportamento definido? [Gap] — **corrigido**: dois banners, o botão desabilitado com o mesmo motivo do menu (Research R16, Spec §Casos de borda, cenário 12)
- [x] CHK055 O aviso e o quadro dizem **por que** o evento ficou quando foi só por contrato ou por comprovante sem valor? [Gap] — **corrigido**: variantes no corpo do aviso e linhas de contrato, comprovantes e grupo no quadro (Contrato §Sino, Research R7 e R15)
- [x] CHK056 O passo 2 do "recriado à mão" leva a um segundo evento preso (apagar no Google um evento com venda o marca, e marcado não pode ser excluído)? [Gap] — **corrigido**: esvaziar antes de apagar; texto de tela fixado (Spec §Casos de borda, Contrato §Textos fixos)
- [x] CHK057 A mensagem de "o Google não confirmou a criação" diz o que fazer se o evento apareceu? [Gap] — **corrigido**: "se apareceu, apague-o lá e devolva de novo" (Contrato, Spec §Casos de borda)

## Notas

- Marque como concluído: `[x]`
- Anote achados na própria linha
- Itens numerados em sequência para referência
- Placar da avaliação (42 perguntas): 15 já atendidas, 2 derrubadas pelo revisor, 6 verdadeiras mas
  dispensáveis, 19 corrigidas; mais 5 achados novos, todos corrigidos.
