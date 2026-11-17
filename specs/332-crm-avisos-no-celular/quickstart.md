# Quickstart — 332 Avisos no celular

## 1. Verificação automática

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
$env:PYTHONUTF8 = '1'; .venv\Scripts\python.exe specs/332-crm-avisos-no-celular/verify_332.py
```

O resultado esperado é tudo `OK`, com zero escapes. `verify_330`, `verify_328` e `verify_325` continuam verdes.

## 2. Tela

Backend e Vite sobem pela worktree, com chaves VAPID de teste (`flask webpush-chaves`), e a tela abre por
`preview_start {url}`. Conferir:
- o painel "Avisos no celular";
- `/manifest.webmanifest` e `/sw.js` servidos;
- desktop e 375×812.

No Browser pane a permissão costuma vir negada: conferir o texto.

## 3. De verdade (pelo dono, depois do deploy)

1. Na máquina do dono, `flask webpush-chaves` gera o par. Colar `WEB_PUSH_VAPID_PUBLICA` e `WEB_PUSH_VAPID_PRIVADA` no
   Render, nunca pelo chat.
2. **No Android ou no computador**: abrir a Plataforma, Conversas → "Avisos no celular" → "Ativar avisos".
3. **No iPhone (iOS 16.4+)**: Compartilhar → "Adicionar à Tela de Início", abrir pelo ícone e ativar.
4. Mandar uma mensagem para o número de teste e conferir que o celular toca e que o toque abre a conversa.
