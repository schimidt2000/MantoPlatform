# Feature 309 — Produtos de tabela: a Visita Mágica do Papai Noel vendida pelo preço da tabela de venda, com os cachês das vagas definidos pela tabela de preços

**Branch**: `309-produtos-de-tabela` (da `main` `6356b80`, em worktree `C:\tmp\mp309` — a árvore
principal está ocupada pela 308 de outro chat) · **Created**: 2026-10-19 · **Status**: Rascunho ·
**Migration**: nenhuma (bloco novo no JSON `pricing_config` + chave nova no snapshot do orçamento;
chave ausente = comportamento de hoje) · **Nível**: 1 (feature — orçamento + teto das vagas no
calendário; EducaManto neutro) — constituição, Princípio VI

**Input**: pedido do dono (19/10/2026): "Nesses casos em que existe uma tabela de preços que vai ser
vendida à pessoa final, a gente talvez tenha que usar uma lógica diferente da da calculadora. Talvez
tenha que ter esse pacote fechado para a vendedora selecionar na calculadora: ela seleciona, e aí os
cachês estão definidos, apesar do valor final — porque hoje a nossa lógica é: os cachês definem o
valor final." Plano de análise (três desenhos concorrentes, três céticos):
`docs/backlog/309-produtos-de-tabela-visita-magica.md` (fora do repositório).

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

## Cenários e Verificação *(obrigatório)*

### História 1 — A vendedora vende a Visita Mágica pelo preço da tabela (Prioridade: P1)

Na calculadora, a vendedora escolhe o produto "Visita Mágica — Papai Noel" (ou "— Papai Noel +
Ajudante") num card próprio. O orçamento sai **R$ 2.500** (ou **R$ 3.600**) em qualquer data normal e
**R$ 5.000** (ou **R$ 6.500**) em 24 e 25/12 — sem markup, sem acréscimo "Outro", sem engenharia
reversa. A memória de cálculo mostra a linha do produto, a mensagem e o PDF trazem "Visita Mágica —
Papai Noel (visita padrão, até 1h): R$ 2.500" e os personagens na equipe. Com só o produto no
orçamento, as quatro durações são iguais e a tela mostra um valor só.

**Por que esta prioridade**: é o pedido — o preço ao cliente vem da tabela de venda, não dos cachês.

**Verificação**: cenários 2, 3, 4 e 12 do `verify_309.py` — totais exatos, memória fechando com o
total, mensagem e PDF com a linha, `quote.produtos` com o preço aplicado e a faixa.

**Cenários de aceite**:

1. **Dado** um orçamento em 20/12 com o produto "Visita Mágica — Papai Noel" e coordenador 1,
   **Quando** calcula, **Então** `total_1h == total_2h == total_3h == total_4h == 2.500,00`, a memória
   tem uma linha "Visita Mágica — Papai Noel · preço de tabela · 2.500" depois de "= Após markup" e a
   soma das linhas fecha com o TOTAL (hotfix 210).
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
superadmin passa do teto como hoje. Dois exemplares do produto = dois Noéis e dois coordenadores.

**Por que esta prioridade**: é o dinheiro — "pagar o teto" passa a ser pagar o combinado.

**Verificação**: cenários 8, 9 e 10.

**Cenários de aceite**:

1. **Dado** um snapshot com o produto Noel + Ajudante em 20/12, **Quando** o teto é calculado,
   **Então** os itens saem na ordem produto → avulsos → extras, com Papai Noel 600 / Ajudante 270 /
   Coordenador 250 / Maquiador 250 em TODAS as colunas (flat; a régua >4h não os escala) e a nota do
   teto explica "cachê da tabela · produto Visita Mágica".
2. **Dado** o mesmo snapshot com data do evento 24/12, **Então** 1.000 / 650 / 500 / 250 e a nota cita
   "Véspera e Natal".
3. **Dado** o evento criado pela API a partir desse orçamento (Google suprimido), **Então** as
   `EventRole` "Papai Noel", "Ajudante do Noel", "Coordenador" e "Maquiador" existem com `cache_cap`
   600 / 270 / 250 / 250 e `cache_value` vazio; o prefill de "Novo evento" e o vínculo 273 produzem os
   mesmos tetos.
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
cliente, ativo, preço normal, preço por faixa de data especial, vagas com "pela tabela" ou valor fixo);
o superadmin cria, edita, desliga ou remove produtos. O servidor valida e devolve 400 apontando o
campo. Produto desligado some da calculadora mas orçamentos antigos que o citam continuam
recalculando; produto removido depois da venda não quebra o evento: a vaga nasce sem teto, com aviso.

