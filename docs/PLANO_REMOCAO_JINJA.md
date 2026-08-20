# Plano de remoção do sistema Jinja legado

> ## Estado em 19/08/2026 — fases 1, 2, 3 e 5 **CONCLUÍDAS e em produção**
>
> | Fase | Estado | Commit |
> | --- | --- | --- |
> | 0 — interruptor | **pulada** (prejudicada: as decisões foram respondidas direto) | — |
> | 1 — órfãos e código morto | ✅ em produção | `c628d25` |
> | 2 — Portal do Artista | ✅ em produção | `9d42f82` |
> | 3 — blueprints substituídos | ✅ em produção (pré-requisito de extração incluído) | `c94995d`, `0aef653`, `e8e17f6`, `5ab99db` |
> | 5 — `/avaliar` | ✅ em produção | `d4d16cc`, `5ab99db` |
> | 4 — decisões | ✅ todas respondidas · vira feature (ver §7) | — |
> | 6 — `calendar` e `financeiro` | 🔨 **4 dos 5 pré-requisitos fechados** — falta só a API+UI das coleções comerciais | `a58f54b`, `a01ab48`, `88ba7a7`, `1343939` |
> | 7 — `auth` e fechamento | ⬜ pendente, depende da feature de conta | — |
>
> **~19.000 linhas de Jinja removidas.** Templates: 84 → 17. Rotas: 530 → 382.
>
> **O que resta de Jinja é exatamente:** `calendar` (agenda, eventos, ensaios, cargos),
> `financeiro` (+ `/vendas/`) e `auth` (login, perfil, troca de senha). Mais os intocáveis da §5.
>
> **A regra que nasceu do caminho:** antes de apagar qualquer blueprint, rodar
> `grep "from app\.<nome>\.routes import"` no repo **inteiro, incluindo `scripts/`**. Foi assim que
> se descobriu que cinco módulos vivos importavam lógica de dentro do Jinja. E rodar
> `scripts/db/check_url_for_orfaos.py` depois de cada lote.


**Data:** 19/08/2026 · **Estado do repositório:** `main` limpo, sincronizado com `origin/main` (5b14d2d)

Este documento é o plano para apagar as páginas server-rendered em Jinja sem afetar a plataforma
React. Ele foi montado a partir de uma varredura completa: 530 rotas Flask, os 84 templates, os três
bundles React, os links que o sistema envia por e-mail/WhatsApp e tudo que vive fora de `app/`.

---

## 1. O retrato

| | |
| --- | --- |
| Rotas Flask mapeadas | **530** |
| Que ficam | **346** — sendo 326 `/api/*`, 6 de servir arquivo, 7 redirects, 2 de OAuth, 5 de sistema |
| Removíveis | **175** |
| Vivas mas ainda Jinja (migrar antes) | **4** |
| Dependem de decisão sua | **5** |
| Templates Jinja | 84 arquivos, 19.808 linhas |
| `app/static/` (100% do Jinja) | 13 arquivos, 2,5 MB |
| Linhas em `*/routes.py` | ≈ 10.000, das quais boa parte é núcleo compartilhado com a API |

Removíveis por arquivo:

```
24  app/admin/routes.py          13  app/talents/routes.py
20  app/talent_portal/routes.py  13  app/financeiro/routes.py
18  app/calendar/routes.py        7  app/clientes/routes.py
18  app/gastos/routes.py          6  app/figurino/routes.py
17  app/formularios/routes.py     5  app/catalogo/routes.py
14  app/revisao/routes.py         2  app/auth/routes.py
14  app/orcamento/routes.py       2  app/__init__.py (/impersonate)
                                  1  app/feedback + 1 app/rh
```

## 2. Por que isso é mais seguro do que parece

`frontend/server.js` é a **única porta pública** da plataforma (`app.mantoproducoes.com.br`). Ele
devolve ao Flask apenas estes caminhos:

```
/api   /uploads   /catalogo/midia   /catalogo/og   /portal/photo   /google   /avaliar   /static
+ regex:  /figurinos/<id>/print     /figurinos/print-event/<id>
```

Todo o resto cai nos bundles React. Ou seja: **as 175 rotas removíveis já não são alcançáveis pelo
endereço que as pessoas usam.** Elas só respondem se alguém bater direto no domínio do serviço
Flask no Railway, que não é divulgado.

Isso muda a natureza do trabalho: não é uma migração, é a remoção de código que já está fora de
circulação. O risco não está em "quebrar uma tela" — está nas seis armadilhas abaixo.

## 3. As armadilhas

### 3.1 `/avaliar/<token>` — o único link para fora que ainda aponta para Jinja

É o mais sério. O link de avaliação enviado às clientes é `{PUBLIC_BASE_URL}/avaliar/<token>`,
gerado em dois lugares (`app/api/agenda_write.py:1604` e o gêmeo Jinja
`app/feedback/routes.py:64`). O prefixo `/avaliar` **está** na lista do proxy, então esses links
aterrissam na página Jinja `feedback/public.html`. **Os tokens não expiram.**

A página React equivalente já existe e funciona (`/catalogo/avaliar/:token`, feature 164) — só a
geração do link nunca foi trocada.

> Apagar `feedback_bp` hoje = link morto na mão de todas as clientes que já receberam o seu.

Saída: trocar os dois geradores para `/catalogo/avaliar/<token>` **e** manter `/avaliar/<token>`
como redirect 302 permanente para os links já em circulação.

