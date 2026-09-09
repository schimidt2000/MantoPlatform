# Pesquisa — Feature 297

Fase 0 do `/speckit-plan`. Cada decisão abaixo foi tomada contra evidência medida, não contra
suposição. As medições na produção foram todas de leitura, sem tocar `access_count`.

## D1 — O defeito relatado não é corrupção, é peso

**Decisão**: tratar "os vídeos não tocam" como um problema de tamanho de arquivo, e resolvê-lo com
conversão no servidor. Nada de investigar codec, MIME ou proxy.

**Evidência** (09/09, disco da produção e rota pública):

| Verificação | Resultado |
|---|---|
| Arquivos presentes em `instance/nfc_media/` | 10, de 42 a 147 MB, 980 MB no total |
| Caixas MP4 fecham no tamanho do arquivo | 10 de 10, nenhum truncado |
| Container e codec | `mp42`, `avc1` (H.264) + `mp4a` (AAC), `moov` no início |
| Resolução | 1080x1920 em seis; **2160x3840 em quatro** |
| Bitrate | 23 a **76 Mbps** |
| Rota pública com `Range: bytes=0-63` | `206`, `Content-Type: video/mp4`, `Accept-Ranges: bytes`, bytes corretos |
| Acessos reais nas tags com vídeo | 45 desde 22/08 |

**Racional**: um vídeo de 16 segundos com 147 MB a 76 Mbps não é assistível em rede móvel, e dez
players 4K na mesma tela esgotam os decodificadores do navegador — daí o `MEDIA_ERR_DECODE` que o
Firefox traduz como "arquivo corrompido". O servidor está correto.

**Alternativas descartadas**: transcodificar por MIME/codec (o codec já é o certo); mexer no proxy
(`/api` já está em `BACKEND_PREFIXES`, `frontend/server.js:192`); trocar o player.

## D2 — ffmpeg já existe na produção, sem dependência nova

**Decisão**: usar o `ffmpeg` do próprio contêiner, invocado por `subprocess`. Nada em
`requirements.txt`.

**Evidência**: `/usr/bin/ffmpeg`, versão `5.1.9-0+deb12u1`, com `libx264`, `libx265`, `aac`,
`libvpx-vp9` e os filtros `scale`, `overlay`, `pad`, `scale2ref`. `ffprobe` no mesmo lugar.

**Risco aceito, com mitigação**: o `ffmpeg` **não está declarado em `render.yaml`** — ele vem da
imagem base do runtime Python do Render. Se o Render trocar a imagem, ele some sem aviso. Mitigação
em FR-006: a ausência degrada para "entrega o vídeo como veio e registra o motivo", nunca derruba o
upload. Vira dívida registrada em `docs/05`.

**Alternativa descartada**: `imageio-ffmpeg` no `requirements.txt`, que embarca um binário estático
de ~40 MB. Só se justifica se o binário do sistema sumir.

## D3 — A cadeia de filtros, provada em bancada

**Decisão**: normalizar para no máximo 1080 de largura e sobrepor a moldura com `scale2ref`, que a
redimensiona ao tamanho exato do vídeo já normalizado.

```text
[0:v]scale='if(gt(iw,1080),1080,iw)':-2,setsar=1[v0];
[1:v][v0]scale2ref=w=iw:h=ih[mold][v1];
[v1][mold]overlay=0:0:format=auto[vout]
```

Saída: `-c:v libx264 -crf 23 -maxrate 5M -bufsize 10M -pix_fmt yuv420p -c:a aac -b:a 128k
-movflags +faststart`, com `-map "[vout]" -map 0:a?` (o `?` deixa passar vídeo sem áudio).

**Evidência** (`scratchpad/prova_moldura.py`, rodado nesta máquina em 09/09): entrada sintética
2160x3840 de 8 s e 28,3 MB, moldura PNG de **1200x2000** — de propósito num tamanho diferente do
vídeo. Resultado:

| Medida | Valor |
|---|---|
| Saída | 1080x1920, 8,0 s, 3,9 MB |
| Equivalente por 30 s | 14,5 MB |
| Tempo de CPU | 2,9 s para 8 s de vídeo |
| Pixel do canto, com × sem moldura | diferença de 289 em 765 |
| Pixel do centro, com × sem moldura | diferença de 19 em 765 |

Ou seja: a moldura encostou na borda, o miolo do vídeo ficou preservado, e o alvo de peso da
decisão do dono (cerca de 15 MB por 30 s) sai naturalmente do `crf 23`. O `-2` na altura garante
número par, exigência do `yuv420p`.

