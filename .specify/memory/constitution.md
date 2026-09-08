<!-- Sync Impact Report
Version change: 2.2.0 → 3.0.0 (MAJOR: Princípio VI redefinido como esteira em dois níveis com Regra
Zero de numeração; Portões de Qualidade reescritos; seção "Operação e Deploy (Render)" criada;
Governança completa)
Modified principles: II (ruff e comentários), III (camadas reais, sem repositório; Jinja legado
qualificado; registros obrigatórios), IV (portões no lugar de "testes e tsc"), VI (esteira em dois
níveis), VII (a constituição também é Living Spec), VIII (verify_NNN.py em specs/NNN-nome/, contra
manto_local, antes do núcleo)
Added sections: XIII Autorização explícita em toda rota de API; XIV Configuração com default real e
efeito externo travado; Operação e Deploy (Render); Governança (emenda, versionamento, conformidade)
Removed sections: nenhuma (o portão do docs/changelog.html saiu — arquivo congelado e arquivado)
Templates requiring updates: spec/plan/tasks/checklist adaptados na mesma rodada (feature 296)
Follow-up TODOs: nenhum
-->
# Constituição da Plataforma Manto

Este documento define os princípios inegociáveis do projeto. Por adotarmos o Spec-Driven
Development, ele é o DNA arquitetural do sistema e reside em `.specify/memory/constitution.md`.
Toda especificação (`/speckit-specify`), todo plano (`/speckit-plan`) e toda implementação
(`/speckit-implement`) DEVEM respeitá-lo. Os comandos são as skills instaladas em
`.claude/skills/speckit-*/` (versionadas) e os scripts que elas chamam vivem em
`.specify/scripts/bash/` — num clone limpo a esteira existe. Em caso de conflito, esta
constituição prevalece sobre conveniência ou pressa.

## Princípios Fundamentais

### I. Reutilizar antes de criar (NÃO-NEGOCIÁVEL)
Antes de escrever qualquer código novo, é OBRIGATÓRIO verificar se já existe algo parecido no
projeto. Lógica duplicada é a principal causa de bugs e de "saída do padrão" neste sistema.
* Procure componentes React, hooks, rotas de API, utilitários e padrões equivalentes antes de
  implementar.
* Se existir algo parecido mas imperfeito, estenda ou refatore — não crie uma segunda versão
  paralela.
* Um mesmo comportamento (ex.: botão de WhatsApp, cálculo de cachê, parsing de evento, componente
  de Input monetário) deve ter UMA fonte de verdade no código.

### II. Padrões de código Python e TypeScript obrigatórios
Todo código do projeto segue padrões estritos de tipagem e clareza, sem exceções:
* **Backend (Python)**:
  * **Type hints** em todas as funções e métodos.
  * **Docstrings** (Google style) em classes e funções públicas.
  * **Nomes descritivos** — sem abreviações obscuras (`user_count`, não `uc`).
  * **Funções pequenas**: máximo ~30 linhas. Se passar, extraia funções.
  * **Aninhamento máximo de 3 níveis** de indentação.
  * **Constantes em UPPER_CASE** no topo do módulo ou em `config.py` — zero strings mágicas
    espalhadas.
  * **Nunca** usar `except Exception` sem logar o erro (padrão da casa:
    `except Exception as exc:  # noqa: BLE001 — <motivo>` + `logger.warning`).
  * **`ruff check`** limpo nos arquivos tocados; **`ruff format` só em arquivo novo** — legado
    segue o estilo circundante, nunca reformatar arquivo inteiro.
* **Frontend (TypeScript / React)**:
  * **TypeScript estrito**: proibido o uso de `any` explícito ou implícito. Defina
    interfaces/types para todas as props, respostas de API e estados.
  * **Componentes modulares**: componentes funcionais React pequenos e com responsabilidade única.
  * **Estilização**: estritamente via **Tailwind CSS** e **shadcn/ui** (`@manto/ui`). Proibido
    criar arquivos `.css` Vanilla soltos ou estilos inline (`style={{...}}`).
