# Feature 313 — O desconto negociado nasce no orçamento, o PIX vale o maior e o acréscimo entra uma vez

**Branch**: `313-desconto-e-pix-na-calculadora` (da `main` em `c074657b`) · **Created**: 2026-10-21 · **Status**:
Rascunho · **Migration**: nenhuma · **Nível**: 1 (feature) — contrato do cálculo do orçamento, do prefill do Novo
evento e do vínculo orçamento → evento alterados; três domínios (orçamento, agenda/venda do evento, e a conta
compartilhada com o EducaManto) — constituição, Princípio VI

**Input**: pedido do dono: "pode começar a 3b" (21/10/2026) — item **3b** do backlog de setembro, **noite do
desconto** (Preparação + P1 da seção 10 do plano). Os dias adicionais (P2 + P3 da mesma seção) são outra feature,
numa noite própria. Fonte completa e revisada: `docs/backlog/3b-calculadora-desconto-e-dias.md` (checkout
principal, untracked; nove dúvidas respondidas em quatro rodadas, nenhuma aberta), reconferida contra a `main` de
21/10 em `pesquisa/reconferencia-2026-10-21.md` e recontada em produção no mesmo dia (seção "Números"). Autorização
para esta esteira: a mesma da 1c — "das coisas já definidas por perguntas pode ir seguindo até implementação"
(20/10), estendida ao item pelo "pode começar a 3b"; merge e push só quando o dono pedir.

## O pedido, nas palavras do dono *(obrigatório)*

Decisões da triagem de setembro (`docs/PLANO_BACKLOG_SETEMBRO.md`, não se reabrem):

> **D3 — Desconto**: % na calculadora, salvo no orçamento, mostrado na mensagem e no PDF, e levado ao evento como
> "valor antes do desconto" e "valor de venda".
>
> **D4 — PIX à vista**: não soma com o desconto negociado: **vale o maior**.

E as respostas que dizem como (seção 7 do plano):

- **Q1 = A** (06/10): o desconto vale "sobre o total do orçamento: apresentação + transporte + acréscimos + nota" —
  a mesma base do PIX à vista.
- **Q8 = B** (13/10): "Tem que funcionar bilateral: ou digita o valor e mostra a porcentagem, ou digita a
  porcentagem e calcula o valor."
- **Q3 = A** (13/10): "A ideia é: quando fizer o orçamento, ele faz o cálculo de 5% automaticamente. Porém algumas
  vezes os clientes choram por desconto adicional e o vendedor altera, dando mais desconto. Ou seja, na proposta
  deve ser mostrado de quanto foi o desconto (de forma arredondada). Mas ainda segue valendo o padrão dos 5%."
- **Q2 = C** (13/10): o PIX à vista no evento, "comercial digitando" — sem botão nem conta automática.
- **Q7** (13/10): "Acho que misturou conceitos. O acréscimo adicionado manualmente é colocado por cima de tudo no
  valor. E o BV é calculado em cima de tudo isso."
- **Q9 = B** (13/10): o BV digitado em reais continua — "Sim, mas reformulado para funcionar com todas essas
  mudanças atuais."
- **3a-Q1 = B** (06/10, no plano irmão): "se o valor total do orçamento mudar, o BV deve acompanhar
  proporcionalmente."

O sintoma de hoje, como a equipe vive: o orçamento não tem desconto. A comercial negocia, digita o valor fechado à
mão no evento e o orçamento fica com o preço cheio; a proposta afirma "desconto especial de 5% aplicado" sempre,
mesmo quando a cliente ganhou mais; e o acréscimo em reais é multiplicado pelas horas na duração extra.

## Clarifications

### Decisões do dono (palavras dele; não se reabrem)

As sete respostas acima. Delas, o que se constrói:

1. O desconto é um percentual sobre o **total** do orçamento, o último passo da conta (depois da nota) — Q1 = A.
2. A comercial digita **o % ou o valor final de uma duração**, e um calcula o outro; as outras durações recebem o
   mesmo % — Q8 = B.
