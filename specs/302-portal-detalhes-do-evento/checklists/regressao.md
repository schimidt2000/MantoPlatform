# Regressão Checklist: o que esta feature pode quebrar sem querer

**Propósito**: testar se os requisitos **dizem o que não pode mudar**. Esta feature mexe num
serializador compartilhado por duas telas, remove uma seção inteira de uma tela e toca três
superfícies de saída — as três formas clássicas de quebrar o que funcionava.
**Created**: 2026-09-22
**Feature**: [spec.md](../spec.md)

**Nota**: gerado pelo `/speckit-checklist` a partir da spec, do plano, do contrato e da pesquisa.

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

- [ ] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs)
- [ ] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo
- [ ] CHK003 `verify_302.py` verde contra `manto_local`, escrita conferida por conexão separada, um cenário que falha
- [ ] CHK004 Tela aberta de verdade; superfície pública em viewport mobile
- [x] CHK005 ~~Migration~~ — **não se aplica**
- [x] CHK006 ~~`validar_startcommand.py`~~ — **não se aplica**
- [ ] CHK007 Gate de RBAC declarado em todo endpoint novo/alterado e linha em `docs/01` §4.3
- [ ] CHK008 Docs por fonte única: `docs/01`, `docs/02`, `docs/03` sempre; `00`/`04`/`05` se aplicável
- [ ] CHK009 Nível 1: `/speckit-converge` sem gaps
- [ ] CHK010 Antes de "em produção": `git status` limpo, `git log -1` = cabeçalho do `docs/03`, sonda `/api/`

## O serializador compartilhado

- [x] CHK011 Está declarado que o serializador da agenda é o **mesmo** do histórico, e o que isso implica? [Consistency, Plano §Constitution Check IV]
- [x] CHK012 Está definido o que cada chave nova vale no histórico? [Completeness, Contrato §historico]
- [x] CHK013 Está declarado que **nenhuma chave sai** do payload nesta entrega? [Completeness, Spec §FR-013a]
- [x] CHK014 Os totais do histórico estão nomeados como coisa que não muda? [Coverage, Contrato §historico]

## A seção que some da Agenda

- [x] CHK015 Está declarado quais contadores dependem (e quais não dependem) da lista removida? [Dependency, Plano §Constitution Check IV]
- [x] CHK016 Está declarado que o link de avaliar sai da Agenda e continua na aba Histórico? [Completeness, Spec §H6]
- [x] CHK017 A remoção está reconhecida como **reversão parcial de uma feature anterior**, com o número dela? [Traceability, Spec §H6 — feature 229]
- [x] CHK018 Está dito onde essa reversão precisa ficar registrada? [Traceability, Spec §Docs — `docs/03` e `docs/02`]
- [ ] CHK019 Há requisito sobre o que acontece com a **prop e os imports órfãos** deixados pela remoção? [Gap — o plano menciona, a spec não exige]

## A janela de deploy em duas partes

- [x] CHK020 Está declarado que servidor e site sobem separados e o que isso proíbe? [Completeness, Spec §FR-013a]
- [x] CHK021 O caso simétrico (site novo, servidor velho) tem requisito próprio? [Coverage, Spec §FR-013b]
- [x] CHK022 A dívida "remover no ciclo seguinte" está registrada com destino? [Traceability, Spec §Docs — `docs/05`]
- [x] CHK023 Está declarado **como se confere** que a regra foi respeitada (abrir o JSON e ver a chave lá)? [Measurability, Spec §Verificação cenário 8 — está no verify, mas o quickstart é quem faz alguém olhar]

## As três superfícies de saída

- [x] CHK024 As três superfícies estão nomeadas uma a uma? [Clarity, Spec §FR-012a]
- [x] CHK025 Está declarado que a tradução do local é **uma** função servindo portal e e-mail? [Consistency, Spec §FR-008 + R4]
- [x] CHK026 A cópia em TypeScript que **fica** está justificada e registrada? [Assumption, R4 — o formulário precisa da distinção preset × livre]
- [x] CHK027 Está declarado que a mensagem de WhatsApp não ganha bloco de Saída, e por quê? [Boundary, Spec §Fora de escopo]