> **CONFIRMADO EMPIRICAMENTE (19/08).** O João acreditava que "as clientes recebem os links novos".
> Não vale para este link. A cadeia foi verificada ponta a ponta e o `frontend/server.js` real foi
> executado contra um backend falso: `GET /avaliar/TOKEN` é **proxiado ao Flask** — inclusive com
> `Host` de portal e de alo. `isBackendRequest` (`server.js:537`) é a **primeira** checagem do
> handler, antes de qualquer mount de SPA. O botão "Pedir feedback da cliente"
> (`EventHeader.tsx:275-287`) copia a URL **crua** devolvida pela API (`agenda_write.py:1624`), sem
> reescrever nada. A `AvaliarPage` React só responde em `/catalogo/avaliar/<token>`, porque o
> bundle roda com `basename="/catalogo"` (`apps/public/src/App.tsx:21,43`).
>
> **A página React tem paridade completa** — grava `ClientFeedback`, tem o CTA do Google Review em
> nota 5 (mesma função, por import) e o mesmo rate limit de 10/h. Está pronta e ociosa.

> **ACHADO NOVO E CRÍTICO — a API React importa do módulo Jinja.**
> `app/api/feedback_write.py:18` importa `POSITIVE_TAGS`, `ATTENTION_TAGS` e `_tags_for_score` de
> `app/feedback/routes.py`. Apagar o arquivo Jinja **derruba o endpoint React de avaliação**, que
> está vivo em produção. Antes de qualquer remoção, essas três constantes têm de sair para um
> módulo próprio (`feedback_ops.py`). Vale como alerta geral: este é o segundo caso de import do
> Jinja para dentro da API — o primeiro são os imports tardios de `calendar/routes.py` (§3.4).

### 3.2 `login_manager.login_view = "auth.login"`

Em `app/__init__.py:27`. Qualquer rota `@login_required` que **fica** monta um redirect para esse
endpoint quando a sessão não existe — e `/uploads/<path>` é `@login_required` **e é proxiada**.

> Apagar o blueprint `auth` sem mexer nisso = `BuildError` 500 em `/uploads` para toda sessão
> anônima ou expirada. A mídia da plataforma inteira para.

Saída: antes de tocar em `auth`, trocar para `login_view = None` + um `unauthorized_handler` que
devolva 401 JSON em `/api/*` e 401 no resto.

### 3.3 Capacidades que só existem no Jinja

Estas não têm substituto em lugar nenhum. Apagar sem decidir = perder a funcionalidade.

| Onde | O que se perde |
| --- | --- |
| `/auth/change-password` | **O único ponto que aplica `must_change_password` para staff.** Confirmado: `admin/user_ops.py` marca o flag na criação (:146) e no reset (:400, :411), e só `auth/routes.py:37` o obriga. A API de login ignora — senha temporária de staff ficaria válida para sempre. *(O lado do talento está coberto pela API, `portal_auth.py:54`.)* |
| `/auth/profile` | Único lugar que grava foto de perfil (`uploads/profiles/user_<id>`) — e a SPA **consome** essa foto via `assetUrl()`. Não existe `PATCH /api/me`. |
| `/talents/<id>/reset-password` | Reset de senha de talento iniciado pelo admin. O portal tem "esqueci minha senha" self-service, que cobre a maioria dos casos. |
| `/figurinos/sync-drive` + `/stream` | Importação de fichas do Google Drive (SSE). Leva junto ~160 linhas de parser de Google Docs. `docs/04` e `docs/05` ainda tratam como funcionalidade viva. |
| `calendar/routes.py:1484, :1537, :1564` | **Agrupar / desagrupar / renomear grupo de eventos.** Não há endpoint nem tela React. A *leitura* de grupo continua ativa em `agenda_read.py:247` e `financeiro_read.py:392`. |
| `calendar/routes.py:712` (`_handle_update_comercial`) | Única escrita de `EventAcrescimo`, `EventInvoice` e `EventInstallment`. A API precisa de paridade antes. |
| `calendar/routes.py:914` (`_sync_commission_payment`) | Um dos **dois** únicos pontos que criam linha de comissão. `event_ops.update_event_comercial` não chama. |
| `revisao/routes.py:121` (`invite_text`) | Mensagem pronta de convite dos revisores para colar no WhatsApp. `GET /api/revisao/<id>` não devolve. |

### 3.4 `calendar/` e `financeiro/` não são remoções limpas

`app/calendar/routes.py` tem 3.831 linhas: cerca de 946 de views Jinja, 691 de handlers `_handle_*`
e **1.007 de núcleo compartilhado com a API** — exportado por *imports tardios* de 10 módulos, que
não aparecem em análise estática. Renomear um helper ali quebra a API em silêncio.
`app/financeiro/routes.py` (1.504 linhas) mistura a regra de comissão de 9 ramos com as views.

Nesses dois, extrair o núcleo para `*_ops.py` vem **antes** de remover qualquer view.

### 3.5 Cascata de `BuildError` entre templates

Um template que fica não pode chamar `url_for()` de um endpoint que saiu — o Flask só descobre isso
em tempo de execução, quando alguém abre a página. Quatro templates cruzam para o `calendar`:

```
app/templates/financeiro/dashboard.html      app/templates/vendas/pipeline.html
app/templates/financeiro/comissoes.html      app/templates/orcamento/historico.html
```

Regra: **apagar a página e os templates que apontam para ela no mesmo commit.**

Alívio: `base.html` tem zero `url_for` — navegação e logout são `href`/`action` hardcoded. O layout
não estoura quando os endpoints somem.

### 3.6 Não existe suíte de testes

