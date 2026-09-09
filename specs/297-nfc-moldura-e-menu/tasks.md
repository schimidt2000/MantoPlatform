---
description: "Tasks da feature 297 — vídeo leve com moldura, menu na tag NFC e recado da cliente"
---
# Tasks: 297 — A luminária vira portal

**Input**: artefatos em `/specs/297-nfc-moldura-e-menu/`

**Pré-requisitos**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/nfc-api.md](./contracts/nfc-api.md),
[quickstart.md](./quickstart.md)

**Verificação (OBRIGATÓRIA — constituição, Princípio VIII)**: `specs/297-nfc-moldura-e-menu/verify_297.py`,
contra `manto_local`, escrito na fase Foundational (T007), **antes** do núcleo de negócio. Quinze
cenários (os 12 planejados mais a corrida do worker, o vídeo deitado e a abertura do sistema). Não existe pytest neste repositório.

**Aviso que muda como se trabalha aqui**: o `manto_local` desta máquina tem 1 tag NFC e nenhuma
entrega, contra 35 tags e 10 vídeos da produção. Nada neste plano depende de dado que já esteja no
espelho; toda fixture é criada e apagada pelo próprio verify.

## Formato: `[ID] [P?] [Story] Descrição`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: US1 a US5, na numeração das histórias da spec

---

## Phase 1: Setup

- [X] T001 [P] Constantes em `app/constants.py`: `MANTO_SPOTIFY_URL` (o link que o dono mandou),
      `NFC_VIDEO_LARGURA_MAXIMA = 1080`, `NFC_VIDEO_CRF = 23`, `NFC_MOLDURA_EXTENSOES`,
      `NFC_MENSAGEM_MAX_CHARS = 1000`, `NFC_PROCESSAMENTO_PRESO_MINUTOS = 30`, com comentário
      dizendo que endereço público é constante de código e nunca variável de ambiente (Princípio XIV)
- [X] T002 [P] Subpastas do disco em `app/__init__.py`, ao lado de `NFC_MEDIA_FOLDER` (`:515-517`):
      criar `nfc_media/entrada`, `nfc_media/mestres` e `nfc_media/sistema` com `os.makedirs`, e
      expor os caminhos em `app.config` — o layout está em `data-model.md` §4

---

## Phase 2: Foundational (bloqueia todas as histórias)

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

- [X] T003 Modelos em `app/models.py` conforme `data-model.md`: as 11 colunas novas de
      `NfcTagDelivery` (§1), a classe `NfcTagMessage` com a relação `tag.messages` e
      `cascade="all, delete-orphan"` (§2), e as 2 colunas novas de `SiteSetting` (§3). Docstring de
      cada bloco explica o PORQUÊ — em especial por que `client_id` do recado é fotografia do
      vínculo, não referência viva
- [X] T004 Migration Alembic **manual** `migrations/versions/<rev>_nfc_moldura_e_recados.py`, com
      `down_revision = "b7d2e4f1a9c3"` (head conferido em 09/09), `upgrade`/`downgrade` completos,
      índice parcial de `processing_status` com `postgresql_where` **e** `sqlite_where` (molde:
      `b7d2e4f1a9c3_notifications.py:57-61`), e os dois índices de `nfc_tag_messages`. Docstring
      longa em pt-BR no estilo de `a1c7d3e59b02`. Aplicar no `manto_local` com `flask db upgrade`
- [X] T005 Conferir, no `manto_local` e relendo `migrations/versions/<rev>_nfc_moldura_e_recados.py`,
      que entregas já existentes são lidas como `pronto` e `has_frame = false` **pelo default da
      coluna**, sem nenhum `UPDATE` de linha no `upgrade` (Princípio IV)
- [X] T006 [P] Núcleo puro `app/impressoes3d/video_ops.py`: `ffmpeg_disponivel()`,
      `sondar(caminho) -> InfoVideo` via `ffprobe`, `montar_filtro(moldura)`,
      `converter(origem, destino, *, moldura, largura_maxima)` com `nice -n 19`, `-threads 1`,
      temporário no disco persistente (**nunca** `/tmp`, `research.md` D5) e exceção própria
      `VideoIndisponivel`. Cadeia de filtros e flags exatas em `research.md` D3