3. A proposta (mensagem e PDF) mostra "de R$ X por R$ Y" e "desconto de N%" arredondado; o 5% do PIX continua
   calculado sozinho e **vale o maior** entre ele e o negociado — Q3 = A, D4.
4. No evento, o PIX à vista a comercial continua digitando — Q2 = C. O evento nasce com o "valor antes do desconto"
   = o cheio do orçamento e o "valor de venda" = o total com o desconto negociado — D3.
5. O acréscimo manual entra **uma vez**, por cima do valor, em qualquer duração (não se multiplica na duração
   extra); o BV em % é calculado **sobre o valor com os acréscimos**, antes da nota — Q7.
6. O BV em reais continua: entra uma vez, no passo do BV, e encolhe com o desconto como o em %; a linha do BV nova
   nasce com o "%" marcado — Q9 = B.
7. O BV de quem indicou acompanha o valor final na mesma proporção — no desconto e no PIX — 3a-Q1 = B.

### Session 2026-10-21 (`/speckit-specify`) — leituras fixadas por esta spec, não palavras do dono

Premissas contestáveis; o dono só precisa dizer se discorda.

1. **Desconto sobre o preço de tabela (309).** Com produto de tabela (Visita Mágica) no orçamento, o desconto
   negociado incide também sobre ele: a Q1 = A diz "total", e o PIX de 5% já vale sobre o produto hoje. A linha do
   produto na proposta continua mostrando o preço cheio (é parte do "de"); o "por" é o total com desconto. Nenhum
   orçamento de produção usa produto ainda (recontagem de 21/10).
2. **Acréscimo negativo** (dívida 100 do `docs/05`: o servidor aceita) segue como acréscimo manual — entra uma vez,
   e baixa a base do BV em % como qualquer acréscimo. Nenhum orçamento de produção tem acréscimo negativo.
3. **O que já foi cotado não muda.** Orçamento salvo antes desta entrega continua com o preço que a cliente recebeu,
   na tela, no PDF e quando vira evento depois — inclusive acima de 4h e no BV que nasce no evento (a 305 lê o
   orçamento salvo). Só o "Recalcular", que gera um orçamento novo, sai pela regra nova (020).
4. **O BV do evento encolhe pelo cheio.** A 305 calcula o BV do evento pela proporção venda ÷ total do orçamento;
   com o desconto dentro do total, a razão daria 1 e o BV não encolheria. A proporção passa a ser venda ÷ **valor
   antes do desconto** (o cheio da duração) — a função única da 305 (`bv_que_acompanha`) não muda de assinatura nem
   de tolerância; muda o número que se passa a ela.
5. **Personalizado com desconto.** O desconto incide também sobre o valor personalizado digitado (plano, passo 6);
   a tela diz isso ao lado do campo, para não parecer que o desconto "some" no personalizado.
6. **O % da proposta e o selo do evento batem.** O "N% de desconto" da proposta é arredondado a uma casa **para
   baixo**, com vírgula e sem ",0" ("8,3%", "10%"): a proposta nunca promete mais do que dá. O selo "N% de
   desconto" do valor de venda no evento passa a usar a mesma regra, para o mesmo desconto não aparecer "8,4%" num
   e "8,3%" no outro.
7. **Fora desta noite, mas no mesmo plano:** os dias adicionais (P2/P3), que dependem do criador de dias do grupo e
   sobem noutra noite. Nenhuma chave de dias é aceita nem devolvida aqui.

## Cenários e Verificação *(obrigatório)*

Semente comum do `verify_313.py`: orçamentos montados pela API de cálculo (nunca semeando `EventRole` inventada),
com e sem transporte fora de SP, acréscimo em R$, BV em % e em reais, nota e duração extra; o Google dublado como
nos verifies da 305/312; usuários descartáveis Comercial, Superadmin, Financeiro, Casting e Revendedor EducaManto.
Antes de mexer no núcleo, um **gabarito de paridade** recalcula os orçamentos reais do espelho com a conta de hoje,
na `c074657b` (seção "Verificação").