Não há pytest nenhum no repositório. O que existe:

- **Playwright** (`frontend/apps/*/e2e/`) — só rotas do React Router, homônimas mas independentes.
  Não cobre Jinja.
- **`scripts/db/verify_*.py`** — um por feature, rodados à mão, pasta inteira gitignorada.
  `verify_206_react_primario.py` é o guardião pós-migração e continua válido: confere o 301 da raiz
  sem desvio para `/auth/login` e que `/uploads`, `/catalogo/midia`, `/figurinos/<id>/print` e
  `/portal/photo` seguem no `url_map`. **Este é o teste de regressão de cada fase.**
- `verify_139/140/141/142` batem em páginas Jinja legadas e vão falhar depois da remoção — são
  históricos, não estão em CI, não bloqueiam.

O portão real de cada fase é mais simples e mais duro:

```bash
python -c "from app import create_app; create_app()"
```

O Flask registra blueprints na importação. Um `ImportError` ou um endpoint órfão derruba o app
inteiro no start — e o Railway só tenta 3 vezes antes de desistir.

---

## 4. O plano

### Fase 0 — Interruptor antes da tesoura ~~(recomendado)~~ · **pular**

> **Revisto em 19/08 após as respostas.** Esta fase existia para responder as decisões 1, 2 e 3 com
> dado real de produção em vez de memória. O João respondeu as três diretamente, então ela perdeu a
> justificativa principal. Sobra só a rede contra uso *desconhecido* do host direto do Flask — que o
> commit por fase, com `git revert` disponível, já cobre a um custo muito menor.
>
> Descrição original preservada abaixo, caso você prefira a rede mesmo assim.

Antes de apagar uma linha, provar em produção que ninguém usa essas rotas.

Um `before_request` em `create_app()` com a **allowlist** dos prefixos vivos (exatamente os do
`server.js`, mais `/health`, `/robots.txt` e `/`): tudo fora dela responde **410 Gone** e registra
no log o caminho e o usuário. Uma variável de ambiente desliga o comportamento sem deploy.

Por que vale a pena: converte uma deleção irreversível numa chave que você desliga em 30 segundos.
Duas semanas de log respondem a pergunta que nenhuma análise estática responde — *alguém da equipe
ainda usa essas telas pelo domínio direto do Flask?* O caso do `invite_text` da revisão (§3.3)
sugere que talvez sim.

Custo: uma sessão. Se preferir pular, o plano funciona igual — só sem essa rede.

### Fase 1 — Órfãos e código morto · ✅ **CONCLUÍDA em 19/08** (commit `c628d25`, branch `240-remocao-jinja-fase1`)

> −1.043 linhas. `create_app()` sobe, `verify_206` 20/20 contra o `manto_local`, ruff sem erro novo.
> **Ainda não mergeada em `main`** — aguardando o João. Ver `docs/03_HISTORICO_MUTACOES.md`.

> **Revisto em 19/08 após verificação adversarial.** Seis dos oito alvos resistiram; **o `rh_bp`
> caiu** e três armadilhas de execução apareceram. A frase original desta seção — "nada aqui é
> referenciado por absolutamente nada" — era falsa para o `rh`.

Confirmados seguros, cada um por busca exaustiva (literais `.html` em todo `.py`, `extends` /
`include` / `import` de nome variável, `add_url_rule`, `getattr`/`importlib`, `scripts/`, `specs/`):

- Templates órfãos: `home.html`, `admin_layout.html`, `financeiro_layout.html` — os três são
  documentos autocontidos (`<!doctype html>` próprio), não layouts herdados. Os 12 `admin_*.html`
  estendem `base.html`, não o `admin_layout.html`.
- Static órfão: `app/static/slapwars.gif` — `git log -S` mostra o ciclo completo: entrou nas páginas
  de erro e foi substituído por `source.gif` no commit 74f97f0.
- `calendar/routes.py`: `travel_estimate` (:2604, **sem decorator** — confirmado por leitura) e
  `_is_outside_sp` (:2545)
- `/impersonate/<role>` e `/impersonate/reset` em `app/__init__.py` — a SPA usa
  `POST/DELETE /api/auth/impersonate` (`useAuth.ts:77,92`); só `base.html` posta nas rotas antigas

**Três armadilhas de execução, todas de deleção — não de análise:**

1. **`home.html` tem um homônimo VIVO.** `app/templates/portal/home.html` é renderizado em
   `app/talent_portal/routes.py:462`. Um glob recursivo por `home.html` derruba o portal. Apagar
   pelo caminho exato.
2. **Não arraste `_SP_CITY_TERMS` junto.** A constante (`calendar/routes.py:2506`) é usada tanto
   pelo `_is_outside_sp` que sai quanto por `_lookup_sp_status` (:2539), que **roda em produção**
   como fallback quando o ViaCEP falha. Apagar só o `def _is_outside_sp` (:2545-2554); apagar o
   bloco "LOGÍSTICA" inteiro causa `NameError` em produção.
3. **Achado colateral:** `event_detail.html:1232` chama `fetch('/events/<id>/travel-estimate')` —
   esse botão **já dá 404 hoje**, porque a função perdeu o decorator em algum momento. Apagar não
   muda nada; só remove a ilusão de que voltaria a funcionar.

**`rh_bp` sai da Fase 1** — vai para a Fase 3. Não quebra produção (`/rh` não é proxiado, o
substituto React existe em `App.tsx:143`, a API vive em `app/api/rh_read.py:16`), mas
`scripts/db/verify_166_rh_tools_bp.py:107-110` exercita `GET /rh/dashboard` esperando 200 e sai com
código 1 se falhar. A pasta `scripts/db/` é gitignorada, e por isso escapou da varredura. No mesmo
commit da remoção, adaptar esse bloco do verify e somá-lo à lista de vítimas da §6.

