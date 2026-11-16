# Quickstart — 344

## Verificar
```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()   # manto_344
$env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
$env:PYTHONPATH = (Get-Location).Path
python specs\344-loja-visitas-e-privacidade\verify_344.py     # 18 cenários
python specs\310-pagamento-loja-virtual\verify_310.py          # regressão (e 340, 341, 310b, 205)
cd frontend; npm run typecheck
```

## Conferir na tela (Browser pane)
1. Loja, 375×812: `/catalogo/v/<slug>?origem=instagram` — formulário com "Seu nome", caixinha
   desmarcada, linha de privacidade com link; `/catalogo/v/privacidade` legível.
2. Com `meta_pixel_id` vazio: nenhum aviso de cookies, nenhuma requisição a `connect.facebook.net`.
   Com um ID de teste: aviso aparece; "Recusar" não carrega nada; "Aceitar" carrega o `fbevents.js`.
3. Sistema interno: campanha → card "Visitas e vendas" com a visita do passo 1 em Instagram e os links
   com "Copiar"; Configurações → campo do pixel; Clientes → ficha com o aceite.

## Em produção, depois do deploy
- Abrir `alo.mantoproducoes.com.br/papai-noel?origem=teste-deploy` e ver +1 em "Outro" no card.
- Sondar `GET /api/virtuais/rastreamento` → JSON.
