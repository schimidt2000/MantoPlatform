# Implementation Plan: Leitura e Gestão de Talentos e Figurino (154)

**Branch**: `154-talentos-figurino-leitura` | **Date**: 2026-07-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/154-talentos-figurino-leitura/spec.md`

## Summary

Primeira fatia da migração de Talentos e Figurino (US3) — equivalente ao que a 145 foi para
Agenda: leitura completa (busca/filtros/paginação de talentos, perfil com histórico de
eventos, catálogo de fichas de figurino) + as ações de gestão mais centrais (aprovar/rejeitar
talento pendente, editar talento, anotação interna, CRUD de ficha de figurino), tudo sem
upload de arquivo (adiado, mesmo padrão da 153). Levantamento do código atual (agente de
pesquisa dedicado) confirmou que só existem lookups mínimos já em JSON hoje — `GET /api/talents`
(picker de casting: id/nome/nome artístico, só ativos) e `figurino_sheets` dentro de
`GET /api/events/new/options` (id/nome/foto) — nenhum dos dois serve como base para esta
fatia (propósito e formato diferentes); toda a superfície desta fatia é endpoint novo.

## Technical Context

Igual à 144-153: Python/Flask + React (Vite/TS/TanStack Query). Sem dependência nova.
Verificação com test client Flask contra `manto_local`, requests fora de `app_context`.

**Sem upload nesta fatia** — perfil do talento e ficha de figurino mostram fotos/documentos já
existentes (campo já salvo no banco), mas não permitem enviar um novo arquivo. Ver Design
Decision 5 para o tratamento de URLs absolutas legadas (fotos importadas do Google Drive).

## Constitution Check

- **I (reutilizar)**: `GET /api/talents` (picker) e `figurino_sheets` de
  `/api/events/new/options` continuam intactos, sem nenhuma mudança — a nova superfície usa
  paths distintos (`/api/talents/directory`, `/api/talents/<id>`, `/api/figurino`) para não
  colidir nem confundir consumidores já existentes (`casting.ts`, `eventCreate.ts`). Núcleo de
  cada ação reaproveita exatamente a lógica de query/validação já em
  `app/talents/routes.py`/`app/figurino/routes.py`, extraída para funções puras reusadas pelos
  dois caminhos (Jinja e API) — mesmo padrão de `casting_ops.py`/`event_ops.py`/
  `observation_ops.py` (146-150).
- **II (padrões de código)**: núcleo em dois módulos novos, `app/talents/talent_ops.py` e
  `app/figurino/figurino_ops.py` — funções pequenas, sem `request`/`flash`/`current_user`
  dentro, type hints/docstrings em todas.
- **III (API first)**: 8 endpoints novos (4 talentos-leitura/escrita + 4 figurino), 100% JSON;
  views Jinja continuam existindo em paralelo.
- **IV (não quebrar)**: paridade de banco verificada contra `manto_local`; toda mutação Jinja
  segue idêntica (inclusive a assimetria real hoje entre `approve_talent`, que não valida o
  status atual — sempre aplica `status="active"` — e `reject_talent`, que recusa se o talento
  não estiver mais `pending`; a API replica essa mesma assimetria, não a "corrige").
- **V (feedback)**: erros 400/403 mostrados inline nos formulários React (mesmo padrão de
  153); toda ação com `useMutation` usa `loading` no `Button`; exclusão de ficha de figurino
  usa `window.confirm(...)` (mesmo padrão já estabelecido, sem componente de Dialog).
- **VII (monetário)**: `total_earned`/cachês do histórico do talento formatados com
  `formatBRL`/`<MoneyInput/>` de `@manto/money` (mesma fonte única já usada em toda a Agenda).
- **VIII (mobile-first)**: lista de talentos (cards) e catálogo de figurino conferidos em
  320–430px — grade de cards já é o padrão visual do Jinja atual, replicado em Tailwind.
- **IX (movimento)**: nenhuma transição nova crítica — listas/perfis são navegação padrão
  (React Router), sem modais/expansões que exijam Framer Motion nesta fatia.

Uma violação justificada — ver Complexity Tracking: dois módulos `_ops` novos (não reusam
`routes.py` como núcleo, diferente de 146-153) porque `app/talents/routes.py` e
`app/figurino/routes.py` não têm helpers compartilhados com outras rotas do projeto (ao
contrário de `calendar/routes.py`), então a mesma exceção "core-in-routes" não se aplica aqui —
o padrão correto e mais simples é o de `casting_ops.py`: módulo `_ops` dedicado.

## Project Structure

### Documentation (this feature)

```text
specs/154-talentos-figurino-leitura/
├── plan.md
├── data-model.md
├── quickstart.md
├── contracts/upload-endpoints... (n/a — ver contracts/talents-figurino-endpoints.md)
└── tasks.md
```

### Source Code (repository root)

```text
app/talents/talent_ops.py          # NOVO — núcleo puro: search_talents, get_talent_profile,
                                    #   approve_talent_status, reject_talent_record,
                                    #   update_talent_fields, save_notes (funções de módulo,
                                    #   sem request/flash/current_user; reusam a query de
                                    #   filtros já existente em list_talents, extraída sem
                                    #   duplicar)