### Fase 2 — Portal do Artista Jinja · o caso mais limpo, e também um reparo de segurança

20 das 21 rotas de `app/talent_portal/routes.py` (806 linhas) + os 12 templates de
`app/templates/portal/`. A `docs/05` já classificava como "caso limpo, 1 sessão".

Vale antecipar porque **não é só limpeza**: essas rotas seguem respondendo pelo host direto do
Flask com validação **mais fraca** que a da API — `profile()` (:544) aceita foto conferindo só a
extensão, sem limite de tamanho, e `media_delete` (:624) tem um bug latente de
`.lstrip("/uploads/")`.

**`/portal/photo/<file>` (:78) fica.** É rota de arquivo, está no proxy, e toda imagem do portal sai
por ela — `/uploads` exige sessão de *staff*, então para o talento vira 302 e ícone quebrado.

Detalhe tranquilizador: o e-mail de redefinição de senha usa `PORTAL_URL` (React). O fallback
`{PUBLIC_BASE_URL}/portal/reset-password/<token>`, apesar de comentado como "rota Jinja legada",
na porta pública cai no bundle React — o proxy não repassa esse caminho. Apagar a rota Jinja
homônima **não** mata o link.

### Fase 3 — Blueprints substituídos 1:1 · ⚠️ **PRÉ-REQUISITO CONCLUÍDO em 19/08** (commit `7512f7d`)

> **A fase 3 não era uma remoção limpa, e o plano original errava nisso.** A varredura de imports
> revelou que **cinco módulos vivos importavam lógica de negócio de dentro dos `routes.py` Jinja** —
> o caso do `feedback` (§3.1) era a ponta de um padrão sistêmico, não uma exceção. Apagar os
> blueprints sem tratar isso derrubaria a API React.
>
> **Já resolvido**, e `main` não tem mais nenhum `from app.<blueprint>.routes import`:
>
> | De onde saiu | Para onde foi | Quem importava |
> | --- | --- | --- |
> | `gastos/routes.py` | `gastos_ops` (já era lá; o Jinja só re-exportava) | `api/dashboard_service`, `api/financeiro_read` ×2, `financeiro/routes` ×2 |
> | `talents/routes.py` (`_parse_period`, um alias) | `talents/rating_ops` | `clientes/client_ops` |
> | `feedback/routes.py` (etiquetas + regra por nota) | **`feedback/feedback_ops.py`** (novo) | `api/feedback_write`, `clientes/client_ops` |
> | `formularios/routes.py` (**271 linhas**, 14 símbolos) | `formularios/formularios_ops.py` | `api/formularios_write`, `api/catalogo_read`, `calendar/sync`, `cli` |
>
> O corte do `formularios` foi deliberadamente **não contíguo**: os decorators de RBAC usam
> `current_user` e `abort`, então são camada de rota e ficaram. `routes.py` foi de 631 para 361
> linhas.
>
> **Lição para as fases seguintes:** antes de apagar qualquer blueprint, rodar
> `grep "from app\.<nome>\.routes import"` no repo inteiro. O `calendar` e o `financeiro` (§3.4)
> têm a mesma doença, em escala maior e com *imports tardios* dentro de função — que o grep pega,
> mas a leitura casual não.

**O que falta na fase 3:** apagar de fato as rotas e os templates dos blueprints abaixo. O caminho
agora está livre.

Cada um tem página React e endpoints `/api` equivalentes, e nenhum está no proxy:

`admin` (24) · `talents` (13) · `clientes` (7) · `gastos` (18) · `revisao` (14) · `orcamento` (14) ·
`formularios` (17) · `catalogo` Jinja (5)

Com as decisões respondidas, esta fase **cresceu e simplificou ao mesmo tempo**:

- `/figurinos/sync-drive` e o `/stream` entram aqui (decisão 1: rodou uma vez, não volta) — mais 2
  rotas e menos ~160 linhas de parser de Google Docs.
- `revisao_bp` sai **inteiro**, `invite_text` incluído (decisão 3: ninguém usa pelo host direto).
- Os formulários Jinja saem **sem redirect de compatibilidade** (decisão 4: só circulam links
  novos).

Dois avisos:

- **Catálogo:** `/catalogo/midia` e `/catalogo/og` são rotas de arquivo e **ficam**. As páginas
  Jinja `/catalogo/<slug>` etc. estão sombreadas pela SPA desde a feature 186 — a prévia de link do
  WhatsApp hoje nasce no `server.js`, não mais nelas.
- **Formulários:** `/f/pre-contrato` e `/f/corporativo` já não são alcançáveis (`server.js`
  redireciona `/f/*` para o React da vitrine). Antes de apagar, confirmar que nenhum link
  divulgado aponta para o domínio direto do Flask — o histórico pré-2026 veio desses formulários.

`app/orcamento/pdf.py` gera o PDF programaticamente, sem template. O PDF não corre risco.

### Fase 4 — As decisões que são suas

> **TODAS RESPONDIDAS pelo João em 19/08/2026.** O registro abaixo virou histórico; o efeito de cada
> resposta já está refletido nas fases. Resumo do que mudou: o sync do Drive e o blueprint da
> revisão saem sem substituto (menos trabalho); **agrupar/desagrupar vira feature obrigatória a
> construir** (mais trabalho); os itens 6, 7 e 8 viram uma feature só; e os dois CSVs saem da raiz
> com ajuste de código.

