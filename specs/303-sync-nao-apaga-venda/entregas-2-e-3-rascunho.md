# RASCUNHO das entregas 2 e 3 — a spec da 303 como estava antes da divisão (30/09/2026)

> **Este arquivo não é a spec da 303.** Em 30/09 o dono decidiu dividir o trabalho em três entregas,
> cada uma com o seu número, a sua esteira e o seu deploy. A spec da 303 (`spec.md`) ficou só com a
> trava do sync. Este é o texto completo de antes da divisão, **congelado**, para os dois
> `/speckit-specify` seguintes partirem dele em vez de recomeçar. Os números das features seguintes
> nascem no `/speckit-specify` de cada uma (constituição VI, Regra Zero).
>
> **Entrega 2 — o dinheiro do cancelamento** (tem migration: duas tabelas): a metade "Cancelar e
> devolver o dinheiro" da História 3; Histórias 4 e 7; FR-013 a FR-021, FR-025 (textos de
> cancelamento e estorno), FR-026 a FR-032 e FR-037; o backend da página de Cancelamentos lendo o
> resumo do cancelado; cenários 12, 16, 18 a 23c, 26 a 36 e a parte de dinheiro do 40.
> Pesquisa: `pesquisa/frente-cancelar-dados.md`, `frente-comissao.md`, `frente-dre.md`,
> `frente-comercial.md`, `90-…`, `91-…` e `00-integracao.md`.
>
> **Entrega 3 — sinalizar e filtrar cancelados** (sem migration): História 8; o resto da FR-033,
> FR-034, FR-035, FR-036 e FR-038; cenários 37 a 39 e a parte de telas do 40.
> Pesquisa: `pesquisa/frente-agenda-telas.md` e `frente-comercial.md`.
>
> **Decisões do dono tomadas depois deste texto, que valem para as entregas 2 e 3:**
>
> - **Correção depois do cancelamento (30/09)**: o Superadmin pode acrescentar comprovante esquecido
>   e corrigir o BV negociado num evento já cancelado; o retido e a comissão são recalculados pelo
>   mesmo caminho da alteração de devolução (FR-015a). Entra na entrega 2.
> - **Até a entrega 2 subir (30/09)**: o evento marcado "Sumiu do Google" só oferece "Devolver ao
>   Google Agenda" — não pode ser cancelado nem excluído. A entrega 2 é quem libera o "Cancelar e
>   devolver o dinheiro" do evento marcado, sem tentar removê-lo do Google.
>
> **Correções que a pesquisa do plano fez neste texto** (já valem; a spec de cada entrega nasce com
> elas): a comissão EducaManto a pagar de evento cancelado fica no ciclo em que estava; a tela de
> Comissões passa a mostrar "No banco"; "meta do Dashboard Comercial" não existe — a meta é o total
> vendido por vendedor, e os rankings são o Top Vendedores da DRE e o `/admin/desempenho`; a
> "Performance da Home" não tem venda — só deixa de contar cargo e cachê de cancelado; o estado da
> devolução usa os códigos do modelo (`nao_pago`, `no_banco`, `pago`); os estornos órfãos já
> pendentes (o do 1244) não são tocados.

---

# Feature 303 — Evento com venda que some do Google fica no sistema, a equipe vê, e o Superadmin decide: volta ao Google ou cancela devolvendo o dinheiro

**Branch**: `303-sync-nao-apaga-venda` (da `main`) · **Created**: 2026-09-29 · **Status**: Rascunho ·
**Migration**: provável aditiva (onde mora a marca — decisão do plan; reusar os campos do pedido de
exclusão da 224 quebra, ver Entidades) · **Nível**: 1 (feature — agenda, notificações, financeiro,
comercial e portal) — constituição, Princípio VI

**Input**: plano do backlog de setembro (`docs/PLANO_BACKLOG_SETEMBRO.md`), decisões D1, D14, D17 e
D18, e as respostas do dono de 29/09. Absorve a correção 224g do plano (estorno no ciclo certo e
BV de evento cancelado fora da Planilha): é o mesmo dinheiro do cancelamento, na mesma função.

## O pedido, nas palavras do dono *(obrigatório)*

Em 22/09, sobre cancelamento: **"passa pelo sistema de verdade"** — evento com venda que some do
Google vira pedido para o dono decidir, em vez de ser apagado (D1). Sobre a comissão: **"sim,
sobre o valor retido"** (D14). Em 29/09 o dono puxou a trava para a onda 1 (D17), escolheu que o
evento **fica na agenda, marcado, e segue contando na venda** (D18), e acrescentou:

> "Acho que não deve ser apenas um aviso no sino. Deve ser algo mais marcante."
>
> "Existe o ponto também de muitas vezes precisarmos devolver o dinheiro. Isso também precisa estar
> nessa spec."
>
> "Normalmente quando um evento muda de data, enviamos mensagens no particular do WhatsApp
> perguntando se a pessoa tem disponibilidade de trocar. Acho que vale o aviso no portal de evento
> em confirmação — entre em contato com a produção."

O aviso marcante escolhido: **faixa no topo de todas as telas + sino**, para **Superadmin e
Comercial**; a decisão é só do Superadmin.

O sintoma, como a equipe vê: um evento vendido desaparece do sistema sem ninguém ter mandado apagar,
e com ele somem os comprovantes, o contrato e a escala. Em produção (29/09, só leitura):

- 5 eventos apagados por sumiço no Google desde 01/08 (2 em agosto, 3 em setembro).
- Em 17/09 foi o `(R&I) GABBY + PANDY + GATUNO` (1244), com venda e comissão: movido no Google de
  13 para 19/09 e depois tirado de lá. A comercial recriou o evento do zero em 24/09 (1336, 07/11)
  — o que estava preso ao 1244 não voltou. O estorno da comissão nasceu com a data da venda de
  agosto (21/08), num mês já fechado.
- 56 eventos futuros têm R$ 172.447,24 em comprovantes anexados e estão expostos à mesma regra.
- "Solicitar exclusão" e "Cancelar" (feature 224) têm **zero** uso: a equipe cancela apagando no
  Google. O cancelamento da 224 já registra a devolução à cliente — ninguém chegou a vê-lo.

Há um segundo caminho de perda, menos visível: evento que **muda de mês** no Google. Em cada mês, a
limpeza apaga o evento gravado naquele mês (pela data do banco) que não está na lista do Google; ele
só escapa se o sync do mês de destino o encontrar antes, pelo id, e gravar a data nova.

- **Adiado para um mês posterior**: o mês antigo é limpo primeiro e apaga o evento; o mês novo o
  importa como evento novo, sem venda, comprovante nem escala.
- **Antecipado para um mês já passado**: o ciclo automático nunca busca esse mês — o evento é
  apagado e não volta. No "Limpar eventos fantasma", só escapa se o mês de destino já tiver outro
  evento no banco.

(Verificado contra o código em 29/09: `app/calendar/sync.py:51-79`, `app/calendar/routes.py:364-365,
2247, 2294-2295`, `app/api/admin_config_write.py:93-99`.)

## Clarifications

### Session 2026-09-29

- Q: Qual é a base da comissão do vendedor quando o evento é cancelado com parte do dinheiro
  retida? → A: **Proporcional** — comissão cheia × (retido ÷ venda). Nunca passa da comissão
  cheia, e vale igual para o EducaManto (a comissão cheia de cada tipo já traz a sua regra).
- Q: O que acontece com o BV de quem indicou quando o evento é cancelado com parte do dinheiro
  retida? → A: **Caso a caso, depende da negociação** — o Superadmin informa no cancelamento quanto
  do BV o parceiro recebe (de zero ao BV inteiro); a Planilha passa a mostrar esse valor.
- Q: No cancelamento, o valor da devolução à cliente já deve vir preenchido? → A: **Vem vazio** —
  o Superadmin escolhe "Tudo" (preenche o total pago), "Parte" (digita o valor) ou "Nada"; não dá
  para cancelar sem escolher. O total pago fica visível ao lado.
- Q: Se o valor da devolução mudar depois do cancelamento, a comissão e o retido acompanham? → A:
  **Acompanham** — o Superadmin altera a devolução na tela do evento cancelado, retido e comissão
  são recalculados na hora, e a comissão já paga é ajustada no próximo repasse (para mais ou para
  menos). Em Gastos Extras o valor da devolução fica só para leitura.