**Detalhes que evitam retrabalho**:
- `setsar=1` normaliza pixels não quadrados; sem isso um vídeo com SAR estranho sai deformado.
- O ffmpeg aplica a rotação da câmera sozinho (`autorotate` é o padrão) e a saída fica sem matriz de
  rotação. Vídeo de iPhone deitado na metadata sai em pé de verdade.
- `format=auto` no `overlay` preserva o canal alfa do PNG.
- A moldura pode ter qualquer dimensão: o `scale2ref` a ajusta. A proporção dela, porém, deve bater
  com a do vídeo, senão ela estica. Como todo vídeo vira 9:16, a moldura deve ser 9:16.

**Alternativa descartada**: `-vf "movie=moldura.png[m];[in][m]overlay"`, que fixa o tamanho da
moldura e obrigaria a gerar uma moldura por resolução.

## D4 — Guardar um mestre 1080p, não o arquivo cru da câmera

**Decisão**: para cada entrega, guardar **duas** versões: o *mestre* (1080p, sem moldura) e o
*entregue* (o mestre com a moldura gravada). Quando o envio é sem moldura, o entregue é o próprio
mestre e só existe um arquivo. O arquivo cru enviado é descartado depois da conversão bem-sucedida.

**Racional**: o motivo de guardar um original é poder trocar a moldura sem pedir o vídeo de volta à
equipe. O mestre 1080p faz isso por cerca de 15 MB, enquanto o arquivo cru custa de 42 a 147 MB.

**Evidência que decide**: o backup de mídia empacota `instance/nfc_media` inteiro
(`app/backup_drive.py:31`) e guarda duas gerações; o comentário no próprio código diz que o regime
atual já ocupa cerca de 6,5 GB dos 15 GB da conta de serviço do Drive
(`app/backup_drive.py:33`). Guardar arquivos crus multiplicaria isso e estouraria a cota.

| Cenário, por vídeo | Disco no Render | Peso no backup |
|---|---|---|
| Hoje | 42 a 147 MB | o mesmo |
| Guardando o cru como original | 150 MB mais 15 MB | pior que hoje |
| **Mestre 1080p mais entregue** | **cerca de 30 MB** | cerca de 30 MB |

**Consequência para a spec**: FR-002 e SC-007 falavam em "arquivo original recebido". Passam a falar
em mestre sem moldura. A garantia para o dono é a mesma: trocar a moldura depois é reprocessar, não
regravar. O custo é uma geração extra de compressão quando a moldura muda, o que é imperceptível
numa troca eventual.

**Alternativa descartada**: não guardar nada além do entregue. Tornaria a troca de moldura
impossível sem pedir os vídeos de volta, e a decisão do dono na pergunta 1 dependia justamente de a
escolha ser reversível.

## D5 — Onde a conversão roda, com o ERP no mesmo contêiner

**Decisão**: converter em segundo plano, **um vídeo por vez**, no próprio serviço do backend, com o
processo em `nice -n 19` e `-threads 1`.

**Evidência** (cgroup do contêiner de produção, 09/09):

| Limite | Valor |
|---|---|
| `cpu.max` | `100000 100000`, ou seja **1 CPU inteira, e só uma** |
| `memory.max` | 2 GB |
| `memory.current` | 891 MB, sobrando cerca de 1,2 GB |

O mesmo processador atende os 3 workers do gunicorn. Uma conversão sem freio deixa o ERP lento para
todo mundo enquanto dura. O `nice` foi testado no contêiner e funciona: o escalonador dá a CPU ao
worker web sempre que ele acorda, e o ffmpeg usa o que sobra.

**Regras que vêm de incidentes já vividos**:
- Arquivo temporário **nunca** em `/tmp`: lá é RAM no Render, e um arquivo grande matou o serviço
  inteiro em 28/08 (`app/backup_drive.py:37-44`, `_tmp_no_disco`). O temporário da conversão fica
  em `instance/`.
- Um vídeo por vez, e nunca durante o `flask db upgrade` do start.

**Alternativa descartada**: um serviço `worker` separado no Render. Resolveria a disputa de CPU, mas
custa outro plano pago, outro deploy e acesso compartilhado ao disco, que o Render não oferece entre
serviços.

## D6 — O upload de 250 MB pode ser cortado pelo proxy hoje

**Decisão**: corrigir junto, no mesmo commit da rota de upload.

**Evidência**: `frontend/server.js:544` define `PROXY_TIMEOUT_MS = 180_000` e `server.js:595` só
dispensa o prazo para o que casa `MEDIA_PATTERNS` (`server.js:546-551`). O download do vídeo NFC casa
o padrão `/(?:media|video|pdf)(?:[/?]|$)/` e fica sem prazo, mas o **upload**
(`POST /api/3d/nfc/<id>/entregas`) não casa nada e herda os 180 s. O upload irmão da Loja Virtual
(`POST /api/virtuais/producao/<id>/video`) termina em `/video` e por isso escapa.