**Por que esta prioridade**: o cadastro é do dono — a Visita é o primeiro produto, não o último.

**Verificação**: cenários 13, 14 e 17 (DEVE FALHAR).

**Cenários de aceite**:

1. **Dado** o superadmin salvando `produtos` válido, **Então** 200, persistido (conexão separada) e
   devolvido em `GET /orcamento/opcoes`; **Dado** preço ≤ 0, chave fora de `^[a-z0-9_]{1,30}$`, vaga sem
   label, tipo de vaga desconhecido, `por_faixa` com faixa inexistente ou descrição > 120, **Então** 400
   com `fields["produtos.<chave>.<campo>"]` e nada gravado.
2. **Dado** produto `ativo: false` citado num snapshot antigo, **Então** recalcula com o preço dele;
   **Dado** produto apagado citado num snapshot antigo, **Então** a venda responde erro de validação
   nomeando o produto e o teto das vagas dele sai sem teto com nota "produto não está mais na tabela".
4. **Dado** um produto sem preço de 24/25 vendido em 24/12, **Então** o preço sai estimado
   (Σ cachês normais × 2,0 × 3,0), marcado como estimativa na memória, no resultado, na mensagem e no
   PDF, e o teto das vagas segue a faixa.
3. **Dado** um COMERCIAL, **Quando** `POST /api/orcamento/settings`, **Então** 403.

---

### História 5 — Produto e itens avulsos convivem no mesmo orçamento (Prioridade: P2)

Festa de 4h com um boneco **e** uma Visita Mágica: as colunas 1h–4h mostram o boneco pela fórmula
em cada coluna **+ 2.500 fixos**; o coordenador incluído no produto não é cobrado em dobro; fora de SP
soma por cima; NF, acréscimos (BV) e PIX incidem sobre o total com o produto; a régua >4h escala só
os avulsos; personalizado "valor final" vence tudo e "multiplicador" não multiplica o produto.

**Por que esta prioridade**: é o caso real de dezembro (bonecos + Noel) e é onde a conta quebra.

**Verificação**: cenários 5, 6 e 7.

**Cenários de aceite**:

1. **Dado** produto Noel + boneco avulso em 20/12 com coordenador 1, **Então**
   `total_Nh = boneco_Nh × markup_Nh + 2.500` (nenhum coordenador fora do produto é cobrado) e, com
   dois produtos, dois coordenadores e dois Noéis no teto.
2. **Dado** fora de SP (manto, van, 50 km), **Então** o transporte de hoje soma por cima de 2.500;
   **Dado** NF, **Então** (2.500 + avulsos) ÷ 0,84; **Dado** BV 10 %, **Então** `valores_brl` = 10 % do
   total com produto; a mensagem mostra PIX = total × 0,95.
3. **Dado** duração 6h com produto + boneco, **Então** `total_custom = boneco_4h ÷ 4 × 6 + 2.500`;
   **Dado** personalizado valor final 3.000, **Então** 3.000 e a memória (sem a linha do produto) fecha
   com o total; **Dado** multiplicador 2, **Então** `cache_base × 2 + 2.500`.

---

### História 6 — Os tetos 712/423 já gravados são corrigidos (Prioridade: P2)

Eventos de Noel criados entre 16/10 e o deploy nasceram com teto 712/423. Um script de uma vez
relata as vagas afetadas (evento, data, vaga, teto, cachê) e, com `--execute`, rebaixa para 600/270
só as vagas **sem cachê digitado e sem artista** com teto exatamente 712/423. O dono roda no Shell do
Render; o relatório zero prova que acabou.

**Por que esta prioridade**: sem isso o casting continua podendo pagar 712 nos eventos de dezembro
já na agenda.

**Verificação**: cenário 18.