- Q: Quando o sync decide entre apagar e manter um SHOW que sumiu do Google, a vaga "Técnico de Som"
  que o sistema preenche sozinho conta como "alguém escalado"? → A: **Não conta no sync** — só conta
  quem a equipe escalou (inclusive a vaga "Técnico de Som (Presença)" quando designada, ou outro
  técnico no lugar do padrão). O botão Excluir da 224 continua como está.

### Session 2026-09-29 (depois do clarify — pedido do dono sobre relatórios)

O dono pediu, depois das cinco perguntas: *"Precisamos incluir no plano essa questão do evento
cancelado e com 600 devolvido aparecendo como −600, sendo que ele é +400. E acredito que possa ter
algo especial para sinalizar e/ou filtrar eventos cancelados."* Um mapeamento contra o código
(29/09) confirmou a causa e levou a quatro perguntas:

- Q: Em que mês o valor retido de um cancelamento entra na DRE? → A: **No mês do cancelamento**, em
  Realizado e Total — é quando o dinheiro já está no caixa, e é onde hoje aparece o −600.
- Q: Como sinalizar e filtrar os eventos cancelados nas telas? → A: **Card + botão "Mostrar
  cancelados"** — DRE e Dashboard Comercial ganham o card "Cancelamentos do período"; agenda, lista
  de vendas e tabela da DRE ganham o botão, desligado por padrão, com o cancelado riscado e o selo
  "Cancelado"; busca e fichas de cliente e talento mostram o selo sempre.
- Q: O valor retido de um evento que era com nota paga imposto na DRE? → A: **Depende da
  negociação, dos prazos e do resto** — o Superadmin informa no cancelamento o imposto sobre o
  retido (como o BV negociado), com 16% do retido exibido ao lado só como referência.
- Q: A venda cancelada e o valor retido contam nos números do comercial? → A: **O retido conta como
  venda** do vendedor no mês do cancelamento — no total vendido, no ranking e na meta; a venda
  original sai do mês dela.

## Cenários e Verificação *(obrigatório)*

### História 1 — Evento com dinheiro que some do Google continua no sistema (Prioridade: P1)

Alguém apaga no Google Agenda um evento que tem venda, comprovante, contrato, gente escalada ou que
faz parte de um grupo comercial. No próximo ciclo do sync, o evento **não** é apagado: continua na
agenda, com tudo o que estava preso a ele, e ganha a marca "Sumiu do Google Agenda" com a data em
que o sistema percebeu. Até a decisão, ele segue valendo como antes em venda, comissão, Planilha e
DRE.

**Por que esta prioridade**: é a única perda de dinheiro em curso no backlog; tudo o mais depende de
o registro existir.

**Verificação**: cenários 1, 3, 4, 5, 6 e 7 do `verify_303.py`.

**Cenários de aceite**:

1. **Dado** um evento com valor de venda que não está mais no Google, **Quando** o sync roda,
   **Então** o evento continua no banco com venda, comprovantes, contrato e escala intactos, e
   está marcado "Sumiu do Google Agenda" com a data de hoje.
2. **Dado** um evento sem venda mas com um comprovante de pagamento, um contrato, uma pessoa
   escalada pela equipe, ou que é líder ou satélite de um grupo comercial, **Quando** some do Google
   e o sync roda, **Então** o evento continua no banco, marcado.
3. **Dado** um evento **vazio** (sem venda, comprovante, contrato, escalado nem grupo) que sumiu
   do Google — inclusive um SHOW cuja única pessoa é o técnico de som que o sistema pôs sozinho —,
   **Quando** o sync roda, **Então** ele é apagado como hoje.
4. **Dado** um evento marcado, **Quando** alguém da equipe o abre, **Então** vê a marca e o dia em
   que o sistema percebeu o sumiço; a marca não se confunde com uma "exclusão solicitada" por uma
   pessoa.

---

### História 2 — A equipe não tem como não ver (Prioridade: P1)

No mesmo ciclo em que o sistema percebe o sumiço, Superadmin e Comercial passam a ver, **em todas
as telas do sistema interno**, uma faixa fixa no topo, em destaque de alerta: quantos eventos com
venda sumiram do Google e o acesso a cada um (título e data). A faixa não se dispensa: some sozinha
quando não houver mais evento marcado. Junto, cada Superadmin e cada Comercial recebe **um** aviso
no sino com o título, a data e o que está preso ao evento (venda, quanto já foi recebido, quantas
pessoas escaladas). O Comercial vê a faixa, o aviso e a marca, e pode contar ao Superadmin por que
o evento sumiu; os botões de decisão são só do Superadmin.

**Por que esta prioridade**: um aviso no sino se perde entre os outros; o evento marcado precisa de
decisão rápida porque o elenco está esperando (História 6).

**Verificação**: cenários 2 e 17 do `verify_303.py` e a conferência de tela.

**Cenários de aceite**:

1. **Dado** um evento que acabou de ser marcado, **Quando** um Superadmin ou um Comercial abre
   qualquer tela do sistema interno, **Então** vê a faixa com "1 evento sumiu do Google Agenda" e o
   link para ele.
2. **Dado** o mesmo evento, **Quando** o ciclo do sync termina, **Então** cada Superadmin e cada
   Comercial tem exatamente uma notificação nova para ele no sino.
3. **Dado** um evento já marcado, **Quando** o sync roda de novo (e de novo), **Então** nenhuma
   notificação nova é criada e a faixa continua igual.
4. **Dado** que o último evento marcado foi resolvido, **Quando** qualquer tela é aberta, **Então**
   a faixa não aparece.
5. **Dado** um usuário de outro papel (Figurino, Casting, Financeiro...), **Quando** abre o sistema,
   **Então** não vê a faixa.

---

### História 3 — O Superadmin decide: volta ao Google, ou cancela e devolve o dinheiro (Prioridade: P1)

Na tela do evento marcado, o Superadmin vê o que está em jogo — venda, quanto a cliente já pagou
(soma dos comprovantes), comissão, BV, quem está escalado — e escolhe:

- **Devolver ao Google Agenda**: o evento era para existir. O sistema o recria no Google com os
  dados atuais e tira a marca; o evento volta a ser sincronizado normalmente.
- **Cancelar e devolver o dinheiro**: o evento não vai acontecer. O Superadmin informa o motivo e
  quanto devolve à cliente — escolhendo "Tudo" (o total que ela pagou, que fica visível ao lado),
  "Parte" ou "Nada"; o valor não vem preenchido — com nome e PIX de quem recebe; se o evento tem BV, diz também quanto dele o parceiro recebe, conforme a
  negociação. A devolução vira um pagamento a fazer na Planilha de Pagamentos, e o evento
  cancelado passa a mostrar a devolução até ela ser paga: quanto, para quem, em que estado (a
  pagar, no banco, paga) e quanto ficou retido. Como o evento já não está no Google, o sistema não
  tenta removê-lo de lá nem mostra aviso de falha por isso.

**Por que esta prioridade**: sem as duas saídas, o evento fica preso na marca; e cancelar sem
devolver o dinheiro é o motivo de a equipe hoje apagar no Google e resolver por fora.

**Verificação**: cenários 10, 11, 12 e 18 do `verify_303.py`.

**Cenários de aceite**:

1. **Dado** um evento marcado, **Quando** o Superadmin escolhe "Devolver ao Google Agenda",
   **Então** o evento passa a existir no Google com título, data, horário, local e descrição atuais,
   a marca some, e o histórico registra quem devolveu e quando.
2. **Dado** um evento marcado em que a cliente pagou R$ 1.000, **Quando** o Superadmin cancela e
   devolve R$ 600 para a cliente, **Então** o evento fica cancelado, a Planilha de Pagamentos ganha
   um pagamento a fazer de R$ 600 para a cliente, e o evento mostra "Devolução de R$ 600,00 — a
   pagar · retido R$ 400,00".
3. **Dado** o mesmo cancelamento, **Quando** o financeiro paga a devolução na Planilha, **Então** o
   evento passa a mostrar a devolução como paga.
4. **Dado** um evento marcado, **Quando** o Superadmin cancela sem devolver nada, **Então** o evento
   fica cancelado sem pagamento a fazer, e mostra "retido R$ <tudo o que foi pago>".
5. **Dado** um usuário que não é Superadmin, **Quando** tenta devolver ao Google ou cancelar,
   **Então** é recusado.

---

### História 4 — A comissão acompanha o dinheiro que ficou (Prioridade: P1)

