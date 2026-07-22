# Feature Specification: Configurações, Logs, Sync, Desempenho e Ferramentas de Migração (Admin) em React

**Feature Branch**: `168-admin-config-react`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Migrar configurações do sistema, logs de auditoria, painel de sync
da agenda (Google Calendar), painel de desempenho, anúncio do portal do talento e as ferramentas
de migração de arquivos (Drive→volume) e importação de catálogo (CSV) do blueprint `admin` para
React + API JSON, fatia da User Story 6 (Cauda Administrativa) da migração 144. Todas as rotas
restritas a SUPERADMIN."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Editar configurações do sistema (Priority: P1)

Como Superadmin, preciso editar as configurações gerais do sistema (comissão padrão,
responsável EducaManto, imposto, Fator R, endereço/logística, chave do Google Maps,
notificações por email, número de WhatsApp dos formulários, data de início do sistema, logo)
pela interface React.

**Why this priority**: é a tela de configuração mais usada e com mais campos — base para o
funcionamento correto de vários outros módulos já migrados (Financeiro, Agenda).

**Independent Test**: editar cada grupo de campos em React e conferir que os valores gravados
são idênticos aos que a tela antiga (`/admin/settings`) gravaria para a mesma entrada, incluindo
o upload de logo.

**Acceptance Scenarios**:

1. **Given** um Superadmin autenticado, **When** ele atualiza os campos numéricos (comissão,
   imposto, Fator R, margem de saída), **Then** os valores são persistidos; entradas inválidas
   (não numéricas) são ignoradas silenciosamente — mesmo comportamento de hoje.
2. **Given** o mesmo Superadmin, **When** ele envia um novo arquivo de logo (formato aceito:
   png/jpg/jpeg/webp/svg), **Then** o arquivo é salvo e `logo_path` atualizado.
3. **Given** o mesmo Superadmin, **When** ele define o responsável EducaManto, **Then** o campo
   é gravado como `null` se o valor não for um id válido.
4. **Given** um usuário sem papel Superadmin, **When** ele tenta acessar a tela ou a API
   diretamente, **Then** recebe 403.

---

### User Story 2 - Consultar logs de auditoria e desempenho (Priority: P2)

Como Superadmin, preciso consultar o histórico de ações (logs de auditoria, com filtro por tipo
de entidade e por quem executou) e o painel de desempenho mensal (casting, figurino, vendas por
pessoa) pela interface React.

**Why this priority**: são telas de consulta (só leitura) — vêm depois da escrita de
configurações por serem menos frequentes no dia a dia.

**Independent Test**: abrir logs com e sem filtro, abrir desempenho para um mês com dados e
outro sem, e conferir paridade com as telas antigas (`/admin/logs`, `/admin/desempenho`).

**Acceptance Scenarios**:

1. **Given** um Superadmin autenticado, **When** ele abre os logs sem filtro, **Then** vê as 50
   entradas mais recentes (paginado), com a lista de tipos de entidade disponíveis para filtro.
2. **Given** o mesmo Superadmin, **When** ele filtra por tipo de entidade e/ou por quem
   executou, **Then** a lista é restrita de acordo, mesma regra de hoje (`ilike` no nome do
   ator).
3. **Given** o mesmo Superadmin, **When** ele abre o desempenho de um mês, **Then** vê os
   totais de casting/figurino por pessoa e vendas por vendedor (contagem e valor total), com o
   mês corrente como padrão quando nenhum é informado ou o formato é inválido.

---

### User Story 3 - Sincronizar agenda e anunciar no portal (Priority: P3)

Como Superadmin, preciso ver o status de sincronização de cada mês com o Google Calendar,
disparar uma sincronização manual dos próximos meses, disparar uma limpeza de eventos fantasma,
e enviar o anúncio de uma nova temporada por email às talentos cadastradas.

**Why this priority**: são ações operacionais pontuais (não usadas todo dia), mas envolvem
integração externa (Google Calendar, email) — vêm depois das telas de consulta puras.

**Independent Test**: disparar sync manual e limpeza de fantasmas (mockando a API do Google) e
conferir os mesmos resultados/mensagens da tela antiga; disparar o anúncio do portal (mockando o
envio de email) e conferir a contagem de enviados/falhas.

**Acceptance Scenarios**:

1. **Given** um Superadmin autenticado, **When** ele abre o painel de sync, **Then** vê, para
   cada mês com eventos no banco, a idade do último sync e se está "fresco" (menos de 20 min).
2. **Given** o mesmo Superadmin, **When** ele dispara "sincronizar agora", **Then** os próximos
   7 meses (atual + 6) são buscados e sincronizados, com o resultado por mês (sucesso/erro).
3. **Given** o mesmo Superadmin, **When** ele dispara "limpar eventos fantasma", **Then** todos
   os meses com eventos no banco são revisados e eventos que não existem mais no Google são
   removidos, com o total removido por mês.
4. **Given** o mesmo Superadmin, **When** ele dispara o anúncio do portal, **Then** o email é
   enviado a cada talento com email cadastrado, retornando quantos foram entregues e quantos
   falharam.

---

### User Story 4 - Ferramentas de migração de arquivos e importação de catálogo (Priority: P4)

Como Superadmin, preciso ver quantos arquivos de talentos ainda apontam para o Google Drive
(pendentes de migração para o volume) e disparar a migração em segundo plano; e ver o status da
última importação do catálogo (CSV) e disparar uma nova importação em segundo plano.

