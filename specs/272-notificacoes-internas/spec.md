# Feature 272 — notificações internas: o aviso deixa de ser e-mail e passa a morar no ERP

*(fundação genérica; a v1 substitui o e-mail de resposta de formulário da 266 e prova a base com
avaliação recebida e convite recusado)*

**Branch**: `272-notificacoes-internas` · **Created**: 2026-09-01 · **Status**: Draft
**Migration**: sim — `migrations/versions/b7d2e4f1a9c3_notifications.py` (revision provisória
`b7d2e4f1a9c3`, `down_revision = "a1c7d3e59b02"`; confirmar o head com `flask db heads` antes de
criar o arquivo). Puramente aditiva: uma tabela nova, nenhuma coluna em tabela existente.

## Problema

A 266 fez o lead aparecer mandando **e-mail** para COMERCIAL/SUPERADMIN a cada resposta de
formulário (`_avisar_comercial`, `app/api/formularios_write.py:74-95`, chamada em `:147` →
`send_form_response_email`, `app/email_service.py:443-490`). O dono foi textual: não gosta de
receber e-mail quando a cliente preenche formulário, e quer um sistema de notificações **dentro do
app**.

O e-mail erra em três coisas que uma notificação in-app acerta:

| | E-mail | Notificação no ERP |
|---|---|---|
| Chega | empurrado, fora do sistema, na caixa pessoal | disponível quando a pessoa olha, no lugar onde ela vai agir |
| Contexto | link absoluto que depende de `PUBLIC_BASE_URL` (o mesmo tipo de dependência do ambiente que a 269 acabou de tirar das mensagens do portal) | caminho relativo da SPA — `/formularios?resposta=<id>`, o deep-link que a 266 já entregou (`FormulariosAdminPage.tsx:670-690`) |
| "Já vi" | não existe; cada e-mail é uma decisão de apagar | `read_at` por pessoa; a contagem no sino cai sozinha |

E o e-mail de formulário não é o único fato do sistema que ninguém fica sabendo. A análise que
originou as ondas (`specs/266-costuras-funil/analise-integracao.md`, §3.4) registra que "feedback
recebido não notifica ninguém, nem nota 1"; e a recusa de convite pelo talento
(`app/talent_portal/portal_ops.py:286-293`) só aparece se alguém abrir a Home e olhar o painel de
casting (`rejected_invites`, `app/api/dashboard_service.py:51-56`). As ondas 3 e 4 do programa
(lembretes de parcela D-3/D0/D+3, follow-up de orçamento, aniversário da criança) são, todas,
"alguém precisa ficar sabendo de X" — e hoje a única ferramenta para isso é mais e-mail.

Não existe nada reaproveitável para isso no banco: `AuditLog` (`app/models.py:584-599`) é centrado
no **ator** ("quem fez o quê"), sem destinatário, sem estado de leitura, em `utcnow`, e nem é
chamado nos POSTs públicos. Uma notificação é centrada no **receptor**.

## Solução

Uma fundação pequena — **uma tabela, um módulo `*_ops`, quatro endpoints, um sino** — e três
produtores na v1. Os produtores das ondas 2-4 entram depois como constante no catálogo + uma
chamada no ponto onde o fato nasce, sem tocar em tabela, endpoint ou UI.

### O que é uma notificação aqui

Um **registro derivado de um fato que o banco já gravou**, endereçado a **pessoas concretas**
(resolvidas por papel no momento da emissão), com texto pronto em pt-BR e um caminho da SPA para
agir. Ela nasce no **mesmo ponto do código** que grava o fato e, quando o fato ainda não foi
comitado, na **mesma transação**.

### Modelo de dados

Tabela `notifications`, model `Notification` em `app/models.py` (ao lado de `AuditLog`, `:584`,
o parente mais próximo em vocabulário). **Uma linha por destinatário** (fan-out na escrita).

| Coluna | Tipo | Por quê |
|---|---|---|
| `id` | Integer PK | `Integer` como as 68 tabelas; o volume (ver retenção) nunca chega perto |
| `user_id` | Integer FK `users.id` `ondelete=CASCADE` NOT NULL | quem recebe. CASCADE porque o repositório apaga usuário de verdade (`app/admin/user_ops.py:442`) e a receita dos `verify_*` também |
| `kind` | String(40) NOT NULL | valor do catálogo (`form_response.nova`, `avaliacao.recebida`, `convite.recusado`); ícone no front e filtro de uma futura tabela de preferências |
| `severity` | String(10) NOT NULL, `server_default='info'` | `info` \| `urgent`. String, não boolean: um nível intermediário futuro entra sem migration |
| `title` | String(200) NOT NULL | texto pronto |
| `body` | String(500) NULL | texto pronto |
| `link_path` | String(300) NULL | caminho **relativo** da SPA interna; nunca URL absoluta |
| `entity_type` | String(30) NULL | `form_response` \| `client_feedback` \| `event_role` — mesma dupla do `AuditLog` (`:595-596`) |
| `entity_id` | Integer NULL | referência **fraca**, sem FK: a tabela é transversal e uma FK por domínio a acoplaria a todos |
| `dedupe_key` | String(120) NOT NULL | `<kind>:<entity_id>[:<marcador>]` — a identidade do aviso |
| `created_at` | DateTime NOT NULL, `default=now_sp` | relógio canônico (`app/constants.py:257`); ver decisão 8 |
| `read_at` | DateTime NULL | NULL = não lida. É o **único** estado; não existe "arquivada" |

Índices e restrições (todos declarados em `__table_args__` **e** na migration — um `flask db
migrate` futuro que não veja o índice parcial no model propõe `drop_index` e derruba o
`startCommand`; memória `manto_alembic_drift_autogenerate`):

- `UniqueConstraint("user_id", "dedupe_key", name="uq_notifications_user_dedupe")` — a trava de
  idempotência é o banco (docs/00 §6 item 10), no molde de `VirtualOrderNotification`
  (`UNIQUE(order_id, kind)`, `app/models.py:3027-3040`: "é a trava, não só um log").
- `Index("ix_notifications_user_unread", "user_id", "id", postgresql_where=text("read_at IS
  NULL"), sqlite_where=text("read_at IS NULL"))` — índice **parcial**: a contagem de não lidas
  (a query mais frequente do sistema depois desta feature) vira varredura só das linhas não lidas
  daquele usuário, e o índice não cresce com o histórico lido.
- `Index("ix_notifications_user_id", "user_id", "id")` — listagem paginada por keyset (`id < :antes_de
  ORDER BY id DESC`); `id` é monotônico e sem empate, ao contrário de `created_at`.
- `Index("ix_notifications_entity", "entity_type", "entity_id")` — "marcar lidas deste objeto" e
  "apagar as deste objeto" sem varredura (mesmo desenho de `ix_audit_logs_entity`, `:588`).

Sem índice global em `created_at`: a limpeza roda uma vez por dia sobre dezenas de milhares de
linhas — seq scan é barato e um índice a mais custaria em toda inserção.

