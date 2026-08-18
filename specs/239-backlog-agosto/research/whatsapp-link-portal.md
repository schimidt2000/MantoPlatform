# Mensagem de cobranca via WhatsApp: incluir link do portal da pessoa para aceitar o convite do evento

## Resumo
O botão "Cobrar no WhatsApp" do painel de confirmações pendentes existe e já funciona (feature 231), mas a mensagem que ele monta no cliente menciona "no portal" sem incluir nenhum link. O portal do artista já tem uma URL raiz pública e estável (`/` → redireciona para `/agenda` se logado, ou `/login` se não) que os e-mails automáticos já usam como "página principal" — é essa mesma URL que falta entrar na mensagem de WhatsApp.

## Causa raiz
Não é bug — é lacuna de dado: a URL do portal nunca foi propagada do backend (`PORTAL_URL` em `app/email_service.py:67-68`) até o componente que monta a mensagem de WhatsApp no frontend interno (`DashboardPage.tsx:69-73`). O texto da mensagem já pressupõe que a pessoa vá "ao portal", só falta o link.

## Comportamento atual (evidencia)
O botão "Cobrar no WhatsApp" fica na Dashboard interna, na lista "quem ainda não confirmou" (feature 231). Em `frontend/apps/internal/src/pages/DashboardPage.tsx:66-117` (`UnconfirmedRow`), quando `item.invite_status === "pending"` (convite já enviado, sem resposta) o componente monta um link `wa.me` assim:

```
frontend/apps/internal/src/pages/DashboardPage.tsx:69-73
const zap = item.whatsapp
  ? `https://wa.me/${item.whatsapp.replace(/\D/g, "")}?text=${encodeURIComponent(
      `Oi, ${item.talent_name}! Falta você confirmar no portal a sua presença em "${item.event_title}". Consegue responder por lá?`,
    )}`
  : null;
```

A mensagem diz "no portal" mas **não contém nenhuma URL** — quem recebe a cobrança não tem para onde clicar; precisa saber de cor o endereço do portal ou já ter o link salvo de outra conversa.

O dado `item.whatsapp` vem de `GET /api/dashboard` → `casting.unconfirmed`, serializado em `app/api/dashboard_service.py:236-254` (`serialize_unconfirmed_ref`), que devolve `talent_name`, `whatsapp`, `invite_status`, `reminder_count` etc., mas não devolve nenhuma URL de portal — o payload do dashboard como um todo (`build_dashboard_summary`, `app/api/dashboard_service.py:448-568`) não expõe a URL do portal em lugar nenhum.

**A URL do portal já existe e é usada em outro lugar**: `app/email_service.py:67-68` define `_portal_url() -> current_app.config.get("PORTAL_URL", "").rstrip("/")` e todos os e-mails automáticos de convite/lembrete/anúncio (`app/email_service.py:171-198`, `228-254`, `325-334`, `346-392`) linkam para `f"{portal_url}/"` — literalmente a "página principal do portal", exatamente como o Joao descreveu. `PORTAL_URL` é uma env var Flask (`.env.example:24`, ex. `https://manto.up.railway.app` ou, em produção real, o domínio próprio servido via `PORTAL_HOSTS` em `frontend/server.js:144-145` = `portal.mantoproducoes.com.br`).

Essa URL só existe hoje no config do Flask (server-side); o app React interno (`frontend/apps/internal`) não tem nenhum env var `VITE_PORTAL_URL` nem busca essa URL de nenhum endpoint — confirmado por busca em todo `frontend/` (nenhum `.env*` na árvore de apps, nenhuma referência a `PORTAL_URL`/`portal_url` fora de `server.js` e `email_service.py`). É por isso que a tela hoje não tem como montar o link: o dado simplesmente não chega ao cliente.

Quanto à "página principal do portal para aceitar o convite": o Portal do Artista (`frontend/apps/portal`) roteia `/` → redireciona para `/agenda` quando autenticado (`frontend/apps/portal/src/App.tsx:46`), protegido por `RequireTalentAuth` (login normal por senha, sem magic link/token por pessoa — confirmado em `App.tsx:37-44`, só há rotas de token para `/reset-password/:token`, não para convite). O convite em si é aceito/recusado em `/convites` (`PortalConvitesPage.tsx`), que lista os cargos pendentes do talento logado e tem os botões "Aceitar"/"Recusar" (`PortalConvitesPage.tsx:15-84`, usando `useAcceptInvite`/`useRejectInvite` de `lib/portalAgenda`). Não existe link direto por convite/evento — é uma lista, não uma página por-convite. Portanto "link para a página principal" (a raiz `/`, que resolve para `/agenda` ou pede login) é de fato a única opção sensata hoje, batendo com o que o Joao já sugeriu ("Pode ser um link para a página principal").

