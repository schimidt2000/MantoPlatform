# Feature 309 — Produtos de tabela: a Visita Mágica do Papai Noel vendida pelo preço da tabela de venda, com os cachês das vagas definidos pela tabela de preços

**Branch**: `309-produtos-de-tabela` (da `main` `6356b80`, em worktree `C:\tmp\mp309` — a árvore
principal está ocupada pela 308 de outro chat) · **Created**: 2026-10-19 · **Status**: Rascunho
(analyze aplicado em 19/10) · **Migration**: nenhuma (bloco novo no JSON `pricing_config` + chave
nova no snapshot do orçamento; chave ausente = comportamento de hoje) · **Nível**: 1 (feature —
orçamento + teto das vagas no calendário; EducaManto neutro) — constituição, Princípio VI

**Input**: pedido do dono (19/10/2026): "Nesses casos em que existe uma tabela de preços que vai ser
vendida à pessoa final, a gente talvez tenha que usar uma lógica diferente da da calculadora. Talvez
tenha que ter esse pacote fechado para a vendedora selecionar na calculadora: ela seleciona, e aí os
cachês estão definidos, apesar do valor final — porque hoje a nossa lógica é: os cachês definem o
valor final." Plano de análise (três desenhos concorrentes, três céticos):
`docs/backlog/308-produtos-de-tabela-visita-magica.md` (árvore principal, fora do repositório; o
número no nome ficou 308, o conteúdo é desta feature).

## O pedido, nas palavras do dono *(obrigatório)*

> "Justamente por essa afirmação de que 712 é o teto, é muito tendencioso que eles paguem o teto.
> Então talvez precise pensar numa lógica um pouco diferente. Talvez seja uma implementação um pouco
> maior, mas não tem problema. [...] De fato, antes dos dias 24 e 25, a gente mantém 600 para o Papai
> Noel. O coordenador, a gente paga o preço atualizado — não dá para manter o de 2025, tem que ser o
> de 2026, o que está escrito na tabela de configurações de preço dentro do sistema. Maquiador, mesma
> coisa. [...] Se eu mexer no markup quando tiver Papai Noel, um evento com um monte de personagens e
> o Papai Noel vai mandar um markup e vai afetar todos — não fica correto."
>
> Sobre a duração: "Esse valor de 2.500 ou 5.000 é para uma visita padrão, com tempo determinado e
> roteiro pré-determinado. Se a pessoa quiser um evento com 3 horas com Papai Noel, não tem nada a ver
> com essa tabela: aí a gente vai para o cálculo normal. Esse pacote é apenas para Visita Mágica:
> Papai Noel; Papai Noel e ajudante (duende)."

O sintoma que a feature resolve: desde a 307 a tabela de preços diz "Papai Noel 712 / Ajudante do
Noel 423" para o preço bater com a tabela de venda (R$ 2.500 / R$ 3.600) — e esse número é o **teto**
da vaga do evento. O pago real em 2025 foi **600 / 270** (planilha de pagamentos: 8 de 9 visitas a
600). Quem escala digita um valor acima, o sistema rebaixa ao teto e grava 712: "pagar o teto" é um
clique, e cachê não desce. A feature separa os dois números: o **preço** vem do produto de tabela; o
**cachê** vem da tabela de preços e vira o teto honesto.

## Clarifications

### Session 2026-10-19 (decisões do dono, antes do `/speckit-specify`)

- Q: O preço do produto escala por duração (1h–4h) ou é fixo? → A: **Fixo por visita.** O produto é só
  a Visita Mágica padrão (tempo e roteiro pré-determinados): Noel; Noel + ajudante. Evento de 3h com
  Papai Noel vai para o cálculo normal (avulso pela fórmula).
- Q: O adicional noturno (+R$ 50/pessoa a partir das 19h) soma sobre o produto? → A: **Embutido** — a
  tabela de venda é o preço; o cachê combinado não depende da hora. Avulsos continuam somando.
- Q: O que fazer com os especiais avulsos "Papai Noel" (712) e "Ajudante do Noel" (423)? → A:
  **Voltam a 600/270 e ficam na tabela** (cachê é cachê); a calculadora avisa "para a Visita Mágica
  use o produto"; não excluir os especiais em 2026.
- Q: Fatia 0 (hotfix 307b) antes desta feature? → A: **Não** — tudo nesta feature, inclusive a remoção
  da troca automática 600→712 e o script que rebaixa os tetos 712/423 já gravados.
- Coordenador e maquiador do produto: **pelo valor da tabela de 2026** (250 / 250; 500 para o
  coordenador em 24/25 pela faixa da 307) — não o pago em 2025.

### Session 2026-10-19 (`/speckit-clarify`)

