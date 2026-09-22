---
description: "Tarefas da feature 302 — o que o artista vê do evento no Portal"
---

# Tasks: O artista passa a ver quando o evento termina, quando é o ensaio e de onde sai

**Input**: artefatos em `/specs/302-portal-detalhes-do-evento/`

**Pré-requisitos**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/api-endpoints.md](./contracts/api-endpoints.md)

**Verificação (OBRIGATÓRIA — constituição, Princípio VIII)**: `verify_302.py` é escrito na fase
Foundational, **antes** do núcleo, e nasce falhando pelos motivos certos (chave ausente no payload,
código `"manto"` cru no JSON). Não existe pytest neste repositório.

**Migration**: **nenhuma**. `app/models.py` não é tocado e `migrations/versions/` não recebe
arquivo — se alguma tarefa abaixo parecer pedir migration, a tarefa está errada.

## Formato: `[ID] [P?] [Story] Descrição`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: história da spec (US1…US7)

---

## Phase 1: Setup

- [X] T001 Acrescentar `DEPARTURE_DEFAULT_LOCATION = "Manto Produções"` em `app/constants.py`, com
      comentário dizendo que o literal já existia em três lugares e que esta constante os
      substitui (R4)

---

## Phase 2: Foundational (bloqueia todas as histórias)

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

- [X] T002 **`specs/302-portal-detalhes-do-evento/verify_302.py`** — os 22 cenários da seção
      "Verificação" da spec. Login por `POST /api/portal/auth/login` (talentos T e U) e
      `POST /api/auth/login` (staff do cenário 13); requisições **fora** de `app.app_context()`;
      cenário 13 conferido por **conexão separada**; três cenários que DEVEM falhar. Escrito AGORA
      e falhando nos cenários ainda não construídos
