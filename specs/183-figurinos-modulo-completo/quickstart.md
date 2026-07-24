# Quickstart: Reestruturação do Banco de Figurinos

## Rodar localmente

```powershell
# Backend, apontando para manto_local (Postgres)
.\scripts\db\run-local.ps1

# Frontend (staff)
cd frontend
npm run dev:internal
```

Abrir `http://localhost:5173/figurinos` (ou porta configurada pelo Vite), logado como
SUPERADMIN (`joao@mantoproducoes.com.br`) para ver o painel de faltantes.

## Aplicar a migration

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
python -m flask db upgrade
```

## Checklist de verificação manual

1. Grade em desktop widescreen (≥1280px) mostra 5-6 colunas.
2. Card com foto mostra o figurino inteiro, alinhado ao topo, sem corte da cabeça.
3. Card sem foto mostra placeholder no mesmo quadro (grade não desalinha).
4. Rodapé do card mostra nome, nº de peças e data.
5. Botão "Imprimir" abre `/figurinos/<id>/print` em nova aba.
6. Ícone de lápis (só para FIGURINO/SUPERADMIN) leva à edição.
7. Painel de faltantes só aparece para SUPERADMIN, começa fechado, título mostra a contagem.
8. Descartar um item o remove da lista; criar um evento novo com o mesmo personagem faz reaparecer.
9. Associar um item a uma ficha existente vincula os cargos e o item some da lista.
10. Busca por nome filtra a grade; filtro de tag filtra por tag; os dois combinados fazem
    interseção.

## Verificação funcional automatizada

Script `scripts/db/verify_183_figurinos_modulo_completo.py` (test client Flask, requests fora de
`app_context`, contra `manto_local`) cobrindo: criar/editar ficha com tags, listar com faltantes,
dispensar, associar (incluindo 403 para não-SUPERADMIN e 404 de ficha inexistente).

## E2E (Playwright)

```powershell
cd frontend/apps/internal
npx playwright test e2e/figurinos.spec.ts
```
