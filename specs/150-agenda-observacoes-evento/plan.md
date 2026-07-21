# Implementation Plan: observações do evento em React (150)

**Branch**: `150-agenda-observacoes-evento` | **Date**: 2026-07-21 | **Spec**: [spec.md](spec.md)

## Summary

Migra as **observações do evento** (hoje só no Jinja) para React + API JSON, aplicando o padrão de
146/147/148/149. Núcleo extraído para um novo `app/calendar/observation_ops.py`; os handlers Jinja
`add_observation`/`delete_observation` viram wrappers finos; dois endpoints REST
(`POST /api/events/<id>/observations`, `DELETE /api/observations/<obs_id>`); o serializer de leitura
passa a expor a **URL do arquivo** das observações de imagem; a `EventDetailPage` ganha uma seção
**Observações** (leitura de texto/link/imagem) com form de adicionar (texto/link) e remover.
Verificação por paridade contra `manto_local`. **Criar imagem fica fora** (upload adiado). Sem
mudança de schema.

## Technical Context

Igual à 146–149: Python/Flask + React (Vite/TS/TanStack Query); sem dependência nova; verificação
com test client contra `manto_local` (Postgres); requests fora de `app_context`. Observações não
disparam e-mail (nenhum mock de envio necessário). Entidade já existente `EventObservation`
(`event_id`, `obs_type` ∈ {text,link,image}, `content`, `file_path`, `label`, `created_at`).
`file_path` das imagens já é um caminho público servido por `/uploads/<path>` (`@login_required`) —
o cookie de sessão cross-subdomínio (144) faz o `<img>` do app React (beta.*) carregar do Flask
(app.*) sem trabalho extra.

## Constitution Check

- **I (reutilizar)**: núcleo único em `observation_ops` (`add_observation`, `delete_observation`),
  reusado por Jinja e API. A regra de "o que conta como observação válida" (texto/link exigem
  conteúdo; imagem exige arquivo) e a de "remoção escopada ao evento" moram só no núcleo.
  Dependência unidirecional `routes → observation_ops` (o módulo só importa `models`, nunca
  `routes` — sem ciclo). O upload de imagem (multipart, `_save_file_upload`) permanece no adaptador
  Jinja — o núcleo recebe `file_path` já resolvido.
- **IV (não quebrar)**: adaptadores Jinja com efeito idêntico (incluindo criar imagem e criar várias
  observações de uma vez, que o loop do handler mantém); paridade verificada campo a campo. O
  POST/DELETE Jinja segue 302.
- **V (feedback)**: form e botão de remover com feedback (mutations do TanStack); o front bloqueia o
  clique enquanto pendente — clique-duplo não cria/remove em duplicidade.
- **VII (monetário)**: sem valor monetário nesta fatia.
- **VIII (mobile-first)**: a seção de Observações é conferida em viewport 320–430px — imagens com
  `max-width:100%`, sem rolagem horizontal, alvos de toque ≥44px.
- **IX (movimento)**: reusa os utilitários de transição já presentes na `EventDetailPage` (sem
  animação nova exigida).

## Project Structure

```text
app/calendar/observation_ops.py   # NOVO: add_observation, delete_observation (núcleo)
app/calendar/routes.py            # add_observation/delete_observation viram wrappers finos
app/api/agenda_write.py           # + POST /api/events/<id>/observations, DELETE /api/observations/<id>
app/api/agenda_read.py            # observations[]: + image_url (derivado de file_path)
frontend/packages/api-client/src/client.ts   # + assetUrl(path) e export de API_BASE
frontend/apps/internal/src/
├── lib/agenda.ts                 # EventoDetalhe.observations: + image_url?: string | null
├── lib/observations.ts           # NOVO: useAddObservation, useDeleteObservation
└── pages/EventDetailPage.tsx     # nova seção Observações (leitura + adicionar texto/link + remover)
scripts/db/verify_150_observacoes.py   # NOVO: paridade API×Jinja
```

## Design Decisions

