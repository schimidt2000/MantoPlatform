# Quickstart — Revisão de Mídia (170)

## Rodar localmente

```powershell
.\scripts\db\run-local.ps1
npm run dev:internal
```

## Roteiro manual

1. `/revisao` — listar espaços como criador, revisor e Superadmin.
2. Criar um espaço com vídeo, imagem e PDF, revisores selecionados.
3. Adicionar material, trocar revisores.
4. Abrir cada tipo de material, comentar ancorado (timecode/página/posição), listar, resolver/
   reabrir, excluir comentário.
5. Substituir um material (mesmo tipo) e conferir o histórico de versão; finalizar um material.
6. Excluir um espaço e confirmar remoção dos arquivos.
7. Como usuário sem acesso, confirmar 403 em cada ação restrita.

## Verificação automatizada

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\db\verify_170_revisao_midia_react.py
```
