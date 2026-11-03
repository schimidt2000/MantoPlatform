---
description: "Tasks da feature 330 — Instagram Direct na caixa de Conversas"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: 330 — Instagram Direct na caixa de Conversas

**Input**: artefatos em `specs/330-crm-instagram-direct/`

**Pré-requisitos**: plan.md, spec.md (3 histórias, 23 cenários), research.md (R1–R13), data-model.md, contracts/api.md

**Verificação (OBRIGATÓRIA — Princípio VIII)**: `specs/330-crm-instagram-direct/verify_330.py` contra o `manto_local`,
no molde do `verify_328`:
- disjuntor de rede;
- dublê do `instagram_client` e do `whatsapp_client`;
- avisos assinados do Instagram;
- conferência por conexão separada;
- login pela API;
- limpeza no `finally`.

É escrito na Foundational (T008), antes do núcleo. O `verify_325` e o `verify_328` são regressão (o envio do WhatsApp
passa a ir pelo adaptador de canal).

**Base**: worktree `C:\tmp\mp330`, branch `330-crm-instagram-direct` sobre a `328-crm-equipe-na-caixa`. Sem merge e sem
push.

## Regra de dependência (todas as fases)

- **`instagram_ops`** importa `aviso_ops` (conversa, inserção idempotente, prévia, espera), `equipe_ops`, `relogio`,
  `constantes` e `midia_ops`. O `aviso_ops` só o chama por **import tardio** dentro de `processar_aviso` (ciclo).
- **`canais`** importa os dois clientes, `configuracao`, `constantes`, `leitura_ops` e `recusa`; o `envio_ops` importa
  `canais`.
- **`equipe_ops`** continua sem importar `aviso_ops`/`envio_ops`.

---

## Phase 1: Setup

- [X] T001 Constantes do Instagram em `app/conversas/constantes.py`:
  - `TIPO_DO_ANEXO_IG`: `image`/`video`/`audio`/`file` → tipos da casa;
  - os anexos que viram texto: `share`, `ig_reel`, `reel`, `story_mention` e `ephemeral`;
  - envio: `MIME_DE_ENVIO_IG` (png/jpeg/gif, mp4/ogg/avi/mov/webm de vídeo, aac/m4a/wav/mp4 de áudio, pdf) e
    `TETO_DE_ENVIO_IG` (imagem 8 MB, resto 25 MB);
  - `TEXTO_MAXIMO_IG_BYTES = 1000`, `JANELA_HUMANA = timedelta(days=7)`, `PERFIL_INTERVALO = timedelta(hours=24)`;
  - `JANELA_ABERTA/HUMANA/FECHADA`;
  - os textos do XV da spec e do contrato:
    - apagada pela cliente, story, menção, publicação, reels, efêmera, não suportada (Instagram) e "Contato do
      Instagram";
    - aviso da janela humana, janela de 7 dias fechada, Instagram não configurado, sem modelos, tipo não aceito e texto
      longo;
    - os motivos de recusa da marca humana e do roteamento.
- [X] T002 [P] `app/config.py` com `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_PAGE_ID` e `INSTAGRAM_ACCOUNT_ID` (default
  vazio = desligado); `app/__init__.py` com o log `[instagram] ligado=… travado=…` na subida; `render.yaml` com as três
  entradas `sync: false` no `manto-backend`.
- [X] T003 [P] `app/integracoes/whatsapp_client.py`: `_requisitar` vira público `requisitar`, e o nome antigo continua
  como alias, para não quebrar ninguém.
- [X] T004 [P] `app/integracoes/instagram_client.py` (novo, sem Flask) sobre o `requisitar`:
  - `ConexaoInstagram(base, versao, token, page_id, account_id, travada)`, com uma conversão para o `ConexaoMeta` do
    transporte;
  - `enviar(conexao, corpo) -> {"id"}` (`POST /{page_id}/messages`, JSON);
  - `enviar_arquivo(conexao, destino, tipo, dados, mime, nome, extras) -> {"id"}` (multipart: `recipient` e `message`
    como JSON, mais `filedata`);
  - `perfil(conexao, igsid) -> {"nome", "usuario"}` (`GET /{igsid}?fields=name,username`).
