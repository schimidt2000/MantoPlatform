<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Conta e dinheiro Checklist: Feature 313 — desconto e PIX na calculadora

**Propósito**: os requisitos da conta (ordem, base, arredondamento, BV, PIX) estão completos, claros e coerentes?
**Created**: 2026-10-21
**Feature**: [spec.md](../spec.md)

**Nota**: gerado pelo `/speckit-checklist`; avaliado item a item contra spec, plan, research e contracts em
21/10. Itens marcados = o requisito existe e é verificável; a evidência vai entre parênteses.

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

- [ ] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs)
- [ ] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo
- [ ] CHK003 `verify_313.py` verde contra `manto_local`, escrita conferida por conexão separada, um cenário que falha
- [ ] CHK004 Tela aberta de verdade (calculadora, orçamento gerado, PDF, Novo evento sem salvar)
- [ ] CHK005 Sem migration (nenhuma mudança em `models.py`)
- [ ] CHK006 Não toca o `startCommand`
- [ ] CHK007 RBAC inalterado e declarado em `docs/01` §4.3
- [ ] CHK008 Docs por fonte única: `docs/01`, `docs/02`, `docs/03`, `docs/04`, `docs/05`

## Ordem da conta (Q7/Q9)

- [x] CHK009 A ordem dos passos do pedido (acréscimo manual → BV em % → BV em reais → nota) está escrita sem
  ambiguidade? [Clarity, Spec §FR-006; research R1]
- [x] CHK010 Está definido sobre que número o BV em % incide (base + acréscimos manuais, sem a nota, sem outro BV)?
  [Clarity, Spec §FR-006, H3 cenário 2 e 4]
- [x] CHK011 Está definido quantas vezes o acréscimo em R$ e o BV em reais entram na duração extra (uma)?
  [Completeness, Spec §FR-006/§FR-007, H3 cenários 1 e 3]
- [x] CHK012 A régua da duração extra diz o que escala (só a base) e o que fica fixo (o produto, 309)? [Clarity, Spec
  §FR-007; research R1]
- [x] CHK013 O acréscimo negativo tem tratamento definido? [Edge Case, Spec Session 2]

## Desconto (D3, Q1, Q8)

- [x] CHK014 A base do desconto (o total com transporte, acréscimos, BV e nota) e a posição dele na conta (o último
  passo) estão explícitas? [Clarity, Spec §FR-002, H1 cenário 3]
- [x] CHK015 O modo bilateral define qual duração sai exata e como as outras são calculadas? [Clarity, Spec §FR-001;
  research R5]
- [x] CHK016 Está definido o que acontece se as duas formas (% e valor) chegarem juntas? [Consistency,
  contracts/api.md: o valor vence]
- [x] CHK017 Os limites (0 < % < 100; valor > 0 e ≤ cheio; igual ao cheio = sem desconto) estão definidos?
  [Edge Case, Spec §FR-010; contracts]
- [x] CHK018 Está definido quais durações o "fechar por R$" aceita, inclusive com produto de tabela e só-produto?
  [Coverage, research R6; Spec H1 cenário 6]
- [x] CHK019 O desconto no personalizado tem regra? [Coverage, Spec Session 5; research R7]
- [x] CHK020 O desconto sobre o produto de tabela tem regra, registrada como premissa contestável? [Assumption, Spec
  Session 1]

## Arredondamento

- [x] CHK021 A regra do % mostrado (uma casa, para baixo, vírgula, sem ",0") está escrita e é a mesma na proposta e no
  selo do evento? [Consistency, Spec §FR-012/§FR-022, Session 6; research R5]
- [x] CHK022 O caso de borda do piso em float (10% achado pelo valor = 9,999…) está tratado? [Edge Case, research R5]
- [x] CHK023 O arredondamento dos totais com desconto e do PIX está definido, e o sem desconto preserva o de hoje
  byte a byte? [Clarity, research R4/R5]
- [x] CHK024 A comparação do "vale o maior" usa o % exato, não o arredondado? [Clarity, Spec §FR-004, H2 cenário 4]

## PIX (D4)

- [x] CHK025 A base do PIX (o cheio) e a regra `max(5%, negociado)` estão escritas, sem soma? [Clarity, Spec §FR-004]
- [x] CHK026 As duas frases do bloco "À Vista (PIX)" (negociado < 5% e ≥ 5%) estão definidas para mensagem e PDF?
  [Completeness, Spec §FR-013; contracts; research R10]
- [x] CHK027 O 5% vem de uma constante única (não de um terceiro literal)? [Consistency, research R4]

## BV que acompanha (3a-Q1)

- [x] CHK028 A fórmula do BV no orçamento (cheio × final ÷ cheio) e no PIX está definida, pela função da 305?
  [Clarity, Spec §FR-005; data-model]
- [x] CHK029 O denominador do BV no evento (o cheio, não o total com desconto) está definido para criação, vínculo e
  alerta? [Completeness, Spec §FR-023; research R3]
- [x] CHK030 A proporção entre líquidos (nota) da 305 está preservada no requisito? [Consistency, research R3]
- [x] CHK031 O caso da venda digitada diferente do orçamento (PIX por cima) tem resultado de BV definido?
  [Coverage, Spec H4 cenário 3]
- [x] CHK032 A dedução da duração pelo valor continua definida com cheio ≠ venda? [Edge Case, Spec §FR-023]

## Notas

- Lacunas achadas e corrigidas nos documentos nesta rodada: a proporção entre líquidos (research R3) e o valor final
  igual ao cheio (contracts).
- Nenhuma pergunta nova ao dono.
