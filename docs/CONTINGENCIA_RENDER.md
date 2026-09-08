# Incidente Railway → Render (28/08/2026) — registro histórico, não é runbook

> **Para operar a produção hoje, o lugar é `docs/01_SISTEMA_E_BANCO.md` §5.3** (serviços, disco,
> backup, acesso ao servidor, healthcheck) e `DEVELOPMENT.md` (publicar e operar). Este arquivo é
> o registro de como a produção foi reerguida no Render em 28/08/2026 e fica como memória do
> incidente — o caminho é citado por `docs/03` (264, 269b/269c) e por specs, por isso não muda.

**DESFECHO (28/08/2026): appeal NEGADO no mesmo dia — banimento permanente. O Render é a casa
definitiva.** Os arquivos que só existiam no volume do Railway estão perdidos em definitivo; a
lista de recoleta é `recuperacao/PENDENCIAS_RECUPERACAO.txt` (local, fora do git). O restante deste
documento é o roteiro que foi seguido.

A conta do Railway foi suspensa em 28/08/2026 ~00:00 ("ToS Violation"; appeal único enviado e
negado no mesmo dia). Produção reerguida no Render a partir do backup local.

## O que tínhamos e o que se perdeu

- **Banco**: dump íntegro de 27/08 02:00 (`backups/manto_2026-08-27_0200.dump`, testado com
  restauração completa em 28/08 — 464 eventos, último lançamento 26/08 23:04). Perdeu-se o dia
  27/08 do banco; a equipe re-digitou (concluído).
- **Arquivos do volume** (uploads/comprovantes/contratos, mídia NFC, vídeos virtuais): só existiam
  no volume do Railway. O que não foi recuperado em 28/08 está **perdido em definitivo** — não há
  acesso a recuperar. O que voltou veio do WordPress antigo (ainda vivo), do disco local e da
  planilha do Form (`docs/03`, entrada 264: catálogo 88%, figurinos 90%, talentos 99%).
- **Código**: GitHub `schimidt2000/MantoPlatform`, `main` íntegra.
- **Segredos**: todos no `.env` local da máquina do dono (nunca em chat/commit).

## Passos seguidos (ordem)

1. Dono criou conta no Render (Sign in with GitHub, conta schimidt2000) + cartão.
2. Dono autorizou o app GitHub do Render no repo `MantoPlatform`.
3. "New +" → **Blueprint** → selecionar o repo → o `render.yaml` da raiz criou:
   `manto-postgres` (basic-1gb) + `manto-backend` (python, standard, disco 10GB em `instance/`)
   + `manto-frontend` (node, starter).
4. Preenchimento dos envVars `sync:false` com os valores do `.env` local (backend) e do
   `BACKEND_URL` do frontend com a URL pública que o `manto-backend` ganhou
   (`https://manto-backend.onrender.com`). **Exceto as variáveis de endereço.** Foi copiando o
   `.env` local para o painel que `PORTAL_URL=http://localhost:5000` entrou em produção e o convite
   do artista — e o link de redefinição de senha — saiu apontando para o localhost do servidor
   (hotfix 269b, `docs/03`). As regras que ficaram (`PORTAL_URL`/`PUBLIC_BASE_URL`/
   `SESSION_COOKIE_DOMAIN` não se definem; `GOOGLE_OAUTH_REDIRECT_URI` recebe a URL pública) estão
   em `docs/01` §5.3 e no `.env.example`. `AUDIT_AGENT_TOKEN` e `MARKETING_AGENT_TOKEN` **não
   foram preenchidos** — pendência em `docs/05`.
5. Restauração do banco: **External Connection String** do `manto-postgres` e, da máquina do dono,
   `pg_restore -w --no-owner --no-acl -d "<EXTERNAL_URL>" backups/manto_2026-08-27_0200.dump`
   (o `flask db upgrade` do start é idempotente sobre o dump, que já estava no head das migrations).
6. Teste na URL provisória: login, calculadora, agenda, um orçamento de ponta a ponta.
7. DNS: `app`, `portal` e `alo.mantoproducoes.com.br` (CNAME na Hostinger) → `manto-frontend.onrender.com`,
   custom domains no serviço (o Render emitiu TLS sozinho). `beta.*` não foi migrado — e deixou
   um cookie órfão para trás (feature 295).
8. Equipe avisada: re-digitar 27/08; agenda dos dias seguintes conferida contra o Google Calendar
   (a sync partiu do banco de 27/08).

## Riscos aceitos na migração

- Sync do Google Calendar a partir de banco de 27/08 → poderia reverter edições de 27/08 no Google.
  Mitigação: conferência manual da agenda no go-live (passo 8).
- E-mail/convites ATIVOS: `DATABASE_URL` sem localhost liga o envio real — comportamento desejado
  do ambiente substituto.
- Rate limit em memória por worker e threads de background ×3 — mesmos trade-offs do Railway,
  documentados em `docs/01` §5.3.

## O que a migração ensinou (hoje em `docs/01` §5.3)

Deploy troca o container (mata `nohup`, limpa `/tmp`, que é RAM); a sessão SSH tem as env vars do
serviço; `python3` fora do CWD precisa de `PYTHONPATH`; conta de serviço não tem cota no My Drive
(backup só em Shared Drive); o frontend não tem healthcheck (janela de 502 a cada deploy).
