<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Feature 307 — Papai Noel em data especial: a tabela de preços tem os valores de 24 e 25/12 e a calculadora os aplica pela data do evento

**Branch**: `307-natal-papai-noel-calculadora` (da `main`) · **Created**: 2026-10-15 · **Status**:
Implementada em 15/10/2026 — `verify_307.py --regressao` 18/18, typecheck limpo, telas conferidas;
aguardando o "push" do dono ·
**Migration**: nenhuma (tudo mora no JSON `pricing_config` de `site_settings` e no snapshot do
orçamento, que já guarda a data do evento) · **Nível**: 1 (feature) — regra de negócio nova em dois
domínios (`app/orcamento/` e o teto de cachê em `app/calendar/`), tela de configuração alterada,
EducaManto tem de ficar neutro

**Input**: pedido do dono (15/10/2026): "A gente precisa colocar na tabela de valores que já tem no
sistema os valores do dia 24 ou 25 e ter algum tipo de trigger para, quando a data selecionada for
essa, o cálculo ser feito diferente, com markup diferente." Análise e decisões no plano aprovado
(`.claude/plans/precisamos-fazer-uma-pequena-compressed-platypus.md`) e na planilha
`Logistica Natal 2025.xlsx` (20 visitas em 24/12/2025, R$ 52.300 de cachês).

## O pedido, nas palavras do dono *(obrigatório)*

"O Natal é uma das épocas em que a gente consegue fazer mais dinheiro do ano. No ano passado a gente
fazia uma tabelinha e mandava para os clientes. Agora a gente usa o sistema, então o ideal é que eu
consiga colocar essas regras dentro do sistema: Papai Noel, ajudante. A gente tem que achar um valor
para o Papai Noel que seja diferenciado tanto antes do dia 23 quanto nos dias 24 e 25, e também o valor
para o artista — chegar nesse valor usando markups diferentes, por ser uma data especial. A gente não
pode fugir muito desse valor, mas tem que pensar na otimização para ganhar bastante dinheiro. Para
ontem."

A tabela de 2025 que ia para os clientes: até 23/12 — Papai Noel R$ 2.500, Papai Noel + 1 ajudante
R$ 3.600; em 24 e 25/12 — R$ 5.000 e R$ 6.500; valores para a cidade de São Paulo; visita de até
30 minutos; até 10 presentes fornecidos pelo contratante.

**O sintoma de hoje**: o especial "Papai Noel" tem cachê 600 e o markup real é 2,6, então a
calculadora dá R$ 2.210; em 24 dos 37 orçamentos com Noel a comercial soma um acréscimo "Outro" de
R$ 800–1.800 à mão para chegar perto da tabela. Esse acréscimo é margem pura: o teto de cachê do
artista continua em 600 e o casting não consegue pagar o cachê de Natal sem o superadmin.

### Clarifications (respostas do dono em 15/10/2026 — não reabrir)

