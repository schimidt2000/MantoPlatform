# Checklist de requisitos: regressão — Feature 312

**Purpose**: testar se os documentos dizem, sem furo, o que esta entrega NÃO pode quebrar.
**Created**: 2026-10-20 · **Audiência**: autor e revisor antes do `/speckit-tasks`
**Fontes**: [spec.md](../spec.md), [plan.md](../plan.md), [contracts/api.md](../contracts/api.md),
[pesquisa/reconferencia-2026-10-20.md](../pesquisa/reconferencia-2026-10-20.md)

Avaliação em 20/10, como no checklist de visibilidade.

## Portas da 306 e da 306b

- [x] CHK001 As portas de venda que ficam livres para o Superadmin estão identificadas pela regra da 306, sem uma
  segunda lista que possa divergir? [Consistency, Spec FR-011, Session item 3]
- [x] CHK002 A rota do motivo (306b) está nomeada como livre, com o papel que ela já tem? [Completeness, Contracts
  "Livre"]
- [x] CHK003 Há requisito de prova de que a trava não alcança essas portas (o Comercial continua recebendo o 409 da
  306 na venda, não o da trava)? [Measurability, verify cenário 10]
- [x] CHK004 O e-mail de remoção no vivo continua definido como hoje, com controle no verify? [Coverage, verify
  cenário 15]
- [x] CHK005 O sino da 306 (texto, chave, um por dia) está dito como intocado? [Completeness, Spec Fora de escopo]

## O que não é cancelado

- [x] CHK006 O evento marcado e o com pedido de exclusão estão fora de todo filtro E de toda recusa? *Corrigido: o
  cenário 14 cobre também o marcado.* [Coverage, Spec FR-010]
- [x] CHK007 O gate do `assign` e o convite no vivo estão definidos como inalterados? [Completeness, Contracts]

## Payloads iguais

- [x] CHK008 "Mês sem cancelado igual à `main`" está definido com as exceções explícitas (chave `cancelamentos` com
  quantidade 0)? [Measurability, Spec SC-007, verify cenário 22]
- [x] CHK009 Trocar a fonte do `paineis.cancelamentos` pela função única está definido como sem mudança nos números
  de hoje? *Corrigido na FR-034.* [Consistency, Spec FR-034]
- [x] CHK010 A regra da comissão do card sem filtro de vendedor está dita (a soma de hoje)? [Clarity, Research R7]
- [x] CHK011 O principal cancelado continua listando os dias do grupo? [Completeness, Spec FR-008]

## Jinja e bundle velho

- [x] CHK012 As superfícies Jinja tocadas estão enumeradas (Dia, conflito, disponibilidade, despachante, rotas fora
  dele, "Imprimir fichas", `create-ensaio`, `link-parent` e a lista de shows)? [Coverage, Research R2, Spec FR-003]
- [x] CHK013 Está dito que o Jinja não ganha tela, template nem card? [Completeness, Spec Fora de escopo]
- [x] CHK014 Todo campo novo é opcional e neutro quando ausente? [Completeness, Spec Casos de borda]
- [x] CHK015 Os campos que saem (`devolucao` legado, `events[].cancelado` da ficha) estão avaliados contra o bundle
  em produção? *Corrigido: o bundle da 306 só lê o `devolucao` como reserva sem `resumo`; `events[].cancelado`
  ausente = falso.* [Edge Case, Spec Session item 7]

## Verifies vizinhos

- [x] CHK016 Os verifies a rodar de novo estão listados, com a base conhecida do `verify_306` (67/69)? [Completeness,
  Spec Verificação, Quickstart]
- [x] CHK017 O `verify_145` (o Dia com o evento mais recente) tem a pegadinha registrada? [Edge Case, plano 1c §6]
  — vai para o `tasks.md` como nota da regressão.

## Notas

- 17 itens; 3 corrigidos nos documentos (CHK006, CHK009, CHK015). Nenhuma pergunta ao dono.
