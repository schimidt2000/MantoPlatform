# Quickstart — Catálogo Público em React (161)

## Rodar localmente

```powershell
.\scripts\db\run-local.ps1        # backend Flask contra manto_local
npm run dev:public                # frontend do catálogo público, noutro terminal
```

## Roteiro manual

1. `/` (app `public`) — grade geral: conferir itens ativos, capa, nome, categorias; usar a
   busca e os filtros de categoria (client-side, sem reload).
2. `/categorias` — conferir grade só com categorias que têm item ativo, com contagem e foto.
3. `/categoria/<slug>` — conferir itens daquela categoria; testar slug inexistente → página
   "não encontrado".
4. `/<slug>` de um produto com 2+ fotos — trocar de foto pela miniatura e por swipe (touch ou
   arrastar com mouse); conferir cross-fade + altura suave; testar com
   `prefers-reduced-motion: reduce` ativado no SO/navegador → troca deve ser instantânea, sem
   animação. Conferir produtos relacionados e o botão "copiar link".
5. `/lista-desejos` — favoritar 2+ produtos na grade/detalhe, abrir a tela, conferir persistência
   (reload da página) e o botão de enviar por WhatsApp (deve abrir com a mensagem correta).
6. Testar tudo em viewport 320px e 430px (DevTools) — nenhuma tela deve gerar rolagem
   horizontal.
7. Comparar com a tela antiga (`/catalogo/*` no Flask, `app.*`) para os mesmos dados — os
   valores devem ser idênticos.

## Verificação automatizada

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\db\verify_161_catalogo_publico_leitura.py
```

Cobre paridade API×Jinja (itens/categorias/detalhe/relacionados), 404 de slug/categoria
inexistente ou inativo, e que todos os endpoints respondem sem sessão autenticada (rota
pública).

## Frontend

```powershell
npm run typecheck:public
npm run build:public
```