* **Comentário explica o PORQUÊ** (a armadilha, a razão da escolha), nunca o óbvio. Tudo em
  pt-BR — código, comentário e texto de interface.

### III. Arquitetura desacoplada e em camadas (API First)
A separação entre backend e frontend é total:
* **Backend é API JSON em todo código novo**: rota nova nunca retorna HTML; respostas são JSON
  padronizados (`jsonify`), erro no envelope único de `json_error`
  (`{"error": {"message", "fields"}}`). O Jinja legado continua registrado e vivo em parte dos
  domínios (`docs/00` §7, `docs/04`); sua remoção está **pausada por decisão do dono**
  (`docs/PARADA_REMOCAO_JINJA.md`) — não apague nem "limpe" blueprint Jinja de passagem.
* **Camadas reais, dependência só para baixo**: endpoint (`app/api/<dominio>_read.py` |
  `_write.py` — só valida RBAC, chama o núcleo e serializa) → núcleo de negócio
  (`app/<dominio>/<nome>_ops.py` — funções puras, sem `flask.request`/`render_template`/`flash`,
  exceções próprias de validação) → models (`app/models.py`). **Não existe camada de repositório
  neste projeto; não crie uma.**
* Onde o núcleo ainda mora em `routes.py` (calendar, financeiro), os imports são tardios e
  renomear um helper quebra a API em silêncio — leia `docs/00` §7 antes de refatorar.
* **Registros obrigatórios, sem os quais nada acusa erro**: módulo novo em `app/api/` só existe se
  importado em `app/api/__init__.py`; componente novo em `@manto/ui` só existe se exportado em
  `packages/ui/src/index.ts`; rota pública nova fora de `/api` só chega ao Flask se entrar em
  `BACKEND_PREFIXES` (`frontend/server.js`).
* Configuração centralizada em `app/config.py`, **com default real**; variável de ambiente só
  sobrepõe (Princípio XIV).

### IV. Não quebrar o que funciona (NÃO-NEGOCIÁVEL)
Estabilidade vale mais que velocidade.
* Passe pelos Portões de Qualidade (abaixo) ANTES de cada merge — não só antes de "pronto".
* Mudanças em pequenos passos verificáveis; cada funcionalidade = um commit atômico.
* Ao alterar um trecho compartilhado (schemas de API, contratos JSON, `models.py`), verifique
  todos os pontos do frontend e do backend que dependem dele antes de declarar "pronto".
* Se uma mudança toca a interface, confirme no app real que continua funcionando — não confie só
  na leitura do código.

### V. UI/UX moderna, consistente e com feedback (em português)
Toda interface segue o padrão visual moderno (Tailwind + shadcn/ui), fala com o usuário em pt-BR e
**nunca deixa o usuário sem resposta**.
* Design System unificado via Tailwind CSS e componentes shadcn/ui — zero cores ou estilos
  hardcoded fora do tema.
* Todo estado assíncrono (requisições de API) tem feedback visual obrigatório via TanStack Query /
  React: **Skeletons/Loading, erro e sucesso**.
* **Nenhum botão fica "morto" ao ser clicado (NÃO-NEGOCIÁVEL)**: todo botão que dispara uma ação
  (salvar, criar, enviar, sincronizar, aprovar, excluir — rápida ou lenta) DEVE mudar de aparência
  de forma visível ao ser clicado (spinner interno do shadcn/ui, opacidade reduzida, texto
  "Salvando...", estado `disabled`) até a resposta da API chegar. "Cliquei e não vi nada acontecer"
  é sempre um bug de UI. Um clique a mais nunca pode criar registro duplicado.
* **Nunca limpar o que o usuário preencheu**: um erro de validação da API JAMAIS apaga os dados já
  digitados no formulário React. O formulário preserva os estados e aponta o(s) campo(s) com
  problema (`ApiRequestError.fields`).
* **Falha de validação sempre tem feedback visível no campo**: ao bloquear um envio,
  destaque/realce o(s) campo(s) faltante(s) e leve o foco até ele. Bloquear em silêncio é proibido.
* Ações destrutivas (deletar, remover) exigem confirmação via `Dialog`/`ConfirmDialog` do
  `@manto/ui`.
