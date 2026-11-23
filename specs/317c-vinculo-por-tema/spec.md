# 317c — Contrato não se liga à venda por palavra de ocasião, e o vínculo fraco cede ao telefone

**Branch**: `317c-vinculo-por-tema` (da `main`) · **Created**: 2026-11-23 · **Status**: Pronta na branch, sem
merge (`verify_317c` 11/11, `verify_317b` 12/12, `verify_317` 36/36) · **Migration**: nenhuma · **Nível**: 2
(correção da 317)

## O pedido

Em 23/11/2026, ao refazer o contrato do Natal Thermas, o evento aparecia como "Assinado em 13/11". O contrato
ligado era de outra cliente: `25122026 + (11) …3334 + Natal`, de uma visita de Papai Noel em 25/12. O dono:

> "Sim, óbvio que precisa ser desligado. Já abra um branch para conferir se os contratos ligados atualmente
> estão condizentes e também revisar a regra caso seja necessário."

O contrato foi desligado do Thermas na produção no mesmo dia (documento 965, hoje em "A conferir" como
"desligado", com a visita 1525 sugerida por ter o mesmo telefone).

## Como o erro aconteceu

O sinal 5 da 317b (`sincronizar_ops._outra_ligacao` → `contratos_ops.tema_por_palavra`): sem venda com a data e
o telefone do contrato, liga à **única venda do dia com uma palavra do tema** no título ou no tema do formulário.
Em 13/11 a visita de Papai Noel ainda não tinha o telefone da cliente; a única venda de 25/12 com a palavra
"natal" era o `(CORP) NATAL THERMAS`. E vínculo automático, depois de feito, **nunca é reavaliado**
(`aplicar_envelope` só chama `_vincular` em documento novo ou "a conferir" automático): quando a visita certa
ganhou o telefone, o contrato continuou no Thermas.

## O que a auditoria mostrou

`auditoria_vinculos.py` (nesta pasta, só leitura) contra o espelho `manto_317c`, restaurado do dump de produção
de 19/11/2026. Para cada contrato de cliente ligado, pergunta o que sustenta o vínculo hoje e o que a regra
decidiria hoje, do zero, usando as funções do próprio sistema.

| O que sustenta o vínculo | Contratos |
|---|---|
| Data + telefone | 206 |
| Telefone, data a um dia | 3 |
| Telefone, outra data (formulário de festa remarcada) | 2 |
| E-mail | 1 |
| **Só a palavra do tema** | **14** |
| Total (todos automáticos; nenhum ligado à mão) | 226 |

Dos 14 ligados só pela palavra:

- **11 estão certos** e mostram por que o sinal existe: "Arraiá com o Snoopy" × `SNOOPY + CHARLIE`, "Turma da
  Mônica" × `MONICA + MAGALI…`, "Raya é o último dragão" × `AURORA + PRINCIPE + RAYA`, "Bem Estar Qualidade de
  Vida" × o tema do formulário. Em 6 deles a venda tem telefone conhecido **diferente** do contrato (outro
  responsável, ficha duplicada) — recusar por "telefone diferente" derrubaria vínculo certo.
- **3 são da palavra "Natal", e nenhum se sustenta**:
  - 965 `25122026 + … + Natal` → Natal Thermas; a visita 1525 tem o telefone do contrato. **Errado** (desligado).
  - 944 `24122026 + … + Natal` (assinado em 03/11) → visita 1413; a visita 1488, do mesmo dia, tem o telefone
    do contrato e está "Sem contrato na ClickSign". **Provavelmente errado**, ainda assim na produção em 23/11.
  - 934, o mesmo nome, envelope cancelado → mesma visita 1413.

A regra de hoje decidiria diferente em 5 contratos: os 3 acima, o 10 (envelope cancelado, "Natal das Crianças",
ligado a uma visita de outro dia pelo telefone) e o 895 ("Ballet cisne e Flamingos", ligado à venda 1354, que
foi cancelada; a venda viva 1424, do mesmo dia e do mesmo telefone, está sem contrato).

Limite da auditoria: o dump é de 19/11. Contratos de 20 a 23/11 não entraram; dezembro é o mês das visitas de
Papai Noel, e todo contrato delas sai com o tema "Natal".

## O que muda

Aprovado pelo dono em 23/11 ("Sim, implementa").

1. **Palavra de ocasião não diz qual é a festa.** Entram em `_PALAVRAS_VAZIAS` (`contratos_ops`): `natal`,
   `natalino`, `natalina`, `noel`, `papai`, `mamae`, `pascoa`, `halloween`, `carnaval`, `junina`, `junino`,
   `reveillon` e `criancas` ("Natal das Crianças", "Dia das Crianças"). Com elas, "Natal" e "Papai Noel" deixam
   de ligar por palavra; "Arraiá com o Snoopy" continua ligando por "snoopy". O contrato sem data + telefone
   vai para "A conferir", onde a comercial confirma com um clique (as vendas do dia já aparecem sugeridas, a
   do mesmo telefone primeiro).
