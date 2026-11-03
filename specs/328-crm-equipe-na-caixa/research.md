# Pesquisa — 328 Conversas em equipe

Decisões da Phase 0. As decisões de produto vieram do dono (spec, Clarifications). Aqui está só o "como".

## R1 — Quem vira responsável ao responder

- **Decisão**: no fim do `_despachar` (`app/conversas/envio_ops.py`), quando a Meta aceita o envio, um `UPDATE
  conversas SET responsavel_id = :autor, assumida_em = :agora WHERE id = :id AND responsavel_id IS NULL`. É
  condicional de propósito: entre duas respostas quase simultâneas, a primeira fica com a conversa, sem "último
  ganha". Envio que falhou (`falhou`) não atribui. O eco não tem autor, então não atribui.
- **Alternativas**: atribuir ao abrir a conversa — descartada, porque abrir não é responder e o dono disse
  "quem responder primeiro".

## R2 — Assumir, transferir, devolver

- **Decisão**: um núcleo só, `equipe_ops.definir_responsavel(conversa_id, novo_id | None, quem, *, modo)`, com
  concorrência otimista: lê o responsável atual, decide se pode e grava com `WHERE responsavel_id IS NOT
  DISTINCT FROM :atual`. Se `rowcount == 0`, alguém mudou no meio e volta 409.
  - `assumir`: só se o atual é nulo ou sem papel de conversas/inativo. Senão, 409 "Esta conversa já foi
    assumida por {nome}.".
  - `transferir`: o destino precisa estar ativo, ter acesso e ter papel de conversas (senão 422
    `fields.responsavel_id`).
  - `devolver`: grava nulo.
- **Por quê**: o "Assumir" em corrida é o cenário 4; a condição no `WHERE` resolve sem trava longa.

## R3 — O início da espera

