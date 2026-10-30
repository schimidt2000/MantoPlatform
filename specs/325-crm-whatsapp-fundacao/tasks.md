---
description: "Tasks da feature 325 — Conversas (WhatsApp na Plataforma)"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: 325 — Conversas (WhatsApp na Plataforma)

**Input**: artefatos em `/specs/325-crm-whatsapp-fundacao/`

**Pré-requisitos**: plan.md, spec.md (histórias e "Verificação"), research.md, data-model.md,
contracts/api.md

**Verificação (OBRIGATÓRIA — Princípio VIII)**: `specs/325-crm-whatsapp-fundacao/verify_325.py`,
contra `manto_local`. Ele é escrito na Phase 2, ANTES do núcleo, e falha pelos motivos certos até
cada história fechar. Usa disjuntor de rede e dublê do cliente da Meta (molde `verify_317`).

## Formato: `[ID] [P?] [Story] Descrição`

## Phase 1: Setup

- [ ] T001 [P] Constantes do domínio em `app/conversas/constantes.py` (+ `app/conversas/__init__.py` vazio):
  - `CANAL_WHATSAPP`/`CANAL_INSTAGRAM`; direções; tipos; situações com `ORDEM_DA_SITUACAO`; origens;
    estados de aviso e de mídia;
  - `TEXTO_DO_TIPO` (pt-BR, Princípio XV); `MOTIVO_DO_ERRO` (R10); MIMEs aceitos por tipo de envio
    (R8);
  - tetos: corpo do aviso 256 KB, mídia 25 MB, texto 4096;
  - `JANELA_HORAS = 24`; limites da varredura (30 s, 10 min, 48 h, 10 tentativas); `MODELOS_CACHE_S = 300`.
- [ ] T002 [P] Configuração em `app/config.py`:
  - `_suppress_whatsapp()`, mesmo corpo de `_suppress_clicksign`, com `WHATSAPP_SUPPRESS_SEND` /
    `WHATSAPP_ALLOW_LOCAL_SEND`;
  - `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN`,
    `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_WABA_ID` (env, `""`);
  - `WHATSAPP_GRAPH_VERSION`, `WHATSAPP_GRAPH_BASE` (default real); `WHATSAPP_AVISO_SINCRONO=False`;
    `WHATSAPP_POLL_SEGUNDOS=5`; `CONVERSAS_MEDIA_FOLDER` (env, `""`).
- [ ] T003 [P] `render.yaml`: `envVars` `sync: false` para os cinco segredos/IDs `WHATSAPP_*` do
  `manto-backend`, com comentário da 325 no molde da ClickSign. O `startCommand` **não** muda.

---

## Phase 2: Foundational (bloqueia as histórias)

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

- [ ] T004 Models em `app/models.py`, conforme `data-model.md`, com docstrings do porquê:
  - `WhatsappAviso`, `Conversa` (`UNIQUE(canal, contato_id)`), `ConversaMensagem` (`UNIQUE
    externo_id`, `UNIQUE chave_envio`), `ConversaMidia` (`UNIQUE mensagem_id`);
  - propriedade tolerante `dados_dict`; backref `Client.conversas`;
  - `created_at` com `datetime.utcnow`.
- [ ] T005 Migration **manual** `migrations/versions/e325a7c1d9f2_conversas_whatsapp.py`:
  - `down_revision = "d323b5a1c0e7"`; `create_table` ×4, com índices e constraints nomeados;
    `downgrade` derruba na ordem inversa;
  - aplicar no `manto_local` com `flask db upgrade`.
- [ ] T006 [P] Cliente da Graph API, sem Flask, em `app/integracoes/whatsapp_client.py`, molde de
  `clicksign_client.py`:
  - exceções `WhatsappErro` → `WhatsappIndisponivel` → `WhatsappTravado`, e `WhatsappRecusou(code)`;
  - `_requisitar` com timeout `(5, 30)`;
  - `enviar_mensagem`, `subir_midia` (multipart), `consultar_midia`, `baixar_midia` (stream com
    teto), `listar_modelos` (paginado, só `APPROVED`), `marcar_lida`;
  - token, base, versão e `travado` sempre por parâmetro; o default é travado.
