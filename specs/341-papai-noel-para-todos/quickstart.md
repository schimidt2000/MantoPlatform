# Roteiro — 341

## Local (`C:\tmp\mp341`, banco `manto_340`)

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
$env:MANTO_SEM_THREADS = '1'; $env:PYTHONPATH = (Get-Location).Path; $env:PYTHONUTF8 = '1'; $env:FLASK_APP = 'run.py'
C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\python.exe -m flask db upgrade
C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\python.exe specs\341-papai-noel-para-todos\verify_341.py
```

Regressão com as mesmas variáveis: `specs\304-loja-natal-papai-noel\verify_304.py` e
`specs\205-loja-interacoes-virtuais\verify_205.py` (as falhas que já existem na `main` com o espelho
de hoje — 304: V1.2, V1.4, V2.1, V2.3; 205: V8.1 — continuam e não são desta feature).

Tela: página da campanha e do pedido em 375×812 (textos novos, "entregue até …"), gestão da campanha
(campo "Entrega dos vídeos até"). `cd frontend; npm run typecheck`.

## Produção (com o deploy da 340, à noite)

1. Depois do deploy: gestão da campanha do Papai Noel → **Entrega dos vídeos até = 13/12/2026** →
   Salvar.
2. Abrir alo.mantoproducoes.com.br/papai-noel no celular: topo e perguntas falando de qualquer
   idade; cartão do vídeo "entregue até 13 de dezembro".