- [X] T007 **`specs/297-nfc-moldura-e-menu/verify_297.py`** — os 12 cenários da seção "Verificação"
      da spec, escritos AGORA e FALHANDO pelos motivos certos. Gera o vídeo de teste na hora com
      `ffmpeg` (encoder `libopenh264` nesta máquina, `libx264` na produção); login só por
      `POST /api/auth/login`; escrita conferida por **conexão separada**; requisições fora de
      `app.app_context()`; cenários 7 e 8 DEVEM falhar do lado do servidor; limpeza no `finally`
      com `roles.clear()` antes de apagar o usuário e remoção dos arquivos criados

**Checkpoint**: modelos migrados no `manto_local`, `video_ops` capaz de converter um arquivo solto,
verify falhando nos cenários ainda não construídos.

---

## Phase 3: História 1 — A cliente consegue, enfim, assistir (P1) 🎯 MVP

**Objetivo**: todo vídeo enviado vira um arquivo de 1080 em pé com cerca de 15 MB por 30 segundos, e
os dez que já estão no ar passam a tocar.

**Verificação da história**: cenários 1, 2 e 11 do `verify_297.py` em PASS.

- [X] T008 [US1] `app/impressoes3d/nfc_ops.py`: `add_delivery` ganha `com_moldura: bool = True`,
      grava o arquivo recebido em `nfc_media/entrada/`, cria a linha com
      `processing_status="pendente"` e **retorna sem converter** — é o que cumpre o SC-003
- [X] T009 [US1] `app/impressoes3d/nfc_ops.py`: a fila — `reivindicar_proxima_entrega()` com o
      `UPDATE` condicional atômico de `data-model.md` §1, `processar_entrega(delivery)` que chama
      `video_ops.converter`, grava mestre e entregue, preenche as colunas de metadados e apaga o
      arquivo de entrada, e `destravar_presas()` para o que ficou em `processando` por mais de 30
      minutos (deploy no meio do caminho)
- [X] T010 [US1] `app/__init__.py`: `_start_nfc_video_worker(app)` no molde de `_start_virtual_sweep`
      (`:318-364`) — guarda de `WERKZEUG_RUN_MAIN`, import dos ops dentro do laço,
      `with app.app_context()` dentro do `while`, `except Exception as exc:  # noqa: BLE001` que
      nunca deixa a thread morrer, `daemon=True`, `name="nfc-video"`, e chamada no bloco do
      `MANTO_SEM_THREADS` (`:841-860`)
- [X] T011 [US1] `app/api/nfc_read.py`: `resolve_code` e o serializador público só enxergam entrega
      com `processing_status == "pronto"`; a rota de mídia pública devolve o mesmo 404 genérico para
      entrega não pronta; o payload público ganha `width`/`height` — contrato em
      `contracts/nfc-api.md` §1 e §2. **O shape vazio não pode mudar** (SC-006)
- [X] T012 [US1] `app/api/nfc_read.py`: o serializador do ERP (`serialize_tag` em `nfc_ops.py:313`)
      passa a devolver `processing_status`, `processing_error`, `file_size_bytes`,
      `duration_seconds`, `width`, `height` e `has_frame` na entrega
- [X] T013 [P] [US1] `frontend/server.js`: acrescentar a rota de upload da tag a `MEDIA_PATTERNS`
      (`:546-551`) para que ela não herde o prazo de 180 s — justificativa em `research.md` D6, com
      comentário no código dizendo por que o padrão do irmão da Loja Virtual já a cobria por acaso
- [X] T014 [P] [US1] `frontend/apps/internal/src/lib/nfc.ts`: tipos novos da entrega; troca do envio
      por `uploadForm` com progresso (molde `apps/internal/src/lib/revisao.ts:53-89`); polling com
      `refetchInterval` que devolve `false` quando nenhuma entrega está `pendente`/`processando`
      (molde `apps/internal/src/lib/adminConfig.ts:170-176`)
- [X] T015 [US1] `frontend/apps/internal/src/components/nfc/VideoDialog.tsx`: `UploadProgressBar`
      durante o envio e `snapshotFile` do `@manto/ui` (`file-upload.tsx:60-63`) para não perder o
      arquivo no celular; estado "preparando" com a copy que diz que pode fechar a janela
- [X] T016 [US1] `app/cli.py`: comando `flask nfc reprocessar [--dry-run] [--id N]` que enfileira as
      entregas existentes, uma a uma, mostrando tamanho de antes e estimativa de depois. É como os
      dez vídeos de produção serão convertidos (FR-018), pelo dono, no Shell do Render

