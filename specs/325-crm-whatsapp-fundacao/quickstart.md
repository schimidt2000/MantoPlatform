# Quickstart — 325 Conversas (WhatsApp)

Roteiro de validação ponta a ponta. Contratos em [contracts/api.md](contracts/api.md); tabelas em
[data-model.md](data-model.md).

## 1. Verificação automática (sem Meta)

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
$env:PYTHONUTF8 = '1'; python specs/325-crm-whatsapp-fundacao/verify_325.py
```

Esperado: todos os cenários `OK`, inclusive os que **devem** falhar (assinatura errada, janela
fechada, Casting, configuração vazia, banco local travado). O verify injeta tokens falsos no
`app.config` e troca o cliente da Meta por um dublê — nada sai da máquina.

## 2. Tela, sem Meta

1. Migration aplicada no `manto_local` (`flask db upgrade` com as variáveis acima).
2. Rodar o verify com `--manter` para deixar uma conversa de demonstração (o próprio verify a
   remove sem a flag).
3. Abrir `/conversas` no Browser pane como Comercial: lista, conversa, mídia, "janela fechada",
   modelo, em desktop e em 375×812 (skill `manto-conferir-tela`).

## 3. Ponta a ponta no número de teste da Meta (o dono faz a parte da Meta)

O que é do dono, porque cria coisas na conta Meta da Manto:

1. Em developers.facebook.com, criar um app do tipo **Business** no portfólio **Manto Produções**
   e acrescentar o produto **WhatsApp**. A Meta oferece um **número de teste** grátis (envia para
   até 5 números cadastrados).
2. Cadastrar o próprio celular como destinatário de teste.
3. Em Business Settings › Usuários do sistema, criar um **System User** com acesso ao app e à
   conta do WhatsApp de teste e gerar um **token permanente** com `whatsapp_business_messaging` e
   `whatsapp_business_management`.
4. Anotar: `Phone number ID` e `WhatsApp Business Account ID` do número de teste; o **App Secret**
   (Configurações do app › Básico); inventar um **Verify token** (texto qualquer, longo).
5. Colar os cinco valores no `.env` local (desenvolvimento) e, quando for subir, no painel do
   Render do `manto-backend` — nunca no chat nem em arquivo versionado.

O que é do agente:

6. Desenvolvimento local precisa de URL pública para o webhook: túnel HTTPS para o Flask local
   (exige o OK do dono para baixar o programa do túnel) **ou** testar direto em produção depois do
   deploy com o módulo ligado só no número de teste.
7. No painel do app › WhatsApp › Configuração, registrar o webhook
   (`<URL>/api/webhooks/whatsapp` + o Verify token) e assinar o campo **messages**.
8. Com `WHATSAPP_ALLOW_LOCAL_SEND=true` (só local), mandar "oi" do celular para o número de teste:
   a conversa aparece em `/conversas` em até 10 s; responder pela tela; conferir "entregue" e
   "lida"; mandar foto e áudio dos dois lados; esperar 24 h (ou ajustar a última recebida no banco
   local) e conferir a recusa do texto livre e o envio de modelo (`hello_world` vem aprovado).

## 4. O que esta fase NÃO valida

O número principal (+55 11 97057-0577) não é ligado. A coexistência real, o roteamento com o
Kommo em paralelo (porta C do `docs/PLANO_CRM_PROPRIO.md`) e o volume real ficam para a Fase 4.