Formato de `dedupe_key`: `form_response.nova:123` · `avaliacao.recebida:88` ·
`convite.recusado:4512:20260901`. O marcador é o que permite, nas ondas, "no máximo um aviso por
parcela por marco" (`parcela.vence:456:D-3`) e "um por criança por ano" sem coluna nova.

Volume esperado: v1 emite poucas unidades/dia × ≤ 10 destinatários ≈ 100 linhas/dia; as ondas 3-4
multiplicam por ~5 e ainda ficam abaixo de 200k/ano — e a retenção mantém a tabela em ~3 meses de
volume.

### Emissão — `app/notificacoes/notificacoes_ops.py`

Pacote novo `app/notificacoes/` (`__init__.py` + `notificacoes_ops.py`), **puro**: importa só
`db`, `models`, `constants` (`RoleName`, `now_sp`) e `sqlalchemy`. Nunca `flask.request`, nunca
`current_user`. Não é só a constituição: o produtor da recusa roda sob sessão de **talento**
(`portal_api_login_required`, `app/api/portal_auth.py:34`) — não há `current_user` interno ali, e
por isso `audit()` (`app/utils.py:46-74`, que infere o ator de `current_user`) não serve de molde.

**Catálogo no topo do módulo** — abrir o arquivo responde "quais fatos avisam quem":

```python
KIND_FORM_RESPONSE = "form_response.nova"
KIND_AVALIACAO = "avaliacao.recebida"
KIND_CONVITE_RECUSADO = "convite.recusado"

DESTINATARIOS_POR_KIND: dict[str, tuple[str, ...]] = {
    KIND_FORM_RESPONSE: (RoleName.COMERCIAL, RoleName.SUPERADMIN),
    KIND_AVALIACAO: (RoleName.COMERCIAL, RoleName.SUPERADMIN),
    KIND_CONVITE_RECUSADO: (RoleName.CASTING, RoleName.SUPERADMIN),
}
SEVERIDADES = ("info", "urgent")
```

Nenhum `kind` endereça "todo mundo": a decisão 5 da 266 vale para a caixa — aviso que vira ruído
deixa de avisar.

**Funções:**

- `resolver_destinatarios(papeis: Iterable[str]) -> list[User]` —
  `User.query.join(User.roles).filter(Role.name.in_(papeis), User.is_active.is_(True),
  User.has_access.is_(True)).distinct()`. É literalmente o filtro de `_avisar_comercial`
  (`formularios_write.py:82-89`) promovido a função única, com `.distinct()` porque quem tem
  COMERCIAL+SUPERADMIN viria duas vezes pelo join. `has_access=False` é a pessoa "só pagamento"
  sem login (`app/models.py:65-69`); não tem como ler.

- `emitir(kind: str, *, title: str, dedupe_key: str, body: str | None = None, link_path: str |
  None = None, entidade: tuple[str, int] | None = None, severity: str = "info", destinatarios:
  list[User] | None = None) -> int` — `destinatarios=None` resolve por `DESTINATARIOS_POR_KIND`;
  a lista explícita serve aos produtores futuros com destinatário individual (o vendedor do
  evento). Valida `kind` e `severity` com `ValueError` (erro de programação, não de dado). Devolve
  quantas linhas gravou.

  **Não comita** — o contrato de `audit()` ("o commit deve ser feito pelo chamador"). É isso que
  põe a notificação na mesma transação do fato quando o fato ainda não foi comitado.

  **Dedupe em duas camadas:** (1) um `SELECT` dos `dedupe_key` já existentes para esses usuários
  e inserção só dos que faltam — caminho normal, nunca estoura; (2) cada inserção dentro de
  `with db.session.begin_nested():` (SAVEPOINT) — se dois workers passarem pelo `SELECT` ao mesmo
  tempo e um bater na UNIQUE, só o savepoint volta, o `IntegrityError` vira `warning` no log e a
  função conta 0 para aquela linha. **A transação do chamador sobrevive** — sem o savepoint, uma
  corrida no aviso desfaria a recusa do convite, e "o aviso derrubando o fato" é o que a decisão
  7 da 266 proibiu.

- **Produtores nomeados no mesmo módulo**, um por fato, para catálogo e texto viverem juntos:
  `notificar_resposta_formulario(response)`, `notificar_avaliacao_recebida(feedback, event)`,
  `notificar_convite_recusado(role)`. Exigem `id` atribuído: fazem `db.session.flush()` se for
  `None`. O domínio só chama `notificar_x(obj)` — nunca monta título.

- Leitura/escrita do lado do usuário, para as views só validarem e serializarem:
  `contar_nao_lidas(user_id) -> int` (um `COUNT` no índice parcial — **nunca** ganhar join; a
  docstring diz isso), `listar(user_id, *, antes_de: int | None, limite: int, somente_nao_lidas:
  bool) -> list[Notification]`, `marcar_lida(user_id, notification_id) -> Notification | None`
  (`None` quando não é dele), `marcar_lidas_ate(user_id, ate_id) -> int`,
  `marcar_lidas_por_objeto(user_id, entity_type, entity_id) -> int`,
  `apagar_por_entidade(entity_type, entity_id) -> int`, `limpar_antigas(agora) -> int`.

**Os dois regimes de transação**, explícitos por produtor:

| Regime | Quando | Como | Consequência |
|---|---|---|---|
| **A — atômico** | o fato ainda não foi comitado (avaliação, recusa) | `add(fato); flush(); notificar_x(fato); commit()` | fato e aviso na mesma transação; se o commit falhar, nenhum dos dois existe. Nunca aviso sem fato |
| **B — best-effort depois do fato** | o fato já foi comitado antes (resposta de formulário, `_save_response` comita em `formularios_ops.py:591`) | `notificar_x(fato); commit()` em transação própria curta, `try/except → rollback → logger.exception` | resposta sem notificação: possível e aceitável; notificação sem resposta: impossível, a resposta já existe |

Em rotina de fundo (ondas 3-4), quem comita é a **rodada**, depois do claim atômico — registrar
na docstring de `emitir`: "em rotina de fundo, quem comita é a rodada".

### Os três produtores da v1

**1. Resposta de formulário público — o que substitui o e-mail.** `app/api/formularios_write.py`:
o corpo de `_avisar_comercial` (`:74-95`) troca `send_async(send_form_response_email, ...)`
(`:92`) por `notificacoes_ops.notificar_resposta_formulario(response); db.session.commit()`,
dentro do mesmo `try/except` best-effort, agora com `db.session.rollback()` no `except` (faltava
porque o envio era em thread). Renomear para `_notificar_comercial`. A chamada continua em
`:147`, **depois** do auto-vínculo (`:125-145`) — por isso o corpo pode dizer "cliente
identificada". Saem os imports `send_async, send_form_response_email` (`:18`) e `Role, User`
(`:34`, ficam sem uso). Honeypot (`:110-111`) e validação (`:114-116`) retornam antes — robô não
gera notificação, como não gerava e-mail.

