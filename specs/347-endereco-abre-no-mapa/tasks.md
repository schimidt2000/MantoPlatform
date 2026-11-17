---
description: "Tasks da feature 347 — endereço do evento abre no app de mapas"
---
# Tasks: Tocar no endereço do evento e escolher o app de mapas

**Input**: artefatos em `/specs/347-endereco-abre-no-mapa/`

**Pré-requisitos**: plan.md, spec.md (histórias e "Verificação"), research.md, data-model.md,
contracts/endereco-no-mapa.md

**Verificação (Princípio VIII)**: `specs/347-endereco-abre-no-mapa/verify_347.py`, escrito na fase
Foundational antes do núcleo (`linksDeMapa`). Nada no backend muda (research R5). Empacota `frontend/packages/ui/src/lib/mapas.ts` com o `esbuild` de
`frontend/node_modules` e roda os casos no `node`; o cenário 6 lê o `manto_local` para provar que
o endereço chega às duas telas.

## Formato: `[ID] [P?] [Story] Descrição`

## Phase 1: Setup

Nenhuma tarefa: sem dependência nova, env, migration ou rota (plan, Contexto técnico).

---

## Phase 2: Foundational (bloqueia as histórias)

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

- [X] T001 **`specs/347-endereco-abre-no-mapa/verify_347.py`** — os 5 cenários da spec
      ("Verificação"): (1) endereço com acento/vírgula/número → 3 opções na ordem Google Maps,
      Apple Mapas, Waze com as URLs exatas de `research.md` R1; (2) "&", "#", "/" e espaços nas
      pontas → codificados e aparados; (3) `""`, `"   "`, `null`, `undefined` → `[]`; (4) **deve
      falhar**: um montador ingênuo (sem `encodeURIComponent`) passado pela mesma checagem tem de
      ser reprovado; (5) `EnderecoNoMapa` exportado em `frontend/packages/ui/src/index.ts` e usado
      com o endereço nas quatro telas da spec; (6) `manto_local`, só leitura: `GET /api/events/<id>`
      de um evento com endereço (login por `POST /api/auth/login`, Superadmin descartável,
      requisições fora do `app_context`) e `portal_ops.get_agenda` de um talento escalado nele
      trazem `location` igual ao gravado; (7) limpeza no `finally` (`rollback`, `roles.clear()`,
      apagar o usuário). Sai com código ≠ 0 se algum falhar. Escrito AGORA e FALHANDO (módulo
      `mapas.ts` ausente).
- [X] T002 `frontend/packages/ui/src/lib/mapas.ts`: `linksDeMapa(endereco)` pura, tipos `AppDeMapa`
      e `OpcaoDeMapa`, URLs em constantes no topo (contrato `contracts/endereco-no-mapa.md`)
- [X] T003 `frontend/packages/ui/src/components/endereco-no-mapa.tsx`: `EnderecoNoMapa` — `null` sem
      endereço; gatilho `<button type="button">` com `MapPin`, cor de link, quebra de linha e nome
      acessível que diz que abre no app de mapas (FR-007, FR-011); `Dialog` "Abrir endereço" com o
      endereço na descrição e as três opções como `<a target="_blank" rel="noopener noreferrer">`
      de altura ≥ 44px que fecham a escolha ao toque (FR-003–FR-006); foco volta ao gatilho
      (herdado do `Dialog`)
- [X] T004 `frontend/packages/ui/src/index.ts`: exportar `EnderecoNoMapa`, `EnderecoNoMapaProps`,
      `linksDeMapa`, `OpcaoDeMapa`, `AppDeMapa`

**Checkpoint**: cenários 1–4 do verify em PASS; cenário 5 ainda falha (nenhuma tela usa a peça).

---

## Phase 3: História 1 — Equipe abre o endereço do evento no app de mapas (P1) 🎯 MVP

**Objetivo**: endereço tocável no cabeçalho e no "Local" de "Dados do evento" do app interno.

**Verificação da história**: cenário 5 do verify em PASS para os dois arquivos do app interno;
quickstart §3 itens 1–4.

- [X] T005 [P] [US1] `frontend/apps/internal/src/components/EventDetail/EventHeader.tsx`: trocar
      `{event.location && <span>• {event.location}</span>}` por `<EnderecoNoMapa
      endereco={event.location} />` (o ícone substitui o "•")
- [X] T006 [P] [US1] `frontend/apps/internal/src/components/EventDetail/ResumoSection.tsx`
      (`DadosLeitura`): `<DataRow label="Local">` mostra `<EnderecoNoMapa
      endereco={event.location} />` quando há endereço e "—" quando não há

**Checkpoint**: história 1 funcional e conferida na tela.

---

## Phase 4: História 2 — Artista abre o endereço do evento pelo portal (P1)

**Objetivo**: endereço tocável nos cards de "Próximos eventos" e "Convites".

**Verificação da história**: cenário 5 do verify em PASS (quatro telas); quickstart §3 itens 5–8.

- [X] T007 [P] [US2] `frontend/apps/portal/src/pages/PortalAgendaPage.tsx` (`RoleCard`): tirar
      `· {role.location}` da linha da data e pôr `<EnderecoNoMapa endereco={role.location} />` em
      linha própria depois do dia relativo ("hoje", "em 3 dias"), com alvo ≥ 44px (FR-007) — o
      quando junto, o onde logo abaixo (decidido na tela aberta, achado U1 do analyze)
- [X] T008 [P] [US2] `frontend/apps/portal/src/pages/PortalConvitesPage.tsx` (`InviteCard`): trocar
      `<p className="text-sm text-muted">{role.location}</p>` por `<EnderecoNoMapa
      endereco={role.location} />` com alvo ≥ 44px, na mesma ordem da Agenda (depois do dia
      relativo)

**Checkpoint**: histórias 1 e 2 funcionam de forma independente.

---

## Phase 5: Polimento e transversais

- [X] T009 `cd frontend && npm run typecheck` limpo (três SPAs) e `ruff check
      specs/347-endereco-abre-no-mapa/verify_347.py` (+ `ruff format`, arquivo novo)
- [X] T010 `verify_347.py` verde nos 5 cenários (o 4 reprovado como deve)
- [X] T011 `quickstart.md` §3 executado no Browser pane (skill `manto-conferir-tela`): app interno
      em 390px e tela larga; portal em 375×812, sem rolagem lateral a 320/375/430px; tema escuro;
      `href`/`target` de cada opção conferidos
- [X] T012 Texto novo ("Abrir endereço", rótulo acessível) revisado pelo Princípio XV na tela
      aberta, junto dos vizinhos
- [X] T013 Docs: `docs/02` (página do evento no app interno; Agenda e Convites do portal) e
      `docs/03` (entrada no topo + linha no índice)

---

## Dependências e ordem

- Foundational: T001 → T002 → T003 → T004 (o verify nasce falhando; `mapas.ts` antes do
  componente; export por último)
- US1 (T005, T006) e US2 (T007, T008) dependem só de T004 e são independentes entre si; as quatro
  tarefas mexem em arquivos diferentes ([P])
- Polimento depois das duas histórias

## Paralelismo

- Depois de T004: T005, T006, T007 e T008 juntos (um arquivo cada)

## Estratégia

- **MVP**: Foundational + História 1 (app interno). A História 2 tem a mesma prioridade e é o mesmo
  componente; as duas sobem juntas.
- Commit `feat(347):` por caminho, nunca `git add -A`. Merge e push só quando o dono pedir; só
  `frontend/` muda → deploy só do `manto-frontend`, sem queda.
