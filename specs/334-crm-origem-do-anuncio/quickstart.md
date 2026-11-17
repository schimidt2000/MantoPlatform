# Quickstart — 334 De qual anúncio veio cada cliente

## 1. Verificação automática

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
$env:PYTHONUTF8 = '1'; .venv\Scripts\python.exe specs/334-crm-origem-do-anuncio/verify_334.py
```

Tudo `OK`, zero escapes. `verify_325`, `verify_328`, `verify_330`, `verify_332` e `verify_333` continuam verdes.

## 2. Tela

Pela worktree, em portas próprias, com dados de teste: uma conversa com contato por anúncio, uma ficha com origem e o
Desempenho com uma campanha e um retorno. Conferir o cabeçalho da conversa, a ficha e a tabela de campanhas, em
desktop e 375×812.

## 3. De verdade (pelo dono, depois do deploy)

1. No Gerenciador de Negócios, dar ao usuário do sistema do WhatsApp a permissão de leitura de anúncios (`ads_read`) e a
   conta de anúncios da Manto. Ou criar outro token e colar em `META_ANUNCIOS_TOKEN`.
2. Clicar num anúncio "enviar mensagem" da Manto e mandar uma mensagem.
3. Conferir na conversa "Veio do anúncio…", na ficha a origem e a campanha, e no Desempenho o lead na campanha.