- [ ] T007 [P] `app/conversas/telefone.py`: `variantes_de_telefone(digitos)` sobre
  `contratos_ops.chave_telefone`, e `telefone_com_nono(digitos)` (R11).
- [ ] T008 [P] `app/conversas/configuracao.py`: `cfg_whatsapp()` lê o `current_app.config` e devolve
  um dataclass (`ligado`, `travado`, token, ids, base, versão, segredo, verify, pasta de mídia), molde
  `_ipc_cfg()`. `ligado` = os quatro obrigatórios preenchidos.
- [ ] T009 **`specs/325-crm-whatsapp-fundacao/verify_325.py`**, com os 21 cenários da spec:
  - disjuntor de rede antes do import; `MANTO_SEM_THREADS=1`; `pop` de `WHATSAPP_ALLOW_LOCAL_SEND`;
  - config falsa injetada no `app.config`; dublê `MetaFalsa` trocando as funções de
    `whatsapp_client` (registra chamadas, devolve wamids e bytes conhecidos);
  - usuários descartáveis `v325-*@manto.local` (Comercial, Casting); login por `POST
    /api/auth/login`; conferência por `create_engine` separado;
  - `--so=N` e `--manter`; limpeza no `finally`.
  - Escrito AGORA, e FALHANDO.
- [ ] T010 Infra em `app/__init__.py` e `app/backup_drive.py`:
  - default `CONVERSAS_MEDIA_FOLDER = instance/conversas_midia` + `makedirs` (molde `NFC_MEDIA_FOLDER`);
  - log da subida `"[whatsapp] ligado=%s travado=%s"` e aviso quando desligado;
  - `_MEDIA_SUBDIRS` ganha `"conversas_midia"`.

**Checkpoint**: tabelas no `manto_local`, cliente e primitivas prontos, verify rodando e falhando
pelos motivos certos.

---

## Phase 3: História 1 — A mensagem da cliente chega (P1) 🎯 MVP

**Objetivo**: aviso assinado → conversa + mensagem recebida, ligada à ficha, sem duplicar, com
reprocessamento.

**Verificação**: cenários 1–6 em PASS; tela da lista e da conversa aberta.

- [ ] T011 [US1] `app/conversas/aviso_ops.py`:
  - `gravar_aviso(corpo: bytes)` (estado `pendente`) e `reivindicar(aviso_id)` (UPDATE atômico,
    resgata `processando` > 10 min);
  - `processar_aviso(aviso_id, cfg)`: itera `entry/changes` com `field=messages`; ignora outro
    `phone_number_id`; `_conversa_do_contato` com `INSERT … ON CONFLICT DO NOTHING` + releitura;
    `_vincular_cliente` pelas variantes;
  - `_gravar_recebida` com `ON CONFLICT (externo_id)`; mídia ganha `ConversaMidia` `pendente`;
  - atualiza `ultima_recebida_em`, `ultima_mensagem_em`, `ultima_previa`, `nao_lidas`;
  - fecha em `processado` ou volta a `pendente` com `erro`.
- [ ] T012 [US1] `app/api/whatsapp_webhook.py`:
  - GET (`hub.*` + `compare_digest`, `text/plain`); POST (teto com `stream.read`, HMAC
    `X-Hub-Signature-256` com `compare_digest`; desligado ou inválido → 404);
  - grava e comita, responde 200; thread, ou síncrono com `WHATSAPP_AVISO_SINCRONO`;
    `@limiter.limit("300 per minute")`; comentário `RBAC:` (público, assinado);
  - registrar em `app/api/__init__.py`.
- [ ] T013 [US1] `app/conversas/varredura.py`:
  - `reprocessar_avisos(limite)`, que pega `pendente` com mais de 30 s ou `processando` parado, e
    `descartado` com 48 h ou 10 tentativas;
  - thread `_start_whatsapp_sweep` em `app/__init__.py` (atrás de `MANTO_SEM_THREADS`, só com o
    módulo ligado, a cada 60 s);
  - comando `flask whatsapp-reprocessar [--aplicar]` em `app/cli.py`.