- **Gatilho**: pela **data do evento** digitada na calculadora, não por botão manual ("quando a
  data selecionada for essa, o cálculo é feito diferente").
- **Markup de 24 e 25/12 = 3,34** sobre os cachês reais de 2025 (Noel 1.000, ajudante 650,
  coordenador 500): Noel sozinho ≈ R$ 5.010, Noel + 1 ajudante ≈ R$ 7.181, Noel + 2 ≈ R$ 9.352. Um
  markup só não bate 5.000 e 6.500 ao mesmo tempo; o dono escolheu manter o Noel na tabela conhecida
  e subir ~10 % o pacote mais vendido.
- **Alcance**: a faixa vale para **qualquer orçamento na data** (boneco, show, princesa…); as
  sobrescritas de cachê são só de Papai Noel, Ajudante do Noel e Coordenador, e os demais personagens
  recebem um **piso de cachê** igual ao do ajudante (650) — senão Noel + boneco a 200 sairia mais
  barato que Noel + ajudante e com teto de 200, o contrário do que a empresa recomenda.
- **Nota para a cliente**: só a nota da data — "Valores especiais de 24 e 25 de dezembro." —
  editável na Configuração de Preços. Sem frase de presentes.
- **Faixa normal (até 23/12)**: tabela antiga 2.500 / 3.600 → Papai Noel passa de 600 para **712** e
  entra o especial **"Ajudante do Noel"** com **423** (com o markup 2,6 de produção: R$ 2.501 e
  R$ 3.601). A comercial para de somar o "Outro".
- **Custos fixos do dia** (maquiador(a), pessoa na base distribuindo figurinos) ficam **embutidos**
  no markup; nada de campo novo. A maquiagem continua opcional por performer.
- **Noturno** (+R$ 50/pessoa a partir das 19h) e **PIX à vista −5 %** continuam como hoje.
- **Horas extras na faixa** (premissa do plano, não palavra do dono — editável na tela): cada hora
  custa o preço cheio (2h = 2 × 1h), porque o tempo do Noel é o recurso escasso na véspera; com os
  defaults de progressão normal, 4h de Noel sairiam por só +17 % sobre 1h.

#### Session 2026-10-15 (`/speckit-clarify`)

Nenhuma ambiguidade crítica: gatilho, alcance, markup, cachês, nota, faixa normal, noturno, PIX e
custos embutidos foram decididos pelo dono em 15/10 e estão transcritos acima. A única leitura do
plano — horas extras lineares na faixa (2h = 2 × 1h) — é um default editável na Configuração de
Preços e está marcada como premissa; se o dono preferir a progressão normal, muda pela tela, sem
código. Cobertura: escopo, papéis, dados, fluxo, bordas, RBAC, integração (EducaManto) e critérios
mensuráveis — tudo Clear; desempenho e observabilidade não mudam (a faixa é uma leitura a mais da
tabela já carregada).

## Cenários e Verificação *(obrigatório)*

### História 1 — Orçamento em 24 ou 25/12 sai pela tabela de Natal (Prioridade: P1)

A comercial monta um orçamento com Papai Noel (e ajudante) e digita a data 24/12. Sem clicar em nada
a mais, o resultado usa o markup 3,34 e os cachês de Natal, a memória de cálculo mostra "Véspera e
Natal", a mensagem do WhatsApp e o PDF trazem a nota da data, e o orçamento salvo guarda tudo isso
congelado. Em 20/12 o mesmo orçamento sai pela tabela normal.

**Por que esta prioridade**: é o pedido literal do dono; hoje o preço de Natal depende de a comercial
lembrar de um acréscimo manual.

**Verificação**: cenários 3–9, 15 e 16 do `verify_307.py`.

**Cenários de aceite**:

1. **Dado** a tabela com a faixa "Véspera e Natal" (dias 24/12 e 25/12, markup 3,34, Noel 1.000,
   Ajudante 650, Coordenador 500, piso 650), **Quando** a comercial orça Papai Noel em 2026-12-24 com
   1 coordenador, **Então** o total de 1h é **R$ 5.010,00**, o quote traz `data_especial` com o
   rótulo "Véspera e Natal" e a nota, a linha "× Markup" da memória tem o detalhe "Véspera e Natal ·
   24/12", a mensagem termina o bloco de investimento com "_Valores especiais de 24 e 25 de
   dezembro._" e o PIX à vista continua −5 % (**R$ 4.759,50**).
2. **Dado** o mesmo elenco mais "Ajudante do Noel" em 2026-12-25, **Então** 1h = **R$ 7.181,00**.
3. **Dado** o cenário 1 às 20h, **Então** o noturno segue somando por fora: **R$ 5.110,00**.
4. **Dado** Papai Noel + um boneco (ator boneco, cachê de tabela 200) em 24/12, **Então** o boneco
   entra pelo piso 650 e o total é igual ao de Noel + Ajudante (R$ 7.181,00); a memória marca
   "piso da data especial".
5. **Dado** "Perna de Pau" sozinho em 24/12, **Então** o markup é 3,34 e o cachê é o maior entre a
   tabela (400) e o piso (650): **R$ 3.841,00** — o gatilho é a data, para qualquer produto.
6. **Dado** o cenário 1 com 2h incluída, **Então** 2h = 2 × 1h (R$ 10.020,00), por os cachês da
   faixa serem lineares por hora e o markup igual nas quatro durações.
7. **Dado** um orçamento de 24/12 fora de SP (van, 50 km, deslocamento por conta da Manto),
   **Então** o transporte da 262 soma por cima do R$ 5.010 exatamente como somaria hoje.
8. **Dado** um orçamento personalizado em 24/12, **Então** o valor digitado vence; `data_especial`
   vem preenchido só como informação.
9. **Dado** um orçamento de 24/12 com acréscimo BV 10 %, **Então** `valores_brl` do BV é 10 % do
   total pós-faixa (a 305 continua válida: a faixa age antes dos acréscimos).
10. **Dado** o mesmo orçamento em 2026-12-20, **Então** `data_especial` é `None`, o markup é o normal
    e não há nota.

---

### História 2 — A tabela normal já vende o Noel e o ajudante pela tabela de 2.500 / 3.600 (Prioridade: P1)

Depois do deploy, sem ninguém mexer na tela, a Configuração de Preços mostra "Papai Noel" com 712 e a
linha nova "Ajudante do Noel" com 423. Um orçamento de 20/12 com Papai Noel sai a R$ 2.501 e com o
ajudante a R$ 3.601. Se o time tiver editado o Papai Noel antes do deploy, o valor dele não é tocado.

**Por que esta prioridade**: fecha a faixa "até 23/12" do pedido e tira o acréscimo manual do
caminho — e é o que vale **hoje**, mesmo que o deploy atrase (dá para fazer pela tela).

**Verificação**: cenários 1, 2 e 12.

**Cenários de aceite**:

1. **Dado** uma configuração salva com "Papai Noel" exatamente em `[600, 650, 675, 700]` e sem
   "Ajudante do Noel", **Quando** a configuração é carregada, **Então** "Papai Noel" vale
   `[712, 800, 850, 900]` e "Ajudante do Noel" `[423, 480, 510, 540]`.
2. **Dado** "Papai Noel" já editado para outro valor, **Então** fica como está.
3. **Dado** "Ajudante do Noel" na lista de especiais excluídos, **Então** não volta.
4. **Dado** a configuração carregada com markup 2,6 e coordenador 250, **Quando** se orça Papai Noel
   em 2026-12-20, **Então** 1h = **R$ 2.501,20**; com Ajudante do Noel, **R$ 3.601,00**.

---

### História 3 — O teto de cachê das vagas do evento honra a data (Prioridade: P1)

A comercial cria o evento a partir do orçamento de 24/12 (ou vincula o orçamento a um evento já
marcado). As vagas nascem com teto Noel 1.000, Ajudante 650, Coordenador 500 (mais o noturno quando
houver), e o casting escala e lança o cachê de Natal sem pedir ao superadmin. Um evento de 20/12 nasce
com o teto normal.

**Por que esta prioridade**: sem isso o preço sobe e o artista continua travado em 600 — o mesmo
defeito do acréscimo manual de hoje.

**Verificação**: cenário 11.

**Cenários de aceite**:

1. **Dado** o snapshot de um orçamento de 24/12 com Papai Noel + Ajudante do Noel + 1 coordenador,
   **Quando** os tetos são calculados para a criação do evento, **Então** Papai Noel `cache_1h` =
   1.000, Ajudante 650, Coordenador 500 (+50 cada se o horário for ≥ 19h) e a nota do teto cita
   "Véspera e Natal".
2. **Dado** o mesmo snapshot em 20/12, **Então** 712 / 423 / 250.
3. **Dado** um orçamento de 20/12 vinculado a um evento marcado para 24/12, **Então** o teto segue a
   data do **evento** (1.000 / 650 / 500) — o artista é pago pelo dia em que trabalha.
4. **Dado** um boneco no snapshot de 24/12, **Então** o teto dele é o piso (650), não 200.

---

### História 4 — O superadmin edita a faixa na Configuração de Preços (Prioridade: P2)

Na tela de Configuração de Preços aparece o card "Datas especiais — Natal": os dias (24/12, 25/12),
o markup por duração, os cachês sobrescritos por item, o cachê do coordenador, o piso dos demais e a
nota da mensagem. Salvar persiste tudo pelo mesmo botão "Salvar configurações"; um dia inválido ou um
markup absurdo é recusado com o campo apontado.

**Por que esta prioridade**: é "a tabela de valores que já tem no sistema" — o dono ajusta número sem
deploy; mas os defaults já valem sem a tela.

**Verificação**: cenários 13 e 14 (um deles **deve falhar**).

**Cenários de aceite**:

1. **Dado** o superadmin logado, **Quando** salva a configuração com `datas_especiais.natal` alterado
   (markup 3,5; dia "12-26" a mais), **Então** o `GET /api/orcamento/opcoes` devolve o bloco salvo e
   um orçamento de 26/12 passa a cair na faixa.
2. **Dado** um dia "13-40" ou um markup 33,4, **Então** 400 com o campo nomeado e nada é gravado.
3. **Dado** uma Comercial, **Quando** tenta salvar a configuração, **Então** 403. **(deve falhar)**
4. **Dado** uma configuração gravada com `datas_especiais` nulo ou malformado, **Quando** a
   calculadora carrega a tabela, **Então** o markup 2,6 e os especiais reais continuam valendo (o
   bloco ruim é trocado pelo padrão, sem derrubar o resto).

---

### História 5 — A calculadora avisa e não grava resultado velho (Prioridade: P2)

Ao digitar 24/12, assim que o resultado volta do servidor, a comercial vê um aviso dourado sob a
data: "🎄 Data especial — Véspera e Natal: markup 3,34× e cachês próprios. Vale para qualquer
orçamento nesta data. Use o item "Ajudante do Noel" (não ator cara limpa) e não some o acréscimo
"Outro" — o preço já é o da tabela especial." Com a data vazia, uma dica diz "Em 24/12 e 25/12 a
tabela especial entra pela data" (dias lidos da tabela). O painel de resultado e o orçamento salvo
mostram "🎄 Valores da data especial: Véspera e Natal." "Gerar Orçamento" vira "Recalculando…" e
fica travado do momento em que o payload muda até o resultado novo chegar (uma resposta antiga que
chegue depois é descartada), para não salvar o preço da data anterior.

**Por que esta prioridade**: a data é opcional e o preço agora depende dela; e o botão hoje salva o que
está na tela mesmo durante o recálculo.

**Verificação**: conferência de tela no Browser pane (calculadora com data vazia, 20/12 e 24/12;
Configuração de Preços, inclusive um 400 apontando o campo; resultado) — não há cenário de API.

**Cenários de aceite**:

1. **Dado** a calculadora com data 2026-12-24, **Então** o aviso dourado aparece com o rótulo e o
   markup "3,34×" (pt-BR); com 2026-12-20 ele some; com a data vazia aparece a dica.
2. **Dado** a troca da data de 20/12 para 24/12, **Quando** a comercial clica "Gerar Orçamento" antes
   de o recálculo voltar, **Então** o botão está desabilitado ("Recalculando…"); habilita quando o
   resultado novo chega.
3. **Dado** a Configuração de Preços com markup 33,4 na faixa, **Quando** o superadmin salva,
   **Então** o card mostra o erro do campo e o foco vai ao primeiro campo inválido; nada se perde.

---

### História 6 — O EducaManto não muda (Prioridade: P3)

Um orçamento do EducaManto com contratação Manto marcada para 24/12 sai igual ao de qualquer outra
data: o musical não tem Visita Mágica.

**Verificação**: cenário 10.

**Cenários de aceite**:

1. **Dado** a contratação Manto do EducaManto com `event_date` 2026-12-24 no payload, **Então** os
   totais são iguais aos de 2026-12-20.

---

### Casos de borda

- Data vazia ou inválida (`"2026-13-01"`, `"24/12"`): nenhuma faixa; preço normal, sem erro.
- Orçamento salvo antes do deploy para 24/12: continua com o preço congelado (regra 020). "Recalcular"
  reaplica a faixa — é um orçamento novo.
- Orçamento personalizado na faixa: o valor digitado vence; `data_especial` e a nota da mensagem
  continuam (afirmam a data, não o valor), e o teto das vagas segue a faixa — o artista trabalha na
  véspera de qualquer jeito.
- Snapshot antigo sem `event_date` e entrada legada sem snapshot: `data_especial` ausente/`None`; PDF
  e tela não quebram.
- Orçamento com show em 24/12: o markup da faixa substitui também o de show; técnico e brinde entram
  como hoje; o coordenador, com ou sem show, usa a lista `coordenador` da faixa.
- Especial com sobrescrita excluído da tabela: a exclusão tira a sobrescrita dele de todas as
  faixas (servidor e tela); ao salvar, nome desconhecido em `cache` é recusado com o campo nomeado.
- Configuração gravada com `datas_especiais` nulo, lista em vez de dict, faixa sem `dias` ou markup
  com 3 valores: a leitura normaliza ou substitui pelo padrão **sem** devolver os DEFAULTS do código
  para o resto da tabela (isso apagaria os preços reais). Sobrescrita de cachê malformada é
  descartada (o especial volta para tabela + piso) — nunca vira cachê zero.
- Orçamento de 20/12 (preço normal) vinculado a um evento de 24/12: o teto segue o evento (Noel
  1.000) e a margem encolhe — aceito; o vínculo 273 não alerta (recalcular o orçamento é o remédio).
- Comercial que, por hábito, soma o "Outro" num orçamento de 24/12: cobra em dobro. A faixa dourada
  avisa; não há bloqueio.
- Fora de SP em 24/12: o teto do coordenador é 500 + km×2÷3, abaixo do que se pagou no litoral em
  2025 (1.250); o superadmin ajusta o teto à mão — comportamento já existente.
- Vaga vinda do Google com nome diferente do rótulo do orçamento (ex.: "Ajudante Papai Noel") não casa
  no vínculo 273 e fica sem teto — comportamento já existente.

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: A tabela de preços DEVE ter um bloco `datas_especiais`, com uma ou mais faixas, cada
  uma com rótulo, lista de dias (`MM-DD`, válidos todo ano; **lista vazia = faixa desligada**),
  markup por duração `[1h, 2h, 3h, 4h]`, sobrescrita de cachê por item especial, cachê do
  coordenador, piso de cachê dos demais performers e nota da mensagem. O padrão é a faixa `natal`
  ("Véspera e Natal", `12-24` e `12-25`, markup `[3.34, 3.34, 3.34, 3.34]`, Papai Noel
  `[1000, 2000, 3000, 4000]`, Ajudante do Noel `[650, 1300, 1950, 2600]`, coordenador
  `[500, 1000, 1500, 2000]`, piso `[650, 1300, 1950, 2600]`, nota "Valores especiais de 24 e 25 de
  dezembro."). A tela edita a faixa `natal`; criar outra faixa é pelo JSON (fora de escopo na tela).
- **FR-002**: Ao carregar a tabela, o sistema DEVE garantir o bloco em configurações antigas, inserir o
  especial "Ajudante do Noel" `[423, 480, 510, 540]` quando ausente e não excluído, e trocar "Papai
  Noel" de `[600, 650, 675, 700]` (o valor antigo) para `[712, 800, 850, 900]` — nunca tocando um
  valor já editado.
- **FR-003**: A leitura da tabela DEVE ser defensiva: bloco ou faixa malformados são substituídos pelo
  padrão; nenhuma exceção ali pode fazer a tabela inteira cair nos DEFAULTS do código.
- **FR-004**: O cálculo do orçamento DEVE determinar a faixa a partir de `event_date` (`AAAA-MM-DD`
  → `MM-DD` ∈ dias), por recorte de texto, sem fuso horário; data vazia ou inválida = nenhuma faixa.
- **FR-005**: Com faixa, o cálculo DEVE usar o markup da faixa no lugar do normal (receptivo e show),
  os cachês sobrescritos para os especiais nomeados (a sobrescrita vale para qualquer variante do
  especial — show, cantor ou simples), o cachê do coordenador da faixa (com e sem show) e, para
  qualquer outro performer (ator, boneco, cantor ou especial sem sobrescrita), o maior entre o cachê
  de tabela e o piso — tudo antes de brinde, noturno, técnico, maquiador, transporte, acréscimos e
  nota fiscal, que seguem como hoje. Técnico de som e maquiador não mudam na faixa.
- **FR-006**: Sem faixa, totais, memória, mensagem e PDF DEVEM ser idênticos aos de hoje; `quote` e
  snapshot ganham apenas chaves opcionais neutras.
- **FR-007**: O `quote` DEVE trazer `data_especial` (`{chave, rotulo, markup, nota_mensagem}` ou
  `None` — a nota vai junto porque o PDF e o orçamento congelado não releem a tabela) e
  `markup_used` igual ao markup aplicado; a memória de cálculo DEVE nomear a faixa na linha do markup
  (detalhe `"Véspera e Natal · 24/12"`) e marcar os cachês sobrescritos ("cachê da data especial") e
  os elevados ao piso ("piso da data especial").
- **FR-008**: A mensagem do WhatsApp e o PDF DEVEM trazer a nota da faixa, em itálico (no PDF,
  `Helvetica-Oblique` com quebra de linha na largura útil), junto da frase de deslocamento; entradas
  antigas sem a chave não quebram.
- **FR-009**: O teto de cachê das vagas (prefill, criação do evento e vínculo 273) DEVE honrar a
  faixa pela data do evento quando ela existe, e pela data do orçamento no prefill; a nota do teto
  cita a faixa.
- **FR-010**: A contratação Manto do EducaManto DEVE continuar neutra: a data do evento não entra no
  cálculo dela.
- **FR-011**: O superadmin DEVE poder editar o bloco pela Configuração de Preços; a validação mora
  no núcleo (`settings.validar_datas_especiais`, exceção própria com `fields`) e o endpoint só a
  traduz em 400: chave `^[a-z0-9_]{1,30}$`, rótulo 1–60 (mais longo é recusado, não cortado), dias
  (`MM-DD` reais, sem repetição — repetido é recusado, não deduplicado — e sem dia que já esteja em
  outra faixa; vazio aceito = faixa desligada), markup (4 valores finitos entre 1,0 e 6,0, gravados
  com 2 casas HALF_UP), coordenador e piso (4 valores ≥ 0 — string inválida, negativo ou infinito é
  erro, nunca default), sobrescritas de cachê só para especiais existentes e com 4 valores **> 0**
  (a sobrescrita passa por fora do piso: zero viraria cachê zero na venda e no teto) e nota ≤ 200
  caracteres numa linha só. O bloco enviado SUBSTITUI o salvo; corpo inválido não grava nada;
  remover a chave `natal` não desliga a faixa (a carga a recria — desligar é `dias: []`); a tela
  destaca o campo recusado (inclusive as linhas da tabela) e leva o foco até ele; papéis sem
  permissão levam 403. Excluir um especial tira a sobrescrita dele de todas as faixas (servidor e
  tela); sobrescrita de especial que não existe mais é descartada na carga.
- **FR-012**: A calculadora DEVE mostrar aviso visível quando a data cair numa faixa e uma dica quando
  a data estiver vazia; o resultado e o orçamento salvo DEVEM indicar a faixa.
- **FR-013**: "Gerar Orçamento" DEVE ficar desabilitado enquanto houver recálculo pendente (desde a
  mudança do payload até a resposta), e após erro de cálculo.
- **FR-014**: Orçamentos já salvos DEVEM permanecer congelados; a faixa só vale para cálculos novos.

### Entidades *(se houver dados)*

- **`pricing_config.datas_especiais`** (JSON em `site_settings`, linha única): `{<chave>: {rotulo,
  dias[], markup[4], cache{<especial>: [4]}, coordenador[4], piso[4], nota_mensagem}}`. Sem migration.
- **`quote.data_especial`** (JSON em `orcamento_history.result_snapshot`): `{chave, rotulo,
  markup[4], nota_mensagem}` ou `None`. `form_snapshot.event_date` já existe.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

- `POST /api/orcamento/settings` — alterado (aceita `datas_especiais`): SUPERADMIN
  (`_require_superadmin`, Princípio XIII); linha de `docs/01` §4.3 revisada.
- `POST /api/orcamento/calcular`, `GET /api/orcamento/opcoes` — contrato ampliado, gate inalterado
  (COMERCIAL ou SUPERADMIN; FINANCEIRO 403).
- Nenhum endpoint novo.

## Verificação (`verify_307.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/307-natal-papai-noel-calculadora/verify_307.py`, contra `manto_local`
(`DATABASE_URL` de `.local-db-url`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`). Login só por
`POST /api/auth/login` com usuários descartáveis (SUPERADMIN e COMERCIAL), cookie do próprio
`test_client`; a configuração de preços real é lida no início, substituída por uma configuração de
teste (markup 2,6; coordenador 250; **Papai Noel no cachê antigo `[600, 650, 675, 700]`, sem
"Ajudante do Noel" e sem `datas_especiais`** — a migração é que entrega 712/423/faixa) e
**restaurada no `finally`** por conexão separada; orçamentos descartáveis são apagados no `finally`
(nenhum evento é gravado: o vínculo 273 é provado com um evento transitório e espião). Sem a
feature, 1–9, 11–13, 15 e 16 ficam vermelhos; 10 e 14 passam por desenho (paridade e gate já
existentes) — a prova está em `verify_307_primeira_falha.txt`. **O portão é a rodada com
`--regressao`**: sem a flag o cenário 17 sai como PULADO, fora da contagem.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | `2026-12-20`, Papai Noel 1h, 1 coord | `total_1h == 2501.20`, `markup_used == [2.6, …]`, `data_especial is None`, mensagem sem nota | não |
| 2 | `2026-12-20`, Noel + Ajudante do Noel | `total_1h == 3601.00` | não |
| 3 | `2026-12-24`, Papai Noel | `5010.00`; `data_especial` com rótulo e nota; linha "× Markup" com detalhe "Véspera e Natal · 24/12"; cachê marcado "cachê da data especial"; PIX à vista R$ 4.759,50; mensagem e PDF com a nota | não |
| 4 | `2026-12-25`, Noel + Ajudante | `7181.00` | não |
| 5 | `2026-12-24` às `20:00` | `5110.00` (noturno por fora) | não |
| 6 | `2026-12-24`, Noel + ator boneco (200) | boneco entra pelo piso 650 → `7181.00`; memória marca o piso | não |
| 7 | `2026-12-24`, "Perna de Pau" sozinho | markup 3,34; cachê = max(400, 650) → `3841.00` | não |
| 8 | `2026-12-24`, 2h incluída | `total_2h == 10020.00` | não |
| 9 | `2026-12-24` + fora de SP (van, 50 km, manto) e `2026-12-24` + personalizado e `2026-12-24` + BV 10 % | transporte somado igual a hoje; personalizado vence; `snapshot.acrescimos[0].valores_brl[0] == 501.00` | não |
| 10 | EducaManto `_totais_contratacao` com `event_date` 24/12 (depois de provar que o cálculo direto 24/12 ≠ 20/12) | totais iguais aos de 20/12 | não |
| 11 | `_compute_performer_caches` com snap 24/12; snap 20/12; snap 20/12 com `data_evento="2026-12-24"`; boneco no snap 24/12; **vínculo 273** com evento transitório de 24/12 e orçamento de 20/12 (espião captura `data_evento`) | 1000/650/500 (+50 se noturno); 712/423/250; 1000/650/500; piso 650 com `cap_notes` explicando; `cap_notes` cita a faixa; o vínculo passa "2026-12-24" (e `None` sem `start_at`) | não |
| 12 | migração da configuração | Papai Noel `[600,…]` → `[712,…]`; `[650,…]` intocado; "Ajudante do Noel" injetado e respeitando `especiais_excluidos`; `datas_especiais` nulo/malformado → padrão, markup 2,6 e especiais reais preservados; sobrescrita malformada descartada; `dias: []` = desligada | não |
| 13 | `POST /api/orcamento/settings` (SUPERADMIN) com markup 3,5 e dia 26/12; depois dia `"13-40"`, markup `33.4`, especial desconhecido, piso negativo, coordenador não numérico; depois markup 3,335 e `dias: []` | persiste (conferido por conexão separada) e 26/12 → 5.250; 400 com `fields` em cada inválido e nada gravado; 3,335 grava 3,34 e dias vazio desliga a faixa | não |
| 14 | COMERCIAL tenta `POST /api/orcamento/settings` | 403 | **sim** |
| 15 | snapshot antigo sem `event_date`; `legacy_quote` | sem erro; `data_especial` ausente/None; PDF gera | não |
| 16 | memória de cálculo de 24/12 soma com o total (regra do hotfix 210) | cachês × markup + pós = total | não |
| 17 | regressão: `verify_305 --regressao` (só com a flag `--regressao`; sem ela sai PULADO, fora da contagem) | 305 verde; 273 na linha de base 8/15 | não |
| 18 | limpeza | configuração real restaurada (conferida por conexão separada); usuários e orçamentos descartáveis apagados | — |

Conferência de tela: `/orcamento` com data 20/12, 24/12 e vazia (faixa, dica, botão travado durante o
recálculo); `/orcamento/configuracoes` (card "Datas especiais — Natal", salvar); `/orcamento/:id` de
um orçamento de 24/12 (nota). Superfície interna: viewport desktop.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Um orçamento de Papai Noel em 24 ou 25/12 sai no valor da faixa (≈ R$ 5.010 sozinho,
  ≈ R$ 7.181 com ajudante) **sem nenhum acréscimo manual** — a proporção de orçamentos de Noel com
  "Outro" cai de 65 % para zero nos orçamentos criados depois do deploy.
- **SC-002**: Um orçamento de Papai Noel até 23/12 sai a R$ 2.501 (R$ 3.601 com ajudante) no dia do
  deploy, sem ninguém editar a tabela.
- **SC-003**: Vagas de Noel, ajudante e coordenador de eventos de 24/25 criados a partir do orçamento
  nascem com teto 1.000 / 650 / 500, e o casting lança esses cachês sem superadmin.
- **SC-004**: Orçamentos sem data especial, o EducaManto e os orçamentos já salvos saem com os mesmos
  números de antes (paridade provada pelo verify) — exceto "Papai Noel" e "Ajudante do Noel", que
  mudam na tabela normal por decisão do FR-002.
- **SC-005**: O superadmin muda dias, markup e cachês da faixa pela tela, e a mudança vale no
  próximo cálculo, sem deploy.

## Fora de escopo

- Papai Noel na loja virtual (`alo.*` é chamada/vídeo — feature 304).
- Pacote "Visita Mágica" de 30 minutos com preço fechado (continua no espaço de 1h / "1 entrada de
  30 minutos").
- Markup diferente por item dentro do mesmo orçamento; "taxa da data" fixa em R$.
- Cachê automático nas vagas sem passar pelo orçamento; cachê por região fora de SP.
- Alerta "já na agenda" por talento em vez de por nome (vários Noéis no mesmo dia acusam venda em dobro).
- Bloquear boneco/show em 24 e 25/12 (é orientação do time, não regra de sistema).
- Costura do plano 3b do backlog (`docs/backlog/` não existe na `main`; fica para a 306).

## Docs a atualizar

`docs/01` §2.10 (`pricing_config.datas_especiais`), §3.13 (`data_especial` no quote; contrato de
`/orcamento/settings`), §4.3 (linha revisada), cabeçalho; `docs/02` A.7 (`/orcamento`: faixa e dica;
`/orcamento/:id`: nota; `/orcamento/configuracoes`: card novo); `docs/03` (entrada 307 no topo + índice
+ linha "Orçamento e EducaManto"; corrigir o cabeçalho, que não cita a 305 — o head de migration
`a7c3e91f4d28` continua certo); `docs/04` linha Orçamento (markup por faixa de data; teto segue a
data do evento; noturno é somado **depois** do markup — o texto atual diz "pré"; o valor antigo exato
do Noel é reescrito na carga); `docs/05` (dívidas a partir da 103: alerta "já na agenda" por nome;
rehydrate não restaura `incluir_duracao`/personalizado; select nativo de especiais do
`PerformersEditor` com 12 itens — violação já existente do Princípio XII.1, decisão do dono; linha
208 atualizada: `_compute_performer_caches` em `routes.py:2835`, ~260 linhas, ganhou
`data_evento`/faixa; `calculate_quote` e `settings_save` já excediam 30 linhas — a 307 só acrescentou
chamadas a helpers).

## Premissas

- O `pricing_config` de produção ainda tem "Papai Noel" em `[600, 650, 675, 700]` (espelho de
  30/09); se o time tiver editado, o guarda não troca e o dono ajusta pela tela. Quem digitar de
  volta exatamente `600/650/675/700` verá 712 na carga seguinte (o guarda compara o valor exato).
- A faixa `natal` sempre existe na tabela (a carga a recoloca se faltar); para desligá-la, basta
  deixar `dias` vazio.
- Cachês 2h–4h da faixa são lineares (2h = 2 × 1h) por decisão do dono; os da tabela normal seguem a
  progressão dos demais itens (`[712, 800, 850, 900]`, `[423, 480, 510, 540]`).
- O coordenador da faixa vale com e sem show (uma lista só).
- Os tetos continuam lidos da tabela **vigente** no momento da criação/vínculo, como hoje.
- Técnico de som e maquiador (vagas de apoio) não têm cachê de faixa: tabela normal, com e sem faixa.
- Rollback do deploy (git revert do merge): um bloco `datas_especiais` já gravado pela tela fica no
  JSON e é ignorado pelo código anterior — inofensivo; nada a desfazer no banco.
- Dia repetido em duas faixas: a primeira faixa do bloco vence (ordem de gravação); a tela não impede.
- A demanda de 25/12 foi zero em 2025; o dia fica na faixa por decisão de tabela, não por dado.