### História 1 — A comercial dá o desconto no orçamento, em % ou pelo valor fechado (Prioridade: P1)

A comercial monta o orçamento como hoje e, quando a cliente "chora por desconto", digita o percentual — ou o valor
fechado de uma das durações ("as 2 horas por R$ 2.200") — no bloco Desconto. A calculadora mostra, por duração, o
valor cheio riscado e o valor com desconto, e o percentual (quando ela digitou o valor) ou o valor de cada duração
(quando digitou o %). O orçamento salvo guarda o que ela digitou; o "Recalcular" reabre igual.

**Por que esta prioridade**: uma em cada três vendas desde junho tem desconto (92 de 267), todo digitado à mão no
evento; o orçamento não registra o que foi negociado.

**Verificação**: cenários 2, 3 e 4 do `verify_313.py`.

**Cenários de aceite**:

1. **Dado** um orçamento de R$ 2.400 em 2h, **Quando** a comercial digita 10%, **Então** cada duração mostra o
   cheio e o valor × 0,9, ao centavo, e o orçamento salvo guarda "10%".
2. **Dado** o mesmo orçamento, **Quando** ela escolhe "fechar as 2 horas por R$ 2.200", **Então** as 2 horas saem
   exatamente R$ 2.200,00, o % mostrado é "8,3%", e as outras durações recebem o mesmo % exato (8,333…%), ao
   centavo.
3. **Dado** um orçamento fora de SP com transporte, acréscimo em R$ e nota, **Quando** há desconto de 10%, **Então**
   o desconto incide sobre o total com tudo isso dentro — nunca só sobre a apresentação.
4. **Dado** um valor fechado maior que o cheio, zero, ou numa duração que o orçamento não oferece, **Quando** ela
   calcula, **Então** a tela mostra o erro no campo do desconto e nada é calculado com ele.
5. **Dado** um orçamento salvo com desconto, **Quando** ela usa "Recalcular", **Então** o campo reabre como ela
   digitou (o % ou o valor e a duração); **Dado** um orçamento salvo antes desta entrega, **Então** o campo reabre
   vazio.
6. **Dado** um orçamento com produto de tabela (309), **Quando** há desconto, **Então** o produto entra na base
   (Session 1) e o "fechar por R$" só oferece a duração que a proposta mostra.

---

### História 2 — A proposta diz o desconto, e o PIX vale o maior (Prioridade: P1)

A cliente recebe a mensagem do WhatsApp e o PDF com, em cada duração, "de R$ X por R$ Y" e "(desconto de N%
aplicado)". O bloco "À Vista (PIX)" continua calculando os 5% sozinho; quando o negociado já é de 5% ou mais, ele
diz "o mesmo valor — o desconto de N% já está aplicado", sem baixar mais.

**Por que esta prioridade**: é o texto que a cliente lê; hoje ele não fala do desconto negociado e promete 5% de
PIX por cima de qualquer valor.

**Verificação**: cenários 5, 6 e 7.

**Cenários de aceite**:

1. **Dado** um orçamento sem desconto, **Então** a mensagem e o PDF são os de hoje, palavra por palavra.
2. **Dado** desconto de 3%, **Então** "de/por", "desconto de 3%" e o PIX de 5% sobre o **cheio** (não 3% e depois
   5%), com a frase de hoje.
3. **Dado** desconto de 10%, **Então** "de/por", "desconto de 10%" e "À Vista (PIX): o mesmo valor — o desconto de
   10% já está aplicado".
4. **Dado** desconto de 4,96%, **Então** a proposta diz "4,9%" e o PIX é de 5% (o "vale o maior" compara o exato).
5. **Dado** um orçamento com transporte fora de SP e desconto, **Então** "Valor da Apresentação" e "Logística e
   Transporte" mostram o valor cheio e somam o "de".