- [ ] T014 [US1] `app/conversas/leitura_ops.py`: `listar_conversas(busca, antes)`,
  `abrir_conversa(id, antes)` e serializadores (`_iso_utc`; `nome` = ficha › perfil › telefone;
  `janela_aberta` e `janela_fecha_em`).
- [ ] T015 [US1] `app/api/conversas_read.py`:
  - `GET /api/conversas` e `GET /api/conversas/<id>`; gate `_pode_conversas()` (COMERCIAL,
    SUPERADMIN) no início da view;
  - comentário `RBAC:`; `configurado`/`envio_travado`/`poll_segundos` no payload da lista;
  - registrar em `app/api/__init__.py`.
- [ ] T016 [US1] `app/api/auth.py`: `serialize_user` ganha `conversas_ligadas` (COMERCIAL ou
  SUPERADMIN real e módulo ligado). `frontend/apps/internal/src/lib/types.ts`: `conversas_ligadas?:
  boolean`.
- [ ] T017 [P] [US1] `frontend/apps/internal/src/lib/conversas.ts`:
  - tipos do contrato;
  - `useConversas(busca)` com `refetchInterval` do payload (padrão 5 s), sem refetch em segundo plano;
  - `useConversa(id)` a cada 4 s; chaves de query.
- [ ] T018 [US1] Tela no app interno:
  - `pages/ConversasPage.tsx`: lista e conversa por `?c=<id>` no endereço (feature 320);
  - `components/conversas/ListaDeConversas.tsx`: busca com debounce, não lidas, horário em SP;
  - `components/conversas/ConversaAberta.tsx`: cabeçalho com link à ficha, mensagens em ordem e
    paginação "anteriores";
  - `components/conversas/Mensagem.tsx`: texto, horário, origem;
  - estados de FR-019; layout de FR-020; Framer Motion com `useReducedMotion`;
  - rota `/conversas` em `App.tsx` e item "Conversas" em `lib/navigation.tsx`
    (`conversas_ligadas`).

**Checkpoint**: cenários 1–6 verdes; a lista mostra a conversa semeada pelo verify (`--manter`).

---

## Phase 4: História 2 — Responder e ver se chegou (P1)

**Objetivo**: texto na janela, com autor, situação que avança e não regride, recusa fora da janela,
clique duplo inofensivo.

**Verificação**: cenários 7–10 e 20 em PASS.

- [ ] T019 [US2] `app/conversas/envio_ops.py`, `enviar_texto(conversa_id, texto, chave_envio,
  autor_id, cfg)`, na ordem R8:
  - não configurado → `NaoConfigurado`; travado → `EnvioTravado`; janela → `JanelaFechada`;
  - `INSERT` `pendente` com chave (conflito → devolve a existente); commit; chamada sem trava;
  - `enviada` + `externo_id`, ou `falhou` com motivo; prévia da conversa;
  - `marcar_lida(conversa_id, cfg)`: zera `nao_lidas`; na Meta, melhor esforço.
- [ ] T020 [US2] `app/conversas/aviso_ops.py`, `_aplicar_status`:
  - monotônico (`ORDEM_DA_SITUACAO`); `failed` com `errors[0].code` → `MOTIVO_DO_ERRO`;
  - id desconhecido → o aviso volta a `pendente` com "mensagem ainda não gravada".
- [ ] T021 [US2] `app/api/conversas_write.py`:
  - `POST /api/conversas/<id>/mensagens` (JSON texto) e `POST /api/conversas/<id>/lida` (204);
  - gate no início; exceções → 409 `janela_fechada`/`envio_travado`, 503 `nao_configurado`, 422
    `fields`;
  - comentário `RBAC:`; registrar em `app/api/__init__.py`.