Quando um evento é cancelado, a comissão do vendedor deixa de ser estornada por inteiro: passa a
ser a comissão cheia na proporção do que ficou **retido** (o que a cliente pagou menos o que foi
devolvido) sobre a venda. Exemplo do dono: venda de R$ 2.000 a 5% (comissão cheia R$ 100), sinal de
R$ 1.000, R$ 600 devolvidos → retido R$ 400, comissão 100 × 400/2.000 = R$ 20; se os R$ 100 já
tinham sido pagos, o próximo repasse do vendedor desconta R$ 80. Com BV de R$ 200 na mesma venda, a
comissão cheia é R$ 90 e a do retido, R$ 18. O desconto cai **no próximo repasse** — não no mês da
venda, que costuma já estar pago. O BV de quem indicou é negociado caso a caso: no cancelamento, o
Superadmin diz quanto dele o parceiro recebe, e a Planilha mostra esse valor, não o BV original.

**Por que esta prioridade**: sem isto, o vendedor perde a comissão do dinheiro que a Manto reteve,
e o estorno de hoje herda a data e o ciclo da comissão original: entra na Planilha do mês seguinte a
esse ciclo, que costuma já estar pago, soma na linha do vendedor e a reabre como "não pago" (ou a
faz sumir, se zerar). Se alguém marcar a linha como paga de novo, o estorno conta como liquidado sem
ter saído de repasse nenhum. Na tela de Comissões ele aparece no mês da venda (somado ao pago,
zerando o saldo) e de novo no mês corrente, e o "Pagar Mês" de qualquer mês o liquida. E comissão que está **no banco** na hora do cancelamento hoje fica intacta e
é paga cheia.

**Verificação**: cenários 19 a 23 do `verify_303.py` e o verify cruzado de Planilha, tela de
Comissões e DRE.

**Cenários de aceite**:

1. **Dado** a venda do exemplo com comissão de R$ 100 ainda **a pagar**, **Quando** o evento é
   cancelado com R$ 600 devolvidos de R$ 1.000 pagos, **Então** a comissão a pagar passa a R$ 20,00.
2. **Dado** a mesma venda com a comissão de R$ 100 já **paga** (ou **no banco**), **Quando** o
   evento é cancelado da mesma forma, **Então** a comissão paga continua como estava e o próximo
   repasse do vendedor desconta R$ 80,00.
3. **Dado** um cancelamento em que tudo o que a cliente pagou foi devolvido, **Quando** a comissão
   já tinha sido paga, **Então** o próximo repasse desconta a comissão inteira; e **quando** ainda
   não tinha sido paga, ela é cancelada.
4. **Dado** um evento com BV de R$ 200 cancelado com "parceiro recebe R$ 50", **Quando** o
   financeiro abre a Planilha de Pagamentos do mês do evento, **Então** o BV aparece com R$ 50,00 —
   na tela nova e na antiga; com "parceiro recebe R$ 0", o BV não aparece.
5. **Dado** qualquer um desses cancelamentos, **Quando** se compara, por evento, a Planilha e a tela
   de Comissões (reabertas depois do cancelamento), **Então** as duas mostram o mesmo valor de
   comissão e de desconto.

---

### História 5 — Evento que só mudou de data não vira sumiço (Prioridade: P2)

A comercial adia um evento no Google, inclusive para outro mês. O sistema não o trata como sumiço:
não apaga, não marca, não avisa. O evento chega à data nova **no mesmo registro**, com venda,
comprovantes e escala. Se um evento marcado voltar a aparecer no Google (o mesmo evento, não uma
cópia), a marca some sozinha e o histórico registra por quê.

**Por que esta prioridade**: adiamento é rotina; sem isto, a faixa acenderia a cada adiamento e o
adiamento para outro mês continuaria destruindo o evento.

**Verificação**: cenários 8 e 9 do `verify_303.py`.

**Cenários de aceite**:

1. **Dado** um evento de setembro que foi movido no Google para novembro, **Quando** o sync roda,
   **Então** o evento continua no banco, com a data de novembro, a mesma venda e os mesmos
   comprovantes, sem marca, sem faixa e sem notificação.
2. **Dado** um evento marcado, **Quando** o sync volta a encontrá-lo no Google, **Então** a marca
   some, a faixa deixa de contá-lo, e o histórico do evento diz que ele reapareceu.

---

### História 6 — O elenco sabe que o evento está em confirmação (Prioridade: P2)

Quem está escalado continua vendo o evento marcado no portal do artista, com o aviso **"Evento em
confirmação — entre em contato com a produção"**. É o complemento da mensagem que a produção já
manda no WhatsApp: o artista não perde um evento que existe, e não vai às cegas a um que pode não
acontecer. Quando o Superadmin devolve ao Google (ou o evento reaparece), o aviso some; quando
cancela, o evento sai do portal como qualquer cancelado.

**Por que esta prioridade**: o caso 1246 (Merida + Cavalo) mostrou o custo de o elenco ir a um
evento que mudou — multa mais cachê.

**Verificação**: cenário 24 do `verify_303.py` e a conferência do portal em 375×812.

**Cenários de aceite**:

1. **Dado** um evento marcado com um artista escalado, **Quando** o artista abre o portal,
   **Então** vê o evento com o aviso "Evento em confirmação — entre em contato com a produção".
2. **Dado** o mesmo evento devolvido ao Google, **Quando** o artista abre o portal, **Então** vê o
   evento sem o aviso.
3. **Dado** um artista que não está escalado no evento, **Quando** abre o portal, **Então** não vê
   nada do evento.

---

### História 7 — O cancelado aparece na DRE pelo que a Manto ficou: +400, não −600 (Prioridade: P1)

Hoje a DRE tira o evento cancelado inteiro, de todos os meses, e soma a devolução como gasto extra
no mês do cancelamento — a devolução nasce como gasto aprovado, e a DRE soma todo gasto aprovado
sem olhar de onde ele vem. No exemplo (venda R$ 2.000, BV R$ 200, pago R$ 1.000, devolvidos R$ 600),
a DRE de setembro mostra **−R$ 600**, e os R$ 400 que ficaram com a Manto não aparecem em mês
nenhum. As duas DREs (a tela nova e a antiga, que continua no ar) fazem igual.

Depois desta feature, o cancelado entra na DRE **no mês do cancelamento**, em Realizado e Total:
o retido (pago − devolvido) soma na receita, numa linha própria "Retido de cancelamentos"; o BV
negociado soma no custo; a comissão do retido soma nas comissões; o imposto sobre o retido é o que
o Superadmin informou no cancelamento; e a devolução deixa de ser gasto na DRE (continua sendo
saída na Planilha de Pagamentos). No exemplo, sem imposto: +400 − 40 (BV negociado) − 18 (comissão)
= **+R$ 342**. O mês do evento (novembro) continua sem nada dele — o cancelado conta uma vez só.

**Por que esta prioridade**: é o número que o dono lê para saber se o mês deu lucro; um
cancelamento que deixou dinheiro na Manto aparece hoje como prejuízo de quase mil reais de
diferença.

**Verificação**: cenários 26 a 36 do `verify_303.py`.

**Cenários de aceite**:

1. **Dado** o exemplo cancelado em setembro, sem imposto informado, **Quando** o financeiro abre a
   DRE de setembro (tela nova e antiga), **Então** vê a linha "Retido de cancelamentos" com R$ 400,
   o custo com +R$ 40, as comissões com +R$ 18, os gastos extras sem os R$ 600 e o resultado do
   evento em +R$ 342, em Realizado e Total, e nada no Projetado.
2. **Dado** o mesmo evento, **Quando** abre a DRE de novembro, **Então** o evento não aparece.
3. **Dado** o mesmo cancelamento com imposto informado de R$ 64, **Quando** abre a DRE de setembro,
   **Então** os impostos têm +R$ 64 e o resultado do evento é +R$ 278.
4. **Dado** a devolução alterada de R$ 600 para R$ 800 depois do cancelamento, **Quando** abre a
   DRE de setembro, **Então** o retido é R$ 200, com a comissão e o resultado recalculados, e nenhuma
   devolução aparece em gastos extras.
5. **Dado** uma multa paga ao elenco, lançada como gasto extra ligado ao evento cancelado, **Quando**
   abre a DRE, **Então** a multa continua em gastos extras — só a devolução à cliente sai.
6. **Dado** qualquer mês sem cancelamento, **Quando** se compara a DRE antes e depois desta feature,
   **Então** os números são idênticos, centavo a centavo.

---

