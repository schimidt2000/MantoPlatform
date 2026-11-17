# Quickstart — 330 Instagram Direct

O contrato está em [contracts/api.md](contracts/api.md) e as tabelas em [data-model.md](data-model.md).

## 1. Verificação automática (sem Meta)

Na worktree (`C:\tmp\mp330`):

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
$env:PYTHONUTF8 = '1'; .venv\Scripts\python.exe specs/330-crm-instagram-direct/verify_330.py
```

O resultado esperado:
- todos os cenários `OK`, inclusive os que **devem** falhar;
- zero escapes de rede;
- `verify_328.py` e `verify_325.py` continuam verdes.

## 2. Tela

1. `flask db upgrade` no `manto_local`: a migration da 330 entra sobre a da 328.
2. `verify_330.py --manter` deixa conversas do Instagram e do WhatsApp de demonstração.
3. Backend e Vite sobem pela worktree, em portas próprias, com chaves falsas do WhatsApp e do Instagram e o envio
   travado. A tela abre por `preview_start {url}`.
4. Conferir, no desktop e em 375×812:
   - o filtro "Canal" e os ícones;
   - a conversa do Instagram com "@usuário";
   - o aviso da janela humana (conversa com 30 h);
   - a conversa com 8 dias, sem campo;
   - nenhum "Enviar modelo" no Instagram.

## 3. Com o Instagram da Manto (depois, pelo dono)

1. No Business Manager, confirmar que o Instagram da Manto está ligado à Página da Manto e que "Permitir acesso às
   mensagens" está ligado (Instagram → Configurações → Mensagens → Ferramentas conectadas).
2. No app da Meta (o mesmo do WhatsApp), acrescentar o produto **Messenger/Instagram**, assinar o objeto `instagram`
   com os campos `messages`, `message_reactions`, `messaging_seen` e `messaging_referral`, e a URL
   `https://app.mantoproducoes.com.br/api/webhooks/instagram` com o mesmo token de verificação.
3. Gerar o token da Página com o usuário do sistema do portfólio e colar `INSTAGRAM_ACCESS_TOKEN`,
   `INSTAGRAM_PAGE_ID` e `INSTAGRAM_ACCOUNT_ID` no Render (nunca pelo chat).
4. Com o app ainda em desenvolvimento, mandar Direct de uma conta pessoal **com papel no app** e conferir:
   - a mensagem chega;
   - o perfil vem com nome e @usuário;
   - a resposta sai, também com foto e áudio;
   - responder pelo app do Instagram aparece como "Enviada por outro app";
   - o Kommo continua recebendo.
5. Confirmar na conta de teste os três pontos que a documentação não fecha:
   - a codificação do upload;
   - os campos do perfil;
   - o código da recusa da marca de resposta humana.
