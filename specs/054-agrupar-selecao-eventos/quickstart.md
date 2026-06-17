# Quickstart — Verificação manual da feature 054

Roteiro para validar a nova seleção de eventos no agrupamento, no app real
(`python run.py`), logado como COMERCIAL, FINANCEIRO ou SUPERADMIN.

> Pré-requisito: ter alguns eventos não-ENSAIO cadastrados em datas variadas (inclusive
> distantes entre si) e pelo menos um com valor de venda preenchido.

## Passo 1 — Busca alcança eventos de datas distantes (FR-001, FR-002, SC-001)

1. Abra um evento (ex.: o do dia 27) e vá à seção **Comercial → Agrupar**.
2. Confirme que a lista de candidatos mostra eventos **fora da janela de ±3 dias**
   (eventos de semanas/meses depois aparecem).
3. Digite parte do nome (ou a data) de um evento distante no campo de busca.
   - ✅ A lista filtra em tempo real (sem recarregar), acento-insensível.
4. Apague a busca.
   - ✅ A lista inicial reaparece (eventos mais recentes primeiro) — FR-005.

## Passo 2 — Marcar vários e agrupar de uma vez (FR-003, SC-002)

1. Marque os checkboxes de **dois ou mais** eventos.
2. Na escolha do principal, deixe o evento atual selecionado (padrão) — FR-004.
3. Clique em **Agrupar eventos**.
   - ✅ O botão desabilita e mostra estado de carregamento (anti-duplo-envio).
   - ✅ Todos os marcados viram satélites do evento atual numa só operação.
4. Recarregue o evento principal.
   - ✅ A seção lista todos os satélites recém-agrupados.

## Passo 3 — Escolher outro evento como principal (FR-004)

1. Em um evento, marque 2 outros eventos.
2. Na escolha do principal, selecione **um dos marcados** (não o atual).
3. Confirme.
   - ✅ O evento escolhido vira o principal; o atual e o outro viram satélites dele.

## Passo 4 — Proteções de integridade (FR-006, FR-007, US3)

1. Observe um evento que já é satélite/principal de outro grupo na lista.
   - ✅ Aparece **desabilitado** com etiqueta "já agrupado" (não dá para marcar).
2. Confirme sem marcar nada.
   - ✅ Aviso "selecione ao menos um evento"; nada muda no banco.
3. Marque um evento que tem **valor de venda** preenchido, sem marcar a confirmação.
   - ✅ O sistema exige a confirmação de substituição antes de zerar (FR-008).
4. Após um erro de validação:
   - ✅ A seleção marcada e a escolha de principal **não** se perdem (FR-010).

## Passo 5 — ENSAIO nunca aparece (FR-006)

1. Confirme que nenhum evento do tipo **ENSAIO** aparece na lista de candidatos.

## Passo 6 — Equivalência com a 053 (FR-012, SC-005)

1. Agrupe via nova tela e abra o **Painel Financeiro** (`/financeiro/`) no período.
   - ✅ O grupo conta como **1 venda**; o CPV soma os cachês dos satélites no principal.
2. Desagrupe um satélite (botão "Desfazer agrupamento").
   - ✅ Ele volta a ter campos comerciais próprios e editáveis (comportamento da 053).

## Checklist de qualidade (Portões da constituição)

- [ ] `ruff check app/calendar/routes.py` sem erros novos.
- [ ] `ruff format --check` nos arquivos tocados (ou formatação aplicada).
- [ ] Comportamento conferido no app real (Princípio IV) — passos 1 a 6.
- [ ] Sem migration (modelo inalterado).