### História 8 — Cancelado sinalizado em todo lugar e escondido só quando se pede (Prioridade: P2)

O cancelado ganha um sinal único — o selo "Cancelado", com o evento riscado — e um jeito único de
aparecer ou não:

- **DRE e Dashboard Comercial**: um card "Cancelamentos do período" (quantidade, pago, devolvido e
  quanto ainda falta devolver, retido, comissão do retido, BV, imposto e efeito no resultado), com
  link para cada evento, como o card da Loja Virtual.
- **Agenda (Mês, Lista e Dia), lista de vendas e tabela "Eventos no período" da DRE**: botão
  "Mostrar cancelados", desligado por padrão; ligado, o cancelado aparece riscado e com o selo.
- **Busca, ficha da cliente e ficha do talento**: o cancelado aparece sempre, com o selo.
- **Página de Cancelamentos**: passa a mostrar pago, cada devolução com o estado, retido, comissão,
  BV e imposto, com filtro por mês do cancelamento e por estado da devolução; o Financeiro passa a
  lê-la.
- **Tela do evento cancelado**: a grade "Resultado" vira "Resultado do cancelamento" (pago,
  devolvido, retido, comissão do retido, BV, imposto) — hoje ela mostra "lucro R$ 1.200" e o aviso
  "R$ 1.000,00 em aberto".

E o retido **conta como venda** do vendedor no mês do cancelamento (total vendido, ranking, meta),
no lugar da venda original, que sai do mês dela.

**Por que esta prioridade**: sem sinal, o cancelado ou some (e ninguém acha o dinheiro retido) ou
aparece como evento normal (a visão Dia e a busca mostram hoje sem marca, e dá para ligar ensaio ou
tag NFC a ele).

**Verificação**: cenários 37 a 40 do `verify_303.py` e a conferência de tela.

**Cenários de aceite**:

1. **Dado** um evento cancelado em setembro, **Quando** a equipe abre a agenda de setembro sem
   mexer em nada, **Então** ele não aparece em Mês, Lista nem Dia; **Quando** liga "Mostrar
   cancelados", **Então** ele aparece riscado, com o selo, e sem a cor ser o único sinal.
2. **Dado** o mesmo evento, **Quando** alguém o procura na busca, **Então** ele aparece sempre, com
   o selo; **Quando** alguém tenta ligar a ele um ensaio, uma tag NFC ou um grupo, **Então** é
   recusado, com o motivo.
3. **Dado** o exemplo, **Quando** o Comercial abre o Dashboard de setembro, **Então** o total
   vendido do vendedor tem +R$ 400 (o retido) e o de novembro não tem os R$ 2.000; o card
   "Cancelamentos do período" mostra 1 cancelado, pago 1.000, devolvido 600, retido 400.
4. **Dado** o exemplo, **Quando** alguém abre a tela do evento cancelado, **Então** vê "Resultado do
   cancelamento" com 1.000 / 600 / 400 / 18 / 40, sem "em aberto".
5. **Dado** um evento que estava marcado "Sumiu do Google" e foi cancelado, **Quando** aparece em
   qualquer lista, **Então** mostra só "Cancelado" (o cancelado vence a marca).

---

### Casos de borda

- **Recriado à mão no Google (id novo)** — o caso do 1244: o sistema importa o evento novo como
  hoje e o antigo continua marcado. Não há fusão automática. O caminho certo é devolver ao Google o
  **antigo** (é ele que tem comprovantes, contrato e escala) e apagar o novo no Google; cancelar o
  antigo geraria comissão em dobro e cobraria de novo quem já pagou. Se o novo já tiver venda, ele
  também fica marcado e é cancelado com "Nada" (pago zero, comissão zero). A tela do evento marcado
  diz isso ao Superadmin.
- **Evento marcado editado no sistema**: hoje só título, data, horário, local e descrição escrevem
  no Google (aba Comercial, escala e clientes não). Enquanto marcado, a edição salva no sistema e
  **não** é escrita no Google — a devolução recria o evento com os dados atuais —, sem aviso de falha
  e sem desfazer troca de tipo.
- **Botão "Sincronizar" do evento marcado**: hoje ele reconstrói o evento a partir do Google; com o
  evento apagado lá, o título viraria "Sem título", as datas se perderiam e a escala seria
  reconciliada pelo título, com e-mail de remoção a gente de verdade. Enquanto marcado, ele não altera
  o evento e diz que o evento não existe no Google. O link "Editar no Google Agenda" também não
  aparece.
- **Evento no passado** que some do Google (percebido pelo "Limpar eventos fantasma" de
  `/admin/sync`): mesma regra — tem dinheiro, fica e avisa; devolver ao Google vale mesmo no passado.
  Antes do deploy, o plan conta quantos eventos passados com dinheiro já não estão no Google: se
  forem muitos, a primeira rodada acenderia a faixa de uma vez e a spec ganha a regra de "primeira
  rodada sem sino".
- **Satélite de grupo comercial cancelado**: sai sem devolução e sem mexer em comissão ou BV — o
  dinheiro do grupo se resolve no líder. Isso evita devolver em dobro ("Tudo" no satélite e depois
  no líder) e a divisão por zero da comissão proporcional (o satélite tem venda zerada).
- **Evento cancelado** ausente do Google: continua ignorado, como hoje (foi tirado de lá de
  propósito).
- **Venda virtual**: segue a regra própria de hoje (nunca apagada, divergência registrada) — ver
  Fora de escopo.
- **Ensaio** (evento-filho) que some do Google: não tem venda; segue a regra de evento vazio. O
  pai marcado não arrasta o ensaio.
- **Google fora do ar ou recusando a consulta** no meio do ciclo: o evento cuja ausência não foi
  confirmada não é apagado nem marcado naquele ciclo — na dúvida, o evento fica.
- **Lista do mês incompleta**: a busca do mês não pagina (uma chamada, até 2.500 itens); a
  confirmação individual da FR-002 é o que impede apagar evento vivo que ficou fora da página.
- **Evento recorrente editado no Google**: cada instância pode ganhar id novo; o sistema não trata
  série (fica como risco no plan).
- **Desconto maior que o repasse seguinte do vendedor**: o item negativo aparece na Planilha e o
  financeiro resolve, como a Planilha já faz hoje com saldo negativo.
- **Devolução "no banco"** conta como paga para a FR-015a (só pode aumentar); o "desfazer pago" da
  Planilha continua existindo.
- **Convite pendente de evento marcado**: aparece no portal com o mesmo aviso, e os botões de
  aceitar/recusar continuam.
- **O mesmo evento some, reaparece e some de novo**: cada sumiço é um aviso novo.
- **Superadmin devolve ao Google, mas o Google recusa**: a marca continua e a tela diz que não deu.
- **Líder de grupo comercial marcado**: o cancelamento continua exigindo desagrupar os satélites
  antes (regra da 224); a tela diz isso em vez de falhar calada.
- **Devolução maior que o recebido**: recusada — o retido nunca fica negativo.
- **Cancelamento de evento não marcado** (pelo botão da 224): ganha as mesmas regras de devolução e
  comissão desta feature — a regra do dinheiro é uma só.
- **Elenco que foi ao local de um evento cancelado em cima da hora**: multa e cachê continuam como
  gasto extra à parte, como no caso 1246 (fora de escopo).

## Requisitos *(obrigatório)*

### Requisitos funcionais

**Trava do sync**

- **FR-001**: O sync NÃO DEVE apagar evento que some do Google Agenda quando o evento tem valor de
  venda, algum comprovante de pagamento, contrato, alguém escalado pela equipe, ou pertence a um
  grupo comercial (líder ou satélite). A vaga "Técnico de Som" que o sistema preenche sozinho com o
  técnico padrão em todo SHOW NÃO conta como escalado; contam a vaga "Técnico de Som (Presença)"
  quando alguém é designado e qualquer técnico posto no lugar do padrão.
- **FR-002**: Antes de tratar um evento como sumido, o sistema DEVE confirmar a ausência consultando
  aquele evento no Google. Evento que existe no Google com outra data — em qualquer mês — é mudança
  de data: não é apagado, não é marcado, não gera aviso, e chega à data nova no mesmo registro,
  inclusive quando o mês de destino já passou ou está fora do horizonte do ciclo. A regra vale para
  todo evento, vazio ou não, exceto venda virtual e evento cancelado, que o sync não atualiza (ver
  Casos de borda).