- [X] T005 `app/conversas/configuracao.py`: `cfg_instagram() -> CfgInstagram(ligado, travado, app_secret, verify_token,
  account_id, pasta_midia, conexao)`.
  - `ligado` exige o token, a Página, a conta, o segredo e a verificação.
  - `travado` usa a mesma `WHATSAPP_SUPPRESS_SEND` (R9).

---

## Phase 2: Foundational

- [X] T006 `app/models.py`: `Conversa.usuario` (String 64) e `Conversa.perfil_em`; `ConversaMensagem.externo_id` e
  `resposta_a` em String(255). Migration **manual** `migrations/versions/a330c4e8f1b2_conversas_instagram.py`
  (`down_revision="f328b2d4e6a1"`), com downgrade. Aplicar no `manto_local`, ensaiar o downgrade e conferir que há um
  head só.
- [X] T007 `app/conversas/aviso_ops.py`:
  - `conversa_do_contato` só deriva telefone e vínculo com a ficha no canal WhatsApp (R3: o IGSID é numérico);
  - `processar_aviso` despacha por `corpo["object"] == "instagram"` para `instagram_ops.processar_entradas(corpo,
    cfg_instagram())`, com import tardio. A garantia de transação, devolução e descarte é a mesma.
- [X] T008 **`specs/330-crm-instagram-direct/verify_330.py`** com os 23 cenários da spec, mais o standby (cenário 18b) e a
  recusa do roteamento (17b).
  - **Dublê** do `instagram_client` (envio JSON e multipart, perfil) e do `baixar_midia`.
  - **Usuários descartáveis**: Ana e Bia (COMERCIAL) e Cris (CASTING).
  - **Janela**: as faixas de 30 h e 8 dias se ajustam por conexão separada (`ultima_recebida_em`).
  - **Áudio**: o cenário do áudio usa o ffmpeg do app (`caminho_do_ffmpeg`), e pulado não é verde.

  Roda agora e **falha** no que não existe.

**Checkpoint**: migration aplicada; verify falhando pelos motivos certos; `verify_325` ainda verde.

---

## Phase 3: História 1 — O Direct chega na caixa (P1) 🎯 MVP

**Verificação**: cenários 1–9 e 22.

- [X] T009 [US1] `app/api/instagram_webhook.py` (novo): `GET` (desafio com `WHATSAPP_VERIFY_TOKEN`) e `POST`
  (assinatura pela `assinatura_valida` do `whatsapp_webhook`, teto de 256 KB, grava cru, processa fora ou síncrono).
  Desligado → 404. Comentário `RBAC:` no topo. Registrar em `app/api/__init__.py`.
- [X] T010 [US1] `app/conversas/instagram_ops.py` (novo): `processar_entradas(corpo, cfg) -> list[int]` (mídias a
  baixar).
  - Para cada `entry` da conta (`entry.id` igual ao `account_id`; senão log e ignora), processa os itens de
    `messaging[]` **e** de `standby[]`.
  - `_gravar_recebida_ig`:
    - conversa `canal=instagram`;
    - uma mensagem por anexo (`mid`, `"{mid}#{n}"`), com o texto no primeiro;
    - texto pronto para story, reels, publicação, efêmera e não suportada, e o `reply_to.story`;
    - `is_deleted` troca o texto da mensagem existente;
    - não lidas, prévia, `ultima_recebida_em` e `abrir_espera` (não para reação).
- [X] T011 [US1] `instagram_ops`:
  - `_gravar_reacao` (`TIPO_REACAO`, `externo_id="reacao:{mid}:{ts}:{acao}"`);
  - `_aplicar_visto` (`read.mid` → `lida` na enviada e nas anteriores abaixo de lida, sem regredir).
