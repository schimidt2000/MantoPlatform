---
description: "Tasks da feature 328 — Conversas em equipe"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: 328 — Conversas em equipe (responsável, alerta, notas, respostas rápidas, áudio)

**Input**: artefatos em `specs/328-crm-equipe-na-caixa/`

**Pré-requisitos**: plan.md, spec.md (5 histórias e a tabela "Verificação"), research.md (R1–R9),
data-model.md, contracts/api.md

**Verificação (OBRIGATÓRIA — constituição, Princípio VIII)**: `specs/328-crm-equipe-na-caixa/verify_328.py`
contra o `manto_local`, no molde do `specs/325-crm-whatsapp-fundacao/verify_325.py`:
- disjuntor de rede e dublê da Meta;
- conferência por conexão separada;
- login só por `POST /api/auth/login`;
- requisições fora de `app.app_context()`;
- limpeza no `finally`.

Ele é escrito na fase Foundational (T008), antes do núcleo, e nasce falhando nos cenários ainda não construídos.

**Base**: worktree `C:\tmp\mp328`, branch `328-crm-equipe-na-caixa` sobre a `325-crm-whatsapp-fundacao` (fora da
`main`). Sem merge e sem push: o dono adiou a publicação.

## Formato: `[ID] [P?] [Story] Descrição`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: US1 (responsável), US2 (alerta), US3 (notas), US4 (respostas rápidas), US5 (áudio)

## Regra de dependência entre módulos (vale para todas as fases)

`equipe_ops` é a camada de baixo: importa `models`, `constantes`, `acesso`, `relogio`, `recusa`,
`notificacoes_ops` e `leitura_ops` (que não importa `equipe_ops`). **Nunca** importa `aviso_ops` nem `envio_ops`,
porque são eles que o importam (um import de volta fecha um ciclo). *Corrigido na convergência (T064).* O relógio UTC sai de `aviso_ops` para `app/conversas/relogio.py` (T002) por
esse motivo, e a exceção de recusa sai de `envio_ops` para `app/conversas/recusa.py` (T003).

---

## Phase 1: Setup

- [X] T001 Constantes da 328 em `app/conversas/constantes.py`:
  - tempos e horário: `ESPERA_PARA_ALERTA = timedelta(minutes=15)`, `HORARIO_DE_ALERTA = (9, 21)` (hora de São
    Paulo, intervalo `[9, 21)`);
  - filtros e ações: `FILTROS_DA_LISTA = ("todas", "minhas", "sem_responsavel")`,
    `ACOES_DO_RESPONSAVEL = ("assumir", "transferir", "devolver")`;
  - limites:
    - `NOTA_MAXIMA = 2000`, `NOTAS_NO_DETALHE = 200`;
    - `RESPOSTA_TITULO_MAXIMO = 80`, `RESPOSTA_ATALHO_MAXIMO = 30`, `RESPOSTA_TEXTO_MAXIMO = TEXTO_MAXIMO`;
    - `CONVERSAO_DE_AUDIO_SEGUNDOS = 60`;
  - os textos de recusa e de aviso do `contracts/api.md`, com o glossário do XV:
    - responsável: `TEXTO_JA_ASSUMIDA` ("Esta conversa já foi assumida por {nome}."), `TEXTO_ALTERADA`,
      `TEXTO_DESTINO_INVALIDO`;
    - notas e respostas rápidas: `TEXTO_NOTA_VAZIA`, `TEXTO_NOTA_LONGA`, os seis das respostas rápidas;
    - áudio: `TEXTO_AUDIO_FALHOU` ("Não foi possível preparar o áudio. Envie o arquivo pelo clipe.");
    - avisos: `TITULO_ESPERANDO` ("{nome} espera resposta há {minutos} min."), `TITULO_TRANSFERIDA`
      ("{quem} transferiu a conversa com {nome} para você.").
- [X] T002 [P] `app/conversas/relogio.py` com `agora_utc()` (movida de `app/conversas/aviso_ops.py`, que passa a
  importá-la de lá). Os importadores da 325 (`envio_ops`, `varredura`, `verify_325`) continuam funcionando por
  `aviso_ops.agora_utc`. Conferir com `Grep "agora_utc"`.