**Racional**: um arquivo de 147 MB numa conexão de subida de 8 Mbps leva mais de 150 s. Está no
limite hoje e passa a ser rotina quando a equipe subir vídeos 4K sabendo que o servidor os comprime.

## D7 — Privacidade dos recados

**Decisão**: guardar apenas o texto e um nome opcional. Nada de e-mail, telefone, IP ou impressão do
navegador. O recado é apagável junto com a tag (cascade) e por ação da equipe.

**Racional**: é a menor superfície de dado pessoal que ainda cumpre o pedido. O controle de abuso
fica no limite de taxa por origem, que o `flask-limiter` já faz em memória sem persistir nada.

**Pendência assumida**: a spec não define retenção. Como o volume hoje é zero e a decisão não muda o
modelo de dados, fica registrada em `docs/05` para o dono decidir quando houver acervo.

## D8 — O que já existe e será reaproveitado no frontend (Princípio I)

Levantamento do que a casa já resolveu, para não inventar nada duas vezes.

| Preciso de | Já existe em | Decisão |
|---|---|---|
| Barra de progresso de upload | `apps/internal/src/lib/revisao.ts:53-89` (`uploadForm` com XHR) e `components/UploadProgressBar.tsx` | **Reusar**. O `VideoDialog` de hoje só mostra `loading`; com arquivos de 150 MB isso é botão mudo por minutos |
| Não perder o arquivo no celular | `packages/ui/src/components/file-upload.tsx:60-63` (`snapshotFile`) | Reusar ao trocar o input do diálogo |
| Acompanhar processo que termina depois | `apps/internal/src/lib/adminConfig.ts:170-176` — `refetchInterval` que devolve `false` quando o backend diz que acabou | Copiar a mecânica para o estado "preparando" |
| Troca de cena com animação | `apps/public/src/components/ProductGallery.tsx:112-154` — `AnimatePresence mode="wait"` com `key` discriminante | Molde da máquina capa → abertura → menu → mensagem |
| Entrada escalonada respeitando movimento reduzido | `apps/public/src/pages/NfcPage.tsx:60-67` — helper `enter(delay)` que devolve `{}` sob `useReducedMotion` | Já está na própria página; estender às cenas novas |
| Formulário público pequeno com erro por campo | `apps/public/src/lib/virtuais.ts:239-244` (`fieldErrorsFrom`) | Reusar; o recado tem dois campos e não justifica react-hook-form |
| Guardar "já viu a abertura" no aparelho | `apps/public/src/lib/wishlist.ts:33-47` — par `getAll`/`saveAll` com `try/catch` que degrada em silêncio | Copiar o padrão, chave própria |
| Botão de link externo | `apps/public/src/pages/NfcPage.tsx:227-238` — `min-h-[48px]`, `rel="noopener noreferrer"`, foco visível, e só renderiza com a URL na mão | Molde exato dos botões de Spotify e Instagram |
| Cor e tipografia | `apps/public/tailwind.config.ts` — paleta `lamp.*` criada na 255 para esta página, mais `gold`, `accent`, `ink` | Zero cor nova. Texto em `gold` usa `gold-ink`, porque `gold` sobre `gold-soft` dá 3,25:1 e reprova AA |

**Duas ausências reais, decididas aqui**:

1. **Não existe componente de checkbox** em `@manto/ui`; cada app monta o seu com `<input
   type="checkbox">` dentro de um `<label>` (`apps/internal/src/pages/AdminUserEditPage.tsx:356-371`).
   A caixinha da moldura segue esse padrão local. Criar um componente compartilhado agora ampliaria
   a feature sem necessidade.
2. **Não existe proporção de retrato para vídeo** — todo `<video>` do repositório usa `aspect-video`
   (16:9), inclusive o card que motivou a queixa (`components/nfc/NfcVideoCard.tsx:35`). Esta feature
   cria o padrão `aspect-[9/16]` com `object-contain` sobre `bg-ink`, seguindo a lição registrada em
   `CharacterCard.tsx:36-38`, onde `object-cover` decapitava personagem.

**Conflito resolvido**: `useNfcResolution` usa `staleTime: Infinity`
(`apps/public/src/lib/nfc.ts:44`) porque o conteúdo não muda durante a visita. Isso continua
verdadeiro: a página pública **não** acompanha o processamento. Se a cliente abrir durante a
conversão, ela vê a página sem a mensagem especial, e o menu aparece completo na próxima visita.
Polling de "preparando" existe só no ERP, onde a equipe está esperando.
