# Checklist: Dinheiro e regressão — feature 307

**Purpose**: testar a qualidade dos requisitos de preço/cachê da faixa de Natal e da paridade do que
não muda (unit tests da spec, não do código)
**Created**: 2026-10-15
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [data-model.md](../data-model.md) ·
[contracts/api.md](../contracts/api.md)
**Depth**: portão de release · **Audience**: autor e revisor antes do implement

## Números da faixa

- [x] CHK001 - Os valores padrão da faixa (dias, markup, cachês de Noel/Ajudante/Coordenador, piso, nota) estão todos quantificados, inclusive para 2h–4h? [Completeness, Spec §FR-001]
- [x] CHK002 - O preço resultante de cada composição-chave (Noel; Noel + 1; 2h; noturno; boneco pelo piso) está escrito como número exato, não como "≈"? [Measurability, Spec §História 1, §Verificação]
- [x] CHK003 - A regra do piso diz a quem se aplica (todo performer sem sobrescrita: ator, boneco, cantor, especial) e a quem não (coordenador, técnico, maquiador)? [Clarity, Spec §FR-005, §Premissas]
- [x] CHK004 - Está definido que a faixa substitui também o markup de show e que o coordenador da faixa vale com e sem show? [Completeness, Spec §Casos de borda, §Premissas]
- [x] CHK005 - A ordem da faixa em relação a brinde, noturno, técnico, maquiador, transporte, acréscimos e NF está declarada (faixa antes; o resto como hoje)? [Consistency, Spec §FR-005, data-model §4]
- [x] CHK006 - A sobrescrita de cachê de um especial com variantes (show/cantor) tem comportamento definido? [Clarity, Spec §FR-005]
- [x] CHK007 - O comportamento do noturno e do PIX −5 % na faixa está decidido e escrito (continuam como hoje), com o número resultante? [Clarity, Spec §Clarifications, §História 1.3]
- [x] CHK008 - "Cada hora extra custa o preço cheio" está expresso como valores de tabela (cachês lineares + markup igual), não como regra de código nova? [Consistency, Spec §FR-001, §Premissas]

## Paridade sem faixa (regressão)

- [x] CHK009 - Está definido o que "idêntico ao de hoje" cobre (totais, memória, mensagem, PDF) e o que pode mudar (chaves opcionais neutras no quote)? [Clarity, Spec §FR-006]
- [x] CHK010 - Snapshots antigos sem `event_date`, entradas legadas sem snapshot e orçamentos já salvos têm comportamento definido? [Coverage, Spec §Casos de borda, §FR-014]
- [x] CHK011 - A neutralidade do EducaManto é um requisito com cenário próprio? [Coverage, Spec §FR-010, §História 6]
- [x] CHK012 - A linha de base da regressão das features 305 e 273 está declarada (273 em 8/15)? [Measurability, Spec §Verificação 17]
- [x] CHK013 - "Recalcular" um orçamento antigo de 24/12 tem resultado definido (reaplica a faixa; o salvo fica congelado)? [Clarity, Spec §Casos de borda]
- [x] CHK014 - O orçamento personalizado na faixa tem definido o que muda (valor digitado vence) e o que fica (nota e `data_especial` informativos)? [Clarity, Spec §História 1.8, §Casos de borda]

## Migração do `pricing_config`

- [x] CHK015 - A condição exata para trocar "Papai Noel" (valor antigo literal) e o que acontece com valor editado estão escritos? [Clarity, Spec §FR-002, §História 2]
- [x] CHK016 - A inserção de "Ajudante do Noel" respeita a lista de excluídos, e isso está dito? [Completeness, Spec §História 2.3]
- [x] CHK017 - A exigência de leitura defensiva (nunca cair nos DEFAULTS do código) tem cenário com entradas malformadas enumeradas? [Coverage, Spec §FR-003, §História 4.4, §Verificação 12]
- [x] CHK018 - O efeito de um rollback do deploy sobre um bloco já gravado pela tela está considerado? [Edge Case, Spec §Premissas]

## Validação do `POST /settings`

- [x] CHK019 - Cada campo do bloco tem regra, limite e mensagem de erro definidos (dias, markup 1,0–6,0, cachês, nomes existentes, nota ≤ 200)? [Completeness, contracts/api.md]
- [x] CHK020 - O cenário de papel sem permissão (403) é um cenário que deve falhar? [Coverage, Spec §Verificação 14]
- [x] CHK021 - O comportamento para dia repetido em duas faixas está definido (primeira faixa vence)? [Clarity, data-model §1]

## Teto das vagas

- [x] CHK022 - Está definido qual data manda no teto em cada caminho (criação e vínculo: data do evento; prefill: data do orçamento)? [Clarity, Spec §FR-009, §História 3.3]
- [x] CHK023 - O teto dos performers fora da sobrescrita na faixa (piso) e dos papéis de apoio (técnico, maquiador: inalterados) está escrito? [Completeness, Spec §História 3.4, §Premissas]
- [x] CHK024 - O comportamento fora de SP na faixa (teto = cachê da faixa + km, ajuste manual pelo superadmin) está registrado como aceito? [Edge Case, Spec §Casos de borda]
- [x] CHK025 - Está dito que os tetos seguem a tabela vigente no momento da criação/vínculo (não a do orçamento)? [Assumption, Spec §Premissas]

## Notas

- Conferida em 15/10/2026 contra a spec revisada na mesma sessão: CHK006, CHK014, CHK018, CHK021
  e CHK023 eram lacunas e foram fechadas na spec/data-model antes de marcar.
