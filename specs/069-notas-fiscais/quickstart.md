# Quickstart — Verificação manual da feature 069

**Rodar contra `manto_local`**: `.\scripts\db\run-local.ps1`.

## Passo 1 — Tarefa de emissão (US1)

1. Num evento, marcar "com nota fiscal", informar o valor da venda.
2. Adicionar uma nota (valor + data) **sem** arquivo; salvar.
   - ✅ A nota fica **a emitir** e aparece na lista de notas a emitir do super admin (dashboard
     financeiro) e no badge do home.
3. Como super admin, subir o arquivo e marcar **emitida**.
   - ✅ A nota some das pendências e fica registrada como emitida (com arquivo/data).
4. Em outra venda, anexar o arquivo da nota já na venda.
   - ✅ A nota nasce **emitida** (não vira tarefa).

## Passo 2 — Múltiplas notas (US2)

1. Evento de R$10.000 com nota: registrar NF1 R$5.000 em 10/06 e NF2 R$5.000 em 10/07.
   - ✅ As duas aparecem; soma R$10.000.
2. Deixar a soma ≠ total.
   - ✅ Sistema **sinaliza** a divergência (não bloqueia).
3. Remover uma nota.
   - ✅ Sai da lista, das tarefas e dos custos.

## Passo 3 — Custo de nota por mês de emissão + detalhe (US3)

1. Com NF1 emitida em junho e NF2 em julho (16%): abrir o painel em junho.
   - ✅ Custo de nota de junho = R$800; detalhe lista evento/nota/data/custo.
2. Trocar período para julho.
   - ✅ Custo = R$800 (NF2).

## Passo 4 — Sem regressão (FR-007)

1. Conferir a DRE/balanço do período.
   - ✅ `impostos`, `receita líquida`, `EBITDA` etc. iguais ao comportamento atual (competência por
     data do evento).

## Passo 5 — Migração (FR-008)

1. Evento legado com `invoice_file`/`invoice_due_date`.
   - ✅ Após a migration, aparece como **uma nota** (emitida se tinha arquivo, senão a emitir),
     preservando arquivo e data.

## Checklist de qualidade

- [ ] Migration manual cria `event_invoices` e migra a nota única (065).
- [ ] `ruff check` sem erros novos.
- [ ] Verificado o ciclo completo contra `manto_local`.
- [ ] DRE inalterada (sem regressão).
- [ ] Máscara BR nos valores das notas.