1. **Núcleo em `observation_ops.py`** (parâmetros explícitos, sem `request.form`/`flash`/
   `current_user`), sem commit interno — o chamador (loop Jinja ou endpoint) commita, preservando o
   "um commit por requisição" de hoje:
   - `add_observation(event, *, obs_type, content=None, label=None, file_path=None)
     -> EventObservation | None` — normaliza `content`/`label` (strip → None se vazio); valida:
     `image` exige `file_path`, `text`/`link` exigem `content`, tipo desconhecido → retorna `None`
     (item ignorado, exatamente como o loop do Jinja pula item inválido). Quando válido,
     `db.session.add(...)` e devolve a observação. **Não** commita.
   - `delete_observation(event, obs_id) -> bool` — busca `EventObservation` escopada ao evento
     (`filter_by(id=obs_id, event_id=event.id)`); se achar, deleta, commita e devolve `True`; senão
     `False` (o adaptador Jinja transforma `False` em `abort(404)`, a API em `json_error(404)`).
2. **Adaptadores Jinja** (`routes.py`): `add_observation` mantém o parsing dos arrays
   `obs_type[]/obs_content[]/obs_label[]/obs_image[]` e o upload de imagem (`_save_file_upload`),
   mas cada item passa a ser criado via `observation_ops.add_observation(...)` (conta os não-`None`
   para o flash e commita uma vez no fim). `delete_observation` chama o núcleo e `abort(404)` se
   `False`. Efeito idêntico ao atual — garantido pela verificação de paridade.
3. **Endpoints REST** (`agenda_write.py`), ambos `@api_login_required` (sem gate de papel, paridade
   com o `@login_required` do Jinja) e devolvendo `serialize_event_detail`:
   - `POST /api/events/<id>/observations` — corpo `{obs_type, content, label?}`. Rejeita
     `obs_type ∉ {text, link}` com 400 (imagem não suportada via API nesta fatia). Chama
     `add_observation(...)`; se retornar `None` (conteúdo vazio), 400 `{content: "Obrigatório"}`;
     senão `db.session.commit()` e devolve o evento.
   - `DELETE /api/observations/<obs_id>` — carrega a observação p/ achar o `event_id`; se não
     existir, 404. Chama `delete_observation(event, obs_id)`; `False` → 404; senão devolve o evento.
     (Segue o padrão de `DELETE /api/roles/<id>` da 147: 200 + evento serializado.)
4. **Serializer** (`agenda_read.py`): cada item de `data["observations"]` ganha
   `"image_url": o.file_path if o.obs_type == "image" else None` (o `file_path` já é `/uploads/...`).
   Campo aditivo — não quebra consumidores da 145. Os demais campos (`id`, `obs_type`, `content`,
   `label`, `created_at`) seguem.
5. **api-client**: exporta `API_BASE` e um helper `assetUrl(path)` (prefixa o path público com a
   base do Flask; em dev, string vazia + proxy Vite). Fonte única da base — o React não concatena
   origem à mão.
6. **Frontend**: `lib/observations.ts` com `useAddObservation(eventId)` (POST) e
   `useDeleteObservation(eventId)` (DELETE), ambos atualizando `["event", eventId]` com o evento
   retornado (mesmo padrão de `lib/casting.ts`/`lib/eventOps.ts`). Na `EventDetailPage`, nova seção
   **Observações**: lista os itens (texto puro; link como âncora `target=_blank rel=noopener`;
   imagem como `<img src={assetUrl(o.image_url)}>` com `max-width:100%`), cada um com botão remover
   (confirmação); abaixo, um form "nova observação" com seletor texto/link + campo de conteúdo +
   rótulo opcional, botão com feedback de pending. Sem opção de imagem (fora de escopo).
7. **Verificação** (`verify_150_observacoes.py`): para adicionar (texto e link) e remover, roda via
   API e via Jinja em eventos equivalentes e compara o estado de `event_observations` campo a campo
   (`obs_type`, `content`, `label`); cobre conteúdo vazio (API 400, Jinja ignora/sem linha), imagem
   via API (400), remoção escopada a outro evento (404), idempotência do delete (2º → 404), e
   leitura: uma observação de imagem pré-existente serializa `image_url` = `file_path`. Jinja segue
   302; API 200/400/404. `ruff` nos arquivos tocados; `tsc`/`build` limpos.

## Complexity Tracking
*Sem violações.*