- [X] T012 [US1] `instagram_ops.atualizar_perfis(conversa_ids, cfg)`, depois do commit do aviso e fora da transação:
  - busca o perfil quando `perfil_em` é nulo, ou quando falta o nome e o carimbo tem mais de 24 h;
  - grava `nome_perfil` e `usuario`, e carimba sempre;
  - a falha só loga.

  É chamada no fim do `processar_aviso` do Instagram.
- [X] T013 [US1] `app/conversas/midia_ops.py`: `baixar_e_guardar` despacha pelo canal da conversa. No Instagram, o link
  vem do `dados` da mensagem (o anexo daquela posição), passa pelo `baixar_midia` com teto de 25 MB, e o MIME sai da
  resposta ou do tipo. O `_criar_midia_ig` grava sem `externo_id`.
- [X] T014 [US1] `app/conversas/leitura_ops.py`:
  - `serializar_conversa` ganha `usuario`, `janela` e `janela_aberta`/`janela_fecha_em` pela regra do canal (R10);
  - `listar_conversas` ganha o filtro `canal`.

  Também:
  - `app/api/conversas_read.py`: `canal` com 422 se inválido, e `canais_ligados` na lista; o `configurado` passa a
    valer com qualquer canal ligado (só o Instagram ligado não pode mostrar "O WhatsApp ainda não foi configurado.");
  - `app/api/auth.py`: `conversas_ligadas` com qualquer canal ligado.
- [X] T015 [P] [US1] Tela (`frontend/apps/internal/src/`):
  - `lib/conversas.ts`: tipos `Canal`, `Janela`, campos opcionais e `useConversas(busca, filtro, canal)`;
  - `components/conversas/IconeDoCanal.tsx` (novo);
  - `FiltroDaLista` ganha os botões de canal, mostrados com `canais_ligados.length > 1`;
  - `ListaDeConversas` mostra o ícone, e `@usuario` no lugar do telefone;
  - `ConversasPage` guarda `?canal=` no endereço;
  - o cabeçalho da `ConversaAberta` mostra o ícone e o @usuário.

**Checkpoint**: cenários 1–9 e 22 em PASS.

---

## Phase 4: História 2 — Responder pelo Direct (P1)

**Verificação**: cenários 10–17 (com 17b).

- [X] T016 [US2] `app/conversas/canais.py` (novo). *Feito:* sem mover o WhatsApp — `canais.py` traz só o que é do
  Instagram, e o `envio_ops` desvia pelo canal da conversa (`_concluir` comum); o `verify_325` ficou 22/22. Plano original:
  `CanalWhatsapp` e `CanalInstagram`, as duas com a mesma
  interface:
  - `ligado`, `travado` e `texto_nao_configurado`;
  - `pre_condicoes(conversa, exige_janela) -> extras`;
  - `validar_texto(texto)` e `tipo_do_arquivo(mime, tamanho)`;
  - `enviar_texto(conversa, texto, extras)` e `enviar_arquivo(conversa, midia, dados, tipo, legenda, extras) -> id
    externo`;
  - `marcar_lida(conversa)`.

  O WhatsApp é o código atual de `envio_ops` movido sem mudar comportamento. No Instagram:
  - a janela de 24 h / 7 dias põe `MESSAGE_TAG`/`HUMAN_AGENT` nos `extras`, e depois de 7 dias recusa com 409
    `janela_fechada`;
  - o texto é limitado em 1.000 bytes;
  - os tipos e tetos são os do Instagram;
  - `marcar_lida` não chama a Meta.

  `canal_da_conversa(conversa, cfg_whatsapp)` escolhe o canal. O `CanalWhatsapp` chama `wc.enviar`/`wc.subir_midia`
  pelo **módulo** (`wc.<função>`), nunca por import direto da função, para o dublê do `verify_325` seguir valendo.
- [X] T017 [US2] `app/conversas/envio_ops.py`: `enviar_texto` e `enviar_arquivo` orquestram pelo canal (chave, reserva,
  cópia local, despacho, `resposta_da_equipe`, falha com motivo). Áudio webm ou ogg numa conversa do Instagram passa
  por `midia_ops.audio_para_m4a`. `enviar_modelo` no Instagram → 409 `sem_modelos`. `marcar_lida` vai pelo canal.