* Mensagens de erro são amigáveis e exibidas via Toasts/Alerts em pt-BR — nunca expor stack trace
  ou erros brutos do banco ao usuário final.

### VI. Spec-Driven Development em dois níveis (NÃO-NEGOCIÁVEL)
Nenhuma mudança começa direto no código. O repositório pratica **dois níveis**; os dois têm pasta
em `specs/`, verificação e entrada no `docs/03`.

**Regra Zero — numeração.** O número da mudança nasce em `specs/`: no Nível 1 pelo
`/speckit-specify` (o hook `before_specify` aloca `NNN = max(pastas em specs/, branches locais,
refs remotos) + 1`, cria a branch `NNN-nome`, e a skill cria `specs/NNN-nome/` e grava
`.specify/feature.json`); no Nível 2 pela pasta criada à mão. `docs/03` **registra** a entrega —
não aloca nem reserva número; plano que enumera trabalho futuro usa números provisórios. Hotfix de
feature entregue herda o número da mãe com sufixo (`267b`, `269c`) e não consome número novo (o
alocador ignora sufixos). Toda mudança entregue tem pasta em `specs/` — "só entrada no docs/03"
não é um nível. Antes de qualquer `/speckit-*`, `.specify/feature.json` aponta para a pasta em
que se está trabalhando; nunca apague o arquivo (sem ele os scripts abortam).

**Nível 1 — FEATURE.** Obrigatório quando há migration, endpoint novo, tela nova, mais de um
domínio, ou quando o dono chamar de feature. Sequência completa, um comando por vez, sempre com
hífen: `/speckit-specify` → `/speckit-clarify` → `/speckit-plan` → `/speckit-checklist` →
`/speckit-tasks` → `/speckit-analyze` → `/speckit-implement` → `/speckit-converge`. Artefatos
mínimos em `specs/NNN-nome/`: `spec.md`, `plan.md`, `tasks.md`, `checklists/`, `verify_NNN.py`.
A esteira é executada pelas skills, uma a uma; não há workflow automatizado.

**Nível 2 — CORREÇÃO.** Hotfix de feature entregue; ajuste pequeno, num só domínio, sem
migration; mudança só de documentação ou do harness. Artefatos mínimos: `specs/NNN[b]-nome/spec.md`
curto (cabeçalho Branch · Created · Status · Migration; "O pedido"; "O que muda"; "Verificação";
"Fora de escopo"), `verify_NNN[b].py` quando tocar comportamento, entrada no `docs/03`. Branch
`NNN[b]-nome` criada da `main`; `.specify/feature.json` apontado para a pasta. Dos comandos, só
`/speckit-clarify` se aplica (roda em `--paths-only`); `checklist`, `analyze`, `implement`,
`converge` e `taskstoissues` exigem `plan.md` e não se rodam. **Escalada:** se a correção precisar
de migration ou tocar um segundo domínio, vira Nível 1 antes de codar.

**Hooks e commits.** Só `before_specify` fica ligado em `.specify/extensions.yml`; os
auto-commits do Spec Kit ficam desligados. Commits seguem `feat(NNN):`, `fix(NNNb):`,
`docs(NNN):`, `merge: …`, sempre por caminho — nunca `git add -A` (a raiz tem tokens e arquivos
não versionados).

### VII. Living Spec (persistência da especificação)
O modelo adotado para o ciclo de vida das features é o **Living Spec**.
* Quando o comportamento desejado do sistema mudar, a alteração é feita **PRIMEIRO** no `spec.md`.
* Depois da spec, os artefatos de planejamento (`plan.md`, `tasks.md`) e o código são regenerados
  ou revisados a partir dela. A especificação não é descartável: é o contrato atualizado do produto.
* **A constituição também é Living Spec**: mudança de infraestrutura, de esteira ou de padrão
  obrigatório entra aqui **no mesmo ciclo** da mudança, com bump de versão e Sync Impact Report.