**Grupo A — só o João sabe responder**

1. ~~O sync de fichas do Google Drive (`/figurinos/sync-drive`) ainda é usado?~~
   **RESPONDIDO (19/08): rodou uma vez só, não será mais usado.** Sai na Fase 3 sem substituto,
   levando junto as ~160 linhas de parser de Google Docs. `docs/04` e `docs/05` precisam parar de
   tratá-lo como funcionalidade viva.
2. ~~Alguém ainda agrupa / desagrupa / renomeia grupo de eventos?~~
   **RESPONDIDO (19/08): SIM, é importantíssimo — "se não está no novo, precisa estar".**
   Virou feature própria: ver §7. Uso real medido no espelho: **19 agrupamentos** (jun–jul/2026),
   **0 desagrupamentos**, 2 renomeações. Desagrupar nunca foi usado mas é **estruturalmente
   obrigatório** (ver §7.2). Renomear vale incluir: custa ~40 linhas e o nome aparece em produção
   no dashboard financeiro e no pipeline de vendas.
3. ~~Alguém abre as páginas de revisão pelo host direto do Flask?~~
   **RESPONDIDO: não.** `revisao_bp` inteiro sai na Fase 3, `invite_text` incluído — sem substituto.
4. ~~Algum link de formulário divulgado aponta para o domínio do backend?~~
   **RESPONDIDO: não — clientes e talentos recebem os links novos.** Os formulários Jinja saem na
   Fase 3 sem redirect de compatibilidade. **Cuidado:** esta resposta *não* cobre o `/avaliar`
   (§3.1) — aquele link sai com o domínio novo mas o caminho continua sendo servido pelo Jinja.
5. ~~Outro agente de IA que leia `.agents/skills`?~~
   **RESPONDIDO: não, só Claude.** `agent/`, `.agents/` e `skills-lock.json` podem sair da raiz.

**Grupo B — construir o substituto ou abrir mão**

6. **Troca obrigatória de senha temporária de staff** — **CONSTRUIR.**
7. **Foto de perfil do usuário** (`PATCH /api/me` com upload) — **CONSTRUIR.**
8. **Reset de senha de talento pelo admin** — **CONSTRUIR.**

Os três viram uma feature só, "auto-serviço de conta", que também libera a Fase 7.

**Grupo C — arrumação de raiz**

9. CSV do Kommo — **RESPONDIDO: já importado, pode sair** (baixar de novo é rápido). Trocar o
   default de `app/cli.py:20` para exigir caminho explícito no mesmo commit.
10. `Produtos Catalogo/` — **RESPONDIDO: export do WordPress já importado, pode sair.** O botão de
    re-import da SPA existe, está vivo **e é um no-op** — ver §7.4 para o que apagar junto.

**Grupo D — método**

11. Fase 0 (`410 Gone` + log) — **prejudicada**: existia para responder 1, 2 e 3 com dado real, e o
    João respondeu as três diretamente. Continua valendo só como rede contra uso desconhecido do
    host direto. *Recomendação revisada: pular*, e confiar no commit por fase com `git revert`.

> **O que NÃO é decisão** (obrigatório, em qualquer cenário): trocar o `login_view` antes de tocar
> no `auth`; pôr o redirect no `/avaliar` antes de apagar o feedback; dar à API a escrita de
> acréscimo/nota/parcela antes da Fase 6; corrigir o sync de comissão em
> `event_ops.update_event_comercial`; apagar página e templates no mesmo commit.

### Fase 5 — `/avaliar` · ⚠️ **METADE FEITA em 19/08** (commit `d4d16cc`, branch `241-avaliar-aponta-para-react`)

> **Feito:** `GET /avaliar/<token>` virou 302 para `/catalogo/avaliar/<token>` e os dois geradores
> emitem o endereço novo. Nenhuma cliente cai mais no Jinja. `verify_241`: 11/11.
>
> **Falta**, e é bloqueante para apagar `feedback_bp`: extrair `POSITIVE_TAGS`, `ATTENTION_TAGS` e
> `_tags_for_score` de `app/feedback/routes.py` para um `feedback_ops.py`, porque
> `app/api/feedback_write.py:18` os importa de lá — **apagar o arquivo hoje derruba a API React**.
> Depois disso saem o POST Jinja, `feedback/public.html` e `feedback/invalid.html`.

Trocar os dois geradores de link para `/catalogo/avaliar/<token>`, transformar `/avaliar/<token>`
em redirect 302 (no `server.js` ou no Flask, preservando os tokens antigos) e só então apagar
`feedback_bp` e `feedback/*.html`.

### Fase 6 — `calendar` e `financeiro`

A parte cara, e por isso a última. A ordem interna importa:

1. ~~Extrair a régua de comissão de `financeiro/routes.py`~~
   ✅ **FEITO em 20/08** (commit `1343939`). 230 linhas foram para `app/financeiro/comissoes_ops.py`
   — o módulo que já era desse domínio, em vez de um `financeiro_ops.py` novo.

   > **Era o pré-requisito mais perigoso.** `app/api/financeiro_read.py`, que alimenta o DRE, o
   > pipeline de vendas e a planilha de pagamentos do React, importava `_event_commission`,
   > `_event_cost`, `_group_cost`, `_get_commission_rate` e `_resync_pending_commissions` de
   > dentro do blueprint Jinja. Apagar aquele arquivo derrubaria o financeiro inteiro da
   > plataforma nova.
   >
   > **O recorte por intervalo levou junto 4 coisas que são camada de rota** (`_has_role`,
   > `require_financeiro`, `_is_educamanto_responsavel` sem argumento, `require_vendas`) — todas
   > dependem de `current_user`. Foram devolvidas. Quem apontou foi o `ruff --select F821`,
   > reclamando de nomes de requisição dentro de um módulo que deve ser puro.
   >
   > **Verificação à altura de um motor que decide quanto cada vendedor recebe:** comissão, custo,
   > custo de grupo e taxa calculados para os **450 eventos** do espelho antes (worktree do `main`)
   > e depois, comparados item a item — **zero divergências**.
