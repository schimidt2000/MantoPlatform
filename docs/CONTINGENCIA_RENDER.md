# Contingência Render — suspensão do Railway (28/08/2026)

**DESFECHO (28/08/2026): appeal NEGADO — banimento permanente. O Render é a casa definitiva.**
Os arquivos que só existiam no volume do Railway estão perdidos em definitivo; a lista de
recoleta é `recuperacao/PENDENCIAS_RECUPERACAO.txt`. O restante deste runbook fica como registro.

A conta do Railway foi suspensa em 28/08/2026 ~00:00 ("ToS Violation"; appeal único enviado e
negado no mesmo dia). Produção reerguida no Render a partir do backup local.

## O que temos e o que perdemos

- **Banco**: dump íntegro de 27/08 02:00 (`backups/manto_2026-08-27_0200.dump`, testado com
  restauração completa em 28/08 — 464 eventos, último lançamento 26/08 23:04). **Perde-se o dia
  27/08**: a equipe precisa re-digitar o que lançou ontem.
- **Arquivos do volume** (uploads/comprovantes/contratos, mídia NFC, vídeos virtuais): SÓ existem
  no volume do Railway. Ficam indisponíveis (links 404) até o appeal devolver o acesso. O sistema
  funciona normalmente sem eles.
- **Código**: GitHub `schimidt2000/MantoPlatform`, main íntegra.
- **Segredos**: todos no `.env` local da máquina do dono (nunca em chat/commit).

## Passos (ordem)

1. Dono cria conta no Render (Sign in with GitHub, conta schimidt2000) + cartão.
2. Dono autoriza o app GitHub do Render no repo `MantoPlatform`.
3. "New +" → **Blueprint** → selecionar o repo → o `render.yaml` da raiz cria:
   `manto-postgres` (basic-1gb) + `manto-backend` (python, standard, disco 10GB em `instance/`)
   + `manto-frontend` (node, starter). Se algum nome de plano for recusado, ajustar no próprio
   arquivo (nomes de plano mudam; o resto do blueprint fica).
4. Preencher os envVars `sync:false` com os valores do `.env` local (backend) e o `BACKEND_URL`
   do frontend com a URL pública que o `manto-backend` ganhar (`https://manto-backend*.onrender.com`).
   `SESSION_COOKIE_DOMAIN`: **não definir** (o Node faz proxy same-origin de `/api`; cookie
   host-only basta e funciona também na URL provisória *.onrender.com).
5. Restaurar o banco: pegar a **External Connection String** do `manto-postgres` e, da máquina do
   dono: `pg_restore -w --no-owner --no-acl -d "<EXTERNAL_URL>" backups/manto_2026-08-27_0200.dump`
   — ANTES do primeiro deploy do backend terminar, ou re-deployar depois (o `flask db upgrade` do
   start é idempotente sobre o dump, que já está no head das migrations).
6. Testar na URL provisória: login, calculadora, agenda, um orçamento de ponta a ponta.
7. DNS: apontar `app.mantoproducoes.com.br` (CNAME) para o `manto-frontend` e adicionar os
   custom domains no serviço (Render emite TLS sozinho). `beta.` idem se ainda for usado.
8. Avisar a equipe: re-digitar 27/08; conferir a agenda dos próximos dias contra o Google
   Calendar (a sync roda com banco de 27/08 e pode reescrever título/dados de evento editado
   ontem — revisar antes de confiar).

## Riscos aceitos

- Sync do Google Calendar parte de banco de 27/08 → pode reverter edições feitas em 27/08 no
  Google. Mitigação: conferência manual da agenda no go-live (passo 8).
- E-mail/convites ATIVOS (produção de verdade): `DATABASE_URL` sem localhost liga
  `MAIL_SUPPRESS_SEND=False`. É o comportamento desejado do ambiente substituto.
- Rate limit em memória por worker, threads de background ×3 — mesmos trade-offs do Railway,
  documentados em `docs/01`.

## Quando o appeal responder

- **Aceito**: primeiro ato = dump fresco do Postgres do Railway + cópia integral do volume para
  fora (o buraco de backup que este incidente expôs: o volume nunca teve cópia externa). Depois,
  decidir com calma onde fica a produção — e o que fazer com os dias divergentes entre os bancos.
- **Negado**: o Render já é a produção; abrir feature para re-upload dos anexos críticos e
  backup externo do disco do Render.
