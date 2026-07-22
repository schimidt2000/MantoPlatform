# Quickstart — Leitura e Gestão de Talentos e Figurino (154)

## Rodar localmente

```powershell
.\scripts\db\run-local.ps1        # backend Flask contra manto_local
npm run dev:internal              # frontend, noutro terminal
```

## Roteiro manual

1. `/talents` — buscar por nome, aplicar um filtro (ex.: tamanho), abrir a aba Pendentes.
2. Abrir o perfil de um talento — conferir contato/aparência/documentos/histórico/total de
   cachê.
3. Como CASTING/SUPERADMIN: aprovar um pendente (vira ativo), rejeitar outro (some da lista).
4. Editar um talento (telefone, por exemplo) e salvar; como SUPERADMIN, editar o CPF.
5. Salvar uma anotação interna com nível de alerta.
6. `/figurinos` — conferir o aviso de "personagens sem ficha"; criar uma ficha nova com
   peças; editar a lista de peças de uma existente; excluir uma ficha.

## Verificação automatizada

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\db\verify_154_talentos_figurino.py
```

Cobre paridade API×Jinja para os 9 fluxos (busca/filtros, perfil, aprovar, rejeitar, editar
incl. CPF-só-SUPERADMIN, anotação, listar/criar/editar/excluir ficha de figurino) e os gates
de papel (CASTING/SUPERADMIN, FIGURINO/SUPERADMIN).
