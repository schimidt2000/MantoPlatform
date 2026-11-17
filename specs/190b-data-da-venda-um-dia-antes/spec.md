# 190b — "Data da venda" um dia antes no detalhe do evento

**Branch**: `lote-1711` (entra no lote de 17/11 com a 345b e as 348–351) · **Created**: 2026-11-17 ·
**Status**: Pronto no lote · **Migration**: nenhuma

## O pedido

A 348, conferindo a aba Comercial, viu a venda de 17/11 aparecer como "16/11". O dono pediu para corrigir no lote
de 17/11 ("pode publicar 19h", resposta à pergunta que incluía a correção da data).

## O que muda

`formatDay` (`frontend/apps/internal/src/components/EventDetail/parts.tsx`), herdado da feature 190, fazia
`new Date("2026-11-17")`. O navegador lê a data pura como meia-noite UTC, e em São Paulo isso ainda é 16/11, às 21h.

- Data pura (`AAAA-MM-DD`) passa a ser formatada pelo texto, como já fazem `formatarDataGasto` e `dataCurta`
  (armadilha 1 do `docs/00` §6).
- Data com hora continua pelo `Date`, no fuso de quem olha.

Também corrige as outras datas puras do detalhe que usam a mesma função: a data de emissão da nota (Financeiro) e
a data do gasto (gastos vinculados).

## Verificação

- O formato sai pelo texto ("2026-11-17" → "17/11/2026"), e a data com hora sai igual ao que saía antes. Conferido
  com `node` contra a função.
- `npm run typecheck`.
- Detalhe de um evento com venda no `manto_local`: a "Data da venda" igual à gravada no banco.

## Fora de escopo

- Outras telas com `new Date(dataPura)`: não foram procuradas aqui.
