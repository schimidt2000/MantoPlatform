# Pesquisa — Feature 313 (desconto e PIX na calculadora)

Fonte: o plano 3b (§4.1–4.3, §6, §8 — só a P1) e `pesquisa/reconferencia-2026-10-21.md`, que vale onde diverge.
Aqui só as decisões técnicas que o plano deixou abertas ou que a reconferência mudou. Linhas contra HEAD `c074657b`.

## R1 — Uma função para a ordem da conta (Q7 + Q9), usada por todos

**Decisão**: `quote_ops.aplicar_acrescimos(base, acrescimos, nota) -> (preco, valores_por_linha)` — pura, em float
como a conta de hoje, implementando a ordem do dono: (a) os acréscimos que **não** são BV — R$ inteiro, uma vez; %
sobre a `base`; (b) o BV em % sobre `base + Σ(a)`, cada linha de BV sobre o mesmo número (os BVs não se veem); o BV
em reais inteiro, uma vez; (c) a nota sobre a soma (`÷ NF_DIVISOR`). E `quote_ops.preco_na_duracao(snap, horas)`,
que monta a base da duração a partir das bases salvas (1–4h: a da coluna; acima de 4h: `(base_4h − produtos) ÷ 4 ×
h + produtos`, o produto fixo da 309) e chama `aplicar_acrescimos` por cima, devolvendo `{bruto, linhas, total}`
(o `total` com o desconto do snapshot). **Acima de 4h sem acréscimo em R$ (nem BV em reais) e sem produto**, a
conta é linear e a regra nova dá o mesmo número que escalar o preço de 4h: aí a extra continua
`round(bruto_4h ÷ 4 × h, 2)` — o arredondamento de hoje, centavo por centavo (refazer pela base mudaria o centavo em
cerca de metade dos orçamentos com nota ou acréscimo em %; analyze A2). Só com acréscimo em R$ ou produto a extra
sai da base. `calculate_quote` usa as duas (as colunas 1–4h e a extra); o prefill
(`extra_por_horas`, `total_custom`) e o evento (`orcamento_evento_ops`, R3) também. **Uma régua só para orçamento
novo.**

**A ordem da soma em float** (analyze B5): nos orçamentos que não são exceção, `aplicar_acrescimos` reproduz a
expressão de hoje — `add` acumulado a partir de 0,0 na ordem do snapshot, `round(t + add, 2)`, depois `round(÷
0,84, 2)`; a base do BV em % é `t + add_dos_não_BV`, sem arredondar, na mesma ordem; o `valores_brl` (Decimal)
sobre esse mesmo número.

**Rationale**: a reconferência achou quatro réguas acima de 4h (calculadora, `produtos.total_na_duracao`, o prefill,
`_linhas_na_duracao`/`acrescimos_do_orcamento`) e a conta inversa da 305; reproduzir a regra nova em cada uma
convidaria a divergência que a 309 já teve.

**Alternativas**: corrigir as quatro réguas uma a uma (rejeitada: quatro lugares para a próxima mudança); recalcular
no evento chamando `calculate_quote` inteiro (rejeitada: lê tabela de preços viva, não o que foi cotado).

## R2 — A marca de regra no orçamento salvo

**Decisão**: o `snapshot` (o `form_snapshot` salvo) ganha `versao_conta: 2` e `bases: [b1, b2, b3, b4]` (a base
pré-acréscimos de cada coluna: apresentação + transporte + produto, a que `aplicar_acrescimos` recebe) e `brutos:
{"1h", "2h", "3h", "4h", "custom"?}` (o preço antes do desconto). Sem `versao_conta` (= os 2.710 salvos), todo
leitor segue o caminho de hoje, inalterado (premissa 3 da spec, 020). Com ela, o evento e o prefill leem os números
pela R1, nunca pela conta inversa.

**Rationale**: os leitores da 305 leem o `form_snapshot` (`snapshot_do_orcamento`, `orcamento_evento_ops.py:65-72`);
a régua velha tem de continuar para o salvo (o `verify_305` cen_04 espera BV de 375 em 6h num orçamento sem a
chave), e a nova para o novo — só uma marca no próprio orçamento distingue. Inteiro, não booleano: a noite dos dias
será a versão 3.

**Validação do que volta do navegador** (o `/salvar` persiste o snapshot que o navegador devolve, research R2 da
305): `bases` com 4 números finitos ≥ 0, `brutos` ≥ os totais gravados e, de 1h a 4h, `|preco_na_duracao(snap,
d).bruto − brutos[d]| ≤ 0,01` (as bases e os cheios contam a mesma história — analyze B8); fora disso, o leitor cai
no caminho de hoje pelas colunas. De 1h a 4h as linhas do BV saem do `valores_brl` (Decimal, como a 305) — a mesma
fonte do `bv_*` do `quote` —, para o BV a repassar da calculadora e o gravado no evento não diferirem em R$ 0,01;
acima de 4h, de `preco_na_duracao`.