### VIII. Verificação antes do núcleo (Test-First)
Não há pytest nem `tests/`. A verificação funcional é `specs/NNN-nome/verify_NNN.py`, executado
contra `manto_local` (espelho da produção, Postgres), **escrito antes** do núcleo de negócio e
listado no `tasks.md` na fase Foundational — falha primeiro pelos motivos certos, passa ao fim de
cada história. Um verify que passa sem exercitar nada é defeito do verify:
* escrita conferida por **conexão separada** (o autoflush da própria sessão esconde falta de commit);
* login **só** por `POST /api/auth/login` com usuário descartável (sessão montada à mão devolve 401);
* requisições HTTP **fora** de `app.app_context()` (contexto persistente vaza o usuário entre
  requisições);
* cookie montado à mão exige `test_client(use_cookies=False)`;
* todo verify de autorização tem um cenário que **deve falhar**;
* limpeza no `finally`, com `rollback()` antes e `user.roles.clear()` antes de apagar usuário.
Roda com `DATABASE_URL` de `.local-db-url`, `FLASK_ENV=development` e `MANTO_SEM_THREADS=1`.
Esqueleto e armadilhas: `DEVELOPMENT.md` §"Escrever um verify" e a skill `manto-verify`. Os
verifies anteriores à 266 vivem em `scripts/db/` (não versionado).

### IX. Valores monetários sempre no padrão brasileiro (NÃO-NEGOCIÁVEL)
Todo valor em dinheiro, em QUALQUER lugar do sistema, é formatado no padrão brasileiro
(ex.: R$ 4.000,00, R$ 1.234,56). Padrão americano é proibido.
* **Na exibição**: nenhum valor monetário aparece "cru". Sempre milhar com `.`, decimal com `,` e
  duas casas.
* **Na digitação**: todo campo de entrada de valor usa o componente React de Input Monetário
  dedicado, que formata automaticamente enquanto o usuário digita.
* **Fonte única (NÃO-NEGOCIÁVEL)**: a formatação para exibição e a máscara de digitação usam a
  biblioteca `@manto/money` — proibido reinventar formatação por tela.
* **No backend o valor continua numérico**: a máscara é só de apresentação; o JSON e o Python
  operam e persistem como `Numeric/Decimal` (`ROUND_HALF_UP`, 2 casas). Centavos só existem na
  fronteira da operadora de pagamento.

### X. Superfícies públicas são mobile-first
O Portal do Artista, o `/cadastro` público, os formulários `/f/*`, a vitrine e o espaço de
revisão são usados majoritariamente em smartphones. Toda tela nestas superfícies DEVE:
* Funcionar sem rolagem horizontal de 320px a 430px de largura.
* Ter alvos de toque confortáveis (≥ 44px) nas ações principais.
* Não usar texto informativo abaixo de 12px.
* Ser conferida em viewport mobile ANTES de declarar pronto.

### XI. Movimento fluido e com propósito (Framer Motion)
Uma mudança de estado visual sem transição vira um "tranco".
* Toda mudança de página, abertura de modais/drawers, expansão de cards e atualizações de listas
  DEVEM utilizar transições suaves do **Framer Motion** (150–350ms).
* **Respeita `prefers-reduced-motion` (NÃO-NEGOCIÁVEL)**: todo uso do Framer Motion DEVE respeitar
  `useReducedMotion()`.
* O movimento comunica causa e efeito.

### XII. Tratamento de dados complexos, comboboxes e autocomplete (NÃO-NEGOCIÁVEL)
1. **Fim dos dropdowns estáticos grandes**: campo de seleção com **mais de 10 itens** NUNCA é um
   `<select>` nativo. Usa obrigatoriamente o `Combobox` pesquisável de `@manto/ui`.
2. **Visualizadores inline (avatares e miniaturas)**: buscas de Talento ou Personagem/Figurino
   exibem miniatura (**circular** para pessoas, **quadrada** para figurinos/personagens). Sem foto,
   placeholder (`AvatarThumb`); imagem que falha vira fallback (`Foto`), nunca quadrado quebrado.
3. **Autocomplete de endereço mandatório**: todo input de endereço usa o `GoogleAddressInput`.
4. **A chave do Google nunca vai para o navegador**: passa via endpoint do Flask (lendo
   `SiteSetting.google_maps_api_key`).
