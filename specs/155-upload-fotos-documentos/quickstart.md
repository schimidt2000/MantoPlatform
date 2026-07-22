# Quickstart — Upload de Fotos e Documentos (Talento + Figurino) (155)

## Rodar localmente

```powershell
.\scripts\db\run-local.ps1        # backend Flask contra manto_local
npm run dev:internal              # frontend, noutro terminal
```

## Roteiro manual

1. `/talents/<id>` — como CASTING/SUPERADMIN, enviar foto de rosto, corpo inteiro, documento e
   CNH; conferir preview atualizado sem reload.
2. Reenviar a foto de rosto com outro arquivo — confirmar que substitui (não duplica).
3. Remover a CNH — campo volta a vazio.
4. Como usuário sem papel CASTING/SUPERADMIN, confirmar que os controles de envio/remoção não
   aparecem (e a API recusa com 403 se chamada diretamente).
5. `/figurinos/<id>/edit` — como FIGURINO/SUPERADMIN, enviar foto, girar 90°, remover.

## Verificação automatizada

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\db\verify_155_upload_fotos_documentos.py
```

Cobre paridade API×Jinja para upload/remover (talento: face/full/doc/cnh) e upload/remover/
girar (figurino), incluindo substituição sem duplicar arquivo, no-op de remover campo vazio, e
os gates de papel (CASTING/SUPERADMIN, FIGURINO/SUPERADMIN → 403 para outros papéis).