## R3 — O evento: cheio no denominador, final na venda

**Decisão**: `orcamento_evento_ops` passa a ter `_bruto_da_duracao(entry, d)` (cheio) ao lado de
`_total_da_duracao(entry, d)` (final). Para orçamento sem `versao_conta`, os dois devolvem o de hoje (iguais). Com
ela: cheio = `brutos[d]` (1–4h) ou `preco_na_duracao(...)["bruto"]` (acima de 4h); final = a coluna gravada (1–4h)
ou `preco_na_duracao(...)["total"]`. Quem usa o quê:

| Leitor | Hoje | Passa a usar |
|---|---|---|
| `acrescimos_do_orcamento` → `total` (o denominador do BV em `plano_dos_acrescimos`) | `_total_da_duracao` | **cheio** |
| `acrescimos_do_orcamento` → valores por linha | `valores_brl` / conta inversa / régua h ÷ 4 | v2: `preco_na_duracao(...)["linhas"]`; legado: igual |
| `_valor_gravado` (teto) | total | cheio |
| `deduzir_duracao` (compara o `sale_value_gross or sale_value`) | total | o **cheio** e, sem casar, o **final** (o
bruto vazio, o gêmeo Jinja e o bundle velho gravam bruto = final — analyze B6) |
| `bv_nasce_no_vinculo` (venda que o vínculo grava) | total | **final** |
| `aplicar_valores_do_orcamento` (273) | `sale_value = sale_value_gross = total` | `sale_value` = final, `sale_value_gross` = cheio |

`bv_que_acompanha` não muda (assinatura e tolerância — quatro chamadores); muda o número passado como `total`. A
proporção continua entre **líquidos** (`plano_dos_acrescimos`: venda × 0,84 com nota no evento ÷ cheio × 0,84 com
nota no orçamento, a régua da B10): o cheio só entra no lugar do total.

**Rationale**: sem isto a razão venda ÷ total dá 1 e o BV não encolhe (reconferência §2); a dedução de duração
deixaria de achar a duração pelo valor.

## R4 — A constante do PIX

**Decisão**: o PIX à vista usa `AVISTA_FATOR` de `app/educamanto/pricing_ops.py:29` (0,95), que o `quote_ops` passa a
importar ao lado do `NF_DIVISOR` (`quote_ops.py:18`): `PIX_PCT_PADRAO = round((1 − AVISTA_FATOR) × 100, 6)` — sem o
`round`, o float dá 5,000000000000004 e o negociado de exatamente 5% (o caso mais comum) perderia a frase "já está
aplicado" (analyze A3). `pix_pct = max(PIX_PCT_PADRAO, desconto exato)`, e a frase compara com tolerância de
0,000001 (`round(d, 6) >= PIX_PCT_PADRAO`); com o negociado ≥ 5%, `pix_d = total_d` e `bv_pix_d = bv_d`, sem
recalcular — a duração fechada por valor não sai um centavo diferente (analyze B4); `pix = round(bruto × (1 − pix_pct ÷ 100), 2)`. O PDF deixa de ter o seu `0.95`
(`pdf.py:235-242`) e lê `pix_*` do `quote`, com `round(total × 0,95, 2)` como leitura de `quote` antigo.

**Rationale**: sem desconto, `bruto = total` e a conta é a de hoje byte a byte (`round(t*0.95,2)`); uma constante
que já existe, em vez de uma terceira.

## R5 — Arredondamento dos valores novos

**Decisão**: os totais continuam em float com `round(x, 2)` (a paridade byte a byte com o gabarito exige); o total
com desconto é `round(bruto × (1 − d ÷ 100), 2)`; a duração do "fechar por R$" sai com o valor digitado exato; o BV
que acompanha vem de `bv_que_acompanha` (Decimal HALF_UP, a da 305). O % mostrado (`desconto_pct_texto`) é
`floor(round(d, 6) × 10) ÷ 10` com vírgula e sem ",0" — o `round(d, 6)` antes do piso evita que 10% achado por valor
(9,9999999…) vire "9,9". O selo do valor de venda no evento usa a mesma regra (função TS única em
`lib/desconto.ts`, R9); onde o `quote` traz `desconto_pct_texto`, a tela mostra o do servidor (uma fonte), e o
verify confere as duas com 8,333…% e 9,9999…% (analyze A20). Os valores novos (total com desconto, PIX) ficam em
float `round(x, 2)` porque são a mesma conta que a mensagem imprime; o BV, que vai a dinheiro gravado no evento,
é Decimal HALF_UP (305) — analyze A15.