**Checkpoint**: um vídeo 4K enviado pelo ERP volta com 1080 e poucos megabytes; a queixa do print
morre aqui. Cenários 1, 2 e 11 do verify em PASS.

---

## Phase 4: História 2 — A moldura da Manto entra sozinha (P1)

**Objetivo**: a caixinha marcada por padrão grava a moldura no vídeo, na mesma passagem da conversão.

**Verificação da história**: cenários 3 e 4 do `verify_297.py` em PASS.

- [X] T017 [US2] `app/impressoes3d/nfc_ops.py`: `moldura_path()` e `abertura_path()` lendo
      `SiteSetting` (linha única `id=1`), e `salvar_moldura(file)` / `salvar_abertura(file)` com nome
      fixo em `nfc_media/sistema/`, no molde de `logo_path` (`app/admin/config_ops.py:78-88`).
      A moldura recusa arquivo que não seja `.png` e PNG **sem transparência real**
      (`app/imaging.py:111`), porque uma moldura opaca cobriria o vídeo inteiro
- [X] T018 [US2] `app/impressoes3d/nfc_ops.py`: `processar_entrega` passa a gerar **duas** saídas
      quando `has_frame` — o mestre sem moldura em `nfc_media/mestres/` e o entregue com a moldura —
      e uma só quando a caixa vem desmarcada. Sem moldura cadastrada ou sem `ffmpeg`, entrega sem
      moldura e preenche `processing_error` com o motivo, nunca perde o vídeo (FR-006)
- [X] T019 [US2] `app/api/nfc_write.py`: `com_moldura` no multipart do upload, ausente equivalendo a
      `true`; `POST /api/3d/nfc/<tag_id>/entregas/<id>/reprocessar` partindo do mestre, com `409` se
      já estiver na fila; `PUT`/`DELETE` de `/api/3d/nfc/moldura` e `/api/3d/nfc/abertura`. Gate
      `require_3d_access()` no início de cada view e comentário `RBAC:` no topo do módulo —
      contratos em `contracts/nfc-api.md` §5, §6 e §7
- [X] T020 [US2] `frontend/apps/internal/src/components/nfc/VideoDialog.tsx`: a caixinha "Aplicar a
      moldura da Manto", **marcada por padrão**, no padrão local de `<input type="checkbox">` dentro
      de `<label>` (`apps/internal/src/pages/AdminUserEditPage.tsx:356-371`, já que `@manto/ui` não
      tem Checkbox). Precisa ser decidida ANTES de escolher o arquivo, porque a escolha do arquivo já
      dispara o envio
- [X] T021 [P] [US2] `frontend/apps/internal/src/components/nfc/MolduraDialog.tsx` (novo): cadastro
      da moldura e do vídeo de abertura, com prévia da moldura sobre um fundo xadrez que revela a
      transparência, aviso quando a proporção foge de 9:16, e o estado de "nenhuma cadastrada".
      Aberto por um botão no cabeçalho da aba Vídeos

**Checkpoint**: envio com a caixa marcada sai com moldura na borda e miolo intacto; desmarcada, sem
moldura. Cenários 3 e 4 em PASS.

---

## Phase 5: História 3 — O menu da luminária (P2)

**Objetivo**: a página pública vira capa, abertura com som, menu de três botões e mensagem especial.

**Verificação da história**: cenário 5 do `verify_297.py` em PASS e a tela conferida em viewport
mobile 375x812, inclusive com "reduzir movimento" ligado.

- [X] T022 [US3] `app/api/nfc_read.py`: o payload público ganha `spotify_url`, `intro_video_url` e
      `aceita_recado`, presentes **também no shape vazio** para o menu genérico ter os dois botões
      externos; e `GET /api/nfc/abertura/video` servindo o arquivo do sistema com
      `send_file(conditional=True)` e limite de taxa folgado — `contracts/nfc-api.md` §1 e §3
- [X] T023 [P] [US3] `frontend/apps/public/src/lib/nfc.ts`: tipos do payload novo e a memória do
      aparelho — par `leu`/`grava` com `try/catch` que degrada em silêncio, no padrão de
      `apps/public/src/lib/wishlist.ts:33-47`, com chave própria para "já viu a abertura"