- [X] T003 [P] `app/conversas/recusa.py` com `Recusa(codigo, mensagem, status, fields=None)` e o atalho
  `campo(nome, mensagem)` (422 `invalido`). Em `app/conversas/envio_ops.py`, `EnvioRecusado` passa a herdar de
  `Recusa` sem mudar a assinatura, e o `_campo` local usa `campo`.
- [X] T004 [P] `app/impressoes3d/video_ops.py`: `caminho_do_ffmpeg() -> str | None` público (embrulha
  `_caminho_binario("ffmpeg")`, aditivo, com docstring de que o áudio das Conversas não exige ffprobe).
- [X] T005 [P] `app/notificacoes/notificacoes_ops.py`:
  - `KIND_CONVERSA_ESPERANDO = "conversa.esperando"` e `KIND_CONVERSA_TRANSFERIDA = "conversa.transferida"` no
    catálogo, com `DESTINATARIOS_POR_KIND` `(COMERCIAL, SUPERADMIN)` para o primeiro e `()` para o segundo
    (destinatário sempre explícito);
  - `apagar_por_entidade(entity_type, entity_id, kind=None)`: com `kind`, apaga só os avisos daquele tipo
    (aditivo, mesmo padrão de `marcar_lidas_por_entidade`). Encerrar a espera não pode apagar o aviso de
    transferência.

---

## Phase 2: Foundational (bloqueia as histórias)

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

- [X] T006 Modelos em `app/models.py` conforme `data-model.md`:
  - `Conversa` ganha:
    - `responsavel_id` (FK `users.id`, `ondelete="SET NULL"`, index);
    - `assumida_em`;
    - `aguardando_desde` (index);
    - a relação `responsavel` (`foreign_keys` explícito).
  - `ConversaNota` (`conversa_notas`) com a relação `autor` e `Conversa.notas` (`cascade="all, delete-orphan"`,
    `passive_deletes=True`).
  - `RespostaRapida` (`respostas_rapidas`).
  - Docstring com o porquê de cada coluna.
- [X] T007 Migration **manual** `migrations/versions/f328b2d4e6a1_conversas_equipe.py`:
  - `down_revision = "e325a7c1d9f2"`;
  - FKs nomeadas;
  - índice único funcional `uq_respostas_rapidas_titulo` em `lower(titulo)` e único `uq_respostas_rapidas_atalho`;
  - downgrade completo.

  Aplicar no `manto_local` com `.venv\Scripts\flask.exe db upgrade` (`FLASK_APP=run.py`, `MANTO_SEM_THREADS=1`)
  e conferir `flask db heads` com um head só.
- [X] T008 **`specs/328-crm-equipe-na-caixa/verify_328.py`** com os 20 cenários da tabela "Verificação" da spec.
  - **Molde:** o `verify_325.py` (disjuntor de rede, dublê da Meta que registra os corpos enviados, avisos
    assinados para recebida e eco).
  - **Usuários descartáveis:** Ana e Bia (COMERCIAL) e Cris (CASTING), com prefixo único; login pela API, um
    `test_client(use_cookies=False)` por pessoa.
  - **Conferência:** por conexão separada (`psycopg`), lendo `conversas.responsavel_id`, `aguardando_desde` e as
    linhas de `notifications`.
  - **Relógio:** os cenários de horário (7–10) chamam `equipe_ops.alertar_esperas(agora_sp=...)` com o horário
    injetado (14h e 22h30, e 9h do dia seguinte).
  - **Áudio:** o cenário 17 gera um webm/opus de 1 s com o ffmpeg local (`-f lavfi -i sine` + `-c:a libopus`;
    sem `libopus`, o encoder nativo `-c:a opus -strict -2`) e pula com motivo quando não houver ffmpeg. O 18 troca `video_ops.caminho_do_ffmpeg` por um dublê que devolve
    `None`.
  - **Flags:** `--manter` deixa os dados para a conferência da tela.

  Roda agora e **falha** nos cenários ainda não construídos.

**Checkpoint**: migration aplicada, constantes e primitivas prontas, verify falhando pelos motivos certos.

---

## Phase 3: História 1 — Fila livre e responsável (P1) 🎯 MVP

**Objetivo**: quem responde primeiro vira o responsável. Dá para assumir, transferir e devolver, e a lista filtra
por responsável.

