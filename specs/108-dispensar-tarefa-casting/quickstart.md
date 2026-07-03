# Quickstart — Dispensar Tarefa de Casting (108)

## Rodar

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
python -m flask db upgrade   # aplica a migration nova
.\scripts\db\run-local.ps1
```

## Roteiro de verificação manual

1. Logado como SUPERADMIN, abrir a home → seção Casting → escolher uma linha pendente →
   clicar "Dispensar" → confirmar no popup → a linha some, contador "N pendentes" e "feito/
   total" atualizam.
2. Abrir o sub-bloco "Dispensadas" → conferir que o cargo aparece com nome, evento, quem/
   quando.
3. Ir na página do evento correspondente → rodar "Sincronizar" (ou aguardar sync automática)
   → voltar à home → confirmar que o cargo **não** reaparece em pendentes.
4. Clicar "Restaurar" no sub-bloco → cargo volta a aparecer em pendentes, contadores
   atualizam de novo.
5. Logado como usuário CASTING (não superadmin) → seção Casting → confirmar que não há
   nenhum botão "Dispensar" nem sub-bloco "Dispensadas".
6. Tentar `POST /roles/<id>/dismiss` diretamente (via script) como usuário não-superadmin →
   `403`.
7. Tentar dispensar um cargo que já tem talento atribuído → nada muda, flash de erro.
8. Duplo clique rápido em "Dispensar" → apenas um registro em `EventLog`, sem erro.

## Verificação automatizada

Script test client (requests fora de `app_context`) cobrindo:
- 403 para não-superadmin em `/roles/<id>/dismiss` e `/restore`.
- Dispensar cargo sem talento → sai de `pending_casting`/contadores da home.
- Dispensar cargo com talento → sem efeito, flash de erro.
- Idempotência: dispensar 2x seguidas não duplica `EventLog` nem quebra.
- Restaurar → volta a contar como pendente.
- **Cenário central**: dispensar um cargo, rodar a função de sync do evento, verificar
  que o cargo continua com `dismissed_at` preenchido (não foi apagado nem recriado) e que
  nenhum cargo duplicado aparece para o mesmo personagem.

## Portões

```powershell
ruff check app/calendar/routes.py app/models.py app/__init__.py
```
