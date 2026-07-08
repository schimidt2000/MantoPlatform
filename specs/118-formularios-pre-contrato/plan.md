# Implementation Plan: Formulários de Pré-Contrato (118)

**Branch**: `118-formularios-pre-contrato` | **Date**: 2026-07-08 | **Spec**: [spec.md](./spec.md)

## Summary

Novo módulo `app/formularios/` com dois formulários públicos (pré-contrato comum e
corporativo, estrutura exata de `formularios contexto/*.md`), no molde do módulo
`cadastro` (blueprint sem `@login_required`, template auto-contido mobile-first, honeypot,
rate-limit). No envio: valida no servidor (erro re-renderiza com os valores preservados),
salva `FormResponse` no banco e renderiza página de sucesso que abre o WhatsApp da cliente
com a mensagem formatada para o número configurado em `SiteSetting.whatsapp_form_number`
(padrão 5511970570577). Área interna (`COMERCIAL`/`FINANCEIRO`/`SUPERADMIN`): listagem de
respostas com links copiáveis dos formulários, detalhe da resposta, associação a cliente
(sugestão automática por telefone normalizado + busca + criar cliente a partir da
resposta), exclusão só SUPERADMIN com `confirm()`. Home ganha alerta "pré-contrato sem
cliente" no painel comercial. `/events/new` ganha buscador de respostas (JSON endpoint,
busca sem acento) que vincula a resposta ao evento; placeholder "Colar aqui resposta
whatsform" substituído.

## Technical Context

**Stack**: o existente (Flask + SQLAlchemy + Jinja2 + JS vanilla). **Storage**: 1 migration
manual — tabela `form_responses` + coluna `whatsapp_form_number` em `site_settings`.
`down_revision = "d0e1f2a3b4c5"` (head atual), conferir unicidade do revision novo.

### Data model

`FormResponse` (`form_responses`):
- `id` PK; `form_type` String(20) not null (`comum` | `corporativo`)
- `data` Text not null — JSON com todos os campos preenchidos (rótulo→valor)
- `contact_name` String(200) not null — contratante (comum) / razão social (corporativo)
- `contact_phone` String(20) nullable, index — WhatsApp normalizado (`normalize_phone` de
  `app/clientes/importer.py:38`) para sugestão de cliente
- `contact_phone_display` String(30) — como digitado
- `event_date` Date nullable, index — data do evento informada
- `client_id` FK `clients.id` nullable, index; `event_id` FK `calendar_events.id`
  nullable, index (vínculo opcional; relationships com `lazy=True`)
- `created_at` DateTime not null

`SiteSetting.whatsapp_form_number` String(20) nullable — número destino das mensagens;
lido com fallback para `5511970570577`; editável em `admin_settings.html` (padrão: input +
parsing na view `admin_settings`).

### Rotas (blueprint `formularios_bp`, `app/formularios/routes.py`)

Públicas (sem login, `@limiter.limit` no POST, honeypot):
- GET/POST `/f/pre-contrato` — formulário comum
- GET/POST `/f/corporativo` — formulário corporativo
- POST sucesso → renderiza `formularios/enviado.html` com o link
  `https://api.whatsapp.com/send?phone=<destino>&text=<mensagem urlencoded>` (botão grande
  + redirecionamento automático via JS). A resposta já está salva ANTES.
- POST inválido → re-renderiza o formulário com `old` (valores preservados) + erros por
  campo (FR-004).

Internas (decorator `require_vendas`-like COMERCIAL/FINANCEIRO/SUPERADMIN, no padrão de
`app/clientes/routes.py:37`):
- GET `/formularios/` — seção de formulários: cards com link copiável de cada formulário +
  listagem das respostas (recentes primeiro, badge de status: sem cliente / com cliente /
  vinculada a evento)
- GET `/formularios/respostas/<id>` — detalhe completo + sugestão de cliente por telefone
  + busca de cliente (reusa endpoint `/clientes/search`) + botão "criar cliente a partir
  da resposta" + associar/desassociar
- POST `/formularios/respostas/<id>/associar` — associa cliente (`client_id` do form) ou
  cria a partir dos dados (`normalize_phone` para dedup, mesmo padrão do quick-create)
- POST `/formularios/respostas/<id>/delete` — só SUPERADMIN (`abort(403)` senão),
  `confirm()` no template
- GET `/formularios/respostas/search?q=` — JSON para o buscador do `/events/new`
  (`strip_accents_lower`/`unaccent_lower_sql` em `contact_name`, dígitos em
  `contact_phone`, limit 10; shape `{id, name, phone_display, form_type, event_date,
  created_at}`)

### Integrações

- **Home** (`app/__init__.py`, rota `/`): sob `show_comercial`, contar/listar
  `FormResponse.client_id IS NULL` → painel `sector-panel` novo em `home.html`
  ("Pré-contratos sem cliente"), cada linha linka pro detalhe da resposta.