- [X] T003 No `verify_302.py`, o **arranjo**: **tudo descartável** — evento, cargo, ensaio e os
      dois talentos nascem e morrem no arquivo, com prefixo próprio. Ensaio entra por `INSERT`
      direto, com `google_event_id` descartável, **nunca** por `POST /api/events/<id>/ensaios`,
      que cria evento no Google Agenda da empresa (R13).
      **Esta tarefa foi reescrita na convergência.** Ela mandava *assumir uma `EventRole`
      existente com `talent_id IS NULL`*, por medo da regra do `CLAUDE.md` §4 ("nunca semeie role
      com `character_name` inventado — o sync do Google apaga a role e manda e-mail de remoção a
      gente de verdade"). Lido de novo, assumir linha de produção é o caminho **mais** arriscado:
      escreve um talento de teste no espelho e depende da limpeza rodar para desfazer. O que a
      regra proíbe é pendurar cargo inventado em evento **REAL**, e isso não acontece aqui
- [X] T004 No `verify_302.py`, a **limpeza no `finally`**: apagar tudo que tem o prefixo —
      ensaios (filhos) antes dos pais, por causa da FK para a própria tabela, e `roles.clear()`
      antes do usuário de staff. **Não há o que restaurar**, porque nada de produção é tocado
      (ver T003); a redação anterior, que mandava devolver a vaga assumida a `talent_id` nulo,
      pertencia ao arranjo antigo
- [X] T005 `MAKEUP_LOCATION_LABELS` + `makeup_location_label()` em `app/calendar/event_ops.py`,
      **colados em `resolve_makeup_location` (`:83-91`)** — o módulo que codifica é o que
      decodifica. Docstring explica que é o inverso daquela função e que serve portal, e-mail e
      WhatsApp (R4)
- [X] T006 [P] Trocar o literal `'Manto Produções'` pela constante em `app/calendar/event_ops.py`
      (no diff de `save_logistics`) e em `app/email_service.py` (linha da Saída) — troca de
      literal por constante, zero mudança de comportamento

**Checkpoint**: `verify_302.py` roda e falha **pelos motivos certos**. Se falhar por `ImportError`,
credencial ou endereço inválido, o verify está errado — conserte o verify, não o código.

---

## Phase 3: US1 — O artista vê quando o evento termina (P1) 🎯 MVP

**Meta**: a linha principal do card passa a `sexta-feira, 3 de out, 16:00 às 20:00 · Local`.

**Teste independente**: abrir `/portal/agenda` como um talento com evento futuro e ler a faixa.
Não depende de nenhuma outra história.

- [X] T007 [US1] `formatDateTimeRange(start, end)` em
      `frontend/apps/portal/src/lib/format.ts`, ao lado de `formatDateTime` — sem `end`, cai em
      `formatDateTime`. **Quando o fim é em outro dia, a saída diz isso** (FR-002a): comparar as
      datas por recorte de string, **nunca** por `new Date().toISOString()` (horário de parede de
      São Paulo). Comentário registra por que o `formatRange` do app interno **não** foi promovido
      (R5)
- [X] T008 [US1] Usar `formatDateTimeRange` na linha principal de
      `frontend/apps/portal/src/pages/PortalAgendaPage.tsx`
- [X] T009 [P] [US1] Idem em `frontend/apps/portal/src/pages/PortalConvitesPage.tsx`
- [X] T010 [P] [US1] **Não** mexer na linha de data de
      `frontend/apps/portal/src/pages/PortalHistoricoPage.tsx`: ela mostra só a data, sem hora, e
      continua assim (FR-001). Deixar um comentário dizendo que a omissão é deliberada — sem ele,
      a próxima pessoa "completa" a tela e acrescenta um horário de início que ninguém pediu

**Checkpoint**: cenários 1 e 4b do verify verdes; faixa conferida nas telas.

---

## Phase 4: US2 — O artista descobre o ensaio pelo portal (P1)

**Meta**: o bloco "Antes do evento" nasce, com os ensaios do show, na Agenda **e** nos Convites.

**Teste independente**: semear um ensaio num show futuro com o talento escalado e abrir as duas
telas.

- [X] T011 [US2] `_antes_do_evento(roles) -> dict[int, dict]` em
      `app/talent_portal/portal_ops.py` — **uma** consulta de ensaios para todos os eventos da
      rodada, indexada por `parent_event_id`. Filtra `event_type == "ENSAIO"`,
      `cancelled_at IS NULL` e **ensaio já realizado** (FR-004a); ordena por `start_at` crescente,
      porque a relação `ensaios` não tem `order_by` e o Postgres devolve ordem arbitrária (R12).
      Item leva `start_at`, `end_at` e `location` — **sem `description`**, com o comentário
      dizendo por quê (R9)
- [X] T012 [US2] `_role_summary` (`portal_ops.py:168-205`) ganha o parâmetro `before_event` e a
      chave homônima; `None` quando não há nada a mostrar (R1)
- [X] T013 [US2] `get_agenda` (`portal_ops.py:208-270`) chama `_antes_do_evento` para
      `pending_invites + upcoming` e passa `None` no histórico; `get_historico`
      (`portal_ops.py:751-801`) passa `None` (R11)
- [X] T014 [US2] Em `app/talent_portal/portal_ops.py`, `.options(selectinload(EventRole.event))`
      nas três consultas de `get_agenda` e na de `get_historico` —
      **tarefa própria de propósito**: o N+1 de `role.event` **já existia**
      antes desta feature, e precisa aparecer no diff como decisão, não como efeito colateral
      (R7). Precedente no repo: `app/api/admin_catalogo_read.py:104`
- [X] T015 [P] [US2] Tipos em `frontend/apps/portal/src/lib/portalAgenda.ts`:
      `PortalRehearsal`, `PortalBeforeEvent`, e `before_event?: PortalBeforeEvent | null` em
      `PortalRole` — **opcional** (FR-013b): na janela de bundle novo com servidor velho o campo
      não existe, e a tela tem de se comportar como hoje
- [X] T016 [US2] Componente `frontend/apps/portal/src/components/AntesDoEvento.tsx` — recolhido por
      padrão, devolve `null` quando não há bloco, alvo de toque ≥44px, rótulo anunciável por leitor
      de tela e estado aberto/fechado audível (FR-009e). Nome visível **"Antes do evento"**, um só,
      no bloco e no controle (FR-009d). Molde: `CacheLine.tsx`
- [X] T017 [US2] Renderizar `<AntesDoEvento>` no card de `PortalAgendaPage.tsx`
- [X] T018 [US2] Renderizar `<AntesDoEvento>` no card de `PortalConvitesPage.tsx` (FR-009a) — é
      onde a informação muda uma decisão que ainda não foi tomada

**Checkpoint**: cenários 2, 3, 4c, 6c, 7, 11, 12 verdes; bloco conferido nas duas telas.

---

## Phase 5: US3 — Maquiagem e saída aparecem (P2)

**Meta**: o bloco ganha as duas linhas de logística, com o local escrito por extenso.

**Teste independente**: gravar logística num evento com elenco e abrir o card.

- [X] T019 [US3] Em `_antes_do_evento` (`app/talent_portal/portal_ops.py`), montar `makeup` e
      `departure` — **cada um existe só se
      houver horário** (FR-006a); o local é companhia. `makeup.location` passa por
      `makeup_location_label`; `departure.location` cai em `DEPARTURE_DEFAULT_LOCATION` quando
      vazio
- [X] T020 [US3] Ordenar os itens do bloco na **ordem cronológica real** — ensaio, maquiagem,
      saída (FR-009c) — em `frontend/apps/portal/src/components/AntesDoEvento.tsx`
- [X] T021 [US3] Renderizar as duas linhas em `AntesDoEvento.tsx`, cada uma omitida quando ausente

**Checkpoint**: cenários 4, 5, 5b, 8b verdes.

---

## Phase 6: US4 — A produção descobre que deixou o elenco no escuro (P2)

**Meta**: chip de pendência + alerta na seção que resolve. **Zero mudança de backend** — todos os
campos já saem em `app/api/agenda_read.py`.

**Teste independente**: abrir um evento futuro com elenco e sem logística.

- [X] T022 [US4] Chip **Logística** em `calcularPendencias`
      (`frontend/apps/internal/src/components/EventDetail/ResumoSection.tsx`), no molde dos chips
      existentes. Condição: pode editar o evento **e** evento futuro **e** ao menos uma vaga com
      talento e não dispensada **e** falta horário de maquiagem ou de saída. Comparar data por
      `start_at`, nunca por `toISOString()`
- [X] T023 [US4] Alerta em linha dentro do painel "Logística & trajeto"
      (`frontend/apps/internal/src/components/EventDetail/LogisticaSection.tsx`), mesma condição,
      dizendo quantas pessoas estão escaladas e que o Portal do Artista mostra esses horários no
      card. Apontar para a saída sugerida que o `TrajetoCard` já exibe ao lado. Sem `Dialog` — não
      é destrutivo e não bloqueia

**Checkpoint**: cenário 13 verde (conexão separada); os quatro estados do chip conferidos na tela.

---

## Phase 7: US5 — A tela para de chamar todo mundo de personagem (P3)

**Meta**: "Função" para vaga que não é de personagem, nas **três** superfícies.

**Teste independente**: abrir as três telas do portal e copiar um convite de Coordenador.

- [X] T024 [US5] `"role_type": role.role_type` em `_role_summary`
      (`app/talent_portal/portal_ops.py`) — o código do modelo, não o rótulo pronto, como já fazem
      `payment_status` e `invite_status` (R6)
- [X] T025 [P] [US5] `role_type?: "character" | "extra"` em
      `frontend/apps/portal/src/lib/portalAgenda.ts` — **opcional** (FR-013b)
- [X] T026 [US5] Componente `frontend/apps/portal/src/components/RoleLine.tsx` — fonte única do
      rótulo, no molde de `CacheLine.tsx`. Sem `role_type` no payload, comporta-se como hoje
- [X] T027 [US5] Usar `<RoleLine>` em `PortalAgendaPage.tsx`, `PortalConvitesPage.tsx` e
      `PortalHistoricoPage.tsx` — os três lugares que hoje repetem a string `Personagem:`
- [X] T028 [P] [US5] E-mail de convite (`app/email_service.py`): rótulo por `role.role_type` e
      local da maquiagem por `makeup_location_label` — hoje o artista recebe
      `Maquiagem: 14:00 — manto` (FR-012a)
- [X] T029 [P] [US5] Mensagem de WhatsApp: rótulo por `role_type` em
      `frontend/apps/internal/src/lib/eventDetail.ts` e local **traduzido** vindo de
      `frontend/apps/internal/src/components/EventDetail/CastingSection.tsx`, que hoje passa
      `event.makeup_location` cru (FR-012b). Reusar o `makeupLocationLabel` que já existe em
      `LogisticaSection.tsx` — extrair para onde os dois alcancem, sem duplicar

**Checkpoint**: cenários 6 e 6b verdes.

---

## Phase 8: US6 — A Agenda deixa de repetir o histórico inteiro (P3)

**Meta**: a Agenda vira só "Próximos eventos".

**Teste independente**: abrir `/portal/agenda` como um talento com muitas apresentações passadas.

- [X] T030 [US6] Remover a `<section>` do Histórico de
      `frontend/apps/portal/src/pages/PortalAgendaPage.tsx`
- [X] T031 [US6] Limpar o que a remoção deixou órfão, **à mão**: o `tsc` não ajuda aqui. Remover
      só a seção não orfana import nenhum (o card continua usando `RatingLink`, `CacheLine` e
      `formatRelativeDay` pelos dois ramos da prop que distingue futuro de passado); os imports só
      ficam órfãos depois que os ramos mortos saírem, e a prop sempre verdadeira o `noUnusedLocals`
      nunca acusa. Conferir que `formatRelativeDay` **continua** em uso
- [X] T032 [US6] **Não** remover `history` do payload de `get_agenda` (FR-013a). Deixar comentário
      no `portal_ops.py` explicando que a lista continua sendo enviada de propósito, com o motivo
      (servidor e site sobem separados) e que a remoção é do ciclo seguinte — senão a próxima
      pessoa "limpa" e derruba o portal de quem não recarregou

**Checkpoint**: cenário 8 verde; contador da aba Histórico conferido na tela.

---

## Phase 9: US7 — A ficha de figurino diz de que evento é (P3)

- [X] T033 [US7] Declaração de RBAC no topo de `app/api/portal_figurino.py` — é o único dos cinco
      módulos do portal sem ela; usar a mesma forma em prosa dos outros quatro. **Não** mexer no
      403: decisão registrada do dono
- [X] T034 [P] [US7] **Nada a mudar no payload da ficha**: `title` e `start_at` já saem
      (`app/api/portal_figurino.py`). Conferir isso e seguir — a tarefa existe para que ninguém
      acrescente `end_at` "por simetria": FR-014 pede nome e data, e a hora já está no card
- [X] T035 [US7] Cabeçalho com nome e data do evento em
      `frontend/apps/portal/src/pages/PortalFigurinoPage.tsx`, usando `formatLongDate`, que **já
      existe** em `format.ts` e não era usada por ninguém (Princípio I)

**Checkpoint**: cenário 10 continua recusando quem não está escalado (é um dos que DEVEM falhar), e
a ficha é conferida **na tela** — a US7 não tem cenário de API próprio, porque o payload não muda.

---

## Phase 10: Polish e documentação

- [X] T036 `ruff check` nos Python tocados (`portal_ops.py`, `event_ops.py`, `email_service.py`,
      `portal_figurino.py`, `constants.py`); `cd frontend && npm run typecheck` limpo nas três SPAs
- [X] T037 Conferência de tela do quickstart §3, **em viewport mobile 375×812** e varrendo
      320–430px: Agenda, Convites, Histórico, ficha de figurino, e a tela interna do evento nos
      dois estados do chip. `tsc` limpo não prova card
- [X] T038 [P] `docs/01` — contrato de `GET /api/portal/agenda` e de
      `GET /api/portal/events/<id>/figurino`
- [X] T039 [P] `docs/02` §C — linhas `/portal/agenda` (a seção Histórico sai; **desfazer a promessa
      do link de avaliar herdada da 229**), `/portal/convites`, `/portal/historico`,
      `/portal/eventos/:id/figurino`; e o detalhe de evento interno (aviso de logística e mensagem
      de convite copiada)
- [X] T040 `docs/03` — entrada nova no topo + linha na tabela do índice, referenciando a **229**
      (o link de avaliar) e a **230** (a lista não-recusada). Correção é entrada nova, nunca edição
      da antiga
- [X] T041 [P] `docs/05` — as seis dívidas: (1) remover `history` de `get_agenda` no ciclo
      seguinte; (2) a observação do ensaio, a reabrir quando o campo for usado como observação;
      (3) a tradução do local de maquiagem em Python e em TypeScript; (4) a ficha de figurino
      recusando com 403 onde o Princípio XIII manda 404; (5) o formatador de horário duplicado
      entre portal e app interno; (6) marcar ensaio não avisar o elenco
- [X] T042 `verify_302.py` → **22/22 OK**; `git status --short` limpo;
      `migrations/versions/` sem untracked (não deve haver nenhum — a feature não tem migration)

---

## Dependências

```text
Setup (T001)
   └─> Foundational (T002-T006)  ← nada começa antes de terminar
          ├─> US1 (T007-T010)         independente
          ├─> US2 (T011-T018)         independente — cria o bloco
          │      └─> US3 (T019-T021)  precisa do bloco existir
          ├─> US4 (T022-T023)         independente (só frontend interno)
          ├─> US5 (T024-T029)         independente
          ├─> US6 (T030-T032)         independente
          └─> US7 (T033-T035)         independente
                 └─> Polish (T036-T042)
```

**A única dependência entre histórias** é US3 depender de US2: as linhas de logística moram no
bloco que US2 cria. As outras cinco podem ser feitas em qualquer ordem.

## Paralelismo

- **T009 e T010** (Convites e Histórico) em paralelo com T008 — arquivos diferentes.
- **T015, T025** (tipos) em paralelo com o backend correspondente.
- **T028 e T029** (e-mail e WhatsApp) em paralelo entre si e com o portal — domínios diferentes.
- **T034** em paralelo com T033 — mesmo arquivo, partes distintas; se conflitar, sequencie.
- **T038, T039, T041** em paralelo — documentos diferentes. **T040 não**: `docs/03` é append-only
  no topo e duas escritas simultâneas se atropelam.

## Estratégia de entrega

**MVP = US1 + US2.** Juntas respondem o pedido do dono inteiro: o horário final (o que ele pediu) e
o ensaio (o que o levantamento achou, e que é a informação mais urgente que o artista não tem). As
duas são P1 e independentes entre si.

**Incremento seguinte = US3 + US4**, que só fazem sentido juntas: expor maquiagem e saída sem
avisar a produção mostraria linha vazia para todo mundo, porque hoje **nenhum** dos 64 eventos
futuros tem logística preenchida.

**Por último, US5, US6 e US7** — correções de texto e de leitura, valiosas e não bloqueantes.

**Tudo entrega num deploy só** (regra da casa: publicar em lote, fora do horário), mas a ordem
acima é a que mantém a branch entregável a cada parada.

---

## Phase 11: Convergência

> **Nota de processo, para quem ler depois:** o `/speckit-converge` é read-only por contrato — ele
> deveria **só** anexar tarefas, e `/speckit-implement` as completaria. Aqui os oito achados foram
> **corrigidos na própria rodada**, porque sete eram de uma a cinco linhas e um era defeito de
> produto saindo para artista. Ficam registrados marcados, com o que foi feito, em vez de
> reaparecerem como fila fantasma. A divergência do processo está dita aqui de propósito.
>
> A avaliação cruzou os 28 FR contra o código e **nenhum requisito ficou sem implementação**. Os
> vãos foram de outra natureza: dois cenários de verify que passavam a vazio, uma quarta superfície
> vazando o código do banco, um componente reimplementado que já existia, e artefatos descrevendo
> o contrário do que o código faz.

- [X] T043 **CRITICAL · contradicts** — o cenário 6b do `verify_302.py` **não provava nada**.
      `"Manto Produções" in html` é verdade em todo e-mail (está no `<title>` e no rodapé de
      `_html_wrap`) e `">manto<"` nunca casa, porque `_info_row` renderiza `>09:00 — manto</td>`.
      Apagar a tradução deixava o cenário verde. Agora olha a **linha da maquiagem**
      (`"— Manto Produções<"` presente, `"— manto<"` ausente), e isso foi **provado por mutação**:
      com `makeup_location_label` removida do e-mail, o verify cai para 21/22
- [X] T044 **HIGH · partial** — FR-007/SC-004 vazavam por uma **quarta superfície** que a spec não
      previu: `save_logistics` (`app/calendar/event_ops.py`) montava
      `f"Local de maquiagem: {old} → {new}"` com o **código cru**, e essa frase vira
      `EventRole.change_description` — o aviso "Este evento teve uma alteração" do card do portal —
      e o corpo de `send_event_changed_email`. O artista lia "Local de maquiagem: manto → local".
      Agora as duas pontas passam por `makeup_location_label`
- [X] T045 **HIGH · contradicts** — o cenário 12 (ensaio órfão) comparava `it["event_id"]` (o id do
      SHOW) com o id do ensaio órfão: nunca iguais, asserção impossível de falhar. E o órfão nascia
      com o mesmo `location` de todos os outros ensaios, indistinguível. Agora tem local próprio
      (`LOCAL_ORFAO`) e ganhou o controle anti-vazio. **Honestidade registrada na docstring**: com
      a consulta atual (`parent_event_id.in_(...)`) ele ainda não pode falhar — é trava para a
      mudança imaginável, não prova do presente
- [X] T046 **MEDIUM · missing (Princípio I e XI)** — `AntesDoEvento` reimplementou à mão um
      recolhível que **já existe**: `AccordionRow` de `@manto/ui` (feature 187), com altura animada
      por Framer Motion, `useReducedMotion`, `aria-expanded` e `aria-controls`. A versão própria
      ficou sem animação nenhuma, contra o Princípio XI que o próprio `plan.md` citou. Trocado; o
      alvo de 44px passou a vir pelo `summary`, que é quem dá altura ao botão. Conferido na tela:
      44px, `aria-expanded` alternando, conteúdo e ordem iguais
- [X] T047 **MEDIUM · contradicts** — T003 e T004 estavam marcadas feitas descrevendo o
      **oposto** do que o verify faz: mandavam assumir uma `EventRole` de produção e restaurá-la.
      O verify cria tudo descartável, de propósito e com o motivo na docstring. As duas tarefas, a
      linha do cenário 14 e a nota da spec foram reescritas para descrever o que existe
- [X] T048 **LOW · contradicts** — FR-015 dizia "**nem** saída **nem** maquiagem preenchidas"
      (as duas faltando), e o código acende quando **qualquer uma** falta. O comportamento é o
      certo — logística pela metade deixa o elenco no escuro do mesmo jeito —, então quem mudou foi
      o requisito
- [X] T049 **LOW · contradicts** — o mapa de código do `plan.md` prometia `end_at` no payload da
      ficha de figurino, que o contrato e a T034 **proíbem**. O código estava certo; o plano é que
      ficou mentindo para quem o lesse depois
- [X] T050 **LOW · partial** — quatro itens de conformidade: `_com_evento()` sem anotação de
      retorno e `_role_summary` com parâmetros novos sem `Args:`/`Returns:` (constituição II);
      `AntesDoEvento` fazendo `rehearsals.length` sem guarda, contra o próprio FR-013b; e
      `docs/01` §4.3 sem linha nenhuma para o portão do portal, apesar de a feature ter quitado a
      declaração que faltava em `portal_figurino.py`

- [X] T051 **MEDIUM · contradicts (achado da própria rodada 1)** — a asserção nova do cenário 6b
      ancorava em `"— Manto Produções<"`, e a linha de **Saída** do mesmo e-mail termina
      exatamente assim: mesmo texto padrão, mesmo travessão. A fixture do cenário não tem horário
      de saída, então a asserção era honesta **por acidente** — bastaria alguém acrescentar saída
      àquele evento para ela voltar a passar sozinha. Ancorada na hora da maquiagem
      (`">09:00 — Manto Produções<"`). Achado ao escrever o roteiro da rodada 2, antes de rodá-la

## Rodada 2 — convergido

Feita depois de `0f3d0c4`, mirando o que as **correções da rodada 1** poderiam ter introduzido —
que é onde esta esteira costuma achar o próximo defeito. **Nenhum vão novo.** O que foi conferido:

| Risco levantado | Resultado |
|---|---|
| `AccordionRow` com `px-3` fora e `pb-3 pl-6` dentro criando recuo duplo | não: `cn` é `twMerge`, e `space-y-2` não conflita com o padding — as três classes sobrevivem, e o recuo alinha o conteúdo sob o rótulo |
| `border-b border-line` do `AccordionRow` aparecendo dentro do card arredondado | não: ele é filho único, então `last:border-0` zera |
| `summary` com elemento interativo dentro do `<button>` (HTML inválido) | não: é um `<span>` com ícone e texto |
| `makeup_location_label(old)` devolvendo `None` e escrevendo "None" no aviso | não pode: `save_logistics` grava `makeup_location or None`, então o banco só tem NULL ou texto não-vazio, e a condição já exclui NULL |
| `LOCAL_ORFAO` quebrando outro cenário que conte ensaios | não: 22/22 |
| chave perdida no payload | não: 18 chaves — as 16 de sempre mais `role_type` e `before_event`, exatamente o contrato |

### Aceito sem mudar, com o motivo

- **O cenário 4b não testa FR-002a.** Ele prova que o payload leva as duas datas; a regra do "dia
  seguinte" mora em `format.ts` e **não tem cobertura automatizada** — o repositório não tem
  runner de teste de frontend (constituição: não há pytest nem equivalente em TS). Foi conferida
  **na tela**, e está escrito aqui para ninguém supor cobertura que não existe.
- **A ficha de figurino usa `formatWeekday` além de `formatLongDate`.** T035 nomeava só o segundo.
  É uma palavra a mais ("sexta-feira, 23 de outubro de 2026") que ninguém pediu e que ninguém
  perde nada por ter.
- **O cenário 13b roda dentro de `app.app_context()`**, contra a regra do próprio módulo. Precisa
  de `db.engine` para escutar as consultas, e não testa permissão — a exceção agora está comentada
  na docstring do cenário.
- **A prop `payment` de `CacheLine` ficou órfã**: quem a passava era o card do histórico da Agenda,
  que saiu na US6. A tela Histórico desenha o cachê inline e nunca importou `CacheLine`, apesar de
  a docstring dele dizer que é "fonte única para Convites, Agenda e Histórico". **Não foi mexido**:
  unificar as duas rendições é melhoria real, não conserto, e mexeria numa tela fora do pedido.
  Registrado aqui; vale como candidato à próxima feature que tocar o Histórico.