- [X] T024 [US3] `frontend/apps/public/src/pages/NfcPage.tsx`: a máquina de cenas — `capa`,
      `abertura`, `menu`, `mensagem` — com `AnimatePresence mode="wait"` e `key` discriminante
      (molde `apps/public/src/components/ProductGallery.tsx:112-154`), reaproveitando o helper
      `enter(delay)` que já existe no arquivo (`:60-67`) e o palco de céu estrelado. A capa aparece
      só na primeira visita do aparelho; sem vídeo de abertura cadastrado, a página abre no menu
- [X] T025 [US3] `frontend/apps/public/src/pages/NfcPage.tsx`: o menu — três botões
      `min-h-[48px]`, no molde do CTA do Instagram que já está lá (`:227-238`), com
      `rel="noopener noreferrer"`, foco visível e a regra de nunca renderizar botão sem destino. O
      botão da mensagem especial só existe quando a tag tem vídeo pronto
- [X] T026 [US3] `frontend/apps/public/src/pages/NfcPage.tsx`: a cena da mensagem — vídeo em
      `aspect-[9/16]` com `object-contain` sobre `bg-ink` (padrão novo no repositório, lição de
      `CharacterCard.tsx:36-38`), palco reservado pelas dimensões que o payload manda, `onError` com
      texto de fallback, e caminho de volta ao menu

**Checkpoint**: a página abre, toca a abertura com som ao toque, mostra o menu e leva à mensagem.
Cenário 5 em PASS.

---

## Phase 6: História 4 — O recado da cliente (P2)

**Objetivo**: a visitante escreve de volta, é agradecida na hora, e o recado chega à equipe.

**Verificação da história**: cenários 6, 7 e 8 do `verify_297.py` em PASS, com 7 e 8 falhando do
lado do servidor.

- [X] T027 [US4] Núcleo puro `app/impressoes3d/nfc_recados_ops.py` (novo):
      `registrar_recado(code, *, message, author_name)` que resolve o código **sem** incrementar
      `access_count`, copia o `client_id` da tag no instante do envio, valida texto vazio e teto de
      1000 caracteres com exceção de campo; `listar_recados(tag_id)`; `marcar_lidos(tag_id)`
- [X] T028 [US4] `app/api/nfc_write.py`: `POST /api/nfc/<code>/recados` público, com
      `@limiter.limit("10 per hour")` (mesmo valor de `cadastro_write.py:50`) e **`201` mesmo para
      código inexistente ou tag desativada**, sem gravar nada — a mesma indistinguibilidade que a
      leitura garante (`contracts/nfc-api.md` §4)
- [X] T029 [P] [US4] `app/__init__.py`: `@app.errorhandler(429)` devolvendo o envelope de
      `json_error` para rotas sob `/api`, ao lado dos handlers de 404/500/403/413 (`:782-801`).
      Hoje o `flask-limiter` devolve HTML cru e o front traduz como "Ocorreu um erro inesperado" nas
      treze rotas públicas que já têm limite — justificativa no Rastreamento de complexidade do plano
- [X] T030 [US4] `app/notificacoes/notificacoes_ops.py`: `KIND_RECADO_NFC = "recado_nfc.novo"` em
      `DESTINATARIOS_POR_KIND` com `(ARTISTA_3D, SUPERADMIN)` — os mesmos papéis que podem ler o
      recado — e o produtor `notificar_recado_nfc(recado)` com `dedupe_key` do id do recado e
      `link_path` para a aba Vídeos. Chamada em regime best-effort: falhar o aviso **não** desfaz o
      recado (molde `app/api/formularios_write.py:73-87`)
- [X] T031 [US4] `app/api/nfc_read.py`: `GET /api/3d/nfc/<tag_id>/recados` e
      `POST /api/3d/nfc/<tag_id>/recados/lidos`, com `require_3d_access()`; e `messages_count` /
      `messages_unread` por tag na lista de gestão, para o card não fazer uma requisição por tag
- [X] T032 [US4] `frontend/apps/public/src/pages/NfcPage.tsx` e `lib/nfc.ts`: o formulário do recado
      dentro da cena da mensagem — texto obrigatório, nome opcional, contador de caracteres, botão
      com estado de envio, erro por campo via `fieldErrorsFrom` (`apps/public/src/lib/virtuais.ts:239-244`)
      e a cena de agradecimento sem sair da página

