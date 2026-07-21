# Quickstart — escrita de casting (146, US1)

Reaproveita a infra das features 144/145. Novo: 1 endpoint de escrita, 1 extração de handler,
o form de escalar no detalhe do evento React.

## Dev
```powershell
.\scripts\db\run-local.ps1            # Flask contra manto_local
npm run dev:internal                  # front (proxy /api), http://localhost:5173
```
Abrir um evento em `/events/:id`; no bloco de elenco, escalar um talento a um cargo (só aparece
se o papel tiver casting).

## Verificação (o núcleo)
`scripts/db/verify_146_casting_write.py` (gitignored), contra `manto_local`, com `send_async`
mockado (nenhum e-mail real):
- Escalar via API produz o estado esperado (talento, cachê ≤ cap p/ não-superadmin,
  assigned_at, invite=pending, figurino resetado, EventLog, 1 convite capturado).
- **Paridade**: a mesma entrada pelo caminho Jinja (test client + form) num cargo gêmeo produz
  estado idêntico.
- 403 (papel sem casting), 404 (role inexistente), idempotência (reenvio não duplica linha).
- Coexistência: o handler Jinja `_handle_assign_casting` segue funcionando (o POST de
  `/events/<id>` continua respondendo).
Front: `tsc --noEmit` + `vite build` limpos.

## Paridade (aceite)
Escalar o mesmo talento com o mesmo cachê, no mesmo cargo, pela API e pelo Jinja, deixa
`event_roles` + `EventLog` no mesmo estado.