2. **Vínculo automático fraco cede ao telefone** (`sincronizar_ops._ceder_ao_telefone`). A cada passada, depois
   dos envelopes e antes da varredura de anexos, o contrato **de evento de hoje em diante** ligado
   **automaticamente** a uma venda que não tem o dia e o telefone dele é conferido de novo: se **uma única
   outra venda viva** do dia tem o telefone, o vínculo passa para ela — o PDF automático sai da venda de antes
   e entra na de agora, e as duas ganham a linha no histórico. Nada muda no que foi ligado, desligado ou
   descartado à mão (FR-005 da 317), no vínculo que já é de data + telefone (mesmo em venda cancelada: dívida
   239), nem em contrato de evento que já passou. Duas vendas com o telefone = ambíguo, não mexe. A passada
   conta `movidos`, e o `clicksign-sincronizar` (a simulação também) mostra o número.
3. **Conserto dos dados.** Na produção, o 944 passa sozinho para a visita 1488 na primeira passada depois do
   deploy. O 965 foi desligado à mão em 23/11 e por isso **não** se religa sozinho: fica em "A conferir" com a
   visita 1525 sugerida. Os envelopes cancelados 934 e 10 e o 895 (venda cancelada) ficam para decisão do dono
   (dívidas 239 e 240).

Refeita a auditoria no espelho com a regra nova: os 3 de "Natal" saem de "só a palavra" para "nada bate", os
11 certos continuam, e a próxima passada passaria exatamente 2 vínculos de venda (944 → 1488 e 965 → 1525).

Não entra: recusar o sinal da palavra quando a venda tem outro telefone (a auditoria mostra 6 vínculos certos
nessa situação).

## Verificação

`verify_317c.py`, contra o espelho da correção, com datas em 2028 como o `verify_317b.py`:

| # | Cenário | O que prova | No código de antes |
|---|---|---|---|
| 1 | Núcleo puro | "Natal", "Papai Noel", "Natal das Crianças", "Páscoa", "Festa Junina" e "Halloween" não têm palavra que diga a festa; "Natal do Snoopy" ainda liga pelo Snoopy | falha |
| 2 | "Natal" num dia em que a única venda com a palavra é um corporativo `NATAL …` de outra cliente | fica "A conferir" (`sem_candidato`) | falha (ligava) |
| 3 | "Papai Noel" com uma só visita de Papai Noel sem telefone no dia | fica "A conferir" | falha (ligava) |
| 4 | "Arraiá com o Snoopy" × `SNOOPY + CHARLIE`; data + telefone com empate pela palavra | continuam ligando | passa |
| 5 | Ligado pela palavra; a venda certa ganha o telefone | a simulação conta 1 vínculo a passar e não grava | falha |
| 6 | A passada seguinte | o vínculo passa para a venda do telefone, o PDF sai de uma e entra na outra, histórico nas duas | falha |
| 7 | Ligado à mão, e outra venda ganha o telefone | não muda (**deve ficar**) | passa |
| 8 | Duas vendas ganham o telefone do contrato | ambíguo, não muda (**deve ficar**) | falha só pela contagem |
| 9 | Contrato de evento que já passou (2001) | não é reavaliado (**deve ficar**) | passa |
| 10 | Segunda passada | nada muda; o vínculo de data + telefone não se mexe | falha só pela contagem |
| 11 | limpeza | registros descartáveis apagados | — |

Resultado em 23/11, no espelho `manto_317c`: **11/11** com a correção e **4/11** com o código de antes;
`verify_317b.py` 12/12 e `verify_317.py` 36/36.

**Isolamento do espelho.** A reavaliação olha todo contrato de hoje em diante, inclusive os reais do espelho —
que o dublê da ClickSign não conhece e o verify não pode mexer. `verify_317.py` (importado pelo 317b e pelo
317c) troca `sincronizar_ops._vinculos_a_reavaliar` por uma versão que só enxerga os contratos do teste.

Ensaio antes do merge: a auditoria e `clicksign-sincronizar --desde` (sem `--aplicar`) contra um dump do dia,
conferindo a contagem de "vínculos que passam para a venda do telefone" contrato a contrato, como na 317b.

## Fora de escopo

- Reescrever os demais sinais da 317b (telefone a um dia, formulário, e-mail): a auditoria não achou erro neles.
- Ligar formulário solto ao evento e juntar fichas duplicadas (dívida já registrada pela 317b).
- Gerar o contrato pela API da ClickSign.
- Nome de documento do fluxo corporativo (`data + razão social + telefone`): o Thermas de dezembro ainda não tem
  contrato na ClickSign; quando tiver, liga por data + telefone se a venda tiver a cliente — hoje não tem.