- [ ] T022 [US2] Frontend:
  - `components/conversas/CaixaDeEnvio.tsx`: Enter envia e Shift+Enter quebra linha (FR-021);
    "Enviando…"; `chave_envio` nova por tentativa (`crypto.randomUUID`); texto só sai do campo no
    sucesso; envio otimista; aviso "janela fechada" com o botão "Enviar modelo";
  - ícones de situação em `Mensagem.tsx` ("enviada", "entregue", "lida", "não entregue" + motivo);
  - `POST …/lida` ao abrir a conversa; mutations em `lib/conversas.ts`.

**Checkpoint**: cenários 7–10 e 20 verdes.

---

## Phase 5: História 5 — Desligado por padrão e travado fora da produção (P1)

**Objetivo**: nada aparece nem sai sem configuração; banco local não envia; papel errado leva 403.

**Verificação**: cenários 16–18 em PASS.

- [ ] T023 [US5] Conferir e fechar as pontas do desligado:
  - webhook 404 e envio 503 sem configuração; `envio_travado` em toda escrita que fala com a Meta
    (texto, mídia, modelo, lida);
  - estado "O WhatsApp ainda não foi configurado." na tela;
  - menu oculto com `conversas_ligadas` falso.
- [ ] T024 [US5] Rodar os cenários 16–18 isolados (`--so=16,17,18`) e conferir que cada um falha
  pelo motivo certo (404, 409 `envio_travado` sem chamada ao dublê, 403). O registro no `docs/05`
  fica na T036.

**Checkpoint**: cenários 16–18 verdes (os três **devem** falhar e falham).

---

## Phase 6: História 3 — Foto, áudio, vídeo e documento (P2)

**Objetivo**: mídia recebida guardada na hora (ou pendente com retentativa) e exibida; mídia enviada
a partir de arquivo.

**Verificação**: cenários 11–13 em PASS.

- [ ] T025 [US3] `app/conversas/midia_ops.py`:
  - `baixar_e_guardar(midia_id, cfg)`: claim da linha, `consultar_midia` → `baixar_midia` com
    teto, gravação em `CONVERSAS_MEDIA_FOLDER/AAAA/MM/<uuid>.<ext>`, `guardada`; ou `pendente`/
    `falhou` com motivo;
  - chamado depois do commit do aviso (mesma thread) e pela varredura (`reprocessar_midias` em
    `varredura.py`).
- [ ] T026 [US3] `app/conversas/envio_ops.py`, `enviar_midia(conversa_id, arquivo, legenda,
  chave_envio, autor_id, cfg)`:
  - valida MIME e tamanho (422 `fields.arquivo`); guarda a cópia local;
    `subir_midia` → `enviar_mensagem`;
  - multipart em `POST /api/conversas/<id>/mensagens` (`conversas_write.py`).
- [ ] T027 [US3] `app/api/conversas_read.py`: `GET /api/conversas/midia/<id>` → `send_file(caminho,
  mimetype, conditional=True)`; 404 sem papel, sem arquivo ou não `guardada`.
- [ ] T028 [US3] Frontend:
  - `Mensagem.tsx`: imagem com `Foto` + `VisualizadorDeArquivo`; `<audio controls>`; `<video
    controls>`; documento com nome e "Ver"; "Arquivo sendo carregado…" e "Arquivo indisponível. Abra
    no celular.";
  - `CaixaDeEnvio.tsx`: botão "Inserir arquivo", com legenda.

**Checkpoint**: cenários 11–13 verdes.

---

## Phase 7: História 4 — Modelos aprovados (P2)

**Objetivo**: com a janela fechada (ou aberta), enviar um modelo aprovado com as variáveis.

**Verificação**: cenários 14–15 em PASS.

- [ ] T029 [US4] `app/conversas/envio_ops.py`:
  - `listar_modelos(cfg)`: cache de 5 min por processo, só aprovados, contagem de `{{n}}` do BODY;
  - `enviar_modelo(conversa_id, nome, idioma, variaveis, chave_envio, autor_id, cfg)`: valida
    aprovado e quantidade de variáveis (422); grava o texto final e `modelo_nome`.