- [X] T018 [P] [US2] `app/conversas/midia_ops.py`: `audio_para_m4a(dados)` (ffmpeg `-vn -c:a aac -b:a 96k -f ipod`,
  arquivo temporário, 60 s; `AudioIndisponivel`).
- [X] T019 [US2] `app/conversas/constantes.py` + `canais`: o motivo da recusa no Instagram.
  - Com a marca humana enviada e a Meta recusando por permissão (`code` 10 ou 200), o texto é o da marca não
    liberada.
  - Recusa por roteamento ou controle de conversa (subcódigos a confirmar no teste): o texto do roteamento.
  - O resto: o `motivo_do_erro` da 325.
- [X] T020 [P] [US2] Tela: a `CaixaDeEnvio` no Instagram:
  - aviso da janela humana acima do campo;
  - depois de 7 dias, só o aviso, sem campo;
  - sem "Enviar modelo";
  - o clipe aceita os tipos do Instagram;
  - o contador de caracteres usa o limite de 1.000.

  Tipos no `lib/conversas.ts`.

**Checkpoint**: cenários 10–17 em PASS; `verify_325` e `verify_328` verdes.

---

## Phase 5: História 3 — Piloto ao lado do Kommo (P2)

**Verificação**: cenários 18–21 (com 18b).

- [X] T021 [US3] `instagram_ops._gravar_eco_ig` (`message.is_echo`):
  - grava ENVIADA com origem `outro`, sem duplicar o próprio `mid`;
  - com envio da Plataforma em voo na conversa e o `mid` ainda desconhecido, levanta `MensagemAindaNaoGravada`;
  - encerra a espera com o momento do eco, sem atribuir.
- [X] T022 [US3] Canal desligado:
  - webhook 404;
  - envio 503 `nao_configurado` com o texto do Instagram;
  - `canais_ligados` sem o Instagram (filtro oculto);
  - na tela, a mensagem `origem: "outro"` aparece como "Enviada por outro app".

**Checkpoint**: todos os cenários em PASS.

---

## Phase 6: Polimento e portões

- [X] T023 `ruff check` nos arquivos tocados; `ruff format` só nos novos (`instagram_client.py`, `instagram_ops.py`,
  `canais.py`, `instagram_webhook.py`, a migration e o verify). Não usar `--fix` no `app/api/__init__.py`.
- [X] T024 `npm run typecheck` limpo (três SPAs).
- [X] T025 `verify_330`, `verify_328` e `verify_325` verdes, com zero escapes.
- [X] T026 Tela pela worktree (backend e Vite em portas próprias), em desktop e 375×812 (quickstart §2).
- [X] T027 Textos novos pelo Princípio XV, na tela.
- [ ] T028 Docs por fonte única:
  - `docs/01`: coluna, webhook, envio, variáveis, RBAC §4.3 e §5 (envs);
  - `docs/02`;
  - `docs/03`: entrada no topo, **NÃO PUBLICADO**, e índice;
  - `docs/04`: invariantes do Instagram;
  - `docs/05`: o canal desligado e os pontos a confirmar no teste;
  - `docs/PLANO_CRM_PROPRIO.md`: a 2b feita e a ligação pela Página no lugar do "Instagram Login".
- [ ] T029 Gates CHK001–CHK011 do `checklists/instagram-roteamento-janela.md` e o quickstart §1–2 executados.

---

## Dependências e ordem

- Setup → Foundational → US1 → US2 → US3 → Polimento.
- A US2 depende da US1 (conversa do Instagram existe), e a US3 da US1 (o processador) e da US2 (o `mid` da própria
  mensagem).
- O T016 move o envio do WhatsApp: o `verify_325` roda logo depois dele.

## Estratégia

- **MVP**: Setup + Foundational + US1 + US2 (as duas P1), que bastam para atender o Direct pela Plataforma.
- **Commits** por grupo lógico (`feat(330): …`), por caminho, com `git commit -F`. Sem merge e sem push.