- **FR-003**: A ausência só está confirmada quando o Google responde que o evento não existe ou que
  está apagado. Qualquer outra resposta é inconclusiva — erro, tempo esgotado, falta de credencial,
  falha ao renovar o acesso — e o sistema NÃO DEVE apagar nem marcar aquele evento naquele ciclo.
- **FR-004**: O evento preservado DEVE ficar marcado "Sumiu do Google Agenda", com a data em que o
  sistema percebeu, visível na tela do evento e nas visões da agenda interna, e distinguível de uma
  exclusão solicitada por uma pessoa.
- **FR-005**: Enquanto marcado, o evento DEVE continuar valendo como antes em venda, comissão,
  Planilha de Pagamentos e DRE.
- **FR-006**: A marca DEVE sumir sozinha quando o sync volta a encontrar o mesmo evento no Google. A
  conferência dos eventos marcados é feita pelo próprio evento a cada ciclo, não pela lista do mês
  (um marcado de setembro deixa de ser listado depois de 01/10).
- **FR-007**: Evento vazio que some do Google DEVE continuar sendo apagado como hoje, depois da
  confirmação da FR-002.
- **FR-008**: Enquanto o evento estiver marcado, o sistema NÃO DEVE escrever edições no Google: a
  edição salva no sistema sem aviso de falha e sem desfazer troca de tipo, e a marca continua. O
  botão "Sincronizar" do evento NÃO DEVE alterar o evento nem a escala enquanto ele estiver marcado.

**Aviso**

- **FR-009**: Enquanto existir ao menos um evento marcado, Superadmin e Comercial DEVEM ver, em
  todas as telas do sistema interno, uma faixa fixa no topo, em destaque de alerta, com a quantidade
  de eventos marcados e o acesso a cada um (título e data). A faixa não pode ser dispensada e some
  sozinha quando não houver mais evento marcado. Outros papéis não a veem.
- **FR-010**: No ciclo em que marca o evento, o sistema DEVE criar uma notificação no sino para cada
  Superadmin e cada Comercial, com título, data, valor de venda, total recebido, número de pessoas
  escaladas e o link para o evento — uma única vez por sumiço, nunca repetida a cada ciclo.

**Decisão**

- **FR-011**: O Superadmin DEVE ver, na tela do evento marcado, o que está em jogo antes de decidir:
  venda, total pago pela cliente, comissão, BV e escalados.
- **FR-012**: O Superadmin DEVE poder devolver o evento marcado ao Google Agenda: o sistema recria o
  evento no Google com título, data, horário, local e descrição atuais, passa a sincronizá-lo pelo
  evento novo e retira a marca. Se o Google recusar, a marca continua e a tela diz que não deu.
- **FR-013**: O Superadmin DEVE poder cancelar o evento marcado informando o motivo e a devolução à
  cliente, sem que o sistema tente removê-lo do Google e sem aviso de falha por isso. A devolução
  NÃO vem preenchida: o Superadmin escolhe "Tudo" (preenche o total pago, exibido ao lado), "Parte"
  (digita um valor maior que zero e menor que o total pago) ou "Nada"; o cancelamento é recusado sem
  essa escolha. Com "Tudo" ou "Parte", nome e PIX de quem recebe são obrigatórios. Se o evento era
  "com nota", o Superadmin DEVE informar também o imposto sobre o retido, em reais (de zero para
  cima; depende da negociação e dos prazos), com 16% do retido exibido ao lado só como referência,
  sem vir preenchido; o valor é alterável depois junto com a devolução (FR-015a).
- **FR-014**: A devolução DEVE entrar na Planilha de Pagamentos como pagamento a fazer à cliente, e o
  evento cancelado DEVE mostrar valor devolvido, quem recebe, estado do pagamento (a pagar, no
  banco, paga) e valor retido (pago − devolvido).
- **FR-015**: Antes de confirmar o cancelamento, a tela DEVE mostrar o efeito na comissão: valor
  retido, comissão resultante e, se a comissão já foi paga, quanto será descontado no próximo
  repasse do vendedor.
- **FR-015a**: O Superadmin DEVE poder alterar a devolução na tela do evento cancelado. O retido e a
  comissão DEVEM ser recalculados na hora; comissão já paga ou no banco é ajustada no próximo
  repasse do beneficiário, para mais ou para menos. Devolução ainda não paga muda de valor;
  devolução já paga (ou no banco) só pode aumentar, e o aumento vira um pagamento complementar à
  cliente. Em Gastos Extras, valor, data, categoria, vínculo com o evento e exclusão da devolução
  DEVEM ficar travados, apontando para o evento; o Financeiro continua podendo corrigir nome e PIX.
- **FR-015b**: Salvar uma devolução em Gastos Extras NÃO DEVE apagar o destinatário "cliente", o
  nome e o PIX nem mudar o estado para "aprovado com edição" (hoje qualquer "Salvar" faz isso, e a
  devolução some da Planilha e do evento). O evento com mais de uma devolução mostra todas.

**Comissão e BV no cancelamento**

- **FR-016**: Ao cancelar um evento, a comissão do beneficiário DEVE passar a ser a comissão cheia
  do evento multiplicada por (valor retido ÷ valor de venda), com retido = total pago − devolvido,
  em vez de ser estornada por inteiro. A comissão cheia é a que o evento teria sem o cancelamento,
  pela regra do seu tipo (comum ou EducaManto); o resultado nunca passa dela.
- **FR-017**: Comissão ainda a pagar DEVE ser ajustada para a comissão do retido (cancelada quando o
  retido é zero). Comissão já paga **ou no banco** NÃO DEVE ser reescrita: o próximo repasse do
  beneficiário desconta a diferença.
- **FR-018**: O desconto (e o ajuste para mais da FR-015a) DEVE cair no primeiro repasse do
  beneficiário ainda não liquidado — para comissão comum e EducaManto —, e não no ciclo da venda.
  Um repasse já liquidado NÃO DEVE ser reaberto por um desconto.
- **FR-019**: Ao cancelar um evento com BV, o Superadmin DEVE informar quanto do BV o parceiro
  recebe (de zero ao BV inteiro, sem valor sugerido — é negociação). A Planilha de Pagamentos, na
  tela nova e na antiga (que continua no ar), DEVE mostrar esse valor no lugar do BV original, e não
  mostrar o BV quando o valor for zero. Evento cancelado antes desta feature, sem valor informado,
  NÃO DEVE mostrar BV na Planilha. BV já pago antes do cancelamento NUNCA é reescrito nem escondido
  (o mesmo princípio da FR-017): o valor negociado fica registrado, e a diferença é conversa.
- **FR-020**: Planilha de Pagamentos, tela de Comissões, tela do evento, página de Cancelamentos e DRE
  DEVEM mostrar, por evento, o mesmo valor de comissão do retido (o mês em que cada uma o mostra
  pode diferir); Planilha e Comissões, também o mesmo desconto.
- **FR-021**: As regras de devolução e comissão desta feature DEVEM valer para todo cancelamento, venha
  ele de um evento marcado ou do botão Cancelar da feature 224, exceto venda virtual, que tem o
  estorno próprio.

**O cancelado na DRE e nos relatórios**

- **FR-026**: O sistema DEVE calcular, numa função única, o resumo financeiro do evento cancelado:
  venda; total pago (comprovantes do próprio evento); cada devolução com valor, destinatário e
  estado; total devolvido (somando **todas** as devoluções do evento); retido = pago − devolvido,
  nunca negativo; comissão do retido (FR-016); BV que conta (o negociado, ou o pago quando já tinha
  sido pago — FR-019); imposto sobre o retido (FR-013). A tela do evento, a página de Cancelamentos,
  as duas DREs, o Dashboard Comercial, a Planilha e a tela de Comissões DEVEM ler essa função, e
  nenhuma delas refaz a conta. Comissão, BV e imposto vêm do que ficou gravado no cancelamento,
  nunca recalculados da venda.
- **FR-027**: A DRE (tela nova e antiga) DEVE lançar o evento cancelado **no mês do cancelamento**,
  nas colunas Realizado e Total, nunca no Projetado: o retido soma na Receita Bruta e aparece numa
  linha própria "Retido de cancelamentos (pago − devolvido)"; o BV que conta soma no custo; a
  comissão do retido soma nas Comissões; o imposto sobre o retido soma nos Impostos. Os cachês do
  cancelado ficam fora.
