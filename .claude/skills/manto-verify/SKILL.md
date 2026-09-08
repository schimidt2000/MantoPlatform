---
name: manto-verify
description: >
  Escrever, rodar e diagnosticar um verify_NNN.py da Manto contra o manto_local (cópia local da
  produção). Use ao criar ou rodar a verificação de uma feature/hotfix, quando um verify "passa
  verde" sem testar nada, ou quando o dono pedir "verifica", "roda o verify", "/manto-verify".
  Regra normativa: constituição, Princípio VIII. Procedimento completo: DEVELOPMENT.md §Escrever
  um verify.
---

# manto-verify — verificação funcional contra o manto_local

## Antes de rodar qualquer coisa

1. `manto_local` de pé e atualizado (`.\scripts\db\refresh-local-db.ps1` se estiver dias atrás
   da produção; `scripts/db/` é local, não versionado).
2. As três variáveis, SEMPRE — o `.env` não é lido por `python script.py`:
   ```powershell
   $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
   .venv\Scripts\python.exe specs\NNN-nome\verify_NNN.py
   ```
3. O espelho traz o token do Google e as credenciais de e-mail REAIS. As travas `_suppress_mail`
   e `_suppress_calendar_invites` (`app/config.py`) cobrem e-mail e convite; qualquer outra escrita
   externa precisa da própria trava (Princípio XIV). O verify começa conferindo
   `app.config["MAIL_SUPPRESS_SEND"] is True`.

## Esqueleto (copie de `specs/266-costuras-funil/verify_266.py`)

- Docstring com a lista de cenários e o comando para rodar.
- `sys.stdout.reconfigure(encoding="utf-8")` — console do Windows em cp1252.
- `REPO_ROOT` no `sys.path`; `FLASK_ENV` e `DATABASE_URL` com `setdefault`.
- `app = create_app(); app.config["TESTING"] = True; app.config["RATELIMIT_ENABLED"] = False`.
- `_engine_externo = create_engine(DATABASE_URL)` + `_no_banco(sql)`: **toda asserção de escrita
  lê por essa conexão** — o autoflush da sessão do app esconde falta de commit (hotfix 257: cinco
  POSTs respondiam 2xx sem `commit()` e a varredura pelo test_client deu "tudo ok").
- `cenario(nome, fn)` acumulando PASS/FAIL; `main()` com `try/finally` e a limpeza como último
  cenário; saída `N/N OK` e código de retorno 1 se algo falhou.
- Prefixo único nos dados descartáveis (`__vNNN_`) para a limpeza achar tudo.

## Como um verify passa verde sem testar nada (os cinco modos conhecidos)

1. **Sessão montada à mão não autentica.** `session_transaction()` com `_user_id` devolve 401.
   Crie usuário descartável com `set_password()` e logue por `POST /api/auth/login`.
2. **`app.app_context()` segurado por fora das requisições faz o `g` sobreviver** — o login da
   preparação vaza e `/api/auth/me` responde 200 até para cookie inválido. Setup de banco dentro
   do contexto; requisições HTTP FORA dele.
3. **`test_client()` reescreve o `Cookie` a partir do próprio jar**: jar vazio APAGA o cabeçalho
   que você montou; jar cheio deduplica por nome. Teste de cookie (duplicado, domínio, ordem)
   exige `app.test_client(use_cookies=False)`.
4. **Autoflush** (acima): conferir pela sessão que escreveu não prova nada.
5. **Sem cenário negativo** não se sabe se o gate existe: todo verify de autorização tem um papel
   sem permissão tentando e recebendo 403/404.

## Limpeza que não estoura

```python
finally:
    db.session.rollback()                      # a sessão pode estar suja de um erro anterior
    user = User.query.filter_by(email=EMAIL_DESCARTAVEL).first()
    if user:
        user.roles.clear()                     # delete em massa estoura a FK de user_roles
        db.session.delete(user)
    db.session.commit()
```

## Fixtures que não explodem

- **Elenco**: nunca crie `EventRole` com `character_name` inventado — o sync do Google reconcilia
  o elenco contra os personagens do título e APAGA a role, chamando `send_removal_email` ANTES
  (artista real recebe "sua participação foi cancelada"). Assuma role existente com
  `talent_id IS NULL`.
- **Agenda**: data distante (`2029-…`) isola cenários de evento; excluir show cascateia para os
  ensaios.
- **Formulário público**: `RATELIMIT_ENABLED = False` (o submit é 10/hora).
- **Distância/Maps**: `SiteSetting.manto_address` no espelho costuma ter lixo de verify antigo →
  400 "Endereço não encontrado"; `google_maps_api_key` vazia (vem do `.env`, que script cru não lê).
- A senha do SUPERADMIN local muda a cada verify: redefina, não peça.

## Depois de verde

Portões da constituição: `cd frontend && npm run typecheck`, `ruff check` nos tocados, tela
aberta (skill `manto-conferir-tela`), docs por fonte única (`docs/00` §10).