- Q: Produto sem preço cadastrado para uma data de faixa especial (ex.: produto novo sem preço de
  24/25, vendido em 24/12) — o que a calculadora faz? → A: **Estima**: custo de cachê **dobrado** e
  markup **um pouco mais alto que o padrão** — o preço sai como estimativa marcada ("preço estimado:
  produto sem preço de 24/12"), nunca o preço normal em silêncio e nunca bloqueio. Fatores editáveis
  pelo superadmin (`produtos_estimativa`: `fator_cache` 2,0 · `markup` 3,0); o teto das vagas segue a
  tabela vigente na data (faixa), não a estimativa.
- Q: A Visita Mágica inclui a maquiagem do Noel no preço de tabela? → A: **Inclusa** — a vaga Maquiador
  nasce pela tabela (teto 250) e o cliente não paga à parte; make de avulso no mesmo orçamento cobra só
  o incremento.
- Q: Cachê dos especiais avulsos em 2h–4h? → A: **Noel 600 / 650 / 675 / 700 · Ajudante do Noel 270 /
  320 / 345 / 370** (tabela antiga do Noel; degrau do ator para o Ajudante).

### Session 2026-10-19 (`/speckit-analyze` — decisões técnicas registradas como premissas; o dono pode vetar)

- Régua >4h com produto: a parte **líquida** do produto fica fixa e os acréscimos %/NF incidem sobre a
  coluna custom como sobre as outras — UMA função (`produtos.total_na_duracao`) usada pela venda, pelo
  prefill, por `_total_da_duracao` e pelo BV da duração custom (305).
- **Uma vaga Maquiador por orçamento** (não uma por produto): teto = `calcular_maquiador(makes dos
  produtos + makes comuns dos avulsos, makes especiais dos avulsos)`; a make do Noel do produto é make
  comum (`make_1` 250). Dois Noéis = um Maquiador com teto 300.
- As vagas do produto resolvem o cachê com `has_show = False` sempre (a Visita não tem show): o
  coordenador do produto é 250 (500 na faixa) mesmo com um avulso de show no mesmo orçamento.
- O snapshot **congela as vagas** do produto (label, tipo, cachê fixo, maquiagem) junto do preço — o
  teto é emitido a partir das vagas congeladas e só o VALOR do cachê vem da tabela viva na data.
- Produto apagado depois da venda: a venda recusa com erro nomeando o produto; no evento as vagas
  congeladas nascem **sem teto e sem nota** (como qualquer vaga com teto `None` hoje); a explicação
  aparece no prefill de "Novo evento" (`caches[].cap_notes`) e no erro da venda.
- Preço congelado pela data do orçamento × teto pela data do evento (orçamento de 20/12 vinculado a
  evento de 24/12): risco **aceito**, como na 307 — registrado em `docs/05`.

## Cenários e Verificação *(obrigatório)*

### História 1 — A vendedora vende a Visita Mágica pelo preço da tabela (Prioridade: P1)

Na calculadora, a vendedora escolhe o produto "Visita Mágica — Papai Noel" (ou "— Papai Noel +
Ajudante") num card próprio. O orçamento sai **R$ 2.500** (ou **R$ 3.600**) em qualquer data normal e
**R$ 5.000** (ou **R$ 6.500**) em 24 e 25/12 — sem markup, sem acréscimo "Outro", sem engenharia
reversa. A memória de cálculo mostra a linha do produto; com só o produto no orçamento, a tela, a
mensagem e o PDF mostram **um valor só** ("Visita Mágica — Papai Noel (visita padrão, até 1h): R$
2.500,00" + PIX único) e os personagens do produto na equipe.

**Por que esta prioridade**: é o pedido — o preço ao cliente vem da tabela de venda, não dos cachês.

**Verificação**: cenários 2, 3, 4 e 12 do `verify_309.py` — totais exatos, memória fechando com o
total pela invariante nova, mensagem e PDF com bloco único, `quote.produtos` com o preço aplicado e a
faixa.

**Cenários de aceite**:

1. **Dado** um orçamento em 20/12 com o produto "Visita Mágica — Papai Noel" e coordenador 1,
   **Quando** calcula, **Então** `total_1h == total_2h == total_3h == total_4h == 2.500,00`; a memória
   tem a linha "Visita Mágica — Papai Noel · preço de tabela · 2.500" depois de "= Após markup" e a
   subtotal "= Após produtos"; `Σcache × markup + Σproduto + Σpos == TOTAL`; a mensagem e o PDF têm UM
   bloco de investimento (sem "2 horas"/"4 horas") e um PIX só.
2. **Dado** o mesmo orçamento em 24/12, **Quando** calcula, **Então** o total é 5.000,00,
   `quote.produtos[0].faixa_chave == "natal"` e o aviso dourado da 307 aparece com o produto.
3. **Dado** "Visita Mágica — Papai Noel + Ajudante" em 25/12, **Quando** calcula, **Então** 6.500,00.
4. **Dado** o produto em 20/12 às 20h, **Quando** calcula, **Então** o total continua 2.500,00 (noturno
   embutido) — e um boneco avulso no mesmo orçamento soma só o noturno dele (+50).

---

### História 2 — A vaga do evento nasce com o teto igual ao cachê combinado (Prioridade: P1)

Quando o orçamento com produto vira evento (criação, prefill de "Novo evento", vínculo 273), as vagas
do produto nascem com **teto = cachê da tabela vigente na data**: Papai Noel 600, Ajudante do Noel
270, Coordenador 250, Maquiador 250 — e em 24/25 Noel 1.000, Ajudante 650, Coordenador 500 (faixa da
307). O cachê continua nascendo vazio (decisões 236/238); o casting que digitar 900 grava 600; o
superadmin passa do teto como hoje. Dois exemplares do produto = dois Noéis, dois coordenadores e UM
Maquiador (teto 300).

**Por que esta prioridade**: é o dinheiro — "pagar o teto" passa a ser pagar o combinado.

**Verificação**: cenários 8, 9 e 10.

**Cenários de aceite**:

1. **Dado** um snapshot com o produto Noel + Ajudante em 20/12, **Quando** o teto é calculado,
   **Então** os itens saem na ordem produto → avulsos → extras, com Papai Noel 600 / Ajudante 270 /
   Coordenador 250 / Maquiador 250 em TODAS as colunas (flat; a régua >4h não os escala) e a nota do
   teto contém o literal `MARCA_PRODUTO` ("cachê da tabela · produto <rótulo>").
2. **Dado** o mesmo snapshot com data do evento 24/12, **Então** 1.000 / 650 / 500 / 250 e a nota cita
   "Véspera e Natal"; **Dado** um avulso com show no mesmo orçamento, **Então** o coordenador do
   produto continua 250 (o da fórmula segue a tabela de show).
3. **Dado** o evento criado pela API a partir desse orçamento (Google suprimido), **Então** as
   `EventRole` "Papai Noel", "Ajudante do Noel", "Coordenador" e "Maquiador" existem com `cache_cap`
   600 / 270 / 250 / 250 e `cache_value` vazio; o prefill de "Novo evento" e o vínculo 273 produzem os
   mesmos tetos; com dois produtos, dois Noéis, dois Coordenadores e UM Maquiador (300) nos três
   caminhos.
4. **Dado** a vaga "Papai Noel" com teto 600, **Quando** um usuário de casting salva 900, **Então**
   grava 600; **Quando** o superadmin salva 900, **Então** grava 900.

---

### História 3 — A tabela de preços volta a dizer o cachê (Prioridade: P1)

"Papai Noel" volta a **600 / 650 / 675 / 700** e "Ajudante do Noel" passa a **270 / 320 / 345 / 370**.
A troca automática 600→712 da 307 deixa de existir; uma troca inversa guardada só age se o valor
estiver exatamente em 712/800/850/900 (e 423/480/510/540). Os dois especiais continuam na tabela:
Noel avulso dentro de uma festa grande segue a fórmula normal (600 × markup), e a calculadora avisa
"Para a Visita Mágica use o produto" quando "Papai Noel" entra avulso sem produto.

**Por que esta prioridade**: sem isso o teto do avulso continua 712 e a edição pela tela não gruda.

**Verificação**: cenários 11 e 12.

**Cenários de aceite**:

1. **Dado** a configuração salva com Noel [712, 800, 850, 900] e Ajudante [423, 480, 510, 540],
   **Quando** a tabela é carregada, **Então** devolve [600, 650, 675, 700] e [270, 320, 345, 370];
   **Dado** Noel editado para 650, **Então** fica 650; **Dado** Noel em [600, …], **Então** NÃO vira 712.
2. **Dado** "Papai Noel" avulso em 20/12 com coordenador 1, **Quando** calcula, **Então** 2.210,00 e
   `quote.avisos` contém o aviso do produto; em 24/12 o avulso segue a faixa da 307 (5.010,00).

---

### História 4 — O superadmin configura os produtos sem deploy (Prioridade: P2)

Em Configuração de Preços, um card "Produtos de tabela" lista cada produto (rótulo, descrição ao
cliente, ativo, preço normal, preço por faixa de data especial, vagas com "pela tabela" ou valor fixo,
maquiagem do personagem); o superadmin cria, edita, desliga ou remove produtos (remoção com
`ConfirmDialog`). O servidor valida e devolve 400 apontando o campo. Produto desligado some da
calculadora mas orçamentos antigos que o citam continuam recalculando; produto removido depois da
venda não quebra o evento: as vagas congeladas nascem sem teto.

**Por que esta prioridade**: o cadastro é do dono — a Visita é o primeiro produto, não o último.

**Verificação**: cenários 13, 14 e 17 (DEVE FALHAR).

**Cenários de aceite**:

1. **Dado** o superadmin salvando `produtos` válido, **Então** 200, persistido (conexão separada) e
   devolvido em `GET /orcamento/opcoes`; **Dado** cada um dos sete corpos inválidos — preço ≤ 0, chave
   fora de `^[a-z0-9_]{1,30}$`, vaga sem label, tipo de vaga desconhecido, cachê fixo zero numa vaga,
   descrição > 120, `produtos_estimativa.markup` fora de [1, 6] —, **Então** 400 com
   `fields["produtos.<chave>.<campo>"]` (ou `produtos_estimativa.markup`) e nada gravado; **Dado**
   `por_faixa` com uma faixa que não existe, **Então** 200 com a entrada órfã descartada e um aviso.
2. **Dado** produto `ativo: false` citado num snapshot antigo, **Então** recalcula com o preço dele;
   **Dado** produto apagado citado num snapshot antigo, **Então** a venda responde erro de validação
   nomeando o produto e o teto das vagas congeladas sai `None` (prefill com `cap_notes` "produto não
   está mais na tabela — teto não aplicado"; `EventRole` sem teto e sem nota).
3. **Dado** um produto sem preço de 24/25 vendido em 24/12, **Então** o preço sai estimado
   (Σ cachês normais × 2,0 × 3,0, HALF_UP), marcado como estimativa na memória, no resultado, na
   mensagem e no PDF, e o teto das vagas segue a faixa.
4. **Dado** um COMERCIAL, **Quando** `POST /api/orcamento/settings`, **Então** 403.

---

### História 5 — Produto e itens avulsos convivem no mesmo orçamento (Prioridade: P2)

Festa de 4h com um boneco **e** uma Visita Mágica: as colunas 1h–4h mostram o boneco pela fórmula
em cada coluna **+ 2.500 fixos**; o coordenador incluído no produto não é cobrado em dobro; fora de SP
soma por cima; NF, acréscimos (BV) e PIX incidem sobre o total com o produto; a régua >4h escala só a
parte que não é produto; personalizado "valor final" vence tudo e "multiplicador" não multiplica o
produto.

**Por que esta prioridade**: é o caso real de dezembro (bonecos + Noel) e é onde a conta quebra.

**Verificação**: cenários 5, 6 e 7.

**Cenários de aceite**:

1. **Dado** produto Noel + boneco avulso em 20/12 com coordenador 1, **Então**
   `total_Nh = boneco_Nh × markup_Nh + 2.500` (nenhum coordenador fora do produto é cobrado;
   `quote.coordenadores_inclusos == 1`); com dois produtos, dois coordenadores e dois Noéis no teto, UM
   Maquiador (300); com um avulso de make especial, a venda cobra só o incremento
   `(calcular_maquiador(1, 1) − calcular_maquiador(1, 0)) × 1,5`.
2. **Dado** fora de SP (manto, van, 50 km), **Então** o transporte de hoje soma por cima de 2.500 com a
   van dimensionada pelas pessoas do produto; **Dado** NF, **Então** (2.500 + avulsos) ÷ 0,84; **Dado**
   BV 10 %, **Então** `valores_brl` = 10 % do total com produto; a mensagem mostra PIX = total × 0,95.
3. **Dado** duração 6h com produto + boneco, **Então** `total_custom = total_na_duracao(...)` = parte
   líquida do boneco de 4h ÷ 4 × 6 + 2.500, com % e NF aplicados depois — igual no prefill e em
   `_total_da_duracao`; **Dado** personalizado valor final 3.000, **Então** 3.000 e a memória (sem as
   linhas do produto) fecha com o total; **Dado** multiplicador 2, **Então** `cache_base × 2 + 2.500`,
   e multiplicador zerado continua recusado ("Informe valores válidos").

---

### História 6 — Os tetos 712/423 já gravados são corrigidos (Prioridade: P2)

Vagas de eventos a partir de 16/10 nasceram com teto exatamente 712 ou 423. Um script de uma vez
relata essas vagas (evento, data, vaga, teto, cachê, artista, ação) e, com `--execute`, rebaixa para
600/270 só as vagas **sem cachê digitado e sem artista**, registrando "(teto corrigido pela 309: 712 →
600)" (ou "423 → 270") na nota; vagas com nome diferente de Papai Noel/Ajudante do Noel entram no
relatório como "conferir à mão". O dono roda no Shell do Render; o relatório zero prova que acabou.

**Por que esta prioridade**: sem isso o casting continua podendo pagar 712 nos eventos de dezembro
já na agenda.

**Verificação**: cenário 18.

**Cenários de aceite**:

1. **Dado** uma vaga descartável com teto 712, sem cachê e sem artista, **Quando** o script roda sem
   `--execute`, **Então** só lista; **Quando** roda com `--execute`, **Então** o teto vira 600 e a nota
   registra a correção; **Dado** uma vaga com cachê já digitado ou artista escalado, **Então** não é
   tocada e aparece como "não corrigida — conferir à mão".

---

### História 7 — O resto não muda (Prioridade: P3)

EducaManto ignora `produtos`; orçamentos salvos antes da feature continuam congelados e, sem a chave,
a conta (quote, mensagem e PDF) é byte a byte a de antes (fora Noel/Ajudante avulsos, História 3); na
janela de deploy (bundle novo com backend velho) "Gerar Orçamento" fica travado quando há produto
selecionado e a resposta veio sem `quote.produtos`.

**Verificação**: cenários 1, 15, 16 e 19 (regressão 307 reescrito, que encadeia a 305).

**Cenários de aceite**:

1. **Dado** um payload sem `produtos` e sem Noel/Ajudante, **Então** `quote` (inclusive `message`),
   mensagem e PDF idênticos ao gabarito gravado no HEAD `6356b80` (golden JSON gerado pela primeira
   rodada do verify, antes do núcleo); **Dado** a contratação Manto do EducaManto com `produtos` no
   payload, **Então** totais iguais aos sem a chave.
2. **Dado** um produto selecionado e `result.quote.produtos` ausente, **Então** o botão fica
   desabilitado com o aviso "o servidor não aplicou o produto" (conferência de tela).

### Casos de borda

- Produto sem preço para a faixa da data (ex.: produto novo sem `por_faixa.natal` em 24/12): o preço
  do produto é **estimado** = Σ cachês 1h das vagas pela tabela normal × `fator_cache` (2,0) × `markup`
  da estimativa (3,0), quantizado HALF_UP — Visita Noel: (600 + 250 + 250) × 2 × 3,0 = 6.600 —, com
  `estimado: true` no `quote.produtos[]`, linha da memória "preço estimado (sem preço de <faixa>)" e
  aviso (`role="alert"`, borda dourada, "Confira antes de enviar") na calculadora e no resultado;
  mensagem e PDF levam "(estimativa)" junto do produto; vagas sem cachê resolvível (label desconhecido)
  ficam fora da soma e geram aviso. O teto das vagas segue a tabela vigente na data (faixa).
- Dois exemplares do mesmo produto: dois Noéis, dois coordenadores, **um** Maquiador (teto pela
  tabela para o total de makes); `num_going` conta todas as pessoas para a van.
- Avulso maquiado junto do produto: a vaga Maquiador única tem teto `calcular_maquiador(makes dos
  produtos + comuns dos avulsos, especiais dos avulsos)`; na venda cobra-se só o incremento sobre as
  makes do produto.
- "Papai Noel" avulso **e** produto no mesmo orçamento: permitido (dois Noéis), ambos com teto 600; o
  aviso "use o produto" só aparece quando não há produto.
- Personagem do título do Google diferente do label ("Duende", "Elfo"): o vínculo 273 casa por nome —
  não casa com "Ajudante do Noel" e a vaga fica sem teto, como hoje para qualquer nome diferente
  (registrado; alias de nomes fora de escopo).
- `coordenador_qty` menor que o número de coordenadores dos produtos: o total é elevado ao dos
  produtos; o campo mostra "N incluído(s) no produto" (número vindo do servidor em
  `quote.coordenadores_inclusos`). O coordenador do produto conta para o mínimo de coordenadores que
  um especial avulso exige (ex.: BGE exige 2 → produto + 1 da fórmula).
- Produto com `preco` igual nas duas faixas ou `por_faixa` vazio: válido; sem variante na data de
  faixa = estimativa marcada (acima). Superadmin que remove uma faixa de `datas_especiais` enquanto um
  produto tem `por_faixa.<faixa>`: a entrada órfã é descartada no salvar, com aviso no card — não 400.
- `_migrar_309` recebe bloco malformado (`produtos: null`, produto sem `vagas`, preço string): produto
  inválido é descartado na carga (nunca preço 0), os DEFAULTS entram só quando a chave está ausente —
  e nada disso derruba o `load()` (exceção ali devolveria os DEFAULTS para a tabela inteira).
- Orçamento salvo com produto cujo preço o dono mudou depois: congelado (regra 020) — o teto do evento,
  porém, é recalculado da tabela viva na criação/vínculo, como hoje; vendido pelo preço normal e
  vinculado a evento em 24/25 → teto da faixa sobre preço normal (risco aceito, `docs/05`).
- `inclui_noturno: false` num produto: cada vaga `especial`/`ator`/`coordenador` dele soma +50 na venda
  e no teto a partir das 19h (o Maquiador não), espelhando os avulsos.

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: A tabela de preços DEVE ter o bloco `produtos` (dicionário chave → produto) com: `rotulo`
  (1–60), `descricao` ao cliente (0–120), `ativo`, `preco` (um valor em R$ > 0, fixo por visita),
  `por_faixa` (chave de faixa de `datas_especiais` → `{preco}`), `vagas` (1–10 itens: `label` 1–120,
  `tipo` ∈ {especial, ator, coordenador, maquiador} — tipo `coordenador` força o label "Coordenador" e
  `maquiador` força "Maquiador" —, `cache` = `null` "pela tabela vigente na data" ou um valor em R$ > 0,
  `needs_makeup` bool opcional só para especial/ator, padrão `false`) e `inclui_noturno` (padrão
  `true`); e o bloco irmão `produtos_estimativa` (`fator_cache` > 0, padrão 2,0; `markup` em [1, 6],
  padrão 3,0). Chave ausente = sem produtos = conta de hoje.
- **FR-002**: Os produtos padrão DEVEM ser "Visita Mágica — Papai Noel" (2.500; natal 5.000; vagas
  Papai Noel com maquiagem · Coordenador · Maquiador, todas pela tabela) e "Visita Mágica — Papai Noel +
  Ajudante" (3.600; natal 6.500; + Ajudante do Noel pela tabela), descrição "visita padrão, até 1h",
  ativos.
- **FR-003**: A vendedora DEVE selecionar produtos na calculadora num card próprio ("Produtos de
  tabela") com `Combobox` (nunca `<select>` nativo; opções com descrição = preço normal e ícone de
  fallback 🎅), podendo repetir e remover; a chave `produtos: [{chave}]` vai no payload ao lado de
  `performers`.
- **FR-004**: O preço do produto DEVE entrar na conta DEPOIS do markup e ANTES de brinde, noturno,
  técnico, maquiador, transporte, acréscimos e NF; DEVE ser o mesmo nas quatro durações. Régua >4h: a
  parte líquida do produto não escala — `produtos.total_na_duracao(subtotal_4h_pré_acréscimos,
  produtos_total, horas, acréscimos, nota_fiscal)` calcula `((subtotal − produtos_total) ÷ 4 × h +
  produtos_total)` e reaplica % / fixos e NF; a MESMA função é usada pela venda (`total_custom`), pelo
  prefill de "Novo evento", por `_total_da_duracao` e pelo BV da duração custom (305), que derivam o
  subtotal pré-acréscimos do `total_4h` pela conta inversa já existente.
- **FR-005**: O produto com `inclui_noturno: true` NÃO soma o adicional noturno nem na venda nem no
  teto das vagas dele; com `false`, cada vaga `especial`/`ator`/`coordenador` dele soma +50 na venda e
  no teto (Maquiador não). Avulsos continuam somando.
- **FR-006**: O coordenador incluído no produto NÃO pode ser cobrado em dobro: uma função única
  `produtos.split_coordenadores(coordenador_qty, min_coordenadores_dos_avulsos, produtos) → (total,
  da_formula, inclusos)` com `total = max(qty, min_coordenadores, inclusos)` e `da_formula = total −
  inclusos` é usada pela venda e pelo teto; o `quote` traz `coordenadores_inclusos` e a tela mostra "N
  incluído(s) no produto"; o total nunca fica abaixo do dos produtos.
- **FR-007**: Há UMA vaga Maquiador por orçamento: teto = `calcular_maquiador(makes dos produtos +
  makes comuns dos avulsos, makes especiais dos avulsos)`; o preço do produto NÃO cobra make à parte e
  a venda cobra só o incremento dos avulsos: `(calcular_maquiador(mp + ra, ea) − calcular_maquiador(mp,
  0)) × 1,5`, zero quando só há produto; a make do personagem do produto (`needs_makeup`) é comum.
- **FR-008**: A memória de cálculo DEVE ter uma linha do tipo `produto` por exemplar, depois de
  "= Após markup", seguida da subtotal "= Após produtos", e obedecer à invariante `Σcache × markup +
  Σproduto + Σpos = TOTAL`; no personalizado "valor final" as linhas `produto` e a subtotal saem (o
  digitado vence); no "multiplicador" o produto NÃO é multiplicado (`cache_base × mult +
  produtos_total`, invariante `Σcache × mult + Σproduto = TOTAL`) e a validação "Informe valores
  válidos" continua olhando `cache_base × mult` antes de somar o produto.
- **FR-009**: A mensagem WhatsApp e o PDF DEVEM trazer a linha do produto com descrição e preço
  aplicado e listar os personagens do produto na equipe; com só produto no orçamento (sem avulsos e sem
  coordenador da fórmula) tela, mensagem e PDF mostram UM valor (bloco único, PIX único; `show_1h`
  verdadeiro e os demais falsos; `total_custom` nulo). O resumo do orçamento que a aba Comercial do
  evento mostra (`resumo_do_orcamento`) inclui os personagens e as makes do produto.
- **FR-010**: O `quote` DEVE ganhar, SEMPRE (listas vazias/zero quando não há produto): `produtos:
  [{chave, rotulo, descricao, preco_aplicado, faixa_chave|null, estimado, vagas: [label…]}]`,
  `produtos_total`, `coordenadores_inclusos` e `avisos: [str]`; o `snapshot` ganha `produtos:
  [{chave, rotulo, preco_aplicado, faixa_chave, estimado, vagas: [{label, tipo, cache, needs_makeup}]}]`
  e `produtos_total` (preço e composição congelados). Snapshot sem a chave = conta de hoje; orçamento
  salvo é congelado.
- **FR-011**: O teto das vagas (prefill, criação e vínculo 273) DEVE emitir primeiro as vagas dos
  produtos — a partir das vagas CONGELADAS no snapshot, flat em todas as colunas, com o VALOR do cachê
  pela tabela vigente na data do EVENTO (faixa da 307 inclusa, `has_show = False`) ou o valor fixo da
  vaga — depois os avulsos, depois os extras (coordenadores dos produtos, coordenadores da fórmula,
  Técnico, o Maquiador único), na MESMA ordem no prefill e na criação; a nota do teto leva o literal
  `MARCA_PRODUTO`; o cachê da vaga continua nascendo vazio e o casting continua rebaixado ao teto;
  produto que não existe mais na tabela → vagas congeladas com teto `None` (nota só no prefill), nunca
  0; label de especial que não existe na tabela → teto `None`.
- **FR-012**: "Papai Noel" DEVE voltar a [600, 650, 675, 700] e "Ajudante do Noel" a
  [270, 320, 345, 370] nos padrões; a troca automática 600→712 DEVE ser removida da carga (e os
  comentários que a justificavam reescritos); uma troca inversa guardada DEVE agir só sobre
  [712, 800, 850, 900] e [423, 480, 510, 540] exatos; os dois especiais NÃO são excluídos; a calculadora
  DEVE avisar "Para a Visita Mágica use o produto" quando "Papai Noel" entra avulso sem produto.
- **FR-013**: `POST /api/orcamento/settings` DEVE aceitar `produtos` e `produtos_estimativa` validados
  no núcleo (exceção própria com `fields` `produtos.<chave>.<campo>` / `produtos.<chave>.vagas.<i>.<campo>`
  / `produtos_estimativa.<campo>`), DEPOIS do bloco `datas_especiais` do mesmo corpo (para `por_faixa`
  ser conferido contra as faixas já atualizadas): chave `^[a-z0-9_]{1,30}$`, rótulo 1–60, descrição
  ≤ 120, preço > 0 finito, `por_faixa` com preço > 0 (faixa inexistente é descartada com aviso, não
  400), 1–10 vagas com label 1–120 e tipo conhecido (labels de coordenador/maquiador forçados), `cache`
  `null` ou > 0, `needs_makeup`/`ativo`/`inclui_noturno` booleanos, `fator_cache` > 0, `markup` em
  [1, 6]; o bloco enviado substitui o salvo; chave AUSENTE no corpo mantém o salvo; corpo inválido não
  grava nada; papéis sem permissão levam 403.
- **FR-014**: A Configuração de Preços DEVE ter o card "Produtos de tabela" no molde do card de datas
  especiais (erro por campo com `aria-invalid` e foco; chips para vagas com tipo, label, cachê e
  maquiagem; remoção de produto/vaga com `ConfirmDialog` de `@manto/ui`; `PriceTable` não se aplica —
  preço é um valor só) e o card "Estimativa" para `produtos_estimativa`.
- **FR-015**: `GET /api/orcamento/opcoes` e `GET /api/orcamento/settings` DEVEM devolver
  `settings.produtos` e `settings.produtos_estimativa` (a calculadora lê de lá); fica registrado que os
  cachês "pela tabela" já chegam ao navegador da vendedora hoje — recorte só-superadmin é fatia própria.
- **FR-016**: A contratação Manto do EducaManto DEVE continuar neutra: `produtos` é removido da cópia do
  payload antes de calcular (o `inputs` do snapshot do EducaManto pode guardar a chave; ela é ignorada
  em todo recálculo); o card não existe lá.
- **FR-017**: "Gerar Orçamento" DEVE ficar desabilitado quando há produto selecionado e a resposta do
  cálculo veio sem a chave `quote.produtos` (backend antigo na janela de deploy), com aviso.
- **FR-018**: Um script de uma vez (`specs/309-produtos-de-tabela/rebaixar_tetos_noel_309.py`) DEVE
  relatar as vagas de eventos com `start_at ≥ 2026-10-16` cujo `cache_cap` é exatamente 712,00 ou 423,00
  (qualquer nome) e, com `--execute`, rebaixar para 600/270 as de nome "Papai Noel"/"Ajudante do Noel"
  com `cache_value` vazio e sem artista, registrando "(teto corrigido pela 309: {antes} → {depois})" na
  nota; as demais só aparecem no relatório ("conferir à mão").
- **FR-019**: A faixa de data especial da 307 (markup 3,34, cachês, piso 650, nota) DEVE continuar
  valendo para avulsos em 24/25. Produto sem preço para a faixa da data DEVE sair **estimado**:
  Σ cachês 1h das vagas pela tabela normal (`has_show = False`; vagas sem cachê resolvível ficam fora e
  avisam) × `produtos_estimativa.fator_cache` × `produtos_estimativa.markup`, quantizado HALF_UP, com
  `estimado: true`, linha própria na memória, "(estimativa)" na mensagem e no PDF e aviso com os fatores
  vigentes — nunca o preço normal em silêncio, nunca bloqueio; o teto das vagas segue a tabela vigente
  na data.
- **FR-020**: Fora de SP (262) soma por cima do produto contando as pessoas dele em `num_going`; NF ÷
  0,84, acréscimos % (BV da 305 com `valores_brl`) e PIX −5 % incidem sobre o total com o produto.
- **FR-021**: `verify_307.py` DEVE ser atualizado onde afirma 712 / 2.501,20 / 3.601 / teto 712 —
  cenários 1 (:253), 2 (:263), 10 (:428), 11 (:507-508), 12 (:574-578, :652), 15 (:792), docstring e
  `NOEL_ANTIGO` — passando a afirmar 600 / 2.210 / 2.912 / teto 600 e que a carga NÃO troca para 712
  (a inversa 712→600 e 423→270 agem); continuar verde com `--regressao` (que encadeia a 305).

### Entidades *(se houver dados)*

- **Produto de tabela** (JSON `pricing_config.produtos.<chave>`): rótulo, descrição, ativo, preço fixo,
  preço por faixa, vagas (label, tipo, cachê ou "pela tabela", maquiagem), inclui_noturno. Sem tabela
  nova. `produtos_estimativa` (fator_cache, markup) ao lado.
- **Seleção de produto congelada** (`snapshot.produtos[]` com preço, faixa, estimativa e vagas;
  `snapshot.produtos_total`) e **produto aplicado** (`quote.produtos[]`, `quote.produtos_total`,
  `quote.coordenadores_inclusos`, `quote.avisos`): o que a vendedora vendeu.
- **Vaga do produto** (`EventRole` existente): nasce com `cache_cap` = cachê resolvido e `cache_value`
  vazio — nenhuma coluna nova.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

- Nenhum endpoint novo; cinco alterados, gates inalterados (constituição XIII): `POST
  /api/orcamento/calcular` e `POST /api/orcamento/salvar` (`_require_vendas` — COMERCIAL, SUPERADMIN)
  aceitam `produtos`; `GET /api/orcamento/opcoes` (`_require_vendas`) e `GET /api/orcamento/settings`
  (`_require_superadmin`) devolvem o bloco; `POST /api/orcamento/settings` (`_require_superadmin`)
  aceita `produtos` + `produtos_estimativa`. As cinco linhas de `docs/01` §4.3 são atualizadas. O
  script de uma vez roda no servidor, sem rota.

## Verificação (`verify_309.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/309-produtos-de-tabela/verify_309.py`, contra `manto_local` (`DATABASE_URL` de
`.local-db-url`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`). Configuração de preços real salva e
restaurada por conexão separada (config de teste determinística: markup 2,6/2,5/2,45/2,4, coordenador
250/300/325/350 e 300/… com show, `make_1` 250, `make_especial` 300, Noel [712, …] e Ajudante [423, …]
GRAVADOS para provar a inversa, SEM `produtos` para provar os padrões, faixa `natal` da 307). Login só
por `POST /api/auth/login` com usuários descartáveis (superadmin, comercial, casting); dublês do Google
como no `verify_305.py`; evento descartável só pela API, roles criadas e apagadas na mesma rodada;
limpeza no `finally`. **Gabarito**: na primeira rodada (HEAD `6356b80`, antes do núcleo) o cenário 1
grava `verify_309_golden.json` (quote + mensagem + texto do PDF de payloads sem produto e sem
Noel/Ajudante: boneco + coordenador em 20/12 e 24/12, fora de SP, NF, BV); nas rodadas seguintes
compara chave a chave ignorando só `produtos`, `produtos_total`, `coordenadores_inclusos` e `avisos`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | payload sem `produtos` | quote, mensagem e PDF iguais ao gabarito do HEAD `6356b80` (paridade) | não |
| 2 | produto Noel 20/12 | 2.500 nas 4 colunas; memória com linha `produto` + "= Após produtos" e `Σcache × markup + Σproduto + Σpos == TOTAL`; mensagem e PDF com bloco único (sem "4 horas") e PIX único; `data_especial` None | não |
| 3 | Noel 24/12 · Noel+Ajudante 20/12 e 25/12 | 5.000 · 3.600 · 6.500; `quote.produtos[].faixa_chave`; `show_2h..4h` falsos | não |
| 4 | produto às 20h; produto + boneco às 20h | 2.500 (noturno embutido); boneco soma só o noturno dele | não |
| 5 | produto + boneco 4h; dois produtos; avulso com show; avulso make especial | `total_Nh = boneco × markup + 2.500`; `coordenadores_inclusos`; 2 produtos = 2 coordenadores e UM Maquiador 300 no teto; coordenador do produto 250 com show avulso; incremento de make | não |
| 6 | fora de SP, NF, BV 10 %, PIX | transporte por cima (van pelas pessoas do produto); ÷0,84 sobre total com produto; `valores_brl`; mensagem × 0,95 | não |
| 7 | régua 6h (com e sem NF/BV); personalizado valor final e multiplicador | `total_na_duracao` igual na venda, no prefill e em `_total_da_duracao`; digitado vence (memória fecha); `cache_base × 2 + produto`; multiplicador zerado recusado | não |
| 8 | `_compute_performer_caches` com produto | ordem produto → avulsos → extras; 600/270/250/250 flat; 24/12 1.000/650/500; `horas_extra` não escala o produto; `MARCA_PRODUTO` nas notas; label desconhecido → `None` | não |
| 9 | criação por API (Google suprimido), prefill e vínculo 273 | `EventRole` com `cache_cap` 600/270/250/250 e `cache_value` vazio nos três caminhos; dois produtos = 2 Noéis, 2 Coordenadores, 1 Maquiador 300; data do evento manda | não |
| 10 | `assign_role` casting × superadmin | casting 900 → 600; superadmin 900 → 900 | não |
| 11 | migração | 712→600 e 423→270 guardadas; Noel 650 intocado; Noel 600 não vira 712; `produtos` ausente → padrões; bloco malformado descartado sem derrubar `load()` | não |
| 12 | avulsos | Noel avulso 20/12 = 2.210 com `avisos`; 24/12 avulso = 5.010 (faixa da 307) | não |
| 13 | `POST /settings` | válido persiste (conexão separada) e volta no `/opcoes`; 7 corpos inválidos → 400 por campo, nada gravado; faixa órfã em `por_faixa` descartada com aviso | não |
| 14 | produto inativo e produto apagado | inativo recalcula snapshot antigo; apagado → erro de validação na venda; teto das vagas congeladas `None` com nota no prefill | não |
| 15 | produto sem `por_faixa` em 24/12 | preço estimado = Σ cachês normais × 2,0 × 3,0 (Noel: 6.600, HALF_UP); `estimado: true`; linha da memória e aviso com os fatores; teto das vagas pela faixa (1.000/500/250) | não |
| 16 | EducaManto | `_totais_contratacao` com e sem `produtos` → iguais (com a faixa provadamente ativa na venda) | não |
| 17 | COMERCIAL `POST /settings` | 403 | **sim** |
| 18 | script `rebaixar_tetos_noel_309.py` | relatório sem `--execute` (inclui vaga 712 de nome diferente como "conferir à mão"); `--execute` rebaixa só vaga Papai Noel/Ajudante 712/423 sem cachê e sem artista, nota por vaga; as outras ficam | não |
| 19 | regressão (`--regressao`) | `verify_307.py --regressao` reescrito e verde (encadeia a 305) | não |
| 20 | limpeza | usuários, orçamentos, evento e roles descartáveis apagados (`roles.clear()`); configuração real restaurada e conferida | — |

Conferência de tela (Browser pane): `/orcamento` (card Produtos com Combobox; valor único quando só
produto; aviso de faixa; aviso "use o produto"; botão travado simulando `quote.produtos` ausente);
`/orcamento/:id` (linha do produto); `/orcamento/configuracoes` (card Produtos de tabela com 400
apontando o campo e foco; `ConfirmDialog` ao remover); `/events/new?orcamento_id=` com o produto Noel +
Ajudante (tetos 600/270/250/250 nas vagas).

## Critérios de sucesso *(obrigatório)*

- **SC-001**: A Visita Mágica sai exatamente R$ 2.500 / R$ 3.600 em data normal e R$ 5.000 / R$ 6.500
  em 24 e 25/12 (não 2.501 / 3.601 / 5.010 / 7.181), sem acréscimo manual.
- **SC-002**: 100 % dos eventos criados de orçamento com produto nascem com teto do Noel 600 (1.000 em
  24/25) e do Ajudante 270 (650); nenhuma vaga de produto nasce com teto 712/423 nem 0.
- **SC-003**: Orçamentos sem produto saem com os mesmos números de antes (quote, mensagem e PDF iguais
  ao gabarito), exceto Noel/Ajudante avulsos, que passam a 600/270 (decisão do dono).
- **SC-004**: O superadmin cria ou altera um produto pela tela e o preço vale no próximo cálculo, sem
  deploy; erro de cadastro aponta o campo.
- **SC-005**: EducaManto, BV do evento (305) e conta inversa continuam iguais (verify 307 reescrito,
  que encadeia a 305, verde).
- **SC-006**: Depois do script, zero vagas de Noel/Ajudante com teto 712/423 sem cachê digitado.

## Fora de escopo

- Markup por item; piso de cachê no casting ("não pode pagar menos de 600" contraria a 236).
- Pacote de 30 minutos com coluna própria de duração; produto que escala por duração.
- Outros produtos além da Visita Mágica (o modelo é genérico; o cadastro é do dono).
- Alias de nomes no vínculo 273 ("Duende" ↔ "Ajudante do Noel").
- Recorte só-superadmin dos cachês no `/opcoes`.
- Aviso na criação/vínculo quando o evento cai em 24/25 e o orçamento foi vendido pelo preço normal
  (risco aceito; `docs/05`).
- `num_colaboradores` vazio no snapshot virando 1 pessoa no prefill (pré-existente; `docs/05`).
- Troca do `<select>` nativo de especiais do `PerformersEditor` pelo `Combobox` (#103) — fatia
  Nível 2 própria.

## Docs a atualizar

`docs/01` (§2.10 `pricing_config.produtos`/`produtos_estimativa`; §3.13 `quote.produtos`/
`produtos_total`/`coordenadores_inclusos`/`avisos`, `snapshot.produtos`, `POST /settings` com
`produtos`, memória tipo `produto` e a invariante, especiais 600/270; §4.3 cinco linhas atualizadas),
`docs/02` (`/orcamento`, `/orcamento/:id`, `/orcamento/configuracoes`, `/events/new`), `docs/03`
(entrada no topo + índice; a 307 fica como história — "712/423 duraram de 16/10 a …"), `docs/04` (linha
Orçamento: produto pós-markup; régua por `total_na_duracao`; teto pela tabela a partir das vagas
congeladas; invariantes), `docs/05` (quitar #107 pelo script; #103 continua; registrar cachês visíveis
no `/opcoes`, o risco aceito do preço congelado × teto da faixa, `num_colaboradores` vazio e a regra do
`verify_307` mudada).

## Premissas

- Markup de produção 2,6 (1h) e coordenador 250 / make 250 (tabela de 2026) — conferidos no espelho e
  em produção em 16/10.
- 2h–4h dos especiais avulsos: Noel 650/675/700 (tabela antiga) e Ajudante 320/345/370 (degrau do
  ator) — confirmados pelo dono em 19/10; só importam para o avulso e para a régua.
- Fatores da estimativa (produto sem preço na faixa): `fator_cache` 2,0 e `markup` 3,0 ("um pouco
  mais alto que o padrão 2,6") — editáveis pelo superadmin; a estimativa é sempre marcada como tal.
- Label fixo "Ajudante do Noel" mesmo quando o personagem é duende/elfo/Rubi/Esmeralda.
- Descrição ao cliente "visita padrão, até 1h" (sem parênteses: a mensagem e a tela já a põem entre
  parênteses); sem a frase de presentes (veto da 307).
- Um Maquiador por orçamento; o preço do produto não cobra maquiagem à parte.
- A tabela de venda é "sem nota" e "antes do PIX" (NF ÷ 0,84 e −5 % incidem como nos demais).
- A faixa `natal` da 307 continua em produção (markup 3,34, cachês 1.000/650/500, piso 650) e é a fonte
  do cachê das vagas do produto em 24/25.
- Esforço 6–7 noites (estimativa dos céticos); deploy à noite, fora do horário da equipe.