- **FR-028**: A devolução à cliente de evento cancelado NÃO DEVE somar em Gastos Extras da DRE, em
  mês nenhum. A DRE a reconhece pela categoria "Devolução a cliente" junto do vínculo com um evento
  cancelado — nunca pelo destinatário. Gasto de outra categoria ligado ao cancelado (multa, cachê à
  parte) e devolução ligada a evento não cancelado continuam em Gastos Extras. Na Planilha e em
  Gastos Extras, a devolução continua sendo saída. A FR-027 e a FR-028 são inseparáveis: uma sem a
  outra mostra 400 − 40 − 18 − 600 = −258.
- **FR-029**: O cancelado NÃO DEVE voltar à DRE do mês do evento. Satélite de grupo e venda virtual
  cancelados NÃO geram retido.
- **FR-030**: O retido DEVE entrar em margens, custo de talento ÷ receita, Fator R e break-even, e
  aparecer na Receita por Tipo como a barra "Retido de cancelamentos". NÃO DEVE entrar em ticket
  médio, "a receber" nem na contagem de eventos da DRE. Na tela antiga, o ticket médio DEVE deixar
  de dividir a Receita Bruta da cascata pelo número de eventos.
- **FR-031**: Nas duas telas, a Tendência de 6 meses NÃO DEVE contar venda, cachê nem evento de
  cancelado (hoje conta), e DEVE somar o retido à receita e ao lucro do mês do cancelamento;
  "Recebimentos Previstos" NÃO DEVE listar parcela de evento cancelado; a nota "a emitir" de evento
  cancelado continua na lista, com o selo "evento cancelado · retido R$ X".
- **FR-032**: O retido DEVE contar como venda do beneficiário **no mês do cancelamento** — no total
  vendido, no ranking de vendedores e na meta do Dashboard Comercial, na Performance da Home e em
  `/admin/desempenho` —, e a venda original do cancelado NÃO DEVE contar no mês dela. Na ficha da
  cliente, o total vendido conta o retido, não a venda original.

**Sinalizar e filtrar o cancelado**

- **FR-033**: O servidor DEVE devolver, no resumo do evento da agenda, da busca e das listas, uma
  situação única com precedência **cancelado > sumiu do Google > exclusão solicitada**. A contagem
  da faixa (FR-009) NÃO DEVE contar cancelado.
- **FR-034**: A DRE e o Dashboard Comercial DEVEM mostrar, quando houver cancelado no período, o
  card "Cancelamentos do período": quantidade, pago, devolvido (e quanto ainda falta pagar), retido,
  comissão do retido, BV, imposto e efeito no resultado, com link para cada evento.
- **FR-035**: Agenda (Mês, Lista e Dia), lista de vendas do Dashboard Comercial e tabela "Eventos no
  período" da DRE DEVEM esconder o cancelado por padrão e ter o botão "Mostrar cancelados", guardado
  no endereço da tela; ligado, o cancelado aparece esmaecido, riscado e com o selo "Cancelado" (não
  só cor), com o retido no lugar da venda e a comissão do retido no lugar da cheia. Hoje o Dia
  mostra o cancelado sem marca — passa a esconder por padrão.
- **FR-036**: A busca, a ficha da cliente, a ficha do talento e a coluna Evento de Gastos Extras
  DEVEM mostrar o cancelado sempre, com o selo. A ficha do talento NÃO DEVE contar cachê de cancelado
  em "Total faturado". Os seletores que reusam a busca (vincular ensaio, tag NFC, candidato a grupo)
  NÃO DEVEM aceitar evento cancelado: ele aparece bloqueado, com o motivo.
- **FR-037**: A tela do evento cancelado DEVE trocar a grade "Resultado" por "Resultado do
  cancelamento" (pago, devolvido, retido, comissão do retido, BV, imposto) e a pendência "em aberto"
  pela devolução e pelo retido; "Sincronizar" e "Editar no Google Agenda" NÃO DEVEM aparecer.
- **FR-038**: A página de Cancelamentos DEVE mostrar pago, cada devolução com o estado (inclusive
  "no banco"), retido, comissão do retido, BV e imposto, com filtro por mês do cancelamento e por
  estado da devolução e o total retido do período. O Financeiro DEVE poder lê-la; as ações seguem só
  do Superadmin.

**Portal do artista**

- **FR-022**: O elenco escalado DEVE ver o evento marcado no portal com o aviso "Evento em confirmação
  — entre em contato com a produção"; o aviso some quando a marca some. O evento cancelado sai da
  agenda, dos convites e do histórico do portal, como hoje, e também DEVE sair da avaliação
  pós-evento (hoje um cancelado que terminou nos últimos 7 dias acende o "Avaliar" e aceita nota).

**Rastro e travas**

- **FR-023**: Marcar, avisar, devolver ao Google, cancelar com devolução e desmarcar (sozinho ou por
  decisão) DEVEM ficar no histórico do evento e na auditoria, com o motivo — no caso da marca, o que
  está preso ao evento.
- **FR-024**: A escrita no Google Agenda desta feature (devolver ao Google) DEVE nascer travada fora
  da produção (Princípio XIV). Hoje não existe trava para evento de show — a de calendário cobre só
  os prazos de figurino —; o plan decide estender essa trava ou criar outra, e a falta de trava nas
  escritas antigas vira dívida no `docs/05`.
- **FR-025**: Os textos do sistema que descrevem o cancelamento e o estorno DEVEM dizer o que
  acontece de fato. Hoje o diálogo diz que a comissão paga "vira estorno no próximo repasse", e a
  documentação de `aplicar_estorno_comissao` diz que a Planilha desconta via `_seller_payable_rows` —
  a Planilha não usa essa função. Também mentem: a tela do evento cancelado ("Não conta em nenhuma
  métrica e sumiu da agenda" — falso, e "sumiu" colide com a marca "Sumiu do Google"); a documentação
  da DRE da API ("sem duplicar" — ela copia o corpo da antiga); e o rótulo "CPV (cachês — eventos
  normais)", que omite o BV.

### Entidades *(se houver dados)*

- **Evento (`CalendarEvent`)**: ganha o estado "sumiu do Google em <data>", que existe até a
  decisão do Superadmin ou o reaparecimento. Onde esse estado mora é decisão do plan, mas a
  verificação de 29/09 mostrou que **reusar os campos do pedido de exclusão da 224 quebra**: o
  Comercial sobrescreveria a marca ao pedir exclusão; "Recusar" zeraria a marca e o sync marcaria e
  avisaria de novo, em ciclo; o autor do pedido é chave para usuário e não existe usuário "Sistema";
  o cancelamento limpa esses campos e apagaria o rastro. A marca não pode tocar `cancelled_at`: é
  isso que faz a FR-005 valer sem mexer no financeiro.
- **Notificação (`Notification`, feature 272)**: um tipo novo de aviso, "evento sumiu do Google",
  endereçado a Superadmins e Comerciais.
- **Devolução à cliente (`SpecialExpense`, categoria devolução, feature 224)**: já existe; passa a
  ser lida pelo evento cancelado para mostrar valor, destinatário, estado e retido.
- **Comissão (`CommissionPayment`)**: a linha do evento cancelado passa a valer o retido; o desconto
  continua sendo uma linha negativa, agora no primeiro repasse não liquidado; o ajuste para mais
  (FR-015a) é uma linha positiva no mesmo repasse. A comissão cheia e a venda usadas na conta ficam
  congeladas no cancelamento (hoje a aba Comercial e a escala do cancelado continuam editáveis).
- **BV (`EventAcrescimo` com `is_bv`)**: no evento cancelado, passa a valer o que o Superadmin
  negociou no cancelamento; onde esse valor mora é decisão do plan — não pode ser o próprio
  acréscimo, que a aba Comercial apaga e recria a cada gravação.
- **Imposto sobre o retido**: valor em reais informado no cancelamento de evento "com nota",
  alterável junto com a devolução; mora junto do que a FR-016 e a FR-019 congelam.
- **Resumo do cancelado (FR-026)**: derivado, sem tabela própria — pago, devoluções, retido,
  comissão, BV e imposto, lidos do que foi gravado.

### RBAC *(obrigatório se houver endpoint novo ou alterado)*

- Devolver ao Google Agenda (endpoint novo, `POST`) — papéis: SUPERADMIN (o gate de
  excluir/cancelar da 224); linha na tabela de `docs/01` §4.3.
- Cancelar (endpoint existente da 224, com corpo de devolução e BV negociado) — papéis inalterados:
  SUPERADMIN.
- Alterar a devolução de evento cancelado (endpoint novo) — papéis: SUPERADMIN. A edição do valor
  pela tela de Gastos Extras passa a ser recusada para gasto de devolução ligado a evento.
