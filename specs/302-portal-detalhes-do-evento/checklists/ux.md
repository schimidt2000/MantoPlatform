# UX Checklist: o card do evento no Portal do Artista

**Propósito**: testar a **qualidade dos requisitos de tela** desta feature — se o que está escrito
é completo, inequívoco e conferível por outra pessoa. Não testa se o código funciona; isso é o
`verify_302.py` e a conferência de tela.
**Created**: 2026-09-22
**Feature**: [spec.md](../spec.md)

**Nota**: gerado pelo `/speckit-checklist` a partir da spec, do plano e do contrato.

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

- [ ] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs)
- [ ] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo
- [ ] CHK003 `verify_302.py` verde contra `manto_local`, escrita conferida por conexão separada, um cenário que falha
- [ ] CHK004 Tela aberta de verdade; superfície pública em viewport mobile
- [x] CHK005 ~~Migration~~ — **não se aplica**: a feature não muda `models.py`
- [x] CHK006 ~~`validar_startcommand.py`~~ — **não se aplica**: não toca `render.yaml`
- [ ] CHK007 Gate de RBAC declarado em todo endpoint novo/alterado e linha em `docs/01` §4.3
- [ ] CHK008 Docs por fonte única: `docs/01`, `docs/02`, `docs/03` sempre; `00`/`04`/`05` se aplicável
- [ ] CHK009 Nível 1: `/speckit-converge` sem gaps
- [ ] CHK010 Antes de "em produção": `git status` limpo, `git log -1` = cabeçalho do `docs/03`, sonda `/api/`

## Completude do que a tela mostra

- [x] CHK011 A ordem dos elementos do card depois da mudança está definida? [Completeness, Spec §H1-H5]
- [x] CHK012 A **ordem dos itens dentro** do bloco "Antes do evento" está especificada? [Gap]
- [x] CHK013 O estado do bloco quando não há nada a mostrar está definido (não existe, não "vazio")? [Completeness, Spec §FR-009]
- [x] CHK014 Está especificado em quais telas o bloco aparece e em quais não aparece? [Completeness, Spec §FR-009a/FR-009b]
- [x] CHK015 O **rótulo visível** do controle que abre o bloco está definido? A spec diz `"mais detalhes"` entre aspas em um lugar e `"Antes do evento"` em outro — são dois nomes para a mesma coisa. [Ambiguity, Spec §FR-009]
- [x] CHK016 O texto de cada rótulo novo ("Função", "Personagem") está definido literalmente? [Clarity, Spec §FR-011]

## Clareza e mensurabilidade

- [x] CHK017 "Card não pode ficar poluído" foi traduzido em critério conferível? [Measurability, Spec §FR-009 + SC-003]
- [x] CHK018 O formato exato da faixa horária está escrito, e não só descrito? [Clarity, Spec §H1 — `20:00 às 23:00`]
- [x] CHK019 O que decide a existência de cada linha (hora, não local) está dito sem ambiguidade? [Clarity, Spec §FR-006a]
- [x] CHK020 A tradução do local de maquiagem está enumerada valor a valor? [Clarity, Contrato §before_event]
- [x] CHK021 Existe requisito mensurável de que o bloco **não empurre** cachê e figurino para fora da primeira dobra em 375×812? [Measurability, Gap]

## Cobertura de cenários de borda da tela

- [x] CHK022 O evento que **vira a meia-noite** tem requisito de exibição? `20:00 às 00:00` lê como evento de 20 horas. [Gap, Edge Case]
- [x] CHK023 O ensaio que **já aconteceu** enquanto o evento ainda é futuro tem requisito? A janela existe sempre, porque o ensaio cai 2 a 4 dias antes. [Gap, Edge Case]
- [x] CHK024 O evento sem horário final tem requisito de exibição? [Coverage, Spec §H1 cenário 2]
- [x] CHK025 O ensaio órfão e o ensaio cancelado têm requisito? [Coverage, Spec §Casos de borda + R12]
- [x] CHK026 A logística pela metade (local sem hora) tem requisito? [Coverage, Spec §FR-006a]
- [x] CHK027 O local de maquiagem **digitado à mão** (endereço livre, que o formulário permite e o banco ainda não tem) tem requisito de exibição? [Coverage, Spec §FR-007 — a regra existe, mas nenhum cenário de aceite a exercita]

## Requisitos não-funcionais de tela

- [x] CHK028 O requisito de viewport mobile está declarado com medida? [NFR, Spec §Conferência de tela — 375×812, varredura 320–430]
- [x] CHK029 O alvo de toque do controle que expande o bloco está declarado? [NFR, Gap — a constituição exige ≥44px, a spec não repete para este controle]
- [x] CHK030 Há requisito de rótulo acessível para o controle de expandir (leitor de tela sabe o que abre)? [NFR, Gap]
- [x] CHK031 Há requisito sobre animação e `useReducedMotion`? [NFR, Plano §Constitution Check XI]