## Permissões e privacidade

- [x] CHK028 Está declarado que nenhum portão muda? [Completeness, Spec §RBAC]
- [x] CHK029 Há cenário que **deve falhar** provando que um talento não vê dado de outro? [Coverage, Spec §Verificação cenário 9]
- [x] CHK030 O ponto de conformidade que **não** é corrigido está nomeado, com motivo e destino? [Traceability, Spec §Premissas + Fora de escopo]
- [x] CHK031 A declaração `RBAC:` faltante está nomeada como item a quitar? [Completeness, Spec §RBAC]

## Efeitos fora do sistema

- [x] CHK032 Está declarado que semear ensaio pelo endpoint escreveria no Google Agenda da empresa? [Assumption, Spec §Verificação + R13]
- [x] CHK033 Está declarado que o verify não pode inventar `character_name`? [Assumption, Spec §Verificação]
- [x] CHK034 Está declarado que o verify **restaura** os campos de logística dos eventos reais do espelho que tocar? [Gap — o quickstart pede, a spec não]
- [x] CHK035 Está declarado que o e-mail não é disparado de verdade durante a verificação? [Coverage, Spec §Verificação — as travas de ambiente]

## Desempenho

- [x] CHK036 Existe requisito mensurável de que a consulta não cresça com o número de escalações? [Measurability, Plano §Metas + cenário 13b]
- [x] CHK037 Está declarado que o N+1 corrigido **já existia** antes da feature? [Assumption, R7 — para não ser lido como regressão introduzida aqui]

## Notas

**Avaliação 1 (2026-09-22)** — **26 de 27 itens de conteúdo passam** após a correção. Três
achados, todos pequenos, e nenhum deles muda o desenho. O único que continua aberto (CHK019) é
item de tarefa, não de requisito:

**CHK019 — sobras da remoção.** Ao tirar a seção Histórico da Agenda, a prop que distinguia
"próximo" de "passado" passa a ser sempre verdadeira e alguns imports ficam órfãos. O `tsc` com
`noUnusedLocals` pega os imports; a prop **não** — ela continua compilando, morta. O plano
menciona; a spec não exige. Vira item de tarefa, não requisito novo.

**CHK034 — restaurar o espelho. CORRIGIDO.** O `verify_302.py` toca **eventos reais** do espelho
(assume uma vaga existente, grava logística), e não só linhas que ele mesmo criou. O quickstart
mandava restaurar; a spec só falava em "apagar descartáveis" — um verify que seguisse a spec ao pé
da letra deixaria uma vaga de produção com `talent_id` de um talento de teste. A linha 14 da tabela
de cenários agora diz restaurar, com o motivo.

**CHK023 — como se confere. JÁ COBERTO.** A instrução humana está no quickstart §4 (abrir o JSON e
confirmar a chave); o cenário 8 do verify prova por API. Reavaliado como atendido.

**O que este checklist confirmou que estava bem coberto**, e é onde a feature mais poderia
escorregar:

- a janela de deploy em duas partes tem requisito nos **dois** sentidos (CHK020, CHK021) — e o
  sentido que falta é sempre o que quebra;
- a remoção da seção está registrada como **reversão parcial da feature 229**, com o número
  (CHK017). Sem isso, daqui a seis meses alguém "conserta" recolocando o link e a duplicação de
  nome volta;
- o N+1 corrigido está declarado como **pré-existente** (CHK037). Sem essa frase, o diff sugere
  que a feature o introduziu e alguém o "reverte" junto.

- Marque como concluído: `[x]`
- Anote achados na própria linha
- Itens numerados em sequência para referência