- **Decisão**: `conversas.aguardando_desde`, UTC.
  - Preenchido em `_gravar_recebida` (`aviso_ops`) só quando a mensagem é **nova** e a coluna está vazia: a
    espera conta da primeira sem resposta.
  - Esvaziado quando a equipe responde: o envio aceito pela Meta (no `_despachar`, junto com o R1) ou um eco do
    celular que seja mensagem de verdade (o `revoke`/`edit` não é resposta).
  - Ao esvaziar, apaga os avisos de espera da conversa (FR-008) com
    `notificacoes_ops.apagar_por_entidade("conversa", id, kind=KIND_CONVERSA_ESPERANDO)`. O filtro por `kind`
    é aditivo: sem ele, a espera encerrada apagaria também o aviso de transferência (FR-018), que aponta para
    a mesma conversa.
  - O status `failed` que chega **depois** do aceite reabre a espera, com `recalcular_espera`: a primeira
    recebida depois da última resposta válida. A resposta que não chegou não conta (caso de borda "Resposta
    que falhou").
- **Dependência entre módulos**: `equipe_ops` fica embaixo e nunca importa `aviso_ops`/`envio_ops`, porque são
  eles que o importam. Por isso o relógio `agora_utc` vai para `app/conversas/relogio.py`, e a exceção
  `Recusa` vai para `app/conversas/recusa.py` (`EnvioRecusado` herda dela).
- **Por quê**: guardar o início, em vez de recalcular pelas mensagens, deixa a rotina de alerta num `SELECT`
  indexado e a lista mostra "há X min" sem consulta extra.

## R4 — O alerta

- **Decisão**: `equipe_ops.alertar_esperas(agora_sp)` roda na passada da thread `whatsapp-sweep`
  (`varredura.ciclo_de_varredura`).
  - Fora de `9 <= hora < 21` em São Paulo (`now_sp()`), não faz nada.
  - Dentro do horário, entram as conversas com `agora_utc − 24 h < aguardando_desde <= agora_utc − 15 min` e
    **ainda sem aviso de espera** (convergência: sem isso, a espera que ninguém responde ocupava o lote por 24 h),
    as mais antigas primeiro, até o lote da varredura. Uma espera com a janela fechada não se responde com
    texto e não pode entrar em toda passada para sempre. Para cada uma, chama
    `notificacoes_ops.emitir(KIND_CONVERSA_ESPERANDO, …)`:
    - `dedupe_key = "conversa.esperando:{id}:{epoch do início}"`, um aviso por espera;
    - `entidade = ("conversa", id)`, `link_path = "/conversas?c={id}"`;
    - destinatário: o responsável, se ativo e com papel; senão `None` (resolve por papel no catálogo).
  - A rodada comita (regime da rotina de fundo, docstring da 272).
  - Kind novo no catálogo, com `DESTINATARIOS_POR_KIND[KIND_CONVERSA_ESPERANDO] = (COMERCIAL, SUPERADMIN)`.
- **Texto** (XV, interno): "{Nome} espera resposta há {N} min." com corpo "{prévia da última mensagem}".
- **Alternativas**: thread própria — descartada, porque a do WhatsApp já roda a cada 60 s e só com o módulo
  ligado.

## R5 — Notas internas

- **Decisão**: tabela `conversa_notas` (conversa CASCADE, autor SET NULL, texto, `created_at` UTC). O detalhe
  da conversa devolve `notas` (as 200 mais recentes, em ordem) e a tela as intercala por horário, com visual
  próprio. Nada vai para a Meta e não há trava de ambiente.

## R6 — Respostas rápidas

- **Decisão**: tabela `respostas_rapidas` com:
  - `titulo` (80), com índice único em `lower(titulo)` — "Pagamento" e "pagamento" não convivem;
  - `atalho` (30), opcional, guardado em minúsculas, sem "/" e sem espaço, também com índice único;
  - `texto` (4.096), `criado_por_id`, `alterado_por_id` e horários.
- **Núcleo**: `respostas_ops` faz o CRUD e devolve as recusas por campo (422). A unicidade é conferida antes
  e o índice segura a corrida (`IntegrityError` → 422).
- **Excluir**: é o registro de verdade (configuração, não histórico), com `ConfirmDialog` na tela.
- **`{nome}`**: substituído na tela (o primeiro nome do contato). O servidor guarda o texto cru.

## R7 — Áudio gravado

- **Navegador**: `MediaRecorder` com o primeiro MIME suportado, nesta ordem:
  1. `audio/ogg;codecs=opus` (Firefox);
  2. `audio/webm;codecs=opus` (Chrome, Edge);
  3. `audio/mp4` (Safari).

  Tempo correndo e limite de 5 min (a nota de voz do WhatsApp chega a 16 MB, e 5 min de Opus ficam em ~2 MB).
  O áudio sai pelo mesmo `POST /api/conversas/<id>/mensagens` multipart, com nome `audio-<data>.<ext>`.
- **Servidor**:
  - `audio/webm` → `midia_ops.webm_para_ogg(bytes)` via ffmpeg com `-c:a copy -f ogg`: só troca o recipiente,
    porque o Opus já está dentro. Testado na máquina de desenvolvimento em 03/11: ffmpeg 8.1 LGPL, sem
    recodificar.
  - Arquivo temporário (o pipe do ffmpeg no Windows é frágil) e timeout de 60 s.
  - O ffmpeg vem de `video_ops`, que ganha um `caminho_do_ffmpeg()` público, para não haver uma segunda
    procura do binário (Princípio I). O ffprobe não é exigido.
  - Sem ffmpeg ou falha → `EnvioRecusado` 422 `fields.arquivo` "Não foi possível preparar o áudio. Envie o
    arquivo pelo clipe.".
  - Áudio `audio/ogg` sai com `voice: true` (nota de voz).
- **Produção**: o ffmpeg 5.1.9 do contêiner do Render (armadilha 24 do `docs/00`) faz a cópia sem encoder.
- **Alternativas**: gravar em ogg no navegador com biblioteca (opus-recorder, ~200 KB de WASM) — descartada,
  porque o remux no servidor custa milissegundos e não pesa no celular.

## R8 — Tela

- **Lista**:
  - filtro `?filtro=todas|minhas|sem_responsavel` no endereço (feature 320), em botões de alternância;
  - cada item mostra o responsável (ou "Sem responsável") e, com espera, "Esperando há 20 min" em vermelho
    a partir de 15.
- **Conversa**:
  - no cabeçalho, "Responsável: Ana" e um menu com "Assumir", "Transferir…" (diálogo com `Combobox` da
    equipe) e "Devolver à fila";
  - caixa com alternância "Mensagem | Nota interna";
  - botão "Respostas rápidas" (lista com busca; "/" no começo do campo abre a mesma lista);
  - "Gerenciar respostas rápidas" num diálogo com criar, editar e excluir;
  - microfone para "Gravar áudio".
- **Linha do tempo**: as notas ficam em dourado claro ("Nota interna · Ana · 14:32").

## R9 — Migration e base

- A base é a branch 325, ainda não está na `main`. Por isso `down_revision = "e325a7c1d9f2"` (o head da 325).
  As features 326 e 327 de outras sessões não têm migration (conferido em 03/11).
- No merge, a 325 entra antes da 328.