2. Dar à API paridade de escrita para `EventAcrescimo` / `EventInvoice` / `EventInstallment`

   > **Dimensionado em 20/08 — é maior do que este item sugeria.** Confirmado que as três escritas
   > existem **só** em `calendar/routes.py` (acréscimos `:864-893`, notas `:898-960`, parcelas
   > `:968-980`, mais a criação em `:3308-3320`). Mas o bloco não é extraível movendo linhas: ele
   > lê `request.form.getlist("acrescimo_bv_recipient[]")` e afins **linha a linha do formulário**,
   > com upload de arquivo por nota (`nf_file__<key>`). Portar isso é **redesenhar o contrato de
   > entrada** — de listas paralelas de formulário para objetos estruturados —, não mover código.
   >
   > Três regras de negócio que o redesenho não pode perder, e que só aparecem lendo o bloco:
   > - o editor de acréscimos só age **se foi enviado** (`if _acr_tipos:`), senão um POST de outra
   >   seção apagaria todos os acréscimos do evento;
   > - o status de pagamento de BV já existente é **preservado por (recebedor, pix)** — sem isso,
   >   salvar a aba "despaga" um BV já pago;
   > - acréscimo percentual é calculado sobre a venda no momento do save e gravado em `amount_brl`.
   >
   > Estimativa honesta: é uma feature própria (ops + endpoints + UI das três coleções), da ordem
   > da feature de grupos. **Não começar como apêndice de outra tarefa.**
   >
   > **PRIMEIRA METADE FEITA em 20/08** (commit `88ba7a7`): `app/calendar/comercial_ops.py` tem o
   > núcleo puro das três coleções, com contrato de lista de dicionários no lugar das listas
   > paralelas de formulário. O handler Jinja traduz e delega — comportamento inalterado, e as
   > duas superfícies vão compartilhar a regra quando a API chegar.
   > `verify_249_comercial_ops.py`: **17/17**, cobrindo as quatro regras delicadas (a quarta
   > apareceu escrevendo o teste: anexar arquivo emite a nota, mas `issued_at` só é carimbado na
   > transição — salvar de novo não reescreve a data de emissão).
   >
   > **Falta:** os endpoints e a UI das três coleções.
3. ~~Corrigir `event_ops.update_event_comercial` para chamar `_sync_commission_payment`~~
   ✅ **FEITO em 20/08** (commit `a01ab48`). A função recebe `sincronizar_comissao` injetada, como
   o `group_ops`. **Provado antes do conserto:** venda de R$ 5.000 com vendedor comissionado
   gerava zero linhas de comissão pela API.

   > **O estrago era pequeno, e vale escrever por quê — para ninguém procurar um rombo que não
   > existe.** `_resync_pending_commissions()` roda a cada abertura da tela de comissões ou de
   > pagamentos (`api/financeiro_read.py:566` e `:670`) e recalcula **toda** linha *a pagar*. A
   > auditoria do espelho achou **zero** linhas `a_pagar` com valor divergente. As 6 divergências
   > existentes são todas `pago` ou `cancelado` — que o código congela de propósito, porque
   > registro histórico do que foi de fato pago não se reescreve.
   >
   > **O que sobrava:** o resync só percorre linhas que já existem. Uma venda que nunca gerou
   > linha nenhuma nunca ganhava uma. **São 3 eventos no espelho** — ids `69`, `62` e `203`, todos
   > sem `sale_date`, somando R$ 12.355 de venda. **Não foram tocados:** mexer em comissão
   > retroativa é decisão do João, não efeito colateral de um conserto. Ver a pendência abaixo.
4. **Construir a gestão de grupos na API e na SPA** — confirmado em uso (decisão 1 da Fase 4).
   Agrupar e desagrupar no mínimo; renomear grupo confirmar se também é usado
5. Só então apagar as 18 views Jinja, os 23 handlers `_handle_*` e as 4.992 linhas de template
   (`event_detail.html` sozinho tem 3.201)

   > ⚠️ **MEDIDO em 20/08 — este item está subdimensionado no plano, e por muito.**
   >
   > Depois de limpar o `financeiro`, sobrou o `calendar`, e ele é outra ordem de grandeza:
   > **`app/calendar/routes.py` exporta 47 símbolos distintos, em 86 pontos de import**, para
   > **13 módulos vivos** (`api/agenda_read`, `api/agenda_write`, `api/agenda`,
   > `api/admin_config_write`, `api/dashboard_service`, `calendar/event_ops`, `calendar/sync`,
   > `calendar/cancel_ops`, `calendar/casting_ops`, `figurino/producao_ops`,
   > `marketing/virtuais_ops`, `talents/rating_ops`, `financeiro/routes`) mais 15 scripts de
   > verificação em `scripts/db/`.
   >
   > A maioria **não é view**: `_create_event_core`, `_validate_event_core`, `_query_month_events`,
   > `parse_characters`, `parse_event_type`, `_build_start_end`, os `_CAN_*`, os
   > `_add_*_record`/`_delete_*_record` de pagamento, contrato, nota e reembolso. Ou seja, o
   > arquivo virou uma **biblioteca compartilhada com views penduradas** — apagar as views não o
   > apaga.
   >
   > **Consequência para o plano:** o item 5 não é "apagar as views". É *primeiro* extrair essas
   > ~47 peças para módulos `*_ops.py` (provavelmente 3 ou 4: criação/validação de evento, consulta
   > de mês, registros financeiros do evento, e parsing de título), e só então apagar. É uma
   > sequência de features, não um lote de deleção — e cada extração pede o mesmo tratamento que a
   > do motor de comissão levou: comparar o resultado contra o `main` para os 450 eventos reais,
   > porque `ruff` e `create_app()` não pegam mudança de número.