**Cenários de aceite**:

1. **Dado** uma vaga descartável com teto 712, sem cachê e sem artista, **Quando** o script roda sem
   `--execute`, **Então** só lista; **Quando** roda com `--execute`, **Então** o teto vira 600 e a nota
   do teto registra a correção; **Dado** uma vaga com cachê já digitado ou artista escalado,
   **Então** não é tocada e aparece no relatório como "não corrigida — conferir à mão".

---

### História 7 — O resto não muda (Prioridade: P3)

EducaManto ignora `produtos`; orçamentos salvos antes da feature continuam congelados e, sem a chave,
a conta é byte a byte a de antes (fora Noel/Ajudante avulsos, História 3); na janela de deploy (bundle
novo com backend velho) "Gerar Orçamento" fica travado quando há produto selecionado e a resposta
veio sem `quote.produtos`.

**Verificação**: cenários 1, 15, 16 e 19 (regressão 305 e 307 atualizado).

**Cenários de aceite**:

1. **Dado** um payload sem `produtos`, **Então** `quote` idêntico ao de hoje (comparação chave a chave
   contra a 307); **Dado** a contratação Manto do EducaManto com `produtos` no payload, **Então**
   totais iguais aos sem a chave.
2. **Dado** um produto selecionado e `result.quote.produtos` ausente, **Então** o botão fica
   desabilitado com o aviso "o servidor não aplicou o produto" (conferência de tela).

### Casos de borda

- Produto sem preço para a faixa da data (ex.: produto novo sem `por_faixa.natal` em 24/12): o preço
  do produto é **estimado** = Σ cachês das vagas pela tabela normal × `fator_cache` (2,0) × `markup`
  da estimativa (3,0) — Visita Noel: (600 + 250 + 250) × 2 × 3,0 = 6.600 —, com `estimado: true` no
  `quote.produtos[]`, linha da memória "preço estimado (sem preço de 24/12)" e aviso dourado forte na
  calculadora e no resultado; mensagem e PDF levam "(estimativa)" junto do produto. O teto das vagas
  segue a tabela vigente na data (faixa), não a estimativa.
- Dois exemplares do mesmo produto: dois Noéis, dois coordenadores, dois maquiadores? — um Maquiador
  por produto (a vaga é do produto); `num_going` conta todas as pessoas para a van.
- Avulso maquiado junto do produto (que já inclui Maquiador): a vaga Maquiador do produto vale e o
  make do avulso entra como adicional (`make_2_adicional`) no teto; na venda cobra-se só o incremento.
- "Papai Noel" avulso **e** produto no mesmo orçamento: permitido (dois Noéis), ambos com teto 600; o
  aviso "use o produto" só aparece quando não há produto.
- Personagem do título do Google diferente do label ("Duende", "Elfo"): o vínculo 273 casa por nome —
  não casa com "Ajudante do Noel" e a vaga fica sem teto, como hoje para qualquer nome diferente
  (registrado; alias de nomes fora de escopo).
- `coordenador_qty` menor que o número de coordenadores dos produtos: o total é elevado ao dos
  produtos; o campo mostra "N incluído(s) no produto".
- Produto com `preco` igual nas duas faixas ou `por_faixa` vazio: válido; sem variante na data de
  faixa = estimativa marcada (acima).
- `_migrar_309` recebe bloco malformado (`produtos: null`, produto sem `vagas`, preço string): produto
  inválido é descartado na carga (nunca preço 0), os DEFAULTS entram só quando a chave está ausente —
  e nada disso derruba o `load()` (exceção ali devolveria os DEFAULTS para a tabela inteira).
- Orçamento salvo com produto cujo preço o dono mudou depois: congelado (regra 020) — o teto do evento,
  porém, é recalculado da tabela viva na criação/vínculo, como hoje.

## Requisitos *(obrigatório)*

### Requisitos funcionais

