# Quickstart — Escrita da Planilha de Pagamentos em React (160)

## Rodar localmente

```powershell
.\scripts\db\run-local.ps1        # backend Flask contra manto_local
npm run dev:internal              # frontend, noutro terminal
```

## Roteiro manual

1. `/financeiro/pagamentos` (React) — como Financeiro/Superadmin, marcar um cachê como "pago" pelo
   seletor de status na linha; conferir que o total do mês atualiza sem recarregar a página.
2. Marcar uma comissão agrupada (vendedor/período) como paga; conferir que todas as comissões
   daquele grupo mudam junto.
3. Selecionar vários itens de tipos diferentes (checkbox por linha), aplicar "marcar como pago" em
   massa; conferir a contagem de itens atualizados.
4. Selecionar cachês + um gasto para exclusão em massa; conferir que só o cachê é excluído e o gasto
   aparece como ignorado, com o motivo.
5. Em um lançamento de salário, registrar um adiantamento com valor e comprovante; conferir que o
   valor líquido a pagar diminui e o adiantamento aparece na lista. Tentar sem comprovante e com
   valor que excede o salário — conferir que ambos são recusados com mensagem clara.
6. Excluir o adiantamento criado; conferir que o valor líquido volta ao original.
7. Clicar em "Exportar CSV"; conferir que o arquivo baixado tem as colunas e linhas esperadas para
   o mês selecionado.
8. Como usuário sem papel Financeiro/Superadmin, confirmar que todas as ações acima são recusadas
   (403) e não aparecem habilitadas na tela.

## Verificação automatizada

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\db\verify_160_escrita_pagamentos_financeiro.py
```

Cobre, contra `manto_local`: marcar status (cada `item_type`, inclusive rejeição de status inválido
por tipo), ação em massa (status e delete, inclusive itens ignorados), adiantamento (criação com
sucesso, cada rejeição — valor zero, soma excede salário, sem comprovante, comprovante grande —, e
exclusão), export CSV (conteúdo e cabeçalhos de resposta), e o gate de acesso (403 fora de
Financeiro/Superadmin) em todas as rotas.
