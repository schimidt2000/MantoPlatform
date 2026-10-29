# Quickstart — validar a 323

## Pré-requisitos

- Worktree `C:\tmp\mp323`, `.local-db-url` copiado, `frontend/node_modules` ligado.
- Migration aplicada no `manto_local`:

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'; flask db upgrade
```

## Verify

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'; python specs/323-nota-pedida-ao-superadmin/verify_323.py
```

Esperado: 12 cenários verdes (tabela da spec). `VERIFY_323_HTML=<arquivo>` grava o e-mail do
cenário 10 para abrir no navegador.

## Portões

```bash
cd frontend && npm run typecheck
```

```bash
ruff check app/calendar/pedido_de_nota_ops.py app/calendar/event_ops.py app/api/agenda_write.py app/api/agenda_read.py app/api/dashboard_service.py app/email_service.py app/models.py app/config.py
```

## Tela (Browser pane, skill `manto-conferir-tela`)

1. Criar evento → ligar "Precisa de nota fiscal" → os dados da nota aparecem; ISS retido sem
   município → erro no campo.
2. Evento existente → "Editar tudo" → ligar o chip → salvar → Home do Superadmin mostra a nota.
3. Card Comercial → ligar → preencher → salvar → leitura mostra os dados.
4. Home do Superadmin (desktop e 375×812): card "Notas a emitir" urgente; copiar discriminação;
   inserir PDF → a linha some.
5. "Ver como" Comercial → o painel some.
