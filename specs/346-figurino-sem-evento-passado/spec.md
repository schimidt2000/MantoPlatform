# 346 — O painel de Figurino da Home não lista evento que já passou

**Branch**: `346-figurino-sem-evento-passado` · **Created**: 2026-11-16 · **Status**: Pronto na branch,
sem push (`verify_346.py` 4/7 antes, 7/7 depois; tela aberta no espelho) · **Migration**: nenhuma

## O pedido

O dono, com o print do painel "👗 Figurino" da Home (131 pendentes, 50 urgentes, o primeiro de
11/11): "Depois que passou o evento não faz mais sentido aparecer aqui como pendente."

## Por que acontecia

`compute_figurino_tasks` (`app/api/dashboard_service.py`) usa o mesmo corte dos outros painéis de
operação, `dashboard_cutoff()`, que vale o `release_date` (01/06/2026 em produção). Com isso o painel
juntava todo figurino não marcado desde junho, e o evento passado ainda ganhava a etiqueta vermelha
"URGENTE" (o `getUrgency` da tela marca tudo que está a 2 dias ou menos, inclusive no passado).

## O que muda

- **`corte_figurino(cutoff)`**: o corte do painel de Figurino passa a ser o mais tarde entre o
  `release_date` e a meia-noite de hoje no relógio de São Paulo (`now_sp`). O evento de hoje continua
  na lista até o fim do dia — é o mais urgente que existe. Mesma régua que a 231 adotou nas
  confirmações ("ninguém cobra confirmação de evento de junho").
- `pending`, `total` e `done` do painel usam o mesmo corte, para a conta fechar.
- **O Casting não muda**: vaga sem talento em evento passado continua na lista de propósito, porque
  o pagamento depende da escala registrada (decisão da 308). Ensaio, dispensados e cancelados a
  avisar também ficam como estão.
- `verify_308.py`: o cenário 6 (figurino sem 🟧/🟠) volta o relógio do painel ao `release_date`
  para seguir provando o filtro da 308 com a janela antiga. Com o dump de 16/11 ele para na
  pré-condição ("o espelho não tem figurino pendente em evento 🟧/🟠", nem desde 01/06) — é dado,
  não regressão: a consulta da pré-condição é SQL puro.

## Verificação

`verify_346.py` no espelho `manto_346` (dump de 16/11 02h + `flask db upgrade` até `e344a1b2c3d4`),
porque o `manto_local` está parado em 20/10 numa migration do CRM sem push:

1. Nenhum item de `figurino.pending` do `GET /api/dashboard` começa antes de hoje 0h (SP).
2. Os ids e o `total` batem com o SELECT direto por conexão separada, com o corte novo.
3. Fronteira com relógio fixo num dia D do espelho: com "agora" = D às 23h59, a vaga do evento de D
   (que já aconteceu horas antes) fica; a do dia anterior sai.
4. `release_date` no futuro continua mandando: nada antes dele.
5. O Casting não muda: vaga de evento passado continua em `casting.pending`.
6. DEVE FALHAR: CASTING sem o papel FIGURINO recebe `figurino: null`.
7. Limpeza.

## Fora de escopo

- Casting, ensaio e as outras listas da Home.
- A etiqueta "URGENTE" do `getUrgency` (`SectorPanel.tsx`) para data passada: com o corte novo o
  painel de Figurino não recebe mais data passada.
- O `date.today()` do `dashboard_cutoff` com `release_date` vazio (dívida 52 do `docs/05`).