## Arquivos relevantes
- frontend/apps/internal/src/pages/DashboardPage.tsx — onde a mensagem de WhatsApp é montada (UnconfirmedRow, linhas 66-117); precisa incluir a URL do portal no texto
- app/api/dashboard_service.py — serializa o payload de GET /api/dashboard (serialize_unconfirmed_ref linhas 236-254; build_dashboard_summary linhas 448-568); precisa expor a URL do portal para o frontend
- app/email_service.py — fonte já existente de _portal_url() (linhas 67-68), usa current_app.config['PORTAL_URL'] — padrão a reaproveitar, não duplicar
- frontend/apps/internal/src/lib/types.ts — define DashboardSummary (linhas 141-156) e UnconfirmedInviteRef; precisa declarar o novo campo de URL
- frontend/apps/portal/src/App.tsx — confirma que "/" é a página principal do portal (redireciona para /agenda se logado) e que não há link mágico por convite (linhas 26-61)
- frontend/apps/portal/src/pages/PortalConvitesPage.tsx — onde o convite é de fato aceito/recusado (lista em /convites, sem link direto por convite)
- .env.example — documenta PORTAL_URL (linha 24) — mesma env var a reaproveitar

## Abordagem proposta pela investigacao
Reaproveitar a `PORTAL_URL` que o backend já tem (mesma fonte usada pelos e-mails), expondo-a no payload que a Dashboard já consome, e usá-la ao montar a mensagem de WhatsApp:

1. **Backend** — em `app/api/dashboard_service.py`, dentro de `build_dashboard_summary` (por volta da linha 558, junto do `return`), adicionar `"portal_url": current_app.config.get("PORTAL_URL", "").rstrip("/") or None` ao dicionário retornado (mesma lógica de `_portal_url()` de `app/email_service.py:67-68` — pode até importar/reaproveitar essa função ou replicar a linha, já que `*_ops`/serviços não devem depender de `email_service`). Isso não exige migração nem endpoint novo — só um campo a mais na resposta de `GET /api/dashboard` que a Dashboard já busca.

2. **Frontend — tipos**: em `frontend/apps/internal/src/lib/types.ts`, adicionar `portal_url: string | null` em `DashboardSummary` (linha ~141).

3. **Frontend — mensagem**: em `frontend/apps/internal/src/pages/DashboardPage.tsx`, `UnconfirmedRow` precisa receber a `portal_url` (via prop, subindo de onde a lista é renderizada — provavelmente `SectorPanel`/seção de casting que já recebe `data: DashboardSummary`) e incluir o link no texto, ex.:
   `Oi, ${item.talent_name}! Falta você confirmar no portal a sua presença em "${item.event_title}". Consegue responder por lá? ${portalUrl}/` (a barra final é o padrão que os e-mails já usam, `f"{portal_url}/"`).
   Se `portal_url` vier `null` (env var ausente em dev/local), omitir o link do texto em vez de gerar uma URL quebrada — mesmo padrão defensivo que o botão já usa hoje (`zap` só existe se `item.whatsapp` existir).

4. Nenhuma migração de banco é necessária — `PORTAL_URL` já é env var de app config, não coluna de tabela.

5. Depois de implementar, atualizar `docs/01_SISTEMA_E_BANCO.md` (campo novo em `GET /api/dashboard`) e `docs/03_HISTORICO_MUTACOES.md` (entrada no topo), conforme a regra obrigatória do `CLAUDE.md`.

Não achei nada em `BounceQueue.tsx` (reforço de e-mail que voltou) que se aplique aqui — é um fluxo diferente (endereço de e-mail errado/caixa cheia), não convite de evento; não precisa mexer nele para este item.

## Riscos mapeados
- Se PORTAL_URL não estiver setada no Railway/produção, o campo virá null e a mensagem ficará sem link (comportamento atual) — vale confirmar que a env var está mesma configurada em produção antes de assumir que o link vai aparecer.
- A URL raiz do portal (`/`) exige login; quem recebe a mensagem e não está logado cai em `/login`, não direto no convite — é o comportamento que o próprio Joao pediu ("pode ser um link para a página principal"), mas vale registrar que não é um deep-link direto para `/convites`.