Texto: `title="Nova resposta: {contact_name}"`, `body="{form_type_label} · festa em
{dd/mm/aaaa | data não informada}" + (" · cliente identificada: {client.name}" se
`client_link_source == "auto_phone"`)`, `link_path="/formularios?resposta={id}"`, entidade
`("form_response", id)`, `severity="info"`. Destinatários: COMERCIAL + SUPERADMIN (decisão 5 da
266 preservada).

`send_form_response_email` (`app/email_service.py:443-490`) é **removida** — era a única
chamadora. `send_async` e os helpers `_info_row/_btn/_info_box/_html_wrap` ficam: servem aos
e-mails de talento (convite, lembrete, reset), que não estão em questão.

**2. Avaliação da cliente recebida.** `app/api/feedback_write.py:100-101`: entre
`db.session.add(feedback)` e o `db.session.commit()` já existente entra `db.session.flush()` +
`notificacoes_ops.notificar_avaliacao_recebida(feedback, event)`. Regime A. Texto: `title="{score}★
— {event.title}"`, `body="{client_name} · {tags unidas por ', '} · {comment[:120]}"`,
`link_path=f"/events/{event.id}?aba=historico"` (a aba Histórico é onde `FeedbackSection` mora,
`EventDetailPage.tsx:150-162`, e a aba já vive na URL, `:178-205`), entidade
`("client_feedback", id)`, **`severity="urgent"` quando `score <= 2`**, `info` caso contrário.
Destinatários: COMERCIAL + SUPERADMIN (quem fala com a cliente; FINANCEIRO não age numa
avaliação). O `ClientFeedback` continua sendo montado inline no endpoint (`:93-99`) — movê-lo para
`feedback_ops` é refatoração da 164, fora daqui.

**3. Convite recusado pelo talento.** `app/talent_portal/portal_ops.py::reject_invite`
(`:286-293`): ganha guarda real de idempotência `if role.invite_status == "rejected": return role`
antes de gravar (hoje a função é "idempotente" só porque regrava o mesmo valor — com aviso,
regravar seria re-avisar); depois `role.invite_status = "rejected";
notificacoes_ops.notificar_convite_recusado(role); db.session.commit()` — o commit de `:292` passa
a cobrir os dois. Regime A. Texto: `title="{talent.artistic_name or talent.full_name} recusou
{character_name}"`, `body="{event.title} · {start_at:%d/%m %H:%M}"`,
`link_path=f"/events/{event_id}?aba=producao"`, entidade `("event_role", id)`,
`dedupe_key=f"convite.recusado:{role.id}:{now_sp():%Y%m%d}"`, `severity="urgent"` quando o evento é
em ≤ 7 dias (mesma janela `ANTECEDENCIA_MAXIMA` de `invite_reminders.py:39`), `info` senão.
Destinatários: CASTING + SUPERADMIN. `role.event` vem do backref (`app/models.py:328`), `role.talent`
de `:563`. É o único produtor sem `current_user` — prova que `emitir` não depende de request.
Complementa a Home, não duplica: o painel mostra o **estado** (some quando alguém reescala), a
notificação registra o **fato** ("fulano recusou às 14:03").

**Efeitos colaterais em endpoints existentes:**

- `GET /api/formularios/respostas/<int:id>` (`formularios_admin_read.py:98-100`, consumido por
  `useFormResponseDetail`, `lib/formulariosAdmin.ts:63-75`) passa a chamar
  `marcar_lidas_por_objeto(current_user.id, "form_response", id)` + `commit()` antes de
  serializar. É um GET que escreve, de propósito — ver decisão 12.
- `formularios_ops.delete_response` (`:323-326`) chama `apagar_por_entidade("form_response", id)`
  na mesma transação — nenhum sino aponta para id morto. (Se apontar, por corrida, a tela já
  trata: "Não foi possível carregar esta resposta.", `FormulariosAdminPage.tsx:542`.)

### API — `app/api/notificacoes_read.py` e `notificacoes_write.py`

Registrados por import em `app/api/__init__.py` (duas linhas no fim do bloco — sem elas a rota não
existe e não há erro nenhum, docs/00 §5). Docstring de topo declarando o RBAC (docs/01 §4.3).

RBAC: só `@api_login_required` (`app/api_utils.py:45`). **Nenhum gate por papel** — o RBAC
aconteceu na emissão (quem foi endereçado); na leitura o escopo é `Notification.user_id ==
current_user.id`, sempre, no servidor (docs/01 §4.4). REVENDEDOR_EDUCAMANTO nem chega aqui: a guarda de perfil restrito da 078
(`_REVENDEDOR_ALLOWED_API`, `app/__init__.py`) devolve 403 antes da view — comportamento herdado,
não gate novo — e o `AppShell` não renderiza o sino para ele. Sem sessão: 401 JSON. Erros pelo envelope `json_error` (`api_utils.py:16`).

| Endpoint | Resposta | Nota |
|---|---|---|
| `GET /api/notificacoes/nao-lidas` | `{"unread_count": n}` | **o endpoint do polling**: um `COUNT` no índice parcial, zero join, zero objeto ORM. Existe separado da lista porque roda a cada 60 s em toda aba aberta — tem de ser a consulta mais barata do sistema |
| `GET /api/notificacoes?antes_de=<id>&limite=30&somente_nao_lidas=1` | `{"items": [{id, kind, severity, title, body, link_path, entity_type, entity_id, created_at, read_at}], "next_before": <id do último ou null>, "unread_count": n}` | keyset por `id`, nunca offset (a página 2 não pula nem repete quando chega aviso novo); `limite` travado em 1..100; `created_at` como ISO naive São Paulo, igual a `start_at` dos eventos |
| `POST /api/notificacoes/<int:id>/lida` | `{"id", "read_at", "unread_count"}` | idempotente (já lida devolve o mesmo `read_at`); de outro usuário ou inexistente → **404, não 403**, para não confirmar existência (convenção do RBAC de arquivo, docs/00 §4). Devolver `unread_count` já recalculado poupa uma requisição |
| `POST /api/notificacoes/lidas` body `{"ate_id": <id>}` | `{"marcadas": n, "unread_count": n}` | `ate_id` **obrigatório** (400 sem ele): marca lidas as do usuário com `id <= ate_id` — o teto evita engolir o lead que chegou depois de a lista ser desenhada e ninguém viu |

Sem `DELETE` e sem "marcar como não lida" na v1: a notificação é registro do fato; "sumir da
lista" é lida, não apagada; retenção limpa o resto.

**Impersonação ("Ver como", `session["impersonate_role"]`, `app/api/auth.py:38`) não se
aplica:** a caixa é do **usuário real**. Não existe caixa do papel; existe caixa da pessoa. Um
SUPERADMIN em "Ver como CASTING" continua vendo as suas. Documentado como decisão, não como o
defeito 3.5 de docs/05 (lá o gate ignora o papel simulado; aqui não há gate).

