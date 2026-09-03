# Hotfix 269c — As vedações que faltaram na 269b

**Branch**: `269c-vedacoes-restantes` (da `main`, já com a 269b) · **Created**: 2026-09-03
**Status**: Pronto, aguardando push · **Migration**: nenhuma
**Verify**: `specs/269b-hotfix-link-do-portal/verify_269b.py` (cenários 7, 8 e 9) — mesmo assunto,
um arquivo só.

## De onde veio

Varredura adversarial de tudo que a Manto manda para fora, rodada depois da 269b: 4 frentes
(e-mail, outros canais, config, frontend), 55 achados, 110 conferências. A maioria era o próprio
defeito da 269b, já corrigido e em produção. Três achados eram **buracos na trava que a 269b
acabara de subir** ou erro de destino, e é o que esta entrada fecha. O resto virou backlog (ver
"Fora de escopo").

## O que muda

1. **A trava de corpo passou a julgar host como a config julga.** A 269b tinha duas listas
   parecidas em lugares diferentes, e a do e-mail era a mais curta: `http://192.168.0.14:5000`,
   `http://10.1.2.3/` e `https://maquina.local/` **passavam**. Agora existe
   `config.host_e_local()` como fonte única, usada pelos dois lados, e a busca no corpo lê
   qualquer URL absoluta em vez de uma lista fixa de hosts.
2. **`send_quote_email` entrou na trava.** É o e-mail do orçamento para a **cliente**, e monta a
   própria `Message` por causa do PDF anexo — por isso não passava por `_send` e era o único
   caminho para fora sem a vedação. A checagem virou `_bloqueia_link_local()`, chamada nos dois
   lugares.
3. **O alerta de ensaio parou de mandar o staff para o Portal do Artista.** É e-mail interno; o
   botão usava `PORTAL_URL` (herança de copiar o e-mail do convite) e levava para o portal em vez
   do evento. Agora aponta para `PUBLIC_BASE_URL/events/<id>`.
4. **O comunicado do portal deixou de escrever o endereço à mão.** O texto "copie o endereço"
   dizia `portal.mantoproducoes.com.br` enquanto o `href` vinha da config — no dia do defeito, um
   dizia uma coisa e o outro levava para outra. Texto e link saem da mesma variável.
5. **A documentação que ensinava o erro foi corrigida.** `docs/CONTINGENCIA_RENDER.md` mandava, no
   passo 4, "preencher os envVars `sync:false` com os valores do `.env` local" — foi exatamente
   assim que `PORTAL_URL=http://localhost:5000` entrou no painel do Render. Agora o passo diz quais
   variáveis nunca vêm do `.env`. O `DEVELOPMENT.md` deixou de ensinar o valor local para produção
   (e de falar em Railway, que morreu).

## Verificação

`verify_269b.py` 9/9 contra `manto_local` com o SMTP dublado. Os três cenários novos: faixa
privada, IPv6 e `.local` barrados enquanto host público parecido (`10minutemail.com`,
`172.15.0.1`, `localhost.exemplo.com`) passa; orçamento com PDF barrado quando o corpo tem link
local e enviado quando não tem; alerta de ensaio apontando para `app.mantoproducoes.com.br/events/<id>`
e sem nenhuma menção ao portal. `ruff` limpo nos dois arquivos tocados.

## Fora de escopo (backlog da varredura, com dono a decidir)

- **`window.location.origin` em três lugares que geram link para fora**: a URL gravada na **tag NFC
  física** (`components/nfc/helpers.ts`), o link público do formulário (`FormulariosAdminPage`) e o
  "Exportar elenco" (`EventHeader`). Mesmo defeito que a 269 corrigiu com `PORTAL_PUBLICO` — e a
  tag NFC é gravada uma vez e vive para sempre.
- **`GOOGLE_OAUTH_REDIRECT_URI`** sem validação e com valor local sugerido; e o `redirect_uri` do
  OAuth do Google saindo de `url_for(_external=True)` (`calendar/routes.py`), derivado de header.
- **`frontend/server.js`**: `BACKEND_URL` ausente cai em silêncio para `http://localhost:5000`, e
  `og:url`/`og:image` são montados a partir de `x-forwarded-host`.
- **Config em geral**: `int(os.getenv(...))` sem guarda (chave vazia no painel derruba o boot),
  valor vazio vencendo default, `SESSION_COOKIE_DOMAIN` e `S3_PUBLIC_URL` sem validação,
  `validar_startcommand.py` ainda validando o `railway.json` da plataforma morta.
- **`portal_url` no payload da Home** e no `types.ts`: campo sem consumidor desde a 269.
