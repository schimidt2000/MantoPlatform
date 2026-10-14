# Checklist: dinheiro do BV — qualidade dos requisitos

**Purpose**: portão antes do `/speckit-tasks` — os requisitos de valor, arredondamento, estado e RBAC do
BV estão completos, claros e sem conflito? (testa a spec, não o código)
**Created**: 2026-10-14
**Feature**: [spec.md](../spec.md) · [research.md](../research.md)

## Completude

- [x] CHK001 A conta do BV do orçamento está definida para as duas fontes (valores gravados e conta inversa) e para quando as duas falham? [Spec FR-001, FR-002; Research R1]
- [x] CHK002 Está definido o arredondamento (base ao centavo antes do %, HALF_UP) e a tolerância de R$ 0,01 entre fontes e entre venda e total? [Spec FR-001, FR-006; Research R1, R3]
- [x] CHK003 Está definido o que acontece com cada estado da linha BV (a pagar, no banco, pago) em cada porta (criação, vínculo, editor, venda que muda)? [Spec FR-015–FR-022; data-model "Estados"]
- [x] CHK004 Está definido o que o editor herda de uma linha antiga e por qual identidade? [Spec FR-015; Research R7]
- [x] CHK005 A regra da venda sem valor está escrita para o BV em % existente, o novo e a volta a um valor? [Spec FR-016, FR-022]
- [x] CHK006 A troca só da nota tem regra própria para BV em R$ e em %? [Spec FR-021; Research R9]
- [x] CHK007 A entrada de valor em formato brasileiro e o valor ilegível têm comportamento definido (nunca descarte silencioso)? [Spec FR-015a; Research R6]

## Clareza

- [x] CHK008 "Na proporção da venda" está quantificado (fórmula, líquido com nota, denominador por duração)? [Spec FR-004, FR-021; Research R3, R9]
- [x] CHK009 "BV pago não muda" está explícito para R$ e para %, e diz o que continua editável? [Spec FR-017a; Research R7]
- [x] CHK010 O corte do alerta está definido de forma mensurável (momento, fuso, o que conta como "ligado depois")? [Spec FR-019; Research R8]

## Consistência

- [x] CHK011 O valor que o alerta propõe ("Lançar o BV") é o mesmo que a criação grava para o mesmo orçamento, duração e venda? [Spec FR-020 × FR-006; Research R8]
- [x] CHK012 A régua do % no editor (com os outros acréscimos, 3b-Q7) e a conta inversa do orçamento (sem eles) estão separadas sem se contradizer? [Research R1 × R7]
- [x] CHK013 As premissas do plano que contrariavam a HEAD (pago em R$ editável, herança por recebedor, lista ignorada só com orçamento) foram reconciliadas na spec? [Spec FR-006, FR-015, FR-017a]

## Cobertura de cenário e bordas

- [x] CHK014 Concorrência (duas aplicações; editor × "marcar pago") tem comportamento definido? [Research R4, R7; verify 34]
- [x] CHK015 Deploy cruzado (bundle antigo × backend novo e o inverso) tem comportamento definido em cada contrato? [contracts/api.md; Spec P-34]
- [x] CHK016 Entradas ruins da conta (NaN, negativo, base ≤ 0, valores do navegador fora do total) estão cobertas sem exceção? [Spec FR-002; Research R1, R2]
- [x] CHK017 Cada FR de dinheiro tem pelo menos um cenário do verify, e os "deve falhar" de PIX e RBAC estão na tabela? [Spec §Verificação]

## RBAC

- [x] CHK018 A matriz de papéis cobre os seis contratos alterados, inclusive a ordem das guardas (301 antes do PIX)? [Spec §RBAC; contracts/api.md]
- [x] CHK019 Está dito que nenhum dado de PIX vai ao histórico do evento? [Spec FR-011, FR-021]

## Notas

Todos passam depois das correções da pesquisa (14/10). Os itens não marcados levariam a pergunta ao dono;
nenhum ficou.