6. **Dado** um orçamento só com produto de tabela, **Então** a proposta tem o mesmo "de/por" e o mesmo bloco de PIX
   no formato que a 309 já usa para ele.
7. **Dado** qualquer orçamento com BV, **Então** a palavra "BV" não aparece na mensagem nem no PDF (hoje também
   não).
8. **Dado** um orçamento salvo antes desta entrega, **Quando** o histórico, o PDF ou o e-mail dele são abertos,
   **Então** saem como saíam ("PIX à vista (5%" como sempre).

---

### História 3 — O acréscimo entra uma vez e o BV é calculado sobre tudo (Prioridade: P1)

Na calculadora, um acréscimo em R$ (urgência, "Outro", deslocamento) entra uma vez em qualquer duração — numa
duração extra de 8h a urgência de R$ 300 continua R$ 300 — e o BV em % incide sobre a apresentação com os
acréscimos, antes da nota. O BV em reais entra uma vez, no passo do BV. A linha nova de BV nasce com o "%" marcado.
A ajuda da "Duração extra" diz a conta de verdade.

**Por que esta prioridade**: é a regra que o dono deu na Q7; sem ela, o desconto e o BV que acompanha seriam
calculados sobre uma conta que ele recusou.

**Verificação**: cenários 1 (paridade com exceções listadas), 8, 9 e 10.

**Cenários de aceite**:

1. **Dado** base de 4h R$ 4.000 com urgência de R$ 300 e duração extra de 8h, **Então** a extra é R$ 8.300 (hoje R$
   8.600); com nota, o ÷ 0,84 incide sobre os R$ 8.300.
2. **Dado** base R$ 2.000, "Outro" de R$ 200 e BV de 10%, **Então** o BV é R$ 220 e o preço R$ 2.420; com nota, o
   BV continua R$ 220.
3. **Dado** BV de R$ 150 em reais, "Outro" de R$ 200 e base de R$ 2.000, **Então** o preço é R$ 2.350 e o BV
   continua R$ 150 também na extra de 6h.
4. **Dado** um BV em reais e um em % no mesmo orçamento, **Então** o em % não vê o em reais (os BVs não se
   somam um sobre o outro).
5. **Dado** produto de tabela numa duração extra, **Então** o produto continua fixo (309) e só a base escala.
6. **Dado** a contratação Manto do EducaManto, **Então** a mesma regra de acréscimo e BV vale lá, e nenhuma chave de
   desconto chega à conta dela.
7. **Dado** os orçamentos reais do espelho, **Então** todos dão o mesmo preço de antes, exceto as exceções
   conhecidas (BV com outro acréscimo; duração extra com acréscimo em R$), cada uma conferida pela fórmula.

---

### História 4 — O evento nasce com o cheio e a venda, e o BV encolhe junto (Prioridade: P1)

No Novo evento a partir de um orçamento com desconto, o "valor antes do desconto" vem com o cheio da duração e o
"valor de venda" com o valor com desconto; o selo "N% de desconto" aparece sozinho. O quadro do BV do orçamento (305)
mostra o BV já encolhido e não acusa "valor diferente do orçamento" quando a venda é o total com desconto. Ao salvar,
o BV gravado é o que acompanha a venda salva — também quando a comercial digita o PIX por cima. O "Outra (h)" usa o
preço do servidor (o acréscimo uma vez). Vincular o orçamento a um evento já criado (273) grava os mesmos dois
valores.

**Por que esta prioridade**: o desconto só vale se chegar à venda, à comissão e ao BV do evento.

**Verificação**: cenários 11, 12, 13 e 14.

**Cenários de aceite**:

1. **Dado** um orçamento com 10% de desconto e BV de 10%, **Quando** o Novo evento abre por ele, **Então** o cheio
   e a venda vêm separados, e o quadro do BV mostra o BV × 0,9.