**Verificação da história**: cenários 1–6, 16 e 19 do `verify_328.py`; tela aberta.

- [X] T009 [US1] Primitivas da equipe em `app/conversas/equipe_ops.py` (arquivo novo). *Feito:* `e_da_equipe`
  e `responsavel_ativo` foram para `app/conversas/acesso.py`, e `serializar_pessoa` para `leitura_ops`,
  porque `leitura_ops` serializa o responsável e não pode importar `equipe_ops` (ciclo):
  - `membros_da_equipe() -> list[User]`: ativos, com acesso e papel COMERCIAL ou SUPERADMIN, por nome. Reusa
    `notificacoes_ops.resolver_destinatarios`.
  - `e_da_equipe(user) -> bool`.
  - `responsavel_ativo(conversa) -> bool`.
  - `serializar_pessoa(user) -> {id, nome} | None`.
- [X] T010 [US1] `equipe_ops.resposta_da_equipe(conversa, autor_id, momento)`, chamada quando a Meta **aceita**
  um envio da Plataforma (R1). Faz `UPDATE conversas SET responsavel_id = :autor, assumida_em = :momento WHERE
  id = :id AND responsavel_id IS NULL` e sincroniza o objeto da sessão. Não comita: o `_despachar` comita.
- [X] T011 [US1] Em `app/conversas/envio_ops.py`, `_despachar` chama `equipe_ops.resposta_da_equipe` só no ramo
  de sucesso (`situacao = enviada`) e com `mensagem.autor_id` presente. O ramo `falhou` não toca o responsável
  (cenário 19).
- [X] T012 [US1] `equipe_ops.definir_responsavel(conversa_id, acao, quem, responsavel_id=None) -> Conversa`, que
  comita (R2):
  - lê o atual, decide e grava com `WHERE responsavel_id IS NOT DISTINCT FROM :atual`;
  - `rowcount == 0` na transferência ou na devolução → `Recusa("alterada", TEXTO_ALTERADA, 409)`;
  - `assumir`: só com responsável nulo ou `not responsavel_ativo(conversa)` (T009: ativo, com acesso e papel de
    conversas); senão `Recusa("ja_assumida", …, 409)` com o nome. Na corrida (`rowcount == 0`), relê a conversa
    e devolve o mesmo `ja_assumida` com o nome de quem ganhou (US1, aceite 3);
  - `transferir`: destino da equipe, senão 422 `fields.responsavel_id`; transferir para quem já é o responsável
    não muda nada e devolve 200;
  - `devolver`: grava nulo;
  - ação fora de `ACOES_DO_RESPONSAVEL` → 422 `fields.acao`; conversa inexistente → 404 `nao_encontrada`.

  Funções de no máximo ~30 linhas: um auxiliar por ação.
- [X] T013 [US1] FR-018 em `equipe_ops._avisar_transferencia(conversa, quem, destino)`:
  - `notificacoes_ops.emitir(KIND_CONVERSA_TRANSFERIDA, destinatarios=[destino], …)`, só quando `destino != quem`;
  - `dedupe_key = f"conversa.transferida:{id}:{epoch de assumida_em}"`, `entidade = ("conversa", id)`;
  - `link_path = f"/conversas?c={id}"`, severidade `info`;
  - na mesma transação do `definir_responsavel` (regime A da 272).
- [X] T014 [US1] `app/conversas/leitura_ops.py`:
  - `serializar_conversa` ganha `responsavel` e `responsavel_ativo`;
  - `listar_conversas(busca, antes, filtro="todas", usuario_id=None)`: `minhas` filtra `responsavel_id =
    usuario_id`; `sem_responsavel` filtra `responsavel_id IS NULL`;
  - `joinedload(Conversa.responsavel)` para não haver N+1.
- [X] T015 [US1] `app/api/conversas_read.py`:
  - `GET /api/conversas` lê `filtro` (fora de `FILTROS_DA_LISTA` → 422 `fields.filtro`) e passa
    `current_user.id`;
  - novo `GET /api/conversas/equipe` → `{"equipe": [...]}`, com o gate `pode_conversas` no início.