- **FR-001**: A tabela de preços DEVE ter o bloco `produtos` (dicionário chave → produto) com: `rotulo`
  (1–60), `descricao` ao cliente (0–120), `ativo`, `preco` (um valor em R$ > 0, fixo por visita),
  `por_faixa` (chave de faixa de `datas_especiais` → `{preco}`), `vagas` (1–10 itens: `label` 1–120,
  `tipo` ∈ {especial, ator, coordenador, maquiador}, `cache` = `null` "pela tabela vigente na data" ou
  um valor em R$ > 0) e `inclui_noturno` (padrão `true`); e o bloco irmão `produtos_estimativa`
  (`fator_cache` > 0, padrão 2,0; `markup` em [1, 6], padrão 3,0) usado quando o produto não tem preço
  para a faixa da data. Chave ausente = sem produtos = conta de hoje.
- **FR-002**: Os produtos padrão DEVEM ser "Visita Mágica — Papai Noel" (2.500; natal 5.000; vagas
  Papai Noel · Coordenador · Maquiador, todas pela tabela) e "Visita Mágica — Papai Noel + Ajudante"
  (3.600; natal 6.500; + Ajudante do Noel pela tabela), descrição "visita padrão (até 1h)", ativos.
- **FR-003**: A vendedora DEVE selecionar produtos na calculadora num card próprio ("Produtos de
  tabela") com `Combobox` (nunca `<select>` nativo), podendo repetir e remover; a chave `produtos:
  [{chave}]` vai no payload ao lado de `performers`.
- **FR-004**: O preço do produto DEVE entrar na conta DEPOIS do markup e ANTES de brinde, noturno,
  técnico, maquiador, transporte, acréscimos e NF; DEVE ser o mesmo nas quatro durações e NÃO escalar
  pela régua >4h (`total_custom = (total_4h − Σprodutos) ÷ 4 × h + Σprodutos`).
- **FR-005**: O produto com `inclui_noturno: true` NÃO soma o adicional noturno nem na venda nem no
  teto das vagas dele; avulsos continuam somando.
- **FR-006**: O coordenador incluído no produto NÃO pode ser cobrado em dobro: a regra
  `coordenadores_da_formula = max(0, coordenador_qty − Σ coordenadores dos produtos)` DEVE ser única
  para venda e teto; a tela mostra "N incluído(s) no produto" e o total nunca fica abaixo do dos
  produtos.
- **FR-007**: A vaga Maquiador do produto vale pela tabela (250) sem cobrar maquiagem à parte no preço
  do produto; makes de avulsos entram como adicionais no teto e cobram só o incremento na venda.
- **FR-008**: A memória de cálculo DEVE ter uma linha do tipo `produto` por exemplar, depois de
  "= Após markup", e continuar somando com o TOTAL; no personalizado "valor final" a linha sai (o
  digitado vence); no "multiplicador" o produto NÃO é multiplicado (`cache_base × mult + Σprodutos`).
- **FR-009**: A mensagem WhatsApp e o PDF DEVEM trazer a linha do produto com descrição e preço
  aplicado, e listar os personagens do produto na equipe; com só o produto no orçamento a tela de
  resultado mostra um valor só (durações iguais).
- **FR-010**: O `quote` DEVE ganhar `produtos: [{chave, rotulo, descricao, preco_aplicado,
  faixa_chave|null, estimado}]` e `avisos: [str]`; o `snapshot` ganha `produtos: [{chave}]`.
  Snapshot sem a chave = conta de hoje; orçamento salvo é congelado.
- **FR-011**: O teto das vagas (prefill, criação e vínculo 273) DEVE emitir primeiro as vagas dos
  produtos — flat em todas as colunas, cachê pela tabela vigente na data do EVENTO (faixa da 307
  inclusa) ou o valor fixo da vaga — depois os avulsos, depois os extras, na MESMA ordem no prefill e
  na criação; o cachê da vaga continua nascendo vazio e o casting continua rebaixado ao teto; produto
  que não existe mais na tabela → vaga sem teto com nota explicando, nunca teto 0.
- **FR-012**: "Papai Noel" DEVE voltar a [600, 650, 675, 700] e "Ajudante do Noel" a
  [270, 320, 345, 370] nos padrões; a troca automática 600→712 DEVE ser removida da carga; uma troca
  inversa guardada DEVE agir só sobre [712, 800, 850, 900] e [423, 480, 510, 540] exatos; os dois
  especiais NÃO são excluídos; a calculadora DEVE avisar "Para a Visita Mágica use o produto" quando
  "Papai Noel" entra avulso sem produto.
- **FR-013**: `POST /api/orcamento/settings` DEVE aceitar `produtos` validado no núcleo (exceção
  própria com `fields` `produtos.<chave>.<campo>`): chave `^[a-z0-9_]{1,30}$`, rótulo 1–60, descrição
  ≤ 120, preço > 0 finito, `por_faixa` só com faixas existentes e preço > 0, 1–10 vagas com label
  1–120 e tipo conhecido, `cache` `null` ou > 0, `ativo` e `inclui_noturno` booleanos; o bloco enviado
  substitui o salvo; corpo inválido não grava nada; papéis sem permissão levam 403. O bloco
  `produtos_estimativa` é validado junto (`fator_cache` > 0 finito; `markup` em [1, 6]).
- **FR-014**: A Configuração de Preços DEVE ter o card "Produtos de tabela" no molde do card de datas
  especiais (erro por campo com `aria-invalid` e foco; chips para vagas; `PriceTable` não se aplica —
  preço é um valor só).
- **FR-015**: `GET /api/orcamento/opcoes` DEVE devolver `settings.produtos` (a calculadora lê de lá);
  fica registrado que os cachês "pela tabela" já chegam ao navegador da vendedora hoje — recorte
  só-superadmin é fatia própria.
- **FR-016**: A contratação Manto do EducaManto DEVE continuar neutra: `produtos` é removido do
  payload antes de calcular; o card não existe lá.
- **FR-017**: "Gerar Orçamento" DEVE ficar desabilitado quando há produto selecionado e a resposta do
  cálculo veio sem `quote.produtos` (backend antigo na janela de deploy), com aviso.
- **FR-018**: Um script de uma vez (`scripts/oneoff/rebaixar_tetos_noel_309.py`) DEVE relatar e, com
  `--execute`, rebaixar para 600/270 as vagas "Papai Noel"/"Ajudante do Noel" com teto exatamente
  712/423, `cache_value` vazio e sem artista, registrando a correção na nota do teto; as demais só
  aparecem no relatório.
- **FR-019**: A faixa de data especial da 307 (markup 3,34, cachês, piso 650, nota) DEVE continuar
  valendo para avulsos em 24/25. Produto sem preço para a faixa da data DEVE sair **estimado**:
  Σ cachês das vagas pela tabela normal × `produtos_estimativa.fator_cache` × `produtos_estimativa.markup`,
  com `estimado: true`, linha própria na memória, "(estimativa)" na mensagem e no PDF e aviso dourado
  forte — nunca o preço normal em silêncio, nunca bloqueio; o teto das vagas segue a tabela vigente na
  data.
- **FR-020**: Fora de SP (262) soma por cima do produto contando as pessoas dele; NF ÷ 0,84, acréscimos
  % (BV da 305 com `valores_brl`) e PIX −5 % incidem sobre o total com o produto.
- **FR-021**: `verify_307.py` DEVE ser atualizado onde afirma 712 / 2.501 / 3.601 / teto 712 (passa a
  600 / 2.210 / 2.912 / 600) e continuar verde; `verify_305.py` em regressão.

### Entidades *(se houver dados)*

- **Produto de tabela** (JSON `pricing_config.produtos.<chave>`): rótulo, descrição, ativo, preço fixo,
  preço por faixa, vagas (label, tipo, cachê ou "pela tabela"), inclui_noturno. Sem tabela nova.
- **Seleção de produto** (snapshot `produtos: [{chave}]`; quote `produtos: [...]`): o que a vendedora
  vendeu, congelado no orçamento.
- **Vaga do produto** (`EventRole` existente): nasce com `cache_cap` = cachê resolvido e `cache_value`
  vazio — nenhuma coluna nova.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

- Nenhum endpoint novo. `POST /api/orcamento/settings` (SUPERADMIN, `_require_superadmin`) passa a
  aceitar o bloco `produtos`; `GET /api/orcamento/opcoes` (COMERCIAL/SUPERADMIN, `_require_vendas`)
  passa a devolvê-lo; `POST /api/orcamento/calcular` e `/salvar` (vendas) aceitam `produtos` no payload
  — linhas de `docs/01` §4.3 atualizadas, não acrescentadas. O script de uma vez roda no servidor, sem
  rota.

## Verificação (`verify_309.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/309-produtos-de-tabela/verify_309.py`, contra `manto_local` (`DATABASE_URL` de
`.local-db-url`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`). Configuração de preços real salva e
restaurada por conexão separada (config de teste determinística: markup 2,6, coordenador 250, make 250,
Noel [712, …] e Ajudante [423, …] gravados para provar a migração inversa, sem `produtos` para provar
os padrões). Login só por `POST /api/auth/login` com usuários descartáveis (superadmin, comercial,
casting); evento descartável criado só pela API com escrita no Google suprimida, roles sem
`character_name` inventado persistente (criadas e apagadas na mesma rodada); limpeza no `finally`.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | payload sem `produtos` | quote idêntico chave a chave ao de hoje (paridade) | não |
| 2 | produto Noel 20/12 | 2.500 nas 4 colunas; memória com linha `produto` fechando com o total; mensagem e PDF com a linha; `data_especial` None | não |
| 3 | Noel 24/12 · Noel+Ajudante 20/12 e 25/12 | 5.000 · 3.600 · 6.500; `quote.produtos[].faixa_chave` | não |
| 4 | produto às 20h; produto + boneco às 20h | 2.500 (noturno embutido); boneco soma só o noturno dele | não |
| 5 | produto + boneco 4h; dois produtos | `total_Nh = boneco × markup + 2.500`; coordenador não em dobro; 2 produtos = 2 coordenadores | não |
| 6 | fora de SP, NF, BV 10 %, PIX | transporte por cima; ÷0,84 sobre total com produto; `valores_brl`; mensagem × 0,95 | não |
| 7 | régua 6h; personalizado valor final e multiplicador | avulsos escalam, produto fixo; digitado vence (memória fecha); `cache_base × 2 + produto` | não |
| 8 | `_compute_performer_caches` com produto | ordem produto → avulsos → extras; 600/270/250/250 flat; 24/12 1.000/650/500; `horas_extra` não escala o produto; cap_notes | não |
| 9 | criação por API (Google suprimido), prefill e vínculo 273 | `EventRole` com `cache_cap` 600/270/250/250 e `cache_value` vazio nos três caminhos; data do evento manda | não |
| 10 | `assign_role` casting × superadmin | casting 900 → 600; superadmin 900 → 900 | não |
| 11 | migração | 712→600 e 423→270 guardadas; Noel 650 intocado; Noel 600 não vira 712; `produtos` ausente → padrões; bloco malformado descartado sem derrubar `load()` | não |
| 12 | avulsos | Noel avulso 20/12 = 2.210 com `avisos`; 24/12 avulso = 5.010 (faixa da 307) | não |
| 13 | `POST /settings` | válido persiste (conexão separada) e volta no `/opcoes`; 7 corpos inválidos → 400 por campo, nada gravado | não |
| 14 | produto inativo e produto apagado | inativo recalcula snapshot antigo; apagado → erro de validação na venda e vaga sem teto com nota no teto | não |
| 15 | produto sem `por_faixa` em 24/12 | preço estimado = Σ cachês normais × 2,0 × 3,0 (Noel: 6.600); `estimado: true`; linha da memória e aviso; teto das vagas pela faixa (1.000/500/250) | não |
| 16 | EducaManto | `_totais_contratacao` com e sem `produtos` → iguais (com a faixa provadamente ativa na venda) | não |
| 17 | COMERCIAL `POST /settings` | 403 | **sim** |
| 18 | script `rebaixar_tetos_noel_309.py` | relatório sem `--execute`; `--execute` rebaixa só vaga 712/423 sem cachê e sem artista; as outras ficam e aparecem no relatório | não |
| 19 | regressão (`--regressao`) | `verify_307.py` atualizado e `verify_305.py` verdes | não |
| 20 | limpeza | usuários, orçamentos, evento e roles descartáveis apagados (`roles.clear()`); configuração real restaurada e conferida | — |