2. **Dado** esse evento salvo pela venda do orçamento, **Então** o BV gravado é o BV cheio × venda ÷ cheio, a
   comissão a pagar é % × (venda − BV), e o Dashboard Comercial soma o desconto concedido.
3. **Dado** a comercial digitando o PIX por cima da venda antes de salvar, **Então** o BV gravado acompanha a venda
   digitada.
4. **Dado** um orçamento salvo antes desta entrega (sem as chaves novas), **Quando** vira evento, **Então** o BV e
   os valores saem como sairiam hoje (Session 3).
5. **Dado** "Outra (h)" de 7h num orçamento novo com acréscimo em R$, **Então** o valor sugerido é o do servidor
   (o acréscimo uma vez), igual ao de um orçamento calculado com 7h; num orçamento salvo antes, a régua de hoje.
6. **Dado** o vínculo (273) de um orçamento com desconto a um evento sem venda, **Então** o evento grava o cheio e a
   venda separados e o BV pela mesma conta.

---

### Casos de borda

- **Deploy cruzado**: toda chave nova é opcional nos dois sentidos. Tela nova com servidor velho mostra o orçamento
  sem desconto (nunca um número errado como certo) e não trava "Gerar Orçamento"; tela velha com servidor novo grava
  bruto = venda = total com desconto — a venda nasce certa e o BV sai encolhido pelo servidor.
- **Aba aberta com o bundle antigo**: o "Recalcular" antigo repopula campo a campo e descarta o desconto do orçamento
  salvo (recalcula o cheio); o Novo evento antigo grava cheio = venda = total com desconto. Nenhum número errado
  como certo; some só o registro do cheio no evento.
- **Gêmeo Jinja da criação de evento** (pausado, só pelo host do backend): lê o mesmo prefill e grava o mesmo número
  em cheio e venda — o total com desconto. A venda nasce certa e o cheio se perde; o orçamento com BV continua
  recusado ali (B8 da 305). Aceito, não se estende.
- **Desconto de 0, vazio ou ausente**, ou valor final igual ao cheio = sem desconto: a conta, a mensagem e o PDF são
  os de hoje.
- **Desconto de 100% ou mais, ou negativo** → recusado no campo; acima de 0 e abaixo de 100 qualquer Comercial
  digita, sem teto (como hoje digita a venda).
- **Digitar o valor com pausa no meio** ("2", depois "200"): a calculadora não pisca um % absurdo como resultado
  válido — o resultado é marcado como desatualizado até a resposta do valor final chegar.
- **Erro de validação**: o card de resultado não mostra os números da conta anterior como se valessem para a
  entrada nova.
- **PDF cheio**: com desconto, as linhas novas cabem na página e não sobem no rodapé (a página já aperta com a nota
  da data especial, 307).
- **Personalizado**: o desconto incide sobre o valor digitado (Session 5).
- **Orçamento com produto de tabela e duração extra**: o produto fica fixo; o desconto incide sobre o total.
- **Evento cancelado** (306/312): o vínculo a evento cancelado continua recusado; nada desta entrega reabre a venda
  do cancelado.

## Requisitos *(obrigatório)*

### Requisitos funcionais

**Conta (núcleo do orçamento)**

- **FR-001**: O cálculo do orçamento DEVE aceitar um desconto em percentual (maior que 0 e menor que 100) **ou** um
  valor final para uma das durações que o orçamento oferece; com o valor final, o percentual é achado pelo servidor
  sem arredondar, a duração digitada sai com o valor exato e as outras com o mesmo percentual, ao centavo.
- **FR-002**: O desconto DEVE incidir sobre o total de cada duração — apresentação, transporte, acréscimos, BV e nota
  dentro —, como último passo da conta, também na duração extra e no personalizado.
- **FR-003**: O resultado DEVE trazer, por duração, o valor antes do desconto e o valor final; o valor final continua
  na chave de total de hoje, para que todo leitor não atualizado mostre o que a cliente paga.
- **FR-004**: O PIX à vista DEVE ser `max(5%, desconto negociado exato)` sobre o valor antes do desconto, por
  duração, numa constante única; nunca soma com o negociado.