- A faixa (quantidade e lista dos eventos marcados) — leitura para SUPERADMIN e COMERCIAL; outros
  papéis recebem a faixa vazia, sem erro.
- A marca vai no payload de detalhe e da agenda para quem já pode ver o evento; as saídas de
  decisão só aparecem por flag do servidor (o frontend não decide RBAC).
- Portal: o aviso vai só nos eventos em que o talento está escalado (portão "é o dono do recurso").
- Página de Cancelamentos (`GET` existente da 224) — ganha FINANCEIRO, só leitura; as ações seguem
  SUPERADMIN.
- "Mostrar cancelados" na agenda — vale para quem já vê a agenda; o resumo do evento continua sem
  dinheiro para quem não vê dinheiro.
- DRE — papéis inalterados (FINANCEIRO e SUPERADMIN). Dashboard Comercial — papéis inalterados.

## Verificação (`verify_303.py`) *(obrigatório — Princípio VIII)*

Arquivo: `specs/303-sync-nao-apaga-venda/verify_303.py`, contra `manto_local` (`DATABASE_URL` de
`.local-db-url`, `FLASK_ENV=development`, `MANTO_SEM_THREADS=1`). Login só por
`POST /api/auth/login`; escrita conferida por conexão separada; limpeza no `finally`. **O Google é
substituído no verify** (lista do mês, consulta de um evento e criação): o `manto_local` tem o token
real da empresa, e nenhum cenário pode ler ou escrever na agenda de verdade.

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Evento com venda ausente da lista e da consulta do Google; sync do mês | fica no banco, marcado, com venda/comprovante/escala intactos; histórico e auditoria | não |
| 2 | Mesmo evento; sync de novo, duas vezes | uma notificação por Superadmin e por Comercial, nenhuma nova | não |
| 3 | Sem venda, com comprovante | fica e é marcado | não |
| 4 | Sem venda, com contrato | fica e é marcado | não |
| 5 | Sem venda, com escalado (role existente com `talent_id`, sem inventar personagem) | fica e é marcado | não |
| 6 | Satélite de grupo comercial, sem venda própria | fica e é marcado | não |
| 7 | Evento vazio sumido; SHOW só com o técnico de som automático | apagados como hoje | não |
| 7a | SHOW com a vaga de Presença designada; SHOW com outro técnico no lugar do padrão | ficam e são marcados | não |
| 8 | Evento movido no Google para um mês posterior; sync dos dois meses em ordem (e a variante antecipado para um mês já passado) | mesmo registro, data nova, venda intacta, sem marca e sem notificação | não |
| 9 | Evento marcado volta à lista do Google | marca some; histórico diz por quê | não |
| 10 | Superadmin devolve ao Google (criação substituída) | evento com o id novo do Google, marca some, histórico | não |
| 11 | COMERCIAL tenta devolver ao Google e cancelar | recusado nos dois; nada muda | **sim** |
| 12 | Superadmin cancela evento marcado com devolução de R$ 600 de R$ 1.000 pagos | cancelado; devolução a pagar de R$ 600 na Planilha; retido R$ 400 no evento; nenhuma tentativa de remover do Google | não |
| 13 | Consulta ao Google falha no meio do ciclo | nada apagado nem marcado | não |
| 14 | Editar evento marcado (título e data; troca de tipo para SHOW); botão Sincronizar do evento marcado | salva sem escrever no Google e sem aviso de falha; marca continua; o Sincronizar não altera evento nem escala | não |
| 15 | Evento cancelado e venda virtual ausentes do Google | comportamento de hoje, sem marca | não |
| 16 | Devolução maior que o pago; e cancelamento sem escolher Tudo/Parte/Nada | recusados; nada muda | **sim** |
| 17 | Faixa: Superadmin e Comercial com 1 evento marcado; Figurino; depois de resolvido | Superadmin e Comercial veem 1; Figurino vê vazia; resolvido → vazia | não |
| 18 | Devolução paga na Planilha | o evento mostra a devolução como paga | não |
| 19 | Venda de R$ 2.000, comissão a pagar de R$ 100; cancela com R$ 400 retidos de R$ 1.000 pagos (e a variante com BV de R$ 200: cheia R$ 90) | comissão a pagar vira R$ 20 (R$ 18 com BV); nunca passa da cheia | não |
| 20 | Comissão paga de R$ 100; mesmo cancelamento | paga intacta; desconto de R$ 80 no primeiro repasse não liquidado; repasse já pago não é reaberto | não |
| 21 | Comissão **no banco**; mesmo cancelamento | tratada como paga: desconto de R$ 80 | não |
| 22 | Devolução total com comissão a pagar / paga | cancelada / desconto da comissão inteira | não |
| 23 | Evento com BV de R$ 200 cancelado com "parceiro recebe R$ 50"; outro com R$ 0; outro com BV já pago | Planilha mostra R$ 50 / nada / o pago intacto, nas duas telas; Planilha e Comissões batem por evento, reabertas depois do cancelamento | não |
| 23c | Satélite de grupo cancelado; Gastos Extras "Salvar" numa devolução | satélite sem devolução nem mexida em comissão/BV; a devolução mantém destinatário, nome e PIX | não |
| 23a | Devolução alterada depois do cancelamento: R$ 600 → R$ 800 (a pagar), com comissão de R$ 20 a pagar; depois, com a comissão já paga, R$ 800 → R$ 500 | comissão vira R$ 10; depois, ajuste de +R$ 15 no próximo repasse; Gastos Extras recusa editar o valor | não |
| 23b | COMERCIAL tenta alterar a devolução; devolução já paga diminuída | recusados | **sim** |
| 24 | Portal: talento escalado e talento de fora, com o evento marcado; avaliação de evento cancelado | escalado vê o aviso; de fora não vê nada; avaliação do cancelado recusada | **sim** (o de fora e a avaliação) |
| 26 | Exemplo (15/11, venda 2.000, BV 200, `commission_rate` 5 gravado no evento, sem nota, pago 1.000) cancelado hoje com 600 devolvidos e "parceiro recebe 40"; DRE do mês do cancelamento na API e na tela antiga | retido 400; custo +40; comissões +18; gastos extras sem os 600; resultado +342 em Realizado e Total, 0 no Projetado; API e tela antiga iguais ao centavo; contra a `main`, o mesmo cenário dá −600 (prova por mutação) | não |
| 27 | Mesmo evento: DRE de novembro e Tendência | novembro sem receita, custo, comissão nem evento; Tendência sem os +2.000 e com +400 no mês do cancelamento | não |
| 28 | Variante "com nota", imposto informado 64 | impostos +64, resultado +278 | não |
| 29 | Devolução alterada de 600 para 800; complemento depois de paga | retido 200, comissão e resultado recalculados no mesmo mês; nenhuma devolução em gastos extras | não |
| 30 | "Salvar" numa devolução em Gastos Extras; tentativa de trocar a categoria | a DRE não volta a somar a devolução; a troca de categoria é recusada | **sim** (a troca) |
| 31 | Multa do elenco ligada ao cancelado; "Devolução a cliente" ligada a evento vivo | as duas continuam em gastos extras | não |
| 32 | Satélite cancelado com comprovante; venda virtual cancelada; cancelado com tudo devolvido e BV de 200 já pago | satélite e virtual sem retido; no terceiro, retido 0, comissão 0, custo +200 | não |
| 33 | Ticket médio, "a receber", Receita por Tipo, Fator R e break-even, nas duas telas | ticket médio e "a receber" sem mudança; ticket da tela antiga não sobe; barra do retido 400; Fator R e break-even com o retido | não |
| 34 | Parcelas e nota "a emitir" do cancelado | parcelas fora dos Recebimentos Previstos; nota na lista, com o selo | não |
| 35 | Abrir Comissões e Planilha (que resincronizam comissões) e depois a DRE | a comissão do retido continua 18 nas três | não |
| 36 | Regressão: DRE e Tendência de todos os meses sem cancelamento do espelho, `main` × branch | idênticas, centavo a centavo | não |
| 37 | Agenda Mês, Lista e Dia sem e com "Mostrar cancelados"; busca; evento marcado e depois cancelado | escondido por padrão nas três; visível riscado com o selo; busca sempre com o selo; situação "cancelado", nunca "sumiu"; faixa não conta cancelado | não |
| 38 | Vincular ensaio, tag NFC e grupo a evento cancelado | recusado, com o motivo | **sim** |
| 39 | FINANCEIRO lê a página de Cancelamentos e tenta alterar a devolução; FIGURINO lê a página | Financeiro lê e é recusado na escrita; Figurino recusado | **sim** (os recusados) |
| 40 | Dashboard Comercial e Performance da Home de setembro e novembro; ficha da cliente; ficha do talento; tela do evento cancelado | vendedor com +400 em setembro e sem os 2.000 em novembro; card com 1 cancelado; cliente com total vendido 400; talento sem o cachê do cancelado; "Resultado do cancelamento" 1.000 / 600 / 400 / 18 / 40, sem "em aberto" | não |
| 41 | limpeza | registros descartáveis apagados (`roles.clear()` antes do usuário) | — |