- [X] T016 [US1] `app/api/conversas_equipe_write.py` (arquivo novo):
  - comentário `RBAC:` no topo, `_negado()` e `_recusa(exc: Recusa)` (envelope `json_error` com `codigo` e
    `fields`);
  - `POST /api/conversas/<int:conversa_id>/responsavel` → 200 `{"conversa": serializar_conversa(...)}`.

  Registrar em `app/api/__init__.py` (import com `# noqa: E402,F401`, ao lado de `conversas_write`).
- [X] T017 [P] [US1] `frontend/apps/internal/src/lib/conversas.ts`:
  - tipos: `Pessoa`, `FiltroDaLista`, `AcaoDoResponsavel`; campos opcionais novos em `ConversaResumo` (armadilha
    21);
  - hooks: `useConversas(busca, filtro)` com o filtro na `queryKey`, `useEquipe()`, `useDefinirResponsavel(id)`
    (invalida a lista e a conversa) e `codigoDaRecusa` reaproveitado.
- [X] T018 [US1] Lista com filtro e responsável:
  - `frontend/apps/internal/src/components/conversas/FiltroDaLista.tsx` (novo): botões de alternância "Todas",
    "Minhas" e "Sem responsável", com `aria-pressed` e alvo ≥ 44 px no celular;
  - `ListaDeConversas.tsx`: linha "Responsável: Ana" ou "Sem responsável" em cada item;
  - `pages/ConversasPage.tsx`: `?filtro=` no endereço, ao lado de `?c=` e `?busca=`.
- [X] T019 [US1] Menu e transferência. *Feito:* botões diretos ("Assumir", "Transferir…", "Devolver à fila") em vez
  de menu, um toque por ação; no celular, o nome de quem atende ganha linha própria:
  - `components/conversas/ResponsavelDaConversa.tsx` (novo): cabeçalho "Responsável: …" e o menu "Assumir",
    "Transferir…" e "Devolver à fila", com `loading` e toast no 409 (texto do servidor), e motion com
    `useReducedMotion`;
  - `components/conversas/TransferirDialog.tsx` (novo): `Combobox` do `@manto/ui` com a equipe e o erro do campo
    `responsavel_id`;
  - encaixar no cabeçalho de `ConversaAberta.tsx`.

**Checkpoint**: cenários 1–6, 16 e 19 em PASS; a fila funciona sozinha.

---

## Phase 4: História 2 — Alerta de cliente esperando (P1)

**Objetivo**: a espera de 15 min, entre 9h e 21h, vira um aviso único no sino, que some quando alguém responde.

**Verificação da história**: cenários 6–11 e 19; a lista mostra a espera.

- [X] T020 [US2] `equipe_ops`: abrir, encerrar e recalcular a espera.
  - `abrir_espera(conversa, momento)`: só se `aguardando_desde` for nulo.
  - `encerrar_espera(conversa)`: zera e chama `notificacoes_ops.apagar_por_entidade("conversa", id,
    kind=KIND_CONVERSA_ESPERANDO)` (FR-008).
  - `recalcular_espera(conversa)`: a primeira recebida depois da última resposta válida (enviada que não falhou,
    e eco que não é `revoke`/`edit`), ou nulo. Serve para o status `failed` que chega depois do aceite (caso de
    borda "Resposta que falhou").
  - `resposta_da_equipe` (T010) passa a chamar `encerrar_espera`.
- [X] T021 [US2] `app/conversas/aviso_ops.py`:
  - `_gravar_recebida` chama `equipe_ops.abrir_espera(conversa, momento)` só quando a mensagem é nova;
  - `_gravar_eco` chama `equipe_ops.encerrar_espera(conversa)` só para eco novo que não é `revoke`/`edit`, e não
    atribui responsável (cenário 6);
  - `_aplicar_status` chama `equipe_ops.recalcular_espera(mensagem.conversa)` ao marcar `falhou` uma enviada que
    estava `enviada`.
