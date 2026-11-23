# 317c — Contrato não se liga à venda por palavra de ocasião, e o vínculo fraco cede ao telefone

**Branch**: `317c-vinculo-por-tema` (da `main`) · **Created**: 2026-11-23 · **Status**: Rascunho — auditoria
feita e regra proposta; código ainda não alterado · **Migration**: nenhuma · **Nível**: 2 (correção da 317)

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

## O que muda (proposta)

1. **Palavra de ocasião não diz qual é a festa.** Entram em `_PALAVRAS_VAZIAS` (`contratos_ops`): `natal`,
   `natalino`, `natalina`, `noel`, `papai`, `mamae`, `pascoa`, `halloween`, `carnaval`, `junina`, `junino`,
   `reveillon`. Com elas, "Natal" e "Papai Noel" deixam de ligar por palavra; "Arraiá com o Snoopy" continua
   ligando por "snoopy". O contrato sem data + telefone vai para "A conferir", onde a comercial confirma com um
   clique (as vendas do dia já aparecem sugeridas, a do mesmo telefone primeiro).
2. **Vínculo automático fraco cede ao telefone.** A cada sincronização, o documento ligado **automaticamente**
   por sinal que não seja data + telefone é conferido de novo: se data + telefone agora apontam para **uma única
   outra venda viva**, o vínculo passa para ela (com o anexo do PDF e a linha no histórico das duas vendas).
   Nada muda no que foi ligado, desligado ou descartado à mão (FR-005 da 317), nem no vínculo que já é de
   data + telefone.
3. **Conserto dos dados** depois do deploy, com a lista da auditoria refeita contra a produção do dia: 965 →
   1525 e 944 → 1488 passam pela regra 2; 934 e 10 (cancelados na ClickSign) e 895 (venda cancelada) ficam
   para decisão do dono.

Não entra: recusar o sinal da palavra quando a venda tem outro telefone (a auditoria mostra 6 vínculos certos
nessa situação).

## Verificação

`verify_317c.py`, contra o espelho da correção, com datas em 2028 como o `verify_317b.py`:

| # | Cenário | O que prova | Deve falhar? |
|---|---|---|---|
| 1 | Contrato "Natal" num dia em que a única venda com a palavra é um corporativo "NATAL …" de outra cliente | vai para "A conferir" (`sem_candidato`), não liga | **sim, no código de hoje** |
| 2 | Contrato "Papai Noel" com uma só visita de Papai Noel no dia, sem telefone | idem | **sim, no código de hoje** |
| 3 | "Arraiá com o Snoopy" × `SNOOPY + CHARLIE` | continua ligando pela palavra | não |
| 4 | Contrato ligado por palavra; a venda certa ganha o telefone depois | a sincronização seguinte passa o vínculo para ela, com histórico nas duas | **sim, no código de hoje** |
| 5 | Mesmo caso, mas o vínculo foi feito à mão | não muda | não |
| 6 | Vínculo de data + telefone com outra venda do mesmo telefone no dia | não muda | não |
| 7 | `verify_317.py` e `verify_317b.py` | seguem verdes (36/36 e 12/12) | não |
| 8 | limpeza | registros descartáveis apagados | — |

Ensaio antes do merge: a auditoria e uma sincronização simulada (`--desde`, sem `--aplicar`) contra um dump do
dia, conferidas contrato a contrato, como na 317b.

## Fora de escopo

- Reescrever os demais sinais da 317b (telefone a um dia, formulário, e-mail): a auditoria não achou erro neles.
- Ligar formulário solto ao evento e juntar fichas duplicadas (dívida já registrada pela 317b).
- Gerar o contrato pela API da ClickSign.
- Nome de documento do fluxo corporativo (`data + razão social + telefone`): o Thermas de dezembro ainda não tem
  contrato na ClickSign; quando tiver, liga por data + telefone se a venda tiver a cliente — hoje não tem.