## Consistência entre superfícies

- [x] CHK032 O rótulo Função/Personagem está exigido nas **três** superfícies, e elas estão nomeadas? [Consistency, Spec §FR-012a]
- [x] CHK033 O escopo da faixa horária está delimitado tela a tela, sem "e nas demais também"? [Consistency, Spec §FR-001 — Agenda e Convites; §FR-014 — a ficha mostra nome e data, sem hora; Histórico mantém só a data]
- [x] CHK034 A mensagem de WhatsApp tem bloco de Maquiagem e não tem de Saída; a spec declara isso como escolha? [Consistency, Spec §Fora de escopo — declarado, mas o motivo "corrigimos o que está errado, não o que falta" só aparece lá e não no requisito]

## Notas

**Avaliação 1 (2026-09-22)** — **21 de 24 itens de conteúdo passam** (CHK011–CHK034, fora os
portões fixos). Seis achados; **três são gaps reais e dois deles têm número atrás**:

**CHK022 — evento que vira a meia-noite. GAP REAL, com dado.** São **34 eventos** no espelho com
fim em dia diferente do início, **4 deles futuros** (o mais próximo é 24/10/2026, 20:00 → 00:00).
Nenhum tem elenco ainda, porque o casting fecha perto da data — ou seja, o defeito **não aparece
hoje e vai aparecer sozinho**. Com o requisito como está, o card diria `20:00 às 00:00`, que lê
como evento de vinte horas. Precisa de requisito próprio.

**CHK023 — ensaio que já passou, evento que ainda vem. GAP REAL, garantido por construção.** O
ensaio cai 2 a 4 dias antes do show, então **sempre** existe uma janela em que ele é passado e o
show é futuro. Hoje a consulta daria zero (o próximo ensaio é 30/09), mas em 01/10 o card do show
de 03/10 mostraria "Ensaio: 30 de set" no bloco de **preparação**. A spec não diz se o ensaio
passado some, fica esmaecido ou fica igual.

**CHK012 — ordem dentro do bloco.** Não especificada. Importa: a ordem cronológica real é ensaio
(dias antes) → maquiagem → saída → evento, e qualquer outra ordem obriga quem lê a remontar a
sequência de cabeça, que é justamente o trabalho que a feature quer poupar.

**CHK015 — dois nomes para a mesma coisa.** A spec escreve `"mais detalhes"` em FR-009 e "Antes do
evento" no plano e no quickstart. Um é o rótulo do controle, o outro é o nome do bloco — mas isso
está implícito, e implícito vira divergência no implement.

**CHK021, CHK029, CHK030 — não-funcionais de toque e leitura.** A constituição já exige ≥44px e
mobile-first, e o plano cita; a spec não repete para o controle novo. Risco baixo (o portão
CHK004 pega na conferência de tela), mas é barato escrever.

**CHK027 — endereço de maquiagem digitado à mão.** A regra de tradução cobre ("qualquer outro
valor → verbatim"), mas nenhum cenário de aceite a exercita, e o banco ainda não tem um caso.
É o valor que um dia vai existir e ninguém terá testado.

**CHK034** é observação, não gap: a escolha está declarada em Fora de escopo, só não está ao lado
do requisito.

**Avaliação 2 (2026-09-22, após correção)** — **24 de 24**. O que entrou na spec:

| Achado | Virou |
|---|---|
| CHK022 | **FR-002a** — evento que termina em outro dia tem de deixar isso explícito; cenário de aceite 4 da História 1; cenário 4b do verify |
| CHK023 | **FR-004a** — ensaio já realizado sai do bloco; cenário de aceite 6 da História 2; cenário 4c do verify |
| CHK012 | **FR-009c** — ordem cronológica real dentro do bloco: ensaio, maquiagem, saída |
| CHK015 | **FR-009d** — um nome só, "Antes do evento", para o bloco e para o controle |
| CHK021, CHK029, CHK030 | **FR-009e** — alvo ≥44px, rótulo anunciável, e o bloco aberto não empurra o cachê para fora da primeira tela |
| CHK027 | cenário de aceite 5 da História 3 + cenário 5b do verify |

**A lição desta rodada**: os dois gaps reais eram invisíveis pela leitura dos artefatos e só
apareceram por **medição do espelho**. O evento que vira a meia-noite não aparece em nenhuma
conversa sobre a feature — aparece numa consulta que pergunta "quantos eventos terminam em outro
dia?" (34, sendo 4 futuros). E o ensaio já realizado dá **zero** hoje, então uma consulta ingênua
o inocentaria: o que o condena é o raciocínio de que o ensaio cai 2 a 4 dias antes do show, logo a
janela existe sempre. Medição achou um; aritmética de calendário achou o outro.

- Marque como concluído: `[x]`
- Anote achados na própria linha
- Itens numerados em sequência para referência
