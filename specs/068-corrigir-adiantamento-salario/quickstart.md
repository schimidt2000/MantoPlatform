# Quickstart — Verificação manual da feature 068

**Rodar contra `manto_local`**: `.\scripts\db\run-local.ps1`, abrir `/financeiro/pagamentos`.

## Passo 1 — Adiantamento persiste e desconta (US1)

1. Num salário não pago, clicar em **Adiantamento**, informar o valor (com a máscara padrão) e
   anexar o comprovante; salvar.
2. **Recarregar** a tela de pagamentos (ou filtrar/trocar mês e voltar).
   - ✅ O adiantamento **continua salvo**; o valor a pagar mostra o **líquido**; o item mostra o
     valor adiantado e o link do comprovante.

## Passo 2 — Máscara padrão (US2)

1. Abrir o modal e digitar no campo de valor.
   - ✅ Comporta-se com a máscara padrão de R$ do sistema.

## Passo 3 — Sem regressão (FR-005)

1. Um salário **sem** adiantamento continua sendo regenerado normalmente ao abrir a tela
   (valor/frequência do salário vigente).

## Checklist de qualidade

- [ ] Sem migration.
- [ ] `ruff check` sem erros novos.
- [ ] Verificado o **ciclo completo** contra `manto_local`: salvar → recarregar → persiste.
- [ ] Salários sem adiantamento regeneram normalmente.