- [X] T022 [US2] `equipe_ops.alertar_esperas(agora_sp=None) -> dict[str, int]` (R4):
  - fora de `HORARIO_DE_ALERTA` em São Paulo (`now_sp()`), devolve `{"alertas": 0}`;
  - dentro do horário:
    - seleciona as conversas com `agora_utc - JANELA < aguardando_desde <= agora_utc - ESPERA_PARA_ALERTA`, das
      mais antigas para as mais novas, até `VARREDURA_LOTE`. Uma espera com a janela de 24 h fechada não se
      responde com texto e não entra em toda passada para sempre;
    - emite `KIND_CONVERSA_ESPERANDO` com `dedupe_key = f"conversa.esperando:{id}:{epoch}"`, `entidade`, link,
      severidade `urgent` e corpo = `ultima_previa`;
    - destinatário: `[responsavel]` quando `responsavel_ativo`; senão `None` (equipe pelo catálogo);
  - comita a rodada.

  O `agora_sp` injetável é o que o verify usa. A conversão SP → UTC usa o fuso de `app.constants` (armadilha 3).
- [X] T023 [US2] `app/conversas/varredura.py`: `ciclo_de_varredura` inclui `equipe_ops.alertar_esperas` na tupla
  de rotinas (isolada como as outras).
- [X] T024 [US2] `leitura_ops.serializar_conversa` ganha `aguardando_desde` (ISO `+00:00`).
- [X] T025 [P] [US2] Espera na lista:
  - `ListaDeConversas.tsx`: "Esperando há N min" (e "há N h" acima de 60), em vermelho a partir de 15 min,
    recalculado a cada minuto sem nova requisição;
  - tipo em `lib/conversas.ts`; helper `tempoDeEspera` em `lib/conversas.ts`.

**Checkpoint**: cenários 6–11 e 19 em PASS.

---

## Phase 5: História 3 — Notas internas (P2)

**Objetivo**: a nota que nunca sai para a cliente, na linha do tempo, com autor.

**Verificação da história**: cenários 12 e 13.

- [X] T026 [US3] `equipe_ops`: as notas.
  - `gravar_nota(conversa_id, texto, autor_id) -> ConversaNota` comita:
    - texto aparado;
    - vazio → 422 `fields.texto`;
    - acima de `NOTA_MAXIMA` → 422 `fields.texto`;
    - conversa inexistente → 404.
  - `notas_da_conversa(conversa_id)`: as `NOTAS_NO_DETALHE` mais recentes, em ordem cronológica, com o autor.
  - `serializar_nota(nota)`.
- [X] T027 [US3] Endpoints:
  - `app/api/conversas_read.py`: o detalhe devolve `notas` no topo do JSON;
  - `app/api/conversas_equipe_write.py`: `POST /api/conversas/<int:conversa_id>/notas` → 201 `{"nota": …}`.
- [X] T028 [P] [US3] `lib/conversas.ts`: tipo `Nota`, `notas` no detalhe e o hook `useGravarNota(id)` (invalida
  o detalhe).
- [X] T029 [US3] Nota na conversa:
  - `components/conversas/NotaInterna.tsx` (novo): balão dourado claro, "Nota interna · Ana · 14:32",
    alinhado ao centro, com a entrada da nota nova por motion com `useReducedMotion`;
  - `ConversaAberta.tsx` intercala notas e mensagens por horário;
  - `CaixaDeEnvio.tsx` ganha a alternância "Mensagem | Nota interna" (alvo ≥ 44 px). Na nota, o campo vale com a
    janela fechada, sem anexo nem modelo, e o botão diz "Gravar nota". O 422 `fields.texto` aparece no
    campo.

**Checkpoint**: cenários 12 e 13 em PASS.

---

## Phase 6: História 4 — Respostas rápidas (P2)

**Objetivo**: a lista de textos prontos da equipe, inserida no campo sem enviar.

**Verificação da história**: cenários 14–16.

- [X] T030 [US4] `app/conversas/respostas_ops.py` (novo):
  - funções: `listar()` (por `lower(titulo)`), `criar(dados, autor_id)`, `alterar(id, dados, autor_id)`,
    `excluir(id)` e `serializar(resposta)`;
  - validação por campo:
    - título obrigatório, até 80 caracteres e único sem distinguir caixa;
    - atalho opcional: `/` inicial removido, minúsculas, sem espaço, até 30 caracteres e único;
    - texto obrigatório, até 4.096 caracteres;
  - recusa → `Recusa` 422 com `fields`; o `IntegrityError` do índice vira a mesma recusa (corrida);
  - inexistente → 404.