Conferência de tela: a faixa em duas telas quaisquer como Superadmin e como Comercial (e ausente
como Figurino); a tela do evento marcado como Superadmin (o que está em jogo + duas saídas) e como
Comercial (marca, sem saídas); o diálogo de cancelamento com devolução parcial e o efeito na
comissão; o evento cancelado mostrando a devolução; o sino; o portal em 375×812 com o aviso; a DRE
(nova e antiga) com a linha do retido e o card de cancelamentos; o Dashboard Comercial com o card e
o botão; a agenda com "Mostrar cancelados" ligado e desligado; a página de Cancelamentos como
Financeiro.

## Critérios de sucesso *(obrigatório)*

- **SC-001**: Depois do deploy, nenhum evento com venda, comprovante, contrato, gente escalada pela
  equipe ou grupo é apagado por sumiço no Google — conferível na auditoria (zero exclusões
  automáticas de evento assim).
- **SC-002**: Evento adiado no Google para outro mês chega à data nova com a mesma venda e os mesmos
  comprovantes em 100% dos casos, sem faixa nem aviso.
- **SC-003**: Todo sumiço de evento com dinheiro aparece na faixa e no sino de Superadmin e Comercial
  no mesmo ciclo do sync em que foi percebido.
- **SC-004**: A partir da faixa, o Superadmin resolve o evento (devolve ao Google, ou cancela
  devolvendo o dinheiro) sem sair da tela do evento.
- **SC-005**: Todo cancelamento com dinheiro recebido deixa, no próprio evento, quanto foi devolvido,
  quanto ficou retido e se a devolução já foi paga.
- **SC-006**: Em todo cancelamento, a comissão resultante é a comissão cheia × retido ÷ venda, nunca
  acima da cheia, e o desconto de comissão já paga aparece no primeiro repasse ainda não liquidado do
  vendedor — nunca num repasse já pago.
- **SC-007**: Todo cancelamento com dinheiro retido aparece na DRE do mês do cancelamento como retido
  − comissão do retido − BV que conta − imposto informado, igual nas duas DREs; nenhum mês mostra
  devolução de cancelado como gasto; e todo mês sem cancelamento continua idêntico, centavo a
  centavo.
- **SC-008**: Em nenhuma tela o cancelado aparece como evento normal: ou está escondido (e o botão
  "Mostrar cancelados" o traz), ou aparece com o selo "Cancelado".

## Fora de escopo

- "Solicitar cancelamento" pelo Comercial com aviso (o resto da D1): onda 2. Nesta feature o
  Comercial vê a faixa e a marca, mas não pede nada pelo sistema.
- Fundir automaticamente um evento recriado à mão no Google (id novo) com o evento marcado.
- Venda virtual: continua com a regra própria (FR-029b da feature de virtuais), sem a marca nova.
- Multa ou cachê do elenco num cancelamento em cima da hora: continua como gasto extra à parte.
- Recuperar BV já pago de evento cancelado: o valor negociado fica registrado; cobrar a diferença
  do parceiro é conversa, não sistema.
- Lembrete recorrente enquanto a marca estiver aberta (a faixa já é permanente).
- Mudar quem pode excluir ou cancelar, ou o que conta como vazio no botão Excluir da 224.
- Gasto extra marcado "Pago" sem prova de saída (D20): só vira dívida no `docs/05`.
- Remoção do Jinja (pausada): na DRE antiga entram só os números vindos das funções comuns, uma
  linha no template e o ajuste do ticket médio. Não extrair nem apagar a view, nem mover
  `_compute_drg` ou `_event_commission` (`docs/PARADA_REMOCAO_JINJA.md`).
- A DRE não lê as linhas de comissão paga nem o desconto no repasse (acerto de caixa, na Planilha);
  não há fechamento de mês — alterar uma devolução reescreve o mês do cancelamento, como cancelar um
  evento passado já reescreve o mês dele desde a 224.
- O que fazer com a nota fiscal do cancelado; marketing contar cancelado como conversão; card de
  "devoluções a pagar" na Home.
- O painel antigo de "Estornos pendentes" (desconta o estorno duas vezes no mês da venda) e as
  parcelas que nunca são marcadas como recebidas: dívidas no `docs/05`, não entram aqui.
- As outras divergências de régua de `/admin/desempenho` (satélite, ensaio, permuta, eixo de data):
  nesta feature, só o cancelado.

## Docs a atualizar

`docs/01` §4.3 (endpoint de devolver ao Google, leitura da faixa, página de Cancelamentos com
FINANCEIRO) e o contrato dos payloads (evento, agenda, portal, DRE, Dashboard Comercial); `docs/02`
(faixa global; tela do evento: marca, saídas, devolução e "Resultado do cancelamento"; diálogo de
cancelamento; portal: aviso; DRE e Dashboard: card de cancelamentos e botão; agenda: "Mostrar
cancelados"; página de Cancelamentos); `docs/03` (entrada no topo + índice); `docs/04`
(invariantes: o sync nunca apaga evento com dinheiro; mudança de data não é sumiço; comissão de
cancelado = comissão cheia × retido ÷ venda, nunca acima da cheia; desconto no primeiro repasse não
liquidado; cancelado entra na DRE pelo retido no mês do cancelamento e a devolução de cancelado
nunca é gasto na DRE; o retido é venda do mês do cancelamento); `docs/05` (riscar a dívida 49;
registrar a D20, a falta de trava nas escritas antigas no Google, a lista do mês sem paginação, a
série recorrente, o painel antigo de estornos, as parcelas nunca marcadas como recebidas e as
réguas de `/admin/desempenho`).

## Premissas

- "Com dinheiro" é a regra que a 224 usa para decidir entre excluir e cancelar (venda, comprovante,
  contrato, escalado), **mais** pertencer a um grupo comercial — o satélite é dia de uma venda que
  mora no líder, e apagá-lo perde a escala daquele dia —, **menos** a vaga de técnico de som que o
  sistema preenche sozinho (decisão do dono, 29/09). A regra do botão Excluir da 224 não muda.
- O "pago pela cliente" é a soma dos comprovantes anexados **ao próprio evento** — a mesma soma que
  a 224 já usa no cancelamento. Num grupo, o dinheiro se resolve no líder (ver Casos de borda).
- Devolver ao Google recria o evento sem convidados; os convites por e-mail do sistema não são
  reenviados.
- Caminhos que limpam por sumiço (verificado em 29/09): o ciclo automático (thread a cada 10 min e
  `sync_worker`), do mês corrente até +6 meses ou até o último evento do banco +1 mês; o "Limpar
  eventos fantasma" de `/admin/sync` (Superadmin), que percorre em ordem os meses que têm algum
  evento no banco, passados inclusive; e a rota antiga `/agenda?force_sync=1`, que só responde
  chamando o backend direto. "Sincronizar agora" (mês corrente e 6 seguintes) e o "Sincronizar" de um
  evento não limpam. A regra vale em todo caminho que limpa.
- Até o deploy, vale a orientação à equipe de não apagar no Google evento com venda.
- O cancelado não conta como evento realizado para a recorrência da cliente; o retido conta no total
  vendido dela (FR-032).
- Taxa e imposto do exemplo: 5% gravado no próprio evento (o padrão do sistema é 2,5%) e 16% como
  referência (configurável). O verify grava a taxa no evento e lê a referência da configuração.
- **Tamanho**: com os relatórios, a 303 toca agenda, notificações, financeiro, comercial e portal. Se
  o plan mostrar que não cabe num deploy seguro, a divisão possível é FR-001 a FR-032 na 303 e
  FR-033 a FR-038 (sinalizar e filtrar, sem migration) numa 303b logo em seguida — nunca separando a
  FR-027 da FR-028.