### Fase 7 — Fechamento

Por último, porque tudo depende disso: `login_view` (§3.2) → apagar `auth` Jinja, `base.html`, os
templates restantes e a poda de `app/static/` (os 7 `.js` morrem com suas páginas).

---

## 5. O que nunca sai

Lista de intocáveis, para consulta rápida durante a execução:

- As **326 rotas `/api/*`**
- **Servir arquivo:** `/uploads/<path>`, `/catalogo/midia/*`, `/catalogo/og/*`, `/portal/photo/*` —
  cerca de 70 pontos de chamada nos três apps passam por `assetUrl()`
- **OAuth:** `/google/connect`, `/google/callback`
- **`/health`** — o `railway.json` faz healthcheck nele; sem ele o deploy não sobe
- `/robots.txt` e o `/` (301 para a plataforma React)
- **Páginas de erro** 403/404/500 + `style.css`, `giphy.gif`, `source.gif`, `apple-touch-icon-*`
- **`figurino_print.html`** + `/figurinos/<id>/print` + `/figurinos/print-event/<id>` — a SPA
  linka (`FigurinoListPage.tsx:128`, `FigurinoSection.tsx:163`); é o único Jinja que a interface
  nova abre de propósito
- `feedback/public.html` e `invalid.html` **até** a Fase 5 estar concluída

## 6. Verificação de cada fase

Em ordem, e nenhuma fase fecha sem as três primeiras passarem:

```bash
python -c "from app import create_app; create_app()"
```

```bash
python scripts/db/verify_206_react_primario.py
```

3. Varredura de `url_for` nos templates que ficaram, procurando endpoints que já saíram
4. Um clique nas superfícies vivas: uma ficha de impressão de figurino, uma foto do portal, um
   `/uploads` autenticado, um link `/avaliar` antigo
5. Só então merge em `main` — que dispara o deploy

Trabalhar em branch por fase, um commit por fase. Assim `git revert` desfaz uma fase inteira sem
tocar nas outras.

---

## 7. Feature nova: gestão de grupos de eventos

Nasceu da decisão 2. **Não é paridade de migração — é lacuna aberta hoje no sistema novo.**

### 7.1 Como funciona hoje

Não existe tabela de grupo: é auto-referência em estrela em `calendar_events`
(`group_leader_id`, `models.py:300`; `group_name` só no líder, `:302`). "Ser líder" não é estado
gravado, é ter filhos (`is_group_leader`, `models.py:398` — property Python, não coluna).
Estado real no espelho: **19 satélites em 5 grupos**, o maior com 13.

Agrupar **zera 15 campos comerciais** do satélite (`_SATELLITE_FIELDS_CLEARED`,
`calendar/routes.py:1484`) — venda, vendedor, comissão, nota, parcelas, vínculo com o orçamento.
**Desagrupar não restaura nada.** Não toca Google Calendar; é só banco.

### 7.2 Três defeitos vivos que a apuração encontrou

Existem **agora**, independentes da remoção do Jinja:

1. **Beco sem saída ao cancelar.** `cancel_ops.py:267` recusa cancelar um líder com
   "Desagrupe os eventos satélites antes", e `ExcluirEventoDialog.tsx:176` exibe essa parede — mas
   **desagrupar não existe na SPA**. Hoje é impossível cancelar um evento líder pela interface nova.
2. **Porta aberta de corrupção.** `PATCH /api/events/<id>/comercial` (`agenda_write.py:923`) **não
   checa `is_satellite`**. A SPA deixa gravar venda num satélite — coisa que o Jinja nunca permitiu
   (`event_detail.html:1594`) — e o valor some das métricas, porque `financeiro_read.py:399` pula
   satélites.
3. **Comissão órfã.** Nenhum dos três handlers chama `_sync_commission_payment`. No espelho, o
   evento 287 é satélite com venda zerada e mantém `commission_payments` de R$ 137,50 com status
   *pago*. Corrigir isso é **mudança de comportamento**, não paridade — decidir de propósito.

### 7.2b Decisões do João (19/08) e o que já foi construído

- **Snapshot antes de apagar: SIM.** `group_ops.snapshot_comercial` grava os 14 campos no histórico
  do evento antes de zerar. Não restaura sozinho — serve para consultar e redigitar.
- **Corrigir a comissão órfã: SIM.** `agrupar` recebe `sincronizar_comissao` injetada e a chama
  depois de zerar a venda; com `sale_value` nula a função cancela a linha *a pagar*. Comissão já
  **paga sobrevive** — dinheiro que saiu não se desfaz por software. Sem limpeza retroativa: o
  evento 287 continua com a comissão órfã de R$ 137,50 até alguém decidir mexer nela à mão.