Conferência de tela (Browser pane): `/orcamento` (card Produtos com Combobox; valor único quando só
produto; aviso de faixa; aviso "use o produto"; botão travado simulando `quote.produtos` ausente);
`/orcamento/:id` (linha do produto); `/orcamento/configuracoes` (card Produtos de tabela com 400
apontando o campo e foco); `/events/new?orcamento_id=` (tetos 600/270/250/250 nas vagas).

## Critérios de sucesso *(obrigatório)*

- **SC-001**: A Visita Mágica sai exatamente R$ 2.500 / R$ 3.600 em data normal e R$ 5.000 / R$ 6.500
  em 24 e 25/12 (não 2.501 / 3.601 / 5.010 / 7.181), sem acréscimo manual.
- **SC-002**: 100 % dos eventos criados de orçamento com produto nascem com teto do Noel 600 (1.000 em
  24/25) e do Ajudante 270 (650); nenhuma vaga de produto nasce com teto 712/423 nem 0.
- **SC-003**: Orçamentos sem produto saem com os mesmos números de antes, exceto Noel/Ajudante
  avulsos, que passam a 600/270 (decisão do dono).
- **SC-004**: O superadmin cria ou altera um produto pela tela e o preço vale no próximo cálculo, sem
  deploy; erro de cadastro aponta o campo.
