<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Regressão e deploy Checklist: Feature 313 — desconto e PIX na calculadora

**Propósito**: os requisitos dizem o que não pode mudar, para quem, e como o deploy e o rollback se comportam?
**Created**: 2026-10-21
**Feature**: [spec.md](../spec.md)

**Nota**: gerado pelo `/speckit-checklist`; avaliado item a item contra spec, plan, research e contracts em 21/10.
Os portões fixos estão em `conta-e-dinheiro.md` (CHK001–CHK008).

## O que já foi cotado (020)

- [x] CHK001 Está escrito que orçamento salvo não muda de preço na tela, no PDF, no e-mail e quando vira evento
  depois? [Completeness, Spec Session 3, §FR-008, SC-005]
- [x] CHK002 Está definido como cada leitor distingue o orçamento salvo do novo (a marca de regra) e o que faz com o
  salvo? [Clarity, research R2/R3; data-model]
- [x] CHK003 O BV de 375 em 6h do `verify_305` (orçamento sem a chave) está nomeado como regressão que tem de continuar
  verde? [Coverage, reconferência §2; Spec verificação 13 e 16]
- [x] CHK004 Está definido o que fazer quando o snapshot devolvido pelo navegador traz bases/cheios inválidos?
  [Edge Case, research R2; data-model "Validação ao ler"]

## Sem desconto, igual a hoje

- [x] CHK005 A mensagem e o PDF sem desconto estão exigidos idênticos, com as exceções da Q7 delimitadas (só nos
  números)? [Consistency, Spec §FR-011 — corrigido nesta rodada; antes contradizia a Q7]
- [x] CHK006 As exceções da paridade estão listadas por categoria e conferidas pela fórmula, não só "diferente"?
  [Measurability, research R11; Spec verificação 1]
- [x] CHK007 O gabarito tem base e momento definidos (a `c074657b`, antes do núcleo)? [Clarity, research R11;
  quickstart §1]

## EducaManto e vizinhos

- [x] CHK008 Está definido que as chaves de desconto não chegam à contratação Manto do EducaManto e que a regra do
  acréscimo vale lá? [Completeness, Spec §FR-009; research R8]
- [x] CHK009 O texto do editor de acréscimos no EducaManto está separado do da calculadora comum? [Consistency,
  Spec §FR-018; research R8]
- [x] CHK010 O gêmeo Jinja tem o comportamento descrito (o que grava, o que perde) e está fora de escopo
  explicitamente? [Coverage, Spec casos de borda — acrescentado nesta rodada; Fora de escopo]
- [x] CHK011 As regressões a rodar estão nomeadas (305, 307, 309, 235, 190)? [Traceability, quickstart §2; plan]

## Deploy cruzado

- [x] CHK012 Tela nova com servidor velho tem comportamento definido (sem desconto; nada trava "Gerar Orçamento")?
  [Edge Case, Spec casos de borda]
- [x] CHK013 Tela velha com servidor novo tem comportamento definido, inclusive o "Recalcular" antigo?
  [Edge Case, Spec casos de borda — "Recalcular" acrescentado nesta rodada]
- [x] CHK014 Toda chave nova é opcional no contrato TypeScript e neutra quando ausente? [Consistency, Spec casos de
  borda; data-model]
- [x] CHK015 O rollback está descrito (o que acontece com orçamentos salvos pela regra nova depois do revert)?
  [Recovery, plan "Deploy e rollback" — acrescentado nesta rodada]

## PDF e proposta

- [x] CHK016 O requisito de o PDF caber numa página com as linhas novas está escrito, com o desenho que o garante?
  [Non-Functional, Spec §FR-015, casos de borda; research R10]
- [x] CHK017 Os três formatos de mensagem (durações, produto + avulsos, só produto) estão cobertos pelo "de/por" e
  pelo PIX? [Coverage, Spec §FR-015, H2 cenário 6]
- [x] CHK018 A ausência da palavra "BV" na proposta continua exigida? [Consistency, Spec H2 cenário 7]

## Notas

- Lacunas corrigidas nesta rodada: FR-011 contra a Q7; o gêmeo Jinja e o "Recalcular" do bundle velho nos casos de
  borda; o rollback no plano.
- Nenhuma pergunta nova ao dono.