- **Renomear grupo entrou** (2 usos reais no histórico, ~40 linhas).

**BACKEND PRONTO E EM PRODUÇÃO** (`verify_246_grupos_api.py`, 22/22 contra o espelho):

- `app/calendar/group_ops.py` — núcleo puro, compartilhado com os handlers Jinja, que passaram a
  delegar. As duas superfícies não divergem mais.
- Cinco endpoints: `GET .../grupo/candidatos?q=`, `POST/DELETE/PATCH .../grupo` e
  `DELETE .../grupo/satelites/<id>` (este não existe no Jinja e é o que destrava dissolver o grupo
  de 13 satélites sem abrir os 13).
- `GET /api/events/<id>` passou a devolver o bloco `group` e a flag `can_group`.
- **Dois defeitos de produção corrigidos:** `PATCH /comercial` agora recusa satélite (aceitava
  gravar venda que sumia dos relatórios), e `json_error` ganhou `**extra` para o 409 poder dizer
  *o que* será apagado.

**FALTA A TELA.** Sem ela a feature não existe para o usuário — os endpoints estão no ar e ninguém
os chama.

### 7.3 Escopo

**API** (em `app/api/agenda_write.py` / `agenda_read.py` / `agenda.py`): estender
`GET /api/events/<id>` com bloco `group` e flag `can_group`; `GET .../grupo/candidatos?q=` com busca
**server-side** (o Jinja despeja os 354 eventos no HTML — não copiar); `POST .../grupo`;
`DELETE .../grupo`; `DELETE .../grupo/satelites/<id>` (o Jinja não tem, e sem ele dissolver o grupo
de 13 exige 13 navegações); `PATCH .../grupo` para o nome. Mais a guarda de satélite no
`PATCH /comercial`.

A confirmação de perda de dado vira **409 tipado** com `needs_confirmation` e a lista de eventos com
venda — melhor que o checkbox genérico do Jinja, porque a tela mostra o que exatamente será zerado.

**SPA:** `GrupoPanel.tsx` (três estados: satélite, líder, avulso) e `AgruparEventosDialog.tsx` (a
peça cara: busca com debounce, seleção de líder reativa, confirmação em duas etapas), montados no
`ComercialSection`; hooks em `eventOps.ts` invalidando **também** agenda, financeiro e vendas.

**Pré-requisito:** extrair `calendar/routes.py:1484-1685` para `app/calendar/group_ops.py` — que já
era o item 1 da Fase 6.

**Tamanho:** 2 a 2,5 dias, ~900–1.100 linhas líquidas.

**Armadilha a não repetir:** as regras de `routes.py:1554-1569` são o que impede grupo aninhado
(A→B→C). Portar "quase igual" cria hierarquia que `_group_events` (que só olha um nível) ignora em
silêncio, e o financeiro passa a somar errado.

### 7.3b Pendências de comissão para o João decidir (nenhuma foi tocada)

Duas coisas que a apuração encontrou no banco e que **não** foram alteradas, porque mexer em
comissão retroativa é decisão de dono, não conserto técnico:

1. **3 eventos com venda e sem linha de comissão nenhuma** — ids `69` (R$ 4.180), `62` (R$ 6.800)
   e `203` (R$ 1.375), todos com `sale_date` vazio. Depois do commit `a01ab48` basta abrir cada um
   e salvar a aba Comercial para a linha nascer; ou decidir que são antigos demais e ficam como
   estão.
2. **A comissão órfã do evento 287** — R$ 137,50 marcados como *pagos* num evento que virou
   satélite e teve a venda zerada. O cálculo atual diz que deveria ser zero. Comissão paga é
   dinheiro que saiu: só um humano decide se vira estorno ou fica como registro.

As outras 5 divergências entre valor gravado e cálculo atual são todas `pago`/`cancelado` e são
**esperadas** — o histórico do que foi pago não acompanha recálculo.

### 7.4 Decisão do José sobre o `Produtos Catalogo` (item 10)

A apuração achou algo que muda a resposta: **o botão "Importar catálogo" da SPA está vivo e é um
no-op.** O importador pula toda linha com `wp_product_id` já no banco e nunca atualiza
(`catalogo/importer.py:174`), e o CSV é um export **congelado** de 16/07. Os 451 itens já entraram,
então cada clique processa 451 linhas e importa zero. Produto criado no WooCommerce depois daquela
data nunca chega.

Pior: se a pasta sumir sem mexer no código, a falha é **silenciosa** — o `except` amplo
(`importer.py:277`) engole o `FileNotFoundError` e a tela nunca renderiza `report.error`, embora a
API já mande o campo. O superadmin vê o botão piscar e nada acontecer.

*Recomendação: aposentar o recurso* (endpoints de start e status, a página, os hooks e o comando
CLI), já que o catálogo tem CRUD próprio e completo na SPA. Aí sim `git rm -r "Produtos Catalogo/"`
— este é rastreado pelo git, ao contrário do CSV do Kommo.

O CSV do Kommo é trivial: trocar `@click.argument("path", default=...)` por `@click.argument("path")`
em `app/cli.py:20` e o arquivo pode sair. Nunca foi versionado, então nunca esteve no Railway.

---

*Levantamento por varredura completa de rotas, templates, bundles React, links de saída e artefatos
fora de `app/`, seguido de verificação adversarial. Das oito alegações da Fase 1, sete resistiram e
uma caiu (`rh_bp`). A conclusão sobre o `/avaliar` foi testada executando o `server.js` real.*