- **SC-005**: EducaManto, PDF, BV do evento (305) e conta inversa continuam iguais (verifies 305 e 307
  atualizado verdes).
- **SC-006**: Depois do script, zero vagas de Noel/Ajudante com teto 712/423 sem cachê digitado.

## Fora de escopo

- Markup por item; piso de cachê no casting ("não pode pagar menos de 600" contraria a 236).
- Pacote de 30 minutos com coluna própria de duração; produto que escala por duração.
- Outros produtos além da Visita Mágica (o modelo é genérico; o cadastro é do dono).
- Alias de nomes no vínculo 273 ("Duende" ↔ "Ajudante do Noel").
- Recorte só-superadmin dos cachês no `/opcoes`.
- Troca do `<select>` nativo de especiais do `PerformersEditor` pelo `Combobox` (#103) — fatia
  Nível 2 própria.

## Docs a atualizar

`docs/01` (§2.10 `pricing_config.produtos`; §3.13 `quote.produtos`/`avisos`, `snapshot.produtos`,
`POST /settings` com `produtos`, memória tipo `produto`, especiais 600/270; §4.3 linhas atualizadas),
`docs/02` (`/orcamento`, `/orcamento/:id`, `/orcamento/configuracoes`, `/events/new`), `docs/03`
(entrada no topo + índice; a 307 fica como história — "712/423 durou de 16/10 a …"), `docs/04` (linha
Orçamento: produto pós-markup; teto pela tabela; invariantes), `docs/05` (quitar #107 pelo script;
#103 continua; registrar cachês visíveis no `/opcoes` e a regra do `verify_307` mudada).

## Premissas

- Markup de produção 2,6 (1h) e coordenador 250 / make 250 (tabela de 2026) — conferidos no espelho e
  em produção em 16/10.
- 2h–4h dos especiais avulsos: Noel 650/675/700 (tabela antiga) e Ajudante 320/345/370 (degrau do
  ator) — confirmados pelo dono em 19/10; só importam para o avulso e para a régua.
- Fatores da estimativa (produto sem preço na faixa): `fator_cache` 2,0 e `markup` 3,0 ("um pouco
  mais alto que o padrão 2,6") — editáveis pelo superadmin; a estimativa é sempre marcada como tal.
- Label fixo "Ajudante do Noel" mesmo quando o personagem é duende/elfo/Rubi/Esmeralda.
- Descrição ao cliente "visita padrão (até 1h)"; sem a frase de presentes (veto da 307).
- Um Maquiador por produto; o preço do produto não cobra maquiagem à parte.
- A tabela de venda é "sem nota" e "antes do PIX" (NF ÷ 0,84 e −5 % incidem como nos demais).
- A faixa `natal` da 307 continua em produção (markup 3,34, cachês 1.000/650/500, piso 650) e é a fonte
  do cachê das vagas do produto em 24/25.
- Esforço 6–7 noites (estimativa dos céticos); deploy à noite, fora do horário da equipe.