app/talents/routes.py              # _handle_* Jinja existentes viram wrappers finos sobre
                                    #   talent_ops (mesmo padrão 146-150) nas rotas de escrita
                                    #   (approve/reject/edit/notes); list_talents e
                                    #   talent_detail (GET) passam a chamar
                                    #   talent_ops.search_talents/get_talent_profile também,
                                    #   sem mudar o HTML renderizado
app/figurino/figurino_ops.py       # NOVO — núcleo puro: list_sheets, create_sheet, edit_sheet,
                                    #   delete_sheet (sem upload de foto — parâmetro de arquivo
                                    #   não existe nesta fatia)
app/figurino/routes.py             # new_sheet/edit_sheet/delete_sheet viram wrappers finos
                                    #   sobre figurino_ops (upload de foto continua tratado só
                                    #   no wrapper Jinja, fora do núcleo, mesmo padrão do
                                    #   contrato na 152/153); figurinos() (GET) passa a chamar
                                    #   figurino_ops.list_sheets
app/api/talents_read.py            # NOVO — GET /api/talents/directory, GET /api/talents/<id>
app/api/talents_write.py           # NOVO — PATCH /api/talents/<id>, POST /api/talents/<id>/
                                    #   {approve,reject,notes}
app/api/figurino_read.py           # NOVO — GET /api/figurino
app/api/figurino_write.py          # NOVO — POST /api/figurino, PATCH /api/figurino/<id>,
                                    #   DELETE /api/figurino/<id>
app/api/__init__.py                # + import dos 4 módulos novos (efeito colateral de registro)
frontend/apps/internal/src/
├── lib/talents.ts                 # NOVO — useTalentDirectory (filtros+paginação),
│                                   #   useTalent(id), useApproveTalent, useRejectTalent,
│                                   #   useUpdateTalent, useSaveTalentNotes
├── lib/figurino.ts                # NOVO — useFigurinoSheets, useCreateFigurinoSheet,
│                                   #   useEditFigurinoSheet, useDeleteFigurinoSheet
├── pages/TalentsListPage.tsx      # NOVO — abas Ativos/Pendentes, busca, filtros, paginação
├── pages/TalentDetailPage.tsx     # NOVO — perfil completo + histórico + anotação
├── pages/TalentEditPage.tsx       # NOVO — form de edição (CPF condicional a superadmin)
├── pages/FigurinoListPage.tsx     # NOVO — catálogo + aviso de personagens sem ficha
├── pages/FigurinoFormPage.tsx     # NOVO — criar/editar ficha (peças dinâmicas, sem foto)
App.tsx                            # + rotas /talents, /talents/:id, /talents/:id/edit,
                                    #   /figurinos, /figurinos/new, /figurinos/:id/edit
packages/api-client/src/client.ts  # assetUrl: detecta URL absoluta (http/https) e não
                                    #   prefixa com API_BASE (fotos legadas do Drive) — ver
                                    #   Design Decision 5