- [ ] T030 [US4] Endpoints `GET /api/conversas/modelos` (`conversas_read.py`; 503 com mensagem) e
  `POST /api/conversas/<id>/modelo` (`conversas_write.py`).
- [ ] T031 [US4] `components/conversas/EnviarModeloDialog.tsx`:
  - `Combobox` do `@manto/ui`, campos por variável e prévia do texto final;
  - "Enviar modelo" com "Enviando…"; `Dialog` centralizado por flex (armadilha 16).

**Checkpoint**: cenários 14–15 verdes.

---

## Phase 8: História 6 — Ecos do app do celular (P3)

**Objetivo**: a mensagem enviada pelo app WhatsApp Business (coexistência) aparece como "enviada
pelo celular".

**Verificação**: cenário 19 em PASS.

- [ ] T032 [US6] `app/conversas/aviso_ops.py`: `field == "smb_message_echoes"` → mensagem `enviada`,
  `origem=celular`, sem autor, idempotente pelo `externo_id`; não reabre a janela. Formato
  conforme `research.md` §Confirmações. `Mensagem.tsx` mostra "Enviada pelo celular".

**Checkpoint**: cenário 19 verde; verify inteiro (1–21) verde.

---

## Phase 9: Polimento e transversais

- [ ] T033 `cd frontend && npm run typecheck` limpo (três SPAs); `ruff check` nos arquivos Python
  tocados e `ruff format` nos novos.
- [ ] T034 Tela aberta de verdade (skill `manto-conferir-tela`), com a conversa semeada pelo verify
  `--manter`:
  - lista, conversa, envio, modelo e mídia;
  - estados vazio, desligado e erro;
  - desktop e 375×812.
- [ ] T035 Texto novo revisado pelo Princípio XV (superfície interna; glossário: "Situação",
  "Inserir arquivo", "Tentar novamente"), lido na tela aberta.
- [ ] T036 Docs por fonte única:
  - `docs/01`: §2 tabelas, §3 seção nova "Conversas", §4.3 uma linha por endpoint, §5 variáveis e
    trava;
  - `docs/02`: tela Conversas;
  - `docs/03`: entrada no topo e linha no índice;
  - `docs/04`: domínio Conversas, com janela, idempotência, nono dígito e varredura;
  - `docs/05`: desligada até o painel; LGPD (prazo de guarda); volume de mídia e backup; teto de
    25 MB;
  - `docs/00` §3: linha do domínio;
  - `docs/PLANO_CRM_PROPRIO.md`: Fase 1 marcada.
- [ ] T037 `quickstart.md` §1–2 executados. A §3 (número de teste da Meta) fica listada como o que é
  do dono, com o teste de deploy do SC-003: mandar mensagens durante um deploy e conferir que nenhuma
  se perde.
- [ ] T038 `/speckit-converge` sem gaps.

---

## Dependências e ordem

- Setup (T001–T003, paralelos) → Foundational (T004 → T005; T006–T008 paralelos; T009 depois de
  T004; T010) → US1 → US2 → US5 → US3 → US4 → US6 → Polimento.
- US2 usa o processador de US1 (status); US3 usa a mídia `pendente` criada em US1; US4 usa o envio
  de US2; US6 usa o processador de US1.
- Dentro da história: `_ops` → endpoint → tela; o verify da história em PASS fecha a fase.

## Paralelismo

- T001, T002 e T003 (arquivos distintos). T006, T007 e T008 (arquivos novos e independentes).
- T017 (lib do front) em paralelo com T014–T015 (o contrato está em `contracts/api.md`).

## Estratégia

- **MVP**: Setup + Foundational + US1 + US2 + US5 (as P1). É possível receber, responder e ter a trava.
- **Incremental**: US3 (mídia) → US4 (modelos) → US6 (eco). Cada uma fecha com o seu trecho do verify.
- Commits por grupo lógico (`feat(325): …`), sempre por caminho, nunca `git add -A`.