**Checkpoint**: recado enviado aparece no ERP e toca o sino; recado inválido é recusado com o campo
apontado. Cenários 6, 7 e 8 em PASS.

---

## Phase 7: História 5 — O gerenciador volta a servir para revisar (P3)

**Objetivo**: a aba Vídeos mostra vídeo em pé, estado do processamento e os recados.

**Verificação da história**: cenário 9 do `verify_297.py` em PASS e a tela aberta com os dez cards.

- [X] T033 [US5] `frontend/apps/internal/src/components/nfc/NfcVideoCard.tsx`: vídeo em
      `aspect-[9/16]` no lugar de `aspect-video` (`:35`) — é a causa de o vídeo vertical aparecer
      espremido; selo de estado (`preparando`, `falhou`) com o motivo e botão de tentar de novo;
      peso e duração ao lado da data; selo de recados não lidos
- [X] T034 [US5] `frontend/apps/internal/src/components/nfc/NfcVideosPanel.tsx`: polling ativo
      enquanto houver entrega em fila, KPI novo de "preparando", e a seção de recados da tag
- [X] T035 [P] [US5] `frontend/apps/internal/src/components/nfc/RecadosDaTag.tsx` (novo): lista dos
      recados de uma tag com autor, data e marcação de lido ao abrir

**Checkpoint**: os dez cards tocam, em pé, com peso e duração visíveis. Cenário 9 em PASS.

---

## Phase 8: Polimento e transversais

- [X] T036 `cd frontend && npm run typecheck` limpo nos três SPAs, e `ruff check` limpo nos arquivos
      tocados (`ruff format` só nos três arquivos novos)
- [X] T037 `verify_297.py` em 12/12 contra o `manto_local`
- [X] T038 Telas abertas de verdade no Browser pane: `/3d/tags?aba=videos` conferida com dado real
      (card em pé, moldura gravada visível, peso, duração, selo de recados, "Moldura e abertura"), e
      `/nfc/<code>` em **375x812** com a estrutura, os alvos de toque de 48px e a ausência de rolagem
      horizontal medidos no DOM. **Ressalva**: o Browser pane entrega ~1 quadro de
      `requestAnimationFrame` por 5,8 s, então o Framer Motion fica parado no estado inicial e as
      cenas não avançam ali — o mesmo acontece com a animação da estrela, que é código da feature 255
      e roda em produção. As cenas precisam de uma passada num celular de verdade (`quickstart.md` §3)
- [X] T039 [P] `docs/01_SISTEMA_E_BANCO.md` §4.3: as sete linhas de RBAC dos endpoints novos e
      alterados, no formato das linhas `:986-993`; e §5.3, as subpastas novas do disco
- [X] T040 [P] `docs/02_MAPA_DE_PAGINAS_E_UX.md`: a página `/nfc/<code>` reescrita como máquina de
      cenas (`:892-930`) e a aba Vídeos de `/3d/tags` (`:866-887`)
- [X] T041 [P] `docs/00_MAPA_DO_SISTEMA.md` §6: a pegadinha do vídeo cru de câmera (peso, não codec)
      e a do `ffmpeg` que existe no contêiner mas não está declarado no `render.yaml`
- [X] T042 [P] `docs/05_DIVIDA_TECNICA.md`: dívida nova do `ffmpeg` não declarado; retenção dos
      recados a decidir; e a nota de que o vídeo da Loja Virtual (feature 205) tem o mesmo problema
      de peso e agora tem um `video_ops.py` pronto para resolvê-lo
- [X] T043 `docs/03_HISTORICO_MUTACOES.md`: entrada 297 no topo mais a linha na tabela do índice —
      contexto (o print e o que a investigação achou), o que mudou por arquivo, as cinco decisões do
      dono, as pegadinhas e a verificação
- [X] T044 `quickstart.md` executado de ponta a ponta, incluindo a sonda do arquivo entregue com
      `ffprobe` para confirmar 1080 de largura e o peso alvo

---

## Dependências e ordem

- Setup → Foundational (bloqueia tudo) → US1 → US2 → US3 → US4 → US5 → Polimento
- **US2 depende de US1**: a moldura entra dentro da conversão que US1 constrói.
- **US4 depende de US3**: o recado mora dentro da cena da mensagem especial.
- **US5 depende de US1**: o estado do processamento só existe depois da fila.
- **US3 é independente de US1 e US2** no código, e pode ser feita em paralelo por outra pessoa; ela
  só precisa das colunas da fase Foundational.
