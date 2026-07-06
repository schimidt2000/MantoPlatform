# Quickstart — Gastos Recorrentes (110)

## Rodar

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
python -m flask db upgrade   # aplica f6a7b8c9d0e1
.\scripts\db\run-local.ps1
```

## Roteiro de verificação manual

1. Como FINANCEIRO/SUPERADMIN: menu → Gastos Recorrentes → cadastrar "Conta de Luz"
   (variável, faixa 400–600, dia ≤ hoje), "Advogado" (débito automático, R$ 1.000, dia 5) e
   "Adobe" (assinatura, R$ 120, cartão "Nubank", dia 12).
2. Home → bloco "Contas recorrentes": alerta "Conta de Luz — aguardando valor". Advogado e
   Adobe NÃO aparecem.
3. Preencher Conta de Luz (ex.: R$ 700 — fora da faixa → destaque) com PIX e vencimento →
   alerta muda para "a pagar"; item aparece em Pagamentos do mês com PIX copiável.
4. Marcar pago (na planilha ou na tela) → alerta some; histórico registra quem/quando.
5. Painel financeiro do mês: despesas incluem 700 + 1000 + 120 (linha Gastos recorrentes).
6. "Pular mês" numa variável sem conta → alerta some, histórico mostra "pulado".
7. Desativar Adobe → não gera lançamento no mês seguinte. Tentar excluir Advogado (com
   lançamento) → bloqueado; excluir conta recém-criada sem lançamento → ok.
8. Como usuário CASTING: home sem bloco de recorrentes; /gastos/recorrentes → 403; /gastos/
   (extras) continua funcionando igual.

## Verificação automatizada

Script test client (requests fora de `app_context`) cobrindo:

- CRUD das contas (3 tipos) + RBAC 403 (papel sem financeiro) + link ausente no menu.
- Alerta home: variável com dia atingido aparece p/ FINANCEIRO/SUPERADMIN, não p/ outros;
  antes do dia esperado não aparece; após preencher vira "a pagar"; após pagar some.
- Preencher → entry `a_pagar` (fora da faixa detectado) → item `recurring` na planilha →
  set-status pago → paid_at preenchido.
- `ensure_recurring_entries`: fixos ganham `registrado` (1 por mês, idempotente 2×);
  `registrado` NUNCA vira item na planilha nem alerta.
- Painel financeiro: soma dos lançamentos do mês inclui variável preenchida + fixos.
- Pular mês → `pulado`, sem item na planilha, fora da soma do painel.
- Excluir conta com lançamento bloqueado; sem lançamento ok.
- Regressão: /gastos/ (extras) — registrar gasto continua funcionando (FR-011).

## Portões

```powershell
ruff check app/models.py app/gastos/routes.py app/financeiro/routes.py app/__init__.py
ruff format <arquivos novos>
```