- **FR-005**: O resultado DEVE trazer, quando há BV, o BV que acompanha o valor final e o do PIX à vista, por
  duração, pela função única da 305 (BV cheio × valor ÷ cheio).
- **FR-006**: O acréscimo manual em R$ DEVE entrar uma vez por duração, inclusive acima de 4h; o acréscimo em %
  incide sobre a base; o BV em % incide sobre a base mais os acréscimos manuais, sem ver outro BV; o BV em reais
  entra uma vez no passo do BV; a nota vem depois de tudo isso.
- **FR-007**: A duração extra DEVE aplicar a régua de horas só à base (cachês, adicionais, transporte), com o produto
  de tabela fixo como na 309, e os passos de acréscimo, BV e nota por cima; o resultado DEVE trazer a base de 4h para
  que o Novo evento sugira qualquer outra duração pelo servidor.
- **FR-008**: O orçamento salvo DEVE guardar o desconto como foi digitado (o % ou o valor e a duração) e a marca de
  que foi cotado pela regra desta entrega; orçamento sem a marca continua sendo lido pela regra com que foi cotado,
  em todo lugar que o lê.
- **FR-009**: A conta compartilhada com o EducaManto DEVE descartar as chaves de desconto antes de calcular a
  contratação Manto; a regra de acréscimo e BV da FR-006 vale lá também.
- **FR-010**: Entrada inválida (percentual fora do intervalo, valor sem duração ou vice-versa, duração que o
  orçamento não oferece, valor ≤ 0 ou maior que o cheio) DEVE ser recusada com 400 apontando o campo.

**Proposta (mensagem e PDF)**

- **FR-011**: Sem desconto, a mensagem e o PDF DEVEM sair idênticos aos de hoje, palavra por palavra — salvo os
  valores dos orçamentos que a regra do acréscimo (Q7, FR-006) muda de preço (BV com outro acréscimo; duração extra
  com acréscimo em R$), cuja mensagem difere só nesses números.
- **FR-012**: Com desconto, cada duração DEVE mostrar "de R$ X por R$ Y" e "(desconto de N% aplicado)", com N
  arredondado a uma casa para baixo, com vírgula e sem ",0".
- **FR-013**: O bloco "À Vista (PIX)" DEVE, com negociado menor que 5%, mostrar o valor com 5% e a frase de hoje; com
  negociado de 5% ou mais, "o mesmo valor — o desconto de N% já está aplicado", sem valores repetidos.
- **FR-014**: A quebra "Valor da Apresentação" / "Logística e Transporte" DEVE sair do valor antes do desconto, e as
  duas linhas somar o "de".
- **FR-015**: Os três formatos de mensagem que existem (durações, produto com avulsos, só produto) DEVEM cobrir o
  "de/por" e o PIX; o PDF DEVE ler o PIX do resultado (com 5% sobre o total como leitura de orçamento antigo) e
  continuar cabendo na página.

**Telas**

- **FR-016**: A calculadora DEVE ter o bloco Desconto bilateral no card "Ajustes Finos", nascendo vazio: o campo de
  % e "ou fechar [duração] por R$", com as durações que o resultado oferece; quem foi digitado por último manda, e o
  outro é preenchido pela resposta do servidor.
- **FR-017**: O card Resultado DEVE mostrar o cheio riscado e o valor final quando há desconto, a linha do PIX à
  vista e, com BV, o BV a repassar (com o desconto e no PIX); fica marcado como desatualizado enquanto a conta não
  voltou ou voltou com erro.
- **FR-018**: A ajuda da "Duração extra" e o editor de acréscimos DEVEM dizer a conta de verdade (o acréscimo uma
  vez, o BV sobre tudo, a nota no fim; na calculadora comum, que o BV acompanha o desconto); a linha nova de BV, e a
  que troca de tipo para BV, nasce com o "%" marcado; a linha gravada reabre como foi gravada.