5. **Economia de quota é regra**: busca preditiva é sempre debounced (hoje 350ms, mín. 3
   caracteres).

### XIII. Autorização explícita em toda rota de API (NÃO-NEGOCIÁVEL)
* **Papéis** são os de `RoleName` em `app/constants.py` (SUPERADMIN, CASTING, FIGURINO, COMERCIAL,
  FINANCEIRO, ENSAIO, REVENDEDOR_EDUCAMANTO, MARKETING, ARTISTA_3D). Papel novo entra ali e é
  semeado por `seed.py`, nunca por migration.
* **SUPERADMIN passa em tudo** (`User.has_permission`, `app/models.py`). O gate é uma **função
  chamada no início da view** (`_has_role(...)`, `_require_*`), nunca decorator herdado do Jinja; o
  módulo declara a intenção num comentário `RBAC:` no topo e a tabela de gates fica em `docs/01`
  §4.3. Ler o nome do gate não basta (`_require_vendas` tem dois significados) — abra o arquivo.
* **Endpoint sem gate explícito não existe**: rota nova nasce com o papel declarado no plano e na
  tabela. Escrita financeira (pagamento de cachê, reembolso, status de planilha) é FINANCEIRO ou
  SUPERADMIN.
* **O frontend nunca decide RBAC**: ou o payload traz a chave (bloco ausente = seção não renderiza)
  ou traz `flags.*`. Arquivo servido pelo Flask devolve **404, não 403**, para não confirmar
  existência; recurso de outro dono também.
* `permissions`/`role_permissions` é mecanismo vestigial (só `user.manage`); não construa sobre ele.

### XIV. Configuração com default real e efeito externo travado (NÃO-NEGOCIÁVEL)
* **Env nova é dívida operacional.** Tudo de que o sistema precisa tem default real em
  `app/config.py`; a variável de ambiente só sobrepõe. Onde não há default possível (segredo),
  `create_app` grita a ausência no log do deploy e a feature entra em `docs/05` como desligada até
  o dono preencher o painel — foi assim que `AUDIT_AGENT_TOKEN` e `MARKETING_AGENT_TOKEN` sumiram
  na migração para o Render.
* **Endereço público é constante do código.** Todo link que sai do sistema (e-mail, mensagem
  copiada, webhook, retorno de checkout) monta a URL a partir de `PORTAL_BASE_URL` /
  `PLATFORM_BASE_URL` via `_url_para_fora` (`app/config.py`); um endereço local em `PORTAL_URL` /
  `PUBLIC_BASE_URL` é ignorado por quem envia de verdade. Proibido `url_for(_external=True)` ou
  `request.url_root` em conteúdo que sai (hotfix 269b).
* **Integração externa nasce travada.** Escrita em serviço de fora (Google Agenda, e-mail,
  InfinitePay, WhatsApp, Drive) entra com a trava `_suppress_*` derivada do host do banco
  (localhost = não escreve) e o escape explícito `*_ALLOW_LOCAL_*=true`, **no mesmo commit** da
  feature — `manto_local` é espelho da produção e traz token e credenciais reais.

## Stack e Restrições Técnicas
* **Arquitetura**: SPA desacoplada — Flask servindo API JSON em `/api/*` + três SPAs React
  (`frontend/apps/{internal,public,portal}`) sobre três pacotes
  (`frontend/packages/{ui,api-client,money}`), servidas por `frontend/server.js`, que faz proxy de
  `/api` e da mídia para o Flask.
* **Backend**: Python 3.11 + Flask + SQLAlchemy + Alembic (migrations à mão). **Frontend**: React +
  Vite + TypeScript + Tailwind CSS + shadcn/ui + Framer Motion + TanStack Query.
* **Banco**: PostgreSQL em produção (Render, serviço `manto-postgres`, blueprint `render.yaml`);
  cópia local da produção `manto_local` (Postgres) para desenvolvimento e verificação — **nunca** o
  SQLite vazio de `instance/` (ele só faz o app subir). Scripts locais em `scripts/db/` (não
  versionado).
