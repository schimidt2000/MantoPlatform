# Quickstart — Feature 322

## Pré-requisitos

- Worktree `C:\tmp\mp322`, `.local-db-url` copiado, `.venv` do repo principal.
- `manto_local` migrado: `flask db upgrade` com as três env vars (CLAUDE.md §4).

## Verify

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\python.exe specs\322-o-que-o-casting-fecha\verify_322.py
```

Esperado: todos os cenários verdes. Antes do núcleo, 17, 18 e 22 (e os que dependem das colunas
novas) ficam vermelhos — é a prova de que o verify testa a mudança.

## Tela

1. `preview_start` do `internal` (`.claude/launch.json`), login de superadmin do `manto_local`.
2. Abrir um evento criado pelo verify com `VERIFY_322_MANTER=1` (ou um evento futuro com orçamento):
   - Casting: cada personagem mostra a linha do perfil abaixo do nome.
   - Equipe de apoio: Coordenador, Técnico de Som e Maquiador com "adicionado pelo sistema".
   - Talento pré-escalado com "inserido pelo comercial".
3. Repetir em 375×812.
4. Editar o evento como comercial: caixa "Maquiagem" travada com a explicação; como superadmin, livre.

## Depois do deploy

- Criar um evento de teste com maquiagem à mão, conferir a vaga, cancelar e apagar (ou pedir ao dono
  que confira no primeiro evento real).
- Avisar a equipe (skill `manto-novidades`): Casting (o perfil e as marcas), Comercial (a maquiagem
  é definida na criação; depois só o superadmin muda).