- **FR-019**: O orçamento gerado DEVE mostrar "de/por", o PIX por duração e o BV a repassar (fora da mensagem); o
  histórico DEVE mostrar o selo "−N%" na linha de orçamento com desconto.
- **FR-020**: O "Recalcular" DEVE restaurar o desconto como foi digitado e zerá-lo em orçamento sem as chaves.
- **FR-021**: O Novo evento DEVE nascer com o "valor antes do desconto" = o cheio da duração e o "valor de venda" =
  o total com desconto, também ao trocar de duração e no "Outra (h)" (pelo valor do servidor); o quadro do BV do
  orçamento DEVE mostrar o BV que acompanha e calar o aviso de "valor diferente" quando a venda é o total.
- **FR-022**: O selo "N% de desconto" do valor de venda DEVE usar o mesmo arredondamento da proposta (Session 6).

**Evento (o que a 305 grava)**

- **FR-023**: O BV que nasce no evento a partir do orçamento — na criação, no vínculo (273) e no alerta de BV
  pendente — DEVE usar o valor antes do desconto como denominador, e a dedução da duração pelo valor de venda DEVE
  continuar achando a duração com bruto ≠ venda.
- **FR-024**: O vínculo de orçamento a evento existente (273) DEVE gravar o cheio e a venda separados.
- **FR-025**: A comissão não muda de regra: % × (venda − BV), com o BV que acompanha.

### Entidades

Nenhuma entidade nova, nenhuma coluna nova. O desconto mora no orçamento salvo (o snapshot de entrada e o de
resultado); o evento já tem "valor antes do desconto" e "valor de venda".

### RBAC *(obrigatório — endpoints alterados)*

Nenhum gate muda. Calcular, salvar, histórico, PDF e e-mail do orçamento: Comercial e Superadmin; os demais 403
(Financeiro inclusive). Prefill do Novo evento e criação de evento: Comercial e Superadmin. Vínculo do orçamento
(273): quem gerencia a venda, com a guarda de autoria da 301. A calculadora do EducaManto (Revendedor EducaManto
inclusive) não recebe desconto: as chaves são descartadas na conta compartilhada. Verificação com um cenário que DEVE
falhar (Financeiro e Casting no cálculo com desconto → 403).

## Verificação (`verify_313.py`) *(obrigatório — Princípio VIII)*