* **Migrations SEMPRE escritas à mão**: toda mudança em `app/models.py` gera migration manual
  (`down_revision` = head atual, só a mudança da feature). `flask db migrate` (autogenerate) é
  proibido: o drift antigo entre modelo e banco entraria na migration e o `flask db upgrade` do
  start derrubaria a produção.
* **Jinja legado**: proibido em código novo (`render_template`, templates, HTML/CSS/JS vanilla,
  jQuery, Bootstrap, `querySelector`). O que existe continua registrado e vivo em parte dos
  domínios; a remoção está pausada por decisão do dono (`docs/PARADA_REMOCAO_JINJA.md`).
* **Ambiente de desenvolvimento**: Windows 11 + PowerShell 5.1 + Git Bash (regras de ferramental
  no `CLAUDE.md`); produção é Linux.
* **Segredos**: nunca commitar senhas, tokens ou chaves. Vivem no `.env` local do dono e no painel
  do Render (`sync: false`).

## Operação e Deploy (Render)
Regras operacionais — o detalhe técnico mora em `docs/01` §5 e o procedimento em `DEVELOPMENT.md`:
1. **Push na `main` é o deploy.** Não há staging. "Push" significa merge da branch na `main` +
   `git push origin main`, e só acontece quando o dono pede. Publicar em lote, fora do horário da
   equipe; cada deploy abre ~1 min de 502 na porta pública (o frontend não tem healthcheck).
2. **`startCommand` do `manto-backend` muda em commit sozinho**, fora do horário, com os Events do
   Render abertos, depois de `python scripts/validar_startcommand.py` verde. O serviço tem disco:
   start que falha deixa a produção fora.
3. **Backend vivo se prova por um endpoint `/api/` devolvendo JSON** — nunca por `/health` na URL
   pública (cai no fallback da SPA e responde 200 com o Flask morto). 502 isolado nos minutos após
   o push é troca de container, não regressão.
4. **Comando de manutenção roda no `manto-backend`** (SSH ou Shell do Render) com
   `MANTO_SEM_THREADS=1`; deploy troca o container (mata `nohup`, limpa `/tmp`, que é RAM) —
   rodada longa só sem push na fila.
5. **Migração destrutiva é ensaiada** em banco descartável restaurado de dump fresco, rodando a
   sequência real `flask db upgrade && python seed.py`, antes do merge.
6. **Variável de ambiente nova nasce desligada em produção** (Princípio XIV): o dono preenche o
   painel; até lá a feature está registrada como pendente em `docs/05`.
7. **Antes de dizer "está em produção"**: `git status --short` limpo, `git log --oneline -1`
   batendo com o cabeçalho do `docs/03`, `migrations/versions/` sem untracked, sonda `/api/` com
   JSON.

## Portões de Qualidade (antes de "pronto")
Uma tarefa só está concluída quando:
* [ ] **Typecheck limpo nas três SPAs** — `cd frontend && npm run typecheck` (internal + public +
  portal; `frontend/package.json`). `npx tsc --noEmit` app a app **não** satisfaz este portão:
  esquece o portal.
* [ ] **`ruff check`** limpo nos arquivos Python tocados; `ruff format` só em arquivo novo.
* [ ] **`verify_NNN.py` verde contra `manto_local`**, com escrita conferida por conexão separada e
  um cenário que falha — nunca contra o SQLite.
* [ ] **Tela aberta de verdade** quando toca UI (`tsc` limpo não é verificação de UI; campo novo do
  payload é opcional no React até backend e bundle estarem na mesma versão); superfície pública
  conferida em viewport mobile.
* [ ] **Migration manual** criada e aplicada no `manto_local` se `models.py` mudou; migração
  destrutiva ensaiada em banco descartável (`DEVELOPMENT.md` §Migrations).
* [ ] **`scripts/validar_startcommand.py` verde** se tocou o `startCommand` do `render.yaml` — e
  a mudança em commit isolado.
* [ ] **Gate de RBAC declarado** em todo endpoint novo ou alterado (Princípio XIII) e linha na
  tabela de `docs/01` §4.3.