scripts/db/verify_154_talentos_figurino.py  # NOVO: paridade API×Jinja
```

**Structure Decision**: dois módulos `_ops` novos (`talent_ops.py`, `figurino_ops.py`) como
núcleo compartilhado — diferente de 146-153, que colocam o núcleo em `routes.py` por causa de
helpers multi-uso; aqui não há esse acoplamento, então o padrão de módulo dedicado
(`casting_ops.py`/`event_ops.py`) é o mais simples e correto. Read/write de API separados por
módulo (`talents_read.py`/`talents_write.py`, `figurino_read.py`/`figurino_write.py`), mesmo
padrão de `agenda_read.py`/`agenda_write.py`.

## Design Decisions

1. **Núcleos `talent_ops.py`/`figurino_ops.py`** (funções de módulo, sem `request`/`flash`/
   `current_user`):
   - `search_talents(*, status, q, ja_trabalhou, language=None, race=None, top=None,
     bottom=None, shoe=None, height_op=None, height_value=None, passport=None, tags=None,
     character=None, page=1, page_size=60) -> dict`: mesma lógica de filtro/paginação de
     `list_talents` hoje, extraída sem duplicar (a view Jinja passa a chamar esta função e
     usa o resultado para montar o contexto do template — comportamento idêntico).
   - `get_talent_profile(talent, *, date_from=None, date_to=None) -> dict`: mesma lógica de
     `talent_detail` (histórico via `EventRole`, totais, personagens feitos) — SEM os blocos
     de avaliação (`received_sub_ratings`/`given_ratings`), que ficam fora desta fatia (ver
     spec Assumptions) e continuam calculados só no wrapper Jinja.
   - `approve_talent_status(talent) -> None`: seta `status="active"` (sem validar estado
     atual — paridade exata com `approve_talent`).
   - `reject_talent_record(talent) -> bool`: `False` se `status != "pending"` (não
     deleta); `True` e deleta se pendente — paridade com `reject_talent`.
   - `update_talent_fields(talent, data: dict, *, is_superadmin: bool) -> dict[str, str]`:
     mesma validação/gravação de `edit_talent` (CPF só se `is_superadmin`, 11 dígitos +
     unicidade); devolve mapa de erros (vazio = sucesso) — troca a lista de `flash` por mapa
     de campo→mensagem (Princípio V), o wrapper Jinja converte de volta pra flash.
   - `save_notes(talent, *, notes, warning_level) -> None`: paridade com `save_talent_notes`.
   - `list_figurino_sheets() -> dict`: mesma lógica de `figurinos()` (sheets +
     `chars_without_sheet`).
   - `create_figurino_sheet(*, character_name, pieces, notes) -> FigurinoSheet | None`:
     paridade com `new_sheet` SEM o parâmetro de foto (upload fora de escopo — a ficha nasce
     sem foto nesta fatia; o wrapper Jinja continua tratando `photo` fora do núcleo, como o
     upload de anexos do evento na 153).
   - `edit_figurino_sheet(sheet, *, character_name, pieces, notes) -> bool`: idem, sem foto.
   - `delete_figurino_sheet(sheet) -> None`: paridade com `delete_sheet` (inclui
     `delete_file(sheet.photo_filename)` e desvincular `EventRole.figurino_sheet_id` — a
     exclusão de foto existente continua acontecendo mesmo sem upload nesta fatia, é limpeza
     de dado já existente, não uma capacidade nova).

2. **Wrappers Jinja finos só nas rotas de ESCRITA — leitura fica em paralelo (correção
   durante a implementação)**: `approve_talent`/`reject_talent`/`save_talent_notes` (rotas de
   escrita simples, sem GET) viram wrappers de poucas linhas chamando o núcleo + `flash`.
   `edit_talent` (POST) mantém o parsing de `request.form` no wrapper, chama
   `update_talent_fields` para validar/gravar, converte erros em `flash`. Mesmo tratamento
   para `new_sheet`/`edit_sheet`/`delete_sheet` no figurino (POST).
   **`list_talents`/`talent_detail`/`figurinos()` (GET) NÃO são refatorados para chamar
   `search_talents`/`get_talent_profile`/`list_sheets`** — motivo técnico descoberto durante a
   implementação: o template `talents_list.html` usa métodos do objeto `Pagination` do
   Flask-SQLAlchemy (`pagination.iter_pages()`, `.has_next`, `.has_prev`, `.next_num`,
   `.prev_num`), que um dict simples não tem; reescrever o template para não depender desses
   métodos tocaria uma tela Jinja funcionando fora do escopo desta fatia. Em vez disso, as
   views GET do Jinja continuam exatamente como estão hoje (zero mudança), e
   `search_talents`/`get_talent_profile`/`list_sheets` são consumidos só pela API — mesmo
   padrão já usado pela Agenda (145): `serialize_event_summary`/`serialize_event_detail`
   também nunca foram chamados pelas views Jinja de agenda/evento, só pela API; a paridade
   entre os dois caminhos é garantida pelo script de verificação, não por uma função
   literalmente compartilhada.

3. **Endpoints REST**:
   - `GET /api/talents/directory` (`@api_login_required`, sem gate de papel — leitura
     aberta): querystring espelha os filtros de `list_talents` (`status`, `q`, `ja_trabalhou`,
     `language[]`, `race[]`, `top[]`, `bottom[]`, `shoe[]`, `height_op`, `height_value`,
     `passport[]`, `tag[]`, `character`, `page`) → chama `search_talents`, devolve
     `{"items": [...], "total", "page", "pages", "pending_count", "filter_options": {...}}`
     (opções de filtro só quando `status=active`, mesma condição de hoje).
   - `GET /api/talents/<id>` (mesmo gate — leitura aberta): `{"talent": {...}, "history":
     {...}, "can_edit": bool}` — `can_edit` é o mesmo `_can_edit_talent()` de hoje, exposto
     para a tela React decidir o que mostrar (mesmo papel de `flags` no detalhe de evento).
   - `PATCH /api/talents/<id>` (CASTING/SUPERADMIN): JSON com os campos editáveis; 400 com
     `fields` se CPF inválido/duplicado; 403 se não-editor.
   - `POST /api/talents/<id>/approve` (CASTING/SUPERADMIN): sem corpo, sempre 200.
   - `POST /api/talents/<id>/reject` (CASTING/SUPERADMIN): sem corpo; 400 se não estiver
     pendente; 200 (`{"ok": true}`) se removido.
   - `POST /api/talents/<id>/notes` (CASTING/SUPERADMIN): JSON `{"notes", "warning_level"}`.
   - `GET /api/figurino` (leitura aberta): `{"items": [...], "chars_without_sheet": [...]}`.
   - `POST /api/figurino` (FIGURINO/SUPERADMIN): JSON `{"character_name", "pieces": [{"name",
     "qty"}], "notes"}`; 400 se nome vazio.
   - `PATCH /api/figurino/<id>` (FIGURINO/SUPERADMIN): idem, edição.
   - `DELETE /api/figurino/<id>` (FIGURINO/SUPERADMIN): sem corpo, 200.
   - Cada endpoint devolve o recurso atualizado no sucesso — aqui não há um "detalhe
     agregador" único como o evento; talento e ficha de figurino são recursos independentes.

4. **Frontend — páginas novas, não seções de uma página existente**: diferente da Agenda (uma
   `EventDetailPage` central), Talentos/Figurino ganham páginas próprias
   (`TalentsListPage`/`TalentDetailPage`/`TalentEditPage`/`FigurinoListPage`/
   `FigurinoFormPage`) e rotas novas no `App.tsx` — replica a estrutura de telas separadas já
   existente no Jinja (`talents_list.html`/`talent_detail.html`/`talent_edit.html`/
   `figurinos.html`/`figurino_form.html`), sem inventar uma navegação nova.

5. **`assetUrl` passa a detectar URL absoluta** (`packages/api-client/src/client.ts`): fotos
   de talento/figurino importadas pelo caminho legado (Google Sheets/Drive) podem já ser uma
   URL absoluta (`https://drive.google.com/...`), diferente de todo anexo de evento (sempre
   `/uploads/...` relativo). Hoje `assetUrl` sempre prefixa `API_BASE` — em produção
   (`API_BASE` não-vazio) isso quebraria uma URL já absoluta. Correção mínima: se `path`
   começar com `http://` ou `https://`, devolver sem prefixar; caso contrário, comportamento
   idêntico ao de hoje. Único ponto de mudança, usado automaticamente por toda tela que já
   chama `assetUrl` (nenhum outro call site muda de comportamento, já que nenhum deles hoje
   lida com URL absoluta).

6. **Ratings/avaliações fora do payload de perfil**: `get_talent_profile` não inclui
   `received_sub_ratings`/`given_ratings` — o wrapper Jinja de `talent_detail` continua
   calculando esses dois blocos separadamente (fora do núcleo) para não tocar nessa área,
   consistente com a decisão de manter `/talents/avaliacoes` inteiramente fora desta fatia.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|---------------------------------------|
| Núcleo em módulos `_ops` novos (`talent_ops.py`/`figurino_ops.py`), não em `routes.py` | Diferente de `calendar/routes.py`, os `routes.py` de talents/figurino não têm helpers compartilhados com outras partes do projeto — não há motivo para acoplar o núcleo ao módulo de rotas | Colocar no `routes.py` misturaria núcleo puro com view functions sem nenhum ganho de reuso (a exceção "core-in-routes" da Agenda existe só por causa de helpers multi-uso que não existem aqui) |