Contra o `manto_local` (`DATABASE_URL` de `.local-db-url`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`), Google
dublado, login só pela API, escrita conferida por conexão separada, limpeza no fim. Escrito **antes** do núcleo, e a
primeira rodada (contra a `main`) guardada.

| # | Cenário | Prova |
|---|---|---|
| 0 | Gabarito de paridade | os orçamentos reais do espelho recalculados na `c074657b`, gravados antes de mexer |
| 1 | Paridade | sem as chaves novas, o resultado é o do gabarito; exceções listadas (BV + outro acréscimo; extra com R$) conferidas pela fórmula; mutação |
| 2 | Desconto em % | cheio, final × (1 − d), memória, snapshot; BV que acompanha; mutação trocando a razão por 1 |
| 3 | Desconto pelo valor | valor exato na duração digitada, % sem arredondar, outras pelo mesmo %; inválidos → 400 no campo |
| 4 | Base do desconto | fora de SP + acréscimo + nota: o desconto sobre o total; mutação antes do transporte / da nota |
| 5 | PIX vale o maior | sem desconto, 3%, 10%, 4,96%; mutação somando |
| 6 | Mensagem e PDF | frases de cada caso, "de/por", a quebra pelo cheio, sem "BV", três formatos (inclusive só produto); PDF de uma página |
| 7 | Orçamento antigo | histórico, PDF e e-mail de um registro antigo saem como antes |
| 8 | Acréscimo uma vez | extra de 8h com urgência; com nota; mutação multiplicando |
| 9 | BV sobre tudo | BV com "Outro"; com nota; na extra; BV em reais uma vez; os dois BVs não se veem |
| 10 | EducaManto | chaves de desconto descartadas; a regra da FR-006 vale na contratação Manto |
| 11 | Prefill | cheio e final separados, base de 4h e preços acima de 4h pelo servidor; orçamento antigo sem as chaves |
| 12 | Evento criado | bruto e venda gravados; BV gravado acompanha (também com o PIX digitado); comissão; desconto concedido |
| 13 | Orçamento antigo vira evento | BV e valores como hoje (a régua antiga e o denominador antigo) |
| 14 | Vínculo 273 | bruto ≠ venda gravados; BV pela mesma conta; evento cancelado continua recusado |
| 15 | RBAC | Financeiro, Casting e Revendedor → 403 no cálculo; Comercial e Superadmin 200 |
| 16 | Regressão | `verify_305 --regressao`, `verify_309`, `verify_307`, `verify_235` verdes |
| L | Limpeza | eventos e orçamentos do verify apagados; nenhuma chamada de rede real |

## Critérios de sucesso *(obrigatório)*

- **SC-001**: A comercial fecha um desconto no orçamento em uma ação (digitando o % ou o valor), sem conta por fora,
  e o evento nasce com o cheio e a venda separados — hoje 92 de 267 vendas têm o desconto digitado à mão.
- **SC-002**: Todo orçamento sem desconto dá o mesmo preço, a mesma mensagem e o mesmo PDF de antes, exceto as
  exceções da regra do acréscimo (Q7), listadas e conferidas uma a uma.
- **SC-003**: Nenhuma proposta promete mais desconto do que dá: o % mostrado nunca é maior que o aplicado, e o PIX
  nunca soma com o negociado.
- **SC-004**: O BV gravado num evento vindo de orçamento com desconto é o BV cheio na mesma proporção da venda, ao
  centavo, e a comissão a pagar sai dele.
- **SC-005**: Nenhum orçamento salvo antes muda de preço em lugar nenhum (tela, PDF, evento criado depois).

## Fora de escopo

- Dias adicionais (P2 e P3 do plano) — outra feature.
- Botão ou conta automática do PIX no evento (Q2 = C).
- Desconto no EducaManto (ele tem o dele).
- Mudar a regra de comissão ou de BV no evento depois de criado (B10 da 305 continua como está).
- Recalcular orçamentos salvos.
- O gêmeo Jinja da criação de evento (lê o mesmo prefill e ignora as chaves novas; pausado).

## Docs a atualizar

`docs/01` (contrato do cálculo, do prefill e do vínculo; a conta na ordem nova), `docs/02` (calculadora, orçamento
gerado, histórico, Novo evento), `docs/03` (entrada nova + índice), `docs/04` (a ordem da conta do orçamento: o
acréscimo uma vez, o BV sobre tudo, o desconto no fim, o PIX que vale o maior; o BV do evento pelo cheio), `docs/05`
(riscar o que quitar; registrar o que sobrar).

## Premissas

- Sem migration: desconto e marca de regra moram no orçamento salvo; o evento já tem os dois valores.
- Constante única do PIX: o fator de à vista que já existe no EducaManto (`AVISTA_FATOR`) ou uma ao lado — decisão
  do plan.
- Arredondamento: os totais seguem a regra de hoje para que a paridade seja byte a byte; os valores novos (desconto,
  PIX, BV) com a regra que o plan escolher e documentar.
- Números de 21/10 (produção, só leitura): 2.710 orçamentos (226 em outubro); desde junho, 267 vendas com valor, 92
  com desconto (63 na faixa de ~5% do PIX, 24 acima disso); das 91 vindas de orçamento, 89 têm o "antes do desconto"
  igual a um total do orçamento; 121 orçamentos acima de 4h, 11 com acréscimo em R$; 34 BVs em % e 2 em reais;
  nenhum acréscimo negativo; nenhum orçamento com produto de tabela; 12 eventos de orçamento desde a 305, nenhum com
  BV.
