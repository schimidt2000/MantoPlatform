# Quickstart — Feature 345

## Pré-requisitos

- Banco `manto_345` (dump de 16/11) com `flask db upgrade` até `f345c0a1b2d3`; URL em `C:\tmp\mp345\.local-db-url`.
- Ambiente: `$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development';
  $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'`.

## Verificar

```powershell
cd C:\tmp\mp345
..\..\Users\schim\Desktop\Manto_Platform\.venv\Scripts\python.exe specs\345-marketing-integrado\verify_345.py
```

O esperado são 17 cenários verdes. Os 5 marcados "deve falhar" respondem 403/409/422, como no contrato
([contracts/api-345.md](./contracts/api-345.md)).

## Conferir as telas (Browser pane, backend e Vite da worktree em portas próprias)

1. `/marketing/desempenho`: o bloco "Por frente" com o estado de cada frente, as campanhas sem frente com o seletor e
   o Google "sem conexão".
2. `/marketing/temas`: os filtros, a confirmação em lote e o Marketing sem o botão "Liberar" num licenciado.
3. `/marketing/decisoes` em 390 px: Aprovar e Recusar (Superadmin) e o diário com "a reavaliar".
4. `/marketing/painel`: o card de anúncio com o selo e o diálogo com o briefing. O tema não liberado mostra erro no
   campo.

## Rodada da rotina (depois do deploy)

Skill `marketing-auditor`: lê a Meta e o Google pelos conectores, faz `POST /run` e `POST /anuncios`, executa as
propostas aprovadas, reavalia o diário, sugere licenças e abre os pedidos e as propostas novas. O relatório vai por
e-mail.