### UI — app interno

**Onde mora o sino.** O desktop não tem topbar (`packages/ui/src/components/app-layout.tsx:169-232`:
`aside` fixo de 256 px + `header` só `lg:hidden`) e criar uma mexeria na silhueta das 60+ páginas
que têm `PageHeader` próprio. `AppLayoutProps` (`:38-53`) ganha `headerActions?: ReactNode`,
renderizado **duas vezes**:

- **desktop**: na linha da marca da sidebar (`:163`, o `div` do `brand` vira `flex items-center
  justify-between`) — o único ponto sempre visível que não é conteúdo de página;
- **mobile**: à direita da barra superior (`:181-192`), com `ml-auto`, **fora do drawer** — um
  sino escondido atrás do hambúrguer não avisa nada. Alvo ≥ 44 px (`h-11 w-11`, o mesmo do botão de
  menu em `:187`).

É o mesmo truque que o `ThemeSwitch` já usa no rodapé (`AppShell.tsx:106-110`: "o AppLayout
renderiza este bloco DUAS vezes"). As duas instâncias compartilham dados pelo cache do TanStack
(mesma `queryKey` = um request) e só uma está visível por vez (`hidden lg:block` × `lg:hidden`).
Prop opcional, sem efeito em portal/public — mas o typecheck dos três apps é portão.
`AppShell.tsx:149-161` passa `headerActions={<NotificacoesBell />}`; o sino não renderiza para
`isRevendedorOnly(user)` (`lib/useAuth.ts:12-25`) — nenhum `kind` da v1 o alcança.

**Componentes** em `frontend/apps/internal/src/components/notificacoes/` (padrão de
`components/nfc/`; ficam no app, não em `@manto/ui`, porque usam `useNavigate` e o pacote "não
conhece o router", `app-layout.tsx:11`): `NotificacoesBell.tsx` (botão + badge + anunciador),
`NotificacoesPanel.tsx` (popover), `NotificacaoItem.tsx` (compartilhado entre popover e página —
duas montagens divergiriam no primeiro ajuste).

**Sino.** `lucide-react` `Bell`; badge com a contagem (`9+` acima de 9) em `bg-accent
text-on-color` (o par do contador do `FilterDropdown`, `filter-dropdown.tsx:59-62`, com o
comentário de contraste a 10 px); some quando zero. `aria-label` dinâmico ("Notificações" /
"Notificações, 3 não lidas"). Anunciador `<span className="sr-only" aria-live="polite">` (padrão
de `EventHeader.tsx:174-176`) que só recebe texto quando a contagem **sobe** em relação ao render
anterior (`useRef`) — anunciar a cada poll seria o e-mail em áudio.

**Popover.** Implementação própria calcada em `FilterDropdown` (`filter-dropdown.tsx:22-44`:
fecha em clique fora e Esc, `aria-expanded`/`aria-controls`, `AnimatePresence` +
`useReducedMotion`) e no `KebabMenu` (`z-30`, a camada de popover do app — o comentário de
`KebabMenu.tsx:26-37` explica por que não `z-20` nem `z-50`). Sem Radix Popover: `@manto/ui` só
tem dialog/slot/tabs (`packages/ui/package.json`) e o `FilterDropdown` existe justamente para não
adicionar overlay novo. Posição: desktop `lg:absolute lg:left-full lg:top-0 lg:ml-2 lg:w-96` (abre
para a **direita** da sidebar, sobre o `main` — nasce dentro do contexto `z-40` da própria
sidebar, então fica por cima do conteúdo); mobile `max-lg:fixed max-lg:inset-x-2 max-lg:top-16
max-lg:max-h-[70vh]` (folha sob a barra, não popover de 320 px cortado). `role="dialog"
aria-label="Notificações"`, foco no título ao abrir e de volta ao sino ao fechar.

Conteúdo: cabeçalho "Notificações" + "Marcar todas como lidas" (desabilitado com 0 não lidas e
enquanto `isPending`; erro vira linha `role="alert"` inline, padrão de `DashboardPage.tsx:652`,
sem fechar o painel — o app não tem lib de toast e não vai ganhar uma por isto). Lista das últimas
20, agrupada por dia ("Hoje", "Ontem", data curta) com `formatRelativeDay`/`formatShortDate` de
`@manto/ui`; hora `HH:mm` recortada da string via `horaDeIsoLocal` (`lib/horaLocal.ts`) — `created_at`
é naive São Paulo, `new Date(iso).toISOString()` deslocaria 3 h (docs/00 §6 item 1). Item = um
`<button>` inteiro: ícone por `kind` (`FileText`, `Star`, `UserX`; fallback `Bell`), ponto
`bg-accent` à esquerda e título em `font-semibold` quando não lida, corpo em uma linha `truncate`,
cor `text-red` + `bg-red-soft` quando `severity === "urgent"`. Clique: **atualização otimista** do
cache (`setQueryData` em `["notificacoes","nao-lidas"]`), `marcarLida.mutate(id)` e
`navigate(link_path)` no mesmo gesto — não espera o POST; o destino é o que importa e o poll
seguinte reconcilia. Rodapé: "Ver todas" → `/notificacoes`.

Estados: carregando = 3 `Skeleton` com a silhueta do item; vazio = "Nada por aqui. Quando chegar
uma resposta de formulário, uma avaliação de cliente ou uma recusa de convite, o aviso aparece
neste sino." (o vazio de um sistema novo precisa ensinar o que vai aparecer); erro na lista =
"Não foi possível carregar as notificações." + "Tentar de novo" (`refetch`); erro no **poll** =
silêncio — o badge some, nada pisca; o sino não é lugar de anunciar falha de infra. 401 no poll =
"deslogado", como `useCurrentUser` já trata (`useAuth.ts:31-38`).

**Página `/notificacoes`** (`pages/NotificacoesPage.tsx`, `<Route>` em `App.tsx` no bloco
`:95-166`, ao lado de `/formularios` `:104`): `PageHeader` "Notificações" com a ação "Marcar todas
como lidas" (envia `ate_id` = maior `id` carregado); `Tabs` "Não lidas" / "Todas"; a mesma
`NotificacaoItem`; "Carregar mais" com `isFetchingNextPage` (`useInfiniteQuery`, cursor
`next_before`). Com `AnimatePresence` + `motion.li layout` a linha some da aba "Não lidas" ao ser
lida (200 ms). **Sem item em `lib/navigation.tsx`**: o sino é a entrada; a lista de ~30 itens da
sidebar já é longa e no mobile o item sumiria dentro do drawer. Exceção à tabela "Onde mexer" de
docs/04 §8, registrada lá.

**Movimento** (Princípio IX, sempre `useReducedMotion`): painel `opacity 0→1, y -4→0` em 150 ms
(idêntico ao `FilterDropdown`); badge `scale 0.6→1` em 200 ms quando aparece ou o número muda
(`key={count}`), nunca a cada poll com o mesmo valor; item lido no popover só troca peso e ponto
(sem sair da lista — item que some ao clicar dá sensação de erro). Com `reduceMotion`:
`initial={undefined}`, duração 0, como `filter-dropdown.tsx:70-74` e `app-layout.tsx:203-213`.

**Hooks** em `frontend/apps/internal/src/lib/notificacoes.ts` (padrão de `formulariosAdmin.ts`):

- `useNaoLidas()` — `queryKey: ["notificacoes", "nao-lidas"]`, `refetchInterval: 60_000`,
  `refetchIntervalInBackground: false` (aba oculta não gasta requisição — o incidente da 263 foi
  thread presa, e não vamos criar carga de fundo à toa), `refetchOnWindowFocus: true` (**exceção
  deliberada** ao default `false` de `createQueryClient`, `packages/api-client/src/queryClient.ts:20-21`:
  é o único dado do app que nasce de gente de fora — cliente pública, talento no portal — e
  invalidação explícita não alcança; precedente de `refetchInterval` em `lib/adminConfig.ts:174`),
  `retry: false`, `enabled: !!user`. Quando o número muda com o painel aberto, invalida a lista.
- `useNotificacoes({ somenteNaoLidas })` — `useInfiniteQuery`, `queryKey: ["notificacoes",
  "lista", { somenteNaoLidas }]`, `initialPageParam: null`, `getNextPageParam: (p) => p.next_before`,
  `staleTime: 0` no popover (cada abertura busca fresco), `enabled: aberto`.
- `useMarcarLida()` / `useMarcarTodasLidas()` — `onSuccess` grava `unread_count` da resposta em
  `["notificacoes","nao-lidas"]` e invalida `["notificacoes","lista"]`. As chaves são filhas de
  `["notificacoes"]` de propósito (a armadilha de docs/04 §8 é prefixo que não é pai).

Custo do poll: ~10-15 usuários × 1-2 abas visíveis × 1 req/min contra um `COUNT` indexado ≈ 0,3
req/s — ordens de grandeza abaixo da calculadora ("request por tecla"). Se um dia pesar, o primeiro
ajuste é `ETag`/304 no `/nao-lidas`, não WebSocket.

### Retenção e limpeza

Regra: lida há mais de **30 dias** → apaga (`read_at < agora - 30d`); não lida há mais de
**180 dias** → apaga (`read_at IS NULL AND created_at < agora - 180d`) — aviso que ninguém abriu
em seis meses não é aviso. Constantes `RETENCAO_LIDA_DIAS = 30` e `RETENCAO_NAO_LIDA_DIAS = 180` no
topo de `notificacoes_ops.py`; `limpar_antigas(agora)` apaga em lotes de 1000 (`DELETE ... WHERE
id IN (SELECT id ... LIMIT 1000)`, repetindo até 0) para não segurar lock numa tabela que recebe
INSERT a cada formulário. Sem soft-delete: a notificação é derivada; o fato continua no banco com
o próprio histórico.

Onde roda: como **segunda chamada no laço diário de `_start_review_cleanup`**
(`app/__init__.py:273-304`, `REVIEW_CLEANUP_INTERVAL = 24h`) — sem oitava thread (cada worker já
carrega 7). **Sem claim atômico**, pela mesma justificativa que docs/04 §7 já dá ao
review-cleanup: apagar por idade é idempotente — três workers rodando o mesmo `DELETE` produzem o
mesmo resultado e nenhum efeito externo. O claim protege efeito que não pode repetir (e-mail,
lembrete); aqui não há. Isso também mantém a migration em uma tabela só (nenhuma coluna nova em
`site_settings`).

CLI `flask notificacoes-limpar [--execute]` (dry-run padrão, molde do `flask compress-images`,
`app/cli.py:61-64`) — para rodar à mão depois do deploy ou num incidente, e é o que o
`verify_272.py` chama para testar a regra sem esperar 24 h.

Cascatas: exclusão de usuário leva as notificações (FK CASCADE); usuário desativado deixa de
**receber** (filtro de `resolver_destinatarios`) e o que já tem envelhece e sai pela regra dos 180
dias; resposta excluída leva as suas (`apagar_por_entidade`); evento excluído (cascade em
`roles`, `models.py:328`) deixa a notificação de recusa apontando para `/events/<id>` — aceito na
v1: a página do evento já tem estado "não encontrado", e o registro de que houve recusa vale mais
que a coerência do link.

### Migration

`migrations/versions/b7d2e4f1a9c3_notifications.py`, escrita **à mão** (nunca autogenerate —
`flask db check` acusa drift antigo em 6 tabelas e um autogenerate cego derruba o `startCommand`,
memória `manto_alembic_drift_autogenerate`), no formato de `e08e454c4780_nfc_tag_deliveries.py`
(docstring com o porquê antes do código): `op.create_table("notifications", ...)` + os três
`op.create_index` (o parcial com `postgresql_where=sa.text("read_at IS NULL")` e `sqlite_where`) +
`op.create_unique_constraint`; `downgrade` = `op.drop_table`. Roda no `startCommand`
(`flask db upgrade`, `render.yaml:22`) dentro da janela normal de ~60 s de 502. Ensaiar
`upgrade → downgrade → upgrade` no `manto_local` e no dump restaurado antes do merge (memória
`manto_ensaio_migracao_destrutiva`) — aqui é aditiva, mas o ritual é o que prova o encadeamento do
head.

### Documentação a atualizar

- **docs/00**: §2 (a linha da factory, `:32`, fala em "7 threads de background" — continuam 7;
  anotar que review-cleanup passa a ter duas rotinas), §4 (nota: "Ver
  como" não muda a caixa de notificações — é da pessoa), §6 (item 2: `notifications.created_at`
  também é `now_sp`; comparar com `AuditLog.created_at` mistura relógios).
- **docs/01**: §2.7 (tabela `notifications`, índices, por que uma linha por destinatário), §3
  (seção nova `3.x Notificações — notificacoes_read.py / notificacoes_write.py`), §4.3 (terceiro
  padrão de RBAC: **na emissão**, com escopo por dono na leitura — não é "ausência de gate" nem
  `flags.<nome>`), cabeçalho "estado do repositório".
- **docs/02**: A.2 (sino no shell — onde fica no desktop e no mobile, popover, deep-links por
  `kind`), rota nova `/notificacoes` "acessível pelo sino, sem item de menu".
- **docs/03**: entrada **272** no topo (migration, a frase do dono como motivação, os dois regimes
  de emissão, o GET que escreve, a remoção do e-mail) + **uma linha de ponteiro em itálico no topo
  da entrada 266** (`docs/03_HISTORICO_MUTACOES.md:495`, logo abaixo do título "266 — Costuras do
  funil") dizendo que o e-mail de resposta nova foi **substituído pela 272**, e "(e-mail
  substituído pela 272)" na linha da 266 no índice (`:67`) — sem reescrever a história. A spec 266 (`specs/266-costuras-funil/spec.md`, decisões 5-7) e seus
  `plan.md:116`/`tasks.md:56` **não se editam**: são o registro do que foi decidido na época.
- **docs/04**: §7 (review-cleanup ganhou a limpeza de notificações; `notificacoes_ops.emitir` na
  lista de peças para reusar nas ondas; "em rotina de fundo, quem comita é a rodada"), §8 (slot
  `headerActions` do `AppLayout`; exceção do item de menu na tabela "Onde mexer").

### O que fica para as ondas (já com a chave desenhada)

Cada um é feature própria (273+ provisórios), um deploy, um verify. Produtor novo = constante no
catálogo + entrada em `DESTINATARIOS_POR_KIND` + `notificar_x()` + uma chamada no ponto do fato.

| `kind` / `dedupe_key` | Onda | Ponto do código | Destinatários | Pré-requisito |
|---|---|---|---|---|
| `parcela.vence:<installment_id>:<D-3\|D0\|D+3>` | 3 | rotina diária nova com claim (molde `invite_reminders.py:130-148`); a poda de notificações pode virar último passo dela | FINANCEIRO + vendedor do evento (`destinatarios` explícito) | `EventInstallment.received` passar a ser escrito (analise §3.3) |
| `orcamento.followup:<orcamento_id>:<dia>` | 4 | mesma rotina diária | vendedor | FK de cliente no orçamento (onda 2; `OrcamentoHistory.client_name` é texto livre, analise §3.1) |
| `aniversario.crianca:<client_id>:<ano>` | 4 | mesma rotina diária; o dado já é lido pela Fila 3D (`impressoes3d_ops.py:564-589`) | COMERCIAL | idem onda 2 |
| `avaliacao.pedido_pendente:<event_id>` (D+1 sem link enviado) | 4 | rotina diária | COMERCIAL | registro de envio do link (analise §3.4) |
| `form_response.ambigua:<id>` | — | `formularios_write.py:129` (`event_link_ambiguous`) | COMERCIAL | não entra: o card da Home já cobre (decisão 2 da 266) |
| e-mails internos que **ainda existem**: `send_ensaio_alert_email` (`event_ops.py:66`), `send_new_expense_alert_email` (`gastos_ops.py:290`), `send_figurino_producao_email`/`send_figurino_pedido_setor_email` (`figurino_producao_write.py:72,106,151`) | a decidir com o dono | cada um vira um `kind` quando ele pedir | ENSAIO / FINANCEIRO / FIGURINO | nenhum — são candidatos naturais, mas o pedido de hoje foi sobre o formulário |

`convite.aceito` fica **descartado**, não adiado: boa notícia em volume vira ruído, e o painel de
confirmações da Home já mostra o estado.

## Decisões

1. **Uma linha por destinatário, não "uma por evento + tabela de leitura".** O estado "lida" é
   por pessoa — é a feature. Com uma tabela só, o sino é **um** `COUNT` indexado e o dedupe é
   **uma** constraint; um `notification_reads` reintroduziria join (anti-join, na verdade) no
   endpoint mais chamado do sistema para economizar ~300 bytes × ≤ 10 por fato. Efeito colateral
   aceito e correto: quem ganha COMERCIAL amanhã não vê os avisos de ontem — não eram para ela.

2. **Destinatários resolvidos na emissão e congelados como `user_id`.** A notificação é a
   fotografia de "quem devia saber disto quando aconteceu", não uma consulta viva sobre papéis.
   Papel muda: quem perdeu COMERCIAL não deve continuar vendo leads; quem ganhou não deve herdar
   dois anos como não lido. É exatamente o que `_avisar_comercial` já faz ao resolver `User.query`
   no momento do POST.

3. **Idempotência pela `UNIQUE(user_id, dedupe_key)`, com SAVEPOINT em volta da inserção.** A
   regra 10 de docs/00 §6 é explícita ("por restrição de banco, não por confiança no fluxo") e
   três workers gunicorn são a norma. O savepoint (`begin_nested` + `IntegrityError` tolerado,
   precedente do hotfix 271 em `_ensure_salary_payments`, `app/financeiro/routes.py:775`) é o que
   faz a trava não derrubar a
   transação do fato. Preferido a `INSERT ... ON CONFLICT DO NOTHING` do dialeto Postgres porque
   é **um caminho só** para Postgres e para o SQLite "dev casual" (`app/config.py:18`) — dois
   caminhos são duas coisas para verificar; para ≤ 10 linhas o custo é o mesmo.

4. **`dedupe_key` explícita e NOT NULL, não `UNIQUE(user_id, kind, entity_type, entity_id)`.** A
   composta não expressa "um por parcela por marco" nem "um por criança por ano" sem coluna
   nova; e com `entity_id` NULL o Postgres trata NULLs como distintos — o dedupe desligaria em
   silêncio. A chave em texto obriga cada produtor a declarar a identidade do aviso.

5. **`emitir` não comita (contrato de `audit()`), e cada produtor declara seu regime.** Só assim
   o produtor escolhe atomicidade: avaliação e recusa vão no mesmo commit do fato (nunca aviso sem
   fato); o formulário público emite depois da resposta já gravada, em transação curta
   best-effort — "resposta sem notificação é aceitável, notificação sem resposta não é". Emitir
   **dentro** de `_save_response` inverteria a prioridade do SC-002 da 118 (salvar antes de tudo).

6. **Texto renderizado na escrita (`title`/`body`/`link_path`), não `payload` interpretado por
   `kind` no front.** O caminho de leitura fica burro e estável enquanto produtores entram um a um;
   a notificação continua legível depois que a entidade muda ou some; é o princípio dos valores
   congelados de docs/00 §6 item 12. Custo assumido: se o nome da contratante for corrigido
   depois, o aviso mantém o antigo.

7. **`severity` por dado, não por `kind`, e como string de dois valores.** A nota da avaliação
   decide `urgent`; a proximidade do evento decide a recusa. É o que faz "nota baixa gritar" sem
   e-mail — cor e badge, não interrupção. String em vez de boolean para um nível intermediário
   entrar sem migration; dois valores em vez de três porque na v1 não há o que distinguir no meio.

8. **`created_at` por `now_sp()`, não `utcnow` como o `AuditLog`.** O "há 12 min" e a ordenação
   da caixa são horário de parede; a retenção compara com `now_sp()`; o front interpreta ISO
   naive como local (`packages/ui/src/lib/date.ts:9-12`). Documentar em docs/00 §6 que comparar
   com `AuditLog.created_at` (UTC) erra 3 h — a mesma ressalva do item 2 para `virtual_*`.

9. **Módulo `*_ops` puro sem `current_user` — e o catálogo inteiro num arquivo.** O produtor da
   recusa roda sob sessão de talento, então a emissão não pode depender de Flask-Login. E abrir
   `notificacoes_ops.py` responde "quais fatos avisam quem" — os textos vivem com o catálogo, não
   espalhados por três endpoints.

10. **RBAC na emissão, escopo por dono na leitura, sem gate de papel nos endpoints.** Terceiro
    padrão de RBAC da casa, a registrar em docs/01 §4.3: o payload é sempre do `current_user.id`,
    no servidor; 404 (não 403) para id alheio, como `/uploads`. A caixa é do usuário real —
    "Ver como" não a troca.

11. **Contagem de não lidas por índice parcial; listagem por keyset em `id`.** O polling precisa
    custar O(não lidas do usuário), não O(histórico) — sem contador desnormalizado em `users`,
    que exigiria reconciliação (o que acontece quando a limpeza apaga não lidas?). Keyset porque a
    lista muda enquanto se pagina.

12. **Abrir a resposta de formulário por qualquer caminho marca lida — um GET que escreve, de
    propósito, e só nesse endpoint.** O lead é aberto por três caminhos (sino, card da Home da 266,
    linha de `/formularios`); marcar só pelo sino deixaria o badge dizendo "3" para quem já tratou
    os três pela lista — o ruído do e-mail em nova roupa. `useFormResponseDetail` só roda com o
    diálogo aberto (`enabled: id != null`), então não há refetch sem olhar humano. Avaliação e
    recusa ficam por clique: o "objeto" delas é a página do evento, que é aberta por dezenas de
    motivos, e marcar lida ali seria implícito demais. Vigiar em produtores futuros.

13. **`ate_id` obrigatório em "marcar todas".** Um lead engolido por "marcar todas" clicado sobre
    uma lista de 40 s atrás seria o pior defeito possível desta feature. O front sempre manda o
    maior `id` que está na tela.

14. **Sino no shell via slot `headerActions` (linha da marca no desktop, barra superior no mobile),
    popover próprio, página `/notificacoes` sem item de menu.** Topbar nova mexeria na silhueta de
    todas as páginas e no esqueleto do `AppShell`; Radix Popover criaria um segundo padrão ao lado
    de `FilterDropdown`/`KebabMenu`; badge num item de menu sumiria no drawer do celular. A página
    existe porque com três produtores a lista não cabe em 20 itens para sempre — mas entra pelo
    sino, não pela sidebar.

15. **Polling de 60 s só da contagem, pausado em aba oculta, com `refetchOnWindowFocus`.** Sem
    SSE/WebSocket: conexão longa é thread do gunicorn ocupada (36 slots, `render.yaml:22`) e o
    incidente de 26/08 foi exatamente requisição presa; para um lead respondido em horas, 60 s é
    "imediato". `refetchIntervalInBackground: false` porque uma aba esquecida não deve gastar
    requisição — e `refetchOnWindowFocus: true` nesta query dá o "volto pra aba, número certo". Sem
    `document.title "(3) Manto"` na v1: com o poll pausado em background ele não atualizaria mesmo,
    e é uma superfície a mais para verificar.

16. **Sem toast, som ou agrupamento "N respostas novas".** Interromper é o que o e-mail fazia; o
    sino é passivo por desenho. Colapsar esconderia nomes e urgência (decisão 6 da 266: o lead é
    perecível); agrupar por **dia** organiza sem esconder. `aria-live` só quando a contagem sobe.

17. **Três produtores na v1, não um.** O primeiro é a queixa do dono; os outros dois custam ~10
    linhas cada e provam a generalidade — dois conjuntos de papéis, o regime atômico, um produtor
    sem `current_user`, `severity` por dado. Sem eles a "fundação" seria promessa.

18. **O e-mail de resposta nova sai do código, não fica atrás de flag.** O dono foi textual; uma
    `SiteSetting` para religar seria interruptor morto (docs/05 §6). `git show` recupera. `send_async`
    e os helpers de layout ficam para os e-mails de talento.

19. **Retenção 30 d (lida) / 180 d (não lida) no laço do review-cleanup, sem claim, sem thread
    nova, sem coluna em `site_settings`.** A tabela precisa ter teto antes das ondas 3-4
    multiplicarem o volume; uma 8ª thread por worker não se justifica para apagar dezenas de
    linhas; e apagar por idade é idempotente — o claim protege efeito externo que não pode
    repetir, e aqui não há. Quando a onda 3 trouxer a rotina diária com claim, a poda pode migrar
    para o último passo dela.

20. **Referência fraca ao objeto (`entity_type`/`entity_id` sem FK) + `apagar_por_entidade` na
    exclusão.** Uma FK por domínio acoplaria a tabela transversal a todos. A v1 limpa na exclusão
    de resposta (o único caminho de exclusão dos três fatos que passa por `*_ops`); evento excluído
    fica com link para página que já trata "não encontrado".

## Verificação

Script `specs/272-notificacoes-internas/verify_272.py` contra o `manto_local` (nunca o SQLite de
`instance/`), escrito **antes** do código, no esqueleto de `verify_266.py` (`:1-60`: reconfigure
utf-8, `.local-db-url`, `FLASK_ENV=development` — obrigatório para `create_app` não subir as threads
reais, memória `manto_create_app_threads_scripts`; helpers `_usuario`/`_login` `:101-117`; `PREFIX
= "__v272_"`; login só pela API; toda escrita conferida por **conexão separada** — lição do hotfix
257; limpeza total ao fim, roles dos usuários antes de apagá-los). Rodar com `MAIL_SUPPRESS_SEND`
ativo.

1. **Formulário → notificação.** POST público `/api/formularios/comum` (payload montado do schema
   vigente, `_payload_formulario` de `verify_266.py:119`) com telefone de cliente existente → 201;
   por conexão separada existe **exatamente 1** linha `kind='form_response.nova'`,
   `dedupe_key='form_response.nova:<id>'`, `link_path='/formularios?resposta=<id>'` por usuário
   ativo+com acesso com papel COMERCIAL ou SUPERADMIN; **0** para CASTING; **0** para COMERCIAL
   com `is_active=False` e para COMERCIAL com `has_access=False`; usuário COMERCIAL+SUPERADMIN
   recebe **1** (distinct); `body` contém "cliente identificada".
2. **Nenhum e-mail.** `mail.record_messages()` vazio durante o POST e `not hasattr(email_service,
   "send_form_response_email")` (removida, não silenciada); `formularios_write.__dict__` não
   referencia `send_async`.
3. **Idempotência.** `notificar_resposta_formulario(response)` chamada duas vezes → contagem não
   muda, segunda chamada devolve 0. **Corrida:** inserir por SQL direto uma linha com a mesma
   `(user_id, dedupe_key)` e chamar `emitir()` numa sessão que tem uma escrita pendente **não
   relacionada** → devolve 0, não levanta, e a escrita pendente comita normalmente (o savepoint
   protegeu a transação do chamador).
4. **Regime A.** POST `/api/avaliar/<token>` com `score=1` → `ClientFeedback` e notificação
   `severity='urgent'`, `link_path='/events/<id>?aba=historico'` existem ambos na conexão
   separada; `score=5` → `severity='info'`. Abrir transação, `add(ClientFeedback)`, `flush`,
   `notificar_avaliacao_recebida`, **`rollback`** → zero notificações e zero feedback.
5. **Regime B.** Monkeypatch de `notificacoes_ops.notificar_resposta_formulario` levantando
   exceção → o POST público continua 201 e a `FormResponse` existe (decisão 7 da 266 preservada);
   o log tem `exception`.
6. **Recusa.** Login de talento e POST `/api/portal/invites/<role_id>/reject` → CASTING +
   SUPERADMIN avisados, COMERCIAL não; `severity='urgent'` quando o evento é em ≤ 7 dias, `info`
   senão; **segundo POST** → 200 e nenhuma linha nova (guarda + UNIQUE); aceitar e recusar de novo
   no mesmo dia → ainda nenhuma (chave por dia).
7. **API.** Como usuário A: `GET /api/notificacoes` lista só as de A e `unread_count` bate com o
   `COUNT` por conexão separada; `POST /<id de B>/lida` → **404** e a linha de B continua `read_at
   IS NULL`; `POST /<id de A>/lida` → `read_at` preenchido, idempotente, `unread_count`
   decrementado na resposta; inserir uma nova (id maior) e `POST /lidas` com `ate_id` = anterior →
   a nova continua não lida; sem `ate_id` → 400 no envelope `json_error`. REVENDEDOR_EDUCAMANTO →
   403 (guarda de perfil restrito da 078). Sem sessão → 401 JSON.
8. **Paginação.** Semear 35 linhas para um usuário → página 1 (30) + página 2 (5) via `next_before`,
   sem repetição nem salto, inclusive quando uma linha nova entra entre as duas chamadas.
9. **Lida ao abrir o objeto.** Com notificação não lida, `GET /api/formularios/respostas/<id>` como o
   destinatário → a dele fica lida e a do outro destinatário **não**.
10. **Exclusão.** `DELETE /api/formularios/respostas/<id>` (SUPERADMIN) → zero linhas para aquele
    `entity_id`, nenhuma outra tocada. Exclusão de usuário com notificações → conclui e as linhas
    somem (CASCADE).
11. **Retenção.** Semear lida há 31 dias, lida há 29, não lida há 181, não lida há 179 →
    `flask notificacoes-limpar --execute` apaga exatamente a 1ª e a 3ª; sem `--execute` não apaga
    nada e imprime a contagem. Relógio passado explicitamente para não depender da hora do teste.
12. **Relógio e plano.** `created_at` da linha nova difere de `now_sp()` por < 60 s e de
    `datetime.utcnow()` por ~3 h. `EXPLAIN (FORMAT JSON)` da query de `contar_nao_lidas` mostra
    `ix_notifications_user_unread` — registrar o plano na saída do verify (é a prova da decisão 11).
13. **Migration.** `flask db heads` único antes e depois; `upgrade → downgrade → upgrade` limpos no
    `manto_local`; `flask db check` sem drift **novo** (o antigo das 6 tabelas é conhecido); ensaio
    no dump noturno restaurado rodando o `startCommand` inteiro.

Na tela (`manto_local`, superadmin + um usuário COMERCIAL, desktop **e** mobile 375 px):

- sino visível na linha da marca (desktop) e na barra superior **fora do drawer** (mobile), sem
  rolagem horizontal;
- submeter um formulário público em outra aba → em ≤ 60 s o badge aparece **sem F5**; aba de rede
  mostra **uma** requisição a `/nao-lidas` por minuto e **nenhuma** com a aba oculta; voltar à aba
  dispara uma;
- abrir o painel → item com nome, data e ícone por `kind`; avaliação nota 1 em vermelho; clicar →
  chega em `/formularios?resposta=<id>` com o diálogo aberto e o badge já caiu **antes** do POST
  voltar; abrir a mesma resposta pela **lista** (não pelo sino) → badge zera no próximo poll;
- "Marcar todas" com 0 → desabilitado; com N → zera, e uma notificação que chegue durante o clique
  continua não lida;
- `/notificacoes`: abas, "Carregar mais", a linha some da aba "Não lidas" ao ser lida;
- "Ver como CASTING" **não** muda a caixa;
- Esc e clique fora fecham o painel; foco volta ao sino; `aria-live` anuncia uma vez ao subir de
  0→1 e nada nos polls seguintes;
- `prefers-reduced-motion` emulado → sem deslocamento nem escala;
- derrubar o backend com o painel fechado → badge some sem erro na tela; com o painel aberto →
  "Tentar de novo".

Portões: `npm run typecheck` limpo nos **três** apps (a prop nova em `@manto/ui` afeta portal e
public por tipo), `ruff check` sem erro novo (imports mortos em `formularios_write.py` removidos),
`docs/00`, `docs/01`, `docs/02`, `docs/03` (entrada 272 + ponteiro na 266) e `docs/04` atualizados
como listado em "Documentação a atualizar". Deploy sozinho na `main`, fora do horário, com o log do
Render aberto; conferir o backend por `GET /api/notificacoes/nao-lidas` autenticado, não por
`/health` (que cai no fallback da SPA — memória `manto_deploys_janela_502`).

## Fora de escopo

**Preferências por `kind` por usuário.** Três tipos, ruído baixo. Entra **antes** da onda 3
(lembretes diários de parcela) — aí o SUPERADMIN, que recebe todos os `kind`, precisa silenciar
`parcela.vence`, ou o sino vira o e-mail de novo. O `kind` já está na tabela para isso.

**Web Push / notificação do navegador.** Pode ser a resposta certa para "não estou com o ERP
aberto", mas exige service worker, permissão e VAPID — feature própria. A v1 substitui o e-mail
com um deploy, não com uma infraestrutura. Se em duas semanas um lead esfriar por ninguém estar
com o ERP aberto, o caminho é este, não voltar o e-mail.

**SSE / WebSocket.** Decisão 15.

**Digest diário.** O dono não quer e-mail; e a decisão 6 da 266 continua válida (o lead é
perecível).

**E-mail como opção (`SiteSetting`/por usuário).** Decisão 18.

**Os outros e-mails internos** (ensaio, gasto novo, produção de figurino). Candidatos naturais,
listados na tabela das ondas; o pedido de hoje foi sobre o formulário, e cada um é uma decisão do
dono, não uma inferência.

**Apagar a notificação quando o evento é excluído.** Exige tocar o cascade de `roles`; a página do
evento já trata "não encontrado". `apagar_por_entidade` está pronta para quando a onda 2 mexer nos
caminhos de exclusão.

**Mover a montagem do `ClientFeedback` para `feedback_ops`.** Refatoração da 164; a chamada de
`notificar_avaliacao_recebida` fica logo antes do commit que já existe.

**`convite.aceito`.** Descartado — ruído em volume; o painel de confirmações da Home já mostra o
estado.

**`document.title` com a contagem, marcar como não lida, excluir uma notificação, arquivar.** Cada
um é uma decisão a mais por linha, e o problema do dono é excesso de decisões, não falta.