- [X] T031 [US4] Em `app/api/conversas_equipe_write.py`: `GET` e `POST /api/conversas/respostas-rapidas`,
  `PATCH` e `DELETE /api/conversas/respostas-rapidas/<int:resposta_id>` (204), com o gate no início de cada view.
- [X] T032 [P] [US4] `lib/conversas.ts`:
  - tipo `RespostaRapida`;
  - hooks `useRespostasRapidas()`, `useCriarResposta()`, `useAlterarResposta()` e `useExcluirResposta()`;
  - `aplicarNome(texto, nome)`: o primeiro nome; sem nome, tira o marcador e a vírgula que sobra ("Olá, {nome}!"
    vira "Olá!").
- [X] T033 [US4] Lista e inserção:
  - `components/conversas/RespostasRapidas.tsx` (novo):
    - o botão abre a lista com busca por título ou atalho;
    - "/" no começo do campo abre a mesma lista já filtrada;
    - teclado ↑ ↓ Enter Esc;
    - no celular, abre na largura da tela;
  - escolher **insere** no campo do `CaixaDeEnvio.tsx`, sem enviar (FR-011).
- [X] T034 [US4] `components/conversas/GerenciarRespostasDialog.tsx` (novo):
  - lista, criar e editar, com o erro do servidor apontado no campo;
  - excluir com `ConfirmDialog` ("Excluir esta resposta?");
  - aberto por "Gerenciar respostas rápidas" no fim da lista.

**Checkpoint**: cenários 14–16 em PASS.

---

## Phase 7: História 5 — Gravar áudio no navegador (P2)

**Objetivo**: o áudio gravado chega como nota de voz, com o webm do Chrome convertido para ogg.

**Verificação da história**: cenários 17 e 18; a tela com o microfone (negado no Browser pane).

- [X] T035 [US5] `app/conversas/midia_ops.py`: `webm_para_ogg(dados: bytes) -> bytes` (R7).
  - Usa `video_ops.caminho_do_ffmpeg()`, com arquivos temporários de entrada e saída.
  - Roda `ffmpeg -hide_banner -v error -y -i in.webm -vn -c:a copy -f ogg out.ogg`, com timeout
    `CONVERSAO_DE_AUDIO_SEGUNDOS`, e apaga os temporários no `finally`.
  - Sem ffmpeg, código ≠ 0, saída vazia ou timeout: `AudioIndisponivel`.
- [X] T036 [US5] `app/conversas/envio_ops.py`, em `enviar_arquivo`:
  - quando o MIME limpo é `audio/webm`:
    - converte depois de `_pre_condicoes` (configuração, trava e janela), para não rodar o ffmpeg num envio que
      vai ser recusado, e antes de `_tipo_do_arquivo`;
    - troca o MIME para `audio/ogg` e o nome para `….ogg`;
    - com `AudioIndisponivel`, devolve `campo("arquivo", TEXTO_AUDIO_FALHOU)`, e nada é gravado nem enviado;
  - em `_subir_e_despachar`, `bloco["voice"] = True` para áudio `audio/ogg` (FR-014);
  - o `audio/webm` **não** entra em `MIME_DE_ENVIO`: só é aceito pela conversão.
- [X] T037 [US5] `components/conversas/GravadorDeAudio.tsx` (novo):
  - MediaRecorder com o primeiro MIME suportado: `audio/ogg;codecs=opus`, depois `audio/webm;codecs=opus`, depois
    `audio/mp4`;
  - tempo correndo (`m:ss`), "Cancelar" e "Enviar";
  - parada automática em 5 min;
  - libera as faixas do microfone ao parar;
  - sem permissão ou sem microfone: o texto do FR-012;
  - alvo ≥ 44 px e motion com `useReducedMotion`.
- [X] T038 [US5] `CaixaDeEnvio.tsx`:
  - o microfone ("Gravar áudio") aparece no lugar de "Enviar" quando o campo está vazio e a janela está aberta;
  - o áudio sai por `useEnviarArquivo`, com nome `audio-AAAAMMDD-HHMMSS.<ext>` e chave nova.

**Checkpoint**: cenários 17 e 18 em PASS (o 17 pula com motivo só sem ffmpeg).

---

## Phase 8: Polimento e portões

