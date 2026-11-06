# Quickstart — 335 Linha do tempo da ficha e funil das conversas

## 1. Verificação

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
$env:PYTHONUTF8 = '1'; .venv\Scripts\python.exe specs/335-crm-linha-do-tempo/verify_335.py
```

Esperado: todos os cenários OK, zero escapes de rede. Regressão: `verify_334`, `verify_333`, `verify_332`,
`verify_330`, `verify_328` e `verify_325`.

## 2. Tela (pela worktree, portas próprias)

1. Backend da worktree numa porta livre (Google dublado, Conversas ligadas com valores falsos, envio travado) e o
   Vite com proxy para ela.
2. Semear dados descartáveis (`t335-`): conversas em etapas diferentes, de dois vendedores, com e sem anúncio; uma
   ficha com todos os marcos.
3. Conferir, em desktop e em 375×812:
   - `/funil`: as seis etapas, as porcentagens, os filtros de canal e campanha, a tabela por vendedor/campanha/canal e a
     lista "Pararam em …" com "Abrir conversa";
   - `/clientes/<id>`: o cartão "Linha do tempo" com os marcos e os links;
   - o item "Funil" no menu Comercial só com as Conversas ligadas.
4. Apagar os dados de teste.
