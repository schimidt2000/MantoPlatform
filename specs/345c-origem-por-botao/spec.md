# 345c — Origem do tema por botão, não por lista

**Branch**: `345c-origem-por-botao` · **Created**: 2026-11-24 · **Status**: EM PRODUÇÃO desde 24/11/2026 (tarde;
só frontend, sem queda) · **Migration**: nenhuma

## O pedido

O dono, em 24/11: "minha funcionária Gabi vai começar a classificar agora os temas e licenças. Para ser mais
rápido, é melhor que fosse um botão e não uma dropdown list. Consegue fazer essa troca rápida e já fazer o
push".

São 476 temas não classificados. Na lista, cada tema custava dois toques (abrir e escolher).

## O que muda

Só `frontend/apps/internal/src/pages/MarketingTemasPage.tsx`, na linha de cada tema de `/marketing/temas`:

- O `<select>` de origem vira um grupo de botões: **Autoral** e **Licenciado**. Um toque marca.
- A origem atual fica preenchida (`aria-pressed`); tocar nela de novo não faz nada.
- **Não classificado** é o estado de partida e só aparece como botão em tema já marcado, para desfazer.
- Mesma chamada de antes (`PATCH /api/marketing/temas-licenca/<id>` com `licenca_origem`). Regras do servidor
  intactas: autoral confirmado sai liberado, licenciado sai não liberado e só o Superadmin libera.

Os filtros do topo continuam em lista.

## Verificação

- `npm run typecheck` limpo nas três SPAs.
- Tela aberta em 375px contra o espelho `manto_lote`: 50 linhas com o grupo de botões, nenhum `<select>` na
  lista, sem rolagem lateral; um toque em "Autoral" gravou, o selo virou "Liberado" e "Não classificado"
  apareceu como botão de desfazer.
- Sem `verify_345c.py`: nenhum comportamento do servidor muda.

## Fora de escopo

- Atalho de teclado e marcação em lote por origem.
- Os filtros do topo e a confirmação em lote das sugestões.
