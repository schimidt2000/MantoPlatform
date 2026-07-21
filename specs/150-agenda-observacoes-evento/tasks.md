# Tasks: observações do evento em React (150)

**Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md)
Padrão de 146/147/148/149: núcleo compartilhado → adaptadores finos (Jinja + API) → React →
verificação por paridade contra `manto_local`. Sem mudança de schema. Observações não disparam
e-mail. Criar imagem fica fora (upload adiado); imagem existente só em leitura.

## Backend — núcleo e adaptadores

- [X] T001 `app/calendar/observation_ops.py` (NOVO): `add_observation(event, *, obs_type,
      content=None, label=None, file_path=None) -> EventObservation | None` (normaliza strip→None;
      `image` exige `file_path`, `text`/`link` exigem `content`, tipo desconhecido → `None`; quando
      válido `db.session.add` e devolve, **sem commit**) e `delete_observation(event, obs_id) -> bool`
      (busca escopada `filter_by(id=obs_id, event_id=event.id)`; deleta+commit→`True`, senão `False`).
      Só importa `models` (sem `routes` — sem ciclo). Docstrings/type hints.
- [X] T002 `routes.py`: `add_observation`/`delete_observation` viram wrappers finos. O `add` mantém o
      parsing dos arrays `obs_type[]/obs_content[]/obs_label[]/obs_image[]` e o upload de imagem
      (`_save_file_upload`), mas cria cada item via `observation_ops.add_observation(...)` (conta os
      não-`None` para o flash, commita 1x no fim). O `delete` chama o núcleo e `abort(404)` se `False`.
      Efeito observável idêntico ao atual.
- [X] T003 `agenda_write.py`: `POST /api/events/<id>/observations` (`@api_login_required`; body
      `{obs_type, content, label?}`; rejeita `obs_type ∉ {text,link}` com 400; `None`→400
      `{content:"Obrigatório"}`; senão commit) e `DELETE /api/observations/<obs_id>`
      (`@api_login_required`; 404 se não existe; núcleo `False`→404). Ambos retornam
      `serialize_event_detail`.
- [X] T004 `agenda_read.py`: cada item de `data["observations"]` ganha
      `"image_url": o.file_path if o.obs_type == "image" else None`. Campo aditivo (demais campos
      inalterados).

## Frontend

- [X] T005 [P] `packages/api-client/src/client.ts`: exportar `API_BASE` e `assetUrl(path)` (prefixa
      path público com a base do Flask; dev = string vazia). `lib/agenda.ts`:
      `EventoDetalhe.observations[]` ganha `image_url?: string | null`. `lib/observations.ts` (NOVO):
      `useAddObservation(eventId)` (POST) e `useDeleteObservation(eventId)` (DELETE) — atualizam
      `["event", id]` com o evento retornado.
- [X] T006 `EventDetailPage.tsx`: nova seção **Observações** — lista texto (puro), link (âncora
      `target=_blank rel=noopener`) e imagem (`<img src={assetUrl(o.image_url)}>`, `max-width:100%`),
      cada item com botão remover (confirmação); form "nova observação" (seletor texto/link + conteúdo
      + rótulo opcional) com feedback de pending. Sem opção de imagem. Conferir viewport 320–430px
      (Princípio VIII).

## Verificação

- [X] T007 `scripts/db/verify_150_observacoes.py`: paridade API×Jinja campo a campo (`obs_type`,
      `content`, `label`) para adicionar texto e link, e remover; conteúdo vazio (API 400, Jinja sem
      linha); imagem via API (400); remoção escopada a outro evento (404); idempotência do delete
      (2º→404); leitura: observação de imagem pré-existente serializa `image_url == file_path`. Jinja
      302, API 200/400/404. `ruff` nos arquivos tocados; `tsc`/`build` limpos.

## Fase final

- [X] T008 Marcar tasks; commit no branch `150-...`; merge+push. `CLAUDE.md`/memória pointer.
      Changelog só quando substituir algo em produção (equipe segue no Jinja) — não republicar agora.

## Dependências

- T001 → T002/T003 (ambos chamam o núcleo). T004 independe de T001-T003 (só serializer).
  T005 → T006. Verificação (T007) por último. Nenhuma mudança de schema.