- [X] T039 `ruff check` nos arquivos Python tocados; `ruff format` só nos novos (`equipe_ops.py`,
  `respostas_ops.py`, `relogio.py`, `recusa.py`, `conversas_equipe_write.py`, a migration e o verify).
- [X] T040 `cd frontend && npm run typecheck` limpo (três SPAs).
- [X] T041 Os 20 cenários do `verify_328.py` em PASS, e `verify_325.py` ainda verde (regressão da fundação). Os
  dois com `MANTO_SEM_THREADS=1` e `PYTHONUTF8=1`.
- [X] T042 Tela aberta de verdade pela worktree (backend 5328 e Vite 5329 com `run_in_background`, e
  `preview_start {url}`), em desktop e 375×812:
  - filtros e espera;
  - assumir, transferir e devolver;
  - nota;
  - respostas rápidas (inserir e gerenciar);
  - microfone (mensagem de negado);
  - sem rolagem lateral de 320 a 430 px (FR-017).
- [X] T043 Textos novos revisados pelo Princípio XV na tela aberta, junto dos vizinhos.
- [X] T044 Docs por fonte única:
  - `docs/01`:
    - §2.7: colunas e tabelas;
    - §3.13.7: endpoints;
    - §4.3: linhas de RBAC;
    - notificações: os dois kinds novos;
  - `docs/02`: tela `/conversas`;
  - `docs/03`: entrada 328 no topo, **NÃO PUBLICADO**, e linha no índice;
  - `docs/04` §6: invariantes de responsável e espera;
  - `docs/05`: dívida criada ou quitada;
  - `docs/PLANO_CRM_PROPRIO.md`: Fase 2a.
- [X] T045 `quickstart.md` executado e gates CHK001–CHK011 de `checklists/equipe-alerta-ux.md` marcados
  (CHK006 e CHK011 como "não se aplica" e "não publicado").

---

## Dependências e ordem

- Setup (T001–T005) → Foundational (T006–T008) → US1 → US2 → US3 → US4 → US5 → Polimento.
- **US2 depende da US1:**
  - `resposta_da_equipe` (T010) é o ponto em que a espera termina (T020);
  - o destinatário do alerta usa `responsavel_ativo` (T009).
- **US3, US4 e US5 são independentes entre si** e só dependem da Foundational:
  - US3 e US4 tocam `conversas_equipe_write.py` e `CaixaDeEnvio.tsx` (sequenciar as edições nesses dois
    arquivos);
  - US5 toca `envio_ops.py` e `CaixaDeEnvio.tsx`.
- Dentro de cada história: `_ops`, depois o endpoint, depois a tela; o verify da história em PASS fecha a fase.

## Paralelismo

- Setup: T002, T003, T004 e T005 em paralelo (arquivos diferentes); T001 antes deles, que usam as constantes.
- US1: T017 (tipos e hooks) em paralelo com T012–T016 (backend).
- US2: T025 em paralelo com T020–T024.
- US3, US4: T028 e T032 (tipos) em paralelo com o backend da própria história.
- Implementação sem subagente (CLAUDE.md §8): o paralelismo marcado é de ordem, não de delegação.

## Estratégia

- **MVP**: Setup + Foundational + US1 + US2 (as duas P1). É a fila livre com o alerta, o que tira a cliente do
  "sem resposta". Fecha com o verify (cenários 1–11, 16 e 19) e a tela.
- **Incremental**: US3 → US4 → US5, cada uma com os seus cenários em PASS.
- **Commits** por grupo lógico (`feat(328): …`), sempre por caminho, mensagem por arquivo (`git commit -F`).
  Sem merge e sem push até o dono pedir (lote 325 → 328).

---

## Phase 9: Convergence

Revisão independente, só de leitura, em 03/11: 21 achados. O F21 (docs e quickstart) já é o T044/T045.