- **`/events/new`** (`event_create.html` + `create_event` em `app/calendar/routes.py`):
  bloco buscador de resposta (input + resultados, JS próprio `form_response_picker.js` no
  estilo do `client_picker.js`, hidden `form_response_id`); no POST, se veio
  `form_response_id` válido, seta `response.event_id = event.id` após o flush. Placeholder
  da descrição troca "Colar aqui resposta whatsform" por "Observações do evento…".
- **Página do evento**: se houver resposta vinculada, link "Ver pré-contrato" no bloco
  comercial (leitura simples, sem editor).

### Templates públicos

`app/templates/formularios/_public_base.html` (doctype completo, viewport, CSS inline
mobile-first — colunas empilhadas, inputs grandes, identidade Manto: roxo + botão verde
WhatsApp `#25D366`) estendido por `pre_contrato.html` e `corporativo.html`. Campos, seções,
obrigatoriedades (asterisco vermelho), máscaras leves (`inputmode` + formatação JS de
CPF/CNPJ/CEP/telefone), condicional "Descreva Outros" (aparece/obriga se "Outros"),
ViaCEP no comum (auto-preenche endereço; falha silenciosa). `enviado.html` com botão
WhatsApp + abertura automática.

### Testing (contra manto_local, requests fora de app_context)

1. POST público comum válido → `FormResponse` salvo, página de sucesso contém
   `api.whatsapp.com/send?phone=5511970570577` e a mensagem com os campos.
2. POST inválido (CPF errado, obrigatório vazio) → 200 com erros e valores preservados no
   HTML (FR-004); nada salvo.
3. Condicional "Outros" sem descrição → erro.
4. Corporativo válido → salvo com `form_type="corporativo"`.
5. Honeypot preenchido → descartado silenciosamente.
6. Home comercial mostra alerta com resposta sem cliente; some após associar.
7. Sugestão por telefone: resposta com telefone de cliente existente sugere o cliente.
8. Associar + criar cliente a partir da resposta (dedup por telefone).
9. Delete: SUPERADMIN ok, COMERCIAL 403.
10. `/formularios/respostas/search` sem acento ("joão" acha "Joao" e vice-versa).
11. `/events/new` com `form_response_id` → `response.event_id` setado.
12. RBAC: rotas internas 403 para papel sem permissão; públicas abrem deslogado.

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Molde do módulo `cadastro` (público+mobile+limiter+honeypot); `normalize_phone`, `strip_accents_lower`/`unaccent_lower_sql`, padrão `client_picker.js`, padrão `sector-panel` da home, padrão SiteSetting/admin_settings. |
| II. Padrões Python | ✅ Type hints, docstrings, validação por função pequena por campo. |
| III. Camadas | ✅ Blueprint novo com rotas finas; formatação da mensagem e validação em funções puras no módulo. |
| IV. Não quebrar | ✅ Tabela nova + 1 coluna nullable em site_settings; `/events/new` só ganha campo opcional; descrição continua livre. |
| V. UI/UX | ✅ Mobile-first (90% celular), erro por campo sem perder dados, loading/duplo-envio protegido, confirmação antes de excluir. |
| VI. Planejar | ✅ Este plano. |
| VII. Moeda BR | N/A (sem valores monetários calculados). |
| VIII. Mobile público | ✅ Superfície pública nova — conferida em viewport mobile. |

**Gate: PASS.**

## Decisões

1. **Salvar antes de abrir o WhatsApp**: o registro no sistema é o que gera valor (alerta,
   associação, vínculo com evento); a mensagem é conveniência. Se a cliente não concluir o
   envio da mensagem, o comercial ainda vê a resposta na home.
2. **Mensagem gerada no servidor** (urlencoded no link `api.whatsapp.com/send`): formato
   idêntico ao conteúdo do formulário (`*Rótulo:* valor` por linha, seções separadas) —
   nada construído no cliente, sem risco de divergência entre banco e mensagem.
3. **Número destino em `SiteSetting`** (`whatsapp_form_number`), não hardcoded — troca sem
   deploy (assumption da spec).
4. **`data` como JSON Text + colunas extraídas** (`contact_name`, `contact_phone`,
   `event_date`): flexível para os dois formulários (campos diferentes) sem uma coluna por
   pergunta; as colunas extraídas cobrem busca/sugestão/ordenação.
5. **URLs públicas curtas `/f/...`**: fáceis de mandar por WhatsApp; seção interna fica em
   `/formularios/`.
6. **Vínculo com evento na `FormResponse.event_id`** (não no evento): evento não ganha
   coluna; N respostas nunca apontam pro mesmo evento sem querer (checagem no POST).
7. **Hard delete com `confirm()` nativo** (padrão feature 107, `admin_users.html`).
