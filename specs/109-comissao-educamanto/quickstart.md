# Quickstart — Comissão EducaManto (109)

## Rodar

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
python -m flask db upgrade   # aplica e5f6a7b8c9d0
.\scripts\db\run-local.ps1
```

## Roteiro de verificação manual

1. Admin → Configurações: conferir select "Responsável EducaManto" apontando para Gabriel
   Lara (backfill da migration); trocar e salvar funciona.
2. Como SUPERADMIN, registrar venda em evento "(EDU) …" com data passada → tela Comissões
   mostra a comissão em nome do Gabriel; planilha de Pagamentos do mês seguinte à realização
   mostra a linha "Comissões" dele com vencimento dia 5.
3. Registrar venda em evento "(EDU) …" com data futura → a comissão NÃO aparece como pagável
   em nenhum mês antes do da realização.
4. Registrar venda em evento comum com vendedora Thays → comissão para Thays no ciclo do mês
   da venda (igual antes).
5. Logar como Gabriel (ENSAIO, responsável): menu mostra Pipeline de Vendas e Comissões;
   pipeline lista só eventos "(EDU…"; comissões mostra só as dele, sem botões de gerência.
6. Logar como outro usuário ENSAIO (Nivaldo): /vendas/ e /financeiro/comissoes → 403;
   menu sem os links.
7. EducaManto → Histórico como superadmin: coluna "Gerado por" preenchida; filtros de
   período e de usuário funcionam. Como COMERCIAL: sem coluna/filtro de usuário (igual à
   calculadora).

## Verificação automatizada

Script test client (requests fora de `app_context`) cobrindo:

- Venda em evento EDU (data passada) → CommissionPayment com `seller_id` = responsável e
  `payable_from` = data do evento; aparece na planilha do mês seguinte à realização.
- Venda em evento EDU (data futura) → não listado como pagável na planilha do mês seguinte
  à VENDA.
- Venda em evento comum → beneficiário = vendedor, `payable_from IS NULL`, ciclo pelo mês da
  venda (regressão FR-005).
- EDU sem responsável configurado → cai na regra comum (FR-006).
- RBAC: responsável acessa /vendas/ (só EDU na lista) e /financeiro/comissoes (só as dele);
  ENSAIO não-responsável → 403 nas duas; COMERCIAL segue vendo tudo.
- Histórico EducaManto: superadmin vê "Gerado por" + filtro user_id funciona; não-superadmin
  não vê; filtros de período funcionam.
- Idempotência: salvar venda 2× não duplica CommissionPayment.

## Portões

```powershell
ruff check app/constants.py app/models.py app/financeiro/routes.py app/calendar/routes.py app/admin/routes.py app/__init__.py app/educamanto/routes.py
```