- [X] T046 CRITICAL: no `CaixaDeEnvio.tsx`, o áudio gravado guarda a chave de envio em `chaveDoRascunho` e, quando o envio falha, a reusa no "Enviar" (sem `mudouORascunho`) — a resposta perdida num 502 não pode virar nota de voz duplicada per Constitution V (contradicts)
- [X] T047 CRITICAL: "Tentar novamente" de `RespostasRapidas.tsx` recebe `isFetching` e mostra `loading` per Constitution V (contradicts)
- [X] T048 Com a lista aberta pela "/" (`painel === "barra"`), o Enter no campo nunca envia, mesmo com a lista vazia ou carregando (`CaixaDeEnvio.tsx`/`teclaNaLista`) per FR-011 (contradicts)
- [X] T049 `alertar_esperas` ignora a conversa que já tem aviso `conversa.esperando` (NOT EXISTS pela entidade e o kind): espera sem resposta não ocupa o lote para sempre; corrigir o texto da dívida 185 em `docs/05` per FR-007/SC-002 (partial)
- [X] T050 Abrir e encerrar a espera respeitando a ordem das mensagens: `abrir_espera` não abre com recebida mais antiga que a última resposta válida, e `encerrar_espera` (envio aceito e eco) só zera se a resposta for mais nova que o início (UPDATE condicional por `momento`) per FR-006/research R3 (partial)
- [X] T051 Reação (recebida ou eco) não abre nem encerra a espera (`aviso_ops._gravar_recebida`, `_gravar_eco`) per US2 (partial)
- [X] T052 `recalcular_espera` conta o eco sem texto (áudio, foto, figurinha) como resposta (`texto IS NULL OR …`) per caso de borda "Resposta que falhou" (partial)
- [X] T053 Cenário no `verify_328.py`: corrida do "Assumir" (objeto lido antes de outra pessoa gravar) → 409 `ja_assumida` com o nome de quem ganhou per US1/AC3 (missing)
- [X] T054 Cenário no `verify_328.py`: responsável que perdeu o acesso → qualquer um assume, e o alerta da espera vai para a equipe per caso de borda "Responsável sem papel"/FR-007 (missing)
- [X] T055 `verify_328.py`: ffmpeg por `video_ops.caminho_do_ffmpeg()` dentro do app, e o cenário 17 pulado não conta como OK (o total diz que pulou e o verify sai com erro) per Constitution VIII (partial)
- [X] T056 Textos pelo XV: "Nada foi gravado. Tente de novo." → sem "nada"/"de novo"; "achar" → "encontrar"; estados vazios no padrão "Nenhum/Nenhuma X …" (`GerenciarRespostasDialog`, `TransferirDialog`, `ListaDeConversas`) per FR-016/Constitution XV (contradicts)
- [X] T057 O título do aviso de espera passa a horas acima de 60 min ("há 12 h"), como a lista per XV/contrato `TITULO_ESPERANDO` (partial)
- [X] T058 `aplicarNome` sem nome só limpa a pontuação junto do marcador ("{nome}, tudo bem?" → "Tudo bem?" sem mexer no resto do texto) per caso de borda `{nome}` (partial)
- [X] T059 `GravadorDeAudio.tsx`: falha do `new MediaRecorder` solta o microfone e avisa; segundo clique durante o pedido de permissão não abre outro fluxo per T037 (partial)
- [X] T060 Foco no primeiro campo inválido na recusa do `GerenciarRespostasDialog` (com `aria-describedby`) e no `Combobox` do `TransferirDialog` per Constitution V (partial)
- [X] T061 `voice: true` só para o áudio gravado na Plataforma (o convertido do webm e o ogg do gravador), não para qualquer ogg do clipe per FR-014 (partial)
- [X] T062 Docstrings em `respostas_ops.serializar` e nas views de respostas rápidas; textos "outra pessoa" e "Conversa não encontrada." em `constantes`; `CaixaDeMensagem` dividida (anexo/linha de envio) per Constitution II (contradicts)
- [X] T063 Verify barato do que faltou: Casting no PATCH/DELETE de resposta, fronteira das 21h, limite de 24 h, várias recebidas seguidas, webm corrompido com ffmpeg, título/atalho/texto acima do limite, atribuição por arquivo, limpeza conferindo notas/respostas/avisos per tabela "Verificação" (missing)
- [X] T064 Corrigir a regra de dependência do `tasks.md` (`equipe_ops` importa `leitura_ops`, que não importa `equipe_ops`) per tasks.md "Regra de dependência" (contradicts)
- [X] T065 `min-w-0` no campo da nota (`NotaInterna.tsx`) per FR-017 (partial)
