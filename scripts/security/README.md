# Auditoria de segurança

`overnight_security_audit.py` valida as barreiras de segurança da plataforma contra a cópia
local do banco real (`manto_local`, PostgreSQL) usando o test client do Flask.

## Como rodar

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
$env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\security\overnight_security_audit.py
```

Sai com código **1** se qualquer verificação falhar — dá para usar como portão de CI.
O resumo em Markdown é gravado em `scripts/security/relatorio_seguranca.md` a cada execução.

## O que é verificado

| Seção | Cobertura |
| --- | --- |
| 1 | Flags do cookie de sessão (`HttpOnly`, `SameSite`, `Secure`) nas sessões de Staff e de Talento, mais a config de produção |
| 1b | Isolamento hermético entre as duas sessões, nos dois sentidos |
| 2 | Talento tentando alcançar endpoints do app interno |
| 2b | Anônimo em endpoints autenticados (interno e portal) |
| 2c | Acesso cruzado entre papéis de staff (vendedor × usuários/RH/financeiro/config/logs) |
| 2d | IDOR no portal: escalação, mídia e figurino de terceiros; `id` do cliente ignorado no PATCH |
| 3d | Mapa dos disparadores de e-mail e onde cada um é acionado |
| 3e | Todo caminho de `mail.send(` está sob `try/except` e atrás do gate de notificações |
| 3 / 3b | Flag desligada (log silencioso) e SMTP fora do ar (falha limpa, sem 500) |
| 3f | Caminho de proposta/orçamento, que anexa PDF e não passa por `_send` |
| 3c | Reset de senha não permite enumeração de conta |

## Cuidados ao editar

- **Requests do test client sempre FORA de `with app.app_context()`** — contexto persistente
  vaza o usuário logado entre requests e mascara falhas de RBAC (regra do projeto, `CLAUDE.md`).
- A massa de teste é prefixada por `AUDIT191` e removida no `finally`; o `cleanup()` apaga
  objeto a objeto porque `query.delete()` não limpa a associação `user_roles`.
- O relatório **nunca** grava o valor do cookie de sessão, só seus atributos — é credencial.
- `Secure` fica ausente em dev (HTTP) de propósito; a auditoria confere o valor esperado para o
  ambiente carregado e valida `ProductionConfig` à parte.

## Observações registradas (não são falhas)

- **Staff não tem reset de senha por e-mail.** Um SUPERADMIN define a senha temporária à mão em
  `app/admin/user_ops.py::reset_password`. Só o Portal do Artista tem fluxo self-service.
- **`send_quote_email` não usa `_send`** — precisa anexar PDF, que `_send` não suporta. Ele
  reimplementa o guarda (try/except + `_emails_enabled()`), e a seção 3e verifica essa
  propriedade em cada caminho de envio em vez de exigir uma função única.