* [ ] **Documentação viva por fonte única** (`docs/00` §10): `docs/01` (contrato/schema/deploy),
  `docs/02` (tela) e `docs/03` (entrada nova no topo, append-only) sempre; `docs/00`, `docs/04` e
  `docs/05` quando a mudança tocar topologia/convenção, invariante de domínio ou dívida.
* [ ] **Nível 1**: `/speckit-converge` executado sem gaps. **Nível 2**: `spec.md` marcada
  "Entregue" com o resultado do verify.
* [ ] **Antes de "em produção"**: `git status --short` limpo, `git log -1` = cabeçalho do
  `docs/03`, `migrations/versions/` sem untracked, sonda `/api/` com JSON.

## Governança
* Esta constituição prevalece sobre qualquer outra prática ou atalho. `CLAUDE.md` traz regras de
  trabalho e ponteiros, nunca princípios novos.
* Toda complexidade adicional precisa ser justificada em planejamento. Planos (`plan.md`) e
  tarefas (`tasks.md`) que violem um princípio se corrigem antes da implementação, não depois;
  `/speckit-analyze` trata conflito com a constituição como CRITICAL — princípio que precisa mudar
  muda aqui, não no plano.
* **Emenda**: qualquer sessão pode propor; o dono aprova. Entra em commit
  `docs(NNN): constituição vX.Y.Z`, com o Sync Impact Report (comentário HTML no topo) e a entrada
  de changelog atualizados. Mudança de infraestrutura, de esteira ou de padrão obrigatório entra no
  mesmo ciclo da mudança (Princípio VII).
* **Versionamento** (semântico): MAJOR = remoção ou redefinição de princípio ou de portão; MINOR =
  princípio/seção nova ou orientação materialmente ampliada; PATCH = redação, typo, ponteiro.
* **Conformidade**: os Portões de Qualidade são conferidos no fim de cada mudança e a entrada no
  `docs/03` é o registro. A constituição chega às skills `speckit-*` em tempo de execução — o que
  está aqui é o que o plano e as tarefas vão cobrar.

**Versão**: 3.0.0 | **Ratificada**: 2026-07-20 | **Última alteração**: 2026-09-08

**Changelog**
* **3.0.0** (2026-09-08): Revisão do harness (feature 296) após a migração Railway → Render
  (28/08/2026; `docs/03` 264) e após seis semanas em que a esteira praticada divergiu da declarada
  (última esteira completa: 255). Princípio VI redefinido como esteira em dois níveis com Regra Zero
  de numeração em `specs/`; sintaxe dos comandos corrigida para hífen (`/speckit-plan`) — a
  afirmação da 2.2.0 de que a sintaxe era com ponto nunca correspondeu à instalação
  (`integration.json: invoke_separator "-"`); VIII alinhado ao `verify_NNN.py` em
  `specs/NNN-nome/`; XIII (RBAC, regra perdida na 2.2.0 — ver `docs/archive/constitution-2.1.0.md`)
  e XIV (configuração e efeito externo) acrescentados; seção Operação e Deploy (Render); Portões
  reescritos (typecheck das três SPAs, verify por conexão separada, tela aberta, ensaio de migração
  destrutiva, RBAC declarado, validador do `startCommand`); Governança completa; headings
  normalizados ao template do Spec Kit; Stack diz Render.
* **2.2.0** (2026-07-30): Adaptação ao fluxo oficial do Spec Kit v0.15+. Inclusão do Caminho
  Completo (Clarify, Checklist, Analyze, Converge) e dos Princípios VII (Living Spec) e VIII
  (Test-First). O arquivo foi movido para `.specify/memory/constitution.md`. *(A frase "sintaxe
  atualizada de hifens para pontos" estava errada — corrigida na 3.0.0.)*
* **2.1.0** (2026-07-28): Novo princípio — dados complexos, comboboxes e autocomplete (`<select>`
  nativo proibido acima de 10 itens).
* **2.0.0** (2026-07-20): MIGRAÇÃO ARQUITETURAL MAJOR. Transição do frontend estático para SPA em
  React (Vite) + TS + Tailwind. Backend restrito a API JSON.