- Dentro de cada história: `_ops` antes do endpoint; endpoint antes da tela; verify em PASS ao fim.
- O verify (T007) é escrito ANTES de qualquer núcleo de negócio e falha primeiro.

## Paralelismo possível

| Podem andar juntas | Por quê |
|---|---|
| T001 e T002 | Arquivos diferentes, sem dependência |
| T013, T014 e as tarefas de backend da US1 | `frontend/server.js` e `lib/nfc.ts` não tocam Python |
| T021 e T020 | Diálogo novo × diálogo existente |
| T023 e T022 | Frontend público × backend |
| T029 e T027 | O handler de 429 é global e independente do núcleo do recado |
| T035 e T033/T034 | Componente novo × componentes existentes |
| T039 a T042 | Quatro documentos diferentes |

## Estratégia

- **MVP**: Setup + Foundational + US1. Nesse ponto a queixa do dono já está resolvida: os vídeos
  tocam para a cliente e no gerenciador. É um candidato legítimo a merge sozinho.
- **Segunda entrega**: US2, que é o pedido principal e sai barato depois de US1.
- **Terceira**: US3 e US4 juntas, porque o recado sem o menu não tem onde morar.
- **Quarta**: US5, polimento da tela de revisão.
- Commit por tarefa ou grupo lógico, `feat(297):`, sempre `git add` por caminho. O merge é um só, no
  fim, quando o dono pedir — publicar é sempre decisão dele.

---

## Phase 9: Convergence

Achados de `/speckit-converge` em 09/09/2026. Nenhum é CRITICAL e nenhum contradiz a constituição:
a implementação satisfaz os 19 requisitos funcionais e as decisões do plano. O que sobra é
**cobertura de verificação** para o que hoje só foi comprovado à mão, uma conferência visual que
esta máquina não conseguiu fazer, e uma função que ficou sem uso.

- [ ] T045 Percorrer `/nfc/<code>` num navegador que ANIME — capa, abertura com som, menu, mensagem,
      envio de recado, agradecimento, volta ao menu e segunda visita — mais a variante com "reduzir
      movimento" ligado, em viewport de celular, per FR-008 · FR-017 · Constituição X e XI (partial).
      Por que ficou de fora: o Browser pane desta sessão está recolhido e entrega ~1 quadro de
      `requestAnimationFrame` por 5,8 s, então o Framer Motion fica parado no estado inicial e o
      `AnimatePresence mode="wait"` nunca troca de cena; o Claude in Chrome não está conectado. O
      controle é a própria estrela que acende, código da feature 255 que roda em produção e aqui
      também congela. Roteiro em `quickstart.md` §3
- [ ] T046 Cenário novo no `verify_297.py`: com `RATELIMIT_ENABLED` LIGADO, o 11º recado da mesma
      origem devolve `429` **no envelope JSON** com mensagem em pt-BR, per FR-013 (partial). Hoje o
      verify desliga o limitador para poder repetir envios, e o comportamento só foi comprovado por
      sondagem manual
- [ ] T047 Cenário novo no `verify_297.py`: sem moldura cadastrada (`nfc_frame_path = NULL`), o
      envio com a caixinha marcada entrega o vídeo **sem moldura**, com `has_frame = false` e o
      motivo em `processing_error`, per FR-006 (partial)
- [ ] T048 Cenário novo no `verify_297.py`: `POST .../reprocessar` devolve a entrega a `pendente` e
      uma segunda chamada é recusada com `409`; depois de processar, o vídeo parte do MESTRE,
      per FR-007 (partial)
- [ ] T049 Depois do deploy, rodar `flask nfc-reprocessar --execute` no Shell do Render (fora do
      horário, `--dry-run` antes) e registrar em `docs/03` os números reais de antes e depois,
      per SC-002 · SC-007 · FR-018 (missing). É ação do dono; o comando já está testado localmente
- [ ] T050 Remover `_remove_delivery_file` de `app/impressoes3d/nfc_ops.py` — ficou sem nenhum uso
      quando `remove_delivery` passou a apagar os três arquivos da entrega (unrequested)