## R6 — O "fechar por R$": quais durações

**Decisão**: o seletor oferece exatamente as durações que o resultado mostra — `show_1h..show_4h` (com `valor_unico`
só a 1h, rotulada "Preço de tabela") e a extra quando `total_custom` existe; o servidor recusa (`fields.desconto_valor`)
uma duração fora desse conjunto, com a mesma regra (`show` já forçado em 1h quando `so_produto`,
`quote_ops.py:579-584`). O payload leva só o campo do modo ativo: modo "%" → `desconto_pct`; modo "valor" →
`desconto_valor` + `desconto_duracao`. O campo do outro modo é só leitura, preenchido do resultado vivo — nunca volta
ao estado que monta o payload (sem laço de recálculo).

## R7 — Personalizado

**Decisão**: o desconto incide sobre o valor personalizado (digitado ou multiplicador), como o plano (passo 6); os
acréscimos continuam fora do personalizado (`valores_brl` zerados, 305); `brutos` guarda o valor personalizado;
`bases` não se aplica (o evento segue "orçamento personalizado", sem BV). O "fechar por R$" vale também no
personalizado. Acima de 4h (o "Outra (h)" e o prefill, analyze B7): o cheio é a régua de hoje sobre
`brutos["4h"]` (multiplicador com produto: o produto fixo, sem acréscimos nem nota, como a 309) e o final = cheio ×
(1 − d), arredondado — nunca a régua sobre o `total_4h` já com desconto, que subtrairia o produto cheio de um total
com desconto.

## R8 — EducaManto

**Decisão**: `_totais_contratacao` (`app/educamanto/quote_ops.py:124-129`) faz `pop` de `desconto_pct`,
`desconto_valor`, `desconto_duracao` junto dos de `event_date`/`produtos`. A regra de acréscimo da R1 vale lá também
(mesma função; nenhum dos orçamentos EducaManto salvos muda — 020). O `AcrescimosEditor` ganha props `tipoBv` (o tipo
que é BV, para a linha que troca para ele nascer em %) e `ajuda` (o texto do rodapé), e o EducaManto passa a ajuda
sem "acompanha o desconto".

## R9 — Tela: estado desatualizado e o arredondamento compartilhado

**Decisão**: o card Resultado e o "outro" campo do desconto seguem `resultadoVivo` (resposta da entrada atual, sem
erro), não só `calcular.isPending`: durante o debounce, numa resposta velha ou com erro, os números ficam
esmaecidos e marcados "recalculando…"/"corrija os campos". Os erros de campo do desconto saem ao lado do bloco
Desconto. `lib/desconto.ts` (novo, no app interno): `textoDoPercentual(d)` (R5) e `percentualDoDesconto(bruto,
venda)`, usados pela calculadora, pelo orçamento gerado, pelo histórico e pelo `ValoresBlock`.

## R10 — PDF de uma página

**Decisão**: no PDF, cada duração mostra "R$ Y (de R$ X)" na mesma linha do valor, e uma linha única "Desconto de N%
aplicado" abaixo do investimento — não uma linha por duração —, para caber na página que a 307 já aperta (nota da
data especial em até 3 linhas). O bloco do PIX lê `pix_*` e, com negociado ≥ 5%, vira "PIX à vista: o mesmo valor —
o desconto de N% já está aplicado". A mensagem do WhatsApp tem as frases da Q3 por duração (ali não há limite de
página).

## R11 — Paridade (o gabarito)

**Decisão**: `gabarito_paridade.py` (na pasta da feature, só leitura) recalcula todos os `form_snapshot` do
`manto_local` com o `calculate_quote` da `c074657b` e grava `quote` + `snapshot` (ou o erro) num JSON no
scratchpad, antes de qualquer mudança no núcleo. O cenário 1 compara depois: idêntico exceto (a) as chaves novas e
(b) as exceções da Q7, cada uma conferida pela fórmula — BV em % com outro acréscimo (o BV passa a incidir sobre o
outro); duração extra com acréscimo em R$ (o R$ uma vez); produto acima de 4h com acréscimo (a 309 escalava o R$).
Os 2 BV em reais sem extra ficam idênticos. A mensagem é comparada byte a byte nos orçamentos sem exceção.

## R12 — O que fica para a noite dos dias

Não se extrai `_calcular_dia` nesta feature: a R1 já separa o que é "do pedido" (acréscimos, BV, nota, desconto,
PIX) do resto da conta, que a noite dos dias quebrará por dia. Nenhuma chave `dias_adicionais` é aceita ou
devolvida aqui; `versao_conta` 3 fica para ela.