**Why this priority**: são ferramentas de manutenção pontual, cada uma já com seu próprio
processo em segundo plano (thread) e rastreador de status — só a superfície de disparo/consulta
muda; é a fatia de menor uso entre as quatro.

**Independent Test**: abrir cada tela, conferir a contagem de pendências/status atual, disparar
o processo em segundo plano e confirmar que uma segunda tentativa enquanto já em andamento é
recusada com aviso, mesma regra de hoje.

**Acceptance Scenarios**:

1. **Given** um Superadmin autenticado, **When** ele abre a tela de migração de arquivos,
   **Then** vê a contagem de arquivos pendentes (ainda em URL do Drive) e o status da migração
   em andamento, se houver.
2. **Given** o mesmo Superadmin, **When** ele dispara a migração, **Then** ela inicia em segundo
   plano; se já estiver em andamento, a API recusa com aviso (não erro).
3. **Given** o mesmo Superadmin, **When** ele abre a tela de importação de catálogo, **Then** vê
   o total de itens já importados e o status da última importação.
4. **Given** o mesmo Superadmin, **When** ele dispara a importação, **Then** ela inicia em
   segundo plano; se já estiver em andamento, a API recusa com aviso.

---

### Edge Cases

- Filtro de logs por ator sem nenhum resultado → lista vazia, sem erro.
- Mês de desempenho em formato inválido ou ausente → cai no mês corrente, mesmo fallback de hoje.
- Sync manual/limpeza com erro em um mês específico (ex.: falha da API do Google) → os demais
  meses continuam sendo processados; o mês com erro aparece marcado, sem interromper o restante.
- Migração de arquivos ou importação de catálogo disparada duas vezes seguidas → segunda
  tentativa recusada com aviso amigável, não erro; processo em andamento continua.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE expor a leitura e a escrita das configurações gerais como endpoints
  JSON, restritos a SUPERADMIN, com as mesmas validações/tolerâncias de hoje (campo inválido é
  ignorado, não bloqueia o resto do formulário).
- **FR-002**: O sistema DEVE expor o upload de logo como parte do endpoint de escrita de
  configurações (multipart), aceitando os mesmos formatos de hoje.
- **FR-003**: O sistema DEVE expor os logs de auditoria (paginados, com filtro por tipo de
  entidade e por ator) como endpoint JSON, restrito a SUPERADMIN.
- **FR-004**: O sistema DEVE expor o painel de desempenho mensal (casting/figurino/vendas) como
  endpoint JSON, restrito a SUPERADMIN, com o mesmo fallback de mês inválido/ausente de hoje.
- **FR-005**: O sistema DEVE expor o status de sync da agenda (por mês) e as duas ações
  (sincronizar agora, limpar fantasmas) como endpoints JSON, restritos a SUPERADMIN,
  reaproveitando exatamente a lógica já existente em `app/calendar/routes.py`/`service.py`.
- **FR-006**: O sistema DEVE expor o disparo do anúncio do portal (email) como endpoint JSON,
  restrito a SUPERADMIN, retornando a contagem de enviados/falhas.
- **FR-007**: O sistema DEVE expor o status e o disparo (em segundo plano) da migração de
  arquivos do Drive e da importação do catálogo como endpoints JSON, restritos a SUPERADMIN,
  reaproveitando os rastreadores de status já existentes (`drive_migration.migration_status`,
  `catalogo.importer.import_status`) sem duplicar o controle de concorrência (recusa amigável se
  já em andamento).
- **FR-008**: O comportamento das rotas Jinja antigas (`/admin/settings`, `/admin/logs`,
  `/admin/sync`, `/admin/desempenho`, `/admin/portal-announcement`, `/admin/migrar-arquivos`,
  `/admin/importar-catalogo`) DEVE permanecer idêntico ao de antes desta fatia até serem
  desativadas — sem regressão enquanto ambas coexistirem.

### Key Entities

- **Configuração do site (SiteSetting)**: registro único (id=1) com todos os parâmetros gerais
  do sistema; já existente — esta fatia não adiciona campos.
- **Log de auditoria (AuditLog)**: ação, tipo/id/nome da entidade, ator, data; já existente.
- **Log de evento (EventLog)**: usado para estatísticas de desempenho (casting/figurino); já
  existente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um Superadmin consegue editar configurações, consultar logs/desempenho, disparar
  sync/limpeza/anúncio do portal e disparar/consultar as duas ferramentas de migração
  inteiramente pela interface React, sem abrir nenhuma tela antiga.
- **SC-002**: Os dados/resultados mostrados em React são idênticos aos das telas antigas para o
  mesmo usuário e mesmos parâmetros — verificado por paridade automatizada (mockando as
  chamadas externas: Google Calendar, email).
- **SC-003**: Nenhum endpoint desta fatia é acessível por um usuário sem papel Superadmin (403
  em todos, tanto tela quanto API).

## Assumptions

- Chamadas externas reais (Google Calendar, envio de email, migração de arquivo em segundo
  plano) são mockadas na verificação automatizada — mesma abordagem já usada nas fatias 148/151
  (Google) e não há necessidade de testar a integração real nesta fatia.
- Fora do escopo: a gestão de produtos do catálogo (`/admin/catalogo*`, CRUD de produtos) — fatia
  própria (169) da US6.
